---
phase: 06-wire-unused-data-modules-opera-metadata
plan: 01
subsystem: products
tags: [ionex, metadata, opera, isce3, importlib]

# Dependency graph
requires:
  - phase: 05-fix-cross-phase-integration-wiring
    provides: correctly wired data-access calls in all product from_aoi functions
provides:
  - get_software_version() helper using importlib.metadata
  - IONEX TEC map fetch wired into CSLC pipeline with graceful degradation
  - OPERA metadata injection in all five product pipelines (RTC, CSLC, DISP, DIST, DSWx)
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - inject_opera_metadata called after validation in every product pipeline
    - get_software_version() via importlib.metadata with dev fallback

key-files:
  created:
    - tests/unit/test_metadata_wiring.py
  modified:
    - src/subsideo/_metadata.py
    - src/subsideo/products/cslc.py
    - src/subsideo/products/rtc.py
    - src/subsideo/products/disp.py
    - src/subsideo/products/dist.py
    - src/subsideo/products/dswx.py

key-decisions:
  - "get_software_version uses importlib.metadata with dev fallback for editable installs"
  - "IONEX failure warns and continues (tec_file=None) rather than failing the CSLC pipeline"

patterns-established:
  - "inject_opera_metadata called after validation, before constructing result dataclass"
  - "get_software_version() used consistently across all five pipelines instead of cfg.product_version"

requirements-completed: [DATA-05, OUT-03]

# Metrics
duration: 4min
completed: 2026-04-06
---

# Phase 06 Plan 01: IONEX/Metadata Wiring Summary

**Wired fetch_ionex into CSLC pipeline with try/except graceful degradation and injected OPERA metadata via get_software_version() into all five product pipelines**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-06T05:54:21Z
- **Completed:** 2026-04-06T05:58:30Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Added get_software_version() helper that reads version from importlib.metadata (falls back to "dev")
- Wired fetch_ionex into run_cslc_from_aoi with try/except warn-and-continue pattern
- Injected inject_opera_metadata into run_rtc, run_cslc, run_disp, run_dist with correct product_type strings
- Updated DSWx to use get_software_version() instead of cfg.product_version
- Created 8 unit tests verifying all wiring points pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add get_software_version, wire IONEX, inject metadata** - `9b7cc99` (feat)
2. **Task 2: Unit tests for IONEX wiring and metadata injection** - `3cf5605` (test)

## Files Created/Modified
- `src/subsideo/_metadata.py` - Added get_software_version() helper
- `src/subsideo/products/cslc.py` - IONEX fetch + metadata injection in run_cslc and run_cslc_from_aoi
- `src/subsideo/products/rtc.py` - Metadata injection in run_rtc
- `src/subsideo/products/disp.py` - Metadata injection in run_disp
- `src/subsideo/products/dist.py` - Metadata injection in run_dist
- `src/subsideo/products/dswx.py` - Updated to use get_software_version()
- `tests/unit/test_metadata_wiring.py` - 8 tests across 5 test classes

## Decisions Made
- get_software_version uses importlib.metadata with "dev" fallback for editable/uninstalled environments
- IONEX download failure warns and continues with tec_file=None rather than failing the entire CSLC pipeline

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing ruff F401 unused import (from_bounds) in dswx.py line 253 -- not caused by this plan's changes, not fixed per scope boundary rules.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All five product pipelines now carry OPERA-compliant identification metadata
- IONEX TEC map support enables ionospheric correction in CSLC processing
- DATA-05 and OUT-03 requirements are closed

## Self-Check: PASSED

All 7 files verified present. Both task commits (9b7cc99, 3cf5605) verified in git log.

---
*Phase: 06-wire-unused-data-modules-opera-metadata*
*Completed: 2026-04-06*
