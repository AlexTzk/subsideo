---
phase: 06-wire-unused-data-modules-opera-metadata
verified: 2026-04-06T06:30:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 6: Wire Unused Data Modules & OPERA Metadata Verification Report

**Phase Goal:** Every Phase 1 data module has at least one consumer, and all five products carry OPERA-compliant identification metadata
**Verified:** 2026-04-06T06:30:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | CSLC pipeline calls `fetch_ionex()` to obtain TEC maps and passes the result as `tec_file` to the processing step | VERIFIED | `cslc.py` lines 363-375: `fetch_ionex()` called in `run_cslc_from_aoi` with `sensing_time.date()`, username, password. Line 397: `tec_file=tec_file` passed to `run_cslc()`. Wrapped in try/except with warn-and-continue. Unit test `test_ionex_fetched_and_passed_to_run_cslc` confirms. |
| 2 | `subsideo validate` CLI can automatically fetch OPERA reference products from ASF DAAC via `ASFClient` when `--reference` is not provided | VERIFIED | `cli.py` lines 281-358: ASF auto-fetch block guarded by `pt in ("rtc", "cslc") and reference_path is None`. Uses `ASFClient`, `Transformer.from_crs` for WGS84 bbox, correct OPERA short names. Clear error on missing creds (line 352-358). Unit test `test_autofetch_called_when_reference_omitted_and_creds_present` confirms. |
| 3 | `inject_opera_metadata()` is called in RTC, CSLC, DISP, and DIST product pipelines (not just DSWx) | VERIFIED | All five product files contain `inject_opera_metadata` calls: `rtc.py` line 245 (product_type="RTC-S1"), `cslc.py` line 214 (product_type="CSLC-S1"), `disp.py` line 373 (product_type="DISP-S1"), `dist.py` line 209 (product_type="DIST-S1"), `dswx.py` line 423 (product_type="DSWx-S2"). Total 10 occurrences across 5 files (import + call each). |
| 4 | All five product types include provenance, software version, and run parameters in their output metadata | VERIFIED | All five pipelines use `get_software_version()` (10 occurrences across 5 files) which reads from `importlib.metadata` with "dev" fallback. `inject_opera_metadata` writes PRODUCT_TYPE, SOFTWARE_VERSION, SOFTWARE_NAME, PRODUCTION_DATETIME, and RUN_PARAMETERS into both GeoTIFF tags and HDF5 `/identification` group attributes. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/subsideo/_metadata.py` | `get_software_version()` helper | VERIFIED | Lines 15-22: uses `importlib.metadata.version("subsideo")` with `PackageNotFoundError` fallback to `"dev"`. Lines 25-60: `inject_opera_metadata` handles both GeoTIFF and HDF5. |
| `src/subsideo/products/cslc.py` | IONEX fetch + metadata injection | VERIFIED | Lines 363-375: `fetch_ionex` in `run_cslc_from_aoi`. Lines 208-226: `inject_opera_metadata` in `run_cslc`. |
| `src/subsideo/products/rtc.py` | Metadata injection in `run_rtc` | VERIFIED | Lines 239-256: `inject_opera_metadata` with product_type="RTC-S1". |
| `src/subsideo/products/disp.py` | Metadata injection in `run_disp` | VERIFIED | Lines 364-384: `inject_opera_metadata` with product_type="DISP-S1" for all HDF5 outputs. |
| `src/subsideo/products/dist.py` | Metadata injection in `run_dist` | VERIFIED | Lines 203-219: `inject_opera_metadata` with product_type="DIST-S1". |
| `src/subsideo/products/dswx.py` | Updated to use `get_software_version()` | VERIFIED | Lines 421-432: uses `get_software_version()` instead of `cfg.product_version`. |
| `src/subsideo/cli.py` | ASF auto-fetch in `validate_cmd` | VERIFIED | Lines 281-358: ASFClient instantiation, WGS84 bbox reprojection, OPERA short names, credential gating. |
| `tests/unit/test_metadata_wiring.py` | Unit tests for all wiring points | VERIFIED | 8 tests across 5 classes. All pass. |
| `tests/unit/test_cli_asf_autofetch.py` | Unit tests for ASF auto-fetch | VERIFIED | 4 tests in TestASFAutoFetch. All pass. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cslc.py` | `data/ionosphere.py` | `fetch_ionex` call in `run_cslc_from_aoi` | WIRED | Line 367: `from subsideo.data.ionosphere import fetch_ionex` (lazy import inside try block) |
| `rtc.py` | `_metadata.py` | `inject_opera_metadata` call in `run_rtc` | WIRED | Line 240: `from subsideo._metadata import get_software_version, inject_opera_metadata` |
| `cslc.py` | `_metadata.py` | `inject_opera_metadata` call in `run_cslc` | WIRED | Line 209: `from subsideo._metadata import get_software_version, inject_opera_metadata` |
| `disp.py` | `_metadata.py` | `inject_opera_metadata` call in `run_disp` | WIRED | Line 365: `from subsideo._metadata import get_software_version, inject_opera_metadata` |
| `dist.py` | `_metadata.py` | `inject_opera_metadata` call in `run_dist` | WIRED | Line 204: `from subsideo._metadata import get_software_version, inject_opera_metadata` |
| `dswx.py` | `_metadata.py` | `inject_opera_metadata` call in `run_dswx` | WIRED | Line 421: `from subsideo._metadata import get_software_version, inject_opera_metadata` |
| `cli.py` | `data/asf.py` | `ASFClient` in `validate_cmd` | WIRED | Line 295: `from subsideo.data.asf import ASFClient` (lazy import) |
| `cli.py` | `config.py` | `Settings()` for Earthdata credentials | WIRED | Line 283: `from subsideo.config import Settings` |

### Data-Flow Trace (Level 4)

Not applicable -- these artifacts are pipeline orchestration and metadata injection, not data-rendering components.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| get_software_version returns string | `python3 -c "from subsideo._metadata import get_software_version; v=get_software_version(); assert isinstance(v,str) and len(v)>0"` | Returns "dev" (editable install) | PASS |
| All 12 unit tests pass | `python3 -m pytest tests/unit/test_metadata_wiring.py tests/unit/test_cli_asf_autofetch.py --no-cov -v` | 12 passed in 1.49s | PASS |
| inject_opera_metadata present in all 5 product modules | `grep -c inject_opera_metadata src/subsideo/products/{rtc,cslc,disp,dist,dswx}.py` | 2 occurrences in each (10 total) | PASS |
| fetch_ionex present in cslc.py | `grep -c fetch_ionex src/subsideo/products/cslc.py` | 2 occurrences | PASS |
| ASFClient present in cli.py | `grep -c ASFClient src/subsideo/cli.py` | 2 occurrences | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DATA-05 | 06-01-PLAN.md | Library can download IONEX TEC maps for ionospheric correction | SATISFIED | `fetch_ionex` called in `cslc.py:run_cslc_from_aoi` with Earthdata credentials, result passed as `tec_file` to processing step |
| DATA-06 | 06-02-PLAN.md | Library can search and download OPERA reference products from ASF DAAC (for validation) | SATISFIED | `ASFClient` wired into `cli.py:validate_cmd` with auto-fetch for RTC/CSLC when `--reference` omitted |
| OUT-03 | 06-01-PLAN.md | All products include OPERA-compliant identification metadata (provenance, version, params) | SATISFIED | `inject_opera_metadata` called in all 5 product pipelines with correct product_type strings and `get_software_version()` |

No orphaned requirements found for Phase 6.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | - | - | - | - |

No TODO, FIXME, placeholder, or stub patterns found in the modified files.

### Human Verification Required

### 1. IONEX Download Integration

**Test:** Run CSLC pipeline with valid Earthdata credentials against a real Sentinel-1 scene and verify IONEX file is downloaded and used.
**Expected:** IONEX file appears in `output_dir/ionex/` and the compass runconfig references it as `tec_file`.
**Why human:** Requires live CDSE and CDDIS network access with valid credentials.

### 2. ASF DAAC Auto-Fetch End-to-End

**Test:** Run `subsideo validate --product-dir <real_rtc_output> --product-type rtc --out /tmp/val` with Earthdata credentials set but no `--reference`.
**Expected:** OPERA reference product auto-downloaded from ASF DAAC and validation comparison runs.
**Why human:** Requires live ASF DAAC access with valid Earthdata credentials.

### 3. OPERA Metadata in Real Products

**Test:** Produce an RTC COG and inspect its GeoTIFF tags; produce a CSLC HDF5 and inspect its `/identification` group attributes.
**Expected:** Tags/attributes contain PRODUCT_TYPE, SOFTWARE_VERSION, SOFTWARE_NAME, PRODUCTION_DATETIME, RUN_PARAMETERS.
**Why human:** Requires actual processing to verify metadata written correctly by rasterio/h5py.

### Gaps Summary

No gaps found. All four success criteria are verified:
1. CSLC pipeline calls `fetch_ionex()` with graceful degradation on failure.
2. `validate` CLI auto-fetches OPERA references from ASF when credentials are available.
3. `inject_opera_metadata()` is called in all five product pipelines.
4. All products include provenance, software version, and run parameters via `get_software_version()`.

All commits verified: `9b7cc99`, `3cf5605`, `1de3a5f`, `c3c59ba`, `5ec52d9`.

---

_Verified: 2026-04-06T06:30:00Z_
_Verifier: Claude (gsd-verifier)_
