---
phase: 08-cslc-gate-promotion-and-aoi-hardening
plan: 03
subsystem: validation
tags: [safe-cache, shared-infra, regression-tests]
requires:
  - phase: 08-01
    provides: stable mask hardening
  - phase: 08-02
    provides: canonical CSLC AOI artifact
provides:
  - Shared SAFE cache integrity validation
  - Eval setup rejection of invalid SAFE inputs
  - Regression coverage for CR-01, CR-02, and HI-01
affects: [RTCSUP-01, RTCSUP-03, Phase 9 reruns]
tech-stack:
  added: []
  patterns: [validation-in-harness, setup-layer SAFE healing, shared-infra regression tests]
key-files:
  created:
    - tests/unit/test_compare_disp.py
  modified:
    - src/subsideo/validation/harness.py
    - src/subsideo/validation/__init__.py
    - src/subsideo/data/cdse.py
    - run_eval_cslc_selfconsist_nam.py
    - run_eval_cslc_selfconsist_eu.py
    - run_eval_rtc_eu.py
    - run_eval_disp.py
    - run_eval_disp_egms.py
    - tests/unit/test_harness.py
key-decisions:
  - "SAFE integrity validation lives in validation harness infrastructure, not product APIs."
  - "find_cached_safe validates cache hits by default and skips invalid hits before returning."
  - "Eval/setup paths remove invalid cached SAFE inputs before redownload or skip handling."
requirements-completed:
  - RTCSUP-01
  - RTCSUP-03
duration: 45 min
completed: 2026-04-30
---

# Phase 8 Plan 03: SAFE Cache and Shared Infrastructure Summary

**Two-layer SAFE integrity validation and regression coverage for shared validation defects**

## Performance

- **Duration:** 45 min
- **Completed:** 2026-04-30
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments

- Added `validate_safe_path()` for ZIP and `.SAFE` directory integrity checks.
- Updated `find_cached_safe()` so invalid cached hits are skipped by default.
- Exported SAFE validation through `subsideo.validation`.
- Wired SAFE validation into CDSE download completion and CSLC/DISP/RTC eval setup paths before readers consume inputs.
- Added regression tests for nodata capture in `compare_disp_egms_l2a()`, `dst_nodata=np.nan` preservation in `_resample_onto_grid()`, and immediate `ReferenceDownloadError` on unclassified HTTP 500 statuses.

## Task Commits

1. **Task 1: Add shared SAFE integrity helper and export it** - `bef731a` (feat)
2. **Task 2: Wire SAFE validation into downloader and eval setup paths** - `b5adaf7` (fix)
3. **Task 3: Add CR-01, CR-02, and HI-01 regression tests** - `c2c3c28` (test)

**Plan metadata:** pending orchestrator metadata commit

## Files Created/Modified

- `src/subsideo/validation/harness.py` - SAFE validation helper, valid-cache scanning, and HTTP status fail-fast behavior.
- `src/subsideo/validation/__init__.py` - Package export for `validate_safe_path`.
- `src/subsideo/data/cdse.py` - Validates completed CDSE SAFE tree downloads.
- `run_eval_cslc_selfconsist_nam.py` - Rejects invalid SAFE cache/download inputs before CSLC.
- `run_eval_cslc_selfconsist_eu.py` - Rejects invalid SAFE cache/download inputs before CSLC.
- `run_eval_rtc_eu.py` - Rejects invalid SAFE cache/download inputs before RTC.
- `run_eval_disp.py` - Rejects invalid SAFE inputs before CSLC/DISP setup.
- `run_eval_disp_egms.py` - Rejects invalid CDSE SAFE directories before CSLC/DISP setup.
- `tests/unit/test_harness.py` - SAFE integrity and HTTP 500 fail-fast tests.
- `tests/unit/test_compare_disp.py` - CR-01 and HI-01 regression tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] local Python environment lacks `rioxarray`**
- **Found during:** Task 3 verification
- **Issue:** The bare `python3` environment cannot import `compare_disp.py` because `rioxarray` is absent.
- **Fix:** Ran compare/harness regression tests through the project `subsideo` micromamba environment.
- **Files modified:** None
- **Verification:** `micromamba run -n subsideo env PYTHONPATH=src:. pytest tests/unit/test_compare_disp.py tests/unit/test_harness.py -q --no-cov` passed.
- **Committed in:** N/A

---

**Total deviations:** 1 auto-fixed (Rule 3)
**Impact on plan:** No behavioral change; verification used the project geospatial environment required by the module.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

Ready for Plan 08-04. Phase 9 reruns now have cache integrity checks before CSLC/DISP/RTC readers consume SAFE inputs.

## Self-Check: PASSED

- `env PYTHONPATH=src:. pytest tests/unit/test_harness.py -q --no-cov` passed for the SAFE helper slice with one expected local burst-DB skip.
- `env PYTHONPATH=src:. python3 -m py_compile src/subsideo/data/cdse.py run_eval_cslc_selfconsist_nam.py run_eval_cslc_selfconsist_eu.py run_eval_rtc_eu.py run_eval_disp.py run_eval_disp_egms.py` passed.
- `micromamba run -n subsideo env PYTHONPATH=src:. pytest tests/unit/test_compare_disp.py tests/unit/test_harness.py -q --no-cov` passed.
- `grep -c "dst_nodata=np.nan" src/subsideo/validation/compare_disp.py` returned `2`.
- `grep -c "status >= 400" src/subsideo/validation/harness.py` returned `1`.
- `grep -c "500" tests/unit/test_harness.py` returned `3`.

---
*Phase: 08-cslc-gate-promotion-and-aoi-hardening*
*Completed: 2026-04-30*
