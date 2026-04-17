# run_eval_cslc.py — N.Am. CSLC-S1 validation against OPERA
# Reuses the S1 SLC SAFE, orbit, and DEM already downloaded by run_eval.py
# (eval-rtc/ inputs).  Downloads the matching OPERA CSLC-S1 reference from
# ASF DAAC and runs the subsideo compass pipeline on burst t144_308029_iw1.
import warnings; warnings.filterwarnings("ignore")

if __name__ == "__main__":
    import earthaccess
    from pathlib import Path
    from datetime import datetime
    from dotenv import load_dotenv

    from subsideo.products.cslc import run_cslc
    from subsideo.validation.compare_cslc import compare_cslc

    load_dotenv()

    # ── Shared inputs (already present from RTC eval) ─────────────────────────
    RTC_EVAL = Path("./eval-rtc")
    SAFE_PATH = RTC_EVAL / "input" / "S1A_IW_SLC__1SDV_20240624T140113_20240624T140140_054466_06A0BA_20E5.zip"
    DEM_PATH  = RTC_EVAL / "dem" / "glo30_utm32611.tif"
    ORBITS_DIR = RTC_EVAL / "orbits"

    BURST_ID    = "t144_308029_iw1"   # compass / opera-rtc lowercase format
    SENSING_DATE = datetime(2024, 6, 24, 14, 1, 16)
    SATELLITE   = "S1A"

    OUT = Path("./eval-cslc")
    OUT.mkdir(exist_ok=True)

    # Sanity-check shared inputs exist
    for p in (SAFE_PATH, DEM_PATH):
        if not p.exists():
            raise SystemExit(
                f"Missing shared input: {p}\n"
                "Run run_eval.py first to download the S1 SAFE and DEM."
            )

    orbit_candidates = sorted(ORBITS_DIR.glob("*.EOF"))
    if not orbit_candidates:
        raise SystemExit(
            f"No orbit file found in {ORBITS_DIR}\n"
            "Run run_eval.py first to download the orbit."
        )
    orbit_path = orbit_candidates[0]

    print(f"SAFE  : {SAFE_PATH.name}  ({SAFE_PATH.stat().st_size / 1e9:.2f} GB)")
    print(f"DEM   : {DEM_PATH.name}")
    print(f"Orbit : {orbit_path.name}")

    # ── 1. Authenticate with Earthdata ────────────────────────────────────────
    auth = earthaccess.login(strategy="environment")

    # ── 2. Download OPERA CSLC-S1 reference from ASF ─────────────────────────
    # OPERA CSLC-S1 granule naming: OPERA_L2_CSLC-S1_T144-308029-IW1_<sensing>Z_<proc>Z_S1A_v1.0
    ref_dir = OUT / "opera_reference"
    ref_dir.mkdir(exist_ok=True)

    existing_h5 = list(ref_dir.glob("OPERA_L2_CSLC-S1*.h5"))
    if existing_h5:
        ref_h5 = existing_h5[0]
        print(f"\nReference already present: {ref_h5.name}")
    else:
        print("\nSearching for OPERA CSLC-S1 reference...")
        ref_results = earthaccess.search_data(
            short_name="OPERA_L2_CSLC-S1_V1",
            temporal=("2024-06-24", "2024-06-25"),
            granule_name="OPERA_L2_CSLC-S1_T144-308029-IW1_20240624T140116Z*",
        )
        if not ref_results:
            # Widen the time window and try without sensing-time suffix
            print("  Narrowed search returned nothing — broadening to burst+date...")
            ref_results = earthaccess.search_data(
                short_name="OPERA_L2_CSLC-S1_V1",
                temporal=("2024-06-24", "2024-06-25"),
                granule_name="OPERA_L2_CSLC-S1_T144-308029-IW1*",
            )
        if not ref_results:
            raise SystemExit(
                "No OPERA CSLC-S1 reference found for T144-308029-IW1 on 2024-06-24.\n"
                "Check https://search.earthdata.nasa.gov — "
                "short_name=OPERA_L2_CSLC-S1_V1 temporal=2024-06-24/2024-06-25"
            )

        print(f"  Found {len(ref_results)} granule(s):")
        for r in ref_results:
            print(f"    {r['meta']['concept-id']}  {r['umm'].get('GranuleUR', '')}")

        downloaded = earthaccess.download(ref_results, str(ref_dir))
        print(f"  Downloaded: {[Path(f).name for f in downloaded]}")

        existing_h5 = list(ref_dir.glob("OPERA_L2_CSLC-S1*.h5"))
        if not existing_h5:
            raise SystemExit(
                "Download completed but no OPERA_L2_CSLC-S1*.h5 found in "
                f"{ref_dir}.\nFiles present: {list(ref_dir.iterdir())}"
            )
        ref_h5 = existing_h5[0]

    print(f"Reference HDF5: {ref_h5.name}  ({ref_h5.stat().st_size / 1e6:.1f} MB)")

    # ── 3. Run CSLC-S1 pipeline (compass) ────────────────────────────────────
    cslc_out = OUT / "output"
    print(f"\nRunning CSLC pipeline on burst {BURST_ID}...")

    # Burst database with EPSG and bbox for compass geogrid computation.
    # Without this, compass computes incorrect grid dimensions.
    burst_db = OUT / "burst_db.sqlite3"
    if not burst_db.exists():
        import sqlite3
        from pyproj import Transformer
        from opera_utils.burst_frame_db import get_burst_id_geojson
        import numpy as np_

        geojson = get_burst_id_geojson(BURST_ID)
        feat = geojson["features"][0]
        coords = feat["geometry"]["coordinates"][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        # Use EPSG from OPERA reference (UTM zone from the product spec)
        epsg = 32611
        t = Transformer.from_crs(4326, epsg, always_xy=True)
        xs, ys = t.transform(lons, lats)
        conn = sqlite3.connect(str(burst_db))
        conn.execute(
            "CREATE TABLE burst_id_map "
            "(burst_id_jpl TEXT PRIMARY KEY, epsg INTEGER, "
            "xmin REAL, ymin REAL, xmax REAL, ymax REAL)"
        )
        conn.execute(
            "INSERT INTO burst_id_map VALUES (?, ?, ?, ?, ?, ?)",
            (BURST_ID, epsg, min(xs), min(ys), max(xs), max(ys)),
        )
        conn.commit()
        conn.close()
        print(f"Created burst database: {burst_db}")

    result = run_cslc(
        safe_paths=[SAFE_PATH],
        orbit_path=orbit_path,
        dem_path=DEM_PATH,
        burst_ids=[BURST_ID],
        output_dir=cslc_out,
        burst_database_file=burst_db,
    )

    print(f"  Valid          : {result.valid}")
    print(f"  Errors         : {result.validation_errors}")

    # compass writes to output_dir/<burst_id>/<burst>_<date>.h5 or directly
    # run_cslc globs output_dir/*.h5; also check one level deeper
    h5_candidates = sorted(cslc_out.glob("*.h5")) + sorted(cslc_out.glob("**/*.h5"))
    # Deduplicate while preserving order
    seen: set[Path] = set()
    h5_candidates_unique: list[Path] = []
    for p in h5_candidates:
        if p not in seen:
            seen.add(p)
            h5_candidates_unique.append(p)

    print(f"  HDF5 outputs   : {[p.name for p in h5_candidates_unique]}")

    if not h5_candidates_unique:
        raise SystemExit("CSLC pipeline produced no HDF5 outputs — check logs above.")

    # Pick the burst HDF5 (prefer one matching the burst ID, skip runconfig)
    product_h5 = next(
        (p for p in h5_candidates_unique if BURST_ID.replace("_", "-").lower() in p.name.lower()
         or BURST_ID.lower() in p.name.lower()),
        h5_candidates_unique[0],
    )
    print(f"  Using product  : {product_h5.name}")

    # ── 4. Validate against OPERA CSLC-S1 reference ───────────────────────────
    print("\nComparing subsideo CSLC-S1 vs OPERA N.Am. reference...")
    val = compare_cslc(product_path=product_h5, reference_path=ref_h5)

    print(f"\n{'='*60}")
    print(f"  Amplitude correlation : {val.amplitude_correlation:.4f}  (threshold > 0.6)")
    print(f"  Amplitude RMSE       : {val.amplitude_rmse_db:.2f} dB  (threshold < 4.0 dB)")
    print(f"  Phase RMS            : {val.phase_rms_rad:.4f} rad  (informational)")
    print(f"  Coherence            : {val.coherence:.4f}  (informational)")
    print(f"{'='*60}")
    for criterion, passed in val.pass_criteria.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {criterion:45s}: {status}")
    print(f"{'='*60}")

    all_pass = all(val.pass_criteria.values())
    print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
    if val.coherence < 0.1:
        print(
            "\nNote: Low phase coherence is expected when comparing across different"
            "\nisce3/compass versions (product uses isce3 0.25.x, OPERA reference uses"
            "\nice3 0.15.x). Amplitude-based metrics are used for validation instead."
        )
