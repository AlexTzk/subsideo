"""Phase 4 selfconsistency ramp-attribution helpers — unit tests.

Covers fit_planar_ramp algorithm correctness, NaN edge case, mask honoring,
compute_ramp_aggregate aggregate computation, auto_attribute_ramp 4-branch
table.
"""
from __future__ import annotations

import numpy as np
import pytest

from subsideo.validation.selfconsistency import (
    auto_attribute_ramp,
    compute_ramp_aggregate,
    fit_planar_ramp,
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
