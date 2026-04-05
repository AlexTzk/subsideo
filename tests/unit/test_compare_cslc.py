"""Unit tests for CSLC-S1 comparison module using synthetic arrays."""
from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pytest

from subsideo.validation.compare_cslc import compare_cslc


def _make_cslc_hdf5(path: Path, data: np.ndarray) -> Path:
    """Create a minimal CSLC HDF5 with ``/data/VV`` complex dataset."""
    with h5py.File(path, "w") as f:
        f.create_group("metadata")
        f.create_dataset("/data/VV", data=data.astype(np.complex64))
    return path


def test_compare_cslc_identical(tmp_path: Path) -> None:
    """Identical products should yield zero phase RMS and perfect coherence."""
    rng = np.random.default_rng(42)
    amp = rng.uniform(0.1, 1.0, (50, 50))
    phase = rng.uniform(-np.pi, np.pi, (50, 50))
    data = amp * np.exp(1j * phase)

    prod = _make_cslc_hdf5(tmp_path / "product.h5", data)
    ref = _make_cslc_hdf5(tmp_path / "reference.h5", data)

    result = compare_cslc(prod, ref)

    assert result.phase_rms_rad == pytest.approx(0.0, abs=1e-6)
    assert result.coherence == pytest.approx(1.0, abs=1e-6)
    assert result.pass_criteria["phase_rms_lt_0.05rad"] is True


def test_compare_cslc_with_phase_shift(tmp_path: Path) -> None:
    """Small (0.01 rad) phase shift should pass the 0.05 rad threshold."""
    rng = np.random.default_rng(42)
    amp = rng.uniform(0.1, 1.0, (50, 50))
    phase = rng.uniform(-np.pi, np.pi, (50, 50))
    ref_data = amp * np.exp(1j * phase)
    prod_data = ref_data * np.exp(1j * 0.01)

    prod = _make_cslc_hdf5(tmp_path / "product.h5", prod_data)
    ref = _make_cslc_hdf5(tmp_path / "reference.h5", ref_data)

    result = compare_cslc(prod, ref)

    assert result.phase_rms_rad == pytest.approx(0.01, abs=0.001)
    assert result.pass_criteria["phase_rms_lt_0.05rad"] is True


def test_compare_cslc_large_phase_fails(tmp_path: Path) -> None:
    """0.1 rad phase shift should fail the 0.05 rad threshold."""
    rng = np.random.default_rng(42)
    amp = rng.uniform(0.1, 1.0, (50, 50))
    phase = rng.uniform(-np.pi, np.pi, (50, 50))
    ref_data = amp * np.exp(1j * phase)
    prod_data = ref_data * np.exp(1j * 0.1)

    prod = _make_cslc_hdf5(tmp_path / "product.h5", prod_data)
    ref = _make_cslc_hdf5(tmp_path / "reference.h5", ref_data)

    result = compare_cslc(prod, ref)

    assert result.phase_rms_rad > 0.05
    assert result.pass_criteria["phase_rms_lt_0.05rad"] is False


def test_compare_cslc_zero_amplitude(tmp_path: Path) -> None:
    """Zero-amplitude pixels should be masked without division-by-zero."""
    rng = np.random.default_rng(42)
    amp = rng.uniform(0.1, 1.0, (50, 50))
    phase = rng.uniform(-np.pi, np.pi, (50, 50))
    data = amp * np.exp(1j * phase)
    data[0:10, 0:10] = 0.0 + 0.0j  # nodata region

    prod = _make_cslc_hdf5(tmp_path / "product.h5", data)
    ref = _make_cslc_hdf5(tmp_path / "reference.h5", data)

    result = compare_cslc(prod, ref)

    assert np.isfinite(result.phase_rms_rad)
    assert np.isfinite(result.coherence)
