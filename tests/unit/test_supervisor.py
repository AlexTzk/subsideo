"""Unit tests for subsideo.validation.supervisor.

Covers the watchdog contract (D-10..D-13):
  - AST parse of EXPECTED_WALL_S (literals + whitelisted BinOps, reject Names/Calls)
  - cache-dir mtime staleness detection
  - cache-dir-from-script convention mapping
  - subprocess run() happy-path passthrough (clean exit code)
  - module-level constants match plan
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest


def test_parse_literal_int(tmp_path: Path) -> None:
    from subsideo.validation.supervisor import _parse_expected_wall_s
    script = tmp_path / "dummy.py"
    script.write_text("EXPECTED_WALL_S = 1800\nif __name__ == '__main__': pass\n")
    assert _parse_expected_wall_s(script) == 1800


def test_parse_literal_float(tmp_path: Path) -> None:
    from subsideo.validation.supervisor import _parse_expected_wall_s
    script = tmp_path / "dummy.py"
    script.write_text("EXPECTED_WALL_S = 1800.0\n")
    assert _parse_expected_wall_s(script) == 1800


def test_parse_missing_constant(tmp_path: Path) -> None:
    from subsideo.validation.supervisor import _parse_expected_wall_s
    script = tmp_path / "dummy.py"
    script.write_text("print('no constant here')\n")
    with pytest.raises(ValueError, match="EXPECTED_WALL_S"):
        _parse_expected_wall_s(script)


def test_parse_binop_accepted(tmp_path: Path) -> None:
    """BinOp on two int literals (30 * 60) must be accepted and reduced to 1800."""
    from subsideo.validation.supervisor import _parse_expected_wall_s
    script = tmp_path / "dummy.py"
    script.write_text("EXPECTED_WALL_S = 30 * 60\n")
    assert _parse_expected_wall_s(script) == 1800


def test_parse_nested_binop_accepted(tmp_path: Path) -> None:
    """Nested BinOp (60 * 60 + 900) must reduce to 4500."""
    from subsideo.validation.supervisor import _parse_expected_wall_s
    script = tmp_path / "dummy.py"
    script.write_text("EXPECTED_WALL_S = 60 * 60 + 900\n")
    assert _parse_expected_wall_s(script) == 4500


def test_parse_name_reference_rejected(tmp_path: Path) -> None:
    """Name references (MINUTES, sys.maxsize) must be rejected."""
    from subsideo.validation.supervisor import _parse_expected_wall_s
    script = tmp_path / "dummy.py"
    script.write_text("MINUTES = 30\nEXPECTED_WALL_S = MINUTES * 60\n")
    with pytest.raises(ValueError, match="literal"):
        _parse_expected_wall_s(script)


def test_parse_function_call_rejected(tmp_path: Path) -> None:
    """Function calls must be rejected."""
    from subsideo.validation.supervisor import _parse_expected_wall_s
    script = tmp_path / "dummy.py"
    script.write_text("EXPECTED_WALL_S = int(30) * 60\n")
    with pytest.raises(ValueError, match="literal"):
        _parse_expected_wall_s(script)


def test_parse_attribute_rejected(tmp_path: Path) -> None:
    """Attribute access (sys.maxsize) must be rejected."""
    from subsideo.validation.supervisor import _parse_expected_wall_s
    script = tmp_path / "dummy.py"
    script.write_text("import sys\nEXPECTED_WALL_S = sys.maxsize\n")
    with pytest.raises(ValueError, match="literal"):
        _parse_expected_wall_s(script)


def test_parse_disallowed_operator_rejected(tmp_path: Path) -> None:
    """Operators outside whitelist (e.g. **) must be rejected."""
    from subsideo.validation.supervisor import _parse_expected_wall_s
    script = tmp_path / "dummy.py"
    script.write_text("EXPECTED_WALL_S = 2 ** 10\n")
    with pytest.raises(ValueError, match="literal"):
        _parse_expected_wall_s(script)


def test_cache_dir_from_script_pilot() -> None:
    from subsideo.validation.supervisor import _cache_dir_from_script
    assert _cache_dir_from_script(Path("run_eval.py")) == Path("eval-rtc")


def test_cache_dir_from_script_dist() -> None:
    from subsideo.validation.supervisor import _cache_dir_from_script
    assert _cache_dir_from_script(Path("run_eval_dist.py")) == Path("eval-dist")


def test_cache_dir_from_script_disp_egms() -> None:
    from subsideo.validation.supervisor import _cache_dir_from_script
    assert _cache_dir_from_script(Path("run_eval_disp_egms.py")) == Path("eval-disp_egms")


def test_newest_mtime_empty(tmp_path: Path) -> None:
    from subsideo.validation.supervisor import _newest_mtime
    assert _newest_mtime(tmp_path) == 0.0


def test_newest_mtime_with_files(tmp_path: Path) -> None:
    from subsideo.validation.supervisor import _newest_mtime
    (tmp_path / "a").write_text("x")
    time.sleep(0.05)
    (tmp_path / "b").write_text("y")
    t = _newest_mtime(tmp_path)
    assert t > 0.0


def test_newest_mtime_missing_dir(tmp_path: Path) -> None:
    from subsideo.validation.supervisor import _newest_mtime
    assert _newest_mtime(tmp_path / "no-such") == 0.0


def test_module_constants_declared() -> None:
    """D-10..D-13 timing constants must be declared at the plan-specified values."""
    from subsideo.validation import supervisor
    assert supervisor.TIMEOUT_EXIT_CODE == 124
    assert supervisor.GRACE_WINDOW_S == 120
    assert supervisor.POLL_INTERVAL_S == 30
    assert supervisor.KILL_GRACE_S == 30


def test_supervisor_main_exit_code_quick_script(tmp_path: Path) -> None:
    """Run a trivial script via supervisor; expect exit 0 after normal completion."""
    from subsideo.validation import supervisor
    script = tmp_path / "quick.py"
    script.write_text(
        "EXPECTED_WALL_S = 60\n"
        "import time\n"
        "time.sleep(0.2)\n"
        "open('marker.txt','w').write('done')\n"
    )
    cache = tmp_path / "eval-quick"
    cache.mkdir()
    rc = supervisor.run(script, cache_dir=cache)
    assert rc in (0, None), f"unexpected rc={rc}"
