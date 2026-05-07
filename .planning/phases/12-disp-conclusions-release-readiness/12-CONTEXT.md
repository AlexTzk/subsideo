# Phase 12: DISP Conclusions & Release Readiness - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 12 closes v1.2 by choosing the DISP production posture from Phase 10–11 evidence, appending the posture decision to both DISP conclusions files, updating the validation methodology doc with v1.2 additions, upgrading the matrix to a v1.2-versioned release artifact, and closing REQUIREMENTS.md traceability so no v1.2 requirement has a stale Pending row.

This phase writes conclusions, updates release-facing documents, and marks requirements — it does not run any new eval candidates. tophu/SNAPHU and the 20×20 m fallback are explicitly deferred to v1.3.

</domain>

<decisions>
## Implementation Decisions

### DISP Production Posture
- **D-01:** v1.2 closes with a **deferred** posture for DISP. Neither SPURT native nor PHASS post-deramping passes criteria on either cell (Phase 11 Phase 11 SPURT/SoCal r=0.003/bias=+19.9mm, SPURT/Bologna r=0.325/bias=+3.44mm, both PHASS variants deformation-sanity-flagged). No production recommendation until unblock conditions are met.
- **D-02:** The named blocker is the **SPURT orbit-class ramp on Bologna** (σ=7.1° → systematic baseline contribution identified). The unblock path is: **tophu/SNAPHU tiled unwrapping with orbital baseline deramping, v1.3 milestone**. The dated unblock condition is: both cells (SoCal + Bologna) pass r > 0.92 AND bias < 3 mm/yr in the same tophu/SNAPHU run.
- **D-03:** SPURT native is named as the **interim best candidate** in conclusions with an explicit caveat: neither cell passes criteria; Bologna is the nearest (bias=3.44 mm/yr, 0.44 mm/yr from threshold); use only if production cannot wait for v1.3.
- **D-04:** **PHASS post-deramping is retired** from the candidate ladder. Structural reason: SBAS re-inversion after external IFG-level deramping is numerically unstable on both cells (trend_delta=-390 mm/yr SoCal, -593 mm/yr Bologna); the deformation sanity flag is cross-cell consistent and is not a parameter-tuning issue. The v1.3 brief should not include PHASS post-deramping as a step.
- **D-05:** ERA5 is retained as a diagnostic option for v1.3 (not promoted to required baseline). Phase 10 worsened SoCal (r=0.007 vs 0.049); Bologna was unchanged. Not a factor in the posture choice.

### Conclusions Files (CONCLUSIONS_DISP_N_AM.md + CONCLUSIONS_DISP_EU.md)
- **D-06:** Add a `## Phase 12 Production Posture` section to **each** conclusions file (append, consistent with Phase 10–11 append pattern). Do not write a standalone release doc. Each section should include: posture label, named blocker, unblock condition, interim SPURT note, PHASS retirement rationale, and v1.3 recommended first step.

### Methodology Doc (docs/validation_methodology.md)
- **D-07:** Write **four new top-level sections (§9–§12)** appended to the existing §1–§8. Parallel structure to existing sections; each section citable by downstream agents independently.
  - §9: CSLC CALIBRATING-to-BINDING conditions — full ADR-style section documenting the two-signal promotion rule (coherence + residual thresholds met + no named blocker), the named-blocker definition, and the dated unblock conditions for Mojave and Iberian AOIs.
  - §10: EGMS L2a reference methodology and Phase 9 named-blocker pattern — how EGMS L2a is used as the EU DISP reference (spatial join, `prepare_for_reference` discipline), plus the candidate-BINDING-with-named-blocker pattern established in Phase 9 for EGMS-dependent CSLC cells.
  - §11: DISP ERA5/deramping/unwrapper diagnostics — consolidates Phase 10 ERA5 two-signal rule, Phase 11 candidate evaluation methodology, PHASS deramping deformation sanity check definition, and SPURT orbit-class attribution pattern.
  - §12: DISP deferred posture and v1.3 handoff — documents the deferred posture decision, unblock criteria, PHASS retirement, interim SPURT status, and the v1.3 recommended candidate order.
- **D-08:** The §9 CSLC CALIBRATING-to-BINDING section must be full ADR-style: problem statement, promotion rule, named-blocker definition, per-AOI unblock conditions, and future promotion guidance. This information exists nowhere else in the docs.

### Requirements Traceability (REQUIREMENTS.md)
- **D-09:** **DISP-06** (ERA5 toggle): mark `[x]` satisfied. Phase 10 delivered the ERA5 toggle and reported results; the requirement does not mandate improvement, only the capability and reporting.
- **D-10:** **CSLC-07** (BINDING promotion): mark as **partial** with a note: `Partial — candidate BINDING evidence with named blockers (Mojave: required_aoi_binding_blocker, Iberian: required_aoi_binding_blocker). Full BINDING deferred to v1.3 pending AOI expansion.` Do not mark `[x]` (full BINDING was not achieved). Do not leave it blank.
- **D-11:** **DISP-07, DISP-08, DISP-09**: already marked `[x]` by Phase 11 VERIFICATION.md — no changes needed.
- **D-12:** **DISP-10, VAL-01, VAL-02, VAL-03, VAL-04**: mark `[x]` satisfied as Phase 12 delivers each one. Update status cells only; do not rebuild the full traceability table.
- **D-13:** Do not rebuild the full traceability table. Update individual cells and add CSLC-07 partial note inline.

### Matrix (results/matrix.md)
- **D-14:** Rename to **v1.2 Results Matrix** — add a version header block at the top (version, date, milestone summary). Keep existing table structure.
- **D-15:** Update DISP NAM and DISP EU rows to show **named-blocker posture first**, candidate evidence in parens. Format: `DEFERRED — spurt:FAIL / deramp:retired / unblock=tophu-SNAPHU+orbital-deramping / interim=spurt-native(caveated)` in the product-quality column. Reference-agreement column keeps measured r and bias values from Phase 11.
- **D-16:** The matrix header says "v1.1 Results Matrix" — Phase 12 updates this to "v1.2 Results Matrix" with an introductory block noting the milestone, date, and completion status.

### Claude's Discretion
- Exact wording of the PHASS retirement rationale in conclusions — the structural argument (SBAS inversion instability on deramped IFGs) must be present but precise prose is at agent discretion.
- Exact section numbering and ToC update in `docs/validation_methodology.md` (the table of contents must be updated to include §9–§12).
- Whether to add a cross-reference footnote in the existing Phase 10 §8 (ERA5 diagnostic) linking forward to the new §11 — agent may do this if it improves navigability.
- Exact matrix row formatting as long as D-15 posture-first ordering is preserved.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and Requirements
- `.planning/ROADMAP.md` — Phase 12 goal, success criteria, and dependency on Phase 11.
- `.planning/REQUIREMENTS.md` — DISP-10, VAL-01, VAL-02, VAL-03, VAL-04 requirement text; CSLC-07 and DISP-06 status context.
- `.planning/PROJECT.md` — v1.2 milestone focus, validation criteria, and out-of-scope boundaries.
- `.planning/STATE.md` — current milestone state and accumulated decisions.

### Phase 11 Evidence (what Phase 12 consumes)
- `.planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md` — candidate execution posture decisions, deramping semantics, blocker evidence rules, ERA5 carry-forward.
- `.planning/phases/11-disp-unwrapper-deramping-candidates/11-VERIFICATION.md` — DISP-07/08/09 satisfaction evidence; SPURT and PHASS outcomes confirmed.
- `CONCLUSIONS_DISP_N_AM.md` — Phase 11 SoCal candidate table: SPURT r=0.003/bias=+19.9mm (N=40k sparse), PHASS deramp r=-0.116/bias=+21.96mm/sanity-flagged. Phase 12 appends §Phase12 here.
- `CONCLUSIONS_DISP_EU.md` — Phase 11 Bologna candidate table: SPURT r=0.325/bias=+3.44mm (orbit-class ramp σ=7.1°), PHASS deramp r=0.052/bias=-3.07mm/sanity-flagged. Phase 12 appends §Phase12 here.

### Phase 10 Evidence
- `.planning/phases/10-disp-era5-ramp-diagnostics/10-CONTEXT.md` — ERA5 two-signal rule, Phase 11 ordering decisions.

### CSLC State (for methodology §9 and CSLC-07 traceability)
- `.planning/phases/09-cslc-egms-third-number-binding-reruns/09-CONTEXT.md` — candidate BINDING evidence, named-blocker pattern, EGMS third-number methodology.
- `results/matrix.md` — current CSLC NAM/EU rows: BINDING BLOCKER / Mojave and Iberian named blockers.

### Release-Facing Artifacts to Update
- `docs/validation_methodology.md` — existing §1–§8; Phase 12 appends §9–§12. MUST read full doc before writing to avoid ToC/numbering conflicts.
- `results/matrix.md` — current v1.1 matrix; Phase 12 upgrades to v1.2 header and updates DISP rows.
- `.planning/REQUIREMENTS.md` — Phase 12 marks DISP-10, VAL-01–04 satisfied; adds CSLC-07 partial note; marks DISP-06 satisfied.

### v1.1 Brief
- `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md` — original candidate ordering, success criteria per candidate; Phase 12 should reference and update/supersede the relevant ladder steps.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_eval_disp.py` and `run_eval_disp_egms.py` — already write validated `metrics.json` / `meta.json` sidecars from cached stacks; no new eval runs needed for Phase 12.
- `src/subsideo/validation/matrix_schema.py` — existing `DISPCellMetrics`, candidate_outcomes schema already has SPURT/PHASS entries from Phase 11; no schema changes needed.
- `src/subsideo/validation/matrix_writer.py` — existing sidecar-driven rendering; Phase 12 updates prose/header in `results/matrix.md`, not the matrix_writer code.

### Established Patterns
- Append-only conclusions: Phase 10 and 11 both appended new sections to CONCLUSIONS files without modifying prior sections. Phase 12 follows the same pattern.
- Phase 1 D-15 append-only methodology doc discipline applies: new v1.2 sections (§9–§12) are appended; no edits to §1–§8 except cross-reference footnotes.
- Metrics live in sidecars; conclusions summarize. Matrix is generated from sidecars (matrix_writer), but `results/matrix.md` itself is committed as a rendered artifact after each milestone.

### Integration Points
- `docs/validation_methodology.md` ToC (lines 17–29) must be updated when §9–§12 are added.
- `results/matrix.md` version header should be at the top of the file, before the manifest/legend lines.
- REQUIREMENTS.md traceability table format: `| DISP-06 | Phase 10 |` rows — update checkboxes and add notes in the requirement text rows above.

</code_context>

<specifics>
## Specific Ideas

- The deferred posture label for DISP should be human-readable in conclusions: "DEFERRED — v1.3 milestone, tophu/SNAPHU tiled unwrapping with orbital baseline deramping." Not just a schema label.
- The SPURT interim caveat must be explicit: "SPURT native is the best available candidate but does not pass criteria on either cell. Bologna is the nearest (bias=3.44 mm/yr vs 3.0 criterion). Use only if production cannot wait for v1.3."
- PHASS retirement note should explain WHY structurally (SBAS inversion instability on externally deramped IFGs) so a future reader knows this isn't a threshold issue but a method incompatibility.
- §9 CALIBRATING-to-BINDING ADR in methodology doc must include: two-signal promotion rule (both coherence AND residual thresholds met, no named blocker), definition of named blocker, per-AOI unblock conditions for Mojave (Coso-Searles frame coverage resolution) and Iberian (EGMS L2a third number or alternative EU frame), and future promotion guidance.

</specifics>

<deferred>
## Deferred Ideas

- tophu/SNAPHU tiled unwrapping candidate evaluation → v1.3 milestone (named in unblock condition).
- 20×20 m validation fallback evaluation → v1.3, if tophu/SNAPHU does not pass.
- PHASS post-deramping with alternative SBAS solver → deprioritised; only relevant if tophu/SNAPHU also fails.
- DSWx-S2 EU recalibration / fit-set quality review → already deferred in REQUIREMENTS.md, out of Phase 12 scope.
- RTC-S1 EU fire-burst substitution → out of Phase 12 scope.
- Full REQUIREMENTS.md traceability table rebuild → D-13 defers this; update cells only.

</deferred>

---

*Phase: 12-disp-conclusions-release-readiness*
*Context gathered: 2026-05-06*
