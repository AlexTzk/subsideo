---
phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
plan: 08
subsystem: validation
tags: [pydantic-v2, yaml, matrix-writer, results-matrix, markdown, guardrail, gate-03, env-09]

# Dependency graph
requires:
  - phase: 01
    provides: "CRITERIA registry (01-05), ProductQualityResult / ReferenceAgreementResult / measurement_key (01-05), evaluate (01-05)"
provides:
  - "MetaJson + MetricsJson Pydantic v2 sidecar schema (validation/matrix_schema.py)"
  - "write_matrix function + CLI entry (validation/matrix_writer.py)"
  - "Hand-edited 10-cell matrix manifest (results/matrix_manifest.yml)"
  - "Threshold-echo drift-visibility mechanism (D-03) via rendered matrix.md"
  - "CALIBRATING-cell italics rendering (GATE-03)"
affects: [01-07 Makefile results-matrix target, Phase 2 RTC EU, Phase 3 CSLC, Phase 4 DISP, Phase 5 DIST, Phase 6 DSWx, Phase 7 release audit, eval-script metrics.json writers]

# Tech tracking
tech-stack:
  added: [pydantic-v2 BaseModel (sidecar schemas), yaml.safe_load (manifest reader)]
  patterns:
    - "Pydantic v2 BaseModel with extra='forbid' + schema_version field (forward-compat hook)"
    - "Manifest + typed sidecars as matrix-source (never glob CONCLUSIONS_*.md, PITFALLS R3/R5)"
    - "Threshold echo in rendered output makes criteria drift visible in git diff (D-03)"
    - "Missing-sidecar renders RUN_FAILED per-cell; other cells keep rendering (ENV-09 isolation)"
    - "Public measurement_key reused across results.py + matrix_writer.py (single source of truth)"

key-files:
  created:
    - src/subsideo/validation/matrix_schema.py
    - src/subsideo/validation/matrix_writer.py
    - results/matrix_manifest.yml
    - tests/unit/test_matrix_schema.py
    - tests/unit/test_matrix_writer.py
  modified:
    - src/subsideo/validation/__init__.py

key-decisions:
  - "Italics-wrap entire cell (vs per-criterion) when ANY criterion is CALIBRATING -- single glance distinguishes release-gating from tuning"
  - "Appended (CALIBRATING) to verdict string in addition to outer italics -- belt-and-braces so a plaintext log dump still surfaces the tag"
  - "Escape pipe chars in cell text (_escape_table_cell) -- defensive against future reason strings containing | that would split the Markdown table"
  - "RUN_FAILED carries per-cell reason in the PQ column (e.g. 'metrics.json missing') but shows plain 'RUN_FAILED' in the RA column -- keeps table compact while preserving diagnostic context"
  - "Malformed JSON catches all Exception (not just ValidationError) and logs + returns None + reason string -- one bad sidecar cannot crash the whole matrix render (ENV-09)"

patterns-established:
  - "Matrix-writer imports ONLY subsideo.validation.{criteria,matrix_schema,results} + stdlib + yaml + loguru -- zero subsideo.products.* imports (respects ARCHITECTURE §Failure-Mode Boundaries)"
  - "Module-level _COMPARATOR_FNS dict for <, <=, >, >= evaluation -- mirrors results.py style, avoids duplicating the operator lookup"
  - "CLI pattern: main() -> int with sys.exit(main()) under __main__ guard -- matches validation/supervisor.py (Plan 01-07) convention"

requirements-completed: [ENV-09, GATE-03]

# Metrics
duration: 18min
completed: 2026-04-22
---

# Phase 1 Plan 08: Matrix Writer Summary

**Manifest-driven `results/matrix.md` generator with Pydantic v2 sidecar schemas (MetaJson/MetricsJson), CRITERIA threshold echo (D-03), CALIBRATING italics (GATE-03), and RUN_FAILED per-cell isolation (ENV-09).**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-04-22T15:13:00Z
- **Completed:** 2026-04-22T15:20:30Z
- **Tasks:** 4 completed (Task 1, 3 followed TDD RED/GREEN flow)
- **Files created:** 5 (2 src + 2 tests + 1 YAML manifest)
- **Files modified:** 1 (validation/__init__.py — 5 entries added to 17 preserved)

## Accomplishments

- **Pydantic v2 sidecar schema** (`matrix_schema.py`, 152 lines) declaring MetaJson + MetricsJson + two nested sub-schemas; `extra='forbid'` strict parsing; `schema_version: int = 1` forward-compat hook on both top-level models.
- **Matrix writer** (`matrix_writer.py`, 198 lines) reading manifest + per-cell sidecars, emitting a two-column Markdown table (Product-quality | Reference-agreement) with every measurement echoed alongside its comparator + threshold + PASS/FAIL verdict, and `*...*` italics wrapping any cell containing a CALIBRATING criterion.
- **10-cell manifest** (`results/matrix_manifest.yml`): 5 products × 2 regions, with each cell carrying `eval_script`, `cache_dir`, `metrics_file`, `meta_file`, `conclusions_doc` (the last being informational-only — the writer never parses CONCLUSIONS_*.md).
- **14/14 tests pass** covering round-trip serialisation, required-field validation, CALIBRATING italics, threshold echo (PASS + FAIL paths), missing-sidecar RUN_FAILED, malformed-JSON tolerance, and CLI end-to-end.
- **Package re-exports**: `MetaJson`, `MetricsJson`, `ProductQualityResultJson`, `ReferenceAgreementResultJson`, `write_matrix` added to `validation/__init__.py` alphabetically; all 17 prior-plan entries preserved (total `__all__` = 22).

## Task Commits

Each task was committed atomically (all commits used `--no-verify` per parallel-execution protocol):

1. **Task 1 (TDD): matrix_schema.py Pydantic v2 models**
   - RED: `4f320dc` — test(01-08): add failing tests for matrix_schema sidecar models
   - GREEN: `f71e969` — feat(01-08): add matrix_schema Pydantic v2 sidecar models
2. **Task 2: matrix_manifest.yml 10-cell registry**
   - `c278bda` — feat(01-08): add results/matrix_manifest.yml 10-cell registry
3. **Task 3 (TDD): matrix_writer.py**
   - RED: `a1a02aa` — test(01-08): add failing tests for matrix_writer
   - GREEN: `a476e40` — feat(01-08): add matrix_writer for manifest-driven results/matrix.md
4. **Task 4: re-export from validation/__init__.py**
   - `64dfcc5` — feat(01-08): re-export matrix_schema + matrix_writer from validation package

## Files Created/Modified

**Created:**
- `src/subsideo/validation/matrix_schema.py` (152 lines) — MetaJson (provenance), MetricsJson (scientific), ProductQualityResultJson + ReferenceAgreementResultJson (nested sub-schemas). All extra='forbid', schema_version=1 defaults on top-level models.
- `src/subsideo/validation/matrix_writer.py` (198 lines) — `write_matrix(manifest_path, out_path)` + `main()` CLI; reads manifest, loops cells, loads per-cell `MetricsJson`, renders two columns with threshold echoes; `--manifest` / `--out` argparse flags.
- `results/matrix_manifest.yml` (97 lines) — hand-edited 10-cell registry; schema_version:1; 5 products × 2 regions; each cell carries eval_script/cache_dir/metrics_file/meta_file/conclusions_doc.
- `tests/unit/test_matrix_schema.py` (111 lines) — 7 tests: round-trip, required-field, extra-forbidden, default-empty, schema_version default, nested-schema extra-forbidden.
- `tests/unit/test_matrix_writer.py` (211 lines) — 7 tests: missing-sidecar RUN_FAILED, populated PASS rendering, CALIBRATING italics, CLI entry, malformed-JSON tolerance, BINDING PASS (no italics), BINDING FAIL.

**Modified:**
- `src/subsideo/validation/__init__.py` (+13 lines) — added matrix_schema + matrix_writer imports + 5 new `__all__` entries alphabetically; all 17 prior-plan re-exports preserved (CRITERIA, Criterion, RETRY_POLICY, ReferenceDownloadError, bounds_for_burst, bounds_for_mgrs_tile, build_stable_mask, coherence_stats, credential_preflight, download_reference_with_retry, ensure_resume_safe, evaluate, measurement_key, ProductQualityResult, ReferenceAgreementResult, residual_mean_velocity, select_opera_frame_by_utc_hour).

## Decisions Made

- **Italics-wrap entire cell** (not per-criterion) when ANY criterion in that column is CALIBRATING. Reason: D-03 intent is "at a glance, release-gating vs tuning" — mixing plain + italicised tokens on one row muddies the visual signal.
- **`(CALIBRATING)` tag inside verdict string** in addition to outer italics. Reason: a plain-text dump (log capture, `grep`) still surfaces the distinction even when Markdown italics are stripped.
- **`_escape_table_cell(text)` pipe-char escape** applied to every cell body. Reason: defence-in-depth — future RUN_FAILED reason strings or criterion names could include `|`, which would silently split the Markdown table.
- **`RUN_FAILED ({reason})` in PQ column, plain `RUN_FAILED` in RA column** when sidecar is missing/malformed. Reason: reason string is per-cell context, not per-column; duplicating it would bloat the table. A downstream reader sees RUN_FAILED twice + one reason — unambiguous.
- **Broad `except Exception` in `_load_metrics`** (not just `ValidationError`) plus `logger.warning + return None, reason`. Reason: JSON decode errors are `json.JSONDecodeError`, Pydantic raises `ValidationError`, future schema versions might raise `ValueError`. ENV-09 per-cell isolation means one bad sidecar must never crash the whole matrix render.
- **Public `measurement_key` import** from `subsideo.validation.results` (not a private re-implementation). Reason: Plan 01-05 explicitly promoted this to the public API for exactly this reuse scenario; a matrix_writer-local helper would be a D-03 drift risk (two places defining "strip `_min`/`_max` from the last dot-segment" — they could disagree).

## Deviations from Plan

None — plan executed exactly as written, with three small tactical enhancements that remained within the plan's stated behaviour requirements:

- Added `_escape_table_cell` helper for pipe-char escape (not explicitly called out in the plan but necessary to keep the Markdown table well-formed when reason strings contain `|`).
- Split `_load_metrics` return type to `tuple[MetricsJson | None, str | None]` so the RUN_FAILED cell can carry a human-readable reason (plan's acceptance criterion said "brief reason").
- Added two extra test cases (`test_malformed_metrics_json_renders_run_failed`, `test_threshold_echo_binding_fail`) beyond the plan's 4 listed tests to cover the malformed-JSON path and the BINDING-FAIL verdict path.

## Issues Encountered

- **Worktree base mismatch**: The worktree was initialised at commit `eff433b` but the expected base (per the prompt) was `3ee4d9f`. Resolved by running the `<worktree_branch_check>` hard-reset, which moved HEAD to `3ee4d9f` (the main-branch tip with Plans 01-04/05/06/07 already landed). No work lost — the reset happened before any file edits in this plan.
- **Bash tool rejected `VAR=value <cmd>` prefix syntax**: PYTHONPATH needed to be set to point at the worktree's `src/` directory (the editable install pointed at the main repo's `src/`, not the worktree). Worked around by invoking pytest via `python -c "import sys; sys.path.insert(0, '...'); import pytest; pytest.main(...)"`. No code change needed; tests ran cleanly.
- **Ruff format modifications** after initial write: ruff formatted all 3 new Python files on first pass (blank line after module docstring, trailing comma on multi-line dict), requiring a second read+edit cycle per file. All final files pass `ruff check` and `ruff format --check` cleanly.

## User Setup Required

None — matrix_writer runs against the committed manifest + any metrics.json sidecars written by future eval-script runs. No env vars, credentials, or external services required for Plan 01-08 itself.

## Verification Evidence

- `python -c "from subsideo.validation import MetaJson, MetricsJson, write_matrix"` → succeeds
- `python -c "from subsideo.validation import CRITERIA, evaluate, bounds_for_burst, ..."` (prior-plan re-exports) → succeeds
- `python -m subsideo.validation.matrix_writer --manifest results/matrix_manifest.yml --out /tmp/matrix.md` → exit 0; 10 cells render (all `RUN_FAILED` in Phase 1, expected pre-eval state)
- `pytest tests/unit/test_matrix_schema.py tests/unit/test_matrix_writer.py -q` → 14/14 pass
- `ruff check src/subsideo/validation/matrix_schema.py src/subsideo/validation/matrix_writer.py tests/unit/test_matrix_schema.py tests/unit/test_matrix_writer.py` → clean
- `ruff format --check ...` → clean
- `grep '_measurement_key' src/subsideo/validation/matrix_writer.py` → zero hits (public `measurement_key` only)
- `grep -E "^(from|import) subsideo\\.products" src/subsideo/validation/matrix_writer.py` → zero hits (no disallowed imports)

## Next Phase Readiness

- **Plan 01-07 `make results-matrix`**: The Makefile target can now invoke `python -m subsideo.validation.matrix_writer --out results/matrix.md` to regenerate the matrix. Plan 01-07 landed the supervisor + Makefile in a parallel worktree; this plan delivers the matrix writer it invokes.
- **Phase 2+ eval-script writers**: The MetaJson + MetricsJson Pydantic v2 contract is the stable target for eval scripts to emit. Any `run_eval_*.py` needs to produce `{cache_dir}/meta.json` + `{cache_dir}/metrics.json` matching these schemas for its matrix cell to render values (not RUN_FAILED).
- **Criteria drift audit**: A future edit to `validation/criteria.py` (e.g. changing `rtc.rmse_db_max` from 0.5 to 0.45) automatically produces a diff in `results/matrix.md` the next time it is regenerated, even when measurements are unchanged — the `< 0.5 PASS` / `< 0.45 PASS` substring change is the D-03 drift signal.

## Self-Check: PASSED

**Files verified:**
- FOUND: `src/subsideo/validation/matrix_schema.py` (152 lines, >= 80 min)
- FOUND: `src/subsideo/validation/matrix_writer.py` (198 lines, >= 150 min)
- FOUND: `results/matrix_manifest.yml` (10 cells validated)
- FOUND: `tests/unit/test_matrix_schema.py` (7 tests)
- FOUND: `tests/unit/test_matrix_writer.py` (7 tests)
- FOUND: `src/subsideo/validation/__init__.py` (22 `__all__` entries; 17 preserved + 5 added)

**Commits verified:**
- FOUND: `4f320dc` (test RED for matrix_schema)
- FOUND: `f71e969` (feat GREEN for matrix_schema)
- FOUND: `c278bda` (feat manifest)
- FOUND: `a1a02aa` (test RED for matrix_writer)
- FOUND: `a476e40` (feat GREEN for matrix_writer)
- FOUND: `64dfcc5` (feat __init__ re-exports)

**TDD gate compliance:**
- Task 1 (tdd="true"): RED gate `4f320dc` (test-only) → GREEN gate `f71e969` (feat) — ✓
- Task 3 (tdd="true"): RED gate `a1a02aa` (test-only) → GREEN gate `a476e40` (feat) — ✓

---
*Phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding*
*Plan: 08*
*Completed: 2026-04-22*
