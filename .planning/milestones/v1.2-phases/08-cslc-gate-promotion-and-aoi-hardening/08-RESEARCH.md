# Phase 8: CSLC Gate Promotion & AOI Hardening - Research

**Date:** 2026-04-30
**Status:** Complete

## Summary

Phase 8 should be planned as four tightly connected workstreams:

1. Stable-terrain buffer correctness and diagnostics.
2. Full CSLC AOI probe regeneration.
3. SAFE cache integrity and shared-infra defect fixes.
4. Threshold-rationale documentation plus stale-test closure.

The work is codebase-internal validation hardening. No new product algorithms are needed. The key risk is letting old v1.1 artifacts continue to drive Phase 9 reruns; plans should replace stale/fabricated evidence with regenerated, test-pinned artifacts.

## Technical Findings

### Stable-Terrain Buffers

- `src/subsideo/validation/stable_terrain.py` already exposes `build_stable_mask(worldcover, slope_deg, coastline, waterbodies, transform, crs, coast_buffer_m=5000.0, water_buffer_m=500.0, slope_max_deg=10.0)`.
- `_buffered_geometry_mask()` currently buffers whatever geometry it receives in the raster CRS context. If a `GeoSeries` carries `EPSG:4326`, it should be reprojected to the raster CRS before `.buffer(buffer_m)`.
- Backward compatibility matters: existing tests pass raw `BaseGeometry` coordinates already in UTM metres, so raw shapely geometries should continue to be assumed in the raster CRS unless wrapped in a `GeoSeries` with `crs`.
- New regression tests should cover at least two UTM zones. SoCal can use EPSG:32611; Iberian can use EPSG:32630.
- Diagnostics should live in CSLC eval outputs or mask metadata, with concrete keys such as `stable_mask_class60_count`, `stable_mask_slope_ok_count`, `stable_mask_coast_excluded_count`, `stable_mask_water_excluded_count`, `stable_mask_final_count`, and `stable_mask_retention_pct`.

### AOI Probe Regeneration

- `scripts/probe_cslc_aoi_candidates.py` exists but includes a deterministic synthetic fallback path. Phase 8 must remove or hard-fail synthetic sensing windows for the canonical artifact.
- v1.1 conclusions identify fabricated N.Am. tuples and invalid EU fallbacks. The regenerated artifact must cover SoCal, all Mojave fallbacks, Iberian Meseta-North, and at least two EU fallback AOIs.
- The artifact should be written under v1.2 planning/research scope, not the old v1.1 research path. Recommended output: `.planning/milestones/v1.2-research/cslc_gate_promotion_aoi_candidates.md`.
- Tests should validate the artifact structurally from a fixture or offline sample, not require live ASF/CDSE credentials in unit tests.

### SAFE Cache Integrity

- `harness.download_reference_with_retry()` already streams to `<dest>.partial` and atomically renames on success for HTTPS-style downloads.
- CSLC N.Am. and EU eval scripts already perform local `zipfile.ZipFile` checks after ASF downloads, but this logic is duplicated and does not protect `find_cached_safe()` hits from old poisoned caches.
- `find_cached_safe()` returns `*.zip` and `*.SAFE` matches without integrity validation. It should either call a shared validator before returning, or callers should immediately validate through a shared helper.
- CDSE SAFE directory downloads in `src/subsideo/data/cdse.py` can produce directory trees. Directory validation should check required markers such as `manifest.safe` and non-empty `measurement` or `annotation` descendants; zip validation should open the archive and require at least one `.SAFE/` member plus no `BadZipFile`.

### Shared-Infra Defects

- CR-01 and HI-01 are in `src/subsideo/validation/compare_disp.py`; the current code already appears to capture `src.nodata` inside the rasterio context and pass `dst_nodata=np.nan` in `_resample_onto_grid()`. Phase 8 should preserve those fixes and add regression tests so they cannot regress.
- CR-02 is in `src/subsideo/validation/harness.py`; the current code explicitly raises `ReferenceDownloadError` for status `>=400` outside retry/abort branches and catches only `ConnectionError`/`Timeout`. Phase 8 should add regression tests for a status such as `500` to prove it fails fast instead of silently retrying via `requests.HTTPError`.

### Stale Tests

- `tests/unit/test_run_eval_cslc_selfconsist_eu.py` contains `test_env07_diff_discipline` and fallback-chain assertions. The current file already skips ENV-07 when scripts have diverged too far, but Phase 8 should make the tests intentional.
- The policy is not "make old structure pass at all costs." Preserve behavioral invariants: real regenerated fallback metadata, no synthetic windows in canonical artifact, script parity where it matters, and clear fallback semantics.

## Recommended Plan Breakdown

| Plan | Objective | Wave | Requirements |
|------|-----------|------|--------------|
| 08-01 | Projected-metre stable terrain buffers + retention diagnostics | 1 | CSLC-08, CSLC-07 |
| 08-02 | Full AOI probe regeneration + stale AOI/fallback test policy | 1 | CSLC-09, CSLC-12 |
| 08-03 | SAFE cache self-healing + shared-infra regressions | 1 | RTCSUP-01, RTCSUP-03 |
| 08-04 | Final threshold rationale docs + closure tests | 2 | CSLC-07, CSLC-12, RTCSUP-01, RTCSUP-03 |

## Validation Architecture

- Unit tests for geometry reprojection, cache integrity, HTTP retry semantics, and raster nodata behavior.
- Static tests for regenerated AOI artifact structure and absence of synthetic fallback windows.
- Focused tests first, then a final Phase 8 suite:
  - `pytest tests/unit/test_stable_terrain.py -q`
  - `pytest tests/unit/test_harness.py -q`
  - `pytest tests/unit/test_compare_disp.py tests/unit/test_run_eval_cslc_selfconsist_eu.py -q`
  - `pytest tests/unit/ -x -q --tb=short`

## Open Risks

- Live ASF/CDSE search may require credentials or network access. Unit tests should not depend on live search.
- Full AOI regeneration may reveal better fallbacks than v1.1 names. That is allowed, but the artifact must record rejected candidates and reasons.
- Existing v1.1 fixes for CR-01/CR-02/HI-01 may already be present. The required Phase 8 value is regression coverage and requirement traceability, not gratuitous rewrites.

## Research Complete

This research is sufficient to plan Phase 8.

