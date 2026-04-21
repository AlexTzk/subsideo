---
phase: 02-rtc-s1-and-cslc-s1-pipelines
plan: 02
subsystem: products
tags: [opera-rtc, cog, rio-cogeo, rtc-s1, geotiff, ruamel-yaml]

# Dependency graph
requires:
  - phase: 01-foundation-and-data-access
    provides: "Settings config, CDSE client, DEM/orbit download, burst DB"
provides:
  - "RTC-S1 pipeline orchestrator (generate_rtc_runconfig, ensure_cog, validate_rtc_product, run_rtc)"
  - "RTCConfig and RTCResult dataclasses in products/types.py"
  - "CSLCConfig and CSLCResult dataclasses in products/types.py"
affects: [02-03-cslc-s1-pipeline, 03-disp-s1-pipeline, 04-validation]

# Tech tracking
tech-stack:
  added: [opera-rtc, rio-cogeo]
  patterns: [lazy-import-conda-deps, runconfig-yaml-generation, cog-post-processing]

key-files:
  created:
    - src/subsideo/products/__init__.py
    - src/subsideo/products/types.py
    - src/subsideo/products/rtc.py
    - tests/unit/test_rtc_pipeline.py
  modified: []

key-decisions:
  - "Lazy imports for opera-rtc and rio-cogeo inside function bodies to support partial conda installs"
  - "DEFLATE COG profile with 5 overview levels and nearest resampling"
  - "Validation checks COG structure, UTM CRS (EPSG 326xx/327xx), and 25-35m pixel size range"

patterns-established:
  - "Lazy import pattern: conda-forge-only deps imported inside function bodies, not at module level"
  - "Pipeline result pattern: dataclass with valid flag + validation_errors list"
  - "Runconfig generation: build dict, write with ruamel.yaml round-trip mode"

requirements-completed: [PROD-01, OUT-01]

# Metrics
duration: 4min
completed: 2026-04-05
---

# Phase 02 Plan 02: RTC-S1 Pipeline Summary

**RTC-S1 pipeline orchestrator wrapping opera-rtc Python API with YAML runconfig generation, COG post-processing via rio-cogeo DEFLATE, and UTM/posting validation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-05T19:11:36Z
- **Completed:** 2026-04-05T19:15:51Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- RTC-S1 pipeline orchestrator with full fetch-configure-run-validate workflow
- YAML runconfig generation matching opera-rtc RunConfig schema exactly
- COG post-processing with DEFLATE compression and 5-level overviews
- Product validation checking COG validity, UTM CRS, and 30m pixel posting
- 6 unit tests passing with mocked conda-forge dependencies

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement RTC-S1 pipeline orchestrator** - `9291f0d` (feat)
2. **Task 2: Unit tests for RTC pipeline with mocked opera-rtc** - `da24564` (test)

## Files Created/Modified
- `src/subsideo/products/__init__.py` - Package init for products module
- `src/subsideo/products/types.py` - RTCConfig, RTCResult, CSLCConfig, CSLCResult dataclasses
- `src/subsideo/products/rtc.py` - RTC-S1 pipeline: runconfig gen, COG conversion, validation, orchestration
- `tests/unit/test_rtc_pipeline.py` - 6 unit tests with mocked opera-rtc and rio-cogeo

## Decisions Made
- Lazy imports for opera-rtc and rio-cogeo inside function bodies to support partial conda installs
- DEFLATE COG profile with 5 overview levels and nearest resampling
- Validation checks COG structure, UTM CRS (EPSG 326xx/327xx), and 25-35m pixel size range

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created products/types.py with RTCConfig/RTCResult dataclasses**
- **Found during:** Task 1 (RTC pipeline implementation)
- **Issue:** Plan references types.py as "created in Plan 01" but products/ directory did not exist yet (Plan 01 likely running in parallel)
- **Fix:** Created products/__init__.py and products/types.py with RTCConfig, RTCResult, CSLCConfig, CSLCResult dataclasses matching the interface spec
- **Files modified:** src/subsideo/products/__init__.py, src/subsideo/products/types.py
- **Verification:** Imports resolve correctly
- **Committed in:** 9291f0d (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Created missing dependency file to unblock pipeline implementation. No scope creep.

## Issues Encountered
- rio_cogeo not available in the test environment (conda-forge only); handled by injecting mock modules via sys.modules in test fixture

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- RTC pipeline orchestrator ready for integration with CLI (Plan 04)
- products/types.py provides shared dataclasses for CSLC pipeline (Plan 03)
- Lazy import pattern established for all conda-forge-only dependencies

---
*Phase: 02-rtc-s1-and-cslc-s1-pipelines*
*Completed: 2026-04-05*
