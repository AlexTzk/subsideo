"""Pure DISP diagnostic helpers for Phase 10 ERA5 delta assessment."""
from __future__ import annotations

from subsideo.validation.matrix_schema import CauseAssessment, Era5Diagnostic

ATTRIBUTION_FLIP_SIGNAL = "attribution_flip"
REFERENCE_CORRELATION_SIGNAL = "reference_correlation_improved"
BIAS_OR_RMSE_SIGNAL = "bias_or_rmse_improved"
RAMP_REDUCTION_SIGNAL = "ramp_magnitude_reduced"


def classify_era5_delta(
    *,
    baseline_correlation: float,
    era5_correlation: float,
    baseline_bias_mm_yr: float,
    era5_bias_mm_yr: float,
    baseline_rmse_mm_yr: float,
    era5_rmse_mm_yr: float,
    baseline_ramp_mean_magnitude_rad: float,
    era5_ramp_mean_magnitude_rad: float,
    attribution_flipped: bool,
    correlation_min_delta: float = 0.05,
    bias_abs_min_delta_mm_yr: float = 1.0,
    rmse_min_delta_mm_yr: float = 1.0,
    ramp_min_delta_rad: float = 5.0,
) -> Era5Diagnostic:
    """Classify ERA5-on deltas using Phase 10's two-signal rule.

    Delta fields are positive when the ERA5-on run improves over the baseline.
    ``meaningful_improvement`` is true only when at least two independent
    improvement signals are present.
    """

    correlation_delta = era5_correlation - baseline_correlation
    bias_abs_delta_mm_yr = abs(baseline_bias_mm_yr) - abs(era5_bias_mm_yr)
    rmse_delta_mm_yr = baseline_rmse_mm_yr - era5_rmse_mm_yr
    ramp_magnitude_delta_rad = (
        baseline_ramp_mean_magnitude_rad - era5_ramp_mean_magnitude_rad
    )

    improvement_signals: list[str] = []
    if attribution_flipped:
        improvement_signals.append(ATTRIBUTION_FLIP_SIGNAL)
    if correlation_delta >= correlation_min_delta:
        improvement_signals.append(REFERENCE_CORRELATION_SIGNAL)
    if (
        bias_abs_delta_mm_yr >= bias_abs_min_delta_mm_yr
        or rmse_delta_mm_yr >= rmse_min_delta_mm_yr
    ):
        improvement_signals.append(BIAS_OR_RMSE_SIGNAL)
    if ramp_magnitude_delta_rad >= ramp_min_delta_rad:
        improvement_signals.append(RAMP_REDUCTION_SIGNAL)

    return Era5Diagnostic(
        mode="on",
        baseline_correlation=baseline_correlation,
        era5_correlation=era5_correlation,
        correlation_delta=correlation_delta,
        baseline_bias_mm_yr=baseline_bias_mm_yr,
        era5_bias_mm_yr=era5_bias_mm_yr,
        bias_abs_delta_mm_yr=bias_abs_delta_mm_yr,
        baseline_rmse_mm_yr=baseline_rmse_mm_yr,
        era5_rmse_mm_yr=era5_rmse_mm_yr,
        rmse_delta_mm_yr=rmse_delta_mm_yr,
        baseline_ramp_mean_magnitude_rad=baseline_ramp_mean_magnitude_rad,
        era5_ramp_mean_magnitude_rad=era5_ramp_mean_magnitude_rad,
        ramp_magnitude_delta_rad=ramp_magnitude_delta_rad,
        improvement_signals=improvement_signals,
        meaningful_improvement=len(improvement_signals) >= 2,
    )


def assess_causes_from_era5(era5: Era5Diagnostic, *, next_test: str) -> CauseAssessment:
    """Return the structured cause assessment implied by an ERA5 diagnostic."""

    if era5.mode == "on" and not era5.meaningful_improvement:
        return CauseAssessment(
            human_verdict="inconclusive_narrowed",
            eliminated_causes=["tropospheric"],
            remaining_causes=[
                "orbit",
                "terrain",
                "unwrapper",
                "cache_or_input_provenance",
            ],
            next_test=next_test,
        )

    return CauseAssessment(
        human_verdict="inconclusive",
        remaining_causes=[
            "tropospheric",
            "orbit",
            "terrain",
            "unwrapper",
            "cache_or_input_provenance",
        ],
        next_test=next_test,
    )
