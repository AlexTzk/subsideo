---
phase: "06"
plan: "02"
subsystem: cli-asf-autofetch
tags: [asf, validation, cli, auto-fetch, earthdata]
dependency_graph:
  requires: [data-asf, config, cli]
  provides: [validate-asf-autofetch]
  affects: [cli-validate]
tech_stack:
  added: []
  patterns: [lazy-import, bbox-reprojection, credential-gating]
key_files:
  created:
    - tests/unit/test_cli_asf_autofetch.py
  modified:
    - src/subsideo/cli.py
decisions:
  - "Lazy import for rasterio, pyproj, ASFClient inside auto-fetch try block"
  - "Auto-fetch only for rtc/cslc; disp uses --egms, dswx uses --year/--month"
  - "30-day window around file mtime as default date range when --start/--end omitted"
metrics:
  duration: "~5min"
  completed: "2026-04-06"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
requirements-completed: [DATA-06]
---

# Phase 06 Plan 02: ASF Auto-Fetch in Validate CLI Summary

**ASF auto-fetch wired into validate_cmd: RTC/CSLC reference products downloaded from ASF DAAC when --reference omitted and Earthdata credentials present**

## What Was Done

### Task 1: Wire ASF auto-fetch into validate_cmd
- Added `--start` and `--end` optional parameters for ASF reference search date range
- Inserted auto-fetch block before RTC/CSLC validation checks in `validate_cmd`
- Auto-fetch extracts product bbox, reprojects UTM to WGS84 via `pyproj.Transformer`, searches ASF DAAC with correct OPERA short names (`OPERA_L2_RTC-S1_V1`, `OPERA_L2_CSLC-S1_V1`)
- Clear error message (exit 1) when no credentials and no `--reference` provided
- All imports lazy inside try/except block for graceful degradation
- Updated existing rtc/cslc error messages to mention auto-fetch option
- **Commit:** `1de3a5f`

### Task 2: Unit tests for ASF auto-fetch
- Created `tests/unit/test_cli_asf_autofetch.py` with 4 tests in `TestASFAutoFetch` class
- `test_autofetch_called_when_reference_omitted_and_creds_present`: Verifies ASFClient.search called with correct short_name for RTC
- `test_autofetch_skipped_for_disp`: Verifies ASFClient NOT called for DISP product type
- `test_missing_creds_no_reference_exits_with_error`: Verifies exit code 1 and "Either provide --reference" message
- `test_autofetch_failure_warns_and_falls_through`: Verifies graceful warning on rasterio.open failure
- All 4 tests pass
- **Commit:** `c3c59ba`

## Deviations from Plan

None - plan executed exactly as written.

## Key Links Wired

| From | To | Via | Pattern |
|------|-----|-----|---------|
| `src/subsideo/cli.py` | `src/subsideo/data/asf.py` | `ASFClient` instantiation in validate_cmd | Lazy import inside try block |
| `src/subsideo/cli.py` | `src/subsideo/config.py` | `Settings()` for Earthdata credentials | `settings.earthdata_username` check |

## Known Stubs

None - all data paths fully wired.

## Verification

- `grep "ASFClient" src/subsideo/cli.py` -- 2 matches (import + instantiation)
- `grep "OPERA_L2_RTC-S1_V1" src/subsideo/cli.py` -- present
- `grep "EARTHDATA_USERNAME" src/subsideo/cli.py` -- present in error message
- `pytest tests/unit/test_cli_asf_autofetch.py --no-cov` -- 4 passed
- `ruff check src/subsideo/cli.py` -- no new errors (pre-existing B008 for typer pattern)

## Self-Check: PASSED

- FOUND: src/subsideo/cli.py
- FOUND: tests/unit/test_cli_asf_autofetch.py
- FOUND: 06-02-SUMMARY.md
- FOUND: commit 1de3a5f
- FOUND: commit c3c59ba
