"""Unit tests for the validation report generator.

Plan 01-05 D-09 big-bang migration: ValidationResult is now a nested
composite (product_quality + reference_agreement). These tests assert the
report renders rows from both sub-results, uses the CRITERIA registry
labels, and propagates evaluate() pass/fail flags into the rendered table.
"""
from __future__ import annotations

import numpy as np

from subsideo.products.types import (
    CSLCValidationResult,
    DISPValidationResult,
    DSWxValidationResult,
    RTCValidationResult,
)
from subsideo.validation.report import _metrics_table_from_result, generate_report
from subsideo.validation.results import ProductQualityResult, ReferenceAgreementResult


def _make_rtc_result(
    *, rmse_db: float, correlation: float, bias_db: float, ssim: float,
) -> RTCValidationResult:
    return RTCValidationResult(
        product_quality=ProductQualityResult(
            measurements={"ssim": ssim}, criterion_ids=[],
        ),
        reference_agreement=ReferenceAgreementResult(
            measurements={
                "rmse_db": rmse_db,
                "correlation": correlation,
                "bias_db": bias_db,
            },
            criterion_ids=["rtc.rmse_db_max", "rtc.correlation_min"],
        ),
    )


class TestMetricsTable:
    """Test _metrics_table_from_result for different composite result types."""

    def test_rtc_result(self) -> None:
        result = _make_rtc_result(
            rmse_db=0.35, correlation=0.995, bias_db=-0.02, ssim=0.91,
        )
        table = _metrics_table_from_result(result)
        # Rows: ssim (product_quality, informational),
        #       rmse_db (1 criterion), correlation (1), bias_db (informational).
        # Distinct measurements: ssim + rmse_db + correlation + bias_db = 4.
        metrics = {row["metric"] for row in table}
        assert any("RMSE" in m for m in metrics)
        assert any("Correlation" in m for m in metrics)
        assert any("Bias" in m for m in metrics)
        assert any("SSIM" in m for m in metrics)

        # rmse_db row should render PASS (0.35 < 0.5)
        rmse_rows = [r for r in table if "RMSE" in r["metric"]]
        assert rmse_rows and all(r["passed"] is True for r in rmse_rows)

        # bias_db has no criterion -> passed should be None
        bias_rows = [r for r in table if "Bias" in r["metric"]]
        assert bias_rows and all(r["passed"] is None for r in bias_rows)

    def test_dswx_result(self) -> None:
        result = DSWxValidationResult(
            product_quality=ProductQualityResult(measurements={}, criterion_ids=[]),
            reference_agreement=ReferenceAgreementResult(
                measurements={
                    "f1": 0.92, "precision": 0.95, "recall": 0.89, "accuracy": 0.96,
                },
                criterion_ids=["dswx.f1_min"],
            ),
        )
        table = _metrics_table_from_result(result)
        # Must have 4 informational rows + 1 criterion row (f1 > 0.90)
        f1_rows = [r for r in table if r["metric"] == "F1"]
        assert f1_rows and all(r["passed"] is True for r in f1_rows)
        # precision / recall / accuracy are informational (no criterion)
        other = [r for r in table if r["metric"] != "F1"]
        assert all(r["passed"] is None for r in other)

    def test_cslc_product_quality_criteria(self) -> None:
        """CSLC amplitude criteria should propagate pass/fail."""
        result = CSLCValidationResult(
            product_quality=ProductQualityResult(
                measurements={"phase_rms_rad": 0.03, "coherence": 0.98},
                criterion_ids=[],
            ),
            reference_agreement=ReferenceAgreementResult(
                measurements={"amplitude_r": 0.75, "amplitude_rmse_db": 2.0},
                criterion_ids=["cslc.amplitude_r_min", "cslc.amplitude_rmse_db_max"],
            ),
        )
        table = _metrics_table_from_result(result)
        amp_r_rows = [r for r in table if "Amplitude r" in r["metric"]]
        amp_rmse_rows = [r for r in table if "Amplitude RMSE" in r["metric"]]
        assert amp_r_rows and all(r["passed"] is True for r in amp_r_rows)
        assert amp_rmse_rows and all(r["passed"] is True for r in amp_rmse_rows)

    def test_cslc_amplitude_fail(self) -> None:
        """Low amplitude r should propagate as passed=False."""
        result = CSLCValidationResult(
            product_quality=ProductQualityResult(
                measurements={"phase_rms_rad": 0.5, "coherence": 0.3},
                criterion_ids=[],
            ),
            reference_agreement=ReferenceAgreementResult(
                measurements={"amplitude_r": 0.4, "amplitude_rmse_db": 6.0},
                criterion_ids=["cslc.amplitude_r_min", "cslc.amplitude_rmse_db_max"],
            ),
        )
        table = _metrics_table_from_result(result)
        amp_r_rows = [r for r in table if "Amplitude r" in r["metric"]]
        amp_rmse_rows = [r for r in table if "Amplitude RMSE" in r["metric"]]
        assert amp_r_rows and all(r["passed"] is False for r in amp_r_rows)
        assert amp_rmse_rows and all(r["passed"] is False for r in amp_rmse_rows)

    def test_disp_criteria(self) -> None:
        result = DISPValidationResult(
            product_quality=ProductQualityResult(measurements={}, criterion_ids=[]),
            reference_agreement=ReferenceAgreementResult(
                measurements={"correlation": 0.95, "bias_mm_yr": 1.5},
                criterion_ids=["disp.correlation_min", "disp.bias_mm_yr_max"],
            ),
        )
        table = _metrics_table_from_result(result)
        corr_rows = [r for r in table if "Correlation" in r["metric"]]
        bias_rows = [r for r in table if "Bias" in r["metric"]]
        assert corr_rows and all(r["passed"] is True for r in corr_rows)
        assert bias_rows and all(r["passed"] is True for r in bias_rows)

    def test_rtc_correlation_fail(self) -> None:
        """Correlation below 0.99 should propagate as passed=False."""
        result = _make_rtc_result(
            rmse_db=0.35, correlation=0.98, bias_db=-0.02, ssim=0.91,
        )
        table = _metrics_table_from_result(result)
        corr_rows = [r for r in table if "Correlation" in r["metric"]]
        assert corr_rows and all(r["passed"] is False for r in corr_rows)

    def test_dswx_fail_criterion(self) -> None:
        result = DSWxValidationResult(
            product_quality=ProductQualityResult(measurements={}, criterion_ids=[]),
            reference_agreement=ReferenceAgreementResult(
                measurements={
                    "f1": 0.80, "precision": 0.85, "recall": 0.75, "accuracy": 0.88,
                },
                criterion_ids=["dswx.f1_min"],
            ),
        )
        table = _metrics_table_from_result(result)
        f1_rows = [r for r in table if r["metric"] == "F1"]
        assert f1_rows and all(r["passed"] is False for r in f1_rows)


class TestGenerateReport:
    """End-to-end tests for report generation."""

    def test_html_and_md_created(self, tmp_path) -> None:
        result = _make_rtc_result(
            rmse_db=0.40, correlation=0.993, bias_db=0.01, ssim=0.88,
        )
        product_arr = np.random.default_rng(0).random((10, 10)).astype(np.float32)
        reference_arr = product_arr + np.random.default_rng(1).normal(0, 0.05, (10, 10)).astype(
            np.float32
        )

        html_path, md_path = generate_report(
            "RTC-S1", result, product_arr, reference_arr, tmp_path
        )

        assert html_path.exists()
        assert md_path.exists()

    def test_html_contains_report_content(self, tmp_path) -> None:
        result = _make_rtc_result(
            rmse_db=0.40, correlation=0.993, bias_db=0.01, ssim=0.88,
        )
        product_arr = np.random.default_rng(0).random((10, 10)).astype(np.float32)
        reference_arr = product_arr + 0.01

        html_path, _ = generate_report(
            "RTC-S1", result, product_arr, reference_arr, tmp_path
        )
        html = html_path.read_text()
        assert "Validation Report" in html
        # At least one criterion row renders PASS or FAIL (not both are "--")
        assert "PASS" in html or "FAIL" in html
        assert "<svg" in html

    def test_md_contains_table(self, tmp_path) -> None:
        result = DSWxValidationResult(
            product_quality=ProductQualityResult(measurements={}, criterion_ids=[]),
            reference_agreement=ReferenceAgreementResult(
                measurements={
                    "f1": 0.92, "precision": 0.95, "recall": 0.89, "accuracy": 0.96,
                },
                criterion_ids=["dswx.f1_min"],
            ),
        )
        product_arr = np.random.default_rng(0).random((10, 10)).astype(np.float32)
        reference_arr = product_arr + 0.01

        _, md_path = generate_report(
            "DSWx-S2", result, product_arr, reference_arr, tmp_path
        )
        md = md_path.read_text()
        assert "|" in md
        assert "Validation Report" in md
        assert "F1" in md

    def test_png_figures_created(self, tmp_path) -> None:
        result = _make_rtc_result(
            rmse_db=0.40, correlation=0.993, bias_db=0.01, ssim=0.88,
        )
        product_arr = np.random.default_rng(0).random((10, 10)).astype(np.float32)
        reference_arr = product_arr + 0.01

        generate_report("RTC-S1", result, product_arr, reference_arr, tmp_path)

        png_files = list(tmp_path.glob("*.png"))
        assert len(png_files) >= 2  # diff map + scatter
