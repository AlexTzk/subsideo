# Phase 6: Wire Unused Data Modules & OPERA Metadata - Research

**Researched:** 2026-04-05
**Domain:** Python pipeline wiring, OPERA metadata injection, CLI auto-fetch
**Confidence:** HIGH

## Summary

Phase 6 is mechanical wiring work. All three target modules (`fetch_ionex`, `ASFClient`, `inject_opera_metadata`) are fully implemented and tested in isolation. The DSWx pipeline already demonstrates the correct metadata injection pattern. The task is to replicate existing patterns into four more product pipelines and wire two unused data modules into their consumers.

The codebase has strong conventions established over five prior phases: lazy imports for conda-forge deps, `Settings` for credential access, try/except with warn-and-continue for optional features, and mock-heavy unit tests for pipeline orchestrators. Every change in this phase follows one of these existing patterns exactly.

**Primary recommendation:** Follow the DSWx metadata injection pattern (dswx.py:420-432) as the template for all four remaining pipelines. Wire `fetch_ionex` into `run_cslc_from_aoi` between orbit fetch and `run_cslc()` call. Wire `ASFClient` into `validate_cmd` as an auto-fetch fallback when `--reference` is omitted.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Call `fetch_ionex` inside `run_cslc_from_aoi` after orbit fetch, before compass invocation
- **D-02:** Source Earthdata credentials from `SubsideoSettings` (`EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD`)
- **D-03:** IONEX download failure should warn and continue with `tec_file=None` (try/except, log warning)
- **D-04:** Extract sensing date from STAC item metadata (same `sensing_time` already parsed for orbit fetch)
- **D-05:** When `--reference` omitted and Earthdata creds available, auto-fetch OPERA reference from ASF
- **D-06:** Auto-fetch applies to RTC and CSLC validation only (DISP uses EGMS, DSWx uses JRC, DIST has no ref)
- **D-07:** If `--reference` omitted AND no Earthdata creds, print clear error explaining both options
- **D-08:** ASF search matches product's AOI bbox and date range from product metadata (GeoTIFF tags or HDF5 attrs)
- **D-09:** Call `inject_opera_metadata` in all five pipelines after product write, before return
- **D-10:** `software_version` via `importlib.metadata.version("subsideo")`
- **D-11:** Product type strings: `"RTC-S1"`, `"CSLC-S1"`, `"DISP-S1"`, `"DIST-S1"`, `"DSWx-S2"`
- **D-12:** `run_params` captures AOI, date range, output dir, and pipeline-specific config
- **D-13:** All Earthdata credentials from `SubsideoSettings` (unified config)
- **D-14:** Unit tests mock `fetch_ionex`, `ASFClient`, `inject_opera_metadata`; verify callers pass correct args
- **D-15:** Test validate CLI auto-fetch path with mocked ASFClient

### Claude's Discretion
- How to extract bbox/datetime from product files for ASF search matching
- Error message wording for missing credentials
- Whether to add a shared helper for `importlib.metadata.version("subsideo")` or inline it
- Exact `run_params` dict contents per product type

### Deferred Ideas (OUT OF SCOPE)
None.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-05 | Library can download IONEX TEC maps for ionospheric correction | `fetch_ionex` is fully implemented in `data/ionosphere.py`; needs wiring into `run_cslc_from_aoi` between orbit fetch and `run_cslc()` call |
| DATA-06 | Library can search and download OPERA reference products from ASF DAAC | `ASFClient` is fully implemented in `data/asf.py`; needs wiring into `validate_cmd` as auto-fetch fallback |
| OUT-03 | All products include OPERA-compliant identification metadata | `inject_opera_metadata` in `_metadata.py` handles GeoTIFF and HDF5; currently only called in DSWx; needs replication to RTC, CSLC, DISP, DIST |
</phase_requirements>

## Architecture Patterns

### Existing Pattern: DSWx Metadata Injection (the template)
**What:** `inject_opera_metadata` called after product file is written, before result is returned
**Where:** `src/subsideo/products/dswx.py` lines 420-432
**Example:**
```python
# 6. Inject OPERA metadata
from subsideo._metadata import inject_opera_metadata

inject_opera_metadata(
    output_path,
    product_type="DSWx-S2",
    software_version=cfg.product_version,
    run_params={
        "s2_bands": [str(p) for p in cfg.s2_band_paths.values()],
        "scl_path": str(cfg.scl_path),
        "output_posting_m": cfg.output_posting_m,
    },
)
```

### Pattern: Software Version via importlib.metadata
**What:** Read package version at runtime instead of hardcoding
**Recommendation:** Create a small helper since it will be called in 5 places:
```python
# In _metadata.py or a new helper
def get_software_version() -> str:
    from importlib.metadata import version, PackageNotFoundError
    try:
        return version("subsideo")
    except PackageNotFoundError:
        return "dev"
```
This avoids duplicating the try/except in every pipeline module. The DSWx pattern currently uses `cfg.product_version` which is a config default `"0.1.0"` -- D-10 explicitly says to use `importlib.metadata` instead.

### Pattern: Warn-and-Continue for Optional Data (IONEX)
**What:** try/except around optional data fetch, log warning, continue with None
**Established by:** Phase 3's post-unwrap QC (flag-and-continue pattern)
```python
# In run_cslc_from_aoi, after orbit fetch:
tec_file = None
try:
    from subsideo.data.ionosphere import fetch_ionex
    tec_file = fetch_ionex(
        date=sensing_time.date(),
        output_dir=output_dir / "ionex",
        username=settings.earthdata_username,
        password=settings.earthdata_password,
    )
except Exception:
    logger.warning("IONEX download failed; proceeding without ionospheric correction")
```

### Pattern: ASF Auto-Fetch in Validate CLI
**What:** When `--reference` is omitted for RTC/CSLC, auto-fetch from ASF
**Where:** `cli.py` validate_cmd, before the existing `reference_path is None` checks
**Key details:**
- Only for `pt in ("rtc", "cslc")` -- per D-06
- Extract bbox from product GeoTIFF tags (rasterio `ds.bounds`) or HDF5 attrs
- Extract datetime from product filename or metadata
- Use OPERA short names: `"OPERA_L2_RTC-S1_V1"` for RTC, `"OPERA_L2_CSLC-S1_V1"` for CSLC
- Download to a temp dir under `out`

### Insertion Points (exact locations)

| File | Function | Insert After | What to Add |
|------|----------|-------------|-------------|
| `products/cslc.py` | `run_cslc_from_aoi` | Line ~341 (orbit fetch) | IONEX fetch (try/except) |
| `products/cslc.py` | `run_cslc_from_aoi` | Line ~357 (before return) | Pass `tec_file` to `run_cslc()` |
| `products/cslc.py` | `run_cslc` | After line ~206 (validate) | Metadata injection on each h5_path |
| `products/rtc.py` | `run_rtc` | After line ~237 (validate) | Metadata injection on each cog_path |
| `products/disp.py` | `run_disp` | After line ~358 (MintPy) | Metadata injection on velocity.h5 and ts paths |
| `products/dist.py` | `run_dist` | After line ~201 (validate) | Metadata injection on each cog_path |
| `products/dswx.py` | `run_dswx` | Already done (line 421) | Verify; update to use `importlib.metadata` |
| `cli.py` | `validate_cmd` | Before line ~279 (rtc check) | ASF auto-fetch block |

### Metadata Injection Per Product Type

| Product | File Format | Product Type String | Output Paths Source | run_params Keys |
|---------|------------|-------------------|-------------------|-----------------|
| RTC | GeoTIFF (.tif) | `"RTC-S1"` | `cog_paths` list | safe_paths, orbit, dem, burst_ids, output_dir |
| CSLC | HDF5 (.h5) | `"CSLC-S1"` | `h5_paths` list | safe_paths, orbit, dem, burst_ids, tec_file |
| DISP | HDF5 (.h5) | `"DISP-S1"` | velocity.h5 + ts_paths | cslc_count, coherence_threshold, ramp_threshold, era5_correction |
| DIST | GeoTIFF (.tif) | `"DIST-S1"` | `cog_paths` list | mgrs_tile_id, track_number, post_date |
| DSWx | GeoTIFF (.tif) | `"DSWx-S2"` | single output_path | s2_bands, scl_path, output_posting_m |

### Extracting Bbox/Datetime from Products for ASF Search (Claude's Discretion)

For the validate CLI auto-fetch, product metadata extraction:

**GeoTIFF (RTC):**
```python
import rasterio
with rasterio.open(product_files[0]) as ds:
    bounds = ds.bounds  # BoundingBox(left, bottom, right, top)
    bbox = [bounds.left, bounds.bottom, bounds.right, bounds.top]
    # For datetime: parse from filename or tags
    tags = ds.tags()
    production_dt = tags.get("PRODUCTION_DATETIME", "")
```

**HDF5 (CSLC):**
```python
import h5py
with h5py.File(product_files[0], "r") as f:
    if "identification" in f:
        attrs = dict(f["identification"].attrs)
        # Parse run_params for date info
```

**Simpler approach:** Since we are injecting OPERA metadata (with `RUN_PARAMETERS` containing AOI/dates) in this same phase, the auto-fetch can read back those tags after injection. However, for the initial validate call (before this phase lands), a filename-based or user-supplied fallback is safer.

**Recommendation:** Accept optional `--start`/`--end` on the validate command for ASF date filtering, and derive bbox from the product's CRS bounds reprojected to WGS84. This is more robust than parsing filenames.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Package version at runtime | Hardcoded version string | `importlib.metadata.version("subsideo")` | hatch-vcs already manages this; stays in sync with git tags |
| Bbox extraction from rasters | Manual coordinate parsing | `rasterio.open().bounds` + `pyproj` transform to WGS84 | Handles any CRS correctly |
| OPERA product short names | Custom string mapping | Hardcoded constants: `"OPERA_L2_RTC-S1_V1"`, `"OPERA_L2_CSLC-S1_V1"` | These are fixed ASF catalog identifiers |

## Common Pitfalls

### Pitfall 1: Metadata Injection on Invalid Products
**What goes wrong:** Calling `inject_opera_metadata` on a product that failed validation (file doesn't exist or is corrupt)
**Why it happens:** Metadata injection placed before validation check, or on all paths including error paths
**How to avoid:** Only inject metadata when product files exist and pipeline didn't error. Place injection after output collection, before validation (matching DSWx pattern), or guard with `if path.exists()`.
**Warning signs:** `FileNotFoundError` or `rasterio.errors.RasterioIOError` from metadata injection

### Pitfall 2: IONEX Failure Breaking CSLC Pipeline
**What goes wrong:** `fetch_ionex` raises (network timeout, auth failure, missing IONEX for date) and crashes `run_cslc_from_aoi`
**Why it happens:** Not wrapping in try/except per D-03
**How to avoid:** Wrap in try/except Exception, log warning, set `tec_file=None`, continue
**Warning signs:** CSLC pipeline fails on dates where IONEX isn't available (recent dates, pre-1998)

### Pitfall 3: UTM Bounds Passed to ASF Search as WGS84
**What goes wrong:** Product bounds are in UTM (meters), but ASF search expects WGS84 (degrees). Passing raw UTM bounds returns zero results.
**Why it happens:** `rasterio.open().bounds` returns coordinates in the file's native CRS
**How to avoid:** Reproject bounds to EPSG:4326 using `pyproj.Transformer` before passing to `ASFClient.search(bbox=...)`
**Warning signs:** ASF search returns empty results for valid products

### Pitfall 4: DISP Has Multiple Output Files
**What goes wrong:** Only injecting metadata into `velocity.h5` but missing time-series HDF5 files
**Why it happens:** DISP produces multiple outputs (velocity + time-series files)
**How to avoid:** Iterate over all HDF5 outputs from MintPy, inject metadata into each
**Warning signs:** Some DISP outputs missing OPERA identification metadata

### Pitfall 5: DIST Returns list[DISTResult] Not DISTResult
**What goes wrong:** Metadata injection code assumes single result object
**Why it happens:** `run_dist_from_aoi` returns `list[DISTResult]` (one per MGRS tile)
**How to avoid:** Inject metadata inside `run_dist()` (the per-tile function), not in `run_dist_from_aoi`
**Warning signs:** N/A -- this is a code structure issue caught by reading the types

### Pitfall 6: ASF Auto-Fetch Credential Check
**What goes wrong:** Auto-fetch attempted without credentials, causing cryptic `earthaccess` auth errors
**Why it happens:** Settings has empty default strings for earthdata credentials
**How to avoid:** Check `settings.earthdata_username and settings.earthdata_password` before attempting auto-fetch; fall through to clear error message per D-07
**Warning signs:** `earthaccess.login()` errors in validate command

## Code Examples

### IONEX Wiring in run_cslc_from_aoi
```python
# After orbit fetch (line ~341), before run_cslc call:
tec_file = None
try:
    from subsideo.data.ionosphere import fetch_ionex
    tec_file = fetch_ionex(
        date=sensing_time.date(),
        output_dir=output_dir / "ionex",
        username=settings.earthdata_username,
        password=settings.earthdata_password,
    )
except Exception:
    logger.warning("IONEX download failed; proceeding without ionospheric correction")

# Then pass tec_file to run_cslc:
return run_cslc(
    safe_paths=safe_paths,
    orbit_path=orbit_path,
    dem_path=dem_path,
    burst_ids=burst_ids,
    output_dir=output_dir,
    tec_file=tec_file,  # <-- NEW
)
```

### Metadata Injection in run_rtc (representative example)
```python
# After validate_rtc_product, before building RTCResult:
from subsideo._metadata import inject_opera_metadata

sw_version = _get_software_version()
for cog_path in cog_paths:
    if cog_path.exists():
        inject_opera_metadata(
            cog_path,
            product_type="RTC-S1",
            software_version=sw_version,
            run_params={
                "safe_paths": [str(p) for p in safe_paths],
                "orbit_path": str(orbit_path),
                "dem_path": str(dem_path),
                "burst_ids": burst_ids,
                "output_dir": str(output_dir),
            },
        )
```

### ASF Auto-Fetch in validate_cmd
```python
# In validate_cmd, before the existing rtc/cslc reference_path checks:
if pt in ("rtc", "cslc") and reference_path is None:
    from subsideo.config import Settings
    settings = Settings()
    if settings.earthdata_username and settings.earthdata_password:
        try:
            from subsideo.data.asf import ASFClient
            import rasterio
            from pyproj import Transformer

            # Extract bbox from product (reproject UTM -> WGS84)
            with rasterio.open(product_files[0]) as ds:
                b = ds.bounds
                crs = ds.crs
            transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
            x1, y1 = transformer.transform(b.left, b.bottom)
            x2, y2 = transformer.transform(b.right, b.top)
            bbox = [x1, y1, x2, y2]

            # Determine date range from product tags
            tags = {}
            with rasterio.open(product_files[0]) as ds:
                tags = ds.tags()
            # ... parse PRODUCTION_DATETIME or RUN_PARAMETERS

            short_name = "OPERA_L2_RTC-S1_V1" if pt == "rtc" else "OPERA_L2_CSLC-S1_V1"
            asf = ASFClient(settings.earthdata_username, settings.earthdata_password)
            results = asf.search(short_name=short_name, bbox=bbox, start=start_dt, end=end_dt)
            if results:
                urls = [r.get("url", "") for r in results[:1]]
                ref_dir = out / "asf_reference"
                downloaded = asf.download(urls, ref_dir)
                if downloaded:
                    reference_path = downloaded[0]
        except Exception as exc:
            typer.echo(f"[WARNING] ASF auto-fetch failed: {exc}", err=True)
    else:
        typer.echo(
            "[FAIL] RTC/CSLC validation requires a reference product.\n"
            "Either provide --reference <path> or set EARTHDATA_USERNAME "
            "and EARTHDATA_PASSWORD for automatic ASF DAAC download.",
            err=True,
        )
        raise typer.Exit(code=1)
```

### Software Version Helper
```python
# In _metadata.py, add:
def get_software_version() -> str:
    """Get subsideo package version from installed metadata."""
    from importlib.metadata import PackageNotFoundError, version
    try:
        return version("subsideo")
    except PackageNotFoundError:
        return "dev"
```

## State of the Art

No changes relevant to this phase. All libraries and patterns are stable and already in use.

## Open Questions

1. **ASF OPERA Product Short Names**
   - What we know: ASF uses short names like `"OPERA_L2_RTC-S1_V1"` for product search
   - What's unclear: Exact short name strings for current OPERA product versions
   - Recommendation: Use the known format; if search returns empty, the auto-fetch gracefully falls back to the "reference required" error. LOW risk since this is validation-only.

2. **Date Range for ASF Search**
   - What we know: Product files may not have easily parseable acquisition dates in metadata
   - What's unclear: Best source of date info before OPERA metadata is injected
   - Recommendation: Add `--start`/`--end` as optional params to `validate_cmd` for ASF date range. If not provided, use a wide window (e.g., 30 days around file modification time). This is a Claude's Discretion item.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `src/subsideo/products/dswx.py:420-432` -- existing metadata injection pattern
- Codebase inspection: `src/subsideo/_metadata.py` -- full `inject_opera_metadata` implementation
- Codebase inspection: `src/subsideo/data/ionosphere.py` -- full `fetch_ionex` implementation
- Codebase inspection: `src/subsideo/data/asf.py` -- full `ASFClient` implementation
- Codebase inspection: `src/subsideo/config.py` -- `Settings` with earthdata credential fields
- Codebase inspection: `src/subsideo/cli.py` -- current `validate_cmd` structure
- Codebase inspection: all five product modules (rtc.py, cslc.py, disp.py, dist.py, dswx.py)
- Python docs: `importlib.metadata.version()` -- standard library, stable API

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries needed; all deps already in project
- Architecture: HIGH -- replicating existing DSWx pattern to 4 more pipelines
- Pitfalls: HIGH -- identified from direct code inspection of insertion points and type signatures

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable -- purely internal wiring, no external API changes)
