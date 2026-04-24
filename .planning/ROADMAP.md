# Roadmap: subsideo

## Overview

subsideo builds a Python library that produces OPERA-equivalent SAR/InSAR geospatial products (RTC-S1, CSLC-S1, DISP-S1, DSWx-S2, DIST-S1) over EU areas of interest. v1.0 shipped the five product pipelines, CDSE/ASF data access, EU burst database, Typer CLI, and a validation framework. v1.1 is a **validation-hardening milestone** that drives every product to an unambiguous per-region PASS, honest FAIL with named upgrade path, or deferral with dated unblock — using OPERA / EGMS / JRC / EMS as validators, not quality ceilings.

## Milestones

- ✅ **v1.0 Initial Release** — Phases 1-9 (shipped 2026-04-09)
- 🚧 **v1.1 N.Am./EU Validation Parity & Scientific PASS** — Phases 1-7

## Phases

<details>
<summary>✅ v1.0 Initial Release (Phases 1-9) — SHIPPED 2026-04-09</summary>

- [x] Phase 1: Foundation, Data Access & Burst DB (4/4 plans)
- [x] Phase 2: RTC-S1 and CSLC-S1 Pipelines (4/4 plans)
- [x] Phase 3: DISP-S1 and DIST-S1 Pipelines (3/3 plans)
- [x] Phase 4: DSWx-S2 Pipeline and Full Interface (3/3 plans)
- [x] Phase 5: Fix Cross-Phase Integration Wiring (2/2 plans)
- [x] Phase 6: Wire Unused Data Modules & OPERA Metadata (2/2 plans)
- [x] Phase 7: CLI Gaps & Code Cleanup (1/1 plan)
- [x] Phase 8: Planning Artifact Cleanup (1/1 plan)
- [x] Phase 9: Fix Report Criteria Keys & Clean Orphaned Code (1/1 plan)

Full details: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

</details>

<details open>
<summary>🚧 v1.1 N.Am./EU Validation Parity & Scientific PASS (Phases 1-7) — IN PROGRESS</summary>

- [ ] **Phase 1: Environment Hygiene, Framework Consolidation & Guardrail Scaffolding** — pin numpy<2, centralise `_cog`/`_mp`, build `validation.harness` + shared stable-terrain/self-consistency modules, land `criteria.py` CALIBRATING/BINDING, split result dataclasses, split tests dir, Makefile + manifest + env lockfile
- [x] **Phase 2: RTC-S1 EU Validation** — 3-5 EU RTC bursts PASS across ≥3 terrain regimes (≥1 with >1000 m relief AND ≥1 >55°N); per-burst reporting; proves Phase 1 harness end-to-end
- [ ] **Phase 3: CSLC-S1 Self-Consistency + EU Validation** — SoCal / Mojave / Iberian Meseta self-consistency coherence > 0.7 and residual < 5 mm/yr (CALIBRATING); OPERA CSLC amplitude sanity r > 0.6 / RMSE < 4 dB; cross-version-phase methodology consolidated
- [ ] **Phase 4: DISP-S1 Comparison Adapter + Honest FAIL** — `prepare_for_reference` adapter (explicit `method=`); self-consistency at native 5×10 m; N.Am./EU re-runs with ramp-attribution diagnostic; DISP Unwrapper Selection scoping brief delivered
- [ ] **Phase 5: DIST-S1 OPERA v0.1 + EFFIS EU** — T11SLT v0.1 comparison (or config-drift deferral) with block-bootstrap CI; CMR probe auto-supersede; EFFIS recall+precision cross-val; 3 EU events; optional chained `prior_dist_s1_product` run
- [ ] **Phase 6: DSWx-S2 N.Am. + EU Recalibration** — N.Am. positive control; AOI research notebook; 12-pair fit set across 6 biomes (Balaton held-out); joint grid search over WIGT/AWGT/PSWT2_MNDWI; typed thresholds module with provenance; EU re-run (F1 > 0.90 bar does not move)
- [ ] **Phase 7: Results Matrix + Release Readiness** — `make eval-all` writes `results/matrix.md` (product-quality / reference-agreement columns); manifest-driven matrix writer; `docs/validation_methodology.md`; TrueNAS Linux pre-release audit; env lockfile + Dockerfile/Apptainer recipe

</details>

## Phase Details

### Phase 1: Environment Hygiene, Framework Consolidation & Guardrail Scaffolding

**Goal**: A fresh clone can `micromamba env create -f conda-env.yml` and land a runnable environment with zero post-install pip commands, zero runtime monkey-patches, a shared `validation.harness`, shared stable-terrain / self-consistency modules, immutable metrics-vs-targets guardrails, a per-cell-isolated Makefile, a committed env lockfile, and a reproducibility container recipe.

**Depends on**: Nothing (first phase)

**Requirements**: ENV-01, ENV-02, ENV-03, ENV-04, ENV-05, ENV-06, ENV-07, ENV-08, ENV-09, ENV-10, GATE-01, GATE-02, GATE-03, GATE-04, GATE-05, CSLC-01, CSLC-02

**Success Criteria** (what must be TRUE):
  1. User runs `micromamba env create -f conda-env.yml` on a clean machine and every Phase 2-7 eval script imports + runs without any additional `pip install` step (ENV-01 / ENV-02 / tophu via conda-forge not pip per research correction)
  2. User greps `rg "_patch_" src/subsideo/products/` and gets zero results; greps `rg "from rio_cogeo" src/` and gets a single hit inside `_cog.py` pinned to `rio-cogeo==6.0.0` (ENV-02 / ENV-03 — 6.0.0 not 7.x per research correction)
  3. User runs `run_eval_dist*.py` three times consecutively on macOS M3 Max and never hangs: the full `_mp` bundle (start method + `MPLBACKEND=Agg` + `RLIMIT_NOFILE` raise + pre-fork `requests.Session` closure + forkserver fallback on Python ≥3.14) plus subprocess-level watchdog with `os.killpg` grandchild cleanup is invoked at the top of every `run_*()` (ENV-04 / ENV-05, prevents PITFALLS P0.1)
  4. User diffs any two eval scripts (e.g. `run_eval_disp_egms.py` vs `run_eval_disp.py`) and sees only reference-data differences — all plumbing (frame selection, retries with per-source policies, resume checks, credential preflight, `bounds_for_burst`) lives in `validation/harness.py` and all geographic bounds derive from burst/MGRS IDs (ENV-06 / ENV-07 / ENV-08, prevents PITFALLS P0.4 and P1.1 cached-bias)
  5. User imports `subsideo.validation.criteria` and finds `CALIBRATING` vs `BINDING` plus a `binding_after_milestone` field on every calibrating gate; imports `subsideo.validation.stable_terrain` and `subsideo.validation.selfconsistency` (with coast buffer + water-body exclusion, median+p25+p75+persistently-coherent fraction, reference-frame aligned residual); sees `ProductQualityResult` and `ReferenceAgreementResult` as distinct dataclasses with no top-level `.passed` collapse; and finds `tests/product_quality/` vs `tests/reference_agreement/` as a directory split (GATE-01 / GATE-02 / GATE-04 / GATE-05 / CSLC-01 / CSLC-02, prevents PITFALLS M1-M6, P2.1-P2.3)
  6. User runs `make eval-all`, `make eval-nam`, `make eval-eu`, or `make eval-{product}-{region}`; a single failing cell does not block the rest of the matrix (per-cell subprocess isolation); every cell writes a `meta.json` sidecar with git SHA + input content hashes; a committed `env.lockfile.txt` plus Dockerfile/Apptainer recipe can rebuild the environment bit-for-bit (ENV-09 / ENV-10 / GATE-03, prevents PITFALLS R1-R4)

**Internal ordering** (per research ARCHITECTURE §Build Order): 0.1 numpy pin → 0.3 `_cog.py` → 0.4 `_mp.py` full bundle → 0.5 + 0.5.5 harness + stable_terrain + selfconsistency (shared with Phases 3 & 4) → 0.6abc `criteria.py` + split dataclasses + test dir split → 0.2 tophu conda-forge pin + `import tophu` regression test → 0.7 + 0.8 + 0.9 Makefile + manifest + lockfile/Dockerfile. `bounds_for_burst` collapses into harness.py per research correction.

**Plans**: 9 plans across 4 waves

Plans:
- [x] 01-01-PLAN.md — Env bootstrap: write conda-env.yml (numpy<2, tophu 0.2.1 conda-forge, dist-s1 2.0.14, py-spy, rio-cogeo==6.0.0 pip layer, -e .[validation,viz]) [Wave 1] [ENV-01, ENV-02, ENV-09, ENV-10]
- [x] 01-02-PLAN.md — Private utility `_cog.py` + rewrite all rio_cogeo import sites + ensure_valid_cog IFD heal [Wave 2] [ENV-03]
- [x] 01-03-PLAN.md — Private utility `_mp.py` full fork bundle + insert configure_multiprocessing at top of 5 run_*() + delete 4 monkey-patches from cslc.py [Wave 2] [ENV-02, ENV-04]
- [x] 01-04-PLAN.md — Shared validation modules: `stable_terrain.py` (WorldCover + slope + coast + water) + `selfconsistency.py` (5-key coherence + reference-frame aligned residual) [Wave 1] [CSLC-01, CSLC-02]
- [x] 01-05-PLAN.md — D-09 BIG-BANG: criteria.py (13 entries) + results.py + 5 composite ValidationResult classes + 5 compare_*.py returns + tests/product_quality + tests/reference_agreement + AST linter + reference_agreement marker — ONE COMMIT [Wave 1] [GATE-01, GATE-02, GATE-04, GATE-05]
- [x] 01-06-PLAN.md — `validation/harness.py` with 5 helpers + RETRY_POLICY + ReferenceDownloadError + pilot run_eval.py migration [Wave 2] [ENV-06, ENV-07, ENV-08]
- [x] 01-07-PLAN.md — `validation/supervisor.py` subprocess watchdog + Makefile (10 cells) + batch-migrate 7 remaining eval scripts [Wave 3] [ENV-05, ENV-07, ENV-08, ENV-09]
- [x] 01-08-PLAN.md — `matrix_schema.py` Pydantic v2 + `results/matrix_manifest.yml` (10 cells) + `matrix_writer.py` with threshold echo + CALIBRATING italicisation [Wave 3] [ENV-09, GATE-03]
- [x] 01-09-PLAN.md — Reproducibility recipe: Dockerfile (mambaorg/micromamba) + Apptainer.def + env.lockfile.{osx-arm64,linux-64}.txt + two-platform D-18 acceptance [Wave 4] [ENV-10, GATE-03]

**Requirements coverage audit** (all 17 Phase 1 requirement IDs):
ENV-01 (01), ENV-02 (01, 03), ENV-03 (02), ENV-04 (03), ENV-05 (07), ENV-06 (06), ENV-07 (06, 07), ENV-08 (06, 07), ENV-09 (01, 07, 08), ENV-10 (01, 09), GATE-01 (05), GATE-02 (05), GATE-03 (08, 09), GATE-04 (05), GATE-05 (05), CSLC-01 (04), CSLC-02 (04). Every requirement appears in at least one plan.

### Phase 2: RTC-S1 EU Validation

**Goal**: Users can run `make eval-rtc-eu` and obtain per-burst PASS/FAIL across 3-5 EU bursts covering ≥3 terrain regimes with at least one >1000 m relief AND at least one >55°N — proving Phase 1 harness on a low-risk deterministic product and demonstrating reproducibility-across-geographies without criterion-creep toward N.Am.'s 0.045 dB headroom.

**Depends on**: Phase 1 (harness, `bounds_for_burst`, criteria.py, matrix manifest)

**Requirements**: RTC-01, RTC-02, RTC-03

**Success Criteria** (what must be TRUE):
  1. User runs `make eval-rtc-eu` and the matrix cell reports per-burst PASS/FAIL across 3-5 EU bursts spanning ≥3 regimes (alpine / plain / arid / boreal / wildfire), with verifiable ≥1 burst of >1000 m relief AND ≥1 burst >55°N in the CONCLUSIONS terrain-regime coverage table (RTC-01, prevents PITFALLS P1.1 cached-bias)
  2. User reads `src/subsideo/validation/criteria.py` and confirms EU RTC reference-agreement criteria are literally the same constants as N.Am. (RMSE < 0.5 dB, r > 0.99) — no tightened constant added post-measurement even if burst RMSE lands in the 0.04-0.1 dB N.Am.-like range (RTC-02, prevents PITFALLS M1 target-creep)
  3. User opens `CONCLUSIONS_RTC_EU.md` and finds selected bursts, regime-coverage table, per-burst numerical results, and — where any burst shows materially different RMSE from N.Am. — an investigation finding in the same doc (RTC-03)

**Plans**: 5 plans across 4 waves

Plans:
- [x] 02-01-PLAN.md — Framework extensions: matrix_schema (RTCEUCellMetrics + BurstResult), criteria.py (INVESTIGATION_TRIGGER entries), harness.find_cached_safe [Wave 1] [RTC-01, RTC-02, RTC-03]
- [x] 02-02-PLAN.md — Probe script + candidate-burst artifact + CONCLUSIONS_RTC_EU.md template shell [Wave 1] [RTC-01, RTC-03]
- [x] 02-03-PLAN.md — matrix_writer RTC-EU render branch + INVESTIGATION_TRIGGER filter [Wave 2] [RTC-01, RTC-03]
- [x] 02-04-PLAN.md — run_eval_rtc_eu.py declarative 5-burst eval script + static-invariant tests [Wave 3] [RTC-01, RTC-03]
- [x] 02-05-PLAN.md — Execute `make eval-rtc-eu` + populate CONCLUSIONS_RTC_EU.md + render matrix row [Wave 4] [RTC-01, RTC-02, RTC-03]

**Requirements coverage audit** (all 3 Phase 2 requirement IDs):
RTC-01 (01, 02, 03, 04, 05), RTC-02 (01, 05), RTC-03 (01, 02, 03, 04, 05). Every requirement appears in at least one plan.

### Phase 3: CSLC-S1 Self-Consistency + EU Validation

**Goal**: Users can run SoCal + Mojave + Iberian Meseta CSLC evals and obtain product-quality numbers (self-consistency coherence and residual mean velocity on stable terrain) that do not depend on cross-version phase comparison — consuming the shared `stable_terrain.py` and `selfconsistency.py` modules from Phase 1 — plus OPERA CSLC amplitude reference-agreement as a sanity check reported separately, with the cross-version phase impossibility consolidated into methodology documentation.

**Depends on**: Phase 1 (numpy<2 pin, harness, shared `stable_terrain.py` + `selfconsistency.py`, criteria.py)

**Requirements**: CSLC-03, CSLC-04, CSLC-05, CSLC-06

**Success Criteria** (what must be TRUE):
  1. User runs SoCal self-consistency eval on burst `t144_308029_iw1` (15 dates, 14 sequential 12-day IFGs) and the matrix cell reports self-consistency coherence > 0.7 (CALIBRATING) plus residual mean velocity < 5 mm/yr over OPERA-CSLC-derived stable pixels (CSLC-03, prevents PITFALLS M5 too-tight-first-rollout)
  2. User runs Mojave self-consistency eval (Coso/Searles Valley primary or a documented-stable fallback from the Pahranagat / Amargosa / Hualapai list) and either passes the same gate, OR exhaustion of the 3-candidate fallback list surfaces as an explicit phase blocker — not as a silent FAIL (CSLC-04, prevents PITFALLS P2.1 mask contamination)
  3. User runs Iberian Meseta EU eval and the matrix cell reports three independent numbers: OPERA CSLC amplitude r > 0.6 / RMSE < 4 dB (sanity), self-consistency coherence > 0.7 over stable terrain (product quality), and EGMS L2a stable-PS residual mean velocity < 5 mm/yr (product quality) — product-quality and reference-agreement never collapse into a single `.passed` (CSLC-05, prevents PITFALLS M2 conflation)
  4. User opens `docs/validation_methodology.md` and finds the cross-version phase impossibility methodology section with diagnostic evidence (removal of carrier, flattening, both — still zero coherence across isce3 major versions) (CSLC-06)

**Planning artifact — coherence metric choice**: research flagged mean-vs-median-vs-persistently-coherent-fraction as a Phase 3 planning decision (see research SUMMARY §Research Flags, PITFALLS P2.2). Plan-phase should resolve before SoCal calibration.

**Plans**: TBD

### Phase 4: DISP-S1 Comparison Adapter + Honest FAIL

**Goal**: Users can run `prepare_for_reference` to multilook subsideo's native 5×10 m DISP to any reference grid (OPERA DISP 30 m or EGMS L2a PS) with an explicit `method=` argument — production default remains native 5×10 m — while the N.Am. and EU re-runs report self-consistency (product quality) and reference-agreement (r vs OPERA DISP, r vs EGMS L2a PS) separately with ramp-attribution diagnostics, and a one-page DISP Unwrapper Selection scoping brief is delivered as the handoff to the follow-up milestone.

**Depends on**: Phase 1 (tophu, `_mp` bundle, harness, shared stable_terrain/selfconsistency, split dataclasses)

**Requirements**: DISP-01, DISP-02, DISP-03, DISP-04, DISP-05

**Success Criteria** (what must be TRUE):
  1. User calls `subsideo.validation.compare_disp.prepare_for_reference(native_velocity, reference_grid, method=...)` with an explicit `method=` argument (no default), accepting (a) path to GeoTIFF, (b) `xr.DataArray` with CRS, or (c) `ReferenceGridSpec` for point-sampling — and the function never writes back to the product (DISP-01 + DISP-05, prevents anti-feature "write back to product" and P3.1 default-kernel silently-chosen)
  2. User re-runs DISP from cached CSLCs for both N.Am. (SoCal) and EU (Bologna) and the matrix cell reports (a) self-consistency coherence > 0.7 + residual < 5 mm/yr at native 5×10 m (product quality, CALIBRATING) reported separately from (b) reference-agreement r at OPERA 30 m / EGMS PS (DISP-02 + DISP-03, prevents PITFALLS M2)
  3. Any observed planar ramp in the reference-agreement output is labelled in CONCLUSIONS with its attributed source (PHASS / tropospheric / orbit / ionospheric) via a ramp-attribution diagnostic — POEORB swap, ERA5 toggle, ramp-direction stability test — rather than collapsed into a single "PHASS FAIL" label (DISP-03, prevents PITFALLS P3.2)
  4. User opens the DISP Unwrapper Selection follow-up milestone scoping brief (delivered as Phase artifact) and finds fresh FAIL numbers plus candidate approaches (PHASS+deramping, SPURT native, tophu-SNAPHU tiled, 20×20 m fallback) each with a success criterion — scoped but not pre-committed (DISP-04)

**Planning artifact — multilook method default**: research identified direct tension between PITFALLS P3.1 (Gaussian σ=0.5×ref physically-correct when reference is itself Gaussian-smoothed) and FEATURES anti-feature table (block-mean as conservative anti-inflation choice). Plan-phase ADR required; this roadmap does not pre-commit.

**Plans**: TBD

### Phase 5: DIST-S1 OPERA v0.1 + EFFIS EU

**Goal**: Users can run `make eval-dist-nam` to either (a) produce a T11SLT v0.1 quantitative comparison with block-bootstrap CI when the config-drift gate passes, or (b) surface "deferred pending operational reference publication" when v0.1 and dist-s1 2.0.14 defaults materially disagree on any of the 7 key parameters — with an automatic CMR probe that supersedes v0.1 the moment operational `OPERA_L3_DIST-ALERT-S1_V1` publishes; meanwhile EU expands from 1 to 3 events plus EFFIS same-resolution cross-validation with genuine recall+precision criteria.

**Depends on**: Phase 1 (`_mp.py` full bundle resolves the dist-s1 hang; harness CloudFront path with per-source retry policy)

**Requirements**: DIST-01, DIST-02, DIST-03, DIST-04, DIST-05, DIST-06, DIST-07

**Success Criteria** (what must be TRUE):
  1. User runs the DIST LA eval and the OPERA v0.1 T11SLT sample is fetched from CloudFront (`d2pn8kiwq2w21t.cloudfront.net/...T11SLT_20250121T015030Z...`) with exponential-backoff retry and cached under `eval-dist/opera_reference/v0.1_T11SLT/` — the sample is preserved on disk regardless of downstream comparison outcome (DIST-01)
  2. Before T11SLT quantitative comparison runs, a config-drift gate extracts the OPERA v0.1 sample's 7 key processing parameters (confirmation-count threshold, pre-image strategy, post-date buffer, baseline window length, despeckle settings + 2 further) and compares against dist-s1 2.0.14 defaults; when material deltas are found the matrix cell reads "deferred pending operational reference publication" and continues (DIST-02, prevents PITFALLS P4.1)
  3. When the config-drift gate passes, the T11SLT comparison reports F1 / precision / recall / accuracy with block-bootstrap 95% CI (1 km blocks, B=500); the matrix cell shows point estimate AND CI; criteria stay F1 > 0.80 and accuracy > 0.85 without tightening toward v0.1's own score (DIST-03, prevents PITFALLS P4.2 single-tile variance + M1 target-creep)
  4. `make eval-dist-nam` includes a CMR probe for operational `OPERA_L3_DIST-ALERT-S1_V1`; on discovery the operational reference supersedes the v0.1 result in the matrix with no manual intervention and no re-planning (DIST-04)
  5. User runs EFFIS cross-validation against cached Aveiro/Viseu 2024 subsideo output via `owslib` WFS and the matrix reports precision > 0.70 AND recall > 0.50 (DIST-05); aggregate `CONCLUSIONS_DIST_EU.md` covers 3 events — 2024 Portuguese wildfires + 2023 Evros Greece EMSR649 + 2022 Romanian forest clear-cuts (DIST-06)
  6. After Phase 1's `_mp.py` bundle lands, the chained `prior_dist_s1_product` run on the DIST EU stack (Sep 28 → Oct 10 → Nov 15) is retried; success is reported as a DIFFERENTIATOR, failure is filed upstream with dist-s1 maintainers and is non-blocking to milestone closure (DIST-07)

**Plans**: TBD

### Phase 6: DSWx-S2 N.Am. + EU Recalibration

**Goal**: Users can run a N.Am. positive control (Lake Tahoe or Pontchartrain) and re-run EU DSWx with recalibrated region-selected thresholds whose values live in a typed constants module `products/dswx_thresholds.py` with full provenance metadata — derived from a deterministic, restart-safe joint grid search over WIGT × AWGT × PSWT2_MNDWI optimising mean F1 across a carefully-curated 12-triple / 6-biome EU fit set (Balaton held out as independent test) — with the F1 > 0.90 bar unchanged and any 0.85 ≤ F1 < 0.90 outcome reported as honest FAIL with named ML-replacement upgrade path.

**Depends on**: Phase 1 (`_cog.py`, harness, criteria.py DSWx F1_THRESHOLD immutable)

**Requirements**: DSWX-01, DSWX-02, DSWX-03, DSWX-04, DSWX-05, DSWX-06, DSWX-07

**Success Criteria** (what must be TRUE):
  1. User runs N.Am. DSWx-S2 positive control on Lake Tahoe or Lake Pontchartrain; matrix reports F1 against JRC Monthly History; any F1 < 0.85 triggers a documented regression investigation (BOA offset / Claverie cross-calibration) before recalibration proceeds (DSWX-01)
  2. User opens `notebooks/dswx_aoi_selection.ipynb` and finds per-AOI selection rationale spanning JRC reference quality + S2 cloud-free scene availability + water-body type diversity + absence of known algorithm failure modes (glacier / frozen lake / heavy turbid / mountain shadow); 12 (AOI, wet, dry) triples across 6 biome-diverse AOIs (Mediterranean reservoir / Atlantic estuary / boreal lake / Pannonian plain / Alpine valley / Iberian summer-dry) with Balaton held out (DSWX-02 + DSWX-03, prevents PITFALLS P5.2 JRC labelling noise)
  3. User runs `scripts/recalibrate_dswe_thresholds.py` and a joint grid search sweeps WIGT ∈ [0.08, 0.20] step 0.005, AWGT ∈ [−0.1, +0.1] step 0.01, PSWT2_MNDWI ∈ [−0.65, −0.35] step 0.02; `notebooks/dswx_recalibration.ipynb` reproduces it deterministically from the cached fit set (DSWX-04 + DSWX-05)
  4. User imports `subsideo.products.dswx_thresholds` and finds a typed `DSWEThresholds` NamedTuple with provenance metadata (grid-search run date, fit-set pointer, F1 on held-out Balaton, reproducibility notebook reference) + EU/N.Am. region selector via pydantic-settings — no YAML, no runtime file I/O, no plain-dict (DSWX-05)
  5. User opens updated `CONCLUSIONS_DSWX.md` and sees fit-set F1 alongside LOO-CV F1 (gap < 0.02 required to rule out overfit); F1 bar stays at 0.90 with 0.85 ≤ F1 < 0.90 labelled "FAIL with named ML-replacement upgrade path"; F1 < 0.85 triggers fit-set quality review; any DSWE F1 ≈ 0.92 ceiling claim is either ground-referenced to the PROTEUS ATBD (citation) or labelled "empirical bound observed over our 6-AOI evaluation" — no game-of-telephone citations (DSWX-06 + DSWX-07, prevents PITFALLS M4 goalpost-moving + P5.1 LOO-CV overfit + P5.3 ceiling-telephone)

**Internal ordering**: AOI research (DSWX-02) must precede fit-set compute commit; grid search (DSWX-04) consumes fit set; threshold module update (DSWX-05) consumes grid-search results; EU re-run (DSWX-06) consumes updated thresholds.

**Plans**: TBD

### Phase 7: Results Matrix + Release Readiness

**Goal**: The milestone closure test — `fresh clone → micromamba env create -f conda-env.yml → make eval-all → filled results/matrix.md` — runs end-to-end on TrueNAS Linux with cold-env under 12 h and warm-env under 10 min, and every cell in the 5-products × 2-regions matrix reads PASS, FAIL-with-named-upgrade-path, or deferred-with-dated-unblock-condition (never n/a, never empty), with `docs/validation_methodology.md` consolidating the four methodological findings and the product-quality vs reference-agreement distinction.

**Depends on**: Phases 1, 2, 3, 4, 5, 6 (all)

**Requirements**: REL-01, REL-02, REL-03, REL-04, REL-05, REL-06

**Success Criteria** (what must be TRUE):
  1. User runs `make eval-all` and `results/matrix.md` is written with all 10 cells filled (5 products × 2 regions); each cell reports product-quality gate status and reference-agreement numbers in structurally separate columns; CALIBRATING cells are visually distinguishable from BINDING cells (REL-01 + REL-05, prevents PITFALLS M2 + M6 perpetual-calibrating via `binding_after_milestone` check)
  2. User reads `results/matrix_manifest.yml` and sees the expected cells with per-eval `metrics.json` sidecar paths; the matrix writer reads only from manifest + sidecars and never glob-parses CONCLUSIONS free-text markdown (REL-02, prevents PITFALLS R3 + R5)
  3. User opens `docs/validation_methodology.md` and finds all four methodological findings (cross-version phase impossibility across isce3 majors; cross-sensor comparison precision-first framing; OPERA frame selection by exact UTC hour + spatial footprint; DSWE-family F1 ≈ 0.92 architectural ceiling) plus the product-quality vs reference-agreement distinction explicitly documented (REL-03)
  4. User runs full `make eval-all` on a freshly-cloned repo inside the homelab TrueNAS Linux dev container and cold-env completes under 12 h; warm-env re-run completes under 10 min (REL-04)
  5. User runs `micromamba env create -f conda-env.yml` on a clean machine and it completes successfully; `pytest` passes as the final closure test (REL-06)

**Plans**: TBD

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation, Data Access & Burst DB | v1.0 | 4/4 | Complete | 2026-04-05 |
| 2. RTC-S1 and CSLC-S1 Pipelines | v1.0 | 4/4 | Complete | 2026-04-05 |
| 3. DISP-S1 and DIST-S1 Pipelines | v1.0 | 3/3 | Complete | 2026-04-05 |
| 4. DSWx-S2 Pipeline and Full Interface | v1.0 | 3/3 | Complete | 2026-04-06 |
| 5. Fix Cross-Phase Integration Wiring | v1.0 | 2/2 | Complete | 2026-04-06 |
| 6. Wire Unused Data Modules & OPERA Metadata | v1.0 | 2/2 | Complete | 2026-04-06 |
| 7. CLI Gaps & Code Cleanup | v1.0 | 1/1 | Complete | 2026-04-06 |
| 8. Planning Artifact Cleanup | v1.0 | 1/1 | Complete | 2026-04-06 |
| 9. Fix Report Criteria Keys & Cleanup | v1.0 | 1/1 | Complete | 2026-04-06 |
| 1. Environment Hygiene, Framework Consolidation & Guardrail Scaffolding | v1.1 | 0/9 | Planned | - |
| 2. RTC-S1 EU Validation | v1.1 | 5/5 | Complete (3/5 PASS w/ investigation) | 2026-04-23 |
| 3. CSLC-S1 Self-Consistency + EU Validation | v1.1 | 0/0 | Not started | - |
| 4. DISP-S1 Comparison Adapter + Honest FAIL | v1.1 | 0/0 | Not started | - |
| 5. DIST-S1 OPERA v0.1 + EFFIS EU | v1.1 | 0/0 | Not started | - |
| 6. DSWx-S2 N.Am. + EU Recalibration | v1.1 | 0/0 | Not started | - |
| 7. Results Matrix + Release Readiness | v1.1 | 0/0 | Not started | - |
