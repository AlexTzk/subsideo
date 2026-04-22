"""Product-quality tests for CSLC-S1 comparison: value + criterion-pass assertions."""
from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pytest

from subsideo.validation.compare_cslc import compare_cslc
from subsideo.validation.results import evaluate


def _make_cslc_hdf5(
    path: Path,
    data: np.ndarray,
    *,
    x_coords: np.ndarray | None = None,
    y_coords: np.ndarray | None = None,
) -> Path:
    """Create a minimal CSLC HDF5 with ``/data/VV`` complex dataset."""
    with h5py.File(path, "w") as f:
        f.create_group("metadata")
        f.create_dataset("/data/VV", data=data.astype(np.complex64))
        if x_coords is not None:
            f.create_dataset("/data/x_coordinates", data=x_coords)
        if y_coords is not None:
            f.create_dataset("/data/y_coordinates", data=y_coords)
    return path


def test_compare_cslc_identical(tmp_path: Path) -> None:
    """Identical products should yield perfect amplitude correlation."""
    rng = np.random.default_rng(42)
    amp = rng.uniform(0.1, 1.0, (50, 50))
    phase = rng.uniform(-np.pi, np.pi, (50, 50))
    data = amp * np.exp(1j * phase)

    prod = _make_cslc_hdf5(tmp_path / "product.h5", data)
    ref = _make_cslc_hdf5(tmp_path / "reference.h5", data)

    result = compare_cslc(prod, ref)

    pq = result.product_quality
    ra = result.reference_agreement
    assert pq.measurements["phase_rms_rad"] == pytest.approx(0.0, abs=1e-6)
    assert pq.measurements["coherence"] == pytest.approx(1.0, abs=1e-6)
    assert ra.measurements["amplitude_r"] == pytest.approx(1.0, abs=1e-6)
    passed = evaluate(ra)
    assert passed["cslc.amplitude_r_min"] is True
    assert passed["cslc.amplitude_rmse_db_max"] is True


def test_compare_cslc_with_phase_shift(tmp_path: Path) -> None:
    """Small phase shift with identical amplitudes should pass amplitude criteria."""
    rng = np.random.default_rng(42)
    amp = rng.uniform(0.1, 1.0, (50, 50))
    phase = rng.uniform(-np.pi, np.pi, (50, 50))
    ref_data = amp * np.exp(1j * phase)
    prod_data = ref_data * np.exp(1j * 0.01)

    prod = _make_cslc_hdf5(tmp_path / "product.h5", prod_data)
    ref = _make_cslc_hdf5(tmp_path / "reference.h5", ref_data)

    result = compare_cslc(prod, ref)

    pq = result.product_quality
    ra = result.reference_agreement
    assert pq.measurements["phase_rms_rad"] == pytest.approx(0.01, abs=0.001)
    passed = evaluate(ra)
    assert passed["cslc.amplitude_r_min"] is True
    assert passed["cslc.amplitude_rmse_db_max"] is True


def test_compare_cslc_large_phase_shift(tmp_path: Path) -> None:
    """Large phase shift still passes amplitude criteria (amplitudes unchanged)."""
    rng = np.random.default_rng(42)
    amp = rng.uniform(0.1, 1.0, (50, 50))
    phase = rng.uniform(-np.pi, np.pi, (50, 50))
    ref_data = amp * np.exp(1j * phase)
    prod_data = ref_data * np.exp(1j * 0.1)

    prod = _make_cslc_hdf5(tmp_path / "product.h5", prod_data)
    ref = _make_cslc_hdf5(tmp_path / "reference.h5", ref_data)

    result = compare_cslc(prod, ref)

    pq = result.product_quality
    ra = result.reference_agreement
    assert pq.measurements["phase_rms_rad"] > 0.05
    # Amplitudes are identical so amplitude criteria still pass
    passed = evaluate(ra)
    assert passed["cslc.amplitude_r_min"] is True
    assert passed["cslc.amplitude_rmse_db_max"] is True


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

    pq = result.product_quality
    ra = result.reference_agreement
    assert np.isfinite(pq.measurements["phase_rms_rad"])
    assert np.isfinite(pq.measurements["coherence"])
    assert np.isfinite(ra.measurements["amplitude_r"])


def test_compare_cslc_amplitude_mismatch(tmp_path: Path) -> None:
    """Large amplitude scaling should fail amplitude_rmse criterion."""
    rng = np.random.default_rng(42)
    amp = rng.uniform(10.0, 100.0, (50, 50))
    phase = rng.uniform(-np.pi, np.pi, (50, 50))
    ref_data = amp * np.exp(1j * phase)
    # 10x amplitude scaling = 20 dB difference
    prod_data = ref_data * 10.0

    prod = _make_cslc_hdf5(tmp_path / "product.h5", prod_data)
    ref = _make_cslc_hdf5(tmp_path / "reference.h5", ref_data)

    result = compare_cslc(prod, ref)

    ra = result.reference_agreement
    assert ra.measurements["amplitude_rmse_db"] > 4.0
    passed = evaluate(ra)
    assert passed["cslc.amplitude_rmse_db_max"] is False
    # Correlation should still be high (linear scaling preserves correlation)
    assert ra.measurements["amplitude_r"] > 0.99


def test_compare_cslc_coordinate_alignment(tmp_path: Path) -> None:
    """Products with different grid extents align by coordinates."""
    rng = np.random.default_rng(42)

    # Reference: 80x80, x=[100..495], y=[1000..210]
    ref_data = rng.uniform(10, 50, (80, 80)).astype(np.float64)
    ref_data = ref_data * np.exp(1j * rng.uniform(-np.pi, np.pi, (80, 80)))
    ref_x = np.arange(100, 500, 5.0)  # 80 pixels
    ref_y = np.arange(1000, 200, -10.0)  # 80 pixels

    # Product: 60x60, x=[200..495], y=[800..210] -- smaller, overlapping
    prod_data = ref_data[20:80, 20:80].copy()  # exact subset
    prod_x = ref_x[20:80]
    prod_y = ref_y[20:80]

    prod = _make_cslc_hdf5(
        tmp_path / "product.h5", prod_data,
        x_coords=prod_x, y_coords=prod_y,
    )
    ref = _make_cslc_hdf5(
        tmp_path / "reference.h5", ref_data,
        x_coords=ref_x, y_coords=ref_y,
    )

    result = compare_cslc(prod, ref)

    # Should align perfectly -- same data in the overlap region
    pq = result.product_quality
    ra = result.reference_agreement
    assert ra.measurements["amplitude_r"] == pytest.approx(1.0, abs=1e-3)
    assert pq.measurements["phase_rms_rad"] == pytest.approx(0.0, abs=1e-3)
    passed = evaluate(ra)
    assert passed["cslc.amplitude_r_min"] is True
    assert passed["cslc.amplitude_rmse_db_max"] is True
