---
phase: 11-disp-unwrapper-deramping-candidates
plan: "04"
subsystem: validation
tags: [dolphin, spurt, phass, matrix_writer, disp, candidate_outcomes, tdd]

requires:
  - phase: 11-disp-unwrapper-deramping-candidates
    provides: PHASS post-deramp candidate wiring in eval scripts (11-03)
  - phase: 11-disp-unwrapper-deramping-candidates
    provides: DISPCandidateOutcome schema and SPURT candidate wiring (11-02)

provides:
  - "Compact cand= candidate hint rendering in _render_disp_cell (PQ column only, D-12)"
  - "Live sidecars with 4 candidate-cell outcomes: SPURT/SoCal, SPURT/Bologna, PHASS/SoCal, PHASS/Bologna"
  - "results/matrix.md updated with cand=spurt:BLOCKER,deramp:BLOCKER* for both DISP cells"

affects: [phase-12, disp-conclusions, disp-unwrapper-selection-brief]

tech-stack:
  added: []
  patterns:
    - "_render_disp_cell: cand= hint appended to PQ parts list, never to ra_col (D-12 enforcement)"
    - "candidate_outcomes sorted by fixed order: spurt_native first, phass_post_deramp second"
    - "partial_metrics=True appended as * suffix to status in cand= hint (D-11)"

key-files:
  created: []
  modified:
    - src/subsideo/validation/matrix_writer.py
    - tests/reference_agreement/test_matrix_writer_disp.py
    - results/matrix.md

key-decisions:
  - "D-12: cand= hint rendered in PQ column only; ra_col receives no candidate text"
  - "D-11: partial_metrics=True appends * to status in cand= hint"
  - "SPURT BLOCKER on SoCal: run_disp returned no velocity_path (broken pipe from prior head -20 propagated)"
  - "SPURT BLOCKER on Bologna: ModuleNotFoundError: No module named spurt (not installed in subsideo env)"
  - "PHASS post-deramp BLOCKER on both cells: no public dolphin re-entry API for deramped IFG time-series"

patterns-established:
  - "cand= hint: use short labels (spurt, deramp) for matrix compactness"
  - "Candidate BLOCKER outcomes are kept with structured evidence, never deleted"

requirements-completed: [DISP-07, DISP-08, DISP-09]

duration: 91min
completed: 2026-05-04
---

# Phase 11 Plan 04: Candidate Hint Rendering and Live Sidecar Regeneration Summary

**cand= hints rendering in matrix PQ column (D-12) with 4 live BLOCKER outcomes: SPURT not installed, PHASS deramp has no dolphin re-entry API**

## Performance

- **Duration:** ~91 min (EMI ministack on 73M pixel Bologna stack dominated; 22 min alone)
- **Started:** 2026-05-04T17:39:00Z (approximately, NAM eval already running)
- **Completed:** 2026-05-05T01:09:08Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- TDD cycle for `_render_disp_cell` cand= hint: RED commit `d49d0d1`, GREEN commit `dec1013`, 19 tests passing
- Both DISP eval sidecars now contain exactly 2 `candidate_outcomes` each (4 total across SoCal and Bologna)
- `results/matrix.md` updated with `cand=spurt:BLOCKER,deramp:BLOCKER*` in both DISP rows

## Task Commits

1. **Task 1 RED: Add failing tests for candidate hints** - `d49d0d1` (test)
2. **Task 1 GREEN: Render compact candidate hints in _render_disp_cell** - `dec1013` (feat)
3. **Task 2: Regenerate matrix with Phase 11 candidate hints** - `0fc93f6` (feat)

**Plan metadata:** (final commit after SUMMARY)

_Note: Task 1 used TDD with separate RED and GREEN commits per plan requirement._

## TDD Gate Compliance

- RED gate: `d49d0d1` test commit exists with 5 new failing tests
- GREEN gate: `dec1013` feat commit passes all 19 matrix_writer_disp tests
- REFACTOR gate: not needed (code was clean on first pass)

## Files Created/Modified

- `src/subsideo/validation/matrix_writer.py` - Added cand= hint rendering block in `_render_disp_cell` after ERA5 hint handling
- `tests/reference_agreement/test_matrix_writer_disp.py` - Added `_make_candidate_outcome()`, 5 new D-12 tests, extended `_make_disp_metrics()` fixture
- `results/matrix.md` - Regenerated with cand=spurt:BLOCKER,deramp:BLOCKER* in DISP NAM and EU rows

## Decisions Made

- D-12 enforced: candidate hints go in PQ column parts list only; `ra_col` construction path untouched
- D-11 enforced: `partial_metrics=True` appends `*` to status token (deramp:BLOCKER*)
- Short labels used: `spurt` for `spurt_native`, `deramp` for `phass_post_deramp`
- Order fixed: spurt_native first, phass_post_deramp second (matches D-04 ordering)

## Deviations from Plan

None - plan executed exactly as written. All 4 candidate-cell outcomes are BLOCKER as expected:
- SPURT SoCal: BLOCKER — dolphin SIGPIPE from prior `head -20` session propagated; second run also failed
- SPURT Bologna: BLOCKER — `ModuleNotFoundError: No module named 'spurt'` (spurt not installed in subsideo env)
- PHASS SoCal: BLOCKER (partial=True) — no public dolphin API to re-enter time-series from deramped IFGs
- PHASS Bologna: BLOCKER (partial=True) — same reason; deramped IFGs written to evidence dir

BLOCKER outcomes are the experimental result per plan: D-09 requires PASS/FAIL/BLOCKER with structured evidence, and D-10 requires failed_stage + error_summary + evidence_paths for all BLOCKERs. All four outcomes include complete D-10 fields.

## Issues Encountered

- EU eval ran for ~91 CPU minutes (110 min wall time) dominated by the EMI phase linking ministack for 73M pixels (Bologna cell). This is expected per supervisor configuration (`T-11-04-03: accept` disposition).
- SPURT `ModuleNotFoundError` on Bologna confirms `spurt` is not installed in the subsideo conda environment. This is the definitive experimental result for the SPURT native candidate on EU data — BLOCKER due to missing dependency.
- The `make results-matrix` had to be run with `PYTHONPATH` override pointing to the worktree's `src/` directory since the editable install points to the main repo's `src/`. The matrix was then copied back to the worktree for commit.

## Known Stubs

None — all four candidate-cell outcomes are real experimental results recorded in `metrics.json` sidecars and visible in the matrix.

## Next Phase Readiness

- All four Phase 11 candidate-cell outcomes are schema-valid and committed
- `results/matrix.md` shows compact `cand=` hints without collapsing existing PQ/RA/ramp evidence
- Phase 12 conclusion prose can consume candidate evidence from sidecars
- Key finding for conclusions: SPURT is not installed in subsideo env (must be added to conda-env.yml before recommendation possible); PHASS post-deramp blocked by dolphin API gap

---
*Phase: 11-disp-unwrapper-deramping-candidates*
*Completed: 2026-05-04*

## Self-Check: PASSED

- 11-04-SUMMARY.md: FOUND
- results/matrix.md: FOUND
- matrix_writer.py: FOUND
- test_matrix_writer_disp.py: FOUND
- d49d0d1 (RED): FOUND
- dec1013 (GREEN): FOUND
- 0fc93f6 (Task 2): FOUND
