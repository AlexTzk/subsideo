"""Tests for DSWxConfig.region + run_dswx region resolution (CONTEXT D-10)."""
from __future__ import annotations

from pathlib import Path

import pytest

from subsideo.products.dswx_thresholds import (
    THRESHOLDS_BY_REGION,
    THRESHOLDS_EU,
    THRESHOLDS_NAM,
)
from subsideo.products.types import DSWxConfig


def _resolve_region_thresholds(
    config: DSWxConfig,
) -> tuple[object, str]:
    """Mirror the resolution snippet from run_dswx for unit-testing.

    The full run_dswx is integration-tested elsewhere (requires CDSE +
    heavy deps); this helper isolates the precedence logic we need to
    pin down for D-10.
    """
    from subsideo.config import Settings

    settings = Settings()
    region = config.region or settings.dswx_region
    return THRESHOLDS_BY_REGION[region], region


def _make_config(region: str | None = None) -> DSWxConfig:
    return DSWxConfig(
        s2_band_paths={
            "B02": Path("x.tif"), "B03": Path("y.tif"),
            "B04": Path("z.tif"), "B08": Path("a.tif"),
            "B11": Path("b.tif"), "B12": Path("c.tif"),
        },
        scl_path=Path("scl.tif"),
        output_dir=Path("/tmp/dswx_test"),
        region=region,
    )


def test_dswx_config_region_defaults_to_none() -> None:
    cfg = _make_config()
    assert cfg.region is None


def test_dswx_config_region_accepts_nam() -> None:
    cfg = _make_config(region="nam")
    assert cfg.region == "nam"


def test_dswx_config_region_accepts_eu() -> None:
    cfg = _make_config(region="eu")
    assert cfg.region == "eu"


def test_run_dswx_region_resolution_explicit_nam(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUBSIDEO_DSWX_REGION", raising=False)
    cfg = _make_config(region="nam")
    thresholds, region = _resolve_region_thresholds(cfg)
    assert region == "nam"
    assert thresholds is THRESHOLDS_NAM


def test_run_dswx_region_resolution_explicit_eu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUBSIDEO_DSWX_REGION", raising=False)
    cfg = _make_config(region="eu")
    thresholds, region = _resolve_region_thresholds(cfg)
    assert region == "eu"
    assert thresholds is THRESHOLDS_EU


def test_run_dswx_region_resolution_env_var_eu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUBSIDEO_DSWX_REGION", "eu")
    cfg = _make_config(region=None)  # config doesn't override; env wins over default
    thresholds, region = _resolve_region_thresholds(cfg)
    assert region == "eu"
    assert thresholds is THRESHOLDS_EU


def test_run_dswx_region_resolution_default_nam(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUBSIDEO_DSWX_REGION", raising=False)
    cfg = _make_config(region=None)
    thresholds, region = _resolve_region_thresholds(cfg)
    assert region == "nam"
    assert thresholds is THRESHOLDS_NAM


def test_run_dswx_region_resolution_config_overrides_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CONTEXT D-10: config.region takes precedence over env var."""
    monkeypatch.setenv("SUBSIDEO_DSWX_REGION", "eu")
    cfg = _make_config(region="nam")
    thresholds, region = _resolve_region_thresholds(cfg)
    assert region == "nam"
    assert thresholds is THRESHOLDS_NAM
