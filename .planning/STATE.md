---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Phase complete — ready for verification
stopped_at: Completed 02-04-PLAN.md
last_updated: "2026-04-05T19:23:24.455Z"
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 8
  completed_plans: 7
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-05)

**Core value:** Produce scientifically accurate, OPERA-spec-compliant SAR/InSAR geospatial products over EU AOIs — validated against official reference products to prove correctness.
**Current focus:** Phase 02 — rtc-s1-and-cslc-s1-pipelines

## Current Position

Phase: 02 (rtc-s1-and-cslc-s1-pipelines) — EXECUTING
Plan: 4 of 4

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

### Pending Todos

None yet.

### Blockers/Concerns

- DIST-S1 (Phase 3) depends on opera-adt/dist-s1 ~April 2026 conda-forge release; treat as conditional until confirmed
- DSWx threshold calibration (Phase 4) has no published EU recipe; budget research time within the phase

## Session Continuity

Last session: 2026-04-05T19:23:24.452Z
Stopped at: Completed 02-04-PLAN.md
Resume file: None
