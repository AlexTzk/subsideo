---
phase: 04-disp-s1-comparison-adapter-honest-fail
reviewed: 2026-04-25T08:35:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - src/subsideo/validation/matrix_schema.py
  - src/subsideo/validation/selfconsistency.py
  - src/subsideo/validation/compare_disp.py
  - src/subsideo/validation/matrix_writer.py
  - run_eval_cslc_selfconsist_nam.py
  - run_eval_disp.py
  - run_eval_disp_egms.py
  - tests/product_quality/test_matrix_schema_disp.py
  - tests/product_quality/test_selfconsistency_ramp.py
  - tests/product_quality/test_selfconsistency_coherence_stack.py
  - tests/product_quality/test_prepare_for_reference.py
  - tests/reference_agreement/test_matrix_writer_disp.py
findings:
  blocking: 0
  high: 1
  medium: 4
  low: 5
  info: 4
  total: 14
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-04-25T08:35:00Z
**Depth:** standard (per-file analysis)
**Files Reviewed:** 11 source/test files (light review on .gitignore, matrix_manifest.yml, matrix.md, validation_methodology.md, CONCLUSIONS files)
**Status:** issues_found

## Summary

Phase 4 successfully delivers the four claimed artifacts: (1) Pydantic v2 schemas for DISP cell metrics with proper `extra="forbid"` discipline; (2) ramp-attribution helpers with deterministic auto-attribute rule; (3) `prepare_for_reference` adapter with three reference-grid forms × four multilook methods; (4) matrix-writer DISP dispatch branch with structurally-disjoint key check. The B1 root-cause fix (lifting `compute_ifg_coherence_stack` to public API) is correctly executed in `run_eval_cslc_selfconsist_nam.py` — the inner-scope helper is gone and only the public symbol remains.

However, the review surfaces **one HIGH-severity correctness bug** in the new `prepare_for_reference` adapter: rasterio's `reproject` silently fills out-of-source-extent destination cells with `0.0` instead of preserving the pre-allocated NaN. The unit tests mask this bug rather than catching it (see HIGH-01 below). This affects all four method branches in the form (a)/(b) raster-to-raster path. Mitigation in run_eval_disp.py (`our_on_opera != 0` filter) is fragile and incomplete; run_eval_disp_egms.py form (c) point-sampling has a related-but-distinct edge-leakage issue.

Four MEDIUM findings cover: silent function shadowing of imported metrics functions (run_eval_disp.py:747-748), `bilinear`/`gaussian` form (c) paths not honoring nodata sentinel, deprecated `datetime.utcnow()` usage, and form (c) `block_mean` edge-leakage when PS points fall outside the raster.

The remaining LOW/INFO items are stylistic or potential-future-bug categories. No security vulnerabilities (no injection, no path traversal beyond the existing `_validate_metrics_path` allow-list, no eval/exec). The honest-FAIL r=0.049 / r=0.336 measurements and the `method=None`-rejecting policy are explicitly out of review scope per phase context.

## High Issues

### HI-01: `prepare_for_reference` silently fills out-of-extent destination cells with 0.0 instead of NaN

**File:** `src/subsideo/validation/compare_disp.py:543-586` (`_resample_onto_grid`)

**Issue:** All four method branches pre-allocate `dst_data = np.full(dst_shape, np.nan, dtype=np.float64)` (line 543) but call `reproject()` without specifying `dst_nodata=np.nan`. rasterio/GDAL's default behavior on un-touched destination cells (those entirely outside the source extent) is to write `0.0`, **not** to preserve the pre-allocated NaN. Empirical verification on the actual test fixture (100×100 native at 5×10 m vs 50×50 ref at 30 m): 100% of destination cells finite, with `out[49,49] == 0.0` despite that pixel being far outside the source footprint. With `dst_nodata=np.nan` explicitly passed, only 23.1% are finite (the correct subset that overlaps source).

This means `prepare_for_reference` returns silently-corrupt data: cells outside the native extent are reported as zero-velocity rather than no-data. Downstream consequences:

- **Correlation/bias/RMSE inflation or deflation** depending on the reference grid's true value at those out-of-extent pixels — both directions of bias are possible.
- The unit test `test_form_a_path_each_method` line 136 (`np.isfinite(out).sum() > 0.5 * out.size`) **passes only because** the bug fills out-of-extent cells with 0.0 (which is finite). With the correct NaN behavior, the assertion would fail at ~23.1%. So the test masks the bug.
- The eval script `run_eval_disp.py` line 695 has a defensive filter `& (our_on_opera != 0)` that catches this incidentally — but excludes legitimately-zero velocity pixels and is a bandaid, not a root-cause fix. `run_eval_disp_egms.py` Stage 9 uses form (c) point-sampling (different code path, distinct issue — see ME-04), so the run_eval_disp.py mitigation does not transfer.

**Fix:**

```python
# In _resample_onto_grid (compare_disp.py:524-586), add dst_nodata=np.nan to BOTH reproject() calls:

# Gaussian path (line 561-569):
reproject(
    source=src_smoothed,
    destination=dst_data,
    src_transform=src_transform,
    src_crs=src_crs,
    dst_transform=dst_transform,
    dst_crs=dst_crs,
    resampling=Resampling.nearest,
    dst_nodata=np.nan,  # Phase 4 HI-01: preserve init NaN on un-touched cells
)

# Other-three-methods path (line 577-585):
reproject(
    source=src_data,
    destination=dst_data,
    src_transform=src_transform,
    src_crs=src_crs,
    dst_transform=dst_transform,
    dst_crs=dst_crs,
    resampling=rmap[method],
    dst_nodata=np.nan,  # Phase 4 HI-01
)
```

Then update `test_form_a_path_each_method` and `test_form_b_dataarray_each_method` to use the correct expected ratio. Either:
- Build fixtures where native fully covers ref so >50% finite is the right invariant, or
- Lower the threshold to `> 0.2 * out.size` and add an explicit assertion that out-of-extent cells are NaN.

The fixture comments (test_prepare_for_reference.py:52, 92-93) already note that native covers only ~22% of ref, so the threshold was a bug from the start. Changing the fixture is the cleaner option.

## Medium Issues

### ME-01: `bias` and `rmse` imports from `subsideo.validation.metrics` are shadowed by float assignments

**File:** `run_eval_disp.py:700, 747-748`

**Issue:** Line 700 imports `from subsideo.validation.metrics import bias, rmse, spatial_correlation`. The names `bias` and `rmse` are then used as functions on lines 709-710. Lines 747-748 immediately rebind these same names to floats (`bias = float(b_mm)`, `rmse = float(e_mm)`). Functionally safe in this script today (no further `bias(...)` calls below), but:

1. A future maintainer adding code below line 748 that calls `bias(x, y)` would crash with `TypeError: 'float' object is not callable`.
2. Linters (ruff `F811` redefinition or `B005`) would flag this if their respective rules were enabled.
3. The pattern is confusing: the same identifier is used as both a function and a value within ~50 lines.

The Bologna script (`run_eval_disp_egms.py:641, 647`) avoids this issue by using inline numpy expressions instead of importing `bias`/`rmse`.

**Fix:** Rename the local floats to disambiguate:
```python
correlation_val = float(r_val)
bias_mm_yr = float(b_mm)
rmse_mm_yr = float(e_mm)
sample_count = int(n_valid)
```
Then update Stage 12 (line 1024-1027) to use the new names.

### ME-02: `_point_sample_from_dataset` `bilinear` and `gaussian` branches do not honor nodata sentinel

**File:** `src/subsideo/validation/compare_disp.py:743-759, 784-804`

**Issue:** The `nearest` (line 726-732) and `block_mean` (line 761-782) branches honor the raster's `nodata` sentinel (replacing matches with NaN before averaging). The `bilinear` branch (line 743-759) and `gaussian` branch (line 784-804) feed the raw `src_data` (or `src_filled` after NaN→0 replacement) directly into `scipy.ndimage.map_coordinates` without checking `nodata`. If the raster has a sentinel value (e.g., -9999 for invalid pixels), bilinear interpolation will mix the sentinel into valid neighbours, silently producing nonsense.

Mitigating factor: dolphin's `velocity.tif` typically does not set a nodata sentinel (NaN is used directly) — but this is implementation-specific and brittle. The contract `prepare_for_reference` advertises (`Path | str | xr.DataArray`) makes no nodata-handling guarantee.

**Fix:** Before invoking `map_coordinates` in both branches, sanitize:
```python
if nodata is not None:
    src_data = np.where(src_data == nodata, np.nan, src_data)
```
Note `map_coordinates` will then propagate NaN with `mode="constant"` + `cval=np.nan`, which is the intended behavior.

### ME-03: `datetime.utcnow()` is deprecated in Python 3.12+

**File:** `run_eval_disp.py:96`, `run_eval_disp_egms.py:113`

**Issue:** Both eval scripts use `datetime.utcnow().isoformat() + "Z"`. `datetime.utcnow()` is deprecated in Python 3.12 and emits a `DeprecationWarning`. The recommended replacement is `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")`. The project targets Python 3.10–3.11 today, but conda-env.yml will pin to 3.11/3.12 going forward.

**Fix:**
```python
from datetime import datetime, timezone
run_start_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
```

### ME-04: Form (c) `block_mean` and `gaussian` paths leak edge-cell data for points outside raster bounds

**File:** `src/subsideo/validation/compare_disp.py:761-782` (block_mean form c), `784-804` (gaussian form c)

**Issue:** When a PS point's projected (row, col) falls outside the raster bounds, the boundary check `if r1 <= r0 or c1 <= c0` (line 771) only triggers when the point is far enough outside that there is **zero** overlap between the ±radius window and the raster. For a point that is 5 m outside a raster with a 30-m (6-pixel-radius) window, the clipped window will still include 1-3 in-bound rows/cols representing the raster edge — and `out[i] = float(win[valid].mean())` returns the edge mean, not NaN.

Practically, this means EGMS L2a PS points that fall just outside the burst footprint will return spurious "edge" velocity values rather than NaN. For Bologna, which has dense PS coverage, this affects only border PS — but their values flow into correlation/bias/RMSE without filtering.

The `gaussian` form-c branch (line 784-804) has the same issue plus: `gaussian_filter` is applied to the entire `src_data` first, which smears edge-zeros into the interior.

**Fix:** After clipping the window, also assert that the point's center is inside the raster bounds:
```python
if not (0 <= r < height and 0 <= c < width):
    out[i] = np.nan
    continue
```
This rejects PS points whose centre falls outside the raster, regardless of window overlap.

## Low Issues

### LO-01: `_load_metrics` catches bare `Exception`, swallows traceback context

**File:** `src/subsideo/validation/matrix_writer.py:60`

**Issue:** `except Exception as e:` followed by `logger.warning("Failed to parse {}: {}", metrics_path, e)` discards the full traceback. For pydantic ValidationError (which carries detailed per-field errors), only `repr(e)` is logged — not the full validation report. Debugging a malformed metrics.json from log output is harder than necessary.

**Fix:** Use `logger.exception(...)` or pass the full traceback:
```python
except Exception as e:
    logger.warning("Failed to parse {}: {}", metrics_path, e)
    logger.debug("Full traceback:\n{}", traceback.format_exc())
    return None, f"{metrics_path.name} invalid"
```

### LO-02: Gaussian path silently biases edge pixels toward zero

**File:** `src/subsideo/validation/compare_disp.py:559, 790`

**Issue:** Both Gaussian sites use `src_filled = np.where(np.isfinite(src_data), src_data, 0.0)` to fill NaN with 0.0 before applying `gaussian_filter`. This is a documented design choice (RESEARCH lines 738-746) but introduces a measurable bias at edges between valid and NaN regions: pixels near the boundary get pulled toward 0 by the Gaussian smooth, since 0.0 is a meaningful velocity value (not a sentinel). The NaN-aware Gaussian pattern (`gaussian_filter` on data with NaN replaced by 0, divided by `gaussian_filter` on the NaN-mask) would avoid this — at the cost of one extra filter call.

For Phase 4's measurement-conservative discipline (block_mean is the chosen kernel), this is a non-issue. The Gaussian path is only used for kernel-comparison studies in the follow-up Unwrapper Selection milestone.

**Fix:** Either (a) document the bias inline with a `# WARNING` comment for future maintainers, or (b) implement the NaN-aware Gaussian:
```python
# NaN-aware Gaussian (alternative to fill-with-zero):
mask = np.isfinite(src_data).astype(np.float64)
data_filled = np.where(mask > 0, src_data, 0.0)
weighted_data = gaussian_filter(data_filled, sigma=...)
weighted_mask = gaussian_filter(mask, sigma=...)
with np.errstate(divide="ignore", invalid="ignore"):
    src_smoothed = np.where(weighted_mask > 0, weighted_data / weighted_mask, np.nan)
```

### LO-03: `nodata` capture inside `_point_sample_from_dataset` is unnecessary

**File:** `src/subsideo/validation/compare_disp.py:707-715`

**Issue:** The docstring says "Captures nodata/transform BEFORE the with-block exits". But this function takes an already-open `src: rasterio.DatasetReader` parameter — there is no `with` block inside this function for the dataset to exit. The dataset stays open for the function's lifetime (the caller `_point_sample` wraps the call in its own `with rasterio.open(...) as src:` block). The CR-01-mirror comment is misleading defensive code.

This is a code-clarity issue only; no runtime impact.

**Fix:** Remove the comment "capture before with-block exit" since there is no with-block in this function. Or restructure so this function opens its own dataset.

### LO-04: Unused parameter `region` in `_render_disp_cell` could mislead future maintainers

**File:** `src/subsideo/validation/matrix_writer.py:374-405`

**Issue:** `_render_disp_cell(metrics_path, *, region: str)` accepts `region` but never uses it inside the function body. The intent (per docstring) is to keep the dispatch signature symmetric with `_render_cslc_selfconsist_cell` (which does use `region`), and tests confirm the value doesn't affect output. But a future maintainer might "clean up" by removing the unused parameter, breaking the dispatch in `write_matrix` (lines 481, 495).

**Fix:** Either (a) document with a noqa-style comment that the parameter is dispatched-API-required:
```python
def _render_disp_cell(
    metrics_path: Path,
    *,
    region: str,  # required for dispatch symmetry; not used in body
) -> tuple[str, str] | None:
```
Or (b) prefix the parameter with `_` to signal "intentionally unused" while still accepting the kwarg:
```python
def _render_disp_cell(
    metrics_path: Path,
    *,
    _region: str = "",  # not used; kept for dispatch symmetry
) -> tuple[str, str] | None:
```
But that breaks callers passing `region=...`. Option (a) is preferred.

### LO-05: `dst_data` shape mismatch when `src_filled` is fed into `reproject` after gaussian smooth

**File:** `src/subsideo/validation/compare_disp.py:559-569`

**Issue:** The Gaussian path computes `src_smoothed = gaussian_filter(src_filled, sigma=(sigma_pix_y, sigma_pix_x))` and then passes `src_smoothed` (same shape as `src_data`) into `reproject` with `src_transform=src_transform`. This is correct only if `src_filled.shape == src_data.shape`. Confirmed: `np.where(condition, x, 0.0)` returns the broadcast shape of `condition` and `x`, both equal to `src_data.shape`. So fine — but a refactor that adds dimension reduction (e.g. averaging multiple bands) would silently break the transform alignment. Worth a sanity assertion:

```python
assert src_smoothed.shape == src_data.shape, "gaussian_filter changed shape"
```

This is a defense-in-depth nit; not a current bug.

## Info Items

### IN-01: Matrix.md DISP-EU shows `coh=0.00 ([fresh])` — surface measurement, not bug

**File:** `eval-disp-egms/metrics.json:5` (rendered to `results/matrix.md:14`)

`product_quality.coherence_median_of_persistent: 0.0` for Bologna's fresh-computed coherence. Looking at the per-pixel coherence stats (line 7-11 of metrics.json), `coherence_p25: 0.0` and `persistently_coherent_fraction: 0.0`. This means no pixels in the stable mask are persistently coherent across all IFGs at threshold 0.6. Whether this is a true measurement (Bologna 19-epoch stack has at least one bad pair dragging persistence to zero) or a methodology issue (threshold too aggressive for cross-constellation S1A+S1B 6-day cadence) is for CONCLUSIONS to interpret. The code path is correct; the number is honestly reported. Out of code-review scope.

### IN-02: `compute_ramp_aggregate` may emit RuntimeWarning on constant coherence input

**File:** `src/subsideo/validation/selfconsistency.py:476`

`pearson_r = float(np.corrcoef(mag_f, coh_f)[0, 1])` — when either `mag_f` or `coh_f` has zero variance (all-equal values), `np.corrcoef` returns NaN with a `RuntimeWarning: invalid value encountered in divide`. The function returns NaN gracefully (downstream `auto_attribute_ramp` treats `nan > 0.5 == False`). Tests don't currently cover this edge case. Not a bug; consider suppressing the warning with `np.errstate` or adding a test for "all-equal coherence" input.

### IN-03: `eval-rtc-eu/*` is missing from .gitignore but referenced in matrix_manifest.yml

**File:** `.gitignore:209-219` (eval folders block)

`.gitignore` lists `eval-rtc/*` (line 219) but not `eval-rtc-eu/*`, even though `results/matrix_manifest.yml:31` references `cache_dir: eval-rtc-eu`. Phase 4 added `eval-cslc-selfconsist-{nam,eu}/*` (lines 211-212) per the prompt. This pre-existing inconsistency (not introduced by Phase 4) means a future RTC-EU eval run will create untracked files outside `.gitignore`'s coverage. Not in Phase 4 scope but flagged for hygiene.

### IN-04: `run_eval_cslc_selfconsist_eu.py` still has inner-scope `_compute_ifg_coherence_stack`

**File:** `run_eval_cslc_selfconsist_eu.py:378, 855` (out of Phase 4 scope; flagged for traceability)

The B1 root-cause fix correctly removed the inner-scope helper from `run_eval_cslc_selfconsist_nam.py`, but the EU sibling script still defines its own inner-scope copy at line 378. This is **not in Phase 4 scope** (Phase 4 only edits the N.Am. eval script per the prompt) but worth tracking: a future Phase 5 should either (a) lift the EU script to import from `selfconsistency.compute_ifg_coherence_stack` like its N.Am. sibling, or (b) consciously decide the EU duplicate stays.

---

## Notes on Out-of-Scope Items

Per the phase prompt, the following observations are NOT findings:

- **r=0.049 (SoCal) and r=0.336 (Bologna) reference-agreement FAILs** — these are intentional measurements; the phase's goal is to report them honestly with diagnostic attribution.
- **Missing default for `method=` in `prepare_for_reference`** — DISP-01 explicit-no-default policy; deliberate API contract.
- **No test for "method=block_mean produces matching numbers"** — deferred to Plan 04-05 §3 ADR; out of v1.1 scope.

## Notes on Project-Specific Conventions Verified

- **DISP-01 explicit-no-default policy:** `prepare_for_reference(method=None)` raises ValueError with "method= is required (DISP-01 explicit-no-default policy)" — verified in source (line 476-480) and test (test_method_none_raises).
- **DISP-05 no-write-back:** SHA256 byte-equal pre/post test (test_no_write_back_to_native) covers form (a). Forms (b) and (c) accept ndarray/spec inputs and don't have a file to corrupt; the contract is satisfied trivially.
- **B1 root-cause fix in run_eval_cslc_selfconsist_nam.py:** Verified via grep — only the public symbol `compute_ifg_coherence_stack` is imported (line 87); the inner-scope `_compute_ifg_coherence_stack` is gone (no match in run_eval_cslc_selfconsist_nam.py).
- **Pydantic v2 schemas:** All new Phase 4 schemas (`PerIFGRamp`, `RampAggregate`, `RampAttribution`, `DISPProductQualityResultJson`, `DISPCellMetrics`) use `model_config = ConfigDict(extra="forbid")` and Literal type aliases for enum-like fields. Tests verify both extra=forbid rejection and Literal validation.
- **micromamba env subsideo:** No `pip install isce3` / `pip install dolphin` / `pip install gdal` in any Phase 4 file — verified via Grep.
- **Phase 1 D-09 lock-in (matrix_schema.py existing types never edited):** Phase 4 additions are appended below the existing types (line 452+). No edits to the Phase 1/2/3 type definitions.

---

_Reviewed: 2026-04-25T08:35:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
