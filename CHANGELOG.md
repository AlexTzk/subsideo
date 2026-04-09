# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.1.0] - 2026-04-09

Initial release. OPERA-equivalent geospatial product pipelines for European
Union areas of interest, validated against OPERA N.Am. and EGMS EU reference
products.

### Added

#### Data Access and Configuration

- CDSE STAC 1.1.0 search and S3 download for Sentinel-1 IW SLC and Sentinel-2
  L2A via `CDSEClient` with OAuth2 authentication and exponential-backoff retry
- ASF DAAC client (`ASFClient`) for OPERA N.Am. reference product search and
  download using asf-search and earthaccess
- GLO-30 Copernicus DEM download and mosaicking via dem-stitcher with automatic
  UTM reprojection at 30m posting
- Sentinel-1 orbit ephemeris download with dual-backend fallback: sentineleof
  (ESA POD hub) primary, s1-orbits (AWS Open Data) secondary
- IONEX TEC map download from CDDIS for ionospheric correction with Earthdata
  Basic auth
- Pydantic BaseSettings configuration with four-layer precedence: environment
  variables > `.env` file > per-run YAML > defaults
- ISCE3-compatible YAML config serialization via ruamel.yaml round-trip mode
- Loguru-based structured logging with configurable verbosity

#### EU Burst Database

- EU burst database builder from ESA Sentinel-1 burst ID GeoJSON (CC-BY 4.0)
  stored as SQLite with opera-utils-compatible schema
- AOI-to-burst resolution via shapely spatial intersection in
  `query_bursts_for_aoi()`
- Pre-computed UTM EPSG codes per burst via pyproj, handling Norway (zone 32V)
  and Svalbard (zones 31X/33X/35X/37X) anomalies
- `build-db` CLI command for database creation without scripting

#### Product Pipelines

- **RTC-S1:** Radiometric terrain-corrected backscatter pipeline wrapping
  opera-rtc with YAML runconfig generation, DEFLATE COG post-processing with
  5-level overviews, and UTM/posting validation
- **CSLC-S1:** Coregistered single-look complex pipeline wrapping compass
  (ISCE3) with YAML runconfig generation, HDF5 output validation checking
  `/data` group structure, and burst ID extraction from output filenames
- **DISP-S1:** Surface displacement time-series pipeline chaining dolphin
  (PS/DS phase linking), tophu (multi-scale tile-based unwrapping), and MintPy
  (time-series inversion with ERA5 tropospheric correction via pyaps3); includes
  post-unwrap planar ramp QC and CDS credential fail-fast validation
- **DSWx-S2:** Dynamic surface water extent pipeline implementing all five DSWE
  diagnostic spectral tests from NASA PROTEUS with SCL cloud masking (classes
  3, 8, 9, 10), 20m band ingestion resampled to 30m UTM COG output
- **DIST-S1:** Surface disturbance pipeline wrapping opera-adt/dist-s1 with
  AOI-to-MGRS tile resolution, RTC time-series construction, and per-tile COG
  validation

#### Validation Framework

- Validation metrics library: RMSE, Pearson correlation, bias, SSIM (with NaN
  masking), F1 score, precision, recall, overall accuracy
- RTC comparison module: dB-domain (10 log10) RMSE and correlation against OPERA
  N.Am. reference with grid alignment via rasterio reprojection
- CSLC comparison module: interferometric phase RMS via conjugate multiplication
  (angle(prod * conj(ref))) with complex HDF5 multi-path fallback
- DISP comparison module: LOS-to-vertical velocity projection, EGMS Ortho
  download via EGMStoolkit, grid-aligned correlation and bias computation
- DSWx comparison module: JRC Global Surface Water tile download, binarization,
  and F1/precision/recall/accuracy computation
- HTML validation reports with inline SVG difference maps and scatter plots via
  Jinja2 templates
- Markdown validation reports with PNG figures and metric summary tables
- Report generator supporting all product types via dataclass field introspection
- ASF DAAC auto-fetch for RTC/CSLC validation when `--reference` omitted and
  Earthdata credentials are available
- EGMS auto-fetch for DISP validation when `--egms` omitted and EGMStoolkit is
  installed

#### CLI

- Typer-based CLI with 8 subcommands: `rtc`, `cslc`, `disp`, `dswx`, `dist`,
  `validate`, `build-db`, `check-env`
- All product commands accept `--aoi`, `--start`, `--end`, `--out`, `--verbose`
- Validate command dispatches to product-specific comparison modules and
  generates HTML + Markdown reports
- `check-env` validates CDSE, Earthdata, and CDS API credentials with
  remediation hints
- GeoJSON AOI validation rejecting non-Polygon/MultiPolygon geometry types

#### Output Compliance

- OPERA metadata injection utility (`inject_opera_metadata`) for both GeoTIFF
  tags and HDF5 `/identification` attributes across all five product types
- Software version tracking via `importlib.metadata` with dev fallback for
  editable installs
- HDF5 output for CSLC and DISP products matching OPERA product specification
- COG GeoTIFF output for RTC, DSWx, and DIST products with UTM projection at
  30m posting

#### Integration Wiring

- All five `run_*_from_aoi()` functions correctly chain CDSE credential
  injection, STAC search, burst resolution, DEM fetch, orbit download, and
  pipeline execution
- Burst query ordered before DEM fetch to provide output EPSG from burst records
- Empty-burst early-exit guards in all from_aoi functions
- IONEX TEC map fetch wired into CSLC pipeline with graceful degradation on
  failure
- Lazy imports for all conda-forge-only dependencies (isce3, dolphin, tophu,
  compass, opera-rtc, dist-s1, mintpy, rio-cogeo, h5py) inside function bodies
  to support partial conda environments
