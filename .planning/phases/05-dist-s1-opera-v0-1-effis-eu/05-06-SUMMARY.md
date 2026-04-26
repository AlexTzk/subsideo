---
phase: 05-dist-s1-opera-v0-1-effis-eu
plan: "06"
subsystem: eval-script/run_eval_dist
tags: [eval-script, cmr-probe, deferred-cell, earthaccess, mp-bundle, supervisor, d16-archival]
dependency_graph:
  requires:
    - src/subsideo/_mp.py (configure_multiprocessing — Phase 1 ENV-04)
    - src/subsideo/validation/harness.py (credential_preflight, bounds_for_mgrs_tile)
    - src/subsideo/validation/matrix_schema.py (DistNamCellMetrics, MetaJson — added by Plan 05-03)
  provides:
    - run_eval_dist.py (T11SLT CMR Stage 0 + DEFERRED metrics.json + D-16 archival)
    - tests/unit/test_run_eval_dist_cmr_stage0.py (4 unit tests guarding the contract)
  affects:
    - eval-dist/metrics.json (DistNamCellMetrics-shaped, runtime-produced)
    - eval-dist/meta.json (MetaJson-shaped provenance sidecar)
    - eval-dist/archive/v0.1_metrics_<mtime-iso>.json (CONTEXT D-16; on operational supersede)
    - matrix_writer dist:nam render branch (Plan 05-05 reads cell_status + cmr_probe_outcome)
tech_stack:
  added: []
  patterns:
    - 3-way CMR-outcome dispatch (operational_found / operational_not_found / probe_failed)
    - importlib-based unit-test driver for top-level scripts (no subprocess)
    - shutil.move atomic archival with mtime-iso filename collision-avoidance
key_files:
  created:
    - tests/unit/test_run_eval_dist_cmr_stage0.py
  modified:
    - run_eval_dist.py
decisions:
  - "Repointed N.Am. DIST eval target from Park Fire (10TFK, 2024-08-05) to T11SLT (LA fires 2025-01-21) per CONTEXT D-05 and RESEARCH Probe 6. Park Fire cache will be preserved as eval-dist-park-fire/ by Plan 05-08 (cache rename only)."
  - "DEFERRED-cell contract: matrix_writer.dist:nam reads `metrics.json.cell_status='DEFERRED'` and `metrics.json.cmr_probe_outcome` to render the cell. Plan 05-05 implements that render branch."
  - "CONTEXT D-16 archival hook implemented now (rather than as a v1.2 TODO) — the ~10 LOC implementation is unit-testable and removes a v1.2 hazard where the archival contract could get lost when the operational pipeline lands."
  - "EXPECTED_WALL_S = 60*60*3 (3h pre-budget for v1.2 full pipeline; deferred path completes in ~30s). Pre-allocating the v1.2 budget now avoids a future bump when the operational pipeline replaces the NotImplementedError."
  - "MetaJson construction uses the actual matrix_schema.py:68-114 field names (schema_version, git_sha, git_dirty, run_started_iso, run_duration_s, python_version, platform, input_hashes). Pydantic v2 `extra='forbid'` enforces this — Test 1 asserts the contract."
metrics:
  duration: "~15 minutes"
  completed_date: "2026-04-25T23:45:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
---

# Phase 05 Plan 06: run_eval_dist.py Rewrite + CMR Stage 0 + D-16 Archival Summary

## One-liner

Rewrote `run_eval_dist.py` from a 450-LOC Park Fire end-to-end pipeline into a 286-LOC T11SLT CMR-probe + DEFERRED-metrics writer with the CONTEXT D-16 archival hook implemented now (4 unit tests cover the 3 outcome branches + the no-prior-metrics edge case).

## Tasks Completed

| # | Name | Commit | Status |
|---|------|--------|--------|
| 1 | Rewrite run_eval_dist.py for T11SLT + CMR Stage 0 + D-16 | 6b9bb17 | Done |
| 2 | tests/unit/test_run_eval_dist_cmr_stage0.py (4 tests) | 92a85e7 | Done |

## Behaviour Sketch

### Stage 0: CMR auto-supersede probe (DIST-04)

```
earthaccess.login(strategy='environment')
bbox = bounds_for_mgrs_tile('11SLT')   # falls back to (-119, 33.5, -118, 34.5)
results = earthaccess.search_data(
    short_name='OPERA_L3_DIST-ALERT-S1_V1',
    bounding_box=bbox,
    temporal=(POST_DATE - 7d, POST_DATE + 7d),
    count=20,
)
```

- `results == []` → `cmr_probe_outcome='operational_not_found'`, `reference_source='none'`
- `results raises Exception` → `cmr_probe_outcome='probe_failed'`, `reference_source='none'`
- `results != []` → `cmr_probe_outcome='operational_found'`, `reference_source='operational_v1'`,
  then **CONTEXT D-16 archival**, then `raise NotImplementedError(v1.2 trigger)`

### Stage 1: Deferred metrics.json write

```python
metrics = DistNamCellMetrics(
    product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
    reference_agreement=ReferenceAgreementResultJson(measurements={}, criterion_ids=[]),
    criterion_ids_applied=[],
    cell_status='DEFERRED',
    reference_source=reference_source,        # 'operational_v1' | 'none'
    cmr_probe_outcome=cmr_probe_outcome,      # 'operational_found' | 'operational_not_found' | 'probe_failed'
    reference_granule_id=reference_granule_id,
    deferred_reason='<Phase 5 scope amendment 2026-04-25 ...>',
)
(OUT / 'metrics.json').write_text(metrics.model_dump_json(indent=2))
```

### Stage 2: meta.json provenance (Blocker 1 fix — verbatim field names)

```python
meta = MetaJson(
    schema_version=1,
    git_sha=git_sha,                      # subprocess git rev-parse HEAD
    git_dirty=git_dirty,                  # subprocess git status --porcelain
    run_started_iso=run_started.isoformat(),
    run_duration_s=time.time() - t_start,
    python_version=platform.python_version(),
    platform=platform.platform(),
    input_hashes={},                      # deferred path has no inputs to hash
)
```

The previous draft used `subsideo_version`, `timestamp_utc_start`, `timestamp_utc_end`,
`wall_seconds` — those names DO NOT EXIST in MetaJson. Pydantic v2 `extra='forbid'` would
raise `ValidationError` on every script invocation. The rewrite uses the actual field
names verbatim and Test 1 asserts MetaJson parses cleanly (regression guard).

## CONTEXT D-16 Archival Hook

```python
existing_metrics = OUT / 'metrics.json'
if existing_metrics.exists():
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    mtime_iso = datetime.fromtimestamp(
        existing_metrics.stat().st_mtime, tz=timezone.utc
    ).isoformat().replace(':', '-')   # filesystem-safe
    archive_dst = ARCHIVE_DIR / f'v0.1_metrics_{mtime_iso}.json'
    shutil.move(str(existing_metrics), str(archive_dst))
```

- Atomic move (rename(2)) on the same filesystem.
- mtime-iso filename means multiple supersede events do not collide.
- Test 3 + Test 4 guard the move-not-copy semantics + the no-prior-metrics edge case.

## v1.2 Hand-off

When OPERA-ADT publishes `OPERA_L3_DIST-ALERT-S1_V1` operationally, the next
`make eval-dist-nam` invocation:

1. `earthaccess.search_data` returns ≥ 1 hit.
2. The script archives any prior `eval-dist/metrics.json` to `eval-dist/archive/`.
3. `NotImplementedError` raises with a clear "v1.2 work" message + the archived
   path + the granule ID.
4. The user runs `/gsd:plan-phase 5 --gaps` (or starts the v1.2 milestone) to
   land the full F1+CI pipeline. v1.2 will replace the `raise` with a real
   pipeline call; the archive directory contract is already in place.

## Test Coverage

```bash
$ /Users/alex/.local/share/mamba/envs/subsideo/bin/python -m pytest \
    tests/unit/test_run_eval_dist_cmr_stage0.py --no-cov -x -v
============================= 4 passed in 2.16s ==============================
```

## Notes for Plan 05-08 (Cache Rename)

- v1.0 Park Fire content is REPLACED in `run_eval_dist.py` (not duplicated).
  Plan 05-08 should rename `eval-dist/` → `eval-dist-park-fire/` BEFORE the
  first Phase 5 `make eval-dist-nam` invocation, otherwise the new T11SLT
  output will collide with the Park Fire cache.

## Notes for Plan 05-09 (Docs)

- `CONCLUSIONS_DIST_N_AM.md` should preserve the v1.0 Park Fire narrative
  as a "historical baseline" preamble, then add the Phase 5 deferred-cell
  sub-section explaining the CMR auto-supersede strategy and the v1.2
  trigger criteria.

## Inline Recovery Note

This plan was originally dispatched as a parallel-worktree subagent
(`agent-a8d2f7be`) which lost Bash permissions in its sandbox and could not
commit. The orchestrator removed the bad worktree (whose base was
`eff433b`, an old non-Wave-1 ancestor — a separate Task isolation bug) and
executed the plan inline on main. All artifacts and commits are in place.
