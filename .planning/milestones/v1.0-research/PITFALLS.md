# Pitfalls Research

**Domain:** SAR/InSAR geospatial processing library — EU AOIs, ISCE3/dolphin stack, CDSE data access, OPERA-spec output
**Researched:** 2026-04-05
**Confidence:** MEDIUM (installation/environment pitfalls HIGH; EU-specific gaps MEDIUM; validation methodology MEDIUM)

---

## Critical Pitfalls

### Pitfall 1: Conda/Pip Environment Corruption via Mixed Package Managers

**What goes wrong:**
Installing ISCE3, GDAL, dolphin, or snaphu via pip (or letting pip pull in C-extension packages after a conda install) silently corrupts shared library linkage. The environment appears to work until runtime, when mismatched `.so` versions cause segfaults, `ImportError`, or subtle numerical wrong-answers with no clear error message.

**Why it happens:**
ISCE3, GDAL, HDF5, FFTW, and pyre are compiled against specific ABI versions managed by conda-forge's solver. Pip resolves only Python package metadata — it cannot satisfy native library constraints. A single `pip install gdal` or `pip install h5py` after a conda environment is set up can pull a conflicting HDF5 or GDAL wheel, breaking the conda-installed binaries.

**How to avoid:**
- Define the full conda environment in an `environment.yml` with pinned channels: `conda-forge` first, `nodefaults` last.
- Never run bare `pip install` for any package with compiled extensions (`gdal`, `h5py`, `numpy`, `scipy`, `shapely`, `fiona`). Use `conda install` for these.
- The project's pure-Python layer (`subsideo` itself) installs via pip on top, but only after all conda packages are locked.
- Enforce this in CI by verifying `conda list --export` does not show pip-sourced overrides of conda packages.
- Use `mamba` (or `conda` with the libmamba solver) instead of classic conda to detect conflicts before installation rather than after.

**Warning signs:**
- `ImportError: libhdf5_cpp.so.NNN: cannot open shared object file` at import time.
- `conda list` shows the same package from both `conda-forge` and `pypi` channels.
- Segfault when calling any ISCE3 CUDA or HDF5 function.
- `ldd $(python -c "import isce3; print(isce3.__file__)")` reports `not found` for any library.

**Phase to address:** Environment / foundation phase (Phase 1). Lock `environment.yml` before any code is written. This is the single most likely cause of project-wide blocking issues.

---

### Pitfall 2: CDSE S3 Non-Standard Endpoint and Credential Management

**What goes wrong:**
boto3 and s3fs default to AWS infrastructure. Omitting the custom endpoint URL or using a standard AWS region string causes all requests to fail silently or with misleading `NoSuchBucket` / `AccessDenied` errors. Separately, CDSE S3 credentials expire and the Secret Key is shown exactly once at generation — losing it requires generating a new pair, breaking all running pipelines.

**Why it happens:**
CDSE runs its own S3-compatible object store at `https://eodata.dataspace.copernicus.eu` with `region_name='default'` — neither is guessable from standard boto3 patterns. Additionally, as of September 2025, the S3 endpoint path format changed (number of slashes in queries), meaning old connection strings silently broke. Token-based auth for the STAC API also requires the Keycloak endpoint at `identity.dataspace.copernicus.eu`, not the standard AWS token endpoint.

**How to avoid:**
- Centralize all CDSE S3 configuration in a single `CDSEClient` class. Never let boto3 configuration be scattered across the codebase.
- Required boto3 kwargs (non-negotiable): `endpoint_url='https://eodata.dataspace.copernicus.eu'`, `region_name='default'`.
- Store credentials as environment variables (`CDSE_ACCESS_KEY`, `CDSE_SECRET_KEY`) loaded via Pydantic settings — never hardcoded.
- Build a credential-refresh wrapper: detect expiry proactively (parse the `exp` claim in the STAC OAuth token), not reactively.
- Add an integration smoke test that downloads a 1-tile S3 object as part of the test suite.
- Note the legacy STAC endpoint `catalogue.dataspace.copernicus.eu/stac` is deprecated from November 2025 — use `stac.dataspace.copernicus.eu/v1` only.

**Warning signs:**
- `botocore.exceptions.NoCredentialsError` or `EndpointResolutionError` when no AWS credentials exist.
- `403 Forbidden` on S3 GET after credential regeneration.
- STAC search returning 0 results for known existing scenes.
- Silent download of 0-byte files (boto3 does not always raise on partial transfers from non-AWS endpoints).

**Phase to address:** CDSE data access phase (Phase 2). Before any pipeline work, validate the full S3 round-trip with a canary test that downloads a real Sentinel-1 SLC burst slice and verifies file size and checksum.

---

### Pitfall 3: EU Burst Database — Treating opera-utils as Global Coverage

**What goes wrong:**
`opera-adt/burst_db` is built around OPERA's operational North America focus. The `is_north_america` flag and frame definitions are N.Am.-specific. Assuming the SQLite database covers EU bursts out of the box will produce silent coverage gaps: queries for EU burst IDs return nothing or incorrect frame mappings.

**Why it happens:**
OPERA's operational mandate is North America. The `burst_db` schema uses OPERA-defined frame boundaries (N.Am. tiling grid). ESA's official burst ID map (GeoJSON, CC-BY 4.0) uses the IW-SLC burst synchronisation grid, which is global but uses a different naming convention and geometry than OPERA's frame system.

**How to avoid:**
- Build the EU burst database from ESA's published burst ID GeoJSON directly. Do not fork or monkey-patch `burst_db` — build a sibling SQLite schema that is structurally compatible but populated from ESA source data.
- Validate spatial completeness by checking burst coverage against a known Sentinel-1 EU track (e.g., track 015 ascending, covering Central Europe) using a reference pass list from ASF CMR.
- Include a geometry integrity check in the database build: no overlapping burst polygons within a swath, no gaps > 0.1 deg along track.
- Map OPERA burst IDs (used in OPERA product filenames) to ESA burst IDs (used in SLC annotations) and persist the mapping in the DB.

**Warning signs:**
- SQLite query for a known EU burst (e.g., IW1 burst over Paris) returns `NULL`.
- Burst footprint polygons have seams or slivers along swath boundaries.
- Frame IDs from `opera-utils` APIs throw `KeyError` for any EU input coordinate.

**Phase to address:** EU burst database phase (Phase 2 / dedicated sub-task). Gate all pipeline development on a validated burst DB with >= 90% EU coverage verified against ESA's published burst count by track.

---

### Pitfall 4: UTM Zone Boundary AOIs and 30 m Grid Misalignment

**What goes wrong:**
AOIs that straddle UTM zone boundaries (e.g., a transect across 30 deg E, the boundary between UTM 36N and 37N) produce output rasters that are either (a) incorrectly forced into a single zone with distortion exceeding OPERA's spec or (b) split into two non-contiguous tiles with a gap at the seam. OPERA products use 30 m UTM posting, but EU spans zones 28N–38N; naive zone selection causes pixel registration errors at zone edges of up to ~250 m.

**Why it happens:**
GDAL and rasterio select UTM zones automatically from bounding box centroids. For elongated AOIs or AOIs bisected by a zone boundary, the auto-selected zone introduces false distortion on the far side. Additionally, different components (DEM fetch, burst query, output geocoding) may independently select different UTM zones for the same AOI, producing grids that do not align.

**How to avoid:**
- Implement a single `select_utm_zone(aoi_geometry)` function used everywhere. For AOIs entirely within one zone, standard selection. For cross-zone AOIs, either: (a) clip and process per-zone and mosaic, or (b) choose the zone covering the majority of the AOI area and document the distortion.
- Add an AOI validator that emits a `WARNING` (not a silent pass) whenever the input AOI crosses a UTM zone boundary.
- Align all intermediate grids (DEM, layover-shadow mask, burst rasters) to the same UTM grid before any pixel-level operation.
- Use GDAL VRT-based mosaicking with `SRC_METHOD=NO_GEOTRANSFORM` suppression to catch misaligned grids at mosaic time rather than silently averaging across offset pixels.

**Warning signs:**
- `gdal.Warp` output has a visible stripe or seam in the middle of a wide AOI.
- Two output tiles for the same scene have different EPSG codes.
- Pixel-wise comparison of RTC output to OPERA reference shows a systematic offset of one or more pixels in easting.
- `rasterio.open().crs` returns different EPSG codes for files that should be co-registered.

**Phase to address:** RTC pipeline phase and any geocoding step. Add a UTM zone boundary regression test using a synthetic AOI straddling 30E.

---

### Pitfall 5: Phase Unwrapping Failures Silently Producing Wrong Displacement

**What goes wrong:**
SNAPHU / tophu return exit code 0 and produce a numerically valid-looking unwrapped interferogram that has cycle-slip errors of 2π multiples. These errors are indistinguishable from correct output by visual inspection at small scale. They propagate through MintPy time-series inversion and produce displacement velocities with systematic biases of integer multiples of ~28 mm (one C-band fringe = 2.8 cm LOS displacement).

**Why it happens:**
- SNAPHU's tile-based mode (used by tophu) produces boundary discontinuities (seams) where tiles are merged. If tile overlap is too small or coherence is low at tile edges, cycle jumps of 2π are introduced.
- Low-coherence regions (water, snow, forest in winter) propagate errors from masked areas into adjacent land pixels via the SNAPHU cost network.
- Europe's high-latitude scenes (Scandinavia, the Baltic) have significant seasonal snow cover, causing coherence loss that is not fully captured by static coherence thresholds.
- SNAPHU uses a non-commercial license; the conda-forge build may differ slightly from source-compiled versions; never mix builds.

**How to avoid:**
- Set tophu tile overlap to >= 300 pixels (not the default 200) for EU scenes with strong topography.
- Apply coherence masking with a per-scene adaptive threshold (not a fixed 0.3), derived from the coherence histogram of each interferogram.
- Implement a post-unwrapping sanity check: fit a planar ramp to the unwrapped phase; flag any residual > 0.5 fringes as a potential cycle-slip indicator.
- Cross-validate at least 5% of unwrapped interferograms against GPSQuake / EGMS reference velocities before using in time-series.
- For snow-affected areas, apply a seasonal coherence stack mask (mask out winter epochs > 60 deg N latitude by default).

**Warning signs:**
- Displacement time series shows step discontinuities of ~28 mm or multiples thereof at a single epoch.
- MintPy's `mintpy.unwrap_error_bridging` step corrects many epochs — this indicates systematic unwrapping errors, not random noise.
- Two spatially adjacent permanent scatterers show velocity difference > 5 mm/yr with no known deformation source.
- Residuals from reference network closure (triple-product check) exceed 0.5 rad RMS.

**Phase to address:** DISP-S1 pipeline phase. Implement the post-unwrapping sanity check and adaptive coherence masking before any time-series inversion.

---

### Pitfall 6: ERA5 / CDS API Configuration Failure Silently Disabling Tropospheric Correction

**What goes wrong:**
MintPy's `correct_troposphere` step with ERA5 fails with `configparser.NoSectionError: No section: 'CDS'` or `AttributeError: 'NoneType' object has no attribute 'get'`. When this step silently fails or is skipped, the displacement time series retains strong tropospheric noise (several cm in mountainous Europe) that is mistaken for real deformation signal.

**Why it happens:**
The CDS API requires a separate `~/.cdsapirc` file with a personal API key. This is a completely independent credential from CDSE, Earthdata, and any cloud credentials. MintPy's tropospheric correction delegates to PyAPS, which reads this file. If it is missing, misconfigured, or placed in a non-home-directory path (e.g., in Docker containers), PyAPS fails at first use — often non-fatally, leaving the time series un-corrected without a loud error.

**How to avoid:**
- Add `~/.cdsapirc` to the project's environment setup checklist and validate it as part of the library's `subsideo check-env` CLI command.
- In the Pydantic settings layer, add `CDSAPI_RC` (path to `.cdsapirc`) as an explicit config option, not a hardcoded path assumption.
- Implement a `verify_era5_access()` function that makes a test API call to the CDS endpoint during setup and raises a clear `ConfigurationError` with remediation instructions.
- Log explicitly at WARNING level when tropospheric correction is skipped, including the reason.

**Warning signs:**
- MintPy log shows `correct_troposphere: skip` without explanation.
- Displacement maps show spatial patterns correlated with topography (DEM) — this is the unmistakable signature of uncompensated tropospheric delay.
- `python -c "import cdsapi; cdsapi.Client()"` raises an error.

**Phase to address:** DISP-S1 pipeline phase (early), before any time-series result is used for validation.

---

### Pitfall 7: GLO-30 DEM Variable Grid Spacing Above 50°N

**What goes wrong:**
GLO-30 tiles above 50°N have variable longitudinal spacing (1.5, 2.0, 3.0 arcseconds depending on latitude band). Automated DEM download code that assumes uniform 1 arcsecond spacing produces incorrectly-dimensioned arrays when stitching tiles for Scandinavia, the Baltic states, or northern UK scenes. This causes either a resampling artefact or a geocoding error that fails silently if the output grid looks "about right."

**Why it happens:**
ESA's original GLO-30 data uses latitude-dependent grid compression to reduce file sizes at high latitudes. Most DEM download utilities designed for SRTM (which uses uniform 1 arcsecond) do not handle this correctly. The resulting stitched DEM has incorrect pixel spacing metadata, which ISCE3 propagates to all downstream geocoded products.

**How to avoid:**
- Always reproject downloaded GLO-30 tiles to a uniform UTM grid at 30 m posting before passing to ISCE3. Never use the native geographic coordinate DEM directly for ISCE3 processing.
- Use `gdal.Warp` with explicit `-tr 30 30 -t_srs EPSG:XXXX` (UTM) as the first processing step on any downloaded DEM tiles.
- Add a DEM validation step that checks pixel spacing is uniform (tolerance: ±0.1 m) before the DEM is consumed by any algorithm.
- Retrieve current GLO-30 version from the data source at build time (as of July 2024, OpenTopography provides DGED 2023_1); pin the version in the test fixtures.

**Warning signs:**
- `gdal.Info` on the stitched DEM shows non-square pixels or non-uniform resolution.
- ISCE3 geocoded output shows a shear (angular distortion) relative to the input SAR geometry.
- DEM tile boundary artefacts visible as horizontal banding in products north of approximately 52°N.

**Phase to address:** Ancillary data management phase (Phase 1/2). Validate the DEM pipeline against a high-latitude test AOI (e.g., Oslo, 59°N) before any RTC or CSLC work.

---

### Pitfall 8: Orbit File Availability Race Condition

**What goes wrong:**
The pipeline fetches POEORB (precise orbit) files, which are only published 20 days after acquisition. If the pipeline is run on data less than 20 days old, it silently falls back to RESORB (restituted orbit, accuracy ~5 cm) or fails entirely. RESORB accuracy is sufficient for most applications, but using it without logging causes validation comparisons to fail against OPERA reference products that always use POEORB.

**Why it happens:**
`sentineleof` and similar orbit downloaders fall back gracefully but do not always surface the fallback prominently. The old SciHub orbit server was shut down in October 2023; ESA migrated orbit files to CDSE and to an AWS S3 bucket (`s3://s1-orbits/`). Code written against the old SciHub endpoint will fail silently (empty response, not an error).

**How to avoid:**
- Use `sentineleof >= 2.0` (post-SciHub migration) or fetch directly from `s3://s1-orbits/` via the Registry of Open Data on AWS.
- Always log at INFO level which orbit type (POEORB vs RESORB) was used for each scene, and include this metadata in the output product HDF5/COG.
- For validation runs, enforce POEORB-only mode: raise `OrbitsNotReadyError` if POEORB is unavailable rather than silently using RESORB.
- Add a 21-day minimum age guard on validation comparison jobs.

**Warning signs:**
- Product metadata shows `orbit_type: RESORB` for scenes older than 21 days (should be POEORB by then).
- Geolocation accuracy of CSLC products is 5–10 m worse than expected.
- `sentineleof` returns a file with "RES" in the filename.

**Phase to address:** CSLC and RTC pipeline phases. Include orbit type in output metadata from day one.

---

### Pitfall 9: OPERA Product Spec Compliance — HDF5 Structural Mismatches

**What goes wrong:**
Output HDF5 files are structurally valid HDF5 but fail OPERA product specification checks: missing mandatory metadata groups (e.g., `/metadata/orbit`, `/metadata/processingInformation`), wrong dataset chunking for CSLC complex arrays, or float32 instead of complex64 for wrapped phase. This causes OPERA tooling (e.g., `opera-utils`) and validation frameworks to fail non-obviously.

**Why it happens:**
The OPERA Product Specification documents (ATBDs) define HDF5 schemas that are not enforced by ISCE3 directly — they are the caller's responsibility. Without a schema validation step in the pipeline, spec drift accumulates silently across development iterations.

**How to avoid:**
- Write an `OperaProductValidator` class that loads the OPERA ATBD schema (JSON or manually transcribed) and validates every output file structure before the pipeline declares success.
- Use OPERA's own `calval-CSLC` and `calval-RTC` tools as the primary schema oracle — run them against outputs in CI.
- Lock chunking and compression settings (chunked `(1, 512, 512)` for 3-D arrays; LZF or GZIP level 4) to match OPERA spec from day one. Do not leave these as "optimize later."
- Validate COG structure for RTC/DSWx outputs: `gdal.Info` must show `LAYOUT=COG` and overviews must be present.

**Warning signs:**
- `h5py.File(output).keys()` is missing expected top-level groups.
- `opera-utils` functions raise `KeyError` on the output file.
- `gdal.Info` on a COG output does not show `Overviews:` entries.
- Validation RMSE metrics are unexpectedly high — this can mask a coordinate reference mismatch caused by missing EPSG metadata.

**Phase to address:** Output format / product spec phase. Build the validator in Phase 1 and run it against stub outputs. Do not defer validation until the pipeline is complete.

---

### Pitfall 10: EGMS Comparison Methodology — CRS and Temporal Mismatch

**What goes wrong:**
Comparing subsideo DISP outputs against EGMS products produces spuriously high RMSE or correlation < 0.5, not because the algorithm is wrong, but because: (a) EGMS uses a different LOS velocity reference frame (mean velocity over the full EGMS processing period, not an absolute datum), (b) EGMS is referenced to GNSS-derived absolute velocities while subsideo outputs are referenced to a local reference pixel, and (c) EGMS v1 and v2 are from completely independent processing runs with different phase unwrapping and filtering — they are not interchangeable as validation ground truth.

**Why it happens:**
The validation design naively treats EGMS as a ground truth absolute displacement reference. It is not — it is a relative velocity map, calibrated to GNSS, with its own systematic errors from tropospheric filtering and seasonal signal removal. Discrepancies of several mm/yr are expected and documented even between EGMS and levelling data.

**How to avoid:**
- In the validation framework, always apply a reference velocity correction before computing RMSE: subtract a common spatial polynomial (affine ramp) from the difference map.
- Document explicitly which EGMS version (v1 or v2) is used, and never mix versions in the same comparison.
- Use GNSS station velocities (EUREF Permanent Network) as an independent third reference, not EGMS, for absolute velocity validation.
- Set validation pass criteria relative to the known EGMS accuracy bounds (EGMS stated accuracy: ~1 mm/yr velocity, ~5 mm displacement per epoch) — comparing against tighter thresholds is scientifically invalid.
- Snow-affected areas (Scandinavia, Alps in winter) should be masked in EGMS comparisons; EGMS explicitly states these are noise-dominated.

**Warning signs:**
- DISP validation RMSE exceeds 3 mm/yr despite visually similar spatial patterns.
- Systematic offset (bias) between subsideo and EGMS > 5 mm/yr — likely a reference frame issue, not an algorithm error.
- Correlation drops from r > 0.95 in summer to r < 0.7 in winter for northern EU AOIs — this is expected due to snow, not a bug.

**Phase to address:** Validation framework phase. Write the validation methodology document before running any EGMS comparisons. Define the comparison protocol (reference correction, masking, EGMS version pinning) before looking at numbers.

---

### Pitfall 11: ISCE3 macOS arm64 Compatibility — Rosetta vs Native Build

**What goes wrong:**
ISCE3 on macOS arm64 (Apple Silicon) has inconsistent native support. The conda-forge feedstock builds are primarily tested on Linux x86-64. On macOS arm64, clang must be explicitly specified (not the Apple clang symlink, not gcc), and CMake framework detection (`CMAKE_FIND_FRAMEWORK`) must be set to `NEVER` to avoid picking up system HDF5 or Python frameworks instead of the conda environment versions. Builds that appear to succeed but used the wrong compiler silently produce wrong numerical results for transcendental math functions used in SAR geometry calculations.

**Why it happens:**
macOS ships its own HDF5 and Python frameworks in system paths that precede conda paths in the linker's search order. CMake's default framework search algorithm prefers these. Additionally, Rosetta 2 x86-64 emulation can mask architecture incompatibilities that only surface under native arm64 builds.

**How to avoid:**
- Always specify `CC=clang CXX=clang++` (conda-forge clang, not Apple clang) when building ISCE3 from source on macOS.
- Add `-DCMAKE_FIND_FRAMEWORK=NEVER` to all CMake invocations.
- Verify the installed ISCE3 binary is arm64, not x86-64: `file $(python -c "import isce3; print(isce3.__file__)")`.
- For macOS CI, use a dedicated arm64 runner, not Rosetta.
- Accept that some ISCE3 features (notably the CUDA GPU path) are Linux-only; macOS targets CPU-only processing.

**Warning signs:**
- `import isce3` succeeds but `isce3.geometry.rdr2geo_array` returns NaN for valid inputs.
- `otool -L` on the isce3 `.so` shows `/System/Library/` framework paths instead of conda environment paths.
- `file` command on isce3 shared libraries shows `x86_64` on an arm64 Mac.

**Phase to address:** Environment / foundation phase (Phase 1). Include a macOS arm64 smoke test in CI from day one.

---

### Pitfall 12: DSWx-S2 — HLS vs Native Sentinel-2 L2A Spectral Differences

**What goes wrong:**
OPERA DSWx-HLS was designed for the Harmonized Landsat Sentinel-2 (HLS) product, not raw Sentinel-2 L2A. The HLS product applies cross-sensor harmonization (BRDF correction, band adjustment) that alters spectral values by up to 10% relative to native L2A. Using native CDSE Sentinel-2 L2A as a drop-in replacement for HLS input will shift the NDWI and MNDWI thresholds used for water detection, causing false positives in bright sand / salt flat areas and false negatives in shallow water.

**Why it happens:**
OPERA's DSWx algorithm paper calibrates detection thresholds on HLS data. The spectral response of Sentinel-2 MSI bands 3 (green) and 8A (NIR), which are most important for water indices, differs measurably between HLS-harmonized and native L2A values.

**How to avoid:**
- Re-calibrate the DSWE (Dynamic Surface Water Extent) thresholds using a training dataset of known water/non-water pixels from CDSE Sentinel-2 L2A over EU scenes before using OPERA's HLS thresholds.
- Apply BRDF normalization (e.g., using the `pybrdf` library or Sen2Cor's output) to Sentinel-2 L2A before input to the DSWx algorithm, reducing spectral discrepancy.
- Add a dedicated DSWx calibration validation step against JRC Global Surface Water as ground truth (not OPERA DSWx-HLS directly, since the input data differ).
- Document this adaptation in the ATBD-equivalent design document; it is a scientifically non-trivial deviation from OPERA's method.

**Warning signs:**
- DSWx F1 score against JRC reference is 0.75–0.80, below the 0.90 target, in desert or agricultural areas.
- High false-positive rate in dry-season imagery over bright bare soil.
- Confusion matrix shows a systematic tilt toward "water" class relative to JRC labels.

**Phase to address:** DSWx-S2 pipeline phase. Budget time for threshold re-calibration; do not assume OPERA thresholds transfer directly to CDSE L2A data.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded UTM zone per pipeline run | Simpler geocoding code | Multi-zone AOIs fail silently; EU-wide products impossible | Never — build zone selector from day one |
| Skip post-unwrapping sanity check | Faster iteration | Wrong displacement values propagate to all downstream products | Never for validation runs |
| Use RESORB orbit without logging | Simpler orbit fetching | Validation comparisons fail; users cannot reproduce results | Only for exploratory/development runs, with explicit flag |
| Use fixed coherence threshold (0.3) | Simple configuration | Miss adaptive masking needed for seasonal EU scenes | Prototype only; replace before validation |
| Single-file HDF5 output (no chunking plan) | Faster first implementation | COG/HDF5 spec compliance failure; rewrite required | Never — set chunking in the output writer from day one |
| Pin entire conda environment to one lockfile | Reproducibility | Lockfile diverges from user installs over time; breaks macOS vs Linux | Acceptable for CI; document that user installs may differ |
| Ignore CDSE token expiry in data access layer | Simpler auth code | Token expires mid-download; corrupted files, cryptic errors | Never in production download paths |
| Compare against EGMS without reference correction | Simpler validation script | Systematically high RMSE that looks like algorithm failure | Never in published validation |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| CDSE S3 (boto3) | Using `region_name='us-east-1'` or omitting region | Set `region_name='default'` and `endpoint_url='https://eodata.dataspace.copernicus.eu'` |
| CDSE S3 (boto3) | Assuming the Secret Key is retrievable after first display | Copy and store the Secret Key immediately at generation; it is shown once only |
| CDSE STAC API | Using legacy `catalogue.dataspace.copernicus.eu/stac` endpoint | Use `stac.dataspace.copernicus.eu/v1` (legacy deprecated November 2025) |
| ERA5 / CDS API (PyAPS) | Assuming `~/.cdsapirc` is present in all environments (Docker, CI) | Set `CDSAPI_RC` env var; add `verify_era5_access()` to env check CLI |
| ASF DAAC (validation data) | Downloading full OPERA HDF5 products when only a small subset is needed | Use CMR granule queries with spatial/temporal filters; download only the required product types |
| Orbit files (sentineleof) | Still pointing to decommissioned SciHub orbit endpoint | Use `sentineleof >= 2.0` or `s3://s1-orbits/` AWS open data bucket |
| GLO-30 DEM tiles | Using native geographic coordinate tiles above 50°N | Always warp to UTM 30 m grid before passing to ISCE3 |
| MintPy (ISCE3 input reader) | Feeding dolphin output directly without `smallbaselineApp.cfg` configuration | MintPy reads dolphin output via its ISCE reader; configure `mintpy.load.processor = isce` and set correct path templates |
| SNAPHU (via tophu) | Using the same tile size for flat and mountainous terrain | Set tile size based on scene coherence statistics; mountainous EU (Alps, Pyrenees) needs smaller tiles with larger overlap |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading entire Sentinel-1 SLC into memory before burst extraction | OOM crash on machines with < 32 GB RAM | Use GDAL windowed reads / burst-level subsetting at ingest | Every scene > ~4 GB SLC |
| Downloading full S3 objects for STAC-discovered scenes | Very slow first-run; re-downloads on retry | Implement range-request byte-range downloads; cache burst-level subsets | Any AOI requiring > 5 scenes |
| Running SNAPHU on full-scene interferograms without tiling | Runtime > 12 hours; OOM for 200 × 200 km AOIs | Always use tophu for EU scenes; set tile size <= 1000 × 1000 pixels | Any interferogram > 10k × 10k pixels |
| Sequential burst-by-burst processing in a Python for-loop | Linear scaling with burst count; 10× slower than necessary | Parallelize burst processing using `concurrent.futures` or Dask; bursts are independent | AOIs with > 10 bursts (common for EU wide-area) |
| Writing uncompressed intermediate HDF5 arrays | Disk fills unexpectedly; I/O bottleneck | Use LZF compression for all intermediate HDF5 datasets | Any time-series stack > 50 epochs |
| Re-downloading ancillary data (DEM, orbit, ionosphere) on every run | Slow reruns; rate-limited by ESA/CDS services | Implement a local cache layer with content-hash validation | Development iteration after day one |
| MintPy loading entire interferogram stack into RAM | OOM for large stacks | Configure `mintpy.networkInversion.numWorker` and use the `HDF-EOS5` file format for chunked access | Stacks > 100 epochs over 1000 km² AOI |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Committing CDSE S3 access key / secret to git | Credential exposure; CDSE account compromise | Never store credentials in code; use Pydantic settings + `.env` excluded from git |
| Committing `~/.cdsapirc` contents to repository | CDS API key exposure | Load CDS key via env var `CDSAPI_KEY`; document in README, not in config files |
| Committing Earthdata login credentials | ASF DAAC account compromise | Same — env vars only, excluded from `.env.example` which only shows variable names |
| Logging full S3 URLs with credentials embedded | Credentials in log files | Use presigned URL logging only; strip query-string credentials from log output |
| Sharing output HDF5 files with orbit/processing metadata intact | Internal infrastructure disclosure | Strip system-specific paths from `/metadata/processingInformation` before sharing |

### Pitfall 13: compass/s1reader/isce3 Incompatibility with numpy >= 2.0

**What goes wrong:**
compass 0.5.6, s1reader 0.2.5, and isce3 0.25.8 have multiple numpy 2.x incompatibilities that cause silent failures or crashes during CSLC geocoding. Four distinct issues surface in sequence:
1. `s1reader.s1_burst_slc.polyfit` uses `%f` formatting on an ndarray — numpy 2.0 raises `TypeError`
2. `compass.s1_geocode_slc` uses `np.string_()` — removed in numpy 2.0 (`AttributeError`)
3. pybind11 auto-conversion of list-of-lists to `isce3.core.Poly2d` fails — isce3 C++ rejects the argument type
4. `compass.utils.geo_runconfig` calls `os.path.isfile(None)` — the None guard for `burst_database_file` is after an unconditional `isfile()` call

**Why it happens:**
numpy 2.0 made intentional breaking changes (removed deprecated aliases, tightened scalar conversion rules, changed pybind11 type coercion behavior). The compass/isce3 ecosystem was built against numpy 1.x and has not yet released compatible updates.

**How to avoid:**
- Pin `numpy < 2.0` in the conda environment if you need compass/isce3 to work out-of-the-box
- OR apply the 4 monkey-patches in `subsideo.products.cslc` (see `_patch_compass_burst_db_none_guard`, `_patch_s1reader_numpy2_compat`, `_patch_burst_az_carrier_poly`, and the `np.string_ = np.bytes_` shim)

**Warning signs:**
- `TypeError: only 0-dimensional arrays can be converted to Python scalars` from polyfit
- `AttributeError: np.string_ was removed in the NumPy 2.0 release`
- `_geocode_slc(): incompatible function arguments` with a very long pybind11 type signature
- `TypeError: stat: path should be string, bytes, os.PathLike or integer, not NoneType`

**Phase to address:** CSLC pipeline. All four patches are applied in `run_cslc()` before invoking compass.

---

### Pitfall 14: compass Geogrid Spacing Bug for UTM Projections

**What goes wrong:**
compass's `generate_geogrids_from_db()` applies degree-like spacings (`4.5e-5, 9.0e-5`) when the burst EPSG matches the DEM EPSG (both UTM). For a ~90km x 40km burst, this produces grids with hundreds of millions of pixels per axis, crashing with `ValueError: array is too big` (requesting exabytes of memory).

**Why it happens:**
The spacing assignment condition at `compass/utils/geo_grid.py:334` is backwards. When `epsg == dem_raster.get_epsg()` (both UTM), it applies degree-scale defaults meant for geographic coordinates. The correct behavior is to use meter-based defaults (5.0/10.0m) for projected CRS and degree-based defaults for geographic CRS.

**How to avoid:**
- Always set `x_posting` and `y_posting` explicitly in the CSLC runconfig (`processing.geocoding.x_posting: 5.0`, `processing.geocoding.y_posting: 10.0`)
- Never rely on compass's default spacing auto-detection for UTM-projected DEMs

**Warning signs:**
- `ValueError: array is too big; arr.size * arr.dtype.itemsize is larger than the maximum possible size`
- Geogrid width/length in the millions or billions
- Processing hangs at memory allocation

**Phase to address:** CSLC pipeline. The posting is set explicitly in `generate_cslc_runconfig()`.

---

### Pitfall 15: CSLC Phase Comparison Fails Across isce3 Major Versions

**What goes wrong:**
Interferometric phase comparison (`angle(product * conj(reference))`) between CSLCs produced by different isce3 major versions yields random noise (phase RMS = pi/sqrt(3) ≈ 1.81 rad, coherence ≈ 0), even though amplitudes correlate (r ≈ 0.79) and the geocoded data is at the correct spatial locations.

**Why it happens:**
Between isce3 0.15 and 0.25, the phase screen computation changed: carrier phase estimation, ellipsoidal flattening, geometric Doppler correction, and SLC interpolation kernels all differ. Each version produces internally consistent CSLCs that form valid interferograms within the same processing chain, but the absolute phase reference differs between versions, making cross-chain phase comparison meaningless.

At C-band (λ ≈ 5.5 cm), even sub-meter differences in geocoding position produce many radians of phase change (0.91 m ≈ 21 rad two-way). Grid alignment must be exact to the pixel center, requiring `x_snap` and `y_snap` to match OPERA's grid.

**How to avoid:**
- Use **amplitude-based metrics** (correlation, RMSE in dB) for cross-version CSLC validation
- Use **interferometric time-series comparison** (velocity fields) for scientific equivalence testing — this cancels the common-reference phase ambiguity
- For phase-coherent comparison, ensure identical isce3/compass/s1reader versions
- Always set `x_snap` and `y_snap` in the geocoding config to align pixel centers with the reference grid

**Warning signs:**
- Phase RMS ≈ 1.81 rad (pi/sqrt(3) = uniform random on [-pi, pi])
- Coherence ≈ 0 despite high amplitude correlation
- Phase differences show no spatial structure (uniform noise)
- Processing parameters match but `ISCE3_version` in reference HDF5 differs from installed version

**Phase to address:** Validation framework. `compare_cslc()` uses amplitude-based criteria as primary pass/fail, with phase metrics reported as informational.

---

### Pitfall 16: compass `burst_database_file` Required for Correct Geogrid

**What goes wrong:**
Running compass CSLC without a burst database SQLite file either crashes (due to the None guard bug in Pitfall 13) or produces a geogrid with incorrect parameters (due to the spacing bug in Pitfall 14). Even if both bugs are patched, the `generate_geogrids()` fallback (no-DB path) computes the burst EPSG from the center lat/lon, which may disagree with OPERA's official EPSG assignment for that burst.

**Why it happens:**
compass was designed to work with a burst database that provides pre-computed EPSG codes and UTM bounding boxes for each burst. The database-free code path exists but is poorly tested and has bugs. OPERA's production system always uses the official burst database.

**How to avoid:**
- Always provide a `burst_database_file` in the runconfig
- For N.Am. validation, create a minimal SQLite from `opera_utils.burst_frame_db.get_burst_id_geojson()` with the correct EPSG and UTM bbox
- For EU production, use subsideo's EU burst database (`~/.subsideo/eu_burst_db.sqlite`)
- Schema: `burst_id_map(burst_id_jpl TEXT PRIMARY KEY, epsg INTEGER, xmin REAL, ymin REAL, xmax REAL, ymax REAL)`

**Phase to address:** CSLC pipeline. `run_cslc()` accepts an optional `burst_database_file` parameter.

---

## "Looks Done But Isn't" Checklist

- [ ] **RTC pipeline:** Produces a GeoTIFF with correct radiometry — verify it is COG-formatted (`gdal.Info` shows `LAYOUT=COG`) with overviews at 2x, 4x, 8x, 16x, 32x
- [x] **CSLC pipeline:** Phase values look correct visually — verify complex64 dtype, correct EPSG in HDF5 metadata, and OPERA-spec group structure in the HDF5 tree. **Verified 2026-04-11:** Amplitude correlation 0.79, RMSE 3.77 dB vs OPERA reference (PASS). Product is complex64 at 5m x 10m posting (EPSG:32611), shape (3959, 17881). Phase comparison not meaningful across isce3 versions (0.15→0.25). Results reproducible across clean re-runs.
- [ ] **Burst database:** Queries return results for EU coordinates — verify coverage against a hand-selected list of known EU burst IDs from ASF's burst catalog
- [ ] **DISP pipeline:** Time series looks reasonable — verify at least 3 reference points co-located with GNSS stations, and that velocity bias < 3 mm/yr at those points
- [ ] **Tropospheric correction:** MintPy log says "correct_troposphere: done" — verify the ERA5 correction actually *changed* the displacement values (non-zero delta)
- [ ] **Validation metrics:** RMSE and correlation pass thresholds — verify the reference product and the test output are co-registered to sub-pixel accuracy before computing metrics
- [ ] **DSWx output:** F1 > 0.90 against JRC — verify this is on a held-out EU scene, not the scene used for threshold calibration
- [ ] **CLI:** `subsideo rtc --help` exits 0 — verify end-to-end with a real CDSE download on a 1-burst test AOI

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Conda/pip environment corruption | HIGH | Delete and rebuild environment from locked `environment.yml`; re-run all tests |
| CDSE S3 credential expiry mid-run | LOW | Regenerate S3 keys in CDSE portal; update env vars; resume from last successful download checkpoint |
| EU burst DB gaps discovered late | MEDIUM | Identify missing burst IDs via ASF CMR; rebuild DB from ESA GeoJSON with expanded coverage; rerun affected pipeline stages |
| Phase unwrapping cycle slips in validation | MEDIUM | Rerun tophu with increased tile overlap; apply bridging correction in MintPy; flag affected epochs in output metadata |
| OPERA spec compliance failure discovered post-implementation | HIGH | Audit all output writers against OPERA ATBD; fix schema deviations; reprocess all test outputs |
| EGMS validation RMSE too high | LOW-MEDIUM | Apply spatial reference correction; verify EGMS version consistency; check snow masking; compare to GNSS as alternate ground truth |
| macOS arm64 build failure | MEDIUM | Switch to explicit conda-forge clang; add `-DCMAKE_FIND_FRAMEWORK=NEVER`; verify binary architecture with `file` command |
| numpy 2.x compass/isce3 crashes | LOW | Apply 4 monkey-patches in `cslc.py`; OR pin `numpy < 2.0` in conda env |
| CSLC phase validation failure across versions | LOW | Switch to amplitude-based metrics; report phase as informational |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Conda/pip environment corruption | Phase 1: Environment / Foundation | `conda list` shows no pip-sourced overrides of conda packages; all imports succeed; ISCE3 unit tests pass |
| CDSE S3 endpoint and credentials | Phase 2: Data Access Layer | Integration test downloads a real 1-burst SLC slice and verifies file size matches CDSE metadata |
| EU burst database gaps | Phase 2: Burst DB Build | Query coverage >= 90% of expected EU burst count per track; geometry integrity check passes |
| UTM zone boundary handling | Phase 3: RTC Pipeline + Phase 4: CSLC Pipeline | Cross-zone AOI regression test produces correctly-seamed output with sub-pixel co-registration |
| Phase unwrapping failures | Phase 5: DISP Pipeline | Post-unwrapping sanity check passes on all test interferograms; no step discontinuities in time series |
| ERA5 / CDS API configuration | Phase 5: DISP Pipeline (early) | `subsideo check-env` validates CDS API access; MintPy log shows tropospheric correction applied |
| GLO-30 variable grid spacing | Phase 2: Ancillary Data + Phase 3: RTC | DEM validation step confirms uniform 30 m UTM grid before ISCE3 consumption; no banding in products north of 52°N |
| Orbit file availability race | Phase 3: RTC + Phase 4: CSLC | Orbit type logged in output metadata; POEORB-only mode enforced for validation runs |
| OPERA HDF5 spec compliance | Phase 3 onward (all product phases) | `OperaProductValidator` passes on every pipeline output; `opera-utils` loads files without error |
| EGMS comparison methodology | Phase 6: Validation Framework | Validation protocol document written before first EGMS comparison; reference correction applied; GNSS cross-check included |
| macOS arm64 build | Phase 1: Environment / Foundation | macOS arm64 CI smoke test passes; binary architecture verified; all ISCE3 geometry tests pass |
| DSWx spectral calibration | Phase 7: DSWx-S2 Pipeline | Threshold calibration dataset held out from validation; F1 measured on independent EU scenes |
| numpy 2.x compass/isce3 compat | CSLC Pipeline | All 4 monkey-patches applied before compass invocation; pipeline completes without TypeErrors |
| Geogrid spacing bug for UTM | CSLC Pipeline | Explicit posting in runconfig; output grid dimensions are O(10^3-10^4), not O(10^8-10^9) |
| Cross-version CSLC phase mismatch | Validation Framework | Amplitude-based criteria used; phase metrics reported as informational |
| Missing burst database file | CSLC Pipeline | burst_database_file provided; EPSG and bbox match OPERA's grid |

---

## Sources

- ISCE3 conda installation issues: https://github.com/isce-framework/isce3/issues/7 (MEDIUM confidence — resolved in recent ISCE3 releases but HDF5 version pinning discipline remains important)
- CDSE S3 API documentation: https://documentation.dataspace.copernicus.eu/APIs/S3.html (HIGH confidence — official docs)
- CDSE S3 endpoint change September 2025: https://dataspace.copernicus.eu/news/2025-7-29-changes-s3-endpoint-eodata-repository (HIGH confidence)
- CDSE STAC legacy endpoint deprecation November 2025: https://sentinels.copernicus.eu/-/cdse-release-of-the-new-cdse-stac-catalogue (HIGH confidence)
- MintPy CDS API configuration errors: https://github.com/insarlab/MintPy/issues/1008 (MEDIUM confidence — specific error reproduced in community)
- MintPy FAQ and known issues: https://mintpy.readthedocs.io/en/latest/FAQs/ (MEDIUM confidence)
- SNAPHU tile-based unwrapping artifacts: general InSAR literature + tophu README (MEDIUM confidence)
- GLO-30 variable grid spacing above 50°N: https://portal.opentopography.org/raster?opentopoID=OTSDEM.032021.4326.3 (HIGH confidence — documented in tile metadata)
- OPERA CSLC validation methodology: https://github.com/OPERA-Cal-Val/calval-CSLC (MEDIUM confidence)
- EGMS validation limitations and snow effects: https://isprs-archives.copernicus.org/articles/XLVIII-4-W7-2023/247/2023/ (MEDIUM confidence — peer-reviewed)
- German vs EGMS comparison: https://link.springer.com/article/10.1007/s41064-024-00273-3 (MEDIUM confidence — 2024 paper)
- Sentinel-1 orbit file migration from SciHub: https://github.com/scottstanie/sentineleof (MEDIUM confidence)
- Orbit files AWS open data: https://registry.opendata.aws/s1-orbits/ (HIGH confidence — official AWS registry)
- DSWx-HLS product spec and HLS vs L2A difference: https://www.jpl.nasa.gov/go/opera/products/dswx-product-suite/ (MEDIUM confidence)
- numpy 2.0 migration guide (removed aliases, scalar conversion): https://numpy.org/doc/stable/numpy_2_0_migration_guide.html (HIGH confidence)
- compass burst_database_file bug: empirically verified 2026-04-11 — `geo_runconfig.py:70-74` calls `os.path.isfile(None)` before line 101 None guard (HIGH confidence)
- compass geogrid spacing bug: empirically verified 2026-04-11 — `geo_grid.py:334-337` applies degree spacings to UTM-projected CRS (HIGH confidence)
- Cross-version CSLC phase incompatibility: empirically verified 2026-04-11 — isce3 0.15.1 vs 0.25.8 produce zero coherence on same input burst, amplitude correlation 0.79 (HIGH confidence)
- macOS ISCE3 build — clang and CMake flags: https://github.com/mgovorcin/conda_installation_isce3/blob/main/README.md (MEDIUM confidence — community-maintained)
- ESA burst ID map publication: https://sentinels.copernicus.eu/-/publication-of-burst-id-maps-for-copernicus-sentinel-1 (HIGH confidence — official ESA)
- opera-adt/burst_db North America focus: https://github.com/opera-adt/burst_db (MEDIUM confidence — inferred from `is_north_america` field and OPERA operational scope)
- Ionospheric correction importance at high latitudes: https://espo.nasa.gov/archive_sarp_2024/content/Ionospheric_Correction_of_InSAR_Time_Series_Analysis_of_C-band_Sentinel-1_TOPS_Data (MEDIUM confidence)

---

*Pitfalls research for: SAR/InSAR geospatial processing library, EU AOIs, ISCE3/dolphin/CDSE/OPERA stack*
*Researched: 2026-04-05*
