"""Unit tests for subsideo.validation.selfconsistency."""
from __future__ import annotations

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# coherence_stats
# ---------------------------------------------------------------------------


def test_coherence_stats_keys_exact() -> None:
    """Return dict must have EXACTLY five keys -- no extras (CSLC-02 + P2.2)."""
    from subsideo.validation.selfconsistency import coherence_stats

    stack = np.full((3, 10, 10), 0.8, dtype=np.float32)
    mask = np.ones((10, 10), dtype=bool)
    stats = coherence_stats(stack, mask)
    assert set(stats.keys()) == {"mean", "median", "p25", "p75", "persistently_coherent_fraction"}


def test_coherence_stats_all_floats() -> None:
    """All five return values must be Python float (not numpy scalars)."""
    from subsideo.validation.selfconsistency import coherence_stats

    stack = np.full((3, 4, 4), 0.75, dtype=np.float32)
    mask = np.ones((4, 4), dtype=bool)
    stats = coherence_stats(stack, mask)
    for k, v in stats.items():
        assert isinstance(v, float), f"{k} should be float, got {type(v).__name__}"


def test_coherence_stats_empty_mask_returns_zeros() -> None:
    """Empty stable_mask: every field returns 0.0, no crash."""
    from subsideo.validation.selfconsistency import coherence_stats

    stack = np.full((3, 4, 4), 0.8, dtype=np.float32)
    mask = np.zeros((4, 4), dtype=bool)
    stats = coherence_stats(stack, mask)
    assert set(stats.keys()) == {"mean", "median", "p25", "p75", "persistently_coherent_fraction"}
    for v in stats.values():
        assert v == 0.0


def test_coherence_stats_persistence_threshold() -> None:
    """Half-above-threshold pixels -> persistent_fraction = 0.5."""
    from subsideo.validation.selfconsistency import coherence_stats

    # 3-layer stack of shape (3, 1, 4); baseline is 0.8 everywhere
    stack = np.full((3, 1, 4), 0.8, dtype=np.float32)
    # In IFG 0 the first two pixels drop to 0.5 (below default 0.6 threshold)
    stack[0, 0, :2] = 0.5
    mask = np.ones((1, 4), dtype=bool)
    stats = coherence_stats(stack, mask, coherence_threshold=0.6)
    # 2 of 4 pixels remain persistently coherent -> 0.5
    assert stats["persistently_coherent_fraction"] == pytest.approx(0.5)


def test_coherence_stats_persistence_custom_threshold() -> None:
    """A tighter threshold reduces persistent_fraction on the same stack."""
    from subsideo.validation.selfconsistency import coherence_stats

    stack = np.full((3, 2, 2), 0.75, dtype=np.float32)
    stack[1, 0, 0] = 0.4  # one pixel drops in one IFG
    mask = np.ones((2, 2), dtype=bool)
    # With threshold 0.5, only (0,0) fails persistence -> 3/4 = 0.75
    stats_low = coherence_stats(stack, mask, coherence_threshold=0.5)
    # With threshold 0.8, all pixels fail persistence -> 0.0
    stats_high = coherence_stats(stack, mask, coherence_threshold=0.8)
    assert stats_low["persistently_coherent_fraction"] == pytest.approx(0.75)
    assert stats_high["persistently_coherent_fraction"] == pytest.approx(0.0)


def test_coherence_stats_mean_median_p25_p75() -> None:
    """Mean/median/p25/p75 derived from per-pixel time-mean of the stack."""
    from subsideo.validation.selfconsistency import coherence_stats

    # Stack shape (2, 1, 4); per-pixel means [0.1, 0.3, 0.7, 0.9]
    stack = np.zeros((2, 1, 4), dtype=np.float32)
    stack[0, 0, :] = np.array([0.0, 0.2, 0.6, 0.8])
    stack[1, 0, :] = np.array([0.2, 0.4, 0.8, 1.0])
    mask = np.ones((1, 4), dtype=bool)
    stats = coherence_stats(stack, mask)
    # Expected time-mean per pixel: [0.1, 0.3, 0.7, 0.9]
    assert stats["mean"] == pytest.approx(0.5, abs=1e-6)
    assert stats["median"] == pytest.approx(0.5, abs=1e-6)
    assert stats["p25"] == pytest.approx(0.25, abs=1e-6)  # np percentile of [.1,.3,.7,.9] at 25
    assert stats["p75"] == pytest.approx(0.75, abs=1e-6)


def test_coherence_stats_nan_values_treated_as_zero() -> None:
    """NaN coherence entries must not propagate into stats."""
    from subsideo.validation.selfconsistency import coherence_stats

    stack = np.full((2, 2, 2), 0.8, dtype=np.float32)
    stack[0, 0, 0] = np.nan
    mask = np.ones((2, 2), dtype=bool)
    stats = coherence_stats(stack, mask)
    # Must not crash; mean must be finite
    assert np.isfinite(stats["mean"])
    assert np.isfinite(stats["median"])
    assert np.isfinite(stats["persistently_coherent_fraction"])


# ---------------------------------------------------------------------------
# residual_mean_velocity
# ---------------------------------------------------------------------------


def test_residual_mean_velocity_median_anchor() -> None:
    """Subtracting the median from a symmetric distribution yields 0 mean."""
    from subsideo.validation.selfconsistency import residual_mean_velocity

    v = np.array([[1.0, 2.0, 3.0, 4.0]], dtype=np.float32)  # median = 2.5
    mask = np.ones((1, 4), dtype=bool)
    # After subtracting median, vals = [-1.5, -0.5, 0.5, 1.5] -> mean = 0.0
    assert residual_mean_velocity(v, mask, frame_anchor="median") == pytest.approx(0.0)


def test_residual_mean_velocity_mean_anchor() -> None:
    """frame_anchor='mean' subtracts the mean -- residual is 0 by construction."""
    from subsideo.validation.selfconsistency import residual_mean_velocity

    v = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)  # mean = 2.0
    mask = np.ones((1, 3), dtype=bool)
    assert residual_mean_velocity(v, mask, frame_anchor="mean") == pytest.approx(0.0)


def test_residual_mean_velocity_all_zero_returns_zero() -> None:
    """All-zero input yields 0.0 residual."""
    from subsideo.validation.selfconsistency import residual_mean_velocity

    v = np.zeros((4, 4), dtype=np.float32)
    mask = np.ones((4, 4), dtype=bool)
    assert residual_mean_velocity(v, mask) == pytest.approx(0.0)


def test_residual_mean_velocity_non_zero_offset() -> None:
    """Skewed distribution: residual after median subtraction is non-zero."""
    from subsideo.validation.selfconsistency import residual_mean_velocity

    # Heavily skewed: median = 1, mean would be much larger
    v = np.array([[0.0, 1.0, 1.0, 10.0]], dtype=np.float32)
    mask = np.ones((1, 4), dtype=bool)
    # After subtracting median 1.0 -> [-1, 0, 0, 9] -> mean = 2.0
    assert residual_mean_velocity(v, mask, frame_anchor="median") == pytest.approx(2.0)


def test_residual_mean_velocity_empty_mask_raises() -> None:
    from subsideo.validation.selfconsistency import residual_mean_velocity

    v = np.zeros((4, 4), dtype=np.float32)
    with pytest.raises(ValueError, match="empty"):
        residual_mean_velocity(v, np.zeros((4, 4), dtype=bool))


def test_residual_mean_velocity_invalid_anchor() -> None:
    from subsideo.validation.selfconsistency import residual_mean_velocity

    v = np.zeros((4, 4), dtype=np.float32)
    mask = np.ones((4, 4), dtype=bool)
    with pytest.raises(ValueError, match="frame_anchor"):
        residual_mean_velocity(v, mask, frame_anchor="unknown")  # type: ignore[arg-type]


def test_residual_mean_velocity_nan_tolerant() -> None:
    """NaN pixels within the mask are excluded from the residual."""
    from subsideo.validation.selfconsistency import residual_mean_velocity

    v = np.array([[1.0, 2.0, np.nan, 4.0]], dtype=np.float32)
    mask = np.ones((1, 4), dtype=bool)
    # Finite values: [1, 2, 4]; median = 2; residual mean = (-1 + 0 + 2)/3 = 0.333...
    result = residual_mean_velocity(v, mask, frame_anchor="median")
    assert np.isfinite(result)


def test_coherence_stats_docstring_mentions_five_keys() -> None:
    """Docstring advertises the five keys Phase 3/4 consumers need."""
    from subsideo.validation.selfconsistency import coherence_stats

    doc = coherence_stats.__doc__ or ""
    assert "persistently_coherent_fraction" in doc
    assert "mean" in doc
    assert "median" in doc
