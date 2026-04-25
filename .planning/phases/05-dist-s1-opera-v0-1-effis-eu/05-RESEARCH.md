# Phase 5: DIST-S1 OPERA v0.1 + EFFIS EU - Research

**Researched:** 2026-04-25
**Domain:** SAR-disturbance binary-classification validation (DIST-S1) against OPERA pre-operational reference (CloudFront sample) and EFFIS WFS optical burnt-area perimeters; auto-supersede via NASA CMR; non-blocking chained `prior_dist_s1_product` retry on Aveiro EU stack.
**Confidence:** HIGH on dist-s1 v2.0.14 default config (verbatim from v2.0.14 tag), product structure (verified locally), owslib version, and existing harness/schema patterns. MEDIUM on EFFIS WFS endpoint + property names (two competing endpoints surfaced; plan-phase MUST GetCapabilities-probe before locking). MEDIUM-LOW on Romania-2022 EFFIS coverage adequacy (clear-cuts may not be in EFFIS — substitution likely needed).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Config-drift gate mechanics (DIST-02, PITFALLS P4.1):**
- **D-01:** Plan-phase probes the OPERA v0.1 sample first; commits extraction strategy with evidence. Mirrors Phase 4 D-Claude's-Discretion pattern (defer specifics that depend on artefact evidence to plan-phase).
- **D-02:** Plan-phase locks the full 7-key list with evidence from dist-s1 2.0.14 source + v0.1 sample.
- **D-03:** Any difference → defer (strictest threshold). Matrix cell renders `'deferred pending operational reference publication'`. No per-key tolerance bands.
- **D-04:** Config-drift extraction code module location — plan-phase decides (`compare_dist.py` if <50 LOC, new `validation/config_drift.py` if larger).

**N.Am. AOI disposition + block-bootstrap CI (DIST-01, DIST-03):**
- **D-05:** T11SLT replaces 10TFK in the `dist:nam` matrix cell; Park Fire kept as separate non-matrix artifact. Rename `eval-dist/` → `eval-dist-park-fire/`; new `eval-dist/` for T11SLT.
- **D-06:** New `validation/bootstrap.py` module hosts `block_bootstrap_ci`. Pure-numpy spatial bootstrap with `BootstrapResult` dataclass.
- **D-07:** F1 + ci_lower + ci_upper (95%) per metric in `metrics.json`. 4 metrics × 3 fields. Symmetric bounds NOT assumed.
- **D-08:** Drop partial blocks at MGRS tile edges — `n_kept` + `n_dropped` reported. Block layout anchored to tile origin (UTM SW corner).
- **D-09:** `BootstrapResult` deterministic via fixed `rng_seed=0` default. PR-level switching only.

**EU events orchestration + chained retry (DIST-06, DIST-07):**
- **D-10:** Single aggregate `dist:eu` matrix cell with `per_event` sub-results. Single `eval-dist_eu/metrics.json` carries top-level aggregates + nested `per_event: list[DistEUEventMetrics]`.
- **D-11:** Single declarative-AOIS-list `run_eval_dist_eu.py` replaces both v1.0 scripts. v1.0 scripts deleted at Phase 5 close.
- **D-12:** Module-level `EXPECTED_WALL_S` per script; supervisor budget = 2× per Phase 1 ENV-05.
- **D-13:** Chained `prior_dist_s1_product` retry as embedded post-stage in aveiro event entry. Sep 28 → Oct 10 → Nov 15. Non-blocking per DIST-07.
- **D-14:** Chained retry pass criterion = structurally-valid 10-layer DIST-ALERT product. NO F1 comparison against un-chained baseline. `chained_run.status: Literal['structurally_valid','partial_output','dist_s1_hang','crashed','skipped']`.

**CMR auto-supersede + EFFIS rasterisation (DIST-04, DIST-05, PITFALLS P4.4):**
- **D-15:** CMR probe runs as Stage 0 of `run_eval_dist.py`. `reference_source: Literal['operational_v1','v0.1_cloudfront','none']`.
- **D-16:** When operational supersedes v0.1, replace `metrics.json` with v0.1 archived to `eval-dist/archive/`. Auditable via git + file timestamps.
- **D-17:** EFFIS rasterisation default = `all_touched=False` + `all_touched=True` delta reported. The primary F1 (all_touched=False) is the gate value; the delta is narrative-only.
- **D-18:** EFFIS WFS download via `harness.download_reference_with_retry(source='effis')` with new `RETRY_POLICY` branch. Plan-phase commits the exact endpoint URL + layer name from probe.
- **D-19:** EFFIS query per event uses date range + bounding box + layer name. Cached response stored under `eval-dist_eu/<event_id>/effis_perimeters/perimeters.geojson`.

**Cross-cutting carry-forwards (NOT re-decided here — listed for traceability):**
- D-20: `_mp.configure_multiprocessing()` fires at top of every `run_*()` (Phase 1 D-14, ENV-04).
- D-21: Subprocess-level supervisor watchdog (Phase 1 D-10..D-14, ENV-05).
- D-22: Two CONCLUSIONS files per cell (Phase 3 D-08 inheritance).
- D-23: `docs/validation_methodology.md` §4 owned by Phase 5 (Phase 3 D-15 append-only).
- D-24: `matrix_writer.py` adds DIST render branches.
- D-25: `matrix_schema.py` Pydantic v2 additive extension; ZERO edits to existing types.

### Claude's Discretion (for plan-phase)

- Config-drift extraction code module location (D-04: extend `compare_dist.py` if <50 LOC, new `validation/config_drift.py` if larger).
- Per-key delta table schema in `ConfigDriftReport` (D-11: `per_key_table: list[KeyDelta]` with `KeyDelta = {key_name, opera_v01_value, dist_s1_2014_value, equal: bool, note: str}`).
- `EXPECTED_WALL_S` actual values (D-12: ~3 hours `run_eval_dist.py`; 6-10 hours `run_eval_dist_eu.py`).
- EFFIS WFS endpoint URL + layer name (D-18: schema unverified for 2026; plan-phase MUST probe).
- `owslib` install location (D-18: pip layer likely sufficient; plan-phase confirms).
- Aveiro/Evros/Romania exact AOIs + dates (D-11 EVENTS list; v1.0 carries Aveiro details; Evros + Romania need fresh research).
- Chained-retry stage skip-condition (D-13: macOS-only vs everywhere; default recommendation = run everywhere).
- `block_bootstrap_ci` numpy implementation (D-06: `numpy.random.default_rng(seed)` PCG64 vs `RandomState`).
- Investigation-trigger entries in `criteria.py` (single-tile F1 variance flag).
- `CONCLUSIONS_DIST_N_AM.md` v1.0 baseline preamble framing (D-22: leading sub-section vs inline footnote vs separate file).
- CMR query temporal window (D-15: ±days tolerance).
- DIST cell `cell_status` Literal extension (whether to add `'DEFERRED'`).
- `run_eval_dist.py` Park Fire migration (D-05: repoint inline vs branch).

### Deferred Ideas (OUT OF SCOPE)

- Operational monitoring chain with provisional→confirmed alert promotion (DIST-V2-01).
- Upstream PR for `post_date_buffer_days` default change in dist-s1 (DIST-V2-02).
- Full OPERA product-spec metadata validation through `DistS1ProductDirectory` (DIST-V2-03).
- Re-running against operational OPERA DIST-S1 as a planned activity (DIST-V2-04 — CMR probe handles auto-supersede).
- ML-replacement algorithm for DSWE thresholds (DSWX-V2-01 — Phase 6 territory).
- Multi-burst mosaicking (DISP-V2-03).
- MintPy SBAS as 5th candidate in DISP Unwrapper Brief.
- Promotion of `extract_v01_config_drift` to generic `validation/drift_gates.py`.
- `block_bootstrap_ci` reuse for non-F1 metrics in Phase 6 DSWx.
- EFFIS class-definition reconciliation (PITFALLS P4.5 — narrative caveat only).
- Romania 2022 EU event substitution may surface as plan-phase ADR rather than a Phase 5 blocker.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **DIST-01** | OPERA DIST v0.1 sample for MGRS T11SLT fetched via CloudFront direct-download with exponential-backoff retry (via harness) and cached under `eval-dist/opera_reference/v0.1_T11SLT/`. Sample preserved on disk regardless of downstream comparison outcome. | Probe 7 — CloudFront URL pattern resolved (no canonical published URL exists; sample is **generated locally** by `run_dist_s1_workflow(mgrs_tile_id='11SLT', post_date='2025-01-21', track_number=71)` per OPERA-ADT's official notebook recipe). Existing harness `download_reference_with_retry(source='CLOUDFRONT')` in place (Phase 1 ENV-06). |
| **DIST-02** | Config-drift gate extracts the OPERA v0.1 sample's 7 key processing parameters and compares against dist-s1 2.0.14 defaults. Material deltas → `cell_status='deferred pending operational reference publication'`. | Probes 1 + 2 — dist-s1 v2.0.14 `defaults.py` retrieved verbatim (37 constants); the OPERA v0.1 product is a **directory of GeoTIFFs** (not HDF5); no structured runconfig metadata is currently written to product tags. Plan-phase MUST treat the gate as comparing **dist-s1 2.0.14 defaults vs the explicit kwargs the OPERA-ADT sample notebook passes** — see Probe 1 for full strategy. |
| **DIST-03** | F1/precision/recall/accuracy with block-bootstrap 95% CI (1 km blocks, B=500). Matrix cell shows point estimate AND CI; criteria stay F1 > 0.80 + accuracy > 0.85 without tightening. | Probe 9 — `numpy.random.default_rng(seed=0)` (PCG64) confirmed as the modern NumPy-recommended RNG; Hall (1985) stationary-block bootstrap canonical; Lahiri (2003) full treatment. Pixel-coordinate-to-block-index calculation: T11SLT 109.8×109.8 km / 30 m posting = 3660×3660 pixels; 1 km / 30 m = 33-pixel blocks; ⌊3660/33⌋ = 110 full blocks per axis = 12100 full blocks (CONTEXT.md said "11881 ÷ 109" — that calc was off; D-08 numbers refresh below). |
| **DIST-04** | `make eval-dist-nam` includes a CMR probe for operational `OPERA_L3_DIST-ALERT-S1_V1`. Auto-supersede on discovery. | Probe 6 — `earthaccess.search_data(short_name='OPERA_L3_DIST-ALERT-S1_V1', bounding_box=..., temporal=...)` signature confirmed; `earthaccess.login(strategy='environment')` reads `EARTHDATA_USERNAME`/`EARTHDATA_PASSWORD` (already wired in v1.0 `run_eval_dist.py`). The collection short_name `OPERA_L3_DIST-ALERT-S1_V1` was probed in v1.0 (recorded in `run_eval_dist.py` lines 167-188) and returned EMPTY as of 2026-04-15 — operational not yet published. |
| **DIST-05** | EFFIS owslib WFS cross-validation. Precision > 0.70 AND recall > 0.50 against EFFIS burnt-area perimeters. | Probe 3 + 5 — owslib 0.35.0 is **noarch pure-Python** (PyPI + conda-forge confirmed); pip layer install in `pyproject.toml [validation]` extras is correct. Two candidate EFFIS WFS endpoints surfaced; plan-phase GetCapabilities-probes both and locks. |
| **DIST-06** | EU DIST coverage = 3 events (2024 Portuguese wildfires + 2023 Evros Greece + 2022 Romanian forest clear-cuts). Aggregate in `CONCLUSIONS_DIST_EU.md`. | Probe 4 + 8 — Aveiro 2024 well-documented (Sept 15-20, 135,000 ha; existing v1.0 scripts have AOI bbox); Evros 2023 EMS activation is **EMSR686** (NOT EMSR649 as CONTEXT.md stated — EMSR649 was an Italian flood). Romania 2022 EFFIS coverage **gap suspected** for clear-cuts; plan-phase ADR may substitute event. |
| **DIST-07** | After Phase 1 `_mp.py` bundle lands, chained `prior_dist_s1_product` retry on the Aveiro stack (Sep 28 → Oct 10 → Nov 15). Success = DIFFERENTIATOR; failure = upstream filing, non-blocking. | Probe 10 — `_mp.configure_multiprocessing()` confirmed landed at `src/subsideo/_mp.py:39` (idempotent + thread-safe; full bundle: MPLBACKEND + RLIMIT_NOFILE + fork/forkserver). Sept 28 + Nov 15 outputs cached under `eval-dist-eu/dist_output/` and `eval-dist-eu-nov15/dist_output/`. **Oct 10 run is MISSING** — that's the middle stage of the chained triple and must be added to the script. `prior_dist_s1_product` arg accepts `DistS1ProductDirectory | str | Path | None` per `runconfig_model.py`. |
</phase_requirements>

## Summary

Phase 5 is the **5th and final per-product validation phase** before the milestone-closure Phase 7. It is HEAVILY plan-phase-probe-driven — six of the ten probes have nontrivial-to-resolve answers and one (Romania 2022 EFFIS coverage) may force an event substitution at plan-phase.

The **biggest single research finding** is that the OPERA DIST-S1 product is a **directory of 11 GeoTIFFs (10 layers + browse PNG)** — NOT an HDF5 — with no canonical "v0.1 sample on CloudFront" URL. The "sample" is GENERATED locally via `run_dist_s1_workflow(mgrs_tile_id='11SLT', post_date='2025-01-21', track_number=71)` per OPERA-ADT's published notebook recipe. This means **DIST-01's "fetch via CloudFront" framing is structurally inconsistent with how the OPERA-ADT v0.1 sample actually works**. Plan-phase MUST resolve this — Probe 1 below proposes the resolution: subsideo runs `run_dist_s1_workflow` with the OPERA-ADT-published kwargs to *regenerate* the v0.1 sample under dist-s1 2.0.14 (which is *itself* the comparison baseline — meaning the F1 should be ~1.0 unless dist-s1 has version-drifted between when OPERA-ADT recorded the sample notebook and 2.0.14 today). The "config-drift gate" then compares **dist-s1 2.0.14 defaults against the explicit kwargs the sample notebook passes** (`post_date_buffer_days=1`, `device='cpu'`, `memory_strategy='high'`, plus any AlgoConfig overrides) — that is the actual material drift surface.

The **second biggest finding** is that `dist-s1 v2.0.14 defaults.py` is now retrieved verbatim from the v2.0.14 tag — 37 constants, none of which match CONTEXT.md's candidate names (`post_date_buffer_days`, `baseline_window_epochs`, `despeckle_window_pixels`, `confirmation_count_M_of_N`, `pre_image_strategy_literal`, `soil_moisture_filter_on_off`, `percolation_threshold` — six of these seven are NOT real keys in v2.0.14). The 7 actual config-drift keys are listed below in Probe 2.

The **third biggest finding** is that Evros 2023 EMS activation is **EMSR686**, not EMSR649 (CONTEXT.md error — EMSR649 was an Italian flood, not a Greek wildfire).

**Primary recommendation:** Plan-phase commits Probe 1 + Probe 2 + Probe 3 + Probe 4 outcomes WITH evidence as the FIRST plan in Wave 1 (an `00-probes-PLAN.md` artifact); these three probes have material answers that change downstream plans. Plans for `bootstrap.py`, `matrix_schema.py` extension, `harness.RETRY_POLICY['effis']` addition, and `compare_dist.py` extension can run in parallel in Wave 1 as written; eval-script rewrites land in Wave 3 once probes are committed.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| OPERA v0.1 sample regeneration (DIST-01) | dist-s1 product workflow (`subsideo.products.dist.run_dist`) | — | Sample is generated, not downloaded; uses same product code as actual eval. |
| CMR probe (DIST-04, Stage 0) | `run_eval_dist.py` (script) calling `earthaccess` lib | `subsideo.validation.harness.download_reference_with_retry(source='EARTHDATA')` for granule fetch on hit | Stage 0 is single-decision flow control; reuses harness retry policy on hit only. |
| Config-drift extraction (DIST-02) | `subsideo.validation.compare_dist` OR new `subsideo.validation.config_drift` (D-04 plan-phase decision) | `subsideo.validation.matrix_schema.ConfigDriftReport` for serialisation | Pure-Python introspection logic; no I/O beyond reading the v0.1 sample directory; lives in validation layer. |
| Block-bootstrap CI (DIST-03) | NEW `subsideo.validation.bootstrap` (D-06) | `subsideo.validation.metrics` consumed unchanged as `metric_fn` | Reusable methodology helper; pure-numpy; no rasterio/I/O. |
| EFFIS WFS download (DIST-05) | `subsideo.validation.harness.download_reference_with_retry(source='effis')` (NEW branch, D-18) | `owslib.wfs.WebFeatureService` invoked from harness | Network access centralised in harness; per-source retry policy is the harness's contract. |
| EFFIS rasterisation (DIST-05) | `run_eval_dist_eu.py` calling `geopandas.read_file` + `rasterio.features.rasterize` | — | Eval-script-local; one-shot transformation; no reuse beyond Phase 5. |
| 3-event orchestration (DIST-06) | `run_eval_dist_eu.py` (declarative `EVENTS: list[EventConfig]` per D-11) | Per-event try/except + per-stage `harness.ensure_resume_safe` (Phase 1 ENV-06) | Multi-event aggregation lives at script level; harness gives resume safety + isolation. |
| Chained retry (DIST-07) | `run_eval_dist_eu.py` aveiro event's `chained_run` post-stage (D-13) | `dist_s1.run_dist_s1_workflow(prior_dist_s1_product=...)` | Embedded in event entry; uses dist-s1 native API; pass criterion = `DistS1ProductDirectory.from_path()` loads + 10 layers. |
| Matrix rendering (DIST cells) | `subsideo.validation.matrix_writer._render_disp_cell`-pattern branch (NEW `_render_dist_*` for nam + eu) | `subsideo.validation.matrix_schema.DistNamCellMetrics` / `DistEUCellMetrics` (NEW) | Manifest-authoritative pattern (REL-02); insert AFTER `disp:*` BEFORE `dswx:*`. |
| Two CONCLUSIONS docs (D-22) | `CONCLUSIONS_DIST_N_AM.md` + `CONCLUSIONS_DIST_EU.md` (existing v1.0 files; v1.1 sub-sections appended) | — | Append-only narrative per Phase 4 D-13; v1.0 baseline preserved as preamble. |
| Methodology doc §4 (D-23) | `docs/validation_methodology.md` §4 (NEW append) | — | Phase-owned section per Phase 3 D-15 append-only. |

## Open Probes Resolved (1-10)

### Probe 1 — OPERA v0.1 HDF5 metadata extraction strategy (D-01)

**Question:** Where do the 7 config keys actually live in the v0.1 T11SLT HDF5? Structured attrs at `/science/.../productionParameters`? JSON-string-encoded? Sidecar XML? Partially missing?

**Evidence:**
- The OPERA DIST-S1 product is **NOT HDF5**. The product is a directory of 11 GeoTIFFs (10 layers + browse PNG) with names matching `EXPECTED_FORMAT_STRING = 'OPERA_L3_DIST-ALERT-S1_T{mgrs_tile_id}_{acq_datetime}_{proc_datetime}_S1_30_v{PRODUCT_VERSION}'` `[CITED: src/dist_s1/constants.py via raw.githubusercontent.com/opera-adt/dist-s1/main]`.
- The 10 layers are: `GEN-DIST-STATUS`, `GEN-METRIC`, `GEN-DIST-STATUS-ACQ`, `GEN-METRIC-MAX`, `GEN-DIST-CONF`, `GEN-DIST-DATE`, `GEN-DIST-COUNT`, `GEN-DIST-PERC`, `GEN-DIST-DUR`, `GEN-DIST-LAST-DATE` `[VERIFIED: TIF_LAYER_DTYPES dict in src/dist_s1/constants.py]`.
- Local v0.1 product directory `/Volumes/Geospatial/Geospatial/subsideo/eval-dist/dist_output/OPERA_L3_DIST-ALERT-S1_T10TFK_20240809T141544Z_20260415T174051Z_S1A_30_v0.1/` contains exactly 11 files matching the `EXPECTED_FORMAT_STRING` pattern with `_v0.1` suffix `[VERIFIED: ls listing]`.
- The OPERA-ADT v0.1 sample for T11SLT is **regenerated locally** by `run_dist_s1_workflow(mgrs_tile_id='11SLT', post_date='2025-01-21', track_number=71, post_date_buffer_days=1, device='cpu', memory_strategy='high', dst_dir=Path('los-angeles'))` per the OPERA-ADT notebook `notebooks/A__E2E_Workflow_Demo.ipynb` Cell 5 + Cell 7 `[CITED: raw.githubusercontent.com/opera-adt/dist-s1/main/notebooks/A__E2E_Workflow_Demo.ipynb]`.
- There is **no canonical CloudFront URL for the v0.1 T11SLT sample**. Web search returned only OPERA documentation PDFs at `d2pn8kiwq2w21t.cloudfront.net/documents/...` — no published `.tif` or `.zip` sample bundle.

**Recommendation (Probe 1 RESOLUTION — major restructuring):**

The "config-drift gate" structurally cannot work as CONTEXT.md frames it (extracting embedded config from a downloaded sample HDF5). The OPERA-ADT v0.1 **sample is not a downloadable HDF5 with embedded config metadata** — it's a notebook recipe that *regenerates* the product locally using whichever dist-s1 version is installed.

The correct interpretation of DIST-02:

1. **The "v0.1 reference"** = the product produced by running `run_dist_s1_workflow(...)` with the OPERA-ADT sample notebook's explicit kwargs `[CITED: A__E2E_Workflow_Demo.ipynb Cell 5]`:
   - `mgrs_tile_id = '11SLT'` (no T prefix)
   - `post_date = '2025-01-21'`
   - `track_number = 71`
   - `post_date_buffer_days = 1`
   - `device = 'cpu'` (forced because MPS doesn't support multiprocessing)
   - `memory_strategy = 'high'`
2. **The "subsideo prediction"** = the product produced by subsideo's `run_dist(mgrs_tile='11SLT', post_date='2025-01-21', ...)` calling the same `run_dist_s1_workflow` under the same dist-s1 2.0.14 — but using **whatever defaults subsideo's wrapper passes** (currently `post_date_buffer_days=5` per `run_eval_dist.py:110`, which is the v1.0 v0.1 customisation).
3. **The "config-drift gate"** = *compares the kwargs the OPERA-ADT sample notebook explicitly passes* (the published recipe) **against the kwargs subsideo's eval script passes** — both then realise on top of dist-s1 2.0.14 defaults. The "drift" is at the application level, not at the product-metadata level.
4. **Minor extraction step:** since the OPERA v0.1 product directory is GeoTIFF, plan-phase can ALSO probe whether the GeoTIFF tags carry any kwargs via `rasterio.open(...).tags()` — these tags are written by subsideo's `_metadata.py::inject_opera_metadata` per `run_eval_dist.py:362-373` (see the existing `inject_opera_metadata(...run_params={...})` call). This is a sanity check for kwargs round-tripping; drift detection against another product's tags would only work if the OPERA-ADT sample regeneration uses the same `inject_opera_metadata` step (it does, since OPERA-ADT's notebook calls `run_dist_s1_workflow` which eventually uses dist-s1's own metadata injection — different code path).

**Concrete extraction code (probe-it-and-decide; <30 LOC, fits D-04 "extend `compare_dist.py`" branch):**

```python
# subsideo/validation/compare_dist.py (additive)
from typing import TypedDict, Literal

class KeyDelta(TypedDict):
    key_name: str
    opera_v01_value: str | int | float | None  # from OPERA-ADT sample notebook
    dist_s1_2014_value: str | int | float | None  # from defaults.py
    equal: bool
    note: str

# OPERA-ADT v0.1 sample notebook explicit kwargs (CITED: A__E2E_Workflow_Demo.ipynb Cell 5+7)
OPERA_V01_SAMPLE_KWARGS: dict[str, object] = {
    'post_date_buffer_days': 1,
    'memory_strategy': 'high',
    'device': 'cpu',
    # All other params NOT explicitly set in the sample notebook → fall to dist-s1 defaults.
}

# dist-s1 2.0.14 defaults that we'd compare against (subset of defaults.py constants)
# Plan-phase commits this 7-key list — see Probe 2 below.
DIST_S1_2014_DEFAULTS_OF_INTEREST: dict[str, object] = {
    'post_date_buffer_days': 1,            # DEFAULT_POST_DATE_BUFFER_DAYS
    'lookback_strategy': 'multi_window',   # DEFAULT_LOOKBACK_STRATEGY
    'n_anniversaries_for_mw': 3,           # DEFAULT_N_ANNIVERSARIES_FOR_MW
    'delta_window_days': 60,               # DEFAULT_DELTA_WINDOW_DAYS
    'apply_despeckling': True,             # DEFAULT_APPLY_DESPECKLING
    'low_confidence_alert_threshold': 2.5, # DEFAULT_LOW_CONFIDENCE_ALERT_THRESHOLD
    'high_confidence_alert_threshold': 4.5,# DEFAULT_HIGH_CONFIDENCE_ALERT_THRESHOLD
}

def extract_v01_config_drift(
    opera_v01_kwargs: dict[str, object],
    dist_s1_2014_defaults: dict[str, object],
) -> list[KeyDelta]:
    """Compare the OPERA v0.1 sample notebook's explicit kwargs against
    dist-s1 2.0.14 defaults. Both inputs are explicit dicts (no introspection
    of a downloaded HDF5 product — the v0.1 sample is regenerated locally).
    """
    deltas: list[KeyDelta] = []
    keys = set(opera_v01_kwargs) | set(dist_s1_2014_defaults)
    for k in sorted(keys):
        opera_v = opera_v01_kwargs.get(k, dist_s1_2014_defaults.get(k))
        ds_v = dist_s1_2014_defaults.get(k, opera_v)
        deltas.append(KeyDelta(
            key_name=k,
            opera_v01_value=opera_v,  # type: ignore[typeddict-item]
            dist_s1_2014_value=ds_v,  # type: ignore[typeddict-item]
            equal=(opera_v == ds_v),
            note='OPERA-ADT sample notebook kwarg' if k in opera_v01_kwargs else 'dist-s1 2.0.14 default',
        ))
    return deltas
```

This brings the entire helper to ~25 LOC — fits the D-04 "<50 LOC → extend compare_dist.py" branch.

**Open risks:**
- **Risk A:** If OPERA-ADT publishes updated kwargs in a future notebook commit, subsideo's hardcoded `OPERA_V01_SAMPLE_KWARGS` drifts silently. Mitigation: pin the notebook commit SHA in the docstring; matrix_writer can echo the SHA in `meta.json`.
- **Risk B:** If a future operational publication ships a different set of explicit kwargs in OPERA-ADT product-spec ATBD, the gate-key list (Probe 2 below) becomes stale. Mitigation: the gate is a v1.1 artefact; v2 work re-derives from operational ATBD.
- **Risk C:** If plan-phase wants tag-level extraction *as well*, `rasterio.open(...).tags()` round-trips whatever subsideo's `inject_opera_metadata` wrote — but this gives subsideo's OWN run_params dict back, not OPERA-ADT's. So tag-level extraction is NOT useful for drift detection; only the explicit kwargs comparison works.

### Probe 2 — dist-s1 2.0.14 default config — exact 7-key list (D-02)

**Question:** What 7 config keys are material to the F1 outcome? CONTEXT.md candidates: `confirmation_count_M_of_N`, `pre_image_strategy_literal`, `post_date_buffer_days`, `baseline_window_epochs`, `despeckle_window_pixels`, `soil_moisture_filter_on_off`, `percolation_threshold`. Cite exact file:line.

**Evidence (verbatim from dist-s1 v2.0.14 tag):**

`[VERIFIED: raw.githubusercontent.com/opera-adt/dist-s1/v2.0.14/src/dist_s1/data_models/defaults.py]`

```python
# Algorithm enumeration (curating the baseline)
DEFAULT_LOOKBACK_STRATEGY = 'multi_window'           # line 18
DEFAULT_MAX_PRE_IMGS_PER_BURST_MW = None             # line 19 (auto-calculated)
DEFAULT_DELTA_LOOKBACK_DAYS_MW = None                # line 20 (auto-calculated)
DEFAULT_POST_DATE_BUFFER_DAYS = 1                    # line 21  ← drifts vs subsideo's 5 (run_eval_dist.py:110)
DEFAULT_N_ANNIVERSARIES_FOR_MW = 3                   # line 22
DEFAULT_DELTA_WINDOW_DAYS = 60                       # line 23

# Despeckling
DEFAULT_INTERPOLATION_METHOD = 'bilinear'            # line 26
DEFAULT_APPLY_DESPECKLING = True                     # line 27

# Alert thresholds (the F1-material ones for backscatter-change)
DEFAULT_LOW_CONFIDENCE_ALERT_THRESHOLD = 2.5         # line 47
DEFAULT_HIGH_CONFIDENCE_ALERT_THRESHOLD = 4.5        # line 48

# Confirmation
DEFAULT_NO_DAY_LIMIT = 30                            # line 51
DEFAULT_PERCENT_RESET_THRESH = 50                    # line 53
DEFAULT_NO_COUNT_RESET_THRESH = 10                   # line 56
DEFAULT_N_CONFIRMATION_OBSERVATIONS = 3              # line 64

# Model
DEFAULT_MODEL_SOURCE = 'transformer_optimized'       # line 33
DEFAULT_MODEL_DTYPE = 'float32'                      # line 38
DEFAULT_APPLY_LOGIT_TO_INPUTS = True                 # line 36
```

**Recommendation — Plan-phase locks the 7-key list as follows:**

| # | Key | dist-s1 2.0.14 default | OPERA-ADT sample notebook | F1 material? | Rationale |
|---|-----|-------------------------|---------------------------|---|---|
| 1 | `post_date_buffer_days` | `1` | `1` (explicit) | YES | Subsideo currently passes `5` (`run_eval_dist.py:110`). The 1-vs-5 difference changes the post-image window — directly affects which post-images are available, directly affects detected disturbance footprint. **THIS IS THE PRIMARY DRIFT KEY.** |
| 2 | `lookback_strategy` | `'multi_window'` | (default) | YES | Switching from multi_window to a single-window strategy materially changes the baseline. |
| 3 | `n_anniversaries_for_mw` | `3` | (default) | YES | Number of yearly anniversaries to use as baseline. Direct effect on temporal sample size of the reference distribution. |
| 4 | `low_confidence_alert_threshold` | `2.5` | (default) | YES | Determines whether a metric value triggers a low-confidence alert — direct binary classification threshold. |
| 5 | `high_confidence_alert_threshold` | `4.5` | (default) | YES | Determines whether a metric value triggers a high-confidence alert — direct binary classification threshold. |
| 6 | `n_confirmation_observations` | `3` | (default) | YES | M-of-N confirmation logic — affects which "first detection" alerts get promoted to confirmed. Maps to CONTEXT.md's "confirmation_count_M_of_N" candidate (different name in 2.0.14). |
| 7 | `apply_despeckling` | `True` | (default) | YES | TBPF despeckling on/off changes the noise floor on the metric layer — directly affects threshold crossings. |

**Replacement for CONTEXT.md candidates that don't exist in v2.0.14:**

| CONTEXT.md candidate | v2.0.14 reality | Note |
|---------------------|-----------------|------|
| `confirmation_count_M_of_N` | `n_confirmation_observations = 3` (not "M of N"; just N count) | Renamed |
| `pre_image_strategy_literal` | `lookback_strategy = 'multi_window'` (only one valid pattern in v2.0.14: `^multi_window$`) | Renamed; only one allowed value in 2.0.14 |
| `baseline_window_epochs` | `n_anniversaries_for_mw = 3` + `delta_window_days = 60` (paired) | Decomposed into 2 scalars |
| `despeckle_window_pixels` | NOT a public config in v2.0.14; `DEFAULT_INTERPOLATION_METHOD='bilinear'` is the closest exposed knob | Internal to TBPF |
| `soil_moisture_filter_on_off` | DOES NOT EXIST in v2.0.14 | dist-s1 v2.x is transformer-based; soil moisture filter was a v1.x heuristic that's gone |
| `percolation_threshold` | DOES NOT EXIST in v2.0.14 | Was a v1.x morphological cleanup; not exposed as a config |
| `post_date_buffer` | `post_date_buffer_days` (exact) | OK |

**Open risks:**
- **Risk D:** Plan-phase may re-derive the 7-key list differently if a deeper inspection of `algoconfig_model.py` validation rules reveals more material knobs. The 7 above are conservative — *the items where a 1-step change demonstrably changes F1*.
- **Risk E:** If the OPERA operational publishes with updated v2.x defaults that drift from 2.0.14, the gate becomes meaningful immediately. (Currently moot — operational not published.)

### Probe 3 — EFFIS WFS endpoint URL + layer name + filter syntax (D-18, D-19)

**Question:** What is the exact WFS `WebFeatureService(url=..., version='2.0.0')` instantiation? What is the layer name? What is the date-filter property?

**Evidence:**

Two competing endpoints surfaced — plan-phase MUST `GetCapabilities`-probe both and lock:

**Candidate A (BurntAreas via MapServer; from `forest-fire.emergency.copernicus.eu/applications/data-and-services` data-and-services page):** `[VERIFIED: WebFetch returned this URL pattern verbatim]`
```
URL:       https://maps.effis.emergency.copernicus.eu/effis
Layer:     ms:modis.ba.poly
Format:    application/x-shapezip (SHAPEZIP) or x-spatialitezip (SPATIALITEZIP)
Recipe:    https://maps.effis.emergency.copernicus.eu/effis?service=WFS&request=getfeature&typename=ms:modis.ba.poly&version=1.1.0&outputformat=SHAPEZIP
```

**Candidate B (BurntAreas via GeoServer; from `directory.spatineo.com/service/328`):** `[VERIFIED: WebFetch returned the layer list]`
```
URL:       http://geohub.jrc.ec.europa.eu:80/effis/wms
Layers:    EFFIS:BurntAreasAll, EFFIS:BurntAreas7Days, EFFIS:BurntAreas30Days
Format:    WMS only? (Spatineo lists this as WMS; WFS support may be parallel at /effis/wfs)
```

**Property names for date filtering (R `effisr` package and EFFIS user guide concur):** `[CITED: github.com/patperu/effisr/blob/master/R/ef_current.R; web search "EFFIS WFS firedate"]`
- `firedate` — fire ignition date (or detection date for MODIS-derived) — string ISO-8601 or `YYYY-MM-DD`.
- `area_ha` — burnt area in hectares.
- `country` — country code.
- `province` — administrative province.
- `commune` — administrative commune.

The R `effisr` package uses a **REST API** at `rest/2/burntareas/current` rather than WFS; WFS-vs-REST distinction matters for owslib usage (REST returns JSON; WFS returns GML/SHAPEZIP/SPATIALITEZIP).

**owslib WFS recipe (canonical, via Context7 `/geopython/owslib`):** `[VERIFIED: ctx7 query]`

```python
from owslib.wfs import WebFeatureService
from owslib.fes import And, BBox, PropertyIsBetween, PropertyIsLike
from owslib.etree import etree
from owslib.fes2 import Filter as Filter2  # WFS 2.0.0 wraps in Filter

# Per-event WFS query (Aveiro example)
wfs = WebFeatureService(
    url='https://maps.effis.emergency.copernicus.eu/effis',
    version='2.0.0',
)
# Aveiro 2024 fires: bbox (-8.8, 40.5, -8.2, 41.0); dates 2024-09-15 → 2024-09-20
filter_xml = etree.tostring(Filter2(And([
    BBox([-8.8, 40.5, -8.2, 41.0], 'urn:ogc:def:crs:EPSG::4326'),
    PropertyIsBetween(propertyname='firedate',
                      lower='2024-09-15', upper='2024-09-20'),
])).toXML()).decode('utf-8')
response = wfs.getfeature(typename='ms:modis.ba.poly', filter=filter_xml)
# response is a file-like object with GML or SHAPEZIP body
gdf = geopandas.read_file(BytesIO(response.read()))  # geopandas auto-detects GML
```

**Recommendation:**

Plan-phase MUST run a real `GetCapabilities` probe of BOTH endpoints (using `owslib.wfs.WebFeatureService(url='...', version='2.0.0').contents` to list available types) and pick whichever has a layer that:
1. Covers the 3 target events (Aveiro 2024 + Evros 2023 + Romania 2022 — see Probe 4 for Romania's gap).
2. Exposes a usable date property name (likely `firedate` per `effisr`).
3. Returns features (not just a layer-list metadata schema).

The data-and-services page recipe (Candidate A) is more recently documented (2025) and explicitly mentions `ms:modis.ba.poly` with SHAPEZIP/SPATIALITEZIP outputs. **Recommended starting point: Candidate A.**

If Candidate A's `ms:modis.ba.poly` is MODIS-only (250 m), the spatial-resolution mismatch with subsideo DIST-S1 (30 m) is a known PITFALLS P4.4 issue (rasterisation choice). EFFIS *also* publishes Sentinel-2-derived 20 m perimeters since 2018 per the EFFIS technical-background page; plan-phase probes whether these are exposed via WFS as a separate layer (e.g., `EFFIS:BurntAreasS2` — speculation; verify via GetCapabilities).

**Open risks:**
- **Risk F:** EFFIS may rate-limit the `getfeature` endpoint; harness retry policy must include `429` retryable + `503` retryable + `401`/`403` aborting (mirrors CDSE/Earthdata policies).
- **Risk G:** EFFIS may return GML (default) rather than SHAPEZIP; `geopandas.read_file(BytesIO(resp.read()))` should handle both via fiona/pyogrio; plan-phase tests this.

### Probe 4 — EFFIS coverage of clear-cut / non-fire forestry events (D-19, PITFALLS P4.5)

**Question:** Does EFFIS cover Romania 2022 forest clear-cuts at all? If not, propose alternatives or substitution.

**Evidence:**

EFFIS is **fire-only**. The R `effisr` package documentation, the EFFIS technical-background page, and the data-and-services page all describe burnt-area perimeters from **MODIS fire-detection** (or Sentinel-2 fire-detection, post-2018). PITFALLS P4.5 explicitly states: "DIST-S1 detects clear-cut logging in unburnt forest — not in EFFIS perimeters." `[CITED: .planning/research/PITFALLS.md §P4.5 line 577]`

**Romania 2022 events that MIGHT be in EFFIS:**
- Romania 2022 had **162,518 ha of vegetation fires** per EFFIS itself (second most in Europe that year). `[CITED: WebSearch "Romania 2022 wildfires", europeandatajournalism.eu/cp_data_news]`
- The **forest** fire area was 13,141 ha (1019 fires) — largest forest burn since 1956.
- EMSR012 ("Fires in Romania") is a Copernicus EMS activation but predates 2022 (the EMSR012 page identifier is a 2010 activation per `emergency.copernicus.eu/mapping/list-of-components/EMSR012` URL pattern — NOT a 2022 event).
- GDACS reports a "Romania wildfires" event with eventid 1005046 spanning 2022-03-20 to 2022-03-28 — likely a ground/grassland fire complex.

**Recommendation:**

CONTEXT.md says "Romania 2022 forest clear-cuts" — interpreting literally, **EFFIS will NOT have these as fire perimeters**. Plan-phase has three options:

1. **Substitute event:** swap Romania 2022 clear-cuts → Romania 2022 wildfires (e.g., the GDACS-flagged March 2022 event; or another large fire event from EFFIS's 162,518 ha). Pick a fire event with material burnt area in EFFIS to test EFFIS coverage at-spec, not against the wrong reference. **(Recommended.)**
2. **Substitute reference:** keep Romania 2022 clear-cuts but use a different reference (JRC Global Forest Cover Change products, Global Forest Watch). This breaks the Phase 5 "EFFIS as same-resolution reference" assumption and requires a new harness branch.
3. **Substitute country:** swap Romania 2022 → another EU 2022 event with strong EFFIS coverage (e.g., Spain's Sierra de la Culebra fire June 2022, ~26,000 ha). Maintains "3 events" structural commitment.

**Plan-phase ADR required.** Surface this as a HIGH-priority probe at start of Wave 1 — the EVENTS list in `run_eval_dist_eu.py` (D-11) cannot be locked until this resolves.

**Open risks:**
- **Risk H:** If plan-phase keeps Romania 2022 clear-cuts AND EFFIS doesn't cover them, recall will be ~0 and the cell will FAIL on a class-mismatch — exactly the wrong signal. M1 anti-target-creep concern.

### Probe 5 — owslib version + install location (D-18)

**Question:** Pin `owslib==0.35.0`. Verify pure-Python (pip layer fine) vs C extensions (conda-forge needed).

**Evidence:**
- PyPI: `owslib 0.35.0`, released 2025-10-28, `requires_python>=3.10`, classifiers list **no C extensions** (`Programming Language :: Python` only). `[VERIFIED: pypi.org/pypi/owslib/json]`
- conda-forge: `owslib 0.35.0`, **noarch** platform = pure-Python no native binaries. `[VERIFIED: anaconda.org/conda-forge/owslib]`

**Recommendation:**

Add `owslib>=0.35,<1` to `pyproject.toml [project.optional-dependencies] validation` extras (NOT to `conda-env.yml` heavy-deps). The pip layer in `conda-env.yml` already uses `pip: -e .[validation,viz]` so the pip install lands automatically.

```toml
# pyproject.toml [project.optional-dependencies] validation:
validation = [
    "opera-utils[disp]>=0.25",
    "pandas>=2.2",
    "scikit-image>=0.22",
    "statsmodels>=0.14",
    "owslib>=0.35,<1",                  # NEW: Phase 5 EFFIS WFS access
    # "EGMStoolkit @ git+https://...",  # already commented
]
```

**Open risks:** none — owslib is well-maintained and `noarch` is stable across all subsideo platforms (macOS arm64 + Linux x86-64).

### Probe 6 — earthaccess CMR query for OPERA_L3_DIST-ALERT-S1_V1 (D-15)

**Question:** Exact `earthaccess.search_data(...)` snippet. Auth path. Confirm collection short_name. Bounding box for T11SLT.

**Evidence:**
- `earthaccess.search_data(short_name='X', bounding_box=(w,s,e,n), temporal=(start, end), count=N)` confirmed canonical signature `[VERIFIED: ctx7 /nsidc/earthaccess query]`.
- `earthaccess.login(strategy='environment')` reads `EARTHDATA_USERNAME` + `EARTHDATA_PASSWORD` env vars; alternative strategies are `netrc` (`~/.netrc`) and `interactive`. `[VERIFIED: ctx7]`
- v1.0 `run_eval_dist.py` already calls `earthaccess.search_data(short_name='OPERA_L3_DIST-ALERT-S1_V1', ...)` at lines 167-188 with EMPTY result as of 2026-04-15 (probe-comment in script). `[VERIFIED: run_eval_dist.py:167-188]`
- The collection short_name `OPERA_L3_DIST-ALERT-S1_V1` is the canonical operational collection name; v0.1 / pre-operational has no CMR collection.

**MGRS T11SLT bounding box (UTM zone 11N, southern California / LA):**
- T11SLT is an MGRS-100km tile in zone 11S (southern California, ~33-34°N).
- Approximate WGS84 bbox: `(-119.0, 33.5, -118.0, 34.5)` covers the LA-Santa-Monica-mountains region where the Jan 2025 fires (Palisades + Eaton) burnt.
- Exact bbox to be derived via `harness.bounds_for_mgrs_tile('11SLT')` — already wired in v1.0 `run_eval_dist.py` import at line 85.

**Recommendation (canonical Stage 0 snippet):**

```python
# run_eval_dist.py — Stage 0 (NEW; replaces v1.0 Stage 2 search-only flow)
import earthaccess
from datetime import datetime, timedelta

CMR_TEMPORAL_TOLERANCE_DAYS = 7  # ±days around 2025-01-21
POST_DATE = '2025-01-21'
MGRS_TILE = '11SLT'

# Auth
earthaccess.login(strategy='environment')  # EARTHDATA_USERNAME/PASSWORD

# Bounding box from harness (no hand-coded literals — ENV-08)
bbox = bounds_for_mgrs_tile(MGRS_TILE)  # (-119.0, 33.5, -118.0, 34.5) approx

# Temporal window
post_dt = datetime.fromisoformat(POST_DATE)
temporal = (
    (post_dt - timedelta(days=CMR_TEMPORAL_TOLERANCE_DAYS)).strftime('%Y-%m-%d'),
    (post_dt + timedelta(days=CMR_TEMPORAL_TOLERANCE_DAYS)).strftime('%Y-%m-%d'),
)

# Probe operational
results = earthaccess.search_data(
    short_name='OPERA_L3_DIST-ALERT-S1_V1',
    bounding_box=bbox,
    temporal=temporal,
    count=20,
)

if results:
    # ON HIT: download + use as reference
    reference_source = 'operational_v1'
    # earthaccess.download(results, str(ref_dir))  # delegates to harness for retry
    ...
else:
    # ON MISS: regenerate v0.1 sample locally per Probe 1 strategy
    reference_source = 'v0.1_cloudfront'  # legacy literal; semantically "regenerated locally"
    ...
```

**Open risks:**
- **Risk I:** `±7 days` is narrow for orbit-pass uncertainty; if the operational granule's `BeginningDateTime` is more than 7 days off the post_date sensing time (unlikely for OPERA which targets specific MGRS+post_date triples), the probe misses. Plan-phase may want ±14 days. Conservative recommendation: ±7 (matches T11SLT's 12-day Sentinel-1 cycle + 1 day slop).

### Probe 7 — CloudFront URL pattern for v0.1 T11SLT sample (DIST-01)

**Question:** Resolve the canonical URL. Confirm HEAD pre-flight + Range support.

**Evidence:** **There is no canonical CloudFront URL for the v0.1 T11SLT sample.** The web search and OPERA-ADT README review returned only OPERA documentation PDFs at `d2pn8kiwq2w21t.cloudfront.net/documents/...` — none host the actual `.tif` product files. `[VERIFIED: WebSearch + WebFetch on github.com/opera-adt/dist-s1/README.md]`

The OPERA-ADT recipe is to **regenerate the sample locally** by running `run_dist_s1_workflow(mgrs_tile_id='11SLT', ...)` per the published `notebooks/A__E2E_Workflow_Demo.ipynb` Cell 5 + Cell 7. `[CITED: A__E2E_Workflow_Demo.ipynb]`

**Recommendation:**

DIST-01's "fetched via CloudFront direct-download with exponential-backoff retry" is structurally inapplicable. Plan-phase has two options:

1. **Reframe DIST-01 as "regenerate via run_dist_s1_workflow with OPERA-ADT-published kwargs" — preserve the `eval-dist/opera_reference/v0.1_T11SLT/` cache directory but populate it via `run_dist_s1_workflow`, NOT via download.** The "exponential-backoff retry" then applies to the dist-s1 workflow's *internal* RTC fetch from ASF DAAC (already retried by the harness via Earthdata path).
2. **If a future OPERA-ADT publishes a stable URL for the v0.1 sample (e.g., `s3://opera-pst-prod-validation-products/...`), update.** This is opportunistic; the URL doesn't currently exist.

The harness `download_reference_with_retry(source='CLOUDFRONT')` is already in place (Phase 1 ENV-06; verified at `harness.py:496-627`) and remains useful for OTHER references that may use CloudFront-signed URLs (e.g., if EMS publishes via CloudFront in the future). Phase 5 keeps the harness branch but doesn't exercise it for DIST-01.

**Open risks:**
- **Risk J:** This is a structural reframing of DIST-01. Plan-phase MUST surface this in a probe-report sub-section so milestone close-out doesn't expect a CloudFront download path that never existed.

### Probe 8 — Aveiro / Evros / Romania exact AOIs + dates

**Question:** Aveiro details exist in v1.0; Evros (EMSR649) and Romania need fresh research.

**Evidence:**

**Aveiro 2024:** `[VERIFIED: run_eval_dist_eu.py:88-95 + WebSearch 2024 Portugal wildfires]`
- AOI: Aveiro/Viseu district, Portugal; centroid ~40.75°N, 8.48°W
- bbox: `(-8.8, 40.5, -8.2, 41.0)` (EPSG:4326)
- MGRS: `29TNF` (UTM 29N / EPSG:32629)
- Track: 147 (ascending, ~18:28 UTC)
- Sensing dates of interest: Sep 28 (post +13d), Oct 10 (post +25d), Nov 15 (post +61d) — chained retry triple
- Fire dates: 2024-09-15 to 2024-09-20 (135,000 ha total)

**Evros 2023:** `[VERIFIED: WebSearch + Wikipedia "2023 Greece wildfires"]`
- **EMS activation = EMSR686, NOT EMSR649** (CONTEXT.md error — EMSR649 was an Italian flood per `emergency.copernicus.eu/mapping/list-of-components/EMSR649`).
- AOI: Evros region, Aristino village near NE Greek-Turkish border
- bbox candidate: `(25.9, 40.7, 26.7, 41.4)` (EPSG:4326) — covers Alexandroupolis area
- MGRS candidates: `35TLF` or `35TMF` or `35TKF` (UTM 35N / EPSG:32635) — plan-phase probes via `dist_s1_enumerator.get_mgrs_tiles_overlapping_geometry`
- Fire dates: 2023-08-19 to 2023-09-08 (94,250 ha — largest forest fire ever recorded in EU)
- Suggested post_date: ~2023-09-15 (~7 days after declared extinguished); buffer 5 days; track candidate to be probed

**Romania 2022:** plan-phase ADR required (Probe 4) — see substitution options. Tentative substitute for EFFIS coverage:
- **Romania March 2022 wildfire complex** (GDACS event 1005046): 2022-03-20 to 2022-03-28; widespread small-fire complex, hard to map as single AOI.
- **Spain Sierra de la Culebra June 2022** (alternative): 2022-06-15 to 2022-06-21; Zamora province; ~26,000 ha; bbox approx `(-6.5, 41.7, -5.9, 42.2)`; MGRS `29TQG`/`29TQH`/`30TUM`. **Strong recommendation.**

**Recommendation:**

Plan-phase EVENTS list:
```python
EVENTS = [
    EventConfig(
        event_id='aveiro',
        post_dates=[date(2024, 9, 28), date(2024, 10, 10), date(2024, 11, 15)],
        aoi_bbox_wgs84=(-8.8, 40.5, -8.2, 41.0),
        mgrs_tile='29TNF',
        track_number=147,
        effis_filter_dates=(date(2024, 9, 15), date(2024, 9, 25)),
        run_chained=True,
    ),
    EventConfig(
        event_id='evros',
        post_dates=[date(2023, 9, 5)],  # ~17 days after fire onset; 2nd post-fire S1 acq
        aoi_bbox_wgs84=(25.9, 40.7, 26.7, 41.4),
        mgrs_tile='35TLF',  # plan-phase confirms via enumerator probe
        track_number=None,  # plan-phase probes
        effis_filter_dates=(date(2023, 8, 19), date(2023, 9, 8)),
        run_chained=False,
    ),
    EventConfig(
        event_id='spain_culebra',  # or 'romania_2022' if plan-phase keeps Romania
        post_dates=[date(2022, 6, 28)],
        aoi_bbox_wgs84=(-6.5, 41.7, -5.9, 42.2),
        mgrs_tile='29TQG',  # plan-phase confirms
        track_number=None,
        effis_filter_dates=(date(2022, 6, 15), date(2022, 6, 22)),
        run_chained=False,
    ),
]
```

**Open risks:**
- **Risk K:** Evros 2023 specific MGRS tile + track + post_date triple needs `dist_s1_enumerator` probe at plan-phase. EMSR686 docs may yield AOI WKT directly; preferable to inferring.
- **Risk L:** Romania substitution decision is a material plan-phase ADR; the chosen event MUST be both DIST-pipeline-runnable (RTC inputs available; track coverage; post_date in S1 cycle) AND have EFFIS coverage. Spain Culebra fits both.

### Probe 9 — block-bootstrap reference + numerical conventions (D-06..D-09)

**Question:** Hall (1985) stationary block bootstrap; Lahiri (2003); confirm numpy.random.default_rng (PCG64) preferred over RandomState; pixel-coordinate-to-block-index calculation; verify implementation pattern.

**Evidence:**
- `numpy.random.default_rng(seed)` returns a `Generator` backed by **PCG64** — the modern best-practice; `numpy.random.RandomState(seed)` (Mersenne Twister) is **legacy** with stronger version-stability guarantees but slower (~40% slower) and statistically inferior. Recommendation: PCG64 for new code. `[CITED: numpy.org/doc/stable/reference/random/generator.html; blog.scientific-python.org/numpy/numpy-rng/]`
- Hall (1985) introduced spatial block bootstrap; Lahiri (2003) "Resampling Methods for Dependent Data" Ch.7-8 is the canonical reference for stationary/moving-block schemes. `[CITED: bashtage.github.io/kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Lahiri_2and7.pdf]`
- T11SLT MGRS-100km tile: 109.8 km × 109.8 km. At 30 m posting: 3660 × 3660 pixels = 13,395,600 total pixels.

**Pixel-coordinate-to-block-index calculation (CORRECTED from CONTEXT.md D-08):**

```
block_size_m = 1000
pixel_size_m = 30
pixels_per_block_axis = floor(block_size_m / pixel_size_m) = floor(33.33) = 33  # full-block rule
n_blocks_per_axis = floor(3660 / 33) = 110
n_full_blocks_2d = 110 × 110 = 12,100  # NOT 11,881 as CONTEXT.md said

# Drop partial blocks (D-08):
n_pixels_in_full_blocks = 110 * 33 = 3,630 (per axis)
n_pixels_in_partial_blocks = 3660 - 3630 = 30 (per axis)
total_pixels_full = 3,630 × 3,630 = 13,176,900
total_pixels_partial = 13,395,600 - 13,176,900 = 218,700
fraction_dropped = 218,700 / 13,395,600 ≈ 1.6%   # NOT 3.7% as CONTEXT.md said
n_dropped_blocks = (110 + 1) * (110 + 1) - 110*110 = 12321 - 12100 = 221  # the L-shaped strip
```

CONTEXT.md D-08 said `109 × 109 = 11881 full blocks + ~436 partial`. That's based on `floor(109.8 km / 1 km) = 109` axis blocks. The discrepancy: with `pixels_per_block_axis = 33` (which is `floor(1000/30)`), you actually get **110 blocks per axis**, not 109. CONTEXT.md slightly under-counted. Plan-phase commits the corrected numbers.

**Recommendation:**

```python
# subsideo/validation/bootstrap.py (NEW, D-06)
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

import numpy as np

DEFAULT_BLOCK_SIZE_M: int = 1000
DEFAULT_N_BOOTSTRAP: int = 500
DEFAULT_RNG_SEED: int = 0
DEFAULT_CI_LEVEL: float = 0.95
DEFAULT_PIXEL_SIZE_M: int = 30


@dataclass(frozen=True)
class BootstrapResult:
    point_estimate: float
    ci_lower: float
    ci_upper: float
    n_blocks_kept: int
    n_blocks_dropped: int
    n_bootstrap: int
    ci_level: float
    rng_seed: int


def block_bootstrap_ci(
    predictions: np.ndarray,
    references: np.ndarray,
    metric_fn: Callable[[np.ndarray, np.ndarray], float],
    *,
    block_size_m: int = DEFAULT_BLOCK_SIZE_M,
    pixel_size_m: int = DEFAULT_PIXEL_SIZE_M,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
    ci_level: float = DEFAULT_CI_LEVEL,
    rng_seed: int | None = DEFAULT_RNG_SEED,
) -> BootstrapResult:
    """Hall (1985) stationary block bootstrap on a 2-D raster pair.

    Drops partial blocks at tile edges (D-08); resamples full block-indices
    with replacement; computes metric_fn over the union of resampled blocks'
    pixels for each of n_bootstrap iterations; returns 2.5/97.5 percentile
    CI bounds (95% CI default).

    Both arrays must have shape (H, W) and identical dtype/shape. NaNs
    propagate to the metric_fn (which masks internally).
    """
    assert predictions.shape == references.shape
    assert predictions.ndim == 2
    H, W = predictions.shape
    px_per_block = block_size_m // pixel_size_m  # 33 for 1km/30m
    n_block_rows = H // px_per_block
    n_block_cols = W // px_per_block
    n_blocks_kept = n_block_rows * n_block_cols
    # Partial-block count: edges + corner
    n_blocks_dropped = (n_block_rows + 1) * (n_block_cols + 1) - n_blocks_kept

    # Pre-compute block-index offsets for fast resampling
    rng = np.random.default_rng(rng_seed)
    block_ids = np.arange(n_blocks_kept).reshape(n_block_rows, n_block_cols)

    # Point estimate
    pred_full = predictions[: n_block_rows * px_per_block, : n_block_cols * px_per_block]
    ref_full = references[: n_block_rows * px_per_block, : n_block_cols * px_per_block]
    point = metric_fn(pred_full.ravel(), ref_full.ravel())

    # Bootstrap loop
    bootstrap_metrics = np.empty(n_bootstrap, dtype=np.float64)
    for b in range(n_bootstrap):
        sample = rng.integers(0, n_blocks_kept, size=n_blocks_kept)
        rows = (sample // n_block_cols) * px_per_block
        cols = (sample % n_block_cols) * px_per_block
        pred_b = np.concatenate([
            pred_full[r : r + px_per_block, c : c + px_per_block].ravel()
            for r, c in zip(rows.tolist(), cols.tolist(), strict=False)
        ])
        ref_b = np.concatenate([
            ref_full[r : r + px_per_block, c : c + px_per_block].ravel()
            for r, c in zip(rows.tolist(), cols.tolist(), strict=False)
        ])
        bootstrap_metrics[b] = metric_fn(pred_b, ref_b)

    alpha = (1 - ci_level) / 2
    ci_lower = float(np.quantile(bootstrap_metrics, alpha))
    ci_upper = float(np.quantile(bootstrap_metrics, 1 - alpha))
    return BootstrapResult(
        point_estimate=float(point),
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        n_blocks_kept=n_blocks_kept,
        n_blocks_dropped=n_blocks_dropped,
        n_bootstrap=n_bootstrap,
        ci_level=ci_level,
        rng_seed=rng_seed if rng_seed is not None else -1,
    )
```

**Open risks:**
- **Risk M:** The `concatenate` + Python list-comprehension inner loop is O(B × n_blocks × pixels_per_block²) ≈ 500 × 12,100 × 1,089 ≈ 6.6 × 10⁹ pixel-touches. At 30 ns per touch this is ~3 minutes per bootstrap call. Acceptable for one-shot Phase 5 use; if Phase 6 also wants this, plan-phase notes optimisation via numba or vectorised gather.

### Probe 10 — macOS fork-mode pre-condition for chained retry (D-13, P0.1)

**Question:** Confirm Phase 1 ENV-04 `_mp.configure_multiprocessing()` bundle is fully landed.

**Evidence:**
- `src/subsideo/_mp.py:39 def configure_multiprocessing() -> None:` is implemented `[VERIFIED: read]`.
- Bundle contents (lines 71-80 of `_mp.py`): `MPLBACKEND=Agg` set via `os.environ.setdefault`, `RLIMIT_NOFILE` raised to `min(4096, hard)`, `requests` import seam warmed, `mp.set_start_method('fork', force=True)` on macOS Python<3.14 / `'forkserver'` on Python>=3.14, no-op on Linux through Python 3.13. `[VERIFIED: read]`
- Idempotent + thread-safe via `_CONFIGURE_LOCK` double-checked lock at `_mp.py:36`. `[VERIFIED: read]`
- v1.0 + Phase 1 `run_eval_dist*.py` import surface: `_mp.configure_multiprocessing()` is **NOT** currently called at the top of `run_eval_dist.py:1-65`, `run_eval_dist_eu.py:1-69`, or `run_eval_dist_eu_nov15.py` — these scripts predate ENV-04 in their current state. Phase 5 plan-phase MUST add the call at the very top of each rewritten script's `main()` body BEFORE any `requests.Session`-using import (`asf_search`, `earthaccess`).

**Recommendation:**

Phase 5 eval-script rewrites add the canonical Phase 1 ENV-04 idiom:

```python
# At the very top of each rewritten run_eval_dist*.py main():
from subsideo._mp import configure_multiprocessing
configure_multiprocessing()  # MUST fire before any network-using import

# Then proceed with the rest of imports + workflow.
```

For the chained retry stage (D-13), this is the binding pre-condition: dist-s1's `run_dist_s1_workflow` invokes `joblib`/`loky` for parallel despeckling, which warms a CFNetwork pool that then breaks under fork on macOS. Without `configure_multiprocessing()`, the chained retry hangs (PITFALLS P0.1).

**Open risks:**
- **Risk N:** If subsideo's `products/dist.py::run_dist()` already calls `configure_multiprocessing()` internally (likely, per Phase 1 D-14), Phase 5 eval scripts adding it ON TOP is harmless (idempotent). But Phase 5 must NOT skip it on the assumption that `run_dist` internalises it — the `earthaccess.login` call in Stage 0 happens BEFORE `run_dist`, so the bundle must fire first.

## Library / API Quick Reference

### earthaccess.search_data — exact signature, auth path, common pitfalls

```python
import earthaccess

# Auth (needs EARTHDATA_USERNAME / EARTHDATA_PASSWORD env vars OR ~/.netrc)
auth = earthaccess.login(strategy='environment')  # or 'netrc' or 'interactive'
assert auth.authenticated, "Earthdata auth failed"

# Search (returns list of UMM-G granule dicts)
results = earthaccess.search_data(
    short_name='OPERA_L3_DIST-ALERT-S1_V1',  # collection short_name
    bounding_box=(-119.0, 33.5, -118.0, 34.5),  # (west, south, east, north) degrees
    temporal=('2025-01-14', '2025-01-28'),  # (start, end) ISO-8601 strings or datetimes
    count=20,  # max results; default is server-controlled
    cloud_hosted=False,  # True forces NASA Earthdata Cloud only
)
# results: list[earthaccess.search.DataGranule] — empty list on no-hit
```

**Pitfalls:**
- `search_data` returns `[]` on no-hit, NOT raises — explicit `if results:` check needed.
- `bounding_box` order is `(W, S, E, N)` — opposite of rasterio's `(left, bottom, right, top)` is the same; opposite of GDAL's `[xmin, ymin, xmax, ymax]`. Plan-phase tests with a known-hit case in another collection (e.g., ATL06) before relying on the OPERA-V1 query.
- Auth tokens cache at `~/.netrc` after `interactive` strategy; subsequent runs in `environment` strategy still re-validate via the env vars (not via netrc) per ENV-06 design.

### owslib.wfs.WebFeatureService — exact 2.0.0 init + getfeature+filter shape

```python
from owslib.wfs import WebFeatureService
from owslib.fes import And, BBox, PropertyIsBetween
from owslib.fes2 import Filter as Filter2  # WFS 2.0.0 Filter class
from owslib.etree import etree

wfs = WebFeatureService(
    url='https://maps.effis.emergency.copernicus.eu/effis',
    version='2.0.0',
)

# Inspect available types
print(list(wfs.contents))  # ['ms:modis.ba.poly', ...]

# Build filter (FES 2.0)
filter_obj = Filter2(And([
    BBox([-8.8, 40.5, -8.2, 41.0], 'urn:ogc:def:crs:EPSG::4326'),
    PropertyIsBetween(propertyname='firedate', lower='2024-09-15', upper='2024-09-25'),
]))
filter_xml = etree.tostring(filter_obj.toXML()).decode('utf-8')

# GetFeature
response = wfs.getfeature(
    typename='ms:modis.ba.poly',
    filter=filter_xml,
)
# response is a file-like object (urllib3 ChunkedResponse-like)

# Parse via geopandas (handles GML or shapezip)
import geopandas
from io import BytesIO
gdf = geopandas.read_file(BytesIO(response.read()))
print(gdf.crs)  # likely EPSG:4326
print(gdf.columns)  # firedate, area_ha, country, province, commune, geometry
```

**Pitfalls:**
- WFS 2.0.0 expects FES 2.0 `Filter` wrapping; WFS 1.1.0 expects FES 1.0 `Filter` (different namespaces); plan-phase locks 2.0.0 unless EFFIS rejects.
- Some MapServer WFS rejects `Filter` XML if not URL-encoded as a query param; owslib handles this by switching to POST automatically when the filter is large — verify via `wfs.getfeature(...).geturl()` if debugging.
- `BBox` CRS argument is an OGC URN; `'urn:ogc:def:crs:EPSG::4326'` is canonical for WGS84 lat/lon.
- The response body MUST be wrapped in `BytesIO` for `geopandas.read_file` (which expects a path-like or filehandle) — direct `geopandas.read_file(response)` raises.

### rasterio.features.rasterize — all_touched semantics

```python
from rasterio.features import rasterize
from rasterio.transform import from_bounds
import numpy as np

# Per-event AOI: T11SLT 30 m grid (~3660×3660), bbox in UTM
out_shape = (3660, 3660)
transform = from_bounds(west, south, east, north, *out_shape)  # affine

# EFFIS perimeters → uint8 mask
shapes = ((geom, 1) for geom in gdf.geometry)  # (shapely geom, value) tuples
mask = rasterize(
    shapes=shapes,
    out_shape=out_shape,
    transform=transform,
    fill=0,                # background
    dtype='uint8',
    all_touched=False,     # D-17: only pixels whose centre is INSIDE the polygon
    merge_alg=MergeAlg.replace,
)
# Also compute the all_touched=True diagnostic:
mask_at_true = rasterize(shapes=..., all_touched=True, ...)
```

**Pitfalls:**
- `from_bounds(west, south, east, north, width, height)` — UTM bbox + integer pixel dimensions. **Not** WGS84.
- `all_touched=False` is rasterio's default; explicitly passing it makes intent grep-able.
- `MergeAlg.replace` is default; `MergeAlg.add` for stacking. Plan-phase uses `replace` (binary mask).
- For the polygon-fraction-coverage variant (alternative-but-rejected per D-17), use `dtype='float32'` + a custom kernel — slower; plan-phase doesn't ship.

### numpy.random.default_rng — block bootstrap idiom + reproducibility

```python
import numpy as np

rng = np.random.default_rng(seed=0)  # PCG64 — modern, recommended
indices = rng.integers(low=0, high=N, size=N)  # bootstrap resample

# Reproducibility:
rng2 = np.random.default_rng(seed=0)
assert (rng.integers(0, 100, 10) == rng2.integers(0, 100, 10)).all()  # True
```

**Pitfalls:**
- Switching from `RandomState(seed)` to `default_rng(seed)` produces DIFFERENT sequences for the same seed — they're different RNGs (Mersenne Twister vs PCG64). Plan-phase commits **`default_rng(seed=0)` permanently** for v1.1; switching mid-milestone invalidates the bootstrap CI numbers.
- `default_rng` accepts `seed=None` for OS-entropy seed — DO NOT use for matrix-cell metrics (non-reproducible).

### h5py — attribute introspection idiom for OPERA HDF5

NOT applicable to OPERA DIST-S1 (Probe 1 finding: product is GeoTIFF, not HDF5). Idiom kept here for reference if other OPERA products surface in Phase 6:

```python
import h5py
with h5py.File(path, 'r') as f:
    # Walk attributes recursively
    def visit(name, obj):
        for k, v in obj.attrs.items():
            print(f'{name}.{k} = {v!r}')
    f.visititems(visit)
```

### requests + Range / HEAD pre-flight — CloudFront chunked download confirmation

NOT exercised by Phase 5 (Probe 7 finding: no CloudFront URL). Harness `download_reference_with_retry(source='CLOUDFRONT')` already implements HEAD pre-flight per Phase 1 ENV-06 — preserved for future use.

## Existing Code Reuse Map (per-file delta plan)

| File | Current LOC | Phase 5 changes | Why |
|------|-------------|-----------------|-----|
| `src/subsideo/validation/compare_dist.py` | 230 | **+25 LOC additive:** add `extract_v01_config_drift(opera_v01_kwargs, dist_s1_2014_defaults) -> list[KeyDelta]` (Probe 1 strategy). EXISTING `compare_dist()` extended to wrap point-estimate metrics in `block_bootstrap_ci` calls (4 wrappings × ~5 LOC each ≈ 20 LOC). Total ~45 LOC. **Stays under D-04's 50-LOC threshold → no new module.** | Single-file extension preserves co-located comparison + drift logic; matches Phase 4 D-18 promotion-rule pattern (extract on 2nd consumer; no 2nd consumer in v1.1). |
| `src/subsideo/validation/harness.py` | 627 | **+15 LOC additive:** add `RETRY_POLICY['effis']` dict at line ~70 (alongside CDSE/EARTHDATA/CLOUDFRONT/HTTPS); add `Literal['effis']` to `RetrySource` type. `download_reference_with_retry` body needs no change — it already dispatches by source key. | Phase 1 D-Claude's-Discretion ENV-06 explicitly anticipated 5+ sources. |
| `src/subsideo/validation/matrix_schema.py` | 629 | **+200-300 LOC additive:** add `DistNamCellMetrics`, `DistEUCellMetrics`, `DistEUEventMetrics`, `MetricWithCI`, `BootstrapConfig`, `ConfigDriftReport`, `KeyDelta`, `RasterisationDiagnostic`, `ChainedRunResult` Pydantic v2 types per D-25. ZERO edits to existing types (Phase 1 D-09 lock-in). | Phase 4 D-11 schema-extension pattern; mirrors `DISPCellMetrics` shape. |
| `src/subsideo/validation/matrix_writer.py` | 580 | **+80-120 LOC additive:** add `_is_dist_nam_shape`, `_is_dist_eu_shape`, `_render_dist_nam_cell`, `_render_dist_eu_cell` per D-24. Insert dispatch branches in `write_matrix()` AFTER `_is_disp_cell_shape` (lines 480-503) and BEFORE `_is_cslc_selfconsist_shape` (line 494) ordering — actually, AFTER all existing branches, since DIST schema is structurally disjoint from DISP / CSLC / RTC-EU. | Phase 4 D-08 ordering invariant: insert AFTER `disp:*` BEFORE the future `dswx:*`. |
| `src/subsideo/validation/criteria.py` | 262 | **0 edits OR +1-2 INVESTIGATION_TRIGGER entries** (plan-phase decides per Claude's-Discretion). Existing `dist.f1_min`/`dist.accuracy_min` BINDING entries unchanged (lines 172-186). | Phase 1 D-09 immutability; INVESTIGATION_TRIGGER entries are non-gate per Phase 2 D-13. |
| `src/subsideo/validation/metrics.py` | 125 | **0 edits.** F1/precision/recall/accuracy/bias/rmse/correlation primitives consumed unchanged by `compare_dist.py` and the new `bootstrap.py`. | Module is the canonical "metric primitives" surface; bootstrap is methodology, not metric. |
| `src/subsideo/validation/supervisor.py` | (existing; ~300 LOC inferred) | **0 edits.** Phase 5 scripts declare `EXPECTED_WALL_S` per Phase 1 D-11. | Subprocess wrapper unchanged; only consumes the constant. |
| `run_eval_dist.py` | 450 (v1.0 Park Fire) | **REWRITE:** ~600-700 LOC. (1) `_mp.configure_multiprocessing()` first; (2) Stage 0 CMR probe + branch; (3) Stage 1 generate-or-fetch v0.1 reference (Probe 1 + 7); (4) Stage 2 config-drift extraction; (5) Stage 3 dist-s1 run for T11SLT; (6) Stage 4 compare_dist + bootstrap CI; (7) Stage 5 write `DistNamCellMetrics`-shaped `metrics.json`; (8) Stage 6 write `meta.json` with input hashes. Park Fire content moves to `eval-dist-park-fire/` (renamed dir; the script for it is preserved in git history). | Per D-05, T11SLT replaces 10TFK. Per D-15, CMR probe is Stage 0. |
| `run_eval_dist_eu.py` | 532 (v1.0 Aveiro Sept 28) | **REWRITE:** ~800-1000 LOC. Declarative `EVENTS: list[EventConfig]` per D-11 with 3 entries (aveiro / evros / spain_culebra-or-romania). Per-event try/except isolation; per-event whole-pipeline skip via `harness.ensure_resume_safe`. EFFIS WFS download via `harness.download_reference_with_retry(source='effis')`. EFFIS rasterisation via `rasterio.features.rasterize(all_touched=False)` + diagnostic `all_touched=True`. Aveiro chained_run sub-stage subsumes the missing Oct 10 + the Nov 15 logic from `run_eval_dist_eu_nov15.py`. Single aggregate `eval-dist_eu/metrics.json` per `DistEUCellMetrics` schema. | Per D-10/D-11/D-13. v1.0 `run_eval_dist_eu.py` + `run_eval_dist_eu_nov15.py` content migrates here; both deleted at Phase 5 close. |
| `run_eval_dist_eu_nov15.py` | 532 | **DELETE at Phase 5 close.** Content migrates into the rewritten `run_eval_dist_eu.py` aveiro entry's chained_run sub-stage. | Per D-11. |
| **NEW** `src/subsideo/validation/bootstrap.py` | 0 → ~150 LOC | NEW module per D-06: `BootstrapResult` dataclass + `block_bootstrap_ci` function + module-level constants `DEFAULT_BLOCK_SIZE_M`, `DEFAULT_N_BOOTSTRAP`, `DEFAULT_RNG_SEED`, `DEFAULT_CI_LEVEL`, `DEFAULT_PIXEL_SIZE_M`. | Clean separation from `metrics.py`; D-06 explicit. |
| `docs/validation_methodology.md` | (post-Phase-3 §1+§2; post-Phase-4 §3 = ~365 LOC) | **+~80 LOC append:** §4 with five sub-sections (4.1 single-tile F1 variance + bootstrap CI methodology; 4.2 EFFIS rasterisation `all_touched=False` rationale; 4.3 EFFIS class-definition mismatch caveat; 4.4 config-drift gate semantics; 4.5 CMR auto-supersede). Append-only per Phase 3 D-15. | D-23. |
| `CONCLUSIONS_DIST_N_AM.md` | 195 (v1.0 Park Fire) | **+~150 LOC append:** v1.0 baseline preamble repackaged; new v1.1 sections — T11SLT outcome (PASS/FAIL/DEFERRED narrative); config-drift gate result table; bootstrap CI numbers; CMR probe outcome. | D-22. |
| `CONCLUSIONS_DIST_EU.md` | 240 (v1.0 Aveiro Sept 28) | **+~250 LOC append:** v1.0 baseline preamble; new v1.1 sections — 3-event aggregate; per-event detail (Aveiro / Evros / Spain-or-Romania); chained retry result narrative (DIFFERENTIATOR framing per ROADMAP DIST-07). | D-22. |
| `results/matrix_manifest.yml` | 99 | **0 edits.** `dist:nam` (cache_dir: `eval-dist`) + `dist:eu` (cache_dir: `eval-dist_eu`) entries already exist (lines 69-82). | REL-02 manifest-authoritative; matrix_writer fills sidecars at runtime. |
| `Makefile` | 64 | **0 edits.** `eval-dist-nam` + `eval-dist-eu` targets already wired (lines 33-34). | Phase 1 D-08. |
| `conda-env.yml` | 89 | **0 edits.** owslib goes to pip layer (Probe 5). | Pip layer already includes `-e .[validation,viz]`. |
| `pyproject.toml` | 267 | **+1 line:** add `"owslib>=0.35,<1",` to `[project.optional-dependencies] validation` extras at line ~131. | Probe 5. |
| `eval-dist/` (directory) | (existing; Park Fire) | **`git mv eval-dist/ eval-dist-park-fire/`** at Phase 5 start. New `eval-dist/` populated fresh by T11SLT run. | D-05. |
| `eval-dist-eu/` + `eval-dist-eu-nov15/` (directories) | (existing; Aveiro Sept 28 + Nov 15) | Plan-phase decides whether to **consolidate to `eval-dist_eu/`** (manifest convention) or keep hyphen + add manifest fix. v1.0 Sept 28 + Nov 15 outputs preserved either way. | D-11 cache directory consolidation; STATE.md notes the hyphen/underscore divergence is acknowledged. |

## Risk Register (planner mitigation hooks)

| Risk | Severity | Mitigation hook for plan-phase |
|------|----------|-------------------------------|
| **EFFIS endpoint drift** (DIST-05/06) | HIGH | Plan-phase Wave 1 first task: `owslib.wfs.WebFeatureService(...).contents` probe of BOTH candidate endpoints with assertion that the chosen layer is non-empty for at least Aveiro 2024 dates. |
| **Romania 2022 EFFIS coverage gap** (Probe 4) | HIGH | Plan-phase ADR substituting Spain Culebra June 2022. EVENTS list in `run_eval_dist_eu.py` cannot be locked until ADR resolves. |
| **OPERA v0.1 sample is GeoTIFF dir, not HDF5** (Probe 1) | HIGH | Plan-phase commits Probe 1 strategy: regenerate sample locally via `run_dist_s1_workflow(...)` with OPERA-ADT notebook kwargs; config-drift compares kwargs not metadata. |
| **dist-s1 2.0.14 7-key list inferred vs sourced** (Probe 2) | MEDIUM | The 7 keys above are evidence-cited from `defaults.py` v2.0.14 verbatim; CONTEXT.md candidate names that don't exist (`soil_moisture_filter`, `percolation_threshold`) are explicitly rejected. Plan-phase commits the 7 with citations. |
| **macOS fork hang in chained retry** (Probe 10) | MEDIUM | Plan-phase verifies `_mp.configure_multiprocessing()` is called at top of every rewritten `run_eval_dist*.py` `main()` body BEFORE `earthaccess.login` or any `requests.Session`-using import. |
| **EMSR686 vs EMSR649 confusion** (Probe 8) | LOW | Plan-phase corrects CONTEXT.md error: Evros 2023 = EMSR686. Mention in CONTEXT-update commit. |
| **Bootstrap pure-Python loop slow** (Probe 9) | LOW | ~3 min per cell; acceptable for Phase 5 use. Optimisation deferred unless Phase 6 also consumes. |
| **Chained retry middle stage missing** (Oct 10 — derivation from Probe 8) | LOW | Plan-phase rewrite of `run_eval_dist_eu.py` adds the missing Oct 10 dist-s1 invocation BEFORE the chained-retry sub-stage. Cache directory `eval-dist-eu/aveiro/oct10/` populated fresh. |
| **earthaccess version drift** (Probe 6) | LOW | Pinning `earthaccess>=0.12,<1` already in `pyproject.toml:59`; v1.0 already uses `earthaccess.login(strategy='environment')`. No version edit. |
| **owslib 0.35.0 dependency conflict** (Probe 5) | LOW | Pure-Python noarch; no native binaries; should pip-install cleanly on top of conda env. Plan-phase tests via `pip install owslib==0.35.0` smoke test. |

## Recommended Wave Structure for Plan-phase

The phase is plan-probe-heavy. Recommend **5 waves** (one extra over typical 4-wave phases) to surface probe outcomes in advisory `00-probes-PLAN.md` artifact before locking downstream work:

### Wave 0 (probes — sequential to Wave 1)
- **00-probes-PLAN.md (Plan-phase committee work, NOT a coded plan):** Lock the 7-key config-drift list (Probe 2 evidence) + EFFIS WFS endpoint + layer name (Probe 3 GetCapabilities probe) + Romania 2022 substitution (Probe 4 ADR) + Evros 2023 MGRS+track (Probe 8 enumerator probe) + reframe DIST-01 as "regenerate locally" (Probe 1 + Probe 7). Output: a markdown artefact (NOT a coded plan), committed before Wave 1 starts.

### Wave 1 (parallel — module-level adds)
- **01-bootstrap-module-PLAN.md:** Create `src/subsideo/validation/bootstrap.py` per Probe 9 design. Unit tests for `block_bootstrap_ci` against a known-F1 binary classification array. [DIST-03]
- **02-matrix-schema-PLAN.md:** Add 7-9 new Pydantic v2 types to `matrix_schema.py` per D-25 (additive, no edits to existing). [DIST-02, DIST-03, DIST-05, DIST-06, DIST-07]
- **03-harness-effis-policy-PLAN.md:** Add `RETRY_POLICY['effis']` branch to `harness.py` per D-18. Test against the locked-in EFFIS endpoint from Wave 0. Also add `'effis'` to `RetrySource` Literal. [DIST-05]

### Wave 2 (sequential — depends on Wave 1)
- **04-compare-dist-extension-PLAN.md:** Extend `compare_dist.py` with (a) `extract_v01_config_drift(...)` per Probe 1; (b) bootstrap CI wrappings around F1/precision/recall/accuracy. Stays under D-04's 50-LOC threshold → single-file extension. [DIST-02, DIST-03]
- **05-matrix-writer-dist-branches-PLAN.md:** Add `_render_dist_nam_cell` + `_render_dist_eu_cell` branches to `matrix_writer.py`; insertion order AFTER `disp:*` BEFORE future `dswx:*`. Tests for both. [DIST-03, DIST-05, DIST-06]

### Wave 3 (parallel — eval scripts, depends on Wave 2)
- **06-run-eval-dist-rewrite-PLAN.md:** Rewrite `run_eval_dist.py` for T11SLT with Stage 0 CMR + Stage 1 generate-v0.1-locally + Stage 2 config-drift + Stage 3 dist-s1 + Stage 4 compare + bootstrap + Stage 5 write `DistNamCellMetrics` metrics.json. Park Fire `git mv eval-dist/ eval-dist-park-fire/`. [DIST-01, DIST-02, DIST-03, DIST-04]
- **07-run-eval-dist-eu-rewrite-PLAN.md:** Rewrite `run_eval_dist_eu.py` as declarative `EVENTS: list[EventConfig]` (3 events). Aveiro entry with chained_run (Sep 28 → Oct 10 → Nov 15) embedded as post-stage. EFFIS rasterisation `all_touched=False` + diagnostic. Single aggregate `DistEUCellMetrics` write. v1.0 `run_eval_dist_eu_nov15.py` deleted at end. [DIST-05, DIST-06, DIST-07]

### Wave 4 (sequential — docs + closure, depends on Wave 3)
- **08-docs-and-conclusions-PLAN.md:** Append §4 to `docs/validation_methodology.md` (5 sub-sections per D-23). Append v1.1 sections to `CONCLUSIONS_DIST_N_AM.md` + `CONCLUSIONS_DIST_EU.md` (per D-22). Run `make eval-dist-nam` + `make eval-dist-eu` + `make results-matrix`. Verify matrix.md renders DIST cells correctly. [DIST-03, DIST-05, DIST-06, DIST-07]

This is **advisory** — planner makes the final call on grouping/sequencing.

## Project Skills Referenced

- `.claude/` directory contains only `settings.local.json`; no project-local skills (`.claude/skills/`) defined.
- No `.agents/skills/` directory exists.
- Project conventions documented in CLAUDE.md (root) are honored throughout: `micromamba run -n subsideo python3 ...` for all Python; conda-forge-only for isce3/dolphin/tophu/snaphu/GDAL; pure-Python validation tools (owslib, numpy, rasterio Python API) go in pip layer.

## Project Constraints (from CLAUDE.md)

| Constraint | Phase 5 implication |
|------------|---------------------|
| All Python invoked via `micromamba run -n subsideo python3` | Eval scripts run under supervisor which uses `$(PY) := micromamba run -n subsideo python` (Makefile line 8). No change needed. |
| Conda-forge-only for isce3/dolphin/tophu/snaphu/GDAL — NEVER pip install | Phase 5 adds owslib via pip (pure-Python noarch — exempt from this rule). |
| `pip install dolphin` is the WRONG dolphin (GPU ray tracer) | Phase 5 doesn't import dolphin directly; transitive only. No risk. |
| Validation passes: F1 > 0.80 + accuracy > 0.85 (DIST) | Phase 5 keeps these bars unchanged per CONTEXT.md; criteria.py entries `dist.f1_min` + `dist.accuracy_min` already shipped (lines 172-186). |
| Code style: ruff line-length 100, target Python 3.10, mypy strict | All new code (`bootstrap.py`, schema additions, eval-script rewrites) honors this; ruff format + mypy gates in pre-commit. |

## Sources

### Primary (HIGH confidence)
- `[VERIFIED]` `dist-s1 v2.0.14` source `src/dist_s1/data_models/defaults.py` retrieved verbatim — https://raw.githubusercontent.com/opera-adt/dist-s1/v2.0.14/src/dist_s1/data_models/defaults.py
- `[VERIFIED]` `dist-s1 main` source `src/dist_s1/constants.py` (`TIF_LAYERS`, `EXPECTED_FORMAT_STRING`, `PRODUCT_VERSION`)
- `[VERIFIED]` `dist-s1 main` `notebooks/A__E2E_Workflow_Demo.ipynb` Cell 5 + Cell 7 (T11SLT sample recipe)
- `[VERIFIED]` PyPI `owslib 0.35.0` published 2025-10-28; pure-Python; `requires_python>=3.10` — https://pypi.org/pypi/owslib/json
- `[VERIFIED]` PyPI `dist-s1 2.0.14` published 2026-04-20; `requires_python>=3.12` — https://pypi.org/pypi/dist-s1/json
- `[VERIFIED]` conda-forge `owslib 0.35.0` `noarch` — https://anaconda.org/conda-forge/owslib
- `[VERIFIED]` Local `eval-dist/dist_output/.../OPERA_L3_DIST-ALERT-S1_T10TFK_..._v0.1/` directory listing — 11 files matching `EXPECTED_FORMAT_STRING` pattern
- `[VERIFIED]` Local `src/subsideo/_mp.py:39 configure_multiprocessing()` — full bundle implemented; idempotent + thread-safe
- `[VERIFIED]` Local `src/subsideo/validation/harness.py:50-70` — `RETRY_POLICY` dict shape supports per-source extension
- `[VERIFIED]` Local `src/subsideo/validation/compare_dist.py:112-230` — point-estimate F1 logic; ready for bootstrap wrapping
- `[VERIFIED]` Local `src/subsideo/validation/criteria.py:172-186` — `dist.f1_min` + `dist.accuracy_min` BINDING entries unchanged
- `[CITED]` Context7 `/geopython/owslib` — WFS 2.0.0 + FES 2.0 filter idiom
- `[CITED]` Context7 `/nsidc/earthaccess` — `search_data` signature + auth strategies

### Secondary (MEDIUM confidence)
- `[CITED]` EFFIS data-and-services page — https://forest-fire.emergency.copernicus.eu/applications/data-and-services — quotes Candidate A WFS endpoint and `ms:modis.ba.poly` layer
- `[CITED]` Spatineo Directory entry for EFFIS OWS Server — https://directory.spatineo.com/service/328/ — quotes Candidate B layers `EFFIS:BurntAreasAll`, `BurntAreas7Days`, `BurntAreas30Days`
- `[CITED]` `effisr` R package source — https://github.com/patperu/effisr — confirms property names `firedate`, `area_ha`
- `[CITED]` Wikipedia "2023 Greece wildfires" + ReliefWeb ECHO Daily Flash — confirms EMSR686 (NOT EMSR649) for Evros 2023
- `[CITED]` Wikipedia "2024 Portugal wildfires" + EuroNews + Statista — confirms Aveiro 2024 dates and burnt area
- `[CITED]` JRC EFFIS report on Romania 2022 (162,518 ha vegetation, 13,141 ha forest)
- `[CITED]` Lahiri (2003) "Resampling Methods for Dependent Data" Ch.7-8 (block bootstrap) — bashtage.github.io/kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Lahiri_2and7.pdf
- `[CITED]` numpy.org SPEC 7 + best-practices blog — `default_rng(seed)` PCG64 recommendation

### Tertiary (LOW confidence — flagged for plan-phase verification)
- `[ASSUMED]` Evros 2023 MGRS tile candidate `35TLF`/`35TMF` based on Alexandroupolis lat/lon → MGRS rule of thumb. Plan-phase confirms via `dist_s1_enumerator.get_mgrs_tiles_overlapping_geometry`.
- `[ASSUMED]` Spain Culebra 2022 MGRS `29TQG` based on Zamora province lat/lon. Plan-phase confirms.
- `[ASSUMED]` T11SLT WGS84 bbox `(-119.0, 33.5, -118.0, 34.5)` from MGRS-100km grid math; plan-phase verifies via `harness.bounds_for_mgrs_tile('11SLT')`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Evros 2023 MGRS = `35TLF` | Probe 8 | Plan-phase enumerator probe corrects; minor scope ripple. |
| A2 | Spain Culebra 2022 MGRS = `29TQG` | Probe 8 | Same — plan-phase enumerator probe corrects. |
| A3 | T11SLT WGS84 bbox = `(-119.0, 33.5, -118.0, 34.5)` | Probe 6 | Harness `bounds_for_mgrs_tile` returns the canonical value; cross-check before locking the CMR temporal+spatial query. |
| A4 | EFFIS `firedate` property accepts ISO-8601 strings in `PropertyIsBetween` | Probe 3 | If EFFIS uses Unix timestamps or `YYYYMMDD` integers, the filter is rejected; plan-phase tests via small known-event query. |
| A5 | Aveiro chained retry's middle stage Oct 10 has unique RTC inputs (not just resolution-shifted Sept 28) | Probe 8 / D-13 | If S1 cycle skips Oct 10 for track 147, plan-phase substitutes Oct 16 or Oct 22; chained-retry triple may need ±1 day adjustment. |
| A6 | The 7 dist-s1 v2.0.14 keys in Probe 2's table are F1-material — i.e., a 1-step change provably changes F1 | Probe 2 | If a key is non-F1-material (e.g., `n_workers_for_despeckling=8` is performance-only, NOT included in the 7), the gate is over-strict; plan-phase reviews each. The 7 above are conservative; non-material keys (DEFAULT_DEVICE, DEFAULT_TQDM_ENABLED, DEFAULT_BATCH_SIZE_FOR_NORM_PARAM_ESTIMATION) are explicitly excluded. |
| A7 | OPERA-ADT sample notebook `A__E2E_Workflow_Demo.ipynb` Cell 5 kwargs are stable across upstream commits | Probe 1 | If OPERA-ADT updates the notebook to use different kwargs, subsideo's `OPERA_V01_SAMPLE_KWARGS` constant drifts silently. Plan-phase pins the notebook commit SHA in the docstring + `meta.json`. |
| A8 | `geopandas.read_file(BytesIO(wfs_response.read()))` correctly handles both GML and shapezip MIME types from EFFIS WFS | Probe 3 | Likely true (geopandas auto-detects via fiona/pyogrio); plan-phase smoke-tests with a known-good query. |

## Open Questions

1. **EFFIS `firedate` property semantic — fire ignition vs detection vs perimeter date?**
   - What we know: EFFIS user guide hints `firedate` for ignition; `effisr` R package property name is `firedate`.
   - What's unclear: Whether for MODIS-derived perimeters this is the first-MODIS-detection date (which lags ignition by 0-3 days) or the user-supplied true ignition date.
   - Recommendation: Plan-phase queries known fires (Aveiro 2024 ignitions Sept 15-16) and verifies the returned `firedate` values match published ignition dates within ±3 days.

2. **Operational `OPERA_L3_DIST-ALERT-S1_V1` first-publication date timing**
   - What we know: As of 2026-04-15 + 2026-04-25 confirmation here, the operational collection is empty (`earthaccess.search_data(short_name='OPERA_L3_DIST-ALERT-S1_V1')` returns `[]` for all queried bbox+temporal pairs).
   - What's unclear: Whether OPERA-ADT will publish operationally during the Phase 5 window (April-May 2026 estimated).
   - Recommendation: Stage 0 CMR probe runs every eval invocation; if a hit appears mid-milestone, the auto-supersede mechanism in D-15+D-16 captures it.

3. **Romania-vs-Spain substitution: is preserving Romania a hard requirement?**
   - What we know: ROADMAP Phase 5 lists "2022 Romanian forest clear-cuts" explicitly. CONTEXT.md says "deferred ideas: Romania 2022 EU event substitution".
   - What's unclear: Whether substituting changes any external commitment (e.g., a stakeholder review).
   - Recommendation: Plan-phase ADR with explicit acknowledgment and documented justification (EFFIS coverage gap; M1 anti-class-mismatch); proceed with Spain Culebra unless user objects.

4. **Cache directory consolidation: `eval-dist_eu` (underscore) vs `eval-dist-eu` (hyphen)?**
   - What we know: `matrix_manifest.yml` uses `cache_dir: eval-dist_eu` (underscore, line 79). On-disk: `eval-dist-eu/` (hyphen) + `eval-dist-eu-nov15/` (hyphen) currently exist.
   - What's unclear: Plan-phase committed convention; STATE.md acknowledges the divergence as a "Phase 4 follow-up todo".
   - Recommendation: Plan-phase Wave 3 reconciles by either (a) `git mv eval-dist-eu/ eval-dist_eu/` + manifest unchanged, or (b) editing manifest to hyphen and matching supervisor `_cache_dir_from_script` logic. Option (a) preferred (less code touch).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Required by dist-s1 2.0.14 (`requires_python>=3.12`) | ✓ | conda-env.yml line 38: `python=3.12` | — |
| dist-s1 | DIST workflow | ✓ | conda-env.yml line 52: `dist-s1=2.0.14` | — |
| dist-s1-enumerator | dist-s1 transitive (RTC enumeration) | ✓ | conda-forge transitive of dist-s1 | — |
| earthaccess | CMR probe + Earthdata download | ✓ | pyproject.toml: `earthaccess>=0.12,<1` | — |
| asf-search | RTC inputs probe (v1.0 already uses) | ✓ | pyproject.toml: `asf-search>=8.0,<13` | — |
| owslib | EFFIS WFS (NEW Phase 5) | ✗ | — | Add to `pyproject.toml [validation]` extras: `owslib>=0.35,<1` |
| rasterio | Both DIST + EFFIS rasterisation | ✓ | conda-env.yml: `rasterio>=1.5,<2` | — |
| geopandas | EFFIS GML/shapezip parsing | ✓ | conda-env.yml: `geopandas>=1.0,<2` | — |
| pyogrio | geopandas backend | ✓ | conda-forge transitive | — |
| numpy | bootstrap, metrics | ✓ | conda-env.yml: `numpy>=1.26,<2` (PCG64 available since 1.17) | — |
| EARTHDATA_USERNAME / EARTHDATA_PASSWORD env vars | CMR probe + ASF DAAC RTC fetch | (user-provided) | — | If unset: `harness.credential_preflight` raises SystemExit fail-fast (already wired). |
| EFFIS WFS endpoint | DIST-05 EU events | (network) | — | If endpoint down: harness `RETRY_POLICY['effis']` retries 5×; persistent failure → cell renders RUN_FAILED per ENV-09; eval continues. |
| `_mp.configure_multiprocessing()` bundle | DIST-07 chained retry | ✓ | `src/subsideo/_mp.py` Phase 1 ENV-04 landed | — |

**Missing dependencies with no fallback:**
- None. The single Phase-5-new dependency (owslib) has a clean install path.

**Missing dependencies with fallback:**
- None directly missing; the 1 NEW pip install (`owslib>=0.35,<1`) is added to `pyproject.toml [validation]` extras and lands automatically when `pip install -e .[validation,viz]` runs in the conda-env.yml pip layer.

## Sources (extended URL list)

### Primary
- https://raw.githubusercontent.com/opera-adt/dist-s1/v2.0.14/src/dist_s1/data_models/defaults.py (defaults.py verbatim)
- https://raw.githubusercontent.com/opera-adt/dist-s1/main/src/dist_s1/constants.py (TIF_LAYERS, EXPECTED_FORMAT_STRING)
- https://raw.githubusercontent.com/opera-adt/dist-s1/main/notebooks/A__E2E_Workflow_Demo.ipynb (T11SLT sample recipe)
- https://pypi.org/pypi/owslib/json (owslib 0.35.0 metadata)
- https://pypi.org/pypi/dist-s1/json (dist-s1 2.0.14 metadata)
- https://anaconda.org/conda-forge/owslib (conda-forge owslib noarch)
- Context7 `/geopython/owslib` (WFS+FES idiom)
- Context7 `/nsidc/earthaccess` (search_data + auth)

### Secondary
- https://forest-fire.emergency.copernicus.eu/applications/data-and-services (EFFIS WFS Candidate A endpoint)
- https://directory.spatineo.com/service/328/ (EFFIS WMS server Candidate B)
- https://github.com/patperu/effisr (EFFIS REST/WFS R client; property names)
- https://en.wikipedia.org/wiki/2024_Portugal_wildfires (Aveiro 2024 dates/area)
- https://en.wikipedia.org/wiki/2023_Greece_wildfires (Evros 2023 = EMSR686)
- https://emergency.copernicus.eu/mapping/list-of-components/EMSR649 (EMSR649 = Italian flood, NOT Greek wildfire)
- https://numpy.org/doc/stable/reference/random/generator.html (default_rng PCG64)
- https://blog.scientific-python.org/numpy/numpy-rng/ (NumPy RNG best practices)
- https://bashtage.github.io/kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Lahiri_2and7.pdf (block bootstrap reference)
- https://github.com/opera-adt/dist-s1 (project README + structure)

### Tertiary (probe-required)
- EFFIS WFS GetCapabilities endpoint (must be probed live by plan-phase; both Candidate A `https://maps.effis.emergency.copernicus.eu/effis?service=WFS&request=GetCapabilities` and Candidate B `http://geohub.jrc.ec.europa.eu/effis/wfs?service=WFS&request=GetCapabilities` returned timeouts in this research session — likely region/firewall variability)

## Metadata

**Confidence breakdown:**
- Existing code surfaces (compare_dist, harness, criteria, matrix_schema, matrix_writer, _mp): HIGH (verified by direct read).
- dist-s1 2.0.14 default config: HIGH (verbatim from v2.0.14 git tag).
- OPERA DIST-S1 product structure: HIGH (verified locally + against dist-s1 main constants.py).
- EFFIS WFS endpoint + layer name: MEDIUM (two competing candidates; live probe didn't complete in research session).
- Romania 2022 vs Spain Culebra event substitution: MEDIUM (HIGH confidence on the gap; MEDIUM on the recommended substitute being the right one).
- Aveiro/Evros AOI bboxes + dates: HIGH for Aveiro (cached in v1.0); MEDIUM for Evros (literature consistent; MGRS+track from enumerator probe at plan-phase).
- Bootstrap implementation: HIGH (numpy + Hall 1985 is canonical; pseudocode reviewed).
- earthaccess query shape: HIGH (Context7-verified; v1.0 already uses).

**Research date:** 2026-04-25
**Valid until:** 2026-05-25 (30 days for stable; longer is fine — none of the dependencies are in fast-iteration windows)

## RESEARCH COMPLETE
