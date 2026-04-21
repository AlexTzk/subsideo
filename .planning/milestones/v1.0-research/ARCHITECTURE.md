# Architecture Research

**Domain:** SAR/InSAR geospatial processing library (OPERA-spec EU products)
**Researched:** 2026-04-05
**Confidence:** MEDIUM — ISCE3/dolphin/MintPy architecture verified via official GitHub repos and published papers; subsideo-specific integration patterns are inferred from upstream repo structures.

---

## Standard Architecture

### System Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                         CLI / Config Layer                          │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────────┐  │
│  │  typer CLI   │  │ Pydantic config │  │   YAML run-config    │  │
│  │  (subcommands│  │ (env + .env +   │  │   (per-pipeline      │  │
│  │  rtc/cslc/   │  │  YAML merge)    │  │    overrides)        │  │
│  │  disp/dswx/  │  └────────┬────────┘  └──────────┬───────────┘  │
│  │  dist/       │           │                       │              │
│  │  validate)   │           └───────────┬───────────┘              │
│  └──────┬───────┘                       │                          │
└─────────┼─────────────────────────────  ↓  ──────────────────────┘
          │                    Settings / RunConfig objects
          ↓
┌─────────────────────────────────────────────────────────────────────┐
│                        Pipeline Orchestration Layer                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────┐  │
│  │  RTC        │  │  CSLC       │  │  DISP        │  │  DSWx    │  │
│  │  Pipeline   │  │  Pipeline   │  │  Pipeline    │  │  Pipeline│  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘  └────┬─────┘  │
│         │                │                │               │         │
│                 ┌────────┴──────────────────────┐                   │
│                 │       Ancillary Resolver       │                   │
│                 │  (DEM, orbit POE, IONEX TEC)   │                   │
│                 └───────────────────────────────┘                   │
└──────────────────────────────────────────────────────────────────────┘
          │
          ↓
┌─────────────────────────────────────────────────────────────────────┐
│                          Algorithm Wrappers                          │
│  ┌────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  isce3     │  │   dolphin    │  │  tophu   │  │   MintPy     │  │
│  │  (RTC,     │  │  (phase-     │  │  (tiled  │  │  (time-      │  │
│  │   CSLC,    │  │   linking,   │  │   unwrap)│  │   series     │  │
│  │   geocode, │  │   PS/DS,     │  └────┬─────┘  │   inversion, │  │
│  │   unw)     │  │   mini-stack │       │        │   ERA5 tropo)│  │
│  └────┬───────┘  └──────┬───────┘       │        └──────┬───────┘  │
│       │                 └───────────────┘               │          │
└───────┼─────────────────────────────────────────────────┼──────────┘
        │                                                  │
        ↓                                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│                          Data Access Layer                           │
│  ┌───────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  CDSE accessor    │  │  Burst/Frame DB   │  │  ASF DAAC        │  │
│  │  (STAC search +   │  │  (EU SQLite from  │  │  accessor        │  │
│  │   S3 download     │  │   ESA GeoJSON)    │  │  (OPERA N.Am.    │  │
│  │   s3://eodata/)   │  │                   │  │   ref products   │  │
│  └───────────────────┘  └──────────────────┘  └──────────────────┘  │
│  ┌───────────────────┐  ┌──────────────────┐                         │
│  │  DEM manager      │  │  Orbit / IONEX   │                         │
│  │  (GLO-30 tile     │  │  fetcher (ESA    │                         │
│  │   stitch + cache) │  │   POE/ROE, IONEX)│                         │
│  └───────────────────┘  └──────────────────┘                         │
└─────────────────────────────────────────────────────────────────────┘
          │
          ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         Output / Validation Layer                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │  Product writers │  │  Validation      │  │  Report          │   │
│  │  (HDF5 for CSLC/ │  │  framework       │  │  generator       │   │
│  │   DISP; COG for  │  │  (RMSE, r, bias, │  │  (HTML/Markdown) │   │
│  │   RTC/DSWx/DIST) │  │   SSIM vs OPERA/ │  │                  │   │
│  └──────────────────┘  │   EGMS/JRC)      │  └──────────────────┘   │
│                         └──────────────────┘                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| CLI layer | Parse subcommands; load config; invoke pipelines | `typer` app with `app.command()` per product type |
| Config layer | Merge env vars + `.env` + YAML overrides; validate | `pydantic.BaseSettings` + `pydantic_settings`; `YamlModel` (dolphin pattern) |
| Pipeline orchestration | Sequence processing steps; manage staging I/O; coordinate wrappers | Plain Python orchestrator functions; no heavyweight DAG needed for v1 |
| Ancillary resolver | Resolve and download DEM, orbit, ionosphere for a given burst/scene | Thin Python module; caches to local dir; called by all pipelines |
| ISCE3 wrapper | Execute RTC normalisation, CSLC burst coregistration, geocoding | Python bindings from `isce3` conda package; called via Python API not subprocess |
| dolphin wrapper | Phase linking mini-stacks, PS/DS selection, wrapped phase output | `dolphin.workflows` Python API; Pydantic `WorkflowConfig` YAML |
| tophu wrapper | Tile-based multi-scale phase unwrapping for large interferograms | `tophu` Python API; composable with snaphu or isce3 unwrappers |
| MintPy wrapper | Ingest dolphin outputs, time-series inversion, ERA5 tropospheric correction | Call `smallbaselineApp` programmatically or via subprocess with generated `.cfg` |
| CDSE accessor | STAC search for S1/S2 granules; S3 download from `s3://eodata/` | `pystac_client` for search; `boto3` with custom endpoint for S3 |
| Burst/Frame DB | Spatial query: given AOI, return burst IDs + UTM frame info | SQLite/GeoPackage (opera-adt `burst_db` schema); extended for EU coverage |
| ASF DAAC accessor | Fetch OPERA N.Am. reference products for validation | `earthaccess` or `requests` + Earthdata auth token |
| DEM manager | Download and stitch GLO-30 tiles for a bounding box | `dem-stitcher` or direct S3/STAC access to AWS Copernicus DEM bucket |
| Orbit/IONEX fetcher | Download precise orbit ephemeris (POE) and IONEX TEC grids | Direct HTTP from ESA orbit server; CDDIS for IONEX |
| Product writers | Write OPERA-spec HDF5 and COG GeoTIFF outputs | `h5py` / `rasterio`; OPERA product spec templates |
| Validation framework | Compare subsideo output against OPERA, EGMS, JRC reference datasets | Metric functions (`numpy`, `scipy`); spatial resampling via `rasterio` |
| Report generator | Produce HTML/Markdown validation reports with figures | `jinja2` templates + `matplotlib`/`plotly` |

---

## Recommended Project Structure

```
src/subsideo/
├── __init__.py
├── _version.py                  # single version source via hatch-vcs
│
├── access/                      # Data access layer
│   ├── __init__.py
│   ├── cdse.py                  # STAC search + S3 download (Sentinel-1/2)
│   ├── asf.py                   # ASF DAAC OPERA ref product download
│   ├── dem.py                   # GLO-30 tile download + stitch
│   ├── orbits.py                # POE/ROE orbit ephemeris download
│   └── ionosphere.py            # IONEX TEC download (ESA/CDDIS)
│
├── bursts/                      # Burst and frame management
│   ├── __init__.py
│   ├── db.py                    # EU burst SQLite build from ESA GeoJSON
│   ├── query.py                 # AOI → burst IDs + UTM frame resolution
│   └── geometry.py              # UTM zone edge handling for EU AOIs
│
├── pipelines/                   # Pipeline orchestration
│   ├── __init__.py
│   ├── rtc.py                   # RTC-S1 pipeline (ISCE3 OPERA-RTC)
│   ├── cslc.py                  # CSLC-S1 pipeline (ISCE3 burst coregistration)
│   ├── disp.py                  # DISP-S1 pipeline (dolphin + tophu + MintPy)
│   ├── dswx.py                  # DSWx-S2 pipeline (Sentinel-2 L2A port)
│   └── dist.py                  # DIST-S1 pipeline (opera-adt/dist-s1 wrapper)
│
├── wrappers/                    # Algorithm adapter layer
│   ├── __init__.py
│   ├── isce3.py                 # ISCE3 Python API calls (RTC, CSLC, geocode)
│   ├── dolphin.py               # dolphin WorkflowConfig build + run
│   ├── tophu.py                 # tophu unwrapping invocation
│   └── mintpy.py                # smallbaselineApp config generation + run
│
├── config/                      # Configuration models
│   ├── __init__.py
│   ├── settings.py              # Global Pydantic BaseSettings (env + .env)
│   ├── rtc_config.py            # Per-run RTC RunConfig (Pydantic + YAML)
│   ├── cslc_config.py
│   ├── disp_config.py
│   ├── dswx_config.py
│   └── dist_config.py
│
├── products/                    # Output format compliance
│   ├── __init__.py
│   ├── hdf5.py                  # CSLC + DISP HDF5 writer (OPERA spec)
│   ├── cog.py                   # COG GeoTIFF writer (RTC + DSWx + DIST)
│   └── spec.py                  # OPERA product spec constants + validators
│
├── validation/                  # Validation framework
│   ├── __init__.py
│   ├── metrics.py               # RMSE, spatial r, bias, SSIM functions
│   ├── compare_opera.py         # Compare against OPERA N.Am. products
│   ├── compare_egms.py          # Compare against EGMS EU products
│   ├── compare_jrc.py           # Compare against JRC water products
│   └── report.py                # HTML/Markdown report generator
│
└── cli/                         # Entry points
    ├── __init__.py
    ├── app.py                   # typer root app
    ├── cmd_rtc.py               # rtc subcommand
    ├── cmd_cslc.py              # cslc subcommand
    ├── cmd_disp.py              # disp subcommand
    ├── cmd_dswx.py              # dswx subcommand
    ├── cmd_dist.py              # dist subcommand
    └── cmd_validate.py          # validate subcommand

tests/
├── unit/
│   ├── access/
│   ├── bursts/
│   ├── validation/
│   └── config/
├── integration/                 # Require credentials / network
│   ├── test_cdse_search.py
│   └── test_rtc_e2e.py
└── fixtures/                    # Small synthetic test data

docs/
scripts/
pyproject.toml                   # hatchling build; hatch-vcs versioning
environment.yml                  # conda-forge: isce3, gdal, dolphin, tophu, snaphu
```

### Structure Rationale

- **`access/`:** All I/O with external systems isolated here. Mock-friendly boundary for unit tests. Nothing else reaches out to the network directly.
- **`bursts/`:** Separated from `access/` because it owns persistent state (the EU SQLite DB). Build once, query many times.
- **`pipelines/`:** Each file is a thin orchestrator that sequences `access → wrappers → products`. No algorithm logic lives here.
- **`wrappers/`:** Adapter layer that translates subsideo's domain models into the conventions of upstream libraries (ISCE3, dolphin, MintPy). Isolates breaking changes in upstream from subsideo's API.
- **`config/`:** Pydantic models per pipeline. Global settings (credentials, paths) in `settings.py`; per-run configs in individual files. Enables YAML serialisation of configs for reproducibility (dolphin's `YamlModel` pattern).
- **`products/`:** Keeps OPERA spec compliance in one place. Every pipeline imports from here rather than writing HDF5/COG independently.
- **`validation/`:** Completely decoupled from pipelines. Takes paths to output files and reference files; computes metrics. Testable in isolation.
- **`cli/`:** Thin. No logic — only argument parsing, config loading, and pipeline invocation.

---

## Architectural Patterns

### Pattern 1: Config-Driven Pipelines (OPERA/dolphin pattern)

**What:** Each pipeline is parameterised by a Pydantic model that can be serialised to/from YAML. The config is the single source of truth for a run; it is saved to the output directory for reproducibility.

**When to use:** All pipelines. This is the established pattern across ISCE3 (`rtc_s1.py <yaml>`), dolphin (`dolphin run <yaml>`), and disp-s1. Subsideo should follow it exactly.

**Trade-offs:** Adds upfront schema design work, but makes runs fully reproducible and testable with fixture configs.

**Example:**
```python
# config/rtc_config.py
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Annotated

class RTCRunConfig(BaseModel):
    burst_id: str
    sensing_start: str
    sensing_end: str
    output_dir: Path
    dem_path: Path | None = None        # None → auto-download GLO-30
    orbit_path: Path | None = None      # None → auto-download POE
    output_posting_m: float = 30.0

    def to_yaml(self, path: Path) -> None: ...
    @classmethod
    def from_yaml(cls, path: Path) -> "RTCRunConfig": ...
```

### Pattern 2: Ancillary Resolver (fetch-once, cache-locally)

**What:** Before any algorithm wrapper runs, a resolver stage looks up and downloads all ancillary inputs (DEM, orbit, ionosphere) keyed by burst ID + date. Results are cached under a configurable `SUBSIDEO_CACHE_DIR`. Pipelines pass resolved paths, never downloading inside wrappers.

**When to use:** All pipelines. Prevents redundant downloads when running many bursts in sequence.

**Trade-offs:** Requires a well-defined cache directory structure. Cache invalidation is time-based (orbits) or version-based (DEM).

**Example:**
```python
# pipelines/rtc.py
def run_rtc(cfg: RTCRunConfig) -> Path:
    dem   = resolve_dem(cfg.burst_id, cache_dir=CACHE)
    orbit = resolve_orbit(cfg.sensing_start, cache_dir=CACHE)
    rtc_wrapper = ISCERTCWrapper(cfg, dem=dem, orbit=orbit)
    product_path = rtc_wrapper.run()
    return product_path
```

### Pattern 3: Wrapper Isolation (thin adapter, no logic)

**What:** Each wrapper file (`wrappers/isce3.py`, `wrappers/dolphin.py`, etc.) is a thin adapter that translates subsideo domain objects into the upstream library's calling convention. No science logic lives in wrappers — only translation and invocation.

**When to use:** Every external algorithm dependency. Protects subsideo's API from upstream changes.

**Trade-offs:** Extra indirection layer. Pays off when upstream APIs change (e.g., dolphin `WorkflowConfig` field renames).

### Pattern 4: Validation as a Standalone Pass

**What:** Validation never runs inside a pipeline. It is a separate CLI subcommand (`validate`) that accepts paths to output files and reference files. Metric functions are pure functions over numpy arrays.

**When to use:** After any pipeline run. Can be run without re-running the pipeline.

**Trade-offs:** Requires output files to be complete before validation. This is correct — never validate partial outputs.

---

## Data Flow

### RTC-S1 Flow

```
CLI: subsideo rtc --burst-id T123-456789-IW2 --date 2024-06-01
    ↓
RTCRunConfig (Pydantic, from CLI args + optional YAML)
    ↓
Ancillary Resolver
    ├── CDSE accessor → S1 SLC burst (s3://eodata/...)
    ├── DEM manager → GLO-30 tiles stitched to burst bbox
    └── Orbit fetcher → POE .EOF file
    ↓
ISCERTCWrapper.run()
    └── isce3.geocode.geocode_slc() + isce3.antenna.rtc_bilinear()
    ↓
Product writer → COG GeoTIFF (30m UTM, OPERA spec)
    ↓
Output: <output_dir>/RTC-S1/<burst_id>/<date>/
```

### CSLC-S1 Flow

```
CLI: subsideo cslc --burst-id T123-456789-IW2 --date 2024-06-01
    ↓
CSLCRunConfig
    ↓
Ancillary Resolver
    ├── CDSE accessor → S1 SLC burst
    ├── DEM manager → GLO-30
    └── Orbit fetcher → POE
    ↓
ISCECSLCWrapper.run()
    └── isce3 burst coregistration → geocoded SLC HDF5
    ↓
Product writer → HDF5 (OPERA CSLC-S1 spec)
    ↓
Output: <output_dir>/CSLC-S1/<burst_id>/<date>/
```

### DISP-S1 Flow (most complex)

```
N × CSLC-S1 HDF5 products (from CSLC pipeline or CDSE/ASF)
    ↓
DISPRunConfig (frame_id, date_range, reference_date)
    ↓
dolphin wrapper
    ├── WorkflowConfig built from DISPRunConfig
    ├── PS/DS selection → compressed SLCs
    ├── Mini-stack phase linking (MiniStackPlanner)
    ├── Interferogram network selection
    └── tophu tiled unwrapping (per tile, multi-resolution)
    ↓
dolphin outputs: unwrapped phase HDF5 stack
    ↓
MintPy wrapper
    ├── Generate smallbaselineApp.cfg from DISPRunConfig
    ├── load_data → ifgramStack.h5
    ├── modify_network, reference_point
    ├── invert_network → time series
    ├── correct_troposphere (ERA5 via PyAPS + ECMWF CDS API)
    └── estimate velocity
    ↓
Product writer → DISP-S1 HDF5 (OPERA spec: displacement, velocity, coherence)
    ↓
Output: <output_dir>/DISP-S1/<frame_id>/<date_range>/
```

### Validation Flow

```
CLI: subsideo validate --product RTC --output <path> --reference <opera_path>
    ↓
ValidationConfig (product type, output path, reference path, metrics)
    ↓
Resampler: align output to reference grid (rasterio warp)
    ↓
Metric functions (pure numpy):
    ├── RMSE, bias
    ├── Pearson r (spatial correlation)
    └── SSIM
    ↓
Report generator (jinja2 template + matplotlib figures)
    ↓
Output: validation_report.html + validation_metrics.json
```

### Key Data Flows Summary

1. **Burst ID is the primary key** — every S1 pipeline operation is keyed on (burst_id, sensing_date). The EU burst DB maps AOI → burst IDs before any I/O starts.
2. **Ancillary data flows into wrappers as paths** — wrappers never fetch; they only consume paths handed to them by the orchestration layer.
3. **CSLC feeds DISP** — the CSLC pipeline is a prerequisite for DISP. Either run subsideo's CSLC pipeline first, or point DISP at externally sourced CSLC HDF5 files.
4. **RTC feeds DIST** — DIST-S1 consumes a time series of RTC-S1 COG products via `distmetrics` / `dist-s1` library.
5. **dolphin outputs feed MintPy** — dolphin produces unwrapped phase stacks that MintPy ingests for time-series inversion.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| CDSE STAC API | `pystac_client.Client.open("https://catalogue.dataspace.copernicus.eu/stac")` | OData also available; STAC preferred for standardisation |
| CDSE S3 | `boto3` with `endpoint_url="https://eodata.dataspace.copernicus.eu"` | Not standard AWS — custom endpoint required; credentials from CDSE portal |
| ASF DAAC | `earthaccess` library; Earthdata login token | Used only for OPERA N.Am. reference product download (validation) |
| GLO-30 DEM | `dem-stitcher` PyPI package or direct `s3://copernicus-dem-30m/` | AWS Open Data bucket; no auth required |
| ESA Orbit Server | HTTP GET `https://step.esa.int/auxdata/orbits/...` | POE (precise orbit) ~2 week lag; ROE (restituted) near-real-time |
| IONEX (TEC) | HTTP from CDDIS `https://cddis.nasa.gov/archive/gnss/products/ionex/` | Earthdata auth required |
| ECMWF CDS API | `cdsapi` Python client; `~/.cdsapirc` key | ERA5 tropospheric correction for MintPy; separate API key |
| EGMS | REST API `https://egms.land.copernicus.eu/` | EU-level InSAR ground motion product; used for DISP validation |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| CLI → pipeline | Function call with config object | CLI constructs config, calls `run_*()` function |
| pipeline → access | Function calls returning `Path` objects | Access layer returns local file paths after download |
| pipeline → wrappers | Function/class calls with config + paths | Wrappers are called after all ancillary inputs are resolved |
| wrappers → upstream libs | Direct Python import (`import isce3`, `import dolphin`) | Never subprocess — use Python APIs |
| dolphin → tophu | dolphin calls tophu via `unwrap_method` config field | Configured in dolphin's `WorkflowConfig.unwrap_options` |
| dolphin → MintPy | File-based: dolphin writes HDF5; MintPy wrapper reads them | Decoupled by filesystem; generates MintPy `.cfg` from template |
| pipelines → product writers | Function calls with numpy arrays + metadata | Writers own all OPERA-spec compliance |
| pipelines → validation | NOT called from pipelines — only from CLI `validate` | Validation is always a separate post-processing step |

---

## Suggested Build Order (Phase Dependencies)

The component graph has a strict dependency ordering that should drive phase sequencing:

```
1. Data access layer (CDSE + ancillaries)
        ↓
2. EU burst DB (required by all S1 pipelines for burst resolution)
        ↓
3. RTC pipeline (simplest ISCE3 workflow; validates access + wrappers)
        ↓
4. CSLC pipeline (depends on RTC patterns; feeds DISP)
        ↓
5. DISP pipeline (depends on CSLC outputs; most complex: dolphin + tophu + MintPy)
        ↓
6. DSWx pipeline (independent of S1 stack; Sentinel-2 L2A + CDSE)
        ↓
7. DIST pipeline (depends on RTC time series)
        ↓
8. Validation framework (depends on all pipelines producing outputs)
```

**Rationale:**
- RTC before CSLC: RTC is the simplest ISCE3 workflow (single-pass). Getting it right validates the full access → wrapper → writer stack cheaply.
- CSLC before DISP: DISP requires a time stack of CSLC HDF5 inputs. CSLC must be stable and spec-compliant before DISP can be tested end-to-end.
- DSWx is independent: No S1 dependency. Can be built in parallel with CSLC if needed.
- DIST depends on RTC time series: Can only be built after at least a minimal RTC pipeline exists.
- Validation last: Needs products to exist, but can be built incrementally alongside pipelines (unit-testable in isolation from day one).

---

## Anti-Patterns

### Anti-Pattern 1: Subprocess Calls to Algorithm Tools

**What people do:** `subprocess.run(["rtc_s1.py", "config.yaml"])` from within the library.

**Why it's wrong:** Hard to test; fragile to PATH/env changes; loses structured error handling; makes the library unimportable without a full conda environment being active.

**Do this instead:** Import and call ISCE3, dolphin, and MintPy via their Python APIs. Subprocess is acceptable only for SNAPHU (no Python API) or as a last resort.

### Anti-Pattern 2: Mixing Data Access with Processing Logic

**What people do:** Downloading a file inside an ISCE3 wrapper function when the expected path is missing.

**Why it's wrong:** Download failures become processing failures with confusing error messages. Retries and caching get duplicated. Pipelines become non-deterministic.

**Do this instead:** All downloads happen in the `access/` layer before any wrapper is called. Wrappers should `assert path.exists()` at their entry point.

### Anti-Pattern 3: Hardcoded UTM Zones

**What people do:** Default to EPSG:32632 (UTM 32N) throughout EU processing.

**Why it's wrong:** EU spans UTM zones 28N–38N. Bursts near zone boundaries appear in two zones. AOIs that cross zone boundaries silently produce misregistered products.

**Do this instead:** Derive the UTM EPSG from the burst/frame database per burst. The `burst_db` schema stores EPSG per frame. Pass it explicitly through all geo-coding steps.

### Anti-Pattern 4: Running Validation Inside Pipelines

**What people do:** Call `compute_rmse(output, reference)` at the end of `run_rtc()`.

**Why it's wrong:** Validation requires reference products that may not be present (different credentials, offline). Mixing concerns makes pipelines fail for reasons unrelated to processing.

**Do this instead:** Validation is always a separate CLI step. Pipelines only produce outputs; they never consume reference data.

### Anti-Pattern 5: Global Credential State

**What people do:** Set CDSE S3 credentials in module-level global variables.

**Why it's wrong:** Makes the library untest-able without live credentials; creates hidden coupling between modules.

**Do this instead:** Pass credentials as part of the Pydantic `Settings` object. Inject into access layer functions. Use `pytest-mock` or `moto` to mock in tests.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Single AOI / few bursts | In-process sequential pipeline execution is fine. No parallelism needed. |
| Region-scale (100s of bursts) | Parallelise at burst level using `concurrent.futures.ProcessPoolExecutor`. dolphin's `MiniStackPlanner` handles internal batch dispatch. |
| Country/EU-scale (10k+ bursts) | Extract CLI as job generator; submit jobs to HPC scheduler (SLURM) or cloud batch. This is out of scope for v1 per PROJECT.md. |

**First bottleneck:** CDSE S3 download throughput. Mitigate with concurrent downloads (boto3 multipart, concurrent burst downloads) and local caching.

**Second bottleneck:** dolphin phase linking memory for large frame stacks. Mitigate by leveraging dolphin's mini-stack batching and `MiniStackPlanner`.

**Third bottleneck:** MintPy ERA5 download rate. ERA5 data retrieval from CDS API is slow (queued). Cache ERA5 grids by date and spatial extent.

---

## Sources

- [ISCE3 GitHub — isce-framework/isce3](https://github.com/isce-framework/isce3) — MEDIUM confidence (README + conda-forge package verified)
- [dolphin GitHub — isce-framework/dolphin](https://github.com/isce-framework/dolphin) — HIGH confidence (JOSS paper + official repo structure verified)
- [dolphin JOSS paper](https://joss.theoj.org/papers/10.21105/joss.06997) — HIGH confidence (peer-reviewed 2024)
- [opera-adt/burst_db — Burst and Frame database](https://github.com/opera-adt/burst_db) — HIGH confidence (official JPL repo)
- [opera-adt/RTC](https://github.com/opera-adt/RTC) — MEDIUM confidence (README structure verified)
- [opera-adt/disp-s1](https://github.com/opera-adt/disp-s1) — MEDIUM confidence (README structure verified)
- [opera-adt/dist-s1](https://github.com/opera-adt/dist-s1) — HIGH confidence (PyPI published + OPERA documentation)
- [opera-adt/opera-utils](https://github.com/opera-adt/opera-utils) — HIGH confidence (official repo + README verified)
- [MintPy GitHub — insarlab/MintPy](https://github.com/insarlab/MintPy) — HIGH confidence (official repo; smallbaselineApp steps verified)
- [CDSE APIs documentation](https://documentation.dataspace.copernicus.eu/APIs.html) — HIGH confidence (official Copernicus documentation)
- [Copernicus DEM GLO-30 on AWS](https://registry.opendata.aws/copernicus-dem/) — HIGH confidence (AWS Open Data registry)
- [OPERA CSLC-S1 ATBD](https://cumulus.asf.earthdatacloud.nasa.gov/PUBLIC/DATA/OPERA/OPERA_CSLC-S1_ATBD_D-108752_Initial_2024-06-24_signed.pdf) — HIGH confidence (official JPL Algorithm Theoretical Basis Document)

---
*Architecture research for: SAR/InSAR geospatial processing library (subsideo)*
*Researched: 2026-04-05*
