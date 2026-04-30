---
phase: 04-disp-s1-comparison-adapter-honest-fail
plan: 01
subsystem: validation
tags: [insar, validation, pydantic, ramp-attribution, planar-fit, coherence-stack, scipy.stats.circstd]

# Dependency graph
requires:
  - phase: 03-cslc-s1-self-consistency-eu-validation
    provides: selfconsistency.py (coherence_stats + residual_mean_velocity + compute_residual_velocity); inner-scope _compute_ifg_coherence_stack source body in run_eval_cslc_selfconsist_nam.py
  - phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
    provides: matrix_schema.py base types (MetricsJson, ProductQualityResultJson, ReferenceAgreementResultJson) — D-09 big-bang lock-in
provides:
  - "selfconsistency.fit_planar_ramp + compute_ramp_aggregate + auto_attribute_ramp (3 ramp-attribution helpers, numpy + scipy.stats.circstd)"
  - "selfconsistency.compute_ifg_coherence_stack (public API; B1 root-cause fix promoting the inner-scope helper)"
  - "selfconsistency._load_cslc_hdf5 (module-private CSLC HDF5 reader sibling)"
  - "matrix_schema.PerIFGRamp + RampAggregate + RampAttribution + DISPProductQualityResultJson + DISPCellMetrics (5 Pydantic v2 types)"
  - "matrix_schema type aliases: CoherenceSource, AttributedSource, DISPCellStatus"
affects: [04-02-prepare-for-reference, 04-03-matrix-writer-render, 04-04-eval-scripts-rerun, 04-05-conclusions-doc-brief]

# Tech tracking
tech-stack:
  added:
    - "scipy.stats.circstd (lazy-imported; existing transitive dep — not new install)"
  patterns:
    - "Plain-dict aggregate returns (compute_ramp_aggregate) to avoid circular import between selfconsistency.py and matrix_schema.py — caller converts to RampAggregate Pydantic at write time"
    - "Public-API promotion via underscore drop + sibling module-private helper extraction (_compute_ifg_coherence_stack inner-scope -> compute_ifg_coherence_stack module-level + _load_cslc_hdf5)"
    - "Type-alias-first Literal export (CoherenceSource / AttributedSource / DISPCellStatus declared at module top before the BaseModel classes that use them — improves IDE hover + matrix_writer reuse)"

key-files:
  created:
    - "tests/product_quality/test_selfconsistency_ramp.py"
    - "tests/product_quality/test_matrix_schema_disp.py"
    - "tests/product_quality/test_selfconsistency_coherence_stack.py"
  modified:
    - "src/subsideo/validation/selfconsistency.py"
    - "src/subsideo/validation/matrix_schema.py"
    - "run_eval_cslc_selfconsist_nam.py"

key-decisions:
  - "compute_ramp_aggregate returns plain dict[str, float | int] (not RampAggregate Pydantic) to avoid a circular import between selfconsistency.py and matrix_schema.py; caller in run_eval_disp.py converts to the model at write time"
  - "_load_cslc_hdf5 uses np.asarray(..., dtype=np.complex64) instead of (...).astype(...) to satisfy mypy [no-any-return] given h5py's typeless return"
  - "auto_attribute_ramp Literal includes 'tropospheric' but the deterministic rule never returns it — reserved for diagnostic (c) ERA5 toggle (deferred per CONTEXT D-09); the type signature documents the full attribution space without code-path inflation"

patterns-established:
  - "Lazy scipy.stats.circstd import pattern: lazy `from scipy.stats import circstd  # lazy` inside aggregate functions to keep selfconsistency.py module top numpy-only"
  - "Per-IFG NaN-fill discipline: helpers that operate on stacks (fit_planar_ramp, compute_ramp_aggregate) NaN-fill per-IFG entries when input is degenerate (<100 valid pixels OR <3 finite IFGs), preserving stack shape so downstream aggregation can count finite entries"
  - "Public-API promotion of inner-scope eval-script helpers: when a Wave-N plan needs an eval-script-local helper, the helper is promoted to a public selfconsistency.py / matrix_schema.py / etc. symbol BEFORE Wave-N starts (not as part of Wave-N itself); enables Wave-N execution without import gymnastics"

requirements-completed: [DISP-02, DISP-03]

# Metrics
duration: 10min
completed: 2026-04-25
---

# Phase 04 Plan 01: Foundation — Pydantic schemas + selfconsistency primitives Summary

**3 ramp-attribution numpy helpers + 5 Pydantic v2 DISP cell-metrics types + `compute_ifg_coherence_stack` extracted from inner-scope to public API; 19 unit tests green; ruff clean; eval script rewired for Plan 04-04 imports.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-25T06:52:56Z
- **Completed:** 2026-04-25T07:02:49Z
- **Tasks:** 3 (all TDD: RED → GREEN, no REFACTOR needed)
- **Files modified/created:** 6 (3 source modified, 3 tests created)

## Accomplishments

- `fit_planar_ramp` (numpy least-squares plane fit on per-IFG unwrapped stack) plus `compute_ramp_aggregate` (mean magnitude, scipy.stats.circstd direction-stability sigma, Pearson r vs coherence) plus `auto_attribute_ramp` (deterministic 4-branch rule with cutoffs at 30 deg / 0.5 r per CONTEXT D-Claude's-Discretion) added to `selfconsistency.py` as additive top-level functions.
- 5 Pydantic v2 types (`PerIFGRamp` / `RampAggregate` / `RampAttribution` / `DISPProductQualityResultJson` / `DISPCellMetrics`) plus 3 Literal type aliases (`CoherenceSource` / `AttributedSource` / `DISPCellStatus`) appended to `matrix_schema.py` after the existing `CSLCSelfConsistEUCellMetrics` block. All types use `ConfigDict(extra="forbid")` per Phase 1 D-09. No edits to existing classes.
- B1 root-cause fix: `_compute_ifg_coherence_stack` (formerly defined at column-4 indent inside `if __name__ == "__main__":` block of `run_eval_cslc_selfconsist_nam.py:487`) lifted into the new module-level public symbol `selfconsistency.compute_ifg_coherence_stack`. Nested `_load_cslc` closure promoted to sibling module-private helper `_load_cslc_hdf5`. Existing callsite + comment in eval script updated; module imports cleanly. Plan 04-04 can now `from subsideo.validation.selfconsistency import compute_ifg_coherence_stack` instead of grepping the unreachable inner-scope symbol.
- Module charter docstring of `selfconsistency.py` broadened per CONTEXT D-10 from "Sequential-IFG coherence statistics + reference-frame aligned residual" to "Sequential-IFG self-consistency primitives" covering all four primitive families.

## Task Commits

Each task was developed via TDD (RED test commit → GREEN implementation commit) and committed atomically:

1. **Task 1 RED — failing tests for ramp-attribution helpers** — `241e58f` (test)
2. **Task 1 GREEN — fit_planar_ramp + compute_ramp_aggregate + auto_attribute_ramp** — `5c3d4f9` (feat)
3. **Task 2 RED — failing schema tests for DISP cell metrics** — `93f8ef5` (test)
4. **Task 2 GREEN — 5 Pydantic v2 DISP cell-metrics types + 3 Literal aliases** — `4e293ef` (feat)
5. **Task 3 RED — failing tests for compute_ifg_coherence_stack** — `3bf73e5` (test)
6. **Task 3 GREEN — public API promotion + caller rewire** — `6d3a795` (refactor)

_TDD plan-level gate sequence (test → feat/refactor) holds for each task; refactor was unnecessary because the GREEN diffs were minimal and stylistically clean on first commit._

## Files Created/Modified

- **`src/subsideo/validation/selfconsistency.py`** (modified) — module charter docstring broadened; appended `fit_planar_ramp`, `compute_ramp_aggregate`, `auto_attribute_ramp`, `_load_cslc_hdf5`, `compute_ifg_coherence_stack` at module top-level. +197 lines net.
- **`src/subsideo/validation/matrix_schema.py`** (modified) — appended 3 Literal aliases (`CoherenceSource`, `AttributedSource`, `DISPCellStatus`) + 5 BaseModel classes (`PerIFGRamp`, `RampAggregate`, `RampAttribution`, `DISPProductQualityResultJson`, `DISPCellMetrics`) at end of file (after `CSLCSelfConsistEUCellMetrics`). +179 lines.
- **`run_eval_cslc_selfconsist_nam.py`** (modified) — added `compute_ifg_coherence_stack` to existing `from subsideo.validation.selfconsistency import (...)` block; deleted inner-scope `_compute_ifg_coherence_stack` def (lines 487–564) including its nested `_load_cslc` closure; updated callsite at line 940 from `_compute_ifg_coherence_stack(...)` to `compute_ifg_coherence_stack(...)`; updated in-comment reference at line 205. Net -78 / +5 lines.
- **`tests/product_quality/test_selfconsistency_ramp.py`** (created, 138 LOC) — 8 tests: synthetic ramp recovery (1), insufficient pixel NaN edge (1), 3-D rejection (1), mask honoring (1), aggregate few-finite NaN (1), aggregate finite (1), 4-branch attribution table (1), custom cutoff override (1).
- **`tests/product_quality/test_matrix_schema_disp.py`** (created, 173 LOC) — 8 tests: round-trip (1), parametrized extra=forbid (2 via parametrize), Literal validation on coherence_source / attributed_source / cell_status (3), inheritance check (1), required-field check (1).
- **`tests/product_quality/test_selfconsistency_coherence_stack.py`** (created, 88 LOC) — 3 tests: 3-epoch round-trip (1), <2-epoch raise (1), NaN-block non-propagation (1).

## Decisions Made

- **`compute_ramp_aggregate` returns plain dict, not `RampAggregate` Pydantic** — avoids circular import between `selfconsistency.py` (would need to import `RampAggregate` from `matrix_schema.py`) and `matrix_schema.py` (which imports from nothing else in validation). Caller in `run_eval_disp.py` (Plan 04-04) converts dict → `RampAggregate` at metrics.json write time. Decision logged here so Plan 04-04 doesn't repeat the analysis.
- **`_load_cslc_hdf5` uses `np.asarray(..., dtype=np.complex64)` instead of `(...).astype(...)`** — fixes mypy `[no-any-return]` on the h5py-sourced array (h5py returns `Any` because of `ignore_missing_imports=True`). Behaviour identical; mypy diagnostic clean. The pre-existing `compute_residual_velocity` at line 261 still uses `.astype()` — left untouched per the additive-only constraint.
- **`auto_attribute_ramp` Literal advertises `'tropospheric'` despite never returning it** — the type signature documents the full attribution space (matches `AttributedSource` Literal in `matrix_schema.py`), so callers can compare-on-equality with all valid labels. The deterministic rule never produces `'tropospheric'` per CONTEXT D-12 — reserved for diagnostic (c) (ERA5 toggle, deferred per D-09). Encoded in the docstring rule list.

## Deviations from Plan

None - plan executed exactly as written. The plan's task-by-task verbatim Python code blocks were faithful to the final implementation; only mechanical adjustments needed (variable renames `X`/`Y`/`A` → `xx`/`yy`/`design_matrix` for ruff N806 conformance, plus `np.asarray` swap for mypy `[no-any-return]`). These are formatting fixes, not deviations from plan intent.

## Issues Encountered

- **Ruff N806 (uppercase variable names)** — `Y, X = np.indices(...)` uses uppercase per math convention but ruff's `N806` rule in this project flags it. Fix: renamed to `yy, xx` (matrix indices) and `design_matrix` (lstsq design). Same fix in test fixtures.
- **Ruff E501 (line >100)** — module charter docstring's first line was 225 chars; broken into title-line + paragraph. One test comment was 107 chars; wrapped to 2 lines.
- **Mypy `[no-any-return]` on `_load_cslc_hdf5`** — h5py's `f[dset_path][:].astype(np.complex64)` returns `Any` because `ignore_missing_imports=True` strips h5py types. Fix: replaced with `np.asarray(f[dset_path][:], dtype=np.complex64)` (numpy is fully typed). All other mypy errors are the pre-existing `[type-arg]` pattern (bare `np.ndarray` without type args), present in the module before this plan's changes; baseline preserved.

## TDD Gate Compliance

Plan-level TDD gate sequence per task:

- **Task 1 RED gate (`241e58f`)** — `test(04-01): add failing tests for ramp-attribution helpers` confirmed failing on `from subsideo.validation.selfconsistency import (auto_attribute_ramp, ...)` ImportError before implementation.
- **Task 1 GREEN gate (`5c3d4f9`)** — `feat(04-01): add ramp-attribution helpers to selfconsistency.py`; 8/8 tests pass.
- **Task 2 RED gate (`93f8ef5`)** — `test(04-01): add failing schema tests for DISP cell metrics` confirmed failing on `from subsideo.validation.matrix_schema import (DISPCellMetrics, ...)` ImportError.
- **Task 2 GREEN gate (`4e293ef`)** — `feat(04-01): add 5 Pydantic v2 DISP cell-metrics types`; 8/8 tests pass.
- **Task 3 RED gate (`3bf73e5`)** — `test(04-01): add failing tests for compute_ifg_coherence_stack` confirmed failing on `from subsideo.validation.selfconsistency import compute_ifg_coherence_stack` ImportError.
- **Task 3 GREEN gate (`6d3a795`)** — `refactor(04-01): promote _compute_ifg_coherence_stack to public API`; 3/3 tests pass; eval script smoke test (`python -c "import run_eval_cslc_selfconsist_nam"`) succeeds.

REFACTOR phase skipped per task — GREEN diffs were small and stylistically clean on first commit; running tests after each ruff/mypy correction confirmed no behaviour drift.

## User Setup Required

None - no external service configuration required. All work is in-repo Python additions and unit tests against synthetic fixtures (no CDSE / Earthdata / CDS API credentials needed).

## Next Phase Readiness

Wave 1 of Phase 4 complete on this plan. Plan 04-02 (Wave 1 sibling) is independent and can run in parallel. Plan 04-03 (Wave 2) depends on the new `matrix_schema.py` types — DISPCellMetrics is now importable. Plan 04-04 (Wave 3) depends on `compute_ifg_coherence_stack` being a public symbol — B1 root-cause fix is complete and the import path `from subsideo.validation.selfconsistency import compute_ifg_coherence_stack` is verified.

No blockers. No threat-flag surfaces introduced (helpers operate on numpy arrays + h5py reads with the same trust posture as Phase 3).

## Self-Check: PASSED

Verifications performed before writing this section:

- **All test files exist:**
  - `tests/product_quality/test_selfconsistency_ramp.py` — FOUND
  - `tests/product_quality/test_matrix_schema_disp.py` — FOUND
  - `tests/product_quality/test_selfconsistency_coherence_stack.py` — FOUND
- **All 6 commits exist in git log:**
  - `241e58f` (Task 1 RED) — FOUND
  - `5c3d4f9` (Task 1 GREEN) — FOUND
  - `93f8ef5` (Task 2 RED) — FOUND
  - `4e293ef` (Task 2 GREEN) — FOUND
  - `3bf73e5` (Task 3 RED) — FOUND
  - `6d3a795` (Task 3 GREEN) — FOUND
- **All 19 plan tests pass** (3 + 8 + 8 = 19) under `micromamba run -n subsideo python -m pytest tests/product_quality/test_selfconsistency_ramp.py tests/product_quality/test_matrix_schema_disp.py tests/product_quality/test_selfconsistency_coherence_stack.py`
- **Ruff clean** on all 6 touched files (3 source + 3 test).
- **Mypy state matches baseline** — pre-existing 7 `[type-arg]` errors on bare `np.ndarray` annotations preserved; new code adds 7 more occurrences of the SAME pattern (consistent with existing module style); no new error categories introduced.
- **Caller smoke test passes:** `python -c "import run_eval_cslc_selfconsist_nam"` exits 0 (no `ImportError` / `NameError` after deletion of inner-scope helper).
- **Public symbol importable:** `python -c "from subsideo.validation.selfconsistency import compute_ifg_coherence_stack"` exits 0 with non-empty docstring.
- **No regressions in pre-existing tests** — 7 existing `test_compare_disp.py` tests + 10 other product_quality tests pass under no-disp/ramp/coherence_stack filter.

---
*Phase: 04-disp-s1-comparison-adapter-honest-fail*
*Completed: 2026-04-25*
