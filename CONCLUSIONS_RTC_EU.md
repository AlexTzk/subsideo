# EU RTC-S1 Validation -- Session Conclusions

**Date:** (to be populated at end of eval run)
**Phase:** v1.1 Phase 2 -- RTC-S1 EU Validation
**Bursts:** 5 bursts across 5 terrain regimes (Alpine / Scandinavian / Iberian / TemperateFlat / Fire)
**Result:** (PASS / FAIL / MIXED -- to be populated)

> This document mirrors the structure of `CONCLUSIONS_RTC_N_AM.md` (v1.0 reference). The §5a "Terrain-Regime Coverage Table" and §5b "Investigation Findings" sections are Phase 2 additions required by RTC-01 + RTC-03. Plan 02-05 (post-eval-run) populates all placeholder values below.

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

Source: `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` (locked Plan 02-02). Plan 02-05 Task 2 populates all five rows uniformly from `eval-rtc-eu/metrics.json` post-run; no template-level burst_id is prescribed here.

| # | burst_id | regime | lat | UTM zone | sensing_utc | cached? | cached_source |
|---|----------|--------|-----|----------|-------------|---------|---------------|
| 1 | (Alpine burst -- populated from metrics.json post-run) | Alpine | ~46.35°N | (EPSG TBD) | (TBD) | No | -- |
| 2 | (Scandinavian burst -- populated from metrics.json post-run) | Scandinavian | ~67.15°N | (EPSG TBD) | (TBD) | No | -- |
| 3 | (Iberian burst -- populated from metrics.json post-run) | Iberian | ~41.15°N | (EPSG TBD) | (TBD) | No | -- |
| 4 | (Bologna burst -- populated from metrics.json post-run) | TemperateFlat | ~44.50°N | EPSG:32632 | (TBD) | Yes | `eval-disp-egms/input/` |
| 5 | (Portuguese fire burst -- populated from metrics.json post-run) | Fire | ~40.70°N | (EPSG TBD) | (TBD) | Yes | `eval-dist-eu/input/` |

### 2.2 Input Data

| Input | Source | Details |
|-------|--------|---------|
| S1 IW SLC SAFEs | ASF DAAC via `asf_search` + `earthaccess` (fresh) or harness.find_cached_safe (cached) | 3 fresh downloads (~12 GB) + 2 reuses from sibling eval cells |
| Precise orbits | `subsideo.data.orbits.fetch_orbit` (sentineleof) | Per-burst POEORB from ESA POD |
| GLO-30 DEM | `subsideo.data.dem.fetch_dem` (dem-stitcher) | Per-burst, cached in `eval-rtc-eu/dem/` |
| OPERA reference products | NASA Earthdata via `earthaccess.search_data(short_name='OPERA_L2_RTC-S1_V1', ...)` + harness.select_opera_frame_by_utc_hour | Per-burst, cached in `eval-rtc-eu/opera_reference/<burst>/` |

### 2.3 Processing Environment

(populate from `eval-rtc-eu/meta.json` after run)

---

## 3. What Was Run

### 3.1 Evaluation Script (`run_eval_rtc_eu.py`)

Script fork of `run_eval.py` generalised to a declarative 5-burst `BURSTS: list[BurstConfig]` loop (D-05). Per-burst try/except isolation (D-06) ensures one burst's failure doesn't block the remaining bursts. Resume-safe per-stage (D-08).

Invoked via: `make eval-rtc-eu` (Makefile line 28; supervisor-wrapped).

### 3.2 RTC Pipeline (`subsideo/products/rtc.py`)

Unchanged from N.Am. validation. Stages: runconfig generation → opera-rtc execution → COG normalisation → OPERA metadata injection → output validation. `_mp.configure_multiprocessing()` fires once per cell (Phase 1 D-14), not per burst.

### 3.3 Validation

`subsideo.validation.compare_rtc.compare_rtc(...)` unchanged from v1.0. Returns `RTCValidationResult` with nested `ProductQualityResult` (ssim) + `ReferenceAgreementResult` (rmse_db, correlation, bias_db, criterion_ids=['rtc.rmse_db_max', 'rtc.correlation_min']).

---

## 4. Bugs Encountered and Fixed

(populate from run log)

---

## 5. Final Validation Results

Per-burst comparison on the OPERA reference grid (bilinear resample to reference, dB-domain statistics).

| # | burst_id | regime | VV RMSE | VV r | VH RMSE | VH r | Status | Investigation? |
|---|----------|--------|---------|------|---------|------|--------|----------------|
| 1 | (Alpine) | Alpine | -- | -- | -- | -- | -- | -- |
| 2 | (Scandinavian) | Scandinavian | -- | -- | -- | -- | -- | -- |
| 3 | (Iberian) | Iberian | -- | -- | -- | -- | -- | -- |
| 4 | (Bologna) | TemperateFlat | -- | -- | -- | -- | -- | -- |
| 5 | (Portugal) | Fire | -- | -- | -- | -- | -- | -- |

**Aggregate:** `X/5 PASS`. Worst RMSE: `-- dB` on burst `--`. Worst r: `--` on burst `--`.

Matrix writer consumes `eval-rtc-eu/metrics.json` (`RTCEUCellMetrics`) and renders the `rtc:eu` cell as `X/N PASS` + ⚠ if any investigation was triggered.

### 5a. Terrain-Regime Coverage Table

**RTC-01 mandatory constraints (P1.1 prevention):**

| burst_id | regime | lat (°) | max_relief_m | cached? |
|----------|--------|---------|--------------|---------|
| (Alpine) | Alpine (>1000 m relief) | -- | -- | No |
| (Scandinavian) | Scandinavian (>55°N) | -- | -- | No |
| (Iberian) | Iberian arid | -- | -- | No |
| (Bologna) | TemperateFlat | -- | -- | Yes (`eval-disp-egms/input/`) |
| (Portugal) | Fire | -- | -- | Yes (`eval-dist-eu/input/`) |

**Constraint checks (populate post-eval):**

- All 5 regimes covered.
- ≥1 burst >1000 m relief: ☐ (confirm Alpine max_relief_m > 1000)
- ≥1 burst >55°N: ☐ (confirm Scandinavian lat > 55)

**P1.1 cached-bias prevention:** by construction, 2 of 5 bursts are cached-cheap (rows 4, 5) but 3 of 5 are fresh downloads (rows 1-3), and the two mandatory-constraint-satisfying bursts (Alpine + Scandinavian) are fresh downloads -- the cheapness bias documented in PITFALLS P1.1 is structurally prevented.

### 5b. Investigation Findings

Per D-13 trigger: any burst with RMSE ≥ 0.15 dB OR r < 0.999 gets a structured sub-section below. Plan 02-05 populates sub-sections for every flagged burst using the D-14 template (Observation / Top Hypotheses / Evidence). No sub-sections means no burst crossed the trigger -- a PASS result in the same sense as the N.Am. baseline.

**Triggered bursts:** (populate from eval-rtc-eu/metrics.json `per_burst[*].investigation_required == True`)

---

#### Template for a flagged burst (to be filled in per D-14):

##### 5b.X Burst `{burst_id}` -- {regime}

**Observation.** RMSE {X:.3f} dB (N.Am. baseline 0.045 dB), r {X:.4f} (baseline 0.9999), bias {X:.3f} dB. Trigger: `{investigation_reason}`.

**Top hypotheses:**
1. (pick from: "steep-relief DEM artefact" / "high-latitude DEM grid anomaly" / "OPERA reference version drift" / "subsideo output format drift" / "SAFE/orbit mismatch")
2. (hypothesis 2)
3. (hypothesis 3)

**Evidence:**
- Hypothesis 1: (one concrete data point -- DEM slope histogram, residual-vs-slope scatter, reference product_version field diff, or granule sensing-UTC delta)
- Hypothesis 2: (one concrete data point)
- Hypothesis 3: (one concrete data point)

---

## 6. Why the Result Is Correct

(populate post-eval: same algorithm core (opera-rtc) + same inputs (GLO-30 DEM, POEORB orbit) + same numerical core (isce3) → near-perfect agreement. Materially different RMSE on any burst would surface in §5b with a named attributable cause.)

---

## 7. Output Files

- `eval-rtc-eu/metrics.json` -- per-cell aggregate (`RTCEUCellMetrics`) consumed by matrix writer.
- `eval-rtc-eu/meta.json` -- provenance (git_sha, git_dirty, run_started_iso, run_duration_s, per_burst_input_hashes).
- `eval-rtc-eu/output/<burst_id>/*.cog.tif` -- per-burst subsideo RTC outputs (VV + VH).
- `eval-rtc-eu/opera_reference/<burst_id>/*.tif` -- per-burst OPERA references (cached).
- `eval-rtc-eu/dem/<burst_id>.tif` -- per-burst GLO-30 DEM (cached).
- `eval-rtc-eu/orbits/` -- cached POEORB .EOF files.

---

## 8. Source Files Changed During This Session

Phase 2 (planning → execution):

- `src/subsideo/validation/matrix_schema.py` -- added `BurstResult` + `RTCEUCellMetrics` (Plan 02-01).
- `src/subsideo/validation/criteria.py` -- extended `Criterion.type` Literal; added 2 `INVESTIGATION_TRIGGER` entries (Plan 02-01).
- `src/subsideo/validation/harness.py` -- added `find_cached_safe` helper (Plan 02-01).
- `src/subsideo/validation/__init__.py` -- re-exported `find_cached_safe` (Plan 02-01).
- `src/subsideo/validation/matrix_writer.py` -- added RTC-EU cell render branch (Plan 02-03).
- `run_eval_rtc_eu.py` -- NEW: declarative 5-burst eval script (Plan 02-04).
- `CONCLUSIONS_RTC_EU.md` -- NEW: this document, populated by Plan 02-05.
- `scripts/probe_rtc_eu_candidates.py` -- NEW: re-runnable probe script (Plan 02-02).
- `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` -- NEW: probe artifact (Plan 02-02).
