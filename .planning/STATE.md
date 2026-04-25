---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: N.Am./EU Validation Parity & Scientific PASS
status: executing
stopped_at: "Phase 3 complete (user-approved 2026-04-25). All 5 plans VERIFIED; CSLC-03/04/05 Validated (CALIBRATING); CSLC-06 Validated. Ready for Phase 4 discuss."
last_updated: "2026-04-25T01:58:00.000Z"
last_activity: "2026-04-25 -- Phase 03 complete: VERIFICATION.md status=human_needed re-verified 16/18; user approved; report appended to CSLC CONCLUSIONS docs"
progress:
  total_phases: 7
  completed_phases: 3
  total_plans: 19
  completed_plans: 19
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-20)

**Core value:** Produce scientifically accurate, OPERA-spec-compliant SAR/InSAR geospatial products over EU AOIs — validated against official reference products to prove correctness.
**Current focus:** Phase 04 — disp-s1-comparison-adapter (next; CONTEXT.md not yet created)

## Current Position

Phase: 03 ✅ COMPLETE (user-approved 2026-04-25); next: Phase 04 (DISP comparison adapter + honest FAIL)
Plan: all 5 Phase 3 plans VERIFIED; Phase 4 planning awaits `/gsd-discuss-phase 4`
Status: Phase 3 closed with 4 pending HUMAN-UAT sign-offs (narrative + PNG inspection + deferrals; user confirmed approval) + 2 named EU follow-ups deferred (Alentejo/MassifCentral re-derivation; EGMS L2a adapter)
Last activity: 2026-04-25 -- Phase 3 closed; verification report appended to CONCLUSIONS_CSLC_SELFCONSIST_{NAM,EU}.md (commit b2571d1)

**Resume path:** `/gsd-discuss-phase 4` to gather Phase 4 context, then `/gsd-plan-phase 4` + `/gsd-execute-phase 4`. Phase 4 (DISP comparison adapter) will append §3 (DISP ramp-attribution) to `docs/validation_methodology.md` per Phase 3 CONTEXT D-15 append-only.

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

Last activity: 2026-04-25 — Phase 3 Plan 03-05 complete (CSLC-06 methodology doc landed). 12 behavior tests green, ruff/mypy clean on touched files (mypy `_load_cslc_complex` annotation issue is pre-existing, out of scope). Commits 5e1dcc0 (RED) + 5cef9dc (GREEN). Plan 03-05 SUMMARY at `.planning/phases/03-cslc-s1-self-consistency-eu-validation/03-05-SUMMARY.md`.
Last session: 2026-04-25T01:34:18.000Z
Stopped at: Phase 3 ready for transition to Phase 4 (DISP comparison adapter; will append §3 DISP ramp-attribution to docs/validation_methodology.md per D-15)
Resume file: invoke `/gsd:transition` for Phase 3 → Phase 4 closeout
