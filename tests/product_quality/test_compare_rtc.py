"""Product-quality tests for RTC-S1 comparison: value assertions."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds

from subsideo.validation.compare_rtc import compare_rtc
from subsideo.validation.results import evaluate


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

    ra = result.reference_agreement
    assert ra.measurements["rmse_db"] == pytest.approx(0.0, abs=1e-6)
    assert ra.measurements["correlation"] == pytest.approx(1.0, abs=1e-6)
    assert ra.measurements["bias_db"] == pytest.approx(0.0, abs=1e-6)
    passed = evaluate(ra)
    assert passed["rtc.rmse_db_max"] is True
    assert passed["rtc.correlation_min"] is True


def test_compare_rtc_with_offset(tmp_path: Path) -> None:
    """10% gain offset should produce nonzero RMSE but high correlation."""
    rng = np.random.default_rng(42)
    ref_data = rng.uniform(0.01, 1.0, (100, 100))
    prod_data = ref_data * 1.1  # 10% gain

    prod = _make_rtc_geotiff(tmp_path / "product.tif", prod_data)
    ref = _make_rtc_geotiff(tmp_path / "reference.tif", ref_data)

    result = compare_rtc(prod, ref)

    ra = result.reference_agreement
    assert ra.measurements["rmse_db"] > 0.0
    # Linear scaling preserves correlation in dB domain
    assert ra.measurements["correlation"] > 0.99
