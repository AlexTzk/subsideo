# Phase 6: DSWx-S2 N.Am. + EU Recalibration - Context

**Gathered:** 2026-04-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 6 closes the 5/5 product validation matrix on the DSWx row by:

- **DSWx-N.Am.-PositiveControl** (Lake Tahoe primary / Lake Pontchartrain fallback, runtime-pick by cloud-cover): a positive-control eval that proves the v1.0 pipeline works at calibration-baseline region against JRC Monthly History; F1 < 0.85 triggers a halting BOA-offset / Claverie-cross-cal / SCL-mask regression investigation before EU recalibration proceeds.
- **DSWx-EU-Balaton** (Balaton held-out): a re-run of `run_eval_dswx.py` against JRC with the recalibrated EU thresholds; matrix-cell value is **Balaton F1**, with fit-set mean F1 + LOO-CV mean F1 reported alongside in metrics.json (BOOTSTRAP §5.4 + DSWX-06 explicit). 0.85 ≤ F1 < 0.90 reports as `cell_status='FAIL'` + `named_upgrade_path='ML-replacement (DSWX-V2-01)'`. F1 < 0.85 reports as FAIL + `named_upgrade_path='fit-set quality review'`. F1 > 0.92 invalidates the ceiling claim and demands §5.1 citation revision.

Plus the recalibration pipeline:

- **AOI selection notebook + probe artifact**: `notebooks/dswx_aoi_selection.ipynb` produces `.planning/milestones/v1.1-research/dswx_fitset_aoi_candidates.md` (Phase 2 D-04 / Phase 3 03-02 probe-and-commit pattern). 5 biome-diverse AOIs selected (Mediterranean reservoir / Atlantic estuary / boreal lake / Alpine valley / Iberian summer-dry; Balaton fixed as Pannonian held-out). Hybrid auto-reject + advisory pre-screen: hard-rejects on cloud-free unavailability, wet/dry water-extent ratio < 1.2 (P5.4 strict), JRC `unknown` class > 20%; advisory flags on jrc_confidence < 5 cloud-free obs > 5%, OSM glacier/frozen/turbid/shadow tags. Plan-phase 06-01 lands the artifact + user lock-in checkpoint BEFORE fit-set compute commits.
- **Fit-set construction**: 12 (AOI, wet-scene, dry-scene) triples × ~1.2 GB SAFE = ~15 GB raw under `eval-dswx-fitset/<aoi>/<wet|dry>/<SAFE>/`. CDSEClient.download_safe + ensure_resume_safe per Phase 5 D-11 declarative-list pattern.
- **Pre-compute intermediate index bands**: per (AOI, scene) cache the 5 float32 numpy index arrays (MNDWI + NDVI + AWESH + MBSRV + MBSRN) + SCL mask + JRC reference under `eval-dswx-fitset/<aoi>/<scene>/intermediates/*.npy`. ~2.4 GB per scene at 10980×10980 float32 → ~30 GB total. Scene pipeline (band read → BOA offset → Claverie cross-cal → index compute) runs once; grid search re-thresholds in pure numpy. ~20× speedup over re-running `_compute_diagnostic_tests` per gridpoint.
- **Joint grid search**: `scripts/recalibrate_dswe_thresholds.py` over WIGT ∈ [0.08, 0.20] step 0.005 (25 vals) × AWGT ∈ [−0.1, +0.1] step 0.01 (21 vals) × PSWT2_MNDWI ∈ [−0.65, −0.35] step 0.02 (16 vals) = 8400 combinations × 12 scene-pairs = ~100k evaluations. Outer parallelism: `joblib.Parallel(n_jobs=-1, backend='loky')` over (AOI, scene); inner gridpoint loop sequential pure-numpy. Per-(AOI, scene) try/except isolation. Restart-safe per-pair `gridscores.parquet` (or JSON-lines) + final `scripts/recalibrate_dswe_thresholds_results.json` aggregate. **Edge-of-grid sentinel**: if joint best-point WIGT/AWGT/PSWT2_MNDWI is at the boundary of any axis, write `cell_status='BLOCKER'` + exit non-zero (P5.1 mitigation) — plan-phase or human must expand bounds + re-run.
- **LOO-CV gap check (post-hoc on best-point only)**: refit thresholds on 11 AOIs at the joint best gridpoint, test on 12th, rotate 12 times. Compute LOO-CV mean F1; gap = fit-set-mean-F1 − LOO-CV-mean-F1. DSWX-06 acceptance: gap < 0.02 required (P5.1 mitigation). Cheap: 12 extra threshold-and-score runs vs 100k full grid.
- **Threshold module** (`src/subsideo/products/dswx_thresholds.py`): frozen dataclass `DSWEThresholds` (slots=True, frozen=True) carrying WIGT/AWGT/PSWT2_MNDWI plus inline provenance (grid_search_run_date, fit_set_hash sha256, fit_set_mean_f1, held_out_balaton_f1, loocv_mean_f1, loocv_gap, notebook_path, results_json_path). Two instances: `THRESHOLDS_NAM` (PROTEUS defaults preserved) + `THRESHOLDS_EU` (recalibrated). Region selector: pydantic-settings env-var `SUBSIDEO_DSWX_REGION: Literal['nam','eu'] = 'nam'` PLUS `DSWxConfig.region: Literal['nam','eu'] | None = None`; `run_dswx` resolves via `config.region or settings.dswx_region`. v1.0 module-level WIGT/AWGT/PSWT2_MNDWI in `products/dswx.py:27-39` are DELETED; `_compute_diagnostic_tests` gains a required `thresholds: DSWEThresholds` keyword. PSWT1_* (Test 4) constants stay (not in recalibration grid).
- **Shoreline 1-pixel buffer**: `compare_dswx` excludes a 1-pixel buffer around every JRC water/land class boundary. Applied UNIFORMLY in grid search AND final F1 reporting (single source of truth). metrics.json: `shoreline_buffer_excluded_pixels: int` + `f1` (gate, shoreline-excluded) + `f1_full_pixels` (diagnostic, no exclusion). P5.2 mitigation.
- **F1 ceiling citation**: plan-phase 06-01 fetches PROTEUS ATBD (https://www.jpl.nasa.gov/go/opera/products/dswx-product-suite or equivalent) + extracts the specific F1 number(s) cited with biome scope. Locked in `docs/validation_methodology.md §5.1` with citation. If no specific number found, fall back to 'empirical bound observed over our 6-AOI evaluation at F1 ≈ X'. P5.3 mitigation.
- **`docs/validation_methodology.md` §5** (Phase 6 owns; Phase 3 D-15 append-only): 5 sub-sections — §5.1 DSWE F1 ceiling citation chain, §5.2 Held-out Balaton vs fit-set methodology, §5.3 Shoreline 1-pixel buffer rationale, §5.4 LOO-CV overfit detection (gap < 0.02), §5.5 Threshold module + region selector design. Leads with structural argument (§5.1 ceiling) before empirical evidence (§5.2-§5.4) before design rationale (§5.5) per Phase 3 D-15 pattern.
- **CONCLUSIONS**: NEW `CONCLUSIONS_DSWX_N_AM.md` (Phase 6 deliverable, manifest already references it) + APPEND v1.1 sections to existing `CONCLUSIONS_DSWX.md` (Phase 4 D-13 / Phase 5 D-22 v1.0-baseline-preamble pattern; v1.0 Balaton narrative becomes leading 'v1.0 Balaton baseline (PROTEUS DSWE defaults; F1=0.7957 against JRC)' section, Phase 6 sections appended). Manifest filename unchanged (`CONCLUSIONS_DSWX.md` for `dswx:eu`, `CONCLUSIONS_DSWX_N_AM.md` for `dswx:nam`).

**Not this phase:**
- Tightening DSWx F1 > 0.90 bar (DSWX-06 + M4 anti-target-creep; immutable in `criteria.py:188`).
- ML-replacement algorithm (DSWX-V2-01; named upgrade path, not Phase 6 scope).
- Global recalibration beyond 6 EU biomes (DSWX-V2-02; v2 milestone).
- Turbid-water / frozen-lake / mountain-shadow handling (DSWX-V2-03; v2).
- New OPERA product classes (DSWx-S1, DSWx-HLS) — out of scope per PROJECT.md.
- Multi-burst mosaicking (cross-cutting v2).
- Picking specific recalibrated threshold values in this CONTEXT — those land at Phase 6 close once the grid search runs.
- Tightening dswx criteria from BOOTSTRAP §5 ('F1 > 0.90 is the bar. It does not move.').
- Modifying `products/dswx.py` algorithm logic — Phase 6 is recalibration, not algorithm replacement (`run_dswx` keeps its 5-test diagnostic + class lookup; only the 3 thresholds change).
- Adding any new product-quality CALIBRATING gates — DSWx stays binary-classification reference-agreement only (JRC IS the reference; no separate self-consistency analogue).
- Picking a DSWx-N.Am. AOI in this CONTEXT — runtime auto-pick by cloud-cover from the locked 2-element CANDIDATES list.

Phase 6 covers the 7 requirements mapped to it: **DSWX-01** (N.Am. positive control + F1 < 0.85 regression investigation), **DSWX-02** (AOI selection notebook with rationale), **DSWX-03** (12-triple/6-biome fit set + Balaton held out), **DSWX-04** (joint grid search over WIGT × AWGT × PSWT2_MNDWI), **DSWX-05** (typed thresholds module + provenance + region selector), **DSWX-06** (EU re-run + LOO-CV gap < 0.02 + honest FAIL labelling), **DSWX-07** (F1 ceiling ground-referenced or own-data-bound).

</domain>

<decisions>
## Implementation Decisions

### EU fit-set AOI selection methodology (DSWX-02, DSWX-03; PITFALLS P5.2 + P5.4)

- **D-01: AOI candidates committed via probe artifact + plan-phase user lock (Phase 2 D-04 / Phase 3 03-02 pattern).** Plan-phase 06-01 produces `.planning/milestones/v1.1-research/dswx_fitset_aoi_candidates.md` listing per-candidate scores (cloud-free availability, JRC confidence, wet/dry ratio, OSM failure-mode flags) for each of 5 biomes. Output also rendered to `docs/dswx_fitset_aoi_selection.md` per FEATURES Phase 5 row. User reviews + locks the 5 selected AOIs (+ rejection reasoning) before fit-set compute commits. De-risks 4-5 days of compute against AOI-quality cap (PITFALLS P5.2). Plan-phase 06-01 is a pre-fit-set probe wave; fit-set construction (Plan 06-02 or later) only proceeds after the lock.

- **D-02: Hybrid auto-reject + advisory pre-screen (Phase 2 D-13/D-14 pattern: 'automation flags, doesn't replace narrative').** Notebook auto-rejects on hard signals: cloud-free scene unavailable in wet OR dry season (auto-drop), wet/dry water-extent ratio < 1.2 (auto-drop per P5.4), JRC `unknown` class > 20% (auto-drop). Advisory-only on soft signals: jrc_confidence (< 5 cloud-free obs in time series) shown as score + flagged > 5%, OSM/Copernicus Land Monitoring failure-mode tags (glacier/frozen/turbid/shadow) shown as flags. Human reviews advisories during plan-phase 06-01 lock-in checkpoint. Notebook outputs a per-candidate score table + the 5 selected + reasoning for rejections in markdown.

- **D-03: P5.4 wet/dry ratio strict 1.2 auto-reject + alternate-year retry.** Per PITFALLS P5.4 explicit: 'If wet-month water extent is < 1.2× dry-month, the AOI-year pair is rejected.' Notebook auto-rejects, then queries JRC Monthly History climatology for an alternate year where the ratio holds. If no alternate year within JRC coverage (≤ 2021 cap) satisfies the ratio, the AOI is dropped. No threshold relaxation — drought-year + flood-year AOI-year pairs get skipped automatically.

- **D-04: Two notebooks: `dswx_aoi_selection.ipynb` (research / candidate scoring / final 5 + reasoning) + `dswx_recalibration.ipynb` (loads grid-search JSON / plots F1 surface / shows held-out Balaton F1 / reproduces frozen constants).** Single concern per notebook. Per REQUIREMENTS DSWX-02 + DSWX-05 explicit. Plan-phase commits both. Fit-set construction (download SAFEs + cache intermediates) lives in `scripts/recalibrate_dswe_thresholds.py` Stage 1 (not a third notebook).

### Grid search architecture & caching (DSWX-04; PITFALLS P5.1)

- **D-05: Per-scene cache 5 float32 intermediate index bands (MNDWI + NDVI + AWESH + MBSRV + MBSRN) + SCL + JRC reference.** Cache layout: `eval-dswx-fitset/<aoi>/<wet|dry>/<scene_id>/intermediates/{mndwi,ndvi,awesh,mbsrv,mbsrn,scl,jrc}.npy`. ~2.4 GB per scene at 10980×10980 float32 (B11/B12 native 20m → 10980 grid; reproject to 10m for compatibility with `_compute_diagnostic_tests`). Total ~30 GB across 12 (AOI, scene) pairs. Scene pipeline (band read → BOA offset → Claverie cross-cal → index compute via `_compute_diagnostic_tests` decomposed) runs ONCE per scene; grid search re-thresholds in pure numpy (no `_compute_diagnostic_tests` re-call per gridpoint). ~20× speedup. Restart-safe via mtime-staleness check on cache dirs (Phase 1 ensure_resume_safe pattern). Decompose `_compute_diagnostic_tests` body into a public `compute_index_bands(blue, green, red, nir, swir1, swir2) -> dict[str, np.ndarray]` and a public `score_water_class_from_indices(indices, thresholds: DSWEThresholds) -> np.ndarray` so the grid search consumes the cheap second function 8400 times per scene without re-parsing SAFE bands.

- **D-06: joblib processes parallel over (AOI, scene); inner gridpoint loop sequential pure-numpy.** `joblib.Parallel(n_jobs=-1, backend='loky')` over the 12 (AOI, scene) pairs. Inner loop: 8400 gridpoints sequential pure-numpy (gridpoint compute is fast pure-numpy thresholding + lookup; thread/process overhead would dominate). M3 Max 16 perf cores → 12 pairs all parallel; ~5-15 min wall on warm cache. Per-(AOI, scene) try/except isolation — one failed scene records `{aoi, scene, status: 'failed', error: <traceback>}` in the per-pair gridscores file but doesn't kill the rest of the grid run. `_mp.configure_multiprocessing()` (Phase 1 D-14) fires once at top of `recalibrate_dswe_thresholds.py` main; loky inherits the bundle.

- **D-07: Per-(AOI, scene) restart-safe checkpoint via `gridscores.parquet` (or JSON-lines if pandas/pyarrow not in conda env).** Each (AOI, scene) writes `eval-dswx-fitset/<aoi>/<scene>/gridscores.parquet` with 8400 rows × (WIGT, AWGT, PSWT2_MNDWI, f1, precision, recall, accuracy, n_pixels_total, n_pixels_shoreline_excluded). After all 12 pairs complete, aggregate into `scripts/recalibrate_dswe_thresholds_results.json` with: per-(AOI, scene) F1 surface, joint best gridpoint, fit-set mean F1, fit-set per-AOI breakdown, full grid heatmap data, edge_check status, LOO-CV table (post-hoc), held-out Balaton F1 (post-hoc). Restart-safe at the (AOI, scene) granularity — a crashed pair re-runs from intermediate cache; completed pairs skip via `gridscores.parquet` mtime check. Plan-phase commits whether parquet vs JSON-lines based on `pyarrow` availability in the conda env.

- **D-08: Edge-of-grid sentinel auto-FAIL.** Per PITFALLS P5.1: if joint best-point WIGT, AWGT, OR PSWT2_MNDWI is at the boundary of any axis (e.g. WIGT=0.08 or 0.20; AWGT=±0.1; PSWT2_MNDWI=−0.65 or −0.35), the script writes `calibration_diagnostics.json edge_check.status='at_edge'` + `cell_status='BLOCKER'` to `scripts/recalibrate_dswe_thresholds_results.json` AND exits non-zero. Plan-phase or human must expand grid bounds + re-run. Strict signal that the grid was too narrow; never silently accept an edge-best gridpoint. Gate prevents grid-too-narrow → wrong best-point → published miscalibrated thresholds.

### Threshold module API shape (DSWX-05)

- **D-09: Frozen dataclass `DSWEThresholds` with slots=True, frozen=True.** `@dataclass(frozen=True, slots=True)` carrying `WIGT: float`, `AWGT: float`, `PSWT2_MNDWI: float` plus provenance fields (D-11). Matches Phase 1 D-09 'frozen-dataclass `Criterion`' pattern in `criteria.py`. Stronger than NamedTuple (slots=True prevents attribute-spelling bugs; frozen=True enforces immutability). Lighter than Pydantic (no validation needed for hardcoded constants; REQUIREMENTS DSWX-05 forbids YAML / runtime I/O). REQUIREMENTS DSWX-05 phrasing 'typed `DSWEThresholds` NamedTuple' is descriptive — the frozen-dataclass pattern matches subsideo's existing immutable-typed-constants discipline (criteria.py).

- **D-10: Region selector via pydantic-settings env-var `SUBSIDEO_DSWX_REGION: Literal['nam','eu'] = 'nam'` PLUS `DSWxConfig.region: Literal['nam','eu'] | None = None`.** Both layers: env var sets the default; DSWxConfig field overrides per-call. `run_dswx` resolves via `region = config.region or settings.dswx_region` (None means 'use settings default'); looks up `THRESHOLDS_BY_REGION[region]` in the new module. Default 'nam' preserves v1.0 N.Am.-default behaviour. Matches REQUIREMENTS DSWX-05 explicit 'pydantic-settings region selector' + keeps DSWxConfig as the call-site override surface. Single source of truth for which region's thresholds apply at any call; auditable in metrics.json `meta.json.region_selected`.

- **D-11: Inline provenance metadata as class attributes on `DSWEThresholds` instances.** Each instance carries: `grid_search_run_date: str` (ISO date), `fit_set_hash: str` (sha256 of sorted (AOI, scene) IDs concatenated), `fit_set_mean_f1: float`, `held_out_balaton_f1: float`, `loocv_mean_f1: float`, `loocv_gap: float`, `notebook_path: str` (relative path to dswx_recalibration.ipynb), `results_json_path: str` (relative path to scripts/recalibrate_dswe_thresholds_results.json). All inline in the module (`src/subsideo/products/dswx_thresholds.py`) — grep-discoverable, no I/O at import time, immutable. Matches REQUIREMENTS DSWX-05 'typed constants module with provenance metadata'. Editing the constants by hand is git-diff-visible. The full grid heatmap data + per-AOI F1 breakdown + LOO-CV per-fold table live in `scripts/recalibrate_dswe_thresholds_results.json` (referenced via `results_json_path` field) — not duplicated inline. The N.Am. instance (`THRESHOLDS_NAM`) carries PROTEUS-paper provenance: `grid_search_run_date='1996-01-01-PROTEUS-baseline'` (or similar sentinel) + cite-string in a `provenance_note` field; only the EU instance carries Phase 6 grid-search numbers.

- **D-12: v1.0 module-level constants in `products/dswx.py:27-39` are DELETED for WIGT/AWGT/PSWT2_MNDWI; replaced by threading `DSWEThresholds` through `_compute_diagnostic_tests`.** `_compute_diagnostic_tests` gains a required keyword `thresholds: DSWEThresholds`; reads `thresholds.WIGT`, `thresholds.AWGT`, `thresholds.PSWT2_MNDWI`. `run_dswx` resolves the threshold set per D-10 and threads it. PSWT1_* (Test 4: PSWT1_MNDWI=−0.44, PSWT1_NIR=1500, PSWT1_SWIR1=900, PSWT1_NDVI=0.7) STAY as `products/dswx.py` module-level constants — they're not in the recalibration grid (REQUIREMENTS DSWX-04 only optimises WIGT, AWGT, PSWT2_MNDWI). PSWT2_BLUE/PSWT2_NIR/PSWT2_SWIR1/PSWT2_SWIR2 ALSO stay at module level (not in the grid). Forces every consumer to be region-aware via API surface, not hidden module state. Discoverable via ripgrep `grep dswx_thresholds`. Test files importing the v1.0 constants must update to import `DEFAULT_THRESHOLDS_NAM.WIGT` etc. — short migration; visible in PR diff.

### Reporting framework + held-out Balaton + F1 ceiling citation (DSWX-06, DSWX-07; PITFALLS P5.1, P5.2, P5.3)

- **D-13: The OFFICIAL `dswx:eu` matrix-cell F1 = held-out Balaton F1 (BOOTSTRAP §5.4 + PITFALLS P5.1 explicit).** Matrix cell renders `f1=0.XX [PASS|FAIL]` with Balaton number. metrics.json schema `reference_agreement.measurements.f1` = Balaton (the gate value). Fit-set mean F1 + LOO-CV mean F1 + per-fit-AOI F1 breakdown reported alongside under `reference_agreement.diagnostics.{fit_set_mean_f1, loocv_mean_f1, per_aoi_breakdown[]}` (DSWX-06 explicit: 'fit-set F1 reported alongside LOO-CV F1'). Keeps held-out discipline pure: fit-set is calibration data, Balaton is test. No fit-set-mean-as-cell-value option ever — directly contradicts PITFALLS P5.1 ('Balaton F1 < 0.90, report FAIL — not fit-set F1 passed').

- **D-14: LOO-CV computed POST-HOC on best gridpoint only.** Grid search runs full 8400-point grid on all 12 (AOI, scene) pairs to identify the joint best gridpoint. Then post-hoc: refit thresholds on 11 AOIs (with the same 8400-point grid restricted to that 11-AOI subset; pick the LOO-best gridpoint per fold), test on the 12th, rotate 12 times. Report `loocv_mean_f1` + per-fold `loocv_per_fold_f1`. DSWX-06 acceptance: `loocv_gap = fit_set_mean_f1 - loocv_mean_f1 < 0.02` required. Cheap: 12 LOO folds × 8400 gridpoints (per-fold) = 100k LOO-fold evaluations; same order as the main grid (~5-15 min added). Per PITFALLS P5.1: LOO-CV is the overfit detector applied to the recalibration result, not the optimisation target. If gap ≥ 0.02, write `cell_status='BLOCKER'` + `loocv_gap_violation=True` and halt before threshold-module update — plan-phase reviews fit-set composition + decides whether to expand AOI count or accept the overfit-flagged calibration.

- **D-15: Honest FAIL labelling via `named_upgrade_path: str | None` field on `DswxCellMetrics` (NOT a cell_status Literal extension).** Reuse the existing `cell_status: Literal['PASS', 'FAIL', 'CALIBRATING', 'MIXED', 'BLOCKER']` (Phase 3 D-03 inherited). Add `named_upgrade_path: str | None = None` to DswxNamCellMetrics + DswxEUCellMetrics. Three semantic states per BOOTSTRAP §5.5: F1 ≥ 0.90 = `cell_status='PASS'` + `named_upgrade_path=None`; 0.85 ≤ F1 < 0.90 = `cell_status='FAIL'` + `named_upgrade_path='ML-replacement (DSWX-V2-01)'`; F1 < 0.85 = `cell_status='FAIL'` + `named_upgrade_path='fit-set quality review'`. matrix_writer concatenates the field into the cell text: `'F1=0.87 FAIL — named upgrade: ML-replacement (DSWX-V2-01)'`. Keeps the cell_status Literal stable across all 5 products (Phase 1 D-09 lock); adds detail in a structured side-channel that doesn't break existing dispatchers. CONCLUSIONS_DSWX.md sub-section 'Named upgrade path' explains the three-state taxonomy + cites Future Work entry (DSWX-V2-01 for the ML path; DSWX-02 fit-set review for the < 0.85 path).

- **D-16: Shoreline 1-pixel buffer applied uniformly in BOTH grid search AND final F1 reporting.** `compare_dswx` computes a 1-pixel buffer mask around every JRC water/land class boundary (via scipy.ndimage.binary_dilation on the `jrc_water_class != 0` array, dilated by 1 pixel, XORed with the original); excluded pixels are masked from F1 computation. Applied UNIFORMLY: grid search optimises against shoreline-excluded F1; final Balaton F1 reported is also shoreline-excluded. Single source of truth for what counts as a fair F1. metrics.json: `reference_agreement.measurements.f1` (gate, shoreline-excluded) + `reference_agreement.diagnostics.f1_full_pixels` (no exclusion, diagnostic) + `reference_agreement.diagnostics.shoreline_buffer_excluded_pixels: int`. P5.2 mitigation rationale documented in `docs/validation_methodology.md §5.3`. Avoids fit/eval kernel mismatch (rejected option B in discussion).

- **D-17: F1 ceiling citation strategy: plan-phase 06-01 PROTEUS ATBD probe + lock in §5.1 with citation (or fall back to own-data bound).** Plan-phase 06-01 fetches PROTEUS ATBD (https://www.jpl.nasa.gov/go/opera/products/dswx-product-suite or document-search via Context7 / web fetch) + extracts the specific F1 number(s) cited with biome scope. Locked in `docs/validation_methodology.md §5.1` with full citation (paper + section + table). If specific number is, e.g., 0.94 for a subset of biomes and 0.85 for another, report the range. If no specific number can be produced, fall back to 'empirical bound observed over our 6-AOI evaluation at F1 ≈ X' — own-data only, not a literature claim. P5.3 mitigation. The criterion threshold in `criteria.py:188-194` (`dswx.f1_min = 0.90` BINDING) stays unchanged — the ceiling is a comment, NOT a criterion (P5.3 explicit isolation). If our v1.1 recalibration lands F1 > 0.92 (beating the cited ceiling), Phase 6 §5.1 must revise the ceiling claim — that's a methodology-doc edit, not a criteria.py edit (the gate stays 0.90).

### N.Am. positive control mechanics (DSWX-01)

- **D-18: Runtime auto-pick by cloud-cover from a locked 2-element CANDIDATES list.** `run_eval_dswx_nam.py` declares `CANDIDATES: list[AOIConfig] = [tahoe, pontchartrain]` at module top (Phase 5 D-11 declarative-list pattern). Each AOIConfig carries `aoi_name`, `mgrs_tile`, `epsg`, `date_start`, `date_end`, `jrc_year`, `jrc_month`. Tahoe primary (MGRS 10SFH or 10SGG depending on the lake's tile coverage) + Pontchartrain fallback (MGRS 15RYR or 15RZR). Each AOI gets a CDSE STAC search for cloud-free scenes (cloud_cover < 15%) in the locked date window. First AOI with a valid scene wins. Records in metrics.json: `selected_aoi`, `selected_scene_id`, `cloud_cover_pct`, `candidates_attempted: list[{aoi_name, scenes_found, cloud_min}]`. If both fail, write `cell_status='BLOCKER'` + exit non-zero. Deterministic on a given CDSE state; reproducible from cache. Plan-phase 06-01 commits exact MGRS tiles + date windows for both candidates with citations from CDSE STAC.

- **D-19: JRC date window capped at 2021** (BOOTSTRAP §5.1 + JRC Monthly History coverage cap). Both Tahoe + Pontchartrain candidates use July 2021 (matches existing Balaton EU eval window). Exact day depends on cloud-free availability resolved at runtime. Plan-phase 06-01 confirms JRC `LATEST/tiles/2021/2021_07/` coverage for both AOIs' lonlat ranges via existing `_jrc_tile_url` helper.

- **D-20: F1 < 0.85 auto-flags + halts EU recalibration via metrics.json gate (Phase 2 D-13/D-14 INVESTIGATION_TRIGGER pattern).** `run_eval_dswx_nam.py` writes `f1_below_regression_threshold: bool = (f1 < 0.85)` and `regression_diagnostic_required: list[str] = ['boa_offset_check', 'claverie_xcal_check', 'scl_mask_audit']` to metrics.json when triggered. `scripts/recalibrate_dswe_thresholds.py` Stage 0 reads `eval-dswx_nam/metrics.json` if present AND asserts `not f1_below_regression_threshold OR investigation_resolved=True`. If the assert fails: print regression diagnostics + exit non-zero. Halts EU recalibration until human writes a BOA-offset / Claverie cross-cal / SCL-mask investigation finding into CONCLUSIONS_DSWX_N_AM.md (and sets `investigation_resolved=True` in metrics.json by hand or via a follow-up commit). Optional: add `criteria.py` `dswx.nam.investigation_f1_max=0.85` `INVESTIGATION_TRIGGER` entry (Phase 2 D-15 pattern) so matrix_writer renders the flag inline. Plan-phase decides whether to add the criteria entry — non-gate, narrative-only.

### CONCLUSIONS structure (carry-forward; Phase 4 D-13 / Phase 5 D-22 pattern)

- **D-21: Two CONCLUSIONS files; v1.0 Balaton baseline preamble in `CONCLUSIONS_DSWX.md`.** (a) NEW `CONCLUSIONS_DSWX_N_AM.md` (Phase 6 deliverable; manifest already references). Sections: 1. Objective (positive control framing); 2. Test setup (selected AOI + scene + JRC ref); 3. Pipeline run (cold/warm wall + Stage logs); 4. Reference-agreement (F1 + precision + recall + OA; threshold = 0.90 BINDING); 5. Investigation findings (only populated if F1 < 0.85). (b) APPEND v1.1 sections to existing `CONCLUSIONS_DSWX.md` (Phase 4 D-13 / Phase 5 D-22 pattern): v1.0 Balaton narrative becomes leading 'v1.0 Balaton baseline (PROTEUS DSWE defaults; F1=0.7957 against JRC)' section; Phase 6 v1.1 sections append below: 'Recalibrated thresholds (region=eu)' + 'Held-out Balaton F1 + LOO-CV gap' + 'Matrix-cell verdict + named upgrade path'. Manifest filename unchanged (`CONCLUSIONS_DSWX.md` for `dswx:eu`, `CONCLUSIONS_DSWX_N_AM.md` for `dswx:nam`) — no `git mv`, no manifest edit needed.

### `docs/validation_methodology.md` §5 (Phase 6 owns; Phase 3 D-15 append-only)

- **D-22: §5 with 5 sub-sections.** §5.1 DSWE F1 ceiling citation chain (PROTEUS ATBD direct fetch evidence + biome scope + own-data-bound fallback if no specific number; P5.3 mitigation; cites Future Work DSWX-V2-01). §5.2 Held-out Balaton vs fit-set methodology (why Balaton is the gate per BOOTSTRAP §5.4 + PITFALLS P5.1; why fit-set mean is not). §5.3 Shoreline 1-pixel buffer rationale (P5.2 commission-98% / omission-74-99% asymmetry argument; uniform application across grid search + reporting per D-16). §5.4 LOO-CV overfit detection (gap < 0.02 acceptance per DSWX-06 + P5.1; post-hoc on best-gridpoint design per D-14). §5.5 Threshold module + region selector design (DSWX-05 typed-constants over YAML/runtime-config; pydantic-settings env-var + DSWxConfig field per D-10; v1.0 module-constant deletion per D-12). §5 leads with structural argument (§5.1 ceiling) before empirical evidence (§5.2-§5.4) before design rationale (§5.5) per Phase 3 D-15 'kernel argument leads, diagnostic appendix follows'. Phase 6 §5 is the single PR-mergeable artifact closing the methodology-doc-from-Phase-3-onward planning queue. Phase 7 owns §6 (or higher) per Phase 3 D-15 append-only.

### Cross-cutting carry-forwards (NOT re-decided here — listed for traceability)

- **D-23: `_mp.configure_multiprocessing()` fires at top of every `run_*()` (Phase 1 D-14, ENV-04).** Phase 6 invokes at top of `run_eval_dswx_nam.py` `main()` AND at top of `scripts/recalibrate_dswe_thresholds.py` `main()` — joblib loky inherits the bundle.

- **D-24: Subprocess-level supervisor watchdog (Phase 1 D-10..D-14, ENV-05).** Each `run_eval_dswx_nam.py` and `scripts/recalibrate_dswe_thresholds.py` invoked via `python -m subsideo.validation.supervisor <script>` (Makefile delegation). `EXPECTED_WALL_S` constant per script: `run_eval_dswx_nam.py = 1800` (~30 min, single-AOI single-scene); `scripts/recalibrate_dswe_thresholds.py = 21600` (~6 hr, full fit-set + grid + LOO-CV). Plan-phase commits exact values based on cold-vs-warm path estimates.

- **D-25: harness.RETRY_POLICY['jrc'] new branch.** Phase 5 added 5th branch 'effis'; Phase 6 adds 6th branch 'jrc' per Phase 1 ENV-06 per-source retry policy pattern. JRC fetch is plain HTTPS GET via existing `urllib.request` in `compare_dswx._fetch_jrc_tile`; refactor to `harness.download_reference_with_retry(source='jrc', url=..., dest_path=...)`. Policy: `RETRY_POLICY['jrc'] = {'retry_on': [503, 504, 'ConnectionError', 'TimeoutError'], 'abort_on': [401, 403, 404], 'max_attempts': 5, 'backoff_factor': 2, 'max_backoff_s': 60}`. JRC has no auth; 404 means tile out-of-coverage which is benign (propagated as None per existing _fetch_jrc_tile signature). Plan-phase commits the policy entry + the refactor.

- **D-26: matrix_schema.py Pydantic v2 additive extension.** Phase 6 ADDS: `DswxNamCellMetrics(MetricsJson)` (carries `selected_aoi`, `selected_scene_id`, `cloud_cover_pct`, `candidates_attempted`, `f1_below_regression_threshold`, `regression_diagnostic_required: list[str]`, `investigation_resolved: bool`, `reference_agreement.measurements.{f1, precision, recall, accuracy}`, `reference_agreement.diagnostics.{f1_full_pixels, shoreline_buffer_excluded_pixels}`, `cell_status`, `named_upgrade_path: str | None`); `DswxEUCellMetrics(MetricsJson)` (carries `region='eu'`, `thresholds_used: DSWEThresholdsRef` (region + provenance hash + grid_search_run_date), `reference_agreement.measurements.f1` (Balaton), `reference_agreement.diagnostics.{fit_set_mean_f1, loocv_mean_f1, loocv_gap, per_aoi_breakdown[], f1_full_pixels, shoreline_buffer_excluded_pixels}`, `cell_status`, `named_upgrade_path: str | None`); plus supporting types `DSWEThresholdsRef`, `PerAOIF1Breakdown`, `LOOCVPerFold`, `RegressionDiagnostic`. ZERO edits to existing types (Phase 1 D-09 big-bang lock holds).

- **D-27: matrix_writer.py adds DSWx render branches (`dswx:nam` + `dswx:eu`) AFTER `dist:*` per Phase 5 D-24 amendment.** Phase 5 D-24 amendment de-locks the BEFORE-cslc/dswx clause; only the AFTER-disp + AFTER-dist invariant holds. Phase 6 dispatch order: `disp_call < dist_eu_call < dist_nam_call < dswx_nam_call < dswx_eu_call`. `_render_dswx_nam_cell` renders `f1=0.XX [PASS|FAIL]` + `selected_aoi` label inline + `named_upgrade_path` inline if set + investigation flag inline if `f1_below_regression_threshold`. `_render_dswx_eu_cell` renders `f1=0.XX [PASS|FAIL]` (Balaton) + `named_upgrade_path` inline if set + LOO-CV gap diagnostic inline. Both BINDING (no italics). Plan-phase commits insertion-order tests per Phase 5 Plan 05-05 pattern.

- **D-28: Two CONCLUSIONS files per cell (Phase 3 D-08 inheritance).** Already covered in D-21. `CONCLUSIONS_DSWX_N_AM.md` (NEW, Phase 6) + `CONCLUSIONS_DSWX.md` (RENAMED-NOT, append v1.1 sections). Manifest unchanged.

- **D-29: criteria.py: ZERO edits to `dswx.f1_min` (BINDING, line 188).** Phase 6 makes ZERO edits to existing entries. Phase 6 MAY add `dswx.nam.investigation_f1_max=0.85` `INVESTIGATION_TRIGGER` entry per D-20 (Phase 2 D-13/D-14 pattern); plan-phase decides — non-gate, narrative-only. The DSWE F1 ≈ 0.92 ceiling claim in the docstring (line 192-194) MAY be revised post-grid-search if recalibration lands F1 > 0.92 (P5.3 contradiction); revision is a docstring edit, not a threshold edit.

- **D-30: matrix_manifest.yml unchanged.** Manifest already wires `dswx:nam` (run_eval_dswx_nam.py + eval-dswx_nam + CONCLUSIONS_DSWX_N_AM.md) + `dswx:eu` (run_eval_dswx.py + eval-dswx + CONCLUSIONS_DSWX.md). Phase 6 fills the metrics.json sidecars + creates the new N.Am. script + extends the EU script + creates the new threshold module + writes the recalibration script.

### Claude's Discretion (for plan-phase)

- **Per-(AOI, scene) gridscores serialisation format** (D-07: parquet vs JSON-lines). Plan-phase confirms `pyarrow` is in the conda-env; if yes, parquet; if no, JSON-lines. Verify with `python -c "import pyarrow"` in the conda-env probe stage.

- **Specific MGRS tiles for Tahoe + Pontchartrain candidates** (D-18). Lake Tahoe's lonlat range straddles MGRS tile 10SFH and 10SFG; Pontchartrain straddles 15RYR. Plan-phase commits exact tile (use the tile fully covering the lake; `bounds_for_mgrs_tile` returns the BBox).

- **`THRESHOLDS_NAM` provenance fields** (D-11). The N.Am. instance preserves PROTEUS defaults (WIGT=0.124, AWGT=0.0, PSWT2_MNDWI=−0.5); provenance fields filled with PROTEUS-paper sentinel values (e.g. `grid_search_run_date='1996-01-01-PROTEUS-baseline'`, `provenance_note='PROTEUS DSWE Algorithm Theoretical Basis Document defaults; never recalibrated for Sentinel-2'`, `fit_set_hash='n/a'`, `fit_set_mean_f1=float('nan')`, etc). Plan-phase commits exact wording.

- **Regression-investigation auto-flag → `criteria.py` INVESTIGATION_TRIGGER entry** (D-20). Phase 2 D-13/D-14 pattern (extending `Literal['BINDING', 'CALIBRATING', 'INVESTIGATION_TRIGGER']`); plan-phase decides whether to add `dswx.nam.investigation_f1_max=0.85` to the registry. Trade-off: gate prevention vs narrative discipline.

- **`_compute_diagnostic_tests` decomposition** (D-05). Decompose into `compute_index_bands(blue, green, red, nir, swir1, swir2) -> dict[str, np.ndarray]` + `score_water_class_from_indices(indices: dict, thresholds: DSWEThresholds) -> np.ndarray` so the grid search consumes the cheap second function. Plan-phase commits the public-symbol promotion (Phase 4 Plan 04-01 pattern: lift inner-scope functions to public module symbols).

- **EXPECTED_WALL_S for `recalibrate_dswe_thresholds.py`** (D-24). 6 hr estimate; cold path includes 12 SAFE downloads (~15 GB) + 12 scene-pipeline runs (each ~5-10 min on a warm DEM/JRC cache) + grid search (~5-15 min) + LOO-CV (~5-15 min). Plan-phase commits exact value with cold-vs-warm rationale. Supervisor budget = 2× per Phase 1 ENV-05.

- **§5.1 PROTEUS ATBD fetch path** (D-17). Plan-phase 06-01 picks: (a) Context7 MCP query for OPERA DSWx-HLS / PROTEUS ATBD; (b) WebFetch on the JPL OPERA documents page; (c) literature search via published F1 evaluation papers on DSWE. Tries (a) first; falls back to (b); falls back to (c); falls back to own-data bound. Plan-phase commits the citation chain in §5.1.

- **`run_eval_dswx_nam.py` Stage layout** (D-18). Should mirror existing `run_eval_dswx.py` 9-stage harness but with the `CANDIDATES` outer loop. Plan-phase commits exact stage breakdown — likely: 0. _mp + supervisor; 1. CDSE auth + credential preflight; 2. AOI candidate iteration + STAC search per candidate; 3. Cloud-free scene selection (first AOI wins); 4. SAFE download via CDSEClient; 5. DSWx pipeline (run_dswx with config.region='nam'); 6. Output inspection; 7. JRC tile fetch via harness retry; 8. compare_dswx with shoreline buffer; 9. metrics.json write + regression-flag assertion.

- **`scripts/recalibrate_dswe_thresholds.py` Stage layout** (D-04..D-08). Plan-phase commits exact stage breakdown — likely: 0. _mp + supervisor + N.Am. regression-flag assert (D-20); 1. AOI lock + fit-set SAFE download (joblib parallel over 5 AOIs × 2 scenes); 2. Per-scene intermediate-band cache compute (joblib parallel; D-05); 3. Joint grid search (joblib parallel over 12 (AOI, scene); D-06); 4. Aggregate to scripts/recalibrate_dswe_thresholds_results.json; 5. Edge-of-grid sentinel check (D-08); 6. LOO-CV post-hoc on best-gridpoint (D-14); 7. LOO-CV gap acceptance check (DSWX-06); 8. Held-out Balaton F1 (run pipeline on Balaton with best gridpoint); 9. Threshold module update — write `src/subsideo/products/dswx_thresholds.py` with new EU instance + provenance; 10. Notebook reproduce check (`papermill notebooks/dswx_recalibration.ipynb`).

- **`docs/dswx_fitset_aoi_selection.md` rendering mechanism** (D-01). Plan-phase decides whether the markdown copy is auto-generated from the notebook (via `jupyter nbconvert --to markdown`) or hand-written from the notebook output. Auto-generated keeps the rendered copy in sync but adds a Makefile target / pre-commit hook.

- **OSM / Copernicus Land Monitoring failure-mode tag query mechanism** (D-02). Plan-phase decides: (a) overpass-turbo Python client (overpass-api-python-wrapper); (b) Copernicus Land Monitoring CGLS-LC100 raster fetch; (c) hardcoded list of known glacier/frozen/turbid/shadow AOIs as a `dswx_failure_mode_aois.yml` resource. Trade-off: query-time cost vs maintenance burden.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source-of-truth scope (read first)

- `.planning/ROADMAP.md` §Phase 6 (lines 198-215) — goal, 5 success criteria, 7 requirements (DSWX-01..07), internal ordering (AOI research precedes fit-set compute commit).
- `.planning/REQUIREMENTS.md` §DSWX-01..07 (lines 73-80) — full text of the 7 requirements; DSWX-V2-01..03 future work for context (not Phase 6 scope).
- `.planning/PROJECT.md` — DSWx F1 > 0.90 pass criterion; v1.1 metrics-vs-targets discipline ("validators not quality ceilings"); key decision "DSWx F1 > 0.90 bar does not move during recalibration".
- `.planning/STATE.md` — Phase 5 closure status; Phase 1 ENV-04 _mp.py bundle status (complete) — pre-condition for `_compute_index_bands` joblib parallelism.
- `BOOTSTRAP_V1.1.md §5` — DSWx phase scope; F1 > 0.90 immutable bar; AOI research first-class sub-task; held-out Balaton; honest FAIL framing.

### Phase 1/2/3/4/5 CONTEXT (REQUIRED for understanding harness, criteria, schema, append-only doc policy, declarative-list pattern)

- `.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/01-CONTEXT.md` — D-01..D-19: criteria.py shape (frozen-dataclass + Literal['BINDING','CALIBRATING','INVESTIGATION_TRIGGER'] + `binding_after_milestone` field); split `ProductQualityResult` / `ReferenceAgreementResult`; `_mp.py` bundle (D-14 ENV-04) — pre-condition for joblib parallelism; supervisor mechanics (D-10..D-14 ENV-05); harness 5 helpers + per-source retry policy (D-Claude's-Discretion ENV-06) — Phase 6 adds 6th source 'jrc' to RETRY_POLICY; matrix_schema.py + matrix_writer.py + matrix_manifest.yml conventions.
- `.planning/phases/02-rtc-s1-eu-validation/02-CONTEXT.md` — D-04 probe-and-commit pattern (Phase 6 D-01 source); D-05/D-06 declarative AOIS-list + per-AOI try/except (Phase 6 D-18 source); D-09/D-10 single aggregate metrics.json + nested per_aoi/per_burst list + top-level aggregates (Phase 6 D-13 source); D-13/D-14/D-15 INVESTIGATION_TRIGGER discipline (Phase 6 D-20 source); D-12 cell-level meta.json with input hashes.
- `.planning/phases/03-cslc-s1-self-consistency-eu-validation/03-CONTEXT.md` — D-08 two CONCLUSIONS files per cell; D-15 docs/validation_methodology.md append-only by phase (Phase 6 owns §5 only, Phase 7 owns §6+); D-13 §1 leads with structural argument before diagnostic appendix (Phase 6 §5 leads with §5.1 ceiling structural argument before §5.2-§5.4 empirical evidence before §5.5 design rationale).
- `.planning/phases/04-disp-s1-comparison-adapter-honest-fail/04-CONTEXT.md` — D-11 Pydantic v2 schema additive extension (Phase 6 D-26 source); D-13 v1.0 narrative preserved as preamble in CONCLUSIONS (Phase 6 D-21 source); D-04 module-level constant pattern (Phase 6 D-09 + EXPECTED_WALL_S inheritance).
- `.planning/phases/05-dist-s1-opera-v0-1-effis-eu/05-CONTEXT.md` — D-04 plan-phase probe-then-commit (Phase 6 D-01 source); D-11 single declarative-AOIS-list (Phase 6 D-18 source); D-22 v1.0-baseline-preamble (Phase 6 D-21 source); D-24 matrix_writer dispatch ordering AFTER disp:* (Phase 6 D-27 places dswx:* AFTER dist:*); D-25 Pydantic v2 additive extension (Phase 6 D-26 mirrors); ROADMAP scope amendment §Phase 5 D-24 amendment (de-locks BEFORE-cslc/dswx clause; Phase 6 dswx:* after dist:* per Phase 5 amendment).

### Phase 6 research (authoritative for HOW)

- `.planning/research/SUMMARY.md` Phase 6 row (lines 180-184) — scope (N.Am. positive control + AOI research + grid search + threshold update + EU re-run); watch-outs (P5.1, P5.2, P5.3, P5.4, M4); single biggest schedule risk (fit-set quality caps F1 regardless of grid).
- `.planning/research/PITFALLS.md §P5.1` (lines 601-630) — DSWE 3-parameter grid search overfit; LOO-CV gap < 0.02; best-grid-point at edge sentinel; cross-validated stability check. D-08 + D-14 implement directly.
- `.planning/research/PITFALLS.md §P5.2` (lines 633-657) — JRC commission/omission asymmetry; shoreline pixel ambiguity; jrc_confidence pre-screen via < 5 cloud-free obs fraction; 1-pixel buffer exclusion. D-02 + D-16 implement directly.
- `.planning/research/PITFALLS.md §P5.3` (lines 660-682) — DSWE F1 ceiling 0.92 citation chain risk; PROTEUS ATBD direct verification; own-data fallback; ceiling claim isolation from criterion threshold. D-17 + D-22 §5.1 implement directly.
- `.planning/research/PITFALLS.md §P5.4` (lines 685-704) — wet/dry water-extent ratio < 1.2 reject; drought/flood year handling; alternate-year retry. D-03 implements directly.
- `.planning/research/PITFALLS.md §M4` — DSWx F1 > 0.90 bar does not move; honest FAIL with named upgrade path. D-15 implements (`named_upgrade_path` field).
- `.planning/research/FEATURES.md §Phase 5` (lines 90-100) — `run_eval_dswx_nam.py` + AOI research artifact + fit-set construction + `scripts/recalibrate_dswe_thresholds.py` (joint grid bounds explicit) + threshold update mechanism + `notebooks/dswx_recalibration.ipynb` + EU re-run + honest FAIL reporting.
- `.planning/research/FEATURES.md §anti-features` (lines 137-138, 148) — ML-replacement scope creep; F1 > 0.90 bar relaxation; interactive AOI picker UI.
- `.planning/research/ARCHITECTURE.md` — harness public API (Phase 6 reuses `bounds_for_mgrs_tile`, `download_reference_with_retry` with new 'jrc' source, `ensure_resume_safe`, `credential_preflight`); matrix_writer manifest-authoritative pattern (REL-02).
- `.planning/research/STACK.md` — `pydantic-settings 2.13.1` (DSWX-05 region selector); `joblib` (grid search parallelism — verify in conda env); `pyarrow` (parquet gridscores — verify); `scipy.ndimage.binary_dilation` (shoreline buffer; existing dep).

### v1.0 CONCLUSIONS (context for what Phase 6 inherits)

- `CONCLUSIONS_DSWX.md` (290 LOC, 2026-04-15) — Lake Balaton 2021-07-08, F1=0.7957 / precision=0.9236 / recall=0.6989 / accuracy=0.9838 against JRC. PROTEUS DSWE absolute PSWT2 thresholds over-fire on dry Pannonia summer landscapes. Phase 6 D-21 keeps this as v1.0 baseline preamble; v1.1 sections append below with recalibrated thresholds + held-out Balaton F1.
- `CONCLUSIONS_RTC_EU.md` (Phase 2) — template for the multi-section CONCLUSIONS shape (Calibration Framing + Investigation Discipline + Per-AOI Table + Aggregate Result). Phase 6 §4 + §5 (regression investigation when F1 < 0.85) reuse this discipline.
- `CONCLUSIONS_DISP_EU.md` + `CONCLUSIONS_DIST_EU.md` (Phase 4 + Phase 5) — template for v1.0-baseline-preamble + v1.1-section-append pattern (Phase 4 D-13 / Phase 5 D-22). Phase 6 D-21 mirrors.

### v1.0 precedent files to match (existing conventions)

- `src/subsideo/products/dswx.py` (803 LOC) — primary modification surface. v1.0 has WIGT/AWGT/PSWT*/CLAVERIE_S2A/INTERPRETED_WATER_CLASS module-level constants + `_compute_diagnostic_tests` + `_classify_water` + `_rescue_connected_wetlands` + `_apply_scl_mask` + `run_dswx`/`run_dswx_from_aoi`. Phase 6 changes per D-12: DELETE WIGT, AWGT, PSWT2_MNDWI module-level constants; KEEP PSWT1_*, PSWT2_BLUE/NIR/SWIR1/SWIR2 (not in recalibration grid); `_compute_diagnostic_tests` gains `thresholds: DSWEThresholds` keyword; `run_dswx` resolves region per D-10. DECOMPOSE per D-05: lift index-band computation to public `compute_index_bands` + threshold-and-classify to public `score_water_class_from_indices`.
- `src/subsideo/products/types.py` (~200 LOC) — `DSWxConfig` dataclass currently carries `s2_band_paths`, `scl_path`, `output_dir`, `output_epsg`, `output_posting_m`, `product_version`. Phase 6 ADDS: `region: Literal['nam', 'eu'] | None = None` (D-10).
- `src/subsideo/products/dswx_thresholds.py` — NEW file (Phase 6 D-09..D-12). Frozen dataclass `DSWEThresholds` + `THRESHOLDS_NAM` instance (PROTEUS defaults, sentinel provenance) + `THRESHOLDS_EU` instance (recalibrated, full provenance) + `THRESHOLDS_BY_REGION: dict[str, DSWEThresholds]`. ~80-150 LOC.
- `src/subsideo/validation/compare_dswx.py` (330 LOC) — primary modification surface. v1.0 `compare_dswx(...)` returns `DSWxValidationResult`. Phase 6 ADDS: shoreline 1-pixel buffer mask (D-16); refactor JRC fetch via `harness.download_reference_with_retry(source='jrc')` (D-25); split F1 reporting into `f1` (gate, shoreline-excluded) + `f1_full_pixels` (diagnostic). compare_dswx return type extended with diagnostics dict.
- `src/subsideo/validation/criteria.py` — `dswx.f1_min = 0.90` BINDING already shipped (line 188). ZERO Phase 6 edits to existing entries. Phase 6 MAY add `dswx.nam.investigation_f1_max = 0.85` INVESTIGATION_TRIGGER entry per D-20 + Claude's Discretion.
- `src/subsideo/validation/harness.py` — 5 helpers consumed; Phase 6 ADDS 6th branch to `RETRY_POLICY` for `'jrc'` source (D-25).
- `src/subsideo/validation/supervisor.py` — Phase 6 scripts declare `EXPECTED_WALL_S` per Phase 1 D-11 (D-24).
- `src/subsideo/validation/matrix_schema.py` (post-Phase-5 LOC) — Pydantic v2 base. Phase 6 ADDS new types per D-26: `DswxNamCellMetrics`, `DswxEUCellMetrics`, `DSWEThresholdsRef`, `PerAOIF1Breakdown`, `LOOCVPerFold`, `RegressionDiagnostic`. ZERO edits to existing types.
- `src/subsideo/validation/matrix_writer.py` (post-Phase-5 LOC) — manifest-driven cell renderer. Phase 6 ADDS `dswx:nam` + `dswx:eu` render branches (D-27). Order: AFTER `dist:*` per Phase 5 D-24 amendment (Phase 5 D-24 left BEFORE-cslc/dswx as a contemporary observation, not a forward lock; Phase 6 places after dist:nam by structural-disjointness argument).
- `src/subsideo/validation/metrics.py` — `f1_score`/`precision_score`/`recall_score`/`overall_accuracy` consumed unchanged.
- `run_eval_dswx.py` (303 LOC v1.0) — EU eval, primary modification target. Phase 6 changes: (1) Stage 0 _mp + supervisor (already wrapped via Makefile); (2) Stage 5 `run_dswx(config=DSWxConfig(..., region='eu'))` (D-10 DSWxConfig extension); (3) Stage 8 `compare_dswx` consumes shoreline buffer (D-16); (4) Stage 9 metrics.json write per `DswxEUCellMetrics` schema (D-26); (5) Module-level `EXPECTED_WALL_S` constant per D-24 (already present at line 27 = 900; plan-phase decides whether to raise post-Phase-6 changes or keep).
- `run_eval_dswx_nam.py` — NEW file (Phase 6 deliverable per FEATURES Phase 5). Forks `run_eval_dswx.py` 9-stage harness; replaces single Balaton AOI with `CANDIDATES` declarative list (D-18). Stage layout per Claude's Discretion above.
- `scripts/recalibrate_dswe_thresholds.py` — NEW file (Phase 6 deliverable per REQUIREMENTS DSWX-04). Multi-stage script: SAFE download → intermediate cache → grid search → LOO-CV → threshold module update. Stage layout per Claude's Discretion above.
- `notebooks/dswx_aoi_selection.ipynb` — NEW file (Phase 6 deliverable per REQUIREMENTS DSWX-02). Per-candidate scoring + 5 selected + reasoning + rendered to `docs/dswx_fitset_aoi_selection.md`.
- `notebooks/dswx_recalibration.ipynb` — NEW file (Phase 6 deliverable per REQUIREMENTS DSWX-05). Loads scripts/recalibrate_dswe_thresholds_results.json + plots F1 surface + shows held-out Balaton F1 + reproduces frozen constants from results JSON.
- `eval-dswx_nam/` — NEW cache directory (Phase 6 D-30; manifest already references); populated at runtime.
- `eval-dswx-fitset/` — NEW cache directory (Phase 6 D-05); per-(AOI, scene) intermediate cache + gridscores parquet/JSON-lines.
- `eval-dswx/` — existing cache (v1.0 Balaton); Phase 6 EU re-run uses the SAME directory (manifest unchanged) — Balaton stays as the held-out test set per BOOTSTRAP §5.2.
- `results/matrix_manifest.yml` — already lists `dswx:nam` (run_eval_dswx_nam.py + eval-dswx_nam/ + CONCLUSIONS_DSWX_N_AM.md) + `dswx:eu` (run_eval_dswx.py + eval-dswx/ + CONCLUSIONS_DSWX.md). Phase 6 fills the metrics.json sidecars at runtime; no manifest schema edits (D-30).
- `Makefile` — `eval-dswx-nam` + `eval-dswx-eu` + `recalibrate-dswx` targets (verify in plan-phase; Phase 1 D-08 wired all 10 cells; Phase 6 verifies `recalibrate-dswx` target exists or adds it).
- `CONCLUSIONS_DSWX.md` (290 LOC) — v1.0 Balaton narrative; Phase 6 appends v1.1 sections per D-21.
- `CONCLUSIONS_DSWX_N_AM.md` — NEW file (Phase 6 deliverable; manifest already references).
- `docs/validation_methodology.md` (post-Phase-5 LOC; §1 + §2 + §3 + §4 landed) — Phase 6 appends §5 only per D-22 (Phase 3 D-15 single-PR-per-phase append).

### External library refs (read as-needed during plan-phase)

- `pydantic-settings 2.13.1` — `BaseSettings` for `SUBSIDEO_DSWX_REGION` env-var (D-10). Pattern in `src/subsideo/config.py` (verify exists).
- `joblib` — `Parallel(n_jobs=-1, backend='loky')` for grid-search parallelism (D-06). Loky inherits `_mp.configure_multiprocessing()` bundle.
- `pyarrow` — `pyarrow.parquet.write_table` for gridscores parquet (D-07; fallback to JSON-lines if not in env).
- `scipy.ndimage.binary_dilation` — shoreline 1-pixel buffer (D-16). Already in v1.0 deps via `_rescue_connected_wetlands`.
- `numpy.random.default_rng` (PCG64, modern) for any LOO-CV randomization (D-14; fold ordering is deterministic 1..12, no rng needed unless plan-phase adds bootstrap CI on F1).
- `rasterio` + `rasterio.features.rasterize` — JRC tile reproject (existing).
- `urllib.request` — current JRC fetch in `compare_dswx._fetch_jrc_tile`; refactor to harness retry per D-25.
- `papermill` (optional) — auto-execute `notebooks/dswx_recalibration.ipynb` as a check (Plan 06-N stage).
- `jupyter nbconvert --to markdown` (optional) — auto-render `notebooks/dswx_aoi_selection.ipynb` to `docs/dswx_fitset_aoi_selection.md` (Claude's Discretion above).

### PROTEUS ATBD reference (plan-phase 06-01 fetches; D-17)

- OPERA DSWx-HLS Algorithm Theoretical Basis Document (PROTEUS): https://www.jpl.nasa.gov/go/opera/products/dswx-product-suite (root) — plan-phase resolves to specific ATBD PDF URL.
- DSWE algorithm origin papers (linked from PROTEUS ATBD): Jones, J. W. 2015 "Efficient Wetland Surface Water Detection and Monitoring via Landsat" + 2019 expansion. Plan-phase 06-01 fetches PROTEUS ATBD; if numerical F1 ceiling not specifically cited, fall back to own-data bound per D-17.

### EU fit-set candidate AOIs (plan-phase 06-01 probes + locks; D-01)

Starting candidate list from BOOTSTRAP §5.2 (plan-phase 06-01 verifies cloud-free + JRC confidence + wet/dry ratio + OSM failure-mode tags + commits 5 selected):

- **Mediterranean reservoir**: Embalse de Alcántara (Spain) | Lago di Bracciano (Italy) | Embalse de Buendía (Spain).
- **Atlantic estuary**: Tagus estuary (Portugal) | Loire estuary (France) | Severn estuary (UK).
- **Boreal lake**: Vänern (Sweden) | Saimaa (Finland) | Mälaren (Sweden).
- **Pannonian plain**: Balaton (Hungary) — fixed as held-out, NOT a fit-set AOI.
- **Alpine valley**: Lago di Garda (Italy) | Lac Léman (Switzerland/France) | Lago Maggiore (Italy/Switzerland).
- **Iberian summer-dry**: Embalse de Alarcón (Spain) | Albufera de Valencia (Spain) | Doñana wetlands (Spain).

Plan-phase 06-01 commits 1 per biome (excluding Pannonian) + reasoning for rejections in `dswx_fitset_aoi_candidates.md`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`src/subsideo/products/dswx.py` (803 LOC)** — primary surface. v1.0 has `_compute_diagnostic_tests` + `_classify_water` + `_rescue_connected_wetlands` + `_apply_scl_mask` + `run_dswx`/`run_dswx_from_aoi` + module-level WIGT/AWGT/PSWT*/CLAVERIE_S2A/INTERPRETED_WATER_CLASS. Phase 6 EXTENDS: (a) DELETE WIGT, AWGT, PSWT2_MNDWI module-level (D-12); (b) `_compute_diagnostic_tests` gains required `thresholds: DSWEThresholds` keyword (D-12); (c) DECOMPOSE into public `compute_index_bands` + `score_water_class_from_indices` for grid search re-use (D-05); (d) `run_dswx` resolves region per D-10.
- **`src/subsideo/products/types.py`** — `DSWxConfig` dataclass; ADD `region: Literal['nam', 'eu'] | None = None` (D-10). Existing `DSWxValidationResult` consumed unchanged (Phase 6 D-26 adds new Pydantic types in matrix_schema, doesn't touch the dataclass).
- **`src/subsideo/validation/compare_dswx.py` (330 LOC)** — primary surface. ADDS shoreline 1-pixel buffer (D-16); refactors JRC fetch via harness retry (D-25); extends F1 reporting with diagnostics dict.
- **`src/subsideo/validation/criteria.py`** — ZERO edits to `dswx.f1_min` (line 188). Phase 6 MAY add `dswx.nam.investigation_f1_max = 0.85` INVESTIGATION_TRIGGER per D-20 (plan-phase decides).
- **`src/subsideo/validation/harness.py`** — ADDS 6th branch `RETRY_POLICY['jrc']` (D-25). Existing 5 helpers consumed unchanged.
- **`src/subsideo/validation/supervisor.py`** — Phase 6 scripts declare `EXPECTED_WALL_S` per Phase 1 D-11.
- **`src/subsideo/validation/matrix_schema.py`** — Pydantic v2 base. ADDS new types per D-26; zero edits to existing.
- **`src/subsideo/validation/matrix_writer.py`** — ADDS `dswx:nam` + `dswx:eu` render branches per D-27 (AFTER `dist:*`).
- **`src/subsideo/validation/metrics.py`** — `f1_score`/`precision_score`/`recall_score`/`overall_accuracy` consumed unchanged.
- **`run_eval_dswx.py` (303 LOC v1.0)** — EU eval, primary modification target. 5 changes per D-26: DSWxConfig.region='eu', shoreline buffer in compare_dswx call, metrics.json schema upgrade to DswxEUCellMetrics, raise EXPECTED_WALL_S if needed.
- **`run_eval_dswx_nam.py`** — NEW file (Phase 6 deliverable). Forks `run_eval_dswx.py` with `CANDIDATES` declarative list per D-18.
- **`scripts/recalibrate_dswe_thresholds.py`** — NEW file (Phase 6 deliverable per REQUIREMENTS DSWX-04 + D-04..D-08).
- **`notebooks/dswx_aoi_selection.ipynb` + `notebooks/dswx_recalibration.ipynb`** — NEW files (Phase 6 deliverables per REQUIREMENTS DSWX-02 + DSWX-05 + D-04).
- **`src/subsideo/products/dswx_thresholds.py`** — NEW file per D-09..D-12. Frozen dataclass + 2 instances + dispatch dict.
- **`CONCLUSIONS_DSWX.md` (290 LOC) + `CONCLUSIONS_DSWX_N_AM.md`** — v1.0 narrative kept as v1.0 baseline preamble (D-21); new N.Am. file Phase 6 creates.
- **`docs/validation_methodology.md`** — append §5 only (D-22) per Phase 3 D-15 single-PR-per-phase append discipline.

### Established Patterns

- **`_mp.configure_multiprocessing()` at top of every `run_*()`** — Phase 1 ENV-04 D-14. PRE-CONDITION for joblib parallelism in `recalibrate_dswe_thresholds.py` (D-23).
- **Subprocess-level supervisor watchdog** — Phase 1 D-10..D-14. Phase 6 declares `EXPECTED_WALL_S` per script (D-24).
- **Per-source retry policy in harness.RETRY_POLICY** — Phase 1 ENV-06 + Phase 5 D-18 'effis'. Phase 6 adds 6th source 'jrc' (D-25).
- **Lazy imports for conda-forge deps** — Phase 1 lazy-import discipline. New code (`compute_index_bands`, `score_water_class_from_indices`, shoreline buffer) imports `numpy` at module top + heavy deps (rasterio, scipy, joblib) inside function bodies.
- **Declarative module-level constants** — `EXPECTED_WALL_S`, `MAX_CLOUD_COVER`, `JRC_YEAR`, `JRC_MONTH` at module top; auditable in git (Phase 1 D-11 + Phase 4 D-04 + Phase 5 D-12).
- **Declarative AOI list with per-AOI try/except** — Phase 2 D-05/D-06 + Phase 5 D-11. Phase 6 D-18 mirrors for `run_eval_dswx_nam.py` CANDIDATES + Phase 6 D-04 mirrors for `recalibrate_dswe_thresholds.py` AOI fit-set.
- **Aggregate metrics.json + nested per_aoi/per_event/per_burst sub-results** — Phase 2 D-09/D-10 + Phase 4 D-11 + Phase 5 D-25. Phase 6 D-26 mirrors for `DswxEUCellMetrics.reference_agreement.diagnostics.per_aoi_breakdown[]`.
- **Cell-level meta.json with input hashes** — Phase 2 D-12. Phase 6 includes per-AOI input hashes (S2 SAFE hashes, JRC tile hashes, intermediate-band cache hashes, threshold module sha256).
- **Matrix-writer manifest-authoritative** — never globs CONCLUSIONS_*.md; reads from `metrics.json` only via `matrix_manifest.yml` (REL-02 PITFALLS R3 + R5 mitigation).
- **Two CONCLUSIONS files per cell** — Phase 3 D-08 + Phase 4 D-22 + Phase 5 D-22. `CONCLUSIONS_DSWX_N_AM.md` + `CONCLUSIONS_DSWX.md` pattern (D-21 + D-30).
- **`docs/validation_methodology.md` append-only by phase** — Phase 3 D-15 + Phase 4 D-23 + Phase 5 D-23. Phase 6 owns §5 (D-22).
- **First-rollout CALIBRATING italicisation** — Phase 4 D-19. NOT applicable to Phase 6 (DSWx is BINDING reference-agreement only; no new CALIBRATING gates).
- **Auto-attribute Literal schema for status enums** — Phase 4 D-11 `attributed_source` + Phase 5 D-25 `cell_status` + `cmr_probe_outcome` + `reference_source`. Phase 6 D-15 reuses pattern via `named_upgrade_path: str | None` (free-text, NOT a Literal — three semantic states with citation strings).
- **v1.0 narrative preserved as baseline preamble in CONCLUSIONS** — Phase 4 D-13 + Phase 5 D-22. Phase 6 D-21 reuses for EU CONCLUSIONS_DSWX.md (Balaton baseline).
- **INVESTIGATION_TRIGGER discipline** — Phase 2 D-13/D-14/D-15. Phase 6 D-20 reuses for N.Am. F1 < 0.85 regression flag.
- **Probe-and-commit pattern** — Phase 2 D-04 (RTC EU bursts) + Phase 3 03-02 (CSLC AOI candidates) + Phase 5 D-04 (config-drift extraction). Phase 6 D-01 reuses for fit-set AOI candidates.

### Integration Points

- **Manifest already wires the cells** — `dswx:nam` + `dswx:eu` exist in `matrix_manifest.yml` (D-30); Phase 6 fills `metrics.json` at runtime.
- **Makefile already has targets** — `eval-dswx-nam` + `eval-dswx-eu`; Phase 6 fills/extends the referenced scripts. Plan-phase verifies `recalibrate-dswx` target exists or adds it.
- **Harness already supports plain HTTPS retry** (Phase 1 ENV-06 + ENV-07); Phase 6 just adds 'jrc' policy entry + refactors `_fetch_jrc_tile` to consume the harness wrapper.
- **`_mp.configure_multiprocessing()` already lands** at top of `run_eval_dswx*` (Phase 1 ENV-04); Phase 6 just consumes for `run_eval_dswx_nam.py` + `recalibrate_dswe_thresholds.py`.
- **Supervisor already wraps** every `run_*()` invocation; Phase 6 declares `EXPECTED_WALL_S` per script.
- **`compare_dswx` already exists** with v1.0 F1 logic; Phase 6 extends with shoreline buffer + diagnostics dict.
- **`dswx:nam` + `dswx:eu` render branches** insertion order in `matrix_writer.py`: AFTER `dist:*` per Phase 5 D-24 amendment (Phase 6 D-27).
- **`DSWxConfig` already has reflectance/output fields**; Phase 6 ADDS `region: Literal['nam', 'eu'] | None` (D-10).
- **`run_dswx` already orchestrates band-read → DSWE → COG-write**; Phase 6 threads `thresholds: DSWEThresholds` + `region` through the pipeline.
- **`pydantic-settings` `BaseSettings`** in `src/subsideo/config.py` — Phase 6 ADDS `SUBSIDEO_DSWX_REGION` env-var (D-10); plan-phase verifies pattern + extends.

### Script / Cell Flow (data shape)

```
run_eval_dswx_nam.py (NEW):
  EXPECTED_WALL_S = 1800  # 30 min single AOI single scene
  CANDIDATES: list[AOIConfig] = [tahoe, pontchartrain]  # D-18 declarative

  # Stage 0: _mp + credential preflight
  _mp.configure_multiprocessing()
  credential_preflight(["CDSE_CLIENT_ID", "CDSE_CLIENT_SECRET", "CDSE_S3_ACCESS_KEY", "CDSE_S3_SECRET_KEY"])

  # Stage 1: AOI candidate iteration + STAC search per candidate
  selected_aoi = None
  candidates_attempted = []
  for cand in CANDIDATES:
    stac_items = cdse.search_stac(collection="SENTINEL-2", bbox=cand.bbox, datetime=cand.window, ...)
    cloud_free = [it for it in stac_items if it.properties.cloud_cover < cand.max_cloud_cover]
    candidates_attempted.append({aoi_name, scenes_found: len(stac_items), cloud_min: min(...)})
    if cloud_free:
      selected_aoi = cand
      selected_scene = sorted(cloud_free, key=cloud_cover)[0]
      break
  if selected_aoi is None:
    write metrics.json with cell_status='BLOCKER'; exit non-zero

  # Stage 2-7: SAFE download, DSWx pipeline, JRC fetch, compare_dswx (with shoreline buffer)
  result = run_dswx(DSWxConfig(..., region='nam'))  # D-10 region selector
  validation = compare_dswx(result.output_path, ..., shoreline_buffer_px=1)  # D-16

  # Stage 8: regression flag (D-20)
  f1_below_regression = validation.f1 < 0.85
  regression_diagnostics = ['boa_offset_check', 'claverie_xcal_check', 'scl_mask_audit'] if f1_below_regression else []

  # Stage 9: write DswxNamCellMetrics (D-26)
  metrics = DswxNamCellMetrics(
    schema_version=1,
    selected_aoi=selected_aoi.name,
    selected_scene_id=selected_scene.id,
    cloud_cover_pct=selected_scene.cloud_cover,
    candidates_attempted=candidates_attempted,
    region='nam',
    reference_agreement=ReferenceAgreementResultJson(
      measurements={'f1': validation.f1, ...},  # shoreline-excluded
      diagnostics={'f1_full_pixels': validation.f1_full, 'shoreline_buffer_excluded_pixels': ...},
      criterion_ids=['dswx.f1_min'],
    ),
    f1_below_regression_threshold=f1_below_regression,
    regression_diagnostic_required=regression_diagnostics,
    investigation_resolved=False,
    cell_status='PASS' if validation.f1 >= 0.90 else 'FAIL',
    named_upgrade_path=None if validation.f1 >= 0.90 else (
      'ML-replacement (DSWX-V2-01)' if validation.f1 >= 0.85 else 'BOA-offset / Claverie cross-cal regression'
    ),
  )
  write eval-dswx_nam/metrics.json + meta.json

scripts/recalibrate_dswe_thresholds.py (NEW):
  EXPECTED_WALL_S = 21600  # 6 hr full fit-set + grid + LOO-CV

  # Stage 0: _mp + N.Am. regression-flag assert (D-20)
  _mp.configure_multiprocessing()
  nam_metrics = json.load("eval-dswx_nam/metrics.json")
  assert not nam_metrics["f1_below_regression_threshold"] OR nam_metrics["investigation_resolved"]

  # Stage 1: AOI lock from .planning/milestones/v1.1-research/dswx_fitset_aoi_candidates.md
  AOIs = [aoi1, aoi2, aoi3, aoi4, aoi5]  # 5 fit-set + 1 held-out (Balaton) — Balaton not in this list
  # Plan-phase 06-01 commits these post-probe-artifact lock

  # Stage 2: SAFE download (joblib parallel; per Phase 5 D-11 try/except isolation)
  Parallel(n_jobs=-1)(delayed(download_safe_pair)(aoi) for aoi in AOIs)

  # Stage 3: Per-scene intermediate cache compute (joblib parallel; D-05)
  Parallel(n_jobs=-1)(delayed(compute_intermediates)(aoi, scene) for aoi in AOIs for scene in [wet, dry])

  # Stage 4: Joint grid search (joblib parallel; D-06)
  results = Parallel(n_jobs=-1)(
    delayed(grid_search_one_pair)(aoi, scene)  # 8400 gridpoints sequential per pair
    for aoi in AOIs for scene in [wet, dry]
  )
  # results: list of dicts; each {aoi, scene, gridscores: list[(WIGT, AWGT, PSWT2_MNDWI, f1, precision, recall, accuracy, n_pixels)]}

  # Stage 5: Aggregate to scripts/recalibrate_dswe_thresholds_results.json
  joint_best = argmax over all (W, A, P) of mean(f1 across 12 (AOI, scene) at that gridpoint)

  # Stage 6: Edge-of-grid sentinel (D-08)
  if joint_best at any axis boundary:
    write results.json with cell_status='BLOCKER' + edge_check.status='at_edge'
    exit non-zero

  # Stage 7: LOO-CV post-hoc (D-14)
  loocv_per_fold = []
  for left_out_idx in range(12):
    subset = AOIs without index left_out_idx
    refit_best = argmax over (W, A, P) of mean(f1 across 11)
    test_f1 = score(subset_left_out, refit_best)
    loocv_per_fold.append({left_out: left_out_idx, refit_best, test_f1})
  loocv_mean_f1 = mean(loocv_per_fold[*].test_f1)
  loocv_gap = fit_set_mean_f1 - loocv_mean_f1

  # Stage 8: LOO-CV gap acceptance check (DSWX-06)
  if loocv_gap >= 0.02:
    write results.json with cell_status='BLOCKER' + loocv_gap_violation=True
    exit non-zero

  # Stage 9: Held-out Balaton F1 (run pipeline with best gridpoint on Balaton; D-13)
  # This becomes the OFFICIAL EU matrix-cell F1
  balaton_f1 = run_pipeline_with_thresholds(balaton, joint_best)

  # Stage 10: Threshold module update (D-09..D-12)
  # Write src/subsideo/products/dswx_thresholds.py with:
  #   THRESHOLDS_EU = DSWEThresholds(WIGT=joint_best.W, AWGT=joint_best.A, PSWT2_MNDWI=joint_best.P,
  #     grid_search_run_date='2026-04-XX', fit_set_hash=sha256(...), fit_set_mean_f1=...,
  #     held_out_balaton_f1=balaton_f1, loocv_mean_f1=..., loocv_gap=..., 
  #     notebook_path='notebooks/dswx_recalibration.ipynb',
  #     results_json_path='scripts/recalibrate_dswe_thresholds_results.json')

  # Stage 11: papermill notebooks/dswx_recalibration.ipynb (Claude's Discretion)
```

</code_context>

<specifics>
## Specific Ideas

- **Held-out Balaton is THE official EU matrix-cell F1** — D-13. This single decision is non-negotiable per BOOTSTRAP §5.4 + PITFALLS P5.1 explicit. The `cell_status='FAIL' + named_upgrade_path='ML-replacement (DSWX-V2-01)'` outcome on 0.85 ≤ Balaton F1 < 0.90 is the milestone-discipline-correct framing — fit-set mean F1 cannot collapse the matrix-cell verdict.
- **The grid search caching strategy is the single largest runtime lever** — D-05. Pre-computing 5 index bands per scene reduces per-gridpoint cost from "re-read SAFE → BOA offset → Claverie cross-cal → MNDWI/NDVI/AWESH/MBSRV/MBSRN → threshold" to "load 5 numpy arrays → threshold → score". ~20× speedup translates to 6 hr cold → 25 min warm — re-runs after threshold tweaks become tractable.
- **Frozen dataclass with slots=True over NamedTuple** — D-09. The REQUIREMENTS phrasing said "NamedTuple" but the existing subsideo immutable-typed-constants pattern (criteria.py `Criterion`) is frozen-dataclass. Matching the in-codebase pattern is more important than literal REQUIREMENTS phrasing — provenance fields (D-11) flow naturally as dataclass attributes whereas NamedTuple needs them as separate module constants alongside.
- **Honest FAIL via `named_upgrade_path` field, not Literal extension** — D-15. Adding a Literal value `'FAIL_WITH_UPGRADE_PATH'` would force every matrix_writer dispatcher (Phase 1 + 2 + 3 + 4 + 5) to handle a state that doesn't apply to other products. The structured side-channel field keeps the cell_status Literal stable; matrix_writer concatenates `named_upgrade_path` only when set.
- **Edge-of-grid auto-FAIL is a hard gate, not a warning** — D-08. PITFALLS P5.1 explicit: edge-best-point means the grid was too narrow. Silently accepting it would publish miscalibrated thresholds. The auto-FAIL forces plan-phase or human to expand grid bounds + re-run — a rare path but the gate prevents the failure mode at zero cost when it doesn't trigger.
- **Shoreline buffer applied uniformly in BOTH grid search AND final reporting** — D-16. Avoids fit/eval kernel mismatch (rejected option B). Single source of truth for what counts as a fair F1; transparent via `f1_full_pixels` diagnostic.
- **F1 ceiling citation is plan-phase 06-01's homework** — D-17. PROTEUS ATBD direct fetch is the gold path; own-data fallback is the floor. Plan-phase 06-01 commits the citation chain in `docs/validation_methodology.md §5.1` BEFORE Phase 6 close — the ceiling claim must be ground-referenced at the moment Phase 6 ships, not deferred to Phase 7 audit.
- **The decomposition of `_compute_diagnostic_tests` into `compute_index_bands` + `score_water_class_from_indices` is the architectural enabler** — D-05. Without that public-symbol promotion, the grid search must re-call `_compute_diagnostic_tests` per gridpoint and re-do BOA + Claverie + index compute, which costs the 20× speedup. Plan-phase commits the public-symbol promotion (Phase 4 Plan 04-01 pattern).
- **Phase 6 is the single biggest schedule risk per BOOTSTRAP and SUMMARY** — fit-set quality caps F1. The probe-and-commit + plan-phase user lock (D-01) is the time-box guardrail; without it, fit-set construction commits compute against AOIs that can silently cap F1 at 0.85.

</specifics>

<deferred>
## Deferred Ideas

- **ML-replacement algorithm path for DSWE** (random forest on band composites) — DSWX-V2-01; named upgrade path; folded into Phase 6 D-15 `named_upgrade_path` for 0.85 ≤ F1 < 0.90 outcomes; not Phase 6 scope.
- **Global recalibration expanding fit set from 6 AOIs to 20–30** (tropical savanna, rainforest, desert, monsoon, subtropical, cold arid biomes) — DSWX-V2-02; v2 global milestone.
- **Turbid-water / frozen-lake / mountain-shadow / tropical-haze handling** — DSWX-V2-03; v2 algorithm work; out of Phase 6 scope (Phase 6 pre-screens AOIs to AVOID these failure modes; not solving them).
- **Bootstrap CI on F1 (block-bootstrap from Phase 5 D-06 reused)** — out of Phase 6 scope; Phase 5 `validation/bootstrap.py` is reusable for non-F1 metrics if Phase 6 plan-phase decides DSWx F1 needs CI bands. Default: scalar F1 with point-estimate per BOOTSTRAP §5.4 phrasing. Plan-phase decides.
- **Per-AOI threshold tuning (regional-not-global within EU)** — out of scope. Recalibration produces a single EU threshold set per BOOTSTRAP §5.3 'Optimise mean F1 across 12 fit-set pairs.' AOI-specific thresholds would re-introduce target-creep + couple validation to AOI-specific quirks.
- **Interactive AOI picker UI for fit-set selection** — Anti-feature per FEATURES §148. Notebook + scripted query is sufficient.
- **README PASS/FAIL badge for DSWx outcome** — Anti-feature per FEATURES §145. Matrix is the canonical status artifact.
- **DSWx-S1 / DSWx-HLS new product classes** — Out of scope per PROJECT.md.
- **`subsideo validate-dswx` CLI subcommand** — Out of scope; eval scripts + Makefile + `make eval-dswx-{nam,eu}` are the surface.
- **PROTEUS ATBD upstream PR** (e.g. correcting the F1 ceiling phrasing if Phase 6 grid search lands F1 > 0.92) — DSWX-V2 future work; not Phase 6 deliverable.
- **`dswx_thresholds.py` extension to per-biome thresholds** — Out of Phase 6 scope. EU/N.Am. region selector is the only granularity (D-10). Per-biome tuning is v2 if it ever proves necessary.
- **Matrix cell trendline / diff column (vs previous run)** — FEATURES Phase 6 differentiator (line 125); not Phase 6 (DSWx) scope; Phase 7 (Results Matrix) decides.
- **Burst-database-backed AOI catalogue query API** — FEATURES Phase 6 differentiator (line 126); v2 scope per FEATURES.
- **`compute_index_bands` / `score_water_class_from_indices` promotion to public API in `subsideo.products`** — Promote at decomposition time per D-05 (Phase 4 Plan 04-01 promotion pattern). The functions become public symbols in `products/dswx.py` so the recalibration script imports them; v2 may add a third consumer (e.g. ML-replacement path needs `compute_index_bands` as feature input).
- **Block-bootstrap CI on Balaton F1** — Phase 6 reports point F1; Phase 5 `validation/bootstrap.py` is available if plan-phase decides CI is needed. Default: point estimate.
- **`docs/validation_methodology.md` cross-section index / table-of-contents** — Phase 7 territory per Phase 3 D-15 append-only; Phase 6 §5 sub-sections only, no index added.

### Reviewed Todos (not folded)

No pending todos matched Phase 6 (`gsd-tools list-todos` returned `count: 0`).

</deferred>

---

*Phase: 06-dswx-s2-n-am-eu-recalibration*
*Context gathered: 2026-04-26*
