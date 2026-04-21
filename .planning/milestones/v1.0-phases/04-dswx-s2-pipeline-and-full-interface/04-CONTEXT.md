# Phase 4: DSWx-S2 Pipeline and Full Interface - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce OPERA-spec DSWx-S2 surface water extent products from Sentinel-2 L2A data over EU AOIs, validated against JRC Global Surface Water monthly history maps. Complete the `subsideo` Typer CLI with all product subcommands (rtc, cslc, disp, dswx, dist, validate) and build the per-product validation report generator (HTML + Markdown with figures).

This phase does NOT include: new product types, real-time orchestration, containerization, or NISAR stubs.

</domain>

<decisions>
## Implementation Decisions

### DSWx-S2 Algorithm Porting
- **D-01:** Start with OPERA DSWx-HLS DSWE thresholds translated to Sentinel-2 L2A band equivalents. Validate against JRC. If F1 > 0.90, ship it. Only invest in EU-specific threshold tuning if OPERA defaults fail validation — do not front-load threshold R&D.
- **D-02:** Use Sentinel-2 L2A's built-in Scene Classification Layer (SCL) for cloud masking. Classes 8-10 (cloud medium/high probability, thin cirrus) and class 3 (cloud shadow) are masked out. No additional cloud detection library needed.
- **D-03:** Output at 30m UTM posting to match OPERA spec and maintain consistency with RTC/DISP output resolution. Sentinel-2 10m bands are downsampled during DSWE computation. JRC reference is also 30m, simplifying validation grid alignment.
- **D-04:** Follow the thin-wrapper pipeline pattern from Phase 2/3. Create `products/dswx.py` with `run_dswx()` (takes S2 L2A paths) and `run_dswx_from_aoi()` (takes AOI + date range, queries CDSE for S2 L2A via existing CDSEClient). Lazy imports for any heavy deps.

### JRC Global Surface Water Validation
- **D-05:** Validate against JRC Monthly Water History maps. Match DSWx output month to JRC month for temporal alignment. Binary comparison: DSWx water pixels vs JRC water-detected pixels.
- **D-06:** Download JRC tiles via direct HTTP from ec.europa.eu (no Google Earth Engine dependency). Tile-based download pattern similar to DEM download in Phase 1. Implement in `validation/compare_dswx.py`.
- **D-07:** Compute F1 score as primary metric (F1 > 0.90 pass criterion). Also compute precision, recall, and overall accuracy for diagnostic reporting. Reuse `validation/metrics.py` for any shared metric utilities.

### CLI Subcommand Design
- **D-08:** All product subcommands accept `--aoi path/to/aoi.geojson` (GeoJSON file path, validated as Polygon/MultiPolygon on load). No inline bbox or WKT — keep it simple.
- **D-09:** Date range via two separate flags: `--start 2025-01-01 --end 2025-03-01`. ISO 8601 date format. Consistent with most geospatial CLIs.
- **D-10:** Progress reporting via existing loguru structured logging with stage-level messages. `--verbose` flag for debug-level output. No progress bars — keeps output pipe-friendly and avoids adding rich as a runtime dep.
- **D-11:** Each product subcommand (`rtc`, `cslc`, `disp`, `dswx`, `dist`) calls the corresponding `run_{product}_from_aoi()` function. `validate` subcommand runs comparison modules on completed outputs.
- **D-12:** Output directory defaults to current working directory, overridable with `--out path/to/dir`. Each product creates a subdirectory within the output dir.

### Validation Report Generation
- **D-13:** Per-product reports (one HTML + one Markdown per product type). No combined summary report — keeps generation simple and reports focused.
- **D-14:** Each report includes: metric summary table (pass/fail per criterion), spatial difference map (matplotlib figure), and scatter plot (product vs reference with regression line). These two figure types plus the metric table are the minimum viable report.
- **D-15:** Use Jinja2 templates for HTML generation. Matplotlib generates figures as inline SVG (for HTML) or saved PNG (for Markdown). Report function in `validation/report.py`.
- **D-16:** OPERA-compliant identification metadata (OUT-03): all products must include provenance, software version, and run parameters in their output metadata. This applies to all existing products (RTC, CSLC, DISP, DIST) and the new DSWx.

### Claude's Discretion
- DSWx DSWE band index formulas and threshold mapping from HLS to S2 bands
- JRC tile URL pattern and download/caching implementation
- Jinja2 template design and CSS styling for HTML reports
- Internal helper functions for figure generation
- Whether to add `dist` as a CLI subcommand (dist-s1 may not be available yet)
- Test fixture design for DSWx and report generation tests

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specifications
- `BOOTSTRAP.md` — Full project brief with architecture decisions and validation strategy
- `pyproject.toml` — Package metadata, dependencies, tool configuration
- `.planning/PROJECT.md` — Living project context with constraints and key decisions
- `.planning/REQUIREMENTS.md` — Acceptance criteria for PROD-04, OUT-03, VAL-05, VAL-06, CLI-01, CLI-02

### Research Findings
- `.planning/research/STACK.md` — Verified technology stack versions
- `.planning/research/PITFALLS.md` — Critical pitfalls and prevention strategies
- `.planning/research/ARCHITECTURE.md` — Component boundaries, data flows

### Existing Code (patterns to follow)
- `src/subsideo/cli.py` — CLI skeleton with check-env subcommand (extend, don't rewrite)
- `src/subsideo/products/rtc.py` — Thin-wrapper pipeline pattern (run_rtc, run_rtc_from_aoi placeholder)
- `src/subsideo/products/disp.py` — AOI entry point pattern (run_disp_from_aoi)
- `src/subsideo/products/dist.py` — AOI entry point pattern (run_dist_from_aoi)
- `src/subsideo/products/types.py` — All Config/Result/ValidationResult dataclasses
- `src/subsideo/validation/compare_rtc.py` — Comparison module pattern (reproject to ref grid, compute metrics)
- `src/subsideo/validation/compare_disp.py` — EGMS comparison with download helper pattern
- `src/subsideo/validation/metrics.py` — Shared metric functions (rmse, spatial_correlation, bias, ssim)
- `src/subsideo/data/cdse.py` — CDSEClient with S2 L2A search already implemented (DATA-02)
- `src/subsideo/config.py` — Settings class with layered config

### External References
- No external specs — requirements fully captured in decisions above and REQUIREMENTS.md

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CDSEClient.search()` — already supports Sentinel-2 L2A via CDSE STAC (DATA-02 complete)
- `validation/metrics.py` — rmse(), spatial_correlation(), bias(), ssim() shared functions
- `compare_rtc.py` / `compare_disp.py` — reproject-to-reference-grid pattern ready to replicate
- `products/types.py` — extend with DSWxConfig, DSWxResult, DSWxValidationResult dataclasses
- `cli.py` — Typer app object ready for new subcommand registration

### Established Patterns
- Thin-wrapper orchestrator: build config → generate runconfig → lazy import → call API → validate → return result
- AOI entry point: parse AOI → query bursts/tiles → fetch data → run pipeline → return result
- Lazy imports for all conda-forge-only deps inside function bodies
- Dataclasses (not Pydantic) for result types

### Integration Points
- CLI subcommands register on the existing `app` Typer instance in cli.py
- Each subcommand calls `run_{product}_from_aoi()` from the corresponding products module
- `validate` subcommand needs to discover completed products and run the appropriate comparison module
- Report generation consumes ValidationResult dataclasses from comparison modules

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-dswx-s2-pipeline-and-full-interface*
*Context gathered: 2026-04-05*
