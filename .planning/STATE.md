---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: N.Am./EU Validation Parity & Scientific PASS
status: shipped
stopped_at: ~
last_updated: "2026-04-30T00:00:00.000Z"
last_activity: 2026-04-30 -- v1.1 milestone closed; archived to .planning/milestones/; git tag v1.1; REQUIREMENTS.md removed (fresh for v1.2)
progress:
  total_phases: 7
  completed_phases: 7
  total_plans: 43
  completed_plans: 43
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-20)

**Core value:** Produce scientifically accurate, OPERA-spec-compliant SAR/InSAR geospatial products over EU AOIs — validated against official reference products to prove correctness.
**Current focus:** v1.2 planning — run /gsd-new-milestone to start next milestone

## Current Position

Phase: 06 (dswx-s2-n-am-eu-recalibration) — COMPLETE
Plan: 7 of 7 (Plan 06-07 complete; Phase 6 closed)
Status: Phase 06 complete — DSWx row fully populated in 5/5 product validation matrix
Last activity: 2026-04-28 -- Phase 06 Plan 07 complete (EU DSWx re-run Balaton F1=0.8165 FAIL; CONCLUSIONS_DSWX.md v1.1 appended; validation_methodology.md §5 appended; matrix.md regen)

**Phase 6 close:** All 7 plans complete. dswx:eu F1=0.8165 FAIL (fit-set quality review); dswx:nam F1=0.9252 PASS (Lake Tahoe). EU recalibration deferred to v1.2 with diagnosed root cause (HLS→S2 L2A spectral transfer gap). Phase 7 (REL-* release deliverables) is the next phase.

**Previous resume path (06-04):** All 5 plans complete (Waves 1 + 2 + 3 + 4). Plan 04-05 (Wave 4: docs + brief) renamed `CONCLUSIONS_DISP_EGMS.md` → `CONCLUSIONS_DISP_EU.md` via `git mv` (R100; history preserved via `git log --follow`); appended 4 v1.1 sub-sections (§11 Product Quality / §12 Reference Agreement / §13 Ramp Attribution / §14 Brief link) to both `CONCLUSIONS_DISP_N_AM.md` (258 → 356 LOC) and `CONCLUSIONS_DISP_EU.md` (304 → 404 LOC) with v1.0 baseline numbers preserved as continuity preamble; wrote `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md` (129 LOC) with 4-candidate × 4-column scoping table (PHASS+post-deramping S/SPURT native M/tophu+SNAPHU L/20×20 m fallback L) and attribution-driven prioritisation recommending ERA5 toggle (DISP-V2-02) FIRST in v1.2; appended §3 multilook ADR to `docs/validation_methodology.md` (247 → 365 LOC) with 5-part PITFALLS+FEATURES dialogue and explicit "Native 5×10 m stays production default" per DISP-05; §4 + §5 NOT created per Phase 3 D-15 append-only. **Phase 4 closure complete.** Honest FAIL signal preserved + scoped: SoCal r=0.049 / Bologna r=0.336 (both FAIL > 0.92), both attributed_source='inconclusive', cross-cell pattern flags atmospheric long-wavelength curvature as primary v1.2 candidate. Ready for verifier per `.planning/config.json` `workflow.verifier: true`.

## Performance Metrics

**Velocity:**

- Total plans completed: 32 (v1.1); 21 (v1.0, shipped)
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 9 | - | - |
| 04 | 5 | - | - |
| 05 | 9 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

**v1.0 historical (reference):**

| Phase 01 P01 | 8min | 3 tasks | 12 files |
| Phase 01 P04 | 5min | 2 tasks | 8 files |
| Phase 01 P03 | 5min | 2 tasks | 5 files |
| Phase 01 P02 | 7min | 1 tasks | 2 files |
| Phase 02 P01 | 3min | 2 tasks | 6 files |
| Phase 02 P03 | 3min | 2 tasks | 4 files |
| Phase 02 P02 | 4min | 2 tasks | 4 files |
| Phase 02 P04 | 2min | 2 tasks | 4 files |
| Phase 03 P01 | 6min | 2 tasks | 3 files |
| Phase 03 P03 | 2min | 2 tasks | 2 files |
| Phase 03 P02 | 4min | 2 tasks | 3 files |
| Phase 04 P01 | 5min | 2 tasks | 7 files |
| Phase 04 P02 | 4min | 2 tasks | 5 files |
| Phase 04 P03 | 3min | 1 tasks | 4 files |
| Phase 05 P01 | 4min | 2 tasks | 4 files |
| Phase 05 P02 | 3min | 2 tasks | 7 files |
| Phase 06 P01 | 4min | 2 tasks | 7 files |
| Phase 06 P02 | 5min | 2 tasks | 2 files |
| Phase 06 P03 | 40min | 2 tasks | 5 files |
| Phase 07 P01 | 4min | 2 tasks | 4 files |
| Phase 08 P01 | 2min | 3 tasks | 6 files |
| Phase 09 P01 | 3min | 3 tasks | 7 files |
| Phase 04 P01 | 10min | 3 tasks | 6 files |
| Phase 04 P02 | 9min | 2 tasks | 2 files |
| Phase 04 P05 | 9min | 4 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work (v1.1):

- [v1.1 Roadmap]: Phase numbering reset to start at 1 (v1.0 phases archived to `.planning/milestones/v1.0-phases/`)
- [v1.1 Roadmap]: BOOTSTRAP Phase 0 expanded to GSD Phase 1 with 17 requirements (+ CSLC-01/CSLC-02 moved from CSLC phase so shared stable_terrain.py + selfconsistency.py modules land before Phases 3 and 4 consume them — per research SUMMARY §0.5.5)
- [v1.1 Roadmap]: 4 BOOTSTRAP corrections baked into Phase 1 criteria — tophu via conda-forge (not pip), rio-cogeo==6.0.0 (not 7.x, Python 3.10 drop), full `_mp.py` bundle (MPLBACKEND + RLIMIT_NOFILE + session close + forkserver fallback, not just set_start_method), `bounds_for_burst` as harness function (not separate module)
- [v1.1 Roadmap]: Phase 1 internal ordering: 0.1 → 0.3 → 0.4 → 0.5+0.5.5 → 0.6abc → 0.2 → 0.7+0.8+0.9 per research ARCHITECTURE Build Order
- [v1.1 Roadmap]: Research flags surfaced as planning artifacts (not roadmap-level commitments): Phase 3 coherence metric choice (mean/median/persistently-coherent); Phase 4 multilook method default (Gaussian vs block-mean — PITFALLS/FEATURES in tension, requires Phase 4 ADR)
- [v1.1 Roadmap]: Phase 5 soft runtime dependency — CMR probe auto-supersede handles OPERA operational DIST-S1 publication without re-planning
- [v1.1 Roadmap]: Phase 6 internal ordering — AOI research (DSWX-02) precedes fit-set compute commit
- [v1.1 Roadmap]: No `prepare_for_reference` default `method=` argument (DISP-01) — validation discipline, per PITFALLS P3.1 tension with FEATURES anti-feature
- [v1.1 Roadmap]: `results/matrix.md` uses manifest + per-eval `metrics.json` sidecars (never glob-parse CONCLUSIONS markdown) — per PITFALLS R3/R5
- [Phase 1 CONTEXT]: `criteria.py` is frozen-dataclass `Criterion` + flat `CRITERIA: dict[str, Criterion]` registry + typed accessor functions; immutability via `frozen=True` + matrix-writer echo + PR-ADR review (no CI hash-check)
- [Phase 1 CONTEXT]: Split `ProductQualityResult` / `ReferenceAgreementResult` is a **nested composite** in new `validation/results.py`; no stored pass-bools (criterion IDs + measurements; pass/fail computed at read time); **big-bang migration in Phase 1** (single commit replaces all 5 compare_*.py returns + tests)
- [Phase 1 CONTEXT]: Watchdog is **per-script subprocess wrap** via `python -m subsideo.validation.supervisor` invoked from Makefile; mtime staleness heuristic; caller-supplied `EXPECTED_WALL_S` per script; `os.killpg` + py-spy stack dump to `watchdog-stacks.txt` before SIGTERM→SIGKILL; exit 124
- [Phase 1 CONTEXT]: **Two-layer `conda-env.yml`** (conda-forge heavies + trailing `pip: -e .[validation,viz]`); **per-platform explicit lockfiles** `env.lockfile.linux-64.txt` + `env.lockfile.osx-arm64.txt`; **Dockerfile primary** from `mambaorg/micromamba` + Apptainer.def derived; **both platforms validated in Phase 1** via M3 Max dev run + `docker build + docker run pytest` on arm64 Docker; Phase 7 TrueNAS cold-env audit remains separate
- [Phase 1 CONTEXT]: Phase 1 populates `criteria.py` with v1.0 BINDING + Phase-3-needed CALIBRATING gates (CSLC/DISP self-consistency coherence>0.7, residual<5 mm/yr, `binding_after_milestone='v1.2'`); Phase 5 EFFIS and DSWx recalibration threshold additions **deferred to Phase 5**
- [Phase 2 CONTEXT]: Standalone `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` probe artifact committed BEFORE eval runs; plan-phase locks 5-burst list from it. Cached-SAFE reuse via harness search-path fallback (eval-rtc-eu → eval-disp-egms → eval-dist-eu; no symlinks/copies). Claude drafts specific burst IDs in plan-phase; user reviews.
- [Phase 2 CONTEXT]: `run_eval_rtc_eu.py` is a single script with declarative `BURSTS: list[BurstConfig]` looping sequentially, per-burst try/except isolation (one failure doesn't block matrix cell), per-burst whole-pipeline skip + per-stage `ensure_resume_safe`. Supervisor wraps as outer boundary; `_mp.configure_multiprocessing()` fires once per cell.
- [Phase 2 CONTEXT]: Single aggregate `eval-rtc-eu/metrics.json` with nested `per_burst: [...]` list (new `RTCEUCellMetrics` Pydantic extension of base `CellMetrics`); top-level aggregates include pass_count/total, reference_agreement.worst_rmse_db/worst_r/worst_burst_id, any_investigation_required. Single cell-level `meta.json` with nested per-burst input hashes. Matrix row renders as single `X/N PASS` + link to CONCLUSIONS_RTC_EU.md.
- [Phase 2 CONTEXT]: RTC-03 investigation trigger is RMSE >= 0.15 dB (~3× N.Am. baseline) OR r < 0.999; dual trigger (RMSE catches bias, r catches structure). Triggers live in `criteria.py` as new `type='INVESTIGATION_TRIGGER'` entries (extending Phase 1 D-01 Literal) — non-gate, do NOT tighten pass criteria (RTC-02 explicit). Eval script auto-flags `per_burst[i].investigation_required` + reason; human writes structured observation + hypothesis + evidence sub-section in CONCLUSIONS_RTC_EU.md per flagged burst.
- [Phase 3 Plan 03-05]: `docs/validation_methodology.md` lands as a new artifact under a new `docs/` directory with §1 (CSLC cross-version phase impossibility) + §2 (product-quality vs reference-agreement distinction) ONLY; per CONTEXT D-15 append-only, §3 DISP ramp-attribution / §4 DSWE F1 ceiling / §5 cross-sensor precision-first / top-level ToC are deferred to Phase 4 / 5-6 / 7 REL-03. §1 leads with the structural isce3 SLC-interpolation-kernel argument (PITFALLS P2.4 mitigation) BEFORE the diagnostic-evidence appendix (carrier/flattening table). compare_cslc.py docstring cross-links the doc anchor at module level. Filename correction noted: plan said CONCLUSIONS_CSLC_EU.md; on-disk file is CONCLUSIONS_CSLC_SELFCONSIST_EU.md (committed under SELFCONSIST_ prefix in f6d5492).

**v1.0 decisions (reference):** see PROJECT.md Key Decisions table + historical log below for ordering context.

- [Init]: CDSE over ASF for EU data — CDSE is the native Copernicus hub; STAC endpoint is `stac.dataspace.copernicus.eu/v1` (changed Nov 2025)
- [Init]: EU burst DB must be built from ESA CC-BY 4.0 GeoJSON — opera-burstdb covers North America only
- [Init]: Two-layer install enforced — conda-forge for ISCE3/GDAL/dolphin/snaphu; pip for pure-Python layer
- [CSLC Eval]: 4 monkey-patches for numpy 2.x compat with compass/s1reader/isce3 pybind11 — scheduled for removal in v1.1 Phase 1 (ENV-02)
- [CSLC Eval]: Cross-version phase comparison (isce3 0.15 vs 0.25) produces zero coherence; amplitude metrics used instead — consolidated into docs/validation_methodology.md in v1.1 Phase 3 (CSLC-06)
- [CSLC Eval]: CSLC amplitude correlation 0.79, RMSE 3.77 dB — PASS with amplitude-based criteria
- [Phase 4 Plan 04-01]: compute_ramp_aggregate returns plain dict (not RampAggregate Pydantic) to avoid circular import between selfconsistency.py and matrix_schema.py; caller (Plan 04-04) converts at metrics.json write time
- [Phase 4 Plan 04-01]: B1 root-cause fix complete -- _compute_ifg_coherence_stack lifted from inner-scope of run_eval_cslc_selfconsist_nam.py:487 to public selfconsistency.compute_ifg_coherence_stack; nested _load_cslc closure promoted to sibling module-private _load_cslc_hdf5; Plan 04-04 imports the public symbol
- [Phase 4 Plan 04-01]: 5 Pydantic v2 DISP cell-metrics types appended to matrix_schema.py (PerIFGRamp, RampAggregate, RampAttribution, DISPProductQualityResultJson, DISPCellMetrics) + 3 Literal type aliases; all use ConfigDict(extra=forbid); no edits to existing types per Phase 1 D-09 lock-in
- [Phase 4 Plan 04-02]: Option A minimal refactor for prepare_for_reference — existing v1.0 compare_disp + compare_disp_egms_l2a top-level functions UNCHANGED; eval scripts (Plan 04-04) call prepare_for_reference BEFORE these v1.0 functions. Resampling.bilinear callsites at compare_disp.py:163 and 175 preserved for v1.0 continuity. CONTEXT D-Claude's-Discretion green-lit Option A or B; A picked for parallelizability and locked-in v1.0 test coverage preservation.
- [Phase 4 Plan 04-02]: xarray + rioxarray promoted to module-top imports of compare_disp.py (not lazy) because they appear in type annotations + isinstance checks at runtime. rioxarray imported with `# noqa: F401` because it binds via .rio accessor side-effect. scipy.ndimage + pyproj.Transformer + rasterio.io.MemoryFile remain lazy (per-method-branch only).
- [Phase 4 Plan 04-02]: prepare_for_reference form (b) -> form (c) bridge via rasterio.io.MemoryFile rather than temp-disk write — xr.DataArray native gets wrapped in an in-memory GeoTIFF so _point_sample_from_dataset stays uniform. Zero disk I/O, zero attack surface (MemoryFile cannot be coerced to read attacker-controlled paths per threat T-04-02-05).
- [Phase 4 Plan 04-03]: matrix_writer DISP dispatch inserted BEFORE CSLC self-consist (per_aoi) and RTC-EU (per_burst) branches at lines 476-489 (CSLC at line 491, RTC-EU at line 506). DISP discriminator (top-level ramp_attribution key) is structurally disjoint from per_aoi and per_burst — order is invariant per RESEARCH lines 593-608. _render_disp_cell single branch handles both region='nam' and region='eu' because DISPCellMetrics schema is symmetric across SoCal and Bologna. PQ column italicised whole-body with attributed_source label inline ('attr=phass'); RA column reuses _render_measurement helper for each criterion ID — no per-DISP RA renderer.
- [Phase 4 Plan 04-03]: Single `_render_disp_cell` branch routes BOTH region='nam' and region='eu' through same DISPCellMetrics schema (locked-in via Plan 04-01 D-Claude's-Discretion). Region parameter passed through for symmetry with `_render_cslc_selfconsist_cell` (which forks between NAM/EU subclasses) but currently unused in the body — kept for forward-compat in case Phase 4 D-08-style regional divergence ever needs to fork the render later. Test 6 in test_matrix_writer_disp.py pins this invariant.
- [Phase 4 Plan 04-04]: Inline `_slope_from_dem` closure (mirroring Phase 3 NAM eval `_compute_slope_deg` at run_eval_cslc_selfconsist_nam.py:488) and module-level `_reproject_mask_to_grid` helper (one per script) — public symbol promotion to `stable_terrain.py` deferred to v1.2 unless a 3rd consumer needs it (current 2 consumers: NAM + EU DISP scripts).
- [Phase 4 Plan 04-04]: Bologna 12-day IFG count = 9 (not 18 as plan predicted). Cross-constellation S1A+S1B 2021 stack has effective 6-day cadence; only 9 sequential pairs fall on the 11-13 day window per `_is_sequential_12day(...) <= 1 day` tolerance. Methodologically consistent with D-07's "sequential 12-day pairs for cross-cell consistency" framing — 6-day pairs would couple the EU coherence statistic to a different baseline than the SoCal cell.
- [Phase 4 Plan 04-04]: Bologna persistently_coherent_fraction = 0.000 is a real signal — mean coh 0.219, p75 0.316, both below 0.6 threshold; no pixel exceeded coherence in EVERY one of the 9 IFGs. Po plain has lower stable-terrain coherence than SoCal Mediterranean. NOT a bug.
- [Phase 4 Plan 04-04]: Both cells produce attributed_source='inconclusive' from the deterministic auto-attribute rule (sigma_dir < 30 deg AND r(mag,coh) > 0.5 cutoffs not met on either cell). This mixed-signal informs Plan 04-05 brief: diagnostics (b) POEORB swap and (c) ERA5 toggle are needed before tightening attribution — exactly the deferred-diagnostic disposition per D-09.
- [Phase 4 Plan 04-04]: Rule 1 bug fix: warm-path velocity_path probe pointed at non-existent `disp/mintpy/velocity.h5` — replaced with `disp/dolphin/timeseries/velocity.tif` (matches DISPResult.velocity_path emitted by products/disp.py:481). Without this fix, every warm invocation forced a full pipeline rerun.
- [Phase 4 Plan 04-04]: Rule 3 fix: EGMS_TOKEN credential preflight made conditional on egms_reference/ CSV cache emptiness. Token is consumed only by Stage 2 download path; on warm re-runs from cached CSVs the token is never read. Old preflight blocked the script unnecessarily before reaching Stage 9.
- [Phase 4 Plan 04-04]: W4 supervisor cache_dir divergence acknowledged but not silently bypassed. supervisor._cache_dir_from_script() derives `eval-disp_egms` (underscore) for run_eval_disp_egms.py while on-disk + manifest both use `eval-disp-egms` (hyphen). Watchdog mtime-staleness check looks at the wrong path (which is empty), but abort is gated by `wall > 2 * expected_wall AND stale > GRACE_WINDOW_S`. Bologna eval completed in ~3 minutes — far below the 2*21600s threshold — so the watchdog did not abort. Pre-existing divergence Phase 4 inherits but does not introduce. Phase 4 follow-up todo: reconcile supervisor cache_dir derivation with on-disk hyphen convention.
- [Phase 4 Plan 04-05]: git mv CONCLUSIONS_DISP_EGMS.md to CONCLUSIONS_DISP_EU.md (R100 rename); 4 v1.1 sub-sections appended to both DISP CONCLUSIONS files (Product Quality / Reference Agreement / Ramp Attribution / Brief link); DISP_UNWRAPPER_SELECTION_BRIEF.md written with 4 candidates x 4 columns at .planning/milestones/v1.1-research/; docs/validation_methodology.md section 3 multilook ADR appended (5-part PITFALLS+FEATURES dialogue); v1.0 baseline numbers preserved as continuity preamble; no section 4/section 5 added per Phase 3 D-15 append-only
- [Phase 4 Plan 04-05]: Section 3 multilook ADR framed as posture-not-science; PITFALLS P3.1 Gaussian-physics + FEATURES anti-feature block_mean both correct on own terms; ADR resolves by picking lower-bound r kernel (block_mean) for milestone-publish artefacts; eval-script constant REFERENCE_MULTILOOK_METHOD lives at module top in run_eval_disp.py + run_eval_disp_egms.py per D-04; switching kernel post-measurement requires PR diff + CONCLUSIONS sub-section per section 3.5; no env-var override / CLI flag
- [Phase 4 Plan 04-05]: Brief author recommends activating diagnostic (c) ERA5 toggle FIRST in v1.2 milestone (DISP-V2-02 integration) given Phase 4's both-cells-inconclusive outcome triggers CONTEXT D-14 'diagnostics b+c BEFORE candidate evaluation' branch; cross-cell pattern (SoCal r(mag,coh)=+0.15 near-zero; Bologna r(mag,coh)=-0.52 negative) suggests atmospheric long-wavelength curvature; if ERA5 flips both cells to phass then ordered escalation is candidate 2 (SPURT) -> 1 (PHASS+post-deramping) -> 3 (tophu+SNAPHU) -> 4 (20x20 m fallback)
- [Phase 6 Plan 06-04]: B2 fix: DSWxValidationDiagnostics attribute side-channel (default None) on DSWxValidationResult is the canonical pattern for zero-breaking-change extensibility; tuple-return would have broken all v1.0 callers
- [Phase 6 Plan 06-04]: Shoreline buffer applied at UTM-grid level using JRC raw encoding (2=water) before _binarize_jrc transform; ensures buffer is in the same coordinate space as the comparison (D-16)
- [Phase 6 Plan 06-04]: download_reference_with_retry parameter is dest= (keyword-only), not dest_path=; source= is also keyword-only per harness.py actual signature
- [Phase 6 Plan 06-04]: matrix_writer dispatch insertion AFTER dist:nam_deferred, BEFORE cslc:selfconsist + rtc:eu (D-27 + W6 strict chain); discriminators keyed on structurally-disjoint field-sets (selected_aoi+candidates_attempted for nam; thresholds_used+loocv_gap for eu)
- [Phase 6 Plan 06-05]: N.Am. DSWx-S2 positive control F1=0.9252 (shoreline-excluded) > 0.90 BINDING PASS at Lake Tahoe T10SFH July 2021; THRESHOLDS_NAM PROTEUS defaults operate at calibration baseline; f1_below_regression_threshold=False; EU recalibration Plan 06-06 cleared
- [Phase 6 Plan 06-06]: EU recalibration deferred to v1.2 — 3-iteration grid search exhausted (Iter-1: 3-axis PSWT2_MNDWI edge trigger; Iter-2: 525-pt WIGT[0.08,0.20]xAWGT[-0.10,0.10] BLOCKER at WIGT edge, F1=0.2092; Iter-3: 1395-pt WIGT[0.08,0.30]xAWGT[-0.20,0.10] BLOCKER again at WIGT=0.30 edge, F1=0.2092). Root cause: HLS LaSRC vs sen2cor BOA aerosol retrieval produces different MNDWI distribution; Claverie static offset insufficient for scene-level correction. THRESHOLDS_EU unchanged (PROTEUS defaults); fit_set_hash=''. CONCLUSIONS_DSWX_EU_RECALIB.md written. Stage 0 assert relaxed to warning. Plan 06-07 unblocked with PROTEUS defaults.
- [Phase 6 Plan 06-05]: MGRS seed tiles 10SFH (Lake Tahoe) + 15RYP (Lake Pontchartrain) added to _mgrs_tiles.geojson with pyproj-computed WGS84 bounds from UTM zone 10N/15N
- [Phase 6 Plan 06-05]: gdal_JP2OpenJPEG.dylib missing from subsideo conda env; fixed by copying from conda pkg cache (micromamba 2.5.0 pip-inspect subprocess bug prevents normal install)
- [Phase 6 Plan 06-05]: W2 fix confirmed: f1_full_pixels=0.8613 + shoreline_buffer_excluded_pixels=243221 live in metrics.json directly (no diagnostics.json sidecar)
- [Phase 6 Plan 06-07]: EU re-run Balaton F1=0.8165 (shoreline-excluded) FAIL; named_upgrade_path='fit-set quality review' (F1<0.85); PROTEUS defaults applied (recalibration deferred to v1.2)
- [Phase 6 Plan 06-07]: ATBD probe Path (c) succeeded: OPERA Cal/Val F1_OSW=0.8786 mean (N=52 scenes); '0.92 ceiling' was OSW class accuracy misattributed as F1; gate at 0.90 is above Cal/Val baseline
- [Phase 6 Plan 06-07]: DswxEUCellMetrics constructor requires ProductQualityResultJson/ReferenceAgreementResultJson (Pydantic BaseModel from matrix_schema), NOT the dataclasses from results.py
- [Phase 6 Plan 06-07]: .gitignore: replace blanket eval-dswx/* with specific subdirectory excludes to allow metrics.json + meta.json tracking (per eval-dswx_nam pattern)
- [Phase 6 Plan 06-07]: Phase 6 closed — DSWx row complete in 5/5 product validation matrix; Phase 7 (REL-*) is next

### Pending Todos

None yet (roadmap just created; awaiting `/gsd:plan-phase 1`).

### Blockers/Concerns

- **Phase 1 P0.1 macOS fork pitfalls**: research identified 4 failure modes beyond BOOTSTRAP's simple `set_start_method('fork')`; full `_mp.py` bundle mandated by success criteria — acceptance = 3 consecutive fresh `make eval-all` runs
- **Phase 1 tophu channel**: tophu is not on PyPI (BOOTSTRAP had pip:; must be conda-forge dependencies:); regression test is `import tophu`, not `from dolphin.unwrap import run` (succeeds without tophu)
- **Phase 3 coherence metric choice**: MEDIUM uncertainty; `/gsd:research-phase 3` may be required before SoCal calibration
- **Phase 4 multilook method ADR**: PITFALLS P3.1 and FEATURES anti-feature table in direct tension; plan-phase must surface and resolve
- **Phase 5 operational OPERA DIST publication**: soft runtime dependency on CMR — handled by automatic probe-and-supersede, but if publication lands mid-milestone the 4:N.Am. matrix cell shifts from "vs v0.1" to "vs operational"
- **Phase 6 fit-set quality**: P5.2 JRC labelling noise + drought-year wet/dry ratio (P5.4) can silently cap F1 below bar; AOI research artifact (DSWX-02) is first-class sub-task, not planning

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260408-pfx | Fix stale ROADMAP.md Phase 9 progress row and checkbox | 2026-04-09 | 40790d5 | [260408-pfx-fix-stale-roadmap-md-phase-9-progress-ro](./quick/260408-pfx-fix-stale-roadmap-md-phase-9-progress-ro/) |
| 260408-q2i | Create comprehensive README.md and CHANGELOG.md | 2026-04-09 | 9c6af76 | [260408-q2i-create-comprehensive-readme-md-and-chang](./quick/260408-q2i-create-comprehensive-readme-md-and-chang/) |

## Session Continuity

Last activity: 2026-04-25 — Phase 4 Plan 04-04 complete (Wave 3: eval-script rewire + warm re-runs + manifest fix). 5 changes per script landed in run_eval_disp.py + run_eval_disp_egms.py (10 total: REFERENCE_MULTILOOK_METHOD constant + EXPECTED_WALL_S=21600 + prepare_for_reference adapter + product-quality block + ramp-attribution + DISPCellMetrics write); manifest cache_dir aligned with on-disk eval-disp-egms (hyphen); both warm re-runs completed (~6 min SoCal, ~3 min Bologna); both metrics.json files validate as DISPCellMetrics; matrix.md regenerated. Honest FAIL signal preserved: SoCal r=0.049 (v1.0=0.0365), bias=+23.6 (v1.0=+23.62); Bologna r=0.336 (v1.0=0.32), bias=+3.46 (v1.0=+3.35). Both attributed_source=inconclusive. Ruff clean on touched files. Commits 75dea9d (Task 1 SoCal eval) + ec2c07d (Task 2 Bologna eval) + ae2707f (Task 3 manifest fix) + 709c0c0 (Task 4 Rule 3 EGMS_TOKEN preflight relaxation) + 0d0df63 (Task 4 matrix.md regen). Plan 04-04 SUMMARY at `.planning/phases/04-disp-s1-comparison-adapter-honest-fail/04-04-SUMMARY.md`.
Last session: 2026-04-30T00:03:26.390Z
Stopped at: context exhaustion at 77% (2026-04-30)
Resume file: None

**Planned Phase:** 05 (dist-s1-opera-v0-1-effis-eu) — 9 plans — 2026-04-25T21:45:44.176Z
