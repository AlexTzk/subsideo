"""Sequential-IFG self-consistency primitives.

Coherence statistics, reference-frame aligned residual, sequential-IFG
coherence-stack construction, and per-IFG planar-ramp fitting for the Phase 4
ramp-attribution diagnostic.

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
    # gate stat -- Phase 3 D-01; immune to bimodal dune/playa contamination).
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
    over the stack (NOT MintPy SBAS).

    Algorithm:
      1. Load each CSLC HDF5 into a complex (H, W) ndarray; stack to (N, H, W).
      2. Extract phase = np.angle(complex) for every pixel, every epoch.
      3. Unwrap the per-pixel time-series via np.unwrap along the time axis.
         (Pure temporal unwrap; pixels that jump by more than pi between
         consecutive epochs are assumed to wrap -- acceptable for stable-
         terrain pixels over 12-day baselines.)
      4. Per-pixel linear-fit phase_rad vs days_since_t0 via vectorised OLS:
         slope_rad_per_day = cov(days, phase) / var(days).
      5. Convert slope to LOS velocity mm/yr:
           wavelength = 0.055465763 m  # Sentinel-1 C-band
           v_m_per_day = -slope_rad_per_day * wavelength / (4 * np.pi)
           v_mm_per_yr = v_m_per_day * 1000.0 * 365.25
         (LOS convention: positive phase rate -> target moving towards sensor
          -> negative vertical velocity for vertical-dominant motion.)
      6. Return (H, W) float32 velocity raster; pixels outside stable_mask
         set to NaN (caller uses stable_mask to filter; NaN fill makes it
         explicit).

    Parameters
    ----------
    cslc_stack_paths : list[Path]
        Ordered HDF5 paths, one per epoch.
    stable_mask : (H, W) bool np.ndarray
        True where pixel is stable terrain.
    sensing_dates : list[datetime] | None
        One datetime per CSLC. If None, extract from each HDF5 via
        identification/zero_doppler_start_time attribute (OPERA spec).

    Returns
    -------
    velocity_mm_yr : (H, W) float32 np.ndarray
        Linear-fit slope converted to mm/yr. NaN outside stable_mask.

    Raises
    ------
    ValueError
        If ``len(cslc_stack_paths) < 3`` (minimum required for a meaningful
        linear fit; fewer epochs under-constrain the velocity regression).
    RuntimeError
        If no VV/HH CSLC dataset is found in an HDF5 file.
    """
    import h5py  # lazy per PATTERNS "Two-layer install + lazy imports"

    if len(cslc_stack_paths) < 3:
        raise ValueError(
            f"compute_residual_velocity requires >=3 epochs; got {len(cslc_stack_paths)}"
        )

    # Step 1 -- load all CSLCs; extract phase.
    stacks: list[np.ndarray] = []
    extracted_dates: list[datetime] = []
    for p in cslc_stack_paths:
        with h5py.File(p, "r") as f:
            # Candidate dataset paths (matches compare_cslc._load_cslc_complex)
            for dset_path in (
                "/data/VV",
                "/data/HH",
                "/science/SENTINEL1/CSLC/grids/VV",
                "/science/SENTINEL1/CSLC/grids/HH",
            ):
                if dset_path in f:
                    cslc = f[dset_path][:].astype(np.complex64)
                    # Outside the parallelogram burst footprint the rectangular
                    # CSLC grid is NaN (~64% of pixels for SoCal t144_308029_iw1).
                    # np.angle(NaN+NaNj) is NaN; replace with 0 so the phase is
                    # deterministic (0 rad) on invalid pixels. The caller's
                    # stable_mask filters them out before the linear fit.
                    bad = ~(np.isfinite(cslc.real) & np.isfinite(cslc.imag))
                    if bad.any():
                        cslc = cslc.copy()
                        cslc[bad] = np.complex64(0)
                    break
            else:
                raise RuntimeError(f"No VV/HH CSLC dataset found in {p}")
            if sensing_dates is None:
                # Try attribute first, then dataset
                id_group = f["identification"]
                ts_val = id_group.attrs.get("zero_doppler_start_time")
                if ts_val is None and "zero_doppler_start_time" in id_group:
                    ts_val = id_group["zero_doppler_start_time"][()]
                if ts_val is None:
                    raise RuntimeError(
                        f"Cannot extract zero_doppler_start_time from {p}: "
                        "attribute and dataset both missing under 'identification'"
                    )
                if isinstance(ts_val, bytes):
                    ts_val = ts_val.decode()
                # OPERA format: "YYYY-MM-DDTHH:MM:SS.sssssssssZ"
                extracted_dates.append(
                    datetime.fromisoformat(str(ts_val).rstrip("Z"))
                )
        stacks.append(np.angle(cslc).astype(np.float32))

    if sensing_dates is None:
        sensing_dates = extracted_dates
    assert len(sensing_dates) == len(cslc_stack_paths), (
        f"sensing_dates length {len(sensing_dates)} != stack length {len(cslc_stack_paths)}"
    )

    phase_stack = np.stack(stacks, axis=0)  # (N, H, W)
    logger.info("compute_residual_velocity: stack shape {}", phase_stack.shape)

    # Step 3 -- temporal unwrap per-pixel
    phase_unwrapped = np.unwrap(phase_stack, axis=0)

    # Step 4 -- linear fit per-pixel (vectorised OLS)
    t0 = sensing_dates[0]
    days = np.array(
        [(d - t0).total_seconds() / 86400.0 for d in sensing_dates],
        dtype=np.float64,
    )
    days_c = days - days.mean()
    # (N, H, W): mean-centred phase
    phase_d = phase_unwrapped.astype(np.float64)
    phase_c = phase_d - phase_d.mean(axis=0, keepdims=True)
    var_days = float((days_c**2).sum())
    # slope = cov(days, phase) / var(days)
    slope = (days_c[:, None, None] * phase_c).sum(axis=0) / var_days
    slope_rad_per_day = slope.astype(np.float32)

    # Step 5 -- convert to mm/yr
    wavelength = 0.055465763  # Sentinel-1 C-band, metres
    v_m_per_day = -slope_rad_per_day * wavelength / (4.0 * float(np.pi))
    v_mm_per_yr = (v_m_per_day * 1000.0 * 365.25).astype(np.float32)

    # Step 6 -- NaN outside stable_mask
    v_mm_per_yr[~stable_mask] = np.float32("nan")
    return np.asarray(v_mm_per_yr, dtype=np.float32)


def fit_planar_ramp(
    ifgrams_stack: np.ndarray,
    mask: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """Fit a planar phase ramp to each IFG in the stack via least squares.

    For each unwrapped IFG, fit ``z = a*x + b*y + c`` on finite-non-zero pixels
    in image (pixel-index) coordinates -- NOT UTM. Reports peak-to-peak
    magnitude across the burst extent, plus direction (degrees from East).

    Per CONTEXT D-Claude's-Discretion: full-burst (not stable-mask-only)
    least-squares plane fit because orbit/tropospheric/PHASS ramps span the
    burst -- masking to stable-only would clip them and bias direction.

    Parameters
    ----------
    ifgrams_stack : (N, H, W) float np.ndarray
        Unwrapped phase in radians per IFG. NaN and zero values are excluded
        from the fit (typical PHASS unwrapper convention: 0 outside valid
        data, NaN for masked-out pixels).
    mask : (H, W) bool np.ndarray | None
        Optional restriction to specific pixels. ``None`` (default) means
        full-burst fit per D-Claude's-Discretion.

    Returns
    -------
    dict[str, np.ndarray]
        Per-IFG arrays of length N:
          - ``'ramp_magnitude_rad'`` : peak-to-peak rad across the burst
          - ``'ramp_direction_deg'`` : degrees from East
            (``atan2(slope_y, slope_x) * 180/pi``)
          - ``'slope_x'`` : a (rad per pixel column)
          - ``'slope_y'`` : b (rad per pixel row)
          - ``'intercept_rad'`` : c

    Raises
    ------
    ValueError
        If ``ifgrams_stack.ndim != 3``.
    """
    if ifgrams_stack.ndim != 3:
        raise ValueError(
            f"ifgrams_stack must be 3-D (N, H, W); got shape {ifgrams_stack.shape}"
        )
    n_ifg, height, width = ifgrams_stack.shape
    yy, xx = np.indices((height, width))
    x_flat = xx.ravel().astype(np.float64)
    y_flat = yy.ravel().astype(np.float64)

    out: dict[str, list[float]] = {
        "ramp_magnitude_rad": [],
        "ramp_direction_deg": [],
        "slope_x": [],
        "slope_y": [],
        "intercept_rad": [],
    }

    for k in range(n_ifg):
        z = ifgrams_stack[k].astype(np.float64)
        valid = np.isfinite(z) & (z != 0.0)
        if mask is not None:
            valid &= mask
        z_flat = z.ravel()
        keep = valid.ravel()

        if int(keep.sum()) < 100:
            out["ramp_magnitude_rad"].append(float("nan"))
            out["ramp_direction_deg"].append(float("nan"))
            out["slope_x"].append(float("nan"))
            out["slope_y"].append(float("nan"))
            out["intercept_rad"].append(float("nan"))
            continue

        design_matrix = np.column_stack(
            [
                x_flat[keep],
                y_flat[keep],
                np.ones(int(keep.sum()), dtype=np.float64),
            ]
        )
        b_vec = z_flat[keep]
        coeffs, _, _, _ = np.linalg.lstsq(design_matrix, b_vec, rcond=None)
        a, b, c = float(coeffs[0]), float(coeffs[1]), float(coeffs[2])

        z_plane_flat = a * x_flat[keep] + b * y_flat[keep] + c
        ramp_magnitude = float(z_plane_flat.max() - z_plane_flat.min())
        ramp_direction_deg = float(np.degrees(np.arctan2(b, a)))

        out["ramp_magnitude_rad"].append(ramp_magnitude)
        out["ramp_direction_deg"].append(ramp_direction_deg)
        out["slope_x"].append(a)
        out["slope_y"].append(b)
        out["intercept_rad"].append(c)

    return {k: np.asarray(v, dtype=np.float64) for k, v in out.items()}


def compute_ramp_aggregate(
    ramp_data: dict[str, np.ndarray],
    ifg_coherence_per_ifg: np.ndarray,
) -> dict[str, float | int]:
    """Compute aggregate ramp statistics across an IFG stack.

    Returns a dict matching ``RampAggregate`` Pydantic model shape:
      - ``mean_magnitude_rad``: mean of finite per-IFG magnitudes
      - ``direction_stability_sigma_deg``: circular stddev (scipy.stats.circstd)
      - ``magnitude_vs_coherence_pearson_r``: Pearson r between magnitude and coherence
      - ``n_ifgs``: count of finite IFGs included

    Returns NaN-filled aggregate (and n_ifgs = number of finite entries, possibly 0)
    when fewer than 3 finite IFG entries are available.

    Per RESEARCH lines 656-684: scipy.stats.circstd handles 359 -> 0 wrap on
    angles. Lazy-imported per the conda-forge dep convention.

    Returns a plain dict (not a Pydantic model) to avoid a circular import
    between selfconsistency.py and matrix_schema.py; the caller in
    run_eval_disp.py converts to ``RampAggregate`` at write time.
    """
    from scipy.stats import circstd  # lazy

    mag = ramp_data["ramp_magnitude_rad"]
    dir_deg = ramp_data["ramp_direction_deg"]
    coh = ifg_coherence_per_ifg

    finite = np.isfinite(mag) & np.isfinite(dir_deg) & np.isfinite(coh)
    if int(finite.sum()) < 3:
        return {
            "mean_magnitude_rad": float("nan"),
            "direction_stability_sigma_deg": float("nan"),
            "magnitude_vs_coherence_pearson_r": float("nan"),
            "n_ifgs": int(finite.sum()),
        }

    mag_f = mag[finite]
    dir_f = dir_deg[finite]
    coh_f = coh[finite]

    mean_magnitude = float(mag_f.mean())
    direction_sigma_deg = float(
        np.degrees(circstd(np.radians(dir_f), high=np.pi, low=-np.pi))
    )
    pearson_r = float(np.corrcoef(mag_f, coh_f)[0, 1])
    return {
        "mean_magnitude_rad": mean_magnitude,
        "direction_stability_sigma_deg": direction_sigma_deg,
        "magnitude_vs_coherence_pearson_r": pearson_r,
        "n_ifgs": int(finite.sum()),
    }


def auto_attribute_ramp(
    direction_stability_sigma_deg: float,
    magnitude_vs_coherence_pearson_r: float,
    *,
    direction_stability_cutoff_deg: float = 30.0,
    coherence_correlation_cutoff: float = 0.5,
) -> Literal["phass", "orbit", "tropospheric", "mixed", "inconclusive"]:
    """Deterministic ramp-source auto-attribute (CONTEXT D-Claude's-Discretion).

    Rules:
      - direction stable (sigma < cutoff_deg): orbit-class signature
      - magnitude correlates with coherence (r > correlation_cutoff): PHASS-class
      - both stable AND correlated: 'mixed'
      - neither: 'inconclusive'
      - ``'tropospheric'``: reserved for diagnostic (c) (ERA5 toggle, deferred
        per D-09); this rule never returns it.

    Cutoffs are NOT criteria.py entries (this rule is for narrative
    attribution, not gating).
    """
    direction_stable = direction_stability_sigma_deg < direction_stability_cutoff_deg
    coh_correlated = magnitude_vs_coherence_pearson_r > coherence_correlation_cutoff

    if direction_stable and coh_correlated:
        return "mixed"
    if direction_stable:
        return "orbit"
    if coh_correlated:
        return "phass"
    return "inconclusive"
