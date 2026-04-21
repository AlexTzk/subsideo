# GSD Milestone — Subsideo N.Am. / EU Validation Parity & Scientific PASS

## Context

`subsideo v1.0` has been exercised against five OPERA products across two continents. Two products (**RTC-S1**, **CSLC-S1**) PASS their N.Am. pass criteria. Two products (**DISP-S1**, **DIST-S1**) have structurally complete pipelines with open scientific questions. One product (**DSWx-S2**) has an EU structural pass but fails its F1 criterion due to a documented algorithm ceiling.

The project goal is a pipeline that produces results **as good as or better than** OPERA and EGMS across all of N.Am. and EU, for all five products. OPERA and EGMS are validators, not quality ceilings. Our bare minimum is to match them; our end-goal is to exceed them where we can do so with certainty. This milestone drives every product to an unambiguous per-region PASS, an honest FAIL with a named path forward, or a deferral with a dated unblock condition.

### A note on metrics and targets

Once a metric becomes a target it stops being a metric. This milestone applies that principle rigorously: **reference-agreement metrics** (our output vs OPERA / EGMS / JRC / EMS) are sanity checks that never tighten based on the reference's score; **product-quality gates** (self-consistency, ground-truth residuals, etc.) are the criteria that define whether the product passes. The two are reported separately and held to different standards. See each phase for how this split is applied.

### Explicitly out of scope

- Global expansion beyond N.Am. and EU (v2 milestone).
- ML-based replacements for threshold algorithms (e.g. DSWE → random forest).
- Adding new OPERA product classes (DSWx-S1, DSWx-HLS, etc.).
- Cross-burst mosaicking / multi-burst consistency checks (deferred to v2).
- Production unwrapper selection for DISP (spun out to a dedicated follow-up milestone — see Phase 3).

## Status snapshot (after validation sessions 2026-04-11 through 2026-04-17)

| Product  | N.Am. | EU | Blocker |
|---|---|---|---|
| RTC-S1   | **PASS** (RMSE 0.045 dB, r=0.9999) | not run | EU validation never executed |
| CSLC-S1  | PASS amplitude sanity check (r=0.79, RMSE 3.77 dB); phase unmeasurable across isce3 versions | not run | Cross-version phase comparison methodologically impossible; EU validation never executed; no self-consistency product-quality gate yet defined |
| DISP-S1  | FAIL (r=0.04, bias +23.6 mm/yr) | FAIL (r=0.32, bias +3.35 mm/yr) | PHASS unwrapping planar ramps on both continents — single root cause |
| DIST-S1  | STRUCTURALLY COMPLETE (Park Fire, no reference at time of session) | PASS cross-sensor precision 88–92% vs EMS | OPERA v0.1 sample product exists for Jan 2025 LA fires (T11SLT); not yet fetched or compared |
| DSWx-S2  | not run | FAIL F1 (0.7957 vs > 0.90) against JRC | DSWE thresholds fit on Landsat/N.Am., never recalibrated for S2 |

## Milestone goals

By milestone end, every cell above becomes **PASS**, **honest FAIL with named upgrade path**, or **deferred with dated unblock condition**. Specifically:

1. Every product has run end-to-end against at least one reference in both N.Am. and EU.
2. Every product that has a measurable product-quality gate in a region produces numbers against that gate, not n/a.
3. Reference-agreement numbers are reported separately from product-quality numbers.
4. The cross-cutting infrastructure fragility (numpy 2.x patches, macOS multiprocessing, missing deps, rio-cogeo imports) is resolved at the environment level.
5. The validation framework is consistent across products.
6. A one-command re-run path exists from cached intermediates for every eval.

The milestone is complete when a fresh clone can check out `main`, run `micromamba env create -f conda-env.yml`, run `make eval-all`, and produce the full results matrix (5 products × 2 regions × 2 criteria columns) with accompanying documentation.

---

## Phase 0 — Environment hygiene & validation framework consolidation

Validation sessions surfaced recurring infrastructure issues currently patched inline per-eval. Fixing them at the environment and framework level removes a class of flaky re-runs across the rest of the milestone.

### 0.1 Pin numpy < 2.0 in `conda-env.yml`

Four monkey-patches in `src/subsideo/products/cslc.py` exist purely to keep compass/s1-reader working under numpy 2.x. Pin numpy < 2.0, remove the patches, update unit tests. Document the sunset condition (upstream compass/s1-reader/isce3 all shipping numpy-2-compatible releases).

Acceptance: `pytest` passes; `run_eval_cslc.py` runs without any `_patch_*` calls in the code path.

### 0.2 Add `tophu` as a first-class dependency

Dolphin imports tophu internally even when `unwrap_method != SNAPHU`. Add tophu to `conda-env.yml`'s `pip:` block. Add a regression test asserting `from dolphin.unwrap import run` does not raise on a clean env.

Acceptance: fresh env install succeeds; `run_eval_disp.py` runs with no additional pip installs.

### 0.3 Centralise `rio_cogeo` imports

Three product files tripped over the rio-cogeo 7.x `cog_validate` move. Create `src/subsideo/_cog.py` exposing version-aware `cog_validate` / `cog_translate`. Replace all direct rio-cogeo imports. Add a non-mocked smoke test.

Acceptance: `rg "from rio_cogeo" src/` returns only the helper module.

### 0.4 Resolve macOS multiprocessing fragility

`dist_s1` deadlocks intermittently on macOS at despeckling; `opera-rtc` requires the `if __name__ == "__main__":` guard on spawn-start-method. Add `src/subsideo/_mp.py` with `_configure_multiprocessing()` that forces `fork` on macOS. Call at the top of each `run_*()` product entry point. Add a watchdog that aborts after 2× expected wall time with 0 throughput rather than hanging.

Acceptance: three consecutive fresh runs of `run_eval_dist.py` and `run_eval_dist_eu.py` succeed on macOS without hanging.

### 0.5 Consolidate the validation framework

Extract `subsideo.validation.harness` module containing:

- `select_opera_frame_by_utc_hour(frames, burst_utc_hour, burst_bbox)` — exact-hour preference + spatial bbox verification + ±1h fallback.
- `download_reference_with_retry(urls, out_dir, auth, backoff_cap_s=300)` — exponential-backoff retry for 429/OOM markers; generalises the CDSE pattern to Earthdata and any HTTPS source. Supports direct-download paths for non-CMR-indexed samples (e.g. OPERA CloudFront).
- `ensure_resume_safe(output_paths, checker_fn)` — resume-safe cache detection.
- `credential_preflight(required=['EARTHDATA', 'CDSE_OAUTH', 'CDSE_S3', 'CDSAPIRC'])` — clear setup URLs, not cryptic 401s.

Update all eval scripts to use the shared harness.

Acceptance: `run_eval_disp_egms.py` diff against `run_eval_disp.py` contains only reference-data differences, not plumbing differences.

### 0.6 Programmatic DEM bounds

`run_eval.py` currently uses hand-coded DEM bounds (`[-119.7, 33.2, -118.3, 34.0]` + 0.2° buffer). This is brittle for anything other than the SoCal eval. Replace with a helper that computes bounds from the burst ID via `opera_utils.burst_frame_db.get_burst_id_geojson()` plus a configurable buffer, matching the pattern used in `run_eval_disp.py`.

Acceptance: no hand-coded geographic bounds anywhere in the eval scripts; all bounds derived from burst/tile ID.

### 0.7 Make-target for the full eval matrix

Add a `Makefile` with `eval-{product}-{region}` targets, `eval-all`, `eval-nam`, `eval-eu`. `eval-all` writes `results/matrix.md` with all cells filled.

Acceptance: `make eval-all` on fresh env produces filled matrix; re-run on warm env completes in seconds.

**Phase 0 deliverables:** 5 code modules added / refactored, all eval scripts updated to use the shared harness, 1 Makefile, 1 regression test file, zero behavioural changes to product pipelines.

---

## Phase 1 — RTC-S1 EU validation

**N.Am. status: PASS. EU status: not run.**

OPERA RTC-S1 is near-global on ASF DAAC with coverage from January 2022 onward (confirmed both in ASF documentation and in practice during the DIST EU eval, which fetched 207 RTC products for the Portuguese fire area). EU reference products exist for arbitrary bursts. No methodology pivot is needed.

### What this phase validates

**Reference-agreement sanity check** (not a tightening target): does our chain produce numerically-reproducible output vs OPERA RTC-S1 across varied EU geographies? Pass criteria identical to N.Am. (RMSE < 0.5 dB, r > 0.99). If our chain is working as specified, we expect RMSE ~0.04 dB and r ~0.9999 everywhere — this is a *reproducibility-across-geographies* check, not a quality gate.

### What this phase does NOT validate

**Absolute radiometric accuracy.** RTC calls `opera-rtc`'s `rtc.rtc_s1.run_parallel()` — the same function that generates the reference. The comparison measures floating-point drift between chain invocations, not algorithmic quality. A proper quality gate (corner-reflector comparison against known radar cross-section) is scoped in Future Work.

This framing means RTC's milestone closure is: "numerically reproducible across varied N.Am. and EU terrain regimes; absolute accuracy vs ground truth is future work." Not a workaround — an honest scope statement.

### 1.1 Confirm OPERA RTC-S1 coverage on candidate EU bursts

Probe ASF DAAC for 3–5 EU bursts across terrain regimes:
- Alpine steep relief (burst from the Eastern Alps or Dolomites).
- Po plain flat temperate (reuse Bologna `t117_249422_iw2` — cached from DISP EGMS eval).
- Iberian arid (burst in central Meseta — also a candidate for Phase 2).
- Scandinavian boreal (burst over central Finland or northern Sweden).
- Portuguese wildfire footprint (any burst from the DIST EU eval — cached RTC inputs already available).

Budget: 1 day for probing + burst selection.

### 1.2 Author `run_eval_rtc_eu.py`

Fork `run_eval.py`. Run against each confirmed burst. Reuse cached DEM / orbits / SAFEs wherever available (Bologna and Portugal candidates should be essentially free).

### 1.3 Pass criteria

Same as N.Am.: RMSE < 0.5 dB, r > 0.99 per burst. If all 3–5 bursts PASS with RMSE in the 0.04–0.1 dB range consistent with N.Am., the EU reproducibility claim is validated. If any burst shows materially different RMSE, investigate — this would indicate a region-dependent bug in DEM fetch / orbit fetch / SAFE handling.

**Phase 1 risks:** Low. RTC is deterministic and the N.Am. eval nailed the criteria with headroom.

**Phase 1 deliverables:** `run_eval_rtc_eu.py`, `CONCLUSIONS_RTC_EU.md`, cached `eval-rtc-eu/` per burst, updated matrix with cell 1:EU filled.

---

## Phase 2 — CSLC-S1: self-consistency product-quality gate + EU validation

**N.Am. status: amplitude reference-agreement PASS (r=0.79, RMSE 3.77 dB); phase unmeasurable.**
**EU status: not run.**

Phase-coherent comparison across isce3 major versions is methodologically impossible — coherence against OPERA reference is 0.0003 even after removing every known correction. This is not a bug; it's a property of isce3 that subsideo cannot work around. What CSLC needs is a separate **product-quality gate** that doesn't depend on the reference's isce3 version.

### What this phase validates

Two independent tracks:

**Reference-agreement sanity check** (OPERA CSLC amplitude): r > 0.6, RMSE < 4 dB. Both continents. Does not tighten. If a future subsideo version lands farther from OPERA than 4 dB RMSE we investigate, but we do not fail the pipeline — it could be a genuinely better calibration. This check confirms our geocoding places amplitude at correct ground locations within cross-version-expected bounds. Phase is not reported.

**Product-quality gates** (separate per continent because reference data differ):
- Both continents: **self-consistency interferometric coherence > 0.7** on stable terrain across sequential 12-day interferograms formed from our own chain. Stable terrain defined as ESA WorldCover class 60 (bare/sparse vegetation) + slope < 10°.
- EU: **residual mean velocity < 5 mm/yr** at EGMS L2a stable-reference PS points within the burst footprint.
- US: **residual mean velocity < 5 mm/yr** at OPERA-CSLC-derived stable pixels within the burst footprint (stability defined by the WorldCover + slope mask above).

The 5 mm/yr bar is set for a 6-month stack. Target to tighten as stacks lengthen beyond 6 months — tracked in Future Work.

### 2.1 Self-consistency eval on SoCal (existing cached stack)

Author `run_eval_cslc_selfconsistency.py`:
- Process 15 dates from burst `t144_308029_iw1` (cached SAFEs from DISP N.Am. eval).
- Form 14 sequential 12-day interferograms through our chain.
- Mask to stable terrain (WorldCover class 60 + slope < 10°).
- Compute mean coherence; assert > 0.7.
- Compute residual mean velocity on OPERA-CSLC-derived stable pixels; assert < 5 mm/yr.
- Write `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md`.

### 2.2 AOI selection for the new US burst (Mojave Desert region)

Add a second US self-consistency point in a different terrain regime. Primary candidate: **Mojave Desert — Coso / Searles Valley area (Eastern California)**. Fallback list: Pahranagat Valley (SE Nevada), Amargosa Valley, Hualapai Plateau (NW Arizona).

Selection rule: chosen AOI must have OPERA CSLC reference coverage AND documented stability in the published InSAR literature. Iterate through fallbacks until one passes both tests. If all fail, surface as a Phase 2 blocker.

Author `run_eval_cslc_selfconsistency_mojave.py` following the same structure as §2.1.

### 2.3 EU CSLC validation (Iberian Meseta)

Primary candidate: **Iberian Meseta — bedrock/sparse-vegetation burst north of Madrid**. Fallback list: Alentejo (interior Portugal), Massif Central (southern France).

Selection rule: chosen AOI must have OPERA CSLC reference coverage AND EGMS L2a stable-reference PS coverage within the burst footprint.

Author `run_eval_cslc_eu.py`:
- OPERA CSLC amplitude sanity check (r > 0.6, RMSE < 4 dB).
- Self-consistency coherence > 0.7 on stable terrain.
- EGMS L2a stable-point residual velocity < 5 mm/yr.

### 2.4 Cross-version phase methodology doc

Consolidate the cross-version phase findings from `CONCLUSIONS_CSLC_N_AM.md` §5 (diagnostic evidence: removal of carrier, flattening, both, still yields zero coherence) into `docs/validation_methodology.md`. Future users will attempt phase comparisons and should find this documented prominently rather than buried in a per-session conclusions file.

**Phase 2 risks:** Low-medium. Self-consistency should be clean on the cached N.Am. stack. Risk is finding our chain has a subtle internal inconsistency that cross-version comparison masked — if so, surfacing it is the desired outcome.

**Phase 2 deliverables:** 3 new eval scripts, 3 new CONCLUSIONS documents, 1 methodology doc, updated matrix with product-quality and reference-agreement columns filled for cells 2:NAM (both SoCal and Mojave) and 2:EU.

---

## Phase 3 — DISP-S1: native-resolution validation + comparison adapter

**N.Am. status: FAIL. EU status: FAIL. Same root cause both continents: PHASS planar ramps.**

The central design decision for this phase: **downsampling to match OPERA's 30 m grid is a validation-comparison choice, not a production choice.** Subsideo's native CSLC resolution is 5 × 10 m (OPERA spec) and the product's scientific contribution is producing displacement at that native resolution. Native resolution stays the production default.

### What this phase validates

**Product-quality gate** (native resolution): self-consistency on stable terrain. Not a reference comparison.

**Reference-agreement sanity checks** (via comparison adapter):
- vs OPERA DISP-S1 on N.Am.: r > 0.92, bias < 3 mm/yr at OPERA's 30 m grid.
- vs EGMS L2a on EU: r > 0.92, bias < 3 mm/yr at EGMS PS points.

Neither reference-agreement criterion tightens based on the reference's score.

### What this phase explicitly does NOT do

**Pick a production unwrapper.** That decision is spun out to a dedicated follow-up milestone ("DISP Unwrapper Selection") because it is a research task with multiple failure modes and deserves its own time-box. This milestone ships DISP with the *current* PHASS configuration, honestly reports self-consistency + reference-agreement numbers (both likely FAIL), and hands off unwrapper research to the follow-up.

**Justification for spinning out:** unwrapper research has genuine design depth — PHASS+deramping, SPURT at native resolution, tophu-SNAPHU tiling, dropping production resolution to 20 × 20 m as a fallback, custom deramping pre-inversion. These are distinct workstreams with different compute costs and different failure modes. Choosing between them based on the milestone's FAIL numbers will be more productive than pre-committing to one here.

### 3.1 Build the comparison adapter

`subsideo.validation.compare_disp.prepare_for_reference(native_velocity, reference_grid)`:
- Takes our native 5 × 10 m velocity raster.
- Multilooks to match reference grid (30 m for OPERA DISP, point-sample for EGMS L2a PS).
- Returns velocity on the reference grid for metric computation.
- Never writes back to the product. Documented as validation-only infrastructure.

Replaces the ad-hoc bilinear reprojection currently in `run_eval_disp.py` Stage 9.

### 3.2 Self-consistency product-quality gate

Same methodology as Phase 2.1:
- Sequential 12-day interferograms from our chain.
- Mean coherence > 0.7 on stable terrain (WorldCover class 60 + slope < 10°).
- Residual mean velocity < 5 mm/yr on ground-truth stable points.
- US: use OPERA-CSLC-derived stable pixels (same as Phase 2.1/2.2).
- EU: use EGMS L2a stable-reference PS points.

This is the criterion that defines whether DISP passes as a product, independent of reference grid.

### 3.3 Re-run N.Am. and EU from cached CSLC stacks

Both runs use cached CSLCs (~40 GB cached for SoCal, ~40 GB cached for Bologna). The pipeline re-runs from Stage 7 (DISP workflow) through Stage 9 (comparison). Expected wall time: ~30 minutes per continent.

Each run reports:
- Product-quality gate result (self-consistency, 5 mm/yr residual).
- Reference-agreement result (r, bias at reference grid).

With the current PHASS unwrapper and the ramp issue still present, both product-quality and reference-agreement are expected to FAIL. The value of running is: a clean baseline FAIL number against current unwrapper, and exercise of the comparison adapter infrastructure that the follow-up unwrapper milestone will need.

### 3.4 Scope the follow-up milestone

Produce a one-page scoping brief for the DISP Unwrapper Selection milestone at the end of Phase 3, grounded in the fresh FAIL numbers. The brief should list candidate approaches (PHASS+deramping, SPURT native, tophu-SNAPHU tiled, 20×20 m fallback multilook) with a success criterion for each. This brief is a Phase 3 deliverable — not a Phase 3 gate.

**Phase 3 risks:** Low (now that unwrapper research is out of scope). The milestone exit for DISP is "pipeline runs, framework validated, honest FAIL reported, follow-up milestone scoped." That's achievable regardless of unwrapper outcomes.

**Phase 3 deliverables:** comparison adapter in validation module, self-consistency gate, re-run both continents from cached CSLCs, 2 updated CONCLUSIONS, 1 follow-up milestone scoping brief. Cells 3:NAM and 3:EU flip to "FAIL with named follow-up milestone."

---

## Phase 4 — DIST-S1: OPERA v0.1 sample comparison + EU tightening

**N.Am. status: STRUCTURALLY COMPLETE at the time of the session; OPERA v0.1 sample now identified.**
**EU status: PASS cross-sensor precision 88–92%.**

At the time of the DIST N.Am. session, no OPERA DIST-S1 reference was publicly discoverable via CMR / ASF DAAC. An OPERA v0.1 pre-operational sample has since been located for MGRS tile **T11SLT** (Southern California, covering the January 2025 LA fires — Palisades and Eaton), acquisition 2025-01-21, produced 2025-08-19. The sample lives on OPERA's CloudFront CDN, not on the ASF DAAC operational archive.

This changes Phase 4's shape. N.Am. flips from "deferred pending publication" to "quantitative comparison against v0.1 sample, with unblock condition to re-run against operational reference when it ships."

### Key caveats for the v0.1 comparison

1. **Pre-operational.** Algorithm or output format may change before operational publication. Any F1 is a snapshot, not a commitment to the operational product's F1.
2. **Not CMR-searchable.** Requires direct-download from CloudFront, not via earthaccess. Uses the `download_reference_with_retry` helper added in Phase 0.5.
3. **Single-tile comparison.** One tile (T11SLT), one post-date. Not a multi-observation confirmation-over-time test.
4. **Different tile from existing Park Fire eval.** Park Fire ran on 10TFK; this runs on T11SLT. Requires a new subsideo pipeline invocation on the LA tile — roughly 30 minutes of compute.
5. **Configuration may differ from dist-s1 2.0.13 defaults.** OPERA may have produced v0.1 with internal thresholds or pre-image strategies that differ from the current dist-s1 release. Low F1 must first rule out config drift before being interpreted as a subsideo FAIL.

### 4.1 N.Am. LA fires comparison against OPERA v0.1

- Fetch OPERA v0.1 T11SLT sample from `d2pn8kiwq2w21t.cloudfront.net/documents/OPERA_L3_DIST-ALERT-S1_T11SLT_20250121T015030Z_20250819T130204Z_S1_30_v0.1.zip`. Cache under `eval-dist/opera_reference/v0.1_T11SLT/`.
- Re-run subsideo pipeline on MGRS tile **T11SLT**, post-date **2025-01-21**, track matching the OPERA sample's ascending/descending pass.
- Before running comparison: dump OPERA v0.1's production metadata and cross-reference against dist-s1 2.0.13's default config. Document any deltas.
- **Config-drift gate:** if the metadata dump shows OPERA v0.1 was produced with materially different processing parameters than dist-s1 2.0.13 defaults (confirmation-count threshold, pre-image strategy, post-date buffer, or similar), **skip the quantitative comparison.** Preserve the fetched v0.1 sample and metadata in `eval-dist/opera_reference/v0.1_T11SLT/` for future reference, report "N.Am. DIST deferred pending operational reference publication" in the matrix, and continue monitoring per §4.2. A comparison against a mis-configured reference produces numbers that could be misread either way.
- If configs match materially: compute F1 / precision / recall / accuracy via existing `compare_dist()` module.
- **Criteria retained as originally specified:** F1 > 0.80, accuracy > 0.85. **No tightening toward v0.1's score.** If our F1 exceeds v0.1's self-F1 we report that as an "as good or better" outcome.
- Report in `CONCLUSIONS_DIST_N_AM_LA.md`, clearly labelled as "vs OPERA v0.1 pre-operational sample."

### 4.2 Monitoring for operational DIST-S1 publication

Add a CMR probe to `make eval-dist-nam` that queries for `OPERA_L3_DIST-ALERT-S1_V1` (and naming variations). If operational publication is found, proceed to operational reference comparison and supersede the v0.1 result. If not, v0.1 comparison is what ships.

Monthly calendar reminder to check publication status. Not blocking milestone unless publication lands mid-milestone.

### 4.3 EU: EFFIS same-resolution-optical cross-validation

The existing EU DIST run against Copernicus EMS VHR optical has 88–92% precision and 3.7–6.3% recall, which is expected for single-snapshot SAR vs multi-date VHR optical. Add a same-resolution-optical cross-check: **EFFIS burnt area products** (S2 dNBR-derived, 10–20 m resolution — roughly matched to DIST-S1's 30 m).

- Author `run_eval_dist_eu_effis.py` as a parallel eval against `eval-dist-eu`'s cached subsideo output.
- Query EFFIS for Aveiro/Viseu 2024 wildfire burnt-area products.
- Compute metrics against EFFIS perimeters.
- **Genuine recall criterion applies here:** recall > 0.50 against EFFIS. Precision > 0.70. This is an apples-to-apples same-resolution-optical comparison, so the precision-first framing used for EMS doesn't apply — both metrics are legitimate.
- Report in a new section of `CONCLUSIONS_DIST_EU.md` labelled "Same-resolution optical cross-validation."

### 4.4 Additional EU DIST events

Expand from one EU event to three across vegetation types:
- 2024 Portuguese wildfires (Mediterranean oak/pine — already done).
- 2023 Evros wildfires, Greece (Mediterranean pine, larger event; EMSR649).
- 2022 Romanian forest clear-cuts (temperate, anthropogenic disturbance).

Each event adds ~30 minutes compute + 1 hour write-up. Aggregate in `CONCLUSIONS_DIST_EU.md`.

### 4.5 Chained `prior_dist_s1_product` investigation

Once Phase 0.4 lands (fork start method on macOS), retry the chained approach from the DIST EU session (Sep 28 → Oct 10 → Nov 15). If Phase 0.4 resolves the hang, include one chained run in `run_eval_dist_eu.py` comparing alert promotion (provisional → confirmed) vs current standalone runs. If still hanging, file upstream with dist-s1 maintainers.

### 4.6 Criteria

**No tightening toward whatever OPERA v0.1 happens to score.** Criteria (F1 > 0.80, accuracy > 0.85) retained as originally specified. If post-reference-comparison runs indicate the criteria are consistently met with significant margin across multiple AOIs, tightening toward a *product-quality target* (not toward OPERA's score) can be considered in a future milestone once we have multiple data points.

**Phase 4 risks:** Low-medium. Main risk is v0.1 sample using a processing config materially different from dist-s1 2.0.13, which could produce misleading low F1. Mitigation: §4.1 config-drift check before running comparison.

**Phase 4 deliverables:** LA v0.1 comparison, CMR-probe monitoring, EFFIS same-resolution cross-validation, 2 additional EU events, updated CONCLUSIONS. Cells 4:NAM flips to "PASS/FAIL vs v0.1" (whichever it ends up); 4:EU tightens from cross-sensor-only to cross-sensor + same-resolution-optical.

---

## Phase 5 — DSWx-S2: N.Am. validation + EU recalibration

**N.Am. status: not run. EU status: FAIL F1 (0.7957 vs > 0.90).**

DSWE-family threshold algorithms have a documented architectural ceiling at F1 ≈ 0.92 globally. This is a property of the threshold-test algorithm class, not of our implementation. Closing the gap beyond that ceiling requires an algorithm class change (random forest on band composites is the standard upgrade path) and is explicitly out of scope.

### What this phase validates

**Reference-agreement** (which is also the product criterion for DSWx, since there's no independent product-quality gate for surface water extent — JRC *is* the reference against which "correct surface water extent" is defined):
- F1 > 0.90 against JRC Monthly History. Both continents. **No relaxation.**

If we land at 0.88 post-recalibration, that's a FAIL. We report it as a FAIL with the DSWE ceiling documented and ML-replacement as the named upgrade path. A FAIL with a known cause and a named fix is more useful than a PASS with a moved goalpost.

### 5.1 N.Am. DSWx-S2 validation

DSWE thresholds are fit for N.Am. Running there should produce F1 close to the calibration ceiling (~0.90) and serves as the positive control that the pipeline is working correctly.

Author `run_eval_dswx_nam.py`. AOI candidates:
- Lake Tahoe, California (deep lake, clean reference, Sierra snowmelt).
- Lake Pontchartrain, Louisiana (brackish, shoreline wetland, class-3 stress test).

Pick one. Same 9-stage harness as `run_eval_dswx.py`. Budget: 1 day.

Expected F1: 0.85–0.92 if the calibration is N.Am.-optimal. Below 0.85 would indicate a regression in our BOA offset / Claverie cross-cal logic.

### 5.2 EU recalibration — fit set construction

Scoped to EU-only per prior scope decisions (global recalibration is v2).

**AOI research is a first-class sub-task of this phase.** The 6 AOIs below are a starting list covering the biome diversity that needs to be represented (Mediterranean reservoir, Atlantic estuary, boreal lake, Pannonian plain, Alpine valley, Iberian summer-dry). Before committing compute, research and select the best specific AOI in each biome based on:
- JRC Monthly History reference quality over the candidate (avoid AOIs where JRC itself is known to be noisy, e.g. sparse cloud-free observations, labelling ambiguity at shoreline).
- S2 cloud-free scene availability in both wet and dry seasons.
- Water body size and type diversity within the AOI (avoid duplication with Balaton's lake-plus-wetland signature).
- Absence of known algorithm failure modes (glacier/frozen lake, heavy turbid water, dominant mountain shadow).

Starting list to research (swap specific water bodies as research dictates):
- Mediterranean reservoir, Iberian interior (e.g. Embalse de Alcántara, Orellana, Valdecañas).
- Atlantic estuary (e.g. Tagus, Shannon, Gironde).
- Boreal lake (e.g. Päijänne, Inari, Vänern).
- Pannonian plain (Balaton — already validated, kept as held-out test set).
- Alpine valley (e.g. Lake Geneva, Como, Constance).
- Iberian summer-dry (e.g. Guadalquivir estuary, Doñana wetland, Ebro delta).

Per selected AOI: one cloud-free S2 L2A scene in wet-season and one in dry-season = 12 (AOI, scene) pairs. Download via existing `CDSEClient.download_safe`. Cache under `eval-dswx-fitset/`. Pull matching JRC Monthly History tiles.

Budget: AOI research + fit set construction 3–4 days. Storage: ~15 GB.

### 5.3 Grid search

Joint grid over DSWE thresholds:
- `WIGT` (MNDWI water index): default 0.124, search [0.08, 0.20] step 0.005.
- `AWGT` (AWEI): default 0.0, search [−0.1, +0.1] step 0.01.
- `PSWT2_MNDWI`: default −0.5, search [−0.65, −0.35] step 0.02.

Optimise mean F1 across 12 fit-set pairs. Hold Balaton out as test set.

Deliverables: `scripts/recalibrate_dswe_thresholds.py`, frozen constants in `src/subsideo/products/dswx.py`, reproducibility notebook `notebooks/dswx_recalibration.ipynb`.

### 5.4 Re-run EU eval with recalibrated thresholds

Re-run `run_eval_dswx.py` with new constants. Report F1.

### 5.5 Reporting — no criterion adjustment

F1 > 0.90 is the bar. **It does not move.** Phase 5 reports exactly what F1 the recalibration achieves:
- F1 ≥ 0.90: PASS.
- 0.85 ≤ F1 < 0.90: FAIL with named upgrade path (DSWE ceiling documented; ML replacement tracked in Future Work).
- F1 < 0.85: FAIL with investigation needed (something went wrong in recalibration — fit-set quality, bug in grid search, etc.).

No threshold adjustment "to make the number pass." The milestone reports where we land against the original bar.

**Phase 5 risks:** Medium. Calibration ceiling is well understood but fit-set AOI quality can cap F1 below expectations. Mitigation: review fit set before committing compute.

**Phase 5 deliverables:** N.Am. eval, 12 fit-set scenes, recalibration script + notebook, updated threshold constants, updated EU eval with honest F1 result. Cell 5:NAM filled; 5:EU flips to PASS (or to FAIL with DSWE ceiling + ML path documented).

---

## Phase 6 — Results matrix and release readiness

### 6.1 Automated results matrix

`make eval-all` writes `results/matrix.md` with cells organised as product × region × (product-quality, reference-agreement). Example layout:

| Product | Region | Product-quality gate | Reference-agreement |
|---|---|---|---|
| RTC | N.Am. | future work (CR validation) | RMSE 0.045 dB PASS |
| RTC | EU | future work | per-burst table PASS |
| CSLC | N.Am. SoCal | coherence 0.XX, residual X mm/yr PASS | r 0.79 / RMSE 3.77 dB sanity |
| CSLC | N.Am. Mojave | ... | ... |
| CSLC | EU Meseta | coherence + EGMS 5 mm/yr | r / RMSE |
| ... | ... | ... | ... |

Commit `results/matrix.md` as the canonical project status artifact.

### 6.2 `docs/validation_methodology.md`

Consolidate the four methodological findings scattered across CONCLUSIONS documents:
- Cross-version phase comparison is impossible across isce3 major versions.
- Cross-sensor comparison requires precision-first metric interpretation.
- OPERA frame selection must match exact UTC hour AND spatial footprint.
- DSWE-family F1 ceiling ≈ 0.92 is architectural, not a tuning problem.

Also document the product-quality vs reference-agreement criteria distinction explicitly, so future contributors don't collapse them.

### 6.3 Pre-release audit

Run full `make eval-all` on a freshly-cloned repo on a freshly-provisioned env. Target: homelab TrueNAS GPU dev container (Linux fork start method, cross-platform sanity check against M3 Max). Verify:
- All cells produce numbers.
- Full `make eval-all` on cold env completes under 12 hours.
- `make eval-all` on warm env completes under 10 minutes.

**Phase 6 deliverables:** automated matrix, methodology doc, pre-release audit report.

---

## Dependencies and ordering

```
Phase 0 (environment)               ← do first
  ├── Phase 1 (RTC EU)              ← needs 0.5 harness, 0.6 bounds
  ├── Phase 2 (CSLC self-consist + EU)  ← needs 0.1 numpy, 0.5 harness
  ├── Phase 3 (DISP adapter + re-run)   ← needs 0.2 tophu, 0.4 mp, 0.5 harness
  ├── Phase 4 (DIST LA + EU)        ← needs 0.4 mp, 0.5 harness (CloudFront path)
  └── Phase 5 (DSWx)                ← needs 0.3 rio-cogeo, 0.5 harness
Phase 6 (matrix + release)          ← needs all of 1–5
```

Phases 1–5 parallelise post-Phase-0. Single developer: serial. Two developers: split DISP+DSWx from the rest.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OPERA v0.1 sample uses a config materially different from dist-s1 2.0.13, producing misleading low F1 | Medium | Medium | §4.1 config-drift check before running comparison. |
| DSWx recalibration lands at F1 0.85–0.89 | Medium-High | Low (honest FAIL acceptable) | Fit-set quality review before compute commit. |
| numpy < 2.0 pin breaks some transitive dependency | Low | Medium | Run full test suite on pinned env before removing patches. |
| macOS fork still deadlocks in some corner | Low | Medium | Fallback to Linux TrueNAS container. |
| EU OPERA RTC coverage sparse for some candidate burst | Low | Low | Phase 1.1 has 5 candidates across regimes; pick the ones that work. |
| Mojave / Meseta primary AOIs fail stability/coverage test | Medium | Low | Documented fallback lists in Phase 2.2 and 2.3; iterate until one passes. |
| DISP follow-up milestone turns out larger than scoped | Medium | Low for this milestone | Out of scope — this milestone ships with honest FAIL and hand-off. |

## Success criteria for milestone closure

1. `micromamba env create -f conda-env.yml` succeeds on a clean machine.
2. `pytest` passes.
3. `make eval-all` writes `results/matrix.md` with all cells filled.
4. Every cell is either PASS, FAIL-with-named-upgrade-path, or deferred-with-dated-unblock-condition.
5. `docs/validation_methodology.md` covers the four methodological findings plus the product-quality / reference-agreement distinction.
6. No runtime monkey-patches in `src/subsideo/products/*.py`.
7. DISP Unwrapper Selection follow-up milestone brief exists as a Phase 3 deliverable.

## Estimated effort

- Phase 0: 3–4 days.
- Phase 1: 2 days.
- Phase 2: 4–5 days (3 AOIs: SoCal self-consist + Mojave + Meseta).
- Phase 3: 3 days (scope contracted — no unwrapper research).
- Phase 4: 3–4 days (LA v0.1 comparison + EFFIS + 2 events).
- Phase 5: 5–7 days (fit set + grid search).
- Phase 6: 2 days.

**Total single-developer estimate:** 22–27 working days (4.5–5.5 weeks).

---

## Future work

Captured here as a first-class section rather than scattered footnotes. These are real follow-ups, not abandonment — each has a named trigger for when it should open as its own milestone.

### RTC

- **Corner-reflector absolute radiometric accuracy validation.** Identify accessible CR networks (DLR Kaufbeuren, ESA European calibration sites), match to S1 burst footprints, extract RTC pixel values, compare to published or measured RCS. This is the validation that can actually claim "better than OPERA" on absolute accuracy grounds. Trigger: after this milestone closes, scope as its own mini-milestone.
- **Time-series radiometric stability.** Process the same burst over 12 months, measure backscatter stability over known-stable targets (rock outcrops, dense urban), compare to OPERA CalVal published stability numbers. Cheaper alternative to CR work and catches orbit/DEM inconsistencies a single-scene comparison misses. Pair with CR work or treat as standalone scoping choice.
- **Upstream bug filings:**
  - opera-rtc timestamp-mismatch bug (Bug 5 in N.Am. RTC conclusions) — minimal repro to upstream, keep our workaround.
  - `load_parameters()` not called automatically after `load_from_yaml()` — upstream PR candidate.
- **Parameterise COG compression** in `ensure_cog()` (currently hardcoded DEFLATE + 5 overviews). ZSTD or LERC may be preferred for cloud-native workflows.

### CSLC

- **GNSS-residual comparison** via Nevada Geodetic Laboratory stations. Requires: (a) which NGL stations fall inside candidate burst footprints; (b) GNSS ENU → S1 LOS projection (standard, via MintPy `gps2los`); (c) defensible residual magnitudes. The 5 mm/yr bar used in this milestone is above typical NGL velocity uncertainty, so GNSS residual would be a tighter gate. Trigger: after this milestone's self-consistency results are in, to calibrate expectations for the tighter bar.
- **Tighten residual velocity bar** from 5 mm/yr as stacks lengthen beyond 6 months. 12+ month stacks typical in InSAR literature support 1–2 mm/yr residuals on stable PS.
- **Tighten amplitude thresholds** (r, RMSE) — only after multiple data points are accumulated, and only if tightening targets a product-quality bar rather than matching OPERA's score more closely.

### DISP

- **Unwrapper Selection milestone** (spun out of Phase 3). Scope brief is a Phase 3 deliverable.
- **ERA5 tropospheric correction** via `pyaps3`. Opportunistic — Bologna's 60 mm/yr bias is inconsistent with ERA5 being dominant. Fold into Unwrapper Selection milestone as a secondary investigation.
- **Multi-burst consistency** (mosaicking) — trigger for v2 global work.

### DIST

- **Operational monitoring chain** (`prior_dist_s1_product` chaining to test alert promotion provisional → confirmed). Partially unblocked by Phase 0.4 (macOS mp fix); full operational chain design is post-milestone.
- **Upstream `post_date_buffer_days` default PR** — changed from 1 to 5 in dist_s1. Non-blocking.
- **Raise `validate_dist_product` bar** — currently does lightweight COG/UTM/pixel checks; could validate full OPERA product-spec metadata via `dist_s1.data_models.output_models.DistS1ProductDirectory`.
- **Re-run against operational OPERA reference** when it ships (CMR-monitored in Phase 4.2).

### DSWx

- **ML-replacement algorithm path** (random forest on band composites). DSWE-family F1 ceiling ≈ 0.92 globally; exceeding requires algorithm class change. Named as the upgrade path in Phase 5's FAIL reporting. Trigger: if/when F1 > 0.92 becomes a product requirement.
- **Global recalibration** (expand fit set from 6 AOIs to 20–30 spanning additional biomes — tropical savanna, rainforest, desert, monsoon, subtropical, cold arid). Trigger: v2 global milestone.
- **Turbid water / frozen lake / mountain-shadow / tropical-haze handling** — documented as algorithm limits at global scope. Trigger: if specific downstream user requires one of these.

### Cross-cutting (v2 global milestone)

- Burst database globalisation (EU-only → full ~1.5 M bursts).
- Validation framework generalisation to GNSS / tide-gauge / literature-derived references for regions without OPERA or EGMS equivalents.
- Data access scaling (CDSE rate limits at global cadence → AWS Open Data / ASF fallback).

---

## Decisions recorded during milestone refinement

All four open questions from the initial draft have been resolved:

1. **Phase 2 AOI fallback behaviour:** exhaust the 3-candidate fallback list per region before surfacing as a Phase 2 blocker. Cross that bridge when we get there.

2. **Phase 4.1 config-drift behaviour:** if OPERA v0.1 metadata shows material configuration deltas vs dist-s1 2.0.13, **skip the comparison and wait for operational publication.** The v0.1 sample is still fetched and preserved for future reference, but the quantitative comparison is deferred. Reflected in §4.1.

3. **Phase 5 fit-set AOIs:** no pre-selected preferences. AOI research is a first-class sub-task of Phase 5 — select based on JRC reference quality + cloud-free scene availability + absence of known algorithm failure modes. Reflected in §5.2.

4. **Publication:** no Medium-post draft queued. Publication decision deferred until the library is considered for going public, which will depend on how the milestone lands. No publication deliverable in this milestone.