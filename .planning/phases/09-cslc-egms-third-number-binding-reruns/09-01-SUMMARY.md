---
phase: 09-cslc-egms-third-number-binding-reruns
plan: 01
subsystem: validation
tags: [cslc, pydantic, sidecars, validation, candidate-binding]
requires:
  - phase: 08-cslc-gate-promotion-and-aoi-hardening
    provides: Phase 8 proposed CSLC BINDING thresholds and acquisition-backed AOI evidence
provides:
  - CSLC candidate BINDING sidecar schema
  - Per-AOI and cell-level candidate BINDING verdict computation in CSLC self-consistency evals
  - Backward-compatible CALIBRATING CSLC sidecar parsing
affects: [phase-09-cslc-reruns, matrix-rendering, cslc-validation-sidecars]
tech-stack:
  added: []
  patterns:
    - Additive Pydantic v2 sidecar fields with extra=forbid
    - Candidate verdicts stored separately from criteria.py CALIBRATING registry rows
key-files:
  created:
    - .planning/phases/09-cslc-egms-third-number-binding-reruns/09-01-SUMMARY.md
  modified:
    - src/subsideo/validation/matrix_schema.py
    - run_eval_cslc_selfconsist_nam.py
    - run_eval_cslc_selfconsist_eu.py
    - tests/unit/test_matrix_schema.py
    - tests/unit/test_run_eval_cslc_selfconsist_nam.py
    - tests/unit/test_run_eval_cslc_selfconsist_eu.py
key-decisions:
  - "Kept criteria.py unchanged so existing CSLC self-consistency criteria remain CALIBRATING during rerun evidence collection."
  - "Stored candidate BINDING thresholds alongside each candidate verdict for auditability."
patterns-established:
  - "Candidate BINDING verdicts use separate candidate_binding fields instead of changing legacy status literals."
  - "BINDING BLOCKER rows carry structured reason_code plus scalar/nested evidence."
requirements-completed: [CSLC-07, VAL-01, VAL-03]
duration: ~25min
completed: 2026-05-01
---

# Phase 09 Plan 01: CSLC Candidate Binding Sidecar Summary

**CSLC self-consistency sidecars now carry explicit candidate BINDING PASS/FAIL/BLOCKER verdicts with locked 0.75 coherence and 2.0 mm/yr residual thresholds, while criteria.py remains CALIBRATING.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-01T03:00:00Z
- **Completed:** 2026-05-01T03:25:56Z
- **Tasks:** 2
- **Files modified:** 6 code/test files plus this summary

## Accomplishments

- Added `CSLCCandidateThresholds`, `CSLCBlockerEvidence`, and `CSLCCandidateBindingResult` to the validation sidecar schema.
- Added optional `candidate_binding` and `opera_frame_search` fields to AOI sidecars, plus cell-level `candidate_binding` inherited by NAM and EU CSLC metrics.
- Updated N.Am. and EU CSLC self-consistency eval scripts to compute candidate verdicts from `0.75` and `2.0`, attach blocker evidence on AOI failures, and aggregate cell-level candidate verdicts.
- Added focused tests proving new candidate fields validate while legacy CALIBRATING sidecars still parse.

## Task Commits

1. **Task 1: Add candidate BINDING schema fields** - `ce5d549` (`feat`)
2. **Task 2: Compute candidate BINDING verdicts in both CSLC eval scripts** - `3e70b37` (`feat`)

## Files Created/Modified

- `src/subsideo/validation/matrix_schema.py` - Candidate BINDING schema models and additive AOI/cell fields.
- `run_eval_cslc_selfconsist_nam.py` - Candidate thresholds, per-AOI verdicts, failure blocker evidence, and cell aggregation.
- `run_eval_cslc_selfconsist_eu.py` - Same candidate verdict wiring for the EU CSLC eval path.
- `tests/unit/test_matrix_schema.py` - Schema coverage for AOI/cell candidate verdicts, blocker evidence, nested evidence, legacy parsing, and OPERA frame-search evidence.
- `tests/unit/test_run_eval_cslc_selfconsist_nam.py` - Source-level checks for candidate constants and wiring.
- `tests/unit/test_run_eval_cslc_selfconsist_eu.py` - Source-level checks for candidate constants and wiring.

## Decisions Made

- Candidate verdicts are separate from existing `status` and `cell_status` literals, preserving old CALIBRATING sidecar compatibility.
- Failure rows use `reason_code="aoi_processing_failed"` with `repr(e)` evidence; this keeps blocker evidence audit-ready without storing credentials or external tokens.
- Cell-level aggregation treats any required AOI `BINDING BLOCKER` as a cell `BINDING BLOCKER`, otherwise any AOI `BINDING FAIL` as cell `BINDING FAIL`, otherwise `BINDING PASS`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The bare `pytest tests/unit/test_matrix_schema.py -q` command used the wrong editable install path on this machine and failed imports. The project environment command ran against this checkout.
- Focused pytest invocations need `--no-cov` because project-wide coverage settings fail narrow test runs by measuring the full package. The focused tests themselves passed.
- `ruff check` on the task files reports pre-existing lint issues in `tests/unit/test_run_eval_cslc_selfconsist_nam.py`; no broad lint cleanup was performed.

## Verification

- `micromamba run -n subsideo pytest tests/unit/test_matrix_schema.py -q --no-cov` - passed, 25 passed.
- `python3 -m py_compile run_eval_cslc_selfconsist_nam.py run_eval_cslc_selfconsist_eu.py` - passed.
- `micromamba run -n subsideo pytest tests/unit/test_run_eval_cslc_selfconsist_nam.py tests/unit/test_run_eval_cslc_selfconsist_eu.py -q --no-cov` - passed, 44 passed, 1 skipped.
- `grep -c "CSLCCandidateBindingResult" src/subsideo/validation/matrix_schema.py` - returned 3.
- `grep -c "candidate_binding" src/subsideo/validation/matrix_schema.py` - returned 2.
- `grep -c "opera_frame_search" src/subsideo/validation/matrix_schema.py` - returned 1.
- `grep -c "CANDIDATE_COHERENCE_MIN = 0.75"` - returned 1 in both CSLC eval scripts.
- `grep -c "CANDIDATE_RESIDUAL_ABS_MAX_MM_YR = 2.0"` - returned 1 in both CSLC eval scripts.
- `src/subsideo/validation/criteria.py` still contains `type="CALIBRATING"` for both CSLC self-consistency criteria.

## Known Stubs

None introduced. Existing empty defaults and placeholder-related test text are schema/test fixtures, not runtime UI or sidecar stubs.

## Threat Flags

None. The changed files extend local JSON sidecar shape and eval-script output only; no new network endpoint, auth path, file trust boundary, or schema migration was introduced beyond the sidecar fields already covered by the plan threat model.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 09-02 can consume `candidate_binding` fields from CSLC metrics sidecars without promoting `criteria.py`. Matrix rendering can now distinguish candidate product-quality verdicts from legacy CALIBRATING status and reference-agreement evidence.

## Self-Check: PASSED

- Found summary file at `.planning/phases/09-cslc-egms-third-number-binding-reruns/09-01-SUMMARY.md`.
- Found task commit `ce5d549`.
- Found task commit `3e70b37`.
- Confirmed no `STATE.md` or `ROADMAP.md` writes were made by this executor; pre-existing `.planning/STATE.md` modification remains unstaged.

---
*Phase: 09-cslc-egms-third-number-binding-reruns*
*Completed: 2026-05-01*
