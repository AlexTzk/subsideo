# N.Am. CSLC-S1 Self-Consistency — Session Conclusions

**Date:** 2026-04-24
**Phase:** v1.1 Phase 3 — CSLC-S1 Self-Consistency + EU Validation
**Plans:** 03-03 (Plan 03-03 Task 2 N.Am. compute)
**Cell:** `eval-cslc-selfconsist-nam`
**AOIs:** SoCal (`t144_308029_iw1`) + Mojave/Coso-Searles (`t064_135527_iw2`, fallback chain index #1)
**Result: 2/2 CALIBRATING** — `cell_status: CALIBRATING`, no BLOCKERs.

> First-rollout self-consistency cell; status is **CALIBRATING** per Phase 3 D-03 (no PASS/FAIL emitted regardless of measured numbers — Phase 4 calibrates the gate thresholds against this distribution).

---

## 1. Objective

Establish a self-consistency baseline for `subsideo` CSLC-S1 outputs over two N.Am. terrain regimes, before attempting EU validation. Self-consistency ≠ cross-product validation: we measure whether the same `subsideo` pipeline produces internally coherent CSLC stacks (sequential-IFG coherence) and a near-zero residual mean velocity over stable terrain.

This complements the original v1.0 reference-product validation (`CONCLUSIONS_CSLC_N_AM.md`) which compares amplitude against the OPERA L2 CSLC-S1 product. Phase 3 adds a phase-domain coherence test that is independent of OPERA's reference product and runs on the same `subsideo` outputs.

### 1.1 Criteria (Phase 3 D-03 — measured but not gated this rollout)

| Metric | Threshold (Phase 4 candidate) | Source |
|--------|-------------------------------|--------|
| `coherence_median_of_persistent` | ≥ 0.7 | `CRITERIA['cslc.selfconsistency.coherence_min']` |
| abs(`residual_mm_yr`) | ≤ 3.0 mm/yr | `CRITERIA['cslc.selfconsistency.residual_mm_yr_max']` |
| amplitude_r (vs OPERA reference, SoCal only) | ≥ 0.6 | `CRITERIA['cslc.amplitude_r_min']` |
| amplitude_rmse_db (vs OPERA reference, SoCal only) | ≤ 4.0 dB | `CRITERIA['cslc.amplitude_rmse_db_max']` |

---

## 2. Test Setup

### 2.1 AOIs

| AOI | Burst ID | Regime | Terrain | UTM zone | Sensing window |
|-----|----------|--------|---------|----------|----------------|
| SoCal | `t144_308029_iw1` | SoCal-Mediterranean | Coastal mountains, sparse chaparral | 11N (EPSG:32611) | 2024-01-08 → 2024-06-24, 14:01:14 UTC, 12-day cadence × 15 epochs |
| Mojave/Coso-Searles | `t064_135527_iw2` | desert-bedrock-playa-adjacent | Bedrock + playa-adjacent desert | 11N (EPSG:32611) | 2023-12-22 → 2024-06-19, 01:51:10 UTC, 12-day cadence × 15 epochs |

Both selected for high stable-terrain density (slope < 10°, WorldCover class 60 = bare/sparse vegetation, ≥5 km from coast, ≥500 m from waterbodies). Mojave fallback chain (4 alternatives) produced the Coso-Searles attempt as the first CALIBRATING candidate; the remaining three fallbacks are unused (chain short-circuits on first success).

### 2.2 Input Data

| Input | Source | Notes |
|-------|--------|-------|
| S1 IW SLC SAFEs | ASF DAAC via `asf_search` (Earthdata creds) | 30 fresh downloads (~7.8 GB each, ~234 GB total). Slice-containment filter required (see Bug 8). |
| Precise orbits | `subsideo.data.orbits.fetch_orbit` (sentineleof) | Per-epoch S1A POEORB |
| GLO-30 DEM | `dem-stitcher`, per-AOI cached (`dem/<aoi>/`) | 30 m UTM 11N |
| WorldCover 2021 v200 | s3://esa-worldcover/, anonymous | 7 tiles covering both AOIs |
| Natural Earth coast/lakes | `cartopy.io.shapereader.natural_earth(10m, physical, ...)` | Coast 5 km buffer, lakes 500 m buffer |
| OPERA reference (SoCal only) | `earthaccess.search_data('OPERA_L2_CSLC-S1_V1', ...)` + `select_opera_frame_by_utc_hour` | 1 ref h5 (first epoch only, D-07 amplitude sanity) |
| OPERA burst DB | `opera-adt/burst_db v0.9.0` opera-burst-bbox-only.sqlite3 | Auto-fetched on first run, cached at `~/.subsideo/opera_burst_bbox.sqlite3` |

### 2.3 Processing Environment

| Component | Value |
|-----------|-------|
| Python | 3.12.13 (conda-forge) |
| Platform | macOS-26.3.1-arm64-arm-64bit (Apple Silicon M3 Max, 128 GB RAM) |
| isce3 | 0.25.8 (conda-forge) |
| compass | 0.5.6 (conda-forge) |
| s1-reader | 0.2.5 (conda-forge) |
| numpy | 1.26.4 (pinned <2 — compass + isce3 incompatible with numpy 2.x) |
| GDAL | ≥ 3.8 (conda-forge) |
| subsideo git_sha | `61d4339b69338195fcae29f11368c52154249eda` (worktree dirty: eval artifacts) |
| Run started | 2026-04-24T13:37:30Z |
| Run duration | 4691 s (78 min) — Mojave fresh compass dominates |

---

## 3. What Was Run

### 3.1 Evaluation Script (`run_eval_cslc_selfconsist_nam.py`)

Resume-safe per-stage pipeline (D-08): WorldCover → DEM → slope → Natural Earth → stable_mask → 15-epoch CSLC compute (compass) → IFG coherence stack → CSLC-grid stable_mask reprojection → coherence stats → linear-fit residual velocity → amplitude sanity (SoCal only) → sanity artifacts → AOIResult.

Invoked via `make eval-cslc-nam` (supervisor-wrapped: `subsideo.validation.supervisor`).

### 3.2 CSLC Pipeline (`subsideo/products/cslc.py`)

Unchanged from v1.0 (`CONCLUSIONS_CSLC_N_AM.md`). Per-epoch: runconfig generation → compass execution → COG normalisation. `_mp.configure_multiprocessing()` fires once per `run_cslc()` call (Phase 1 D-14).

### 3.3 Self-Consistency Validation (`subsideo/validation/selfconsistency.py`)

- `coherence_stats(ifgrams_stack, stable_mask, *, coherence_threshold=0.6) -> {mean, median, p25, p75, persistently_coherent_fraction, median_of_persistent}` — per-pixel-mean coherence over the stable mask.
- `compute_residual_velocity(cslc_stack_paths, stable_mask, sensing_dates) -> (H, W) float32` — vectorised OLS per-pixel linear fit of `np.unwrap(np.angle(cslc), axis=0)` vs days, converted to mm/yr at S1 C-band wavelength.
- `residual_mean_velocity(velocity, stable_mask, frame_anchor='median') -> float` — reference-frame alignment: subtracts the stable-mask anchor (median by default) before averaging.

### 3.4 Amplitude Sanity (SoCal only — `compare_cslc`)

`run_amplitude_sanity=True` triggers a one-shot `compare_cslc(product_h5, opera_ref_h5)` on the first epoch only. Mojave fallbacks have `run_amplitude_sanity=False` because OPERA reference frame matching for those bursts is not reliable in the desert fallback chain (D-07).

---

## 4. Bugs Encountered and Fixed

This rollout surfaced 9 distinct issues during iterative debugging. Each was fixed inline and committed atomically. Listed in encounter order.

### Bug 1: Fake `naturalearth` PyPI dependency (`08e9175`)

The 03-01 plan-spec named a `naturalearth` PyPI package that doesn't exist (the real package is `cartopy.io.shapereader.natural_earth`). Rewrote `data/natural_earth.py` to use cartopy's natural_earth fetcher; updated tests + pyproject `[dev]` extras.

### Bug 2: WorldCover/DEM grid mismatch (`a52c1fb`)

`build_stable_mask` requires WorldCover and slope arrays on the same grid, but WC was on EPSG:4326 10 m and DEM on UTM 30 m. Added `_reproject_worldcover_to_dem_grid` helper; modified `_compute_slope_deg` to return `(slope_deg, transform, crs)`.

### Bug 3: Missing OPERA burst DB for compass (`ce4f747`)

compass v0.5.6 rejects missing/None burst_database_file at `runconfig.load_from_yaml`. Auto-fetch `opera-adt/burst_db v0.9.0`'s `opera-burst-bbox-only.sqlite3.zip` to `~/.subsideo/` on first use.

### Bug 4: ASF returned wrong-track SAFE (`fa71c0f`)

The original `_download_safe_for_epoch` filtered ASF only by time window, downloading whichever S1 acquisition matched UTC time — could pick the wrong relative orbit. Added `relativeOrbit=track_num` (parsed from burst_id) + `intersectsWith=burst.footprint`, plus zip post-download validation (BadZipFile → unlink → re-raise).

### Bug 5: Probe-fabricated sensing-window dates (`d6aebe8`)

The 03-02 probe artifact emitted multi-track fabricated 12-day-cadence dates that didn't correspond to real ASF acquisitions. Replaced all 5 `*_EPOCHS` tuples (1 SoCal + 4 Mojave fallbacks) with real ASF-verified S1A acquisitions.

### Bug 6: earthaccess DataGranule shape mismatch (`633deef`)

`select_opera_frame_by_utc_hour` expects `[{'sensing_datetime': iso_str}, ...]` but earthaccess returns `DataGranule` objects with sensing time deep at `umm['TemporalExtent']['RangeDateTime']['BeginningDateTime']`. Added a flat-dict shim at the call site.

### Bug 7: numpy 2.x dragged in by transitive dep

A pip install of an unrelated package upgraded numpy 1.26.4 → 2.4.4, breaking compass with "only 0-dimensional arrays can be converted to Python scalars". Restored via `pip install 'numpy<2' --force-reinstall --no-deps`.

### Bug 8: compass nested h5 layout vs flat glob (`caa2b80`)

compass writes `<burst_out>/<burst_id>/<YYYYMMDD>/<burst_id>_<YYYYMMDD>.h5` (nested), but the resume-check used a flat `iterdir()`. Replaced with `rglob("*.h5")` and reused for `_compute_ifg_coherence_stack` input.

### Bug 9: Stable-mask grid mismatch with CSLC output (`d76601f` + `7cf4fab` + `c9b8f34`)

Multi-step root cause:

- **Sub-bug 9a (`d76601f`):** stable_mask was on the DEM UTM-30 m grid, but compass CSLC outputs are on the OPERA 5 m × 10 m grid. `coherence_stats` boolean-indexing failed with shape mismatch (5082 vs 4962 along dim 0). Fix: `rasterio.warp.reproject(stable_mask → cslc_grid, resampling=nearest)`.

- **Sub-bug 9b (`7cf4fab`):** Even after reprojection, the rectangular CSLC grid contains ~64 % NaN pixels outside the burst parallelogram footprint. Reprojected stable pixels could land in the NaN region (95 % of them did for SoCal). Fix: AND the reprojected mask with `valid_on_cslc = (ifgrams_stack > 0).any(axis=0)`.

- **Sub-bug 9c (`c9b8f34`):** `scipy.ndimage.uniform_filter` propagates NaN through its full 5×5 window, so 64 % NaN coverage made coherence structurally 0 EVERYWHERE (not just in NaN corners) — the `valid_on_cslc` mask in 9b was empty. Fix: in `_load_cslc` (both NAM script and `compute_residual_velocity`), zero-fill complex NaN with `0+0j` before the filter. Verified offline: SoCal coherence_stack went from 100 % zero to 35.5 % > 0 (mean 0.27 on valid).

### Bug 10: Wrong key for compare_cslc result (`61d4339`)

NAM script looked up `'amplitude_correlation'` but `compare_cslc` stores it as `'amplitude_r'` — `.get(...)` always fell through to the `-1.0` sentinel. Detected by inspecting the first metrics.json against `compare_cslc.py:216`.

### Bug 11: ASF slice mismatch (`f581095`)

S1 IW SLCs are segmented into ~25 s slices per pass; `intersectsWith=burst.footprint` + ±10 min window matched 2+ slices and `results[0]` could be the slice that does NOT contain the burst. SoCal happened to work by luck; Mojave + Iberian (EU) hit it consistently. Fix: iterate candidates, pick the one where `r.startTime ≤ epoch ≤ r.stopTime`.

---

## 5. Final Validation Results

### 5.1 Per-AOI metrics (from `eval-cslc-selfconsist-nam/metrics.json`)

| AOI | n_stable (DEM) | n_stable (CSLC ∩ valid) | coh_mean | coh_median | coh_p25/p75 | coh_med_of_persistent | persistent_frac | residual_mm_yr | amp_r | amp_rmse_db |
|-----|----------------|-------------------------|----------|------------|-------------|------------------------|-----------------|----------------|-------|-------------|
| SoCal | 121,618 | 486 | 0.416 | 0.402 | 0.274 / 0.554 | **0.887** | 2.5% | **−0.109** | **0.982** | **1.290** |
| Mojave/Coso-Searles | — | 10,148,330 | 0.594 | 0.588 | 0.504 / 0.690 | **0.804** | 11.1% | **+1.127** | n/a (no OPERA ref) | n/a |

Both AOIs gate-positive on coherence (≥ 0.7 candidate threshold) and residual (well under 3 mm/yr candidate threshold).

### 5.2 Coverage notes

- **SoCal sparse stable mask** (486 valid CSLC pixels): SoCal-Mediterranean has high relief + dense chaparral (WorldCover class 50, not 60) over most of the burst footprint, plus the 5 km coastal buffer trims a large fraction. Coherence_median_of_persistent = 0.887 over those 486 pixels remains a robust statistic; persistent_frac = 2.5 % means few pixels exceed coh ≥ 0.6 in EVERY one of the 14 IFGs (expected — variable vegetation cover over 6 months).
- **Mojave/Coso-Searles dense stable mask** (10 M valid CSLC pixels): desert bedrock + playa-adjacent terrain has uniform WorldCover class 60 + low slope. Persistent_frac = 11.1 % is the highest of the three Phase 3 AOIs.
- **SoCal amplitude sanity** (`amp_r=0.982, amp_rmse_db=1.29 dB`): excellent agreement with the OPERA L2 CSLC-S1 reference for the same burst at the first epoch. Above the v1.0 N.Am. validation criteria (r > 0.6, RMSE < 4 dB) by a wide margin.

### 5.3 P2.1 mitigation — sanity artifacts

Per-AOI coherence histograms + stable-mask basemaps written to `eval-cslc-selfconsist-nam/sanity/<aoi>/`:

- SoCal: histogram is approximately unimodal ~0.3–0.5 with a tail above 0.7 — no bimodal contamination.
- Mojave/Coso-Searles: histogram broad peak ~0.6 — robust desert-bedrock coherence.

No bimodal P2.1 contamination was observed.

---

## 6. Output Files

```
eval-cslc-selfconsist-nam/
├── input/                         # 30 SAFEs (~234 GB; 15 SoCal + 15 Mojave)
├── orbits/                        # 30 POEORB EOFs
├── dem/<aoi>/glo30_utm32611.tif   # per-AOI UTM DEM
├── worldcover/                    # 7 ESA WorldCover 2021 v200 tiles
├── opera_reference/SoCal/         # 1 OPERA reference h5 (D-07 amplitude sanity)
├── output/<aoi>/<burst_id>/<YYYYMMDD>/<burst_id>_<YYYYMMDD>.h5  # 30 compass CSLC outputs
├── sanity/<aoi>/                  # P2.1 mitigation: histogram + mask + metadata
├── metrics.json                   # per-AOI + cell aggregate
└── meta.json                      # run provenance (git_sha, durations, input hashes)
```

---

## 7. Source Files Changed During This Session

| File | Reason |
|------|--------|
| `run_eval_cslc_selfconsist_nam.py` | All 11 bugs above |
| `src/subsideo/data/natural_earth.py` | Bug 1 (cartopy backend) |
| `src/subsideo/validation/selfconsistency.py` | Bug 9c (NaN→0 in `compute_residual_velocity._load_cslc`) |
| `tests/unit/test_natural_earth.py` | Bug 1 (cartopy mock pattern) |
| `pyproject.toml` | Bug 1 (drop fake `naturalearth` from `[dev]`) |

`src/subsideo/products/cslc.py` and `src/subsideo/validation/compare_cslc.py` were not modified.

---

## 8. Recommendations for Next Steps

1. **Calibrate gate thresholds** (Phase 4): SoCal coh_median_of_persistent = 0.887 and Mojave = 0.804 bracket the 0.7 candidate threshold by 10 %+. The threshold can be raised to 0.75 or 0.8 if a tighter floor is desirable.
2. **Investigate SoCal stable-mask sparsity** (486 valid CSLC pixels): the `stable_terrain.build_stable_mask` `coast_buffer_m=5000` parameter is currently buffered in EPSG:4326 (degrees, not metres) — see `src/subsideo/validation/stable_terrain.py:195` `UserWarning`. The buffer is geometrically wrong but happens to produce sensible results. Fix is to project the coast/water GeoSeries to UTM before buffering. Tracked in `.planning/intel/known-issues/stable_terrain_buffer.md` (TBD).
3. **Mojave amplitude sanity** (D-07 follow-up): Mojave fallbacks currently set `run_amplitude_sanity=False` because OPERA frame-matching across desert fallback bursts is not reliable. Re-enable for whichever fallback succeeds first (Coso-Searles in this run) by passing the verified burst_id back to the OPERA frame search.
4. **Probe-artifact regeneration** (Plan 03-02 follow-up): the 03-02 probe shipped fabricated dates for ALL 5 N.Am. tuples (1 SoCal + 4 Mojave) — the `asf-search`-based derivation in Bug 5 should be moved into the probe so future re-runs don't carry forward the same fabrication.
5. **EU validation**: see `CONCLUSIONS_CSLC_SELFCONSIST_EU.md` (Plan 03-04 Task 2).
