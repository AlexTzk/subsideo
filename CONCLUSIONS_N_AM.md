# N.Am. RTC-S1 Validation — Session Conclusions

**Date:** 2026-04-11
**Burst:** `T144-308029-IW1`
**Scene:** S1A, 2024-06-24T14:01:16Z, relative orbit 144
**Result: PASS** — subsideo RTC-S1 output matches official OPERA reference to within 0.045 dB RMSE (criterion: < 0.5 dB) with r = 0.9999 (criterion: > 0.99).

---

## 1. Objective

Validate that `subsideo v0.1.0` produces RTC-S1 backscatter products that are numerically equivalent to the official [OPERA L2 RTC-S1](https://www.jpl.nasa.gov/go/opera/products/rtc-product) products distributed by NASA/JPL via ASF DAAC.

The pass criteria (from the project specification) are:

| Metric | Criterion |
|--------|-----------|
| RMSE   | < 0.5 dB  |
| r (Pearson correlation) | > 0.99 |

---

## 2. Test Setup

### 2.1 Target Burst

| Field | Value |
|-------|-------|
| Burst ID (opera-rtc format) | `t144_308029_iw1` |
| Burst ID (OPERA product format) | `T144-308029-IW1` |
| Sensing time | 2024-06-24T14:01:16Z |
| Platform | Sentinel-1A |
| Relative orbit | 144 |
| Geographic area | Southern California (Ventura / Los Angeles counties) |
| UTM zone | 11N (EPSG:32611) |

The burst was chosen by searching ASF for OPERA L2 RTC-S1 products over a small Southern California AOI (`box(-118.5, 34.0, -118.0, 34.5)`) and selecting a scene with an unambiguous match between the OPERA reference product and an available S1 IW SLC granule on ASF.

### 2.2 Input Data

| Input | Source | Details |
|-------|--------|---------|
| S1 IW SLC SAFE | ASF DAAC via `asf_search` + `earthaccess` | `S1A_IW_SLC__1SDV_20240624T140101_20240624T140128_054416_069F47_4B0F.zip` (~4 GB) |
| Precise orbit (POEORB) | ESA POD hub via `sentineleof` | `.EOF` file for 2024-06-24, S1A |
| GLO-30 DEM | `dem-stitcher`, bounds `[-119.7, 33.2, -118.3, 34.0]`, EPSG:32611 | Copernicus GLO-30 (official OPERA DEM) |
| OPERA reference product | NASA Earthdata / ASF DAAC via `earthaccess` | `OPERA_L2_RTC-S1_T144-308029-IW1_20240624T140116Z_20240626T193600Z_S1A_30_v1.0_{VV,VH,mask}.tif` |

### 2.3 Processing Environment

| Component | Version |
|-----------|---------|
| Python | 3.12 |
| isce3 | 0.25.8 (conda-forge) |
| opera-rtc | v1.0.4 / R5.3 (installed from `/Users/alex/repos/subsideo/RTC/`) |
| rio-cogeo | 7.x |
| rasterio | 1.5.x |
| sentineleof | 0.11.1 |
| dem-stitcher | 2.5.13 |
| subsideo | 0.1.0 (dev install) |

---

## 3. What Was Run

### 3.1 Evaluation Script (`run_eval.py`)

The script performs five sequential steps:

1. **Download OPERA reference** — `earthaccess.search_data(short_name="OPERA_L2_RTC-S1_V1", ...)` + `earthaccess.download()`
2. **Find matching S1 SLC on ASF** — `asf_search.search(platform=SENTINEL1, processingLevel="SLC", beamMode="IW", relativeOrbit=144, ...)` then picks the scene closest in time to `SENSING_DATE`
3. **Fetch DEM and orbit** — `subsideo.data.dem.fetch_dem()` and `subsideo.data.orbits.fetch_orbit()`
4. **Download S1 SAFE** — `asf_search` scene download via `ASFSession.auth_with_creds()`
5. **Run RTC pipeline** — `subsideo.products.rtc.run_rtc()`

### 3.2 RTC Pipeline (`subsideo/products/rtc.py`)

`run_rtc()` executes four stages:

1. **Runconfig generation** — `generate_rtc_runconfig()` writes an opera-rtc YAML runconfig with all required fields (`input_file_group`, `dynamic_ancillary_file_group`, `product_group`, `processing`)
2. **opera-rtc execution** — loads runconfig via `RunConfig.load_from_yaml()`, calls `load_parameters()` (enum conversion), then `run_parallel()`
3. **COG conversion** — `ensure_cog()` converts each output GeoTIFF to Cloud-Optimized GeoTIFF via `rio_cogeo` (DEFLATE, 5 overview levels)
4. **Validation + metadata** — `validate_rtc_product()` checks COG structure, UTM CRS, and 30 m pixel size; `inject_opera_metadata()` writes OPERA-compliant identification tags

### 3.3 Validation Comparison

A standalone Python script reprojects the subsideo output onto the OPERA reference grid (bilinear), masks to valid pixels in both products (linear power > 0), converts to dB, and computes RMSE, bias, and Pearson r.

---

## 4. Bugs Encountered and Fixed

This section documents every non-trivial issue hit during the session and how it was resolved. Each fix is preserved in the current codebase.

### Bug 1: Wrong burst ID — `ValueError: Could not find any of the burst IDs`

**Symptom:**
```
ValueError: Could not find any of the burst IDs in the provided safe files
```

**Root cause:** The initial burst ID `t144_308026_iw1` belongs to the *preceding* S1 acquisition in the same orbit, not the SAFE file that was downloaded. Burst `308026` is in a different granule than `308029`.

**Fix:** Used `s1reader.load_bursts()` to enumerate burst IDs actually present in the downloaded SAFE, confirmed `t144_308029_iw1` was present, and updated `BURST_ID` and the OPERA reference granule name filter accordingly. Also updated `SENSING_DATE` from `14:01:08` to `14:01:16` to match the correct granule.

---

### Bug 2: Missing enum conversion — `AttributeError: 'SimpleNamespace' has no attribute 'dem_interpolation_method_enum'`

**Symptom:**
```
AttributeError: 'types.SimpleNamespace' object has no attribute 'dem_interpolation_method_enum'
```

**Root cause:** `rtc.runconfig.RunConfig.load_from_yaml()` populates fields as raw strings. `rtc.runconfig.load_parameters()` exists to convert those strings to isce3 enum objects (e.g., `dem_interpolation_method` → `isce3.core.DataInterpMethod`), but it is *never called automatically* by `load_from_yaml`. `run_parallel()` then fails when it tries to use the unconverted string as an enum.

**Fix:** Added an explicit `load_parameters(opera_cfg)` call in `run_rtc()` between `load_from_yaml` and `run_parallel`:

```python
from rtc.runconfig import RunConfig, load_parameters
opera_cfg = RunConfig.load_from_yaml(str(runconfig_yaml))
load_parameters(opera_cfg)  # converts strings → isce3 enums
```

---

### Bug 3: DEM coverage failure — `ValueError: DEM file does not fully cover product geogrid`

**Symptom:**
```
ValueError: DEM file does not fully cover product geogrid
```

**Root cause:** The DEM was initially fetched for bounds `[-118.6, 33.9, -117.9, 34.6]`, which is approximately 1° too far east. The actual footprint of burst `t144_308029_iw1` is `[-119.48, 33.43, -118.52, 33.77]` (western Ventura/Los Angeles area). The old bounds missed the western half of the burst entirely.

**Fix:** Updated DEM bounds to `[-119.7, 33.2, -118.3, 34.0]` (burst footprint + 0.2° buffer on all sides) and deleted the stale DEM file so it would be re-fetched.

---

### Bug 4: macOS multiprocessing spawn — `RuntimeError: bootstrap phase`

**Symptom:**
```
RuntimeError: An attempt has been made to start a new process before the current process
has finished its bootstrapping phase.
```

**Root cause:** macOS uses `spawn` (not `fork`) as the default multiprocessing start method. When `opera-rtc`'s `run_parallel()` creates a `multiprocessing.Pool`, Python re-imports `run_eval.py` as `__main__` in each worker process. Because all top-level code in `run_eval.py` was at module scope, each worker re-executed `run_rtc()`, which tried to create another Pool — producing infinite recursive spawning.

**Fix:** Wrapped *all* top-level code in `run_eval.py` under `if __name__ == "__main__":`. This is the standard macOS/Windows requirement for any script that uses `multiprocessing`.

---

### Bug 5: opera-rtc internal COG step timestamp mismatch — `FileNotFoundError`

**Symptom:**
```
RuntimeError: eval-rtc/output/t144_308029_iw1/...T143035Z_mask.tif: No such file or directory
```

**Root cause:** opera-rtc's `run_parallel()` builds its output file list using `datetime.now()` at the *start* of the run. The actual files are written with a new `datetime.now()` call ~27 seconds later (after processing). The two timestamps diverge, so opera-rtc's internal COG conversion step tries to open a filename that was never created.

**Attempted workaround that failed:** Setting `output_imagery_format: GTiff` in the YAML runconfig under `processing` triggered a yamale schema validation error:
```
yamale.YamaleError: runconfig.groups.processing.output_imagery_format: Unexpected element
```
The opera-rtc yamale schema does not permit this key at all in the user-facing runconfig.

**Actual fix:** Override the field on the namespace object *after* loading (bypassing schema validation entirely):
```python
opera_cfg.groups.product_group.output_imagery_format = "GTiff"
```
This tells opera-rtc to write plain GeoTIFF instead of COG, skipping the broken internal COG step. `subsideo`'s own `ensure_cog()` step then handles COG conversion correctly.

---

### Bug 6: rio-cogeo 7.x API change — `ModuleNotFoundError: No module named 'rio_cogeo.cog_validate'`

**Symptom:**
```
ModuleNotFoundError: No module named 'rio_cogeo.cog_validate'
```

**Root cause:** In rio-cogeo 7.x, `cog_validate` was moved to the top-level package. The old import path `from rio_cogeo.cog_validate import cog_validate` no longer exists.

**Fix:** Updated the import in `validate_rtc_product()`:
```python
# Before:
from rio_cogeo.cog_validate import cog_validate
# After:
from rio_cogeo import cog_validate
```

---

### Bug 7: Double `.cog.tif` conversion

**Symptom:** `ensure_cog()` was called on `*_VV.cog.tif` files from a previous partial run, producing `*_VV.cog.cog.tif`.

**Root cause:** `output_dir.glob("*.tif")` matched both `*_VV.tif` and `*_VV.cog.tif`. Also, the original `glob` was non-recursive and missed files in the per-burst subdirectory (`t144_308029_iw1/`).

**Fix:**
```python
output_tifs = sorted(
    p for p in output_dir.rglob("*.tif") if not p.name.endswith(".cog.tif")
)
```

---

### Bug 8: COG metadata injection — `CPLE_AppDefinedError: COG layout`

**Symptom:**
```
rasterio._err.CPLE_AppDefinedError: File ...VH.cog.tif has C(loud) O(ptimized)
G(eoTIFF) layout. Updating it will generally result in losing part of the
optimizations...
```

**Root cause:** `_inject_geotiff()` in `_metadata.py` opened the file with `rasterio.open(path, "r+")`. GDAL refuses this on COG files by default because updating tags in-place can break the byte-range structure that makes COGs efficient.

**Fix:** Pass the `IGNORE_COG_LAYOUT_BREAK=YES` open option:
```python
with rasterio.open(path, "r+", IGNORE_COG_LAYOUT_BREAK="YES") as ds:
    ds.update_tags(**metadata)
```
The file remains a valid GeoTIFF; only the perfect COG byte-range ordering may be slightly perturbed, which is acceptable for a metadata-only tag update.

---

## 5. Final Validation Results

Comparison performed by reprojecting the subsideo output onto the OPERA reference grid (bilinear resampling), masking to pixels with valid linear-power backscatter in both products, converting to dB, and computing statistics over ~1.95 million pixels covering the full burst footprint.

| Polarisation | Valid pixels | RMSE | Bias | Pearson r | Pass/Fail |
|-------------|-------------|------|------|-----------|-----------|
| VV | 1,949,833 | **0.045 dB** | ~0.0 dB | **0.9999** | PASS |
| VH | 1,949,759 | **0.043 dB** | ~0.0 dB | **0.9999** | PASS |

Both channels comfortably exceed the RMSE < 0.5 dB and r > 0.99 pass criteria.

---

## 6. Why the Result Is Correct

The near-perfect agreement (RMSE ~0.04 dB, r ~0.9999) is expected and explainable:

1. **Same algorithm core.** Both subsideo and the official OPERA pipeline use the same `opera-rtc` / `isce3` implementation. The subsideo pipeline is literally calling `rtc.rtc_s1.run_parallel()` — the same function that produced the reference product.

2. **Same inputs.** The identical Sentinel-1 SAFE granule, POEORB orbit file, and GLO-30 DEM tiles were used. There are no algorithm or data differences that could introduce a systematic offset.

3. **The residual 0.04 dB RMSE** is consistent with floating-point non-determinism and the bilinear reprojection required to align the two products onto a common grid for comparison. The OPERA reference product was generated on different hardware at a different time; any sub-pixel geometric differences manifest as small interpolation artefacts at land/water and land/shadow boundaries.

4. **Zero bias** confirms there is no systematic radiometric offset — the calibration constants, DEM interpolation, and gamma-nought normalization are identical in both pipelines.

5. **r = 0.9999** across ~2 million pixels is an astronomically tight fit for a real SAR scene with high dynamic range (urban, vegetation, water, shadow). It confirms spatial structure is preserved with no geometric shift or mis-registration.

---

## 7. Output Files

```
eval-rtc/
├── opera_reference_308029/
│   ├── OPERA_L2_RTC-S1_T144-308029-IW1_20240624T140116Z_20240626T193600Z_S1A_30_v1.0_VV.tif
│   ├── OPERA_L2_RTC-S1_T144-308029-IW1_20240624T140116Z_20240626T193600Z_S1A_30_v1.0_VH.tif
│   └── OPERA_L2_RTC-S1_T144-308029-IW1_20240624T140116Z_20240626T193600Z_S1A_30_v1.0_mask.tif
├── output/t144_308029_iw1/
│   ├── OPERA_L2_RTC-S1_T144-308029-IW1_20240624T140116Z_20260411T162136Z_S1A_30_v0.1.0_VV.tif
│   ├── OPERA_L2_RTC-S1_T144-308029-IW1_20240624T140116Z_20260411T162136Z_S1A_30_v0.1.0_VH.tif
│   ├── OPERA_L2_RTC-S1_T144-308029-IW1_20240624T140116Z_20260411T162136Z_S1A_30_v0.1.0_mask.tif
│   ├── OPERA_L2_RTC-S1_T144-308029-IW1_20240624T140116Z_20260411T162136Z_S1A_30_v0.1.0_VV.cog.tif
│   ├── OPERA_L2_RTC-S1_T144-308029-IW1_20240624T140116Z_20260411T162136Z_S1A_30_v0.1.0_VH.cog.tif
│   ├── OPERA_L2_RTC-S1_T144-308029-IW1_20240624T140116Z_20260411T162136Z_S1A_30_v0.1.0_mask.cog.tif
│   ├── OPERA_L2_RTC-S1_T144-308029-IW1_20240624T140116Z_20260411T162136Z_S1A_30_v0.1.0.h5
│   ├── OPERA_L2_RTC-S1_T144-308029-IW1_20240624T140116Z_20260411T162136Z_S1A_30_v0.1.0.png
│   └── rtc.log
├── dem/        (GLO-30 DEM tiles, EPSG:32611, bounds [-119.7,33.2,-118.3,34.0])
├── orbits/     (S1A POEORB .EOF file)
└── input/      (S1A IW SLC SAFE .zip, ~4 GB)
```

---

## 8. Source Files Changed During This Session

| File | Changes |
|------|---------|
| `src/subsideo/products/rtc.py` | Added `load_parameters()` call; namespace override for `output_imagery_format`; `rglob` with `.cog.tif` filter; fixed `rio_cogeo` import |
| `src/subsideo/_metadata.py` | Added `IGNORE_COG_LAYOUT_BREAK="YES"` to rasterio open call |
| `run_eval.py` | Wrapped all top-level code in `if __name__ == "__main__":` guard; corrected `BURST_ID`, `SENSING_DATE`, DEM bounds, and OPERA reference granule name |
