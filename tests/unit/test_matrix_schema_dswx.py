"""Tests for src/subsideo/validation/matrix_schema.py — Phase 6 DSWx cell types."""
from __future__ import annotations

import math
from typing import get_args

import pytest
from pydantic import ValidationError

from subsideo.validation.matrix_schema import (
    DSWEThresholdsRef,
    DswxEUCellMetrics,
    DswxEUCellStatus,
    DswxNamCellMetrics,
    DswxNamCellStatus,
    LOOCVPerFold,
    PerAOIF1Breakdown,
    ProductQualityResultJson,
    ReferenceAgreementResultJson,
    RegressionDiagnostic,
)


def test_all_phase_6_types_importable() -> None:
    assert DswxNamCellMetrics is not None
    assert DswxEUCellMetrics is not None
    assert DSWEThresholdsRef is not None
    assert PerAOIF1Breakdown is not None
    assert LOOCVPerFold is not None
    assert RegressionDiagnostic is not None
    assert DswxNamCellStatus is not None
    assert DswxEUCellStatus is not None


def test_dswx_nam_cell_status_literal() -> None:
    args = set(get_args(DswxNamCellStatus))
    assert args == {"PASS", "FAIL", "BLOCKER"}


def test_dswx_eu_cell_status_literal() -> None:
    args = set(get_args(DswxEUCellStatus))
    assert args == {"PASS", "FAIL", "BLOCKER"}


def test_dsweresref_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        DSWEThresholdsRef.model_validate({
            "region": "nam",
            "grid_search_run_date": "2026-04-26",
            "fit_set_hash": "abc",
            "unknown_key": "garbage",  # extra=forbid rejects
        })


def test_per_aoi_f1_breakdown_shape() -> None:
    p = PerAOIF1Breakdown(
        aoi_id="alcantara",
        biome="Mediterranean reservoir",
        wet_scene_f1=0.91,
        dry_scene_f1=0.88,
        aoi_mean_f1=0.895,
    )
    assert p.aoi_id == "alcantara"
    assert p.aoi_mean_f1 == 0.895


def test_loocv_per_fold_shape_with_season() -> None:
    """B1 fix: LOOCVPerFold encodes (aoi, season) leave-one-pair-out."""
    f = LOOCVPerFold(
        fold_idx=0,
        left_out_aoi="alcantara",
        left_out_season="wet",
        refit_best_wigt=0.115,
        refit_best_awgt=0.005,
        refit_best_pswt2_mndwi=-0.48,
        test_f1=0.87,
    )
    assert f.fold_idx == 0
    assert f.left_out_season == "wet"
    assert f.test_f1 == 0.87


def test_regression_diagnostic_shape() -> None:
    r = RegressionDiagnostic(
        f1_below_regression_threshold=True,
        regression_diagnostic_required=[
            "boa_offset_check",
            "claverie_xcal_check",
            "scl_mask_audit",
        ],
        investigation_resolved=False,
    )
    assert r.f1_below_regression_threshold is True
    assert "scl_mask_audit" in r.regression_diagnostic_required


def _build_dswx_nam_pass_metrics() -> DswxNamCellMetrics:
    """Helper: build a PASS-state DswxNamCellMetrics for round-trip tests."""
    return DswxNamCellMetrics(
        product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResultJson(
            measurements={
                "f1": 0.95,
                "precision": 0.96,
                "recall": 0.94,
                "accuracy": 0.99,
            },
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
        # W2 fix: f1_full_pixels + shoreline_buffer_excluded_pixels populated:
        f1_full_pixels=0.93,
        shoreline_buffer_excluded_pixels=15234,
    )


def test_dswx_nam_cell_metrics_round_trip() -> None:
    m = _build_dswx_nam_pass_metrics()
    serialised = m.model_dump_json()
    restored = DswxNamCellMetrics.model_validate_json(serialised)
    assert restored.cell_status == "PASS"
    assert restored.region == "nam"
    assert restored.named_upgrade_path is None
    assert restored.regression.f1_below_regression_threshold is False
    assert restored.candidates_attempted == m.candidates_attempted
    # W2 fix:
    assert restored.f1_full_pixels == 0.93
    assert restored.shoreline_buffer_excluded_pixels == 15234


def test_dswx_nam_cell_metrics_named_upgrade_path_fail() -> None:
    m = _build_dswx_nam_pass_metrics()
    m_fail = m.model_copy(update={
        "cell_status": "FAIL",
        "named_upgrade_path": "ML-replacement (DSWX-V2-01)",
    })
    serialised = m_fail.model_dump_json()
    restored = DswxNamCellMetrics.model_validate_json(serialised)
    assert restored.cell_status == "FAIL"
    assert restored.named_upgrade_path == "ML-replacement (DSWX-V2-01)"


def test_dswx_nam_cell_metrics_w2_optional_diagnostics() -> None:
    """W2 fix: f1_full_pixels + shoreline_buffer_excluded_pixels accept None for BLOCKER."""
    m = _build_dswx_nam_pass_metrics()
    m_blocker = m.model_copy(update={
        "cell_status": "BLOCKER",
        "f1_full_pixels": None,
        "shoreline_buffer_excluded_pixels": None,
    })
    serialised = m_blocker.model_dump_json()
    restored = DswxNamCellMetrics.model_validate_json(serialised)
    assert restored.f1_full_pixels is None
    assert restored.shoreline_buffer_excluded_pixels is None


def _build_dswx_eu_metrics() -> DswxEUCellMetrics:
    """Helper: build a sample DswxEUCellMetrics for round-trip tests.

    B1 fix: loocv_per_fold has 10 entries (leave-one-pair-out across
    5 fit-set AOIs x 2 seasons), NOT 12.
    """
    fitset_aois = ["alcantara", "tagus", "vanern", "garda", "donana"]
    fitset_pairs = [
        (aoi, season) for aoi in fitset_aois for season in ("wet", "dry")
    ]
    assert len(fitset_pairs) == 10, "B1 fix: 5 AOIs x 2 seasons = 10 pairs"
    return DswxEUCellMetrics(
        product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResultJson(
            measurements={
                "f1": 0.91,
                "precision": 0.93,
                "recall": 0.89,
                "accuracy": 0.98,
            },
            criterion_ids=["dswx.f1_min"],
        ),
        criterion_ids_applied=["dswx.f1_min"],
        region="eu",
        thresholds_used=DSWEThresholdsRef(
            region="eu",
            grid_search_run_date="2026-04-30",
            fit_set_hash="abc123def456",
        ),
        fit_set_mean_f1=0.92,
        loocv_mean_f1=0.91,
        loocv_gap=0.01,
        loocv_per_fold=[
            LOOCVPerFold(
                fold_idx=i,
                left_out_aoi=aoi,
                left_out_season=season,
                refit_best_wigt=0.115,
                refit_best_awgt=0.005,
                refit_best_pswt2_mndwi=-0.48,
                test_f1=0.91,
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
        f1_full_pixels=0.89,  # without shoreline exclusion
        shoreline_buffer_excluded_pixels=125000,
        cell_status="PASS",
        named_upgrade_path=None,
    )


def test_dswx_eu_cell_metrics_round_trip() -> None:
    m = _build_dswx_eu_metrics()
    serialised = m.model_dump_json()
    restored = DswxEUCellMetrics.model_validate_json(serialised)
    assert restored.region == "eu"
    assert restored.cell_status == "PASS"
    assert restored.thresholds_used.region == "eu"
    assert restored.fit_set_mean_f1 == 0.92
    assert restored.loocv_gap == 0.01
    # B1 fix: 10 folds (was 12)
    assert len(restored.loocv_per_fold) == 10
    assert restored.shoreline_buffer_excluded_pixels == 125000


def test_dswx_eu_cell_metrics_named_upgrade_paths() -> None:
    """D-15: free-form string side-channel; documented values incl. W3 BLOCKER paths."""
    m = _build_dswx_eu_metrics()
    for path_text in [
        "ML-replacement (DSWX-V2-01)",
        "fit-set quality review",
        "BOA-offset / Claverie cross-cal regression",
        "grid expansion required",  # W3 BLOCKER for edge-of-grid
    ]:
        m_fail = m.model_copy(update={
            "cell_status": "FAIL",
            "named_upgrade_path": path_text,
        })
        serialised = m_fail.model_dump_json()
        restored = DswxEUCellMetrics.model_validate_json(serialised)
        assert restored.named_upgrade_path == path_text


def test_dswx_eu_cell_metrics_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        DswxEUCellMetrics.model_validate({
            **_build_dswx_eu_metrics().model_dump(),
            "unknown_key": "garbage",
        })


def test_dswx_eu_cell_metrics_blocker_state_w3() -> None:
    """W3 fix: BLOCKER pre-finalize state with NaN/empty sentinels round-trips cleanly.

    Plan 06-06 Stage 6 (edge-of-grid sentinel) and Stage 8 (LOO-CV gap gate) write
    a partial DswxEUCellMetrics with cell_status='BLOCKER' before final values are
    computed. The schema must accept NaN floats + empty lists + sentinel strings.
    """
    blocker = DswxEUCellMetrics(
        product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResultJson(
            # BLOCKER state: no F1 computed yet; measurements left empty
            measurements={},
            criterion_ids=["dswx.f1_min"],
        ),
        criterion_ids_applied=["dswx.f1_min"],
        region="eu",
        thresholds_used=DSWEThresholdsRef(
            region="eu",
            grid_search_run_date="blocker-pre-finalize",  # W3 sentinel
            fit_set_hash="",                              # W3 sentinel
        ),
        fit_set_mean_f1=float("nan"),
        loocv_mean_f1=float("nan"),
        loocv_gap=float("nan"),
        # Default empty lists per W3:
        f1_full_pixels=float("nan"),
        # shoreline_buffer_excluded_pixels uses default 0:
        cell_status="BLOCKER",
        named_upgrade_path="grid expansion required",  # Stage 6 sentinel-named path
    )
    # Round-trip:
    serialised = blocker.model_dump_json()
    restored = DswxEUCellMetrics.model_validate_json(serialised)
    assert restored.cell_status == "BLOCKER"
    assert math.isnan(restored.fit_set_mean_f1)
    assert restored.loocv_per_fold == []
    assert restored.per_aoi_breakdown == []
    assert restored.shoreline_buffer_excluded_pixels == 0
    assert restored.thresholds_used.grid_search_run_date == "blocker-pre-finalize"
    assert restored.named_upgrade_path == "grid expansion required"


def test_existing_dist_eu_cell_metrics_unchanged() -> None:
    """Phase 6 D-26: ZERO edits to existing matrix_schema types (Phase 5 D-25 lock)."""
    from subsideo.validation.matrix_schema import DistEUCellMetrics

    fields = DistEUCellMetrics.model_fields
    # Phase 5 D-25 fields must still be present:
    assert "pass_count" in fields
    assert "total" in fields
    assert "all_pass" in fields
    assert "cell_status" in fields
    assert "worst_event_id" in fields
    assert "worst_f1" in fields
    assert "any_chained_run_failed" in fields
    assert "per_event" in fields
