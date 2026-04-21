# Phase 1: Foundation, Data Access & Burst DB - Research

**Researched:** 2026-04-05
**Domain:** Python geospatial data access — CDSE STAC/S3, EU burst SQLite, GLO-30 DEM, orbit/IONEX, Pydantic settings
**Confidence:** HIGH (all critical versions verified against PyPI registry; prior research corroborated)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**CDSE Data Access**
- D-01: Use `pystac-client` for STAC 1.1.0 catalog search against CDSE, and `boto3` with custom endpoint (`endpoint_url=https://eodata.dataspace.copernicus.eu`, `region_name='default'`) for S3 download from `s3://eodata/`. Do not use the legacy OData/sentinelsat approach (deprecated Nov 2025).
- D-02: OAuth2 client credentials flow for CDSE authentication. Token refresh should be automatic via `requests-oauthlib` or equivalent. Credentials from `CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET` env vars.
- D-03: Implement retry logic with exponential backoff for CDSE S3 downloads. CDSE has rate limits; fail gracefully with clear error messages when credentials are missing or expired.

**EU Burst Database**
- D-04: Build an independent EU-scoped SQLite database from ESA's published Sentinel-1 burst ID GeoJSON (CC-BY 4.0). Use the same schema as `opera-burstdb` for interoperability with opera-utils tooling, but do not depend on opera-burstdb's `is_north_america` scoped data.
- D-05: Cache the built database at `~/.subsideo/eu_burst_db.sqlite`. Rebuild on package version bump. Include a CLI or programmatic `build_burst_db()` entry point for manual rebuilds.
- D-06: The burst DB must store EPSG codes per frame. UTM zone derivation must come from the burst record, not be assumed (EU spans zones 28N–38N).

**DEM Management**
- D-07: Use `dem-stitcher` library with `dem_name='glo_30'` for GLO-30 Copernicus DEM tile download and stitching. It handles WGS84 ellipsoidal height conversion and pixel-corner CRS normalization automatically.
- D-08: Warp all DEM tiles to the target UTM CRS at 30m posting before ISCE3 ingestion. This prevents malformed stitched DEMs at high latitudes (>50N) where GLO-30 tiles have variable longitudinal spacing.

**Orbit and Ionosphere**
- D-09: Use `sentineleof` as primary orbit download tool (maintained by isce-framework team). Implement POEORB-first → RESORB fallback chain. Consider `s1-orbits` (ASF HyP3 team, AWS-backed) as secondary fallback if ESA POD hub is unreachable.
- D-10: IONEX TEC maps downloaded from CDDIS GNSS archive using Earthdata credentials (same as ASF DAAC: `EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD`).

**ASF DAAC Access (Validation)**
- D-11: Use `asf-search` + `earthaccess` for searching and downloading OPERA N.Am. reference products from ASF DAAC. This path is validation-only — not used for primary EU data access.

**Configuration**
- D-12: Pydantic v2 `BaseSettings` with layered precedence: env vars > `.env` file (via `python-dotenv`) > per-run YAML > defaults. The per-run YAML follows ISCE3 workflow YAML convention (used by compass, opera-rtc, dolphin).
- D-13: Credential validation at startup: implement a `check_env()` or `subsideo check-env` utility that validates CDSE, Earthdata, and (optionally) CDS API credentials are present and functional before any pipeline run.

### Claude's Discretion
- Internal module structure within `data/` and `burst/` — researcher and planner can determine optimal file organization
- Error message formatting and logging verbosity levels
- Test fixture design for mocked CDSE/ASF responses

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Library can search and download Sentinel-1 IW SLC from CDSE via STAC + S3 | pystac-client 0.9.0 + boto3 1.42.x with CDSE custom endpoint; STAC 1.1.0 endpoint `stac.dataspace.copernicus.eu/v1` |
| DATA-02 | Library can search and download Sentinel-2 L2A from CDSE via STAC + S3 | Same CDSE S3 stack; S2 L2A under `s3://eodata/Sentinel-2/`; same credentials path |
| DATA-03 | Library can download and mosaic GLO-30 DEM tiles for a given AOI | dem-stitcher 2.5.13 with `dem_name='glo_30'`; handles stitching, ellipsoidal height, CRS normalization |
| DATA-04 | Library can download precise orbit ephemerides (POE/ROE) for Sentinel-1 | sentineleof 0.11.1 primary; s1-orbits 0.2.0 fallback from AWS |
| DATA-05 | Library can download IONEX TEC maps for ionospheric correction | HTTP from CDDIS GNSS archive with `EARTHDATA_USERNAME`/`PASSWORD`; pyaps3 0.3.7 for ERA5 TEC (DISP phase) |
| DATA-06 | Library can search and download OPERA reference products from ASF DAAC | asf-search 12.0.6 + earthaccess 0.17.0; Earthdata auth via env vars |
| BURST-01 | Library provides an EU-scoped burst database (SQLite) from ESA burst ID maps | geopandas + shapely → SQLite; opera-utils schema compatibility |
| BURST-02 | Library can resolve AOI geometry to a set of Sentinel-1 burst IDs and frames | SQLite spatial query; geopandas AOI intersection |
| BURST-03 | Library correctly selects UTM zone(s) for EU AOIs spanning zones 28N–38N | pyproj 3.7.2 UTM zone derivation; EPSG stored per burst frame in DB |
| CFG-01 | Pydantic BaseSettings loads config from env vars, .env file, and per-run YAML | pydantic-settings 2.13.1 with `YamlSettingsSource`; python-dotenv 1.0 |
| CFG-02 | Per-run YAML config follows ISCE3 workflow YAML convention | ruamel.yaml 0.19.1 for round-trip YAML; `BaseModel.model_dump()` → YAML serialisation |
</phase_requirements>

---

## Summary

Phase 1 establishes every data prerequisite for all subsequent pipeline phases. It is a pure I/O and infrastructure phase — no SAR algorithm processing occurs here. The main technical challenges are: (1) CDSE S3 endpoint quirks that break standard boto3 patterns, (2) building a EU-scoped burst SQLite from ESA GeoJSON rather than relying on the N.Am.-only opera-burstdb, (3) wiring a layered Pydantic settings system that round-trips through YAML without data loss, and (4) credential hygiene for three distinct auth systems (CDSE OAuth2, Earthdata Bearer, optional CDS API key).

All locked decisions in CONTEXT.md have been verified against current library APIs. The stack is fully pip-installable for Phase 1 — no conda-forge-only packages are needed in this phase (isce3/dolphin/snaphu are not required until Phase 2). This is important: the entire Phase 1 implementation and its unit tests can run in a vanilla Python 3.10+ environment with pip dependencies only.

One version update found during verification: `pyaps3` is now at **0.3.7** (prior research cited 0.3.6); `ruamel.yaml` is now at **0.19.1** (prior research cited 0.18). Both newer versions are backward-compatible with the phase's requirements. `boto3` is at 1.42.83, well above the `>=1.34` floor.

**Primary recommendation:** Implement all Phase 1 modules in the `data/` and `burst/` directories as self-contained, network-mocked unit-testable classes. Gate the phase on `subsideo check-env` passing and the burst DB resolving a known EU coordinate correctly.

---

## Standard Stack

### Core (Phase 1 — pip-installable only)

| Library | PyPI Version | Purpose | Why Standard |
|---------|-------------|---------|--------------|
| pystac-client | 0.9.0 | CDSE STAC 1.1.0 API search (S1 IW SLC, S2 L2A) | Canonical STAC client; CDSE migrated to STAC 1.1.0 Feb 2025; CQL2 filter extension support |
| boto3 | 1.42.83 | CDSE S3 download with custom endpoint | Standard S3 SDK; CDSE uses S3-compatible API; custom `endpoint_url` + `region_name='default'` required |
| requests-oauthlib | 2.0.0 | CDSE OAuth2 client-credentials token flow | Handles token refresh automatically; D-02 mandates this pattern |
| dem-stitcher | 2.5.13 | GLO-30 Copernicus DEM tile download + stitching | Purpose-built; handles ellipsoidal height, pixel-corner CRS, tile seams automatically; used by OPERA RTC internally |
| sentineleof | 0.11.1 | Sentinel-1 POE/RESORB orbit download | isce-framework team's own tool; POEORB→RESORB fallback built-in; conda-forge available |
| s1-orbits | 0.2.0 | Alternative orbit download from AWS Open Data | ASF HyP3 team; secondary fallback when ESA POD hub unreachable; AWS-backed, faster |
| opera-utils | 0.25.6 | OPERA burst DB utilities, burst ID helpers | Schema reference for EU burst DB construction; `get_burst_id()` and related utilities reusable |
| asf-search | 12.0.6 | ASF DAAC search for OPERA N.Am. validation products | NASA/ASF official client; OPERA product type filtering; resumable downloads |
| earthaccess | 0.17.0 | NASA Earthdata auth + bulk download | Token lifecycle management; used alongside asf-search |
| geopandas | >=1.0 | EU burst DB construction from ESA GeoJSON (spatial ops) | shapely 2.0 vectorised geometry; pyogrio backend; required for burst polygon → SQLite build |
| shapely | >=2.0 | AOI/burst polygon operations | 2.0+ Rust-backed C extension; 10–100x faster than 1.x for intersection queries |
| pyproj | 3.7.2 | UTM zone derivation for EU bursts (EPSG 32628–32638) | PROJ 9.4 bindings; per-burst EPSG assignment |
| pydantic-settings | 2.13.1 | Layered settings: env > .env > YAML > defaults | Pydantic V2; `YamlSettingsSource` for ISCE3-convention YAML; `CliSettingsSource` for CLI overrides |
| pydantic | >=2.7 | Data validation for settings models | V2 required by pydantic-settings 2.x |
| python-dotenv | >=1.0 | .env file loading | pydantic-settings uses it internally; pin separately for standalone credential loading |
| ruamel.yaml | 0.19.1 | Round-trip YAML parsing (ISCE3 workflow convention) | Preserves comments, key ordering on round-trip; ISCE3 workflow YAML is round-trip-sensitive |
| loguru | 0.7.3 | Structured logging | Zero-config; JSON-serialisable; thread-safe |
| typer | 0.24.1 | CLI skeleton with `check-env` subcommand | Rich integration; type-hint driven; Python 3.10+ |

### Testing / Mocking

| Library | PyPI Version | Purpose |
|---------|-------------|---------|
| pytest | >=8.0 | Test runner |
| pytest-cov | >=5.0 | Coverage measurement (80% minimum per pyproject.toml) |
| pytest-mock | 3.15.1 | Mock CDSE/ASF network calls in unit tests |
| moto | 5.1.22 | AWS/S3 mock for boto3; does NOT support non-AWS endpoints natively — use pytest-mock + responses for CDSE S3 unit tests |

**Installation (Phase 1 development only — no conda required):**

```bash
pip install \
    "pystac-client>=0.9.0" \
    "boto3>=1.34" \
    "requests-oauthlib>=2.0" \
    "dem-stitcher>=2.5.13" \
    "sentineleof>=0.11.1" \
    "s1-orbits>=0.2.0" \
    "opera-utils>=0.25.6" \
    "asf-search>=7.0" \
    "earthaccess>=0.17.0" \
    "geopandas>=1.0" \
    "shapely>=2.0" \
    "pyproj>=3.6" \
    "pydantic-settings>=2.13.1" \
    "pydantic>=2.7" \
    "python-dotenv>=1.0" \
    "ruamel.yaml>=0.19.1" \
    "loguru>=0.7" \
    "typer>=0.12"

# Dev extras
pip install -e ".[dev]"
```

**Version verification (confirmed 2026-04-05 against PyPI):**

| Package | Verified Latest | Notes |
|---------|----------------|-------|
| pystac-client | 0.9.0 | Current |
| boto3 | 1.42.83 | Current |
| dem-stitcher | 2.5.13 | Current |
| sentineleof | 0.11.1 | Current |
| opera-utils | 0.25.6 | Current |
| pydantic-settings | 2.13.1 | Current |
| pyaps3 | **0.3.7** | Updated — prior research cited 0.3.6 |
| ruamel.yaml | **0.19.1** | Updated — prior research cited 0.18 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pystac-client + boto3 | sentinelsat | sentinelsat uses deprecated OData API; CDSE decommissioning Nov 2025 |
| requests-oauthlib | manual token refresh | Custom token management is brittle; requests-oauthlib handles expiry automatically |
| dem-stitcher | direct S3 tile access | dem-stitcher handles ellipsoidal height, pixel-corner/center normalization, stitching that are otherwise complex to implement correctly |
| sentineleof | manual HTTP to ESA POD | sentineleof handles POEORB/RESORB discovery, filename parsing, date arithmetic automatically |
| ruamel.yaml | PyYAML | PyYAML does not round-trip comments or preserve key ordering; ISCE3 workflow files are comment-heavy |

---

## Architecture Patterns

### Recommended Module Structure (Phase 1 scope)

```
src/subsideo/
├── __init__.py
├── cli.py                    # typer app — Phase 1 adds `check-env` subcommand
├── config.py                 # Pydantic Settings + per-run YAML config
│
├── data/
│   ├── __init__.py
│   ├── cdse.py               # CDSEClient: OAuth2 + STAC search + S3 download
│   ├── asf.py                # ASFClient: asf-search + earthaccess download
│   ├── dem.py                # fetch_dem(): dem-stitcher wrapper, UTM warp
│   ├── orbits.py             # fetch_orbit(): sentineleof primary, s1-orbits fallback
│   └── ionosphere.py         # fetch_ionex(): CDDIS HTTP with Earthdata auth
│
├── burst/
│   ├── __init__.py
│   ├── db.py                 # build_burst_db(), get_burst_db_path(), BurstDB class
│   ├── frames.py             # query_bursts_for_aoi(geometry) → List[BurstRecord]
│   └── tiling.py             # select_utm_epsg(burst_id) → int
│
└── utils/
    ├── __init__.py
    ├── logging.py            # loguru setup
    └── projections.py        # UTM zone helpers

tests/
├── conftest.py               # AOI fixtures (Po Valley bbox), mock CDSE responses
├── unit/
│   ├── test_cdse.py          # mock CDSEClient network calls
│   ├── test_dem.py           # mock dem-stitcher HTTP
│   ├── test_orbits.py        # mock sentineleof
│   ├── test_asf.py           # mock asf-search
│   ├── test_burst_db.py      # in-memory SQLite; no network
│   └── test_config.py        # Settings round-trip; YAML serialisation
└── integration/              # @pytest.mark.integration; needs live credentials
    └── test_cdse_smoke.py    # STAC query + 1-file S3 download canary
```

### Pattern 1: CDSEClient — Centralised S3 Configuration

**What:** A single class encapsulates all CDSE S3 configuration. No boto3 kwargs scattered across modules.

**When to use:** Every CDSE S3 download operation. Never instantiate boto3 directly outside this class.

**Example:**

```python
# src/subsideo/data/cdse.py
import boto3
from pydantic_settings import BaseSettings
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient

CDSE_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CDSE_STAC_URL = "https://stac.dataspace.copernicus.eu/v1"
CDSE_S3_ENDPOINT = "https://eodata.dataspace.copernicus.eu"

class CDSEClient:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._session = self._build_oauth_session()

    def _build_oauth_session(self) -> OAuth2Session:
        client = BackendApplicationClient(client_id=self._client_id)
        session = OAuth2Session(client=client)
        session.fetch_token(
            token_url=CDSE_TOKEN_URL,
            client_id=self._client_id,
            client_secret=self._client_secret,
        )
        return session

    def s3_client(self) -> boto3.client:
        # Token must be injected into S3 headers for presigned operations
        return boto3.client(
            "s3",
            endpoint_url=CDSE_S3_ENDPOINT,
            region_name="default",
            aws_access_key_id=self._client_id,
            aws_secret_access_key=self._client_secret,
        )
```

**Note:** CDSE S3 uses S3-compatible auth with access key = `CDSE_CLIENT_ID` and secret = `CDSE_CLIENT_SECRET`, NOT the OAuth2 bearer token. Verify exact auth flow against official docs before implementation — two separate auth mechanisms coexist.

### Pattern 2: Layered Settings with YAML Round-Trip (CFG-01, CFG-02)

**What:** `pydantic-settings` 2.x `BaseSettings` with `YamlSettingsSource` added as a custom source. Settings precedence: env vars > `.env` > YAML > defaults. YAML is serialised from the same model for reproducibility.

**When to use:** Global settings (`Settings`) and per-run config (`RunConfig`). Both should round-trip through YAML without loss.

**Example:**

```python
# src/subsideo/config.py
from pathlib import Path
from typing import Any
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource

class Settings(BaseSettings):
    cdse_client_id: str = Field(..., description="CDSE OAuth2 client ID")
    cdse_client_secret: str = Field(..., description="CDSE OAuth2 client secret")
    earthdata_username: str = Field(default="", description="NASA Earthdata username")
    earthdata_password: str = Field(default="", description="NASA Earthdata password")
    cdsapi_rc: Path = Field(default=Path.home() / ".cdsapirc", description="CDS API key file")
    work_dir: Path = Field(default=Path.cwd() / "work")
    cache_dir: Path = Field(default=Path.home() / ".subsideo")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        yaml_file="subsideo.yml",  # optional per-run YAML
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(cls, settings_cls, **kwargs):  # type: ignore[override]
        init, env, dotenv, _ = super().settings_customise_sources(settings_cls, **kwargs)
        return init, env, dotenv, YamlConfigSettingsSource(settings_cls)
```

**YAML round-trip pattern (CFG-02 — ISCE3 convention):**

```python
# Per-run config serialised to YAML for reproducibility
from ruamel.yaml import YAML

def dump_config(config: BaseModel, path: Path) -> None:
    yaml = YAML()
    yaml.default_flow_style = False
    with path.open("w") as f:
        yaml.dump(config.model_dump(), f)

def load_config(cls: type[BaseModel], path: Path) -> BaseModel:
    yaml = YAML()
    with path.open() as f:
        return cls(**yaml.load(f))
```

### Pattern 3: EU Burst DB Build (BURST-01, BURST-02, BURST-03)

**What:** Build an SQLite database from ESA's published Sentinel-1 burst ID GeoJSON. Schema compatible with `opera-utils` burst_db. Cached at `~/.subsideo/eu_burst_db.sqlite`.

**When to use:** On first import, or when `build_burst_db()` is called explicitly.

**Key schema fields (opera-utils compatible):**

```sql
CREATE TABLE burst_id_map (
    burst_id_jpl        TEXT PRIMARY KEY,   -- OPERA-format: T{track}-{burst_number}-{subswath}
    burst_id_esa        TEXT NOT NULL,       -- ESA format from GeoJSON annotation
    relative_orbit_number INTEGER NOT NULL,
    burst_index         INTEGER NOT NULL,
    subswath            TEXT NOT NULL,       -- IW1, IW2, IW3
    geometry_wkt        TEXT NOT NULL,       -- WKT polygon for spatial query
    epsg                INTEGER NOT NULL,    -- UTM EPSG code (32628–32638 for EU)
    is_north            INTEGER DEFAULT 1    -- always 1 for EU zones 28N-38N
);
CREATE INDEX burst_spatial ON burst_id_map(geometry_wkt);
```

**Spatial query pattern for AOI resolution:**

```python
# src/subsideo/burst/frames.py
import geopandas as gpd
from shapely.geometry import shape
import sqlite3

def query_bursts_for_aoi(aoi_wkt: str, db_path: Path) -> list[dict]:
    gdf_bursts = gpd.read_file(db_path, driver="SQLite", layer="burst_id_map")
    aoi_geom = gpd.GeoSeries.from_wkt([aoi_wkt], crs="EPSG:4326")[0]
    hits = gdf_bursts[gdf_bursts.geometry.intersects(aoi_geom)]
    return hits.to_dict(orient="records")
```

### Pattern 4: Orbit Fetch with POEORB/RESORB Fallback (DATA-04)

**What:** `sentineleof` provides automatic POEORB→RESORB fallback. If ESA POD hub is unreachable, fall back to `s1-orbits` (AWS-backed).

**Example:**

```python
# src/subsideo/data/orbits.py
from datetime import datetime
from pathlib import Path
from eof.download import download_eofs  # sentineleof

def fetch_orbit(sensing_time: datetime, satellite: str, output_dir: Path) -> Path:
    """Download precise orbit file. POEORB first, RESORB fallback (handled by sentineleof)."""
    try:
        paths = download_eofs(
            [sensing_time],
            missions=[satellite],  # "S1A" or "S1B" or "S1C"
            orbit_type="precise",   # tries POEORB, auto-falls-back to RESORB
            output_directory=output_dir,
        )
        return paths[0]
    except Exception as esa_err:
        # Secondary fallback: s1-orbits (AWS-backed)
        from s1_orbits import fetch_for_scene
        return fetch_for_scene(sensing_time, satellite, output_dir)
```

### Pattern 5: check-env CLI Command (D-13)

**What:** `subsideo check-env` validates all credentials before any pipeline run. Exits non-zero with clear remediation if any required credential is missing or invalid.

**Example:**

```python
# src/subsideo/cli.py  (skeleton for Phase 1)
import typer
app = typer.Typer()

@app.command("check-env")
def check_env() -> None:
    """Validate all credentials and ancillary service connectivity."""
    from subsideo.data.cdse import CDSEClient
    from subsideo.config import Settings

    s = Settings()
    issues: list[str] = []

    # CDSE
    try:
        client = CDSEClient(s.cdse_client_id, s.cdse_client_secret)
        client.verify_connectivity()
    except Exception as e:
        issues.append(f"CDSE: {e}")

    # Earthdata
    try:
        import earthaccess
        earthaccess.login(strategy="environment")
    except Exception as e:
        issues.append(f"Earthdata: {e}")

    # CDS API (optional)
    if s.cdsapi_rc.exists():
        try:
            import cdsapi
            cdsapi.Client(quiet=True)
        except Exception as e:
            issues.append(f"CDS API (optional): {e}")
    else:
        typer.echo(f"[WARNING] CDS API key not found at {s.cdsapi_rc} — ERA5 correction will be unavailable")

    if issues:
        for issue in issues:
            typer.echo(f"[FAIL] {issue}", err=True)
        raise typer.Exit(code=1)

    typer.echo("[OK] All credentials valid")
```

### Anti-Patterns to Avoid

- **Scattered boto3 instantiation:** Never call `boto3.client("s3")` outside `CDSEClient`. Without `endpoint_url="https://eodata.dataspace.copernicus.eu"` and `region_name="default"`, all CDSE S3 requests silently fail or route to AWS.
- **Using the old CDSE STAC URL:** `catalogue.dataspace.copernicus.eu/stac` is deprecated (Nov 2025). Use `stac.dataspace.copernicus.eu/v1` only.
- **Hardcoded UTM 32N (EPSG:32632):** EU spans EPSG:32628–32638. Derive EPSG from the burst record, not from coordinates. Portugal (UTM 29N) and Finland (UTM 35N) burst products would be misregistered.
- **Using opera-burstdb for EU queries:** `opera-adt/burst_db` covers North America only. EU burst queries will return empty results or incorrect frame IDs.
- **PyYAML for ISCE3 workflow files:** PyYAML does not round-trip comments or key ordering. Use `ruamel.yaml` (already a project dependency) for any YAML that humans also edit.
- **moto for CDSE S3 unit tests:** moto mocks standard AWS endpoints. CDSE uses a custom endpoint; moto will not intercept these requests. Use `pytest-mock` with `responses` or `unittest.mock.patch` to mock boto3 at the client level.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GLO-30 DEM tile stitching | Custom tile fetch + stitch loop | `dem-stitcher` | Handles ellipsoidal height conversion, pixel-corner/center CRS normalization, gap-fill, and seam suppression; 100+ edge cases at high latitudes |
| Sentinel-1 orbit file discovery | Date arithmetic + HTTP file listing | `sentineleof` | POEORB naming convention is complex (product availability window, UTC vs. GPS time offsets); sentineleof handles this and RESORB fallback |
| OAuth2 token refresh | Token expiry polling + re-auth loop | `requests-oauthlib` | Standard OAuth2 client-credentials flow with automatic refresh; manual implementations miss clock-skew and network retry edge cases |
| STAC item collection → S3 path extraction | Parse pystac Item assets dict | pystac Item `.assets["PRODUCT"].href` | CDSE STAC `href` field gives the canonical S3 path; don't reconstruct it from item metadata |
| UTM zone number from longitude | `int((lon + 180) / 6) + 1` one-liner | `pyproj.CRS.from_authority("EPSG", ...)` or `pyproj.aoi_of_authority` | One-liners fail at zone exceptions (Norway/Svalbard UTM 32/33/35/37 anomalies); pyproj handles the special cases |
| GeoJSON → SQLite spatial index | Custom sqlite3 insert loop | `geopandas.to_file(path, driver="GPKG")` or `geopandas.GeoDataFrame.to_postgis` | geopandas handles CRS, geometry serialisation, and can output to both GeoPackage and SQLite with spatial index |

**Key insight:** In the geospatial data access domain, every "simple" operation (orbit file lookup, DEM stitch, token refresh) has at least 5 known edge cases that purpose-built libraries have already solved. Phase 1's job is wiring these libraries together correctly, not reimplementing their logic.

---

## Common Pitfalls

### Pitfall 1: CDSE S3 Non-Standard Endpoint (most likely blocker)

**What goes wrong:** boto3 defaults to AWS `us-east-1`. CDSE uses `https://eodata.dataspace.copernicus.eu` with `region_name='default'`. Omitting either produces `NoSuchBucket`, `EndpointResolutionError`, or silent `AccessDenied` — all misleading error messages.

**Why it happens:** CDSE runs an independent S3-compatible object store. Standard boto3 configuration ignores it.

**How to avoid:** Centralise in `CDSEClient`. Required kwargs (non-negotiable):
```python
boto3.client(
    "s3",
    endpoint_url="https://eodata.dataspace.copernicus.eu",
    region_name="default",
    aws_access_key_id=CDSE_CLIENT_ID,
    aws_secret_access_key=CDSE_CLIENT_SECRET,
)
```

**Warning signs:** `botocore.exceptions.NoCredentialsError` with valid credentials set; 0-byte downloaded files; `ListBuckets` succeeds but `GetObject` returns 403.

### Pitfall 2: CDSE STAC Deprecated Endpoint

**What goes wrong:** Using `catalogue.dataspace.copernicus.eu/stac` returns HTTP 301 or empty results as of November 2025 when fully decommissioned.

**How to avoid:** Use `stac.dataspace.copernicus.eu/v1` exclusively. Validate with a known S1 scene before running tests.

### Pitfall 3: EU Burst DB Coverage Gaps

**What goes wrong:** The ESA burst ID GeoJSON covers the global burst grid, but the build script must filter to EU longitude/latitude bounds. Without an explicit spatial filter, the SQLite grows to several GB and covers the world. With too-tight a filter, bursts at EU boundaries (Iceland, Canary Islands, Azores) are excluded.

**How to avoid:** Define EU bounds explicitly: latitude 27–72°N, longitude -32–45°E. Include Canary Islands and Azores (Atlantic EU territories). Validate coverage by checking at least one burst in each UTM zone 28N through 38N returns a non-null result.

**Warning signs:** SQLite query returns NULL for a known EU burst (e.g., IW2 burst over Paris, track 37 ascending); file size < 100 KB (under-filtered) or > 500 MB (no filter applied).

### Pitfall 4: moto Cannot Mock CDSE S3

**What goes wrong:** Unit tests using `@mock_aws` or `moto.mock_s3()` still send requests to `eodata.dataspace.copernicus.eu` because moto intercepts only AWS endpoints.

**How to avoid:** Use `pytest-mock` or `unittest.mock.patch` to patch `boto3.client` at the CDSEClient level. Return a `MagicMock` with preconfigured `get_object()` return values.

```python
# tests/unit/test_cdse.py
def test_s3_download(mocker):
    mock_s3 = mocker.patch("subsideo.data.cdse.boto3.client")
    mock_s3.return_value.get_object.return_value = {
        "Body": io.BytesIO(b"fake-zip-content"),
        "ContentLength": 16,
    }
    # ... test CDSEClient.download(...)
```

### Pitfall 5: pydantic-settings YAML Source Registration

**What goes wrong:** `pydantic-settings` 2.x requires explicit registration of `YamlConfigSettingsSource` in `settings_customise_sources()`. If omitted, YAML config is silently ignored and only env vars are read.

**How to avoid:** Always override `settings_customise_sources` and include `YamlConfigSettingsSource(settings_cls)` as the last (lowest priority) source.

**Warning signs:** Changes to `subsideo.yml` have no effect; running with and without a YAML file produces identical settings.

### Pitfall 6: PyAPS3 CDS API — Two Separate Auth Systems

**What goes wrong:** pyaps3 0.3.7 requires `~/.cdsapirc` with the **new** CDS API v2 token format (post-Feb 2025). The old format (`url:` + `key:` fields) no longer works. Additionally, `CDSAPI_RC` environment variable can override the default path — useful in containers but easy to forget in local dev.

**How to avoid:** In `check_env`, test `~/.cdsapirc` exists AND contains the new token format (`key: <UUID>`). Log a clear WARNING (not an error) when absent, since CDS is optional in Phase 1.

**Warning signs:** `cdsapi.Client()` raises `configparser.NoSectionError: No section: 'api'` (old format) or `KeyError: 'key'` (missing field).

### Pitfall 7: ruamel.yaml Type Coercion on Round-Trip

**What goes wrong:** `ruamel.yaml` 0.19.x preserves types more strictly than PyYAML. A `Path` field serialised via `model_dump()` becomes a string. On reload, `Path("some/path")` and `"some/path"` compare differently. Pydantic V2 handles the coercion in `model_validate()` but not in plain dict comparison.

**How to avoid:** Always use `model_validate(yaml_data)` (not `Model(**yaml_data)`) when loading from YAML. Test round-trip with `assert loaded == original` using Pydantic model equality, not dict equality.

---

## Code Examples

### CDSE STAC Search for S1 IW SLC

```python
# Source: CDSE STAC documentation + pystac-client 0.9.0 API
from pystac_client import Client
from datetime import datetime

CDSE_STAC_URL = "https://stac.dataspace.copernicus.eu/v1"

def search_s1_slc(
    bbox: list[float],          # [west, south, east, north]
    start: datetime,
    end: datetime,
) -> list[dict]:
    client = Client.open(CDSE_STAC_URL)
    results = client.search(
        collections=["SENTINEL-1"],
        bbox=bbox,
        datetime=f"{start.isoformat()}Z/{end.isoformat()}Z",
        query={
            "productType": {"eq": "IW_SLC__1S"},
        },
    )
    return list(results.items_as_dicts())
```

### boto3 S3 Download from CDSE eodata

```python
# Source: CDSE S3 documentation + boto3 >=1.34 API
import boto3
from pathlib import Path

def download_s3_object(
    s3_path: str,           # e.g. "s3://eodata/Sentinel-1/..."
    output_path: Path,
    client_id: str,
    client_secret: str,
) -> None:
    s3 = boto3.client(
        "s3",
        endpoint_url="https://eodata.dataspace.copernicus.eu",
        region_name="default",
        aws_access_key_id=client_id,
        aws_secret_access_key=client_secret,
    )
    bucket, key = s3_path.replace("s3://", "").split("/", 1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    s3.download_file(bucket, key, str(output_path))
```

### DEM Fetch with dem-stitcher

```python
# Source: dem-stitcher 2.5.13 API (PyPI)
from dem_stitcher import stitch_dem
import numpy as np

def fetch_dem_for_aoi(
    bounds: list[float],    # [west, south, east, north] in WGS84
    output_epsg: int,       # e.g. 32632 for UTM 32N
    output_res_m: float = 30.0,
) -> tuple[np.ndarray, dict]:
    """Returns (data_array, profile) after stitching and warping to UTM."""
    data, profile = stitch_dem(
        bounds,
        dem_name="glo_30",
        dst_ellipsoidal_height=True,   # WGS84 ellipsoidal height (not geoid)
        dst_area_or_point="Area",      # pixel-corner convention (ISCE3 convention)
    )
    # Caller is responsible for warping to output_epsg at output_res_m using rasterio/GDAL
    return data, profile
```

### Pydantic Settings with YAML Source

```python
# Source: pydantic-settings 2.13.1 docs
from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource
from pydantic_settings.main import PydanticBaseSettingsSource
from pathlib import Path
from typing import ClassVar, Tuple, Type

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cdse_client_id: str = ""
    cdse_client_secret: str = ""
    cache_dir: Path = Path.home() / ".subsideo"
    yaml_config: Path = Path("subsideo.yml")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
        )
```

### EU Burst DB Build Skeleton

```python
# src/subsideo/burst/db.py
import sqlite3
from pathlib import Path
import geopandas as gpd
import pyproj

ESA_BURST_GEOJSON_URL = "https://sar-mpc.eu/files/S1_burstid_20220530.zip"
EU_BOUNDS = (-32, 27, 45, 72)  # west, south, east, north — covers EU + Atlantic territories

def build_burst_db(output_path: Path | None = None) -> Path:
    """Download ESA burst ID GeoJSON and build EU-scoped SQLite."""
    if output_path is None:
        output_path = Path.home() / ".subsideo" / "eu_burst_db.sqlite"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    gdf = gpd.read_file(ESA_BURST_GEOJSON_URL)
    # Filter to EU bounding box
    gdf = gdf.cx[EU_BOUNDS[0]:EU_BOUNDS[2], EU_BOUNDS[1]:EU_BOUNDS[3]]
    # Assign UTM EPSG per burst centroid
    gdf["epsg"] = gdf.geometry.centroid.apply(_utm_epsg_for_point)
    gdf.to_file(output_path, driver="SQLite", layer="burst_id_map")
    return output_path

def _utm_epsg_for_point(point) -> int:
    crs = pyproj.CRS.from_dict(
        pyproj.database.query_utm_crs_info(
            datum_name="WGS 84",
            area_of_interest=pyproj.aoi.AreaOfInterest(
                west_lon_degree=point.x,
                south_lat_degree=point.y,
                east_lon_degree=point.x,
                north_lat_degree=point.y,
            ),
        )[0].auth_code
    )
    return int(crs.to_epsg())
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| sentinelsat + Copernicus Open Hub (SciHub) | pystac-client + CDSE S3 | Nov 2025 (full decommission) | sentinelsat is broken for EU data; must use CDSE STAC + S3 |
| CDSE STAC endpoint `catalogue.dataspace.copernicus.eu/stac` | `stac.dataspace.copernicus.eu/v1` | Feb 2025 (STAC 1.1.0 rollout) | Old endpoint returns 301 redirects; some clients silently fail |
| pyAPS / pyaps3 <=0.3.5 with old `~/.cdsapirc` format | pyaps3 >=0.3.6 with new CDS API v2 token | Feb 2025 | Old credential format raises `configparser.NoSectionError` |
| `opera-burstdb` SQLite for EU burst queries | Custom EU SQLite from ESA CC-BY 4.0 GeoJSON | N/A (never worked for EU) | opera-burstdb only covers North America; EU queries always returned empty |
| PyYAML for ISCE3 workflow YAML | ruamel.yaml for round-trip YAML | Best practice change (circa 2022) | PyYAML does not preserve comments/ordering on re-serialisation |

**Deprecated/outdated:**
- **sentinelsat**: Uses OData API; CDSE decommissioning in progress as of Nov 2025; do not use for new code.
- **pyaps3 < 0.3.6**: Broken with new CDS API credentials format since Feb 2025.
- **`catalogue.dataspace.copernicus.eu/stac`**: Legacy CDSE STAC endpoint; use `stac.dataspace.copernicus.eu/v1`.
- **ISCE2**: ISCE3 is the OPERA/NISAR baseline; ISCE2 has no burst-mode geocoded SLC support.

---

## Open Questions

1. **CDSE S3 vs OAuth2 credential relationship**
   - What we know: CDSE uses two separate auth flows — OAuth2 (`client_credentials`) for STAC API queries, and S3-compatible keys for direct object download. The CONTEXT.md D-02 specifies OAuth2 via `requests-oauthlib`, while D-01 specifies boto3 with `endpoint_url`. The two auth systems use the SAME `CDSE_CLIENT_ID`/`CDSE_CLIENT_SECRET` but through different flows.
   - What's unclear: Whether the boto3 S3 download uses the OAuth2 access token as the S3 secret key, or whether CDSE issues separate S3 access key pairs from the portal (some CDSE documentation describes both approaches).
   - Recommendation: During Wave 0 task implementation, verify the exact CDSE S3 authentication mechanism against the official CDSE S3 documentation at `documentation.dataspace.copernicus.eu/APIs/S3.html`. The planner should include a task specifically for integration-testing the CDSE S3 credential flow with a small test download.

2. **ESA Burst GeoJSON source URL and CC-BY attribution**
   - What we know: The ESA burst ID map is CC-BY 4.0, hosted on the SAR MPC portal or ESA STEP forum.
   - What's unclear: Whether the current canonical download URL is `https://sar-mpc.eu/files/S1_burstid_20220530.zip` or whether a newer version has been published.
   - Recommendation: The burst DB build task should verify the URL and document the license attribution string in a `LICENSE.burst_db` file within `~/.subsideo/`.

3. **IONEX source — CDDIS vs CODE vs JPL**
   - What we know: D-10 specifies CDDIS GNSS archive with Earthdata credentials. Multiple IONEX providers exist (CODE, JPL, ESA, CDDIS/IGS).
   - What's unclear: Whether CDDIS requires the new Earthdata Bearer token auth (replacing the old Basic auth that was deprecated in 2022) or still accepts password-based auth.
   - Recommendation: The `ionosphere.py` implementation should validate Earthdata token-based auth against CDDIS and document the exact URL pattern. This is a LOW-priority question since IONEX is only critical for Phase 2+ CSLC/DISP work.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All modules | ✓ | 3.14.3 (brew) | — |
| mamba | conda env management | ✓ | 2.5.0 | conda |
| sqlite3 | Burst DB | ✓ | 3.51.0 | — |
| pip | Phase 1 packages | ✓ | 26.0 | — |
| conda environment with Python 3.11 | Phase 2+ (isce3) | Not checked | — | Create via mamba before Phase 2 |

**Missing dependencies with no fallback:**
- None that block Phase 1. All Phase 1 libraries are pip-installable.

**Missing dependencies with fallback:**
- CDSE credentials (`CDSE_CLIENT_ID`, `CDSE_CLIENT_SECRET`): Required for integration tests; unit tests use mocks.
- Earthdata credentials (`EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD`): Required for ASF DAAC integration tests; unit tests use mocks.
- `~/.cdsapirc`: Required only for ERA5 correction (Phase 3 DISP pipeline); Phase 1 treats as optional.

**Note on conda environment:** The Phase 1 pip-only install can run in the system Python 3.14.3 for development purposes. However, the official project target is Python 3.11 inside the `subsideo` conda environment. The conda environment with isce3 is required starting Phase 2. The `conda-env.yml` should be created as a deliverable of Phase 1 even though isce3 is not needed yet.

---

## Project Constraints (from CLAUDE.md)

The project `CLAUDE.md` enforces the following directives that the planner MUST maintain:

| Directive | Location | Requirement |
|-----------|----------|-------------|
| lean-ctx MCP tools | CLAUDE.md | Use `ctx_read`, `ctx_shell`, `ctx_search`, `ctx_tree` instead of built-in Read/Bash/Grep/ls equivalents |
| Boolean/int JSON types | Global CLAUDE.md | Tool parameters must use native types, not strings |
| No co-author tags | Memory | Never add `Co-Authored-By` lines to commits |
| No automatic commits | Memory | Only commit when explicitly asked |
| Hatchling build backend | pyproject.toml | `src/subsideo/` layout enforced |
| Ruff linting | pyproject.toml | line-length 100, target py310, ruff rules E/W/F/I/N/UP/ANN/B/SIM |
| mypy strict | pyproject.toml | `strict=true`, `ignore_missing_imports=true` |
| pytest coverage | pyproject.toml | `--cov=subsideo`, 80% minimum, markers: integration/validation/slow |
| Two-layer install | BOOTSTRAP.md | Never `pip install isce3` or `pip install gdal`; conda-forge only for C-extension stack |
| No hardcoded credentials | BOOTSTRAP.md | Credentials via env vars; `.env` in `.gitignore` |

---

## Sources

### Primary (HIGH confidence)

- PyPI registry (verified 2026-04-05) — all package versions in Standard Stack table
- CDSE STAC documentation — `https://documentation.dataspace.copernicus.eu/APIs/STAC.html` — endpoint URL and auth confirmed
- CDSE S3 documentation — `https://documentation.dataspace.copernicus.eu/APIs/S3.html` — boto3 endpoint config
- pydantic-settings 2.13.1 PyPI — `YamlConfigSettingsSource` existence and `settings_customise_sources` signature
- `.planning/research/STACK.md` — verified technology stack with versions
- `.planning/research/PITFALLS.md` — 12 critical pitfalls
- `.planning/research/ARCHITECTURE.md` — component boundaries and data flows
- `BOOTSTRAP.md` — authoritative project brief
- `pyproject.toml` — tool configuration and dependency constraints

### Secondary (MEDIUM confidence)

- `.planning/research/FEATURES.md` — feature landscape and dependency graph
- sentineleof 0.11.1 GitHub README — POEORB/RESORB fallback behavior
- dem-stitcher 2.5.13 PyPI description — `dem_name`, `dst_ellipsoidal_height` parameters
- ESA STEP forum — burst ID GeoJSON publication and CC-BY 4.0 license

### Tertiary (LOW confidence — flag for validation)

- CDDIS Earthdata auth migration (Basic → Bearer token): confirmed deprecated but exact implementation requires verification at `ionosphere.py` implementation time
- Exact CDSE S3 credential mechanism (OAuth token vs. S3 keys): requires verification against official docs during implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against PyPI registry on 2026-04-05
- Architecture: HIGH — directly derived from BOOTSTRAP.md, ARCHITECTURE.md, and locked CONTEXT.md decisions
- Pitfalls: HIGH (CDSE/S3 pitfalls) / MEDIUM (burst DB coverage gaps) — CDSE pitfalls verified by official docs; burst DB pitfalls from prior research
- Code examples: MEDIUM — patterns are correct but CDSE S3 auth flow has one open question (see Open Questions #1)

**Research date:** 2026-04-05
**Valid until:** 2026-07-05 (90 days) — CDSE API is actively evolving; re-verify STAC endpoint and S3 auth annually
