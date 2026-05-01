---
phase: 09-cslc-egms-third-number-binding-reruns
plan: 03
subsystem: validation
tags: [cslc, mojave, opera, validation, candidate-binding]
requires:
  - phase: 09-cslc-egms-third-number-binding-reruns
    provides: Plan 09-01 candidate BINDING sidecar schema and blocker evidence fields
provides:
  - Mojave OPERA frame-search evidence capture for amplitude sanity
  - Explicit Mojave OPERA frame-unavailable candidate BINDING blocker disposition
  - Source-level tests for bounded Mojave fallback evidence policy
affects: [phase-09-cslc-reruns, cslc-validation-sidecars, mojave-amplitude-sanity]
tech-stack:
  added: []
  patterns:
    - Reuse candidate_binding sidecars for availability blockers while preserving CALIBRATING AOI status
    - Keep Mojave fallback expansion bounded to acquisition-backed Phase 8 chain entries
key-files:
  created:
    - .planning/phases/09-cslc-egms-third-number-binding-reruns/09-03-SUMMARY.md
  modified:
    - run_eval_cslc_selfconsist_nam.py
    - tests/unit/test_run_eval_cslc_selfconsist_nam.py
key-decisions:
  - "Mojave fallback leaves now run amplitude sanity, but missing OPERA HDF5 references become candidate BINDING BLOCKER evidence rather than changing structural CALIBRATING fallback success."
  - "OPERA frame-search evidence is captured from cached references as well as first-epoch search/download paths so warm reruns still write audit evidence."
patterns-established:
  - "Per-AOI OPERA reference availability evidence is stored in AOIResult.opera_frame_search and mirrored into CSLCBlockerEvidence.evidence on unavailable Mojave references."
requirements-completed: [CSLC-11, VAL-01, VAL-03]
duration: ~4min
completed: 2026-05-01
---

# Phase 09 Plan 03: Mojave Amplitude Evidence Summary

**Mojave/Coso-Searles, Pahranagat, and Amargosa now attempt OPERA amplitude sanity and record schema-valid frame-search evidence or a named unavailable blocker.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-01T03:29:31Z
- **Completed:** 2026-05-01T03:32:39Z
- **Tasks:** 2
- **Files modified:** 2 code/test files plus this summary

## Accomplishments

- Enabled `run_amplitude_sanity=True` only on the three accepted Mojave fallback leaves: Coso-Searles, Pahranagat, and Amargosa.
- Added OPERA first-epoch reference evidence with `opera_frame_search`, including burst token, granule pattern, HDF5 candidate count, and selected reference path.
- Converted missing Mojave OPERA reference HDF5 into `reason_code="mojave_opera_frame_unavailable"` candidate BINDING blocker evidence without broadening the AOI search.
- Added source-level tests pinning bounded fallback order, OPERA evidence fields, and no Hualapai runnable-chain expansion.

## Task Commits

1. **Task 1: Enable bounded Mojave amplitude-sanity evidence capture** - `0392495` (`feat`)
2. **Task 2: Add tests for Mojave bounded fallback evidence** - `ec7abdf` (`test`)

## Files Created/Modified

- `run_eval_cslc_selfconsist_nam.py` - Enables bounded Mojave amplitude sanity, records OPERA frame-search evidence, and emits unavailable blocker evidence when needed.
- `tests/unit/test_run_eval_cslc_selfconsist_nam.py` - Pins fallback order, evidence fields, reason code, and bounded runnable chain.
- `.planning/phases/09-cslc-egms-third-number-binding-reruns/09-03-SUMMARY.md` - Execution summary.

## Decisions Made

- Kept AOI `status="CALIBRATING"` for successful Mojave self-consistency rows so fallback-chain structure remains unchanged; amplitude availability affects the separate `candidate_binding` verdict.
- Reused the Plan 09-01 sidecar schema instead of adding new schema fields.
- Did not add or research any new Mojave AOIs.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Bare `pytest tests/unit/test_run_eval_cslc_selfconsist_nam.py -q` imports an unrelated installed checkout on this machine and enforces full-project coverage. Verification used the project environment command with `--no-cov`, matching the prior Plan 09-01 local environment note.
- A parallel executor committed Plan 09-02 while this plan ran. This plan did not touch `run_eval_cslc_selfconsist_eu.py`, `compare_cslc.py`, or shared tracking files.

## Verification

- `python3 -m py_compile run_eval_cslc_selfconsist_nam.py` - passed.
- `micromamba run -n subsideo pytest tests/unit/test_run_eval_cslc_selfconsist_nam.py -q --no-cov` - passed, 22 passed.
- `grep -c "opera_frame_search" run_eval_cslc_selfconsist_nam.py` - returned 8.
- `grep -c "mojave_opera_frame_unavailable" run_eval_cslc_selfconsist_nam.py` - returned 1.
- `grep -c "Mojave/Coso-Searles" tests/unit/test_run_eval_cslc_selfconsist_nam.py` - returned 8.
- `grep -c "opera_frame_search" tests/unit/test_run_eval_cslc_selfconsist_nam.py` - returned 1.
- `grep -c "mojave_opera_frame_unavailable" tests/unit/test_run_eval_cslc_selfconsist_nam.py` - returned 1.

## Known Stubs

None introduced. Empty dictionaries/lists and `None` values in changed files are runtime initializers or test accumulators, not UI or sidecar stubs.

## Threat Flags

None. The OPERA reference-search trust boundary and fallback expansion threat are covered by the plan threat model; no new network endpoint, auth path, file trust boundary, or schema migration was introduced.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 09-05 reruns can now write Mojave OPERA availability evidence into `eval-cslc-selfconsist-nam/metrics.json`. Matrix rendering can consume the existing candidate BINDING blocker shape from Plan 09-01.

## Self-Check: PASSED

- Found summary file at `.planning/phases/09-cslc-egms-third-number-binding-reruns/09-03-SUMMARY.md`.
- Found task commit `0392495`.
- Found task commit `ec7abdf`.
- Confirmed no `STATE.md` or `ROADMAP.md` writes were made by this executor.

---
*Phase: 09-cslc-egms-third-number-binding-reruns*
*Completed: 2026-05-01*
