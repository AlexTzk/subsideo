"""Unit tests for Phase 5 matrix_writer DIST render branches (Plan 05-05 Task 3).

Covers:
  - _is_dist_eu_shape + _render_dist_eu_cell (all-PASS and mixed-with-chained-warning)
  - _is_dist_nam_shape + _render_dist_nam_deferred_cell (DEFERRED cell)
  - Dispatch ordering invariant: disp_call < dist_eu_call < dist_nam_call
    (D-24 amendment: AFTER-disp is the structurally meaningful pair;
    relative ordering against cslc/dswx is NOT asserted -- contemporary
    observation only, not a forward lock).
"""
from __future__ import annotations

import json
from pathlib import Path

from subsideo.validation.matrix_schema import (
    BootstrapConfig,
    ChainedRunResult,
    DistEUCellMetrics,
    DistEUEventMetrics,
    EFFISQueryMeta,
    MetricWithCI,
    ProductQualityResultJson,
    RasterisationDiagnostic,
    ReferenceAgreementResultJson,
)
from subsideo.validation.matrix_writer import (
    _is_dist_eu_shape,
    _is_dist_nam_shape,
    _render_dist_eu_cell,
    _render_dist_nam_deferred_cell,
)


def _make_event(
    event_id: str,
    f1: float,
    status: str = "PASS",
    chained: ChainedRunResult | None = None,
) -> DistEUEventMetrics:
    """Helper -- produce a minimal valid DistEUEventMetrics for tests."""
    return DistEUEventMetrics(
        event_id=event_id,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        f1=MetricWithCI(point=f1, ci_lower=f1 - 0.04, ci_upper=f1 + 0.04),
        precision=MetricWithCI(point=0.80, ci_lower=0.75, ci_upper=0.85),
        recall=MetricWithCI(point=0.65, ci_lower=0.60, ci_upper=0.70),
        accuracy=MetricWithCI(point=0.92, ci_lower=0.90, ci_upper=0.94),
        rasterisation_diagnostic=RasterisationDiagnostic(
            all_touched_false_f1=f1,
            all_touched_true_f1=f1 + 0.03,
            delta_f1=0.03,
        ),
        bootstrap_config=BootstrapConfig(n_blocks_kept=12100, n_blocks_dropped=221),
        effis_query_meta=EFFISQueryMeta(
            wfs_endpoint="https://api.effis.emergency.copernicus.eu/rest/2/burntareas/current/",
            layer_name="burntareas/current",
            filter_string="<filter/>",
            response_feature_count=5,
            fetched_at="2026-04-25T10:00:00+00:00",
        ),
        chained_run=chained,
    )


def test_dist_eu_all_pass_render(tmp_path: Path) -> None:
    """All-PASS aggregate renders without fail count or warning glyph."""
    cell = DistEUCellMetrics(
        product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResultJson(
            measurements={"worst_f1": 0.85},
            criterion_ids=["dist.f1_min"],
        ),
        criterion_ids_applied=["dist.f1_min", "dist.accuracy_min"],
        pass_count=3,
        total=3,
        all_pass=True,
        cell_status="PASS",
        worst_event_id="evros",
        worst_f1=0.85,
        any_chained_run_failed=False,
        per_event=[
            _make_event("aveiro", 0.88),
            _make_event("evros", 0.85),
            _make_event("spain_culebra", 0.91),
        ],
    )
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(cell.model_dump_json(indent=2))

    assert _is_dist_eu_shape(metrics_path)
    assert not _is_dist_nam_shape(metrics_path)
    cols = _render_dist_eu_cell(metrics_path)
    assert cols is not None
    pq_col, ra_col = cols
    assert pq_col == "—"
    assert ra_col == "3/3 PASS | worst f1=0.850 (evros)"
    assert "FAIL" not in ra_col
    assert "⚠" not in ra_col


def test_dist_eu_mixed_with_chained_warning(tmp_path: Path) -> None:
    """Mixed PASS/FAIL with chained-retry warning renders fail count + warning glyph."""
    chained = ChainedRunResult(
        status="dist_s1_hang",
        output_dir=None,
        n_layers_present=None,
        dist_status_nonempty=None,
        error="ProcessHangDetected",
        traceback=None,
    )
    cell = DistEUCellMetrics(
        product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResultJson(
            measurements={"worst_f1": 0.62},
            criterion_ids=["dist.f1_min"],
        ),
        criterion_ids_applied=["dist.f1_min", "dist.accuracy_min"],
        pass_count=2,
        total=3,
        all_pass=False,
        cell_status="MIXED",
        worst_event_id="spain_culebra",
        worst_f1=0.62,
        any_chained_run_failed=True,
        per_event=[
            _make_event("aveiro", 0.88, status="PASS", chained=chained),
            _make_event("evros", 0.85, status="PASS"),
            _make_event("spain_culebra", 0.62, status="FAIL"),
        ],
    )
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(cell.model_dump_json(indent=2))

    cols = _render_dist_eu_cell(metrics_path)
    assert cols is not None
    pq_col, ra_col = cols
    assert pq_col == "—"
    assert ra_col == "2/3 PASS (1 FAIL) | worst f1=0.620 (spain_culebra) ⚠"


def test_dist_nam_deferred_render(tmp_path: Path) -> None:
    """Deferred dist:nam cell renders 'DEFERRED (CMR: <outcome>)'."""
    raw = {
        "schema_version": 1,
        "cell_status": "DEFERRED",
        "reference_source": "none",
        "cmr_probe_outcome": "operational_not_found",
        "reference_granule_id": None,
        "deferred_reason": "Phase 5 scope amendment 2026-04-25",
        "product_quality": {"measurements": {}, "criterion_ids": []},
        "reference_agreement": {"measurements": {}, "criterion_ids": []},
        "criterion_ids_applied": [],
    }
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(json.dumps(raw))

    assert _is_dist_nam_shape(metrics_path)
    assert not _is_dist_eu_shape(metrics_path)  # no per_event key
    cols = _render_dist_nam_deferred_cell(metrics_path)
    assert cols is not None
    pq_col, ra_col = cols
    assert pq_col == "—"
    assert ra_col == "DEFERRED (CMR: operational_not_found)"


def test_dispatch_ordering_dist_after_disp() -> None:
    """write_matrix dispatches dist:eu AFTER disp:* (D-24 amendment).

    The structurally meaningful invariant is AFTER-disp:* -- disp:* and
    dist:eu both have valid metrics.json sidecars when both phases land,
    and disp:*'s ramp_attribution discriminator must be checked first.
    The relative ordering against cslc:* / dswx:* is a contemporary
    observation only (D-24 amendment in ROADMAP Phase 5 scope-amendment
    block); future phases may legitimately re-order new schemas.
    """
    import subsideo.validation.matrix_writer as mw_mod

    src = Path(mw_mod.__file__).read_text()

    # Each discriminator appears exactly once in the dispatch block as
    # `if metrics_path.exists() and _is_*_shape(metrics_path):`.
    # The function definitions use a typed signature (e.g. `def _is_disp_cell_shape(
    # metrics_path: Path)`) which does NOT match the bare `(metrics_path)` suffix.
    # Use first occurrence of the dispatch callsite pattern for ordering.
    disp_call = src.find("_is_disp_cell_shape(metrics_path)")
    dist_eu_call = src.find("_is_dist_eu_shape(metrics_path)")
    dist_nam_call = src.find("_is_dist_nam_shape(metrics_path)")

    assert disp_call != -1, "disp:* dispatch site missing"
    assert dist_eu_call != -1, "dist:eu dispatch site missing (Plan 05-05 not landed?)"
    assert dist_nam_call != -1, "dist:nam dispatch site missing"

    # Structurally meaningful ordering only (D-24 amendment):
    # disp -> dist_eu -> dist_nam.
    # NOT asserted: dist_nam < cslc, dist_nam < dswx, etc.
    assert disp_call < dist_eu_call, (
        f"DIST-EU dispatched BEFORE disp:* (disp@{disp_call} dist_eu@{dist_eu_call}); "
        f"violates D-24 amendment AFTER-disp invariant"
    )
    assert dist_eu_call < dist_nam_call, (
        f"DIST-NAM dispatched BEFORE DIST-EU (dist_eu@{dist_eu_call} dist_nam@{dist_nam_call}); "
        f"violates Plan 05-05 internal ordering (per_event before DEFERRED-shape)"
    )
