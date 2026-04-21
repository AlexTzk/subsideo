---
phase: 02-rtc-s1-and-cslc-s1-pipelines
plan: 01
subsystem: validation
tags: [dataclasses, numpy, scipy, scikit-image, ssim, rmse, pearson-r]

requires:
  - phase: 01-foundation-and-data-access
    provides: project structure, config patterns, burst DB schema
provides:
  - Pipeline config/result dataclasses (RTCConfig, CSLCConfig, RTCResult, CSLCResult)
  - Validation result types (RTCValidationResult, CSLCValidationResult)
  - Pure-function validation metrics (rmse, spatial_correlation, bias, ssim)
affects: [02-02, 02-03, 02-04, phase-03, phase-04]

tech-stack:
  added: [scikit-image (structural_similarity)]
  patterns: [dataclass result containers, NaN-masked numpy metrics, lazy imports for heavy deps]

key-files:
  created:
    - src/subsideo/products/__init__.py
    - src/subsideo/products/types.py
    - src/subsideo/validation/__init__.py
    - src/subsideo/validation/metrics.py
    - tests/unit/test_metrics.py
    - tests/unit/test_types.py

key-decisions:
  - "Dataclasses over Pydantic for result types -- plain containers, not settings"
  - "Lazy import for skimage in ssim() to avoid heavy import on module load"
  - "Return 0.0 on empty valid data rather than raising exceptions"

patterns-established:
  - "NaN masking: np.isfinite(predicted) & np.isfinite(reference) before all metric ops"
  - "Lazy imports for heavy optional deps (skimage) inside function body"
  - "Dataclass result containers with field(default_factory=list) for mutable defaults"

requirements-completed: [VAL-01]

duration: 3min
completed: 2026-04-05
---

# Phase 02 Plan 01: Shared Types and Validation Metrics Summary

**Pipeline dataclasses (RTCConfig, CSLCConfig, RTCResult, CSLCResult, validation results) and pure-function metrics (RMSE, Pearson r, bias, SSIM) with NaN masking**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-05T19:11:33Z
- **Completed:** 2026-04-05T19:14:24Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- 6 dataclass types defined for pipeline configs, results, and validation results
- 4 validation metric functions with NaN masking (rmse, spatial_correlation, bias, ssim)
- 18 unit tests passing (7 for types, 11 for metrics)

## Task Commits

Each task was committed atomically:

1. **Task 1: Define pipeline types and validation result models** - `288200b` (feat)
2. **Task 2: RED - failing tests for validation metrics** - `8055f32` (test)
3. **Task 2: GREEN - implement validation metrics** - `3dc2545` (feat)

## Files Created/Modified
- `src/subsideo/products/__init__.py` - Package init for products module
- `src/subsideo/products/types.py` - RTCConfig, CSLCConfig, RTCResult, CSLCResult, RTCValidationResult, CSLCValidationResult dataclasses
- `src/subsideo/validation/__init__.py` - Package init for validation module
- `src/subsideo/validation/metrics.py` - Pure-function metrics: rmse, spatial_correlation, bias, ssim
- `tests/unit/test_types.py` - 7 tests for all 6 dataclass types
- `tests/unit/test_metrics.py` - 11 tests for all 4 metric functions

## Decisions Made
- Used dataclasses (not Pydantic) for result types since they are plain containers, not settings
- Lazy import for skimage structural_similarity to avoid heavy import at module load time
- Return 0.0 on empty valid data rather than raising exceptions
- SSIM test allows negative values since uncorrelated random data can produce slightly negative SSIM

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed SSIM test assertion for random data**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** Test asserted `0.0 < ssim < 1.0` but SSIM of uncorrelated random arrays can be slightly negative (-0.01)
- **Fix:** Changed assertion to `-1.0 <= result < 1.0`
- **Files modified:** tests/unit/test_metrics.py
- **Verification:** All 11 tests pass
- **Committed in:** 3dc2545 (part of GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test assertion fix. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functions are fully implemented with real logic.

## Next Phase Readiness
- Types and metrics ready for consumption by Plans 02-04
- RTCConfig/CSLCConfig will be used by RTC and CSLC pipeline orchestrators
- Validation metrics will be used by compare_rtc.py and compare_cslc.py in Plan 04

---
*Phase: 02-rtc-s1-and-cslc-s1-pipelines*
*Completed: 2026-04-05*
