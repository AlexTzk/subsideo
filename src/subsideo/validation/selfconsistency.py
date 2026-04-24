"""Sequential-IFG coherence statistics + reference-frame aligned residual velocity.

Consumed by Phase 3 CSLC self-consistency eval and Phase 4 DISP
self-consistency eval. The ``coherence_stats`` function ships all six
statistics (``mean`` / ``median`` / ``p25`` / ``p75`` /
``persistently_coherent_fraction`` / ``median_of_persistent``) so Phase 3
calibration can select the appropriate bar without another dataclass edit
(PITFALLS P2.2 research-flagged planning decision; D-01 resolves to
``median_of_persistent`` as the gate stat).

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

from datetime import datetime
from pathlib import Path
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
        Keys (exactly six): ``mean``, ``median``, ``p25``, ``p75``,
        ``persistently_coherent_fraction``, ``median_of_persistent``.
        All values are Python floats. If ``stable_mask`` is empty, every
        value is 0.0 and no exception is raised.

        ``median_of_persistent`` is the median per-pixel-mean coherence
        restricted to pixels that are both in ``stable_mask`` and
        persistently coherent across every IFG (P2.2 robust gate stat,
        Phase 3 D-01). Returns 0.0 when no persistently-coherent pixels
        exist (guards against empty intersection of stable & persistent).
    """
    if int(stable_mask.sum()) == 0:
        logger.warning("coherence_stats called with empty stable_mask -- returning zeros")
        return {
            "mean": 0.0,
            "median": 0.0,
            "p25": 0.0,
            "p75": 0.0,
            "persistently_coherent_fraction": 0.0,
            "median_of_persistent": 0.0,
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

    # median_of_persistent = median per-pixel-mean coherence over pixels that are
    # both in the stable mask AND persistently coherent in every IFG (P2.2 robust
    # gate stat — Phase 3 D-01; immune to bimodal dune/playa contamination).
    persistent_stable = all_ifgs_above & stable_mask
    if int(persistent_stable.sum()) == 0:
        stats["median_of_persistent"] = 0.0
    else:
        stats["median_of_persistent"] = float(np.median(per_pixel_mean[persistent_stable]))

    logger.debug(
        "coherence_stats: n_stable={}, mean={:.3f}, median={:.3f}, "
        "p25={:.3f}, p75={:.3f}, persistent_frac={:.3f}, median_of_persistent={:.3f}",
        int(stable_mask.sum()),
        stats["mean"],
        stats["median"],
        stats["p25"],
        stats["p75"],
        stats["persistently_coherent_fraction"],
        stats["median_of_persistent"],
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


def compute_residual_velocity(
    cslc_stack_paths: list[Path],
    stable_mask: np.ndarray,
    *,
    sensing_dates: list[datetime] | None = None,
) -> np.ndarray:
    """Per-pixel linear-fit residual velocity (mm/yr) from a CSLC stack.

    Per CONTEXT 03-CONTEXT.md D-Claude's-Discretion: linear-fit per-pixel
    over the stack (NOT MintPy SBAS). Wraps the pixel-wise unwrapped-phase
    -> velocity regression used by the Phase 3 eval scripts.

    Parameters
    ----------
    cslc_stack_paths : list[Path]
        Ordered list of subsideo CSLC HDF5 paths (one per epoch).
    stable_mask : (H, W) bool np.ndarray
        True where pixel is stable terrain.
    sensing_dates : list[datetime] | None
        One datetime per CSLC; required for the mm/yr scaling. If None,
        dates are extracted from the HDF5 ``identification/zero_doppler_start_time``
        attribute (OPERA CSLC-S1 spec) via a lazy h5py read.

    Returns
    -------
    velocity_mm_yr : (H, W) float32 np.ndarray
        Linear-fit slope converted to mm/yr via Sentinel-1 wavelength
        (lambda = 0.055465763 m, LOS: v_mm_yr = -slope_rad_per_yr * lambda /
        (4*pi) * 1000 * seconds_per_year_inverse). NaN outside stable_mask.

    Raises
    ------
    NotImplementedError
        Implementation is deferred to Plan 03-03 which runs the full CSLC
        stack. This stub documents the signature and type contract for
        downstream callers (run_eval_cslc_selfconsist_nam.py etc.).
    ValueError
        If ``len(cslc_stack_paths) < 3`` (minimum required for a meaningful
        linear fit; fewer epochs under-constrain the velocity regression).
    """
    # Implementation deferred to Plan 03-03 (eval script integration).
    # Plan 03-01 ships the signature + type contract only.
    raise NotImplementedError(
        "compute_residual_velocity is implemented in Plan 03-03. "
        "This stub defines the interface for downstream eval scripts."
    )
