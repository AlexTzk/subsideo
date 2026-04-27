# scripts/recalibrate_dswe_thresholds.py -- DSWx EU threshold recalibration via joint grid search
#
# Phase 6 DSWX-04 + DSWX-05 + DSWX-06: joint grid search over WIGT x AWGT x
# PSWT2_MNDWI; 8400 gridpoints x 10 fit-set (AOI, scene) pairs (5 AOIs x 2
# wet/dry seasons; Balaton held out per BOOTSTRAP §5.4 -- NOT in fit set, NOT
# in LOO-CV folds). PITFALLS P5.1 mitigation: edge-of-grid sentinel + LOO-CV
# gap < 0.02 acceptance gate. CONTEXT D-04..D-08 + D-13..D-16.
#
# Iteration 1 fixes:
# - B1: 10-fold leave-one-pair-out (NOT 12; CONTEXT D-14 wording error)
# - B3: Stages 5/7/9 explicit code (no placeholder stubs)
# - B4: Stage 3 compute_intermediates body fully specified (promoted helpers)
# - W1: Stage 10 sentinel-anchor slicing (no fragile regex)
# - W3: Stages 6+8 BLOCKER writes use validated DswxEUCellMetrics schema
#
# Storage estimate : ~30 GB per (AOI, scene) intermediate cache; ~12 SAFEs
# Compute estimate : 25-45 min realistic (12-core loky); 6 hr conservative (cold)
#
# Resume-safe: per-(AOI, scene) intermediate cache + gridscores.parquet skip via
# mtime-staleness check on cache dirs.
import warnings; warnings.filterwarnings("ignore")  # noqa: E702, I001

EXPECTED_WALL_S = 21600   # 6 hr cold path; supervisor 2x = 12 hr abort (CONTEXT D-24)


if __name__ == "__main__":
    # Phase 1 ENV-04 mandatory; loky workers default to spawn (RESEARCH §joblib pattern)
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
    from itertools import product
    from pathlib import Path
    from typing import Any, Literal

    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    from dotenv import load_dotenv
    from joblib import Parallel, delayed
    from loguru import logger

    from subsideo.data.cdse import CDSEClient, extract_safe_s3_prefix
    from subsideo.products.dswx import (
        IndexBands,
        _apply_boa_offset_and_claverie,
        _classify_water,
        _read_bands,
        _resolve_band_paths_from_safe,
        compute_index_bands,
        score_water_class_from_indices,
    )
    from subsideo.products.dswx_thresholds import DSWEThresholds
    from subsideo.validation.compare_dswx import (
        _compute_shoreline_buffer_mask,
        _fetch_jrc_tile_for_bbox,
        _reproject_jrc_to_s2_grid,
    )
    from subsideo.validation.harness import (
        bounds_for_mgrs_tile,
        credential_preflight,
        ensure_resume_safe,
    )
    from subsideo.validation.matrix_schema import (
        DSWEThresholdsRef,
        DswxEUCellMetrics,
        LOOCVPerFold,
        PerAOIF1Breakdown,
        ProductQualityResultJson,
        ReferenceAgreementResultJson,
    )
    from subsideo.validation.metrics import (
        f1_score,
        overall_accuracy,
        precision_score,
        recall_score,
    )

    load_dotenv()
    credential_preflight([
        "CDSE_CLIENT_ID", "CDSE_CLIENT_SECRET",
        "CDSE_S3_ACCESS_KEY", "CDSE_S3_SECRET_KEY",
    ])

    run_started = datetime.now(timezone.utc)
    t_start = time.time()

    @dataclass(frozen=True)
    class FitsetAOI:
        """Per-AOI declarative fit-set entry (CONTEXT D-04)."""

        aoi_id: str  # 'alcantara' / 'tagus' / etc.
        biome: str
        bbox: tuple[float, float, float, float]
        mgrs_tile: str
        epsg: int
        wet_year: int
        wet_month: int
        dry_year: int
        dry_month: int
        held_out: bool

    # AOIs locked per Plan 06-01 dswx_fitset_aoi_candidates.md
    # 5 fit-set + 1 Balaton held-out = 6 AOIs x 2 (wet/dry) = 12 (AOI, scene) pairs total;
    # B1 fix: ONLY 10 of those (5 fit-set x 2 seasons) participate in the grid search +
    # LOO-CV; the 2 Balaton pairs are scored at the joint best gridpoint at Stage 9.
    # NOTE: MGRS tile corrections applied (Plan 06-06 STAC-verified tiles):
    # - 29SQE (Alcantara) → 29TPE: 29SQE does not exist in CDSE STAC; 29TPE covers
    #   the main reservoir body at lat 39.64-40.64 (water concentrated at lat 39.75-39.80)
    # - 32TQR (Garda) → 32TPR: 32TQR does not exist in CDSE STAC; 32TPR is the actual
    #   tile (confirmed via live STAC search; covers Lake Garda completely)
    # - 33TXP (Balaton) → 33TXM: 33TXP does not exist in CDSE STAC; 33TXM covers Balaton
    # - 33VVF (Vanern) → 33VUF: 33VVF only covers a tiny sliver of eastern Vanern; 33VUF
    #   covers the main lake body (41% JRC water at lat 58.51-58.98)
    # - Tagus wet_month=2 → 3: Feb 2021 JRC tile is all-zero (no observations); Mar OK
    # - Vanern wet_month=8→7, dry_month=5→4: Jul has 0% cloud, 41.1% JRC water; Apr has
    #   1.7% cloud, 41.6% JRC water; both months verified with live JRC tile downloads
    AOIS: list[FitsetAOI] = [
        FitsetAOI(
            aoi_id="alcantara", biome="Mediterranean reservoir",
            bbox=(-7.05, 39.55, -6.65, 39.95),
            mgrs_tile="29TPE", epsg=32629,  # corrected: 29SQE not in CDSE STAC
            wet_year=2021, wet_month=3,   # Mar wet (after winter rain); 0.03% cloud on 29TPE
            dry_year=2021, dry_month=8,   # Aug dry; 0.0-0.7% cloud on 29TPE
            held_out=False,
        ),
        FitsetAOI(
            aoi_id="tagus", biome="Atlantic estuary",
            bbox=(-9.45, 38.55, -8.85, 39.05),
            mgrs_tile="29SMC", epsg=32629,  # confirmed correct
            wet_year=2021, wet_month=3,   # Mar; Feb JRC tile is all-zero; Mar=22.2% water OK
            dry_year=2021, dry_month=8,   # Aug; 21.7% water in JRC
            held_out=False,
        ),
        FitsetAOI(
            aoi_id="vanern", biome="Boreal lake",
            bbox=(12.40, 58.45, 14.20, 59.45),
            mgrs_tile="33VUF", epsg=32633,  # corrected: 33VVF only a sliver; 33VUF = main body
            wet_year=2021, wet_month=7,   # Jul; 0.0% cloud on 33VUF; JRC 41.1% water
            dry_year=2021, dry_month=4,   # Apr; 1.7% cloud on 33VUF; JRC 41.6% water
            held_out=False,
        ),
        FitsetAOI(
            aoi_id="garda", biome="Alpine valley",
            bbox=(10.55, 45.55, 10.85, 45.85),
            mgrs_tile="32TPR", epsg=32632,  # corrected: 32TQR not in CDSE STAC
            wet_year=2021, wet_month=6,   # Jun (snowmelt); 14.0% cloud on 32TPR (best in month)
            dry_year=2021, dry_month=10,  # Oct; 0.0% cloud on 32TPR
            held_out=False,
        ),
        FitsetAOI(
            aoi_id="donana", biome="Iberian summer-dry",
            bbox=(-6.55, 36.80, -6.30, 37.05),
            mgrs_tile="29SQB", epsg=32629,  # confirmed correct
            wet_year=2021, wet_month=3,   # Mar; 0.0% cloud on 29SQB
            dry_year=2021, dry_month=8,   # Aug; 4.9% cloud on 29SQB
            held_out=False,
        ),
        FitsetAOI(
            aoi_id="balaton", biome="Pannonian plain",
            bbox=(17.20, 46.60, 18.20, 46.95),
            mgrs_tile="33TXM", epsg=32633,  # corrected: 33TXP not in CDSE STAC
            wet_year=2021, wet_month=4,   # Apr; 0.0% cloud on 33TXM
            dry_year=2021, dry_month=7,   # Jul; 0.0% cloud on 33TXM
            held_out=True,  # CONTEXT D-01 + BOOTSTRAP §5.4 + DSWX-03
        ),
    ]

    FIT_SET_AOIS = [a for a in AOIS if not a.held_out]  # 5 AOIs
    HELD_OUT_AOI = next(a for a in AOIS if a.held_out)  # Balaton

    # Grid bounds (CONTEXT D-04; verified 8400 = 25 x 21 x 16 per RESEARCH lines 318-321)
    WIGT_VALS = np.arange(0.08, 0.20 + 1e-9, 0.005)              # 25 values
    AWGT_VALS = np.arange(-0.10, 0.10 + 1e-9, 0.01)               # 21 values
    PSWT2_MNDWI_VALS = np.arange(-0.65, -0.35 + 1e-9, 0.02)       # 16 values
    GRIDPOINTS = list(product(WIGT_VALS, AWGT_VALS, PSWT2_MNDWI_VALS))
    assert len(GRIDPOINTS) == 8400, f"expected 8400 gridpoints, got {len(GRIDPOINTS)}"

    CACHE = Path("./eval-dswx-fitset")
    CACHE.mkdir(exist_ok=True)
    RESULTS_PATH = Path("scripts/recalibrate_dswe_thresholds_results.json")
    BLOCKER_METRICS_PATH = Path("eval-dswx/metrics.json")  # Stages 6 + 8 W3 BLOCKER write

    # ====================================================================
    # Stage 0: N.Am. regression-flag assert (CONTEXT D-20 INVESTIGATION_TRIGGER halt)
    # ====================================================================
    nam_metrics_path = Path("eval-dswx_nam/metrics.json")
    if nam_metrics_path.exists():
        nam_metrics = _json.loads(nam_metrics_path.read_text())
        regression = nam_metrics.get("regression", {})
        f1_below = regression.get("f1_below_regression_threshold", False)
        resolved = regression.get("investigation_resolved", False)
        if f1_below and not resolved:
            logger.error(
                "HALT: eval-dswx_nam/metrics.json shows f1_below_regression_threshold=True "
                "AND investigation_resolved=False. Plan 06-05 INVESTIGATION_TRIGGER gate "
                "(CONTEXT D-20) blocks EU recalibration until BOA-offset / Claverie cross-cal "
                "/ SCL-mask audit completes and CONCLUSIONS_DSWX_N_AM.md §5 is populated. "
                f"Diagnostics required: {regression.get('regression_diagnostic_required', [])}"
            )
            sys.exit(2)
    else:
        logger.warning(
            "eval-dswx_nam/metrics.json missing; Plan 06-05 has not run yet. "
            "Recalibration proceeds without N.Am. regression check (uncommon path)."
        )

    # ====================================================================
    # Stage 1: AOI lock (already loaded at module level via AOIS / FIT_SET_AOIS / HELD_OUT_AOI)
    # ====================================================================
    logger.info(f"Fit-set AOIs ({len(FIT_SET_AOIS)}): {[a.aoi_id for a in FIT_SET_AOIS]}")
    logger.info(f"Held-out AOI: {HELD_OUT_AOI.aoi_id}")
    logger.info(
        f"Total fit-set pairs: {len(FIT_SET_AOIS) * 2} "
        "(5 AOIs x 2 wet/dry -- B1 fix: 10 folds)"
    )
    logger.info(
        "Total Balaton pairs: 2 (1 AOI x 2 wet/dry; held out, scored at Stage 9 only)"
    )

    # ====================================================================
    # Stage 2: SAFE download (joblib parallel; CDSE rate-limit ~5 concurrent)
    # ====================================================================
    cdse = CDSEClient(
        client_id=os.environ["CDSE_CLIENT_ID"],
        client_secret=os.environ["CDSE_CLIENT_SECRET"],
    )

    def download_aoi_scene(
        aoi: FitsetAOI, season: Literal["wet", "dry"]
    ) -> tuple[str, str, Path]:
        """Download one (AOI, season) SAFE via CDSE STAC + S3.

        Returns (aoi_id, season, safe_dir). Raises on permanent failure.
        Per-AOI try/except isolation lives in the caller loop.
        """
        year = aoi.wet_year if season == "wet" else aoi.dry_year
        month = aoi.wet_month if season == "wet" else aoi.dry_month
        bbox = bounds_for_mgrs_tile(aoi.mgrs_tile, buffer_deg=0.1)
        # Pass naive datetimes -- CDSEClient.search_stac appends 'Z' to
        # isoformat() output; tz-aware datetime.isoformat() already ends
        # with '+00:00', so appending 'Z' would produce the invalid
        # '2021-03-01T00:00:00+00:00Z' string.
        items = cdse.search_stac(
            collection="SENTINEL-2",
            bbox=list(bbox),
            start=datetime(year, month, 1),
            end=datetime(year, month, 28, 23, 59, 59),
            product_type="S2MSI2A",
            max_items=50,  # increased from 20; MGRS tile filter below narrows to target tile
        )
        # MGRS tile filter: keep only items from the exact expected tile.
        # The STAC bbox search returns all tiles overlapping the search bbox;
        # without this filter, the lowest-cloud-cover scene may belong to a
        # neighbouring tile and produce a JRC/S2 spatial mismatch.
        # Two paths: (1) STAC property "s2:mgrs_tile" (preferred, present in
        # new CDSE STAC); (2) tile code embedded in the scene ID as "T{5chars}"
        # (e.g., "T29SQE" in "S2A_MSIL2A_..._T29SQE_...").
        def _item_mgrs_tile(item: dict) -> str:
            # Path 1: explicit STAC property
            prop_tile = (item.get("properties") or {}).get("s2:mgrs_tile", "")
            if prop_tile:
                return prop_tile.upper().lstrip("T")
            # Path 2: tile code in scene ID (6th '_'-split token starting with T)
            scene_id = item.get("id", "")
            for token in scene_id.split("_"):
                if token.startswith("T") and len(token) == 6:
                    return token[1:]  # strip leading "T" -> e.g. "29SQE"
            return ""

        cloud_free = [
            it for it in items
            if (it.get("properties", {}).get("eo:cloud_cover") or 100) < 15
            and _item_mgrs_tile(it).upper() == aoi.mgrs_tile.upper()
        ]
        if not cloud_free:
            # Widen cloud threshold to 30% before giving up, to handle months
            # with light cloud cover that still have valid observations over
            # the water body (CONTEXT D-04 robustness note).
            cloud_free = [
                it for it in items
                if (it.get("properties", {}).get("eo:cloud_cover") or 100) < 30
                and _item_mgrs_tile(it).upper() == aoi.mgrs_tile.upper()
            ]
        if not cloud_free:
            raise RuntimeError(
                f"no cloud-free scene for {aoi.aoi_id} {season} ({year}-{month:02d}) "
                f"on tile {aoi.mgrs_tile!r} (searched {len(items)} items from CDSE STAC)"
            )
        scene = sorted(cloud_free, key=lambda i: i["properties"].get("eo:cloud_cover", 100))[0]
        safe_id = scene["id"]
        # download_safe creates <scene>.SAFE inside output_root; pass the
        # parent directory. The SAFE dir itself is CACHE/aoi/season/<scene>.SAFE.
        output_root = CACHE / aoi.aoi_id / season
        output_root.mkdir(parents=True, exist_ok=True)
        safe_dir = output_root / f"{safe_id}.SAFE"
        if not ensure_resume_safe(safe_dir, manifest_keys=["MTD_MSIL2A.xml"]):
            safe_dir = cdse.download_safe(
                extract_safe_s3_prefix(scene), output_root
            )
        return (aoi.aoi_id, season, safe_dir)

    pairs_to_download = [(a, s) for a in AOIS for s in ("wet", "dry")]
    # n_jobs=2: CDSE WAF throttles 4 parallel STAC searches; 2 concurrent
    # STAC lookups avoids exhausting retries while still parallelising S3 download.
    download_results = Parallel(n_jobs=2, backend="loky")(
        delayed(download_aoi_scene)(a, s) for a, s in pairs_to_download
    )

    # Build mapping aoi_id -> {wet: safe_dir, dry: safe_dir}
    SAFE_INDEX: dict[tuple[str, str], Path] = {}
    aoi_safes: dict[str, dict[str, Path]] = {}
    for aoi_id, season, safe_dir in download_results:
        aoi_safes.setdefault(aoi_id, {})[season] = safe_dir
        SAFE_INDEX[(aoi_id, season)] = safe_dir

    # ====================================================================
    # Stage 3: Per-scene intermediate cache compute (joblib parallel; D-05; B4 fix concrete body)
    # ====================================================================
    # B4 fix: explicit decomposed helpers (no placeholder body).
    # We use promoted helpers from src/subsideo/products/dswx.py:
    #   - _resolve_band_paths_from_safe(safe_dir) -> dict[str, Path]
    #   - _read_bands(band_paths, target_resolution_m, target_epsg) -> 7 arrays
    #   - _apply_boa_offset_and_claverie([blue, green, red, nir, swir1, swir2], scene_id)
    # And from src/subsideo/validation/compare_dswx.py:
    #   - _fetch_jrc_tile_for_bbox(year, month, lonlat_bbox, cache_dir) -> Path | None
    #   - _reproject_jrc_to_s2_grid(jrc_tile_path, target_epsg, target_shape) -> np.ndarray

    def compute_intermediates(aoi: FitsetAOI, season: Literal["wet", "dry"]) -> Path:
        """Compute 5 index bands + raw blue/nir/swir1/swir2 + SCL mask + JRC tile per (AOI, scene).

        Cache layout: eval-dswx-fitset/<aoi>/<season>/<scene_id>/intermediates/*.npy
        Resume-safe: skip if all expected .npy files exist + mtime is fresh.

        B4 fix: concrete explicit body with promoted helpers from
        src/subsideo/products/dswx.py (Plan 06-06 architectural enabler).
        """
        scene_id = SAFE_INDEX[(aoi.aoi_id, season)].name.replace(".SAFE", "")
        safe_dir = SAFE_INDEX[(aoi.aoi_id, season)]
        intermediates_dir = safe_dir.parent / scene_id / "intermediates"
        # Warm-cache skip: if all expected .npy files exist, return early
        if (intermediates_dir / "mndwi.npy").exists() and (intermediates_dir / "jrc.npy").exists():
            logger.info(f"intermediate cache hit: {aoi.aoi_id}/{season}")
            return intermediates_dir
        intermediates_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"computing intermediates for {aoi.aoi_id}/{season}")

        # 1. Locate B02-B12 + SCL paths inside SAFE (promoted from run_eval_dswx.py)
        band_paths = _resolve_band_paths_from_safe(safe_dir)

        # 2. Read bands at 20m S2 native resolution (UTM grid for the AOI's MGRS tile)
        #    _read_bands internally applies BOA offset + Claverie cross-calibration.
        blue, green, red, nir, swir1, swir2, scl = _read_bands(
            band_paths, target_resolution_m=20, target_epsg=aoi.epsg,
        )

        # 3. Apply BOA offset + HLS Claverie cross-calibration to optical bands (Plan 06-03)
        #    NOTE: _read_bands already handles BOA offset + Claverie; this call is a
        #    documented no-op pass-through (B4 fix keeps the pipeline explicit for clarity).
        blue, green, red, nir, swir1, swir2 = _apply_boa_offset_and_claverie(
            [blue, green, red, nir, swir1, swir2], scene_id,
        )

        # 4. Compute index bands via Plan 06-03 newly-public function:
        indices = compute_index_bands(blue, green, red, nir, swir1, swir2)

        # 5. Save intermediates as float32 .npy (D-05 layout)
        np.save(intermediates_dir / "mndwi.npy", indices.mndwi.astype(np.float32))
        np.save(intermediates_dir / "ndvi.npy", indices.ndvi.astype(np.float32))
        np.save(intermediates_dir / "awesh.npy", indices.awesh.astype(np.float32))
        np.save(intermediates_dir / "mbsrv.npy", indices.mbsrv.astype(np.float32))
        np.save(intermediates_dir / "mbsrn.npy", indices.mbsrn.astype(np.float32))

        # 6. Save raw bands required by score_water_class_from_indices PSWT1/PSWT2 boundary tests:
        np.save(intermediates_dir / "blue.npy", blue.astype(np.float32))
        np.save(intermediates_dir / "nir.npy", nir.astype(np.float32))
        np.save(intermediates_dir / "swir1.npy", swir1.astype(np.float32))
        np.save(intermediates_dir / "swir2.npy", swir2.astype(np.float32))
        np.save(intermediates_dir / "scl.npy", scl.astype(np.uint8))

        # 7. Fetch JRC tile + reproject to S2 UTM grid (via promoted compare_dswx helpers).
        jrc_year = aoi.wet_year if season == "wet" else aoi.dry_year
        jrc_month = aoi.wet_month if season == "wet" else aoi.dry_month
        jrc_tile_path = _fetch_jrc_tile_for_bbox(
            year=jrc_year, month=jrc_month, lonlat_bbox=aoi.bbox,
            cache_dir=CACHE / "jrc",
        )
        # Reproject JRC raster to the S2 UTM grid established by blue/etc. above.
        jrc_aligned = _reproject_jrc_to_s2_grid(
            jrc_tile_path,
            target_epsg=aoi.epsg,
            target_shape=blue.shape,
        )
        np.save(intermediates_dir / "jrc.npy", jrc_aligned.astype(np.uint8))

        return intermediates_dir

    intermediate_dirs: list[Path] = Parallel(n_jobs=-1, backend="loky")(
        delayed(compute_intermediates)(a, s) for a, s in pairs_to_download
    )

    # ====================================================================
    # Stage 4: Joint grid search (joblib parallel over 12 pairs; D-06)
    # ====================================================================
    def grid_search_one_pair(aoi_id: str, season: str, intermediates_dir: Path) -> Path:
        """Run 8400-gridpoint grid search on one (AOI, scene). Writes gridscores.parquet."""
        out_path = intermediates_dir.parent / "gridscores.parquet"
        if out_path.exists():
            logger.info(f"grid search cache hit: {aoi_id}/{season}")
            return out_path

        # Load intermediates
        mndwi = np.load(intermediates_dir / "mndwi.npy")
        ndvi = np.load(intermediates_dir / "ndvi.npy")
        mbsrv = np.load(intermediates_dir / "mbsrv.npy")
        mbsrn = np.load(intermediates_dir / "mbsrn.npy")
        awesh = np.load(intermediates_dir / "awesh.npy")
        blue = np.load(intermediates_dir / "blue.npy")
        nir = np.load(intermediates_dir / "nir.npy")
        swir1 = np.load(intermediates_dir / "swir1.npy")
        swir2 = np.load(intermediates_dir / "swir2.npy")
        scl = np.load(intermediates_dir / "scl.npy")
        jrc = np.load(intermediates_dir / "jrc.npy")

        # SCL cloud-mask (values 3, 8, 9, 10) excluded
        cloud_mask = np.isin(scl, [3, 8, 9, 10])

        # JRC Monthly History: 0=no obs, 1=not water, 2=water
        # _compute_shoreline_buffer_mask expects a BINARY mask (1=water, 0=non-water).
        # Pass the binarized JRC so the buffer computes on the actual water/land boundary.
        jrc_binary = (jrc == 2).astype(np.uint8)
        # Shoreline buffer on JRC binary grid (D-16; uniform-application)
        shoreline_buffer = _compute_shoreline_buffer_mask(jrc_binary, iterations=1)
        valid_mask_full = (~cloud_mask) & (jrc != 0)  # 0 = JRC no-observation
        valid_mask_excl = valid_mask_full & (~shoreline_buffer)

        # Reconstruct IndexBands for score_water_class_from_indices
        indices = IndexBands(mndwi=mndwi, ndvi=ndvi, mbsrv=mbsrv, mbsrn=mbsrn, awesh=awesh)

        # Iterate 8400 gridpoints
        wigts, awgts, pswt2_mndwis = [], [], []
        f1s, precisions, recalls, accuracies = [], [], [], []
        n_total, n_excl = [], []
        for w, a, p in GRIDPOINTS:
            thresholds = DSWEThresholds(
                WIGT=float(w), AWGT=float(a), PSWT2_MNDWI=float(p),
                grid_search_run_date="<grid_search_in_progress>",
                fit_set_hash="", fit_set_mean_f1=float("nan"),
                held_out_balaton_f1=float("nan"), loocv_mean_f1=float("nan"),
                loocv_gap=float("nan"), notebook_path="",
                results_json_path="", provenance_note="",
            )
            diag = score_water_class_from_indices(
                indices, blue=blue, nir=nir, swir1=swir1, swir2=swir2,
                thresholds=thresholds,
            )
            water_class = _classify_water(diag)
            dswx_binary = ((water_class >= 1) & (water_class <= 3)).astype(np.uint8)

            wigts.append(w)
            awgts.append(a)
            pswt2_mndwis.append(p)
            f1s.append(f1_score(dswx_binary[valid_mask_excl], jrc_binary[valid_mask_excl]))
            precisions.append(
                precision_score(dswx_binary[valid_mask_excl], jrc_binary[valid_mask_excl])
            )
            recalls.append(
                recall_score(dswx_binary[valid_mask_excl], jrc_binary[valid_mask_excl])
            )
            accuracies.append(
                overall_accuracy(dswx_binary[valid_mask_excl], jrc_binary[valid_mask_excl])
            )
            n_total.append(int(valid_mask_full.sum()))
            n_excl.append(int(valid_mask_excl.sum()))

        # Write parquet
        table = pa.Table.from_arrays(
            [wigts, awgts, pswt2_mndwis, f1s, precisions, recalls, accuracies, n_total, n_excl],
            names=[
                "WIGT", "AWGT", "PSWT2_MNDWI", "f1", "precision", "recall",
                "accuracy", "n_pixels_total", "n_pixels_shoreline_excluded",
            ],
        )
        pq.write_table(table, out_path, compression="zstd")
        return out_path

    grid_results: list[Path] = Parallel(n_jobs=-1, backend="loky")(
        delayed(grid_search_one_pair)(a.aoi_id, s, intermediates_dir)
        for (a, s), intermediates_dir in zip(pairs_to_download, intermediate_dirs, strict=False)
    )

    # ====================================================================
    # Stage 5: Aggregate per-pair gridscores -> joint best gridpoint + per-AOI breakdown
    # B3 fix: explicit code (no '...' placeholder)
    # ====================================================================
    # Aggregate ONLY the 10 fit-set pairs (5 AOIs x 2 seasons; Balaton excluded;
    # Balaton's 2 pairs are scored at Stage 9 against the joint best gridpoint).
    fit_set_aoi_ids = {a.aoi_id for a in FIT_SET_AOIS}
    gridscores_dfs = []
    for aoi in FIT_SET_AOIS:
        for season in ("wet", "dry"):
            scene_dir = CACHE / aoi.aoi_id / season
            scene_id = next(
                (p.name.replace(".SAFE", "") for p in scene_dir.glob("S2*.SAFE")),
                None,
            )
            if scene_id is None:
                continue
            path = scene_dir / scene_id / "gridscores.parquet"
            if not path.exists():
                logger.warning(
                    f"missing gridscores.parquet for {aoi.aoi_id}/{season}; skipping"
                )
                continue
            df = pq.read_table(path).to_pandas()
            df["aoi_id"] = aoi.aoi_id
            df["season"] = season
            df["biome"] = aoi.biome
            gridscores_dfs.append(df)
    all_gs = pd.concat(gridscores_dfs, ignore_index=True)
    assert len(all_gs) == len(FIT_SET_AOIS) * 2 * len(GRIDPOINTS), (
        f"expected {len(FIT_SET_AOIS) * 2 * len(GRIDPOINTS)} rows in fit-set aggregate "
        f"(10 pairs x 8400 gridpoints), got {len(all_gs)}"
    )

    # Mean F1 per gridpoint across 10 fit-set pairs
    mean_f1_per_grid = (
        all_gs.groupby(["WIGT", "AWGT", "PSWT2_MNDWI"])["f1"].mean().reset_index()
    )
    joint_best_idx = mean_f1_per_grid["f1"].idxmax()
    joint_best = (
        float(mean_f1_per_grid.loc[joint_best_idx, "WIGT"]),
        float(mean_f1_per_grid.loc[joint_best_idx, "AWGT"]),
        float(mean_f1_per_grid.loc[joint_best_idx, "PSWT2_MNDWI"]),
    )
    fit_set_mean_f1 = float(mean_f1_per_grid.loc[joint_best_idx, "f1"])

    # Per-AOI breakdown at joint best (5 entries; one per fit-set AOI)
    per_aoi_breakdown_raw: list[dict[str, Any]] = []
    for aoi in FIT_SET_AOIS:
        aoi_df = all_gs[
            (all_gs["aoi_id"] == aoi.aoi_id)
            & (all_gs["WIGT"] == joint_best[0])
            & (all_gs["AWGT"] == joint_best[1])
            & (all_gs["PSWT2_MNDWI"] == joint_best[2])
        ]
        wet_match = aoi_df[aoi_df["season"] == "wet"]
        dry_match = aoi_df[aoi_df["season"] == "dry"]
        wet_f1 = float(wet_match["f1"].iloc[0]) if len(wet_match) else float("nan")
        dry_f1 = float(dry_match["f1"].iloc[0]) if len(dry_match) else float("nan")
        per_aoi_breakdown_raw.append({
            "aoi_id": aoi.aoi_id,
            "biome": aoi.biome,
            "wet_scene_f1": wet_f1,
            "dry_scene_f1": dry_f1,
            "aoi_mean_f1": float(np.nanmean([wet_f1, dry_f1])),
        })

    # ====================================================================
    # Stage 6: Edge-of-grid sentinel (D-08) -- W3 fix uses validated DswxEUCellMetrics
    # ====================================================================
    def _at_edge(val: float, arr: "np.ndarray") -> bool:
        return abs(val - float(arr[0])) < 1e-9 or abs(val - float(arr[-1])) < 1e-9

    edge_check_status = "ok"
    if _at_edge(joint_best[0], WIGT_VALS):
        edge_check_status = "at_edge_WIGT"
    elif _at_edge(joint_best[1], AWGT_VALS):
        edge_check_status = "at_edge_AWGT"
    elif _at_edge(joint_best[2], PSWT2_MNDWI_VALS):
        edge_check_status = "at_edge_PSWT2_MNDWI"

    if edge_check_status != "ok":
        # W3 fix: write a DswxEUCellMetrics-validated metrics.json (NOT a hand-rolled JSON).
        # All required diagnostic fields use NaN sentinels per Plan 06-02 W3 BLOCKER state.
        run_date_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        BLOCKER_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        blocker_metrics = DswxEUCellMetrics(
            product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
            reference_agreement=ReferenceAgreementResultJson(
                measurements={"f1": float("nan")},
                criterion_ids=["dswx.f1_min"],
            ),
            criterion_ids_applied=["dswx.f1_min"],
            region="eu",
            thresholds_used=DSWEThresholdsRef(
                region="eu",
                grid_search_run_date="blocker-pre-finalize",
                fit_set_hash="",
            ),
            fit_set_mean_f1=float(fit_set_mean_f1),
            loocv_mean_f1=float("nan"),
            loocv_gap=float("nan"),
            # default empty list for loocv_per_fold + per_aoi_breakdown per W3:
            f1_full_pixels=float("nan"),
            cell_status="BLOCKER",
            named_upgrade_path="grid expansion required",  # W3 sentinel-named path
        )
        # Validate the schema, then write:
        BLOCKER_METRICS_PATH.write_text(blocker_metrics.model_dump_json(indent=2))
        # Also write a sidecar results.json with edge_check details for CHECKPOINT 1:
        results_blocker = {
            "cell_status": "BLOCKER",
            "edge_check": {"status": edge_check_status, "joint_best": list(joint_best)},
            "joint_best_gridpoint": {
                "WIGT": joint_best[0], "AWGT": joint_best[1], "PSWT2_MNDWI": joint_best[2],
            },
            "fit_set_mean_f1": float(fit_set_mean_f1),
            "grid_bounds": {
                "WIGT": [float(WIGT_VALS[0]), float(WIGT_VALS[-1])],
                "AWGT": [float(AWGT_VALS[0]), float(AWGT_VALS[-1])],
                "PSWT2_MNDWI": [float(PSWT2_MNDWI_VALS[0]), float(PSWT2_MNDWI_VALS[-1])],
            },
            "named_upgrade_path": "grid expansion required",
        }
        RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULTS_PATH.write_text(_json.dumps(results_blocker, indent=2))
        logger.error(
            f"BLOCKER: edge-of-grid sentinel triggered ({edge_check_status}); "
            f"joint_best={joint_best}; expand grid bounds + re-run (CONTEXT D-08)."
        )
        sys.exit(2)

    # ====================================================================
    # Stage 7: LOO-CV post-hoc on best-gridpoint (D-14 + B1 fix: 10-fold leave-one-pair-out)
    # ====================================================================
    # B1 fix: 10 folds = 5 fit-set AOIs x 2 seasons (NOT 12 -- Balaton held out;
    # NOT 5 -- leave-one-AOI-out collapses both seasons of held-out AOI together
    # which loses signal). Resolves CONTEXT D-14 "rotate 12 times" wording error.
    fitset_pairs = [(aoi, season) for aoi in FIT_SET_AOIS for season in ("wet", "dry")]
    assert len(fitset_pairs) == 10, "B1 fix: 10 fit-set pairs (5 AOIs x 2 seasons)"

    loocv_per_fold_records: list[dict[str, Any]] = []
    for left_out_idx, (left_out_aoi, left_out_season) in enumerate(fitset_pairs):
        # Refit set: 9 fit-set pairs (excluding left_out (aoi, season))
        fold_df = all_gs[
            ~(
                (all_gs["aoi_id"] == left_out_aoi.aoi_id)
                & (all_gs["season"] == left_out_season)
            )
        ]
        # Per-gridpoint mean F1 across the 9 refit pairs
        fold_mean_f1 = (
            fold_df.groupby(["WIGT", "AWGT", "PSWT2_MNDWI"])["f1"].mean().reset_index()
        )
        fold_best_idx = fold_mean_f1["f1"].idxmax()
        fold_best = (
            float(fold_mean_f1.loc[fold_best_idx, "WIGT"]),
            float(fold_mean_f1.loc[fold_best_idx, "AWGT"]),
            float(fold_mean_f1.loc[fold_best_idx, "PSWT2_MNDWI"]),
        )
        # Score the left-out pair at the per-fold refit-best gridpoint:
        test_row = all_gs[
            (all_gs["aoi_id"] == left_out_aoi.aoi_id)
            & (all_gs["season"] == left_out_season)
            & (all_gs["WIGT"] == fold_best[0])
            & (all_gs["AWGT"] == fold_best[1])
            & (all_gs["PSWT2_MNDWI"] == fold_best[2])
        ]
        test_f1 = float(test_row["f1"].iloc[0]) if len(test_row) else float("nan")
        # Note: LOOCVPerFold schema uses lowercase field names
        loocv_per_fold_records.append({
            "fold_idx": left_out_idx,
            "left_out_aoi": left_out_aoi.aoi_id,
            "left_out_season": left_out_season,
            "refit_best_wigt": fold_best[0],
            "refit_best_awgt": fold_best[1],
            "refit_best_pswt2_mndwi": fold_best[2],
            "test_f1": test_f1,
        })

    loocv_mean_f1 = float(np.nanmean([f["test_f1"] for f in loocv_per_fold_records]))
    loocv_gap = float(fit_set_mean_f1 - loocv_mean_f1)

    # ====================================================================
    # Stage 8: LOO-CV gap acceptance check (DSWX-06; D-14) -- W3: validated DswxEUCellMetrics
    # ====================================================================
    if loocv_gap >= 0.02:
        run_date_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        BLOCKER_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Convert LOOCVPerFold + PerAOIF1Breakdown rows to schema instances:
        loocv_models = [LOOCVPerFold(**r) for r in loocv_per_fold_records]
        per_aoi_models = [PerAOIF1Breakdown(**r) for r in per_aoi_breakdown_raw]
        blocker_metrics = DswxEUCellMetrics(
            product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
            reference_agreement=ReferenceAgreementResultJson(
                measurements={"f1": float("nan")},
                criterion_ids=["dswx.f1_min"],
            ),
            criterion_ids_applied=["dswx.f1_min"],
            region="eu",
            thresholds_used=DSWEThresholdsRef(
                region="eu",
                grid_search_run_date="blocker-pre-finalize",
                fit_set_hash="",
            ),
            fit_set_mean_f1=float(fit_set_mean_f1),
            loocv_mean_f1=loocv_mean_f1,
            loocv_gap=loocv_gap,
            loocv_per_fold=loocv_models,
            per_aoi_breakdown=per_aoi_models,
            f1_full_pixels=float("nan"),
            cell_status="BLOCKER",
            named_upgrade_path="fit-set quality review",  # W3 sentinel-named path
        )
        BLOCKER_METRICS_PATH.write_text(blocker_metrics.model_dump_json(indent=2))
        results_blocker = {
            "cell_status": "BLOCKER",
            "loocv_gap_violation": True,
            "loocv_gap": loocv_gap,
            "fit_set_mean_f1": float(fit_set_mean_f1),
            "loocv_mean_f1": loocv_mean_f1,
            "loocv_per_fold": loocv_per_fold_records,
            "joint_best_gridpoint": {
                "WIGT": joint_best[0], "AWGT": joint_best[1], "PSWT2_MNDWI": joint_best[2],
            },
            "named_upgrade_path": "fit-set quality review",
        }
        RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULTS_PATH.write_text(_json.dumps(results_blocker, indent=2))
        logger.error(
            f"BLOCKER: LOO-CV gap = {loocv_gap:.4f} >= 0.02; overfit detected; "
            "expand AOI count or accept overfit-flagged calibration (CONTEXT D-14)."
        )
        sys.exit(2)

    # ====================================================================
    # Stage 9: Held-out Balaton F1 (D-13) -- B3 fix concrete pipeline call
    # ====================================================================
    # Compute fit_set_hash for THRESHOLDS_EU provenance (used in run_date_iso below + Stage 10):
    fit_set_ids = sorted([
        f"{aoi.aoi_id}-{season}-{SAFE_INDEX[(aoi.aoi_id, season)].name}"
        for aoi in FIT_SET_AOIS for season in ("wet", "dry")
    ])
    fit_set_hash = hashlib.sha256("\n".join(fit_set_ids).encode()).hexdigest()
    grid_search_run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Score Balaton wet + dry at the joint best gridpoint using the SAME
    # score_water_class_from_indices path as Stage 4. We reuse the cached
    # Balaton intermediates (created at Stage 3) -- no re-read of SAFE.
    balaton_thresholds = DSWEThresholds(
        WIGT=joint_best[0], AWGT=joint_best[1], PSWT2_MNDWI=joint_best[2],
        grid_search_run_date=grid_search_run_date,
        fit_set_hash=fit_set_hash,
        fit_set_mean_f1=fit_set_mean_f1,
        held_out_balaton_f1=float("nan"),  # filled below once computed
        loocv_mean_f1=loocv_mean_f1,
        loocv_gap=loocv_gap,
        notebook_path="notebooks/dswx_recalibration.ipynb",
        results_json_path="scripts/recalibrate_dswe_thresholds_results.json",
        provenance_note="Plan 06-06 grid search EU recalibration result.",
    )

    balaton_f1s: list[float] = []
    for season in ("wet", "dry"):
        scene_dir = CACHE / HELD_OUT_AOI.aoi_id / season
        scene_id = next(
            (p.name.replace(".SAFE", "") for p in scene_dir.glob("S2*.SAFE")), None,
        )
        if scene_id is None:
            balaton_f1s.append(float("nan"))
            continue
        intermediates_dir = scene_dir / scene_id / "intermediates"
        # Read pre-computed Balaton intermediates (Stage 3 cached them):
        mndwi = np.load(intermediates_dir / "mndwi.npy")
        ndvi = np.load(intermediates_dir / "ndvi.npy")
        mbsrv = np.load(intermediates_dir / "mbsrv.npy")
        mbsrn = np.load(intermediates_dir / "mbsrn.npy")
        awesh = np.load(intermediates_dir / "awesh.npy")
        blue = np.load(intermediates_dir / "blue.npy")
        nir = np.load(intermediates_dir / "nir.npy")
        swir1 = np.load(intermediates_dir / "swir1.npy")
        swir2 = np.load(intermediates_dir / "swir2.npy")
        scl = np.load(intermediates_dir / "scl.npy")
        jrc = np.load(intermediates_dir / "jrc.npy")
        cloud_mask = np.isin(scl, [3, 8, 9, 10])
        # JRC Monthly History: 2=water, 1=not water, 0=no obs
        # _compute_shoreline_buffer_mask expects binary (1=water, 0=non-water)
        jrc_bin_for_buf = (jrc == 2).astype(np.uint8)
        shoreline_buffer = _compute_shoreline_buffer_mask(jrc_bin_for_buf, iterations=1)
        valid_mask_excl = (~cloud_mask) & (jrc != 0) & (~shoreline_buffer)
        indices = IndexBands(mndwi=mndwi, ndvi=ndvi, mbsrv=mbsrv, mbsrn=mbsrn, awesh=awesh)
        diag = score_water_class_from_indices(
            indices, blue=blue, nir=nir, swir1=swir1, swir2=swir2,
            thresholds=balaton_thresholds,
        )
        water_class = _classify_water(diag)
        dswx_binary = ((water_class >= 1) & (water_class <= 3)).astype(np.uint8)
        jrc_binary = (jrc == 2).astype(np.uint8)
        balaton_f1s.append(
            float(f1_score(dswx_binary[valid_mask_excl], jrc_binary[valid_mask_excl]))
        )

    balaton_f1 = float(np.nanmean(balaton_f1s))
    logger.info(f"Balaton F1 (mean of wet+dry at joint best gridpoint): {balaton_f1:.4f}")

    # ====================================================================
    # Stage 10: Threshold module update (D-09..D-12) -- W1 fix sentinel-anchor slicing
    # ====================================================================
    # W1 fix: replace fragile regex with sentinel-comment anchor slicing.
    # Plan 06-02 introduced `# ╔═ THRESHOLDS_EU_BEGIN ═` and `# ╚═ THRESHOLDS_EU_END ═`
    # comment anchors framing the THRESHOLDS_EU instance. Stage 10 reads the file,
    # finds anchor offsets via `text.find()`, asserts both are present (fail-loud
    # `assert begin_idx > 0 and end_idx > begin_idx`), slices out the block
    # between, replaces with new instance, writes back.
    threshold_module_path = Path("src/subsideo/products/dswx_thresholds.py")
    src = threshold_module_path.read_text()
    BEGIN_ANCHOR = "# ╔═ THRESHOLDS_EU_BEGIN ═"
    END_ANCHOR = "# ╚═ THRESHOLDS_EU_END ═"
    begin_idx = src.find(BEGIN_ANCHOR)
    end_idx = src.find(END_ANCHOR)
    assert begin_idx > 0, (
        f"THRESHOLDS_EU_BEGIN sentinel anchor missing in {threshold_module_path}; "
        f"Plan 06-02 must have committed both anchors framing the THRESHOLDS_EU "
        f"instance assignment. W1 fix requires fail-loud assertion before rewrite."
    )
    assert end_idx > begin_idx, (
        f"THRESHOLDS_EU_END sentinel anchor missing or before BEGIN in "
        f"{threshold_module_path}; W1 fix requires both anchors present."
    )
    # Compute end offset including the END_ANCHOR line:
    end_line_end = src.find("\n", end_idx)
    if end_line_end < 0:
        end_line_end = len(src)
    new_eu_block_lines = [
        BEGIN_ANCHOR,
        "THRESHOLDS_EU = DSWEThresholds(",
        f"    WIGT={joint_best[0]:.4f},",
        f"    AWGT={joint_best[1]:.4f},",
        f"    PSWT2_MNDWI={joint_best[2]:.4f},",
        f"    grid_search_run_date='{grid_search_run_date}',",
        f"    fit_set_hash='{fit_set_hash}',",
        f"    fit_set_mean_f1={fit_set_mean_f1:.4f},",
        f"    held_out_balaton_f1={balaton_f1:.4f},",
        f"    loocv_mean_f1={loocv_mean_f1:.4f},",
        f"    loocv_gap={loocv_gap:.4f},",
        "    notebook_path='notebooks/dswx_recalibration.ipynb',",
        "    results_json_path='scripts/recalibrate_dswe_thresholds_results.json',",
        "    provenance_note=(",
        "        'Joint grid search over WIGT x AWGT x PSWT2_MNDWI; '",
        f"        '{len(fitset_pairs)} fit-set (AOI, scene) pairs across 5 EU biomes '",
        "        '(Mediterranean reservoir / Atlantic estuary / boreal lake / '",
        "        'Alpine valley / Iberian summer-dry); Balaton held out as test '",
        "        'set per BOOTSTRAP_V1.1.md §5.4. Plan 06-06 grid search.'",
        "    ),",
        ")",
        END_ANCHOR,
    ]
    new_eu_block = "\n".join(new_eu_block_lines)
    new_src = src[:begin_idx] + new_eu_block + src[end_line_end:]
    threshold_module_path.write_text(new_src)
    logger.info(
        f"updated THRESHOLDS_EU: WIGT={joint_best[0]:.4f}, AWGT={joint_best[1]:.4f}, "
        f"PSWT2_MNDWI={joint_best[2]:.4f}; fit_set_mean_f1={fit_set_mean_f1:.4f}; "
        f"loocv_gap={loocv_gap:.4f}; held_out_balaton_f1={balaton_f1:.4f}"
    )

    # ====================================================================
    # Stage 11: Notebook reproduce (papermill ABSENT per RESEARCH; SKIP)
    # ====================================================================
    logger.info("Stage 11 (papermill notebook execute): SKIPPED -- papermill not in conda env.")
    logger.info(
        "Manual reproduce: micromamba run -n subsideo jupyter nbconvert --to notebook "
        "--execute --inplace notebooks/dswx_recalibration.ipynb"
    )

    # ====================================================================
    # Final results.json
    # ====================================================================
    results = {
        "cell_status": "PASS",
        "edge_check": {"status": "ok", "joint_best": list(joint_best)},
        "joint_best_gridpoint": {
            "WIGT": float(joint_best[0]),
            "AWGT": float(joint_best[1]),
            "PSWT2_MNDWI": float(joint_best[2]),
        },
        "fit_set_mean_f1": float(fit_set_mean_f1),
        "loocv_mean_f1": loocv_mean_f1,
        "loocv_gap": loocv_gap,
        "loocv_per_fold": loocv_per_fold_records,
        "per_aoi_breakdown": per_aoi_breakdown_raw,
        "held_out_balaton_f1": float(balaton_f1),
        "fit_set_hash": fit_set_hash,
        "grid_search_run_date": grid_search_run_date,
        "wall_s": time.time() - t_start,
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip(),
        "python": platform.python_version(),
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(_json.dumps(results, indent=2))
    logger.info(f"recalibration complete: results -> {RESULTS_PATH}")
