---
phase: 06-dswx-s2-n-am-eu-recalibration
plan: "04"
subsystem: validation
tags: [dswx, compare_dswx, matrix_writer, shoreline-buffer, jrc-retry, scipy, pydantic]

# Dependency graph
requires:
  - phase: 06-dswx-s2-n-am-eu-recalibration/06-02
    provides: "harness.download_reference_with_retry(source='jrc') + RETRY_POLICY['jrc'] + DswxNamCellMetrics + DswxEUCellMetrics schemas"
provides:
  - "_compute_shoreline_buffer_mask helper in compare_dswx.py (D-16 single source of truth)"
  - "JRC retry refactor via harness.download_reference_with_retry(source='jrc') (D-25)"
  - "DSWxValidationDiagnostics dataclass + diagnostics attribute on DSWxValidationResult (B2 fix)"
  - "_is_dswx_nam_shape + _is_dswx_eu_shape discriminators in matrix_writer.py"
  - "_render_dswx_nam_cell + _render_dswx_eu_cell renderers in matrix_writer.py"
  - "Dispatch ordering: disp<dist_eu<dist_nam<dswx_nam<dswx_eu<cslc<rtc (D-27 + W6 strict chain)"
affects:
  - "06-05-PLAN: N.Am. eval calls compare_dswx(..., shoreline_buffer_px=1) + reads result.diagnostics"
  - "06-06-PLAN: EU grid search uses _compute_shoreline_buffer_mask uniformly"
  - "06-07-PLAN: EU re-run uses compare_dswx + diagnostics attribute"

# Tech tracking
tech-stack:
  added:
    - "scipy.ndimage.binary_dilation (lazy-imported in _compute_shoreline_buffer_mask)"
  patterns:
    - "B2 fix pattern: add optional attribute to existing dataclass (default None) rather than changing return type"
    - "Shoreline buffer: compute on JRC reference grid, reproject alongside JRC mosaic (D-16)"
    - "Harness retry refactor: status attribute on ReferenceDownloadError for 404 detection"
    - "matrix_writer discriminator: structurally-disjoint key-set per schema (D-27)"

key-files:
  created:
    - "tests/unit/test_compare_dswx_shoreline.py"
    - "tests/unit/test_matrix_writer_dswx.py"
  modified:
    - "src/subsideo/products/types.py"
    - "src/subsideo/validation/compare_dswx.py"
    - "src/subsideo/validation/matrix_writer.py"

key-decisions:
  - "B2 fix: diagnostics attribute side-channel on DSWxValidationResult (default None) instead of tuple-return change — ZERO breaking change for v1.0 callers; Plans 06-05/06-06/06-07 access via result.diagnostics"
  - "Shoreline buffer applied at UTM-grid level using JRC raw encoding (jrc_crop==2 = water) before _binarize_jrc transform"
  - "download_reference_with_retry uses keyword arg dest= (not dest_path=); source= is keyword-only"
  - "404 detection via getattr(exc, 'status', None) == 404 OR '404' in str(exc) to cover both code paths"
  - "Test fixtures use ProductQualityResultJson/ReferenceAgreementResultJson (not dataclass variants) for Pydantic model construction"

patterns-established:
  - "B2 attribute extension: new optional field with default=None on existing dataclass is the canonical non-breaking extension pattern"
  - "Shoreline mask computed on JRC binary (2=water) grid before binarize_jrc transform"
  - "matrix_writer discriminators: pure JSON key-presence check, no Pydantic parse, structurally disjoint"

requirements-completed: [DSWX-06]

# Metrics
duration: 9min
completed: "2026-04-27"
---

# Phase 06 Plan 04: DSWx Shoreline Buffer + Matrix Writer DSWx Branches Summary

**Shoreline-excluded F1 via scipy.ndimage binary_dilation, JRC retry refactor via harness, DSWxValidationDiagnostics B2 attribute extension, and 4 new matrix_writer DSWx render symbols with W6 strict dispatch ordering**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-27T01:32:00Z
- **Completed:** 2026-04-27T01:41:06Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 5

## Accomplishments

- Added `_compute_shoreline_buffer_mask` to `compare_dswx.py` using lazy-imported `scipy.ndimage.binary_dilation`; XOR-of-dilations approach handles asymmetric JRC commission/omission at shoreline (PITFALLS P5.2 mitigation)
- Refactored `_fetch_jrc_tile` to use `harness.download_reference_with_retry(source='jrc')` (D-25); 404 propagated as None (tile-out-of-coverage semantics preserved)
- Added `DSWxValidationDiagnostics` dataclass and `diagnostics: DSWxValidationDiagnostics | None = None` attribute to existing `DSWxValidationResult` (B2 fix: ZERO breaking change — v1.0 callers unaffected)
- `compare_dswx` now returns shoreline-excluded F1 as gate value (D-16); `result.diagnostics` carries `f1_full_pixels` + `shoreline_buffer_excluded_pixels` for Plans 06-05/06-06/06-07
- Added `_is_dswx_nam_shape`, `_is_dswx_eu_shape`, `_render_dswx_nam_cell`, `_render_dswx_eu_cell` to `matrix_writer.py`; dispatch order locked: `disp < dist_eu < dist_nam < dswx_nam < dswx_eu < cslc_selfconsist < rtc_eu` (W6 strict chain)
- ZERO edits to existing matrix_writer render branches (Phase 1 D-09 + Phase 5 D-25 lock verified via git diff)

## Task Commits

1. **Task 1: Shoreline buffer + JRC retry refactor + DSWxValidationDiagnostics (B2)** - `a3699fc` (feat)
2. **Task 2: DSWx render branches + dispatch ordering** - `2a63075` (feat)

## Files Created/Modified

- `src/subsideo/products/types.py` — Added `DSWxValidationDiagnostics` dataclass; added `diagnostics` field to `DSWxValidationResult`
- `src/subsideo/validation/compare_dswx.py` — Added `_compute_shoreline_buffer_mask`; refactored `_fetch_jrc_tile` via harness; apply shoreline buffer in `compare_dswx` and populate diagnostics
- `src/subsideo/validation/matrix_writer.py` — Added 2 discriminators + 2 renderers + 2 dispatch branches (pure additive)
- `tests/unit/test_compare_dswx_shoreline.py` — 8 tests: mask shape/boundary invariants, B2 backward compat, JRC retry contract, 404 propagation, non-404 re-raise
- `tests/unit/test_matrix_writer_dswx.py` — 11 tests: shape discriminators, render PASS/FAIL/BLOCKER variants, dispatch ordering W6 strict chain, existing branches unchanged

## Decisions Made

- **B2 fix pattern confirmed**: Attribute side-channel (default None) on existing dataclass is the right approach for zero-breaking-change extensibility; tuple-return change would have broken all v1.0 callers
- **Shoreline buffer applied at UTM level**: JRC raw encoding (2=water, 1=not-water) used to build binary for `_compute_shoreline_buffer_mask` before `_binarize_jrc`; ensures the buffer is in the same coordinate space as the comparison
- **`dest=` not `dest_path=`**: `download_reference_with_retry` parameter is `dest`, discovered from reading the actual harness signature (plan showed `dest_path`)
- **Test fixtures use `ProductQualityResultJson`/`ReferenceAgreementResultJson`**: Pydantic models require JSON-schema types, not dataclass types from `validation/results.py`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected `download_reference_with_retry` parameter name**
- **Found during:** Task 1 (JRC retry refactor implementation)
- **Issue:** Plan showed `dest_path=local_path` but actual harness signature uses `dest=local_path`
- **Fix:** Used correct `dest=local_path` keyword argument
- **Files modified:** `src/subsideo/validation/compare_dswx.py`
- **Verification:** Tests pass; harness import and call verified
- **Committed in:** a3699fc

**2. [Rule 1 - Bug] Fixed test fixtures to use Pydantic JSON schema types**
- **Found during:** Task 2 (matrix_writer test implementation)
- **Issue:** Test fixtures passed `ProductQualityResult` (dataclass) to `DswxNamCellMetrics` (Pydantic model expecting `ProductQualityResultJson`); pydantic validation error
- **Fix:** Changed fixtures to use `ProductQualityResultJson` + `ReferenceAgreementResultJson` from `matrix_schema`
- **Files modified:** `tests/unit/test_matrix_writer_dswx.py`
- **Verification:** All 11 tests pass
- **Committed in:** 2a63075

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug)
**Impact on plan:** Both fixes were necessary for correctness. No scope creep; both discovered during implementation of planned work.

## Issues Encountered

- Pre-existing test failures in `test_compare_dswx.py` (`test_url_format`, `test_class_mapping`) confirmed pre-existing via git stash; out-of-scope per deviation rules, not modified
- Pre-existing mypy errors in `_binarize_dswx` / `_binarize_jrc` (missing `ndarray` type args) and `matrix_writer.py` (`yaml` stubs missing) — confirmed pre-existing, not introduced by this plan

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plans 06-05, 06-06, 06-07 can now call `compare_dswx(...)` and access `result.diagnostics.f1_full_pixels` / `.shoreline_buffer_excluded_pixels`
- `_compute_shoreline_buffer_mask` is the single source of truth for shoreline buffer (D-16); grid search and final reporting both use the same function
- matrix_writer dispatch table is complete for all Phase 6 DSWx cell types; metrics.json written by Plans 06-05/06-06/06-07 will route correctly

## Self-Check: PASSED

- FOUND: tests/unit/test_compare_dswx_shoreline.py
- FOUND: tests/unit/test_matrix_writer_dswx.py
- FOUND: src/subsideo/products/types.py (DSWxValidationDiagnostics + diagnostics field)
- FOUND: src/subsideo/validation/compare_dswx.py (_compute_shoreline_buffer_mask + harness retry)
- FOUND: src/subsideo/validation/matrix_writer.py (_is_dswx_nam_shape + _is_dswx_eu_shape + renderers + dispatch)
- FOUND: a3699fc (Task 1 commit)
- FOUND: 2a63075 (Task 2 commit)
- FOUND: db442df (metadata commit)

---
*Phase: 06-dswx-s2-n-am-eu-recalibration*
*Completed: 2026-04-27*
