"""Unit tests for subsideo._mp.configure_multiprocessing."""

from __future__ import annotations

import multiprocessing as mp
import os
import platform
import sys

import pytest


@pytest.fixture(autouse=True)
def _reset_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset the module-level _CONFIGURED flag before each test."""
    import subsideo._mp as _mp

    monkeypatch.setattr(_mp, "_CONFIGURED", False)


def test_sets_mplbackend_agg(monkeypatch: pytest.MonkeyPatch) -> None:
    """configure_multiprocessing() sets MPLBACKEND=Agg when unset."""
    from subsideo._mp import configure_multiprocessing

    monkeypatch.delenv("MPLBACKEND", raising=False)
    configure_multiprocessing()
    assert os.environ["MPLBACKEND"] == "Agg"


def test_honours_existing_mplbackend(monkeypatch: pytest.MonkeyPatch) -> None:
    """setdefault means an already-set MPLBACKEND must not be overwritten."""
    from subsideo._mp import configure_multiprocessing

    monkeypatch.setenv("MPLBACKEND", "Qt5Agg")
    configure_multiprocessing()
    assert os.environ["MPLBACKEND"] == "Qt5Agg"


@pytest.mark.skipif(platform.system() == "Windows", reason="rlimit N/A on Windows")
def test_raises_rlimit_nofile() -> None:
    """On non-Windows, the soft RLIMIT_NOFILE is bumped to min(4096, hard)."""
    import resource

    from subsideo._mp import configure_multiprocessing

    configure_multiprocessing()
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    assert soft >= min(4096, hard), f"soft rlimit {soft} should be >= min(4096, hard={hard})"


@pytest.mark.skipif(platform.system() != "Darwin", reason="start method check is macOS-only")
def test_sets_fork_start_method_on_macos() -> None:
    """On macOS: Python <3.14 uses 'fork', Python >=3.14 uses 'forkserver'."""
    from subsideo._mp import configure_multiprocessing

    configure_multiprocessing()
    expected = "forkserver" if sys.version_info >= (3, 14) else "fork"
    assert mp.get_start_method() == expected


def test_idempotent() -> None:
    """Two consecutive calls must not raise -- short-circuits via _CONFIGURED."""
    from subsideo._mp import configure_multiprocessing

    configure_multiprocessing()
    configure_multiprocessing()  # second call short-circuits via _CONFIGURED


def test_no_import_side_effect() -> None:
    """Importing subsideo._mp alone must NOT configure multiprocessing."""
    import importlib

    import subsideo._mp as _mp

    # Reset flag via reload -- simulates a fresh import
    importlib.reload(_mp)
    # After fresh import, _CONFIGURED is False (configure_multiprocessing not called)
    assert _mp._CONFIGURED is False
