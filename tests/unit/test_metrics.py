"""Tests for validation metric functions: rmse, spatial_correlation, bias, ssim."""
import numpy as np
import pytest

from subsideo.validation.metrics import bias, rmse, spatial_correlation, ssim


class TestRMSE:
    def test_rmse_exact(self):
        predicted = np.array([1.0, 2.0, 3.0])
        reference = np.array([1.1, 2.1, 3.1])
        assert rmse(predicted, reference) == pytest.approx(0.1, abs=1e-10)

    def test_rmse_identical(self):
        a = np.array([1.0, 2.0, 3.0])
        assert rmse(a, a) == 0.0

    def test_rmse_nan_masking(self):
        predicted = np.array([1.0, np.nan, 3.0])
        reference = np.array([1.1, 2.1, 3.1])
        # Only indices 0 and 2 are valid: diffs are 0.1, 0.1
        assert rmse(predicted, reference) == pytest.approx(0.1, abs=1e-10)


class TestSpatialCorrelation:
    def test_spatial_correlation_perfect(self):
        a = np.arange(100, dtype=float)
        assert spatial_correlation(a, a) == pytest.approx(1.0, abs=1e-10)

    def test_spatial_correlation_known(self):
        # Linear relationship: y = 2x + 1 -> r = 1.0
        x = np.arange(50, dtype=float)
        y = 2.0 * x + 1.0
        assert spatial_correlation(y, x) == pytest.approx(1.0, abs=1e-10)

    def test_spatial_correlation_nan(self):
        x = np.array([1.0, np.nan, 3.0, 4.0, 5.0])
        y = np.array([2.0, 3.0, np.nan, 8.0, 10.0])
        # Valid pairs: (1,2), (4,8), (5,10) -> perfect linear
        assert spatial_correlation(x, y) == pytest.approx(1.0, abs=1e-10)


class TestBias:
    def test_bias_positive(self):
        predicted = np.array([2.0, 3.0, 4.0])
        reference = np.array([1.0, 2.0, 3.0])
        assert bias(predicted, reference) == pytest.approx(1.0)

    def test_bias_nan_masking(self):
        predicted = np.array([2.0, np.nan, 4.0])
        reference = np.array([1.0, 2.0, 3.0])
        # Valid pairs: (2,1), (4,3) -> bias = 1.0
        assert bias(predicted, reference) == pytest.approx(1.0)


class TestSSIM:
    def test_ssim_identical(self):
        rng = np.random.default_rng(42)
        a = rng.random((64, 64))
        assert ssim(a, a) == pytest.approx(1.0, abs=1e-6)

    def test_ssim_different(self):
        rng = np.random.default_rng(42)
        a = rng.random((64, 64))
        b = rng.random((64, 64))
        result = ssim(a, b)
        assert 0.0 < result < 1.0

    def test_ssim_nan_crop(self):
        rng = np.random.default_rng(42)
        a = rng.random((64, 64))
        b = a.copy()
        # Add NaN border
        a[:5, :] = np.nan
        a[-5:, :] = np.nan
        result = ssim(a, b)
        # Should still compute a valid SSIM on the cropped region
        assert 0.0 < result <= 1.0
