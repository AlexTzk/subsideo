---
phase: 08-cslc-gate-promotion-and-aoi-hardening
plan: 04
subsystem: validation
tags: [cslc, binding-thresholds, methodology, closure-tests]
requires:
  - phase: 08-01
    provides: projected stable-mask buffers and retention diagnostics
  - phase: 08-02
    provides: acquisition-backed AOI artifact
  - phase: 08-03
    provides: SAFE integrity validation and shared-infra regressions
provides:
  - CSLC v1.2 BINDING threshold proposal rationale
  - Phase 8 CSLC conclusions handoff notes
  - Focused and broad unit-test closure evidence
affects: [CSLC-07, CSLC-12, RTCSUP-01, RTCSUP-03, Phase 9 CSLC reruns]
tech-stack:
  added: []
  patterns: [threshold-rationale-in-requirements, append-only methodology, stale-test policy tied to regenerated artifact]
key-files:
  created:
    - .planning/milestones/v1.2-phases/08-cslc-gate-promotion-and-aoi-hardening/08-04-SUMMARY.md
  modified:
    - .planning/REQUIREMENTS.md
    - docs/validation_methodology.md
    - CONCLUSIONS_CSLC_SELFCONSIST_NAM.md
    - CONCLUSIONS_CSLC_SELFCONSIST_EU.md
    - tests/unit/test_run_eval_cslc_selfconsist_nam.py
key-decisions:
  - "Phase 8 proposes `median_of_persistent >= 0.75` and residual <= 2.0 mm/yr; Phase 9 performs final promotion reruns."
  - "Product-quality CSLC self-consistency remains separate from reference-agreement amplitude sanity."
  - "Hualapai stays rejected in tests and docs because the v1.2 probe found only 14 unique acquisition dates."
requirements-completed:
  - CSLC-07
  - CSLC-12
  - RTCSUP-01
  - RTCSUP-03
duration: 40 min
completed: 2026-04-30
---

# Phase 8 Plan 04: Threshold Rationale and Closure Summary

**CSLC v1.2 binding-threshold proposal, conclusions handoff, and closure tests**

## Performance

- **Duration:** 40 min
- **Completed:** 2026-04-30
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Added the Phase 8 proposed CSLC BINDING threshold rationale to `.planning/REQUIREMENTS.md`.
- Added the `CSLC v1.2 binding proposal (Phase 8)` methodology section, keeping product-quality and reference-agreement separate.
- Appended Phase 8 input-hardening notes to both CSLC self-consistency conclusions files.
- Updated stale NAM fallback tests to follow the v1.2 acquisition-backed artifact and keep Hualapai documented as rejected.
- Ran the focused Phase 8 suite and broad unit suite successfully in the project micromamba environment.

## Task Commits

1. **Task 1: Add CSLC v1.2 binding proposal rationale to requirements/methodology docs** - `d008109` (docs)
2. **Task 2: Add Phase 8 diagnostic notes to CSLC conclusions** - `d5a97ad` (docs)
3. **Task 3: Final Phase 8 closure test suite and stale NAM test cleanup** - `e6e7f6b` (test)

**Plan metadata:** pending orchestrator metadata commit

## Files Created/Modified

- `.planning/REQUIREMENTS.md` - Records the Phase 8 CSLC threshold proposal and calibration values.
- `docs/validation_methodology.md` - Adds the CSLC v1.2 binding proposal and Phase 9 promotion boundary.
- `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` - Adds the N.Am. Phase 8 input-hardening handoff.
- `CONCLUSIONS_CSLC_SELFCONSIST_EU.md` - Adds the EU Phase 8 input-hardening handoff.
- `tests/unit/test_run_eval_cslc_selfconsist_nam.py` - Aligns NAM fallback tests with the regenerated v1.2 artifact and rejected Hualapai row.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] NAM stale test still required rejected Hualapai**
- **Found during:** Broad unit suite
- **Issue:** `test_mojave_fallback_chain_order` and `test_all_mojave_epochs_have_15_entries` still expected Hualapai to be runnable.
- **Fix:** Updated the tests to assert the three accepted Mojave fallbacks and confirm Hualapai remains in the artifact as rejected.
- **Files modified:** `tests/unit/test_run_eval_cslc_selfconsist_nam.py`
- **Verification:** Targeted NAM tests passed; broad unit suite passed.
- **Committed in:** `e6e7f6b`

---

**Total deviations:** 1 auto-fixed (Rule 2)
**Impact on plan:** Improved CSLC-12 coverage by removing another stale v1.1 fallback-shape assertion.

## Issues Encountered

None remaining.

## User Setup Required

None.

## Next Phase Readiness

Ready for Phase 9 planning/execution. CSLC gate-promotion inputs are hardened, threshold rationale is documented, and stale fallback tests no longer require invalid v1.1 AOI bindings.

## Self-Check: PASSED

- `micromamba run -n subsideo env PYTHONPATH=src:. pytest tests/unit/test_stable_terrain.py tests/unit/test_harness.py tests/unit/test_compare_disp.py tests/unit/test_probe_cslc_aoi_candidates.py tests/unit/test_run_eval_cslc_selfconsist_eu.py -q --no-cov` passed with one intentional ENV-07 skip.
- `micromamba run -n subsideo env PYTHONPATH=src:. pytest tests/unit/ -x -q --tb=short --no-cov` passed with one intentional ENV-07 skip.
- Requirements/methodology greps confirmed `coherence >= 0.75`, `residual <= 2.0 mm/yr`, `0.887`, `0.804`, `0.868`, `CSLC v1.2 binding proposal`, and `median_of_persistent`.
- Conclusions greps confirmed exactly one `Phase 8 v1.2 input-hardening note` in each file and references to `cslc_gate_promotion_aoi_candidates.md`, `median_of_persistent >= 0.75`, and `residual <= 2.0 mm/yr`.

---
*Phase: 08-cslc-gate-promotion-and-aoi-hardening*
*Completed: 2026-04-30*
