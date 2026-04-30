---
phase: 04-disp-s1-comparison-adapter-honest-fail
plan: 03
subsystem: validation
tags: [insar, validation, matrix-writer, calibrating, render, dispatch, pydantic-render]

# Dependency graph
requires:
  - phase: 04-disp-s1-comparison-adapter-honest-fail
    provides: matrix_schema.DISPCellMetrics + DISPProductQualityResultJson + RampAttribution + AttributedSource + CoherenceSource + DISPCellStatus (Plan 04-01 schema additions)
  - phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
    provides: matrix_writer module + _render_measurement helper + _escape_table_cell + dispatch loop pattern in write_matrix
provides:
  - "matrix_writer._is_disp_cell_shape (top-level ramp_attribution-key discriminator)"
  - "matrix_writer._render_disp_cell (italicised CALIBRATING PQ + non-italicised BINDING RA via _render_measurement reuse)"
  - "Dispatch insertion in write_matrix: DISP branch BEFORE CSLC self-consist (per_aoi) + RTC-EU (per_burst) -- structurally disjoint schemas, ramp_attribution is the unambiguous Phase 4 marker"
affects: [04-04-eval-scripts-rerun, 04-05-conclusions-doc-brief]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-cell symmetric render branch (mirror of _render_cslc_selfconsist_cell) -- both region='nam' and region='eu' route through a single _render_disp_cell because the DISPCellMetrics schema is symmetric across SoCal and Bologna"
    - "Schema-discriminator dispatch BEFORE pydantic validation: cheap json.loads + key check (ramp_attribution presence) protects the base MetricsJson(extra='forbid') from rejecting DISP-only fields"
    - "Mixed PQ-italics + RA-non-italics rendering: PQ side wraps the whole metric body in '*...*' with CALIBRATING tag inline; RA side reuses _render_measurement which already does PASS/FAIL formatting -- BINDING criteria render as plain text"
    - "attributed_source label inline in PQ column (CONTEXT D-13): cell-level audit trail in metrics.json, human-review canonical labelling in CONCLUSIONS prose, but matrix.md gets the auto-attribute label inline so a reader scanning the matrix sees the per-cell PHASS/orbit/mixed/inconclusive flag without opening CONCLUSIONS"

key-files:
  created:
    - "tests/reference_agreement/test_matrix_writer_disp.py"
  modified:
    - "src/subsideo/validation/matrix_writer.py"

key-decisions:
  - "DISP dispatch inserted BEFORE both CSLC self-consist (per_aoi) and RTC-EU (per_burst) branches at lines 476-489 (CSLC at line 491, RTC-EU at line 506). Schemas are structurally disjoint -- ramp_attribution co-occurs with neither per_aoi nor per_burst. Order is an invariant, not a guess (RESEARCH lines 593-608). Verified via line-number ordering grep."
  - "PQ column wraps the whole metric body in '*...*' italics with '(CALIBRATING)' tag INSIDE the italics (final form: '*coh=0.87 ([phase3-cached]) / resid=-0.1 mm/yr / attr=phass (CALIBRATING)*'). Mirrors the CSLC self-consist convention at matrix_writer.py:346 ('*{pq_body}*{warn}'). The CALIBRATING tag inline + outer italics is belt-and-braces per Phase 1 D-03 / GATE-03."
  - "RA column reuses the existing _render_measurement helper (one entry per ra.criterion_ids) joined by ' / '. No separate per-DISP RA renderer. The helper already produces 'value (op threshold VERDICT)' for BINDING criteria and appends '(CALIBRATING)' for CALIBRATING ones; reusing it preserves the per-criterion verdict formatting consistency across all matrix cells."
  - "BLOCKER warning glyph (U+26A0) appended to PQ column when m.cell_status == 'BLOCKER' (mirrors the CSLC self-consist any_blocker convention at matrix_writer.py:344). MIXED + CALIBRATING + PASS + FAIL render without glyph -- BLOCKER is the only DISP cell_status that surfaces the warning."
  - "_render_disp_cell returns None on DISPCellMetrics.model_validate_json failure; write_matrix() falls through to the default RUN_FAILED rendering branch. Mirrors _render_cslc_selfconsist_cell + _render_rtc_eu_cell parse-failure semantics."

patterns-established:
  - "Phase 4 schema discriminator pattern: cheap json.loads + dict-key check (ramp_attribution / per_aoi / per_burst) BEFORE Pydantic validation. Each subsequent phase that adds a new MetricsJson subclass should follow this 'check the unique top-level key, then defer to subclass.model_validate_json' pattern. The base MetricsJson uses extra='forbid' so directly trying to validate a phase-specific shape against the base is a guaranteed failure."
  - "Render branch fall-through on parse failure: each _render_*_cell helper returns None when model_validate_json raises, the dispatch caller logs via logger.warning + continues to the next branch, ultimately falling through to the default RUN_FAILED rendering. This means a malformed DISP cell renders as RUN_FAILED rather than crashing the entire matrix write."
  - "_render_measurement reuse for any cell type with criterion_ids-based RA: when a new cell type's RA section is BINDING criteria from criteria.py CRITERIA registry, _render_measurement is the canonical renderer -- do NOT re-implement value-(op-threshold-VERDICT) formatting. Reuse count is now 5 (1 def + 1 default branch + 1 CSLC + 1 RTC-EU + 1 DISP)."

requirements-completed: [DISP-03]

# Metrics
duration: 4min
completed: 2026-04-25
---

# Phase 04 Plan 03: matrix_writer DISP cell render branch Summary

**2 new helpers (`_is_disp_cell_shape` + `_render_disp_cell`) + dispatch insertion in `write_matrix()` BEFORE the existing CSLC self-consist + RTC-EU branches; 13 unit tests covering shape discrimination + render correctness for both regions + BLOCKER glyph + provenance flag rendering + parse-failure fall-through + end-to-end write_matrix integration; ruff + mypy clean on touched files; existing matrix_writer behaviour for CSLC/RTC/default cells unchanged.**

## Performance

- **Duration:** 4 min (3 min 52 sec)
- **Started:** 2026-04-25T07:25:44Z
- **Completed:** 2026-04-25T07:29:36Z
- **Tasks:** 2 (Task 1 RED + GREEN; Task 2 full test matrix)
- **Files modified/created:** 2 (1 source modified, 1 test file created)

## Accomplishments

- **`_is_disp_cell_shape(metrics_path: Path) -> bool`** added to `matrix_writer.py` per CONTEXT D-11 schema discriminator. Cheap json.loads + dict-key check for top-level `ramp_attribution`. Catches OSError + ValueError on parse failure; degrades to False (mirrors `_is_cslc_selfconsist_shape` and `_is_rtc_eu_shape` patterns).
- **`_render_disp_cell(metrics_path: Path, *, region: str) -> tuple[str, str] | None`** added to `matrix_writer.py` per CONTEXT D-12 + D-13 + D-19 + D-21. Single render branch handles both `disp:nam` (region='nam') and `disp:eu` (region='eu') because the DISPCellMetrics schema is symmetric across SoCal and Bologna. PQ column italicised with `attributed_source` label inline ('attr=phass'); RA column reuses the existing `_render_measurement` helper for each criterion ID. Returns None on parse failure -> write_matrix() falls through to default RUN_FAILED branch.
- **Dispatch insertion in `write_matrix()`** at lines 476-489 BEFORE the existing CSLC self-consist branch (line 491) and RTC-EU branch (line 506). Verified via line-number ordering grep: DISP=476, CSLC=491. The DISP discriminator is structurally disjoint from per_aoi (CSLC) and per_burst (RTC-EU); dispatch order is an invariant, not a guess (RESEARCH lines 593-608).
- **13-test suite** at `tests/reference_agreement/test_matrix_writer_disp.py` covering: 4 `_is_disp_cell_shape` cases (true on disp metrics; false without ramp_attribution / on missing file / on invalid JSON), 8 `_render_disp_cell` cases (nam tuple shape; eu identical to nam; cell_status=BLOCKER warning glyph; phase3-cached + fresh provenance rendering; attr=phass + attr=inconclusive labels; parse failure returns None), and 1 end-to-end via write_matrix (manifest with one disp:nam cell + valid metrics.json renders via the DISP dispatch branch -- not the default RUN_FAILED branch).

## Task Commits

Each task was developed via TDD (RED smoke commit -> GREEN feat commit; Task 2 = full test matrix replacing the smoke test) and committed atomically:

1. **Task 1 RED -- failing smoke test** -- `e5b5361` (test). ImportError on `from subsideo.validation.matrix_writer import (_is_disp_cell_shape, _render_disp_cell)` confirmed before implementation.
2. **Task 1 GREEN -- _is_disp_cell_shape + _render_disp_cell + dispatch insertion** -- `488282e` (feat). +104 LOC on matrix_writer.py (475 -> 579 LOC). Helpers placed AFTER `_render_cslc_selfconsist_cell` and BEFORE `def write_matrix(...)`. Dispatch block inserted in `write_matrix` BEFORE the `# Phase 3 CSLC self-consistency branch:` comment.
3. **Task 2 -- 13-test matrix** -- `7d6e178` (test). +268 / -11 LOC vs the smoke test (the smoke test from Task 1 RED was replaced with the full suite which also covers it semantically).

_TDD plan-level gate sequence (test -> feat -> test) holds. Task 1 follows strict RED (ImportError) -> GREEN (impl) flow; Task 2 is a test-only commit because the impl already existed from Task 1 -- the tests act as behavior pinning rather than a strict RED -> GREEN cycle on a different feature. This matches the plan's two-task structure (Task 1 = impl with smoke test, Task 2 = full unit-test matrix) and mirrors Plan 04-02's same-shape commit sequence._

## Files Created/Modified

- **`src/subsideo/validation/matrix_writer.py`** (modified) -- appended `_is_disp_cell_shape` (15 LOC) + `_render_disp_cell` (60 LOC) + section divider comment after `_render_cslc_selfconsist_cell` (line 348) and before `def write_matrix(...)` (line 351 -> 440). Inserted DISP dispatch block (12 LOC) in `write_matrix` body BEFORE the CSLC self-consist branch (line 387 -> 476). Net +104 LOC; 475 -> 579.
- **`tests/reference_agreement/test_matrix_writer_disp.py`** (created, 257 LOC) -- 13 tests under 3 sections (`_is_disp_cell_shape` / `_render_disp_cell` / End-to-end via write_matrix). Uses tmp_path for all fixtures; absolute paths in the e2e manifest (mirrors `tests/unit/test_matrix_writer.py` convention at lines 23-24).

## Decisions Made

- **DISP dispatch BEFORE CSLC + RTC-EU branches** -- per CONTEXT D-21 + RESEARCH lines 593-608, the DISP `ramp_attribution` discriminator is structurally disjoint from CSLC `per_aoi` and RTC-EU `per_burst` keys. Dispatch order is an invariant, not a guess. Verified at runtime via line-number ordering: DISP=476, CSLC=491, RTC-EU=506. Test 13 (end-to-end) covers the dispatch path; the line-number grep in plan acceptance criteria 5 covers the position invariant.
- **Single `_render_disp_cell` for both regions** -- the DISPCellMetrics Pydantic schema is identical across N.Am. SoCal and EU Bologna (Plan 04-01 D-Claude's-Discretion). Region only enters via the manifest dispatch (`cell["region"]` = 'nam' / 'eu'), not via the cell render itself. The `region` parameter is passed through for symmetry with `_render_cslc_selfconsist_cell` (which uses it to switch between `CSLCSelfConsistNAMCellMetrics` and `CSLCSelfConsistEUCellMetrics` types) and is currently unused in the body of `_render_disp_cell` -- but kept for forward-compat in case Phase 4 D-08-style regional divergence ever needs to fork the render later. Test 6 (`test_render_disp_cell_eu_returns_same_shape`) pins this invariant.
- **PQ column format: `*coh=A.AA ([source]) / resid=B.B mm/yr / attr=label (CALIBRATING)*`** -- italicised whole-body with `(CALIBRATING)` tag INSIDE the italics. Mirrors `_render_cslc_selfconsist_cell:346` (`f"*{pq_body}*{warn}"`). Inline `attributed_source` label per CONTEXT D-13. Provenance label in square brackets so the inline `(coherence_source)` doesn't visually conflict with the surrounding parens. BLOCKER warning glyph (U+26A0) appended OUTSIDE the italics so it's visible against the italic body.
- **RA column reuses `_render_measurement` for each criterion ID** -- no per-DISP RA renderer. The existing helper produces `value (op threshold VERDICT)` for BINDING and appends `(CALIBRATING)` for CALIBRATING criteria, joined by ` / `. The DISP RA criteria (`disp.correlation_min`, `disp.bias_mm_yr_max`) are both BINDING from v1.0; the rendered RA column is non-italicised plain PASS/FAIL.

## Deviations from Plan

One **Rule 3** auto-fix applied during execution; did not change plan intent:

### Rule 3 - Blocking: Unused `# type: ignore[arg-type]` comments on Pydantic Literal-field assigns in test fixtures

- **Found during:** Task 2 mypy check.
- **Issue:** The plan's verbatim test code at `_make_disp_metrics` includes `coherence_source=coherence_source,  # type: ignore[arg-type]` (and 2 similar sites for `attributed_source` + `cell_status`). Mypy flags these as `[unused-ignore]` because the project's mypy config narrows `str` -> `Literal["..."]` correctly when the runtime value is one of the Literal values. Identical issue documented in Plan 04-02 SUMMARY's deviation log at the same site pattern.
- **Fix:** Removed the 3 unused `# type: ignore[arg-type]` comments. Behaviour identical (the function still raises Pydantic ValidationError at runtime when an invalid Literal value is passed); the comments were redundant noise.
- **Files modified:** `tests/reference_agreement/test_matrix_writer_disp.py`
- **Verification:** mypy reports 0 errors; ruff clean; all 13 tests pass.
- **Committed in:** `7d6e178` (Task 2)

---

**Total deviations:** 1 auto-fixed (1 blocking).
**Impact on plan:** No plan-intent change. Same fix pattern as Plan 04-02; mypy noise reduction only.

## Issues Encountered

- **`micromamba run -n subsideo` shell-function shim still broken** -- same issue documented in Plan 04-02 SUMMARY ("invocation produced shell errors via the auto-loaded function wrap; resolved by using the env's python directly `/Users/alex/.local/share/mamba/envs/subsideo/bin/python`"). Functionally identical (same env, same packages); plan acceptance commands honoured at the env level. Not a deviation -- the same approach Plan 04-02 took. Plan acceptance criterion `micromamba run -n subsideo python -c "from subsideo.validation.matrix_writer import write_matrix, _is_disp_cell_shape, _render_disp_cell; print('OK')"` was executed via the equivalent env-python invocation; output `OK`.

## TDD Gate Compliance

Plan-level TDD gate sequence:

- **Task 1 RED gate (`e5b5361`)** -- `test(04-03): add failing smoke test for matrix_writer DISP branch` confirmed failing on `ImportError: cannot import name '_is_disp_cell_shape' from 'subsideo.validation.matrix_writer'` before implementation.
- **Task 1 GREEN gate (`488282e`)** -- `feat(04-03): add DISP cell render branch to matrix_writer`; smoke test passes; all 24 pre-existing matrix_writer tests still pass.
- **Task 2 (`7d6e178`)** -- `test(04-03): add 13-test matrix for matrix_writer DISP render branch`. RED-equivalent: the 13 tests would have failed against an empty implementation (Task 1 RED state); they pass against the GREEN state from Task 1. Per Plan 04-03 task structure, Task 2 is a test-suite commit (not a fresh RED -> GREEN cycle on a different feature) -- mirrors Plan 04-02's structure.

REFACTOR phase skipped per task -- GREEN diff was small and stylistically clean on first commit; running tests after the type-ignore removal confirmed no behaviour drift.

## User Setup Required

None - no external service configuration required. All work is in-repo Python additions and unit tests against synthetic Pydantic fixtures (no CDSE / Earthdata / CDS API credentials needed).

## Next Phase Readiness

Wave 2 of Phase 4 complete. Plan 04-04 (Wave 3: eval-script rewire to write `eval-disp/metrics.json` + `eval-disp_egms/metrics.json` per the new DISPCellMetrics schema) can now consume the matrix_writer rendering -- once Plan 04-04 lands the cell metrics.json files, `make matrix` will render them via the DISP branch added in this plan.

Public API now exposed from `matrix_writer.py`:

- `from subsideo.validation.matrix_writer import _is_disp_cell_shape, _render_disp_cell` -- both symbols available (although they're underscore-prefixed module-private; the test file imports them via the module-internal path, mirroring `_render_cslc_selfconsist_cell` precedent).
- `write_matrix(manifest_path, out_path)` continues to be the public entry point; the new DISP branch is dispatched automatically based on the metrics.json shape.

No blockers. Threat-flag dispositions match the plan's threat_model:

- **T-04-03-01 (Tampering / _is_disp_cell_shape)** mitigated by `try/except (OSError, ValueError)` returning False on parse failure (matches `_is_cslc_selfconsist_shape` pattern).
- **T-04-03-02 (Tampering / _render_disp_cell)** mitigated by `try/except Exception` on `DISPCellMetrics.model_validate_json` returning None; write_matrix falls through to default RUN_FAILED rendering.
- **T-04-03-03 (Information disclosure / rendered cells)** accepted -- only measurements rendered via existing `_render_measurement`; no PII; no credentials in metrics.json by Phase 1 design.
- **T-04-03-04 (Denial of service / DISP dispatch order)** mitigated -- DISP check is BEFORE CSLC + RTC-EU; constant-time work per cell (single JSON parse + Pydantic validation).

## Self-Check: PASSED

Verifications performed before writing this section:

- **Files exist:**
  - `src/subsideo/validation/matrix_writer.py` -- FOUND (579 LOC; 475 -> 579; +104 net)
  - `tests/reference_agreement/test_matrix_writer_disp.py` -- FOUND (257 LOC, new)
- **All 3 commits exist in git log:**
  - `e5b5361` (Task 1 RED) -- FOUND
  - `488282e` (Task 1 GREEN) -- FOUND
  - `7d6e178` (Task 2) -- FOUND
- **All 13 plan tests pass** under `/Users/alex/.local/share/mamba/envs/subsideo/bin/python -m pytest tests/reference_agreement/test_matrix_writer_disp.py -v --no-cov` (functionally identical to `micromamba run -n subsideo pytest ...`).
- **DISP dispatch BEFORE CSLC self-consist:** verified -- DISP at line 476, CSLC at line 491; 476 < 491.
- **Public API imports succeed:** `python -c "from subsideo.validation.matrix_writer import write_matrix, _is_disp_cell_shape, _render_disp_cell"` exits 0.
- **Existing v1.0 matrix_writer behaviour preserved:** `tests/unit/test_matrix_writer.py` all 24 tests pass; `tests/product_quality/test_matrix_schema_disp.py` all 8 Plan 04-01 tests pass; `tests/reference_agreement/` 33 tests + new 13 tests = 46 pass; broader regression check across reference_agreement + matrix tests = 74 pass.
- **Ruff clean** on both touched files.
- **Mypy clean** on test file (0 errors); matrix_writer.py preserves the pre-existing baseline (1 `[import-untyped]` error on line 27 about `yaml` -- existed before this plan; not introduced by these changes).
- **`_render_measurement` reuse count = 5** (def at line 73 + default-branch use at line 119 + 1 CSLC self-consist + 1 RTC-EU + 1 DISP-cell new use at line 432).
- **Schema-discriminator dispatch ordering invariant:** DISP `ramp_attribution`, CSLC `per_aoi`, RTC-EU `per_burst` are structurally disjoint per the matrix_schema.py Pydantic types -- no JSON file can have all three keys simultaneously without an extra='forbid' violation, so the dispatch order is correctness-equivalent regardless of position. The position is enforced for the (inevitable) Phase 5+ schemas that may co-occur with one of these markers.

---
*Phase: 04-disp-s1-comparison-adapter-honest-fail*
*Completed: 2026-04-25*
