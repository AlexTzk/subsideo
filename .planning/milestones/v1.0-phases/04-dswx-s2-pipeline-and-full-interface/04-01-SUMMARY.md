---
phase: 04-dswx-s2-pipeline-and-full-interface
plan: 01
subsystem: products
tags: [dswx, dswe, sentinel-2, water-classification, opera-metadata, cog, proteus]

requires:
  - phase: 02-rtc-cslc-pipelines
    provides: "Pipeline thin-wrapper pattern, types.py dataclasses, metrics.py, rtc.py ensure_cog pattern"
provides:
  - "DSWxConfig/DSWxResult/DSWxValidationResult dataclasses"
  - "DSWx-S2 pipeline (run_dswx, run_dswx_from_aoi) with DSWE spectral classification"
  - "Binary classification metrics (f1_score, precision_score, recall_score, overall_accuracy)"
  - "OPERA metadata injection utility (inject_opera_metadata) for GeoTIFF and HDF5"
affects: [04-02-cli-subcommands, 04-03-validation-reports, compare_dswx]

tech-stack:
  added: []
  patterns: ["OPERA metadata injection via _metadata.py shared utility", "DSWE 5-bit diagnostic spectral test pattern"]

key-files:
  created:
    - src/subsideo/products/dswx.py
    - src/subsideo/_metadata.py
    - tests/unit/test_dswx.py
    - tests/unit/test_metadata.py
    - tests/unit/test_dswx_pipeline.py
  modified:
    - src/subsideo/products/types.py
    - src/subsideo/validation/metrics.py

key-decisions:
  - "DSWE diagnostic tests use PROTEUS default thresholds mapped to S2 L2A bands (D-01)"
  - "SCL mask covers classes 3,8,9,10 (shadow, cloud med/high, cirrus) per D-02"
  - "All bands read at 20m (B11 reference grid) then resampled to 30m UTM COG per D-03"
  - "inject_opera_metadata is a shared utility for all product types (GeoTIFF + HDF5)"

patterns-established:
  - "OPERA metadata injection: call inject_opera_metadata at end of every pipeline"
  - "Binary classification metrics: f1/precision/recall/accuracy for water/disturbance validation"

requirements-completed: [PROD-04, OUT-03]

duration: 5min
completed: 2026-04-05
---

# Phase 04 Plan 01: DSWx-S2 Pipeline and OPERA Metadata Summary

**DSWE spectral water classification pipeline with five diagnostic tests (PROTEUS thresholds), SCL cloud masking, 30m UTM COG output, and shared OPERA metadata injection utility for all product types**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-06T01:04:07Z
- **Completed:** 2026-04-06T01:09:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- DSWx-S2 pipeline implementing all five DSWE diagnostic spectral tests from NASA PROTEUS
- Shared OPERA metadata injection utility supporting both GeoTIFF tags and HDF5 /identification attrs
- Four binary classification metrics (F1, precision, recall, overall accuracy) for DSWx/DIST validation
- DSWxConfig/DSWxResult/DSWxValidationResult dataclasses following established pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: DSWx types, classification metrics, and OPERA metadata utility**
   - `ed14218` (test: failing tests for types, metrics, metadata)
   - `293b487` (feat: implement types, metrics, _metadata.py)
2. **Task 2: DSWx-S2 pipeline orchestrator** - `f6558f4` (feat)

_Note: Task 1 used TDD (RED then GREEN commits)_

## Files Created/Modified
- `src/subsideo/products/types.py` - Added DSWxConfig, DSWxResult, DSWxValidationResult dataclasses
- `src/subsideo/validation/metrics.py` - Added f1_score, precision_score, recall_score, overall_accuracy
- `src/subsideo/_metadata.py` - OPERA metadata injection for GeoTIFF and HDF5 product files
- `src/subsideo/products/dswx.py` - DSWx-S2 pipeline with DSWE classification, SCL masking, COG output
- `tests/unit/test_dswx.py` - Tests for types and classification metrics (18 tests)
- `tests/unit/test_metadata.py` - Tests for OPERA metadata injection (4 tests)
- `tests/unit/test_dswx_pipeline.py` - Tests for DSWE diagnostic logic (18 tests)

## Decisions Made
- Used PROTEUS default DSWE thresholds without EU-specific tuning (per D-01: validate first, tune only if F1 < 0.90)
- SCL cloud mask covers classes 3, 8, 9, 10 (shadow, cloud med prob, cloud high prob, thin cirrus) per D-02
- All bands read at 20m resolution (B11 as reference grid) then resampled to 30m UTM COG per D-03
- inject_opera_metadata created as shared utility in _metadata.py rather than per-pipeline metadata code
- Water classification uses vectorised LUT indexing rather than np.vectorize for performance

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed all-zero band test expectation**
- **Found during:** Task 2 (pipeline tests)
- **Issue:** Test expected diagnostic=0 for all-zero bands, but MNDWI=0 > PSWT thresholds of -0.44/-0.5 means tests 4 and 5 legitimately pass
- **Fix:** Changed test to use realistic dry-land reflectance values instead of all-zeros
- **Files modified:** tests/unit/test_dswx_pipeline.py
- **Verification:** All 18 pipeline tests pass
- **Committed in:** f6558f4 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test expectation)
**Impact on plan:** Minor test correction, no scope change.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functions are fully implemented with real logic.

## Next Phase Readiness
- DSWx pipeline ready for CLI integration (04-02)
- inject_opera_metadata ready to be wired into existing RTC/CSLC/DISP pipelines
- Binary classification metrics ready for compare_dswx.py (04-03)

---
*Phase: 04-dswx-s2-pipeline-and-full-interface*
*Completed: 2026-04-05*
