"""Tests for src/subsideo/validation/compare_dswx.py — Phase 6 D-16 shoreline buffer + D-25 JRC retry."""
# ruff: noqa: E501
from __future__ import annotations

import contextlib
import inspect
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest


def test_compute_shoreline_buffer_mask_one_pixel_ring() -> None:
    """Half-water/half-land array produces a 1-2 px boundary band."""
    from subsideo.validation.compare_dswx import _compute_shoreline_buffer_mask

    arr = np.zeros((20, 20), dtype=np.uint8)
    arr[:10, :] = 1  # top half is water
    # bottom half is land (0)

    mask = _compute_shoreline_buffer_mask(arr, iterations=1)

    assert mask.shape == arr.shape
    assert mask.dtype == bool
    # The boundary is between rows 9 and 10. With iterations=1 dilation,
    # the buffer captures rows 8-11 (4 rows = 2*width pixels of True).
    assert mask.sum() > 0
    # Pure-water rows (0-7) should be False; pure-land rows (12-19) should be False.
    assert not mask[0:7, :].any(), "pure water rows should NOT be in shoreline buffer"
    assert not mask[13:20, :].any(), "pure land rows should NOT be in shoreline buffer"
    # Boundary rows (8-11) should have True pixels.
    assert mask[8:12, :].sum() > 0


def test_compute_shoreline_buffer_mask_all_water() -> None:
    from subsideo.validation.compare_dswx import _compute_shoreline_buffer_mask

    arr = np.ones((10, 10), dtype=np.uint8)
    mask = _compute_shoreline_buffer_mask(arr, iterations=1)
    assert not mask.any(), "all-water array has no shoreline boundary"


def test_compute_shoreline_buffer_mask_all_land() -> None:
    from subsideo.validation.compare_dswx import _compute_shoreline_buffer_mask

    arr = np.zeros((10, 10), dtype=np.uint8)
    mask = _compute_shoreline_buffer_mask(arr, iterations=1)
    assert not mask.any(), "all-land array has no shoreline boundary"


def test_compute_shoreline_buffer_mask_one_pixel_thickness() -> None:
    """1-pixel buffer iterations=1 means buffer is at most 2 pixels wide on each side."""
    from subsideo.validation.compare_dswx import _compute_shoreline_buffer_mask

    arr = np.zeros((100, 100), dtype=np.uint8)
    arr[:50, :] = 1  # boundary at row 49/50

    mask = _compute_shoreline_buffer_mask(arr, iterations=1)

    # Boundary buffer should NOT extend more than ~2 rows above + 2 below = 4 rows.
    boundary_extent_top = mask[:50, :].sum(axis=1).nonzero()[0]
    boundary_extent_bottom = mask[50:, :].sum(axis=1).nonzero()[0]
    # Conservative: buffer is bounded within 2 px of the boundary.
    assert len(boundary_extent_top) <= 2, (
        f"buffer extends too far into water: {boundary_extent_top}"
    )
    assert len(boundary_extent_bottom) <= 2, (
        f"buffer extends too far into land: {boundary_extent_bottom}"
    )


def test_dswx_validation_result_diagnostics_attribute_b2() -> None:
    """B2 fix: DSWxValidationResult.diagnostics defaults to None (backward compat)."""
    from subsideo.products.types import (
        DSWxValidationDiagnostics,
        DSWxValidationResult,
    )
    from subsideo.validation.results import (
        ProductQualityResult,
        ReferenceAgreementResult,
    )

    # v1.0 caller pattern (no diagnostics argument):
    result = DSWxValidationResult(
        product_quality=ProductQualityResult(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResult(
            measurements={"f1": 0.92, "precision": 0.93, "recall": 0.91, "accuracy": 0.99},
            criterion_ids=["dswx.f1_min"],
        ),
    )
    assert result.diagnostics is None, "B2 fix: diagnostics defaults to None (backward compat)"

    # Phase 6 caller pattern (diagnostics populated):
    result_with_diag = DSWxValidationResult(
        product_quality=ProductQualityResult(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResult(
            measurements={"f1": 0.91},
            criterion_ids=["dswx.f1_min"],
        ),
        diagnostics=DSWxValidationDiagnostics(
            f1_full_pixels=0.89,
            shoreline_buffer_excluded_pixels=125000,
        ),
    )
    assert result_with_diag.diagnostics is not None
    assert result_with_diag.diagnostics.f1_full_pixels == 0.89
    assert result_with_diag.diagnostics.shoreline_buffer_excluded_pixels == 125000


def test_jrc_retry_refactor_via_harness(tmp_path: Path) -> None:
    """_fetch_jrc_tile invokes harness.download_reference_with_retry with source='jrc'."""
    from subsideo.validation import compare_dswx

    with patch(
        "subsideo.validation.harness.download_reference_with_retry"
    ) as mock_download:
        mock_download.return_value = tmp_path / "fake_tile.tif"
        # Ensure the file doesn't exist so the cache-hit branch is skipped
        with contextlib.suppress(Exception):
            compare_dswx._fetch_jrc_tile(
                "https://jeodpp.jrc.ec.europa.eu/test.tif",
                tmp_path / "jrc_test_cache",
            )

        if mock_download.called:
            call_kwargs = mock_download.call_args.kwargs
            assert call_kwargs.get("source") == "jrc", (
                f"_fetch_jrc_tile must call download_reference_with_retry(source='jrc'), "
                f"got: {call_kwargs}"
            )
        else:
            # If local_path.exists() returned True (cache hit), download was skipped.
            # Verify via code inspection that the refactor landed.
            source = inspect.getsource(compare_dswx._fetch_jrc_tile)
            assert "download_reference_with_retry" in source
            assert "source=\"jrc\"" in source or "source='jrc'" in source


def test_jrc_404_propagates_as_none(tmp_path: Path) -> None:
    """ReferenceDownloadError with 404 -> None (preserve v1.0 tile-out-of-coverage semantics)."""
    from subsideo.validation import compare_dswx
    from subsideo.validation.harness import ReferenceDownloadError

    with patch(
        "subsideo.validation.harness.download_reference_with_retry"
    ) as mock_download:
        mock_download.side_effect = ReferenceDownloadError(
            source="jrc", status=404, url="https://jeodpp.jrc.ec.europa.eu/missing.tif"
        )
        result = compare_dswx._fetch_jrc_tile(
            "https://jeodpp.jrc.ec.europa.eu/missing.tif",
            tmp_path / "jrc_404_test",
        )
        assert result is None, "_fetch_jrc_tile must propagate 404 as None"


def test_jrc_other_error_reraises(tmp_path: Path) -> None:
    """Non-404 ReferenceDownloadError must re-raise (e.g., exhausted retries)."""
    from subsideo.validation import compare_dswx
    from subsideo.validation.harness import ReferenceDownloadError

    with patch(
        "subsideo.validation.harness.download_reference_with_retry"
    ) as mock_download:
        mock_download.side_effect = ReferenceDownloadError(
            source="jrc",
            status=503,
            url="https://jeodpp.jrc.ec.europa.eu/flaky.tif",
        )
        with pytest.raises(ReferenceDownloadError):
            compare_dswx._fetch_jrc_tile(
                "https://jeodpp.jrc.ec.europa.eu/flaky.tif",
                tmp_path / "jrc_retry_exhausted_test",
            )
