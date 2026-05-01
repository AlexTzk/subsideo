# Phase 9: CSLC EGMS Third Number & Binding Reruns - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 9 reruns the CSLC N.Am. and EU validation cells so they can leave plain CALIBRATING and report BINDING CSLC product-quality outcomes. It populates or names a blocker for the deferred EU EGMS L2a stable-PS residual, resolves the Mojave amplitude-sanity disposition using the regenerated fallback chain, regenerates verdict-bearing CSLC metrics/sidecars, updates the matrix output, and prepares any supported criteria promotion at phase closure.

This phase does not broaden CSLC science scope beyond the N.Am./EU validation cells, does not add new AOI research beyond the Phase 8 regenerated artifact, and does not work on DISP except where shared matrix/sidecar mechanics are touched incidentally.

</domain>

<decisions>
## Implementation Decisions

### Binding Gate Promotion
- **D-01:** Use a dual-record transition for CSLC gate promotion. Phase 9 should keep the existing `criteria.py` CALIBRATING registry stable while reruns execute, write explicit candidate BINDING verdicts using the Phase 8 proposed thresholds, then promote the registry at closure only if rerun evidence supports the promotion.
- **D-02:** Candidate BINDING thresholds are the Phase 8 proposal: `median_of_persistent >= 0.75` and stable-terrain residual `<= 2.0 mm/yr`. If regenerated metrics undercut these thresholds, document the evidence and block or narrow promotion rather than silently moving the gate.
- **D-03:** Do not silently reinterpret old sidecars after changing registry thresholds. Any registry promotion must be paired with regenerated Phase 9 metrics/sidecars and conclusions that make the transition auditable.

### EGMS L2a Residual Failure Policy
- **D-04:** The EU EGMS L2a stable-PS residual should be populated whenever current tooling and sufficient stable-PS support allow it.
- **D-05:** A named EGMS blocker is acceptable only for current upstream access/API/tooling failure or scientifically insufficient stable-PS support after filtering/clipping.
- **D-06:** EGMS blockers must record the evidence needed for audit: request bounds, tool/package version, error or retry evidence, stable-PS counts before and after filtering/clipping, valid paired sample counts, and thresholds such as `stable_std_max` and `min_valid_points`.
- **D-07:** Adapter/schema mismatches are Phase 9 implementation work to fix unless the mismatch traces to current upstream breakage. They should not be treated as acceptable blockers by default.

### Mojave Amplitude Sanity
- **D-08:** Attempt Mojave amplitude sanity across the actual runnable fallback chain. Start with Mojave/Coso-Searles; attempt Pahranagat or Amargosa only if the selected runnable fallback changes or earlier attempts fail.
- **D-09:** For each attempted Mojave burst, record OPERA frame-search evidence and whether amplitude sanity was populated or unavailable. The accepted outcome may be populated metrics or an explicit unavailable disposition with frame-search evidence.
- **D-10:** Do not turn Mojave amplitude sanity into a deep nearby-frame research project. Searching beyond the regenerated fallback chain is out of Phase 9 scope unless planning discovers a trivial existing frame match.

### Matrix and Result Wording
- **D-11:** CSLC N.Am./EU matrix cells should leave plain CALIBRATING in Phase 9. They may report BINDING PASS, BINDING FAIL, or BINDING BLOCKER.
- **D-12:** BINDING BLOCKER is acceptable when a required evidence path is unavailable for an accepted reason and the blocker is named with metric sidecars or frame/API evidence. This satisfies the roadmap requirement that CSLC cells no longer read only as CALIBRATING while preserving scientific honesty.
- **D-13:** Product-quality, reference-agreement, and blocker evidence must remain structurally distinct in sidecars and matrix rendering. Do not collapse EGMS residual, self-consistency gates, and OPERA amplitude sanity into a single prose verdict.

### Rerun Cost Posture
- **D-14:** Use a hybrid audit rerun posture. Phase 9 may reuse cached SAFEs and intermediates after Phase 8-style integrity checks, but must force recomputation of verdict-bearing metrics, sidecars, matrix output, and conclusions.
- **D-15:** Cached-input reuse should be explicit in `meta.json`/sidecars through hashes, cache-hit notes, or provenance fields. The audit claim is regenerated metrics from validated cached inputs, not a full cold redownload.
- **D-16:** If cache integrity or sidecar schema validation fails, rerun or regenerate the affected AOI/cell rather than carrying stale metrics forward.

### the agent's Discretion
- Exact schema shape for candidate BINDING verdict fields, as long as old CALIBRATING criteria and new candidate BINDING outcomes are both auditable.
- Whether registry promotion happens in the final Phase 9 plan or is deferred to Phase 12 if rerun evidence is ambiguous.
- Exact wording of BINDING BLOCKER cells, provided blockers are named and backed by structured evidence.
- Exact implementation split between eval scripts, `matrix_schema.py`, `matrix_writer.py`, and conclusions docs.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and Requirements
- `.planning/ROADMAP.md` - Phase 9 goal, dependency on Phase 8, requirements, and four success criteria.
- `.planning/REQUIREMENTS.md` - CSLC-07, CSLC-10, CSLC-11, VAL-01, and VAL-03 requirement text; includes Phase 8 proposed BINDING threshold rationale.
- `.planning/PROJECT.md` - v1.2 milestone focus, metrics-vs-targets discipline, product-quality/reference-agreement separation, and out-of-scope boundaries.
- `.planning/STATE.md` - current v1.2 position and accumulated prior decisions affecting CSLC and matrix rendering.

### Prior Phase Context and Evidence
- `.planning/milestones/v1.2-phases/08-cslc-gate-promotion-and-aoi-hardening/08-CONTEXT.md` - Phase 8 decisions on threshold proposal, regenerated AOI probe source of truth, SAFE cache integrity, and Phase 9 ownership of final promotion.
- `.planning/milestones/v1.1-phases/07-results-matrix-release-readiness/07-CONTEXT.md` - matrix closure policy, CALIBRATING annotation, and sidecar-driven rendering discipline.
- `.planning/milestones/v1.1-phases/03-cslc-s1-self-consistency-eu-validation/03-CONTEXT.md` - original CSLC self-consistency gate metric, EU three-number schema, and CALIBRATING discipline.
- `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` - SoCal and Mojave/Coso-Searles baseline metrics and Mojave amplitude-sanity follow-up.
- `CONCLUSIONS_CSLC_SELFCONSIST_EU.md` - Iberian baseline metrics, EGMS L2a third-number deferral, and EU fallback notes.
- `docs/validation_methodology.md` - product-quality vs reference-agreement discipline and CSLC cross-version phase-comparison limits.

### Code Entry Points
- `run_eval_cslc_selfconsist_nam.py` - N.Am. CSLC rerun script, SoCal anchor, Mojave fallback chain, amplitude-sanity gating, and N.Am. sidecar writer.
- `run_eval_cslc_selfconsist_eu.py` - EU CSLC rerun script, EGMS L2a download/residual path, EU sidecar writer, and amplitude-sanity best-effort path.
- `src/subsideo/validation/compare_cslc.py` - CSLC amplitude comparison and `compare_cslc_egms_l2a_residual` helper.
- `src/subsideo/validation/criteria.py` - current CALIBRATING CSLC self-consistency criteria and BINDING amplitude criteria; candidate promotion target.
- `src/subsideo/validation/matrix_schema.py` - metrics sidecar schema contract.
- `src/subsideo/validation/matrix_writer.py` - CSLC matrix rendering, CALIBRATING/BINDING wording, and sidecar consumption.
- `tests/unit/test_matrix_writer.py` - existing CSLC self-consistency rendering tests and expected matrix behavior.
- `tests/unit/test_criteria_registry.py` - criteria registry invariants, including current CSLC CALIBRATING thresholds.
- `Makefile` - `make eval-cslc-nam`, `make eval-cslc-eu`, and `make results-matrix` targets.

### Research and Generated Artifacts
- `.planning/milestones/v1.2-research/cslc_gate_promotion_aoi_candidates.md` - Phase 8 regenerated AOI/fallback evidence; downstream agents must verify the path exists and read it before changing AOI or fallback behavior.
- `results/matrix.md` - current matrix output to be regenerated from Phase 9 sidecars.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_eval_cslc_selfconsist_nam.py` already models SoCal plus a Mojave fallback chain and writes `CSLCSelfConsistNAMCellMetrics` into `eval-cslc-selfconsist-nam/metrics.json`.
- `run_eval_cslc_selfconsist_eu.py` already contains `_fetch_egms_l2a`, writes a georeferenced velocity raster, calls `compare_cslc_egms_l2a_residual`, and includes `egms_l2a_stable_ps_residual_mm_yr` when populated.
- `compare_cslc_egms_l2a_residual` already filters stable PS by `mean_velocity_std`, clips to raster bounds, enforces `min_valid_points`, and returns NaN for insufficient valid samples.
- `criteria.py` already has CSLC amplitude BINDING criteria and CSLC self-consistency CALIBRATING criteria with `binding_after_milestone='v1.2'`.
- `matrix_writer.py` already renders CALIBRATING criteria with binding milestone language and has a dedicated CSLC self-consistency rendering path.

### Established Patterns
- Metrics live in `metrics.json`/`meta.json` sidecars and matrix output is generated from sidecars, never parsed from conclusions markdown.
- CALIBRATING/BINDING status changes need to be visible through criteria registry, sidecar schema, rendered matrix text, and tests.
- Expensive eval scripts are allowed to reuse cached inputs, but cache integrity and input hashes are part of the provenance story.
- Per-AOI failure isolation is preferred so one failed fallback or unavailable evidence path becomes a named row/blocker rather than masking the whole cell.

### Integration Points
- Candidate BINDING verdicts likely touch `matrix_schema.py`, `run_eval_cslc_selfconsist_{nam,eu}.py`, `matrix_writer.py`, and CSLC matrix-writer tests.
- EGMS blocker evidence likely touches the EU eval script, `compare_cslc_egms_l2a_residual` diagnostics, metrics schema, and conclusions documentation.
- Mojave amplitude-sanity disposition connects the N.Am. eval script's fallback chain, OPERA reference search/fetch logic, `compare_cslc`, and N.Am. conclusions.
- Final Phase 9 output connects `make eval-cslc-nam`, `make eval-cslc-eu`, `make results-matrix`, `results/matrix.md`, and the CSLC conclusions files.

</code_context>

<specifics>
## Specific Ideas

- Use Phase 8 thresholds as candidate BINDING values, not as silent registry edits before evidence is regenerated.
- Treat EGMS stable-PS insufficiency as a scientific blocker only when counts make the insufficiency explicit.
- The matrix language should make "BINDING BLOCKER" visibly different from both PASS/FAIL and old CALIBRATING.
- Phase 9 should regenerate verdict-bearing sidecars even when cached SAFEs/intermediates are reused.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within Phase 9 scope.

</deferred>

---

*Phase: 09-cslc-egms-third-number-and-binding-reruns*
*Context gathered: 2026-04-30*
