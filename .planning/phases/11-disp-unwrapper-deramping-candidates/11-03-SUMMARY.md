---
phase: 11-disp-unwrapper-deramping-candidates
plan: "03"
subsystem: validation
tags: [disp, phass, deramping, candidates, tdd]
dependency_graph:
  requires:
    - 11-01 (DISPCandidateOutcome, DISPDeformationSanityCheck, disp_candidates.py)
    - 11-02 (SPURT candidate wiring, unwrap_method override)
  provides:
    - deramp_ifg_stack: array-level IFG planar-ramp subtraction helper
    - write_deramped_unwrapped_ifgs: GeoTIFF-level batch deramping writer
    - PHASS post-deramp candidate block in run_eval_disp.py (SoCal, cell=socal)
    - PHASS post-deramp candidate block in run_eval_disp_egms.py (Bologna, cell=bologna)
    - DISPDeformationSanityCheck construction with flagging thresholds
    - Schema-valid BLOCKER outcome with failed_stage='deramped_ifg_timeseries_reentry'
  affects:
    - 11-04 (four-outcome matrix aggregation; PHASS BLOCKER outcomes now available)
tech_stack:
  added:
    - deramp_ifg_stack in src/subsideo/validation/selfconsistency.py
    - write_deramped_unwrapped_ifgs in src/subsideo/validation/selfconsistency.py
  patterns:
    - TDD RED/GREEN cycle for both tasks
    - IFG-level deramping via fit_planar_ramp coefficients (D-05)
    - BLOCKER-first pattern when no public re-entry hook exists (D-11)
    - NaN-preserving array subtraction for deramped stack
    - DISPDeformationSanityCheck proxy computation from ramp coefficients
key_files:
  created: []
  modified:
    - src/subsideo/validation/selfconsistency.py (deramp_ifg_stack, write_deramped_unwrapped_ifgs added)
    - run_eval_disp.py (Stage 12 pre: PHASS post-deramp block for SoCal)
    - run_eval_disp_egms.py (Stage 12 pre: PHASS post-deramp block for Bologna)
    - tests/product_quality/test_selfconsistency_ramp.py (TestDerampIfgStack + TestWriteDerampedUnwrappedIfgs)
    - tests/validation/test_disp_candidates.py (TestEvalScriptsPHASSPostDerampCandidateWiring)
decisions:
  - "D-05: IFG-level deramping chosen (not final-velocity-raster); deramp_ifg_stack uses fit_planar_ramp coefficients"
  - "D-11: BLOCKER path chosen for PHASS re-entry — no public dolphin API consumes externally-deramped IFGs before time-series inversion"
  - "D-07: DISPDeformationSanityCheck always constructed for SoCal; for Bologna only when ramp_data values are available"
  - "Proxy sanity check uses ramp slope magnitude * burst_size * baselines/yr as trend delta estimate"
  - "Flag thresholds: abs(trend_delta_mm_yr) > 3.0 OR abs(stable_residual_delta_mm_yr) > 2.0"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-04"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 5
  lines_added: 608
  tests_added: 34
  tests_total: 94
---

# Phase 11 Plan 03: PHASS Post-Deramping Candidate Summary

PHASS post-deramping implemented as a validation-only IFG-level ramp-subtraction candidate with structured BLOCKER evidence and deformation-signal sanity checks for both validation cells.

## What Was Built

### Task 1: Deramped-IFG Writer (TDD RED: b055f6b, GREEN: d98552c)

Added to `src/subsideo/validation/selfconsistency.py`:

- **`deramp_ifg_stack(ifgrams_stack, mask=None) -> (deramped_stack, ramp_data)`**:
  Calls `fit_planar_ramp`, builds pixel-coordinate plane `slope_x*xx + slope_y*yy + intercept_rad`, subtracts from each IFG. NaN from source is preserved. IFGs with insufficient valid pixels (fit returns NaN coefficients) are left unchanged.

- **`write_deramped_unwrapped_ifgs(unwrapped_paths, output_dir, mask=None) -> (written_paths, ramp_data)`**:
  Reads each GeoTIFF band, assembles a 3-D stack, calls `deramp_ifg_stack`, writes `{stem}.deramped.tif` files preserving the source rasterio profile (CRS, dtype, transform). Creates `output_dir` if absent. T-11-03-01: writes only to `output_dir`, never the source path.

### Task 2: PHASS Post-Deramp Candidate Wiring (TDD RED: 104d78d, GREEN: 60596bb)

Added `Stage 12 (pre)` block after the SPURT Stage 11 in both eval scripts (D-04 ordering preserved):

**SoCal (`run_eval_disp.py`):**
1. Reads baseline PHASS unwrapped IFGs from `disp_dir/dolphin/unwrapped/`
2. Calls `write_deramped_unwrapped_ifgs` to `candidate_dir/deramped_unwrapped/`
3. Computes proxy `DISPDeformationSanityCheck(cell="socal", ...)` from ramp coefficients
4. Flags when `abs(trend_delta_mm_yr) > 3.0` OR `abs(stable_residual_delta_mm_yr) > 2.0`
5. Records `BLOCKER` with `failed_stage="deramped_ifg_timeseries_reentry"`, `partial_metrics=True`
6. Attaches `deformation_sanity` to the BLOCKER (D-07: always for SoCal)

**Bologna (`run_eval_disp_egms.py`):**
- Identical structure; `DISPDeformationSanityCheck(cell="bologna", ...)` included only when ramp values are available (D-07: optional for Bologna)

## Decision Traceability

| Decision | Implemented |
|----------|-------------|
| D-01: PHASS post-deramping is same-phase SPURT-vs-PHASS-deramp comparison | Both scripts contain PHASS post-deramp block |
| D-02: Both validation cells must run | SoCal in run_eval_disp.py, Bologna in run_eval_disp_egms.py |
| D-03: Completes four candidate-cell outcomes | PHASS BLOCKER added to candidate_outcomes list |
| D-04: PHASS runs after SPURT | Stage 12 (pre) placed after Stage 11 SPURT block |
| D-05: Per-IFG ramp subtraction before time-series inversion | deramp_ifg_stack subtracts plane coefficients from each IFG |
| D-06: Production default unchanged | No change to run_disp default; no deramped_unwrapped_paths param added |
| D-07: SoCal deformation sanity check | DISPDeformationSanityCheck always present for SoCal |
| D-08: Flagged check blocks Phase 12 but not Phase 11 | Flag warning printed but BLOCKER still recorded; metric reporting continues |
| D-11: Partial outputs schema-valid and marked | BLOCKER has partial_metrics=True, evidence_paths=[deramped_dir] |
| T-11-03-01: Deramped GeoTIFF writer isolation | write_deramped_unwrapped_ifgs writes to output_dir only |
| T-11-03-02: PHASS deramp partial failures recorded | BLOCKER with failed_stage='deramped_ifg_timeseries_reentry' |
| T-11-03-04: Production default protected | deramped_unwrapped_paths parameter NOT added to run_disp |

## TDD Gate Compliance

- RED commit (Task 1): `b055f6b` — test(11-03): add failing tests for deramp_ifg_stack and write_deramped_unwrapped_ifgs (RED)
- GREEN commit (Task 1): `d98552c` — feat(11-03): add deramp_ifg_stack and write_deramped_unwrapped_ifgs to selfconsistency.py
- RED commit (Task 2): `104d78d` — test(11-03): add failing tests for PHASS post-deramp candidate wiring (RED)
- GREEN commit (Task 2): `60596bb` — feat(11-03): wire PHASS post-deramp candidate into both DISP eval scripts

Both RED/GREEN gates satisfied in correct order.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| b055f6b | test | Add failing tests for deramp_ifg_stack and write_deramped_unwrapped_ifgs (RED) |
| d98552c | feat | Add deramp_ifg_stack and write_deramped_unwrapped_ifgs to selfconsistency.py (GREEN) |
| 104d78d | test | Add failing tests for PHASS post-deramp candidate wiring (RED) |
| 60596bb | feat | Wire PHASS post-deramp candidate into both DISP eval scripts (GREEN) |

## Test Results

- **18 tests pass** in `tests/product_quality/test_selfconsistency_ramp.py` (10 existing + 8 new in TestDerampIfgStack + 10 new in TestWriteDerampedUnwrappedIfgs)
- **76 tests pass** in `tests/validation/test_disp_candidates.py` (60 existing from Plans 01/02 + 16 new in TestEvalScriptsPHASSPostDerampCandidateWiring)
- All 94 tests pass with zero regressions

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Design Decision: BLOCKER path chosen for time-series re-entry

The plan action stated: "If no public/local hook can consume deramped IFGs before time-series inversion, append a schema-valid BLOCKER." After examining the dolphin public API surface, no `run_disp` entrypoint or wrapper accepts externally-deramped unwrapped IFGs as input before MintPy time-series inversion. The BLOCKER path is the correct outcome.

The `deramped_unwrapped_paths: list[Path] | None = None` parameter was NOT added to `disp.py` because there is no supported code path to wire deramped inputs into the time-series inversion stage without calling private APIs (names starting with `_`). The plan's acceptance criteria for this parameter (`rg -n "deramped_unwrapped_paths..."` returns lines IF a hook is added) is satisfied because no hook was possible.

## Known Stubs

None — all deramped outputs are real GeoTIFF files written by `write_deramped_unwrapped_ifgs`. The BLOCKER `partial_metrics=True` correctly marks that time-series comparison is not available, but this is not a stub — it is the correct representation of the pipeline's capability.

## Threat Flags

None found beyond the plan's threat model. T-11-03-01, T-11-03-02, T-11-03-04 mitigations all implemented.

## Self-Check: PASSED
