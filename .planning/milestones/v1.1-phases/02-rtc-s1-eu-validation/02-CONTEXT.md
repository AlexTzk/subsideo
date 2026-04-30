# Phase 2: RTC-S1 EU Validation - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 is the **first user of the Phase 1 harness on a real matrix cell**. It proves EU reproducibility for the deterministic product (RTC-S1) across ≥3 terrain regimes and delivers:

- **Candidate-burst probe** (`.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md`) — ASF OPERA-RTC coverage + cache status + best-match sensing date per BOOTSTRAP §1.1 candidate.
- **`run_eval_rtc_eu.py`** — single script with a declarative `BURSTS` list covering 5 regimes (Alpine >1000 m relief, Scandinavian >55°N, Iberian arid, Bologna temperate-flat cached, Portuguese fire cached), looping over bursts with per-burst try/except isolation.
- **Single `eval-rtc-eu/metrics.json`** — aggregate summary (`pass_count/total`, worst RMSE/r, product_quality + reference_agreement sub-aggregates) + nested `per_burst: [...]` list; single `eval-rtc-eu/meta.json` for provenance. Matrix writer reads the aggregate; per-burst drilldown lives in the file and in `CONCLUSIONS_RTC_EU.md`.
- **`CONCLUSIONS_RTC_EU.md`** — mirrors `CONCLUSIONS_RTC_N_AM.md`, adds the mandatory terrain-regime coverage table `{burst_id, lat, max_relief_m, cached?}` (P1.1), and automated per-burst investigation sub-sections for bursts that cross the trigger.
- **Shared harness reuse across eval cells** — `eval-rtc-eu/` reuses cached SAFEs from `eval-disp-egms/` (Bologna) and `eval-dist-eu/` (Portuguese fire) via a harness search-path fallback — no symlink, no copy, no duplication.

**Not this phase:** modifying `validation/compare_rtc.py` (no changes needed — already returns nested `ProductQualityResult` + `ReferenceAgreementResult` from Phase 1); tightening criteria based on per-burst scores (RTC-02 explicit, PITFALLS M1); per-burst Makefile targets (Phase 1 deferred, Phase 2 reaffirms that a single `eval-rtc-eu` target suffices); parallelism over bursts; opera-rtc internals.

Phase 2 covers the 3 requirements mapped to it: **RTC-01** (per-burst PASS/FAIL, ≥3 regimes, ≥1 >1000 m relief AND ≥1 >55°N), **RTC-02** (EU criteria identical to N.Am. — do not tighten), **RTC-03** (CONCLUSIONS with selected bursts, regime coverage, per-burst numbers, and investigation findings where RMSE is materially different from N.Am.).

</domain>

<decisions>
## Implementation Decisions

### Burst selection & probe

- **D-01: Standalone probe artifact produced BEFORE eval execution.** A dedicated `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` is committed as a Phase 2 sub-deliverable. One row per BOOTSTRAP §1.1 candidate (plus any Claude-added alternatives) with columns: `burst_id`, `regime` (Alpine / Scandinavian / Iberian / Temperate-flat / Fire), `best_match_sensing_utc`, `opera_rtc_granules_2024_2025` (count), `cached_safe` (path if present, empty otherwise), `lat`, `expected_max_relief_m`. Query uses `asf-search` (same pattern as `run_eval_disp.py`). The 5-burst final list is locked by plan-phase from this artifact; downstream the probe doc is referenced but not re-run at eval time.
- **D-02: Cached-SAFE reuse via harness search-path fallback.** New helper (tentative: `harness.find_cached_safe(granule_id, search_dirs: list[Path])`) or extension to `ensure_resume_safe` that checks `eval-rtc-eu/input/` first then falls back to `eval-disp-egms/input/`, `eval-dist-eu/input/`, `eval-dist-eu-nov15/input/`. No symlinks, no copies — the script reads SAFEs from wherever they live. Downstream DEM/orbit/OPERA-reference caches stay cell-local (not shared) since they're burst-specific, lightweight, and cleanly partitioned.
- **D-03: 5-burst fixed list covering all 5 BOOTSTRAP §1.1 regimes.** Alpine (>1000 m relief, likely Italian/Swiss Alps) + Scandinavian (>55°N, likely Sweden/Finland/Norway) + Iberian arid (Meseta north of Madrid, same general AOI family as Phase 3 CSLC candidate) + Po-plain Bologna (cached from DISP-EGMS) + Portuguese fire footprint (cached from DIST-EU). Mandatory constraints (RTC-01: ≥1 >1000 m AND ≥1 >55°N) satisfied by Alpine + Scandinavian. Other three distribute terrain diversity without extra download cost.
- **D-04: Claude drafts specific burst IDs + sensing dates in plan-phase; user reviews.** Context-phase does not pin specific burst IDs — those emerge from the probe artifact (D-01) querying ASF live. Plan-phase proposes concrete `t<relorb>_<burst>_iw<swath>` IDs with sensing UTC hours, user greenlights or adjusts before `run_eval_rtc_eu.py` is written.

### Script orchestration

- **D-05: Single `run_eval_rtc_eu.py` with declarative `BURSTS` list + for-loop.** Module-level `BURSTS: list[BurstConfig] = [BurstConfig(burst_id=..., sensing_time=..., regime=..., output_epsg=..., ...), ...]`. Mirrors the existing `run_eval_disp_egms.py` multi-AOI pattern; each iteration calls the same harness helpers (`bounds_for_burst`, `select_opera_frame_by_utc_hour`, `download_reference_with_retry`, `ensure_resume_safe`, `credential_preflight`) as `run_eval.py`. No argparse subcommand, no external Makefile per-burst target, no script-per-burst.
- **D-06: Per-burst try/except, accumulate + report.** Each burst iteration is wrapped in a try/except that captures the exception, records `BurstResult(burst_id=..., status='FAIL', error=repr(e), traceback=tb)`, and continues to the next burst. Final `metrics.json` contains all 5 rows regardless of mid-loop failures, so a broken Scandinavian burst doesn't block 4/5 signal in the matrix. Supervisor-level watchdog (Phase 1 D-12) is still the outer boundary.
- **D-07: Sequential execution across bursts.** No multiprocessing/threading across bursts — `opera-rtc`'s `run_parallel()` already saturates cores within a single burst. Adding burst-level parallelism doubles peak memory (each burst holds a ~4 GB SAFE + DEM), re-opens the fork-pitfall surface that Phase 1 `_mp.py` was designed to close, and gains nothing when the supervisor already wraps the cell. Phase 1 `_mp.configure_multiprocessing()` is called once at the top of `run_rtc()`; not re-called per burst.
- **D-08: Per-burst whole-pipeline skip + per-stage `ensure_resume_safe` within burst.** Before any work on a burst, check whether all expected outputs (`<cache>/opera_reference_<burst>/*.tif`, `<cache>/output/<burst>/*.cog.tif`, per-burst `metrics_burst.json`) pass the checker — if yes, skip the burst entirely (log "skipping: cached"). Otherwise enter the 5-stage pipeline (OPERA ref, DEM, orbit, SAFE, RTC) with an `ensure_resume_safe` guard at each stage, matching `run_eval.py`. Warm re-run of all 5 bursts finishes in seconds.

### Validation output layout (metrics.json + meta.json + matrix)

- **D-09: Single aggregate `eval-rtc-eu/metrics.json` with nested `per_burst: [...]`.** One file per cell per ARCHITECTURE §6 manifest (matrix writer reads only the manifest-declared path — never globs). Top-level contains the aggregate; `per_burst` is the drilldown list. Schema lives as a new Pydantic v2 model in `validation/matrix_schema.py` (extending Phase 1's base `CellMetrics` model). Violates neither ARCHITECTURE §6 (single metrics_file path) nor FEATURES per-burst drilldown requirement — nesting reconciles both.
- **D-10: Aggregate summary shape.** Top-level fields (Pydantic v2):
  - `pass_count: int` / `total: int` / `all_pass: bool` / `any_investigation_required: bool`
  - `product_quality: {count_pass, count_total}` — null for RTC (no product-quality gate in v1.1 for RTC; research says RTC is deterministic pass/fail against reference only — product-quality aggregation reserved for Phases 3/4 CSLC/DISP self-consistency)
  - `reference_agreement: {count_pass, count_total, worst_rmse_db: float, worst_r: float, worst_burst_id: str}`
  - `per_burst: list[BurstResult]` where each `BurstResult` carries: `burst_id`, `regime`, `lat`, `max_relief_m`, `cached`, `status`, `product_quality: ProductQualityResult | null`, `reference_agreement: ReferenceAgreementResult`, `investigation_required: bool`, `investigation_reason: str | null`, `error: str | null`.
- **D-11: Matrix row — single `X/N PASS` + link to CONCLUSIONS.** `results/matrix.md` shows one row for the RTC-EU cell in the canonical `Product | Region | Product-quality | Reference-agreement | Status | Notes` columns. Cell value format `5/5 PASS` (or `4/5 PASS, 1/5 FAIL`) with `Notes` column linking to `CONCLUSIONS_RTC_EU.md`. The per-burst table lives inside `CONCLUSIONS_RTC_EU.md`, not in the matrix. Matches FEATURES §Phase 1 "aggregated to a single matrix cell" guidance.
- **D-12: Single cell-level `eval-rtc-eu/meta.json` with nested per-burst hashes.** One provenance file per cell (not per-burst) with top-level `schema_version`, `git_sha`, `git_dirty`, `run_started_iso`, `run_duration_s`, `python_version`, `platform`, and a nested `per_burst_input_hashes: {burst_id: {safe_sha256, dem_sha256, orbit_sha256, opera_reference_sha256}}`. Keeps Phase 1 D-schema intact (one meta per cell) while surfacing per-burst input-hash drift when the reference product gets re-processed upstream.

### Investigation discipline (RTC-03)

- **D-13: Trigger is RMSE ≥ 0.15 dB (≈3× N.Am. baseline) OR r < 0.999.** N.Am. baseline is RMSE 0.045 dB / r 0.9999; 0.15 dB is "meaningfully different but still far below the 0.5 dB criterion" — the intended signal. Dual trigger: RMSE catches bias/amplitude drift, r catches structural disagreement (geometric shift, mis-registration). Both thresholds live in `criteria.py` as new entries NOT typed as gates: `rtc.eu.investigation_rmse_db_min = 0.15` and `rtc.eu.investigation_r_max = 0.999` — flagged with `type='INVESTIGATION_TRIGGER'` (new non-gate marker) so matrix-writer knows not to treat them as BINDING/CALIBRATING pass criteria.
- **D-14: Investigation form = structured sub-section per flagged burst in `CONCLUSIONS_RTC_EU.md`.** Section template per flagged burst: (1) **Observation** — RMSE, r, bias values side-by-side with N.Am. baseline; (2) **Top 2–3 hypotheses** — pick from a phase-maintained hypothesis list: "steep-relief DEM artefact", "high-latitude DEM grid anomaly", "OPERA reference version drift", "subsideo output format drift", "SAFE/orbit mismatch"; (3) **Evidence** — one concrete data point per hypothesis (DEM slope histogram, residual-vs-slope scatter, reference product_version field diff, granule sensing-UTC delta). No dedicated notebook per burst (that's Phase 6-scale); CONCLUSIONS prose + small inline tables or png references only.
- **D-15: Automated flagging in eval script.** `run_eval_rtc_eu.py` computes `investigation_required = (rmse_db >= 0.15) or (r < 0.999)` per burst and writes `investigation_required: bool` + `investigation_reason: str` ("RMSE 0.17 dB >= 0.15 dB") into the per-burst metrics. `matrix_writer` reads `any_investigation_required` from the aggregate and annotates the cell with ⚠ when true. Human writes the actual investigation text into CONCLUSIONS.md using the flagged burst list — automation flags, doesn't replace narrative.

### Claude's Discretion (for plan-phase)

- **Specific burst IDs and sensing dates** (D-04) — Claude drafts concrete IDs from the probe artifact; user reviews before code is written.
- **Terrain-regime coverage table auto-compute** — whether `max_relief_m` is computed at eval time from the DEM tile (preferred) or hand-filled in CONCLUSIONS_RTC_EU.md from known geography. Recommendation: compute at eval time from the cached DEM (read min/max elevation in the burst bbox), write into `per_burst[].max_relief_m`, include in CONCLUSIONS table.
- **BurstConfig dataclass shape** — whether to live in `run_eval_rtc_eu.py` (local to the script) or in a new shared `validation/eval_types.py` (shared across Phase 3+ eval scripts). Research didn't pre-commit; start local, promote if Phases 3/4/6 reuse the same shape.
- **OPERA reference discovery** — whether `download_reference_with_retry` or `select_opera_frame_by_utc_hour` is the right helper for "find the granule for this burst and this sensing date". Both exist; the latter is newer and handles ±1h offsets. Default to `select_opera_frame_by_utc_hour` per harness FEATURES §38.
- **Probe query implementation** — whether the probe artifact is written by a hand-run script (`scripts/probe_rtc_eu_candidates.py`) committed as a sub-deliverable, or a notebook, or a gsd-sdk query. Hand-run Python script is most consistent with v1.0 style (see `run_eval_disp.py` for ASF-query precedent); notebook adds Jupyter dep surface we don't need in Phase 2.
- **Multi-zone UTM handling** — each burst has its own output EPSG (UTM zone inferred from burst footprint per `opera_utils.burst_frame_db`). `BurstConfig.output_epsg` is per-burst; harness `bounds_for_burst` already gives WGS84 bbox, conversion happens in the RTC pipeline invocation.
- **Investigation hypothesis list** — maintained as a prose list in CONCLUSIONS_RTC_EU.md (not code). Whether to codify a small `INVESTIGATION_HYPOTHESES = [...]` tuple in `compare_rtc.py` or keep purely narrative — Claude's discretion at plan-phase; narrative is lighter-weight and sufficient at 5 bursts.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source-of-truth scope (read first)

- `.planning/ROADMAP.md` §Phase 2 — goal, success criteria, 3 requirements (RTC-01..03), RTC-02 explicit criteria-freeze, internal ordering.
- `.planning/REQUIREMENTS.md` §RTC-01, RTC-02, RTC-03 — full text of the 3 requirements.
- `.planning/PROJECT.md` — pass criteria (RTC RMSE < 0.5 dB, r > 0.99), two-layer install, CDSE-over-ASF convention, validation philosophy (reference-agreement is sanity check; product-quality is gate).
- `.planning/STATE.md` — v1.1 accumulated decisions; Phase 1 closure status.

### Phase 1 context (REQUIRED for understanding harness shape)

- `.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/01-CONTEXT.md` — D-01..D-19 decisions from Phase 1: `criteria.py` shape, split `ProductQualityResult`/`ReferenceAgreementResult` (D-06, D-08 at phase-1), `metrics.json` + `meta.json` schema (Claude's Discretion section), supervisor mechanics (D-10..D-14), harness per-source retry policy (Claude's Discretion).
- `.planning/phases/01-.../01-09-SUMMARY.md` — confirms Phase 1 reproducibility layer (Dockerfile + lockfiles) landed; Phase 2 inherits working env.

### Phase 2 research (authoritative for HOW)

- `.planning/research/FEATURES.md` §Phase 1 RTC EU (lines 46–53) — candidate-burst probe artifact rationale, `run_eval_rtc_eu.py` fork pattern, per-burst PASS/FAIL output, `CONCLUSIONS_RTC_EU.md` template convention.
- `.planning/research/PITFALLS.md` §P1.1 (lines 254–273) — cached-bias prevention mechanism (≥1 >1000 m relief AND ≥1 >55°N), terrain-regime coverage table schema `{burst_id, lat, max_relief_m, cached?}`, warning signs, structural/code/artifact prevention strategies.
- `.planning/research/ARCHITECTURE.md` §6 (matrix_manifest.yml + per-eval metrics.json sidecar pattern), §7 (cache dirs at repo root, gitignored), §1 (harness public API).
- `.planning/research/SUMMARY.md` §BOOTSTRAP corrections + §Phase 2 row (line 156–160) — 2-day effort estimate, low-risk framing, P1.1 watch-out.
- `.planning/research/STACK.md` — no Phase-2-specific stack additions; RTC pipeline reuses v1.0 deps (opera-rtc, isce3, rio-cogeo 6.0.0 via `_cog`).

### v1.0 precedent files to match (existing conventions)

- `run_eval.py` (114 LOC) — **the fork source** per FEATURES. Matches target structure exactly: `if __name__ == "__main__":` guard, harness imports, `credential_preflight(["EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"])`, OPERA ref via `earthaccess.search_data(...)`, ASF SAFE via `asf_search`, DEM via `subsideo.data.dem.fetch_dem`, orbit via `subsideo.data.orbits.fetch_orbit`, `run_rtc(...)` call. Phase 2 forks to `run_eval_rtc_eu.py` and generalises to a `BURSTS` list.
- `run_eval_disp_egms.py` — multi-AOI declarative-list pattern Phase 2 mirrors.
- `CONCLUSIONS_RTC_N_AM.md` — canonical RTC CONCLUSIONS template; Phase 2 mirrors structure + adds terrain-regime coverage table + per-burst investigation sub-sections where triggered.
- `src/subsideo/validation/compare_rtc.py` — **unchanged in Phase 2** per FEATURES. Returns `RTCValidationResult` with nested `product_quality` + `reference_agreement` (Phase 1 big-bang migration D-06..D-09 already landed).
- `src/subsideo/validation/harness.py` — the 5 helpers. Phase 2 is the **second** harness consumer (Phase 1 migrated `run_eval.py` as pilot); Phase 2 may surface a new helper like `find_cached_safe(granule_id, search_dirs)` if D-02 needs one.
- `src/subsideo/validation/matrix_schema.py` — Pydantic v2 base `CellMetrics` model. Phase 2 extends with `RTCEUCellMetrics` (pass_count, total, per_burst list).
- `src/subsideo/validation/matrix_writer.py` — reads manifest + metrics.json. Phase 2 adds RTC-EU cell row rendering (likely inline fmt, no new module).
- `src/subsideo/validation/supervisor.py` — Phase 1 subprocess wrapper. Phase 2's `run_eval_rtc_eu.py` must declare `EXPECTED_WALL_S` at module level (Phase 1 D-11 convention). Budget: ~5 bursts × 30 min/burst cold + 10 min reference fetches ≈ 3 hours safe margin; warm-run (all cached) ≈ 2 min.
- `src/subsideo/validation/criteria.py` — Phase 2 adds 2 non-gate entries: `rtc.eu.investigation_rmse_db_min = 0.15`, `rtc.eu.investigation_r_max = 0.999` with `type='INVESTIGATION_TRIGGER'`. Requires a new `Criterion` type enum variant (extends Phase 1 D-01 `Literal['BINDING', 'CALIBRATING']` to `Literal['BINDING', 'CALIBRATING', 'INVESTIGATION_TRIGGER']`).
- `src/subsideo/products/rtc.py` — unchanged in Phase 2.
- `Makefile` — already has `eval-rtc-eu: ; $(SUPERVISOR) run_eval_rtc_eu.py` target from Phase 1 D-12 (Makefile lines 28). Phase 2 creates the referenced script; no Makefile edits.
- `results/matrix_manifest.yml` — already lists the `rtc:eu` cell with `eval_script: run_eval_rtc_eu.py`, `cache_dir: eval-rtc-eu`, `conclusions_doc: CONCLUSIONS_RTC_EU.md`, `metrics_file: eval-rtc-eu/metrics.json` (Phase 1 D-08 committed). Phase 2 realises the referenced paths; no manifest edits.

### v1.0 CONCLUSIONS (context for why this is low-risk)

- `CONCLUSIONS_RTC_N_AM.md` §5 — the 0.045 dB / r 0.9999 baseline; §6 — why the result is correct (same algorithm core + same inputs → near-perfect agreement). Same result expected for EU bursts where OPERA ref + subsideo both use identical opera-rtc / GLO-30 DEM / POEORB orbit. Materially different RMSE implies a real region-specific effect worth investigating (D-13..D-15).

### External library refs (read as-needed during plan-phase)

- `opera_utils.burst_frame_db.get_burst_id_geojson()` — burst footprint WGS84 polygons; consumed by `harness.bounds_for_burst()`. Source of lat + UTM zone per burst for the coverage table.
- `asf_search.search(platform='SENTINEL-1A/B', processingLevel='SLC', ...)` — SAFE discovery for the probe and fallback.
- `earthaccess.search_data(short_name='OPERA_L2_RTC-S1_V1', temporal=..., granule_name=...)` — OPERA reference discovery. Harness `select_opera_frame_by_utc_hour` wraps this for ±1h offset tolerance.
- ESA Sentinel-1 burst map / `opera-utils` EU schema (built in v1.0) — authoritative EU burst IDs + footprints. No external URL; consumed via `opera_utils` API.

### No external ADR/spec docs for Phase 2

Phase 2 is codebase-internal validation work; no external spec consumed. All canonical refs above are internal planning docs, v1.0 CONCLUSIONS, or the library APIs already used in v1.0.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`run_eval.py` (114 LOC)** — the fork source; Phase 2's `run_eval_rtc_eu.py` generalises this to a `BURSTS: list[BurstConfig]` loop while keeping every harness call identical.
- **`src/subsideo/validation/compare_rtc.py` (94 LOC)** — already emits `RTCValidationResult(product_quality=None-for-now, reference_agreement=ReferenceAgreementResult(rmse=..., correlation=..., bias=..., ssim=...))`. Phase 2 consumes unchanged.
- **`src/subsideo/validation/harness.py`** — `bounds_for_burst`, `select_opera_frame_by_utc_hour`, `download_reference_with_retry`, `ensure_resume_safe`, `credential_preflight`. Phase 2 is the 2nd production consumer (after Phase 1 pilot); may add `find_cached_safe(granule_id, search_dirs)` if D-02 requires a helper.
- **`src/subsideo/validation/supervisor.py`** — subprocess wrap + mtime-staleness watchdog. Phase 2 script declares `EXPECTED_WALL_S` at module level per Phase 1 D-11 convention (budget ~3 h cold, ~2 min warm for 5 bursts).
- **`src/subsideo/validation/matrix_schema.py`** — Pydantic v2 base model. Phase 2 adds a `RTCEUCellMetrics` subtype for the aggregate+per_burst nested shape (D-09, D-10).
- **`src/subsideo/validation/matrix_writer.py`** — manifest-driven cell renderer. Phase 2 adds the cell-format logic for `X/N PASS` + investigation-⚠ annotation (D-11, D-15).
- **`src/subsideo/products/rtc.py`** — `run_rtc(safe_paths, orbit_path, dem_path, burst_ids, output_dir)` entry point. Unchanged in Phase 2; `_mp.configure_multiprocessing()` fires once per cell (Phase 1 D-14) not per burst.
- **`src/subsideo/data/dem.fetch_dem`, `data/orbits.fetch_orbit`** — cached download helpers. Consumed per-burst with `ensure_resume_safe` guards.
- **`CONCLUSIONS_RTC_N_AM.md`** — template; Phase 2 `CONCLUSIONS_RTC_EU.md` mirrors section structure (Objective, Test Setup, Bugs Encountered, Final Validation Results) + adds Terrain-Regime Coverage Table + per-burst Investigation Sub-Sections.

### Established Patterns

- **Lazy imports for conda-forge deps** — `products/rtc.py` imports isce3/opera-rtc inside function bodies. Phase 2 script imports `run_rtc` at module top (all harness+subsideo imports inside the `if __name__ == "__main__":` guard, per Phase 1 `_mp` preconditions).
- **`credential_preflight` first** — every harness-based eval script starts with `credential_preflight(required=[...])` before any network I/O. Phase 2 requires `['EARTHDATA_USERNAME', 'EARTHDATA_PASSWORD']` for OPERA reference fetch (ASF), plus optionally CDSE creds if any EU SAFE is not cached and needs CDSE S3 download. Declaring CDSE preflight upfront even for cache hits is defensible; Claude's discretion.
- **`if __name__ == "__main__":` guard** — non-negotiable per Phase 1 `_mp` bundle; every eval script has it.
- **Per-stage `ensure_resume_safe` gate** — explicit call per stage, not magic. Phase 2 D-08 adds an outer per-burst gate on top.
- **Resume-by-file-presence** — cached = file exists AND passes a lightweight checker (rasterio readable, non-zero size). `ensure_resume_safe(paths, checker_fn)` contract.
- **`EXPECTED_WALL_S` module-level** — supervisor AST-parses this constant; required on every eval script that runs under `make`.
- **`loguru` logging** — Phase 2 script uses `from loguru import logger`; no print() except for top-level banners.
- **Matrix manifest is authoritative** — Phase 2 never globs `CONCLUSIONS_*.md` or `eval-*/metrics.json`; all paths flow from `results/matrix_manifest.yml`.

### Integration Points

- **`Makefile: eval-rtc-eu`** — target already defined (line 28 of Makefile): `$(SUPERVISOR) run_eval_rtc_eu.py`. Phase 2 delivers the referenced script; Makefile unchanged.
- **`results/matrix_manifest.yml: rtc:eu`** — cell entry already present (Phase 1 D-08). Phase 2 fills the referenced `eval-rtc-eu/metrics.json` path at runtime.
- **`.gitignore: eval-*/`** — existing pattern; `eval-rtc-eu/` cache dir is auto-ignored.
- **`src/subsideo/validation/criteria.py`** — Phase 2 adds 2 non-gate `INVESTIGATION_TRIGGER` entries + extends the `Criterion.type` Literal (Phase 1 D-01).
- **`src/subsideo/validation/matrix_schema.py`** — Phase 2 adds `RTCEUCellMetrics` Pydantic model (extends `CellMetrics` base).
- **`src/subsideo/validation/matrix_writer.py`** — Phase 2 adds cell-render branch for the RTC-EU cell type (inline within existing render function; no new module).
- **New files**:
  - `run_eval_rtc_eu.py` at repo root.
  - `CONCLUSIONS_RTC_EU.md` at repo root (post-eval).
  - `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` (pre-eval probe artifact).
  - Optional: `scripts/probe_rtc_eu_candidates.py` that produces the probe artifact; committed as a sub-deliverable.
  - Optional: `src/subsideo/validation/eval_types.py` if `BurstConfig` is promoted from local-to-script to shared (Claude's discretion).

### Matrix / Script Flow (data shape)

```
run_eval_rtc_eu.py iterates BURSTS:
  for burst in BURSTS:
    try:
      credential_preflight([...])          # once, outside loop
      bounds = bounds_for_burst(burst.burst_id)
      opera_ref = select_opera_frame_by_utc_hour(...)
      safe = find_cached_safe(...) or download(...)  # D-02 fallback
      dem, orbit = fetch_dem(bounds, ...), fetch_orbit(...)
      result = run_rtc(safe, orbit, dem, [burst.burst_id], ...)
      compare = compare_rtc(result.output_paths[0], opera_ref_path)
      per_burst.append(BurstResult(
        burst_id=burst.burst_id,
        regime=burst.regime,
        lat=...,
        max_relief_m=compute_max_relief(dem),
        cached=safe_was_cached,
        status='PASS' if compare.reference_agreement.passed else 'FAIL',
        reference_agreement=compare.reference_agreement,
        investigation_required=(compare.rmse >= 0.15 or compare.r < 0.999),
        investigation_reason=...,
        error=None,
      ))
    except Exception as e:
      per_burst.append(BurstResult(burst_id=..., status='FAIL', error=repr(e), ...))

  write eval-rtc-eu/metrics.json  (RTCEUCellMetrics with per_burst list)
  write eval-rtc-eu/meta.json     (provenance + nested per_burst_input_hashes)
  # CONCLUSIONS_RTC_EU.md written separately (human / plan task)
```

</code_context>

<specifics>
## Specific Ideas

- **Probe artifact format** — `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` is a committed markdown table with the columns listed in D-01. Rationale: "no burst without ASF OPERA RTC coverage is a wasted compute run" (FEATURES line 50). Committing the probe result makes the burst choice auditable in git history — anyone can see why a regime was dropped (no coverage) or a fallback was swapped in.
- **Bologna + Portugal are the 'free 2 bursts'** — Phase 2 gets 5-burst coverage without ~8 GB of fresh download because Phase 1 (DISP-EGMS, DIST-EU) already cached those SAFEs. D-02 harness fallback is the mechanism.
- **Criterion immutability is Phase 2's hardest rule** — RTC-02 explicitly forbids tightening even if EU bursts cluster at 0.05 dB like N.Am. Phase 2 must NOT add a second `rtc.eu.rmse_db_max` entry with a tighter value. Investigation trigger (D-13) is a *separate, non-gate* concept.
- **Investigation trigger is the escape valve** — RTC-03 asks for documented investigation when EU differs "materially" from N.Am. Without D-13's concrete number, RTC-03 becomes a judgment-call trap. 0.15 dB / r 0.999 are calibrated from the N.Am. baseline (0.045 dB / 0.9999), give enough headroom to avoid flagging normal variance (terrain complexity bumps RMSE to 0.06–0.08 dB), and still catch real region-specific effects.
- **No product-quality gate for RTC in v1.1** — RTC has no self-consistency gate (that's CSLC/DISP per Phase 3/4). The `product_quality` field in the metrics.json aggregate is `null` for RTC cells; matrix writer renders as "n/a (reference-agreement product)" or similar. This is consistent with Phase 1 D-04 (RTC criteria are BINDING reference-agreement only; no CALIBRATING entries for RTC).
- **Single cell entry, single matrix row** — matrix design is 10 cells (5 products × 2 regions); Phase 2 RTC-EU is one cell with 5 bursts inside. Not 5 cells. This is the entire reason the metrics.json nesting decision (D-09) matters.

</specifics>

<deferred>
## Deferred Ideas

- **Per-burst Makefile targets** (`eval-rtc-eu-alpine`, etc.) — Phase 1 deferred this "until Phase 2 burst probing surfaces a concrete need". Phase 2 does not surface the need: single `eval-rtc-eu` target + per-burst try/except isolation (D-06) + harness watchdog are sufficient. Revisit in Phase 4+ if any phase legitimately needs to re-run a single burst from `make` without editing the script.
- **Parallel burst execution** — rejected in D-07; documented rationale (memory, fork-pitfall surface, no speedup win). Revisit only if cold-env `make eval-all` approaches the Phase 7 REL-04 12h budget and RTC-EU is the bottleneck.
- **Burst-DB-backed AOI catalogue** (FEATURES Differentiators §126) — "attractive but Phase-scope creep; better as v2". Phase 2 hand-picks via BOOTSTRAP candidates + probe, not catalogue query.
- **Shared `BurstConfig` in `validation/eval_types.py`** — start local-to-`run_eval_rtc_eu.py`; promote if Phase 3/4/6 eval scripts adopt the same pattern. No pre-commit.
- **Jupyter notebook per investigation-flagged burst** — D-14 rejects this; CONCLUSIONS prose + inline evidence is enough at the 3-regime scale. Revisit if a real investigation turns up a bug deep enough that a notebook is the natural artifact.
- **r > 0.999 as a new CALIBRATING gate** — NOT done. r 0.999 is the investigation *trigger*, not a new pass criterion. RTC-02 explicit: criteria do not tighten. Any promotion to gate requires GATE-05 (≥3 data points across ≥3 regions).
- **Cross-version OPERA reference drift detection** — if OPERA re-processes RTC products mid-v1.1, the cached-reference-hash in meta.json (D-12) surfaces drift on the next run. A dedicated re-fetch-on-hash-mismatch loop is deferred (v2).
- **Automatic regime classification from DEM** — whether regime (Alpine/Scandinavian/Iberian/…) auto-derives from `lat`+`max_relief_m` or is hand-labeled in `BurstConfig.regime`. Hand-labeled is cleaner at 5 bursts; revisit if the burst set grows.
- **CDSE alternative for OPERA reference** — if ASF Earthdata rate-limits or fails, CDSE doesn't host OPERA products. Fall back only to "skip this burst with FAIL + error='OPERA reference unavailable'"; do not construct a CDSE-based reference path.

### Reviewed Todos (not folded)

No pending todos matched Phase 2 (gsd-tools list-todos returned `count: 0`).

</deferred>

---

*Phase: 02-rtc-s1-eu-validation*
*Context gathered: 2026-04-22*
