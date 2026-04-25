"""Block-bootstrap confidence-interval helper for Phase 5 DIST-S1 validation.

Hall (1985) stationary block bootstrap on a 2-D raster pair. Drops partial
blocks at tile edges (CONTEXT D-08); resamples full block-indices with
replacement; computes ``metric_fn`` over the union of resampled blocks'
pixels for each of ``n_bootstrap`` iterations; returns 2.5/97.5 percentile
CI bounds (95% CI default).

Pure-numpy implementation. PCG64 RNG (numpy.random.default_rng) per
SciPy/NumPy SPEC 7 + Phase 5 CONTEXT D-09 (rng_seed=0 default). Mersenne
Twister (np.random.RandomState) explicitly rejected (slower, statistically
inferior).

Module-level constants (PATTERNS section "Module-level constants pattern"):
    DEFAULT_BLOCK_SIZE_M    = 1000  -- 1 km blocks (CONTEXT D-08)
    DEFAULT_N_BOOTSTRAP     = 500   -- B=500 resamples (CONTEXT D-09)
    DEFAULT_RNG_SEED        = 0     -- PCG64 fixed seed (CONTEXT D-09)
    DEFAULT_CI_LEVEL        = 0.95  -- 95% CI (CONTEXT D-07)
    DEFAULT_PIXEL_SIZE_M    = 30    -- subsideo DIST-S1 grid posting

Switching any default requires a visible PR diff (auditable in
``git log --grep='DEFAULT_BLOCK_SIZE_M'``); never an env var or CLI flag.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

DEFAULT_BLOCK_SIZE_M: int = 1000
DEFAULT_N_BOOTSTRAP: int = 500
DEFAULT_RNG_SEED: int = 0
DEFAULT_CI_LEVEL: float = 0.95
DEFAULT_PIXEL_SIZE_M: int = 30


@dataclass(frozen=True)
class BootstrapResult:
    """Block-bootstrap CI result for a single metric.

    Attributes
    ----------
    point_estimate : float
        ``metric_fn`` evaluated on the full (unsampled) raster pair, after
        cropping to the full-block grid (partial-block edges dropped per
        CONTEXT D-08).
    ci_lower : float
        Lower bound at ``ci_level`` (default 2.5 percentile).
    ci_upper : float
        Upper bound at ``ci_level`` (default 97.5 percentile).
    n_blocks_kept : int
        Count of full ``block_size_m``-sized blocks that fit inside the raster.
    n_blocks_dropped : int
        Count of partial blocks at the east + south edges (information loss
        proxy; CONTEXT D-08 transparency).
    n_bootstrap : int
        Number of bootstrap resamples (typically 500).
    ci_level : float
        Confidence level used for percentile CI (typically 0.95).
    rng_seed : int
        PCG64 seed used for reproducibility (typically 0 per CONTEXT D-09).
    """

    point_estimate: float
    ci_lower: float
    ci_upper: float
    n_blocks_kept: int
    n_blocks_dropped: int
    n_bootstrap: int
    ci_level: float
    rng_seed: int


def block_bootstrap_ci(
    predictions: np.ndarray,
    references: np.ndarray,
    metric_fn: Callable[[np.ndarray, np.ndarray], float],
    *,
    block_size_m: int = DEFAULT_BLOCK_SIZE_M,
    pixel_size_m: int = DEFAULT_PIXEL_SIZE_M,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
    ci_level: float = DEFAULT_CI_LEVEL,
    rng_seed: int = DEFAULT_RNG_SEED,
) -> BootstrapResult:
    """Hall (1985) stationary block bootstrap on a 2-D raster pair.

    Parameters
    ----------
    predictions, references : np.ndarray
        2-D arrays of identical shape ``(H, W)``. NaN values are passed
        through to ``metric_fn`` which is expected to mask internally
        (mirrors ``subsideo.validation.metrics`` convention).
    metric_fn : Callable[[ndarray, ndarray], float]
        Pure-function metric primitive (e.g., ``metrics.f1_score``). Called
        with 1-D ravelled arrays.
    block_size_m : int, default 1000
        Block edge length in metres.
    pixel_size_m : int, default 30
        Raster posting in metres (subsideo DIST-S1 native).
    n_bootstrap : int, default 500
        Number of bootstrap resamples.
    ci_level : float, default 0.95
        Confidence level for percentile CI bounds.
    rng_seed : int, default 0
        PCG64 seed for ``np.random.default_rng``.

    Returns
    -------
    BootstrapResult
        Frozen dataclass with point estimate, CI bounds, block counts,
        bootstrap parameters.

    Notes
    -----
    Inner-loop runtime is ~3 minutes for T11SLT (3660x3660, 12,100 blocks,
    B=500) per RESEARCH Probe 9. Optimisation deferred until a 2nd consumer
    appears.
    """
    if predictions.shape != references.shape:
        raise ValueError(
            f"predictions {predictions.shape} != references {references.shape}"
        )
    if predictions.ndim != 2:
        raise ValueError(f"predictions must be 2-D; got ndim={predictions.ndim}")

    H, W = predictions.shape
    px_per_block = block_size_m // pixel_size_m  # 33 for 1km/30m
    n_block_rows = H // px_per_block
    n_block_cols = W // px_per_block
    n_blocks_kept = n_block_rows * n_block_cols
    # Partial blocks: include the L-shaped strip at east + south edges,
    # plus the south-east corner. Total partial = (rows+1)*(cols+1) - kept.
    n_blocks_dropped = (n_block_rows + 1) * (n_block_cols + 1) - n_blocks_kept

    if n_blocks_kept == 0:
        raise ValueError(
            f"raster ({H}x{W}) too small for block_size_m={block_size_m}"
            f" / pixel_size_m={pixel_size_m} (need at least {px_per_block}x{px_per_block})"
        )

    # Crop to full-block grid for both point estimate and bootstrap pool.
    pred_full = predictions[: n_block_rows * px_per_block, : n_block_cols * px_per_block]
    ref_full = references[: n_block_rows * px_per_block, : n_block_cols * px_per_block]

    # Point estimate on the full-block-cropped pair.
    point = float(metric_fn(pred_full.ravel(), ref_full.ravel()))

    # Bootstrap loop -- resample n_blocks_kept indices with replacement,
    # gather pixels by block-index, evaluate metric_fn.
    rng = np.random.default_rng(rng_seed)
    bootstrap_metrics = np.empty(n_bootstrap, dtype=np.float64)
    for b in range(n_bootstrap):
        sample = rng.integers(0, n_blocks_kept, size=n_blocks_kept)
        # Map block index -> top-left pixel coordinate
        rows = (sample // n_block_cols) * px_per_block
        cols = (sample % n_block_cols) * px_per_block
        # Gather pixels (concatenate is O(B * blocks * pixels^2); RESEARCH
        # Risk M flagged this; ~3 min/call is acceptable for Phase 5).
        pred_b = np.concatenate(
            [
                pred_full[r : r + px_per_block, c : c + px_per_block].ravel()
                for r, c in zip(rows.tolist(), cols.tolist(), strict=False)
            ]
        )
        ref_b = np.concatenate(
            [
                ref_full[r : r + px_per_block, c : c + px_per_block].ravel()
                for r, c in zip(rows.tolist(), cols.tolist(), strict=False)
            ]
        )
        bootstrap_metrics[b] = float(metric_fn(pred_b, ref_b))

    alpha = (1.0 - ci_level) / 2.0
    ci_lower = float(np.quantile(bootstrap_metrics, alpha))
    ci_upper = float(np.quantile(bootstrap_metrics, 1.0 - alpha))

    return BootstrapResult(
        point_estimate=point,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        n_blocks_kept=n_blocks_kept,
        n_blocks_dropped=n_blocks_dropped,
        n_bootstrap=n_bootstrap,
        ci_level=ci_level,
        rng_seed=rng_seed,
    )
