# Phase 10: DISP ERA5 & Ramp Diagnostics - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-03
**Phase:** 10-disp-era5-ramp-diagnostics
**Areas discussed:** ERA5 rerun posture, Attribution verdict wording, Provenance depth, Success threshold for improvement

---

## ERA5 Rerun Posture

| Question | Options Presented | Selected |
|----------|-------------------|----------|
| Should Phase 10 treat ERA5 as a strict paired experiment? | Paired on/off for both cells; Warm baseline + ERA5-on; ERA5-on best effort | Warm baseline + ERA5-on |
| If ERA5 cannot run cleanly, what should count as an acceptable blocker? | Tooling blocker; Credential/data blocker; No blocker until exhausted | Credential/data blocker |
| What should Phase 10 be allowed to conclude? | Clear label only; Narrowed ambiguity accepted; Decision-driving only | Narrowed ambiguity accepted |
| If ERA5 improves one cell but not the other, how should conclusions treat the cells? | Cell-specific verdicts; Milestone-level verdict; Primary-cell priority | Cell-specific verdicts |
| How much orbit/DEM/slope/terrain evidence should Phase 10 collect? | Minimal provenance; Diagnostic provenance; Deep terrain investigation | Diagnostic provenance |
| Where should diagnostic provenance live? | Sidecars only; Sidecars + conclusions tables; Separate provenance report | Sidecars + conclusions tables |
| What ERA5 result should be strong enough to change Phase 11 candidate ordering? | Any improvement; Meaningful diagnostic jump; Pass-bar only | Meaningful diagnostic jump |
| If ERA5 helps modestly but not enough to reorder candidates, how should Phase 10 frame it? | Keep Phase 11 order unchanged; Add ERA5 as required baseline; Run both baselines in Phase 11 | Add ERA5 as required baseline |

**Notes:** The v1.1 baseline remains authoritative. Phase 10 should focus on diagnostic deltas and not burn time re-proving the existing no-ERA5 failures.

---

## Attribution Verdict Wording

| Question | Options Presented | Selected |
|----------|-------------------|----------|
| If Phase 10 eliminates one cause but still leaves multiple plausible explanations, how should the conclusion label it? | inconclusive_narrowed; mixed; Plain inconclusive plus notes | inconclusive_narrowed |
| Should inconclusive_narrowed be schema-level or represented with existing schema plus detail fields? | Schema value; Detail field; Conclusions only | Detail field |
| What causes should Phase 10 explicitly distinguish? | Core four; Core four + provenance/cache; Open taxonomy | Core four + provenance/cache |
| When should conclusions say a cause is eliminated? | Strict evidence only; Reasonable evidence; Planner discretion | Strict evidence only |
| What should happen if ERA5-on worsens the metrics? | Treat as anti-evidence for tropospheric cause; Treat as inconclusive; Treat as blocker | Treat as anti-evidence for tropospheric cause |
| How should conflicting cell results be represented? | Separate cause fields per cell; Shared cause fields plus per-cell notes; Worst-case cause set | Separate cause fields per cell |

**Notes:** Keep `attributed_source="inconclusive"` for compatibility and add structured per-cell cause fields.

---

## Provenance Depth

| Question | Options Presented | Selected |
|----------|-------------------|----------|
| For terrain-vs-ramp correlation, what level of evidence should Phase 10 require? | Simple correlation; Multi-signal terrain summary; Visual diagnostics too | Multi-signal terrain summary |
| For orbit provenance, what should be required? | Orbit file inventory; Coverage sanity; Orbit diagnostic rerun | Coverage sanity |
| For DEM provenance, what should Phase 10 record? | DEM source only; DEM source + terrain stats; DEM alternate check | DEM source + terrain stats |
| For cache/input provenance, what should be mandatory? | Hashes only; Hashes + cache mode; Full lineage table | Hashes + cache mode |
| Should Phase 10 require provenance diagnostics to pass schema validation before conclusions are updated? | Yes, hard gate; Soft gate; Only for final matrix | Yes, hard gate |

**Notes:** Sidecars are canonical; conclusions render readable provenance tables.

---

## Success Threshold for Improvement

| Question | Options Presented | Selected |
|----------|-------------------|----------|
| Which improvement should count as meaningful? | Any one strong signal; Two-signal confirmation; Reference-agreement driven | Two-signal confirmation |
| Should the two-signal rule apply per cell or across the milestone? | Per cell; Across both cells; Hybrid | Hybrid |
| What should happen if only one cell meets the two-signal improvement rule? | Cell-specific Phase 11 branch; Keep global order, annotate exception; Run an extra diagnostic | Keep global order, annotate exception |
| Should ramp magnitude reduction alone ever trigger ERA5-on as required baseline for Phase 11? | No; Yes, if large; Only if both cells show it | No |
| If ERA5 does not meet the two-signal rule, what should Phase 11 start with? | Brief order unchanged; PHASS deramping first; Planner decides | Brief order unchanged |

**Notes:** Global Phase 11 ordering changes only with cross-cell support. Otherwise use the v1.1 brief order.

---

## the agent's Discretion

- Exact schema field names for diagnostic detail fields.
- Exact numerical thresholds for "material" ramp reduction or meaningful r/bias/RMSE movement, provided the plan defines them before reading results.
- Exact implementation split across eval scripts, schema, helper modules, and conclusions docs.

## Deferred Ideas

None.
