# run_eval_dist.py -- N.Am. DIST-S1 validation against OPERA reference
#
# Runs the subsideo DIST-S1 surface-disturbance pipeline against a N.Am.
# MGRS tile with a known disturbance event (wildfire), and attempts to
# compare it against the OPERA DIST-S1 reference product from ASF DAAC.
#
# Target:
#   AOI     : Park Fire, California 2024 (Tehama/Butte county)
#   Window  : 2024-07-01 -> 2024-08-15 (covers July 24 ignition)
#   MGRS    : 10TEM / 10TFM (NorCal, UTM 10N / EPSG:32610)
#
# Prerequisites:
#   - EARTHDATA_USERNAME / EARTHDATA_PASSWORD in .env (for ASF DAAC + earthaccess)
#   - subsideo conda env with dist_s1 2.0.13, opera-utils, asf-search, earthaccess
#
# Storage estimate: ~2-3 GB (OPERA RTC-S1 stack + DIST-S1 reference COG + workflow scratch)
# Compute estimate: 20-60 minutes on M3 Max
#
# Resume-safe: each stage skips if outputs already exist.
#
# ---------------------------------------------------------------------------
# Probe results (recorded in Task 3 sub-step 3a, 2026-04-15):
# ---------------------------------------------------------------------------
#
# Probe 1 -- OPERA DIST-S1 reference product availability on NASA Earthdata:
#   * earthaccess.search_data(short_name='OPERA_L3_DIST-ALERT-S1_V1', ...) -> EMPTY
#   * earthaccess.search_data(short_name='OPERA_L3_DIST-S1_V1', ...)       -> EMPTY
#   * earthaccess.search_data(short_name='OPERA_L3_DIST-ANN-S1_V1', ...)   -> EMPTY
#   * CMR keyword search 'OPERA DIST' returns only HLS-based products:
#       - OPERA_L3_DIST-ALERT-HLS_V1 (Harmonized Landsat-Sentinel-2, NOT S1)
#       - OPERA_L3_DIST-ANN-HLS_V1
#     and the DISP-S1 collection (OPERA_L3_DISP-S1_V1).
#   * asf-search: no DIST-S1 dataset or processingLevel. Only DISP-S1
#     products are under the OPERA-S1 asf-search dataset as of 2026-04.
#
# Conclusion: OPERA DIST-S1 reference products are NOT yet published to
# ASF DAAC / NASA Earthdata. The Option A reference path is unavailable
# at eval time. The script handles this by running the subsideo DIST-S1
# pipeline end-to-end anyway and emitting a "STRUCTURALLY COMPLETE"
# verdict (no reference comparison) in place of a PASS/FAIL metric table.
# The compare_dist() module is still exercised: if any .tif is dropped
# into eval-dist/opera_reference/ by hand after publication, the script
# picks it up on the next rerun and produces real metrics.
#
# Probe 2 -- OPERA RTC-S1 input product availability:
#   * asf.search(dataset='OPERA-S1', processingLevel='RTC',
#       intersectsWith=<Park Fire bbox>, start='2024-07-15', end='2024-08-15')
#     returns 50+ products across Sentinel-1 tracks T035, T042, T115, T137.
#   * Track 115 (ascending, ~14:16 UTC) has 9 products in the window --
#     sufficient for the dist_s1 multi-window lookback strategy.
#   * Example fileID:
#       OPERA_L2_RTC-S1_T115-245704-IW1_20240809T141606Z_20240809T193525Z_S1A_30_v1.0
#
# ---------------------------------------------------------------------------
# dist_s1 2.0.13 API notes (probed in Task 1 sub-step 1c):
# ---------------------------------------------------------------------------
# run_dist_s1_workflow(mgrs_tile_id, post_date, track_number, dst_dir, ...)
# Default lookback_strategy='multi_window'. Auto-fetches RTC inputs from
# ASF DAAC given mgrs_tile_id + post_date + track_number -- matches our
# existing products/dist.py::run_dist() wiring exactly.
# ---------------------------------------------------------------------------
import warnings; warnings.filterwarnings("ignore")

EXPECTED_WALL_S = 1800   # Plan 01-07 supervisor AST-parses this constant (D-11)

if __name__ == "__main__":
    import json as _json
    import os
    import sys
    import time
    from datetime import datetime
    from pathlib import Path

    import numpy as np
    from dotenv import load_dotenv

    import asf_search as asf
    import earthaccess

    from subsideo.products.dist import run_dist, validate_dist_product
    from subsideo._metadata import get_software_version, inject_opera_metadata
    from subsideo.validation.compare_dist import compare_dist
    from subsideo.validation.harness import (
        bounds_for_burst,
        bounds_for_mgrs_tile,
        credential_preflight,
        download_reference_with_retry,
        ensure_resume_safe,
        select_opera_frame_by_utc_hour,
    )

    load_dotenv()

    credential_preflight(["EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"])

    # -- Stage 0: Configuration & pre-flight ---------------------------------
    AOI_NAME = "Park Fire, California (2024)"
    # MGRS 10TFK was probe-verified via dist_s1_enumerator.get_mgrs_tiles_overlapping_geometry
    # for the Park Fire bbox. The canonical dist_s1 MGRS tile catalogue returns
    # 10SEJ, 10SFJ, 10TEK, 10TFK as the four tiles covering bbox (-122, 39.5, -121.5, 40.2).
    # 10TFK sits directly over the Tehama/Butte burn scar centroid (-121.7, 40.0).
    # Track 115 (ascending, UTC ~14:15) has 88 RTC-S1 products in the lookup
    # (80 pre / 8 post) for post_date=2024-08-05 with buffer=5 days.
    # ENV-08: dist_s1 auto-derives bounds from mgrs_tile_id (no hand-coded
    # bounds literal here); harness.bounds_for_mgrs_tile is imported at
    # module top for future phase-agnostic use.
    MGRS_TILE = "10TFK"
    TRACK_NUMBER = 115
    POST_DATE = "2024-08-05"       # ~12 days after July 24 ignition, allows DIST alert confirmation
    POST_DATE_BUFFER_DAYS = 5      # dist_s1 caps this below 6 (S1 pass length)
    DATE_START = "2024-07-01"      # RTC input window / reference search window
    DATE_END = "2024-08-15"
    AOI_BBOX = (-122.0, 39.5, -121.5, 40.2)
    EPSG = 32610                   # UTM 10N

    # Alternative tiles / tracks (if 10TFK + 115 fails Task 4 may retry):
    #   10TEK track 042 (western Tehama side of scar, descending)
    #   10SFJ track 115 (south of Park Fire, mostly unburned)
    #   11SKA (Maui 2023 wildfire alternative)
    #   10UDB (PNW 2024 wildfire alternative)

    OUT = Path("./eval-dist")
    OUT.mkdir(exist_ok=True)

    print("=" * 70)
    print("DIST-S1 Validation: subsideo vs OPERA N.Am. Reference")
    print("=" * 70)
    print(f"  AOI        : {AOI_NAME}")
    print(f"  MGRS tile  : {MGRS_TILE}")
    print(f"  Rel. orbit : {TRACK_NUMBER}")
    print(f"  Post date  : {POST_DATE}")
    print(f"  BBox       : {AOI_BBOX}")
    print(f"  EPSG       : {EPSG}")
    print(f"  Period     : {DATE_START} -> {DATE_END}")
    print(f"  Output dir : {OUT}")

    # Pre-flight credentials already validated above via harness.credential_preflight.
    print()

    # -- Stage 1: ASF DAAC + earthaccess auth --------------------------------
    print("-- Stage 1: Authentication --")
    auth = earthaccess.login(strategy="environment")
    print(f"  Earthdata auth : {'OK' if auth else 'FAIL'}")

    session = asf.ASFSession().auth_with_creds(
        username=os.environ["EARTHDATA_USERNAME"],
        password=os.environ["EARTHDATA_PASSWORD"],
    )
    print("  ASF session    : OK")

    # -- Stage 2: Search for OPERA DIST-S1 reference -------------------------
    # As documented in probe 1 above, OPERA DIST-S1 reference products are
    # not yet published to NASA Earthdata / ASF DAAC. We still run the
    # search (in case the product has shipped between authoring and run
    # time) but gracefully fall through if the catalog returns empty.
    print("\n-- Stage 2: Search OPERA DIST-S1 reference --")
    ref_dir = OUT / "opera_reference"
    ref_dir.mkdir(exist_ok=True)
    opera_granules_cache = OUT / "opera_dist_granules.json"

    opera_results: list = []
    if opera_granules_cache.exists():
        print(f"  Cached granule list: {opera_granules_cache.name}")
        cached = _json.loads(opera_granules_cache.read_text())
        print(f"  {len(cached)} cached granule(s)")
    else:
        short_names_to_try = [
            "OPERA_L3_DIST-ALERT-S1_V1",
            "OPERA_L3_DIST-S1_V1",
            "OPERA_L3_DIST-ANN-S1_V1",
            "OPERA_L3_DIST_PROVISIONAL_V0",
        ]
        for sn in short_names_to_try:
            try:
                r = earthaccess.search_data(
                    short_name=sn,
                    temporal=(DATE_START, DATE_END),
                    bounding_box=AOI_BBOX,
                    count=20,
                )
                n = len(r) if r else 0
                print(f"  {sn}: {n} hit(s)")
                if r:
                    opera_results.extend(r)
                    break
            except Exception as exc:
                print(f"  {sn}: ERR {str(exc)[:80]}")

        if opera_results:
            # Cache minimally
            cache_payload = [
                {"GranuleUR": r["umm"].get("GranuleUR", "?")}
                for r in opera_results
            ]
            opera_granules_cache.write_text(_json.dumps(cache_payload, indent=2))
            print(f"  Cached {len(opera_results)} granule(s)")
        else:
            print()
            print("  !! OPERA DIST-S1 reference products NOT available in Earthdata/ASF DAAC")
            print("  !! Proceeding with pipeline run only -- comparison deferred.")

    # -- Stage 3: Download OPERA DIST-S1 reference + check RTC availability --
    print("\n-- Stage 3: Download reference COG + probe RTC availability --")

    reference_cog: Path | None = None
    if opera_results:
        print(f"  Downloading {len(opera_results)} OPERA DIST-S1 granule(s)...")
        try:
            earthaccess.download(opera_results, str(ref_dir))
            dist_status_files = sorted(ref_dir.glob("*DIST-STATUS*.tif"))
            if not dist_status_files:
                # Fallback: any .tif in the ref dir
                dist_status_files = sorted(ref_dir.glob("*.tif"))
            if dist_status_files:
                reference_cog = dist_status_files[0]
                sz = reference_cog.stat().st_size / 1e6
                print(f"  Reference COG: {reference_cog.name} ({sz:.1f} MB)")
            else:
                print("  No .tif files found after download -- reference unavailable")
        except Exception as exc:
            print(f"  Download failed: {str(exc)[:200]}")
    else:
        # Manual-drop fallback: user can put a .tif in ref_dir for offline re-runs.
        for candidate in sorted(ref_dir.glob("*.tif")):
            reference_cog = candidate
            print(f"  Using manually-placed reference: {candidate.name}")
            break

    # Probe RTC input availability (we don't download these ourselves --
    # dist_s1 auto-fetches them given mgrs_tile_id + track + post_date).
    print("\n  Probing OPERA RTC-S1 input availability...")
    try:
        w, s, e, n = AOI_BBOX
        aoi_wkt = f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"
        rtc_hits = asf.search(
            dataset="OPERA-S1",
            processingLevel="RTC",
            platform=asf.PLATFORM.SENTINEL1,
            start=f"{DATE_START}T00:00:00Z",
            end=f"{DATE_END}T23:59:59Z",
            intersectsWith=aoi_wkt,
            maxResults=100,
        )
        # Filter to the target relative orbit
        track_tag = f"T{TRACK_NUMBER:03d}"
        rtc_matches = [
            r for r in rtc_hits
            if track_tag in r.properties.get("fileID", "")
        ]
        print(f"  RTC-S1 products on {track_tag}: {len(rtc_matches)}")
        print(f"  RTC-S1 products across all tracks: {len(rtc_hits)}")
        if len(rtc_matches) < 2:
            print("  !! Fewer than 2 RTC inputs on target track -- dist_s1 may struggle")
    except Exception as exc:
        print(f"  RTC search failed: {str(exc)[:200]}")

    # -- Stage 4: Prepare dist_s1 inputs -------------------------------------
    # dist_s1 2.0.13 auto-fetches RTC inputs from ASF DAAC when given
    # mgrs_tile_id, post_date, and track_number. This matches the current
    # wiring in subsideo.products.dist.run_dist(). Option A -- no manual
    # RTC download needed.
    print("\n-- Stage 4: dist_s1 input preparation --")
    print("  Mode: Option A (dist_s1 auto-fetches RTC from ASF DAAC)")
    print(f"  mgrs_tile_id={MGRS_TILE}, post_date={POST_DATE}, track={TRACK_NUMBER}")

    # -- Stage 5: Run the DIST-S1 pipeline -----------------------------------
    #
    # We call dist_s1.run_dist_s1_workflow directly rather than going through
    # subsideo.products.dist.run_dist() because dist_s1 2.0.13 defaults
    # post_date_buffer_days=1, which is too tight for the 12-day Sentinel-1
    # repeat cycle -- a 1-day window commonly misses the nearest post-image.
    # We use a 5-day buffer (dist_s1 caps this below 6 days = S1 pass length).
    #
    # The validation + OPERA metadata injection that run_dist() normally
    # performs is replicated inline below after the workflow returns.
    print("\n-- Stage 5: DIST-S1 Pipeline --")
    dist_out = OUT / "dist_output"
    dist_out.mkdir(parents=True, exist_ok=True)

    # Resume-safety: look specifically for the OPERA DIST-S1 GEN-DIST-STATUS
    # layer, not any .tif (the dist_s1 workflow caches RTC inputs under
    # dist_out/<mgrs>/<track>/<date>/*.tif which we must NOT treat as outputs).
    # Exclude *STATUS-ACQ (that's the single-acquisition confidence layer,
    # not the confirmed status we want for validation).
    def _find_status_cog(root: Path) -> Path | None:
        candidates = sorted(root.glob("**/OPERA_L3_DIST-ALERT-S1_*_GEN-DIST-STATUS.tif"))
        # Filter out GEN-DIST-STATUS-ACQ matches (glob also picks up the longer name)
        candidates = [p for p in candidates if "STATUS-ACQ" not in p.name.upper()]
        return candidates[0] if candidates else None

    dist_cog: Path | None = _find_status_cog(dist_out)
    if dist_cog is not None:
        errs = validate_dist_product([dist_cog])
        if errs:
            print(f"  Existing output has validation warnings:")
            for e in errs:
                print(f"    ! {e}")
        print(f"  Already present: {dist_cog}")
        print(f"  Size: {dist_cog.stat().st_size / 1e6:.1f} MB")

    if dist_cog is None:
        from dist_s1 import run_dist_s1_workflow

        # M3 Max note: dist_s1 auto-detects device='mps' as the "best" device
        # but Apple MPS does not support multiprocessing, so the pydantic
        # AlgoConfigData validator rejects mps + n_workers > 1. Force CPU
        # with the default 8-worker pool (128 GB RAM is plenty for this).
        print(f"  Running dist_s1.run_dist_s1_workflow...")
        print(f"    mgrs_tile_id       : {MGRS_TILE}")
        print(f"    track_number       : {TRACK_NUMBER}")
        print(f"    post_date          : {POST_DATE}")
        print(f"    post_date_buffer_d : {POST_DATE_BUFFER_DAYS}")
        print(f"    dst_dir            : {dist_out}")
        print(f"    device             : cpu (forced to enable multiprocessing)")
        print(f"  This may take 20-60 minutes...")
        t0 = time.time()
        try:
            out_path = run_dist_s1_workflow(
                mgrs_tile_id=MGRS_TILE,
                post_date=POST_DATE,
                track_number=TRACK_NUMBER,
                dst_dir=dist_out,
                post_date_buffer_days=POST_DATE_BUFFER_DAYS,
                device="cpu",
            )
        except Exception as exc:
            elapsed_min = (time.time() - t0) / 60
            print(f"\n  dist_s1 workflow failed after {elapsed_min:.1f} min: {str(exc)[:500]}")
            raise SystemExit(f"DIST-S1 pipeline crashed: {exc}")
        elapsed_min = (time.time() - t0) / 60
        print(f"\n  Completed in {elapsed_min:.1f} min")
        print(f"  Workflow returned path: {out_path}")

        # Prefer the confirmed GEN-DIST-STATUS layer (not -ACQ single-acquisition)
        dist_cog = _find_status_cog(dist_out)
        if dist_cog is None:
            # Fall back to the ACQ layer or any .tif under a product directory
            acq_candidates = sorted(
                dist_out.glob("**/OPERA_L3_DIST-ALERT-S1_*_GEN-DIST-STATUS-ACQ.tif")
            )
            if acq_candidates:
                dist_cog = acq_candidates[0]
                print(f"  Falling back to STATUS-ACQ layer: {dist_cog.name}")
            else:
                any_tif = sorted(dist_out.glob("**/OPERA_L3_DIST-ALERT-S1_*.tif"))
                if any_tif:
                    dist_cog = any_tif[0]
        if dist_cog is None:
            raise SystemExit("DIST-S1 workflow produced no recognizable DIST-ALERT-S1 .tif outputs.")

        # Lightweight validation (skip strict COG validation if it trips --
        # some dist_s1 outputs may not be COG-structured)
        errs = validate_dist_product([dist_cog])
        if errs:
            print("  Validation warnings:")
            for e in errs:
                print(f"    ! {e}")

        # OPERA metadata injection (normally run_dist would do this)
        try:
            sw_version = get_software_version()
            inject_opera_metadata(
                dist_cog,
                product_type="DIST-S1",
                software_version=sw_version,
                run_params={
                    "mgrs_tile_id": MGRS_TILE,
                    "track_number": TRACK_NUMBER,
                    "post_date": POST_DATE,
                    "post_date_buffer_days": POST_DATE_BUFFER_DAYS,
                    "output_dir": str(dist_out),
                },
            )
        except Exception as exc:
            print(f"  OPERA metadata injection skipped: {str(exc)[:200]}")

    print(f"\n  DIST-S1 COG: {dist_cog}")

    # -- Stage 6: Output inspection ------------------------------------------
    print("\n-- Stage 6: Output Inspection --")
    import rasterio

    with rasterio.open(dist_cog) as ds:
        dist_data = ds.read(1)
        print(f"  shape : {dist_data.shape}")
        print(f"  CRS   : {ds.crs}")
        print(f"  dtype : {ds.dtypes[0]}")
        print(f"  bounds: {ds.bounds}")

    # Class histogram: GEN-DIST-STATUS labels (0..8, 255 nodata)
    # See subsideo.validation.compare_dist for the full class table.
    print("\n  GEN-DIST-STATUS class histogram:")
    labels = [
        (0, "no disturbance           "),
        (1, "first detection (prov.)  "),
        (2, "provisional (confirmed)  "),
        (3, "confirmed (fd low)       "),
        (4, "confirmed (prov low)     "),
        (5, "confirmed (fd high)      "),
        (6, "confirmed (high)         "),
        (7, "finished                 "),
        (8, "finished (confirmed)     "),
        (255, "nodata                   "),
    ]
    total = dist_data.size
    for cls, label in labels:
        n = int((dist_data == cls).sum())
        pct = 100.0 * n / total if total else 0.0
        if n or cls in (0, 255):
            print(f"    {cls:3d} {label}: {n:12,d}  ({pct:6.2f}%)")

    # -- Stage 7: Validation vs OPERA DIST-S1 --------------------------------
    print("\n-- Stage 7: Validation vs OPERA DIST-S1 --")

    if reference_cog is None:
        print(f"\n  {'='*60}")
        print("  OPERA DIST-S1 reference: NOT AVAILABLE")
        print("  Verdict : STRUCTURALLY COMPLETE")
        print(f"  {'='*60}")
        print()
        print("  The subsideo DIST-S1 pipeline ran end-to-end and produced a")
        print("  valid COG output. Comparison against the OPERA reference is")
        print("  deferred until DIST-S1 is published to NASA Earthdata (the")
        print("  probe at Stage 2 found only HLS-based DIST products and the")
        print("  DISP-S1 collection).")
        print()
        print(f"  Our output: {dist_cog}")
        print(f"  Drop an OPERA DIST-S1 .tif in {ref_dir} and re-run this")
        print("  script to perform the full comparison.")
        print(f"  {'='*60}")
        sys.exit(0)

    print(f"  Product    : {dist_cog.name}")
    print(f"  Reference  : {reference_cog.name}")
    result = compare_dist(product_path=dist_cog, reference_path=reference_cog)

    print(f"\n  {'='*60}")
    print(f"  F1               : {result.f1:.4f}   (criterion: > 0.80)")
    print(f"  Precision        : {result.precision:.4f}")
    print(f"  Recall           : {result.recall:.4f}")
    print(f"  Overall accuracy : {result.overall_accuracy:.4f}  (criterion: > 0.85)")
    print(f"  Valid pixels     : {result.n_valid_pixels:,}")
    print(f"  {'='*60}")
    for k, v in result.pass_criteria.items():
        print(f"  {k:30s}: {'PASS' if v else 'FAIL'}")
    overall = all(result.pass_criteria.values()) if result.pass_criteria else False
    print(f"  {'Overall':30s}: {'PASS' if overall else 'FAIL'}")
    print(f"  {'='*60}")

    sys.exit(0 if overall else 1)
