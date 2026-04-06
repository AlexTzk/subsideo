# Roadmap: subsideo

## Overview

subsideo builds a Python library that produces OPERA-equivalent SAR/InSAR geospatial products (RTC-S1, CSLC-S1, DISP-S1, DSWx-S2, DIST-S1) over EU areas of interest. The work proceeds in four coarse phases: first establishing the data access and burst database foundation that gates all algorithm work; then building and validating the SAR amplitude and coregistration pipelines (RTC + CSLC); then the complex displacement and disturbance pipelines (DISP + DIST); and finally the independent optical surface-water pipeline (DSWx) alongside the complete user-facing CLI and validation reporting layer.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation, Data Access & Burst DB** - Establish the conda environment, CDSE/ASF data access layer, EU burst database, DEM/orbit ancillaries, and project config
- [x] **Phase 2: RTC-S1 and CSLC-S1 Pipelines** - Produce and validate OPERA-spec RTC COG and CSLC HDF5 products over EU AOIs
- [x] **Phase 3: DISP-S1 and DIST-S1 Pipelines** - Produce and validate OPERA-spec displacement time-series and surface disturbance products
- [x] **Phase 4: DSWx-S2 Pipeline and Full Interface** - Produce and validate OPERA-spec surface water extent products; complete CLI and validation reporting
- [x] **Phase 5: Fix Cross-Phase Integration Wiring** - Fix all interface contract mismatches between Phase 1 modules and Phase 2/3/4 callers (B-01 through B-06)
- [x] **Phase 6: Wire Unused Data Modules & OPERA Metadata** - Wire fetch_ionex, ASFClient, and inject_opera_metadata into their consumers
- [ ] **Phase 7: CLI Gaps & Code Cleanup** - Add build-db CLI, wire EGMS auto-fetch, remove orphaned code
- [ ] **Phase 8: Planning Artifact Cleanup** - Fix stale ROADMAP/REQUIREMENTS/SUMMARY metadata

## Phase Details

### Phase 1: Foundation, Data Access & Burst DB
**Goal**: All data prerequisites exist — CDSE and ASF access works, the EU burst database resolves AOI geometries to burst IDs, ancillary downloads are automated, and the project's config system is in place
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, BURST-01, BURST-02, BURST-03, CFG-01, CFG-02
**Success Criteria** (what must be TRUE):
  1. `subsideo check-env` runs and confirms CDSE credentials, ASF DAAC credentials, and (if configured) CDS API key are valid
  2. A STAC query for S1 IW SLC over a given EU bounding box returns scene metadata, and those scenes download to local storage via CDSE S3
  3. The EU burst SQLite resolves any EU bounding box to a set of Sentinel-1 burst IDs with correct UTM zone assignments (zones 28N-38N)
  4. GLO-30 DEM tiles for a given AOI are downloaded, mosaicked, and warped to a uniform 30 m UTM grid; orbit and IONEX files for any S1 acquisition are fetched with POEORB-first fallback
  5. Pydantic config loads from env vars, .env, and a per-run YAML; YAML round-trips without loss
**Plans**: 4 plans

Plans:
- [x] 01-01-PLAN.md — Package scaffold, Pydantic Settings, YAML round-trip, check-env CLI skeleton
- [x] 01-02-PLAN.md — CDSEClient: OAuth2, STAC 1.1.0 search, S3 download with retry (DATA-01, DATA-02)
- [x] 01-03-PLAN.md — EU burst SQLite: build from ESA GeoJSON, AOI query, UTM EPSG assignment (BURST-01/02/03)
- [x] 01-04-PLAN.md — DEM (dem-stitcher), orbit (sentineleof), IONEX (CDDIS), ASF DAAC (DATA-03/04/05/06)

### Phase 2: RTC-S1 and CSLC-S1 Pipelines
**Goal**: Users can produce OPERA-spec RTC backscatter and CSLC coregistered SLC products from Sentinel-1 IW SLC data over EU AOIs, with per-product validation against OPERA North America reference products
**Depends on**: Phase 1
**Requirements**: PROD-01, PROD-02, OUT-01, OUT-02, VAL-01, VAL-02, VAL-03
**Success Criteria** (what must be TRUE):
  1. Running the RTC pipeline on a Sentinel-1 scene over an EU AOI produces a COG GeoTIFF at 30 m UTM posting that passes the OPERA product validator (correct chunking, metadata, provenance fields)
  2. Running the CSLC pipeline on the same scene produces an HDF5 file following the OPERA CSLC product specification hierarchy, readable by opera-utils
  3. Pixel-level RMSE between the RTC output and an OPERA N.Am. reference product computed over a matching acquisition falls below 0.5 dB with spatial correlation above 0.99
  4. Phase RMS between the CSLC output and an OPERA N.Am. CSLC reference falls below 0.05 rad
  5. The VAL-01 metric functions (RMSE, spatial correlation, bias, SSIM) return correct values on synthetic test arrays
**Plans**: 4 plans

Plans:
- [x] 02-01-PLAN.md — Shared types (RTCConfig, CSLCResult, etc.) and validation metrics (RMSE, correlation, bias, SSIM) with TDD (VAL-01)
- [x] 02-02-PLAN.md — RTC-S1 pipeline orchestrator: opera-rtc runconfig generation, API invocation, COG conversion, product validation (PROD-01, OUT-01)
- [x] 02-03-PLAN.md — CSLC-S1 pipeline orchestrator: compass runconfig generation, API invocation, HDF5 validation (PROD-02, OUT-02)
- [x] 02-04-PLAN.md — Validation comparison modules: compare_rtc (dB-domain) and compare_cslc (interferometric phase) vs OPERA N.Am. reference (VAL-02, VAL-03)

### Phase 3: DISP-S1 and DIST-S1 Pipelines
**Goal**: Users can produce OPERA-spec surface displacement time-series and surface disturbance products from Sentinel-1 data over EU AOIs, with displacement validated against EGMS EU reference products
**Depends on**: Phase 2
**Requirements**: PROD-03, PROD-05, VAL-04
**Success Criteria** (what must be TRUE):
  1. Running the DISP pipeline on a stack of CSLC HDF5 inputs produces an OPERA-spec DISP HDF5 displacement time series; the post-unwrapping sanity check runs automatically and flags any planar ramp anomalies
  2. Spatial correlation between DISP-S1 velocity output and the EGMS EU reference over a test AOI exceeds 0.92 with absolute velocity bias below 3 mm/yr
  3. Running the DIST pipeline on an RTC time series produces a COG GeoTIFF surface disturbance product that passes the OPERA product validator
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — DISP-S1 pipeline orchestrator: dolphin phase linking, tophu unwrapping, MintPy time-series inversion with ERA5 correction (PROD-03)
- [x] 03-02-PLAN.md — DIST-S1 pipeline orchestrator: dist-s1 wrapper with conditional import, COG validation (PROD-05)
- [x] 03-03-PLAN.md — EGMS validation comparison: LOS-to-vertical projection, grid alignment, correlation and bias metrics (VAL-04)

### Phase 4: DSWx-S2 Pipeline and Full Interface
**Goal**: Users can produce OPERA-spec surface water extent products from Sentinel-2 L2A data over EU AOIs, validated against JRC Global Surface Water; the complete CLI with all subcommands is functional and validation reports are generated
**Depends on**: Phase 1 (DSWx data access); Phase 3 (validate subcommand covers all products)
**Requirements**: PROD-04, OUT-03, VAL-05, VAL-06, CLI-01, CLI-02
**Success Criteria** (what must be TRUE):
  1. Running the DSWx pipeline on a Sentinel-2 L2A scene over an EU AOI produces a COG GeoTIFF with EU-calibrated DSWE thresholds that achieves F1 > 0.90 against the JRC Global Surface Water reference
  2. All products (RTC, CSLC, DISP, DIST, DSWx) carry OPERA-compliant identification metadata including provenance, software version, and run parameters
  3. The `subsideo` CLI exposes rtc, cslc, disp, dswx, dist, and validate subcommands; each product subcommand accepts --aoi, --date-range, and --out parameters
  4. Running `subsideo validate` on completed product outputs generates an HTML and Markdown report with metric tables and spatial diff maps
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md — DSWx types, OPERA metadata utility, and DSWx-S2 pipeline orchestrator (PROD-04, OUT-03)
- [x] 04-02-PLAN.md — JRC validation comparison and validation report generator (VAL-05, VAL-06)
- [x] 04-03-PLAN.md — Complete CLI with all product subcommands and validate command (CLI-01, CLI-02)

### Phase 5: Fix Cross-Phase Integration Wiring
**Goal**: All five product `*_from_aoi` functions call Phase 1 data-access modules with correct constructor args, method names, and signatures — unblocking every broken E2E flow
**Depends on**: Phases 1-4 (fixes wiring between them)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, CLI-01
**Gap Closure:** Closes integration bugs B-01, B-02, B-03, B-04, B-05, B-06 from v1.0 audit
**Success Criteria** (what must be TRUE):
  1. `CDSEClient` is instantiated with valid `client_id` and `client_secret` in all five product `*_from_aoi` functions
  2. RTC and CSLC callers use `search_stac()` with correct keyword arguments (`start_date`, `end_date`)
  3. RTC and CSLC callers use `query_bursts_for_aoi()` from `burst/frames.py` instead of nonexistent `BurstDB` class
  4. `fetch_orbit()` is called with `(sensing_time, satellite, output_dir)` signature in all callers
  5. `fetch_dem()` is called with required `output_epsg` arg and callers unpack the `tuple[Path, dict]` return correctly
  6. CLI DIST command iterates `list[DISTResult]` instead of accessing `.valid` on the list directly
  7. All five product CLI flows (`subsideo rtc/cslc/disp/dist/dswx --aoi ...`) reach the algorithm invocation step without crashing on data-access calls
**Plans**: 2 plans

Plans:
- [x] 05-01-PLAN.md — Fix B-01 through B-05 in rtc.py and cslc.py with unit tests (DATA-01, DATA-03, DATA-04)
- [x] 05-02-PLAN.md — Fix B-01/B-05 in disp/dist/dswx, B-06 in CLI, update existing tests (DATA-02, CLI-01)

### Phase 6: Wire Unused Data Modules & OPERA Metadata
**Goal**: Every Phase 1 data module has at least one consumer, and all five products carry OPERA-compliant identification metadata
**Depends on**: Phase 5 (integration wiring must be correct first)
**Requirements**: DATA-05, DATA-06, OUT-03
**Gap Closure:** Closes audit gaps DATA-05 (unwired ionex), DATA-06 (unwired ASF), OUT-03 (metadata only in DSWx)
**Success Criteria** (what must be TRUE):
  1. CSLC pipeline calls `fetch_ionex()` to obtain TEC maps and passes the result as `tec_file` to the processing step (instead of hardcoded `None`)
  2. `subsideo validate` CLI can automatically fetch OPERA reference products from ASF DAAC via `ASFClient` when `--reference` is not provided
  3. `inject_opera_metadata()` is called in RTC, CSLC, DISP, and DIST product pipelines (not just DSWx)
  4. All five product types include provenance, software version, and run parameters in their output metadata
**Plans**: 2 plans

Plans:
- [x] 06-01-PLAN.md — Wire IONEX into CSLC, inject OPERA metadata into all 5 pipelines, get_software_version helper (DATA-05, OUT-03)
- [x] 06-02-PLAN.md — Wire ASF auto-fetch into validate CLI for RTC/CSLC reference products (DATA-06)

### Phase 7: CLI Gaps & Code Cleanup
**Goal**: Add missing CLI entry points and clean up orphaned code identified by v1.0 milestone audit
**Depends on**: Phase 6
**Requirements**: BURST-01, VAL-04
**Gap Closure:** Closes tech debt from v1.0 milestone audit — build-db CLI, EGMS auto-fetch, orphaned code removal
**Success Criteria** (what must be TRUE):
  1. `subsideo build-db <geojson>` CLI command exists and calls `build_burst_db()` to create `~/.subsideo/eu_burst_db.sqlite`
  2. `subsideo validate --product-type disp` auto-fetches EGMS reference via `fetch_egms_ortho()` when `--egms` is not provided
  3. Orphaned `select_utm_epsg()` in `burst/tiling.py` is removed or inlined
  4. Stale comment in `cli.py:42` about Plan 04 connectivity check is removed
**Plans**: 1 plan

Plans:
- [x] 07-01-PLAN.md — Add build-db CLI, wire EGMS auto-fetch, remove dead code (BURST-01, VAL-04)

### Phase 8: Planning Artifact Cleanup
**Goal**: Fix all stale planning metadata in ROADMAP.md, REQUIREMENTS.md, and SUMMARY frontmatter so artifacts accurately reflect completed v1.0 work
**Depends on**: Phase 7
**Requirements**: None (planning artifacts only)
**Gap Closure:** Closes housekeeping tech debt from v1.0 milestone audit
**Success Criteria** (what must be TRUE):
  1. ROADMAP.md progress table shows all 6 phases as Complete with correct plan counts
  2. All executed plan checkboxes in ROADMAP.md are checked (`[x]`)
  3. REQUIREMENTS.md coverage summary reflects 27/27 satisfied with 0 pending; merge conflict markers removed
  4. All 18 SUMMARY.md files have `requirements_completed` frontmatter populated
**Plans**: 0 plans

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation, Data Access & Burst DB | 4/4 | Complete | - |
| 2. RTC-S1 and CSLC-S1 Pipelines | 4/4 | Complete | - |
| 3. DISP-S1 and DIST-S1 Pipelines | 3/3 | Complete | - |
| 4. DSWx-S2 Pipeline and Full Interface | 3/3 | Complete | - |
| 5. Fix Cross-Phase Integration Wiring | 2/2 | Complete | - |
| 6. Wire Unused Data Modules & OPERA Metadata | 2/2 | Complete | - |
| 7. CLI Gaps & Code Cleanup | 0/1 | In Progress | - |
| 8. Planning Artifact Cleanup | 0/0 | Not started | - |
