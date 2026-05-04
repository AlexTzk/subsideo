"""Phase 4 matrix_schema DISP types — Pydantic v2 round-trip + extra=forbid + Literal validation."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from subsideo.validation.matrix_schema import (
    CauseAssessment,
    DISPCellMetrics,
    DISPProductQualityResultJson,
    Era5Diagnostic,
    PerIFGRamp,
    RampAggregate,
    RampAttribution,
    ReferenceAgreementResultJson,
)


def _make_valid_disp_metrics() -> DISPCellMetrics:
    """Construct a fully-valid DISPCellMetrics fixture."""
    pq = DISPProductQualityResultJson(
        measurements={
            "coherence_median_of_persistent": 0.88,
            "residual_mm_yr": -0.11,
        },
        criterion_ids=[
            "disp.selfconsistency.coherence_min",
            "disp.selfconsistency.residual_mm_yr_max",
        ],
        coherence_source="phase3-cached",
    )
    ra = ReferenceAgreementResultJson(
        measurements={
            "correlation": 0.04,
            "bias_mm_yr": 23.6,
            "rmse_mm_yr": 59.6,
            "sample_count": 12345,
        },
        criterion_ids=["disp.correlation_min", "disp.bias_mm_yr_max"],
    )
    aggregate = RampAggregate(
        mean_magnitude_rad=5.5,
        direction_stability_sigma_deg=12.3,
        magnitude_vs_coherence_pearson_r=0.42,
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
        attributed_source="phass",
        attribution_note="Automated; human review pending in CONCLUSIONS",
    )
    return DISPCellMetrics(
        schema_version=1,
        product_quality=pq,
        reference_agreement=ra,
        ramp_attribution=ramp_attribution,
        cell_status="MIXED",
        criterion_ids_applied=[
            "disp.selfconsistency.coherence_min",
            "disp.selfconsistency.residual_mm_yr_max",
            "disp.correlation_min",
            "disp.bias_mm_yr_max",
        ],
        runtime_conda_list_hash=None,
    )


def test_disp_cell_metrics_round_trip() -> None:
    original = _make_valid_disp_metrics()
    js = original.model_dump_json()
    parsed = DISPCellMetrics.model_validate_json(js)
    # Round-trip preserves every field.
    assert parsed.product_quality.coherence_source == "phase3-cached"
    assert parsed.product_quality.measurements["coherence_median_of_persistent"] == pytest.approx(
        0.88
    )
    assert parsed.reference_agreement.measurements["correlation"] == pytest.approx(0.04)
    assert parsed.ramp_attribution.attributed_source == "phass"
    assert parsed.ramp_attribution.aggregate.n_ifgs == 14
    assert len(parsed.ramp_attribution.per_ifg) == 1
    assert parsed.ramp_attribution.per_ifg[0].ifg_idx == 0
    assert parsed.cell_status == "MIXED"
    assert parsed.era5_diagnostic is None
    assert parsed.cause_assessment is None


def test_phase10_diagnostics_are_additive_optional_fields() -> None:
    base = _make_valid_disp_metrics()
    payload = base.model_dump()
    payload["era5_diagnostic"] = {
        "mode": "on",
        "baseline_correlation": 0.049,
        "era5_correlation": 0.11,
        "correlation_delta": 0.061,
        "baseline_bias_mm_yr": 23.6,
        "era5_bias_mm_yr": 20.0,
        "bias_abs_delta_mm_yr": 3.6,
        "baseline_rmse_mm_yr": 59.6,
        "era5_rmse_mm_yr": 56.5,
        "rmse_delta_mm_yr": 3.1,
        "baseline_ramp_mean_magnitude_rad": 35.6,
        "era5_ramp_mean_magnitude_rad": 28.0,
        "ramp_magnitude_delta_rad": 7.6,
        "improvement_signals": [
            "reference_correlation_improved",
            "bias_or_rmse_improved",
        ],
        "meaningful_improvement": True,
    }
    payload["cause_assessment"] = {
        "human_verdict": "inconclusive_narrowed",
        "eliminated_causes": ["tropospheric"],
        "remaining_causes": [
            "orbit",
            "terrain",
            "unwrapper",
            "cache_or_input_provenance",
        ],
        "next_test": "Run SPURT native candidate.",
    }

    parsed = DISPCellMetrics.model_validate(payload)

    assert parsed.era5_diagnostic is not None
    assert parsed.era5_diagnostic.mode == "on"
    assert parsed.era5_diagnostic.meaningful_improvement is True
    assert parsed.cause_assessment is not None
    assert parsed.cause_assessment.human_verdict == "inconclusive_narrowed"
    assert parsed.cause_assessment.eliminated_causes == ["tropospheric"]


def test_phase10_models_reject_invalid_literals_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Era5Diagnostic.model_validate({"mode": "enabled"})

    with pytest.raises(ValidationError):
        CauseAssessment.model_validate(
            {
                "eliminated_causes": ["troposphere"],
                "remaining_causes": [],
                "next_test": "",
            }
        )

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Era5Diagnostic.model_validate({"mode": "off", "unexpected": True})


@pytest.mark.parametrize(
    "model_cls,extra_payload",
    [
        (
            PerIFGRamp,
            {
                "ifg_idx": 0,
                "ref_date_iso": "2024-01-08",
                "sec_date_iso": "2024-01-20",
                "ramp_magnitude_rad": 1.0,
                "ramp_direction_deg": 30.0,
                "unknown_field": "rejected",
            },
        ),
        (
            RampAggregate,
            {
                "mean_magnitude_rad": 1.0,
                "direction_stability_sigma_deg": 10.0,
                "magnitude_vs_coherence_pearson_r": 0.3,
                "n_ifgs": 10,
                "unknown_field": "rejected",
            },
        ),
    ],
)
def test_extra_forbid_rejects_unknown_keys(
    model_cls: type, extra_payload: dict[str, object]
) -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        model_cls.model_validate(extra_payload)


def test_coherence_source_rejects_invalid_literal() -> None:
    pq_dict = {
        "measurements": {},
        "criterion_ids": [],
        "coherence_source": "invalid-source-value",
    }
    with pytest.raises(ValidationError):
        DISPProductQualityResultJson.model_validate(pq_dict)


def test_attributed_source_rejects_invalid_literal() -> None:
    base = _make_valid_disp_metrics()
    payload = base.model_dump()
    payload["ramp_attribution"]["attributed_source"] = "invalid-attr"
    with pytest.raises(ValidationError):
        DISPCellMetrics.model_validate(payload)


def test_attributed_source_rejects_inconclusive_narrowed_literal() -> None:
    base = _make_valid_disp_metrics()
    payload = base.model_dump()
    payload["ramp_attribution"]["attributed_source"] = "inconclusive_narrowed"
    with pytest.raises(ValidationError):
        DISPCellMetrics.model_validate(payload)


def test_cell_status_rejects_invalid_literal() -> None:
    base = _make_valid_disp_metrics()
    payload = base.model_dump()
    payload["cell_status"] = "INVALID-STATUS"
    with pytest.raises(ValidationError):
        DISPCellMetrics.model_validate(payload)


def test_disp_product_quality_inherits_base_fields() -> None:
    pq = DISPProductQualityResultJson(
        measurements={"x": 1.0},
        criterion_ids=["disp.selfconsistency.coherence_min"],
        coherence_source="fresh",
    )
    # Inherited fields work.
    assert pq.measurements == {"x": 1.0}
    assert pq.criterion_ids == ["disp.selfconsistency.coherence_min"]
    # New field works.
    assert pq.coherence_source == "fresh"


def test_disp_cell_metrics_requires_coherence_source() -> None:
    base = _make_valid_disp_metrics()
    payload = base.model_dump()
    # Drop the coherence_source field from product_quality.
    del payload["product_quality"]["coherence_source"]
    with pytest.raises(ValidationError, match="coherence_source"):
        DISPCellMetrics.model_validate(payload)
