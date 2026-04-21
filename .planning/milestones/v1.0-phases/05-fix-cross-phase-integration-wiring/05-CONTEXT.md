# Phase 5: Fix Cross-Phase Integration Wiring - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix all interface contract mismatches between Phase 1 data-access modules and Phase 2/3/4 product callers (bugs B-01 through B-06). No new features, no API changes to Phase 1 modules — callers must conform to existing interfaces.

</domain>

<decisions>
## Implementation Decisions

### Credential Handling (B-01)
- **D-01:** CDSEClient must be instantiated with `client_id` and `client_secret` from the project config/environment. Use `SubsideoSettings` to load credentials, matching the pattern already established in Phase 1.
- **D-02:** [auto] All five product `*_from_aoi` functions get the same fix pattern — no per-product special casing.

### STAC Search (B-02)
- **D-03:** RTC and CSLC callers must use `client.search_stac()` (not `.search()`) with `start=` and `end=` kwargs (not `datetime_range`). DISP, DIST, and DSWx already do this correctly — use them as the reference pattern.

### Burst DB Access (B-03)
- **D-04:** RTC and CSLC callers must import `query_bursts_for_aoi` from `subsideo.burst.frames` (not a nonexistent `BurstDB` class from `burst.db`). DISP and DIST already do this correctly.

### Orbit Fetch (B-04)
- **D-05:** RTC and CSLC callers must call `fetch_orbit(sensing_time=..., satellite=..., output_dir=...)`. They currently pass a single Path arg. Need to extract sensing_time and satellite from STAC item metadata.

### DEM Fetch (B-05)
- **D-06:** All SAR product callers (RTC, CSLC, DISP, DIST) must pass `output_epsg` to `fetch_dem()`. EPSG should come from burst records (already resolved during burst query).
- **D-07:** Callers must unpack the `tuple[Path, dict]` return from `fetch_dem()` — currently they assign directly to `dem_path` as if it returns `Path`.

### CLI DIST Handler (B-06)
- **D-08:** CLI dist command must iterate `list[DISTResult]` from `run_dist_from_aoi()`. Check each result's `.valid` attribute individually, report failures per-tile.

### Testing Strategy
- **D-09:** [auto] Unit tests for each fix — mock Phase 1 modules and verify callers pass correct args. No integration tests (those require live CDSE credentials).

### Claude's Discretion
- Specific error messages and logging around credential loading
- How to extract sensing_time/satellite from STAC items (parse from item metadata)
- Whether to add a shared helper for CDSEClient instantiation or repeat inline in each module

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 1 Module Interfaces (the "correct" API)
- `src/subsideo/data/cdse.py` — CDSEClient constructor (line ~45) and search_stac signature (line ~86)
- `src/subsideo/data/dem.py` — fetch_dem signature (line ~14): requires output_epsg, returns tuple[Path, dict]
- `src/subsideo/data/orbits.py` — fetch_orbit signature (line ~10): (sensing_time, satellite, output_dir)
- `src/subsideo/burst/frames.py` — query_bursts_for_aoi signature (line ~12): (aoi_wkt, db_path)
- `src/subsideo/config.py` — SubsideoSettings with CDSE credentials

### Broken Callers (files to fix)
- `src/subsideo/products/rtc.py` — run_rtc_from_aoi (~line 310+): B-01, B-02, B-03, B-04, B-05
- `src/subsideo/products/cslc.py` — run_cslc_from_aoi (~line 282+): B-01, B-02, B-03, B-04, B-05
- `src/subsideo/products/disp.py` — run_disp_from_aoi (~line 486+): B-01, B-05
- `src/subsideo/products/dist.py` — run_dist_from_aoi (~line 277+): B-01, B-05
- `src/subsideo/products/dswx.py` — run_dswx_from_aoi (~line 527+): B-01
- `src/subsideo/cli.py` — dist_cmd (~line 233): B-06

### Working Reference Patterns (callers that do it right)
- `src/subsideo/products/disp.py` — correct search_stac, burst query, fetch_orbit usage
- `src/subsideo/products/dist.py` — correct search_stac, burst query, fetch_orbit usage

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- DISP and DIST `*_from_aoi` functions already have correct wiring for B-02, B-03, B-04 — copy their patterns
- SubsideoSettings in config.py loads CDSE_CLIENT_ID and CDSE_CLIENT_SECRET from env/.env

### Established Patterns
- Lazy imports for conda-forge deps inside function bodies (Phase 1-4 decision)
- BurstRecord dataclass has `.burst_id_jpl` and UTM EPSG stored at DB build time
- All product modules follow the same `run_X(...)` + `run_X_from_aoi(...)` dual-function pattern

### Integration Points
- Each `*_from_aoi` function is the sole bridge between data-access (Phase 1) and algorithm execution (Phase 2-4)
- CLI subcommands call `*_from_aoi` functions directly
- No intermediate orchestration layer — fixes go directly in the product module files

</code_context>

<specifics>
## Specific Ideas

No specific requirements — this is mechanical contract-alignment work. All correct patterns already exist in the codebase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-fix-cross-phase-integration-wiring*
*Context gathered: 2026-04-05*
