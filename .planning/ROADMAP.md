# Roadmap: subsideo

## Overview

v1.2 focuses on CSLC Binding & DISP Science Pass work. Phase 08 hardened CSLC validation inputs and proposed binding thresholds; Phase 09 reran CSLC N.Am./EU cells and produced an evidence-backed BINDING BLOCKER deferment rather than promoting the registry. The remaining active roadmap restores the DISP half of v1.2: ERA5/ramp diagnostics first, candidate unwrapper/deramping evaluation second, then conclusions, matrix, methodology, and traceability closure.

## Phases

**Phase Numbering:**
- Integer phases (09, 10, 11): Planned milestone work
- Decimal phases (10.1, 10.2): Urgent insertions, if needed

- [x] **Phase 09: CSLC EGMS Third Number & Binding Reruns** - Regenerate CSLC N.Am./EU sidecars and matrix rows as candidate BINDING outcomes; keep registry promotion blocked by named evidence where needed
- [x] **Phase 10: DISP ERA5 & Ramp Diagnostics** - Rerun SoCal and Bologna DISP evaluations from cached stacks with ERA5 and shared orbit/DEM provenance diagnostics (completed 2026-05-04)
- [x] **Phase 11: DISP Unwrapper & Deramping Candidates** - Evaluate PHASS post-deramping and at least one alternative unwrapper/resolution candidate against unchanged references (completed 2026-05-05)
- [ ] **Phase 12: DISP Conclusions & Release Readiness** - Choose the DISP production posture, update methodology/matrix/requirements traceability, and close the v1.2 release evidence

## Phase Details

### Phase 09: CSLC EGMS Third Number & Binding Reruns
**Goal**: Rerun the CSLC N.Am. and EU validation cells so they leave plain CALIBRATING and report audit-ready candidate BINDING outcomes, while preserving scientific blockers instead of promoting criteria prematurely.
**Depends on**: Phase 08
**Requirements**: CSLC-07, CSLC-10, CSLC-11, VAL-01, VAL-03
**Success Criteria** (what must be TRUE):
  1. `make eval-cslc-nam` writes regenerated `metrics.json` and `meta.json` sidecars with candidate BINDING evidence or named blocker evidence.
  2. `make eval-cslc-eu` writes regenerated `metrics.json` and `meta.json` sidecars with EGMS L2a residual evidence or named blocker evidence.
  3. Mojave/Coso-Searles OPERA amplitude sanity is populated or has explicit frame-search unavailable evidence.
  4. `results/matrix.md` renders CSLC N.Am./EU as BINDING PASS, BINDING FAIL, or BINDING BLOCKER, not plain CALIBRATING.
  5. `criteria.py` remains CALIBRATING unless regenerated sidecars support registry promotion.
**Plans**: 5/5 plans complete

Plans:
- [x] 09-01-PLAN.md - Candidate BINDING sidecar schema and locked threshold contract
- [x] 09-02-PLAN.md - EGMS L2a diagnostics and named blocker evidence
- [x] 09-03-PLAN.md - Mojave OPERA amplitude sanity and fallback frame-search evidence
- [x] 09-04-PLAN.md - CSLC matrix rendering for candidate BINDING outcomes
- [x] 09-05-PLAN.md - CSLC reruns, matrix regeneration, and guarded promotion/deferment closure

### Phase 10: DISP ERA5 & Ramp Diagnostics
**Goal**: Establish whether ERA5 tropospheric correction and shared orbit/DEM/terrain provenance explain or improve the v1.1 DISP SoCal and Bologna reference-agreement failures before changing the production unwrapper.
**Depends on**: Phase 09
**Requirements**: DISP-06, RTCSUP-02
**Success Criteria** (what must be TRUE):
  1. User can rerun SoCal and Bologna DISP evaluations from cached CSLC stacks with ERA5 enabled and disabled.
  2. Conclusions report whether ramp magnitude, ramp direction stability, reference correlation, bias, and RMSE improve relative to the v1.1 baselines (`r=0.049` SoCal, `r=0.336` Bologna).
  3. Shared orbit, DEM, slope, and terrain provenance diagnostics explain whether failures are atmospheric, terrain-driven, cache/provenance-related, or still inconclusive.
  4. Product-quality, reference-agreement, and ramp-attribution metrics remain structurally separate in sidecars and conclusions.
**Plans**: 4

Plans:
- [x] 10-01-PLAN.md - Schema and diagnostic helper contract
- [x] 10-02-PLAN.md - ERA5 toggle and separate diagnostic output routing
- [x] 10-03-PLAN.md - Orbit, DEM, terrain, and cache provenance sidecars
- [x] 10-04-PLAN.md - Matrix/conclusions rendering and live diagnostic rerun/blocker handling

### Phase 11: DISP Unwrapper & Deramping Candidates
**Goal**: Evaluate the next DISP science candidate(s) from the v1.1 Unwrapper Selection brief without changing the native 5 x 10 m production output or the `prepare_for_reference(method=...)` validation discipline.
**Depends on**: Phase 10
**Requirements**: DISP-07, DISP-08, DISP-09
**Success Criteria** (what must be TRUE):
  1. User can apply a PHASS post-deramping candidate to the v1.1 cached DISP stacks and compare it against the unchanged reference pipeline.
  2. User can run at least one alternative candidate selected from SPURT native, tophu/SNAPHU tiled, or 20 x 20 m validation fallback.
  3. Candidate failures are captured as structured metrics or blocker evidence, not terminal-only logs.
  4. N.Am. OPERA and EU EGMS comparisons continue using explicit `prepare_for_reference(method=...)`.
  5. Product-quality, reference-agreement, and ramp-attribution outcomes remain separated in sidecars, matrix output, and conclusions.
**Plans**: 5

Plans:
**Wave 1**
- [x] 11-01-PLAN.md - Candidate evidence schema and helper contract

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 11-02-PLAN.md - SPURT native candidate execution

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 11-03-PLAN.md - PHASS pre-inversion deramping candidate

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 11-04-PLAN.md - Candidate sidecars and matrix hints

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 11-05-PLAN.md - Candidate conclusion sections

### Phase 12: DISP Conclusions & Release Readiness
**Goal**: Close v1.2 by choosing the DISP production posture and updating all release-facing artifacts so CSLC/DISP outcomes, requirements, matrix cells, and methodology are traceable and audit-ready.
**Depends on**: Phase 11
**Requirements**: DISP-10, VAL-01, VAL-02, VAL-03, VAL-04
**Success Criteria** (what must be TRUE):
  1. Updated DISP conclusions choose one production posture: PASS, keep PHASS with deramping, switch unwrapper, use a coarser validation fallback, or defer with one named blocker and dated unblock condition.
  2. `make eval-cslc-nam`, `make eval-cslc-eu`, `make eval-disp-nam`, and `make eval-disp-eu` can be run independently from cached intermediates and write validated `metrics.json` plus `meta.json` sidecars.
  3. `docs/validation_methodology.md` includes v1.2 additions for CSLC gate promotion/deferment, EGMS L2a residual handling, DISP ERA5/deramping/unwrapper diagnostics, and CALIBRATING-to-BINDING conditions.
  4. `results/matrix.md` has v1.2 CSLC/DISP N.Am./EU outcomes with no empty cells and no collapsed product-quality/reference-agreement verdicts.
  5. `REQUIREMENTS.md` traceability has no stale v1.1 Pending rows and maps every v1.2 requirement to exactly one phase.
**Plans**: TBD

Plans:
- [ ] 12-01-PLAN.md - TBD after Phase 11 evidence

## Progress

**Execution Order:**
Phases execute in numeric order: 09 -> 10 -> 11 -> 12

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 09. CSLC EGMS Third Number & Binding Reruns | 5/5 | Complete | 2026-05-02 |
| 10. DISP ERA5 & Ramp Diagnostics | 4/4 | Complete   | 2026-05-04 |
| 11. DISP Unwrapper & Deramping Candidates | 5/5 | Complete   | 2026-05-05 |
| 12. DISP Conclusions & Release Readiness | 0/TBD | Not started | - |
