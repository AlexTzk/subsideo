"""CSLC-S1 product validation against OPERA N.Am. reference.

Uses amplitude-based metrics (correlation, RMSE in dB) rather than
interferometric phase coherence.  Phase comparison between different
isce3 major versions (e.g. 0.15 vs 0.25) yields random noise because
the phase reference computation changed.  See CONCLUSIONS_CSLC_N_AM.md
Section 5 and .planning/research/PITFALLS.md Pitfall 15 for details.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from loguru import logger

from subsideo.products.types import CSLCValidationResult


def _load_cslc_complex(hdf5_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load complex SLC data and coordinates from OPERA CSLC HDF5.

    Returns
    -------
    tuple of (complex_data, x_coordinates, y_coordinates)
    """
    import h5py

    candidate_paths = [
        "/data/VV",
        "/data/HH",
        "/science/SENTINEL1/CSLC/grids/VV",
        "/science/SENTINEL1/CSLC/grids/HH",
    ]
    with h5py.File(hdf5_path, "r") as f:
        data = None
        for dset_path in candidate_paths:
            if dset_path in f:
                data = f[dset_path][:].astype(np.complex128)
                break
        # Fallback: first complex dataset under /data
        if data is None and "data" in f:
            for key in f["data"]:
                dset = f[f"data/{key}"]
                if hasattr(dset, "shape") and np.issubdtype(
                    dset.dtype, np.complexfloating
                ):
                    data = dset[:].astype(np.complex128)
                    break
        if data is None:
            raise ValueError(f"No complex SLC dataset found in {hdf5_path}")

        # Load coordinates if available (try both compass and OPERA layouts)
        x_coords = y_coords = None
        coord_candidates = [
            ("data/x_coordinates", "data/y_coordinates"),
            ("science/SENTINEL1/CSLC/grids/x_coordinates",
             "science/SENTINEL1/CSLC/grids/y_coordinates"),
        ]
        for x_path, y_path in coord_candidates:
            if x_path in f and y_path in f:
                x_coords = f[x_path][:]
                y_coords = f[y_path][:]
                break

    return data, x_coords, y_coords


def compare_cslc(
    product_path: Path, reference_path: Path
) -> CSLCValidationResult:
    """Compare CSLC-S1 product against OPERA N.Am. reference.

    Computes both interferometric phase metrics and amplitude-based metrics.
    Phase coherence between different isce3/compass versions is expected to
    be low due to differences in phase screen computation (carrier phase,
    flattening).  Amplitude-based metrics are version-independent and serve
    as the primary validation criteria.

    Args:
        product_path: Path to subsideo CSLC HDF5.
        reference_path: Path to OPERA N.Am. CSLC HDF5 from ASF DAAC.

    Returns:
        CSLCValidationResult with amplitude and phase metrics.
    """
    # 1. Load complex data with coordinates
    prod_complex, prod_x, prod_y = _load_cslc_complex(product_path)
    ref_complex, ref_x, ref_y = _load_cslc_complex(reference_path)

    # 2. Align grids if shapes differ (find overlapping region by coordinates)
    if prod_complex.shape != ref_complex.shape:
        if prod_x is not None and ref_x is not None and prod_y is not None and ref_y is not None:
            logger.info(
                "Product shape {} != reference shape {}; aligning by coordinates",
                prod_complex.shape, ref_complex.shape,
            )
            x_overlap_min = max(prod_x[0], ref_x[0])
            x_overlap_max = min(prod_x[-1], ref_x[-1])
            # y decreases (north→south): overlap north = min of the two
            # northern edges, overlap south = max of the two southern edges
            y_overlap_max = min(prod_y[0], ref_y[0])
            y_overlap_min = max(prod_y[-1], ref_y[-1])

            px0 = int(np.searchsorted(prod_x, x_overlap_min))
            px1 = int(np.searchsorted(prod_x, x_overlap_max, side='right'))
            py0 = int(np.searchsorted(-prod_y, -y_overlap_max))
            py1 = int(np.searchsorted(-prod_y, -y_overlap_min, side='right'))

            rx0 = int(np.searchsorted(ref_x, x_overlap_min))
            rx1 = int(np.searchsorted(ref_x, x_overlap_max, side='right'))
            ry0 = int(np.searchsorted(-ref_y, -y_overlap_max))
            ry1 = int(np.searchsorted(-ref_y, -y_overlap_min, side='right'))

            prod_complex = prod_complex[py0:py1, px0:px1]
            ref_complex = ref_complex[ry0:ry1, rx0:rx1]

            min_rows = min(prod_complex.shape[0], ref_complex.shape[0])
            min_cols = min(prod_complex.shape[1], ref_complex.shape[1])
            prod_complex = prod_complex[:min_rows, :min_cols]
            ref_complex = ref_complex[:min_rows, :min_cols]

            logger.info("Aligned shapes: product={}, reference={}", prod_complex.shape, ref_complex.shape)

    # 3. Mask invalid pixels
    mask = ~np.isnan(prod_complex) & ~np.isnan(ref_complex) & (np.abs(prod_complex) > 0) & (np.abs(ref_complex) > 0)
    if not np.any(mask):
        logger.warning("No valid pixels for CSLC comparison")
        return CSLCValidationResult(
            phase_rms_rad=float("inf"),
            coherence=0.0,
            amplitude_correlation=0.0,
            amplitude_rmse_db=float("inf"),
            pass_criteria={
                "amplitude_correlation_gt_0.6": False,
                "amplitude_rmse_lt_2dB": False,
            },
        )

    prod_masked = prod_complex[mask]
    ref_masked = ref_complex[mask]

    # 4. Amplitude-based metrics (version-independent)
    prod_amp = np.abs(prod_masked)
    ref_amp = np.abs(ref_masked)

    amp_corr = float(np.corrcoef(prod_amp, ref_amp)[0, 1])

    # RMSE in dB — use minimum amplitude threshold to avoid noise-dominated
    # pixels where tiny differences produce huge dB spreads
    amp_thresh = 5.0
    strong_mask = (prod_amp > amp_thresh) & (ref_amp > amp_thresh)
    if np.sum(strong_mask) > 100:
        prod_db = 20 * np.log10(prod_amp[strong_mask])
        ref_db = 20 * np.log10(ref_amp[strong_mask])
    else:
        prod_db = 20 * np.log10(prod_amp)
        ref_db = 20 * np.log10(ref_amp)
    amp_rmse_db = float(np.sqrt(np.mean((prod_db - ref_db) ** 2)))

    # 5. Phase metrics (informational — low coherence expected across isce3 versions)
    ifg = prod_masked * np.conj(ref_masked)
    phase_diff = np.angle(ifg)
    phase_rms = float(np.sqrt(np.mean(phase_diff ** 2)))

    ifg_norm = ifg / np.abs(ifg)
    coherence = float(np.abs(np.mean(ifg_norm)))

    logger.info(
        "CSLC validation: amp_corr={:.4f}, amp_RMSE={:.2f} dB, "
        "phase_RMS={:.4f} rad, coherence={:.4f}",
        amp_corr, amp_rmse_db, phase_rms, coherence,
    )

    return CSLCValidationResult(
        phase_rms_rad=phase_rms,
        coherence=coherence,
        amplitude_correlation=amp_corr,
        amplitude_rmse_db=amp_rmse_db,
        pass_criteria={
            "amplitude_correlation_gt_0.6": amp_corr > 0.6,
            "amplitude_rmse_lt_4dB": amp_rmse_db < 4.0,
        },
    )
