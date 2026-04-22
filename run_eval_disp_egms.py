# run_eval_disp_egms.py — EU DISP-S1 validation against EGMS L2a reference
#
# Downloads a 6-month stack of S1 IW SLC scenes from CDSE (Copernicus Data
# Space Ecosystem) over Bologna, Italy, builds a CSLC-S1 stack using compass,
# runs the full DISP pipeline (dolphin native), and compares the resulting
# LOS velocity field against EGMS L2a per-track PS reference products.
#
# Target:
#   Burst     : t117_249422_iw2  (Bologna city centre, ascending track 117)
#   Frame     : OPERA F31178
#   Period    : 2021-01-01 .. 2021-06-30   (within EGMS 2018_2022 release)
#   EGMS      : level L2a, release 2018_2022, ascending track 117
#
# Prerequisites:
#   - CDSE_CLIENT_ID / CDSE_CLIENT_SECRET in .env or env vars
#   - EGMS_TOKEN in .env (from https://egms.land.copernicus.eu/ user profile)
#   - ~/.cdsapirc with valid CDS API credentials (if dolphin/MintPy ERA5 path used)
#   - conda env `subsideo`: isce3, compass, dolphin, tophu, snaphu, opera-utils
#   - pip: EGMStoolkit (pip install git+https://github.com/alexisInSAR/EGMStoolkit.git)
#
# Storage estimate : ~130 GB (15 SLCs x ~8 GB + CSLC/DISP outputs)
# Compute estimate : 3-6 hours depending on hardware
#
# Resume-safe: each stage skips work if outputs already exist.
import warnings; warnings.filterwarnings("ignore")

EXPECTED_WALL_S = 5400   # Plan 01-07 supervisor AST-parses this constant (D-11)

if __name__ == "__main__":
    import os
    import sqlite3
    import sys
    import time
    from datetime import datetime
    from pathlib import Path

    import numpy as np
    from dotenv import load_dotenv

    from subsideo.data.cdse import CDSEClient, extract_safe_s3_prefix
    from subsideo.data.dem import fetch_dem
    from subsideo.data.orbits import fetch_orbit
    from subsideo.products.cslc import run_cslc
    from subsideo.products.disp import run_disp
    from subsideo.validation.harness import (
        bounds_for_burst,
        bounds_for_mgrs_tile,
        credential_preflight,
        download_reference_with_retry,
        ensure_resume_safe,
        select_opera_frame_by_utc_hour,
    )

    load_dotenv()

    credential_preflight([
        "CDSE_CLIENT_ID", "CDSE_CLIENT_SECRET",
        "EARTHDATA_USERNAME", "EARTHDATA_PASSWORD",
        "EGMS_TOKEN",
    ])

    # ── Configuration ────────────────────────────────────────────────────────
    BURST_ID = "t117_249422_iw2"
    RELATIVE_ORBIT = 117
    EGMS_TRACK = 117
    EGMS_PASS = "Ascending"
    EGMS_RELEASE = "2018_2022"
    EGMS_LEVEL = "L2a"

    # 6-month window: ~15 S1A repeat-pass acquisitions at 12-day interval
    DATE_START = "2021-01-01"
    DATE_END   = "2021-06-30"

    # Burst footprint via harness.bounds_for_burst (ENV-08 — no hand-coded
    # numeric bounds literal). BURST_BBOX is unbuffered for STAC / ROI
    # queries; DEM fetch (Stage 4) uses a wider buffered tuple.
    BURST_BBOX = bounds_for_burst(BURST_ID, buffer_deg=0.0)
    EPSG = 32632  # UTM 32N (Bologna)

    OUT = Path("./eval-disp-egms")
    OUT.mkdir(exist_ok=True)

    print("=" * 70)
    print("DISP-S1 Validation: subsideo vs EGMS EU L2a Reference")
    print("=" * 70)
    print(f"  Burst      : {BURST_ID}")
    print(f"  Rel. orbit : {RELATIVE_ORBIT}")
    print(f"  Period     : {DATE_START} -> {DATE_END}")
    print(f"  EGMS       : {EGMS_LEVEL} {EGMS_RELEASE} track {EGMS_TRACK} {EGMS_PASS}")
    print(f"  Output dir : {OUT}")

    # ── Pre-flight checks ────────────────────────────────────────────────────
    # Credentials already validated above via harness.credential_preflight.
    cdsapirc = Path.home() / ".cdsapirc"
    if not cdsapirc.exists():
        print("  WARN: ~/.cdsapirc not found -- ERA5 correction paths in MintPy will fail.")
        print("        Dolphin-native velocity path does not require ERA5, continuing.")
    print(f"  CDS API    : {cdsapirc if cdsapirc.exists() else '(missing)'}")
    print()

    # ── Stage 1: CDSE client ─────────────────────────────────────────────────
    print("-- Stage 1: CDSE authentication --")
    cdse = CDSEClient(
        client_id=os.environ["CDSE_CLIENT_ID"],
        client_secret=os.environ["CDSE_CLIENT_SECRET"],
    )
    _ = cdse._get_token()  # fail fast on bad credentials
    print("  CDSE token OK")

    # ── Stage 2: EGMS L2a reference download ────────────────────────────────
    print("\n-- Stage 2: EGMS L2a reference --")
    ref_dir = OUT / "egms_reference"
    ref_dir.mkdir(exist_ok=True)

    # EGMStoolkit unzips each granule into its own subdirectory, so search
    # recursively. Filter out EGMStoolkit's own merged-output CSVs to avoid
    # picking up stale state on re-runs.
    existing_csv = sorted(
        p for p in ref_dir.rglob("*.csv")
        if not p.name.startswith("merged_")
    )
    if existing_csv:
        print(f"  {len(existing_csv)} EGMS CSV file(s) already downloaded")
        for p in existing_csv[:5]:
            print(f"    {p.relative_to(ref_dir)}")
        egms_csv_paths = existing_csv
    else:
        print("  Running EGMStoolkit download workflow...")
        try:
            from EGMStoolkit.classes import EGMSdownloaderapi, EGMSS1burstIDapi, EGMSS1ROIapi
            from EGMStoolkit.functions import egmsdatatools
        except ImportError as exc:
            raise SystemExit(
                "EGMStoolkit not installed. See run_eval_disp_egms.py header for "
                f"install instructions. Error: {exc}"
            ) from exc

        # 2a. Fetch ESA->EGMS burst ID map (cached inside EGMStoolkit's
        # bundled 3rdparty/ directory; S1burstIDmap takes no workdirectory).
        print("  [2a] burst ID map...")
        info = EGMSS1burstIDapi.S1burstIDmap(verbose=False)
        info.downloadfile(verbose=False)

        # 2b. Build ROI for Bologna bbox, L2a, 2018_2022 release, track 117 asc.
        # bbox must be a list[float] (the str type hint is misleading -- a
        # str triggers a GMT pscoast country-code lookup path).
        print("  [2b] ROI selection...")
        roi = EGMSS1ROIapi.S1ROIparameter(
            workdirectory=str(ref_dir),
            verbose=False,
        )
        roi.bbox = list(BURST_BBOX)
        roi.egmslevel = EGMS_LEVEL
        roi.release = EGMS_RELEASE
        roi.createROI(verbose=False)
        roi.detectfromIDmap(
            info,
            Track_user=EGMS_TRACK,
            Pass_user=EGMS_PASS,
            verbose=False,
        )

        # 2c. Download matched granules
        print("  [2c] downloading granules...")
        dl = EGMSdownloaderapi.egmsdownloader(verbose=False)
        dl.updatelist(infoS1ROIparameter=roi, verbose=False)
        dl.printlist(verbose=True)
        dl.token = os.environ["EGMS_TOKEN"]
        dl.download(outputdir=str(ref_dir), unzipmode=False, cleanmode=False)
        dl.unzipfile(
            outputdir=str(ref_dir),
            unzipmode=True,
            nbworker=2,
            cleanmode=False,
            verbose=False,
        )

        # 2d. Merge into consolidated CSV, then clip to bbox
        print("  [2d] merging + clipping...")
        egmsdatatools.datamergingcsv(
            infoEGMSdownloader=dl,
            inputdir=str(ref_dir),
            outputdir=str(ref_dir),
            mode="onlist",
            verbose=False,
            paratosave="all",
        )

        egms_csv_paths = sorted(
            p for p in ref_dir.rglob("*.csv")
            if not p.name.startswith("merged_")
        )
        print(f"  {len(egms_csv_paths)} EGMS CSV file(s) available")

    if not egms_csv_paths:
        print("  WARNING: no EGMS L2a CSVs -- validation will be deferred.")

    # ── Stage 3: Search CDSE for S1 SLCs ─────────────────────────────────────
    #
    # CDSE's STAC backend intermittently returns Postgres OOM on wide-date
    # queries ("OutOfMemoryError ... SPI Exec"). Chunk the window into
    # monthly slices -- each slice returns ~30 items which stays well under
    # the backend's memory threshold and reduces WAF pagination pressure.
    print("\n-- Stage 3: Search S1 SLC scenes on CDSE --")
    stac_cache = OUT / "stac_items.json"
    import json as _json
    if stac_cache.exists():
        stac_items = _json.loads(stac_cache.read_text())
        print(f"  Loaded cached STAC items: {len(stac_items)} (from {stac_cache.name})")
    else:
        from datetime import timedelta

        # Load any partial cache from a prior failed run so we only re-fetch
        # missing slices.
        partial_cache = OUT / "stac_items.partial.json"
        stac_items: list[dict]
        if partial_cache.exists():
            stac_items = _json.loads(partial_cache.read_text())
            print(f"  Resuming from partial cache: {len(stac_items)} items")
        else:
            stac_items = []
        seen_ids: set[str] = {it.get("id") for it in stac_items if it.get("id")}

        slice_start = datetime.fromisoformat(f"{DATE_START}T00:00:00")
        window_end = datetime.fromisoformat(f"{DATE_END}T23:59:59")
        failed_slices: list[str] = []
        while slice_start < window_end:
            slice_end = min(slice_start + timedelta(days=30), window_end)
            label = f"{slice_start.date()} -> {slice_end.date()}"
            try:
                chunk = cdse.search_stac(
                    collection="SENTINEL-1",
                    bbox=list(BURST_BBOX),
                    start=slice_start,
                    end=slice_end,
                    product_type="IW_SLC__1S",
                    max_items=60,
                )
            except Exception as exc:
                print(f"  slice {label}: FAILED ({type(exc).__name__}) -- skipping")
                failed_slices.append(label)
                slice_start = slice_end
                continue
            new = 0
            for it in chunk:
                iid = it.get("id")
                if iid and iid not in seen_ids:
                    seen_ids.add(iid)
                    stac_items.append(it)
                    new += 1
            print(f"  slice {label}: {len(chunk):3d} items ({new} new)")
            # Persist after every successful slice so a later failure still
            # leaves us ahead for the next run.
            partial_cache.write_text(_json.dumps(stac_items))
            slice_start = slice_end

        if failed_slices:
            print(f"  WARN: {len(failed_slices)} slice(s) failed: {failed_slices}")
            print("  Re-run the script later to backfill missing slices.")
        stac_cache.write_text(_json.dumps(stac_items))
        partial_cache.unlink(missing_ok=True)
        print(f"  CDSE STAC total: {len(stac_items)} unique items (cached)")

    def _rel_orbit(item: dict) -> int | None:
        props = item.get("properties", {}) or {}
        for k in ("sat:relative_orbit", "relativeOrbitNumber", "relative_orbit_number"):
            if k in props:
                try:
                    return int(props[k])
                except (TypeError, ValueError):
                    pass
        return None

    def _pol(item: dict) -> str:
        props = item.get("properties", {}) or {}
        return str(props.get("polarisationChannels") or props.get("sar:polarizations") or "")

    def _start_time(item: dict) -> str:
        return (item.get("properties", {}) or {}).get("start_datetime") or \
               (item.get("properties", {}) or {}).get("datetime", "")

    filtered: list[dict] = []
    for it in stac_items:
        ro = _rel_orbit(it)
        if ro != RELATIVE_ORBIT:
            continue
        if "VV" not in _pol(it) or "VH" not in _pol(it):  # dual-pol SDV
            continue
        filtered.append(it)

    # Deduplicate by date (YYYY-MM-DD of start time)
    by_date: dict[str, dict] = {}
    for it in filtered:
        st = _start_time(it)
        if not st:
            continue
        date_key = st[:10]
        if date_key not in by_date:
            by_date[date_key] = it

    slc_items = sorted(by_date.values(), key=_start_time)
    print(f"  {len(slc_items)} unique SDV SLC date(s) on orbit {RELATIVE_ORBIT}")
    for i, it in enumerate(slc_items):
        name = it.get("id", "?")
        print(f"    [{i+1:2d}] {_start_time(it)[:19]}  {name[:55]}")

    if not slc_items:
        raise SystemExit("No S1 SLC scenes found on CDSE -- check bbox/date/orbit.")

    # ── Stage 4: DEM ─────────────────────────────────────────────────────────
    print("\n-- Stage 4: DEM --")
    dem_dir = OUT / "dem"
    dem_dir.mkdir(exist_ok=True)
    existing_dem = sorted(dem_dir.glob("*.tif"))
    if existing_dem:
        dem_path = existing_dem[0]
        print(f"  Already present: {dem_path.name}")
    else:
        dem_path, _ = fetch_dem(
            bounds=list(bounds_for_burst(BURST_ID, buffer_deg=0.2)),
            output_epsg=EPSG,
            output_dir=dem_dir,
        )
        print(f"  DEM: {dem_path.name}")

    # ── Stage 5: Burst database ──────────────────────────────────────────────
    print("\n-- Stage 5: Burst database --")
    burst_db = OUT / "burst_db.sqlite3"
    if not burst_db.exists():
        from opera_utils.burst_frame_db import get_burst_geodataframe
        from pyproj import Transformer

        gdf = get_burst_geodataframe(burst_ids=[BURST_ID])
        if gdf.empty:
            raise SystemExit(f"opera-utils has no geometry for burst {BURST_ID}")
        geom = gdf.iloc[0].geometry
        # opera-utils may attach Z=0 to ring coords; .xy drops Z cleanly and
        # returns matching lon/lat sequences as two 1-D arrays.
        lons, lats = geom.exterior.coords.xy
        t = Transformer.from_crs(4326, EPSG, always_xy=True)
        xs, ys = t.transform(list(lons), list(lats))
        conn = sqlite3.connect(str(burst_db))
        conn.execute(
            "CREATE TABLE burst_id_map "
            "(burst_id_jpl TEXT PRIMARY KEY, epsg INTEGER, "
            "xmin REAL, ymin REAL, xmax REAL, ymax REAL)"
        )
        conn.execute(
            "INSERT INTO burst_id_map VALUES (?, ?, ?, ?, ?, ?)",
            (BURST_ID, EPSG, min(xs), min(ys), max(xs), max(ys)),
        )
        conn.commit()
        conn.close()
        print(f"  Created: {burst_db}")
    else:
        print(f"  Exists: {burst_db}")

    # ── Stage 6: Download SLCs + build CSLC stack ────────────────────────────
    print("\n-- Stage 6: Build CSLC Stack --")
    print(f"  Processing {len(slc_items)} scenes into single-burst CSLCs...")
    input_dir = OUT / "input"
    input_dir.mkdir(exist_ok=True)
    cslc_dir = OUT / "cslc"
    cslc_dir.mkdir(exist_ok=True)
    orbit_dir = OUT / "orbits"
    orbit_dir.mkdir(exist_ok=True)

    cslc_paths: list[Path] = []
    failed_scenes: list[str] = []

    for i, item in enumerate(slc_items):
        item_id: str = item.get("id", "")
        scene_id = item_id.removesuffix(".SAFE")
        sensing_str = _start_time(item)[:19]
        sensing_dt = datetime.fromisoformat(sensing_str.rstrip("Z"))
        date_tag = sensing_dt.strftime("%Y%m%d")
        platform = (item.get("properties", {}) or {}).get("platform", "sentinel-1a")
        sat_tag = "S1A" if "1a" in platform.lower() else "S1B"

        cslc_out = cslc_dir / f"scene_{date_tag}"
        label = f"[{i+1:2d}/{len(slc_items)}] {date_tag}"

        existing = sorted(cslc_out.glob("**/*.h5"))
        existing = [p for p in existing if "runconfig" not in p.name.lower()]
        if existing:
            cslc_h5 = existing[0]
            print(f"  {label}: exists ({cslc_h5.name})")
            cslc_paths.append(cslc_h5)
            continue

        print(f"  {label}: ", end="", flush=True)

        # CDSE STAC 1.1.0 publishes per-swath assets under the SAFE prefix.
        # Derive the SAFE root prefix and download the unzipped SAFE tree.
        s3_uri = extract_safe_s3_prefix(item)

        safe_dir = input_dir / f"{scene_id}.SAFE"
        manifest = safe_dir / "manifest.safe"
        if not manifest.exists():
            if s3_uri is None:
                print("SKIP (no S3 URI in STAC item)")
                failed_scenes.append(date_tag)
                continue
            print("downloading SAFE (CDSE)... ", end="", flush=True)
            try:
                safe_dir = cdse.download_safe(s3_uri, input_dir)
            except Exception as exc:
                print(f"SKIP (download: {exc})")
                failed_scenes.append(date_tag)
                continue

        if not (safe_dir / "manifest.safe").exists():
            print("SKIP (manifest.safe missing after download)")
            failed_scenes.append(date_tag)
            continue
        safe_path = safe_dir

        print("orbit... ", end="", flush=True)
        try:
            orbit_path = fetch_orbit(
                sensing_time=sensing_dt,
                satellite=sat_tag,
                output_dir=orbit_dir,
            )
        except Exception as exc:
            print(f"SKIP (orbit: {exc})")
            failed_scenes.append(date_tag)
            continue

        print("CSLC... ", end="", flush=True)
        t0 = time.time()
        try:
            result = run_cslc(
                safe_paths=[safe_path],
                orbit_path=orbit_path,
                dem_path=dem_path,
                burst_ids=[BURST_ID],
                output_dir=cslc_out,
                burst_database_file=burst_db,
            )
        except Exception as exc:
            elapsed = time.time() - t0
            print(f"FAIL ({elapsed:.0f}s: {exc})")
            failed_scenes.append(date_tag)
            continue

        elapsed = time.time() - t0
        if result.valid and result.output_paths:
            cslc_h5 = result.output_paths[0]
            cslc_paths.append(cslc_h5)
            print(f"OK ({elapsed:.0f}s, {cslc_h5.name})")
        else:
            print(f"FAIL ({elapsed:.0f}s: {result.validation_errors})")
            failed_scenes.append(date_tag)

    print(f"\n  CSLC stack : {len(cslc_paths)} files")
    print(f"  Failed     : {len(failed_scenes)} scenes")
    if failed_scenes:
        print(f"               {', '.join(failed_scenes)}")

    if len(cslc_paths) < 5:
        raise SystemExit(
            f"Only {len(cslc_paths)} CSLCs produced -- need at least 5. "
            "Check download/processing logs above."
        )

    cslc_paths = sorted(cslc_paths, key=lambda p: p.name)
    print("\n  Stack (sorted):")
    for p in cslc_paths:
        sz = p.stat().st_size / 1e6
        print(f"    {p.name}  ({sz:.1f} MB)")

    input_size_gb = sum(
        f.stat().st_size for f in input_dir.rglob("*") if f.is_file()
    ) / 1e9
    print(f"\n  Total SLC storage: {input_size_gb:.1f} GB")

    # ── Stage 7: DISP pipeline ───────────────────────────────────────────────
    print("\n-- Stage 7: DISP Pipeline (dolphin native) --")
    disp_dir = OUT / "disp"
    velocity_path = disp_dir / "dolphin" / "timeseries" / "velocity.tif"

    if velocity_path.exists():
        print(f"  Velocity already exists: {velocity_path}")
        print(f"  Size: {velocity_path.stat().st_size / 1e6:.1f} MB")
    else:
        print(f"  Input  : {len(cslc_paths)} CSLCs")
        print(f"  Output : {disp_dir}")
        print("  Running full DISP pipeline -- this may take several hours...\n")

        t0 = time.time()
        disp_result = run_disp(
            cslc_paths=cslc_paths,
            output_dir=disp_dir,
            threads_per_worker=8,
            n_parallel_bursts=2,
            block_shape=(512, 512),
            n_parallel_unwrap=8,
        )
        elapsed_min = (time.time() - t0) / 60

        print(f"\n  Completed in {elapsed_min:.1f} minutes")
        print(f"  Valid        : {disp_result.valid}")
        print(f"  Velocity     : {disp_result.velocity_path}")
        print(f"  Time-series  : {len(disp_result.timeseries_paths)} file(s)")

        if disp_result.qc_warnings:
            print("  QC warnings:")
            for w in disp_result.qc_warnings:
                print(f"    ! {w}")

        if not disp_result.valid:
            print(f"  Errors: {disp_result.validation_errors}")
            raise SystemExit("DISP pipeline failed -- see errors above.")

        velocity_path = disp_result.velocity_path

    if velocity_path is None or not velocity_path.exists():
        raise SystemExit("No velocity.tif produced. DISP pipeline may have failed silently.")

    # ── Stage 8: Output inspection ───────────────────────────────────────────
    print("\n-- Stage 8: Output Inspection --")
    print(f"\n  Our velocity: {velocity_path}")

    import rasterio

    with rasterio.open(velocity_path) as ds:
        our_velocity = ds.read(1).astype(np.float64)
        print(f"  shape : {our_velocity.shape}")
        print(f"  CRS   : {ds.crs}")
        print(f"  dtype : {ds.dtypes[0]}")

    valid = np.isfinite(our_velocity) & (our_velocity != 0)
    if valid.any():
        print("\n  velocity stats (non-zero):")
        print(f"    valid pixels : {valid.sum():,}")
        print(f"    min          : {np.nanmin(our_velocity[valid]):.4f}")
        print(f"    max          : {np.nanmax(our_velocity[valid]):.4f}")
        print(f"    mean         : {np.nanmean(our_velocity[valid]):.4f}")
        print(f"    std          : {np.nanstd(our_velocity[valid]):.4f}")

    # ── Stage 9: Compare against EGMS L2a ────────────────────────────────────
    print("\n-- Stage 9: Validation vs EGMS L2a --")
    if not egms_csv_paths:
        print("  No EGMS L2a reference CSVs available -- comparison deferred.")
        sys.exit(0)

    from subsideo.validation.compare_disp import compare_disp_egms_l2a

    result = compare_disp_egms_l2a(
        velocity_path=velocity_path,
        egms_csv_paths=egms_csv_paths,
        velocity_col="mean_velocity",
        velocity_units="rad_per_year",
    )

    print(f"\n  {'='*60}")
    print(f"  Correlation  : {result.correlation:.4f}   (criterion: > 0.92)")
    print(f"  Bias         : {result.bias_mm_yr:+.4f} mm/yr (criterion: < 3 mm/yr)")
    print(f"  {'='*60}")
    for k, v in result.pass_criteria.items():
        print(f"  {k:30s}: {'PASS' if v else 'FAIL'}")
    overall = all(result.pass_criteria.values())
    print(f"  {'Overall':30s}: {'PASS' if overall else 'FAIL'}")
    print(f"  {'='*60}")
