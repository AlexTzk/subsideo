"""Tests for DSWx-S2 pipeline classification logic.

Tests the internal functions: _compute_diagnostic_tests, _classify_water,
_apply_scl_mask. Does NOT test run_dswx or run_dswx_from_aoi (require
real rasterio files / network).
"""
from __future__ import annotations

import numpy as np
import pytest

from subsideo.products.dswx import (
    INTERPRETED_WATER_CLASS,
    SCL_MASK_VALUES,
    _apply_scl_mask,
    _classify_water,
    _compute_diagnostic_tests,
)


class TestComputeDiagnosticTests:
    """Test the 5-bit DSWE diagnostic test computation."""

    def _make_bands(self, **overrides) -> dict[str, np.ndarray]:
        """Create default uint16 band arrays (1x1 pixel) with overrides."""
        defaults = {
            "blue": 500,
            "green": 500,
            "red": 500,
            "nir": 500,
            "swir1": 500,
            "swir2": 500,
        }
        defaults.update(overrides)
        return {k: np.array([[v]], dtype=np.uint16) for k, v in defaults.items()}

    def test_high_mndwi_sets_bit0(self):
        """High green, low swir1 -> MNDWI > 0.124 -> bit 0."""
        bands = self._make_bands(green=5000, swir1=1000)
        diag = _compute_diagnostic_tests(**bands)
        assert diag[0, 0] & 0b00001, "Test 1 (MNDWI) bit should be set"

    def test_mbsrv_gt_mbsrn_sets_bit1(self):
        """green + red > nir + swir1 -> bit 1."""
        bands = self._make_bands(green=3000, red=3000, nir=1000, swir1=1000)
        diag = _compute_diagnostic_tests(**bands)
        assert diag[0, 0] & 0b00010, "Test 2 (MBSRV>MBSRN) bit should be set"

    def test_awesh_positive_sets_bit2(self):
        """AWESH = blue + 2.5*green - 1.5*(nir+swir1) - 0.25*swir2 > 0."""
        # Make AWESH strongly positive: high blue+green, low nir/swir
        bands = self._make_bands(blue=5000, green=5000, red=500, nir=100, swir1=100, swir2=100)
        diag = _compute_diagnostic_tests(**bands)
        assert diag[0, 0] & 0b00100, "Test 3 (AWESH) bit should be set"

    def test_pswt1_sets_bit3(self):
        """Partial surface water Test 4: MNDWI > -0.44, low NIR/SWIR1, NDVI < 0.7."""
        bands = self._make_bands(
            green=2000, swir1=800, nir=1000, red=800, blue=500, swir2=500
        )
        # MNDWI = (2000 - 800) / (2000 + 800) = 0.428 > -0.44 YES
        # swir1=800 < 900 YES
        # nir=1000 < 1500 YES
        # NDVI = (1000 - 800) / (1000 + 800) = 0.111 < 0.7 YES
        diag = _compute_diagnostic_tests(**bands)
        assert diag[0, 0] & 0b01000, "Test 4 (PSWT1) bit should be set"

    def test_pswt2_sets_bit4(self):
        """Partial surface water Test 5: aggressive thresholds."""
        bands = self._make_bands(
            green=2000, swir1=500, nir=500, red=500, blue=500, swir2=500
        )
        # MNDWI = (2000-500)/(2000+500) = 0.6 > -0.5 YES
        # blue=500 < 1000 YES
        # swir1=500 < 3000 YES
        # swir2=500 < 1000 YES
        # nir=500 < 2500 YES
        diag = _compute_diagnostic_tests(**bands)
        assert diag[0, 0] & 0b10000, "Test 5 (PSWT2) bit should be set"

    def test_no_tests_pass_for_dry_land(self):
        """Typical dry land reflectance -> no DSWE tests pass."""
        # High NIR, high SWIR, low green -> land signature
        bands = self._make_bands(
            blue=1500, green=1500, red=2000, nir=4000, swir1=3500, swir2=2500
        )
        diag = _compute_diagnostic_tests(**bands)
        assert diag[0, 0] == 0, f"Expected 0 for dry land, got {diag[0, 0]:#07b}"

    def test_multi_pixel_array(self):
        """Works with multi-pixel arrays."""
        shape = (3, 4)
        bands = {
            k: np.full(shape, 500, dtype=np.uint16)
            for k in ("blue", "green", "red", "nir", "swir1", "swir2")
        }
        diag = _compute_diagnostic_tests(**bands)
        assert diag.shape == shape
        assert diag.dtype == np.uint8


class TestClassifyWater:
    """Test the diagnostic-to-water-class mapping."""

    def test_all_zeros_is_not_water(self):
        diag = np.array([[0b00000]], dtype=np.uint8)
        result = _classify_water(diag)
        assert result[0, 0] == 0

    def test_all_bits_set_is_high_confidence(self):
        diag = np.array([[0b11111]], dtype=np.uint8)
        result = _classify_water(diag)
        assert result[0, 0] == 1

    def test_known_mapping_moderate(self):
        diag = np.array([[0b00011]], dtype=np.uint8)
        result = _classify_water(diag)
        assert result[0, 0] == 2  # Moderate confidence

    def test_known_mapping_wetland(self):
        diag = np.array([[0b01000]], dtype=np.uint8)
        result = _classify_water(diag)
        assert result[0, 0] == 3  # Potential Wetland

    def test_known_mapping_low_confidence(self):
        diag = np.array([[0b10000]], dtype=np.uint8)
        result = _classify_water(diag)
        assert result[0, 0] == 4  # Low Confidence

    def test_all_32_values_covered(self):
        """All 32 diagnostic values should be in the lookup table."""
        for val in range(32):
            assert val in INTERPRETED_WATER_CLASS


class TestApplySclMask:
    """Test SCL cloud/shadow masking."""

    def test_mask_cloud_values(self):
        water = np.array([[1, 2, 3, 0]], dtype=np.uint8)
        scl = np.array([[3, 8, 9, 10]], dtype=np.uint8)
        result = _apply_scl_mask(water, scl)
        np.testing.assert_array_equal(result, [[255, 255, 255, 255]])

    def test_preserve_non_cloud(self):
        water = np.array([[1, 2, 3, 0]], dtype=np.uint8)
        scl = np.array([[4, 5, 6, 7]], dtype=np.uint8)
        result = _apply_scl_mask(water, scl)
        np.testing.assert_array_equal(result, water)

    def test_mixed_mask(self):
        water = np.array([[1, 2, 0, 3]], dtype=np.uint8)
        scl = np.array([[4, 9, 5, 3]], dtype=np.uint8)
        result = _apply_scl_mask(water, scl)
        expected = np.array([[1, 255, 0, 255]], dtype=np.uint8)
        np.testing.assert_array_equal(result, expected)

    def test_does_not_modify_input(self):
        water = np.array([[1, 2]], dtype=np.uint8)
        scl = np.array([[9, 4]], dtype=np.uint8)
        original = water.copy()
        _apply_scl_mask(water, scl)
        np.testing.assert_array_equal(water, original)

    def test_scl_mask_values_correct(self):
        """SCL mask covers shadow(3), cloud med(8), cloud high(9), cirrus(10)."""
        assert SCL_MASK_VALUES == frozenset({3, 8, 9, 10})
