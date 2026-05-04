---
phase: 10-disp-era5-ramp-diagnostics
plan: 01
subsystem: validation
tags: [disp, era5, diagnostics, pydantic, product-quality]

# Dependency graph
requires:
  - phase: 04-disp-s1-comparison-adapter-honest-fail
    provides: v1.1 DISP sidecar schema and ramp attribution baseline
provides:
  - Phase 10 additive DISP ERA5 diagnostic sidecar contract
  - Deterministic two-signal ERA5 improvement helper
  - Structured cause narrowing helper preserving AttributedSource compatibility
affects: [phase-10, phase-11, disp, matrix-sidecars]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Pydantic v2 extra-forbid sidecar models
    - Pure validation helper returning schema objects

key-files:
  created:
    - src/subsideo/validation/disp_diagnostics.py
    - tests/product_quality/test_disp_diagnostics.py
  modified:
    - src/subsideo/validation/matrix_schema.py
    - tests/product_quality/test_matrix_schema_disp.py

key-decisions:
  - "Preserved attributed_source='inconclusive' compatibility; inconclusive_narrowed exists only as a human verdict inside CauseAssessment."
  - "Defined ERA5 deltas so positive values mean improvement over the baseline."
  - "Set meaningful_improvement only when at least two improvement signals are present."

patterns-established:
  - "Phase 10 DISP diagnostic schema is additive through optional DISPCellMetrics fields."
  - "ERA5 cause assessment narrows tropospheric only when ERA5-on lacks meaningful improvement."

requirements-completed: [DISP-06, RTCSUP-02]

# Metrics
duration: 4min
completed: 2026-05-04
---

# Phase 10 Plan 01: DISP ERA5 Diagnostic Contract Summary

**Additive DISP sidecar schema plus deterministic ERA5 delta and cause-narrowing helpers for Phase 10 diagnostics**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-04T05:43:04Z
- **Completed:** 2026-05-04T05:47:02Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `Era5Diagnostic` and `CauseAssessment` as optional `DISPCellMetrics` fields without changing `AttributedSource`.
- Added `classify_era5_delta()` with exact improvement signal strings and the required two-signal meaningful-improvement rule.
- Added `assess_causes_from_era5()` so no-improvement ERA5-on results eliminate only `tropospheric` while keeping remaining causes explicit.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add additive Phase 10 DISP diagnostic schema** - `ce8df90` (feat)
2. **Task 2: Add deterministic ERA5 delta and cause helpers** - `2da1c3a` (feat)

## Files Created/Modified

- `src/subsideo/validation/matrix_schema.py` - Added Phase 10 literals, `Era5Diagnostic`, `CauseAssessment`, and optional DISP metric fields.
- `tests/product_quality/test_matrix_schema_disp.py` - Added additive-schema, literal rejection, and `inconclusive_narrowed` attribution compatibility tests.
- `src/subsideo/validation/disp_diagnostics.py` - Added pure ERA5 delta classification and cause assessment helpers.
- `tests/product_quality/test_disp_diagnostics.py` - Added one-signal, two-signal, deterministic-order, and cause-narrowing helper tests.

## Decisions Made

- Followed the plan's exact cause taxonomy: `tropospheric`, `orbit`, `terrain`, `unwrapper`, `cache_or_input_provenance`.
- Kept `CacheMode` in the schema contract for downstream provenance plans even though Plan 01 does not yet attach cache provenance fields.
- Used `--no-cov` for focused pytest verification because the repo pytest config enforces global 80% coverage even for single-file task runs.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Direct `pytest` under the system interpreter could not import the `src/` package layout until rerun with `PYTHONPATH=src`.
- Focused pytest without `--no-cov` passed tests but failed the global coverage gate; focused verification was rerun with `--no-cov`.

## Verification

- `PYTHONPATH=src pytest tests/product_quality/test_matrix_schema_disp.py -q --no-cov` passed.
- `PYTHONPATH=src pytest tests/product_quality/test_disp_diagnostics.py -q --no-cov` passed.
- `PYTHONPATH=src pytest tests/product_quality/test_matrix_schema_disp.py tests/product_quality/test_disp_diagnostics.py -q --no-cov` passed.
- `PYTHONPATH=src python3 -m py_compile src/subsideo/validation/disp_diagnostics.py` passed.
- `grep -c "CauseLiteral" src/subsideo/validation/matrix_schema.py` returned `3`.
- `grep -c "Era5Diagnostic" src/subsideo/validation/matrix_schema.py` returned `2`.
- `grep -c "CauseAssessment" src/subsideo/validation/matrix_schema.py` returned `2`.
- `grep -c "inconclusive_narrowed" src/subsideo/validation/matrix_schema.py` returned `0`.

## Known Stubs

None.

## Threat Flags

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 10 can now wire ERA5-on/off eval script outputs into schema-valid DISP sidecars. Phase 11 can consume deterministic improvement signals and cause assessment fields without changing legacy v1.1 DISP sidecar compatibility.

## Self-Check: PASSED

- Found `src/subsideo/validation/matrix_schema.py`.
- Found `src/subsideo/validation/disp_diagnostics.py`.
- Found `tests/product_quality/test_matrix_schema_disp.py`.
- Found `tests/product_quality/test_disp_diagnostics.py`.
- Found `.planning/phases/10-disp-era5-ramp-diagnostics/10-01-SUMMARY.md`.
- Found task commit `ce8df90`.
- Found task commit `2da1c3a`.

---
*Phase: 10-disp-era5-ramp-diagnostics*
*Completed: 2026-05-04*
