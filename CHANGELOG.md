# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [1.1.0] - 2026-04-28

v1.1 N.Am./EU Validation Parity & Scientific PASS milestone. Drives every
product (RTC, CSLC, DISP, DIST, DSWx) to an unambiguous PASS, FAIL-with-named-upgrade-path,
or DEFERRED-with-dated-unblock across both N.Am. and EU regions.

### Validation Results

- **RTC-S1 EU:** 3/5 bursts PASS across alpine/plain/arid/boreal/wildfire terrain regimes
- **RTC-S1 N.Am.:** DEFERRED — N.Am. eval script (run_eval.py) not migrated to v1.1 harness sidecars in this milestone (EU was the focus); unblock: v1.2 N.Am. harness migration
- **CSLC-S1 self-consistency:** 3/3 AOIs CALIBRATING (SoCal coh=0.887, Coso-Searles coh=0.804, Iberian coh=0.868); eligible for v1.2 binding (≥3 data points)
- **DISP-S1:** SoCal r=0.049 FAIL / Bologna r=0.336 FAIL (both attributed_source=inconclusive); DISP Unwrapper Selection brief scoped for v1.2
- **DIST-S1 N.Am.:** DEFERRED — operational `OPERA_L3_DIST-ALERT-S1_V1` not yet published in CMR; CMR auto-supersede probe active
- **DIST-S1 EU:** 0/3 events PASS (Aveiro/Evros/Culebra); 3 attributable causes documented; chained prior_dist_s1_product retry filed upstream
- **DSWx-S2 N.Am.:** F1=0.9252 PASS (Lake Tahoe T10SFH, July 2021)
- **DSWx-S2 EU:** F1=0.8165 FAIL — fit-set quality review (HLS→S2 L2A spectral transfer gap; EU recalibration deferred to v1.2)

### Added

- `results/matrix.md` — 10-cell validation matrix (5 products × 2 regions) with
  product-quality and reference-agreement in structurally separate columns; CALIBRATING cells
  italicised with `binds v1.2` milestone annotation; DEFERRED cells carry dated unblock conditions
- `docs/validation_methodology.md` — §6 (OPERA UTC-hour frame selection by
  `harness.select_opera_frame_by_utc_hour()`) and §7 (cross-sensor precision-first
  framing for DIST-S1 vs EFFIS); top-level TOC linking all 7 sections
- `validation/bootstrap.py` — block-bootstrap 95% CI for DIST-S1 per-event F1 (Phase 5)
- `validation/effis.py` — EFFIS REST API access + dual rasterise for DIST-S1 EU cross-validation (Phase 5)
- `products/dswx_thresholds.py` — typed DSWEThresholds frozen+slots dataclass with
  provenance metadata and EU/N.Am. region selector (Phase 6)
- Dockerfile, Apptainer.def, env.lockfile.linux-64.txt, env.lockfile.osx-arm64.txt —
  reproducibility recipe (Phase 1)

### Deferred to v1.2

- **REL-04 TrueNAS Linux audit:** Full `make eval-all` on freshly-cloned repo inside
  the homelab TrueNAS Linux dev container. Infrastructure already committed (Dockerfile,
  Apptainer.def, lockfiles). Unblock: provision TrueNAS Linux dev container and run
  `docker build -f Dockerfile .` + `make eval-all` (v1.2).
- **RTC-S1 N.Am. harness migration:** Migrate run_eval.py to validation.harness
  (bounds_for_burst + metrics.json + meta.json write) and execute N.Am. RTC re-run (v1.2).
- **DSWx-S2 EU recalibration:** HLS→S2 L2A spectral transfer gap diagnosed; dedicated
  scene-level BOA offset correction required before joint WIGT×AWGT×PSWT2_MNDWI grid
  search converges (v1.2).
- **DIST-S1 N.Am. quantitative comparison:** Awaiting operational `OPERA_L3_DIST-ALERT-S1_V1`
  publication in CMR (CMR auto-supersede probe active in run_eval_dist.py).
- **DISP-S1 unwrapper selection:** PHASS+deramping / SPURT / tophu-SNAPHU / 20×20 m
  fallback candidates scoped in DISP_UNWRAPPER_SELECTION_BRIEF.md (v1.2 milestone).

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
