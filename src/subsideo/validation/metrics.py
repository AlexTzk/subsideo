"""Pure-function validation metrics for comparing predicted vs reference arrays.

All functions accept numpy arrays and handle NaN/nodata masking internally.
No file I/O -- comparison modules handle loading and spatial alignment.
"""
from __future__ import annotations

import numpy as np
from scipy import stats


def rmse(predicted: np.ndarray, reference: np.ndarray) -> float:
    """Root Mean Square Error between predicted and reference arrays.

    NaN values in either array are excluded from the computation.
    Returns 0.0 if no valid pairs exist.
    """
    mask = np.isfinite(predicted) & np.isfinite(reference)
    diff = predicted[mask] - reference[mask]
    if len(diff) == 0:
        return 0.0
    return float(np.sqrt(np.mean(diff**2)))


def spatial_correlation(predicted: np.ndarray, reference: np.ndarray) -> float:
    """Pearson correlation coefficient between predicted and reference arrays.

    NaN values in either array are excluded. Returns 0.0 if fewer than 2
    valid pairs exist.
    """
    mask = np.isfinite(predicted) & np.isfinite(reference)
    p = predicted[mask].ravel()
    r = reference[mask].ravel()
    if len(p) < 2:
        return 0.0
    corr, _ = stats.pearsonr(p, r)
    return float(corr)


def bias(predicted: np.ndarray, reference: np.ndarray) -> float:
    """Mean difference (predicted - reference).

    NaN values in either array are excluded. Returns 0.0 if no valid
    pairs exist.
    """
    mask = np.isfinite(predicted) & np.isfinite(reference)
    if not np.any(mask):
        return 0.0
    return float(np.mean(predicted[mask] - reference[mask]))


def ssim(
    predicted: np.ndarray,
    reference: np.ndarray,
    data_range: float | None = None,
) -> float:
    """Structural Similarity Index between 2-D arrays.

    Handles NaN by cropping to the bounding box of valid pixels and
    filling any remaining NaN within that box with 0. Uses scikit-image
    ``structural_similarity`` under the hood (lazy import).

    Returns 0.0 if no valid pixels exist.
    """
    from skimage.metrics import structural_similarity

    mask = np.isfinite(predicted) & np.isfinite(reference)
    rows, cols = np.where(mask)
    if len(rows) == 0:
        return 0.0
    r0, r1 = rows.min(), rows.max() + 1
    c0, c1 = cols.min(), cols.max() + 1
    p = predicted[r0:r1, c0:c1].copy()
    r = reference[r0:r1, c0:c1].copy()
    # Fill any remaining NaN within the bounding box
    p = np.nan_to_num(p, nan=0.0)
    r = np.nan_to_num(r, nan=0.0)
    if data_range is None:
        data_range = float(np.nanmax(r) - np.nanmin(r))
    if data_range == 0:
        return 1.0 if np.allclose(p, r) else 0.0
    return float(structural_similarity(p, r, data_range=data_range))
