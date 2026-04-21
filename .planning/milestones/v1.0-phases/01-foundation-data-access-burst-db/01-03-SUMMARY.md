---
phase: 01-foundation-data-access-burst-db
plan: 03
subsystem: burst-db
tags: [burst-db, sqlite, geopandas, pyproj, shapely, spatial-query]

requires:
  - "Installable subsideo package with Settings.cache_dir"
provides:
  - "BurstRecord dataclass with 8 opera-utils-compatible fields"
  - "build_burst_db() builds EU burst SQLite from ESA GeoJSON (CC-BY 4.0)"
  - "query_bursts_for_aoi() resolves AOI WKT to burst records via shapely intersection"
  - "select_utm_epsg() reads EPSG directly from burst record (no coordinate derivation)"
  - "utm_epsg_from_lon() uses pyproj for Norway/Svalbard-safe UTM zone lookup"
affects: [01-02, 02-*]

tech-stack:
  added: [geopandas, shapely, pyproj]
  patterns: [opera-utils-compatible-schema, pre-stored-epsg, spatial-intersection-query]

key-files:
  created:
    - src/subsideo/burst/db.py
    - src/subsideo/burst/frames.py
    - src/subsideo/burst/tiling.py
    - src/subsideo/utils/projections.py
    - tests/unit/test_burst_db.py
  modified: []

key-decisions:
  - "UTM EPSG is stored at DB build time via pyproj query_utm_crs_info, never derived at query time -- avoids Norway/Svalbard zone anomaly bugs"
  - "build_burst_db() is the programmatic entry point for D-05; no separate CLI subcommand needed in Phase 1"
  - "Spatial query uses Python-side shapely intersection (not SpatiaLite) -- sufficient for EU burst counts and avoids SpatiaLite dependency"

patterns-established:
  - "Pre-stored EPSG: burst records carry their UTM zone from build time"
  - "Opera-utils compatible schema: burst_id_map table with JPL and ESA burst ID columns"
  - "In-memory SQLite fixtures for unit testing (no network)"

requirements-completed: [BURST-01, BURST-02, BURST-03]

duration: 5min
completed: 2026-04-05
---

# Phase 01 Plan 03: EU Burst Database and AOI Query Layer Summary

**Opera-utils-compatible EU burst SQLite built from ESA GeoJSON with pyproj UTM zone assignment and shapely AOI intersection query**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-05T17:45:56Z
- **Completed:** 2026-04-05T17:50:54Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- BurstRecord dataclass with 8 fields matching opera-utils burst_id_map schema
- build_burst_db() pipeline: load ESA GeoJSON, filter to EU bounds (-32/27/45/72), assign UTM EPSG via pyproj, write SQLite
- query_bursts_for_aoi() resolves WKT polygons to burst records using shapely intersection
- select_utm_epsg() reads directly from BurstRecord.epsg (never re-derives from coordinates)
- utm_epsg_from_lon() uses pyproj query_utm_crs_info for Norway/Svalbard zone anomaly safety
- 6 unit tests with in-memory SQLite fixtures (no network access needed)

## Task Commits

Each task was committed atomically:

1. **Task 1: Burst DB build pipeline and data classes** - `ce7ba81` (feat)
2. **Task 2 RED: Failing tests for query and UTM selector** - `5712320` (test)
3. **Task 2 GREEN: AOI query and UTM selector implementation** - `54d9ac8` (feat)

## Files Created/Modified

- `src/subsideo/burst/db.py` - BurstRecord, get_burst_db_path(), build_burst_db(), ESA_BURST_DB_ATTRIBUTION
- `src/subsideo/burst/frames.py` - query_bursts_for_aoi() with shapely intersection
- `src/subsideo/burst/tiling.py` - select_utm_epsg() reads from burst record
- `src/subsideo/utils/projections.py` - utm_epsg_from_lon() using pyproj query_utm_crs_info
- `tests/unit/test_burst_db.py` - 6 tests with in-memory SQLite fixture (3 synthetic burst records)

## Decisions Made

- UTM EPSG is computed once at DB build time using pyproj query_utm_crs_info and stored in the burst record. This handles Norway (zone 32V) and Svalbard (zones 31X/33X/35X/37X) anomalies that break the naive formula.
- Spatial query uses Python-side shapely intersection rather than SpatiaLite. For EU burst counts (~100k records) this is fast enough and avoids adding a SpatiaLite extension dependency.
- build_burst_db() accepts both URL and local file paths for the ESA GeoJSON source via geopandas.read_file().

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered

The plan's verification step expected utm_epsg_from_lon(12.5, 45.0) == 32632, but 12.5E is actually in UTM zone 33N (zone boundary at 12E). The implementation is correct -- pyproj correctly returns 32633. The test fixtures use lon=11 (correctly in zone 32N), so no code changes were needed.

## Known Stubs

None. All functions are fully implemented. build_burst_db() requires a real ESA GeoJSON to produce a populated database, but the function itself is complete and callable.

## User Setup Required

None for unit tests. For production use, the ESA Sentinel-1 burst ID GeoJSON must be downloaded separately and passed to build_burst_db().

## Next Phase Readiness

- All Phase 2+ pipelines can use query_bursts_for_aoi() to resolve AOIs to burst IDs
- The burst DB schema is opera-utils compatible, enabling reuse of opera-utils burst tooling
- select_utm_epsg() is the single source of truth for UTM zone assignment

## Self-Check: PASSED

- All 5 created files exist on disk
- All 3 task commits found in git log (ce7ba81, 5712320, 54d9ac8)
- STATE.md: plan counter advanced to 4/4, 75% progress
- ROADMAP.md: 01-03-PLAN.md marked [x]
- REQUIREMENTS.md: BURST-01/02/03 marked complete

---
*Phase: 01-foundation-data-access-burst-db*
*Completed: 2026-04-05*
