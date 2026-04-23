"""Unit tests for subsideo.validation.matrix_schema (Pydantic v2 sidecars)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError


def test_metrics_json_round_trip() -> None:
    from subsideo.validation.matrix_schema import (
        MetricsJson,
        ProductQualityResultJson,
        ReferenceAgreementResultJson,
    )

    obj = MetricsJson(
        product_quality=ProductQualityResultJson(
            measurements={"coherence": 0.73},
            criterion_ids=["cslc.selfconsistency.coherence_min"],
        ),
        reference_agreement=ReferenceAgreementResultJson(
            measurements={"rmse_db": 0.045, "correlation": 0.998},
            criterion_ids=["rtc.rmse_db_max", "rtc.correlation_min"],
        ),
        criterion_ids_applied=[
            "cslc.selfconsistency.coherence_min",
            "rtc.rmse_db_max",
            "rtc.correlation_min",
        ],
    )
    js = obj.model_dump_json()
    loaded = MetricsJson.model_validate_json(js)
    assert loaded == obj


def test_meta_json_required_fields() -> None:
    from subsideo.validation.matrix_schema import MetaJson

    # Missing git_sha -> ValidationError
    with pytest.raises(ValidationError):
        MetaJson(
            git_dirty=False,
            run_started_iso="",
            run_duration_s=0.0,
            python_version="",
            platform="",
        )  # type: ignore[call-arg]


def test_meta_json_full_construction() -> None:
    from subsideo.validation.matrix_schema import MetaJson

    m = MetaJson(
        git_sha="abc123",
        git_dirty=False,
        run_started_iso="2026-04-21T00:00:00Z",
        run_duration_s=1234.5,
        python_version="3.11.7",
        platform="darwin-arm64",
        input_hashes={"safe_zip_1": "sha256:..."},
    )
    assert m.schema_version == 1
    assert m.git_sha == "abc123"


def test_metrics_json_extra_forbidden() -> None:
    from subsideo.validation.matrix_schema import MetricsJson

    with pytest.raises(ValidationError):
        MetricsJson.model_validate_json(json.dumps({"unknown_field": 42}))


def test_metrics_json_default_empty() -> None:
    from subsideo.validation.matrix_schema import MetricsJson

    m = MetricsJson()
    assert m.product_quality.measurements == {}
    assert m.reference_agreement.measurements == {}
    assert m.criterion_ids_applied == []
    assert m.runtime_conda_list_hash is None
    assert m.schema_version == 1


def test_meta_json_schema_version_default() -> None:
    """Loading JSON missing ``schema_version`` uses default (1)."""
    from subsideo.validation.matrix_schema import MetaJson

    payload = json.dumps(
        {
            "git_sha": "deadbeef",
            "git_dirty": True,
            "run_started_iso": "2026-04-22T00:00:00Z",
            "run_duration_s": 42.0,
            "python_version": "3.11.7",
            "platform": "darwin-arm64",
        }
    )
    m = MetaJson.model_validate_json(payload)
    assert m.schema_version == 1


def test_product_quality_result_json_extra_forbidden() -> None:
    """Unknown field on nested sub-schema raises."""
    from subsideo.validation.matrix_schema import ProductQualityResultJson

    with pytest.raises(ValidationError):
        ProductQualityResultJson.model_validate_json(
            json.dumps({"measurements": {}, "criterion_ids": [], "bogus": 1})
        )


# ---------------------------------------------------------------------------
# Phase 2 additions: BurstResult + RTCEUCellMetrics (D-09, D-10)
# ---------------------------------------------------------------------------


def test_burst_result_round_trip() -> None:
    from subsideo.validation.matrix_schema import (
        BurstResult,
        ReferenceAgreementResultJson,
    )

    obj = BurstResult(
        burst_id="t088_186752_iw2",
        regime="Alpine",
        lat=46.52,
        max_relief_m=2800.0,
        cached=False,
        status="PASS",
        product_quality=None,
        reference_agreement=ReferenceAgreementResultJson(
            measurements={"rmse_db": 0.08, "correlation": 0.9995, "bias_db": 0.0},
            criterion_ids=["rtc.rmse_db_max", "rtc.correlation_min"],
        ),
        investigation_required=False,
        investigation_reason=None,
        error=None,
        traceback=None,
    )
    js = obj.model_dump_json()
    loaded = BurstResult.model_validate_json(js)
    assert loaded == obj


def test_burst_result_forbids_extra() -> None:
    from subsideo.validation.matrix_schema import BurstResult

    with pytest.raises(ValidationError):
        BurstResult(
            burst_id="t088_186752_iw2",
            regime="Alpine",
            status="PASS",
            some_extra_field=123,
        )  # type: ignore[call-arg]


def test_burst_result_status_literal() -> None:
    from subsideo.validation.matrix_schema import BurstResult

    with pytest.raises(ValidationError):
        BurstResult(
            burst_id="t088_186752_iw2",
            regime="Alpine",
            status="INVALID",  # type: ignore[arg-type]
        )


def test_burst_result_regime_literal() -> None:
    from subsideo.validation.matrix_schema import BurstResult

    with pytest.raises(ValidationError):
        BurstResult(
            burst_id="t088_186752_iw2",
            regime="Martian",  # type: ignore[arg-type]
            status="PASS",
        )


def test_rtc_eu_cell_metrics_round_trip() -> None:
    from subsideo.validation.matrix_schema import (
        BurstResult,
        ReferenceAgreementResultJson,
        RTCEUCellMetrics,
    )

    b1 = BurstResult(
        burst_id="t088_186752_iw2",
        regime="Alpine",
        lat=46.52,
        max_relief_m=2800.0,
        cached=False,
        status="PASS",
        reference_agreement=ReferenceAgreementResultJson(
            measurements={"rmse_db": 0.08, "correlation": 0.9995, "bias_db": 0.0},
            criterion_ids=["rtc.rmse_db_max", "rtc.correlation_min"],
        ),
    )
    b2 = BurstResult(
        burst_id="t117_249422_iw2",
        regime="TemperateFlat",
        lat=44.50,
        max_relief_m=80.0,
        cached=True,
        status="PASS",
        reference_agreement=ReferenceAgreementResultJson(
            measurements={"rmse_db": 0.05, "correlation": 0.9999, "bias_db": 0.0},
            criterion_ids=["rtc.rmse_db_max", "rtc.correlation_min"],
        ),
    )
    obj = RTCEUCellMetrics(
        pass_count=2,
        total=2,
        all_pass=True,
        any_investigation_required=False,
        reference_agreement_aggregate={
            "worst_rmse_db": 0.08,
            "worst_r": 0.9995,
            "worst_burst_id": "t088_186752_iw2",
        },
        per_burst=[b1, b2],
    )
    js = obj.model_dump_json()
    loaded = RTCEUCellMetrics.model_validate_json(js)
    assert loaded == obj


def test_rtc_eu_cell_metrics_extends_metrics_json() -> None:
    from subsideo.validation.matrix_schema import MetricsJson, RTCEUCellMetrics

    obj = RTCEUCellMetrics(
        pass_count=0,
        total=1,
        all_pass=False,
        any_investigation_required=False,
        per_burst=[],
    )
    assert isinstance(obj, MetricsJson)


def test_rtc_eu_cell_metrics_total_ge_1() -> None:
    from subsideo.validation.matrix_schema import RTCEUCellMetrics

    with pytest.raises(ValidationError):
        RTCEUCellMetrics(
            pass_count=0,
            total=0,
            all_pass=False,
            any_investigation_required=False,
            per_burst=[],
        )
