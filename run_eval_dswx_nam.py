# run_eval_dswx_nam.py -- N.Am. DSWx-S2 positive control against JRC Global Surface Water
#
# Phase 6 DSWX-01: positive-control eval that proves the v1.0 DSWx pipeline
# produces F1 > 0.90 against JRC over Tahoe (T10SFH primary) or Pontchartrain
# (T15RYP fallback). Runtime auto-pick by cloud-cover from a locked 2-element
# CANDIDATES list (CONTEXT D-18). F1 < 0.85 triggers BOA-offset / Claverie cross-cal
# / SCL-mask regression investigation (D-20) and halts EU recalibration via the
# metrics.json gate.
#
# CANDIDATES locked per Plan 06-01 dswx_fitset_aoi_candidates.md:
#   - Lake Tahoe (CA): MGRS 10SFH, EPSG 32610, July 2021
#   - Lake Pontchartrain (LA): MGRS 15RYP, EPSG 32615, July 2021
#
# Prerequisites:
#   - CDSE_CLIENT_ID / CDSE_CLIENT_SECRET in .env or env vars
#   - CDSE_S3_ACCESS_KEY / CDSE_S3_SECRET_KEY in .env (separate from OAuth)
#   - conda env `subsideo`: rasterio, rioxarray, pyproj, shapely, numpy, scipy
#
# Storage estimate : ~1.5 GB (S2 L2A SAFE + DSWx COG + JRC tile cache)
# Compute estimate : 10-30 minutes on M3 Max (cold path)
#
# Resume-safe: each stage skips work if outputs already exist.
import warnings; warnings.filterwarnings("ignore")  # noqa: E702, I001

EXPECTED_WALL_S = 1800   # 30 min cold path; supervisor 2x = 1 hr abort (CONTEXT D-24)


if __name__ == "__main__":
    # Phase 1 ENV-04 mandatory: PITFALLS P0.1 binding pre-condition.
    from subsideo._mp import configure_multiprocessing
    configure_multiprocessing()

    import hashlib
    import json as _json
    import os
    import platform
    import subprocess
    import sys
    import time
    from dataclasses import dataclass
    from datetime import datetime, timezone
    from pathlib import Path
    from typing import Literal

    from dotenv import load_dotenv
    from loguru import logger

    from subsideo.data.cdse import CDSEClient, extract_safe_s3_prefix
    from subsideo.products.dswx import run_dswx
    from subsideo.products.types import DSWxConfig
    from subsideo.validation.compare_dswx import compare_dswx
    from subsideo.validation.harness import (
        bounds_for_mgrs_tile,
        credential_preflight,
    )
    from subsideo.validation.matrix_schema import (
        DswxNamCellMetrics,
        ProductQualityResultJson,
        ReferenceAgreementResultJson,
        RegressionDiagnostic,
    )

    load_dotenv()
    credential_preflight([
        "CDSE_CLIENT_ID", "CDSE_CLIENT_SECRET",
        "CDSE_S3_ACCESS_KEY", "CDSE_S3_SECRET_KEY",
    ])

    run_started = datetime.now(timezone.utc)
    t_start = time.time()

    print("=" * 70)
    print("DSWx-S2 N.Am. Positive Control: subsideo vs JRC Global Surface Water")
    print("=" * 70)
    print("  Phase 6 DSWX-01: F1 > 0.90 binding criterion")
    print("  CANDIDATES: Lake Tahoe (CA) primary, Lake Pontchartrain (LA) fallback")

    # -------------------------------------------------------------------------
    # AOIConfig declarative structure (D-18 CANDIDATES pattern)
    # -------------------------------------------------------------------------

    @dataclass(frozen=True)
    class AOIConfig:
        """Per-candidate declarative config (CONTEXT D-18)."""

        aoi_name: str
        mgrs_tile: str
        epsg: int
        date_start: str
        date_end: str
        jrc_year: int
        jrc_month: int
        max_cloud_cover: float

    # CANDIDATES locked per Plan 06-01 dswx_fitset_aoi_candidates.md (D-18):
    CANDIDATES: list[AOIConfig] = [
        AOIConfig(
            aoi_name="Lake Tahoe (CA)",
            mgrs_tile="10SFH",   # Plan 06-01 verified via USGS ScienceBase
            epsg=32610,
            date_start="2021-07-01",
            date_end="2021-07-31",
            jrc_year=2021,
            jrc_month=7,
            max_cloud_cover=15.0,
        ),
        AOIConfig(
            aoi_name="Lake Pontchartrain (LA)",
            mgrs_tile="15RYP",   # Plan 06-01 verified via STAC (or T15RYR if STAC flipped)
            epsg=32615,
            date_start="2021-07-01",
            date_end="2021-07-31",
            jrc_year=2021,
            jrc_month=7,
            max_cloud_cover=15.0,
        ),
    ]

    # DSWx-S2 requires these six bands plus the SCL cloud mask
    BAND_NAMES = ("B02", "B03", "B04", "B08", "B11", "B12")

    CACHE = Path("./eval-dswx_nam")
    CACHE.mkdir(exist_ok=True)

    # -------------------------------------------------------------------------
    # Stage 1: CDSE authentication
    # -------------------------------------------------------------------------
    print("\n-- Stage 1: CDSE authentication --")
    cdse_client_id = os.environ["CDSE_CLIENT_ID"]
    cdse_client_secret = os.environ["CDSE_CLIENT_SECRET"]
    cdse = CDSEClient(client_id=cdse_client_id, client_secret=cdse_client_secret)
    _ = cdse._get_token()  # fail fast on bad credentials
    print("  CDSE token OK")

    # -------------------------------------------------------------------------
    # Stage 2: AOI candidate iteration (D-18 cloud-cover first-winner logic)
    # -------------------------------------------------------------------------
    print("\n-- Stage 2: CANDIDATES iteration (cloud-cover first-winner) --")
    selected_aoi: AOIConfig | None = None
    selected_scene: dict | None = None
    candidates_attempted: list[dict] = []

    def _cloud_cover(item: dict) -> float:
        props = item.get("properties", {}) or {}
        for k in ("eo:cloud_cover", "cloudCover", "cloud_cover"):
            if k in props and props[k] is not None:
                try:
                    return float(props[k])
                except (TypeError, ValueError):
                    pass
        return 100.0

    for cand in CANDIDATES:
        try:
            logger.info("-- Candidate: {} (MGRS {}) --", cand.aoi_name, cand.mgrs_tile)
            bbox = bounds_for_mgrs_tile(cand.mgrs_tile, buffer_deg=0.1)
            stac_cache = CACHE / f"stac_{cand.mgrs_tile}.json"
            if stac_cache.exists():
                stac_items = _json.loads(stac_cache.read_text())
                logger.info("  Loaded cached STAC items: {} ({})", len(stac_items), stac_cache.name)
            else:
                stac_items = cdse.search_stac(
                    collection="SENTINEL-2",
                    bbox=list(bbox),
                    start=datetime.fromisoformat(f"{cand.date_start}T00:00:00"),
                    end=datetime.fromisoformat(f"{cand.date_end}T23:59:59"),
                    product_type="S2MSI2A",
                    max_items=50,
                )
                stac_cache.write_text(_json.dumps(stac_items))

            cloud_free = [
                it for it in stac_items
                if _cloud_cover(it) <= cand.max_cloud_cover
            ]
            cloud_min = min(
                (_cloud_cover(it) for it in stac_items),
                default=100.0,
            )
            attempt_entry: dict = {
                "aoi_name": cand.aoi_name,
                "scenes_found": len(stac_items),
                "cloud_min": float(cloud_min),
            }
            candidates_attempted.append(attempt_entry)
            logger.info(
                "  {} scenes; {} cloud-free (cc <= {}%); min cc = {:.1f}%",
                len(stac_items), len(cloud_free), cand.max_cloud_cover, cloud_min,
            )

            if cloud_free:
                selected_aoi = cand
                selected_scene = sorted(cloud_free, key=_cloud_cover)[0]
                logger.info(
                    "  Selected: {} scene {} cc={:.1f}%",
                    cand.aoi_name,
                    selected_scene.get("id"),
                    _cloud_cover(selected_scene),
                )
                break
        except Exception as e:  # noqa: BLE001 -- per-candidate isolation
            logger.error("Candidate {} STAC search failed: {}", cand.aoi_name, e)
            candidates_attempted.append({
                "aoi_name": cand.aoi_name,
                "scenes_found": 0,
                "cloud_min": 100.0,
                "error": repr(e),
            })

    # BLOCKER path: both candidates failed STAC search (D-18 + threat T-06-05-04)
    if selected_aoi is None or selected_scene is None:
        metrics = DswxNamCellMetrics(
            product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
            reference_agreement=ReferenceAgreementResultJson(
                measurements={"f1": float("nan")},
                criterion_ids=["dswx.f1_min"],
            ),
            criterion_ids_applied=["dswx.f1_min"],
            selected_aoi="(none)",
            selected_scene_id="(none)",
            cloud_cover_pct=float("nan"),
            candidates_attempted=candidates_attempted,
            region="nam",
            cell_status="BLOCKER",
            named_upgrade_path=None,
            regression=RegressionDiagnostic(
                f1_below_regression_threshold=False,
                regression_diagnostic_required=[],
                investigation_resolved=False,
            ),
            # W2 fix: BLOCKER state -- diagnostics fields are None (no F1 computed)
            f1_full_pixels=None,
            shoreline_buffer_excluded_pixels=None,
        )
        (CACHE / "metrics.json").write_text(metrics.model_dump_json(indent=2))
        logger.error("BLOCKER: no candidate AOI found a cloud-free S2 scene in window")
        sys.exit(2)

    safe_id: str = selected_scene.get("id", "").removesuffix(".SAFE")
    scene_cloud_cover = _cloud_cover(selected_scene)

    print(f"\n  Selected AOI: {selected_aoi.aoi_name}")
    print(f"  Scene:        {safe_id}")
    print(f"  Cloud cover:  {scene_cloud_cover:.1f}%")

    # -------------------------------------------------------------------------
    # Stage 3: Download the SAFE tree
    # -------------------------------------------------------------------------
    print("\n-- Stage 3: Download S2 SAFE tree --")
    input_dir = CACHE / "input"
    input_dir.mkdir(exist_ok=True)
    safe_dir = input_dir / f"{safe_id}.SAFE"
    manifest = safe_dir / "manifest.safe"

    if manifest.exists():
        print(f"  Already present: {safe_dir.name}")
    else:
        s3_uri = extract_safe_s3_prefix(selected_scene)
        if s3_uri is None:
            raise SystemExit("No S3 URI in STAC item -- cannot download SAFE.")
        print(f"  S3 prefix: {s3_uri}")
        print("  Downloading (this can take several minutes)...")
        t_dl = time.time()
        safe_dir = cdse.download_safe(s3_uri, input_dir)
        print(f"  Downloaded in {(time.time() - t_dl)/60:.1f} min -> {safe_dir.name}")

    if not (safe_dir / "manifest.safe").exists():
        raise SystemExit("manifest.safe missing after download.")

    # -------------------------------------------------------------------------
    # Stage 4: Locate band files inside the SAFE tree
    # -------------------------------------------------------------------------
    # S2 L2A SAFE layout:
    #   R10m/ : B02, B03, B04, B08  -- native 10m
    #   R20m/ : B02, B03, B04, B05, B06, B07, B8A, B11, B12, SCL -- native/resampled 20m
    # B08 (842 nm NIR) is NOT in R20m -- only B8A is. DSWx reader reprojects
    # every band to B11 20m grid, so we pull B08 from R10m.
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

    # -------------------------------------------------------------------------
    # Stage 5: Run DSWx-S2 pipeline with region='nam' (Plan 06-03 region threading)
    # -------------------------------------------------------------------------
    print("\n-- Stage 5: DSWx-S2 Pipeline (region='nam') --")
    dswx_out_dir = CACHE / "output"
    dswx_out_dir.mkdir(exist_ok=True)
    dswx_cog = dswx_out_dir / "dswx_s2.tif"

    if dswx_cog.exists():
        print(f"  Already present: {dswx_cog}")
        print(f"  Size: {dswx_cog.stat().st_size / 1e6:.1f} MB")
        dswx_result_path = dswx_cog
    else:
        cfg = DSWxConfig(
            s2_band_paths=band_paths,
            scl_path=scl_path,
            output_dir=dswx_out_dir,
            output_epsg=selected_aoi.epsg,
            output_posting_m=30.0,
            region="nam",   # Phase 6 D-10: THRESHOLDS_NAM PROTEUS defaults applied
        )
        t_dswx = time.time()
        dswx_result = run_dswx(cfg)
        elapsed = time.time() - t_dswx
        print(f"  Completed in {elapsed:.1f}s")
        print(f"  Valid       : {dswx_result.valid}")
        print(f"  Output      : {dswx_result.output_path}")
        if dswx_result.validation_errors:
            for e in dswx_result.validation_errors:
                print(f"    ! {e}")
        if not dswx_result.valid or dswx_result.output_path is None:
            raise SystemExit("DSWx pipeline failed -- see errors above.")
        dswx_result_path = dswx_result.output_path

    # -------------------------------------------------------------------------
    # Stage 6: Output inspection
    # -------------------------------------------------------------------------
    print("\n-- Stage 6: Output Inspection --")
    import rasterio
    with rasterio.open(dswx_result_path) as ds:
        water_class = ds.read(1)
        print(f"  shape : {water_class.shape}")
        print(f"  CRS   : {ds.crs}")
        print(f"  dtype : {ds.dtypes[0]}")

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

    # -------------------------------------------------------------------------
    # Stage 7: Compare against JRC Monthly History
    # B2 fix: compare_dswx returns single DSWxValidationResult; read
    # diagnostics via .diagnostics attribute (NOT tuple unpack)
    # -------------------------------------------------------------------------
    print("\n-- Stage 7: Validation vs JRC GSW --")
    jrc_cache = CACHE / "jrc"
    jrc_cache.mkdir(exist_ok=True)

    validation = compare_dswx(
        product_path=dswx_result_path,
        year=selected_aoi.jrc_year,
        month=selected_aoi.jrc_month,
        cache_dir=jrc_cache,
    )
    # B2 fix: read diagnostics as attribute on DSWxValidationResult (NOT tuple unpack)
    diagnostics = validation.diagnostics

    f1 = float(validation.reference_agreement.measurements["f1"])
    precision = float(validation.reference_agreement.measurements["precision"])
    recall = float(validation.reference_agreement.measurements["recall"])
    accuracy = float(validation.reference_agreement.measurements["accuracy"])

    print(f"\n  {'='*60}")
    print(f"  F1           : {f1:.4f}   (criterion: > 0.90 BINDING)")
    print(f"  Precision    : {precision:.4f}")
    print(f"  Recall       : {recall:.4f}")
    print(f"  Accuracy     : {accuracy:.4f}")
    if diagnostics is not None:
        f1_full_fmt = f"{diagnostics.f1_full_pixels:.4f}"
        print(f"  F1_full_px   : {f1_full_fmt}  (diagnostic; no shoreline exclusion)")
        print(f"  Shoreline px : {diagnostics.shoreline_buffer_excluded_pixels}  excluded")
    print(f"  {'='*60}")

    # -------------------------------------------------------------------------
    # Stage 8: INVESTIGATION_TRIGGER (CONTEXT D-20)
    # F1 < 0.85 flags BOA-offset / Claverie cross-cal / SCL-mask regression
    # -------------------------------------------------------------------------
    print("\n-- Stage 8: INVESTIGATION_TRIGGER assessment --")
    f1_below_regression = f1 < 0.85
    regression = RegressionDiagnostic(
        f1_below_regression_threshold=bool(f1_below_regression),
        regression_diagnostic_required=(
            ["boa_offset_check", "claverie_xcal_check", "scl_mask_audit"]
            if f1_below_regression
            else []
        ),
        investigation_resolved=False,
    )

    # cell_status + named_upgrade_path (D-15 three-state taxonomy)
    if f1 > 0.90:
        cell_status: Literal["PASS", "FAIL", "BLOCKER"] = "PASS"
        named_upgrade_path: str | None = None
    elif f1 >= 0.85:
        cell_status = "FAIL"
        named_upgrade_path = "ML-replacement (DSWX-V2-01)"
    else:
        cell_status = "FAIL"
        named_upgrade_path = "BOA-offset / Claverie cross-cal regression"

    print(f"  cell_status          : {cell_status}")
    print(f"  named_upgrade_path   : {named_upgrade_path}")
    print(f"  f1_below_regression  : {f1_below_regression}")
    if f1_below_regression:
        print("  INVESTIGATION_TRIGGER: BOA-offset / Claverie cross-cal / SCL-mask audit required")

    # -------------------------------------------------------------------------
    # Stage 9: DswxNamCellMetrics write (D-26 + W2 fix)
    # W2 fix: f1_full_pixels + shoreline_buffer_excluded_pixels populate
    # DswxNamCellMetrics directly (Plan 06-02 schema symmetry with DswxEUCellMetrics).
    # W2 fix: NO separate eval sidecar for diagnostics; fields live in metrics.json.
    # -------------------------------------------------------------------------
    print("\n-- Stage 9: metrics.json write (DswxNamCellMetrics; W2 fix) --")
    # W2 fix: extract diagnostic fields from result.diagnostics (B2 attribute access)
    f1_full_pixels: float | None = (
        float(diagnostics.f1_full_pixels) if diagnostics is not None else None
    )
    shoreline_buffer_excluded_pixels: int | None = (
        int(diagnostics.shoreline_buffer_excluded_pixels) if diagnostics is not None else None
    )

    metrics = DswxNamCellMetrics(
        product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResultJson(
            measurements={
                "f1": f1,
                "precision": precision,
                "recall": recall,
                "accuracy": accuracy,
            },
            criterion_ids=["dswx.f1_min"],
        ),
        criterion_ids_applied=["dswx.f1_min"],
        selected_aoi=selected_aoi.aoi_name,
        selected_scene_id=safe_id,
        cloud_cover_pct=scene_cloud_cover,
        candidates_attempted=candidates_attempted,
        region="nam",
        cell_status=cell_status,  # type: ignore[arg-type]
        named_upgrade_path=named_upgrade_path,
        regression=regression,
        # W2 fix: diagnostics inline in metrics.json -- no separate sidecar file
        f1_full_pixels=f1_full_pixels,
        shoreline_buffer_excluded_pixels=shoreline_buffer_excluded_pixels,
    )
    (CACHE / "metrics.json").write_text(metrics.model_dump_json(indent=2))
    print(f"  Written: {(CACHE / 'metrics.json')}")

    # -------------------------------------------------------------------------
    # Stage 10: meta.json (Phase 2 D-12 input hashes + threat T-06-05-05)
    # -------------------------------------------------------------------------
    print("\n-- Stage 10: meta.json write --")
    git_sha = subprocess.check_output(  # noqa: S603, S607
        ["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent
    ).decode().strip()
    git_dirty_output = subprocess.check_output(  # noqa: S603, S607
        ["git", "status", "--porcelain"], cwd=Path(__file__).parent
    ).decode().strip()
    git_dirty = bool(git_dirty_output)

    # Cheap content-hash of SAFE file listing (full per-file hash too slow)
    safe_file_list = sorted(
        str(f.relative_to(safe_dir)) for f in safe_dir.rglob("*") if f.is_file()
    )
    safe_hash = hashlib.sha256("|".join(safe_file_list).encode()).hexdigest()[:16]

    threshold_module_path = Path(__file__).parent / "src/subsideo/products/dswx_thresholds.py"
    threshold_module_hash = (
        hashlib.sha256(threshold_module_path.read_bytes()).hexdigest()[:16]
        if threshold_module_path.exists()
        else "unavailable"
    )

    wall_s = time.time() - t_start
    meta = {
        "git_sha": git_sha,
        "git_dirty": git_dirty,
        "run_started_utc": run_started.isoformat(),
        "wall_s": wall_s,
        "platform": platform.platform(),
        "python_version": sys.version,
        "selected_aoi": selected_aoi.aoi_name,
        "selected_mgrs_tile": selected_aoi.mgrs_tile,
        "selected_scene_id": safe_id,
        "cloud_cover_pct": scene_cloud_cover,
        "jrc_year": selected_aoi.jrc_year,
        "jrc_month": selected_aoi.jrc_month,
        "input_hashes": {
            "safe_filename_hash_prefix": safe_hash,
            "threshold_module_sha256_prefix": threshold_module_hash,
        },
    }
    (CACHE / "meta.json").write_text(_json.dumps(meta, indent=2))
    print(f"  Written: {(CACHE / 'meta.json')}")
    print(f"  wall_s = {wall_s:.0f}s ({wall_s/60:.1f} min)")
    print(f"  EXPECTED_WALL_S = {EXPECTED_WALL_S}s; headroom = {EXPECTED_WALL_S - wall_s:.0f}s")

    # -------------------------------------------------------------------------
    # Final status
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    if cell_status == "PASS":
        print(f"PASS: F1={f1:.4f} > 0.90 over {selected_aoi.aoi_name}")
        print("EU recalibration (Plan 06-06) cleared to proceed.")
    elif cell_status == "FAIL" and not f1_below_regression:
        print(f"FAIL (named upgrade path): F1={f1:.4f} between 0.85 and 0.90")
        print(f"named_upgrade_path = '{named_upgrade_path}'")
        print("EU recalibration (Plan 06-06) cleared to proceed (F1 >= 0.85; no regression).")
    else:
        print(f"INVESTIGATION_TRIGGER: F1={f1:.4f} < 0.85")
        print("EU recalibration HALTED via metrics.json gate until investigation completes.")
        print("See CONCLUSIONS_DSWX_N_AM.md §5 for required audit steps:")
        print("  - boa_offset_check")
        print("  - claverie_xcal_check")
        print("  - scl_mask_audit")
    print("=" * 70)

    sys.exit(0)
