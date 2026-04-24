"""Unit tests for compare_cslc_egms_l2a_residual + _load_egms_l2a_points extension.

Phase 3 D-12: EGMS L2a stable-PS residual computation for CSLC self-consistency
EU validation (Iberian Meseta cell). Tests use in-memory GeoTIFFs via
rasterio.MemoryFile + synthetic CSVs — no network, no conda-forge imports at
module top.
"""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_velocity_geotiff(tmp_path: Path, value: float, width: int = 100, height: int = 100) -> Path:
    """Create a small in-memory velocity GeoTIFF (EPSG:4326) at a known location."""
    import rasterio
    from rasterio.transform import from_bounds

    p = tmp_path / "velocity.tif"
    # bbox: lon -4..−1, lat 39..42 (Iberian Meseta-ish)
    west, south, east, north = -4.0, 39.0, -1.0, 42.0
    transform = from_bounds(west, south, east, north, width, height)
    data = np.full((1, height, width), value, dtype=np.float32)

    with rasterio.open(
        p, "w", driver="GTiff",
        height=height, width=width,
        count=1, dtype="float32",
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data)
    return p


def _make_egms_csv(
    tmp_path: Path,
    n_points: int,
    mean_velocity: float = 1.0,
    mean_velocity_std: float = 0.5,
    lon_range: tuple[float, float] = (-3.5, -1.5),
    lat_range: tuple[float, float] = (39.5, 41.5),
    include_std: bool = True,
    filename: str = "egms_l2a.csv",
) -> Path:
    """Write a synthetic EGMS L2a CSV with uniform values."""
    rng = np.random.default_rng(42)
    lons = rng.uniform(*lon_range, size=n_points)
    lats = rng.uniform(*lat_range, size=n_points)
    d: dict = {
        "longitude": lons,
        "latitude": lats,
        "mean_velocity": np.full(n_points, mean_velocity),
    }
    if include_std:
        d["mean_velocity_std"] = np.full(n_points, mean_velocity_std)
    df = pd.DataFrame(d)
    p = tmp_path / filename
    df.to_csv(p, index=False)
    return p


# ---------------------------------------------------------------------------
# Test 1: happy path — residual ~ 0.0 (after reference-frame alignment)
# ---------------------------------------------------------------------------

def test_compare_cslc_egms_l2a_residual_happy_path(tmp_path: Path) -> None:
    """Synthetic 200-point stable PS; our velocity = 1.5, EGMS = 1.0.

    After reference-frame alignment (subtract median of our sampled = 1.5),
    our_aligned = 0.0 everywhere. EGMS = 1.0. Paired residual = mean(|0-1|) = 1.0.

    Wait — re-read D-12: subtract stable-set median of OUR values, then
    compare |our_aligned - egms_velocity|. With our=1.5, egms=1.0:
    our_aligned = 1.5 - 1.5 = 0.0; residual = mean(|0 - 1.0|) = 1.0.

    For residual ~ 0.0 we need our_aligned ≈ egms_velocity:
    Choose our=1.5 velocity raster, EGMS=0.0 mean_velocity.
    After align: our_aligned = 1.5 - 1.5 = 0.0; |0 - 0| = 0.0.
    """
    from subsideo.validation.compare_cslc import compare_cslc_egms_l2a_residual

    vel_tif = _make_velocity_geotiff(tmp_path, value=1.5)
    csv_path = _make_egms_csv(
        tmp_path, n_points=200, mean_velocity=0.0, mean_velocity_std=0.5,
    )
    result = compare_cslc_egms_l2a_residual(vel_tif, [csv_path])
    assert isinstance(result, float)
    assert np.isfinite(result)
    assert abs(result) < 0.1  # reference-frame aligned; EGMS=0.0, our_aligned=0.0


# ---------------------------------------------------------------------------
# Test 2: stable-PS filter — only points with std < threshold pass
# ---------------------------------------------------------------------------

def test_stable_ps_filter_by_mean_velocity_std(tmp_path: Path) -> None:
    """200 PS points: 100 with std=0.5 (stable), 100 with std=3.0 (unstable).

    The function should only use the 100 stable points.
    """
    from subsideo.validation.compare_cslc import compare_cslc_egms_l2a_residual

    vel_tif = _make_velocity_geotiff(tmp_path, value=1.5)

    # Stable 100 points
    stable_csv = _make_egms_csv(
        tmp_path, n_points=100, mean_velocity=0.0, mean_velocity_std=0.5, filename="stable.csv"
    )
    # Unstable 100 points — would corrupt residual if included (large mean_velocity)
    unstable_csv = _make_egms_csv(
        tmp_path, n_points=100, mean_velocity=50.0, mean_velocity_std=3.0, filename="unstable.csv"
    )

    result = compare_cslc_egms_l2a_residual(
        vel_tif, [stable_csv, unstable_csv], stable_std_max=2.0
    )
    # If unstable points were included, residual >> 10 mm/yr (EGMS=50 mm/yr).
    # If only stable points: our_aligned=0, EGMS=0 → residual ~ 0.
    assert isinstance(result, float)
    assert np.isfinite(result)
    assert abs(result) < 1.0  # stable-PS-only residual is small


# ---------------------------------------------------------------------------
# Test 3: n_valid < 100 returns NaN
# ---------------------------------------------------------------------------

def test_returns_nan_when_too_few_valid_points(tmp_path: Path) -> None:
    """Only 30 stable PS within raster bounds → NaN (min_valid_points=100)."""
    from subsideo.validation.compare_cslc import compare_cslc_egms_l2a_residual

    vel_tif = _make_velocity_geotiff(tmp_path, value=1.5)
    # Write 30 points that are all inside bounds
    csv_path = _make_egms_csv(
        tmp_path, n_points=30, mean_velocity=0.0, mean_velocity_std=0.5
    )
    result = compare_cslc_egms_l2a_residual(vel_tif, [csv_path], min_valid_points=100)
    assert isinstance(result, float)
    assert not np.isfinite(result)  # NaN expected


# ---------------------------------------------------------------------------
# Test 4: _load_egms_l2a_points — extended column backward compatibility
# ---------------------------------------------------------------------------

def test_load_egms_l2a_points_with_mean_velocity_std(tmp_path: Path) -> None:
    """CSV with mean_velocity_std → returned DataFrame includes it."""
    from subsideo.validation.compare_disp import _load_egms_l2a_points

    csv_path = _make_egms_csv(tmp_path, n_points=50, include_std=True, filename="with_std.csv")
    df = _load_egms_l2a_points([csv_path])
    assert "mean_velocity_std" in df.columns
    assert "lon" in df.columns
    assert "lat" in df.columns
    assert "mean_velocity" in df.columns


def test_load_egms_l2a_points_without_mean_velocity_std(tmp_path: Path) -> None:
    """CSV WITHOUT mean_velocity_std → returned DataFrame has only minimal columns."""
    from subsideo.validation.compare_disp import _load_egms_l2a_points

    csv_path = _make_egms_csv(
        tmp_path, n_points=50, include_std=False, filename="no_std.csv"
    )
    df = _load_egms_l2a_points([csv_path])
    assert "mean_velocity_std" not in df.columns
    assert "lon" in df.columns
    assert "mean_velocity" in df.columns


# ---------------------------------------------------------------------------
# Test 5: cross-module import discipline — compare_disp NOT imported at module top
# ---------------------------------------------------------------------------

def test_cross_module_import_is_function_body_local() -> None:
    """compare_disp must NOT be imported at compare_cslc module top.

    Importing compare_cslc alone must not pull compare_disp into sys.modules
    before the function is called. This verifies PATTERNS D-12 constraint.
    """
    import sys

    # Remove compare_disp from sys.modules if already there from a prior test
    for key in list(sys.modules.keys()):
        if "compare_disp" in key:
            del sys.modules[key]

    # Now import compare_cslc fresh
    for key in list(sys.modules.keys()):
        if "compare_cslc" in key:
            del sys.modules[key]

    import subsideo.validation.compare_cslc  # noqa: F401

    # compare_disp should NOT be in sys.modules yet (not eagerly imported)
    assert not any("compare_disp" in k for k in sys.modules), (
        "compare_disp was eagerly imported at module top of compare_cslc — "
        "violates PATTERNS D-12 cross-module import discipline. "
        "The import must live inside compare_cslc_egms_l2a_residual function body."
    )
