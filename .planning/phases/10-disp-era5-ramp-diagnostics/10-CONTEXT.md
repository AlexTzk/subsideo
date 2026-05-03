# Phase 10: DISP ERA5 & Ramp Diagnostics - Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 10 activates the next DISP diagnostic step before changing unwrapper or production resolution. It reruns the v1.1 SoCal and Bologna DISP cells with an ERA5-on path where possible, compares against the documented v1.1 no-ERA5/off baselines, and adds diagnostic provenance for orbit, DEM, slope, terrain, stable-mask retention, ramp attribution, and cache/input reuse.

This phase answers whether atmospheric correction, orbit/DEM/terrain effects, or input provenance explain the v1.1 DISP reference-agreement failures enough to guide Phase 11 candidate ordering. It does not choose the production unwrapper, add new AOIs, change native 5 x 10 m production output, or broaden into a general RTC/terrain investigation.

</domain>

<decisions>
## Implementation Decisions

### ERA5 Rerun Posture
- **D-01:** Use the existing v1.1 no-ERA5/off results as the warm baseline. Phase 10 should run the new ERA5-on path where possible and focus on diagnostic deltas rather than re-proving the same baseline FAIL numbers.
- **D-02:** ERA5 blockers are acceptable for CDS API / ERA5 data access failures. Local code, adapter, conda environment, `pyaps3`, MintPy, or integration issues are Phase 10 implementation work by default.
- **D-03:** If ERA5 helps modestly but consistently and does not introduce new artifacts, Phase 10 should make ERA5-on the required baseline for Phase 11 candidates without doubling every Phase 11 candidate into on/off variants.
- **D-04:** SoCal and Bologna may receive cell-specific diagnostic verdicts and Phase 11 notes. Do not force one shared attribution label across AOIs with different coherence regimes and reference products.

### Attribution Verdict Wording
- **D-05:** Use `inconclusive_narrowed` as the human-facing concept when diagnostics eliminate at least one major cause but cannot honestly assign a single source. Keep the top-level machine label honest rather than overclaiming.
- **D-06:** Do not add `inconclusive_narrowed` as a new attribution literal. Keep `attributed_source="inconclusive"` for compatibility and add structured detail fields such as `eliminated_causes`, `remaining_causes`, and `next_test`.
- **D-07:** The structured cause taxonomy for Phase 10 is `tropospheric`, `orbit`, `terrain`, `unwrapper`, and `cache_or_input_provenance`.
- **D-08:** Mark a cause eliminated only when targeted diagnostic evidence directly contradicts it. Softer "unlikely" judgments belong in conclusions prose, not in structured `eliminated_causes`.
- **D-09:** If a sane ERA5-on run consistently worsens or does not improve relevant metrics, Phase 10 may treat that as anti-evidence for a tropospheric cause and eliminate `tropospheric` for that cell where justified.
- **D-10:** Store eliminated causes, remaining causes, and next discriminating tests per cell. SoCal and Bologna each get their own structured cause fields.

### Diagnostic Provenance
- **D-11:** Terrain provenance must include a multi-signal terrain summary: slope distribution, stable-mask retention, elevation range, and terrain-vs-ramp correlation.
- **D-12:** Orbit provenance must include filenames/types and coverage sanity: verify orbit validity windows cover each sensing time.
- **D-13:** DEM provenance must include source, tile list/hash, nodata fraction, elevation range, and slope distribution.
- **D-14:** Cache/input provenance must include hashes plus cache mode for major inputs and outputs: reused, regenerated, or redownloaded.
- **D-15:** Diagnostic provenance lives in schema-valid sidecars as the canonical record and in readable conclusions tables for review. Do not create a separate provenance report unless the planner discovers a strong reason.
- **D-16:** Provenance sidecars must schema-validate before conclusions are updated. Invalid sidecars block Phase 10 closure.

### Phase 11 Reordering Threshold
- **D-17:** A meaningful Phase 10 improvement requires two-signal confirmation: at least two of attribution flip, reference correlation improvement, bias/RMSE improvement, or ramp magnitude reduction.
- **D-18:** Apply a hybrid reordering rule. Cell-specific notes are allowed, but the global Phase 11 candidate order changes only with cross-cell support.
- **D-19:** If only one cell meets the two-signal rule, keep the global Phase 11 candidate order and annotate the cell-specific exception.
- **D-20:** Ramp magnitude reduction alone is not enough to make ERA5-on the required Phase 11 baseline or reorder candidates. It must be paired with reference-agreement improvement or an attribution flip.
- **D-21:** If ERA5 does not meet the two-signal rule, Phase 11 should follow the v1.1 brief order: SPURT native first, then PHASS deramping, then tophu/SNAPHU, then 20 x 20 m fallback.

### the agent's Discretion
- Exact schema field names for Phase 10 diagnostic detail fields, as long as they preserve `attributed_source="inconclusive"` compatibility and expose per-cell `eliminated_causes`, `remaining_causes`, and `next_test`.
- Exact numerical cutoffs for "material" ramp reduction or meaningful r/bias/RMSE improvement, provided the final plan implements the two-signal rule and documents the thresholds before reading results.
- Exact implementation split between `run_eval_disp.py`, `run_eval_disp_egms.py`, `matrix_schema.py`, helper modules, and conclusions docs.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and Requirements
- `.planning/ROADMAP.md` - Phase 10 goal, dependencies, requirements, and success criteria.
- `.planning/REQUIREMENTS.md` - DISP-06 and RTCSUP-02 requirement text; Phase 11/12 traceability for downstream impacts.
- `.planning/PROJECT.md` - v1.2 milestone focus, validation criteria, metrics-vs-targets discipline, out-of-scope boundaries, and Phase 09 CSLC state.
- `.planning/STATE.md` - current Phase 10 position and accumulated decisions.

### Prior DISP Decisions and Evidence
- `.planning/milestones/v1.1-phases/04-disp-s1-comparison-adapter-honest-fail/04-CONTEXT.md` - locked DISP comparison-adapter decisions, `prepare_for_reference(method=...)`, ramp-attribution framing, and v1.1 deferrals.
- `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md` - v1.1 handoff brief; baseline metrics, ERA5-first recommendation, and Phase 11 candidate order.
- `CONCLUSIONS_DISP_N_AM.md` - SoCal v1.1 baseline, reference-agreement FAIL, ramp attribution, and product-quality context.
- `CONCLUSIONS_DISP_EU.md` - Bologna v1.1 baseline, EGMS comparison, low-coherence finding, ramp attribution, and product-quality context.
- `docs/validation_methodology.md` - product-quality/reference-agreement separation and DISP comparison-adapter methodology.

### Recent CSLC / Shared-Validation Context
- `.planning/milestones/v1.2-phases/08-cslc-gate-promotion-and-aoi-hardening/08-CONTEXT.md` - shared cache integrity, provenance, and terrain/stable-mask diagnostics discipline.
- `.planning/phases/09-cslc-egms-third-number-binding-reruns/09-CONTEXT.md` - sidecar-first candidate verdict pattern, named blocker discipline, and regenerated sidecar/matrix posture.

### Code Entry Points
- `run_eval_disp.py` - N.Am. SoCal DISP eval script, warm cached stack, OPERA reference comparison, product-quality and ramp-attribution sidecar writer.
- `run_eval_disp_egms.py` - EU Bologna DISP eval script, EGMS L2a comparison, warm cached stack, product-quality and ramp-attribution sidecar writer.
- `src/subsideo/products/disp.py` - DISP production pipeline and current ERA5/MintPy configuration surface; native product output should not be downgraded in this phase.
- `src/subsideo/validation/compare_disp.py` - `prepare_for_reference(method=...)` adapter and DISP comparison helpers.
- `src/subsideo/validation/selfconsistency.py` - `fit_planar_ramp`, `compute_ramp_aggregate`, and `auto_attribute_ramp` helpers.
- `src/subsideo/validation/matrix_schema.py` - existing DISP sidecar schema and likely home for Phase 10 diagnostic/provenance fields.
- `src/subsideo/validation/matrix_writer.py` - sidecar-driven matrix rendering; downstream Phase 12 will consume Phase 10 sidecar shape.
- `src/subsideo/validation/harness.py` - validation cache and SAFE integrity helpers; reuse existing cache/provenance patterns.
- `Makefile` - `make eval-disp-nam`, `make eval-disp-eu`, and later `make results-matrix`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_eval_disp.py` and `run_eval_disp_egms.py` already define `REFERENCE_MULTILOOK_METHOD = "block_mean"` and write DISP metrics sidecars from cached SoCal/Bologna stacks.
- `DISPCellMetrics`, `RampAttribution`, `PerIFGRamp`, and `RampAggregate` already exist in `src/subsideo/validation/matrix_schema.py`; Phase 10 should extend additively rather than breaking v1.1 sidecars.
- `fit_planar_ramp`, `compute_ramp_aggregate`, and `auto_attribute_ramp` already provide the core ramp-attribution machinery. The existing auto-rule never returns `tropospheric`; Phase 10 can add diagnostic detail fields rather than changing that literal.
- `prepare_for_reference(method=...)` already enforces explicit comparison methods and remains validation-only.
- Phase 08/09 cache/provenance patterns already require input hashes, cache reuse/redownload notes, and schema-valid blocker evidence.

### Established Patterns
- Metrics live in `metrics.json` / `meta.json` sidecars and conclusions summarize them. Matrix output is generated from sidecars, never parsed from conclusions markdown.
- Product-quality, reference-agreement, and diagnostic attribution are separate evidence categories. Do not collapse them into a single prose verdict.
- Warm reruns from cached inputs are acceptable when hashes/cache mode make reuse explicit.
- Named blockers are acceptable for current upstream data/API access problems, but local adapter or schema mismatches should be implementation work unless traced to upstream breakage.
- Phase 11 candidate ordering is brief-driven unless Phase 10 produces enough diagnostic evidence to justify changing it.

### Integration Points
- ERA5 diagnostics likely touch `run_eval_disp.py`, `run_eval_disp_egms.py`, `src/subsideo/products/disp.py`, and the MintPy/pyaps configuration path.
- Diagnostic provenance likely touches `matrix_schema.py`, the eval scripts, helper code for orbit/DEM/slope summaries, and conclusions tables.
- Any sidecar shape change must be validated before conclusions updates and should preserve legacy v1.1 DISP sidecar compatibility.
- Phase 10 output feeds Phase 11 candidate choice and Phase 12 matrix/methodology closure.

</code_context>

<specifics>
## Specific Ideas

- "Inconclusive narrowed" is the review concept, not a new schema literal.
- Use ERA5-on as the Phase 11 baseline only if improvement is consistent and paired with another diagnostic signal.
- If ERA5 does not change the diagnosis, Phase 11 starts with SPURT native per the v1.1 brief.
- Terrain/orbit/DEM provenance should be strong enough to rule causes in or out, but plotting and deep terrain investigation are optional planner discretion rather than required deliverables.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within Phase 10 scope.

</deferred>

---

*Phase: 10-disp-era5-ramp-diagnostics*
*Context gathered: 2026-05-03*
