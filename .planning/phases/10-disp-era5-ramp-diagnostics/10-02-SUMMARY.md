---
phase: 10-disp-era5-ramp-diagnostics
plan: 02
subsystem: disp
tags: [disp, era5, diagnostics, eval-scripts]

# Dependency graph
requires:
  - phase: 10-disp-era5-ramp-diagnostics
    plan: 01
    provides: additive ERA5 diagnostic sidecar schema
provides:
  - Explicit DISP ERA5 on/off pipeline toggle
  - Separate ERA5-on diagnostic output directories for SoCal and Bologna
  - ERA5 mode recorded in DISP metrics sidecars
affects: [disp, eval-disp, eval-disp-egms, phase-11]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Literal-based mode toggle
    - Warm baseline preservation through separate output directory routing

key-files:
  created:
    - .planning/phases/10-disp-era5-ramp-diagnostics/10-02-SUMMARY.md
  modified:
    - src/subsideo/products/disp.py
    - tests/unit/test_disp_pipeline.py
    - run_eval_disp.py
    - run_eval_disp_egms.py

key-decisions:
  - "ERA5-on remains the default diagnostic mode; ERA5-off disables CDS credential validation."
  - "ERA5-on eval outputs write under disp-era5-on while OUT / \"disp\" remains the warm no-ERA5/off baseline path."
  - "Plan 10-02 records era5_diagnostic.mode only; delta fields remain None until full delta classification is wired."

requirements-completed: [DISP-06]

# Metrics
duration: 4min
completed: 2026-05-04
---

# Phase 10 Plan 02: DISP ERA5 Toggle and Diagnostic Routing Summary

**ERA5 correction is now explicitly toggleable, with SoCal and Bologna ERA5-on diagnostics routed beside the preserved v1.1 no-ERA5/off baselines.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-04T05:56:13Z
- **Completed:** 2026-05-04T05:59:43Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `era5_mode: Literal["on", "off"] = "on"` to `_generate_mintpy_template()` and `run_disp()`.
- Added ERA5-off MintPy config generation with `mintpy.troposphericDelay.method = no` and `weatherModel = auto`.
- Guarded `_validate_cds_credentials(cdsapirc_path)` so missing `.cdsapirc` blocks ERA5-on only.
- Routed SoCal and Bologna ERA5-on DISP outputs to `disp-era5-on` while keeping `OUT / "disp"` as the baseline path.
- Passed `era5_mode=ERA5_MODE` from both eval scripts into `run_disp()`.
- Wrote `era5_diagnostic=Era5Diagnostic(mode=ERA5_MODE)` in both DISP metrics sidecars without inventing delta values.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add `era5_mode` to the DISP pipeline** - `895d5d1` (feat)
2. **Task 2: Route ERA5-on diagnostic outputs in both eval scripts** - `f1a5350` (feat)

## Files Created/Modified

- `src/subsideo/products/disp.py` - Added ERA5 mode validation, MintPy template switching, and CDS credential guard.
- `tests/unit/test_disp_pipeline.py` - Added ERA5-off template, credential-free ERA5-off run, and invalid-mode tests.
- `run_eval_disp.py` - Added ERA5 constants, `disp-era5-on` routing, `run_disp(..., era5_mode=ERA5_MODE)`, and sidecar mode recording.
- `run_eval_disp_egms.py` - Mirrored the SoCal ERA5 routing and sidecar mode recording for Bologna.
- `.planning/phases/10-disp-era5-ramp-diagnostics/10-02-SUMMARY.md` - Execution summary.

## Decisions Made

- Kept `ERA5_MODE` as a module constant rather than an environment variable or CLI flag, matching the existing `REFERENCE_MULTILOOK_METHOD` pattern.
- Preserved the warm baseline path explicitly via `baseline_disp_dir = OUT / "disp"` in both eval scripts.
- Left ERA5 delta fields unset because Plan 10-02 only wires diagnostic routing; full delta classification belongs to later Phase 10 work.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Focused pytest requires coverage bypass**
- **Found during:** Task 1 verification
- **Issue:** `pytest tests/unit/test_disp_pipeline.py -q` runs all 13 tests successfully but exits 1 because repo-wide coverage fail-under remains active for focused test runs.
- **Fix:** Verified the focused unit suite with `PYTHONPATH=src pytest tests/unit/test_disp_pipeline.py -q --no-cov`, matching the Plan 10-01 focused-test precedent.
- **Files modified:** None
- **Commit:** N/A

## Issues Encountered

- No CDS/ERA5 authentication gate was exercised because this plan performed code and unit verification only, not live ERA5 downloads.
- Existing untracked files `.claude/` and `marker.txt` were present and left untouched.

## Verification

- `PYTHONPATH=src pytest tests/unit/test_disp_pipeline.py -q --no-cov` passed with 13 tests.
- `python3 -m py_compile run_eval_disp.py run_eval_disp_egms.py` passed.
- `grep -c "era5_mode" src/subsideo/products/disp.py` returned `9`.
- `grep -c "mintpy.troposphericDelay.method = no" src/subsideo/products/disp.py` returned `1`.
- `grep -c "disp-era5-on" run_eval_disp.py` returned `1`.
- `grep -c "era5_mode=ERA5_MODE" run_eval_disp_egms.py` returned `1`.
- `PYTHONPATH=src pytest tests/unit/test_disp_pipeline.py -q` executed all 13 tests but failed the global coverage gate (`total of 20 is less than fail-under=80`).

## Known Stubs

None.

## Threat Flags

None - the planned CDS credential and eval-cache boundaries were handled by mode-gated credential validation and separate ERA5-on output directories.

## User Setup Required

Live ERA5-on diagnostic runs still require a valid `~/.cdsapirc`; ERA5-off local diagnostic tests do not.

## Self-Check: PASSED

- Found `src/subsideo/products/disp.py`.
- Found `tests/unit/test_disp_pipeline.py`.
- Found `run_eval_disp.py`.
- Found `run_eval_disp_egms.py`.
- Found `.planning/phases/10-disp-era5-ramp-diagnostics/10-02-SUMMARY.md`.
- Found task commit `895d5d1`.
- Found task commit `f1a5350`.

---
*Phase: 10-disp-era5-ramp-diagnostics*
*Completed: 2026-05-04*
