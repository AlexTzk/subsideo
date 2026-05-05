"""Phase 4 matrix_writer DISP branch -- render correctness + dispatch order."""
from __future__ import annotations

import json
from pathlib import Path

from subsideo.validation.matrix_schema import (
    CauseAssessment,
    DISPCandidateOutcome,
    DISPCellMetrics,
    DISPProductQualityResultJson,
    Era5Diagnostic,
    PerIFGRamp,
    RampAggregate,
    RampAttribution,
    ReferenceAgreementResultJson,
)
from subsideo.validation.matrix_writer import (
    _is_disp_cell_shape,
    _render_disp_cell,
    write_matrix,
)


def _make_candidate_outcome(
    candidate: str,
    *,
    status: str = "PASS",
    cell: str = "socal",
    partial_metrics: bool = False,
) -> DISPCandidateOutcome:
    """Minimal DISPCandidateOutcome builder for test fixtures."""
    kwargs: dict = dict(
        candidate=candidate,
        cell=cell,
        status=status,
        cached_input_valid=True,
        partial_metrics=partial_metrics,
    )
    if status == "BLOCKER":
        kwargs["failed_stage"] = "unwrap"
        kwargs["error_summary"] = "test error"
        kwargs["evidence_paths"] = ["/tmp/log.txt"]
    return DISPCandidateOutcome(**kwargs)


def _make_disp_metrics(
    *,
    coherence_source: str = "phase3-cached",
    attributed_source: str = "phass",
    cell_status: str = "MIXED",
    coh: float = 0.87,
    resid: float = -0.11,
    correlation: float = 0.04,
    bias_mm_yr: float = 23.6,
    include_era5_diagnostic: bool = False,
    include_cause_assessment: bool = False,
    candidate_outcomes: list[DISPCandidateOutcome] | None = None,
) -> DISPCellMetrics:
    pq = DISPProductQualityResultJson(
        measurements={
            "coherence_median_of_persistent": coh,
            "residual_mm_yr": resid,
        },
        criterion_ids=[
            "disp.selfconsistency.coherence_min",
            "disp.selfconsistency.residual_mm_yr_max",
        ],
        coherence_source=coherence_source,
    )
    ra = ReferenceAgreementResultJson(
        measurements={
            "correlation": correlation,
            "bias_mm_yr": bias_mm_yr,
            "rmse_mm_yr": 50.0,
            "sample_count": 12345,
        },
        criterion_ids=["disp.correlation_min", "disp.bias_mm_yr_max"],
    )
    aggregate = RampAggregate(
        mean_magnitude_rad=5.5,
        direction_stability_sigma_deg=80.0,
        magnitude_vs_coherence_pearson_r=0.7,
        n_ifgs=14,
    )
    per_ifg = [
        PerIFGRamp(
            ifg_idx=0,
            ref_date_iso="2024-01-08",
            sec_date_iso="2024-01-20",
            ramp_magnitude_rad=4.2,
            ramp_direction_deg=22.0,
            ifg_coherence_mean=0.71,
        ),
    ]
    ramp_attribution = RampAttribution(
        per_ifg=per_ifg,
        aggregate=aggregate,
        attributed_source=attributed_source,
        attribution_note="test fixture",
    )
    era5_diagnostic = None
    if include_era5_diagnostic:
        era5_diagnostic = Era5Diagnostic(
            mode="on",
            improvement_signals=[
                "correlation_improved",
                "rmse_improved",
            ],
            meaningful_improvement=True,
        )
    cause_assessment = None
    if include_cause_assessment:
        cause_assessment = CauseAssessment(
            human_verdict="inconclusive_narrowed",
            eliminated_causes=["tropospheric"],
            remaining_causes=["orbit", "terrain", "unwrapper"],
            next_test="Run SPURT native candidate.",
        )
    return DISPCellMetrics(
        schema_version=1,
        product_quality=pq,
        reference_agreement=ra,
        ramp_attribution=ramp_attribution,
        cell_status=cell_status,
        criterion_ids_applied=[
            "disp.selfconsistency.coherence_min",
            "disp.selfconsistency.residual_mm_yr_max",
            "disp.correlation_min",
            "disp.bias_mm_yr_max",
        ],
        runtime_conda_list_hash=None,
        era5_diagnostic=era5_diagnostic,
        cause_assessment=cause_assessment,
        candidate_outcomes=candidate_outcomes or [],
    )


def _write(path: Path, m: DISPCellMetrics) -> None:
    path.write_text(m.model_dump_json(indent=2))


# -------------------- _is_disp_cell_shape --------------------


def test_is_disp_cell_shape_true_on_disp_metrics(tmp_path: Path) -> None:
    p = tmp_path / "metrics.json"
    _write(p, _make_disp_metrics())
    assert _is_disp_cell_shape(p) is True


def test_is_disp_cell_shape_false_without_ramp_attribution(tmp_path: Path) -> None:
    p = tmp_path / "metrics.json"
    p.write_text(json.dumps({"per_aoi": [], "schema_version": 1}))
    assert _is_disp_cell_shape(p) is False


def test_is_disp_cell_shape_false_on_missing_file(tmp_path: Path) -> None:
    assert _is_disp_cell_shape(tmp_path / "does-not-exist.json") is False


def test_is_disp_cell_shape_false_on_invalid_json(tmp_path: Path) -> None:
    p = tmp_path / "metrics.json"
    p.write_text("not-json-at-all")
    assert _is_disp_cell_shape(p) is False


# -------------------- _render_disp_cell --------------------


def test_render_disp_cell_nam_returns_tuple(tmp_path: Path) -> None:
    p = tmp_path / "metrics.json"
    _write(p, _make_disp_metrics())
    cols = _render_disp_cell(p, region="nam")
    assert cols is not None
    pq_col, ra_col = cols
    assert pq_col.startswith("*") and pq_col.endswith("*")
    assert "coh=" in pq_col
    assert "resid=" in pq_col
    assert "attr=" in pq_col
    assert "CALIBRATING" in pq_col
    # RA col: per-criterion measurements rendered via _render_measurement
    assert "0.04" in ra_col or "FAIL" in ra_col  # correlation rendered
    # RA body should NOT be italicised whole-body (existing _render_measurement
    # output style is "value (op threshold VERDICT)").
    assert not (ra_col.startswith("*") and ra_col.endswith("*"))


def test_render_disp_cell_eu_returns_same_shape(tmp_path: Path) -> None:
    p = tmp_path / "metrics.json"
    _write(p, _make_disp_metrics())
    cols_nam = _render_disp_cell(p, region="nam")
    cols_eu = _render_disp_cell(p, region="eu")
    assert cols_nam is not None
    assert cols_eu is not None
    # Both regions render through the same DISPCellMetrics schema; same fixture
    # produces identical output regardless of region argument (region only
    # affects matrix-writer dispatch via the manifest, not the cell render).
    assert cols_nam == cols_eu


def test_render_disp_cell_blocker_appends_warning(tmp_path: Path) -> None:
    p = tmp_path / "metrics.json"
    _write(p, _make_disp_metrics(cell_status="BLOCKER"))
    cols = _render_disp_cell(p, region="eu")
    assert cols is not None
    pq_col, _ = cols
    assert "⚠" in pq_col


def test_render_disp_cell_shows_phase3_cached_provenance(tmp_path: Path) -> None:
    p = tmp_path / "metrics.json"
    _write(p, _make_disp_metrics(coherence_source="phase3-cached"))
    cols = _render_disp_cell(p, region="nam")
    assert cols is not None
    pq_col, _ = cols
    assert "[phase3-cached]" in pq_col


def test_render_disp_cell_shows_fresh_provenance(tmp_path: Path) -> None:
    p = tmp_path / "metrics.json"
    _write(p, _make_disp_metrics(coherence_source="fresh"))
    cols = _render_disp_cell(p, region="eu")
    assert cols is not None
    pq_col, _ = cols
    assert "[fresh]" in pq_col


def test_render_disp_cell_shows_attr_phass(tmp_path: Path) -> None:
    p = tmp_path / "metrics.json"
    _write(p, _make_disp_metrics(attributed_source="phass"))
    cols = _render_disp_cell(p, region="nam")
    assert cols is not None
    pq_col, _ = cols
    assert "attr=phass" in pq_col


def test_render_disp_cell_shows_attr_inconclusive(tmp_path: Path) -> None:
    p = tmp_path / "metrics.json"
    _write(p, _make_disp_metrics(attributed_source="inconclusive"))
    cols = _render_disp_cell(p, region="nam")
    assert cols is not None
    pq_col, _ = cols
    assert "attr=inconclusive" in pq_col


def test_render_disp_cell_shows_phase10_era5_flags(tmp_path: Path) -> None:
    p = tmp_path / "metrics.json"
    _write(
        p,
        _make_disp_metrics(
            include_era5_diagnostic=True,
            include_cause_assessment=True,
        ),
    )
    cols = _render_disp_cell(p, region="nam")
    assert cols is not None
    pq_col, _ = cols
    assert "era5=on" in pq_col
    assert "signals=2" in pq_col
    assert "narrowed=tropospheric" in pq_col


def test_render_disp_cell_returns_none_on_malformed_disp_metrics(tmp_path: Path) -> None:
    """A JSON with ramp_attribution but missing coherence_source should fail
    DISPCellMetrics validation -> _render_disp_cell returns None."""
    p = tmp_path / "metrics.json"
    bogus = {
        "schema_version": 1,
        "ramp_attribution": {
            "per_ifg": [],
            "aggregate": {
                "mean_magnitude_rad": 1.0,
                "direction_stability_sigma_deg": 10.0,
                "magnitude_vs_coherence_pearson_r": 0.3,
                "n_ifgs": 5,
            },
            "attributed_source": "orbit",
            "attribution_note": "",
        },
        "product_quality": {
            "measurements": {},
            "criterion_ids": [],
            # MISSING coherence_source -> DISPProductQualityResultJson validation fails
        },
        "reference_agreement": {"measurements": {}, "criterion_ids": []},
        "criterion_ids_applied": [],
        "cell_status": "MIXED",
    }
    p.write_text(json.dumps(bogus))
    assert _render_disp_cell(p, region="nam") is None


# -------------------- End-to-end via write_matrix --------------------


def test_write_matrix_renders_disp_via_disp_branch(tmp_path: Path) -> None:
    """E2E: a manifest with one disp:nam cell + valid metrics.json renders via
    the DISP dispatch branch (not the default RUN_FAILED branch)."""
    cache = tmp_path / "eval-disp"
    cache.mkdir()
    metrics_path = cache / "metrics.json"
    _write(metrics_path, _make_disp_metrics())
    meta_path = cache / "meta.json"
    meta_path.write_text(json.dumps({
        "schema_version": 1,
        "git_sha": "abc",
        "git_dirty": False,
        "run_started_iso": "2026-04-25T00:00:00",
        "run_duration_s": 100.0,
        "python_version": "3.11.0",
        "platform": "darwin",
        "input_hashes": {},
    }))

    manifest = tmp_path / "manifest.yml"
    manifest.write_text(
        f"""schema_version: 1
cells:
  - product: disp
    region: nam
    eval_script: run_eval_disp.py
    cache_dir: {cache}
    metrics_file: {metrics_path}
    meta_file: {meta_path}
    conclusions_doc: CONCLUSIONS_DISP_N_AM.md
"""
    )

    out = tmp_path / "matrix.md"
    write_matrix(manifest, out)
    text = out.read_text()
    # Validate DISP-branch rendering signature
    assert "DISP" in text
    assert "CALIBRATING" in text
    assert "attr=phass" in text
    assert "[phase3-cached]" in text
    # Make sure RUN_FAILED is NOT present (would indicate dispatch fell through)
    assert "RUN_FAILED" not in text


# -------------------- Phase 11 candidate hints (D-12) --------------------


def test_render_disp_cell_candidate_hints_in_pq_col(tmp_path: Path) -> None:
    """candidate_outcomes appear in pq_col as cand=... compact text (D-12)."""
    p = tmp_path / "metrics.json"
    outcomes = [
        _make_candidate_outcome("spurt_native", status="PASS"),
        _make_candidate_outcome("phass_post_deramp", status="FAIL"),
    ]
    _write(p, _make_disp_metrics(candidate_outcomes=outcomes))
    cols = _render_disp_cell(p, region="nam")
    assert cols is not None
    pq_col, ra_col = cols
    # Compact hint must appear in PQ column
    assert "cand=" in pq_col
    assert "spurt:PASS" in pq_col
    assert "deramp:FAIL" in pq_col
    # RA column must NOT contain candidate text (D-12 separation)
    assert "cand=" not in ra_col


def test_render_disp_cell_candidate_hints_sorted_spurt_first(tmp_path: Path) -> None:
    """spurt_native appears before phass_post_deramp in cand= hint (D-12)."""
    p = tmp_path / "metrics.json"
    # Supply in reverse order; output must still be sorted spurt first.
    outcomes = [
        _make_candidate_outcome("phass_post_deramp", status="BLOCKER"),
        _make_candidate_outcome("spurt_native", status="PASS"),
    ]
    _write(p, _make_disp_metrics(candidate_outcomes=outcomes))
    cols = _render_disp_cell(p, region="nam")
    assert cols is not None
    pq_col, _ = cols
    assert "cand=" in pq_col
    # spurt must come before deramp in the string
    spurt_pos = pq_col.index("spurt:PASS")
    deramp_pos = pq_col.index("deramp:BLOCKER")
    assert spurt_pos < deramp_pos


def test_render_disp_cell_candidate_partial_metrics_appends_star(tmp_path: Path) -> None:
    """partial_metrics=True appends '*' to the status label (D-11)."""
    p = tmp_path / "metrics.json"
    outcomes = [
        _make_candidate_outcome("spurt_native", status="BLOCKER", partial_metrics=True),
        _make_candidate_outcome("phass_post_deramp", status="FAIL"),
    ]
    _write(p, _make_disp_metrics(candidate_outcomes=outcomes))
    cols = _render_disp_cell(p, region="nam")
    assert cols is not None
    pq_col, _ = cols
    assert "spurt:BLOCKER*" in pq_col
    assert "deramp:FAIL" in pq_col  # no star on non-partial


def test_render_disp_cell_no_candidate_outcomes_no_cand_hint(tmp_path: Path) -> None:
    """Sidecars without candidate_outcomes produce no cand= text (backward compat)."""
    p = tmp_path / "metrics.json"
    _write(p, _make_disp_metrics())
    cols = _render_disp_cell(p, region="nam")
    assert cols is not None
    pq_col, ra_col = cols
    assert "cand=" not in pq_col
    assert "cand=" not in ra_col


def test_render_disp_cell_ra_col_never_contains_cand(tmp_path: Path) -> None:
    """RA column must not contain cand= regardless of candidate status (D-12)."""
    p = tmp_path / "metrics.json"
    outcomes = [
        _make_candidate_outcome("spurt_native", status="PASS"),
        _make_candidate_outcome("phass_post_deramp", status="PASS"),
    ]
    _write(p, _make_disp_metrics(candidate_outcomes=outcomes))
    cols = _render_disp_cell(p, region="eu")
    assert cols is not None
    _, ra_col = cols
    assert "cand=" not in ra_col
