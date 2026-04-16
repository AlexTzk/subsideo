"""Unit tests for the DIST-S1 validation module.

Generates small synthetic UTM GeoTIFFs and exercises three behaviours:
1. Identical product/reference -> perfect F1 and accuracy.
2. All-zero product/reference -> F1 = 0.0 (no positives), accuracy = 1.0.
3. Shifted-grid product -> reprojection path runs without raising.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin


def _write_dist_raster(
    path: Path,
    data: np.ndarray,
    *,
    epsg: int = 32632,
    origin_x: float = 500000.0,
    origin_y: float = 4900000.0,
    pixel_size: float = 30.0,
) -> Path:
    """Write a single-band uint8 DIST-S1-like raster at the given UTM origin."""
    height, width = data.shape
    transform = from_origin(origin_x, origin_y, pixel_size, pixel_size)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="uint8",
        crs=CRS.from_epsg(epsg),
        transform=transform,
        nodata=255,
    ) as ds:
        ds.write(data.astype(np.uint8), 1)
    return path


# ---------------------------------------------------------------------------
# Test 1: identical product/reference -> perfect metrics
# ---------------------------------------------------------------------------


def test_compare_dist_identical_matches(tmp_path: Path) -> None:
    """Two identical rasters with mixed labels score perfect on every metric."""
    from subsideo.validation.compare_dist import compare_dist

    # 20x20 uint8 raster: top half disturbed (label 5), bottom half clean (0)
    data = np.zeros((20, 20), dtype=np.uint8)
    data[:10, :] = 5  # disturbed high-confidence

    prod = _write_dist_raster(tmp_path / "prod.tif", data)
    ref = _write_dist_raster(tmp_path / "ref.tif", data)

    result = compare_dist(prod, ref)

    assert result.f1 == 1.0
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.overall_accuracy == 1.0
    assert result.n_valid_pixels == 400  # 20 * 20
    assert all(result.pass_criteria.values())
    assert "f1_gt_0.80" in result.pass_criteria
    assert "accuracy_gt_0.85" in result.pass_criteria


# ---------------------------------------------------------------------------
# Test 2: all-zero rasters -> F1 = 0 (no positives), accuracy = 1
# ---------------------------------------------------------------------------


def test_compare_dist_all_zero(tmp_path: Path) -> None:
    """Two all-zero rasters: no positives, zero-division F1 floor kicks in."""
    from subsideo.validation.compare_dist import compare_dist

    data = np.zeros((20, 20), dtype=np.uint8)
    prod = _write_dist_raster(tmp_path / "prod.tif", data)
    ref = _write_dist_raster(tmp_path / "ref.tif", data)

    result = compare_dist(prod, ref)

    assert result.f1 == 0.0
    assert result.overall_accuracy == 1.0
    assert result.n_valid_pixels == 400
    assert result.pass_criteria["f1_gt_0.80"] is False
    assert result.pass_criteria["accuracy_gt_0.85"] is True


# ---------------------------------------------------------------------------
# Test 3: shifted grid -> reprojection code path runs
# ---------------------------------------------------------------------------


def test_compare_dist_shifted_grid(tmp_path: Path) -> None:
    """Product on a grid shifted by 1 pixel: reprojection runs, result is valid."""
    from subsideo.validation.compare_dist import compare_dist

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

    # Reprojection should run without raising; result should be valid.
    result = compare_dist(prod, ref)
    assert result is not None
    assert result.n_valid_pixels > 0
    # Metrics should be finite (not NaN) since n_valid > 100.
    assert np.isfinite(result.f1)
    assert np.isfinite(result.precision)
    assert np.isfinite(result.recall)
    assert np.isfinite(result.overall_accuracy)
