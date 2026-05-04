"""Root conftest.py for worktree test isolation.

When running pytest from a git worktree, the editable install in the conda
environment points to the main repo src. This conftest ensures the worktree's
own src/subsideo takes precedence so that changes made in the worktree are
tested against the worktree version, not the main repo version.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Insert the worktree's src dir at the front of sys.path so that worktree
# modifications to subsideo take precedence over the editable-install copy.
_WORKTREE_SRC = Path(__file__).parent / "src"
if str(_WORKTREE_SRC) not in sys.path:
    sys.path.insert(0, str(_WORKTREE_SRC))
