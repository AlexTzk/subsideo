"""Per-script subprocess watchdog with mtime-staleness heuristic.

Invoked as a CLI:

    python -m subsideo.validation.supervisor <eval_script.py>

Monitored signals:

* Wall time vs ``EXPECTED_WALL_S`` (module-level literal AST-parsed from the
  target script; D-11).
* Output-cache directory mtime staleness (D-10; abort only when
  ``wall > 2 * expected`` AND the cache-dir rglob mtime has not advanced
  for ``GRACE_WINDOW_S`` = 120 s).

On abort (D-12, D-13):

1. Best-effort ``py-spy dump --pid <child_pid> > <cache_dir>/watchdog-stacks.txt``
   (FileNotFoundError -> warning; any other failure -> warning).
2. ``os.killpg(pgid, SIGTERM)`` -> ``KILL_GRACE_S`` = 30 s grace -> ``os.killpg(pgid, SIGKILL)``.
3. ``sys.exit(TIMEOUT_EXIT_CODE)`` where ``TIMEOUT_EXIT_CODE = 124`` (the
   conventional ``timeout(1)`` exit code so Makefile can distinguish watchdog
   abort from other non-zero exits).

Clean exit: child's returncode passes through unchanged.

Threat model (plan 01-07 T-07-01, T-07-03, T-07-06):

* The supervisor owns a fresh process group (``start_new_session=True``) so
  isce3 / dist-s1 grandchildren are killed alongside the Python child.
* ``EXPECTED_WALL_S`` must be a literal or a whitelisted ``BinOp`` of
  literals; arbitrary Name / Call / Attribute / Subscript references are
  rejected (T-07-06 -- no arbitrary-expression eval path).
* Makefile invokes eval scripts only through the supervisor, so no script
  can skip the watchdog by being run directly from a recipe.
"""
from __future__ import annotations

import argparse
import ast
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

GRACE_WINDOW_S: int = 120
POLL_INTERVAL_S: int = 30
KILL_GRACE_S: int = 30
TIMEOUT_EXIT_CODE: int = 124


# ----------------------------------------------------------------------------
# AST parser for EXPECTED_WALL_S (T-07-06 mitigation -- no arbitrary eval)
# ----------------------------------------------------------------------------


_ALLOWED_BINOPS: dict[type, object] = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.FloorDiv: lambda a, b: a // b,
}


def _eval_literal_tree(node: ast.AST) -> int | float:
    """Reduce ``node`` to an int/float via the whitelisted literal tree.

    Accepts:

    * ``ast.Constant`` whose value is an int/float (excluding bool).
    * ``ast.BinOp`` whose operator is in :data:`_ALLOWED_BINOPS` and whose
      operands recursively reduce via this function.

    Raises :class:`ValueError` on any other shape (Name, Call, Attribute,
    Subscript, disallowed operator, bool constant, string constant).
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        left = _eval_literal_tree(node.left)
        right = _eval_literal_tree(node.right)
        reducer = _ALLOWED_BINOPS[type(node.op)]
        return reducer(left, right)  # type: ignore[operator]
    raise ValueError(
        f"EXPECTED_WALL_S must be a literal (int/float) or a BinOp of "
        f"literals on one of [+, -, *, //]; got {ast.dump(node)}"
    )


def _parse_expected_wall_s(script_path: Path) -> int:
    """AST-parse ``script_path`` and return the ``EXPECTED_WALL_S`` value.

    Accepted value forms:

    * Bare int / float literal: ``EXPECTED_WALL_S = 1800``.
    * BinOp of two Constants on a whitelisted operator:
      ``EXPECTED_WALL_S = 30 * 60`` / ``EXPECTED_WALL_S = 60 * 60 + 900``
      (nested BinOps of Constants are accepted recursively).

    Rejected (raises :class:`ValueError`):

    * Name references (``sys.maxsize``, ``MINUTES``, ...).
    * Function calls (``timedelta(...).total_seconds()``).
    * Attribute / Subscript access.
    * Any operator outside the whitelist (``**``, ``/``, bit-shift, etc.).

    This is a safety-bounded relaxation -- no arbitrary-code eval path.
    """
    tree = ast.parse(script_path.read_text(), filename=str(script_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "EXPECTED_WALL_S":
                    try:
                        value = _eval_literal_tree(node.value)
                    except ValueError as e:
                        raise ValueError(f"{script_path}: {e}") from None
                    return int(value)
    raise ValueError(
        f"{script_path}: must declare module-level EXPECTED_WALL_S = <int_seconds>"
    )


# ----------------------------------------------------------------------------
# Cache-dir throughput heuristic (D-10)
# ----------------------------------------------------------------------------


def _newest_mtime(cache_dir: Path) -> float:
    """Return the newest file mtime under ``cache_dir`` (recursive), or 0.0.

    Returns ``0.0`` when ``cache_dir`` is missing, empty, or unreadable. Never
    raises (the watchdog must remain responsive even if the subprocess has
    just mkdir'd the cache-dir or is mid-rename).
    """
    if not cache_dir.exists():
        return 0.0
    try:
        return max(
            (f.stat().st_mtime for f in cache_dir.rglob("*") if f.is_file()),
            default=0.0,
        )
    except (OSError, FileNotFoundError):
        return 0.0


def _cache_dir_from_script(script_path: Path) -> Path:
    """Map ``run_eval_<suffix>.py`` -> ``eval-<suffix>`` (pilot: ``eval-rtc``)."""
    stem = script_path.stem
    if stem == "run_eval":
        return Path("eval-rtc")
    if stem.startswith("run_eval_"):
        suffix = stem[len("run_eval_"):]
        return Path(f"eval-{suffix}")
    # Fallback: strip any run_ prefix
    return Path(f"eval-{stem.removeprefix('run_')}")


# ----------------------------------------------------------------------------
# py-spy best-effort dump (D-13)
# ----------------------------------------------------------------------------


def _py_spy_dump(pid: int, out_path: Path) -> None:
    """Run ``py-spy dump --pid <pid>`` and write to ``out_path``.

    Best-effort: logs a warning on :class:`FileNotFoundError` (py-spy not
    installed in the environment) or on any other subprocess failure. Never
    raises -- the watchdog must proceed to SIGTERM even if the dump fails.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with out_path.open("w") as f:
            subprocess.run(
                ["py-spy", "dump", "--pid", str(pid)],
                stdout=f,
                stderr=subprocess.STDOUT,
                timeout=30,
                check=False,
            )
        logger.info("py-spy dump written to {}", out_path)
    except FileNotFoundError:
        logger.warning("py-spy not installed; skipping stack dump")
    except Exception as e:  # noqa: BLE001
        logger.warning("py-spy dump failed: {}", e)


# ----------------------------------------------------------------------------
# Main supervisor loop (D-12)
# ----------------------------------------------------------------------------


def run(script_path: Path, cache_dir: Path | None = None) -> int:
    """Launch ``script_path`` in a new process group, monitor, kill on staleness.

    Parameters
    ----------
    script_path : Path
        Path to an ``run_eval_*.py`` script. Must declare a module-level
        ``EXPECTED_WALL_S`` literal (int/float) or whitelisted BinOp; the
        AST parser rejects anything else to avoid arbitrary-code eval.
    cache_dir : Path | None, default None
        Optional override for the cache directory monitored for mtime
        staleness. When ``None``, derived from the script name via
        :func:`_cache_dir_from_script`.

    Returns
    -------
    int
        Child process's return code on clean exit, or
        :data:`TIMEOUT_EXIT_CODE` (124) on watchdog abort.
    """
    # WR-10: validate script path before spawning a subprocess so a caller
    # cannot trick the supervisor into executing arbitrary files via
    # ``python -m subsideo.validation.supervisor /tmp/evil.py`` (T-07-01). The
    # naming-convention check is a warning rather than a hard stop so that
    # test fixtures and ad-hoc diagnostic scripts still work, but the
    # file-exists / not-a-symlink checks refuse to execute anything that
    # would let a share-dir attacker substitute a symlinked payload.
    if not script_path.is_file():
        raise SystemExit(
            f"supervisor: {script_path} is not a regular file"
        )
    if script_path.is_symlink():
        raise SystemExit(
            f"supervisor: {script_path} is a symlink; refusing to execute"
        )
    if not script_path.name.startswith("run_eval"):
        logger.warning(
            "supervisor: {} does not match run_eval_*.py naming convention",
            script_path,
        )

    expected_wall = _parse_expected_wall_s(script_path)
    cache_dir = cache_dir if cache_dir is not None else _cache_dir_from_script(script_path)
    logger.info(
        "supervisor: script={} expected_wall={}s cache_dir={} grace={}s",
        script_path,
        expected_wall,
        cache_dir,
        GRACE_WINDOW_S,
    )

    start = time.monotonic()
    last_mtime = _newest_mtime(cache_dir)
    last_change = start

    proc = subprocess.Popen(
        [sys.executable, str(script_path)],
        start_new_session=True,  # setsid -> new process group (T-07-01)
    )
    pgid = os.getpgid(proc.pid)

    try:
        while proc.poll() is None:
            time.sleep(POLL_INTERVAL_S)
            now = time.monotonic()
            current_mtime = _newest_mtime(cache_dir)
            if current_mtime > last_mtime:
                last_mtime = current_mtime
                last_change = now

            wall = now - start
            stale = now - last_change

            if wall > 2 * expected_wall and stale > GRACE_WINDOW_S:
                logger.warning(
                    "Watchdog abort: wall={}s > 2x{}s AND cache stale {}s > {}s",
                    int(wall),
                    expected_wall,
                    int(stale),
                    GRACE_WINDOW_S,
                )
                # (1) py-spy dump BEFORE killing
                _py_spy_dump(proc.pid, cache_dir / "watchdog-stacks.txt")
                # (2) SIGTERM process group
                try:
                    os.killpg(pgid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                # (3) Grace window then SIGKILL
                try:
                    proc.wait(timeout=KILL_GRACE_S)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(pgid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
                return TIMEOUT_EXIT_CODE
    except KeyboardInterrupt:
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=KILL_GRACE_S)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        raise

    return proc.returncode or 0


def main() -> int:
    """CLI entry point: ``python -m subsideo.validation.supervisor <script>``."""
    parser = argparse.ArgumentParser(description="subsideo validation supervisor")
    parser.add_argument("script", type=Path, help="Path to run_eval_*.py")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Override cache dir (default: derived from script name)",
    )
    args = parser.parse_args()
    return run(args.script, args.cache_dir)


if __name__ == "__main__":
    sys.exit(main())
