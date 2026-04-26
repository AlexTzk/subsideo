"""Tests for src/subsideo/validation/criteria.py — Phase 6 DSWx INVESTIGATION_TRIGGER."""
from __future__ import annotations

from subsideo.validation.criteria import CRITERIA, Criterion


def test_dswx_nam_investigation_trigger_present() -> None:
    assert "dswx.nam.investigation_f1_max" in CRITERIA


def test_dswx_nam_investigation_trigger_shape() -> None:
    c = CRITERIA["dswx.nam.investigation_f1_max"]
    assert isinstance(c, Criterion)
    assert c.name == "dswx.nam.investigation_f1_max"
    assert c.threshold == 0.85
    assert c.comparator == "<"
    assert c.type == "INVESTIGATION_TRIGGER"
    assert c.binding_after_milestone is None


def test_dswx_nam_investigation_rationale_text() -> None:
    """Rationale must reference the gating action so matrix_writer renders correctly."""
    c = CRITERIA["dswx.nam.investigation_f1_max"]
    text = c.rationale
    assert "F1 < 0.85" in text
    assert "BOA-offset" in text or "BOA offset" in text
    assert "Claverie" in text
    assert "SCL-mask" in text or "SCL mask" in text
    assert "halts EU recalibration" in text or "halt EU recalibration" in text
    assert "BINDING dswx.f1_min stays at 0.90" in text


def test_dswx_f1_min_binding_unchanged() -> None:
    """Phase 6 D-29: ZERO edits to existing dswx.f1_min BINDING."""
    c = CRITERIA["dswx.f1_min"]
    assert c.threshold == 0.90
    assert c.comparator == ">"
    assert c.type == "BINDING"
    assert c.binding_after_milestone is None


def test_criteria_count_after_phase_6_addition() -> None:
    """Phase 6 adds exactly 1 entry -> count = 16 total per module docstring."""
    # 9 v1.0 BINDING + 4 v1.1 CALIBRATING + 3 INVESTIGATION_TRIGGER = 16
    investigation_count = sum(
        1 for c in CRITERIA.values() if c.type == "INVESTIGATION_TRIGGER"
    )
    assert investigation_count == 3, (
        f"expected 3 INVESTIGATION_TRIGGER (RTC-EU x2 + DSWx-NAM x1), "
        f"got {investigation_count}"
    )
