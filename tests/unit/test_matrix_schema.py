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
