---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: N.Am./EU Validation Parity & Scientific PASS
status: Roadmap created — ready for phase planning
stopped_at: Roadmap created (7 phases, 49 requirements mapped, 100% coverage)
last_updated: "2026-04-20T00:00:00.000Z"
last_activity: 2026-04-20
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-20)

**Core value:** Produce scientifically accurate, OPERA-spec-compliant SAR/InSAR geospatial products over EU AOIs — validated against official reference products to prove correctness.
**Current focus:** v1.1 N.Am./EU Validation Parity & Scientific PASS — drive every product to PASS / honest FAIL with named upgrade path / deferral with dated unblock condition.

## Current Position

Phase: Not started — roadmap created
Plan: —
Status: Roadmap created, ready for `/gsd:plan-phase 1`
Last activity: 2026-04-20 — ROADMAP.md written with 7 phases, 49 v1.1 requirements mapped (100% coverage)

## Performance Metrics

**Velocity:**

- Total plans completed: 0 (v1.1); 21 (v1.0, shipped)
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

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

Last activity: 2026-04-20 — v1.1 roadmap written (7 phases, 49 requirements, 100% coverage)
Last session: 2026-04-20
Stopped at: Roadmap created; ready for `/gsd:plan-phase 1`
Resume file: None
