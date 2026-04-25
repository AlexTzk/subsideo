# run_eval_disp.py — N.Am. DISP-S1 validation against OPERA
#
# Downloads a 6-month stack of S1 IW SLC scenes from ASF DAAC, builds
# a CSLC-S1 stack using compass, runs the full DISP pipeline
# (dolphin + tophu + MintPy with ERA5 tropospheric correction), and
# compares the resulting velocity field against OPERA DISP-S1 reference.
#
# Prerequisites:
#   - EARTHDATA_USERNAME / EARTHDATA_PASSWORD in .env or env vars
#   - ~/.cdsapirc with valid CDS API credentials (ERA5 correction)
#   - conda env: isce3, compass, dolphin, tophu, snaphu, mintpy
#
# Storage estimate: ~130 GB (15 SLCs x ~8 GB + CSLC/DISP outputs)
# Compute estimate: 3-6 hours depending on hardware
#
# Resume-safe: each stage skips work if outputs already exist.
import warnings; warnings.filterwarnings("ignore")  # noqa: E702, I001

from typing import Literal  # noqa: E402

# Phase 4 D-Claude's-Discretion: 6h cap (warm re-run + ramp fit + adapter ~30 min/cell;
# cold full-pipeline ~3 h/cell + safety margin). 21600s expressed as 60*60*6 because
# supervisor AST-parser whitelists nested BinOp of literal Constants (Plan 01-07 T-07-06).
EXPECTED_WALL_S = 60 * 60 * 6   # 21600 -- Plan 01-07 supervisor AST-parses this
REFERENCE_MULTILOOK_METHOD: Literal["block_mean"] = "block_mean"  # Phase 4 D-04


def _reproject_mask_to_grid(
    mask: "object",  # numpy ndarray; use object to satisfy ruff ANN401
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
    from datetime import datetime
    from pathlib import Path

    import asf_search as asf
    import earthaccess
    import h5py
    import numpy as np
    from dotenv import load_dotenv

    from subsideo.data.dem import fetch_dem
    from subsideo.data.orbits import fetch_orbit
    from subsideo.products.cslc import run_cslc
    from subsideo.products.disp import run_disp
    from subsideo.validation.harness import (
        bounds_for_burst,
        credential_preflight,
    )

    load_dotenv()

    credential_preflight([
        "CDSE_CLIENT_ID", "CDSE_CLIENT_SECRET",
        "EARTHDATA_USERNAME", "EARTHDATA_PASSWORD",
    ])

    # Phase 4 Stage 12 prerequisite: wall-time + run-start tracking for meta.json
    t_start = time.monotonic()
    run_start_iso = datetime.utcnow().isoformat() + "Z"

    # ── Configuration ────────────────────────────────────────────────────────
    BURST_ID = "t144_308029_iw1"
    RELATIVE_ORBIT = 144

    # 6-month window: ~15 S1A repeat-pass acquisitions at 12-day interval
    DATE_START = "2024-01-01"
    DATE_END   = "2024-06-30"

    # Burst footprint via harness.bounds_for_burst (ENV-08 — no hand-coded
    # numeric bounds literal). BURST_BBOX is derived unbuffered for STAC /
    # asf-search WKT queries; DEM fetch uses a wider buffered tuple.
    BURST_BBOX = bounds_for_burst(BURST_ID, buffer_deg=0.0)
    EPSG = 32611  # UTM 11N

    OUT = Path("./eval-disp")
    OUT.mkdir(exist_ok=True)

    print("=" * 70)
    print("DISP-S1 Validation: subsideo vs OPERA N.Am. Reference")
    print("=" * 70)
    print(f"  Burst      : {BURST_ID}")
    print(f"  Rel. orbit : {RELATIVE_ORBIT}")
    print(f"  Period     : {DATE_START} -> {DATE_END}")
    print(f"  Output dir : {OUT}")

    # ── Pre-flight checks ────────────────────────────────────────────────────
    cdsapirc = Path.home() / ".cdsapirc"
    if not cdsapirc.exists():
        raise SystemExit(
            "~/.cdsapirc not found. ERA5 tropospheric correction requires "
            "CDS API credentials.\nRegister at https://cds.climate.copernicus.eu/"
        )
    print(f"  CDS API    : {cdsapirc}")
    print()

    # ── Stage 1: Authenticate ────────────────────────────────────────────────
    print("-- Stage 1: Authentication --")
    auth = earthaccess.login(strategy="environment")
    print("  Earthdata auth OK")

    session = asf.ASFSession().auth_with_creds(
        username=os.environ["EARTHDATA_USERNAME"],
        password=os.environ["EARTHDATA_PASSWORD"],
    )
    print("  ASF session OK")

    # ── Stage 2: Search for OPERA DISP-S1 reference ──────────────────────────
    # OPERA DISP-S1 products are cloud-native Zarr stores (not downloadable
    # HDF5 like RTC/CSLC).  We search now and open remotely in Stage 9.
    print("\n-- Stage 2: OPERA DISP-S1 Reference --")
    ref_dir = OUT / "opera_reference"
    ref_dir.mkdir(exist_ok=True)

    w, s, e, n = BURST_BBOX
    opera_disp_results = None
    print("  Searching for OPERA DISP-S1 products...")
    try:
        opera_disp_results = earthaccess.search_data(
            short_name="OPERA_L3_DISP-S1_V1",
            temporal=(DATE_START, DATE_END),
            bounding_box=(w, s, e, n),
        )
    except Exception as e:
        print(f"  Search error: {e}")

    if opera_disp_results:
        # OPERA DISP frames cover different orbits and times.  Our burst
        # t144_308029_iw1 is on relative orbit 144 (ascending) with sensing
        # time ~14:01 UTC.  Filter frames by the time portion of the reference
        # date to match this orbit pass — descending frames with ~01:50 UTC
        # references will produce zero correlation.
        BURST_HOUR = 14  # our burst's UTC hour

        frame_counts: dict[str, int] = {}
        frame_hours: dict[str, int] = {}
        for r in opera_disp_results:
            name = r["umm"].get("GranuleUR", "")
            parts = name.split("_")
            frame = next((p for p in parts if p.startswith("F")), None)
            # Ref time format: ...F38503_VV_20230805T140045Z_...
            import re as _re
            m = _re.search(r"_(\d{8})T(\d{6})Z_", name)
            hour = int(m.group(2)[:2]) if m else -1
            if frame:
                frame_counts[frame] = frame_counts.get(frame, 0) + 1
                frame_hours[frame] = hour

        print(f"  Found {len(opera_disp_results)} product(s):")
        for f in sorted(frame_counts):
            print(f"    {f}: {frame_counts[f]} products, acquisition hour ~{frame_hours[f]:02d} UTC")  # noqa: E501

        # Prefer exact UTC hour match, fall back to ±1 hour.  Frame numbers
        # differ by 1 within a single orbit pass, so exact hour match is the
        # strongest filter to ensure the frame covers our burst footprint.
        exact_frames = [f for f, h in frame_hours.items() if h == BURST_HOUR]
        if exact_frames:
            matching_frames = exact_frames
            print(f"  Exact UTC {BURST_HOUR} match: {exact_frames}")
        else:
            matching_frames = [f for f, h in frame_hours.items() if abs(h - BURST_HOUR) <= 1]
            print(f"  No exact match; using ±1h: {matching_frames}")

        if not matching_frames:
            print(f"  WARNING: No frames matching UTC hour ~{BURST_HOUR}")
            print("  Falling back to all frames -- correlation may fail")
            matching_frames = list(frame_counts.keys())

        # Among matching frames, pick the one with most products
        target_frame = max(matching_frames, key=lambda f: frame_counts[f])
        opera_disp_results = [
            r for r in opera_disp_results
            if target_frame in r["umm"].get("GranuleUR", "")
        ]
        print(f"  Using frame {target_frame} (UTC {frame_hours[target_frame]:02d}): {len(opera_disp_results)} product(s)")  # noqa: E501
        for r in opera_disp_results[:5]:
            print(f"    {r['umm'].get('GranuleUR', '?')}")
        if len(opera_disp_results) > 5:
            print(f"    ... and {len(opera_disp_results) - 5} more")
    else:
        print("  WARNING: No OPERA DISP-S1 products found on Earthdata.")
        print("  Pipeline will run anyway -- comparison deferred.")

    # ── Stage 3: Search ASF for S1 SLCs ──────────────────────────────────────
    print("\n-- Stage 3: Search S1 SLC scenes --")
    w, s, e, n = BURST_BBOX
    aoi_wkt = f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"
    slc_results = asf.search(
        platform=asf.PLATFORM.SENTINEL1,
        processingLevel="SLC",
        beamMode="IW",
        relativeOrbit=RELATIVE_ORBIT,
        intersectsWith=aoi_wkt,
        start=f"{DATE_START}T00:00:00Z",
        end=f"{DATE_END}T23:59:59Z",
        maxResults=100,
    )

    # Filter to dual-pol SDV only (skip SSH single-pol)
    slc_results = [r for r in slc_results if "SDV" in r.properties["fileID"]]

    # Deduplicate by date: pick the SLC whose time range best contains
    # the burst sensing time (~14:01:16 UTC).  The later segment (start
    # ~14:01:13) fully covers the burst; the earlier one (~14:00:49) has
    # the burst at its very edge and fails compass processing.
    BURST_UTC_SECONDS = 14 * 3600 + 1 * 60 + 16  # 14:01:16

    by_date: dict[str, object] = {}
    for r in slc_results:
        date_key = r.properties["startTime"][:10]  # YYYY-MM-DD
        start_dt = datetime.fromisoformat(r.properties["startTime"][:19])
        stop_dt = datetime.fromisoformat(r.properties.get("stopTime", r.properties["startTime"])[:19])  # noqa: E501
        start_sec = start_dt.hour * 3600 + start_dt.minute * 60 + start_dt.second
        stop_sec = stop_dt.hour * 3600 + stop_dt.minute * 60 + stop_dt.second
        contains_burst = start_sec <= BURST_UTC_SECONDS <= stop_sec
        margin = min(BURST_UTC_SECONDS - start_sec, stop_sec - BURST_UTC_SECONDS) if contains_burst else -1  # noqa: E501

        if date_key not in by_date:
            by_date[date_key] = (r, contains_burst, margin)
        else:
            _, prev_contains, prev_margin = by_date[date_key]
            # Prefer the SLC that contains the burst; tie-break by margin
            if (contains_burst and not prev_contains) or \
               (contains_burst and prev_contains and margin > prev_margin):
                by_date[date_key] = (r, contains_burst, margin)

    slc_results = sorted([r for r, _, _ in by_date.values()], key=lambda r: r.properties["startTime"])  # noqa: E501
    print(f"  Found {len(slc_results)} unique SLC date(s) on orbit {RELATIVE_ORBIT}")
    for i, r in enumerate(slc_results):
        print(f"    [{i+1:2d}] {r.properties['startTime'][:19]}  {r.properties['fileID'][:55]}")  # noqa: E501

    if not slc_results:
        raise SystemExit("No S1 SLC scenes found -- check date range and orbit number.")

    # ── Stage 4: Download DEM ────────────────────────────────────────────────
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
        from opera_utils.burst_frame_db import get_burst_id_geojson
        from pyproj import Transformer

        geojson = get_burst_id_geojson(BURST_ID)
        feat = geojson["features"][0]
        coords = feat["geometry"]["coordinates"][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        t = Transformer.from_crs(4326, EPSG, always_xy=True)
        xs, ys = t.transform(lons, lats)
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
    print(f"  Processing {len(slc_results)} scenes into single-burst CSLCs...")
    input_dir = OUT / "input"
    input_dir.mkdir(exist_ok=True)
    cslc_dir = OUT / "cslc"
    cslc_dir.mkdir(exist_ok=True)
    orbit_dir = OUT / "orbits"
    orbit_dir.mkdir(exist_ok=True)

    cslc_paths: list[Path] = []
    failed_scenes: list[str] = []

    for i, scene in enumerate(slc_results):
        scene_id = scene.properties["fileID"].removesuffix("-SLC")
        sensing_str = scene.properties["startTime"][:19]
        sensing_dt = datetime.fromisoformat(sensing_str.rstrip("Z"))
        date_tag = sensing_dt.strftime("%Y%m%d")
        satellite = scene.properties.get("platform", "Sentinel-1A")
        sat_tag = "S1A" if "1A" in satellite else "S1B"

        cslc_out = cslc_dir / f"scene_{date_tag}"
        label = f"[{i+1:2d}/{len(slc_results)}] {date_tag}"

        # Check if CSLC already exists for this date
        existing_cslc = sorted(cslc_out.glob("**/*.h5"))
        # Filter out runconfig files -- only want actual CSLC products
        existing_cslc = [p for p in existing_cslc if "runconfig" not in p.name.lower()]
        if existing_cslc:
            cslc_h5 = existing_cslc[0]
            print(f"  {label}: exists ({cslc_h5.name})")
            cslc_paths.append(cslc_h5)
            continue

        print(f"  {label}: ", end="", flush=True)

        # -- Download SLC --
        safe_path = input_dir / f"{scene_id}.zip"
        if not safe_path.exists():
            # Check for any zip matching this date
            date_zips = sorted(input_dir.glob(f"*{date_tag}*.zip"))
            if date_zips:
                safe_path = date_zips[0]
            else:
                print("downloading SLC... ", end="", flush=True)
                try:
                    scene.download(path=str(input_dir), session=session)
                except Exception as e:
                    print(f"SKIP (download: {e})")
                    failed_scenes.append(date_tag)
                    continue
                # Find what was actually downloaded
                candidates = sorted(input_dir.glob(f"*{date_tag}*.zip"))
                if not candidates:
                    candidates = sorted(input_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime)
                if candidates:
                    safe_path = candidates[-1]

        if not safe_path.exists():
            print("SKIP (no SAFE file)")
            failed_scenes.append(date_tag)
            continue

        # -- Fetch orbit --
        print("orbit... ", end="", flush=True)
        try:
            orbit_path = fetch_orbit(
                sensing_time=sensing_dt,
                satellite=sat_tag,
                output_dir=orbit_dir,
            )
        except Exception as e:
            print(f"SKIP (orbit: {e})")
            failed_scenes.append(date_tag)
            continue

        # -- Run CSLC --
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
        except Exception as e:
            elapsed = time.time() - t0
            print(f"FAIL ({elapsed:.0f}s: {e})")
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

    # -- Stack summary --
    print(f"\n  CSLC stack : {len(cslc_paths)} files")
    print(f"  Failed     : {len(failed_scenes)} scenes")
    if failed_scenes:
        print(f"               {', '.join(failed_scenes)}")

    if len(cslc_paths) < 5:
        raise SystemExit(
            f"Only {len(cslc_paths)} CSLCs produced -- need at least 5 for meaningful "
            "time-series inversion.\nCheck download/processing logs above."
        )

    # Sort CSLC stack by date (filename contains date)
    cslc_paths = sorted(cslc_paths, key=lambda p: p.name)
    print("\n  Stack (sorted):")
    for p in cslc_paths:
        sz = p.stat().st_size / 1e6
        print(f"    {p.name}  ({sz:.1f} MB)")

    # Estimate total input size
    input_size_gb = sum(f.stat().st_size for f in input_dir.glob("*.zip")) / 1e9
    print(f"\n  Total SLC storage: {input_size_gb:.1f} GB")

    # ── Stage 7: Run DISP pipeline ───────────────────────────────────────────
    print("\n-- Stage 7: DISP Pipeline (dolphin -> tophu -> MintPy) --")
    disp_dir = OUT / "disp"
    # Phase 4 Rule 1 bug fix: dolphin 0.42+ produces velocity.tif under
    # `dolphin/timeseries/`, not `mintpy/velocity.h5`. The previous warm-path
    # probe pointed at a path that never exists, forcing a full re-run on
    # every invocation. Use the actual dolphin output for the warm probe.
    velocity_path = disp_dir / "dolphin" / "timeseries" / "velocity.tif"

    if velocity_path.exists():
        print(f"  Velocity already exists: {velocity_path}")
        print(f"  Size: {velocity_path.stat().st_size / 1e6:.1f} MB")
    else:
        print(f"  Input  : {len(cslc_paths)} CSLCs")
        print(f"  Output : {disp_dir}")
        print("  Running full DISP pipeline -- this may take several hours...")
        print()

        t0 = time.time()
        disp_result = run_disp(
            cslc_paths=cslc_paths,
            output_dir=disp_dir,
            threads_per_worker=8,       # M3 Max: 16 cores, use 8 threads per worker
            n_parallel_bursts=2,        # 2 bursts in parallel (128 GB RAM allows it)
            block_shape=(512, 512),     # larger blocks = fewer iterations
            n_parallel_unwrap=8,        # parallel unwrapping jobs
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
        raise SystemExit("No velocity.h5 produced. DISP pipeline may have failed silently.")

    # ── Stage 8: Explore our output ──────────────────────────────────────────
    print("\n-- Stage 8: Output Inspection --")
    print(f"\n  Our velocity: {velocity_path}")

    import rasterio

    # dolphin outputs velocity as GeoTIFF (rad/year in LOS)
    our_velocity = None
    with rasterio.open(velocity_path) as ds:
        our_velocity = ds.read(1).astype(np.float64)
        our_crs = ds.crs
        our_transform = ds.transform
        print(f"  shape : {our_velocity.shape}")
        print(f"  CRS   : {our_crs}")
        print(f"  dtype : {ds.dtypes[0]}")

    valid = np.isfinite(our_velocity) & (our_velocity != 0)
    if valid.any():
        print("\n  velocity stats (non-zero):")
        print(f"    valid pixels : {valid.sum():,}")
        print(f"    min          : {np.nanmin(our_velocity[valid]):.4f}")
        print(f"    max          : {np.nanmax(our_velocity[valid]):.4f}")
        print(f"    mean         : {np.nanmean(our_velocity[valid]):.4f}")
        print(f"    std          : {np.nanstd(our_velocity[valid]):.4f}")

    # Check time-series epochs
    ts_dir = disp_dir / "dolphin" / "timeseries"
    ts_files = sorted(ts_dir.glob("20*.tif")) if ts_dir.exists() else []
    if ts_files:
        print(f"\n  Time-series: {len(ts_files)} epochs")
        print(f"    first: {ts_files[0].name}")
        print(f"    last : {ts_files[-1].name}")

    # ── Stage 9: Compare against OPERA reference ─────────────────────────────
    print("\n-- Stage 9: Validation vs OPERA DISP-S1 --")

    if not opera_disp_results:
        print("  No OPERA DISP-S1 reference products available.")
        print("  Pipeline completed successfully -- comparison deferred.")
        print(f"\n  Our velocity: {velocity_path}")

    else:
        import re as _re
        from datetime import datetime as _dt

        import h5py
        import requests

        # Download OPERA DISP NetCDF files directly via HTTPS + Earthdata basic auth.
        # earthaccess.download() tries .zarr links which fail with 500 errors,
        # but direct HTTPS download of .nc files works with Earthdata credentials.
        print(f"  Downloading {len(opera_disp_results)} OPERA DISP .nc files...")
        session = requests.Session()
        session.auth = (
            os.environ["EARTHDATA_USERNAME"],
            os.environ["EARTHDATA_PASSWORD"],
        )

        downloaded_nc: list[Path] = []
        for j, result in enumerate(opera_disp_results):
            granule = result["umm"].get("GranuleUR", f"product_{j}")
            nc_path = ref_dir / f"{granule}.nc"

            if nc_path.exists() and nc_path.stat().st_size > 1e6:
                downloaded_nc.append(nc_path)
                continue

            # Find the .nc link
            nc_url = None
            for link in result.data_links():
                if link.endswith(".nc") and "short_wavelength" not in link:
                    nc_url = link
                    break

            if nc_url is None:
                print(f"  [{j+1}/{len(opera_disp_results)}] {granule[:60]}: no .nc link")
                continue

            print(f"  [{j+1}/{len(opera_disp_results)}] downloading {granule[:55]}...", end="", flush=True)  # noqa: E501
            try:
                r = session.get(nc_url, stream=True, allow_redirects=True)
                if r.status_code != 200:
                    print(f" FAIL ({r.status_code})")
                    continue
                with open(nc_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1048576):
                        f.write(chunk)
                mb = nc_path.stat().st_size / 1e6
                print(f" OK ({mb:.0f} MB)")
                downloaded_nc.append(nc_path)
            except Exception as exc:
                print(f" ERROR: {exc}")

        print(f"\n  Downloaded {len(downloaded_nc)} OPERA DISP file(s)")

        if not downloaded_nc:
            print("  No OPERA references available -- cannot compare.")
            sys.exit(0)

        # Read displacement fields from OPERA products, parse dates, build stack
        print("\n  Reading OPERA displacement fields...")
        date_pattern = _re.compile(r"_(\d{8}T\d{6}Z)_(\d{8}T\d{6}Z)_v")
        opera_data: list[tuple[float, np.ndarray]] = []  # (time_years, displacement)
        opera_x = opera_y = opera_crs_epsg = None

        for nc_path in downloaded_nc:
            m = date_pattern.search(nc_path.name)
            if not m:
                continue
            ref_dt = _dt.strptime(m.group(1), "%Y%m%dT%H%M%SZ")
            sec_dt = _dt.strptime(m.group(2), "%Y%m%dT%H%M%SZ")
            dt_years = (sec_dt - ref_dt).total_seconds() / (365.25 * 86400)

            try:
                with h5py.File(nc_path, "r") as hf:
                    disp = hf["displacement"][:]
                    if opera_x is None:
                        opera_x = hf["corrections/x"][:]
                        opera_y = hf["corrections/y"][:]
                        # OPERA DISP-S1 products use UTM (same as our output)
                        opera_crs_epsg = 32611  # UTM 11N (same as ours for this frame)
                opera_data.append((dt_years, disp))
            except Exception as exc:
                print(f"    {nc_path.name}: read error: {exc}")

        print(f"  Loaded {len(opera_data)} epochs, shape={opera_data[0][1].shape if opera_data else '?'}")  # noqa: E501

        if len(opera_data) < 3:
            print("  Too few epochs to derive velocity")
            sys.exit(0)

        # Compute OPERA velocity via per-pixel linear fit (displacement = velocity * time)
        print("\n  Computing OPERA velocity via linear fit...")
        times = np.array([t for t, _ in opera_data])
        stack = np.stack([d for _, d in opera_data], axis=0)

        # Vectorised least-squares per pixel: displacement = v*t + b
        # We want just v (slope)
        T = times - times.mean()
        denom = (T * T).sum()
        opera_velocity = np.full(stack.shape[1:], np.nan, dtype=np.float32)
        finite_mask = np.isfinite(stack)
        for r in range(stack.shape[1]):
            for c in range(stack.shape[2]):
                pix = stack[:, r, c]
                m = np.isfinite(pix)
                if m.sum() < 3:
                    continue
                t_m = T[m]
                p_m = pix[m] - pix[m].mean()
                d = (t_m * t_m).sum()
                if d > 0:
                    opera_velocity[r, c] = (t_m * p_m).sum() / d

        valid_opera = np.isfinite(opera_velocity)
        print(f"  OPERA velocity valid pixels: {valid_opera.sum():,}")
        print(f"    mean: {np.nanmean(opera_velocity):.6f}")
        print(f"    std : {np.nanstd(opera_velocity):.6f}")
        print(f"    shape: {opera_velocity.shape}")

        # Save for later analysis
        opera_vel_path = ref_dir / "opera_velocity_derived.npy"
        np.save(opera_vel_path, opera_velocity)
        print(f"  Saved: {opera_vel_path}")

        # --- Phase 4 D-01 + D-02: prepare_for_reference adapter ---
        print(
            "\n  [Phase 4 Stage 9] Multilooking native velocity onto OPERA "
            "grid via prepare_for_reference(method='block_mean')..."
        )
        import rioxarray  # noqa: F401  (registers .rio accessor)
        import xarray as xr
        from rasterio.transform import from_origin

        from subsideo.validation.compare_disp import prepare_for_reference

        opera_dx = float(opera_x[1] - opera_x[0])
        opera_dy = float(opera_y[1] - opera_y[0])
        opera_transform = from_origin(
            float(opera_x[0]) - 0.5 * opera_dx,
            float(opera_y[0]) - 0.5 * opera_dy,
            abs(opera_dx),
            abs(opera_dy),
        )
        opera_da = xr.DataArray(
            opera_velocity.astype(np.float64),
            dims=("y", "x"),
            coords={"y": opera_y, "x": opera_x},
        ).rio.write_crs(f"EPSG:{opera_crs_epsg}").rio.write_transform(opera_transform)

        our_on_opera = prepare_for_reference(
            native_velocity=velocity_path,
            reference_grid=opera_da,
            method=REFERENCE_MULTILOOK_METHOD,
        )
        if isinstance(our_on_opera, xr.DataArray):
            our_on_opera = our_on_opera.values
        print(
            f"  Multilooked velocity: shape={our_on_opera.shape}, "
            f"finite={int(np.isfinite(our_on_opera).sum()):,}"
        )

        # Compute metrics on valid-pixel intersection
        valid = np.isfinite(opera_velocity) & np.isfinite(our_on_opera) & (our_on_opera != 0)
        n_valid = int(valid.sum())
        print(f"  Valid intersection: {n_valid:,} pixels")

        if n_valid > 100:
            from subsideo.validation.metrics import bias, rmse, spatial_correlation

            # Convert our velocity from rad/year to m/year using Sentinel-1 wavelength
            # lambda_s1 = 0.0555 m; LOS displacement = -lambda * phase / (4*pi)
            lambda_s1 = 0.05546576  # m
            our_meters = -our_on_opera * lambda_s1 / (4.0 * np.pi)

            # OPERA displacement is already in meters
            r_val = spatial_correlation(our_meters, opera_velocity)
            b_val = bias(our_meters, opera_velocity)
            e_val = rmse(our_meters, opera_velocity)

            # Convert to mm/yr for criteria
            b_mm = b_val * 1000
            e_mm = e_val * 1000

            print(f"\n  {'='*60}")
            print(f"  Correlation  : {r_val:.4f}     (criterion: > 0.92)")
            print(f"  Bias         : {b_mm:.4f} mm/yr (criterion: < 3 mm/yr)")
            print(f"  RMSE         : {e_mm:.4f} mm/yr")
            print(f"  Valid pixels : {n_valid:,}")
            print(f"  {'='*60}")
            pass_corr = r_val > 0.92
            pass_bias = abs(b_mm) < 3.0
            overall = pass_corr and pass_bias
            print(f"  correlation > 0.92  : {'PASS' if pass_corr else 'FAIL'}")
            print(f"  |bias| < 3 mm/yr    : {'PASS' if pass_bias else 'FAIL'}")
            print(f"  Overall             : {'PASS' if overall else 'FAIL'}")
            print(f"  {'='*60}")
        else:
            # Phase 4 W3: honest BLOCKER path -- emit NaN reference-agreement
            # so the canonical-name assignment below does NOT hit NameError on
            # the small-sample branch. cell_status will be inferred 'BLOCKER'
            # in Stage 10 from the stable_mask_pixels < 100 criterion.
            print("  Not enough valid pixels for comparison -- emitting NaN reference-agreement.")
            r_val = float("nan")
            b_val = float("nan")
            e_val = float("nan")
            b_mm = float("nan")
            e_mm = float("nan")
            # n_valid was already computed above (= int(valid.sum()))

        # Phase 4 W3: canonical Stage 9 outputs (DISP-05 honest-FAIL discipline).
        # These names feed Stage 12 directly. NO dir() introspection — undefined
        # names must surface as NameError, not silently zero out (which would
        # corrupt the FAIL signal we are trying to report).
        # Phase 4 ME-01: avoid shadowing the imported `bias`/`rmse` callables
        # (line 700) by using disambiguated _val-suffixed names that flow into
        # Stage 12 (lines 1024-1027) verbatim.
        correlation_val = float(r_val)
        bias_mm_yr = float(b_mm)        # mm/yr (existing v1.0 conversion)
        rmse_mm_yr = float(e_mm)        # mm/yr
        sample_count = int(n_valid)

        # Skip the old remote-access code path
        opera_disp_results = None  # prevent fall-through

    # --- Phase 4 Stage 10: product-quality block (CONTEXT D-05..D-08) ---
    print(
        "\n  [Phase 4 Stage 10] Computing product-quality (coherence + "
        "residual) on stable terrain..."
    )
    from pathlib import Path as _PhasePath

    from rasterio.warp import Resampling as _Resampling
    from rasterio.warp import reproject as _reproject

    from subsideo.data.natural_earth import load_coastline_and_waterbodies
    from subsideo.data.worldcover import fetch_worldcover_class60, load_worldcover_for_bbox
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
    worldcover_dir = _PhasePath("eval-disp/worldcover")
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

    # 10.2 Coherence: cross-cell read for SoCal (CONTEXT D-08)
    phase3_metrics_path = _PhasePath("eval-cslc-selfconsist-nam/metrics.json")
    coherence_source = "fresh"
    coh_stats: dict[str, float] = {}
    if phase3_metrics_path.exists():
        import json as _json
        try:
            phase3 = _json.loads(phase3_metrics_path.read_text())
            socal = next(a for a in phase3.get("per_aoi", []) if a.get("aoi_name") == "SoCal")
            m = socal.get("product_quality", {}).get("measurements", {})
            if m and "coherence_median_of_persistent" in m:
                # Strip residual_mm_yr -- DISP residual is fresh (D-08)
                coh_stats = {
                    k: float(v) for k, v in m.items() if k != "residual_mm_yr"
                }
                coherence_source = "phase3-cached"
                _coh_med = coh_stats.get("coherence_median_of_persistent")
                print(
                    f"  coherence: phase3-cached "
                    f"coh_med_of_persistent={_coh_med:.3f}"
                )
        except (StopIteration, KeyError, ValueError) as _err:
            print(
                f"  coherence: phase3 cache present but unreadable "
                f"({_err}) -- falling back to fresh"
            )
            coherence_source = "fresh"
            coh_stats = {}

    if coherence_source == "fresh":
        # B1 root-cause fix: import the PUBLIC compute_ifg_coherence_stack from
        # selfconsistency.py (Plan 04-01 Task 3 promotion). Do NOT import from
        # run_eval_cslc_selfconsist_nam -- that symbol is now removed and only
        # exists at module level via the public selfconsistency.py promotion.
        print("  coherence: fresh-computing from cached CSLCs (boxcar 5x5)...")
        sorted_h5 = sorted(_PhasePath("eval-disp/cslc").rglob("*.h5"))
        sorted_h5 = [p for p in sorted_h5 if "runconfig" not in p.name.lower()]
        ifgrams_stack = compute_ifg_coherence_stack(sorted_h5, boxcar_px=5)
        stable_mask_cslc = _reproject_mask_to_grid(
            stable_mask, dem_transform, dem_crs, ifgrams_stack.shape[1:]
        )
        coh_stats = coherence_stats(ifgrams_stack, stable_mask_cslc, coherence_threshold=0.6)

    # 10.3 Residual: ALWAYS fresh from dolphin output (CONTEXT D-08)
    print("  residual: fresh from dolphin velocity.tif...")
    import rasterio as _rio
    with _rio.open(velocity_path) as _src:
        v_rad_per_year = _src.read(1).astype(np.float64)
        velocity_transform = _src.transform
    SENTINEL1_WAVELENGTH_M = 0.05546576
    v_mm_yr = -v_rad_per_year * SENTINEL1_WAVELENGTH_M / (4.0 * np.pi) * 1000.0
    stable_mask_vel = _reproject_mask_to_grid(
        stable_mask, dem_transform, dem_crs, v_mm_yr.shape
    )
    if int(stable_mask_vel.sum()) > 0:
        residual = residual_mean_velocity(v_mm_yr, stable_mask_vel, frame_anchor="median")
    else:
        residual = float("nan")
    print(f"  residual_mm_yr: {residual:+.2f}")

    # --- Phase 4 Stage 11: ramp-attribution diagnostic (CONTEXT D-09..D-12) ----
    print("\n  [Phase 4 Stage 11] Per-IFG planar ramp fit + attribution...")
    import re as _re_phase4

    from subsideo.validation.matrix_schema import (
        DISPCellMetrics,
        DISPProductQualityResultJson,
        MetaJson,
        PerIFGRamp,
        RampAggregate,
        RampAttribution,
        ReferenceAgreementResultJson,
    )
    from subsideo.validation.selfconsistency import (
        auto_attribute_ramp,
        compute_ramp_aggregate,
        fit_planar_ramp,
    )

    unwrapped_dir = _PhasePath("eval-disp/disp/dolphin/unwrapped")
    unw_files = sorted(unwrapped_dir.glob("*.unw.tif"))
    date_pat = _re_phase4.compile(r"^(\d{8})_(\d{8})\.unw\.tif$")
    def _is_sequential_12day(ref_iso: str, sec_iso: str) -> bool:
        from datetime import datetime as _dt
        return abs((_dt.fromisoformat(sec_iso) - _dt.fromisoformat(ref_iso)).days - 12) <= 1

    sequential_unw: list[tuple[Path, str, str]] = []
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
    cor_dir = _PhasePath("eval-disp/disp/dolphin/interferograms")
    for f, _, _ in sequential_unw:
        cor_file = cor_dir / f.name.replace(".unw.tif", ".int.cor.tif")
        if not cor_file.exists():
            ifg_coh_means.append(float("nan"))
            continue
        with _rio.open(cor_file) as _src:
            cor = _src.read(1).astype(np.float64)
        valid_cor = np.isfinite(cor) & (cor > 0)
        ifg_coh_means.append(float(cor[valid_cor].mean()) if valid_cor.any() else float("nan"))
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
        magnitude_vs_coherence_pearson_r=agg_dict["magnitude_vs_coherence_pearson_r"],
    )
    print(f"  ramp aggregate: mean_mag={agg_dict['mean_magnitude_rad']:.2f} rad, "
          f"sigma_dir={agg_dict['direction_stability_sigma_deg']:.1f} deg, "
          f"r(mag,coh)={agg_dict['magnitude_vs_coherence_pearson_r']:.2f}")
    print(f"  auto-attributed source: {attributed_source}")

    per_ifg_records: list[PerIFGRamp] = []
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
    print("\n  [Phase 4 Stage 12] Writing eval-disp/metrics.json + meta.json...")
    import hashlib as _hash
    import platform as _platform
    import subprocess as _sp
    import sys as _sys
    import time as _time

    OUT_DIR = _PhasePath("eval-disp")
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
    # W3 -- explicit references to the canonical names assigned in Edit 2
    # (correlation_val, bias_mm_yr, rmse_mm_yr, sample_count -- renamed per
    # Phase 4 ME-01 to disambiguate from the imported `bias`/`rmse` callables
    # at line 700). NO dir() introspection. If any name is undefined here,
    # NameError surfaces loudly, which is the desired behaviour per the
    # plan's explicit "do NOT silently set them to 0" requirement.
    ra = ReferenceAgreementResultJson(
        measurements={
            "correlation": correlation_val,
            "bias_mm_yr": bias_mm_yr,
            "rmse_mm_yr": rmse_mm_yr,
            "sample_count": float(sample_count),
        },
        criterion_ids=["disp.correlation_min", "disp.bias_mm_yr_max"],
    )
    metrics = DISPCellMetrics(
        schema_version=1,
        product_quality=pq,
        reference_agreement=ra,
        ramp_attribution=ramp_attribution_obj,
        cell_status=cell_status,
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
        git_sha = _sp.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        git_dirty = bool(_sp.check_output(["git", "status", "--porcelain"], text=True).strip())
    except Exception:
        git_sha, git_dirty = "unknown", False

    def _sha256_file(p: Path) -> str:
        h = _hash.sha256()
        with open(p, "rb") as fh:
            for block in iter(lambda: fh.read(65536), b""):
                h.update(block)
        return h.hexdigest()

    input_hashes: dict[str, str] = {"velocity_tif": _sha256_file(velocity_path)}
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
    print(f"eval-disp (SoCal): cell_status={cell_status}")
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
        f"  RA: r={correlation_val:.3f} (>0.92 BINDING) / "
        f"bias={bias_mm_yr:+.2f} mm/yr (<3.0 BINDING)"
    )
    print(f"  Ramp: attr={attributed_source}, mean_mag={agg_dict['mean_magnitude_rad']:.2f} rad")
    print("=" * 70)
