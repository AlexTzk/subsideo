"""Tests for src/subsideo/validation/matrix_writer.py — Phase 6 D-27 DSWx render branches."""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from subsideo.validation.matrix_schema import (
    DSWEThresholdsRef,
    DswxEUCellMetrics,
    DswxNamCellMetrics,
    LOOCVPerFold,
    PerAOIF1Breakdown,
    ProductQualityResultJson,
    ReferenceAgreementResultJson,
    RegressionDiagnostic,
)
from subsideo.validation.matrix_writer import (
    _is_dswx_eu_shape,
    _is_dswx_nam_shape,
    _render_dswx_eu_cell,
    _render_dswx_nam_cell,
)


@pytest.fixture
def dswx_nam_metrics_pass() -> DswxNamCellMetrics:
    return DswxNamCellMetrics(
        product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResultJson(
            measurements={"f1": 0.95, "precision": 0.96, "recall": 0.94, "accuracy": 0.99},
            criterion_ids=["dswx.f1_min"],
        ),
        criterion_ids_applied=["dswx.f1_min"],
        selected_aoi="Lake Tahoe (CA)",
        selected_scene_id="S2A_MSIL2A_20210716T185919_N0500_R013_T10SFH_xxx",
        cloud_cover_pct=8.3,
        candidates_attempted=[
            {"aoi_name": "Lake Tahoe (CA)", "scenes_found": 5, "cloud_min": 8.3},
        ],
        region="nam",
        cell_status="PASS",
        named_upgrade_path=None,
        regression=RegressionDiagnostic(
            f1_below_regression_threshold=False,
            regression_diagnostic_required=[],
            investigation_resolved=False,
        ),
        f1_full_pixels=0.93,
        shoreline_buffer_excluded_pixels=15234,
    )


@pytest.fixture
def dswx_eu_metrics_pass() -> DswxEUCellMetrics:
    fitset_aois = ["alcantara", "tagus", "vanern", "garda", "donana"]
    fitset_pairs = [(aoi, season) for aoi in fitset_aois for season in ("wet", "dry")]
    return DswxEUCellMetrics(
        product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResultJson(
            measurements={"f1": 0.92, "precision": 0.93, "recall": 0.91, "accuracy": 0.98},
            criterion_ids=["dswx.f1_min"],
        ),
        criterion_ids_applied=["dswx.f1_min"],
        region="eu",
        thresholds_used=DSWEThresholdsRef(
            region="eu",
            grid_search_run_date="2026-04-30",
            fit_set_hash="abc123def456",
        ),
        fit_set_mean_f1=0.93,
        loocv_mean_f1=0.92,
        loocv_gap=0.012,
        loocv_per_fold=[
            LOOCVPerFold(
                fold_idx=i,
                left_out_aoi=aoi,
                left_out_season=season,
                refit_best_wigt=0.115,
                refit_best_awgt=0.005,
                refit_best_pswt2_mndwi=-0.48,
                test_f1=0.92,
            )
            for i, (aoi, season) in enumerate(fitset_pairs)
        ],
        per_aoi_breakdown=[
            PerAOIF1Breakdown(
                aoi_id="alcantara",
                biome="Mediterranean reservoir",
                wet_scene_f1=0.93,
                dry_scene_f1=0.91,
                aoi_mean_f1=0.92,
            ),
        ],
        f1_full_pixels=0.89,
        shoreline_buffer_excluded_pixels=125000,
        cell_status="PASS",
        named_upgrade_path=None,
    )


def test_is_dswx_nam_shape_positive(
    tmp_path: Path, dswx_nam_metrics_pass: DswxNamCellMetrics
) -> None:
    p = tmp_path / "metrics.json"
    p.write_text(dswx_nam_metrics_pass.model_dump_json())
    assert _is_dswx_nam_shape(p) is True


def test_is_dswx_nam_shape_negative_disp(tmp_path: Path) -> None:
    p = tmp_path / "metrics.json"
    p.write_text(json.dumps({"ramp_attribution": {"sigma_dir": 12.0}, "region": "nam"}))
    assert _is_dswx_nam_shape(p) is False


def test_is_dswx_eu_shape_positive(tmp_path: Path, dswx_eu_metrics_pass: DswxEUCellMetrics) -> None:
    p = tmp_path / "metrics.json"
    p.write_text(dswx_eu_metrics_pass.model_dump_json())
    assert _is_dswx_eu_shape(p) is True


def test_is_dswx_eu_shape_negative_dist(tmp_path: Path) -> None:
    p = tmp_path / "metrics.json"
    p.write_text(json.dumps({"per_event": [], "cell_status": "PASS"}))
    assert _is_dswx_eu_shape(p) is False


def test_render_dswx_nam_pass(tmp_path: Path, dswx_nam_metrics_pass: DswxNamCellMetrics) -> None:
    p = tmp_path / "metrics.json"
    p.write_text(dswx_nam_metrics_pass.model_dump_json())
    result = _render_dswx_nam_cell(p)
    assert result is not None
    pq, ra = result
    assert pq == "—"
    assert "F1=0.950" in ra
    assert "PASS" in ra
    assert "Lake Tahoe" in ra
    assert "named upgrade" not in ra
    assert "INVESTIGATION_REQUIRED" not in ra


def test_render_dswx_nam_fail_with_named_upgrade(
    tmp_path: Path, dswx_nam_metrics_pass: DswxNamCellMetrics
) -> None:
    fail = dswx_nam_metrics_pass.model_copy(
        update={
            "cell_status": "FAIL",
            "named_upgrade_path": "ML-replacement (DSWX-V2-01)",
        }
    )
    fail.reference_agreement.measurements["f1"] = 0.87
    p = tmp_path / "metrics.json"
    p.write_text(fail.model_dump_json())
    result = _render_dswx_nam_cell(p)
    assert result is not None
    _, ra = result
    assert "F1=0.870 FAIL" in ra
    assert "ML-replacement (DSWX-V2-01)" in ra


def test_render_dswx_nam_investigation_required(
    tmp_path: Path, dswx_nam_metrics_pass: DswxNamCellMetrics
) -> None:
    """F1 < 0.85 and not yet resolved -> INVESTIGATION_REQUIRED inline."""
    inv = dswx_nam_metrics_pass.model_copy(
        update={
            "cell_status": "FAIL",
            "named_upgrade_path": "BOA-offset / Claverie cross-cal regression",
            "regression": RegressionDiagnostic(
                f1_below_regression_threshold=True,
                regression_diagnostic_required=["boa_offset_check", "claverie_xcal_check"],
                investigation_resolved=False,
            ),
        }
    )
    inv.reference_agreement.measurements["f1"] = 0.83
    p = tmp_path / "metrics.json"
    p.write_text(inv.model_dump_json())
    result = _render_dswx_nam_cell(p)
    assert result is not None
    _, ra = result
    assert "F1=0.830 FAIL" in ra
    assert "INVESTIGATION_REQUIRED" in ra


def test_render_dswx_eu_pass(tmp_path: Path, dswx_eu_metrics_pass: DswxEUCellMetrics) -> None:
    p = tmp_path / "metrics.json"
    p.write_text(dswx_eu_metrics_pass.model_dump_json())
    result = _render_dswx_eu_cell(p)
    assert result is not None
    pq, ra = result
    assert pq == "—"
    assert "F1=0.920 PASS" in ra
    assert "LOOCV gap=0.012" in ra
    assert "named upgrade" not in ra


def test_render_dswx_eu_fail_with_ml_replacement(
    tmp_path: Path, dswx_eu_metrics_pass: DswxEUCellMetrics
) -> None:
    fail = dswx_eu_metrics_pass.model_copy(
        update={
            "cell_status": "FAIL",
            "named_upgrade_path": "ML-replacement (DSWX-V2-01)",
        }
    )
    fail.reference_agreement.measurements["f1"] = 0.87
    p = tmp_path / "metrics.json"
    p.write_text(fail.model_dump_json())
    result = _render_dswx_eu_cell(p)
    assert result is not None
    _, ra = result
    assert "F1=0.870 FAIL" in ra
    assert "ML-replacement (DSWX-V2-01)" in ra
    assert "LOOCV gap=" in ra


def test_dispatch_order_dswx_after_dist() -> None:
    """CONTEXT D-27 + Phase 5 D-24 amendment + W6 invariant: full strict ordering chain.

    W6 fix asserts the complete order after Plan 06-04 insertion:
        disp_call < dist_eu_call < dist_nam_call < dswx_nam_call < dswx_eu_call
        < cslc_selfconsist_call < rtc_eu_call
    """
    from subsideo.validation import matrix_writer as mw

    source = inspect.getsource(mw)
    # Find line indices of dispatch shape-discriminator calls in write_matrix:
    disp_idx = source.find("_is_disp_cell_shape(metrics_path)")
    dist_eu_idx = source.find("_is_dist_eu_shape(metrics_path)")
    dist_nam_idx = source.find("_is_dist_nam_shape(metrics_path)")
    dswx_nam_idx = source.find("_is_dswx_nam_shape(metrics_path)")
    dswx_eu_idx = source.find("_is_dswx_eu_shape(metrics_path)")
    cslc_selfconsist_idx = source.find("_is_cslc_selfconsist_shape(metrics_path)")
    rtc_eu_idx = source.find("_is_rtc_eu_shape(metrics_path)")

    assert disp_idx > 0, "disp dispatch missing"
    assert dist_eu_idx > 0, "dist_eu dispatch missing"
    assert dist_nam_idx > 0, "dist_nam dispatch missing"
    assert dswx_nam_idx > 0, "dswx_nam dispatch missing"
    assert dswx_eu_idx > 0, "dswx_eu dispatch missing"
    assert cslc_selfconsist_idx > 0, "cslc_selfconsist dispatch missing"
    assert rtc_eu_idx > 0, "rtc_eu dispatch missing"

    # Strict ordering chain:
    assert disp_idx < dist_eu_idx, (
        f"disp must dispatch before dist_eu (disp={disp_idx}, dist_eu={dist_eu_idx})"
    )
    assert dist_eu_idx < dist_nam_idx, "dist_eu must dispatch before dist_nam"
    assert dist_nam_idx < dswx_nam_idx, "dist_nam must dispatch before dswx_nam (D-27)"
    assert dswx_nam_idx < dswx_eu_idx, "dswx_nam must dispatch before dswx_eu"
    # W6 fix: lock dswx_eu BEFORE cslc_selfconsist + rtc_eu:
    assert dswx_eu_idx < cslc_selfconsist_idx, (
        f"dswx_eu must be before cslc_selfconsist; "
        f"got dswx_eu={dswx_eu_idx}, cslc={cslc_selfconsist_idx}"
    )
    assert dswx_eu_idx < rtc_eu_idx, (
        f"dswx_eu must be before rtc_eu; "
        f"got dswx_eu={dswx_eu_idx}, rtc_eu={rtc_eu_idx}"
    )


def test_existing_render_branches_unchanged() -> None:
    """Plan 06-04 ZERO edits to existing render branches (Phase 1 D-09 + Phase 5 D-25 lock)."""
    from subsideo.validation import matrix_writer as mw

    # Verify existing renderers are still importable + callable:
    assert hasattr(mw, "_render_dist_eu_cell")
    assert hasattr(mw, "_render_dist_nam_deferred_cell")
    assert hasattr(mw, "_render_disp_cell")
    assert hasattr(mw, "_is_disp_cell_shape")
    assert hasattr(mw, "_is_dist_eu_shape")
    assert hasattr(mw, "_is_dist_nam_shape")
    assert hasattr(mw, "_is_cslc_selfconsist_shape")
    assert hasattr(mw, "_is_rtc_eu_shape")
