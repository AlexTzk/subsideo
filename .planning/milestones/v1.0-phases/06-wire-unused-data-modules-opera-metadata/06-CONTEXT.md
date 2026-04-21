# Phase 6: Wire Unused Data Modules & OPERA Metadata - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire `fetch_ionex`, `ASFClient`, and `inject_opera_metadata` into their consumers so every Phase 1 data module has at least one caller, and all five product types carry OPERA-compliant identification metadata (provenance, version, run params). No new modules — only wiring existing code into existing pipelines.

</domain>

<decisions>
## Implementation Decisions

### IONEX Wiring into CSLC (DATA-05)
- **D-01:** Call `fetch_ionex` inside `run_cslc_from_aoi` after orbit fetch, before compass invocation — keeps data-fetch-then-process ordering consistent with all `*_from_aoi` functions.
- **D-02:** Source Earthdata credentials from `SubsideoSettings` (`EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD`) — same config pattern as CDSE credentials (Phase 5 D-01).
- **D-03:** IONEX download failure should warn and continue with `tec_file=None` — ionospheric correction is a refinement, not a hard requirement. Use try/except around `fetch_ionex`, log warning on failure.
- **D-04:** Extract the sensing date from the STAC item metadata (same `sensing_time` already parsed for orbit fetch) and pass to `fetch_ionex(date=sensing_time.date(), ...)`.

### ASF Auto-Fetch in Validate CLI (DATA-06)
- **D-05:** When `--reference` is omitted and Earthdata credentials are available, auto-fetch the matching OPERA N.Am. reference product from ASF DAAC using `ASFClient`.
- **D-06:** Auto-fetch applies to RTC and CSLC validation only — DISP uses EGMS (separate `--egms` flag), DSWx uses JRC (year/month), DIST has no reference product.
- **D-07:** If `--reference` is omitted AND Earthdata credentials are missing, print a clear error message explaining both options (provide `--reference` manually, or set `EARTHDATA_USERNAME`/`EARTHDATA_PASSWORD`).
- **D-08:** ASF search should match the product's AOI bounding box and approximate date range. Use the product's metadata (GeoTIFF tags or HDF5 attrs) to extract bbox and datetime for the search query.

### OPERA Metadata Injection (OUT-03)
- **D-09:** Call `inject_opera_metadata` in all five product pipelines (RTC, CSLC, DISP, DIST, DSWx) after product file is written, before returning the result — same pattern already used in DSWx.
- **D-10:** `software_version` should be read from package metadata via `importlib.metadata.version("subsideo")` — standard Python pattern, already set up by hatch-vcs.
- **D-11:** `product_type` strings: `"RTC-S1"`, `"CSLC-S1"`, `"DISP-S1"`, `"DIST-S1"`, `"DSWx-S2"` — matching OPERA product type identifiers.
- **D-12:** `run_params` should capture the essential pipeline inputs: AOI, date range, output directory, and any pipeline-specific config (e.g., DEM source for RTC, ERA5 correction flag for DISP).

### Credential Sourcing
- **D-13:** All Earthdata credentials (for both IONEX and ASF) come from `SubsideoSettings` — unified config approach, consistent with Phase 5's CDSE credential pattern.

### Testing Strategy
- **D-14:** Unit tests for each wiring point — mock `fetch_ionex`, `ASFClient`, and `inject_opera_metadata`, verify callers pass correct args. No integration tests.
- **D-15:** Test the validate CLI's auto-fetch path with mocked ASFClient.

### Claude's Discretion
- How to extract bbox/datetime from product files for ASF search matching
- Error message wording for missing credentials
- Whether to add a shared helper for `importlib.metadata.version("subsideo")` or inline it
- Exact `run_params` dict contents per product type

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Unwired Modules (the source APIs to wire)
- `src/subsideo/data/ionosphere.py` — `fetch_ionex(date, output_dir, username, password) -> Path`
- `src/subsideo/data/asf.py` — `ASFClient(username, password)` with `.search()` and `.download()` methods
- `src/subsideo/_metadata.py` — `inject_opera_metadata(product_path, product_type, software_version, run_params)`

### Consumer Files (where to add wiring)
- `src/subsideo/products/cslc.py` — `run_cslc_from_aoi` (~line 280+): add IONEX fetch + metadata injection
- `src/subsideo/products/rtc.py` — `run_rtc_from_aoi`: add metadata injection
- `src/subsideo/products/disp.py` — `run_disp_from_aoi`: add metadata injection
- `src/subsideo/products/dist.py` — `run_dist_from_aoi`: add metadata injection
- `src/subsideo/products/dswx.py` — already has metadata injection (line 421); verify correctness
- `src/subsideo/cli.py` — `validate_cmd` (~line 246): add ASF auto-fetch when `--reference` omitted

### Reference Patterns
- `src/subsideo/products/dswx.py:421` — existing `inject_opera_metadata` call pattern to replicate
- `src/subsideo/products/cslc.py:44` — existing `tec_file` parameter pass-through to compass runconfig
- `src/subsideo/config.py` — `SubsideoSettings` with Earthdata credential fields

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `inject_opera_metadata` in `_metadata.py`: fully implemented, handles both GeoTIFF and HDF5 formats
- `ASFClient` in `data/asf.py`: fully implemented with search and download methods
- `fetch_ionex` in `data/ionosphere.py`: fully implemented with Earthdata auth
- `SubsideoSettings` already has `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD` fields
- CSLC's `run_cslc` already accepts `tec_file` parameter and passes it to compass runconfig

### Established Patterns
- Lazy imports for conda-forge deps inside function bodies
- All `*_from_aoi` functions follow the same structure: settings → client → search → burst query → DEM → orbit → process → return
- DSWx metadata injection pattern: call after product write, before return

### Integration Points
- CSLC `run_cslc_from_aoi`: insert IONEX fetch between orbit fetch and `run_cslc()` call
- Each product's `*_from_aoi` or main processing function: insert metadata injection after file write
- CLI `validate_cmd`: insert ASF auto-fetch before the `reference_path is None` check

</code_context>

<specifics>
## Specific Ideas

No specific requirements — this is mechanical wiring work. All correct patterns already exist in the codebase (DSWx metadata injection, credential loading from Settings).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-wire-unused-data-modules-opera-metadata*
*Context gathered: 2026-04-05*
