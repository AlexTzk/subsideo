---
phase: 05-fix-cross-phase-integration-wiring
plan: 01
subsystem: products
tags: [rtc, cslc, cdse, burst-db, integration-wiring]

requires:
  - phase: 01-core-config-and-data-access
    provides: CDSEClient, fetch_dem, fetch_orbit, query_bursts_for_aoi, Settings
  - phase: 02-rtc-s1-and-cslc-s1-pipelines
    provides: run_rtc_from_aoi, run_cslc_from_aoi functions
provides:
  - Corrected run_rtc_from_aoi with all 5 data-access calls matching Phase 1 API
  - Corrected run_cslc_from_aoi with identical fixes
  - Unit tests verifying correct argument passing for all call sites
affects: [05-02, validation, cli]

tech-stack:
  added: []
  patterns:
    - "Settings() instantiation inside from_aoi functions for credential injection"
    - "Burst query before DEM fetch to get output_epsg from BurstRecord"
    - "STAC item metadata extraction for orbit fetch (sensing_time, satellite)"

key-files:
  created: []
  modified:
    - src/subsideo/products/rtc.py
    - src/subsideo/products/cslc.py
    - tests/unit/test_rtc_pipeline.py
    - tests/unit/test_cslc_pipeline.py

key-decisions:
  - "Reordered data-access block: search -> burst query -> DEM -> orbit -> download (burst epsg needed before DEM fetch)"
  - "Added empty-burst early-exit guard returning valid=False with descriptive error"

patterns-established:
  - "from_aoi wiring pattern: Settings -> CDSEClient(creds) -> search_stac -> burst query -> fetch_dem(epsg) -> fetch_orbit(metadata) -> download -> run_pipeline"

requirements-completed: [DATA-01, DATA-03, DATA-04]

duration: 4min
completed: 2026-04-06
---

# Phase 05 Plan 01: Fix RTC and CSLC from_aoi Integration Wiring Summary

**Fixed all 5 integration bugs (CDSEClient credentials, search_stac, burst query, fetch_orbit, fetch_dem) in run_rtc_from_aoi and run_cslc_from_aoi**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-06T05:28:34Z
- **Completed:** 2026-04-06T05:33:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Fixed B-01: CDSEClient now receives client_id/client_secret from Settings instead of empty constructor
- Fixed B-02: search_stac replaces nonexistent search() method with correct kwargs (SENTINEL-1, IW_SLC__1S)
- Fixed B-03: query_bursts_for_aoi from burst.frames replaces nonexistent BurstDB.query_by_geometry
- Fixed B-04: fetch_orbit receives sensing_time/satellite/output_dir named args from STAC item metadata
- Fixed B-05: fetch_dem receives output_epsg from burst record and returns tuple (path, profile)
- Added unit tests verifying all 5 fixes in both RTC and CSLC from_aoi functions

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix run_rtc_from_aoi and run_cslc_from_aoi (B-01 through B-05)** - `6e0d777` (fix)
2. **Task 2: Add unit tests for run_rtc_from_aoi and run_cslc_from_aoi** - `828d888` (test)

## Files Created/Modified
- `src/subsideo/products/rtc.py` - Fixed all 5 data-access call sites in run_rtc_from_aoi
- `src/subsideo/products/cslc.py` - Fixed identical 5 bugs in run_cslc_from_aoi
- `tests/unit/test_rtc_pipeline.py` - Added test_run_rtc_from_aoi_mocked with 5 assertion groups
- `tests/unit/test_cslc_pipeline.py` - Added test_run_cslc_from_aoi_mocked with 5 assertion groups

## Decisions Made
- Reordered data-access block so burst query comes before DEM fetch (burst epsg needed for output_epsg)
- Added empty-burst early-exit guard returning valid=False with descriptive error message
- Used .rstrip("Z") on STAC datetime for Python 3.10 compatibility with fromisoformat

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all data-access calls are wired to real Phase 1 module APIs.

## Next Phase Readiness
- RTC and CSLC from_aoi functions now correctly call all Phase 1 data-access modules
- Plan 05-02 can proceed with remaining product fixes (disp, dswx, dist)
- All 13 existing + new unit tests pass

---
*Phase: 05-fix-cross-phase-integration-wiring*
*Completed: 2026-04-06*
