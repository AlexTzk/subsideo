# run_eval_dist.py -- N.Am. DIST-S1 validation (Phase 5 scope amendment)
#
# This script runs every `make eval-dist-nam` invocation. Per the Phase 5
# scope amendment (2026-04-25), the dist:nam matrix cell ships as DEFERRED
# pending operational publication of OPERA_L3_DIST-ALERT-S1_V1 in CMR
# (RESEARCH Probes 1 + 6 confirmed: no canonical CloudFront URL for the
# v0.1 sample; operational collection is empty as of 2026-04-25).
#
# Behaviour
# ---------
# Stage 0 (the only stage in Phase 5):
#   - Authenticate to NASA Earthdata via earthaccess.login(strategy='environment').
#   - Query CMR for OPERA_L3_DIST-ALERT-S1_V1 covering T11SLT 2025-01-21
#     +/- CMR_TEMPORAL_TOLERANCE_DAYS.
#   - Outcome 'operational_not_found' (the expected Phase 5 outcome) ->
#     write deferred metrics.json + meta.json; matrix_writer renders the
#     cell as 'DEFERRED (CMR: operational_not_found)'.
#   - Outcome 'operational_found' -> CONTEXT D-16 archival: if
#     eval-dist/metrics.json exists, move it to
#     eval-dist/archive/v0.1_metrics_<mtime-iso>.json. Then raise
#     NotImplementedError; the v1.2 work item is to land the full Stage
#     1+ F1+CI pipeline. v1.2 will replace the raise with the pipeline
#     call; the archive directory contract is already in place.
#   - Outcome 'probe_failed' (network/auth/CMR error) -> log and write
#     deferred metrics.json with cmr_probe_outcome='probe_failed'.
#
# Park Fire (v1.0 baseline, 10TFK) cache is preserved at
# eval-dist-park-fire/ (renamed by Plan 05-08); CONCLUSIONS_DIST_N_AM.md
# preserves the v1.0 narrative as historical-baseline preamble (Plan 05-09).
#
# Pre-conditions
# --------------
# - EARTHDATA_USERNAME / EARTHDATA_PASSWORD env vars (for earthaccess.login).
# - subsideo conda env with earthaccess >= 0.12.
# - _mp.configure_multiprocessing() fires at top of __main__ (Phase 1 ENV-04).
# - Subprocess-level supervisor watchdog wraps this invocation
#   (Makefile: `make eval-dist-nam` -> python -m subsideo.validation.supervisor run_eval_dist.py).
#
# Wallclock budget
# ----------------
# EXPECTED_WALL_S = 60 * 60 * 3 (3 hours). The deferred path completes in
# ~30 s (CMR probe + JSON dump). The 3-hour budget is pre-allocated for
# the v1.2 full pipeline (regenerate v0.1 sample locally + run dist-s1 +
# bootstrap CI), which estimates 1.5-2 h cold + safety margin. Keeping
# the budget at v1.2 size now means future migration doesn't need a
# budget bump (Warning 10 fix from checker iteration 1).
# Supervisor budget = 2*EXPECTED_WALL_S = 6h (Phase 1 ENV-05 contract).
import warnings  # noqa: I001

warnings.filterwarnings("ignore")

EXPECTED_WALL_S = 60 * 60 * 3   # 10800s; supervisor AST-parses (Phase 1 D-11)


def _resolve_git_sha_and_dirty(repo_root: object) -> tuple[str, bool]:
    """Return (git_sha, git_dirty) or ('<unknown>', False) if git unavailable.

    Subprocess-level helper. Two-call form because `git rev-parse HEAD`
    and `git status --porcelain` are independent operations; we tolerate
    either failing without aborting the eval.
    """
    import subprocess

    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True
        ).strip()
    except Exception:
        sha = "<unknown>"
    try:
        porcelain = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=repo_root, text=True
        ).strip()
        dirty = bool(porcelain)
    except Exception:
        dirty = False
    return sha, dirty


def run() -> int:
    """Execute Stage 0 CMR probe + DEFERRED metrics.json + meta.json write.

    Refactored as a function so tests/unit/test_run_eval_dist_cmr_stage0.py
    can monkey-patch ``earthaccess`` and drive the three CMR outcomes
    without spawning a subprocess.

    Returns 0 on success (operational_not_found or probe_failed paths);
    raises NotImplementedError on operational_found (v1.2 trigger).
    """
    import platform
    import shutil
    import time
    import traceback
    from datetime import datetime, timedelta, timezone
    from pathlib import Path

    import earthaccess
    from dotenv import load_dotenv
    from loguru import logger

    from subsideo.validation.harness import (
        bounds_for_mgrs_tile,
        credential_preflight,
    )
    from subsideo.validation.matrix_schema import (
        DistNamCellMetrics,
        MetaJson,
        ProductQualityResultJson,
        ReferenceAgreementResultJson,
    )

    load_dotenv()
    credential_preflight(["EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"])

    run_started = datetime.now(timezone.utc)
    t_start = time.time()

    # -- Configuration -------------------------------------------------------
    # Constants kept ALL_CAPS (the planner specifies these names verbatim) and
    # noqa'd for ruff N806 — they are module-style constants moved into run()
    # only so unit tests can monkey-patch earthaccess without spawning a subprocess.
    AOI_NAME = "Los Angeles January 2025 wildfires (Palisades + Eaton)"  # noqa: N806
    MGRS_TILE = "11SLT"  # noqa: N806  -- NOT 'T11SLT'; dist_s1 expects no T prefix
    POST_DATE = "2025-01-21"  # noqa: N806
    CMR_TEMPORAL_TOLERANCE_DAYS = 7  # noqa: N806  -- +/- around POST_DATE

    OUT = Path("./eval-dist")  # noqa: N806
    OUT.mkdir(exist_ok=True)
    ARCHIVE_DIR = OUT / "archive"  # noqa: N806  -- CONTEXT D-16

    print("=" * 70)
    print("DIST-S1 N.Am. Evaluation: Phase 5 (deferred + CMR auto-supersede)")
    print("=" * 70)
    print(f"  AOI            : {AOI_NAME}")
    print(f"  MGRS tile      : {MGRS_TILE}")
    print(f"  Post date      : {POST_DATE}")
    print(f"  CMR tolerance  : +/- {CMR_TEMPORAL_TOLERANCE_DAYS} days")
    print(f"  Cache dir      : {OUT}")
    print(f"  Archive dir    : {ARCHIVE_DIR} (CONTEXT D-16)")
    print(
        f"  Expected wall  : {EXPECTED_WALL_S}s (deferred path completes in ~30s; "
        f"budget pre-allocated for v1.2 full pipeline)"
    )
    print()

    # -- Stage 0: CMR probe --------------------------------------------------
    print("-- Stage 0: CMR auto-supersede probe (DIST-04) --")
    auth = earthaccess.login(strategy="environment")
    auth_ok = auth and getattr(auth, "authenticated", False)
    print(f"  Earthdata auth : {'OK' if auth_ok else 'FAIL'}")

    try:
        bbox = bounds_for_mgrs_tile(MGRS_TILE)
        print(f"  T{MGRS_TILE} bbox : {bbox}")
    except Exception as e:
        logger.error("bounds_for_mgrs_tile({}) failed: {}", MGRS_TILE, e)
        bbox = (-119.0, 33.5, -118.0, 34.5)  # RESEARCH Probe 6 fallback for T11SLT
        print(
            f"  T{MGRS_TILE} bbox : {bbox} "
            f"(fallback; bounds_for_mgrs_tile failed: {type(e).__name__})"
        )

    post_dt = datetime.fromisoformat(POST_DATE)
    temporal_start = (post_dt - timedelta(days=CMR_TEMPORAL_TOLERANCE_DAYS)).strftime("%Y-%m-%d")
    temporal_end = (post_dt + timedelta(days=CMR_TEMPORAL_TOLERANCE_DAYS)).strftime("%Y-%m-%d")
    print(f"  Temporal       : {temporal_start} -> {temporal_end}")

    # CMRProbeOutcome / ReferenceSource Literals
    cmr_probe_outcome: str  # one of CMRProbeOutcome Literal values
    reference_source: str   # one of ReferenceSource Literal values
    reference_granule_id: str | None = None

    try:
        results = earthaccess.search_data(
            short_name="OPERA_L3_DIST-ALERT-S1_V1",
            bounding_box=bbox,
            temporal=(temporal_start, temporal_end),
            count=20,
        )
        n_hits = len(results) if results else 0
        print(f"  CMR results    : {n_hits} hit(s)")
        if results:
            cmr_probe_outcome = "operational_found"
            reference_source = "operational_v1"
            # Defensive granule_id extraction: earthaccess.DataGranule API
            # has shifted across versions.
            try:
                first = results[0]
                if hasattr(first, "render_dict"):
                    umm = first.render_dict()
                    reference_granule_id = umm.get("meta", {}).get("concept-id")
                elif isinstance(first, dict):
                    reference_granule_id = first.get("meta", {}).get("concept-id")
                if reference_granule_id is None:
                    reference_granule_id = repr(first)[:100]
            except Exception as ge:
                reference_granule_id = f"<extraction-failed: {type(ge).__name__}>"
            print(f"  Granule        : {reference_granule_id}")

            # CONTEXT D-16: archive any pre-existing metrics.json BEFORE
            # the v1.2 pipeline overwrites it. Implementing the archival
            # hook now (rather than in v1.2) costs ~10 LOC, is unit-testable,
            # and avoids a v1.2 hazard where the archival contract gets lost.
            existing_metrics = OUT / "metrics.json"
            if existing_metrics.exists():
                ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
                mtime_iso = (
                    datetime.fromtimestamp(existing_metrics.stat().st_mtime, tz=timezone.utc)
                    .isoformat()
                    .replace(":", "-")  # filesystem-safe
                )
                archive_dst = ARCHIVE_DIR / f"v0.1_metrics_{mtime_iso}.json"
                shutil.move(str(existing_metrics), str(archive_dst))
                logger.info(
                    "CONTEXT D-16 archival: moved {} -> {} (mtime preserved in filename)",
                    existing_metrics, archive_dst,
                )
                print(f"  D-16 archived  : {archive_dst}")

            # Phase 5 scope amendment: the operational-found path is v1.2
            # work. v1.2 will replace this raise with the actual pipeline
            # call; the archival hook above is already in place.
            raise NotImplementedError(
                "OPERA_L3_DIST-ALERT-S1_V1 is now published in CMR. The full F1+CI "
                "pipeline (regenerate v0.1 sample locally, run dist-s1 over T11SLT, "
                "bootstrap CI, write full DistNamCellMetrics schema) is v1.2 work "
                "per the Phase 5 scope amendment. Re-plan via `/gsd:plan-phase 5 "
                "--gaps` once the v1.2 milestone activates. "
                "CONTEXT D-16 archival of any prior eval-dist/metrics.json has "
                "already been performed (see archive/ directory). "
                f"Granule: {reference_granule_id}"
            )
        else:
            cmr_probe_outcome = "operational_not_found"
            reference_source = "none"
    except NotImplementedError:
        # Re-raise the v1.2-trigger signal to surface upward; supervisor catches.
        raise
    except Exception as e:
        logger.error("CMR probe failed: {}", e)
        traceback.print_exc()
        cmr_probe_outcome = "probe_failed"
        reference_source = "none"

    print(f"  Outcome        : {cmr_probe_outcome}")
    print()

    # -- Stage 1: Write deferred metrics.json --------------------------------
    print("-- Stage 1: Write deferred metrics.json (Phase 5 scope amendment) --")
    metrics = DistNamCellMetrics(
        product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResultJson(measurements={}, criterion_ids=[]),
        criterion_ids_applied=[],
        cell_status="DEFERRED",
        reference_source=reference_source,  # type: ignore[arg-type]
        cmr_probe_outcome=cmr_probe_outcome,  # type: ignore[arg-type]
        reference_granule_id=reference_granule_id,
        deferred_reason=(
            "Phase 5 scope amendment 2026-04-25: DIST-01 / DIST-02 / DIST-03 deferred "
            "to v1.2. RESEARCH Probe 1 found that the OPERA v0.1 sample has no canonical "
            "CloudFront URL (notebook-recipe regeneration only); RESEARCH Probe 6 "
            "confirmed OPERA_L3_DIST-ALERT-S1_V1 returns empty in CMR as of 2026-04-25. "
            "The CMR auto-supersede probe (DIST-04) runs every invocation; on operational "
            "publication mid-v1.x, this script archives any prior metrics.json to "
            "eval-dist/archive/ (CONTEXT D-16) and raises NotImplementedError to trigger "
            "the v1.2 re-plan."
        ),
    )
    metrics_path = OUT / "metrics.json"
    metrics_path.write_text(metrics.model_dump_json(indent=2))
    print(f"  Wrote          : {metrics_path}")

    # -- Stage 2: Write meta.json (provenance) -------------------------------
    # Field names verified verbatim against
    # src/subsideo/validation/matrix_schema.py:68-114 (MetaJson definition).
    # Pydantic v2 `extra='forbid'` rejects any drifted name at construction
    # time. Actual fields: schema_version, git_sha, git_dirty,
    # run_started_iso, run_duration_s, python_version, platform, input_hashes.
    print("-- Stage 2: Write meta.json (provenance) --")
    git_sha, git_dirty = _resolve_git_sha_and_dirty(Path(__file__).parent)

    run_duration_s = time.time() - t_start
    meta = MetaJson(
        schema_version=1,
        git_sha=git_sha,
        git_dirty=git_dirty,
        run_started_iso=run_started.isoformat(),
        run_duration_s=run_duration_s,
        python_version=platform.python_version(),
        platform=platform.platform(),
        input_hashes={},  # Deferred path has no inputs to hash; v1.2 will populate
    )
    meta_path = OUT / "meta.json"
    meta_path.write_text(meta.model_dump_json(indent=2))
    print(f"  Wrote          : {meta_path}")

    print()
    print("=" * 70)
    print(
        f"DIST-S1 N.Am. eval complete: cell_status=DEFERRED, "
        f"cmr_probe_outcome={cmr_probe_outcome}"
    )
    print("=" * 70)
    return 0


if __name__ == "__main__":
    # Phase 1 ENV-04 mandatory: fire BEFORE any requests.Session-using import
    # (asf_search, earthaccess). PITFALLS P0.1 mitigation; idempotent.
    from subsideo._mp import configure_multiprocessing

    configure_multiprocessing()

    import sys

    sys.exit(run())
