# Feature Research

**Domain:** SAR/InSAR geospatial processing library — OPERA-equivalent products for EU AOIs
**Researched:** 2026-04-05
**Confidence:** HIGH (core product specs), MEDIUM (ecosystem comparisons), LOW (anti-feature reasoning)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features a SAR/InSAR processing library must have. Missing any of these means the library is not
usable for its stated purpose.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| RTC-S1 pipeline (backscatter) | Core Level-2 product; entry point for any Sentinel-1 analysis | HIGH | ISCE3 wraps the algorithm; main complexity is orbit/DEM acquisition and CDSE S3 integration |
| CSLC-S1 pipeline (coregistered SLC) | Required input for DISP; foundational burst-level product | HIGH | ISCE3 burst coregistration; must be geocoded to UTM at 5×10 m posting per OPERA spec |
| DISP-S1 pipeline (displacement time series) | Primary science output; users need mm-precision deformation maps | HIGH | dolphin (phase linking) + tophu (unwrapping) + MintPy (inversion); three chained tools |
| DSWx-S2 pipeline (dynamic surface water) | Water extent is a high-demand operational product | HIGH | Ports OPERA DSWx-HLS logic from Landsat+S2 HLS to CDSE S2-L2A; band mapping non-trivial |
| DIST-S1 pipeline (surface disturbance) | Land disturbance detection from RTC time series | HIGH | Wraps opera-adt/dist-s1; DIST-S1 itself releases ~April 2026 — timing risk |
| EU burst database | Without it no EU product can be identified or queried | HIGH | opera-burstdb covers N.Am. only; must build SQLite from ESA burst ID GeoJSON (CC-BY 4.0) |
| CDSE data access layer | All EU S1 SLC / S2 L2A data lives on CDSE S3 | MEDIUM | Non-standard S3 endpoint (`s3://eodata/`); requires CDSE credentials; needs STAC search |
| GLO-30 DEM download and tile management | Every RTC/CSLC/DISP run needs a DEM; without it pipelines fail silently | MEDIUM | Copernicus DEM GLO-30; tile stitching and UTM projection required |
| Orbit (POE/ROE) + ionosphere (IONEX) download | Precise orbits required for CSLC accuracy; IONEX for DISP corrections | MEDIUM | Multiple sources (ESA GNSS Service, CODE/JPL IONEX); fallback chain needed |
| HDF5 output for CSLC and DISP | OPERA spec compliance; interoperability with OPERA tooling (e.g., dolphin reads OPERA CSLC HDF5) | MEDIUM | Must follow CF-1.8 convention and OPERA HDF5 hierarchy per product spec documents |
| COG GeoTIFF output for RTC and DSWx | OPERA spec compliance; required for QGIS/GDAL consumption and cloud access patterns | MEDIUM | Internal tiling (256×256), overviews, LZW/DEFLATE compression; use GDAL COG driver |
| OPERA product metadata (HDF5 `/identification`) | Users and validators need product provenance, version, processing params | MEDIUM | RTC-S1 spec defines exact HDF5 variable names; must match exactly for validator interop |
| Typer-based CLI with subcommands | Scientists expect a command-line entry point for each product type | LOW | `subsideo rtc`, `subsideo cslc`, `subsideo disp`, `subsideo dswx`, `subsideo validate` |
| Pydantic settings configuration | Config from env vars + .env + per-run YAML is the modern Python scientific standard | LOW | Pydantic v2 `BaseSettings`; layered: env > dotenv > YAML > defaults |
| Loguru structured logging | Processing pipelines produce voluminous output; structured logs are essential for debugging | LOW | Replace stdlib `logging`; already chosen in PROJECT.md |

### Differentiators (Competitive Advantage)

Features that distinguish subsideo from running OPERA directly or using existing tools like pyroSAR or
HyP3. These address the core value: scientifically accurate OPERA-spec products over EU AOIs, validated.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| EU burst database (EU-scoped SQLite) | No other open-source tool publishes a validated EU burst→frame mapping; closes the N.Am.-only gap in opera-burstdb | HIGH | Built from ESA's CC-BY 4.0 burst ID GeoJSON; required for all CSLC/DISP frame consistency |
| CDSE-native data access | Competing tools (HyP3, pyroSAR) use ASF DAAC; CDSE is faster and more complete for EU | MEDIUM | Custom boto3 endpoint config; STAC search with `pystac_client`; no ASF DAAC roundtrip |
| Validation framework with pass/fail thresholds | Proves correctness against OPERA N.Am. and EGMS EU references; no other EU SAR lib does this | HIGH | RMSE/r/F1 metrics per product; OPERA comparison + EGMS calibration comparison |
| HTML/Markdown validation reports | Validation results are consumed by scientists and reviewers, not just automated CI | MEDIUM | Jinja2 templates or similar; per-run report with metric tables, maps, diff images |
| Multi-zone UTM handling for EU AOIs | EU spans UTM 28N–38N; zone-boundary AOIs silently produce artifacts without explicit handling | HIGH | Not a user-facing feature but a correctness guarantee; no competitor documents this |
| OPERA product spec compliance at output | Products can be ingested by any OPERA-aware tool (dolphin reads OPERA CSLC HDF5 directly) | MEDIUM | Strict adherence to OPERA product spec HDF5 hierarchy and COG structure |
| ERA5 tropospheric correction integration | MintPy + ECMWF CDS API for ERA5; reduces long-wavelength atmospheric noise in DISP | MEDIUM | Requires separate `~/.cdsapirc`; document clearly; verify DISP r > 0.92 threshold met |
| ASF DAAC access for N.Am. reference products | Enables cross-continental validation by fetching the same product type from OPERA N.Am. | LOW | Earthdata credentials; `earthaccess` library; validation-only path, not primary data |

### Anti-Features (Commonly Requested, Often Problematic)

Features that appear useful but should be deliberately excluded from v1 scope.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time / operational processing infrastructure | Scientists want "push new S1 acquisition → auto-run pipeline" | This is a PGE/SDS orchestration problem (Prefect, Airflow, OPERA SDS); building it couples library to infrastructure and creates a maintenance surface 10x the library itself | Document integration patterns; let users wire CLI into their own schedulers |
| Windows native support | Broader accessibility | ISCE3 + GDAL + snaphu conda stack does not build on Windows; WSL2 is the stated acceptable workaround; native support requires a separate CI matrix with no upstream support | Document WSL2 usage clearly |
| VLM (vertical land motion) product | Logical extension of DISP-S1 | OPERA itself deferred VLM to 2028; the algorithm requires GNSS calibration points and a separate inversion chain; adds a 6+ month scope | Defer to v2; stub module with `NotImplementedError` |
| GPU-accelerated processing as a first-class feature | dolphin supports JAX/CUDA for 5–20x speedup | GPU availability is not guaranteed on researcher workstations; adds CUDA dependency to install; dolphin already exposes GPU as optional | Document optional GPU usage in dolphin config; do not require it |
| Multi-mission support (NISAR, ERS, ENVISAT) | Wider applicability | Adds sensor-specific burst geometry, polarization mapping, and data access layers per mission; dilutes EU Sentinel-1/2 focus | Scope to S1/S2 only; add NISAR stub stubs only per PROJECT.md |
| Web UI / interactive dashboard | Lower barrier for non-CLI users | Out of scope for a Python library; Jupyter notebooks cover interactive exploration | Provide tutorial notebooks with Folium/ipyleaflet maps |
| Containerised production service / Docker image | Reproducibility and deployment | Two-layer install (conda + pip) is not trivially Dockerised; ISCE3 conda package size is large; maintaining Docker images is ongoing ops work | Provide environment.yml and conda-lock file instead |
| Automated data ordering / tasking | Some commercial SAR platforms support on-demand tasking | Sentinel-1 is free and continuously archived; tasking adds API key management and commercial dependency | Use STAC search against CDSE archive |

---

## Feature Dependencies

```
EU Burst Database
    └──required by──> CSLC-S1 pipeline
                          └──required by──> DISP-S1 pipeline
                                                └──requires──> Phase unwrapping (tophu/SNAPHU)
                                                └──requires──> MintPy time-series inversion
                                                    └──requires──> ERA5 via CDS API (optional correction)

CDSE Data Access Layer
    └──required by──> RTC-S1 pipeline
    └──required by──> CSLC-S1 pipeline
    └──required by──> DSWx-S2 pipeline (S2-L2A)

GLO-30 DEM
    └──required by──> RTC-S1 pipeline (terrain correction)
    └──required by──> CSLC-S1 pipeline (geocoding)

Orbit (POE/ROE) fetch
    └──required by──> CSLC-S1 pipeline (precise orbit state vectors)

RTC-S1 pipeline
    └──required by──> DIST-S1 pipeline (takes RTC time series as input)

Validation Framework
    └──requires──> ASF DAAC access (OPERA N.Am. reference products)
    └──requires──> EGMS comparison module (EU reference velocities)
    └──requires──> All product pipelines (something to validate)

CLI subcommands
    └──wraps──> all product pipelines
    └──wraps──> Validation Framework

Pydantic settings
    └──used by──> all product pipelines
    └──used by──> CLI subcommands
    └──used by──> Validation Framework
```

### Dependency Notes

- **EU Burst DB requires ESA burst ID GeoJSON:** The ESA burst ID map (CC-BY 4.0) is the source of truth; the SQLite must be built once and then shipped as a package data asset or downloaded on first use.
- **CSLC requires EU Burst DB:** Each burst must resolve to a consistent frame ID and UTM grid; without the DB, geocoding grid is non-deterministic per run.
- **DISP requires CSLC:** dolphin's phase linking operates on a stack of CSLC products; CSLC must precede any DISP run temporally and in pipeline ordering.
- **DIST-S1 requires RTC:** dist-s1 takes a time series of RTC backscatter images as input; RTC pipeline must be functional and producing spec-compliant COGs first.
- **DSWx-S2 is independent:** Does not depend on any SAR pipeline; uses S2 optical data only — can be developed in parallel with SAR pipelines.
- **Validation requires working pipelines:** The validation framework can only be built meaningfully once at least one pipeline produces outputs; RTC should be the first target.
- **ERA5 correction is optional at runtime:** MintPy can run without tropospheric correction; ERA5 enhances quality but is not a hard dependency for basic DISP outputs.

---

## MVP Definition

### Launch With (v1)

The minimum needed to demonstrate correctness of EU OPERA-equivalent products.

- [ ] EU burst database (SQLite, EU coverage) — without this nothing else works for EU
- [ ] CDSE data access layer (STAC search + S3 download for S1 SLC and S2 L2A) — gating dependency
- [ ] GLO-30 DEM download and tile management — required by both RTC and CSLC
- [ ] Orbit (POE/ROE) and IONEX fetch — required for CSLC accuracy
- [ ] RTC-S1 pipeline producing spec-compliant COG GeoTIFF — first validated product; simplest pipeline
- [ ] CSLC-S1 pipeline producing spec-compliant HDF5 — prerequisite for DISP
- [ ] DISP-S1 pipeline producing HDF5 displacement time series — primary science product
- [ ] DSWx-S2 pipeline producing COG GeoTIFF — independent; high downstream value
- [ ] DIST-S1 pipeline wrapping opera-adt/dist-s1 — dependent on DIST-S1 upstream release timing
- [ ] Validation framework with OPERA N.Am. comparison + EGMS comparison — proves correctness
- [ ] Validation report generation (HTML/Markdown) — required for any scientific acceptance
- [ ] CLI (`subsideo rtc|cslc|disp|dswx|dist|validate`) — required for usability
- [ ] Pydantic settings (env + .env + YAML) — required for reproducible runs

### Add After Validation (v1.x)

- [ ] ERA5 tropospheric correction — add once DISP baseline is validated; improves velocity accuracy
- [ ] GPU acceleration documentation — document dolphin JAX path once CPU baseline is confirmed working
- [ ] Tutorial Jupyter notebooks — once pipelines are stable, notebooks lower the barrier to adoption
- [ ] Conda-lock file and environment reproducibility tooling — needed before wider sharing

### Future Consideration (v2+)

- [ ] VLM (vertical land motion) — defer until OPERA publishes algorithm; ~2028 per OPERA roadmap
- [ ] NISAR support — stub only in v1; flesh out when NISAR science data products are available
- [ ] Batch processing helpers / parallelisation framework — premature without knowing real user scale patterns
- [ ] Additional validation baselines (GNSS network, PS-InSAR commercial) — valuable but not required for v1 correctness proof

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| EU burst database | HIGH | HIGH | P1 |
| CDSE data access layer | HIGH | MEDIUM | P1 |
| GLO-30 DEM management | HIGH | MEDIUM | P1 |
| Orbit + IONEX fetch | HIGH | MEDIUM | P1 |
| RTC-S1 pipeline | HIGH | HIGH | P1 |
| CSLC-S1 pipeline | HIGH | HIGH | P1 |
| DISP-S1 pipeline | HIGH | HIGH | P1 |
| DSWx-S2 pipeline | HIGH | HIGH | P1 |
| DIST-S1 pipeline | MEDIUM | HIGH | P1 (timing-dependent) |
| Validation framework (metrics) | HIGH | HIGH | P1 |
| Validation report generation | MEDIUM | MEDIUM | P1 |
| CLI subcommands | HIGH | LOW | P1 |
| Pydantic settings | HIGH | LOW | P1 |
| HDF5/COG output spec compliance | HIGH | MEDIUM | P1 |
| OPERA metadata hierarchy | MEDIUM | MEDIUM | P1 |
| Multi-zone UTM handling | HIGH | HIGH | P1 (correctness, not user-facing) |
| ERA5 tropospheric correction | MEDIUM | MEDIUM | P2 |
| ASF DAAC access (validation only) | MEDIUM | LOW | P1 (validation path) |
| GPU acceleration docs | LOW | LOW | P2 |
| Tutorial notebooks | MEDIUM | LOW | P2 |
| Conda-lock reproducibility | MEDIUM | LOW | P2 |
| VLM product | LOW | HIGH | P3 |
| NISAR support | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for v1 launch
- P2: Should have; add post-validation
- P3: Nice to have; defer to v2+

---

## Competitor Feature Analysis

| Feature | OPERA (JPL/ASF) | pyroSAR + SNAP | HyP3 (ASF cloud service) | subsideo (this project) |
|---------|-----------------|----------------|--------------------------|------------------------|
| RTC product | YES — N.Am. only | YES — SNAP-based, not OPERA spec | YES — OPERA-spec, N.Am. only | YES — EU, OPERA spec via ISCE3 |
| CSLC product | YES — N.Am. only | NO | NO | YES — EU, OPERA spec |
| DISP product | YES — N.Am. only | NO | NO | YES — EU |
| DSWx product | YES (HLS-based) | NO | NO | YES — CDSE S2-L2A adaptation |
| DIST product | YES — N.Am. (~April 2026) | NO | NO | YES — wraps dist-s1 |
| EU coverage | NO | YES (any region) | NO | YES — primary target |
| CDSE-native access | NO (ASF DAAC) | NO (various) | NO (ASF DAAC) | YES |
| Validation framework | Internal only | NO | NO | YES — vs OPERA + EGMS |
| CLI | PGE/SDS internal | YES (Python API) | REST API only | YES — Typer subcommands |
| Open-source library | YES (isce3, dolphin) | YES | NO (service) | YES |
| Output spec compliance | YES (reference) | Partial | YES | YES — matches OPERA spec |

---

## Sources

- [OPERA ASF Landing Page](https://asf.alaska.edu/datasets/daac/opera/)
- [NASA Earthdata OPERA Project](https://www.earthdata.nasa.gov/data/projects/opera)
- [OPERA DISP-S1 Product — NASA Earthdata](https://www.earthdata.nasa.gov/data/catalog/asf-opera-l3-disp-s1-v1-1)
- [OPERA RTC-S1 Product Spec PDF](https://d2pn8kiwq2w21t.cloudfront.net/documents/ProductSpec_RTC-S1.pdf)
- [OPERA CSLC-S1 Specs GitHub](https://github.com/opera-adt/CSLC-S1_Specs)
- [dolphin GitHub (isce-framework)](https://github.com/isce-framework/dolphin)
- [dolphin JOSS paper](https://joss.theoj.org/papers/10.21105/joss.06997)
- [opera-utils GitHub](https://github.com/opera-adt/opera-utils)
- [burst_db GitHub](https://github.com/opera-adt/burst_db)
- [MintPy GitHub](https://github.com/insarlab/MintPy)
- [dist-s1 GitHub](https://github.com/opera-adt/dist-s1)
- [CDSE S3 access documentation](https://documentation.dataspace.copernicus.eu/APIs/S3.html)
- [CDSE APIs overview](https://documentation.dataspace.copernicus.eu/APIs.html)
- [EGMS — Copernicus Land Monitoring Service](https://land.copernicus.eu/en/products/european-ground-motion-service)
- [COG OGC Standard](https://docs.ogc.org/is/21-026/21-026.html)
- [ESA burst ID map publication forum post](https://forum.step.esa.int/t/publication-of-official-burst-id-maps/36328)
- [OPERA DSWx-HLS NASA Earthdata](https://www.earthdata.nasa.gov/data/catalog/pocloud-opera-l3-dswx-hls-v1-1.0)
- [OPERA DIST-S1 GitHub](https://github.com/opera-adt/dist-s1)
- [OPERA near-global DIST product suite](https://www.earthdata.nasa.gov/data/projects/nsite/solutions/opera-near-global-surface-dist-product-suite)
- [Pydantic Settings docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

---

*Feature research for: SAR/InSAR geospatial processing library (subsideo)*
*Researched: 2026-04-05*
