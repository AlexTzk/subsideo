"""Phase 10 DISP ERA5 diagnostic helper tests."""
from __future__ import annotations

import pytest

from subsideo.validation.disp_diagnostics import (
    assess_causes_from_era5,
    classify_era5_delta,
)
from subsideo.validation.matrix_schema import Era5Diagnostic


def test_classify_era5_delta_one_signal_ramp_only_is_not_meaningful() -> None:
    diagnostic = classify_era5_delta(
        baseline_correlation=0.049,
        era5_correlation=0.06,
        baseline_bias_mm_yr=23.6,
        era5_bias_mm_yr=23.2,
        baseline_rmse_mm_yr=59.6,
        era5_rmse_mm_yr=59.0,
        baseline_ramp_mean_magnitude_rad=35.6,
        era5_ramp_mean_magnitude_rad=28.0,
        attribution_flipped=False,
    )

    assert diagnostic.ramp_magnitude_delta_rad == pytest.approx(7.6)
    assert diagnostic.improvement_signals == ["ramp_magnitude_reduced"]
    assert diagnostic.meaningful_improvement is False


def test_classify_era5_delta_two_signals_is_meaningful() -> None:
    diagnostic = classify_era5_delta(
        baseline_correlation=0.049,
        era5_correlation=0.12,
        baseline_bias_mm_yr=23.6,
        era5_bias_mm_yr=21.9,
        baseline_rmse_mm_yr=59.6,
        era5_rmse_mm_yr=58.9,
        baseline_ramp_mean_magnitude_rad=35.6,
        era5_ramp_mean_magnitude_rad=34.0,
        attribution_flipped=False,
    )

    assert diagnostic.correlation_delta == pytest.approx(0.071)
    assert diagnostic.bias_abs_delta_mm_yr == pytest.approx(1.7)
    assert diagnostic.improvement_signals == [
        "reference_correlation_improved",
        "bias_or_rmse_improved",
    ]
    assert diagnostic.meaningful_improvement is True


def test_classify_era5_delta_keeps_signal_order_deterministic() -> None:
    diagnostic = classify_era5_delta(
        baseline_correlation=0.049,
        era5_correlation=0.12,
        baseline_bias_mm_yr=23.6,
        era5_bias_mm_yr=21.9,
        baseline_rmse_mm_yr=59.6,
        era5_rmse_mm_yr=57.0,
        baseline_ramp_mean_magnitude_rad=35.6,
        era5_ramp_mean_magnitude_rad=28.0,
        attribution_flipped=True,
    )

    assert diagnostic.improvement_signals == [
        "attribution_flip",
        "reference_correlation_improved",
        "bias_or_rmse_improved",
        "ramp_magnitude_reduced",
    ]


def test_assess_causes_no_improvement_era5_on_eliminates_only_tropospheric() -> None:
    diagnostic = Era5Diagnostic(
        mode="on",
        improvement_signals=["ramp_magnitude_reduced"],
        meaningful_improvement=False,
    )

    assessment = assess_causes_from_era5(
        diagnostic,
        next_test="Run SPURT native candidate.",
    )

    assert assessment.human_verdict == "inconclusive_narrowed"
    assert assessment.eliminated_causes == ["tropospheric"]
    assert assessment.remaining_causes == [
        "orbit",
        "terrain",
        "unwrapper",
        "cache_or_input_provenance",
    ]
    assert assessment.next_test == "Run SPURT native candidate."


def test_assess_causes_meaningful_improvement_keeps_causes_open() -> None:
    diagnostic = Era5Diagnostic(
        mode="on",
        improvement_signals=[
            "reference_correlation_improved",
            "bias_or_rmse_improved",
        ],
        meaningful_improvement=True,
    )

    assessment = assess_causes_from_era5(
        diagnostic,
        next_test="Compare Phase 11 baseline.",
    )

    assert assessment.human_verdict == "inconclusive"
    assert assessment.eliminated_causes == []
    assert assessment.remaining_causes == [
        "tropospheric",
        "orbit",
        "terrain",
        "unwrapper",
        "cache_or_input_provenance",
    ]
