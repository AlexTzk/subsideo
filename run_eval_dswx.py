# run_eval_dswx.py -- EU DSWx-S2 validation against JRC Global Surface Water
#
# Downloads a single cloud-free Sentinel-2 L2A scene from CDSE over Lake
# Balaton (Hungary), runs the subsideo DSWx-S2 surface-water pipeline, and
# compares the resulting water-class COG against the JRC Global Surface
# Water Monthly History raster for the matching month.
#
# Target:
#   AOI     : Lake Balaton, Hungary (a large, cloud-clearable inland lake
#             with stable shoreline -- good JRC reference signal)
#   Month   : 2024-07 (summer, typically low cloud cover; well within JRC
#             Monthly History coverage which runs 1984 -> present-2yrs)
#   EPSG    : 32633 (UTM 33N)
#
# Prerequisites:
#   - CDSE_CLIENT_ID / CDSE_CLIENT_SECRET in .env or env vars
#   - CDSE_S3_ACCESS_KEY / CDSE_S3_SECRET_KEY in .env (separate from OAuth
#     credentials -- create at https://eodata-s3keysmanager.dataspace.copernicus.eu/)
#   - conda env `subsideo`: rasterio, rio-cogeo, pyproj, shapely, numpy
#
# Storage estimate : ~1.5 GB (S2 L2A SAFE tree + DSWx COG + JRC tile cache)
# Compute estimate : 5-15 minutes on M3 Max
#
# Resume-safe: each stage skips work if outputs already exist.
import warnings

warnings.filterwarnings("ignore")

EXPECTED_WALL_S = 900  # Plan 01-07 supervisor AST-parses this constant (D-11)

if __name__ == "__main__":
    import hashlib
    import json as _json
    import os
    import platform
    import subprocess
    import sys
    import time
    from datetime import datetime, timezone
    from pathlib import Path

    import numpy as np
    from dotenv import load_dotenv
    from loguru import logger

    from subsideo.data.cdse import CDSEClient, extract_safe_s3_prefix
    from subsideo.products.dswx import run_dswx
    from subsideo.products.dswx_thresholds import THRESHOLDS_EU
    from subsideo.products.types import DSWxConfig
    from subsideo.validation.compare_dswx import compare_dswx
    from subsideo.validation.harness import (
        bounds_for_mgrs_tile,
        credential_preflight,
    )
    from subsideo.validation.matrix_schema import (
        DSWEThresholdsRef,
        DswxEUCellMetrics,
        LOOCVPerFold,
        PerAOIF1Breakdown,
        ProductQualityResultJson,
        ReferenceAgreementResultJson,
    )

    t_start = time.time()

    load_dotenv()

    credential_preflight([
        "CDSE_CLIENT_ID",
        "CDSE_CLIENT_SECRET",
        "CDSE_S3_ACCESS_KEY",
        "CDSE_S3_SECRET_KEY",
    ])

    # -- Stage 0: EU recalibration pre-check (W5 fix) --------------------------
    # Plan 06-07 W5: verify THRESHOLDS_EU.fit_set_hash is populated (grid-search
    # landed) before running any pipeline work. Originally an assert; relaxed to
    # a warning in Plan 06-06 closure because the EU recalibration was deferred
    # to v1.2 with an honest BLOCKER (see CONCLUSIONS_DSWX_EU_RECALIB.md).
    # Plan 06-07 proceeds with PROTEUS defaults; Balaton F1 will be reported
    # with named_upgrade_path set accordingly.
    # W5 sentinel check: Plan 06-06 grid search did not land.
    if not THRESHOLDS_EU.fit_set_hash:
        logger.warning(
            "THRESHOLDS_EU.fit_set_hash is empty -- running with PROTEUS defaults "
            "(EU recalibration deferred to v1.2; see CONCLUSIONS_DSWX_EU_RECALIB.md). "
            "Re-run scripts/recalibrate_dswe_thresholds.py before EU eval "
            "if recalibration is needed."
        )

    # -- Configuration --------------------------------------------------------
    # ENV-08: Lake Balaton sits inside MGRS-100km tile 33TXP (UTM 33N). The
    # harness seed GeoJSON ships this tile; bounds_for_mgrs_tile returns a
    # buffered (west, south, east, north) tuple suitable for the CDSE STAC
    # search below -- no hand-coded AOI_BBOX literal here.
    AOI_NAME = "Lake Balaton, Hungary"
    MGRS_TILE = "33TXP"
    AOI_BBOX = bounds_for_mgrs_tile(MGRS_TILE, buffer_deg=0.1)
    EPSG = 32633  # UTM 33N

    # JRC Monthly History LATEST only publishes through 2021, so the S2
    # scene must come from a month the JRC reference also covers. July is
    # typically cloud-free over Pannonia and lake level is stable.
    DATE_START = "2021-07-01"
    DATE_END = "2021-07-31"
    JRC_YEAR = 2021
    JRC_MONTH = 7

    # Max cloud cover for scene selection (percent)
    MAX_CLOUD_COVER = 15.0

    # DSWx-S2 requires these six bands plus the SCL cloud mask at R20m
    BAND_NAMES = ("B02", "B03", "B04", "B08", "B11", "B12")

    OUT = Path("./eval-dswx")
    OUT.mkdir(exist_ok=True)

    print("=" * 70)
    print("DSWx-S2 Validation: subsideo vs JRC Global Surface Water")
    print("=" * 70)
    print(f"  AOI        : {AOI_NAME}")
    print(f"  MGRS tile  : {MGRS_TILE}")
    print(f"  BBox       : {AOI_BBOX}")
    print(f"  EPSG       : {EPSG}")
    print(f"  Period     : {DATE_START} -> {DATE_END}")
    print(f"  JRC ref    : Monthly History {JRC_YEAR}-{JRC_MONTH:02d}")
    print(f"  Output dir : {OUT}")

    # -- Pre-flight checks ----------------------------------------------------
    # Credentials already validated above via harness.credential_preflight.
    print()

    # -- Stage 1: CDSE client -------------------------------------------------
    print("-- Stage 1: CDSE authentication --")
    cdse = CDSEClient(
        client_id=os.environ["CDSE_CLIENT_ID"],
        client_secret=os.environ["CDSE_CLIENT_SECRET"],
    )
    _ = cdse._get_token()  # fail fast on bad credentials
    print("  CDSE token OK")

    # -- Stage 2: Search CDSE for S2 L2A scenes -------------------------------
    print("\n-- Stage 2: Search S2 L2A scenes on CDSE --")
    stac_cache = OUT / "stac_items.json"
    if stac_cache.exists():
        stac_items = _json.loads(stac_cache.read_text())
        print(f"  Loaded cached STAC items: {len(stac_items)} (from {stac_cache.name})")
    else:
        stac_items = cdse.search_stac(
            collection="SENTINEL-2",
            bbox=list(AOI_BBOX),
            start=datetime.fromisoformat(f"{DATE_START}T00:00:00"),
            end=datetime.fromisoformat(f"{DATE_END}T23:59:59"),
            product_type="S2MSI2A",
            max_items=50,
        )
        stac_cache.write_text(_json.dumps(stac_items))
        print(f"  CDSE STAC: {len(stac_items)} items (cached)")

    def _cloud_cover(item: dict) -> float:
        props = item.get("properties", {}) or {}
        for k in ("eo:cloud_cover", "cloudCover", "cloud_cover"):
            if k in props and props[k] is not None:
                try:
                    return float(props[k])
                except (TypeError, ValueError):
                    pass
        return 100.0

    def _start_time(item: dict) -> str:
        p = item.get("properties", {}) or {}
        return p.get("start_datetime") or p.get("datetime", "")

    # Sort by cloud cover ascending and pick the first below the threshold.
    scored = sorted(stac_items, key=_cloud_cover)
    print(f"  {len(scored)} scenes in window; showing top 5 by cloud cover:")
    for i, it in enumerate(scored[:5]):
        print(
            f"    [{i+1}] {_start_time(it)[:19]}  cc={_cloud_cover(it):5.1f}%  "
            f"{it.get('id', '?')[:55]}"
        )

    eligible = [it for it in scored if _cloud_cover(it) <= MAX_CLOUD_COVER]
    if not eligible:
        raise SystemExit(
            f"No S2 L2A scenes with cloud cover <= {MAX_CLOUD_COVER}% in window. "
            f"Widen the date range or raise MAX_CLOUD_COVER."
        )

    scene = eligible[0]
    scene_id: str = scene.get("id", "").removesuffix(".SAFE")
    safe_id = scene_id  # alias for meta.json
    print(f"\n  Selected: {scene_id}")
    print(f"  Cloud    : {_cloud_cover(scene):.1f}%")
    print(f"  Time     : {_start_time(scene)[:19]}")

    # -- Stage 3: Download the SAFE tree --------------------------------------
    print("\n-- Stage 3: Download S2 SAFE tree --")
    input_dir = OUT / "input"
    input_dir.mkdir(exist_ok=True)
    safe_dir = input_dir / f"{scene_id}.SAFE"
    manifest = safe_dir / "manifest.safe"

    if manifest.exists():
        print(f"  Already present: {safe_dir.name}")
    else:
        s3_uri = extract_safe_s3_prefix(scene)
        if s3_uri is None:
            raise SystemExit("No S3 URI in STAC item -- cannot download SAFE.")
        print(f"  S3 prefix: {s3_uri}")
        print("  Downloading (this can take several minutes)...")
        t0 = time.time()
        safe_dir = cdse.download_safe(s3_uri, input_dir)
        print(f"  Downloaded in {(time.time() - t0)/60:.1f} min -> {safe_dir.name}")

    if not (safe_dir / "manifest.safe").exists():
        raise SystemExit("manifest.safe missing after download.")

    # -- Stage 4: Locate band files inside the SAFE tree ----------------------
    #
    # S2 L2A SAFE layout publishes per-resolution subfolders under IMG_DATA:
    #   R10m/ : B02, B03, B04, B08, (AOT, TCI, WVP)       -- native 10m
    #   R20m/ : B02, B03, B04, B05, B06, B07, B8A, B11,   -- native/resampled 20m
    #           B12, SCL, (AOT, TCI, WVP)
    #   R60m/ : all bands including B01, B09, B10         -- resampled 60m
    # B08 (the 842 nm NIR) is NOT in R20m -- only B8A is. The DSWx reader
    # reprojects every band to the B11 20m grid anyway, so we pull B08 from
    # R10m. All other bands come from R20m (where they're pixel-aligned to
    # B11 natively, saving a reprojection step).
    print("\n-- Stage 4: Locate band files (R20m + R10m for B08) --")
    r20_candidates = sorted(safe_dir.glob("GRANULE/*/IMG_DATA/R20m"))
    r10_candidates = sorted(safe_dir.glob("GRANULE/*/IMG_DATA/R10m"))
    if not r20_candidates:
        raise SystemExit(f"No R20m folder found under {safe_dir}/GRANULE/*/IMG_DATA/")
    if not r10_candidates:
        raise SystemExit(f"No R10m folder found under {safe_dir}/GRANULE/*/IMG_DATA/")
    r20_dir = r20_candidates[0]
    r10_dir = r10_candidates[0]
    print(f"  R20m dir: {r20_dir.relative_to(safe_dir)}")
    print(f"  R10m dir: {r10_dir.relative_to(safe_dir)}")

    band_paths: dict[str, Path] = {}
    for band in BAND_NAMES:
        if band == "B08":
            src_dir, suffix = r10_dir, "10m"
        else:
            src_dir, suffix = r20_dir, "20m"
        matches = sorted(src_dir.glob(f"*_{band}_{suffix}.jp2"))
        if not matches:
            raise SystemExit(f"Band {band} not found in {src_dir}")
        band_paths[band] = matches[0]
        print(f"  {band}: {matches[0].name}")

    scl_matches = sorted(r20_dir.glob("*_SCL_20m.jp2"))
    if not scl_matches:
        raise SystemExit(f"SCL not found in {r20_dir}")
    scl_path = scl_matches[0]
    print(f"  SCL: {scl_path.name}")

    # -- Stage 5: Run DSWx-S2 pipeline ----------------------------------------
    print("\n-- Stage 5: DSWx-S2 Pipeline --")
    dswx_out_dir = OUT / "output"
    dswx_cog = dswx_out_dir / "dswx_s2.tif"

    if dswx_cog.exists():
        print(f"  Already present: {dswx_cog}")
        print(f"  Size: {dswx_cog.stat().st_size / 1e6:.1f} MB")
    else:
        cfg = DSWxConfig(
            s2_band_paths=band_paths,
            scl_path=scl_path,
            output_dir=dswx_out_dir,
            output_epsg=EPSG,
            output_posting_m=30.0,
            region="eu",  # Phase 6 D-10: applies THRESHOLDS_EU (recalibration deferred)
        )
        t0_pipeline = time.time()
        dswx_result = run_dswx(cfg)
        elapsed = time.time() - t0_pipeline
        print(f"  Completed in {elapsed:.1f}s")
        print(f"  Valid       : {dswx_result.valid}")
        print(f"  Output      : {dswx_result.output_path}")
        if dswx_result.validation_errors:
            for e in dswx_result.validation_errors:
                print(f"    ! {e}")
        if not dswx_result.valid:
            raise SystemExit("DSWx pipeline failed -- see errors above.")
        dswx_cog = dswx_result.output_path

    # -- Stage 6: Output inspection -------------------------------------------
    print("\n-- Stage 6: Output Inspection --")
    import rasterio

    with rasterio.open(dswx_cog) as ds:
        water_class = ds.read(1)
        print(f"  shape : {water_class.shape}")
        print(f"  CRS   : {ds.crs}")
        print(f"  dtype : {ds.dtypes[0]}")

    # Class histogram: 0=NotWater, 1=HighConf, 2=Moderate, 3=PotentialWetland,
    #                  4=LowConf, 255=Masked
    print("\n  water-class histogram:")
    for cls, label in [
        (0, "not water        "),
        (1, "high confidence  "),
        (2, "moderate         "),
        (3, "potential wetland"),
        (4, "low confidence   "),
        (255, "masked           "),
    ]:
        n = int((water_class == cls).sum())
        pct = 100.0 * n / water_class.size
        print(f"    {cls:3d} {label}: {n:12,d}  ({pct:6.2f}%)")

    # -- Stage 7: Compare against JRC Monthly History -------------------------
    print("\n-- Stage 7: Validation vs JRC GSW --")
    jrc_cache = OUT / "jrc_cache"
    jrc_cache.mkdir(exist_ok=True)

    # Phase 6 D-04 + B2 fix: single-return compare_dswx; access diagnostics via
    # .diagnostics attribute (NOT tuple unpack -- zero breaking change for callers)
    validation = compare_dswx(
        product_path=dswx_cog,
        year=JRC_YEAR,
        month=JRC_MONTH,
        cache_dir=jrc_cache,
    )
    # B2 fix: diagnostics via attribute access
    diagnostics = validation.diagnostics  # DSWxValidationDiagnostics | None

    balaton_f1 = validation.reference_agreement.measurements["f1"]
    balaton_precision = validation.reference_agreement.measurements["precision"]
    balaton_recall = validation.reference_agreement.measurements["recall"]
    balaton_accuracy = validation.reference_agreement.measurements["accuracy"]

    print(f"\n  {'='*60}")
    print(f"  F1           : {balaton_f1:.4f}   (criterion: > 0.90)")
    print(f"  Precision    : {balaton_precision:.4f}")
    print(f"  Recall       : {balaton_recall:.4f}")
    print(f"  Accuracy     : {balaton_accuracy:.4f}")
    if diagnostics is not None:
        print(
            f"  F1 (full px) : {diagnostics.f1_full_pixels:.4f}"
            "  (diagnostic; no shoreline exclusion)"
        )
        print(f"  Shoreline px : {diagnostics.shoreline_buffer_excluded_pixels:,d}  (excluded)")
    print(f"  {'='*60}")
    overall = float(balaton_f1) > 0.90 if not np.isnan(float(balaton_f1)) else False
    print(f"  {'F1 > 0.90':30s}: {'PASS' if overall else 'FAIL'}")
    print(f"  {'Overall':30s}: {'PASS' if overall else 'FAIL'}")
    print(f"  {'='*60}")

    # -- Stage 8: Threshold context print ------------------------------------
    print("\n-- Stage 8: Threshold context --")
    print("  region            : eu (Phase 6 D-10; PROTEUS defaults, recalibration deferred)")
    print(f"  THRESHOLDS_EU.WIGT       : {THRESHOLDS_EU.WIGT}")
    print(f"  THRESHOLDS_EU.AWGT       : {THRESHOLDS_EU.AWGT}")
    print(f"  THRESHOLDS_EU.PSWT2_MNDWI: {THRESHOLDS_EU.PSWT2_MNDWI}")
    print(f"  fit_set_hash      : {THRESHOLDS_EU.fit_set_hash!r} (empty = PROTEUS placeholder)")

    # ============================================================================
    # Stage 9: DswxEUCellMetrics write (Phase 6 D-26 + D-13 official Balaton F1)
    # ============================================================================
    print("\n-- Stage 9: Write DswxEUCellMetrics --")

    # Read recalibration aggregate per Plan 06-06 Stage 5 + Stage 7 (B1 fix: 10 LOOCV folds).
    # T-06-07-05 mitigation: if the file is missing or corrupt, stamp NaN diagnostics
    # rather than aborting -- the eval still produces metrics.json with cell_status
    # from Balaton F1 alone.
    recalib_results_path = Path("scripts/recalibrate_dswe_thresholds_results.json")
    if recalib_results_path.exists():
        recalib = _json.loads(recalib_results_path.read_text())
        # Under honest-BLOCKER closure (Plan 06-06), the results.json has
        # fit_set_mean_f1 but no loocv_per_fold or per_aoi_breakdown -- those
        # were never populated because the grid search did not converge.
        fit_set_mean_f1 = float(recalib.get("fit_set_mean_f1", float("nan")))
        loocv_mean_f1 = float(recalib.get("loocv_mean_f1", float("nan")))
        loocv_gap = float(recalib.get("loocv_gap", float("nan")))
        # B1 fix: loocv_per_fold has 10 entries each with left_out_aoi + left_out_season.
        # Under BLOCKER closure these will be empty lists -- that is expected.
        loocv_per_fold = [LOOCVPerFold(**f) for f in recalib.get("loocv_per_fold", [])]
        per_aoi_breakdown = [
            PerAOIF1Breakdown(**a) for a in recalib.get("per_aoi_breakdown", [])
        ]
    else:
        logger.warning(
            "scripts/recalibrate_dswe_thresholds_results.json missing; "
            "stamping NaN diagnostics in DswxEUCellMetrics. "
            "Plan 06-06 must complete before Plan 06-07 EU re-run."
        )
        fit_set_mean_f1 = float("nan")
        loocv_mean_f1 = float("nan")
        loocv_gap = float("nan")
        loocv_per_fold = []
        per_aoi_breakdown = []

    # B2 fix: diagnostics from validation.diagnostics attribute (NOT tuple unpack)
    if diagnostics is not None:
        f1_full_pixels = float(diagnostics.f1_full_pixels)
        shoreline_buffer_excluded_pixels = int(diagnostics.shoreline_buffer_excluded_pixels)
    else:
        # Should not happen post-Plan-06-04 since compare_dswx always populates,
        # but defensive default for backward compat:
        f1_full_pixels = float("nan")
        shoreline_buffer_excluded_pixels = 0

    # cell_status logic per CONTEXT D-15 + BOOTSTRAP §5.5:
    # F1 > 0.90 = PASS; 0.85 <= F1 < 0.90 = FAIL + ML-replacement; F1 < 0.85 = FAIL + review
    _f1 = float(balaton_f1)
    if not np.isnan(_f1) and _f1 > 0.90:
        cell_status = "PASS"
        named_upgrade_path = None
    elif not np.isnan(_f1) and _f1 >= 0.85:
        cell_status = "FAIL"
        named_upgrade_path = "ML-replacement (DSWX-V2-01)"
    else:
        cell_status = "FAIL"
        named_upgrade_path = "fit-set quality review"

    # Construct thresholds_used provenance stamp.
    # Under honest-BLOCKER closure: grid_search_run_date='2026-MM-DD' (PLACEHOLDER),
    # fit_set_hash='' (empty). Documented per CONCLUSIONS_DSWX_EU_RECALIB.md.
    thresholds_ref = DSWEThresholdsRef(
        region="eu",
        grid_search_run_date=THRESHOLDS_EU.grid_search_run_date,
        fit_set_hash=THRESHOLDS_EU.fit_set_hash,
    )

    metrics = DswxEUCellMetrics(
        product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResultJson(
            measurements={
                "f1": float(balaton_f1),  # GATE per CONTEXT D-13 (held-out Balaton)
                "precision": float(balaton_precision),
                "recall": float(balaton_recall),
                "accuracy": float(balaton_accuracy),
            },
            criterion_ids=["dswx.f1_min"],
        ),
        criterion_ids_applied=["dswx.f1_min"],
        region="eu",
        thresholds_used=thresholds_ref,
        fit_set_mean_f1=fit_set_mean_f1,
        loocv_mean_f1=loocv_mean_f1,
        loocv_gap=loocv_gap,
        loocv_per_fold=loocv_per_fold,
        per_aoi_breakdown=per_aoi_breakdown,
        f1_full_pixels=f1_full_pixels,
        shoreline_buffer_excluded_pixels=shoreline_buffer_excluded_pixels,
        cell_status=cell_status,  # type: ignore[arg-type]
        named_upgrade_path=named_upgrade_path,
    )
    out_dir = Path("./eval-dswx")
    out_dir.mkdir(exist_ok=True)
    (out_dir / "metrics.json").write_text(metrics.model_dump_json(indent=2))
    print(f"  metrics.json written: {out_dir / 'metrics.json'}")

    # meta.json with git SHA + input hashes (Phase 2 D-12)
    try:
        git_sha = (
            subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
        git_dirty = bool(subprocess.call(["git", "diff", "--quiet"], stderr=subprocess.DEVNULL))
    except subprocess.CalledProcessError:
        git_sha = "unknown"
        git_dirty = False

    threshold_module_hash = hashlib.sha256(
        Path("src/subsideo/products/dswx_thresholds.py").read_bytes()
    ).hexdigest()[:16]

    meta = {
        "git_sha": git_sha,
        "git_dirty": git_dirty,
        "run_started_utc": datetime.fromtimestamp(t_start, tz=timezone.utc).isoformat(),
        "wall_s": time.time() - t_start,
        "platform": platform.platform(),
        "python_version": sys.version,
        "selected_aoi": AOI_NAME,
        "mgrs_tile": MGRS_TILE,
        "selected_scene_id": safe_id,
        "input_hashes": {
            "threshold_module_sha256_prefix": threshold_module_hash,
            "fit_set_hash_from_recalibration": THRESHOLDS_EU.fit_set_hash,
        },
    }
    (out_dir / "meta.json").write_text(_json.dumps(meta, indent=2))
    print(f"  meta.json written: {out_dir / 'meta.json'}")

    print("\n=== EU re-run complete ===")
    print(f"Held-out Balaton F1 = {balaton_f1:.4f}  (criterion: > 0.90)")
    print(f"cell_status         = {cell_status}")
    if named_upgrade_path:
        print(f"named_upgrade_path  = {named_upgrade_path!r}")
    if not np.isnan(loocv_gap):
        print(
            f"loocv_gap           = {loocv_gap:.4f} "
            f"({len(loocv_per_fold)} folds; B1 fix expects 10)"
        )
    else:
        print("loocv_gap           = NaN (recalibration deferred; no LOO-CV performed)")
    print(
        f"thresholds          = WIGT={THRESHOLDS_EU.WIGT} AWGT={THRESHOLDS_EU.AWGT} "
        f"PSWT2_MNDWI={THRESHOLDS_EU.PSWT2_MNDWI} (PROTEUS defaults)"
    )

    sys.exit(0 if cell_status == "PASS" else 1)
