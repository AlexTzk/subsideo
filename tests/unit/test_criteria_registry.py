"""Smoke tests for subsideo.validation.criteria (GATE-01, GATE-05)."""
from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, is_dataclass

import pytest

from subsideo.validation import criteria as criteria_mod
from subsideo.validation.criteria import CRITERIA, Criterion


def test_criterion_is_frozen_dataclass() -> None:
    assert is_dataclass(Criterion)
    c = next(iter(CRITERIA.values()))
    with pytest.raises(FrozenInstanceError):
        c.threshold = 99.0  # type: ignore[misc]


def test_registry_has_16_entries() -> None:
    # Phase 6 D-20 added dswx.nam.investigation_f1_max (16 total; was 15 in Phase 5).
    assert len(CRITERIA) == 16


def test_binding_count_and_milestone_field() -> None:
    binding = [c for c in CRITERIA.values() if c.type == "BINDING"]
    calibrating = [c for c in CRITERIA.values() if c.type == "CALIBRATING"]
    investigation = [c for c in CRITERIA.values() if c.type == "INVESTIGATION_TRIGGER"]
    assert len(binding) == 9
    assert len(calibrating) == 4
    assert len(investigation) == 3  # Phase 6 adds dswx.nam.investigation_f1_max
    assert all(c.binding_after_milestone is None for c in binding)
    assert all(c.binding_after_milestone == "v1.2" for c in calibrating)
    assert all(c.binding_after_milestone is None for c in investigation)


def test_every_criterion_has_rationale() -> None:
    for c in CRITERIA.values():
        assert c.rationale and len(c.rationale) > 20, (
            f"{c.name} has insufficient rationale: {c.rationale!r}"
        )


def test_expected_criterion_ids() -> None:
    expected = {
        "rtc.rmse_db_max", "rtc.correlation_min",
        "rtc.eu.investigation_rmse_db_min", "rtc.eu.investigation_r_max",
        "cslc.amplitude_r_min", "cslc.amplitude_rmse_db_max",
        "cslc.selfconsistency.coherence_min", "cslc.selfconsistency.residual_mm_yr_max",
        "disp.correlation_min", "disp.bias_mm_yr_max",
        "disp.selfconsistency.coherence_min", "disp.selfconsistency.residual_mm_yr_max",
        "dist.f1_min", "dist.accuracy_min",
        "dswx.f1_min",
        # Phase 6 D-20 addition:
        "dswx.nam.investigation_f1_max",
    }
    assert set(CRITERIA.keys()) == expected


def test_no_phase5_placeholders() -> None:
    """D-05: no EFFIS or DSWx recalibration entries at Phase 1."""
    for cid in CRITERIA:
        lc = cid.lower()
        assert "effis" not in lc
        assert "recalibrated" not in lc


def test_typed_accessors_exist() -> None:
    accessors = [
        name for name, obj in inspect.getmembers(criteria_mod, inspect.isfunction)
        if not name.startswith("_") and obj.__module__ == criteria_mod.__name__
    ]
    assert len(accessors) >= 15, f"expected >=15 typed accessors, got {len(accessors)}"


# ---------------------------------------------------------------------------
# Phase 2 additions: INVESTIGATION_TRIGGER registry + RTC-02 guardrails
# ---------------------------------------------------------------------------


def test_investigation_triggers_do_not_mutate_rtc_binding() -> None:
    """RTC-02: the two BINDING RTC criteria MUST remain at their v1.0 thresholds.

    This test is the enforcement point for RTC-02 ("EU RTC reference-agreement
    criteria are identical to N.Am. and DO NOT tighten based on per-burst
    scores"). Any Phase 2 edit that tightens these two fails this test.
    """
    assert CRITERIA["rtc.rmse_db_max"].threshold == 0.5
    assert CRITERIA["rtc.rmse_db_max"].comparator == "<"
    assert CRITERIA["rtc.rmse_db_max"].type == "BINDING"
    assert CRITERIA["rtc.correlation_min"].threshold == 0.99
    assert CRITERIA["rtc.correlation_min"].comparator == ">"
    assert CRITERIA["rtc.correlation_min"].type == "BINDING"


def test_investigation_trigger_type_literal_accepts() -> None:
    """Criterion.type Literal extended to accept 'INVESTIGATION_TRIGGER'."""
    c = Criterion(
        name="test.smoke", threshold=1.0, comparator=">=",
        type="INVESTIGATION_TRIGGER", binding_after_milestone=None,
        rationale="smoke test of extended Literal",
    )
    assert c.type == "INVESTIGATION_TRIGGER"


def test_no_rtc_eu_gate_entries() -> None:
    """RTC-02 structural enforcement: rtc.eu.* must only be INVESTIGATION_TRIGGER.

    If a future edit adds e.g. 'rtc.eu.rmse_db_max' as BINDING or CALIBRATING,
    this test fails. Prevents silent criterion-creep.
    """
    rtc_eu_keys = [k for k in CRITERIA if k.startswith("rtc.eu.")]
    assert len(rtc_eu_keys) == 2, (
        f"Only 2 rtc.eu.* entries allowed (the two INVESTIGATION_TRIGGER "
        f"entries from Phase 2 D-13); got {rtc_eu_keys}"
    )
    for k in rtc_eu_keys:
        assert CRITERIA[k].type == "INVESTIGATION_TRIGGER", (
            f"{k}: rtc.eu.* criteria MUST be type='INVESTIGATION_TRIGGER' "
            f"(RTC-02 anti-tightening); got type={CRITERIA[k].type!r}"
        )


def test_investigation_trigger_accessors() -> None:
    """Typed accessors exist for the 2 new INVESTIGATION_TRIGGER entries."""
    from subsideo.validation.criteria import (
        rtc_eu_investigation_r_max,
        rtc_eu_investigation_rmse_db_min,
    )

    a = rtc_eu_investigation_rmse_db_min()
    assert a.threshold == 0.15
    assert a.type == "INVESTIGATION_TRIGGER"
    assert a.comparator == ">="
    b = rtc_eu_investigation_r_max()
    assert b.threshold == 0.999
    assert b.type == "INVESTIGATION_TRIGGER"
    assert b.comparator == "<"


# ---------------------------------------------------------------------------
# Phase 3 additions: gate_metric_key field on Criterion (D-04)
# ---------------------------------------------------------------------------


class TestGateMetricKey:
    """Phase 3 D-04: Criterion has gate_metric_key field; CSLC entries tagged."""

    def test_cslc_selfconsistency_coherence_min_gate_metric_key(self) -> None:
        """CSLC coherence criterion uses 'median_of_persistent' as gate stat."""
        assert CRITERIA["cslc.selfconsistency.coherence_min"].gate_metric_key == "median_of_persistent"

    def test_cslc_selfconsistency_residual_gate_metric_key(self) -> None:
        """CSLC residual criterion also tags gate_metric_key (D-04 audit record)."""
        assert CRITERIA["cslc.selfconsistency.residual_mm_yr_max"].gate_metric_key == "median_of_persistent"

    def test_all_other_criteria_have_gate_metric_key_field(self) -> None:
        """All Criterion instances (not just CSLC) carry the field (default ok)."""
        for cid, c in CRITERIA.items():
            assert hasattr(c, "gate_metric_key"), f"{cid} missing gate_metric_key"

    def test_gate_metric_key_default_value(self) -> None:
        """Non-CSLC-selfconsistency entries carry the default (any value acceptable)."""
        # The field must exist; its value is irrelevant for non-selfconsistency rows.
        rtc = CRITERIA["rtc.rmse_db_max"]
        assert isinstance(rtc.gate_metric_key, str)

    def test_criterion_frozen_with_gate_metric_key(self) -> None:
        """gate_metric_key field respects frozen=True invariant."""
        from dataclasses import FrozenInstanceError

        c = Criterion(
            name="test.gatemk",
            threshold=1.0,
            comparator=">",
            type="BINDING",
            binding_after_milestone=None,
            rationale="smoke test gate_metric_key frozen",
            gate_metric_key="foo",
        )
        assert c.gate_metric_key == "foo"
        with pytest.raises(FrozenInstanceError):
            c.gate_metric_key = "bar"  # type: ignore[misc]

    def test_cslc_calibrating_thresholds_unchanged(self) -> None:
        """M1 target-creep prevention: thresholds must not change when adding field."""
        assert CRITERIA["cslc.selfconsistency.coherence_min"].threshold == 0.7
        assert CRITERIA["cslc.selfconsistency.coherence_min"].type == "CALIBRATING"
        assert CRITERIA["cslc.selfconsistency.coherence_min"].binding_after_milestone == "v1.2"
        assert CRITERIA["cslc.selfconsistency.residual_mm_yr_max"].threshold == 5.0
        assert CRITERIA["cslc.selfconsistency.residual_mm_yr_max"].type == "CALIBRATING"
