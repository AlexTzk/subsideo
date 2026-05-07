# Phase 12: DISP Conclusions & Release Readiness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-06
**Phase:** 12-disp-conclusions-release-readiness
**Areas discussed:** DISP posture, Methodology doc, Requirements closure, Matrix & conclusions

---

## DISP Production Posture

| Option | Description | Selected |
|--------|-------------|----------|
| Defer — named blocker | Close v1.2 as deferred; SPURT orbit-class ramp is named blocker; tophu/SNAPHU is unblock path; no new eval runs in Phase 12 | ✓ |
| Run tophu/SNAPHU in Ph.12 | Phase 12 adds a tophu/SNAPHU candidate run before writing conclusions | |
| 20×20 m fallback | Declare 5×10 m validation as the blocker; adopt 20×20 m as comparison posture | |

**User's choice:** Defer — named blocker
**Notes:** Phase 12 is conclusions/documentation only. tophu/SNAPHU explicitly deferred to v1.3.

---

## Unblock Condition Format

| Option | Description | Selected |
|--------|-------------|----------|
| Metric target + milestone name | Concrete: 'r > 0.92 AND bias < 3 mm/yr on both cells in tophu/SNAPHU run; v1.3 milestone' | ✓ |
| Qualitative next-step | 'Evaluate tophu/SNAPHU in v1.3' — simpler, less auditable | |

**User's choice:** Metric target + milestone name
**Notes:** Dated unblock condition gives Phase 12 a clean, audit-ready closer.

---

## Interim Candidate Recommendation

| Option | Description | Selected |
|--------|-------------|----------|
| No interim recommendation | DISP remains CALIBRATING; no production use until unblock | |
| Name SPURT as interim candidate | Flag SPURT native as 'best available' with explicit caveat that neither cell passes criteria | ✓ |

**User's choice:** Name SPURT as interim candidate
**Notes:** Bologna SPURT nearest to threshold (bias=3.44 mm/yr vs 3.0 criterion). Caveat must be explicit.

---

## PHASS Post-Deramping Retirement

| Option | Description | Selected |
|--------|-------------|----------|
| Retire PHASS post-deramping | Removed from candidate ladder; tophu/SNAPHU replaces it in v1.3 brief | ✓ |
| Keep as deprioritised | Stays in brief as 'deprioritised — sanity-flagged' for optionality | |

**User's choice:** Retire (confirmed after Claude provided implication analysis)
**Notes:** User asked for implications before deciding. Claude explained: cross-cell consistency of deformation sanity flag (both cells, large magnitude) is a structural signal not a parameter-tuning issue. User confirmed retire. Structural reason (SBAS inversion instability on externally deramped IFGs) must be documented in conclusions.

---

## Methodology Doc Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated sections §9–§12 | Four new top-level sections parallel to existing structure | ✓ |
| Append to existing sections | Content appended within §2 (product-quality) and §8 (ERA5) | |

**User's choice:** Dedicated sections §9–§12

---

## CALIBRATING-to-BINDING Section Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Full ADR-style section | Problem statement, promotion rule, named-blocker definition, per-AOI unblock conditions, future guidance | ✓ |
| Compact paragraph | One paragraph referencing criteria.py thresholds | |

**User's choice:** Full ADR-style section
**Notes:** This information exists nowhere else; must be standalone.

---

## EGMS L2a Methodology Section Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Methodology + Phase 9 blocker pattern | How EGMS L2a is used as EU reference AND the named-blocker pattern from Phase 9 | ✓ |
| EGMS reference methodology only | Only the comparison discipline, no CSLC binding context | |

**User's choice:** Methodology + Phase 9 blocker pattern

---

## CSLC-07 Traceability Treatment

| Option | Description | Selected |
|--------|-------------|----------|
| Mark partial — named blocker evidence | Keep [ ] but add note: 'Partial — candidate BINDING, named blockers defer promotion to v1.3' | ✓ |
| Mark satisfied — Phase 9 met intent | Mark [x] since CSLC is no longer 'merely CALIBRATING' | |
| Leave unchecked, add note | Same as partial but without the 'Partial' label | |

**User's choice:** Mark partial — named blocker evidence

---

## DISP-06 (ERA5 Toggle) Status

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — mark satisfied | Phase 10 delivered capability and results; requirement doesn't mandate improvement | ✓ |
| No — leave unchecked | ERA5 didn't improve reference agreement; downstream motivation unmet | |

**User's choice:** Yes — mark satisfied

---

## REQUIREMENTS.md Rebuild Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Update status cells only | Mark new requirements, add CSLC-07 note, no structural rebuild | ✓ |
| Rebuild full traceability table | Regenerate entire requirement→phase mapping from scratch | |

**User's choice:** Update status cells only

---

## Matrix Version Header

| Option | Description | Selected |
|--------|-------------|----------|
| v1.2 header + update DISP rows | Add version block at top; update DISP row posture | ✓ |
| Update rows only | Leave 'v1.1 Results Matrix' header; update DISP cells only | |

**User's choice:** v1.2 header + update DISP rows

---

## DISP Matrix Row Format

| Option | Description | Selected |
|--------|-------------|----------|
| Named blocker + candidate summary | Posture first: 'DEFERRED — spurt:FAIL / deramp:retired / unblock=tophu-SNAPHU...' | ✓ |
| Keep Phase 11 candidate detail | Keep cand= hint format; add posture=deferred field | |

**User's choice:** Named blocker + candidate summary (posture-first)

---

## Conclusions File Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Append to each conclusions file | '## Phase 12 Production Posture' section in CONCLUSIONS_DISP_N_AM.md and CONCLUSIONS_DISP_EU.md | ✓ |
| Standalone release doc | Single DISP_V1.2_RELEASE_POSTURE.md; conclusions unchanged | |

**User's choice:** Append to each conclusions file (consistent with Phase 10–11 append pattern)

---

## Claude's Discretion

- Exact wording of PHASS retirement rationale in conclusions (structural argument must be present)
- Exact prose for §9–§12 methodology sections (structure and content requirements locked; language is agent discretion)
- Whether to add a cross-reference footnote in existing §8 linking forward to new §11
- Exact matrix row formatting within the posture-first constraint (D-15)
- ToC update mechanics in docs/validation_methodology.md

## Deferred Ideas

- tophu/SNAPHU candidate evaluation → v1.3 milestone
- 20×20 m fallback evaluation → v1.3 (if tophu/SNAPHU fails)
- PHASS post-deramping with alternative SBAS solver → deprioritised
- DSWx-S2 EU recalibration → already deferred in REQUIREMENTS.md
- RTC-S1 EU fire-burst substitution → out of scope
- Full REQUIREMENTS.md traceability rebuild → D-13 defers to cell updates only
