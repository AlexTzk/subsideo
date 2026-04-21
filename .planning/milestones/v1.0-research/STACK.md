# Stack Research

**Domain:** SAR/InSAR geospatial processing library (Python, EU AOI, OPERA-spec products)
**Researched:** 2026-04-05
**Confidence:** HIGH (versions verified against PyPI/GitHub releases; conda-forge packages cross-checked)

---

## Recommended Stack

### Core Algorithm Layer (conda-forge only — never pip install these)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| isce3 | 0.25.10 | SAR processing engine: RTC backscatter, CSLC burst coregistration, geocoding, orbit/DEM interpolation | NASA/JPL reference implementation; the only production-grade Python SAR framework with NISAR/Sentinel-1 burst support; OPERA itself uses it |
| compass | 0.5.6 | CSLC-S1 burst workflow (COregistered Multi-temPorAl SAR SLC) | OPERA-ADT's official CSLC-S1 workflow; wraps isce3 burst processing; conda-forge available |
| opera-rtc | v1.0.4 (R5.3) | RTC-S1 backscatter workflow | OPERA-ADT's official RTC-S1 workflow; wraps isce3 RTC; provides 30m UTM COG output matching OPERA spec |
| dolphin | 0.42.5 | InSAR PS/DS phase linking for DISP-S1 | OPERA-ADT/isce-framework reference implementation; published JOSS 2024; handles large-scale covariance estimation and MLE phase linking |
| tophu | 0.2.1 | Multi-scale tile-based 2-D phase unwrapping | Designed specifically for OPERA DISP-S1 large interferograms; parallelises SNAPHU over tiles at multiple resolutions |
| snaphu (snaphu-py) | 0.4.1 | Statistical-cost network-flow phase unwrapping binary | Industry standard for InSAR unwrapping; non-commercial research license; conda-forge; snaphu-py is the isce-framework's thin Python wrapper |
| dist-s1 | conda-forge | Surface disturbance delineation from RTC-S1 time series | OPERA-ADT official DIST-S1 workflow; conda-forge distributed |
| GDAL | >=3.8 | Raster/vector I/O, projection, format conversion | Required by rasterio, isce3, dolphin; conda-forge build links system GDAL cleanly; do not use pip wheel (binary incompatibility) |

### Data Access Layer (pip-installable)

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| pystac-client | 0.9.0 | CDSE STAC API search (STAC spec 1.1.0) | CDSE launched new STAC catalogue Feb 2025 using STAC 1.1.0; pystac-client is the canonical client; supports CQL2 filter extension for S1 burst/polygon queries |
| boto3 | >=1.34 | CDSE S3 (`s3://eodata/`) access with custom endpoint | CDSE S3 uses custom endpoint and S3-compatible keys; boto3 with `endpoint_url` override is the standard approach; the new CDSE STAC uses S3 paths as canonical data references |
| asf-search | 12.0.6 | ASF DAAC search and download for OPERA N.Am. validation products | Official NASA/ASF Python wrapper for their Search API; supports OPERA product type filtering; required for fetching reference RTC/CSLC/DISP products for validation |
| earthaccess | 0.17.0 | NASA Earthdata auth and bulk download | Handles Earthdata Login token lifecycle; recommended alongside asf-search for authenticated HTTPS streaming |

### Orbit and Auxiliary Data (pip-installable)

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| sentineleof | 0.11.1 | Sentinel-1 POE/RESORB orbit file download | Maintained by the isce-framework team (same org as isce3/dolphin); downloads from ESA Copernicus POD service with POEORB→RESORB fallback; conda-forge available |
| s1-orbits | 0.2.0 | Alternative orbit download from AWS Open Data | ASF HyP3 team's package; fetches from the Sentinel-1 Precise Orbit Determination Registry of Open Data on AWS — faster than ESA POD hub; best-available logic (POEORB first, RESORB fallback) |
| pyaps3 | 0.3.6 | ERA5 tropospheric delay correction (MintPy dependency) | Required by MintPy for `correct_troposphere`; updated Feb 2025 for the new CDS API (old cdsapirc format breaks 0.3.5); key integration point for DISP pipeline |
| cdsapi | >=0.7 | ECMWF CDS API client for ERA5 download | Required by pyaps3; credentials in `~/.cdsapirc`; updated 2025 CDS requires new token format |

### DEM Management (pip-installable)

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| dem-stitcher | 2.5.13 | GLO-30 Copernicus DEM tile download and stitching | Purpose-built for this use case; supports `dem_name='glo_30'`; performs WGS84 ellipsoidal height conversion and pixel-centre/pixel-corner CRS normalisation automatically; used by OPERA RTC and dolphin internally |

### Burst Database (pip-installable)

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| opera-utils | 0.25.6 | OPERA burst/frame DB utilities, HDF5 helpers, product I/O | opera-adt reference toolkit; `get_burst_id()`, `get_frame_to_burst_mapping()`, OPERA HDF5 product readers; pip-installable; the EU burst DB extension must augment (not replace) this package's `burst_db` SQLite schema |
| s1-reader | 0.2.5 | Sentinel-1 SAFE/zip burst parsing into ISCE3-compatible objects | opera-adt/isce-framework canonical SLC reader; reads burst metadata, swath geometry, calibration LUTs from S1 SAFE zips; conda-forge (`s1reader`) |

### Raster I/O and Array Processing (conda-forge preferred; pip fallback OK)

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| rasterio | 1.5.0 | COG GeoTIFF read/write, windowed I/O, reprojection | Standard raster I/O in scientific Python; 1.5.0 is the first major-version bump in years — includes internal COG writing without `rio-cogeo` for simple cases |
| rioxarray | 0.22.0 | xarray extension: CRS-aware raster arrays, COG export | Bridges rasterio and xarray; essential for reprojection and clip-to-AOI operations; the standard way to handle multi-band COG stacks in xarray workflows |
| rio-cogeo | 7.0.2 | Cloud-Optimized GeoTIFF creation and validation plugin | Best-in-class COG writer with overview control, block-size tuning, and STAC-compatible metadata injection; use when rasterio's built-in COG mode is insufficient |
| xarray | >=2024.11 | N-dimensional labelled arrays, HDF5/NetCDF I/O | Core array model for multi-temporal stacks; used throughout dolphin and MintPy; use `engine='h5netcdf'` for OPERA HDF5 files |
| h5py | >=3.10 | Low-level HDF5 read/write | Required for direct OPERA CSLC/DISP HDF5 product writing and reading; use alongside xarray for structured access |
| numpy | >=1.26 | Numerical arrays | Baseline; pinned by isce3/dolphin |
| scipy | >=1.13 | Signal processing, interpolation, statistics | Used by tophu (remez filter), MintPy, and validation metrics |

### Vector and Geometry (conda-forge preferred)

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| shapely | >=2.0 | Geometry objects and operations | shapely 2.0 dropped GEOS direct binding in favour of vectorised C extension — 10–100x faster for AOI/burst intersection; geopandas 1.0 requires shapely>=2 |
| geopandas | >=1.0 | GeoDataFrame: spatial joins, AOI clipping, burst footprint DB | Standard for vector operations; 1.0 defaults to pyogrio (GDAL-backed) instead of Fiona; required for EU burst footprint SQLite generation |
| pyproj | 3.7.2 | CRS transformations, UTM zone determination | Required by rasterio/geopandas; 3.7.x adds PROJ 9.4 bindings; critical for EU multi-zone UTM (28N–38N) handling |

### Time-Series Inversion (conda-forge for MintPy; pip for PyAPS3)

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| MintPy | 1.6.3 | InSAR time-series inversion, velocity estimation, tropospheric correction | insarlab/JPL reference implementation; production-proven for Sentinel-1 SBAS; built-in ERA5 correction via PyAPS3; HDF5-based time-series format compatible with OPERA DISP-S1 spec |

### Configuration and CLI

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| typer | 0.24.1 | CLI framework (subcommands: rtc, cslc, disp, dswx, validate) | FastAPI author; type-hint driven; 0.24 requires Python>=3.10 (matches project target); rich integration for progress bars and panels |
| pydantic-settings | 2.13.1 | Settings management: env vars + .env + YAML per-run config | Pydantic V2-based; handles layered config (env → .env → YAML → defaults); `CliSettingsSource` enables `--option` overrides on top of file config |
| pydantic | >=2.7 | Data validation for config models and product metadata | V2 required by pydantic-settings 2.x; Rust-backed core for fast validation |
| python-dotenv | >=1.0 | .env file loading for CDSE/Earthdata credentials | pydantic-settings uses dotenv internally; pin separately for standalone credential loading |

### Logging

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| loguru | 0.7.3 | Structured logging | Zero-config, thread-safe, JSON-serialisable (`serialize=True`); no handler setup boilerplate; well-suited for scientific pipeline stages where log interception per-phase is useful |

### Reporting and Validation Metrics

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| scikit-image | >=0.24 | SSIM computation for DSWx/RTC spatial validation | `skimage.metrics.structural_similarity` is the standard SSIM implementation; faster than custom implementations |
| matplotlib | >=3.9 | Validation report figures (difference maps, scatter plots) | Standard; use `constrained_layout=True` for publication-quality panels |
| jinja2 | >=3.1 | HTML report generation | Template-based HTML report generation; pairs with matplotlib SVG output |
| EGMStoolkit | 0.2.15 | EGMS product download and format conversion for validation | Published 2024 paper (Springer Earth Science Informatics); the only maintained Python toolkit for EGMS data access; covers all three EGMS product levels |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| hatchling | Build backend | Lightweight, pure-Python; recommended by Scientific Python Development Guide; VCS versioning via `hatch-vcs` |
| hatch-vcs | VCS-driven version from git tags | Use with hatchling; avoids hard-coded version strings |
| pytest >=8.0 | Test runner | Standard; use `pytest-xdist` for parallel test execution across pipeline stages |
| pytest-cov 7.1.0 | Coverage measurement | Pairs with pytest; configure in `pyproject.toml` |
| ruff | Linter + formatter | Replaces flake8 + isort + black; single tool, fast; use for CI |
| mypy | Static type checking | Run in `strict` mode for config/data models; relaxed for array-heavy code |
| pre-commit | Git hook management | Enforce ruff + mypy pre-commit; standard in isce-framework repos |
| uv | Fast dependency resolver + venv manager | Recommended as pip/venv replacement for pure-Python layers on top of conda env |
| conda / mamba | Conda-forge package manager | Required for isce3, GDAL, dolphin, tophu, snaphu; use `mamba` for speed |

---

## Installation

```bash
# 1. Create conda environment (Python 3.11, all conda-forge-only deps)
mamba create -n subsideo python=3.11 -c conda-forge
mamba activate subsideo

# 2. Core algorithm stack (conda-forge only — never pip install these)
mamba install -c conda-forge \
    isce3 \
    compass \
    s1reader \
    dolphin \
    tophu \
    snaphu \
    dist-s1 \
    gdal \
    rasterio \
    rioxarray \
    geopandas \
    shapely \
    pyproj \
    xarray \
    h5py \
    numpy \
    scipy \
    mintpy

# 3. Pure-Python pip-installable layer (install on top of the conda env)
pip install \
    opera-utils \
    dem-stitcher \
    pystac-client \
    boto3 \
    asf-search \
    earthaccess \
    sentineleof \
    "s1-orbits>=0.2.0" \
    pyaps3 \
    cdsapi \
    rio-cogeo \
    "scikit-image>=0.24" \
    EGMStoolkit \
    typer \
    "pydantic-settings>=2.13" \
    pydantic \
    python-dotenv \
    loguru \
    jinja2 \
    matplotlib

# 4. Dev dependencies
pip install -e ".[dev]"
# dev extras in pyproject.toml: pytest>=8, pytest-cov, pytest-xdist, ruff, mypy, pre-commit, hatch-vcs
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| isce3 | ISCE2 | Never for new work; ISCE2 is in maintenance mode; ISCE3 is the NISAR/OPERA baseline |
| isce3 | SNAP (ESA Sentinel Application Platform) | If you need a GUI or Java-based pipeline; not suitable for Python-native scripting |
| isce3 | GMTSAR / PyGMTSAR | If you only need traditional two-pass InSAR without burst-mode coregistration; lacks OPERA product spec compliance |
| dolphin | StaMPS | If your target uses older PS methodology (EPS/L-band); dolphin's DS processing has better performance on C-band short-baseline stacks |
| dolphin | MintPy standalone (SBAS) | If you only need SBAS velocity — dolphin + MintPy is the full OPERA DISP-S1 stack and is more accurate for urban PS |
| tophu | snaphu-py direct | For small (<500×500 km) interferograms where tiling is unnecessary; tophu adds overhead for tile stitching |
| dem-stitcher | SRTM via ASF | GLO-30 Copernicus DEM is the official OPERA DEM choice; SRTM has void-fill differences and is deprecated in OPERA spec |
| pystac-client + boto3 | sentinelsat | sentinelsat uses the older OData API; CDSE has deprecated the old API in favour of STAC + S3; pystac-client is the 2025 standard |
| sentineleof | s1-orbits | Use s1-orbits when operating in AWS (fetches from Registry of Open Data, faster); use sentineleof when operating on-prem/EU (fetches directly from ESA POD hub) |
| asf-search + earthaccess | manual HTTPS download | asf-search handles OPERA-specific product type filtering and resumable downloads; manual download doesn't scale for validation batches |
| MintPy | PyRate | PyRate only supports GAMMA/ROI_PAC input format; MintPy natively supports OPERA CSLC HDF5 and dolphin outputs |
| pydantic-settings | dynaconf / hydra | pydantic-settings 2.x handles env + .env + YAML with the same Pydantic V2 validation as data models; dynaconf/hydra add complexity without benefit for this use case |
| ruff | flake8 + black + isort | ruff replaces all three with a single Rust-backed tool; 10–100x faster in CI; adopted by isce-framework repos |
| hatchling | setuptools | Scientific Python guide recommends hatchling for new projects; setuptools' setup.py pattern is legacy; hatchling + hatch-vcs gives clean VCS versioning |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pip install isce3` | No PyPI package exists; attempting pip install fetches an unrelated stub or fails silently | `mamba install -c conda-forge isce3` |
| `pip install gdal` | The PyPI GDAL wheel frequently has version mismatches with system or conda GDAL; causes subtle rasterio/isce3 import failures | `mamba install -c conda-forge gdal` |
| sentinelsat | Uses the legacy Copernicus Open Access Hub (now SciHub) OData API which CDSE is retiring; incomplete EU archive | pystac-client + boto3 against CDSE STAC/S3 |
| SNAP (ESA) | Java-based GUI tool; no scriptable Python API suitable for batch pipeline integration; GPF graph XML workflow is not version-controlled cleanly | isce3 + compass/opera-rtc |
| PyRate | Only reads GAMMA/ROI_PAC inputs; not compatible with OPERA CSLC HDF5 or dolphin outputs | MintPy (reads OPERA HDF5 natively) |
| pyAPS (pre-0.3.6) | The old CDS (cdsapirc v1) credentials format stopped working Feb 2025; pyAPS 0.3.5 and earlier will silently fail ERA5 downloads | pyaps3 >=0.3.6 |
| opera-burstdb (N.Am. only) | opera-adt/burst_db SQLite only covers North America burst footprints; EU bursts not present | opera-utils + custom EU burst DB from ESA burst ID GeoJSON (CC-BY 4.0) |
| ISCE2 | Predecessor to isce3; different Python API; no burst-mode geocoded SLC support; OPERA is fully migrated to isce3 | isce3 |
| fiona | geopandas >=1.0 defaults to pyogrio (GDAL-backed, faster); fiona adds a redundant GDAL binding and is slower for bulk vector I/O | pyogrio (installed with geopandas via conda-forge) |
| Zarr (as primary product format) | OPERA product specification mandates HDF5 (CSLC, DISP) and COG GeoTIFF (RTC, DSWx); Zarr is incompatible with the OPERA spec | h5py + rasterio/rio-cogeo per product type |
| Windows native Python (non-WSL2) | isce3 conda-forge package is Linux x86-64 and macOS arm64 only; no Windows native wheel | WSL2 on Windows; native Linux or macOS |

---

## Stack Patterns by Pipeline

**If building RTC-S1 pipeline:**
- Use `opera-rtc` (wraps isce3 RTC module) as the algorithm core
- Use `dem-stitcher` with `dem_name='glo_30'` for DEM
- Use `sentineleof` for POE/RESORB orbit files
- Output: COG GeoTIFF, 30m UTM, matching OPERA RTC-S1 product spec
- Validation: compare against OPERA N.Am. RTC via `asf-search` + `earthaccess`

**If building CSLC-S1 pipeline:**
- Use `compass` (OPERA-ADT CSLC workflow) wrapping isce3 burst coregistration
- Use `s1-reader` to parse Sentinel-1 SAFE/zip burst objects
- Use `opera-utils` for burst ID extraction and frame mapping
- Use EU burst DB (custom SQLite, augmenting opera-utils schema) for EU frame coverage
- Output: HDF5, burst-wise, 30m UTM, matching OPERA CSLC-S1 spec

**If building DISP-S1 pipeline:**
- Use `dolphin` for PS/DS phase linking (input: CSLC HDF5 stack)
- Use `tophu` for multi-scale tile-based unwrapping (calls snaphu-py internally)
- Use `MintPy` for time-series inversion and ERA5 tropospheric correction
- ERA5 requires `pyaps3 >=0.3.6` + valid `~/.cdsapirc` (new CDS format)
- Output: HDF5 displacement time series, 30m UTM

**If building DSWx-S2 pipeline:**
- Port OPERA DSWx-HLS algorithm to CDSE Sentinel-2 L2A (10m, SCL cloud mask)
- Use `pystac-client` + `boto3` to access `s3://eodata/Sentinel-2/` via CDSE
- Use `rioxarray` + `rasterio` for band-level COG I/O and reprojection
- Output: COG GeoTIFF, 30m UTM (or 10m depending on spec)

**If building the EU burst database:**
- Download ESA Sentinel-1 Burst ID GeoJSON (CC-BY 4.0) from ESA STEP platform
- Use `geopandas` + `shapely` to construct SQLite with burst footprints, UTM EPSGs, relative orbit numbers
- Schema must be compatible with `opera-utils` burst_db to reuse existing tooling
- Use `pyproj` for UTM zone assignment per burst (EU spans 28N–38N)

**If running on macOS arm64:**
- isce3 conda-forge supports arm64 as of 0.19+; all other packages have arm64 wheels
- SNAPHU binary is available on conda-forge for arm64
- Avoid `isce3-cuda` (CUDA not available on Apple Silicon)

**If running validation against EGMS:**
- Use `EGMStoolkit 0.2.15` for EGMS product download (all three EGMS product levels)
- EGMS products are CSV/GeoTIFF; use `geopandas` for spatial join to your displacement grid
- Compare line-of-sight velocity fields; account for ascending/descending geometry when converting

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| isce3 0.25.x | Python 3.10–3.11 | 3.12 not yet tested in conda-forge builds |
| dolphin 0.42.x | isce3 >=0.19, opera-utils >=0.20 | dolphin uses opera-utils for OPERA HDF5 I/O |
| compass 0.5.6 | isce3 >=0.19, s1-reader >=0.2 | CSLC workflow version must be compatible with isce3 minor version |
| MintPy 1.6.3 | pyaps3 >=0.3.6 | pyaps3 0.3.5 breaks ERA5 download with new CDS API |
| geopandas >=1.0 | shapely >=2.0, pyogrio | shapely 1.x not supported; fiona not required |
| pydantic-settings 2.13 | pydantic >=2.7 | pydantic V1 incompatible; entire settings layer requires V2 |
| rasterio 1.5.0 | GDAL >=3.8 | Rasterio 1.5 raises minimum GDAL from 3.3 to 3.8 |
| tophu 0.2.1 | snaphu-py >=0.4 | tophu calls snaphu-py as its unwrapping backend |

---

## Sources

- [isce3 Releases (GitHub)](https://github.com/isce-framework/isce3/releases) — version 0.25.10, March 2025
- [isce3 conda-forge feedstock](https://anaconda.org/conda-forge/isce3/files?version=0.19.1) — conda-forge availability confirmed
- [dolphin PyPI](https://pypi.org/project/dolphin/) — version 0.42.5, March 2026
- [dolphin JOSS paper](https://joss.theoj.org/papers/10.21105/joss.06997) — academic reference, OPERA CSLC input support
- [opera-utils PyPI](https://pypi.org/project/opera-utils/) — version 0.25.6
- [tophu Releases (GitHub)](https://github.com/isce-framework/tophu/releases) — version 0.2.1, Feb 2025
- [snaphu-py PyPI](https://pypi.org/project/snaphu/) — version 0.4.1
- [compass (OPERA-ADT)](https://github.com/opera-adt/COMPASS) — version 0.5.6, CSLC-S1 workflow
- [opera-adt/RTC](https://github.com/opera-adt/RTC) — version v1.0.4 / R5.3
- [s1-reader Releases (GitHub)](https://github.com/isce-framework/s1-reader/releases) — version 0.2.5
- [MintPy PyPI](https://pypi.org/project/mintpy/) — version 1.6.3, Nov 2025
- [pyaps3 ECMWF CDS migration (GitHub Discussion)](https://github.com/insarlab/PyAPS/discussions/40) — 0.3.6 required for new CDS API
- [sentineleof PyPI](https://pypi.org/project/sentineleof/) — version 0.11.1
- [s1-orbits PyPI](https://pypi.org/project/s1-orbits/) — version 0.2.0
- [dem-stitcher PyPI](https://pypi.org/project/dem-stitcher/) — version 2.5.13, Feb 2026
- [pystac-client PyPI](https://pypi.org/project/pystac-client/) — version 0.9.0, Jul 2025
- [CDSE STAC new catalogue announcement](https://dataspace.copernicus.eu/news/2025-2-13-release-new-cdse-stac-catalogue) — Feb 2025 STAC 1.1.0 rollout
- [CDSE STAC documentation](https://documentation.dataspace.copernicus.eu/APIs/STAC.html) — S3 as primary data path
- [asf-search PyPI](https://pypi.org/project/asf-search/) — version 12.0.6
- [earthaccess PyPI](https://pypi.org/project/earthaccess/) — version 0.17.0
- [rasterio PyPI](https://pypi.org/project/rasterio/) — version 1.5.0
- [rioxarray PyPI](https://pypi.org/project/rioxarray/) — version 0.22.0
- [rio-cogeo PyPI](https://pypi.org/project/rio-cogeo/) — version 7.0.2
- [pyproj installation docs](https://pyproj4.github.io/pyproj/stable/installation.html) — version 3.7.2
- [geopandas ecosystem docs](https://geopandas.org/en/latest/community/ecosystem.html) — 1.1 with shapely>=2, pyogrio default
- [typer PyPI](https://pypi.org/project/typer/) — version 0.24.1
- [pydantic-settings Releases](https://github.com/pydantic/pydantic-settings/releases) — version 2.13.1
- [loguru PyPI](https://pypi.org/project/loguru/) — version 0.7.3
- [EGMStoolkit (GitHub)](https://github.com/alexisInSAR/EGMStoolkit) — version 0.2.15 Beta
- [EGMS-toolkit paper (Springer)](https://link.springer.com/article/10.1007/s12145-024-01356-w) — published 2024
- [dist-s1 (opera-adt)](https://github.com/opera-adt/dist-s1) — conda-forge distributed, DIST-S1 workflow
- [Scientific Python packaging guide](https://learn.scientific-python.org/development/guides/packaging-simple/) — hatchling recommendation

---

*Stack research for: SAR/InSAR geospatial processing library (subsideo)*
*Researched: 2026-04-05*
