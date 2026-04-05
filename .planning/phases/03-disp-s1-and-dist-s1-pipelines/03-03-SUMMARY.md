---
phase: 03-disp-s1-and-dist-s1-pipelines
plan: 03
subsystem: validation
tags: [egms, disp-s1, validation, displacement, los-projection, egmstoolkit]

# Dependency graph
requires:
  - phase: 03-disp-s1-and-dist-s1-pipelines
    plan: 01
    provides: "DISPValidationResult dataclass in types.py"
  - phase: 02-rtc-s1-and-cslc-s1-pipelines
    provides: "compare_rtc.py pattern, metrics.py shared functions"

provides:
  - "compare_disp() for DISP-EGMS velocity comparison"
  - "fetch_egms_ortho() for EGMS Ortho product download"
  - "_los_to_vertical() for LOS-to-vertical projection"

affects:
  - "validation/ module: adds DISP comparison capability"

# Tech stack
tech-stack:
  added: [EGMStoolkit]
  patterns: [lazy-import, grid-alignment, los-projection]

# Key files
key-files:
  created:
    - src/subsideo/validation/compare_disp.py
    - tests/unit/test_compare_disp.py
  modified: []

# Decisions
decisions:
  - "EGMStoolkit imported lazily inside fetch_egms_ortho to handle optional dependency"
  - "LOS-to-vertical projection uses cos(theta) division with NaN for zero cosine"
  - "Grid alignment always reprojects subsideo output to EGMS grid (never vice versa)"

# Metrics
metrics:
  duration: "2min"
  completed: "2026-04-05T23:34:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 0
---

# Phase 03 Plan 03: DISP-EGMS Validation Comparison Summary

EGMS Ortho comparison module with LOS-to-vertical projection, EGMStoolkit download, and grid-aligned metric computation (r > 0.92, bias < 3 mm/yr pass criteria).

## What Was Built

### compare_disp.py

- `fetch_egms_ortho(bbox, output_dir)` -- downloads EGMS Ortho vertical displacement product using EGMStoolkit lazy import. Raises ImportError with install instructions if toolkit missing.
- `_los_to_vertical(los_velocity, incidence_angle)` -- projects LOS velocity to vertical via `v_los / cos(theta)`. Supports scalar (mean fallback) and per-pixel incidence angle arrays.
- `compare_disp(product_path, egms_ortho_path, incidence_angle_path, mean_incidence_deg)` -- main comparison: loads EGMS reference grid, reprojects DISP product to match, applies LOS-to-vertical projection, masks to intersection of valid pixels, computes correlation and bias via shared metrics module.

### test_compare_disp.py

8 tests covering:
- LOS-to-vertical with scalar and array incidence angles
- Identical arrays (r > 0.99, bias ~ 0)
- Known bias detection (2 mm/yr offset)
- Partial NaN overlap handling
- Pass criteria key verification
- EGMStoolkit ImportError when missing
- Mocked EGMStoolkit download returns valid .tif path

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | e36a23a | DISP-EGMS validation comparison module |
| 2 | 5436bdf | Unit tests for DISP-EGMS comparison |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ruff B904 `raise from` chain**
- **Found during:** Task 1 verification
- **Issue:** ImportError re-raise in `fetch_egms_ortho` was missing `from err` chain
- **Fix:** Changed `raise ImportError(...)` to `raise ImportError(...) from err`
- **Files modified:** src/subsideo/validation/compare_disp.py
- **Commit:** e36a23a (included in task commit)

## Known Stubs

None -- all functions are fully implemented with real logic. EGMStoolkit download is a real call (not stubbed); it will work when the package is installed.

## Self-Check: PASSED
