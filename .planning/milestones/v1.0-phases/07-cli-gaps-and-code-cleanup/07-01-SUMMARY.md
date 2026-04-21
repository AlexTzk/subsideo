---
phase: 07-cli-gaps-and-code-cleanup
plan: 01
subsystem: cli
tags: [typer, cli, burst-db, egms, dead-code-removal]

requires:
  - phase: 01-config-and-data-access
    provides: burst/db.py build_burst_db function
  - phase: 03-disp-dist-egms
    provides: validation/compare_disp.py fetch_egms_ortho function

provides:
  - build-db CLI command for EU burst database creation
  - EGMS auto-fetch in validate --product-type disp
  - Dead code cleanup (tiling.py removed)

affects: []

tech-stack:
  added: []
  patterns:
    - "EGMS auto-fetch mirrors ASF auto-fetch pattern: lazy imports in try block, warning on failure"

key-files:
  created: []
  modified:
    - src/subsideo/cli.py
    - tests/unit/test_burst_db.py
    - tests/unit/test_cli.py

key-decisions:
  - "EGMS auto-fetch placed before if/elif product chain to set egms_path before disp validation block"
  - "build-db uses typer.Argument for positional geojson param, consistent with CLI UX expectation"

patterns-established:
  - "Auto-fetch pattern: standalone if-block before product validation chain, lazy imports, try/except with warning"

requirements-completed: [BURST-01, VAL-04]

duration: 4min
completed: 2026-04-06
---

# Phase 7 Plan 1: CLI Gaps and Code Cleanup Summary

**build-db CLI command, EGMS auto-fetch for DISP validation, and dead tiling.py removal**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-06T18:01:42Z
- **Completed:** 2026-04-06T18:05:15Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added `subsideo build-db <geojson>` CLI command wrapping build_burst_db
- Wired EGMS auto-fetch into `validate --product-type disp` when `--egms` omitted
- Removed orphaned `burst/tiling.py` and cleaned stale `(existing)` comment
- Updated test suite: removed dead tiling tests, added build-db to help text assertion

## Task Commits

Each task was committed atomically:

1. **Task 1: Add build-db CLI command and EGMS auto-fetch block** - `74b4912` (feat)
2. **Task 2: Remove dead code and update tests** - `844caf7` (refactor)

## Files Created/Modified
- `src/subsideo/cli.py` - Added build-db command, EGMS auto-fetch block, cleaned stale comment
- `src/subsideo/burst/tiling.py` - Deleted (dead code)
- `tests/unit/test_burst_db.py` - Removed select_utm_epsg import and tests
- `tests/unit/test_cli.py` - Added build-db to subcommand help assertion

## Decisions Made
- EGMS auto-fetch placed as standalone if-block before the if/elif product validation chain, so egms_path is set before the disp branch checks it
- build-db uses typer.Argument (positional) for geojson path, consistent with `subsideo build-db <geojson>` UX

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All v1.0 milestone CLI gaps closed
- Phase 07 complete (single plan phase)

---
*Phase: 07-cli-gaps-and-code-cleanup*
*Completed: 2026-04-06*
