# Phase 4: DSWx-S2 Pipeline and Full Interface - Research

**Researched:** 2026-04-05
**Domain:** DSWx-S2 surface water mapping, CLI interface, validation reporting
**Confidence:** HIGH

## Summary

Phase 4 covers three workstreams: (1) porting the OPERA DSWx-HLS DSWE algorithm from HLS/Landsat bands to Sentinel-2 L2A bands, (2) completing the Typer CLI with all product subcommands, and (3) building the validation report generator (HTML + Markdown). The DSWE algorithm is well-documented via NASA's PROTEUS repository (Apache 2.0) -- it consists of five diagnostic spectral tests using MNDWI, MBSRV, MBSRN, AWESH, and NDVI with published default thresholds. Sentinel-2 L2A bands map cleanly to the required HLS bands. JRC Global Surface Water Monthly History tiles are available via direct HTTP from JRC's FTP server without requiring Google Earth Engine.

The existing codebase has strong patterns to follow: thin-wrapper pipeline orchestrators (rtc.py, disp.py, dist.py), comparison modules (compare_rtc.py, compare_disp.py), shared metrics (metrics.py), and dataclass-based result types (types.py). The CLI skeleton already exists with a Typer app and `check-env` subcommand. Jinja2 is already a dependency (via pydantic/typer transitive) and can be used directly for HTML report templates.

**Primary recommendation:** Implement `products/dswx.py` following the exact same thin-wrapper pattern as rtc.py, port the five DSWE diagnostic tests with PROTEUS default thresholds mapped to S2 L2A bands, validate against JRC Monthly History tiles, then wire all CLI subcommands and report generation.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Start with OPERA DSWx-HLS DSWE thresholds translated to Sentinel-2 L2A band equivalents. Validate against JRC. If F1 > 0.90, ship it. Only invest in EU-specific threshold tuning if OPERA defaults fail validation -- do not front-load threshold R&D.
- **D-02:** Use Sentinel-2 L2A's built-in Scene Classification Layer (SCL) for cloud masking. Classes 8-10 (cloud medium/high probability, thin cirrus) and class 3 (cloud shadow) are masked out. No additional cloud detection library needed.
- **D-03:** Output at 30m UTM posting to match OPERA spec and maintain consistency with RTC/DISP output resolution. Sentinel-2 10m bands are downsampled during DSWE computation. JRC reference is also 30m, simplifying validation grid alignment.
- **D-04:** Follow the thin-wrapper pipeline pattern from Phase 2/3. Create `products/dswx.py` with `run_dswx()` (takes S2 L2A paths) and `run_dswx_from_aoi()` (takes AOI + date range, queries CDSE for S2 L2A via existing CDSEClient). Lazy imports for any heavy deps.
- **D-05:** Validate against JRC Monthly Water History maps. Match DSWx output month to JRC month for temporal alignment. Binary comparison: DSWx water pixels vs JRC water-detected pixels.
- **D-06:** Download JRC tiles via direct HTTP from ec.europa.eu (no Google Earth Engine dependency). Tile-based download pattern similar to DEM download in Phase 1. Implement in `validation/compare_dswx.py`.
- **D-07:** Compute F1 score as primary metric (F1 > 0.90 pass criterion). Also compute precision, recall, and overall accuracy for diagnostic reporting. Reuse `validation/metrics.py` for any shared metric utilities.
- **D-08:** All product subcommands accept `--aoi path/to/aoi.geojson` (GeoJSON file path, validated as Polygon/MultiPolygon on load). No inline bbox or WKT.
- **D-09:** Date range via two separate flags: `--start 2025-01-01 --end 2025-03-01`. ISO 8601 date format.
- **D-10:** Progress reporting via existing loguru structured logging with stage-level messages. `--verbose` flag for debug-level output. No progress bars.
- **D-11:** Each product subcommand (`rtc`, `cslc`, `disp`, `dswx`, `dist`) calls the corresponding `run_{product}_from_aoi()` function. `validate` subcommand runs comparison modules on completed outputs.
- **D-12:** Output directory defaults to current working directory, overridable with `--out path/to/dir`. Each product creates a subdirectory within the output dir.
- **D-13:** Per-product reports (one HTML + one Markdown per product type). No combined summary report.
- **D-14:** Each report includes: metric summary table (pass/fail per criterion), spatial difference map (matplotlib figure), and scatter plot (product vs reference with regression line). Two figure types plus metric table.
- **D-15:** Use Jinja2 templates for HTML generation. Matplotlib generates figures as inline SVG (for HTML) or saved PNG (for Markdown). Report function in `validation/report.py`.
- **D-16:** OPERA-compliant identification metadata (OUT-03): all products must include provenance, software version, and run parameters in their output metadata. This applies to all existing products and the new DSWx.

### Claude's Discretion
- DSWx DSWE band index formulas and threshold mapping from HLS to S2 bands
- JRC tile URL pattern and download/caching implementation
- Jinja2 template design and CSS styling for HTML reports
- Internal helper functions for figure generation
- Whether to add `dist` as a CLI subcommand (dist-s1 may not be available yet)
- Test fixture design for DSWx and report generation tests

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROD-04 | Library can produce DSWx-S2 surface water extent products from S2 L2A over EU AOIs | DSWE algorithm fully documented from PROTEUS source; S2 band mapping verified; thin-wrapper pattern established |
| OUT-03 | All products include OPERA-compliant identification metadata (provenance, version, params) | Metadata can be injected via rasterio/h5py tag writing; applies to all existing products + new DSWx |
| VAL-05 | Library can compare DSWx-S2 output against JRC Global Surface Water (F1 > 0.90) | JRC Monthly History tiles available via HTTP; F1/precision/recall metrics straightforward to implement |
| VAL-06 | Library generates HTML/Markdown validation reports with metric tables and diff maps | Jinja2 available; matplotlib for figures; existing ValidationResult dataclasses provide input data |
| CLI-01 | Typer CLI exposes subcommands: rtc, cslc, disp, dswx, validate | Existing Typer app with check-env command; add subcommands following same pattern |
| CLI-02 | Each product subcommand accepts --aoi, --date-range, and --out parameters | Typer Option/Argument pattern; D-08/D-09/D-12 define exact flag design |
</phase_requirements>

## Standard Stack

### Core (already in project dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rasterio | >=1.3 | Read S2 L2A bands, write COG output, reproject for validation | Already used in all pipeline modules |
| numpy | >=1.26 | Band math for DSWE spectral indices | Already used everywhere |
| scipy | >=1.12 | Not directly needed for DSWx but available | Already a dependency |
| rioxarray | 0.22.0 | Multi-band S2 COG I/O with CRS awareness | Already in stack recommendations |
| rio-cogeo | 7.0.2 | COG conversion for DSWx output | Already used in rtc.py ensure_cog() |
| jinja2 | >=3.1 | HTML report template rendering | Available (transitive dependency, version 3.1.6 confirmed) |
| matplotlib | >=3.9 | Validation report figures (diff maps, scatter plots) | In [viz] optional deps; needed for reports |
| typer | >=0.12 | CLI subcommand framework | Already used in cli.py (version 0.24.1 confirmed) |
| loguru | >=0.7 | Structured logging with stage-level messages | Already used in all modules |

### New Dependencies Needed
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scikit-image | >=0.22 | SSIM for DSWx spatial validation (already in [validation] extras) | Already available via metrics.py lazy import |

### No New Dependencies Required
All libraries needed for Phase 4 are already declared in `pyproject.toml` (core deps or optional extras). Jinja2 is a transitive dependency already installed. Matplotlib needs to be available at runtime for report generation -- it is in the `[viz]` optional extras group.

**Note:** `matplotlib` and `jinja2` should be added to core dependencies (or a new `[reports]` group) since VAL-06 makes them required, not optional. Currently matplotlib is only in `[viz]`. Decision for planner: either add to core deps or create `[reports]` extra.

## Architecture Patterns

### Recommended Project Structure (new/modified files)
```
src/subsideo/
├── cli.py                    # MODIFIED: add rtc, cslc, disp, dswx, dist, validate subcommands
├── products/
│   ├── types.py              # MODIFIED: add DSWxConfig, DSWxResult, DSWxValidationResult
│   └── dswx.py               # NEW: DSWx-S2 pipeline (run_dswx, run_dswx_from_aoi)
├── validation/
│   ├── compare_dswx.py       # NEW: JRC comparison + tile download
│   ├── metrics.py            # MODIFIED: add f1_score, precision, recall, overall_accuracy
│   ├── report.py             # NEW: HTML/Markdown report generation
│   └── templates/            # NEW: Jinja2 HTML templates
│       └── report.html       # NEW: base report template
└── _metadata.py              # NEW: shared OPERA metadata injection utility
```

### Pattern 1: DSWx Pipeline (following rtc.py pattern)
**What:** Thin-wrapper orchestrator with lazy imports
**When to use:** For `products/dswx.py`
**Example:**
```python
# Source: existing rtc.py / disp.py patterns in codebase
def run_dswx(
    s2_band_paths: dict[str, Path],  # {"B02": ..., "B03": ..., "B04": ..., "B08": ..., "B11": ..., "B12": ...}
    scl_path: Path,
    output_dir: Path,
    output_epsg: int | None = None,
) -> DSWxResult:
    """Run DSWE classification on Sentinel-2 L2A bands."""
    import rasterio
    # ... compute indices, apply thresholds, classify, write COG
```

### Pattern 2: CLI Subcommand (following check-env pattern)
**What:** Typer command that calls `run_{product}_from_aoi()`
**When to use:** For each product subcommand in cli.py
**Example:**
```python
@app.command("dswx")
def dswx_cmd(
    aoi: Path = typer.Option(..., "--aoi", help="GeoJSON file (Polygon/MultiPolygon)"),
    start: str = typer.Option(..., "--start", help="Start date (YYYY-MM-DD)"),
    end: str = typer.Option(..., "--end", help="End date (YYYY-MM-DD)"),
    out: Path = typer.Option(Path("."), "--out", help="Output directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    from subsideo.products.dswx import run_dswx_from_aoi
    from subsideo.utils.logging import configure_logging
    configure_logging(verbose=verbose)
    result = run_dswx_from_aoi(aoi=aoi, date_range=(start, end), output_dir=out / "dswx")
    # ... report result
```

### Pattern 3: Validation Report Generation
**What:** Consumes ValidationResult dataclasses, generates HTML + Markdown with embedded figures
**When to use:** For `validation/report.py`
**Example:**
```python
def generate_report(
    product_type: str,
    validation_result: RTCValidationResult | DISPValidationResult | DSWxValidationResult,
    product_array: np.ndarray,
    reference_array: np.ndarray,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Generate HTML and Markdown validation reports."""
    # 1. Generate matplotlib figures (diff map + scatter plot)
    # 2. Render Jinja2 HTML template with inline SVG
    # 3. Write Markdown with PNG figure references
    # Returns (html_path, md_path)
```

### Pattern 4: OPERA Metadata Injection (OUT-03)
**What:** Shared utility to write OPERA-compliant identification metadata to any product
**When to use:** Called at the end of every product pipeline (RTC, CSLC, DISP, DIST, DSWx)
**Example:**
```python
def inject_opera_metadata(
    product_path: Path,
    product_type: str,
    software_version: str,
    run_params: dict,
) -> None:
    """Write OPERA-compliant identification metadata to product file."""
    # For GeoTIFF: use rasterio update mode to write tags
    # For HDF5: use h5py to write attributes to /identification group
```

### Anti-Patterns to Avoid
- **Do not use Google Earth Engine for JRC data:** Direct HTTP download from JRC FTP is simpler and has no auth dependency.
- **Do not hardcode DSWE thresholds in multiple places:** Define them as a dataclass or named constants in one module.
- **Do not make matplotlib/jinja2 a top-level import:** Use lazy import pattern consistent with the rest of the codebase.
- **Do not create a monolithic CLI function:** Each subcommand should be a separate function calling the corresponding `run_{product}_from_aoi()`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| COG creation | Custom GDAL/rasterio tiling code | `rio_cogeo.cog_translate()` | Already proven in rtc.py; handles overviews, compression, block size |
| F1/precision/recall | Custom set-operation metrics | sklearn-style implementation or numpy-based | Simple to implement but edge cases (all-zero arrays, NaN handling) need care |
| HTML templating | String concatenation for HTML | Jinja2 `Environment` + `FileSystemLoader` | XSS-safe, maintainable, separates content from presentation |
| SVG figure embedding | Manual SVG string building | matplotlib `fig.savefig(buf, format='svg')` to BytesIO | Standard matplotlib pattern for inline SVG |
| GeoTIFF metadata tags | Custom binary header manipulation | `rasterio.open(path, 'r+')` + `ds.update_tags()` | Standard rasterio API for TIFF tag writing |

## Common Pitfalls

### Pitfall 1: S2 L2A Reflectance Scaling
**What goes wrong:** Sentinel-2 L2A surface reflectance values are stored as uint16 with a scale factor of 10000 (i.e., 1000 = 0.1 reflectance). The PROTEUS DSWE thresholds for `pswt_1_nir`, `pswt_1_swir1`, etc. are in scaled integer units (e.g., 1500 = 0.15 reflectance), but the index thresholds (MNDWI > 0.124) assume normalized ratios.
**Why it happens:** Confusion between raw DN values and physical reflectance.
**How to avoid:** Read S2 L2A bands as uint16, keep in scaled integer form for the absolute band thresholds (Test 4, Test 5). Compute MNDWI/NDVI as ratios which are scale-invariant. Document the convention.
**Warning signs:** All pixels classified as water, or no pixels classified as water.

### Pitfall 2: S2 L2A Band Resolution Mismatch
**What goes wrong:** S2 bands have different native resolutions: B02/B03/B04/B08 are 10m, B11/B12 are 20m. Computing indices across resolutions without resampling produces misaligned arrays.
**Why it happens:** Reading bands at native resolution without upsampling SWIR to 10m first.
**How to avoid:** Either (a) read all bands at 20m resolution (simpler, since output is 30m anyway), or (b) upsample B11/B12 to 10m before computation. Since D-03 mandates 30m output, read everything at 20m then reproject/resample to 30m UTM during output. Use `rasterio.warp.reproject()` with `Resampling.bilinear`.
**Warning signs:** Array shape mismatches, numpy broadcasting errors.

### Pitfall 3: SCL Cloud Mask Band Alignment
**What goes wrong:** The SCL (Scene Classification Layer) is at 20m resolution. If processing bands at 10m, SCL must be upsampled. If processing at 20m, alignment is direct.
**Why it happens:** Resolution mismatch between SCL and reflectance bands.
**How to avoid:** Process everything at 20m resolution internally, then resample output to 30m. SCL is uint8 categorical -- use `Resampling.nearest` (not bilinear) for categorical data.
**Warning signs:** Cloud-free water pixels being masked, or clouds not masked.

### Pitfall 4: JRC Monthly History Tile Coordinate System
**What goes wrong:** JRC tiles use a grid-based naming convention with 40000-unit increments (pixel coordinates), not geographic coordinates. Mapping an AOI bounding box to tile filenames requires understanding the JRC tile grid.
**Why it happens:** Non-obvious tile naming scheme (e.g., `0000080000-0000120000.tif`).
**How to avoid:** Calculate tile indices from geographic coordinates using the known grid parameters: the dataset covers the globe at 30m resolution, 10-degree tiles are 40000 pixels wide/tall at the equator. Build a helper function that maps (lon, lat) to the tile filename.
**Warning signs:** 404 errors when fetching tiles, wrong geographic area in validation.

### Pitfall 5: JRC Monthly History Water Value Encoding
**What goes wrong:** JRC Monthly History uses specific pixel values: 0 = no data, 1 = not water, 2 = water. Binary comparison against DSWx must map correctly: DSWx classes 1-2 (high/moderate confidence water) should map to "water", JRC value 2 maps to "water".
**Why it happens:** Assuming standard 0/1 binary encoding.
**How to avoid:** Explicitly document and verify the JRC encoding. Filter to valid pixels (value > 0), then compare: DSWx water (classes 1-2) vs JRC water (value 2).
**Warning signs:** F1 scores near 0 or near 1 with suspiciously low recall.

### Pitfall 6: Matplotlib Backend in Headless Environments
**What goes wrong:** `import matplotlib.pyplot` fails or hangs if no display is available (CI, SSH sessions).
**Why it happens:** Default matplotlib backend tries to open a GUI window.
**How to avoid:** Set `matplotlib.use('Agg')` before importing pyplot, or use the `MPLBACKEND=Agg` environment variable. Do this inside the lazy import block.
**Warning signs:** `RuntimeError: no display` or process hangs on figure creation.

## Code Examples

### DSWE Spectral Index Computation (from PROTEUS source, Apache 2.0)

The five diagnostic tests, translated from PROTEUS `dswx_hls.py` to Sentinel-2 L2A bands:

```python
# Source: https://github.com/nasa/PROTEUS/blob/main/src/proteus/dswx_hls.py

# Sentinel-2 L2A band mapping:
#   Blue  = B02 (10m)    -> HLS Blue
#   Green = B03 (10m)    -> HLS Green
#   Red   = B04 (10m)    -> HLS Red
#   NIR   = B08 (10m) or B8A (20m) -> HLS NIR
#   SWIR1 = B11 (20m)    -> HLS SWIR1
#   SWIR2 = B12 (20m)    -> HLS SWIR2

# Index formulas (scale-invariant ratios):
# MNDWI = (green - swir1) / (green + swir1)
# NDVI  = (nir - red) / (nir + red)

# Composite formulas (use raw scaled reflectance):
# MBSRV = green + red
# MBSRN = nir + swir1
# AWESH = blue + 2.5 * green - 1.5 * (nir + swir1) - 0.25 * swir2

# Default PROTEUS thresholds:
WIGT = 0.124           # MNDWI threshold for Test 1
AWGT = 0.0             # AWESH threshold for Test 3
PSWT1_MNDWI = -0.44    # Partial surface water Test 4
PSWT1_NIR = 1500       # Scaled reflectance (0.15)
PSWT1_SWIR1 = 900      # Scaled reflectance (0.09)
PSWT1_NDVI = 0.7
PSWT2_MNDWI = -0.5     # Partial surface water Test 5
PSWT2_BLUE = 1000      # Scaled reflectance (0.10)
PSWT2_NIR = 2500       # Scaled reflectance (0.25)
PSWT2_SWIR1 = 3000     # Scaled reflectance (0.30)
PSWT2_SWIR2 = 1000     # Scaled reflectance (0.10)


def _compute_diagnostic_tests(
    blue: np.ndarray,
    green: np.ndarray,
    red: np.ndarray,
    nir: np.ndarray,
    swir1: np.ndarray,
    swir2: np.ndarray,
) -> np.ndarray:
    """Compute 5-bit DSWE diagnostic layer from S2 L2A bands.

    All band arrays should be in scaled integer reflectance (x10000).
    Returns uint8 array with bits 0-4 representing tests 1-5.
    """
    # Avoid division by zero
    eps = 1e-10

    mndwi = (green.astype(np.float32) - swir1) / (green + swir1 + eps)
    ndvi = (nir.astype(np.float32) - red) / (nir + red + eps)
    mbsrv = green.astype(np.float32) + red
    mbsrn = nir.astype(np.float32) + swir1
    awesh = blue.astype(np.float32) + 2.5 * green - 1.5 * mbsrn - 0.25 * swir2

    diag = np.zeros(blue.shape, dtype=np.uint8)
    diag += np.uint8(mndwi > WIGT)          # Test 1: bit 0
    diag += np.uint8(mbsrv > mbsrn) * 2     # Test 2: bit 1
    diag += np.uint8(awesh > AWGT) * 4      # Test 3: bit 2
    # Test 4 (partial surface water - conservative)
    diag += np.uint8(
        (mndwi > PSWT1_MNDWI) & (swir1 < PSWT1_SWIR1)
        & (nir < PSWT1_NIR) & (ndvi < PSWT1_NDVI)
    ) * 8                                     # bit 3
    # Test 5 (partial surface water - aggressive)
    diag += np.uint8(
        (mndwi > PSWT2_MNDWI) & (blue < PSWT2_BLUE)
        & (swir1 < PSWT2_SWIR1) & (swir2 < PSWT2_SWIR2)
        & (nir < PSWT2_NIR)
    ) * 16                                    # bit 4

    return diag
```

### Diagnostic-to-Water-Class Mapping (from PROTEUS)

```python
# Source: https://github.com/nasa/PROTEUS/blob/main/src/proteus/dswx_hls.py
# The PROTEUS codebase maps all 32 possible 5-bit diagnostic values to classes:
#   0 = Not Water
#   1 = Water - High Confidence
#   2 = Water - Moderate Confidence
#   3 = Potential Wetland
#   4 = Low Confidence Water or Wetland
#   255 = Fill / no data

# Simplified mapping (most common patterns):
INTERPRETED_WATER_CLASS = {
    0b00000: 0,   # no tests pass -> not water
    0b00001: 0,   # only MNDWI -> not water (insufficient)
    0b00010: 0,   # only MBSRV>MBSRN -> not water
    0b00011: 2,   # MNDWI + MBSRV -> moderate confidence
    0b00100: 0,   # only AWESH -> not water
    0b00101: 2,   # MNDWI + AWESH -> moderate confidence
    0b00110: 2,   # MBSRV + AWESH -> moderate confidence
    0b00111: 1,   # MNDWI + MBSRV + AWESH -> high confidence
    0b01000: 3,   # only PSW conservative -> potential wetland
    0b01111: 1,   # first 4 tests pass -> high confidence
    0b10000: 4,   # only PSW aggressive -> low confidence
    0b11111: 1,   # all tests pass -> high confidence
    # ... full 32-entry table in PROTEUS source
}
```

### JRC Monthly History Tile Download

```python
# Source: https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GSWE/MonthlyHistory/
# Tile URL pattern verified by browsing directory structure

JRC_BASE_URL = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata"
    "/GSWE/MonthlyHistory/LATEST/tiles"
)

def _jrc_tile_url(year: int, month: int, tile_x: int, tile_y: int) -> str:
    """Build JRC Monthly History tile URL.

    Tile coordinates are in 40000-pixel increments.
    Example: tile_x=2, tile_y=3 -> '0000080000-0000120000.tif'
    """
    x_str = f"{tile_x * 40000:010d}"
    y_str = f"{tile_y * 40000:010d}"
    return f"{JRC_BASE_URL}/{year}/{year}_{month:02d}/{x_str}-{y_str}.tif"

# JRC pixel values:
#   0 = no data / no observation
#   1 = not water
#   2 = water
```

### SCL Cloud Mask Application

```python
# Source: Sentinel-2 L2A SCL product specification
# SCL values to mask (D-02):
#   3 = cloud shadow
#   8 = cloud medium probability
#   9 = cloud high probability
#   10 = thin cirrus
SCL_MASK_VALUES = {3, 8, 9, 10}

def _apply_scl_mask(data: np.ndarray, scl: np.ndarray) -> np.ndarray:
    """Mask pixels where SCL indicates cloud/shadow."""
    mask = np.isin(scl, list(SCL_MASK_VALUES))
    result = data.copy()
    result[mask] = np.nan  # or nodata value
    return result
```

### Validation Report HTML Template Pattern

```python
# Jinja2 template rendering with matplotlib SVG
import io
import base64
import matplotlib
matplotlib.use('Agg')  # headless backend
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader

def _fig_to_svg(fig) -> str:
    """Convert matplotlib figure to inline SVG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='svg', bbox_inches='tight')
    plt.close(fig)
    return buf.getvalue().decode('utf-8')

def _fig_to_png_path(fig, path: Path) -> Path:
    """Save matplotlib figure as PNG for Markdown reports."""
    fig.savefig(str(path), format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    return path
```

### OPERA Metadata Injection (OUT-03)

```python
# For COG GeoTIFF products (RTC, DSWx, DIST):
import rasterio

def _inject_cog_metadata(cog_path: Path, metadata: dict) -> None:
    with rasterio.open(cog_path, 'r+') as ds:
        ds.update_tags(**{
            "OPERA_PRODUCT_TYPE": metadata["product_type"],
            "OPERA_SOFTWARE_VERSION": metadata["software_version"],
            "OPERA_PROVENANCE": metadata["provenance"],
            "OPERA_RUN_PARAMETERS": json.dumps(metadata["run_params"]),
            "OPERA_PROCESSING_DATETIME": metadata["processing_datetime"],
        })

# For HDF5 products (CSLC, DISP):
import h5py

def _inject_hdf5_metadata(h5_path: Path, metadata: dict) -> None:
    with h5py.File(h5_path, 'a') as f:
        grp = f.require_group("/identification")
        for key, value in metadata.items():
            grp.attrs[key] = value
```

## Sentinel-2 L2A to HLS Band Mapping

| DSWE Band | HLS Band | S2 L2A Band | Wavelength (nm) | Native Resolution | Notes |
|-----------|----------|-------------|-----------------|-------------------|-------|
| Blue | B02 | B02 | 490 | 10m | Direct equivalent |
| Green | B03 | B03 | 560 | 10m | Direct equivalent |
| Red | B04 | B04 | 665 | 10m | Direct equivalent |
| NIR | B05 (Landsat) / B8A (HLS-S30) | B8A | 865 | 20m | Use B8A (narrow NIR) for DSWE, not B08 (wide NIR); B8A is the HLS-S30 harmonized NIR band |
| SWIR1 | B06 (Landsat) / B11 (HLS-S30) | B11 | 1610 | 20m | Direct equivalent |
| SWIR2 | B07 (Landsat) / B12 (HLS-S30) | B12 | 2190 | 20m | Direct equivalent |

**Critical note on NIR band:** HLS uses B8A (narrow NIR, 865nm, 20m) not B08 (wide NIR, 842nm, 10m) for the DSWE computation. B8A matches Landsat NIR more closely. Using B08 instead would shift NDVI and AWESH values.

## DSWE Water Classification Values

| Value | Label | Description | Diagnostic Bit Pattern |
|-------|-------|-------------|----------------------|
| 0 | Not Water | Insufficient evidence for water | 0 or 1 tests pass |
| 1 | Water - High Confidence | Strong evidence of open water | 3+ core tests pass |
| 2 | Water - Moderate Confidence | Moderate evidence | 2 core tests pass |
| 3 | Potential Wetland | Partial surface water, conservative | Test 4 passes |
| 4 | Low Confidence Water/Wetland | Partial surface water, aggressive | Test 5 passes |
| 255 | Fill/No Data | Cloud, shadow, or invalid | Masked by SCL |

## JRC Global Surface Water Access

| Property | Value |
|----------|-------|
| Base URL | `https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GSWE/MonthlyHistory/LATEST/tiles/` |
| Directory structure | `{year}/{year}_{month:02d}/{tile_x:010d}-{tile_y:010d}.tif` |
| Tile size | 40000 x 40000 pixels (10-degree at 30m equatorial) |
| Resolution | 30m |
| Pixel values | 0=nodata, 1=not water, 2=water |
| Coverage | March 1984 to December 2021 (454 months) |
| Format | GeoTIFF |
| Auth required | None (public HTTP) |
| Alternative access | Google Earth Engine (`JRC/GSW1_4/MonthlyHistory`) -- NOT used per D-06 |

**Limitation:** Monthly History ends at December 2021 (data version 1.4). For validation of DSWx products processed from 2022+ imagery, the closest available JRC month should be used with a note about temporal mismatch. The `Aggregated/` layer (occurrence/recurrence) could be a fallback for newer dates.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Google Earth Engine for JRC access | Direct HTTP from JRC FTP | Always available | No GEE auth dependency |
| DSWE v1 (MNDWI-only) | DSWE v2 (5 diagnostic tests) | PROTEUS/OPERA 2023 | Better partial water detection in wetlands |
| Manual HTML reports | Jinja2 templated reports | Standard practice | Maintainable, consistent styling |
| Separate metadata files | In-product metadata tags | OPERA spec requirement | Self-describing products |

## Project Constraints (from CLAUDE.md)

- **ruff** with line-length 100, target Python 3.10
- **isort** via ruff with `known-first-party = ["subsideo"]`
- **mypy** strict mode (ignore_missing_imports=true for GDAL/ISCE3)
- **Hatchling** build backend, src layout
- **pytest** with `--cov=subsideo --cov-report=term-missing` and 80% coverage minimum
- **Never pip install** isce3, gdal, dolphin, tophu, snaphu -- conda-forge only
- **Lazy imports** for conda-forge-only deps inside function bodies
- **Dataclasses** (not Pydantic) for result types
- **loguru** for logging
- **CDSE credentials** via env vars / `.env` -- never commit credentials
- Test markers: `@pytest.mark.integration`, `@pytest.mark.validation`, `@pytest.mark.slow`

## Open Questions

1. **Full 32-entry DSWE interpretation table**
   - What we know: PROTEUS source has the complete mapping of all 32 possible 5-bit diagnostic values to water classes 0-4.
   - What's unclear: The exact mapping for all 32 entries was not fully extracted (only the most common patterns shown above).
   - Recommendation: During implementation, reference the PROTEUS source directly at `github.com/nasa/PROTEUS` to copy the full `interpreted_dswx_band_dict`. It is Apache 2.0 licensed.

2. **JRC tile coordinate mapping**
   - What we know: Tiles use 40000-pixel-increment naming. The geographic extent per tile is ~10 degrees at 30m.
   - What's unclear: Exact relationship between tile indices and geographic coordinates (origin point, whether tiles cover full globe).
   - Recommendation: During implementation, download one known EU tile (e.g., covering Netherlands) and verify the geographic extent matches expectations before building the general mapping function.

3. **matplotlib/jinja2 dependency placement**
   - What we know: Both are needed for report generation (VAL-06). Jinja2 is already transitively installed. Matplotlib is in `[viz]` extras only.
   - What's unclear: Whether to add matplotlib to core deps or create a `[reports]` extra.
   - Recommendation: Add both to a new `[reports]` optional group and make the report module import them lazily. The validate CLI subcommand should check availability and provide a helpful error if missing.

## Sources

### Primary (HIGH confidence)
- [NASA PROTEUS repository](https://github.com/nasa/PROTEUS) - DSWE algorithm source code (dswx_hls.py), default thresholds (dswx_hls.yaml), Apache 2.0 license
- [JRC FTP data server](https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GSWE/) - Monthly History directory structure and tile naming verified by crawling
- Existing codebase: rtc.py, disp.py, dist.py, compare_rtc.py, compare_disp.py, metrics.py, types.py, cli.py -- all patterns directly inspected

### Secondary (MEDIUM confidence)
- [USGS DSWE product page](https://www.usgs.gov/landsat-missions/landsat-collection-2-level-3-dynamic-surface-water-extent-science-product) - Classification values and test descriptions
- [JRC Global Surface Water download portal](https://global-surface-water.appspot.com/download) - Tile size and download options
- [JRC Monthly Water History GEE catalog](https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_MonthlyHistory) - Pixel value encoding (0/1/2) and temporal coverage
- [Sentinel-2 band specifications](https://clearsky.vision/knowledge/sentinel2-spectral-bands) - Band wavelengths and resolutions
- [MNDWI Sentinel-2 formula](https://docs.geopera.com/en/docs/spectral-indices/sentinel-2/mndwi) - Band mapping for MNDWI computation

### Tertiary (LOW confidence)
- JRC tile coordinate-to-geographic mapping -- inferred from directory structure, needs implementation-time verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in project dependencies, versions confirmed
- Architecture: HIGH - all patterns directly observed in existing codebase (Phases 1-3)
- DSWE algorithm: HIGH - sourced from PROTEUS official implementation with default thresholds
- JRC access: MEDIUM - directory structure verified but tile coordinate mapping needs implementation validation
- Pitfalls: HIGH - based on known S2 L2A characteristics and observed patterns in similar workflows

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable domain, algorithms not changing)
