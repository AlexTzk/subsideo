# Phase 5: DIST-S1 OPERA v0.1 + EFFIS EU - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 5 validates subsideo's DIST-S1 pipeline against two reference families on two regions, plus a non-blocking differentiator and an auto-supersede probe — closing the 5/5 product validation matrix on the DIST row.

- **DIST-N.Am.-T11SLT** (LA fires, post-date 2025-01-21, MGRS T11SLT): re-run subsideo dist-s1 against OPERA's pre-operational v0.1 sample fetched from CloudFront. The cell PASSES, FAILS, or DEFERS based on a config-drift gate that compares the v0.1 sample's 7 key processing parameters against dist-s1 2.0.14 defaults. When the gate passes, F1 / precision / recall / accuracy are computed with block-bootstrap 95% CI. **A CMR probe runs first** — if operational `OPERA_L3_DIST-ALERT-S1_V1` has published, it transparently supersedes v0.1 with no manual intervention.
- **DIST-EU-3-events** (Aveiro/Viseu Portuguese wildfires 2024 + Evros Greece EMSR649 2023 + Romania forest clear-cuts 2022): re-run subsideo dist-s1 against EFFIS WFS burnt-area perimeters as same-resolution optical reference. Aggregate F1 across 3 events. Aveiro additionally runs a chained `prior_dist_s1_product` retry (Sep 28 → Oct 10 → Nov 15) as a non-blocking differentiator.

Plus four artefact deliverables:

- **CMR auto-supersede stage** in `run_eval_dist.py` (Stage 0): queries CMR for operational `OPERA_L3_DIST-ALERT-S1_V1` covering T11SLT 2025-01-21; on hit, fetches via `earthaccess` and uses as reference; on miss, falls back to v0.1 CloudFront sample. `metrics.json` carries `reference_source: Literal['operational_v1','v0.1_cloudfront','none']`.
- **Config-drift gate** with 7 OPERA v0.1 parameters extracted from the sample HDF5 (extraction strategy + key list locked in plan-phase from sample evidence). Any single-key difference triggers `cell_status='deferred'`. `metrics.json` carries `config_drift: {status, per_key_table, message}`.
- **`validation/bootstrap.py`** new module with `block_bootstrap_ci(predictions, references, metric_fn, block_size_m=1000, n_bootstrap=500, ci_level=0.95)` — pure-numpy spatial bootstrap. Drops partial blocks at MGRS tile edges; reports `n_blocks_kept` + `n_blocks_dropped` for transparency.
- **EFFIS WFS retry policy** added as a new branch in `harness.RETRY_POLICY` (5 sources now: CDSE / Earthdata / CloudFront / EGMS / EFFIS). `download_reference_with_retry` accepts `source='effis'` for `owslib.wfs.WebFeatureService` calls. Plan-phase commits the exact EFFIS endpoint URL + layer name from probe.

**Not this phase:**
- Tightening DIST F1 > 0.80 / accuracy > 0.85 thresholds (M1 anti-target-creep; per ROADMAP DIST-03 explicit "without tightening toward v0.1's own score").
- Operational monitoring chain with provisional→confirmed alert promotion (DIST-V2-01 deferred).
- Upstream PR for `post_date_buffer_days` default change in dist-s1 (DIST-V2-02 deferred to v2).
- Full OPERA product-spec metadata validation through `dist_s1.data_models.output_models.DistS1ProductDirectory` (DIST-V2-03 deferred).
- Re-running against operational OPERA DIST-S1 as a planned activity — Phase 5 ships the auto-supersede probe; if operational publishes mid-milestone the probe handles it; otherwise re-run is in v2 (DIST-V2-04, but the probe makes it intervention-free if it lands first).
- New criteria.py entries beyond `INVESTIGATION_TRIGGER` for single-tile F1 variance flagging (Phase 2 D-13/D-14 pattern; non-gate, narrative-only).
- Adding any new product-quality CALIBRATING gates — DIST stays binary-classification reference-agreement only (no self-consistency analogue is meaningful for a disturbance product).
- Modifying `products/dist.py` or the `dist_s1.run_dist_s1_workflow` chain — Phase 5 is validation-side only.
- Picking up Park Fire as a matrix cell — Park Fire stays as a non-matrix artifact at `eval-dist-park-fire/` (renamed from `eval-dist/`).

Phase 5 covers the 7 requirements mapped to it: **DIST-01** (CloudFront direct-download with retry + cached under eval-dist/opera_reference/v0.1_T11SLT/), **DIST-02** (config-drift gate + 7 keys + skip-and-defer semantics), **DIST-03** (F1/precision/recall/accuracy + block-bootstrap 95% CI), **DIST-04** (CMR probe auto-supersede), **DIST-05** (EFFIS owslib WFS cross-validation, precision > 0.70 AND recall > 0.50), **DIST-06** (3-event aggregate EU coverage), **DIST-07** (chained `prior_dist_s1_product` retry, non-blocking differentiator).

</domain>

<decisions>
## Implementation Decisions

### Config-drift gate mechanics (DIST-02, PITFALLS P4.1)

- **D-01: Plan-phase probes the OPERA v0.1 sample first; commits extraction strategy with evidence.** Plan-phase fetches the v0.1 HDF5 sample (or pulls from cache if Phase 1 ENV-06 harness already cached it) and runs `h5dump -A` (or h5py introspection) to surface where the 7 keys actually live: structured HDF5 attributes at `/science/SENTINEL1/identification/processingInformation/productionParameters`, JSON-string-encoded attributes, sidecar XML, partially missing, etc. Plan-phase then commits the extraction strategy + key paths with a "config drift extraction probe report" sub-section in PLAN.md. PITFALLS P4.1 explicitly warns this is unknowable from the spec alone — "pre-operational products often have incomplete metadata". The chosen approach mirrors Phase 4 D-Claude's-Discretion pattern (defer specifics that depend on artefact evidence to plan-phase).

- **D-02: Plan-phase locks the full 7-key list with evidence from dist-s1 2.0.14 source + v0.1 sample.** DIST-02 names 5 keys explicitly (confirmation-count threshold, pre-image strategy, post-date buffer, baseline window length, despeckle settings) + "2 further". Plan-phase researches `dist-s1 2.0.14` Python source (`dist_s1/dist_processing.py` defaults dict) and the v0.1 sample's metadata to surface the actual 2-further-keys with evidence. Candidates from PITFALLS P4.1 cite: `post_date_buffer_days` (default 1, OPERA v0.1 may use 5), `baseline_window_epochs`, `despeckle_window_pixels`, `confirmation_count_M_of_N` (e.g. "2 of 3" vs "3 of 5"), `pre_image_strategy_literal` (e.g. "rolling_median" vs "fixed_baseline"), `soil_moisture_filter_on_off`, `percolation_threshold`. Plan-phase commits the exact 7 with citations.

- **D-03: Any difference → defer (strictest threshold).** When ANY of the 7 keys differs between the OPERA v0.1 sample and dist-s1 2.0.14 defaults — even by one numerical step — the matrix cell renders `'deferred pending operational reference publication'`. No per-key tolerance bands; no algorithmic-structure-only filter. Reasoning: (i) M1 anti-target-creep — comparing against a pre-operational reference whose config silently differs is exactly the "validators not quality ceilings" failure mode the milestone discipline rejects. (ii) The matrix-cell semantics are clean: PASS / FAIL / DEFERRED. Per-key tolerances introduce interpretation pressure that downstream readers cannot audit. (iii) When operational publishes (DIST-04 auto-supersede), the gate becomes irrelevant — the strictness only matters during the v0.1 window. Per Phase 2 D-15 investigation discipline ("automation flags, doesn't replace narrative") the auto-deferral writes the per-key delta table into `metrics.json` so a human reader can independently disagree in CONCLUSIONS prose.

- **D-04: Config-drift extraction code module location — plan-phase decides.** Two reasonable homes: extend `compare_dist.py` (where the comparison plumbing lives in v1.0) with a `extract_v01_config_drift(opera_sample_path) -> DriftReport` helper, OR create `validation/config_drift.py` as a dedicated module (cleaner separation; allows future reuse if v1.2+ adds config-drift gates for other products). Plan-phase chooses based on extraction code complexity discovered in D-01 probe. If extraction is <50 LOC, extend `compare_dist.py`; if larger, new module. `DriftReport` Pydantic v2 model lives in `matrix_schema.py` (additive; Phase 4 D-11 schema extension pattern).

### N.Am. AOI disposition + block-bootstrap CI (DIST-01, DIST-03)

- **D-05: T11SLT replaces 10TFK in the dist:nam matrix cell; Park Fire kept as separate non-matrix artifact.** Phase 5 work resolves to MGRS T11SLT (LA fires, post-date 2025-01-21) per DIST-01. The v1.0 Park Fire run (MGRS 10TFK, Tehama/Butte county California 2024) was a "structurally complete, no comparison" outcome — OPERA reference wasn't published, so no F1 was computed; numbers don't enter the matrix. **Action:** rename existing `eval-dist/` → `eval-dist-park-fire/` (preserving v1.0 cache + run.log + opera_reference/ contents intact); new `eval-dist/` directory (cache_dir per `matrix_manifest.yml`) is created fresh for T11SLT. Park Fire CONCLUSIONS_DIST_N_AM.md preserved as v1.0 baseline preamble at the top of the rewritten v1.1 CONCLUSIONS_DIST_N_AM.md (Phase 4 D-13 pattern — keeps the discovery audit trail readable). No manifest entry for Park Fire (it's not a matrix cell); the renamed directory is a historical artifact only. CONCLUSIONS_DIST_N_AM.md gets v1.1 sections appended with T11SLT numbers; v1.0 Park Fire content moves to a "v1.0 baseline" leading section.

- **D-06: New `validation/bootstrap.py` module hosts `block_bootstrap_ci`.** Clean separation from `metrics.py` (which carries point-estimate F1 / precision / recall / accuracy / bias / rmse / correlation). Bootstrap is a methodology helper, not a metric. New module signature: `block_bootstrap_ci(predictions: np.ndarray, references: np.ndarray, metric_fn: Callable[[np.ndarray, np.ndarray], float], block_size_m: int = 1000, pixel_size_m: int = 30, n_bootstrap: int = 500, ci_level: float = 0.95, rng_seed: int | None = 0) -> BootstrapResult`. Returns `BootstrapResult` dataclass with `point_estimate`, `ci_lower`, `ci_upper`, `n_blocks_kept`, `n_blocks_dropped`, `n_bootstrap`, `ci_level`, `rng_seed`. Rationale for new module over `metrics.py`: (i) bootstrap is reusable for non-F1 metrics (bias CI in DSWx Phase 6 if needed); (ii) keeps `metrics.py` as a clean "metric primitives" module; (iii) module-level constants (`DEFAULT_BLOCK_SIZE_M = 1000`, `DEFAULT_N_BOOTSTRAP = 500`, `DEFAULT_RNG_SEED = 0`) are auditable per Phase 1 D-11 convention.

- **D-07: F1 + ci_lower + ci_upper (95%) per metric in `metrics.json`.** Schema: `reference_agreement.metrics: {f1: {point: 0.823, ci_lower: 0.781, ci_upper: 0.860}, precision: {...}, recall: {...}, accuracy: {...}}` (4 metrics × 3 fields = 12 numerical fields total under reference_agreement.metrics). Matches ROADMAP DIST-03 explicit phrasing "block-bootstrap 95% CI" + "matrix cell shows point estimate AND CI". Symmetric bounds NOT assumed (block-bootstrap distributions can be skewed for binary-classification F1 near boundary). Matrix cell renders as `f1=0.823 [0.781, 0.860] PASS` (when point > 0.80; CI displayed for transparency). Bootstrap config sub-block at `reference_agreement.bootstrap_config: {block_size_m: 1000, n_bootstrap: 500, ci_level: 0.95, n_blocks_kept: 11881, n_blocks_dropped: 436, rng_seed: 0}` for reproducibility audit.

- **D-08: Drop partial blocks at MGRS tile edges — n_kept + n_dropped reported.** MGRS T11SLT is 109.8 × 109.8 km. At 1km blocks: 109 × 109 = 11881 full 1km blocks fit fully inside; ~436 partial blocks at the east + south edges contain only fraction-of-1km worth of pixels. Bootstrap pool is the 11881 full blocks; sampled with replacement B=500 times. Information loss is bounded (~3.7% of tile pixels live in edge blocks at 30m resolution = ~436 × ~mean-30-pixels = ~13k pixels of ~12.1M total). `metrics.json bootstrap_config.n_blocks_kept` + `n_blocks_dropped` disclose the choice. Rationale: standard spatial-bootstrap practice (Hall 1985 stationary-block bootstrap; Lahiri 2003); transparent; defensible; mechanically simpler than weighted partial-block resampling. Block layout: anchored to tile origin (UTM SW corner); blocks are non-overlapping `(block_row, block_col)` indices into a `(109, 109)` grid. Bootstrap resamples block indices with replacement; for each bootstrap iteration, the metric is computed over the union of resampled blocks' pixels.

- **D-09: BootstrapResult deterministic via fixed `rng_seed=0` default.** Reproducible across re-runs by default. Plan-phase commits whether to expose `rng_seed` as an eval-script module-level constant (Phase 1 D-11 + Phase 4 D-04 pattern) OR keep it as a `block_bootstrap_ci` keyword default. Random seed visible in `metrics.json bootstrap_config.rng_seed` regardless. Switching seed across re-runs is a PR-level action (visible in git diff) — never an env var or CLI flag.

### EU events orchestration + chained retry (DIST-06, DIST-07)

- **D-10: Single aggregate `dist:eu` matrix cell with per_event sub-results.** Phase 2 RTC-EU per-burst pattern (Phase 2 D-09/D-10) — single `eval-dist_eu/metrics.json` carries top-level aggregates (`per_event_count`, `pass_count`, `worst_f1`, `worst_event_id`, `any_investigation_required`) + nested `per_event: list[DistEUEventMetrics]`. Each `DistEUEventMetrics` has `event_id` (Literal['aveiro','evros','romania']), `f1` + `precision` + `recall` + `accuracy` (each with `point`/`ci_lower`/`ci_upper` per D-07), `effis_perimeter_paths`, `chained_run` (Aveiro only, non-blocking, optional). Single `CONCLUSIONS_DIST_EU.md` narrative (existing v1.0 file, append v1.1 sub-sections per Phase 4 D-13 pattern). Matrix cell renders as `dist:eu  X/3 PASS`. Manifest unchanged (`dist:eu` cell already exists with `cache_dir: eval-dist_eu`); no schema-breaking changes. REL-01's "5×2 = 10 cells" structural commitment preserved.

- **D-11: Single declarative-AOIS-list `run_eval_dist_eu.py` replaces both v1.0 scripts.** Phase 2 D-05/D-06 pattern — `run_eval_dist_eu.py` carries `EVENTS: list[EventConfig]` at module top with three entries (aveiro, evros, romania) looped sequentially; per-event `try`/`except` isolation so one failing event doesn't block the matrix; per-event whole-pipeline skip + per-stage `ensure_resume_safe` (Phase 1 D-Claude's-Discretion harness pattern). Existing `run_eval_dist_eu.py` (532 LOC, Aveiro) + `run_eval_dist_eu_nov15.py` (532 LOC, Aveiro Nov 15 follow-up) content **migrates into the new script**: aveiro entry inherits the v1.0 SAFE search + dist-s1 invocation logic (preserves cached SAFE provenance); the nov15-specific stage becomes the **chained_run sub-stage** of the aveiro event entry (per D-13 below). v1.0 scripts deleted at Phase 5 close — git history preserves them. EVENTS list shape: `EventConfig(event_id, post_dates: list[date], pre_dates: list[date], aoi_bbox_wgs84, mgrs_tile, effis_layer_name, effis_filter_dates, expected_burnt_area_km2, run_chained: bool)`. Plan-phase commits exact dates + AOIs for the 3 events with citations from EFFIS / EMSR649 / Copernicus EMS.

- **D-12: Module-level `EXPECTED_WALL_S` per event aggregated to script budget.** Per Phase 1 D-11 supervisor convention. Single supervisor invocation per script (not per-event); script-level `EXPECTED_WALL_S = sum(per_event_wall_s) + chained_retry_wall_s + safety_margin`. Estimated 6–10 hours wall (3 events × ~2 hours each + chained retry). Plan-phase commits exact value based on cached-vs-cold paths. Per-event-internal budget guard handled by per-stage `ensure_resume_safe` short-circuiting; supervisor watchdog catches script-level run-away only.

- **D-13: Chained `prior_dist_s1_product` retry as embedded post-stage in aveiro event entry.** Aveiro event has stages: pre-fetch → DEM → orbit → enumerate → 3× run_dist (Sep 28 → Oct 10 → Nov 15) un-chained → EFFIS download + rasterise → F1+CI computation → **chained_retry stage**: re-runs Nov 15 with `prior_dist_s1_product=<Oct 10 output>` argument (which itself was produced with `prior_dist_s1_product=<Sep 28 output>`); writes result to `eval-dist_eu/aveiro/chained/`. Non-blocking per DIST-07 — exception in this stage is caught, logged, and recorded as `chained_run.status='dist_s1_hang'` or `'crashed'` or `'skipped'` without failing the event. Embedded location keeps the chain logically tied to its un-chained baseline (same SAFEs + same DEM + same enumerate result). One Makefile target (`make eval-dist-eu`); single supervisor invocation; cache stays under `eval-dist_eu/aveiro/`. ROADMAP DIST-07 explicit: "non-blocking to milestone closure".

- **D-14: Chained retry pass criterion = structurally-valid 10-layer DIST-ALERT product.** Pass criterion = `dist_s1.data_models.output_models.DistS1ProductDirectory.from_path(chained_output_dir)` loads without exception AND all 10 layers are present (DIST-STATUS, DIST-CONFIDENCE, DIST-COUNT, etc. per OPERA spec) AND DIST-STATUS layer has at least one non-zero pixel. **No F1 comparison against un-chained baseline** — alert-promotion's confirmation-count logic legitimately changes the disturbance footprint, so F1 divergence is expected, not pathological. Loose-version "runs without crashing" rejected because dist-s1 can produce empty / partial outputs after the macOS-fork-hang regression. Tight-version "F1 within ±X of baseline" rejected because it converts a DIFFERENTIATOR signal into a false-FAIL hazard. `metrics.json per_event[aveiro].chained_run.status: Literal['structurally_valid','partial_output','dist_s1_hang','crashed','skipped']` with structurally_valid being the only pass state. CONCLUSIONS_DIST_EU.md aveiro section narrates the chained run as "DIFFERENTIATOR — structurally-valid 10-layer product produced; alert-promotion footprint compared to baseline qualitatively (figure)" — per ROADMAP DIST-07 "success is reported as a DIFFERENTIATOR".

### CMR auto-supersede + EFFIS rasterisation (DIST-04, DIST-05, PITFALLS P4.4)

- **D-15: CMR probe runs as Stage 0 of `run_eval_dist.py`.** Stage 0 queries CMR (NASA Common Metadata Repository) for collection `OPERA_L3_DIST-ALERT-S1_V1` covering MGRS T11SLT for sensing time around 2025-01-21. Uses `earthaccess.search_data(short_name='OPERA_L3_DIST-ALERT-S1_V1', bounding_box=(...), temporal=(...))`. On hit: fetches via earthaccess (Earthdata authenticated path; Phase 1 ENV-06 harness `download_reference_with_retry` with `source='earthdata'` retry policy) and uses operational granule as reference. On miss (most likely outcome during Phase 5 — operational publication is uncertain): falls back to v0.1 CloudFront sample (Phase 1 ENV-06 harness with `source='cloudfront'` retry policy). The decision is made once per eval invocation and recorded in `metrics.json`: `reference_source: Literal['operational_v1','v0.1_cloudfront','none']` + `reference_granule_id: str | None` + `cmr_probe_outcome: Literal['operational_found','operational_not_found','probe_failed']`. **No make-time supervisor probe** — single decision point per eval invocation; eliminates make-time/eval-time desync risk. Per Phase 1 ENV-06 the harness already supports both Earthdata and CloudFront paths — Phase 5 wires them into a conditional Stage 0.

- **D-16: When operational supersedes v0.1, replace `metrics.json` with v0.1 archived to `eval-dist/archive/`.** ROADMAP DIST-04 explicit: "no manual intervention" and "supersedes the v0.1 result in the matrix". Mechanism: (i) Stage 0 detects operational publication. (ii) If a previous v0.1 metrics.json exists, it's moved to `eval-dist/archive/v0.1_metrics_YYYY-MM-DDTHH-MM-SS.json` (timestamped from previous file's mtime) before the new run starts. (iii) The new run writes fresh `metrics.json` against the operational reference. (iv) `meta.json` records `reference_source: 'operational_v1'` + `previous_reference_archived_at: '<archive-path>'`. (v) `CONCLUSIONS_DIST_N_AM.md` gets an appended sub-section "v1.1 vs operational OPERA_L3_DIST-ALERT-S1_V1" — the v0.1 sub-section is preserved as "pre-operational baseline" (Phase 4 D-13 pattern). Auditable via git (CONCLUSIONS diff) + file timestamps (archive directory). Reasoning for archive-not-side-by-side: side-by-side schema bloat is short-term value (only the first publication week is interesting); long-term the operational is the single truth, and the v0.1 archive remains readable for cross-version studies.

- **D-17: EFFIS rasterisation default = `all_touched=False` + `all_touched=True` delta reported.** Default rasterisation per `rasterio.features.rasterize` with `all_touched=False`: only pixels whose center falls inside the EFFIS polygon are labelled "burnt". Conservative — doesn't inflate recall via boundary-touching pixels (PITFALLS P4.4 mitigation: prevents the 2–4 percentage-point F1 inflation that boundary-only labelling produces). The eval ALSO computes the `all_touched=True` F1 as an investigation diagnostic; `metrics.json per_event[N].rasterisation_diagnostic: {all_touched_false_f1, all_touched_true_f1, delta_f1}`. The primary F1 (all_touched=False) is the gate value; the delta is narrative-only (CONCLUSIONS narrates "F1 under all_touched=True is X — Y percentage points higher; primary metric uses all_touched=False per validation methodology §4"). `docs/validation_methodology.md §4` (this phase's append-only section, Phase 3 D-15 pattern) documents the rasterisation choice + cites PITFALLS P4.4 mitigation. Per-event rasterisation rule is uniform (no per-event tuning — target-creep prevention).

- **D-18: EFFIS WFS download via `harness.download_reference_with_retry(source='effis')` with new `RETRY_POLICY` branch.** Phase 1 ENV-06 already established the per-source retry policy pattern (CDSE / Earthdata / CloudFront / EGMS). Phase 5 adds a 5th branch: `RETRY_POLICY['effis'] = {'retry_on': [503, 504, 'ConnectionError', 'TimeoutError'], 'abort_on': [401, 403, 404], 'max_attempts': 5, 'backoff_factor': 2, 'max_backoff_s': 60}`. The retry function dispatches to `owslib.wfs.WebFeatureService(...).getfeature(...)` for `source='effis'`. Plan-phase commits the exact endpoint URL + layer name from a probe (research notes "EFFIS WFS endpoint — 2026 schema unverified; layer names drift" — plan-phase MUST verify before committing). Plan-phase also commits whether `owslib==0.35.0` (per `STACK.md` recommendation) is added to `conda-env.yml` (heavy native? may need conda-forge) or to the pip layer. EFFIS WFS responses are GML; eval converts via `geopandas.read_file(BytesIO(wfs_response))` to GeoDataFrame, then rasterises to subsideo's 30 m DIST grid per D-17.

- **D-19: EFFIS query per event uses date range + bounding box + layer name.** Per-event WFS GetFeature filter: `filter = And(BBOX(<event_aoi_bbox>), PropertyIsBetween('FIREDATE', start, end))` (or equivalent OGC Filter expression — exact property name is layer-specific, plan-phase commits). Cached response stored under `eval-dist_eu/<event_id>/effis_perimeters/perimeters.geojson` for re-run determinism. Cache invalidation via `ensure_resume_safe` mtime check; warm re-runs skip the WFS call. `meta.json per_event[N].effis_query_meta: {wfs_endpoint, layer_name, filter_string, response_feature_count, fetched_at}` for reproducibility.

### Cross-cutting carry-forwards from earlier phases (NOT re-decided here — listed for traceability)

- **D-20: `_mp.configure_multiprocessing()` fires at top of every `run_*()` (Phase 1 D-14, ENV-04).** Per Phase 1 ENV-04 D-Claude's-Discretion the bundle is mandatory: start method 'fork' on macOS / 'spawn' on Linux + `MPLBACKEND=Agg` + `RLIMIT_NOFILE` raise to 4096 + pre-fork `requests.Session` closure + `forkserver` fallback on Python ≥3.14. Phase 5 invokes it at the very top of each `run_eval_dist*.py` `main()` function (before any other import that might warm a network session). PITFALLS P0.1 (macOS fork pitfalls) is the binding pre-condition for DIST-07 chained retry — without the bundle, dist-s1 hangs.

- **D-21: Subprocess-level supervisor watchdog (Phase 1 D-10..D-14, ENV-05).** Each `run_eval_dist*.py` is invoked via `python -m subsideo.validation.supervisor run_eval_dist.py` (Makefile delegation). Watchdog mtime-staleness heuristic + per-script `EXPECTED_WALL_S` constant + `os.killpg` grandchild cleanup + py-spy stack dump on stale-detection. ENV-05 acceptance criterion (3 consecutive fresh `run_eval_dist*.py` runs without hanging on macOS) was achieved in Phase 1; Phase 5 just consumes.

- **D-22: Two CONCLUSIONS files per cell (Phase 3 D-08 inheritance).** `CONCLUSIONS_DIST_N_AM.md` (existing 195 LOC v1.0 file) + `CONCLUSIONS_DIST_EU.md` (existing 240 LOC v1.0 file) both get v1.1 sections appended. v1.0 narratives preserved as "v1.0 baseline" preamble per Phase 4 D-13 pattern. `matrix_manifest.yml` already references both files in the `conclusions_doc` field — no manifest edits needed for the doc names.

- **D-23: `docs/validation_methodology.md` §4 owned by Phase 5 (Phase 3 D-15 append-only).** Phase 5 appends ONE new section `§4: DIST-S1 Validation Methodology` covering: (4.1) single-tile F1 variance + block-bootstrap CI methodology (1km blocks, B=500, drop-partial-blocks, fixed seed), (4.2) EFFIS rasterisation choice + `all_touched=False` rationale, (4.3) EFFIS class-definition mismatch (PITFALLS P4.5 — low-severity ground fire / clear-cut forestry / etc. — narrative caveat that bounds expected precision/recall), (4.4) config-drift gate semantics + 7-key list + "any difference → defer" rationale, (4.5) CMR auto-supersede behaviour. NO §5 / §6 — those are Phase 6 / Phase 7 territory per Phase 3 D-15. Single-PR append at Phase 5 close alongside CONCLUSIONS updates.

- **D-24: `matrix_writer.py` adds DIST render branches.** Phase 4 added `disp:nam` + `disp:eu` branches (Phase 4 D-08 schema, mixed CALIBRATING + BINDING rendering). Phase 5 adds `dist:nam` + `dist:eu` render branches. `dist:nam` cell renders `f1=0.823 [0.781, 0.860] PASS` style + `reference_source` label (operational_v1 vs v0.1_cloudfront) inline. `dist:eu` cell renders aggregate `X/3 PASS` style + per-event mini-table in CONCLUSIONS link. Config-drift status (`PASSED` / `DEFERRED`) shown inline for `dist:nam` only (EU has no config-drift gate — EFFIS is its own reference). Order in `_render_*` dispatch: insert DIST branches BEFORE DSWx (which Phase 6 will add) but AFTER existing DISP branches per Phase 4 D-08 ordering invariant.

- **D-25: `matrix_schema.py` Pydantic v2 additive extension.** Phase 5 ADDS: `DistNamCellMetrics` (extends `MetricsJson`; carries `config_drift: ConfigDriftReport | None`, `reference_agreement.metrics: dict[str, MetricWithCI]`, `bootstrap_config: BootstrapConfig`, `reference_source: Literal[...]`, `reference_granule_id: str | None`, `cmr_probe_outcome: Literal[...]`); `DistEUCellMetrics` (extends `MetricsJson`; carries `per_event: list[DistEUEventMetrics]`, top-level aggregates per Phase 2 D-09/D-10); `DistEUEventMetrics` (event_id Literal, F1+CI per metric, EFFIS rasterisation_diagnostic, optional chained_run); `MetricWithCI` (point + ci_lower + ci_upper); `BootstrapConfig`; `ConfigDriftReport` (status Literal + per-key delta table); `RasterisationDiagnostic`; `ChainedRunResult`. Plan-phase commits exact field names + nesting per Phase 4 D-11 schema-extension review pattern. ZERO edits to existing types (Phase 1 D-09 big-bang lock holds).

### Claude's Discretion (for plan-phase)

- **Config-drift extraction code module location** — D-04: extend `compare_dist.py` if extraction is <50 LOC, new `validation/config_drift.py` if larger. Plan-phase decides after the D-01 probe lands.
- **Per-key delta table schema in `ConfigDriftReport`** — D-11 carries `per_key_table: list[KeyDelta]` where `KeyDelta = {key_name, opera_v01_value, dist_s1_2014_value, equal: bool, note: str}`. Plan-phase commits exact `KeyDelta` Pydantic shape.
- **`EXPECTED_WALL_S` actual values** — D-12 estimates 6-10 hours for `run_eval_dist_eu.py` and ~3 hours for `run_eval_dist.py`. Plan-phase commits exact values with cold-vs-warm-path rationale; supervisor budget = 2× per Phase 1 ENV-05.
- **EFFIS WFS endpoint URL + layer name** — D-18: research notes the schema is unverified for 2026; plan-phase MUST probe and commit. Likely candidates: `https://maps.effis.emergency.copernicus.eu/gwis` or similar; layer like `EFFIS.CurrentSituation` or `BurntAreas2024`.
- **`owslib` install location** — D-18: pip layer (pip-installable) likely sufficient; plan-phase confirms by checking if `owslib==0.35.0` has any C extensions. If yes, conda-forge; if no, pip layer in `pyproject.toml [validation]` extras.
- **Aveiro / Evros / Romania exact AOIs + dates** — D-11 EVENTS list: plan-phase commits exact lat/lon bboxes + sensing date triples per event with citations from EFFIS / EMSR649 / Copernicus EMS. Existing v1.0 `run_eval_dist_eu.py` carries Aveiro details (preserve via migration); Evros + Romania need fresh research.
- **Chained-retry stage skip-condition** — D-13: plan-phase decides whether to gate the chained retry on macOS-only (chained workflow's hang risk per PITFALLS P0.1 was macOS-specific) or run it everywhere. Default recommendation: run everywhere; the watchdog catches Linux hangs too.
- **`block_bootstrap_ci` numpy implementation details** — D-06: plan-phase commits whether to use `numpy.random.default_rng(seed)` (PCG64, modern) vs `numpy.random.RandomState(seed)` (Mersenne Twister, legacy); pixel-coordinate-to-block-index calculation; numerical stability notes.
- **Investigation-trigger entries in `criteria.py`** — single-tile F1 variance per PITFALLS P4.2 may warrant an `INVESTIGATION_TRIGGER` entry (e.g. `f1_ci_width > 0.05` flags single-tile variance for narrative review). Phase 2 D-13/D-14 pattern. Plan-phase decides whether to add — gate prevention vs narrative discipline.
- **`CONCLUSIONS_DIST_N_AM.md` v1.0 baseline preamble framing** — D-22: keep the v1.0 Park Fire content as a leading "v1.0 historical baseline" sub-section vs as an inline footnote vs as a separate `CONCLUSIONS_DIST_N_AM_HISTORICAL.md` file. Recommendation: leading sub-section per Phase 4 D-13.
- **CMR query temporal window** — D-15: query for sensing time around 2025-01-21 — plan-phase commits exact ±days tolerance. ±7 days reasonable to cover orbit-pass uncertainty.
- **DIST cell `cell_status` Literal extension** — Phase 3 D-03 + Phase 4 D-19 inherit `Literal['PASS','FAIL','CALIBRATING','MIXED','BLOCKER']`. Phase 5 may need `'DEFERRED'` to render config-drift defer outcome distinctly. Plan-phase decides whether to extend the Literal in `matrix_schema.py` (additive change) or render DEFERRED through one of the existing states (e.g. MIXED with note).
- **`run_eval_dist.py` Park Fire migration** — D-05: when renaming `eval-dist/` → `eval-dist-park-fire/`, the existing `run_eval_dist.py` content needs to either (a) be repointed to T11SLT inline (clobbering Park Fire logic) or (b) be branched: keep `run_eval_dist.py` for T11SLT (DIST-01 mandate); preserve `run_eval_dist_park_fire.py` as a renamed-but-disabled-from-manifest script. Recommendation: (a) — the v1.0 Park Fire script content was a "structurally complete" run anyway; T11SLT inherits the structure (auth → enumerate → SAFE search → DEM → 2× run_dist → compare) with different inputs.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source-of-truth scope (read first)

- `.planning/ROADMAP.md` §Phase 5 (lines 157-173) — goal, 6 success criteria, 7 requirements (DIST-01..07), CMR auto-supersede semantics, chained retry non-blocking framing.
- `.planning/REQUIREMENTS.md` §DIST-01..07 (lines 62-70 v1.1 + lines 192-198 traceability) — full text of the 7 requirements; DIST-V2-01..04 future work for context (not Phase 5 scope).
- `.planning/PROJECT.md` — DIST F1 > 0.80 + accuracy > 0.85 pass criteria; v1.1 metrics-vs-targets discipline ("validators not quality ceilings"); EU expansion goal.
- `.planning/STATE.md` — Phase 4 closure status; ENV-04 _mp.py bundle status (Phase 1 complete) — pre-condition for DIST-07 chained retry.

### Phase 1/2/3/4 CONTEXT (REQUIRED for understanding harness, criteria, schema, append-only doc policy)

- `.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/01-CONTEXT.md` — D-04 to D-19: criteria.py (`Literal['BINDING','CALIBRATING','INVESTIGATION_TRIGGER']` + `binding_after_milestone` field); split `ProductQualityResult` / `ReferenceAgreementResult`; `_mp.py` bundle (D-14 ENV-04) — pre-condition for DIST-07; supervisor mechanics (D-10..D-14 ENV-05); harness 5 helpers + per-source retry policy (D-Claude's-Discretion ENV-06) — Phase 5 adds 5th source 'effis' to RETRY_POLICY; matrix_schema.py + matrix_writer.py + matrix_manifest.yml conventions.
- `.planning/phases/02-rtc-s1-eu-validation/02-CONTEXT.md` — D-05/D-06 declarative AOIS-list + per-AOI try/except (Phase 5 D-11 pattern source); D-09/D-10 single aggregate `metrics.json` + nested `per_event/per_burst` list + top-level aggregates (Phase 5 D-10 pattern source); D-13/D-14/D-15 `INVESTIGATION_TRIGGER` discipline (Phase 5 D-25 reuses for F1 variance flag if added); D-12 cell-level `meta.json` with input hashes (Phase 5 includes per-event sources hashes).
- `.planning/phases/03-cslc-s1-self-consistency-eu-validation/03-CONTEXT.md` — D-08 two CONCLUSIONS files per cell (`CONCLUSIONS_DIST_N_AM.md` + `CONCLUSIONS_DIST_EU.md` already exist); D-15 `docs/validation_methodology.md` append-only by phase (Phase 5 owns §4 only, NOT §5/§6); D-13 §1 leads with structural argument before diagnostic appendix (Phase 5 §4 leads with single-tile F1 variance methodology before EFFIS rasterisation diagnostic).
- `.planning/phases/04-disp-s1-comparison-adapter-honest-fail/04-CONTEXT.md` — D-11 Pydantic v2 schema additive extension (`DispCellMetrics` shape — Phase 5 mirrors via `DistNamCellMetrics` + `DistEUCellMetrics`); D-13 v1.0 narrative preserved as preamble in CONCLUSIONS (Phase 5 D-22 reuses); D-19 first-rollout CALIBRATING cell rendering (DIST has no new CALIBRATING gates so simpler than DISP); D-04 module-level constant pattern (Phase 5 inherits via `EXPECTED_WALL_S` per script + `DEFAULT_BLOCK_SIZE_M` / `DEFAULT_N_BOOTSTRAP` / `DEFAULT_RNG_SEED` in bootstrap.py).

### Phase 5 research (authoritative for HOW)

- `.planning/research/SUMMARY.md` — Phase 5 row (DIST OPERA v0.1 + EFFIS EU): scope (LA T11SLT comparison or deferral; CMR probe; EFFIS cross-val; +1 EU event); watch-outs (P4.1/P4.2 already correctly scoped in BOOTSTRAP §4.1; P4.3/P4.4/P4.5 surface as plan-phase concerns); chained `prior_dist_s1_product` feasibility depends on Phase 1 _mp.py bundle (RESOLVED — Phase 1 ENV-04 complete).
- `.planning/research/PITFALLS.md §P0.1` — macOS fork mode failure modes; pre-condition for DIST-07 chained retry. Phase 1 mitigation already in place (ENV-04).
- `.planning/research/PITFALLS.md §P4.1` — OPERA v0.1 metadata extraction failure modes (HDF5 attrs vs JSON-strings vs sidecar XML vs partially missing). D-01 mitigation: plan-phase probe-then-commit. Mitigation framing: artifact-level transparency (DriftReport with full per-key table) over hidden best-effort.
- `.planning/research/PITFALLS.md §P4.2` — single-tile F1 variance; mitigation = block-bootstrap CI (1 km blocks, B=500). D-06..D-09 implement directly.
- `.planning/research/PITFALLS.md §P4.3` — CloudFront URL expiry + no Range support. Phase 1 ENV-06 harness `download_reference_with_retry(source='cloudfront')` mitigates: HEAD pre-flight + chunked download + URL refresh per chunk. Phase 5 just consumes.
- `.planning/research/PITFALLS.md §P4.4` — EFFIS perimeter rasterisation `all_touched=True` vs `False` (2-4pp F1 swing). D-17 mitigation: `all_touched=False` default + `all_touched=True` delta reported as diagnostic.
- `.planning/research/PITFALLS.md §P4.5` — EFFIS "burnt" class-definition mismatch (low-severity ground fire / burn-and-resprout / clear-cut etc.). Narrative caveat in `docs/validation_methodology.md` §4.3 (D-23) — bounds expected precision/recall.
- `.planning/research/FEATURES.md §Phase 5` — DIST T11SLT comparison or deferral; CMR probe; EFFIS cross-val; +1 EU event. (lines from FEATURES grep: "Phase 4 has soft external dependency on OPERA operational publication"; "owslib==0.35.0 (EFFIS WFS; no pyeffis exists)".)
- `.planning/research/ARCHITECTURE.md` — harness public API; matrix_writer manifest-authoritative pattern (REL-02).
- `.planning/research/STACK.md` — `owslib==0.35.0` for EFFIS WFS (D-18 + Claude's Discretion item); `dist-s1` 2.0.14 (DIST-02 baseline); `asf-search` 12.0.7 (CMR probe + earthaccess); `boto3` (CDSE not used here, CloudFront direct via `requests` + signed URL).

### v1.0 CONCLUSIONS (context for what Phase 5 inherits)

- `CONCLUSIONS_DIST_N_AM.md` (195 LOC, 2026-04-15) — Park Fire MGRS 10TFK; "OPERA reference NOT YET PUBLISHED"; structurally-complete-no-comparison outcome. v1.0 §1.2 AOI rationale + §2 pipeline run details preserved as v1.1 "v1.0 historical baseline" preamble (D-05 + D-22). Phase 5 v1.1 sections append at end with T11SLT numbers.
- `CONCLUSIONS_DIST_EU.md` (240 LOC, ~2026-04-16) — Aveiro 2024 (likely); v1.0 narrative preserved as preamble. Phase 5 v1.1 sections append with 3-event aggregate.

### v1.0 precedent files to match (existing conventions)

- `src/subsideo/validation/compare_dist.py` (existing, 2026-04-15 era) — primary modification surface for config-drift extraction. v1.0 `compare_dist(subsideo_path, reference_path)` returns `DistValidationResult`. Phase 5 ADDS `extract_v01_config_drift(opera_sample_path) -> DriftReport` (or moves to new module per D-04). Phase 5 also expands return type to include split `product_quality` (empty for DIST) + `reference_agreement` (F1+CI per D-07).
- `src/subsideo/validation/harness.py` (627 LOC, Phase 1) — 5 helpers consumed unchanged. Phase 5 ADDS 5th branch to `RETRY_POLICY: dict[str, RetryPolicy]` for `'effis'` source (D-18). Phase 5 is the 6th harness consumer (after Phase 1 pilot + Phase 2 RTC-EU + Phase 3 CSLC-NAM/EU + Phase 4 DISP-NAM/EU).
- `src/subsideo/validation/supervisor.py` — Phase 5 eval scripts declare `EXPECTED_WALL_S` constant per Phase 1 D-11 (D-12 / D-21).
- `src/subsideo/validation/matrix_schema.py` (449 LOC + Phase 4 additions) — Pydantic v2 base. Phase 5 ADDS 7 new types (D-25): `DistNamCellMetrics`, `DistEUCellMetrics`, `DistEUEventMetrics`, `MetricWithCI`, `BootstrapConfig`, `ConfigDriftReport`, `RasterisationDiagnostic`, `ChainedRunResult`. ZERO edits to existing types.
- `src/subsideo/validation/matrix_writer.py` — Phase 5 ADDS `dist:nam` + `dist:eu` render branches (D-24). Order: AFTER `disp:*` (Phase 4 D-08), BEFORE `dswx:*` (Phase 6 future).
- `src/subsideo/validation/criteria.py` — Phase 5 makes ZERO edits to existing entries (`dist.f1_threshold = 0.80` + `dist.accuracy_threshold = 0.85` already shipped in v1.0). Phase 5 MAY add `INVESTIGATION_TRIGGER` entry for F1 CI width per Claude's Discretion (plan-phase decides).
- `src/subsideo/validation/metrics.py` — point-estimate F1 / precision / recall / accuracy / bias / rmse / correlation primitives consumed unchanged. Phase 5 does NOT extend; bootstrap is a separate `validation/bootstrap.py` module per D-06.
- `src/subsideo/products/dist.py` — `run_dist()` entry point UNCHANGED in Phase 5 per "Not this phase" boundary.
- `src/subsideo/data/asf.py` — Earthdata + earthaccess auth path; consumed by CMR probe (D-15).
- `run_eval_dist.py` (450 LOC, v1.0 Park Fire) — primary modification target for N.Am. T11SLT cell. Phase 5 changes per D-05: (1) Stage 0 CMR probe (D-15), (2) v0.1 CloudFront sample fetch (when CMR misses) — already partially in place per `eval-dist/opera_reference/` directory existing, (3) config-drift extraction stage (D-01..D-04), (4) F1 + bootstrap CI computation (D-06..D-09), (5) write nested `metrics.json` per `DistNamCellMetrics` schema, (6) declare `EXPECTED_WALL_S` constant.
- `run_eval_dist_eu.py` (532 LOC, v1.0 Aveiro) + `run_eval_dist_eu_nov15.py` (532 LOC, v1.0 Aveiro Nov 15 follow-up) — both content migrates into a single new declarative-AOIS-list `run_eval_dist_eu.py` per D-11. v1.0 scripts deleted at Phase 5 close. EVENTS list with 3 entries (aveiro / evros / romania); aveiro entry's chained_retry stage subsumes nov15 logic per D-13.
- `eval-dist/` — existing cache from v1.0 Park Fire — RENAMED to `eval-dist-park-fire/` per D-05 at Phase 5 start. New `eval-dist/` populated fresh for T11SLT.
- `eval-dist_eu/` (existing) + `eval-dist-eu/` + `eval-dist-eu-nov15/` (existing) — cache directory consolidation per D-11. Plan-phase decides whether to consolidate to `eval-dist_eu/` or rename to `eval-dist-eu/` (matrix_manifest.yml uses `eval-dist_eu` underscore — plan-phase confirms convention; harness `find_cached_safe` fallback search-path may already handle the divergence per Phase 4 STATE.md note).
- `results/matrix_manifest.yml` — already lists `dist:nam` (eval_script: run_eval_dist.py, cache_dir: eval-dist) + `dist:eu` (eval_script: run_eval_dist_eu.py, cache_dir: eval-dist_eu) — Phase 5 fills the metrics.json sidecars at runtime; no manifest schema edits.
- `Makefile` — `eval-dist-nam` + `eval-dist-eu` targets already defined per Phase 1 D-08; Phase 5 fills the referenced scripts (which already exist with v1.0 content; Phase 5 rewrites + extends).
- `CONCLUSIONS_RTC_EU.md` (Phase 2) — template for the multi-section CONCLUSIONS shape Phase 5 emulates: Calibration Framing + Investigation Discipline + Per-Event Table + Aggregate Result. Phase 2 D-13/D-14/D-15 investigation pattern reapplied to DIST single-tile F1 variance + EFFIS class-definition mismatch.
- `CONCLUSIONS_DISP_EU.md` (Phase 4) — template for v1.0-baseline-preamble + v1.1-section-append pattern (Phase 4 D-13). Phase 5 mirrors for DIST.

### External library refs (read as-needed during plan-phase)

- `dist-s1` 2.0.14 — Python source (`dist_s1/dist_processing.py` likely path) for default config parameter values. Source for D-02 7-key list extraction.
- `dist_s1.data_models.output_models.DistS1ProductDirectory` — D-14 chained retry pass criterion: `from_path(...)` loads + 10 layers present + DIST-STATUS non-empty.
- `earthaccess` 0.17.0 — `search_data(short_name='OPERA_L3_DIST-ALERT-S1_V1', bounding_box, temporal)` for CMR probe (D-15).
- `owslib` 0.35.0 — `WebFeatureService` + `getfeature(typename=, filter=)` for EFFIS WFS (D-18 + D-19). Plan-phase verifies `owslib==0.35.0` is the right version — STACK.md asserts this; plan-phase confirms via probe.
- `rasterio.features.rasterize` — `all_touched=False` rasterisation (D-17). Already in v1.0 dependency tree.
- `geopandas.read_file` — GML response parsing for owslib WFS (D-18).
- `numpy.random.default_rng` (PCG64) vs `numpy.random.RandomState` (Mersenne) — plan-phase commits per Claude's Discretion (D-09).
- `h5py` — direct HDF5 attribute introspection for D-01 probe (or `h5dump -A` shell tool).
- `asf_search` — already in v1.0 stack; not the primary CMR client (`earthaccess` is); may help with granule URL resolution post-CMR-hit.

### EFFIS WFS endpoint references (plan-phase MUST verify before locking)

- `https://maps.effis.emergency.copernicus.eu/` — EFFIS map server (likely WFS endpoint base; plan-phase probes for WFS subpath like `/gwis/services` or `/wfs`).
- `https://forest-fire.emergency.copernicus.eu/` — alternative endpoint surfaced in some EFFIS literature; plan-phase probes both.
- EMSR649 (Evros 2023) — Copernicus EMS activation product naming; plan-phase resolves the activation's Vector Mapping product URL for the burnt-area perimeter.
- 2022 Romanian forest clear-cuts — likely a non-EMSR event (clear-cuts aren't fires); plan-phase confirms whether EFFIS covers forestry activity at all (PITFALLS P4.5 explicitly notes "DIST-S1 detects clear-cut logging in unburnt forest — not in EFFIS perimeters"). May require alternative reference (Forest Cover Change products from JRC, Global Forest Watch, etc.) OR may signal that "Romania forest clear-cuts" is the wrong choice for EFFIS validation and a different EU event substitutes. Plan-phase reviews and surfaces.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`src/subsideo/validation/compare_dist.py`** — primary surface. v1.0 has `compare_dist(...)` for F1/precision/recall/accuracy point estimates against an OPERA reference HDF5. Phase 5 EXTENDS: (a) point-estimate metrics wrapped in `block_bootstrap_ci` calls (D-06..D-09), (b) NEW `extract_v01_config_drift(opera_sample_path) -> DriftReport` helper (D-04 — same file or new module by plan-phase decision).
- **`src/subsideo/validation/harness.py` (627 LOC, Phase 1)** — 5 helpers consumed unchanged; ADD `RETRY_POLICY['effis']` branch (D-18). Existing `download_reference_with_retry` dispatches by `source` already supports CDSE / Earthdata / CloudFront / EGMS — Phase 5 adds the 5th source.
- **`src/subsideo/validation/supervisor.py`** — subprocess wrapper. Phase 5 scripts declare `EXPECTED_WALL_S` per Phase 1 D-11.
- **`src/subsideo/validation/matrix_schema.py` (449 LOC + Phase 4 additions)** — Pydantic v2 base. ADD 7 new types (D-25); zero edits to existing.
- **`src/subsideo/validation/matrix_writer.py` (475 LOC + Phase 4 additions)** — manifest-driven cell renderer. ADD `dist:nam` + `dist:eu` render branches (D-24).
- **`src/subsideo/validation/criteria.py`** — `dist.f1_threshold` + `dist.accuracy_threshold` BINDING entries already shipped. ZERO edits in Phase 5 (Phase 4 D-19 inherited).
- **`src/subsideo/validation/metrics.py`** — F1 / precision / recall / accuracy / bias / rmse / correlation point-estimates. UNCHANGED. Phase 5's bootstrap helper lives in new `bootstrap.py` per D-06.
- **`run_eval_dist.py` (450 LOC v1.0)** — N.Am. eval, primary modification target. Phase 5 inserts CMR Stage 0, config-drift extraction, F1+CI computation, schema-compliant metrics.json write.
- **`run_eval_dist_eu.py` (532 LOC v1.0) + `run_eval_dist_eu_nov15.py` (532 LOC v1.0)** — EU evals, both CONTENT MIGRATES into a single new declarative-AOIS-list `run_eval_dist_eu.py` per D-11.
- **`CONCLUSIONS_DIST_N_AM.md` (195 LOC) + `CONCLUSIONS_DIST_EU.md` (240 LOC)** — v1.0 narratives preserved as v1.1 baseline preamble (D-22).
- **`docs/validation_methodology.md` (existing, post-Phase-3 §1+§2; post-Phase-4 §3)** — append §4 only (D-23).

### Established Patterns

- **`_mp.configure_multiprocessing()` at top of every `run_*()`** — Phase 1 ENV-04 D-14. PRE-CONDITION for DIST-07 chained retry (PITFALLS P0.1).
- **Subprocess-level supervisor watchdog** — Phase 1 D-10..D-14. Phase 5 declares `EXPECTED_WALL_S` per script.
- **Per-source retry policy in harness.RETRY_POLICY** — Phase 1 ENV-06. Phase 5 adds 5th source 'effis'.
- **Lazy imports for conda-forge deps** — Phase 1 lazy-import discipline. New code (`block_bootstrap_ci`, `extract_v01_config_drift`, EFFIS WFS query) imports `numpy` at module top + heavy deps (rasterio, geopandas, owslib, h5py, earthaccess) inside function bodies.
- **Declarative module-level constants** — `EXPECTED_WALL_S`, `DEFAULT_BLOCK_SIZE_M`, `DEFAULT_N_BOOTSTRAP`, `DEFAULT_RNG_SEED` at module top; auditable in git (Phase 1 D-11 + Phase 4 D-04).
- **Aggregate metrics.json + nested per_event/per_burst sub-results** — Phase 2 D-09/D-10 + Phase 4 D-11. Phase 5 D-10 + D-25 mirrors.
- **Cell-level meta.json with input hashes** — Phase 2 D-12. Phase 5 includes per-event input hashes (SAFE hashes, EFFIS perimeter response hashes, OPERA v0.1 sample hash, dist-s1 output hashes).
- **Matrix-writer manifest-authoritative** — never globs CONCLUSIONS_*.md; reads from `metrics.json` only via `matrix_manifest.yml` (REL-02 PITFALLS R3+R5 mitigation).
- **Two CONCLUSIONS files per cell** — Phase 3 D-08 + Phase 4 D-22. `CONCLUSIONS_DIST_N_AM.md` + `CONCLUSIONS_DIST_EU.md` pattern.
- **`docs/validation_methodology.md` append-only by phase** — Phase 3 D-15 + Phase 4 D-23. Phase 5 owns §4.
- **First-rollout CALIBRATING italicisation** — Phase 4 D-19. NOT applicable to Phase 5 (no new CALIBRATING gates).
- **Auto-attribute Literal schema for status enums** — Phase 4 D-11 `attributed_source` Literal. Phase 5 reuses pattern for `cell_status`, `config_drift.status`, `chained_run.status`, `cmr_probe_outcome`, `reference_source`.
- **v1.0 narrative preserved as baseline preamble in CONCLUSIONS** — Phase 4 D-13. Phase 5 D-22 reuses for both N.Am. (Park Fire baseline) + EU (Aveiro v1.0 baseline).
- **Module-level constant at top + raise-on-missing** — Phase 4 D-04. Phase 5 applies to bootstrap config defaults.

### Integration Points

- **Manifest already wires the cells** — `dist:nam` + `dist:eu` exist in `matrix_manifest.yml`; Phase 5 fills `metrics.json` at runtime.
- **Makefile already has targets** — `eval-dist-nam` + `eval-dist-eu`; Phase 5 fills the referenced scripts.
- **Harness already supports CloudFront + Earthdata paths** (Phase 1 ENV-06 + ENV-07); Phase 5 just adds 'effis' branch + wires Stage 0 CMR probe.
- **`_mp.configure_multiprocessing()` already lands** at top of `run_dist*` (Phase 1 ENV-04); Phase 5 just consumes.
- **Supervisor already wraps** every `run_*()` invocation; Phase 5 declares `EXPECTED_WALL_S` per script.
- **`compare_dist.py` already exists** with v1.0 F1 logic; Phase 5 extends with bootstrap + config-drift.
- **`dist:nam` + `dist:eu` render branches** insertion order in `matrix_writer.py`: AFTER `disp:*` (Phase 4 D-08), BEFORE `dswx:*` (Phase 6 future). Plan-phase places per Phase 4 D-08 ordering invariant.

</code_context>

<specifics>
## Specific Ideas

- **"Validators not quality ceilings" is the milestone-discipline north star** — Phase 5 D-03 (any-difference-defer) + D-07 (95% CI exposed for transparency, not threshold-tightening) + D-17 (rasterisation-default-conservative + delta-reported) all align to this.
- **Phase 4's honest-FAIL pattern carries forward** — DIST may produce surprising F1 numbers under v0.1 reference; Phase 5's job is to report them honestly with config-drift gating that distinguishes "subsideo broken" from "v0.1 reference materially diverged from production defaults".
- **CMR auto-supersede is the milestone-friendly answer to "what if operational publishes mid-Phase-5"** — D-15 + D-16 wire it as an eval-script Stage 0; the matrix cell silently shifts from v0.1 to operational reference with full audit trail in metrics.json + meta.json + CONCLUSIONS append.
- **Park Fire's v1.0 outcome is preserved-not-lost** — D-05 + D-22 ensure the v1.0 "structurally complete, no comparison" Park Fire run is readable in CONCLUSIONS_DIST_N_AM.md as historical baseline, and the cache directory is renamed (not deleted).
- **EFFIS WFS endpoint + layer name probe is the highest-uncertainty plan-phase action** — D-18 + Claude's Discretion items. Research notes the schema is unverified for 2026; plan-phase MUST commit with evidence (probe via `owslib` `WebFeatureService.contents` listing).
- **The chained-retry stage is THE differentiator artifact** — D-13 + D-14. ROADMAP DIST-07 explicit: "success is reported as a DIFFERENTIATOR". This is one of the few Phase 5 deliverables that explicitly does NOT serve the matrix-cell PASS/FAIL discipline; it's a feature of subsideo, not a validation gate.

</specifics>

<deferred>
## Deferred Ideas

- **Operational monitoring chain with provisional→confirmed alert promotion** — DIST-V2-01; deferred to v2.
- **Upstream PR for `post_date_buffer_days` default change in dist-s1** — DIST-V2-02; deferred to v2 (if Phase 5's config-drift gate identifies this as a material drift, the finding becomes the basis for the upstream PR but the PR itself isn't a Phase 5 deliverable).
- **Full OPERA product-spec metadata validation through `DistS1ProductDirectory`** — DIST-V2-03; deferred to v2. Phase 5 D-14 only requires the pass criterion subset (10 layers + DIST-STATUS non-empty), not full metadata schema validation.
- **Re-running against operational OPERA DIST-S1 as a planned activity** — DIST-V2-04; the Phase 5 CMR probe handles auto-supersede if it lands mid-milestone, otherwise this is a v2 task.
- **ML-replacement algorithm for DSWE thresholds** — DSWX-V2-01; not Phase 5 territory at all (different product), noted only because user mentioned "named upgrade path" framing in milestone discipline.
- **Multi-burst mosaicking** — DISP-V2-03 / cross-cutting; out of scope.
- **MintPy SBAS as 5th candidate in DISP Unwrapper Brief** — Phase 4 deferred (4-candidate framing intentional); not Phase 5 territory.
- **Promotion of `extract_v01_config_drift` from `compare_dist.py` (or `validation/config_drift.py`) to a generic `validation/drift_gates.py`** — only if DSWx Phase 6 also needs config-drift gates (no current evidence it does); Phase 5 keeps the helper local per Phase 4 D-18 promotion-rule pattern (extract to shared module on 2nd consumer).
- **`block_bootstrap_ci` reuse for non-F1 metrics in Phase 6 DSWx** — out of scope here; Phase 6 plan-phase decides if DSWx F1 needs CI bands too.
- **EFFIS class-definition reconciliation** (PITFALLS P4.5 — EFFIS "burnt" includes low-severity ground fire / burn-and-resprout that DIST may miss; DIST "disturbed" includes clear-cut / windthrow / defoliation that EFFIS doesn't include) — narrative caveat in `docs/validation_methodology.md §4.3` per D-23, NOT a Phase 5 mitigation. The class mismatch bounds expected precision/recall; Phase 5 reports precision > 0.70 + recall > 0.50 as the gate per DIST-05; failure to clear the bar is a v2 conversation.
- **Romania 2022 EU event substitution** — Claude's Discretion + canonical_refs note: EFFIS may not cover clear-cuts; plan-phase confirms event choice and may substitute (e.g. another wildfire instead of clear-cuts) if EFFIS reference isn't available. Substitution surfaces as a plan-phase ADR rather than a Phase 5 blocker.

</deferred>

---

*Phase: 05-dist-s1-opera-v0-1-effis-eu*
*Context gathered: 2026-04-25*
