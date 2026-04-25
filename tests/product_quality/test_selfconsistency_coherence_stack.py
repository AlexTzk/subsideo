"""Phase 4 selfconsistency public compute_ifg_coherence_stack helper -- unit tests.

Promotes the helper formerly defined inner-scope in
run_eval_cslc_selfconsist_nam.py to public selfconsistency.py API. Tests
exercise the round-trip behaviour on synthetic CSLC stacks plus the raise-
on-misuse contract.
"""
from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pytest

from subsideo.validation.selfconsistency import compute_ifg_coherence_stack


def _write_synthetic_cslc(
    path: Path,
    *,
    height: int = 32,
    width: int = 32,
    seed: int = 0,
    nan_block: tuple[slice, slice] | None = None,
) -> Path:
    """Write a synthetic complex CSLC HDF5 at /data/VV.

    Amplitude ~ 1.0 with small Gaussian phase noise; high inter-epoch
    coherence on a sequential pair built from two such files using the
    same seed (epoch-coherent). NaN block is optional for the NaN-safety
    test.
    """
    rng = np.random.default_rng(seed=seed)
    amp = np.ones((height, width), dtype=np.float32)
    phase = (0.05 * rng.standard_normal((height, width))).astype(np.float32)
    arr = (amp * np.exp(1j * phase)).astype(np.complex64)
    if nan_block is not None:
        arr = arr.copy()
        arr[nan_block] = np.complex64(np.nan + 1j * np.nan)
    with h5py.File(path, "w") as f:
        grp = f.create_group("data")
        grp.create_dataset("VV", data=arr)
    return path


def test_compute_ifg_coherence_stack_round_trip(tmp_path: Path) -> None:
    """3-epoch synthetic stack -> 2 finite coherence IFGs in (0, 1]."""
    paths = [
        _write_synthetic_cslc(tmp_path / f"epoch_{i:02d}.h5", seed=i)
        for i in range(3)
    ]
    coh = compute_ifg_coherence_stack(sorted(paths), boxcar_px=5)
    assert coh.shape == (2, 32, 32)
    assert coh.dtype == np.float32
    assert np.isfinite(coh).all()
    assert (coh >= 0.0).all()
    assert (coh <= 1.0001).all()  # tiny float tolerance over the [0,1] range
    # High-coherence synthetic stack -> mean coherence well above 0.5
    assert float(coh.mean()) > 0.5


def test_compute_ifg_coherence_stack_requires_two_epochs(tmp_path: Path) -> None:
    only = _write_synthetic_cslc(tmp_path / "only.h5", seed=0)
    with pytest.raises(ValueError, match="requires >=2 epochs"):
        compute_ifg_coherence_stack([only], boxcar_px=5)


def test_compute_ifg_coherence_stack_handles_nan_block(tmp_path: Path) -> None:
    """NaN in input must NOT propagate globally to the coherence output.

    Mirrors the NaN-replacement-with-zero behaviour the original inner-scope
    helper relied on for SoCal's parallelogram-burst footprint (~64% NaN
    coverage of the rectangular CSLC grid).
    """
    paths = [
        _write_synthetic_cslc(
            tmp_path / f"epoch_{i:02d}.h5",
            seed=i,
            nan_block=(slice(0, 8), slice(0, 8)),
        )
        for i in range(3)
    ]
    coh = compute_ifg_coherence_stack(sorted(paths), boxcar_px=5)
    # Most of the output is finite (the helper replaces NaN with 0+0j before
    # the boxcar; only the 8x8 corner -- a small fraction -- is degenerate).
    finite_fraction = float(np.isfinite(coh).sum()) / coh.size
    assert finite_fraction > 0.5
