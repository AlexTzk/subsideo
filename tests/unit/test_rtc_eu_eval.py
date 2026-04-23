"""Static-invariant tests for run_eval_rtc_eu.py.

These tests do NOT run the RTC pipeline (conda-forge deps + network). They
verify structural properties of the script that would break either the
supervisor AST parser or the Phase 2 design invariants.

Tests run under the default ``subsideo`` env; no real RTC processing occurs.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "run_eval_rtc_eu.py"


@pytest.fixture(scope="module")
def script_src() -> str:
    return SCRIPT_PATH.read_text()


@pytest.fixture(scope="module")
def script_ast(script_src: str) -> ast.Module:
    return ast.parse(script_src, filename=str(SCRIPT_PATH))


def test_supervisor_can_parse_expected_wall_s() -> None:
    """T-07-06: supervisor._parse_expected_wall_s must accept the EXPECTED_WALL_S form."""
    from subsideo.validation.supervisor import _parse_expected_wall_s

    value = _parse_expected_wall_s(SCRIPT_PATH)
    assert isinstance(value, int)
    assert value >= 60 * 60  # at least 1 hour
    assert value <= 60 * 60 * 24  # sanity upper bound (1 day)


def test_bursts_literal_exists(script_ast: ast.Module) -> None:
    """Module-level ``BURSTS = [...]`` assignment with exactly 5 elements."""
    bursts_list = None
    for node in ast.walk(script_ast):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "BURSTS":
                    bursts_list = node.value
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "BURSTS":
                bursts_list = node.value
    assert bursts_list is not None, "BURSTS not assigned at module level"
    assert isinstance(bursts_list, (ast.List, ast.Tuple)), (
        f"BURSTS must be a list/tuple literal, got {type(bursts_list).__name__}"
    )
    assert len(bursts_list.elts) == 5, (
        f"BURSTS must have exactly 5 entries (5 regimes per D-03); "
        f"got {len(bursts_list.elts)}"
    )


def test_bursts_cover_five_regimes(script_src: str) -> None:
    """Every regime label from the Literal[...] set appears exactly once in BURSTS."""
    expected = {"Alpine", "Scandinavian", "Iberian", "TemperateFlat", "Fire"}
    for label in expected:
        count = script_src.count(f'regime="{label}"')
        assert count >= 1, f'regime="{label}" not found in BURSTS'
    # Exactly 5 regime=... occurrences (one per BurstConfig).
    total_regime = sum(script_src.count(f'regime="{r}"') for r in expected)
    assert total_regime == 5


def test_rtc_01_constraints_embedded(script_src: str) -> None:
    """RTC-01 mandatory constraints (>1000 m relief, >55°N) must be annotated."""
    assert ">1000 m relief" in script_src
    assert ">55" in script_src


def test_script_imports_find_cached_safe(script_src: str) -> None:
    """D-02 requires harness.find_cached_safe."""
    assert "find_cached_safe" in script_src
    assert "from subsideo.validation.harness import" in script_src


def test_script_imports_rtc_eu_cell_metrics(script_src: str) -> None:
    """D-09/D-10 require RTCEUCellMetrics + BurstResult."""
    assert "RTCEUCellMetrics" in script_src
    assert "BurstResult" in script_src


def test_script_uses_investigation_trigger_thresholds(script_src: str) -> None:
    """D-13: investigation_required must derive from CRITERIA INVESTIGATION_TRIGGER entries."""
    assert "rtc.eu.investigation_rmse_db_min" in script_src
    assert "rtc.eu.investigation_r_max" in script_src
    # Belt: CRITERIA is the source, not hardcoded.
    assert "CRITERIA" in script_src


def test_credential_preflight_present(script_src: str) -> None:
    """SP-2: every harness-based eval script calls credential_preflight."""
    assert "credential_preflight(" in script_src
    assert '"EARTHDATA_USERNAME"' in script_src
    assert '"EARTHDATA_PASSWORD"' in script_src


def test_per_burst_try_except_present(script_ast: ast.Module) -> None:
    """D-06: the main loop iterating BURSTS contains a try/except."""
    # Walk the AST; find the For loop iterating BURSTS; check it contains a Try.
    for node in ast.walk(script_ast):
        if (
            isinstance(node, ast.For)
            and isinstance(node.iter, ast.Name)
            and node.iter.id == "BURSTS"
        ):
            has_try = any(isinstance(inner, ast.Try) for inner in node.body)
            assert has_try, "for cfg in BURSTS: body must contain a try/except (D-06)"
            return
    pytest.fail("No `for ... in BURSTS:` loop found in run_eval_rtc_eu.py")


def test_bursts_have_alpine_relief_gt_1000_annotation(script_src: str) -> None:
    """Claude-drafted Alpine burst must be annotated as >1000 m relief (RTC-01)."""
    # The script comments reference "~3200 m relief" for the Alpine row.
    has_relief_annotation = (
        "~3200 m" in script_src or "3200 m" in script_src or "3000 m" in script_src
    )
    assert has_relief_annotation, (
        "Alpine BurstConfig must have a relief annotation above 1000 m (RTC-01)."
    )


def test_bursts_have_scandinavian_lat_gt_55(script_src: str) -> None:
    """Scandinavian burst centroid_lat must be > 55.0 (RTC-01)."""
    # Extract the BURSTS list via ast, find the Scandinavian row.
    tree = ast.parse(script_src)
    scandinavian_lats: list[float] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "BurstConfig"
        ):
            kwargs = {kw.arg: kw.value for kw in node.keywords}
            regime_node = kwargs.get("regime")
            centroid_node = kwargs.get("centroid_lat")
            if (
                regime_node is not None
                and isinstance(regime_node, ast.Constant)
                and regime_node.value == "Scandinavian"
                and centroid_node is not None
                and isinstance(centroid_node, ast.Constant)
                and isinstance(centroid_node.value, (int, float))
            ):
                scandinavian_lats.append(float(centroid_node.value))
    assert scandinavian_lats, "No Scandinavian BurstConfig found"
    for lat in scandinavian_lats:
        assert lat > 55.0, (
            f"Scandinavian centroid_lat={lat} violates RTC-01 (must be >55°N)"
        )


def test_no_hand_coded_bounds_outside_bursts(script_src: str) -> None:
    """ENV-08 continuity: no top-level hand-coded geographic bounds literals.

    Bounds come from ``bounds_for_burst(cfg.burst_id, ...)``. The test
    checks the script does NOT contain a ``BBOX = (...)`` assignment at
    module level with float literals, which was the v1.0 anti-pattern.
    """
    tree = ast.parse(script_src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.upper() in (
                    "BBOX", "AOI", "BOUNDS", "AOI_BBOX"
                ):
                    pytest.fail(
                        f"Found hand-coded bounds {target.id} = ... at module level; "
                        f"ENV-08 requires bounds_for_burst()"
                    )


def test_script_syntax_valid(script_src: str) -> None:
    ast.parse(script_src)


def test_expected_wall_s_is_hours() -> None:
    """EXPECTED_WALL_S should be at least 2h cold-run budget for 5 bursts."""
    from subsideo.validation.supervisor import _parse_expected_wall_s

    val = _parse_expected_wall_s(SCRIPT_PATH)
    assert val >= 2 * 60 * 60, (
        f"EXPECTED_WALL_S={val}s is less than 2h; too tight for 5 RTC "
        f"bursts + OPERA downloads. Phase 2 CONTEXT recommends ~4h cold "
        f"for variable-network safety margin."
    )


def test_datetime_import_is_clean(script_src: str) -> None:
    """WARNING fix: datetime + timedelta must be a single clean import.

    The first revision used ``__import__("datetime").timedelta(days=1)``
    in 4 call sites. Those were replaced with a single
    ``from datetime import datetime, timedelta`` import and direct
    ``timedelta(...)`` usage. This test enforces the clean form.
    """
    assert "from datetime import datetime, timedelta" in script_src, (
        "run_eval_rtc_eu.py must import timedelta alongside datetime "
        "(WARNING fix from Plan 02-04 revision)."
    )
    # No remaining __import__("datetime") usages -- the old pattern is gone.
    assert '__import__("datetime")' not in script_src, (
        'Legacy __import__("datetime").timedelta(...) pattern detected; '
        "use imported timedelta symbol directly."
    )


def test_bursts_have_main_guard(script_ast: ast.Module) -> None:
    """SP-1: top-level work must be inside ``if __name__ == '__main__':``."""
    has_main_guard = False
    for node in script_ast.body:
        if (
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
        ):
            has_main_guard = True
            break
    assert has_main_guard, (
        "run_eval_rtc_eu.py must wrap top-level work in "
        "`if __name__ == '__main__':` (SP-1 / _mp precondition)."
    )


def test_expected_wall_s_is_module_level(script_ast: ast.Module) -> None:
    """EXPECTED_WALL_S must be assigned at module level (not inside main guard),
    so the supervisor's AST parser picks it up without executing the script."""
    for node in script_ast.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "EXPECTED_WALL_S":
                    return
    pytest.fail("EXPECTED_WALL_S must be a module-level assignment, not inside main guard")
