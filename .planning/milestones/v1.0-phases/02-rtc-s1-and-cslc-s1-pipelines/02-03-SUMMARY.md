---
phase: 02-rtc-s1-and-cslc-s1-pipelines
plan: 03
subsystem: products
tags: [cslc, compass, hdf5, isce3, sentinel-1, sar]

requires:
  - phase: 01-foundation-and-data-access
    provides: "config.py with ruamel.yaml dump_config pattern"
provides:
  - "CSLC-S1 pipeline orchestrator: generate_cslc_runconfig, validate_cslc_product, run_cslc"
  - "CSLCConfig and CSLCResult dataclasses in products/types.py"
affects: [disp-s1-pipeline, validation]

tech-stack:
  added: [compass, h5py]
  patterns: [lazy-import-conda-deps, yaml-runconfig-generation, hdf5-product-validation]

key-files:
  created:
    - src/subsideo/products/cslc.py
    - src/subsideo/products/types.py
    - src/subsideo/products/__init__.py
    - tests/unit/test_cslc_pipeline.py
  modified: []

key-decisions:
  - "Lazy import for compass and h5py inside functions to support partial conda installs"
  - "HDF5 validation checks /data group existence rather than hardcoded dataset paths (compass version flexibility)"
  - "Burst ID extraction from output filenames uses regex pattern for compass naming convention"

patterns-established:
  - "Pipeline function pattern: config -> runconfig YAML -> compass API call -> glob outputs -> validate"
  - "HDF5 validation: existence + h5py open + required groups, not deep schema check"

requirements-completed: [PROD-02, OUT-02]

duration: 3min
completed: 2026-04-05
---

# Phase 02 Plan 03: CSLC-S1 Pipeline Summary

**CSLC-S1 pipeline orchestrator wrapping compass Python API with YAML runconfig generation and HDF5 product validation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-05T19:11:39Z
- **Completed:** 2026-04-05T19:14:54Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- CSLC-S1 pipeline with generate_cslc_runconfig, validate_cslc_product, and run_cslc functions
- Compass YAML runconfig generation matching OPERA CSLC-S1 schema (input_file_group, dynamic_ancillary_file_group, product_path_group, primary_executable)
- HDF5 product validation checking /data group, datasets, and /metadata or /identification groups
- 5 unit tests with mocked compass calls covering runconfig generation, validation, and full pipeline

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement CSLC-S1 pipeline orchestrator** - `cc53d75` (feat)
2. **Task 2: Unit tests for CSLC pipeline with mocked compass** - `07f165e` (test)

## Files Created/Modified
- `src/subsideo/products/cslc.py` - CSLC-S1 pipeline: runconfig generation, compass invocation, HDF5 validation
- `src/subsideo/products/types.py` - CSLCConfig and CSLCResult dataclasses (plus RTCConfig/RTCResult)
- `src/subsideo/products/__init__.py` - Products package init
- `tests/unit/test_cslc_pipeline.py` - 5 unit tests with mocked compass and h5py fixtures

## Decisions Made
- Lazy import for compass and h5py inside functions since they are conda-forge-only dependencies
- HDF5 validation checks /data group existence rather than hardcoded dataset paths to handle compass version differences
- Burst ID extraction from output filenames uses regex pattern matching compass naming convention (t001_123456_iw1)
- Created products/types.py with both RTC and CSLC dataclasses (parallel plan 02-01 creates same; merge will reconcile)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created products/types.py and __init__.py**
- **Found during:** Task 1
- **Issue:** Plan references types.py from Plan 01 (parallel execution), but it doesn't exist in this worktree
- **Fix:** Created products/types.py with CSLCConfig, CSLCResult, RTCConfig, RTCResult dataclasses matching plan interface spec
- **Files modified:** src/subsideo/products/types.py, src/subsideo/products/__init__.py
- **Verification:** Imports succeed
- **Committed in:** cc53d75 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Required for parallel execution. Types match plan interface spec exactly.

## Issues Encountered
None

## Known Stubs
None - all functions are fully implemented with proper error handling.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CSLC pipeline ready for integration with burst DB and data access layers
- validate_cslc_product can be extended with deeper schema checks when compass output format is confirmed
- CSLCResult feeds into DISP-S1 pipeline (Phase 3) as input CSLC stack

---
*Phase: 02-rtc-s1-and-cslc-s1-pipelines*
*Completed: 2026-04-05*
