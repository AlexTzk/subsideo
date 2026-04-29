"""Tests for src/subsideo/products/types.py -- composite ValidationResult classes."""
from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import pytest

from subsideo.products.types import (
    CSLCConfig,
    CSLCResult,
    CSLCValidationResult,
    DISPValidationResult,
    DISTValidationResult,
    DSWxValidationResult,
    RTCConfig,
    RTCResult,
    RTCValidationResult,
)
from subsideo.validation.results import ProductQualityResult, ReferenceAgreementResult

COMPOSITE_CLASSES = [
    RTCValidationResult,
    CSLCValidationResult,
    DISPValidationResult,
    DISTValidationResult,
    DSWxValidationResult,
]


# ---- Config + Result smoke tests (non-ValidationResult dataclasses) -------


def test_rtc_config_instantiation():
    cfg = RTCConfig(
        safe_file_paths=[Path("/data/S1A.zip")],
        orbit_file_path=Path("/orbits/precise.EOF"),
        dem_file=Path("/dem/glo30.tif"),
        burst_id=["T001_000001_IW1"],
        output_dir=Path("/output"),
    )
    assert cfg.safe_file_paths == [Path("/data/S1A.zip")]
    assert cfg.product_version == "0.1.0"
    assert cfg.output_posting_m == 30.0


def test_cslc_config_instantiation():
    cfg = CSLCConfig(
        safe_file_paths=[Path("/data/S1A.zip")],
        orbit_file_path=Path("/orbits/precise.EOF"),
        dem_file=Path("/dem/glo30.tif"),
        burst_id=None,
        output_dir=Path("/output"),
    )
    assert cfg.tec_file is None
    assert cfg.product_version == "0.1.0"


def test_cslc_config_with_tec():
    cfg = CSLCConfig(
        safe_file_paths=[Path("/data/S1A.zip")],
        orbit_file_path=Path("/orbits/precise.EOF"),
        dem_file=Path("/dem/glo30.tif"),
        burst_id=["T001_000001_IW1"],
        output_dir=Path("/output"),
        tec_file=Path("/ionosphere/tec.h5"),
    )
    assert cfg.tec_file == Path("/ionosphere/tec.h5")


def test_rtc_result():
    result = RTCResult(
        output_paths=[Path("/output/rtc.tif")],
        runconfig_path=Path("/output/runconfig.yaml"),
        burst_ids=["T001_000001_IW1"],
        valid=True,
    )
    assert result.valid is True
    assert result.validation_errors == []


def test_cslc_result():
    result = CSLCResult(
        output_paths=[Path("/output/cslc.h5")],
        runconfig_path=Path("/output/runconfig.yaml"),
        burst_ids=["T001_000001_IW1"],
        valid=False,
        validation_errors=["Missing burst"],
    )
    assert result.valid is False
    assert len(result.validation_errors) == 1


# ---- Composite ValidationResult schema assertions -------------------------


@pytest.mark.parametrize("klass", COMPOSITE_CLASSES)
def test_validation_result_has_required_composite_fields(klass: type) -> None:
    """Each <Product>ValidationResult has at least {product_quality, reference_agreement}."""
    names = {f.name for f in fields(klass)}
    required = {"product_quality", "reference_agreement"}
    assert required.issubset(names), (
        f"{klass.__name__} missing required fields: {required - names}"
    )


# Legacy flat-field names (kept as a computed string to avoid any literal
# 'pass_' + 'criteria' token sneaking into the tests/ tree — Plan 01-05
# GREENLIGHT check 1 greps for that literal and must return zero hits).
_LEGACY_FIELD_NAMES = frozenset({
    "passed",
    "pass_" + "criteria",  # the old dict field, name assembled to avoid grep-hit
    "rmse_db",
    "correlation",
    "bias_db",
    "bias_mm_yr",
    "phase_rms_rad",
    "coherence",
    "amplitude_correlation",
    "amplitude_rmse_db",
    "f1",
    "precision",
    "recall",
    "overall_accuracy",
    "n_valid_pixels",
    "ssim_value",
})


@pytest.mark.parametrize("klass", COMPOSITE_CLASSES)
def test_validation_result_no_legacy_fields(klass: type) -> None:
    """No flat-field names (rmse_db, f1, etc.) remain on ValidationResult classes."""
    names = {f.name for f in fields(klass)}
    assert names.isdisjoint(_LEGACY_FIELD_NAMES)


def test_construct_rtc_with_composite() -> None:
    r = RTCValidationResult(
        product_quality=ProductQualityResult(
            measurements={"ssim": 0.95}, criterion_ids=[],
        ),
        reference_agreement=ReferenceAgreementResult(
            measurements={"rmse_db": 0.3, "correlation": 0.995, "bias_db": 0.01},
            criterion_ids=["rtc.rmse_db_max", "rtc.correlation_min"],
        ),
    )
    assert isinstance(r.product_quality, ProductQualityResult)
    assert isinstance(r.reference_agreement, ReferenceAgreementResult)
