---
phase: 03-disp-s1-and-dist-s1-pipelines
plan: 02
subsystem: products
tags: [dist-s1, disturbance, mgrs, cog, rtc-timeseries, conda-forge]

requires:
  - phase: 03-01
    provides: "DISPConfig, DISPResult, DISPValidationResult types in types.py"
  - phase: 02-01
    provides: "RTCConfig, RTCResult types and run_rtc pipeline"
provides:
  - "DISTConfig and DISTResult dataclasses in types.py"
  - "run_dist() low-level wrapper around dist_s1.run_dist_s1_workflow()"
  - "run_dist_from_aoi() end-to-end AOI+date range entry point"
  - "_aoi_to_mgrs_tiles() AOI-to-MGRS tile resolution"
  - "validate_dist_product() COG+UTM structural validation"
affects: [03-03, 04-cli, validation]

tech-stack:
  added: [dist-s1]
  patterns: [lazy-import-conda-forge, aoi-to-tile-resolution, rtc-timeseries-first]

key-files:
  created:
    - src/subsideo/products/dist.py
    - tests/unit/test_dist_pipeline.py
  modified:
    - src/subsideo/products/types.py

key-decisions:
  - "Separate validate_dist_product from validate_rtc_product to keep modules independent"
  - "Simplified MGRS tile resolution from AOI centroid (best-effort; dist-s1 validates tile availability)"
  - "Used query_bursts_for_aoi from burst.frames (not burst.db) matching existing DISP pattern"

patterns-established:
  - "AOI-to-MGRS: centroid-based UTM zone + latitude band mapping for MGRS tile IDs"
  - "RTC-first: run_dist_from_aoi builds RTC time series before calling dist-s1"

requirements-completed: [PROD-05]

duration: 4min
completed: 2026-04-05
---

# Phase 03 Plan 02: DIST-S1 Pipeline Summary

**DIST-S1 surface disturbance pipeline with run_dist() wrapping dist-s1 conda-forge package and run_dist_from_aoi() building RTC time series first**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-05T23:32:15Z
- **Completed:** 2026-04-05T23:36:28Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- DISTConfig and DISTResult dataclasses appended after DISP types in types.py
- dist.py with run_dist() wrapping dist_s1.run_dist_s1_workflow() via lazy conditional import
- run_dist_from_aoi() resolves MGRS tiles, builds RTC time series, then calls run_dist per tile
- validate_dist_product() checks COG structure, UTM CRS, and pixel size
- 8 unit tests covering validation, import errors, runtime errors, MGRS resolution, and AOI entry point

## Task Commits

Each task was committed atomically:

1. **Task 1: Add DIST types and create dist.py orchestrator** - `9f35111` (feat)
2. **Task 1 fix: Use correct burst query function** - `0d5acbd` (fix)
3. **Task 2: Unit tests for DIST pipeline** - `9438718` (test)

## Files Created/Modified
- `src/subsideo/products/types.py` - Added DISTConfig and DISTResult dataclasses after DISP types
- `src/subsideo/products/dist.py` - DIST-S1 pipeline orchestrator with run_dist and run_dist_from_aoi
- `tests/unit/test_dist_pipeline.py` - 8 unit tests with mocked dist-s1 and Phase 1/2 dependencies

## Decisions Made
- Kept validate_dist_product separate from validate_rtc_product (module independence)
- Simplified MGRS tile resolution using centroid-based UTM zone mapping (dist-s1 validates availability)
- Used query_bursts_for_aoi from burst.frames matching the DISP pipeline pattern

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed import of non-existent query_bursts function**
- **Found during:** Task 2 (unit test run)
- **Issue:** Plan specified `from subsideo.burst.db import query_bursts` but no such function exists; correct function is `query_bursts_for_aoi` in `burst.frames`
- **Fix:** Changed import to `from subsideo.burst.frames import query_bursts_for_aoi` and updated burst_id access to use `.burst_id_jpl` attribute
- **Files modified:** src/subsideo/products/dist.py
- **Verification:** All 8 tests pass
- **Committed in:** 0d5acbd

**2. [Rule 1 - Bug] Fixed unused import and bare raise**
- **Found during:** Task 1 (ruff check)
- **Issue:** `import math` unused; `raise ImportError` inside except without `from exc`
- **Fix:** Removed unused import, added `from exc` to raise chain
- **Files modified:** src/subsideo/products/dist.py
- **Verification:** ruff check passes
- **Committed in:** 9f35111 (part of initial commit after fix)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
- rio_cogeo not installed in test environment; tests use mocked rio_cogeo (autouse fixture) following existing test_rtc_pipeline.py pattern

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DIST pipeline ready for CLI integration (Phase 03-03 or Phase 04)
- dist-s1 is conda-forge-only; clear ImportError message guides installation
- validate_dist_product reusable for future validation plans

---
*Phase: 03-disp-s1-and-dist-s1-pipelines*
*Completed: 2026-04-05*
