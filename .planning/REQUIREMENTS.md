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

- [ ] **ENV-01**: User can install a fresh environment via `micromamba env create -f conda-env.yml` with zero post-install pip commands required to run any eval script (tophu installed from conda-forge, not pip; numpy < 2.0 pinned)
- [ ] **ENV-02**: No runtime monkey-patches exist in `src/subsideo/products/*.py` (the four `_patch_*` calls in `cslc.py` for numpy-2 compat are removed); unit tests pass under the numpy<2 pin
- [ ] **ENV-03**: All `rio_cogeo` imports route through `src/subsideo/_cog.py` (a version-aware shim pinning `rio-cogeo==6.0.0` — do NOT adopt 7.x, which drops Python 3.10 support)
- [ ] **ENV-04**: macOS multiprocessing fork-mode bundle is invoked at the top of every `run_*()` product entry point via `src/subsideo/_mp.configure_multiprocessing()` (start method + `MPLBACKEND=Agg` + `RLIMIT_NOFILE` raise + pre-fork requests.Session closure + forkserver fallback on Python ≥3.14)
- [ ] **ENV-05**: A subprocess-level watchdog aborts any `run_*()` invocation after 2× expected wall time at zero throughput and cleans up grandchild processes via `os.killpg`; three consecutive fresh `run_eval_dist*.py` runs succeed on macOS without hanging
- [ ] **ENV-06**: `src/subsideo/validation/harness.py` exposes `select_opera_frame_by_utc_hour`, `download_reference_with_retry` (supports Earthdata, CDSE, and plain HTTPS/CloudFront auth backends), `ensure_resume_safe`, `credential_preflight`, and `bounds_for_burst`
- [ ] **ENV-07**: All existing eval scripts (`run_eval.py`, `run_eval_cslc.py`, `run_eval_disp.py`, `run_eval_disp_egms.py`, `run_eval_dist.py`, `run_eval_dist_eu.py`, `run_eval_dswx.py`) are refactored to consume `validation.harness`; diffs between equivalent eval scripts contain only reference-data differences, not plumbing differences
- [ ] **ENV-08**: No hand-coded geographic bounds exist in any eval script — all bounds derive from burst/MGRS-tile ID via `harness.bounds_for_burst()`
- [ ] **ENV-09**: User can invoke `make eval-all`, `make eval-nam`, `make eval-eu`, and `make eval-{product}-{region}` targets; failure in one cell does not block matrix generation for the remaining cells (per-cell subprocess isolation with `meta.json` sidecar capturing git SHA + input content hashes)
- [ ] **ENV-10**: A committed `env.lockfile.txt` and a reproducibility recipe (Dockerfile or Apptainer definition) pin a specific resolved environment used by the milestone closure test

### Metrics-vs-Targets Guardrails (cross-cutting)

- [ ] **GATE-01**: `src/subsideo/validation/criteria.py` exists as an immutable module with `CALIBRATING` vs `BINDING` criterion types and a `binding_after_milestone` field on every calibrating gate
- [ ] **GATE-02**: Validation result dataclasses are split into `ProductQualityResult` and `ReferenceAgreementResult`; no top-level single `.passed` collapses the two, and no downstream writer (CONCLUSIONS template, matrix writer, report) may merge them
- [ ] **GATE-03**: `results/matrix.md` reports product-quality and reference-agreement as two distinct columns per (product, region) cell; `CALIBRATING` cells are visually distinguishable from `BINDING` cells
- [ ] **GATE-04**: Test suite is split into `tests/product_quality/` (asserts measured values) and `tests/reference_agreement/` (asserts plumbing only — never asserts reference-agreement thresholds)
- [ ] **GATE-05**: Every new product-quality gate introduced in v1.1 (CSLC self-consistency coherence, residual mean velocity, DISP self-consistency) ships as `CALIBRATING` and requires ≥3 measured data points before promotion to `BINDING` in a future milestone

### RTC-S1 EU Validation

- [x] **RTC-01**: User can run `make eval-rtc-eu` and obtain per-burst PASS/FAIL across 3-5 EU bursts spanning ≥3 terrain regimes (alpine, plain, arid, boreal, wildfire); at least one burst has >1000 m relief AND at least one burst is >55°N
- [x] **RTC-02**: EU RTC reference-agreement criteria (RMSE < 0.5 dB, r > 0.99) are identical to N.Am. and DO NOT tighten based on per-burst scores — even if burst RMSE lands in the 0.04–0.1 dB range consistent with N.Am.
- [x] **RTC-03**: `CONCLUSIONS_RTC_EU.md` documents the selected bursts, regime coverage, and per-burst numerical results; any burst showing materially different RMSE than N.Am. triggers an investigation finding in the same doc

### CSLC-S1 Self-Consistency Gate + EU Validation

- [ ] **CSLC-01**: `src/subsideo/validation/stable_terrain.py` constructs a stable-terrain mask for a given burst footprint from ESA WorldCover class 60 (bare/sparse vegetation) + slope < 10° + coastline buffer + water-body exclusion
- [ ] **CSLC-02**: `src/subsideo/validation/selfconsistency.py` computes sequential 12-day interferometric coherence statistics (mean, median, persistently-coherent fraction) and residual mean velocity over a stable-terrain mask for a given CSLC stack
- [x] **CSLC-03**: SoCal self-consistency eval (burst `t144_308029_iw1`, 15 dates, 14 sequential IFGs) reports self-consistency coherence > 0.7 (CALIBRATING gate) and residual mean velocity < 5 mm/yr over OPERA-CSLC-derived stable pixels
- [x] **CSLC-04**: Mojave Desert self-consistency eval (Coso/Searles Valley primary, or a documented-stable AOI from the 3-candidate fallback list — Pahranagat Valley / Amargosa Valley / Hualapai Plateau) passes the same self-consistency gate, OR exhaustion of the fallback list surfaces a Phase blocker
- [x] **CSLC-05**: Iberian Meseta EU eval (primary: bedrock/sparse-vegetation burst north of Madrid; fallbacks: Alentejo / Massif Central) reports (a) OPERA CSLC amplitude reference-agreement r > 0.6, RMSE < 4 dB; (b) self-consistency coherence > 0.7 over stable terrain; (c) EGMS L2a stable-PS residual mean velocity < 5 mm/yr
- [x] **CSLC-06**: Cross-version phase comparison methodology is consolidated in `docs/validation_methodology.md` with the diagnostic evidence (removal of carrier, flattening, both — still yields zero coherence across isce3 major versions)

### DISP-S1 Comparison Adapter + Honest FAIL

- [x] **DISP-01**: `subsideo.validation.compare_disp.prepare_for_reference(native_velocity, reference_grid, method=...)` is validation-only infrastructure that multilooks subsideo's native 5×10 m velocity to a reference grid (30 m raster for OPERA DISP OR point coordinates for EGMS L2a PS); `method=` has no default and must be explicit; the function never writes back to the product
- [x] **DISP-02
**: DISP self-consistency product-quality gate (sequential 12-day coherence > 0.7 and residual mean velocity < 5 mm/yr on stable terrain at native 5×10 m resolution) is computed for both N.Am. (SoCal) and EU (Bologna) from cached CSLC stacks
- [x] **DISP-03
**: N.Am. and EU DISP re-runs from cached CSLCs report reference-agreement (r vs OPERA DISP-S1 at 30 m; r vs EGMS L2a at PS points) separately from product-quality results; any observed planar ramp is labelled by attributed source (PHASS / tropospheric / orbit / ionospheric) via a ramp-attribution diagnostic (POEORB swap, ERA5 toggle, ramp-direction stability test)
- [ ] **DISP-04**: A one-page "DISP Unwrapper Selection" follow-up milestone scoping brief is delivered as a Phase artifact, grounded in the fresh FAIL numbers and listing candidate approaches (PHASS+deramping, SPURT native, tophu-SNAPHU tiled, 20×20 m fallback) with a success criterion per approach
- [x] **DISP-05**: Native 5×10 m resolution remains the production default for DISP-S1; downsampling to the reference grid lives exclusively in `prepare_for_reference` and is documented as validation-only in both code and methodology doc

### DIST-S1 OPERA v0.1 Sample Comparison + EU Tightening

- [ ] **DIST-01**: The OPERA DIST v0.1 sample for MGRS tile T11SLT is fetched via CloudFront direct-download with exponential-backoff retry (via harness) and cached under `eval-dist/opera_reference/v0.1_T11SLT/` (the sample is preserved on disk regardless of downstream comparison outcome)
- [ ] **DIST-02**: Before running the T11SLT quantitative comparison, a config-drift gate extracts the OPERA v0.1 sample's 7 key processing parameters (confirmation-count threshold, pre-image strategy, post-date buffer, baseline window length, despeckle settings + 2 further) and compares against dist-s1 2.0.14 defaults; material deltas cause skip-and-defer (matrix cell reads "deferred pending operational reference publication")
- [ ] **DIST-03**: When the config-drift gate passes, T11SLT comparison computes F1 / precision / recall / accuracy with block-bootstrap confidence interval (1 km blocks, B=500); matrix cell reports point estimate AND CI; criteria remain F1 > 0.80 and accuracy > 0.85 without tightening toward v0.1's own score
- [ ] **DIST-04**: `make eval-dist-nam` includes a CMR probe for operational `OPERA_L3_DIST-ALERT-S1_V1` publication; on discovery, the operational reference supersedes the v0.1 result in the matrix without manual intervention
- [ ] **DIST-05**: EFFIS same-resolution-optical cross-validation runs against cached Aveiro/Viseu 2024 subsideo output via `owslib` WFS and reports precision > 0.70 AND recall > 0.50 against EFFIS burnt-area perimeters
- [ ] **DIST-06**: EU DIST coverage expands from 1 event to 3 (2024 Portuguese wildfires + 2023 Evros Greece EMSR649 + 2022 Romanian forest clear-cuts) with aggregate results in `CONCLUSIONS_DIST_EU.md`
- [ ] **DIST-07**: After Phase 1 `_mp.py` bundle lands, the chained `prior_dist_s1_product` run is retried on the DIST EU stack (Sep 28 → Oct 10 → Nov 15); success is reported as a DIFFERENTIATOR, failure is filed upstream with dist-s1 maintainers (non-blocking)

### DSWx-S2 N.Am. Validation + EU Recalibration

- [ ] **DSWX-01**: N.Am. DSWx-S2 positive control eval runs on a selected AOI (Lake Tahoe or Lake Pontchartrain) and reports F1 against JRC Monthly History; F1 < 0.85 triggers regression investigation (BOA offset / Claverie cross-calibration) before recalibration proceeds
- [ ] **DSWX-02**: EU fit-set AOI selection is documented in `notebooks/dswx_aoi_selection.ipynb` with per-AOI rationale spanning JRC reference quality + S2 cloud-free scene availability + water-body type diversity + absence of known algorithm failure modes (glacier/frozen lake, heavy turbid water, dominant mountain shadow)
- [ ] **DSWX-03**: EU fit set contains 12 (AOI, wet-scene, dry-scene) triples across 6 biome-diverse AOIs (Mediterranean reservoir, Atlantic estuary, boreal lake, Pannonian plain, Alpine valley, Iberian summer-dry); Balaton is held out as independent test set
- [ ] **DSWX-04**: `scripts/recalibrate_dswe_thresholds.py` performs a joint grid search over `WIGT` ([0.08, 0.20] step 0.005), `AWGT` ([−0.1, +0.1] step 0.01), and `PSWT2_MNDWI` ([−0.65, −0.35] step 0.02), optimising mean F1 across the fit set
- [ ] **DSWX-05**: Recalibrated thresholds live in `src/subsideo/products/dswx_thresholds.py` as a typed constants module with provenance metadata and EU/N.Am. region selector via `pydantic-settings`; `notebooks/dswx_recalibration.ipynb` reproduces the grid search deterministically from the cached fit set
- [ ] **DSWX-06**: EU DSWx re-run with recalibrated thresholds reports F1 against JRC without adjusting the F1 > 0.90 bar; fit-set F1 is reported alongside LOO-CV F1 (gap < 0.02 required to rule out overfit); 0.85 ≤ F1 < 0.90 is labelled "FAIL with named ML-replacement upgrade path"; F1 < 0.85 triggers fit-set quality review
- [ ] **DSWX-07**: The "DSWE F1 ceiling ≈ 0.92" claim in any FAIL reporting is either ground-referenced to the PROTEUS ATBD (with citation) or documented as "empirical bound observed over our 6-AOI evaluation" — no inherited game-of-telephone citation

### Results Matrix & Release Readiness

- [ ] **REL-01**: `make eval-all` writes `results/matrix.md` with all 10 cells (5 products × 2 regions) filled; each cell reports product-quality gate status and reference-agreement numbers in separate columns; CALIBRATING cells are visually distinguishable
- [ ] **REL-02**: `results/matrix_manifest.yml` lists expected cells and their per-eval `metrics.json` sidecar paths; the matrix writer reads only from manifest + sidecars (never glob-parses CONCLUSIONS documents)
- [ ] **REL-03**: `docs/validation_methodology.md` covers the four methodological findings (cross-version phase impossibility across isce3 major versions, cross-sensor comparison precision-first framing, OPERA frame selection by exact UTC hour + spatial footprint, DSWE-family F1 ≈ 0.92 architectural ceiling) AND explicitly documents the product-quality vs reference-agreement distinction
- [ ] **REL-04**: Pre-release audit runs a full `make eval-all` on a freshly-cloned repo inside the homelab TrueNAS Linux dev container; cold-env run completes under 12 h; warm-env re-run completes under 10 min
- [ ] **REL-05**: At milestone close, every matrix cell is labelled PASS, FAIL-with-named-upgrade-path, or deferred-with-dated-unblock-condition — no cell reads "n/a" or is empty
- [ ] **REL-06**: `micromamba env create -f conda-env.yml` on a clean machine completes successfully, and `pytest` passes, as the final closure test

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
| ENV-01 | Phase 1 | Pending |
| ENV-02 | Phase 1 | Pending |
| ENV-03 | Phase 1 | Pending |
| ENV-04 | Phase 1 | Pending |
| ENV-05 | Phase 1 | Pending |
| ENV-06 | Phase 1 | Pending |
| ENV-07 | Phase 1 | Pending |
| ENV-08 | Phase 1 | Pending |
| ENV-09 | Phase 1 | Pending |
| ENV-10 | Phase 1 | Pending |
| GATE-01 | Phase 1 | Pending |
| GATE-02 | Phase 1 | Pending |
| GATE-03 | Phase 1 | Pending |
| GATE-04 | Phase 1 | Pending |
| GATE-05 | Phase 1 | Pending |
| RTC-01 | Phase 2 | Complete (2026-04-23) |
| RTC-02 | Phase 2 | Complete (2026-04-23) |
| RTC-03 | Phase 2 | Complete (2026-04-23) |
| CSLC-01 | Phase 1 | Pending |
| CSLC-02 | Phase 1 | Pending |
| CSLC-03 | Phase 3 | Validated (CALIBRATING — SoCal coh_med_of_persistent=0.887 / residual=−0.109 mm/yr; amp_r=0.982 / amp_rmse=1.290 dB) |
| CSLC-04 | Phase 3 | Validated (CALIBRATING — Mojave/Coso-Searles fallback #1 coh_med_of_persistent=0.804 / residual=+1.127 mm/yr; chain short-circuited on first valid fallback per design) |
| CSLC-05 | Phase 3 | Validated-with-deferral (CALIBRATING — Iberian coh_med_of_persistent=0.868 / residual=+0.347 mm/yr; EGMS L2a third-number deferred per Bug 8 follow-up) |
| CSLC-06 | Phase 3 | Validated (Plan 03-05) |
| DISP-01 | Phase 4 | Validated (Plan 04-02 prepare_for_reference adapter; Plan 04-04 callsites in run_eval_disp.py form (b) xr.DataArray + run_eval_disp_egms.py form (c) ReferenceGridSpec; v1.0 Resampling.bilinear callsites removed; explicit method= no default per DISP-01) |
| DISP-02 | Phase 4 | Validated (Plan 04-04 — coherence + residual computed for both cells: SoCal coh_med_of_persistent=0.887 [phase3-cached] / residual=-0.030 mm/yr; Bologna coh_med_of_persistent=0.000 [fresh] / residual=+0.117 mm/yr — both CALIBRATING) |
| DISP-03 | Phase 4 | Validated (Plan 04-04 — RA reported separately from PQ for both cells; per-IFG planar ramp + auto_attribute_ramp diagnostic populated; both cells attributed_source='inconclusive' under deterministic rule with diagnostics b+c deferred per D-09) |
| DISP-04 | Phase 4 | Pending (Plan 04-05 Wave 4) |
| DISP-05 | Phase 4 | Validated (Plan 04-02 + Plan 04-04 — `prepare_for_reference` is validation-only with SHA256 byte-equal pre/post test; products/disp.py:481 `velocity_path` remains native 5x10 m; eval scripts call adapter for comparison only) |
| DIST-01 | Phase 5 | Pending |
| DIST-02 | Phase 5 | Pending |
| DIST-03 | Phase 5 | Pending |
| DIST-04 | Phase 5 | Pending |
| DIST-05 | Phase 5 | Pending |
| DIST-06 | Phase 5 | Pending |
| DIST-07 | Phase 5 | Pending |
| DSWX-01 | Phase 6 | Pending |
| DSWX-02 | Phase 6 | Pending |
| DSWX-03 | Phase 6 | Pending |
| DSWX-04 | Phase 6 | Pending |
| DSWX-05 | Phase 6 | Pending |
| DSWX-06 | Phase 6 | Pending |
| DSWX-07 | Phase 6 | Pending |
| REL-01 | Phase 7 | Pending |
| REL-02 | Phase 7 | Pending |
| REL-03 | Phase 7 | Pending |
| REL-04 | Phase 7 | Pending |
| REL-05 | Phase 7 | Pending |
| REL-06 | Phase 7 | Pending |

**Coverage:**
- v1.1 requirements: 49 total (10 ENV + 5 GATE + 3 RTC + 6 CSLC + 5 DISP + 7 DIST + 7 DSWX + 6 REL)
- Mapped to phases: 49
- Unmapped: 0

**Per-phase counts:**
- Phase 1 (Environment Hygiene, Framework Consolidation & Guardrail Scaffolding): 17 (ENV-01..10, GATE-01..05, CSLC-01..02)
- Phase 2 (RTC-S1 EU Validation): 3 (RTC-01..03)
- Phase 3 (CSLC-S1 Self-Consistency + EU Validation): 4 (CSLC-03..06)
- Phase 4 (DISP-S1 Comparison Adapter + Honest FAIL): 5 (DISP-01..05)
- Phase 5 (DIST-S1 OPERA v0.1 + EFFIS EU): 7 (DIST-01..07)
- Phase 6 (DSWx-S2 N.Am. + EU Recalibration): 7 (DSWX-01..07)
- Phase 7 (Results Matrix + Release Readiness): 6 (REL-01..06)

---
*Requirements defined: 2026-04-20*
*Last updated: 2026-04-20 after roadmap creation — CSLC-01 and CSLC-02 moved to Phase 1 (shared stable_terrain.py + selfconsistency.py per research SUMMARY §0.5.5); 49/49 mapped, 0 orphans*
