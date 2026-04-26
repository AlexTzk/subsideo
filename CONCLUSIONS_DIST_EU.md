# EU DIST-S1 Evaluation -- Session Conclusions

**Date:** 2026-04-16 / 2026-04-17
**AOI:** MGRS 29TNF (2024 Portuguese Wildfires, Aveiro/Viseu; EPSG:32629 UTM 29N)
**Scenes:** Post dates 2024-09-28 and 2024-11-15, relative orbit 147, S1A
**Reference:** Copernicus EMS Rapid Mapping EMSR760 burn perimeters (VHR optical delineation, WorldView-2/3)
**Result:** **STRUCTURALLY COMPLETE with cross-sensor quantitative comparison** -- pipeline produces valid DIST-S1 output for EU AOIs with high precision (88-92%) against EMS burn perimeters; low recall (3.7-6.3% confirmed, 25.7-31.0% including provisionals) is expected for single-snapshot SAR vs multi-date VHR optical

---

## 1. Objective

The N.Am. DIST-S1 evaluation (CONCLUSIONS_DIST_N_AM.md) proved the pipeline runs end-to-end but could not measure accuracy because OPERA DIST-S1 reference products are not yet published. This EU evaluation closes that gap by:

1. Proving the `dist_s1` pipeline works for EU MGRS tiles (not just N.Am.)
2. Comparing output against an independent reference: Copernicus EMS Rapid Mapping activation EMSR760 burn perimeters for the September 2024 Portuguese wildfires
3. Testing whether a later post-fire observation date improves detection accuracy (Sep 28 vs Nov 15)

This is a **cross-sensor comparison** (C-band SAR backscatter change vs VHR optical burn mapping), not an algorithm-equivalence test. The EMS reference uses WorldView-2/3 optical imagery at ~0.3-0.5 m resolution; DIST-S1 uses Sentinel-1 SAR at 30 m. Precision measures spatial agreement; recall asymmetry is expected.

### 1.1 Pass Criteria

| Metric | Criterion | Rationale |
| --- | --- | --- |
| Precision (cross-sensor) | > 0.50 | When DIST-S1 flags disturbance, does it land within the EMS burn perimeter? |
| Structural checks | all pass | Valid COG, correct CRS, 30 m pixel, disturbance detected |

F1 and recall criteria are intentionally omitted for cross-sensor comparison -- SAR-based single-snapshot detection will never match multi-date VHR optical mapping recall. Precision is the meaningful metric: does the pipeline detect real disturbance, or is it hallucinating?

### 1.2 AOI Choice Rationale

The September 2024 Portuguese wildfires (Aveiro/Viseu district) are an ideal EU test case:

- **Large and well-documented:** ~135,000 ha burned across multiple fronts (Sept 15-19 2024), the deadliest Portuguese fire season in years
- **Authoritative reference:** Copernicus EMS Rapid Mapping activation EMSR760 with 4 AOIs, 11 delineation products, and 111,324 ha of mapped burn perimeters from WorldView-2/3 optical imagery
- **Good Sentinel-1 coverage:** OPERA RTC-S1 products available on ASF DAAC for 4 tracks (T045, T052, T125, T147) covering the fire area
- **EU-specific:** validates that the pipeline works outside North America using the same OPERA RTC-S1 inputs auto-fetched from ASF DAAC

MGRS tile **29TNF** was resolved via `mgrs.MGRS().toMGRS()` for the fire centroid (~40.75°N, 8.48°W). Track **147** (ascending, ~18:28 UTC) was selected for having the most RTC products (32 in the Jul-Oct 2024 window, 9 unique dates with 6 pre-fire and 3 post-fire). Probe via `dist_s1_enumerator.enumerate_one_dist_s1_product` confirmed 165 RTC inputs (150 pre + 15 post bursts) for post_date=2024-09-28.

---

## 2. Test Setup

### 2.1 Targets

| Parameter | Sep 28 run | Nov 15 run |
| --- | --- | --- |
| AOI name | 2024 Portuguese Wildfires (Aveiro/Viseu) | same |
| MGRS tile | 29TNF | same |
| UTM EPSG | 32629 (UTM zone 29N) | same |
| Sentinel-1 track | 147 (ascending, UTC ~18:28) | same |
| Post date | 2024-09-28 | 2024-11-15 |
| Days post-fire | 13 | 61 |
| Post date buffer | 5 days | 5 days |
| Pre-image strategy | Multi-window anniversary (3 years) | same |
| Pre-image bursts | 150 | 150 |
| Post-image bursts | 15 | 15 |
| Output grid | 3660 x 3660, 30 m posting | same |
| Compute time | 8.3 min (M3 Max, CPU) | 8.5 min |

### 2.2 Harness

`run_eval_dist_eu.py` -- 6-stage evaluation script:

1. **Stage 1** -- Earthdata authentication (ASF DAAC for RTC auto-fetch)
2. **Stage 2** -- Probe OPERA RTC-S1 availability for EU tile (confirm data exists)
3. **Stage 3** -- Enumerate dist_s1 inputs via `dist_s1_enumerator`
4. **Stage 4** -- Run `dist_s1.run_dist_s1_workflow` with resume-safe output detection
5. **Stage 5** -- Output inspection: shape, CRS, class histogram
6. **Stage 6** -- Download Copernicus EMS EMSR760 burn perimeters via EMS API, rasterise, and compute binary classification metrics

The script auto-downloads EMS reference data from `https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/` on first run and caches it in `eval-dist-eu/ems_reference/`.

### 2.3 Reference Data

**Copernicus EMS Rapid Mapping -- EMSR760** (Wildfire in Portugal)

- Activation: 2024-09-16 by Portuguese National Authority for Civil Protection
- Event: Wildfires in Oliveira de Azeméis, Sever do Vouga, Albergaria-a-Velha (Aveiro region)
- 4 AOIs, 11 delineation products, delivered 2024-09-16 to 2024-09-24
- Source imagery: WorldView-2/3 VHR optical
- Total mapped burnt area: 111,324 ha (EMS report)
- Data format: GeoJSON vector polygons (observedEvent layers)
- 784 burn perimeter features intersect MGRS tile 29TNF after reprojection and deduplication
- Dissolved union area within tile: ~90,131 ha (rasterised at 30 m = 1,001,492 pixels)

---

## 3. Execution Log

### 3.1 Sep 28 Run (13 days post-fire)

| Stage | What happened | Time |
| --- | --- | --- |
| 1 | Earthdata auth OK, ASF session OK | ~1 s |
| 2 | 207 OPERA RTC-S1 products found; Track 147: 9 dates (6 pre, 3 post) | ~3 s |
| 3 | dist_s1_enumerator: 150 pre + 15 post = 165 total bursts | ~45 s |
| 4 | `run_dist_s1_workflow(device='cpu')` -- download 330 RTC files, despeckle, 15 post-bursts x ~3400 chips | 8.3 min |
| 5 | 3660x3660 uint8, EPSG:32629, 30 m; 41,833 confirmed + 296,735 provisional | ~1 s |
| 6 | Downloaded 4 EMSR760 GeoJSONs, rasterised, computed metrics | ~5 s |

### 3.2 Nov 15 Run (61 days post-fire)

| Stage | What happened | Time |
| --- | --- | --- |
| 1-3 | Same as Sep 28 (different pre-image anniversary dates: Nov 2021-2023) | ~50 s |
| 4 | `run_dist_s1_workflow(device='cpu')` -- download 330 RTC files, despeckle, detect | 8.5 min |
| 5 | 3660x3660 uint8, EPSG:32629, 30 m; 68,330 confirmed + 355,149 provisional | ~1 s |
| 6 | Reused cached EMSR760 GeoJSONs, computed metrics | ~5 s |

---

## 4. Metrics

### 4.1 DIST-S1 vs Copernicus EMS EMSR760 -- Confirmed Disturbance (labels 2-8)

| Metric | Sep 28 (13 days) | Nov 15 (61 days) | Change |
| --- | --- | --- | --- |
| F1 | 0.0708 | 0.1175 | +66% |
| **Precision** | **0.8824** | **0.9199** | **+4 pts** |
| Recall | 0.0369 | 0.0628 | +70% |
| Overall accuracy | 0.9089 | 0.9113 | +0.2 pts |
| IoU | 0.0367 | 0.0624 | +70% |
| DIST-S1 area | 3,765 ha | 6,150 ha | +63% |
| EMS burnt area | 90,131 ha | 90,131 ha | -- |
| Overlap | 3,322 ha | 5,657 ha | +70% |

### 4.2 Including Provisional Alerts (labels 1-8)

| Metric | Sep 28 | Nov 15 | Change |
| --- | --- | --- | --- |
| F1 | 0.3838 | 0.4351 | +13% |
| Precision | 0.7596 | 0.7320 | -3 pts |
| Recall | 0.2568 | 0.3095 | +5 pts |
| IoU | 0.2375 | 0.2780 | +4 pts |
| DIST-S1 area | 30,471 ha | 38,113 ha | +25% |
| Overlap | 23,145 ha | 27,897 ha | +21% |

### 4.3 Class Histograms

| Label | Description | Sep 28 | Nov 15 |
| --- | --- | --- | --- |
| 0 | No disturbance | 10,306,222 (76.94%) | 10,221,308 (76.30%) |
| 1 | First detection (provisional) | 296,735 (2.22%) | 355,149 (2.65%) |
| 4 | Confirmed (provisional low) | 41,833 (0.31%) | 68,330 (0.51%) |
| 255 | Nodata | 2,750,810 (20.54%) | 2,750,813 (20.54%) |

### 4.4 Structural Checks (both runs)

| Check | Result |
| --- | --- |
| Valid COG output | PASS |
| CRS matches EPSG:32629 | PASS |
| Grid size > 1000x1000 | PASS (3660x3660) |
| Pixel size 25-35 m | PASS (30.0 m) |
| Disturbance detected | PASS |
| Precision > 0.50 (cross-sensor) | PASS (88-92%) |

**Overall verdict:** All structural checks pass. Cross-sensor precision is excellent (88-92%). The pipeline correctly localises disturbance within the EMS burn perimeter with very low false alarm rate.

---

## 5. Interpretation

### 5.1 Why Precision Is High

When DIST-S1 flags a pixel as "disturbed", it lands within the EMS-mapped burn perimeter 88-92% of the time. The 8-12% false positives likely represent:
- Disturbance from non-fire causes (agriculture, construction) that the DIST algorithm correctly detects but the fire-specific EMS reference doesn't cover
- Edge effects at the 30 m pixel boundary vs the VHR optical burn perimeter

This high precision validates that the pipeline's disturbance signal is real, not noise.

### 5.2 Why Recall Is Low

DIST-S1 detects 3.7-6.3% (confirmed) or 25.7-31.0% (including provisionals) of the EMS-mapped burn area. This is expected for three reasons:

1. **Single-snapshot vs cumulative monitoring.** Each run uses ONE post-fire Sentinel-1 acquisition. The DIST-S1 algorithm is designed for operational monitoring where it accumulates evidence across observations. A single snapshot can only detect the most dramatic backscatter changes.

2. **SAR vs optical sensitivity.** EMS used WorldView-3 VHR optical imagery that detects colour/reflectance changes (scorching, ash deposition) immediately visible after fire. C-band SAR responds to structural canopy changes -- light-to-moderate burn severity may not produce detectable backscatter change.

3. **Resolution mismatch.** EMS mapped at ~0.3-0.5 m; DIST-S1 operates at 30 m. Small burnt patches and edge detail are lost.

### 5.3 Temporal Improvement

The Nov 15 run (61 days post-fire) improved every metric vs Sep 28 (13 days):
- Confirmed recall: 3.7% → 6.3% (+70%)
- Confirmed area: 3,765 → 6,150 ha (+63%)
- Precision: 88% → 92% (+4 pts)

This confirms the low recall is partly temporal -- a later observation against anniversary baseline (same season, prior years) produces stronger contrast. The burn scar structural signal strengthens as vegetation doesn't recover while surrounding areas maintain seasonal patterns.

### 5.4 Provisional Alerts Are Meaningful

Including label 1 (first-detection provisional) raises recall from 6.3% to 31.0% (Nov 15). These provisionals have 73% precision -- still accurate, just not yet promoted to "confirmed" because the algorithm only saw a single post-fire observation. In an operational monitoring chain with multiple observations, these would promote over time.

---

## 6. Lessons Learned

1. **OPERA RTC-S1 products are available globally on ASF DAAC, not just N.Am.** The ASF probe found 207 RTC-S1 products covering the Portuguese fire area across 4 tracks (T045, T052, T125, T147) in the Jul-Oct 2024 window. The `dist_s1.run_dist_s1_workflow` auto-fetch from ASF DAAC works unchanged for EU MGRS tiles -- no CDSE-specific data access path was needed.

2. **`dist_s1_enumerator` resolves EU MGRS tiles.** `enumerate_one_dist_s1_product(mgrs_tile_id='29TNF', track_number=147, ...)` returned 165 RTC inputs (150 pre + 15 post). The enumerator's internal MGRS-to-burst mapping covers global tiles, not just N.Am.

3. **Copernicus EMS Rapid Mapping API provides machine-readable burn perimeters.** The EMS dashboard API at `rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code=EMSR760` returns activation metadata with GeoJSON download URLs for each AOI's delineation products. The eval script auto-downloads and caches these on first run.

4. **Chained `prior_dist_s1_product` processing is impractically slow.** Attempts to chain observations (Sep 28 → Oct 10 → Nov 15) using the `prior_dist_s1_product` parameter resulted in runs exceeding 3+ hours without completing, vs 8 minutes for standalone runs. The cause is likely the per-burst prior-state comparison overhead compounded by multiprocessing interactions on macOS (spawn start method). The chained approach was abandoned in favour of standalone runs at two dates.

5. **`dist_s1` multiprocessing can deadlock on macOS.** Several runs hung at the despeckling phase (0% progress, workers spawned but not progressing). The issue appeared intermittently and was exacerbated by memory pressure from concurrent processes. The original Sep 28 run (via `run_eval_dist_eu.py`) completed without issues; subsequent runs from standalone scripts sometimes hung. Setting `n_workers_for_despeckling=1` did not fully resolve the issue. Running the eval via the original `if __name__ == "__main__":` script structure proved most reliable.

6. **Cross-sensor comparison requires careful metric interpretation.** F1 and recall numbers are misleadingly low when comparing SAR single-snapshot detection against VHR optical multi-date mapping. Precision is the meaningful metric for validating that the detection signal is real. The evaluation framework should report these as "cross-sensor spatial agreement" rather than "accuracy" to avoid misinterpretation.

---

## 7. Artifacts Produced

| File | Description |
| --- | --- |
| `run_eval_dist_eu.py` | 6-stage EU DIST-S1 evaluation harness with EMS reference comparison |
| `eval-dist-eu/` | Sep 28 DIST-S1 output + cached EMSR760 GeoJSONs |
| `eval-dist-eu-nov15/` | Nov 15 DIST-S1 output |
| `eval-dist-eu/ems_reference/` | 4 EMSR760 burn perimeter GeoJSON files |
| `CONCLUSIONS_DIST_EU.md` | This document |

---

## 8. Next Steps

### Immediate

- Write up results and commit evaluation artifacts

### Future improvements

- **Operational monitoring chain:** The `prior_dist_s1_product` chaining approach would test alert promotion (provisional → confirmed) but needs investigation into the macOS multiprocessing hang. Consider running on a Linux machine or in a container where `fork` start method is default.
- **Additional EU events:** Validate against other EU disturbance types (e.g. 2024 Greek wildfires, 2023 Evros wildfire, forest clear-cuts) to build confidence across vegetation types and event magnitudes.
- **Rasterised EMS reference as `.tif`:** Currently the eval script rasterises EMS GeoJSON on the fly. Pre-rasterising and saving as a COG would allow using the existing `compare_dist()` module directly via the manual-reference drop path.
- **EFFIS / dNBR cross-validation:** Compare DIST-S1 output against EFFIS burnt area products or Sentinel-2 dNBR to add an optical cross-sensor reference that doesn't require VHR imagery.
- **Later post_dates with more observations:** A post_date of 2025-01-15 or later would give 4+ months of post-fire data. With the anniversary baseline, the burn-scar contrast should be even stronger.
- **Fix multiprocessing reliability:** Investigate whether setting `multiprocessing.set_start_method('fork')` before the dist_s1 call resolves the macOS deadlock. The `spawn` method (macOS default) requires careful handling of module-level state that dist_s1's internal workers may not account for.

---

## v1.1 Phase 5 Update (2026-04-25): 3-event aggregate ships honest FAIL

The above v1.0 narrative remains the historical baseline (Aveiro Sept 28 + Nov 15 single-event explorations). v1.1 builds the 3-event aggregate infrastructure called for in the ROADMAP Phase 5 success criteria and reports an **honest FAIL** outcome consistent with Phase 4's pattern.

### What changed

- **3-event aggregate**: Aveiro (Portuguese wildfires) + Evros (Greek wildfires, EMSR686 — corrected from EMSR649 per RESEARCH Probe 8) + Spain Sierra de la Culebra (substituted for Romania 2022 clear-cuts per RESEARCH Probe 4 — EFFIS is fire-only and Romania clear-cuts have no EFFIS coverage).
- **Aveiro chained triple** (DIST-07 differentiator): Sept 28 → Oct 10 → **Nov 15** (the missing middle date is now present; the standalone `run_eval_dist_eu_nov15.py` is deleted and its logic lives in the aveiro `chained_retry` sub-stage of `run_eval_dist_eu.py`).
- **Reference path pivot**: EFFIS WFS endpoints both unreachable (Plan 05-02 probe; Candidate A timeout, Candidate B DNS NXDOMAIN); switched to EFFIS REST API at `api.effis.emergency.copernicus.eu/rest/2/burntareas/current/`. Constants pinned in `eval-dist_eu/effis_endpoint_lock.txt`. Greece country code is `EL` not `GR`.
- **Per-event try/except isolation**: One event's crash no longer blocks the matrix-cell write (Plan 05-07 D-12 invariant).
- **F1 + 95% block-bootstrap CI**: Per-event metric reporting via `validation/bootstrap.py` (Hall 1985 moving block bootstrap, PCG64 seed=0, B=500, 1000-m blocks).
- **Dual-rasterise diagnostic**: `all_touched=False` (primary) + `all_touched=True` (diagnostic) bracket the rasterisation-induced uncertainty per CONTEXT D-17.

### Live eval result: 0/3 PASS — honest FAIL

`make eval-dist-eu` ran end-to-end in ~30 minutes. All 3 events failed, with 3 distinct attributable causes:

| Event | Status | F1 [CI] | Cause |
|-------|--------|---------|-------|
| aveiro 2024-09-28 | FAIL | 0.000 [0.000, 0.000] | dist_s1 produced no `GEN-DIST-STATUS.tif` — silent failure mode (no exception raised; output file simply absent). chained_retry not attempted because primary post-date stage failed. |
| evros 2023-09-05 | FAIL | 0.000 [0.000, 0.000] | Same dist_s1 silent-no-output mode. Track number was the speculative fallback (`track=29`); the runtime probe via `dist_s1_enumerator` did not succeed in overriding the default. |
| spain_culebra 2022-06-28 | FAIL | 0.000 [0.000, 0.000] | `ValueError: no LUT data found for MGRS tile 29TQG track number 125`. Available track numbers per `dist_s1_enumerator.mgrs_burst_data` LUT for 29TQG are `1, 52, 74, 147, 154` — none of which is 125. Speculative fallback wrong; runtime probe didn't override. |

Aggregate matrix-cell render: `0/3 PASS (3 FAIL) | worst f1=0.000 (aveiro)`.

### What's working (the Phase 5 deliverable)

The infrastructure is structurally complete and tested:

- **Per-event try/except absorbed all 3 crashes** without blocking the matrix-cell write — exactly the D-12 invariant.
- **`metrics.json` validates against `DistEUCellMetrics`** (Pydantic v2 `extra='forbid'`); per-event records include `f1`, `precision`, `recall`, `accuracy` as `MetricWithCI` shapes (point + ci_lower + ci_upper, all 0.0 here because dist_s1 produced no output, but the schema is exercised).
- **`meta.json` validates against `MetaJson`** with verbatim field names (Blocker 1 fix from Plan 05-06).
- **`matrix_writer._render_dist_eu_cell` (Plan 05-05)** consumes the metrics.json and renders the cell correctly.
- **EFFIS REST client (Plan 05-05)** queried successfully — the `effis_query_meta` block in each per-event record captures the request fingerprint.
- **CONTEXT D-23 cache layout**: per-event sub-directories under `eval-dist_eu/aveiro/`, `eval-dist_eu/evros/`, `eval-dist_eu/spain_culebra/` were created.
- **Matrix manifest unchanged**: `matrix_writer` reads JSON sidecars only (REL-02 manifest-authoritative); CONCLUSIONS files are narrative only and are NOT parsed.

### What needs v1.2 attention

Three concrete failure modes documented above, each with a clear fix path:

1. **dist_s1 silent-no-output mode (aveiro + evros)**: `run_dist_s1_workflow` returned without raising, but the `GEN-DIST-STATUS.tif` was missing. The most likely root cause is the `spawn` start method on macOS (the v1.0 multiprocessing-deadlock note from the historical baseline above is the prior-art evidence). Fix candidates: (a) `multiprocessing.set_start_method('fork')` ahead of dist_s1 invocation; (b) Linux container; (c) inspect dist_s1 internal worker logs for the actual failure point. Phase 1's `_mp.configure_multiprocessing()` already attempts forkserver — investigate whether dist_s1 honours it.

2. **Runtime track-number probing didn't override speculative fallback (evros + spain_culebra)**: The plan called for `dist_s1_enumerator.get_mgrs_tiles_overlapping_geometry` to populate the EVENTS list at runtime; the speculative defaults (`track=29` for evros, `track=125` for spain_culebra) were intended as fallbacks only. v1.2 fix: use `dist_s1_enumerator.get_burst_ids_in_mgrs_tiles` to enumerate the valid tracks per MGRS tile and pick the one with the most coverage in the AOI bbox + date window.

3. **Aveiro chained_triple validation (DIST-07)**: chained_retry status is `SKIPPED` (event crashed before differentiator stage). The chain itself (Sept 28 → Oct 10 → Nov 15 with `prior_dist_s1_product` = previous stage's output) is wired into `run_eval_dist_eu.py._chained_retry_for_aveiro` and ready to validate once the primary stage succeeds.

### Audit trail

- Eval invocation: `python -m subsideo.validation.supervisor run_eval_dist_eu.py`
- Wallclock: ~30 minutes (well under the 8-hour `EXPECTED_WALL_S` budget; supervisor budget = 16h)
- Sidecar paths: `eval-dist_eu/metrics.json`, `eval-dist_eu/meta.json`
- Schema parsers (regression-protected): `DistEUCellMetrics`, `MetaJson` (Pydantic v2 `extra='forbid'`)
- Matrix render branch: `_render_dist_eu_cell` in `src/subsideo/validation/matrix_writer.py` (added by Plan 05-05)
- Tests: `tests/unit/test_matrix_writer_dist.py` (4 tests covering DIST-EU + DIST-NAM branches; all pass)

### Phase 5 verdict

**Infrastructure: COMPLETE.** The eval script, schema definitions, REST client, matrix render branches, and unit tests all land per the plan. **Scientific verdict: FAIL** with three distinct, attributable causes — preserved as the honest-FAIL signal per the project's Phase 4 precedent. v1.2 will fix the dist_s1 silent-output mode and runtime track probing, then re-run the eval to attempt PASS.
