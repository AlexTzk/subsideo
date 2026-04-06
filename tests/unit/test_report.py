"""Unit tests for the validation report generator."""
from __future__ import annotations

import numpy as np
import pytest

from subsideo.products.types import DSWxValidationResult, RTCValidationResult
from subsideo.validation.report import _metrics_table_from_result, generate_report


class TestMetricsTable:
    """Test _metrics_table_from_result for different result types."""

    def test_rtc_result(self):
        result = RTCValidationResult(
            rmse_db=0.35,
            correlation=0.995,
            bias_db=-0.02,
            ssim_value=0.91,
            pass_criteria={
                "rmse_lt_0.5dB": True,
                "correlation_gt_0.99": True,
            },
        )
        table = _metrics_table_from_result(result)
        assert len(table) == 4
        metrics = {row["metric"] for row in table}
        assert "rmse_db" in metrics
        assert "correlation" in metrics
        assert "bias_db" in metrics
        assert "ssim_value" in metrics

        rmse_row = next(r for r in table if r["metric"] == "rmse_db")
        assert rmse_row["value"] == "0.3500"
        assert rmse_row["passed"] is True

    def test_dswx_result(self):
        result = DSWxValidationResult(
            f1=0.92,
            precision=0.95,
            recall=0.89,
            overall_accuracy=0.96,
            pass_criteria={"f1_gt_0.90": True},
        )
        table = _metrics_table_from_result(result)
        assert len(table) == 4
        f1_row = next(r for r in table if r["metric"] == "f1")
        assert f1_row["passed"] is True
        assert f1_row["criterion"] == "F1 > 0.90"

    def test_failing_criterion(self):
        result = DSWxValidationResult(
            f1=0.80,
            precision=0.85,
            recall=0.75,
            overall_accuracy=0.88,
            pass_criteria={"f1_gt_0.90": False},
        )
        table = _metrics_table_from_result(result)
        f1_row = next(r for r in table if r["metric"] == "f1")
        assert f1_row["passed"] is False


class TestGenerateReport:
    """End-to-end tests for report generation."""

    def test_html_and_md_created(self, tmp_path):
        result = RTCValidationResult(
            rmse_db=0.40,
            correlation=0.993,
            bias_db=0.01,
            ssim_value=0.88,
            pass_criteria={
                "rmse_lt_0.5dB": True,
                "correlation_gt_0.99": True,
            },
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

    def test_html_contains_report_content(self, tmp_path):
        result = RTCValidationResult(
            rmse_db=0.40,
            correlation=0.993,
            bias_db=0.01,
            ssim_value=0.88,
            pass_criteria={
                "rmse_lt_0.5dB": True,
                "correlation_gt_0.99": True,
            },
        )
        product_arr = np.random.default_rng(0).random((10, 10)).astype(np.float32)
        reference_arr = product_arr + 0.01

        html_path, _ = generate_report(
            "RTC-S1", result, product_arr, reference_arr, tmp_path
        )
        html = html_path.read_text()
        assert "Validation Report" in html
        assert "PASS" in html or "FAIL" in html
        assert "<svg" in html  # Inline SVG figures

    def test_md_contains_table(self, tmp_path):
        result = DSWxValidationResult(
            f1=0.92,
            precision=0.95,
            recall=0.89,
            overall_accuracy=0.96,
            pass_criteria={"f1_gt_0.90": True},
        )
        product_arr = np.random.default_rng(0).random((10, 10)).astype(np.float32)
        reference_arr = product_arr + 0.01

        _, md_path = generate_report(
            "DSWx-S2", result, product_arr, reference_arr, tmp_path
        )
        md = md_path.read_text()
        assert "|" in md
        assert "Validation Report" in md
        assert "f1" in md

    def test_png_figures_created(self, tmp_path):
        result = RTCValidationResult(
            rmse_db=0.40,
            correlation=0.993,
            bias_db=0.01,
            ssim_value=0.88,
            pass_criteria={"rmse_lt_0.5dB": True, "correlation_gt_0.99": True},
        )
        product_arr = np.random.default_rng(0).random((10, 10)).astype(np.float32)
        reference_arr = product_arr + 0.01

        generate_report("RTC-S1", result, product_arr, reference_arr, tmp_path)

        png_files = list(tmp_path.glob("*.png"))
        assert len(png_files) >= 2  # diff map + scatter
