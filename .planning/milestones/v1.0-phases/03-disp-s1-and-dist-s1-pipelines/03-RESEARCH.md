# Phase 3: DISP-S1 and DIST-S1 Pipelines - Research

**Researched:** 2026-04-05
**Domain:** InSAR displacement time-series (dolphin + tophu + MintPy), surface disturbance (dist-s1), EGMS validation
**Confidence:** MEDIUM-HIGH

## Summary

Phase 3 implements two product pipelines and one validation module. The DISP-S1 pipeline chains dolphin (PS/DS phase linking) -> tophu (multi-scale unwrapping) -> MintPy (time-series inversion with ERA5 tropospheric correction). The DIST-S1 pipeline wraps opera-adt/dist-s1 over an RTC time series. EGMS validation compares vertical velocity against EGMS Ortho products via EGMStoolkit.

All three upstream libraries (dolphin, tophu, dist-s1) expose Python APIs that can be called programmatically. dolphin uses a `DisplacementWorkflow` Pydantic config class with a `run()` function. tophu provides `multiscale_unwrap()`. MintPy provides a `TimeSeriesAnalysis` class with step-wise `run()`. dist-s1 exposes `run_dist_s1_workflow()`. The established thin-wrapper pattern from Phase 2 (generate config -> call library API -> validate output -> return structured result) applies cleanly to all four.

**Primary recommendation:** Build `products/disp.py` and `products/dist.py` as thin wrappers following the rtc.py/cslc.py pattern. DISP orchestrates three stages (dolphin, tophu, MintPy) with a post-unwrapping planar-ramp sanity check between tophu and MintPy. DIST wraps dist-s1's single entry point. EGMS validation in `validation/compare_disp.py` follows the compare_rtc.py pattern with LOS-to-vertical projection added.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Single orchestrator in `products/disp.py` with `run_disp()`. Chains: CSLC stack -> dolphin phase linking -> tophu multi-scale unwrapping -> MintPy time-series inversion. Matches the thin-wrapper pattern from Phase 2 (rtc.py, cslc.py).
- **D-02:** End-to-end AOI + date range interface. User provides AOI geometry + date range -> pipeline runs CSLC (via Phase 2 `run_cslc()`) to build the stack -> feeds CSLC HDF5 stack into dolphin -> tophu -> MintPy. Full automation, no manual intermediate steps.
- **D-03:** ERA5 tropospheric correction via MintPy/PyAPS3 is **mandatory**. Pipeline must fail if `~/.cdsapirc` is missing or CDS API key is invalid. Validate CDS credentials at pipeline start (before any processing) using the existing `check_env()` pattern from Phase 1.
- **D-04:** dolphin, tophu, and MintPy are called via their Python APIs (not subprocess). Lazy imports for all three (conda-forge-only deps). Generate YAML runconfigs programmatically from subsideo's Pydantic config, matching the Phase 1/2 pattern.
- **D-05:** Automated post-unwrapping sanity check with flag-and-continue behavior. Fit a plane to the unwrapped phase; if residual exceeds a configurable threshold, FLAG the result in HDF5 metadata (warning field) but do not fail the pipeline. Log the anomaly via loguru.
- **D-06:** Coherence masking applied before unwrapping with configurable threshold (default 0.3). Pixels below the coherence threshold are masked out before feeding to tophu/snaphu. Threshold exposed in config as `coherence_mask_threshold`.
- **D-07:** Use EGMS Ortho product level as validation reference.
- **D-08:** Compare vertical component only. Project subsideo LOS velocity to vertical using incidence angle, then compare against EGMS Ortho vertical field.
- **D-09:** Use EGMStoolkit 0.2.15 for EGMS product download.
- **D-10:** Validation module in `validation/compare_disp.py` accepts subsideo DISP output path + EGMS Ortho path, aligns grids via rasterio reproject, computes spatial correlation (r > 0.92) and absolute velocity bias (< 3 mm/yr). Reuse `validation/metrics.py` from Phase 2.
- **D-11:** Implement `products/dist.py` with full wrapper now, using conditional lazy import for dist-s1. If dist-s1 is not installed, raise a clear `ImportError` with conda-forge install instructions. Unit tests mock dist-s1.
- **D-12:** End-to-end AOI + date range interface for DIST, matching DISP pattern.
- **D-13:** DIST output as COG GeoTIFF with OPERA-compliant metadata. Validation is structural compliance only (OPERA product validator) -- no EU-specific reference dataset exists for DIST.

### Claude's Discretion
- Internal helper functions for dolphin/tophu/MintPy config generation
- DISPConfig/DISPResult and DISTConfig/DISTResult dataclass design (extend products/types.py)
- Test fixture design for mocked dolphin/tophu/MintPy/dist-s1 outputs
- Whether to cache intermediate CSLC/RTC stacks when running end-to-end
- Error message formatting for multi-stage pipeline failures

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROD-03 | Library can produce DISP-S1 displacement time-series products using dolphin + tophu + MintPy | dolphin `DisplacementWorkflow` + `run()`, tophu `multiscale_unwrap`, MintPy `TimeSeriesAnalysis` -- all have Python APIs for programmatic invocation |
| PROD-05 | Library can produce DIST-S1 surface disturbance products from RTC time series | dist-s1 `run_dist_s1_workflow()` accepts MGRS tile + date + track, wrappable via thin-wrapper pattern |
| VAL-04 | Library can compare DISP-S1 output against EGMS EU displacement products (r > 0.92, bias < 3 mm/yr) | EGMStoolkit for EGMS Ortho download; LOS-to-vertical projection via `d_vert = d_los / cos(theta)`; existing `metrics.py` provides `spatial_correlation()` and `bias()` |
</phase_requirements>

## Standard Stack

### Core (conda-forge only -- never pip install)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| dolphin | 0.42.5 | PS/DS phase linking for DISP-S1 | OPERA-ADT reference implementation; `DisplacementWorkflow` + `run()` Python API |
| tophu | 0.2.1 | Multi-scale tile-based 2-D phase unwrapping | isce-framework reference; parallelises SNAPHU over tiles; called by dolphin internally but also usable standalone |
| snaphu-py | 0.4.1 | SNAPHU unwrapping binary wrapper | Backend for tophu; non-commercial research license |
| MintPy | 1.6.3 | Time-series inversion, velocity estimation, ERA5 correction | insarlab/JPL reference; `TimeSeriesAnalysis` class with step-wise Python API |
| pyaps3 | >=0.3.6 | ERA5 tropospheric delay via CDS API | Required by MintPy; **must be >=0.3.6** for new CDS API token format (0.3.5 silently fails) |
| dist-s1 | conda-forge | Surface disturbance delineation from RTC-S1 time series | OPERA-ADT official DIST-S1 workflow; `run_dist_s1_workflow()` entry point |

### Supporting (pip-installable, already in project)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| EGMStoolkit | 0.2.15 | EGMS product download (Ortho level) | DISP validation -- download reference vertical velocity GeoTIFFs |
| rasterio | >=1.3 | Grid alignment for EGMS validation (reproject) | Already used in compare_rtc.py |
| scipy | >=1.12 | Plane fitting for unwrap QC (`scipy.linalg.lstsq`) | Post-unwrapping planar ramp detection |
| cdsapi | >=0.7 | ECMWF CDS API client for ERA5 | Required by pyaps3; credentials in `~/.cdsapirc` |

### Not Adding New Pip Dependencies

All libraries needed are either already in `pyproject.toml` (rasterio, scipy, h5py, numpy) or are conda-forge-only (dolphin, tophu, MintPy, dist-s1). EGMStoolkit should be added to the `[validation]` optional group.

## Architecture Patterns

### Recommended Project Structure

```
src/subsideo/
  products/
    disp.py          # NEW: run_disp() orchestrator
    dist.py          # NEW: run_dist() orchestrator
    types.py         # EXTEND: DISPConfig, DISPResult, DISTConfig, DISTResult, DISPValidationResult
  validation/
    compare_disp.py  # NEW: EGMS comparison
tests/unit/
    test_disp_pipeline.py  # NEW
    test_dist_pipeline.py  # NEW
    test_compare_disp.py   # NEW
```

### Pattern 1: Thin Wrapper Orchestrator (replicate from cslc.py/rtc.py)

**What:** Each product module follows: build config dataclass -> generate library-specific config -> lazy-import library -> call library API -> validate output -> return result dataclass.

**DISP specifics -- three-stage chain:**

```python
# products/disp.py (simplified structure)
from subsideo.products.types import DISPConfig, DISPResult

def _validate_cds_credentials(cdsapirc_path: Path) -> None:
    """Fail fast if CDS API key is missing/invalid (D-03)."""
    if not cdsapirc_path.exists():
        raise FileNotFoundError(
            f"CDS API config not found at {cdsapirc_path}. "
            "ERA5 tropospheric correction is mandatory for DISP. "
            "Register at https://cds.climate.copernicus.eu/"
        )

def _run_dolphin_phase_linking(
    cslc_file_list: list[Path],
    work_dir: Path,
    coherence_threshold: float,
) -> tuple[list[Path], list[Path]]:
    """Stage 1: dolphin PS/DS phase linking -> wrapped interferograms."""
    from dolphin.workflows.config import DisplacementWorkflow
    from dolphin.workflows.displacement import run as dolphin_run

    cfg = DisplacementWorkflow(
        cslc_file_list=cslc_file_list,
        # ... configure phase_linking, output_options, etc.
    )
    outputs = dolphin_run(cfg)
    return outputs.stitched_ifg_paths, outputs.stitched_cor_paths

def _run_unwrapping(
    ifg_paths: list[Path],
    cor_paths: list[Path],
    coherence_threshold: float,
) -> list[Path]:
    """Stage 2: tophu multi-scale unwrapping with coherence mask (D-06)."""
    # Note: dolphin can run unwrapping internally via unwrap_options
    # But D-05 requires a post-unwrap QC step between unwrapping and MintPy
    ...

def _check_unwrap_quality(unwrapped_path: Path, threshold: float) -> dict:
    """Post-unwrap planar ramp QC (D-05). Returns warning dict."""
    ...

def _run_mintpy_timeseries(
    work_dir: Path,
    custom_template: Path,
) -> list[Path]:
    """Stage 3: MintPy time-series inversion with ERA5 correction."""
    from mintpy.smallbaselineApp import TimeSeriesAnalysis

    app = TimeSeriesAnalysis(
        customTemplateFile=str(custom_template),
        workDir=str(work_dir),
    )
    app.open()
    app.run(steps=['load_data', 'invert_network', 'correct_troposphere',
                   'deramp', 'correct_dem_error', 'velocity'])
    app.close()
    ...

def run_disp(
    cslc_paths: list[Path],
    output_dir: Path,
    cdsapirc_path: Path | None = None,
    coherence_mask_threshold: float = 0.3,
    ramp_threshold: float = 1.0,
) -> DISPResult:
    """Run the full DISP-S1 pipeline (D-01, D-02)."""
    ...
```

### Pattern 2: DIST-S1 Thin Wrapper

**What:** Single-stage wrapper around `dist_s1.run_dist_s1_workflow()`.

```python
# products/dist.py
def run_dist(
    mgrs_tile_id: str,
    post_date: str,
    track_number: int,
    output_dir: Path,
) -> DISTResult:
    """Run the DIST-S1 surface disturbance pipeline (D-11, D-12)."""
    try:
        from dist_s1 import run_dist_s1_workflow
    except ImportError:
        raise ImportError(
            "dist-s1 is not installed. Install via conda-forge: "
            "mamba install -c conda-forge dist-s1"
        )
    run_dist_s1_workflow(mgrs_tile_id, post_date, track_number, dst_dir=output_dir)
    # Collect outputs, validate COG structure, return DISTResult
    ...
```

### Pattern 3: EGMS Validation (replicate compare_rtc.py pattern)

**What:** Load subsideo DISP velocity, project LOS to vertical, load EGMS Ortho vertical, reproject to common grid, compute metrics.

```python
# validation/compare_disp.py
def compare_disp(
    product_path: Path,
    egms_ortho_path: Path,
    incidence_angle_path: Path | None = None,
    mean_incidence_deg: float = 33.0,
) -> DISPValidationResult:
    """Compare DISP-S1 velocity against EGMS Ortho vertical (D-07, D-08, D-10).

    LOS-to-vertical projection: v_vert = v_los / cos(theta)
    where theta is the local incidence angle.
    """
    ...
```

### Anti-Patterns to Avoid
- **Calling dolphin/tophu/MintPy via subprocess:** Decision D-04 explicitly requires Python API calls. Subprocess adds fragility and makes error handling harder.
- **Skipping ERA5 correction:** Decision D-03 makes it mandatory. Never allow an uncorrected velocity output -- it will fail VAL-04 thresholds.
- **Hardcoding incidence angle:** For accurate LOS-to-vertical projection, use the per-pixel incidence angle from the CSLC metadata if available. Fall back to a mean value (33 deg for Sentinel-1) only if per-pixel not available.
- **Assuming horizontal motion is negligible for LOS-to-vertical:** This is the standard assumption for validation, but document this limitation. Error can reach significant percentages in areas with large horizontal motion.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PS/DS phase linking | Custom phase linking | dolphin's `DisplacementWorkflow` + `run()` | Handles large-scale covariance estimation, MLE phase linking; published in JOSS 2024 |
| Phase unwrapping | Custom unwrapper | tophu `multiscale_unwrap` (or dolphin's internal unwrapping) | Multi-resolution tiling, parallel SNAPHU, handles large interferograms |
| Time-series inversion | Custom SBAS | MintPy `TimeSeriesAnalysis` | Handles network inversion, ERA5 correction, DEM error, velocity estimation |
| ERA5 tropospheric delay | Manual ERA5 download + correction | pyaps3 (via MintPy) | Handles CDS API auth, GRIB download, delay computation for each acquisition |
| EGMS data download | Manual HTTP/FTP | EGMStoolkit | Handles EGMS API auth, tile selection, product level filtering |
| Planar ramp fitting | Custom least squares | `scipy.linalg.lstsq` on coordinate grid | Standard approach; fast; handles masked pixels via NaN exclusion |
| Surface disturbance delineation | Custom disturbance detector | dist-s1 `run_dist_s1_workflow()` | OPERA-ADT official algorithm; handles all statistical thresholding and temporal baseline logic |

## Common Pitfalls

### Pitfall 1: pyaps3 Version Mismatch (CDS API Breaking Change)
**What goes wrong:** ERA5 download silently fails or returns empty data with pyaps3 < 0.3.6
**Why it happens:** ECMWF migrated to new CDS API in Feb 2025. Old cdsapirc token format and old pyaps3 versions cannot authenticate.
**How to avoid:** Pin `pyaps3 >= 0.3.6` in conda-env.yml. Validate CDS credentials at pipeline start (D-03) by attempting a lightweight CDS API call before committing to CSLC processing.
**Warning signs:** MintPy's `correct_troposphere` step completes without error but produces zero-valued corrections.

### Pitfall 2: dolphin Unwrapping Mode Configuration
**What goes wrong:** dolphin has its own internal unwrapping step via `unwrap_options`. If subsideo also runs tophu separately, the interferograms get unwrapped twice or the pipeline skips the dolphin-internal unwrap and feeds wrapped phase to MintPy.
**Why it happens:** dolphin's `DisplacementWorkflow` includes `unwrap_options: UnwrapOptions` and `timeseries_options: TimeseriesOptions` that can run the entire chain internally.
**How to avoid:** Use dolphin's full workflow including its internal unwrapping and time-series steps if possible. Only separate the stages if the post-unwrap QC (D-05) requires intercepting between unwrapping and time-series inversion. If using dolphin end-to-end, configure `unwrap_options` to use tophu/snaphu backend.
**Warning signs:** Duplicate output directories with wrapped and unwrapped phase.

### Pitfall 3: LOS-to-Vertical Projection Accuracy
**What goes wrong:** Validation correlation drops below 0.92 threshold.
**Why it happens:** Simple `v_vert = v_los / cos(theta)` assumes negligible horizontal motion. In tectonically active areas or landslide zones, horizontal motion can cause 10-67% error in the vertical estimate.
**How to avoid:** For validation, select test AOIs with predominantly vertical motion (subsidence areas, e.g., Netherlands, Po Valley). Document the assumption. Use per-pixel incidence angle, not a single mean value.
**Warning signs:** Systematic bias in one direction; scatter plot shows non-linear relationship.

### Pitfall 4: EGMS Grid Alignment
**What goes wrong:** Metrics are computed on misaligned grids, producing artificially low correlation.
**Why it happens:** EGMS Ortho products use a specific grid definition that may not match subsideo's output UTM grid exactly.
**How to avoid:** Always reproject subsideo output to the EGMS reference grid (not vice versa), matching the compare_rtc.py pattern. Handle partial overlap (EGMS may not cover the full AOI) by computing metrics only over the intersection.
**Warning signs:** r value near 0 despite visual agreement; large NaN areas after reprojection.

### Pitfall 5: MintPy Input Format for dolphin Outputs
**What goes wrong:** MintPy cannot read the interferogram stack produced by dolphin.
**Why it happens:** MintPy supports multiple input formats (ISCE, ARIA, FRInGE, HyP3, etc.) but expects specific directory structures and metadata files for each. dolphin outputs need to be in a format MintPy can load.
**How to avoid:** dolphin's `DisplacementWorkflow` can produce output in a MintPy-compatible format when `timeseries_options` is configured. Alternatively, use dolphin's built-in MintPy integration. Check the `mintpy.load.processor` setting matches the dolphin output format.
**Warning signs:** MintPy's `load_data` step fails with "no data found" or reads wrong dimensions.

### Pitfall 6: dist-s1 Conda-Forge Availability
**What goes wrong:** dist-s1 not installable, blocking DIST-S1 product generation.
**Why it happens:** STATE.md notes: "DIST-S1 depends on opera-adt/dist-s1 ~April 2026 conda-forge release; treat as conditional until confirmed."
**How to avoid:** D-11 already handles this: conditional lazy import with clear `ImportError` message. Unit tests mock dist-s1. Integration tests skip if not installed.
**Warning signs:** `conda install -c conda-forge dist-s1` returns "package not found."

### Pitfall 7: dolphin Internal Unwrapping Already Includes Tophu
**What goes wrong:** Developer builds a separate tophu unwrapping step when dolphin already does it internally.
**Why it happens:** dolphin's `DisplacementWorkflow` has `unwrap_options` that configures the unwrapping method. When set to use tophu (or snaphu), dolphin runs the unwrapping as part of its workflow.
**How to avoid:** Check if dolphin's built-in workflow already chains phase linking -> unwrapping -> time-series. If it does, the "three separate stages" may actually be one dolphin `run()` call plus a post-hoc QC step. The planner should investigate whether to use dolphin end-to-end or split stages.
**Warning signs:** Reviewing dolphin source shows `unwrapping.py` and `timeseries_options` already in the workflow config.

## Code Examples

### dolphin DisplacementWorkflow API

```python
# Source: https://github.com/isce-framework/dolphin/blob/main/src/dolphin/workflows/displacement.py
# Confidence: HIGH (verified from source)

from dolphin.workflows.config import DisplacementWorkflow
from dolphin.workflows.displacement import run as dolphin_run, OutputPaths

# DisplacementWorkflow is a Pydantic model with these key fields:
# - cslc_file_list: list[Path]  (required)
# - input_options: InputOptions
# - output_options: OutputOptions
# - ps_options: PsOptions
# - phase_linking: PhaseLinkingOptions
# - interferogram_network: InterferogramNetwork
# - unwrap_options: UnwrapOptions
# - timeseries_options: TimeseriesOptions

cfg = DisplacementWorkflow(
    cslc_file_list=[Path("path/to/cslc1.h5"), Path("path/to/cslc2.h5")],
    # Additional options configured as needed
)
outputs: OutputPaths = dolphin_run(cfg)

# OutputPaths contains:
# - stitched_ifg_paths: list[Path]
# - stitched_cor_paths: list[Path]
# - unwrapped_paths: list[Path] | None
# - timeseries_paths: list[Path] | None
# - reference_point: ReferencePoint | None
```

### MintPy TimeSeriesAnalysis API

```python
# Source: https://github.com/insarlab/MintPy/blob/main/src/mintpy/smallbaselineApp.py
# Confidence: MEDIUM-HIGH (verified from source, limited docs)

from mintpy.smallbaselineApp import TimeSeriesAnalysis

# Key config file options (smallbaselineApp.cfg format):
# mintpy.load.processor = dolphin  (or isce, aria, etc.)
# mintpy.troposphericDelay.method = pyaps  (uses ERA5 by default)
# mintpy.troposphericDelay.weatherModel = ERA5
# mintpy.networkInversion.minTempCoh = 0.7
# mintpy.timeFunc.polynomial = 1  (linear velocity)

app = TimeSeriesAnalysis(
    customTemplateFile='my_config.cfg',
    workDir='/path/to/project',
)
app.open()
app.run(steps=[
    'load_data',
    'modify_network',
    'reference_point',
    'invert_network',
    'correct_troposphere',  # requires pyaps3 + cdsapirc
    'deramp',
    'correct_dem_error',
    'velocity',
])
app.close()

# Read velocity output:
from mintpy.utils import readfile
velocity, meta = readfile.read('velocity.h5')
```

### tophu multiscale_unwrap

```python
# Source: https://tophu.readthedocs.io/en/latest/api/tophu.multiscale_unwrap.html
# Confidence: MEDIUM (readthedocs 403, reconstructed from multiple sources)

import tophu

# SnaphuUnwrap is the callback for SNAPHU-based unwrapping
unwrapper = tophu.SnaphuUnwrap(
    cost="smooth",     # cost function: smooth or defo
    init="mcf",        # initialization: mcf or mst
)

# multiscale_unwrap performs tiled multi-resolution unwrapping
unwrapped, conncomp = tophu.multiscale_unwrap(
    ifg=interferogram,      # 2D complex interferogram array
    corr=coherence,         # 2D coherence [0,1] array
    nlooks=1.0,             # number of looks
    unwrap_func=unwrapper,  # unwrapping callback (SnaphuUnwrap)
    downsample_factor=(3, 3),  # coarse resolution factor
    ntiles=(2, 2),          # tile grid
)
```

### dist-s1 Workflow API

```python
# Source: https://github.com/opera-adt/dist-s1
# Confidence: HIGH (verified from README)

from pathlib import Path
from dist_s1 import run_dist_s1_workflow

run_dist_s1_workflow(
    mgrs_tile_id='33UUP',      # MGRS tile ID (EU example)
    post_date='2025-06-15',     # acquisition date
    track_number=95,            # Sentinel-1 relative orbit
    dst_dir=Path('output'),     # output directory
)

# Product validation:
from dist_s1.data_models.output_models import ProductDirectoryData
product = ProductDirectoryData.from_product_path('output/')
```

### LOS-to-Vertical Projection

```python
# Source: InSAR theory (Hanssen 2001; Ferretti et al. 2007)
# Confidence: HIGH (established formula)

import numpy as np

def los_to_vertical(
    velocity_los: np.ndarray,
    incidence_angle_rad: np.ndarray | float,
) -> np.ndarray:
    """Project LOS velocity to vertical component.

    Assumes negligible horizontal motion (valid for subsidence areas).
    v_vert = v_los / cos(theta)
    """
    return velocity_los / np.cos(incidence_angle_rad)

# Mean Sentinel-1 incidence angle ~33 degrees
# For per-pixel: extract from CSLC metadata or dolphin output
mean_theta = np.deg2rad(33.0)
v_vertical = los_to_vertical(v_los, mean_theta)
```

### Planar Ramp QC Check (D-05)

```python
# Source: standard InSAR QC approach
# Confidence: HIGH (well-established technique)

import numpy as np
from scipy.linalg import lstsq

def check_planar_ramp(
    unwrapped_phase: np.ndarray,
    threshold_rad: float = 1.0,
) -> dict:
    """Fit a plane to unwrapped phase and check residual.

    Returns dict with 'has_ramp', 'residual_rms', 'plane_coeffs'.
    """
    rows, cols = np.where(np.isfinite(unwrapped_phase))
    if len(rows) < 3:
        return {"has_ramp": False, "residual_rms": 0.0, "plane_coeffs": [0, 0, 0]}

    values = unwrapped_phase[rows, cols]

    # Design matrix: [row, col, 1]
    A = np.column_stack([rows, cols, np.ones(len(rows))])
    coeffs, residuals, _, _ = lstsq(A, values)

    # Compute residual RMS
    fitted = A @ coeffs
    rms = float(np.sqrt(np.mean((values - fitted) ** 2)))

    return {
        "has_ramp": rms > threshold_rad,
        "residual_rms": rms,
        "plane_coeffs": coeffs.tolist(),
    }
```

### CDS API Credential Validation (D-03)

```python
# Source: cdsapi library pattern
# Confidence: MEDIUM (API may vary by version)

from pathlib import Path

def validate_cds_credentials(cdsapirc_path: Path) -> None:
    """Validate CDS API credentials exist and are readable.

    Fails fast before any CSLC processing begins (D-03).
    """
    if not cdsapirc_path.exists():
        raise FileNotFoundError(
            f"CDS API configuration not found at {cdsapirc_path}. "
            "ERA5 tropospheric correction is mandatory for DISP-S1. "
            "Register at https://cds.climate.copernicus.eu/ and create "
            "~/.cdsapirc with your API key."
        )

    # Verify file has url and key fields
    content = cdsapirc_path.read_text()
    if "url:" not in content or "key:" not in content:
        raise ValueError(
            f"CDS API config at {cdsapirc_path} missing required fields. "
            "File must contain 'url:' and 'key:' entries."
        )
```

## Dataclass Design (Claude's Discretion)

Recommended types to add to `products/types.py`:

```python
@dataclass
class DISPConfig:
    """Configuration for a DISP-S1 processing run."""
    cslc_file_paths: list[Path]
    output_dir: Path
    cdsapirc_path: Path
    coherence_mask_threshold: float = 0.3
    ramp_check_threshold: float = 1.0
    product_version: str = "0.1.0"

@dataclass
class DISPResult:
    """Output from a DISP-S1 processing run."""
    velocity_path: Path | None
    timeseries_paths: list[Path]
    unwrapped_paths: list[Path]
    runconfig_path: Path
    valid: bool
    ramp_warnings: list[str] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)

@dataclass
class DISTConfig:
    """Configuration for a DIST-S1 processing run."""
    mgrs_tile_id: str
    post_date: str
    track_number: int
    output_dir: Path

@dataclass
class DISTResult:
    """Output from a DIST-S1 processing run."""
    output_paths: list[Path]
    valid: bool
    validation_errors: list[str] = field(default_factory=list)

@dataclass
class DISPValidationResult:
    """Validation metrics comparing DISP output against EGMS reference."""
    correlation: float
    velocity_bias_mm_yr: float
    pass_criteria: dict[str, bool] = field(default_factory=dict)
```

## Key Design Decision: dolphin End-to-End vs. Split Stages

**Important finding:** dolphin's `DisplacementWorkflow` can run the entire chain (phase linking -> unwrapping -> time-series) as a single `run()` call. The config includes `unwrap_options` (tophu/snaphu backend) and `timeseries_options`.

**Recommendation for D-05 compliance:** Use dolphin's full workflow for phase linking + unwrapping (stages 1-2), then intercept the unwrapped phase for planar ramp QC, then run MintPy separately for time-series inversion + ERA5 correction. This is because:
1. dolphin handles the phase-linking-to-unwrapping handoff internally (avoids format issues)
2. The post-unwrap QC (D-05) needs to inspect unwrapped phase before time-series inversion
3. MintPy provides more mature ERA5 tropospheric correction than dolphin's internal time-series

**Concrete approach:**
- Configure `DisplacementWorkflow` with unwrapping enabled but timeseries disabled
- After `dolphin_run()`, inspect `OutputPaths.unwrapped_paths` for planar ramp
- Feed unwrapped interferograms into MintPy's `TimeSeriesAnalysis`

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ISCE2 + StaMPS (PS only) | dolphin (PS+DS combined) | 2024 (JOSS paper) | Better performance on C-band short-baseline stacks |
| Manual SNAPHU tiling | tophu multi-scale unwrapping | 2023 | Automated tile management for large interferograms |
| Old CDS API (cdsapi v1) | New CDS API (cdsapi v2) | Feb 2025 | pyaps3 >= 0.3.6 required; old tokens break silently |
| SBAS via MintPy alone | dolphin + MintPy | 2024 | dolphin adds DS processing before MintPy time-series |
| Manual EGMS download | EGMStoolkit | 2024 (Springer paper) | Automated download of all 3 EGMS product levels |

## Open Questions

1. **dolphin-MintPy Format Compatibility**
   - What we know: dolphin outputs interferograms and MintPy reads them via `load_data`
   - What's unclear: Exact `mintpy.load.processor` setting for dolphin output format. May need `dolphin` or `isce` processor type.
   - Recommendation: During implementation, test with `mintpy.load.processor = dolphin` first. If not supported, check if dolphin outputs ISCE-compatible format.

2. **dist-s1 MGRS Tile vs AOI Interface**
   - What we know: dist-s1 API takes MGRS tile ID, not arbitrary AOI geometry
   - What's unclear: How to map arbitrary EU AOI to MGRS tile(s) for dist-s1 input
   - Recommendation: Use existing burst DB or a MGRS tile lookup utility. May need to run dist-s1 per-tile and mosaic.

3. **EGMStoolkit Python API Details**
   - What we know: EGMStoolkit can download EGMS Ortho products via CLI and Python
   - What's unclear: Exact Python function signatures for programmatic download (documentation not fully accessible)
   - Recommendation: During implementation, inspect EGMStoolkit source for download functions. Fallback: wrap the CLI entry point if Python API is insufficient.

4. **dolphin timeseries_options Scope**
   - What we know: dolphin has `timeseries_options: TimeseriesOptions` in its config
   - What's unclear: Whether dolphin's built-in time-series includes ERA5 correction or just basic inversion
   - Recommendation: Use MintPy for time-series (decision D-04 chains dolphin -> tophu -> MintPy, and D-03 requires ERA5 which MintPy handles natively).

## Project Constraints (from CLAUDE.md)

- **conda-forge deps:** dolphin, tophu, snaphu-py, MintPy, dist-s1 must come from conda-forge
- **Lazy imports:** All conda-forge-only deps must use lazy imports inside function bodies
- **Dataclasses over Pydantic for results** (Phase 2 decision): DISPResult, DISTResult, DISPValidationResult use `@dataclass`
- **Loguru for logging:** All pipeline stages use `logger.info/warning/error`
- **Line length 100, Python 3.10 target**
- **ruff + mypy strict** (ignore_missing_imports=true for GDAL/ISCE3/dolphin/MintPy)
- **pytest markers:** `@pytest.mark.integration` for live credentials, `@pytest.mark.validation` for full pipeline
- **Never commit credentials** (CDSE, Earthdata, CDS API)
- **80% coverage minimum**

## Sources

### Primary (HIGH confidence)
- [dolphin displacement.py source](https://github.com/isce-framework/dolphin/blob/main/src/dolphin/workflows/displacement.py) -- `run()` function signature, `OutputPaths` dataclass
- [dolphin config/_displacement.py source](https://github.com/isce-framework/dolphin/blob/main/src/dolphin/workflows/config/_displacement.py) -- `DisplacementWorkflow` class fields
- [dist-s1 README](https://github.com/opera-adt/dist-s1) -- `run_dist_s1_workflow()` API, install instructions
- [MintPy smallbaselineApp.py source](https://github.com/insarlab/MintPy/blob/main/src/mintpy/smallbaselineApp.py) -- `TimeSeriesAnalysis` class API
- [MintPy default config](https://github.com/insarlab/MintPy/blob/main/src/mintpy/defaults/smallbaselineApp.cfg) -- ERA5 and inversion settings

### Secondary (MEDIUM confidence)
- [dolphin PyPI](https://pypi.org/project/dolphin/) -- version 0.42.5, March 2026
- [tophu readthedocs](https://tophu.readthedocs.io/en/latest/api/tophu.multiscale_unwrap.html) -- `multiscale_unwrap` API (403 on fetch, reconstructed from multiple sources)
- [EGMStoolkit GitHub](https://github.com/alexisInSAR/EGMStoolkit) -- version 0.2.15
- [EGMS toolkit paper (Springer)](https://link.springer.com/article/10.1007/s12145-024-01356-w) -- published 2024
- [pyaps3 CDS migration discussion](https://github.com/insarlab/PyAPS/discussions/40) -- 0.3.6 requirement

### Tertiary (LOW confidence)
- tophu `multiscale_unwrap` exact parameter signature -- readthedocs returned 403; reconstructed from search results and snaphu-py docs
- EGMStoolkit Python API function signatures -- documentation site not fully accessible; CLI usage confirmed

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified via PyPI/GitHub with exact versions
- Architecture: MEDIUM-HIGH -- dolphin/MintPy Python APIs confirmed from source; exact format handoff between dolphin and MintPy needs implementation-time verification
- Pitfalls: HIGH -- pyaps3 CDS issue well-documented; unwrapping configuration verified from source

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (30 days; dolphin/MintPy are stable releases)
