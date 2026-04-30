---
phase: 05-dist-s1-opera-v0-1-effis-eu
plan: "03"
subsystem: validation
tags: [bootstrap, schema, pydantic, additive, ci-band, dist-s1]
dependency_graph:
  requires: [05-01]
  provides: [block_bootstrap_ci, BootstrapResult, MetricWithCI, BootstrapConfig, DistEUCellMetrics, DistNamCellMetrics, DistEUEventMetrics, EFFISQueryMeta, RasterisationDiagnostic, ChainedRunResult]
  affects: [05-04, 05-05, 05-06, 05-07]
tech_stack:
  added:
    - numpy PCG64 block bootstrap (Hall 1985 stationary bootstrap)
    - Pydantic v2 BaseModel with extra='forbid' for all new schema types
  patterns:
    - module-level DEFAULT_* constants (auditable via git log --grep)
    - frozen dataclass for immutable result containers
    - additive-only schema extension (zero edits to existing types)
    - TDD (RED test commit then GREEN implementation commit)
key_files:
  created:
    - src/subsideo/validation/bootstrap.py
    - tests/unit/test_bootstrap.py
  modified:
    - src/subsideo/validation/matrix_schema.py
decisions:
  - "BootstrapConfig.block_size_m/n_bootstrap/rng_seed defaults wired to match bootstrap.py DEFAULT_* constants exactly (1000/500/0) to enforce single source of truth"
  - "DistNamCellMetrics ships as minimal deferred-cell shape only; v1.2 extension hook documented in docstring"
  - "spain_culebra replaces romania as third DistEUEventID per RESEARCH Probe 4 ADR (EFFIS fire-only; no clear-cut coverage)"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-25"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 1
---

# Phase 05 Plan 03: Bootstrap CI + DIST Schema Extension Summary

Pure-numpy Hall (1985) block-bootstrap CI helper plus 8 new Pydantic v2 schema types enabling all Wave 2/3 Phase 5 plans; zero edits to existing schema types.

## What Was Built

### Task 1: src/subsideo/validation/bootstrap.py (187 LOC, NEW)

**Module signature:**

```python
def block_bootstrap_ci(
    predictions: np.ndarray,
    references: np.ndarray,
    metric_fn: Callable[[np.ndarray, np.ndarray], float],
    *,
    block_size_m: int = 1000,   # DEFAULT_BLOCK_SIZE_M
    pixel_size_m: int = 30,     # DEFAULT_PIXEL_SIZE_M
    n_bootstrap: int = 500,     # DEFAULT_N_BOOTSTRAP
    ci_level: float = 0.95,     # DEFAULT_CI_LEVEL
    rng_seed: int = 0,          # DEFAULT_RNG_SEED
) -> BootstrapResult: ...
```

**Algorithm:** Hall (1985) stationary block bootstrap on 2-D raster pairs.
- Crops to full-block grid (drops partial-block L-strip at east + south edges, CONTEXT D-08)
- PCG64 RNG (`np.random.default_rng(seed=0)`) per CONTEXT D-09; Mersenne Twister rejected
- Resamples `n_blocks_kept` block indices with replacement for each of B iterations
- Returns 2.5/97.5 percentile CI bounds for `ci_level=0.95`

**Runtime estimate:** ~3 minutes for T11SLT (3660x3660, 12,100 blocks, B=500) per RESEARCH Probe 9.

**Block math for T11SLT:**
- `px_per_block = 1000 // 30 = 33`
- `n_block_rows = n_block_cols = 3660 // 33 = 110`
- `n_blocks_kept = 110 * 110 = 12100`
- `n_blocks_dropped = (110+1)*(110+1) - 12100 = 12321 - 12100 = 221`

**BootstrapResult** is a `@dataclass(frozen=True)` with 8 fields: `point_estimate`, `ci_lower`, `ci_upper`, `n_blocks_kept`, `n_blocks_dropped`, `n_bootstrap`, `ci_level`, `rng_seed`.

### Task 1: tests/unit/test_bootstrap.py (101 LOC, NEW)

5 tests, all pass:
1. `test_module_level_defaults` — constants resolve to (1000, 500, 0, 0.95, 30)
2. `test_point_estimate_matches_metric_fn` — for 1320x1320 raster, point_estimate matches `f1_score(pred.ravel(), ref.ravel())` within 1e-9
3. `test_deterministic_seed_reproducibility` — two calls with rng_seed=0 produce identical ci_lower/ci_upper/n_blocks_kept/n_blocks_dropped
4. `test_block_count_math_for_t11slt_shape` — 3660x3660 raster yields n_blocks_kept=12100, n_blocks_dropped=221
5. `test_nan_propagation_through_metric_fn` — NaN inputs do not crash; result is finite

### Task 2: src/subsideo/validation/matrix_schema.py (629 → 870 LOC, 242 lines appended)

**8 new Pydantic v2 types (all `model_config = ConfigDict(extra='forbid')`):**

```
MetricWithCI
  point: float, ci_lower: float, ci_upper: float

BootstrapConfig
  block_size_m=1000, n_bootstrap=500, ci_level=0.95, rng_seed=0
  n_blocks_kept: int (required), n_blocks_dropped: int (required)

EFFISQueryMeta
  wfs_endpoint, layer_name, filter_string, response_feature_count, fetched_at

RasterisationDiagnostic
  all_touched_false_f1 (gate), all_touched_true_f1 (diagnostic), delta_f1

ChainedRunResult
  status: ChainedRunStatus, output_dir, n_layers_present, dist_status_nonempty, error, traceback

DistEUEventMetrics (BaseModel)
  event_id: DistEUEventID, status, f1/precision/recall/accuracy: MetricWithCI
  rasterisation_diagnostic, bootstrap_config, effis_query_meta, chained_run (Aveiro only)

DistEUCellMetrics(MetricsJson)       -- aggregate EU DIST cell
  pass_count, total=3, all_pass, cell_status, worst_event_id, worst_f1
  any_chained_run_failed, per_event: list[DistEUEventMetrics]

DistNamCellMetrics(MetricsJson)      -- MINIMAL deferred shape
  cell_status="DEFERRED", reference_source="none", cmr_probe_outcome (required)
  reference_granule_id, deferred_reason
```

**6 new Literal aliases:**
- `DistEUEventID = Literal["aveiro", "evros", "spain_culebra"]` (NOT romania — RESEARCH Probe 4 ADR)
- `ChainedRunStatus = Literal["structurally_valid", "partial_output", "dist_s1_hang", "crashed", "skipped"]`
- `CMRProbeOutcome = Literal["operational_found", "operational_not_found", "probe_failed"]`
- `ReferenceSource = Literal["operational_v1", "v0.1_cloudfront", "none"]`
- `DistEUCellStatus = Literal["PASS", "FAIL", "MIXED", "BLOCKER"]`
- `DistNamCellStatus = Literal["PASS", "FAIL", "DEFERRED"]`

## Type Hierarchy

```
DistEUCellMetrics(MetricsJson)
  └── per_event: list[DistEUEventMetrics]
        ├── f1/precision/recall/accuracy: MetricWithCI
        ├── rasterisation_diagnostic: RasterisationDiagnostic
        ├── bootstrap_config: BootstrapConfig
        ├── effis_query_meta: EFFISQueryMeta
        └── chained_run: ChainedRunResult | None  (Aveiro only)

DistNamCellMetrics(MetricsJson)        [minimal deferred shape]
  └── v1.2 extension: adds ConfigDriftReport + bootstrap_config + MetricWithCI metrics
```

## DistNamCellMetrics v1.2-Extension Hook

The `DistNamCellMetrics` docstring documents the forward-extension path:

> v1.2 will EXTEND this class with `config_drift: ConfigDriftReport`, `bootstrap_config: BootstrapConfig`, and `reference_agreement.metrics: dict[str, MetricWithCI]` once OPERA_L3_DIST-ALERT-S1_V1 publishes operationally in CMR. The CMR auto-supersede probe in run_eval_dist.py Stage 0 (DIST-04) handles the v1.2 transition without re-planning.

matrix_writer (Plan 05-05) discriminates via `cell_status == 'DEFERRED' AND presence of reference_source key`.

## Decisions Made

1. **BootstrapConfig defaults tied to bootstrap.py constants** — `block_size_m=1000`, `n_bootstrap=500`, `rng_seed=0` match `DEFAULT_*` constants exactly. Changing either requires a PR diff in both files (auditable via `git log`).
2. **spain_culebra not romania** — RESEARCH Probe 4 ADR: EFFIS fire perimeter database does not cover clear-cut events; romania's Rosu forest clear-cut is ineligible. Third event is Spain's Culebra wildfire.
3. **DistNamCellMetrics minimal shape ships now** — Full v1.2 schema deferred until OPERA_L3_DIST-ALERT-S1_V1 publishes operationally in CMR (per scope amendment 2026-04-25). `cmr_probe_outcome` is required (not optional) to force Stage 0 probe result to always be recorded.
4. **TDD execution order** — tests written first (RED), implementation second (GREEN), no REFACTOR needed. Committed as two separate commits per task protocol.

## Deviations from Plan

None. Plan executed exactly as written.

## Self-Check

### Files Exist
- `src/subsideo/validation/bootstrap.py`: FOUND (187 LOC)
- `tests/unit/test_bootstrap.py`: FOUND (101 LOC)
- `src/subsideo/validation/matrix_schema.py`: FOUND (870 LOC, 242 lines added)

### Commits Exist
- `d969b66`: feat(05-03): add block_bootstrap_ci + BootstrapResult + unit tests
- `c7cd067`: feat(05-03): append 8 new Pydantic v2 types to matrix_schema.py (additive only)

### Tests
- 5/5 tests pass in tests/unit/test_bootstrap.py (confirmed by pytest output)
- All 8 new types importable and validated via /tmp/run_final_verify.py
- extra='forbid' enforced on all new types
- spain_culebra present in DistEUEventID, romania absent
- 242 insertions, 0 deletions in matrix_schema.py (additive immutability preserved)

## Self-Check: PASSED
