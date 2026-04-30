# Requirements: subsideo v1.1 — N.Am./EU Validation Parity & Scientific PASS

**Defined:** 2026-04-20
**Core Value:** Produce scientifically accurate, OPERA-spec-compliant SAR/InSAR geospatial products over EU AOIs — validated against official reference products to prove correctness.
**Milestone Goal:** Drive every product (RTC, CSLC, DISP, DIST, DSWx) to an unambiguous per-region (N.Am. + EU) PASS, an honest FAIL with named upgrade path, or a deferral with a dated unblock condition — using OPERA/EGMS/JRC/EMS as validators, not as quality ceilings.
**Source scope doc:** `BOOTSTRAP_V1.1.md` (2026-04-20)
**Source research:** `.planning/research/SUMMARY.md` (with 4 BOOTSTRAP corrections surfaced)

---

## v1.1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Environment & Framework Consolidation

- [x] **ENV-01**: User can install a fresh environment via `micromamba env create -f conda-env.yml` with zero post-install pip commands required to run any eval script (tophu installed from conda-forge, not pip; numpy < 2.0 pinned)
- [x] **ENV-02**: No runtime monkey-patches exist in `src/subsideo/products/*.py` (the four `_patch_*` calls in `cslc.py` for numpy-2 compat are removed); unit tests pass under the numpy<2 pin
- [x] **ENV-03**: All `rio_cogeo` imports route through `src/subsideo/_cog.py` (a version-aware shim pinning `rio-cogeo==6.0.0` — do NOT adopt 7.x, which drops Python 3.10 support)
- [x] **ENV-04**: macOS multiprocessing fork-mode bundle is invoked at the top of every `run_*()` product entry point via `src/subsideo/_mp.configure_multiprocessing()` (start method + `MPLBACKEND=Agg` + `RLIMIT_NOFILE` raise + pre-fork requests.Session closure + forkserver fallback on Python ≥3.14)
- [x] **ENV-05**: A subprocess-level watchdog aborts any `run_*()` invocation after 2× expected wall time at zero throughput and cleans up grandchild processes via `os.killpg`; three consecutive fresh `run_eval_dist*.py` runs succeed on macOS without hanging
- [x] **ENV-06**: `src/subsideo/validation/harness.py` exposes `select_opera_frame_by_utc_hour`, `download_reference_with_retry` (supports Earthdata, CDSE, and plain HTTPS/CloudFront auth backends), `ensure_resume_safe`, `credential_preflight`, and `bounds_for_burst`
- [x] **ENV-07**: All existing eval scripts (`run_eval.py`, `run_eval_cslc.py`, `run_eval_disp.py`, `run_eval_disp_egms.py`, `run_eval_dist.py`, `run_eval_dist_eu.py`, `run_eval_dswx.py`) are refactored to consume `validation.harness`; diffs between equivalent eval scripts contain only reference-data differences, not plumbing differences
- [x] **ENV-08**: No hand-coded geographic bounds exist in any eval script — all bounds derive from burst/MGRS-tile ID via `harness.bounds_for_burst()`
- [x] **ENV-09**: User can invoke `make eval-all`, `make eval-nam`, `make eval-eu`, and `make eval-{product}-{region}` targets; failure in one cell does not block matrix generation for the remaining cells (per-cell subprocess isolation with `meta.json` sidecar capturing git SHA + input content hashes)
- [x] **ENV-10**: A committed `env.lockfile.txt` and a reproducibility recipe (Dockerfile or Apptainer definition) pin a specific resolved environment used by the milestone closure test

### Metrics-vs-Targets Guardrails (cross-cutting)

- [x] **GATE-01**: `src/subsideo/validation/criteria.py` exists as an immutable module with `CALIBRATING` vs `BINDING` criterion types and a `binding_after_milestone` field on every calibrating gate
- [x] **GATE-02**: Validation result dataclasses are split into `ProductQualityResult` and `ReferenceAgreementResult`; no top-level single `.passed` collapses the two, and no downstream writer (CONCLUSIONS template, matrix writer, report) may merge them
- [x] **GATE-03**: `results/matrix.md` reports product-quality and reference-agreement as two distinct columns per (product, region) cell; `CALIBRATING` cells are visually distinguishable from `BINDING` cells
- [x] **GATE-04**: Test suite is split into `tests/product_quality/` (asserts measured values) and `tests/reference_agreement/` (asserts plumbing only — never asserts reference-agreement thresholds)
- [x] **GATE-05**: Every new product-quality gate introduced in v1.1 (CSLC self-consistency coherence, residual mean velocity, DISP self-consistency) ships as `CALIBRATING` and requires ≥3 measured data points before promotion to `BINDING` in a future milestone

### RTC-S1 EU Validation

- [x] **RTC-01**: User can run `make eval-rtc-eu` and obtain per-burst PASS/FAIL across 3-5 EU bursts spanning ≥3 terrain regimes (alpine, plain, arid, boreal, wildfire); at least one burst has >1000 m relief AND at least one burst is >55°N
- [x] **RTC-02**: EU RTC reference-agreement criteria (RMSE < 0.5 dB, r > 0.99) are identical to N.Am. and DO NOT tighten based on per-burst scores — even if burst RMSE lands in the 0.04–0.1 dB range consistent with N.Am.
- [x] **RTC-03**: `CONCLUSIONS_RTC_EU.md` documents the selected bursts, regime coverage, and per-burst numerical results; any burst showing materially different RMSE than N.Am. triggers an investigation finding in the same doc

### CSLC-S1 Self-Consistency Gate + EU Validation

- [x] **CSLC-01**: `src/subsideo/validation/stable_terrain.py` constructs a stable-terrain mask for a given burst footprint from ESA WorldCover class 60 (bare/sparse vegetation) + slope < 10° + coastline buffer + water-body exclusion
- [x] **CSLC-02**: `src/subsideo/validation/selfconsistency.py` computes sequential 12-day interferometric coherence statistics (mean, median, persistently-coherent fraction) and residual mean velocity over a stable-terrain mask for a given CSLC stack
- [x] **CSLC-03**: SoCal self-consistency eval (burst `t144_308029_iw1`, 15 dates, 14 sequential IFGs) reports self-consistency coherence > 0.7 (CALIBRATING gate) and residual mean velocity < 5 mm/yr over OPERA-CSLC-derived stable pixels
- [x] **CSLC-04**: Mojave Desert self-consistency eval (Coso/Searles Valley primary, or a documented-stable AOI from the 3-candidate fallback list — Pahranagat Valley / Amargosa Valley / Hualapai Plateau) passes the same self-consistency gate, OR exhaustion of the fallback list surfaces a Phase blocker
- [x] **CSLC-05**: Iberian Meseta EU eval (primary: bedrock/sparse-vegetation burst north of Madrid; fallbacks: Alentejo / Massif Central) reports (a) OPERA CSLC amplitude reference-agreement r > 0.6, RMSE < 4 dB; (b) self-consistency coherence > 0.7 over stable terrain; (c) EGMS L2a stable-PS residual mean velocity < 5 mm/yr
- [x] **CSLC-06**: Cross-version phase comparison methodology is consolidated in `docs/validation_methodology.md` with the diagnostic evidence (removal of carrier, flattening, both — still yields zero coherence across isce3 major versions)

### DISP-S1 Comparison Adapter + Honest FAIL

- [x] **DISP-01**: `subsideo.validation.compare_disp.prepare_for_reference(native_velocity, reference_grid, method=...)` is validation-only infrastructure that multilooks subsideo's native 5×10 m velocity to a reference grid (30 m raster for OPERA DISP OR point coordinates for EGMS L2a PS); `method=` has no default and must be explicit; the function never writes back to the product
- [x] **DISP-02**: DISP self-consistency product-quality gate (sequential 12-day coherence > 0.7 and residual mean velocity < 5 mm/yr on stable terrain at native 5×10 m resolution) is computed for both N.Am. (SoCal) and EU (Bologna) from cached CSLC stacks
- [x] **DISP-03**: N.Am. and EU DISP re-runs from cached CSLCs report reference-agreement (r vs OPERA DISP-S1 at 30 m; r vs EGMS L2a at PS points) separately from product-quality results; any observed planar ramp is labelled by attributed source (PHASS / tropospheric / orbit / ionospheric) via a ramp-attribution diagnostic (POEORB swap, ERA5 toggle, ramp-direction stability test)
- [x] **DISP-04**: A one-page "DISP Unwrapper Selection" follow-up milestone scoping brief is delivered as a Phase artifact, grounded in the fresh FAIL numbers and listing candidate approaches (PHASS+deramping, SPURT native, tophu-SNAPHU tiled, 20×20 m fallback) with a success criterion per approach
- [x] **DISP-05**: Native 5×10 m resolution remains the production default for DISP-S1; downsampling to the reference grid lives exclusively in `prepare_for_reference` and is documented as validation-only in both code and methodology doc

### DIST-S1 OPERA v0.1 Sample Comparison + EU Tightening

- [ ] **DIST-01**: [deferred to v1.2 — see Scope amendment in ROADMAP.md Phase 5; OPERA v0.1 sample has no canonical CloudFront URL per RESEARCH Probe 1] The OPERA DIST v0.1 sample for MGRS tile T11SLT is fetched via CloudFront direct-download with exponential-backoff retry (via harness) and cached under `eval-dist/opera_reference/v0.1_T11SLT/` (the sample is preserved on disk regardless of downstream comparison outcome).
- [ ] **DIST-02**: [deferred to v1.2 — operational reference not yet published per RESEARCH Probe 6 + DIST-01 deferral] Before running the T11SLT quantitative comparison, a config-drift gate extracts the OPERA v0.1 sample's 7 key processing parameters (confirmation-count threshold, pre-image strategy, post-date buffer, baseline window length, despeckle settings + 2 further) and compares against dist-s1 2.0.14 defaults; material deltas cause skip-and-defer (matrix cell reads "deferred pending operational reference publication").
- [ ] **DIST-03**: [deferred to v1.2 — F1+CI vs operational reference is moot until reference exists per RESEARCH Probe 6] When the config-drift gate passes, T11SLT comparison computes F1 / precision / recall / accuracy with block-bootstrap confidence interval (1 km blocks, B=500); matrix cell reports point estimate AND CI; criteria remain F1 > 0.80 and accuracy > 0.85 without tightening toward v0.1's own score.
- [x] **DIST-04**: `make eval-dist-nam` includes a CMR probe for operational `OPERA_L3_DIST-ALERT-S1_V1` publication; on discovery, the operational reference supersedes the v0.1 result in the matrix without manual intervention
- [x] **DIST-05**: EFFIS same-resolution-optical cross-validation runs against cached Aveiro/Viseu 2024 subsideo output via `owslib` WFS and reports precision > 0.70 AND recall > 0.50 against EFFIS burnt-area perimeters [infrastructure delivered; honest FAIL 0/3 events — 3 attributable causes documented for v1.2 fix paths]
- [x] **DIST-06**: EU DIST coverage expands from 1 event to 3 (2024 Portuguese wildfires + 2023 Evros Greece EMSR686 + 2022 Spain Sierra de la Culebra wildfire — Romania substituted per EFFIS coverage gap; EMSR649 corrected to EMSR686 per RESEARCH Probe 8) with aggregate results in `CONCLUSIONS_DIST_EU.md`
- [x] **DIST-07**: After Phase 1 `_mp.py` bundle lands, the chained `prior_dist_s1_product` run is retried on the DIST EU stack (Sep 28 → Oct 10 → Nov 15); success is reported as a DIFFERENTIATOR, failure is filed upstream with dist-s1 maintainers (non-blocking)

### DSWx-S2 N.Am. Validation + EU Recalibration

- [x] **DSWX-01**: N.Am. DSWx-S2 positive control eval runs on a selected AOI (Lake Tahoe or Lake Pontchartrain) and reports F1 against JRC Monthly History; F1 < 0.85 triggers regression investigation (BOA offset / Claverie cross-calibration) before recalibration proceeds — F1=0.9252 PASS (Lake Tahoe T10SFH, July 2021)
- [x] **DSWX-02**: EU fit-set AOI selection is documented in `notebooks/dswx_aoi_selection.ipynb` with per-AOI rationale spanning JRC reference quality + S2 cloud-free scene availability + water-body type diversity + absence of known algorithm failure modes (glacier/frozen lake, heavy turbid water, dominant mountain shadow) [partial — notebook exists; per-AOI rationale in `.planning/milestones/v1.1-research/dswx_fitset_aoi_candidates.md` rather than fully consolidated in notebook; not a Phase 6 gate per verifier]
- [x] **DSWX-03**: EU fit set contains 12 (AOI, wet-scene, dry-scene) triples across 6 biome-diverse AOIs (Mediterranean reservoir, Atlantic estuary, boreal lake, Pannonian plain, Alpine valley, Iberian summer-dry); Balaton is held out as independent test set [blocker path satisfied — HLS→S2 L2A spectral transfer gap diagnosed; EU recalibration deferred to v1.2 per CONCLUSIONS_DSWX_EU_RECALIB.md]
- [x] **DSWX-04**: `scripts/recalibrate_dswe_thresholds.py` performs a joint grid search over `WIGT` ([0.08, 0.20] step 0.005), `AWGT` ([−0.1, +0.1] step 0.01), and `PSWT2_MNDWI` ([−0.65, −0.35] step 0.02), optimising mean F1 across the fit set [blocker path satisfied — 3-iteration grid search exhausted; best fit_set_mean_f1=0.2092; root cause documented]
- [x] **DSWX-05**: Recalibrated thresholds live in `src/subsideo/products/dswx_thresholds.py` as a typed constants module with provenance metadata and EU/N.Am. region selector via `pydantic-settings`; `notebooks/dswx_recalibration.ipynb` reproduces the grid search deterministically from the cached fit set
- [x] **DSWX-06**: EU DSWx re-run with recalibrated thresholds reports F1 against JRC without adjusting the F1 > 0.90 bar; fit-set F1 is reported alongside LOO-CV F1 (gap < 0.02 required to rule out overfit); 0.85 ≤ F1 < 0.90 is labelled "FAIL with named ML-replacement upgrade path"; F1 < 0.85 triggers fit-set quality review
- [x] **DSWX-07**: The "DSWE F1 ceiling ≈ 0.92" claim in any FAIL reporting is either ground-referenced to the PROTEUS ATBD (with citation) or documented as "empirical bound observed over our 6-AOI evaluation" — no inherited game-of-telephone citation

### Results Matrix & Release Readiness

- [x] **REL-01**: `make eval-all` writes `results/matrix.md` with all 10 cells (5 products × 2 regions) filled; each cell reports product-quality gate status and reference-agreement numbers in separate columns; CALIBRATING cells are visually distinguishable
- [x] **REL-02**: `results/matrix_manifest.yml` lists expected cells and their per-eval `metrics.json` sidecar paths; the matrix writer reads only from manifest + sidecars (never glob-parses CONCLUSIONS documents)
- [x] **REL-03**: `docs/validation_methodology.md` covers the four methodological findings (cross-version phase impossibility across isce3 major versions, cross-sensor comparison precision-first framing, OPERA frame selection by exact UTC hour + spatial footprint, DSWE-family F1 ≈ 0.92 architectural ceiling) AND explicitly documents the product-quality vs reference-agreement distinction
- [x] **REL-04**: Pre-release audit runs a full `make eval-all` on a freshly-cloned repo inside the homelab TrueNAS Linux dev container; cold-env run completes under 12 h; warm-env re-run completes under 10 min [deferred to v1.2 — infrastructure committed (Dockerfile, Apptainer.def, lockfiles); dated unblock condition in CHANGELOG.md [1.1.0]]
- [x] **REL-05**: At milestone close, every matrix cell is labelled PASS, FAIL-with-named-upgrade-path, or deferred-with-dated-unblock-condition — no cell reads "n/a" or is empty
- [x] **REL-06**: `micromamba env create -f conda-env.yml` on a clean machine completes successfully, and `pytest` passes, as the final closure test

## v2 Requirements

Deferred to future releases. Tracked but not in this milestone.

### RTC Future Work

- **RTC-V2-01**: Corner-reflector absolute radiometric accuracy validation against DLR Kaufbeuren / ESA European calibration sites
- **RTC-V2-02**: Time-series radiometric stability validation (12-month burst, stable-target backscatter)
- **RTC-V2-03**: Parameterised COG compression in `ensure_cog()` (currently hardcoded DEFLATE + 5 overviews; ZSTD/LERC alternatives)
- **RTC-V2-04**: Upstream filings — opera-rtc timestamp-mismatch bug minimal repro; `load_parameters()` auto-call PR

### CSLC Future Work

- **CSLC-V2-01**: GNSS-residual comparison via Nevada Geodetic Laboratory stations with gps2los projection
- **CSLC-V2-02**: Tighten residual velocity bar from 5 mm/yr as stacks lengthen beyond 6 months (1–2 mm/yr typical on 12+ month stacks)
- **CSLC-V2-03**: Tighten amplitude thresholds (r, RMSE) — only after multiple data points and only toward a product-quality target, never toward OPERA's score

### DISP Future Work

- **DISP-V2-01**: DISP Unwrapper Selection dedicated milestone (scope brief delivered as Phase artifact in v1.1)
- **DISP-V2-02**: ERA5 tropospheric correction investigation via pyaps3 (opportunistic; folded into Unwrapper Selection milestone as secondary)
- **DISP-V2-03**: Multi-burst consistency / mosaicking (v2 global work)

### DIST Future Work

- **DIST-V2-01**: Operational monitoring chain with `prior_dist_s1_product` alert promotion (provisional → confirmed) — full operational chain design
- **DIST-V2-02**: Upstream `post_date_buffer_days` default PR to dist-s1 (changed from 1 to 5)
- **DIST-V2-03**: Raise `validate_dist_product` bar via full OPERA product-spec metadata validation through `dist_s1.data_models.output_models.DistS1ProductDirectory`
- **DIST-V2-04**: Re-run against operational OPERA DIST-S1 reference when it ships (CMR-monitored in v1.1 Phase 4)
- **DIST-V2-05**: Re-evaluate DIST-01 / DIST-02 / DIST-03 against operational `OPERA_L3_DIST-ALERT-S1_V1` once the collection publishes in CMR. Inherits the bootstrap CI methodology (`validation/bootstrap.py`) and matrix schema scaffolding shipped in v1.1 Phase 5; only the eval-script Stage 1+2 (regenerate-sample / config-drift / F1+CI) is new work. The CMR auto-supersede probe in `run_eval_dist.py` Stage 0 (DIST-04, shipped in v1.1) makes this a "next eval invocation" event, not a re-planning event. The Phase 5 D-16 archival hook (Plan 05-06: rename existing `eval-dist/metrics.json` → `eval-dist/archive/v0.1_metrics_<mtime>.json` before writing fresh sidecars) is already in place; v1.2 only adds the post-archival population code path.

### DSWx Future Work

- **DSWX-V2-01**: ML-replacement algorithm path (random forest on band composites) — named upgrade path if F1 > 0.92 becomes a product requirement
- **DSWX-V2-02**: Global recalibration expanding fit set from 6 AOIs to 20–30 spanning tropical savanna / rainforest / desert / monsoon / subtropical / cold arid biomes
- **DSWX-V2-03**: Turbid water / frozen lake / mountain shadow / tropical haze handling

### Cross-Cutting Future Work (v2 Global Milestone)

- **CROSS-V2-01**: Burst database globalisation (EU-only → full ~1.5 M bursts)
- **CROSS-V2-02**: Validation framework generalisation to GNSS / tide-gauge / literature-derived references for regions without OPERA or EGMS equivalents
- **CROSS-V2-03**: Data access scaling (CDSE rate limits → AWS Open Data / ASF fallback)

## Out of Scope

Explicitly excluded from v1.1. Documented to prevent scope creep (15 anti-features — 4 from BOOTSTRAP + 11 surfaced by research).

| Feature | Reason |
|---------|--------|
| Global expansion beyond N.Am. and EU | v2 milestone scope; v1.1 is a parity/hardening milestone on two fixed regions |
| ML-based replacements for DSWE threshold algorithms | Named as DSWX-V2-01 upgrade path; in-scope only if F1 > 0.92 becomes a product requirement |
| Relaxing the DSWx F1 > 0.90 bar during recalibration | Moving the goalpost defeats the milestone's honest-FAIL principle |
| New OPERA product classes (DSWx-S1, DSWx-HLS) | v2 milestone scope |
| Multi-burst mosaicking / cross-burst consistency checks | v2 global milestone scope |
| Production DISP unwrapper selection | Spun out to dedicated follow-up milestone; v1.1 ships honest FAIL on current PHASS |
| Gaussian or Lanczos multilooking as default in `prepare_for_reference` | Requires explicit `method=` argument — no default (validation discipline; research identified this as an unresolved Phase 4 ADR) |
| Writing `prepare_for_reference` output back to the product | Validation-only infrastructure — never part of the product |
| New `subsideo validate-dist-la` CLI subcommand | v0.1 fetch happens via eval script + harness; no new public CLI surface |
| README PASS/FAIL badge | Matrix in `results/matrix.md` is the canonical status artifact |
| Tightening RTC EU criteria because N.Am. nailed 0.045 dB | Reference-agreement metrics never tighten based on the reference's own score (GATE-01 target-creep prevention) |
| Tightening CSLC residual velocity bar from 5 mm/yr during v1.1 | CALIBRATING gate requires ≥3 data points before promotion (GATE-05) |
| Interactive AOI picker UI for Phase 6 (DSWx) | Scripted-query notebook is sufficient and more reproducible |
| Medium post / external publication | Publication decision deferred; not a milestone deliverable |
| Docker release as distribution channel | Dockerfile delivered for CI/reproducibility closure test only, not as product distribution |
| Windows native support | ISCE3/GDAL/snaphu conda stack does not build on Windows; WSL2 acceptable |
| Commercial cloud deployment / SDS/PGE orchestration | Library, not pipeline orchestrator |

## Traceability

Which phases cover which requirements. Populated by roadmapper.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ENV-01 | Phase 1 | Complete (Plan 01-01) |
| ENV-02 | Phase 1 | Complete (Plans 01-01 + 01-03) |
| ENV-03 | Phase 1 | Complete (Plan 01-02) |
| ENV-04 | Phase 1 | Complete (Plan 01-03) |
| ENV-05 | Phase 1 | Complete (Plan 01-07) |
| ENV-06 | Phase 1 | Complete (Plan 01-06) |
| ENV-07 | Phase 1 | Complete (Plans 01-06 + 01-07) |
| ENV-08 | Phase 1 | Complete (Plans 01-06 + 01-07) |
| ENV-09 | Phase 1 | Complete (Plans 01-01 + 01-07 + 01-08) |
| ENV-10 | Phase 1 | Complete (Plans 01-01 + 01-09) |
| GATE-01 | Phase 1 | Complete (Plan 01-05) |
| GATE-02 | Phase 1 | Complete (Plan 01-05) |
| GATE-03 | Phase 1 | Complete (Plans 01-08 + 01-09) |
| GATE-04 | Phase 1 | Complete (Plan 01-05) |
| GATE-05 | Phase 1 | Complete (Plan 01-05) |
| RTC-01 | Phase 2 | Complete (2026-04-23) |
| RTC-02 | Phase 2 | Complete (2026-04-23) |
| RTC-03 | Phase 2 | Complete (2026-04-23) |
| CSLC-01 | Phase 1 | Complete (Plan 01-04) |
| CSLC-02 | Phase 1 | Complete (Plan 01-04) |
| CSLC-03 | Phase 3 | Validated (CALIBRATING — SoCal coh_med_of_persistent=0.887 / residual=−0.109 mm/yr; amp_r=0.982 / amp_rmse=1.290 dB) |
| CSLC-04 | Phase 3 | Validated (CALIBRATING — Mojave/Coso-Searles fallback #1 coh_med_of_persistent=0.804 / residual=+1.127 mm/yr; chain short-circuited on first valid fallback per design) |
| CSLC-05 | Phase 3 | Validated-with-deferral (CALIBRATING — Iberian coh_med_of_persistent=0.868 / residual=+0.347 mm/yr; EGMS L2a third-number deferred per Bug 8 follow-up) |
| CSLC-06 | Phase 3 | Validated (Plan 03-05) |
| DISP-01 | Phase 4 | Validated (Plan 04-02 prepare_for_reference adapter; Plan 04-04 callsites in run_eval_disp.py form (b) xr.DataArray + run_eval_disp_egms.py form (c) ReferenceGridSpec; v1.0 Resampling.bilinear callsites removed; explicit method= no default per DISP-01) |
| DISP-02 | Phase 4 | Validated (Plan 04-04 — coherence + residual computed for both cells: SoCal coh_med_of_persistent=0.887 [phase3-cached] / residual=-0.030 mm/yr; Bologna coh_med_of_persistent=0.000 [fresh] / residual=+0.117 mm/yr — both CALIBRATING) |
| DISP-03 | Phase 4 | Validated (Plan 04-04 — RA reported separately from PQ for both cells; per-IFG planar ramp + auto_attribute_ramp diagnostic populated; both cells attributed_source='inconclusive' under deterministic rule with diagnostics b+c deferred per D-09) |
| DISP-04 | Phase 4 | Validated (Plan 04-05 — DISP_UNWRAPPER_SELECTION_BRIEF.md at .planning/milestones/v1.1-research/; 4 candidates × 4 columns; ERA5 toggle recommended first) |
| DISP-05 | Phase 4 | Validated (Plan 04-02 + Plan 04-04 — `prepare_for_reference` is validation-only with SHA256 byte-equal pre/post test; products/disp.py:481 `velocity_path` remains native 5x10 m; eval scripts call adapter for comparison only) |
| DIST-01 | Phase 5 | Deferred to v1.2 (no canonical CloudFront URL per RESEARCH Probe 1; CMR auto-supersede probe in Stage 0 of run_eval_dist.py) |
| DIST-02 | Phase 5 | Deferred to v1.2 (no operational reference per RESEARCH Probe 6; config-drift gate moot until OPERA_L3_DIST-ALERT-S1_V1 publishes) |
| DIST-03 | Phase 5 | Deferred to v1.2 (F1+CI moot without reference; bootstrap.py + schema scaffold shipped and ready) |
| DIST-04 | Phase 5 | Complete (Plan 05-06 — CMR Stage 0 auto-supersede probe; DEFERRED metrics.json write; 3-way dispatch; 4 unit tests) |
| DIST-05 | Phase 5 | Satisfied-honest-FAIL (Plans 05-04 + 05-05 + 05-07 — EFFIS WFS REST pivot per Probe 3; infrastructure complete; 0/3 events pass quantitative threshold; 3 attributable causes documented in CONCLUSIONS_DIST_EU.md for v1.2 fix paths) |
| DIST-06 | Phase 5 | Complete (Plans 05-07 + 05-08 + 05-09 — 3 events: aveiro + evros EMSR686 + spain_culebra; Romania/EMSR649 corrected per RESEARCH Probe 8) |
| DIST-07 | Phase 5 | Complete (Plan 05-07 — chained prior_dist_s1_product retry wired; upstream dist_s1 macOS multiprocessing failure documented; non-blocking) |
| DSWX-01 | Phase 6 | Complete (Plan 06-05 — F1=0.9252 Lake Tahoe T10SFH PASS) |
| DSWX-02 | Phase 6 | Partial (Plan 06-01 — notebook exists; per-AOI rationale in .planning/milestones/v1.1-research/dswx_fitset_aoi_candidates.md; not consolidated in notebook; not a Phase 6 gate per verifier) |
| DSWX-03 | Phase 6 | Complete (blocker path — Plan 06-01 fit-set lock; HLS→S2 L2A spectral transfer gap diagnosed in Plan 06-06; EU recalibration deferred to v1.2) |
| DSWX-04 | Phase 6 | Complete (blocker path — Plan 06-06; 3-iteration grid search exhausted; best fit_set_mean_f1=0.2092; WIGT edge trigger confirmed root cause) |
| DSWX-05 | Phase 6 | Complete (Plans 06-02 + 06-03 + 06-06 — frozen+slots DSWEThresholds + THRESHOLDS_NAM + THRESHOLDS_EU + THRESHOLDS_BY_REGION; Settings.dswx_region env-var; provenance metadata) |
| DSWX-06 | Phase 6 | Complete (Plan 06-07 — EU F1=0.8165 FAIL with named_upgrade_path='fit-set quality review'; bar unchanged at 0.90; LOO-CV gap=nan documented) |
| DSWX-07 | Phase 6 | Complete (Plan 06-07 — OPERA Cal/Val F1_OSW=0.8786 mean N=52 scenes; '0.92 ceiling' ground-referenced; gate at 0.90 above Cal/Val baseline) |
| REL-01 | Phase 7 | Complete (Plan 07-01 — 10 cells filled; zero RUN_FAILED; CALIBRATING italicised) |
| REL-02 | Phase 7 | Complete (Plan 07-01 — manifest-driven; no CONCLUSIONS glob-parse confirmed by test_matrix_writer_reads_only_manifest) |
| REL-03 | Phase 7 | Complete (Plan 07-02 — 808-line methodology doc; TOC + §1-§7; 4 methodological findings + pq-vs-ra distinction) |
| REL-04 | Phase 7 | Deferred with dated unblock (Plan 07-03 — Dockerfile + Apptainer.def + lockfiles committed; CHANGELOG.md [1.1.0] §Deferred to v1.2; unblock: provision TrueNAS Linux dev container + docker build + make eval-all) |
| REL-05 | Phase 7 | Complete (Plan 07-01 — all 10 cells labelled PASS/FAIL/DEFERRED/CALIBRATING; no n/a or empty) |
| REL-06 | Phase 7 | Complete (Plan 07-03 — 554 passed, 1 skipped, 0 failed; live confirmed) |

**Coverage:**
- v1.1 requirements: 49 total (10 ENV + 5 GATE + 3 RTC + 6 CSLC + 5 DISP + 7 DIST + 7 DSWX + 6 REL)
- Mapped to phases: 49
- Unmapped: 0

**Per-phase counts:**
- Phase 1 (Environment Hygiene, Framework Consolidation & Guardrail Scaffolding): 17 (ENV-01..10, GATE-01..05, CSLC-01..02)
- Phase 2 (RTC-S1 EU Validation): 3 (RTC-01..03)
- Phase 3 (CSLC-S1 Self-Consistency + EU Validation): 4 (CSLC-03..06)
- Phase 4 (DISP-S1 Comparison Adapter + Honest FAIL): 5 (DISP-01..05)
- Phase 5 (DIST-S1 OPERA v0.1 + EFFIS EU): 7 (DIST-01..07; DIST-01/02/03 deferred to v1.2 per scope amendment 2026-04-25 — see ROADMAP.md Phase 5 scope amendment block)
- Phase 6 (DSWx-S2 N.Am. + EU Recalibration): 7 (DSWX-01..07)
- Phase 7 (Results Matrix + Release Readiness): 6 (REL-01..06)

---
*Requirements defined: 2026-04-20*
*Last updated: 2026-04-30 after v1.1 milestone close — all 28 stale Pending rows updated to reflect VERIFICATION.md statuses; DIST-06 event names corrected (EMSR686, Spain Culebra); DISP-02/03/04 newlines normalised*
