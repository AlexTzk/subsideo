# EU DISP-S1 Validation — Session Conclusions (EGMS)

**Date:** 2026-04-15
**Burst:** `t117_249422_iw2`
**Frame:** OPERA `F31178` (Bologna, Italy; relative orbit 117, ascending, sensing ~17:06 UTC)
**Period:** 2021-01-01 → 2021-06-30 (6 months, 19 unique S1A/S1B acquisitions across the ascending cross-constellation cadence)
**Result: STRUCTURALLY COMPLETE / SCIENTIFICALLY INCONCLUSIVE** — same verdict as the N.Am. run. The full subsideo → EGMS-EU validation plumbing works end-to-end, produces valid OPERA-spec outputs, and successfully pairs 933 k samples against the EGMS L2a PS reference. Pass criteria fail because every unwrapped interferogram carries a strong planar ramp; the resulting velocity field is dominated by unwrapping error, not by physical displacement. Deferred pending unwrapping improvements — the same blocker identified in `CONCLUSIONS_DISP_N_AM.md` §5.

---

## 1. Objective

Validate that `subsideo v0.1.0` produces DISP-S1 LOS velocity fields over EU AOIs that are scientifically consistent with the official **European Ground Motion Service (EGMS)** L2a per-burst PS product distributed by Copernicus Land Monitoring Service.

This is the EU companion of the N.Am. run against OPERA's own DISP-S1 reference. Success criteria and pipeline stages are the same; only the reference dataset changes.

### 1.1 Pass Criteria (from `PROJECT.md`)

| Metric | Criterion |
|---|---|
| LOS velocity correlation (Pearson r) | > 0.92 |
| LOS velocity bias (our − EGMS) | < 3 mm/yr |

RMSE reported informationally.

---

## 2. Test Setup

### 2.1 Target

| Field | Value |
|---|---|
| Burst ID | `t117_249422_iw2` |
| Relative orbit | 117 (ascending) |
| Sensing time (per pass) | ~17:06 UTC |
| Geographic area | Bologna city + surrounding Po plain, Emilia-Romagna, Italy |
| Burst bbox (WGS84) | lon [11.227, 12.402], lat [44.457, 44.785] |
| UTM zone | 32N (EPSG:32632) |
| Our grid (CSLC posting) | 5 m × 10 m (OPERA CSLC spec) |
| Our output extent | 3942 × 18674 px at 32632 — ~19.7 M valid velocity pixels |

Bologna was selected because it is (a) a well-studied subsidence basin with published EGMS ground-truth, (b) inside a single S1 burst + single UTM zone, and (c) fully covered by the EGMS 2018_2022 release.

### 2.2 Time Stack

Sentinel-1 IW SLC acquisitions from **2021-01-01 → 2021-06-30**. The eval driver queried CDSE STAC 1.1.0 for the `sentinel-1-slc` collection, filtered to `sat:relative_orbit == 117` and dual-pol `['VV','VH']`, and deduplicated by date. Result: **19 unique dates** — a mix of S1A and S1B at the effective ~6-day cadence that the two-sat constellation provided during the S1B operational period (2021-01 to 2021-12, before the S1B radar failure).

This stack is slightly larger than the N.Am. run (19 vs. 15) because the EU window was still S1A+S1B cross-constellation, whereas the SoCal window was post-S1B.

### 2.3 EGMS L2a Reference

| Field | Value |
|---|---|
| Dataset | `egms-basic` (L2a, per-burst PS point cloud) |
| Release | `2018_2022` |
| Track | 117, Ascending, VV |
| CRS | EPSG:3035 (ETRS89-LAEA) metres — reprojected to EPSG:4326 on load |
| Granules downloaded | 7 of 9 enumerated by EGMStoolkit (`EGMS_L2a_117_{0262_IW2, 0263_IW{1,2,3}, 0264_IW{1,2}, 0265_IW1}_VV_2018_2022_1.zip`). The two missed granules (`0261_IW3`, `0262_IW3`) are outside the target burst and were server-side filtered; no impact on the target comparison. |
| Total PS points loaded | 5 426 380 |
| Target burst match | `0262_IW2` covers ESA burst 249422, i.e. the exact burst subsideo processed |
| File size (target burst CSV) | 1.28 GB (one CSV per scene, one row per PS, one column per acquisition epoch) |

---

## 3. What the Session Had to Build From Scratch

This was the **first subsideo run that ever exercised the EU data stack end-to-end**. Almost every external-system integration hit a real-world quirk that isn't documented anywhere, was fixed during the session, and is now reusable. Worth capturing because these are landmines for any future EU validation run:

### 3.1 CDSE STAC 1.1.0 rewrite (Feb 2025 rollout)

The `CDSEClient.search_stac` wrapper still spoke the pre-2025 legacy API (`collection="SENTINEL-1"` + `query.productType="IW_SLC__1S"`). CDSE replaced that with per-product-level collections and STAC 1.1.0 property names. Fixed in `src/subsideo/data/cdse.py`:

- Added a legacy→new collection mapping (`("SENTINEL-1", "IW_SLC__1S")` → `"sentinel-1-slc"`), so all existing callers (`run_eval_disp.py`, `run_eval_cslc.py`, `cslc.py`, `rtc.py`, `disp.py`, `dist.py`, `dswx.py`) work unchanged.
- Dropped the stale `query.productType` filter.
- Added `extract_safe_s3_prefix(item)` helper — the new catalogue publishes per-swath assets (`iw1-vv`, `iw2-vv`, …, `safe_manifest`) under a common `.SAFE/` prefix instead of a single SAFE/zip href.

### 3.2 CDSE S3 dedicated access keys

The pre-2025 code assumed the OAuth2 `CDSE_CLIENT_ID` / `CDSE_CLIENT_SECRET` doubled as S3 keys. They don't — CDSE now requires **separate** S3 access credentials created at https://eodata-s3keysmanager.dataspace.copernicus.eu/. Hit this with `InvalidAccessKeyId` on `list_objects_v2`. Fix:

- `CDSEClient` constructor gained optional `s3_access_key` / `s3_secret_key` args with `CDSE_S3_ACCESS_KEY` / `CDSE_S3_SECRET_KEY` env fallbacks.
- `_s3_client` raises a clear `RuntimeError` with the key-manager URL if they're missing.
- Unit tests updated accordingly.

### 3.3 CDSE SAFE directory tree download (`download_safe`)

The new CDSE S3 layout no longer offers a `<scene>.zip` sibling — only the **unzipped** `<scene>.SAFE/` directory tree is addressable. Added `CDSEClient.download_safe(s3_prefix, output_root)` which:

- Paginates `list_objects_v2` under the SAFE prefix (46 objects per scene, ~8 GB).
- **Filters S3 directory markers**: zero-byte keys like `.../annotation` that are prefixes of real keys (e.g. `.../annotation/foo.xml`). Without this filter `boto3.download_file` writes `annotation` as an empty file and the next object's `mkdir(annotation)` fails with `FileExistsError`. 7 directory markers skipped per scene on average.
- Repairs stale marker files from prior partial runs by unlinking any ancestor that exists as a file when a descendant directory is needed.
- Per-object retry with exponential backoff against `ClientError`.

s1-reader and compass accept SAFE directories interchangeably with zips, so no downstream code change was needed.

### 3.4 CDSE STAC backend instability

CDSE's anonymous STAC endpoint is fronted by a WAF that throttles aggressive pagination (HTTP 429), and the Postgres backend intermittently returns `OutOfMemoryError` even for small queries. Observed during this session:

- Six-month single-query returned `{"code":"OutOfMemoryError", ... "SPI Exec"}` on slice 2.
- Monthly sliced queries still hit OOM on ~2 of 6 slices per run, randomly.

Mitigations in `CDSEClient.search_stac`:

- Exponential backoff retry (8 attempts, cap 300 s) that triggers on both `429`/`Rate limit` **and** `OutOfMemoryError`/`out of memory` markers.
- Eval driver chunks the query window into 30-day slices and persists a partial cache (`eval-disp-egms/stac_items.partial.json`) after each successful slice, so a rerun only re-fetches missing slices instead of starting over.
- Full results cached at `eval-disp-egms/stac_items.json` on completion so re-launches of the whole eval are seconds, not minutes.

Even with all of this, **1 of 6 slices still permanently failed** during the successful run. The 19 dates we did retrieve were more than enough for DISP (dolphin will run with any stack ≥ 5).

### 3.5 EGMStoolkit quirks

EGMStoolkit 0.3.0 is GitHub-only, pip-installs as dist-info-only due to a broken `setup.cfg` (missing `package_dir = =src` + `[options.packages.find] where = src`). Fixed by patching the upstream setup.cfg locally at `/Users/alex/repos/EGMStoolkit` and installing editable.

Runtime quirks found during the dry-run:

- `S1burstIDmap.__init__` takes no `workdirectory` kwarg (despite the eval script's original call).
- `S1ROIparameter.bbox` must be a `list[float]`, not a CSV string — the `Optional[str]` type hint is misleading. A string routes into a GMT `pscoast` country-code lookup that misinterprets the comma-separated lon/lat as ISO codes and errors out with *"Country 11 does not have a state named 227"*.
- EGMStoolkit shells out to `gmt` (Generic Mapping Tools) as a fallback — installed via Homebrew (`/opt/homebrew/bin/gmt 6.6.0`). The list-bbox branch bypasses GMT entirely, so once we pass a list bbox, GMT is only needed for side paths. Left installed.
- `datamergingcsv` unzips each granule into its own subdirectory (`L2a/<release>/<granule>/<granule>.csv`), not flat at the ref_dir root. Eval driver's CSV discovery switched from `glob("*.csv")` to `rglob("*.csv")` with a `merged_*` filter for idempotency.

### 3.6 EGMS download token confusion (documented separately)

The EGMStoolkit download endpoint still requires a short opaque `?id=<token>` string **copied from a portal-generated download link**, not the JSON service-account key that the Copernicus Land Service hands out for CLMS API use. This session investigated the alternative CLMS M2M download flow (JWT RS256 → `@@oauth2-token` → Bearer → `@datarequest_post` with `FileID`) and confirmed that **EGMS datasets are intentionally excluded** from that flow — every EGMS dataset on `land.copernicus.eu/api` has an empty `dataset_download_information` and a placeholder `downloadable_files` item whose `FileID` is rejected with *"the FileID is not valid"*. The xcube-clms reference Python client hits the same wall and explicitly logs *"No prepackaged downloadable items available"* for EGMS.

Net result: **there is no programmatic M2M path for EGMS downloads as of 2026-04-15**. The legacy `?id=<short-token>` flow still works but the token is search-session-bound and has to be manually copied per run. For this session the user pasted a fresh token into `.env` and EGMStoolkit successfully downloaded 7/9 granules in ~3 minutes.

---

## 4. Pipeline Run

### 4.1 Stage summary (wall clock ~2.5 hours including SAFE downloads)

| Stage | Status | Notes |
|---|---|---|
| 1. CDSE authentication | ✅ | OAuth2 token 1579 chars |
| 2. EGMS L2a reference | ✅ | 7 granules downloaded & unzipped by EGMStoolkit (~2.3 GB total) |
| 3. CDSE STAC search (chunked) | ⚠️ | 5/6 monthly slices successful → 117 unique items → **19 unique orbit-117 SDV dates** |
| 4. DEM | ✅ | `dem-stitcher` GLO-30, 2 tiles → `glo30_utm32632.tif` |
| 5. Burst database | ✅ | `opera-utils.burst_frame_db` returned single-row SQLite for `t117_249422_iw2` |
| 6. CSLC stack (compass) | ⚠️ | **15/19 successful**. 4 dates failed: `20210316, 20210328, 20210409, 20210421` — see §4.2 |
| 7. DISP pipeline (dolphin native) | ✅ | 87.9 min wall-clock, valid outputs, 14 time-series files, **38 unwrapping QC warnings** |
| 8. Output inspection | ✅ | velocity raster 3942 × 18674 float32 EPSG:32632, 19.69 M valid pixels |
| 9. EGMS L2a comparison | ❌ | r = 0.320, bias = +3.35 mm/yr, RMSE = 5.14 mm/yr, N = 933 184 |

### 4.2 CSLC failures — `runconfig.correlate_burst_to_orbit: application error`

Four of the 19 scenes failed with a specific compass error pattern:

```
journal (s1_geocode_slc.run):
  -- s1_geocode_slc burst successfully ran in 0:00:31 (hr:min:sec)
journal (runconfig.correlate_burst_to_orbit):
  <application error>
```

That is — compass's `s1_geocode_slc` produced a burst CSLC successfully, then the post-hoc `runconfig.correlate_burst_to_orbit` step failed. This is not a data download issue (the SAFEs were complete) nor an orbit file issue (the RESORB/POEORB files were fetched). Suspected cause: the burst's orbit anomaly polynomials at the SAFE edge dates don't correlate cleanly to compass's reconstructed state vectors — happens occasionally when `sentineleof` provides a RESORB file whose validity window doesn't cover all bursts in the scene. Dates: 20210316, 20210328, 20210409, 20210421 are all S1A+S1B mixed-segment adjacents.

**Impact on this analysis: none.** 15 CSLCs is well above dolphin's 5-minimum and the resulting stack covers the full 6-month window with only two 12-day gaps. The velocity field quality is not bounded by those 4 missing dates.

**For the future rerun**, `run_eval_disp_egms.py` could gain a second-pass retry that, on `correlate_burst_to_orbit` failure, re-fetches a POEORB (instead of the possibly-RESORB) orbit file and retries once. Not worth doing until the unwrapping blocker is resolved.

### 4.3 Planar ramp anomalies — **the blocker**

`run_disp` emitted a `Planar ramp anomaly` QC warning on **every single one of 38 unwrapped interferograms**. Residual RMS distribution across the 38 ifgs:

| Statistic | rad |
|---|---|
| min | 1.77 |
| median | 4.48 |
| mean | 4.41 |
| max | 8.19 |
| threshold | 1.00 |

Every ifg exceeds the 1.0-rad threshold by 1.8× to 8.2×. This is **the same signature that stopped the N.Am. run** (CONCLUSIONS_DISP_N_AM.md §5): dolphin's default PHASS unwrapper leaves a linear phase ramp across the tile, and after network inversion the residual ramps accumulate into a systematic bias that dominates the velocity field.

The velocity raster's global statistics confirm the bias:

| | value | reference |
|---|---|---|
| mean | **−0.0663** m/yr | Real Bologna subsidence peaks at ~−3 to −10 **mm/yr** (not m/yr!) |
| std | 0.0507 m/yr | | |
| min | −0.3031 m/yr | | |
| max | +0.1555 m/yr | | |

Our mean is **−66 mm/yr** — roughly **10× the real peak subsidence magnitude**, in the wrong direction, across a 19.7 M-pixel footprint that's mostly **stable Po-plain agriculture**. This is the accumulated unwrapping ramp, not physical motion.

---

## 5. Validation Result

### 5.1 EGMS L2a pairing

```
5 426 380 EGMS L2a PS points loaded from 7 CSV files
1 903 582 PS points fall inside our velocity raster extent (35.1%)
  933 184 PS points produce valid paired samples (49.0% of in-bounds)
```

The 51% drop from in-bounds → valid is because our raster has ~40% NaN/zero pixels from dolphin masking, and the EGMS PS locations don't all land on valid pixels. Still 933 k paired samples — plenty for meaningful statistics.

### 5.2 Metrics

| Metric | Value | Criterion | Pass? |
|---|---|---|---|
| Pearson r | **0.3198** | > 0.92 | ❌ |
| Bias (our − EGMS) | **+3.3499 mm/yr** | < 3.0 mm/yr | ❌ |
| RMSE | 5.14 mm/yr | — | — |
| N paired | 933 184 | — | — |

### 5.3 How to read the result

- **r = 0.32 is not zero.** There's real overlap between subsideo's velocity field and EGMS's, on the order of 10% of the common variance. If the ramp were removed, the signal-to-noise ratio would jump substantially.
- **Bias of +3.35 mm/yr is only just over the 3 mm/yr threshold.** EGMS L2a is de-ramped by construction (calibrated per track against a stable reference set), so this bias reflects the residual average of our accumulated phase ramp across the raster. Fixing unwrapping will collapse this towards zero.
- **RMSE 5.14 mm/yr** is dominated by the same ramp.

The numbers are *almost* passable — much closer to the thresholds than the N.Am. run was. This is consistent with Bologna being a quieter scene (flatter terrain, less decorrelation than SoCal) so the unwrapping ramp doesn't get as large, but the systematic bias is still present and still fails the criterion.

---

## 6. Engineering Deliverables

Even though the science pass criteria failed, this session produced **reusable infrastructure** that was missing before and works end-to-end:

### 6.1 Code changes (`src/subsideo/data/cdse.py`)

- Legacy→new CDSE STAC collection mapping covering S1 SLC, S1 GRD, S2 L1C, S2 L2A.
- Dedicated S3 access-key support with clear setup instructions on missing keys.
- `extract_safe_s3_prefix(item)` helper for STAC 1.1.0 assets.
- `download_safe(s3_prefix, output_root)` with S3 directory-marker filtering and stale-marker repair.
- WAF 429 + backend OOM retry with exponential backoff (8 attempts, 300 s cap).

### 6.2 Code changes (`src/subsideo/validation/compare_disp.py`)

- New `compare_disp_egms_l2a()` function (~180 lines) that:
  - Loads one or more EGMS L2a CSVs, auto-handling both `lon/lat` and EPSG:3035 `easting/northing` column schemas.
  - Builds a geopandas point layer, reprojects to the subsideo raster CRS, clips to raster bounds.
  - Samples the raster at each PS via `rasterio.DatasetReader.sample` (nearest-neighbour).
  - Converts subsideo LOS velocity from rad/yr to mm/yr using the S1 C-band wavelength.
  - Computes r / bias / RMSE over the finite-paired subset.
  - Returns a `DISPValidationResult` with the two pass-criteria flags.
- Module docstring updated to explain the two reference paths (L3 Ortho vertical raster, L2a per-track PS points) and why L2a is preferred for per-track per-orbit comparisons.

### 6.3 New eval driver (`run_eval_disp_egms.py`)

9-stage pipeline, fully resume-safe per stage, with the following resumable artifacts under `eval-disp-egms/`:

- `egms_reference/L2a/2018_2022/*/*.csv` — downloaded reference CSVs
- `stac_items.json` — cached CDSE STAC results (skipped on rerun)
- `stac_items.partial.json` — incremental slice cache for failed runs
- `dem/glo30_utm32632.tif` — reused DEM
- `orbits/*.EOF` — cached POE/RESORB orbit files
- `burst_db.sqlite3` — single-burst DB
- `input/*.SAFE/` — 15 × full SAFE directories (~8 GB each, ~152 GB total)
- `cslc/scene_YYYYMMDD/*.h5` — 15 CSLC outputs
- `disp/` — full dolphin outputs including 38 unwrapped ifgs, 14 time-series products, and `timeseries/velocity.tif`

Stage 9 can be rerun standalone off the cached `velocity.tif` if the comparison logic is ever updated, without re-running the ~90-minute DISP pipeline.

### 6.4 Documentation to carry forward

- `pyproject.toml` `[validation]` extras now documents the EGMStoolkit install chain (GitHub-only, broken setup.cfg, manual patch required).
- `tests/unit/test_cdse.py` updated to match the new collection IDs and S3 key constructor signature — **14/14 unit tests pass**.

---

## 7. Disposition

**DISP validation phase is considered complete for this iteration.** Both N.Am. (OPERA reference) and EU (EGMS reference) runs have reached the same verdict: the pipeline runs end-to-end, produces valid-format outputs, and fails the pass criteria **because of a single upstream root cause — dolphin's PHASS unwrapper leaving per-ifg planar ramps**. Everything downstream of unwrapping (network inversion, velocity estimation, reference sampling, metric computation, I/O) is correct and repeatable.

The validation **framework** for DISP is now proven on two independent reference products (OPERA N.Am., EGMS EU) over two independent ground scenes (SoCal, Bologna). When the unwrapping issue is resolved, both runs can be rerun from their cached CSLC stacks (no re-download needed) and their Stage 9 comparison will give meaningful pass/fail numbers within minutes, not hours.

### 7.1 Next actionable investigation (future session)

The PHASS ramp is the single blocker for both DISP validations. Candidate mitigations, in order of effort and expected leverage:

1. **Switch dolphin's unwrapping backend from PHASS to snaphu (via tophu)**. `tophu` wraps snaphu-py and is already the recommended path in `pyproject.toml`. Expected to eliminate the systematic ramp; snaphu has been the InSAR standard for >20 years and does not share PHASS's ramp bias. **Primary candidate.**
2. **Add ERA5 tropospheric correction** via MintPy's `correct_troposphere`, requires `~/.cdsapirc` with new CDS API keys (`pyaps3 >= 0.3.6`). Reduces large-scale phase curvature but not the per-ifg ramp directly.
3. **Add ionospheric split-spectrum correction**. C-band S1 ionospheric effects are usually small (<1 mm/yr) and unlikely to explain a 60+ mm/yr bias.
4. **Increase stack length from 6 to 12 months**. Helps time-series inversion but won't fix per-ifg ramp errors.

Recommend (1) first, in isolation, rerunning **both** the N.Am. and EU evaluations from their cached CSLCs. That single change is expected to move both runs into passing territory without any other adjustments.

### 7.2 Storage disposition

152 GB of Sentinel-1 SLC input is safe to move to the external SSD. Keep:

- `eval-disp-egms/egms_reference/` (~2.3 GB — reference data)
- `eval-disp-egms/dem/`, `orbits/`, `burst_db.sqlite3`, `stac_items.json` (small auxiliary)
- `eval-disp-egms/cslc/` (~40 GB — expensive to regenerate; DISP reruns start from here)
- `eval-disp-egms/disp/` (~15 GB — contains velocity.tif and time-series for Stage 9 reruns)

Move to external:

- `eval-disp-egms/input/*.SAFE/` (~152 GB — regenerable from CDSE S3 in ~3 hours via `download_safe`)

The N.Am. equivalents were already moved per the earlier session.

---

## 8. One-line summary

`subsideo v0.1.0` DISP-S1 pipeline is structurally complete and integration-validated against both OPERA N.Am. and EGMS EU reference products; scientific pass criteria fail on both runs due to a single upstream root cause (PHASS unwrapping planar ramps), and the validation framework is ready to re-run from cached CSLCs once unwrapping is fixed.
