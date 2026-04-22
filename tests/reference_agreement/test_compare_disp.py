"""Plumbing tests for DISP-S1 comparison: shape + criterion_id wiring.

Per GATE-04: NO numeric-literal threshold assertions. See conftest.py
AST linter.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds

from subsideo.products.types import DISPValidationResult
from subsideo.validation.compare_disp import compare_disp
from subsideo.validation.results import ProductQualityResult, ReferenceAgreementResult

pytestmark = pytest.mark.reference_agreement


def _make_velocity_tif(path: Path, data: np.ndarray) -> Path:
    rows, cols = data.shape
    transform = from_bounds(0, 0, float(cols), float(rows), cols, rows)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=rows,
        width=cols,
        count=1,
        dtype="float64",
        crs=CRS.from_epsg(32632),
        transform=transform,
    ) as dst:
        dst.write(data, 1)
    return path


def test_returns_composite_shape(tmp_path: Path) -> None:
    """compare_disp returns the nested composite ValidationResult."""
    rng = np.random.default_rng(42)
    data = rng.uniform(1.0, 10.0, (100, 100))
    prod = _make_velocity_tif(tmp_path / "product.tif", data)
    ref = _make_velocity_tif(tmp_path / "reference.tif", data)

    result = compare_disp(prod, ref, mean_incidence_deg=0.0)

    assert isinstance(result, DISPValidationResult)
    assert isinstance(result.product_quality, ProductQualityResult)
    assert isinstance(result.reference_agreement, ReferenceAgreementResult)


def test_criterion_ids_wired(tmp_path: Path) -> None:
    """Criterion IDs populated so evaluate() does not KeyError."""
    rng = np.random.default_rng(42)
    data = rng.uniform(1.0, 10.0, (100, 100))
    prod = _make_velocity_tif(tmp_path / "product.tif", data)
    ref = _make_velocity_tif(tmp_path / "reference.tif", data)

    result = compare_disp(prod, ref, mean_incidence_deg=0.0)
    ra_ids = result.reference_agreement.criterion_ids
    assert "disp.correlation_min" in ra_ids
    assert "disp.bias_mm_yr_max" in ra_ids


def test_partial_overlap_masks_nans(tmp_path: Path) -> None:
    """Metrics should be finite when reference has NaN in half the frame."""
    rng = np.random.default_rng(42)
    data = rng.uniform(1.0, 10.0, (100, 100))

    # Reference has NaN in top half
    ref_data = data.copy()
    ref_data[:50, :] = np.nan

    prod = _make_velocity_tif(tmp_path / "product.tif", data)
    ref = _make_velocity_tif(tmp_path / "reference.tif", ref_data)

    result = compare_disp(prod, ref, mean_incidence_deg=0.0)

    ra = result.reference_agreement
    assert np.isfinite(ra.measurements["correlation"])
    assert np.isfinite(ra.measurements["bias_mm_yr"])
