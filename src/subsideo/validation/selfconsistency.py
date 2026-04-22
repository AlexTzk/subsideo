"""Sequential-IFG coherence statistics + reference-frame aligned residual velocity.

Consumed by Phase 3 CSLC self-consistency eval and Phase 4 DISP
self-consistency eval. The ``coherence_stats`` function ships all five
statistics (``mean`` / ``median`` / ``p25`` / ``p75`` /
``persistently_coherent_fraction``) so Phase 3 calibration can select
the appropriate bar without another dataclass edit (PITFALLS P2.2
research-flagged planning decision).

``residual_mean_velocity`` performs reference-frame alignment by
subtracting the stable-mask anchor (median by default, per PITFALLS
P2.3) from every pixel before computing residual -- absolute LOS
velocity magnitudes are arbitrary; the apples-to-apples comparison
is the centred residual.

Pure-function module -- no I/O, no module-top conda-forge imports.
Consumers include ``validation/stable_terrain.py`` only indirectly
(callers pass the mask produced by ``build_stable_mask``).
"""
from __future__ import annotations

from typing import Literal

import numpy as np
from loguru import logger

DEFAULT_COHERENCE_THRESHOLD: float = 0.6


def coherence_stats(
    ifgrams_stack: np.ndarray,
    stable_mask: np.ndarray,
    *,
    coherence_threshold: float = DEFAULT_COHERENCE_THRESHOLD,
) -> dict[str, float]:
    """Return per-stable-pixel coherence statistics across an IFG stack.

    Ships every candidate statistic (mean / median / p25 / p75 /
    persistently_coherent_fraction) so Phase 3 calibration can pick the
    appropriate bar without another dataclass edit (PITFALLS P2.2).

    Parameters
    ----------
    ifgrams_stack : (N, H, W) float np.ndarray
        Per-IFG coherence arrays in [0, 1]. NaN entries are treated as 0
        both for the per-pixel time-mean and for the persistence threshold.
    stable_mask : (H, W) bool np.ndarray
        True where pixel is considered stable terrain (from ``build_stable_mask``).
    coherence_threshold : float, default 0.6
        Per-IFG coherence threshold used to compute
        ``persistently_coherent_fraction``.

    Returns
    -------
    stats : dict[str, float]
        Keys (exactly five): ``mean``, ``median``, ``p25``, ``p75``,
        ``persistently_coherent_fraction``. All values are Python floats.
        If ``stable_mask`` is empty, every value is 0.0 and no exception
        is raised.
    """
    if int(stable_mask.sum()) == 0:
        logger.warning("coherence_stats called with empty stable_mask -- returning zeros")
        return {
            "mean": 0.0,
            "median": 0.0,
            "p25": 0.0,
            "p75": 0.0,
            "persistently_coherent_fraction": 0.0,
        }

    # NaN -> 0 everywhere (conservative for both mean and persistence)
    stack = np.where(np.isfinite(ifgrams_stack), ifgrams_stack, 0.0).astype(np.float64)

    # (N, H, W) -> (H, W): per-pixel mean coherence across the time dimension
    per_pixel_mean = stack.mean(axis=0)

    vals = per_pixel_mean[stable_mask]
    stats: dict[str, float] = {
        "mean": float(vals.mean()),
        "median": float(np.median(vals)),
        "p25": float(np.percentile(vals, 25)),
        "p75": float(np.percentile(vals, 75)),
    }

    # persistently_coherent_fraction = fraction of stable pixels whose
    # per-IFG coherence exceeds the threshold for EVERY IFG in the stack
    per_ifg_above = stack >= coherence_threshold
    all_ifgs_above = per_ifg_above.all(axis=0)  # (H, W)
    num_persistent = int((all_ifgs_above & stable_mask).sum())
    stats["persistently_coherent_fraction"] = float(num_persistent) / float(int(stable_mask.sum()))

    logger.debug(
        "coherence_stats: n_stable={}, mean={:.3f}, median={:.3f}, "
        "p25={:.3f}, p75={:.3f}, persistent_frac={:.3f}",
        int(stable_mask.sum()),
        stats["mean"],
        stats["median"],
        stats["p25"],
        stats["p75"],
        stats["persistently_coherent_fraction"],
    )
    return stats


def residual_mean_velocity(
    velocity_mm_yr: np.ndarray,
    stable_mask: np.ndarray,
    *,
    frame_anchor: Literal["median", "mean"] = "median",
) -> float:
    """Return the stable-mask mean velocity after reference-frame alignment.

    Reference-frame alignment subtracts the stable-mask anchor (median by
    default) from every stable-mask pixel before averaging -- LOS velocity
    magnitudes are arbitrary per PITFALLS P2.3; what matters is the
    deviation from the stable-terrain reference.

    Parameters
    ----------
    velocity_mm_yr : (H, W) float np.ndarray
        Line-of-sight velocity field in mm/yr. NaN pixels within the mask
        are excluded from the residual computation.
    stable_mask : (H, W) bool np.ndarray
        True where pixel is stable terrain (from ``build_stable_mask``).
    frame_anchor : {'median', 'mean'}, default 'median'
        How to compute the reference-frame anchor from stable-mask pixels.
        Median is the default per PITFALLS P2.3 (robust to stable-mask
        false-positives).

    Returns
    -------
    residual : float
        Mean of ``(velocity - anchor)`` over finite stable-mask pixels.
        Returns 0.0 if all stable-mask pixels are NaN.

    Raises
    ------
    ValueError
        If ``stable_mask.sum() == 0`` or ``frame_anchor`` is not recognised.
    """
    if int(stable_mask.sum()) == 0:
        raise ValueError("stable_mask is empty; cannot compute residual mean velocity")

    vals = velocity_mm_yr[stable_mask]
    vals = vals[np.isfinite(vals)]
    if len(vals) == 0:
        return 0.0

    if frame_anchor == "median":
        anchor = float(np.median(vals))
    elif frame_anchor == "mean":
        anchor = float(vals.mean())
    else:
        raise ValueError(
            f"frame_anchor must be 'median' or 'mean', got {frame_anchor!r}"
        )

    residual = float((vals - anchor).mean())
    logger.debug(
        "residual_mean_velocity: n_stable={}, anchor={:.3f} mm/yr, residual={:.3f} mm/yr",
        len(vals),
        anchor,
        residual,
    )
    return residual
