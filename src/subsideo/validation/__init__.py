"""subsideo.validation -- validation framework.

Re-exports the shared stable-terrain + self-consistency helpers consumed
by Phase 3 CSLC and Phase 4 DISP. Other submodules (criteria, results,
harness, supervisor, matrix_*) land in subsequent Phase 1 plans and
must APPEND to this file's ``__all__`` -- never rewrite it.
"""
from __future__ import annotations

from subsideo.validation.selfconsistency import (
    coherence_stats,
    residual_mean_velocity,
)
from subsideo.validation.stable_terrain import build_stable_mask

__all__ = [
    "build_stable_mask",
    "coherence_stats",
    "residual_mean_velocity",
]
