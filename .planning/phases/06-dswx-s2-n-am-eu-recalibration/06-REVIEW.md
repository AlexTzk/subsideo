---
phase: 06-dswx-s2-n-am-eu-recalibration
reviewed: 2026-04-26T00:00:00Z
depth: standard
files_reviewed: 33
files_reviewed_list:
  - .gitignore
  - CONCLUSIONS_DSWX.md
  - CONCLUSIONS_DSWX_EU_RECALIB.md
  - CONCLUSIONS_DSWX_N_AM.md
  - docs/dswx_fitset_aoi_selection.md
  - docs/validation_methodology.md
  - eval-dswx/meta.json
  - eval-dswx/metrics.json
  - eval-dswx_nam/meta.json
  - eval-dswx_nam/metrics.json
  - results/matrix.md
  - run_eval_dswx.py
  - run_eval_dswx_nam.py
  - scripts/recalibrate_dswe_thresholds.py
  - src/subsideo/config.py
  - src/subsideo/products/dswx.py
  - src/subsideo/products/dswx_thresholds.py
  - src/subsideo/products/types.py
  - src/subsideo/validation/_mgrs_tiles.geojson
  - src/subsideo/validation/criteria.py
  - src/subsideo/validation/dswx_failure_modes.yml
  - src/subsideo/validation/harness.py
  - src/subsideo/validation/matrix_schema.py
  - tests/unit/test_compare_dswx_shoreline.py
  - tests/unit/test_criteria_dswx_investigation.py
  - tests/unit/test_criteria_registry.py
  - tests/unit/test_dswx_decomposition.py
  - tests/unit/test_dswx_pipeline.py
  - tests/unit/test_dswx_region_resolution.py
  - tests/unit/test_dswx_thresholds.py
  - tests/unit/test_harness_jrc_retry.py
  - tests/unit/test_matrix_schema_dswx.py
  - tests/unit/test_run_eval_dswx_nam_smoke.py
  - src/subsideo/validation/compare_dswx.py
  - src/subsideo/validation/matrix_writer.py
findings:
  critical: 7
  warning: 6
  info: 4
  total: 17
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-04-26T00:00:00Z
**Depth:** standard
**Files Reviewed:** 33
**Status:** issues_found

## Summary

This phase implements: (1) decomposition of `_compute_diagnostic_tests` into `compute_index_bands` + `score_water_class_from_indices`, (2) region-aware threshold dispatch via `DSWxConfig.region`, (3) the N.Am. positive-control eval (`run_eval_dswx_nam.py`), (4) Phase 6 schema types in `matrix_schema.py`, and (5) the EU recalibration grid search (`scripts/recalibrate_dswe_thresholds.py`). The architecture is generally sound, with careful treatment of the intermediate-cache path and LOO-CV. However, several correctness defects were found spanning data-type mismatches, a silent no-op helper misleadingly named as a transformation, a concurrency hazard in the grid search, a path-traversal vector in the MGRS tile lookup, and metrics.json files committed with `git_dirty: true`.

---

## Critical Issues

### CR-01: `_apply_boa_offset_and_claverie` is a documented no-op that silently skips Claverie cross-calibration when called with raw bands

**File:** `src/subsideo/products/dswx.py:716-742`

**Issue:** `_apply_boa_offset_and_claverie` is described as "promoted helper" for Stage 3 of the recalibration script and its name implies it applies both the BOA offset and the Claverie cross-calibration. However, the function body is an explicit no-op — it just returns `band_list` unchanged. Its docstring admits the Claverie step is "already applied inside `_read_bands`", but Stage 3 of `recalibrate_dswe_thresholds.py` (line 395–397) calls this function on arrays that were already returned by `_read_bands`, which *has already applied both corrections*. The result is correct only because `_read_bands` does the work first. If any future caller passes raw DN arrays to `_apply_boa_offset_and_claverie` expecting calibration to be applied (the natural reading of the function name and signature), they will receive uncalibrated arrays with no error or warning. This is a latent correctness trap that is especially dangerous because it sits on the hot path for the EU recalibration grid search.

**Fix:** Either (a) make the function actually perform the cross-calibration on raw DN input and rename it to clearly indicate it is only for raw input, or (b) rename it to `_assert_already_calibrated` / `_noop_already_calibrated` and add an explicit assertion that serves as a guard, or (c) delete it from the public symbol list and inline a comment at the one call site that the step is already done.

```python
# Option (b): rename + guard pattern
def _noop_already_calibrated(
    band_list: list[np.ndarray],
    scene_id: str,
) -> list[np.ndarray]:
    """No-op pass-through: BOA offset + Claverie already applied by _read_bands.

    Raises AssertionError if called with clearly uncalibrated data.
    """
    _ = scene_id
    # Sanity check: calibrated blue band should rarely exceed 10000 DN
    assert len(band_list) == 6
    return band_list
```

---

### CR-02: `score_water_class_from_indices` accumulates into `diag` with repeated `+=` on a `uint8` array — overflow silently wraps when >1 test fires

**File:** `src/subsideo/products/dswx.py:193-222`

**Issue:** `diag` is `dtype=np.uint8`. The five tests add 1, 2, 4, 8, and 16 respectively. Their sum can reach 31 (0b11111), which fits in uint8. However, the accumulation uses `diag += np.uint8(condition)` then `diag += np.uint8(condition) * 2` etc. The problem is the intermediate cast: `np.uint8(condition) * 2` produces a `uint8` result. If `condition` is `True` (value 1), `np.uint8(1) * 2 = 2` — correct. But `np.uint8(condition)` where `condition` is an array produces a `bool_` array that is then multiplied, which works. The actual overflow risk is: if all 5 tests fire, `diag = 1+2+4+8+16 = 31` — still within uint8. This arithmetic is safe in the current 5-bit encoding. **However**, the cast `np.uint8(indices.mndwi > thresholds.WIGT)` raises a `DeprecationWarning` in NumPy ≥ 1.24 when the argument is an array (scalar cast from array). The correct form is `.astype(np.uint8)`. With NumPy 2.0, this becomes a hard error.

**Fix:**
```python
# Replace all occurrences of the scalar-cast-from-array pattern:
diag += (indices.mndwi > thresholds.WIGT).astype(np.uint8)
diag += (indices.mbsrv > indices.mbsrn).astype(np.uint8) * np.uint8(2)
diag += (indices.awesh > thresholds.AWGT).astype(np.uint8) * np.uint8(4)
# ... etc.
```

---

### CR-03: `_fetch_jrc_tile_for_bbox` leaves rasterio dataset handles open on partial failure paths

**File:** `src/subsideo/validation/compare_dswx.py:243-257`

**Issue:** The multi-tile merge path opens all datasets in a list comprehension (line 243: `datasets = [rasterio.open(p) for p in tile_paths]`), then uses a `try/finally` to close them. This is correct for the happy path. However, if `rasterio.open(p)` raises for one of the paths in the list comprehension itself (e.g., a file was deleted between the `stat().st_size` check on line 228 and the open on line 243), the datasets opened before the failing call are never closed — `datasets` is not yet bound, so the `finally` block references an unbound name and raises `NameError`, shadowing the original exception and leaking open file handles.

**Fix:**
```python
datasets = []
try:
    for p in tile_paths:
        datasets.append(rasterio.open(p))
    merged_arr, merged_transform = rasterio_merge(datasets)
    profile = datasets[0].profile.copy()
    profile.update(
        width=merged_arr.shape[-1],
        height=merged_arr.shape[-2],
        transform=merged_transform,
        count=1,
    )
    with rasterio.open(merged_path, "w", **profile) as dst:
        dst.write(merged_arr[0], 1)
finally:
    for ds in datasets:
        ds.close()
```

---

### CR-04: Stage 4 grid search in `recalibrate_dswe_thresholds.py` runs `Parallel(n_jobs=-1)` inside a `loky` worker context — potential nested parallelism / loky worker crash

**File:** `scripts/recalibrate_dswe_thresholds.py:528-531`

**Issue:** Stage 4 dispatches `grid_search_one_pair` via `Parallel(n_jobs=-1, backend="loky")`. Each worker call runs 1395 iterations of `score_water_class_from_indices` (a tight numpy loop). This is safe. The problem is that Stage 3 (`compute_intermediates`) also uses `Parallel(n_jobs=-1, backend="loky")` and workers may import `scipy.ndimage.binary_dilation` via `_compute_shoreline_buffer_mask`. Some scipy builds internally use OpenMP or BLAS thread pools, which can deadlock or corrupt state when spawned inside loky workers (loky uses `fork`-safe but OpenMP may not reset thread counts on fork). More critically: `n_jobs=-1` at Stage 4 spawns one worker per core to process 12 pairs simultaneously. Each of those workers internally calls `numpy` vectorized ops over arrays of shape `~(5490, 5490)` (~30 million elements). On a 12-core machine this creates 12 concurrent numpy array allocations of ~110 MB each, for ~1.3 GB peak — this exceeds stated "~30 GB per (AOI, scene)" budget estimates and may cause OOM failures on systems with less than 16 GB free. The `n_jobs=-1` should be limited.

**Fix:** Cap Stage 4 concurrency:
```python
grid_results: list[Path] = Parallel(n_jobs=min(4, len(pairs_to_download)), backend="loky")(
    delayed(grid_search_one_pair)(a.aoi_id, s, intermediates_dir)
    for (a, s), intermediates_dir in zip(pairs_to_download, intermediate_dirs, strict=False)
)
```

---

### CR-05: `_reproject_jrc_to_s2_grid` constructs a transform via `from_bounds` using a corner-swapped `min_x/max_x/min_y/max_y` from `Transformer.transform` — produces an incorrect transform when the CRS projection is non-monotonic at the bounds corners

**File:** `src/subsideo/validation/compare_dswx.py:305-310`

**Issue:** Lines 307–310 transform the bounding-box corners from EPSG:4326 to the target UTM via `t.transform(bounds_4326[0], bounds_4326[1])` and `t.transform(bounds_4326[2], bounds_4326[3])`. This assumes the corners of the geographic bounding box map to the corners of the projected bounding box. For UTM zones this is approximately true for small extents, but the function is called with `aoi.bbox` that spans up to 1° in latitude and 2° in longitude (e.g. Ebro Delta bbox `(0.50, 40.50, 1.10, 40.90)`). The resulting `from_bounds(min_x, min_y, max_x, max_y, cols, rows)` uses `min_x, min_y` and `max_x, max_y` as the min/max of the PROJECTED space. However, `Transformer.transform` with `always_xy=True` returns `(x, y)` = `(easting, northing)`. The code assigns `min_x, min_y = t.transform(lon_min, lat_min)` and `max_x, max_y = t.transform(lon_max, lat_max)`, which is fine for a standard UTM zone. **However**, if `target_transform is None` is reached (line 302), the derived transform covers the *full JRC tile* projected bounds (from `transform_bounds` on `src.crs` which is EPSG:4326, 10° tiles), not the AOI's `target_shape`. This means `from_bounds` receives the tile's full projected extent but `cols, rows` are the *AOI's* shape — the resulting pixel size is incorrect (it will be the full JRC tile cell size divided by AOI pixel count, not 30m). The function is only used from Stage 3 where `target_transform is not None` (passed as the B11 profile's transform attribute), so this code path is unreachable in current practice. But the None path is incorrect and calling code that omits `target_transform` will silently produce wrong output.

**Fix:** Add an explicit guard:
```python
if dst_transform is None:
    raise ValueError(
        "_reproject_jrc_to_s2_grid: target_transform is required; "
        "the None/derive path produces incorrect pixel size and is unsupported."
    )
```

---

### CR-06: `run_eval_dswx.py` MGRS tile `33TXP` does not match the Balaton SAFE scene ID downloaded (`T33TYN`)

**File:** `run_eval_dswx.py:97-98`, `eval-dswx/meta.json:11`

**Issue:** `run_eval_dswx.py` sets `MGRS_TILE = "33TXP"` (line 97) and uses `bounds_for_mgrs_tile("33TXP")` to define the CDSE search bbox. The committed `eval-dswx/meta.json` shows the actually-downloaded scene ID is `S2B_MSIL2A_20210708T094029_N0500_R036_T33TYN_20230203T071138` — which belongs to tile **33TYN**, not 33TXP. This is exactly the cross-tile contamination failure mode that `recalibrate_dswe_thresholds.py` guards against with its MGRS tile filter (lines 292–309). `run_eval_dswx.py` has **no such MGRS tile filter** — it picks the first cloud-free scene in the search results regardless of which tile it belongs to. The resulting DSWx product covers tile 33TYN (a neighbouring tile), not 33TXP (the intended Balaton coverage). All F1 metrics in `eval-dswx/metrics.json` are therefore computed against the wrong spatial footprint: the JRC reference covers the 33TXP AOI but the DSWx product covers 33TYN. The reported F1 = 0.816 is not the Balaton held-out F1 but an artefact of cross-tile comparison. Additionally, `recalibrate_dswe_thresholds.py` uses `33TXM` (corrected) for Balaton, not `33TXP` — there is a tile-ID inconsistency between the two scripts.

**Fix:** Add the same MGRS tile filter used in `recalibrate_dswe_thresholds.py` to `run_eval_dswx.py` Stage 2, and unify the Balaton MGRS tile ID to `33TXM` (the verified correct tile) across both scripts:
```python
# After stac_items = cdse.search_stac(...)
eligible = [
    it for it in scored
    if _cloud_cover(it) <= MAX_CLOUD_COVER
    and _item_mgrs_tile(it).upper() == MGRS_TILE.upper()
]
```

---

### CR-07: `eval-dswx/meta.json` and `eval-dswx_nam/meta.json` committed with `git_dirty: true` — metrics traceability broken

**File:** `eval-dswx/meta.json:4`, `eval-dswx_nam/meta.json:4`

**Issue:** Both committed meta.json sidecars carry `"git_dirty": true`. This means the pipeline ran against a working tree with uncommitted changes. The `input_hashes.threshold_module_sha256_prefix` values therefore cannot be reliably associated with any specific commit state. Any downstream audit that attempts to reproduce these results from the referenced `git_sha` will silently reproduce different results if the uncommitted changes included modifications to `dswx_thresholds.py`, `dswx.py`, or `compare_dswx.py`. The validation methodology document (via its meta.json reproducibility contract) requires clean-state runs.

**Fix:** Re-run both eval scripts on a clean working tree (all changes committed). If the run must proceed with uncommitted changes, enforce a warning-as-error policy in the eval scripts:
```python
if git_dirty:
    logger.error(
        "REPRODUCIBILITY: working tree is dirty (uncommitted changes). "
        "Re-run on a clean working tree before committing meta.json. "
        "Aborting."
    )
    sys.exit(1)
```

---

## Warnings

### WR-01: `run_dswx` instantiates `Settings()` unconditionally on every call, even when `cfg.region` is already set

**File:** `src/subsideo/products/dswx.py:812-815`

**Issue:** `run_dswx` always instantiates `Settings()` before checking `cfg.region`. When `cfg.region` is non-None, the Settings instance is only used to fall back — but it still reads `.env` and environment variables, which involves I/O. This creates a hidden dependency on environment state even for callers that have fully specified the config. More importantly, `Settings()` construction can fail with a `pydantic.ValidationError` if env vars contain invalid values for other settings fields (e.g., an invalid `SUBSIDEO_DSWX_REGION` unrelated to the current call). Callers passing `cfg.region="eu"` will have their run aborted by an unrelated env var misconfiguration.

**Fix:** Only construct `Settings()` when `cfg.region` is None:
```python
region = cfg.region
if region is None:
    from subsideo.config import Settings
    region = Settings().dswx_region
thresholds = THRESHOLDS_BY_REGION[region]
```

---

### WR-02: `run_eval_dswx.py` Stage 9 MGRS tile `33TXP` is used in `bounds_for_mgrs_tile` but the seed GeoJSON may not contain it

**File:** `run_eval_dswx.py:98`, `src/subsideo/validation/harness.py:222`

**Issue:** `bounds_for_mgrs_tile("33TXP")` will attempt the opera_utils primary path (which fails since opera-utils 0.25.6 lacks MGRS helpers), then fall back to the seed GeoJSON. The harness docstring (line 222) states the seed covers `10TFK, 29TNF, 33TXP at minimum`. However, based on finding CR-06, the correct Balaton tile for CDSE is `33TXM` (per the corrections in `recalibrate_dswe_thresholds.py`). If `33TXP` is not in the CDSE STAC at all, the search will return zero items for the intended tile after the MGRS filter fix from CR-06, even though `bounds_for_mgrs_tile("33TXP")` succeeds. This means the tile ID in `_mgrs_tiles.geojson` and the tile ID used in the CDSE filter must agree and both point to the correct tile.

**Fix:** Change `MGRS_TILE = "33TXP"` to `MGRS_TILE = "33TXM"` in `run_eval_dswx.py` and ensure `33TXM` is present in `_mgrs_tiles.geojson`.

---

### WR-03: Grid search parquet files from Iteration 2 (525 gridpoints) are incompatible with Iteration 3 (1395 gridpoints) but the Stage 5 assertion will silently pass if old files are partially present

**File:** `scripts/recalibrate_dswe_thresholds.py:448-450`, `562-565`

**Issue:** Stage 4's cache-hit logic checks `out_path.exists()` (line 449). If stale 525-gridpoint parquet files from Iteration 2 exist in the cache, the Stage 4 worker returns them without recomputation. Stage 5's assertion (line 562–565) checks `len(all_gs) == len(FIT_SET_AOIS) * 2 * len(GRIDPOINTS)` — but if any of the 10 parquet files have the old 525-row count while `GRIDPOINTS` now has 1395 entries, the concat will produce `10 * 525 = 5250` rows and the assertion will catch this. However, if **all** 10 parquet files are stale (all 525-row), the assertion fires: `5250 != 1395*10=13950`. But the script comment on line 448 says "Old gridscores.parquet files from Iter-2 (525 points) are stale and must be deleted before re-running this script." This is a human-action requirement with no automated enforcement. There is no code that detects or deletes stale parquet files.

**Fix:** Add a row-count staleness check in Stage 4's cache-hit path:
```python
if out_path.exists():
    existing = pq.read_table(out_path)
    if len(existing) == len(GRIDPOINTS):
        logger.info(f"grid search cache hit: {aoi_id}/{season}")
        return out_path
    else:
        logger.warning(
            f"stale gridscores.parquet ({len(existing)} rows != {len(GRIDPOINTS)}); "
            "deleting and recomputing"
        )
        out_path.unlink()
```

---

### WR-04: `_compute_shoreline_buffer_mask` docstring says "default 4-connectivity" but `binary_dilation` default uses a full 3x3 (8-connected) structuring element when `structure` is not specified

**File:** `src/subsideo/validation/compare_dswx.py:127`

**Issue:** The docstring states "Default 4-connectivity structuring element via the binary_dilation iterations parameter." `scipy.ndimage.binary_dilation` with no `structure` argument uses a cross-shaped (4-connected) structuring element only in 2D by default — this is correct. However the comment on line 127 is ambiguous about whether it is the default behaviour of the API or a deliberate choice. The inconsistency: `_rescue_connected_wetlands` in `dswx.py` line 317–318 explicitly passes `structure=np.ones((3,3), dtype=bool)` (8-connected) to achieve a square buffer. `_compute_shoreline_buffer_mask` uses the default 4-connected. These two buffers have different geometries. The inconsistency is not inherently wrong but the docstring misidentifies the structuring element as the cause of "XOR-of-dilations correctly handles the asymmetric shoreline" — it is actually the XOR logic that handles it, not the connectivity. If a future developer copies the pattern and adds an explicit `structure` arg they may inadvertently change the evaluated F1 metric.

**Fix:** Clarify the docstring and explicitly pass the structuring element:
```python
struct = None  # scipy default = 4-connected cross (not 3x3 square)
water_dilated = binary_dilation(water, structure=struct, iterations=iterations)
non_water_dilated = binary_dilation(non_water, structure=struct, iterations=iterations)
```
And update the docstring to accurately describe the connectivity.

---

### WR-05: `recalibrate_dswe_thresholds.py` Stage 10 generates a provenance string that hardcodes `"525 gridpoints = 25x21"` even though Iteration 3 expands to 1395 (45×31)

**File:** `scripts/recalibrate_dswe_thresholds.py:882`

**Issue:** Line 882 in the `new_eu_block_lines` list that gets written into `dswx_thresholds.py` contains the literal string:
```
'Joint grid search over WIGT x AWGT (525 gridpoints = 25x21); '
```
This is stale from Iteration 2. Iteration 3 uses `WIGT_VALS = np.linspace(0.08, 0.30, 45)` and `AWGT_VALS = np.linspace(-0.20, 0.10, 31)` (1395 gridpoints = 45×31), per the comment on line 200–206 and the `assert len(GRIDPOINTS) == 1395` on line 211. When Stage 10 runs, it will write `"525 gridpoints = 25x21"` into the committed `THRESHOLDS_EU.provenance_note`, which is incorrect provenance.

**Fix:** Use dynamic values:
```python
f"        'Joint grid search over WIGT x AWGT ({len(GRIDPOINTS)} gridpoints = "
f"{len(WIGT_VALS)}x{len(AWGT_VALS)}); '",
```

---

### WR-06: `compare_dswx.py` imports `from rasterio.windows import Window` and `from rasterio.windows import from_bounds as window_from_bounds` but uses them in the same function body where `rasterio.windows.transform` is called without the module import

**File:** `src/subsideo/validation/compare_dswx.py:388-393`, `470`

**Issue:** The `compare_dswx` function imports `from rasterio.windows import Window` and `from rasterio.windows import from_bounds as window_from_bounds` at the top of the function body (lines 388-392), but then at line 470 calls `rasterio.windows.transform(...)` using the `rasterio` module-level import. This works because `rasterio` is also imported at line 389, but the code inconsistently mixes module-level and from-import style for the same submodule (`rasterio.windows`). More importantly, line 388 imports `Resampling` from `rasterio.warp` while line 389 imports `reproject` and `transform_bounds` also from `rasterio.warp`. These two imports could be combined, and `from rasterio.windows import Window` is imported but `Window` is only used as a constructor argument to `rasterio.windows.transform` at line 470, which could instead use `from rasterio.windows import transform as window_transform` for consistency.

This is a maintainability issue: if `rasterio.windows` is refactored, `rasterio.windows.transform` at line 470 will fail silently until runtime while the explicit `from`-imports at the top of the function shadow the issue.

**Fix:** Consolidate imports:
```python
import rasterio
from rasterio.enums import Resampling
from rasterio.merge import merge
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import Window, from_bounds as window_from_bounds
from rasterio.windows import transform as window_transform
```

---

## Info

### IN-01: `warnings.filterwarnings("ignore")` at module level in both eval scripts suppresses all warnings globally

**File:** `run_eval_dswx.py:25-27`, `run_eval_dswx_nam.py:23`, `scripts/recalibrate_dswe_thresholds.py:30`

**Issue:** All three scripts call `warnings.filterwarnings("ignore")` at module level (before `if __name__ == "__main__"` in the case of `recalibrate_dswe_thresholds.py`). This suppresses NumPy deprecation warnings (relevant to CR-02), rasterio CRS warnings, and any library warnings emitted during testing. Running `pytest tests/unit/` from the same interpreter session would also be affected if these modules are imported. The suppression in `recalibrate_dswe_thresholds.py` is outside `__main__` guard (line 30 vs line 35), so it fires on import.

**Fix:** Scope the suppression inside `if __name__ == "__main__"` and use a context manager or `filterwarnings("ignore", category=SpecificWarning)` instead of a blanket ignore.

---

### IN-02: `test_matrix_schema_dswx.py` uses `"donana"` in the `_build_dswx_eu_metrics` helper after Iteration 2 replaced Donana with Ebro Delta

**File:** `tests/unit/test_matrix_schema_dswx.py:177-178`

**Issue:** The `_build_dswx_eu_metrics` helper at line 177 uses `fitset_aois = ["alcantara", "tagus", "vanern", "garda", "donana"]`. The recalibration script replaced Donana with `"ebro_delta"` (Iteration 2 fix B, line 169–186 of `recalibrate_dswe_thresholds.py`). The test constructs valid `LOOCVPerFold` records with `left_out_aoi="donana"` that will never match any actual recalibration output. While the schema test itself remains valid (it tests the Pydantic model shape, not the AOI names), it creates a false impression that Donana is still in the fit set and may cause confusion when the real `loocv_per_fold` output is compared against this helper's expected AOI list.

**Fix:** Update the helper to use `"ebro_delta"` instead of `"donana"`.

---

### IN-03: `eval-dswx/metrics.json` carries `fit_set_mean_f1: 0.20915...` which is an implausibly low value suggesting grid search failure or data corruption

**File:** `eval-dswx/metrics.json:26`

**Issue:** The committed `eval-dswx/metrics.json` has `"fit_set_mean_f1": 0.20915070764250182` — an F1 of ~21% across the fit set is far below the PROTEUS baseline (~82–92% expected over stable water bodies). The `loocv_mean_f1` and `loocv_gap` are `NaN`, and `loocv_per_fold` and `per_aoi_breakdown` are empty, consistent with a BLOCKER state. Yet `cell_status` is `"FAIL"` (not `"BLOCKER"`) and a real Balaton F1 of 0.816 was computed. This means the Stage 6 edge-of-grid or Stage 8 LOO-CV gates must have triggered, writing the 0.209 fit_set_mean_f1 as a partial result, but the script's BLOCKER path should have called `sys.exit(2)` and never reached the final metrics write. The `0.209` value is suspicious and may indicate that the Iteration 2 525-gridpoint parquet files were partially loaded (the stale-cache issue from WR-03) producing a joint best at the wrong gridpoint. The committed state therefore does not represent a valid recalibration run.

**Fix:** Investigate and re-run the recalibration on clean cache after deleting stale parquet files. The `fit_set_mean_f1` in the final committed `metrics.json` must be > 0.85 for the output to be meaningful.

---

### IN-04: `run_eval_dswx_nam.py` Stage 10 uses `git status --porcelain` to detect dirty state but `run_eval_dswx.py` uses `git diff --quiet` — inconsistent approach, and `--porcelain` includes untracked files

**File:** `run_eval_dswx_nam.py:483-485`, `run_eval_dswx.py:465-466`

**Issue:** `run_eval_dswx_nam.py` uses `git status --porcelain` output, which includes untracked files (files that are new and not staged). `run_eval_dswx.py` uses `git diff --quiet` which only detects tracked file modifications. An untracked `eval-dswx_nam/jrc/*.tif` file (which `.gitignore` excludes) will mark the N.Am. meta.json as `git_dirty=True` even if the code is clean. Meanwhile `run_eval_dswx.py`'s `git diff --quiet` will miss staged-but-not-committed changes. Both approaches are imprecise; a consistent approach using `git diff --quiet HEAD` (which checks both staged and unstaged changes to tracked files) should be used in both scripts.

**Fix:** Use a consistent check in both scripts:
```python
git_dirty = bool(
    subprocess.call(
        ["git", "diff", "--quiet", "HEAD"],
        stderr=subprocess.DEVNULL,
        cwd=Path(__file__).parent,
    )
)
```

---

_Reviewed: 2026-04-26T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
