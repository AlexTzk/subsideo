---
phase: 11-disp-unwrapper-deramping-candidates
plan: "02"
subsystem: disp
tags:
  - spurt
  - unwrap-method
  - candidate-matrix
  - tdd
dependency_graph:
  requires:
    - 11-01 (candidate evidence contract: DISPCandidateOutcome, disp_candidates.py helpers)
  provides:
    - SPURT native unwrap path in run_disp via unwrap_method="spurt"
    - Stage 11 SPURT candidate blocks in both eval scripts
    - Schema-valid DISPCandidateOutcome records for spurt_native on socal and bologna
  affects:
    - 11-03 (PHASS deramping candidate, runs after SPURT per D-04 ordering)
    - 11-04 (four-outcome matrix aggregation, consumes candidate_outcomes from both scripts)
tech_stack:
  added:
    - UnwrapMethod.SPURT (dolphin) — now reachable from run_disp via unwrap_method override
  patterns:
    - Validation-only function parameter override preserving production default (D-06)
    - Isolated candidate output directory via candidate_output_dir(base, "spurt_native")
    - Graceful BLOCKER capture: exceptions and missing velocity_path -> make_candidate_blocker
    - Explicit method= kwarg on prepare_for_reference (T-11-02-03)
key_files:
  modified:
    - src/subsideo/products/disp.py (unwrap_method Literal["phass","spurt"]="phass" param on run_disp and _run_dolphin_phase_linking; ValueError guard; UnwrapMethod.SPURT/PHASS enum mapping)
    - run_eval_disp.py (Stage 11 SPURT candidate block; candidate_outcomes wired into DISPCellMetrics)
    - run_eval_disp_egms.py (Stage 11 SPURT candidate block; candidate_outcomes wired into DISPCellMetrics)
    - tests/validation/test_disp_candidates.py (TestRunDispUnwrapMethodOverride and TestEvalScriptsSPURTCandidateWiring — 20 new tests, total 60)
decisions:
  - "D-06: unwrap_method defaults to 'phass' in all signatures; SPURT is never activated without explicit caller opt-in"
  - "D-13: ERA5 axis excluded; spurt runs with era5_mode='off' only"
  - "D-14: tophu/SNAPHU fallback excluded from Phase 11 SPURT candidate path"
  - "D-04: SPURT candidate block placed before PHASS deramping in both eval scripts"
metrics:
  duration: "~45 minutes active coding (two-session execution)"
  completed: "2026-05-05T00:03:12Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
  lines_added: 574
  tests_added: 20
  tests_total: 60
---

# Phase 11 Plan 02: SPURT Native Candidate Summary

SPURT native wired as first alternative-unwrapper candidate on both validation cells (socal/bologna) via validation-only `unwrap_method="spurt"` override in `run_disp`, preserving PHASS as the production default (D-06).

## What Was Built

### Task 1: Validation-only unwrap-method override (TDD RED: a69cc97, GREEN: 4306749)

Added `unwrap_method: Literal["phass", "spurt"] = "phass"` to both `_run_dolphin_phase_linking` and `run_disp` in `src/subsideo/products/disp.py`. The parameter:

- Defaults to `"phass"` — no change for any existing caller (D-06)
- Maps `"spurt"` → `UnwrapMethod.SPURT` and `"phass"` → `UnwrapMethod.PHASS` via explicit enum assignment
- Validates before all other logic with `ValueError("unwrap_method must be 'phass' or 'spurt'")` on any other value (T-11-02-01)

### Task 2: SPURT candidate blocks in both eval scripts (GREEN: 34cd97c)

Added Stage 11 SPURT candidate blocks in `run_eval_disp.py` (cell=socal) and `run_eval_disp_egms.py` (cell=bologna) before their respective `DISPCellMetrics(...)` construction:

- Candidate directory isolated via `candidate_output_dir(OUT_DIR, "spurt_native")` (T-11-01-03)
- Runs `run_disp(sorted_h5, output_dir=spurt_candidate_dir, era5_mode="off", unwrap_method="spurt", ...)` (D-13)
- On success: compares velocity via `prepare_for_reference(method=REFERENCE_MULTILOOK_METHOD)` (T-11-02-03), builds `DISPCandidateOutcome(candidate="spurt_native", cell=..., status=candidate_status_from_metrics(...), ...)`
- On failure: catches all exceptions and missing `velocity_path` as `make_candidate_blocker(candidate="spurt_native", ...)` (T-11-02-02)
- `candidate_outcomes` list wired into `DISPCellMetrics(candidate_outcomes=candidate_outcomes)` (D-12)

## Decisions Made

- **D-06 preserved**: All existing callers unaffected — production PHASS default requires no code change.
- **D-13 applied**: `era5_mode="off"` on SPURT runs; ERA5 not added to SPURT candidate axis.
- **D-14 applied**: No tophu/SNAPHU fallback in SPURT path; tophu references in file headers are baseline pipeline docs only.
- **D-04 ordering**: SPURT Stage 11 placed before PHASS deramping Stage (which will be Plan 03/Stage 12).

## TDD Gate Compliance

- RED commit: `a69cc97` — `test(11-02): add failing tests for unwrap_method override and SPURT candidate wiring`
- GREEN commit (Task 1): `4306749` — `feat(11-02): add validation-only unwrap-method override to run_disp and _run_dolphin_phase_linking`
- GREEN commit (Task 2): `34cd97c` — `feat(11-02): wire SPURT candidate runs into both DISP eval scripts`

Both gate commits present and ordered correctly.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| a69cc97 | test | Add failing tests for unwrap_method override and SPURT candidate wiring (RED) |
| 4306749 | feat | Add validation-only unwrap-method override to run_disp and _run_dolphin_phase_linking (GREEN Task 1) |
| 34cd97c | feat | Wire SPURT candidate runs into both DISP eval scripts (GREEN Task 2) |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced beyond what the plan's threat model already covers.

## Self-Check: PASSED

Files verified:
- `src/subsideo/products/disp.py` — FOUND (two occurrences of Literal["phass","spurt"]="phass", UnwrapMethod.SPURT/PHASS, ValueError guard)
- `run_eval_disp.py` — FOUND (spurt_native, candidate_output_dir, candidate_status_from_metrics, make_candidate_blocker, method=REFERENCE_MULTILOOK_METHOD)
- `run_eval_disp_egms.py` — FOUND (same as above, cell="bologna")
- `tests/validation/test_disp_candidates.py` — FOUND (60 tests pass)

Commits verified:
- a69cc97 — FOUND in git log
- 4306749 — FOUND in git log
- 34cd97c — FOUND in git log

All 60 tests pass. py_compile clean on all three modified modules.
