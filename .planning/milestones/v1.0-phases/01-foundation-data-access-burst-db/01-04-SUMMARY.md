---
phase: 01-foundation-data-access-burst-db
plan: 04
subsystem: data
tags: [dem-stitcher, sentineleof, s1-orbits, ionex, asf-search, earthaccess, cddis]

requires:
  - "01-01: Settings class with earthdata credentials and cache_dir/work_dir paths"
provides:
  - "fetch_dem() -- dem-stitcher wrapper with GLO-30 download and UTM warp at 30m posting"
  - "fetch_orbit() -- sentineleof primary with s1-orbits AWS fallback for Sentinel-1 orbits"
  - "fetch_ionex() -- CDDIS GNSS IONEX download with Earthdata Basic auth"
  - "ASFClient -- asf-search + earthaccess for OPERA N.Am. validation product search/download"
affects: [02-rtc-pipeline, 02-cslc-pipeline, 03-disp-pipeline, 04-validation]

tech-stack:
  added: [dem-stitcher, sentineleof, s1-orbits, asf-search, earthaccess]
  patterns: [library-wrapping, fallback-chain, mocked-network-tests]

key-files:
  created:
    - src/subsideo/data/dem.py
    - src/subsideo/data/orbits.py
    - src/subsideo/data/ionosphere.py
    - src/subsideo/data/asf.py
    - tests/unit/test_dem.py
    - tests/unit/test_orbits.py
    - tests/unit/test_ionosphere.py
    - tests/unit/test_asf.py
  modified: []

key-decisions:
  - "Used rasterio.band() for in-memory reproject to avoid writing intermediate WGS84 DEM to disk"
  - "Lazy imports for eof.download and s1_orbits in fetch_orbit() to avoid import errors when only one backend is installed"

patterns-established:
  - "Library-wrapping: thin wrappers around purpose-built libraries (dem-stitcher, sentineleof) rather than hand-rolling download logic"
  - "Fallback chain: try-except around primary library, fall back to alternative (sentineleof -> s1-orbits)"
  - "Mock-at-module-boundary: mock subsideo.data.X.library_func, not the library directly"

requirements-completed: [DATA-03, DATA-04, DATA-05, DATA-06]

duration: 5min
completed: 2026-04-05
---

# Phase 01 Plan 04: Ancillary Data Modules Summary

**DEM/orbit/ionosphere/ASF download modules wrapping dem-stitcher, sentineleof, s1-orbits, and asf-search with 27 mocked unit tests**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-05T17:45:50Z
- **Completed:** 2026-04-05T17:51:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Four ancillary data modules covering all Phase 2+ pipeline prerequisites (DEM, orbits, ionosphere TEC, validation products)
- 27 unit tests with fully mocked external libraries (no network calls)
- Fallback chain for orbit download: sentineleof (ESA POD hub) -> s1-orbits (AWS)

## Task Commits

Each task was committed atomically:

1. **Task 1: DEM and orbit ancillary download modules** - `6041713` (feat)
2. **Task 2: IONEX and ASF DAAC access modules** - `8888b11` (feat)

## Files Created/Modified
- `src/subsideo/data/dem.py` - fetch_dem() wrapping dem-stitcher with GLO-30 + UTM warp
- `src/subsideo/data/orbits.py` - fetch_orbit() with sentineleof/s1-orbits fallback
- `src/subsideo/data/ionosphere.py` - fetch_ionex() downloading CDDIS IONEX with Earthdata auth
- `src/subsideo/data/asf.py` - ASFClient wrapping asf-search + earthaccess (validation-only)
- `tests/unit/test_dem.py` - 6 tests for DEM download and warp
- `tests/unit/test_orbits.py` - 5 tests for orbit download with fallback
- `tests/unit/test_ionosphere.py` - 7 tests for IONEX URL construction, auth, file writing
- `tests/unit/test_asf.py` - 9 tests for ASF search and download

## Decisions Made
- Used lazy imports for `eof.download` and `s1_orbits` inside `fetch_orbit()` to avoid import errors when only one orbit backend is installed in the environment.
- rasterio.band() used for in-memory reproject workflow -- avoids writing an intermediate WGS84 DEM to disk.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added rasterio.band mock to DEM tests**
- **Found during:** Task 1 (test verification)
- **Issue:** rasterio.band() calls dataset.dtypes which returns empty set on a MagicMock, causing KeyError
- **Fix:** Added `mocker.patch("subsideo.data.dem.rasterio.band")` to the _mock_rasterio fixture
- **Files modified:** tests/unit/test_dem.py
- **Verification:** All 6 DEM tests pass
- **Committed in:** 6041713 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test fixture fix. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All four ancillary data modules ready for Phase 2 pipeline consumption
- DEM, orbit, ionosphere, and ASF validation products can be fetched via clean API
- Full unit test suite (35 tests across all Phase 01 plans) passes

---
*Phase: 01-foundation-data-access-burst-db*
*Completed: 2026-04-05*
