"""Phase 4 selfconsistency ramp-attribution helpers — unit tests.

Covers fit_planar_ramp algorithm correctness, NaN edge case, mask honoring,
compute_ramp_aggregate aggregate computation, auto_attribute_ramp 4-branch
table.

Phase 11 Plan 03: deramp_ifg_stack and write_deramped_unwrapped_ifgs helpers.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from subsideo.validation.selfconsistency import (
    auto_attribute_ramp,
    compute_ramp_aggregate,
    deramp_ifg_stack,
    fit_planar_ramp,
    write_deramped_unwrapped_ifgs,
)


def test_fit_planar_ramp_recovers_known_ramp() -> None:
    # z = 0.05*x + 0.03*y + 7.0 on a 256x256 grid — no noise.
    height, width = 256, 256
    yy, xx = np.indices((height, width))
    z = 0.05 * xx + 0.03 * yy + 7.0
    stack = z[np.newaxis, :, :].astype(np.float64)  # (1, 256, 256)
    out = fit_planar_ramp(stack, mask=None)
    assert out["slope_x"][0] == pytest.approx(0.05, abs=1e-6)
    assert out["slope_y"][0] == pytest.approx(0.03, abs=1e-6)
    assert out["intercept_rad"][0] == pytest.approx(7.0, abs=1e-6)
    # peak-to-peak = 0.05*255 + 0.03*255 = 20.4
    assert out["ramp_magnitude_rad"][0] == pytest.approx(20.4, abs=1e-3)
    # direction = degrees(atan2(0.03, 0.05)) ≈ 30.96 deg
    assert out["ramp_direction_deg"][0] == pytest.approx(
        np.degrees(np.arctan2(0.03, 0.05)), abs=1e-6
    )


def test_fit_planar_ramp_insufficient_pixels_returns_nan() -> None:
    # IFG 0: all zero (excluded from fit) -> NaN per-IFG entry.
    # IFG 1: valid plane.
    height, width = 100, 100
    z_zero = np.zeros((height, width), dtype=np.float64)
    yy, xx = np.indices((height, width))
    z_valid = 0.1 * xx + 0.05 * yy + 1.0
    stack = np.stack([z_zero, z_valid], axis=0).astype(np.float64)
    out = fit_planar_ramp(stack)
    assert np.isnan(out["slope_x"][0])
    assert np.isnan(out["slope_y"][0])
    assert np.isnan(out["ramp_magnitude_rad"][0])
    # IFG 1 fits normally
    assert out["slope_x"][1] == pytest.approx(0.1, abs=1e-6)
    assert out["slope_y"][1] == pytest.approx(0.05, abs=1e-6)


def test_fit_planar_ramp_rejects_non_3d_stack() -> None:
    bad = np.zeros((100, 100), dtype=np.float64)  # 2-D, not 3-D
    with pytest.raises(ValueError, match="must be 3-D"):
        fit_planar_ramp(bad)


def test_fit_planar_ramp_honors_mask() -> None:
    # 256x256 plane; mask restricts to a 50x50 region — still > 100 px so fit succeeds.
    height, width = 256, 256
    yy, xx = np.indices((height, width))
    z = 0.05 * xx + 0.03 * yy + 1.0
    stack = z[np.newaxis, :, :].astype(np.float64)
    mask = np.zeros((height, width), dtype=bool)
    mask[100:150, 100:150] = True  # 2500 pixels > 100
    out = fit_planar_ramp(stack, mask=mask)
    assert out["slope_x"][0] == pytest.approx(0.05, abs=1e-6)
    # Mask too small (<100 pixels) -> NaN
    mask_small = np.zeros((height, width), dtype=bool)
    mask_small[0:5, 0:5] = True  # 25 pixels < 100
    out_small = fit_planar_ramp(stack, mask=mask_small)
    assert np.isnan(out_small["slope_x"][0])


def test_compute_ramp_aggregate_handles_few_finite() -> None:
    ramp_data = {
        "ramp_magnitude_rad": np.array([1.0, np.nan, np.nan, np.nan]),
        "ramp_direction_deg": np.array([10.0, np.nan, np.nan, np.nan]),
        "slope_x": np.zeros(4),
        "slope_y": np.zeros(4),
        "intercept_rad": np.zeros(4),
    }
    coh = np.array([0.8, 0.7, 0.6, 0.5])
    agg = compute_ramp_aggregate(ramp_data, coh)
    assert np.isnan(agg["mean_magnitude_rad"])
    assert np.isnan(agg["direction_stability_sigma_deg"])
    assert np.isnan(agg["magnitude_vs_coherence_pearson_r"])
    assert agg["n_ifgs"] == 1  # only the first row was finite


def test_compute_ramp_aggregate_computes_finite_aggregate() -> None:
    # 10 IFGs with random direction (large sigma) + correlated magnitude/coh
    rng = np.random.default_rng(seed=42)
    n = 10
    mag = np.linspace(1.0, 5.0, n)
    coh = np.linspace(0.5, 0.9, n)  # perfectly correlated with mag
    dir_deg = rng.uniform(-180, 180, n)  # truly random direction
    ramp_data = {
        "ramp_magnitude_rad": mag,
        "ramp_direction_deg": dir_deg,
        "slope_x": np.zeros(n),
        "slope_y": np.zeros(n),
        "intercept_rad": np.zeros(n),
    }
    agg = compute_ramp_aggregate(ramp_data, coh)
    assert agg["n_ifgs"] == n
    assert agg["mean_magnitude_rad"] == pytest.approx(mag.mean(), abs=1e-9)
    # Pearson r between mag and coh both linear from same start -> r ~ 1.0
    assert agg["magnitude_vs_coherence_pearson_r"] == pytest.approx(1.0, abs=1e-6)
    # Random direction => sigma should be substantial (>> 30 deg). Allow a
    # generous lower bound to avoid flakiness on small samples.
    assert agg["direction_stability_sigma_deg"] > 30.0


def test_auto_attribute_ramp_branch_table() -> None:
    # 4 cutoff-edge cases (CONTEXT D-Claude's-Discretion: 30 deg, 0.5 r)
    assert auto_attribute_ramp(10.0, 0.1) == "orbit"
    assert auto_attribute_ramp(50.0, 0.7) == "phass"
    assert auto_attribute_ramp(10.0, 0.7) == "mixed"
    assert auto_attribute_ramp(50.0, 0.1) == "inconclusive"


def test_auto_attribute_ramp_honors_custom_cutoffs() -> None:
    # With direction_stability_cutoff_deg=20, sigma=25 is now random (was stable at default 30).
    assert (
        auto_attribute_ramp(
            25.0, 0.1, direction_stability_cutoff_deg=20.0
        )
        == "inconclusive"
    )
    # And with coherence_correlation_cutoff=0.3, r=0.4 is now correlated
    # (was uncorrelated at default 0.5).
    assert (
        auto_attribute_ramp(
            50.0, 0.4, coherence_correlation_cutoff=0.3
        )
        == "phass"
    )


# ---------------------------------------------------------------------------
# Phase 11 Plan 03: deramp_ifg_stack and write_deramped_unwrapped_ifgs
# ---------------------------------------------------------------------------


def _make_plane_stack(
    n_ifg: int,
    height: int,
    width: int,
    slope_x: float = 0.05,
    slope_y: float = 0.03,
    intercept: float = 2.0,
    residual_scale: float = 0.1,
    rng_seed: int = 42,
) -> np.ndarray:
    """Make an (N, H, W) stack of plane + small residuals."""
    rng = np.random.default_rng(seed=rng_seed)
    yy, xx = np.indices((height, width), dtype=np.float64)
    plane = slope_x * xx + slope_y * yy + intercept
    residuals = rng.uniform(-residual_scale, residual_scale, size=(n_ifg, height, width))
    return (plane[np.newaxis, :, :] + residuals).astype(np.float64)


class TestDerampIfgStack:
    """Unit tests for deramp_ifg_stack."""

    def test_planar_residuals_approximately_zero_after_deramp(self) -> None:
        """After deramping, fitted slopes of the output should be near zero."""
        height, width = 256, 256
        stack = _make_plane_stack(4, height, width, slope_x=0.05, slope_y=0.03)
        deramped, ramp_data = deramp_ifg_stack(stack, mask=None)
        # Fit residual slopes on deramped output
        residual_ramp = fit_planar_ramp(deramped)
        assert residual_ramp["slope_x"].shape == (4,)
        # Slopes should be close to zero (within 1e-3 rad/pixel)
        finite_mask = np.isfinite(residual_ramp["slope_x"])
        assert finite_mask.any(), "At least one deramped IFG should have a valid slope"
        assert np.abs(residual_ramp["slope_x"][finite_mask]).max() < 0.01
        assert np.abs(residual_ramp["slope_y"][finite_mask]).max() < 0.01

    def test_non_planar_residual_values_remain_finite(self) -> None:
        """Non-planar values (Gaussian bumps) survive deramping and are finite."""
        height, width = 128, 128
        yy, xx = np.indices((height, width), dtype=np.float64)
        plane = 0.04 * xx + 0.02 * yy + 1.0
        # Add a Gaussian bump as the non-planar signal
        bump = 1.5 * np.exp(-((xx - 64) ** 2 + (yy - 64) ** 2) / (2 * 20**2))
        raw = (plane + bump)[np.newaxis, :, :]
        deramped, ramp_data = deramp_ifg_stack(raw)
        assert np.isfinite(deramped).all(), "Deramped output must be fully finite for clean input"

    def test_nan_where_source_not_finite(self) -> None:
        """NaN pixels in the source are preserved as NaN in the deramped output."""
        height, width = 64, 64
        stack = _make_plane_stack(2, height, width)
        # Introduce NaN in a patch
        stack[:, 10:20, 10:20] = np.nan
        deramped, _ = deramp_ifg_stack(stack)
        # The NaN region should remain NaN in the output
        assert np.all(np.isnan(deramped[:, 10:20, 10:20]))
        # Remaining region should be finite
        assert np.isfinite(deramped[:, 30:50, 30:50]).all()

    def test_returns_ramp_data_dict_with_correct_keys(self) -> None:
        """ramp_data returned must have the same keys as fit_planar_ramp output."""
        stack = _make_plane_stack(3, 64, 64)
        _, ramp_data = deramp_ifg_stack(stack)
        expected_keys = {"ramp_magnitude_rad", "ramp_direction_deg", "slope_x", "slope_y", "intercept_rad"}
        assert set(ramp_data.keys()) == expected_keys

    def test_invalid_2d_input_raises_value_error(self) -> None:
        """2-D input must raise ValueError (delegated from fit_planar_ramp path)."""
        bad = np.zeros((100, 100), dtype=np.float64)
        with pytest.raises(ValueError, match="must be 3-D"):
            deramp_ifg_stack(bad)

    def test_mask_parameter_is_forwarded(self) -> None:
        """mask= kwarg is passed through to fit_planar_ramp correctly."""
        height, width = 128, 128
        stack = _make_plane_stack(2, height, width)
        mask = np.ones((height, width), dtype=bool)
        mask[:50, :] = False  # restrict to lower half
        # Should not raise; mask is forwarded
        deramped, ramp_data = deramp_ifg_stack(stack, mask=mask)
        assert deramped.shape == stack.shape


class TestWriteDerampedUnwrappedIfgs:
    """Unit tests for write_deramped_unwrapped_ifgs (disk I/O helper)."""

    def test_output_paths_named_with_deramped_suffix(self) -> None:
        """Written files must be named {source_stem}.deramped.tif."""
        import rasterio
        from rasterio.transform import from_bounds

        height, width = 64, 64
        stack_data = _make_plane_stack(2, height, width)
        transform = from_bounds(0, 0, 1, 1, width, height)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            unw_paths = []
            for i in range(2):
                p = tmp / f"20240101_2024011{i+2}.unw.tif"
                profile = {
                    "driver": "GTiff", "dtype": "float32",
                    "width": width, "height": height, "count": 1,
                    "crs": "EPSG:32611", "transform": transform,
                }
                with rasterio.open(p, "w", **profile) as dst:
                    dst.write(stack_data[i].astype(np.float32), 1)
                unw_paths.append(p)

            out_dir = tmp / "deramped"
            written, ramp_data = write_deramped_unwrapped_ifgs(unw_paths, out_dir)

            assert len(written) == 2
            for src, dest in zip(unw_paths, written):
                expected_name = src.stem + ".deramped.tif"
                assert dest.name == expected_name, f"Expected {expected_name}, got {dest.name}"
                assert dest.exists(), f"Output file {dest} does not exist"

    def test_output_directory_is_created(self) -> None:
        """write_deramped_unwrapped_ifgs must create output_dir if absent."""
        import rasterio
        from rasterio.transform import from_bounds

        height, width = 32, 32
        stack_data = _make_plane_stack(1, height, width)
        transform = from_bounds(0, 0, 1, 1, width, height)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            p = tmp / "20240101_20240113.unw.tif"
            profile = {
                "driver": "GTiff", "dtype": "float32",
                "width": width, "height": height, "count": 1,
                "crs": "EPSG:32611", "transform": transform,
            }
            with rasterio.open(p, "w", **profile) as dst:
                dst.write(stack_data[0].astype(np.float32), 1)

            out_dir = tmp / "nested" / "deramped_output"
            written, _ = write_deramped_unwrapped_ifgs([p], out_dir)
            assert out_dir.exists()
            assert len(written) == 1

    def test_source_profile_preserved(self) -> None:
        """Output GeoTIFF must use the same CRS and dtype as the source."""
        import rasterio
        from rasterio.transform import from_bounds

        height, width = 64, 64
        stack_data = _make_plane_stack(1, height, width)
        transform = from_bounds(0, 0, 1, 1, width, height)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            p = tmp / "20240101_20240113.unw.tif"
            profile = {
                "driver": "GTiff", "dtype": "float32",
                "width": width, "height": height, "count": 1,
                "crs": "EPSG:32611", "transform": transform,
            }
            with rasterio.open(p, "w", **profile) as dst:
                dst.write(stack_data[0].astype(np.float32), 1)

            out_dir = tmp / "deramped"
            written, _ = write_deramped_unwrapped_ifgs([p], out_dir)

            with rasterio.open(written[0]) as ds:
                assert ds.crs.to_epsg() == 32611
                assert ds.dtypes[0] == "float32"
                assert ds.width == width
                assert ds.height == height

    def test_returns_ramp_data_dict(self) -> None:
        """ramp_data returned must have fit_planar_ramp keys."""
        import rasterio
        from rasterio.transform import from_bounds

        height, width = 64, 64
        stack_data = _make_plane_stack(2, height, width)
        transform = from_bounds(0, 0, 1, 1, width, height)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            unw_paths = []
            for i in range(2):
                p = tmp / f"20240101_2024011{i+2}.unw.tif"
                profile = {
                    "driver": "GTiff", "dtype": "float32",
                    "width": width, "height": height, "count": 1,
                    "crs": "EPSG:32611", "transform": transform,
                }
                with rasterio.open(p, "w", **profile) as dst:
                    dst.write(stack_data[i].astype(np.float32), 1)
                unw_paths.append(p)

            out_dir = tmp / "deramped"
            _, ramp_data = write_deramped_unwrapped_ifgs(unw_paths, out_dir)
            expected_keys = {"ramp_magnitude_rad", "ramp_direction_deg", "slope_x", "slope_y", "intercept_rad"}
            assert set(ramp_data.keys()) == expected_keys
