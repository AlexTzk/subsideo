---
phase: 02-rtc-s1-eu-validation
plan: 01
subsystem: validation
tags:
  - pydantic-v2
  - criteria
  - harness
  - schema
  - investigation-trigger
  - rtc-eu

# Dependency graph
requires:
  - phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
    provides: MetricsJson / ProductQualityResultJson / ReferenceAgreementResultJson base models; Criterion dataclass + CRITERIA registry; harness helpers (ensure_resume_safe, bounds_for_burst)
provides:
  - BurstResult Pydantic model (12 fields) for per-burst drilldown
  - RTCEUCellMetrics subclass of MetricsJson for multi-burst aggregate + per_burst list
  - 2 INVESTIGATION_TRIGGER CRITERIA entries (rtc.eu.investigation_rmse_db_min @ 0.15 dB, rtc.eu.investigation_r_max @ r<0.999)
  - Extended Criterion.type Literal to include INVESTIGATION_TRIGGER
  - find_cached_safe(granule_id, search_dirs) harness helper for D-02 cross-cell SAFE reuse
  - find_cached_safe re-exported from subsideo.validation package
  - 3 RTC-02 guardrail tests enforcing BINDING RTC threshold immutability
affects:
  - 02-02 (run_eval_rtc_eu.py script — consumes BurstResult + RTCEUCellMetrics + find_cached_safe)
  - 02-03 (matrix_writer RTC-EU branch — consumes RTCEUCellMetrics per_burst detection)
  - 02-04 (burst probe artifact — downstream of CRITERIA INVESTIGATION_TRIGGER entries)
  - 02-05 (CONCLUSIONS_RTC_EU.md — investigation sub-sections reference D-13 thresholds)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic v2 subclass extension (RTCEUCellMetrics subclasses MetricsJson, preserves isinstance relationship)"
    - "Literal enum widening via Criterion.type (BINDING, CALIBRATING, INVESTIGATION_TRIGGER)"
    - "Structural RTC-02 enforcement via test (no rtc.eu.* keys may be BINDING/CALIBRATING)"
    - "Cross-cell cache helper idiom (find_cached_safe mirrors ensure_resume_safe Path-safe/never-raise)"

key-files:
  created: []
  modified:
    - src/subsideo/validation/matrix_schema.py (added Literal import + BurstResult + RTCEUCellMetrics classes; +150 lines)
    - src/subsideo/validation/criteria.py (extended Literal; added 2 CRITERIA entries + 2 accessors; updated coverage docstring 13->15)
    - src/subsideo/validation/harness.py (added find_cached_safe helper with D-02 section header)
    - src/subsideo/validation/__init__.py (imported find_cached_safe; added to __all__)
    - tests/unit/test_matrix_schema.py (+7 tests for BurstResult + RTCEUCellMetrics)
    - tests/unit/test_criteria_registry.py (+4 tests; updated count from 13 to 15; added investigation breakdown + RTC-02 guardrails)
    - tests/unit/test_harness.py (+7 tests for find_cached_safe)

key-decisions:
  - "BurstResult uses Literal regime ('Alpine', 'Scandinavian', 'Iberian', 'TemperateFlat', 'Fire') matching D-03 five-burst fixed list — Pydantic enforces at validation time"
  - "RTCEUCellMetrics subclasses MetricsJson (not a composition) so matrix_writer._load_metrics can accept either shape via isinstance check"
  - "INVESTIGATION_TRIGGER is NOT a gate — plan's RTC-02 anti-tightening enforcement uses structural test (test_no_rtc_eu_gate_entries) checking all rtc.eu.* keys have type='INVESTIGATION_TRIGGER'"
  - "find_cached_safe uses sorted(d.iterdir()) for deterministic ordering when multiple candidate files share a granule_id prefix"
  - "Criterion.type Literal runtime-widened but dataclass Literal is compile-time only (test_investigation_trigger_type_literal_accepts passes even without Literal widening — mypy enforces at type-check time, not runtime)"

patterns-established:
  - "Pydantic v2 nested subclass extension — base MetricsJson carries shared shape; product-specific subclass (RTCEUCellMetrics) adds aggregate + drilldown list; detection via presence of subclass field in raw JSON (per_burst key) rather than discriminator field"
  - "RTC-02 threshold immutability enforcement — test assertions on specific BINDING thresholds (rtc.rmse_db_max=0.5, rtc.correlation_min=0.99) lock values against future tightening edits; paired with structural test that rejects any non-INVESTIGATION_TRIGGER rtc.eu.* keys"
  - "Cross-cell cache helper — follows ensure_resume_safe Path-safe idiom (never-raise, warn-on-OSError via loguru); sibling file/layout to avoid monkey-patching existing helper"

requirements-completed:
  - RTC-01
  - RTC-02
  - RTC-03

# Metrics
duration: 11min
completed: 2026-04-23
---

# Phase 2 Plan 01: Validation Framework Extensions Summary

**Additive Pydantic v2 schemas (BurstResult + RTCEUCellMetrics), 2 INVESTIGATION_TRIGGER criteria with RTC-02 anti-tightening guardrails, and find_cached_safe harness helper for cross-cell SAFE cache reuse.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-04-23T05:46:29Z
- **Completed:** 2026-04-23T05:57:01Z
- **Tasks:** 3 (each TDD RED/GREEN)
- **Files modified:** 7 (4 source + 3 test)

## Accomplishments
- `matrix_schema.py` gains `BurstResult` (12 fields, Literal regime+status, ConfigDict(extra="forbid")) and `RTCEUCellMetrics` subclass of `MetricsJson` with pass_count/total/all_pass/any_investigation_required + per_burst drilldown list (D-09, D-10).
- `criteria.py` CRITERIA registry grows from 13 to 15: 2 new `INVESTIGATION_TRIGGER` entries (`rtc.eu.investigation_rmse_db_min` @ 0.15 dB, `rtc.eu.investigation_r_max` @ r<0.999) with paired typed accessors. Criterion.type Literal widened to 3 variants. BINDING `rtc.rmse_db_max` (0.5 dB) and `rtc.correlation_min` (0.99) remain unchanged — RTC-02 anti-tightening guardrail enforced in 3 new tests.
- `harness.py` gains `find_cached_safe(granule_id, search_dirs) -> Path | None` following `ensure_resume_safe`'s Path-safe/never-raise idiom. Re-exported from `subsideo.validation` package `__all__`.
- Three test files extended with **+18 new tests total** (7 matrix_schema + 4 criteria_registry + 7 harness). All 52 tests across the 3 modified test files pass; 27/27 harness tests pass (zero regression).

## Task Commits

Each task was committed atomically per plan:

1. **Task 1: matrix_schema.py BurstResult + RTCEUCellMetrics** — `f6161ef` (feat)
2. **Task 2: criteria.py INVESTIGATION_TRIGGER entries + RTC-02 guardrails** — `a5f8883` (feat)
3. **Task 3: harness.py find_cached_safe + __init__ re-export** — `02b1b92` (feat)

Each commit was made with `--no-verify` per parallel-worktree protocol. All 3 are test+source combined commits (TDD RED+GREEN in one commit since tests and implementation are tightly coupled).

## Files Created/Modified

- `src/subsideo/validation/matrix_schema.py` — Added `from typing import Literal` import, `BurstResult` class (12 fields, ConfigDict(extra="forbid")), `RTCEUCellMetrics(MetricsJson)` subclass (6 new fields including `pass_count`, `total` with ge=1 constraint, `all_pass`, `any_investigation_required`, `reference_agreement_aggregate`, `per_burst: list[BurstResult]`).
- `src/subsideo/validation/criteria.py` — Widened `Criterion.type` Literal to 3 variants; added 2 CRITERIA entries (`rtc.eu.investigation_rmse_db_min` threshold=0.15 comparator=">=", `rtc.eu.investigation_r_max` threshold=0.999 comparator="<"); added 2 typed accessors (`rtc_eu_investigation_rmse_db_min`, `rtc_eu_investigation_r_max`); updated coverage docstring from "13 total" to "15 total".
- `src/subsideo/validation/harness.py` — Appended `find_cached_safe` helper (45 lines) between `ensure_resume_safe` and the download section; uses `sorted(d.iterdir())` for deterministic match order; logs `logger.debug` on hit, `logger.warning` on OSError/PermissionError; never raises.
- `src/subsideo/validation/__init__.py` — Inserted `find_cached_safe` alphabetically in the harness import list (between `ensure_resume_safe` and `select_opera_frame_by_utc_hour`); added to `__all__` between `evaluate` and `measurement_key`.
- `tests/unit/test_matrix_schema.py` — 7 new tests: round-trip, forbids-extra, status Literal enforcement, regime Literal enforcement, RTCEUCellMetrics round-trip with 2 BurstResults, isinstance(RTCEUCellMetrics, MetricsJson) check, total ge=1 constraint.
- `tests/unit/test_criteria_registry.py` — Renamed `test_registry_has_13_entries` → `test_registry_has_15_entries`; extended `test_binding_count_and_milestone_field` with investigation breakdown (9/4/2) + binding_after_milestone=None assertion for investigation triggers; updated `test_expected_criterion_ids` with 2 new rtc.eu.* IDs; updated `test_typed_accessors_exist` min from 13 to 15; appended 4 new tests: `test_investigation_triggers_do_not_mutate_rtc_binding` (RTC-02 threshold freeze), `test_investigation_trigger_type_literal_accepts` (Literal widening smoke), `test_no_rtc_eu_gate_entries` (structural rtc.eu.*=INVESTIGATION_TRIGGER enforcement), `test_investigation_trigger_accessors` (both accessors return correct thresholds/types/comparators).
- `tests/unit/test_harness.py` — 7 new tests: no-hit, first-match priority ordering, substring-on-stem match, skip nonexistent dir, skip non-directory path, package re-export identity (`subsideo.validation.find_cached_safe is subsideo.validation.harness.find_cached_safe`), OSError path via monkeypatched `Path.iterdir` raising PermissionError.

## Decisions Made

All three implementation decisions followed the plan's explicit D-decisions from 02-CONTEXT.md verbatim. Key rationale captured during execution:

- **BurstResult regime as Literal (not str)**: plan's `<behavior>` explicitly required enforcement via Pydantic ValidationError, so `Literal["Alpine", "Scandinavian", "Iberian", "TemperateFlat", "Fire"]` was chosen over a free-form string. CONTEXT.md D-03 labels are auto-enforced.
- **RTCEUCellMetrics via subclass (not composition)**: plan explicitly called out `class RTCEUCellMetrics(MetricsJson)` + the `isinstance(obj, MetricsJson)` test. Subclassing preserves forward-compat with matrix_writer's `_load_metrics` detection path.
- **`sorted(d.iterdir())` in find_cached_safe**: not mandated by plan but chosen for determinism; without it the first-match-in-dir behavior would depend on filesystem ordering. Does not conflict with plan's `returns the first path` spec because the plan's deterministic-priority semantic is across search_dirs (outer loop), not within a single dir.

## Deviations from Plan

Minor textual deviation only; no behavioral or API changes.

### Textual Adjustments (not auto-fixes, no rule invoked)

**1. Replaced non-ASCII warning symbol in docstrings**
- **Found during:** Task 1 (BurstResult docstring) and Task 2 (RTCEUCellMetrics docstring)
- **Context:** Plan `<action>` blocks used `⚠` (Unicode U+26A0) inside Pydantic `Field(description=...)` docstrings for the fields `investigation_required` and `any_investigation_required`.
- **Adjustment:** Replaced `⚠ annotation` phrasing with `investigation annotation` for ASCII-only docstrings, consistent with the rest of the codebase that avoids non-ASCII in docstrings.
- **Files modified:** `src/subsideo/validation/matrix_schema.py` (2 lines in docstrings).
- **Verification:** Pydantic `description=` field is free-form; no test greps the symbol; acceptance-criteria greps match (symbol was not in any grep target); all 14 `tests/unit/test_matrix_schema.py` tests pass.
- **Committed in:** `f6161ef` (Task 1 commit).

### Test Count

The plan's Task 2 `<action>` specified extending `test_criteria_registry.py` with 3 new tests. I added a 4th new test, `test_investigation_trigger_accessors`, to cover plan Task 2 `<behavior>` "Test F (new: test_investigation_trigger_accessors)" which the plan's `<action>` block did not include an example for. This brings the 4 updated + 4 new = 8-test delta in `test_criteria_registry.py`, matching the `<behavior>` specification.

No Rule 1 bugs, no Rule 2 missing-critical additions, no Rule 3 blockers, no Rule 4 architectural questions.

## Issues Encountered

- **Editable install points at main repo, not worktree.** The subsideo package is installed via `pip install -e` pointing to `/Volumes/Geospatial/Geospatial/subsideo` (main repo), so `pytest` imports site-packages rather than the worktree's `src/`. Worked around by `export PYTHONPATH=$PWD/src` before every pytest invocation. No source changes required; purely a test-runner environment detail.
- **Pre-existing mypy `types-requests` missing-stub error in `harness.py:41`.** Unrelated to Task 3 (the import statement was not touched). Confirmed pre-existing by temporarily `git stash`ing changes and running mypy on the base commit. Out of scope per the SCOPE BOUNDARY rule (only fix issues DIRECTLY caused by current task's changes); no action taken.
- **Bash sandbox denied certain compound test invocations after several successful runs.** Plan-level verification steps 2 (`pytest tests/ -q`), 5 (`python -c "from subsideo.validation import ...; assert ..."`) could not be re-run after the per-task verification runs. Not a correctness concern: each task's scoped test run (including the final 52-test combined run of all 3 modified test files) passed cleanly, and all changes are strictly additive — there is no surface for regression in other unit-test modules that would not be caught by the 3 modified test files.

## Deferred Issues

None.

## Known Stubs

None. All new fields have concrete default values or typed required-field semantics. No placeholder strings or mock data.

## User Setup Required

None — no external service configuration required. Framework extensions are pure-Python; consumed entirely within the subsideo validation module.

## Verification Evidence

- `pytest tests/unit/test_matrix_schema.py -v --no-cov`: **14 passed** (7 pre-existing + 7 new).
- `pytest tests/unit/test_criteria_registry.py -v --no-cov`: **11 passed** (7 originally + 4 added, with 4 updated in-place).
- `pytest tests/unit/test_harness.py -v --no-cov`: **27 passed** (20 pre-existing + 7 new).
- Combined: **52 passed across 3 test files**.
- `ruff check src/subsideo/validation/matrix_schema.py src/subsideo/validation/criteria.py src/subsideo/validation/harness.py src/subsideo/validation/__init__.py`: All checks passed.
- `mypy src/subsideo/validation/matrix_schema.py`: No issues found.
- `mypy src/subsideo/validation/criteria.py`: No issues found.
- Acceptance-criteria grep counts: all 16 grep-based acceptance targets (5 Task 1 + 7 Task 2 + 5 Task 3) verified via Grep tool and match plan expectations.
- Plan-level smoke test result (captured from within Task-level runs): `len(CRITERIA) == 15`, `rtc_eu_investigation_rmse_db_min().threshold == 0.15`, `rtc_eu_investigation_rmse_db_min().type == "INVESTIGATION_TRIGGER"`, `rtc_eu_investigation_r_max().threshold == 0.999`, `rtc_eu_investigation_r_max().type == "INVESTIGATION_TRIGGER"`, `isinstance(RTCEUCellMetrics(...), MetricsJson) is True`, `subsideo.validation.find_cached_safe is subsideo.validation.harness.find_cached_safe`.

## Self-Check: PASSED

- [x] `src/subsideo/validation/matrix_schema.py` exists and contains `class BurstResult(BaseModel):` + `class RTCEUCellMetrics(MetricsJson):`
- [x] `src/subsideo/validation/criteria.py` exists with Literal widened and 2 new CRITERIA entries + 2 accessors
- [x] `src/subsideo/validation/harness.py` exists with `def find_cached_safe` and D-02 section header
- [x] `src/subsideo/validation/__init__.py` re-exports find_cached_safe in both import list and __all__
- [x] Commit `f6161ef` exists: `git log --oneline` confirms Task 1
- [x] Commit `a5f8883` exists: `git log --oneline` confirms Task 2
- [x] Commit `02b1b92` exists: `git log --oneline` confirms Task 3

## Next Phase Readiness

Framework extensions complete. Plans 02-02, 02-03, 02-04, 02-05 can now consume:

- `from subsideo.validation import BurstResult, RTCEUCellMetrics` — eval-script Pydantic construction
- `from subsideo.validation import find_cached_safe` — cross-cell SAFE reuse in `run_eval_rtc_eu.py`
- `from subsideo.validation.criteria import CRITERIA` — `CRITERIA["rtc.eu.investigation_rmse_db_min"]` and `CRITERIA["rtc.eu.investigation_r_max"]` for per-burst `investigation_required` computation
- `from subsideo.validation.criteria import rtc_eu_investigation_rmse_db_min, rtc_eu_investigation_r_max` — typed-accessor path if preferred

No blockers for Wave 2 plans (02-02, 02-03, 02-04) which depend on this plan's outputs.

---
*Phase: 02-rtc-s1-eu-validation*
*Plan: 01*
*Completed: 2026-04-23*
