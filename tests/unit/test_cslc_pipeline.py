"""Unit tests for the CSLC-S1 pipeline orchestrator."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import h5py
import numpy as np
from pytest_mock import MockerFixture
from ruamel.yaml import YAML

from subsideo.products.cslc import (
    generate_cslc_runconfig,
    run_cslc,
    validate_cslc_product,
)
from subsideo.products.types import CSLCConfig


def _make_cslc_config(tmp_path: Path, **overrides: object) -> CSLCConfig:
    """Create a CSLCConfig with sensible defaults for testing."""
    defaults = {
        "safe_file_paths": [tmp_path / "S1A_IW_SLC__1SDV_20230101.zip"],
        "orbit_file_path": tmp_path / "S1A_OPER_AUX_POEORB.EOF",
        "dem_file": tmp_path / "dem.tif",
        "burst_id": ["T001-123456-IW1"],
        "output_dir": tmp_path / "output",
    }
    defaults.update(overrides)
    return CSLCConfig(**defaults)


def _make_test_hdf5(path: Path, *, with_data: bool = True, with_metadata: bool = True) -> Path:
    """Create a minimal OPERA-like CSLC HDF5 file for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as f:
        if with_data:
            grp = f.create_group("data")
            grp.create_dataset("VV", data=np.zeros((10, 10), dtype=np.complex64))
        if with_metadata:
            f.create_group("metadata")
    return path


# --- generate_cslc_runconfig tests ---


def test_generate_cslc_runconfig(tmp_path: Path) -> None:
    """Runconfig YAML has correct compass schema structure."""
    cfg = _make_cslc_config(tmp_path)
    yaml_path = tmp_path / "runconfig.yaml"

    result = generate_cslc_runconfig(cfg, yaml_path)

    assert result == yaml_path
    assert yaml_path.exists()

    yaml = YAML()
    with open(yaml_path) as fh:
        data = yaml.load(fh)

    groups = data["runconfig"]["groups"]
    assert groups["primary_executable"]["product_type"] == "CSLC_S1"
    assert isinstance(groups["input_file_group"]["safe_file_path"], list)
    assert "scratch" in groups["product_path_group"]["scratch_path"]
    assert isinstance(groups["dynamic_ancillary_file_group"]["dem_file"], str)
    assert groups["input_file_group"]["burst_id"] == ["T001-123456-IW1"]


def test_generate_cslc_runconfig_no_tec(tmp_path: Path) -> None:
    """Runconfig with tec_file=None writes null in YAML."""
    cfg = _make_cslc_config(tmp_path, tec_file=None)
    yaml_path = tmp_path / "runconfig.yaml"

    generate_cslc_runconfig(cfg, yaml_path)

    yaml = YAML()
    with open(yaml_path) as fh:
        data = yaml.load(fh)

    tec = data["runconfig"]["groups"]["dynamic_ancillary_file_group"]["tec_file"]
    assert tec is None


# --- validate_cslc_product tests ---


def test_validate_cslc_product_valid(tmp_path: Path) -> None:
    """Valid HDF5 with /data/VV and /metadata passes validation."""
    h5_path = _make_test_hdf5(tmp_path / "cslc_valid.h5")

    errors = validate_cslc_product([h5_path])

    assert errors == []


def test_validate_cslc_product_missing_data(tmp_path: Path) -> None:
    """HDF5 without /data group reports an error."""
    h5_path = _make_test_hdf5(
        tmp_path / "cslc_no_data.h5", with_data=False, with_metadata=True
    )

    errors = validate_cslc_product([h5_path])

    assert len(errors) > 0
    assert any("data" in e.lower() for e in errors)


# --- run_cslc tests ---


def test_run_cslc_mocked(tmp_path: Path, mocker: MockerFixture) -> None:
    """Full pipeline with mocked compass produces valid CSLCResult."""
    out_dir = tmp_path / "out"
    h5_path = out_dir / "t001_123456_iw1_20230101.h5"

    def _fake_compass_run(run_config_path: str, grid_type: str) -> None:
        """Simulate compass output: create a valid HDF5 file."""
        _make_test_hdf5(h5_path)

    # Mock the compass import inside run_cslc
    mock_module = MagicMock()
    mock_module.run = _fake_compass_run
    mocker.patch.dict("sys.modules", {"compass": MagicMock(), "compass.s1_cslc": mock_module})

    result = run_cslc(
        safe_paths=[tmp_path / "S1A.zip"],
        orbit_path=tmp_path / "orbit.EOF",
        dem_path=tmp_path / "dem.tif",
        burst_ids=["T001"],
        output_dir=out_dir,
    )

    assert result.valid is True
    assert result.burst_ids == ["T001"]
    assert result.runconfig_path.exists()
    assert len(result.output_paths) == 1
    assert result.validation_errors == []
