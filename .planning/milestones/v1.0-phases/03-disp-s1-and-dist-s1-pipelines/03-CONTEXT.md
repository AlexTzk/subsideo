# Phase 3: DISP-S1 and DIST-S1 Pipelines - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce OPERA-spec DISP-S1 displacement time-series products (dolphin phase linking → tophu unwrapping → MintPy time-series inversion with mandatory ERA5 tropospheric correction) and DIST-S1 surface disturbance products (dist-s1) from Sentinel-1 data over EU AOIs. Build EGMS EU validation comparison using EGMStoolkit for reference product download and vertical-component velocity comparison. DIST-S1 product validation uses the OPERA product validator (structural compliance check only — no EU-specific reference dataset for DIST).

This phase does NOT include: DSWx-S2 (Phase 4), CLI subcommands (Phase 4), or HTML validation reports (Phase 4).

</domain>

<decisions>
## Implementation Decisions

### DISP-S1 Pipeline Orchestration
- **D-01:** Single orchestrator in `products/disp.py` with `run_disp()`. Chains: CSLC stack → dolphin phase linking → tophu multi-scale unwrapping → MintPy time-series inversion. Matches the thin-wrapper pattern from Phase 2 (rtc.py, cslc.py).
- **D-02:** End-to-end AOI + date range interface. User provides AOI geometry + date range → pipeline runs CSLC (via Phase 2 `run_cslc()`) to build the stack → feeds CSLC HDF5 stack into dolphin → tophu → MintPy. Full automation, no manual intermediate steps.
- **D-03:** ERA5 tropospheric correction via MintPy/PyAPS3 is **mandatory**. Pipeline must fail if `~/.cdsapirc` is missing or CDS API key is invalid. Validate CDS credentials at pipeline start (before any processing) using the existing `check_env()` pattern from Phase 1.
- **D-04:** dolphin, tophu, and MintPy are called via their Python APIs (not subprocess). Lazy imports for all three (conda-forge-only deps). Generate YAML runconfigs programmatically from subsideo's Pydantic config, matching the Phase 1/2 pattern.

### Unwrapping Quality Control
- **D-05:** Automated post-unwrapping sanity check with flag-and-continue behavior. Fit a plane to the unwrapped phase; if residual exceeds a configurable threshold, FLAG the result in HDF5 metadata (warning field) but do not fail the pipeline. Log the anomaly via loguru.
- **D-06:** Coherence masking applied before unwrapping with configurable threshold (default 0.3). Pixels below the coherence threshold are masked out before feeding to tophu/snaphu. Threshold exposed in config as `coherence_mask_threshold`.

### EGMS Validation
- **D-07:** Use EGMS Ortho product level as validation reference. Ortho provides vertical and east-west displacement maps in mm/yr on a regular grid (GeoTIFF), easiest to compare against subsideo's geocoded output.
- **D-08:** Compare vertical component only. Project subsideo LOS velocity to vertical using incidence angle, then compare against EGMS Ortho vertical field. Standard approach in literature. Horizontal motion ignored in this validation.
- **D-09:** Use EGMStoolkit 0.2.15 for EGMS product download. It handles all 3 product levels, published 2024. Wrap in `validation/compare_disp.py` alongside the metrics computation.
- **D-10:** Validation module in `validation/compare_disp.py` accepts subsideo DISP output path + EGMS Ortho path, aligns grids via rasterio reproject, computes spatial correlation (r > 0.92) and absolute velocity bias (< 3 mm/yr). Reuse `validation/metrics.py` from Phase 2.

### DIST-S1 Integration
- **D-11:** Implement `products/dist.py` with full wrapper now, using conditional lazy import for dist-s1. If dist-s1 is not installed, raise a clear `ImportError` with conda-forge install instructions. Unit tests mock dist-s1.
- **D-12:** End-to-end AOI + date range interface for DIST, matching DISP pattern. User provides AOI + dates → pipeline runs RTC (via Phase 2 `run_rtc()`) to build time series → feeds RTC COG stack into dist-s1.
- **D-13:** DIST output as COG GeoTIFF with OPERA-compliant metadata. Validation is structural compliance only (OPERA product validator) — no EU-specific reference dataset exists for DIST.

### Claude's Discretion
- Internal helper functions for dolphin/tophu/MintPy config generation
- DISPConfig/DISPResult and DISTConfig/DISTResult dataclass design (extend products/types.py)
- Test fixture design for mocked dolphin/tophu/MintPy/dist-s1 outputs
- Whether to cache intermediate CSLC/RTC stacks when running end-to-end
- Error message formatting for multi-stage pipeline failures

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specifications
- `BOOTSTRAP.md` — Full project brief with architecture decisions and validation strategy
- `pyproject.toml` — Package metadata, dependencies, tool configuration
- `.planning/PROJECT.md` — Living project context with constraints and key decisions
- `.planning/REQUIREMENTS.md` — Acceptance criteria for PROD-03, PROD-05, VAL-04

### Research Findings
- `.planning/research/STACK.md` — Verified technology stack: dolphin 0.42.5, tophu 0.2.1, snaphu-py 0.4.1, MintPy 1.6.3, pyaps3 0.3.6, EGMStoolkit 0.2.15
- `.planning/research/PITFALLS.md` — Critical pitfalls including pyaps3 0.3.6 requirement for new CDS API, SNAPHU non-commercial license
- `.planning/research/ARCHITECTURE.md` — Component boundaries, data flows

### Phase 2 Artifacts (pipelines this phase builds on)
- `src/subsideo/products/rtc.py` — run_rtc() orchestrator (DIST-S1 input)
- `src/subsideo/products/cslc.py` — run_cslc() orchestrator (DISP-S1 input)
- `src/subsideo/products/types.py` — RTCConfig, CSLCConfig, RTCResult, CSLCResult, RTCValidationResult, CSLCValidationResult
- `src/subsideo/validation/metrics.py` — rmse(), spatial_correlation(), bias(), ssim() shared metrics
- `src/subsideo/validation/compare_rtc.py` — RTC comparison pattern to replicate for DISP
- `src/subsideo/validation/compare_cslc.py` — CSLC comparison pattern

### Phase 1 Artifacts (data layer)
- `src/subsideo/data/cdse.py` — CDSEClient for CDSE S3 data access
- `src/subsideo/data/dem.py` — fetch_dem() for GLO-30 DEM
- `src/subsideo/data/orbits.py` — fetch_orbit() for POE/RESORB
- `src/subsideo/burst/db.py` — EU burst DB query
- `src/subsideo/config.py` — Settings class with layered config

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_cslc()` (products/cslc.py): CSLC orchestrator — DISP pipeline chains from its output
- `run_rtc()` (products/rtc.py): RTC orchestrator — DIST pipeline chains from its output
- `validation/metrics.py`: rmse(), spatial_correlation(), bias(), ssim() — reuse for DISP/EGMS comparison
- `compare_rtc.py` / `compare_cslc.py`: Comparison module pattern (grid alignment, structured results) to replicate for DISP

### Established Patterns
- Thin wrapper pattern: generate YAML runconfig → call library Python API → validate output → return structured result
- Lazy imports for conda-forge-only deps (isce3, opera-rtc, compass)
- Dataclasses in types.py for config and result containers
- Unit tests with mocked external deps, pytest markers for integration/validation

### Integration Points
- `products/types.py`: Add DISPConfig, DISPResult, DISTConfig, DISTResult, DISPValidationResult
- `config.py`: Add DISP/DIST-specific config fields (coherence_mask_threshold, era5 settings)
- `validation/`: Add compare_disp.py for EGMS comparison

</code_context>

<specifics>
## Specific Ideas

- DISP pipeline must validate CDS credentials at startup (before any CSLC processing begins) since ERA5 correction is mandatory
- EGMS Ortho comparison should handle the case where EGMS coverage doesn't fully overlap the AOI — compute metrics only over the intersection
- dist-s1 conditional import pattern should match the existing lazy import pattern used for isce3/compass in Phase 2

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-disp-s1-and-dist-s1-pipelines*
*Context gathered: 2026-04-05*
