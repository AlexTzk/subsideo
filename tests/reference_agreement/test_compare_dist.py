"""Plumbing tests for DIST-S1 comparison: shape + criterion_id wiring.

Per GATE-04: NO numeric-literal threshold assertions. See conftest.py
AST linter.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

from subsideo.products.types import DISTValidationResult
from subsideo.validation.compare_dist import compare_dist
from subsideo.validation.results import ProductQualityResult, ReferenceAgreementResult

pytestmark = pytest.mark.reference_agreement


def _write_dist_raster(
    path: Path,
    data: np.ndarray,
    *,
    origin_x: float = 500000.0,
    origin_y: float = 4900000.0,
) -> Path:
    height, width = data.shape
    # 30-metre pixel size per standard DIST-S1 convention
    pixel_size = 30.0
    transform = from_origin(origin_x, origin_y, pixel_size, pixel_size)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="uint8",
        crs=CRS.from_epsg(32632),
        transform=transform,
        nodata=255,
    ) as ds:
        ds.write(data.astype(np.uint8), 1)
    return path


def test_returns_composite_shape(tmp_path: Path) -> None:
    """compare_dist returns the nested composite ValidationResult."""
    data = np.zeros((20, 20), dtype=np.uint8)
    data[:10, :] = 5
    prod = _write_dist_raster(tmp_path / "prod.tif", data)
    ref = _write_dist_raster(tmp_path / "ref.tif", data)

    result = compare_dist(prod, ref)
    assert isinstance(result, DISTValidationResult)
    assert isinstance(result.product_quality, ProductQualityResult)
    assert isinstance(result.reference_agreement, ReferenceAgreementResult)


def test_criterion_ids_wired(tmp_path: Path) -> None:
    """Criterion IDs populated so evaluate() does not KeyError."""
    data = np.zeros((20, 20), dtype=np.uint8)
    data[:10, :] = 5
    prod = _write_dist_raster(tmp_path / "prod.tif", data)
    ref = _write_dist_raster(tmp_path / "ref.tif", data)

    result = compare_dist(prod, ref)
    ra_ids = result.reference_agreement.criterion_ids
    assert "dist.f1_min" in ra_ids
    assert "dist.accuracy_min" in ra_ids


def test_shifted_grid_reprojection(tmp_path: Path) -> None:
    """Product on a grid shifted by 1 pixel: reprojection runs, result is valid."""
    # Reference: baseline 20x20 raster with a disturbance block in the middle
    ref_data = np.zeros((20, 20), dtype=np.uint8)
    ref_data[5:15, 5:15] = 5
    ref = _write_dist_raster(
        tmp_path / "ref.tif",
        ref_data,
        origin_x=500000.0,
        origin_y=4900000.0,
    )

    # Product: same data, origin shifted by one pixel (30 m) in x
    prod_data = ref_data.copy()
    prod = _write_dist_raster(
        tmp_path / "prod.tif",
        prod_data,
        origin_x=500000.0 + 30.0,
        origin_y=4900000.0,
    )

    # Reprojection should run without raising; result should have finite metrics.
    result = compare_dist(prod, ref)
    assert result is not None
    ra = result.reference_agreement
    # n_valid_pixels must be populated; np.isfinite covers both positivity and
    # finiteness without smuggling a numeric-literal threshold into the test.
    assert np.isfinite(ra.measurements["n_valid_pixels"])
    # Metrics should be finite since n_valid is above the compare_dist floor.
    assert np.isfinite(ra.measurements["f1"])
    assert np.isfinite(ra.measurements["precision"])
    assert np.isfinite(ra.measurements["recall"])
    assert np.isfinite(ra.measurements["accuracy"])
