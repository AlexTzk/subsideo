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
import warnings; warnings.filterwarnings("ignore")

if __name__ == "__main__":
    import os
    import sys
    import time
    import sqlite3
    from pathlib import Path
    from datetime import datetime
    from dotenv import load_dotenv

    import asf_search as asf
    import earthaccess
    import numpy as np
    import h5py

    from subsideo.products.cslc import run_cslc
    from subsideo.products.disp import run_disp
    from subsideo.data.dem import fetch_dem
    from subsideo.data.orbits import fetch_orbit

    load_dotenv()

    # ── Configuration ────────────────────────────────────────────────────────
    BURST_ID = "t144_308029_iw1"
    RELATIVE_ORBIT = 144

    # 6-month window: ~15 S1A repeat-pass acquisitions at 12-day interval
    DATE_START = "2024-01-01"
    DATE_END   = "2024-06-30"

    # Burst footprint from opera-utils burst DB (SoCal, Ventura/LA area)
    # WGS84: (-119.48, 33.42) to (-118.52, 33.79)
    BURST_BBOX = (-119.5, 33.4, -118.5, 33.8)
    DEM_BBOX   = [-119.7, 33.2, -118.3, 34.0]  # wider for DEM coverage
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
            print(f"    {f}: {frame_counts[f]} products, acquisition hour ~{frame_hours[f]:02d} UTC")

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
            print(f"  Falling back to all frames -- correlation may fail")
            matching_frames = list(frame_counts.keys())

        # Among matching frames, pick the one with most products
        target_frame = max(matching_frames, key=lambda f: frame_counts[f])
        opera_disp_results = [
            r for r in opera_disp_results
            if target_frame in r["umm"].get("GranuleUR", "")
        ]
        print(f"  Using frame {target_frame} (UTC {frame_hours[target_frame]:02d}): {len(opera_disp_results)} product(s)")
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
        stop_dt = datetime.fromisoformat(r.properties.get("stopTime", r.properties["startTime"])[:19])
        start_sec = start_dt.hour * 3600 + start_dt.minute * 60 + start_dt.second
        stop_sec = stop_dt.hour * 3600 + stop_dt.minute * 60 + stop_dt.second
        contains_burst = start_sec <= BURST_UTC_SECONDS <= stop_sec
        margin = min(BURST_UTC_SECONDS - start_sec, stop_sec - BURST_UTC_SECONDS) if contains_burst else -1

        if date_key not in by_date:
            by_date[date_key] = (r, contains_burst, margin)
        else:
            _, prev_contains, prev_margin = by_date[date_key]
            # Prefer the SLC that contains the burst; tie-break by margin
            if (contains_burst and not prev_contains) or \
               (contains_burst and prev_contains and margin > prev_margin):
                by_date[date_key] = (r, contains_burst, margin)

    slc_results = sorted([r for r, _, _ in by_date.values()], key=lambda r: r.properties["startTime"])
    print(f"  Found {len(slc_results)} unique SLC date(s) on orbit {RELATIVE_ORBIT}")
    for i, r in enumerate(slc_results):
        print(f"    [{i+1:2d}] {r.properties['startTime'][:19]}  {r.properties['fileID'][:55]}")

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
            bounds=DEM_BBOX,
            output_epsg=EPSG,
            output_dir=dem_dir,
        )
        print(f"  DEM: {dem_path.name}")

    # ── Stage 5: Burst database ──────────────────────────────────────────────
    print("\n-- Stage 5: Burst database --")
    burst_db = OUT / "burst_db.sqlite3"
    if not burst_db.exists():
        from pyproj import Transformer
        from opera_utils.burst_frame_db import get_burst_id_geojson

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
    velocity_path = disp_dir / "mintpy" / "velocity.h5"

    if velocity_path.exists():
        print(f"  Velocity already exists: {velocity_path}")
        print(f"  Size: {velocity_path.stat().st_size / 1e6:.1f} MB")
    else:
        print(f"  Input  : {len(cslc_paths)} CSLCs")
        print(f"  Output : {disp_dir}")
        print(f"  Running full DISP pipeline -- this may take several hours...")
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
        print(f"\n  velocity stats (non-zero):")
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
        import requests
        import h5py
        from datetime import datetime as _dt
        import re as _re

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

            print(f"  [{j+1}/{len(opera_disp_results)}] downloading {granule[:55]}...", end="", flush=True)
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

        print(f"  Loaded {len(opera_data)} epochs, shape={opera_data[0][1].shape if opera_data else '?'}")

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

        # Compare against our velocity by reprojecting our output to OPERA grid
        print("\n  Reprojecting our velocity to OPERA grid...")
        from rasterio.warp import Resampling, reproject
        from rasterio.transform import from_origin

        # Build OPERA grid transform from x/y coordinates
        opera_dx = float(opera_x[1] - opera_x[0])
        opera_dy = float(opera_y[1] - opera_y[0])  # typically negative
        opera_transform = from_origin(
            opera_x[0] - opera_dx / 2,
            opera_y[0] - opera_dy / 2,
            abs(opera_dx),
            abs(opera_dy),
        )

        our_on_opera = np.full(opera_velocity.shape, np.nan, dtype=np.float32)
        with rasterio.open(velocity_path) as src:
            reproject(
                source=rasterio.band(src, 1),
                destination=our_on_opera,
                dst_transform=opera_transform,
                dst_crs=f"EPSG:{opera_crs_epsg}",
                resampling=Resampling.bilinear,
            )

        # Compute metrics on valid-pixel intersection
        valid = np.isfinite(opera_velocity) & np.isfinite(our_on_opera) & (our_on_opera != 0)
        n_valid = int(valid.sum())
        print(f"  Valid intersection: {n_valid:,} pixels")

        if n_valid > 100:
            from subsideo.validation.metrics import spatial_correlation, bias, rmse

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
            print("  Not enough valid pixels for comparison")

        # Skip the old remote-access code path
        opera_disp_results = None  # prevent fall-through

    if opera_disp_results:
        import xarray as xr

        # OPERA DISP-S1 products are Zarr stores — open remotely via
        # earthaccess (S3/HTTPS) without downloading.
        print(f"  Opening {len(opera_disp_results)} OPERA DISP product(s) remotely...")

        # Collect displacement values at each epoch from OPERA products
        opera_displacements: dict[str, np.ndarray] = {}
        opera_crs = None
        opera_transform = None

        try:
            # earthaccess.open() returns file-like objects for remote access
            file_handles = earthaccess.open(opera_disp_results[:20])
            print(f"  Opened {len(file_handles)} remote file handle(s)")

            # Open first product to explore structure
            print("\n  Exploring OPERA DISP-S1 product structure...")
            ds = xr.open_dataset(file_handles[0], engine="h5netcdf")
            print(f"  Variables: {list(ds.data_vars)}")
            print(f"  Coords  : {list(ds.coords)}")
            print(f"  Dims    : {dict(ds.dims)}")
            for var in ds.data_vars:
                print(f"    {var}: shape={ds[var].shape}, dtype={ds[var].dtype}")
            ds.close()

            # Try to read displacement from each product
            for j, fh in enumerate(file_handles):
                try:
                    ds = xr.open_dataset(fh, engine="h5netcdf")
                    # Look for displacement variable
                    disp_var = None
                    for candidate in ["displacement", "short_wavelength_displacement",
                                      "unwrapped_phase", "recommended_displacement"]:
                        if candidate in ds.data_vars:
                            disp_var = candidate
                            break
                    if disp_var is None:
                        # Fallback: first 2D float variable
                        for var in ds.data_vars:
                            if ds[var].ndim >= 2 and np.issubdtype(ds[var].dtype, np.floating):
                                disp_var = var
                                break

                    if disp_var:
                        data = ds[disp_var].values
                        if data.ndim == 3:
                            data = data[0]  # Take first band if 3D
                        granule = opera_disp_results[j]["umm"].get("GranuleUR", f"product_{j}")
                        opera_displacements[granule] = data
                        if j == 0:
                            print(f"\n  Using variable: '{disp_var}', shape={data.shape}")

                    ds.close()
                except Exception as e:
                    print(f"  Product {j}: read error: {e}")
                    continue

        except Exception as e:
            print(f"  Remote access failed: {e}")
            print("  Trying alternative access via Zarr...")

            # Alternative: try opening as Zarr store via HTTPS
            try:
                import zarr
                import fsspec

                for j, result in enumerate(opera_disp_results[:5]):
                    # Get data URLs from granule metadata
                    links = result.data_links()
                    zarr_urls = [l for l in links if "zarr" in l.lower() or ".nc" in l.lower()]
                    if zarr_urls:
                        print(f"  Product {j} URLs: {zarr_urls[:2]}")
                    else:
                        all_urls = result.data_links()
                        print(f"  Product {j} all URLs: {all_urls[:3]}")
            except Exception as e2:
                print(f"  Zarr fallback also failed: {e2}")

        if opera_displacements:
            print(f"\n  Read {len(opera_displacements)} OPERA displacement field(s)")

            # Compute OPERA velocity via linear fit (displacement vs time)
            # Extract dates from granule names:
            # OPERA_L3_DISP-S1_IW_F38503_VV_<ref_date>_<secondary_date>_...
            import re
            from datetime import datetime as dt

            date_pattern = re.compile(r"_(\d{8}T\d{6}Z)_(\d{8}T\d{6}Z)_v")
            epoch_data: list[tuple[float, np.ndarray]] = []

            for granule, disp in opera_displacements.items():
                m = date_pattern.search(granule)
                if m:
                    ref_date = dt.strptime(m.group(1), "%Y%m%dT%H%M%SZ")
                    sec_date = dt.strptime(m.group(2), "%Y%m%dT%H%M%SZ")
                    dt_years = (sec_date - ref_date).total_seconds() / (365.25 * 86400)
                    epoch_data.append((dt_years, disp))
                    if len(epoch_data) <= 3:
                        print(f"    {sec_date.strftime('%Y-%m-%d')}: dt={dt_years:.3f} yr")

            if len(epoch_data) >= 3:
                print(f"\n  Computing OPERA velocity from {len(epoch_data)} epochs...")

                # Stack and fit velocity per pixel
                times = np.array([t for t, _ in epoch_data])
                stack = np.stack([d for _, d in epoch_data], axis=0)  # (n_epochs, rows, cols)
                rows, cols = stack.shape[1], stack.shape[2]

                # Linear fit: displacement = velocity * time + offset
                # Vectorised per-pixel least-squares
                opera_velocity = np.full((rows, cols), np.nan, dtype=np.float64)
                for r_idx in range(rows):
                    for c_idx in range(cols):
                        pixel_ts = stack[:, r_idx, c_idx]
                        valid_mask = np.isfinite(pixel_ts)
                        if valid_mask.sum() >= 3:
                            A = np.column_stack([times[valid_mask], np.ones(valid_mask.sum())])
                            coeffs, _, _, _ = np.linalg.lstsq(A, pixel_ts[valid_mask], rcond=None)
                            opera_velocity[r_idx, c_idx] = coeffs[0]

                valid_opera = np.isfinite(opera_velocity)
                print(f"  OPERA velocity: {valid_opera.sum():,} valid pixels")
                print(f"    mean: {np.nanmean(opera_velocity):.4f}")
                print(f"    std : {np.nanstd(opera_velocity):.4f}")

                # Save OPERA velocity for inspection
                opera_vel_path = ref_dir / "opera_velocity_derived.npy"
                np.save(opera_vel_path, opera_velocity)
                print(f"  Saved: {opera_vel_path}")

                # Compare against our velocity
                if our_velocity is not None:
                    from subsideo.validation.metrics import spatial_correlation, bias, rmse

                    # Shapes will likely differ — OPERA frame vs our single burst.
                    # Crop to overlapping region based on shape.
                    if opera_velocity.shape == our_velocity.shape:
                        valid = np.isfinite(opera_velocity) & np.isfinite(our_velocity)
                        n_valid = valid.sum()
                        print(f"\n  Comparison ({n_valid:,} valid pixels):")
                        if n_valid > 10:
                            r_val = spatial_correlation(our_velocity, opera_velocity)
                            b_val = bias(our_velocity, opera_velocity)
                            e_val = rmse(our_velocity, opera_velocity)
                            print(f"    Correlation  : {r_val:.4f}  (criterion: > 0.92)")
                            print(f"    Bias         : {b_val:.4f} mm/yr  (criterion: < 3)")
                            print(f"    RMSE         : {e_val:.4f} mm/yr")
                            pass_corr = r_val > 0.92
                            pass_bias = abs(b_val) < 3.0
                            overall = pass_corr and pass_bias
                            print(f"\n  {'='*50}")
                            print(f"  correlation > 0.92 : {'PASS' if pass_corr else 'FAIL'}")
                            print(f"  |bias| < 3 mm/yr   : {'PASS' if pass_bias else 'FAIL'}")
                            print(f"  Overall            : {'PASS' if overall else 'FAIL'}")
                            print(f"  {'='*50}")
                    else:
                        print(f"\n  Shape mismatch: ours={our_velocity.shape}, OPERA={opera_velocity.shape}")
                        print("  OPERA covers full frame; our output is single-burst.")
                        print("  Spatial subsetting needed -- extracting burst footprint from OPERA frame...")

                        # Attempt: if OPERA is larger, try to find our burst region
                        # within the OPERA frame by cross-correlation on valid-pixel patterns
                        print("  NOTE: Georeferenced comparison requires CRS/transform metadata")
                        print("  from both products. This will be implemented once product")
                        print("  structure is confirmed. Saving both arrays for manual analysis.")
                        np.save(ref_dir / "our_velocity.npy", our_velocity)
                        print(f"  Saved: {ref_dir / 'our_velocity.npy'}")
            else:
                print(f"  Only {len(epoch_data)} epoch(s) with parseable dates -- need >= 3 for velocity fit")
        else:
            print("  No displacement data read from OPERA products.")

    # ── Summary ──────────────────────────────────────────────────────────────
    ts_path = disp_dir / "mintpy" / "timeSeries.h5"
    print(f"\n{'='*70}")
    print("DISP-S1 Pipeline Completed")
    print(f"{'='*70}")
    print(f"  CSLC stack  : {len(cslc_paths)} files")
    print(f"  Velocity    : {velocity_path}")
    print(f"  Time-series : {ts_path if ts_path.exists() else 'N/A'}")
    print(f"  OPERA ref   : {len(opera_disp_results) if opera_disp_results else 0} product(s)")
    print(f"  Output dir  : {OUT}")
    print(f"{'='*70}")
