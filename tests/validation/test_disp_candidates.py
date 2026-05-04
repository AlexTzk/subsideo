"""Phase 11 candidate evidence schema and helper regression tests.

Covers:
- DISPCandidateOutcome schema validation (D-09 through D-12)
- DISPDeformationSanityCheck schema validation (D-07)
- DISPCellMetrics.candidate_outcomes additive sidecar field (D-12)
- candidate_output_dir helper (T-11-01-03)
- candidate_status_from_metrics thresholds (D-01 brief + D-09)
- make_candidate_blocker structured evidence (D-10)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

# ============================================================================
# Task 1: Schema tests (DISPCandidateOutcome, DISPDeformationSanityCheck,
#          DISPCellMetrics.candidate_outcomes)
# ============================================================================


def _make_base_disp_cell_metrics_dict() -> dict:
    """Minimal valid DISPCellMetrics payload for legacy (no candidate_outcomes) tests."""
    return {
        "schema_version": 1,
        "product_quality": {
            "measurements": {"coherence_median_of_persistent": 0.87},
            "criterion_ids": ["disp.selfconsistency.coherence_min"],
            "coherence_source": "phase3-cached",
        },
        "reference_agreement": {
            "measurements": {"correlation": 0.049, "bias_mm_yr": 23.6},
            "criterion_ids": ["disp.correlation_min"],
        },
        "ramp_attribution": {
            "per_ifg": [],
            "aggregate": {
                "mean_magnitude_rad": 5.5,
                "direction_stability_sigma_deg": 80.0,
                "magnitude_vs_coherence_pearson_r": 0.15,
                "n_ifgs": 14,
            },
            "attributed_source": "inconclusive",
            "attribution_note": "",
        },
        "cell_status": "MIXED",
        "criterion_ids_applied": [],
        "runtime_conda_list_hash": None,
    }


class TestDISPCandidateOutcomeSchema:
    """D-09: every candidate-cell outcome is PASS, FAIL, or BLOCKER."""

    def test_pass_outcome_validates(self) -> None:
        from subsideo.validation.matrix_schema import DISPCandidateOutcome

        outcome = DISPCandidateOutcome(
            candidate="spurt_native",
            cell="socal",
            status="PASS",
            cached_input_valid=True,
        )
        assert outcome.status == "PASS"
        assert outcome.candidate == "spurt_native"
        assert outcome.cell == "socal"

    def test_fail_outcome_validates(self) -> None:
        from subsideo.validation.matrix_schema import DISPCandidateOutcome

        outcome = DISPCandidateOutcome(
            candidate="phass_post_deramp",
            cell="bologna",
            status="FAIL",
            cached_input_valid=False,
        )
        assert outcome.status == "FAIL"

    def test_blocker_outcome_with_full_evidence(self) -> None:
        """D-10: BLOCKER must preserve all required evidence fields."""
        from subsideo.validation.matrix_schema import DISPCandidateOutcome

        outcome = DISPCandidateOutcome(
            candidate="spurt_native",
            cell="socal",
            status="BLOCKER",
            failed_stage="unwrap",
            error_summary="SPURT raised RuntimeError: insufficient pixels",
            evidence_paths=["eval-disp/candidates/spurt_native/spurt.log"],
            cached_input_valid=True,
            partial_metrics=True,
            reference_correlation=0.45,
        )
        assert outcome.status == "BLOCKER"
        assert outcome.failed_stage == "unwrap"
        assert outcome.error_summary is not None
        assert len(outcome.evidence_paths) == 1
        assert outcome.partial_metrics is True
        assert outcome.reference_correlation == pytest.approx(0.45)

    def test_extra_field_raises_validation_error(self) -> None:
        """ConfigDict(extra='forbid') must reject unknown fields (T-11-01-01)."""
        from subsideo.validation.matrix_schema import DISPCandidateOutcome

        with pytest.raises(ValidationError):
            DISPCandidateOutcome(
                candidate="spurt_native",
                cell="socal",
                status="PASS",
                cached_input_valid=True,
                nonexistent_field="oops",  # type: ignore[call-arg]
            )

    def test_invalid_candidate_name_raises(self) -> None:
        """DISPCandidateName Literal rejects unknown candidate strings."""
        from subsideo.validation.matrix_schema import DISPCandidateOutcome

        with pytest.raises(ValidationError):
            DISPCandidateOutcome(
                candidate="tophu_snaphu",  # not a valid literal  # type: ignore[arg-type]
                cell="socal",
                status="PASS",
                cached_input_valid=True,
            )

    def test_invalid_cell_raises(self) -> None:
        """DISPCandidateCell Literal rejects unknown cell names."""
        from subsideo.validation.matrix_schema import DISPCandidateOutcome

        with pytest.raises(ValidationError):
            DISPCandidateOutcome(
                candidate="spurt_native",
                cell="los_angeles",  # type: ignore[arg-type]
                status="PASS",
                cached_input_valid=True,
            )

    def test_invalid_status_raises(self) -> None:
        """DISPCandidateStatus Literal rejects non PASS/FAIL/BLOCKER strings."""
        from subsideo.validation.matrix_schema import DISPCandidateOutcome

        with pytest.raises(ValidationError):
            DISPCandidateOutcome(
                candidate="spurt_native",
                cell="socal",
                status="CALIBRATING",  # type: ignore[arg-type]
                cached_input_valid=True,
            )

    def test_default_evidence_paths_is_empty_list(self) -> None:
        from subsideo.validation.matrix_schema import DISPCandidateOutcome

        outcome = DISPCandidateOutcome(
            candidate="phass_post_deramp",
            cell="bologna",
            status="PASS",
            cached_input_valid=True,
        )
        assert outcome.evidence_paths == []
        assert outcome.partial_metrics is False
        assert outcome.failed_stage is None

    def test_serialization_round_trip(self) -> None:
        """Schema-valid PASS outcome survives JSON round-trip."""
        from subsideo.validation.matrix_schema import DISPCandidateOutcome

        outcome = DISPCandidateOutcome(
            candidate="spurt_native",
            cell="socal",
            status="PASS",
            cached_input_valid=True,
            reference_correlation=0.73,
            reference_bias_mm_yr=1.2,
        )
        raw = json.loads(outcome.model_dump_json())
        restored = DISPCandidateOutcome.model_validate(raw)
        assert restored.reference_correlation == pytest.approx(0.73)
        assert restored.status == "PASS"


class TestDISPDeformationSanityCheckSchema:
    """D-07: lightweight deformation-signal sanity check on Phase 11 outcomes."""

    def test_unflagged_sanity_check_validates(self) -> None:
        from subsideo.validation.matrix_schema import DISPDeformationSanityCheck

        check = DISPDeformationSanityCheck(
            cell="socal",
            trend_delta_mm_yr=0.5,
            direction_change_deg=12.0,
        )
        assert check.flagged is False
        assert check.flag_reason == ""

    def test_flagged_sanity_check_preserves_reason(self) -> None:
        from subsideo.validation.matrix_schema import DISPDeformationSanityCheck

        check = DISPDeformationSanityCheck(
            cell="socal",
            trend_delta_mm_yr=8.0,
            direction_change_deg=95.0,
            flagged=True,
            flag_reason="trend delta > 5 mm/yr AND direction change > 60 deg",
        )
        assert check.flagged is True
        assert "trend delta" in check.flag_reason

    def test_extra_field_raises_validation_error(self) -> None:
        from subsideo.validation.matrix_schema import DISPDeformationSanityCheck

        with pytest.raises(ValidationError):
            DISPDeformationSanityCheck(
                cell="socal",
                nonexistent="oops",  # type: ignore[call-arg]
            )

    def test_invalid_cell_raises(self) -> None:
        from subsideo.validation.matrix_schema import DISPDeformationSanityCheck

        with pytest.raises(ValidationError):
            DISPDeformationSanityCheck(cell="los_angeles")  # type: ignore[arg-type]

    def test_outcome_with_sanity_check_validates(self) -> None:
        """DISPCandidateOutcome can embed a DISPDeformationSanityCheck."""
        from subsideo.validation.matrix_schema import (
            DISPCandidateOutcome,
            DISPDeformationSanityCheck,
        )

        sanity = DISPDeformationSanityCheck(
            cell="socal",
            trend_delta_mm_yr=1.5,
            direction_change_deg=20.0,
            stable_residual_delta_mm_yr=0.3,
        )
        outcome = DISPCandidateOutcome(
            candidate="phass_post_deramp",
            cell="socal",
            status="PASS",
            cached_input_valid=True,
            deformation_sanity=sanity,
        )
        assert outcome.deformation_sanity is not None
        assert outcome.deformation_sanity.trend_delta_mm_yr == pytest.approx(1.5)


class TestDISPCellMetricsCandidateOutcomesField:
    """D-12: candidate_outcomes is additive; existing fields unchanged."""

    def test_legacy_sidecar_without_candidate_outcomes_validates(self) -> None:
        """DISPCellMetrics validates legacy sidecars with no candidate_outcomes."""
        from subsideo.validation.matrix_schema import DISPCellMetrics

        data = _make_base_disp_cell_metrics_dict()
        metrics = DISPCellMetrics.model_validate(data)
        assert metrics.candidate_outcomes == []

    def test_existing_fields_still_present(self) -> None:
        """product_quality, reference_agreement, ramp_attribution unchanged."""
        from subsideo.validation.matrix_schema import DISPCellMetrics

        data = _make_base_disp_cell_metrics_dict()
        metrics = DISPCellMetrics.model_validate(data)
        assert hasattr(metrics, "product_quality")
        assert hasattr(metrics, "reference_agreement")
        assert hasattr(metrics, "ramp_attribution")

    def test_candidate_outcomes_with_spurt_and_phass_validates(self) -> None:
        """DISPCellMetrics validates with SPURT/PHASS candidate_outcomes."""
        from subsideo.validation.matrix_schema import DISPCellMetrics

        data = _make_base_disp_cell_metrics_dict()
        data["candidate_outcomes"] = [
            {
                "candidate": "spurt_native",
                "cell": "socal",
                "status": "PASS",
                "cached_input_valid": True,
                "reference_correlation": 0.71,
                "reference_bias_mm_yr": 1.8,
            },
            {
                "candidate": "phass_post_deramp",
                "cell": "socal",
                "status": "PASS",
                "cached_input_valid": True,
                "reference_correlation": 0.68,
                "reference_bias_mm_yr": 2.1,
                "partial_metrics": False,
            },
        ]
        metrics = DISPCellMetrics.model_validate(data)
        assert len(metrics.candidate_outcomes) == 2
        assert metrics.candidate_outcomes[0].candidate == "spurt_native"
        assert metrics.candidate_outcomes[1].candidate == "phass_post_deramp"

    def test_candidate_outcomes_blocker_in_disp_cell_metrics(self) -> None:
        from subsideo.validation.matrix_schema import DISPCellMetrics

        data = _make_base_disp_cell_metrics_dict()
        data["candidate_outcomes"] = [
            {
                "candidate": "spurt_native",
                "cell": "bologna",
                "status": "BLOCKER",
                "failed_stage": "phase_linking",
                "error_summary": "dolphin raised MemoryError",
                "evidence_paths": ["eval-disp/candidates/spurt_native/crash.log"],
                "cached_input_valid": True,
                "partial_metrics": True,
            }
        ]
        metrics = DISPCellMetrics.model_validate(data)
        assert metrics.candidate_outcomes[0].status == "BLOCKER"
        assert metrics.candidate_outcomes[0].partial_metrics is True

    def test_candidate_outcomes_json_round_trip(self) -> None:
        from subsideo.validation.matrix_schema import DISPCellMetrics

        data = _make_base_disp_cell_metrics_dict()
        data["candidate_outcomes"] = [
            {
                "candidate": "phass_post_deramp",
                "cell": "bologna",
                "status": "FAIL",
                "cached_input_valid": True,
                "reference_correlation": 0.33,
            }
        ]
        metrics = DISPCellMetrics.model_validate(data)
        raw = json.loads(metrics.model_dump_json())
        restored = DISPCellMetrics.model_validate(raw)
        assert restored.candidate_outcomes[0].reference_correlation == pytest.approx(0.33)
        assert restored.candidate_outcomes[0].status == "FAIL"

    def test_extra_field_in_candidate_outcome_raises(self) -> None:
        """ConfigDict(extra='forbid') propagates through candidate_outcomes list."""
        from subsideo.validation.matrix_schema import DISPCellMetrics

        data = _make_base_disp_cell_metrics_dict()
        data["candidate_outcomes"] = [
            {
                "candidate": "spurt_native",
                "cell": "socal",
                "status": "PASS",
                "cached_input_valid": True,
                "bad_field": "oops",
            }
        ]
        with pytest.raises(ValidationError):
            DISPCellMetrics.model_validate(data)


# ============================================================================
# Task 2: Helper function tests
# ============================================================================


class TestCandidateOutputDir:
    """T-11-01-03: candidate_output_dir returns base_dir/candidates/candidate."""

    def test_spurt_native_output_dir(self) -> None:
        from subsideo.validation.disp_candidates import candidate_output_dir

        result = candidate_output_dir(Path("eval-disp"), "spurt_native")
        assert result == Path("eval-disp/candidates/spurt_native")

    def test_phass_post_deramp_output_dir(self) -> None:
        from subsideo.validation.disp_candidates import candidate_output_dir

        result = candidate_output_dir(Path("eval-disp"), "phass_post_deramp")
        assert result == Path("eval-disp/candidates/phass_post_deramp")

    def test_absolute_base_dir(self) -> None:
        from subsideo.validation.disp_candidates import candidate_output_dir

        result = candidate_output_dir(Path("/data/eval-disp"), "spurt_native")
        assert result == Path("/data/eval-disp/candidates/spurt_native")

    def test_does_not_return_base_dir_itself(self) -> None:
        """T-11-01-03 mitigation: must never return the baseline eval dir."""
        from subsideo.validation.disp_candidates import candidate_output_dir

        result = candidate_output_dir(Path("eval-disp"), "spurt_native")
        assert result != Path("eval-disp")


class TestCandidateStatusFromMetrics:
    """D-09: deterministic PASS/FAIL/BLOCKER from metric thresholds."""

    # BLOCKER: both correlation and ramp_mean are None
    def test_blocker_when_all_metrics_none(self) -> None:
        from subsideo.validation.disp_candidates import candidate_status_from_metrics

        status = candidate_status_from_metrics(
            "spurt_native",
            correlation=None,
            bias_mm_yr=None,
            ramp_mean_magnitude_rad=None,
            attributed_source=None,
        )
        assert status == "BLOCKER"

    def test_blocker_phass_when_all_metrics_none(self) -> None:
        from subsideo.validation.disp_candidates import candidate_status_from_metrics

        status = candidate_status_from_metrics(
            "phass_post_deramp",
            correlation=None,
            bias_mm_yr=None,
            ramp_mean_magnitude_rad=None,
            attributed_source=None,
        )
        assert status == "BLOCKER"

    # SPURT PASS: correlation >= 0.7 AND ramp_mean < 5.0 AND attributed_source == "inconclusive"
    def test_spurt_pass_exact_thresholds(self) -> None:
        from subsideo.validation.disp_candidates import candidate_status_from_metrics

        status = candidate_status_from_metrics(
            "spurt_native",
            correlation=0.71,
            bias_mm_yr=2.0,
            ramp_mean_magnitude_rad=4.9,
            attributed_source="inconclusive",
        )
        assert status == "PASS"

    def test_spurt_fail_low_correlation(self) -> None:
        from subsideo.validation.disp_candidates import candidate_status_from_metrics

        status = candidate_status_from_metrics(
            "spurt_native",
            correlation=0.69,
            bias_mm_yr=2.0,
            ramp_mean_magnitude_rad=3.0,
            attributed_source="inconclusive",
        )
        assert status == "FAIL"

    def test_spurt_fail_high_ramp(self) -> None:
        from subsideo.validation.disp_candidates import candidate_status_from_metrics

        status = candidate_status_from_metrics(
            "spurt_native",
            correlation=0.75,
            bias_mm_yr=2.0,
            ramp_mean_magnitude_rad=5.1,
            attributed_source="inconclusive",
        )
        assert status == "FAIL"

    def test_spurt_fail_non_inconclusive_attributed_source(self) -> None:
        from subsideo.validation.disp_candidates import candidate_status_from_metrics

        status = candidate_status_from_metrics(
            "spurt_native",
            correlation=0.75,
            bias_mm_yr=2.0,
            ramp_mean_magnitude_rad=3.0,
            attributed_source="orbit",
        )
        assert status == "FAIL"

    # PHASS PASS: correlation >= 0.5 OR ramp_mean < 1.0
    def test_phass_pass_correlation_threshold(self) -> None:
        from subsideo.validation.disp_candidates import candidate_status_from_metrics

        status = candidate_status_from_metrics(
            "phass_post_deramp",
            correlation=0.49,
            bias_mm_yr=2.0,
            ramp_mean_magnitude_rad=0.9,
            attributed_source="inconclusive",
        )
        assert status == "PASS"

    def test_phass_pass_ramp_threshold(self) -> None:
        from subsideo.validation.disp_candidates import candidate_status_from_metrics

        status = candidate_status_from_metrics(
            "phass_post_deramp",
            correlation=0.49,
            bias_mm_yr=2.0,
            ramp_mean_magnitude_rad=0.9,
            attributed_source="inconclusive",
        )
        assert status == "PASS"

    def test_phass_pass_by_correlation_alone(self) -> None:
        from subsideo.validation.disp_candidates import candidate_status_from_metrics

        status = candidate_status_from_metrics(
            "phass_post_deramp",
            correlation=0.51,
            bias_mm_yr=5.0,
            ramp_mean_magnitude_rad=2.0,
            attributed_source="orbit",
        )
        assert status == "PASS"

    def test_phass_pass_by_ramp_alone(self) -> None:
        from subsideo.validation.disp_candidates import candidate_status_from_metrics

        status = candidate_status_from_metrics(
            "phass_post_deramp",
            correlation=0.3,
            bias_mm_yr=5.0,
            ramp_mean_magnitude_rad=0.5,
            attributed_source="orbit",
        )
        assert status == "PASS"

    def test_phass_fail_both_conditions_unmet(self) -> None:
        from subsideo.validation.disp_candidates import candidate_status_from_metrics

        status = candidate_status_from_metrics(
            "phass_post_deramp",
            correlation=0.3,
            bias_mm_yr=5.0,
            ramp_mean_magnitude_rad=2.0,
            attributed_source="orbit",
        )
        assert status == "FAIL"

    def test_no_era5_axis_in_function_signature(self) -> None:
        """ERA5 must NOT be a candidate axis (D-13)."""
        import inspect

        from subsideo.validation.disp_candidates import candidate_status_from_metrics

        sig = inspect.signature(candidate_status_from_metrics)
        assert "era5" not in str(sig).lower()


class TestMakeCandidateBlocker:
    """D-10: make_candidate_blocker returns DISPCandidateOutcome(status='BLOCKER')."""

    def test_blocker_with_partial_metrics_true(self) -> None:
        from subsideo.validation.disp_candidates import make_candidate_blocker
        from subsideo.validation.matrix_schema import DISPCandidateOutcome

        outcome = make_candidate_blocker(
            candidate="spurt_native",
            cell="socal",
            failed_stage="unwrap",
            error_summary="SPURT failed: segfault in libspurt.so",
            evidence_paths=["eval-disp/candidates/spurt_native/crash.log"],
            cached_input_valid=True,
            partial_metrics=True,
        )
        assert isinstance(outcome, DISPCandidateOutcome)
        assert outcome.status == "BLOCKER"
        assert outcome.partial_metrics is True
        assert outcome.failed_stage == "unwrap"
        assert outcome.error_summary is not None
        assert len(outcome.evidence_paths) == 1

    def test_blocker_default_partial_metrics_false(self) -> None:
        from subsideo.validation.disp_candidates import make_candidate_blocker

        outcome = make_candidate_blocker(
            candidate="phass_post_deramp",
            cell="bologna",
            failed_stage="phase_linking",
            error_summary="dolphin OOM",
            evidence_paths=[],
            cached_input_valid=False,
        )
        assert outcome.status == "BLOCKER"
        assert outcome.partial_metrics is False

    def test_blocker_preserves_candidate_and_cell(self) -> None:
        from subsideo.validation.disp_candidates import make_candidate_blocker

        outcome = make_candidate_blocker(
            candidate="phass_post_deramp",
            cell="bologna",
            failed_stage="timeseries",
            error_summary="MintPy timeout after 3600s",
            evidence_paths=["eval-disp/candidates/phass_post_deramp/mintpy.log"],
            cached_input_valid=True,
        )
        assert outcome.candidate == "phass_post_deramp"
        assert outcome.cell == "bologna"

    def test_blocker_is_schema_valid_pydantic(self) -> None:
        """Output of make_candidate_blocker must be schema-valid for JSON round-trip."""
        from subsideo.validation.disp_candidates import make_candidate_blocker

        outcome = make_candidate_blocker(
            candidate="spurt_native",
            cell="bologna",
            failed_stage="download",
            error_summary="S3 timeout",
            evidence_paths=[],
            cached_input_valid=False,
            partial_metrics=True,
        )
        raw = outcome.model_dump_json()
        from subsideo.validation.matrix_schema import DISPCandidateOutcome

        restored = DISPCandidateOutcome.model_validate_json(raw)
        assert restored.status == "BLOCKER"
        assert restored.partial_metrics is True
