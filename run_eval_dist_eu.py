# run_eval_dist_eu.py -- EU DIST-S1 validation: 3-event aggregate (Phase 5 v1.1)
#
# Replaces v1.0 run_eval_dist_eu.py (Aveiro Sept 28 only) + v1.0
# run_eval_dist_eu_nov15.py (Aveiro Nov 15 only). The Nov 15 logic
# becomes the aveiro event's chained_retry sub-stage; the standalone
# Nov15 script is deleted by Plan 05-08.
#
# Events (CONTEXT D-11 + RESEARCH Probe 4 + Probe 8):
#   - aveiro: 2024 Portuguese wildfires (Aveiro/Viseu); MGRS 29TNF; track 147
#     Chained triple: Sept 28 -> Oct 10 -> Nov 15 (DIST-07 differentiator).
#   - evros: 2023 Greek wildfires (Alexandroupolis); EMSR686;
#     MGRS 35TLF; track number probed at runtime (Warning 9 fix)
#   - spain_culebra: June 2022 Sierra de la Culebra fire (Zamora province);
#     MGRS 29TQG; track number probed at runtime (RESEARCH Probe 4 + Probe 8)
#
# Track-number probe (Task 0 logic, inlined in main()):
#   The previously-speculative track_number=29 (evros) and track_number=125
#   (spain_culebra) values are *defaults* used only if the runtime probe
#   via dist_s1_enumerator.get_mgrs_tiles_overlapping_geometry fails. On
#   a successful probe, the EVENTS list track_numbers are overwritten with
#   the probe-derived values BEFORE the per-event loop starts.
#
# Reference: EFFIS REST burnt-area perimeters (DIST-05) via Plan 05-05 effis.py;
# rasterised onto subsideo's 30 m DIST-STATUS grid (CONTEXT D-17 dual-rasterise).
#
# Pre-conditions
# --------------
# - EARTHDATA_USERNAME / EARTHDATA_PASSWORD env vars (ASF DAAC + earthaccess).
# - subsideo conda env with dist-s1 2.0.14, earthaccess >= 0.12.
# - _mp.configure_multiprocessing() fires at top of main() (PITFALLS P0.1
#   pre-condition for DIST-07 chained retry).
# - eval-dist_eu/effis_endpoint_lock.txt populated by Plan 05-02 (EFFIS_REST_URL
#   imported via validation.effis module-level constants).
#
# Wallclock budget
# ----------------
# EXPECTED_WALL_S = 60 * 60 * 8 (8 hours). Per-event estimate:
#   - aveiro: warm path ~1h (cached SAFEs from v1.0); chained retry ~30 min
#   - evros: cold path ~2h (no v1.0 cache)
#   - spain_culebra: cold path ~2h
# Total cold: ~5-6h; warm: ~1-2h. 8h = mid-range estimate per CONTEXT D-12.
# Supervisor budget = 2*EXPECTED_WALL_S = 16h (Phase 1 ENV-05).
import warnings; warnings.filterwarnings("ignore")  # noqa: E702, I001

EXPECTED_WALL_S = 60 * 60 * 8   # 28800s; supervisor AST-parses (Phase 1 D-11)


if __name__ == "__main__":
    # Phase 1 ENV-04 mandatory: PITFALLS P0.1 binding pre-condition for DIST-07
    # chained retry; idempotent + thread-safe. Fires BEFORE any
    # requests.Session-using import (asf_search, earthaccess) and BEFORE
    # `from dist_s1 import run_dist_s1_workflow` import.
    from subsideo._mp import configure_multiprocessing
    configure_multiprocessing()

    import platform
    import subprocess
    import sys
    import time
    import traceback
    from dataclasses import dataclass
    from datetime import date, datetime, timezone
    from pathlib import Path
    from typing import Literal

    import numpy as np
    import rasterio
    from dotenv import load_dotenv
    from loguru import logger

    from subsideo.validation.bootstrap import (
        DEFAULT_BLOCK_SIZE_M,
        DEFAULT_N_BOOTSTRAP,
        DEFAULT_RNG_SEED,
        block_bootstrap_ci,
    )
    from subsideo.validation.compare_dist import DIST_DISTURBED_LABELS, _binarize_dist
    from subsideo.validation.effis import (
        fetch_effis_perimeters,
        rasterise_perimeters_to_grid,
    )
    from subsideo.validation.harness import (
        credential_preflight,
    )
    from subsideo.validation.matrix_schema import (
        BootstrapConfig,
        ChainedRunResult,
        DistEUCellMetrics,
        DistEUEventMetrics,
        EFFISQueryMeta,
        MetaJson,
        MetricWithCI,
        ProductQualityResultJson,
        RasterisationDiagnostic,
        ReferenceAgreementResultJson,
    )
    from subsideo.validation.metrics import (
        f1_score,
        overall_accuracy,
        precision_score,
        recall_score,
    )

    load_dotenv()
    credential_preflight(["EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"])

    run_started = datetime.now(timezone.utc)
    t_start = time.time()

    # -- Configuration -------------------------------------------------------

    @dataclass(frozen=False)  # frozen=False so the track-number probe can update
    class EventConfig:
        """Per-event declarative config (CONTEXT D-11)."""

        event_id: Literal["aveiro", "evros", "spain_culebra"]
        # Sept 28 / Oct 10 / Nov 15 for aveiro chained triple; single entry for others
        post_dates: list[date]
        aoi_bbox_wgs84: tuple[float, float, float, float]  # (W, S, E, N)
        mgrs_tile: str
        track_number: int               # may be overwritten by Task 0 probe
        track_number_source: str        # "v1.0_cache" / "probed" / "speculative_fallback"
        effis_filter_dates: tuple[date, date]   # (start, end) for firedate range filter
        expected_burnt_area_km2: float          # narrative sanity check; not a gate
        run_chained: bool               # True for aveiro only (DIST-07)
        # subsideo v1.0 default; differs from dist-s1 2.0.14 default of 1
        post_date_buffer_days: int = 5

    EVENTS: list[EventConfig] = [
        EventConfig(
            event_id="aveiro",
            post_dates=[date(2024, 9, 28), date(2024, 10, 10), date(2024, 11, 15)],
            aoi_bbox_wgs84=(-8.8, 40.5, -8.2, 41.0),
            mgrs_tile="29TNF",
            track_number=147,
            track_number_source="v1.0_cache",  # locked from v1.0 run_eval_dist_eu.py provenance
            effis_filter_dates=(date(2024, 9, 15), date(2024, 9, 25)),
            expected_burnt_area_km2=1350.0,  # 135,000 ha
            run_chained=True,
        ),
        EventConfig(
            event_id="evros",  # EMSR686; corrected from CONTEXT.md per RESEARCH Probe 8
            post_dates=[date(2023, 9, 5)],  # ~17 days after fire onset
            aoi_bbox_wgs84=(25.9, 40.7, 26.7, 41.4),
            mgrs_tile="35TLF",  # RESEARCH Probe 8 candidate; probe may correct
            track_number=29,    # speculative fallback per RESEARCH Probe 8
            track_number_source="speculative_fallback",  # Task 0 probe will overwrite
            effis_filter_dates=(date(2023, 8, 19), date(2023, 9, 8)),
            expected_burnt_area_km2=942.5,  # 94,250 ha; largest EU forest fire ever
            run_chained=False,
        ),
        EventConfig(
            event_id="spain_culebra",  # substituted per RESEARCH Probe 4 (EFFIS fire-only)
            post_dates=[date(2022, 6, 28)],  # ~7 days after fire onset
            aoi_bbox_wgs84=(-6.5, 41.7, -5.9, 42.2),
            mgrs_tile="29TQG",  # RESEARCH Probe 8 candidate; probe may correct
            track_number=125,   # speculative fallback per RESEARCH Probe 8
            track_number_source="speculative_fallback",  # Task 0 probe will overwrite
            effis_filter_dates=(date(2022, 6, 15), date(2022, 6, 22)),
            expected_burnt_area_km2=260.0,  # 26,000 ha
            run_chained=False,
        ),
    ]

    CACHE = Path("./eval-dist_eu")  # underscore convention from matrix_manifest.yml
    CACHE.mkdir(exist_ok=True)

    # -- Task 0: Track-number probe (Warning 9 fix from checker iteration 1) -

    def _probe_track_numbers_for_events(events: list[EventConfig]) -> list[EventConfig]:
        """Resolve track_number for events whose source is 'speculative_fallback'.

        Uses dist_s1_enumerator.get_mgrs_tiles_overlapping_geometry over the
        event AOI bbox to find S1 acquisitions covering the AOI. Picks the
        most-frequent track_number across the covering granules.

        On probe failure (e.g., dist_s1_enumerator API change, no granules
        found), the speculative fallback value is kept and logged. Aveiro's
        track_number_source='v1.0_cache' bypasses the probe entirely.
        """
        try:
            from dist_s1_enumerator import get_mgrs_tiles_overlapping_geometry
        except ImportError:
            logger.warning(
                "dist_s1_enumerator.get_mgrs_tiles_overlapping_geometry "
                "unavailable; track_numbers stay at speculative_fallback values"
            )
            return events
        try:
            from shapely.geometry import box as shapely_box
        except ImportError:
            logger.warning("shapely unavailable; cannot construct probe geometry")
            return events

        updated: list[EventConfig] = []
        for cfg in events:
            if cfg.track_number_source != "speculative_fallback":
                updated.append(cfg)
                continue
            try:
                aoi_geom = shapely_box(*cfg.aoi_bbox_wgs84)
                # Probe API surface is approximate per RESEARCH Probe 8;
                # adapt to the actual signature returned by your installed version.
                probe_results = get_mgrs_tiles_overlapping_geometry(
                    geometry=aoi_geom,
                )
                # Filter to entries that mention the configured mgrs_tile,
                # collect track_numbers, pick the mode (most-frequent).
                # The exact field names ('mgrs_tile_id', 'track_number') may
                # vary by enumerator version; the probe is best-effort.
                track_candidates = []
                for entry in (probe_results or []):
                    entry_dict = (
                        entry if isinstance(entry, dict)
                        else getattr(entry, "__dict__", {})
                    )
                    tile = entry_dict.get("mgrs_tile_id") or entry_dict.get("tile_id")
                    track = (
                        entry_dict.get("track_number")
                        or entry_dict.get("relative_orbit_number")
                    )
                    if tile == cfg.mgrs_tile and track is not None:
                        track_candidates.append(int(track))

                if track_candidates:
                    from collections import Counter
                    most_common_track, _count = Counter(track_candidates).most_common(1)[0]
                    if most_common_track != cfg.track_number:
                        logger.info(
                            "Track-number probe: {} mgrs_tile={} probed_track={} "
                            "(was speculative={}; overwriting)",
                            cfg.event_id, cfg.mgrs_tile, most_common_track, cfg.track_number,
                        )
                    cfg.track_number = most_common_track
                    cfg.track_number_source = "probed"
                else:
                    logger.warning(
                        "Track-number probe: no candidates for {} mgrs_tile={}; "
                        "keeping speculative fallback track_number={}",
                        cfg.event_id, cfg.mgrs_tile, cfg.track_number,
                    )
            except Exception as e:
                logger.warning(
                    "Track-number probe failed for {}: {}: {}; "
                    "keeping speculative fallback track_number={}",
                    cfg.event_id, type(e).__name__, e, cfg.track_number,
                )
            updated.append(cfg)
        return updated

    print("=" * 70)
    print("DIST-S1 EU Evaluation: 3-event aggregate (Phase 5 v1.1)")
    print("=" * 70)
    print("-- Task 0: Track-number probe --")
    EVENTS = _probe_track_numbers_for_events(EVENTS)
    for cfg in EVENTS:
        print(f"  {cfg.event_id:15s} mgrs_tile={cfg.mgrs_tile:6s} track={cfg.track_number:4d} "
              f"(source={cfg.track_number_source})")
    print()

    # -- Per-event pipeline helpers ------------------------------------------

    def _run_dist_for_event_post(
        cfg: EventConfig,
        post_date: date,
        out_dir: Path,
        prior_product: Path | None = None,
    ) -> Path:
        """Single dist_s1 invocation for one (event, post_date) tuple."""
        from dist_s1 import run_dist_s1_workflow

        # Resume guard: check for an actual GEN-DIST-STATUS.tif sentinel file
        # rather than passing a glob pattern to ensure_resume_safe (which
        # performs exact filename membership testing, not glob matching --
        # see harness.py:432). HI-01 fix.
        if out_dir.exists():
            existing_sentinel = next(out_dir.glob("*GEN-DIST-STATUS.tif"), None)
            if existing_sentinel is not None:
                logger.info(
                    "dist_s1 cached for {} {} at {}", cfg.event_id, post_date, out_dir
                )
                return out_dir

        out_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "dist_s1 RUN: event={} post_date={} prior={}",
            cfg.event_id, post_date, prior_product,
        )
        run_dist_s1_workflow(
            mgrs_tile_id=cfg.mgrs_tile,
            post_date=post_date.isoformat(),
            track_number=cfg.track_number,
            dst_dir=out_dir,
            post_date_buffer_days=cfg.post_date_buffer_days,
            device="cpu",
            memory_strategy="high",
            prior_dist_s1_product=str(prior_product) if prior_product else None,
        )
        return out_dir

    def _chained_retry_for_aveiro(cfg: EventConfig, base_dir: Path) -> ChainedRunResult:
        """DIST-07 chained prior_dist_s1_product retry (CONTEXT D-13/D-14).

        Threads the prior product through the triple: Sept 28 (no prior) ->
        Oct 10 (prior=Sept 28) -> Nov 15 (prior=Oct 10). Pass criterion
        (CONTEXT D-14): structurally-valid 10-layer DIST-ALERT product.
        Section 4 of CONCLUSIONS_DIST_EU.md handles None ChainedRunResult
        gracefully (Plan 05-09 substitution recipe).

        The missing Oct 10 invocation (RESEARCH Risk Open Q5; v1.0 cache had
        only Sept 28 + Nov 15) is added HERE as the middle stage, ensuring
        the full three-date chain runs.
        """
        chained_dst = base_dir / "chained"
        try:
            sept28_dir = base_dir / "sept28"
            _run_dist_for_event_post(cfg, cfg.post_dates[0], sept28_dir, prior_product=None)
            # Oct 10 is the MISSING middle stage from v1.0; added per RESEARCH Probe 10
            oct10_dir = base_dir / "oct10"
            _run_dist_for_event_post(cfg, cfg.post_dates[1], oct10_dir, prior_product=sept28_dir)
            chained_dst.mkdir(parents=True, exist_ok=True)
            _run_dist_for_event_post(cfg, cfg.post_dates[2], chained_dst, prior_product=oct10_dir)

            from dist_s1.data_models.output_models import DistS1ProductDirectory
            DistS1ProductDirectory.from_path(chained_dst)  # raises on invalid

            n_layers = sum(1 for _ in chained_dst.glob("*GEN-*.tif"))
            dist_status_path = next(chained_dst.glob("*GEN-DIST-STATUS.tif"), None)

            dist_status_nonempty: bool | None = None
            if dist_status_path is not None:
                with rasterio.open(dist_status_path) as ds:
                    dist_status_nonempty = bool((ds.read(1) > 0).any())

            structurally_valid = n_layers == 10 and bool(dist_status_nonempty)
            return ChainedRunResult(
                status="structurally_valid" if structurally_valid else "partial_output",
                output_dir=str(chained_dst),
                n_layers_present=n_layers,
                dist_status_nonempty=dist_status_nonempty,
            )
        except Exception as e:
            logger.error("chained_retry crashed for {}: {}", cfg.event_id, e)
            return ChainedRunResult(
                status="crashed",
                output_dir=str(chained_dst) if chained_dst.exists() else None,
                error=repr(e),
                traceback=traceback.format_exc(),
            )

    def _binarise_subsideo_to_disturbed_mask(dist_status_path: Path) -> tuple[np.ndarray, dict]:
        """Read subsideo's GEN-DIST-STATUS COG and return a binary mask."""
        with rasterio.open(dist_status_path) as ds:
            raster = ds.read(1)
            profile = ds.profile
        binarised = _binarize_dist(raster, disturbed_labels=DIST_DISTURBED_LABELS)
        return binarised, profile

    def process_event(cfg: EventConfig) -> DistEUEventMetrics:
        """End-to-end per-event pipeline (CONTEXT D-10/D-11/D-13)."""
        base_dir = CACHE / cfg.event_id
        base_dir.mkdir(parents=True, exist_ok=True)

        primary_post = cfg.post_dates[0]
        primary_dist_dir = base_dir / "dist_output"
        _run_dist_for_event_post(cfg, primary_post, primary_dist_dir, prior_product=None)

        dist_status_path = next(primary_dist_dir.glob("*GEN-DIST-STATUS.tif"), None)
        if dist_status_path is None:
            raise RuntimeError(
                f"dist_s1 produced no GEN-DIST-STATUS.tif under {primary_dist_dir} "
                f"for {cfg.event_id} {primary_post}"
            )

        subsideo_mask, profile = _binarise_subsideo_to_disturbed_mask(dist_status_path)

        gdf, effis_meta = fetch_effis_perimeters(
            event_id=cfg.event_id,
            bbox_wgs84=cfg.aoi_bbox_wgs84,
            date_start=cfg.effis_filter_dates[0],
            date_end=cfg.effis_filter_dates[1],
            cache_dir=CACHE,
        )

        target_crs = profile["crs"]
        gdf_utm = gdf.to_crs(target_crs)
        out_shape = (profile["height"], profile["width"])
        transform = profile["transform"]

        mask_at_false_uint8, mask_at_true_uint8 = rasterise_perimeters_to_grid(
            gdf_utm, out_shape, transform
        )
        mask_at_false = mask_at_false_uint8.astype(np.float32)
        mask_at_true = mask_at_true_uint8.astype(np.float32)

        f1_ci = block_bootstrap_ci(
            subsideo_mask, mask_at_false, metric_fn=f1_score,
            block_size_m=DEFAULT_BLOCK_SIZE_M,
            n_bootstrap=DEFAULT_N_BOOTSTRAP, rng_seed=DEFAULT_RNG_SEED,
        )
        prec_ci = block_bootstrap_ci(
            subsideo_mask, mask_at_false, metric_fn=precision_score,
            block_size_m=DEFAULT_BLOCK_SIZE_M,
            n_bootstrap=DEFAULT_N_BOOTSTRAP, rng_seed=DEFAULT_RNG_SEED,
        )
        rec_ci = block_bootstrap_ci(
            subsideo_mask, mask_at_false, metric_fn=recall_score,
            block_size_m=DEFAULT_BLOCK_SIZE_M,
            n_bootstrap=DEFAULT_N_BOOTSTRAP, rng_seed=DEFAULT_RNG_SEED,
        )
        acc_ci = block_bootstrap_ci(
            subsideo_mask, mask_at_false, metric_fn=overall_accuracy,
            block_size_m=DEFAULT_BLOCK_SIZE_M,
            n_bootstrap=DEFAULT_N_BOOTSTRAP, rng_seed=DEFAULT_RNG_SEED,
        )

        # Diagnostic: F1 with all_touched=True rasterisation (CONTEXT D-17)
        f1_at_true = f1_score(subsideo_mask.ravel(), mask_at_true.ravel())

        chained: ChainedRunResult | None = None
        if cfg.run_chained:
            chained = _chained_retry_for_aveiro(cfg, base_dir)

        f1_pass = f1_ci.point_estimate > 0.80
        acc_pass = acc_ci.point_estimate > 0.85
        prec_pass = prec_ci.point_estimate > 0.70
        rec_pass = rec_ci.point_estimate > 0.50
        all_criteria_pass = f1_pass and acc_pass and prec_pass and rec_pass
        status: Literal["PASS", "FAIL"] = "PASS" if all_criteria_pass else "FAIL"

        # Warning 11 fix: BootstrapConfig.block_size_m uses DEFAULT_BLOCK_SIZE_M directly
        # (dead-code arithmetic from checker iteration 1 is removed).
        return DistEUEventMetrics(
            event_id=cfg.event_id,
            status=status,
            f1=MetricWithCI(
                point=f1_ci.point_estimate,
                ci_lower=f1_ci.ci_lower,
                ci_upper=f1_ci.ci_upper,
            ),
            precision=MetricWithCI(
                point=prec_ci.point_estimate,
                ci_lower=prec_ci.ci_lower,
                ci_upper=prec_ci.ci_upper,
            ),
            recall=MetricWithCI(
                point=rec_ci.point_estimate,
                ci_lower=rec_ci.ci_lower,
                ci_upper=rec_ci.ci_upper,
            ),
            accuracy=MetricWithCI(
                point=acc_ci.point_estimate,
                ci_lower=acc_ci.ci_lower,
                ci_upper=acc_ci.ci_upper,
            ),
            rasterisation_diagnostic=RasterisationDiagnostic(
                all_touched_false_f1=f1_ci.point_estimate,
                all_touched_true_f1=f1_at_true,
                delta_f1=f1_at_true - f1_ci.point_estimate,
            ),
            bootstrap_config=BootstrapConfig(
                block_size_m=DEFAULT_BLOCK_SIZE_M,
                n_bootstrap=f1_ci.n_bootstrap,
                ci_level=f1_ci.ci_level,
                n_blocks_kept=f1_ci.n_blocks_kept,
                n_blocks_dropped=f1_ci.n_blocks_dropped,
                rng_seed=f1_ci.rng_seed,
            ),
            effis_query_meta=effis_meta,
            chained_run=chained,
        )

    # -- Main loop -----------------------------------------------------------
    print(f"  Cache dir    : {CACHE}")
    print(f"  EXPECTED_WALL: {EXPECTED_WALL_S}s")
    print()

    per_event: list[DistEUEventMetrics] = []
    for cfg in EVENTS:
        t_event_start = time.time()
        print(f"-- Event: {cfg.event_id} (track={cfg.track_number}) --")
        try:
            row = process_event(cfg)
            per_event.append(row)
            elapsed = time.time() - t_event_start
            print(f"  {cfg.event_id} {row.status} in {elapsed:.0f}s "
                  f"(f1={row.f1.point:.3f} [{row.f1.ci_lower:.3f}, {row.f1.ci_upper:.3f}])")
        except Exception as e:  # noqa: BLE001 -- per-event isolation (Phase 2 D-06)
            elapsed = time.time() - t_event_start
            tb = traceback.format_exc()
            logger.error("Event {} FAIL ({:.0f}s): {}", cfg.event_id, elapsed, e)
            per_event.append(
                DistEUEventMetrics(
                    event_id=cfg.event_id,
                    status="FAIL",
                    f1=MetricWithCI(point=0.0, ci_lower=0.0, ci_upper=0.0),
                    precision=MetricWithCI(point=0.0, ci_lower=0.0, ci_upper=0.0),
                    recall=MetricWithCI(point=0.0, ci_lower=0.0, ci_upper=0.0),
                    accuracy=MetricWithCI(point=0.0, ci_lower=0.0, ci_upper=0.0),
                    rasterisation_diagnostic=RasterisationDiagnostic(
                        all_touched_false_f1=0.0, all_touched_true_f1=0.0, delta_f1=0.0,
                    ),
                    bootstrap_config=BootstrapConfig(n_blocks_kept=0, n_blocks_dropped=0),
                    effis_query_meta=EFFISQueryMeta(
                        wfs_endpoint="", layer_name="", filter_string="",
                        response_feature_count=0, fetched_at=run_started.isoformat(),
                    ),
                    chained_run=None,
                    error=repr(e),
                    traceback=tb,
                )
            )

    # -- Aggregate write -----------------------------------------------------
    pass_count = sum(1 for r in per_event if r.status == "PASS")
    total = len(per_event)
    worst_event = min(per_event, key=lambda r: r.f1.point)
    any_chained_failed = any(
        r.chained_run is not None
        and r.chained_run.status not in ("structurally_valid", "skipped")
        for r in per_event
    )
    cell_status: Literal["PASS", "FAIL", "MIXED", "BLOCKER"]
    if pass_count == total:
        cell_status = "PASS"
    elif pass_count == 0:
        cell_status = "FAIL"
    else:
        cell_status = "MIXED"

    metrics = DistEUCellMetrics(
        product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResultJson(
            measurements={"worst_f1": worst_event.f1.point},
            criterion_ids=["dist.f1_min", "dist.accuracy_min"],
        ),
        criterion_ids_applied=["dist.f1_min", "dist.accuracy_min"],
        pass_count=pass_count,
        total=total,
        all_pass=(pass_count == total),
        cell_status=cell_status,
        worst_event_id=worst_event.event_id,
        worst_f1=worst_event.f1.point,
        any_chained_run_failed=any_chained_failed,
        per_event=per_event,
    )
    metrics_path = CACHE / "metrics.json"
    metrics_path.write_text(metrics.model_dump_json(indent=2))

    # -- Provenance write ----------------------------------------------------
    # MetaJson field names verified verbatim against
    # src/subsideo/validation/matrix_schema.py:68-114. The previous draft
    # used `subsideo_version`, `timestamp_utc_start`, `timestamp_utc_end`,
    # `wall_seconds` -- those are NOT MetaJson fields. Pydantic v2
    # `extra="forbid"` rejects them at construction time. The actual fields
    # are: schema_version, git_sha, git_dirty, run_started_iso,
    # run_duration_s, python_version, platform, input_hashes
    # (Blocker 1 fix from checker iteration 1).
    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent, text=True
        ).strip()
    except Exception:
        git_sha = "<unknown>"
    try:
        porcelain = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=Path(__file__).parent, text=True
        ).strip()
        git_dirty = bool(porcelain)
    except Exception:
        git_dirty = False

    run_duration_s = time.time() - t_start
    meta = MetaJson(
        schema_version=1,
        git_sha=git_sha,
        git_dirty=git_dirty,
        run_started_iso=run_started.isoformat(),
        run_duration_s=run_duration_s,
        python_version=platform.python_version(),
        platform=platform.platform(),
        input_hashes={
            f"effis_perimeters_{r.event_id}": r.effis_query_meta.filter_string[:64]
            for r in per_event if r.effis_query_meta.filter_string
        },
    )
    meta_path = CACHE / "meta.json"
    meta_path.write_text(meta.model_dump_json(indent=2))

    print()
    print("=" * 70)
    print(f"DIST-S1 EU eval complete: {pass_count}/{total} PASS, cell_status={cell_status}, "
          f"worst f1={worst_event.f1.point:.3f} ({worst_event.event_id})")
    if any_chained_failed:
        print("  WARNING: At least one chained_run did not produce a structurally-valid product")
    print(f"  metrics_path: {metrics_path}")
    print(f"  meta_path:    {meta_path}")
    print("=" * 70)
    sys.exit(0)
