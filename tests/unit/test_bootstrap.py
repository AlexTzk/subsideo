"""Unit tests for subsideo.validation.bootstrap (Plan 05-03 Task 1)."""
from __future__ import annotations

import numpy as np
import pytest

from subsideo.validation.bootstrap import (
    BootstrapResult,
    DEFAULT_BLOCK_SIZE_M,
    DEFAULT_CI_LEVEL,
    DEFAULT_N_BOOTSTRAP,
    DEFAULT_PIXEL_SIZE_M,
    DEFAULT_RNG_SEED,
    block_bootstrap_ci,
)
from subsideo.validation.metrics import f1_score


def test_module_level_defaults():
    """The 5 documented module-level constants resolve to the locked values."""
    assert DEFAULT_BLOCK_SIZE_M == 1000
    assert DEFAULT_N_BOOTSTRAP == 500
    assert DEFAULT_RNG_SEED == 0
    assert DEFAULT_CI_LEVEL == 0.95
    assert DEFAULT_PIXEL_SIZE_M == 30


def test_point_estimate_matches_metric_fn():
    """BootstrapResult.point_estimate equals metric_fn(pred.ravel(), ref.ravel())."""
    rng = np.random.default_rng(seed=42)
    pred = (rng.random((1320, 1320)) > 0.5).astype(np.float32)
    ref = pred.copy()  # perfect agreement
    ref.flat[::13] = 1.0 - ref.flat[::13]  # introduce ~7.7% disagreement
    expected = f1_score(pred.ravel(), ref.ravel())
    result = block_bootstrap_ci(
        pred,
        ref,
        metric_fn=f1_score,
        block_size_m=1000,
        pixel_size_m=30,
        n_bootstrap=10,  # small B for fast test
        rng_seed=0,
    )
    assert isinstance(result, BootstrapResult)
    assert abs(result.point_estimate - expected) < 1e-9


def test_deterministic_seed_reproducibility():
    """Same seed -> same bootstrap CI bounds (PCG64 deterministic)."""
    rng = np.random.default_rng(seed=42)
    pred = (rng.random((660, 660)) > 0.5).astype(np.float32)
    ref = pred.copy()
    ref.flat[::13] = 1.0 - ref.flat[::13]
    r1 = block_bootstrap_ci(pred, ref, metric_fn=f1_score, n_bootstrap=20, rng_seed=0)
    r2 = block_bootstrap_ci(pred, ref, metric_fn=f1_score, n_bootstrap=20, rng_seed=0)
    assert r1.ci_lower == r2.ci_lower
    assert r1.ci_upper == r2.ci_upper
    assert r1.n_blocks_kept == r2.n_blocks_kept
    assert r1.n_blocks_dropped == r2.n_blocks_dropped


def test_block_count_math_for_t11slt_shape():
    """For a 3660x3660 raster, n_blocks_kept == 12100 and n_blocks_dropped == 221.

    Verifies RESEARCH Probe 9 corrected count: floor(3660/33) = 110 blocks per axis;
    full grid 110*110 = 12100; partial L-strip (110+1)*(110+1) - 12100 = 221.
    """
    pred = np.zeros((3660, 3660), dtype=np.float32)
    ref = np.zeros((3660, 3660), dtype=np.float32)
    result = block_bootstrap_ci(
        pred,
        ref,
        metric_fn=f1_score,
        block_size_m=1000,
        pixel_size_m=30,
        n_bootstrap=2,  # we only check the block math, not the metric
        rng_seed=0,
    )
    assert result.n_blocks_kept == 110 * 110
    assert result.n_blocks_dropped == (110 + 1) * (110 + 1) - (110 * 110)


def test_nan_propagation_through_metric_fn():
    """NaN inputs do not crash; metric_fn masks and returns a finite float."""
    rng = np.random.default_rng(seed=42)
    pred = (rng.random((660, 660)) > 0.5).astype(np.float32)
    ref = pred.copy()
    # Inject NaNs into 5% of pixels
    nan_mask = rng.random((660, 660)) < 0.05
    pred[nan_mask] = np.nan
    ref[nan_mask] = np.nan
    result = block_bootstrap_ci(
        pred,
        ref,
        metric_fn=f1_score,
        n_bootstrap=10,
        rng_seed=0,
    )
    assert np.isfinite(result.point_estimate)
    assert np.isfinite(result.ci_lower)
    assert np.isfinite(result.ci_upper)
