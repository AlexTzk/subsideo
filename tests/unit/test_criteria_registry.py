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


def test_registry_has_15_entries() -> None:
    assert len(CRITERIA) == 15


def test_binding_count_and_milestone_field() -> None:
    binding = [c for c in CRITERIA.values() if c.type == "BINDING"]
    calibrating = [c for c in CRITERIA.values() if c.type == "CALIBRATING"]
    investigation = [c for c in CRITERIA.values() if c.type == "INVESTIGATION_TRIGGER"]
    assert len(binding) == 9
    assert len(calibrating) == 4
    assert len(investigation) == 2
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
