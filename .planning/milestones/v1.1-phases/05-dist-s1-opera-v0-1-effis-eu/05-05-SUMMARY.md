---
phase: 05-dist-s1-opera-v0-1-effis-eu
plan: "05"
subsystem: validation
tags: [effis, rest-api, matrix-writer, dist-eu, dist-nam, render-branch, additive]
dependency_graph:
  requires: [05-02, 05-03, 05-04]
  provides: [effis.fetch_effis_perimeters, effis.rasterise_perimeters_to_grid, matrix_writer._is_dist_eu_shape, matrix_writer._render_dist_eu_cell, matrix_writer._render_dist_nam_deferred_cell]
  affects: [05-06, 05-07]
tech_stack:
  added: [requests (REST client), urllib3.Retry (retry adapter)]
  patterns: [REST pagination, spatial post-filter, dual-rasterise, schema-discriminator dispatch]
key_files:
  created:
    - src/subsideo/validation/effis.py
    - tests/unit/test_matrix_writer_dist.py
  modified:
    - src/subsideo/validation/matrix_writer.py
decisions:
  - "WFS replaced by EFFIS REST API (both WFS candidates failed; see effis_endpoint_lock.txt)"
  - "D-18 amendment: requests.Session + urllib3.Retry instead of download_reference_with_retry (incompatible contract)"
  - "EFFIS_WFS_URL/LAYER_NAME/FILTER_NAMESPACE exported as REST-backed aliases for plan interface contract"
  - "Dispatch insertion AFTER disp:* per D-24 amendment; BEFORE-cslc is contemporary observation only"
  - "Test 4 uses src.find() not second_occurrence() because dispatch callsite appears exactly once per discriminator"
metrics:
  duration_minutes: 45
  tasks_completed: 3
  files_created: 2
  files_modified: 1
  completed_date: "2026-04-25"
---

# Phase 05 Plan 05: EFFIS REST Client + Matrix Writer DIST Branches Summary

**One-liner:** EFFIS REST client with urllib3-retry + per_event/DEFERRED discriminator branches wired into matrix_writer dispatch chain.

## What Was Built

### Task 1: `src/subsideo/validation/effis.py` (NEW, 290 LOC)

REST API implementation replacing the originally-planned WFS approach after both WFS candidates failed during Plan 05-02 probing.

**Endpoint constants (from `eval-dist_eu/effis_endpoint_lock.txt`):**
- `EFFIS_REST_URL = "https://api.effis.emergency.copernicus.eu/rest/2/burntareas/current/"`
- `EFFIS_DATE_PROPERTY = "firedate"`
- `EFFIS_FILTER_NAMESPACE = "drf"` (Django REST Framework QueryParam namespace)
- `EFFIS_WFS_URL`, `EFFIS_LAYER_NAME`, `EFFIS_FILTER_NAMESPACE` exported as backward-compat aliases

**Public functions:**
- `fetch_effis_perimeters(event_id, bbox_wgs84, date_start, date_end, cache_dir, *, country)` — REST API GET with country + date filter, spatial post-filter (bbox intersection), GeoJSON cache at `cache_dir/<event_id>/effis_perimeters/perimeters.geojson`
- `rasterise_perimeters_to_grid(gdf, out_shape, transform)` — dual rasterise: `all_touched=False` (primary/gate) and `all_touched=True` (diagnostic; ~+2-4pp F1 per PITFALLS P4.4)

**D-18 amendment compliance:**
- `RETRY_POLICY['EFFIS']` consulted via `_build_retry_session()` which mounts a `urllib3.Retry` adapter on `requests.Session`
- `download_reference_with_retry` NOT called (0 references in effis.py)
- Harness owns policy declaration; effis.py owns dispatch entry point

**Note on `intersects` filter:** The REST API's `intersects` geometry parameter returns HTTP 403 (WAF-blocked). Country + date range filter is used instead, with geopandas spatial post-filter applied in code.

### Task 2: `src/subsideo/validation/matrix_writer.py` (MODIFIED, +4 functions, +2 dispatch branches)

Four new functions appended after `_render_disp_cell`, before `write_matrix`:

- `_is_dist_eu_shape(metrics_path)` — discriminates `per_event` key (structurally disjoint from DISP/CSLC/RTC)
- `_is_dist_nam_shape(metrics_path)` — discriminates `cell_status='DEFERRED'` + `reference_source` key
- `_render_dist_eu_cell(metrics_path)` — renders `X/3 PASS | worst f1=N.NNN (event_id)` with optional ` ⚠` glyph
- `_render_dist_nam_deferred_cell(metrics_path)` — renders `DEFERRED (CMR: <cmr_probe_outcome>)`

Two dispatch branches inserted AFTER the `disp:*` branch per the D-24 amendment (structurally meaningful invariant). Dispatch ordering: disp@580 → dist_eu@596 → dist_nam@612.

All existing render branches (DISP, CSLC self-consist, RTC-EU, default RUN_FAILED) are byte-identical.

### Task 3: `tests/unit/test_matrix_writer_dist.py` (NEW, 206 LOC, 4 tests)

- `test_dist_eu_all_pass_render`: `3/3 PASS | worst f1=0.850 (evros)` — no fail count, no glyph
- `test_dist_eu_mixed_with_chained_warning`: `2/3 PASS (1 FAIL) | worst f1=0.620 (spain_culebra) ⚠`
- `test_dist_nam_deferred_render`: `DEFERRED (CMR: operational_not_found)`
- `test_dispatch_ordering_dist_after_disp`: asserts disp_call < dist_eu_call < dist_nam_call; cslc/dswx ordering unconstrained per D-24 amendment

All 4 tests pass (+ 5 test_bootstrap tests = 9 passed total).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Pivot] REST API replaces WFS/owslib**
- **Found during:** Task 1 (critical_pivot in objective)
- **Issue:** Both WFS endpoints failed (Candidate A: ReadTimeout; Candidate B: DNS NXDOMAIN). User approved REST pivot.
- **Fix:** Implemented `requests`-based REST client instead of `owslib.wfs.WebFeatureService`. WFS-style constant names (`EFFIS_WFS_URL`, `EFFIS_LAYER_NAME`, `EFFIS_FILTER_NAMESPACE`) still exported as aliases to satisfy the plan's interface contract.
- **Files modified:** `src/subsideo/validation/effis.py` (entire implementation)
- **Commits:** c27629d

**2. [Rule 1 - Bug] Test 4 second_occurrence() assumption incorrect**
- **Found during:** Task 3 test run
- **Issue:** Plan template assumed each discriminator would appear twice in source (function def + dispatch call). The function definitions use typed signatures (`def _is_disp_cell_shape(metrics_path: Path)`) which don't match the bare `_is_disp_cell_shape(metrics_path)` needle, so there was only 1 occurrence. `second_occurrence()` returned -1.
- **Fix:** Replaced `second_occurrence()` with direct `src.find()` (first occurrence = the dispatch callsite).
- **Files modified:** `tests/unit/test_matrix_writer_dist.py`
- **Commit:** 5ae2b7f (included in same commit)

**3. [Rule 2 - Missing] EFFIS country code mapping**
- **Found during:** Task 1
- **Issue:** The `intersects` geometry filter is WAF-blocked (HTTP 403). REST query uses country + date range instead. Country must be auto-derived from bbox centroid when caller doesn't supply it.
- **Fix:** Added `_country_for_bbox()` heuristic + spatial post-filter in `fetch_effis_perimeters`.
- **Files modified:** `src/subsideo/validation/effis.py`
- **Commit:** c27629d

## Dual-Rasterise Contract (CONTEXT D-17)

| Mask | `all_touched` | Role | Metric |
|------|--------------|------|--------|
| `mask_at_false` | `False` | PRIMARY (gate value) | F1 used in cell metric |
| `mask_at_true` | `True` | DIAGNOSTIC only | ~+2-4pp inflation per P4.4 |

Caller: `rasterise_perimeters_to_grid(gdf, out_shape, transform)` where `gdf` is already in the target CRS (caller reprojects before calling).

## D-18 Amendment Implementation

Per ROADMAP Phase 5 scope-amendment block:

| Component | Role |
|-----------|------|
| `harness.RETRY_POLICY['EFFIS']` | Policy declaration (owned by harness) |
| `effis._build_retry_session()` | Projects policy onto urllib3.Retry adapter |
| `requests.Session` with `HTTPAdapter(max_retries=Retry(...))` | Transport layer with exponential backoff |
| `abort_on` post-check on response status | Raises `ReferenceDownloadError` on 401/403/404 |

## Known Stubs

None. Both public functions are fully implemented.

## Threat Flags

None found beyond the documented threat register in the plan.

## Self-Check

### Created files exist
- `/Volumes/Geospatial/Geospatial/subsideo/.claude/worktrees/agent-aa838a59/src/subsideo/validation/effis.py`: FOUND
- `/Volumes/Geospatial/Geospatial/subsideo/.claude/worktrees/agent-aa838a59/tests/unit/test_matrix_writer_dist.py`: FOUND
- `/Volumes/Geospatial/Geospatial/subsideo/.claude/worktrees/agent-aa838a59/src/subsideo/validation/matrix_writer.py`: FOUND (modified)

### Commits exist
- c27629d: feat(05-05) effis.py — FOUND
- b9432e2: feat(05-05) matrix_writer.py DIST branches — FOUND
- 5ae2b7f: test(05-05) test_matrix_writer_dist.py — FOUND

## Self-Check: PASSED
