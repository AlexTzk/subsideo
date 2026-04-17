# subsideo

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Build Backend: Hatchling](https://img.shields.io/badge/build-hatchling-purple.svg)](https://hatch.pypa.io/)

OPERA-equivalent geospatial product pipelines for the European Union, built on
Sentinel-1/2 and the Copernicus Data Space Ecosystem.

## What is subsideo?

**subsideo** is a Python library that produces
[OPERA](https://www.jpl.nasa.gov/go/opera/)-equivalent geospatial products
(RTC-S1, CSLC-S1, DISP-S1, DSWx-S2, DIST-S1) for European Union areas of
interest. It wraps the NASA/JPL ISCE3 and dolphin algorithm stack, pulls
Sentinel-1/2 data from the Copernicus Data Space Ecosystem (CDSE), and
generates products that comply with the OPERA product specification.

The OPERA project currently produces these products only over North America.
subsideo extends that coverage to the EU by building an EU burst database from
ESA's published burst ID maps, using CDSE as the primary data source, and
providing a validation framework that compares outputs against OPERA N.Am.
reference products and the European Ground Motion Service (EGMS).

What makes it different:

- **EU coverage** via a custom burst database built from ESA's CC-BY 4.0 burst
  ID GeoJSON, extending the opera-utils schema
- **CDSE-native** data access using STAC 1.1.0 search and S3 download from the
  `s3://eodata/` bucket
- **Validation-first** approach with automated comparison against OPERA N.Am.,
  EGMS EU, and JRC Global Surface Water reference products

## Products

| Product  | Description                           | Input          | Output Format | Validation Reference     |
|----------|---------------------------------------|----------------|---------------|--------------------------|
| RTC-S1   | Radiometric terrain-corrected backscatter | Sentinel-1 SLC | COG GeoTIFF, 30m UTM | OPERA N.Am. RTC-S1   |
| CSLC-S1  | Coregistered single-look complex      | Sentinel-1 SLC | HDF5, 30m UTM        | OPERA N.Am. CSLC-S1  |
| DISP-S1  | Surface displacement time series      | CSLC-S1 stack  | HDF5, 30m UTM        | EGMS EU Ortho         |
| DSWx-S2  | Dynamic surface water extent          | Sentinel-2 L2A | COG GeoTIFF, 30m UTM | JRC Global Surface Water |
| DIST-S1  | Surface disturbance detection         | RTC-S1 time series | COG GeoTIFF, 30m UTM | --                |

## Architecture

```
src/subsideo/
  cli.py              # Typer CLI: subsideo rtc|cslc|disp|dswx|dist|validate|build-db|check-env
  config.py           # Pydantic BaseSettings (env vars + .env + YAML per-run config)
  _metadata.py        # OPERA metadata injection for GeoTIFF and HDF5 products
  data/               # All I/O: CDSE, ASF DAAC, DEM, orbits, ionosphere
    cdse.py           #   CDSEClient: OAuth2 auth, STAC search, S3 download
    dem.py            #   GLO-30 Copernicus DEM via dem-stitcher
    orbits.py         #   Sentinel-1 orbit files (sentineleof + s1-orbits fallback)
    ionosphere.py     #   IONEX TEC maps from CDDIS
    asf.py            #   ASF DAAC client for OPERA reference products (validation)
  burst/              # EU burst database (extends opera-utils for EU coverage)
    db.py             #   Build/query EU burst SQLite from ESA GeoJSON
    frames.py         #   AOI-to-burst resolution via shapely intersection
  products/           # One module per product pipeline
    rtc.py            #   RTC-S1 via opera-rtc
    cslc.py           #   CSLC-S1 via compass (ISCE3)
    disp.py           #   DISP-S1 via dolphin + tophu + MintPy
    dswx.py           #   DSWx-S2 with DSWE spectral classification
    dist.py           #   DIST-S1 via dist-s1
    types.py          #   Pipeline config/result dataclasses
  validation/         # Metrics + cross-comparison vs OPERA/EGMS/JRC
    metrics.py        #   RMSE, Pearson r, bias, SSIM, F1, precision, recall
    compare_rtc.py    #   RTC vs OPERA N.Am. (dB-domain)
    compare_cslc.py   #   CSLC vs OPERA N.Am. (interferometric phase)
    compare_disp.py   #   DISP vs EGMS Ortho (LOS-to-vertical projection)
    compare_dswx.py   #   DSWx vs JRC Global Surface Water
    report.py         #   HTML + Markdown report generator
  utils/              # I/O helpers, logging
    logging.py        #   Loguru-based structured logging
    projections.py    #   UTM zone determination via pyproj
```

**Data flow:** `data/` fetches inputs (SLC, DEM, orbits) -> `burst/` resolves
EU burst/frame geometry -> `products/` runs processing pipelines ->
`validation/` compares outputs against reference products and generates reports.

## Installation

subsideo requires a two-layer install. Heavy native dependencies (ISCE3, GDAL,
dolphin, snaphu) are only available from conda-forge. Pure-Python components
install via pip on top.

**Step 1: Create the conda environment**

```bash
mamba create -n subsideo -c conda-forge python=3.12 \
    isce3 gdal dolphin snaphu pyyaml \
    opera-utils s1reader compass mintpy dist-s1
conda activate subsideo
```

**Step 2: Install pip-only dependencies and subsideo**

```bash
# tophu (Linux only — skip on macOS; phase unwrapping will not be available)
pip install tophu

# opera-rtc (not on conda-forge or PyPI — install from GitHub)
Instructions to install RTC under a conda environment.

1. Download the source code:

```bash
git clone https://github.com/opera-adt/RTC.git RTC
```

2. Install `isce3`:

```bash
conda install -c conda-forge isce3
```

3. Install `s1-reader` via pip:
```bash
git clone https://github.com/opera-adt/s1-reader.git s1-reader
conda install -c conda-forge --file s1-reader/requirements.txt
python -m pip install ./s1-reader
```

4. Install `RTC` via pip:
```bash
git clone https://github.com/opera-adt/RTC.git RTC
python -m pip install ./RTC
```



### Usage

The command below generates the RTC product:

```bash
rtc_s1.py <path to rtc yaml file>
```

To compare the RTC-S1 products, use `rtc_compare.py`.

```bash
python rtc_s1.py <1st product HDF5> <2nd product HDF5>
```


# Install subsideo itself
pip install -e ".[dev]"
```

# You may also check the env with
```bash
/Users/<YOUR_USERNAME>/.local/share/mamba/envs/subsideo/bin/subsideo check-env
```

> **Note:** `tophu` requires Linux (`__linux` constraint on conda-forge). On
> macOS, install via pip (`pip install tophu`) for the pure-Python portion, but
> the SNAPHU unwrapping backend will only work on Linux.

> **Important:** Never `pip install isce3`, `pip install gdal`, `pip install
> dolphin`, or `pip install snaphu`. These packages either do not exist on PyPI
> or refer to unrelated projects. Always install them from conda-forge.

## Configuration

subsideo uses layered configuration: environment variables > `.env` file >
per-run YAML > defaults.

### Required credentials

| Variable              | Purpose                        | Registration                                  |
|-----------------------|--------------------------------|-----------------------------------------------|
| `CDSE_CLIENT_ID`      | CDSE OAuth2 client ID          | https://dataspace.copernicus.eu (free)        |
| `CDSE_CLIENT_SECRET`  | CDSE OAuth2 client secret      | Same as above                                 |
| `EARTHDATA_USERNAME`  | NASA Earthdata login           | https://urs.earthdata.nasa.gov (free)         |
| `EARTHDATA_PASSWORD`  | NASA Earthdata password        | Same as above                                 |

### Optional credentials

| Variable / File    | Purpose                                      |
|--------------------|----------------------------------------------|
| `~/.cdsapirc`     | ECMWF CDS API key for ERA5 tropospheric correction (DISP pipeline) |

### Configuration methods

Create a `.env` file in your working directory:

```env
CDSE_CLIENT_ID=your-client-id
CDSE_CLIENT_SECRET=your-client-secret
EARTHDATA_USERNAME=your-username
EARTHDATA_PASSWORD=your-password
```

Or provide a per-run YAML config:

```yaml
cache_dir: /data/subsideo/cache
work_dir: /data/subsideo/work
cdse_client_id: your-client-id
cdse_client_secret: your-client-secret
```

Verify your credentials are configured correctly:

```bash
subsideo check-env
```

## Quick Start

**1. Build the EU burst database** (one-time setup)

Download the ESA Sentinel-1 burst ID GeoJSON from the
[ESA STEP platform](https://step.esa.int/) and build the SQLite database:

```bash
subsideo build-db /path/to/esa_burst_ids.geojson
```

This creates `~/.subsideo/eu_burst_db.sqlite` with burst footprints, UTM EPSG
codes, and relative orbit numbers for all EU bursts.

**2. Produce RTC-S1 backscatter for an area of interest**

```bash
subsideo rtc \
    --aoi my_aoi.geojson \
    --start 2025-01-01 \
    --end 2025-01-15 \
    --out ./output
```

**3. Validate the output against OPERA N.Am. reference products**

```bash
subsideo validate \
    --product-dir ./output/rtc \
    --product-type rtc \
    --out ./reports
```

If Earthdata credentials are configured, the validation command will
automatically download the matching OPERA reference product from ASF DAAC.

## CLI Reference

All commands accept `--verbose` / `-v` for debug-level logging.

### Product pipelines

Each product command follows the same pattern:

```
subsideo <product> --aoi <geojson> --start <YYYY-MM-DD> --end <YYYY-MM-DD> --out <dir>
```

| Command | Description |
|---------|-------------|
| `subsideo rtc`  | Produce RTC-S1 radiometric terrain-corrected backscatter |
| `subsideo cslc` | Produce CSLC-S1 coregistered single-look complex |
| `subsideo disp` | Produce DISP-S1 displacement time series |
| `subsideo dswx` | Produce DSWx-S2 dynamic surface water extent |
| `subsideo dist` | Produce DIST-S1 surface disturbance maps |

### Validation

```bash
# RTC validation (auto-fetches reference from ASF if Earthdata credentials set)
subsideo validate --product-dir ./output/rtc --product-type rtc --out ./reports

# RTC validation with explicit reference
subsideo validate --product-dir ./output/rtc --product-type rtc \
    --reference /path/to/opera_rtc.tif --out ./reports

# CSLC validation
subsideo validate --product-dir ./output/cslc --product-type cslc --out ./reports

# DISP validation against EGMS (auto-fetches if EGMStoolkit installed)
subsideo validate --product-dir ./output/disp --product-type disp --out ./reports

# DISP validation with explicit EGMS reference
subsideo validate --product-dir ./output/disp --product-type disp \
    --egms /path/to/egms_ortho.tif --out ./reports

# DSWx validation against JRC Global Surface Water
subsideo validate --product-dir ./output/dswx --product-type dswx \
    --year 2025 --month 1 --out ./reports
```

### Utilities

```bash
# Build EU burst database from ESA GeoJSON
subsideo build-db /path/to/esa_burst_ids.geojson [-o /custom/output/path.sqlite]

# Validate credentials and service connectivity
subsideo check-env [-v]
```

## Validation Framework

subsideo includes a validation framework that compares outputs against
established reference products to verify scientific accuracy.

### Reference products

| Product | Reference Source | Comparison Method |
|---------|-----------------|-------------------|
| RTC-S1  | OPERA N.Am. RTC (via ASF DAAC) | dB-domain RMSE, Pearson correlation, SSIM |
| CSLC-S1 | OPERA N.Am. CSLC (via ASF DAAC) | Interferometric phase RMS via conjugate multiplication |
| DISP-S1 | EGMS EU Ortho (via EGMStoolkit) | LOS-to-vertical projection, correlation, bias |
| DSWx-S2 | JRC Global Surface Water | Binary F1 score, precision, recall, overall accuracy |

### Pass criteria

| Metric | Product | Threshold |
|--------|---------|-----------|
| RMSE   | RTC-S1  | < 0.5 dB |
| Pearson r | RTC-S1 | > 0.99 |
| Phase RMS | CSLC-S1 | < 0.05 rad |
| Pearson r | DISP-S1 | > 0.92 |
| Bias   | DISP-S1 | < 3 mm/yr |
| F1 score | DSWx-S2 | > 0.90 |

### Report generation

Validation produces both HTML and Markdown reports with:

- Difference maps (product vs reference)
- Scatter plots (correlation visualization)
- Per-metric pass/fail status with measured values
- Product metadata and configuration summary

## Development

### Commands

```bash
# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy src/subsideo/

# Unit tests (no network, mocked I/O)
pytest tests/unit/

# Single test file
pytest tests/unit/test_burst_db.py

# Specific test
pytest tests/unit/test_cdse.py::test_search_by_aoi -v

# Integration tests (require CDSE credentials)
pytest -m integration

# Validation tests (full pipeline runs)
pytest -m validation

# Skip slow tests
pytest -m "not slow"
```

### Test markers

| Marker | Purpose |
|--------|---------|
| `@pytest.mark.integration` | Requires live CDSE credentials |
| `@pytest.mark.validation` | Full pipeline cross-comparison |
| `@pytest.mark.slow` | Real processing pipelines |

### Coverage

pytest is configured with `--cov=subsideo --cov-report=term-missing` and an
80% minimum coverage requirement.

### Code style

- **ruff** for linting and formatting (line-length 100, Python 3.10 target)
- **mypy** in strict mode (`ignore_missing_imports = true` for GDAL/ISCE3)
- **isort** via ruff with `known-first-party = ["subsideo"]`

## Technology Stack

### Algorithm layer (conda-forge only)

| Package | Purpose |
|---------|---------|
| isce3 | SAR processing engine (RTC, CSLC geocoding) |
| compass | CSLC-S1 burst coregistration workflow |
| opera-rtc | RTC-S1 backscatter workflow |
| dolphin | PS/DS phase linking for DISP-S1 |
| tophu | Multi-scale tile-based phase unwrapping |
| snaphu-py | Statistical-cost phase unwrapping binary |
| MintPy | InSAR time-series inversion and tropospheric correction |
| dist-s1 | Surface disturbance delineation from RTC time series |
| GDAL | Raster/vector I/O, projection, format conversion |

### Data access (pip-installable)

| Package | Purpose |
|---------|---------|
| pystac-client | CDSE STAC 1.1.0 search |
| boto3 | CDSE S3 download (`s3://eodata/`) |
| dem-stitcher | GLO-30 Copernicus DEM download and stitching |
| sentineleof / s1-orbits | Sentinel-1 orbit ephemeris download |
| asf-search / earthaccess | ASF DAAC access for OPERA reference products |

### I/O and processing

| Package | Purpose |
|---------|---------|
| rasterio / rio-cogeo | COG GeoTIFF read/write |
| h5py / xarray | HDF5 product I/O |
| geopandas / shapely | Vector geometry and spatial operations |
| pyproj | CRS transformations and UTM zone determination |
| numpy / scipy | Numerical computation |
| scikit-image | SSIM for validation |

### CLI and configuration

| Package | Purpose |
|---------|---------|
| typer | CLI framework with subcommands |
| pydantic-settings | Layered config (env + .env + YAML) |
| loguru | Structured logging |

## Platform Support

| Platform | Status |
|----------|--------|
| Linux x86-64 | Primary target |
| macOS arm64 (Apple Silicon) | Secondary target (isce3 supports arm64 since 0.19+) |
| Windows (WSL2) | Supported via WSL2; native Windows not supported |

## License

MIT -- see [LICENSE](LICENSE) for details.
