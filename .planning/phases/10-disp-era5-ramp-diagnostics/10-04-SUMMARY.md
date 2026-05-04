---
phase: 10-disp-era5-ramp-diagnostics
plan: 04
subsystem: validation
tags: [disp, era5, ramp-diagnostics, egms, opera]

requires:
  - phase: 10-disp-era5-ramp-diagnostics
    provides: Diagnostic schema, ERA5 mode routing, provenance sidecars
provides:
  - Live SoCal and Bologna ERA5-on DISP diagnostic results
  - Phase 10 conclusion sections and ERA5 methodology guidance
  - Phase 11 candidate-order disposition
affects: [phase-11, disp-unwrapper-selection, validation-methodology]

tech-stack:
  added: []
  patterns: [schema-valid sidecars before conclusion edits, two-signal ERA5 promotion rule]

key-files:
  created:
    - .planning/phases/10-disp-era5-ramp-diagnostics/10-04-SUMMARY.md
  modified:
    - src/subsideo/validation/matrix_writer.py
    - tests/reference_agreement/test_matrix_writer_disp.py
    - run_eval_disp.py
    - CONCLUSIONS_DISP_N_AM.md
    - CONCLUSIONS_DISP_EU.md
    - docs/validation_methodology.md

key-decisions:
  - "ERA5-on is diagnostic only for Phase 10; neither cell met the two-signal rule."
  - "Phase 11 keeps the v1.1 order: SPURT native, PHASS deramping, tophu/SNAPHU, then 20 x 20 m fallback."

patterns-established:
  - "Conclusion sections compare fixed v1.1 baselines to schema-valid Phase 10 sidecars."
  - "Matrix rendering surfaces compact ERA5 status without collapsing product-quality, reference-agreement, and ramp-attribution evidence."

requirements-completed: [DISP-06, RTCSUP-02]

duration: live-run dominated
completed: 2026-05-04
---

# Phase 10 Plan 04 Summary

**ERA5-on DISP diagnostics completed for SoCal and Bologna, with schema-valid sidecars and no ERA5 data-access blocker; both cells remain MIXED/inconclusive.**

## Performance

- **Duration:** live EU run took 96.9 minutes after cached inputs and four SAFE redownloads
- **Completed:** 2026-05-04
- **Tasks:** 3
- **Files modified:** 6 tracked files across Task 1 and Task 3

## Accomplishments

- Added compact DISP matrix rendering for ERA5 mode, improvement-signal count, and narrowed-cause hint.
- Ran `make eval-disp-nam` and `make eval-disp-eu` with ERA5 enabled; both wrote schema-valid sidecars.
- Added `## Phase 10 ERA5 diagnostic` sections to both DISP conclusion files and `### ERA5 tropospheric diagnostic` to the validation methodology.
- Preserved Phase 11 v1.1 candidate ordering because neither cell met the two-signal rule.

## Task Commits

1. **Task 1: compact matrix rendering** - `3ded28f` (`feat(10-04): render DISP ERA5 diagnostic flags`)
2. **Task 2/3: live diagnostics, local fix, conclusions, methodology** - `0bd36e2` (`docs(10-04): record ERA5 diagnostic results`)

## Live Diagnostic Results

### SoCal / OPERA

- `make eval-disp-nam` completed after fixing cached Phase 3 SoCal `product_quality: null` handling in `run_eval_disp.py`.
- Sidecar: `eval-disp/metrics.json`, validated as `DISPCellMetrics`.
- ERA5-on metrics: `r=0.0071`, `bias=+55.4325 mm/yr`, `RMSE=70.0391 mm/yr`, `N=481,392`.
- Product-quality: `coherence_median_of_persistent=0.000`, residual `-0.04 mm/yr`.
- Ramp attribution: mean magnitude `35.59 rad`, direction sigma `124.5 deg`, label `inconclusive`.
- Status: `MIXED`.

### Bologna / EGMS

- `make eval-disp-eu` completed. No `.cdsapirc`, CDS API, ERA5 license, or ERA5 download blocker occurred.
- Four known COMPASS post-step failures were tolerated: `20210316`, `20210328`, `20210409`, `20210421`.
- Sidecar: `eval-disp-egms/metrics.json`, validated as `DISPCellMetrics`.
- ERA5-on metrics: `r=0.3358`, `bias=+3.4608 mm/yr`, `RMSE=5.2425 mm/yr`, `N=1,126,687`.
- Product-quality: `coherence_median_of_persistent=0.000`, residual `+0.14 mm/yr`.
- Ramp attribution: mean magnitude `26.00 rad`, direction sigma `117.1 deg`, label `inconclusive`.
- Status: `MIXED`.

## Decisions Made

- ERA5 is not promoted to a required Phase 11 baseline because the two-signal rule was not met in either cell.
- Product-quality, reference-agreement, and ramp-attribution remain separate in docs and matrix rendering.
- `inconclusive_narrowed` remains human-facing only; no schema pass/fail category was added for it.

## Deviations from Plan

### Auto-fixed Issues

**1. Local cached-metrics null handling**
- **Found during:** `make eval-disp-nam`
- **Issue:** cached Phase 3 SoCal metrics had `product_quality: null`, causing `AttributeError: 'NoneType' object has no attribute 'get'`.
- **Fix:** guarded the `product_quality` lookup in `run_eval_disp.py`.
- **Verification:** `python3 -m py_compile run_eval_disp.py`; successful rerun of `make eval-disp-nam`.
- **Committed in:** `0bd36e2`.

**Total deviations:** 1 auto-fixed local-code issue.
**Impact on plan:** Required to complete the planned live diagnostic; no scope expansion.

## Issues Encountered

- Bologna had four known COMPASS post-step scene failures, but the driver continued with 15 CSLCs and completed the DISP/EGMS comparison.
- The final EU terminal showed noisy `sys.excepthook` lines after writing metrics, but the command exited 0 and both sidecars validated.

## User Setup Required

None. ERA5 access worked with the existing CDS configuration.

## Next Phase Readiness

Phase 11 can consume the conclusion sections and sidecars directly. The global order remains: SPURT native first, then PHASS deramping, then tophu/SNAPHU, then 20 x 20 m fallback.

---
*Phase: 10-disp-era5-ramp-diagnostics*
*Completed: 2026-05-04*
