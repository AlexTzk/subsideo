# Phase 5: Fix Cross-Phase Integration Wiring - Research

**Researched:** 2026-04-05
**Domain:** Python interface contract alignment (no new libraries, no API changes)
**Confidence:** HIGH

## Summary

This phase is purely mechanical: six bugs (B-01 through B-06) where Phase 2/3/4 product modules call Phase 1 data-access functions with wrong signatures, wrong imports, or missing arguments. All correct patterns already exist in the codebase -- DISP and DIST `*_from_aoi` functions demonstrate the right way for most calls, and the Phase 1 module signatures are stable and well-documented.

The research confirms every bug by comparing actual caller code against the canonical Phase 1 interfaces. No library research is needed -- this is internal contract alignment only. The fix pattern for each bug is deterministic: copy the working pattern from a sibling module.

**Primary recommendation:** Fix each caller to match the Phase 1 interface exactly, using DISP/DIST `*_from_aoi` as reference patterns. Add unit tests that mock Phase 1 modules and assert correct argument passing.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: CDSEClient must be instantiated with `client_id` and `client_secret` from SubsideoSettings
- D-02: All five product `*_from_aoi` functions get the same credential fix pattern
- D-03: RTC and CSLC callers must use `client.search_stac()` with `start=` and `end=` kwargs
- D-04: RTC and CSLC callers must import `query_bursts_for_aoi` from `subsideo.burst.frames`
- D-05: RTC and CSLC callers must call `fetch_orbit(sensing_time=..., satellite=..., output_dir=...)`
- D-06: All SAR product callers must pass `output_epsg` to `fetch_dem()`
- D-07: Callers must unpack the `tuple[Path, dict]` return from `fetch_dem()`
- D-08: CLI dist command must iterate `list[DISTResult]` from `run_dist_from_aoi()`
- D-09: Unit tests for each fix -- mock Phase 1 modules, verify correct args

### Claude's Discretion
- Specific error messages and logging around credential loading
- How to extract sensing_time/satellite from STAC items
- Whether to add a shared helper for CDSEClient instantiation or repeat inline

### Deferred Ideas (OUT OF SCOPE)
None.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Search and download Sentinel-1 IW SLC from CDSE via STAC + S3 | B-01 (credentials) and B-02 (search_stac) fixes make S1 search functional |
| DATA-02 | Search and download Sentinel-2 L2A from CDSE via STAC + S3 | B-01 fix in dswx.py makes S2 search functional |
| DATA-03 | Download and mosaic GLO-30 DEM for AOI | B-05 fix (output_epsg + tuple unpack) makes DEM fetch functional |
| DATA-04 | Download precise orbit ephemerides for Sentinel-1 | B-04 fix (correct args to fetch_orbit) makes orbit download functional |
| CLI-01 | Typer CLI exposes subcommands: rtc, cslc, disp, dswx, validate | B-06 fix makes CLI dist handler functional; all subcommands already registered |
</phase_requirements>

## Bug-by-Bug Analysis

### B-01: CDSEClient() missing credentials (all 5 modules)

**What's wrong:** All five `*_from_aoi` functions call `CDSEClient()` with no args.
**Correct signature:** `CDSEClient(client_id: str, client_secret: str)` (cdse.py line 45).
**Affected files:** rtc.py:310, cslc.py:282, disp.py:486, dist.py:277, dswx.py:527.

**Fix pattern:**
```python
from subsideo.config import Settings

settings = Settings()
client = CDSEClient(
    client_id=settings.cdse_client_id,
    client_secret=settings.cdse_client_secret,
)
```

**Discretion recommendation -- shared helper vs inline:** Use inline instantiation. A shared helper adds indirection for a two-line operation. All five call sites are in separate modules with lazy imports; a helper would create a new import dependency. Keep it simple and consistent with the existing pattern in the codebase.

### B-02: Wrong search method and args (RTC, CSLC)

**What's wrong:** rtc.py:313 and cslc.py:285 call `client.search(collection=..., bbox=..., datetime_range=...)`.
**Correct method:** `client.search_stac(collection, bbox, start, end, product_type=, max_items=)` (cdse.py line 86).
**CDSEClient has no `.search()` method** -- this is a runtime AttributeError.

**RTC fix (lines 311-317):**
```python
start_dt = datetime.strptime(date_range[0], "%Y-%m-%d")
end_dt = datetime.strptime(date_range[1], "%Y-%m-%d")
items = client.search_stac(
    collection="SENTINEL-1",
    bbox=list(geom.bounds),
    start=start_dt,
    end=end_dt,
    product_type="IW_SLC__1S",
)
```
Note: collection name is `"SENTINEL-1"` (not `"sentinel-1-slc"`), and `product_type="IW_SLC__1S"` filters to SLC. Reference: disp.py:487-493.

**CSLC fix:** Identical pattern.

### B-03: Wrong burst DB import (RTC, CSLC)

**What's wrong:** rtc.py:336-339 and cslc.py:308-311 do:
```python
from subsideo.burst.db import BurstDB
db = BurstDB()
burst_ids = db.query_by_geometry(geom.wkt)
```
There is no `BurstDB` class in `burst/db.py`. The module defines `BurstRecord` dataclass and `build_burst_db()` function.

**Correct import and usage** (from dist.py:246, disp.py:477):
```python
from subsideo.burst.frames import query_bursts_for_aoi

bursts = query_bursts_for_aoi(aoi_wkt=geom.wkt)
burst_ids = [b.burst_id_jpl for b in bursts]
```

**Important:** `query_bursts_for_aoi` returns `list[BurstRecord]`. Each `BurstRecord` has `.epsg` -- needed for B-05 fix.

### B-04: Wrong fetch_orbit() args (RTC, CSLC)

**What's wrong:** rtc.py:332 and cslc.py:304 call `fetch_orbit(safe_paths[0])` -- passing a single `Path`.
**Correct signature:** `fetch_orbit(sensing_time: datetime, satellite: str, output_dir: Path)` (orbits.py line 10).

**Fix requires extracting metadata from STAC items.** Reference pattern from disp.py:510-518:
```python
sensing_time = datetime.fromisoformat(
    scene.get("properties", {}).get("datetime", start_str)
)
satellite = scene.get("properties", {}).get("platform", "S1A")
orbit_path = fetch_orbit(
    sensing_time=sensing_time,
    satellite=satellite,
    output_dir=output_dir / "orbits",
)
```

**RTC/CSLC restructuring needed:** Current RTC/CSLC only process `items[0]` (first scene). The fix needs to parse the STAC item dict for `datetime` and `platform` properties. STAC item dicts from `search_stac()` follow standard STAC 1.1.0 structure with `properties.datetime` and `properties.platform`.

### B-05: fetch_dem() missing output_epsg and tuple unpack (RTC, CSLC, DISP, DIST)

**What's wrong:**
1. Callers omit `output_epsg` argument: `fetch_dem(geom.bounds, output_dir / "dem")`
2. Callers assign return to `dem_path` as if it returns `Path`, but it returns `tuple[Path, dict]`

**Correct signature:** `fetch_dem(bounds, output_epsg, output_dir, output_res_m=30.0) -> tuple[Path, dict]` (dem.py line 14).

**Affected callers and current code:**
- rtc.py:333: `dem_path = fetch_dem(geom.bounds, output_dir / "dem")`
- cslc.py:305: `dem_path = fetch_dem(geom.bounds, output_dir / "dem")`
- disp.py:497: `dem_path = fetch_dem(bounds=bbox, output_dir=output_dir / "dem")`
- dist.py:288: `dem_path = fetch_dem(bounds=bbox, output_dir=output_dir / "dem")`

**Fix pattern:**
```python
# Get EPSG from burst records (already resolved)
output_epsg = bursts[0].epsg  # BurstRecord.epsg set at DB build time

dem_path, _dem_profile = fetch_dem(
    bounds=list(geom.bounds),  # or bbox
    output_epsg=output_epsg,
    output_dir=output_dir / "dem",
)
```

**EPSG source for each module:**
- **RTC:** From `bursts[0].epsg` after fixing B-03 (burst query returns BurstRecord with epsg)
- **CSLC:** Same as RTC
- **DISP:** From `bursts[0].epsg` (already has correct burst query)
- **DIST:** From `bursts[0].epsg` (already has correct burst query)
- **DSWx:** Not a SAR product, does not call `fetch_dem()` -- not affected

**Note on RTC/CSLC:** These modules currently compute `epsg = utm_epsg_from_lon(centroid.x)` independently. After fixing B-03, they will have burst records with `.epsg`. Should use burst-derived EPSG for consistency with other modules. The existing `utm_epsg_from_lon` call can remain for the `run_rtc()` inner call if needed, but `fetch_dem` must use burst EPSG.

### B-06: CLI dist handler treats list as single result

**What's wrong:** cli.py:232-236:
```python
result = run_dist_from_aoi(aoi=aoi, date_range=(start, end), output_dir=product_dir)
if not result.valid:
    typer.echo(f"[FAIL] DIST: {result.validation_errors}", err=True)
```
But `run_dist_from_aoi()` returns `list[DISTResult]` (one per MGRS tile).

**Fix pattern:**
```python
results = run_dist_from_aoi(aoi=aoi, date_range=(start, end), output_dir=product_dir)
failures = [r for r in results if not r.valid]
if failures:
    for r in failures:
        typer.echo(f"[FAIL] DIST tile: {r.validation_errors}", err=True)
    raise typer.Exit(code=1)
typer.echo(f"[OK] DIST: {len(results)} tiles written to {product_dir}")
```

## Architecture Patterns

### Fix Order

Fixes should be applied in dependency order:
1. **B-01 first** (credentials) -- all modules need this before any call works
2. **B-03 next** (burst import) -- provides BurstRecord with .epsg needed for B-05
3. **B-02** (search method) -- independent but logically follows B-01
4. **B-04** (orbit args) -- requires STAC item structure from B-02 fix
5. **B-05** (DEM args) -- requires burst records from B-03 fix
6. **B-06 last** (CLI) -- independent, smallest fix

### Module Grouping

Natural grouping by file:
- **rtc.py:** B-01, B-02, B-03, B-04, B-05 (all 5 bugs)
- **cslc.py:** B-01, B-02, B-03, B-04, B-05 (all 5 bugs)
- **disp.py:** B-01, B-05 (2 bugs)
- **dist.py:** B-01, B-05 (2 bugs)
- **dswx.py:** B-01 only (1 bug)
- **cli.py:** B-06 only (1 bug)

### Existing Working Patterns to Copy

| Bug | Reference Module | Lines |
|-----|-----------------|-------|
| B-01 | None exists -- new pattern needed | -- |
| B-02 | disp.py:487-493 | search_stac with correct args |
| B-03 | disp.py:477-478, dist.py:246 | query_bursts_for_aoi import |
| B-04 | disp.py:510-518, dist.py:306-314 | fetch_orbit with STAC metadata |
| B-05 | None correct -- all callers have this bug | -- |
| B-06 | None -- CLI-specific | -- |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CDSE credential loading | Custom env var parsing | `Settings()` from config.py | Already handles env + .env + YAML precedence via pydantic-settings |
| STAC item metadata parsing | Custom datetime/platform extraction | Standard dict access on STAC item | STAC 1.1.0 spec guarantees `properties.datetime` and `properties.platform` |
| UTM EPSG determination | Manual UTM zone calculation | `BurstRecord.epsg` from burst query | Already computed at DB build time by pyproj |

## Common Pitfalls

### Pitfall 1: Mock Target Location
**What goes wrong:** Tests mock `subsideo.products.rtc.CDSEClient` instead of `subsideo.data.cdse.CDSEClient`.
**Why it happens:** Lazy imports inside function bodies mean the import target is the source module, not the caller module.
**How to avoid:** Mock at the source: `mocker.patch("subsideo.data.cdse.CDSEClient", ...)`. This is the pattern used in test_disp_pipeline.py:388.
**Warning signs:** Test passes but mock is never called.

### Pitfall 2: fetch_dem Positional vs Keyword Args
**What goes wrong:** Calling `fetch_dem(bbox, epsg, output_dir)` positionally works but is fragile.
**How to avoid:** Always use keyword args: `fetch_dem(bounds=bbox, output_epsg=epsg, output_dir=...)`.

### Pitfall 3: Empty Burst List for EPSG
**What goes wrong:** `bursts[0].epsg` raises IndexError if no bursts found for AOI.
**Why it happens:** AOI outside EU coverage, or burst DB not built.
**How to avoid:** Check `if not bursts:` before accessing `.epsg` and return early with error.

### Pitfall 4: STAC Item Dict Structure
**What goes wrong:** Accessing `item["properties"]["datetime"]` on items returned by `search_stac()`.
**Why it happens:** `search_stac()` returns `items_as_dicts()` which are raw STAC dicts. The `datetime` field may be ISO format with or without trailing `Z`.
**How to avoid:** Use `datetime.fromisoformat()` which handles both. Strip trailing `Z` if needed for Python <3.11 compat (project targets 3.10-3.11).

### Pitfall 5: RTC/CSLC Single-Scene vs Multi-Scene
**What goes wrong:** Current RTC/CSLC `from_aoi` only process `items[0]`. After fixing B-02, they get a list of STAC items.
**Why it matters:** For this phase, keep the single-scene behavior -- the goal is contract alignment, not feature addition. Process `items[0]` but with correct method calls.
**How to avoid:** Don't restructure RTC/CSLC into multi-scene loops. That's a future enhancement.

## Code Examples

### Complete B-01 + B-02 + B-03 + B-04 + B-05 Fix for RTC (run_rtc_from_aoi)

```python
# Imports (lazy, inside function body)
from subsideo.burst.frames import query_bursts_for_aoi
from subsideo.config import Settings
from subsideo.data.cdse import CDSEClient
from subsideo.data.dem import fetch_dem
from subsideo.data.orbits import fetch_orbit

# B-01: Instantiate with credentials
settings = Settings()
client = CDSEClient(
    client_id=settings.cdse_client_id,
    client_secret=settings.cdse_client_secret,
)

# B-02: Correct search method
start_dt = datetime.strptime(date_range[0], "%Y-%m-%d")
end_dt = datetime.strptime(date_range[1], "%Y-%m-%d")
items = client.search_stac(
    collection="SENTINEL-1",
    bbox=list(geom.bounds),
    start=start_dt,
    end=end_dt,
    product_type="IW_SLC__1S",
)

# B-03: Correct burst query
bursts = query_bursts_for_aoi(aoi_wkt=geom.wkt)
burst_ids = [b.burst_id_jpl for b in bursts]

# B-05: Correct DEM fetch with EPSG and tuple unpack
output_epsg = bursts[0].epsg
dem_path, _dem_profile = fetch_dem(
    bounds=list(geom.bounds),
    output_epsg=output_epsg,
    output_dir=output_dir / "dem",
)

# B-04: Correct orbit fetch from STAC item metadata
scene = items[0]
sensing_time = datetime.fromisoformat(
    scene.get("properties", {}).get("datetime", date_range[0])
)
satellite = scene.get("properties", {}).get("platform", "S1A")
orbit_path = fetch_orbit(
    sensing_time=sensing_time,
    satellite=satellite,
    output_dir=output_dir / "orbits",
)
```

### Test Pattern for Verifying Correct Args

```python
def test_run_rtc_from_aoi_passes_credentials(tmp_path, mocker):
    """B-01: CDSEClient gets client_id and client_secret from Settings."""
    # Mock Settings
    mock_settings = MagicMock()
    mock_settings.cdse_client_id = "test-id"
    mock_settings.cdse_client_secret = "test-secret"
    mocker.patch("subsideo.config.Settings", return_value=mock_settings)

    # Mock CDSEClient
    mock_client = MagicMock()
    mock_client.search_stac.return_value = [...]
    mock_cls = mocker.patch("subsideo.data.cdse.CDSEClient", return_value=mock_client)

    # ... run function ...

    mock_cls.assert_called_once_with(
        client_id="test-id",
        client_secret="test-secret",
    )
```

### B-06 CLI Fix

```python
results = run_dist_from_aoi(aoi=aoi, date_range=(start, end), output_dir=product_dir)
failures = [r for r in results if not r.valid]
if failures:
    for f in failures:
        typer.echo(f"[FAIL] DIST tile: {f.validation_errors}", err=True)
    raise typer.Exit(code=1)
typer.echo(f"[OK] DIST: {len(results)} tiles written to {product_dir}")
```

## Open Questions

1. **datetime.fromisoformat and trailing Z**
   - What we know: Python 3.10 `fromisoformat()` does not accept trailing `Z`. Python 3.11+ does.
   - What's unclear: Whether CDSE STAC items include trailing `Z` in datetime strings.
   - Recommendation: Strip trailing `Z` before parsing: `dt_str.rstrip("Z")`. Safe for both 3.10 and 3.11.

2. **RTC/CSLC download pattern after search fix**
   - What we know: Current code does `client.download(items[0], output_dir)` but `download()` takes `(s3_path: str, output_path: Path)`.
   - What's unclear: Whether `items[0]` from `items_as_dicts()` is being used as an S3 path or needs asset href extraction.
   - Recommendation: Follow DISP pattern -- extract `scene.get("assets", {}).get("data", {}).get("href", "")` for the S3 path. This is a secondary fix within B-02 scope.

## Project Constraints (from CLAUDE.md)

- **ruff** with line-length 100, target Python 3.10
- **mypy** strict mode (ignore_missing_imports for GDAL/ISCE3)
- **pytest** with `--cov=subsideo --cov-report=term-missing`, 80% coverage minimum
- **Lazy imports** for conda-forge deps inside function bodies
- **Never commit credentials**
- **hatchling** build backend, src layout

## Sources

### Primary (HIGH confidence)
- `src/subsideo/data/cdse.py` -- CDSEClient constructor (line 45), search_stac (line 86), download (line 136)
- `src/subsideo/data/dem.py` -- fetch_dem signature (line 14), returns tuple[Path, dict]
- `src/subsideo/data/orbits.py` -- fetch_orbit signature (line 10)
- `src/subsideo/burst/frames.py` -- query_bursts_for_aoi signature (line 12)
- `src/subsideo/burst/db.py` -- BurstRecord dataclass (line 45) with .epsg field
- `src/subsideo/config.py` -- Settings class with cdse_client_id/cdse_client_secret
- `src/subsideo/products/disp.py` -- working reference for search_stac, burst query, fetch_orbit
- `src/subsideo/products/dist.py` -- working reference for search_stac, burst query, fetch_orbit
- `tests/unit/test_disp_pipeline.py` -- test_run_disp_from_aoi_mocked (line 355) for mock patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, purely internal contract alignment
- Architecture: HIGH -- all correct patterns already exist in the codebase
- Pitfalls: HIGH -- bugs are concrete and reproducible from source inspection

**Research date:** 2026-04-05
**Valid until:** indefinite (internal codebase contracts, not external dependencies)
