---
phase: 08-cslc-gate-promotion-and-aoi-hardening
plan: 01
subsystem: validation
tags: [cslc, stable-terrain, geospatial, diagnostics]
requires:
  - phase: v1.1 Phase 3
    provides: CSLC self-consistency eval scripts and stable-terrain module
provides:
  - CRS-aware stable-terrain geometry buffering
  - CSLC stable-mask retention diagnostics in sanity metadata
affects: [CSLC-07, CSLC-08, Phase 9 CSLC reruns]
tech-stack:
  added: []
  patterns: [lazy geospatial imports, mask_metadata diagnostics]
key-files:
  created: []
  modified:
    - src/subsideo/validation/stable_terrain.py
    - tests/unit/test_stable_terrain.py
    - run_eval_cslc_selfconsist_nam.py
    - run_eval_cslc_selfconsist_eu.py
key-decisions:
  - "Raw shapely geometries remain assumed to be in raster CRS; CRS-carrying GeoSeries inputs are reprojected before metre buffering."
  - "Stable-mask retention diagnostics are written to per-AOI mask_metadata.json rather than changing metrics schemas."
patterns-established:
  - "CRS-carrying geometries call to_crs(raster_crs) before buffer(buffer_m)."
  - "CSLC eval scripts compute class/slope/coast/water/final retention counts from DEM-grid masks."
requirements-completed:
  - CSLC-08
  - CSLC-07
duration: 40 min
completed: 2026-04-30
---

# Phase 8 Plan 01: Projected-Metre Stable-Terrain Buffers Summary

**CRS-aware stable-terrain buffering with CSLC mask-retention diagnostics for Phase 9 gate evidence**

## Performance

- **Duration:** 40 min
- **Started:** 2026-04-30T21:09:00Z
- **Completed:** 2026-04-30T21:49:30Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- GeoSeries coastline/waterbody inputs now reproject to the raster CRS before metric buffering.
- Offline regressions cover EPSG:32611 and EPSG:32630 while preserving raw shapely behavior.
- N.Am. and EU CSLC eval scripts now write stable-mask class, slope, buffer-exclusion, final-count, retention, and CRS diagnostics to per-AOI sanity metadata.

## Task Commits

1. **Task 1: Reproject GeoSeries geometries before buffering** - `4a83f44` (fix)
2. **Task 2: Add stable-mask retention diagnostics to CSLC eval scripts** - `6eea45c` (feat)

**Plan metadata:** pending orchestrator metadata commit

## Files Created/Modified

- `src/subsideo/validation/stable_terrain.py` - Reprojects CRS-carrying GeoSeries geometry collections before buffering.
- `tests/unit/test_stable_terrain.py` - Adds SoCal UTM 11N and Iberian UTM 30N reprojection regressions.
- `run_eval_cslc_selfconsist_nam.py` - Writes stable-mask retention diagnostics for N.Am. AOIs.
- `run_eval_cslc_selfconsist_eu.py` - Writes stable-mask retention diagnostics for EU AOIs.

## Decisions Made

- Mask diagnostics live in `mask_metadata.json` sidecars, avoiding a schema change to product-quality metrics.
- Water-excluded counts are measured after coastline exclusion, so coast and water counts explain the sequential stable-mask narrowing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test command needed workspace PYTHONPATH**
- **Found during:** Task 1 verification
- **Issue:** Bare `pytest` resolved an older `/Users/alex/repos/subsideo` install and failed imports.
- **Fix:** Ran unit verifications with `env PYTHONPATH=src ... --no-cov` to target this checkout and avoid whole-project coverage fail-under on focused tests.
- **Files modified:** None
- **Verification:** `env PYTHONPATH=src pytest tests/unit/test_stable_terrain.py -q --no-cov` passed.
- **Committed in:** N/A

---

**Total deviations:** 1 auto-fixed (Rule 3)
**Impact on plan:** Verification targeted the current workspace; implementation scope unchanged.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 08-02. Phase 9 can consume projected-buffer behavior and retention diagnostics after the remaining AOI and cache-hardening work lands.

## Self-Check: PASSED

- `env PYTHONPATH=src pytest tests/unit/test_stable_terrain.py -q --no-cov` passed.
- `env PYTHONPATH=src python3 -m py_compile run_eval_cslc_selfconsist_nam.py run_eval_cslc_selfconsist_eu.py` passed.
- Grep checks confirmed `to_crs`, `EPSG:32611`, `EPSG:32630`, `stable_mask_retention_pct`, `stable_mask_final_count`, and `stable_mask_buffer_crs`.

---
*Phase: 08-cslc-gate-promotion-and-aoi-hardening*
*Completed: 2026-04-30*
