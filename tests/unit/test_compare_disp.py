"""Unit tests for DISP-S1 EGMS comparison module using synthetic arrays."""
from __future__ import annotations

from pathlib import Path
from math import cos, radians

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds

from subsideo.validation.compare_disp import (
    _los_to_vertical,
    compare_disp,
    fetch_egms_ortho,
)


def _make_velocity_tif(
    path: Path, data: np.ndarray, *, epsg: int = 32632, pixel_size: float = 30.0
) -> Path:
    """Write a minimal GeoTIFF with given 2-D float64 array."""
    rows, cols = data.shape
    transform = from_bounds(0, 0, pixel_size * cols, pixel_size * rows, cols, rows)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=rows,
        width=cols,
        count=1,
        dtype="float64",
        crs=CRS.from_epsg(epsg),
        transform=transform,
    ) as dst:
        dst.write(data, 1)
    return path


# --- LOS-to-vertical tests ---


def test_los_to_vertical_scalar() -> None:
    """Scalar incidence angle correctly divides by cos(theta)."""
    arr = np.full((5, 5), 10.0)
    result = _los_to_vertical(arr, 33.0)
    expected = 10.0 / cos(radians(33.0))
    assert np.allclose(result, expected, atol=0.01)


def test_los_to_vertical_array() -> None:
    """Per-pixel incidence angle array handles row-wise projection."""
    los = np.full((3, 3), 5.0)
    # Broadcast angles per row: 30, 33, 36 degrees
    angles = np.array([[30.0] * 3, [33.0] * 3, [36.0] * 3])
    result = _los_to_vertical(los, angles)

    assert np.allclose(result[0], 5.0 / cos(radians(30.0)), atol=0.01)
    assert np.allclose(result[1], 5.0 / cos(radians(33.0)), atol=0.01)
    assert np.allclose(result[2], 5.0 / cos(radians(36.0)), atol=0.01)


# --- compare_disp tests ---


def test_compare_disp_identical(tmp_path: Path) -> None:
    """Identical products should yield r~1.0 and bias~0.0."""
    rng = np.random.default_rng(42)
    data = rng.uniform(1.0, 10.0, (100, 100))

    prod = _make_velocity_tif(tmp_path / "product.tif", data)
    ref = _make_velocity_tif(tmp_path / "reference.tif", data)

    # mean_incidence_deg=0 means LOS == vertical (cos(0)=1)
    result = compare_disp(prod, ref, mean_incidence_deg=0.0)

    assert result.correlation > 0.99
    assert abs(result.bias_mm_yr) < 0.01


def test_compare_disp_known_bias(tmp_path: Path) -> None:
    """Constant 2 mm/yr bias should be detected."""
    rng = np.random.default_rng(42)
    ref_data = rng.uniform(0.0, 10.0, (100, 100))
    prod_data = ref_data + 2.0

    prod = _make_velocity_tif(tmp_path / "product.tif", prod_data)
    ref = _make_velocity_tif(tmp_path / "reference.tif", ref_data)

    result = compare_disp(prod, ref, mean_incidence_deg=0.0)

    assert abs(result.bias_mm_yr - 2.0) < 0.1


def test_compare_disp_partial_overlap(tmp_path: Path) -> None:
    """Metrics computed over intersection only when reference has NaN."""
    rng = np.random.default_rng(42)
    data = rng.uniform(1.0, 10.0, (100, 100))

    # Reference has NaN in top half
    ref_data = data.copy()
    ref_data[:50, :] = np.nan

    prod = _make_velocity_tif(tmp_path / "product.tif", data)
    ref = _make_velocity_tif(tmp_path / "reference.tif", ref_data)

    result = compare_disp(prod, ref, mean_incidence_deg=0.0)

    assert np.isfinite(result.correlation)
    assert np.isfinite(result.bias_mm_yr)


def test_compare_disp_pass_criteria(tmp_path: Path) -> None:
    """Pass criteria keys reflect thresholds correctly for good data."""
    rng = np.random.default_rng(42)
    data = rng.uniform(1.0, 10.0, (100, 100))
    # Tiny noise to avoid degenerate case
    prod_data = data + rng.normal(0, 0.001, data.shape)

    prod = _make_velocity_tif(tmp_path / "product.tif", prod_data)
    ref = _make_velocity_tif(tmp_path / "reference.tif", data)

    result = compare_disp(prod, ref, mean_incidence_deg=0.0)

    assert "correlation_gt_0.92" in result.pass_criteria
    assert "bias_lt_3mm_yr" in result.pass_criteria
    assert result.pass_criteria["correlation_gt_0.92"] is True
    assert result.pass_criteria["bias_lt_3mm_yr"] is True


# --- fetch_egms_ortho tests ---


def test_fetch_egms_ortho_import_error(tmp_path: Path, mocker) -> None:
    """Raises ImportError with helpful message when EGMStoolkit is missing."""
    mocker.patch.dict("sys.modules", {"EGMStoolkit": None})

    with pytest.raises(ImportError, match="EGMStoolkit"):
        fetch_egms_ortho(bbox=(11.0, 48.0, 12.0, 49.0), output_dir=tmp_path)


def test_fetch_egms_ortho_mocked(tmp_path: Path, mocker) -> None:
    """Mocked EGMStoolkit download returns downloaded file path."""
    import types

    mock_module = types.ModuleType("EGMStoolkit")

    output_dir = tmp_path / "egms"

    def mock_download(*, bbox, product_level, output_dir):
        """Create a dummy GeoTIFF to simulate download."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        data = np.ones((10, 10))
        _make_velocity_tif(out / "egms_ortho.tif", data)

    mock_module.download = mock_download
    mocker.patch.dict("sys.modules", {"EGMStoolkit": mock_module})

    result = fetch_egms_ortho(bbox=(11.0, 48.0, 12.0, 49.0), output_dir=output_dir)

    assert result.exists()
    assert result.suffix == ".tif"
