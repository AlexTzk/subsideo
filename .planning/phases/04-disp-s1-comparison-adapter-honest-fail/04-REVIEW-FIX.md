---
phase: 04-disp-s1-comparison-adapter-honest-fail
iteration: 1
fix_scope: critical_warning
fixed_at: 2026-04-25T16:05:00Z
review_path: .planning/phases/04-disp-s1-comparison-adapter-honest-fail/04-REVIEW.md
findings_in_scope: 5
fixed: 5
skipped: 9
status: all_fixed
---

# Phase 4: Code Review Fix Report

**Fixed at:** 2026-04-25T16:05:00Z
**Source review:** `.planning/phases/04-disp-s1-comparison-adapter-honest-fail/04-REVIEW.md`
**Iteration:** 1
**Fix scope:** critical_warning (HIGH + MEDIUM under this project's nomenclature)

**Summary:**
- Findings in scope (HIGH + MEDIUM): 5
- Fixed: 5
- Skipped (out of scope -- LOW + INFO): 9
- Status: `all_fixed`

## Fixed Issues

### HI-01: `prepare_for_reference` silently fills out-of-extent destination cells with 0.0 instead of NaN

**Files modified:**
- `src/subsideo/validation/compare_disp.py`
- `tests/product_quality/test_prepare_for_reference.py`

**Commit:** `326ce5f`

**Applied fix:**
- Added `dst_nodata=np.nan` to BOTH `reproject()` calls in `_resample_onto_grid` (the gaussian path at lines ~561-570 and the other-three-methods path at lines ~577-586). rasterio/GDAL otherwise fills un-touched destination cells with `0.0`, silently corrupting the output by reporting "zero velocity" where the native footprint did not cover.
- Resized the `ref_path`/`ref_dataarray` test fixtures from 50x50 (1500m extent) to 15x15 (450m extent) so the reference grid lies entirely inside the 500x1000m native footprint. This way the existing `np.isfinite(out).sum() > 0.5 * out.size` invariant correctly verifies post-fix behaviour. Pre-fix the test passed only because the bug filled out-of-extent cells with 0.0 (finite).
- Updated docstrings on `ref_path` and `test_form_a_path_each_method` / `test_form_b_dataarray_each_method` to call out the HI-01 rationale.
- Verified empirically that `dst_nodata=np.nan` correctly preserves NaN on out-of-extent cells (400/400 cells NaN when ref does not overlap src) and that all 17 tests in `test_prepare_for_reference.py` pass.

### ME-01: `bias` and `rmse` imports shadowed by float assignments

**Files modified:**
- `run_eval_disp.py`

**Commit:** `bbb06ac`

**Applied fix:**
- Renamed the canonical Stage 9 outputs from `correlation` / `bias` / `rmse` to `correlation_val` / `bias_mm_yr` / `rmse_mm_yr` so they no longer shadow the imported `bias` and `rmse` callables from `subsideo.validation.metrics`.
- Updated the corresponding Stage 12 references in the `ReferenceAgreementResultJson(...)` dict and the closing summary print at line 1093 (broken across two lines to keep within ruff line-length 100).
- Updated the Phase-4 W3 comment block above the Stage 12 dict to reference the new disambiguated names.
- Verified with `ruff check` and `ast.parse`. Tests not directly applicable (eval-script-only changes), so smoke-checked the AST parse per the verification spec.

### ME-02: `bilinear` and `gaussian` form-c branches do not honor nodata sentinel

**Files modified:**
- `src/subsideo/validation/compare_disp.py`

**Commit:** `4a8aa38`

**Applied fix:**
- In `_point_sample_from_dataset`, added `if nodata is not None: src_data = np.where(src_data == nodata, np.nan, src_data)` at the top of both the `bilinear` branch (lines ~743-762) and the `gaussian` branch (lines ~787-810). This now matches the pre-existing nodata-sanitization in the `nearest` branch (line 730) and `block_mean` branch (line 776).
- `map_coordinates(mode="constant", cval=np.nan)` propagates NaN through bilinear interpolation, so the `bilinear` branch's existing kwargs are already correct -- the fix is just to feed it sanitized data.
- For `gaussian`, NaN is replaced with 0.0 anyway by the existing `src_filled` line; the fix ensures sentinels aren't smeared into the smooth output before that fill-with-zero step.
- Verified with `ruff check` and the full test_prepare_for_reference suite (17/17 pass).

### ME-03: deprecated `datetime.utcnow()` usage

**Files modified:**
- `run_eval_disp.py`
- `run_eval_disp_egms.py`

**Commit:** `8a916ef`

**Applied fix:**
- Updated the imports from `from datetime import datetime` to `from datetime import datetime, timezone` in both eval scripts.
- Replaced `datetime.utcnow().isoformat() + "Z"` with `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")` -- this produces the same ISO-8601 with explicit UTC `Z` suffix output but uses the timezone-aware API that won't emit a `DeprecationWarning` on Python 3.12+.
- Verified with `ruff check`, `ast.parse`, and a smoke check of the strftime format -- emits `2026-04-25T16:03:55Z`-style strings as expected.

### ME-04: form-c `block_mean` and `gaussian` paths leak edge-cell data for points outside raster bounds

**Files modified:**
- `src/subsideo/validation/compare_disp.py`

**Commit:** `377c09c`

**Applied fix:**
- In the `block_mean` branch of `_point_sample_from_dataset`, added an explicit centre-bounds check before the window-overlap check: `if not (0 <= r < height and 0 <= c < width): out[i] = np.nan; continue`. This rejects PS points whose centre lies outside the raster, regardless of how much of the +/-6-px window overlaps with valid pixels.
- In the `gaussian` branch, mirrored the same logic with a vectorized OOB mask after `map_coordinates`: `oob = (r<0)|(r>=H)|(c<0)|(c>=W); sampled_gauss[oob] = np.nan`. `map_coordinates(mode="constant", cval=np.nan)` already handles strictly-OOB coords for bilinear interpolation, but the explicit mask keeps the contract symmetric with `block_mean` and is defensive against future refactors.
- Verified empirically with a smoke test using a 10x10 native raster and three PS points (one inside, one just outside the east edge by 10m, one far outside by ~100km): both `block_mean` and `gaussian` correctly returned NaN for the two outside points and a real value for the inside point.
- All 17 tests in test_prepare_for_reference.py still pass.

## Skipped Issues

The following findings are out of scope for this critical_warning fix pass (severity below HIGH/MEDIUM):

### LO-01: `_load_metrics` catches bare `Exception`, swallows traceback context

**File:** `src/subsideo/validation/matrix_writer.py:60`
**Reason:** out_of_scope (severity below critical_warning -- LOW)
**Original issue:** `except Exception as e: logger.warning(...)` discards the full traceback; pydantic ValidationError detail is lost.

### LO-02: Gaussian path silently biases edge pixels toward zero

**File:** `src/subsideo/validation/compare_disp.py:559, 790`
**Reason:** out_of_scope (severity below critical_warning -- LOW)
**Original issue:** `np.where(np.isfinite(src_data), src_data, 0.0)` introduces edge bias in `gaussian_filter`. Documented design choice; non-blocking for v1.1.

### LO-03: `nodata` capture inside `_point_sample_from_dataset` is unnecessary

**File:** `src/subsideo/validation/compare_disp.py:707-715`
**Reason:** out_of_scope (severity below critical_warning -- LOW)
**Original issue:** Misleading "capture before with-block exit" docstring -- there is no with-block in this function. Code-clarity only, no runtime impact.

### LO-04: Unused parameter `region` in `_render_disp_cell`

**File:** `src/subsideo/validation/matrix_writer.py:374-405`
**Reason:** out_of_scope (severity below critical_warning -- LOW)
**Original issue:** `region` parameter dispatched-API-required but unused in body; risk of future "cleanup" breaking dispatch.

### LO-05: `dst_data` shape mismatch defense-in-depth assertion missing

**File:** `src/subsideo/validation/compare_disp.py:559-569`
**Reason:** out_of_scope (severity below critical_warning -- LOW)
**Original issue:** No `assert src_smoothed.shape == src_data.shape` after `gaussian_filter`. Defense-in-depth nit.

### IN-01: Matrix.md DISP-EU shows `coh=0.00 ([fresh])` -- surface measurement

**File:** `eval-disp-egms/metrics.json:5`
**Reason:** out_of_scope (severity below critical_warning -- INFO)
**Original issue:** `coherence_median_of_persistent: 0.0` for Bologna -- honest measurement, interpretation deferred to CONCLUSIONS.

### IN-02: `compute_ramp_aggregate` may emit RuntimeWarning on constant input

**File:** `src/subsideo/validation/selfconsistency.py:476`
**Reason:** out_of_scope (severity below critical_warning -- INFO)
**Original issue:** `np.corrcoef` returns NaN with a RuntimeWarning on zero-variance input; downstream handles NaN gracefully.

### IN-03: `eval-rtc-eu/*` missing from `.gitignore`

**File:** `.gitignore:209-219`
**Reason:** out_of_scope (severity below critical_warning -- INFO; pre-existing, not Phase 4 introduced)
**Original issue:** `.gitignore` lists `eval-rtc/*` but not `eval-rtc-eu/*`, even though `results/matrix_manifest.yml` references it.

### IN-04: `run_eval_cslc_selfconsist_eu.py` still has inner-scope `_compute_ifg_coherence_stack`

**File:** `run_eval_cslc_selfconsist_eu.py:378, 855`
**Reason:** out_of_scope (Phase 4 only edits the N.Am. eval script per the prompt; flagged for traceability into Phase 5)
**Original issue:** B1 root-cause fix correctly removed the inner-scope helper from N.Am. but EU sibling script still defines its own copy.

---

## Verification Summary

| Finding | Verification Method | Result |
|---------|----------------------|--------|
| HI-01 | full test suite + empirical NaN-preservation smoke check | 17/17 pass; 400/400 cells NaN when ref outside src |
| ME-01 | `ruff check` + `ast.parse` | clean |
| ME-02 | full test suite + `ruff check` | 17/17 pass; clean |
| ME-03 | `ruff check` + `ast.parse` + strftime format smoke check | clean |
| ME-04 | full test suite + per-branch OOB smoke check | 17/17 pass; block_mean + gaussian both reject OOB to NaN |

All five in-scope findings fixed and committed. No fixes required rollback. No source files left in a broken state.

---

_Fixed: 2026-04-25T16:05:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
