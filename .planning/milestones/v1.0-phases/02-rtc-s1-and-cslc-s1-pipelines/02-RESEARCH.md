# Phase 02: RTC-S1 and CSLC-S1 Pipelines - Research

**Researched:** 2026-04-05
**Domain:** SAR product pipeline wrappers (opera-rtc, compass), output format compliance (COG/HDF5), validation metrics
**Confidence:** MEDIUM-HIGH

## Summary

This phase wraps two OPERA-ADT reference implementations -- opera-rtc (RTC-S1 backscatter) and COMPASS (CSLC-S1 coregistered SLC) -- with thin Python orchestrators that handle data fetching via the Phase 01 data access layer, programmatic YAML runconfig generation, algorithm invocation via Python API, output format compliance, and post-write validation. In parallel, a shared validation metrics module (RMSE, spatial correlation, bias, SSIM) and two per-product comparison modules are built to cross-compare outputs against OPERA N.Am. reference products downloaded from ASF DAAC.

Both opera-rtc and COMPASS follow the same pattern: they consume YAML runconfig files, load input SAFE/orbit/DEM paths from the config, and produce output files. The key integration work is (1) generating valid runconfigs from subsideo's Pydantic config, (2) calling their Python APIs (not subprocess), and (3) converting or validating outputs to match the OPERA product spec format that ASF distributes.

**Primary recommendation:** Build thin orchestrator functions in `products/rtc.py` and `products/cslc.py` that generate YAML runconfigs, call the upstream Python APIs (`rtc.runconfig.RunConfig.load_from_yaml()` + `rtc.rtc_s1.run_parallel()` for RTC; `compass.s1_cslc.run()` for CSLC), then validate the output. Build the validation framework as an independent module that operates purely on file paths and numpy arrays.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Thin Python API wrapper around `opera-rtc` (OPERA-ADT reference implementation). Call opera-rtc's Python API directly -- do not use subprocess/CLI invocation or reimplement RTC from raw isce3 calls. opera-rtc already produces spec-compliant 30m UTM COG output.
- **D-02:** The wrapper (`products/rtc.py`) orchestrates: fetch SLC via CDSEClient -> resolve bursts via burst DB -> fetch DEM via dem-stitcher -> fetch orbits -> generate opera-rtc runconfig -> call opera-rtc -> validate output.
- **D-03:** opera-rtc uses a YAML runconfig. Generate this programmatically from subsideo's Pydantic config, filling in paths to downloaded SLC, DEM, orbits, and output directory.
- **D-04:** Config-driven compass execution via Python API. compass (OPERA-ADT CSLC workflow) uses YAML runconfig files matching the ISCE3 workflow convention already adopted in Phase 01 config.
- **D-05:** The wrapper (`products/cslc.py`) orchestrates: fetch SLC -> resolve bursts -> fetch DEM -> fetch orbits -> generate compass runconfig -> call compass Python entry point -> validate HDF5 output.
- **D-06:** Use `s1-reader` to parse Sentinel-1 SAFE/zip into burst objects. Use `opera-utils` for burst ID extraction and frame mapping. These are the canonical OPERA-ADT libraries for SLC ingestion.
- **D-07:** Shared metric functions in `validation/metrics.py`: RMSE, spatial correlation (Pearson r), bias, SSIM. These are reusable across all product types in Phase 3/4.
- **D-08:** Per-product comparison modules: `validation/compare_rtc.py` and `validation/compare_cslc.py`. Each handles loading the OPERA N.Am. reference product (different format per product type), aligning spatial grids, and calling the shared metrics.
- **D-09:** Reference products fetched from ASF DAAC via `data/asf.py` (built in Phase 01). The comparison modules accept paths to both the subsideo output and the OPERA reference, returning a structured metrics result.
- **D-10:** RTC output written as Cloud-Optimized GeoTIFF via `rio-cogeo` with OPERA-compliant metadata (provenance, software version, run parameters). 30m UTM posting.
- **D-11:** CSLC output written as HDF5 following OPERA CSLC product specification hierarchy, readable by `opera-utils`. Use `h5py` for structure, `opera-utils` product I/O helpers for metadata layout.
- **D-12:** Lightweight `validate_product()` function runs post-write to confirm required metadata fields, chunking, CRS, and structure. Fails loudly if spec check fails -- do not silently produce non-compliant output.

### Claude's Discretion
- Internal helper functions and utility organization within products/ and validation/
- Test fixture design for mocked pipeline runs (synthetic arrays, fake HDF5/COG)
- Error message formatting for pipeline failures
- Whether to use xarray or raw numpy for intermediate array operations

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROD-01 | Library can produce RTC-S1 backscatter products from S1 IW SLC over EU AOIs using ISCE3 | opera-rtc Python API (`RunConfig.load_from_yaml()` + `run_parallel()`), YAML runconfig generation, Phase 01 data access layer |
| PROD-02 | Library can produce CSLC-S1 coregistered SLC products from S1 IW SLC over EU AOIs using ISCE3 | COMPASS Python API (`compass.s1_cslc.run()`), YAML runconfig generation, s1-reader for burst parsing |
| OUT-01 | RTC and DSWx products are written as Cloud-Optimised GeoTIFF with correct metadata | opera-rtc produces GeoTIFF natively; post-process to COG via rio-cogeo; OPERA metadata fields documented |
| OUT-02 | CSLC and DISP products are written as HDF5 following OPERA product specification hierarchy | COMPASS produces HDF5 natively following OPERA CSLC spec; validate with opera-utils readers |
| VAL-01 | Library computes pixel-level RMSE, spatial correlation, bias, and SSIM between products | numpy/scipy for RMSE/correlation/bias; scikit-image `structural_similarity` for SSIM; rasterio for grid alignment |
| VAL-02 | Library can compare RTC-S1 output against OPERA N.Am. RTC reference (RMSE < 0.5 dB, r > 0.99) | ASFClient downloads OPERA_L2_RTC-S1 products; rasterio reproject/align to common grid; apply dB-domain metrics |
| VAL-03 | Library can compare CSLC-S1 output against OPERA N.Am. CSLC reference (phase RMS < 0.05 rad) | ASFClient downloads OPERA_L2_CSLC-S1 HDF5; h5py to read complex data; phase difference via numpy angle operations |

</phase_requirements>

## Standard Stack

### Core Algorithm Libraries (conda-forge only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| opera-rtc | v1.0.4 (R5.3) | RTC-S1 backscatter workflow wrapping isce3 | OPERA-ADT official; produces 30m UTM output matching OPERA spec |
| compass | 0.5.6 | CSLC-S1 burst workflow wrapping isce3 | OPERA-ADT official CSLC-S1 workflow |
| isce3 | 0.25.10 | Underlying SAR processing engine | NASA/JPL reference; used by both opera-rtc and compass |
| s1-reader | 0.2.5 | Sentinel-1 SAFE/zip burst parsing | OPERA-ADT canonical SLC reader |
| opera-utils | 0.25.6 | Burst ID extraction, frame mapping, OPERA HDF5 I/O | OPERA-ADT reference toolkit |

### Output and Validation Libraries (pip-installable)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rio-cogeo | 7.0.2 | COG GeoTIFF creation with overview/block-size control | Best-in-class COG writer; needed for OPERA-compliant RTC output |
| rasterio | 1.5.0 | Raster I/O, reprojection, grid alignment for validation | Standard raster I/O; required for spatial resampling before metric computation |
| h5py | >=3.10 | HDF5 read/write for CSLC product and OPERA reference products | Direct HDF5 access; needed for CSLC product structure and validation |
| scikit-image | >=0.24 | SSIM computation via `structural_similarity` | Standard SSIM implementation; `skimage.metrics.structural_similarity` |
| numpy | >=1.26 | Array operations for all metrics | Baseline numerical array library |
| scipy | >=1.13 | Pearson correlation (`scipy.stats.pearsonr`) | Standard for statistical functions |
| ruamel.yaml | >=0.18 | YAML runconfig generation (round-trip mode) | Already used in Phase 01 config; preserves comments and ordering |

### Already Available from Phase 01

| Library | Purpose in This Phase |
|---------|----------------------|
| pystac-client + boto3 | CDSEClient for SLC download |
| dem-stitcher | DEM fetching |
| sentineleof / s1-orbits | Orbit file download |
| asf-search + earthaccess | OPERA reference product download (validation) |
| pydantic / pydantic-settings | Config models and runconfig generation |
| loguru | Logging throughout pipeline orchestration |

## Architecture Patterns

### Recommended Project Structure (New Files)
```
src/subsideo/
├── products/               # NEW: Pipeline orchestrators
│   ├── __init__.py
│   ├── rtc.py              # RTC-S1 orchestrator (D-01, D-02, D-03)
│   └── cslc.py             # CSLC-S1 orchestrator (D-04, D-05, D-06)
├── validation/             # NEW: Validation framework
│   ├── __init__.py
│   ├── metrics.py          # Shared: RMSE, correlation, bias, SSIM (D-07)
│   ├── compare_rtc.py      # RTC vs OPERA N.Am. comparison (D-08)
│   └── compare_cslc.py     # CSLC vs OPERA N.Am. comparison (D-08)
tests/
├── unit/
│   ├── test_rtc_pipeline.py
│   ├── test_cslc_pipeline.py
│   ├── test_metrics.py
│   ├── test_compare_rtc.py
│   └── test_compare_cslc.py
```

### Pattern 1: Config-to-Runconfig Translation

**What:** Each pipeline has a Pydantic model (e.g., `RTCConfig`) that represents subsideo's view of the run parameters. A `generate_runconfig()` function translates this into the upstream YAML format that opera-rtc/compass expect.

**When to use:** Every pipeline invocation. This is the bridge between subsideo's config and the upstream tools.

**Example:**
```python
# products/rtc.py
from pydantic import BaseModel, Field
from pathlib import Path
from ruamel.yaml import YAML

class RTCConfig(BaseModel):
    """Subsideo RTC-S1 run configuration."""
    safe_file_paths: list[Path]
    orbit_file_path: Path
    dem_file: Path
    burst_id: list[str]
    output_dir: Path
    product_version: str = "0.1.0"
    output_posting_m: float = 30.0

def generate_rtc_runconfig(cfg: RTCConfig, output_yaml: Path) -> Path:
    """Generate opera-rtc YAML runconfig from subsideo RTCConfig."""
    runconfig = {
        "runconfig": {
            "name": "rtc_s1_workflow",
            "groups": {
                "primary_executable": {"product_type": "RTC_S1"},
                "input_file_group": {
                    "safe_file_path": [str(p) for p in cfg.safe_file_paths],
                    "orbit_file_path": [str(cfg.orbit_file_path)],
                    "burst_id": cfg.burst_id,
                },
                "dynamic_ancillary_file_group": {
                    "dem_file": str(cfg.dem_file),
                },
                "product_group": {
                    "product_path": str(cfg.output_dir),
                    "output_dir": str(cfg.output_dir),
                    "product_version": cfg.product_version,
                },
            },
        }
    }
    yaml = YAML()
    yaml.default_flow_style = False
    with open(output_yaml, "w") as fh:
        yaml.dump(runconfig, fh)
    return output_yaml
```

### Pattern 2: Pipeline Orchestrator (fetch -> configure -> run -> validate)

**What:** Each pipeline function follows a fixed sequence: resolve inputs -> download ancillary data -> generate runconfig YAML -> call upstream Python API -> validate output format.

**When to use:** All pipeline orchestrators (`products/rtc.py`, `products/cslc.py`).

**Example:**
```python
# products/rtc.py
from dataclasses import dataclass
from pathlib import Path

@dataclass
class RTCResult:
    """Result of an RTC-S1 pipeline run."""
    output_paths: list[Path]
    runconfig_path: Path
    burst_ids: list[str]
    valid: bool
    validation_errors: list[str]

def run_rtc(
    safe_paths: list[Path],
    orbit_path: Path,
    dem_path: Path,
    burst_ids: list[str],
    output_dir: Path,
) -> RTCResult:
    """Execute the RTC-S1 pipeline via opera-rtc Python API."""
    # 1. Generate runconfig
    cfg = RTCConfig(
        safe_file_paths=safe_paths,
        orbit_file_path=orbit_path,
        dem_file=dem_path,
        burst_id=burst_ids,
        output_dir=output_dir,
    )
    runconfig_yaml = output_dir / "rtc_runconfig.yaml"
    generate_rtc_runconfig(cfg, runconfig_yaml)

    # 2. Load and run via opera-rtc Python API
    from rtc.runconfig import RunConfig
    from rtc.rtc_s1 import run_parallel

    opera_cfg = RunConfig.load_from_yaml(str(runconfig_yaml))
    run_parallel(opera_cfg, str(output_dir / "rtc.log"), True)

    # 3. Post-process: ensure COG compliance
    output_tifs = list(output_dir.glob("*.tif"))
    cog_paths = [_ensure_cog(p) for p in output_tifs]

    # 4. Validate output
    errors = validate_rtc_product(cog_paths)

    return RTCResult(
        output_paths=cog_paths,
        runconfig_path=runconfig_yaml,
        burst_ids=burst_ids,
        valid=len(errors) == 0,
        validation_errors=errors,
    )
```

### Pattern 3: Pure-Function Validation Metrics

**What:** Metrics functions take numpy arrays and return scalar values. No I/O, no file loading. Comparison modules handle loading/alignment and call metrics.

**When to use:** `validation/metrics.py` -- always pure functions. `validation/compare_*.py` -- handles file I/O and calls metrics.

**Example:**
```python
# validation/metrics.py
import numpy as np
from scipy import stats

def rmse(predicted: np.ndarray, reference: np.ndarray) -> float:
    """Root mean squared error between two arrays."""
    mask = np.isfinite(predicted) & np.isfinite(reference)
    diff = predicted[mask] - reference[mask]
    return float(np.sqrt(np.mean(diff ** 2)))

def spatial_correlation(predicted: np.ndarray, reference: np.ndarray) -> float:
    """Pearson correlation coefficient between two 2D arrays."""
    mask = np.isfinite(predicted) & np.isfinite(reference)
    r, _ = stats.pearsonr(predicted[mask].ravel(), reference[mask].ravel())
    return float(r)

def bias(predicted: np.ndarray, reference: np.ndarray) -> float:
    """Mean bias (predicted - reference)."""
    mask = np.isfinite(predicted) & np.isfinite(reference)
    return float(np.mean(predicted[mask] - reference[mask]))

def ssim(
    predicted: np.ndarray,
    reference: np.ndarray,
    data_range: float | None = None,
) -> float:
    """Structural similarity index (SSIM)."""
    from skimage.metrics import structural_similarity
    mask = np.isfinite(predicted) & np.isfinite(reference)
    # Use bounding box of valid data for SSIM
    rows, cols = np.where(mask)
    if len(rows) == 0:
        return 0.0
    r0, r1 = rows.min(), rows.max() + 1
    c0, c1 = cols.min(), cols.max() + 1
    p = predicted[r0:r1, c0:c1]
    r = reference[r0:r1, c0:c1]
    if data_range is None:
        data_range = float(np.nanmax(r) - np.nanmin(r))
    return float(structural_similarity(p, r, data_range=data_range))
```

### Anti-Patterns to Avoid

- **Subprocess invocation of opera-rtc or compass:** Both have Python APIs. Use `RunConfig.load_from_yaml()` + `run_parallel()` for RTC, and `compass.s1_cslc.run()` for CSLC. Subprocess hides errors, loses structured logging, and makes testing impossible.
- **Downloading inside wrappers:** All data fetching (SLC, DEM, orbits) must happen before the pipeline function is called. Wrappers receive paths, not URLs.
- **Computing metrics on misaligned grids:** Always reproject both product and reference to the same CRS/resolution before computing metrics. Use rasterio reproject with bilinear resampling.
- **NaN handling in metrics:** SAR products have nodata pixels (shadow/layover). All metric functions must mask NaN/nodata before computation. Never let NaN propagate into RMSE or correlation.
- **Mixing dB and linear domains:** RTC products can be in gamma0 (linear power) or dB. Validation RMSE of 0.5 dB means the comparison must be done in dB domain. Always convert to dB before metric computation for RTC.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RTC backscatter computation | Custom isce3 RTC calls | `opera-rtc` Python API | opera-rtc handles burst extraction, radiometric calibration, terrain correction, geocoding, and mosaicking. Reimplementing is months of work. |
| CSLC burst coregistration | Custom isce3 coregistration | `compass` Python API | compass handles reference burst selection, orbit-based coregistration, rdr2geo/geo2rdr transforms, and geocoded SLC output. |
| COG creation with overviews | Custom GDAL/rasterio COG writing | `rio-cogeo` | rio-cogeo handles overview generation, block sizing, compression, and COG validation in one call. |
| SSIM computation | Custom structural similarity | `skimage.metrics.structural_similarity` | SSIM has a specific mathematical formulation with windowed means/variances. The scikit-image implementation is tested and optimised. |
| OPERA reference product download | Custom HTTP/S3 download | `ASFClient` (Phase 01) | Already built. Handles Earthdata auth, product type filtering, and resumable download. |
| Burst ID resolution | Custom burst geometry matching | `query_bursts_for_aoi()` (Phase 01) | Already built. Handles EU burst DB spatial query and UTM zone assignment. |

## Common Pitfalls

### Pitfall 1: opera-rtc Produces HDF5 + GeoTIFF, Not COG

**What goes wrong:** opera-rtc's native output is HDF5 (primary) plus standard GeoTIFF (secondary). The GeoTIFF output is NOT Cloud-Optimised. Treating it as COG-ready and shipping it without conversion will fail COG validation.

**Why it happens:** opera-rtc's `mosaic_geobursts.py` writes using `output_raster_format='GTiff'` with standard GDAL driver settings. No internal overview generation or tiled layout.

**How to avoid:** After opera-rtc completes, run `rio-cogeo` on each output GeoTIFF to produce a properly tiled, overview-equipped COG. Add OPERA-compliant metadata as GeoTIFF tags.

**Warning signs:** `rio_cogeo.cog_validate()` returns `is_valid=False` on opera-rtc's direct output.

### Pitfall 2: CSLC Phase Comparison Requires Complex Coherence

**What goes wrong:** Naively computing phase RMS between two CSLC products by taking `angle(product) - angle(reference)` produces meaningless results if the two products have different absolute phase offsets (different orbit solutions or reference points).

**Why it happens:** CSLC products contain complex-valued (amplitude + phase) data. The absolute phase depends on the slant range path which differs between processing systems. Only the relative phase (interferometric phase) or the coherence magnitude is physically meaningful for comparison.

**How to avoid:** For CSLC validation, compute the interferometric phase: `angle(product * conj(reference))`. This cancels the common slant range contribution. The RMS of this interferometric phase should be < 0.05 rad for matching acquisitions. Also compute the cross-correlation magnitude (coherence).

**Warning signs:** Phase RMS values near pi (meaningless result) or near 0 only when product and reference are identical files.

### Pitfall 3: Grid Alignment Before Metrics

**What goes wrong:** The subsideo product and OPERA reference may have slightly different grid origins, pixel sizes, or CRS (different UTM zone for N.Am. vs EU). Computing pixel-level metrics on misaligned grids produces inflated RMSE and deflated correlation.

**Why it happens:** OPERA N.Am. products use N.Am. UTM zones. Subsideo products use EU UTM zones. Even within the same zone, grid origins may differ by sub-pixel amounts.

**How to avoid:** In each comparison module (`compare_rtc.py`, `compare_cslc.py`), always reproject both product and reference to a common grid using `rasterio.warp.reproject()` with bilinear resampling before calling any metric function. The reference grid should be the target (reproject the subsideo output to match the reference).

**Warning signs:** RMSE values that are orders of magnitude above expected thresholds even for identical data processed twice.

### Pitfall 4: YAML Runconfig Schema Validation

**What goes wrong:** opera-rtc and compass validate their YAML runconfigs against JSON/YAML schemas using `yamale`. If the generated runconfig has missing required fields, unexpected field names, or wrong types, the upstream library raises a cryptic validation error.

**Why it happens:** The YAML schema is defined in `schemas/` subdirectories of opera-rtc and compass. The schema is strict and field names are exact (e.g., `safe_file_path` not `safe_files`).

**How to avoid:** Study the default YAML templates in each library's `defaults/` directory. For opera-rtc: `src/rtc/defaults/rtc_s1.yaml`. For compass: `src/compass/defaults/s1_cslc_geo.yaml`. Start from the default and override only the fields you need. Use `deep_merge(defaults, overrides)` pattern.

**Warning signs:** `yamale.YamaleError` or `KeyError` when calling `RunConfig.load_from_yaml()`.

### Pitfall 5: SSIM Requires Same-Sized Arrays and data_range

**What goes wrong:** `skimage.metrics.structural_similarity` fails or returns incorrect values if arrays have different shapes, contain NaN, or if `data_range` is not specified for floating-point data.

**Why it happens:** SSIM uses a sliding window to compute local statistics. NaN in the window corrupts the calculation. Without explicit `data_range`, scikit-image uses the data type range (0-255 for uint8, which is wrong for float32 SAR data).

**How to avoid:** Always: (1) align arrays to same shape via rasterio reproject, (2) fill NaN with a neutral value or crop to valid data bounding box, (3) pass `data_range` explicitly as the range of the reference data. For RTC in dB domain, a typical data_range is ~30 dB.

**Warning signs:** SSIM near 0 or near 1 regardless of actual similarity; `ValueError` about array shapes.

## Code Examples

### opera-rtc Python API Invocation
```python
# Source: opera-adt/RTC GitHub repository analysis
# rtc.runconfig.RunConfig.load_from_yaml() loads and validates YAML
# rtc.rtc_s1.run_parallel() executes the full RTC workflow

from rtc.runconfig import RunConfig
from rtc.rtc_s1 import run_parallel

# Load validated runconfig from generated YAML
cfg = RunConfig.load_from_yaml(str(runconfig_yaml_path))

# Execute RTC processing (parallel burst processing + mosaicking)
run_parallel(
    cfg=cfg,
    logfile_path=str(output_dir / "rtc.log"),
    flag_logger_full_format=True,
)
# Output files written to cfg.groups.product_group.product_path
```

### compass (CSLC) Python API Invocation
```python
# Source: opera-adt/COMPASS GitHub repository analysis
# compass.s1_cslc.run() accepts a YAML path and grid type string

from compass.s1_cslc import run as run_cslc

# Execute CSLC processing in geocoded grid coordinates
run_cslc(
    run_config_path=str(runconfig_yaml_path),
    grid_type="geo",  # geocoded SLC output (not radar coordinates)
)
# Output HDF5 written to path specified in runconfig product_path_group
```

### opera-rtc YAML Runconfig Structure (Minimal Required Fields)
```yaml
# Source: opera-adt/RTC src/rtc/defaults/rtc_s1.yaml
runconfig:
  name: rtc_s1_workflow
  groups:
    primary_executable:
      product_type: RTC_S1  # REQUIRED
    input_file_group:
      safe_file_path:       # REQUIRED: list of SAFE zip paths
        - /path/to/S1A_IW_SLC.zip
      orbit_file_path:      # REQUIRED: list of orbit EOF paths
        - /path/to/S1A_OPER_AUX_POEORB.EOF
      burst_id:             # Optional: list of burst IDs to process
        - T123-456789-IW2
    dynamic_ancillary_file_group:
      dem_file: /path/to/dem.tif
    static_ancillary_file_group:
      burst_database_file: null  # Optional: use built-in
    product_group:
      product_path: /output/rtc/
      output_dir: /output/rtc/
      product_version: "0.1.0"
```

### compass YAML Runconfig Structure (Minimal Required Fields)
```yaml
# Source: opera-adt/COMPASS src/compass/defaults/s1_cslc_geo.yaml
runconfig:
  name: cslc_s1_workflow
  groups:
    input_file_group:
      safe_file_path:       # REQUIRED: list of SAFE zip paths
        - /path/to/S1A_IW_SLC.zip
      orbit_file_path:      # REQUIRED: list of orbit EOF paths
        - /path/to/S1A_OPER_AUX_POEORB.EOF
      burst_id: null        # Optional: process specific bursts
    dynamic_ancillary_file_group:
      dem_file: /path/to/dem.tif
      tec_file: null        # Optional: ionospheric correction
    product_path_group:
      product_path: /output/cslc/
      scratch_path: /output/cslc/scratch/
      product_version: "0.1.0"
    primary_executable:
      product_type: CSLC_S1
```

### COG Conversion Post-Processing
```python
# Source: rio-cogeo documentation
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles

def ensure_cog(input_tif: Path, output_cog: Path | None = None) -> Path:
    """Convert a GeoTIFF to Cloud-Optimized GeoTIFF."""
    output_cog = output_cog or input_tif.with_suffix(".cog.tif")
    profile = cog_profiles.get("deflate")  # DEFLATE compression
    cog_translate(
        str(input_tif),
        str(output_cog),
        profile,
        overview_level=5,       # Build 5 overview levels
        overview_resampling="nearest",
        use_cog_driver=True,    # Use GDAL COG driver
    )
    return output_cog
```

### RTC Validation Comparison (dB Domain)
```python
# validation/compare_rtc.py
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

from subsideo.validation.metrics import rmse, spatial_correlation, bias, ssim

@dataclass
class RTCValidationResult:
    rmse_db: float
    correlation: float
    bias_db: float
    ssim_value: float
    pass_criteria: dict[str, bool]

def compare_rtc(
    product_path: Path,
    reference_path: Path,
) -> RTCValidationResult:
    """Compare RTC product against OPERA N.Am. reference in dB domain."""
    # Load and align grids
    with rasterio.open(reference_path) as ref:
        ref_data = ref.read(1).astype(np.float64)
        ref_profile = ref.profile

    with rasterio.open(product_path) as prod:
        prod_data = np.empty_like(ref_data)
        reproject(
            source=rasterio.band(prod, 1),
            destination=prod_data,
            dst_transform=ref_profile["transform"],
            dst_crs=ref_profile["crs"],
            resampling=Resampling.bilinear,
        )

    # Convert to dB (RTC is in linear power)
    ref_db = 10.0 * np.log10(np.where(ref_data > 0, ref_data, np.nan))
    prod_db = 10.0 * np.log10(np.where(prod_data > 0, prod_data, np.nan))

    result = RTCValidationResult(
        rmse_db=rmse(prod_db, ref_db),
        correlation=spatial_correlation(prod_db, ref_db),
        bias_db=bias(prod_db, ref_db),
        ssim_value=ssim(prod_db, ref_db),
        pass_criteria={
            "rmse_lt_0.5dB": rmse(prod_db, ref_db) < 0.5,
            "correlation_gt_0.99": spatial_correlation(prod_db, ref_db) > 0.99,
        },
    )
    return result
```

### CSLC Phase Validation (Interferometric Phase)
```python
# validation/compare_cslc.py
import h5py
import numpy as np

def compare_cslc(
    product_path: Path,
    reference_path: Path,
) -> CSLCValidationResult:
    """Compare CSLC product against OPERA N.Am. reference via interferometric phase."""
    # Load complex data from HDF5
    with h5py.File(product_path, "r") as f:
        prod_complex = f["/data/VV"][:]  # complex64 array

    with h5py.File(reference_path, "r") as f:
        ref_complex = f["/data/VV"][:]

    # Compute interferometric phase (cancels common slant range)
    ifg = prod_complex * np.conj(ref_complex)
    phase_diff = np.angle(ifg)

    # Mask zero-amplitude pixels
    mask = (np.abs(prod_complex) > 0) & (np.abs(ref_complex) > 0)
    phase_rms = float(np.sqrt(np.mean(phase_diff[mask] ** 2)))

    return CSLCValidationResult(
        phase_rms_rad=phase_rms,
        coherence=float(np.abs(np.mean(ifg[mask] / np.abs(ifg[mask])))),
        pass_criteria={"phase_rms_lt_0.05rad": phase_rms < 0.05},
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom isce3 RTC calls | opera-rtc wrapper (v1.0.4) | 2024 R5.3 release | No need to chain individual isce3 functions; opera-rtc handles full workflow |
| ISCE2 for SAR processing | ISCE3 (0.25.x) | 2023-2024 | ISCE2 in maintenance; ISCE3 is the NISAR/OPERA baseline |
| Manual COG creation via GDAL | rio-cogeo 7.x with GDAL COG driver | 2024 | `use_cog_driver=True` flag uses native GDAL COG driver, faster and more reliable |
| `skimage.measure.compare_ssim` | `skimage.metrics.structural_similarity` | scikit-image 0.16 | Old function name removed; must use new import path |

## Open Questions

1. **OPERA RTC output format: HDF5 vs COG**
   - What we know: opera-rtc produces both HDF5 (primary metadata + data) and GeoTIFF (raster layers). The OPERA distribution on ASF packages GeoTIFF for raster data + HDF5 for metadata. The GeoTIFF is NOT COG out of the box.
   - What's unclear: Whether opera-rtc has a flag to directly produce COG, or if post-processing via rio-cogeo is always needed.
   - Recommendation: Always post-process with rio-cogeo to guarantee COG compliance (D-10). This is safer than relying on upstream flags.

2. **CSLC HDF5 Dataset Paths**
   - What we know: CSLC products contain complex backscatter under a `/data/` group. The OPERA spec uses CF-1.8 conventions.
   - What's unclear: Exact HDF5 group hierarchy (e.g., `/data/VV` vs `/science/SENTINEL1/CSLC/grids/VV`). This varies by OPERA product version.
   - Recommendation: Use opera-utils I/O helpers to read CSLC products rather than hardcoding HDF5 paths. If writing, inspect compass's output to match the structure it produces.

3. **Matching Acquisitions for Validation**
   - What we know: Validation requires the same Sentinel-1 acquisition processed by both subsideo (EU AOI) and OPERA (N.Am.). There is no geographic overlap between EU and N.Am.
   - What's unclear: The validation approach must use an N.Am. AOI for the comparison test (same input data processed by subsideo and by OPERA). This means the validation test is not run on EU data.
   - Recommendation: For validation, process an N.Am. Sentinel-1 acquisition through both subsideo (using the N.Am. burst DB from opera-utils, or by using a matching acquisition) and compare against the OPERA product from ASF. Document that validation uses N.Am. acquisitions; operational use targets EU.

## Project Constraints (from CLAUDE.md)

- **Conda-forge deps:** isce3, GDAL, dolphin, tophu, snaphu from conda-forge only -- never pip install
- **opera-rtc and compass:** Available via conda-forge; must be installed in the conda environment
- **ruff** with line-length 100, target Python 3.10; isort via ruff with `known-first-party = ["subsideo"]`
- **mypy strict** mode (but `ignore_missing_imports = true` for GDAL/ISCE3)
- **pytest** with `--cov=subsideo --cov-report=term-missing` and 80% coverage minimum
- **Never commit credentials:** CDSE and Earthdata credentials via env vars / `.env`
- **loguru** for structured logging -- use existing `utils/logging.py` pattern
- **Pydantic v2** for all config models
- **Two-layer install:** conda-forge for native deps, pip for pure-Python
- **GSD Workflow:** Work through GSD commands; do not make direct repo edits outside GSD

## Sources

### Primary (HIGH confidence)
- [opera-adt/RTC GitHub](https://github.com/opera-adt/RTC) -- source code analysis of `rtc_s1.py`, `runconfig.py`, `h5_prep.py`, `mosaic_geobursts.py`
- [opera-adt/COMPASS GitHub](https://github.com/opera-adt/COMPASS) -- source code analysis of `s1_cslc.py`, `defaults/s1_cslc_geo.yaml`
- [OPERA RTC-S1 Product Guide (ASF HyP3)](https://hyp3-docs.asf.alaska.edu/guides/opera_rtc_product_guide/) -- product format, layers, naming
- [OPERA CSLC-S1 Earthdata catalog](https://www.earthdata.nasa.gov/data/catalog/asf-opera-l2-cslc-s1-v1-1) -- HDF5 format, CF-1.8, content description
- [scikit-image SSIM docs](https://scikit-image.org/docs/stable/api/skimage.metrics.html) -- `structural_similarity` API

### Secondary (MEDIUM confidence)
- [OPERA RTC-S1 Product Specification PDF](https://d2pn8kiwq2w21t.cloudfront.net/documents/ProductSpec_RTC-S1.pdf) -- metadata field tables (not fully extracted)
- [opera-adt/CSLC-S1_Specs GitHub](https://github.com/opera-adt/CSLC-S1_Specs) -- product spec repository (XML-based, not fully parsed)
- [OPERA-Cal-Val/calval-CSLC](https://github.com/OPERA-Cal-Val/calval-CSLC) -- CSLC validation tools (reference approach)

### Tertiary (LOW confidence)
- opera-rtc COG output capabilities -- could not confirm whether opera-rtc has a native COG flag; recommend rio-cogeo post-processing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- opera-rtc and compass are the official OPERA-ADT implementations; versions verified against GitHub releases
- Architecture: HIGH -- orchestrator pattern well-established from Phase 01; upstream Python API signatures confirmed from source code
- Pitfalls: MEDIUM-HIGH -- format conversion (GeoTIFF to COG) confirmed from source analysis; phase comparison approach is domain knowledge from InSAR literature
- Validation metrics: HIGH -- numpy/scipy/scikit-image APIs are stable and well-documented

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (opera-rtc and compass are stable releases; unlikely to change in 30 days)

---
*Phase: 02-rtc-s1-and-cslc-s1-pipelines*
*Research completed: 2026-04-05*
