"""subsideo.validation -- validation framework.

Re-exports the shared modules consumed by Phase 3 CSLC, Phase 4 DISP,
and Plan 01-07 harness + supervisor + matrix_writer.
"""
from __future__ import annotations

from subsideo.validation.criteria import CRITERIA, Criterion
from subsideo.validation.results import (
    ProductQualityResult,
    ReferenceAgreementResult,
    evaluate,
    measurement_key,
)
from subsideo.validation.selfconsistency import (
    coherence_stats,
    residual_mean_velocity,
)
from subsideo.validation.stable_terrain import build_stable_mask

__all__ = [
    "CRITERIA",
    "Criterion",
    "ProductQualityResult",
    "ReferenceAgreementResult",
    "build_stable_mask",
    "coherence_stats",
    "evaluate",
    "measurement_key",
    "residual_mean_velocity",
]
