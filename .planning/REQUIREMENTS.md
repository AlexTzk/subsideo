# Requirements: subsideo

**Defined:** 2026-04-05
**Core Value:** Produce scientifically accurate, OPERA-spec-compliant SAR/InSAR geospatial products over EU AOIs — validated against official reference products to prove correctness.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Access

- [x] **DATA-01**: Library can search and download Sentinel-1 IW SLC data from CDSE via STAC + S3
- [x] **DATA-02**: Library can search and download Sentinel-2 L2A data from CDSE via STAC + S3
- [x] **DATA-03**: Library can download and mosaic GLO-30 Copernicus DEM tiles for a given AOI
- [x] **DATA-04**: Library can download precise orbit ephemerides (POE/ROE) for Sentinel-1
- [ ] **DATA-05**: Library can download IONEX TEC maps for ionospheric correction
- [ ] **DATA-06**: Library can search and download OPERA reference products from ASF DAAC (for validation)

### Burst Management

- [x] **BURST-01**: Library provides an EU-scoped burst database (SQLite) built from ESA burst ID maps
- [x] **BURST-02**: Library can resolve AOI geometry to a set of Sentinel-1 burst IDs and frames
- [x] **BURST-03**: Library correctly selects UTM zone(s) for EU AOIs spanning zones 28N–38N

### Products

- [x] **PROD-01**: Library can produce RTC-S1 backscatter products from S1 IW SLC over EU AOIs using ISCE3
- [x] **PROD-02**: Library can produce CSLC-S1 coregistered SLC products from S1 IW SLC over EU AOIs using ISCE3
- [x] **PROD-03**: Library can produce DISP-S1 displacement time-series products using dolphin + tophu + MintPy
- [x] **PROD-04**: Library can produce DSWx-S2 surface water extent products from S2 L2A over EU AOIs
- [x] **PROD-05**: Library can produce DIST-S1 surface disturbance products from RTC time series

### Output Compliance

- [x] **OUT-01**: RTC and DSWx products are written as Cloud-Optimised GeoTIFF with correct metadata
- [x] **OUT-02**: CSLC and DISP products are written as HDF5 following OPERA product specification hierarchy
- [ ] **OUT-03**: All products include OPERA-compliant identification metadata (provenance, version, params)

### Validation

- [x] **VAL-01**: Library computes pixel-level RMSE, spatial correlation, bias, and SSIM between products
- [x] **VAL-02**: Library can compare RTC-S1 output against OPERA N.Am. RTC reference (RMSE < 0.5 dB, r > 0.99)
- [x] **VAL-03**: Library can compare CSLC-S1 output against OPERA N.Am. CSLC reference (phase RMS < 0.05 rad)
- [x] **VAL-04**: Library can compare DISP-S1 output against EGMS EU displacement products (r > 0.92, bias < 3 mm/yr)
- [x] **VAL-05**: Library can compare DSWx-S2 output against JRC Global Surface Water (F1 > 0.90)
- [x] **VAL-06**: Library generates HTML/Markdown validation reports with metric tables and diff maps

### Interface

- [x] **CLI-01**: Typer CLI exposes subcommands: rtc, cslc, disp, dswx, validate
- [x] **CLI-02**: Each product subcommand accepts --aoi, --date-range, and --out parameters
- [x] **CFG-01**: Pydantic BaseSettings loads config from env vars, .env file, and per-run YAML
- [x] **CFG-02**: Per-run YAML config follows ISCE3 workflow YAML convention

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Notifications & Monitoring

- **MON-01**: Progress callbacks/events for long-running pipeline stages
- **MON-02**: Structured JSON log output for pipeline integration

### Extended Products

- **EXT-01**: VLM (vertical land motion) product from DISP time series
- **EXT-02**: NISAR data support stubs

### Performance

- **PERF-01**: GPU-accelerated phase linking via dolphin JAX backend
- **PERF-02**: Async parallel downloads for large EU frame sets

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time operational pipeline orchestration | Library, not SDS/PGE; users wire CLI into their own schedulers |
| Windows native support | ISCE3 + GDAL + snaphu conda stack doesn't build on Windows; WSL2 acceptable |
| Commercial cloud deployment / Docker images | Two-layer install not trivially containerised; defer to community |
| Web UI / interactive dashboard | Out of scope for library; Jupyter notebooks cover interactive use |
| Multi-mission support (ERS, ENVISAT) | Dilutes Sentinel-1/2 EU focus; NISAR stubs only per v2 |
| Automated data ordering / tasking | Sentinel-1/2 is free archived data; STAC search is sufficient |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 5 | Complete |
| DATA-02 | Phase 5 | Complete |
| DATA-03 | Phase 5 | Complete |
| DATA-04 | Phase 5 | Complete |
| DATA-05 | Phase 6 | Pending |
| DATA-06 | Phase 6 | Pending |
| BURST-01 | Phase 1 | Complete |
| BURST-02 | Phase 1 | Complete |
| BURST-03 | Phase 1 | Complete |
| CFG-01 | Phase 1 | Complete |
| CFG-02 | Phase 1 | Complete |
| PROD-01 | Phase 2 | Complete |
| PROD-02 | Phase 2 | Complete |
| OUT-01 | Phase 2 | Complete |
| OUT-02 | Phase 2 | Complete |
| VAL-01 | Phase 2 | Complete |
| VAL-02 | Phase 2 | Complete |
| VAL-03 | Phase 2 | Complete |
| PROD-03 | Phase 3 | Complete |
| PROD-05 | Phase 3 | Complete |
| VAL-04 | Phase 3 | Complete |
| PROD-04 | Phase 4 | Complete |
| OUT-03 | Phase 6 | Pending |
| VAL-05 | Phase 4 | Complete |
| VAL-06 | Phase 4 | Complete |
| CLI-01 | Phase 5 | Complete |
| CLI-02 | Phase 4 | Complete |

**Coverage:**
- v1 requirements: 27 total
- Mapped to phases: 27
- Satisfied: 20
- Pending (gap closure): 7 (DATA-01–04, DATA-05, DATA-06, CLI-01, OUT-03)
- Unmapped: 0

---
*Requirements defined: 2026-04-05*
*Last updated: 2026-04-05 after roadmap creation*
