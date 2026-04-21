# Feature Research — v1.1 N.Am./EU Validation Parity & Scientific PASS

**Domain:** validation / eval hardening for an OPERA-equivalent SAR/InSAR/optical product library
**Researched:** 2026-04-20
**Confidence:** HIGH (every feature is specified in BOOTSTRAP_V1.1.md; this file rationalises, categorises, and surfaces dependencies against the v1.0 codebase I read under `src/subsideo/validation/` and the `run_eval_*.py` scripts in the project root)

---

## Scope reminder — what this milestone is and is not

This is a **validation / scientific-closure milestone**, not a feature-addition milestone. The five product pipelines already exist and ship in v1.0. What v1.1 adds is:

1. Infrastructure that turns ad-hoc per-script eval plumbing into a shared harness.
2. Product-quality gates (self-consistency) that don't depend on reference products.
3. Eval coverage in regions where v1.0 never ran (RTC-EU, CSLC-EU, DSWx-N.Am.).
4. A single canonical results matrix and a one-command re-run path.
5. Explicit, honest PASS / FAIL-with-named-upgrade / deferred-with-unblock per cell.

The "user" throughout this document is **Alex (the developer running `make eval-all`)**. End-user-visible product APIs are **not** changing in v1.1.

---

## Feature Landscape

### Table Stakes (milestone fails without these)

The milestone's own closure test is `fresh clone → conda env create → make eval-all → filled results matrix`. Every feature below is on that critical path.

#### Phase 0 — Environment hygiene & harness

| Feature | Why it's table-stakes | Complexity | Extends / depends on |
|---------|----------------------|------------|----------------------|
| **numpy < 2.0 pin in `conda-env.yml`** + removal of the four `_patch_*` calls in `src/subsideo/products/cslc.py` | Every v1.0 CSLC run has a monkey-patch dependency; leaving it means the milestone ships with runtime patches the BOOTSTRAP explicitly forbids | S | Modifies `conda-env.yml`; deletes code from `src/subsideo/products/cslc.py`; touches unit tests that asserted patch behaviour |
| **`tophu` as first-class pip dep in `conda-env.yml`** | Dolphin imports tophu unconditionally; fresh envs break without it | S | Modifies `conda-env.yml` pip block; new regression test asserting `from dolphin.unwrap import run` succeeds |
| **`src/subsideo/_cog.py` helper** (version-aware `cog_validate` / `cog_translate` wrapper) | rio-cogeo 7.x moved `cog_validate`; three product files currently break on import; the milestone requires a single import point | S | New module; replaces direct `rio_cogeo` imports in `src/subsideo/products/{rtc,dswx,dist}.py`; ripgrep check `rg "from rio_cogeo" src/` must return only `_cog.py` |
| **`src/subsideo/_mp.py` helper** (forces `fork` start method on macOS; watchdog that aborts after 2× expected wall time) | `dist_s1` deadlocks on macOS with default `spawn`; opera-rtc needs the `__main__` guard; without this, three-of-three fresh `run_eval_dist*.py` runs do not succeed | M | New module; called at top of every `run_*()` entry point in `src/subsideo/products/*.py`; watchdog is a `threading.Timer` around the subprocess call — not a first-class library feature |
| **`subsideo.validation.harness` module** (new package under `src/subsideo/validation/`) with four functions: `select_opera_frame_by_utc_hour`, `download_reference_with_retry`, `ensure_resume_safe`, `credential_preflight` | Every `run_eval_*.py` currently open-codes these concerns differently; the milestone explicitly requires "`run_eval_disp_egms.py` diff against `run_eval_disp.py` contains only reference-data differences, not plumbing differences" | L | New module; replaces ad-hoc code in all seven `run_eval_*.py` files in repo root; depends on `earthaccess` (Earthdata), `CDSEClient` (already in `src/subsideo/data/cdse.py`), plain `requests` for CloudFront |
| `select_opera_frame_by_utc_hour(frames, burst_utc_hour, burst_bbox) -> OperaFrame` | Existing N.Am. eval (`run_eval.py`) currently hand-picks UTC-hour frames by string prefix match on `granule_name`; OPERA occasionally publishes frames at ±1h offsets, and the spatial bbox check catches the "right hour wrong footprint" edge case | S | Takes a list of ASF DAAC `ASFProduct` (or equivalent dict) candidates + target sensing UTC hour (int 0-23) + target burst WGS84 bbox; exact-hour preference first, ±1h fallback, filter to those whose footprint intersects the burst bbox, return best match (smallest Haversine centroid distance among matches). Anti-pattern prevented: "frame matched on date alone → wrong swath fetched" |
| `download_reference_with_retry(urls, out_dir, auth, backoff_cap_s=300) -> list[Path]` | CDSE 429s, ASF OOM markers, CloudFront rate-limits — each currently hand-patched per script with different backoff strategies | M | Auth backends to support: **Earthdata** (uses `earthaccess.get_requests_session()`), **CDSE OAuth2** (reuses `CDSEClient._get_token()`), **plain HTTPS** for CloudFront (no auth, just `requests.Session()` with a UA header). Retry triggers: HTTP 429, HTTP 503, `CDSE_OOM` body-string marker, connection reset errno, partial-content < expected bytes. Backoff: `min(backoff_cap_s, 2**attempt + jitter)`, `backoff_cap_s=300` means the 6th retry caps at 300s and stays there for remaining attempts (default 8). Returns list of paths in same order as input URLs |
| `ensure_resume_safe(output_paths, checker_fn) -> bool` | "Cached" currently = "any file exists" — corrupt partial downloads cause silent re-use | S | Takes an iterable of `Path` plus a `checker_fn: (Path) -> bool` (e.g., `rasterio.open(p).read(1).any()` for a COG; `h5py.File(p).keys()` non-empty for HDF5). Returns `True` only if every path exists AND passes checker. Anti-feature blocked: "smart content-hash equality check" (BOOTSTRAP says resume-safety is structural, not semantic) |
| `credential_preflight(required=['EARTHDATA', 'CDSE_OAUTH', 'CDSE_S3', 'CDSAPIRC']) -> CredentialStatus` | Today a missing key produces a 401 deep inside the pipeline, hours into an eval | S | Human output: coloured terminal block, one line per credential with ✓ / ✗ / ⚠ and the setup URL (same URL style already used in `run_eval_disp_egms.py`). Machine output: JSON via `--json` flag. Return dataclass with `.ok: bool`, `.missing: list[str]`, `.warnings: list[str]` so `make` can exit non-zero before any compute begins. Known credentials: `EARTHDATA` (EARTHDATA_USERNAME/PASSWORD), `CDSE_OAUTH` (CDSE_CLIENT_ID/SECRET), `CDSE_S3` (CDSE_S3_ACCESS_KEY/SECRET_KEY — separate from OAuth per `run_eval_dswx.py` preflight), `CDSAPIRC` (file `~/.cdsapirc` exists and parses), `EGMS_TOKEN`. Not terminal-coloured by default — coloured only when stdout is a TTY (so CI logs stay clean) |
| **Programmatic DEM bounds** helper | `run_eval.py` hand-codes `DEM_BBOX = [-119.7, 33.2, -118.3, 34.0]`; reusing across EU bursts requires a programmatic path | S | Pattern already exists in `run_eval_disp.py`; extract to a helper `subsideo.burst.bbox.dem_bbox_from_burst(burst_id: str, buffer_deg: float = 0.2) -> tuple[float, float, float, float]` that reads the burst footprint from `opera_utils.burst_frame_db` and buffers |
| **`Makefile` with `eval-{product}-{region}`, `eval-all`, `eval-nam`, `eval-eu` targets** | The milestone-closure test calls `make eval-all` by name; without the Makefile the closure test is meaningless | S | New top-level `Makefile`. Each target wraps the corresponding `run_eval_*.py` script. `eval-all` depends on every per-cell target plus a final `results/matrix.md` write step. Re-run on warm env must finish in seconds (all individual scripts are already resume-safe, so this is automatic if Phase 0.5 lands cleanly) |
| **`results/matrix.md` writer** | A table written across all eval scripts is already the milestone's canonical status artifact (matrix layout sketched in BOOTSTRAP §6.1); without a writer the closure test cannot produce it | S | New module `src/subsideo/validation/matrix.py`. Aggregates per-eval JSON sidecar files written by each `run_eval_*.py` (new convention: each eval writes `eval-{product}-{region}/metrics.json`). Markdown generation via plain f-string or `tabulate` — not Jinja (report.py already uses Jinja; matrix is simpler and does not need templates) |

#### Phase 1 — RTC EU validation

| Feature | Why it's table-stakes | Complexity | Extends / depends on |
|---------|----------------------|------------|----------------------|
| **Candidate-burst probe report** | The BOOTSTRAP names 5 candidate EU bursts; the probe is a Phase 0/1-boundary artifact that must exist before Phase 1 can run because any burst without ASF OPERA RTC coverage is a wasted compute run | S | Produces `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` with: burst ID, OPERA RTC availability on ASF DAAC (granule count in 2024-01 to 2025-12), best matching S1 sensing date, whether SAFE/DEM/orbit are already cached. Query implementation uses `asf-search` like the existing `run_eval_disp.py` |
| **`run_eval_rtc_eu.py`** (fork of `run_eval.py`) | The eval script that actually runs the comparison | M | Reuses cached DEM/orbits/SAFEs where available. Runs `subsideo.products.rtc.run_rtc`. Calls `compare_rtc(product_path, reference_path)` already in `src/subsideo/validation/compare_rtc.py` (no changes to `compare_rtc.py` needed). Writes `eval-rtc-eu/{burst_id}/metrics.json` for each burst |
| **Per-burst PASS/FAIL output** | Without per-burst rows the matrix cell collapses to one number over regionally-diverse data, which contradicts the reproducibility-across-geographies framing | S | Output format: a small markdown table inside `CONCLUSIONS_RTC_EU.md` plus the per-burst rows aggregated to a single matrix cell "5/5 PASS" or "3/5 PASS, 2/5 FAIL". Criteria per burst identical to N.Am.: RMSE < 0.5 dB, r > 0.99 |
| **`CONCLUSIONS_RTC_EU.md`** | Mirrors `CONCLUSIONS_RTC_N_AM.md` convention; milestone expects per-phase conclusions docs | S | Standard template used throughout v1.0: context, reference-agreement numbers, what it validates, what it doesn't, next-actions |

#### Phase 2 — CSLC self-consistency gate + EU

| Feature | Why it's table-stakes | Complexity | Extends / depends on |
|---------|----------------------|------------|----------------------|
| **Self-consistency coherence computation** on stable terrain | The BOOTSTRAP explicitly calls this out as the product-quality gate that replaces the methodologically-impossible cross-version phase comparison; without it CSLC has no product-quality number in any matrix cell | L | New code: probably `src/subsideo/validation/selfconsistency.py` with `compute_stable_coherence(cslc_stack: list[Path], aoi_mask: np.ndarray, slope_mask: np.ndarray) -> float`. Inputs: 15 CSLC HDF5 files from sequential 12-day passes; stable-terrain mask = ESA WorldCover class 60 (bare/sparse vegetation) AND slope < 10°. Computation: form 14 sequential single-look interferograms via `prod_t * conj(prod_t+1)`, compute pixel-wise coherence via a small boxcar (typical 5×5), mean over stable-terrain pixels within the burst footprint, report a single scalar per AOI. The gate: mean coherence > 0.7 |
| **Stable-PS residual velocity computation** | Second half of the product-quality gate: "residual mean velocity < 5 mm/yr at stable reference points" — a PASS/FAIL number per AOI | M | Depends on existence of "stable reference points" per region. Operational definition per BOOTSTRAP §2: <br>• **US**: OPERA-CSLC-derived stable pixels (operationally: pixels passing the WorldCover class 60 + slope < 10° mask AND with inter-epoch phase std below a threshold; the threshold is the research parameter — start from published InSAR-stable-pixel thresholds, tune on the SoCal cached stack). <br>• **EU**: EGMS L2a PS points labelled stable by EGMS itself (i.e., EGMS L2a `mean_velocity_std < 2 mm/yr`; the L2a columns already expose this — see `_load_egms_l2a_points` in `src/subsideo/validation/compare_disp.py`). <br>The computation itself: sample our chain's MintPy-inverted (or simple velocity-fit) time-series at the stable-point locations, compute mean absolute residual velocity in mm/yr. |
| **ESA WorldCover + SRTM slope mask builder** | The stable-terrain mask inputs aren't yet acquired in v1.0 | S-M | New module `src/subsideo/validation/stable_terrain.py` with: `fetch_worldcover_class60(bbox, out_dir)` using the ESA WorldCover S3 bucket (`s3://esa-worldcover/v200/2021/`, public-read, STAC-browsable); `compute_slope_from_dem(dem_path) -> np.ndarray` using `gdaldem slope` or numpy gradient — already have DEM caching via `subsideo.data.dem`. Composite mask via boolean AND |
| **`run_eval_cslc_selfconsistency.py`** (SoCal, cached stack) | The first self-consistency eval; everything else in Phase 2 follows its structure | M | Uses cached SoCal SAFEs from DISP N.Am. eval. Processes 15 dates through `run_cslc`, forms 14 IFGs, masks, reports coherence + residual velocity. Writes `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` |
| **Mojave AOI selection + `run_eval_cslc_selfconsistency_mojave.py`** | Second US self-consistency point in a different terrain regime — required by BOOTSTRAP to exercise the methodology in more than one place | M | Primary AOI: Mojave Desert (Coso/Searles Valley). Fallback list (exhaust before surfacing as a blocker): Pahranagat Valley, Amargosa Valley, Hualapai Plateau. Selection rule: AOI must have OPERA CSLC reference coverage AND documented InSAR stability in published literature |
| **`run_eval_cslc_eu.py`** (Iberian Meseta) | EU CSLC has never run in v1.0; required to fill the matrix cell | M | Primary AOI: Iberian Meseta bedrock/sparse-vegetation burst north of Madrid. Fallbacks: Alentejo (interior Portugal), Massif Central. Three outputs: (a) OPERA CSLC amplitude sanity (r > 0.6, RMSE < 4 dB via existing `compare_cslc`); (b) self-consistency coherence > 0.7; (c) EGMS L2a stable-point residual < 5 mm/yr |
| **`docs/validation_methodology.md` — Cross-version phase section** | The BOOTSTRAP requires the cross-version phase findings from `CONCLUSIONS_CSLC_N_AM.md` §5 to be consolidated into the methodology doc; otherwise future users hit the same wall and fall back to the per-session conclusions file | S | New file. Section content: summary of cross-version isce3 phase-reference problem, diagnostic evidence (carrier removal, flattening — neither recovers coherence), why amplitude-only is the correct validation path, guidance for anyone tempted to try phase across versions. Audience: us-future-self and external contributors; depth: one page with evidence citations. Written in plain markdown — not Sphinx-rendered (no doc-site infrastructure in scope for v1.1) |

#### Phase 3 — DISP comparison adapter + self-consistency

| Feature | Why it's table-stakes | Complexity | Extends / depends on |
|---------|----------------------|------------|----------------------|
| **`subsideo.validation.compare_disp.prepare_for_reference(native_velocity, reference_grid) -> xr.DataArray`** | BOOTSTRAP §3.1 names this as the central Phase 3 infrastructure — it replaces the ad-hoc bilinear reprojection in `run_eval_disp.py` Stage 9 with a reusable, validation-only adapter | M | Extends `src/subsideo/validation/compare_disp.py`. <br>**Signature**: `prepare_for_reference(native_velocity: Path \| xr.DataArray, reference_grid: Path \| xr.DataArray \| ReferenceGridSpec) -> xr.DataArray`. <br>**`reference_grid` accepts three forms**: (a) a path to a GeoTIFF (read CRS + transform + shape via rasterio); (b) an `xr.DataArray` with CRS encoded via `rioxarray`; (c) a `ReferenceGridSpec(crs, transform, width, height)` dataclass for cases where no raster exists (e.g., EGMS L2a point cloud — in which case the function short-circuits to point-sampling and returns the sampled values as a 1-D DataArray indexed by PS ID). <br>**Multilooking choice** (critical; changes reported r/bias): simple box-filter averaging at the ratio of our native GSD (5×10 m) to reference GSD (30 m for OPERA DISP). Not Gaussian, not Lanczos. Justification: simple averaging is the method OPERA itself uses in multi-looking CSLC; it is the conservative choice that doesn't attribute bias/r changes to resampling kernel selection. **Gaussian-weighted or Lanczos are explicit anti-features** — see anti-features table below. <br>**Never writes back to the product**. Documented at module level as "validation-only infrastructure; production default remains 5×10 m native" |
| **DISP self-consistency gate** (product-quality) | Same methodology as Phase 2 CSLC self-consistency but on DISP outputs; required to have ANY product-quality number in 3:NAM and 3:EU cells | S | Reuses `subsideo.validation.selfconsistency` module from Phase 2. Inputs: our chain's CSLC stack (cached). Outputs: coherence > 0.7, residual < 5 mm/yr. Will FAIL under current PHASS unwrapper — that is the intended signal |
| **N.Am. DISP re-run from cached CSLCs** | Required to produce a clean baseline FAIL number (reference-agreement r and bias) against the current unwrapper — numbers the follow-up unwrapper milestone needs | S | `run_eval_disp.py` already has the full pipeline; change is running with the new comparison adapter (§3.1) and writing separate product-quality / reference-agreement numbers to the JSON sidecar. ~30 min compute from cache |
| **EU DISP re-run from cached CSLCs** | Same shape as N.Am.; fills 3:EU cell | S | `run_eval_disp_egms.py` + adapter. ~30 min compute |
| **DISP Unwrapper Selection scoping brief** | Phase 3 deliverable per BOOTSTRAP; the deliverable that unlocks the follow-up milestone | S | Single markdown file at `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md`. Audience: us-future-self + anyone picking up the follow-up milestone. Depth: one page. Content: restate the FAIL numbers from Phase 3 (planar ramps, r=0.04 N.Am. / r=0.32 EU), list the four candidate approaches (PHASS+deramping, SPURT native, tophu-SNAPHU tiled, 20×20 m fallback multilook), name a success criterion for each, flag compute cost tier (S/M/L). Not a plan — a brief |
| **Updated `CONCLUSIONS_DISP_N_AM.md` and `CONCLUSIONS_DISP_EGMS.md`** | Mirror structure used through v1.0; each must report product-quality AND reference-agreement numbers separately, per the BOOTSTRAP's "two are reported separately" rule | S | Editing existing files to add the product-quality section and link to the follow-up milestone brief |

#### Phase 4 — DIST OPERA v0.1 + EFFIS

| Feature | Why it's table-stakes | Complexity | Extends / depends on |
|---------|----------------------|------------|----------------------|
| **OPERA v0.1 sample fetch from CloudFront** (`d2pn8kiwq2w21t.cloudfront.net/...T11SLT_20250121T015030Z...zip`) | The N.Am. cell has no reference without this; ASF DAAC does not index the v0.1 sample | S | Uses `harness.download_reference_with_retry` from Phase 0.5 (plain-HTTPS auth backend). Interface: the eval script (`run_eval_dist.py` or a new `run_eval_dist_la.py`) calls the helper directly — **not** exposed as a new CLI subcommand. BOOTSTRAP does not ask for a CLI surface here, and adding one would be anti-feature scope creep for a single-URL fetch. Cached under `eval-dist/opera_reference/v0.1_T11SLT/` |
| **Config-drift gate** | BOOTSTRAP §4.1 requires: if OPERA v0.1 metadata shows materially different processing parameters vs dist-s1 2.0.13 defaults, SKIP comparison and report "N.Am. DIST deferred pending operational reference publication". Without this, a low F1 could be misread as a subsideo FAIL when it's really a config mismatch | M | New logic in `run_eval_dist.py`: after fetching v0.1 sample, parse its production metadata (HDF5 attributes / OPERA product-spec fields), compare against `dist_s1.__version__` defaults for `confirmation_count_threshold`, `pre_image_strategy`, `post_date_buffer_days`, and a small whitelist of other known parameters. <br>**UX**: <br>• Matrix cell: "deferred — config drift (see CONCLUSIONS)" instead of F1 number. <br>• Console log: explicit `WARN` block listing which parameters drifted and by how much. <br>• Exit code: 0 (deferral is not an error — it is a valid milestone outcome). <br>• The fetched v0.1 sample is preserved on disk regardless — do not delete on skip |
| **`run_eval_dist.py` LA T11SLT run** (MGRS tile retarget) | Existing `run_eval_dist.py` targets Park Fire / tile 10TFK — Phase 4.1 requires re-running on T11SLT with the matching track and post-date 2025-01-21 | S-M | Either parameterise the existing script via CLI flags (preferred; aligns with v1.0 pydantic-settings pattern) or fork to `run_eval_dist_la.py` (low-friction, mirrors how v1.0 forked EU from N.Am. evals). Expected compute ~30 min |
| **CMR-monitoring `make eval-dist-nam` probe** | BOOTSTRAP §4.2 requires a probe that queries CMR for `OPERA_L3_DIST-ALERT-S1_V1` on every invocation, so the day operational publication lands the eval automatically supersedes v0.1 | S | New helper `subsideo.validation.cmr_probe.check_dist_s1_operational() -> OperationalRefStatus`. Uses `earthaccess.search_datasets(keyword='OPERA DIST ALERT S1')`. <br>**Output if operational publication is found mid-milestone**: console prints an unmissable block ("⚡ OPERA DIST-S1 V1 NOW PUBLISHED — re-running against operational reference instead of v0.1"), fetches the first matching granule, and continues with the operational reference comparison. Falls through to v0.1 path if not found. Not blocking on milestone unless publication lands mid-milestone |
| **`run_eval_dist_eu_effis.py`** (EFFIS same-resolution cross-validation) | EU cell goes from precision-only (cross-sensor vs EMS VHR) to precision+recall (same-resolution vs EFFIS) — BOOTSTRAP requires this for EU DIST to strengthen beyond a single validator | M | New script parallel to `run_eval_dist_eu.py`. Reuses cached `eval-dist-eu/` subsideo output (no re-processing). <br>**EFFIS query input**: the user specifies AOI via **country + date range + event ID if known** (EFFIS API accepts `?country=PT&date_from=2024-09-15&date_to=2024-10-15`); eval script retains today's manual AOI config (bbox + date window) — no interactive selection. The script transforms these into an EFFIS burnt-area GeoJSON fetch, rasterises at 30 m to match DIST grid, compares via existing `compare_dist()` with **new recall-first criterion**: recall > 0.50, precision > 0.70 (not the EMS precision-first framing) |
| **2 additional EU DIST events** (Evros 2023, Romanian clear-cuts 2022) | Expansion from 1 to 3 events per BOOTSTRAP §4.4 | M | Each event is a new eval script or parameterised invocation of `run_eval_dist_eu.py`. Budget ~30 min compute + 1h write-up each. Aggregated into updated `CONCLUSIONS_DIST_EU.md` |
| **Updated `CONCLUSIONS_DIST_N_AM.md` and `CONCLUSIONS_DIST_EU.md`** | Required reporting per BOOTSTRAP | S | Mirror structure of v1.0 CONCLUSIONS files |

#### Phase 5 — DSWx N.Am. + EU recalibration

| Feature | Why it's table-stakes | Complexity | Extends / depends on |
|---------|----------------------|------------|----------------------|
| **`run_eval_dswx_nam.py`** | N.Am. DSWx has never run in v1.0; positive-control eval required to prove pipeline works at calibration-baseline region | M | Fork of `run_eval_dswx.py`. AOI: one of Lake Tahoe CA / Lake Pontchartrain LA (pick during execution based on cloud-free availability). Same 9-stage harness as EU |
| **AOI research artifact for EU fit set** | BOOTSTRAP §5.2 makes AOI research a first-class sub-task. Without an artifact capturing the per-AOI selection rationale, the recalibration is not reproducible — Balaton has to be held out as the test set, so the 6 fit-set AOIs must be defensibly chosen against the biome / JRC-quality / cloud-availability / no-failure-mode criteria | M | Deliverable: `notebooks/dswx_fitset_aoi_selection.ipynb` — a scripted query notebook that: queries CDSE STAC for S2 L2A cloud-free availability per candidate AOI in wet + dry seasons; queries JRC Monthly History raster noise metrics at each candidate; flags candidates with known failure modes (glacier / frozen lake / mountain-shadow / heavy turbid water) using OpenStreetMap + Copernicus Land Monitoring tags. <br>**Output**: a markdown table in the notebook showing per-candidate scores, the 6 selected, and reasoning for rejections. Commits the notebook AND a rendered markdown copy `docs/dswx_fitset_aoi_selection.md` for readers who don't want to open Jupyter |
| **Fit-set construction** (12 (AOI, scene) pairs × ~1.2 GB each ≈ 15 GB) | Inputs for the grid search | S | Uses existing `CDSEClient.download_safe`. Cached under `eval-dswx-fitset/` |
| **`scripts/recalibrate_dswe_thresholds.py`** (joint grid over WIGT × AWGT × PSWT2_MNDWI) | The actual recalibration runner | M | Joint grid: WIGT ∈ [0.08, 0.20] step 0.005 (25 values), AWGT ∈ [−0.1, +0.1] step 0.01 (21 values), PSWT2_MNDWI ∈ [−0.65, −0.35] step 0.02 (16 values) ≈ 8400 combinations × 12 (AOI, scene) pairs. Optimise mean F1 across fit set; hold Balaton out as test set. <br>**Output**: `scripts/recalibrate_dswe_thresholds_results.json` with best thresholds + full grid heatmap data + held-out Balaton F1 + fit-set mean F1 + per-AOI F1 breakdown |
| **Threshold update mechanism in `src/subsideo/products/dswx.py`** | The recalibrated constants must actually ship in the product code | S | Two constraints: <br>• **Constants live in module-level** (discoverable via ripgrep), with provenance comments (`# value from Phase 5.3 grid search, 2026-04-XX, recalibrate_dswe_thresholds_results.json`). <br>• **Overridable via `DSWxConfig`** (already a pydantic model in `subsideo.products.types`) so a user or a future recalibration run can override without editing source. <br>Existing v1.0 `DSWxConfig` already has constants as fields — Phase 5.3 just updates the defaults + adds the provenance comments + updates the reproducibility notebook pointer |
| **`notebooks/dswx_recalibration.ipynb`** (reproducibility notebook) | Someone must be able to re-derive the thresholds without re-reading `recalibrate_dswe_thresholds.py` | S | Loads the JSON results, plots the F1 surface, shows held-out Balaton F1, reproduces the frozen constants. Committed |
| **Re-run EU DSWx with recalibrated thresholds + honest FAIL report if F1 < 0.90** | F1 > 0.90 is the bar and BOOTSTRAP says it does NOT move. If recalibration lands at F1 ∈ [0.85, 0.90), the matrix reports FAIL with named DSWE ceiling / ML-replacement upgrade path | S | Re-run `run_eval_dswx.py` with new constants. <br>**Honest FAIL reporting format**: <br>• Matrix cell: "FAIL — F1 = 0.87 (DSWE ceiling; ML upgrade named in Future Work)". <br>• `CONCLUSIONS_DSWX.md`: explicit failure analysis section citing F1 ≈ 0.92 architectural ceiling literature. <br>• **No README "PASS badge" change** — README is not in scope; matrix is the status artifact |

#### Phase 6 — Results matrix + release readiness

| Feature | Why it's table-stakes | Complexity | Extends / depends on |
|---------|----------------------|------------|----------------------|
| **`results/matrix.md` with canonical column structure** | The entire milestone closure test is "`make eval-all` produces filled matrix" | S | Canonical columns: `Product | Region/AOI | Product-quality gate | Reference-agreement | Status | Notes`. Rows: RTC×(N.Am., 5 EU bursts), CSLC×(SoCal, Mojave, Meseta), DISP×(N.Am., EU), DIST×(LA v0.1 or deferred, Park Fire structural, EU Portugal, EU Greece, EU Romania, EU EFFIS), DSWx×(N.Am. positive control, EU Balaton held-out). Status column uses the three BOOTSTRAP verdicts: `PASS` / `FAIL (named upgrade: ...)` / `deferred (unblock when: ...)` |
| **`docs/validation_methodology.md`** | Required by BOOTSTRAP §6.2; consolidates four methodological findings + the product-quality vs reference-agreement distinction | M | New file. Outline: (1) Cross-version phase comparison is impossible across isce3 majors; (2) Cross-sensor comparison requires precision-first metric interpretation; (3) OPERA frame selection must match exact UTC hour AND spatial footprint; (4) DSWE-family F1 ceiling ≈ 0.92 is architectural, not tuning. Plus: the split between reference-agreement (sanity check) and product-quality (gate) criteria, with examples drawn from each phase. Estimated length: 8–12 pages markdown (~3000–5000 words). Audience: external contributors + us-future-self + anyone reviewing the library for adoption. Depth: full methodological rationale with evidence pointers, not tutorial-level how-to |
| **Pre-release audit on TrueNAS Linux** | Milestone success criterion #1 is "fresh clone on clean machine succeeds" — it's not met if we only tested on M3 Max | S | TrueNAS GPU dev container (Linux, fork start method). **In-scope platform-portability hazards to verify**: (a) Linux-fork vs macOS-fork start-method parity (should be a no-op on Linux since we only forced fork on macOS); (b) conda-forge isce3 arm64-macOS vs Linux-x86_64 output-byte-equivalence on a reference burst; (c) the `~/.cdsapirc` / `EARTHDATA_*` credential discovery path works identically under `bash` on Linux vs `zsh` on macOS; (d) ripgrep `rg` isn't required by tooling; (e) `make` vs `gmake` — Makefile is GNU-compatible; (f) line endings / CR-LF do not sneak into any eval script. **Not in scope**: Windows, WSL2-detailed testing, NISAR, any tile caches larger than N.Am. SoCal + EU Bologna (already the milestone's compute budget). |
| **Audit report artifact** | Without an artifact the audit is invisible | S | `.planning/milestones/v1.1-research/PRERELEASE_AUDIT_TRUENAS.md` with timestamped results: cold-env `make eval-all` duration, warm-env duration, diff-to-matrix vs M3 Max run |

---

### Differentiators (raise the bar; optional but recommended)

These are features BOOTSTRAP_V1.1 names or implies but are not strict milestone-closure blockers — they make the milestone better but the milestone can close without them.

| Feature | Value proposition | Complexity | Extends / depends on |
|---------|-------------------|------------|----------------------|
| **Coloured + JSON dual output for `credential_preflight`** | Humans get a readable status screen; CI pipelines get machine-readable status. BOOTSTRAP is silent on dual output, but it generalises the feature in the direction v1.2 CI will need | S | Feature of `harness.credential_preflight` — adds ~30 LOC over the minimum |
| **`make eval-all` summary line at the end** ("5/5 PASS across 12 AOIs in 4h17m") | One-glance status without opening the matrix file | S | End of `results/matrix.md` generation; printed to stdout |
| **Per-eval `metrics.json` sidecar schema (versioned)** | Machine-readable consumers (future CI, external dashboards) can parse results without regex over the markdown matrix | S | `src/subsideo/validation/_schema.py` with a pydantic `EvalMetricsV1` model; every `run_eval_*.py` writes one. Opens the door to a dashboard in v1.2 without locking us into one now |
| **Chained `prior_dist_s1_product` run** (BOOTSTRAP §4.5) | If Phase 0.4 resolves the hang, one chained Sep 28 → Oct 10 → Nov 15 run demonstrates the alert-promotion flow (provisional → confirmed) the operational OPERA DIST-S1 product will use | M | Parallel run in `run_eval_dist_eu.py`. Anti-requires nothing; if still hangs, file upstream and punt. Explicitly *not* gating on milestone closure |
| **Watchdog telemetry log** (from `_mp.py`) | When the watchdog triggers, dumping live-process state (py-spy dump, if available) accelerates diagnosis | S | Optional py-spy dump on abort; falls back to `faulthandler.dump_traceback_later` from stdlib |
| **Bursts-of-opportunity auto-retry** in `download_reference_with_retry` | If a CDSE 503 lingers, we back off and then prefer a different burst date if it exists — useful for CDSE evenings-UTC brownouts that recur | M | Beyond the BOOTSTRAP spec; optional feature flag. Skip unless time allows |
| **`results/matrix.md` includes trendline vs previous run** (diff column) | Seeing "r: 0.043 → 0.039 (↑)" highlights regressions in DISP-follow-up-milestone contributions | S | Compares against `results/matrix.previous.md`. Differentiator because the diff adds value but missing doesn't fail the milestone |
| **Burst-database-backed AOI catalogue** for selection | Instead of hand-picking Alpine / Meseta / Balaton, query the EU burst DB for "bursts with WorldCover coverage + EGMS L2a coverage + known stable literature" | M | Extends `subsideo.burst.db` with a catalogue query API. Attractive but Phase-scope creep; better as v2 |

---

### Anti-features (explicitly excluded by BOOTSTRAP_V1.1)

These are features that would be tempting to add but are explicitly out of scope. Calling them out prevents drift.

| Anti-feature | Why requested | Why problematic | BOOTSTRAP reference |
|--------------|---------------|-----------------|---------------------|
| **Picking a production DISP unwrapper within this milestone** | "We've seen PHASS FAIL — surely we should fix it now?" | Unwrapper research is a genuinely multi-candidate workstream with distinct compute/failure profiles. Committing to one in Phase 3 short-circuits the research. BOOTSTRAP spins it out to a dedicated follow-up milestone with the brief as the handoff | §3 — "This phase explicitly does NOT pick a production unwrapper" |
| **ML-based replacements for DSWE threshold algorithms** | "If DSWE F1 ceiling is 0.92 architectural, random forest will clear it" | Scope creep — moves from validation milestone to new algorithm class. Named as the upgrade path for post-v1.1 | §5, "Out of scope" + Future Work |
| **Relaxing DSWx F1 > 0.90 bar during recalibration** | "If we land at 0.89 and move the bar to 0.85, we PASS" | Target captured. BOOTSTRAP is explicit: "F1 > 0.90 is the bar. It does not move." An honest FAIL with named upgrade path is more useful than a moved goalpost | §5.5 |
| **Multi-burst mosaicking / cross-burst consistency checks** | "Real users will run on multi-burst AOIs" | Deferred to v2 global milestone — EU/N.Am. parity first | "Explicitly out of scope" |
| **New OPERA product classes (DSWx-S1, DSWx-HLS, etc.)** | "While we're in here, add DSWx-S1" | Opens sensor-specific burst geometry and validator surfaces; dilutes focus | "Explicitly out of scope" |
| **Global expansion beyond N.Am. + EU** | "Why not Africa / Australia / tropics?" | Fit-set construction, reference data availability, burst DB coverage all need global reboot — v2 milestone | "Explicitly out of scope" |
| **Gaussian-weighted or Lanczos multilooking in `prepare_for_reference`** | "Better resampling kernel → higher reported r" | Higher reported r from kernel choice is not a real product improvement — it's kernel-driven artifact. Simple averaging is what OPERA uses in its own multilook; divergence from that moves us away from reproducible reference-agreement | BOOTSTRAP §3.1 — "validation-only infrastructure; never writes back to the product"; implicitly, the kernel choice shouldn't inflate reference-agreement beyond what OPERA's own tooling would show |
| **Writing comparison-adapter output back to the product** | "If we're multilooking for validation, cache the multilooked product for downstream consumers" | Couples validation to product. BOOTSTRAP §3 explicitly requires the adapter to be validation-only. Native 5×10 m stays the production default | §3.1 — "Never writes back to the product" |
| **A new `subsideo validate-dist-la` CLI subcommand** | "Surface the v0.1 comparison as a CLI" | Scope creep. BOOTSTRAP calls for the fetch via the harness helper, run via an eval script — not a new CLI verb | §4.1 is silent on CLI; adding one is beyond BOOTSTRAP |
| **README PASS/FAIL badge** | "Quick status for casual visitors" | Moving target; requires CI to refresh; out of scope for this milestone. Matrix is the canonical status artifact | §6 is silent on README — canonical artifact is `results/matrix.md` |
| **Re-running RTC EU with tighter criteria because the N.Am. number was 0.045 dB** | "Our N.Am. RMSE was 0.045 — let's tighten the EU criterion to 0.1" | Criterion-by-score drift. Pass criteria don't move based on the reference's own score — foundational rule of BOOTSTRAP's "metric vs target" framing | Milestone preamble |
| **Tightening CSLC residual velocity bar from 5 mm/yr during Phase 2** | "SoCal stack was 6 months; if we get 2 mm/yr residual, tighten to 2" | The 5 mm/yr bar is set for a 6-month stack; tightening triggers on stack length not residual score. Moved to Future Work | §2 "What this phase validates" |
| **Interactive AOI picker UI for Phase 5 fit set** | "A notebook widget to click AOIs on a map" | Notebook + scripted query is sufficient; widgets add maintenance surface | §5.2 calls for scripted query + markdown table |
| **New `validate_dist_product` OPERA-spec full-metadata validation** | "While in here, tighten DIST product validation" | Named in Future Work as a post-milestone upgrade; not milestone-blocking | Future work DIST bullet |
| **Medium post / external publication** | "Share the v1.1 results externally" | BOOTSTRAP decision log item #4: "no publication deliverable in this milestone" | Decisions recorded during milestone refinement, item 4 |
| **Docker / containerised release** | "Package v1.1 for reproducibility" | Two-layer conda+pip install is not trivially Dockerisable; `conda-lock` is a differentiator for v1.2 if needed | Out of scope implicitly (never mentioned) |

---

## Feature Dependencies

```
Phase 0 (environment + harness)
├── 0.1 numpy pin ────────────────────┬── required by Phase 2 (CSLC evals can't patch numpy 2.x)
├── 0.2 tophu ──────────────────────── required by Phase 3 (DISP re-runs)
├── 0.3 _cog.py ──────────────────────┬── required by Phase 5 (DSWx COG writing)
│                                    └── required by Phase 1 (RTC COG writing)
├── 0.4 _mp.py ───────────────────────┬── required by Phase 4 (DIST LA run on macOS)
│                                    └── required by Phase 3 EU re-run (tophu internals)
├── 0.5 harness ──────────────────────┬── required by every run_eval_*.py refactor
│    ├── select_opera_frame_by_utc_hour ── used by Phase 1 (RTC EU), Phase 2 (CSLC EU), Phase 3 (DISP EU)
│    ├── download_reference_with_retry ─── used by Phase 4 (CloudFront v0.1), Phase 4 (CMR probe)
│    ├── ensure_resume_safe ─────────────── used by every eval script
│    └── credential_preflight ───────────── used by Makefile targets
├── 0.6 programmatic DEM bounds ─────── required by Phase 1 (EU bursts), Phase 2 (Meseta / Mojave)
└── 0.7 Makefile ──────────────────────┬── required by Phase 6 (make eval-all closure test)
                                      └── enables Phase 0.5 harness adoption verification

Phase 1 (RTC EU) ── independent after Phase 0
Phase 2 (CSLC self-consist + EU) ── depends on 0.1 numpy pin
    └── stable-terrain mask module ── reused by Phase 3 DISP self-consistency
Phase 3 (DISP) ── depends on 0.2 tophu + 0.4 _mp + Phase 2 stable-terrain mask module
    └── prepare_for_reference adapter ── reused by matrix writer for consistent reporting grid
Phase 4 (DIST) ── depends on 0.4 _mp + 0.5 harness (CloudFront retry path)
    └── config-drift gate ── unique to Phase 4, no downstream reuse
Phase 5 (DSWx) ── depends on 0.3 _cog + 0.5 harness
    └── fit-set AOI catalogue ── could become v2 input but not milestone dependency
Phase 6 (matrix + release) ── depends on all Phase 1–5 outputs
    └── audit report ── terminal artifact, no downstream reuse within milestone
```

### Dependency notes

- **Phase 0 must land first.** Every subsequent phase calls at least one Phase 0 helper. This is why BOOTSTRAP §Dependencies explicitly puts Phase 0 as the root of the DAG.
- **Phase 2 stable-terrain mask module is reused by Phase 3.** The exact same `stable_terrain.py` that builds the WorldCover + slope composite for CSLC self-consistency is re-used by DISP self-consistency. If either phase slips, the other inherits the slip. Recommend: implement stable_terrain.py as Phase 0.5.5 sub-step, not as Phase 2 code.
- **Phase 5 is the largest single phase (5–7 days)** and is the single biggest schedule risk per the BOOTSTRAP risk register. Fit-set quality caps F1 regardless of grid-search quality — so AOI-research time (3–4 days) must land before compute commits.
- **Phase 4 has a soft external dependency** on OPERA operational DIST-S1 publication timing. If operational publication lands mid-milestone, §4.2 CMR probe handles the swap automatically — not a blocker, but could shift the 4:N.Am. cell from "PASS vs v0.1" to "PASS vs operational".
- **Phase 6 is the only phase that must run last.** Phases 1–5 parallelise post-Phase-0 for a two-developer split; single-developer stays serial.

---

## MVP Definition (for v1.1 milestone)

### Launch with (milestone closure-required)

All in the table-stakes sections above. Concretely, the minimum to close the milestone:

- [ ] Phase 0.1–0.7: every item (5 modules, 1 Makefile, 1 regression test file)
- [ ] Phase 1: 3 of 5 EU RTC bursts PASS (BOOTSTRAP says 3–5; 3 is the floor)
- [ ] Phase 2: SoCal + Mojave + Meseta self-consistency runs, all three with coherence + residual numbers (PASS or FAIL)
- [ ] Phase 3: comparison adapter shipped; both continents re-run from cached CSLCs; follow-up brief written
- [ ] Phase 4: LA T11SLT result (either PASS/FAIL or deferred with config-drift gate); EFFIS EU result; at least one of the two additional EU events
- [ ] Phase 5: N.Am. positive control eval; recalibrated thresholds; EU re-run with new thresholds (PASS or FAIL)
- [ ] Phase 6: `results/matrix.md`, `docs/validation_methodology.md`, TrueNAS audit

### Add after validation (v1.2)

- [ ] Machine-readable metrics JSON dashboard (builds on `metrics.json` sidecars)
- [ ] DISP Unwrapper Selection follow-up milestone (scoped as Phase 3 deliverable)
- [ ] CR absolute radiometric accuracy validation for RTC (Future Work)
- [ ] GNSS-residual comparison for CSLC via Nevada Geodetic Laboratory (Future Work)
- [ ] Remaining 2 EU DIST events if only 1 landed in v1.1
- [ ] `conda-lock` pinning for reproducible environments

### Future consideration (v2+)

- [ ] ML-replacement algorithm path for DSWx (DSWE F1 ceiling upgrade)
- [ ] Global recalibration of DSWx fit-set (beyond EU)
- [ ] Multi-burst mosaicking
- [ ] Burst DB globalisation
- [ ] Tide gauge / GNSS network validation baselines for regions without OPERA/EGMS equivalents

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Phase 0 harness module | HIGH | M-L | P1 |
| Phase 0 numpy pin + patch removal | HIGH | S | P1 |
| Phase 0 Makefile | HIGH | S | P1 |
| Phase 0 `_cog.py` | HIGH | S | P1 |
| Phase 0 `_mp.py` | HIGH | M | P1 |
| Phase 0 credential preflight | MEDIUM | S | P1 |
| Phase 0 matrix writer | HIGH | S | P1 |
| Phase 1 RTC EU eval (3–5 bursts) | HIGH | M | P1 |
| Phase 2 stable-terrain mask module | HIGH | M | P1 |
| Phase 2 CSLC self-consistency (SoCal) | HIGH | M | P1 |
| Phase 2 CSLC Mojave | MEDIUM | M | P1 |
| Phase 2 CSLC EU Meseta | HIGH | M | P1 |
| Phase 2 cross-version phase methodology doc | MEDIUM | S | P1 |
| Phase 3 comparison adapter | HIGH | M | P1 |
| Phase 3 DISP self-consistency gate | HIGH | S | P1 |
| Phase 3 N.Am. + EU re-runs | HIGH | S (from cache) | P1 |
| Phase 3 unwrapper-selection brief | MEDIUM | S | P1 |
| Phase 4 LA v0.1 fetch + run | HIGH | M | P1 |
| Phase 4 config-drift gate | HIGH | M | P1 |
| Phase 4 CMR probe | MEDIUM | S | P1 |
| Phase 4 EFFIS EU | HIGH | M | P1 |
| Phase 4 2 additional EU events | MEDIUM | M | P1 (soft — one minimum) |
| Phase 4 chained DIST run | LOW | M | P2 |
| Phase 5 N.Am. positive control | HIGH | M | P1 |
| Phase 5 AOI research notebook | HIGH | M | P1 |
| Phase 5 fit-set construction | HIGH | S | P1 |
| Phase 5 grid search | HIGH | M | P1 |
| Phase 5 threshold update + provenance | HIGH | S | P1 |
| Phase 5 reproducibility notebook | MEDIUM | S | P1 |
| Phase 5 EU re-run with honest FAIL | HIGH | S | P1 |
| Phase 6 `results/matrix.md` | HIGH | S | P1 |
| Phase 6 `docs/validation_methodology.md` | HIGH | M | P1 |
| Phase 6 TrueNAS audit | HIGH | S | P1 |
| Differentiator: coloured+JSON preflight | MEDIUM | S | P2 |
| Differentiator: versioned sidecar schema | MEDIUM | S | P2 |
| Differentiator: matrix trendline diff | LOW | S | P3 |
| Differentiator: burst-DB-backed AOI catalogue | LOW | M | P3 |

**Priority key:**
- P1: Required for milestone closure (table-stakes)
- P2: Differentiator — recommended if time allows
- P3: Nice to have — defer to v1.2 unless trivially cheap

---

## Cross-reference to v1.0 code being extended

| v1.1 feature | Existing v1.0 code it extends |
|--------------|------------------------------|
| `harness.select_opera_frame_by_utc_hour` | New; ad-hoc logic lives inline in `run_eval.py` (filename prefix match) |
| `harness.download_reference_with_retry` | Generalises: `CDSEClient` retry in `src/subsideo/data/cdse.py`, `earthaccess.download` wrappers in every `run_eval_*.py` |
| `harness.ensure_resume_safe` | Generalises: per-script `if not any(dir.glob('*.tif')):` patterns in `run_eval.py`, `run_eval_dist.py` etc |
| `harness.credential_preflight` | Generalises: the preflight `for key in (...):` blocks in `run_eval_dswx.py`, `run_eval_disp_egms.py` |
| `subsideo._cog` | Replaces direct imports in `src/subsideo/products/{rtc,dswx,dist}.py` |
| `subsideo._mp` | New; injected into `src/subsideo/products/{rtc,cslc,disp,dswx,dist}.py::run_*()` entry points |
| `subsideo.validation.selfconsistency` | New module; no v1.0 predecessor |
| `subsideo.validation.stable_terrain` | New module; no v1.0 predecessor |
| `subsideo.validation.compare_disp.prepare_for_reference` | Extends existing `src/subsideo/validation/compare_disp.py`; replaces bilinear reprojection inside `compare_disp()` itself + Stage 9 of `run_eval_disp.py` |
| `subsideo.validation.matrix` | New module; no v1.0 predecessor |
| `subsideo.validation.cmr_probe` | New module; no v1.0 predecessor (uses existing `earthaccess` dep) |
| `subsideo.burst.bbox` helper | Extends existing `src/subsideo/burst/` package which already has db/tiling modules |
| DSWE threshold constants update | Modifies `src/subsideo/products/dswx.py` + existing `DSWxConfig` in `src/subsideo/products/types.py` |
| `eval_{product}_{region}` scripts | Each is a new file parallel to the existing seven `run_eval_*.py` scripts in the repo root |

---

## Sources

- `/Volumes/Geospatial/Geospatial/subsideo/BOOTSTRAP_V1.1.md` — primary source for every feature in this document
- `/Volumes/Geospatial/Geospatial/subsideo/.planning/PROJECT.md` — milestone framing, pass criteria, Out-of-Scope
- `/Volumes/Geospatial/Geospatial/subsideo/src/subsideo/validation/compare_disp.py` — existing `compare_disp()` and `compare_disp_egms_l2a()` that Phase 3.1 extends
- `/Volumes/Geospatial/Geospatial/subsideo/src/subsideo/validation/compare_rtc.py` — unchanged by v1.1; consumed by Phase 1
- `/Volumes/Geospatial/Geospatial/subsideo/src/subsideo/validation/compare_cslc.py` — unchanged by v1.1; consumed by Phase 2 amplitude sanity check
- `/Volumes/Geospatial/Geospatial/subsideo/src/subsideo/validation/compare_dist.py` — unchanged by v1.1; consumed by Phase 4
- `/Volumes/Geospatial/Geospatial/subsideo/run_eval.py`, `run_eval_cslc.py`, `run_eval_disp.py`, `run_eval_disp_egms.py`, `run_eval_dist.py`, `run_eval_dist_eu.py`, `run_eval_dswx.py` — existing per-eval scripts that will be refactored to use the Phase 0.5 harness
- `/Volumes/Geospatial/Geospatial/subsideo/.planning/milestones/v1.0-research/FEATURES.md` — v1.0 features context (not re-researched per BOOTSTRAP instruction)
- [ESA WorldCover v200 (2021) — S3 public-read bucket](https://esa-worldcover.org/en/data-access) — class 60 for stable-terrain mask input (Phase 2)
- [EFFIS (European Forest Fire Information System) API](https://effis.jrc.ec.europa.eu/applications/data-request-form) — burnt-area product for Phase 4.3
- [OPERA DIST-S1 v0.1 sample on CloudFront](https://d2pn8kiwq2w21t.cloudfront.net/) — referenced in BOOTSTRAP §4.1 for the direct-download path

---

*Feature research for: subsideo v1.1 N.Am./EU Validation Parity & Scientific PASS milestone (validation/eval features only)*
*Researched: 2026-04-20*
