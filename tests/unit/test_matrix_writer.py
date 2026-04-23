"""Unit tests for subsideo.validation.matrix_writer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


def _write_manifest(tmp_path: Path) -> Path:
    m = tmp_path / "manifest.yml"
    m.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "cells": [
                    {
                        "product": "rtc",
                        "region": "nam",
                        "eval_script": "run_eval.py",
                        "cache_dir": str(tmp_path / "eval-rtc"),
                        "metrics_file": str(tmp_path / "eval-rtc" / "metrics.json"),
                        "meta_file": str(tmp_path / "eval-rtc" / "meta.json"),
                        "conclusions_doc": "CONCLUSIONS_N_AM.md",
                    },
                    {
                        "product": "cslc",
                        "region": "nam",
                        "eval_script": "run_eval_cslc.py",
                        "cache_dir": str(tmp_path / "eval-cslc"),
                        "metrics_file": str(tmp_path / "eval-cslc" / "metrics.json"),
                        "meta_file": str(tmp_path / "eval-cslc" / "meta.json"),
                        "conclusions_doc": "CONCLUSIONS_CSLC_N_AM.md",
                    },
                ],
            }
        )
    )
    return m


def test_missing_sidecars_render_run_failed(tmp_path: Path) -> None:
    from subsideo.validation.matrix_writer import write_matrix

    manifest = _write_manifest(tmp_path)
    out = tmp_path / "matrix.md"
    write_matrix(manifest, out)
    body = out.read_text()
    # Both cells have missing metrics.json -> both render RUN_FAILED
    assert body.count("RUN_FAILED") >= 2


def test_populated_cell_rendering(tmp_path: Path) -> None:
    from subsideo.validation.matrix_writer import write_matrix

    manifest = _write_manifest(tmp_path)
    # Populate RTC cell with metrics.json
    rtc_dir = tmp_path / "eval-rtc"
    rtc_dir.mkdir()
    rtc_metrics = {
        "schema_version": 1,
        "product_quality": {"measurements": {}, "criterion_ids": []},
        "reference_agreement": {
            "measurements": {"rmse_db": 0.045, "correlation": 0.998},
            "criterion_ids": ["rtc.rmse_db_max", "rtc.correlation_min"],
        },
        "criterion_ids_applied": ["rtc.rmse_db_max", "rtc.correlation_min"],
        "runtime_conda_list_hash": None,
    }
    (rtc_dir / "metrics.json").write_text(json.dumps(rtc_metrics))

    out = tmp_path / "matrix.md"
    write_matrix(manifest, out)
    body = out.read_text()
    # RTC row should show measurements + PASS verdicts for BINDING gates
    assert "RTC" in body and "NAM" in body
    assert "0.045" in body
    assert "PASS" in body
    # rtc.rmse_db_max threshold echoed: comparator + threshold visible
    assert "< 0.5" in body


def test_calibrating_cell_italicised(tmp_path: Path) -> None:
    from subsideo.validation.matrix_writer import write_matrix

    manifest = _write_manifest(tmp_path)
    cslc_dir = tmp_path / "eval-cslc"
    cslc_dir.mkdir()
    cslc_metrics = {
        "schema_version": 1,
        "product_quality": {
            "measurements": {"coherence": 0.73, "residual_mm_yr": 2.1},
            "criterion_ids": [
                "cslc.selfconsistency.coherence_min",
                "cslc.selfconsistency.residual_mm_yr_max",
            ],
        },
        "reference_agreement": {"measurements": {}, "criterion_ids": []},
        "criterion_ids_applied": [
            "cslc.selfconsistency.coherence_min",
            "cslc.selfconsistency.residual_mm_yr_max",
        ],
        "runtime_conda_list_hash": None,
    }
    (cslc_dir / "metrics.json").write_text(json.dumps(cslc_metrics))

    out = tmp_path / "matrix.md"
    write_matrix(manifest, out)
    body = out.read_text()
    # CALIBRATING cells render in italics: look for `*...*` wrapping the measurement
    for line in body.splitlines():
        if "CSLC" in line and "NAM" in line:
            assert "*" in line, f"CSLC row should be italicised: {line}"
            assert "CALIBRATING" in line, f"CSLC row should tag CALIBRATING: {line}"
            break
    else:
        pytest.fail("CSLC row not found in matrix output")


def test_matrix_writer_cli(tmp_path: Path) -> None:
    """CLI entry point runs with --manifest + --out args."""
    import sys

    from subsideo.validation.matrix_writer import main

    manifest = _write_manifest(tmp_path)
    out = tmp_path / "matrix.md"
    argv_backup = sys.argv
    sys.argv = ["matrix_writer", "--manifest", str(manifest), "--out", str(out)]
    try:
        rc = main()
    finally:
        sys.argv = argv_backup
    assert rc == 0
    assert out.exists()


def test_malformed_metrics_json_renders_run_failed(tmp_path: Path) -> None:
    """Invalid JSON in metrics.json -> cell renders RUN_FAILED, does not crash."""
    from subsideo.validation.matrix_writer import write_matrix

    manifest = _write_manifest(tmp_path)
    rtc_dir = tmp_path / "eval-rtc"
    rtc_dir.mkdir()
    (rtc_dir / "metrics.json").write_text("{not valid json")
    out = tmp_path / "matrix.md"
    write_matrix(manifest, out)
    body = out.read_text()
    assert "RUN_FAILED" in body


def test_threshold_echo_binding_pass(tmp_path: Path) -> None:
    """BINDING criterion in PASS state echoes comparator + threshold + PASS tag."""
    from subsideo.validation.matrix_writer import write_matrix

    manifest = _write_manifest(tmp_path)
    rtc_dir = tmp_path / "eval-rtc"
    rtc_dir.mkdir()
    rtc_metrics = {
        "schema_version": 1,
        "product_quality": {"measurements": {}, "criterion_ids": []},
        "reference_agreement": {
            "measurements": {"rmse_db": 0.10, "correlation": 0.995},
            "criterion_ids": ["rtc.rmse_db_max", "rtc.correlation_min"],
        },
        "criterion_ids_applied": ["rtc.rmse_db_max", "rtc.correlation_min"],
        "runtime_conda_list_hash": None,
    }
    (rtc_dir / "metrics.json").write_text(json.dumps(rtc_metrics))
    out = tmp_path / "matrix.md"
    write_matrix(manifest, out)
    body = out.read_text()
    # Measurement value (0.1) printed alongside criterion threshold (0.5) with comparator (<) + PASS
    assert "0.1" in body
    assert "< 0.5" in body
    assert "PASS" in body
    # Correlation side: 0.995 > 0.99
    assert "0.995" in body
    assert "> 0.99" in body
    # BINDING cells are NOT italicised
    for line in body.splitlines():
        if "RTC" in line and "NAM" in line:
            # no italics markers on a pure-BINDING row
            assert "*" not in line, f"BINDING-only row should not be italicised: {line}"
            break


def test_threshold_echo_binding_fail(tmp_path: Path) -> None:
    """BINDING criterion in FAIL state echoes FAIL tag."""
    from subsideo.validation.matrix_writer import write_matrix

    manifest = _write_manifest(tmp_path)
    rtc_dir = tmp_path / "eval-rtc"
    rtc_dir.mkdir()
    rtc_metrics = {
        "schema_version": 1,
        "product_quality": {"measurements": {}, "criterion_ids": []},
        "reference_agreement": {
            "measurements": {"rmse_db": 0.8, "correlation": 0.95},
            "criterion_ids": ["rtc.rmse_db_max", "rtc.correlation_min"],
        },
        "criterion_ids_applied": ["rtc.rmse_db_max", "rtc.correlation_min"],
        "runtime_conda_list_hash": None,
    }
    (rtc_dir / "metrics.json").write_text(json.dumps(rtc_metrics))
    out = tmp_path / "matrix.md"
    write_matrix(manifest, out)
    body = out.read_text()
    assert "FAIL" in body


# -- Plan 02-03 additions: RTC-EU render branch + INVESTIGATION_TRIGGER filter --


def _write_rtc_eu_manifest(tmp_path: Path) -> Path:
    m = tmp_path / "manifest.yml"
    m.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "cells": [
                    {
                        "product": "rtc",
                        "region": "eu",
                        "eval_script": "run_eval_rtc_eu.py",
                        "cache_dir": str(tmp_path / "eval-rtc-eu"),
                        "metrics_file": str(
                            tmp_path / "eval-rtc-eu" / "metrics.json"
                        ),
                        "meta_file": str(
                            tmp_path / "eval-rtc-eu" / "meta.json"
                        ),
                        "conclusions_doc": "CONCLUSIONS_RTC_EU.md",
                    },
                ],
            }
        )
    )
    return m


def _write_rtc_eu_metrics(
    tmp_path: Path,
    pass_count: int,
    total: int,
    any_investigation_required: bool,
) -> None:
    rtc_dir = tmp_path / "eval-rtc-eu"
    rtc_dir.mkdir(exist_ok=True)
    # Build a minimal per_burst list matching pass_count/total.
    per_burst = []
    for i in range(total):
        is_pass = i < pass_count
        per_burst.append(
            {
                "burst_id": f"t{i:03d}_000000_iw1",
                "regime": "Alpine",
                "lat": 46.0,
                "max_relief_m": 2800.0,
                "cached": False,
                "status": "PASS" if is_pass else "FAIL",
                "product_quality": None,
                "reference_agreement": {
                    "measurements": {
                        "rmse_db": 0.05 if is_pass else 0.6,
                        "correlation": 0.9999 if is_pass else 0.98,
                        "bias_db": 0.0,
                    },
                    "criterion_ids": [
                        "rtc.rmse_db_max", "rtc.correlation_min"
                    ],
                },
                "investigation_required": False,
                "investigation_reason": None,
                "error": None,
                "traceback": None,
            }
        )
    body = {
        "schema_version": 1,
        "product_quality": {"measurements": {}, "criterion_ids": []},
        "reference_agreement": {
            "measurements": {},
            "criterion_ids": [],
        },
        "criterion_ids_applied": [
            "rtc.rmse_db_max", "rtc.correlation_min"
        ],
        "runtime_conda_list_hash": None,
        "pass_count": pass_count,
        "total": total,
        "all_pass": pass_count == total,
        "any_investigation_required": any_investigation_required,
        "reference_agreement_aggregate": {
            "worst_rmse_db": 0.1,
            "worst_r": 0.999,
            "worst_burst_id": "t000_000000_iw1",
        },
        "per_burst": per_burst,
    }
    (rtc_dir / "metrics.json").write_text(json.dumps(body))


def test_rtc_eu_cell_renders_x_of_n_pass(tmp_path: Path) -> None:
    from subsideo.validation.matrix_writer import write_matrix

    manifest = _write_rtc_eu_manifest(tmp_path)
    _write_rtc_eu_metrics(tmp_path, pass_count=5, total=5,
                          any_investigation_required=False)
    out = tmp_path / "matrix.md"
    write_matrix(manifest, out)
    body = out.read_text()
    assert "5/5 PASS" in body
    # Warning glyph must NOT appear when any_investigation_required is False.
    assert "⚠" not in body


def test_rtc_eu_cell_renders_with_investigation_warning(tmp_path: Path) -> None:
    from subsideo.validation.matrix_writer import write_matrix

    manifest = _write_rtc_eu_manifest(tmp_path)
    _write_rtc_eu_metrics(tmp_path, pass_count=5, total=5,
                          any_investigation_required=True)
    out = tmp_path / "matrix.md"
    write_matrix(manifest, out)
    body = out.read_text()
    assert "5/5 PASS ⚠" in body


def test_rtc_eu_cell_partial_pass(tmp_path: Path) -> None:
    from subsideo.validation.matrix_writer import write_matrix

    manifest = _write_rtc_eu_manifest(tmp_path)
    _write_rtc_eu_metrics(tmp_path, pass_count=4, total=5,
                          any_investigation_required=False)
    out = tmp_path / "matrix.md"
    write_matrix(manifest, out)
    body = out.read_text()
    # Expected: "4/5 PASS (1 FAIL)"
    assert "4/5 PASS (1 FAIL)" in body


def test_rtc_eu_cell_zero_pass(tmp_path: Path) -> None:
    from subsideo.validation.matrix_writer import write_matrix

    manifest = _write_rtc_eu_manifest(tmp_path)
    _write_rtc_eu_metrics(tmp_path, pass_count=0, total=5,
                          any_investigation_required=False)
    out = tmp_path / "matrix.md"
    write_matrix(manifest, out)
    body = out.read_text()
    assert "0/5 PASS (5 FAIL)" in body


def test_rtc_eu_pq_column_is_em_dash(tmp_path: Path) -> None:
    from subsideo.validation.matrix_writer import write_matrix

    manifest = _write_rtc_eu_manifest(tmp_path)
    _write_rtc_eu_metrics(tmp_path, pass_count=5, total=5,
                          any_investigation_required=False)
    out = tmp_path / "matrix.md"
    write_matrix(manifest, out)
    body = out.read_text()
    # The RTC-EU row must have an em-dash in the PQ column position.
    # Row format: "| RTC | EU | — | 5/5 PASS |"
    rtc_row = [ln for ln in body.splitlines() if "| RTC | EU |" in ln]
    assert len(rtc_row) == 1
    # The PQ column is between the 3rd and 4th pipe characters.
    parts = [p.strip() for p in rtc_row[0].split("|")]
    # parts = ['', 'RTC', 'EU', '—', '5/5 PASS', '']
    assert parts[3] == "—"


def test_investigation_trigger_filtered_from_cell_column() -> None:
    from subsideo.validation.matrix_writer import _render_cell_column
    from subsideo.validation.results import ReferenceAgreementResult

    # A result erroneously listing an INVESTIGATION_TRIGGER criterion
    # alongside a BINDING criterion must render only the BINDING verdict.
    result = ReferenceAgreementResult(
        measurements={
            "rmse_db": 0.05,
            "correlation": 0.9995,
            "investigation_rmse_db": 0.05,  # bogus key; should not render
        },
        criterion_ids=[
            "rtc.rmse_db_max",                      # BINDING
            "rtc.eu.investigation_rmse_db_min",     # INVESTIGATION_TRIGGER -- filtered
        ],
    )
    rendered = _render_cell_column(result)
    # Must render the BINDING criterion verdict (rmse_db=0.05 < 0.5 PASS)
    assert "0.05" in rendered
    assert "PASS" in rendered
    # Must NOT render any >= 0.15 threshold or INVESTIGATION wording.
    assert "0.15" not in rendered
    assert "INVESTIGATION" not in rendered.upper()


def test_investigation_trigger_only_returns_em_dash() -> None:
    from subsideo.validation.matrix_writer import _render_cell_column
    from subsideo.validation.results import ReferenceAgreementResult

    # A result with ONLY INVESTIGATION_TRIGGER criteria (after filter,
    # effectively empty) must render as "—" -- same as the no-criteria path.
    result = ReferenceAgreementResult(
        measurements={"investigation_rmse_db": 0.05},
        criterion_ids=["rtc.eu.investigation_rmse_db_min"],
    )
    assert _render_cell_column(result) == "—"


def test_schema_detection_uses_per_burst_key(tmp_path: Path) -> None:
    """_is_rtc_eu_shape returns True when metrics.json has a per_burst key.

    Covers behavior Test H (schema detection discriminator). The pure helper
    is tested directly without invoking write_matrix, so the assertion is on
    the return value rather than on a rendered matrix cell.
    """
    from subsideo.validation.matrix_writer import _is_rtc_eu_shape

    # metrics.json with per_burst key -> RTC-EU shape detected.
    with_per_burst_path = tmp_path / "with_per_burst.json"
    with_per_burst = {"per_burst": [], "pass_count": 0, "total": 0}
    with_per_burst_path.write_text(json.dumps(with_per_burst))
    assert _is_rtc_eu_shape(with_per_burst_path) is True

    # metrics.json without per_burst key -> default path.
    without_per_burst_path = tmp_path / "without_per_burst.json"
    without_per_burst = {"metric": 0.5, "passed": True}
    without_per_burst_path.write_text(json.dumps(without_per_burst))
    assert _is_rtc_eu_shape(without_per_burst_path) is False


def test_non_rtc_eu_cells_render_unchanged(tmp_path: Path) -> None:
    """Regression: default MetricsJson cell (no per_burst) uses _render_cell_column."""
    from subsideo.validation.matrix_writer import write_matrix

    manifest = _write_manifest(tmp_path)  # existing helper; RTC NAM + CSLC NAM cells
    rtc_dir = tmp_path / "eval-rtc"
    rtc_dir.mkdir(exist_ok=True)
    (rtc_dir / "metrics.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "product_quality": {"measurements": {}, "criterion_ids": []},
                "reference_agreement": {
                    "measurements": {
                        "rmse_db": 0.045,
                        "correlation": 0.9999,
                        "bias_db": 0.0,
                    },
                    "criterion_ids": [
                        "rtc.rmse_db_max", "rtc.correlation_min"
                    ],
                },
                "criterion_ids_applied": [
                    "rtc.rmse_db_max", "rtc.correlation_min"
                ],
                "runtime_conda_list_hash": None,
            }
        )
    )
    out = tmp_path / "matrix.md"
    write_matrix(manifest, out)
    body = out.read_text()
    # Must render with the default cell-column format: numeric values + verdicts.
    assert "0.045" in body
    assert "0.9999" in body
    assert "PASS" in body
    # MUST NOT render as X/N PASS (that's RTC-EU format).
    assert "/1 PASS" not in body
    assert "/5 PASS" not in body
