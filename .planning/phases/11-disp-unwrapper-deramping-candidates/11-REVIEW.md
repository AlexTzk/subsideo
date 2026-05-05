---
phase: 11-disp-unwrapper-deramping-candidates
reviewed: 2026-05-05T01:30:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - conftest.py
  - run_eval_disp.py
  - run_eval_disp_egms.py
  - results/matrix.md
  - CONCLUSIONS_DISP_EU.md
  - CONCLUSIONS_DISP_N_AM.md
  - src/subsideo/products/disp.py
  - src/subsideo/validation/disp_candidates.py
  - src/subsideo/validation/matrix_schema.py
  - src/subsideo/validation/matrix_writer.py
  - src/subsideo/validation/selfconsistency.py
  - tests/product_quality/test_selfconsistency_ramp.py
  - tests/reference_agreement/test_matrix_writer_disp.py
  - tests/validation/__init__.py
  - tests/validation/test_disp_candidates.py
findings:
  critical: 7
  warning: 5
  info: 0
  total: 12
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-05-05T01:30:00Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

This phase adds SPURT native and PHASS post-deramping as evaluated DISP candidates via `run_eval_disp.py` and `run_eval_disp_egms.py`, with supporting schema additions in `matrix_schema.py` and `disp_candidates.py`, and matrix rendering in `matrix_writer.py`. The schema layer, matrix writer, and `selfconsistency.py` are correct. Both eval scripts contain a cluster of cascading API misuse bugs in the SPURT ramp attribution block that silently fail at runtime. All four bugs in that block are caught by a blanket `except Exception`, producing no ramp data for either candidate without any loud failure signal. The `run_disp_from_aoi` public function is also broken independently of this phase.

---

## Critical Issues (BLOCKER)

### CR-01: `fit_planar_ramp` called with 2-D array — raises `ValueError` unconditionally

**File:** `run_eval_disp.py:1229` and `run_eval_disp_egms.py:1119`

**Issue:** The SPURT ramp attribution loop reads each IFG as a 2-D array via `_ds.read(1).astype(float)` (shape `(H, W)`) and passes it directly to `fit_planar_ramp(_phase)`. The function's first line raises `ValueError: ifgrams_stack must be 3-D (N, H, W); got shape (H, W)`. This fires for every file in the loop. The baseline ramp path correctly builds a 3-D stack first via `np.stack(...)`. The SPURT path never performs that stacking.

**Fix:** Stack all IFGs into a 3-D array first (matching the baseline pattern), or expand dims at the call site:

```python
# Option A: stack all files first (matches baseline pattern)
spurt_phase_list = []
for _unw_f in spurt_unw_files[:14]:
    with _rio_spurt2.open(_unw_f) as _ds:
        spurt_phase_list.append(_ds.read(1).astype(np.float32))
spurt_stack = np.stack(spurt_phase_list, axis=0)  # (N, H, W)
ramp_data = fit_planar_ramp(spurt_stack, mask=None)

# Option B (single-IFG): expand dims at call site
_fit_dict = fit_planar_ramp(_phase[np.newaxis, :, :])  # (1, H, W)
```

---

### CR-02: Return value of `fit_planar_ramp` accessed as object attributes — `AttributeError`

**File:** `run_eval_disp.py:1230-1232` and `run_eval_disp_egms.py:1120-1122`

**Issue:** After calling `_fit = fit_planar_ramp(_phase)`, the code accesses `_fit.ramp_magnitude_rad` and `_fit.ramp_direction_deg` as object attributes. `fit_planar_ramp` returns `dict[str, np.ndarray]`. This raises `AttributeError: 'dict' object has no attribute 'ramp_magnitude_rad'` — though CR-01's `ValueError` fires first, masking this bug.

**Fix:** Access via dict keys, consistent with baseline usage:

```python
# Wrong:
if _np_spurt.isfinite(_fit.ramp_magnitude_rad):

# Correct:
if _np_spurt.isfinite(_fit_dict["ramp_magnitude_rad"][0]):
    spurt_ramps.append(float(_fit_dict["ramp_magnitude_rad"][0]))
    spurt_dirs.append(float(_fit_dict["ramp_direction_deg"][0]))
```

---

### CR-03: `compute_ramp_aggregate` called with two Python lists instead of `(dict, np.ndarray)`

**File:** `run_eval_disp.py:1234` and `run_eval_disp_egms.py:1124`

**Issue:** The SPURT ramp block calls `compute_ramp_aggregate(spurt_ramps, spurt_dirs)` where both arguments are `list[float]`. The function signature is `compute_ramp_aggregate(ramp_data: dict[str, np.ndarray], ifg_coherence_per_ifg: np.ndarray)`. Passing scalar lists is entirely wrong and would raise `TypeError` or produce silently incorrect results.

**Fix:** Pass the `fit_planar_ramp` dict and a per-IFG coherence array:

```python
ramp_data = fit_planar_ramp(spurt_stack, mask=None)
spurt_coh_arr = np.array(spurt_coh_means, dtype=np.float64)
_spurt_ramp_agg = compute_ramp_aggregate(ramp_data, spurt_coh_arr)
```

---

### CR-04: `auto_attribute_ramp` called with a dict positional argument instead of two floats

**File:** `run_eval_disp.py:1237` and `run_eval_disp_egms.py:1127`

**Issue:** `auto_attribute_ramp(_spurt_ramp_agg)` is called with a single positional dict argument. The actual function signature is `auto_attribute_ramp(direction_stability_sigma_deg: float, magnitude_vs_coherence_pearson_r: float)`. This raises `TypeError`. The baseline path correctly calls it via keyword arguments.

**Fix:**

```python
# Wrong:
_spurt_attr = auto_attribute_ramp(_spurt_ramp_agg)

# Correct (matches baseline):
_spurt_attr = auto_attribute_ramp(
    direction_stability_sigma_deg=_spurt_ramp_agg["direction_stability_sigma_deg"],
    magnitude_vs_coherence_pearson_r=_spurt_ramp_agg["magnitude_vs_coherence_pearson_r"],
)
```

---

### CR-05: Unit mismatch in SPURT vs OPERA reference comparison — bias and RMSE ~1000× wrong

**File:** `run_eval_disp.py:1197-1198`

**Issue:** `adapted_mm` is in mm/yr (converted by `* 1000.0` at line 1187). `ref_arr = opera_da.values.astype(float)` is the OPERA DISP velocity array in m/yr. The bias and RMSE computations then apply `* 1000.0` again:

```python
spurt_bias = float(_bias_fn(adapted_mm[valid_mask], ref_arr[valid_mask]) * 1000.0)
spurt_rmse = float(_rmse_fn(adapted_mm[valid_mask], ref_arr[valid_mask]) * 1000.0)
```

This computes `(mm/yr − m/yr) × 1000`, a unit subtraction that is ~1000× off and then scaled again. The `spurt_bias` label claims mm/yr but the value will be ~10⁶ mm/yr for any real signal. Correlation is unaffected (unitless).

**Fix:** Convert `ref_arr` to mm/yr before the metric functions, and remove the extra `* 1000.0`:

```python
ref_arr_mm = opera_da.values.astype(float) * 1000.0  # m/yr → mm/yr
spurt_bias = float(_bias_fn(adapted_mm[valid_mask], ref_arr_mm[valid_mask]))
spurt_rmse = float(_rmse_fn(adapted_mm[valid_mask], ref_arr_mm[valid_mask]))
```

---

### CR-06: `sorted_h5` used at line 1142 but only defined in `"fresh"` branch — `NameError` on cached path

**File:** `run_eval_disp.py:1142`

**Issue:** `sorted_h5` is assigned inside the `if coherence_source == "fresh":` branch. When `coherence_source == "phase3-cached"` (the SoCal production path), that branch is skipped and `sorted_h5` is never defined. Line 1142 then passes `cslc_paths=sorted_h5` to `run_disp()`, raising `NameError: name 'sorted_h5' is not defined`. The EU script does NOT have this bug — `sorted_h5` is assigned unconditionally there.

**Fix:** Move `sorted_h5` assignment outside the `"fresh"` conditional:

```python
# Define unconditionally (needed for SPURT stage regardless of coherence source)
sorted_h5 = sorted(_PhasePath("eval-disp/cslc").rglob("*.h5"))
sorted_h5 = [p for p in sorted_h5 if "runconfig" not in p.name.lower()]

if coherence_source == "fresh":
    ifgrams_stack = compute_ifg_coherence_stack(sorted_h5, boxcar_px=5)
    ...
```

---

### CR-07: `run_disp_from_aoi` calls `client.download()` — method does not exist on `CDSEClient`

**File:** `src/subsideo/products/disp.py:710`

**Issue:** `client.download(s3_key, safe_path)` is called on a `CDSEClient` instance. The public method on `CDSEClient` is `download_safe(s3_prefix: str, output_root: Path) -> Path`. There is no `download()` method. This raises `AttributeError` for every scene, making `run_disp_from_aoi` entirely unusable.

Additionally, `_validate_cds_credentials(cdsapirc_path)` is called unconditionally at line 629 regardless of whether ERA5 is used, with no `era5_mode` parameter to opt out.

**Fix:**

```python
# Wrong:
client.download(s3_key, safe_path)

# Correct:
safe_path = client.download_safe(s3_key, output_root=safe_path.parent)
```

Add `era5_mode` parameter and guard credential check:

```python
def run_disp_from_aoi(..., era5_mode: Literal["on", "off"] = "on") -> DISPResult:
    ...
    if era5_mode == "on":
        _validate_cds_credentials(cdsapirc_path)
```

---

## Warnings

### WR-01: All four SPURT ramp bugs silently swallowed by blanket `except Exception`

**File:** `run_eval_disp.py:1240-1241` and `run_eval_disp_egms.py:1129-1130`

**Issue:** The entire SPURT ramp attribution block is wrapped in `try: ... except Exception as exc_ramp: print(...)`. All four CRs above fire as exceptions caught here. The script continues with `spurt_ramp_mean = None`, silently recording BLOCKER status. There is no log write to `spurt_log_path`, and no indication whether the blocker came from a missing `spurt` module vs. a code error. This is the reason the current `cand=spurt:BLOCKER` result cannot be trusted as an algorithmic signal.

**Fix:** Write exception to `spurt_log_path` and surface programming errors:

```python
except Exception as exc_ramp:
    spurt_log_path.write_text(
        f"ramp_attribution error: {type(exc_ramp).__name__}: {exc_ramp}\n"
    )
    print(f"  SPURT ramp attribution failed: {type(exc_ramp).__name__}: {exc_ramp}")
    if isinstance(exc_ramp, (TypeError, ValueError, AttributeError)):
        raise  # surface implementation bugs loudly
```

---

### WR-02: `_reproject_mask_to_grid` duplicated identically in both eval scripts

**File:** `run_eval_disp.py` and `run_eval_disp_egms.py`

**Issue:** The helper function `_reproject_mask_to_grid` is defined in full in both files with identical implementation. Any fix must be applied to both files, with no guarantee of sync.

**Fix:** Move to `src/subsideo/validation/eval_utils.py` and import from both scripts.

---

### WR-03: `_is_sequential_12day` comment claims `<= 2` days tolerance but code uses `<= 1`

**File:** `run_eval_disp_egms.py:836-840`

**Issue:** The comment reads "Tolerance widened to +/- 2 days" but the predicate is `<= 1`. This means the code either silently excludes cross-constellation IFG pairs the comment intended to include, or the comment describes intended behavior that was never implemented.

**Fix:** Either update the comment to match the code (`<= 1` day), or update the code to match the comment and verify IFG selection impact.

---

### WR-04: `run_disp` docstring claims tophu and MintPy — neither is present in implementation

**File:** `src/subsideo/products/disp.py:444-446`

**Issue:** The docstring states "tophu unwrapping -> MintPy time-series inversion" but the implementation uses dolphin's internal PHASS/SPURT unwrapper with no tophu or MintPy call. Stale docstrings in public API functions mislead callers.

**Fix:** Update docstring to reflect the actual pipeline (dolphin phase linking + PHASS/SPURT unwrapping + ERA5 correction).

---

### WR-05: `compute_residual_velocity` uses bare `assert` for input validation

**File:** `src/subsideo/validation/selfconsistency.py:299-301`

**Issue:** `assert len(sensing_dates) == len(cslc_stack_paths), ...` is silently disabled when Python runs with `-O` (optimize) flag. For a public function with a documented contract, violated preconditions should raise `ValueError`.

**Fix:**

```python
if len(sensing_dates) != len(cslc_stack_paths):
    raise ValueError(
        f"sensing_dates length {len(sensing_dates)} != stack length {len(cslc_stack_paths)}"
    )
```

---

_Reviewed: 2026-05-05T01:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
