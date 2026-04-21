---
phase: 02-rtc-s1-and-cslc-s1-pipelines
plan: 04
subsystem: validation
tags: [validation, rtc, cslc, comparison, metrics]
dependency_graph:
  requires: [02-01, 02-02, 02-03]
  provides: [compare_rtc, compare_cslc, RTCValidationResult, CSLCValidationResult]
  affects: [validation-reporting, cli-validate]
tech_stack:
  added: []
  patterns: [interferometric-phase-comparison, db-domain-rtc-validation, rasterio-reproject-grid-alignment]
key_files:
  created:
    - src/subsideo/validation/compare_rtc.py
    - src/subsideo/validation/compare_cslc.py
    - tests/unit/test_compare_rtc.py
    - tests/unit/test_compare_cslc.py
  modified: []
decisions:
  - "dB-domain comparison for RTC (10*log10) per Pitfall 5 -- RMSE 0.5 dB threshold requires dB comparison"
  - "Interferometric phase via conj multiplication per Pitfall 2 -- angle(prod*conj(ref)) cancels slant range"
  - "Grid alignment reprojects product to reference (not vice versa) per Pitfall 3"
  - "30 dB data_range for SSIM based on typical SAR dynamic range"
metrics:
  duration: 2min
  completed: "2026-04-05T19:22:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 0
requirements-completed: [VAL-02, VAL-03]
---

# Phase 02 Plan 04: Validation Comparison Modules Summary

RTC and CSLC comparison modules that load subsideo products and OPERA N.Am. references, align grids, convert to domain-appropriate representations, and compute pass/fail metrics against REQUIREMENTS.md thresholds.

## Completed Tasks

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Implement RTC and CSLC comparison modules | 4c2ffcf | compare_rtc.py, compare_cslc.py |
| 2 | Unit tests for comparison modules | c3f6067 | test_compare_rtc.py, test_compare_cslc.py |

## Key Implementation Details

**RTC Comparison (`compare_rtc`):**
- Loads reference GeoTIFF as target grid
- Reprojects product to reference CRS/transform via rasterio.warp.reproject
- Converts both to dB domain (10*log10) before metrics
- Computes RMSE, correlation, bias, SSIM using shared metrics module
- Pass criteria: RMSE < 0.5 dB, correlation > 0.99

**CSLC Comparison (`compare_cslc`):**
- Loads complex HDF5 data with multi-path fallback (/data/VV, /science/SENTINEL1/CSLC/grids/VV, etc.)
- Computes interferometric phase via conjugate multiplication (not naive angle difference)
- Masks zero-amplitude pixels to avoid division by zero
- Pass criteria: phase RMS < 0.05 rad

## Decisions Made

1. **dB-domain for RTC:** RMSE threshold of 0.5 dB requires dB-space comparison; linear-domain RMSE would be meaningless
2. **Interferometric phase for CSLC:** angle(prod * conj(ref)) cancels common slant range path; naive angle subtraction is physically wrong
3. **Product-to-reference reprojection:** Reference grid is authoritative; resampling the reference would alter the validation baseline
4. **30 dB SSIM data_range:** Typical SAR backscatter spans ~30 dB dynamic range

## Verification

- All 7 unit tests pass (3 RTC + 4 CSLC)
- ruff check passes on all new files
- Module imports verified

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None -- all functions are fully implemented with real logic.

## Self-Check: PASSED

All 4 created files verified on disk. Both commit hashes (4c2ffcf, c3f6067) found in git log.
