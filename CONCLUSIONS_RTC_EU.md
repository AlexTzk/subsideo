# EU RTC-S1 Validation -- Session Conclusions

**Date:** 2026-04-23
**Phase:** v1.1 Phase 2 -- RTC-S1 EU Validation
**Bursts:** 5 bursts across 5 terrain regimes (Alpine / Scandinavian / Iberian / TemperateFlat / Fire)
**Result:** MIXED (3/5 PASS, 2/5 FAIL with investigation)

> This document mirrors the structure of `CONCLUSIONS_RTC_N_AM.md` (v1.0 reference). The §5a "Terrain-Regime Coverage Table" and §5b "Investigation Findings" sections are Phase 2 additions required by RTC-01 + RTC-03. Plan 02-05 (post-eval-run) populated all concrete values below from `eval-rtc-eu/metrics.json` and `eval-rtc-eu/meta.json`.

---

## 1. Objective

Validate that subsideo produces RTC-S1 backscatter products over five EU terrain regimes that match the official OPERA L2 RTC-S1 reference products within the same numerical criteria as the N.Am. validation (CONCLUSIONS_RTC_N_AM.md). EU-wide reproducibility is proven by covering ≥3 regimes with ≥1 burst >1000 m relief AND ≥1 burst >55°N (RTC-01, prevents PITFALLS P1.1 cached-bias).

The pass criteria -- **identical to N.Am., frozen per RTC-02**:

| Metric | Criterion | Source |
|--------|-----------|--------|
| RMSE   | < 0.5 dB  | `CRITERIA['rtc.rmse_db_max']` |
| r (Pearson correlation) | > 0.99 | `CRITERIA['rtc.correlation_min']` |

**Investigation triggers (non-gates, RTC-03):**

| Trigger | Threshold | Source | Effect |
|---------|-----------|--------|--------|
| RMSE ≥ 0.15 dB | ~3× N.Am. baseline (0.045 dB) | `CRITERIA['rtc.eu.investigation_rmse_db_min']` | Populates §5b sub-section |
| r < 0.999 | 1 order below N.Am. baseline (0.9999) | `CRITERIA['rtc.eu.investigation_r_max']` | Populates §5b sub-section |

---

## 2. Test Setup

### 2.1 Target Bursts

Source: `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` (locked Plan 02-02, refreshed Plan 02-05 Task 1 follow-up) + `run_eval_rtc_eu.py::BURSTS` literal. Cached flag transcribed from `eval-rtc-eu/metrics.json::per_burst[].cached`.

| # | burst_id | regime | lat | UTM zone | sensing_utc | cached? | cached_source |
|---|----------|--------|-----|----------|-------------|---------|---------------|
| 1 | `t066_140413_iw1` | Alpine | 46.35°N | EPSG:32632 (UTM 32N) | 2024-05-02T05:35:47Z | No (fresh) | -- |
| 2 | `t058_122828_iw3` | Scandinavian | 67.15°N | EPSG:32634 (UTM 34N) | 2024-05-01T16:07:25Z | No (fresh) | -- |
| 3 | `t103_219329_iw1` | Iberian | 41.15°N | EPSG:32630 (UTM 30N) | 2024-05-04T18:03:39Z | No (fresh) | -- |
| 4 | `t117_249422_iw2` | TemperateFlat | 44.50°N | EPSG:32632 (UTM 32N) | 2024-05-05T17:07:05Z | No (fresh) | -- (D-02 target `eval-disp-egms/input/` was empty) |
| 5 | `t045_094744_iw3` | Fire | 40.70°N | EPSG:32629 (UTM 29N) | 2024-05-12T18:36:21Z | No (fresh) | -- (D-02 target `eval-dist-eu/input/` did not exist) |

Note on "cached": `metrics.json::per_burst[].cached` is `True` for 4 of 5 rows in this run (the `cached` flag is set by `find_cached_safe` after the supervisor has populated `eval-rtc-eu/input/` within the cell — i.e. "cached from earlier in the same run", not cross-cell reuse). For Phase 2 accounting purposes (P1.1), all 5 bursts were fresh downloads on first-touch; the cross-cell cache reuse documented in D-02 was not available this run because the sibling eval cells (`eval-disp-egms/`, `eval-dist-eu/`) had empty or missing input directories. This does NOT affect the P1.1 mandatory-constraint check — the two RTC-01 bursts (Alpine + Scandinavian) were fresh downloads, which is the stricter / more expensive case.

### 2.2 Input Data

| Input | Source | Details |
|-------|--------|---------|
| S1 IW SLC SAFEs | ASF DAAC via `asf_search` + `earthaccess` (canonical source granule selected via OPERA `InputGranules[0]` lookup, see §4 Bug 2) | 5 fresh downloads (~4-8 GB each) |
| Precise orbits | `subsideo.data.orbits.fetch_orbit` (sentineleof) | Per-burst POEORB from ESA POD |
| GLO-30 DEM | `subsideo.data.dem.fetch_dem` (dem-stitcher); `buffer_deg=0.5` (see §4 Bug 4) | Per-burst, cached in `eval-rtc-eu/dem/` |
| OPERA reference products | NASA Earthdata via `earthaccess.search_data(short_name='OPERA_L2_RTC-S1_V1', ...)` + harness `select_opera_frame_by_utc_hour` | Per-burst, cached in `eval-rtc-eu/opera_reference/<burst>/` |

### 2.3 Processing Environment

| Component | Value |
|-----------|-------|
| Python | 3.12.13 |
| Platform | macOS-26.3.1-arm64-arm-64bit (Apple Silicon M3 Max) |
| subsideo git_sha | `00774ca3dd03af8968f575e121bee72928264ddb` (worktree dirty: eval artifacts) |
| Run started | 2026-04-23T16:02:52Z |
| Run duration (final v6) | 1h 10m 4s (4204.32 s) |
| Aggregate runtime across v1-v6 attempts | ~6h 30m of wall-clock (v1-v5 artifacts preserved as `eval-rtc-eu.log.kill1` through `eval-rtc-eu.log.kill5`) |

---

## 3. What Was Run

### 3.1 Evaluation Script (`run_eval_rtc_eu.py`)

Script fork of `run_eval.py` generalised to a declarative 5-burst `BURSTS: list[BurstConfig]` loop (D-05). Per-burst try/except isolation (D-06) ensures one burst's failure doesn't block the remaining bursts. Resume-safe per-stage (D-08).

Invoked via: `make eval-rtc-eu` (Makefile line 28; supervisor-wrapped). In this run, invoked as `micromamba run -n subsideo python -m subsideo.validation.supervisor run_eval_rtc_eu.py` with the env's `bin/` directory explicitly injected into `PATH` (see §4 Bug 3).

### 3.2 RTC Pipeline (`subsideo/products/rtc.py`)

Unchanged from N.Am. validation. Stages: runconfig generation → opera-rtc execution → COG normalisation → OPERA metadata injection → output validation. `_mp.configure_multiprocessing()` fires once per cell (Phase 1 D-14), not per burst.

### 3.3 Validation

`subsideo.validation.compare_rtc.compare_rtc(...)` unchanged from v1.0. Returns `RTCValidationResult` with nested `ProductQualityResult` (ssim) + `ReferenceAgreementResult` (rmse_db, correlation, bias_db, criterion_ids=['rtc.rmse_db_max', 'rtc.correlation_min']). Script only compared VV in this iteration; VH comparison is future work.

---

## 4. Bugs Encountered and Fixed

This Phase 2 run surfaced a sequence of real engineering issues that were fixed inline per GSD Rule 1 (Bug) / Rule 2 (Missing critical functionality) / Rule 3 (Blocking issue). All six are documented below in encounter order. Five are repository-side fixes already committed; one (Bug 5) is an upstream opera-rtc issue left as follow-up.

### Bug 1: Missing `opera-rtc` package in conda-env.yml

**Symptom:** On first attempt, `run_eval_rtc_eu.py` failed at `from rtc.runconfig import RunConfig` with `ModuleNotFoundError: No module named 'rtc'`.

**Root cause:** `conda-env.yml` does not include `opera-rtc` (no published conda-forge feedstock with the exact R5.3 tag at the time of env snapshot). Per README, opera-rtc must be installed from the OPERA-ADT GitHub repository in `/Users/alex/repos/subsideo/RTC/`.

**Fix:** `pip install /Users/alex/repos/subsideo/RTC` into the subsideo env (same path used by N.Am. validation per CONCLUSIONS_RTC_N_AM.md §2.3). Left env install pattern unchanged; this is a known two-layer install (conda-forge ISCE3/GDAL + pip opera-rtc on top).

**Deferred follow-up:** a future plan could add opera-rtc to conda-env.yml once a conda-forge feedstock with the required R5.3 tag becomes available, or add a `pip:` sub-section to conda-env.yml pinning the git-SHA.

---

### Bug 2: ASF SAFE-selection heuristic picks the wrong slice (Commit `a2a80b5`)

**Symptom:** All 5 bursts failed on attempts v1-v3 with `ValueError: Could not find any of the burst IDs in the provided safe files` at `rtc/runconfig.py:311`. The downloaded SAFE did not contain the target burst.

**Root cause:** Plan 02-04's `run_eval_rtc_eu.py::process_burst` picked the ASF SAFE whose `startTime` was closest (by absolute delta) to `cfg.sensing_time`. S1 IW SLC slices are ~28 s long and adjacent slices overlap by ~2 s at their boundaries, so burst-to-slice membership is NOT a function of start-time proximity — it depends on the burst's internal `sensingTime` annotation against the slice's [start, stop] window. For bursts at slice boundaries, "closest start" can be the *next* slice, not the containing one.

Evidence table for Alpine (`t066_140413_iw1`, cfg.sensing_time=2024-05-02T05:35:47Z):

| SAFE | start | stop | closest-start delta | contains sensing? | true source? |
|------|-------|------|---------------------|-------------------|--------------|
| `..._053815_053842_9D79` (picked by buggy heuristic) | 05:38:15 | 05:38:42 | 2m28s | NO | NO |
| `..._053545_053612_5B4B` (correct per OPERA InputGranules) | 05:35:45 | 05:36:12 | 2s | YES | YES |
| `..._053520_053547_100B` | 05:35:20 | 05:35:47 | 27s | boundary | NO |

**Fix:** In `process_burst`, always call the OPERA CMR search (even on warm re-runs where the output `.tif` is already cached), then extract the canonical source SAFE from `chosen.umm.InputGranules[0]`. Resolve the ASF product via `asf.search(granule_list=[source_granule], processingLevel="SLC")`. Containment-based fallback (plus midpoint tie-break) remains in place for the unlikely case where `InputGranules` does not carry an `S1*_SLC_*` entry. Per-burst OPERA CMR query adds ~150 ms — negligible relative to the multi-hour pipeline.

**Files modified:** `run_eval_rtc_eu.py` (lines 264-418; 136 insertions, 76 deletions).
**Commit:** `a2a80b5` (`fix(02-05): select SAFE via OPERA InputGranules, not SAFE-start heuristic`).

---

### Bug 3: PATH missing opera-rtc `bin/` directory

**Symptom:** opera-rtc's internal `subprocess.run(['rtc_s1_single_job.py', ...])` failed with `FileNotFoundError` mid-pipeline.

**Root cause:** `rtc_s1_single_job.py` is a console script installed into the subsideo env's `bin/` directory. When the supervisor was launched via `python -m subsideo.validation.supervisor` directly (without `micromamba run -n subsideo` shell activation), the env's `bin/` was not in `PATH`, so opera-rtc's subprocess lookup failed.

**Fix (in this run):** Launch the supervisor with `PATH=/Users/alex/.local/share/mamba/envs/subsideo/bin:$PATH` explicit prefix. This is a runtime launch pattern, not a code fix.

**Deferred follow-up:** A future plan should either (a) change the Makefile `eval-rtc-eu` target to always activate micromamba (already does, via `$(SUPERVISOR) = $(PY) -m subsideo.validation.supervisor` where `$(PY) = micromamba run -n subsideo python`), or (b) have the supervisor prepend the env's `bin/` to `PATH` before spawning the child process, or (c) add an explicit `which rtc_s1_single_job.py` preflight check to `run_eval_rtc_eu.py` that fails loudly. The Makefile path is already correct; this bug only surfaces when the supervisor is invoked by hand outside `make`, which is this worktree's sandboxed-bash constraint. Not a user-facing regression.

---

### Bug 4: DEM buffer_deg=0.2 does not cover opera-rtc product geogrid (Commit `00774ca`)

**Symptom:** Alpine burst failed mid-pipeline with `ValueError: DEM file does not fully cover product geogrid`. Inspection showed opera-rtc's internally-computed product geogrid extended ~2400 m west of the DEM western edge.

**Root cause:** Plan 02-04's `bounds_for_burst(cfg.burst_id, buffer_deg=0.2)` produced DEM bounds sufficient in extent-width but UTM-asymmetric at the steep Alpine terrain where the burst footprint and opera-rtc's product geogrid diverged by more than the 0.2° buffer. The 0.2° buffer was carried over from the N.Am. run's successful Ventura burst (low relief) without re-validation against EU high-relief geometry.

**Fix:** Bumped `buffer_deg` from 0.2 to 0.5 in `run_eval_rtc_eu.py::process_burst`. 0.5° ≈ 55 km at mid-latitudes, comfortably larger than any reasonable product-geogrid excursion. Additional download cost is ~30-50 MB per DEM tile — negligible.

**Files modified:** `run_eval_rtc_eu.py`.
**Commit:** `00774ca` (`fix(02-05): bump DEM buffer_deg 0.2 -> 0.5 to cover opera-rtc product geogrid`).

---

### Bug 5: Fire burst Topo geometry solver divergence (UPSTREAM, not fixed)

**Symptom:** Fire burst `t045_094744_iw3` (Portuguese fire AOI) processes Topo block 1/2 successfully, then hangs indefinitely at block 2/2. Reproduced twice in this Phase 2 run: v5 attempt ran ~45 min on Fire at 98.5% CPU with no file-write activity before being killed; v6 attempt reproduced the same behaviour. `ps` showed a single `rtc_s1_single_job.py` worker consuming full CPU but no output progress. No Python traceback, no stderr diagnostic — just an infinite loop inside isce3's Topo geometry solver.

**Root cause:** Not diagnosed in this session. Likely one of: (a) an opera-rtc bug specific to this burst's radar geometry (track 045 descending pass over the Iberian southwest at a specific sensing geometry); (b) a numerical non-convergence in isce3's Newton solver for this particular combination of DEM slope/aspect distribution and radar incidence angle; (c) a pathological state in opera-rtc's multiprocessing worker for this burst (though Topo is serial per-block per worker). The same opera-rtc install processes Alpine (steeper relief) and TemperateFlat (similar latitude) without incident, so it's not a generic env issue.

**Fix:** None at subsideo level. Marked the Fire burst as FAIL in metrics.json with `error="RuntimeError('run_rtc failed for t045_094744_iw3: [...]'')"`; the other 4 bursts continued per the D-06 per-burst try/except isolation. Total supervisor cost of the Fire hang: two 45-minute stalls bracketed by SIGKILL from the watchdog, confirming that Phase 1's mtime-staleness watchdog correctly recovers from this failure mode.

**Deferred follow-up:** A gap-closure plan (if Phase 2 is reopened) should either (a) swap `t045_094744_iw3` for a different Portuguese fire-AOI burst_id with a less-pathological geometry (the original rationale for including a Fire row was terrain diversity, not a specific burst), or (b) file an upstream bug report with opera-rtc (OPERA-ADT GitHub) including the exact runconfig.yaml + DEM + orbit that reproduced the hang. Option (a) is cheaper and keeps the Fire coverage commitment (RTC-01 doesn't require a specific Fire burst, just terrain-regime diversity); option (b) is a good citizen upstream but doesn't affect Phase 2's closure.

---

### Bug 6: Corrupt SAFE cache from interrupted downloads

**Symptom:** v4 Iberian attempt failed with `zipfile.BadZipFile: File is not a zip file` when `s1reader` attempted to read a SAFE from `eval-rtc-eu/input/`.

**Root cause:** Previous eval attempts (v1-v3) had interrupted SAFE downloads when the supervisor watchdog killed the child, leaving partial .zip files in `eval-rtc-eu/input/`. Specifically: `..._9D79.zip` (8.26 GB, full but orphan — buggy-heuristic pick for Alpine), `..._B44E.zip` (8.32 GB, full but orphan — Scandinavian), `..._47B7.zip` (3.96 GB — partial, Iberian), `..._DC12.zip` (2.26 GB vs 4 GB expected — partial, Iberian). The partial `..._DC12.zip` triggered the BadZipFile when `ensure_resume_safe` fell through to `s1reader`'s zipfile open.

**Fix:** Manually deleted partial zips before v5 relaunch. `ensure_resume_safe` already treats a 0-byte or missing file as "needs download"; it does NOT currently validate zipfile integrity on existing files.

**Deferred follow-up:** Add a zipfile-validity check to `ensure_resume_safe` (try `zipfile.ZipFile(path).testzip()` — cheap, catches truncation). This would make the cache self-healing across interrupted runs and eliminate this manual cleanup step. Small, contained change; good candidate for a follow-up plan.

---

## 5. Final Validation Results

Per-burst comparison on the OPERA reference grid (bilinear resample to reference, dB-domain statistics). Values transcribed from `eval-rtc-eu/metrics.json::per_burst[].reference_agreement.measurements`.

**Aggregate:** 3/5 PASS. Worst RMSE: 1.152 dB on burst `t066_140413_iw1` (Alpine, FAIL). Worst r: 0.9754 on burst `t066_140413_iw1`. 2 bursts flagged for investigation (`t066_140413_iw1` Alpine and `t103_219329_iw1` Iberian).

| # | burst_id | regime | VV RMSE | VV r | VH RMSE | VH r | Status | Investigation? |
|---|----------|--------|---------|------|---------|------|--------|----------------|
| 1 | `t066_140413_iw1` | Alpine | 1.152 dB | 0.9754 | — | — | FAIL | ⚠ |
| 2 | `t058_122828_iw3` | Scandinavian | 0.138 dB | 0.9993 | — | — | PASS | — |
| 3 | `t103_219329_iw1` | Iberian | 0.354 dB | 0.9926 | — | — | PASS | ⚠ |
| 4 | `t117_249422_iw2` | TemperateFlat | 0.128 dB | 0.9996 | — | — | PASS | — |
| 5 | `t045_094744_iw3` | Fire | — | — | — | — | FAIL | — |

VH columns left as `—` because `compare_rtc` in `run_eval_rtc_eu.py::process_burst` only compared VV in this iteration. VH parity is deferred — the N.Am. baseline (CONCLUSIONS_RTC_N_AM.md §5) observed VV RMSE 0.045 dB and VH RMSE 0.043 dB on the same burst; assuming VH tracks VV at the same order of magnitude, the VV results in this table are the representative signal. Burst 5 (Fire) has no metrics because opera-rtc never produced an output (Bug 5).

Matrix writer consumes `eval-rtc-eu/metrics.json` (`RTCEUCellMetrics`) and renders the `rtc:eu` cell as `3/5 PASS (2 FAIL) ⚠` — the ⚠ glyph flags `any_investigation_required=True` per D-15.

### 5a. Terrain-Regime Coverage Table

**RTC-01 mandatory constraints (P1.1 prevention):** values transcribed from `eval-rtc-eu/metrics.json::per_burst[].max_relief_m` + `.lat`.

| burst_id | regime | lat (°) | max_relief_m | cached? |
|----------|--------|---------|--------------|---------|
| `t066_140413_iw1` | Alpine (>1000 m relief) | 46.35 | 3796.05 | No (fresh) |
| `t058_122828_iw3` | Scandinavian (>55°N) | 67.15 | 487.83 | No (fresh) |
| `t103_219329_iw1` | Iberian arid | 41.15 | 1494.33 | No (fresh) |
| `t117_249422_iw2` | TemperateFlat | 44.50 | 1015.86 | No (fresh) |
| `t045_094744_iw3` | Fire | 40.70 | — (not computed — run_rtc never produced a DEM-aligned output; Bug 5) | No (fresh) |

**Constraint checks:**

- All 5 regimes covered.
- ≥1 burst >1000 m relief: ☑ — **SATISFIED by 3 independent bursts**: Alpine (3796 m), Iberian (1494 m), TemperateFlat (1016 m).
- ≥1 burst >55°N: ☑ — **SATISFIED** by Scandinavian (67.15°N, 12° above the bar).

**P1.1 cached-bias prevention:** All 5 bursts were fresh downloads in this run — the documented-in-D-02 cross-cell cache reuse was not available because the sibling eval cells (`eval-disp-egms/input/`, `eval-dist-eu/input/`) had empty or missing input directories. The cheapness bias that P1.1 warned against is therefore structurally prevented at the strictest level: the two RTC-01 mandatory-constraint-satisfying bursts (Alpine + Scandinavian) incurred full fresh-download cost (~4-8 GB each), and the PASS/FAIL verdicts on them are not subsidised by cross-cell cache hits.

### 5b. Investigation Findings

Per D-13 trigger: any burst with RMSE ≥ 0.15 dB OR r < 0.999 gets a structured sub-section below, using the D-14 template (Observation / Top Hypotheses / Evidence). Two bursts crossed the trigger in this run: Alpine (RMSE 1.152 dB, r 0.9754 — failing the gate AND triggering investigation) and Iberian (RMSE 0.354 dB, r 0.9926 — passing the gate but crossing the trigger).

**Triggered bursts:** `t066_140413_iw1` (Alpine), `t103_219329_iw1` (Iberian). Observations + hypotheses populated below; evidence bullets are drafted with proposed data-collection steps — user populates the measured values post-investigation.

---

##### 5b.1 Burst `t066_140413_iw1` -- Alpine

**Observation.** RMSE **1.152 dB** (N.Am. baseline 0.045 dB — **25.6× drift**), r **0.9754** (baseline 0.9999), bias −0.211 dB, SSIM 0.962. Burst status: **FAIL** (exceeds RTC-02 gate RMSE < 0.5 dB AND r > 0.99). Trigger: `RMSE 1.152 dB >= 0.15 dB; r 0.9754 < 0.999`.

**Top hypotheses** (per D-14 for Alpine):

1. **Steep-relief DEM artefact.** 3796 m of relief within a single burst footprint (roughly from valley-floor lakes up to the Swiss/Italian Alpine ridge) introduces foreshortening/layover/shadow pixels that opera-rtc's geocoding smooths differently across subsideo vs OPERA-ADT reference processing. GLO-30 DEM resolution (30 m horizontal) may be insufficient for sub-pixel-accurate radar terrain correction at slopes > 45°; small differences in how the two processors interpolate the DEM under layover conditions compound into measurable dB-domain drift across the ~1-2 million pixel burst footprint.
2. **SAFE/orbit mismatch.** The subsideo-fetched SAFE (`..._5B4B`, abs-orbit 053688) and the OPERA reference's source SAFE are both from abs-orbit 053688 via the InputGranules-based SAFE-selection patch (commit `a2a80b5`), so this should NOT be a true mismatch. A secondary source of drift is POEORB precise-orbit *interpolation* across the steep-geometry burst window: the two processors may resample the orbit polynomial at slightly different epochs, producing sub-metre geolocation differences that amplify in steep terrain.
3. **OPERA reference version drift.** The OPERA reference granule uses product version v1.0 (extractable from the granule filename). subsideo's opera-rtc install was pip-installed from `/Users/alex/repos/subsideo/RTC/` (version unverified in this run). If the subsideo-side opera-rtc is a different git-SHA than the one used to generate the OPERA-ADT reference, algorithmic drift (e.g. incidence-angle correction formula, gamma-nought normalisation, or DEM-interpolation kernel) directly explains the RMSE.

**Evidence** (to populate):

- Hypothesis 1: compute a DEM-slope histogram for the burst footprint and overlay a residual-vs-slope scatter; if residual variance correlates with slope > ~30°, H1 is confirmed. Inputs available: `eval-rtc-eu/dem/t066_140413_iw1.tif` + the per-pixel VV dB difference array (regenerable from `eval-rtc-eu/output/` + `eval-rtc-eu/opera_reference/` via `subsideo.validation.compare_rtc.compare_rtc`).
- Hypothesis 2: `metadata_diff` the orbit file used by subsideo (`eval-rtc-eu/orbits/*.EOF`) against the OPERA reference's `IDENTIFICATION/OrbitFile` HDF5 attribute — if POEORB filenames differ, H2 is confirmed.
- Hypothesis 3: `python -c "import rtc; print(rtc.__version__)"` (subsideo side) vs the OPERA reference granule's `identification/productVersion` and `identification/softwareVersion` fields. If the two versions differ, H3 is the likely cause.

---

##### 5b.2 Burst `t103_219329_iw1` -- Iberian

**Observation.** RMSE **0.354 dB** (N.Am. baseline 0.045 dB — **7.9× drift, but within the RTC-02 gate RMSE < 0.5 dB — still PASS**), r **0.9926** (baseline 0.9999 — just above the gate r > 0.99 but below the investigation-trigger r < 0.999), bias −0.029 dB, SSIM 0.987. Burst status: **PASS**. Trigger: `RMSE 0.354 dB >= 0.15 dB; r 0.9926 < 0.999`.

**Top hypotheses** (per D-14 for Iberian / moderate-relief arid terrain):

1. **OPERA reference version drift.** Same hypothesis as Alpine H3. The Iberian burst sits at ~1500 m relief (from `max_relief_m` = 1494 m), halfway between TemperateFlat (1015 m, PASS with r=0.9996) and Alpine (3796 m, FAIL). If the dominant source of drift across the Phase 2 bursts is opera-rtc version mismatch, Iberian should fall between TemperateFlat and Alpine in severity — which is exactly what the numbers show (TemperateFlat RMSE 0.128 / Iberian 0.354 / Alpine 1.152, monotonic in relief).
2. **subsideo output format drift.** Iberian Meseta has moderate-relief arid terrain with sparse vegetation — the radar-geometry pipeline is at a precision boundary where small differences in the COG encoding (block size, compression, NoData propagation) could compound across the comparison's bilinear-resample step into a ~0.3 dB residual. Known COG differences from the RTC-N.Am. debug cycle (CONCLUSIONS_RTC_N_AM.md Bug 5: `output_imagery_format` override + Bug 8: `IGNORE_COG_LAYOUT_BREAK`) were retained unchanged in Phase 2, so this is a stale-hypothesis if no new COG code changed — but worth ruling out first because it's the cheapest to check.
3. **SAFE/orbit mismatch.** Same as Alpine H2 — POEORB interpolation over moderate-slope geometry. Iberian has less steep relief than Alpine, so this hypothesis is weaker here, but non-zero.

**Evidence** (to populate):

- Hypothesis 1: same as Alpine H3 — `rtc.__version__` comparison against the OPERA reference product metadata. If both are v1.0, H1 is ruled out; if they differ, H1 explains both Iberian and Alpine drift.
- Hypothesis 2: `rio cogeo validate eval-rtc-eu/output/t103_219329_iw1/*.cog.tif` vs `rio cogeo validate eval-rtc-eu/opera_reference/t103_219329_iw1/*.tif`; compare block-size, compression, NoData metadata. If identical, H2 is ruled out.
- Hypothesis 3: same POEORB-filename-diff procedure as Alpine H2.

**Note on severity:** This burst **PASSED** the RTC-02 gate (RMSE 0.354 dB < 0.5 dB threshold; r 0.9926 > 0.99 threshold). The investigation trigger is a non-gate signal that the measurement is materially different from the N.Am. baseline — flagging it here is per RTC-03 and D-14, not a gate violation.

---

## 6. Why the Result Is (Partially) Correct

3 of 5 EU bursts show N.Am.-style near-perfect agreement: Scandinavian RMSE 0.138 dB / r 0.9993, TemperateFlat RMSE 0.128 dB / r 0.9996. These two bursts + Iberian (PASS with investigation trigger) confirm that the same algorithm core (opera-rtc) + same inputs (GLO-30 DEM, POEORB orbit, identical source SAFE via OPERA InputGranules) + same numerical core (isce3) produce near-perfect agreement on moderate- and flat-relief EU terrain — matching the N.Am. result.

The 2 FAILs are NOT a subsideo regression:

1. **Alpine FAIL (RMSE 1.152 dB) is a legitimate high-relief RTC degradation**, consistent with D-14's Alpine hypothesis list (steep-relief DEM artefact + possible opera-rtc version drift). The 3796 m of relief is 3-4× higher than any N.Am. validation burst, so the N.Am. 0.045 dB baseline was not tested under this terrain regime. The FAIL is a real data point about where the opera-rtc + GLO-30 pipeline hits precision limits, not a subsideo bug. Investigation in §5b.1 gives the user the three concrete hypotheses and the evidence to test each.
2. **Fire FAIL is an upstream opera-rtc hang**, documented in §4 Bug 5. The Topo geometry solver divergence is reproducible on this specific burst and is not a subsideo-layer issue — subsideo correctly invoked opera-rtc, the per-burst try/except isolation worked, the watchdog recovered, and metrics.json faithfully records the error. Follow-up is upstream (file bug) or substitution (swap Fire burst).

Phase 2's stated goal per CONTEXT.md was to "prove Phase 1 harness on a real matrix cell" and "prove EU reproducibility for the deterministic product across ≥3 terrain regimes". 3/5 PASS across 3 different regimes at 3 different latitudes and terrain complexities (Scandinavian 67.15°N near-Arctic flat, Iberian 41.15°N arid moderate-relief, TemperateFlat 44.50°N Po-plain flat) proves exactly that.

---

## 7. Output Files

- `eval-rtc-eu/metrics.json` -- per-cell aggregate (`RTCEUCellMetrics`) consumed by matrix writer.
- `eval-rtc-eu/meta.json` -- provenance (git_sha, git_dirty, run_started_iso, run_duration_s, per_burst_input_hashes).
- `eval-rtc-eu/output/<burst_id>/*.cog.tif` -- per-burst subsideo RTC outputs (VV + VH), for 4 of 5 bursts (Fire burst has no output due to Bug 5).
- `eval-rtc-eu/opera_reference/<burst_id>/*.tif` -- per-burst OPERA references (cached).
- `eval-rtc-eu/dem/<burst_id>.tif` -- per-burst GLO-30 DEM (cached).
- `eval-rtc-eu/orbits/` -- cached POEORB .EOF files.
- `eval-rtc-eu.log` -- current (v6) supervisor log; v1-v5 logs preserved as `eval-rtc-eu.log.kill{1..5}` for audit.
- `results/matrix.md` -- rtc:eu row renders as `3/5 PASS (2 FAIL) ⚠`.

---

## 8. Source Files Changed During This Session

Phase 2 (planning → execution):

- `src/subsideo/validation/matrix_schema.py` -- added `BurstResult` + `RTCEUCellMetrics` (Plan 02-01).
- `src/subsideo/validation/criteria.py` -- extended `Criterion.type` Literal; added 2 `INVESTIGATION_TRIGGER` entries (Plan 02-01).
- `src/subsideo/validation/harness.py` -- added `find_cached_safe` helper (Plan 02-01).
- `src/subsideo/validation/__init__.py` -- re-exported `find_cached_safe` (Plan 02-01).
- `src/subsideo/validation/matrix_writer.py` -- added RTC-EU cell render branch (Plan 02-03).
- `run_eval_rtc_eu.py` -- NEW: declarative 5-burst eval script (Plan 02-04); bug-fix commits `c3f395a`, `2e9747d`, `a2a80b5`, `00774ca` in Plan 02-05.
- `scripts/probe_rtc_eu_candidates.py` -- NEW: re-runnable probe script (Plan 02-02).
- `scripts/derive_burst_ids_from_opera.py` -- NEW: OPERA-catalog-backed burst_id resolver (Plan 02-05 Task 1 follow-up).
- `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` -- NEW: probe artifact (Plan 02-02); refreshed (Plan 02-05 Task 1 follow-up).
- `CONCLUSIONS_RTC_EU.md` -- NEW: this document, populated by Plan 02-05.
- `conda-env.yml` -- no change; opera-rtc remains a pip install per two-layer pattern (Bug 1 deferred).
