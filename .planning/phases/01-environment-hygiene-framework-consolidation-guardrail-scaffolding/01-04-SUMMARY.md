---
phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
plan: 04
subsystem: validation
tags:
  - validation
  - cslc
  - disp
  - stable-terrain
  - coherence
  - self-consistency
  - pure-function-module
requirements_completed:
  - CSLC-01
  - CSLC-02
dependencies:
  requires: []
  provides:
    - "build_stable_mask pure-function mask constructor (CSLC-01)"
    - "coherence_stats 5-key statistics dict (CSLC-02 + P2.2)"
    - "residual_mean_velocity reference-frame aligned residual (P2.3)"
  affects:
    - "src/subsideo/validation/__init__.py (newly populated)"
tech_stack:
  added: []
  patterns:
    - "Pure-function numpy helpers (validation/metrics.py precedent)"
    - "TYPE_CHECKING + TypeAlias for conda-forge-only type annotations"
    - "Lazy import of geopandas/shapely/rasterio inside function bodies"
    - "Loguru brace-style debug logging"
key_files:
  created:
    - src/subsideo/validation/stable_terrain.py
    - src/subsideo/validation/selfconsistency.py
    - tests/unit/test_stable_terrain.py
    - tests/unit/test_selfconsistency.py
  modified:
    - src/subsideo/validation/__init__.py
decisions:
  - "Threat T-04-01 (mitigated): enforce CSLC-01 defaults (5 km coast, 500 m water, slope<=10 deg) via module constants; narrow via kwargs"
  - "Threat T-04-02 (mitigated): coherence_stats ships all 5 candidate statistics so Phase 3 can pick the calibration bar without another dataclass edit (PITFALLS P2.2)"
  - "Threat T-04-03 (mitigated): residual_mean_velocity subtracts the stable-mask median (default) before averaging -- reference-frame alignment per PITFALLS P2.3"
  - "Threat T-04-04 (mitigated): coherence_stats returns zeros on empty mask; residual_mean_velocity raises ValueError so callers handle the gate explicitly"
  - "Threat T-04-05 (mitigated): only numpy + loguru at module top; geopandas/shapely/rasterio lazy-imported inside _buffered_geometry_mask; TYPE_CHECKING block supplies annotations without runtime cost"
  - "Used TypeAlias (PEP 613) for GeometryLike / CRSLike so mypy --strict recognises the TYPE_CHECKING-defined union as a valid type"
  - "Explicit np.asarray(..., dtype=bool) returns to satisfy numpy's no-any-return under mypy --strict"
metrics:
  duration_seconds: 856
  duration_min: 14
  tasks_completed: 3
  commits: 7
  files_created: 4
  files_modified: 1
  tests_added: 25
  tests_passing: 25
completed_at: "2026-04-22T14:23:04Z"
---

# Phase 01 Plan 04: Shared Stable-Terrain & Self-Consistency Modules Summary

## One-liner

Ships `validation/stable_terrain.build_stable_mask` (CSLC-01: WorldCover class 60 + slope<=10deg + 5 km coast + 500 m water buffers) and `validation/selfconsistency.{coherence_stats,residual_mean_velocity}` (CSLC-02 + P2.2/P2.3: 5-key coherence dict + reference-frame-aligned residual) as pure-function numpy modules consumed by Phase 3 CSLC and Phase 4 DISP self-consistency gates.

## What Changed

### Task 1: `validation/stable_terrain.py` + unit tests

Created 208-line pure-function module exposing `build_stable_mask(worldcover, slope_deg, coastline=None, waterbodies=None, *, transform=None, crs=None, coast_buffer_m=5000, water_buffer_m=500, slope_max_deg=10.0)`.

Implements the four CSLC-01 exclusion criteria:

1. **WorldCover class filter** — keep only pixels where `worldcover == 60` (bare/sparse vegetation, the ESA WorldCover v2 stable class).
2. **Slope gate** — keep only pixels where `slope_deg <= 10` (NaN slopes excluded; handles layover/shadow on steep terrain).
3. **Coastline buffer** — rasterise `coastline.buffer(5000)` into an exclusion mask; mitigates tidal loading / soil moisture / wave spray decorrelation.
4. **Water-body buffer** — rasterise `waterbodies.buffer(500)` into an exclusion mask; mitigates reservoir-edge false-positives (PITFALLS P2.1).

Module constants `WORLDCOVER_BARE_SPARSE_CLASS=60`, `DEFAULT_SLOPE_MAX_DEG=10.0`, `DEFAULT_COAST_BUFFER_M=5000.0`, `DEFAULT_WATER_BUFFER_M=500.0` make the CSLC-01 defaults inspectable from downstream code.

Lazy-import discipline: only `numpy` and `loguru` at module top; `geopandas`, `shapely`, `rasterio` imported inside `_buffered_geometry_mask` so pip-install-only users can import the module without the conda-forge stack.

10 unit tests in `tests/unit/test_stable_terrain.py` cover: all-class-60 input, no-class-60 input, slope gate at default 10deg, slope gate tightened to 5deg, NaN-slope exclusion, shape-mismatch ValueError, CSLC-01 constant values, coast-buffer ring exclusion (geopandas importorskip), water-body ring exclusion (geopandas importorskip), and output dtype==np.bool_.

### Task 2: `validation/selfconsistency.py` + unit tests

Created 165-line pure-function module with two exported functions:

**`coherence_stats(ifgrams_stack, stable_mask, *, coherence_threshold=0.6) -> dict[str, float]`** — computes per-pixel time-mean coherence, then returns a dict with EXACTLY five keys:

- `mean` — mean of per-pixel time-mean over stable mask
- `median` — median of per-pixel time-mean over stable mask
- `p25`, `p75` — 25th / 75th percentiles of per-pixel time-mean
- `persistently_coherent_fraction` — fraction of stable-mask pixels whose per-IFG coherence exceeds `coherence_threshold` for EVERY interferogram in the stack

Returns all five so Phase 3 can pick the calibration bar (mean / median / persistent-fraction) without another dataclass edit — directly addresses PITFALLS P2.2 research-flagged planning decision. Empty mask returns zeros across the board (no crash). NaN coherence entries are treated as 0 both for time-mean and persistence checks.

**`residual_mean_velocity(velocity_mm_yr, stable_mask, *, frame_anchor='median') -> float`** — subtracts the stable-mask anchor from every pixel, then averages the centred values. Per PITFALLS P2.3, LOS velocity magnitudes are arbitrary; only the deviation from the stable-terrain reference is apples-to-apples. Default `frame_anchor='median'` is robust to stable-mask false-positives; `frame_anchor='mean'` supported via `Literal`. Empty mask raises `ValueError`; NaN velocity pixels excluded from residual.

15 unit tests in `tests/unit/test_selfconsistency.py` cover: exact 5-key return, all-floats invariant, empty-mask zeros, persistence threshold default 0.6, persistence threshold custom (0.5 vs 0.8), mean/median/p25/p75 arithmetic with a constructed stack, NaN-tolerance for coherence_stats, median anchor, mean anchor, all-zero input, non-zero skewed offset, empty-mask ValueError, invalid-anchor ValueError, NaN-tolerance for velocity, and docstring advertising the 5 keys.

### Task 3: `validation/__init__.py`

Populated the previously-empty (0 bytes) package init with re-exports so Phase 3/4 consumers can write `from subsideo.validation import build_stable_mask, coherence_stats, residual_mean_velocity`. `__all__` list is APPEND-safe — plans 01-05 (adding `ProductQualityResult`, `ReferenceAgreementResult`, `evaluate`) and 01-06 (adding harness helpers) append, never rewrite.

## Tasks Executed

| Task | Name                                                         | Commit  | Lines changed |
| ---- | ------------------------------------------------------------ | ------- | ------------- |
| 1a   | TDD RED: failing tests for build_stable_mask                 | f5ee814 | +157          |
| 1b   | TDD GREEN: implement build_stable_mask (CSLC-01)             | 12878e0 | +197          |
| 2a   | TDD RED: failing tests for coherence_stats + residual_mean_velocity | 1de484e | +185    |
| 2b   | TDD GREEN: implement coherence_stats + residual_mean_velocity (CSLC-02) | 178c4ff | +165 |
| 3    | Populate validation/__init__.py re-exports                   | 1687777 | +20           |
| R1   | REFACTOR: satisfy ruff ANN/N/F/I on new modules              | da4eb9c | +21/-12       |
| R2   | REFACTOR: satisfy mypy --strict on stable_terrain.py         | 7f43e72 | +6/-5         |

Two refactor commits (R1, R2) were produced under Rule 3 (auto-fix blocking issues) to bring the new modules into compliance with the project's baseline ruff + mypy configuration; see Deviations below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Lint/Type Errors] Brought new modules into ruff / mypy --strict compliance**

- **Found during:** Post-Task-3 verification
- **Issue:** The plan's `<action>` block used `Any` throughout for `coastline`, `waterbodies`, `transform`, `crs`, and `geometry` parameters. The project's ruff config (`pyproject.toml [tool.ruff.lint].select` includes `ANN`) rejects `Any` annotations with ANN401. Two test functions also left `gpd = pytest.importorskip(...)` assignments unused (F841). Mypy `--strict` additionally rejected the returned `mask.astype(bool)` / `raster.astype(bool)` as `no-any-return` and the `TYPE_CHECKING`-defined `GeometryLike` / `CRSLike` unions as non-type variables.
- **Fix:** Replaced `Any` with concrete types imported inside a `TYPE_CHECKING` block (`Affine`, `GeoSeries`, `BaseGeometry`, `rasterio.crs.CRS`, `pyproj.CRS`); annotated the unions with PEP 613 `TypeAlias`; wrapped mask returns in `np.asarray(..., dtype=bool)` assigned to typed `np.ndarray` locals; dropped the unused `gpd` assignments; silenced `N811` for the uppercase-to-mixed-case CRS import renames with per-line `# noqa: N811`.
- **Files modified:** `src/subsideo/validation/stable_terrain.py`, `tests/unit/test_stable_terrain.py`, `tests/unit/test_selfconsistency.py`
- **Commits:** `da4eb9c`, `7f43e72`

**2. [Rule 3 - Worktree Path Recovery] Recovered from early absolute-path leak into parent repo**

- **Found during:** Task 1 RED phase, after the first `Write` call
- **Issue:** The first implementation pass used absolute paths under `/Volumes/Geospatial/Geospatial/subsideo/...` which pointed to the parent checkout, not this worktree (which lives under `.claude/worktrees/agent-aa0ba1b2`). A stray test file was committed to the parent `main` branch as `84565a5`, and a stray `stable_terrain.py` landed untracked on the parent filesystem.
- **Fix:** Removed the untracked stray on the parent filesystem; ran `git revert 84565a5` on the parent `main` to undo only my commit (leaving the other parallel agent's `f0c2241` intact per the scope-boundary rule). Then redid Task 1 (RED + GREEN) inside the worktree using correct paths, producing the canonical commits on the `worktree-agent-aa0ba1b2` branch. No content lost.
- **Files modified:** None remaining on parent beyond the revert commit; all actual plan deliverables live on the worktree branch.
- **Commits on worktree (canonical):** `f5ee814`, `12878e0`, `1de484e`, `178c4ff`, `1687777`, `da4eb9c`, `7f43e72`.

## Authentication Gates

None — all tasks were fully automated in the subsideo micromamba env.

## Verification Summary

| Check                                                                         | Result |
| ----------------------------------------------------------------------------- | ------ |
| `from subsideo.validation import build_stable_mask, coherence_stats, residual_mean_velocity` | PASS |
| `pytest tests/unit/test_stable_terrain.py tests/unit/test_selfconsistency.py` | 25/25 PASS |
| `rg 'def build_stable_mask\|def coherence_stats\|def residual_mean_velocity' src/subsideo/validation/` | exactly 3 hits |
| `ruff check` on new/modified files                                            | PASS (all checks passed) |
| `mypy --strict --ignore-missing-imports` on new modules                       | PASS (0 errors across 3 files) |
| No `geopandas`/`rasterio`/`shapely` imports at module top of `stable_terrain.py` | PASS (top-level imports: `__future__`, `typing`, `numpy`, `loguru`) |
| No `geopandas`/`rasterio`/`shapely` imports at module top of `selfconsistency.py` | PASS (same four top-level imports) |
| `WORLDCOVER_BARE_SPARSE_CLASS == 60`                                          | PASS |
| `DEFAULT_COAST_BUFFER_M == 5000.0`                                            | PASS |
| `DEFAULT_WATER_BUFFER_M == 500.0`                                             | PASS |
| `DEFAULT_SLOPE_MAX_DEG == 10.0`                                               | PASS |
| `coherence_stats` returns exactly `{mean, median, p25, p75, persistently_coherent_fraction}` | PASS (asserted in test) |
| `coherence_stats` docstring mentions all 5 keys                               | PASS |
| `residual_mean_velocity(velocity, stable_mask)` subtracts stable-mask median by default | PASS (asserted in test) |
| `residual_mean_velocity` with empty mask raises ValueError                    | PASS (asserted in test) |

## Decisions Made

- **T-04-01 mitigation**: CSLC-01 defaults (5 km coast, 500 m water, slope<=10°) are module constants — inspectable and test-asserted — rather than magic numbers buried inside the function body. Downstream tightening via explicit kwargs.
- **T-04-02 mitigation**: `coherence_stats` returns all 5 candidate statistics (not just one) so Phase 3 calibration can switch between mean / median / persistent-fraction without another dataclass edit. Directly addresses PITFALLS P2.2 research-flagged planning decision.
- **T-04-03 mitigation**: `residual_mean_velocity` defaults to `frame_anchor='median'` (robust to stable-mask false-positives) per PITFALLS P2.3; `mean` available via Literal kwarg. Empty-mask case is a ValueError, not a silent zero — callers must handle the gate explicitly.
- **T-04-05 mitigation**: Moved `Any` annotations into a `TYPE_CHECKING + TypeAlias` block so the module imports cleanly in pip-install-only environments (no `geopandas`/`shapely`/`rasterio` at runtime module top). mypy `--strict` sees full concrete type info; runtime stays lazy.

## Self-Check: PASSED

Created files verified on disk:
- `src/subsideo/validation/stable_terrain.py` — FOUND
- `src/subsideo/validation/selfconsistency.py` — FOUND
- `src/subsideo/validation/__init__.py` — FOUND (modified from 0 bytes to 620 bytes)
- `tests/unit/test_stable_terrain.py` — FOUND
- `tests/unit/test_selfconsistency.py` — FOUND

Commits verified in `git log` on branch `worktree-agent-aa0ba1b2`:
- `f5ee814` — FOUND (RED test for build_stable_mask)
- `12878e0` — FOUND (GREEN build_stable_mask)
- `1de484e` — FOUND (RED tests for selfconsistency)
- `178c4ff` — FOUND (GREEN selfconsistency)
- `1687777` — FOUND (__init__.py re-exports)
- `da4eb9c` — FOUND (ruff refactor)
- `7f43e72` — FOUND (mypy refactor)

All three tasks done; all required deliverables committed on the worktree branch.
