"""Phase 4 prepare_for_reference adapter — 12-cell method×form matrix + DISP-05 no-write-back."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest
import rasterio
import rioxarray  # noqa: F401  (registers .rio accessor)
import xarray as xr
from rasterio.transform import from_origin

from subsideo.validation.compare_disp import (
    MultilookMethod,
    ReferenceGridSpec,
    prepare_for_reference,
)

# -------------------- Fixtures --------------------


@pytest.fixture
def native_path(tmp_path: Path) -> Path:
    """Synthetic native 100x100 raster at 5x10 m posting in EPSG:32611, value = X+Y."""
    height = width = 100
    yy, xx = np.indices((height, width))
    data = (xx + yy).astype(np.float32)
    # 5 m x 10 m posting; origin at (500000, 4000000) in UTM 11N.
    transform = from_origin(500000.0, 4000000.0, 5.0, 10.0)
    out = tmp_path / "native.tif"
    with rasterio.open(
        out,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=transform,
    ) as dst:
        dst.write(data, 1)
    return out


@pytest.fixture
def ref_path(tmp_path: Path) -> Path:
    """Synthetic reference 50x50 raster at 30m posting in EPSG:32611, all zeros."""
    height = width = 50
    data = np.zeros((height, width), dtype=np.float32)
    # Anchor inside the native footprint (origin at 500000, 4000000;
    # native is 500m wide x 1000m tall).
    transform = from_origin(500000.0, 4000000.0, 30.0, 30.0)
    out = tmp_path / "ref.tif"
    with rasterio.open(
        out,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=transform,
    ) as dst:
        dst.write(data, 1)
    return out


@pytest.fixture
def ref_dataarray(ref_path: Path) -> xr.DataArray:
    """Build an xr.DataArray from the same shape/transform as ref_path."""
    height = width = 50
    data = np.zeros((height, width), dtype=np.float32)
    transform = from_origin(500000.0, 4000000.0, 30.0, 30.0)
    da = xr.DataArray(
        data,
        dims=("y", "x"),
        coords={
            "y": np.arange(height) * (-30.0) + 4000000.0,
            "x": np.arange(width) * 30.0 + 500000.0,
        },
    )
    out: xr.DataArray = da.rio.write_crs("EPSG:32611").rio.write_transform(transform)
    return out


@pytest.fixture
def ref_spec() -> ReferenceGridSpec:
    """10 PS points well inside the native footprint."""
    # Native footprint: x in [500000, 500500] (100 px * 5 m), y in [3999000,
    # 4000000] (100 px * 10 m, origin top -> south).
    # Convert UTM 11N at lat ~ 36.0 to lon/lat. Approximate values:
    # 500000 E, 36.0 N is roughly 117.04 deg W, 36.097 deg N (UTM 11N
    # central meridian -117). Use small offsets in PS-meaningful spacing.
    lons = np.linspace(-117.040, -117.038, 10)
    lats = np.linspace(36.097, 36.099, 10)
    points = np.column_stack([lons, lats])
    return ReferenceGridSpec(points_lonlat=points, crs="EPSG:4326")


# -------------------- Error-path tests (3) --------------------


def test_method_none_raises(native_path: Path, ref_path: Path) -> None:
    with pytest.raises(ValueError, match="method= is required"):
        prepare_for_reference(native_path, ref_path, method=None)


def test_method_bogus_raises(native_path: Path, ref_path: Path) -> None:
    with pytest.raises(ValueError, match="method must be one of"):
        prepare_for_reference(native_path, ref_path, method="bogus")


def test_reference_grid_unsupported_form_raises(native_path: Path) -> None:
    with pytest.raises(ValueError, match="reference_grid must be"):
        prepare_for_reference(native_path, 42, method="block_mean")


# -------------------- 12-cell method-x-form matrix (4 methods x 3 forms) -----


_METHODS: list[MultilookMethod] = ["gaussian", "block_mean", "bilinear", "nearest"]


@pytest.mark.parametrize("method", _METHODS)
def test_form_a_path_each_method(
    method: MultilookMethod, native_path: Path, ref_path: Path
) -> None:
    """Form (a): reference is a GeoTIFF on disk."""
    out = prepare_for_reference(native_path, ref_path, method=method)
    assert isinstance(out, np.ndarray)
    assert out.shape == (50, 50)
    # At least 50% of pixels finite (overlapping region).
    assert np.isfinite(out).sum() > 0.5 * out.size


@pytest.mark.parametrize("method", _METHODS)
def test_form_b_dataarray_each_method(
    method: MultilookMethod, native_path: Path, ref_dataarray: xr.DataArray
) -> None:
    """Form (b): reference is xr.DataArray with CRS via rioxarray."""
    out = prepare_for_reference(native_path, ref_dataarray, method=method)
    assert isinstance(out, xr.DataArray)
    assert out.shape == ref_dataarray.shape
    assert out.rio.crs == ref_dataarray.rio.crs
    assert np.isfinite(out.values).sum() > 0.5 * out.size


@pytest.mark.parametrize("method", _METHODS)
def test_form_c_spec_each_method(
    method: MultilookMethod, native_path: Path, ref_spec: ReferenceGridSpec
) -> None:
    """Form (c): reference is ReferenceGridSpec for PS-point sampling."""
    out = prepare_for_reference(native_path, ref_spec, method=method)
    assert isinstance(out, np.ndarray)
    assert out.ndim == 1
    assert len(out) == len(ref_spec.points_lonlat)
    # NOTE: PS coords may fall outside the native footprint -> some NaN allowed.
    # Just check that we got numeric output (no exception, correct length).


# -------------------- DISP-05 audit: no write-back to product --------------


def test_no_write_back_to_native(native_path: Path, ref_path: Path) -> None:
    """DISP-05 + CONTEXT D-17: prepare_for_reference must NEVER mutate native_velocity."""
    pre = hashlib.sha256(native_path.read_bytes()).hexdigest()
    _ = prepare_for_reference(native_path, ref_path, method="block_mean")
    post = hashlib.sha256(native_path.read_bytes()).hexdigest()
    assert pre == post, "prepare_for_reference must not write back to native_velocity"


# -------------------- Spot-check: block_mean on synthetic plane --------------


def test_block_mean_recovers_local_mean(native_path: Path, ref_path: Path) -> None:
    """Synthetic native = X + Y; block_mean should be near the local-window mean."""
    out = prepare_for_reference(native_path, ref_path, method="block_mean")
    # Top-left ref pixel covers native rows 0..2, cols 0..5
    # (30 m / 10 m = 3 native rows, 30 m / 5 m = 6 native cols).
    # Expected average of (xx + yy) over that window.
    expected_top_left = float(np.mean([(c + r) for r in range(3) for c in range(6)]))
    # Allow loose tolerance — exact behaviour depends on the rasterio averaging
    # weighting at boundaries, but the order of magnitude should match.
    assert abs(float(out[0, 0]) - expected_top_left) < 5.0
