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


# ---------------------------------------------------------------------------
# Phase 3 additions: CSLC self-consistency rendering (D-03 + D-06 + D-11 + W8)
# ---------------------------------------------------------------------------


def _make_cslc_selfconsist_metrics(
    tmp_path: Path,
    eval_dir_name: str,
    *,
    cell_status: str = "CALIBRATING",
    any_blocker: bool = False,
    worst_coh: float = 0.78,
    worst_resid: float = 2.1,
    worst_aoi: str = "SoCal",
    worst_amp_r: float | None = 0.79,
    worst_amp_rmse_db: float | None = 3.8,
    per_aoi: list[dict] | None = None,
    egms_resid: float | None = None,
    candidate_binding: dict | None = None,
) -> Path:
    """Write a synthetic CSLCSelfConsist metrics.json to tmp_path."""
    d = tmp_path / eval_dir_name
    d.mkdir(exist_ok=True)

    if per_aoi is None:
        per_aoi = [
            {
                "aoi_name": "SoCal", "regime": "", "burst_id": None,
                "sensing_window": [], "status": "CALIBRATING",
                "attempt_index": 0, "reason": None, "attempts": [],
                "stable_mask_pixels": None,
                "product_quality": {
                    "measurements": {
                        "coherence_median_of_persistent": worst_coh,
                        "residual_mm_yr": worst_resid,
                        **({"egms_l2a_stable_ps_residual_mm_yr": egms_resid} if egms_resid else {}),
                    },
                    "criterion_ids": ["cslc.selfconsistency.coherence_min"],
                },
                "reference_agreement": (
                    {"measurements": {"amplitude_r": worst_amp_r,
                                      "amplitude_rmse_db": worst_amp_rmse_db},
                     "criterion_ids": ["cslc.amplitude_r_min"]}
                    if worst_amp_r is not None else None
                ),
                "error": None, "traceback": None,
            },
        ]

    body = {
        "schema_version": 1,
        "product_quality": {"measurements": {}, "criterion_ids": []},
        "reference_agreement": {"measurements": {}, "criterion_ids": []},
        "criterion_ids_applied": ["cslc.selfconsistency.coherence_min"],
        "runtime_conda_list_hash": None,
        "pass_count": 1,
        "total": len(per_aoi),
        "cell_status": cell_status,
        "any_blocker": any_blocker,
        "product_quality_aggregate": {
            "worst_coherence_median_of_persistent": worst_coh,
            "worst_residual_mm_yr": worst_resid,
            "worst_aoi": worst_aoi,
        },
        "reference_agreement_aggregate": {
            **({"worst_amp_r": worst_amp_r, "worst_amp_rmse_db": worst_amp_rmse_db,
                "worst_aoi": worst_aoi} if worst_amp_r is not None else {}),
        },
        "per_aoi": per_aoi,
        **({"candidate_binding": candidate_binding} if candidate_binding else {}),
    }
    p = d / "metrics.json"
    p.write_text(json.dumps(body))
    return p


def _write_cslc_selfconsist_manifest(tmp_path: Path, *, region: str = "nam") -> Path:
    dir_name = f"eval-cslc-selfconsist-{region}"
    m = tmp_path / "manifest.yml"
    m.write_text(
        yaml.safe_dump({
            "schema_version": 1,
            "cells": [{
                "product": "cslc",
                "region": region,
                "eval_script": f"run_eval_cslc_selfconsist_{region}.py",
                "cache_dir": str(tmp_path / dir_name),
                "metrics_file": str(tmp_path / dir_name / "metrics.json"),
                "meta_file": str(tmp_path / dir_name / "meta.json"),
                "conclusions_doc": f"CONCLUSIONS_CSLC_SELFCONSIST_{region.upper()}.md",
            }],
        })
    )
    return m


class TestCSLCSelfConsistRendering:
    def test_is_cslc_selfconsist_shape_detects_per_aoi(self, tmp_path: Path) -> None:
        from subsideo.validation.matrix_writer import _is_cslc_selfconsist_shape

        p_aoi = tmp_path / "with_per_aoi.json"
        p_aoi.write_text(json.dumps({"per_aoi": []}))
        assert _is_cslc_selfconsist_shape(p_aoi) is True

        p_no = tmp_path / "without_per_aoi.json"
        p_no.write_text(json.dumps({"per_burst": []}))
        assert _is_cslc_selfconsist_shape(p_no) is False

    def test_is_cslc_selfconsist_shape_prioritised_over_rtc_eu(
        self, tmp_path: Path
    ) -> None:
        """JSON with both per_aoi and per_burst -> selfconsist shape wins (D-11)."""
        from subsideo.validation.matrix_writer import (
            _is_cslc_selfconsist_shape,
            _is_rtc_eu_shape,
        )

        p = tmp_path / "both.json"
        p.write_text(json.dumps({"per_aoi": [], "per_burst": []}))
        assert _is_cslc_selfconsist_shape(p) is True
        assert _is_rtc_eu_shape(p) is True  # Also True, but selfconsist checked first

    def test_calibrating_cell_renders_italicised(self, tmp_path: Path) -> None:
        """CALIBRATING status renders with *...* italics (Phase 1 D-03)."""
        from subsideo.validation.matrix_writer import write_matrix

        manifest = _write_cslc_selfconsist_manifest(tmp_path, region="nam")
        _make_cslc_selfconsist_metrics(
            tmp_path, "eval-cslc-selfconsist-nam",
            cell_status="CALIBRATING", any_blocker=False,
            worst_coh=0.78, worst_resid=2.1, worst_aoi="SoCal",
        )
        out = tmp_path / "matrix.md"
        write_matrix(manifest, out)
        body = out.read_text()
        cslc_row = [ln for ln in body.splitlines() if "| CSLC | NAM |" in ln]
        assert len(cslc_row) == 1, f"Expected 1 CSLC NAM row, got: {cslc_row}"
        assert "*" in cslc_row[0], f"CALIBRATING should be italicised: {cslc_row[0]}"
        assert "CALIBRATING" in cslc_row[0]

    def test_calibrating_cell_pq_format(self, tmp_path: Path) -> None:
        """PQ column: 'X/N CALIBRATING | coh=A.AA / resid=B.B mm/yr (AOI)' format."""
        from subsideo.validation.matrix_writer import _render_cslc_selfconsist_cell

        metrics_path = _make_cslc_selfconsist_metrics(
            tmp_path, "eval-cslc-selfconsist-nam",
            worst_coh=0.78, worst_resid=2.1, worst_aoi="SoCal",
        )
        result = _render_cslc_selfconsist_cell(metrics_path, region="nam")
        assert result is not None
        pq_col, ra_col = result
        assert "CALIBRATING" in pq_col
        assert "coh=0.78" in pq_col
        assert "resid=2.1" in pq_col
        assert "(SoCal)" in pq_col  # W8 attribution fix
        assert "|" in pq_col  # pipe delimiter between status and metrics

    def test_blocker_mixed_rendering_with_aoi_attribution(
        self, tmp_path: Path
    ) -> None:
        """MIXED cell: '1/2 CALIBRATING, 1/2 BLOCKER | coh=... (AOI)' with U+26A0 in RA."""
        from subsideo.validation.matrix_writer import _render_cslc_selfconsist_cell

        per_aoi = [
            {
                "aoi_name": "SoCal", "regime": "", "burst_id": None,
                "sensing_window": [], "status": "CALIBRATING",
                "attempt_index": 0, "reason": None, "attempts": [],
                "stable_mask_pixels": None,
                "product_quality": {
                    "measurements": {"coherence_median_of_persistent": 0.78,
                                     "residual_mm_yr": 2.1},
                    "criterion_ids": ["cslc.selfconsistency.coherence_min"],
                },
                "reference_agreement": None,
                "error": None, "traceback": None,
            },
            {
                "aoi_name": "Mojave", "regime": "", "burst_id": None,
                "sensing_window": [], "status": "BLOCKER",
                "attempt_index": 0, "reason": "All fallbacks failed", "attempts": [],
                "stable_mask_pixels": None,
                "product_quality": None,
                "reference_agreement": None,
                "error": None, "traceback": None,
            },
        ]
        body = {
            "schema_version": 1,
            "product_quality": {"measurements": {}, "criterion_ids": []},
            "reference_agreement": {"measurements": {}, "criterion_ids": []},
            "criterion_ids_applied": [],
            "runtime_conda_list_hash": None,
            "pass_count": 1, "total": 2,
            "cell_status": "MIXED", "any_blocker": True,
            "product_quality_aggregate": {
                "worst_coherence_median_of_persistent": 0.78,
                "worst_residual_mm_yr": 2.1,
                "worst_aoi": "SoCal",
            },
            "reference_agreement_aggregate": {},
            "per_aoi": per_aoi,
        }
        metrics_path = tmp_path / "metrics_mixed.json"
        metrics_path.write_text(json.dumps(body))

        result = _render_cslc_selfconsist_cell(metrics_path, region="nam")
        assert result is not None
        pq_col, ra_col = result
        assert "1/2 CALIBRATING" in pq_col
        assert "1/2 BLOCKER" in pq_col
        assert "(SoCal)" in pq_col  # attribution of worst-case AOI
        # U+26A0 warning glyph when any_blocker=True
        assert "⚠" in pq_col or "⚠" in ra_col

    def test_eu_cell_three_numbers(self, tmp_path: Path) -> None:
        """EU cell PQ shows egms_resid= metric (three-number schema per CSLC-05)."""
        from subsideo.validation.matrix_writer import _render_cslc_selfconsist_cell

        metrics_path = _make_cslc_selfconsist_metrics(
            tmp_path, "eval-cslc-selfconsist-eu",
            cell_status="CALIBRATING", any_blocker=False,
            worst_coh=0.75, worst_resid=2.8, worst_aoi="Iberian",
            worst_amp_r=0.81, worst_amp_rmse_db=3.2,
            egms_resid=1.9,
        )
        result = _render_cslc_selfconsist_cell(metrics_path, region="eu")
        assert result is not None
        pq_col, ra_col = result
        assert "egms_resid=1.9" in pq_col

    def test_candidate_binding_pass_not_italicised(self, tmp_path: Path) -> None:
        """Candidate BINDING PASS rows render as binding evidence, not CALIBRATING."""
        from subsideo.validation.matrix_writer import _render_cslc_selfconsist_cell

        metrics_path = _make_cslc_selfconsist_metrics(
            tmp_path, "eval-cslc-selfconsist-nam",
            worst_coh=0.88, worst_resid=0.1, worst_aoi="SoCal",
            candidate_binding={"verdict": "BINDING PASS"},
        )
        result = _render_cslc_selfconsist_cell(metrics_path, region="nam")
        assert result is not None
        pq_col, ra_col = result
        assert "BINDING PASS" in pq_col
        assert "coh=0.88" in pq_col
        assert "resid=0.1 mm/yr" in pq_col
        assert "*" not in pq_col
        assert "*" not in ra_col

    def test_candidate_binding_fail_renders_verdict(self, tmp_path: Path) -> None:
        """Candidate BINDING FAIL rows expose the fail verdict explicitly."""
        from subsideo.validation.matrix_writer import _render_cslc_selfconsist_cell

        metrics_path = _make_cslc_selfconsist_metrics(
            tmp_path, "eval-cslc-selfconsist-nam",
            worst_coh=0.70, worst_resid=2.4, worst_aoi="Mojave",
            candidate_binding={"verdict": "BINDING FAIL"},
        )
        result = _render_cslc_selfconsist_cell(metrics_path, region="nam")
        assert result is not None
        pq_col, _ra_col = result
        assert "BINDING FAIL" in pq_col
        assert "*" not in pq_col

    def test_candidate_binding_blocker_renders_reason(self, tmp_path: Path) -> None:
        """Candidate BINDING BLOCKER rows include the named blocker reason."""
        from subsideo.validation.matrix_writer import _render_cslc_selfconsist_cell

        metrics_path = _make_cslc_selfconsist_metrics(
            tmp_path, "eval-cslc-selfconsist-nam",
            any_blocker=True, worst_coh=0.80, worst_resid=1.3,
            worst_aoi="Mojave/Coso-Searles", worst_amp_r=None,
            candidate_binding={
                "verdict": "BINDING BLOCKER",
                "blocker": {
                    "reason_code": "mojave_opera_frame_unavailable",
                    "evidence": {"candidate_count": 0},
                },
            },
        )
        result = _render_cslc_selfconsist_cell(metrics_path, region="nam")
        assert result is not None
        pq_col, ra_col = result
        assert "BINDING BLOCKER" in pq_col
        assert "blocker=mojave_opera_frame_unavailable" in pq_col
        assert "unavailable=mojave_opera_frame_unavailable" in ra_col
        assert "*" not in pq_col
        assert "*" not in ra_col

    def test_candidate_binding_eu_row_renders_egms_residual(
        self, tmp_path: Path
    ) -> None:
        """EU candidate rows include the EGMS residual when sidecar evidence exists."""
        from subsideo.validation.matrix_writer import _render_cslc_selfconsist_cell

        metrics_path = _make_cslc_selfconsist_metrics(
            tmp_path, "eval-cslc-selfconsist-eu",
            worst_coh=0.86, worst_resid=0.3, worst_aoi="Iberian",
            egms_resid=1.4,
            candidate_binding={"verdict": "BINDING PASS"},
        )
        result = _render_cslc_selfconsist_cell(metrics_path, region="eu")
        assert result is not None
        pq_col, _ra_col = result
        assert "BINDING PASS" in pq_col
        assert "egms_resid=1.4 mm/yr" in pq_col

    def test_legacy_no_candidate_binding_still_calibrating(
        self, tmp_path: Path
    ) -> None:
        """Legacy CSLC sidecars without candidate_binding keep old CALIBRATING style."""
        from subsideo.validation.matrix_writer import _render_cslc_selfconsist_cell

        metrics_path = _make_cslc_selfconsist_metrics(
            tmp_path, "eval-cslc-selfconsist-nam",
            worst_coh=0.78, worst_resid=2.1, worst_aoi="SoCal",
        )
        result = _render_cslc_selfconsist_cell(metrics_path, region="nam")
        assert result is not None
        pq_col, _ra_col = result
        assert "CALIBRATING" in pq_col
        assert pq_col.startswith("*")

    def test_rtc_eu_rendering_unaffected_by_phase3(self, tmp_path: Path) -> None:
        """Regression: RTC-EU cell still renders X/N PASS correctly."""
        from subsideo.validation.matrix_writer import write_matrix

        manifest = _write_rtc_eu_manifest(tmp_path)
        _write_rtc_eu_metrics(tmp_path, pass_count=5, total=5,
                              any_investigation_required=False)
        out = tmp_path / "matrix.md"
        write_matrix(manifest, out)
        body = out.read_text()
        assert "5/5 PASS" in body

    def test_makefile_references_selfconsist_scripts(self) -> None:
        """Makefile eval-cslc-nam/eu targets must reference selfconsist scripts."""
        makefile = Path("Makefile").read_text()
        assert "run_eval_cslc_selfconsist_nam.py" in makefile, (
            "Makefile eval-cslc-nam must point to run_eval_cslc_selfconsist_nam.py"
        )
        assert "run_eval_cslc_selfconsist_eu.py" in makefile, (
            "Makefile eval-cslc-eu must point to run_eval_cslc_selfconsist_eu.py"
        )
