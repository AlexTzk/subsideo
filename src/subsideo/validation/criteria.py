"""Immutable metrics-vs-targets criterion registry.

Every criterion here is either inherited verbatim from v1.0 compare_*.py
hardcoded thresholds or introduced for Phase 3/4 CSLC/DISP self-consistency
as CALIBRATING with binding_after_milestone='v1.2'.

Editing this file requires citing an ADR, upstream spec change, or ground-
truth validation in the PR description (D-03). Immutability is enforced
via frozen=True + drift visibility via matrix_writer.py (Plan 01-09)
echoing each criterion's threshold alongside the measured value in
results/matrix.md.

DO NOT pre-populate Phase 5 deliverables here (D-05). Phase 5 adds its
own entries when it lands (EFFIS precision/recall, DSWx recalibration F1).

Coverage:
  9 v1.0 BINDING (RTC x2, CSLC amplitude x2, DISP x2, DIST x2, DSWx x1)
  4 v1.1 CALIBRATING (CSLC self-consistency x2, DISP self-consistency x2)
  2 v1.1 INVESTIGATION_TRIGGER (RTC-EU Phase 2 D-13: RMSE, r -- NOT gates)
 = 15 total.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Criterion:
    """A single pass/fail threshold with provenance."""

    name: str
    threshold: float
    comparator: Literal[">", ">=", "<", "<="]
    type: Literal["BINDING", "CALIBRATING", "INVESTIGATION_TRIGGER"]
    binding_after_milestone: str | None
    rationale: str


CRITERIA: dict[str, Criterion] = {
    # -- RTC BINDING (v1.0 compare_rtc.py:68-71) --
    "rtc.rmse_db_max": Criterion(
        name="rtc.rmse_db_max", threshold=0.5, comparator="<", type="BINDING",
        binding_after_milestone=None,
        rationale=(
            "OPERA RTC-S1 N.Am. agreement baseline (CONCLUSIONS_RTC_N_AM.md "
            "Sec 3); reference-agreement criterion, never tightened toward "
            "N.Am.'s observed 0.045 dB headroom (PITFALLS M1 target-creep prevention)."
        ),
    ),
    "rtc.correlation_min": Criterion(
        name="rtc.correlation_min", threshold=0.99, comparator=">", type="BINDING",
        binding_after_milestone=None,
        rationale=(
            "OPERA RTC-S1 cross-version correlation, hardcoded v1.0 "
            "compare_rtc.py:70; inherited unchanged."
        ),
    ),
    # -- RTC-EU INVESTIGATION triggers (Phase 2 D-13) --
    # NOT gates. Non-gate markers flagging per-burst deviations that warrant
    # a structured CONCLUSIONS_RTC_EU.md investigation sub-section (D-14).
    # MUST NOT be used to tighten BINDING rtc.rmse_db_max/rtc.correlation_min
    # (RTC-02 explicit).
    "rtc.eu.investigation_rmse_db_min": Criterion(
        name="rtc.eu.investigation_rmse_db_min", threshold=0.15, comparator=">=",
        type="INVESTIGATION_TRIGGER", binding_after_milestone=None,
        rationale=(
            "EU RTC per-burst investigation trigger (~3x N.Am. baseline "
            "0.045 dB); still well below BINDING rtc.rmse_db_max (0.5 dB). "
            "NOT a gate -- triggers a CONCLUSIONS_RTC_EU.md investigation "
            "sub-section per D-14 when a burst meets or exceeds this RMSE. "
            "RTC-02: reference-agreement gates never tighten based on per-"
            "burst scores (PITFALLS M1 target-creep prevention)."
        ),
    ),
    "rtc.eu.investigation_r_max": Criterion(
        name="rtc.eu.investigation_r_max", threshold=0.999, comparator="<",
        type="INVESTIGATION_TRIGGER", binding_after_milestone=None,
        rationale=(
            "EU RTC per-burst investigation trigger (1 order of magnitude "
            "below N.Am. baseline r = 0.9999); still above BINDING "
            "rtc.correlation_min (0.99). Catches structural disagreement "
            "(geometric shift, mis-registration) that RMSE may miss. "
            "NOT a gate -- D-14 CONCLUSIONS investigation trigger. "
            "RTC-02: criteria never tighten."
        ),
    ),
    # -- CSLC amplitude BINDING (v1.0 compare_cslc.py:174-183) --
    "cslc.amplitude_r_min": Criterion(
        name="cslc.amplitude_r_min", threshold=0.6, comparator=">", type="BINDING",
        binding_after_milestone=None,
        rationale=(
            "Cross-version isce3 phase-coherence impossibility (CONCLUSIONS_CSLC_N_AM.md "
            "Sec 5); amplitude r is the reference-agreement sanity gate when "
            "phase cannot be compared across isce3 majors."
        ),
    ),
    "cslc.amplitude_rmse_db_max": Criterion(
        name="cslc.amplitude_rmse_db_max", threshold=4.0, comparator="<", type="BINDING",
        binding_after_milestone=None,
        rationale=(
            "CSLC amplitude-RMSE ceiling, hardcoded v1.0 compare_cslc.py:180; "
            "inherited reference-agreement sanity gate."
        ),
    ),
    # -- CSLC self-consistency CALIBRATING (Phase 1 D-04) --
    "cslc.selfconsistency.coherence_min": Criterion(
        name="cslc.selfconsistency.coherence_min", threshold=0.7, comparator=">",
        type="CALIBRATING", binding_after_milestone="v1.2",
        rationale=(
            "Stable-terrain sequential-IFG coherence bar -- first rollout Phase 3 "
            "(SoCal / Mojave / Iberian Meseta). Published C-band stable-terrain "
            "coherence is 0.75-0.85 per PITFALLS P2.2; 0.7 is starting bar. "
            "GATE-05: >=3 measured data points before BINDING promotion."
        ),
    ),
    "cslc.selfconsistency.residual_mm_yr_max": Criterion(
        name="cslc.selfconsistency.residual_mm_yr_max", threshold=5.0, comparator="<",
        type="CALIBRATING", binding_after_milestone="v1.2",
        rationale=(
            "Residual mean velocity on reference-frame-aligned stable terrain "
            "(PITFALLS P2.3) -- first rollout Phase 3. Tightening to 1-2 mm/yr "
            "as stacks lengthen beyond 6 months is v2 work (CSLC-V2-02)."
        ),
    ),
    # -- DISP BINDING (v1.0 compare_disp.py:356-363) --
    "disp.correlation_min": Criterion(
        name="disp.correlation_min", threshold=0.92, comparator=">", type="BINDING",
        binding_after_milestone=None,
        rationale=(
            "EGMS Ortho vertical-displacement correlation baseline, hardcoded "
            "v1.0 compare_disp.py:356; reference-agreement criterion."
        ),
    ),
    "disp.bias_mm_yr_max": Criterion(
        name="disp.bias_mm_yr_max", threshold=3.0, comparator="<", type="BINDING",
        binding_after_milestone=None,
        rationale=(
            "Allowed |bias| between subsideo DISP and EGMS reference (mm/yr); "
            "inherited v1.0 compare_disp.py."
        ),
    ),
    # -- DISP self-consistency CALIBRATING (Phase 1 D-04) --
    "disp.selfconsistency.coherence_min": Criterion(
        name="disp.selfconsistency.coherence_min", threshold=0.7, comparator=">",
        type="CALIBRATING", binding_after_milestone="v1.2",
        rationale=(
            "Mirror of CSLC self-consistency coherence gate, applied to DISP "
            "at native 5x10 m (Phase 4). GATE-05: >=3 measured data points "
            "before BINDING promotion."
        ),
    ),
    "disp.selfconsistency.residual_mm_yr_max": Criterion(
        name="disp.selfconsistency.residual_mm_yr_max", threshold=5.0, comparator="<",
        type="CALIBRATING", binding_after_milestone="v1.2",
        rationale=(
            "Mirror of CSLC self-consistency residual at DISP native 5x10 m "
            "(Phase 4). GATE-05: >=3 measured data points before BINDING promotion."
        ),
    ),
    # -- DIST BINDING (v1.0 compare_dist.py:212-215) --
    "dist.f1_min": Criterion(
        name="dist.f1_min", threshold=0.80, comparator=">", type="BINDING",
        binding_after_milestone=None,
        rationale=(
            "DIST-S1 F1 baseline (not tightened toward v0.1's own score); "
            "inherited v1.0 compare_dist.py:213."
        ),
    ),
    "dist.accuracy_min": Criterion(
        name="dist.accuracy_min", threshold=0.85, comparator=">", type="BINDING",
        binding_after_milestone=None,
        rationale=(
            "DIST-S1 overall accuracy baseline, inherited v1.0 compare_dist.py:214."
        ),
    ),
    # -- DSWx BINDING (v1.0 compare_dswx.py:298) --
    "dswx.f1_min": Criterion(
        name="dswx.f1_min", threshold=0.90, comparator=">", type="BINDING",
        binding_after_milestone=None,
        rationale=(
            "DSWE-family architectural ceiling ~=0.92 per PROTEUS ATBD "
            "(CONCLUSIONS_DSWX.md Sec 3). 0.90 bar is ~2 pts below ceiling; "
            "moving it requires ML upgrade path (DSWX-V2-01) -- M4 goalpost "
            "prevention."
        ),
    ),
}


# -- Typed accessor functions (D-02) --


def rtc_rmse_db_max() -> Criterion:
    return CRITERIA["rtc.rmse_db_max"]


def rtc_correlation_min() -> Criterion:
    return CRITERIA["rtc.correlation_min"]


def cslc_amplitude_r_min() -> Criterion:
    return CRITERIA["cslc.amplitude_r_min"]


def cslc_amplitude_rmse_db_max() -> Criterion:
    return CRITERIA["cslc.amplitude_rmse_db_max"]


def cslc_selfconsistency_coherence_min() -> Criterion:
    return CRITERIA["cslc.selfconsistency.coherence_min"]


def cslc_selfconsistency_residual_mm_yr_max() -> Criterion:
    return CRITERIA["cslc.selfconsistency.residual_mm_yr_max"]


def disp_correlation_min() -> Criterion:
    return CRITERIA["disp.correlation_min"]


def disp_bias_mm_yr_max() -> Criterion:
    return CRITERIA["disp.bias_mm_yr_max"]


def disp_selfconsistency_coherence_min() -> Criterion:
    return CRITERIA["disp.selfconsistency.coherence_min"]


def disp_selfconsistency_residual_mm_yr_max() -> Criterion:
    return CRITERIA["disp.selfconsistency.residual_mm_yr_max"]


def dist_f1_min() -> Criterion:
    return CRITERIA["dist.f1_min"]


def dist_accuracy_min() -> Criterion:
    return CRITERIA["dist.accuracy_min"]


def dswx_f1_min() -> Criterion:
    return CRITERIA["dswx.f1_min"]


def rtc_eu_investigation_rmse_db_min() -> Criterion:
    return CRITERIA["rtc.eu.investigation_rmse_db_min"]


def rtc_eu_investigation_r_max() -> Criterion:
    return CRITERIA["rtc.eu.investigation_r_max"]
