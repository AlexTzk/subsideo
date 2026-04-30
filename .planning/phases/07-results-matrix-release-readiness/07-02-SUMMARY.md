---
phase: 07-results-matrix-release-readiness
plan: 02
subsystem: validation
tags: [methodology, documentation, validation_methodology]

requires:
  - phase: 03-cslc-s1-self-consistency-eu-validation
    provides: §1 cross-version phase impossibility (append-only baseline)
  - phase: 04-disp-s1-comparison-adapter-honest-fail
    provides: §3 multilook ADR
  - phase: 05-dist-s1-opera-v0-1-effis-eu
    provides: §4 DIST methodology
  - phase: 06-dswx-s2-n-am-eu-recalibration
    provides: §5 DSWE F1 ceiling

provides:
  - docs/validation_methodology.md: TOC + §6 + §7 + fixed anchors + corrected §2.6 forward-refs

affects: [release, verification]

tech-stack:
  added: []
  patterns:
    - Methodology doc sections: ## heading + <a name="anchor"> + bold TL;DR + numbered sub-sections

key-files:
  created: []
  modified:
    - docs/validation_methodology.md

key-decisions:
  - "TOC inserted before §1 (navigational exception to append-only policy)"
  - "§2.6 stale forward-refs updated: 'Phase 4 will document' → '§6 documents'; 'Phase 5 will append' → '§7 documents'"
  - "pq-vs-ra and dist-methodology anchors added to §2 and §4"

patterns-established:
  - "Each methodology section: ## N. Title + <a name='anchor'> + TL;DR + structural-argument + policy-statement + code-pointer + diagnostic-evidence"

requirements-completed: [REL-03]

duration: completed prior session (commit 4e12c0c)
completed: 2026-04-28
---

# Plan 07-02: validation_methodology.md — TOC + §6 + §7 + stale ref fixes

**docs/validation_methodology.md completed with TOC (7 sections), §6 OPERA UTC-hour frame selection, §7 cross-sensor precision-first framing, two missing anchors added, two stale §2.6 forward-references corrected.**

## Performance

- **Duration:** prior session
- **Completed:** 2026-04-28
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added `<a name="pq-vs-ra">` to §2 and `<a name="dist-methodology">` to §4 (were missing per CONTEXT D-04)
- Fixed stale §2.6: "Phase 4 harness-first discipline will document" → "§6 documents"; "Phase 5 will append" → "§7 documents"
- Prepended 7-entry TOC with anchor links for all sections
- Appended §6 (4 sub-sections: structural argument on UTC-hour + ascending/descending disambiguation, policy statement, `select_opera_frame_by_utc_hour()` code pointer, diagnostic evidence from RTC EU alpine burst T168-356151-IW1)
- Appended §7 (4 sub-sections: temporal class-definition mismatch, precision-first policy, `effis.py` dual-rasterise code pointer, §4.3 cross-reference)
- Final doc: 808 lines, 8 `##` headers (TOC + §1–§7), 7 `<a name=` anchors

## Task Commits

1. **Task 1: Anchors + stale forward-ref fixes** — `4e12c0c` (docs(07-02), first portion)
2. **Task 2: TOC + §6 + §7 append** — `4e12c0c` (docs(07-02), same commit)

## Files Created/Modified

- `docs/validation_methodology.md` — 706 → 808 lines; TOC prepended; §6+§7 appended; anchors added; §2.6 stale text removed

## Decisions Made

- TOC insertion before §1 is the one approved exception to append-only policy (navigational element)
- §6 and §7 follow the same structural voice as §1–§5 (structural argument → policy statement → code pointer → diagnostic evidence)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- REL-03 closed. Methodology doc covers all four findings + TOC + all 7 anchors.

---
*Phase: 07-results-matrix-release-readiness*
*Completed: 2026-04-28*
