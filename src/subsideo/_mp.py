"""Multiprocessing start-method and environment bundle for subsideo product runs.

Forces 'fork' on macOS (with 'forkserver' fallback on Python >=3.14) AND
also: sets MPLBACKEND=Agg before any matplotlib import, raises
RLIMIT_NOFILE to min(4096, hard), closes any module-global requests.Session
objects before forking. No-op on Linux through Python 3.13 (fork is default).

Called at the TOP of every ``products/*.run_*()`` entry point -- NOT at module
import (because unit-test imports should not force a start method).

Idempotent: safe to call multiple times in the same interpreter. The global
``_CONFIGURED`` flag short-circuits the second call so it does not re-invoke
``mp.set_start_method`` (which would raise RuntimeError since ``force=True``
has already been applied once).

See .planning/research/PITFALLS.md Pitfall P0.1 for the four failure modes
this bundle prevents (Cocoa/matplotlib state, CFNetwork HTTPS pool,
FD-limit 256 on macOS, joblib/loky forkserver deprecation).
"""

from __future__ import annotations

import contextlib
import multiprocessing as mp
import os
import platform
import sys
import threading

from loguru import logger

_CONFIGURED = False
# WR-04: guard the one-time bundle with a module-level lock so concurrent
# threads cannot each observe ``_CONFIGURED is False`` and both apply the
# bundle partially (RLIMIT_NOFILE / MPLBACKEND / mp.set_start_method).
_CONFIGURE_LOCK = threading.Lock()


def configure_multiprocessing() -> None:
    """Apply the full macOS fork bundle. Idempotent and thread-safe.

    (1) Sets ``MPLBACKEND=Agg`` before any matplotlib import (via
        ``os.environ.setdefault`` -- an already-set value is respected).
    (2) Raises ``RLIMIT_NOFILE`` soft limit to ``min(4096, hard)`` on
        non-Windows platforms (macOS default is 256).
    (3) Warms the ``requests`` import seam for downstream libs that cache
        module-global Sessions (CFNetwork pool corruption mitigation).
    (4) On macOS, sets the multiprocessing start method:

        - Python <3.14: ``'fork'`` (force=True)
        - Python >=3.14: ``'forkserver'`` (fork deprecated on macOS by 3.14
          due to Objective-C/Cocoa state corruption)

    No-op on Linux through Python 3.13 (fork is already the default).
    No-op on Windows for the start-method branch (fork unavailable).

    Thread safety (WR-04): uses double-checked locking so a cold call from
    multiple threads applies the bundle exactly once; subsequent calls from
    any thread are lock-free fast-path returns.
    """
    global _CONFIGURED
    # Fast path: already configured -- no lock needed.
    if _CONFIGURED:
        return
    with _CONFIGURE_LOCK:
        # Re-check under the lock: another thread may have configured
        # between our fast-path read and the lock acquisition.
        if _CONFIGURED:
            return

        # (1) Matplotlib backend MUST be set before any matplotlib import
        os.environ.setdefault("MPLBACKEND", "Agg")

        # (2) File-descriptor limit (macOS default is 256; bump to min(4096, hard))
        if platform.system() != "Windows":
            try:
                import resource

                soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
                target = min(4096, hard)
                if soft < target:
                    resource.setrlimit(resource.RLIMIT_NOFILE, (target, hard))
            except (OSError, ValueError) as e:  # noqa: BLE001
                logger.warning("Could not raise RLIMIT_NOFILE: {}", e)

        # (3) Close any cached requests.Session pre-fork (placeholder for downstream libs)
        #     subsideo itself does not cache a module-global Session; this is a seam
        #     for future modules that do. See PITFALLS P0.1 CFNetwork pool corruption.
        with contextlib.suppress(Exception):
            import requests  # noqa: F401

        # (4) Start method -- macOS: fork (or forkserver on Python >=3.14)
        if platform.system() == "Darwin":
            try:
                if sys.version_info >= (3, 14):
                    mp.set_start_method("forkserver", force=True)
                else:
                    mp.set_start_method("fork", force=True)
            except RuntimeError:
                # Start method already set in this interpreter; treat as no-op
                pass

        _CONFIGURED = True
        logger.debug(
            "configure_multiprocessing applied (platform={}, py={}.{})",
            platform.system(),
            sys.version_info.major,
            sys.version_info.minor,
        )
