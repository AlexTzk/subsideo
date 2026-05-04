"""Phase 11 shared candidate helper functions for DISP unwrapper/deramping evaluation.

Provides:
- candidate_output_dir: Returns the candidate-specific output directory.
- candidate_status_from_metrics: Deterministic PASS/FAIL/BLOCKER from metric thresholds.
- make_candidate_blocker: Constructs a schema-valid BLOCKER DISPCandidateOutcome.

Thresholds are taken from the v1.1 DISP_UNWRAPPER_SELECTION_BRIEF.md (D-01 through D-14).
The candidate axis is unwrapper/deramping only — do not add atmospheric correction mode
to any function signature.

Integration:
- Consumed by run_eval_disp.py and run_eval_disp_egms.py in Phase 11 candidate runners.
- Output DISPCandidateOutcome records are appended to DISPCellMetrics.candidate_outcomes
  in the canonical metrics.json sidecar (D-12 additive pattern).
"""

from __future__ import annotations

from pathlib import Path

from subsideo.validation.matrix_schema import (
    AttributedSource,
    DISPCandidateCell,
    DISPCandidateName,
    DISPCandidateOutcome,
    DISPCandidateStatus,
)


def candidate_output_dir(base_dir: Path, candidate: DISPCandidateName) -> Path:
    """Return the candidate-specific output directory inside base_dir.

    The returned path is always ``base_dir / "candidates" / candidate`` —
    never the baseline eval directory itself (T-11-01-03 mitigation).

    Args:
        base_dir: The base eval output directory (e.g. ``Path("eval-disp")``).
        candidate: One of ``"spurt_native"`` or ``"phass_post_deramp"``.

    Returns:
        ``base_dir / "candidates" / candidate``

    Example:
        >>> candidate_output_dir(Path("eval-disp"), "spurt_native")
        PosixPath('eval-disp/candidates/spurt_native')
    """
    return base_dir / "candidates" / candidate


def candidate_status_from_metrics(
    candidate: DISPCandidateName,
    *,
    correlation: float | None,
    bias_mm_yr: float | None,
    ramp_mean_magnitude_rad: float | None,
    attributed_source: AttributedSource | None,
) -> DISPCandidateStatus:
    """Compute deterministic PASS/FAIL/BLOCKER status from candidate metrics.

    Thresholds are taken from DISP_UNWRAPPER_SELECTION_BRIEF.md and D-01 through D-14.
    Atmospheric correction mode is not a candidate axis (D-13/D-14).

    BLOCKER rule (both candidates):
        Return "BLOCKER" when *both* ``correlation is None`` and
        ``ramp_mean_magnitude_rad is None`` — indicating insufficient metrics to
        classify the outcome.

    SPURT native (``candidate == "spurt_native"``) PASS rule:
        ``correlation >= 0.7 AND ramp_mean_magnitude_rad < 5.0
        AND attributed_source == "inconclusive"``

    PHASS post-deramp (``candidate == "phass_post_deramp"``) PASS rule:
        ``(correlation >= 0.5) OR (ramp_mean_magnitude_rad < 1.0)``

    Otherwise: FAIL.

    Args:
        candidate: ``"spurt_native"`` or ``"phass_post_deramp"``.
        correlation: Pearson r against reference. None if not computed.
        bias_mm_yr: Velocity bias in mm/yr. None if not computed.
        ramp_mean_magnitude_rad: Mean IFG ramp magnitude in radians. None if not computed.
        attributed_source: Ramp attribution label. None if ramp diagnostics unavailable.

    Returns:
        One of ``"PASS"``, ``"FAIL"``, or ``"BLOCKER"``.
    """
    # BLOCKER: insufficient metrics to classify
    if correlation is None and ramp_mean_magnitude_rad is None:
        return "BLOCKER"

    if candidate == "spurt_native":
        # SPURT native: correlation >= 0.7, ramp < 5.0 rad, attributed=inconclusive
        if (
            correlation is not None
            and correlation >= 0.7
            and ramp_mean_magnitude_rad is not None
            and ramp_mean_magnitude_rad < 5.0
            and attributed_source == "inconclusive"
        ):
            return "PASS"
        return "FAIL"

    else:  # candidate == "phass_post_deramp"
        # PHASS deramping requires: correlation >= 0.5 OR ramp_mean < 1.0 rad
        corr_pass = correlation is not None and correlation >= 0.5
        ramp_pass = ramp_mean_magnitude_rad is not None and ramp_mean_magnitude_rad < 1.0
        if corr_pass or ramp_pass:
            return "PASS"
        return "FAIL"


def make_candidate_blocker(
    candidate: DISPCandidateName,
    cell: DISPCandidateCell,
    failed_stage: str,
    error_summary: str,
    evidence_paths: list[str],
    cached_input_valid: bool,
    partial_metrics: bool = False,
) -> DISPCandidateOutcome:
    """Construct a schema-valid BLOCKER DISPCandidateOutcome (D-10).

    All required BLOCKER evidence fields are preserved:
    - candidate name and cell
    - failed stage
    - error summary
    - evidence/log artifact paths
    - cached-input validity flag
    - partial metrics flag

    Args:
        candidate: One of ``"spurt_native"`` or ``"phass_post_deramp"``.
        cell: One of ``"socal"`` or ``"bologna"``.
        failed_stage: Pipeline stage where the block was triggered (e.g. ``"unwrap"``).
        error_summary: repr(exception) or human-readable error description.
        evidence_paths: List of log or artifact file paths produced before the block.
        cached_input_valid: True when the cached stack inputs were verified valid.
        partial_metrics: True when some metric outputs were produced before blocking.

    Returns:
        A ``DISPCandidateOutcome`` with ``status="BLOCKER"`` and all evidence fields set.
    """
    return DISPCandidateOutcome(
        candidate=candidate,
        cell=cell,
        status="BLOCKER",
        failed_stage=failed_stage,
        error_summary=error_summary,
        evidence_paths=evidence_paths,
        cached_input_valid=cached_input_valid,
        partial_metrics=partial_metrics,
    )
