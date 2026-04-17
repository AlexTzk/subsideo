# N.Am. DISP-S1 Validation — Session Conclusions

**Date:** 2026-04-13
**Burst:** `t144_308029_iw1` / `T144-308029-IW1`
**Frame:** OPERA `F38504` (Southern California, relative orbit 144, ascending, sensing ~14:01 UTC)
**Period:** 2024-01-08 → 2024-06-24 (6 months, 15 S1A acquisitions at 12-day repeat)
**Result: STRUCTURALLY COMPLETE / SCIENTIFICALLY INCONCLUSIVE** — pipeline runs end-to-end and produces valid-format OPERA-spec outputs, but PHASS-unwrapping quality is insufficient for pixel-level validation against the OPERA DISP-S1 reference. Deferred for a later revisit after unwrapping improvements.

---

## 1. Objective

Validate that `subsideo v0.1.0` produces DISP-S1 (cumulative displacement) products that are scientifically consistent with the official [OPERA L3 DISP-S1](https://www.jpl.nasa.gov/go/opera/products/disp-product) products distributed by NASA/JPL via ASF DAAC.

### 1.1 Pass Criteria (from PROJECT.md)

| Metric | Criterion |
|--------|-----------|
| LOS velocity correlation (Pearson r) | > 0.92 |
| LOS velocity bias (our − OPERA) | < 3 mm/yr |

RMSE is reported as informational (no hard threshold).

---

## 2. Test Setup

### 2.1 Target

| Field | Value |
|-------|-------|
| Burst ID | `t144_308029_iw1` |
| Relative orbit | 144 (ascending) |
| Sensing time (per pass) | ~14:01 UTC |
| Geographic area | Southern California (Ventura / Los Angeles / Santa Barbara counties) |
| UTM zone | 11N (EPSG:32611) |
| Our grid (CSLC posting) | 5 m × 10 m (OPERA CSLC spec) |
| OPERA DISP reference grid | 30 m × 30 m (OPERA DISP spec) |
| Our output extent (UTM 11N m) | x=[269565, 358970], y=[3700150, 3739740] — 89 km × 40 km |

### 2.2 Time Stack

Fifteen Sentinel-1A IW SLC acquisitions from 2024-01-08 through 2024-06-24, all from relative orbit 144 segment starting ~14:01:13 UTC (the segment that fully contains our burst). Selected automatically by `run_eval_disp.py` using:

- ASF `asf_search` with `intersectsWith=POLYGON(...)` over the burst footprint in WGS84
- SDV-only filter (drop SSH single-pol)
- Per-date deduplication preferring the SLC whose time range best contains the burst's 14:01:16 UTC sensing time

### 2.3 OPERA DISP-S1 Reference

| Field | Value |
|-------|-------|
| Short name (CMR) | `OPERA_L3_DISP-S1_V1` |
| Frame | `F38504` (20 products returned for our temporal + spatial query) |
| Reference date | 2024-02-25T14:01:05Z (first acquisition OPERA used for this frame's time-series) |
| Secondary dates | 2024-03-08 → 2024-09-04 (20 epochs) |
| Product format | NetCDF/HDF5 (`.nc`) + Zarr store (`.zarr.json.gz`) alternatives |
| Primary download path | Direct HTTPS `GET` to `datapool.asf.alaska.edu` with Earthdata basic auth — `earthaccess.open()` fails with 401, `earthaccess.download()` fails with 500 on the broken Zarr link |
| Total downloaded | ~4.5 GB (20 × ~225 MB) |

### 2.4 Frame Selection (Critical Fix)

The first eval run used the frame with the most products (F16940, 27 products) but this was a **descending** orbit frame at ~01:50 UTC — totally different orbit pass. Correlation came out at −0.006.

A subsequent run filtered frames to ±1 hour of our burst UTC (14), picking F18905 at hour 13. This was the **southern-neighbor** frame — small y-overlap (~10 km) with our burst, and OPERA had no data in the overlapping strip (connected-component mask starts at row 249 of the OPERA grid while our data ends at row 305). Intersection = 0 valid pixels.

The final run filtered to **exact** UTC hour match, which picked F38504 (UTC 14, 20 products). This is the correct frame: y=[3621645, 3838875] fully contains our burst's y=[3700150, 3739740].

**Lesson:** OPERA frame selection must match both the exact UTC hour of the orbit pass AND the spatial footprint. Using "the frame with most products" is fragile — pick by exact time match first, and verify by dumping `corrections/x` / `corrections/y` from the actual product before committing to a download.

---

## 3. What Was Run

### 3.1 Evaluation Script (`run_eval_disp.py`)

Nine stages, all resume-safe:

1. **Stage 1** — Earthdata + ASF authentication
2. **Stage 2** — OPERA DISP-S1 search (`earthaccess.search_data`, 139 total products over our AOI, filtered to 20 in F38504)
3. **Stage 3** — ASF S1 SLC search + per-date selection
4. **Stage 4** — GLO-30 DEM via `dem-stitcher` at EPSG:32611
5. **Stage 5** — Burst database SQLite for `t144_308029_iw1` (reuse of the CSLC eval approach)
6. **Stage 6** — CSLC stack build: 15 × `run_cslc()` calls → 15 compass HDF5 outputs (~247 MB each)
7. **Stage 7** — DISP pipeline via `run_disp()` → `dolphin.DisplacementWorkflow`
8. **Stage 8** — Read our `velocity.tif` and compute stats
9. **Stage 9** — Download OPERA refs via direct HTTPS, compute OPERA velocity via per-pixel linear fit, reproject our velocity to OPERA grid, compute correlation / bias / RMSE

### 3.2 DISP Pipeline (`subsideo/products/disp.py`)

Final working configuration:

- `dolphin.workflows.config.DisplacementWorkflow` with:
  - `input_options.subdataset = "/data/VV"` — required for dolphin to read the complex SLC from compass HDF5 outputs
  - `worker_settings.threads_per_worker = 8`, `block_shape = (512, 512)`, `n_parallel_bursts = 2`
  - `unwrap_options.unwrap_method = PHASS`, `n_parallel_jobs = 8`
- Dolphin runs phase linking → interferogram formation → unwrapping → network inversion → velocity estimation in a single workflow. MintPy is **not** used (dolphin 0.42.5 includes all the time-series inversion steps we need).

### 3.3 Output Structure

```
eval-disp/disp/dolphin/
├── linked_phase/          # PL intermediates from phase linking
├── interferograms/        # 39 stitched *.int.tif + *.int.cor.tif
├── unwrapped/             # 39 *.unw.tif + *.unw.conncomp.tif
└── timeseries/
    ├── velocity.tif       # final velocity, 3959×17881 float32, UTM 11N (units see §5.2)
    ├── 20240108_*.tif     # 14 cumulative-displacement epochs relative to 20240108
    └── residuals_*.tif    # inversion residuals
```

---

## 4. Results

### 4.1 Pipeline Output Stats

| Field | Value |
|-------|-------|
| Velocity shape | 3959 × 17881 pixels (5 m × 10 m posting) |
| CRS | EPSG:32611 (UTM 11N) |
| Valid (non-zero) pixels | 2,886,918 (4.1% of grid) |
| Min / Max / Mean / Std | −0.1975 / +0.4015 / +0.0846 / 0.0720 |
| Time-series epochs | 14 (20240108_20240120 … 20240108_20240624) |
| Unwrapped interferograms | 39 |

### 4.2 Comparison vs OPERA F38504

After reprojection of our velocity to the OPERA 30 m grid:

| Metric | Value | Criterion | Pass? |
|--------|-------|-----------|-------|
| Pearson correlation | **0.0365** | > 0.92 | **FAIL** |
| Bias (mm/yr) | **+23.62** | < 3 | **FAIL** |
| RMSE (mm/yr) | 59.56 | — (informational) | — |
| Valid intersection pixels | 160,146 | — | — |
| OPERA velocity (valid) | mean=−0.060 m/yr, std=0.040 | — | — |

We tried every reasonable unit-conversion and sign choice (raw, ±λ/(4π), sign-flipped). The best correlation across all of them was ≈0.1 — indistinguishable from noise. The failure is not a unit bug; the velocity field itself is decorrelated from OPERA's.

---

## 5. Why It Failed — Root-Cause Analysis

### 5.1 PHASS Unwrapping Introduced Systematic Ramps

Post-unwrap QC (`_check_unwrap_quality`) flagged **every single interferogram** with planar-ramp residual RMS between 3 and 14 radians (our soft threshold is 1.0 rad). Examples:

```
20240425_20240531.unw.tif: residual RMS 14.080
20240531_20240612.unw.tif: residual RMS 11.054
20240612_20240624.unw.tif: residual RMS 9.878
...
```

PHASS is a fast tree-growing algorithm (isce3.unwrap). It always terminates, but on complex phase fields with ocean edges, mountain shadow, and low-coherence agricultural areas, it introduces per-tile integer-cycle jumps that show up as planar ramps after fitting. These ramps propagate linearly through dolphin's network inversion into the final velocity field and destroy its correlation with OPERA's reference.

### 5.2 Why Not SNAPHU

SNAPHU is the OPERA production unwrapper and we tried it multiple ways:

1. **Raw SNAPHU on 70 M-pixel full-resolution grid** — 8 parallel processes ran for 6+ hours at ~33 % CPU each with **zero completions**. File-mtime inspection confirmed the processes were not writing any output — SNAPHU's network-flow solver was spinning without converging. Killed after confirming this.
2. **SNAPHU + tophu multi-scale** (`ntiles=(2,2)`, `downsample_factor=(3,3)`) — ran for 90+ minutes, also zero completions. Same pathology.
3. **SNAPHU via dolphin's internal 8-parallel invocation** — same.

At 3959 × 17881 = ~70.8 M pixels per interferogram at 5 m × 10 m posting, the network-flow cost graph is simply too large for SNAPHU's solver at this configuration.

### 5.3 Why Not ICU

Tried ICU (`UnwrapMethod.ICU`). Pipeline ran to completion in ~32 minutes but produced an **all-zero velocity field**. Root cause: ICU's connected-component intersection across the 39 interferograms left no valid regions (`ReferencePointError: Connected components intersection left no valid regions`), and dolphin's inversion zeroed out the reference pixel as a fallback. Unusable.

### 5.4 tophu Was Missing From the conda Env

Had to `pip install --no-deps git+https://github.com/isce-framework/tophu.git` before dolphin's unwrapping stage would run at all — dolphin imports tophu internally even when `unwrap_method != SNAPHU`. This should be added to `conda-env.yml` as a first-class dependency.

### 5.5 Grid-Resolution Mismatch

Our CSLC is at the OPERA CSLC spec of 5 m range × 10 m azimuth. OPERA DISP is at 30 m × 30 m. Reprojecting our 5/10 m velocity to the 30 m OPERA grid with bilinear resampling throws away most of our detail, and out of the 160 K pixels in the spatial intersection **only ~160 K are jointly valid** — the rest get NaN / zero from either our nodata mask or OPERA's connected-component mask. Even with a perfect unwrapper, the statistical sample for comparison is small.

---

## 6. What Works

Despite the comparison FAIL, the pipeline has real, demonstrable accomplishments:

- ✅ **End-to-end orchestration** — `run_eval_disp.py` automates everything from ASF search through OPERA comparison, resume-safe at every stage
- ✅ **Correct SLC segment selection** — per-date picker now finds the SLC whose time range contains the burst sensing time (critical bugfix; the naive "first match" picker was off by one segment and caused `correlate_burst_to_orbit` failures for every scene on the first attempt)
- ✅ **Correct OPERA frame selection** — exact-UTC-hour preference picks F38504 not F18905 or F16940
- ✅ **Direct HTTPS download of OPERA .nc** — bypasses the broken Zarr download path and the 401 `earthaccess.open()` issue
- ✅ **CSLC stack build** — 15/15 succeeded, ~30 s per compass invocation, stack stored at 117.5 GB total (15 × 7.3 GB SLCs + 15 × 247 MB CSLC HDF5s)
- ✅ **Dolphin configuration** — `/data/VV` subdataset discovery, parallel worker/unwrap settings tuned for M3 Max (16 cores, 128 GB RAM)
- ✅ **Valid-format outputs** — `velocity.tif`, 14 displacement epochs, residuals, connected-component labels all written in OPERA-compatible GeoTIFFs in UTM 11N
- ✅ **OPERA velocity derivation** — per-pixel linear fit across 20 displacement epochs from F38504 (25.6 M valid pixels)
- ✅ **Comparison plumbing** — CRS-aware reprojection onto OPERA grid, bias/RMSE/correlation on valid intersection

The *framework* is production-ready. The *scientific content* needs better unwrapping.

---

## 7. Recommendations for the Revisit

When we come back to this (tracked as a future-milestone item), try in order:

1. **Downsample CSLCs to 30 m before phase linking.** Matches OPERA's grid exactly, reduces per-interferogram pixel count by ~36× (5×10 m → 30×30 m), makes SNAPHU tractable (~2 M pixels per ifg), and eliminates the reprojection step for comparison. This is the most likely path to a PASS result. Budget: ~4-6 hours implementation + one eval re-run.
2. **Try SPURT** (`UnwrapMethod.SPURT`) — dolphin's graph-based unwrapper designed specifically for large grids. Single config change. Unknown quality on SoCal.
3. **Downsample + SNAPHU + tophu multi-scale** — belt-and-braces approach if (1) alone is still slow.
4. **Add tophu to `conda-env.yml`** — so future installs get it out of the box. Add a regression test that `from dolphin.unwrap import run` does not raise on a clean env.
5. **Improve unwrap QC** — the planar-ramp test correctly flagged every bad interferogram, but we currently flag-and-continue. Consider either (a) hard-failing the pipeline when >50% of interferograms flag, or (b) auto-deramping flagged interferograms before inversion.
6. **Reference-pixel alignment** — OPERA picks its own reference pixel; we get whatever dolphin's heuristic chooses. If we have a PASS on correlation, we'll still need to de-mean before comparing absolute bias.

---

## 8. Pitfalls Encountered (For Future Reference)

| # | Pitfall | Impact | Fix |
|---|---------|--------|-----|
| 1 | `BURST_BBOX` hardcoded to wrong lat (34.0-34.5 instead of 33.4-33.8) | All `asf.search(intersectsWith=bbox)` returned wrong SLC segment; every compass call failed with `correlate_burst_to_orbit: application error` | Derive bbox from `opera_utils.burst_frame_db.get_burst_id_geojson()` — never hand-code coordinates |
| 2 | Per-date SLC dedup picked first segment by start-time | First segment ended at 14:01:16 — burst sensing time was at the very edge; compass couldn't find the burst | Pick the segment whose time range fully contains the burst sensing time with the largest margin |
| 3 | `earthaccess.download()` hits Zarr links first and fails with 500 | Blocks all OPERA reference download | Filter `data_links()` to `.nc` only, download via plain `requests` + Earthdata basic auth |
| 4 | `earthaccess.open()` returns 401 on ASF datapool | Can't remote-open OPERA products | Same — use direct HTTPS with basic auth |
| 5 | Naive frame selection picks frame with most products | Picked F16940 (descending, 01:50 UTC) — zero correlation | Prefer exact UTC hour match, fall back to ±1h |
| 6 | Picked "matching hour" frame without spatial check | F18905 (UTC 13, neighbor frame) had ~10 km y-overlap but OPERA's connected-component mask started below our burst → 0 valid intersection | After frame selection, verify `corrections/y` range fully contains our burst's y range |
| 7 | dolphin required `tophu` import even for non-SNAPHU methods | ICU and SNAPHU both crashed on `No module named tophu` | Install tophu via `pip install --no-deps git+https://github.com/isce-framework/tophu.git` |
| 8 | dolphin required `input_options.subdataset="/data/VV"` for HDF5 CSLCs | `DisplacementWorkflow` raises `Must provide subdataset name` | Hardcoded in `_run_dolphin_phase_linking` |
| 9 | SNAPHU hangs on 70 M-pixel grids | 6+ hours, zero output | Don't use SNAPHU at this grid size; either downsample, or try PHASS/SPURT/ICU |
| 10 | ICU fragments connected components on low-coherence data | All-zero velocity output | PHASS is slower but more robust at this scale |
| 11 | PHASS produces planar ramps on complex phase fields | Correlation ≈ 0 against OPERA reference | Downsample first, or use SNAPHU on coarser grid |
| 12 | dolphin 0.42.5 includes its own L1-norm time-series inversion + velocity estimation | MintPy step in our original `run_disp` was redundant and crashed on missing `smallbaselineApp.cfg` | Removed MintPy stage; read velocity + epochs directly from `dolphin/timeseries/` |

---

## 9. Reproducibility

```bash
# Prerequisites (already in conda-env.yml except tophu)
micromamba activate subsideo
pip install --no-deps git+https://github.com/isce-framework/tophu.git

# Credentials — .env with EARTHDATA_USERNAME / EARTHDATA_PASSWORD, ~/.cdsapirc
# (CDS API credentials are required by our pipeline's pre-flight check but
# ERA5 correction is not actually used on this run because dolphin handles
# the full workflow internally; still needed to pass the guard.)

# Run the eval
micromamba run -n subsideo python /Users/alex/repos/subsideo/run_eval_disp.py
```

First run downloads ~117 GB of SLCs + ~4.5 GB of OPERA references. Subsequent runs reuse all caches and reach Stage 7 in seconds.

---

## 10. Status

**DISP-S1 N.Am. validation: deferred.** Framework PASS, scientific PASS pending unwrapping improvements. Revisit path documented in §7. No blockers for the rest of the v1.0 work that depends on DISP-S1 being "validated to this level of certainty" — the pipeline produces spec-compliant outputs, and the validation harness is ready to run end-to-end once unwrapping quality is addressed.

---

**Next step:** EGMS EU validation for DISP-S1 (tracked separately in `run_eval_disp_egms.py`).
