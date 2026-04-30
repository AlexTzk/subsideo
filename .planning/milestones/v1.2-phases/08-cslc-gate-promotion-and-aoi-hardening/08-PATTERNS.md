# Phase 8: CSLC Gate Promotion & AOI Hardening - Patterns

**Date:** 2026-04-30
**Status:** Complete

## File Pattern Map

| Target | Role | Closest analog | Pattern to preserve |
|--------|------|----------------|---------------------|
| `src/subsideo/validation/stable_terrain.py` | Shared validation primitive | Self | Pure functions, lazy heavy imports, no module-top geopandas/rasterio imports |
| `tests/unit/test_stable_terrain.py` | Geometry unit tests | Existing buffer tests | Import optional geospatial deps with `pytest.importorskip`; keep tests offline |
| `scripts/probe_cslc_aoi_candidates.py` | Re-runnable probe tool | `scripts/probe_rtc_eu_candidates.py` and self | Soft CLI script, writes markdown artifact, network calls isolated behind helpers |
| `.planning/milestones/v1.2-research/cslc_gate_promotion_aoi_candidates.md` | Probe artifact | `.planning/milestones/v1.1-research/cslc_selfconsist_aoi_candidates.md` | Markdown table plus locked windows and rejected-candidate rationale |
| `src/subsideo/validation/harness.py` | Shared validation plumbing | Existing `find_cached_safe`, `download_reference_with_retry` | Path-safe helpers, no product imports, never silently swallow integrity failures |
| `src/subsideo/validation/__init__.py` | Public validation re-export | Existing harness re-exports | Add new helper exports in both import list and `__all__` |
| `tests/unit/test_harness.py` | Harness regression tests | Existing retry/cache tests | Mock sessions/filesystem, no real network |
| `src/subsideo/data/cdse.py` | CDSE SAFE tree downloader | Existing `download_safe_tree` | Per-object retry loop; validate returned local `.SAFE` directory |
| `run_eval_cslc_selfconsist_nam.py` | CSLC N.Am. eval integration | Self and `run_eval_rtc_eu.py` | Declarative AOIs, `find_cached_safe` first, per-epoch isolation |
| `run_eval_cslc_selfconsist_eu.py` | CSLC EU eval integration | N.Am. script | Preserve useful parity, but do not force obsolete structure |
| `run_eval_rtc_eu.py`, `run_eval_disp.py`, `run_eval_disp_egms.py` | Other SAFE consumers | Existing SAFE download paths | Call shared cache-integrity helper before readers consume cached or downloaded SAFEs |
| `src/subsideo/validation/compare_disp.py` | DISP comparison adapter | Self | Preserve `src.nodata` capture inside context and `dst_nodata=np.nan` in reproject |
| `.planning/REQUIREMENTS.md` | Requirements/rationale doc | Existing v1.2 requirements table | Add explicit proposed threshold rationale for CSLC-07 if needed |

## Concrete Code Patterns

### Stable-Terrain Geometry Handling

Current `stable_terrain.py` pattern:

```python
if isinstance(geometry, BaseGeometry):
    gs = gpd.GeoSeries([geometry], crs=crs)
elif isinstance(geometry, gpd.GeoSeries):
    gs = geometry
else:
    gs = gpd.GeoSeries(geometry, crs=crs)

buffered = gs.buffer(buffer_m)
```

Phase 8 should preserve raw `BaseGeometry` as already-in-raster-CRS, but reproject a `GeoSeries` that carries a CRS:

```python
if getattr(gs, "crs", None) is not None and str(gs.crs) != str(crs):
    gs = gs.to_crs(crs)
```

Add tests using `gpd.GeoSeries(..., crs="EPSG:4326")` with raster CRS `EPSG:32611` and `EPSG:32630`.

### SAFE Integrity Helper

Follow harness style:

```python
def validate_safe_path(path: Path, *, repair: bool = false) -> bool:
    ...
```

Expected behaviors:

- `*.zip`: open with `zipfile.ZipFile`, require at least one member containing `.SAFE/`, return `False` on `BadZipFile`.
- `*.SAFE` directory: require `manifest.safe` and at least one non-empty descendant under `measurement` or `annotation`.
- Missing path: `False`.
- Do not delete unless a caller explicitly asks for repair/removal.

Then `find_cached_safe(..., require_valid=True)` can skip invalid hits and keep searching sibling cache dirs.

### Probe Artifact Pattern

The v1.1 probe writes:

```markdown
## Candidate AOIs (D-10 schema)
| aoi | regime | candidate_burst_id | ... |

## Locked Sensing Windows
### MOJAVE_COSO_EPOCHS — Mojave/Coso-Searles
```

Phase 8 should write a v1.2 artifact with no `[SYNTHETIC FALLBACK]` entries and explicit rejected candidates:

```markdown
## Rejected Candidates
| aoi | reason | evidence |
```

### Stale Test Policy

Keep behavioral assertions, not accidental script-shape assertions. Good assertions:

- canonical artifact contains SoCal, Mojave/Coso-Searles, Mojave/Pahranagat, Mojave/Amargosa, Mojave/Hualapai, Iberian Meseta-North, and at least two EU fallback AOIs.
- canonical artifact contains no `SYNTHETIC FALLBACK`.
- regenerated EU fallback names in the eval script come from artifact values or stale fallback tests are removed with a rationale comment/doc entry.

## Pattern Mapping Complete

Use these patterns while executing Phase 8 plans.

