# EU CSLC-S1 Self-Consistency — Session Conclusions

**Date:** 2026-04-24
**Phase:** v1.1 Phase 3 — CSLC-S1 Self-Consistency + EU Validation
**Plans:** 03-04 (Plan 03-04 Task 2 EU compute, minimum-viable scope)
**Cell:** `eval-cslc-selfconsist-eu`
**AOI:** Iberian/Meseta-North (`t103_219329_iw1`)
**Result: 1/1 CALIBRATING** — `cell_status: CALIBRATING`, no BLOCKERs.

> First-rollout self-consistency cell; status is **CALIBRATING** per Phase 3 D-03. Iberian/Alentejo and Iberian/Massif Central fallbacks were planned but the 03-02 probe shipped invalid burst IDs for both — those AOIs are deferred to a follow-up (see §5.2).

---

## 1. Objective

Verify that the N.Am. self-consistency pipeline (`CONCLUSIONS_CSLC_SELFCONSIST_NAM.md`) reproduces over EU AOIs without code changes other than the EU-specific data-access path (CDSE STAC originally; ASF in this rollout — see §4 Bug 4) and the optional EGMS L2a third-number step.

This is a self-consistency cell (same `subsideo` outputs, internal coherence + residual stable-set velocity), NOT a cross-product validation against OPERA, because OPERA L2 CSLC-S1 V1 is a N.Am.-only product (no EU coverage). The EGMS L2a stable-PS residual was planned as a third independent reference but is deferred (see §5.1).

### 1.1 Criteria (Phase 3 D-03 — measured but not gated this rollout)

Identical to N.Am. (`CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` §1.1):

| Metric | Threshold (Phase 4 candidate) | Source |
|--------|-------------------------------|--------|
| `coherence_median_of_persistent` | ≥ 0.7 | `CRITERIA['cslc.selfconsistency.coherence_min']` |
| abs(`residual_mm_yr`) | ≤ 3.0 mm/yr | `CRITERIA['cslc.selfconsistency.residual_mm_yr_max']` |
| `egms_l2a_stable_ps_residual_mm_yr` | ≤ 2.0 mm/yr (CSLC-05 third number) | not run this rollout |

OPERA reference amplitude sanity (`cslc.amplitude_r_min`, `cslc.amplitude_rmse_db_max`) is not applicable for EU AOIs — OPERA CSLC-S1 V1 catalog has no EU bursts. The EU script logs a warning and skips the step.

---

## 2. Test Setup

### 2.1 AOI

| Field | Value |
|-------|-------|
| Burst ID | `t103_219329_iw1` |
| Regime | iberian-meseta-sparse-vegetation |
| Geographic area | Iberian Meseta-North (Castilla y León / Castilla–La Mancha) |
| WGS84 bbox | (−3.303°E, 40.566°N, −2.123°E, 40.998°N) |
| UTM zone | 30N (EPSG:32630), bbox (474360, 4490640, 573780, 4538910) |
| Sensing window | 2024-01-05 → 2024-06-21, 18:03:20 UTC, 12-day cadence × 15 epochs (S1A POEORB, descending track 103) |

Selected for high stable-terrain density (Iberian steppe / fallow agriculture: WorldCover class 60 dominant, low slope, far from coast). Phase 2 RTC-EU validation also used this burst — verified Iberian footprint.

### 2.2 Input Data

| Input | Source | Notes |
|-------|--------|-------|
| S1 IW SLC SAFEs | ASF DAAC via `asf_search` (Earthdata creds) | 15 fresh downloads (~7.8 GB each, ~117 GB total). Slice-containment filter required (Bug 7). |
| Precise orbits | `subsideo.data.orbits.fetch_orbit` (sentineleof) | Per-epoch S1A POEORB |
| GLO-30 DEM | `dem-stitcher`, cached (`dem/Iberian/`) | 30 m UTM 30N |
| WorldCover 2021 v200 | s3://esa-worldcover/, anonymous | 4 tiles covering Iberian Meseta |
| Natural Earth coast/lakes | `cartopy.io.shapereader.natural_earth(10m, physical, ...)` | Coast 5 km buffer, lakes 500 m buffer |
| OPERA reference | n/a — V1 catalog is N.Am.-only | Amplitude sanity skipped with warning |
| EGMS L2a | `EGMStoolkit` GitHub | **Not run** — upstream packaging + API mismatch (see §5.1) |
| OPERA burst DB | `opera-adt/burst_db v0.9.0` | Reuses NAM-fetched cache at `~/.subsideo/opera_burst_bbox.sqlite3` (covers global S1, including EU) |

### 2.3 Processing Environment

| Component | Value |
|-----------|-------|
| Python | 3.12.13 (conda-forge) |
| Platform | macOS-26.3.1-arm64-arm-64bit (Apple Silicon M3 Max, 128 GB RAM) |
| isce3 | 0.25.8 (conda-forge) |
| compass | 0.5.6 (conda-forge) |
| s1-reader | 0.2.5 (conda-forge) |
| numpy | 1.26.4 (pinned <2) |
| GDAL | ≥ 3.8 (conda-forge) |
| subsideo git_sha | `f581095bfcc2aa16cca214ba9bbf586723b3bce5` (worktree dirty: eval artifacts) |
| Run started | 2026-04-24T16:20:07Z |
| Run duration | 4386 s (73 min) — fresh ASF download dominates |

---

## 3. What Was Run

### 3.1 Evaluation Script (`run_eval_cslc_selfconsist_eu.py`)

Same shape as `run_eval_cslc_selfconsist_nam.py` (Plan 03-03). The EU-specific deltas are:

- ASF-based `_download_safe_for_epoch` (was CDSE STAC originally — see Bug 4)
- `EU_BURST_DB_PATH = ~/.subsideo/opera_burst_bbox.sqlite3` (reuses NAM auto-fetched DB)
- EGMS L2a third-number step at the tail end (deferred this rollout — Bug 8)

Invoked via `make eval-cslc-eu` (supervisor-wrapped).

### 3.2 CSLC Pipeline (`subsideo/products/cslc.py`)

Unchanged.

### 3.3 Self-Consistency Validation (`subsideo/validation/selfconsistency.py`)

Identical to NAM cell. The NaN→0 fix (commit `c9b8f34`) is required for both N.Am. and EU because the CSLC rectangular grid is parallelogram-footprint with NaN corners regardless of region.

---

## 4. Bugs Encountered and Fixed

This rollout inherited all 11 fixes from the N.Am. session (`CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` §4) and surfaced 8 EU-specific issues. Listed in encounter order (after the N.Am. fixes had landed).

### Bug 1: Stale `subsideo.products._mp` import (`f02b121`)

`subsideo._mp` lives at the package root, not under `subsideo.products`. The EU script's import `from subsideo.products import _mp` fails at script load. Removed the import and the explicit `_mp.configure_multiprocessing()` call — `run_cslc()` does this internally at its top (Phase 1 D-14).

### Bug 2: Probe-fabricated EU sensing windows + 2/3 burst IDs misbound (`2b59ad6`)

The 03-02 probe shipped invalid EU AOI configs:

- `t103_219329_iw1` (Meseta-North primary): burst ID is correct (Iberian Meseta, EPSG 32630) but the `IBERIAN_PRIMARY_EPOCHS` tuple mixed three pass times (06:18 / 06:26 / 18:11 UTC) — a single S1A burst has a single consistent UTC pass.
- `t008_016940_iw2` (supposed Alentejo): burst bbox places this in **New Zealand** (EPSG 32760).
- `t131_279647_iw2` (supposed Massif Central): burst bbox places this in **Arctic Norway** (~69.7°N, EPSG 32633).

The fallback_chain logic processed the broken fallbacks first (both FAILed instantly with `WorldCover bbox` errors over wrong continents) and never tried the valid Meseta-North primary.

**Fix:** Replaced `IBERIAN_PRIMARY_EPOCHS` with 15 real ASF-verified S1A acquisitions (track 103 descending, 18:03:20 UTC, 2024-01-05 → 2024-06-21). Set `fallback_chain=()` so IberianAOI runs as a leaf with the validated primary burst. Alentejo + Massif Central re-derivation is deferred (§5.2).

### Bug 3: `fetch_dem` + `fetch_orbit` signature mismatch (`5f4218b`)

`fetch_dem(bounds, output_epsg, output_dir) -> (Path, dict)` and `fetch_orbit(sensing_time, satellite, output_dir) -> Path`, but the EU script was calling `fetch_dem(bounds, output_dir=...)` (missing `output_epsg`, expecting single-Path return) and `fetch_orbit(safe, output_dir=...)` (passing SAFE path as `sensing_time`, missing `satellite`). Both probably worked at one point against an earlier API. Mirror the NAM call patterns; pass epoch + hard-coded `S1A` for orbit.

### Bug 4: CDSE STAC returned 0 items (`18df6f1`)

`pystac_client.Client.open("https://catalogue.dataspace.copernicus.eu/stac")` with `collections=["SENTINEL-1"]`, productType=SLC, bbox + datetime±1h returned 0 items for 2024 Iberian queries. Suspected collection-rename or query-syntax drift since the CDSE STAC was rebuilt Feb 2025. ASF mirrors the same S1 SLCs and Earthdata credentials are already in scope (used for OPERA reference fetch in NAM); ported the NAM ASF-based `_download_safe_for_epoch` (with `relativeOrbit + intersectsWith` filter + zip validation).

### Bug 5: Missing `eu_burst_db.sqlite` for compass (`04bf1be`)

The EU script pointed `EU_BURST_DB_PATH` at `~/.subsideo/eu_burst_db.sqlite` — a Phase 1 planned artifact that was never built. compass's `runconfig.load_from_yaml` rejects missing files. The OPERA `opera-burst-bbox-only.sqlite3` v0.9.0 covers all global S1 bursts including EU (verified `t103_219329_iw1 → EPSG:32630, bbox(474360, 4490640, 573780, 4538910)`). Reuse the NAM cache. EU-specific burst DB derivation (Phase 1 D-12) is deferred since the OPERA DB suffices for our bursts.

### Bug 6: `numpy<2` re-broken by EGMStoolkit install

`pip install git+https://github.com/alexisInSAR/EGMStoolkit.git` upgraded numpy 1.26.4 → 2.4.4 as a transitive dep, breaking compass + isce3 again. Reverted via `pip install 'numpy<2' --force-reinstall --no-deps`. Going forward, all pip installs in this env should use `--no-deps` for packages that don't actually need newer numpy.

### Bug 7: ASF slice mismatch (`f581095`, also fixed in NAM)

Same root cause as the NAM Bug 11 — but in EU it consistently picked the wrong slice (180345 instead of the 180320 slice that contains the burst), wasting 24 GB of ASF download per attempt. Slice-containment filter (`r.startTime ≤ epoch ≤ r.stopTime`) applied symmetrically to both scripts.

### Bug 8: EGMStoolkit upstream packaging + API drift (deferred)

The Phase 3 plan called for an EGMS L2a stable-PS residual as the third gate metric (CSLC-05 D-12). Two upstream issues prevent integration this rollout:

1. `EGMStoolkit==0.2.15` is not on PyPI (pyproject metadata claimed it would be). GitHub HEAD (`alexisInSAR/EGMStoolkit`) builds via `pip install` but installs only the dist-info folder — the upstream `setup.cfg` is missing `package_dir = =src` for src-layout. A patched local clone fixes this in one line and `pip install -e` works.
2. Even with the local install fix, EGMStoolkit 0.3.0 has a class-based API (`EGMSdownloader.download(outputdir, unzipmode, cleanmode, force, verbose)`) — the EU script calls a functional 0.2.x API (`EGMStoolkit.download(bbox, product_level='L2a', release='2019_2023', output_dir=...)`).

The script's existing `try/except` around `_fetch_egms_l2a` already logs the failure and continues; `egms_l2a_stable_ps_residual_mm_yr` is null in metrics.json. Adapting `_fetch_egms_l2a` to the 0.3.0 class API is the deferred follow-up (§5.1).

---

## 5. Final Validation Results

### 5.1 Per-AOI metrics (from `eval-cslc-selfconsist-eu/metrics.json`)

| AOI | n_stable (DEM) | n_stable (CSLC ∩ valid) | coh_mean | coh_median | coh_p25/p75 | coh_med_of_persistent | persistent_frac | residual_mm_yr | egms_residual |
|-----|----------------|-------------------------|----------|------------|-------------|------------------------|-----------------|----------------|----------------|
| Iberian/Meseta-North | 117,341 | 84,453 | 0.849 | 0.846 | 0.838 | 0.891 | **0.868** | **92.3 %** | **+0.347** | n/a (deferred) |

Above the 0.7 coherence gate by 17 % and the 3 mm/yr residual gate by 8.6× — the cleanest of the three Phase 3 AOIs by every metric.

### 5.2 Coverage notes

- **Stable-mask retention**: 84,453 / 117,341 = 72 % of DEM-grid stable pixels survived the CSLC valid-data intersection. Iberian Meseta-North's burst footprint covers a large fraction of the AOI's stable interior — much higher retention than SoCal (0.4 %) which was clipped by the coast buffer.
- **persistent_frac = 92.3 %**: 92 % of stable pixels exceed coh ≥ 0.6 in EVERY one of the 14 sequential IFGs. Over 6 months of bare/sparse Iberian Meseta. This is unusually high and primarily reflects the steppe's lack of phenological change.
- **EGMS L2a third-number deferred**: see Bug 8 + §5.3.

### 5.3 Coherence histogram

`eval-cslc-selfconsist-eu/sanity/Iberian/coherence_histogram.png` shows a strongly unimodal distribution centred at 0.85 with almost the entire mass above the 0.7 gate. No bimodal P2.1 contamination.

### 5.4 OPERA amplitude sanity (n/a)

OPERA L2 CSLC-S1 V1 has no EU coverage; `compare_cslc` is skipped with the warning "OPERA CSLC-S1 V1 is N.Am. only; EU AOI amplitude sanity is best-effort". `reference_agreement` is null in metrics.json. By design.

### 5.5 Methodology cross-references (Phase 3 Plan 03-05 / CSLC-06)

- **Cross-version phase impossibility**: even if OPERA L2 CSLC-S1 V1 had EU
  coverage, single-scene phase comparison against a different-isce3-version
  reference would yield coherence ≈ 0 regardless of the corrections applied.
  The structural argument (isce3 SLC-interpolation kernel changed upstream of
  any phase-screen correction) is consolidated in
  [`docs/validation_methodology.md#cross-version-phase`](docs/validation_methodology.md#cross-version-phase).
  This CONCLUSIONS doc inherits the argument; PRs adding a new
  phase-correction branch must address the kernel argument before merge.
- **Product-quality vs reference-agreement distinction — three-number row**:
  the per-AOI table in §5.1 is the **motivating example** for
  [`docs/validation_methodology.md` §2](docs/validation_methodology.md#2-product-quality-vs-reference-agreement-distinction).
  Three independent numbers coexist as distinct measurements that never
  collapse into a single `.passed` verdict:

  - **(a)** OPERA CSLC amplitude `amp_r` / `amp_rmse_db` — reference-agreement
    BINDING. Not applicable for the EU AOI (OPERA L2 CSLC-S1 V1 is N.Am.-only)
    but the row category exists by design. See SoCal in
    `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` §5.1 for the populated form
    (`amp_r=0.982, amp_rmse_db=1.290 dB`).
  - **(b)** Self-consistency coherence `coh_med_of_persistent` —
    product-quality CALIBRATING. Iberian/Meseta-North = 0.891.
  - **(c)** Self-consistency residual `residual_mm_yr` plus the planned EGMS
    L2a stable-PS residual `egms_l2a_stable_ps_residual_mm_yr` —
    product-quality CALIBRATING. Iberian/Meseta-North residual = +0.347 mm/yr.
    The EGMS L2a third number is deferred this rollout (Bug 8); when populated
    it joins (c) without changing the category framing.

---

## 6. Output Files

```
eval-cslc-selfconsist-eu/
├── input/                                                  # 15 SAFEs (~117 GB)
├── orbits/                                                 # 15 POEORB EOFs
├── dem/Iberian/glo30_utm32630.tif                          # UTM 30N DEM
├── worldcover/                                             # 4 ESA WorldCover 2021 v200 tiles
├── output/Iberian/t103_219329_iw1/<YYYYMMDD>/<...>.h5      # 15 compass CSLC outputs
├── sanity/Iberian/                                         # P2.1 mitigation
├── egms/Iberian/                                           # empty (EGMS step deferred)
├── metrics.json                                            # per-AOI + cell aggregate
└── meta.json                                               # run provenance
```

---

## 7. Source Files Changed During This Session

All N.Am. session changes carry through (`CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` §7). EU-only deltas:

| File | Reason |
|------|--------|
| `run_eval_cslc_selfconsist_eu.py` | Bugs 1–7 (imports, signatures, ASF switch, burst DB reuse, slice match, real epochs, `fallback_chain=()`) |

No `src/subsideo/**` source files were modified for the EU cell beyond what the N.Am. cell already touched.

---

## 8. Recommendations for Next Steps

1. **Re-derive Iberian/Alentejo + Iberian/Massif Central burst IDs** (Bug 2 follow-up): use the same `asf-search` + footprint-intersection approach used for `IBERIAN_PRIMARY_EPOCHS` in this session. Target tracks: Alentejo (~38.5°N, UTM 29N — typical S1 tracks 8/37/110/139/154); Massif Central (~45°N, UTM 31N — typical S1 tracks 59/88/161). Restore `fallback_chain=(Alentejo, MassifCentral)` once both are validated.
2. **Adapt `_fetch_egms_l2a` to EGMStoolkit 0.3.0 class API** (Bug 8 follow-up): the 0.3.0 API requires `EGMSdownloader` instantiation + product configuration via class methods rather than a single `download(bbox, product_level, release)` call. Test against the EGMS public API to verify L2a 2019–2023 release fetches CSVs covering the Meseta-North bbox. Re-run cached eval (~5 min) to populate `egms_l2a_stable_ps_residual_mm_yr`.
3. **Patch EGMStoolkit packaging upstream**: open a PR adding `package_dir = =src` to `setup.cfg` (one line) so `pip install EGMStoolkit @ git+...` produces a working installation. Removes the local-clone-and-patch step.
4. **Build the planned EU-specific burst DB** (Phase 1 D-12 deferred): build `~/.subsideo/eu_burst_db.sqlite` from ESA's published burst ID GeoJSON via `subsideo/burst/db.py`. Required when EU AOIs need bursts not present in the OPERA global DB. For Phase 3 AOIs this is unnecessary — OPERA's DB already covers them.
5. **Calibrate gate thresholds** (Phase 4): combined N.Am. + EU coh_median_of_persistent samples are 0.804, 0.868, 0.887. The 0.7 candidate threshold has 100 % pass rate and is conservative; a tightened threshold (e.g. 0.78) would still pass all three but reject AOIs with marginal coherence.
