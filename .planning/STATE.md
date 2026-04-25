---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: N.Am./EU Validation Parity & Scientific PASS
status: executing
stopped_at: "Completed 04-02-PLAN.md (prepare_for_reference adapter + ReferenceGridSpec + 17 tests; Wave 1 of Phase 4 done); ready for Wave 2 (04-03 matrix_writer DISP cell render)"
last_updated: "2026-04-25T07:18:00.000Z"
last_activity: 2026-04-25
progress:
  total_phases: 7
  completed_phases: 3
  total_plans: 24
  completed_plans: 21
  percent: 87
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-20)

**Core value:** Produce scientifically accurate, OPERA-spec-compliant SAR/InSAR geospatial products over EU AOIs — validated against official reference products to prove correctness.
**Current focus:** Phase 04 — disp-s1-comparison-adapter-honest-fail

## Current Position

Phase: 04 (disp-s1-comparison-adapter-honest-fail) — EXECUTING
Plan: 3 of 5
Status: Ready to execute Wave 2 (Plan 04-03 matrix_writer DISP cell render)
Last activity: 2026-04-25

**Resume path:** Plans 04-01 + 04-02 complete (Wave 1). Plan 04-03 (Wave 2: matrix_writer disp:nam + disp:eu render branches) depends on Plan 04-01's `DISPCellMetrics` + `RampAttribution` Pydantic types — already importable from `subsideo.validation.matrix_schema`. Plan 04-02's `prepare_for_reference` is consumed by Plan 04-04 (Wave 3: eval-script rewire). Phase 4 (DISP comparison adapter) will append §3 (DISP ramp-attribution + multilook ADR) to `docs/validation_methodology.md` per Phase 3 CONTEXT D-15 append-only via Plan 04-05 (Wave 4).

## Performance Metrics

**Velocity:**

- Total plans completed: 18 (v1.1); 21 (v1.0, shipped)
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 9 | - | - |

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
| Phase 07 P01 | 4min | 2 tasks | 4 files |
| Phase 08 P01 | 2min | 3 tasks | 6 files |
| Phase 09 P01 | 3min | 3 tasks | 7 files |
| Phase 04 P01 | 10min | 3 tasks | 6 files |
| Phase 04 P02 | 9min | 2 tasks | 2 files |

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

Last activity: 2026-04-25 — Phase 4 Plan 04-02 complete (Wave 1 sibling: prepare_for_reference adapter). 17 unit tests green (3 error-path + 12 method-x-form + 1 DISP-05 no-write-back + 1 block_mean spot-check). Ruff + mypy clean on touched files (compare_disp.py 380 -> 806 LOC; tests/product_quality/test_prepare_for_reference.py new 187 LOC). Commits c58ab99 (Task 1 RED smoke test) + 4bf9922 (Task 1 GREEN feat) + 7f21dbf (Task 2 full test matrix). Plan 04-02 SUMMARY at `.planning/phases/04-disp-s1-comparison-adapter-honest-fail/04-02-SUMMARY.md`.
Last session: 2026-04-25T07:18:00.000Z
Stopped at: Completed 04-02-PLAN.md (prepare_for_reference adapter + ReferenceGridSpec + 17 tests; Wave 1 of Phase 4 done); ready for Wave 2 (04-03 matrix_writer DISP cell render)
Resume file: None
