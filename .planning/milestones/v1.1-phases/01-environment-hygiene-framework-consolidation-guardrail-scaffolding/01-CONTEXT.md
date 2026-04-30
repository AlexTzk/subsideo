# Phase 1: Environment Hygiene, Framework Consolidation & Guardrail Scaffolding - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 is the v1.1 validation-hardening foundation. It delivers the structural skeleton every downstream phase (2 RTC EU, 3 CSLC self-consistency, 4 DISP adapter, 5 DIST, 6 DSWx, 7 results matrix) consumes:

- **Environment hygiene** — `conda-env.yml` + per-platform lockfiles + Dockerfile/Apptainer; `numpy<2` pin; remove 4 monkey-patches from `products/cslc.py`; tophu via conda-forge; centralise `rio_cogeo` through `_cog.py`; macOS multiprocessing fork bundle in `_mp.py`; subprocess-level watchdog.
- **Framework consolidation** — `validation/harness.py` with 5 shared helpers (`select_opera_frame_by_utc_hour`, `download_reference_with_retry`, `ensure_resume_safe`, `credential_preflight`, `bounds_for_burst`); all 7 existing eval scripts refactored to consume the harness; hand-coded geographic bounds eliminated.
- **Guardrail scaffolding** — immutable `validation/criteria.py` with `CALIBRATING`/`BINDING` distinction + `binding_after_milestone` enforcement; split `ProductQualityResult` / `ReferenceAgreementResult` dataclasses (no top-level `.passed`); `tests/product_quality/` vs `tests/reference_agreement/` directory split; shared `validation/stable_terrain.py` + `validation/selfconsistency.py` modules (consumed by Phase 3 CSLC and Phase 4 DISP); per-cell-isolated Makefile + `matrix_manifest.yml` + per-eval `meta.json`/`metrics.json` sidecars.

**Not this phase:** running any eval beyond the regression smoke tests (that's Phases 2-6); picking coherence statistic (mean/median/persistently-coherent) — Phase 3 calibration decision; DISP multilook default — Phase 4 ADR.

Phase 1 deliverables are the 17 requirements mapped to it: ENV-01..10 + GATE-01..05 + CSLC-01..02.

</domain>

<decisions>
## Implementation Decisions

### `criteria.py` API shape & immutability (ENV-06 support, GATE-01, GATE-05, M1/M4/M5/M6)

- **D-01:** `Criterion` is a `@dataclass(frozen=True)` with fields: `name: str`, `threshold: float`, `comparator: Literal['>', '>=', '<', '<=']`, `type: Literal['BINDING', 'CALIBRATING']`, `binding_after_milestone: str | None` (None for BINDING), `rationale: str` (why this threshold exists; cites upstream spec, ADR, or architectural ceiling).
- **D-02:** Criteria grouping: **flat `CRITERIA: dict[str, Criterion]` registry** keyed by canonical ID (`'rtc.rmse_db_max'`, `'cslc.amplitude_r_min'`, `'cslc.selfconsistency.coherence_min'`, etc.) for iteration (matrix writer, tests), **plus typed accessor functions** (`def rtc_rmse_db_max() -> Criterion: return CRITERIA['rtc.rmse_db_max']`) for call-site readability in `compare_*.py`.
- **D-03:** Immutability enforcement is **runtime `frozen=True` + drift visibility** — no CI hash-check, no CODEOWNERS/pre-commit hook. The `matrix_writer` echoes the criterion name + threshold alongside every measured value in `results/matrix.md`, so any criterion edit produces a visible git diff of the matrix itself. PR review policy: any edit to `validation/criteria.py` must cite an ADR or upstream spec change in the PR description.
- **D-04:** Phase 1 populates criteria.py with two scope sets:
  - **v1.0 BINDING criteria already hardcoded in compare_*.py** — RTC: `RMSE_DB_MAX=0.5`, `R_MIN=0.99`. CSLC amplitude sanity: `R_MIN=0.6`, `RMSE_DB_MAX=4`. DISP: `R_MIN=0.92`, `BIAS_MM_YR_MAX=3`. DIST: `F1_MIN=0.80`, `ACCURACY_MIN=0.85`. DSWx: `F1_MIN=0.90` (rationale cites DSWE architectural ceiling ≈ 0.92 — no relaxation per M4).
  - **Phase 3/4-needed new CALIBRATING gates** — `cslc.selfconsistency.coherence_min=0.7` and `cslc.selfconsistency.residual_mm_yr_max=5`, both with `type='CALIBRATING'` and `binding_after_milestone='v1.2'` (per GATE-05: ≥3 measured data points before promotion). Same pair mirrored for `disp.selfconsistency.*`.
- **D-05:** Phase 5 deliverables (EFFIS precision/recall, DSWx recalibration F1 threshold reaffirmation) are **deferred to Phase 5** — Phase 1 does NOT pre-populate placeholders. Adding a criterion is additive; Phase 5 adds its own entries when it lands.
- **Claude's Discretion:** Matrix-writer metadata rules (how CALIBRATING cells are visually distinguished, how `binding_after_milestone` is enforced at milestone-close) live in `matrix_writer.py`, not `criteria.py` — per research Anti-Pattern 1 (don't conflate data-output shapes with threshold constants).

### Split `ProductQualityResult` / `ReferenceAgreementResult` (GATE-02, M2)

- **D-06:** **Nested composite shape.** Each per-product result (e.g. `CSLCValidationResult`, `DISPValidationResult`) becomes `@dataclass class CSLCValidationResult: product_quality: ProductQualityResult, reference_agreement: ReferenceAgreementResult`. No top-level `.passed` attribute — the two sub-results are always surfaced separately. Matrix writer reads both fields from a single `metrics.json` per eval cell.
- **D-07:** **Location: new `src/subsideo/validation/results.py` module.** Contains the two generic base types (`ProductQualityResult`, `ReferenceAgreementResult`). Per-product types (`CSLCValidationResult`, etc.) stay in `src/subsideo/products/types.py` but their fields now compose with the two generic types. Import direction: `products/types.py → validation/results.py` is safe (results.py has no `products` or `validation/compare_*` imports). This respects research ARCHITECTURE § Failure-Mode Boundaries (forbidden: `products/* → validation/*` as a full validation dependency; importing data-only types from `validation/results.py` is acceptable as a one-way leaf).
- **D-08:** **Named fields + criterion IDs, no stored bools.** Each result stores `measurements: dict[str, float]` (measured values) and `criterion_ids: list[str]` (which `CRITERIA` registry entries apply). Pass/fail is **computed at read time** by `evaluate(result, criteria) -> dict[criterion_id, bool]`. Never stored as a bool on the result object — this makes pass/fail drift-safe: edits to `criteria.py` thresholds re-evaluate old `metrics.json` records correctly. Replaces the current `pass_criteria: dict[str, bool]` field.
- **D-09:** **Big-bang migration in Phase 1.** Single commit/PR replaces all 5 per-product ValidationResult types + all 5 `compare_*.py` return signatures + all affected tests. No adapter shim, no `@property` back-compat aliases, no per-phase migration. Fail-fast: any v1.0 script still reading `.correlation` or `.f1` breaks immediately — caught by the tests-dir-split migration in the same commit bundle.

### Watchdog mechanics (ENV-04, ENV-05, P0.1)

- **D-10:** **Throughput heuristic: output-directory mtime staleness.** The supervisor polls the eval's cache_dir recursively every 30s, tracks the newest entry's mtime. If nothing has changed for a `grace_window=120s` AND wall time has exceeded `2 × EXPECTED_WALL_S` → abort. Matches how existing eval scripts signal progress (they continuously write stage outputs).
- **D-11:** **Wall-time source: caller-supplied per-script constant.** Each `run_eval_*.py` declares a module-level `EXPECTED_WALL_S = 1800` (or appropriate value). Supervisor reads it via subprocess environment or by parsing the script's AST at launch. Script authors know their workload; no central registry in criteria.py (wall-time is ops, not science).
- **D-12:** **Scope: per-script subprocess wrap via Makefile supervisor.** Makefile target runs `python -m subsideo.validation.supervisor run_eval_dist.py` (not `python run_eval_dist.py`). Supervisor forks the script as subprocess, monitors wall + throughput, sends SIGTERM then SIGKILL to the **process group** via `os.killpg` (catches isce3/dist-s1 grandchildren). Per-cell isolation — one hang cannot stage the matrix; each subprocess gets fresh network pool, fresh FD table, fresh matplotlib state (research P0.1 mitigation).
- **D-13:** **Abort diagnostics: py-spy dump + SIGTERM→SIGKILL + exit 124.** Before killing, supervisor runs `py-spy dump --pid <pid>` and writes Python stack traces to `<cache_dir>/watchdog-stacks.txt`. Send SIGTERM to process group; 30s grace; SIGKILL if still alive. Exit 124 (conventional `timeout(1)` exit code) so Makefile can distinguish watchdog abort from other failures. `py-spy` added to conda-env.yml as a lightweight dependency (pip, no native build).
- **D-14:** `_mp.configure_multiprocessing()` (called at top of every `run_*()` entry point per ENV-04) is **separate** from the supervisor. It handles: `set_start_method('fork')` on macOS with `forkserver` fallback for Python ≥3.14; `os.environ['MPLBACKEND'] = 'Agg'` before any matplotlib import; `resource.setrlimit(RLIMIT_NOFILE, (4096, hard))`; close any module-global `requests.Session` cached before fork. The supervisor is the outer boundary (subprocess + watchdog); `_mp` is inner config within each subprocess.

### Env authoring & reproducibility recipe (ENV-01, ENV-02, ENV-09, ENV-10, REL-04, REL-06)

- **D-15:** **Two-layer conda-env.yml.** Root-level `conda-env.yml` lists only conda-forge binary deps (`python=3.11`, `numpy<2.0`, `isce3=0.25.10`, `gdal>=3.8`, `dolphin=0.42.5`, `tophu=0.2.1`, `snaphu`, `compass=0.5.6`, `opera-rtc=1.0.4`, `dist-s1=2.0.14`, `s1reader=0.2.5`, `mintpy=1.6.3`, `rio-cogeo=6.0.0`, `pyaps3>=0.3.6`, `cdsapi`, `py-spy`) then a trailing `pip:` section with `- -e .[validation,viz]` installing the pure-Python layer from pyproject. Single command (`micromamba env create -f conda-env.yml`) produces a working environment. `pyproject.toml` remains the pip source of truth — not duplicated.
- **D-16:** **Per-platform explicit lockfiles.** Two committed files: `env.lockfile.linux-64.txt` (`micromamba list --explicit --md5` from within a Linux Docker container) and `env.lockfile.osx-arm64.txt` (same, from M3 Max). Bit-for-bit rebuild via `micromamba create -n subsideo --file env.lockfile.<platform>.txt`. Regenerated on every `conda-env.yml` edit; Phase 7 pre-release audit verifies rebuild works cold.
- **D-17:** **Reproducibility recipe: Dockerfile primary + Apptainer definition derived.** `Dockerfile` at repo root using `mambaorg/micromamba:latest` as base (NOT `ubuntu:22.04 + apt install micromamba` — the mambaorg image is an order of magnitude smaller and has micromamba pre-configured). Multi-stage: heavy layer (`micromamba env create --file conda-env.yml`) cached in builder; thin runtime copies env + repo source. `Apptainer.def` at repo root derives from the Docker image via `docker-daemon://subsideo:dev`. CPU-only — no CUDA layer (dist-s1 GPU path is M3-incompatible and not needed for closure test).
- **D-18:** **Phase 1 validates BOTH platforms.** Acceptance tests run on:
  - **osx-arm64 (M3 Max, dev machine):** `micromamba env create -f conda-env.yml` + `pytest tests/unit tests/integration` + 3 consecutive `run_eval_dist*.py` runs without hang (ENV-05 acceptance).
  - **linux-64 via Docker on M3 Max:** `docker build . -t subsideo:dev && docker run --rm subsideo:dev micromamba run -n subsideo pytest tests/unit tests/integration` plus one small eval cold (e.g. `docker run --rm subsideo:dev make eval-rtc-nam` provided the OPERA/SAFE inputs are mount-accessible).
  - Phase 7 TrueNAS cold-env `make eval-all` audit remains a **separate Phase 7 deliverable** (REL-04). Phase 1's Linux-via-Docker test catches env-create failures early but does not replace the full TrueNAS cold-env run.
- **D-19:** Windows native + osx-x86_64 are explicitly out of scope (per REQUIREMENTS.md v1.1 anti-features table, per research STACK).

### Claude's Discretion (areas where Claude has flexibility for plan-phase)

- **Tests split migration scope:** Keep existing `tests/unit/` for pure-unit tests; create `tests/product_quality/` (asserts values — includes the migrated self-consistency smoke test fixtures, DSWx F1 gate tests) and `tests/reference_agreement/` (asserts plumbing only — no threshold assertions). Move `tests/unit/test_compare_*.py` into the appropriate new dir based on content inspection (those that assert correlation/RMSE values → reference_agreement, plumbing-only tests stay unit). Flat under each — no per-product subdirs at v1.1 scale. Add `@pytest.mark.reference_agreement` marker + a CI-adjacent linter rule that rejects `assert` statements referencing `criteria.py` thresholds in the `tests/reference_agreement/` tree.
- **Makefile orchestration depth:** Start with the minimum research-specified targets (`eval-all`, `eval-nam`, `eval-eu`, `eval-{product}-{region}`, `results-matrix`, `clean-cache`). Per-burst granularity deferred unless Phase 2 burst probing surfaces a concrete need. Makefile targets call into the Python supervisor, which does the actual subprocess orchestration — Makefile stays thin (~20 lines). Serial by default; `make -j` opt-in is a Phase 7 perf concern, not Phase 1.
- **`metrics.json` + `meta.json` schema split:** Two sidecar files per eval, both in `<cache_dir>/`:
  - `meta.json` — provenance only: `schema_version`, `git_sha`, `git_dirty`, `run_started_iso`, `run_duration_s`, `python_version`, `platform`, `input_hashes: dict[str, str]` (SHA256 of primary inputs — SAFE zips, DEM tile list, orbit file, reference product — not every intermediate).
  - `metrics.json` — scientific: `schema_version`, `product_quality: ProductQualityResult` (serialised), `reference_agreement: ReferenceAgreementResult` (serialised), `criterion_ids_applied: list[str]`, `runtime_conda_list_hash` (optional, SHA of `conda list --explicit` at run time).
  - Both defined by Pydantic v2 models in `validation/matrix_schema.py`; `validation/matrix_writer.py` reads them via manifest lookup. Schema version field on both enables forward evolution.
- **`_cog.py` API:** Match research ARCHITECTURE §2 verbatim — `cog_validate(path) -> tuple[bool, list[str], list[str]]` (is_valid, errors, warnings) with warnings surfaced (not swallowed, per P0.3); `cog_translate(src, dst, profile, **kwargs)`; `RIO_COGEO_VERSION: tuple[int, int, int]`; `ensure_valid_cog(path)` that re-translates in place if IFD-offset warning present (fixes the v1.0 P0.3 silent-COG-degradation bug).
- **`harness.py` per-source retry policy:** Dict-keyed constants inside `harness.py` — `RETRY_POLICY = {'CDSE': {'retry_on': [429, 'OutOfMemoryError'], 'abort_on': [401, 403]}, 'EARTHDATA': {...}, 'CLOUDFRONT': {...refresh_url_on: [403]...}}`. `download_reference_with_retry` refuses to proceed without an explicit source key; raises `ReferenceDownloadError` on abort-status codes.
- **Pilot eval for harness migration:** Land `validation/harness.py` + `run_eval.py` (smallest, well-understood, RTC N.Am. — already PASS in v1.0) migration in the same commit. Batch-migrate the other 6 eval scripts (`run_eval_cslc.py`, `run_eval_disp.py`, `run_eval_disp_egms.py`, `run_eval_dist.py`, `run_eval_dist_eu.py`, `run_eval_dswx.py`) in a single follow-up commit. Eval-diff acceptance check (ENV-07) runs at end of the second commit.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source-of-truth scope (read first)

- `BOOTSTRAP_V1.1.md` — authoritative milestone scope (§0.1–0.7 Phase 1 deliverables; §Dependencies; §Risk register). Research identified 4 corrections to this doc — see SUMMARY below.
- `.planning/ROADMAP.md` §Phase 1 — the 17 requirements, 6 success criteria, internal ordering.
- `.planning/REQUIREMENTS.md` — ENV-01..10 + GATE-01..05 + CSLC-01..02 full text.
- `.planning/PROJECT.md` — v1.0 Key Decisions table (hatchling backend, loguru logging, pydantic-settings config, two-layer install), v1.1 Active requirements checkbox list.
- `.planning/STATE.md` — v1.1 accumulated decisions including the 4 BOOTSTRAP corrections, Phase 1 internal ordering.

### Phase 1 research (authoritative for HOW)

- `.planning/research/SUMMARY.md` — executive summary + 4 BOOTSTRAP corrections table + Phase 0 expansion table (what Phase 1 actually delivers).
- `.planning/research/STACK.md` — v1.1 stack deltas; version pins (numpy<2, tophu=0.2.1 conda-forge, rio-cogeo==6.0.0, tenacity, owslib); explicitly rejected packages.
- `.planning/research/ARCHITECTURE.md` — **critical read for plan-phase.** §1 harness.py public API; §2 `_cog`/`_mp` top-level placement; §3 `prepare_for_reference` in compare_disp.py (Phase 4); §4 DSWx thresholds (Phase 5); §5 eval scripts at repo root; §6 `results/matrix.md` manifest + metrics.json; §7 cache dirs; §8 test architecture; §Failure-Mode Boundaries import-cycle analysis; §Build Order Phase 1 internal ordering (0.1 → 0.3 → 0.4 → 0.5+0.5.5 → 0.6abc → 0.2 → 0.7+0.8+0.9).
- `.planning/research/PITFALLS.md` — M-series metrics-vs-targets (M1–M6 — the guardrail motivation); P0.1 macOS fork four failure modes; P0.2 numpy<2 transitive breakage; P0.3 rio_cogeo COG-validity bug; P0.4 retry-policy-per-source; P2.1/P2.2/P2.3 stable-terrain methodology (shared module consumed by Phase 3/4).
- `.planning/research/FEATURES.md` — table-stakes / differentiators / anti-features list (15 anti-features total).

### v1.0 precedent files to match (existing conventions)

- `src/subsideo/_metadata.py` — precedent for top-level private module with leading underscore (90 lines). `_cog.py` and `_mp.py` follow this pattern.
- `src/subsideo/products/types.py` — precedent for `@dataclass` plain result containers. New `validation/results.py` extends this pattern.
- `src/subsideo/config.py` — pydantic-settings precedent. `matrix_schema.py` uses Pydantic v2 models in the same style.
- `src/subsideo/validation/compare_*.py` — 5 files that `criteria.py` + `results.py` migration touches.
- `src/subsideo/products/cslc.py` §§156-227, 296, 392-407 — the 4 monkey-patches to remove per ENV-02 (`_patch_compass_burst_db_none_guard`, `_patch_s1reader_numpy2_compat`, `_patch_burst_az_carrier_poly` plus one more).
- `run_eval.py` — simplest eval script (114 lines), pilot for harness migration per research recommendation.

### v1.0 CONCLUSIONS (context for why the guardrails exist)

- `CONCLUSIONS_N_AM.md` §Bug 4 — the macOS multiprocessing spawn root cause that ENV-04 `_mp.py` addresses.
- `CONCLUSIONS_CSLC_N_AM.md` §5 — the cross-version phase impossibility (consolidated into `docs/validation_methodology.md` in Phase 3, not Phase 1).
- `CONCLUSIONS_DIST_EU.md` §Chained `prior_dist_s1_product` — the dist-s1 macOS hang motivating the full `_mp` bundle beyond BOOTSTRAP's simple `set_start_method('fork')`.
- `CONCLUSIONS_DSWX.md` §3 — DSWE F1 ≈ 0.92 architectural ceiling cited in `criteria.py` rationale for DSWx F1_MIN.

### External library refs (read as-needed during plan-phase)

- `opera_utils.burst_frame_db.get_burst_id_geojson()` — authoritative burst-bounds source for `bounds_for_burst()` (collapses BOOTSTRAP §0.5 and §0.6 into one function per ARCHITECTURE §1).
- `rio_cogeo` 6.0.0 API — `cogeo.cog_validate`, `cogeo.cog_translate`, `profiles.cog_profiles`. Research STACK §3 pins to 6.0.0 specifically (7.x drops Python 3.10).
- `py-spy` (>= 0.3) — stack dump on watchdog abort. Pip-installable, pure binary, no native build.
- `mambaorg/micromamba` Docker image — base for Dockerfile. Docs at <https://mamba.readthedocs.io/en/latest/user_guide/micromamba-docker.html>.

### No external ADR/spec docs for Phase 1

Phase 1 is codebase-internal infrastructure; no external spec consumed. All canonical refs above are either internal planning docs or upstream library docs.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`src/subsideo/_metadata.py` (90 lines)** — exact precedent for top-level leading-underscore private module. `_cog.py` and `_mp.py` follow its file layout and docstring conventions.
- **`src/subsideo/products/types.py` (163 lines)** — plain `@dataclass` result containers pattern. `validation/results.py` uses the same `from __future__ import annotations` + `@dataclass` shape. The 5 per-product `*ValidationResult` classes (RTCValidationResult, CSLCValidationResult, DISPValidationResult, DISTValidationResult, DSWxValidationResult) get replaced in the big-bang migration (D-09).
- **`src/subsideo/validation/compare_*.py` (5 files, 1141 LOC total)** — existing comparison logic stays functionally intact; only return signatures change to the nested composite shape. `compare_dist.py` (224 LOC) and `compare_disp.py` (363 LOC) already have implicit product-quality vs reference-agreement separation in their per-pixel logic — the refactor makes it structural.
- **`src/subsideo/validation/metrics.py` (124 lines)** — f1, precision, recall, accuracy, correlation, RMSE computations. Unchanged; consumed unchanged by migrated `compare_*.py`.
- **`src/subsideo/config.py`** — `pydantic-settings` BaseSettings precedent. `matrix_schema.py` Pydantic models follow the same v2 style.
- **`pyproject.toml` optional extras (`validation`, `viz`, `dev`)** — already defines the pip-layer split conda-env.yml will import via `pip: -e .[validation,viz]`.
- **7 existing `run_eval_*.py` scripts (3,176 LOC total)** — `run_eval.py` (114 LOC) is the pilot harness-migration target per D-10 Claude's Discretion note. The others range from 196 LOC (`run_eval_cslc.py`) to 844 LOC (`run_eval_disp.py` — mostly plumbing that collapses to harness calls).
- **`tests/unit/` (23 test modules)** — existing fixtures (`conftest.py`: `po_valley_bbox`, `tmp_cache_dir`) stay. The 5 `test_compare_*.py` modules are the primary migration surface for D-09.

### Established Patterns

- **Two-layer install (conda-forge heavies + pip pure-Python)** — v1.0 decision carried forward (PROJECT.md Key Decisions). D-15 `conda-env.yml` preserves it.
- **Lazy imports for conda-forge deps** — `products/*.py` import isce3/dolphin/compass inside function bodies, not at module top. This keeps `pip install subsideo` + pure-Python usage functional even without the conda stack. `_mp.py` and `_cog.py` must preserve this — only import conda-forge-only libs where needed, not unconditionally at module top.
- **Eval-script → product entry point pattern** — each `run_eval_*.py` calls `products.<product>.run_<product>()` which is the supervisor-wrapped entry point. `configure_multiprocessing()` is invoked at the **top of the product entry point** (per ENV-04), not inside the eval script, so `pip install subsideo` consumers also get the fork fix.
- **Hatchling + hatch-vcs build backend** — no change. Phase 1 does not touch pyproject build metadata.
- **ruff + mypy configs (pyproject.toml `[tool.ruff]`, `[tool.mypy]`)** — unchanged. Phase 1 new modules must conform to `line-length=100`, `target-version=py310`, strict mypy. Test that the 4 patch-removals (D-09 cslc.py edits) don't re-introduce ruff warnings.
- **Loguru for logging** — all new modules use `from loguru import logger` per v1.0 convention (PROJECT.md Key Decisions).

### Integration Points

- **`src/subsideo/products/{rtc,cslc,disp,dist,dswx}.py` top of `run_*()` entry point** — single new line: `_mp.configure_multiprocessing()` (ENV-04). Replaces the ad-hoc `if __name__ == "__main__":` guard pattern in eval scripts.
- **`src/subsideo/products/{rtc,dist,dswx}.py` + `_metadata.py`** — replace inline `from rio_cogeo import cog_validate` and `try/except ImportError` blocks with `from subsideo._cog import cog_validate, cog_translate, ensure_valid_cog` (ENV-03). 14 import sites identified by `rg "from rio_cogeo"`.
- **`src/subsideo/products/cslc.py`** — delete 4 `_patch_*` functions (lines 156-227, 226, 296, 392-407 approx) and their call sites (ENV-02). Adjusts the `test_cslc_pipeline.py` unit tests for the removal.
- **All 7 `run_eval_*.py` scripts** — 5 shared helpers consumed from `subsideo.validation.harness`; all hand-coded `bounds = [...]` replaced with `harness.bounds_for_burst(burst_id, buffer_deg=0.2)` (ENV-08). Diff between equivalent scripts (e.g. `run_eval_disp_egms.py` vs `run_eval_disp.py`) contains only reference-data differences (ENV-07 acceptance check).
- **New `Makefile` at repo root** — targets invoke `python -m subsideo.validation.supervisor run_eval_<product>_<region>.py`. Cache-dir cleanup targets alongside. `results-matrix` target calls `python -m subsideo.validation.matrix_writer --out results/matrix.md`.
- **New `results/matrix_manifest.yml`** — hand-edited list of 10 cells (5 products × 2 regions) with `eval_script`, `cache_dir`, `conclusions_doc`, `metrics_file` per cell. Committed; machine-readable.
- **New `Dockerfile` + `Apptainer.def` at repo root** — multi-stage build from `mambaorg/micromamba:latest`. Both committed per D-17.
- **New lockfiles at repo root: `env.lockfile.linux-64.txt`, `env.lockfile.osx-arm64.txt`** — committed, regenerated on every `conda-env.yml` edit per D-16.

</code_context>

<specifics>
## Specific Ideas

- **Pilot for harness migration is `run_eval.py`** (smallest, RTC N.Am., already PASS in v1.0) per research recommendation ARCHITECTURE §Build Order. Land harness.py + run_eval.py migration in one commit as proof-out, then batch-migrate the remaining 6 eval scripts.
- **py-spy dump on watchdog abort** is explicitly flagged as a differentiator in research FEATURES §Differentiators — user selected this explicitly over "SIGTERM→SIGKILL only" (D-13).
- **Both platforms validated in Phase 1** (not just M3 Max as initially implied by platform-matrix answer) — user explicitly clarified Phase 1 closes with Docker-on-M3-Max running `docker build + docker run pytest + one small eval`, catching Linux env-create failures before they become Phase 7 surprises (D-18).
- **No CODEOWNERS / pre-commit hook for `criteria.py`** — user picked `frozen=True` + matrix-echo over heavier enforcement. Keeps the solo-dev workflow light; the matrix-echo mechanism (criterion threshold printed alongside measured value in matrix.md) is the drift-detection primitive.
- **Phase 5 EFFIS and DSWx recalibration threshold additions explicitly deferred to Phase 5.** Phase 1 does not pre-populate placeholder entries in criteria.py for these — adding is additive.
- **`py-spy` becomes a new Phase 1 dependency** — added to conda-env.yml `pip:` layer (alongside `-e .[validation,viz]`). Not currently in pyproject.toml — plan-phase needs to decide whether to add as a `dev` extra, a new `ops` extra, or a direct `conda-env.yml` pip line.

</specifics>

<deferred>
## Deferred Ideas

- **Per-burst Makefile target granularity** (e.g. `eval-rtc-eu-t117_249422_iw2`) — not needed at v1.1 scale (15 eval scripts, 10 matrix cells). Defer until Phase 2 burst probing surfaces a concrete need (user decided "I'm ready for CONTEXT.md" without pursuing Makefile depth).
- **`make -j` parallelism** — Phase 7 perf concern; Phase 1 Makefile stays serial. Linux TrueNAS cold-env audit (12h budget) is serial-adequate; parallelism discussion belongs in Phase 7 if the 12h bound is at risk.
- **Adaptive wall-time from prior run history** — deferred; research said "caller-supplied per-script constant" is adequate at v1.1 scale. Revisit if actual wall times diverge significantly from hardcoded `EXPECTED_WALL_S`.
- **`conda-lock` pinning** — explicitly rejected by research for v1.1 (deferred to v2+). `env.lockfile.<platform>.txt` via `micromamba list --explicit --md5` is sufficient.
- **Matrix-writer drift unit test** (asserting specific hash of criteria.py) — user rejected in D-03 in favour of runtime frozen + PR review + matrix-echo. If drift incidents emerge, this is the fallback to reconsider.
- **Per-product test subdirectories** (e.g. `tests/product_quality/cslc/`) — flat structure chosen at v1.1 scale per Claude's Discretion. Revisit if tests-split tree grows past ~30 files per dir.
- **`.devcontainer/devcontainer.json` for VS Code** — nice-to-have; could ship now or Phase 7 or v2. Not blocking; not discussed.
- **CUDA layer in Dockerfile** — dist-s1's GPU path is M3-incompatible; research-rejected for Phase 1. CPU-only Dockerfile ships in Phase 1.
- **Per-source `tenacity` retry library adoption inside harness** — STACK §2 lists `tenacity==9.1.4` as a v1.1 add; details of whether `download_reference_with_retry` uses tenacity or rolls its own is Claude's Discretion at plan-phase.
- **Matrix writer's CALIBRATING-cell visual distinction rendering** — user explicitly excluded this from `criteria.py` scope; it's a `matrix_writer.py` concern at plan-phase.

### Reviewed Todos (not folded)

No pending todos matched Phase 1 (STATE.md shows "None yet (roadmap just created; awaiting `/gsd:plan-phase 1`)").

</deferred>

---

*Phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding*
*Context gathered: 2026-04-21*
