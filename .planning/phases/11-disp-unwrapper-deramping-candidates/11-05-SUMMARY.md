---
phase: 11-disp-unwrapper-deramping-candidates
plan: "05"
subsystem: validation
tags: [disp, conclusions, candidates, spurt, phass, deramping, phase11]

requires:
  - phase: 11-disp-unwrapper-deramping-candidates
    provides: "Live sidecars with 4 candidate-cell outcomes and cand= matrix hints (11-04)"
  - phase: 11-disp-unwrapper-deramping-candidates
    provides: "PHASS post-deramp candidate wiring and BLOCKER outcomes (11-03)"
  - phase: 11-disp-unwrapper-deramping-candidates
    provides: "SPURT candidate wiring and BLOCKER outcomes (11-02)"

provides:
  - "Phase 11 unwrapper and deramping candidates section in CONCLUSIONS_DISP_N_AM.md"
  - "Phase 11 unwrapper and deramping candidates section in CONCLUSIONS_DISP_EU.md"
  - "SoCal candidate table: spurt_native BLOCKER + phass_post_deramp BLOCKER* from schema-valid sidecar"
  - "Bologna candidate table: spurt_native BLOCKER + phass_post_deramp BLOCKER* from schema-valid sidecar"
  - "D-08 flag note: PHASS deformation sanity is Phase 12 production-recommendation blocker only"
  - "D-13 note: ERA5 not promoted to required Phase 11 baseline"
  - "D-14 note: tophu/SNAPHU and 20x20 m fallback deferred as later ladder steps"

affects: [phase-12, disp-production-posture, disp-unwrapper-selection-brief]

tech-stack:
  added: []
  patterns:
    - "Candidate evidence appended as separate section in conclusions, after existing product-quality/RA/ramp sections (D-12)"
    - "BLOCKER table rows use — for null sidecar fields; partial=True marked with * suffix (D-11)"
    - "Numbers copied directly from schema-valid metrics.json sidecars, never from terminal logs or matrix markdown (T-11-05-01)"

key-files:
  created: []
  modified:
    - CONCLUSIONS_DISP_N_AM.md
    - CONCLUSIONS_DISP_EU.md

key-decisions:
  - "D-06: Conclusion prose preserves PHASS deramping as validation-only and does not change the native production default"
  - "D-08: Deformation-sanity flag is a Phase 12 production-recommendation blocker, not a Phase 11 metric-reporting blocker"
  - "D-09: Conclusion tables report each candidate-cell outcome as PASS, FAIL, or BLOCKER"
  - "D-10: Conclusion blocker notes preserve structured blocker meaning from sidecars"
  - "D-11: BLOCKER* suffix distinguishes partial-metrics outcomes from comparable PASS/FAIL evidence"
  - "D-12: Candidate status table kept separate from product-quality, reference-agreement, and ramp-attribution sections"
  - "D-13: ERA5 carry-forward documented as not promoted to required baseline"
  - "D-14: tophu/SNAPHU and 20 x 20 m fallback noted as later ladder steps deferred to Phase 12"

patterns-established:
  - "Candidate sections append AFTER existing product/RA/ramp sections — never replace them"
  - "Null sidecar fields rendered as — in conclusion tables (not omitted, not zero)"

requirements-completed: [DISP-07, DISP-08, DISP-09]

duration: 3min
completed: 2026-05-05
---

# Phase 11 Plan 05: Phase 11 Candidate Evidence in DISP Conclusions Summary

**Phase 11 BLOCKER outcomes for SPURT native and PHASS post-deramping recorded in both DISP conclusion files from schema-valid sidecars, preserving validation-only posture and leaving production selection to Phase 12**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-05T01:12:56Z
- **Completed:** 2026-05-05T01:15:12Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Appended `## Phase 11 unwrapper and deramping candidates` section to `CONCLUSIONS_DISP_N_AM.md` with SoCal candidate table
- Appended `## Phase 11 unwrapper and deramping candidates` section to `CONCLUSIONS_DISP_EU.md` with Bologna candidate table
- Both sections carry forward D-08 (deformation sanity flag is Phase 12 blocker only), D-13 (ERA5 not promoted), D-14 (tophu/SNAPHU and 20x20 m fallback as later ladder steps)
- All 95 existing matrix_writer_disp + disp_candidates tests still pass

## Task Commits

1. **Task 1: Append Phase 11 candidate conclusion sections** - `944a691` (docs)

**Plan metadata:** (final commit after SUMMARY)

## Files Created/Modified

- `CONCLUSIONS_DISP_N_AM.md` - Appended Phase 11 candidate evidence section with SoCal spurt_native + phass_post_deramp BLOCKER table
- `CONCLUSIONS_DISP_EU.md` - Appended Phase 11 candidate evidence section with Bologna spurt_native + phass_post_deramp BLOCKER table

## Decisions Made

- Candidate evidence tables populated directly from `eval-disp/metrics.json` and `eval-disp-egms/metrics.json` `candidate_outcomes` arrays (T-11-05-01: repudiation mitigation)
- Null sidecar fields (r, bias_mm_yr, rmse_mm_yr, mean_ramp_rad) rendered as `—` for BLOCKER rows per D-11
- PHASS post-deramp row marked BLOCKER* with explicit note that `partial_metrics=True` means no comparable PASS/FAIL evidence exists (D-11)
- PHASS deformation sanity flagged as Phase 12 production-recommendation blocker, NOT Phase 11 metric-reporting blocker (D-08)
- ERA5 carry-forward: SoCal worsened (r: 0.0490 → 0.0071, bias: +23.62 → +55.43 mm/yr); Bologna unchanged (r: 0.3358 → 0.3358); neither meets two-signal promotion rule (D-13)
- tophu/SNAPHU and 20 x 20 m fallback referenced as "later ladder steps deferred to Phase 12" without choosing them (D-14)
- Validation-only posture explicitly stated: "Phase 12 consumes these candidate outcomes to choose production posture" (T-11-05-02)

## Deviations from Plan

None — plan executed exactly as written. The conclusion sections carry exactly the required decision traceability and use sidecar numbers verbatim.

## Issues Encountered

None.

## Known Stubs

None. All candidate outcome rows reflect real experimental results from schema-valid sidecars. BLOCKER outcomes with null metrics are not stubs — they are the correct representation of experiments that did not reach a comparable PASS/FAIL measurement (D-11).

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. T-11-05-01 mitigated: conclusion numbers copied from schema-valid `metrics.json` sidecars, not terminal logs. T-11-05-02 mitigated: validation-only posture and Phase 12 handoff explicitly stated.

## Next Phase Readiness

- Both DISP conclusion files now contain Phase 11 candidate evidence with PASS/FAIL/BLOCKER status per D-09
- All four candidate-cell BLOCKER outcomes are schema-valid, sidecar-backed, and visible in both the matrix and the conclusions
- Phase 12 can consume: spurt_native BLOCKER on both cells (SPURT not installed; broken pipe), phass_post_deramp BLOCKER* on both cells (no dolphin re-entry API; deformation sanity flagged)
- Key Phase 12 decision inputs: (1) add spurt to conda-env.yml and retry, (2) seek dolphin API for deramped-IFG time-series, or (3) escalate to tophu/SNAPHU or 20x20 m fallback

---
*Phase: 11-disp-unwrapper-deramping-candidates*
*Completed: 2026-05-05*

## Self-Check: PASSED

- CONCLUSIONS_DISP_N_AM.md: FOUND
- CONCLUSIONS_DISP_EU.md: FOUND
- 11-05-SUMMARY.md: FOUND
- 944a691 (Task 1 docs): FOUND
