---
phase: 11-disp-unwrapper-deramping-candidates
plan: "01"
subsystem: validation
tags: [disp, candidates, schema, pydantic, tdd]
dependency_graph:
  requires: []
  provides:
    - DISPCandidateOutcome schema in matrix_schema.py
    - DISPDeformationSanityCheck schema in matrix_schema.py
    - DISPCellMetrics.candidate_outcomes additive field
    - candidate_output_dir helper
    - candidate_status_from_metrics helper
    - make_candidate_blocker helper
  affects:
    - src/subsideo/validation/matrix_schema.py
    - run_eval_disp.py (consumers in later plans)
    - run_eval_disp_egms.py (consumers in later plans)
tech_stack:
  added:
    - src/subsideo/validation/disp_candidates.py (new module)
  patterns:
    - TDD RED/GREEN cycle across both tasks
    - ConfigDict(extra="forbid") for all new Pydantic models
    - Literal type aliases for strict enum-like validation
    - Additive sidecar pattern (DISPCellMetrics.candidate_outcomes with default=[])
key_files:
  created:
    - src/subsideo/validation/disp_candidates.py
    - tests/validation/__init__.py
    - tests/validation/test_disp_candidates.py
    - conftest.py (worktree path isolation)
  modified:
    - src/subsideo/validation/matrix_schema.py
decisions:
  - "DISPCandidateStatus is PASS/FAIL/BLOCKER only (D-09) — not CALIBRATING or MIXED"
  - "DISPCandidateOutcome embedded in DISPCellMetrics.candidate_outcomes as additive list (D-12)"
  - "SPURT threshold: corr >= 0.7 AND ramp < 5.0 rad AND attributed=inconclusive"
  - "PHASS threshold: corr >= 0.5 OR ramp < 1.0 rad (OR logic — softer bar post-deramping)"
  - "BLOCKER triggered only when both correlation and ramp_mean are None (insufficient metrics)"
  - "conftest.py added at worktree root to ensure worktree src takes precedence over editable install"
metrics:
  duration: "~7min"
  completed: "2026-05-04"
  tasks_completed: 2
  files_created: 4
  files_modified: 1
---

# Phase 11 Plan 01: Candidate Evidence Contract Summary

**One-liner:** Strict Pydantic candidate evidence models with deterministic PASS/FAIL/BLOCKER thresholds for SPURT native and PHASS post-deramping on SoCal/Bologna cells.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Failing tests for schema + helpers | 8be3772 | tests/validation/__init__.py, tests/validation/test_disp_candidates.py |
| 1 GREEN | Add candidate evidence models | 3629b3e | src/subsideo/validation/matrix_schema.py, conftest.py |
| 2 GREEN | Create shared candidate helpers | 5e54bcb | src/subsideo/validation/disp_candidates.py |

## What Was Built

### Schema (Task 1)

Added to `src/subsideo/validation/matrix_schema.py`:

- `DISPCandidateName = Literal["spurt_native", "phass_post_deramp"]`
- `DISPCandidateCell = Literal["socal", "bologna"]`
- `DISPCandidateStatus = Literal["PASS", "FAIL", "BLOCKER"]`
- `DISPDeformationSanityCheck(BaseModel)` — lightweight sanity check for PHASS deramping (D-07)
- `DISPCandidateOutcome(BaseModel)` — full candidate-cell evidence record with BLOCKER fields (D-09/D-10/D-11)
- `DISPCellMetrics.candidate_outcomes: list[DISPCandidateOutcome]` — additive field with `default_factory=list` (D-12)

Both new models use `ConfigDict(extra="forbid")` mitigating T-11-01-01 (schema tampering via extra fields).

### Helpers (Task 2)

Created `src/subsideo/validation/disp_candidates.py` with:

- `candidate_output_dir(base_dir, candidate) -> Path`: Returns `base_dir / "candidates" / candidate` — never the baseline eval directory (T-11-01-03).
- `candidate_status_from_metrics(candidate, *, correlation, bias_mm_yr, ramp_mean_magnitude_rad, attributed_source) -> DISPCandidateStatus`: Deterministic PASS/FAIL/BLOCKER thresholds from DISP_UNWRAPPER_SELECTION_BRIEF.md.
- `make_candidate_blocker(...) -> DISPCandidateOutcome`: Constructs schema-valid BLOCKER with all D-10 evidence fields.

No ERA5 axis in any function signature (D-13/D-14).

## Decision Traceability

| Decision | Implemented |
|----------|-------------|
| D-09: PASS/FAIL/BLOCKER statuses only | `DISPCandidateStatus = Literal["PASS", "FAIL", "BLOCKER"]` |
| D-10: BLOCKER preserves all evidence fields | `DISPCandidateOutcome` fields: failed_stage, error_summary, evidence_paths, cached_input_valid, partial_metrics |
| D-11: Partial metrics schema-valid and marked | `partial_metrics: bool = False` field on `DISPCandidateOutcome` |
| D-12: Candidate evidence additive, not replacing | `DISPCellMetrics.candidate_outcomes` is a new field; product_quality/reference_agreement/ramp_attribution unchanged |
| T-11-01-01: Schema tampering prevention | `ConfigDict(extra="forbid")` on both new models |
| T-11-01-03: Output routing tamper prevention | `candidate_output_dir` always returns `base_dir / "candidates" / candidate` |

## Test Results

- **40 tests pass** in `tests/validation/test_disp_candidates.py`
- **28 existing DISP tests pass** in `tests/reference_agreement/test_matrix_writer_disp.py` + `tests/product_quality/test_matrix_schema_disp.py` (no regressions)
- TDD RED/GREEN gates satisfied (RED: 8be3772, GREEN: 3629b3e + 5e54bcb)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree editable-install isolation**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** The `subsideo` package is installed as editable from the main repo (`file:///Volumes/Geospatial/Geospatial/subsideo`). Running `pytest` from the worktree imported the unmodified main-repo version, causing all tests to fail with `ImportError` even after schema additions.
- **Fix:** Added `conftest.py` at the worktree root to `sys.path.insert(0, worktree_src)`, ensuring worktree modifications take precedence. This is the standard pytest worktree isolation pattern.
- **Files modified:** conftest.py (new)
- **Commit:** 3629b3e

## Known Stubs

None — all schema fields are concrete Pydantic models, all helper functions implement real threshold logic. No placeholder values flow to any rendering or comparison code in this plan.

## Threat Flags

None found beyond the threat model already in the plan. Both T-11-01-01 and T-11-01-03 mitigations are implemented.

## Self-Check: PASSED

- `src/subsideo/validation/matrix_schema.py` modified — confirmed present
- `src/subsideo/validation/disp_candidates.py` created — confirmed present
- `tests/validation/test_disp_candidates.py` created — confirmed present
- Commits 8be3772, 3629b3e, 5e54bcb — confirmed in git log
- 40/40 tests pass
