# subsideo — Project Brief
**Goal-oriented Software Design (GSD) brief for Claude Code / autonomous development agents**

---

## 1. Project Identity

| Field | Value |
|---|---|
| Package name | `subsideo` |
| PyPI slug | `subsideo` |
| Import name | `subsideo` |
| Language | Python ≥ 3.10 |
| License | Apache-2.0 |
| Target platforms | Linux x86-64 (primary), macOS arm64 (secondary) |
| Build backend | Hatchling |

---

## 2. Problem Statement

NASA JPL's OPERA project produces four near-real-time geospatial product suites derived from Sentinel-1 and Sentinel-2/Landsat data — surface water extent (DSWx), surface disturbance (DIST), surface displacement (DISP), and vertical land motion (VLM) — but coverage is **geofenced to North America and US territories**. The European equivalent for displacement (EGMS) is a batch product updated in multi-year epochs, not operationally. No open Python library exists that:

1. Wraps the OPERA/ISCE3 algorithm stack with a clean, developer-facing API.
2. Targets EU areas of interest (AOIs) using the Copernicus Data Space Ecosystem (CDSE) as the data backend.
3. Ships a validation framework that compares against both OPERA N.Am. reference products (cross-validation at overlap zones) and EGMS EU products.

`subsideo` fills that gap.

---

## 3. Functional Goals (ordered by implementation priority)

### G1 — RTC-S1 for EU  *(Phase 1 — implement first)*
Produce Radiometric Terrain-Corrected SAR backscatter products from Sentinel-1 IW SLC data over user-specified EU AOIs. The algorithm is the ISCE3-based OPERA RTC pipeline. Validation: pixel-level diff against official OPERA RTC-S1 products fetched from ASF DAAC over an NA overlap area.

### G2 — CSLC-S1 for EU  *(Phase 2)*
Produce Coregistered Single-Look Complex products — the foundational input for displacement time series. Uses ISCE3 burst coregistration. Validate geometric accuracy against OPERA CSLC products.

### G3 — DISP-S1 for EU  *(Phase 2, depends on G2)*
Produce InSAR time-series surface displacement products. Uses `dolphin` (isce-framework) for phase linking, SNAPHU/tophu for phase unwrapping, MintPy for time-series inversion and tropospheric correction. Output: HDF5 granules at 30 m UTM spatial posting, matching OPERA DISP-S1 product specification. Validate against EGMS EU products.

### G4 — DSWx-S2 for EU  *(Phase 3)*
Produce Dynamic Surface Water Extent products from Sentinel-2 L2A. Port the OPERA DSWx-HLS algorithm, adapting HLS data access to direct CDSE Sentinel-2 pulls. Validate against JRC Global Surface Water and Copernicus water body products.

### G5 — DIST-S1 for EU  *(Phase 3)*
Produce Surface Disturbance products from Sentinel-1 RTC time series. Based on the `opera-adt/dist-s1` workflow. Use cases: wildfire monitoring, deforestation, infrastructure change.

### G6 — Validation framework  *(cross-cutting)*
A structured `subsideo.validation` module that computes spatial correlation, RMSE, bias maps, and temporal consistency between `subsideo` outputs and reference products (OPERA N.Am. via ASF DAAC, EGMS via CLMS). Outputs standardized reports.

---

## 4. Non-Goals (explicit out-of-scope)

- VLM (vertical land motion) — OPERA's own VLM product targets 2028; skip for v1.
- Real-time operational production infrastructure (SDS/PGE orchestration) — this is a library, not a pipeline orchestrator.
- Commercial cloud deployment / containerised production service — out of scope for v1.
- Support for NISAR data — future work; placeholder stubs only.
- Windows native support — not a priority; WSL2 is acceptable.

---

## 5. Repository Layout

```
subsideo/
├── src/
│   └── subsideo/
│       ├── __init__.py
│       ├── cli.py                  # typer-based CLI: `subsideo rtc`, `subsideo disp`, etc.
│       ├── config.py               # Pydantic settings: CDSE creds, working dirs, DEM path
│       │
│       ├── data/                   # Data access layer (all I/O lives here)
│       │   ├── __init__.py
│       │   ├── cdse.py             # CDSE STAC/OData search + S3 download wrapper
│       │   ├── asf.py              # ASF DAAC access for OPERA reference products (validation)
│       │   ├── dem.py              # GLO-30 Copernicus DEM download and tile management
│       │   ├── orbits.py           # S1-A/B/C POE/ROE orbit ephemeris download (CDDIS)
│       │   └── ionosphere.py       # IONEX TEC map download (CDDIS GNSS archive)
│       │
│       ├── burst/                  # Burst database and frame management
│       │   ├── __init__.py
│       │   ├── db.py               # EU burst DB: wraps opera-utils burst_db + EU frame extension
│       │   ├── frames.py           # EU frame-to-burst mapping (SQLite queries)
│       │   └── tiling.py           # UTM zone selection for EU (zones 28–38N)
│       │
│       ├── products/               # One module per OPERA product type
│       │   ├── __init__.py
│       │   ├── rtc.py              # G1: RTC-S1 pipeline wrapper (opera-adt/RTC + ISCE3)
│       │   ├── cslc.py             # G2: CSLC-S1 pipeline wrapper (ISCE3 burst coregistration)
│       │   ├── disp.py             # G3: DISP-S1 pipeline (dolphin + tophu + MintPy)
│       │   ├── dswx.py             # G4: DSWx-S2 pipeline (Sentinel-2 L2A from CDSE)
│       │   └── dist.py             # G5: DIST-S1 pipeline (opera-adt/dist-s1)
│       │
│       ├── validation/             # G6: Validation framework
│       │   ├── __init__.py
│       │   ├── metrics.py          # RMSE, spatial correlation, bias, SSIM
│       │   ├── compare_opera.py    # Pixel-level diff vs OPERA N.Am. products (ASF DAAC)
│       │   ├── compare_egms.py     # Comparison vs EGMS EU displacement products
│       │   ├── compare_jrc.py      # DSWx validation vs JRC Global Surface Water
│       │   └── report.py           # HTML/Markdown validation report generator
│       │
│       └── utils/
│           ├── __init__.py
│           ├── io.py               # Cloud-optimised GeoTIFF / HDF5 read-write helpers
│           ├── projections.py      # UTM zone helpers for EU; CRS reprojection utils
│           └── logging.py          # Loguru-based structured logging setup
│
├── tests/
│   ├── conftest.py                 # Shared fixtures; AOI constants (Po Valley, Rhine delta)
│   ├── unit/
│   │   ├── test_burst_db.py
│   │   ├── test_cdse.py
│   │   ├── test_dem.py
│   │   └── test_metrics.py
│   ├── integration/                # Requires live CDSE credentials; marked @pytest.mark.integration
│   │   ├── test_rtc_eu.py
│   │   └── test_disp_eu.py
│   └── validation/                 # Cross-comparison; marked @pytest.mark.validation
│       ├── test_rtc_vs_opera.py
│       └── test_disp_vs_egms.py
│
├── notebooks/
│   ├── 01_rtc_po_valley.ipynb      # Demo: RTC over Po Valley, Italy
│   ├── 02_disp_amsterdam.ipynb     # Demo: Displacement over Amsterdam subsidence area
│   └── 03_dswx_danube_delta.ipynb  # Demo: Surface water, Danube Delta
│
├── docs/
│   ├── index.md
│   ├── install.md                  # Conda + pip split-install instructions
│   ├── products/
│   │   ├── rtc.md
│   │   ├── disp.md
│   │   └── dswx.md
│   ├── validation.md
│   └── api/                        # mkdocstrings auto-generated API docs
│
├── conda-env.yml                   # Full environment including isce3, gdal (conda-forge)
├── environment-dev.yml             # conda-env.yml + dev extras
├── pyproject.toml
├── .env.example                    # CDSE_CLIENT_ID, CDSE_CLIENT_SECRET, EARTHDATA_* vars
├── .pre-commit-config.yaml
├── .github/
│   └── workflows/
│       ├── ci.yml                  # pytest on push (unit tests; integration skipped)
│       └── publish.yml             # PyPI publish on tag
├── CHANGELOG.md
└── README.md
```

---

## 6. Architecture Decisions

### 6.1 ISCE3 / dolphin installation split
ISCE3 and several heavy dependencies (GDAL, HDF5 native libs) cannot be reliably installed via pip alone. The project uses a **two-layer install**:

1. `conda-env.yml` installs the conda-forge-only stack: `isce3`, `gdal`, `hdf5`, `snaphu`, `isce-framework::dolphin`, `isce-framework::tophu`.
2. `pip install subsideo` (or `pip install -e .`) installs the pure-Python package and pip-installable dependencies on top.

Document this clearly in `install.md`. The `pyproject.toml` does **not** declare `isce3` or `gdal` as pip dependencies — they are declared only in `conda-env.yml`.

### 6.2 Data access: CDSE over ASF DAAC
All EU Sentinel-1/2 input data is pulled from the **Copernicus Data Space Ecosystem** S3 bucket (`s3://eodata/`). This requires a free CDSE account (env vars: `CDSE_CLIENT_ID`, `CDSE_CLIENT_SECRET`). ASF DAAC access (env vars: `EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD`) is used only for fetching OPERA N.Am. reference products during validation.

### 6.3 Burst database for EU
OPERA's `opera-burstdb` SQLite covers North America only. For EU, `subsideo.burst.db` will:
1. Extend `opera-utils`' burst DB utilities using ESA's published global burst ID maps (available from ESA Burst ID Map, CC-BY 4.0).
2. Build a lightweight EU-scoped SQLite file (`eu_burst_db.sqlite`) with the same schema as `opera-burstdb`, indexed by track/burst/IW subswath.
3. Cache this file locally on first run (`~/.subsideo/eu_burst_db.sqlite`); refresh on version bump.

### 6.4 Output format
All products follow the OPERA product specification document format: HDF5 (`.h5`) for CSLC and DISP products (30 m UTM posting), Cloud-Optimised GeoTIFF (`.tif`) for RTC and DSWx. This maximises interoperability with OPERA tooling and QGIS.

### 6.5 Configuration
Global config via `subsideo.config.Settings` (Pydantic `BaseSettings`), populated from environment variables with `.env` fallback. Per-run config via YAML files (same pattern as ISCE3 workflow YAML). No hardcoded paths.

### 6.6 CLI design
```bash
subsideo rtc   --aoi bbox.geojson --date-range 2024-01-01 2024-03-01 --out ./rtc-output
subsideo cslc  --aoi bbox.geojson --date-range 2024-01-01 2024-06-01 --out ./cslc-output
subsideo disp  --aoi bbox.geojson --date-range 2023-01-01 2024-06-01 --out ./disp-output
subsideo dswx  --aoi bbox.geojson --date-range 2024-04-01 2024-09-01 --out ./dswx-output
subsideo validate rtc  --eu ./rtc-output --opera-frame 11114 --out ./validation-rtc
subsideo validate disp --eu ./disp-output --egms-epoch 2018-2022 --out ./validation-disp
```

---

## 7. Key External Dependencies

| Package | Source | Purpose |
|---|---|---|
| `isce3` | conda-forge | Core SAR processing engine (RTC, CSLC) |
| `dolphin` | isce-framework/dolphin (conda-forge) | Phase linking + PS/DS processing for DISP |
| `tophu` | isce-framework/tophu (conda-forge) | Tile-based phase unwrapping |
| `snaphu` | conda-forge | Phase unwrapping (SNAPHU binary) |
| `mintpy` | PyPI / conda-forge | InSAR time-series inversion, tropospheric correction |
| `opera-utils` | PyPI / conda-forge | OPERA burst DB, CSLC/DISP file parsing |
| `s1-reader` | PyPI (opera-adt) | Sentinel-1 SLC burst reader, ISCE3-compatible |
| `cdse-client` | PyPI | CDSE STAC search + S3 download |
| `asf-search` | PyPI | ASF DAAC product search (validation) |
| `rasterio` | PyPI / conda-forge | Raster I/O, COG write |
| `h5py` | PyPI / conda-forge | HDF5 product read/write |
| `pystac-client` | PyPI | STAC API queries |
| `typer` | PyPI | CLI |
| `pydantic` | PyPI | Config validation |

---

## 8. Validation Strategy

### Phase A — N.Am. parity (before EU runs)
1. Pick a test frame on the US West Coast (e.g. frame 11114, covering central California).
2. Run `subsideo rtc` over that frame and date range.
3. Fetch the official OPERA RTC-S1 product for the same frame/date from ASF DAAC.
4. Compute pixel-level RMSE and spatial correlation over land pixels (exclude no-data ocean mask).
5. **Pass criterion**: RMSE < 0.5 dB backscatter, spatial correlation > 0.99.

Repeat the same parity check for CSLC (phase difference < 0.05 rad RMS over stable targets) and DISP (displacement difference < 2 mm RMS over coherent pixels).

### Phase B — EU production run + EU validation
1. Run `subsideo disp` over Po Valley, Italy (well-documented subsidence, present in EGMS 2018-2022 epoch).
2. Compare line-of-sight velocity maps against EGMS descending velocity product.
3. **Pass criterion**: Pearson r > 0.92, mean bias < 3 mm/yr over stable reference network pixels.

Repeat for a DSWx run over the Danube Delta (compare against JRC GSW monthly occurrence).

---

## 9. Testing Conventions

- **Unit tests** (`tests/unit/`): mock all I/O; no network calls; run in CI on every push. Target > 80% coverage.
- **Integration tests** (`tests/integration/`): require live CDSE credentials; use small 50×50 km AOI; marked `@pytest.mark.integration`; run manually or on a scheduled nightly CI job.
- **Validation tests** (`tests/validation/`): full pipeline runs over reference AOIs; marked `@pytest.mark.validation`; run manually before release tagging.
- Test fixtures in `conftest.py` provide: small synthetic SAR arrays, mock CDSE API responses, pre-downloaded burst DB excerpts.

---

## 10. Implementation Sequence for Autonomous Agent

Execute phases strictly in order. Each phase ends with a passing test gate before proceeding.

```
Phase 0 — Scaffold
  [ ] Initialise repo with hatchling layout (src/subsideo/)
  [ ] Write pyproject.toml (provided)
  [ ] Write conda-env.yml with isce3, dolphin, tophu, snaphu, gdal
  [ ] Write .env.example and config.py (Pydantic Settings)
  [ ] Write cli.py skeleton (typer app with stubbed subcommands)
  [ ] Write utils/logging.py (loguru setup)
  [ ] Set up pre-commit (ruff, mypy)
  [ ] Set up GitHub Actions CI (unit tests only)
  TEST GATE: `pytest tests/unit/` passes; ruff + mypy clean

Phase 1 — Data access layer
  [ ] Implement data/dem.py: GLO-30 tile download + mosaic for AOI
  [ ] Implement data/orbits.py: POE/ROE fetch from CDDIS
  [ ] Implement data/ionosphere.py: IONEX TEC fetch from CDDIS
  [ ] Implement data/cdse.py: CDSE STAC search + S3 download for S1 SLC and S2 L2A
  [ ] Implement data/asf.py: ASF DAAC OPERA product search and download
  [ ] Implement burst/db.py: EU burst DB build from ESA burst ID maps
  [ ] Implement burst/frames.py: frame-to-burst mapping queries
  [ ] Unit tests for all data/ and burst/ modules (mocked I/O)
  TEST GATE: `pytest tests/unit/` passes

Phase 2 — RTC-S1 (G1)
  [ ] Implement products/rtc.py wrapping opera-adt/RTC + ISCE3
  [ ] Wire RTC into CLI: `subsideo rtc`
  [ ] Integration test: small EU AOI (e.g. 50x50 km over Bavaria)
  [ ] Validation test: compare vs OPERA RTC-S1 on NA frame 11114
  TEST GATE: Validation pass criterion met (RMSE < 0.5 dB, r > 0.99)

Phase 3 — CSLC-S1 (G2) + DISP-S1 (G3)
  [ ] Implement products/cslc.py: ISCE3 burst coregistration pipeline
  [ ] Implement products/disp.py: dolphin phase linking → tophu unwrapping → MintPy inversion
  [ ] Wire CSLC + DISP into CLI
  [ ] Validation test CSLC: phase RMS vs OPERA CSLC on NA frame
  [ ] Validation test DISP: velocity comparison vs EGMS (Po Valley)
  TEST GATE: CSLC phase RMS < 0.05 rad; DISP r > 0.92, bias < 3 mm/yr

Phase 4 — DSWx-S2 (G4)
  [ ] Implement products/dswx.py: port DSWx-HLS algorithm to CDSE Sentinel-2 L2A
  [ ] Validation test: Danube Delta vs JRC GSW monthly occurrence
  TEST GATE: Spatial agreement (F1 score water vs non-water) > 0.90

Phase 5 — DIST-S1 (G5)
  [ ] Implement products/dist.py: wrapping opera-adt/dist-s1 workflow
  [ ] Demo notebook: wildfire scar detection in southern EU

Phase 6 — Validation framework, docs, packaging
  [ ] Implement validation/metrics.py, compare_opera.py, compare_egms.py, compare_jrc.py
  [ ] Implement validation/report.py: Markdown + HTML report output
  [ ] Write notebooks/01–03
  [ ] Write docs/ (MkDocs-material)
  [ ] Publish to PyPI (hatch build + twine upload)
  [ ] Submit conda-forge feedstock PR
```

---

## 11. Environment File Template

> Save as `conda-env.yml` at repo root.

```yaml
name: subsideo
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.11
  - isce3>=0.18
  - gdal>=3.8
  - hdf5>=1.12
  - snaphu>=2.0
  - proj>=9.3
  # isce-framework packages (conda-forge)
  - dolphin>=0.25       # phase linking SAS for DISP
  - tophu>=0.4          # tile-based phase unwrapping
  # pip-installable packages installed on top
  - pip
  - pip:
      - subsideo[geo,validation]
```

---

## 12. Credential Environment Variables

```
# Copernicus Data Space Ecosystem (CDSE) — free registration at dataspace.copernicus.eu
CDSE_CLIENT_ID=<your-cdse-client-id>
CDSE_CLIENT_SECRET=<your-cdse-client-secret>

# NASA Earthdata — for fetching OPERA N.Am. validation products from ASF DAAC
EARTHDATA_USERNAME=<your-earthdata-username>
EARTHDATA_PASSWORD=<your-earthdata-password>

# Working directories
SUBSIDEO_WORK_DIR=/path/to/scratch
SUBSIDEO_CACHE_DIR=~/.subsideo
```

Never commit credentials. `python-dotenv` will load `.env` automatically. `.env` is in `.gitignore`.

---

## 13. Known Hard Problems / Agent Warnings

1. **EU burst DB completeness**: The `opera-adt/burst_db` SQLite file only indexes N.Am. frames. Building a global or EU-scoped equivalent requires parsing ESA's published Sentinel-1 burst ID maps (GeoJSON, CC-BY). Implement this in `burst/db.py` with a build script that caches the result. Do not hardcode frame IDs.

2. **ISCE3 not pip-installable**: Never attempt `pip install isce3`. It must come from conda-forge. The pyproject.toml intentionally omits it from `dependencies`. The agent must always set up the conda environment first, then pip-install `subsideo` into it.

3. **dolphin package name collision**: There is an unrelated `dolphin-python` on PyPI (GPU ray tracer). The correct `dolphin` for DISP processing is from `isce-framework/dolphin` on conda-forge. Never `pip install dolphin` without the conda environment active.

4. **CDSE S3 bucket access**: Direct S3 access to `s3://eodata/` requires endpoint override (`endpoint_url=https://eodata.dataspace.copernicus.eu`) in boto3/s3fs — it is not standard AWS S3. Configure this in `data/cdse.py`.

5. **UTM zone handling for EU**: EU spans UTM zones 28N through 38N (and some northern zones). OPERA N.Am. assumes a narrower UTM range. `burst/tiling.py` must correctly compute and handle multi-zone AOIs, including tile edge cases at zone boundaries.

6. **SNAPHU licensing**: SNAPHU is available under a non-commercial research license. Document this in the README. It is available via conda-forge. The `tophu` package provides tile-based parallelisation on top of SNAPHU.

7. **Tropospheric correction for EU**: MintPy's tropospheric correction uses ERA5 reanalysis. For EU, ECMWF ERA5 data is available via the Copernicus Climate Data Store (CDS) API. Users need a separate CDS API key (`~/.cdsapirc`). Document this in `install.md`.
