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


def test_registry_has_13_entries() -> None:
    assert len(CRITERIA) == 13


def test_binding_count_and_milestone_field() -> None:
    binding = [c for c in CRITERIA.values() if c.type == "BINDING"]
    calibrating = [c for c in CRITERIA.values() if c.type == "CALIBRATING"]
    assert len(binding) == 9
    assert len(calibrating) == 4
    assert all(c.binding_after_milestone is None for c in binding)
    assert all(c.binding_after_milestone == "v1.2" for c in calibrating)


def test_every_criterion_has_rationale() -> None:
    for c in CRITERIA.values():
        assert c.rationale and len(c.rationale) > 20, (
            f"{c.name} has insufficient rationale: {c.rationale!r}"
        )


def test_expected_criterion_ids() -> None:
    expected = {
        "rtc.rmse_db_max", "rtc.correlation_min",
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
    assert len(accessors) >= 13, f"expected >=13 typed accessors, got {len(accessors)}"
