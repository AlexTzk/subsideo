"""DSWE threshold constants for DSWx-S2 surface-water classification.

Region-aware (N.Am. = PROTEUS defaults; EU = recalibrated).
Update only via the recalibration workflow in
``scripts/recalibrate_dswe_thresholds.py`` (Plan 06-06).

This module contains the 3 grid-tunable thresholds (WIGT, AWGT,
PSWT2_MNDWI) per CONTEXT D-04 + DSWX-04. The remaining DSWE constants
(PSWT1_*, PSWT2_BLUE/NIR/SWIR1/SWIR2) are NOT in the recalibration grid
and stay as module-level constants in ``products/dswx.py`` (Plan 06-03
deletes only WIGT/AWGT/PSWT2_MNDWI from there; the rest stay).

Provenance metadata is inline per CONTEXT D-11: every instance carries
the grid_search_run_date, fit_set_hash, fit-set/LOO-CV/Balaton F1
numbers, the reproducibility notebook path, and the results JSON path.
The N.Am. instance preserves PROTEUS-paper sentinel values; the EU
instance is overwritten by Plan 06-06's grid-search Stage 10 with real
numbers.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DSWEThresholds:
    """The 3 grid-tunable DSWE thresholds + provenance metadata.

    Frozen + slots for immutability (matches criteria.py:Criterion
    precedent + slots=True upgrade per CONTEXT D-09). Provenance fields
    enable forensic auditability of which fit set + grid search produced
    these constants.
    """

    # -- Tunable thresholds (in CONTEXT D-04 grid) --
    WIGT: float          # MNDWI water-index threshold (Test 1)
    AWGT: float          # AWESH threshold (Test 3)
    PSWT2_MNDWI: float   # PSWT2 aggressive MNDWI threshold (Test 5)

    # -- Provenance --
    grid_search_run_date: str         # ISO date or sentinel ('1996-01-01-PROTEUS-baseline')
    fit_set_hash: str                 # sha256 hex of sorted (AOI, scene) IDs concatenated; or 'n/a'
    fit_set_mean_f1: float            # NaN sentinel for PROTEUS-baseline NAM
    held_out_balaton_f1: float        # NaN for NAM
    loocv_mean_f1: float              # NaN for NAM
    loocv_gap: float                  # NaN for NAM
    notebook_path: str                # 'notebooks/dswx_recalibration.ipynb' (or 'n/a')
    results_json_path: str            # 'scripts/recalibrate_dswe_thresholds_results.json' or 'n/a'
    provenance_note: str              # human-readable cite string


# -- N.Am. instance (PROTEUS defaults preserved; CONTEXT D-Claude's-Discretion D-11 wording) --
# ╔═ THRESHOLDS_NAM_BEGIN ═
THRESHOLDS_NAM = DSWEThresholds(
    WIGT=0.124,
    AWGT=0.0,
    PSWT2_MNDWI=-0.5,
    grid_search_run_date="1996-01-01-PROTEUS-baseline",
    fit_set_hash="n/a",
    fit_set_mean_f1=float("nan"),
    held_out_balaton_f1=float("nan"),
    loocv_mean_f1=float("nan"),
    loocv_gap=float("nan"),
    notebook_path="n/a",
    results_json_path="n/a",
    provenance_note=(
        "PROTEUS DSWE Algorithm Theoretical Basis Document defaults; "
        "never recalibrated for Sentinel-2. See OPERA DSWx-HLS "
        "Product Specification v1.0.0 D-107395 RevB (PROTEUS ATBD "
        "citation chain probed in .planning/milestones/v1.1-research/"
        "dswx_proteus_atbd_ceiling_probe.md per Plan 06-01)."
    ),
)
# ╚═ THRESHOLDS_NAM_END ═


# -- EU instance (Plan 06-06 grid-search output; populated at Phase 6 close) --
# NOTE: Plan 06-06 Stage 10 overwrites these with real grid-search values.
# Until then, WIGT/AWGT/PSWT2_MNDWI are PLACEHOLDER (matching N.Am. defaults
# so the EU pipeline doesn't fail before recalibration completes).
# W1 fix: the sentinel-comment anchors below frame the THRESHOLDS_EU
# assignment so Plan 06-06 Stage 10 can fail-loud rewrite this block via
# `text.find('# ╔═ THRESHOLDS_EU_BEGIN ═')` slicing instead of fragile regex.
# ╔═ THRESHOLDS_EU_BEGIN ═
THRESHOLDS_EU = DSWEThresholds(
    WIGT=0.124,           # PLACEHOLDER -- replaced by Plan 06-06 grid-search best gridpoint
    AWGT=0.0,             # PLACEHOLDER
    PSWT2_MNDWI=-0.5,     # PLACEHOLDER
    grid_search_run_date="2026-MM-DD",  # filled at Plan 06-06 Stage 10
    fit_set_hash="",                     # sha256 of sorted (AOI, scene) IDs
    fit_set_mean_f1=float("nan"),
    held_out_balaton_f1=float("nan"),
    loocv_mean_f1=float("nan"),
    loocv_gap=float("nan"),
    notebook_path="notebooks/dswx_recalibration.ipynb",
    results_json_path="scripts/recalibrate_dswe_thresholds_results.json",
    provenance_note=(
        "PLACEHOLDER pending Plan 06-06 grid search. Joint grid search over "
        "WIGT x AWGT x PSWT2_MNDWI; 10 fit-set (AOI, scene) pairs across 5 EU "
        "biomes (5 fit-set AOIs x 2 wet/dry seasons); Balaton held out as test "
        "set per BOOTSTRAP_V1.1.md §5.4 (NOT counted in the 10 fit-set pairs). "
        "B1 fix: 10 pairs corrected from earlier \"12\" wording in CONTEXT D-14 "
        "which conflated fit-set + held-out totals."
    ),
)
# ╚═ THRESHOLDS_EU_END ═


THRESHOLDS_BY_REGION: dict[str, DSWEThresholds] = {
    "nam": THRESHOLDS_NAM,
    "eu": THRESHOLDS_EU,
}


__all__ = [
    "DSWEThresholds",
    "THRESHOLDS_NAM",
    "THRESHOLDS_EU",
    "THRESHOLDS_BY_REGION",
]
