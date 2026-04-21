---
phase: 07-cli-gaps-and-code-cleanup
verified: 2026-04-06T19:15:00Z
status: passed
score: 4/4 must-haves verified
gaps: []
---

# Phase 7: CLI Gaps & Code Cleanup Verification Report

**Phase Goal:** Add missing CLI entry points and clean up orphaned code identified by v1.0 milestone audit
**Verified:** 2026-04-06T19:15:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `subsideo build-db <geojson>` CLI command exists and calls `build_burst_db()` to create `~/.subsideo/eu_burst_db.sqlite` | VERIFIED | `build_db_cmd` at cli.py:107-124; `@app.command("build-db")` registered; `--help` exits 0 with GEOJSON argument and --output option; imports `build_burst_db` from `subsideo.burst.db` at line 121 |
| 2 | `subsideo validate --product-type disp` auto-fetches EGMS reference via `fetch_egms_ortho()` when `--egms` is not provided | VERIFIED | EGMS auto-fetch block at cli.py:379-403; guard `if pt == "disp" and egms_path is None:` at line 380; imports `fetch_egms_ortho` from `subsideo.validation.compare_disp` at line 389; mirrors ASF auto-fetch pattern (lazy imports, try/except with warning) |
| 3 | Orphaned `select_utm_epsg()` in `burst/tiling.py` is removed or inlined | VERIFIED | `src/subsideo/burst/tiling.py` does not exist (deleted in commit 844caf7); grep for `select_utm_epsg` in `src/` and `tests/` returns zero matches; only stale agent worktrees (`.claude/worktrees/`) retain old copies |
| 4 | Stale comment in `cli.py:42` about Plan 04 connectivity check is removed | VERIFIED | cli.py line 43 reads `# check-env` (clean separator); grep for `(existing)` returns no matches in cli.py |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/subsideo/cli.py` | build-db command and EGMS auto-fetch block | VERIFIED | `def build_db_cmd` at line 108; EGMS auto-fetch at lines 379-403; 499 lines total; substantive implementation |
| `tests/unit/test_cli.py` | Test coverage for build-db command registration | VERIFIED | Line 28 checks `"build-db"` in help output assertion list; 149 lines total |
| `src/subsideo/burst/tiling.py` | Must NOT exist | VERIFIED | File deleted |
| `tests/unit/test_burst_db.py` | No references to `select_utm_epsg` or tiling | VERIFIED | 87 lines; no imports from `subsideo.burst.tiling`; no `test_select_utm_epsg` functions |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/subsideo/cli.py` | `src/subsideo/burst/db.py` | `from subsideo.burst.db import build_burst_db` | WIRED | Import at cli.py:121; called at line 123 with `geojson_source=geojson, output_path=output`; target function exists at db.py:75 |
| `src/subsideo/cli.py` | `src/subsideo/validation/compare_disp.py` | `from subsideo.validation.compare_disp import fetch_egms_ortho` | WIRED | Import at cli.py:389; called at line 400 with `bbox=bbox, output_dir=egms_dir`; target function exists at compare_disp.py:21 |

### Data-Flow Trace (Level 4)

Not applicable -- build-db and EGMS auto-fetch are CLI commands that delegate to existing data modules. No dynamic rendering artifacts to trace.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| build-db command registered and shows help | `python3 -c "from typer.testing import CliRunner; ..." build-db --help` | Usage text with GEOJSON argument, --output, --verbose; exit code 0 | PASS |
| All 8 subcommands appear in app | `python3 -c "from subsideo.cli import app; cmds = [c.name for c in app.registered_commands]; print(cmds)"` | `['check-env', 'build-db', 'rtc', 'cslc', 'disp', 'dswx', 'dist', 'validate']` | PASS |
| tiling.py absent from filesystem | `test -f src/subsideo/burst/tiling.py` | File not found (DELETED) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| BURST-01 | 07-01-PLAN | EU-scoped burst database built from ESA burst ID maps | SATISFIED | build-db CLI command provides user-facing entry point to `build_burst_db()` -- the function itself was implemented in Phase 1 |
| VAL-04 | 07-01-PLAN | Compare DISP-S1 output against EGMS EU displacement products | SATISFIED | EGMS auto-fetch wired into validate CLI so `--egms` is no longer required; `fetch_egms_ortho()` called automatically |

No orphaned requirements found. REQUIREMENTS.md does not map any additional IDs to Phase 7 beyond what the plan claims.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| src/subsideo/cli.py | 109, 110-112, 113 | B008: typer.Argument/Option in function defaults | Info | Pre-existing pattern across all typer commands in cli.py; standard typer usage; not a Phase 7 regression |
| src/subsideo/cli.py | 110 | UP045: `Optional[Path]` instead of `Path \| None` | Info | Pre-existing style; consistent with `from typing import Optional` already imported; not a Phase 7 regression |

No TODOs, FIXMEs, placeholders, or stub implementations found in Phase 7 changes.

### Human Verification Required

None. All four success criteria are programmatically verifiable and have been confirmed.

### Gaps Summary

No gaps found. All four success criteria are fully satisfied:

1. `build-db` command is registered, shows correct help, and calls through to `build_burst_db()` with proper argument mapping.
2. EGMS auto-fetch block runs before the disp validation branch, extracts bbox from velocity files, calls `fetch_egms_ortho()`, and falls back gracefully on failure.
3. `burst/tiling.py` is deleted with no dangling references in source or tests.
4. The stale `(existing)` annotation is removed from the check-env section separator.

---

_Verified: 2026-04-06T19:15:00Z_
_Verifier: Claude (gsd-verifier)_
