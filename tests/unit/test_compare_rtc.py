"""Unit tests for RTC-S1 comparison module using synthetic arrays."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds

from subsideo.validation.compare_rtc import compare_rtc


def _make_rtc_geotiff(
    path: Path, data: np.ndarray, epsg: int = 32632, pixel_size: float = 30.0
) -> Path:
    """Write a minimal GeoTIFF with given 2-D float32 array."""
    rows, cols = data.shape
    transform = from_bounds(0, 0, pixel_size * cols, pixel_size * rows, cols, rows)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=rows,
        width=cols,
        count=1,
        dtype="float32",
        crs=CRS.from_epsg(epsg),
        transform=transform,
    ) as dst:
        dst.write(data.astype(np.float32), 1)
    return path


def test_compare_rtc_identical(tmp_path: Path) -> None:
    """Identical products should yield zero RMSE, perfect correlation."""
    rng = np.random.default_rng(42)
    data = rng.uniform(0.01, 1.0, (100, 100))

    prod = _make_rtc_geotiff(tmp_path / "product.tif", data)
    ref = _make_rtc_geotiff(tmp_path / "reference.tif", data)

    result = compare_rtc(prod, ref)

    assert result.rmse_db == pytest.approx(0.0, abs=1e-6)
    assert result.correlation == pytest.approx(1.0, abs=1e-6)
    assert result.bias_db == pytest.approx(0.0, abs=1e-6)
    assert result.pass_criteria["rmse_lt_0.5dB"] is True
    assert result.pass_criteria["correlation_gt_0.99"] is True


def test_compare_rtc_with_offset(tmp_path: Path) -> None:
    """10% gain offset should produce nonzero RMSE but high correlation."""
    rng = np.random.default_rng(42)
    ref_data = rng.uniform(0.01, 1.0, (100, 100))
    prod_data = ref_data * 1.1  # 10% gain

    prod = _make_rtc_geotiff(tmp_path / "product.tif", prod_data)
    ref = _make_rtc_geotiff(tmp_path / "reference.tif", ref_data)

    result = compare_rtc(prod, ref)

    assert result.rmse_db > 0.0
    # Linear scaling preserves correlation in dB domain
    assert result.correlation > 0.99


def test_compare_rtc_handles_zeros(tmp_path: Path) -> None:
    """Zero pixels should be masked via NaN in log10, not cause inf/nan results."""
    rng = np.random.default_rng(42)
    data = rng.uniform(0.01, 1.0, (100, 100))
    data[0:10, 0:10] = 0.0  # nodata region

    prod = _make_rtc_geotiff(tmp_path / "product.tif", data)
    ref = _make_rtc_geotiff(tmp_path / "reference.tif", data)

    result = compare_rtc(prod, ref)

    assert np.isfinite(result.rmse_db)
    assert np.isfinite(result.correlation)
    assert np.isfinite(result.bias_db)
    assert np.isfinite(result.ssim_value)
