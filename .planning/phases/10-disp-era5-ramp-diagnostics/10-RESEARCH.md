# Phase 10 Research: DISP ERA5 & Ramp Diagnostics

**Phase:** 10 - DISP ERA5 & Ramp Diagnostics
**Date:** 2026-05-03
**Status:** Complete

## Objective

Plan how to rerun the v1.1 SoCal and Bologna DISP cells with an ERA5 toggle, add shared orbit/DEM/terrain/cache provenance, and convert the deltas into honest Phase 11 ordering guidance without changing the production unwrapper.

## Key Findings

### Current Code Surface

- `run_eval_disp.py` and `run_eval_disp_egms.py` already warm-start from cached `disp/dolphin/timeseries/velocity.tif`, write `metrics.json` and `meta.json`, and compute `RampAttribution`.
- `src/subsideo/products/disp.py` currently treats CDS credentials and ERA5 as mandatory: `_validate_cds_credentials()` raises on missing `.cdsapirc`, `_generate_mintpy_template()` always writes `mintpy.troposphericDelay.method = pyaps` and `mintpy.troposphericDelay.weatherModel = ERA5`, and `run_disp()` always validates CDS credentials.
- `src/subsideo/validation/matrix_schema.py` already contains `AttributedSource = Literal["phass", "orbit", "tropospheric", "mixed", "inconclusive"]`. Phase 10 should not add `inconclusive_narrowed`; it should add structured details under the existing `RampAttribution` / `DISPCellMetrics` shape.
- `src/subsideo/validation/selfconsistency.py` already provides `fit_planar_ramp()`, `compute_ramp_aggregate()`, and `auto_attribute_ramp()`. The current auto-rule never returns `tropospheric`, which matches the Phase 10 decision to keep tropospheric verdicts evidence-driven from ERA5 deltas.
- `src/subsideo/data/orbits.py` returns EOF paths but does not parse validity windows. Phase 10 needs a small parser/helper for orbit validity coverage.
- `src/subsideo/data/dem.py` uses `dem_stitcher.stitch_dem(..., dem_name="glo_30")` and writes `glo30_utm{epsg}.tif`; the provenance helper can summarize this raster and hash it without changing DEM fetching.

### External ERA5 / PyAPS / MintPy Notes

- Copernicus CDS API access now uses a personal access token in `$HOME/.cdsapirc` and the new endpoint `https://cds.climate.copernicus.eu/api`; legacy CDS credentials can fail authentication. Sources: [CDS API setup](https://cds.climate.copernicus.eu/en/how-to-api), [ECMWF CDS documentation](https://confluence.ecmwf.int/display/CKB/Climate%2BData%2BStore%2B%28CDS%29%2Bdocumentation?preview=%2F174856258%2F453323309%2Fnewcdsrequestlimit.png).
- PyAPS3 documents ERA5 as the active weather model path and requires CDS account setup plus accepted ERA5 data terms before download tests pass. Source: [PyAPS README](https://github.com/insarlab/PyAPS).
- MintPy's `smallbaselineApp` supports `mintpy.troposphericDelay.method = pyaps` and `mintpy.troposphericDelay.weatherModel = ERA5`; the template also supports disabling troposphere correction with `method = no` and using a weather directory to reuse downloads. Source: [MintPy README / template snippets](https://github.com/insarlab/MintPy).

### Baselines to Preserve

The v1.1 brief is the baseline, not a result to be recomputed before implementation:

| Cell | Reference | r | Bias mm/yr | RMSE mm/yr | Mean Ramp rad | Direction Sigma deg | Attribution |
|------|-----------|---|------------|------------|---------------|---------------------|-------------|
| SoCal | OPERA DISP-S1 | 0.0490 | +23.6153 | 59.5567 | 35.5881 | 124.5336 | `inconclusive` |
| Bologna | EGMS L2a | 0.3358 | +3.4608 | 5.2425 | 25.9980 | 117.0968 | `inconclusive` |

### Implementation Shape

- Add an explicit ERA5 mode, likely `era5_mode: Literal["on", "off"]`, to `run_disp()` and the eval scripts.
- Keep existing output directories as v1.1 baseline caches. For ERA5-on diagnostic reruns, write to distinct directories such as `eval-disp/disp-era5-on` and `eval-disp-egms/disp-era5-on` to avoid overwriting v1.1 no-ERA5/off sidecars.
- Add helper functions for diagnostic provenance rather than embedding all logic in eval scripts. Likely module: `src/subsideo/validation/disp_diagnostics.py`.
- Extend Pydantic schemas additively:
  - `Era5Diagnostic`
  - `CauseAssessment`
  - `TerrainDiagnostics`
  - `OrbitCoverageDiagnostic`
  - `DemDiagnostics`
  - `CacheProvenance`
  - optional fields on `DISPCellMetrics`
- Keep `meta.json.input_hashes` for legacy compatibility and add richer cache/provenance structures inside `metrics.json` or nested sidecar objects. The Phase 10 context says diagnostic provenance sidecars are canonical; existing code already treats `metrics.json` as the canonical scientific sidecar and `meta.json` as provenance sidecar.
- Add unit tests before live rerun expectations. Live commands (`make eval-disp-nam`, `make eval-disp-eu`) may block only for CDS API / ERA5 data access failures; local code failures are implementation work.

## Validation Architecture

### Unit Validation

- Schema round-trip tests must prove legacy v1.1 DISP sidecars still validate when new Phase 10 fields are absent.
- Schema tests must reject invalid cause literals and reject `inconclusive_narrowed` as `attributed_source`.
- Helper tests must cover:
  - two-signal improvement classification,
  - ERA5 no-improvement eliminating `tropospheric` only when metrics are sane,
  - terrain summary with slope/elevation/stable-mask/terrain-ramp correlation,
  - orbit validity coverage parsing from EOF names/header text or conservative unavailable status,
  - cache mode literals: `reused`, `regenerated`, `redownloaded`.

### Script Validation

- `run_eval_disp.py` and `run_eval_disp_egms.py` must expose a deterministic ERA5 toggle and write the selected mode into `metrics.json`.
- `make eval-disp-nam` and `make eval-disp-eu` remain the user-facing commands.
- Focused tests may inspect source for the exact config strings:
  - ERA5-on template contains `mintpy.troposphericDelay.method = pyaps`
  - ERA5-off template contains `mintpy.troposphericDelay.method = no`
  - ERA5-on output directory is distinct from v1.1 baseline output.

### Result Validation

- Conclusions must compare against the fixed v1.1 baselines above.
- A Phase 11 global ordering change requires at least two improvement signals in both cells or otherwise cross-cell support:
  - attribution flip,
  - reference correlation improvement,
  - bias/RMSE improvement,
  - ramp magnitude reduction.
- One-cell-only improvement becomes a cell-specific note and keeps the v1.1 global Phase 11 order: SPURT native, PHASS deramping, tophu/SNAPHU, 20 x 20 m fallback.

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| CDS API credentials or ERA5 license blocks live reruns | Treat as named blocker only when `.cdsapirc` and license/data access fail after local code path is validated. |
| ERA5-on overwrites v1.1 warm baseline | Use distinct ERA5-on output dirs and explicit sidecar `era5_mode`. |
| Schema change breaks old matrix rendering | Add optional fields only and test old fixtures. |
| Attribution overclaims `tropospheric` | Keep `attributed_source="inconclusive"` unless deterministic evidence supports another existing literal; store narrowed detail in `eliminated_causes`, `remaining_causes`, and `next_test`. |
| Conclusions drift from sidecars | Require schema-valid sidecars before conclusions edits and cite sidecar fields in tables. |

## Recommended Plan Split

1. Schema and diagnostic helper contract.
2. ERA5 toggle through `run_disp()` and both eval scripts.
3. Orbit/DEM/terrain/cache provenance collection and sidecar writes.
4. Conclusions/methodology updates plus rerun/blocker verification.

## Sources

- `.planning/phases/10-disp-era5-ramp-diagnostics/10-CONTEXT.md`
- `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md`
- `run_eval_disp.py`
- `run_eval_disp_egms.py`
- `src/subsideo/products/disp.py`
- `src/subsideo/validation/matrix_schema.py`
- `src/subsideo/validation/selfconsistency.py`
- [CDS API setup](https://cds.climate.copernicus.eu/en/how-to-api)
- [ECMWF CDS documentation](https://confluence.ecmwf.int/display/CKB/Climate%2BData%2BStore%2B%28CDS%29%2Bdocumentation?preview=%2F174856258%2F453323309%2Fnewcdsrequestlimit.png)
- [PyAPS README](https://github.com/insarlab/PyAPS)
- [MintPy README](https://github.com/insarlab/MintPy)

## RESEARCH COMPLETE
