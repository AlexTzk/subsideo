---
phase: 09-cslc-egms-third-number-binding-reruns
plan: 05
subsystem: validation
tags: [cslc, binding, rerun, matrix, criteria]
requires:
  - phase: 09-cslc-egms-third-number-binding-reruns
    provides: Candidate BINDING schema, blocker evidence, Mojave frame-search evidence, and matrix rendering
provides:
  - Regenerated CSLC self-consistency sidecars with candidate BINDING evidence
  - Results matrix rows showing CSLC BINDING BLOCKER outcomes
  - Documented criteria-promotion deferment with blocker reasons
affects: [criteria-registry, results-matrix, cslc-conclusions, phase-verification]
tech-stack:
  added: []
  patterns:
    - Preserve ignored eval sidecars with forced git staging when they are phase evidence
    - Promote criteria only when regenerated sidecars report BINDING PASS for both CSLC cells
key-files:
  created:
    - eval-cslc-selfconsist-nam/metrics.json
    - eval-cslc-selfconsist-nam/meta.json
    - eval-cslc-selfconsist-eu/metrics.json
    - eval-cslc-selfconsist-eu/meta.json
    - .planning/phases/09-cslc-egms-third-number-binding-reruns/09-05-SUMMARY.md
  modified:
    - results/matrix.md
    - CONCLUSIONS_CSLC_SELFCONSIST_NAM.md
    - CONCLUSIONS_CSLC_SELFCONSIST_EU.md
key-decisions:
  - "criteria.py remains CALIBRATING because regenerated N.Am. and EU sidecars report BINDING BLOCKER."
  - "N.Am. promotion is blocked by SoCal stable-mask/burst-footprint intersection producing zero valid pixels."
  - "EU promotion is blocked by EGMStoolkit API mismatch before EGMS L2a CSV diagnostics can run."
patterns-established:
  - "A candidate BINDING BLOCKER is a valid Phase 9 outcome when sidecars contain named evidence and conclusions document deferment."
requirements-completed: [CSLC-07, CSLC-10, CSLC-11, VAL-01, VAL-03]
duration: ~35min
completed: 2026-05-01
---

# Phase 09 Plan 05: CSLC Rerun and Promotion Decision Summary

**CSLC reruns now produce preserved candidate BINDING evidence and matrix rows, with criteria promotion explicitly deferred by named blockers.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-05-01T07:55:00Z
- **Tasks:** 3
- **Files modified:** 8 evidence, matrix, documentation, and summary files

## Accomplishments

- Ran `make eval-cslc-eu`, which regenerated the EU sidecar with Iberian self-consistency measurements and an EGMS blocker.
- Ran `make eval-cslc-nam`, which regenerated the N.Am. sidecar with a SoCal blocker and Mojave/Coso-Searles candidate PASS plus OPERA amplitude sanity.
- Ran `make results-matrix`, which now renders both CSLC rows as `BINDING BLOCKER`.
- Preserved the ignored eval sidecars in git with forced staging so Phase 9 evidence is reviewable.
- Replaced all `TODO(Phase 9 rerun):` placeholders in both CSLC conclusions with actual blocker/deferment language.
- Left `src/subsideo/validation/criteria.py` unchanged because both CSLC cells are blocked.

## Task Commits

1. **Task 1: Run CSLC EU/N.Am. reruns and regenerate matrix** - `de7b5ff` (`test`)
2. **Task 2: Guarded criteria promotion or explicit deferment** - `109f8a4` (`docs`)

## Files Created/Modified

- `eval-cslc-selfconsist-nam/metrics.json` - N.Am. candidate BINDING sidecar: cell-level `BINDING BLOCKER`, SoCal `aoi_processing_failed`, Mojave `BINDING PASS`.
- `eval-cslc-selfconsist-nam/meta.json` - N.Am. rerun provenance.
- `eval-cslc-selfconsist-eu/metrics.json` - EU candidate BINDING sidecar: cell-level `BINDING BLOCKER`, Iberian EGMS tooling blocker.
- `eval-cslc-selfconsist-eu/meta.json` - EU rerun provenance.
- `results/matrix.md` - CSLC N.Am. and EU rows render explicit `BINDING BLOCKER` text.
- `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` - Phase 9 N.Am. deferment evidence replaces rerun TODOs.
- `CONCLUSIONS_CSLC_SELFCONSIST_EU.md` - Phase 9 EU deferment evidence replaces rerun TODOs.
- `.planning/phases/09-cslc-egms-third-number-binding-reruns/09-05-SUMMARY.md` - This execution summary.

## Decisions Made

- Did not promote `cslc.selfconsistency.coherence_min` or `cslc.selfconsistency.residual_mm_yr_max`; both remain CALIBRATING with v1.2 binding deferral.
- Treated `make eval-cslc-nam` exit 2 as a valid scientific-blocker outcome because the script wrote sidecars and matrix-consumable evidence before failing the cell.
- Committed ignored sidecars because they are the authoritative Phase 9 rerun evidence.

## Deviations from Plan

### Auto-fixed Issues

**1. Micromamba lock access outside workspace**
- **Found during:** Task 1 rerun commands.
- **Issue:** `make eval-cslc-eu` initially could not open `/Users/alex/.cache/mamba/proc/proc.lock` inside the sandbox.
- **Fix:** Reran Make targets with approved escalation so micromamba could access its lock/cache.
- **Files modified:** None.
- **Verification:** `make eval-cslc-eu`, `make eval-cslc-nam`, and `make results-matrix` all ran to sidecar/matrix output.

**2. Ignored eval sidecars would not appear in normal git status**
- **Found during:** Task 1 artifact review.
- **Issue:** `eval-cslc-selfconsist-*/metrics.json` and `meta.json` existed but were ignored/untracked.
- **Fix:** Used forced staging for the four sidecars in the rerun artifact commit.
- **Files modified:** Eval sidecar files.
- **Verification:** Commit `de7b5ff` includes the four sidecar files.

## Issues Encountered

- EU rerun blocker: `EGMStoolkit` lacks the expected `download` attribute, recorded as `egms_l2a_upstream_access_or_tooling_failure`.
- N.Am. rerun blocker: SoCal stable-mask intersection dropped from 2,286 pixels to 0 valid pixels after burst-footprint intersection, recorded as `aoi_processing_failed`.
- `make eval-cslc-nam` exited 2 because the cell has a required blocked AOI, but it wrote the evidence sidecars used by matrix/deferment.

## Verification

- `make eval-cslc-eu` - exited 0 and wrote EU sidecar evidence.
- `make eval-cslc-nam` - exited 2 after writing N.Am. sidecar evidence with a named SoCal blocker.
- `make results-matrix` - exited 0 and wrote `results/matrix.md`.
- `micromamba run -n subsideo python -m pytest tests/unit/test_criteria_registry.py -q --no-cov` - passed, 17 passed.
- `micromamba run -n subsideo python -m pytest tests/unit/test_matrix_writer.py tests/unit/test_matrix_schema.py -q --no-cov` - passed, 54 passed.
- `micromamba run -n subsideo python -m pytest tests/unit/test_matrix_schema.py tests/unit/test_matrix_writer.py tests/unit/test_criteria_registry.py tests/unit/test_compare_cslc.py tests/unit/test_run_eval_cslc_selfconsist_nam.py tests/unit/test_run_eval_cslc_selfconsist_eu.py -q --no-cov` - passed, 129 passed, 1 skipped.
- `micromamba run -n subsideo python -m pytest tests/unit/ -x -q --tb=short --no-cov` - passed, 624 passed, 1 skipped.
- `grep -n "CSLC" results/matrix.md` - shows N.Am. and EU rows as `BINDING BLOCKER`.
- `grep -c "TODO(Phase 9 rerun):" CONCLUSIONS_CSLC_SELFCONSIST_NAM.md CONCLUSIONS_CSLC_SELFCONSIST_EU.md` - both returned 0.

## Known Stubs

None. The Phase 9 rerun TODO placeholders were replaced.

## Threat Flags

No credentials or environment variables were committed. Blocker evidence records reason codes, counts, thresholds, request bounds, and sanitized exception strings only.

## User Setup Required

None for the completed phase result. Future promotion work needs separate fixes for SoCal stable-mask intersection and the EGMS toolkit adapter/API mismatch.

## Next Phase Readiness

Phase verification can confirm that Phase 9 delivered an evidence-backed deferment rather than a registry promotion. Follow-up planning should target the two named blockers before attempting CSLC BINDING promotion again.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/09-cslc-egms-third-number-binding-reruns/09-05-SUMMARY.md`.
- Rerun artifacts are committed in `de7b5ff`.
- Deferment conclusions are committed in `109f8a4`.
- `criteria.py` remains CALIBRATING for CSLC self-consistency criteria.
