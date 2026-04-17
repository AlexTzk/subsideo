"""Unit tests for the CSLC-S1 pipeline orchestrator."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import h5py
import numpy as np
from pytest_mock import MockerFixture
import yaml

from subsideo.products.cslc import (
    generate_cslc_runconfig,
    run_cslc,
    validate_cslc_product,
)
from subsideo.products.types import CSLCConfig, CSLCResult


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

    with open(yaml_path) as fh:
        data = yaml.safe_load(fh)

    groups = data["runconfig"]["groups"]
    assert groups["primary_executable"]["product_type"] == "CSLC_S1"
    assert isinstance(groups["input_file_group"]["safe_file_path"], list)
    assert "scratch" in groups["product_path_group"]["scratch_path"]
    assert isinstance(groups["dynamic_ancillary_file_group"]["dem_file"], str)
    assert groups["input_file_group"]["burst_id"] == ["T001-123456-IW1"]


def test_generate_cslc_runconfig_no_tec(tmp_path: Path) -> None:
    """Runconfig with tec_file=None omits tec_file key (yamale compat)."""
    cfg = _make_cslc_config(tmp_path, tec_file=None)
    yaml_path = tmp_path / "runconfig.yaml"

    generate_cslc_runconfig(cfg, yaml_path)

    with open(yaml_path) as fh:
        data = yaml.safe_load(fh)

    # tec_file key should be absent when tec_file=None
    # (yamale str(required=False) accepts absent key but rejects null)
    ancillary = data["runconfig"]["groups"]["dynamic_ancillary_file_group"]
    assert "tec_file" not in ancillary


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

    # Mock the numpy 2.x compatibility patches (they import real compass/s1reader)
    mocker.patch("subsideo.products.cslc._patch_compass_burst_db_none_guard")
    mocker.patch("subsideo.products.cslc._patch_s1reader_numpy2_compat")
    mocker.patch("subsideo.products.cslc._patch_burst_az_carrier_poly")

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


MOCK_STAC_ITEM = {
    "assets": {"data": {"href": "s3://eodata/test.zip"}},
    "properties": {
        "datetime": "2025-01-15T00:00:00",
        "platform": "S1A",
    },
}


def test_run_cslc_from_aoi_mocked(tmp_path: Path, mocker: MockerFixture) -> None:
    """Verify run_cslc_from_aoi wires all Phase 1 data-access calls correctly."""
    # Mock Settings (B-01)
    mock_settings = MagicMock()
    mock_settings.cdse_client_id = "test-id"
    mock_settings.cdse_client_secret = "test-secret"
    mocker.patch("subsideo.config.Settings", return_value=mock_settings)

    # Mock CDSEClient (B-01 + B-02)
    mock_client_instance = MagicMock()
    mock_client_instance.search_stac.return_value = [MOCK_STAC_ITEM]

    def _fake_download(s3_path: str, output_path: Path, **kwargs: object) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.touch()
        return output_path

    mock_client_instance.download.side_effect = _fake_download
    mock_client_cls = MagicMock(return_value=mock_client_instance)
    mocker.patch("subsideo.data.cdse.CDSEClient", mock_client_cls)

    # Mock burst query (B-03)
    mock_burst = MagicMock()
    mock_burst.burst_id_jpl = "T001_000001_IW1"
    mock_burst.epsg = 32632
    mock_burst_query = mocker.patch(
        "subsideo.burst.frames.query_bursts_for_aoi",
        return_value=[mock_burst],
    )

    # Mock fetch_dem (B-05) — returns tuple
    dem_path = tmp_path / "dem.tif"
    dem_path.touch()
    mock_fetch_dem = mocker.patch(
        "subsideo.data.dem.fetch_dem",
        return_value=(dem_path, {"driver": "GTiff"}),
    )

    # Mock fetch_orbit (B-04)
    orbit_path = tmp_path / "orbit.EOF"
    orbit_path.touch()
    mock_fetch_orbit = mocker.patch(
        "subsideo.data.orbits.fetch_orbit",
        return_value=orbit_path,
    )

    # Mock run_cslc (the inner call)
    mock_cslc_result = CSLCResult(
        output_paths=[tmp_path / "cslc.h5"],
        runconfig_path=tmp_path / "runconfig.yaml",
        burst_ids=["T001_000001_IW1"],
        valid=True,
    )
    mocker.patch("subsideo.products.cslc.run_cslc", return_value=mock_cslc_result)

    aoi = {
        "type": "Polygon",
        "coordinates": [
            [[11.0, 48.0], [12.0, 48.0], [12.0, 49.0], [11.0, 49.0], [11.0, 48.0]]
        ],
    }

    from subsideo.products.cslc import run_cslc_from_aoi

    result = run_cslc_from_aoi(
        aoi=aoi,
        date_range=("2025-01-01", "2025-03-01"),
        output_dir=tmp_path / "out",
    )

    # B-01: CDSEClient gets credentials
    mock_client_cls.assert_called_once_with(
        client_id="test-id", client_secret="test-secret"
    )

    # B-02: search_stac called with correct kwargs
    mock_client_instance.search_stac.assert_called_once()
    search_kwargs = mock_client_instance.search_stac.call_args
    assert search_kwargs.kwargs["collection"] == "SENTINEL-1"
    assert search_kwargs.kwargs["product_type"] == "IW_SLC__1S"
    assert isinstance(search_kwargs.kwargs["start"], __import__("datetime").datetime)
    assert isinstance(search_kwargs.kwargs["end"], __import__("datetime").datetime)
    assert isinstance(search_kwargs.kwargs["bbox"], list)

    # B-03: burst query uses frames module with aoi_wkt
    mock_burst_query.assert_called_once()
    assert "aoi_wkt" in mock_burst_query.call_args.kwargs

    # B-04: fetch_orbit with named args
    mock_fetch_orbit.assert_called_once()
    orbit_kwargs = mock_fetch_orbit.call_args.kwargs
    assert "sensing_time" in orbit_kwargs
    assert orbit_kwargs["satellite"] == "S1A"
    assert "output_dir" in orbit_kwargs

    # B-05: fetch_dem with output_epsg and bounds as list
    mock_fetch_dem.assert_called_once()
    dem_kwargs = mock_fetch_dem.call_args.kwargs
    assert dem_kwargs["output_epsg"] == 32632
    assert isinstance(dem_kwargs["bounds"], list)

    assert result.valid is True
