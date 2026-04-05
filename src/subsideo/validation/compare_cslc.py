"""CSLC-S1 product validation against OPERA N.Am. reference."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from loguru import logger

from subsideo.products.types import CSLCValidationResult


def _load_cslc_complex(hdf5_path: Path) -> np.ndarray:
    """Load complex SLC data from OPERA CSLC HDF5.

    Tries common HDF5 dataset paths used by different OPERA CSLC versions.
    Falls back to scanning the ``/data`` group for the first complex dataset.
    """
    import h5py

    candidate_paths = [
        "/data/VV",
        "/data/HH",
        "/science/SENTINEL1/CSLC/grids/VV",
        "/science/SENTINEL1/CSLC/grids/HH",
    ]
    with h5py.File(hdf5_path, "r") as f:
        for dset_path in candidate_paths:
            if dset_path in f:
                return f[dset_path][:].astype(np.complex128)
        # Fallback: first complex dataset under /data
        if "data" in f:
            for key in f["data"]:
                dset = f[f"data/{key}"]
                if hasattr(dset, "shape") and np.issubdtype(
                    dset.dtype, np.complexfloating
                ):
                    return dset[:].astype(np.complex128)
    raise ValueError(f"No complex SLC dataset found in {hdf5_path}")


def compare_cslc(
    product_path: Path, reference_path: Path
) -> CSLCValidationResult:
    """Compare CSLC-S1 product against OPERA N.Am. reference via interferometric phase.

    Per Pitfall 2 in RESEARCH.md: naive phase subtraction ``angle(prod) - angle(ref)``
    is meaningless because absolute phase depends on slant range path.  Instead,
    compute interferometric phase: ``angle(product * conj(reference))`` which cancels
    the common slant range contribution.

    Args:
        product_path: Path to subsideo CSLC HDF5.
        reference_path: Path to OPERA N.Am. CSLC HDF5 from ASF DAAC.

    Returns:
        CSLCValidationResult with phase RMS, coherence, and pass/fail.
    """
    # 1. Load complex data
    prod_complex = _load_cslc_complex(product_path)
    ref_complex = _load_cslc_complex(reference_path)

    # 2. Compute interferometric phase (cancels common slant range)
    # Per Pitfall 2: must use conjugate multiplication, not simple angle difference
    ifg = prod_complex * np.conj(ref_complex)

    # 3. Mask zero-amplitude pixels (shadow/layover)
    mask = (np.abs(prod_complex) > 0) & (np.abs(ref_complex) > 0)
    if not np.any(mask):
        logger.warning("No valid pixels for CSLC comparison")
        return CSLCValidationResult(
            phase_rms_rad=float("inf"),
            coherence=0.0,
            pass_criteria={"phase_rms_lt_0.05rad": False},
        )

    # 4. Phase RMS
    phase_diff = np.angle(ifg)
    phase_rms = float(np.sqrt(np.mean(phase_diff[mask] ** 2)))

    # 5. Coherence magnitude (mean of unit-normalized interferogram)
    ifg_masked = ifg[mask]
    ifg_norm = ifg_masked / np.abs(ifg_masked)
    coherence = float(np.abs(np.mean(ifg_norm)))

    logger.info(
        f"CSLC validation: phase_RMS={phase_rms:.4f} rad, coherence={coherence:.4f}"
    )

    return CSLCValidationResult(
        phase_rms_rad=phase_rms,
        coherence=coherence,
        pass_criteria={"phase_rms_lt_0.05rad": phase_rms < 0.05},
    )
