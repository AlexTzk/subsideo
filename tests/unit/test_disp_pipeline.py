"""Unit tests for the DISP-S1 displacement time-series pipeline."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import rasterio
from pytest_mock import MockerFixture
from rasterio.crs import CRS
from rasterio.transform import from_bounds

from subsideo.products.disp import (
    _check_unwrap_quality,
    _generate_mintpy_template,
    _validate_cds_credentials,
    run_disp,
    run_disp_from_aoi,
)
from subsideo.products.types import DISPResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_CRS = CRS.from_epsg(32632)
_TEST_TRANSFORM = from_bounds(500000, 5300000, 500600, 5300600, 20, 20)


def _make_test_unwrapped_tif(path: Path, *, add_ramp: bool = False) -> Path:
    """Create a small (20x20) unwrapped-phase GeoTIFF."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if add_ramp:
        x, y = np.meshgrid(np.arange(20), np.arange(20))
        rng = np.random.default_rng(123)
        # Strong ramp + significant non-planar noise -> high residual after plane fit
        data = (
            10.0 * x
            + 10.0 * y
            + 50.0 * np.sin(x * 0.5) * np.cos(y * 0.3)
            + rng.standard_normal((20, 20)) * 5.0
        ).astype(np.float32)
    else:
        data = np.ones((20, 20), dtype=np.float32)

    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": 20,
        "height": 20,
        "count": 1,
        "crs": _TEST_CRS,
        "transform": _TEST_TRANSFORM,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data, 1)
    return path


def _make_test_ifg_tif(path: Path) -> Path:
    """Create a small (20x20) interferogram GeoTIFF (float32 phase)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.random.default_rng(42).standard_normal((20, 20)).astype(np.float32)

    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": 20,
        "height": 20,
        "count": 1,
        "crs": _TEST_CRS,
        "transform": _TEST_TRANSFORM,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data, 1)
    return path


def _make_test_cor_tif(path: Path, *, high_coherence: bool = True) -> Path:
    """Create a small (20x20) coherence GeoTIFF."""
    path.parent.mkdir(parents=True, exist_ok=True)
    value = 0.8 if high_coherence else 0.1
    data = np.full((20, 20), value, dtype=np.float32)

    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": 20,
        "height": 20,
        "count": 1,
        "crs": _TEST_CRS,
        "transform": _TEST_TRANSFORM,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data, 1)
    return path


def _write_cdsapirc(path: Path, *, complete: bool = True) -> Path:
    """Write a test .cdsapirc file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["url: https://cds.climate.copernicus.eu/api\n"]
    if complete:
        lines.append("key: 12345:abcdef-0000-1111-2222-333333333333\n")
    path.write_text("".join(lines))
    return path


# ---------------------------------------------------------------------------
# Test 1-3: _validate_cds_credentials
# ---------------------------------------------------------------------------


def test_validate_cds_missing_file(tmp_path: Path) -> None:
    """Raises FileNotFoundError when cdsapirc does not exist."""
    import pytest

    with pytest.raises(FileNotFoundError, match="CDS API config not found"):
        _validate_cds_credentials(tmp_path / "nonexistent")


def test_validate_cds_incomplete_file(tmp_path: Path) -> None:
    """Raises ValueError when cdsapirc is missing key: line."""
    import pytest

    _write_cdsapirc(tmp_path / ".cdsapirc", complete=False)
    with pytest.raises(ValueError, match="incomplete"):
        _validate_cds_credentials(tmp_path / ".cdsapirc")


def test_validate_cds_valid_file(tmp_path: Path) -> None:
    """No exception when cdsapirc has both url: and key: lines."""
    _write_cdsapirc(tmp_path / ".cdsapirc", complete=True)
    _validate_cds_credentials(tmp_path / ".cdsapirc")  # should not raise


# ---------------------------------------------------------------------------
# Test 4-5: _check_unwrap_quality
# ---------------------------------------------------------------------------


def test_check_unwrap_quality_flagged(tmp_path: Path) -> None:
    """Non-planar noise in GeoTIFF triggers flagged=True."""
    tif = _make_test_unwrapped_tif(tmp_path / "ramp.tif", add_ramp=True)
    result = _check_unwrap_quality(tif, threshold=0.1)
    assert result["flagged"] is True
    assert result["residual_rms"] > 0.1


def test_check_unwrap_quality_clean(tmp_path: Path) -> None:
    """Uniform-phase GeoTIFF is flagged=False with a generous threshold."""
    tif = _make_test_unwrapped_tif(tmp_path / "clean.tif", add_ramp=False)
    result = _check_unwrap_quality(tif, threshold=10.0)
    assert result["flagged"] is False


# ---------------------------------------------------------------------------
# Test 6: _generate_mintpy_template
# ---------------------------------------------------------------------------


def test_generate_mintpy_template(tmp_path: Path) -> None:
    """MintPy template file contains required configuration keys."""
    cfg_path = _generate_mintpy_template(tmp_path, Path.home() / ".cdsapirc")
    assert cfg_path.exists()

    contents = cfg_path.read_text()
    assert "mintpy.load.processor = dolphin" in contents
    assert "mintpy.troposphericDelay.method = pyaps" in contents
    assert "mintpy.troposphericDelay.weatherModel = ERA5" in contents
    assert "mintpy.networkInversion.minTempCoh = 0.7" in contents
    assert "mintpy.timeFunc.polynomial = 1" in contents


# ---------------------------------------------------------------------------
# Test 7: run_disp with mocked deps returns valid result
# ---------------------------------------------------------------------------


def test_run_disp_mocked(tmp_path: Path, mocker: MockerFixture) -> None:
    """Full pipeline with mocked dolphin/tophu/MintPy returns valid DISPResult."""
    cdsapirc = _write_cdsapirc(tmp_path / ".cdsapirc")

    # Create test interferogram and coherence files
    dolphin_dir = tmp_path / "out" / "dolphin"
    ifg_path = _make_test_ifg_tif(dolphin_dir / "ifg_001.tif")
    cor_path = _make_test_cor_tif(dolphin_dir / "cor_001.tif", high_coherence=True)

    # Mock dolphin
    mock_outputs = MagicMock()
    mock_outputs.stitched_ifg_paths = [str(ifg_path)]
    mock_outputs.stitched_cor_paths = [str(cor_path)]

    mock_dolphin_run = MagicMock(return_value=mock_outputs)
    mock_dolphin_config = MagicMock()

    mocker.patch.dict(
        "sys.modules",
        {
            "dolphin": MagicMock(),
            "dolphin.workflows": MagicMock(),
            "dolphin.workflows.config": MagicMock(
                DisplacementWorkflow=mock_dolphin_config,
            ),
            "dolphin.workflows.displacement": MagicMock(run=mock_dolphin_run),
        },
    )

    # Mock tophu: return numpy arrays
    mock_tophu = MagicMock()
    unwrapped_arr = np.ones((20, 20), dtype=np.float32)
    mock_tophu.multiscale_unwrap.return_value = (
        unwrapped_arr,
        np.zeros((20, 20), dtype=np.int32),
    )
    mock_tophu.SnaphuUnwrap.return_value = MagicMock()
    mocker.patch.dict("sys.modules", {"tophu": mock_tophu})

    # Mock MintPy
    mock_app = MagicMock()
    mock_ts_class = MagicMock(return_value=mock_app)

    def _fake_mintpy_run(steps: list[str]) -> None:
        mintpy_dir = tmp_path / "out" / "mintpy"
        mintpy_dir.mkdir(parents=True, exist_ok=True)
        (mintpy_dir / "velocity.h5").touch()
        (mintpy_dir / "timeseries.h5").touch()

    mock_app.run.side_effect = _fake_mintpy_run

    mocker.patch.dict(
        "sys.modules",
        {
            "mintpy": MagicMock(),
            "mintpy.smallbaselineApp": MagicMock(
                TimeSeriesAnalysis=mock_ts_class,
            ),
        },
    )

    # Mock scipy
    mock_scipy = MagicMock()
    mock_scipy_linalg = MagicMock()
    mock_scipy_linalg.lstsq.return_value = (
        np.array([0.0, 0.0, 1.0]),
        np.array([]),
        3,
        np.array([1.0, 1.0, 1.0]),
    )
    mocker.patch.dict(
        "sys.modules",
        {
            "scipy": mock_scipy,
            "scipy.linalg": mock_scipy_linalg,
        },
    )

    result = run_disp(
        cslc_paths=[tmp_path / "cslc.h5"],
        output_dir=tmp_path / "out",
        cdsapirc_path=cdsapirc,
    )

    assert isinstance(result, DISPResult)
    assert result.valid is True
    assert result.velocity_path is not None


# ---------------------------------------------------------------------------
# Test 8: run_disp returns invalid when dolphin ImportError
# ---------------------------------------------------------------------------


def test_run_disp_import_error(tmp_path: Path, mocker: MockerFixture) -> None:
    """ImportError from dolphin yields invalid DISPResult."""
    cdsapirc = _write_cdsapirc(tmp_path / ".cdsapirc")

    mocker.patch(
        "subsideo.products.disp._run_dolphin_phase_linking",
        side_effect=ImportError("No module named 'dolphin'"),
    )

    result = run_disp(
        cslc_paths=[tmp_path / "cslc.h5"],
        output_dir=tmp_path / "out",
        cdsapirc_path=cdsapirc,
    )

    assert result.valid is False
    assert len(result.validation_errors) > 0
    err_lower = result.validation_errors[0].lower()
    assert "not installed" in err_lower or "dolphin" in err_lower


# ---------------------------------------------------------------------------
# Test 9: run_disp returns qc_warnings when ramp QC flags anomaly
# ---------------------------------------------------------------------------


def test_run_disp_qc_warning(tmp_path: Path, mocker: MockerFixture) -> None:
    """Post-unwrap QC ramp detection populates qc_warnings."""
    cdsapirc = _write_cdsapirc(tmp_path / ".cdsapirc")

    dolphin_dir = tmp_path / "out" / "dolphin"
    ifg_path = _make_test_ifg_tif(dolphin_dir / "ifg_001.tif")
    cor_path = _make_test_cor_tif(dolphin_dir / "cor_001.tif", high_coherence=True)

    mocker.patch(
        "subsideo.products.disp._run_dolphin_phase_linking",
        return_value=([ifg_path], [cor_path]),
    )
    mocker.patch(
        "subsideo.products.disp._apply_coherence_mask",
        return_value=[ifg_path],
    )

    # Produce a file with non-planar noise -> high residual
    unwrap_dir = tmp_path / "out" / "unwrap"
    ramp_path = _make_test_unwrapped_tif(unwrap_dir / "ramp.tif", add_ramp=True)
    mocker.patch(
        "subsideo.products.disp._run_unwrapping",
        return_value=[ramp_path],
    )

    mintpy_dir = tmp_path / "out" / "mintpy"
    mintpy_dir.mkdir(parents=True, exist_ok=True)
    (mintpy_dir / "velocity.h5").touch()

    mocker.patch(
        "subsideo.products.disp._generate_mintpy_template",
        return_value=mintpy_dir / "smallbaselineApp.cfg",
    )
    mocker.patch(
        "subsideo.products.disp._run_mintpy_timeseries",
        return_value=[mintpy_dir / "velocity.h5"],
    )

    result = run_disp(
        cslc_paths=[tmp_path / "cslc.h5"],
        output_dir=tmp_path / "out",
        cdsapirc_path=cdsapirc,
        ramp_threshold=0.01,
    )

    assert result.valid is True
    assert len(result.qc_warnings) > 0
    assert "ramp" in result.qc_warnings[0].lower()


# ---------------------------------------------------------------------------
# Test 10: run_disp_from_aoi with mocked Phase 1/2 deps
# ---------------------------------------------------------------------------


def test_run_disp_from_aoi_mocked(tmp_path: Path, mocker: MockerFixture) -> None:
    """AOI entry point builds CSLC stack then calls run_disp."""
    cdsapirc = _write_cdsapirc(tmp_path / ".cdsapirc")

    # Mock burst query (lazy import target: subsideo.burst.frames)
    mock_burst = MagicMock()
    mock_burst.burst_id_jpl = "T001_000001_IW1"
    mocker.patch(
        "subsideo.burst.frames.query_bursts_for_aoi",
        return_value=[mock_burst],
    )

    # Mock CDSEClient (lazy import target: subsideo.data.cdse)
    mock_client_instance = MagicMock()
    mock_client_instance.search_stac.return_value = [
        {
            "assets": {"data": {"href": "s3://eodata/test.zip"}},
            "properties": {
                "datetime": "2025-01-15T00:00:00",
                "platform": "S1A",
            },
        }
    ]

    def _fake_download(
        s3_path: str, output_path: Path, **kwargs: object
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.touch()
        return output_path

    mock_client_instance.download.side_effect = _fake_download
    mock_client_cls = MagicMock(return_value=mock_client_instance)
    mocker.patch("subsideo.data.cdse.CDSEClient", mock_client_cls)

    # Mock fetch_dem
    dem_path = tmp_path / "dem.tif"
    dem_path.touch()
    mocker.patch("subsideo.data.dem.fetch_dem", return_value=dem_path)

    # Mock fetch_orbit
    orbit_path = tmp_path / "orbit.EOF"
    orbit_path.touch()
    mocker.patch("subsideo.data.orbits.fetch_orbit", return_value=orbit_path)

    # Mock run_cslc
    cslc_output = tmp_path / "cslc_001.h5"
    cslc_output.touch()
    mock_cslc_result = MagicMock()
    mock_cslc_result.valid = True
    mock_cslc_result.output_paths = [cslc_output]
    mocker.patch(
        "subsideo.products.cslc.run_cslc",
        return_value=mock_cslc_result,
    )

    # Mock run_disp (the inner call)
    mock_disp_result = DISPResult(
        velocity_path=tmp_path / "velocity.h5",
        timeseries_paths=[],
        output_dir=tmp_path / "out",
        valid=True,
    )
    mock_run_disp = mocker.patch(
        "subsideo.products.disp.run_disp",
        return_value=mock_disp_result,
    )

    aoi = {
        "type": "Polygon",
        "coordinates": [
            [
                [11.0, 48.0],
                [12.0, 48.0],
                [12.0, 49.0],
                [11.0, 49.0],
                [11.0, 48.0],
            ]
        ],
    }

    result = run_disp_from_aoi(
        aoi=aoi,
        date_range=("2025-01-01", "2025-03-01"),
        output_dir=tmp_path / "out",
        cdsapirc_path=cdsapirc,
    )

    # Verify run_disp was called with the CSLC paths from run_cslc
    mock_run_disp.assert_called_once()
    call_args = mock_run_disp.call_args
    actual_cslc_paths = call_args.kwargs.get(
        "cslc_paths", call_args.args[0] if call_args.args else []
    )
    assert cslc_output in actual_cslc_paths

    assert result.valid is True
    assert isinstance(result, DISPResult)
