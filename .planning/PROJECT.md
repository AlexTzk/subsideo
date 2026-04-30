# subsideo

## What This Is

A Python library that produces OPERA-equivalent geospatial products (RTC-S1, CSLC-S1, DISP-S1, DSWx-S2, DIST-S1) for European Union areas of interest. It wraps the ISCE3/dolphin algorithm stack, pulls Sentinel-1/2 data from the Copernicus Data Space Ecosystem (CDSE), and ships a validation framework that compares outputs against OPERA N.Am. reference products and EGMS EU products.

## Core Value

Produce scientifically accurate, OPERA-spec-compliant SAR/InSAR geospatial products over EU AOIs — validated against official reference products to prove correctness.

## Requirements

### Validated

- ✓ EU burst database extending opera-utils for EU coverage (ESA burst ID maps) — v1.0
- ✓ CDSE data access layer (STAC search + S3 download for S1 SLC and S2 L2A) — v1.0
- ✓ ASF DAAC access for OPERA N.Am. reference product fetching (validation) — v1.0
- ✓ GLO-30 Copernicus DEM download and tile management — v1.0
- ✓ Orbit ephemeris (POE/ROE) and ionosphere (IONEX TEC) download — v1.0
- ✓ Pydantic settings configuration (env vars + .env + YAML per-run config) — v1.0
- ✓ RTC-S1 pipeline for EU AOIs using ISCE3/OPERA-RTC via CDSE data — v1.0
- ✓ CSLC-S1 pipeline for EU AOIs using ISCE3 burst coregistration — v1.0
- ✓ DISP-S1 pipeline using dolphin + tophu + MintPy for displacement time series — v1.0
- ✓ DIST-S1 pipeline wrapping opera-adt/dist-s1 for surface disturbance — v1.0
- ✓ DSWx-S2 pipeline porting OPERA DSWx-HLS to CDSE Sentinel-2 L2A — v1.0
- ✓ Typer-based CLI with all subcommands (rtc, cslc, disp, dswx, dist, validate, build-db) — v1.0
- ✓ Validation framework: metrics + comparison modules (OPERA, EGMS, JRC) — v1.0
- ✓ Validation report generation (HTML/Markdown) — v1.0
- ✓ Output format compliance: HDF5 for CSLC/DISP, COG GeoTIFF for RTC/DSWx — v1.0

### Active

*(No active requirements — v1.2 requirements to be defined via `/gsd-new-milestone`)*

### Validated (v1.1 additions)

- ✓ Reproducible conda-forge environment (numpy<2, tophu, rio-cogeo shim, _mp.py fork bundle, subprocess watchdog, per-platform lockfiles) — v1.1
- ✓ Shared validation harness (harness.py, stable_terrain.py, selfconsistency.py, criteria.py CALIBRATING/BINDING, split dataclasses) — v1.1
- ✓ RTC-S1 EU burst-level validation: 3/5 PASS across Alpine/Iberian/Portuguese regimes; same criteria as N.Am. — v1.1
- ✓ CSLC-S1 self-consistency framework: SoCal/Mojave/Iberian CALIBRATING PASS; cross-version phase impossibility documented — v1.1
- ✓ DISP-S1 comparison adapter + honest FAIL: prepare_for_reference (explicit method=); ramp-attribution diagnostic; Unwrapper Selection brief — v1.1
- ✓ DIST-S1 CMR auto-supersede probe + EFFIS 3-event EU infrastructure; DIST-01/02/03 deferred-with-evidence to v1.2 — v1.1
- ✓ DSWx-S2 N.Am. F1=0.9252 PASS (Lake Tahoe); typed threshold constants; EU honest FAIL F1=0.8165 with named upgrade path — v1.1
- ✓ 10-cell manifest-driven results matrix + 808-line validation_methodology.md; 554 unit tests; Dockerfile + Apptainer — v1.1

## Current Milestone: v1.1 N.Am./EU Validation Parity & Scientific PASS

**Goal:** Drive every product to an unambiguous per-region PASS, an honest FAIL with named upgrade path, or a deferral with dated unblock condition — using OPERA/EGMS as validators, not quality ceilings.

**Target deliverables:**
- All 5 products × 2 regions × 2 criteria columns produce numbers (no n/a)
- Reference-agreement metrics reported separately from product-quality gates; neither tightens based on the reference's own score
- Cross-cutting infrastructure fragility (numpy 2.x patches, macOS mp, missing deps, rio-cogeo imports) resolved at environment level
- Single-command re-run path from cached intermediates for every eval
- Closure test: fresh clone → `micromamba env create -f conda-env.yml` → `make eval-all` → filled results matrix

**Explicitly out of scope for v1.1:** global expansion beyond N.Am./EU, ML-based replacements for threshold algorithms, new OPERA product classes, multi-burst mosaicking, DISP unwrapper selection (spun out to dedicated follow-up milestone).

**Estimated effort:** 22-27 working days single-developer.

### Out of Scope

- VLM (vertical land motion) — OPERA's own VLM targets 2028; skip for v1
- Real-time operational production infrastructure (SDS/PGE orchestration) — this is a library, not a pipeline orchestrator
- Commercial cloud deployment / containerised production service — out of scope for v1
- NISAR data support — future work; placeholder stubs only
- Windows native support — not a priority; WSL2 is acceptable

## Current State

Shipped v1.1 with ~22,600 LOC Python (source + tests) across 184+ files. 308 v1.1 commits over 21 days (2026-04-08 → 2026-04-29).

**v1.1 Results Matrix:**

| Product | N.Am. | EU |
|---------|-------|-----|
| RTC | DEFERRED (v1.2 re-run) | 3/5 PASS ⚠ |
| CSLC | *CALIBRATING* | *CALIBRATING* |
| DISP | FAIL r=0.049 (inconclusive ramp) | FAIL r=0.336 (inconclusive ramp) |
| DIST | DEFERRED (CMR: operational_not_found) | 0/3 PASS |
| DSWX | F1=0.9252 PASS | F1=0.8165 FAIL |

All 10 cells filled — PASS, FAIL-with-named-upgrade-path, or DEFERRED-with-dated-unblock. No n/a, no empty cells. CALIBRATING gates bind at v1.2 (≥3 data points required for promotion).

## Context

- **Algorithm stack**: ISCE3 (RTC, CSLC), dolphin (phase linking for DISP), tophu (tile-based unwrapping), SNAPHU (unwrapping binary), MintPy (time-series inversion + tropospheric correction)
- **Data backend**: CDSE S3 bucket (`s3://eodata/`) with custom endpoint — not standard AWS S3. ASF DAAC used only for validation reference products.
- **EU burst DB**: Built from ESA CC-BY 4.0 GeoJSON; extends opera-utils schema for EU coverage.
- **Two-layer install**: ISCE3, GDAL, dolphin, tophu, snaphu are conda-forge only. Pure-Python package installs via pip on top.
- **UTM zone complexity**: EU spans zones 28N–38N; multi-zone AOIs and zone-boundary edge cases are non-trivial.
- **Tropospheric correction**: MintPy uses ERA5 via ECMWF CDS API, requiring a separate `~/.cdsapirc` key.
- **SNAPHU licensing**: Non-commercial research license; available via conda-forge.
- **Target platforms**: Linux x86-64 (primary), macOS arm64 (secondary).
- **Python**: >=3.10, targeting 3.11.

## Constraints

- **Conda-forge deps**: ISCE3, GDAL, dolphin, tophu, snaphu must come from conda-forge — never pip install these
- **CDSE credentials**: Required for all EU data access (free registration at dataspace.copernicus.eu)
- **Earthdata credentials**: Required for OPERA N.Am. validation product access from ASF DAAC
- **CDS API key**: Required for ERA5 tropospheric correction in DISP pipeline
- **Output spec compliance**: Products must match OPERA product specification format (HDF5/COG, 30m UTM posting)
- **Validation pass criteria**: RTC RMSE < 0.5 dB, r > 0.99; CSLC amplitude r > 0.6, RMSE < 4 dB (phase comparison methodologically impossible across isce3 versions — see CONCLUSIONS_CSLC_N_AM.md §5); DISP r > 0.92, bias < 3 mm/yr; DSWx F1 > 0.90; DIST F1 > 0.80, accuracy > 0.85
- **Metrics-vs-targets discipline (v1.1)**: reference-agreement metrics (vs OPERA/EGMS/JRC/EMS) are sanity checks that never tighten based on the reference's own score; product-quality gates (self-consistency, ground-truth residuals) define PASS/FAIL — the two are reported separately

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CDSE over ASF DAAC for EU data | CDSE is the native Copernicus data hub; ASF mirrors are incomplete for EU | Implemented Phase 01 |
| Hatchling build backend | Lightweight, modern, aligns with scientific Python ecosystem | Implemented Phase 01 |
| EU burst DB from ESA maps | opera-burstdb only covers N.Am.; ESA publishes global burst IDs under CC-BY | Implemented Phase 01 |
| HDF5 for CSLC/DISP, COG for RTC/DSWx | Matches OPERA product spec for interoperability with OPERA tooling and QGIS | Implemented Phase 02-04 |
| Loguru for logging | Structured logging with minimal boilerplate for scientific workflows | Implemented Phase 01 |
| EGMS auto-fetch in validate CLI | Mirrors ASF auto-fetch pattern — lazy import, try/except with warning on failure | Implemented Phase 07 |
| build-db as CLI subcommand | Users need a way to create EU burst SQLite from ESA GeoJSON without scripting | Implemented Phase 07 |
| Native CSLC/DISP resolution stays production default; downsampling only in comparison adapter | OPERA-spec 5×10 m is subsideo's scientific contribution; matching OPERA's 30 m grid is a validation choice, not a product choice | Planned v1.1 Phase 3 |
| Spin DISP unwrapper selection out to a dedicated follow-up milestone | Multiple candidate approaches (PHASS+deramping, SPURT native, tophu-SNAPHU tiled, 20×20 m fallback) with distinct compute/failure profiles deserve their own time-box; choice should be informed by v1.1's clean baseline FAIL numbers | Planned v1.1 Phase 3 |
| Pin numpy < 2.0 in conda-env.yml; remove the four monkey-patches | Patches in cslc.py exist purely to keep compass/s1-reader working under numpy 2.x — sunset condition is upstream numpy-2-compatible releases | Planned v1.1 Phase 0 |
| OPERA v0.1 DIST sample comparison gated by config-drift check | If OPERA produced v0.1 with materially different processing parameters than dist-s1 2.0.13 defaults, comparison is skipped (not adjusted) and N.Am. cell deferred until operational reference ships | Planned v1.1 Phase 4 |
| DSWx F1 > 0.90 bar does not move during recalibration | DSWE-family algorithms have an architectural F1 ceiling ≈ 0.92; honest FAIL with named ML-replacement upgrade path is more useful than moving the goalpost | Planned v1.1 Phase 5 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-30 after v1.1 milestone — 8 requirements moved to Validated; Current State reflects shipped matrix; v1.2 requirements to be defined via /gsd-new-milestone*
