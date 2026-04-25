---
phase: 05-dist-s1-opera-v0-1-effis-eu
plan: "01"
subsystem: planning
tags: [roadmap, requirements, defer, scope-amendment, research-resolution-log]
dependency_graph:
  requires: []
  provides:
    - "ROADMAP.md Phase 5 scope amendment block with deferral rationale + D-18 + D-24 amendments"
    - "REQUIREMENTS.md DIST-01/02/03 status=Deferred to v1.2 + DIST-V2-05 entry"
    - "05-RESEARCH.md Resolution Log (Risks A-M + Q1-Q5)"
  affects:
    - ".planning/ROADMAP.md"
    - ".planning/REQUIREMENTS.md"
    - ".planning/phases/05-dist-s1-opera-v0-1-effis-eu/05-RESEARCH.md"
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - ".planning/ROADMAP.md"
    - ".planning/REQUIREMENTS.md"
    - ".planning/phases/05-dist-s1-opera-v0-1-effis-eu/05-RESEARCH.md"
decisions:
  - "DIST-01/02/03 deferred to v1.2: OPERA DIST-S1 v0.1 has no canonical CloudFront URL (RESEARCH Probe 1) and the operational OPERA_L3_DIST-ALERT-S1_V1 collection is empty in CMR as of 2026-04-25 (RESEARCH Probe 6)"
  - "EMSR649 corrected to EMSR686 for Evros 2023 wildfire activation (RESEARCH Probe 8 — EMSR649 was an Italian flood)"
  - "Romania 2022 clear-cuts substituted with Spain Sierra de la Culebra June 2022 — EFFIS is fire-only and has no coverage of logging clear-cuts (PITFALLS P4.5; RESEARCH Probe 4 ADR)"
  - "D-18 amendment: EFFIS WFS dispatch via effis.py direct owslib call (not harness.download_reference_with_retry whose Path contract is incompatible with in-memory WFS streams)"
  - "D-24 amendment: matrix_writer DIST insert AFTER disp:* only — the pre-cslc/pre-dswx constraint relaxed to an unverified contemporary observation"
metrics:
  duration_minutes: 8
  completed_date: "2026-04-25"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 3
---

# Phase 05 Plan 01: ROADMAP + REQUIREMENTS Scope Amendment Summary

**One-liner:** Deferred DIST-01/02/03 to v1.2 (no canonical CloudFront URL + empty CMR collection), corrected EMSR686 + Spain Culebra substitution, and appended D-18/D-24 amendments + 18-row Resolution Log to Planning artifacts.

## What Was Done

### Task 1: ROADMAP.md Phase 5 amendment (commit f7006fd)

**Lines modified:** Phase 5 block (~lines 159-196 post-edit)

Changes applied:
1. **Scope amendment block** inserted after `**Goal**:` and before `**Depends on**:` with 8 bullet points covering:
   - DIST-01 deferral rationale citing RESEARCH Probe 1 (no canonical CloudFront URL)
   - DIST-02/03 deferral rationale citing RESEARCH Probe 6 (empty CMR collection as of 2026-04-25)
   - EMSR correction: EMSR649 → EMSR686
   - Romania → Spain Sierra de la Culebra substitution with EFFIS fire-only coverage rationale
   - D-18 amendment (EFFIS direct owslib dispatch; harness owns RETRY_POLICY declaration only)
   - D-24 amendment (DIST branches insert AFTER disp:* only; pre-cslc lock relaxed)

2. **Success criteria status tags appended:**
   - Criteria 1, 2, 3: `[deferred to v1.2]`
   - Criterion 4: `[Phase 5 deliverable]`
   - Criterion 5: `[Phase 5 deliverable]` + inline EMSR686 + Spain Culebra corrections
   - Criterion 6: `[Phase 5 deliverable]`

3. **Plans block expanded** with D-18/D-24 amendment callouts in plan descriptions and updated requirements coverage audit (DIST-01/02/03 now covered by plans 01 and 06 for the deferral scaffolding).

4. **Progress table** was already correct at `0/9 | Planned` — no change needed.

### Task 2: REQUIREMENTS.md DIST-01/02/03 deferral (commit 9184610)

**Lines modified:**
- DIST-01/02/03 v1.1 requirement bullets (lines ~64-66 post-edit): prepended `[deferred to v1.2 — ...]` tag with evidence-anchored rationale
- Traceability table rows DIST-01/02/03 (lines ~193-195): `Pending` → `Deferred to v1.2`
- DIST-V2-05 added after DIST-V2-04 (line ~120): full text with D-16 archival hook callout
- Per-phase counts Phase 5 line (line ~224): appended deferral parenthetical
- Bottom metadata line (line ~230): appended `; 2026-04-25 DIST-01/02/03 marked Deferred to v1.2 per Phase 5 scope amendment (RESEARCH Probes 1 + 6)`

**Unchanged:** DIST-04/05/06/07 remain `Pending`. Total v1.1 requirement count stays `49 total / 49 mapped / 0 unmapped`.

### Task 3: 05-RESEARCH.md Resolution Log (commit a9a3ba0)

**Appended** a `## Resolution Log` section (51 lines) immediately before `## RESEARCH COMPLETE` marker. Zero deletions to existing prose (pure append verified via `git diff | grep "^-"`).

The Resolution Log contains:
- **13 Risk rows (A-M)** with disposition column (resolved / accepted-as-narrative / accepted-as-blocker / deferred-to-v1.2 / mitigated-via-amendment) and "Resolved by" column citing Plan 05-0X identifiers or amendment references
- **5 Question rows (Q1-Q5)** with same disposition vocabulary

## Evidence Anchors Cited

| Probe | Finding | Cited in |
|-------|---------|----------|
| RESEARCH Probe 1 | OPERA DIST-S1 v0.1 has no canonical CloudFront URL; OPERA-ADT notebook Cell 5 regenerates sample locally via `run_dist_s1_workflow(...)` | ROADMAP scope amendment bullet 1; REQUIREMENTS.md DIST-01 tag; Resolution Log Risk J |
| RESEARCH Probe 4 | Spain Sierra de la Culebra June 2022 ADR: fire-only EFFIS coverage + S1 pass coverage confirmed | ROADMAP scope amendment bullet 5; Resolution Log Risk L |
| RESEARCH Probe 6 | `earthaccess.search_data(short_name='OPERA_L3_DIST-ALERT-S1_V1', ...)` returns empty result set as of 2026-04-25 | ROADMAP scope amendment bullet 2; REQUIREMENTS.md DIST-02/03 tags; Resolution Log Q2 |
| RESEARCH Probe 8 | EMSR686 (Evros 2023 wildfire); EMSR649 was an Italian flood | ROADMAP scope amendment bullet 4; criterion 5 inline correction |

## Unchanged Status

- **DIST-04** (CMR auto-supersede probe): `Pending` — ships in Phase 5
- **DIST-05** (EFFIS WFS cross-validation): `Pending` — ships in Phase 5
- **DIST-06** (EU 3-event aggregate): `Pending` — ships in Phase 5
- **DIST-07** (chained prior_dist_s1_product retry): `Pending` — ships in Phase 5
- Total v1.1 requirement count: `49 total` (deferral is a status, not a removal)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — this plan is documentation-only (no code stubs).

## Threat Flags

None — changes are confined to `.planning/` documentation files with no network endpoints, auth paths, file access patterns, or schema changes at trust boundaries.

## Self-Check: PASSED

- `.planning/ROADMAP.md` modified — file exists and contains scope amendment block with both RESEARCH Probe 1 and RESEARCH Probe 6 citations
- `.planning/REQUIREMENTS.md` modified — DIST-01/02/03 traceability rows show `Deferred to v1.2`; DIST-V2-05 present
- `.planning/phases/05-dist-s1-opera-v0-1-effis-eu/05-RESEARCH.md` modified — `## Resolution Log` section present with 13 Risk rows + 5 Q rows; `## RESEARCH COMPLETE` still at end

Commits:
- f7006fd: docs(05-01): amend ROADMAP.md Phase 5 with deferral markers + D-18/D-24 amendments + EMSR686 + Spain Culebra
- 9184610: docs(05-01): amend REQUIREMENTS.md DIST-01/02/03 to Deferred to v1.2 + add DIST-V2-05
- a9a3ba0: docs(05-01): append Resolution Log to 05-RESEARCH.md (Risks A-M + Q1-Q5 dispositions)
