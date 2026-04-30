---
phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
verified: 2026-04-22T17:55:00Z
status: passed
score: 17/17 must-haves verified
overrides_applied: 0
quality_debt:
  - id: CR-01
    file: src/subsideo/validation/compare_disp.py
    line: 319
    issue: "src.nodata accessed after rasterio context manager exits — will raise RasterioIOError on EGMS L2a comparison"
    severity: critical
    owner: "/gsd-code-review-fix before Phase 4 execution"
  - id: CR-02
    file: src/subsideo/validation/harness.py
    line: 515
    issue: "resp.raise_for_status() raises HTTPError (RequestException subclass) silently swallowed by retry fallback, violating RETRY_POLICY contract for unknown 5xx statuses"
    severity: critical
    owner: "/gsd-code-review-fix before Phase 3/4 execution"
  - count: 10_warnings + 5_info
    source: 01-REVIEW.md
    owner: "Phase 7 pre-release audit or /gsd-code-review-fix"
deferred:
  - truth: "6 pre-existing unit test failures (test_compare_dswx x2, test_disp_pipeline x2, test_metadata_wiring x1, test_orbits x1)"
    addressed_in: "Phase 4 DISP / Phase 6 DSWx"
    evidence: "deferred-items.md documents pre-existence; attributions cite file-owning phases"
---

# Phase 01: Environment Hygiene, Framework Consolidation & Guardrail Scaffolding Verification Report

**Phase Goal:** Land the foundational environment manifest, shared validation substrate, immutable criteria registry, composite ValidationResult, harness + batch-migration, watchdog orchestration, matrix writer, and reproducibility (lockfiles + Dockerfile + Apptainer). Phase is the foundation every other v1.1 phase depends on.

**Verified:** 2026-04-22T17:55:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Must-Haves)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `conda-env.yml` exists, solves on osx-arm64 (dry-run log at 01-01-dryrun.txt) | VERIFIED | File exists (88 lines); 01-01-dryrun.txt present in phase dir; Plan 01-01 SUMMARY documents the dryrun probe. Errata commit `1c09021` resolved pin conflicts; live env successfully rebuilt 2026-04-22. |
| 2 | numpy<2 pin active; 4 monkey-patches deleted from products/cslc.py | VERIFIED | `grep numpy>=1.26,<2.0 conda-env.yml` returns 1 line; `grep _patch_ src/subsideo/products/cslc.py` returns 0 hits; `grep np\.string_\s*=\s*np\.bytes_ src/subsideo/products/cslc.py` returns 0 hits. |
| 3 | `src/subsideo/_cog.py` single-route for rio_cogeo + IFD-offset heal (ensure_valid_cog) | VERIFIED | File exists (123 lines); 5 public names `cog_validate, cog_translate, cog_profiles, ensure_valid_cog, RIO_COGEO_VERSION` present at declared line numbers; `from rio_cogeo|import rio_cogeo` under `src/` returns hits ONLY in `src/subsideo/_cog.py`; 4 consumer files import `from subsideo._cog import`; `RIO_COGEO_VERSION() == (6, 0, 0)` at runtime. 44 unit tests pass (test_cog_helper + test_metadata + test_rtc_pipeline + test_dist_pipeline + test_dswx_pipeline). |
| 4 | `src/subsideo/_mp.py` full fork bundle + configure_multiprocessing() at top of 5 run_*() | VERIFIED | File exists (94 lines); `configure_multiprocessing` + `_CONFIGURED` + `MPLBACKEND` + `RLIMIT_NOFILE` + `forkserver` all present; `rg 'from subsideo\._mp import configure_multiprocessing' src/subsideo/products/` returns 5 hits; `rg '^\s*configure_multiprocessing\(\)' src/subsideo/products/` returns 5 hits (one per run_*()). 6 unit tests in test_mp_helper.py pass. |
| 5 | `src/subsideo/validation/stable_terrain.py` + selfconsistency.py (CSLC-01, CSLC-02) — pure functions, no module-top I/O | VERIFIED | Both files exist (208 + 165 lines); `build_stable_mask` with `WORLDCOVER_BARE_SPARSE_CLASS=60`, `DEFAULT_COAST_BUFFER_M=5000.0`, `DEFAULT_WATER_BUFFER_M=500.0`, `DEFAULT_SLOPE_MAX_DEG=10.0` module constants present; `coherence_stats` returns 5-key dict `{mean, median, p25, p75, persistently_coherent_fraction}` (verified empirically); `residual_mean_velocity` subtracts median anchor before averaging (verified: `[1,2,3]` → 0.0). 25 unit tests pass. |
| 6 | `src/subsideo/validation/criteria.py` frozen Criterion + flat CRITERIA registry | VERIFIED | File exists (213 lines); `@dataclass(frozen=True)` + `class Criterion`; `len(CRITERIA) == 13`; `9 BINDING + 4 CALIBRATING`; every CALIBRATING has `binding_after_milestone == 'v1.2'` (verified programmatically); every BINDING has `binding_after_milestone is None`. 7 test_criteria_registry tests pass. |
| 7 | `src/subsideo/validation/results.py` ProductQualityResult + ReferenceAgreementResult nested composites (no stored pass-bools) | VERIFIED | File exists (101 lines); `class ProductQualityResult` + `class ReferenceAgreementResult` + `def evaluate` + `def measurement_key` all present; `grep pass_criteria src/` returns 0 hits outside docstrings (which explicitly say "NEVER holds a .passed bool"); `grep pass_criteria tests/` returns 0 hits. Evaluate round-trip verified: `{'cslc.selfconsistency.coherence_min': True}` for measurement `coherence=0.75` above threshold 0.7. |
| 8 | `src/subsideo/validation/harness.py` 6 public helpers + RETRY_POLICY + ReferenceDownloadError | VERIFIED | File exists (541 lines); 6 public functions all present at declared line numbers (`bounds_for_burst`, `bounds_for_mgrs_tile`, `credential_preflight`, `select_opera_frame_by_utc_hour`, `ensure_resume_safe`, `download_reference_with_retry`); `RETRY_POLICY` dict has 4 keys `{CDSE, CLOUDFRONT, EARTHDATA, HTTPS}`; `class ReferenceDownloadError` defined; `_mgrs_tiles.geojson` seed ships 3 tiles (10TFK, 29TNF, 33TXP). 20 unit tests pass. |
| 9 | `bounds_for_burst` wraps opera_utils with `subsideo.burst.db` fallback | VERIFIED | harness.py lines 101-174 implement the two-path lookup (`opera_utils.burst_frame_db.get_burst_id_geojson` primary + `subsideo.burst.db.query_bounds` fallback); `def query_bounds` added at `src/subsideo/burst/db.py:176`; raises ValueError citing BOTH failure paths when neither finds the burst_id. |
| 10 | 8 eval scripts all consume harness (run_eval.py + 7 batch-migrated) | VERIFIED | `grep -E '^EXPECTED_WALL_S\s*=' run_eval*.py` returns 8 hits (one per script); `grep bounds_for_(burst\|mgrs_tile)` finds 56 hits across 8 scripts; `grep 'bounds\s*=\s*\[-?[0-9]' run_eval*.py` returns 0 hits (zero hand-coded numeric bounds); `grep 'if not os\.environ\.get' run_eval*.py` returns 0 hits (all replaced by credential_preflight); scripts/env07_diff_check.py EXIT=0 for both acceptance pairs (disp/disp_egms + dist/dist_eu). |
| 11 | `src/subsideo/validation/supervisor.py` subprocess watchdog (mtime + py-spy + killpg + exit 124) | VERIFIED | File exists (309 lines); `GRACE_WINDOW_S=120`, `TIMEOUT_EXIT_CODE=124`, `KILL_GRACE_S=30`, `POLL_INTERVAL_S=30` constants declared; `subprocess.Popen(..., start_new_session=True)` at line 233 creates new process group; `os.killpg(pgid, SIGTERM)` then `SIGKILL` at lines 261, 269; `_py_spy_dump` writes stack dump; `_parse_expected_wall_s` AST-parses all 8 eval scripts successfully (verified programmatically, values {900, 1800×5, 2700, 5400×2}). 17 unit tests pass. `python -m subsideo.validation.supervisor --help` prints argparse usage. |
| 12 | Makefile with 10 cells | VERIFIED | Makefile exists (62 lines); declares 10 eval-{product}-{region} targets: eval-rtc-nam, eval-rtc-eu, eval-cslc-nam, eval-cslc-eu, eval-disp-nam, eval-disp-eu, eval-dist-nam, eval-dist-eu, eval-dswx-nam, eval-dswx-eu; plus aggregators eval-all, eval-nam, eval-eu; plus results-matrix and FORCE-guarded clean-cache. `make -n eval-rtc-nam` shows `micromamba run -n subsideo python -m subsideo.validation.supervisor run_eval.py`; `make -n clean-cache` refuses without FORCE=1. |
| 13 | `src/subsideo/validation/matrix_schema.py` (Pydantic v2) + matrix_writer.py + results/matrix_manifest.yml | VERIFIED | matrix_schema.py exists (153 lines) with `class MetaJson` + `class MetricsJson` + 2 nested sub-schemas, all Pydantic v2 `BaseModel` with `extra='forbid'` and `schema_version: int = 1`; matrix_writer.py exists (199 lines) with `def write_matrix` + `def main`; `results/matrix_manifest.yml` exists with all 10 cells (schema_version:1, 5 products × 2 regions); `python -m subsideo.validation.matrix_writer --manifest results/matrix_manifest.yml --out /tmp/verify_matrix.md` exits 0 and produces valid two-column Markdown (all 10 cells render RUN_FAILED pre-eval as expected for Phase 1 state). 14 unit tests pass. |
| 14 | `env.lockfile.osx-arm64.txt` + `env.lockfile.linux-64.txt` | VERIFIED | osx-arm64 lockfile: 574 lines, 434 conda-forge URL pins, contains tophu / dist-s1 / py-spy / isce3 / rio-cogeo; linux-64 lockfile: 592 lines, 443 conda-forge URL pins, same key packages plus tophu==0.2.1 via pip. Two-layer format with `# --- PIP LAYER ---` marker. |
| 15 | `Dockerfile` (mambaorg/micromamba) + `Apptainer.def` + `.dockerignore` | VERIFIED | Dockerfile (50 lines): multi-stage, `FROM mambaorg/micromamba:latest AS builder` + runtime stage, `USER $MAMBA_USER` preserved, `MAMBA_DOCKERFILE_ACTIVATE=1`, no CUDA, no USER root, CMD runs pytest. Apptainer.def (27 lines): `Bootstrap: docker-daemon` + `From: subsideo:dev` + `%runscript exec micromamba run -n base` + `%test` stanza. .dockerignore (45 lines) excludes `.planning/`, `eval-*/`, `__pycache__/`, `.git/`, credentials; preserves src/, tests/, pyproject.toml, conda-env.yml. |
| 16 | `01-09-ACCEPTANCE.md` D-18 two-platform validation | VERIFIED | File exists (185 lines); documents osx-arm64 GREEN (env create + lockfile + pytest smoke) + linux-64-via-Docker GREEN (docker build after Task 5 fix + lockfile + pytest-in-container); both platforms report identical 285/6-failed pytest counts confirming env parity. Also documents the Task 5 Dockerfile /app staging fix and the 7 pre-existing test failures (6 in current state after Plan 01-05 refactor reduced them from 7 → 6). |
| 17 | All 17 requirement IDs (ENV-01..10, GATE-01..05, CSLC-01..02) claimed by plans | VERIFIED | Union of plan frontmatter `requirements:` covers all 17 IDs: ENV-01 (01-01), ENV-02 (01-01, 01-03), ENV-03 (01-02), ENV-04 (01-03), ENV-05 (01-07), ENV-06 (01-06), ENV-07 (01-06, 01-07), ENV-08 (01-06, 01-07), ENV-09 (01-01, 01-07, 01-08), ENV-10 (01-01, 01-09), GATE-01 (01-05), GATE-02 (01-05), GATE-03 (01-08, 01-09), GATE-04 (01-05), GATE-05 (01-05), CSLC-01 (01-04), CSLC-02 (01-04). Zero ORPHANED requirements. |

**Score:** 17/17 must-haves verified

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `conda-env.yml` | Two-layer manifest with numpy<2, tophu=0.2.1, dist-s1=2.0.14, py-spy=0.4.1, rio-cogeo==6.0.0 | VERIFIED | 88 lines; all pins present |
| `src/subsideo/_cog.py` | ≥80 lines; 5 public names; lazy imports | VERIFIED | 123 lines; rio_cogeo imports inside function bodies only |
| `src/subsideo/_mp.py` | ≥50 lines; configure_multiprocessing + _CONFIGURED | VERIFIED | 94 lines; idempotent via _CONFIGURED flag |
| `src/subsideo/validation/stable_terrain.py` | ≥80 lines; build_stable_mask | VERIFIED | 208 lines |
| `src/subsideo/validation/selfconsistency.py` | ≥80 lines; coherence_stats + residual_mean_velocity | VERIFIED | 165 lines |
| `src/subsideo/validation/criteria.py` | ≥180 lines; 13-entry CRITERIA | VERIFIED | 213 lines; 13 entries (9 BINDING + 4 CALIBRATING) |
| `src/subsideo/validation/results.py` | ≥80 lines; composite result types | VERIFIED | 101 lines |
| `src/subsideo/validation/harness.py` | ≥250 lines; 6 helpers + RETRY_POLICY | VERIFIED | 541 lines; all 6 helpers exported |
| `src/subsideo/validation/supervisor.py` | ≥150 lines; run + main + helpers | VERIFIED | 309 lines |
| `src/subsideo/validation/matrix_schema.py` | ≥80 lines; MetaJson + MetricsJson | VERIFIED | 153 lines |
| `src/subsideo/validation/matrix_writer.py` | ≥150 lines; write_matrix + main | VERIFIED | 199 lines |
| `src/subsideo/validation/_mgrs_tiles.geojson` | 3 tiles (10TFK, 29TNF, 33TXP) | VERIFIED | 1491 bytes; 3 features, closed-ring polygons |
| `src/subsideo/products/types.py` | 5 nested-composite ValidationResult classes | VERIFIED | All 5 verified programmatically (`product_quality` + `reference_agreement` fields; no pass_criteria) |
| `results/matrix_manifest.yml` | 10 cells, schema_version:1 | VERIFIED | 98 lines; 10 cells with eval_script/cache_dir/metrics_file/meta_file/conclusions_doc |
| `Makefile` | 10 eval cells + aggregators + results-matrix + clean-cache | VERIFIED | 62 lines; all targets parse; `make -n` dry-runs correct |
| `Dockerfile` | Multi-stage mambaorg/micromamba | VERIFIED | 50 lines; build tested GREEN per 01-09-ACCEPTANCE.md |
| `Apptainer.def` | docker-daemon bootstrap | VERIFIED | 27 lines |
| `.dockerignore` | Thin build context | VERIFIED | 45 lines |
| `env.lockfile.osx-arm64.txt` | ≥50 lines; two-layer | VERIFIED | 574 lines; all expected pins present |
| `env.lockfile.linux-64.txt` | ≥50 lines; two-layer | VERIFIED | 592 lines; all expected pins present |
| `scripts/env07_diff_check.py` | ≥50 lines; machine-verifiable | VERIFIED | 151 lines; EXIT=0 on both acceptance pairs |

## Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `conda-env.yml` | pyproject.toml extras | `pip: -e .[validation,viz]` | WIRED | Confirmed at conda-env.yml:86 |
| `_metadata.py`, `products/{rtc,dist,dswx}.py` | `subsideo._cog` | `from subsideo._cog import` | WIRED | 4 files import from _cog; rio_cogeo imports routed only through _cog |
| All 5 `run_*()` entry points | `_mp.configure_multiprocessing` | deferred function-body import | WIRED | 5/5 hits for `from subsideo._mp import configure_multiprocessing` and 5/5 `configure_multiprocessing()` calls |
| `validation/selfconsistency` | `validation/stable_terrain` | `from subsideo.validation.stable_terrain import build_stable_mask` | WIRED | Consumer unit tests in Phase 3/4 will exercise |
| `validation/harness.bounds_for_burst` | `opera_utils + subsideo.burst.db.query_bounds` | Primary + fallback chain | WIRED | 20 harness unit tests exercise both paths |
| `run_eval.py` pilot | `validation/harness` | `from subsideo.validation.harness import bounds_for_burst, credential_preflight, ...` | WIRED | `grep bounds_for_burst run_eval.py` returns ≥1 hit |
| Makefile eval-* targets | `validation/supervisor` | `python -m subsideo.validation.supervisor <script>` | WIRED | `make -n eval-rtc-nam` prints correct supervisor invocation |
| `matrix_writer` | `criteria.CRITERIA + results.ProductQualityResult/ReferenceAgreementResult + measurement_key` | imports from `subsideo.validation.{criteria,results}` | WIRED | `python -m subsideo.validation.matrix_writer` produces valid matrix.md |
| `validation/__init__.py` | All public names | re-export hub | WIRED | 22 names in `__all__`; every Phase 1 deliverable importable via `from subsideo.validation import X` |

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `build_stable_mask` | returned boolean mask | DB-less pure function over numpy arrays | YES (verified: 9/9 stable px on all-60 input) | FLOWING |
| `coherence_stats` | returned dict | pure numpy over input stack | YES (verified: 5-key dict with real values on 3x3 stack) | FLOWING |
| `residual_mean_velocity` | returned float | pure numpy over velocity + mask | YES (verified: `[1,2,3]` → 0.0 median-centred) | FLOWING |
| `evaluate(ProductQualityResult)` | pass/fail dict | criteria lookup + comparator fn | YES (verified: `{coherence: 0.75}` → `{cslc.selfconsistency.coherence_min: True}`) | FLOWING |
| `write_matrix` | results/matrix.md rows | YAML manifest + metrics.json sidecars | YES (10 cells render RUN_FAILED pre-eval; pipeline will populate once Phase 2+ writes sidecars) | FLOWING |
| `bounds_for_burst('t144_308029_iw1')` | 4-tuple bounds | opera_utils.burst_frame_db | YES (verified in SUMMARY 01-06: `(-119.48, 33.43, -118.52, 33.77)`) | FLOWING |
| `_parse_expected_wall_s` | int wall-time budget | AST parse of module-level constant | YES (verified: parses 8/8 eval scripts; values 900–5400) | FLOWING |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All Phase 1 public APIs importable | `python -c "from subsideo.validation import *; from subsideo._cog import *; from subsideo._mp import *"` | Succeeded | PASS |
| CRITERIA registry has 13 entries (9 BINDING + 4 CALIBRATING) | `python -c "from subsideo.validation import CRITERIA; ..."` | "CRITERIA entries: 13; BINDING: 9; CALIBRATING: 4" | PASS |
| Every CALIBRATING has `binding_after_milestone == 'v1.2'` | AST walk | "GATE-01/GATE-05 verified" | PASS |
| rio-cogeo pinned to 6.x | `RIO_COGEO_VERSION()` | `(6, 0, 0)` | PASS |
| Supervisor constants correct | TIMEOUT_EXIT_CODE, GRACE_WINDOW_S | 124, 120 | PASS |
| RETRY_POLICY 4 sources | `list(RETRY_POLICY.keys())` | `['CDSE', 'CLOUDFRONT', 'EARTHDATA', 'HTTPS']` | PASS |
| Matrix writer end-to-end | `python -m subsideo.validation.matrix_writer --manifest results/matrix_manifest.yml --out /tmp/verify_matrix.md` | "10 cells written" with valid two-column Markdown | PASS |
| ENV-07 diff classifier disp/disp_egms | `python scripts/env07_diff_check.py run_eval_disp.py run_eval_disp_egms.py` | EXIT=0 "diff is reference-data only" | PASS |
| ENV-07 diff classifier dist/dist_eu | `python scripts/env07_diff_check.py run_eval_dist.py run_eval_dist_eu.py` | EXIT=0 | PASS |
| Supervisor AST-parse all 8 eval scripts | `_parse_expected_wall_s()` for each | All 8 return valid ints | PASS |
| Makefile eval-rtc-nam dry-run | `make -n eval-rtc-nam` | Prints correct supervisor invocation | PASS |
| Makefile clean-cache safety | `make -n clean-cache` (no FORCE=1) | exits 2 with refusal message | PASS |
| Supervisor CLI --help | `python -m subsideo.validation.supervisor --help` | Prints argparse usage | PASS |
| Phase 1 new unit tests | `pytest tests/unit/test_{cog_helper,mp_helper,stable_terrain,selfconsistency,criteria_registry,harness,supervisor,matrix_schema,matrix_writer}.py` | 96 passed, 0 failed | PASS |
| Product-quality + reference-agreement tests | `pytest tests/product_quality tests/reference_agreement` | 26 passed, 0 failed | PASS |
| Full unit-test suite | `pytest tests/unit` | 285 passed, 6 failed (pre-existing deferred items) | PASS (regressions = 0) |

## Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| ENV-01 | 01-01 | Single-command env create, no post-install pip, tophu from conda-forge, numpy<2 | SATISFIED | conda-env.yml with two-layer pins; errata commit `1c09021` resolved osx-arm64 solve conflicts; linux-64 install via Docker tested GREEN |
| ENV-02 | 01-01, 01-03 | No runtime monkey-patches in products/; numpy<2 obviates _patch_* | SATISFIED | `grep _patch_ src/subsideo/products/` returns 0 hits; `np.string_ = np.bytes_` removed |
| ENV-03 | 01-02 | All rio_cogeo routed through `_cog.py`; rio-cogeo==6.0.0 | SATISFIED | Single-file routing proven by grep; IFD-heal path implemented and unit-tested |
| ENV-04 | 01-03 | `_mp.configure_multiprocessing()` at top of every run_*() | SATISFIED | 5 hits in src/subsideo/products/; full P0.1 bundle (start method + MPLBACKEND + RLIMIT_NOFILE + forkserver fallback) |
| ENV-05 | 01-07 | Subprocess watchdog + os.killpg + 124 exit | SATISFIED | supervisor.py implements D-10..D-13 contract; 17 unit tests pass. 3-consecutive dist-run soak test not yet executed (acceptance spec belongs to Phase 5) but core watchdog semantics are all tested |
| ENV-06 | 01-06 | harness.py 6 public helpers | SATISFIED | All 6 exposed + RETRY_POLICY + ReferenceDownloadError |
| ENV-07 | 01-06, 01-07 | Eval scripts consume harness; diffs are reference-data only | SATISFIED | scripts/env07_diff_check.py EXIT=0 on both acceptance pairs |
| ENV-08 | 01-06, 01-07 | No hand-coded bounds; all via bounds_for_burst / bounds_for_mgrs_tile | SATISFIED | `grep 'bounds\s*=\s*\[-?[0-9]' run_eval*.py` returns 0 hits; 56 hits for harness bounds helpers |
| ENV-09 | 01-01, 01-07, 01-08 | Makefile eval-all / eval-nam / eval-eu; per-cell isolation | SATISFIED | Makefile with 10 cells + aggregators + results-matrix; supervisor subprocess isolation verified |
| ENV-10 | 01-01, 01-09 | Committed lockfile + Dockerfile or Apptainer | SATISFIED | Both per-platform lockfiles + Dockerfile + Apptainer.def committed; D-18 two-platform validation GREEN |
| GATE-01 | 01-05 | Immutable criteria.py with CALIBRATING/BINDING + binding_after_milestone | SATISFIED | 13-entry CRITERIA, frozen Criterion dataclass, every CALIBRATING carries 'v1.2' |
| GATE-02 | 01-05 | Split ProductQualityResult / ReferenceAgreementResult; no .passed bool | SATISFIED | 5 composite ValidationResult types verified; 0 `pass_criteria` hits outside docstrings |
| GATE-03 | 01-08, 01-09 | results/matrix.md 2 columns per cell; CALIBRATING distinguished | SATISFIED | Matrix writer emits two-column markdown with CALIBRATING italics + (CALIBRATING) tag |
| GATE-04 | 01-05 | tests/product_quality vs tests/reference_agreement split | SATISFIED | Both directories exist; conftest.py AST linter rejects numeric-literal comparands (pytest.exit(returncode=4)) |
| GATE-05 | 01-05 | CALIBRATING gates ship with binding_after_milestone='v1.2' | SATISFIED | All 4 CALIBRATING criteria carry v1.2; enforced via unit test |
| CSLC-01 | 01-04 | validation/stable_terrain.py build_stable_mask from WorldCover class 60 + slope<10° + coast + water buffers | SATISFIED | 10 unit tests cover all 4 gates; CSLC-01 defaults exposed as module constants |
| CSLC-02 | 01-04 | validation/selfconsistency.py coherence_stats + residual_mean_velocity | SATISFIED | 15 unit tests cover 5-key return + persistence threshold + median/mean anchors |

**Orphaned requirements:** None. All 17 Phase 1 requirement IDs claimed by at least one plan frontmatter.

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| src/subsideo/validation/compare_disp.py | 319 | `src.nodata` after `rasterio.open(...)` context exits (CR-01) | Warning (quality-debt) | Per verification_notes: classified as quality-debt for `/gsd-code-review-fix` before Phase 4 execution; does not block phase completion. Will fail EGMS L2a comparison at runtime when nodata is declared. |
| src/subsideo/validation/harness.py | 515 | `resp.raise_for_status()` raises RequestException subclass silently caught by retry fallback (CR-02) | Warning (quality-debt) | Per verification_notes: classified as quality-debt. Unknown 5xx silently retried, violating RETRY_POLICY contract. |
| src/subsideo/validation/compare_cslc.py | 92-123 | Silent shape-mismatch fall-through when coords missing (WR-02) | Info | quality-debt, Phase 3 touchup |
| src/subsideo/_cog.py | 114-123 | Deterministic temp file race for parallel heals (WR-03) | Info | quality-debt, edge case |
| src/subsideo/_mp.py | 31-88 | `_CONFIGURED` flag not thread-safe (WR-04) | Info | quality-debt, low probability |
| src/subsideo/validation/compare_cslc.py | 169-170 | Division by zero in coherence (WR-05) | Info | quality-debt, Phase 3 |
| src/subsideo/burst/db.py | 216-220 | `sqlite3.connect` context manager does not close connection (WR-06) | Info | quality-debt |
| src/subsideo/validation/compare_dswx.py | 4, 110 | Missing `urllib.error` import (WR-07) | Info | quality-debt |
| src/subsideo/validation/matrix_writer.py | 148 | Unvalidated manifest path (WR-08) | Info | quality-debt, defense-in-depth |
| src/subsideo/validation/harness.py | 298-303 | `credential_preflight` treats whitespace as set (WR-09) | Info | quality-debt |
| src/subsideo/validation/supervisor.py | 231-234 | Script path validation missing (WR-10) | Info | quality-debt, low threat surface |
| Various | — | 5 info-severity findings from 01-REVIEW.md | Info | Tracked for Phase 7 pre-release audit |

**Classification:** All 17 findings in 01-REVIEW.md are classified as **quality-debt** per verification_notes. None block Phase 1 completion. Listed in frontmatter `quality_debt` section for `/gsd-code-review-fix` handoff before Phase 3/4 execution.

## Deferred Items

Pre-existing test failures documented in `deferred-items.md` and confirmed by running the full unit suite (285 passed / 6 failed). These are NOT regressions introduced by Phase 1; they pre-exist and have named Phase 4/5 owners.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | tests/unit/test_compare_dswx.py::TestJrcTileUrl::test_url_format | Phase 6 DSWx | Stale JRC tile-ID assertion; owner is compare_dswx.py |
| 2 | tests/unit/test_compare_dswx.py::TestBinarizeDswx::test_class_mapping | Phase 6 DSWx | binarize_dswx default classes changed |
| 3 | tests/unit/test_disp_pipeline.py::test_run_disp_mocked | Phase 4 DISP | DISPResult.valid=True under mocked fixtures; dolphin workflow mocks stale |
| 4 | tests/unit/test_disp_pipeline.py::test_run_disp_qc_warning | Phase 4 DISP | Same dolphin workflow mock gap |
| 5 | tests/unit/test_metadata_wiring.py::TestMetadataInjectionInDISP::test_run_disp_calls_inject_opera_metadata | Phase 4 DISP | Post-01-05 DISP pipeline refactor; mock-call assertion drift |
| 6 | tests/unit/test_orbits.py::TestFetchOrbit::test_fallback_to_s1_orbits | Targeted fix (not scope-bound to v1.1 phase) | ConnectionError in fallback path before assertion |

**Status impact:** Deferred items do not affect the phase pass status. Every Phase 1 deliverable is verified; these 6 failures pre-exist and are tracked in `deferred-items.md` with named owners.

## Gaps Summary

No gaps found. All 17 must-haves verified:

- Environment manifest (conda-env.yml) + lockfiles + Dockerfile + Apptainer.def: landed and D-18 validated on osx-arm64 and linux-64.
- Shared validation substrate (stable_terrain.py + selfconsistency.py): 25 unit tests passing; CSLC-01 + CSLC-02 closed.
- Immutable criteria registry (13 entries): frozen Criterion dataclass; 9 BINDING + 4 CALIBRATING; every CALIBRATING carries `binding_after_milestone='v1.2'`.
- Composite ValidationResult (5 products): 2-field nested composite with no `.passed` bool; `evaluate()` read-time pass/fail computation; drift-safe.
- Harness with 6 helpers + RETRY_POLICY + MGRS-tile seed + burst-DB fallback: 20 unit tests; pilot + 7 batch-migrated eval scripts consume it end-to-end.
- Supervisor with mtime/py-spy/killpg + exit 124: 17 unit tests; AST-parse verified on all 8 eval scripts.
- Makefile with 10 matrix cells + FORCE-guarded clean-cache: dry-runs verified; supervisor delegation confirmed.
- Matrix writer with Pydantic v2 schemas + manifest-driven rendering + CALIBRATING italics: 14 unit tests; end-to-end render produces valid markdown with threshold echo.
- ENV-07 machine-verifiable diff classifier: both acceptance pairs (disp/disp_egms + dist/dist_eu) EXIT=0.

**Quality-debt notice:** 01-REVIEW.md identified 2 critical + 10 warning + 5 info findings. Per verification_notes, these are classified as quality-debt for `/gsd-code-review-fix` before Phase 3/4 execution and do NOT block Phase 1 completion. Phase 1's goal — land the foundation — is met. The two critical findings (CR-01 rasterio-closed-context, CR-02 retry-swallow) should be prioritized before Phase 3 (which will exercise compare_cslc against live references) and Phase 4 (which will exercise compare_disp's EGMS L2a path).

---

*Verified: 2026-04-22T17:55:00Z*
*Verifier: Claude (gsd-verifier)*
