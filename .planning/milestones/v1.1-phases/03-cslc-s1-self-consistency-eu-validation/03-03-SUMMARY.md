---
phase: 03-cslc-s1-self-consistency-eu-validation
plan: "03"
subsystem: validation
status: "partial — Task 1 (code) complete; Task 2 (compute + CONCLUSIONS + sign-off) deferred to user"
tags: [cslc, selfconsistency, nam, eval-script, tdd, compute-residual-velocity]
completed_date: "2026-04-24"

dependency_graph:
  requires:
    - 03-01-SUMMARY.md  # selfconsistency.py scaffolding, matrix_schema AOIResult/CSLCSelfConsistNAMCellMetrics
    - 03-02-SUMMARY.md  # probe artifact: SoCal/Mojave epoch locks + burst IDs
  provides:
    - run_eval_cslc_selfconsist_nam.py  # N.Am. CSLC eval entry point
    - compute_residual_velocity implementation  # fills 03-01 stub
    - tests/unit/test_run_eval_cslc_selfconsist_nam.py  # 19 static-invariant tests
  affects:
    - 03-04-PLAN.md  # EU fork: IberianAOI uses same AOIConfig pattern + run_amplitude_sanity=True

tech_stack:
  added:
    - scipy.ndimage.uniform_filter (boxcar coherence in _compute_ifg_coherence_stack)
    - matplotlib.pyplot (P2.1 sanity artifact rendering)
    - h5py (lazy-imported in compute_residual_velocity + _compute_ifg_coherence_stack)
  patterns:
    - "EXPECTED_WALL_S BinOp at module top (supervisor AST-parse contract)"
    - "AOIConfig frozen dataclass local to script (D-05 analog)"
    - "fallback_chain recursion: first-CALIBRATING-wins; all-FAIL -> BLOCKER"
    - "run_amplitude_sanity flag drives D-07 gating (not aoi_name literal)"
    - "compute_residual_velocity: vectorised OLS per-pixel phase slope -> mm/yr"
    - "P2.3 reference-frame alignment via stable-set median anchor"
    - "P2.1 sanity artifacts: coherence_histogram.png + stable_mask PNG + JSON"
    - "Exit 0 for CALIBRATING/MIXED/PASS; exit 1 for BLOCKER/FAIL (D-03)"

key_files:
  created:
    - run_eval_cslc_selfconsist_nam.py        # ~970 LOC; N.Am. eval script
    - tests/unit/test_run_eval_cslc_selfconsist_nam.py  # 19 static-invariant tests
  modified:
    - src/subsideo/validation/selfconsistency.py  # fill compute_residual_velocity stub

decisions:
  - "D-11 fallback order: Coso/Searles > Pahranagat > Amargosa > Hualapai (probe-locked)"
  - "Hualapai MOJAVE_HUALAPAI_EPOCHS flagged [SYNTHETIC FALLBACK] in code comment"
  - "compute_residual_velocity uses vectorised OLS (not np.polyfit) for memory efficiency"
  - "ast.literal_eval incompatible with BinOp in Python 3.12; use compile+eval in tests"
  - "matplotlib.use(Agg) placed before pyplot import with noqa:I001 to satisfy ruff"

metrics:
  duration_min: 71
  tasks_completed: 1
  tasks_total: 2
  files_created: 3
  files_modified: 1
  tests_added: 19
  tests_passing: 40  # 19 new + 21 selfconsistency regression
---

# Phase 03 Plan 03: CSLC Self-Consistency N.Am. Eval — Summary

**One-liner:** Implement N.Am. CSLC self-consistency eval script with SoCal 15-epoch anchor + Mojave 4-fallback chain, filling compute_residual_velocity stub via vectorised OLS phase-to-velocity regression.

**Status:** Partial — Task 1 (code + tests) complete and committed. Task 2 (execute `make eval-cslc-nam`, populate `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md`, human sign-off) deferred to user per plan scope.

## What Was Built (Task 1)

### `run_eval_cslc_selfconsist_nam.py` (new, ~970 LOC)

End-to-end N.Am. CSLC self-consistency evaluation script. Key structural properties (all verified by tests):

- `EXPECTED_WALL_S = 60 * 60 * 16` at module top as a BinOp literal (supervisor AST-parses)
- All imports and orchestration inside `if __name__ == "__main__":` guard
- `AOIS: list[AOIConfig] = [SoCalAOI, MojaveAOI]`
- **SoCalAOI**: `burst_id="t144_308029_iw1"`, `SOCAL_EPOCHS` (15 datetimes, verbatim from probe artifact), `run_amplitude_sanity=True`
- **MojaveAOI**: parent row with `fallback_chain=(_MOJAVE_FALLBACKS)` — 4 candidates in probe-locked order
- **MOJAVE_COSO/PAHRANAGAT/AMARGOSA/HUALAPAI_EPOCHS**: each a 15-datetime tuple copied verbatim from `.planning/milestones/v1.1-research/cslc_selfconsist_aoi_candidates.md`
- Hualapai flagged `[SYNTHETIC FALLBACK]` in code comment (ASF query returned < 15 scenes)
- `process_aoi()`: handles `fallback_chain` recursion; first CALIBRATING/PASS wins; all-FAIL → BLOCKER
- `run_amplitude_sanity` flag (not aoi_name literal) gates D-07 amplitude sanity check
- `_compute_ifg_coherence_stack()`: N-1 sequential IFGs + boxcar coherence (scipy.ndimage)
- `_write_sanity_artifacts()`: P2.1 coherence_histogram.png + stable_mask_over_basemap.png + mask_metadata.json
- `_resolve_cell_status()`: CALIBRATING → CALIBRATING; CALIBRATING+BLOCKER → MIXED; all-BLOCKER → BLOCKER
- Exit code: 0 for CALIBRATING/MIXED/PASS; 1 for BLOCKER/all-FAIL (D-03)

### `src/subsideo/validation/selfconsistency.py` (modified)

`compute_residual_velocity` stub (Plan 03-01 `NotImplementedError`) filled:

- Loads each CSLC HDF5, extracts VV/HH complex array
- Extracts `zero_doppler_start_time` from `identification` group (attr-first, dataset-fallback)
- `np.unwrap` along time axis for temporal phase unwrapping
- Vectorised OLS: `slope = sum(days_c * phase_c) / sum(days_c^2)` — no per-pixel loop
- Converts slope to mm/yr: `v = -slope * 0.055465763 / (4π) * 1000 * 365.25`
- NaN fill outside stable_mask; returns float32 (H, W)

### `tests/unit/test_run_eval_cslc_selfconsist_nam.py` (new, 19 tests)

Static-invariant tests (no network, no isce3):

| Test | Description |
|------|-------------|
| T-1 | EXPECTED_WALL_S is module-top BinOp evaluating to 57600 |
| T-1b | supervisor._parse_expected_wall_s succeeds |
| T-2 | AOIS structure: SoCalAOI first, MojaveAOI second |
| T-3 | SoCal lock: burst_id=t144_308029_iw1, 15 SOCAL_EPOCHS |
| T-4 | Mojave fallback chain order: Coso→Pahranagat→Amargosa→Hualapai + burst IDs |
| T-5 | SoCal success path smoke (compute_residual_velocity + coherence_stats mocked via stub HDF5) |
| T-6 | All-fallbacks-FAIL → parent BLOCKER + 4 FAIL attempts + MIXED cell_status |
| T-7a | First-PASS wins: Coso succeeds → 1 attempt, parent CALIBRATING |
| T-7b | Second-PASS wins: Coso FAIL + Pahranagat → 2 attempts, Amargosa/Hualapai absent |
| T-8a/b/c/d | Exit code contract: CALIBRATING→0, BLOCKER→1, MIXED→0 |
| T-9 | Reference-frame alignment: uniform +3.0 → residual=0.0 (P2.3) |
| T-10 | Sanity artifact paths in script (P2.1 mitigation) |
| Extra | All MOJAVE_*_EPOCHS have 15 entries; run_amplitude_sanity field + flag; no aoi_name literal; no placeholder datetimes |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Python 3.12 ast.literal_eval rejects BinOp nodes**
- **Found during:** Task 1 GREEN phase — test_expected_wall_s_is_module_level_binop failed
- **Issue:** `ast.literal_eval(BinOp_node)` raises ValueError in Python 3.12 (changed from 3.11 where it worked for int arithmetic)
- **Fix:** Used `compile(ast.Expression(body=node), ...) + eval(code, {"__builtins__": {}})` for safe integer-arithmetic-only evaluation
- **Files modified:** `tests/unit/test_run_eval_cslc_selfconsist_nam.py`

**2. [Rule 1 - Bug] ruff I001 on interleaved matplotlib.use() between imports**
- **Found during:** Task 1 REFACTOR phase — ruff I001 on `_write_sanity_artifacts`
- **Issue:** `matplotlib.use("Agg")` must appear between `import matplotlib` and `import matplotlib.pyplot` (functional requirement), but ruff flags this as unsorted import block
- **Fix:** Added `# noqa: I001` to the first import of the block
- **Files modified:** `run_eval_cslc_selfconsist_nam.py`

**3. [Rule 1 - Bug] mypy `no-any-return` on compute_residual_velocity**
- **Found during:** Task 1 REFACTOR phase — mypy strict mode
- **Issue:** numpy type inference chain loses concrete dtype on chained operations
- **Fix:** Added `np.asarray(v_mm_per_yr, dtype=np.float32)` explicit cast at return
- **Files modified:** `src/subsideo/validation/selfconsistency.py`

**4. [Rule 2 - Missing critical] Comment contained forbidden pattern `cfg.aoi_name == "SoCal"`**
- **Found during:** GREEN phase test run — test_run_amplitude_sanity_field_and_flag failed
- **Issue:** Two code comments explaining BLOCKER 4 fix used the exact string `cfg.aoi_name == "SoCal"`, which the test (correctly) rejects to prevent drift back to the old conditional
- **Fix:** Rewrote comments to avoid the literal pattern while preserving the explanation
- **Files modified:** `run_eval_cslc_selfconsist_nam.py`

## Task 2 — Deferred to User

Task 2 (`checkpoint:human-verify gate=blocking`) is NOT executed by this agent per the objective scope. The following remains for the user:

1. Run `make eval-cslc-nam` (supervisor wraps script; budget ~12h cold, ~48h worst-case Mojave fallback-chain)
2. Inspect P2.1 sanity artifacts in `eval-cslc-selfconsist-nam/sanity/SoCal/` and the winning Mojave fallback
3. Populate `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` from `metrics.json` + `meta.json` + sanity artifacts
4. Verify SoCal first-epoch amplitude sanity regression (r vs v1.0 baseline 0.79, RMSE 3.77 dB)
5. Commit `eval-cslc-selfconsist-nam/metrics.json`, `meta.json`, `sanity/`, `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md`

The eval script is ready to run and will produce `eval-cslc-selfconsist-nam/metrics.json` (CSLCSelfConsistNAMCellMetrics) with per_aoi entries for SoCal (CALIBRATING, run_amplitude_sanity) and Mojave (CALIBRATING from first successful fallback, or BLOCKER on exhaustion).

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 303f42f | test | RED: 19 failing tests for run_eval_cslc_selfconsist_nam.py |
| c11f14b | feat | GREEN: implement script + fill compute_residual_velocity stub + fix tests |

## Self-Check: PASSED

| Item | Status |
|------|--------|
| `run_eval_cslc_selfconsist_nam.py` exists at repo root | FOUND |
| `tests/unit/test_run_eval_cslc_selfconsist_nam.py` exists | FOUND |
| `src/subsideo/validation/selfconsistency.py` exists (compute_residual_velocity implemented) | FOUND |
| RED commit 303f42f exists | FOUND |
| GREEN commit c11f14b exists | FOUND |
| 19 tests pass | VERIFIED |
| 21 selfconsistency regression tests pass | VERIFIED |
| ruff clean on script + selfconsistency.py | VERIFIED |
| mypy clean on selfconsistency.py | VERIFIED |
| No STATE.md or ROADMAP.md modified | VERIFIED |
| CONCLUSIONS_CSLC_SELFCONSIST_NAM.md NOT populated | VERIFIED (Task 2 scope) |
