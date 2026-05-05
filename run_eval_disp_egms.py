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
import warnings; warnings.filterwarnings("ignore")  # noqa: E702, I001

from typing import Literal  # noqa: E402

# Phase 4 D-Claude's-Discretion: 6h cap (warm re-run + ramp fit + adapter ~30 min/cell;
# cold full-pipeline ~3 h/cell + safety margin). 21600s expressed as 60*60*6 because
# supervisor AST-parser whitelists nested BinOp of literal Constants (Plan 01-07 T-07-06).
EXPECTED_WALL_S = 60 * 60 * 6   # 21600 -- Plan 01-07 supervisor AST-parses this
REFERENCE_MULTILOOK_METHOD: Literal["block_mean"] = "block_mean"  # Phase 4 D-04
ERA5_MODE: Literal["on", "off"] = "on"
BASELINE_ERA5_MODE: Literal["off"] = "off"


def _reproject_mask_to_grid(
    mask: "object",  # numpy ndarray
    src_transform: "object",  # rasterio Affine
    src_crs: "object",  # rasterio CRS
    target_shape: tuple[int, int],
) -> "object":
    """Reproject a (H, W) bool stable_mask onto a target raster grid via nearest-neighbour.

    Phase 4 helper: re-grids a stable-terrain mask (built on the DEM grid) onto
    the CSLC / velocity raster grid before feeding `coherence_stats` /
    `residual_mean_velocity`. Uses rasterio.warp.reproject in nearest mode to
    preserve boolean class labels.
    """
    import numpy as np
    import rasterio as _rio
    from rasterio.warp import Resampling as _Resampling
    from rasterio.warp import reproject as _reproject

    h_src, w_src = mask.shape
    h_tgt, w_tgt = target_shape
    sx = w_src / w_tgt
    sy = h_src / h_tgt
    target_transform = src_transform * _rio.Affine(sx, 0, 0, 0, sy, 0)
    out = np.zeros(target_shape, dtype=np.float32)
    _reproject(
        source=mask.astype(np.float32),
        destination=out,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=target_transform,
        dst_crs=src_crs,
        resampling=_Resampling.nearest,
    )
    return out.astype(bool)

if __name__ == "__main__":
    import os
    import sqlite3
    import sys
    import time
    from datetime import datetime, timezone
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
        credential_preflight,
        validate_safe_path,
    )

    load_dotenv()

    # EGMS_TOKEN is only required when the EGMS L2a CSV cache is empty
    # (Stage 2 download path). On warm re-runs from cached CSVs the token is
    # never read; relax the preflight conditionally so the script can be
    # re-run without re-issuing an EGMS portal token.
    _required_env = ["CDSE_CLIENT_ID", "CDSE_CLIENT_SECRET",
                     "EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"]
    _egms_cache_dir = Path("./eval-disp-egms/egms_reference")
    _has_egms_csv = bool(
        _egms_cache_dir.exists() and any(
            p for p in _egms_cache_dir.rglob("*.csv")
            if not p.name.startswith("merged_")
        )
    )
    if not _has_egms_csv:
        _required_env.append("EGMS_TOKEN")
    credential_preflight(_required_env)

    # Phase 4 Stage 12 prerequisite: wall-time + run-start tracking for meta.json
    # Phase 4 ME-03: datetime.utcnow() is deprecated in 3.12+; use the
    # timezone-aware now(timezone.utc) alternative and emit a 'Z' suffix.
    t_start = time.monotonic()
    run_start_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

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
        if ERA5_MODE == "on":
            raise SystemExit(
                "~/.cdsapirc not found. ERA5 tropospheric correction requires "
                "CDS API credentials.\nRegister at https://cds.climate.copernicus.eu/"
            )
        print("  WARN: ~/.cdsapirc not found -- ERA5 correction is disabled.")
    print(f"  ERA5 mode  : {ERA5_MODE} (baseline: {BASELINE_ERA5_MODE})")
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
        dem_cache_mode = "reused"
        print(f"  Already present: {dem_path.name}")
    else:
        dem_path, _ = fetch_dem(
            bounds=list(bounds_for_burst(BURST_ID, buffer_deg=0.2)),
            output_epsg=EPSG,
            output_dir=dem_dir,
        )
        dem_cache_mode = "redownloaded"
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
    slc_cache_inputs: list[tuple[str, Path, str]] = []
    cslc_cache_inputs: list[tuple[str, Path, str]] = []
    tracked_orbits: list[tuple[Path, datetime, str]] = []
    successful_sensing_times: list[datetime] = []

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
            cslc_cache_inputs.append((f"cslc_{date_tag}", cslc_h5, "reused"))
            successful_sensing_times.append(sensing_dt)
            continue

        print(f"  {label}: ", end="", flush=True)

        # CDSE STAC 1.1.0 publishes per-swath assets under the SAFE prefix.
        # Derive the SAFE root prefix and download the unzipped SAFE tree.
        s3_uri = extract_safe_s3_prefix(item)

        safe_dir = input_dir / f"{scene_id}.SAFE"
        manifest = safe_dir / "manifest.safe"
        slc_cache_mode = "reused"
        if not manifest.exists():
            if s3_uri is None:
                print("SKIP (no S3 URI in STAC item)")
                failed_scenes.append(date_tag)
                continue
            print("downloading SAFE (CDSE)... ", end="", flush=True)
            try:
                safe_dir = cdse.download_safe(s3_uri, input_dir)
                slc_cache_mode = "redownloaded"
            except Exception as exc:
                print(f"SKIP (download: {exc})")
                failed_scenes.append(date_tag)
                continue

        if not (safe_dir / "manifest.safe").exists():
            print("SKIP (manifest.safe missing after download)")
            failed_scenes.append(date_tag)
            continue
        if not validate_safe_path(safe_dir):
            print("SKIP (SAFE integrity validation failed)")
            failed_scenes.append(date_tag)
            continue
        safe_path = safe_dir
        slc_cache_inputs.append((f"slc_{date_tag}", safe_path, slc_cache_mode))

        print("orbit... ", end="", flush=True)
        try:
            existing_orbit_paths = {p.resolve() for p in orbit_dir.glob("*.EOF")}
            orbit_path = fetch_orbit(
                sensing_time=sensing_dt,
                satellite=sat_tag,
                output_dir=orbit_dir,
            )
            orbit_cache_mode = (
                "reused" if orbit_path.resolve() in existing_orbit_paths else "redownloaded"
            )
            tracked_orbits.append((orbit_path, sensing_dt, orbit_cache_mode))
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
            cslc_cache_inputs.append((f"cslc_{date_tag}", cslc_h5, "regenerated"))
            successful_sensing_times.append(sensing_dt)
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
    baseline_disp_dir = OUT / "disp"
    disp_dir = OUT / ("disp-era5-on" if ERA5_MODE == "on" else "disp")
    velocity_path = disp_dir / "dolphin" / "timeseries" / "velocity.tif"
    if ERA5_MODE == "on":
        print(f"  Warm baseline preserved: {baseline_disp_dir}")

    if velocity_path.exists():
        print(f"  Velocity already exists: {velocity_path}")
        print(f"  Size: {velocity_path.stat().st_size / 1e6:.1f} MB")
        velocity_cache_mode = "reused"
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
            era5_mode=ERA5_MODE,
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
        velocity_cache_mode = "regenerated"

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

    # ── Stage 9: Validation vs EGMS L2a (Phase 4 D-01 + D-02 form-c) ──────────
    print(
        "\n-- Stage 9: Validation vs EGMS L2a "
        "(Phase 4 prepare_for_reference) --"
    )
    if not egms_csv_paths:
        print("  No EGMS L2a reference CSVs available -- comparison deferred.")
        sys.exit(0)

    from subsideo.validation.compare_disp import (
        ReferenceGridSpec,
        _load_egms_l2a_points,
        prepare_for_reference,
    )

    print(
        "  Multilooking native velocity at EGMS L2a PS points via "
        "prepare_for_reference(method='block_mean')..."
    )
    egms_df = _load_egms_l2a_points(egms_csv_paths, velocity_col="mean_velocity")
    egms_spec = ReferenceGridSpec(
        points_lonlat=np.column_stack([
            egms_df["lon"].values.astype(np.float64),
            egms_df["lat"].values.astype(np.float64),
        ]),
        crs="EPSG:4326",
        point_ids=None,
    )
    our_at_ps_rad_per_year = prepare_for_reference(
        native_velocity=velocity_path,
        reference_grid=egms_spec,
        method=REFERENCE_MULTILOOK_METHOD,
    )
    SENTINEL1_WAVELENGTH_M = 0.05546576
    our_at_ps_mm_yr = (
        -our_at_ps_rad_per_year * SENTINEL1_WAVELENGTH_M / (4.0 * np.pi) * 1000.0
    )
    ref_ps_mm_yr = egms_df["mean_velocity"].values.astype(np.float64)
    valid = np.isfinite(our_at_ps_mm_yr) & np.isfinite(ref_ps_mm_yr)
    n_valid = int(valid.sum())
    print(f"  Paired PS samples: {n_valid:,} / {len(ref_ps_mm_yr):,}")

    if n_valid >= 100:
        correlation = float(
            np.corrcoef(our_at_ps_mm_yr[valid], ref_ps_mm_yr[valid])[0, 1]
        )
        bias = float((our_at_ps_mm_yr[valid] - ref_ps_mm_yr[valid]).mean())
        rmse = float(
            np.sqrt(((our_at_ps_mm_yr[valid] - ref_ps_mm_yr[valid]) ** 2).mean())
        )
    else:
        correlation = float("nan")
        bias = float("nan")
        rmse = float("nan")
    sample_count = n_valid

    print(f"\n  {'='*60}")
    print(f"  Correlation  : {correlation:.4f}   (criterion: > 0.92)")
    print(f"  Bias         : {bias:+.4f} mm/yr (criterion: < 3 mm/yr)")
    print(f"  RMSE         : {rmse:.4f} mm/yr")
    print(f"  {'='*60}")

    # --- Phase 4 Stage 10: product-quality block (CONTEXT D-05..D-08) ---
    print(
        "\n  [Phase 4 Stage 10] Computing product-quality (coherence + "
        "residual) on stable terrain..."
    )
    from pathlib import Path as _PhasePath

    from rasterio.warp import Resampling as _Resampling
    from rasterio.warp import reproject as _reproject

    from subsideo.data.natural_earth import load_coastline_and_waterbodies
    from subsideo.data.worldcover import (
        fetch_worldcover_class60,
        load_worldcover_for_bbox,
    )
    from subsideo.validation.selfconsistency import (
        coherence_stats,
        compute_ifg_coherence_stack,
        residual_mean_velocity,
    )
    from subsideo.validation.stable_terrain import build_stable_mask

    # Phase 4 B2 acknowledgement: `dem_path` is pre-bound at Stage 4 and
    # reachable here; do NOT re-bind. Slope-from-DEM is computed inline
    # because the existing `compute_slope_from_dem` analog lives in
    # run_eval_cslc_selfconsist_nam.py as a closure (Phase 3 D-Claude's-
    # Discretion). Same algorithm, kept colocated for Phase 4.
    def _slope_from_dem(p):  # noqa: ANN001, ANN202 — inline helper closure
        import rasterio as _rio_local
        with _rio_local.open(p) as _src:
            dem = _src.read(1).astype(np.float32)
            pixel_m = abs(_src.transform.a)
            dem_transform = _src.transform
            dem_crs = _src.crs
        dz_dy, dz_dx = np.gradient(dem, pixel_m)
        slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
        return np.degrees(slope_rad).astype(np.float32), dem_transform, dem_crs

    # 10.1 Build stable mask (CONTEXT D-06: identical params to Phase 3 SoCal)
    worldcover_dir = _PhasePath("eval-disp-egms/worldcover")
    fetch_worldcover_class60(BURST_BBOX, out_dir=worldcover_dir)
    wc_data, wc_transform, wc_crs = load_worldcover_for_bbox(
        BURST_BBOX, tiles_dir=worldcover_dir
    )
    slope_deg, dem_transform, dem_crs = _slope_from_dem(dem_path)
    coastline, waterbodies = load_coastline_and_waterbodies(BURST_BBOX)
    wc_on_dem = np.empty(slope_deg.shape, dtype=wc_data.dtype)
    _reproject(
        source=wc_data, destination=wc_on_dem,
        src_transform=wc_transform, src_crs=wc_crs,
        dst_transform=dem_transform, dst_crs=dem_crs,
        resampling=_Resampling.nearest,
    )
    stable_mask = build_stable_mask(
        wc_on_dem, slope_deg, coastline=coastline, waterbodies=waterbodies,
        transform=dem_transform, crs=dem_crs,
        coast_buffer_m=5000, water_buffer_m=500, slope_max_deg=10,
    )
    n_stable = int(stable_mask.sum())
    print(f"  stable_mask pixels: {n_stable:,}")
    cell_status = "BLOCKER" if n_stable < 100 else "MIXED"

    # 10.2 Coherence: Bologna fresh path (no Phase 3 cache to reuse; D-08)
    # Phase 4 B2 acknowledgement: `dem_path` is pre-bound at Stage 4
    # (run_eval_disp_egms.py Stage 4). Reachable here; do NOT re-bind.
    coherence_source = "fresh"
    # phase3_metrics_path retained only for meta.json input_hashes (read-only)
    phase3_metrics_path = _PhasePath("eval-cslc-selfconsist-nam/metrics.json")
    print("  coherence: fresh-computing from cached CSLCs (boxcar 5x5)...")
    # B1 root-cause fix: import the PUBLIC compute_ifg_coherence_stack from
    # selfconsistency.py (Plan 04-01 Task 3 promotion). Do NOT import from
    # run_eval_cslc_selfconsist_nam -- inner-scope, unreachable.
    sorted_h5 = sorted(_PhasePath("eval-disp-egms/cslc").rglob("*.h5"))
    sorted_h5 = [p for p in sorted_h5 if "runconfig" not in p.name.lower()]
    ifgrams_stack = compute_ifg_coherence_stack(sorted_h5, boxcar_px=5)
    stable_mask_cslc = _reproject_mask_to_grid(
        stable_mask, dem_transform, dem_crs, ifgrams_stack.shape[1:]
    )
    coh_stats = coherence_stats(
        ifgrams_stack, stable_mask_cslc, coherence_threshold=0.6
    )

    # 10.3 Residual: ALWAYS fresh from dolphin output (CONTEXT D-08)
    print("  residual: fresh from dolphin velocity.tif...")
    import rasterio as _rio
    with _rio.open(velocity_path) as _src:
        v_rad_per_year = _src.read(1).astype(np.float64)
    v_mm_yr = (
        -v_rad_per_year * SENTINEL1_WAVELENGTH_M / (4.0 * np.pi) * 1000.0
    )
    stable_mask_vel = _reproject_mask_to_grid(
        stable_mask, dem_transform, dem_crs, v_mm_yr.shape
    )
    if int(stable_mask_vel.sum()) > 0:
        residual = residual_mean_velocity(
            v_mm_yr, stable_mask_vel, frame_anchor="median"
        )
    else:
        residual = float("nan")
    print(f"  residual_mm_yr: {residual:+.2f}")

    # --- Phase 4 Stage 11: ramp-attribution diagnostic (CONTEXT D-09..D-12) ---
    print("\n  [Phase 4 Stage 11] Per-IFG planar ramp fit + attribution...")
    import re as _re_phase4

    from subsideo.validation.matrix_schema import (
        DISPCandidateOutcome,
        DISPCellMetrics,
        DISPProductQualityResultJson,
        Era5Diagnostic,
        MetaJson,
        PerIFGRamp,
        RampAggregate,
        RampAttribution,
        ReferenceAgreementResultJson,
    )
    from subsideo.validation.disp_candidates import (
        candidate_output_dir,
        candidate_status_from_metrics,
        make_candidate_blocker,
    )
    from subsideo.validation.disp_diagnostics import (
        cache_provenance,
        summarize_dem,
        summarize_orbit_coverage,
        summarize_terrain,
    )
    from subsideo.validation.selfconsistency import (
        auto_attribute_ramp,
        compute_ramp_aggregate,
        fit_planar_ramp,
    )

    unwrapped_dir = disp_dir / "dolphin" / "unwrapped"
    unw_files = sorted(unwrapped_dir.glob("*.unw.tif"))
    date_pat = _re_phase4.compile(r"^(\d{8})_(\d{8})\.unw\.tif$")

    def _is_sequential_12day(ref_iso: str, sec_iso: str) -> bool:
        from datetime import datetime as _dt
        # Bologna 2021 stack is dual-sat S1A+S1B with effective 6-day cadence
        # but we still construct nominal 12-day pairs for cross-cell methodology
        # consistency (D-07). Tolerance widened to +/- 2 days to accommodate
        # cross-constellation pairs that fall on alternating S1A/S1B days.
        return abs(
            (_dt.fromisoformat(sec_iso) - _dt.fromisoformat(ref_iso)).days - 12
        ) <= 1

    sequential_unw = []
    for f in unw_files:
        mt = date_pat.match(f.name)
        if mt is None:
            continue
        ref_iso = f"{mt.group(1)[0:4]}-{mt.group(1)[4:6]}-{mt.group(1)[6:8]}"
        sec_iso = f"{mt.group(2)[0:4]}-{mt.group(2)[4:6]}-{mt.group(2)[6:8]}"
        if _is_sequential_12day(ref_iso, sec_iso):
            sequential_unw.append((f, ref_iso, sec_iso))
    print(f"  sequential 12-day IFGs found: {len(sequential_unw)}")

    ifgrams_unw_stack_list = []
    for f, _, _ in sequential_unw:
        with _rio.open(f) as _src:
            ifgrams_unw_stack_list.append(_src.read(1).astype(np.float32))
    ifgrams_unw_stack = (
        np.stack(ifgrams_unw_stack_list, axis=0)
        if ifgrams_unw_stack_list
        else np.zeros((0, 1, 1), dtype=np.float32)
    )

    ifg_coh_means: list[float] = []
    cor_dir = disp_dir / "dolphin" / "interferograms"
    for f, _, _ in sequential_unw:
        cor_file = cor_dir / f.name.replace(".unw.tif", ".int.cor.tif")
        if not cor_file.exists():
            ifg_coh_means.append(float("nan"))
            continue
        with _rio.open(cor_file) as _src:
            cor = _src.read(1).astype(np.float64)
        valid_cor = np.isfinite(cor) & (cor > 0)
        ifg_coh_means.append(
            float(cor[valid_cor].mean()) if valid_cor.any() else float("nan")
        )
    ifg_coh_per_ifg = np.array(ifg_coh_means, dtype=np.float64)

    if ifgrams_unw_stack.shape[0] > 0:
        ramp_data = fit_planar_ramp(ifgrams_unw_stack, mask=None)
        agg_dict = compute_ramp_aggregate(ramp_data, ifg_coh_per_ifg)
    else:
        ramp_data = {
            "ramp_magnitude_rad": np.zeros((0,), dtype=np.float64),
            "ramp_direction_deg": np.zeros((0,), dtype=np.float64),
            "slope_x": np.zeros((0,), dtype=np.float64),
            "slope_y": np.zeros((0,), dtype=np.float64),
            "intercept_rad": np.zeros((0,), dtype=np.float64),
        }
        agg_dict = {
            "mean_magnitude_rad": float("nan"),
            "direction_stability_sigma_deg": float("nan"),
            "magnitude_vs_coherence_pearson_r": float("nan"),
            "n_ifgs": 0,
        }
    attributed_source = auto_attribute_ramp(
        direction_stability_sigma_deg=agg_dict["direction_stability_sigma_deg"],
        magnitude_vs_coherence_pearson_r=(
            agg_dict["magnitude_vs_coherence_pearson_r"]
        ),
    )
    print(
        f"  ramp aggregate: mean_mag={agg_dict['mean_magnitude_rad']:.2f} rad, "
        f"sigma_dir={agg_dict['direction_stability_sigma_deg']:.1f} deg, "
        f"r(mag,coh)={agg_dict['magnitude_vs_coherence_pearson_r']:.2f}"
    )
    print(f"  auto-attributed source: {attributed_source}")

    per_ifg_records = []
    for k, (_f, ref_iso, sec_iso) in enumerate(sequential_unw):
        per_ifg_records.append(PerIFGRamp(
            ifg_idx=k,
            ref_date_iso=ref_iso,
            sec_date_iso=sec_iso,
            ramp_magnitude_rad=float(ramp_data["ramp_magnitude_rad"][k]),
            ramp_direction_deg=float(ramp_data["ramp_direction_deg"][k]),
            ifg_coherence_mean=(
                float(ifg_coh_per_ifg[k])
                if not np.isnan(ifg_coh_per_ifg[k])
                else None
            ),
        ))
    ramp_attribution_obj = RampAttribution(
        per_ifg=per_ifg_records,
        aggregate=RampAggregate(**agg_dict),
        attributed_source=attributed_source,
        attribution_note="Automated; human review pending in CONCLUSIONS",
    )

    # --- Phase 4 Stage 12: write metrics.json + meta.json --------------------
    print(
        "\n  [Phase 4 Stage 12] Writing eval-disp-egms/metrics.json + "
        "meta.json..."
    )
    import hashlib as _hash
    import platform as _platform
    import subprocess as _sp
    import sys as _sys
    import time as _time

    OUT_DIR = _PhasePath("eval-disp-egms")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    def _coh(*keys, default=float("nan")):  # noqa: ANN001, ANN002, ANN202
        for k in keys:
            if k in coh_stats:
                return float(coh_stats[k])
        return float(default)

    pq = DISPProductQualityResultJson(
        measurements={
            "coherence_median_of_persistent": _coh(
                "coherence_median_of_persistent", "median_of_persistent"
            ),
            "residual_mm_yr": float(residual),
            "coherence_mean": _coh("coherence_mean", "mean"),
            "coherence_median": _coh("coherence_median", "median"),
            "coherence_p25": _coh("coherence_p25", "p25"),
            "coherence_p75": _coh("coherence_p75", "p75"),
            "persistently_coherent_fraction": _coh(
                "persistently_coherent_fraction"
            ),
        },
        criterion_ids=[
            "disp.selfconsistency.coherence_min",
            "disp.selfconsistency.residual_mm_yr_max",
        ],
        coherence_source=coherence_source,
    )
    # W3 -- explicit references to the canonical names assigned in Stage 9
    # (correlation, bias, rmse, sample_count). NO dir() introspection. If any
    # name is undefined here, NameError surfaces loudly.
    ra = ReferenceAgreementResultJson(
        measurements={
            "correlation": correlation,
            "bias_mm_yr": bias,
            "rmse_mm_yr": rmse,
            "sample_count": float(sample_count),
        },
        criterion_ids=["disp.correlation_min", "disp.bias_mm_yr_max"],
    )

    dem_diagnostics = summarize_dem(dem_path)
    terrain_diagnostics = summarize_terrain(dem_path, stable_mask, None)

    orbit_by_sensing: dict[str, tuple[Path, datetime, str]] = {
        sensing.isoformat(): (path, sensing, mode)
        for path, sensing, mode in tracked_orbits
    }
    cached_orbit_paths = sorted(orbit_dir.glob("*.EOF"))
    for sensing in successful_sensing_times:
        key = sensing.isoformat()
        if key in orbit_by_sensing:
            continue
        for candidate in cached_orbit_paths:
            coverage = summarize_orbit_coverage(candidate, sensing)
            if coverage.covers_sensing_time is True:
                orbit_by_sensing[key] = (candidate, sensing, "reused")
                break
        if key not in orbit_by_sensing:
            orbit_by_sensing[key] = (Path(""), sensing, "reused")
    orbit_provenance = [
        summarize_orbit_coverage(path, sensing)
        for path, sensing, _mode in orbit_by_sensing.values()
    ]

    cache_provenance_records = [
        cache_provenance("dem", dem_path, dem_cache_mode),
        *[
            cache_provenance(name, path, mode)
            for name, path, mode in slc_cache_inputs
        ],
        *[
            cache_provenance(name, path, mode)
            for name, path, mode in cslc_cache_inputs
        ],
        *[
            cache_provenance(f"orbit_{sensing:%Y%m%d}", path, mode)
            for path, sensing, mode in orbit_by_sensing.values()
            if path.name
        ],
        cache_provenance("velocity_tif", velocity_path, velocity_cache_mode),
    ]

    # ── Stage 11: SPURT native candidate (Phase 11 D-01, D-02, D-04) ──────────
    # SPURT is executed BEFORE PHASS deramping per D-04.
    # Outputs are isolated under OUT_DIR/candidates/spurt_native (T-11-01-03).
    # No ERA5 axis (D-13). No tophu/SNAPHU fallback (D-14).
    print("\n-- Stage 11: SPURT native candidate --")
    candidate_outcomes: list[DISPCandidateOutcome] = []

    spurt_candidate_dir = candidate_output_dir(OUT_DIR, "spurt_native")
    spurt_candidate_dir.mkdir(parents=True, exist_ok=True)
    spurt_log_path = spurt_candidate_dir / "candidate.log"

    try:
        spurt_result = run_disp(
            cslc_paths=sorted_h5,
            output_dir=spurt_candidate_dir,
            era5_mode="off",
            unwrap_method="spurt",
            threads_per_worker=8,
            n_parallel_bursts=2,
            block_shape=(512, 512),
            n_parallel_unwrap=8,
        )
        print(f"  SPURT result valid: {spurt_result.valid}")
        print(f"  SPURT velocity: {spurt_result.velocity_path}")

        spurt_velocity_path = spurt_result.velocity_path
        if spurt_velocity_path is not None and spurt_velocity_path.exists():
            # Compare SPURT velocity against EGMS L2a PS reference (T-11-02-03)
            spurt_corr: float | None = None
            spurt_bias: float | None = None
            spurt_rmse: float | None = None
            spurt_ramp_mean: float | None = None
            spurt_ramp_dir_sigma: float | None = None
            spurt_attributed: str | None = None

            try:
                from subsideo.validation.compare_disp import prepare_for_reference
                from subsideo.validation.metrics import (
                    bias as _bias_fn,
                    rmse as _rmse_fn,
                )
                import numpy as _np_spurt

                spurt_at_ps = prepare_for_reference(
                    native_velocity=spurt_velocity_path,
                    reference_grid=egms_spec,
                    method=REFERENCE_MULTILOOK_METHOD,
                )
                SENTINEL1_WAVELENGTH_M_SPURT = 0.05546576
                spurt_at_ps_mm_yr = (
                    -spurt_at_ps * SENTINEL1_WAVELENGTH_M_SPURT / (4.0 * _np_spurt.pi) * 1000.0
                )
                _ref_ps = egms_df["mean_velocity"].values.astype(_np_spurt.float64)
                _valid_spurt = _np_spurt.isfinite(spurt_at_ps_mm_yr) & _np_spurt.isfinite(_ref_ps)
                n_valid_spurt = int(_valid_spurt.sum())

                if n_valid_spurt >= 100:
                    spurt_corr = float(
                        _np_spurt.corrcoef(spurt_at_ps_mm_yr[_valid_spurt], _ref_ps[_valid_spurt])[0, 1]
                    )
                    spurt_bias = float(
                        _bias_fn(spurt_at_ps_mm_yr[_valid_spurt], _ref_ps[_valid_spurt])
                    )
                    spurt_rmse = float(
                        _rmse_fn(spurt_at_ps_mm_yr[_valid_spurt], _ref_ps[_valid_spurt])
                    )
                    print(
                        f"  SPURT vs EGMS L2a: r={spurt_corr:.4f}  "
                        f"bias={spurt_bias:+.2f} mm/yr  "
                        f"RMSE={spurt_rmse:.2f} mm/yr  N={n_valid_spurt:,}"
                    )
                else:
                    print(f"  SPURT: insufficient valid PS pairs ({n_valid_spurt}) for comparison")

            except Exception as exc_compare:
                print(f"  SPURT comparison failed: {type(exc_compare).__name__}: {exc_compare}")
                spurt_log_path.write_text(f"comparison error: {exc_compare}\n")

            # Compute SPURT ramp attribution
            try:
                from subsideo.validation.selfconsistency import (
                    auto_attribute_ramp,
                    compute_ramp_aggregate,
                    fit_planar_ramp,
                )
                import rasterio as _rio_spurt2
                spurt_unw_dir = spurt_candidate_dir / "dolphin" / "unwrapped"
                spurt_unw_files = sorted(spurt_unw_dir.glob("*.unw.tif")) if spurt_unw_dir.exists() else []
                if spurt_unw_files:
                    # CR-01: build 3-D stack (N, H, W) before calling fit_planar_ramp
                    # CR-03: collect per-IFG coherence means in the same loop
                    spurt_phase_list = []
                    spurt_coh_means_list: list[float] = []
                    _spurt_cor_dir = spurt_candidate_dir / "dolphin" / "interferograms"
                    for _unw_f in spurt_unw_files[:14]:
                        with _rio_spurt2.open(_unw_f) as _ds:
                            spurt_phase_list.append(_ds.read(1).astype(np.float32))
                        _cor_f = _spurt_cor_dir / _unw_f.name.replace(".unw.tif", ".int.cor.tif")
                        if _cor_f.exists():
                            with _rio_spurt2.open(_cor_f) as _ds:
                                _cor = _ds.read(1).astype(np.float64)
                            _vc = np.isfinite(_cor) & (_cor > 0)
                            spurt_coh_means_list.append(float(_cor[_vc].mean()) if _vc.any() else float("nan"))
                        else:
                            spurt_coh_means_list.append(float("nan"))
                    if spurt_phase_list:
                        # CR-01 fix: pass 3-D stack to fit_planar_ramp
                        spurt_stack = np.stack(spurt_phase_list, axis=0)  # (N, H, W)
                        _fit_dict = fit_planar_ramp(spurt_stack, mask=None)
                        # CR-03 fix: build coherence array parallel to phase list
                        spurt_coh_arr = np.array(spurt_coh_means_list, dtype=np.float64)
                        _spurt_ramp_agg = compute_ramp_aggregate(_fit_dict, spurt_coh_arr)
                        # CR-02 fix: access result via dict keys (not attributes)
                        spurt_ramp_mean = float(_spurt_ramp_agg["mean_magnitude_rad"])
                        spurt_ramp_dir_sigma = float(_spurt_ramp_agg["direction_stability_sigma_deg"])
                        # CR-04 fix: call auto_attribute_ramp with keyword args
                        _spurt_attr = auto_attribute_ramp(
                            direction_stability_sigma_deg=_spurt_ramp_agg["direction_stability_sigma_deg"],
                            magnitude_vs_coherence_pearson_r=_spurt_ramp_agg["magnitude_vs_coherence_pearson_r"],
                        )
                        spurt_attributed = _spurt_attr
                        print(f"  SPURT ramp: mean={spurt_ramp_mean:.3f} rad  sigma={spurt_ramp_dir_sigma:.1f} deg  attr={spurt_attributed}")
            except Exception as exc_ramp:
                # WR-01: surface the exception type; re-raise programming errors
                spurt_log_path.write_text(
                    f"ramp_attribution error: {type(exc_ramp).__name__}: {exc_ramp}\n"
                )
                print(f"  SPURT ramp attribution failed: {type(exc_ramp).__name__}: {exc_ramp}")
                if isinstance(exc_ramp, (TypeError, ValueError, AttributeError)):
                    raise

            spurt_status = candidate_status_from_metrics(
                "spurt_native",
                correlation=spurt_corr,
                bias_mm_yr=spurt_bias,
                ramp_mean_magnitude_rad=spurt_ramp_mean,
                attributed_source=spurt_attributed,  # type: ignore[arg-type]
            )
            print(f"  SPURT candidate status: {spurt_status}")
            candidate_outcomes.append(
                DISPCandidateOutcome(
                    candidate="spurt_native",
                    cell="bologna",
                    status=spurt_status,
                    cached_input_valid=True,
                    reference_correlation=spurt_corr,
                    reference_bias_mm_yr=spurt_bias,
                    reference_rmse_mm_yr=spurt_rmse,
                    ramp_mean_magnitude_rad=spurt_ramp_mean,
                    ramp_direction_sigma_deg=spurt_ramp_dir_sigma,
                    attributed_source=spurt_attributed,  # type: ignore[arg-type]
                    partial_metrics=False,
                )
            )
        else:
            print("  SPURT produced no velocity.tif -- recording BLOCKER")
            candidate_outcomes.append(
                make_candidate_blocker(
                    candidate="spurt_native",
                    cell="bologna",
                    failed_stage="spurt_unwrap_or_timeseries",
                    error_summary=(
                        f"run_disp returned no velocity_path. "
                        f"valid={spurt_result.valid} "
                        f"errors={spurt_result.validation_errors}"
                    ),
                    evidence_paths=[str(spurt_log_path)],
                    cached_input_valid=True,
                    partial_metrics=False,
                )
            )
    except Exception as exc_spurt:
        print(f"  SPURT candidate FAILED: {type(exc_spurt).__name__}: {exc_spurt}")
        spurt_log_path.write_text(f"{type(exc_spurt).__name__}: {exc_spurt}\n")
        candidate_outcomes.append(
            make_candidate_blocker(
                candidate="spurt_native",
                cell="bologna",
                failed_stage="spurt_unwrap_or_timeseries",
                error_summary=f"{type(exc_spurt).__name__}: {exc_spurt}",
                evidence_paths=[str(spurt_log_path)],
                cached_input_valid=True,
                partial_metrics=False,
            )
        )

    # ── Stage 12 (pre): PHASS post-deramp candidate (Phase 11 D-01, D-02, D-03, D-04, D-05) ──
    # PHASS post-deramping is the second candidate after SPURT (D-04 ordering).
    # Bologna cell: include DISPDeformationSanityCheck when values are available (D-07).
    # A flagged sanity check blocks Phase 12 recommendation but NOT Phase 11 reporting (D-08).
    print("\n-- Stage 12 (pre): PHASS post-deramp candidate (Bologna) --")
    from subsideo.validation.matrix_schema import DISPDeformationSanityCheck
    from subsideo.validation.selfconsistency import write_deramped_unwrapped_ifgs as _write_deramped

    phass_deramp_dir = candidate_output_dir(OUT_DIR, "phass_post_deramp")
    phass_deramp_dir.mkdir(parents=True, exist_ok=True)
    phass_deramp_log = phass_deramp_dir / "candidate.log"

    # Read baseline PHASS unwrapped IFGs (from same disp_dir as Stage 11)
    _phass_unw_dir = disp_dir / "dolphin" / "unwrapped"
    _phass_unw_files = sorted(_phass_unw_dir.glob("*.unw.tif")) if _phass_unw_dir.exists() else []
    print(f"  PHASS baseline unwrapped IFGs: {len(_phass_unw_files)}")

    # Step 1: Write deramped IFGs (D-05 IFG-level deramping; T-11-03-01 isolation)
    _deramped_dir = phass_deramp_dir / "deramped_unwrapped"
    _phass_deramped_paths: list[_PhasePath] = []
    _phass_ramp_data: dict = {}
    try:
        if _phass_unw_files:
            _phass_deramped_paths, _phass_ramp_data = _write_deramped(
                _phass_unw_files, _deramped_dir
            )
            print(f"  Deramped IFGs written: {len(_phass_deramped_paths)} -> {_deramped_dir}")
        else:
            print("  No baseline unwrapped IFGs found for PHASS deramping -- skipping write")
    except Exception as exc_deramp:
        print(f"  PHASS deramping write failed: {exc_deramp}")
        phass_deramp_log.write_text(f"write_deramped_unwrapped_ifgs error: {exc_deramp}\n")

    # Step 2: Compute deformation-signal sanity check for Bologna (D-07: include when values available)
    _sanity_trend_delta: float | None = None
    _sanity_direction_change: float | None = None
    _sanity_stable_residual_delta: float | None = None
    _sanity_flagged = False
    _sanity_flag_reason = ""
    _bologna_sanity: "DISPDeformationSanityCheck | None" = None
    try:
        if _phass_ramp_data and "slope_x" in _phass_ramp_data:
            import numpy as _np_sanity_b
            _sx = _phass_ramp_data["slope_x"]
            _sy = _phass_ramp_data["slope_y"]
            _LAMBDA = 0.05546576
            _BASELINES_PER_YEAR = 365.25 / 12.0
            _finite_sx = _sx[_np_sanity_b.isfinite(_sx)]
            _finite_sy = _sy[_np_sanity_b.isfinite(_sy)]
            if len(_finite_sx) > 0:
                _H, _W = 512, 512
                _mean_ramp_vel_rad_yr = (
                    float(_np_sanity_b.abs(_finite_sx).mean()) * _W
                    + float(_np_sanity_b.abs(_finite_sy).mean()) * _H
                ) * _BASELINES_PER_YEAR
                _sanity_trend_delta = (
                    -_mean_ramp_vel_rad_yr * _LAMBDA / (4.0 * _np_sanity_b.pi) * 1000.0
                )
                _sanity_stable_residual_delta = float(
                    _np_sanity_b.abs(_finite_sx).mean() * _W * _BASELINES_PER_YEAR
                    * _LAMBDA / (4.0 * _np_sanity_b.pi) * 1000.0
                )
                _dir_rad = _phass_ramp_data.get("ramp_direction_deg", _np_sanity_b.zeros(1))
                _finite_dir = _dir_rad[_np_sanity_b.isfinite(_dir_rad)]
                _sanity_direction_change = float(_np_sanity_b.std(_finite_dir)) if len(_finite_dir) > 1 else None
                if abs(_sanity_trend_delta) > 3.0:
                    _sanity_flagged = True
                    _sanity_flag_reason += f"trend_delta {_sanity_trend_delta:+.2f} mm/yr > 3.0; "
                if abs(_sanity_stable_residual_delta) > 2.0:
                    _sanity_flagged = True
                    _sanity_flag_reason += f"stable_residual_delta {_sanity_stable_residual_delta:+.2f} mm/yr > 2.0; "
                # Bologna: include sanity check when values are available (D-07)
                _bologna_sanity = DISPDeformationSanityCheck(
                    cell="bologna",
                    trend_delta_mm_yr=_sanity_trend_delta,
                    direction_change_deg=_sanity_direction_change,
                    stable_residual_delta_mm_yr=_sanity_stable_residual_delta,
                    flagged=_sanity_flagged,
                    flag_reason=_sanity_flag_reason.strip(),
                )
                if _sanity_flagged:
                    print(f"  WARN (D-08): deformation sanity flagged -- {_sanity_flag_reason.strip()}")
    except Exception as exc_sanity:
        print(f"  Sanity check computation failed: {exc_sanity}")
        # Leave _bologna_sanity = None (D-07: include only when values are available)

    # Step 3: Run MintPy-style SBAS inversion on the deramped IFGs.
    from subsideo.validation.selfconsistency import run_phass_sbas_inversion as _run_phass_sbas

    _phass_sbas_dir = phass_deramp_dir / "sbas_inversion"
    _phass_sbas_dir.mkdir(parents=True, exist_ok=True)
    _phass_vel_path: _PhasePath | None = None
    try:
        if _phass_deramped_paths:
            _phass_vel_path, _phass_dates, _ = _run_phass_sbas(
                _phass_deramped_paths, _phass_sbas_dir
            )
            print(f"  PHASS SBAS velocity written: {_phass_vel_path}")
        else:
            print("  PHASS SBAS: no deramped IFGs available -- skipping inversion")
    except Exception as exc_sbas:
        phass_deramp_log.write_text(
            f"sbas_inversion error: {type(exc_sbas).__name__}: {exc_sbas}\n"
        )
        print(f"  PHASS SBAS inversion failed: {exc_sbas}")
        _phass_vel_path = None

    # Compare PHASS SBAS velocity against EGMS L2a reference (same as baseline)
    _phass_corr: float | None = None
    _phass_bias: float | None = None
    _phass_rmse: float | None = None
    _phass_ramp_mean: float | None = None
    _phass_ramp_dir_sigma: float | None = None
    _phass_attributed: str | None = None

    if _phass_vel_path is not None and _phass_vel_path.exists():
        try:
            import rasterio as _rio_phass
            import numpy as _np_phass
            from subsideo.validation.compare_disp import (
                ReferenceGridSpec as _RGS,
                prepare_for_reference as _prep_ref,
            )
            from subsideo.validation.metrics import (
                bias as _bias_phass,
                rmse as _rmse_phass,
            )

            # PHASS SBAS velocity is already in mm/yr
            _phass_at_ps = _prep_ref(
                native_velocity=_phass_vel_path,
                reference_grid=egms_spec,
                method=REFERENCE_MULTILOOK_METHOD,
            )
            _phass_arr = _np_phass.asarray(_phass_at_ps).astype(float)
            _ref_phass_mm = egms_df["mean_velocity"].values.astype(_np_phass.float64)
            _valid_phass = _np_phass.isfinite(_phass_arr) & _np_phass.isfinite(_ref_phass_mm)
            n_valid_phass = int(_valid_phass.sum())
            if n_valid_phass >= 100:
                _phass_corr = float(
                    _np_phass.corrcoef(_phass_arr[_valid_phass], _ref_phass_mm[_valid_phass])[0, 1]
                )
                _phass_bias = float(_bias_phass(_phass_arr[_valid_phass], _ref_phass_mm[_valid_phass]))
                _phass_rmse = float(_rmse_phass(_phass_arr[_valid_phass], _ref_phass_mm[_valid_phass]))
                print(
                    f"  PHASS SBAS vs EGMS L2a: r={_phass_corr:.4f}  "
                    f"bias={_phass_bias:+.2f} mm/yr  RMSE={_phass_rmse:.2f} mm/yr  N={n_valid_phass:,}"
                )
            else:
                print(f"  PHASS SBAS: insufficient valid PS pairs ({n_valid_phass}) for comparison")

            # Ramp attribution on deramped IFGs
            from subsideo.validation.selfconsistency import (
                auto_attribute_ramp as _auto_attr_phass,
                compute_ramp_aggregate as _ramp_agg_phass,
                fit_planar_ramp as _fit_ramp_phass,
            )
            if _phass_deramped_paths:
                _phass_phase_list = []
                _phass_coh_list: list[float] = []
                _phass_cor_dir = disp_dir / "dolphin" / "interferograms"
                for _dp in _phass_deramped_paths[:14]:
                    with _rio_phass.open(_dp) as _ds:
                        _phass_phase_list.append(_ds.read(1).astype(_np_phass.float32))
                    _phass_cor_f = _phass_cor_dir / _dp.name.replace(".unw.deramped.tif", ".int.cor.tif")
                    if _phass_cor_f.exists():
                        with _rio_phass.open(_phass_cor_f) as _ds:
                            _cor = _ds.read(1).astype(_np_phass.float64)
                        _vc = _np_phass.isfinite(_cor) & (_cor > 0)
                        _phass_coh_list.append(float(_cor[_vc].mean()) if _vc.any() else float("nan"))
                    else:
                        _phass_coh_list.append(float("nan"))
                if _phass_phase_list:
                    _phass_stk = _np_phass.stack(_phass_phase_list, axis=0)
                    _phass_fd = _fit_ramp_phass(_phass_stk, mask=None)
                    _phass_ca = _np_phass.array(_phass_coh_list, dtype=_np_phass.float64)
                    _phass_agg = _ramp_agg_phass(_phass_fd, _phass_ca)
                    _phass_ramp_mean = float(_phass_agg["mean_magnitude_rad"])
                    _phass_ramp_dir_sigma = float(_phass_agg["direction_stability_sigma_deg"])
                    _phass_attributed = _auto_attr_phass(
                        direction_stability_sigma_deg=_phass_agg["direction_stability_sigma_deg"],
                        magnitude_vs_coherence_pearson_r=_phass_agg["magnitude_vs_coherence_pearson_r"],
                    )
                    print(f"  PHASS ramp: mean={_phass_ramp_mean:.3f} rad  sigma={_phass_ramp_dir_sigma:.1f} deg  attr={_phass_attributed}")
        except Exception as exc_phass_cmp:
            phass_deramp_log.write_text(
                f"comparison error: {type(exc_phass_cmp).__name__}: {exc_phass_cmp}\n"
            )
            print(f"  PHASS comparison failed: {type(exc_phass_cmp).__name__}: {exc_phass_cmp}")

        _phass_status = candidate_status_from_metrics(
            "phass_post_deramp",
            correlation=_phass_corr,
            bias_mm_yr=_phass_bias,
            ramp_mean_magnitude_rad=_phass_ramp_mean,
            attributed_source=_phass_attributed,  # type: ignore[arg-type]
        )
        print(f"  PHASS post-deramp candidate status (Bologna): {_phass_status}")
        _phass_outcome = DISPCandidateOutcome(
            candidate="phass_post_deramp",
            cell="bologna",
            status=_phass_status,
            cached_input_valid=True,
            reference_correlation=_phass_corr,
            reference_bias_mm_yr=_phass_bias,
            reference_rmse_mm_yr=_phass_rmse,
            ramp_mean_magnitude_rad=_phass_ramp_mean,
            ramp_direction_sigma_deg=_phass_ramp_dir_sigma,
            attributed_source=_phass_attributed,  # type: ignore[arg-type]
            partial_metrics=False,
            deformation_sanity=_bologna_sanity,
        )
        candidate_outcomes.append(_phass_outcome)
    else:
        # SBAS inversion failed or no deramped paths -- fall back to BLOCKER
        _phass_blocker = make_candidate_blocker(
            candidate="phass_post_deramp",
            cell="bologna",
            failed_stage="sbas_inversion",
            error_summary=(
                "PHASS SBAS inversion failed or no deramped IFGs available. "
                "Partial evidence preserved in deramped_unwrapped/."
            ),
            evidence_paths=[str(_deramped_dir)],
            cached_input_valid=True,
            partial_metrics=True,
        )
        _phass_blocker_final = _phass_blocker.model_copy(
            update={"deformation_sanity": _bologna_sanity}
        )
        candidate_outcomes.append(_phass_blocker_final)
        print("  PHASS post-deramp (Bologna): BLOCKER (sbas_inversion)")
    print(f"  Deformation sanity included: {_bologna_sanity is not None}")

    # ── Stage 12: Metrics serialisation ─────────────────────────────────────
    metrics = DISPCellMetrics(
        schema_version=1,
        product_quality=pq,
        reference_agreement=ra,
        ramp_attribution=ramp_attribution_obj,
        era5_diagnostic=Era5Diagnostic(mode=ERA5_MODE),
        terrain_diagnostics=terrain_diagnostics,
        orbit_provenance=orbit_provenance,
        dem_diagnostics=dem_diagnostics,
        cache_provenance=cache_provenance_records,
        cell_status=cell_status,
        candidate_outcomes=candidate_outcomes,
        criterion_ids_applied=[
            "disp.selfconsistency.coherence_min",
            "disp.selfconsistency.residual_mm_yr_max",
            "disp.correlation_min",
            "disp.bias_mm_yr_max",
        ],
        runtime_conda_list_hash=None,
    )
    (OUT_DIR / "metrics.json").write_text(metrics.model_dump_json(indent=2))
    print(f"  Wrote {OUT_DIR / 'metrics.json'}")

    try:
        git_sha = _sp.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
        git_dirty = bool(
            _sp.check_output(["git", "status", "--porcelain"], text=True).strip()
        )
    except Exception:
        git_sha, git_dirty = "unknown", False

    def _sha256_file(p: Path) -> str:
        h = _hash.sha256()
        with open(p, "rb") as fh:
            for block in iter(lambda: fh.read(65536), b""):
                h.update(block)
        return h.hexdigest()

    input_hashes = {"velocity_tif": _sha256_file(velocity_path)}
    if phase3_metrics_path.exists():
        input_hashes["phase3_cslc_metrics"] = _sha256_file(phase3_metrics_path)

    meta = MetaJson(
        schema_version=1,
        git_sha=git_sha,
        git_dirty=git_dirty,
        run_started_iso=run_start_iso,
        run_duration_s=_time.monotonic() - t_start,
        python_version=_sys.version.split()[0],
        platform=_platform.platform(),
        input_hashes=input_hashes,
    )
    (OUT_DIR / "meta.json").write_text(meta.model_dump_json(indent=2))
    print(f"  Wrote {OUT_DIR / 'meta.json'}")

    print("\n" + "=" * 70)
    print(f"eval-disp-egms (Bologna): cell_status={cell_status}")
    coh_med_disp = coh_stats.get(
        "coherence_median_of_persistent",
        coh_stats.get("median_of_persistent", float("nan")),
    )
    print(
        f"  PQ: coh_med_of_persistent={coh_med_disp:.3f} "
        f"(coherence_source={coherence_source}) / "
        f"residual={residual:+.2f} mm/yr (CALIBRATING)"
    )
    print(
        f"  RA: r={correlation:.3f} (>0.92 BINDING) / "
        f"bias={bias:+.2f} mm/yr (<3.0 BINDING)"
    )
    print(
        f"  Ramp: attr={attributed_source}, "
        f"mean_mag={agg_dict['mean_magnitude_rad']:.2f} rad"
    )
    print("=" * 70)
