"""Tests for DSWx types and binary classification metrics."""
from __future__ import annotations

import numpy as np
import pytest

from subsideo.products.types import DSWxConfig, DSWxResult, DSWxValidationResult
from subsideo.validation.metrics import (
    f1_score,
    overall_accuracy,
    precision_score,
    recall_score,
)


# ---- DSWx type smoke tests ------------------------------------------------


class TestDSWxTypes:
    def test_dswx_config_fields(self, tmp_path):
        cfg = DSWxConfig(
            s2_band_paths={"B02": tmp_path / "b02.tif"},
            scl_path=tmp_path / "scl.tif",
            output_dir=tmp_path,
        )
        assert cfg.output_posting_m == 30.0
        assert cfg.product_version == "0.1.0"
        assert cfg.output_epsg is None

    def test_dswx_result_defaults(self, tmp_path):
        result = DSWxResult(output_path=tmp_path / "out.tif", valid=True)
        assert result.validation_errors == []

    def test_dswx_validation_result(self):
        vr = DSWxValidationResult(
            f1=0.92, precision=0.90, recall=0.94, overall_accuracy=0.95
        )
        assert vr.pass_criteria == {}


# ---- Binary classification metrics ----------------------------------------


class TestF1Score:
    def test_basic(self):
        pred = np.array([1, 1, 0, 0])
        ref = np.array([1, 0, 1, 0])
        assert f1_score(pred, ref) == pytest.approx(0.5)

    def test_perfect(self):
        pred = np.array([1, 1, 0, 0])
        ref = np.array([1, 1, 0, 0])
        assert f1_score(pred, ref) == pytest.approx(1.0)

    def test_all_zero_predicted(self):
        pred = np.array([0, 0, 0, 0])
        ref = np.array([1, 1, 0, 0])
        assert f1_score(pred, ref) == 0.0

    def test_all_zero_both(self):
        pred = np.array([0, 0, 0, 0])
        ref = np.array([0, 0, 0, 0])
        assert f1_score(pred, ref) == 0.0


class TestPrecisionScore:
    def test_basic(self):
        pred = np.array([1, 1, 0, 0])
        ref = np.array([1, 0, 1, 0])
        # TP=1, FP=1 -> 0.5
        assert precision_score(pred, ref) == pytest.approx(0.5)

    def test_no_positives(self):
        pred = np.array([0, 0, 0])
        ref = np.array([1, 1, 0])
        assert precision_score(pred, ref) == 0.0


class TestRecallScore:
    def test_basic(self):
        pred = np.array([1, 1, 0, 0])
        ref = np.array([1, 0, 1, 0])
        # TP=1, FN=1 -> 0.5
        assert recall_score(pred, ref) == pytest.approx(0.5)

    def test_no_true_positives(self):
        pred = np.array([0, 0, 0])
        ref = np.array([1, 1, 0])
        assert recall_score(pred, ref) == 0.0


class TestOverallAccuracy:
    def test_basic(self):
        pred = np.array([1, 1, 0, 0])
        ref = np.array([1, 0, 1, 0])
        # correct: pos 0 (1==1), pos 3 (0==0) => 2/4 = 0.5
        assert overall_accuracy(pred, ref) == pytest.approx(0.5)

    def test_perfect(self):
        pred = np.array([1, 0, 1])
        ref = np.array([1, 0, 1])
        assert overall_accuracy(pred, ref) == pytest.approx(1.0)

    def test_empty(self):
        pred = np.array([])
        ref = np.array([])
        assert overall_accuracy(pred, ref) == 0.0
