---
phase: 04-dswx-s2-pipeline-and-full-interface
plan: 03
subsystem: cli
tags: [typer, cli, geojson, validation, loguru]

requires:
  - phase: 04-01
    provides: DSWx-S2 pipeline with run_dswx_from_aoi
  - phase: 04-02
    provides: Validation report generator (generate_report)
provides:
  - Complete CLI with rtc/cslc/disp/dswx/dist/validate subcommands
  - AOI GeoJSON validation helper
  - run_rtc_from_aoi and run_cslc_from_aoi wrappers
affects: []

tech-stack:
  added: []
  patterns: [lazy-import-in-command-body, aoi-validation-before-pipeline]

key-files:
  created:
    - tests/unit/test_cli.py
  modified:
    - src/subsideo/cli.py
    - src/subsideo/products/rtc.py
    - src/subsideo/products/cslc.py

key-decisions:
  - "Adapted validate --disp to use --egms flag matching actual compare_disp(egms_ortho_path=) API"
  - "Added run_rtc_from_aoi and run_cslc_from_aoi wrappers to match disp/dist/dswx pattern"
  - "dist command catches ImportError with helpful conda-forge install message"

patterns-established:
  - "CLI product subcommands: lazy import + _load_aoi + configure_logging + result.valid check"

requirements-completed: [CLI-01, CLI-02]

duration: 3min
completed: 2026-04-05
---

# Phase 4 Plan 3: Complete CLI Summary

**Typer CLI with 7 subcommands (check-env, rtc, cslc, disp, dswx, dist, validate) accepting --aoi/--start/--end/--out flags and validation report generation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-05T20:59:25Z
- **Completed:** 2026-04-05T21:02:54Z
- **Tasks:** 1
- **Files modified:** 4

## Accomplishments
- All product subcommands (rtc, cslc, disp, dswx, dist) wired with --aoi, --start, --end, --out, --verbose flags
- Validate subcommand dispatches to compare_rtc/cslc/disp/dswx and generates HTML+Markdown reports
- AOI validation helper rejects non-Polygon/MultiPolygon GeoJSON before any pipeline runs
- Added run_rtc_from_aoi and run_cslc_from_aoi to complete the from_aoi pattern across all products

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire all CLI subcommands** - `5a2dbb2` (feat)

## Files Created/Modified
- `src/subsideo/cli.py` - Complete CLI with all 7 subcommands and _load_aoi helper
- `src/subsideo/products/rtc.py` - Added run_rtc_from_aoi wrapper
- `src/subsideo/products/cslc.py` - Added run_cslc_from_aoi wrapper
- `tests/unit/test_cli.py` - 12 tests covering help output and AOI validation

## Decisions Made
- Adapted validate command's DISP path to use --egms flag matching the actual compare_disp API (takes egms_ortho_path, not aoi_wkt)
- Added run_rtc_from_aoi and run_cslc_from_aoi wrappers since only disp/dist/dswx had from_aoi entry points
- dist command wraps import in try/except with helpful conda-forge install message

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added run_rtc_from_aoi and run_cslc_from_aoi**
- **Found during:** Task 1
- **Issue:** CLI references run_rtc_from_aoi and run_cslc_from_aoi but only disp/dist/dswx had from_aoi wrappers
- **Fix:** Added from_aoi wrappers following the same pattern as dswx (CDSE search, orbit/DEM fetch, burst resolution)
- **Files modified:** src/subsideo/products/rtc.py, src/subsideo/products/cslc.py
- **Verification:** CLI imports resolve correctly, help text displays
- **Committed in:** 5a2dbb2

**2. [Rule 1 - Bug] Adapted validate --disp to match actual API**
- **Found during:** Task 1
- **Issue:** Plan used aoi_wkt parameter for compare_disp but actual API takes egms_ortho_path positionally
- **Fix:** Changed validate command to use --egms flag for EGMS reference path
- **Files modified:** src/subsideo/cli.py
- **Verification:** CLI help shows --egms flag; dispatch logic passes path correctly
- **Committed in:** 5a2dbb2

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
- Package was installed from a different worktree; reinstalled with pip to resolve import paths

## Known Stubs
None - all CLI commands wire to real product module functions.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All CLI subcommands registered and tested
- Full pipeline execution requires conda-forge dependencies (isce3, dolphin, etc.)
- Phase 04 complete pending verification

---
*Phase: 04-dswx-s2-pipeline-and-full-interface*
*Completed: 2026-04-05*
