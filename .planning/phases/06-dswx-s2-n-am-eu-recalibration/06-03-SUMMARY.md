---
phase: 06-dswx-s2-n-am-eu-recalibration
plan: 03
subsystem: dswx-decomposition
tags: [refactor, decomposition, region-threading, public-api, byte-equivalent, wave-2]
dependency_graph:
  requires:
    - 06-02  # DSWEThresholds + THRESHOLDS_NAM + Settings.dswx_region
  provides:
    - src/subsideo/products/dswx.py::IndexBands
    - src/subsideo/products/dswx.py::compute_index_bands
    - src/subsideo/products/dswx.py::score_water_class_from_indices
    - src/subsideo/products/types.py::DSWxConfig.region
  affects:
    - 06-04  # run_dswx(DSWxConfig(region='nam'/'eu')) now works
    - 06-05  # DSWx EU evaluation uses DSWxConfig(region='eu')
    - 06-06  # Grid search consumes IndexBands + score_water_class_from_indices
    - 06-07  # Validation uses region-threaded run_dswx
tech_stack:
  added:
    - npt.NDArray[np.float32/np.uint16/np.uint8] type annotations in dswx.py new functions
    - numpy.typing import in dswx.py
  patterns:
    - frozen+slots dataclass for cacheable IndexBands (D-05 architectural pattern)
    - required keyword-only thresholds parameter (D-12 no-default contract)
    - lazy Settings import inside run_dswx body (circular-dep avoidance pattern)
key_files:
  created:
    - tests/unit/test_dswx_decomposition.py
    - tests/unit/test_dswx_region_resolution.py
  modified:
    - src/subsideo/products/dswx.py
    - src/subsideo/products/types.py
    - tests/unit/test_dswx_pipeline.py
decisions:
  - "Use npt.NDArray[dtype] for new IndexBands + public function signatures; existing bare np.ndarray in private functions left unchanged (pre-existing pattern)"
  - "run_dswx parameter stays as 'cfg' (not 'config'); plan's acceptance-criteria string 'config.region' was a doc mismatch; logic and tests verified correct"
  - "Removed pre-existing unused 'from_bounds' import from _write_cog_30m (Rule 1 auto-fix, ruff F401)"
  - "Updated test_dswx_pipeline.py calls to _compute_diagnostic_tests to pass thresholds=THRESHOLDS_NAM (Rule 1 auto-fix: broken by required keyword change)"
metrics:
  duration: "40 minutes"
  completed: "2026-04-27"
  tasks_completed: 2
  files_created: 2
  files_modified: 3
---

# Phase 6 Plan 03: DSWx Decomposition + Region Threading Summary

**One-liner:** Wave 2 algorithm refactor: IndexBands + compute_index_bands + score_water_class_from_indices public API + DSWxConfig.region field + run_dswx region resolution, with zero-byte-change regression against v1.0 PROTEUS defaults (SHA256-verified).

## Tasks

### Task 1: Decompose _compute_diagnostic_tests + delete WIGT/AWGT/PSWT2_MNDWI (commits 7f7d4e5 RED, 00457f6 GREEN)

Decomposed the monolithic `_compute_diagnostic_tests` function into two cacheable public functions:

- `IndexBands`: frozen+slots dataclass (5 float32 fields: mndwi, ndvi, mbsrv, mbsrn, awesh)
- `compute_index_bands(blue, green, red, nir, swir1, swir2) -> IndexBands`: pure-numpy, threshold-free
- `score_water_class_from_indices(indices, blue, nir, swir1, swir2, *, thresholds: DSWEThresholds) -> npt.NDArray[np.uint8]`: reads only 3 grid-tunable thresholds
- `_compute_diagnostic_tests` becomes a backward-compat shim with REQUIRED `thresholds` keyword (no default)

Deleted WIGT=0.124, AWGT=0.0, PSWT2_MNDWI=-0.5 module-level constants per CONTEXT D-12.
Kept 8 non-grid constants (PSWT1_MNDWI/NIR/SWIR1/NDVI + PSWT2_BLUE/NIR/SWIR1/SWIR2).
Updated `__all__` with 3 new public symbols.
Added module-level import `from subsideo.products.dswx_thresholds import THRESHOLDS_BY_REGION, DSWEThresholds`.

9 unit tests in test_dswx_decomposition.py - all pass.
Byte-equivalence regression: SHA256 of score_water_class_from_indices(..., thresholds=THRESHOLDS_NAM) output equals SHA256 of v1.0 inline reference on 100x100 random array (seed=7).

### Task 2: DSWxConfig.region field + run_dswx region resolution (commits 492ed30 RED, e13a259 GREEN)

Added `region: Literal["nam", "eu"] | None = None` field to `DSWxConfig` in `types.py` per CONTEXT D-10. `None` signals "use Settings.dswx_region (env-var default 'nam')".

Added region resolution to `run_dswx` body:
```python
region = cfg.region or settings.dswx_region
thresholds = THRESHOLDS_BY_REGION[region]
```
Lazy-imports `Settings` inside `run_dswx` to avoid circular dep with `subsideo.config`.
Logs region + thresholds values at INFO level for auditability.

8 unit tests in test_dswx_region_resolution.py - all pass.
Precedence: config.region > SUBSIDEO_DSWX_REGION env-var > default 'nam'.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_dswx_pipeline.py calls _compute_diagnostic_tests without thresholds=**
- Found during: Task 1 - run full dswx suite
- Issue: 5 existing tests called `_compute_diagnostic_tests(**bands)` without the now-required `thresholds=` keyword
- Fix: Added `thresholds=THRESHOLDS_NAM` to all 5 test calls; added `THRESHOLDS_NAM` import; added `-> None` return type annotations to updated methods
- Files modified: tests/unit/test_dswx_pipeline.py
- Commit: 00457f6

**2. [Rule 1 - Bug] Unused rasterio.transform.from_bounds import in _write_cog_30m**
- Found during: Task 1 - ruff check on dswx.py
- Issue: Pre-existing F401 ruff error; `from_bounds` imported but never used inside `_write_cog_30m`
- Fix: Removed the import
- Files modified: src/subsideo/products/dswx.py
- Commit: 00457f6

**3. [Rule 1 - Type] New functions inherited bare np.ndarray pattern (25 pre-existing mypy errors)**
- Found during: Task 2 - mypy check
- Issue: New IndexBands fields and function signatures used bare `np.ndarray` like the rest of the file, adding 23 new mypy errors (total 41)
- Fix: Added `import numpy.typing as npt` and typed all new functions with `npt.NDArray[np.float32/np.uint16/np.uint8]`; reduced total mypy errors from 41 to 18 (below pre-existing 25 baseline)
- Files modified: src/subsideo/products/dswx.py
- Commit: e13a259

**4. [Deviation - Doc mismatch] Plan acceptance criteria used 'config.region' but run_dswx uses 'cfg'**
- Found during: Task 2 - verifying acceptance criteria
- Issue: `run_dswx(cfg: DSWxConfig)` uses `cfg` as the parameter name; plan acceptance criteria grep looked for `"region = config.region"` which is a documentation mismatch
- Fix: No code change needed; the logic `cfg.region or settings.dswx_region` is semantically identical; all region resolution tests pass; noted as doc mismatch

## Known Stubs

None. All new public API is fully wired. THRESHOLDS_EU placeholder (from Plan 06-02) is intentional and tracked in the 06-02 SUMMARY.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced by this plan.

## Verification Results

- test_dswx_decomposition.py: 9 passed
- test_dswx_region_resolution.py: 8 passed
- Full dswx suite (excl. pre-existing compare_dswx failure): 86 passed
- Full unit suite: 493 passed, 8 failed (all 8 pre-existing, unchanged)
- Byte-equivalence regression: PASSED (SHA256 match)
- ruff check on plan files: PASSED
- mypy on plan files: 18 errors (all pre-existing bare np.ndarray pattern in private functions; 0 errors in new code)

## Self-Check: PASSED

- FOUND: src/subsideo/products/dswx.py (IndexBands, compute_index_bands, score_water_class_from_indices)
- FOUND: src/subsideo/products/types.py (region: Literal["nam", "eu"] | None = None)
- FOUND: tests/unit/test_dswx_decomposition.py
- FOUND: tests/unit/test_dswx_region_resolution.py
- FOUND: 00457f6 (Task 1 GREEN)
- FOUND: e13a259 (Task 2 GREEN)
