---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: v1.0 milestone complete
stopped_at: Completed 09-01-PLAN.md
last_updated: "2026-04-09T01:40:19.023Z"
last_activity: 2026-04-09
progress:
  total_phases: 9
  completed_phases: 9
  total_plans: 21
  completed_plans: 21
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-09)

**Core value:** Produce scientifically accurate, OPERA-spec-compliant SAR/InSAR geospatial products over EU AOIs — validated against official reference products to prove correctness.
**Current focus:** v1.0 shipped — planning next milestone

## Current Position

Milestone: v1.0 complete
Next: `/gsd:new-milestone` to define v2.0

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01 P01 | 8min | 3 tasks | 12 files |
| Phase 01 P04 | 5min | 2 tasks | 8 files |
| Phase 01 P03 | 5min | 2 tasks | 5 files |
| Phase 01 P02 | 7min | 1 tasks | 2 files |
| Phase 02 P01 | 3min | 2 tasks | 6 files |
| Phase 02 P03 | 3min | 2 tasks | 4 files |
| Phase 02 P02 | 4min | 2 tasks | 4 files |
| Phase 02 P04 | 2min | 2 tasks | 4 files |
| Phase 03 P01 | 6min | 2 tasks | 3 files |
| Phase 03 P03 | 2min | 2 tasks | 2 files |
| Phase 03 P02 | 4min | 2 tasks | 3 files |
| Phase 04 P01 | 5min | 2 tasks | 7 files |
| Phase 04 P02 | 4min | 2 tasks | 5 files |
| Phase 04 P03 | 3min | 1 tasks | 4 files |
| Phase 05 P01 | 4min | 2 tasks | 4 files |
| Phase 05 P02 | 3min | 2 tasks | 7 files |
| Phase 06 P01 | 4min | 2 tasks | 7 files |
| Phase 06 P02 | 5min | 2 tasks | 2 files |
| Phase 07 P01 | 4min | 2 tasks | 4 files |
| Phase 08 P01 | 2min | 3 tasks | 6 files |
| Phase 09 P01 | 3min | 3 tasks | 7 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: CDSE over ASF for EU data — CDSE is the native Copernicus hub; STAC endpoint is `stac.dataspace.copernicus.eu/v1` (changed Nov 2025)
- [Init]: EU burst DB must be built from ESA CC-BY 4.0 GeoJSON — opera-burstdb covers North America only
- [Init]: Two-layer install enforced — conda-forge for ISCE3/GDAL/dolphin/snaphu; pip for pure-Python layer
- [Phase 01]: Moved conda-forge-only deps to optional [conda] group so pip install works in dev environments
- [Phase 01]: YamlConfigSettingsSource reads yaml_file from model_config not init kwargs; tests use dynamic subclass
- [Phase 01]: Lazy imports for orbit backends (sentineleof/s1-orbits) to handle partial conda installs
- [Phase 01]: UTM EPSG stored at DB build time via pyproj; never derived at query time
- [Phase 01]: Spatial query uses Python-side shapely intersection (no SpatiaLite dependency)
- [Phase 01]: S3 auth uses client_id/secret as AWS credentials, separate from OAuth2 bearer token
- [Phase 02]: Dataclasses over Pydantic for result types -- plain containers, not settings
- [Phase 02]: Lazy import for skimage in ssim() to avoid heavy import on module load
- [Phase 02]: Lazy import for compass/h5py inside functions for partial conda install support
- [Phase 02]: HDF5 validation checks /data group existence rather than hardcoded dataset paths
- [Phase 02]: Lazy imports for opera-rtc and rio-cogeo inside function bodies to support partial conda installs
- [Phase 02]: dB-domain RTC comparison and interferometric phase CSLC comparison per RESEARCH.md pitfalls
- [Phase 03]: Lazy imports for all conda-forge deps (dolphin, tophu, mintpy, scipy) inside function bodies
- [Phase 03]: Post-unwrap QC uses plane-fit residual RMS, flags but does not fail pipeline
- [Phase 03]: CDS credential validation at pipeline start before any processing (fail-fast)
- [Phase 03]: EGMStoolkit lazy import in fetch_egms_ortho; LOS-to-vertical via cos(theta) division; grid alignment always reprojects to EGMS grid
- [Phase 03]: Separate validate_dist_product from validate_rtc_product for module independence
- [Phase 03]: Simplified MGRS tile resolution from AOI centroid; dist-s1 validates tile availability
- [Phase 04]: DSWE diagnostic tests use PROTEUS defaults mapped to S2 L2A; inject_opera_metadata is shared utility for all product types
- [Phase 04]: Markup from markupsafe for SVG inline rendering in Jinja2 autoescape mode
- [Phase 04]: Adapted validate --disp to use --egms flag matching actual compare_disp API
- [Phase 04]: Added run_rtc_from_aoi and run_cslc_from_aoi wrappers to complete from_aoi pattern across all products
- [Phase 05]: Reordered data-access block so burst query precedes DEM fetch (burst epsg needed for output_epsg)
- [Phase 05]: Added empty-burst early-exit guard in from_aoi functions
- [Phase 05]: Reordered burst query before DEM fetch in dist.py to access burst EPSG
- [Phase 05]: Added empty-bursts guard in disp.py run_disp_from_aoi for early error return
- [Phase 06]: get_software_version uses importlib.metadata with dev fallback for editable installs
- [Phase 06]: IONEX failure warns and continues with tec_file=None rather than failing CSLC pipeline
- [Phase 06]: Lazy imports for rasterio/pyproj/ASFClient inside auto-fetch try block; 30-day mtime window as default date range
- [Phase 07]: EGMS auto-fetch placed before if/elif product chain; build-db uses typer.Argument for positional geojson
- [Phase 08]: No code changes needed -- purely planning artifact metadata corrections
- [Phase 09]: Fallback lookup using field-name prefix startswith() for correlation ambiguity between RTC and DISP
- [CSLC Eval]: 4 monkey-patches for numpy 2.x compat with compass/s1reader/isce3 pybind11
- [CSLC Eval]: Burst database SQLite required for correct geogrid computation; compass's DB-free path has multiple bugs
- [CSLC Eval]: Grid snapping (x_snap=5, y_snap=10) required for pixel-center alignment with OPERA reference
- [CSLC Eval]: Cross-version phase comparison (isce3 0.15 vs 0.25) produces zero coherence; amplitude metrics used instead
- [CSLC Eval]: CSLC amplitude correlation 0.79, RMSE 3.77 dB — PASS with amplitude-based criteria

### Pending Todos

None yet.

### Blockers/Concerns

- DIST-S1 (Phase 3) depends on opera-adt/dist-s1 ~April 2026 conda-forge release; treat as conditional until confirmed
- DSWx threshold calibration (Phase 4) has no published EU recipe; budget research time within the phase

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260408-pfx | Fix stale ROADMAP.md Phase 9 progress row and checkbox | 2026-04-09 | 40790d5 | [260408-pfx-fix-stale-roadmap-md-phase-9-progress-ro](./quick/260408-pfx-fix-stale-roadmap-md-phase-9-progress-ro/) |
| 260408-q2i | Create comprehensive README.md and CHANGELOG.md | 2026-04-09 | 9c6af76 | [260408-q2i-create-comprehensive-readme-md-and-chang](./quick/260408-q2i-create-comprehensive-readme-md-and-chang/) |

## Session Continuity

Last activity: 2026-04-09
Last session: 2026-04-09T01:51:40Z
Stopped at: Completed quick task 260408-q2i
Resume file: None
