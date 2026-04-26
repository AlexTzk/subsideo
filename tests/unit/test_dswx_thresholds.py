"""Tests for src/subsideo/products/dswx_thresholds.py + Settings.dswx_region."""
from __future__ import annotations

import math
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from pydantic import ValidationError

from subsideo.products.dswx_thresholds import (
    THRESHOLDS_BY_REGION,
    THRESHOLDS_EU,
    THRESHOLDS_NAM,
    DSWEThresholds,
)


def test_dswethresholds_imports() -> None:
    assert DSWEThresholds.__name__ == "DSWEThresholds"
    assert THRESHOLDS_NAM is not None
    assert THRESHOLDS_EU is not None
    assert isinstance(THRESHOLDS_BY_REGION, dict)


def test_thresholds_nam_proteus_defaults() -> None:
    assert THRESHOLDS_NAM.WIGT == 0.124
    assert THRESHOLDS_NAM.AWGT == 0.0
    assert THRESHOLDS_NAM.PSWT2_MNDWI == -0.5


def test_thresholds_nam_provenance_sentinels() -> None:
    assert THRESHOLDS_NAM.grid_search_run_date == "1996-01-01-PROTEUS-baseline"
    assert THRESHOLDS_NAM.fit_set_hash == "n/a"
    assert math.isnan(THRESHOLDS_NAM.fit_set_mean_f1)
    assert math.isnan(THRESHOLDS_NAM.held_out_balaton_f1)
    assert math.isnan(THRESHOLDS_NAM.loocv_mean_f1)
    assert math.isnan(THRESHOLDS_NAM.loocv_gap)
    assert THRESHOLDS_NAM.notebook_path == "n/a"
    assert THRESHOLDS_NAM.results_json_path == "n/a"
    assert "PROTEUS" in THRESHOLDS_NAM.provenance_note


def test_dswethresholds_frozen() -> None:
    with pytest.raises(FrozenInstanceError):
        THRESHOLDS_NAM.WIGT = 0.5  # type: ignore[misc]


def test_dswethresholds_slots() -> None:
    assert hasattr(DSWEThresholds, "__slots__")
    assert len(DSWEThresholds.__slots__) > 0
    # slots=True prevents creating new attributes (raises TypeError or AttributeError
    # depending on Python version; both indicate the slot restriction is enforced):
    with pytest.raises((AttributeError, TypeError)):
        instance = DSWEThresholds(
            WIGT=0.1,
            AWGT=0.0,
            PSWT2_MNDWI=-0.5,
            grid_search_run_date="2026-04-26",
            fit_set_hash="abc",
            fit_set_mean_f1=0.92,
            held_out_balaton_f1=0.88,
            loocv_mean_f1=0.91,
            loocv_gap=0.01,
            notebook_path="notebooks/x.ipynb",
            results_json_path="scripts/x.json",
            provenance_note="test",
        )
        instance.new_field = "garbage"  # type: ignore[attr-defined]


def test_thresholds_by_region_dispatch() -> None:
    assert set(THRESHOLDS_BY_REGION.keys()) == {"nam", "eu"}
    assert THRESHOLDS_BY_REGION["nam"] is THRESHOLDS_NAM
    assert THRESHOLDS_BY_REGION["eu"] is THRESHOLDS_EU


def test_thresholds_eu_placeholder_provenance_paths() -> None:
    # Plan 06-06 overwrites placeholders; until then, paths are placeholders.
    assert THRESHOLDS_EU.notebook_path == "notebooks/dswx_recalibration.ipynb"
    assert (
        THRESHOLDS_EU.results_json_path
        == "scripts/recalibrate_dswe_thresholds_results.json"
    )
    assert "PLACEHOLDER" in THRESHOLDS_EU.provenance_note


def test_settings_dswx_region_default(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure no env-var contamination from a previous test:
    monkeypatch.delenv("SUBSIDEO_DSWX_REGION", raising=False)
    from subsideo.config import Settings

    s = Settings()
    assert s.dswx_region == "nam"


def test_settings_dswx_region_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUBSIDEO_DSWX_REGION", "eu")
    from subsideo.config import Settings

    s = Settings()
    assert s.dswx_region == "eu"


def test_settings_dswx_region_invalid_value() -> None:
    from subsideo.config import Settings

    with pytest.raises(ValidationError):
        Settings(dswx_region="garbage")  # type: ignore[arg-type]


def test_thresholds_eu_sentinel_anchors_present() -> None:
    """W1 fix: Plan 06-06 Stage 10 fail-loud rewrite needs sentinel-comment anchors."""
    src_path = (
        Path(__file__).resolve().parent.parent.parent
        / "src"
        / "subsideo"
        / "products"
        / "dswx_thresholds.py"
    )
    text = src_path.read_text()
    begin = text.find("# ╔═ THRESHOLDS_EU_BEGIN ═")
    end = text.find("# ╚═ THRESHOLDS_EU_END ═")
    assert begin > 0, (
        "THRESHOLDS_EU_BEGIN sentinel anchor missing"
        " — required for W1 Plan 06-06 rewrite"
    )
    assert end > begin, "THRESHOLDS_EU_END sentinel anchor missing or before BEGIN"
