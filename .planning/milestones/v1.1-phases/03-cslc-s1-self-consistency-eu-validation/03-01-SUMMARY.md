---
phase: 03-cslc-s1-self-consistency-eu-validation
plan: 01
subsystem: validation
tags: [cslc, matrix-schema, matrix-writer, worldcover, natural-earth, selfconsistency, criteria, egms]
dependency_graph:
  requires: []
  provides:
    - src/subsideo/validation/selfconsistency.py::coherence_stats (6-key dict with median_of_persistent)
    - src/subsideo/validation/selfconsistency.py::compute_residual_velocity (stub, Plan 03-03 implements)
    - src/subsideo/validation/criteria.py::Criterion.gate_metric_key field
    - src/subsideo/validation/matrix_schema.py::AOIResult
    - src/subsideo/validation/matrix_schema.py::CSLCSelfConsistNAMCellMetrics
    - src/subsideo/validation/matrix_schema.py::CSLCSelfConsistEUCellMetrics
    - src/subsideo/validation/matrix_writer.py::_is_cslc_selfconsist_shape
    - src/subsideo/validation/matrix_writer.py::_render_cslc_selfconsist_cell
    - src/subsideo/validation/compare_cslc.py::compare_cslc_egms_l2a_residual
    - src/subsideo/data/worldcover.py::fetch_worldcover_class60
    - src/subsideo/data/worldcover.py::load_worldcover_for_bbox
    - src/subsideo/data/worldcover.py::build_permanent_water_mask
    - src/subsideo/data/natural_earth.py::load_coastline_and_waterbodies
  affects:
    - results/matrix_manifest.yml (cslc:nam + cslc:eu cells re-wired to selfconsist dirs)
    - Makefile (eval-cslc-nam + eval-cslc-eu targets updated to selfconsist scripts)
    - pyproject.toml (EGMStoolkit==0.2.15 + naturalearth added to [dev] extras)
tech_stack:
  added:
    - EGMStoolkit==0.2.15 (EGMS L2a CSV download, pyproject.toml [dev])
    - naturalearth (Natural Earth geometries, pyproject.toml [dev])
  patterns:
    - TYPE_CHECKING guard for lazy conda-forge imports in data/ modules
    - Pydantic v2 BaseModel with model_rebuild() for self-referential AOIResult
    - _is_*_shape JSON shape discriminator before Pydantic validation
key_files:
  created:
    - src/subsideo/validation/matrix_schema.py (AOIResult + CSLCSelfConsist{NAM,EU}CellMetrics appended)
    - src/subsideo/validation/matrix_writer.py (_is_cslc_selfconsist_shape + _render_cslc_selfconsist_cell + dispatch branch added)
    - src/subsideo/data/worldcover.py
    - src/subsideo/data/natural_earth.py
    - tests/unit/test_worldcover.py
    - tests/unit/test_natural_earth.py
  modified:
    - src/subsideo/validation/selfconsistency.py (median_of_persistent key + compute_residual_velocity stub)
    - src/subsideo/validation/criteria.py (gate_metric_key field on Criterion dataclass)
    - src/subsideo/validation/compare_cslc.py (compare_cslc_egms_l2a_residual added)
    - src/subsideo/validation/compare_disp.py (_load_egms_l2a_points extended to include mean_velocity_std)
    - results/matrix_manifest.yml (cslc cells wired to eval-cslc-selfconsist-{nam,eu}/)
    - Makefile (eval-cslc-{nam,eu} targets updated)
    - pyproject.toml ([dev] extras extended)
    - tests/unit/test_matrix_schema.py (Phase 3 AOIResult + CSLCSelfConsist test classes added; Path import bug fixed)
    - tests/unit/test_matrix_writer.py (Phase 3 rendering test class added)
decisions:
  - "AOIResult uses model_rebuild() to resolve self-referential attempts list (Pydantic v2 forward-ref pattern)"
  - "build_permanent_water_mask return type uses TYPE_CHECKING GeoDataFrame import to satisfy ruff ANN401"
  - "worldcover.py placed in data/ not validation/stable_terrain per CONTEXT Claude's Discretion (Phase 6 DSWx reuse)"
  - "naturalearth unpinned in pyproject.toml — PyPI only hosts a narrow version range with stable API surface"
metrics:
  duration: "~45 minutes (continuation agent; Tasks 3-5 GREEN + SUMMARY)"
  completed: "2026-04-23"
  tasks_completed: 5
  files_changed: 15
---

# Phase 3 Plan 01: CSLC Self-Consistency Scaffolding Summary

**One-liner:** Extended selfconsistency/criteria/matrix schema+writer with CSLC self-consistency contracts, added EGMS L2a residual helper and WorldCover/Natural Earth data fetchers, wired manifest+Makefile to new script names.

## Tasks Completed

### Task 1 — Extend selfconsistency.py + criteria.py (prior agent, commit a40bf17)

Extended `coherence_stats` to return a 6-key dict adding `median_of_persistent` — the median per-pixel-mean coherence restricted to pixels that are both in `stable_mask` AND persistently coherent across every IFG. This robust gate stat (P2.2 — immune to bimodal dune/playa contamination) is the Phase 3 D-01 coherence metric.

Added `compute_residual_velocity` stub to `selfconsistency.py` with the Plan 03-03 signature and `NotImplementedError`.

Added `gate_metric_key: str = "median_of_persistent"` field to `Criterion` dataclass in `criteria.py` (Phase 3 D-04). Default applies to all existing CSLC CALIBRATING entries; non-CSLC entries carry the default and do not consult this field.

Tests: `TestMedianOfPersistent` class (4 tests in test_selfconsistency.py) + `TestGateMetricKey` class (2 tests in test_criteria_registry.py).

### Task 2 — compare_cslc_egms_l2a_residual + _load_egms_l2a_points extension (prior agent, commit ec4fad3)

Added `compare_cslc_egms_l2a_residual(our_velocity_raster, egms_csv_paths, stable_std_max=2.0)` to `compare_cslc.py`. Uses function-body-local import of `_load_egms_l2a_points` from `compare_disp` (D-12 cross-module discipline). Filters EGMS PS points by `mean_velocity_std < stable_std_max`, reprojects to raster CRS, applies reference-frame alignment (P2.3: subtract stable-set median of our chain), returns mean absolute residual in mm/yr.

Extended `_load_egms_l2a_points` in `compare_disp.py` to optionally include `mean_velocity_std` column when present in CSVs (backward-compatible with existing `compare_disp_egms_l2a` call site).

Tests: `tests/unit/test_compare_cslc_egms_l2a.py` (5 tests using rasterio MemoryFile fixtures, no network).

### Task 3 — Matrix schema + writer Phase 3 additions (RED: commit 712672b; GREEN: commit 61247dc)

**RED phase (prior agent):** `tests/unit/test_matrix_schema.py` `TestAOIResult`, `TestCSLCSelfConsistNAMCellMetrics`, `TestCSLCSelfConsistEUCellMetrics`, `TestManifestShape` classes + `tests/unit/test_matrix_writer.py` `TestCSLCSelfConsistRendering` class written — all failing.

**GREEN phase (this agent):**

Added to `matrix_schema.py`:
- `AOIStatus` and `CSLCCellStatus` type aliases
- `AOIResult` Pydantic model with self-referential `attempts` list (model_rebuild() for forward-ref resolution)
- `CSLCSelfConsistNAMCellMetrics(MetricsJson)` with `pass_count`, `total`, `cell_status`, `any_blocker`, `product_quality_aggregate`, `reference_agreement_aggregate`, `per_aoi`
- `CSLCSelfConsistEUCellMetrics(CSLCSelfConsistNAMCellMetrics)` — inherit-only, distinguishes EU for writer dispatch

Added to `matrix_writer.py`:
- `_is_cslc_selfconsist_shape(metrics_path)` — JSON shape discriminator checking for `per_aoi` key
- `_render_cslc_selfconsist_cell(metrics_path, *, region)` — renders italicised CALIBRATING labels with pipe-delimited status|metrics format, AOI attribution in parens (W8 fix), U+26A0 warning glyph on `any_blocker=True`, EU three-number schema (egms_resid)
- Dispatch branch in `write_matrix` loop, placed BEFORE `_is_rtc_eu_shape` branch

Updated:
- `results/matrix_manifest.yml` cslc:nam + cslc:eu cells to `eval-cslc-selfconsist-{nam,eu}/` cache dirs and `run_eval_cslc_selfconsist_{nam,eu}.py` scripts
- `Makefile` eval-cslc-nam + eval-cslc-eu targets updated to selfconsist script names

Bug fixed: missing `from pathlib import Path` import in test_matrix_schema.py (Rule 1 auto-fix — red-phase test had NameError).

44 tests pass across test_matrix_schema.py + test_matrix_writer.py.

### Task 4 — data/worldcover.py + data/natural_earth.py (commit 4052ef4)

**worldcover.py:**
- `_tile_name(lat_south, lon_west)` — ESA WorldCover v200 filename for 3x3 degree tile
- `_tiles_covering_bbox(bbox)` — list of (lat_south, lon_west) corners covering a bbox
- `fetch_worldcover_class60(bbox, *, out_dir)` — anonymous S3 download (no credentials), idempotent cache-hit skip
- `load_worldcover_for_bbox(bbox, *, tiles_dir)` — rasterio.merge mosaic returning `(uint8 ndarray, Affine, CRS)`
- `build_permanent_water_mask(bounds, *, tiles_dir, buffer_m=500.0)` — WorldCover class-200 pixel extraction with UTM reprojection buffer (PITFALLS P2.1(b) playa fix)

**natural_earth.py:**
- `load_coastline_and_waterbodies(bbox, *, scale='10m')` — returns `(coastline, waterbodies)` GeoSeries clipped to bbox using `naturalearth` PyPI package (lazy-imported)
- Module docstring directs readers to `worldcover.build_permanent_water_mask` for inland water exclusion (PITFALLS P2.1 rationale)

**Tests:** 11 worldcover tests + 5 natural_earth tests = 16 total, all using rasterio.MemoryFile fixtures and `patch.dict` for naturalearth, no network.

### Task 5 — pyproject.toml [dev] extras (commit d98bc71)

Added to `[project.optional-dependencies.dev]`:
- `"EGMStoolkit==0.2.15"` — Phase 3 EU EGMS L2a CSV download
- `"naturalearth"` — Phase 3 coastline geometries (unpinned — stable API)

Resolves BLOCKER 5: `pip install -e ".[dev]"` now installs both packages at env-setup time, eliminating deferred install steps in Plan 03-03/04 eval scripts.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing `from pathlib import Path` in test_matrix_schema.py**
- **Found during:** Task 3 GREEN phase
- **Issue:** The red-phase test file `tests/unit/test_matrix_schema.py::TestManifestShape.test_cslc_cells_point_to_selfconsist_dirs` used `Path(...)` without importing it, causing `NameError` at test collection time.
- **Fix:** Added `from pathlib import Path` to the imports section.
- **Files modified:** `tests/unit/test_matrix_schema.py`
- **Commit:** 61247dc (included in the GREEN phase commit)

**2. [Rule 1 - Bug] Test fixture for build_permanent_water_mask used wrong pixel rows**
- **Found during:** Task 4 test run
- **Issue:** `TestBuildPermanentWaterMask::test_returns_geodataframe_with_buffers` placed class-200 water pixels at rows 30-40 of a 90x90 tile, but the bbox only covered the first 30 rows (rows 0-29 = lat 36→33 at 0.1deg/pixel). Water pixels were outside the merge bounds so the returned array had no class-200 values, causing the assertion `len(gdf) > 0` to fail.
- **Fix:** Changed tile_data to 30x30, placed water pixels at rows 5-15 (within bbox coverage), updated MemoryFile width/height to match.
- **Files modified:** `tests/unit/test_worldcover.py`
- **Commit:** 4052ef4

## Known Stubs

- `src/subsideo/validation/selfconsistency.py::compute_residual_velocity` — raises `NotImplementedError` with reference to Plan 03-03. Intentional stub per plan spec; Plan 03-03 provides the implementation.

## Self-Check: PASSED

All created/modified files exist and all task commits are present in git log.

Commits:
- a40bf17 feat(03-01): extend selfconsistency.py + criteria.py (Task 1, prior agent)
- ec4fad3 feat(03-01): add compare_cslc_egms_l2a_residual + extend _load_egms_l2a_points (Task 2, prior agent)
- 712672b test(03-01): add Task 3 red-phase tests (Task 3 RED, prior agent)
- 61247dc feat(03-01): implement matrix_schema + matrix_writer Phase 3 additions (Task 3 GREEN, this agent)
- 4052ef4 feat(03-01): add data/worldcover.py + data/natural_earth.py + unit tests (Task 4, this agent)
- d98bc71 chore(03-01): add EGMStoolkit==0.2.15 + naturalearth to pyproject.toml [dev] extras (Task 5, this agent)

Test counts: 60 tests pass across Task 3+4 test files; 54 regression tests pass across Task 1+2+stable_terrain files.
