"""subsideo.validation -- validation framework.

Re-exports the shared modules consumed by Phase 3 CSLC, Phase 4 DISP,
and Plan 01-07 harness + supervisor + matrix_writer.
"""
from __future__ import annotations

from subsideo.validation.criteria import CRITERIA, Criterion
from subsideo.validation.harness import (
    RETRY_POLICY,
    ReferenceDownloadError,
    bounds_for_burst,
    bounds_for_mgrs_tile,
    credential_preflight,
    download_reference_with_retry,
    ensure_resume_safe,
    select_opera_frame_by_utc_hour,
)
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
    "RETRY_POLICY",
    "ReferenceAgreementResult",
    "ReferenceDownloadError",
    "bounds_for_burst",
    "bounds_for_mgrs_tile",
    "build_stable_mask",
    "coherence_stats",
    "credential_preflight",
    "download_reference_with_retry",
    "ensure_resume_safe",
    "evaluate",
    "measurement_key",
    "residual_mean_velocity",
    "select_opera_frame_by_utc_hour",
]
