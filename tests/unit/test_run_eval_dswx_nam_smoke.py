"""Static-invariant tests for run_eval_dswx_nam.py.

These tests do NOT execute the eval script or require CDSE credentials.
They verify module-level constants, structural patterns, and schema
invariants that the supervisor + Plan 06-06 gate depend on.

W2 fix invariants: f1_full_pixels + shoreline_buffer_excluded_pixels
  live in metrics.json directly (no separate sidecar file).
B2 fix invariants: compare_dswx returns a single DSWxValidationResult;
  diagnostics accessed via .diagnostics attribute (not tuple unpack).
"""
from __future__ import annotations

import ast
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent.parent / "run_eval_dswx_nam.py"


def test_script_exists() -> None:
    """run_eval_dswx_nam.py must exist at the repo root."""
    assert SCRIPT.exists(), f"run_eval_dswx_nam.py missing at {SCRIPT}"


def test_script_min_lines() -> None:
    """Script must have at least 250 lines per plan acceptance criteria."""
    lines = SCRIPT.read_text().splitlines()
    assert len(lines) >= 250, f"Script only has {len(lines)} lines (min 250)"


def test_expected_wall_s_value() -> None:
    """CONTEXT D-24: EXPECTED_WALL_S = 1800 (30 min cold path; supervisor 2x = 1 hr abort).

    The supervisor AST-parses this constant (Phase 1 D-11).
    """
    src = SCRIPT.read_text()
    assert "EXPECTED_WALL_S = 1800" in src, (
        "EXPECTED_WALL_S must be exactly 1800 (30 min cold path; D-24); "
        "supervisor AST-parses this literal"
    )


def test_expected_wall_s_ast_parseable() -> None:
    """Verify supervisor can AST-parse EXPECTED_WALL_S = 1800 at module level."""
    tree = ast.parse(SCRIPT.read_text())
    found = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "EXPECTED_WALL_S" and isinstance(node.value, ast.Constant):  # noqa: E501
                    found = ast.literal_eval(node.value)
    assert found == 1800, f"EXPECTED_WALL_S AST-parse yielded {found!r} (expected 1800)"


def test_mp_configure_multiprocessing_at_top() -> None:
    """Phase 1 ENV-04 + CONTEXT D-23: configure_multiprocessing() fires first in main."""
    src = SCRIPT.read_text()
    assert "from subsideo._mp import configure_multiprocessing" in src, (
        "Must import configure_multiprocessing from subsideo._mp"
    )
    assert "configure_multiprocessing()" in src, (
        "Must call configure_multiprocessing() at top of main (ENV-04)"
    )


def test_credential_preflight_4_vars() -> None:
    """CDSE OAuth + S3 keys all checked in credential_preflight."""
    src = SCRIPT.read_text()
    assert "CDSE_CLIENT_ID" in src, "Must check CDSE_CLIENT_ID credential"
    assert "CDSE_CLIENT_SECRET" in src, "Must check CDSE_CLIENT_SECRET credential"
    assert "CDSE_S3_ACCESS_KEY" in src, "Must check CDSE_S3_ACCESS_KEY credential"
    assert "CDSE_S3_SECRET_KEY" in src, "Must check CDSE_S3_SECRET_KEY credential"


def test_candidates_list_has_tahoe_and_pontchartrain() -> None:
    """CONTEXT D-18: 2-element CANDIDATES list with both locked AOIs."""
    src = SCRIPT.read_text()
    assert "Lake Tahoe" in src, "CANDIDATES must include Lake Tahoe (CA)"
    assert "Lake Pontchartrain" in src, "CANDIDATES must include Lake Pontchartrain (LA)"
    # MGRS tiles per Plan 06-01 lock:
    assert "10SFH" in src, "Tahoe MGRS tile 10SFH must be present"
    # Pontchartrain: STAC verified one of these at runtime
    assert "15RYP" in src or "15RYR" in src, (
        "Pontchartrain MGRS tile 15RYP or 15RYR must be present"
    )


def test_candidates_type_annotation() -> None:
    """CANDIDATES must carry the list[AOIConfig] type annotation (D-18 pattern)."""
    src = SCRIPT.read_text()
    assert "CANDIDATES: list[AOIConfig]" in src, (
        "CANDIDATES must be declared as `CANDIDATES: list[AOIConfig]` per D-18"
    )


def test_dswx_config_region_nam() -> None:
    """Plan 06-03: DSWxConfig(..., region='nam') in Stage 5."""
    src = SCRIPT.read_text()
    assert 'region="nam"' in src or "region='nam'" in src, (
        "DSWxConfig must include region='nam' (Plan 06-03 region threading)"
    )


def test_compare_dswx_b2_attribute_access() -> None:
    """B2 fix: compare_dswx returns single DSWxValidationResult; diagnostics via attribute.

    The old tuple-unpack pattern `validation, diagnostics = compare_dswx(...)` is
    FORBIDDEN. Plans 06-05/06-06/06-07 use `validation = compare_dswx(...)`
    followed by `diagnostics = validation.diagnostics`.
    """
    src = SCRIPT.read_text()
    assert "validation = compare_dswx(" in src, (
        "B2 fix: must bind `validation = compare_dswx(...)` (single return), "
        "NOT tuple unpack"
    )
    assert "validation.diagnostics" in src, (
        "B2 fix: must access diagnostics via `validation.diagnostics` attribute"
    )
    # Tuple unpack must NOT appear
    assert "validation, diagnostics = compare_dswx(" not in src, (
        "B2 fix FORBIDS tuple unpack `validation, diagnostics = compare_dswx(...)` -- "
        "use attribute access on DSWxValidationResult"
    )


def test_investigation_trigger_diagnostics_list() -> None:
    """CONTEXT D-20: 3 specific diagnostic types must appear in regression_diagnostic_required."""
    src = SCRIPT.read_text()
    assert "boa_offset_check" in src, "Must include 'boa_offset_check' regression diagnostic"
    assert "claverie_xcal_check" in src, "Must include 'claverie_xcal_check' regression diagnostic"
    assert "scl_mask_audit" in src, "Must include 'scl_mask_audit' regression diagnostic"


def test_named_upgrade_path_three_states() -> None:
    """CONTEXT D-15 + D-20: three named upgrade path strings present."""
    src = SCRIPT.read_text()
    assert "ML-replacement (DSWX-V2-01)" in src, (
        "Must include 'ML-replacement (DSWX-V2-01)' named upgrade path for 0.85 <= F1 < 0.90"
    )
    assert "BOA-offset" in src, "Must include BOA-offset in regression upgrade path"
    assert "Claverie cross-cal" in src, "Must include Claverie cross-cal in regression upgrade path"
    assert "regression" in src.lower(), "Must include 'regression' in upgrade path label"


def test_metrics_json_uses_dswx_nam_cell_metrics() -> None:
    """Plan 06-02: DswxNamCellMetrics + RegressionDiagnostic used at write time."""
    src = SCRIPT.read_text()
    assert "DswxNamCellMetrics(" in src, (
        "Must construct DswxNamCellMetrics for metrics.json write"
    )
    assert "RegressionDiagnostic(" in src, (
        "Must construct RegressionDiagnostic for regression block"
    )


def test_no_diagnostics_sidecar_w2() -> None:
    """W2 fix: f1_full_pixels + shoreline_buffer_excluded_pixels live in metrics.json directly.

    No separate eval sidecar for diagnostics; the DswxNamCellMetrics schema
    (Plan 06-02 + W2 fix) carries these fields inline for symmetry with DswxEUCellMetrics.
    """
    src = SCRIPT.read_text()
    assert "f1_full_pixels=" in src, (
        "W2 fix: must populate f1_full_pixels= in DswxNamCellMetrics constructor"
    )
    assert "shoreline_buffer_excluded_pixels=" in src, (
        "W2 fix: must populate shoreline_buffer_excluded_pixels= in DswxNamCellMetrics"
    )
    assert "diagnostics.json" not in src, (
        "W2 fix: script MUST NOT write a diagnostics.json sidecar; "
        "fields live in metrics.json directly"
    )


def test_blocker_exit_non_zero() -> None:
    """CONTEXT D-18: both candidates fail -> cell_status='BLOCKER' + sys.exit(2)."""
    src = SCRIPT.read_text()
    assert "BLOCKER" in src, "Must write cell_status='BLOCKER' when both candidates fail"
    assert "sys.exit(2)" in src, (
        "Must sys.exit(2) for BLOCKER state (D-18; both candidates fail STAC search)"
    )


def test_meta_json_has_git_sha() -> None:
    """Stage 10: meta.json must include git_sha key (threat T-06-05-05 mitigation)."""
    src = SCRIPT.read_text()
    assert '"git_sha"' in src or "'git_sha'" in src, (
        "meta.json write must include git_sha field"
    )
    # Script can use either ["git", "rev-parse", "HEAD"] list form
    # or the "git rev-parse HEAD" string form
    assert "rev-parse" in src and "HEAD" in src, (
        "Must use git rev-parse HEAD (or equivalent list form) to populate git_sha"
    )


def test_product_quality_result_json_import() -> None:
    """DswxNamCellMetrics requires ProductQualityResultJson (not dataclass variant)."""
    src = SCRIPT.read_text()
    assert "ProductQualityResultJson" in src, (
        "Must import and use ProductQualityResultJson (Pydantic model), "
        "not ProductQualityResult (dataclass)"
    )
    assert "ReferenceAgreementResultJson" in src, (
        "Must import and use ReferenceAgreementResultJson (Pydantic model)"
    )
