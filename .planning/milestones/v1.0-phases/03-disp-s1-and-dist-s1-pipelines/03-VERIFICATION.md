---
phase: 03-disp-s1-and-dist-s1-pipelines
verified: 2026-04-05T23:41:20Z
status: passed
score: 6/6 must-haves verified
---

# Phase 3: DISP-S1 and DIST-S1 Pipelines Verification Report

**Phase Goal:** Users can produce OPERA-spec surface displacement time-series and surface disturbance products from Sentinel-1 data over EU AOIs, with displacement validated against EGMS EU reference products
**Verified:** 2026-04-05T23:41:20Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | DISP pipeline chains dolphin phase linking, tophu unwrapping, and MintPy time-series inversion; post-unwrapping QC runs automatically and flags planar ramp anomalies | VERIFIED | `disp.py` lines 57-288 implement 5-stage chain (dolphin -> coherence mask -> tophu -> QC -> MintPy). `_check_unwrap_quality` (line 181) uses scipy lstsq plane fit and flags via loguru WARNING without failing pipeline. Tests `test_run_disp_mocked` and `test_run_disp_qc_warning` confirm. |
| 2 | Spatial correlation between DISP-S1 velocity and EGMS EU reference exceeds 0.92 with absolute bias below 3 mm/yr (pass criteria coded) | VERIFIED | `compare_disp.py` lines 163-169 return `DISPValidationResult` with `pass_criteria={"correlation_gt_0.92": corr > 0.92, "bias_lt_3mm_yr": abs(bias_val) < 3.0}`. Tests `test_compare_disp_pass_criteria` and `test_compare_disp_known_bias` confirm metric computation and criteria keys. |
| 3 | DIST pipeline on RTC time series produces COG GeoTIFF that passes OPERA product validator | VERIFIED | `dist.py` lines 133-215 wrap `dist_s1.run_dist_s1_workflow()` with lazy import, then call `validate_dist_product()` (lines 24-70) which checks COG validity via rio_cogeo, UTM CRS, and pixel size. Tests `test_run_dist_mocked`, `test_validate_dist_valid_cog`, `test_validate_dist_not_cog`, `test_validate_dist_non_utm` confirm. |
| 4 | run_disp_from_aoi accepts AOI geometry + date range, builds CSLC stack, then feeds to run_disp | VERIFIED | `disp.py` lines 398-566 implement full AOI entry point: resolves AOI, queries bursts, searches CDSE, fetches DEM/orbits, runs run_cslc per scene, collects CSLC paths, calls run_disp. Test `test_run_disp_from_aoi_mocked` confirms wiring. |
| 5 | run_dist_from_aoi accepts AOI + date range, resolves MGRS tiles, runs RTC, then runs dist-s1 | VERIFIED | `dist.py` lines 218-336 implement full AOI entry point: resolves MGRS tiles via `_aoi_to_mgrs_tiles`, queries bursts, searches CDSE, builds RTC time series, calls run_dist per tile. Test `test_run_dist_from_aoi_mocked` confirms run_rtc and run_dist both called. |
| 6 | All conda-forge imports (dolphin, tophu, MintPy, dist-s1, scipy) are lazy | VERIFIED | dolphin: line 69-70 inside function body. tophu: line 143. mintpy: line 264. scipy: line 190. dist_s1: line 168. All inside function bodies, not module-level. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/subsideo/products/types.py` | DISPConfig, DISPResult, DISPValidationResult, DISTConfig, DISTResult | VERIFIED | All 5 dataclasses present with correct fields (lines 81-131) |
| `src/subsideo/products/disp.py` | DISP-S1 pipeline orchestrator | VERIFIED | 567 lines, exports run_disp and run_disp_from_aoi, fully implemented |
| `src/subsideo/products/dist.py` | DIST-S1 pipeline orchestrator | VERIFIED | 337 lines, exports run_dist and run_dist_from_aoi, fully implemented |
| `src/subsideo/validation/compare_disp.py` | EGMS comparison module | VERIFIED | 171 lines, exports compare_disp and fetch_egms_ortho |
| `tests/unit/test_disp_pipeline.py` | Unit tests for DISP pipeline | VERIFIED | 453 lines, 10 test functions, all pass |
| `tests/unit/test_dist_pipeline.py` | Unit tests for DIST pipeline | VERIFIED | 328 lines, 8 test functions, all pass |
| `tests/unit/test_compare_disp.py` | Unit tests for DISP-EGMS comparison | VERIFIED | 165 lines, 8 test functions, all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| disp.py | dolphin.workflows.config.DisplacementWorkflow | lazy import line 69 | WIRED | Inside `_run_dolphin_phase_linking` function body |
| disp.py | mintpy.smallbaselineApp.TimeSeriesAnalysis | lazy import line 264 | WIRED | Inside `_run_mintpy_timeseries` function body |
| disp.py | types.py (DISPResult) | import line 18 | WIRED | Module-level import, used throughout |
| disp.py | cslc.py (run_cslc) | lazy import line 439 | WIRED | Inside `run_disp_from_aoi` |
| dist.py | dist_s1.run_dist_s1_workflow | lazy import line 168 | WIRED | Inside `run_dist` function body |
| dist.py | types.py (DISTConfig, DISTResult) | import line 13 | WIRED | Module-level import |
| dist.py | rtc.py (run_rtc) | lazy import line 250 | WIRED | Inside `run_dist_from_aoi` |
| compare_disp.py | metrics.py (spatial_correlation, bias) | import line 18 | WIRED | Module-level import, called in compare_disp |
| compare_disp.py | rasterio.warp.reproject | import line 15 | WIRED | Used in compare_disp for grid alignment |
| compare_disp.py | types.py (DISPValidationResult) | import line 17 | WIRED | Module-level import, returned by compare_disp |
| compare_disp.py | EGMStoolkit | lazy import line 41 | WIRED | Inside fetch_egms_ortho with ImportError handling |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 26 phase tests pass | `PYTHONPATH=src python -m pytest tests/unit/test_disp_pipeline.py tests/unit/test_dist_pipeline.py tests/unit/test_compare_disp.py -v` | 26 passed | PASS |
| Ruff lint clean | `ruff check src/subsideo/products/disp.py src/subsideo/products/dist.py src/subsideo/validation/compare_disp.py src/subsideo/products/types.py` | All checks passed | PASS |
| Module imports succeed | Verified via test collection (tests import all public APIs) | No import errors | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PROD-03 | 03-01-PLAN | Produce DISP-S1 displacement time-series using dolphin + tophu + MintPy | SATISFIED | `run_disp()` chains all three with lazy imports, CDS validation, coherence masking, post-unwrap QC. 10 tests pass. |
| PROD-05 | 03-02-PLAN | Produce DIST-S1 surface disturbance products from RTC time series | SATISFIED | `run_dist()` wraps dist_s1 with lazy import, COG validation. `run_dist_from_aoi()` builds RTC time series first. 8 tests pass. |
| VAL-04 | 03-03-PLAN | Compare DISP-S1 against EGMS EU displacement products (r > 0.92, bias < 3 mm/yr) | SATISFIED | `compare_disp()` reprojects to EGMS grid, applies LOS-to-vertical projection, computes correlation and bias with pass criteria thresholds. `fetch_egms_ortho()` downloads via EGMStoolkit. 8 tests pass. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | - | - | - | No TODO, FIXME, placeholder, or stub patterns detected in any phase 03 files |

### Human Verification Required

### 1. DISP Pipeline End-to-End with Real Data

**Test:** Run `run_disp_from_aoi()` on a small EU AOI with real CDSE credentials and a stack of 10+ Sentinel-1 acquisitions
**Expected:** Pipeline produces velocity.h5 with reasonable displacement values; post-unwrap QC log messages appear for any ramp anomalies
**Why human:** Requires live CDSE credentials, conda-forge deps (dolphin, tophu, MintPy), and ERA5 CDS API key; processing takes 30+ minutes

### 2. DIST Pipeline End-to-End with Real Data

**Test:** Run `run_dist_from_aoi()` on a known disturbance event AOI with real data
**Expected:** Pipeline produces COG GeoTIFF that passes `validate_dist_product()` with actual dist-s1 processing
**Why human:** Requires conda-forge dist-s1 package and live CDSE data access

### 3. EGMS Validation Accuracy

**Test:** Run `compare_disp()` comparing real DISP output against downloaded EGMS Ortho product for the same AOI
**Expected:** Spatial correlation > 0.92 and absolute velocity bias < 3 mm/yr
**Why human:** Requires real processed DISP output, EGMStoolkit installed, and EGMS data download; validates scientific accuracy

### Gaps Summary

No gaps found. All observable truths are verified. All artifacts exist, are substantive (no stubs), and are properly wired. All 26 unit tests pass. All key links are confirmed in the source code. Requirements PROD-03, PROD-05, and VAL-04 are satisfied.

Note: REQUIREMENTS.md has a git merge conflict marker on lines 110-113 (PROD-05 status) that should be resolved as a housekeeping item. This does not affect the codebase.

---

_Verified: 2026-04-05T23:41:20Z_
_Verifier: Claude (gsd-verifier)_
