"""Tests for src/subsideo/products/dswx.py -- Phase 6 D-05 decomposition + D-12 deletion."""
from __future__ import annotations

import hashlib

import numpy as np
import pytest

from subsideo.products import dswx as dswx_module
from subsideo.products.dswx import (
    PSWT1_MNDWI,
    PSWT1_NDVI,
    PSWT1_NIR,
    PSWT1_SWIR1,
    PSWT2_BLUE,
    PSWT2_NIR,
    PSWT2_SWIR1,
    PSWT2_SWIR2,
    IndexBands,
    _compute_diagnostic_tests,
    compute_index_bands,
    score_water_class_from_indices,
)
from subsideo.products.dswx_thresholds import THRESHOLDS_NAM


def test_index_bands_dataclass_shape() -> None:
    assert hasattr(IndexBands, "__slots__")
    assert "mndwi" in IndexBands.__slots__
    assert "ndvi" in IndexBands.__slots__
    assert "mbsrv" in IndexBands.__slots__
    assert "mbsrn" in IndexBands.__slots__
    assert "awesh" in IndexBands.__slots__


def test_compute_index_bands_threshold_free() -> None:
    """compute_index_bands accepts 6 bands; takes NO thresholds; output deterministic."""
    rng = np.random.default_rng(42)
    blue = rng.integers(0, 10000, (50, 50), dtype=np.uint16)
    green = rng.integers(0, 10000, (50, 50), dtype=np.uint16)
    red = rng.integers(0, 10000, (50, 50), dtype=np.uint16)
    nir = rng.integers(0, 10000, (50, 50), dtype=np.uint16)
    swir1 = rng.integers(0, 10000, (50, 50), dtype=np.uint16)
    swir2 = rng.integers(0, 10000, (50, 50), dtype=np.uint16)

    indices_a = compute_index_bands(blue, green, red, nir, swir1, swir2)
    indices_b = compute_index_bands(blue, green, red, nir, swir1, swir2)

    assert isinstance(indices_a, IndexBands)
    assert indices_a.mndwi.shape == (50, 50)
    assert indices_a.mndwi.dtype == np.float32
    np.testing.assert_array_equal(indices_a.mndwi, indices_b.mndwi)
    np.testing.assert_array_equal(indices_a.awesh, indices_b.awesh)


def test_score_water_class_returns_uint8() -> None:
    rng = np.random.default_rng(123)
    blue = rng.integers(0, 10000, (50, 50), dtype=np.uint16)
    green = rng.integers(0, 10000, (50, 50), dtype=np.uint16)
    red = rng.integers(0, 10000, (50, 50), dtype=np.uint16)
    nir = rng.integers(0, 10000, (50, 50), dtype=np.uint16)
    swir1 = rng.integers(0, 10000, (50, 50), dtype=np.uint16)
    swir2 = rng.integers(0, 10000, (50, 50), dtype=np.uint16)

    indices = compute_index_bands(blue, green, red, nir, swir1, swir2)
    diag = score_water_class_from_indices(
        indices, blue=blue, nir=nir, swir1=swir1, swir2=swir2,
        thresholds=THRESHOLDS_NAM,
    )
    assert diag.dtype == np.uint8
    assert diag.shape == (50, 50)
    # 5-bit packed diagnostic: max value = 31
    assert diag.max() <= 31


def _v1_0_compute_diagnostic_tests_inline(
    blue: np.ndarray,
    green: np.ndarray,
    red: np.ndarray,
    nir: np.ndarray,
    swir1: np.ndarray,
    swir2: np.ndarray,
) -> np.ndarray:
    """v1.0 _compute_diagnostic_tests body inlined from dswx.py @ pre-Phase-6.

    Hard-coded WIGT=0.124, AWGT=0.0, PSWT2_MNDWI=-0.5 (PROTEUS defaults).
    Tests the Phase 6 D-05 + D-12 refactor produces byte-equivalent output
    for backward compatibility regression.
    """
    eps = 1e-10
    green_f = green.astype(np.float32)
    nir_f = nir.astype(np.float32)
    red_f = red.astype(np.float32)
    swir1_f = swir1.astype(np.float32)

    mndwi = (green_f - swir1_f) / (green_f + swir1_f + eps)
    ndvi = (nir_f - red_f) / (nir_f + red_f + eps)
    mbsrv = green_f + red_f
    mbsrn = nir_f + swir1_f
    awesh = (
        blue.astype(np.float32) + 2.5 * green_f
        - 1.5 * mbsrn - 0.25 * swir2.astype(np.float32)
    )

    diag = np.zeros(blue.shape, dtype=np.uint8)
    diag += np.uint8(mndwi > 0.124)          # Test 1: bit 0 (WIGT)
    diag += np.uint8(mbsrv > mbsrn) * 2      # Test 2: bit 1
    diag += np.uint8(awesh > 0.0) * 4        # Test 3: bit 2 (AWGT)

    diag += np.uint8(
        (mndwi > PSWT1_MNDWI) & (swir1 < PSWT1_SWIR1)
        & (nir < PSWT1_NIR) & (ndvi < PSWT1_NDVI)
    ) * 8

    diag += np.uint8(
        (mndwi > -0.5) & (blue < PSWT2_BLUE)  # PSWT2_MNDWI = -0.5
        & (swir1 < PSWT2_SWIR1) & (swir2 < PSWT2_SWIR2)
        & (nir < PSWT2_NIR)
    ) * 16

    return diag


def test_score_water_class_byte_equivalent_v1_0() -> None:
    """CRITICAL regression: new decomposition + THRESHOLDS_NAM = v1.0 output, byte-for-byte."""
    rng = np.random.default_rng(7)  # deterministic
    blue = rng.integers(0, 10000, (100, 100), dtype=np.uint16)
    green = rng.integers(0, 10000, (100, 100), dtype=np.uint16)
    red = rng.integers(0, 10000, (100, 100), dtype=np.uint16)
    nir = rng.integers(0, 10000, (100, 100), dtype=np.uint16)
    swir1 = rng.integers(0, 10000, (100, 100), dtype=np.uint16)
    swir2 = rng.integers(0, 10000, (100, 100), dtype=np.uint16)

    # New API (Phase 6):
    indices = compute_index_bands(blue, green, red, nir, swir1, swir2)
    diag_new = score_water_class_from_indices(
        indices, blue=blue, nir=nir, swir1=swir1, swir2=swir2,
        thresholds=THRESHOLDS_NAM,
    )

    # v1.0 inline reference:
    diag_v10 = _v1_0_compute_diagnostic_tests_inline(blue, green, red, nir, swir1, swir2)

    # Byte-for-byte match required:
    np.testing.assert_array_equal(diag_new, diag_v10)
    sha_new = hashlib.sha256(diag_new.tobytes()).hexdigest()
    sha_v10 = hashlib.sha256(diag_v10.tobytes()).hexdigest()
    assert sha_new == sha_v10


def test_backward_compat_shim_matches_decomposition() -> None:
    """_compute_diagnostic_tests(thresholds=...) composes the two public functions identically."""
    rng = np.random.default_rng(99)
    bands = {b: rng.integers(0, 10000, (30, 30), dtype=np.uint16)
             for b in ("blue", "green", "red", "nir", "swir1", "swir2")}

    # Via shim:
    diag_shim = _compute_diagnostic_tests(
        bands["blue"], bands["green"], bands["red"],
        bands["nir"], bands["swir1"], bands["swir2"],
        thresholds=THRESHOLDS_NAM,
    )

    # Via direct decomposition:
    indices = compute_index_bands(
        bands["blue"], bands["green"], bands["red"],
        bands["nir"], bands["swir1"], bands["swir2"],
    )
    diag_direct = score_water_class_from_indices(
        indices, blue=bands["blue"], nir=bands["nir"],
        swir1=bands["swir1"], swir2=bands["swir2"],
        thresholds=THRESHOLDS_NAM,
    )

    np.testing.assert_array_equal(diag_shim, diag_direct)


def test_module_constants_deleted() -> None:
    """CONTEXT D-12: WIGT, AWGT, PSWT2_MNDWI module-level constants are DELETED."""
    assert not hasattr(dswx_module, "WIGT")
    assert not hasattr(dswx_module, "AWGT")
    assert not hasattr(dswx_module, "PSWT2_MNDWI")


def test_module_constants_kept() -> None:
    """CONTEXT D-12: PSWT1_* + PSWT2_BLUE/NIR/SWIR1/SWIR2 stay at module level."""
    assert dswx_module.PSWT1_MNDWI == -0.44
    assert dswx_module.PSWT1_NIR == 1500
    assert dswx_module.PSWT1_SWIR1 == 900
    assert dswx_module.PSWT1_NDVI == 0.7
    assert dswx_module.PSWT2_BLUE == 1000
    assert dswx_module.PSWT2_NIR == 2500
    assert dswx_module.PSWT2_SWIR1 == 3000
    assert dswx_module.PSWT2_SWIR2 == 1000


def test_compute_diagnostic_tests_thresholds_required() -> None:
    """CONTEXT D-12: thresholds= keyword is REQUIRED (no default)."""
    rng = np.random.default_rng(0)
    bands = [rng.integers(0, 10000, (5, 5), dtype=np.uint16) for _ in range(6)]
    with pytest.raises(TypeError):  # missing required keyword
        _compute_diagnostic_tests(*bands)  # type: ignore[call-arg]


def test_public_api_exports() -> None:
    assert "compute_index_bands" in dswx_module.__all__
    assert "score_water_class_from_indices" in dswx_module.__all__
    assert "IndexBands" in dswx_module.__all__
