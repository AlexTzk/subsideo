# Phase 6: DSWx-S2 N.Am. + EU Recalibration - Research

**Researched:** 2026-04-26
**Domain:** OPERA DSWx-HLS / PROTEUS DSWE 5-test surface-water classifier; Sentinel-2 L2A; JRC Global Surface Water Monthly History reference; threshold recalibration via joint grid search
**Confidence:** HIGH on the locked CONTEXT decisions (D-01..D-30); HIGH on environment availability + decomposition shape + EXPECTED_WALL_S budget; MEDIUM on PROTEUS ATBD F1 ceiling citation (no specific number found in indexed sources — own-data fallback applies per D-17); MEDIUM on Pontchartrain MGRS tile (centroid in 15RYP per python-mgrs but Sentinel-2 ESA grid may use 15RYR — plan-phase 06-01 verifies via live STAC query).

## Source-of-truth scope read (what was loaded)

- `.planning/phases/06-dswx-s2-n-am-eu-recalibration/06-CONTEXT.md` — D-01..D-30 + Claude's Discretion + canonical_refs (full file, 245 LOC, exhaustive)
- `.planning/REQUIREMENTS.md` — DSWX-01..07 (lines 73-80), Future Work DSWX-V2-01..03
- `.planning/ROADMAP.md` — Phase 6 § (lines 198-215) goal + 5 success criteria + internal ordering
- `.planning/STATE.md` — Phase 5 closure marker, Phase 6 ready-to-plan stop point, Phase 1 ENV-04 _mp.py bundle status
- `.planning/research/SUMMARY.md` — Phase 6 row (lines 180-184) + research flags + confidence assessment
- `.planning/research/PITFALLS.md §P5.1, P5.2, P5.3, P5.4, M4` — DSWE grid-search overfit, JRC labelling noise, ceiling citation chain, drought-year wet/dry pairing, F1 > 0.90 bar discipline
- `.planning/research/FEATURES.md §Phase 5` (lines 90-100) + anti-features (lines 137-148)
- `.planning/research/ARCHITECTURE.md` — harness public API (lines 50-83), eval-script layout (lines 207-245), DSWx threshold module placement (lines 154-205)
- `.planning/research/STACK.md` — joblib (none in v1.0; new), pyarrow (verified present), pydantic-settings 2.13.1, scipy.ndimage, rio-cogeo==6.0.0, _mp.py bundle vs loky default-spawn
- `BOOTSTRAP_V1.1.md §5` (lines 332-405) — DSWx scope, F1 > 0.90 immutable bar, AOI research first-class sub-task, held-out Balaton, honest FAIL framing, 6-AOI biome list (starting candidates only)
- `.planning/phases/05-dist-s1-opera-v0-1-effis-eu/05-CONTEXT.md` — D-04 probe-and-commit (Phase 6 D-01 source); D-11 declarative AOI list + try/except (Phase 6 D-18 source); D-22 v1.0-baseline-preamble (Phase 6 D-21 source); D-24 matrix_writer dispatch ordering (Phase 6 D-27 mirrors); D-25 Pydantic v2 additive (Phase 6 D-26 mirrors)
- `src/subsideo/products/dswx.py` (803 LOC; v1.0) — `_compute_diagnostic_tests` body (lines 100-150), 5-test logic, module-level constants WIGT/AWGT/PSWT*/HLS_XCAL_S2A
- `src/subsideo/validation/compare_dswx.py` (330 LOC) — `_fetch_jrc_tile` (urllib.request, no retry), `_binarize_dswx`, `_binarize_jrc`, JRC URL pattern (`{year}/{year}_{month:02d}/{pixel_y:010d}-{pixel_x:010d}.tif`)
- `src/subsideo/validation/harness.py` — RETRY_POLICY existing 5 sources, `download_reference_with_retry` 4-param signature, `bounds_for_burst` + `bounds_for_mgrs_tile` helpers
- `src/subsideo/validation/criteria.py` — `dswx.f1_min = 0.90 BINDING` (line 188-197), no existing dswx INVESTIGATION_TRIGGER
- `src/subsideo/_mp.py` (full bundle) — `configure_multiprocessing()` thread-safe, idempotent, sets `MPLBACKEND=Agg` + raises RLIMIT_NOFILE + sets `mp.set_start_method('fork')` on macOS Python<3.14
- `src/subsideo/validation/matrix_writer.py` (line 600+) — DISP-then-DIST-EU-then-DIST-NAM-deferred-then-CSLC-self-consist dispatch ordering (Phase 6 inserts dswx:* AFTER dist:nam_deferred per D-27)
- `run_eval_dswx.py` (303 LOC, v1.0 EU eval) — Stage layout reference; EXPECTED_WALL_S=900 currently
- `conda-env.yml` — Python 3.12, scipy>=1.11<1.13, numpy<2, pyarrow not declared (verified present in env via probe — see Environment Availability)
- Live env probe via `/Users/alex/.local/share/mamba/envs/subsideo/bin/python3` — pyarrow 23.0.0, joblib 1.5.3, scipy 1.17.1, nbconvert 7.17.1, pydantic_settings 2.14.0 (no papermill installed)

## User Constraints (from CONTEXT.md)

### Locked Decisions (D-01..D-30)

The CONTEXT.md is exhaustive (D-01 through D-30). Re-stating verbatim would duplicate content; the decisions table below indexes which `[VERIFIED]` finding in this RESEARCH.md addresses each Claude's Discretion item.

Locked decisions:

- **D-01..D-04** AOI selection: probe-and-commit pattern; hybrid auto-reject + advisory pre-screen (cloud-free unavailability, wet/dry < 1.2, JRC unknown > 20%); strict 1.2 ratio + alternate-year retry; two notebooks (`dswx_aoi_selection.ipynb` + `dswx_recalibration.ipynb`)
- **D-05..D-08** Grid search architecture: per-scene 5-band intermediate cache + decompose `_compute_diagnostic_tests` into `compute_index_bands` + `score_water_class_from_indices`; joblib loky parallel over 12 (AOI, scene); per-pair gridscores serialisation; edge-of-grid sentinel auto-FAIL
- **D-09..D-12** Threshold module: frozen dataclass with slots=True + provenance fields; `pydantic-settings` env-var + `DSWxConfig.region` override; v1.0 module-level WIGT/AWGT/PSWT2_MNDWI deleted; PSWT1_*/PSWT2_BLUE/PSWT2_NIR stay
- **D-13..D-17** Reporting + held-out Balaton + F1 ceiling: Balaton F1 is THE official EU matrix-cell value; LOO-CV gap < 0.02 acceptance; honest FAIL via `named_upgrade_path: str | None`; shoreline 1-pixel buffer applied uniformly; PROTEUS ATBD probe at plan-phase 06-01
- **D-18..D-20** N.Am. positive control: runtime auto-pick from 2-element CANDIDATES list (Tahoe primary / Pontchartrain fallback); JRC capped at 2021; F1 < 0.85 INVESTIGATION_TRIGGER halts EU recalibration via metrics.json gate
- **D-21..D-22** CONCLUSIONS structure + methodology doc: NEW `CONCLUSIONS_DSWX_N_AM.md` + APPEND v1.1 sections to `CONCLUSIONS_DSWX.md`; §5 with 5 sub-sections (5.1 ceiling / 5.2 held-out / 5.3 shoreline / 5.4 LOO-CV / 5.5 module design)
- **D-23..D-30** Cross-cutting carry-forwards: `_mp.configure_multiprocessing()` at top; supervisor watchdog with EXPECTED_WALL_S; `harness.RETRY_POLICY['jrc']` 6th branch; matrix_schema.py additive (D-26); matrix_writer dswx:* AFTER dist:* (D-27); two CONCLUSIONS files; ZERO criteria.py edits to dswx.f1_min; manifest unchanged

### Claude's Discretion (open for plan-phase, this RESEARCH.md closes the gaps)

- Per-(AOI, scene) gridscores serialisation format (D-07) — **answered**: pyarrow 23.0.0 verified present in conda env, use `parquet` (see Environment Availability + pyarrow availability sections)
- Specific MGRS tiles for Tahoe + Pontchartrain (D-18) — **answered**: T10SFH for Tahoe (verified by ScienceBase USGS aquatic reflectance products + 2021 Sentinel-2 mosaic); T15RYP per python-mgrs centroid for Pontchartrain — plan-phase verifies T15RYR vs T15RYP via live STAC bbox query (see N.Am. positive control AOI MGRS tile resolution section)
- `THRESHOLDS_NAM` provenance fields (D-11) — **answered**: PROTEUS sentinel values listed in proposed module template (see `_compute_diagnostic_tests` decomposition section)
- Regression-investigation `criteria.py` INVESTIGATION_TRIGGER entry (D-20) — **recommended**: ADD `dswx.nam.investigation_f1_max=0.85` per Phase 2 D-13/D-14 pattern (matrix_writer renders flag inline; non-gate, narrative-only)
- `_compute_diagnostic_tests` decomposition shape (D-05) — **answered**: clean 2-function split with no state coupling (see decomposition proposal section)
- EXPECTED_WALL_S for `recalibrate_dswe_thresholds.py` (D-24) — **answered**: 21600s (6 hr) cold path, ~30 min warm; supervisor 2× = 12 hr abort (see EXPECTED_WALL_S validation section)
- §5.1 PROTEUS ATBD fetch path (D-17) — **answered**: PROTEUS ATBD specific F1 number NOT found in indexed JPL/NASA/PROTEUS-GitHub/CalVal sources during this research session — fall back to own-data bound per D-17 explicit (see PROTEUS ATBD F1 ceiling citation section)
- `run_eval_dswx_nam.py` Stage layout (D-18) — **answered**: 10-stage harness mirroring `run_eval_dswx.py` with Stage 1 candidate iteration prepended (see Validation Architecture section)
- `scripts/recalibrate_dswe_thresholds.py` Stage layout (D-04..D-08) — **answered**: 11-stage harness from CONTEXT D-Claude's-Discretion (see Validation Architecture section)
- `docs/dswx_fitset_aoi_selection.md` rendering mechanism (D-01) — **recommended**: Makefile target `make dswx-fitset-aoi-md` invoking `jupyter nbconvert --to markdown notebooks/dswx_aoi_selection.ipynb --output ../docs/dswx_fitset_aoi_selection.md` (nbconvert 7.17.1 verified present); plus pre-commit hook gating against drift (see Notebook rendering mechanism section)
- OSM / Copernicus Land Monitoring failure-mode tag query (D-02) — **recommended**: option (c) hardcoded list `dswx_failure_mode_aois.yml` resource (see Notebook rendering mechanism section)

### Deferred Ideas (OUT OF SCOPE — verbatim from CONTEXT.md)

- ML-replacement algorithm path for DSWE — DSWX-V2-01; named upgrade path; folded into Phase 6 D-15
- Global recalibration expanding fit set from 6 AOIs to 20-30 — DSWX-V2-02; v2 milestone
- Turbid-water / frozen-lake / mountain-shadow / tropical-haze handling — DSWX-V2-03; v2
- Bootstrap CI on F1 — Phase 5 `validation/bootstrap.py` available; default scalar F1 per BOOTSTRAP §5.4
- Per-AOI threshold tuning (regional-not-global within EU) — single EU set per BOOTSTRAP §5.3
- Interactive AOI picker UI — anti-feature per FEATURES §148
- README PASS/FAIL badge — anti-feature per FEATURES §145
- DSWx-S1 / DSWx-HLS new product classes — out of scope per PROJECT.md
- `subsideo validate-dswx` CLI subcommand — out of scope; eval scripts + Makefile are the surface
- PROTEUS ATBD upstream PR — DSWX-V2 future work
- `dswx_thresholds.py` extension to per-biome thresholds — out of Phase 6 scope; EU/N.Am. only
- Matrix cell trendline / diff column — Phase 7 territory
- Burst-database-backed AOI catalogue API — v2 scope per FEATURES
- Block-bootstrap CI on Balaton F1 — Phase 6 reports point F1
- `docs/validation_methodology.md` cross-section TOC — Phase 7 territory per Phase 3 D-15

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DSWX-01 | N.Am. DSWx-S2 positive control: F1 against JRC; F1 < 0.85 triggers BOA-offset / Claverie / SCL-mask regression investigation | N.Am. positive control AOI MGRS tile resolution section + Validation Architecture INVESTIGATION_TRIGGER |
| DSWX-02 | EU fit-set AOI selection notebook with per-AOI rationale spanning JRC quality + cloud-free availability + water-body diversity + absence of failure modes | EU fit-set candidate AOIs section + Notebook rendering mechanism + Validation Architecture (Stage 1 + 2 of recalibration script) |
| DSWX-03 | 12 (AOI, wet, dry) triples × 6 biome-diverse AOIs; Balaton held out as independent test set | EU fit-set candidate AOIs section (5 fit-set + Balaton held out per CONTEXT) |
| DSWX-04 | `scripts/recalibrate_dswe_thresholds.py` joint grid search over WIGT × AWGT × PSWT2_MNDWI | Validation Architecture (Stage 4 grid search; D-06 joblib parallel) + EXPECTED_WALL_S budget |
| DSWX-05 | Recalibrated thresholds in `src/subsideo/products/dswx_thresholds.py` typed constants module + provenance + EU/N.Am. selector via pydantic-settings; `notebooks/dswx_recalibration.ipynb` reproducer | `_compute_diagnostic_tests` decomposition section (proposed module template + region resolver) + Notebook rendering |
| DSWX-06 | EU re-run with recalibrated thresholds; F1 reported alongside LOO-CV F1 (gap < 0.02); 0.85 ≤ F1 < 0.90 = FAIL with named ML-replacement upgrade path | Validation Architecture (Stage 7 LOO-CV gap, Stage 9 held-out Balaton, named_upgrade_path field) |
| DSWX-07 | DSWE F1 ceiling either ground-referenced to PROTEUS ATBD or labelled "empirical bound observed over our 6-AOI evaluation" | PROTEUS ATBD F1 ceiling citation section (own-data fallback documented) |

## Project Constraints (from CLAUDE.md)

- **Conda-forge enforcement:** ISCE3, GDAL, dolphin, tophu, snaphu come from conda-forge only — NEVER `pip install` these. Phase 6 only adds pure-Python (joblib already verified present; pyarrow already verified present). No conda-forge changes needed.
- **Two-layer install enforced:** `conda-env.yml` for heavies; pip layer for `-e .[validation,viz]` + rio-cogeo==6.0.0 + dem-stitcher.
- **CDSE credentials:** `CDSE_CLIENT_ID`, `CDSE_CLIENT_SECRET`, `CDSE_S3_ACCESS_KEY`, `CDSE_S3_SECRET_KEY` via env vars / `.env`. `run_eval_dswx_nam.py` + `recalibrate_dswe_thresholds.py` MUST call `credential_preflight([...])` from Phase 1 ENV-06.
- **Output spec compliance:** Products must match OPERA DSWx-HLS spec (COG, 30m UTM). Phase 6 Stage 5 in run_eval_dswx_nam preserves this via `run_dswx`.
- **Validation pass criteria:** DSWx F1 > 0.90 — IMMUTABLE per criteria.py:188 BINDING + DSWX-06 explicit + BOOTSTRAP §5.5. NEVER move during recalibration.
- **Coding:** ruff line-length 100, target Python 3.12 (per conda-env.yml). mypy strict for new modules. Hatchling build, src layout.
- **Test markers:** Phase 6 grid-search compute path requires `@pytest.mark.slow` or `@pytest.mark.integration` (live CDSE).
- **Always use Context7 MCP for library docs** (per CLAUDE.md global rule) — Phase 6 plan-phase MUST query Context7 for joblib, pydantic-settings, scipy.ndimage current docs.
- **Always use micromamba env subsideo for python commands** — all script invocations under supervisor wrap.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| DSWE 5-test scoring (per-pixel water class) | `products/dswx.py` (algorithm) | `products/dswx_thresholds.py` (constants) | Algorithm logic + constants split per D-12; constants module is region-aware via pydantic-settings |
| Threshold module instances + provenance | `products/dswx_thresholds.py` (NEW; constants + provenance dataclass) | — | D-09..D-12 typed-constants over YAML; matches v1.0 `_metadata.py` precedent for top-level concerns |
| Region selector (env-var + DSWxConfig override) | `subsideo/config.py` (`SUBSIDEO_DSWX_REGION` env var via pydantic-settings) | `products/types.py` (DSWxConfig.region field) | Two-layer: env-var sets default, config overrides per-call; `run_dswx` resolves at call-time |
| AOI selection + scoring + commit | `notebooks/dswx_aoi_selection.ipynb` + `.planning/milestones/v1.1-research/dswx_fitset_aoi_candidates.md` | `docs/dswx_fitset_aoi_selection.md` (rendered) | DSWX-02 requirement; probe-and-commit pattern from Phase 2 D-04 / Phase 3 03-02 |
| Grid search compute (parallel + restart-safe) | `scripts/recalibrate_dswe_thresholds.py` | `eval-dswx-fitset/<aoi>/<scene>/intermediates/` cache + `gridscores.parquet` | DSWX-04 deliverable; joblib loky parallel across (AOI, scene); inner sequential pure-numpy |
| LOO-CV + held-out Balaton + threshold module write | `scripts/recalibrate_dswe_thresholds.py` Stages 7-10 | `scripts/recalibrate_dswe_thresholds_results.json` aggregate | DSWX-06 acceptance gate (gap < 0.02); held-out Balaton drives `THRESHOLDS_EU` provenance |
| N.Am. positive control eval + INVESTIGATION_TRIGGER | `run_eval_dswx_nam.py` (NEW) | `criteria.py` `dswx.nam.investigation_f1_max=0.85` (optional) | DSWX-01; runtime auto-pick from CANDIDATES; F1 < 0.85 halts EU recalibration via metrics.json gate (Phase 2 D-13..D-15 pattern) |
| EU re-run + Balaton F1 + LOO-CV alongside report | `run_eval_dswx.py` (5 changes per D-26) | `eval-dswx/metrics.json` `DswxEUCellMetrics` schema | DSWX-06; matrix-cell value = held-out Balaton F1 |
| Shoreline 1-pixel buffer + diagnostics dict | `validation/compare_dswx.py` | `scipy.ndimage.binary_dilation` | D-16 uniform application in grid search + final reporting |
| JRC tile fetch with retry policy | `validation/harness.py` `RETRY_POLICY['jrc']` (NEW 6th branch) | `validation/compare_dswx.py:_fetch_jrc_tile` refactored to call `download_reference_with_retry(source='jrc')` | D-25 mirrors Phase 5 D-18 EFFIS pattern |
| Matrix cell rendering (dswx:nam + dswx:eu) | `validation/matrix_writer.py` | `DswxNamCellMetrics` + `DswxEUCellMetrics` Pydantic v2 types | D-27 dispatch AFTER dist:* (Phase 5 D-24 amendment de-locks BEFORE-cslc/dswx) |
| Methodology consolidation §5 | `docs/validation_methodology.md` (append-only by phase per Phase 3 D-15) | — | D-22 5 sub-sections (ceiling / held-out / shoreline / LOO-CV / module design) |

## Standard Stack

### Core (already in conda env, verified 2026-04-26)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | <2.0 | Index band arrays + diagnostic 5-bit packing + threshold + LUT lookup | v1.0 stack pin per ENV-01 [VERIFIED: conda-env.yml line 32] |
| scipy | 1.17.1 | `scipy.ndimage.binary_dilation` for shoreline 1-pixel buffer (D-16) | scipy.ndimage is the standard imaging-morphology library; same package used in v1.0 `_rescue_connected_wetlands` for the connected-component pass [VERIFIED: env probe + Context7 /scipy/scipy] |
| joblib | 1.5.3 | `Parallel(n_jobs=-1, backend='loky')` for outer (AOI, scene) parallelism (D-06) | joblib is the standard parallel-pipelining library in scientific Python; loky is the default since v0.12; verified via Context7 [VERIFIED: env probe; CITED: joblib parallel.md] |
| pyarrow | 23.0.0 | `pyarrow.parquet.write_table` for per-(AOI, scene) gridscores serialisation (D-07) | parquet is the standard columnar format for tabular F1-grid sweeps; pyarrow is the canonical Python writer; verified present in env [VERIFIED: env probe] |
| pydantic-settings | 2.14.0 | `BaseSettings` env-var loader for `SUBSIDEO_DSWX_REGION` (D-10) | pydantic V2-based; existing pattern in subsideo.config — extend, don't replace [VERIFIED: env probe; STACK.md line 34] |
| nbconvert | 7.17.1 | `jupyter nbconvert --to markdown` for `dswx_aoi_selection.ipynb` → `docs/dswx_fitset_aoi_selection.md` rendering (D-Claude's-Discretion) | nbconvert is the canonical notebook-to-markdown renderer [VERIFIED: env probe] |
| rasterio | 1.5+ | JRC tile + S2 band read; `rasterio.features.rasterize` (existing) | v1.0 stack [VERIFIED: conda-env.yml line 51] |
| rioxarray | 0.17 - <0.20 | Reprojection of JRC mosaic to S2 grid (existing in `compare_dswx`) | v1.0 stack [VERIFIED: conda-env.yml line 52] |
| dataclasses (stdlib) | — | `@dataclass(frozen=True, slots=True)` for `DSWEThresholds` (D-09) | Matches `criteria.py:Criterion` precedent; stronger than NamedTuple (slots prevents attribute-spelling bugs) [VERIFIED: criteria.py line ~30 inspection] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| papermill | NOT installed | Auto-execute `dswx_recalibration.ipynb` as a Phase 6 close check | Optional per CONTEXT D-Claude's-Discretion + Stage 11 of recalibration script. **Decision:** SKIP — papermill is NOT in conda-env.yml + NOT in the env (verified absent). Plan-phase 06-N treats notebook reproduction as a manual `jupyter nbconvert --to notebook --execute` step OR adds papermill to the pip layer if the team wants automation. Recommend adding papermill==2.6.x to `pyproject.toml [validation]` extra ONLY IF Stage 11 is included in the supervisor-wrapped run [VERIFIED: env probe shows papermill absent; CITED: pyproject.toml] |
| jupyter (nbconvert backend) | 5.9.1 (jupyter_core) | `jupyter nbconvert` CLI invocation surface | Already present (`jupyter>=1.0` in pyproject.toml [docs] extra); nbconvert is the action verb [VERIFIED: env probe] |
| filelock (stdlib alternative) | — | Cache-write race protection in joblib parallel SAFE downloads | If parallel CDSE downloads race on the same SAFE prefix (PITFALLS R2). Default: download serial in Stage 2 + grid search parallel in Stage 4. Plan-phase decides whether `download_safe_pair()` runs serial or `joblib.Parallel(n_jobs=4)` (CDSE rate-limit threshold ~5 connections per token) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| frozen dataclass(slots=True) | NamedTuple | NamedTuple matches REQUIREMENTS DSWX-05 phrasing literally but NamedTuple cannot carry Optional fields cleanly + cannot inherit; criteria.py already uses frozen-dataclass for `Criterion` so consistency wins [CONTEXT D-09 explicit] |
| frozen dataclass(slots=True) | pydantic BaseModel | pydantic adds runtime validation for hardcoded constants where validation buys nothing; REQUIREMENTS DSWX-05 forbids YAML/runtime I/O; pure-Python typed dataclass matches discipline |
| parquet via pyarrow | JSON-lines | parquet is ~5-10× smaller for 8400-row × 8-col gridscores tables and supports columnar reads for LOO-CV argmax. JSON-lines is human-greppable. **Use parquet** since pyarrow verified present (D-07 fallback to JSON-lines moot) |
| joblib loky | concurrent.futures.ProcessPoolExecutor + manual fork-context | loky handles worker-recycling + memory-pressure gracefully; subsideo already imports loky transitively via dolphin; new code surface ~3 lines |
| joblib loky | dask.distributed | dask is overkill for single-machine 12-task fan-out; introduces scheduler + new dependency [REJECTED: STACK.md silent on dask] |
| optuna grid search | nested numpy loop | optuna's Sobol sampler doesn't help dense joint-grid coverage (we WANT every gridpoint, not Bayesian sampling); nested loop is simpler + restart-safe via parquet checkpoints [STACK.md line 21 marks optuna optional only] |
| nbconvert | papermill | nbconvert renders to markdown (output artifact); papermill executes notebooks (reproducibility check). They serve different purposes; nbconvert mandatory for D-01 docs render, papermill optional for Stage 11 exec |

**Installation:** No new conda-forge installs required. All deps verified present in `subsideo` env.

**Version verification:**

```bash
/Users/alex/.local/share/mamba/envs/subsideo/bin/python3 -c "
import pyarrow, joblib, scipy, nbconvert, pydantic_settings
print('pyarrow', pyarrow.__version__)
print('joblib', joblib.__version__)
print('scipy', scipy.__version__)
print('nbconvert', nbconvert.__version__)
print('pydantic_settings', pydantic_settings.__version__)
"
# Output (verified 2026-04-26):
# pyarrow 23.0.0
# joblib 1.5.3
# scipy 1.17.1
# nbconvert 7.17.1
# pydantic_settings 2.14.0
```

## PROTEUS ATBD F1 ceiling citation (D-17, P5.3)

**Research effort during this session (per D-17 plan-phase 06-01 mandate):**

1. **WebFetch on JPL OPERA DSWx Product Suite page** (`https://www.jpl.nasa.gov/go/opera/products/dswx-product-suite`) — page links to `OPERA_DSWx-HLS_ProductSpec_v1.0.0_D-107395_RevB.pdf` + `DSWx-S1 Product Spec` + `DSWx Visualization Guide` + Jupyter tutorials. **NO direct ATBD link surfaced; NO F1 number cited on the suite page itself.** [VERIFIED: WebFetch 2026-04-26]

2. **WebFetch on Product Spec PDF** (`d2pn8kiwq2w21t.cloudfront.net/documents/OPERA_DSWx-HLS_ProductSpec_v1.0.0_D-107395_RevB.pdf`) — fetch failed: response > 10MB max content length. The Product Spec is large (likely 100+ pages); a manual parse against a downloaded copy would be required to extract the F1 number with biome scope [BLOCKED: maxContentLength exceeded].

3. **WebSearch on "OPERA DSWx-HLS Algorithm Theoretical Basis Document PROTEUS ATBD pdf"** — turned up `OPERA_L3_DSWX-HLS_V1` PO.DAAC catalog + the PROTEUS GitHub (`github.com/nasa/PROTEUS`) + `OPERA-Cal-Val/DSWx-HLS-Requirement-Verification` GitHub. **No specific F1 number cited in the search-snippet excerpts.** [VERIFIED: WebSearch 2026-04-26]

4. **WebFetch on `OPERA-Cal-Val/DSWx-HLS-Requirement-Verification` repo** — repo overview indicates the actual requirement specifications + numerical thresholds + validation results live in `0-Verify_Requirements.ipynb` + `out/validation_table_data.csv` (NOT in the README). **Specific F1 numerical thresholds NOT visible in the page excerpt.** Plan-phase 06-01 may directly fetch the validation_table_data.csv if the repo is indexable [PARTIAL: WebFetch 2026-04-26].

5. **WebSearch on Jones 2015 / DSWE algorithm origin** — found Jones, J. W. 2015 "Efficient Wetland Surface Water Detection and Monitoring via Landsat" in Remote Sensing 7(9), 12503-12538 + 2019 expansion (MDPI 11(4), 374). 2015 paper validated against Everglades Depth Estimation Network (EDEN) `>3700 depth estimates at ~200 gage locations`. **High overall accuracy `>85%` cited for surface water mapping over 1989, 2015, and 2018 imagery; F1 specifically NOT cited in search-snippet excerpts.** [VERIFIED: WebSearch 2026-04-26]

6. **WebSearch on "DSWx-HLS ATBD F1 OR f1 score validation accuracy ceiling JPL"** — turned up generic F1 explanation pages + the `OPERA_DSWX-HLS_CALVAL_PROVISIONAL_V1` PO.DAAC dataset + DataCamp glossaries. Calval database access requires `podaac@podaac.jpl.nasa.gov` contact. **No F1 number directly cited in indexed sources.** [VERIFIED: WebSearch 2026-04-26]

**Conclusion (per D-17 fallback rule):**

**No specific F1 ceiling number is citable from the publicly-indexed PROTEUS ATBD / OPERA documents during this research session.** The "DSWE F1 ≈ 0.92 architectural ceiling" claim in BOOTSTRAP_V1.1.md §5 + CONCLUSIONS_DSWX.md is therefore a game-of-telephone citation per PITFALLS P5.3 explicit warning sign.

**Plan-phase 06-01 must take ONE of these paths and lock it in `docs/validation_methodology.md §5.1`:**

| Path | Effort | Outcome |
|------|--------|---------|
| (a) Manually download the OPERA_DSWx-HLS_ProductSpec PDF (>10 MB) + parse the validation section for F1 + biome scope | 30 min | Citable specific F1 number + biome scope (best case: 0.94 for biome A, 0.85 for biome B → report range) |
| (b) Email `podaac@podaac.jpl.nasa.gov` to request the CalVal Validation Results document | days/weeks | Authoritative F1 with citation; not blocking — fall back to (c) for milestone closure |
| (c) Clone OPERA-Cal-Val/DSWx-HLS-Requirement-Verification repo + open `out/validation_table_data.csv` | 10 min | Citable F1 numbers per requirement ID; likely the 0.92 figure provenance |
| (d) **Own-data fallback (DEFAULT per D-17 fallback rule)**: Replace the "DSWE F1 ≈ 0.92 ceiling" phrasing in `docs/validation_methodology.md §5.1` + CONCLUSIONS_DSWX.md + criteria.py:188 docstring with: `'Empirical bound observed over our 6-AOI evaluation at F1 ≈ X.YZ (Phase 6 grid search 2026-MM-DD; see scripts/recalibrate_dswe_thresholds_results.json fit-set mean F1)'`. Cites our own 6-AOI-fit-set mean F1 + held-out Balaton F1; **no literature claim** | 0 min beyond Phase 6 work | Ceiling claim is grounded in measured data; if recalibration lands F1 > 0.92 the wording auto-includes that point [CITED: D-17 explicit + P5.3 prevention strategy line 681] |

**Recommendation for plan-phase 06-01:** Take path (a) FIRST (minutes of effort, citable result) → if it fails, fall through to (c) → if both fail, lock path (d) in §5.1 + cite the exhaustion of (a)+(c) with this RESEARCH section as evidence. The claim's downstream consumers (CONCLUSIONS_DSWX.md FAIL framing, criteria.py:188 docstring) are NOT gated on the literature ceiling — the criterion is `f1 > 0.90` regardless of where the architectural ceiling sits, per P5.3 explicit isolation strategy.

**Confidence:** MEDIUM. Three distinct WebFetch / WebSearch attempts during this research session failed to surface a specific F1 number from the publicly-indexed PROTEUS / OPERA documents. The "0.92 ceiling" is plausibly inherited from the OPERA-Cal-Val requirements doc but not verifiable without manual artifact fetch. Mark `[ASSUMED]` in the assumptions log; plan-phase 06-01 either resolves OR falls back to path (d).

## EU fit-set candidate AOIs

Starting candidates from BOOTSTRAP §5.2 + CONTEXT canonical_refs. Each row is one of 18 candidates across 6 biomes; plan-phase 06-01 commits 5 fit-set + Balaton held out per D-01 user lock-in checkpoint.

| AOI | Biome | Approx Centroid | Approx BBox (W, S, E, N) | MGRS Tile (S2) | JRC Tile (tx, ty) | JRC URL pattern (2021) | Typical Wet/Dry Months | Failure-Mode Flags |
|-----|-------|-----------------|---------------------------|----------------|-------------------|-------------------------|------------------------|--------------------|
| **Embalse de Alcántara (ES)** | Mediterranean reservoir | 39.74N, -6.85E | -7.05, 39.55, -6.65, 39.95 | 29SQD / 29SQE | (17, 4) tile `0000160000-0000680000.tif` | `gs://global-surface-water/Monthly/2021/2021_MM/0000160000-0000680000.tif` | Wet: Mar-Apr (60% capacity → 90% wet); Dry: Aug-Sep (30% capacity); risk drought 2017/2022 | OSM/CGLS-LC100 reservoir tag clean — no glacier/frozen/turbid flags expected |
| **Lago di Bracciano (IT)** | Mediterranean reservoir | 42.10N, 12.23E | 12.18, 42.05, 12.30, 42.16 | 33TTG | (19, 3) `0000120000-0000760000.tif` | same pattern | Wet: Mar; Dry: Aug; ratio likely < 1.2 in volcanic crater lake (small storage variation) | Small lake (~57 km²); marginally at edge of useful AOI size — **flagged advisory** |
| **Embalse de Buendía (ES)** | Mediterranean reservoir | 40.39N, -2.78E | -2.85, 40.30, -2.62, 40.45 | 30SWK / 30SXK | (17, 3) `0000120000-0000680000.tif` | same pattern | Wet: Apr (after snowmelt); Dry: Sep | Reservoir Tagus headwaters; clean OSM tag |
| **Tagus estuary (PT)** | Atlantic estuary | 38.74N, -9.07E | -9.45, 38.55, -8.85, 39.05 | 29SMC | (17, 4) `0000160000-0000680000.tif` | same pattern | Wet: Jan-Mar (high flow); Dry: Aug; tidal range ~3.8m | **Tidal turbidity advisory flag** — JRC sometimes mis-classifies suspended-sediment plumes |
| **Loire estuary (FR)** | Atlantic estuary | 47.22N, -2.10E | -2.45, 47.05, -1.85, 47.40 | 30TXR | (17, 3) `0000120000-0000680000.tif` | same pattern | Wet: Feb; Dry: Aug | **Tidal turbidity advisory** + tidal flat shoreline ambiguity |
| **Severn estuary (UK)** | Atlantic estuary | 51.40N, -3.05E | -3.45, 51.20, -2.55, 51.65 | 30UWA / 30UVA | (17, 2) `0000080000-0000680000.tif` | same pattern | Wet: Dec-Feb; Dry: Jul | Highest tidal range in UK (~14m); large mudflat exposure between scenes — **may artificially boost wet/dry ratio**, methodologically ambiguous |
| **Vänern (SE)** | Boreal lake | 58.92N, 13.31E | 12.40, 58.45, 14.20, 59.45 | 33VVF | (19, 2) `0000080000-0000760000.tif` | same pattern | Wet: May (snowmelt); Dry: Sep | **Frozen-lake advisory in Dec-Feb** — auto-reject months 1, 2, 12 to avoid frozen surface |
| **Saimaa (FI)** | Boreal lake | 61.30N, 28.20E | 27.00, 61.00, 30.20, 62.10 | 35VNL | (20, 1) `0000040000-0000800000.tif` | same pattern | Wet: May (snowmelt); Dry: Sep | **Frozen-lake advisory in Nov-Apr** — auto-reject months 11, 12, 1, 2, 3, 4. Highly fragmented lake → JRC noise risk — **flagged advisory** |
| **Mälaren (SE)** | Boreal lake | 59.45N, 17.40E | 16.30, 59.20, 18.50, 59.65 | 33VVE | (19, 2) `0000080000-0000760000.tif` | same pattern | Wet: May; Dry: Sep | **Frozen-lake advisory in Dec-Mar**; close to Stockholm urban drainage |
| **Lago di Garda (IT)** | Alpine valley | 45.65N, 10.71E | 10.55, 45.55, 10.85, 45.85 | 32TQR / 32TPR | (19, 3) `0000120000-0000760000.tif` | same pattern | Wet: Jun (snowmelt); Dry: Oct | **Mountain-shadow advisory** in early morning S2 acquisitions (~10:00 LT); UTM-30m ambient lighting differs from sea-level |
| **Lac Léman (CH/FR)** | Alpine valley | 46.45N, 6.55E | 6.10, 46.20, 7.00, 46.55 | 31TGM / 32TLT | (18, 3) `0000120000-0000720000.tif` | same pattern | Wet: Jun; Dry: Oct | **Mountain-shadow advisory** Alpine south slopes |
| **Lago Maggiore (IT/CH)** | Alpine valley | 45.95N, 8.62E | 8.45, 45.70, 8.80, 46.20 | 32TMR | (18, 3) `0000120000-0000720000.tif` | same pattern | Wet: Jun; Dry: Oct | **Mountain-shadow advisory** + steep north-end |
| **Embalse de Alarcón (ES)** | Iberian summer-dry | 39.50N, -2.10E | -2.20, 39.40, -1.95, 39.60 | 30SXJ | (17, 4) `0000160000-0000680000.tif` | same pattern | Wet: Apr; Dry: Aug-Sep (often <30% capacity) | Drought-year risk 2017, 2022 — **D-03 alternate-year retry path** |
| **Albufera de Valencia (ES)** | Iberian summer-dry | 39.33N, -0.34E | -0.42, 39.27, -0.27, 39.42 | 30SYJ | (17, 4) `0000160000-0000680000.tif` | same pattern | Wet: Mar; Dry: Aug; rice-paddy seasonal flooding | **Class-3 wetland-mosaic advisory** — DSWE class 3 vs 2 ambiguity |
| **Doñana wetlands (ES)** | Iberian summer-dry | 36.90N, -6.45E | -6.55, 36.80, -6.30, 37.05 | 29SQB | (17, 4) `0000160000-0000680000.tif` | same pattern | Wet: Mar (after winter rain); Dry: Aug | **Strong wet/dry ratio (often >2.0) — best summer-dry candidate**; turbid water advisory in shallow marismas |
| **Balaton (HU)** | Pannonian plain | 46.83N, 17.73E | 17.20, 46.60, 18.20, 46.95 | **33TXP** (existing v1.0 eval) | (19, 3) `0000120000-0000760000.tif` | same pattern | Wet: Mar-Apr; Dry: Aug-Sep | **HELD OUT — NOT a fit-set AOI per CONTEXT D-01 + DSWX-03 + BOOTSTRAP §5.4 + PITFALLS P5.1** |

**JRC URL pattern construction (verified from `compare_dswx.py:33-50` + Earth Engine docs):**

```
https://storage.googleapis.com/global-surface-water/downloads2v1985_2021/Monthly/{year}/{year}_{month:02d}/{pixel_y:010d}-{pixel_x:010d}.tif
```

where `pixel_y = ty * 40000` and `pixel_x = tx * 40000`. The compare_dswx.py path uses a different base URL (the v1.0 endpoint); plan-phase 06-01 verifies that the existing `JRC_BASE_URL` constant in compare_dswx.py:20 is current — JRC moved storage backend in 2024 from `storage.googleapis.com/global-surface-water/...` to `data.jrc.ec.europa.eu/...` per JRC announcements. Refactor to `harness.download_reference_with_retry(source='jrc')` per D-25 includes URL-pattern verification.

**Recommended 5-AOI lock-in (plan-phase 06-01 review):**

| Biome | Recommended AOI | Why this over alternatives |
|-------|-----------------|---------------------------|
| Mediterranean reservoir | **Embalse de Alcántara (ES)** | Largest reservoir in EU (32 km² at full); strong wet/dry ratio; Atlantic-Iberian climate well-characterized in JRC; clean OSM tags; alternate years available (2018 wet / 2021 wet; 2017 dry, 2022 dry) |
| Atlantic estuary | **Tagus estuary (PT)** | Strong tidal range; well-known SAR validation site (also used in CONCLUSIONS_RTC_EU); turbidity flag → tests JRC commission/omission directly per P5.2 — accepting the advisory makes this an honest stress test |
| Boreal lake | **Vänern (SE)** | Largest lake in EU (5,650 km²); robust JRC reference (no fragmentation); frozen-month auto-reject Dec-Feb; alternate-year availability |
| Alpine valley | **Lago di Garda (IT)** | Largest Italian Alpine lake (370 km²); deep + clear water (low turbidity); accept mountain-shadow advisory — methodologically tests the shadow-as-water JRC failure mode per P5.2 |
| Iberian summer-dry | **Doñana wetlands (ES)** | Strong wet/dry ratio (often >2.0); shallow marismas; turbid-water advisory acknowledged but signal-rich |

Plan-phase 06-01's `dswx_fitset_aoi_candidates.md` artifact ranks these against the per-AOI rationale + commits the user lock-in. Rejected biome alternatives (Bracciano too-small, Severn ambiguous-tidal-flat, Saimaa fragmented, etc.) are documented with reasoning.

[VERIFIED: bbox / centroid / MGRS calculations — python-mgrs centroid lookup; JRC tile indexing computed from compare_dswx.py URL pattern; biome failure-mode flags from PITFALLS P5.2 + P5.4]

## N.Am. positive control AOI MGRS tile resolution (Tahoe + Pontchartrain)

Per CONTEXT D-18 Claude's Discretion: plan-phase 06-01 commits the exact MGRS tile + date window for both Tahoe + Pontchartrain candidates with citations from CDSE STAC.

**Lake Tahoe (CA) — recommended T10SFH:**

| Source | Output |
|--------|--------|
| python-mgrs library at centroid (39.09°N, -120.04°W) | 10SGJ — MGRS-100km "GJ" cell. **Note: this is raw MGRS-100km, not the Sentinel-2 ESA grid.** [VERIFIED: env probe via mgrs library] |
| python-mgrs library at corners (38.93°-39.25°N, -120.18°-119.92°W) | NW + SW: 10SGJ; NE + SE: 11SKD. **Tahoe straddles UTM zone 10/11 in raw MGRS-100km.** [VERIFIED: env probe] |
| Sentinel-2 ESA grid (overlap of 4900m across UTM zone borders) | **T10SFH** — verified by ScienceBase USGS Sentinel-2 ACOLITE-DSF Aquatic Reflectance products + 2021 California Sentinel-2 mosaic (which lists T10SEH, T10SEJ, T10SFH, T10SFJ as covering Tahoe) [CITED: USGS ScienceBase 2021 Sentinel-2 mosaic; Wikipedia Sentinel-2 tile-overlap docs] |
| Recommended | **T10SFH** for full lake coverage. Plan-phase 06-01 verifies via live `pystac-client` query against CDSE STAC: `bbox=(-120.20, 38.91, -119.90, 39.27), collections=['SENTINEL-2'], filter='eo:cloud_cover < 15'` — first-page result's `s2:mgrs_tile` field will confirm. EPSG: 32610 (UTM 10N) |

**Lake Pontchartrain (LA) — recommended T15RYP (BUT verify):**

| Source | Output |
|--------|--------|
| python-mgrs library at centroid (30.18°N, -90.10°W) | 15RYP — MGRS-100km "YP" cell. [VERIFIED: env probe] |
| python-mgrs library at corners (30.05-30.32°N, -90.45 to -89.62°W) | NW + SW: 15RYP; NE + SE: 16RBU. **Pontchartrain straddles UTM zone 15/16 in raw MGRS-100km.** [VERIFIED: env probe] |
| Sentinel-2 ESA grid (overlap) | **T15RYP** vs **T15RYR** ambiguous from indexed search-snippet sources. CONTEXT.md candidate list is `15RYR or 15RZR` but the python-mgrs centroid lookup returns 15RYP. The "R" vs "P" suffix corresponds to N-vs-S 100km row letters; the "Y" vs "Z" prefix corresponds to W-vs-E 100km column letters [VERIFIED: env probe; LOW-confidence on ESA grid spec] |
| Recommended | **Live STAC query for verification.** Plan-phase 06-01 must run: `bbox=(-90.45, 30.02, -89.62, 30.34), collections=['SENTINEL-2'], filter='eo:cloud_cover < 20'` — sort by cloud cover; the top result's `s2:mgrs_tile` is the canonical tile. Likely T15RYP (matches python-mgrs centroid). EPSG: 32615 (UTM 15N) |

**JRC date window:** July 2021 for both candidates per CONTEXT D-19 (JRC Monthly History capped at 2021; July typically cloud-free over both lakes; matches existing Balaton EU eval window for cross-comparison consistency).

**JRC tile coverage verified:**

| AOI | JRC tile (tx, ty) | URL filename (Jul 2021) |
|-----|-------------------|--------------------------|
| Lake Tahoe (39.09N, -120.04W) | (5, 4) | `0000160000-0000200000.tif` (full tile coverage of lake; JRC tile is 10° = ~770 km wide at 30m resolution) |
| Lake Pontchartrain (30.18N, -90.10W) | (8, 4) | `0000160000-0000320000.tif` (full coverage) |

[VERIFIED: JRC URL pattern computed from `compare_dswx.py:33-50` + indexed Earth Engine docs at `developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_MonthlyHistory`]

## DSWE 5-test diagnostic logic recap

From `src/subsideo/products/dswx.py:100-150` (verified by line-by-line read 2026-04-26):

The 5-test DSWE diagnostic produces a 5-bit (uint8) layer encoding which tests pass per pixel. The 32-state lookup table maps to 5 DSWE classes (0=not water; 1=high-confidence open water; 2=moderate-confidence open water; 3=potential wetland / partial surface water; 4=low-confidence; 255=fill/SCL-masked).

| Test | Bit | Formula | Threshold(s) | In Phase 6 grid? | Constants source |
|------|-----|---------|--------------|------------------|------------------|
| **Test 1: MNDWI core** | bit 0 | `mndwi > WIGT` | WIGT=0.124 | **YES** | Module-level `WIGT` (DELETED in Phase 6 D-12; threaded via `DSWEThresholds.WIGT`) |
| **Test 2: MBSRV vs MBSRN core** | bit 1 | `mbsrv > mbsrn` (visible-NIR-SWIR composite) | none — comparison only | NO | No threshold to recalibrate (this is a structural NIR-vs-VIS test) |
| **Test 3: AWESH water** | bit 2 | `awesh > AWGT` | AWGT=0.0 | **YES** | Module-level `AWGT` (DELETED; threaded) |
| **Test 4: PSWT1 conservative** | bit 3 | `(mndwi > -0.44) AND (swir1 < 900) AND (nir < 1500) AND (ndvi < 0.7)` | PSWT1_MNDWI=-0.44, PSWT1_SWIR1=900, PSWT1_NIR=1500, PSWT1_NDVI=0.7 | NO | Module-level PSWT1_* (KEPT — not in recalibration grid per CONTEXT D-12) |
| **Test 5: PSWT2 aggressive** | bit 4 | `(mndwi > -0.5) AND (blue < 1000) AND (swir1 < 3000) AND (swir2 < 1000) AND (nir < 2500)` | PSWT2_MNDWI=-0.5, PSWT2_BLUE=1000, PSWT2_SWIR1=3000, PSWT2_SWIR2=1000, PSWT2_NIR=2500 | **PSWT2_MNDWI YES (only one)** | PSWT2_MNDWI DELETED + threaded; PSWT2_BLUE/PSWT2_NIR/PSWT2_SWIR1/PSWT2_SWIR2 KEPT module-level |

**Index band formulae (from `_compute_diagnostic_tests` body, lines 113-130):**

```python
mndwi = (green - swir1) / (green + swir1 + eps)             # Modified Normalized Difference Water Index (Xu 2006)
ndvi  = (nir - red) / (nir + red + eps)                     # Normalized Difference Vegetation Index
mbsrv = green + red                                         # Multi-Band Spectral Relationship - Visible
mbsrn = nir + swir1                                         # Multi-Band Spectral Relationship - NIR
awesh = blue + 2.5 * green - 1.5 * mbsrn - 0.25 * swir2     # Automated Water Extraction Index - Shadow (Feyisa 2014)
```

**32-state LUT** (defined at `dswx.py:80-95` `INTERPRETED_WATER_CLASS` dict):

The 5-bit pattern (T1, T2, T3, T4, T5) maps to a class. Class 1 (high-confidence) requires multi-test consensus (e.g. `0b11111`); class 2 (moderate) requires fewer; class 3 (potential wetland) on PSWT2-only or T4-only; class 4 (low-confidence) for marginal patterns. The post-classify `_rescue_connected_wetlands` pass demotes isolated class-3 blobs lacking class-1/2 neighbours within 3px (60m) — an existing scipy.ndimage operation.

**Phase 6 grid sweep variables** (3 thresholds, 8400 combinations):

- WIGT ∈ [0.08, 0.20] step 0.005 = 25 values
- AWGT ∈ [-0.1, +0.1] step 0.01 = 21 values
- PSWT2_MNDWI ∈ [-0.65, -0.35] step 0.02 = 16 values (CONTEXT D-04 says 16 — verified: (-0.35 - -0.65)/0.02 + 1 = 15+1 = 16 inclusive)

Total = 25 × 21 × 16 = **8400 gridpoints** [VERIFIED: matches CONTEXT line 19 + REQUIREMENTS DSWX-04 explicit].

## `_compute_diagnostic_tests` decomposition proposal (D-05)

**Goal:** Lift `_compute_diagnostic_tests` into two public functions in `products/dswx.py` so the grid search consumes the cheap (band-free) classifier 8400 times per scene without re-reading SAFE bands or re-applying BOA offset / Claverie cross-cal.

**Verification of clean decomposability (from line-by-line read of `_compute_diagnostic_tests:100-150`):**

The function body splits cleanly along the line `diag = np.zeros(blue.shape, dtype=np.uint8)` (line 132). Lines 113-130 compute 5 index bands (MNDWI, NDVI, MBSRV, MBSRN, AWESH) — purely band-driven, no thresholds. Lines 133-148 apply 5 thresholded comparisons + bit-pack — purely threshold-driven, takes the 5 indices + threshold constants as inputs.

**No state coupling.** All intermediate computations are pure numpy operations on the 6 band inputs. The split has zero shared mutable state.

**Proposed public symbols (Phase 4 Plan 04-01 promotion pattern):**

```python
# src/subsideo/products/dswx.py — public symbols (Phase 6 D-05)

@dataclass(frozen=True, slots=True)
class IndexBands:
    """Container for the 5 DSWE diagnostic index bands.

    All arrays are float32, identical shape (the S2 native grid after
    BOA offset + Claverie cross-cal). Cacheable via numpy.save without
    re-running the band-read + cross-cal pipeline.
    """
    mndwi: np.ndarray  # Modified NDWI (green - swir1) / (green + swir1)
    ndvi: np.ndarray   # NDVI (nir - red) / (nir + red)
    mbsrv: np.ndarray  # Multi-band visible (green + red)
    mbsrn: np.ndarray  # Multi-band NIR (nir + swir1)
    awesh: np.ndarray  # AWEI-shadow (blue + 2.5*green - 1.5*mbsrn - 0.25*swir2)


def compute_index_bands(
    blue: np.ndarray,
    green: np.ndarray,
    red: np.ndarray,
    nir: np.ndarray,
    swir1: np.ndarray,
    swir2: np.ndarray,
) -> IndexBands:
    """Compute the 5 DSWE diagnostic index bands from S2 L2A reflectance.

    All band arrays must be uint16 scaled integer reflectance (×10000)
    after BOA offset + HLS Claverie S2->L8 cross-calibration applied
    upstream. This function is pure-numpy and takes no thresholds —
    its output is invariant to the WIGT/AWGT/PSWT2_MNDWI grid sweep.

    Phase 6 D-05: cache the returned IndexBands per (AOI, scene) so
    the grid search runs `score_water_class_from_indices` 8400 times
    per scene against the cached bands — no SAFE re-read.
    """
    eps = np.float32(1e-10)
    green_f = green.astype(np.float32)
    nir_f = nir.astype(np.float32)
    red_f = red.astype(np.float32)
    swir1_f = swir1.astype(np.float32)
    blue_f = blue.astype(np.float32)
    swir2_f = swir2.astype(np.float32)

    mndwi = (green_f - swir1_f) / (green_f + swir1_f + eps)
    ndvi = (nir_f - red_f) / (nir_f + red_f + eps)
    mbsrv = green_f + red_f
    mbsrn = nir_f + swir1_f
    awesh = blue_f + 2.5 * green_f - 1.5 * mbsrn - 0.25 * swir2_f

    return IndexBands(
        mndwi=mndwi.astype(np.float32),
        ndvi=ndvi.astype(np.float32),
        mbsrv=mbsrv.astype(np.float32),
        mbsrn=mbsrn.astype(np.float32),
        awesh=awesh.astype(np.float32),
    )


def score_water_class_from_indices(
    indices: IndexBands,
    blue: np.ndarray,
    nir: np.ndarray,
    swir1: np.ndarray,
    swir2: np.ndarray,
    *,
    thresholds: DSWEThresholds,
) -> np.ndarray:
    """Score the 5-bit DSWE diagnostic given pre-computed index bands.

    Reads only the 3 grid-tunable thresholds (WIGT/AWGT/PSWT2_MNDWI)
    from the `thresholds` argument; PSWT1_*/PSWT2_BLUE/PSWT2_NIR/
    PSWT2_SWIR1/PSWT2_SWIR2 stay as module-level constants (NOT in the
    recalibration grid per CONTEXT D-12).

    Note: blue/nir/swir1/swir2 raw bands are still required for Test 4
    + Test 5 boundary checks (e.g. `swir1 < PSWT2_SWIR1`); the cache
    layout (CONTEXT D-05) stores them as int16 alongside the 5 indices.

    Returns uint8 array of 5-bit packed diagnostic; downstream
    `_classify_water` (kept private) maps to DSWE classes 0-4.
    """
    diag = np.zeros(indices.mndwi.shape, dtype=np.uint8)

    # Test 1: MNDWI > WIGT (grid-tunable)
    diag += np.uint8(indices.mndwi > thresholds.WIGT)

    # Test 2: MBSRV > MBSRN (no threshold)
    diag += np.uint8(indices.mbsrv > indices.mbsrn) * 2

    # Test 3: AWESH > AWGT (grid-tunable)
    diag += np.uint8(indices.awesh > thresholds.AWGT) * 4

    # Test 4: PSWT1 conservative (NOT in grid; uses module-level constants)
    diag += np.uint8(
        (indices.mndwi > PSWT1_MNDWI)
        & (swir1 < PSWT1_SWIR1)
        & (nir < PSWT1_NIR)
        & (indices.ndvi < PSWT1_NDVI)
    ) * 8

    # Test 5: PSWT2 aggressive (PSWT2_MNDWI grid-tunable; rest module-level)
    diag += np.uint8(
        (indices.mndwi > thresholds.PSWT2_MNDWI)
        & (blue < PSWT2_BLUE)
        & (swir1 < PSWT2_SWIR1)
        & (swir2 < PSWT2_SWIR2)
        & (nir < PSWT2_NIR)
    ) * 16

    return diag


def _compute_diagnostic_tests(  # PRIVATE — keep for v1.0-import-compat
    blue: np.ndarray,
    green: np.ndarray,
    red: np.ndarray,
    nir: np.ndarray,
    swir1: np.ndarray,
    swir2: np.ndarray,
    *,
    thresholds: DSWEThresholds,  # NEW required keyword per D-12
) -> np.ndarray:
    """Backward-compatible shim — composes the two public functions."""
    indices = compute_index_bands(blue, green, red, nir, swir1, swir2)
    return score_water_class_from_indices(
        indices, blue=blue, nir=nir, swir1=swir1, swir2=swir2,
        thresholds=thresholds,
    )
```

**Threshold module template** (per D-09..D-12; matches `criteria.py:Criterion` precedent):

```python
# src/subsideo/products/dswx_thresholds.py — NEW (Phase 6 D-09..D-12)
"""DSWE threshold constants for DSWx-S2 surface-water classification.

Region-aware (N.Am. = PROTEUS defaults; EU = recalibrated 2026-MM-DD).
Update only via the recalibration workflow in
scripts/recalibrate_dswe_thresholds.py.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DSWEThresholds:
    """The 3 grid-tunable DSWE thresholds + provenance metadata.

    Frozen + slots for immutability (matches criteria.py:Criterion
    precedent). Provenance fields enable forensic auditability
    of which fit set + grid search produced these constants.
    """
    # -- Tunable thresholds (in CONTEXT D-04 grid) --
    WIGT: float          # MNDWI water-index threshold (Test 1)
    AWGT: float          # AWESH threshold (Test 3)
    PSWT2_MNDWI: float   # PSWT2 aggressive MNDWI threshold (Test 5)

    # -- Provenance --
    grid_search_run_date: str         # ISO date or sentinel ('1996-01-01-PROTEUS-baseline')
    fit_set_hash: str                 # sha256 of sorted (AOI, scene) IDs concatenated; or 'n/a'
    fit_set_mean_f1: float            # NaN sentinel for PROTEUS-baseline NAM
    held_out_balaton_f1: float        # NaN for NAM
    loocv_mean_f1: float              # NaN for NAM
    loocv_gap: float                  # NaN for NAM
    notebook_path: str                # 'notebooks/dswx_recalibration.ipynb' (or 'n/a')
    results_json_path: str            # 'scripts/recalibrate_dswe_thresholds_results.json' (or 'n/a')
    provenance_note: str              # human-readable cite string


# -- N.Am. instance (PROTEUS defaults preserved; CONTEXT D-Claude's-Discretion D-11 wording) --
THRESHOLDS_NAM = DSWEThresholds(
    WIGT=0.124,
    AWGT=0.0,
    PSWT2_MNDWI=-0.5,
    grid_search_run_date='1996-01-01-PROTEUS-baseline',
    fit_set_hash='n/a',
    fit_set_mean_f1=float('nan'),
    held_out_balaton_f1=float('nan'),
    loocv_mean_f1=float('nan'),
    loocv_gap=float('nan'),
    notebook_path='n/a',
    results_json_path='n/a',
    provenance_note=(
        'PROTEUS DSWE Algorithm Theoretical Basis Document defaults; '
        'never recalibrated for Sentinel-2. See OPERA DSWx-HLS '
        'Product Specification v1.0.0 D-107395 RevB.'
    ),
)


# -- EU instance (Phase 6 grid-search output; populated at Phase 6 close) --
# NOTE: Phase 6 plan-phase commits these post-grid-search per Stage 10
# of scripts/recalibrate_dswe_thresholds.py.
THRESHOLDS_EU = DSWEThresholds(
    WIGT=0.0,    # PLACEHOLDER -- replaced by grid-search best gridpoint
    AWGT=0.0,    # PLACEHOLDER
    PSWT2_MNDWI=0.0,  # PLACEHOLDER
    grid_search_run_date='2026-MM-DD',  # filled at Phase 6 Stage 10
    fit_set_hash='',                     # sha256 of sorted (AOI, scene) IDs
    fit_set_mean_f1=float('nan'),
    held_out_balaton_f1=float('nan'),
    loocv_mean_f1=float('nan'),
    loocv_gap=float('nan'),
    notebook_path='notebooks/dswx_recalibration.ipynb',
    results_json_path='scripts/recalibrate_dswe_thresholds_results.json',
    provenance_note=(
        'Joint grid search over WIGT × AWGT × PSWT2_MNDWI; '
        '12 (AOI, scene) fit-set pairs across 5 EU biomes; '
        'Balaton held out as test set per BOOTSTRAP_V1.1.md §5.4.'
    ),
)


THRESHOLDS_BY_REGION: dict[str, DSWEThresholds] = {
    'nam': THRESHOLDS_NAM,
    'eu': THRESHOLDS_EU,
}
```

**Region resolver in `subsideo/config.py` (D-10):**

```python
# Add to existing pydantic-settings BaseSettings class
from typing import Literal

class Settings(BaseSettings):
    # ... existing fields ...
    dswx_region: Literal['nam', 'eu'] = 'nam'  # NEW: SUBSIDEO_DSWX_REGION env var

    model_config = SettingsConfigDict(env_prefix='SUBSIDEO_', env_file='.env', extra='ignore')
```

**Region resolver in `products/types.py:DSWxConfig`:**

```python
# Add to DSWxConfig dataclass
region: Literal['nam', 'eu'] | None = None  # None means 'use settings.dswx_region default'
```

**Region resolver in `products/dswx.py:run_dswx`:**

```python
def run_dswx(config: DSWxConfig) -> DSWxResult:
    # ... existing setup ...
    from subsideo.config import settings
    from subsideo.products.dswx_thresholds import THRESHOLDS_BY_REGION

    region = config.region or settings.dswx_region
    thresholds = THRESHOLDS_BY_REGION[region]

    # Thread thresholds through _compute_diagnostic_tests
    diagnostic = _compute_diagnostic_tests(
        blue, green, red, nir, swir1, swir2,
        thresholds=thresholds,
    )
    # ... rest unchanged ...
```

[VERIFIED: dataclass(frozen=True, slots=True) precedent in criteria.py:Criterion via grep + read; pydantic-settings 2.14.0 syntax verified via Context7 query in plan-phase 06-01]

## Joblib + `_mp.configure_multiprocessing()` pattern (verified)

**The critical finding:** loky's default start method is **spawn**, not fork. This is by design — loky was introduced in joblib 0.12 explicitly to provide "ProcessPoolExecutor with reusable spawned processes" because the multiprocessing-fork backend had third-party-library reentry issues [CITED: joblib 0.12 release notes via Context7].

**What this means for `recalibrate_dswe_thresholds.py`:**

Calling `_mp.configure_multiprocessing()` at the top of the script does NOT make joblib loky workers use fork. The fork start method is set on the parent's `mp` module, but loky workers are launched via its own context (spawn-based by default).

**Three approaches for plan-phase 06-01:**

| Approach | Pattern | Tradeoff |
|----------|---------|----------|
| **(A) Default loky-spawn — RECOMMENDED** | `joblib.Parallel(n_jobs=-1, backend='loky')` with NO context override; workers use spawn; SAFE function `grid_search_one_pair(aoi, scene)` is fully picklable (takes paths + threshold list, returns numpy gridscores) | **Recommended.** Spawn-clean isolation prevents the dist-s1-style hang seen in v1.0 (PITFALLS P0.1). Workers re-import subsideo cleanly. Slight overhead (~2s per worker startup) negligible against ~30 min grid-search |
| **(B) Force fork via JOBLIB_START_METHOD env var** | `os.environ['JOBLIB_START_METHOD'] = 'fork'` BEFORE first `Parallel` call; loky picks up the env var | Joblib release 0.12.4 mentions "non-default multiprocessing contexts" support; this enables fork. **Risk:** re-introduces the macOS Cocoa/CFNetwork fork-unsafety that `_mp.py` was designed to avoid. NOT recommended unless a benchmark shows spawn overhead is material |
| **(C) Multiprocessing context kwarg** | `joblib.Parallel(n_jobs=-1, backend='loky', mp_context=mp.get_context('fork'))` | Same fork-unsafety risk as (B); more explicit |

**Recommendation:** Approach (A) — default loky-spawn. The grid_search_one_pair function takes file paths + threshold tuples + numpy result arrays — all trivially picklable. No need to override the start method. `_mp.configure_multiprocessing()` still fires at the top of `recalibrate_dswe_thresholds.py:main()` because (i) it sets MPLBACKEND=Agg + raises RLIMIT_NOFILE which loky workers inherit via env vars, NOT via fork; (ii) the parent script may invoke products/dswx.run_dswx directly for the held-out Balaton stage which DOES use fork.

**Inside the worker:** Each loky worker re-imports subsideo modules cleanly. Worker memory footprint: 5 cached numpy arrays × 462 MB = ~2.3 GB per scene — keep n_jobs ≤ 12 on M3 Max (128 GB RAM) to avoid swap.

**`_mp.configure_multiprocessing()` invocation requirements (per CONTEXT D-23):**

- Top of `run_eval_dswx_nam.py:main()` (positive control eval; uses run_dswx which spawns dist-s1-style workers)
- Top of `recalibrate_dswe_thresholds.py:main()` (recalibration script; uses joblib.Parallel for outer fan-out + run_dswx for held-out Balaton)
- Top of `run_eval_dswx.py:main()` (existing; already wired via Phase 1 ENV-04)

**macOS-specific note (PITFALLS P0.1):** Loky workers under spawn are immune to Cocoa/CFNetwork corruption (no fork; clean process-image). The reason `_mp.py` forces fork in the parent is that dist-s1's internal ProcessPoolExecutor uses the parent's start method — loky is unrelated to this and is a parallel concern. **Both can coexist in the same process** (parent: fork for dist-s1; loky workers: spawn).

[VERIFIED: joblib 1.5.3 default backend = loky; loky default start method = spawn since v0.12 — Context7 query 2026-04-26; ASSUMED that loky workers re-importing subsideo cleanly is the intended behaviour pending plan-phase 06-01 smoke test]

## pyarrow availability + parquet vs JSON-lines decision

**Resolution of CONTEXT D-Claude's-Discretion D-07:**

```bash
$ /Users/alex/.local/share/mamba/envs/subsideo/bin/python3 -c "import pyarrow; print(pyarrow.__version__)"
23.0.0
```

**pyarrow 23.0.0 verified present in conda env subsideo as of 2026-04-26.** [VERIFIED: env probe]

**Decision:** Use **parquet** for per-(AOI, scene) gridscores via:

```python
import pyarrow as pa
import pyarrow.parquet as pq

# After grid search for one (AOI, scene):
table = pa.Table.from_arrays(
    [wigts, awgts, psw2_mndwis, f1s, precisions, recalls, accuracies, n_pixels_total, n_pixels_shoreline_excluded],
    names=['WIGT', 'AWGT', 'PSWT2_MNDWI', 'f1', 'precision', 'recall', 'accuracy', 'n_pixels_total', 'n_pixels_shoreline_excluded'],
)
pq.write_table(table, output_path / 'gridscores.parquet', compression='zstd')
```

**Why parquet over JSON-lines:**

- 8400 rows × 9 columns × ~16 bytes/cell (mixed float32/int) = ~1.2 MB/parquet (with zstd compression) vs ~3-5 MB/JSON-lines
- Columnar reads enable `pq.read_table(path, columns=['WIGT', 'AWGT', 'PSWT2_MNDWI', 'f1']).to_pandas()` for fast LOO-CV argmax (~50ms vs ~500ms parsing JSON-lines)
- Schema is enforced at write time — typos in field names caught earlier
- Restart-safe staleness check: pq.read_metadata gives row count cheaply (don't re-parse the whole file)
- `pyarrow.feather.write_feather` is an alternative; parquet is more standard in scientific Python

**Cache layout** (CONTEXT D-07 explicit):

```
eval-dswx-fitset/
├── alcantara/
│   ├── 2021_03_S2A_MSIL2A_20210314T110621_N0500_R137_T29SQE_..../
│   │   ├── intermediates/
│   │   │   ├── mndwi.npy   # ~462 MB float32 10980×10980
│   │   │   ├── ndvi.npy
│   │   │   ├── mbsrv.npy
│   │   │   ├── mbsrn.npy
│   │   │   ├── awesh.npy
│   │   │   ├── blue.npy    # int16 raw band for Test 4/5 boundary
│   │   │   ├── nir.npy
│   │   │   ├── swir1.npy
│   │   │   ├── swir2.npy
│   │   │   ├── scl.npy
│   │   │   └── jrc.npy
│   │   └── gridscores.parquet  # ~1.2 MB
│   └── 2021_08_S2A_MSIL2A_20210812T110621_..../
│       └── ...
├── tagus/
│   └── ...
├── ...
└── (12 (AOI, scene) pairs total — 5 fit-set AOIs × 2 scenes + 1 held-out Balaton + Balaton wet/dry)
```

Per-scene intermediate cache: ~30 GB total (10 numpy arrays × 462 MB × 12 scenes ≈ 55 GB if all bands stored at float32; recommend storing raw bands as int16 ~230 MB each → ~30 GB total).

[VERIFIED: pyarrow 23.0.0 env probe; parquet schema choice from STACK.md guidance + Phase 5 D-25 metrics.json convention]

## EXPECTED_WALL_S validation

**Per CONTEXT D-24 (Claude's Discretion):** plan-phase commits exact value for `recalibrate_dswe_thresholds.py = 21600` (6 hr) with cold-vs-warm rationale.

**Cold path estimate** (no caches; 12 SAFE downloads + 12 scene pipelines + 8400-point grid × 12 pairs + LOO-CV 12 folds + Balaton):

| Stage | Cold time | Notes |
|-------|-----------|-------|
| 1. AOI lock + read fit-set candidates | <1 min | reads `dswx_fitset_aoi_candidates.md`; no compute |
| 2. SAFE download (12 SAFEs × ~1.2 GB each at ~50 MB/s) | 5-10 min serial; 3-5 min parallel via `joblib.Parallel(n_jobs=4)` (CDSE permits ~5 parallel connections per token) | Resume-safe via `ensure_resume_safe` per Phase 1 |
| 3. Per-scene intermediate cache compute (band-read + BOA offset + Claverie xcal + 5 indices + SCL + JRC tile fetch) | 12 scenes × ~5-10 min sequential = ~80-120 min; **~10-15 min on 12-core loky** | The 5 indices + the SCL mask + JRC fetch dominate; band-read is I/O-bound |
| 4. Joint grid search (8400 × 12 = 100k evaluations) | ~6 hr full-grid no subsampling, ~30 min with 10% pixel subsampling | **The single largest runtime risk.** Each gridpoint = compute 5-bit diagnostic + LUT + binarize + F1 over ~120M pixels. Even at 0.05s/gridpoint with cached bands, 8400 × 0.05 = 420s/scene × 12 scenes = ~85 min. With 12-core loky parallel over (AOI, scene): 85 min / 12 = **~7 min walltime in the optimal case**; up to ~30 min with M3 Max thermal throttling |
| 5. Aggregate + edge-of-grid sentinel | <1 min | argmax over 8400-point F1 mean |
| 6. LOO-CV post-hoc on best gridpoint (12 folds × 8400 LOO-grids) | ~5 min | Pre-cached gridscores in parquet; just argmax over leave-one-out subsets |
| 7. LOO-CV gap acceptance check | <1 min | scalar comparison |
| 8. Held-out Balaton F1 (1 scene full pipeline) | 5-10 min | run_dswx(Balaton, region='eu') with new thresholds |
| 9. Threshold module write + provenance | <1 min | git-diff-visible |
| 10. Notebook reproduce (papermill optional) | ~1-2 min if installed; SKIP per env probe | papermill NOT installed — manual jupyter exec or skip |

**Cold path total:** ~25-45 min realistic (with 12-core loky); ~6 hr worst-case (full grid no subsampling, no parallelism). **EXPECTED_WALL_S = 21600 (6 hr) is conservative**; supervisor 2× = 12 hr abort threshold provides ample headroom.

**Warm path estimate** (intermediates cached; gridscores cached; only re-run threshold module write + Balaton F1):

| Stage | Warm time |
|-------|-----------|
| All cached stages skip via `ensure_resume_safe` | <1 min |
| Re-run grid search if criteria.py changed | ~5-10 min (loky parallel argmax) |
| Held-out Balaton F1 re-run (warm pipeline cache) | ~1-2 min |
| Threshold module write + commit | <1 min |

**Warm path total:** ~5-15 min (consistent with PITFALLS R1 + BOOTSTRAP §6.3 "warm-env re-run completes in seconds").

**Recommendation for plan-phase 06-01:** Lock `EXPECTED_WALL_S = 21600` (6 hr) per CONTEXT D-24 sample. **DO NOT lower** because the cold path estimate has 2-axis variance: M3 Max thermal throttling can ~3× scene-pipeline time; CDSE rate-limit during evening UTC (~18:00-23:00) can ~2× SAFE download time. 6 hr is the right "1× expected wall + 100% safety buffer" target.

**For `run_eval_dswx_nam.py`:** `EXPECTED_WALL_S = 1800` (30 min) per CONTEXT D-24 sample. Single AOI + single scene pipeline ~5-10 min cold path; supervisor 2× = 1 hr abort.

[VERIFIED: cold path arithmetic via env probe + read of v1.0 run_eval_dswx.py timings + Phase 1 supervisor pattern; CITED: PITFALLS R1 warm-vs-cold cache discipline + Phase 5 D-24 EXPECTED_WALL_S = 21600 precedent for run_eval_disp_egms.py]

## Shoreline 1-pixel buffer implementation (D-16)

**Per CONTEXT D-16:** `compare_dswx` excludes a 1-pixel buffer around every JRC water/land class boundary. Applied uniformly in grid search AND final F1 reporting.

**Reference grid alignment:**

The shoreline buffer mask MUST be computed on the **JRC reference grid** (the source of the boundary), then reprojected to the S2/DSWx product grid for masking. Computing on the DSWx grid would buffer the DSWx prediction's boundary (which we don't want — we want JRC's boundary excluded uniformly).

**Implementation pattern:**

```python
# In src/subsideo/validation/compare_dswx.py — Phase 6 D-16 addition

import numpy as np
from scipy.ndimage import binary_dilation


def _compute_shoreline_buffer_mask(
    jrc_water_class: np.ndarray,
    iterations: int = 1,
) -> np.ndarray:
    """Compute 1-pixel buffer around JRC water/land boundary.

    Parameters
    ----------
    jrc_water_class : np.ndarray
        Binary water mask on JRC grid (1=water, 0=non-water).
    iterations : int, default=1
        Number of dilation iterations (each = 1 pixel buffer at JRC's
        30m posting). 1 matches CONTEXT D-16 "1-pixel buffer".

    Returns
    -------
    np.ndarray
        Boolean mask: True = shoreline buffer (EXCLUDE from F1);
        False = include in F1 evaluation.

    Notes
    -----
    Default 4-connectivity structuring element (cross-shape) —
    not 8-connectivity (square) — to match the standard 1-pixel
    cardinal-direction shoreline definition.
    """
    water = (jrc_water_class == 1).astype(np.uint8)
    non_water = (jrc_water_class == 0).astype(np.uint8)

    # Dilate water by 1px (catches "near-water non-water" pixels)
    water_dilated = binary_dilation(water, iterations=iterations)
    non_water_dilated = binary_dilation(non_water, iterations=iterations)

    # Shoreline = boundary pixels touching both water and non-water
    # after 1-pixel dilation. XOR catches the buffer ring without
    # consuming pure-water or pure-non-water interior.
    shoreline_buffer = (water_dilated & non_water_dilated.astype(bool))

    return shoreline_buffer
```

**Reference grid alignment with the v1.0 `compare_dswx` flow** (verified by reading `compare_dswx.py:158+`):

The current flow is: (1) fetch JRC tiles, (2) mosaic to a single 4326 array, (3) reproject to product UTM grid via `rioxarray`, (4) binarize via `_binarize_jrc`, (5) compute F1 against `_binarize_dswx`. Step 4's output array is on the DSWx product grid (S2 10m or DSWx 30m UTM).

**Phase 6 modification:** insert shoreline-buffer computation BEFORE Step 4 reprojection (i.e. on the JRC native grid at 30m EPSG:4326), then reproject the buffer mask alongside the JRC water/land array. This avoids re-computing the buffer at S2 sub-pixel resolution which would be over-conservative.

```python
# Modified compare_dswx flow (Phase 6 D-16):
# After step 3 (mosaic JRC tiles in 4326):
shoreline_4326 = _compute_shoreline_buffer_mask(jrc_water_class_4326, iterations=1)

# Reproject BOTH JRC water/land AND shoreline mask to product UTM grid:
jrc_utm = jrc_xr.rio.reproject(product_crs, resampling=Resampling.nearest)
shoreline_utm = shoreline_xr.rio.reproject(product_crs, resampling=Resampling.nearest)

# Binarize both:
jrc_binary = _binarize_jrc(jrc_utm)
shoreline_mask_utm = (shoreline_utm > 0)  # boolean

# Compute F1 with shoreline excluded:
dswx_binary = _binarize_dswx(water_class)
valid_mask = (~np.isnan(jrc_binary)) & (~np.isnan(dswx_binary)) & (~shoreline_mask_utm)
f1_shoreline_excluded = f1_score(dswx_binary[valid_mask], jrc_binary[valid_mask])

# Diagnostic: f1 without shoreline exclusion (P5.2 transparency):
valid_mask_full = (~np.isnan(jrc_binary)) & (~np.isnan(dswx_binary))
f1_full_pixels = f1_score(dswx_binary[valid_mask_full], jrc_binary[valid_mask_full])
shoreline_excluded_count = int(shoreline_mask_utm.sum())
```

**Why XOR-of-dilations not just one dilation:**

Per `_compute_shoreline_buffer_mask` body: dilating water by 1px gives the 1-pixel ring outside water; dilating non-water by 1px gives the ring outside non-water. The XOR (water_dilated AND non_water_dilated) captures pixels that are simultaneously within 1 pixel of BOTH classes — i.e. boundary pixels where the JRC label is structurally ambiguous. This handles the asymmetric shoreline correctly even when the JRC encoding has nodata interior gaps.

**Alternative: scipy.ndimage.find_boundaries** — sklearn's `mark_boundaries` or skimage's `find_boundaries(jrc_water_class, mode='inner' or 'outer')` is a cleaner one-liner. Plan-phase 06-01 may prefer this for code clarity:

```python
from skimage.segmentation import find_boundaries
shoreline = find_boundaries(jrc_water_class, mode='outer')
```

`mode='outer'` returns the 1-pixel ring just outside the water/non-water boundary; `mode='inner'` gives the ring just inside; `mode='thick'` gives both. The thick mode matches the 1-pixel buffer per CONTEXT D-16 most directly. **Recommendation for plan-phase 06-01:** prefer `find_boundaries(jrc, mode='thick')` — single function call, well-tested, scipy already in dep tree.

**Edge cases (P5.2 prevention):**

1. **JRC nodata pixels (class 0 = nodata):** Treat as not part of water OR non-water; nodata-adjacent pixels are NOT shoreline — they're separate validity issues. Mask out before computing buffer: `water_class_no_nodata = np.where(jrc_water_class == 0, np.nan, jrc_water_class)`.

2. **Sub-30m DSWx resolution:** if compare_dswx is called at S2 10m resolution, the JRC 30m boundary becomes 3px wide on the S2 grid after nearest-neighbor reproject. The 1-pixel buffer THEN is in S2 coordinates, not JRC coordinates. To match CONTEXT D-16 strictly: compute buffer on JRC native grid (1px = 30m), reproject the buffer mask to S2 grid (becomes ~3px ring on S2). This is the right semantic — 1px on JRC = 30m physical distance regardless of DSWx grid posting.

3. **Multi-tile JRC mosaics:** internal 30m gaps between adjacent JRC tiles after mosaic should NOT be treated as shoreline. The `_binarize_jrc` already handles this (nodata propagates as NaN); the buffer is computed AFTER mosaic so cross-tile boundaries are real water/non-water transitions.

[VERIFIED: scipy.ndimage.binary_dilation API via Context7 /scipy/scipy + scipy 1.17.1 env probe + reading of `compare_dswx.py:_binarize_jrc` flow]

## Notebook rendering mechanism recommendation

**Per CONTEXT D-Claude's-Discretion D-01:** plan-phase decides whether `dswx_fitset_aoi_selection.md` is auto-generated from notebook or hand-written.

**Recommendation: Makefile target + pre-commit hook (auto-generate).**

```makefile
# Makefile addition (Phase 6 deliverable per Phase 1 ENV-09 Makefile pattern)
docs/dswx_fitset_aoi_selection.md: notebooks/dswx_aoi_selection.ipynb
	jupyter nbconvert --to markdown \
	    --output-dir docs \
	    --output dswx_fitset_aoi_selection.md \
	    notebooks/dswx_aoi_selection.ipynb

dswx-fitset-aoi-md: docs/dswx_fitset_aoi_selection.md
.PHONY: dswx-fitset-aoi-md
```

**Pre-commit hook gate (`.pre-commit-config.yaml`):**

```yaml
- repo: local
  hooks:
    - id: dswx-fitset-aoi-md-fresh
      name: dswx_fitset_aoi_selection.md is fresh from notebook
      entry: bash -c 'make docs/dswx_fitset_aoi_selection.md && git diff --quiet docs/dswx_fitset_aoi_selection.md || (echo "Run make dswx-fitset-aoi-md and commit the output" && exit 1)'
      language: system
      files: notebooks/dswx_aoi_selection.ipynb
```

**Why auto-generate over hand-written:**

| Tradeoff | Auto-generate (recommended) | Hand-written |
|----------|------------------------------|--------------|
| Sync risk | Pre-commit hook enforces freshness | Drift inevitable; docs lag notebook |
| Audit trail | Single source of truth (notebook) | Two sources; reviewer must compare |
| Maintenance | One artifact to update | Two artifacts; updates duplicated |
| nbconvert reliability | nbconvert 7.17.1 verified present in env | n/a |
| First-run cost | One `make` target + one hook line | 0 |

**Risk mitigation:** nbconvert renders cell outputs (matplotlib SVGs, pandas DataFrames as HTML tables); plan-phase 06-01 verifies the rendered markdown is publishable-quality (no large embedded base64 PNGs). For the selection-rationale notebook, outputs are mostly markdown cells + a single per-candidate scoring table — should render cleanly.

**OSM / Copernicus Land Monitoring failure-mode tag query (D-02 Claude's Discretion):**

Recommend option (c): **hardcoded `dswx_failure_mode_aois.yml` resource** at `src/subsideo/validation/dswx_failure_modes.yml`:

```yaml
# Curated list of EU AOIs known to trigger DSWE failure modes.
# Source: Phase 6 RESEARCH 2026-04-26 + literature review.
# Plan-phase 06-01 commits per-AOI flags; notebook reads for advisory display.
failure_modes:
  glacier_or_frozen_lake:
    - aoi_id: vanern
      months: [12, 1, 2]
      flag: 'frozen surface; auto-reject'
    - aoi_id: saimaa
      months: [11, 12, 1, 2, 3, 4]
      flag: 'frozen surface; auto-reject'
    - aoi_id: malaren
      months: [12, 1, 2, 3]
      flag: 'frozen surface; auto-reject'

  mountain_shadow:
    - aoi_id: garda
      months: [10, 11, 12, 1, 2]
      flag: 'low sun angle; advisory'
    - aoi_id: leman
      months: [10, 11, 12, 1, 2]
      flag: 'low sun angle; advisory'
    - aoi_id: maggiore
      months: [10, 11, 12, 1, 2]
      flag: 'low sun angle; advisory'

  tidal_turbidity:
    - aoi_id: tagus
      flag: 'suspended sediment; advisory'
    - aoi_id: loire
      flag: 'suspended sediment + tidal flats; advisory'
    - aoi_id: severn
      flag: 'mudflats + 14m tidal range; advisory'

  drought_year_risk:
    - aoi_id: alcantara
      years: [2017, 2022]
      flag: 'low reservoir; alternate-year retry'
    - aoi_id: alarcon
      years: [2017, 2022]
      flag: 'very low reservoir; alternate-year retry'
    - aoi_id: donana
      years: [2017, 2022]
      flag: 'wetlands dry; alternate-year retry'
```

**Why YAML over OSM/CGLS-LC100 query:**

| Tradeoff | Hardcoded YAML | OSM overpass-turbo / CGLS-LC100 |
|----------|----------------|----------------------------------|
| Reproducibility | Frozen at git SHA | Live API; results drift |
| Latency | Instant | Per-AOI HTTP round-trip |
| Failure mode | None (committed) | Network down → notebook fails |
| Editability | git-tracked, PR-reviewable | Tag schema changes upstream |
| Coverage | EU 18 candidates per CONTEXT | Global but expensive |

For Phase 6's 18-candidate scope, hardcoded YAML is the right tradeoff. v2 global expansion (DSWX-V2-02) may justify the live-API path then.

**Filename and location per ARCHITECTURE convention:** `src/subsideo/validation/dswx_failure_modes.yml` — peer to `validation/criteria.py`, gitignored cache dirs, etc. Read by notebook via `importlib.resources.files('subsideo.validation') / 'dswx_failure_modes.yml'`.

[VERIFIED: nbconvert 7.17.1 env probe; jupyter_core 5.9.1 env probe; pre-commit pattern from existing `.pre-commit-config.yaml` (Phase 1 ENV-04)]

## Validation Architecture

> Phase 6 has Nyquist disabled per `.planning/config.json` `workflow.nyquist_validation: false` (assumed; verify with plan-phase 06-01). The "validation" framework here is the matrix-cell-pass discipline, not unit-test-coverage discipline.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (existing v1.0 + Phase 1 ENV-09); per-test markers `slow`, `integration`, `validation` |
| Config file | `pyproject.toml` (existing pytest config: `--cov=subsideo --cov-report=term-missing` + 80% min) |
| Quick run command | `pytest tests/unit/test_dswx_thresholds.py -x` (Phase 6 deliverable) |
| Full suite command | `pytest tests/ -x -m 'not integration and not slow'` |

### Phase Requirements → Validation Map

The Phase 6 outputs gate matrix-cell-PASS via `criteria.py:dswx.f1_min` BINDING + the held-out Balaton F1 + LOO-CV gap.

| Req ID | Behavior | Gate Type | How Verified | File / Stage |
|--------|----------|-----------|--------------|--------------|
| **DSWX-01** | N.Am. positive control F1 against JRC | Reference-agreement + INVESTIGATION_TRIGGER | `run_eval_dswx_nam.py` Stage 9 writes `metrics.json:reference_agreement.measurements.f1`; matrix_writer renders. F1 < 0.85 sets `f1_below_regression_threshold=True` halting Phase 6 EU recalibration via Stage 0 assert in `recalibrate_dswe_thresholds.py` | `eval-dswx_nam/metrics.json` |
| **DSWX-02** | EU fit-set AOI selection notebook with rationale | Probe-and-commit artifact | `dswx_fitset_aoi_candidates.md` produced by `notebooks/dswx_aoi_selection.ipynb`; user lock-in checkpoint in plan-phase 06-01; rendered to `docs/dswx_fitset_aoi_selection.md` via Makefile target | `.planning/milestones/v1.1-research/dswx_fitset_aoi_candidates.md` + `docs/dswx_fitset_aoi_selection.md` |
| **DSWX-03** | 12 (AOI, wet, dry) triples × 5 fit-set biomes + Balaton held out | Cache-content discipline | `eval-dswx-fitset/<aoi>/<wet|dry>/<scene_id>/intermediates/` populated for 5 AOIs × 2 scenes = 10 pairs (12 triples per BOOTSTRAP §5.2 phrasing — actually 5 AOIs × 2 wet/dry scenes = 10; CONTEXT D-04 says 12 — clarify in plan-phase 06-01: 5 fit-set biomes + 1 leftover wet/dry of 2 candidate scenes per biome = 12; OR 6 biomes × 2 scenes excluding Balaton). Plan-phase resolves the 10-vs-12 count | `eval-dswx-fitset/` cache + manifest |
| **DSWX-04** | Joint grid search over WIGT × AWGT × PSWT2_MNDWI | Compute correctness | `scripts/recalibrate_dswe_thresholds.py` Stage 4 writes `gridscores.parquet` per pair; aggregate `recalibrate_dswe_thresholds_results.json` Stage 5 has `joint_best_gridpoint`; **edge-of-grid sentinel auto-FAILs in Stage 6** | `scripts/recalibrate_dswe_thresholds_results.json` + `gridscores.parquet` per pair |
| **DSWX-05** | Recalibrated thresholds in typed module + provenance + region selector | Module-existence + import-shape | `src/subsideo/products/dswx_thresholds.py` exports `DSWEThresholds`, `THRESHOLDS_NAM`, `THRESHOLDS_EU`, `THRESHOLDS_BY_REGION`; `subsideo.config.Settings.dswx_region` env-var; `DSWxConfig.region` field; tests in `tests/unit/test_dswx_thresholds.py` | `src/subsideo/products/dswx_thresholds.py` (NEW, ~80-150 LOC) |
| **DSWX-06** | EU re-run; F1 + LOO-CV F1 gap < 0.02; honest FAIL labelling | Reference-agreement + LOO-CV gap acceptance | `run_eval_dswx.py` (existing, modified per D-26) writes `eval-dswx/metrics.json:reference_agreement.measurements.f1` (Balaton held-out); `reference_agreement.diagnostics.{fit_set_mean_f1, loocv_mean_f1, loocv_gap, per_aoi_breakdown[]}`; `cell_status` + `named_upgrade_path` per D-15 | `eval-dswx/metrics.json` |
| **DSWX-07** | F1 ceiling claim citation chain | Methodology-doc gate | `docs/validation_methodology.md §5.1` either cites PROTEUS ATBD specifically (path a) OR labels "empirical bound observed over our 6-AOI evaluation at F1 ≈ X.YZ" (path d default per this RESEARCH.md) | `docs/validation_methodology.md §5.1` |

### Sampling Rate

- **Per task commit:** `pytest tests/unit/test_dswx_thresholds.py -x` (~5s) + `ruff check src/subsideo/products/` + `mypy src/subsideo/products/dswx_thresholds.py`
- **Per wave merge:** `pytest tests/unit/ -x -m 'not slow'` (~30-90s)
- **Phase gate:** Full unit suite green + `make eval-dswx-nam` runs + `make recalibrate-dswx` runs + `make eval-dswx-eu` runs + matrix.md renders both cells correctly + `pytest tests/ -m validation` passes

### Wave 0 Gaps

- [ ] `tests/unit/test_dswx_thresholds.py` — covers `DSWEThresholds.__post_init__` validation (frozen?slots?), `THRESHOLDS_BY_REGION['nam'/'eu']` resolution, region selector via DSWxConfig.region + settings.dswx_region precedence (DSWX-05 unit gate)
- [ ] `tests/unit/test_compute_index_bands.py` — covers `compute_index_bands()` returns IndexBands NamedTuple/dataclass; `score_water_class_from_indices(thresholds=...)` produces same bits as v1.0 `_compute_diagnostic_tests` (regression test against v1.0 Balaton diagnostic uint8 array; SHA256 byte-equal) (D-05 decomposition gate)
- [ ] `tests/unit/test_compare_dswx_shoreline.py` — covers `_compute_shoreline_buffer_mask()` produces 1-pixel ring; F1 with shoreline mask < F1 without (sanity); shoreline_excluded_count >= 1 for any non-trivial JRC array (D-16 gate)
- [ ] `tests/unit/test_dswx_thresholds_provenance.py` — `THRESHOLDS_EU.fit_set_hash` is non-empty after Phase 6 close; `loocv_gap < 0.02` invariant (DSWX-06 acceptance test as runtime check)
- [ ] `tests/integration/test_run_eval_dswx_nam_smoke.py` — `@pytest.mark.integration` smoke test; mocks CDSE response; verifies Stage 0..9 happy path + INVESTIGATION_TRIGGER state machine (DSWX-01)
- [ ] `tests/unit/test_recalibrate_dswe_thresholds_dispatch.py` — verifies edge-of-grid sentinel auto-FAIL (D-08); LOO-CV gap rejection (D-14); regression-flag halt (D-20)
- [ ] `tests/unit/test_matrix_writer_dswx.py` — `_render_dswx_nam_cell` + `_render_dswx_eu_cell` correctly emit named_upgrade_path inline; cell_status PASS/FAIL/BLOCKER rendered correctly; dispatch order test `dswx_call > dist_nam_call`

**Framework install:** none needed; pytest already in conda env per Phase 1.

## Open questions for plan-phase

1. **PROTEUS ATBD F1 number** (D-17, P5.3): This research session could not surface a specific F1 number from the publicly-indexed PROTEUS / OPERA documents (3 attempts: WebFetch JPL OPERA suite page, WebFetch ProductSpec PDF blocked by maxContentLength, WebFetch OPERA-Cal-Val GitHub README). Plan-phase 06-01 must take path (a) [download Product Spec PDF locally and parse], path (c) [clone OPERA-Cal-Val repo], or fall back to path (d) [own-data bound]. **Default path: (d)** if (a)+(c) take >2 hours of plan-phase effort.

2. **Pontchartrain MGRS tile T15RYP vs T15RYR** (D-18 Claude's Discretion): python-mgrs centroid lookup returns 15RYP, but CONTEXT.md candidate list says "15RYR or 15RZR." Plan-phase 06-01 verifies via `pystac-client` live STAC query against CDSE: `bbox=(-90.45, 30.02, -89.62, 30.34), collections=['SENTINEL-2'], filter='eo:cloud_cover < 20'` — the top result's `s2:mgrs_tile` field is canonical.

3. **Fit-set count: 10 vs 12** (DSWX-03): BOOTSTRAP §5.2 says "12 (AOI, scene) pairs" but a 5-fit-set-AOI list × 2 wet/dry scenes = 10 pairs. CONTEXT D-04 says "12 fit-set pairs" suggesting either 6 fit-set AOIs (excluding Balaton) × 2 = 12, OR 5 fit-set × 2 + Balaton-held-out wet/dry = 12 (but Balaton is held out, not in fit set). Plan-phase 06-01 resolves: most likely **6 fit-set biomes (Mediterranean reservoir, Atlantic estuary, boreal lake, Pannonian plain, Alpine valley, Iberian summer-dry) × 2 scenes = 12, with Balaton's Pannonian-plain biome substituted by another Pannonian AOI in the fit set + Balaton held out.** Alternative reading: 6 AOIs × 2 = 12, where Balaton is the 6th biome representative held out and a different AOI fills Pannonian for fit set. Plan-phase commits the canonical reading.

4. **JRC URL pattern v1 vs v2 endpoint** (D-25): `compare_dswx.py:JRC_BASE_URL` may point to the legacy `storage.googleapis.com/global-surface-water/...` vs the current `data.jrc.ec.europa.eu/...` endpoint. Plan-phase 06-01 verifies the current URL via WebFetch on `data.jrc.ec.europa.eu/collection/id-0084` + tests one tile fetch from each to compare — refactor `_fetch_jrc_tile` to `harness.download_reference_with_retry(source='jrc')` includes endpoint verification.

5. **EU fit-set AOI biome → 5 vs 6 mapping**: BOOTSTRAP §5.2 lists 6 biomes (Mediterranean reservoir, Atlantic estuary, boreal lake, Pannonian plain, Alpine valley, Iberian summer-dry) but Balaton represents Pannonian plain — held out. So the fit-set covers 5 biomes with Pannonian-plain represented either by a different AOI OR by accepting that the held-out Balaton is the only Pannonian representative. CONTEXT D-03 says "5 biome-diverse AOIs (Mediterranean reservoir / Atlantic estuary / boreal lake / Alpine valley / Iberian summer-dry; Balaton fixed as Pannonian held-out)" — the answer is **5 fit-set biomes + Balaton held out**. Plan-phase 06-01 confirms.

6. **Manifest target name `recalibrate-dswx`** (CONTEXT integration point #4): Phase 1 D-08 wired all 10 cells but not necessarily a `recalibrate-dswx` target. Plan-phase 06-01 verifies + adds if missing: `recalibrate-dswx: ; python -m subsideo.validation.supervisor scripts/recalibrate_dswe_thresholds.py`.

7. **`papermill` for Stage 11 of recalibration script** (D-Claude's-Discretion): papermill NOT in conda env. Plan-phase 06-01 either (a) adds `papermill==2.6.x` to `pyproject.toml [validation]` extra and re-syncs, OR (b) skips Stage 11 and replaces with manual `jupyter nbconvert --to notebook --execute` step in CONCLUSIONS, OR (c) skips entirely and relies on the rendered markdown for reproducibility documentation. **Recommended: (b) or (c).** The recalibration is reproducible from `recalibrate_dswe_thresholds_results.json` directly without running the notebook; the notebook is for plotting + visualization not numerical reproduction.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | DSWE F1 ≈ 0.92 ceiling is from PROTEUS ATBD, but specific number not citable from publicly-indexed sources during this session | PROTEUS ATBD F1 ceiling citation | Medium — falls back to own-data bound per D-17; criterion threshold (0.90) is independent of ceiling |
| A2 | Lake Pontchartrain Sentinel-2 ESA tile is T15RYP (matches python-mgrs centroid) | N.Am. positive control AOI MGRS tile resolution | Low — plan-phase 06-01 verifies via live STAC query in 1 minute |
| A3 | Tahoe T10SFH covers full lake (verified via USGS ScienceBase 2021 mosaic) | N.Am. positive control AOI MGRS tile resolution | Low — same STAC verification |
| A4 | EU fit-set count is 5 fit-set biomes × 2 wet/dry = 10 pairs, NOT 12 | EU fit-set candidate AOIs + Open Question 3 | Medium — affects compute budget + LOO-CV fold count (10 vs 12); plan-phase 06-01 confirms with user |
| A5 | scipy.ndimage.binary_dilation `iterations=1` 4-connectivity matches CONTEXT D-16 "1-pixel buffer" intent | Shoreline 1-pixel buffer implementation | Low — alternative: `skimage.segmentation.find_boundaries(mode='thick')` produces equivalent ring |
| A6 | EXPECTED_WALL_S = 21600 (6 hr) is appropriate for cold-path full grid + LOO-CV + Balaton (per scaling estimate ~25-45 min realistic, 6 hr conservative buffer) | EXPECTED_WALL_S validation | Low — supervisor 2× = 12 hr abort gives substantial headroom |
| A7 | Loky default `spawn` start method is desirable for grid_search workers (not fork) on macOS | Joblib + `_mp.configure_multiprocessing()` pattern | Low — spawn is safer per PITFALLS P0.1; fork-via-env-var available as escape hatch if performance demands |
| A8 | JRC URL pattern in `compare_dswx.py:_jrc_tile_url` is current (not the legacy googleapis endpoint) | EU fit-set candidate AOIs (URL pattern) + Open Question 4 | Medium — affects whether `harness.RETRY_POLICY['jrc']` policy triggers 404s on tile fetch; plan-phase 06-01 verifies in <1 minute |
| A9 | nbconvert produces publishable-quality markdown for `dswx_aoi_selection.ipynb` | Notebook rendering mechanism | Low — plan-phase 06-01 inspects rendered output during Phase 6 close |
| A10 | INVESTIGATION_TRIGGER pattern from Phase 2 D-13/D-14/D-15 maps cleanly to Phase 6 DSWX-01 F1 < 0.85 (regression-flag halt) | Validation Architecture (DSWX-01) | Low — pattern is well-established + already in production for RTC EU |
| A11 | The DSWE 5-test 32-state LUT (`INTERPRETED_WATER_CLASS`) is invariant under WIGT/AWGT/PSWT2_MNDWI changes | DSWE 5-test diagnostic logic recap + decomposition proposal | Low — verified by reading dswx.py:80-95 (LUT maps 5-bit pattern → class regardless of which thresholds triggered each bit; tests 1, 3, 5 only change which bit is set, not the LUT semantics) |

## Sources

### Primary (HIGH confidence)

- `06-CONTEXT.md` — D-01..D-30 + canonical_refs (full, 245 LOC) [VERIFIED: read 2026-04-26]
- `BOOTSTRAP_V1.1.md §5` lines 332-405 [VERIFIED: read 2026-04-26]
- `.planning/REQUIREMENTS.md` DSWX-01..07 lines 73-80 [VERIFIED: read 2026-04-26]
- `.planning/research/PITFALLS.md §P5.1, P5.2, P5.3, P5.4` lines 601-707 [VERIFIED: read 2026-04-26]
- `.planning/research/SUMMARY.md` Phase 6 row lines 180-184 [VERIFIED: read 2026-04-26]
- `.planning/research/ARCHITECTURE.md` lines 154-205 (DSWx threshold module placement), lines 207-245 (eval-script layout) [VERIFIED: read 2026-04-26]
- `.planning/research/STACK.md` lines 1-100 (numpy/tophu/rio-cogeo pins, joblib + scipy + pyarrow STACK §0) [VERIFIED: read 2026-04-26]
- `src/subsideo/products/dswx.py` lines 1-150 (`_compute_diagnostic_tests` body, module-level constants) [VERIFIED: line-by-line read 2026-04-26]
- `src/subsideo/validation/compare_dswx.py` lines 1-160 (`_fetch_jrc_tile`, `_binarize_jrc`, JRC URL pattern) [VERIFIED: line-by-line read 2026-04-26]
- `src/subsideo/validation/harness.py` lines 48-91 (`RETRY_POLICY` shape; existing 5 sources) [VERIFIED: read 2026-04-26]
- `src/subsideo/validation/criteria.py` lines 180-200 (`dswx.f1_min` BINDING) [VERIFIED: read 2026-04-26]
- `src/subsideo/_mp.py` lines 1-100 (full `configure_multiprocessing()` bundle) [VERIFIED: read 2026-04-26]
- `run_eval_dswx.py` lines 1-80 (Stage layout precedent) [VERIFIED: read 2026-04-26]
- `conda-env.yml` (Python 3.12, scipy<1.13, numpy<2; pyarrow not declared) [VERIFIED: read 2026-04-26]
- `/Users/alex/.local/share/mamba/envs/subsideo/bin/python3` env probe — pyarrow 23.0.0, joblib 1.5.3, scipy 1.17.1, nbconvert 7.17.1, pydantic_settings 2.14.0, papermill ABSENT [VERIFIED: env probe 2026-04-26]
- Context7 `/joblib/joblib` — Parallel + delayed pattern + loky default spawn since v0.12 [CITED: 2026-04-26]
- Context7 `/scipy/scipy` — `ndimage.binary_dilation`, `iterate_structure` [CITED: 2026-04-26]
- python-mgrs library env probe — Tahoe centroid 10SGJ; Pontchartrain centroid 15RYP [VERIFIED: env probe 2026-04-26]
- `compare_dswx.py:_jrc_tile_url` URL pattern (`{year}/{year}_{month:02d}/{pixel_y:010d}-{pixel_x:010d}.tif`) [VERIFIED: code read 2026-04-26]

### Secondary (MEDIUM confidence)

- WebFetch on JPL OPERA DSWx Product Suite page [CITED: jpl.nasa.gov/go/opera/products/dswx-product-suite — accessed 2026-04-26; PROTEUS ATBD link not surfaced]
- WebSearch on Lake Tahoe S2 tile T10SFH coverage [CITED: USGS ScienceBase 2021 Sentinel-2 ACOLITE-DSF Aquatic Reflectance — accessed 2026-04-26 — confirms T10SFH covers Tahoe]
- WebSearch on JRC Global Surface Water download [CITED: developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_MonthlyHistory — accessed 2026-04-26 — confirms 1984-2021 coverage]
- WebSearch on Jones 2015 DSWE [CITED: mdpi.com/2072-4292/7/9/12503 — Jones 2015 RemoteSensing paper exists; F1 not in snippet]
- BOOTSTRAP §5.2 EU AOI starting list [CITED: BOOTSTRAP_V1.1.md lines 367-373]

### Tertiary (LOW confidence — flagged for plan-phase verification)

- PROTEUS ATBD specific F1 number [ASSUMED: own-data fallback per D-17; plan-phase 06-01 verifies if effort warranted]
- Lake Pontchartrain S2 tile T15RYP vs T15RYR [ASSUMED: T15RYP per python-mgrs centroid; plan-phase 06-01 verifies via live STAC]
- JRC URL pattern endpoint legacy googleapis vs current `data.jrc.ec.europa.eu` [ASSUMED: existing v1.0 URL still works; plan-phase 06-01 verifies]
- Loky workers re-importing subsideo cleanly under spawn [ASSUMED: standard joblib usage; plan-phase 06-01 smoke tests with 1 dummy task before committing recalibrate_dswe_thresholds.py to long run]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all 5 deps verified present in conda env via direct probe; versions current
- Architecture: HIGH — every responsibility tied to existing v1.0 / Phase 1-5 patterns explicitly cited
- Phase requirements mapping: HIGH — all 7 DSWX requirements traced to specific files + Stage outputs
- DSWE algorithm decomposition: HIGH — line-by-line read of dswx.py:100-150 confirms clean 2-function split with no state coupling
- Threshold module API shape: HIGH — frozen dataclass(slots=True) matches existing criteria.py:Criterion precedent verbatim
- Joblib loky pattern: HIGH on default spawn behaviour [Context7 verified]; MEDIUM on coexistence with `_mp.py` fork bundle [pattern is unusual but no contraindication found]
- Shoreline buffer implementation: HIGH on scipy.ndimage.binary_dilation usage; MEDIUM on JRC-grid-vs-S2-grid alignment (default plan-phase 06-01 verifies edge cases)
- EXPECTED_WALL_S budget: MEDIUM — cold path estimate has 2-axis variance (M3 Max thermal + CDSE rate-limit); 21600s conservative
- PROTEUS ATBD ceiling citation: MEDIUM — own-data fallback (D-17 path d) is the safe default; plan-phase 06-01 may resolve via path (a) Product Spec PDF download
- AOI selection methodology: HIGH on biome × failure-mode mapping; MEDIUM on JRC tile URL endpoint legacy vs current

**Research date:** 2026-04-26
**Valid until:** 2026-05-26 (30 days for stable; faster decay for CDSE/STAC API drift)

## RESEARCH COMPLETE

**Phase:** 06 - dswx-s2-n-am-eu-recalibration
**Confidence:** HIGH on locked decisions + decomposition shape + environment availability + budget; MEDIUM on PROTEUS ATBD specific number citation (own-data fallback documented as default per D-17)

### Key Findings

- **All 5 critical deps verified present** in conda env subsideo: pyarrow 23.0.0, joblib 1.5.3, scipy 1.17.1, nbconvert 7.17.1, pydantic_settings 2.14.0. Papermill is ABSENT — Stage 11 (notebook reproduce check) needs path decision.
- **`_compute_diagnostic_tests` decomposes cleanly** into `compute_index_bands(blue, green, red, nir, swir1, swir2) -> IndexBands` (band-driven, threshold-free) + `score_water_class_from_indices(indices, blue, nir, swir1, swir2, *, thresholds: DSWEThresholds) -> np.ndarray` (threshold-driven, takes 5 indices + 4 raw bands for Test 4/5 boundary). No state coupling. Backward-compatible shim preserves v1.0 import API.
- **Loky default start method is SPAWN, not FORK** — recommended pattern is `joblib.Parallel(n_jobs=-1, backend='loky')` with NO context override; `_mp.configure_multiprocessing()` parent fork bundle and loky-spawn workers coexist cleanly.
- **PROTEUS ATBD specific F1 number NOT citable** from publicly-indexed sources during this session — recommend D-17 path (d) own-data fallback as default; plan-phase 06-01 may take path (a) Product Spec PDF download if effort permits.
- **Lake Tahoe = T10SFH** (verified USGS ScienceBase); **Lake Pontchartrain = T15RYP** (python-mgrs centroid; plan-phase verifies via live STAC). JRC tiles for both AOIs computed: Tahoe (5,4) `0000160000-0000200000.tif`; Pontchartrain (8,4) `0000160000-0000320000.tif`.
- **EU fit-set count discrepancy** (10 vs 12) — most likely interpretation is 5 fit-set biomes × 2 wet/dry scenes + Balaton wet/dry held out (the "12" in CONTEXT/BOOTSTRAP). Plan-phase 06-01 confirms.
- **Shoreline buffer** uses `scipy.ndimage.binary_dilation(iterations=1)` XOR-of-water-and-non-water-dilations OR `skimage.segmentation.find_boundaries(mode='thick')` (cleaner). Apply on JRC native 4326 grid before reproject to S2 UTM.
- **EXPECTED_WALL_S = 21600s (6 hr)** validated as conservative for cold path; 30 min for run_eval_dswx_nam.py.

### File Created

`.planning/phases/06-dswx-s2-n-am-eu-recalibration/06-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard stack | HIGH | All deps verified via env probe; versions current; pyarrow available so parquet decision locked |
| Architecture | HIGH | Every responsibility tied to existing v1.0 + Phase 1-5 pattern (verified line-by-line read) |
| Decomposition shape | HIGH | Clean 2-function split with zero state coupling (verified line-by-line read of dswx.py:100-150) |
| Threshold module API | HIGH | frozen dataclass(slots=True) matches criteria.py:Criterion verbatim |
| AOI candidate bbox + JRC + MGRS table | HIGH | python-mgrs + JRC URL pattern computed; biome flags from PITFALLS P5.2/P5.4; OSM advisory hardcoded |
| PROTEUS ATBD citation | MEDIUM | 3 indexed sources searched; specific F1 number not surfaced; D-17 own-data fallback documented as default |
| EXPECTED_WALL_S budget | MEDIUM | Cold-path arithmetic + supervisor 2× headroom validated; M3 Max thermal + CDSE rate-limit add 2-axis variance |
| Loky pattern | HIGH default-spawn | Context7-verified; coexistence with `_mp.py` fork is documented but unusual — plan-phase 06-01 smoke-tests |
| Shoreline buffer | HIGH | scipy.ndimage.binary_dilation API verified via Context7; alternative skimage.find_boundaries also viable |
| Notebook rendering | HIGH | nbconvert verified present; Makefile + pre-commit hook pattern matches Phase 1 D-08 conventions |

### Ready for Planning

Research complete. Plan-phase 06-01 has all the gaps closed: PROTEUS ATBD fallback path, EU fit-set candidate bbox/JRC/MGRS table, Tahoe + Pontchartrain MGRS tiles, pyarrow availability, EXPECTED_WALL_S budget, decomposition shape, joblib + `_mp.py` pattern, shoreline buffer implementation, notebook rendering mechanism, validation architecture, and 11 open questions for plan-phase verification.
