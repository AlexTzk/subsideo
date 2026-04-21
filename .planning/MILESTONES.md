# Milestones

## v1.0 Initial Release (Shipped: 2026-04-09)

**Phases completed:** 9 phases, 21 plans, 39 tasks

**Key accomplishments:**

- Pydantic-settings layered config (env > .env > YAML) with ISCE3-compatible YAML round-trip and Typer CLI check-env skeleton
- CDSEClient with OAuth2 (requests-oauthlib BackendApplicationClient), STAC 1.1.0 search for S1/S2, and S3 download with exponential-backoff retry
- Opera-utils-compatible EU burst SQLite built from ESA GeoJSON with pyproj UTM zone assignment and shapely AOI intersection query
- DEM/orbit/ionosphere/ASF download modules wrapping dem-stitcher, sentineleof, s1-orbits, and asf-search with 27 mocked unit tests
- Pipeline dataclasses (RTCConfig, CSLCConfig, RTCResult, CSLCResult, validation results) and pure-function metrics (RMSE, Pearson r, bias, SSIM) with NaN masking
- RTC-S1 pipeline orchestrator wrapping opera-rtc Python API with YAML runconfig generation, COG post-processing via rio-cogeo DEFLATE, and UTM/posting validation
- CSLC-S1 pipeline orchestrator wrapping compass Python API with YAML runconfig generation and HDF5 product validation
- RTC Comparison (`compare_rtc`):
- DISP-S1 displacement pipeline chaining dolphin phase linking, tophu unwrapping, and MintPy time-series inversion with mandatory ERA5 tropospheric correction
- DIST-S1 surface disturbance pipeline with run_dist() wrapping dist-s1 conda-forge package and run_dist_from_aoi() building RTC time series first
- 1. [Rule 1 - Bug] Fixed ruff B904 `raise from` chain
- DSWE spectral water classification pipeline with five diagnostic tests (PROTEUS thresholds), SCL cloud masking, 30m UTM COG output, and shared OPERA metadata injection utility for all product types
- JRC Monthly History comparison for DSWx water classification with HTML/Markdown validation report generation for all product types
- Typer CLI with 7 subcommands (check-env, rtc, cslc, disp, dswx, dist, validate) accepting --aoi/--start/--end/--out flags and validation report generation
- Fixed all 5 integration bugs (CDSEClient credentials, search_stac, burst query, fetch_orbit, fetch_dem) in run_rtc_from_aoi and run_cslc_from_aoi
- Wired CDSE credentials via Settings in disp/dist/dswx from_aoi functions, fixed DEM tuple unpack, and CLI dist list iteration
- Wired fetch_ionex into CSLC pipeline with try/except graceful degradation and injected OPERA metadata via get_software_version() into all five product pipelines
- ASF auto-fetch wired into validate_cmd: RTC/CSLC reference products downloaded from ASF DAAC when --reference omitted and Earthdata credentials present
- build-db CLI command, EGMS auto-fetch for DISP validation, and dead tiling.py removal
- Fixed stale ROADMAP progress table (Phase 7 now Complete), REQUIREMENTS coverage (27/27 satisfied), and added requirements-completed frontmatter to 4 SUMMARY files
- Fixed report.py _CRITERIA_MAP key mismatches (bias_lt_3mm_yr, phase_rms_lt_0.05rad), added correlation ambiguity fallback, removed 3 orphaned code items

---
