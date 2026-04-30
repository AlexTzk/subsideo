# Roadmap: subsideo

## Overview

subsideo builds a Python library that produces OPERA-equivalent SAR/InSAR geospatial products (RTC-S1, CSLC-S1, DISP-S1, DSWx-S2, DIST-S1) over EU areas of interest. v1.0 shipped the five product pipelines, CDSE/ASF data access, EU burst database, Typer CLI, and a validation framework. v1.1 hardened the validation matrix across N.Am./EU. v1.2 focuses on **CSLC binding and DISP science pass**: promote CSLC self-consistency gates from CALIBRATING to BINDING, resolve deferred EGMS/AOI hardening, and turn DISP's v1.1 honest FAIL into a pass or a much narrower named blocker.

## Milestones

- ✅ **v1.0 Initial Release** — Phases 1-9 (shipped 2026-04-09)
- ✅ **v1.1 N.Am./EU Validation Parity & Scientific PASS** — Phases 1-7 (shipped 2026-04-29)
- 🟡 **v1.2 CSLC Binding & DISP Science Pass** — Phases 8-12 (planned 2026-04-30)

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

<details>
<summary>✅ v1.1 N.Am./EU Validation Parity & Scientific PASS (Phases 1-7) — SHIPPED 2026-04-29</summary>

Full details: [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)

- [x] **Phase 1: Environment Hygiene, Framework Consolidation & Guardrail Scaffolding** (9/9 plans, complete 2026-04-22) — pin numpy<2, centralise `_cog`/`_mp`, build `validation.harness` + shared stable-terrain/self-consistency modules, land `criteria.py` CALIBRATING/BINDING, split result dataclasses, split tests dir, Makefile + manifest + env lockfile
- [x] **Phase 2: RTC-S1 EU Validation** — 3-5 EU RTC bursts PASS across ≥3 terrain regimes (≥1 with >1000 m relief AND ≥1 >55°N); per-burst reporting; proves Phase 1 harness end-to-end
- [x] **Phase 3: CSLC-S1 Self-Consistency + EU Validation** (5/5 plans, complete 2026-04-25) — SoCal coh=0.887/−0.109 mm/yr + Mojave coh=0.804/+1.127 mm/yr + Iberian coh=0.868/+0.347 mm/yr; all CALIBRATING — SoCal / Mojave / Iberian Meseta self-consistency coherence > 0.7 and residual < 5 mm/yr (CALIBRATING); OPERA CSLC amplitude sanity r > 0.6 / RMSE < 4 dB; cross-version-phase methodology consolidated
- [x] **Phase 4: DISP-S1 Comparison Adapter + Honest FAIL** (5/5 plans, complete 2026-04-25) — `prepare_for_reference` adapter (explicit `method=`); self-consistency at native 5×10 m; N.Am./EU re-runs with ramp-attribution diagnostic; DISP Unwrapper Selection scoping brief delivered
- [x] **Phase 5: DIST-S1 OPERA v0.1 + EFFIS EU** (9/9 plans, complete 2026-04-25) — T11SLT v0.1 CMR deferred; CMR probe auto-supersede; EFFIS 3 EU events (aveiro 0/3 FAIL); chained_run differentiator structurally_valid
- [x] **Phase 6: DSWx-S2 N.Am. + EU Recalibration** (7/7 plans, complete 2026-04-28) — N.Am. F1=0.9252 PASS (Lake Tahoe); EU recalibration deferred to v1.2 (HLS to S2 L2A spectral gap); Balaton F1=0.8165 FAIL (fit-set quality review); typed thresholds module; methodology §5 appended
- [x] **Phase 7: Results Matrix + Release Readiness** — `make eval-all` writes `results/matrix.md` (product-quality / reference-agreement columns); manifest-driven matrix writer; `docs/validation_methodology.md`; TrueNAS Linux pre-release audit; env lockfile + Dockerfile/Apptainer recipe (3/3 plans, complete 2026-04-29; REL-04 TrueNAS deferred to v1.2 with dated unblock)

</details>

<details open>
<summary>🟡 v1.2 CSLC Binding & DISP Science Pass (Phases 8-12) — PLANNED</summary>

- [ ] **Phase 8: CSLC Gate Promotion & AOI Hardening** — fix stable-terrain buffer geometry, regenerate acquisition-backed AOI probe artifacts, add EU fallback AOIs, reject truncated SAFE caches, and propose BINDING CSLC gate thresholds.
- [ ] **Phase 9: CSLC EGMS Third Number & Binding Reruns** — adapt EGMS L2a integration, populate the EU stable-PS residual, restore Mojave amplitude sanity if possible, rerun CSLC N.Am./EU, and promote CSLC matrix cells out of CALIBRATING.
- [ ] **Phase 10: DISP Atmospheric & Provenance Diagnostics** — run ERA5/tropospheric diagnostics on cached SoCal/Bologna stacks, use RTC-style DEM/orbit provenance checks only where needed, and decide whether atmospheric curvature explains the v1.1 ramp pattern.
- [ ] **Phase 11: DISP Candidate Evaluation** — test PHASS deramping plus at least one candidate from SPURT native, tophu/SNAPHU tiled, or 20 x 20 m fallback while preserving native 5 x 10 m production output.
- [ ] **Phase 12: Matrix, Methodology & v1.2 Closure** — update CSLC/DISP conclusions, methodology, requirements traceability, and matrix rows with explicit PASS/FAIL/defer outcomes.

</details>

## Phase Details

### Phase 8: CSLC Gate Promotion & AOI Hardening

**Goal**: Users can trust the CSLC self-consistency inputs before gate promotion: stable-terrain masks buffer coast/water in projected metres, AOI probe artifacts are regenerated from real acquisition searches, fallback AOIs are validated, and interrupted SAFE caches self-heal before readers consume them.

**Depends on**: v1.1 Phase 3 CSLC self-consistency framework; v1.1 Phase 4 shared product-quality / reference-agreement split

**Requirements**: CSLC-07, CSLC-08, CSLC-09, RTCSUP-01

**Success Criteria** (what must be TRUE):
  1. User runs unit tests for `stable_terrain.py` and sees projected metre buffering for coast/water masks across at least two UTM zones, with SoCal coastal stable-pixel retention explained by metrics rather than EPSG:4326 degree-buffer artefacts (CSLC-08).
  2. User runs the CSLC AOI probe and obtains ASF/CDSE-verified sensing windows for SoCal, Mojave/Coso-Searles, Iberian Meseta-North, and at least two EU fallback AOIs; no fabricated date tuples remain in the probe artifact (CSLC-09).
  3. User interrupts a SAFE download and reruns CSLC/DISP/RTC eval setup; truncated zip files are detected and redownloaded before `s1reader`, `compass`, or `opera-rtc` attempts to read them (RTCSUP-01).
  4. User opens `.planning/REQUIREMENTS.md` and the Phase 8 summary and finds a proposed CSLC BINDING threshold rationale grounded in v1.1 values (0.804, 0.868, 0.887 coherence; residuals all < 1.2 mm/yr) plus any added v1.2 AOI values (CSLC-07).

**Plans**: To be generated by `$gsd-plan-phase 8`

### Phase 9: CSLC EGMS Third Number & Binding Reruns

**Goal**: Users can run CSLC N.Am./EU cells and obtain BINDING CSLC product-quality results, including the deferred EU EGMS L2a stable-PS residual and a resolved Mojave amplitude-sanity disposition.

**Depends on**: Phase 8

**Requirements**: CSLC-07, CSLC-10, CSLC-11, VAL-01, VAL-03

**Success Criteria** (what must be TRUE):
  1. User runs `make eval-cslc-eu` and the EU metrics include a populated `egms_l2a_stable_ps_residual_mm_yr` or a hard blocker tied to a current upstream EGMS access/API failure, not a silent null (CSLC-10).
  2. User runs `make eval-cslc-nam` and sees SoCal plus Mojave/Coso-Searles rerun through the BINDING gate logic; Mojave amplitude sanity is either populated against OPERA or explicitly marked unavailable with frame-search evidence (CSLC-11).
  3. User opens `results/matrix.md` and CSLC N.Am./EU rows no longer read only as CALIBRATING; they report BINDING PASS/FAIL or a named blocker with metric sidecars (CSLC-07, VAL-03).
  4. User can rerun CSLC cells from cached intermediates and sidecars validate against the manifest schema (VAL-01).

**Plans**: To be generated by `$gsd-plan-phase 9`

### Phase 10: DISP Atmospheric & Provenance Diagnostics

**Goal**: Users can determine whether DISP's v1.1 inconclusive ramps are atmospheric/provenance-driven before spending heavy compute on unwrapper candidates.

**Depends on**: v1.1 DISP cached CSLC/DISP stacks; Phase 8 cache integrity

**Requirements**: DISP-06, RTCSUP-02

**Success Criteria** (what must be TRUE):
  1. User reruns SoCal and Bologna DISP evaluations from cached CSLCs with ERA5/tropospheric correction toggled and receives before/after ramp magnitude, direction stability, r, bias, and RMSE metrics (DISP-06).
  2. User reads updated DISP conclusions and sees whether atmospheric long-wavelength curvature is supported, rejected, or still mixed after ERA5 diagnostics (DISP-06).
  3. If DISP diagnostics implicate orbit/DEM/provenance rather than atmosphere, user can run shared provenance checks that compare orbit filenames, DEM coverage/slope, and relevant processor versions, using RTC EU drift methodology only as support evidence (RTCSUP-02).

**Plans**: To be generated by `$gsd-plan-phase 10`

### Phase 11: DISP Candidate Evaluation

**Goal**: Users can compare concrete DISP remediation candidates against the same N.Am./EU reference-agreement and product-quality metrics without changing the native product default.

**Depends on**: Phase 10

**Requirements**: DISP-07, DISP-08, DISP-09, VAL-01

**Success Criteria** (what must be TRUE):
  1. User runs a PHASS post-deramping candidate and the metrics show whether it reduces ramp magnitude and improves reference-agreement without writing deramped data back into the native 5 x 10 m product (DISP-07).
  2. User runs at least one alternative candidate from SPURT native, tophu/SNAPHU tiled, or 20 x 20 m fallback; runtime failures, hangs, connected-component collapse, and memory/time limits are captured as structured candidate metrics (DISP-08).
  3. User compares SoCal OPERA and Bologna EGMS results through `prepare_for_reference(method=...)`, with product-quality, reference-agreement, and ramp-attribution reported separately for every candidate (DISP-09).
  4. User can rerun selected DISP candidate cells from cached intermediates and regenerate `metrics.json` / `meta.json` without re-downloading S1 inputs (VAL-01).

**Plans**: To be generated by `$gsd-plan-phase 11`

### Phase 12: Matrix, Methodology & v1.2 Closure

**Goal**: Users can inspect a complete v1.2 CSLC/DISP validation story: requirements traceability, methodology updates, conclusions, and matrix rows all agree on PASS/FAIL/defer outcomes.

**Depends on**: Phases 8-11

**Requirements**: DISP-10, VAL-01, VAL-02, VAL-03

**Success Criteria** (what must be TRUE):
  1. User opens `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md`, `CONCLUSIONS_CSLC_SELFCONSIST_EU.md`, `CONCLUSIONS_DISP_N_AM.md`, and `CONCLUSIONS_DISP_EU.md` and finds v1.2 sections with final metrics, decisions, and named blockers where applicable (DISP-10, VAL-03).
  2. User opens `docs/validation_methodology.md` and finds v1.2 sections covering CSLC gate promotion, EGMS L2a residual handling, DISP ERA5/deramping/unwrapper diagnostics, and the rationale for any binding thresholds (VAL-02).
  3. User runs the CSLC/DISP-focused eval targets and `results/matrix.md` renders all four CSLC/DISP cells with no empty values and no collapsed product-quality/reference-agreement verdicts (VAL-01, VAL-03).
  4. User opens `.planning/REQUIREMENTS.md` and sees every v1.2 requirement mapped to exactly one phase, with future RTC/DIST/DSWx work still out of scope unless directly tied to CSLC/DISP (DISP-10).

**Plans**: To be generated by `$gsd-plan-phase 12`

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

**Plans**:

- [x] 03-01-PLAN.md — Scaffolding: selfconsistency `median_of_persistent`, criteria `gate_metric_key`, matrix_schema + matrix_writer types, `compare_cslc_egms_l2a_residual`, data/worldcover + data/natural_earth, Makefile + matrix_manifest + pyproject dev extras [Wave 1] [CSLC-03, CSLC-04, CSLC-05]
- [x] 03-02-PLAN.md — CSLC AOI probe script + committed artifact naming 7 candidate burst IDs (4 Mojave + 3 Iberian) with 15-epoch sensing windows + SoCal window lock + user lock-in checkpoint [Wave 1] [CSLC-04, CSLC-05]
- [x] 03-03-PLAN.md — N.Am. CSLC self-consistency eval: SoCal 15-epoch stack + Mojave fallback chain + CONCLUSIONS_CSLC_SELFCONSIST_NAM.md [Wave 2] [CSLC-03, CSLC-04] *(complete 2026-04-24: SoCal coh=0.887 / residual=−0.109 mm/yr; Coso-Searles fallback #1 coh=0.804 / residual=+1.127 mm/yr; CALIBRATING 2/2, 78 min)*
- [x] 03-04-PLAN.md — EU CSLC self-consistency eval: Iberian Meseta + three-number schema (OPERA amp / self-consistency / EGMS L2a residual) + CONCLUSIONS_CSLC_SELFCONSIST_EU.md [Wave 2] [CSLC-05] *(complete 2026-04-24: Iberian coh=0.868 / residual=+0.347 mm/yr; CALIBRATING 1/1, 73 min; EGMS L2a third-number deferred per Bug 8)*
- [x] 03-05-PLAN.md — `docs/validation_methodology.md`: §1 cross-version phase impossibility (kernel argument leads; diagnostic evidence appendix) + §2 product-quality vs reference-agreement distinction (Iberian three-number motivating example; M1+M4 anti-creep both directions) [Wave 3] [CSLC-06] — §3/§4/§5 deferred to Phase 4/5/6/7 per D-15 append-only

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

**Plans**: 5 plans across 4 waves

Plans:
- [x] 04-01-PLAN.md — Schema + selfconsistency ramp helpers: matrix_schema.py adds DISPCellMetrics + RampAttribution + RampAggregate + PerIFGRamp + DISPProductQualityResultJson; selfconsistency.py adds fit_planar_ramp + compute_ramp_aggregate + auto_attribute_ramp; unit tests [Wave 1] [DISP-02, DISP-03]
- [x] 04-02-PLAN.md — compare_disp.py prepare_for_reference adapter (4 methods × 3 reference_grid forms; explicit method=, no default per DISP-01) + ReferenceGridSpec + 12-cell unit test matrix + DISP-05 no-write-back audit [Wave 1] [DISP-01, DISP-05]
- [x] 04-03-PLAN.md — matrix_writer.py disp:nam + disp:eu render branches (CALIBRATING italics on PQ + non-italics PASS/FAIL on RA + attributed_source label inline; DISP dispatch BEFORE CSLC self-consist) + tests [Wave 2] [DISP-03]
- [x] 04-04-PLAN.md — run_eval_disp.py + run_eval_disp_egms.py 5 changes per script (REFERENCE_MULTILOOK_METHOD constant, EXPECTED_WALL_S=21600, Stage 9 adapter, Stage 10 PQ block w/ cross-cell coherence read for SoCal, Stage 11 ramp-attribution, Stage 12 DISPCellMetrics write); manifest cache_dir fix; warm re-runs produce metrics.json + meta.json for both cells [Wave 3] [DISP-01, DISP-02, DISP-03, DISP-05]
- [x] 04-05-PLAN.md — Docs+brief: git mv CONCLUSIONS_DISP_EGMS.md → CONCLUSIONS_DISP_EU.md; append v1.1 Product Quality / Reference Agreement / Ramp Attribution / Brief link sections to both CONCLUSIONS files; write DISP_UNWRAPPER_SELECTION_BRIEF.md (4 candidates × 4 columns); append §3 multilook ADR to docs/validation_methodology.md (5-part PITFALLS+FEATURES dialogue) [Wave 4] [DISP-03, DISP-04, DISP-05]

**Requirements coverage audit** (all 5 Phase 4 requirement IDs):
DISP-01 (02, 04), DISP-02 (01, 04), DISP-03 (01, 03, 04, 05), DISP-04 (05), DISP-05 (02, 04, 05). Every requirement appears in at least one plan.

### Phase 5: DIST-S1 OPERA v0.1 + EFFIS EU

**Goal**: Users can run `make eval-dist-nam` to either (a) produce a T11SLT v0.1 quantitative comparison with block-bootstrap CI when the config-drift gate passes, or (b) surface "deferred pending operational reference publication" when v0.1 and dist-s1 2.0.14 defaults materially disagree on any of the 7 key parameters — with an automatic CMR probe that supersedes v0.1 the moment operational `OPERA_L3_DIST-ALERT-S1_V1` publishes; meanwhile EU expands from 1 to 3 events plus EFFIS same-resolution cross-validation with genuine recall+precision criteria.

**Scope amendment (2026-04-25):** Phase 5 success criteria 1, 2, and 3 are deferred to v1.2.
- **Why criterion 1 (DIST-01 CloudFront fetch) is deferred:** RESEARCH Probe 1 found that the OPERA DIST-S1 v0.1 product has no canonical CloudFront URL; OPERA-ADT publishes a notebook recipe (`notebooks/A__E2E_Workflow_Demo.ipynb` Cell 5) that *regenerates* the sample locally via `run_dist_s1_workflow(mgrs_tile_id='11SLT', post_date='2025-01-21', track_number=71, ...)`. The "fetch-and-compare" framing is structurally inapplicable.
- **Why criteria 2 + 3 (DIST-02 config-drift + DIST-03 F1+CI) are deferred:** RESEARCH Probe 6 confirmed that `earthaccess.search_data(short_name='OPERA_L3_DIST-ALERT-S1_V1', ...)` returns an empty result set as of 2026-04-25 (the operational collection has not been published). Without an operational reference, F1+CI computation has no target.
- **What still ships in Phase 5:** criteria 4 (DIST-04 CMR auto-supersede probe; Stage 0 of `run_eval_dist.py` runs every invocation and writes a `cell_status='DEFERRED'` metrics.json on miss; auto-fills when operational publishes), 5 (DIST-05 EFFIS WFS cross-validation), 6 (DIST-06 EU 3-event aggregate), and 7 (DIST-07 chained `prior_dist_s1_product` retry on Aveiro stack). Bootstrap CI methodology (`validation/bootstrap.py`) ships now and is used for EU per-event F1.
- **EMSR correction:** the Evros 2023 wildfire EMS activation is **EMSR686**, not EMSR649 (RESEARCH Probe 8 — EMSR649 was an Italian flood). The roadmap text below previously said "EMSR649"; treat all references to that activation ID in Phase 5 work as EMSR686.
- **Romania substitution:** the third EU event in Phase 5 is **Spain Sierra de la Culebra June 2022** (~26,000 ha; RESEARCH Probe 4 ADR), not the originally-listed "2022 Romanian forest clear-cuts". EFFIS is fire-only and does not cover clear-cut logging (PITFALLS P4.5); Romania 2022 had no fire-event EFFIS coverage that aligns with subsideo's pipeline window.
- **D-18 amendment (EFFIS WFS dispatch):** CONTEXT.md D-18 originally bound EFFIS WFS access to `harness.download_reference_with_retry(source='effis')`. That contract returns a `Path` to a downloaded artifact, which is incompatible with `owslib.wfs.WebFeatureService.getfeature(...)` whose response is an in-memory stream parsed by `geopandas.read_file(BytesIO(...))`. D-18 is therefore amended: `validation/effis.py` calls `owslib.wfs.WebFeatureService` directly. Retry semantics still come from `harness.RETRY_POLICY['EFFIS']` (Plan 05-04 lands the dict entry); `effis.py` reads that policy and applies it inline via a thin retry wrapper (e.g. `tenacity.Retrying(...)` keyed on the policy's `retry_on`/`abort_on` lists, or an equivalent urllib3 retry adapter on the owslib session). The harness still owns the policy declaration; only the dispatch entry-point shifts.
- **D-24 amendment (matrix_writer dispatch ordering):** CONTEXT.md D-24 originally locked DIST render branches to insert "BEFORE DSWx (which Phase 6 will add) but AFTER existing DISP branches per Phase 4 D-08 ordering invariant". The structurally-meaningful invariant is the AFTER-disp:* part: schemas are disjoint, but disp:* and dist:eu both have valid metrics.json sidecars when both phases land, and disp:* must be checked first because its `ramp_attribution` discriminator is unambiguous. The BEFORE part (cslc:* / dswx:*) is a contemporary observation, not a forward lock — Phase 6 may legitimately re-order DSWx ahead of DIST as new schemas land. Plan 05-05's `test_dispatch_ordering_dist_before_cslc` test therefore asserts only `disp_call < dist_eu_call AND dist_eu_call < dist_nam_call` (the structurally meaningful pair), leaving the pre-cslc relationship as an unverified contemporary state.

**Depends on**: Phase 1 (`_mp.py` full bundle resolves the dist-s1 hang; harness CloudFront path with per-source retry policy)

**Requirements**: DIST-01, DIST-02, DIST-03, DIST-04, DIST-05, DIST-06, DIST-07

**Success Criteria** (what must be TRUE):
  1. User runs the DIST LA eval and the OPERA v0.1 T11SLT sample is fetched from CloudFront (`d2pn8kiwq2w21t.cloudfront.net/...T11SLT_20250121T015030Z...`) with exponential-backoff retry and cached under `eval-dist/opera_reference/v0.1_T11SLT/` — the sample is preserved on disk regardless of downstream comparison outcome (DIST-01) [deferred to v1.2]
  2. Before T11SLT quantitative comparison runs, a config-drift gate extracts the OPERA v0.1 sample's 7 key processing parameters (confirmation-count threshold, pre-image strategy, post-date buffer, baseline window length, despeckle settings + 2 further) and compares against dist-s1 2.0.14 defaults; when material deltas are found the matrix cell reads "deferred pending operational reference publication" and continues (DIST-02, prevents PITFALLS P4.1) [deferred to v1.2]
  3. When the config-drift gate passes, the T11SLT comparison reports F1 / precision / recall / accuracy with block-bootstrap 95% CI (1 km blocks, B=500); the matrix cell shows point estimate AND CI; criteria stay F1 > 0.80 and accuracy > 0.85 without tightening toward v0.1's own score (DIST-03, prevents PITFALLS P4.2 single-tile variance + M1 target-creep) [deferred to v1.2]
  4. `make eval-dist-nam` includes a CMR probe for operational `OPERA_L3_DIST-ALERT-S1_V1`; on discovery the operational reference supersedes the v0.1 result in the matrix with no manual intervention and no re-planning (DIST-04) [Phase 5 deliverable]
  5. User runs EFFIS cross-validation against cached Aveiro/Viseu 2024 subsideo output via `owslib` WFS and the matrix reports precision > 0.70 AND recall > 0.50 (DIST-05); aggregate `CONCLUSIONS_DIST_EU.md` covers 3 events — 2024 Portuguese wildfires + 2023 Evros Greece EMSR686 + 2022 Spain Sierra de la Culebra wildfire (substituted from Romania per EFFIS coverage gap) (DIST-06) [Phase 5 deliverable]
  6. After Phase 1's `_mp.py` bundle lands, the chained `prior_dist_s1_product` run on the DIST EU stack (Sep 28 → Oct 10 → Nov 15) is retried; success is reported as a DIFFERENTIATOR, failure is filed upstream with dist-s1 maintainers and is non-blocking to milestone closure (DIST-07) [Phase 5 deliverable]

**Plans**: 9 plans across 6 waves

Plans:
- [x] 05-01-PLAN.md — ROADMAP + REQUIREMENTS scope amendment (defer DIST-01/02/03; correct EMSR686; document Spain substitution; D-18 + D-24 amendments; RESEARCH Resolution Log) [Wave 0] [DIST-01, DIST-02, DIST-03]
- [x] 05-02-PLAN.md — EFFIS WFS endpoint GetCapabilities probe + lock artifact [Wave 0] [DIST-05, DIST-06]
- [x] 05-03-PLAN.md — Pure-additive scaffolding: bootstrap.py module + matrix_schema.py 7 EU types + minimal DistNamCellMetrics-Deferred [Wave 1] [DIST-03, DIST-05, DIST-06, DIST-07]
- [x] 05-04-PLAN.md — harness.RETRY_POLICY['EFFIS'] + pyproject.toml owslib pip pin [Wave 1] [DIST-05]
- [x] 05-05-PLAN.md — validation/effis.py (WFS query + dual rasterise) + matrix_writer dist:nam (DEFERRED) + dist:eu (X/3 PASS) render branches [Wave 2] [DIST-04, DIST-05, DIST-06]
- [x] 05-06-PLAN.md — run_eval_dist.py rewrite: CMR Stage 0 auto-supersede probe + DEFERRED metrics.json write + D-16 archival + unit tests [Wave 2] [DIST-01, DIST-02, DIST-03, DIST-04]
- [x] 05-07-PLAN.md — run_eval_dist_eu.py rewrite as declarative EVENTS list (Aveiro chained triple including missing Oct 10 + Evros EMSR686 + Spain Culebra) + track_number probe [Wave 3] [DIST-05, DIST-06, DIST-07]
- [x] 05-08-PLAN.md — Cache directory cleanup: eval-dist → eval-dist-park-fire rename; eval-dist-eu* → eval-dist_eu consolidation; delete run_eval_dist_eu_nov15.py [Wave 4] [DIST-04, DIST-06]
- [x] 05-09-PLAN.md — Docs: docs/validation_methodology.md §4 append + CONCLUSIONS_DIST_N_AM.md (deferred sub-section) + CONCLUSIONS_DIST_EU.md (3-event sub-section) [Wave 5] [DIST-04, DIST-05, DIST-06, DIST-07]

**Requirements coverage audit** (all 7 Phase 5 requirement IDs):
DIST-01 (01, 06), DIST-02 (01, 06), DIST-03 (01, 03, 06), DIST-04 (01, 05, 06, 08, 09), DIST-05 (02, 03, 04, 05, 07, 09), DIST-06 (01, 02, 03, 05, 07, 08, 09), DIST-07 (03, 07, 09). Every requirement appears in at least one plan.

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

**Plans**: 7 plans across 5 waves

Plans:
- [x] 06-01-PLAN.md — Probe artifacts: dswx_fitset_aoi_candidates.md (5+1 AOIs locked) + PROTEUS ATBD ceiling chain probe + dswx_aoi_selection.ipynb + dswx_failure_modes.yml + Makefile recalibrate-dswx + dswx-fitset-aoi-md targets + USER LOCK-IN CHECKPOINT [Wave 1] [DSWX-02, DSWX-03, DSWX-07]
- [x] 06-02-PLAN.md — Foundation scaffolding: dswx_thresholds.py (frozen+slots DSWEThresholds + 2 instances + dispatch dict) + Settings.dswx_region env-var + criteria.py dswx.nam.investigation_f1_max INVESTIGATION_TRIGGER + harness.RETRY_POLICY['jrc'] + matrix_schema 6 new Pydantic types (DswxNamCellMetrics + DswxEUCellMetrics + 4 helpers) [Wave 1] [DSWX-05, DSWX-06]
- [x] 06-03-PLAN.md — dswx.py decomposition (compute_index_bands + score_water_class_from_indices + IndexBands public API) + DELETE 3 module-level constants (WIGT/AWGT/PSWT2_MNDWI) + KEEP 8 (PSWT1_*/PSWT2_BLUE/NIR/SWIR1/SWIR2) + thread thresholds keyword + DSWxConfig.region field + run_dswx region resolution [Wave 2] [DSWX-04, DSWX-05]
- [x] 06-04-PLAN.md — compare_dswx shoreline 1-pixel buffer (D-16 uniform application) + JRC retry refactor via harness.download_reference_with_retry(source='jrc') + matrix_writer dswx render branches (_is_dswx_*_shape + _render_dswx_*_cell; AFTER dist:* per D-27) [Wave 2] [DSWX-06]
- [x] 06-05-PLAN.md — N.Am. positive control: run_eval_dswx_nam.py NEW (10-stage CANDIDATES iteration + INVESTIGATION_TRIGGER halt) + execute eval + CONCLUSIONS_DSWX_N_AM.md NEW + USER CHECKPOINT [Wave 3] [DSWX-01] — F1=0.9252 PASS (Lake Tahoe T10SFH); EU recalibration cleared; checkpoint APPROVED
- [x] 06-06-PLAN.md — Recalibration pipeline: 3-iteration grid search exhausted; honest BLOCKER (fit_set_mean_f1=0.2092 across all 1395 gridpoints); HLS→S2 L2A spectral transfer gap diagnosed; THRESHOLDS_EU unchanged (PROTEUS defaults); CONCLUSIONS_DSWX_EU_RECALIB.md written; Stage 0 assert relaxed to warning; Plan 06-07 unblocked [Wave 4] [DSWX-03, DSWX-04, DSWX-05, DSWX-06]
- [x] 06-07-PLAN.md — EU re-run + reporting: run_eval_dswx.py 5 changes (region='eu', tuple-unpack, DswxEUCellMetrics, recalibration results read) + execute Balaton EU re-run + CONCLUSIONS_DSWX.md v1.0 baseline preamble + 3 v1.1 sections + docs/validation_methodology.md §5 (5 sub-sections) + matrix.md regen [Wave 5] [DSWX-06, DSWX-07]

**Requirements coverage audit** (all 7 Phase 6 requirement IDs):
DSWX-01 (05), DSWX-02 (01), DSWX-03 (01, 06), DSWX-04 (03, 06), DSWX-05 (02, 03, 06), DSWX-06 (02, 04, 06, 07), DSWX-07 (01, 07). Every requirement appears in at least one plan.

**Plan-phase commits resolved**:
- AOI fit-set lock: 5 EU biomes (Alcántara / Tagus / Vänern / Garda / Doñana) + Balaton held-out per CONTEXT D-01 + Plan 06-01 user checkpoint
- N.Am. positive-control candidates: Tahoe T10SFH + Pontchartrain T15RYP per CONTEXT D-18 + Plan 06-01 STAC verification
- PROTEUS ATBD ceiling: own-data fallback default per CONTEXT D-17 path (d); Plan 06-01 may resolve via path (a) Product Spec PDF download
- pyarrow availability: parquet for gridscores per CONTEXT D-07; pyarrow 23.0.0 verified present
- Decomposition shape: clean 2-function split (compute_index_bands + score_water_class_from_indices) + IndexBands public dataclass per CONTEXT D-05
- EXPECTED_WALL_S: 1800s (run_eval_dswx_nam.py) + 21600s (recalibrate_dswe_thresholds.py) per CONTEXT D-24


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

**Plans**: 3 plans across 2 waves

Plans:
- [x] 07-01-PLAN.md — RTC:NAM DEFERRED sidecar + matrix_writer DEFERRED branch + CALIBRATING binds v1.2 annotations (3 sites) + matrix.md regen [Wave 1] [REL-01, REL-02, REL-05]
- [x] 07-02-PLAN.md — validation_methodology.md §6 + §7 + TOC + §2.6 stale forward-ref fixes + missing anchors (pq-vs-ra, dist-methodology) [Wave 1] [REL-03]
- [x] 07-03-PLAN.md — pytest closure test + CHANGELOG.md v1.1 entry (REL-04 TrueNAS deferral note) [Wave 2] [REL-04, REL-06]

**Requirements coverage audit** (all 6 Phase 7 requirement IDs):
REL-01 (01), REL-02 (01), REL-03 (02), REL-04 (03), REL-05 (01), REL-06 (03). Every requirement appears in at least one plan.

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
| 1. Environment Hygiene, Framework Consolidation & Guardrail Scaffolding | v1.1 | 9/9 | Complete | 2026-04-22 |
| 2. RTC-S1 EU Validation | v1.1 | 5/5 | Complete (3/5 PASS w/ investigation) | 2026-04-23 |
| 3. CSLC-S1 Self-Consistency + EU Validation | v1.1 | 5/5 | Complete (SoCal/Mojave/Iberian CALIBRATING PASS) | 2026-04-25 |
| 4. DISP-S1 Comparison Adapter + Honest FAIL | v1.1 | 5/5 | Complete (honest FAIL on r > 0.92 + bias < 3 mm/yr; cells MIXED with attributed_source=inconclusive; v1.2 follow-up scoped via DISP_UNWRAPPER_SELECTION_BRIEF.md) | 2026-04-25 |
| 5. DIST-S1 OPERA v0.1 + EFFIS EU | v1.1 | 9/9 | Complete (infrastructure shipped; EU honest FAIL 0/3 PASS — 3 attributable causes documented for v1.2; DIST-01/02/03 deferred-with-evidence to v1.2) | 2026-04-26 |
| 6. DSWx-S2 N.Am. + EU Recalibration | v1.1 | 7/7 | Complete (N.Am. F1=0.9252 PASS; EU recalib deferred v1.2 HLS→S2 gap; Balaton F1=0.8165 FAIL fit-set quality review) | 2026-04-27 |
| 7. Results Matrix + Release Readiness | v1.1 | 3/3 | Complete (10-cell matrix filled; methodology doc §6+§7; pytest 554/554; REL-04 TrueNAS deferred v1.2) | 2026-04-29 |
