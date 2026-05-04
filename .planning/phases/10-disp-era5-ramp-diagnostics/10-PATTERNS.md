# Phase 10 Pattern Map

**Phase:** 10 - DISP ERA5 & Ramp Diagnostics
**Date:** 2026-05-03

## Files to Modify or Create

| Target | Role | Closest Existing Analog | Pattern to Reuse |
|--------|------|-------------------------|------------------|
| `src/subsideo/validation/matrix_schema.py` | Additive Pydantic sidecar contract | `DISPCellMetrics`, `RampAttribution`, `CSLCCandidateBindingResult` | `BaseModel`, `ConfigDict(extra="forbid")`, optional additive fields for backward compatibility |
| `src/subsideo/validation/disp_diagnostics.py` | Pure helper module for ERA5 deltas and provenance summaries | `src/subsideo/validation/selfconsistency.py` | Pure functions, lazy geospatial imports inside functions, no I/O at import time |
| `src/subsideo/products/disp.py` | ERA5 toggle in pipeline config | `_generate_mintpy_template()`, `_validate_cds_credentials()`, `run_disp()` | Explicit parameters, fail fast only when ERA5-on requires CDS credentials |
| `run_eval_disp.py` | SoCal ERA5 diagnostic script wiring | Existing Stage 7, Stage 11, Stage 12 blocks | Warm output probing, explicit constants, sidecar construction through Pydantic models |
| `run_eval_disp_egms.py` | Bologna ERA5 diagnostic script wiring | Existing Stage 7, Stage 11, Stage 12 blocks | Same shape as SoCal while preserving EGMS-specific reference logic |
| `src/subsideo/validation/matrix_writer.py` | Matrix display of diagnostic flags | `_render_disp_cell()` | Shape detection by `ramp_attribution`; compact PQ annotation |
| `CONCLUSIONS_DISP_N_AM.md` | Human-facing SoCal verdict | Existing v1.1 conclusions tables | Sidecar-backed tables, no matrix parsing from conclusions |
| `CONCLUSIONS_DISP_EU.md` | Human-facing Bologna verdict | Existing v1.1 conclusions tables | Same structure as SoCal with EGMS notes |
| `docs/validation_methodology.md` | Methodology update | DISP multilook section | Explicit separation of product-quality, reference-agreement, and diagnostic attribution |
| `tests/product_quality/test_matrix_schema_disp.py` | Schema regression tests | Existing DISP schema tests | Validate Pydantic round-trip and literal rejection |
| `tests/product_quality/test_selfconsistency_ramp.py` or new `tests/product_quality/test_disp_diagnostics.py` | Diagnostic helper tests | Existing pure-function tests | Numpy fixtures, no network, deterministic thresholds |
| `tests/unit/test_disp_pipeline.py` | ERA5 template/pipeline tests | Existing `_generate_mintpy_template` tests | Mocked pipeline, source-visible config assertions |
| `tests/reference_agreement/test_matrix_writer_disp.py` | Matrix rendering tests | Existing DISP render tests | Small synthetic sidecar fixture |

## Concrete Code Excerpts

### Pydantic Schema Style

Existing schema classes use:

```python
class RampAttribution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    per_ifg: list[PerIFGRamp] = Field(default_factory=list)
```

Phase 10 should follow this style for new diagnostic models and use optional fields on `DISPCellMetrics`:

```python
era5_diagnostic: Era5Diagnostic | None = None
cause_assessment: CauseAssessment | None = None
terrain_diagnostics: TerrainDiagnostics | None = None
orbit_provenance: list[OrbitCoverageDiagnostic] = Field(default_factory=list)
dem_diagnostics: DemDiagnostics | None = None
cache_provenance: list[CacheProvenance] = Field(default_factory=list)
```

### Pure Helper Style

`selfconsistency.py` keeps imports light at module import and performs geospatial imports inside functions. `disp_diagnostics.py` should do the same:

```python
def summarize_dem(dem_path: Path, stable_mask: np.ndarray | None = None) -> DemDiagnostics:
    import rasterio
```

### Eval Script Stage Style

Both DISP eval scripts already have stage banners and construct Pydantic sidecars near the end. Phase 10 should extend those existing Stage 11 and Stage 12 blocks rather than adding a separate report file.

### Matrix Writer Style

`_render_disp_cell()` currently reads `DISPCellMetrics`, then renders coherence, residual, attribution, and reference-agreement values. Add only compact annotations, for example `era5=on`, `narrowed=tropospheric`, or `prov=ok`, and keep detailed evidence in conclusions.

## Planning Constraints

- Do not add `inconclusive_narrowed` to `AttributedSource`.
- Do not change native 5 x 10 m production output.
- Do not change Phase 11 candidate ordering unless the sidecar-backed two-signal rule supports it.
- Do not make CDS API access failures look like successful local code execution.
- Do not create a separate provenance report unless execution discovers a concrete need; canonical evidence is sidecars plus conclusions tables.

## PATTERN MAPPING COMPLETE
