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
