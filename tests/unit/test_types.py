"""Tests for pipeline types and validation result models."""
from pathlib import Path

from subsideo.products.types import (
    CSLCConfig,
    CSLCResult,
    CSLCValidationResult,
    RTCConfig,
    RTCResult,
    RTCValidationResult,
)


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


def test_rtc_validation_result():
    val = RTCValidationResult(
        rmse_db=0.3,
        correlation=0.99,
        bias_db=0.01,
        ssim_value=0.95,
        pass_criteria={"rmse": True, "correlation": True},
    )
    assert val.rmse_db == 0.3
    assert val.pass_criteria["rmse"] is True


def test_cslc_validation_result():
    val = CSLCValidationResult(
        phase_rms_rad=0.04,
        coherence=0.85,
        pass_criteria={"phase_rms": True},
    )
    assert val.phase_rms_rad == 0.04
    assert val.coherence == 0.85
