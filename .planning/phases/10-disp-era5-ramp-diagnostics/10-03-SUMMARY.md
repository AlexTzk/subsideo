---
phase: 10-disp-era5-ramp-diagnostics
plan: 03
subsystem: validation
tags: [disp, provenance, dem, orbit, terrain, cache, pydantic]

# Dependency graph
requires:
  - phase: 10-disp-era5-ramp-diagnostics
    plan: 01
    provides: additive DISP diagnostic schema contract
  - phase: 10-disp-era5-ramp-diagnostics
    plan: 02
    provides: ERA5 mode routing in DISP eval scripts
provides:
  - Schema-valid DISP terrain, orbit, DEM, and cache provenance sidecar fields
  - Network-free provenance helper functions for DEM, terrain, orbit, and cache summaries
  - SoCal and Bologna eval-script wiring for provenance sidecar writes
affects: [phase-10, phase-11, disp, matrix-sidecars]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Pydantic v2 extra-forbid provenance models
    - Lazy rasterio import inside validation helpers
    - Eval-script cache-mode tracking from warm/redownload/regeneration branches

key-files:
  created: []
  modified:
    - src/subsideo/validation/matrix_schema.py
    - src/subsideo/validation/disp_diagnostics.py
    - run_eval_disp.py
    - run_eval_disp_egms.py
    - tests/product_quality/test_matrix_schema_disp.py
    - tests/product_quality/test_disp_diagnostics.py

key-decisions:
  - "Kept provenance fields additive so legacy DISP sidecars validate unchanged."
  - "Used helper-level SHA256 hashing for DEM/cache provenance while preserving meta.input_hashes compatibility."
  - "Recorded cached-orbit fallback rows as UNKNOWN coverage when no EOF can be matched, so each successful sensing time has an orbit provenance record."

patterns-established:
  - "Major DISP inputs and outputs carry cache modes from explicit eval-script branch decisions."
  - "Terrain provenance summarizes the DEM-grid stable mask and only computes terrain-vs-ramp correlation when arrays are shape-compatible."

requirements-completed: [DISP-06, RTCSUP-02]

# Metrics
duration: 30min
completed: 2026-05-04
---

# Phase 10 Plan 03: DISP Provenance Diagnostics Summary

**Schema-valid orbit, DEM, terrain, stable-mask, and cache provenance now flows into both DISP cell sidecars.**

## Performance

- **Duration:** 30 min
- **Started:** 2026-05-04T05:39:00Z
- **Completed:** 2026-05-04T06:09:19Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Added `TerrainDiagnostics`, `OrbitCoverageDiagnostic`, `DemDiagnostics`, and `CacheProvenance` to `DISPCellMetrics`.
- Implemented deterministic provenance helpers: `sha256_file`, `summarize_dem`, `summarize_terrain`, `summarize_orbit_coverage`, and `cache_provenance`.
- Wired SoCal and Bologna DISP eval scripts to write DEM, terrain, orbit, and cache provenance while keeping `MetaJson(input_hashes=...)`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend schema for provenance diagnostics** - `8573dc5` (feat)
2. **Task 2: Implement provenance helper functions** - `4d640ad` (feat)
3. **Task 3: Write provenance fields from both DISP eval scripts** - `1b8fb14` (feat)

## Files Created/Modified

- `src/subsideo/validation/matrix_schema.py` - Added provenance models and optional `DISPCellMetrics` fields.
- `tests/product_quality/test_matrix_schema_disp.py` - Added provenance validation, legacy default, and invalid cache-mode tests.
- `src/subsideo/validation/disp_diagnostics.py` - Added DEM, terrain, orbit coverage, SHA256, and cache provenance helpers.
- `tests/product_quality/test_disp_diagnostics.py` - Added GeoTIFF, orbit filename, and cache provenance fixtures.
- `run_eval_disp.py` - Tracks SoCal DEM/SLC/CSLC/orbit/velocity cache modes and writes provenance fields.
- `run_eval_disp_egms.py` - Mirrors provenance tracking and sidecar writes for Bologna.

## Decisions Made

- `summarize_terrain()` raises on stable-mask/DEM shape mismatch; eval scripts pass ramp correlation only when shape-compatible, currently `None` for per-IFG ramp vectors.
- Orbit fetch cache mode is inferred by comparing EOF paths before and after `fetch_orbit()`; successful fetches not present beforehand are marked `redownloaded`.
- Existing warm CSLC paths are recorded as `reused`; new `run_cslc()` outputs are `regenerated`; velocity warm path is `reused` and `run_disp()` output is `regenerated`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Focused pytest uses `--no-cov`, matching prior Phase 10 summaries, because repo-wide coverage fail-under is not meaningful for two targeted test files.
- Existing untracked `.claude/` and `marker.txt` were present before this plan and left untouched.

## Verification

- `PYTHONPATH=src pytest tests/product_quality/test_matrix_schema_disp.py tests/product_quality/test_disp_diagnostics.py -q --no-cov` passed.
- `python3 -m py_compile src/subsideo/validation/disp_diagnostics.py run_eval_disp.py run_eval_disp_egms.py` passed.
- `grep -c "TerrainDiagnostics" src/subsideo/validation/matrix_schema.py` returned `2`.
- `grep -c "CacheProvenance" src/subsideo/validation/matrix_schema.py` returned `2`.
- `grep -c "summarize_dem" run_eval_disp.py` returned `2`.
- `grep -c "orbit_provenance" run_eval_disp_egms.py` returned `2`.

## Known Stubs

None.

## Threat Flags

None - no new network endpoints, auth paths, file access trust boundaries, or schema-breaking changes were introduced.

## User Setup Required

None - helper and static verification are network-free. Live ERA5-on eval runs still require the existing `~/.cdsapirc` setup from Plan 10-02.

## Next Phase Readiness

Phase 10 conclusions can now consume schema-valid provenance from both DISP sidecars before interpreting ERA5/ramp diagnostic deltas. Phase 11 can distinguish cache/input, DEM, orbit, and terrain evidence without adding another sidecar shape.

## Self-Check: PASSED

- Found `.planning/phases/10-disp-era5-ramp-diagnostics/10-03-SUMMARY.md`.
- Found `src/subsideo/validation/matrix_schema.py`.
- Found `src/subsideo/validation/disp_diagnostics.py`.
- Found `run_eval_disp.py`.
- Found `run_eval_disp_egms.py`.
- Found `tests/product_quality/test_matrix_schema_disp.py`.
- Found `tests/product_quality/test_disp_diagnostics.py`.
- Found task commit `8573dc5`.
- Found task commit `4d640ad`.
- Found task commit `1b8fb14`.

---
*Phase: 10-disp-era5-ramp-diagnostics*
*Completed: 2026-05-04*
