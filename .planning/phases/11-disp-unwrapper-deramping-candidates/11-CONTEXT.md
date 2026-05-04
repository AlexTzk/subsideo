# Phase 11: disp-unwrapper-deramping-candidates - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 11 evaluates the next DISP science candidates from the v1.1 Unwrapper Selection brief using the existing cached SoCal and Bologna DISP stacks. It runs SPURT native and PHASS post-deramping candidate paths, compares them against unchanged OPERA/EGMS references through explicit `prepare_for_reference(method=...)`, and records product-quality, reference-agreement, ramp-attribution, candidate-status, and blocker evidence separately.

This phase does not change the native 5 x 10 m production default, does not promote ERA5 into a required baseline, does not add new AOIs, and does not choose the final production posture. Phase 12 consumes Phase 11 evidence to choose PASS, PHASS deramping, unwrapper switch, coarser fallback, or named deferment.

</domain>

<decisions>
## Implementation Decisions

### Candidate Execution Posture
- **D-01:** Phase 11 must run both SPURT native and PHASS post-deramping in the same phase so Phase 12 gets a direct unwrapper-vs-deramp comparison.
- **D-02:** Both candidates must run on both validation cells: SoCal against OPERA DISP-S1 and Bologna against EGMS L2a.
- **D-03:** Do not early-stop after SPURT success. The core Phase 11 result set is four candidate-cell outcomes: SPURT/SoCal, SPURT/Bologna, PHASS deramping/SoCal, and PHASS deramping/Bologna.
- **D-04:** Execute SPURT first, then PHASS deramping. This honors Phase 10 evidence that ERA5 did not improve the failures and the v1.1/Phase 10 ordering that points first to an unwrapper-class test.

### Deramping Semantics
- **D-05:** PHASS post-deramping must subtract fitted planar ramps from per-IFG unwrapped phases before MintPy/time-series inversion. Do not treat final-velocity-raster deramping as the main candidate.
- **D-06:** PHASS deramping is a validation candidate only in Phase 11. It may produce candidate outputs and sidecars for comparison, but must not change the native production default.
- **D-07:** PHASS deramping must include a lightweight deformation-signal sanity check, especially for SoCal, so a metric gain is not accepted as production-safe if it looks like real long-wavelength deformation was erased.
- **D-08:** A flagged deformation-signal sanity check blocks a Phase 12 production recommendation for PHASS deramping, but does not block Phase 11 from reporting candidate metrics.

### Candidate Evidence and Blockers
- **D-09:** Every candidate-cell outcome must be one of `PASS`, `FAIL`, or `BLOCKER` with structured sidecar evidence. Numeric metrics and conclusions prose are not sufficient by themselves.
- **D-10:** A `BLOCKER` must include at minimum candidate name, cell, failed stage, exception/error summary, evidence or log artifact paths, and cached-input validity.
- **D-11:** If a candidate blocks after producing some outputs, preserve schema-valid partial metrics and mark them clearly as partial so they are useful for replanning without being mistaken for comparable PASS/FAIL evidence.
- **D-12:** Candidate results should surface in canonical sidecars, explanatory conclusion sections, and compact matrix status or hint text. Matrix rendering must remain compact and must not collapse product-quality, reference-agreement, and ramp-attribution evidence into one verdict.

### ERA5 Carry-Forward
- **D-13:** Phase 10 ERA5-on diagnostics did not promote ERA5 into a required Phase 11 baseline. SoCal worsened (`r=0.0071`, `bias=+55.43 mm/yr`, `RMSE=70.04 mm/yr`), Bologna was effectively unchanged (`r=0.3358`, `bias=+3.46 mm/yr`, `RMSE=5.24 mm/yr`), and both cells remained `inconclusive` for ramp attribution.
- **D-14:** Phase 11 should therefore follow the Phase 10/v1.1 global order: SPURT native first, PHASS deramping second, with tophu/SNAPHU and 20 x 20 m fallback left as later ladder steps unless planning discovers they are necessary to satisfy the stated Phase 11 success criteria.

### the agent's Discretion
- Exact schema field names for candidate status, blockers, partial metrics, and matrix hint text, provided the sidecars remain schema-valid and preserve the decisions above.
- Exact implementation split between eval scripts, helper modules, `matrix_schema.py`, `matrix_writer.py`, conclusion files, and tests.
- Exact lightweight deformation-signal sanity check method, provided it is explicit enough for Phase 12 to decide whether PHASS deramping is production-safe.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and Requirements
- `.planning/ROADMAP.md` - Phase 11 goal, dependency on Phase 10, requirements, and success criteria.
- `.planning/REQUIREMENTS.md` - DISP-07, DISP-08, and DISP-09 requirement text; out-of-scope boundary preserving native production resolution.
- `.planning/PROJECT.md` - v1.2 milestone focus, DISP validation criteria, metrics-vs-targets discipline, and explicit scope limits.
- `.planning/STATE.md` - current milestone state and accumulated validation decisions.

### Prior DISP Evidence and Decisions
- `.planning/phases/10-disp-era5-ramp-diagnostics/10-CONTEXT.md` - ERA5 diagnostic decision rules, two-signal promotion rule, and Phase 11 ordering threshold.
- `.planning/phases/10-disp-era5-ramp-diagnostics/10-04-SUMMARY.md` - live ERA5-on SoCal/Bologna results and explicit Phase 11 candidate-order disposition.
- `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md` - candidate definitions, original success criteria, compute tiers, and risks for PHASS deramping, SPURT, tophu/SNAPHU, and 20 x 20 m fallback.
- `CONCLUSIONS_DISP_N_AM.md` - SoCal v1.1 and Phase 10 DISP evidence, OPERA reference-agreement context, and ramp-attribution sections.
- `CONCLUSIONS_DISP_EU.md` - Bologna v1.1 and Phase 10 DISP evidence, EGMS comparison context, low-coherence finding, and ramp-attribution sections.
- `docs/validation_methodology.md` - `prepare_for_reference(method=...)`, product-quality/reference-agreement separation, multilook ADR, and Phase 10 ERA5 diagnostic guidance.

### Code Entry Points
- `run_eval_disp.py` - N.Am. SoCal DISP eval script, cached stack orchestration, OPERA comparison, ERA5 diagnostic sidecar fields, and existing PHASS path.
- `run_eval_disp_egms.py` - EU Bologna DISP eval script, EGMS L2a comparison, cached stack orchestration, ERA5 diagnostic sidecar fields, and existing PHASS path.
- `src/subsideo/products/disp.py` - production DISP pipeline, current `UnwrapMethod.PHASS` selection, unwrapped IFG handling, and native product behavior that Phase 11 must not silently downgrade.
- `src/subsideo/validation/compare_disp.py` - `prepare_for_reference(method=...)` adapter and DISP reference comparison helpers.
- `src/subsideo/validation/selfconsistency.py` - `fit_planar_ramp`, `compute_ramp_aggregate`, and `auto_attribute_ramp` helpers for deramping/ramp evidence.
- `src/subsideo/validation/matrix_schema.py` - existing `DISPCellMetrics`, `RampAttribution`, `Era5Diagnostic`, and `CauseAssessment` schema patterns; likely home for candidate evidence additions.
- `src/subsideo/validation/matrix_writer.py` - sidecar-driven matrix rendering; should add compact candidate hints without collapsing evidence streams.
- `Makefile` - `make eval-disp-nam`, `make eval-disp-eu`, and `make results-matrix` orchestration targets.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_eval_disp.py` and `run_eval_disp_egms.py` already run the SoCal/Bologna cells from cached stacks and write schema-valid `DISPCellMetrics` sidecars.
- `src/subsideo/products/disp.py` currently wires dolphin with `UnwrapMethod.PHASS`; Phase 11 can introduce a candidate configuration path for SPURT without changing the production default.
- `fit_planar_ramp`, `compute_ramp_aggregate`, and `auto_attribute_ramp` already provide the core ramp-fit and attribution machinery needed for PHASS post-deramping evidence.
- `DISPCellMetrics`, `RampAttribution`, `Era5Diagnostic`, and `CauseAssessment` provide additive schema patterns for new candidate-status and blocker structures.
- `matrix_writer.py` already renders compact Phase 10 ERA5 diagnostic hints from sidecars, which is the nearest pattern for Phase 11 candidate hints.

### Established Patterns
- Metrics live in `metrics.json` / `meta.json` sidecars and matrix output is generated from sidecars, never parsed from conclusions markdown.
- Product-quality, reference-agreement, and diagnostic/ramp attribution are separate evidence streams and must remain separate in sidecars, matrix cells, and conclusions.
- Warm reruns from cached inputs are acceptable when cache mode, hashes, or validity evidence make reuse explicit.
- Named blockers are acceptable when they include structured evidence; terminal-only failures are not sufficient.
- ERA5 is diagnostic evidence only for this path unless a future phase explicitly changes that posture.

### Integration Points
- SPURT candidate work likely touches dolphin unwrap configuration in the eval path and may require helper functions to route output directories so SPURT and PHASS candidate products do not overwrite each other.
- PHASS deramping likely touches unwrapped IFG handling before MintPy/time-series inversion, plus sidecar fields for deramp parameters, partial metrics, and deformation-signal sanity checks.
- Candidate evidence likely touches `matrix_schema.py`, eval scripts, conclusions, matrix writer tests, and possibly new candidate-specific tests.
- Phase 12 will consume Phase 11 sidecars and conclusions to choose production posture, so Phase 11 should keep enough structured detail to avoid re-running or reinterpreting terminal logs.

</code_context>

<specifics>
## Specific Ideas

- The required core matrix is SPURT/SoCal, SPURT/Bologna, PHASS deramping/SoCal, and PHASS deramping/Bologna.
- SPURT is first because ERA5 did not improve the failures and the remaining leading hypothesis is an unwrapper-class issue.
- PHASS deramping remains required despite SPURT-first ordering because DISP-07 needs deramping evidence and Phase 12 needs direct comparison.
- Deramping can report metrics even when the signal-preservation sanity check flags risk; the flag blocks production recommendation, not candidate measurement.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within Phase 11 scope.

</deferred>

---

*Phase: 11-disp-unwrapper-deramping-candidates*
*Context gathered: 2026-05-04*
