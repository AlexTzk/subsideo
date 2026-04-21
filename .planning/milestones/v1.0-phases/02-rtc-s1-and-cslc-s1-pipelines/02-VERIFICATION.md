---
phase: 02-rtc-s1-and-cslc-s1-pipelines
verified: 2026-04-05T12:00:00Z
status: passed
score: 5/5 success criteria verified
re_verification: false
---

# Phase 2: RTC-S1 and CSLC-S1 Pipelines Verification Report

**Phase Goal:** Users can produce OPERA-spec RTC backscatter and CSLC coregistered SLC products from Sentinel-1 IW SLC data over EU AOIs, with per-product validation against OPERA North America reference products
**Verified:** 2026-04-05
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | RTC pipeline produces COG GeoTIFF at 30m UTM posting that passes product validator | VERIFIED | `run_rtc()` generates opera-rtc runconfig, invokes `RunConfig.load_from_yaml` + `run_parallel`, COG-converts via `cog_translate`, validates UTM CRS (EPSG 326xx/327xx) and 25-35m pixel size. Tests: `test_run_rtc_mocked`, `test_validate_rtc_product_valid`, `test_validate_rtc_product_bad_crs` all pass. |
| 2 | CSLC pipeline produces HDF5 following OPERA CSLC spec hierarchy readable by opera-utils | VERIFIED | `run_cslc()` generates compass runconfig, invokes `compass.s1_cslc.run(grid_type="geo")`, validates HDF5 for `/data` group with datasets and `/metadata` or `/identification` group via h5py. Tests: `test_run_cslc_mocked`, `test_validate_cslc_product_valid`, `test_validate_cslc_product_missing_data` all pass. |
| 3 | RTC RMSE < 0.5 dB with correlation > 0.99 (comparison in dB domain) | VERIFIED | `compare_rtc()` reprojects product to reference grid via `rasterio.warp.reproject`, converts to dB (`10*log10`), computes all metrics via shared `metrics.py`, returns `RTCValidationResult` with `pass_criteria["rmse_lt_0.5dB"]` and `pass_criteria["correlation_gt_0.99"]`. Tests: `test_compare_rtc_identical` (rmse=0, r=1.0), `test_compare_rtc_with_offset`, `test_compare_rtc_handles_zeros` all pass. |
| 4 | CSLC phase RMS < 0.05 rad (interferometric phase comparison) | VERIFIED | `compare_cslc()` loads complex data via h5py, computes `angle(product * conj(reference))` (not naive subtraction), returns `CSLCValidationResult` with `pass_criteria["phase_rms_lt_0.05rad"]`. Tests: `test_compare_cslc_identical` (phase_rms=0), `test_compare_cslc_with_phase_shift` (0.01 rad passes), `test_compare_cslc_large_phase_fails` (0.1 rad fails) all pass. |
| 5 | VAL-01 metric functions return correct values on synthetic test arrays | VERIFIED | `metrics.py` implements `rmse`, `spatial_correlation`, `bias`, `ssim` with NaN masking (`np.isfinite`). Uses `scipy.stats.pearsonr` and `skimage.metrics.structural_similarity`. 11 unit tests pass covering exact values, NaN masking, edge cases. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/subsideo/products/__init__.py` | Package init | VERIFIED | Exists (1 line) |
| `src/subsideo/products/types.py` | 6 dataclasses (RTCConfig, CSLCConfig, RTCResult, CSLCResult, RTCValidationResult, CSLCValidationResult) | VERIFIED | 77 lines, all 6 dataclasses present with correct fields |
| `src/subsideo/validation/__init__.py` | Package init | VERIFIED | Exists (empty file) |
| `src/subsideo/validation/metrics.py` | 4 metric functions (rmse, spatial_correlation, bias, ssim) | VERIFIED | 82 lines, all 4 functions with NaN masking, scipy/skimage imports |
| `src/subsideo/products/rtc.py` | RTC pipeline orchestrator (min 100 lines) | VERIFIED | 252 lines with generate_rtc_runconfig, ensure_cog, validate_rtc_product, run_rtc |
| `src/subsideo/products/cslc.py` | CSLC pipeline orchestrator (min 80 lines) | VERIFIED | 229 lines with generate_cslc_runconfig, validate_cslc_product, run_cslc |
| `src/subsideo/validation/compare_rtc.py` | RTC comparison module (min 50 lines) | VERIFIED | 72 lines with compare_rtc, dB conversion, grid alignment |
| `src/subsideo/validation/compare_cslc.py` | CSLC comparison module (min 50 lines) | VERIFIED | 93 lines with compare_cslc, interferometric phase, coherence |
| `tests/unit/test_types.py` | Type instantiation tests | VERIFIED | 93 lines, 7 tests |
| `tests/unit/test_metrics.py` | Metric function tests (min 60 lines) | VERIFIED | 79 lines, 11 tests |
| `tests/unit/test_rtc_pipeline.py` | RTC pipeline tests (min 60 lines) | VERIFIED | 209 lines, 6 tests |
| `tests/unit/test_cslc_pipeline.py` | CSLC pipeline tests (min 50 lines) | VERIFIED | 138 lines, 5 tests |
| `tests/unit/test_compare_rtc.py` | RTC comparison tests (min 40 lines) | VERIFIED | 83 lines, 3 tests |
| `tests/unit/test_compare_cslc.py` | CSLC comparison tests (min 40 lines) | VERIFIED | 86 lines, 4 tests |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `metrics.py` | `scipy.stats.pearsonr` | import | WIRED | `from scipy import stats` at line 9; `stats.pearsonr(p, r)` at line 36 |
| `metrics.py` | `skimage.metrics.structural_similarity` | lazy import in ssim() | WIRED | `from skimage.metrics import structural_similarity` at line 65 |
| `rtc.py` | `rtc.runconfig.RunConfig` | lazy import | WIRED | `RunConfig.load_from_yaml(str(runconfig_yaml))` at line 217 |
| `rtc.py` | `rtc.rtc_s1.run_parallel` | lazy import | WIRED | `run_parallel(opera_cfg, ...)` at line 220 |
| `rtc.py` | `rio_cogeo.cogeo.cog_translate` | import in ensure_cog | WIRED | `cog_translate(str(input_tif), ...)` at lines 97-109 |
| `cslc.py` | `compass.s1_cslc.run` | lazy import | WIRED | `compass_run(run_config_path=str(runconfig_yaml), grid_type="geo")` at line 180 |
| `cslc.py` | `h5py.File` | import in validate_cslc_product | WIRED | `h5py.File(path, "r")` at line 100 |
| `compare_rtc.py` | `metrics.py` | import rmse, spatial_correlation, bias, ssim | WIRED | `from subsideo.validation.metrics import bias, rmse, spatial_correlation, ssim` at line 12 |
| `compare_rtc.py` | `rasterio.warp.reproject` | grid alignment | WIRED | `reproject(source=rasterio.band(prod, 1), ...)` at lines 39-45 |
| `compare_cslc.py` | `h5py.File` | CSLC HDF5 reading | WIRED | `h5py.File(hdf5_path, "r")` at lines 26, 35 |

### Data-Flow Trace (Level 4)

Not applicable -- these modules are pipeline orchestrators and comparison functions that operate on external data (Sentinel-1 SLC, OPERA reference products). No dynamic data rendering to trace. Data flow correctness is verified through unit tests with synthetic arrays.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 36 phase 02 tests pass | `PYTHONPATH=src pytest tests/unit/test_types.py test_metrics.py test_rtc_pipeline.py test_cslc_pipeline.py test_compare_rtc.py test_compare_cslc.py -x` | 36 passed in 0.94s | PASS |
| Types importable | `python -c "from subsideo.products.types import RTCConfig, CSLCConfig, RTCResult, CSLCResult"` | Verified via test_types.py passing | PASS |
| Metrics importable | `python -c "from subsideo.validation.metrics import rmse, spatial_correlation, bias, ssim"` | Verified via test_metrics.py passing | PASS |
| No subprocess usage in pipelines | `grep -r subprocess src/subsideo/products/` | No matches | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PROD-01 | 02-02 | Library can produce RTC-S1 backscatter products from S1 IW SLC over EU AOIs using ISCE3 | SATISFIED | `run_rtc()` orchestrates opera-rtc (wraps isce3) via Python API with runconfig generation, COG conversion, and validation |
| PROD-02 | 02-03 | Library can produce CSLC-S1 coregistered SLC products from S1 IW SLC over EU AOIs using ISCE3 | SATISFIED | `run_cslc()` orchestrates compass (wraps isce3) via Python API with runconfig generation, HDF5 validation |
| OUT-01 | 02-02 | RTC products are written as Cloud-Optimised GeoTIFF with correct metadata | SATISFIED | `ensure_cog()` uses `rio_cogeo.cog_translate` with DEFLATE profile; `validate_rtc_product()` checks COG validity, UTM CRS, 30m posting |
| OUT-02 | 02-03 | CSLC products are written as HDF5 following OPERA product specification hierarchy | SATISFIED | `validate_cslc_product()` checks /data group, datasets, /metadata or /identification groups via h5py |
| VAL-01 | 02-01 | Library computes pixel-level RMSE, spatial correlation, bias, and SSIM between products | SATISFIED | `metrics.py` implements all 4 functions with NaN masking; 11 unit tests verify correctness |
| VAL-02 | 02-04 | Library can compare RTC-S1 output against OPERA N.Am. RTC reference (RMSE < 0.5 dB, r > 0.99) | SATISFIED | `compare_rtc()` with dB-domain comparison, grid alignment, pass_criteria dict with thresholds |
| VAL-03 | 02-04 | Library can compare CSLC-S1 output against OPERA N.Am. CSLC reference (phase RMS < 0.05 rad) | SATISFIED | `compare_cslc()` with interferometric phase via `np.conj`, coherence computation, pass_criteria dict |

No orphaned requirements found -- all 7 requirement IDs mapped to Phase 2 in REQUIREMENTS.md are covered by plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | No anti-patterns detected |

No TODO/FIXME/placeholder comments, no empty implementations, no subprocess usage, no hardcoded empty data in source files.

### Human Verification Required

### 1. End-to-End RTC Pipeline with Real Data

**Test:** Run `run_rtc()` with actual Sentinel-1 SLC data over an EU AOI using real CDSE credentials, then run `compare_rtc()` against a downloaded OPERA N.Am. reference product.
**Expected:** COG GeoTIFF produced with valid UTM CRS, 30m posting, RMSE < 0.5 dB, correlation > 0.99.
**Why human:** Requires live CDSE credentials, conda-forge dependencies (isce3, opera-rtc, rio-cogeo), and OPERA reference data from ASF DAAC. Cannot be tested without a running conda environment with all native dependencies.

### 2. End-to-End CSLC Pipeline with Real Data

**Test:** Run `run_cslc()` with actual Sentinel-1 SLC data, then run `compare_cslc()` against a downloaded OPERA N.Am. CSLC reference.
**Expected:** HDF5 with /data and /metadata groups, phase RMS < 0.05 rad, high coherence.
**Why human:** Requires live CDSE credentials, conda-forge dependencies (isce3, compass), and matching OPERA CSLC reference from ASF DAAC.

### 3. COG Compliance Verification

**Test:** Open the RTC COG output in QGIS or `rio cogeo validate` CLI to confirm overviews, internal tiling, and metadata are correct.
**Expected:** Valid COG structure with DEFLATE compression, overviews at 5 levels, correct band metadata.
**Why human:** rio-cogeo validation is mocked in unit tests; real COG compliance needs actual file inspection.

### Gaps Summary

No gaps found. All 5 success criteria from the ROADMAP are verified at the code level. All 7 requirement IDs are satisfied with substantive implementations. All 36 unit tests pass. All key links are wired correctly (no orphaned modules, no stub implementations).

The only remaining verification is end-to-end testing with real Sentinel-1 data in a full conda environment with native dependencies (isce3, opera-rtc, compass, rio-cogeo) -- this requires human execution with live CDSE credentials.

---

_Verified: 2026-04-05_
_Verifier: Claude (gsd-verifier)_
