# Project Research Summary

**Project:** subsideo
**Domain:** SAR/InSAR geospatial processing library — OPERA-equivalent products for EU AOIs
**Researched:** 2026-04-05
**Confidence:** HIGH (stack and features), MEDIUM (architecture integration patterns, pitfall recovery costs)

## Executive Summary

Subsideo is a Python library that produces OPERA-specification SAR/InSAR products (RTC-S1, CSLC-S1, DISP-S1, DSWx-S2, DIST-S1) for European areas of interest, filling a gap left by OPERA's operational North America focus. The authoritative implementation path is clear and well-precedented: ISCE3 is the only production-grade Python SAR engine with Sentinel-1 burst support, dolphin and tophu are the OPERA-ADT reference implementations for phase linking and unwrapping, and MintPy is the established time-series inversion layer. All key packages are conda-forge distributed, with a strict divide between the conda-only core (ISCE3, GDAL, HDF5, dolphin) and a pip-installable pure-Python layer for data access, configuration, and CLI. The install discipline is non-negotiable: mixing pip and conda for compiled packages silently corrupts the environment in ways that are expensive to debug.

The central differentiator — and the first prerequisite that gates all S1 pipeline work — is a validated EU burst database. The OPERA burst_db SQLite only covers North America; subsideo must build an equivalent from ESA's CC-BY 4.0 burst ID GeoJSON. Everything downstream (CSLC coregistration, DISP phase linking, DIST disturbance detection) is keyed on burst IDs that can only be resolved correctly with this database in place. CDSE data access is the other gating dependency: Sentinel-1/2 data for EU lives on CDSE's non-standard S3 endpoint, and the STAC catalogue migrated to a new endpoint in November 2025. Both the burst DB and the CDSE data access layer must be built and validated before any algorithm pipeline is attempted.

The primary risks are correctness risks, not technology risks. Phase unwrapping cycle slips in the DISP pipeline produce plausible-looking but wrong displacement values; ERA5 tropospheric correction silently disabling leaves cm-scale atmospheric noise in the time series; and DSWx spectral thresholds derived from HLS data do not transfer directly to native Sentinel-2 L2A. Each of these requires explicit defensive design — post-unwrapping sanity checks, environment validation CLI commands, and DSWx threshold re-calibration against EU training data — built in during the relevant pipeline phase, not retrofitted during validation.

## Key Findings

### Recommended Stack

The stack splits cleanly into two layers. The algorithm core (ISCE3, GDAL, HDF5, dolphin, tophu, snaphu, MintPy, rasterio, geopandas, xarray) must be installed from conda-forge and must never be touched by pip; these packages have compiled C/Fortran extensions linked against shared libraries that only conda-forge's solver can satisfy. The pure-Python layer (opera-utils, dem-stitcher, pystac-client, boto3, asf-search, earthaccess, sentineleof, pyaps3, typer, pydantic-settings, loguru) installs cleanly on top via pip. The configuration and CLI layer uses pydantic-settings 2.x for layered env/dotenv/YAML config — the same pattern used internally by dolphin — and typer for subcommand dispatch.

**Core technologies:**
- `isce3` 0.25.10: SAR processing engine — the only Python-native NISAR/OPERA-spec engine; no alternative for burst coregistration and geocoding
- `dolphin` 0.42.5: PS/DS phase linking — OPERA-ADT reference implementation, JOSS 2024 peer-reviewed
- `tophu` 0.2.1: Tile-based phase unwrapping — designed specifically for large EU-scale interferograms; calls snaphu internally
- `MintPy` 1.6.3: Time-series inversion — reads OPERA CSLC HDF5 and dolphin outputs natively; includes ERA5 tropospheric correction via pyaps3
- `pystac-client` 0.9.0 + `boto3`: CDSE data access — CDSE migrated to STAC 1.1.0 in Feb 2025 and deprecated the old OData/STAC endpoints by Nov 2025
- `opera-utils` 0.25.6: Burst DB utilities and OPERA HDF5 I/O helpers — pip-installable; EU burst coverage must be added as a sibling SQLite schema
- `dem-stitcher` 2.5.13: GLO-30 tile management — handles WGS84 ellipsoidal height conversion and pixel-centre normalisation automatically
- `pydantic-settings` 2.13.1 + `typer` 0.24.1: Config and CLI layer — matches the dolphin/OPERA-ADT pattern exactly

**Critical version constraints:**
- `pyaps3 >= 0.3.6`: earlier versions silently fail ERA5 downloads due to CDS API credential format change (Feb 2025)
- `geopandas >= 1.0` requires `shapely >= 2.0`; fiona is no longer needed
- `rasterio 1.5.0` requires `GDAL >= 3.8`
- `sentineleof >= 2.0` post-SciHub migration; old endpoint decommissioned Oct 2023

### Expected Features

**Must have (table stakes):**
- EU burst database (SQLite from ESA burst ID GeoJSON) — gates all S1 pipelines; no EU coverage without it
- CDSE data access layer (STAC search + S3 download) — all EU S1/S2 data lives here
- GLO-30 DEM management — required by RTC and CSLC pipelines; must warp to UTM before ISCE3 consumption
- Orbit (POE/ROE) and IONEX fetch with fallback logging — POEORB-only mode for validation
- RTC-S1 pipeline producing OPERA-spec COG GeoTIFF at 30m UTM
- CSLC-S1 pipeline producing OPERA-spec HDF5 (prerequisite for DISP)
- DISP-S1 pipeline producing HDF5 displacement time series (primary science output)
- DSWx-S2 pipeline (independent of S1; high downstream value)
- DIST-S1 pipeline wrapping opera-adt/dist-s1 (timing-dependent on upstream ~April 2026 release)
- Validation framework: RMSE/r/SSIM/F1 metrics vs OPERA N.Am. and EGMS EU references
- HTML/Markdown validation reports
- CLI (`subsideo rtc|cslc|disp|dswx|dist|validate`) via typer
- OPERA product spec compliance: HDF5 structure for CSLC/DISP, COG structure for RTC/DSWx/DIST
- Multi-zone UTM handling (EU spans zones 28N–38N; this is a correctness requirement, not optional)

**Should have (competitive differentiators):**
- ERA5 tropospheric correction integration (add post-DISP baseline validation; improves velocity accuracy)
- GPU acceleration documentation for dolphin JAX path (once CPU baseline confirmed)
- Tutorial Jupyter notebooks with Folium maps
- Conda-lock file for environment reproducibility

**Defer to v2+:**
- VLM (vertical land motion) — OPERA deferred to 2028; requires GNSS calibration inversion chain
- NISAR support — stub only in v1; data products not yet available
- Batch processing / parallelisation framework — premature without real user scale data
- Real-time/operational processing infrastructure — out of scope; document CLI integration patterns instead

### Architecture Approach

The architecture is a five-layer stack: CLI/config at the top, pipeline orchestration below, algorithm wrappers adapting to upstream library APIs, a data access layer managing all external I/O, and a product/validation layer at the output end. The key structural principle is strict separation: the `access/` module is the only code that touches the network; wrappers in `wrappers/` are thin adapters that translate subsideo domain objects into upstream library conventions and contain no science logic; pipelines in `pipelines/` sequence these pieces but perform no algorithm work themselves; and validation is always a separate CLI pass, never called from inside a pipeline. Every pipeline is parameterised by a Pydantic model serialisable to YAML — the same config-driven pattern used by dolphin and OPERA-ADT tools — so every run is reproducible by replaying its config file.

**Major components:**
1. `access/` — CDSE STAC/S3, ASF DAAC, GLO-30 DEM, orbit/IONEX fetchers; mock-friendly boundary for unit tests
2. `bursts/` — EU burst SQLite build from ESA GeoJSON; AOI-to-burst-ID resolution; UTM zone assignment per burst
3. `pipelines/` — Thin orchestrators: RTC, CSLC, DISP, DSWx, DIST; no algorithm logic
4. `wrappers/` — ISCE3, dolphin, tophu, MintPy adapters; absorb upstream API changes
5. `config/` — Pydantic settings (global) + per-pipeline run configs; YAML serialisable for reproducibility
6. `products/` — OPERA spec compliance for HDF5 (CSLC/DISP) and COG GeoTIFF (RTC/DSWx/DIST); one place for all format rules
7. `validation/` — Pure functions over numpy arrays; completely decoupled from pipelines; testable in isolation
8. `cli/` — Typer subcommands; no logic, only argument parsing and pipeline invocation

**Key patterns:**
- Config-driven pipelines: each run config is saved to the output directory; runs are reproducible by YAML replay
- Ancillary resolver: all DEM/orbit/ionosphere downloads happen before any wrapper is called; wrappers assert path.exists() at entry
- Wrapper isolation: wrappers are adapters, not algorithms; science logic lives in upstream libraries
- Validation as a standalone pass: validate command accepts paths to completed outputs, never runs inside a pipeline

### Critical Pitfalls

1. **Conda/pip environment corruption** — Never pip-install compiled packages (gdal, h5py, numpy, scipy, shapely); define the full environment in `environment.yml` with pinned channels; enforce in CI via `conda list` inspection. This is the single most likely cause of project-wide blocking issues. Address in Phase 1 before any code is written.

2. **CDSE S3 non-standard endpoint** — Always use `endpoint_url='https://eodata.dataspace.copernicus.eu'` and `region_name='default'` in a centralised `CDSEClient`; never scatter boto3 config across the codebase. The STAC endpoint changed to `stac.dataspace.copernicus.eu/v1` in November 2025 — legacy endpoint is dead. The S3 Secret Key is shown only once at generation. Build a credential-expiry check from day one.

3. **EU burst database gaps** — opera-utils burst_db covers North America only; EU queries return NULL silently. Build the EU SQLite from ESA's CC-BY 4.0 burst ID GeoJSON and validate >= 90% EU coverage against ESA's published burst count per track before writing any pipeline code.

4. **Phase unwrapping cycle slips** — SNAPHU exits 0 and produces numerically valid output that contains 2π cycle jumps (28 mm per C-band fringe). These propagate silently through MintPy into the final velocity field. Mitigation: tophu tile overlap >= 300 pixels for EU scenes, adaptive coherence masking, post-unwrapping planar ramp sanity check, and cross-validation against EGMS before accepting any time series.

5. **OPERA HDF5 spec compliance drift** — The OPERA ATBD defines HDF5 schemas that ISCE3 does not enforce. Without an `OperaProductValidator` running in CI, spec drift accumulates. Build the validator in Phase 1 (even against stub outputs) and never relax it. Wrong chunking, missing metadata groups, or float32 instead of complex64 will break opera-utils downstream.

6. **DSWx spectral threshold mismatch** — OPERA's DSWx thresholds were calibrated on HLS (harmonised Landsat + Sentinel-2), not native Sentinel-2 L2A. Applying OPERA thresholds directly to CDSE L2A produces elevated false positives over bright soil and false negatives in shallow water. Threshold re-calibration against EU training data is required before the DSWx pipeline can be validated.

7. **GLO-30 variable grid spacing above 50N** — GLO-30 tiles above 50°N use latitude-dependent longitudinal compression. Always warp to a uniform UTM 30m grid before passing to ISCE3. Validate the DEM pipeline against a high-latitude test AOI (Oslo, 59°N) before any RTC work.

## Implications for Roadmap

Based on the combined research, the component dependency graph dictates a clear phase sequence. The data access and EU burst database layers gate everything; RTC is the simplest algorithm pipeline and validates the full stack cheaply; CSLC gates DISP; DSWx is independent and can run in parallel.

### Phase 1: Environment and Foundation

**Rationale:** The conda/pip environment corruption pitfall is the single most likely cause of project-wide failure. Lock the environment before writing any code. Also establish OPERA spec compliance tooling now — retrofitting it later is categorised as HIGH recovery cost.

**Delivers:** Verified conda environment with full ISCE3/dolphin/MintPy stack; `OperaProductValidator` class (even against stubs); project structure scaffold; CI smoke test for macOS arm64.

**Addresses:** Table stakes — infrastructure prerequisites for all pipelines; OPERA product spec compliance from day zero.

**Avoids:** Pitfall 1 (conda/pip corruption), Pitfall 9 (OPERA spec compliance drift), Pitfall 11 (macOS arm64 build failures).

### Phase 2: Data Access Layer and EU Burst Database

**Rationale:** CDSE access and the EU burst database are gating dependencies for all S1 pipeline work. Neither can be deferred. DSWx also depends on CDSE for Sentinel-2 L2A. GLO-30 DEM management and orbit/IONEX fetching belong here because the ancillary resolver pattern must be established before pipelines are built.

**Delivers:** `CDSEClient` with STAC search and S3 download; EU burst SQLite with >= 90% coverage and geometry integrity; GLO-30 DEM manager with UTM warping; orbit/IONEX fetcher with POEORB/RESORB fallback and logging; `subsideo check-env` CLI command validating all credentials.

**Addresses:** CDSE data access (table stakes), EU burst database (table stakes and key differentiator), GLO-30 DEM management (table stakes), orbit/IONEX fetch (table stakes).

**Avoids:** Pitfall 2 (CDSE endpoint/credential), Pitfall 3 (EU burst DB gaps), Pitfall 7 (GLO-30 high-latitude grid spacing), Pitfall 8 (orbit file availability race).

**Research flag:** CDSE STAC endpoint and S3 path format changed in 2025; validate integration with live endpoint early and include a canary integration test.

### Phase 3: RTC-S1 Pipeline

**Rationale:** RTC is the simplest ISCE3 workflow (single-pass; no burst coregistration). It validates the full access → wrapper → product writer stack at lowest cost, and producing a spec-compliant RTC COG is the prerequisite for DIST-S1.

**Delivers:** End-to-end RTC-S1 pipeline: CDSE S1 SLC → isce3 RTC → OPERA-spec COG GeoTIFF at 30m UTM; UTM zone selector; `OperaProductValidator` passing on real output; `subsideo rtc` CLI subcommand.

**Addresses:** RTC-S1 pipeline (table stakes), multi-zone UTM handling (correctness requirement), OPERA product spec compliance.

**Avoids:** Pitfall 4 (UTM zone boundary misalignment), Pitfall 8 (orbit type logging), Pitfall 9 (OPERA HDF5/COG spec compliance).

### Phase 4: CSLC-S1 Pipeline

**Rationale:** CSLC is the prerequisite for DISP. It is also more complex than RTC (burst coregistration, geocoded HDF5 output). Establishing the CSLC pipeline and validating its HDF5 output structure before starting DISP avoids debugging two layers simultaneously.

**Delivers:** CSLC-S1 pipeline: CDSE S1 SLC → compass/isce3 burst coregistration → OPERA-spec HDF5 at 5×10m UTM; `subsideo cslc` CLI; CSLC HDF5 validator passing.

**Addresses:** CSLC-S1 pipeline (table stakes), HDF5 output spec compliance, EU burst DB integration for frame mapping.

**Avoids:** Pitfall 4 (UTM zone handling), Pitfall 8 (POEORB logging), Pitfall 9 (HDF5 spec compliance).

**Research flag:** CSLC pipeline involves compass (OPERA-ADT) wrapping isce3 burst coregistration — the integration between s1-reader, compass, and isce3 is well-documented in OPERA-ADT repos but may require careful version alignment; validate compass 0.5.6 against isce3 0.25.x before starting implementation.

### Phase 5: DISP-S1 Pipeline

**Rationale:** DISP is the primary science output and the most complex pipeline: dolphin phase linking → tophu unwrapping → MintPy time-series inversion. It also has the highest risk of silent correctness failures (cycle slips, tropospheric noise). Defensive measures must be built in during this phase, not added post-validation.

**Delivers:** DISP-S1 pipeline: CSLC HDF5 stack → dolphin PS/DS phase linking → tophu tiled unwrapping → MintPy inversion → OPERA-spec DISP HDF5 displacement time series; post-unwrapping sanity check; ERA5 CDS API validation in `check-env`; `subsideo disp` CLI.

**Addresses:** DISP-S1 pipeline (table stakes), ERA5 tropospheric correction (v1.x, but CDS API validation must be present from day one of this phase).

**Avoids:** Pitfall 5 (phase unwrapping cycle slips), Pitfall 6 (ERA5/CDS API silent failure), performance traps (SNAPHU without tiling, MintPy OOM for large stacks).

**Research flag:** dolphin MiniStackPlanner configuration for EU scene sizes, and MintPy's `smallbaselineApp` integration with dolphin output paths, need hands-on validation. These are well-documented but have known configuration gotchas (mintpy.load.processor = isce, path templates).

### Phase 6: DSWx-S2 Pipeline

**Rationale:** DSWx is independent of all S1 pipelines; it could in principle be built in parallel with Phases 3–5. It is placed here because it has a research-heavy sub-task (spectral threshold re-calibration) that is best addressed after the team has pipeline-building patterns established.

**Delivers:** DSWx-S2 pipeline: CDSE Sentinel-2 L2A → EU-calibrated DSWE thresholds → OPERA-spec COG GeoTIFF; JRC Global Surface Water validation; threshold calibration dataset documentation; `subsideo dswx` CLI.

**Addresses:** DSWx-S2 pipeline (table stakes), JRC validation (validation framework).

**Avoids:** Pitfall 12 (HLS vs native S2 L2A spectral mismatch); must re-calibrate DSWE thresholds — do not assume OPERA HLS thresholds transfer.

**Research flag:** DSWx threshold calibration methodology against CDSE S2 L2A is a scientifically non-trivial step with no existing published recipe for EU scenes; budget explicit research and calibration time within this phase.

### Phase 7: DIST-S1 Pipeline

**Rationale:** DIST-S1 depends on an RTC time series (Phase 3) and on the upstream opera-adt/dist-s1 library (~April 2026 release). It is placed last among product pipelines to avoid blocking on upstream release timing.

**Delivers:** DIST-S1 pipeline wrapping opera-adt/dist-s1; `subsideo dist` CLI; DIST COG GeoTIFF output.

**Addresses:** DIST-S1 pipeline (table stakes, timing-dependent).

**Avoids:** Timing risk from upstream dist-s1 release; do not start implementation until dist-s1 is published on conda-forge.

### Phase 8: Validation Framework

**Rationale:** Validation requires all product pipelines to produce outputs. However, the metric functions (pure numpy) and the EGMS comparison methodology must be designed before running any comparisons — the validation protocol document (EGMS version pinning, reference correction, snow masking rules) should be written at the start of this phase, before any numbers are computed.

**Delivers:** Validation framework with RMSE, spatial r, SSIM, F1 metrics; OPERA N.Am. comparison module; EGMS EU comparison module (with reference polynomial correction and snow masking); JRC water comparison module; HTML/Markdown report generator; `subsideo validate` CLI.

**Addresses:** Validation framework (table stakes and key differentiator), HTML validation reports (table stakes).

**Avoids:** Pitfall 10 (EGMS comparison methodology — CRS and temporal mismatch); write the protocol document first.

**Research flag:** EGMS v2 product format and download API should be verified against EGMStoolkit 0.2.15 capabilities before implementing the comparison module.

### Phase Ordering Rationale

- The dependency graph (burst DB → RTC → DIST; burst DB → CSLC → DISP; access layer → all pipelines) drives phases 1–5 sequentially; DSWx and DIST can shift without affecting CSLC/DISP.
- Building the `OperaProductValidator` in Phase 1 (not Phase 8) prevents HIGH-recovery-cost OPERA spec compliance failures discovered post-implementation.
- The CDSE canary integration test in Phase 2 must pass before any pipeline phase begins; a broken data access layer will waste weeks of debugging masked as algorithm errors.
- Validation is last because it requires outputs, but metric functions can be unit-tested with synthetic data from day one of Phase 8.

### Research Flags

Phases likely needing `/gsd:research-phase` deeper research during planning:

- **Phase 2 (CDSE data access):** CDSE S3 endpoint changed in September 2025 and STAC in November 2025; implementation patterns from 2024 tutorials are stale. Verify current `stac.dataspace.copernicus.eu/v1` CQL2 filter syntax and S3 path format before implementing.
- **Phase 4 (CSLC pipeline):** compass 0.5.6 + isce3 0.25.x version alignment and actual burst coregistration config schema need hands-on verification; OPERA ATBD is the reference but implementation gaps exist.
- **Phase 5 (DISP pipeline):** dolphin `WorkflowConfig` YAML schema and MintPy `smallbaselineApp` integration path for dolphin outputs are documented but have known configuration gotchas that need validation in the target environment.
- **Phase 6 (DSWx threshold calibration):** No published recipe exists for calibrating DSWE thresholds from OPERA HLS to native Sentinel-2 L2A over EU; this requires domain research, not just library documentation.

Phases with standard, well-documented patterns (skip research-phase):

- **Phase 1 (Environment):** conda-forge install patterns are well-established; the `environment.yml` structure is straightforward.
- **Phase 3 (RTC pipeline):** opera-rtc wrapping isce3 is the simplest ISCE3 workflow; well-documented in opera-adt/RTC.
- **Phase 8 (Validation framework):** Pure metric functions (RMSE, Pearson r, SSIM) are standard; jinja2 HTML reporting is straightforward.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Versions cross-checked against PyPI, conda-forge, and GitHub releases as of April 2026; critical version constraints (pyaps3, sentineleof, geopandas) verified against issue trackers |
| Features | HIGH (core), MEDIUM (anti-features) | Product specs verified against OPERA ATBDs and NASA Earthdata catalogue; anti-feature reasoning is inferred from scope analysis |
| Architecture | MEDIUM | ISCE3/dolphin/MintPy architecture verified via official repos and JOSS paper; subsideo-specific integration patterns are inferred from upstream repo structures, not from a deployed subsideo reference |
| Pitfalls | MEDIUM-HIGH | Installation and CDSE endpoint pitfalls are HIGH confidence (official docs, confirmed endpoint changes); EU burst DB gaps and phase unwrapping pitfalls are MEDIUM confidence (community reports and literature) |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **DIST-S1 upstream timing:** opera-adt/dist-s1 is listed as releasing ~April 2026; if the release slips, Phase 7 cannot begin. Monitor the dist-s1 GitHub repo; Phase 7 should be treated as a conditional phase until the package is confirmed on conda-forge.

- **DSWx threshold calibration dataset:** No training dataset of EU water/non-water labels for Sentinel-2 L2A is identified in the research. This must be sourced (likely from JRC Global Surface Water + CDSE S2 L2A scene co-registration) before Phase 6 can proceed.

- **CSLC-DISP round-trip test data:** Testing the full CSLC → DISP chain requires a time stack of CSLC products; generating these during development is expensive. Consider using a subset of OPERA N.Am. CSLC products (from ASF DAAC) for DISP pipeline development and EU CSLC products for integration testing only.

- **EGMS validation version pinning:** The research recommends EGMStoolkit 0.2.15 for EGMS data access, but does not confirm which EGMS product version (v1 or v2) will be used as the validation baseline. This must be decided before Phase 8 begins; mixing versions invalidates comparisons.

- **ERA5 CDS API key availability:** The `~/.cdsapirc` credential setup is required for DISP tropospheric correction. This is a personal API key; its availability in CI/CD and shared compute environments must be planned before Phase 5.

## Sources

### Primary (HIGH confidence)
- [isce3 Releases (GitHub)](https://github.com/isce-framework/isce3/releases) — version 0.25.10, March 2025
- [dolphin JOSS paper](https://joss.theoj.org/papers/10.21105/joss.06997) — peer-reviewed 2024
- [CDSE STAC documentation](https://documentation.dataspace.copernicus.eu/APIs/STAC.html) — official CDSE APIs
- [CDSE S3 API documentation](https://documentation.dataspace.copernicus.eu/APIs/S3.html) — official; endpoint change September 2025 confirmed
- [CDSE STAC legacy endpoint deprecation](https://sentinels.copernicus.eu/-/cdse-release-of-the-new-cdse-stac-catalogue) — November 2025
- [opera-adt/burst_db GitHub](https://github.com/opera-adt/burst_db) — official JPL repo; N.Am.-only confirmed
- [OPERA CSLC-S1 ATBD (JPL)](https://cumulus.asf.earthdatacloud.nasa.gov/PUBLIC/DATA/OPERA/OPERA_CSLC-S1_ATBD_D-108752_Initial_2024-06-24_signed.pdf) — algorithm specification
- [GLO-30 variable grid spacing (OpenTopography)](https://portal.opentopography.org/raster?opentopoID=OTSDEM.032021.4326.3) — documented in tile metadata
- [Scientific Python packaging guide](https://learn.scientific-python.org/development/guides/packaging-simple/) — hatchling recommendation

### Secondary (MEDIUM confidence)
- [MintPy FAQ and known issues](https://mintpy.readthedocs.io/en/latest/FAQs/) — CDS API configuration and ERA5 correction
- [pyaps3 CDS migration discussion](https://github.com/insarlab/PyAPS/discussions/40) — 0.3.6 credential format change
- [OPERA CSLC calval tools](https://github.com/OPERA-Cal-Val/calval-CSLC) — validation methodology
- [EGMStoolkit paper (Springer)](https://link.springer.com/article/10.1007/s12145-024-01356-w) — published 2024
- [EGMS validation limitations (ISPRS Archives)](https://isprs-archives.copernicus.org/articles/XLVIII-4-W7-2023/247/2023/) — snow effects and accuracy bounds

### Tertiary (LOW confidence)
- Anti-feature scope reasoning — inferred from OPERA roadmap and competitor analysis; validate against actual user requests when the project has early adopters
- DSWx threshold transfer from HLS to S2 L2A — inferred from spectral differences; no published EU calibration study found

---
*Research completed: 2026-04-05*
*Ready for roadmap: yes*
