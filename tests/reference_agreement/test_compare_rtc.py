"""Plumbing tests for RTC-S1 comparison: shape + criterion_id wiring only.

Per GATE-04: NO numeric-literal threshold assertions. See the conftest.py
AST linter in this directory for enforcement.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds

from subsideo.products.types import RTCValidationResult
from subsideo.validation.compare_rtc import compare_rtc
from subsideo.validation.results import ProductQualityResult, ReferenceAgreementResult

pytestmark = pytest.mark.reference_agreement


def _make_rtc_geotiff(
    path: Path, data: np.ndarray, epsg: int = 32632, pixel_size: float = 30.0
) -> Path:
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


def test_returns_composite_shape(tmp_path: Path) -> None:
    """compare_rtc returns the nested composite ValidationResult."""
    rng = np.random.default_rng(42)
    data = rng.uniform(0.01, 1.0, (100, 100))
    prod = _make_rtc_geotiff(tmp_path / "product.tif", data)
    ref = _make_rtc_geotiff(tmp_path / "reference.tif", data)

    result = compare_rtc(prod, ref)

    assert isinstance(result, RTCValidationResult)
    assert isinstance(result.product_quality, ProductQualityResult)
    assert isinstance(result.reference_agreement, ReferenceAgreementResult)


def test_criterion_ids_wired(tmp_path: Path) -> None:
    """Criterion IDs must be populated so evaluate() does not KeyError."""
    rng = np.random.default_rng(42)
    data = rng.uniform(0.01, 1.0, (100, 100))
    prod = _make_rtc_geotiff(tmp_path / "product.tif", data)
    ref = _make_rtc_geotiff(tmp_path / "reference.tif", data)

    result = compare_rtc(prod, ref)
    ra_ids = result.reference_agreement.criterion_ids
    assert "rtc.rmse_db_max" in ra_ids
    assert "rtc.correlation_min" in ra_ids


def test_handles_zero_pixels(tmp_path: Path) -> None:
    """Zero pixels should be masked via NaN in log10, not cause inf/nan results."""
    rng = np.random.default_rng(42)
    data = rng.uniform(0.01, 1.0, (100, 100))
    data[0:10, 0:10] = 0.0  # nodata region

    prod = _make_rtc_geotiff(tmp_path / "product.tif", data)
    ref = _make_rtc_geotiff(tmp_path / "reference.tif", data)

    result = compare_rtc(prod, ref)
    ra = result.reference_agreement
    assert np.isfinite(ra.measurements["rmse_db"])
    assert np.isfinite(ra.measurements["correlation"])
    assert np.isfinite(ra.measurements["bias_db"])
    assert np.isfinite(result.product_quality.measurements["ssim"])
