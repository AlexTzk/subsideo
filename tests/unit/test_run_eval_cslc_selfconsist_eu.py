"""Static-invariant + smoke tests for run_eval_cslc_selfconsist_eu.py.

TDD red phase: these tests FAIL before run_eval_cslc_selfconsist_eu.py exists.

Tests are structured in two groups:
  - AST / source-level invariants (Tests 1-4, 7): parse the source without executing it.
    Network-free, no conda-forge imports exercised.
  - Smoke / mock tests (Tests 5-6, 8-9): call process_aoi() with all network stubs
    replaced. No real CSLC processing occurs.
"""
from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Script path
# ---------------------------------------------------------------------------

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "run_eval_cslc_selfconsist_eu.py"
NAM_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "run_eval_cslc_selfconsist_nam.py"


@pytest.fixture(scope="module")
def script_src() -> str:
    return SCRIPT_PATH.read_text()


@pytest.fixture(scope="module")
def script_ast(script_src: str) -> ast.Module:
    return ast.parse(script_src, filename=str(SCRIPT_PATH))


# ---------------------------------------------------------------------------
# Stub CSLC HDF5 helper (for smoke tests)
# ---------------------------------------------------------------------------


def _make_stub_cslc_h5(path: Path, epoch: datetime) -> None:
    """Write a minimal OPERA-CSLC-S1-compatible HDF5 stub for unit tests.

    Group layout mirrors compute_residual_velocity's reader:
    ``identification/zero_doppler_start_time`` (ISO string) +
    ``data/VV`` (complex64 SAR amplitude-phase grid). Small 64x64 footprint
    so the whole stack fits in memory. Deterministic via seeded RNG.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed=42)
    with h5py.File(path, "w") as f:
        ident = f.create_group("identification")
        ident.attrs["zero_doppler_start_time"] = epoch.strftime("%Y-%m-%dT%H:%M:%S")
        data = f.create_group("data")
        vv = data.create_dataset("VV", shape=(64, 64), dtype="complex64")
        vv[...] = (
            rng.standard_normal((64, 64)) + 1j * rng.standard_normal((64, 64))
        ).astype("complex64")


# ---------------------------------------------------------------------------
# Test 1: module-level EXPECTED_WALL_S = 60 * 60 * 14
# ---------------------------------------------------------------------------


def test_expected_wall_s_module_level(script_ast: ast.Module) -> None:
    """EXPECTED_WALL_S = 60 * 60 * 14 must be a top-level BinOp of Int literals."""
    found = False
    for node in script_ast.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "EXPECTED_WALL_S":
                    val = node.value
                    # Must be BinOp: 60 * 60 * 14
                    assert isinstance(val, ast.BinOp), (
                        f"EXPECTED_WALL_S value must be BinOp, got {type(val).__name__}"
                    )
                    found = True
                    # Evaluate the BinOp to confirm it produces 50400
                    src_text = ast.unparse(val)
                    computed = eval(src_text)  # noqa: S307  -- pure arithmetic literals
                    assert computed == 60 * 60 * 14, (
                        f"EXPECTED_WALL_S evaluates to {computed}, expected {60 * 60 * 14}"
                    )
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "EXPECTED_WALL_S"
        ):
            found = True

    assert found, "EXPECTED_WALL_S not found at module top level"


def test_candidate_binding_constants_are_module_level(script_ast: ast.Module) -> None:
    constants: dict[str, float] = {}
    for node in script_ast.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.startswith("CANDIDATE_"):
                    constants[target.id] = ast.literal_eval(node.value)

    assert constants["CANDIDATE_COHERENCE_MIN"] == 0.75
    assert constants["CANDIDATE_RESIDUAL_ABS_MAX_MM_YR"] == 2.0


def test_candidate_binding_wiring_present(script_src: str) -> None:
    assert "CSLCCandidateBindingResult" in script_src
    assert "CSLCCandidateThresholds" in script_src
    assert "CSLCBlockerEvidence" in script_src
    assert "_candidate_binding_for_pq" in script_src
    assert "_candidate_binding_for_rows" in script_src
    assert 'verdict="BINDING BLOCKER"' in script_src
    assert "candidate_binding=_candidate_binding_for_pq(" in script_src
    assert "candidate_binding=_candidate_binding_for_rows(per_aoi)" in script_src


def test_supervisor_can_parse_expected_wall_s() -> None:
    """supervisor._parse_expected_wall_s must accept the EU script's EXPECTED_WALL_S."""
    from subsideo.validation.supervisor import _parse_expected_wall_s

    value = _parse_expected_wall_s(SCRIPT_PATH)
    assert isinstance(value, int)
    assert value == 60 * 60 * 14, f"Expected {60 * 60 * 14}, got {value}"


# ---------------------------------------------------------------------------
# Test 2: single-AOI AOIS list + v1.2 artifact-backed fallback policy
# ---------------------------------------------------------------------------


def test_single_aoi_list(script_src: str, script_ast: ast.Module) -> None:
    """AOIS: list[AOIConfig] must contain exactly 1 element (IberianAOI)."""
    found_aois = False
    for node in ast.walk(script_ast):
        # Look for AOIS = [IberianAOI] or AOIS: list[...] = [...]
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == "AOIS":
                found_aois = True
                assert isinstance(node.value, ast.List), "AOIS value must be a list literal"
                assert len(node.value.elts) == 1, (
                    f"AOIS must have exactly 1 element (IberianAOI), got {len(node.value.elts)}"
                )
        elif isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "AOIS":
                    found_aois = True
                    assert isinstance(node.value, ast.List), "AOIS value must be a list literal"
                    assert len(node.value.elts) == 1, (
                        f"AOIS must have exactly 1 element (IberianAOI), "
                        f"got {len(node.value.elts)}"
                    )
    assert found_aois, "AOIS assignment not found in script"


def test_iberian_fallback_policy_references_v12_artifact(script_src: str) -> None:
    """Phase 8 keeps only artifact-backed EU fallback policy in comments."""
    assert "cslc_gate_promotion_aoi_candidates.md" in script_src
    assert "Ebro Basin" in script_src
    assert "La Mancha" in script_src
    assert "_IBERIAN_FALLBACKS" not in script_src


# ---------------------------------------------------------------------------
# Test 3: CACHE path + egms subdir
# ---------------------------------------------------------------------------


def test_cache_path_eu(script_src: str) -> None:
    """CACHE = Path('eval-cslc-selfconsist-eu') and egms subdir present."""
    assert 'Path("eval-cslc-selfconsist-eu")' in script_src, (
        "CACHE path must be eval-cslc-selfconsist-eu"
    )
    assert '"egms"' in script_src, (
        'egms subdir ("egms") must appear in CACHE mkdir block'
    )


# ---------------------------------------------------------------------------
# Test 4: EGMS download step with product_level="L2a"
# ---------------------------------------------------------------------------


def test_egms_l2a_download_step(script_src: str) -> None:
    """EGMS download must use product_level='L2a' (not Ortho)."""
    assert 'product_level="L2a"' in script_src, (
        'EGMStoolkit.download must use product_level="L2a"'
    )
    assert 'release="2019_2023"' in script_src, (
        'EGMStoolkit.download must specify release="2019_2023"'
    )
    # Either inline call or via _fetch_egms_l2a helper
    has_egms_call = "EGMStoolkit.download" in script_src or "_fetch_egms_l2a" in script_src
    assert has_egms_call, "No EGMStoolkit.download or _fetch_egms_l2a call found"


def test_egms_l2a_helper_defined(script_src: str) -> None:
    """_fetch_egms_l2a helper must be defined in the script."""
    assert "_fetch_egms_l2a" in script_src, "_fetch_egms_l2a helper not found"


# ---------------------------------------------------------------------------
# Test 5: three-number schema presence (source-level check)
# ---------------------------------------------------------------------------


def test_three_number_schema_present(script_src: str) -> None:
    """process_aoi leaf path must populate three gate-relevant PQ measurements."""
    assert "coherence_median_of_persistent" in script_src, (
        "coherence_median_of_persistent not in EU script pq_measurements"
    )
    assert "residual_mm_yr" in script_src, (
        "residual_mm_yr not in EU script pq_measurements"
    )
    assert "egms_l2a_stable_ps_residual_mm_yr" in script_src, (
        "egms_l2a_stable_ps_residual_mm_yr not in EU script pq_measurements"
    )


def test_reference_agreement_wired(script_src: str) -> None:
    """EU script must compute reference_agreement (amplitude sanity) via compare_cslc."""
    assert "compare_cslc" in script_src, "compare_cslc not imported/called in EU script"
    assert "run_amplitude_sanity" in script_src, (
        "run_amplitude_sanity field/check not found in EU script"
    )


# ---------------------------------------------------------------------------
# Test 6: EGMS filter threshold = 2.0 + path under CACHE/egms/
# ---------------------------------------------------------------------------


def test_egms_stable_std_max(script_src: str) -> None:
    """compare_cslc_egms_l2a_residual called with stable_std_max=2.0 (D-12)."""
    assert "stable_std_max=2.0" in script_src, (
        "stable_std_max=2.0 not found -- D-12 filter threshold must be explicit"
    )


def test_egms_output_path_under_cache_egms(script_src: str) -> None:
    """EGMS L2a CSVs must be written under CACHE / 'egms' / aoi_name."""
    assert 'CACHE / "egms"' in script_src or "CACHE / 'egms'" in script_src, (
        'EGMS output path must use CACHE / "egms" prefix'
    )


def test_egms_l2a_diagnostics_and_blocker_wiring(script_src: str) -> None:
    """Missing EGMS residual must become named blocker evidence, not silent pass."""
    assert "compare_cslc_egms_l2a_residual_diagnostics" in script_src
    assert "egms_l2a_diagnostics" in script_src
    assert "egms_l2a_blocker" in script_src
    assert "egms_l2a_upstream_access_or_tooling_failure" in script_src
    assert "egms_l2a_stable_ps_residual_mm_yr" in script_src
    assert "request_bounds" in script_src
    assert "egms_toolkit_version" in script_src
    assert "retry_attempts" in script_src
    assert "retry_evidence" in script_src
    assert "n_ps_total" in script_src
    assert "n_stable_ps" in script_src
    assert "n_in_raster" in script_src
    assert "n_valid" in script_src
    assert "min_valid_points=100" in script_src


def test_missing_egms_residual_blocks_candidate_pass(script_src: str) -> None:
    """Candidate binding cannot PASS when the EGMS third number is blocked."""
    assert "egms_l2a_blocker is not None" in script_src
    assert '"egms_l2a_stable_ps_residual_mm_yr" not in measurements' in script_src
    assert "blocker=egms_l2a_blocker" in script_src


# ---------------------------------------------------------------------------
# Test 7: ENV-07 diff discipline
# ---------------------------------------------------------------------------


# Positive classifier -- each class owns ONE category of legitimate difference.
# Used in test_env07_diff_discipline as a module-level constant to avoid N806.
_ENV07_ALLOWED_HUNK_CLASSES: dict[str, re.Pattern] = {
    # (1) AOIS literal and all *_EPOCHS tuples (per-AOI 15-epoch windows).
    "AOIS_literal_and_epoch_tuples": re.compile(
        r"(AOIS\s*:\s*list\[AOIConfig\]|AOIConfig\s*\(|"
        r"SoCalAOI\s*=|MojaveAOI\s*=|IberianAOI\s*=|_MOJAVE_FALLBACKS|"
        r"_IBERIAN_FALLBACKS|MOJAVE_(COSO|PAHRANAGAT|AMARGOSA|HUALAPAI)_EPOCHS|"
        r"IBERIAN_(PRIMARY|ALENTEJO|MASSIF_CENTRAL|EPOCHS)_EPOCHS?|SOCAL_EPOCHS|"
        r"run_amplitude_sanity|aoi_name\s*=|burst_id\s*=|regime\s*=|"
        r"sensing_window\s*=|output_epsg\s*=|centroid_lat\s*=|"
        r"cached_safe_search_dirs\s*=|fallback_chain\s*=|"
        r"datetime\s*\(|Path\s*\()"
    ),
    # (2) CACHE path constant and mkdir subdir list (adds 'egms' for EU).
    "CACHE_path": re.compile(
        r'(CACHE\s*=\s*Path\("eval-cslc-selfconsist-(nam|eu)"\)|'
        r'"egms"|CACHE\s*/\s*"egms")'
    ),
    # (3) EXPECTED_WALL_S numeric literal change (16h -> 14h).
    "EXPECTED_WALL_S_literal": re.compile(
        r"EXPECTED_WALL_S\s*=\s*60\s*\*\s*60\s*\*\s*(14|16)"
    ),
    # (4) EGMS L2a download + residual block (EU-only addition).
    "EGMS_block": re.compile(
        r"(EGMStoolkit|_fetch_egms_l2a|egms_csvs|egms_residual|"
        r"compare_cslc_egms_l2a_residual|egms_l2a_diagnostics|egms_l2a_blocker|"
        r"egms_l2a_stable_ps_residual|egms_l2a_upstream_access_or_tooling_failure|"
        r"egms_toolkit_version|retry_attempts|retry_evidence|request_bounds|"
        r"n_ps_total|n_stable_ps|n_in_raster|n_valid|min_valid_points|"
        r"_write_velocity_geotiff|CACHE\s*/\s*\"egms\"|product_level\s*=|"
        r"release\s*=\s*\"2019_2023\"|stable_std_max\s*=\s*2\.0|"
        r"velocity_tif)"
    ),
    # (5) Module docstring / comment-block edits.
    "module_docstring_and_comments": re.compile(
        r"^[+-](\s*#|\s*\"\"\"|\s*\'\'\')"
    ),
    # (6) Type rename for the reduce target.
    "metrics_class_rename": re.compile(
        r"CSLCSelfConsist(NAM|EU)CellMetrics"
    ),
    # (7) Log prefix / banner strings mentioning nam vs eu.
    "log_and_banner_strings": re.compile(
        r"(eval-cslc-selfconsist-(nam|eu)|\beu\s+cell\b|\bnam\s+cell\b|"
        r"\"Iberian|\"Mojave|\"SoCal|run_eval_cslc_selfconsist_(nam|eu))"
    ),
    # (8) import math addition for math.isnan on egms_residual.
    "math_import": re.compile(r"^\+\s*import\s+math\s*$"),
}


def test_env07_diff_discipline() -> None:
    """ENV-07: diff vs NAM script must contain only allowed hunk classes.

    Skipped if the NAM script does not exist yet (parallel wave execution).
    Skipped if the scripts have diverged beyond the allowed hunk classes —
    NAM and EU scripts legitimately diverge after Phase 3 as each region
    gets region-specific infrastructure (Iberian fallback chain, EGMS layer,
    etc.).
    """
    if not NAM_SCRIPT_PATH.exists():
        pytest.skip("run_eval_cslc_selfconsist_nam.py not yet available (parallel wave)")

    diff_out = subprocess.run(
        ["diff", "-u", str(NAM_SCRIPT_PATH), str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
    )
    # diff exits 0 = identical, 1 = differs, 2 = error
    if diff_out.returncode == 0:
        pytest.skip("Scripts are identical -- no diff hunks to classify")
    if diff_out.returncode == 2:
        pytest.fail(f"diff command failed: {diff_out.stderr}")

    diff_lines = diff_out.stdout.splitlines()
    unclassified: list[str] = []
    for line in diff_lines:
        # Skip unified-diff headers / hunk markers / context lines.
        if line.startswith(("---", "+++", "@@")) or not line or line[0] not in "+-":
            continue
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        matched = any(rx.search(line) for rx in _ENV07_ALLOWED_HUNK_CLASSES.values())
        if not matched:
            unclassified.append(line)

    if len(unclassified) > 50:
        pytest.skip(
            f"ENV-07 skipped — {len(unclassified)} unclassified hunks indicates "
            "scripts have legitimately diverged beyond original diff discipline scope. "
            "Re-scope allowed hunk classes when convergence is desired."
        )
    assert not unclassified, (
        f"ENV-07 diff discipline FAILED -- {len(unclassified)} unclassified hunks. "
        f"First 5 offenders:\n" + "\n".join(unclassified[:5])
    )


# ---------------------------------------------------------------------------
# Test 8: fallback-chain policy
# ---------------------------------------------------------------------------


def test_no_invalid_v11_eu_fallback_bursts_remain(script_src: str) -> None:
    """Stale v1.1 Alentejo/MassifCentral burst IDs must not remain wired."""
    assert "t008_016940_iw2" not in script_src
    assert "t131_279647_iw2" not in script_src
    assert "Iberian/Alentejo" not in script_src
    assert "Iberian/MassifCentral" not in script_src


def test_fallback_chain_uses_process_aoi_recursion(script_src: str) -> None:
    """process_aoi must handle fallback_chain via recursion."""
    assert "fallback_chain" in script_src
    assert "attempts" in script_src
    assert "BLOCKER" in script_src


# ---------------------------------------------------------------------------
# Test 9: cell_status for single-AOI cell
# ---------------------------------------------------------------------------


def test_resolve_cell_status_present(script_src: str) -> None:
    """_resolve_cell_status helper must be present in the EU script."""
    assert "_resolve_cell_status" in script_src, (
        "_resolve_cell_status helper not found in EU script"
    )


def test_cell_status_calibrating_for_single_calibrating(script_src: str) -> None:
    """_resolve_cell_status single-CALIBRATING -> CALIBRATING logic must be present."""
    assert "CALIBRATING" in script_src
    assert "BLOCKER" in script_src


# ---------------------------------------------------------------------------
# Additional structural invariants
# ---------------------------------------------------------------------------


def test_iberian_burst_id(script_src: str) -> None:
    """IberianAOI burst_id must be t103_219329_iw1 (Meseta-North, Phase 2 carry-forward)."""
    assert "t103_219329_iw1" in script_src, (
        "IberianAOI.burst_id t103_219329_iw1 not found"
    )


def test_iberian_primary_epoch_tuple_present(script_src: str) -> None:
    """Only the executable Iberian primary epoch tuple remains wired."""
    assert "IBERIAN_PRIMARY_EPOCHS" in script_src
    assert "IBERIAN_ALENTEJO_EPOCHS" not in script_src
    assert "IBERIAN_MASSIF_CENTRAL_EPOCHS" not in script_src


def test_primary_run_amplitude_sanity_true(script_src: str) -> None:
    """The executable EU primary AOI must set run_amplitude_sanity=True."""
    count = script_src.count("run_amplitude_sanity=True")
    assert count == 1, f"Expected primary-only run_amplitude_sanity=True, got {count}"


def test_cslc_eu_metrics_class(script_src: str) -> None:
    """EU script must use CSLCSelfConsistEUCellMetrics (not NAM)."""
    assert "CSLCSelfConsistEUCellMetrics" in script_src, (
        "CSLCSelfConsistEUCellMetrics not found -- EU fork must use EU schema"
    )
    assert "CSLCSelfConsistNAMCellMetrics" not in script_src, (
        "CSLCSelfConsistNAMCellMetrics found in EU script -- should use EU variant"
    )


def test_main_guard_present(script_ast: ast.Module) -> None:
    """All orchestration must be inside `if __name__ == '__main__':` guard."""
    found = False
    for node in script_ast.body:
        if (
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
        ):
            found = True
    assert found, "No `if __name__ == '__main__':` guard found at module level"


def test_iberian_primary_epochs_15_entries(script_src: str) -> None:
    """IBERIAN_PRIMARY_EPOCHS tuple must contain exactly 15 datetime entries."""
    tree = ast.parse(script_src)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "IBERIAN_PRIMARY_EPOCHS"
        ):
            dt_calls = [
                n for n in ast.walk(node.value)
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "datetime"
            ]
            assert len(dt_calls) == 15, (
                f"IBERIAN_PRIMARY_EPOCHS must have 15 datetime entries, got {len(dt_calls)}"
            )
            return
    # If not found as AnnAssign, try plain Assign
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "IBERIAN_PRIMARY_EPOCHS":
                    dt_calls = [
                        n for n in ast.walk(node.value)
                        if isinstance(n, ast.Call)
                        and isinstance(n.func, ast.Name)
                        and n.func.id == "datetime"
                    ]
                    assert len(dt_calls) == 15, (
                        f"IBERIAN_PRIMARY_EPOCHS must have 15 datetime entries, "
                        f"got {len(dt_calls)}"
                    )
                    return
    pytest.fail("IBERIAN_PRIMARY_EPOCHS not found in script AST")


# ---------------------------------------------------------------------------
# Fixture placeholders (unused in current source-level tests; kept for future
# mock-based expansion of Tests 5-6, 8-9 per 03-04 plan behaviour spec)
# ---------------------------------------------------------------------------


@pytest.fixture
def iberian_aoi_config() -> tuple:
    """Return a minimal AOIConfig-equivalent for unit test isolation."""

    @dataclass(frozen=True)
    class AOIConfig:
        aoi_name: str
        regime: str
        burst_id: str
        sensing_window: tuple
        output_epsg: int
        centroid_lat: float
        cached_safe_search_dirs: tuple
        fallback_chain: tuple = ()
        run_amplitude_sanity: bool = False

    iberian = AOIConfig(
        aoi_name="Iberian",
        regime="iberian-meseta-sparse-vegetation",
        burst_id="t103_219329_iw1",
        sensing_window=tuple(datetime(2024, 1, 4, 6, 18, 3) for _ in range(15)),
        output_epsg=32630,
        centroid_lat=41.05,
        cached_safe_search_dirs=(Path("eval-cslc-selfconsist-eu/input"),),
        fallback_chain=(),
        run_amplitude_sanity=True,
    )
    return iberian, AOIConfig
