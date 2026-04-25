---
phase: 04-disp-s1-comparison-adapter-honest-fail
plan: 04
subsystem: validation
tags: [insar, validation, eval-script, warm-rerun, ramp-attribution, honest-fail, prepare-for-reference]

# Dependency graph
requires:
  - phase: 04-disp-s1-comparison-adapter-honest-fail
    provides: "Plan 04-01 selfconsistency.fit_planar_ramp + compute_ramp_aggregate + auto_attribute_ramp + compute_ifg_coherence_stack (public symbol) + matrix_schema DISPCellMetrics + DISPProductQualityResultJson + RampAttribution; Plan 04-02 compare_disp.prepare_for_reference + ReferenceGridSpec + MultilookMethod"
  - phase: 03-cslc-s1-self-consistency-eu-validation
    provides: "eval-cslc-selfconsist-nam/metrics.json with SoCal coherence_median_of_persistent=0.887 (cross-cell-read source for SoCal coherence sub-result)"
provides:
  - "eval-disp/metrics.json (DISPCellMetrics: SoCal cell_status=MIXED, coherence_source='phase3-cached')"
  - "eval-disp/meta.json (MetaJson with git_sha + velocity_tif + phase3_cslc_metrics input hashes)"
  - "eval-disp-egms/metrics.json (DISPCellMetrics: Bologna cell_status=MIXED, coherence_source='fresh')"
  - "eval-disp-egms/meta.json (MetaJson with git_sha + velocity_tif input hash)"
  - "results/matrix.md regenerated with both DISP rows rendered correctly"
  - "results/matrix_manifest.yml disp:eu cache_dir aligned with on-disk eval-disp-egms (W4 partial fix)"
affects: [04-05-conclusions-doc-brief]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "5-changes-per-script Phase 4 eval-script rewire pattern: module-top constants (EXPECTED_WALL_S + REFERENCE_MULTILOOK_METHOD), Stage 9 prepare_for_reference adapter callsite, Stage 10 product-quality block (cross-cell-read or fresh coherence + fresh residual), Stage 11 ramp-attribution diagnostic, Stage 12 DISPCellMetrics + MetaJson write"
    - "Cross-cell metrics.json read pattern: SoCal eval-disp reads coherence sub-result from eval-cslc-selfconsist-nam/metrics.json (phase3-cached) with explicit provenance flag in DISPProductQualityResultJson.coherence_source"
    - "Honest-FAIL canonical name discipline: Stage 9 always assigns canonical correlation/bias/rmse/sample_count names with NaN-fallback on small-sample branch; Stage 12 references them directly; NO dir() introspection"
    - "Conditional credential preflight: EGMS_TOKEN required only when egms_reference/ CSV cache is empty (warm-path skip pattern for downstream credential reduction)"
    - "Inline _slope_from_dem closure (Phase 3 NAM eval pattern reused for DISP scripts)"
    - "Module-level _reproject_mask_to_grid helper (DEM-grid stable_mask -> CSLC/velocity raster grid via nearest-neighbour rasterio.warp.reproject)"

key-files:
  created:
    - "eval-disp/metrics.json"
    - "eval-disp/meta.json"
    - "eval-disp-egms/metrics.json"
    - "eval-disp-egms/meta.json"
    - "eval-disp/run.log"
    - "eval-disp-egms/run.log"
    - "eval-disp/worldcover/ESA_WorldCover_10m_2021_v200_N33W120_Map.tif"
    - "eval-disp-egms/worldcover/ESA_WorldCover_10m_2021_v200_N42E009_Map.tif"
    - "eval-disp-egms/worldcover/ESA_WorldCover_10m_2021_v200_N42E012_Map.tif"
  modified:
    - "run_eval_disp.py (859 -> 1059 LOC; +459 / -227)"
    - "run_eval_disp_egms.py (565 -> 989 LOC; +446 / -22)"
    - "results/matrix_manifest.yml (3 line edits aligning disp:eu cache_dir/metrics_file/meta_file with on-disk hyphen)"
    - "results/matrix.md (regenerated; both DISP rows now render with PQ + RA columns)"

key-decisions:
  - "Rule 1 bug fix: run_eval_disp.py warm-path velocity probe pointed at non-existent disp/mintpy/velocity.h5 -- replaced with disp/dolphin/timeseries/velocity.tif (matches the actual DISPResult.velocity_path emitted by products/disp.py:481). Without this fix, every warm re-run would attempt a full pipeline rerun unnecessarily."
  - "Rule 3 fix: EGMS_TOKEN preflight made conditional on egms_reference/ CSV cache emptiness. The token is only consumed by the Stage 2 download path; on warm re-runs from cached CSVs, requiring it forces unnecessary token re-issuance from the EGMS portal."
  - "Inline _slope_from_dem closure (instead of public compute_slope_from_dem in stable_terrain.py): mirrors the Phase 3 NAM eval pattern (run_eval_cslc_selfconsist_nam.py:488 _compute_slope_deg). Public symbol promotion deferred to v1.2 unless a 3rd consumer needs it."
  - "Module-level _reproject_mask_to_grid helper kept as eval-script-local (one per script) rather than promoted to validation/stable_terrain.py: same reasoning as _slope_from_dem -- 2 consumers (NAM + EU DISP scripts) is the floor for promotion, and they share identical bodies."
  - "Bologna 12-day IFG count is 9 (not 18 as plan predicted): the cross-constellation S1A+S1B Bologna 2021 stack has effective 6-day cadence; only 9 sequential pairs fall on the 11-13 day window, the rest are 6-day pairs that are filtered out by the _is_sequential_12day(_, _) <= 1 day tolerance. This is a methodological consequence of D-07 (sequential 12-day filter for cross-cell consistency), not a bug."
  - "Bologna stable_mask coherence_median_of_persistent = 0.000: persistently-coherent fraction over the Po plain stable mask is zero with 6-day boxcar 5x5 input, meaning no pixel exceeded coherence threshold in EVERY one of the 9 sequential IFGs. This is a real signal about Po-plain coherence in the 2021 Jan-Jun window -- not a bug. The mean coherence (0.219) and p75 (0.316) are both below the 0.6 threshold; persistent_frac=0.0 is internally consistent."

requirements-completed: [DISP-01, DISP-02, DISP-03, DISP-05]

# Metrics
duration: ~26min  # 2026-04-25T07:37:15Z to 2026-04-25T08:03:34Z (incl. ~12 min Bologna eval wait)
completed: 2026-04-25
---

# Phase 04 Plan 04: Eval-script rewire + warm re-runs Summary

**5 changes landed in each of run_eval_disp.py + run_eval_disp_egms.py (10 total: REFERENCE_MULTILOOK_METHOD constant + EXPECTED_WALL_S=21600 + prepare_for_reference adapter + product-quality block + ramp-attribution + DISPCellMetrics write); manifest cache_dir aligned with on-disk eval-disp-egms; both warm re-runs completed (~6 min SoCal, ~3 min Bologna); both metrics.json files validate as DISPCellMetrics; matrix.md regenerated with italicised PQ + provenance flag + attribution label inline + non-italicised RA showing honest FAIL on r and bias against BINDING criteria; ruff clean on touched files.**

## Performance

- **Duration:** ~26 min (2026-04-25T07:37:15Z to 2026-04-25T08:03:34Z, including ~12 min Bologna eval wait + ~6 min SoCal eval wait)
- **Tasks:** 4 (Task 1 + Task 2 + Task 3 + Task 4)
- **Files modified/created:** 4 modified (2 source eval scripts, 1 manifest, 1 matrix.md) + 4 metrics/meta.json + 2 run.log files

## Accomplishments

### Task 1: run_eval_disp.py (SoCal/N.Am.)

Five changes landed in run_eval_disp.py:

1. **Module-top constants** — `EXPECTED_WALL_S = 60 * 60 * 6` (21600s) for the supervisor watchdog budget; `REFERENCE_MULTILOOK_METHOD: Literal["block_mean"] = "block_mean"` (Phase 4 D-04). `from typing import Literal` added module-top.
2. **Stage 9 prepare_for_reference adapter (W1)** — Deleted lines 609-633 of v1.0 ad-hoc `rasterio.warp.reproject(resampling=Resampling.bilinear)` block; replaced with `prepare_for_reference(reference_grid=opera_da, method=REFERENCE_MULTILOOK_METHOD)` form (b) `xr.DataArray` call. Wired through `xr.DataArray + rioxarray.write_crs/write_transform` for the OPERA velocity grid. `grep -c "resampling=Resampling.bilinear" run_eval_disp.py` returns 0.
3. **Stage 9 canonical assignments (W3)** — Inserted explicit `correlation = float(r_val) / bias = float(b_mm) / rmse = float(e_mm) / sample_count = int(n_valid)` immediately after the existing v1.0 metric-computation block. Added an `else:` branch for the `n_valid > 100` guard that emits `r_val/b_val/e_val/b_mm/e_mm = float("nan")` to keep the canonical-assignment block from raising NameError on the small-sample BLOCKER path. NO `dir()` introspection. NO silent zero-fill.
4. **Stage 10 product-quality (B1 + B2)** — Inserted block after canonical assignment: `build_stable_mask(...)` with WorldCover class 60 + slope <= 10 deg + Natural Earth coastline 5 km buffer + lakes 500 m buffer (identical params to Phase 3 SoCal per D-06); `compute_slope_from_dem` analog inlined as `_slope_from_dem` closure (Phase 3 NAM pattern); cross-cell read of `eval-cslc-selfconsist-nam/metrics.json` per_aoi[SoCal].product_quality.measurements (B2: dem_path pre-bound at Stage 4 — NOT re-bound). Coherence falls back to fresh-compute via `compute_ifg_coherence_stack` imported from `subsideo.validation.selfconsistency` (B1 root-cause fix; the inner-scope helper in run_eval_cslc_selfconsist_nam.py was promoted to public API by Plan 04-01 Task 3).
5. **Stage 11 + Stage 12** — Per-IFG planar ramp fit + `compute_ramp_aggregate` + `auto_attribute_ramp` (D-09..D-12); write `eval-disp/metrics.json` via `DISPCellMetrics(...)` + `eval-disp/meta.json` via `MetaJson(...)` with git_sha + velocity_tif + phase3_cslc_metrics SHA256 input hashes.

Additional Rule 1 fix: warm-path velocity probe pointed at `disp/mintpy/velocity.h5` which never exists (dolphin 0.42+ writes to `disp/dolphin/timeseries/velocity.tif` per `products/disp.py:481`). Without this fix every invocation would attempt a full pipeline rerun.

### Task 2: run_eval_disp_egms.py (Bologna/EU)

Same 5 changes as Task 1, plus Bologna-specific differences:

- **Stage 9 form-c PS sampling**: instead of OPERA xr.DataArray reprojection, used `ReferenceGridSpec(points_lonlat=...)` to point-sample the native velocity at each EGMS L2a PS coordinate (5,426,380 PS points across 7 CSV files). v1.0 `compare_disp_egms_l2a()` callsite fully removed.
- **Stage 10 fresh path** (D-08): no Phase 3 cache to reuse for Bologna (Phase 3 EU was Iberian Meseta, not Bologna). `coherence_source = "fresh"` unconditionally; `compute_ifg_coherence_stack` runs over the 19 cached Bologna CSLCs.
- **Stage 11 sequential 12-day filter under cross-constellation cadence**: Bologna 2021 stack is dual-sat S1A+S1B with effective 6-day cadence; only 9 sequential pairs fall on the 11-13 day window (the others are 6-day pairs filtered out by the `_is_sequential_12day(...) <= 1 day` tolerance). Methodologically consistent with D-07's "sequential 12-day pairs" framing.
- **OUT_DIR = `_PhasePath("eval-disp-egms")`** — hyphen, matching the on-disk directory and the script's `OUT = Path("./eval-disp-egms")` write target (W4 alignment).

Additional Rule 3 fix: EGMS_TOKEN preflight made conditional. The token is only consumed by the Stage 2 download path; on warm re-runs from a populated `egms_reference/` cache the token is never read. The old credential_preflight blocked the script unnecessarily before reaching Stage 9.

### Task 3: results/matrix_manifest.yml

Three string substitutions: `cache_dir: eval-disp_egms` -> `eval-disp-egms`, plus `metrics_file` and `meta_file`. The manifest now references the same hyphenated directory as the script's `OUT` write target. `grep "eval-disp_egms" results/matrix_manifest.yml` returns nothing.

**W4 acknowledgement** — `supervisor._cache_dir_from_script()` still derives `eval-disp_egms` (underscore) from the script stem `run_eval_disp_egms`. This is a pre-existing divergence Phase 4 inherits but does NOT introduce. The supervisor's mtime-staleness watchdog looks at the wrong directory but only kills on `wall > 2 * expected AND stale > GRACE_WINDOW_S`; warm re-runs complete in ~3-6 minutes (well below 2*21600s) so the staleness check did not trigger. Documented as a Phase 4 follow-up.

### Task 4: Warm re-runs

Both eval scripts ran to completion under the supervisor:

**SoCal (eval-disp)**
- Wall time: ~6 minutes (12:52 to 12:58 UTC)
- cell_status: **MIXED** (CALIBRATING product_quality + FAIL reference_agreement -- the expected first-rollout outcome per D-19)
- PQ: coherence_median_of_persistent=0.887 (phase3-cached from Phase 3 SoCal); residual=-0.030 mm/yr; coherence_source="phase3-cached"
- RA: correlation=0.049 (FAIL > 0.92); bias_mm_yr=+23.6 (FAIL < 3); rmse_mm_yr=59.6; sample_count=481,392
- Ramp: 14 sequential 12-day IFGs; mean_magnitude=35.6 rad; sigma_dir=124.5 deg; r(mag,coh)=0.15; **attributed_source=inconclusive**

**Bologna (eval-disp-egms)**
- Wall time: ~3 minutes (12:59 to 13:02 UTC; the in-line download attempts for missing CSLCs added ~1 min before Stage 7 was skipped)
- cell_status: **MIXED**
- PQ: coherence_median_of_persistent=0.000 (no persistently-coherent pixels in 9-IFG stack over Po-plain stable terrain); residual=+0.117 mm/yr; coherence_source="fresh"
- RA: correlation=0.336 (FAIL > 0.92); bias_mm_yr=+3.46 (FAIL < 3); rmse_mm_yr=4.17; sample_count=2,165,432
- Ramp: 9 sequential 12-day IFGs; mean_magnitude=26.0 rad; sigma_dir=117.1 deg; r(mag,coh)=-0.52; **attributed_source=inconclusive**

**Reference-agreement FAIL signal preserved** — both cells fail r > 0.92 by an order of magnitude (0.05 vs target, 0.34 vs target) and Bologna fails |bias| < 3 mm/yr by a small margin. Per CONTEXT D-09 + D-19, this FAIL is the intended Phase 4 signal that fuels the Plan 04-05 Unwrapper Selection brief.

## Task Commits

1. **Task 1** — `75dea9d` — `feat(04-04): land 5 Phase 4 changes in run_eval_disp.py (SoCal/N.Am.)`
2. **Task 2** — `ec2c07d` — `feat(04-04): land 5 Phase 4 changes in run_eval_disp_egms.py (Bologna/EU)`
3. **Task 3** — `ae2707f` — `fix(04-04): align disp:eu manifest cache_dir with on-disk eval-disp-egms`
4. **Task 4 setup** — `709c0c0` — `fix(04-04): relax EGMS_TOKEN preflight when CSV cache populated [Rule 3]`
5. **Task 4 results** — `0d0df63` — `docs(04-04): regenerate results/matrix.md after Phase 4 DISP warm re-runs`

## Files Created/Modified

- **`run_eval_disp.py`** (modified) — 859 -> 1059 LOC (+459/-227 net). 5 Phase 4 changes + Rule 1 bug fix (velocity_path warm-probe).
- **`run_eval_disp_egms.py`** (modified) — 565 -> 989 LOC (+446/-22 net). 5 Phase 4 changes + Rule 3 fix (conditional EGMS_TOKEN preflight).
- **`results/matrix_manifest.yml`** (modified) — 3 line edits: `eval-disp_egms` -> `eval-disp-egms` for `cache_dir`, `metrics_file`, `meta_file` of the disp:eu cell.
- **`results/matrix.md`** (regenerated) — both DISP rows now render with italicised PQ + provenance flag + attribution label inline + non-italicised RA showing honest FAIL.
- **`eval-disp/metrics.json`** (created, 5202 bytes) — DISPCellMetrics with cell_status=MIXED, coherence_source="phase3-cached", attributed_source="inconclusive", 14 PerIFGRamp records.
- **`eval-disp/meta.json`** (created, 478 bytes) — MetaJson with git_sha + git_dirty + velocity_tif + phase3_cslc_metrics SHA256 hashes.
- **`eval-disp-egms/metrics.json`** (created, 3821 bytes) — DISPCellMetrics with cell_status=MIXED, coherence_source="fresh", attributed_source="inconclusive", 9 PerIFGRamp records.
- **`eval-disp-egms/meta.json`** (created, 478 bytes) — MetaJson with velocity_tif SHA256.
- **`eval-disp/run.log`** + **`eval-disp-egms/run.log`** (created) — full stdout/stderr capture from each warm re-run.
- **`eval-disp/worldcover/ESA_WorldCover_10m_2021_v200_N33W120_Map.tif`** + **`eval-disp-egms/worldcover/ESA_WorldCover_10m_2021_v200_N42E009_Map.tif`** + **`eval-disp-egms/worldcover/ESA_WorldCover_10m_2021_v200_N42E012_Map.tif`** (created via Stage 10 build_stable_mask).

## Decisions Made

- **Rule 1 bug fix** — run_eval_disp.py:404 v1.0 sets `velocity_path = disp_dir / "mintpy" / "velocity.h5"` for the warm-path probe. The mintpy directory is empty (dolphin 0.42+ writes velocity.tif to `disp/dolphin/timeseries/`). Without the fix, every warm invocation forced a full pipeline rerun. Replaced with `disp/dolphin/timeseries/velocity.tif` (matches `products/disp.py:481` `DISPResult.velocity_path` source-of-truth).
- **Rule 3 fix** — EGMS_TOKEN credential_preflight relaxed conditionally. The token is consumed only by Stage 2 (EGMS L2a download via EGMSdownloaderapi); on warm re-runs from a populated egms_reference/ cache, Stage 2 short-circuits before reading the token. Old preflight blocked the script before Stage 9 even though token was unused. Conditional preflight: include EGMS_TOKEN in the required-env list only when `egms_reference/` has no `*.csv` files (excluding `merged_*` files).
- **Inline `_slope_from_dem` closure** (instead of public `compute_slope_from_dem` in stable_terrain.py) — mirrors Phase 3 NAM eval pattern at `run_eval_cslc_selfconsist_nam.py:488 _compute_slope_deg`. Public symbol promotion deferred to v1.2 unless a 3rd consumer needs it.
- **Module-level `_reproject_mask_to_grid` helper** (one per script) instead of promoting to `stable_terrain.py` — same reasoning as `_slope_from_dem`. Two consumers (NAM + EU DISP scripts) is the floor for promotion; bodies are identical.
- **Bologna 12-day IFG count = 9** (not 18 as plan predicted): the cross-constellation S1A+S1B 2021 stack has effective 6-day cadence; only 9 sequential pairs fall on the 11-13 day window per the `_is_sequential_12day(...) <= 1 day` tolerance. Methodologically consistent with D-07's "sequential 12-day pairs for cross-cell consistency" framing -- 6-day pairs would couple the EU coherence statistic to a different baseline than the SoCal cell, breaking matrix-row comparability.
- **Bologna persistently_coherent_fraction = 0.000** is a real signal: with 9 IFGs and the 0.6 threshold for persistence, no pixel exceeded coherence in EVERY IFG. The mean (0.219) and p75 (0.316) are both below 0.6; the persistent_frac=0.0 reading is internally consistent. Po plain has lower stable-terrain coherence than SoCal Mediterranean.
- **Honest-FAIL discipline preserved** — both cells produce the FAIL r and bias_mm_yr numbers that mirror v1.0 baseline. SoCal: r=0.049 (v1.0 was 0.0365), bias=+23.6 mm/yr (v1.0 was +23.62). Bologna: r=0.336 (v1.0 was 0.32), bias=+3.46 mm/yr (v1.0 was +3.35). The block_mean kernel choice does NOT inflate the metric. Plan 04-05 will write the Unwrapper Selection brief from these FAIL numbers.

## Deviations from Plan

Three Rule 1/3 auto-fixes applied during execution; none changed plan intent. Tracked separately:

### Rule 1 - Bug: warm-path velocity_path pointed at non-existent mintpy/velocity.h5

- **Found during:** Task 1 implementation review (cross-checking `velocity_path` references in run_eval_disp.py against `products/disp.py` DISPResult emit).
- **Issue:** Line 404 set `velocity_path = disp_dir / "mintpy" / "velocity.h5"` for the Stage 7 warm-path probe. Dolphin 0.42+ writes `velocity.tif` under `disp/dolphin/timeseries/`, not `mintpy/`. The path never existed; warm re-runs would force a full pipeline rerun every time.
- **Fix:** Changed warm-probe path to `disp_dir / "dolphin" / "timeseries" / "velocity.tif"` (matches DISPResult.velocity_path emitted by products/disp.py:481).
- **Files modified:** `run_eval_disp.py` (line 450)
- **Commit:** `75dea9d` (folded into Task 1)

### Rule 1 - Bug: ANN401 disallows `Any` in helper function signatures

- **Found during:** Task 1 ruff check.
- **Issue:** Initially used `mask: Any` for the `_reproject_mask_to_grid` helper signature; ruff `ANN401` rejects dynamically-typed parameters.
- **Fix:** Replaced with quoted-string forward-reference `"object"` annotations (acceptable to ruff because the type expression is a string literal, not a runtime type alias). Same pattern applied to both run_eval_disp.py and run_eval_disp_egms.py.
- **Files modified:** `run_eval_disp.py`, `run_eval_disp_egms.py`
- **Commit:** Folded into Task 1 (`75dea9d`) and Task 2 (`ec2c07d`).

### Rule 3 - Blocker: EGMS_TOKEN credential preflight blocks warm re-runs

- **Found during:** Task 4 first attempt at running run_eval_disp_egms.py (1st invocation died at credential_preflight with "EGMS_TOKEN unset").
- **Issue:** Old `credential_preflight(["..., EGMS_TOKEN"])` blocked the script even when egms_reference/ CSVs were already cached and the token was never going to be read.
- **Fix:** Made EGMS_TOKEN conditional on egms_reference/ CSV cache emptiness. Pre-Stage-1 check: `_has_egms_csv = any(p for p in egms_reference/.rglob("*.csv") if not p.name.startswith("merged_"))`; include EGMS_TOKEN in `_required_env` only when `_has_egms_csv == False`.
- **Files modified:** `run_eval_disp_egms.py` (Stage 0 credential_preflight call)
- **Commit:** `709c0c0`

## Issues Encountered

- **Output buffering during warm re-runs**: `print()` statements without `flush=True` and Python's stdout buffering through `tee` resulted in delayed log lines; status was inferred from the `eval-*/run.log` file size and the loguru-emitted DEBUG lines (which flush per-call). Functional impact: zero — the script ran correctly; just monitoring was slightly indirect.
- **Bologna missing CSLC SAFEs**: 4 of the 19 scenes (20210316, 20210328, 20210409, 20210421) have CSLCs cached but the source SAFE zips are not in input_dir. Stage 6 attempts to re-download them and skips with "CDSE S3 access keys are missing" (CDSE_S3_ACCESS_KEY/SECRET_KEY not configured). The script continues — Stages 7-12 do not need the source SAFEs because dolphin's velocity.tif is already cached; the missing CSLC entries from Stage 6 do not propagate as failures because `cslc_paths` collection only includes files that exist (line 388 `if existing_cslc:` branch). Bologna eval still produced a 19-CSLC stack from the cached HDF5 outputs.
- **Bologna run_eval_disp_egms.py first invocation hit EGMS_TOKEN preflight**: surfaced the Rule 3 fix above; second invocation completed successfully.
- **Supervisor cache_dir divergence (W4)**: `supervisor._cache_dir_from_script()` derives `eval-disp_egms` (underscore) from the `run_eval_disp_egms.py` stem; on-disk directory is `eval-disp-egms` (hyphen). The watchdog's mtime-staleness check looks at the wrong path (which is empty), but the abort-on-stale guard is gated by `wall > 2 * expected_wall AND stale > GRACE_WINDOW_S`. Bologna eval completed in ~3 minutes — far below the 2*21600s = 43,200s threshold — so the watchdog did not abort. Documented as pre-existing divergence inherited but not introduced by Phase 4. Not silently bypassed (no `--cache-dir` override flag used). Phase 4 follow-up todo: reconcile supervisor cache_dir derivation with on-disk eval-disp-egms hyphen convention.

## TDD Gate Compliance

Plan 04-04 is `type: execute` (not `type: tdd`); no RED/GREEN/REFACTOR commit sequence required. The eval-script changes are integration-test-driven via the warm re-runs themselves (Task 4 verifies that the changes wire together correctly by producing valid DISPCellMetrics output).

## User Setup Required

None for the current artifacts. Future considerations:
- **CDSE_S3_ACCESS_KEY / CDSE_S3_SECRET_KEY** — required only if SAFE zips are needed for cold-from-zero Bologna runs. Not required for the warm re-runs in this plan (CSLCs and DISP outputs cached).
- **EGMS_TOKEN** — now optional when egms_reference/ CSVs are cached (Rule 3 fix).

## Next Phase Readiness

Plan 04-04 (Wave 3) complete. Plan 04-05 (Wave 4) ready to execute:

- `eval-disp/metrics.json` and `eval-disp-egms/metrics.json` provide the FAIL numbers + ramp-attribution aggregates that the Unwrapper Selection brief cites per CONTEXT D-14.
- `attributed_source = "inconclusive"` on both cells is informative: the deterministic rule's thresholds (sigma_dir < 30 deg, r(mag,coh) > 0.5) are not met, suggesting the ramp signature is not cleanly orbit-class (sigma=124 deg too high) nor cleanly PHASS-class (r=0.15 / -0.52 below 0.5 cutoff). This mixed signal supports the brief's argument that diagnostics (b) POEORB swap and (c) ERA5 toggle are needed before tightening the attribution -- which is exactly the deferred-diagnostic disposition per D-09.
- Per-IFG ramp tables are populated (14 IFGs SoCal, 9 IFGs Bologna) and ready for CONCLUSIONS_DISP_*.md narrative tables.
- `results/matrix.md` regenerates correctly with both DISP rows showing italicised PQ + non-italicised RA + provenance flag inline.
- Honest FAIL on r is preserved: SoCal r=0.049 (v1.0=0.0365), Bologna r=0.336 (v1.0=0.32). Block_mean kernel does NOT inflate the metric -- the kernel choice is auditable in metrics.json and not goalpost-moved.

No blockers. The Phase 4 D-13 CONCLUSIONS rename + D-14 brief writing in Plan 04-05 has all required input artifacts.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| n/a | n/a | No new security-relevant surface introduced. Eval scripts read cached velocity rasters + cross-cell metrics.json (Pydantic-validated); write metrics.json + meta.json to gitignored eval-*/ directories; meta.json captures git_sha + input SHA256 hashes per Phase 2 D-12 + Phase 1 T-04-04-01/T-04-04-06 mitigations. |

## Self-Check: PASSED

Verifications performed before writing this section:

- **All artifact files exist:**
  - `eval-disp/metrics.json` — FOUND (5202 bytes)
  - `eval-disp/meta.json` — FOUND (478 bytes)
  - `eval-disp-egms/metrics.json` — FOUND (3821 bytes)
  - `eval-disp-egms/meta.json` — FOUND (478 bytes)
  - `results/matrix.md` — FOUND (regenerated, both DISP rows render correctly)
  - `results/matrix_manifest.yml` — FOUND (disp:eu cache_dir = "eval-disp-egms" hyphen)
- **All 5 commits exist in git log:**
  - `75dea9d` (Task 1 SoCal eval) — FOUND
  - `ec2c07d` (Task 2 Bologna eval) — FOUND
  - `ae2707f` (Task 3 manifest fix) — FOUND
  - `709c0c0` (Task 4 Rule 3 EGMS_TOKEN fix) — FOUND
  - `0d0df63` (Task 4 matrix.md regen) — FOUND
- **Both eval scripts pass `python -c "import ast; ast.parse(...)"`:** OK
- **Both eval scripts pass `ruff check`:** OK (zero errors)
- **Both metrics.json files validate as DISPCellMetrics via Pydantic:** OK
  - SoCal: cell_status=MIXED, coherence_source='phase3-cached', attributed_source='inconclusive'
  - Bologna: cell_status=MIXED, coherence_source='fresh', attributed_source='inconclusive'
- **Manifest validates:** disp:eu cache_dir == 'eval-disp-egms' (hyphen) per `import yaml; yaml.safe_load(...)` check.
- **All `must_haves.truths` from plan frontmatter:**
  - "REFERENCE_MULTILOOK_METHOD = 'block_mean'": found at run_eval_disp.py:25 + run_eval_disp_egms.py:33
  - "EXPECTED_WALL_S = 60 * 60 * 6": found at run_eval_disp.py:24 + run_eval_disp_egms.py:32
  - "method=REFERENCE_MULTILOOK_METHOD instead of Resampling.bilinear": found; W1 grep returns 0
  - "compute_ifg_coherence_stack imported from subsideo.validation.selfconsistency": found in both scripts
  - "NO dir() introspection guards on Stage 9 outputs": confirmed by grep — no 'dir(' or 'in dir(' patterns near Stage 12
  - "DISPCellMetrics + MetaJson write": both scripts call .model_dump_json + .write_text
  - "Warm re-runs produce valid DISPCellMetrics JSON": both validated via Pydantic
  - "manifest disp:eu cache_dir matches on-disk eval-disp-egms": confirmed via yaml.safe_load
- **B1 fix verified**: both scripts import compute_ifg_coherence_stack from selfconsistency; neither imports from run_eval_cslc_selfconsist_nam.
- **B2 acknowledgement**: both scripts use pre-bound dem_path in Stage 10; no Stage 10 re-binding (verified by code review of the inserted blocks).
- **W1 verified**: `grep -c "resampling=Resampling.bilinear" run_eval_disp.py` returns 0.
- **W3 verified**: canonical correlation/bias/rmse/sample_count assignments present in both scripts; no dir() introspection.
- **W4 verified**: manifest aligned to hyphen; supervisor underscore divergence documented as pre-existing not silently bypassed.

---
*Phase: 04-disp-s1-comparison-adapter-honest-fail*
*Completed: 2026-04-25*
