---
phase: 03-disp-s1-and-dist-s1-pipelines
plan: 01
subsystem: products
tags: [dolphin, tophu, mintpy, disp-s1, displacement, insar, phase-linking, unwrapping]

# Dependency graph
requires:
  - phase: 02-rtc-s1-and-cslc-s1-pipelines
    provides: "types.py dataclass pattern, cslc.py thin-wrapper pattern, run_cslc() entry point"
provides:
  - "DISPConfig, DISPResult, DISPValidationResult dataclasses in types.py"
  - "run_disp() low-level CSLC-list orchestrator"
  - "run_disp_from_aoi() end-to-end AOI+date range pipeline"
affects: [03-03-compare-disp, validation, cli]

# Tech tracking
tech-stack:
  added: [dolphin, tophu, mintpy, pyaps3, scipy.linalg]
  patterns: [multi-stage-pipeline-orchestration, post-processing-qc-flag-and-continue, cds-credential-validation]

key-files:
  created:
    - src/subsideo/products/disp.py
    - tests/unit/test_disp_pipeline.py
  modified:
    - src/subsideo/products/types.py

key-decisions:
  - "Lazy imports for all conda-forge deps (dolphin, tophu, mintpy, scipy) inside function bodies"
  - "Post-unwrap QC uses plane-fit residual RMS, flags but does not fail pipeline"
  - "run_disp_from_aoi uses query_bursts_for_aoi from burst.frames (not burst.db)"

patterns-established:
  - "Multi-stage pipeline pattern: validate credentials -> dolphin -> mask -> unwrap -> QC -> MintPy"
  - "CDS credential fail-fast pattern: check cdsapirc before any processing"

requirements-completed: [PROD-03]

# Metrics
duration: 6min
completed: 2026-04-05
---

# Phase 03 Plan 01: DISP-S1 Pipeline Orchestrator Summary

**DISP-S1 displacement pipeline chaining dolphin phase linking, tophu unwrapping, and MintPy time-series inversion with mandatory ERA5 tropospheric correction**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-05T23:22:01Z
- **Completed:** 2026-04-05T23:28:01Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- DISP-S1 pipeline orchestrator with 5-stage processing chain (dolphin -> coherence mask -> tophu -> QC -> MintPy)
- End-to-end AOI entry point that builds CSLC stack via run_cslc() then feeds into run_disp()
- CDS credential validation fails fast before any processing starts
- Post-unwrapping planar ramp QC flags anomalies without failing the pipeline
- 10 unit tests with fully mocked conda-forge dependencies

## Task Commits

Each task was committed atomically:

1. **Task 1: Add DISP types and create disp.py orchestrator** - `b69e475` (feat)
2. **Task 2: Unit tests for DISP pipeline** - `8b5123d` (test)

## Files Created/Modified
- `src/subsideo/products/disp.py` - DISP-S1 pipeline orchestrator with run_disp() and run_disp_from_aoi()
- `src/subsideo/products/types.py` - Extended with DISPConfig, DISPResult, DISPValidationResult dataclasses
- `tests/unit/test_disp_pipeline.py` - 10 unit tests covering CDS validation, unwrap QC, template generation, full pipeline, AOI entry point

## Decisions Made
- Used `query_bursts_for_aoi` from `burst.frames` (the actual API) rather than `query_bursts` from `burst.db` (which doesn't exist)
- Coherence masking writes masked interferograms as separate files (`_masked.tif`) to preserve originals
- MintPy template uses hardcoded step list matching OPERA DISP-S1 workflow specification

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected burst query import path**
- **Found during:** Task 1 (disp.py implementation)
- **Issue:** Plan referenced `query_bursts` from `burst.db` but the actual function is `query_bursts_for_aoi` in `burst.frames`
- **Fix:** Used correct import `from subsideo.burst.frames import query_bursts_for_aoi`
- **Files modified:** src/subsideo/products/disp.py
- **Verification:** Import succeeds, function signature matches
- **Committed in:** b69e475

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential correction to use correct existing API. No scope creep.

## Issues Encountered
- Ruff lint required import sorting fix and f-string prefix removal (auto-fixed)
- Variable name `A` violated N806 naming convention, renamed to `design`

## Known Stubs
None -- all functions are fully implemented with proper error handling and lazy imports.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DISP pipeline ready for DIST-S1 (Plan 02) and EGMS validation comparison (Plan 03)
- DISPResult and DISPValidationResult types available for validation module
- run_disp_from_aoi() provides the end-to-end interface for CLI integration

## Self-Check: PASSED

All files exist, all commits verified, all tests pass, lint clean.

---
*Phase: 03-disp-s1-and-dist-s1-pipelines*
*Completed: 2026-04-05*
