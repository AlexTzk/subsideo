# Phase 2: RTC-S1 and CSLC-S1 Pipelines - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce OPERA-spec RTC-S1 backscatter (COG GeoTIFF) and CSLC-S1 coregistered SLC (HDF5) products from Sentinel-1 IW SLC data over EU AOIs. Build the validation framework with shared metric functions (RMSE, spatial correlation, bias, SSIM) and per-product comparison modules that cross-compare outputs against OPERA North America reference products downloaded via ASF DAAC.

This phase does NOT include: DISP, DIST, or DSWx pipelines (Phase 3/4), the full CLI subcommands (Phase 4), or validation report generation (Phase 4).

</domain>

<decisions>
## Implementation Decisions

### RTC-S1 Pipeline
- **D-01:** Thin Python API wrapper around `opera-rtc` (OPERA-ADT reference implementation). Call opera-rtc's Python API directly — do not use subprocess/CLI invocation or reimplement RTC from raw isce3 calls. opera-rtc already produces spec-compliant 30m UTM COG output.
- **D-02:** The wrapper (`products/rtc.py`) orchestrates: fetch SLC via CDSEClient → resolve bursts via burst DB → fetch DEM via dem-stitcher → fetch orbits → generate opera-rtc runconfig → call opera-rtc → validate output.
- **D-03:** opera-rtc uses a YAML runconfig. Generate this programmatically from subsideo's Pydantic config, filling in paths to downloaded SLC, DEM, orbits, and output directory.

### CSLC-S1 Pipeline
- **D-04:** Config-driven compass execution via Python API. compass (OPERA-ADT CSLC workflow) uses YAML runconfig files matching the ISCE3 workflow convention already adopted in Phase 01 config.
- **D-05:** The wrapper (`products/cslc.py`) orchestrates: fetch SLC → resolve bursts → fetch DEM → fetch orbits → generate compass runconfig → call compass Python entry point → validate HDF5 output.
- **D-06:** Use `s1-reader` to parse Sentinel-1 SAFE/zip into burst objects. Use `opera-utils` for burst ID extraction and frame mapping. These are the canonical OPERA-ADT libraries for SLC ingestion.

### Validation Framework
- **D-07:** Shared metric functions in `validation/metrics.py`: RMSE, spatial correlation (Pearson r), bias, SSIM. These are reusable across all product types in Phase 3/4.
- **D-08:** Per-product comparison modules: `validation/compare_rtc.py` and `validation/compare_cslc.py`. Each handles loading the OPERA N.Am. reference product (different format per product type), aligning spatial grids, and calling the shared metrics.
- **D-09:** Reference products fetched from ASF DAAC via `data/asf.py` (built in Phase 01). The comparison modules accept paths to both the subsideo output and the OPERA reference, returning a structured metrics result.

### Output Format Compliance
- **D-10:** RTC output written as Cloud-Optimized GeoTIFF via `rio-cogeo` with OPERA-compliant metadata (provenance, software version, run parameters). 30m UTM posting.
- **D-11:** CSLC output written as HDF5 following OPERA CSLC product specification hierarchy, readable by `opera-utils`. Use `h5py` for structure, `opera-utils` product I/O helpers for metadata layout.
- **D-12:** Lightweight `validate_product()` function runs post-write to confirm required metadata fields, chunking, CRS, and structure. Fails loudly if spec check fails — do not silently produce non-compliant output.

### Claude's Discretion
- Internal helper functions and utility organization within products/ and validation/
- Test fixture design for mocked pipeline runs (synthetic arrays, fake HDF5/COG)
- Error message formatting for pipeline failures
- Whether to use xarray or raw numpy for intermediate array operations

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specifications
- `BOOTSTRAP.md` — Full project brief with architecture decisions and validation strategy
- `pyproject.toml` — Package metadata, dependencies, tool configuration
- `.planning/PROJECT.md` — Living project context with constraints and key decisions
- `.planning/REQUIREMENTS.md` — Acceptance criteria for PROD-01, PROD-02, OUT-01, OUT-02, VAL-01, VAL-02, VAL-03

### Research Findings
- `.planning/research/STACK.md` — Verified technology stack: opera-rtc v1.0.4, compass 0.5.6, isce3 0.25.10 versions and APIs
- `.planning/research/PITFALLS.md` — Critical pitfalls including CDSE S3 endpoint, conda-forge-only deps
- `.planning/research/ARCHITECTURE.md` — Component boundaries, data flows between modules

### Phase 01 Artifacts (foundation this phase builds on)
- `src/subsideo/data/cdse.py` — CDSEClient with OAuth2, STAC search, S3 download
- `src/subsideo/data/dem.py` — fetch_dem() with dem-stitcher GLO-30
- `src/subsideo/data/orbits.py` — fetch_orbit() with sentineleof
- `src/subsideo/data/asf.py` — ASFClient for OPERA reference product download
- `src/subsideo/burst/db.py` — EU burst DB build and query
- `src/subsideo/burst/frames.py` — query_bursts_for_aoi()
- `src/subsideo/config.py` — Settings class with layered config

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CDSEClient` (data/cdse.py): OAuth2 token management, STAC search, S3 download — used by both RTC and CSLC pipelines
- `fetch_dem()` (data/dem.py): GLO-30 DEM download and UTM warp — both pipelines need DEM
- `fetch_orbit()` (data/orbits.py): POEORB/RESORB orbit files — both pipelines need orbits
- `ASFClient` (data/asf.py): OPERA reference product download — used by validation modules
- `query_bursts_for_aoi()` (burst/frames.py): AOI → burst ID resolution
- `select_utm_epsg()` (burst/tiling.py): UTM zone selection for EU AOIs
- `Settings` (config.py): Pydantic config with YAML round-trip — pipeline configs extend this

### Established Patterns
- Loguru logging via `utils/logging.py`
- Pydantic models for structured config
- Unit tests with mocked I/O in `tests/unit/`
- Integration marker for tests requiring live credentials

### Integration Points
- New `src/subsideo/products/` package directory (rtc.py, cslc.py)
- New `src/subsideo/validation/` package directory (metrics.py, compare_rtc.py, compare_cslc.py)
- CLI subcommands `rtc` and `cslc` in cli.py (extend existing typer app)

</code_context>

<specifics>
## Specific Ideas

- opera-rtc and compass both consume YAML runconfigs — generate these from subsideo's Pydantic config to maintain a single source of truth
- Validation pass criteria are hard numbers from REQUIREMENTS.md: RTC RMSE < 0.5 dB, r > 0.99; CSLC phase RMS < 0.05 rad
- The validation metrics module should return structured results (dataclass/Pydantic model) so Phase 4 report generation can consume them directly
- Both pipelines share the same data fetch pattern (SLC + DEM + orbits) — consider a shared orchestration helper

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-rtc-s1-and-cslc-s1-pipelines*
*Context gathered: 2026-04-05*
