---
phase: 04-disp-s1-comparison-adapter-honest-fail
plan: 05
subsystem: validation
tags: [insar, validation, conclusions, brief, docs, ramp-attribution, multilook-adr]

# Dependency graph
requires:
  - phase: 04-disp-s1-comparison-adapter-honest-fail
    provides: "Plan 04-04 eval-disp/metrics.json (DISPCellMetrics, SoCal cell_status=MIXED, coherence_source='phase3-cached', attributed_source='inconclusive') + eval-disp-egms/metrics.json (DISPCellMetrics, Bologna cell_status=MIXED, coherence_source='fresh', attributed_source='inconclusive')"
  - phase: 03-cslc-s1-self-consistency-eu-validation
    provides: "docs/validation_methodology.md sections 1 + 2 (cross-version phase impossibility + product-quality vs reference-agreement distinction); Phase 3 D-15 append-only by phase locking Phase 4 ownership of section 3 only"
provides:
  - "CONCLUSIONS_DISP_EU.md (renamed from CONCLUSIONS_DISP_EGMS.md via git mv; v1.0 narrative preserved + 4 v1.1 sub-sections)"
  - "CONCLUSIONS_DISP_N_AM.md (4 v1.1 sub-sections appended)"
  - ".planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md (new file; 4-candidates x 4-columns scoping brief)"
  - "docs/validation_methodology.md section 3 multilook ADR (5-part PITFALLS+FEATURES dialogue)"
  - "Phase 4 closure - all 5 plans complete; ready for verifier"
affects: [05-dist-s1-opera-v0.1-effis-eu, 06-dswx-s2-nam-eu-recalibration, 07-results-matrix-release-readiness, v1.2-disp-unwrapper-selection-followup]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "v1.0 narrative preservation as preamble pattern: append v1.1 sub-sections AFTER existing content with horizontal rule + v1.1 header; cite v1.0 numbers in continuity sub-sections per Phase 4 D-13"
    - "Multi-section CONCLUSIONS append pattern (Phase 2 RTC-EU emulation): 4 v1.1 sub-sections per cell (11 PQ / 12 RA / 13 Ramp Attribution / 14 Brief link); each sub-section has consistent table-driven structure"
    - "Append-only by phase docs/validation_methodology.md pattern (Phase 3 D-15 inherited): Phase 4 owns section 3 ONLY; sections 4 + 5 explicitly NOT created (deferred to Phases 5/6/7); section 2.6 cross-reference table updated to flip 'will append' to 'landed in section 3'"
    - "Scoping-brief artifact convention: .planning/milestones/v1.1-research/ canonical home for forward-looking research artifacts; one-page (~150 LOC) dense markdown; user reviews + greenlights before commit; cites fresh metrics.json numbers; not a plan, not an ADR"
    - "5-part PITFALLS+FEATURES dialogue ADR structure (Phase 4 D-03): (1) Problem statement (2) PITFALLS argument (3) FEATURES anti-feature argument (4) Decision (5) Constraint/locking; resolves the research-flagged tension by acknowledging both sides correct on their own terms then choosing posture not science"
    - "Atomic per-task git commits with conventional-commit prefix per task; git mv as its own commit (R100 rename) so history follows correctly via git log --follow"

key-files:
  created:
    - ".planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md (129 LOC)"
    - ".planning/phases/04-disp-s1-comparison-adapter-honest-fail/04-05-SUMMARY.md (this file)"
  modified:
    - "CONCLUSIONS_DISP_EU.md (renamed from CONCLUSIONS_DISP_EGMS.md; 304 -> 404 LOC; +100 v1.1 sections)"
    - "CONCLUSIONS_DISP_N_AM.md (258 -> 356 LOC; +98 v1.1 sections)"
    - "docs/validation_methodology.md (247 -> 365 LOC; +118 LOC: section 3 5-part dialogue + section 2.6 cross-ref table update)"

key-decisions:
  - "Plan 04-04 produced cell_status=MIXED on both cells (SoCal + Bologna); Bologna persistently_coherent_fraction=0.000 is a real signal not a BLOCKER per Plan 04-04 SUMMARY (residual + RA still computed; 1.13M paired samples). Standard 4-section append used; BLOCKER-shape Step 4 of plan Action NOT triggered."
  - "Bologna v1.0 numbers updated in continuity citation: v1.0 had r=0.3198 / bias=+3.3499 / RMSE=5.14 with n=933,184; Phase 4 form-c PS sampling produces n=1,126,687 (PS catalogue grew with explicit block_mean discipline). Continuity reflects both kernel and sample-count delta -- transparent in CONCLUSIONS prose."
  - "Section 13.5 human-review note documents the inconclusive-x-2 cross-cell pattern as suggestive of atmospheric long-wavelength curvature (SoCal r(mag,coh)=+0.15 near-zero; Bologna r(mag,coh)=-0.52 negatively-correlated). Brief author's recommendation to v1.2 roadmapper: activate diagnostic (c) ERA5 toggle FIRST (DISP-V2-02) before candidate evaluation per CONTEXT D-14 decision tree branch for inconclusive cells."
  - "Section 3 ADR posture-not-science framing per CONTEXT D-Specifics: PITFALLS P3.1 Gaussian-physics argument and FEATURES anti-feature block_mean argument are both correct on their own terms; the ADR resolves by picking the lower-bound r kernel for milestone-publish artefacts (anti-M1 target-creep) without claiming the kernel is physically more correct."
  - "Section 13 narrative explicitly distinguishes 'mean per-IFG ramp magnitude' from v1.0 1.0-rad soft-flag threshold to anchor the diagnostic context; SoCal mean=35.6 rad is an order-of-magnitude over the v1.0 flag threshold even after Phase 4's adapter-vs-bilinear delta is normalised."
  - "Section 2.6 cross-reference table updated in-place: row for DISP ramp-attribution flips from 'Phase 4 will append (PHASS N.Am./EU re-runs as authoritative evidence)' to 'Phase 4 landed the multilook-method ADR in section 3 (this doc); ramp-attribution per-cell evidence lives in CONCLUSIONS_DISP_*.md section 13'. Mirrors Phase 3 D-15 single-section-per-phase append discipline."

patterns-established:
  - "Pattern: v1.1 update preamble. Each cell's v1.0 narrative kept verbatim; v1.1 sub-sections added below a horizontal rule with explicit 'The sections below are Phase 4 additions. The v1.0 narrative above is preserved as the v1.0 baseline...' framing. Continuity citations call out the kernel-and-sample-count delta explicitly."
  - "Pattern: 4-candidate scoping brief 4-column table. Each candidate gets description / success criterion / compute tier (S/M/L) / dep delta. Per-candidate prose section adds risk + cross-reference to v1.0 evidence. Attribution-driven prioritisation section translates Phase 4 attribution labels into ordered candidate evaluation per CONTEXT D-14 decision tree."
  - "Pattern: Phase-owned methodology-doc section. Phase 4 owns section 3 ONLY; section 2.6 cross-reference table is updated in-place (NOT a new sub-section) to flag what landed vs what's still deferred. Future phases (5/6/7) own sections 4 + 5 + final ToC."
  - "Pattern: Atomic per-task commits. Task 1 = pure git mv (R100); Task 2 = both CONCLUSIONS appends in one commit (1 file pair); Task 3 = brief-only commit; Task 4 = methodology-doc-only commit. Each commit message documents WHAT changed AND WHY (not just file list)."

requirements-completed: [DISP-03, DISP-04, DISP-05]

# Metrics
duration: 9min
completed: 2026-04-25
---

# Phase 4 Plan 5: Docs + Brief Closure Summary

**4 documentation artifacts landed (CONCLUSIONS rename + 4 v1.1 sub-sections per file + DISP Unwrapper Selection scoping brief + docs/validation_methodology.md §3 multilook ADR), closing Phase 4 with the honest-FAIL signal preserved and the v1.2 follow-up milestone fully scoped via attribution-driven candidate prioritisation.**

## Performance

- **Duration:** ~9 min (2026-04-25T08:13:39Z to 2026-04-25T08:22:47Z)
- **Started:** 2026-04-25T08:13:39Z
- **Completed:** 2026-04-25T08:22:47Z
- **Tasks:** 4 (Task 1 git mv + Task 2 dual CONCLUSIONS append + Task 3 brief + Task 4 docs §3)
- **Files modified/created:** 1 created (brief), 3 modified (2 CONCLUSIONS, 1 methodology doc), 1 renamed (CONCLUSIONS_DISP_EGMS.md → EU.md)

## Accomplishments

### Task 1: git mv CONCLUSIONS_DISP_EGMS.md → CONCLUSIONS_DISP_EU.md

Pure rename via `git mv`. R100 (no content change) — verified via `git diff --staged --stat` showing rename marker. `git log --follow CONCLUSIONS_DISP_EU.md` traces back to commit `eff433b results: first eval runs` (the v1.0 EGMS file's original commit). Manifest reference (`results/matrix_manifest.yml` `disp:eu` `conclusions_doc: CONCLUSIONS_DISP_EU.md`) was already correct from Phase 1 D-08 + Plan 04-04 Task 3 — the rename aligns the filesystem with the manifest.

### Task 2: v1.1 sections appended to both CONCLUSIONS files

Both `CONCLUSIONS_DISP_N_AM.md` (258 → 356 LOC; +98) and `CONCLUSIONS_DISP_EU.md` (304 → 404 LOC; +100) gained four v1.1 sub-sections after the existing v1.0 narrative:

- **§11 Product Quality (CALIBRATING)**: 11.1 Coherence (5-row table: median_of_persistent + mean + median + p25/p75 + persistently_coherent_fraction with provenance flag inline) + 11.2 Residual mean velocity (1-row table). SoCal: coh_med_of_persistent=0.887 (phase3-cached, above 0.7 bar), residual=-0.030 mm/yr (PASS < 5). Bologna: coh_med_of_persistent=0.000 (fresh — real signal on Po-plain agricultural mask, not a bug), residual=+0.117 mm/yr (PASS < 5).
- **§12 Reference Agreement (BINDING)**: 4-row metric table (r / bias / RMSE / sample_count). SoCal r=0.0490 / bias=+23.6153 / RMSE=59.5567 / n=481,392 — FAIL on r > 0.92 and bias < 3 mm/yr. Bologna r=0.3358 / bias=+3.4608 / RMSE=5.2425 / n=1,126,687 — FAIL on both. v1.0 baseline cited inline ("for continuity, the v1.0 numbers using `Resampling.bilinear` were r=0.0365 / bias=+23.62 [...]"); kernel choice does NOT inflate the metric.
- **§13 Ramp Attribution**: 13.1 top-5-by-magnitude per-IFG table + 13.2 4-row aggregate table + 13.3 auto-attribute label (`inconclusive` on both cells) + 13.4 diagnostic deferrals (b POEORB swap no-op-on-current-stacks; c ERA5 toggle deferred per DISP-V2-02 + CONTEXT D-09) + 13.5 human review note flagging cross-cell atmospheric-curvature candidate.
- **§14 DISP Unwrapper Selection — Handoff**: link to `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md` per Phase 4 D-15 / D-16.

Phase 4 closure verdict footer per CONTEXT D-19: cell_status = MIXED = CALIBRATING product_quality + FAIL reference_agreement on both cells. The FAIL on reference-agreement is structurally correct — documents the PHASS unwrapper limitation, not a subsideo-layer bug. Block_mean preserves the honest FAIL signal.

### Task 3: DISP Unwrapper Selection scoping brief (4 candidates × 4 columns)

New file at `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md` (129 LOC; target 100-280). Single dense page per CONTEXT D-15.

**Context section** opens with v1.1 closure FAIL numbers from both metrics.json files: SoCal r=0.0490 / bias=+23.6153 (FAIL); Bologna r=0.3358 / bias=+3.4608 (FAIL). Cites v1.0 baseline numbers (r=0.0365 / r=0.3198) for continuity; kernel choice does NOT inflate the metric.

**Candidate table** (4 candidates × 4 columns: description / success criterion / compute tier / dep delta):

1. **PHASS + post-deramping** — S compute (numpy lstsq); criterion: r > 0.5 OR mean ramp magnitude < 1.0 rad
2. **SPURT native** — M compute (no new deps; one-line dolphin config); criterion: r > 0.7 + post-rerun mean magnitude < 5 rad + auto_attribute='inconclusive'
3. **tophu + SNAPHU multi-scale tiled** — L compute (~60 min/cell); criterion: r > 0.85 + PASS on at least one cell
4. **20×20 m fallback multilook** — L compute (~3 h/cell cold); criterion: PASS reference-agreement gate at 30 m

**Attribution-driven prioritisation** (CONTEXT D-14): Phase 4's `inconclusive × 2` outcome triggers the "diagnostics (b)+(c) BEFORE candidate evaluation" branch. Brief recommends activating diagnostic (c) ERA5 toggle FIRST in v1.2 milestone (cross-cell pattern: SoCal r(mag,coh)=+0.15 near-zero; Bologna r(mag,coh)=-0.52 negative — atmospheric long-wavelength curvature is a candidate); then SPURT (2) → PHASS+deramping (1) → tophu (3) → 20×20 m (4) per ordered escalation.

**Out of scope** explicitly excludes MintPy SBAS as 5th candidate per CONTEXT D-15 (4-candidate framing intentional). Open questions section poses 5 questions for v1.2 roadmapper covering ERA5 integration, candidate ordering after attribution, held-out test cell, production resolution decision, Bologna coherence-floor gate-stat flexibility.

### Task 4: docs/validation_methodology.md §3 multilook ADR

Appended §3 (247 → 365 LOC; +118 LOC, including +118 for §3 + 1-line edit to §2.6 cross-reference table).

**5-part PITFALLS+FEATURES dialogue** per CONTEXT D-03:

- **§3.1 Problem statement** — Native 5×10 m DISP must compare against OPERA DISP-S1 (30 m) and EGMS L2a PS (point cloud); multilook method changes reported r/bias materially (PITFALLS P3.1: r differs by > 0.03 across kernels). Native 5×10 m stays production default (DISP-05 + ROADMAP key decision); adapter is validation-only.
- **§3.2 PITFALLS P3.1 argument** — Gaussian σ=0.5×ref is physically consistent with OPERA's smoothing; kernel-matching is standard practice in remote-sensing validation when the reference is itself a multi-look product.
- **§3.3 FEATURES anti-feature argument** — block_mean is the kernel-flattery floor; conservative kernel matches OPERA's CSLC multilook + truncates high-frequencies most pessimistically; lower-bound r is the ship-it kernel for milestone artefacts.
- **§3.4 Decision: block_mean as eval-script default** — both arguments correct on their own terms; the choice is posture not science. Floor behaviour + OPERA parity + no M1 goalpost-moving. The eval-script constant `REFERENCE_MULTILOOK_METHOD: Literal["block_mean"] = "block_mean"` lives at module top in both run_eval_disp.py + run_eval_disp_egms.py.
- **§3.5 Constraint: kernel choice is comparison-method, NOT product-quality** — Native 5×10 m stays production default (DISP-05 explicit). Switching kernels post-measurement requires PR diff to constant + CONCLUSIONS sub-section documenting new kernel's r/bias. No env-var override / CLI flag. Kernel must be code-visible.

**§2.6 cross-section reference table** updated: DISP ramp-attribution row flipped from "Phase 4 will append (PHASS N.Am./EU re-runs as authoritative evidence)" to "Phase 4 landed the multilook-method ADR in §3 (this doc); ramp-attribution per-cell evidence lives in CONCLUSIONS_DISP_N_AM.md §13 + CONCLUSIONS_DISP_EU.md §13".

**Phase 4 owns §3 ONLY per Phase 3 D-15** — verified `grep -cE "^## 4\\. "` returns 0 and `grep -cE "^## 5\\. "` returns 0.

## Task Commits

Each task was committed atomically:

1. **Task 1: Git mv CONCLUSIONS_DISP_EGMS.md → CONCLUSIONS_DISP_EU.md** — `06232a6` (docs)
2. **Task 2: v1.1 sections appended to both DISP CONCLUSIONS files** — `67ec71f` (docs)
3. **Task 3: DISP Unwrapper Selection scoping brief** — `90daab0` (docs)
4. **Task 4: §3 multilook method ADR appended to validation methodology doc** — `343beff` (docs)

(Plan metadata commit follows this SUMMARY.md write per execute-plan.md.)

## Files Created/Modified

- `CONCLUSIONS_DISP_EU.md` (renamed from `CONCLUSIONS_DISP_EGMS.md` via `git mv`; 304 → 404 LOC; +100 LOC of v1.1 sub-sections after preserved v1.0 narrative). git log --follow traces to original v1.0 commit `eff433b`.
- `CONCLUSIONS_DISP_N_AM.md` (modified; 258 → 356 LOC; +98 LOC of v1.1 sub-sections after preserved v1.0 narrative).
- `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md` (created; 129 LOC). 4-candidate × 4-column scoping brief; Phase 4 D-15 / D-16 v1.1 closure handoff to DISP-V2-01 follow-up milestone.
- `docs/validation_methodology.md` (modified; 247 → 365 LOC; +118 LOC of §3 5-part dialogue + 1-line §2.6 cross-reference update). Phase 4 owns §3 only; §4 + §5 deferred to Phases 5/6/7.

## Decisions Made

- **Standard 4-section append (not BLOCKER replacement) on Bologna** — Plan 04-04 SUMMARY explicitly confirms cell_status=MIXED with the persistently_coherent_fraction=0.000 finding as a "real signal not a bug" (residual + RA still computed; 1.13M paired samples). Plan 04-05 Action Step 4 BLOCKER replacement applies to "fewer than 100 valid pixels" stable-mask shape, which Bologna doesn't have. Standard §11/§12/§13/§14 sections used; pcf=0.000 finding integrated into §11.1 prose with Po-plain agricultural-coherence context.
- **Bologna v1.0 sample count delta cited transparently** — v1.0 had n=933,184; Phase 4 form-c PS sampling produces n=1,126,687 (PS catalogue + explicit block_mean discipline grew the paired sample). Continuity citation in §12 reflects both kernel AND sample-count delta to avoid hidden-baseline drift.
- **Cross-cell atmospheric-curvature pattern flagged in human review notes** — both cells' inconclusive labels combined with their specific coh-correlation signs (SoCal r(mag,coh)=+0.15 near-zero; Bologna r(mag,coh)=-0.52 negative) suggest atmospheric long-wavelength curvature. §13.5 human review notes name this as the next diagnostic in line; brief's attribution-driven prioritisation section recommends ERA5 toggle (DISP-V2-02) FIRST in v1.2 milestone before candidate evaluation per CONTEXT D-14 decision tree.
- **§3 framed as posture-not-science** — neither PITFALLS Gaussian-physics nor FEATURES anti-feature argument is wrong on its own terms. The ADR resolves by picking the lower-bound r kernel (block_mean) for milestone-publish artefacts, explicitly acknowledging the kernel-flattery attack-surface argument wins for shipped numbers without claiming Gaussian is physically incorrect.
- **§2.6 cross-reference table updated in-place** — instead of adding a new sub-section, the existing table row for DISP ramp-attribution is flipped from "Phase 4 will append" to "Phase 4 landed the multilook-method ADR in §3 (this doc)". Section numbering remains 2.6; mirrors Phase 3 D-15 single-section-per-phase append discipline.

## Deviations from Plan

None. Plan executed exactly as written. The plan's Action Step 4 BLOCKER-replacement branch was inspected and correctly identified as not-applicable (Bologna persistently_coherent_fraction=0.000 is a measurement, not the BLOCKER stable-mask <100-pixel shape).

## Issues Encountered

- **READ-BEFORE-EDIT hook reminders** fired three times during the session (CONCLUSIONS_DISP_N_AM.md, CONCLUSIONS_DISP_EU.md, docs/validation_methodology.md). Each fired AFTER the Edit tool reported success ("The file has been updated successfully"). The files had been read at session start as part of the initial context load; the hook appears to be a precaution that triggers regardless of prior reads, particularly for the renamed CONCLUSIONS_DISP_EU.md which had been read under its old name CONCLUSIONS_DISP_EGMS.md before the git mv. Verified via `wc -l` + `grep` that all edits applied correctly. No content lost; no corruption.
- **Bash quote escaping** — one verification check (`grep -cE '^## 3\\. DISP'`) returned 0 due to bash double-escaping of the period; re-run with single-escaped pattern returned 1. The §3 header is correctly present at line 249.

## TDD Gate Compliance

Plan 04-05 is `type: execute` (not `type: tdd`); no RED/GREEN/REFACTOR commit sequence required. Documentation-only plan — verification is via grep checks on artifact contents, all of which passed.

## User Setup Required

**Brief review (per CONTEXT D-16):** the brief is committed by Claude as research output; the user is expected to review and (if needed) request follow-up edits. Per the auto-mode discipline active during this session (`workflow.auto_advance: true`), the brief was committed without an interactive checkpoint; user can reopen + edit if review surfaces revisions.

## Next Phase Readiness

Plan 04-05 (Wave 4) complete. **Phase 4 closure complete: all 5 plans done.**

- All Phase 4 must_haves.truths verified:
  - ✓ git mv preserved history (git log --follow shows commits 06232a6 + 67ec71f + eff433b)
  - ✓ Both CONCLUSIONS files have 4 v1.1 sub-sections (`grep -cE "^## 1[1-4]\."` returns 4 on both)
  - ✓ Brief exists with 4-candidates × 4-columns at canonical v1.1-research path
  - ✓ docs/validation_methodology.md §3 5-part dialogue appended; §4 + §5 NOT created (Phase 3 D-15 append-only)
  - ✓ "Native 5×10 m stays production default" string explicit in §3.5 per DISP-05
  - ✓ Brief cites FAIL numbers + ramp aggregate + attributed_source from Plan 04-04 metrics.json files
  - ✓ v1.0 baseline numbers preserved as continuity preamble in CONCLUSIONS files
  - ✓ No placeholder strings (`<NAM_*>` / `<EU_*>`) remain in any artifact
- Phase 4 honest-FAIL signal preserved + scoped: SoCal r=0.0490 (FAIL > 0.92), Bologna r=0.3358 (FAIL > 0.92), both attributed_source=`inconclusive`, brief recommends ERA5 toggle (DISP-V2-02) + SPURT (candidate 2) prioritisation for v1.2 milestone.
- ROADMAP Phase 4 v1.1 row ready to advance from "4/5 In progress" to "5/5 Complete" status.
- Verifier ready (per `.planning/config.json` `workflow.verifier: true`).

No blockers. No follow-up todos for v1.1 closure. The DISP-V2-01 follow-up milestone roadmapper consumes the brief as its primary input.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| n/a | n/a | No new security-relevant surface introduced. Documentation artifacts only; all numerical values cited are already public (criteria.py thresholds, Plan 04-04 metrics.json which is committed to gitignored eval-*/ dirs but cited verbatim with full provenance). No PII; no credentials; brief audience is research-handoff-internal. |

## Self-Check: PASSED

Verifications performed before writing this section:

- **All artifact files exist:**
  - `CONCLUSIONS_DISP_EU.md` — FOUND (404 LOC; ≥ 400 target)
  - `CONCLUSIONS_DISP_N_AM.md` — FOUND (356 LOC; ≥ 350 target)
  - `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md` — FOUND (129 LOC; in [100, 280] target)
  - `docs/validation_methodology.md` — FOUND (365 LOC; ≥ 320 target)
- **CONCLUSIONS_DISP_EGMS.md does NOT exist** — confirmed via `test ! -f`
- **All 4 commits exist in git log:**
  - `06232a6` (Task 1 git mv) — FOUND
  - `67ec71f` (Task 2 dual CONCLUSIONS append) — FOUND
  - `90daab0` (Task 3 brief) — FOUND
  - `343beff` (Task 4 §3) — FOUND
- **git log --follow CONCLUSIONS_DISP_EU.md** returns ≥ 2 commits including the v1.0 origin (`eff433b results: first eval runs`) — verified history preservation.
- **All must_haves.truths from plan frontmatter:**
  - "git mv preserves history" — confirmed via `git log --follow`
  - "Both CONCLUSIONS files have v1.1 sub-sections (PQ + RA + Ramp + Brief link)" — `grep -cE "^## 1[1-4]\."` returns 4 on both files
  - "Brief exists with 4 candidates × 4 columns" — table found at line 51 with all 4 column headers (`Success criterion`, `Compute tier`, `Dep delta`)
  - "§3 5-part dialogue per CONTEXT D-03" — `grep -cE "^### 3\.[1-5]"` returns 5 (3.1 + 3.2 + 3.3 + 3.4 + 3.5 all present)
  - "Native 5×10 m stays production default in §3.5 per DISP-05" — `grep -c "Native 5.10 m stays"` returns 1
  - "Brief cites FRESH numbers from metrics.json" — verified by spot-check of brief Context section against metrics.json values (r=0.0490, bias=+23.6153, attributed_source='inconclusive' on SoCal; r=0.3358, bias=+3.4608, attributed_source='inconclusive' on Bologna)
  - "v1.0 numbers (Resampling.bilinear) preserved as continuity preamble" — `grep -c "Resampling.bilinear"` returns 2 on N_AM, 2 on EU
  - "No §4 / §5 added" — `grep -cE "^## 4\."` and `^## 5\.` both return 0
- **No placeholders remain anywhere:** `grep -rE '<(NAM|EU)_[A-Z_]+>'` on all 3 artifacts returns no output.

---
*Phase: 04-disp-s1-comparison-adapter-honest-fail*
*Completed: 2026-04-25*
