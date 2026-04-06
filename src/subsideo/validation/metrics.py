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


# ---------------------------------------------------------------------------
# Binary classification metrics (DSWx / DIST validation)
# ---------------------------------------------------------------------------


def f1_score(predicted: np.ndarray, reference: np.ndarray) -> float:
    """F1 score for binary classification arrays.

    Accepts 1-D integer or boolean arrays.  Returns 0.0 when no positive
    predictions or references exist.
    """
    tp = np.sum((predicted == 1) & (reference == 1))
    fp = np.sum((predicted == 1) & (reference == 0))
    fn = np.sum((predicted == 0) & (reference == 1))
    precision_val = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall_val = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    if precision_val + recall_val == 0:
        return 0.0
    return float(2 * precision_val * recall_val / (precision_val + recall_val))


def precision_score(predicted: np.ndarray, reference: np.ndarray) -> float:
    """Precision (TP / (TP + FP)) for binary classification arrays."""
    tp = np.sum((predicted == 1) & (reference == 1))
    fp = np.sum((predicted == 1) & (reference == 0))
    return float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0


def recall_score(predicted: np.ndarray, reference: np.ndarray) -> float:
    """Recall (TP / (TP + FN)) for binary classification arrays."""
    tp = np.sum((predicted == 1) & (reference == 1))
    fn = np.sum((predicted == 0) & (reference == 1))
    return float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0


def overall_accuracy(predicted: np.ndarray, reference: np.ndarray) -> float:
    """Overall accuracy ((TP + TN) / total) for binary classification arrays."""
    correct = np.sum(predicted == reference)
    total = predicted.size
    return float(correct / total) if total > 0 else 0.0
