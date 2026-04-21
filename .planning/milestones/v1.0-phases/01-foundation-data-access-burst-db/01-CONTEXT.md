# Phase 1: Foundation, Data Access & Burst DB - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish the complete data infrastructure layer: CDSE and ASF DAAC data access, EU burst database construction, DEM/orbit/ionosphere ancillary downloads, and the project configuration system. No product pipelines are built in this phase — only the foundation they depend on.

</domain>

<decisions>
## Implementation Decisions

### CDSE Data Access
- **D-01:** Use `pystac-client` for STAC 1.1.0 catalog search against CDSE, and `boto3` with custom endpoint (`endpoint_url=https://eodata.dataspace.copernicus.eu`, `region_name='default'`) for S3 download from `s3://eodata/`. Do not use the legacy OData/sentinelsat approach (deprecated Nov 2025).
- **D-02:** OAuth2 client credentials flow for CDSE authentication. Token refresh should be automatic via `requests-oauthlib` or equivalent. Credentials from `CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET` env vars.
- **D-03:** Implement retry logic with exponential backoff for CDSE S3 downloads. CDSE has rate limits; fail gracefully with clear error messages when credentials are missing or expired.

### EU Burst Database
- **D-04:** Build an independent EU-scoped SQLite database from ESA's published Sentinel-1 burst ID GeoJSON (CC-BY 4.0). Use the same schema as `opera-burstdb` for interoperability with opera-utils tooling, but do not depend on opera-burstdb's `is_north_america` scoped data.
- **D-05:** Cache the built database at `~/.subsideo/eu_burst_db.sqlite`. Rebuild on package version bump. Include a CLI or programmatic `build_burst_db()` entry point for manual rebuilds.
- **D-06:** The burst DB must store EPSG codes per frame. UTM zone derivation must come from the burst record, not be assumed (EU spans zones 28N–38N).

### DEM Management
- **D-07:** Use `dem-stitcher` library with `dem_name='glo_30'` for GLO-30 Copernicus DEM tile download and stitching. It handles WGS84 ellipsoidal height conversion and pixel-corner CRS normalization automatically.
- **D-08:** Warp all DEM tiles to the target UTM CRS at 30m posting before ISCE3 ingestion. This prevents malformed stitched DEMs at high latitudes (>50N) where GLO-30 tiles have variable longitudinal spacing.

### Orbit and Ionosphere
- **D-09:** Use `sentineleof` as primary orbit download tool (maintained by isce-framework team). Implement POEORB-first → RESORB fallback chain. Consider `s1-orbits` (ASF HyP3 team, AWS-backed) as secondary fallback if ESA POD hub is unreachable.
- **D-10:** IONEX TEC maps downloaded from CDDIS GNSS archive using Earthdata credentials (same as ASF DAAC: `EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD`).

### ASF DAAC Access (Validation)
- **D-11:** Use `asf-search` + `earthaccess` for searching and downloading OPERA N.Am. reference products from ASF DAAC. This path is validation-only — not used for primary EU data access.

### Configuration
- **D-12:** Pydantic v2 `BaseSettings` with layered precedence: env vars > `.env` file (via `python-dotenv`) > per-run YAML > defaults. The per-run YAML follows ISCE3 workflow YAML convention (used by compass, opera-rtc, dolphin).
- **D-13:** Credential validation at startup: implement a `check_env()` or `subsideo check-env` utility that validates CDSE, Earthdata, and (optionally) CDS API credentials are present and functional before any pipeline run.

### Claude's Discretion
- Internal module structure within `data/` and `burst/` — researcher and planner can determine optimal file organization
- Error message formatting and logging verbosity levels
- Test fixture design for mocked CDSE/ASF responses

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specifications
- `BOOTSTRAP.md` — Full project brief with repository layout, architecture decisions, validation strategy, and implementation sequence
- `pyproject.toml` — Package metadata, dependencies, tool configuration (ruff, mypy, pytest)
- `.planning/PROJECT.md` — Living project context with constraints and key decisions

### Research Findings
- `.planning/research/STACK.md` — Verified technology stack with versions and rationale
- `.planning/research/PITFALLS.md` — 12 critical pitfalls with prevention strategies
- `.planning/research/ARCHITECTURE.md` — Component boundaries, data flows, build order
- `.planning/research/FEATURES.md` — Feature landscape and dependency graph

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project. Only `pyproject.toml`, `BOOTSTRAP.md`, and `.gitignore` exist.

### Established Patterns
- Hatchling build backend with `src/subsideo/` layout (defined in pyproject.toml)
- Ruff linting (line-length 100, target py310) and mypy strict mode configured
- Pytest with `--cov=subsideo`, 80% coverage minimum, three custom markers (integration, validation, slow)

### Integration Points
- `src/subsideo/` package directory needs to be created with `__init__.py`
- CLI entry point: `subsideo.cli:app` (typer app, defined in pyproject.toml scripts)
- Config: `subsideo.config.Settings` (Pydantic BaseSettings)

</code_context>

<specifics>
## Specific Ideas

- CDSE S3 uses non-standard endpoint — this is the #1 integration gotcha per pitfalls research
- pyaps3 >=0.3.6 is required for the new CDS API (Feb 2025 breaking change) — verify this in the conda environment
- The ESA burst ID GeoJSON is CC-BY 4.0 licensed — document attribution in the burst DB module

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation-data-access-burst-db*
*Context gathered: 2026-04-05*
