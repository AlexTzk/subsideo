"""Product-quality tests for DIST-S1 comparison: value + criterion-pass assertions."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

from subsideo.validation.compare_dist import compare_dist
from subsideo.validation.results import evaluate


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


def test_compare_dist_identical_matches(tmp_path: Path) -> None:
    """Two identical rasters with mixed labels score perfect on every metric."""
    # 20x20 uint8 raster: top half disturbed (label 5), bottom half clean (0)
    data = np.zeros((20, 20), dtype=np.uint8)
    data[:10, :] = 5  # disturbed high-confidence

    prod = _write_dist_raster(tmp_path / "prod.tif", data)
    ref = _write_dist_raster(tmp_path / "ref.tif", data)

    result = compare_dist(prod, ref)

    ra = result.reference_agreement
    assert ra.measurements["f1"] == 1.0
    assert ra.measurements["precision"] == 1.0
    assert ra.measurements["recall"] == 1.0
    assert ra.measurements["accuracy"] == 1.0
    assert ra.measurements["n_valid_pixels"] == 400.0  # 20 * 20

    passed = evaluate(ra)
    assert all(passed.values())
    assert "dist.f1_min" in passed
    assert "dist.accuracy_min" in passed


def test_compare_dist_all_zero(tmp_path: Path) -> None:
    """Two all-zero rasters: no positives, zero-division F1 floor kicks in."""
    data = np.zeros((20, 20), dtype=np.uint8)
    prod = _write_dist_raster(tmp_path / "prod.tif", data)
    ref = _write_dist_raster(tmp_path / "ref.tif", data)

    result = compare_dist(prod, ref)

    ra = result.reference_agreement
    assert ra.measurements["f1"] == 0.0
    assert ra.measurements["accuracy"] == 1.0
    assert ra.measurements["n_valid_pixels"] == 400.0

    passed = evaluate(ra)
    assert passed["dist.f1_min"] is False
    assert passed["dist.accuracy_min"] is True
