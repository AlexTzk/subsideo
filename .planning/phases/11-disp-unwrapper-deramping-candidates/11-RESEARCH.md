# Phase 11: DISP Unwrapper & Deramping Candidates - Research

**Researched:** 2026-05-04
**Domain:** DISP-S1 InSAR candidate validation, dolphin unwrapping, PHASS deramping, sidecar-driven matrix reporting
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
## Implementation Decisions

### Candidate Execution Posture
- **D-01:** Phase 11 must run both SPURT native and PHASS post-deramping in the same phase so Phase 12 gets a direct unwrapper-vs-deramp comparison.
- **D-02:** Both candidates must run on both validation cells: SoCal against OPERA DISP-S1 and Bologna against EGMS L2a.
- **D-03:** Do not early-stop after SPURT success. The core Phase 11 result set is four candidate-cell outcomes: SPURT/SoCal, SPURT/Bologna, PHASS deramping/SoCal, and PHASS deramping/Bologna.
- **D-04:** Execute SPURT first, then PHASS deramping. This honors Phase 10 evidence that ERA5 did not improve the failures and the v1.1/Phase 10 ordering that points first to an unwrapper-class test.

### Deramping Semantics
- **D-05:** PHASS post-deramping must subtract fitted planar ramps from per-IFG unwrapped phases before MintPy/time-series inversion. Do not treat final-velocity-raster deramping as the main candidate.
- **D-06:** PHASS deramping is a validation candidate only in Phase 11. It may produce candidate outputs and sidecars for comparison, but must not change the native production default.
- **D-07:** PHASS deramping must include a lightweight deformation-signal sanity check, especially for SoCal, so a metric gain is not accepted as production-safe if it looks like real long-wavelength deformation was erased.
- **D-08:** A flagged deformation-signal sanity check blocks a Phase 12 production recommendation for PHASS deramping, but does not block Phase 11 from reporting candidate metrics.

### Candidate Evidence and Blockers
- **D-09:** Every candidate-cell outcome must be one of `PASS`, `FAIL`, or `BLOCKER` with structured sidecar evidence. Numeric metrics and conclusions prose are not sufficient by themselves.
- **D-10:** A `BLOCKER` must include at minimum candidate name, cell, failed stage, exception/error summary, evidence or log artifact paths, and cached-input validity.
- **D-11:** If a candidate blocks after producing some outputs, preserve schema-valid partial metrics and mark them clearly as partial so they are useful for replanning without being mistaken for comparable PASS/FAIL evidence.
- **D-12:** Candidate results should surface in canonical sidecars, explanatory conclusion sections, and compact matrix status or hint text. Matrix rendering must remain compact and must not collapse product-quality, reference-agreement, and ramp-attribution evidence into one verdict.

### ERA5 Carry-Forward
- **D-13:** Phase 10 ERA5-on diagnostics did not promote ERA5 into a required Phase 11 baseline. SoCal worsened (`r=0.0071`, `bias=+55.43 mm/yr`, `RMSE=70.04 mm/yr`), Bologna was effectively unchanged (`r=0.3358`, `bias=+3.46 mm/yr`, `RMSE=5.24 mm/yr`), and both cells remained `inconclusive` for ramp attribution.
- **D-14:** Phase 11 should therefore follow the Phase 10/v1.1 global order: SPURT native first, PHASS deramping second, with tophu/SNAPHU and 20 x 20 m fallback left as later ladder steps unless planning discovers they are necessary to satisfy the stated Phase 11 success criteria.

### the agent's Discretion
- Exact schema field names for candidate status, blockers, partial metrics, and matrix hint text, provided the sidecars remain schema-valid and preserve the decisions above.
- Exact implementation split between eval scripts, helper modules, `matrix_schema.py`, `matrix_writer.py`, conclusion files, and tests.
- Exact lightweight deformation-signal sanity check method, provided it is explicit enough for Phase 12 to decide whether PHASS deramping is production-safe.

### Deferred Ideas (OUT OF SCOPE)
## Deferred Ideas

None - discussion stayed within Phase 11 scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DISP-07 | Apply PHASS post-deramping to cached DISP stacks without changing native 5 x 10 m production output, then compare product-quality and reference-agreement metrics against the unchanged v1.1 reference pipeline. | Use validation-only candidate outputs under separate directories; subtract per-IFG fitted planes before the time-series stage; preserve `prepare_for_reference(method="block_mean")` for OPERA/EGMS comparisons. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: src/subsideo/products/disp.py] [VERIFIED: docs/validation_methodology.md] |
| DISP-08 | Run at least one alternative unwrapper/resolution candidate from SPURT native, tophu/SNAPHU tiled, or 20 x 20 m fallback, with failures captured as structured metrics. | SPURT is required by CONTEXT and is supported by installed `dolphin.UnwrapMethod`; tophu/SNAPHU is available as an optional fallback but should stay later unless SPURT blocks. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md] [VERIFIED: local import introspection] |
| DISP-09 | Compare candidate outputs on both N.Am. OPERA and EU EGMS references using explicit `prepare_for_reference(method=...)`, with product-quality, reference-agreement, and ramp-attribution reported separately. | Existing SoCal/Bologna eval scripts already route through `prepare_for_reference(method="block_mean")`, write `DISPCellMetrics`, and matrix-render product-quality/reference-agreement/ramp evidence as separate streams. [VERIFIED: run_eval_disp.py] [VERIFIED: run_eval_disp_egms.py] [VERIFIED: src/subsideo/validation/matrix_writer.py] |
</phase_requirements>

## Summary

Phase 11 should be planned as an additive validation-candidate layer on top of the existing DISP eval scripts, not as a production pipeline rewrite. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md] The native production path currently hard-codes PHASS unwrapping through dolphin in `src/subsideo/products/disp.py`, and the validation methodology explicitly keeps native 5 x 10 m output separate from comparison-adapter products. [VERIFIED: src/subsideo/products/disp.py] [VERIFIED: docs/validation_methodology.md]

The four mandatory outcomes are SPURT/SoCal, SPURT/Bologna, PHASS-deramp/SoCal, and PHASS-deramp/Bologna. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md] Phase 10 already showed ERA5 did not meet the two-signal promotion rule, so Phase 11 should not multiply every candidate into ERA5-on/off variants. [VERIFIED: .planning/phases/10-disp-era5-ramp-diagnostics/10-04-SUMMARY.md] [VERIFIED: docs/validation_methodology.md]

**Primary recommendation:** implement a candidate-run abstraction that writes schema-valid candidate evidence into the existing `DISPCellMetrics` sidecars, runs SPURT first by setting `UnwrapOptions.unwrap_method=UnwrapMethod.SPURT`, then runs PHASS post-deramping by subtracting per-IFG fitted planes before time-series inversion while preserving the unchanged reference comparison discipline. [VERIFIED: local import introspection] [VERIFIED: src/subsideo/validation/selfconsistency.py] [VERIFIED: docs/validation_methodology.md]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Candidate orchestration | Validation eval scripts | Product pipeline helper | The SoCal/Bologna scripts own cached stack selection, reference comparison, sidecar writing, and cell-specific provenance. [VERIFIED: run_eval_disp.py] [VERIFIED: run_eval_disp_egms.py] |
| SPURT native unwrapping | Product pipeline helper | Validation eval scripts | The dolphin workflow owns `UnwrapOptions`; eval scripts should pass candidate configuration without changing the production default. [VERIFIED: src/subsideo/products/disp.py] [VERIFIED: local import introspection] |
| PHASS post-deramping | Product pipeline helper | Validation helper module | Plane fitting is already a validation primitive, but deramping must happen on unwrapped IFGs before time-series inversion, not only in final metrics. [VERIFIED: src/subsideo/validation/selfconsistency.py] [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md] |
| OPERA/EGMS comparison | Validation adapter | Eval scripts | `prepare_for_reference(method=...)` is the explicit validation adapter and must remain the comparison gateway for both reference products. [VERIFIED: docs/validation_methodology.md] [VERIFIED: run_eval_disp.py] [VERIFIED: run_eval_disp_egms.py] |
| Candidate status/blockers | Sidecar schema | Matrix writer and conclusions | Existing matrix output is sidecar-driven, and Phase 11 requires structured PASS/FAIL/BLOCKER outcomes rather than terminal-only logs. [VERIFIED: src/subsideo/validation/matrix_schema.py] [VERIFIED: src/subsideo/validation/matrix_writer.py] [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md] |

## Project Constraints (from AGENTS.md)

- Use Context7 MCP or its CLI fallback for current documentation when researching libraries/frameworks/SDKs/APIs/CLI/cloud services. [VERIFIED: prompt-supplied AGENTS.md]
- Start documentation lookup by resolving a library ID before fetching docs, unless an exact `/org/project` ID is provided. [VERIFIED: prompt-supplied AGENTS.md]
- Context7 did not contain the relevant InSAR `dolphin` package; the returned matches were unrelated Dolphin language/scheduler/database/document/parser/emulator projects. [VERIFIED: Context7 CLI lookup]
- Local package introspection and official ReadTheDocs/GitHub sources were used for `dolphin`/`tophu` claims when Context7 did not provide the relevant library. [VERIFIED: local import introspection] [CITED: https://dolphin-insar.readthedocs.io/en/latest/reference/dolphin/unwrap/] [CITED: https://github.com/isce-framework/tophu]

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12.13 in lockfile | Eval scripts, Pydantic sidecars, geospatial processing | The project conda environment pins Python 3.12, and local env imports run under `micromamba run -n subsideo`. [VERIFIED: env.lockfile.osx-arm64.txt] [VERIFIED: local import introspection] |
| dolphin | 0.42.5 | DISP phase linking, unwrapping, time-series outputs | Installed dolphin exposes `UnwrapMethod` values including `PHASS` and `SPURT`, matching Phase 11 candidate needs. [VERIFIED: conda-env.yml] [VERIFIED: local import introspection] |
| numpy | 2.3.5 via local env | Plane fitting/array manipulation for deramping | Existing `fit_planar_ramp` and eval scripts use NumPy arrays for IFG stacks and metrics. [VERIFIED: local import introspection] [VERIFIED: src/subsideo/validation/selfconsistency.py] |
| rasterio | 1.5.0 | Read/write GeoTIFF unwrapped IFGs, velocity rasters, and comparison grids | Existing DISP eval and product code use rasterio for unwrapped phase, coherence, velocity, and reprojection work. [VERIFIED: local import introspection] [VERIFIED: run_eval_disp.py] |
| Pydantic | 2.13.3 | Strict sidecar schemas | `matrix_schema.py` uses Pydantic v2 models with `ConfigDict(extra="forbid")` across metrics sidecars. [VERIFIED: local import introspection] [VERIFIED: src/subsideo/validation/matrix_schema.py] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tophu | 0.2.0 in local env; 0.2.1 in Linux conda comment | Multi-scale tiled SNAPHU fallback | Keep as later ladder step if SPURT blocks/fails and PHASS deramping does not produce useful evidence. [VERIFIED: local import introspection] [VERIFIED: conda-env.yml] [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md] |
| snaphu | 0.4.1 | SNAPHU unwrapping backend/fallback | Use only for tophu/SNAPHU fallback or targeted tests; do not replace SPURT as the required first alternative. [VERIFIED: local import introspection] [VERIFIED: conda-env.yml] |
| MintPy | 1.6.2 local import; 1.6.3 conda-env target | Historical time-series template support | Do not plan new MintPy SBAS candidate; use only existing pipeline support where already wired. [VERIFIED: local import introspection] [VERIFIED: conda-env.yml] [VERIFIED: .planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md] |
| pyaps3 | 0.3.7 | ERA5 diagnostic support | Do not promote ERA5 to required candidate baseline in Phase 11 because Phase 10 did not meet the two-signal rule. [VERIFIED: local import introspection] [VERIFIED: .planning/phases/10-disp-era5-ramp-diagnostics/10-04-SUMMARY.md] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SPURT native first | tophu/SNAPHU tiled first | tophu/SNAPHU is heavier and explicitly later in Phase 11 unless SPURT cannot satisfy DISP-08. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md] |
| PHASS post-deramping before inversion | Final velocity-raster deramping | Final-raster deramping is rejected by the locked deramping semantics because it cannot test whether pre-inversion ramp removal changes the time-series solution. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md] |
| Candidate sidecar extension | Separate ad hoc report | The project matrix consumes sidecars and must not parse conclusions markdown, so candidate status belongs in schema-valid sidecars. [VERIFIED: src/subsideo/validation/matrix_schema.py] [VERIFIED: src/subsideo/validation/matrix_writer.py] |

**Installation:**
```bash
micromamba create -f conda-env.yml
micromamba run -n subsideo python -c "from dolphin.workflows.config._unwrap_options import UnwrapMethod; print([m.value for m in UnwrapMethod])"
```

**Version verification:** `micromamba run -n subsideo python` verified `dolphin=0.42.5`, `tophu=0.2.0`, `snaphu=0.4.1`, `mintpy=1.6.2`, `pyaps3=0.3.7`, `rasterio=1.5.0`, `pydantic=2.13.3`, and `pytest=9.0.3`. [VERIFIED: local import introspection]

## Architecture Patterns

### System Architecture Diagram

```text
Cached CSLC stacks
  |-- SoCal eval-disp/cslc [VERIFIED: run_eval_disp.py]
  |-- Bologna eval-disp-egms/cslc [VERIFIED: run_eval_disp_egms.py]
  v
Candidate runner
  |-- candidate=spurt -> dolphin DisplacementWorkflow -> UnwrapMethod.SPURT
  |-- candidate=phass_deramp -> existing PHASS unwrapped IFGs -> fit planar ramp -> subtract plane -> time-series solution
  v
Candidate output directory (separate from native default)
  v
Product-quality metrics + reference-agreement metrics + ramp-attribution metrics
  |-- OPERA/EGMS comparison via prepare_for_reference(method="block_mean")
  |-- blocker/partial evidence if a stage fails
  v
DISPCellMetrics extension + meta.json provenance
  v
results/matrix.md compact hints + CONCLUSIONS_DISP_{N_AM,EU}.md candidate sections
  v
Phase 12 production-posture decision
```

### Recommended Project Structure

```text
src/subsideo/products/
├── disp.py                       # Add candidate config parameters without changing default PHASS behavior. [VERIFIED: src/subsideo/products/disp.py]
src/subsideo/validation/
├── disp_candidates.py            # New candidate status/blocker helpers and shared eval orchestration. [ASSUMED]
├── selfconsistency.py            # Reuse/extend ramp fit helpers for deramped IFG generation. [VERIFIED: src/subsideo/validation/selfconsistency.py]
├── matrix_schema.py              # Add additive candidate evidence models. [VERIFIED: src/subsideo/validation/matrix_schema.py]
├── matrix_writer.py              # Render compact candidate hints from sidecars. [VERIFIED: src/subsideo/validation/matrix_writer.py]
run_eval_disp.py                  # SoCal candidate runs and OPERA comparison. [VERIFIED: run_eval_disp.py]
run_eval_disp_egms.py             # Bologna candidate runs and EGMS comparison. [VERIFIED: run_eval_disp_egms.py]
tests/reference_agreement/
└── test_matrix_writer_disp.py    # Extend DISP matrix rendering tests. [VERIFIED: tests/reference_agreement/test_matrix_writer_disp.py]
tests/product_quality/
└── test_selfconsistency_ramp.py  # Extend ramp/deramp tests. [VERIFIED: tests/product_quality/test_selfconsistency_ramp.py]
```

### Pattern 1: Candidate Status Is Additive Sidecar Evidence

**What:** Add a nested candidate evidence block to `DISPCellMetrics` rather than replacing product-quality/reference-agreement/ramp fields. [VERIFIED: src/subsideo/validation/matrix_schema.py]

**When to use:** Every SPURT or PHASS-deramp candidate-cell run should emit `PASS`, `FAIL`, or `BLOCKER`; partial outputs should be schema-valid and marked partial. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md]

**Example:**
```python
# Source: existing Pydantic v2 sidecar pattern in matrix_schema.py [VERIFIED: src/subsideo/validation/matrix_schema.py]
class DISPCandidateOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate: Literal["spurt_native", "phass_post_deramp"]
    cell: Literal["socal", "bologna"]
    status: Literal["PASS", "FAIL", "BLOCKER"]
    failed_stage: str | None = None
    error_summary: str | None = None
    evidence_paths: list[str] = Field(default_factory=list)
    cached_input_valid: bool
    partial_metrics: bool = False
```

### Pattern 2: SPURT Is a Dolphin UnwrapOption Switch

**What:** The installed dolphin package exposes `UnwrapMethod.SPURT`, and `UnwrapOptions` accepts `unwrap_method` plus `spurt_options`. [VERIFIED: local import introspection]

**When to use:** Plan a SPURT candidate run by passing candidate config into the product helper or an eval-only wrapper, while keeping the default production invocation PHASS. [VERIFIED: src/subsideo/products/disp.py] [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md]

**Example:**
```python
# Source: local introspection of dolphin.workflows.config._unwrap_options [VERIFIED: local import introspection]
from dolphin.workflows.config import UnwrapOptions
from dolphin.workflows.config._unwrap_options import UnwrapMethod

unwrap_options = UnwrapOptions(
    run_unwrap=True,
    unwrap_method=UnwrapMethod.SPURT,
    n_parallel_jobs=n_parallel_unwrap,
)
```

### Pattern 3: Deramp IFGs Before Time-Series Inversion

**What:** Fit a planar ramp per unwrapped IFG, subtract the fitted plane, and then feed deramped IFGs into the downstream time-series stage. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md] [VERIFIED: src/subsideo/validation/selfconsistency.py]

**When to use:** PHASS post-deramping candidate only; do not use it as a production default or final velocity cosmetic correction. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md]

**Example:**
```python
# Source: fit_planar_ramp coefficients returned by selfconsistency.py [VERIFIED: src/subsideo/validation/selfconsistency.py]
ramp_data = fit_planar_ramp(ifgrams_unw_stack, mask=None)
for idx, phase in enumerate(ifgrams_unw_stack):
    yy, xx = np.indices(phase.shape, dtype=np.float64)
    plane = (
        ramp_data["slope_x"][idx] * xx
        + ramp_data["slope_y"][idx] * yy
        + ramp_data["intercept_rad"][idx]
    )
    deramped = np.where(np.isfinite(phase), phase - plane, np.nan)
```

### Anti-Patterns to Avoid

- **Changing production default to SPURT or deramped PHASS in Phase 11:** Phase 11 is evidence gathering; Phase 12 chooses production posture. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md]
- **Writing candidate failures only to terminal logs:** Phase 11 requires structured blocker evidence in sidecars. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md]
- **Collapsing candidate outcome into one verdict:** Product-quality, reference-agreement, and ramp-attribution remain separate evidence streams. [VERIFIED: docs/validation_methodology.md]
- **Using implicit comparison defaults:** `prepare_for_reference(method=...)` must stay explicit for both OPERA and EGMS comparisons. [VERIFIED: docs/validation_methodology.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Native SPURT unwrapping | Custom graph unwrapping | dolphin `UnwrapMethod.SPURT` | Installed dolphin already exposes SPURT and candidate-specific options. [VERIFIED: local import introspection] |
| Planar ramp fitting | Ad hoc per-script least-squares copies | `fit_planar_ramp` and `compute_ramp_aggregate` | Existing helpers are tested and already feed DISP ramp-attribution sidecars. [VERIFIED: src/subsideo/validation/selfconsistency.py] [VERIFIED: tests/product_quality/test_selfconsistency_ramp.py] |
| Matrix rendering from conclusions | Markdown parsing | `metrics.json` sidecars through `matrix_writer.py` | Existing project contract says matrix rendering is sidecar-driven. [VERIFIED: src/subsideo/validation/matrix_writer.py] |
| Reference grid adaptation | Silent raster resampling defaults | `prepare_for_reference(method="block_mean")` | Explicit method selection is the validation discipline and keeps comparison choices auditable. [VERIFIED: docs/validation_methodology.md] |
| Blocker reporting | Free-form log scraping | Pydantic blocker/candidate models | Existing schemas use `extra="forbid"` and structured blocker patterns. [VERIFIED: src/subsideo/validation/matrix_schema.py] |

**Key insight:** the hard part is not invoking SPURT or fitting planes; the hard part is preserving candidate evidence provenance so Phase 12 can decide production posture without rerunning or reinterpreting logs. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md]

## Common Pitfalls

### Pitfall 1: Candidate Outputs Overwrite Baseline Outputs
**What goes wrong:** SPURT or PHASS-deramp outputs replace `eval-disp/metrics.json` or `eval-disp-egms/metrics.json` without preserving the unchanged reference pipeline. [ASSUMED]
**Why it happens:** Existing eval scripts have fixed output directories and write one `metrics.json` per cell. [VERIFIED: run_eval_disp.py] [VERIFIED: run_eval_disp_egms.py]
**How to avoid:** Use candidate-specific subdirectories or nested sidecar fields while preserving canonical baseline semantics. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md]
**Warning signs:** Matrix cells lose ERA5/baseline fields or conclusions can no longer quote unchanged v1.1/Phase 10 numbers. [VERIFIED: .planning/phases/10-disp-era5-ramp-diagnostics/10-04-SUMMARY.md]

### Pitfall 2: Deramping After Velocity Generation
**What goes wrong:** A final velocity raster is deramped, producing a cosmetic reference-agreement change that does not test the candidate required by DISP-07. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md]
**Why it happens:** Existing ramp-attribution code fits per-IFG planes for diagnostics, but does not currently create deramped IFGs for a new time-series solution. [VERIFIED: run_eval_disp.py] [VERIFIED: run_eval_disp_egms.py]
**How to avoid:** Plan a helper that writes deramped unwrapped IFGs before the downstream time-series stage and records ramp coefficients. [VERIFIED: src/subsideo/validation/selfconsistency.py]
**Warning signs:** Candidate code only touches `velocity.tif` or only updates `RampAttribution` without regenerating a candidate time-series output. [ASSUMED]

### Pitfall 3: Treating SoCal Metric Gain As Safe Without Signal Preservation Check
**What goes wrong:** Long-wavelength deformation may be removed alongside artifact and still improve agreement metrics. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md]
**Why it happens:** Plane removal is intentionally blind to whether the plane is artifact or geophysical signal. [ASSUMED]
**How to avoid:** Record a lightweight deformation-signal sanity check in the PHASS-deramp candidate evidence and block production recommendation if it flags. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md]
**Warning signs:** PHASS-deramp candidate status is `PASS` with no deformation-signal field or no SoCal-specific note. [ASSUMED]

### Pitfall 4: Reintroducing ERA5 Candidate Multiplication
**What goes wrong:** Planning doubles each candidate into ERA5-on/off variants, expanding scope and compute without a locked decision. [ASSUMED]
**Why it happens:** Phase 10 had ERA5 machinery and sidecars, but the live results did not promote ERA5. [VERIFIED: .planning/phases/10-disp-era5-ramp-diagnostics/10-04-SUMMARY.md]
**How to avoid:** Keep ERA5 diagnostic fields as context, not candidate axes. [VERIFIED: docs/validation_methodology.md]
**Warning signs:** Plan tasks list SPURT-ERA5 and PHASS-deramp-ERA5 as required Phase 11 outputs. [ASSUMED]

## Code Examples

### Local Verification of SPURT Support

```python
# Source: verified in local subsideo env [VERIFIED: local import introspection]
from dolphin.workflows.config._unwrap_options import UnwrapMethod

assert "SPURT" in [method.name for method in UnwrapMethod]
assert "spurt" in [method.value for method in UnwrapMethod]
```

### Candidate Blocker Capture

```python
# Source: follows existing structured blocker and error fields in matrix_schema.py [VERIFIED: src/subsideo/validation/matrix_schema.py]
try:
    result = run_candidate(cell=cell, candidate=candidate)
except Exception as exc:
    outcome = DISPCandidateOutcome(
        candidate=candidate,
        cell=cell,
        status="BLOCKER",
        failed_stage=current_stage,
        error_summary=f"{type(exc).__name__}: {exc}",
        evidence_paths=[str(log_path)],
        cached_input_valid=cached_input_valid,
        partial_metrics=partial_metrics_available,
    )
```

### Preserve Explicit Reference Method

```python
# Source: validation methodology and existing eval scripts [VERIFIED: docs/validation_methodology.md] [VERIFIED: run_eval_disp.py]
candidate_at_reference = prepare_for_reference(
    candidate_velocity,
    reference_grid_or_points,
    method=REFERENCE_MULTILOOK_METHOD,  # "block_mean"
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PHASS-only native DISP validation with honest FAIL | Run SPURT and PHASS-deramp validation candidates on both cells | Phase 11 scope, 2026-05-04 | Produces direct unwrapper-vs-deramp evidence for Phase 12. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md] |
| ERA5 as possible next baseline | ERA5 remains diagnostic only | Phase 10 completed 2026-05-04 | Phase 11 should not require ERA5-on for candidates. [VERIFIED: .planning/phases/10-disp-era5-ramp-diagnostics/10-04-SUMMARY.md] |
| Matrix showing only ramp attribution hint | Matrix should add compact candidate hints | Phase 11 scope, 2026-05-04 | Candidate status becomes visible without collapsing evidence streams. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md] |

**Deprecated/outdated:**
- Treating MintPy SBAS as a fifth candidate is out of scope for this candidate ladder. [VERIFIED: .planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md]
- Treating 20 x 20 m as a production default in Phase 11 is out of scope. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A new `src/subsideo/validation/disp_candidates.py` helper is the cleanest implementation location. | Recommended Project Structure | Planner may instead keep helpers inside eval scripts or product module; low risk if schema behavior is preserved. |
| A2 | Candidate output overwrite is a plausible risk with current fixed output directories. | Common Pitfalls | Planner might over-design directory isolation, but avoiding overwrite is consistent with locked baseline preservation. |
| A3 | Plane removal can erase geophysical long-wavelength signal. | Common Pitfalls | If too conservative, PHASS-deramp may be blocked from production recommendation even when metrics improve. |
| A4 | ERA5 candidate multiplication is a likely planning failure mode. | Common Pitfalls | If future user decision changes ERA5 posture, planner would need to revise candidate matrix. |

## Open Questions (RESOLVED)

1. **Exact time-series re-entry point for deramped IFGs**
   - What we know: Locked semantics require deramped unwrapped IFGs before time-series inversion. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md]
   - What's unclear: Existing `run_disp` currently relies on dolphin output directories and does not expose a public "rerun inversion from modified unwrapped IFGs" entry point. [VERIFIED: src/subsideo/products/disp.py]
   - Resolution: Plan 11-03 resolves this by adding an explicit validation-only `deramped_unwrapped_paths: list[Path] | None = None` product-helper hook if a supported local/public re-entry path exists, and otherwise preserving the PHASS post-deramp candidate as a schema-valid partial `BLOCKER` with `failed_stage="deramped_ifg_timeseries_reentry"`, deramped-IFG evidence paths, cached-input validity, and `partial_metrics=True`. This satisfies D-05, D-10, and D-11 without requiring private dolphin APIs or changing production defaults. [RESOLVED: 11-03-PLAN.md]

2. **PHASS deramp sanity-check metric**
   - What we know: SoCal requires a lightweight deformation-signal sanity check. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md]
   - What's unclear: No specific GPS/NGL data integration is in scope or currently available as a dependency. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md]
   - Resolution: Plan 11-01 defines `DISPDeformationSanityCheck`; Plan 11-03 records `trend_delta_mm_yr`, `direction_change_deg`, and `stable_residual_delta_mm_yr`, with `flagged=True` when `abs(trend_delta_mm_yr) > 3.0` or `abs(stable_residual_delta_mm_yr) > 2.0`. The flag blocks Phase 12 production recommendation for PHASS deramping per D-08 but does not block Phase 11 candidate measurement per D-07. [RESOLVED: 11-01-PLAN.md, 11-03-PLAN.md]

3. **tophu/SNAPHU fallback trigger**
   - What we know: Phase 11 requires SPURT and PHASS deramping; tophu/SNAPHU and 20 x 20 m are later ladder steps unless needed for success criteria. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md]
   - What's unclear: Planner may decide whether a fallback task is needed to satisfy the "at least one alternative candidate" success criterion if SPURT blocks. [VERIFIED: .planning/REQUIREMENTS.md]
   - Resolution: No tophu/SNAPHU fallback task is planned in Phase 11. DISP-08 requires running at least one alternative candidate with failures captured as structured metrics; Plan 11-02 runs SPURT native on both cells and records `BLOCKER` outcomes if SPURT fails before comparable metrics. That structured SPURT outcome satisfies the Phase 11 alternative-candidate requirement, while D-14 keeps tophu/SNAPHU and 20 x 20 m as later ladder steps for Phase 12 or a follow-on gap plan if Phase 11 evidence proves they are needed. [RESOLVED: 11-02-PLAN.md]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| micromamba | Eval/test commands | yes | 2.5.0 | None needed. [VERIFIED: command -v micromamba] |
| make | Eval orchestration | yes | GNU Make 3.81 | Direct `micromamba run -n subsideo python ...` commands. [VERIFIED: command -v make] |
| dolphin | SPURT/PHASS candidate runs | yes | 0.42.5 | None for SPURT; blocker if absent. [VERIFIED: local import introspection] |
| tophu | Later fallback | yes | 0.2.0 | Use SPURT/PHASS required candidates first. [VERIFIED: local import introspection] |
| snaphu | tophu/SNAPHU fallback | yes | 0.4.1 | Defer fallback if not needed. [VERIFIED: local import introspection] |
| pyaps3 | ERA5 diagnostics context | yes | 0.3.7 | Not required for Phase 11 candidates. [VERIFIED: local import introspection] |
| pytest | Unit/schema tests | yes | 9.0.3 | None needed. [VERIFIED: local import introspection] |

**Missing dependencies with no fallback:** None identified for the required SPURT and PHASS-deramp planning surface. [VERIFIED: local import introspection]

**Missing dependencies with fallback:** Context7 did not index the relevant InSAR dolphin package; official ReadTheDocs/GitHub and local package introspection cover the needed API evidence. [VERIFIED: Context7 CLI lookup] [CITED: https://dolphin-insar.readthedocs.io/en/latest/reference/dolphin/unwrap/] [CITED: https://github.com/isce-framework/tophu]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | No user auth/session surface in this phase. [VERIFIED: phase scope in .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md] |
| V3 Session Management | no | No browser/API sessions in this phase. [VERIFIED: phase scope in .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md] |
| V4 Access Control | no | Local eval scripts operate on workspace files, not multi-user resources. [VERIFIED: Makefile] |
| V5 Input Validation | yes | Use Pydantic `extra="forbid"` sidecar schemas and explicit enum literals for candidate status. [VERIFIED: src/subsideo/validation/matrix_schema.py] |
| V6 Cryptography | yes | Use existing SHA256 provenance hashing; do not invent custom integrity checks. [VERIFIED: run_eval_disp.py] [VERIFIED: run_eval_disp_egms.py] |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Stale or overwritten candidate artifacts | Tampering | Candidate-specific directories and SHA256/cache provenance in `meta.json`/metrics evidence. [VERIFIED: run_eval_disp.py] [VERIFIED: src/subsideo/validation/matrix_schema.py] |
| Malformed sidecars poisoning matrix output | Tampering | Pydantic validation plus matrix fall-through to `RUN_FAILED` on parse errors. [VERIFIED: src/subsideo/validation/matrix_writer.py] |
| Silent reference-method drift | Repudiation | Keep module-level `REFERENCE_MULTILOOK_METHOD` and explicit `prepare_for_reference(method=...)`. [VERIFIED: docs/validation_methodology.md] |
| Terminal-only failures lost after rerun | Repudiation | Structured `BLOCKER` evidence with stage, error, paths, and cached-input validity. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md] |

## Sources

### Primary (HIGH confidence)

- `.planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md` - locked decisions, candidate matrix, blockers, ERA5 carry-forward. [VERIFIED: file read]
- `.planning/REQUIREMENTS.md` - DISP-07, DISP-08, DISP-09 requirements and out-of-scope production-resolution boundary. [VERIFIED: file read]
- `.planning/phases/10-disp-era5-ramp-diagnostics/10-04-SUMMARY.md` - live Phase 10 ERA5 results and Phase 11 ordering. [VERIFIED: file read]
- `docs/validation_methodology.md` - explicit `prepare_for_reference(method=...)`, block_mean discipline, evidence-stream separation, ERA5 carry-forward. [VERIFIED: file read]
- `src/subsideo/products/disp.py` - current PHASS dolphin wiring and native pipeline output behavior. [VERIFIED: code grep/read]
- `src/subsideo/validation/selfconsistency.py` - ramp fitting and aggregate helper patterns. [VERIFIED: code grep/read]
- `src/subsideo/validation/matrix_schema.py` - Pydantic sidecar schema patterns and existing DISP metrics. [VERIFIED: code grep/read]
- `src/subsideo/validation/matrix_writer.py` - sidecar-driven DISP matrix rendering. [VERIFIED: code grep/read]
- Local import introspection in `micromamba run -n subsideo python` - installed versions and dolphin `UnwrapMethod`/option fields. [VERIFIED: command output]

### Secondary (MEDIUM confidence)

- https://dolphin-insar.readthedocs.io/en/latest/reference/dolphin/unwrap/ - official dolphin unwrap reference located by web search after Context7 mismatch. [CITED: official docs]
- https://github.com/isce-framework/tophu - official tophu GitHub source for fallback package identity. [CITED: official repository]

### Tertiary (LOW confidence)

- None used as authority; all planning-critical claims are from project files, code, local environment, or official package sources. [VERIFIED: source audit]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified by local imports, lockfile/env files, and code usage. [VERIFIED: local import introspection] [VERIFIED: conda-env.yml]
- Architecture: HIGH - current eval scripts, product helper, schemas, and matrix writer expose clear integration points. [VERIFIED: code grep/read]
- Pitfalls: MEDIUM - major pitfalls are locked by context and methodology, while some implementation failure modes are inferred from fixed output-directory patterns. [VERIFIED: .planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md] [ASSUMED]

**Research date:** 2026-05-04
**Valid until:** 2026-06-03 for project-code decisions; re-check package docs/versions before implementation if the environment changes. [ASSUMED]
