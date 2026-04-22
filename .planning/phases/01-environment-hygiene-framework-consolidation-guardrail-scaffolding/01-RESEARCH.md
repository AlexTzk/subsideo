# Phase 1: Environment Hygiene, Framework Consolidation & Guardrail Scaffolding - Research

**Researched:** 2026-04-21
**Domain:** Validation-hardening foundation for subsideo v1.1 (Python library; conda-forge + pip two-layer install; SAR/InSAR eval framework)
**Confidence:** HIGH (all 17 decisions locked in CONTEXT.md; every file path / API shape / version pin below was verified against the live codebase, `opera_utils` runtime, `rio_cogeo` source, PyPI, and conda-forge metadata on 2026-04-21)

## Summary

Phase 1 is **codebase-internal infrastructure**. Zero new scientific logic — every deliverable is either (a) a refactor of existing code into a new module, (b) a new constants / dataclass / helper module that downstream phases consume, or (c) environment / reproducibility scaffolding (conda-env.yml, Dockerfile, Makefile, lockfiles). The 19 decisions in CONTEXT.md (D-01..D-19) exhaustively specify WHAT; this RESEARCH covers HOW — exact file paths, line ranges, import sites, API signatures, command invocations, and edge cases.

Three deliverables are **load-bearing for every downstream phase**:
1. `validation/harness.py` with 5 public helpers (consumed by 7 existing + ~6 new eval scripts).
2. `validation/criteria.py` + `validation/results.py` + split per-product ValidationResult types (consumed by all 5 compare_*.py files, the matrix writer, and the test-dir split).
3. `_mp.py` + `validation/supervisor.py` (consumed by every `products/*.run_*()` entry point via `configure_multiprocessing()`, and by the Makefile via subprocess wrap).

**Primary recommendation:** Follow the ROADMAP internal ordering verbatim (0.1 numpy → 0.3 _cog → 0.4 _mp → 0.5+0.5.5 harness+stable_terrain+selfconsistency → 0.6abc criteria+results+test-split → 0.2 tophu pin → 0.7+0.8+0.9 Makefile+manifest+env). Land `validation/harness.py` with `run_eval.py` (the 114-LOC pilot) migration in the same commit as proof-out; batch-migrate the other 6 eval scripts in a second commit. The big-bang migration of D-09 (all 5 ValidationResult types + all 5 compare_*.py returns + all 5 test_compare_*.py files) MUST be one atomic PR — fail-fast is the explicit design.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**`criteria.py` API shape & immutability:**
- **D-01:** `Criterion` is `@dataclass(frozen=True)` with fields: `name: str`, `threshold: float`, `comparator: Literal['>', '>=', '<', '<=']`, `type: Literal['BINDING', 'CALIBRATING']`, `binding_after_milestone: str | None` (None for BINDING), `rationale: str`.
- **D-02:** Flat `CRITERIA: dict[str, Criterion]` registry keyed by canonical ID (`'rtc.rmse_db_max'`, `'cslc.amplitude_r_min'`, `'cslc.selfconsistency.coherence_min'`, etc.) + typed accessor functions (`def rtc_rmse_db_max() -> Criterion: return CRITERIA['rtc.rmse_db_max']`).
- **D-03:** Immutability = runtime `frozen=True` + matrix-writer echo drift visibility. **No** CI hash-check, **no** CODEOWNERS, **no** pre-commit hook. PR review policy: edit cites ADR or upstream spec.
- **D-04:** Phase 1 populates: v1.0 BINDING (RTC 0.5/0.99, CSLC amp 0.6/4, DISP 0.92/3, DIST 0.80/0.85, DSWx 0.90) + Phase-3/4-needed CALIBRATING (cslc.selfconsistency.coherence_min=0.7, residual_mm_yr_max=5; disp.selfconsistency.* mirror, binding_after_milestone='v1.2').
- **D-05:** Phase 5 deliverables (EFFIS precision/recall, DSWx recalibration threshold reaffirmation) DEFERRED to Phase 5 — Phase 1 does NOT pre-populate placeholders.

**Split ValidationResult:**
- **D-06:** Nested composite: `@dataclass class <Product>ValidationResult: product_quality: ProductQualityResult; reference_agreement: ReferenceAgreementResult`. No top-level `.passed`.
- **D-07:** New `src/subsideo/validation/results.py` contains generic `ProductQualityResult` + `ReferenceAgreementResult`. Per-product types stay in `src/subsideo/products/types.py`. Import direction: `products/types.py → validation/results.py` allowed (one-way data-only leaf).
- **D-08:** Named fields + criterion IDs, no stored bools. Each result stores `measurements: dict[str, float]` + `criterion_ids: list[str]`. Pass/fail computed at read time via `evaluate(result, criteria) -> dict[criterion_id, bool]`.
- **D-09:** **Big-bang migration in Phase 1.** Single commit/PR replaces all 5 per-product ValidationResult types + all 5 compare_*.py return signatures + all affected tests. Fail-fast — no `@property` back-compat aliases.

**Watchdog mechanics:**
- **D-10:** Throughput heuristic = output-directory mtime staleness. Poll cache_dir every 30s; if nothing changed for `grace_window=120s` AND wall time > `2 × EXPECTED_WALL_S` → abort.
- **D-11:** Wall-time source = caller-supplied per-script constant. Each `run_eval_*.py` declares module-level `EXPECTED_WALL_S = <seconds>`. Supervisor reads via subprocess env or AST parse.
- **D-12:** Scope = per-script subprocess wrap via Makefile supervisor. Makefile runs `python -m subsideo.validation.supervisor run_eval_dist.py`. Supervisor forks script as subprocess; sends SIGTERM then SIGKILL to process group via `os.killpg`.
- **D-13:** Abort diagnostics = py-spy stack dump → `<cache_dir>/watchdog-stacks.txt` → SIGTERM → 30s grace → SIGKILL → exit 124. py-spy added to conda-env.yml.
- **D-14:** `_mp.configure_multiprocessing()` is SEPARATE from supervisor. It sets `set_start_method('fork')` on macOS (forkserver fallback Python ≥3.14) + `MPLBACKEND=Agg` + `RLIMIT_NOFILE` (4096, hard) + closes module-global `requests.Session` pre-fork.

**Env & reproducibility:**
- **D-15:** Two-layer `conda-env.yml`. Top-level `dependencies:` has conda-forge binaries only (python=3.11, numpy<2.0, isce3=0.25.10, gdal>=3.8, dolphin=0.42.5, tophu=0.2.1, snaphu-py=0.4.1, compass=0.5.6, opera-rtc=1.0.4, dist-s1=2.0.14, s1reader=0.2.5, mintpy=1.6.3, rio-cogeo=6.0.0, pyaps3>=0.3.6, cdsapi, py-spy). Trailing `pip:` installs `- -e .[validation,viz]`.
- **D-16:** Per-platform explicit lockfiles. Two files: `env.lockfile.linux-64.txt` (via `micromamba list --explicit --md5` inside Linux Docker) + `env.lockfile.osx-arm64.txt` (same, from M3 Max native). Regenerated on every `conda-env.yml` edit.
- **D-17:** Dockerfile primary from `mambaorg/micromamba:latest`, multi-stage (heavy layer cached; thin runtime copies env + source). Apptainer.def derives from Docker via `docker-daemon://subsideo:dev`. CPU-only — no CUDA.
- **D-18:** Phase 1 validates BOTH platforms — osx-arm64 M3 Max dev run + linux-64 Docker on M3 Max (`docker build . -t subsideo:dev && docker run --rm subsideo:dev micromamba run -n subsideo pytest tests/unit tests/integration` + one small eval cold). Phase 7 TrueNAS cold-env audit stays separate.
- **D-19:** Windows native + osx-x86_64 explicitly out of scope.

### Claude's Discretion

- **Tests split migration scope:** tests/unit stays for pure-unit. Create tests/product_quality/ (asserts values — includes migrated self-consistency smoke test fixtures, DSWx F1 gate tests) + tests/reference_agreement/ (asserts plumbing only — no threshold assertions). Content-inspect each tests/unit/test_compare_*.py. Flat under each — no per-product subdirs. Add `@pytest.mark.reference_agreement` marker + a CI-adjacent linter rule that rejects `assert` statements referencing `criteria.py` thresholds in `tests/reference_agreement/`.
- **Makefile orchestration depth:** Minimum targets = `eval-all`, `eval-nam`, `eval-eu`, `eval-{product}-{region}`, `results-matrix`, `clean-cache`. Per-burst deferred. Makefile ~20 lines — calls `python -m subsideo.validation.supervisor`. Serial by default; `make -j` opt-in is Phase 7.
- **metrics.json + meta.json schema split:** Two sidecars per eval. `meta.json` = provenance (schema_version, git_sha, git_dirty, run_started_iso, run_duration_s, python_version, platform, input_hashes). `metrics.json` = scientific (schema_version, product_quality: ProductQualityResult serialised, reference_agreement: ReferenceAgreementResult serialised, criterion_ids_applied, runtime_conda_list_hash). Both defined by Pydantic v2 models in `validation/matrix_schema.py`.
- **`_cog.py` API:** `cog_validate(path) -> tuple[bool, list[str], list[str]]` (is_valid, errors, warnings — **warnings surfaced, not swallowed**); `cog_translate(src, dst, profile, **kwargs)`; `RIO_COGEO_VERSION: tuple[int, int, int]`; `ensure_valid_cog(path)` that re-translates in place if IFD-offset warning present.
- **`harness.py` per-source retry policy:** Dict-keyed constants — `RETRY_POLICY = {'CDSE': {...}, 'EARTHDATA': {...}, 'CLOUDFRONT': {...refresh_url_on: [403]...}}`. `download_reference_with_retry` refuses to proceed without an explicit source key.
- **Pilot eval for harness migration:** Land `validation/harness.py` + `run_eval.py` migration in the same commit. Batch-migrate the other 6 eval scripts in a single follow-up commit. ENV-07 diff check runs at end of second commit.

### Deferred Ideas (OUT OF SCOPE)

- Per-burst Makefile target granularity (e.g. `eval-rtc-eu-t117_249422_iw2`)
- `make -j` parallelism — Phase 7 perf concern
- Adaptive wall-time from prior run history — caller-supplied constant adequate at v1.1 scale
- `conda-lock` pinning — explicitly rejected for v1.1 (deferred to v2+); `env.lockfile.<platform>.txt` via `micromamba list --explicit --md5` sufficient
- Matrix-writer drift unit test (hash of criteria.py) — rejected in D-03
- Per-product test subdirectories (tests/product_quality/cslc/)
- .devcontainer/devcontainer.json
- CUDA layer in Dockerfile
- Per-source `tenacity` inside harness — Claude's Discretion at plan-phase
- Matrix-writer CALIBRATING-cell visual distinction — `matrix_writer.py` concern, not `criteria.py`

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description (from REQUIREMENTS.md) | Research Support |
|----|------------------------------------|------------------|
| ENV-01 | Fresh `micromamba env create -f conda-env.yml` runs with zero post-install pip; tophu via conda-forge; numpy<2.0 | D-15 two-layer env.yml; §A (Environment) — exact YAML contents + verified 2026-04-21 versions |
| ENV-02 | No runtime monkey-patches in src/subsideo/products/*.py (4 patches removed from cslc.py); unit tests pass under numpy<2 | §B CSLC Patch Removal — 4 exact locations + impact on test_cslc_pipeline.py lines 127-129 |
| ENV-03 | All rio_cogeo imports route through src/subsideo/_cog.py (rio-cogeo==6.0.0 pin) | §C `_cog.py` API + 10 import-site rewrite list |
| ENV-04 | `_mp.configure_multiprocessing()` invoked at top of every `run_*()` product entry | §D `_mp.py` full bundle + 5 product entry-point call sites |
| ENV-05 | Subprocess watchdog aborts after 2× expected wall at zero throughput; os.killpg cleanup; 3 consecutive fresh dist runs succeed on macOS | §E `validation/supervisor.py` — mtime polling, py-spy dump, SIGTERM→SIGKILL sequence |
| ENV-06 | `validation/harness.py` exposes select_opera_frame_by_utc_hour, download_reference_with_retry (Earthdata/CDSE/CloudFront), ensure_resume_safe, credential_preflight, bounds_for_burst | §F `harness.py` public API — 5 signatures + per-source retry policy dict |
| ENV-07 | All 7 eval scripts refactored to consume harness; diffs contain only reference-data differences, not plumbing | §F.pilot — `run_eval.py` migration + batch migration + diff acceptance check |
| ENV-08 | No hand-coded geographic bounds in any eval script — all bounds from `harness.bounds_for_burst()` | §F — `bounds_for_burst(burst_id, buffer_deg=0.2)` wraps `opera_utils.burst_frame_db.get_burst_id_geojson`; 7 existing `bounds=[...]` hardcoded sites to replace |
| ENV-09 | User can invoke `make eval-all/eval-nam/eval-eu/eval-{product}-{region}`; cell failure does not block matrix; meta.json per-cell with git SHA + input content hashes | §G Makefile + §H matrix_manifest.yml + §I metrics.json/meta.json schemas |
| ENV-10 | Committed `env.lockfile.txt` + reproducibility recipe (Dockerfile or Apptainer) | §A per-platform lockfiles + §J Dockerfile + Apptainer.def |
| GATE-01 | `validation/criteria.py` exists as immutable module with CALIBRATING/BINDING types + `binding_after_milestone` on every calibrating gate | §K `criteria.py` schema + 9 populated entries (5 v1.0 BINDING + 4 CALIBRATING) |
| GATE-02 | Validation result dataclasses split into ProductQualityResult and ReferenceAgreementResult; no top-level `.passed` | §L `validation/results.py` + §M big-bang migration across 5 compare_*.py + 5 test files + 5 products/types.py classes |
| GATE-03 | `results/matrix.md` reports product-quality and reference-agreement as two distinct columns; CALIBRATING cells visually distinguishable | §H matrix_writer.py + §I metrics.json schema (composite result serialisation) |
| GATE-04 | Tests split into tests/product_quality/ (asserts measured values) + tests/reference_agreement/ (asserts plumbing only — never thresholds) | §N tests-split migration — per-file classification + linter rule for threshold-free reference_agreement tree |
| GATE-05 | Every new product-quality gate in v1.1 (CSLC self-consistency, DISP self-consistency) ships CALIBRATING; requires ≥3 measured points before BINDING promotion | §K criteria.py populates both mirrored pairs with binding_after_milestone='v1.2' |
| CSLC-01 | `validation/stable_terrain.py` builds stable-terrain mask from WorldCover class 60 + slope <10° + coastline buffer + water-body exclusion | §O `stable_terrain.py` public API — coast buffer 5km, water buffer 500m, optional exclude_mask |
| CSLC-02 | `validation/selfconsistency.py` computes sequential 12-day coherence stats (mean, median, persistently-coherent fraction) + residual mean velocity over stable mask | §P `selfconsistency.py` public API — per PITFALLS P2.1/P2.2/P2.3 (median + p25 + p75 + persistently-coherent fraction, reference-frame aligned residual) |

</phase_requirements>

## Architectural Responsibility Map

This phase is a pure-Python library layer (no multi-tier application). The tier analysis maps Phase 1 capabilities to subsideo's internal subsystems, not external tiers.

| Capability | Primary Subsystem | Secondary Subsystem | Rationale |
|------------|-------------------|---------------------|-----------|
| Multiprocessing start-method configuration | `src/subsideo/_mp.py` (top-level private) | products/*.py entry points | Cross-cutting interpreter-level state; precedent = `_metadata.py`. Not `utils/` because utils is stateless. |
| COG validation / translation shim | `src/subsideo/_cog.py` (top-level private) | products/{rtc,dswx,dist}.py + `_metadata.py` (consumers) | Version-drift wrapper with side effects (re-translate on warning); top-level private per `_metadata.py` precedent. |
| Subprocess watchdog + py-spy dump | `src/subsideo/validation/supervisor.py` | Makefile (caller) | Validation-infrastructure — not product pipeline. Invoked as `python -m subsideo.validation.supervisor`. |
| Validation framework plumbing (retries, frame selection, bounds) | `src/subsideo/validation/harness.py` | 7+6 eval scripts at repo root | Validation-layer concern; peer to compare_*.py. Single file (~300-400 LOC); split threshold ~600 LOC. |
| Stable-terrain mask construction | `src/subsideo/validation/stable_terrain.py` | Phase 3 compare_cslc / Phase 4 compare_disp | Shared module consumed by self-consistency gates across products. |
| Sequential-IFG coherence + residual velocity stats | `src/subsideo/validation/selfconsistency.py` | Phase 3 CSLC eval / Phase 4 DISP eval | Shared computation; consumer of `stable_terrain.py` output. |
| Immutable criterion registry | `src/subsideo/validation/criteria.py` | 5 compare_*.py; matrix_writer.py; tests/product_quality | Data-only module (no I/O, no logic). Frozen dataclass + dict registry. |
| Generic pass/fail result types | `src/subsideo/validation/results.py` | products/types.py per-product ValidationResult classes | Leaf data-only module (no `products/*` or `validation/compare_*` imports). Only direction allowed is `products/types → validation/results`. |
| Pydantic schemas for metrics/meta sidecars | `src/subsideo/validation/matrix_schema.py` | matrix_writer.py + every eval script (producer) | Contract between eval-script writers and matrix reader. |
| Matrix aggregation (markdown generation) | `src/subsideo/validation/matrix_writer.py` | Makefile `results-matrix` target | Reads manifest + per-eval sidecars; never globs CONCLUSIONS. |
| Makefile orchestration | `Makefile` at repo root | `python -m subsideo.validation.supervisor` (per target) | Thin (~20 lines); calls supervisor per eval cell. |
| Per-cell results manifest | `results/matrix_manifest.yml` at repo root | matrix_writer.py (reader) | Hand-edited; 10 cells (5 products × 2 regions). |
| Env reproducibility | `conda-env.yml` + `env.lockfile.{linux-64,osx-arm64}.txt` + `Dockerfile` + `Apptainer.def` at repo root | Makefile + Phase 7 closure test | All at repo root — consistent with `pyproject.toml`, `.env`, CONCLUSIONS_*.md placements. |

**Forbidden import directions (per ARCHITECTURE §Failure-Mode Boundaries):**
- `products/* → validation/compare_*` — cycle (compare_* imports products/types).
- `products/types → validation/results` — **ALLOWED** (data-only leaf, one-way, the basis of D-07).
- `_cog / _mp → any subsideo.*` — leaf modules; must remain leaves.
- `validation/harness → products/*` — cycle risk (eval scripts import both).
- `utils/* → products/* or validation/*` — layering inversion.

## Standard Stack

### Core (conda-forge only — NEVER pip install)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python | 3.11 | Runtime | Matches v1.0; isce3 0.25.10 conda-forge build targets 3.10–3.11 [VERIFIED: introspection of /Users/alex/.local/share/mamba/envs/subsideo — currently on 3.11] |
| numpy | <2.0 (pinned) | Numerical core | compass 0.5.6 / s1reader 0.2.5 / isce3 0.25.10 pybind11 lack numpy-2 compat; removes the 4 monkey-patches in cslc.py [VERIFIED: current env numpy 2.4.4 causes the patch-requiring path; STACK §1 verified 2026-04-20] |
| isce3 | 0.25.10 | SAR core | v1.0 baseline, unchanged [CITED: STACK §9.4] |
| gdal | >=3.8 | Raster I/O | v1.0 baseline [CITED: STACK §Full conda-env.yml delta] |
| dolphin | 0.42.5 | InSAR phase linking | v1.0 baseline [CITED: STACK §9.4] |
| tophu | 0.2.1 | Multi-scale unwrapping | **Not on PyPI** — conda-forge only [VERIFIED: `curl api.anaconda.org/package/conda-forge/tophu` returns latest 0.2.1] |
| snaphu-py | 0.4.1 | SNAPHU unwrapping | v1.0 baseline [CITED: STACK §Full conda-env.yml delta] |
| compass | 0.5.6 | OPERA CSLC-S1 workflow | v1.0 baseline; no newer release [CITED: STACK §9.4] |
| opera-rtc | 1.0.4 | OPERA RTC-S1 workflow | v1.0 baseline |
| dist-s1 | 2.0.14 | OPERA DIST-S1 workflow | Bump from 2.0.13 [VERIFIED: `curl api.anaconda.org/package/conda-forge/dist-s1` latest 2.0.14 on conda-forge] |
| s1reader | 0.2.5 | Sentinel-1 SAFE burst reader | v1.0 baseline [CITED: STACK §9.4] |
| mintpy | 1.6.3 | Time-series analysis | v1.0 baseline |
| rio-cogeo | **==6.0.0** | COG validate/translate | 7.x drops Python 3.10 [VERIFIED: PyPI JSON 2026-04-21, latest 7.0.2, 6.0.0 the recommended pin] |
| pyaps3 | >=0.3.6 | ERA5 tropospheric correction | v1.0 baseline, 0.3.5 broken under new CDS API |
| cdsapi | — | ERA5 download | v1.0 baseline |
| py-spy | 0.4.1 | Watchdog stack dump | NEW in v1.1 Phase 1 [VERIFIED: conda-forge latest 0.4.1 = PyPI latest 0.4.1 as of 2026-04-21] |

### Pip layer (installed via conda-env.yml trailing `pip:` section as `-e .[validation,viz]`)

Already defined in `pyproject.toml` `[project.optional-dependencies]` — Phase 1 does NOT touch pyproject.toml except to consider whether to add py-spy. **Recommendation:** add py-spy to `conda-env.yml` pip: layer (outside pyproject.toml) because it's ops-tooling only needed when the watchdog aborts. A Phase 7 perf audit can decide whether to promote to a new `ops` extra in pyproject.toml.

**Version verification commands (run before writing conda-env.yml):**
```bash
# Versions as of 2026-04-21, already verified for this research:
curl -s "https://api.anaconda.org/package/conda-forge/tophu" | jq -r '.latest_version'          # 0.2.1
curl -s "https://api.anaconda.org/package/conda-forge/dist-s1" | jq -r '.latest_version'        # 2.0.14
curl -s "https://api.anaconda.org/package/conda-forge/py-spy" | jq -r '.latest_version'         # 0.4.1
curl -s "https://pypi.org/pypi/rio-cogeo/json" | jq -r '.info.version'                          # 7.0.2 (do NOT use; pin 6.0.0)
curl -s "https://pypi.org/pypi/tenacity/json" | jq -r '.info.version'                           # 9.1.4
curl -s "https://pypi.org/pypi/owslib/json" | jq -r '.info.version'                             # 0.35.0
```

### Alternatives Considered (all REJECTED for v1.1 — explicit for the planner)

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| conda-forge tophu | `pip install tophu` | Doesn't exist on PyPI (404). Research SUMMARY / STACK §2 correction |
| rio-cogeo 6.0.0 | rio-cogeo 7.x | 7.x drops Python 3.10, subsideo pins >=3.10 [STACK §3] |
| `mambaorg/micromamba:latest` | `ubuntu:22.04 + apt install micromamba` | mambaorg image is order-of-magnitude smaller; pre-configured user + entrypoint |
| GNU make | `just`, `taskfile.dev` | Breaks closure test (`fresh clone → micromamba env create → make eval-all` would need extra install) |
| stdlib `multiprocessing` + os.killpg | `pebble.ProcessPool` | Overreach; one call site doesn't justify dep [STACK §8] |
| `os.killpg` for grandchildren | `subprocess.run(timeout=…)` or thread-level watchdog | Grandchildren (isce3/dist-s1) orphaned without process-group signal [PITFALLS P0.1] |
| py-spy dump before SIGKILL | SIGTERM→SIGKILL only | User selected explicitly (D-13, FEATURES differentiator) |
| Immutable `frozen=True` only | CI hash-check + CODEOWNERS + pre-commit hook | User rejected heavier enforcement (D-03) — solo-dev workflow |
| `meta.json` + `metrics.json` sidecars per cell | Glob-parse CONCLUSIONS markdown | Fragile; breaks on wording changes [PITFALLS R5] |

## Architecture Patterns

### System Architecture Diagram

```
             ┌────────────────────────────────────────────┐
             │   Makefile (repo root, ~20 lines)          │
             │   make eval-all / eval-nam / eval-eu       │
             │   make eval-{product}-{region}             │
             │   make results-matrix / clean-cache        │
             └────────────────────┬───────────────────────┘
                                  │ invokes via subprocess
                                  ▼
      ┌─────────────────────────────────────────────────────────┐
      │   python -m subsideo.validation.supervisor <script.py>   │
      │   ──────────────────────────────────────────────────    │
      │   Reads EXPECTED_WALL_S from script env / AST.          │
      │   Forks subprocess; sets up new process group.          │
      │   Polls <cache_dir> mtime every 30s.                    │
      │   grace=120s no-change AND wall > 2×EXPECTED_WALL_S →    │
      │     py-spy dump → watchdog-stacks.txt →                 │
      │     os.killpg(SIGTERM) → 30s grace →                    │
      │     os.killpg(SIGKILL) → exit 124.                      │
      │   Clean exit → pass through child exit code.            │
      └────────────────────────────┬─────────────────────────────┘
                                   │ forks subprocess
                                   ▼
      ┌─────────────────────────────────────────────────────────┐
      │   run_eval_*.py (7 existing + harness-migrated)          │
      │   Each: imports from subsideo.validation.harness:        │
      │   - credential_preflight()                               │
      │   - bounds_for_burst(burst_id, buffer_deg=0.2)           │
      │   - select_opera_frame_by_utc_hour(...)                  │
      │   - download_reference_with_retry(...)                   │
      │   - ensure_resume_safe(...)                              │
      │                                                          │
      │   Calls into products.<product>.run_<product>():         │
      │     FIRST LINE: _mp.configure_multiprocessing()          │
      │       → set_start_method('fork'), force=True (macOS)     │
      │       → MPLBACKEND=Agg, RLIMIT_NOFILE=(4096,hard)        │
      │       → close any module-global requests.Session         │
      │       → forkserver fallback on Python ≥3.14              │
      │                                                          │
      │   On completion: writes                                  │
      │     <cache_dir>/meta.json (provenance, input hashes)     │
      │     <cache_dir>/metrics.json (ProductQualityResult +     │
      │       ReferenceAgreementResult serialised via            │
      │       validation/matrix_schema.py Pydantic v2 models)    │
      └────────────────────────────┬─────────────────────────────┘
                                   │ on make results-matrix
                                   ▼
      ┌─────────────────────────────────────────────────────────┐
      │   python -m subsideo.validation.matrix_writer            │
      │     --out results/matrix.md                              │
      │                                                          │
      │   Reads: results/matrix_manifest.yml (10 cells)          │
      │   Per cell: loads <cache_dir>/{meta,metrics}.json        │
      │   Per measured value: echoes CRITERIA[criterion_id]      │
      │     threshold alongside — drift visibility (D-03)        │
      │   Writes two-column table: Product-quality │ Reference-   │
      │     agreement, with CALIBRATING cells visually distinct  │
      └──────────────────────────────────────────────────────────┘

      ┌─────────────────────────────────────────────────────────┐
      │   Cross-cutting leaf modules (imported by products/*)    │
      │                                                          │
      │   _cog.py     — rio-cogeo==6.0.0 re-exports:             │
      │     cog_validate(path) → (bool, errors, warnings)        │
      │     cog_translate(src, dst, profile, **kw)               │
      │     ensure_valid_cog(path) — re-translate on IFD warn    │
      │     RIO_COGEO_VERSION: tuple[int,int,int]                │
      │                                                          │
      │   _mp.py      — macOS fork bundle:                       │
      │     configure_multiprocessing() — idempotent              │
      │                                                          │
      │   validation/criteria.py — frozen-dataclass registry:    │
      │     CRITERIA: dict[str, Criterion]                       │
      │     Typed accessors: rtc_rmse_db_max(), etc.             │
      │                                                          │
      │   validation/results.py — generic result types:          │
      │     ProductQualityResult, ReferenceAgreementResult       │
      │     evaluate(result, criteria) → dict[id, bool]          │
      │                                                          │
      │   products/types.py — per-product composite types:       │
      │     RTCValidationResult composes both generics           │
      │                                                          │
      │   validation/stable_terrain.py — mask construction       │
      │   validation/selfconsistency.py — coherence + residual   │
      └──────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (delta against shipped v1.0 tree)

```
subsideo/
├── Makefile                           # NEW v1.1 Phase 1 §G
├── conda-env.yml                      # NEW v1.1 Phase 1 §A
├── env.lockfile.linux-64.txt          # NEW v1.1 Phase 1 §A
├── env.lockfile.osx-arm64.txt         # NEW v1.1 Phase 1 §A
├── Dockerfile                         # NEW v1.1 Phase 1 §J
├── Apptainer.def                      # NEW v1.1 Phase 1 §J
├── pyproject.toml                     # unchanged (or add py-spy optional)
├── results/
│   └── matrix_manifest.yml            # NEW v1.1 Phase 1 §H (10 cells hand-edited)
├── src/subsideo/
│   ├── _metadata.py                   # existing v1.0 (precedent for _cog, _mp)
│   ├── _cog.py                        # NEW v1.1 Phase 1 §C
│   ├── _mp.py                         # NEW v1.1 Phase 1 §D
│   ├── products/
│   │   ├── cslc.py                    # MODIFIED: -4 monkey-patches (§B), +_mp call
│   │   ├── rtc.py                     # MODIFIED: rio_cogeo → _cog, +_mp call
│   │   ├── dswx.py                    # MODIFIED: rio_cogeo → _cog, +_mp call
│   │   ├── dist.py                    # MODIFIED: rio_cogeo → _cog, +_mp call
│   │   ├── disp.py                    # MODIFIED: +_mp call
│   │   └── types.py                   # MODIFIED: 5 ValidationResult classes → composite (D-06)
│   └── validation/
│       ├── __init__.py                # MODIFIED: re-export harness public API
│       ├── harness.py                 # NEW v1.1 Phase 1 §F (5 helpers)
│       ├── supervisor.py              # NEW v1.1 Phase 1 §E (watchdog subprocess wrap)
│       ├── criteria.py                # NEW v1.1 Phase 1 §K
│       ├── results.py                 # NEW v1.1 Phase 1 §L
│       ├── stable_terrain.py          # NEW v1.1 Phase 1 §O (consumed by Phase 3/4)
│       ├── selfconsistency.py         # NEW v1.1 Phase 1 §P (consumed by Phase 3/4)
│       ├── matrix_schema.py           # NEW v1.1 Phase 1 §I
│       ├── matrix_writer.py           # NEW v1.1 Phase 1 §H
│       ├── compare_rtc.py             # MODIFIED: return signature (D-06/D-09)
│       ├── compare_cslc.py            # MODIFIED: return signature (D-06/D-09)
│       ├── compare_disp.py            # MODIFIED: return signature (D-06/D-09)
│       ├── compare_dist.py            # MODIFIED: return signature (D-06/D-09)
│       └── compare_dswx.py            # MODIFIED: return signature (D-06/D-09)
├── tests/
│   ├── conftest.py                    # MODIFIED: add shared fixtures
│   ├── unit/                          # existing — plumbing/helper tests stay
│   ├── product_quality/               # NEW v1.1 Phase 1 §N — asserts values
│   └── reference_agreement/           # NEW v1.1 Phase 1 §N — plumbing only
└── run_eval*.py                       # ALL 7 MODIFIED: import from harness (D-15, ENV-07)
```

### Pattern 1: Top-level leading-underscore private modules

**What:** Cross-cutting infrastructure that (a) wraps a third-party library version drift OR (b) mutates interpreter-global state OR (c) is imported by every product pipeline → `src/subsideo/_foo.py` with leading underscore.

**Precedent:** `src/subsideo/_metadata.py` (90 lines) — cross-cutting private helper for OPERA metadata injection. Source:
```python
# src/subsideo/_metadata.py:1-13
"""OPERA-compliant identification metadata injection for all product types.

Injects provenance, software version, and run parameters into both
GeoTIFF (via rasterio tags) and HDF5 (via /identification group attrs).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger
```

**Apply to:** `_cog.py` (§C), `_mp.py` (§D). Both follow the same docstring style, `from __future__ import annotations`, lazy imports for conda-forge-only libs.

### Pattern 2: Plain @dataclass result containers (no Pydantic for pure data)

**What:** Result types that are consumed internally (not validated user input) use `@dataclass` not Pydantic BaseModel.

**Precedent:** `src/subsideo/products/types.py` (163 lines) — 163 LOC of `@dataclass` classes. Source:
```python
# src/subsideo/products/types.py:1-12
"""Pipeline configuration, result, and validation result types.

Dataclasses (not Pydantic) -- these are plain result containers consumed
by pipeline orchestrators and validation comparison modules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
```

**Apply to:** `validation/results.py` (§L), `validation/criteria.py` (§K). Use `@dataclass(frozen=True)` for `Criterion` (D-01).

**Note:** `validation/matrix_schema.py` (§I) DOES use Pydantic v2 models because the metrics.json / meta.json sidecars are the contract between eval-script writers and the matrix reader — schema validation + JSON serialisation is the whole point. Follow `src/subsideo/config.py` style (pydantic-settings).

### Pattern 3: Lazy imports for conda-forge deps inside function bodies

**What:** `products/*.py` import isce3/dolphin/compass/rio_cogeo/rasterio INSIDE function bodies, NOT at module top. Keeps `pip install subsideo` + pure-Python usage functional even without the conda stack.

**Verified:**
```python
# src/subsideo/products/rtc.py:102-103 (inside function body)
    from rio_cogeo.cogeo import cog_translate
    from rio_cogeo.profiles import cog_profiles
# src/subsideo/products/rtc.py:138-139 (inside function body)
    import rasterio
    from rio_cogeo import cog_validate
```

**Apply to:** `_cog.py`, `_mp.py`. Only import `multiprocessing`, `platform`, `os`, `resource`, `signal` (stdlib) at module top. `rio_cogeo` imports inside function bodies. BUT wrap with a module-level `_RIO_COGEO_VERSION` probe that caches the version on first call so `RIO_COGEO_VERSION` constant is available.

### Pattern 4: Eval script → product entry-point pattern

**What:** Each `run_eval_*.py` calls `products.<product>.run_<product>()` as the subprocess-wrapped entry point. `configure_multiprocessing()` is invoked at the **top of the product entry point** (per ENV-04, D-14), NOT inside the eval script, so `pip install subsideo` consumers also get the fork fix.

### Anti-Patterns to Avoid (from CONTEXT.md Claude's Discretion + research)

| Anti-pattern | Why it's bad | Instead |
|--------------|--------------|---------|
| Conflating data-output shapes with threshold constants (e.g. CALIBRATING-cell rendering logic in criteria.py) | Violates SRP; criteria.py is data-only. | Keep matrix_writer.py visual distinction separate from criteria.py |
| CODEOWNERS/pre-commit hooks for criteria.py | REJECTED per D-03 — heavier than needed for solo-dev workflow. | Runtime `frozen=True` + matrix-echo drift visibility + PR review with ADR citation |
| `@property` back-compat aliases (e.g. `RTCValidationResult.rmse_db` that shims from `product_quality.measurements['rmse_db']`) | REJECTED per D-09 big-bang — fail-fast. | Single commit replaces all 5 types + all 5 compare_*.py + all 5 test_compare_*.py |
| Pre-populating Phase 5 placeholders in criteria.py | REJECTED per D-05 additive. | Phase 5 adds its own entries when it lands |
| `products/* → validation/compare_*` import | Cycle (compare_* imports products/types). | `products/types → validation/results` ONE-WAY allowed; harness never imports products. |
| Globbing CONCLUSIONS_*.md to parse metric numbers | Fragile; breaks on wording. | matrix_manifest.yml + metrics.json sidecars (machine-readable) |
| Moving eval scripts to `scripts/` or `evals/` | Breaks ~30+ CONCLUSIONS doc references. | Keep at repo root; Makefile target names abstract location. Threshold ~25 scripts (v1.1 has 15). |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Burst bounds from burst_id | Custom SQLite lookup or hand-coded bbox per burst | `opera_utils.burst_frame_db.get_burst_id_geojson([burst_id])` [VERIFIED signature: `(burst_ids: Sequence[str] \| None = None, as_geodataframe: bool = False) -> GeojsonOrGdf`] | Already in the v1.0 pip layer via `opera-utils==0.25.6` — exposes `get_burst_id_geojson`, `get_burst_geodataframe`, `get_frame_bbox`, `get_intersecting_frames`. `bounds_for_burst` wraps it + applies `buffer_deg=0.2`. |
| COG validation / re-translation after metadata injection | Manual IFD-offset checking | `rio_cogeo==6.0.0` `cog_validate`, `cog_translate`, `cog_profiles` via `_cog.py` | `cog_validate` returns `tuple[bool, list[str], list[str]]` (is_valid, errors, warnings) since 2.1.1 (2021); IFD-offset is a **warning** — must be surfaced, not swallowed [PITFALLS P0.3] |
| macOS fork bundle (multiprocessing + matplotlib + FD + requests.Session) | One-line `mp.set_start_method('fork')` | Full `_mp.configure_multiprocessing()` per D-14 | 4 failure modes beyond fork: Cocoa/matplotlib state corruption, CFNetwork HTTPS pool corruption, FD-limit (macOS default 256), joblib/loky fork deprecation [PITFALLS P0.1] |
| HTTP retry on per-source taxonomy | `urllib3.Retry` or bespoke retry loop | Per-source `RETRY_POLICY` dict in harness.py; optionally `tenacity==9.1.4` composability | Earthdata 401 is NOT retryable; CloudFront 403 IS retryable with fresh URL; CDSE 429 is transient. Generic retry loses source-aware abort [PITFALLS P0.4] |
| Subprocess watchdog + grandchild cleanup | Thread or signal-based watchdog | `subprocess.Popen` wrap + `os.killpg(pgrp, SIGTERM/SIGKILL)` | Thread-level leaks under fork; signal-based fragile under multi-threaded C extensions (isce3, GDAL) [PITFALLS P0.1] |
| py-spy stack-dump on abort | Parse `/proc/PID/status` or attach custom debugger | `py-spy dump --pid <pid>` | Pure-binary, no native build needed (pip or conda-forge); reports all threads of all Python processes in the group |
| Criterion registry | YAML / JSON config file | `@dataclass(frozen=True) Criterion` + dict in `criteria.py` | Type-safe; git diff highlights changes; no runtime file I/O; matches `src/subsideo/products/types.py` dataclass convention |
| Matrix generation from CONCLUSIONS markdown | Regex-extract numbers from free-text | `results/matrix_manifest.yml` + per-eval `{meta,metrics}.json` sidecars | Machine-readable; survives CONCLUSIONS prose rewording; schema-versionable [PITFALLS R3, R5] |
| Reproducibility env lockfile | `conda-lock` (rejected) | `micromamba list --explicit --md5 > env.lockfile.<platform>.txt` | v1.1 scope (deferred conda-lock to v2); per-platform explicit URLs sufficient [CITED: CONTEXT.md Deferred] |

**Key insight:** Phase 1 is a **refactoring phase**. The custom-code surface is deliberately minimized — almost every "new module" is either (a) a re-export of existing third-party surface (`_cog.py`, `_mp.py`), (b) a data-only registry (`criteria.py`, `matrix_manifest.yml`), (c) a serialisation schema (`matrix_schema.py`), or (d) a thin wrapper around an existing helper (`bounds_for_burst` around `opera_utils.burst_frame_db.get_burst_id_geojson`). The only substantial new logic is `supervisor.py` (subprocess + mtime poll + os.killpg) and `selfconsistency.py` (coherence stats from ifgrams, already tested pattern in dolphin/MintPy).

## Runtime State Inventory

> Phase 1 is a refactor/rename/restructure phase (removing monkey-patches from `products/cslc.py`, rewriting all `rio_cogeo` imports through `_cog.py`, migrating 5 ValidationResult types). Inventory required.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | **None.** No databases, datastores, or cached artifacts embed `_patch_*` function names, the existing `RTCValidationResult.pass_criteria` keys, or any rio_cogeo import path. Verified: `grep -r "_patch_" eval-*/` returns zero hits; `grep -r "pass_criteria" eval-*/` finds only Python tracebacks in `.log` files (safe to leave). | None |
| **Live service config** | **None.** subsideo has no external n8n/Datadog/Tailscale service config referencing these internal symbols. | None |
| **OS-registered state** | **None.** No Windows Task Scheduler / launchd / systemd unit references. | None |
| **Secrets / env vars** | `EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD`, `CDSE_CLIENT_ID`, `CDSE_CLIENT_SECRET`, `~/.cdsapirc` — **unchanged by Phase 1**. These are credential keys used by harness.py's `credential_preflight`; names stay identical. | None — harness consumes existing env vars |
| **Build artifacts / installed packages** | `src/subsideo.egg-info/` (from `pip install -e .`) — no changes required; `pyproject.toml` is not touched by Phase 1 except possibly adding a new `ops` extra for py-spy. After conda-env.yml update, a full `pip install -e .[validation,viz]` via the conda-env.yml pip: section rebuilds the egg-info. Existing `pyc` / `__pycache__` directories will auto-regenerate on first import. | One full clean rebuild at end of phase: `rm -rf src/subsideo/__pycache__/ src/subsideo/**/__pycache__/ src/subsideo.egg-info/; micromamba run -n subsideo pip install -e .[validation,viz]` |
| **Test collection state** | `tests/unit/test_compare_*.py` → will be relocated to `tests/product_quality/` or `tests/reference_agreement/` (per §N). `tests/integration/` is empty (has only `__init__.py`). | `pytest --collect-only` re-run after migration to verify no orphaned or doubly-collected tests. |
| **Currently-installed conda env (active)** | `numpy 2.4.4`, `tophu 0.2.0`, `dist_s1 2.0.13` — these will downgrade/bump via Phase 1's `conda-env.yml` rebuild. py-spy is not installed yet. | Clean-env regeneration: `micromamba env remove -n subsideo && micromamba env create -f conda-env.yml` |

**The canonical question:** *After every file in the repo is updated, what runtime systems still have the old symbols cached, stored, or registered?*

**Answer:** Only Python bytecode caches (`__pycache__/` + `.pyc`) and the installed egg-info. Both regenerate on next import / `pip install -e .`. No cross-runtime state survives the phase.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `micromamba` | conda-env.yml rebuild | ✓ | 2.5.0 (verified `micromamba --version`) | — |
| `docker` | Linux-64 Dockerfile build on M3 Max (D-18) | ✓ | Docker 29.4.0 (verified `docker --version`) | — |
| `make` | Makefile (§G) | ✓ | GNU Make 3.81 (macOS default) | — |
| `git` | pre-commit / matrix_writer meta.json git_sha | ✓ (implicit) | — | — |
| Python 3.11 conda-forge | Fresh env create | ✓ via conda-forge | 3.11.x | — |
| `isce3=0.25.10` conda-forge | numpy-pin + patch removal verification | ✓ currently installed in env `subsideo` | 0.25.10 (unchanged) | — |
| `tophu=0.2.1` conda-forge | §A env pin + §O.2 import regression test | ✓ conda-forge latest 0.2.1 (bump from current 0.2.0) | 0.2.1 | — |
| `dist-s1=2.0.14` conda-forge | bump from 2.0.13 | ✓ conda-forge latest 2.0.14 | 2.0.14 | — |
| `rio-cogeo==6.0.0` pip | `_cog.py` | ✓ PyPI releases include 6.0.0 (current env has 7.0.2 which needs DOWNGRADE) | 6.0.0 | — |
| `py-spy=0.4.1` conda-forge or PyPI | watchdog stack dump | ✓ both (conda-forge 0.4.1, PyPI 0.4.1) — NOT currently installed | 0.4.1 | watchdog without stack dump (degrades D-13 debug quality, NOT blocking) |
| `tenacity==9.1.4` pip | harness `download_reference_with_retry` (optional per Claude's Discretion) | ✓ PyPI latest 9.1.4 | 9.1.4 | Roll-your-own exponential backoff — acceptable per Claude's Discretion |
| `owslib==0.35.0` pip | NOT Phase 1 (Phase 5 EFFIS — OUT OF SCOPE) | ✓ PyPI latest 0.35.0 | — | — |
| `mambaorg/micromamba:latest` Docker base | Dockerfile § J | ✓ Docker Hub public image | tag `latest` (v2.5.0) OR `debian-latest` | — |
| M3 Max native (osx-arm64) | Phase 1 dev-run acceptance | ✓ (user's machine) | M3 Max | — |
| TrueNAS Linux | Phase 7 cold-env audit (OUT OF SCOPE for Phase 1) | n/a | — | — |

**Missing dependencies with no fallback:** **None.** All tooling present or installable via Phase 1's own deliverables.

**Missing dependencies with fallback:** `py-spy` — fallback is watchdog without stack dump (degrades D-13 diagnostic quality to SIGTERM→SIGKILL only). Plan should treat this as a hard requirement since py-spy pip install is trivially available.

## Common Pitfalls

### Pitfall 1: macOS fork mode insufficient alone (PITFALLS P0.1)

**What goes wrong:** `multiprocessing.set_start_method('fork', force=True)` fixes the dist-s1 hang for a single `run_eval_dist.py`, but `make eval-all` triggers 4 additional failure modes: (1) Cocoa/matplotlib state corruption, (2) CFNetwork HTTPS session pool corruption, (3) FD-limit (macOS default 256 / 1024), (4) joblib/loky deprecation warning silently falling back to spawn.
**Why it happens:** The fork inherits live parent state including open sockets, matplotlib canvases, and file descriptors. A parent that has already `plt.plot()`ed or `requests.Session.get()`d poisons the fork.
**How to avoid:** Full `_mp.configure_multiprocessing()` bundle per D-14: `set_start_method('fork', force=True)` + `os.environ['MPLBACKEND'] = 'Agg'` **before** any matplotlib import + `resource.setrlimit(resource.RLIMIT_NOFILE, (4096, hard))` + close any module-global `requests.Session` before fork + `if sys.version_info >= (3, 14): use 'forkserver'`. Called at the TOP of every `products/*.run_*()` entry point.
**Warning signs:** `SSL_ERROR_ZERO_RETURN` after first eval stage completes; `OSError: [Errno 24] Too many open files` during DIST chip processing; joblib DeprecationWarning; hangs only reproducible in the full matrix, not in single scripts.
**Acceptance gate:** Three consecutive fresh `run_eval_dist*.py` runs succeed on M3 Max without hanging (ENV-05).

### Pitfall 2: rio_cogeo `cog_validate` IFD-offset warning silently swallowed (PITFALLS P0.3)

**What goes wrong:** `_cog.cog_validate()` returns `(True, [], [<IFD-offset warning>])`; naive call sites check only `is_valid` and ignore warnings. Newly-written COGs silently degrade to non-COG GeoTIFFs — downstream range-reads fall back to whole-file reads (slow).
**Why it happens:** rio-cogeo's `cog_validate` distinguishes errors, warnings, and info. The IFD-offset-past-300-byte-header is emitted as a **warning**, not an error — but it's a real COG-layout break (not a stylistic concern). The v1.0 `_metadata.py::_inject_geotiff` pattern (re-translate after tag update) is correct; Phase 1 formalises it as `ensure_valid_cog(path)`.
**How to avoid:** Per Claude's Discretion `_cog.py` API — `cog_validate(path) -> tuple[bool, list[str], list[str]]` surfaces warnings explicitly; `ensure_valid_cog(path)` re-translates in place if any IFD/layout warning is present. All metadata-injection code paths use `ensure_valid_cog` post-tag.
**Warning signs:** `gdalinfo <file> | grep LAYOUT` returns nothing; downstream users report slow tile reads.
**Smoke test:** `tests/product_quality/test_cog_validity.py` loads each output COG and asserts `is_valid=True` AND `warnings==[]` after metadata injection (consider `tests/unit/` too if the test is fully mocked).

### Pitfall 3: numpy<2 pin transitively breaks shapely/rasterio via conda solver acceptance (PITFALLS P0.2)

**What goes wrong:** `numpy<2.0` in conda-env.yml is accepted by the solver. Tests pass. Weeks later a user hits `AttributeError: 'numpy.int64' object has no attribute 'tolist'` because shapely 2.1+ has soft numpy-2 deps and the solver downgraded shapely to an unsupported older version.
**Why it happens:** Conda solver optimises constraint satisfaction, not test coverage.
**How to avoid:** After the pin lands, run `pytest tests/unit tests/integration` on BOTH macOS-arm64 AND linux-64 (Docker) per D-18. Record full `conda list --explicit --md5` as build artifact (this IS env.lockfile.<platform>.txt per D-16). Document sunset condition at top of conda-env.yml ("remove when isce3 ≥ 0.26 + compass numpy-2 + s1reader numpy-2 + all on conda-forge — see STACK §1").
**Warning signs:** `conda list` shows shapely 2.0.x rather than 2.1.x (with no explicit shapely pin); `test_burst_db` or similar unrelated tests fail after pin; CI matrix passes on Linux but fails on macOS-arm64 (or vice-versa).
**Acceptance gate:** Both lockfile platforms (`env.lockfile.linux-64.txt` + `env.lockfile.osx-arm64.txt`) generated and committed; `pytest tests/unit tests/integration` green on both.

### Pitfall 4: Forbidden import cycles (ARCHITECTURE §Failure-Mode Boundaries)

**What goes wrong:** A new module inadvertently imports `products/*` from `validation/harness` or `validation/results`, creating a cycle with `products/types → validation/results`.
**Why it happens:** `products/types.py` composes `ProductQualityResult` + `ReferenceAgreementResult` (D-07); if harness or results tries to inspect a `<Product>ValidationResult` by type, the import goes both directions.
**How to avoid:** `validation/results.py` MUST be a leaf — only imports from stdlib + `dataclasses`. `validation/harness.py` MAY import from `subsideo.data`, `subsideo.burst`, `subsideo.utils`, but NEVER from `subsideo.products`. Eval scripts import both (harness + products) — they are the top of the graph.
**Warning signs:** `ImportError: cannot import name ...` with circular import traceback; pytest collection errors; pyflakes / ruff `F401` in one module, `F402` in another.
**Test:** Run `ruff check --select=I src/` after refactor; run `python -c "import subsideo.validation.harness; import subsideo.validation.results; import subsideo.products.types; import subsideo.validation.compare_rtc"` to confirm no cycles.

### Pitfall 5: Per-source retry policy missing = infinite retry on 401 (PITFALLS P0.4)

**What goes wrong:** Naive `download_reference_with_retry` retries ALL HTTPError exceptions. Earthdata 401 (expired token) retries forever — wall-clock dominated by stalled downloads.
**Why it happens:** 401 / 403 / 404 / 429 / 503 have different semantics per source. CDSE 429 is transient; Earthdata 401 is permanent for this token; CloudFront 403 means "URL signature expired — refresh URL".
**How to avoid:** Per Claude's Discretion — dict-keyed constants in harness.py, `download_reference_with_retry` refuses to proceed without explicit source key. Policy:
```python
RETRY_POLICY = {
    'CDSE': {'retry_on': [429, 503, 'OutOfMemoryError'], 'abort_on': [401, 403]},
    'EARTHDATA': {'retry_on': [429, 503], 'abort_on': [401, 403, 404]},
    'CLOUDFRONT': {'retry_on': [503, 'ExpiredToken'], 'abort_on': [401, 404], 'refresh_url_on': [403]},
}
```
Abort statuses raise `ReferenceDownloadError(source, status)`.
**Warning signs:** N retry attempts all with 401; wall-clock on make eval-all dominated by one stalled download; backoff cap (300s) hit repeatedly.

### Pitfall 6: Test-split migration leaves reference_agreement tests asserting on criteria.py thresholds (GATE-04)

**What goes wrong:** A test moved to `tests/reference_agreement/` still asserts `result.product_quality.measurements['correlation'] > 0.92` (literal value from a criterion). This turns reference-agreement into a CI gate, exactly what the split is designed to prevent [PITFALLS M3].
**Why it happens:** Reviewer assumes "moved to reference_agreement dir" is the discipline without checking assertion content.
**How to avoid:** Per Claude's Discretion — a CI-adjacent linter rule rejects `assert` statements referencing `criteria.py` thresholds in `tests/reference_agreement/`. The linter pattern: ast-parse each test file; collect `ast.Compare` nodes; for each comparand that is a `ast.Constant` (float), flag it. Allow `is None`, `pytest.approx(...)`, `np.isfinite(...)`, `np.any(...)`, `len(...)`, etc. — these are plumbing checks.
**Warning signs:** A `tests/reference_agreement/test_compare_rtc.py` file that begins `assert result.product_quality.measurements['rmse_db'] < 0.5` (this IS a criteria.py threshold).
**Minimum viable linter:** `rg --type py 'assert.*\s+[<>]=?\s+\d+(\.\d+)?' tests/reference_agreement/` returns zero hits; a `tests/reference_agreement/conftest.py` with a pytest fixture that fails collection if any test in this tree imports from `subsideo.validation.criteria` for comparison purposes.

### Pitfall 7: Supervisor mtime-staleness heuristic false-positives on long-single-stage operations

**What goes wrong:** The D-10 heuristic says "abort if cache_dir has no mtime change in grace_window=120s AND wall_time > 2×EXPECTED_WALL_S". Some legitimate stages (large SAFE download, DEM stitching, long isce3 geocode) run quietly for 5-10 minutes without writing to the cache_dir.
**Why it happens:** `fetch_safe` downloads to a temp file and renames atomically at completion; `run_rtc` geocodes in scratch before writing output; these legitimately don't touch the cache_dir mtime.
**How to avoid:** The AND condition (120s no-change AND wall > 2×EXPECTED_WALL_S) is the safety valve — wall-time budget must have already doubled. Setting `EXPECTED_WALL_S` correctly per script is critical: for dist-s1 nominal 30 min, 2×=60 min, grace=120s. A stage legitimately running for 5 min at 50 min wall-clock will be aborted only if nothing changes for 2 more minutes past the 60-min mark.
Alternative: additionally poll `/tmp/` and the `scratch/` subdirectory for mtime changes. Tradeoff: more false-negatives (hang detected later).
**Warning signs:** Supervisor aborts a legitimate run; legitimate 40-min DIST runs terminated at 60 min + 2 min.
**Mitigation:** Allow each eval script to export `CACHE_WATCH_PATHS` (comma-separated) so supervisor watches multiple directories. Default = output cache_dir.

### Pitfall 8: mambaorg/micromamba Dockerfile USER + ENTRYPOINT gotchas

**What goes wrong:** The `mambaorg/micromamba` image sets `USER $MAMBA_USER` (default `mambauser`, UID 57439) and `ENTRYPOINT ["/usr/local/bin/_entrypoint.sh"]`. A custom Dockerfile that adds `USER root` or overwrites `ENTRYPOINT` without prepending `_entrypoint.sh` breaks env activation — `micromamba run -n subsideo pytest` fails because the env isn't activated in non-interactive docker run.
**Why it happens:** The `_entrypoint.sh` auto-activates the env; bypassing it leaves micromamba unactivated.
**How to avoid:**
```dockerfile
FROM mambaorg/micromamba:latest
USER $MAMBA_USER
COPY --chown=$MAMBA_USER:$MAMBA_USER conda-env.yml /tmp/
RUN micromamba install -y -n base -f /tmp/conda-env.yml && micromamba clean --all --yes
ARG MAMBA_DOCKERFILE_ACTIVATE=1    # activate on subsequent RUN
COPY --chown=$MAMBA_USER:$MAMBA_USER . /app/
WORKDIR /app
# To run the tests: docker run --rm subsideo:dev pytest tests/unit tests/integration
# (the default ENTRYPOINT activates the env)
```
**Warning signs:** `docker run subsideo:dev pytest` reports `ModuleNotFoundError: No module named 'rasterio'`; `conda list` shows wrong packages.
**Verify:** `docker run --rm subsideo:dev micromamba list | head -5` shows Python 3.11 + isce3 + dolphin.

## Code Examples

### Example 1: `_cog.py` top-level private module (§C)

Source reference: `src/subsideo/_metadata.py:1-13` (the precedent pattern).

Template for `src/subsideo/_cog.py`:
```python
"""Version-aware wrapper around rio-cogeo 6.0.0.

Centralises every import so a future rio-cogeo upgrade is a single-file
change.  Surfaces `cog_validate` warnings explicitly (the IFD-offset-past-
300-byte-header warning is a real COG-layout break, not a stylistic
concern — see .planning/research/PITFALLS.md Pitfall P0.3).

All rio_cogeo imports are deferred inside function bodies so `pip install
subsideo` without the conda-forge stack still imports this module cleanly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

_RIO_COGEO_VERSION: tuple[int, int, int] | None = None


def _get_version() -> tuple[int, int, int]:
    global _RIO_COGEO_VERSION
    if _RIO_COGEO_VERSION is None:
        import rio_cogeo
        parts = tuple(int(p) for p in rio_cogeo.__version__.split(".")[:3])
        _RIO_COGEO_VERSION = parts + (0,) * (3 - len(parts))
    return _RIO_COGEO_VERSION


def cog_validate(path: str | Path) -> tuple[bool, list[str], list[str]]:
    """Return (is_valid, errors, warnings) for the given path.

    Source: rio-cogeo 6.0.0 signature is
    ``cog_validate(src_path, strict=False, config=None, quiet=False) ->
    Tuple[bool, List[str], List[str]]`` [VERIFIED: github.com/cogeotiff/
    rio-cogeo/blob/6.0.0/rio_cogeo/cogeo.py].
    """
    from rio_cogeo import cog_validate as _impl
    is_valid, errors, warnings = _impl(str(path), quiet=True)
    if warnings:
        logger.warning("rio_cogeo warnings for {}: {}", path, warnings)
    return is_valid, errors, warnings


def cog_translate(src: str | Path, dst: str | Path, profile: Any, **kwargs: Any) -> None:
    """Wrap rio_cogeo.cog_translate."""
    from rio_cogeo import cog_translate as _impl
    _impl(str(src), str(dst), profile, **kwargs)


def cog_profiles() -> Any:
    """Return rio_cogeo's cog_profiles registry."""
    from rio_cogeo import cog_profiles as _profiles
    return _profiles


def ensure_valid_cog(path: str | Path) -> None:
    """Validate *path*; if IFD-offset warning is present, re-translate in place.

    Fixes the PITFALLS P0.3 silent-COG-degradation bug.  All metadata-
    injection code paths in v1.1 call this post-tag.
    """
    path = Path(path)
    is_valid, errors, warnings = cog_validate(path)
    ifd_bad = any(
        "offset of main IFD" in w.lower() or "ifd" in w.lower()
        for w in warnings
    )
    if not ifd_bad:
        return
    logger.info("Re-translating {} to heal IFD-offset warning", path)
    tmp = path.with_suffix(path.suffix + ".cogtmp")
    cog_translate(
        src=str(path),
        dst=str(tmp),
        profile=cog_profiles().get("deflate"),
        in_memory=False,
        quiet=True,
    )
    tmp.replace(path)


def RIO_COGEO_VERSION() -> tuple[int, int, int]:  # noqa: N802
    return _get_version()
```

### Example 2: `_mp.py` full fork bundle (§D, D-14, PITFALLS P0.1)

Template for `src/subsideo/_mp.py`:
```python
"""Multiprocessing start-method and environment bundle for subsideo product runs.

Forces 'fork' on macOS (with forkserver fallback on Python ≥3.14) AND
also: sets MPLBACKEND=Agg before any matplotlib import, raises
RLIMIT_NOFILE to 4096, closes any module-global requests.Session objects
before forking.  No-op on Linux through Python 3.13 (fork is default there).

Called at the TOP of every `products/*.run_*()` entry point — NOT at
module import (because unit-test imports should not force a start method).
Idempotent: safe to call multiple times in the same interpreter.
"""
from __future__ import annotations

import multiprocessing as mp
import os
import platform
import sys


_CONFIGURED = False


def configure_multiprocessing() -> None:
    """Apply the full macOS fork bundle.  Idempotent."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    # (1) Matplotlib backend — BEFORE any matplotlib import
    os.environ.setdefault("MPLBACKEND", "Agg")

    # (2) File-descriptor limit (macOS default is 256)
    if platform.system() != "Windows":
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        target = min(4096, hard)
        if soft < target:
            resource.setrlimit(resource.RLIMIT_NOFILE, (target, hard))

    # (3) Close any cached requests.Session pre-fork
    #    (Call-site-managed — modules that cache sessions should register
    #     close callbacks here.  For v1.1 scope, no global session exists
    #     in subsideo itself; this is a placeholder for downstream libs.)
    try:
        import requests  # noqa: F401
    except Exception:
        pass

    # (4) Start method
    if platform.system() == "Darwin":
        try:
            if sys.version_info >= (3, 14):
                mp.set_start_method("forkserver", force=True)
            else:
                mp.set_start_method("fork", force=True)
        except RuntimeError:
            # Already set this session — treat as no-op
            pass

    _CONFIGURED = True
```

### Example 3: `harness.bounds_for_burst` wrapping opera_utils (§F, ENV-08)

Source reference: `opera_utils.burst_frame_db.get_burst_id_geojson` signature verified `(burst_ids: Sequence[str] | None = None, as_geodataframe: bool = False) -> GeojsonOrGdf` [VERIFIED: Python introspection against `/Users/alex/.local/share/mamba/envs/subsideo/bin/python3` with `opera_utils 0.25.6`].

```python
# src/subsideo/validation/harness.py (excerpt)
from pathlib import Path
from typing import Any, Callable, Sequence

from loguru import logger


def bounds_for_burst(
    burst_id: str,
    buffer_deg: float = 0.2,
) -> tuple[float, float, float, float]:
    """Return (west, south, east, north) bounds for a burst_id, buffered by `buffer_deg`.

    Wraps `opera_utils.burst_frame_db.get_burst_id_geojson([burst_id],
    as_geodataframe=True)` and applies a symmetric degree buffer.  Falls
    back to the subsideo EU burst DB if opera_utils doesn't recognise the
    burst (EU bursts not yet in opera-utils; see `subsideo.burst.db`).

    Used by every run_eval_*.py to eliminate hand-coded
    `bounds=[-119.7, 33.2, -118.3, 34.0]` literals (ENV-08).
    """
    try:
        from opera_utils.burst_frame_db import get_burst_id_geojson
        gdf = get_burst_id_geojson([burst_id], as_geodataframe=True)
        if len(gdf) == 0:
            raise ValueError(f"Burst {burst_id!r} not in opera_utils burst_frame_db")
        west, south, east, north = gdf.total_bounds
    except Exception as first_err:  # noqa: BLE001
        logger.debug("opera_utils lookup failed for {}: {}; trying EU burst DB", burst_id, first_err)
        try:
            from subsideo.burst.db import query_bounds  # or equivalent existing helper
            west, south, east, north = query_bounds(burst_id)
        except Exception as second_err:
            raise ValueError(
                f"Burst {burst_id!r} not in opera_utils or subsideo EU DB: "
                f"({first_err}, {second_err})"
            ) from second_err

    return (
        west - buffer_deg,
        south - buffer_deg,
        east + buffer_deg,
        north + buffer_deg,
    )
```

### Example 4: `criteria.py` frozen dataclass + registry (§K, D-01..D-05)

```python
# src/subsideo/validation/criteria.py
"""Immutable metrics-vs-targets criterion registry.

Every criterion here has been either (a) inherited verbatim from v1.0
compare_*.py hardcoded thresholds, or (b) introduced for Phase 3/4 CSLC /
DISP self-consistency as CALIBRATING with binding_after_milestone='v1.2'.

Editing this file requires citing an ADR, upstream spec change, or
ground-truth validation in the PR description (D-03).  Immutability is
enforced via `frozen=True` at runtime + drift visibility via
matrix_writer.py echoing each criterion's threshold alongside the
measured value in results/matrix.md.

DO NOT pre-populate Phase 5 deliverables here (D-05).  Adding a new
criterion is additive: Phase 5 adds its own entries when it lands.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Criterion:
    name: str
    threshold: float
    comparator: Literal[">", ">=", "<", "<="]
    type: Literal["BINDING", "CALIBRATING"]
    binding_after_milestone: str | None  # None for BINDING
    rationale: str


CRITERIA: dict[str, Criterion] = {
    # ── RTC BINDING (from v1.0 compare_rtc.py:68-70) ────────────────
    "rtc.rmse_db_max": Criterion(
        name="rtc.rmse_db_max", threshold=0.5, comparator="<", type="BINDING",
        binding_after_milestone=None,
        rationale="OPERA RTC-S1 N.Am. agreement baseline — see "
                  "CONCLUSIONS_RTC_N_AM.md §3; reference-agreement criterion.",
    ),
    "rtc.correlation_min": Criterion(
        name="rtc.correlation_min", threshold=0.99, comparator=">", type="BINDING",
        binding_after_milestone=None,
        rationale="OPERA RTC-S1 cross-version correlation — hardcoded in "
                  "v1.0 compare_rtc.py:70; inherited unchanged.",
    ),
    # ── CSLC amplitude BINDING (from v1.0 compare_cslc.py:180-181) ──
    "cslc.amplitude_r_min": Criterion(
        name="cslc.amplitude_r_min", threshold=0.6, comparator=">", type="BINDING",
        binding_after_milestone=None,
        rationale="Cross-version isce3 phase-coherence impossibility — "
                  "amplitude is the sanity gate (CONCLUSIONS_CSLC_N_AM.md §5).",
    ),
    "cslc.amplitude_rmse_db_max": Criterion(
        name="cslc.amplitude_rmse_db_max", threshold=4.0, comparator="<", type="BINDING",
        binding_after_milestone=None,
        rationale="CSLC amplitude-RMSE ceiling — hardcoded v1.0 compare_cslc.py:181.",
    ),
    # ── CSLC self-consistency CALIBRATING (NEW in Phase 1) ──────────
    "cslc.selfconsistency.coherence_min": Criterion(
        name="cslc.selfconsistency.coherence_min", threshold=0.7, comparator=">",
        type="CALIBRATING", binding_after_milestone="v1.2",
        rationale="Stable-terrain coherence gate — first rollout v1.1 Phase 3 "
                  "(SoCal/Mojave/Meseta). GATE-05: ≥3 measured points before "
                  "BINDING promotion. Published C-band stable-terrain coherence "
                  "is 0.75-0.85 per PITFALLS P2.2; 0.7 is starting bar.",
    ),
    "cslc.selfconsistency.residual_mm_yr_max": Criterion(
        name="cslc.selfconsistency.residual_mm_yr_max", threshold=5.0, comparator="<",
        type="CALIBRATING", binding_after_milestone="v1.2",
        rationale="Residual mean velocity on stable terrain — first rollout "
                  "v1.1 Phase 3. Tightening to 1-2 mm/yr as stacks lengthen "
                  "beyond 6 months is v2 Future Work (CSLC-V2-02).",
    ),
    # ── DISP BINDING (from v1.0 compare_disp.py:181-183) ────────────
    "disp.correlation_min": Criterion(
        name="disp.correlation_min", threshold=0.92, comparator=">", type="BINDING",
        binding_after_milestone=None,
        rationale="EGMS Ortho vertical-displacement correlation — "
                  "hardcoded v1.0 compare_disp.py:181.",
    ),
    "disp.bias_mm_yr_max": Criterion(
        name="disp.bias_mm_yr_max", threshold=3.0, comparator="<", type="BINDING",
        binding_after_milestone=None,
        rationale="Allowed bias between subsideo DISP and EGMS; |bias| < 3 mm/yr.",
    ),
    # ── DISP self-consistency CALIBRATING (NEW in Phase 1) ──────────
    "disp.selfconsistency.coherence_min": Criterion(
        name="disp.selfconsistency.coherence_min", threshold=0.7, comparator=">",
        type="CALIBRATING", binding_after_milestone="v1.2",
        rationale="Mirror of CSLC self-consistency — Phase 4 native-5×10m. "
                  "GATE-05: ≥3 measured points before BINDING promotion.",
    ),
    "disp.selfconsistency.residual_mm_yr_max": Criterion(
        name="disp.selfconsistency.residual_mm_yr_max", threshold=5.0, comparator="<",
        type="CALIBRATING", binding_after_milestone="v1.2",
        rationale="Mirror of CSLC self-consistency residual — Phase 4.",
    ),
    # ── DIST BINDING (from v1.0 compare_dist.py:212-215) ────────────
    "dist.f1_min": Criterion(
        name="dist.f1_min", threshold=0.80, comparator=">", type="BINDING",
        binding_after_milestone=None,
        rationale="DIST-S1 F1 baseline (not a tightened goalpost) — "
                  "compare_dist.py:213.",
    ),
    "dist.accuracy_min": Criterion(
        name="dist.accuracy_min", threshold=0.85, comparator=">", type="BINDING",
        binding_after_milestone=None,
        rationale="DIST-S1 overall accuracy baseline — compare_dist.py:214.",
    ),
    # ── DSWx BINDING (from v1.0 compare_dswx.py:298) ────────────────
    "dswx.f1_min": Criterion(
        name="dswx.f1_min", threshold=0.90, comparator=">", type="BINDING",
        binding_after_milestone=None,
        rationale="DSWE-family architectural ceiling ≈0.92 per PROTEUS ATBD "
                  "(CONCLUSIONS_DSWX.md §3). 0.90 bar is ~2% below ceiling; "
                  "moving it requires ML upgrade path (DSWX-V2-01).",
    ),
}


# ── Typed accessor functions (D-02) ────────────────────────────────

def rtc_rmse_db_max() -> Criterion:
    return CRITERIA["rtc.rmse_db_max"]


def rtc_correlation_min() -> Criterion:
    return CRITERIA["rtc.correlation_min"]


def cslc_amplitude_r_min() -> Criterion:
    return CRITERIA["cslc.amplitude_r_min"]


def cslc_amplitude_rmse_db_max() -> Criterion:
    return CRITERIA["cslc.amplitude_rmse_db_max"]


def cslc_selfconsistency_coherence_min() -> Criterion:
    return CRITERIA["cslc.selfconsistency.coherence_min"]


def cslc_selfconsistency_residual_mm_yr_max() -> Criterion:
    return CRITERIA["cslc.selfconsistency.residual_mm_yr_max"]


def disp_correlation_min() -> Criterion:
    return CRITERIA["disp.correlation_min"]


def disp_bias_mm_yr_max() -> Criterion:
    return CRITERIA["disp.bias_mm_yr_max"]


def disp_selfconsistency_coherence_min() -> Criterion:
    return CRITERIA["disp.selfconsistency.coherence_min"]


def disp_selfconsistency_residual_mm_yr_max() -> Criterion:
    return CRITERIA["disp.selfconsistency.residual_mm_yr_max"]


def dist_f1_min() -> Criterion:
    return CRITERIA["dist.f1_min"]


def dist_accuracy_min() -> Criterion:
    return CRITERIA["dist.accuracy_min"]


def dswx_f1_min() -> Criterion:
    return CRITERIA["dswx.f1_min"]
```

### Example 5: `results.py` split generic types (§L, D-06..D-08)

```python
# src/subsideo/validation/results.py
"""Generic result types for product-quality vs reference-agreement split.

Per-product ValidationResult classes in src/subsideo/products/types.py
COMPOSE these two types (D-07). Import direction is
products/types.py → validation/results.py (one-way; data-only leaf).

Per D-08: named fields + criterion_ids, no stored booleans.
Pass/fail is computed at read time via evaluate() — keeps old metrics.json
records re-evaluable against edited criteria thresholds (drift-safe).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from subsideo.validation.criteria import CRITERIA, Criterion


@dataclass
class ProductQualityResult:
    """Per-product-quality-gate measurements + criterion IDs.

    Never holds a .passed bool. Use evaluate() below at read time.
    """
    measurements: dict[str, float] = field(default_factory=dict)
    criterion_ids: list[str] = field(default_factory=list)


@dataclass
class ReferenceAgreementResult:
    """Per-reference-agreement measurements + criterion IDs."""
    measurements: dict[str, float] = field(default_factory=dict)
    criterion_ids: list[str] = field(default_factory=list)


def _compare(value: float, criterion: Criterion) -> bool:
    ops = {
        ">": float.__gt__, ">=": float.__ge__,
        "<": float.__lt__, "<=": float.__le__,
    }
    return bool(ops[criterion.comparator](float(value), float(criterion.threshold)))


def evaluate(
    result: ProductQualityResult | ReferenceAgreementResult,
    criteria: dict[str, Criterion] = CRITERIA,
) -> dict[str, bool]:
    """Return {criterion_id: passed_bool} for every criterion listed on result.

    Never mutates result. Read-time computation means old metrics.json
    records remain re-evaluable against edited criteria.py thresholds.
    """
    out: dict[str, bool] = {}
    for cid in result.criterion_ids:
        crit = criteria[cid]
        # Measurement key matches the last part of criterion ID after the
        # final dot — convention: criterion 'rtc.rmse_db_max' reads
        # measurement key 'rmse_db'. Strip the leading domain + trailing
        # threshold-semantic suffix.
        # (Plan may refine the mapping; the simplest convention is a
        # measurement dict keyed by the criterion's short suffix.)
        short_key = cid.split(".")[-1].removesuffix("_min").removesuffix("_max")
        if short_key in result.measurements:
            out[cid] = _compare(result.measurements[short_key], crit)
    return out
```

### Example 6: Migrated `products/types.py` — composite shape (D-06, D-07, D-09)

Before (source: `src/subsideo/products/types.py:62-69`):
```python
@dataclass
class RTCValidationResult:
    rmse_db: float
    correlation: float
    bias_db: float
    ssim_value: float
    pass_criteria: dict[str, bool] = field(default_factory=dict)
```

After (Phase 1 big-bang migration):
```python
from subsideo.validation.results import ProductQualityResult, ReferenceAgreementResult


@dataclass
class RTCValidationResult:
    product_quality: ProductQualityResult
    reference_agreement: ReferenceAgreementResult
    # NO top-level .passed.  NO pass_criteria dict.
    # Call sites compute pass/fail via validation.results.evaluate(...)
```

Same shape applied to `CSLCValidationResult`, `DISPValidationResult`, `DISTValidationResult`, `DSWxValidationResult` — see §M for per-file migration steps.

Migrated `compare_rtc.py` return (was `src/subsideo/validation/compare_rtc.py:63-72`):
```python
from subsideo.validation.results import ProductQualityResult, ReferenceAgreementResult
from subsideo.products.types import RTCValidationResult

# ...existing metric computations above unchanged (rmse_val, corr_val, bias_val, ssim_val)...

return RTCValidationResult(
    product_quality=ProductQualityResult(
        measurements={"ssim": ssim_val},
        criterion_ids=[],  # v1.0 had no product-quality gate for RTC; stays empty
    ),
    reference_agreement=ReferenceAgreementResult(
        measurements={
            "rmse_db": rmse_val,
            "correlation": corr_val,
            "bias_db": bias_val,
        },
        criterion_ids=["rtc.rmse_db_max", "rtc.correlation_min"],
    ),
)
```

### Example 7: `supervisor.py` entry point (§E, D-10..D-13)

```python
# src/subsideo/validation/supervisor.py
"""Per-script subprocess watchdog with mtime staleness heuristic.

Invoked via:  python -m subsideo.validation.supervisor <eval_script.py>

Monitors:
  - Wall time vs EXPECTED_WALL_S (module-level constant in eval script)
  - Output-cache mtime staleness (D-10)

On abort (2×EXPECTED_WALL_S exceeded AND cache mtime stale for grace_window):
  1. py-spy dump --pid <child_pid> > <cache_dir>/watchdog-stacks.txt
  2. os.killpg(pgid, SIGTERM)
  3. 30s grace
  4. os.killpg(pgid, SIGKILL) if still alive
  5. sys.exit(124)  — conventional timeout(1) exit code
"""
from __future__ import annotations

import argparse
import ast
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

GRACE_WINDOW_S = 120
POLL_INTERVAL_S = 30
KILL_GRACE_S = 30
TIMEOUT_EXIT_CODE = 124


def _parse_expected_wall_s(script_path: Path) -> int:
    """AST-parse the script; return EXPECTED_WALL_S literal or raise."""
    tree = ast.parse(script_path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "EXPECTED_WALL_S":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, (int, float)):
                        return int(node.value.value)
    raise ValueError(
        f"{script_path}: must declare module-level EXPECTED_WALL_S = <int_seconds>"
    )


def _newest_mtime(cache_dir: Path) -> float:
    if not cache_dir.exists():
        return 0.0
    try:
        return max(
            (f.stat().st_mtime for f in cache_dir.rglob("*") if f.is_file()),
            default=0.0,
        )
    except (OSError, FileNotFoundError):
        return 0.0


def _py_spy_dump(pid: int, out_path: Path) -> None:
    try:
        with out_path.open("w") as f:
            subprocess.run(
                ["py-spy", "dump", "--pid", str(pid)],
                stdout=f, stderr=subprocess.STDOUT,
                timeout=30, check=False,
            )
        logger.info("py-spy dump written to {}", out_path)
    except FileNotFoundError:
        logger.warning("py-spy not installed; skipping stack dump")
    except Exception as e:  # noqa: BLE001
        logger.warning("py-spy dump failed: {}", e)


def _cache_dir_from_script(script_path: Path) -> Path:
    """Convention: run_eval_dist.py → eval-dist/."""
    stem = script_path.stem.removeprefix("run_eval_").removeprefix("run_eval")
    stem = stem.strip("_") or "rtc"  # run_eval.py → eval-rtc
    return Path(f"eval-{stem}" if stem != "rtc" or script_path.name != "run_eval.py" else "eval-rtc")


def run(script_path: Path, cache_dir: Path | None = None) -> int:
    expected_wall = _parse_expected_wall_s(script_path)
    cache_dir = cache_dir or _cache_dir_from_script(script_path)

    start = time.monotonic()
    last_mtime = _newest_mtime(cache_dir)
    last_change = start

    # Fork subprocess in new process group
    proc = subprocess.Popen(
        [sys.executable, str(script_path)],
        start_new_session=True,  # setsid → new process group
    )
    pgid = os.getpgid(proc.pid)

    try:
        while proc.poll() is None:
            time.sleep(POLL_INTERVAL_S)
            now = time.monotonic()
            current_mtime = _newest_mtime(cache_dir)
            if current_mtime > last_mtime:
                last_mtime = current_mtime
                last_change = now

            wall = now - start
            stale = now - last_change

            if wall > 2 * expected_wall and stale > GRACE_WINDOW_S:
                logger.warning(
                    "Watchdog abort: wall={}s > 2×{}s AND cache stale for {}s",
                    int(wall), expected_wall, int(stale),
                )
                # (1) py-spy dump BEFORE killing
                _py_spy_dump(proc.pid, cache_dir / "watchdog-stacks.txt")
                # (2) SIGTERM process group
                os.killpg(pgid, signal.SIGTERM)
                # (3) Grace
                try:
                    proc.wait(timeout=KILL_GRACE_S)
                except subprocess.TimeoutExpired:
                    os.killpg(pgid, signal.SIGKILL)
                    proc.wait(timeout=5)
                return TIMEOUT_EXIT_CODE
    except KeyboardInterrupt:
        os.killpg(pgid, signal.SIGTERM)
        proc.wait(timeout=KILL_GRACE_S)
        raise

    return proc.returncode or 0


def main() -> int:
    parser = argparse.ArgumentParser("subsideo supervisor")
    parser.add_argument("script", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args()
    return run(args.script, args.cache_dir)


if __name__ == "__main__":
    sys.exit(main())
```

### Example 8: `conda-env.yml` (§A, D-15)

Canonical form (file: `conda-env.yml` at repo root):
```yaml
# conda-env.yml — subsideo v1.1 environment
# Sunset conditions:
#   numpy<2.0           → isce3 ≥ 0.26 + compass numpy-2 + s1reader numpy-2
#   rio-cogeo==6.0.0    → subsideo baseline Python bumps to ≥3.11 (v1.2 scope)
#   tophu (conda-forge) → dolphin ≥0.43 makes tophu optional + tophu ships to PyPI
name: subsideo
channels:
  - conda-forge
  - nodefaults
dependencies:
  # ── Runtime ───────────────────────────────────────────────
  - python=3.11
  - numpy>=1.26,<2.0        # Phase 1 §A pin — removes 4 monkey-patches
  - scipy>=1.14
  - pip

  # ── SAR / InSAR core (conda-forge only, NEVER pip) ───────
  - isce3=0.25.10
  - compass=0.5.6
  - s1reader=0.2.5
  - dolphin=0.42.5
  - tophu=0.2.1             # §A correction to BOOTSTRAP §0.2 — conda-forge
  - snaphu-py=0.4.1
  - mintpy=1.6.3
  - dist-s1=2.0.14          # bump from 2.0.13

  # ── Raster / vector I/O ──────────────────────────────────
  - gdal>=3.8
  - rasterio=1.5.*
  - rioxarray=0.22.*
  - geopandas>=1.0
  - shapely>=2.0
  - pyproj=3.7.*
  - xarray>=2024.11
  - h5py>=3.12
  - scikit-image>=0.24

  # ── Dev + test ───────────────────────────────────────────
  - pytest>=8
  - pytest-cov
  - pytest-mock
  - ruff
  - mypy
  - pre-commit

  # ── Ops (watchdog stack dumps) ───────────────────────────
  - py-spy=0.4.1            # Phase 1 §E — watchdog diagnostic

  # ── Pip-layer (pure Python on top of conda) ──────────────
  - pip:
      - -e .[validation,viz]
      - rio-cogeo==6.0.0    # Phase 1 §C pin — 7.x drops Python 3.10
      # Optional: add tenacity==9.1.4 if Claude's Discretion chose tenacity for harness retries
```

### Example 9: `Dockerfile` (§J, D-17)

```dockerfile
# Dockerfile at repo root — Phase 1 §J
# Target: subsideo:dev   (CPU-only; M3 Max arm64 and linux/amd64)
FROM mambaorg/micromamba:latest AS builder

USER $MAMBA_USER
COPY --chown=$MAMBA_USER:$MAMBA_USER conda-env.yml /tmp/conda-env.yml
COPY --chown=$MAMBA_USER:$MAMBA_USER pyproject.toml README.md LICENSE /app/
COPY --chown=$MAMBA_USER:$MAMBA_USER src /app/src

WORKDIR /app
RUN micromamba install -y -n base -f /tmp/conda-env.yml && \
    micromamba clean --all --yes

# Final stage: thin runtime on top of cached env
FROM mambaorg/micromamba:latest
COPY --from=builder /opt/conda /opt/conda
USER $MAMBA_USER
WORKDIR /app
COPY --chown=$MAMBA_USER:$MAMBA_USER . /app
ARG MAMBA_DOCKERFILE_ACTIVATE=1

# Default: run pytest to verify env
CMD ["pytest", "tests/unit", "tests/integration"]
```

**Verification commands:**
```bash
docker build . -t subsideo:dev
docker run --rm subsideo:dev pytest tests/unit tests/integration
docker run --rm subsideo:dev micromamba list | head -20
```

### Example 10: `Apptainer.def` (§J, D-17)

```singularity
# Apptainer.def — derives from Docker image (CPU only; no CUDA)
Bootstrap: docker-daemon
From: subsideo:dev

%labels
    maintainer subsideo-team
    subsideo-milestone v1.1-phase1

%environment
    export LC_ALL=C.UTF-8
    export MAMBA_DOCKERFILE_ACTIVATE=1

%runscript
    exec micromamba run -n base "$@"

%test
    micromamba run -n base pytest tests/unit -q
```

### Example 11: `Makefile` (§G, minimum viable, D-12)

```make
# Makefile at repo root — Phase 1 §G (Claude's Discretion: minimum viable)
# Supervisor: python -m subsideo.validation.supervisor <script.py>
SHELL := /bin/bash
PY := micromamba run -n subsideo python
SUPERVISOR := $(PY) -m subsideo.validation.supervisor

.PHONY: eval-all eval-nam eval-eu results-matrix clean-cache \
        eval-rtc-nam eval-rtc-eu eval-cslc-nam eval-cslc-eu \
        eval-disp-nam eval-disp-eu eval-dist-nam eval-dist-eu \
        eval-dswx-nam eval-dswx-eu

eval-rtc-nam:   ; $(SUPERVISOR) run_eval.py
eval-rtc-eu:    ; $(SUPERVISOR) run_eval_rtc_eu.py
eval-cslc-nam:  ; $(SUPERVISOR) run_eval_cslc.py
eval-cslc-eu:   ; $(SUPERVISOR) run_eval_cslc_eu.py
eval-disp-nam:  ; $(SUPERVISOR) run_eval_disp.py
eval-disp-eu:   ; $(SUPERVISOR) run_eval_disp_egms.py
eval-dist-nam:  ; $(SUPERVISOR) run_eval_dist.py
eval-dist-eu:   ; $(SUPERVISOR) run_eval_dist_eu.py
eval-dswx-nam:  ; $(SUPERVISOR) run_eval_dswx_nam.py
eval-dswx-eu:   ; $(SUPERVISOR) run_eval_dswx.py

eval-nam: eval-rtc-nam eval-cslc-nam eval-disp-nam eval-dist-nam eval-dswx-nam
eval-eu:  eval-rtc-eu  eval-cslc-eu  eval-disp-eu  eval-dist-eu  eval-dswx-eu

eval-all: eval-nam eval-eu results-matrix

results-matrix:
	$(PY) -m subsideo.validation.matrix_writer --out results/matrix.md

clean-cache:
	@read -p "Remove eval-*/ caches? [y/N] " yn; \
	if [ "$$yn" = "y" ]; then rm -rf eval-*/; fi
```

**Per-cell isolation:** each `eval-*` target delegates to the supervisor, which forks a fresh subprocess → fresh FD table, fresh requests.Session, fresh matplotlib state (P0.1 mitigation). Failure in one target (exit 124 from supervisor OR non-zero from script) doesn't block the rest because Make with `-k` (`make -k eval-all`) continues past errors; for ENV-09 "per-cell isolation" acceptance the `results-matrix` target should read manifest + sidecars and write cells labelled `RUN_FAILED` for missing ones (§H).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 4 monkey-patches in products/cslc.py (numpy-2 compat for compass/s1reader/isce3) | numpy<2 pin + delete patches | Phase 1 ENV-01/02 | Removes 114 LOC of brittle patches. Sunset when isce3 ≥ 0.26 rebuilds against pybind11 ≥ 2.12. |
| Three inline `try/except ImportError` blocks around `from rio_cogeo.cogeo/cog_validate import ...` | Single `from subsideo._cog import cog_validate` | Phase 1 ENV-03 | 10 import sites collapse to 1. rio-cogeo==6.0.0 pin (not 7.x — STACK §3 correction). |
| Plain `multiprocessing.set_start_method('fork')` or no call at all | Full `_mp.configure_multiprocessing()` bundle (start method + MPLBACKEND + ulimit + session close + forkserver on py≥3.14) | Phase 1 ENV-04 (PITFALLS P0.1) | 3 failure modes become detectable/preventable: Cocoa state, CFNetwork pool, FD-limit. |
| Ad-hoc retry loops per eval script (different policies for CDSE/Earthdata/CloudFront) | `harness.download_reference_with_retry(..., source=...)` with per-source `RETRY_POLICY` dict | Phase 1 ENV-06/07 | Earthdata 401 no longer retries forever; CloudFront 403 refreshes URL; CDSE 429 backs off correctly. |
| Hand-coded `bounds = [west, south, east, north]` literals in every eval script | `harness.bounds_for_burst(burst_id, buffer_deg=0.2)` wrapping `opera_utils.burst_frame_db.get_burst_id_geojson` | Phase 1 ENV-08 | Zero hand-coded geographic literals; regenerable from burst DB. |
| Single `.passed: bool` collapsing product-quality + reference-agreement | Nested composite `ProductQualityResult + ReferenceAgreementResult`; pass/fail computed at read time via `evaluate()` | Phase 1 GATE-02 / D-06..D-09 | Matrix cell shows two distinct columns; prevents M2 conflation. |
| Thresholds hardcoded in compare_*.py (e.g. `> 0.99` inline at compare_rtc.py:70) | `validation/criteria.py` immutable registry with `@dataclass(frozen=True) Criterion` + typed accessors | Phase 1 GATE-01 / D-01..D-05 | 13 thresholds now centralized + git-diff-visible. Prevents M1 target-creep via visible matrix echo. |
| Eval scripts with inline fork + no watchdog | `make eval-X` → supervisor subprocess wrap with mtime staleness + os.killpg + py-spy dump + exit 124 | Phase 1 ENV-05 / D-12 | 3 consecutive fresh `run_eval_dist*.py` runs on macOS succeed without hanging. |
| Manual interpretation of CONCLUSIONS markdown | `results/matrix_manifest.yml` + per-eval `{meta,metrics}.json` Pydantic schemas | Phase 1 ENV-09 / GATE-03 | Matrix generation machine-readable end-to-end. |
| pip install + hand-curated env (no lockfile, no Docker) | `conda-env.yml` + per-platform `env.lockfile.<os>.txt` + Dockerfile + Apptainer.def | Phase 1 ENV-10 / D-15..D-18 | Closure-test reproducibility; both platforms (osx-arm64 + linux-64 Docker) validated in Phase 1. |

**Deprecated/outdated:**
- `rio-cogeo` 7.x — drops Python 3.10 (subsideo pins >=3.10); STAY ON 6.0.0 until v1.2 Python baseline bump.
- The `try/except` polymorphism around `cog_validate` import path — NO API move happened in 7.x (STACK §3 correction).
- `pip install tophu` — doesn't exist (PyPI 404); conda-forge only.
- Global expansion assumptions built into the v1.0 burst DB — scope is still N.Am. + EU.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `opera_utils.burst_frame_db.get_burst_id_geojson` covers all `burst_id`s used across 7 existing + 6 new eval scripts | §F (Example 3) | Some EU bursts may not be in opera-utils' N.Am.-only DB. Research SUMMARY §3 already mentions this — `bounds_for_burst` falls back to `subsideo.burst.db.query_bounds`. Risk: the subsideo EU burst DB helper name/signature needs confirmation. Plan should verify the fallback's signature. [ASSUMED — needs call-site check during plan-phase] |
| A2 | Cache-dir mtime-staleness heuristic triggers only on true hangs (not on legitimate long download/geocode stages with atomic rename) | Pitfall 7 | False-positive aborts of legitimate 40-min runs. Mitigation: documented `EXPECTED_WALL_S` budget + 2× multiplier + 120s grace. [ASSUMED — will be validated by 3 consecutive fresh dist runs per ENV-05] |
| A3 | Supervisor-parsed `EXPECTED_WALL_S` module-level constant is sufficient; no supervisor-side registry | Example 7 (§E) | If AST parse is brittle (e.g. someone sets `EXPECTED_WALL_S = 30 * 60`), the parser misses non-literal expressions. Mitigation: require literal integer; ValueError if expression found. [ASSUMED — parse rule is clear for literal ints only] |
| A4 | `py-spy dump --pid <pid>` works on an attached subprocess on macOS M3 Max without additional setup (permissions) | Example 7 (§E) | macOS SIP may require elevated permissions to attach to a subprocess. py-spy docs say `sudo` may be needed on some macOS configurations. Mitigation: the subprocess is a child of the supervisor, so attachment should work without sudo. Fallback: log warning if py-spy fails, continue with SIGTERM. [ASSUMED — verify on Phase 1 first-run] |
| A5 | tests/reference_agreement/ linter can be a pytest plugin (conftest.py) instead of a standalone pre-commit check | Pitfall 6 + §N | If implemented as conftest.py collection hook, it only catches tests at pytest-collect time, not pre-commit. For v1.1 solo-dev workflow that's likely fine. Pre-commit hook is the heavier alternative. [ASSUMED — plan-phase chooses which layer] |
| A6 | The 4th monkey-patch is the inline `np.string_ = np.bytes_` shim at cslc.py:400-402 (not a 4th named function) | §B | If the 4th patch is something else the researcher missed, ENV-02 acceptance (`grep _patch_` returns 0) could still false-pass. Verified via `grep -n "_patch_\|np\.string_\s*=\s*np\.bytes_"` returning exactly 3 `def _patch_` lines + 1 inline shim. [VERIFIED: 4 total monkey-patching locations in cslc.py — 3 named functions + 1 inline np.string_ = np.bytes_ shim] |
| A7 | `mambaorg/micromamba:latest` is the right tag (not `debian-latest` or `jammy-cuda-latest`) for an arm64-native M3 Max build | Example 9 (§J) | `latest` on Docker Hub multi-arch may pull a non-arm64 image on Apple Silicon without Rosetta. Docker Desktop on M3 Max auto-emulates. Research finding: `docker buildx --platform linux/arm64,linux/amd64` is available but not required for Phase 1 scope (D-18 specifies linux-64 Docker on M3 Max under emulation). [ASSUMED — plan-phase should pin an explicit tag like `mambaorg/micromamba:2.5.0` for reproducibility] |
| A8 | All 10 matrix cells have an `eval_script` that writes `{meta,metrics}.json` — no eval script is optional | §H | Phases 2-6 are each responsible for their eval scripts writing the sidecars. Phase 1's matrix_writer only needs to handle MISSING sidecar gracefully (mark cell RUN_FAILED). Phase 1 doesn't need to author the 10 eval scripts — 7 exist, 6 more come in Phases 2-6. [VERIFIED from CONTEXT.md — Phase 1 scope is plumbing, not adding new eval scripts] |

## Open Questions

1. **Should py-spy become a `pyproject.toml [project.optional-dependencies]` extra, a dev extra, or stay conda-env.yml-only?**
   - What we know: py-spy 0.4.1 is on both conda-forge and PyPI; it's a pure Rust binary with no native build. Per CONTEXT.md Claude's Discretion it's added to conda-env.yml. Not currently in pyproject.toml.
   - What's unclear: if a user does `pip install subsideo[dev]` without the conda env, should they get py-spy? The supervisor degrades gracefully without it (logs warning, skips dump). Adding a new `ops` extra would be cleanest but adds scope.
   - Recommendation: ship py-spy in conda-env.yml ONLY (D-15). Do not add to pyproject.toml in Phase 1. If needed later, promote to a new `ops` extra.

2. **`subsideo.burst.db` fallback API for `bounds_for_burst` (A1).**
   - What we know: opera_utils.burst_frame_db may not cover every EU burst ID. `subsideo.burst.db` exists per CLAUDE.md (builds EU SQLite from ESA burst map).
   - What's unclear: the exact public API — whether `query_bounds(burst_id) -> (w,s,e,n)` exists or must be added; whether `burst/db.py` file exposes a function with the same signature.
   - Recommendation: plan-phase greps `src/subsideo/burst/db.py` for a bounds lookup function and either reuses it or adds `query_bounds` helper as a small Phase 1 sub-task.

3. **Does `evaluate()` in `validation/results.py` need to handle missing measurements gracefully?**
   - What we know: `result.criterion_ids` and `result.measurements` are independently maintained; a criterion_id could reference a measurement key that hasn't been populated.
   - What's unclear: is missing measurement → `False` (conservative) or → raise KeyError (fail-fast)?
   - Recommendation: raise KeyError — fail-fast matches D-09 big-bang philosophy. Matrix writer catches + surfaces as "MEASUREMENT MISSING" in the cell.

4. **Makefile `clean-cache` vs per-target rebuild contract.**
   - What we know: Per Claude's Discretion, `clean-cache` exists. Per D-12, each eval runs subprocess-isolated.
   - What's unclear: does `clean-cache` nuke all `eval-*/` dirs (force full re-download) or only the matrix manifest + sidecars?
   - Recommendation: `clean-cache` prompts user (`y/N`) before removing `eval-*/`; `clean-results` (not listed by Claude's Discretion, but minor) could clean only `results/` sidecars.

5. **Should `conda-env.yml` pin `rasterio=1.5.*` or allow `>=1.4,<2`?**
   - What we know: v1.0 uses `rasterio>=1.4,<2` in pyproject.toml; rasterio 1.5.0 raised GDAL floor from 3.3 to 3.8.
   - What's unclear: strict pin `rasterio=1.5.*` prevents a future bugfix 1.6; loose pin `>=1.4,<2` keeps install flexible.
   - Recommendation: loose (`>=1.5,<2` to ensure GDAL 3.8 floor); v1.0 compat preserved.

6. **`env.lockfile.linux-64.txt` generation on M3 Max via Docker — is that a supported workflow?**
   - What we know: Docker Desktop on M3 Max supports linux/amd64 via Rosetta emulation; `docker run --platform linux/amd64 mambaorg/micromamba micromamba env create -f conda-env.yml && micromamba list --explicit --md5` produces a linux-64 lockfile.
   - What's unclear: whether emulated-install solver reports the SAME packages an actual linux-64 host would solve. Risk: low (conda-forge is content-addressed; solver is platform-aware).
   - Recommendation: Phase 1 generates via emulation; Phase 7 TrueNAS audit cross-verifies.

## Sources

### Primary (HIGH confidence — verified in this session)

- `src/subsideo/_metadata.py` (lines 1-99; verified 2026-04-21) — `_cog.py` / `_mp.py` placement precedent
- `src/subsideo/products/types.py` (lines 1-163; verified 2026-04-21) — 5 ValidationResult classes to migrate
- `src/subsideo/products/cslc.py` (lines 10-12, 156, 226, 296, 392-407; verified via `grep -n "_patch_"`) — 4 monkey-patch locations
- `src/subsideo/validation/compare_rtc.py` (lines 11, 63-72; 72 LOC total) — return signature change scope
- `src/subsideo/validation/compare_cslc.py` (lines 16, 128-137, 174-183; 183 LOC total) — return signature change scope
- `src/subsideo/validation/compare_disp.py` (lines 27, 177-184, 356-363; 363 LOC total) — return signature change scope
- `src/subsideo/validation/compare_dist.py` (lines 43, 184-191, 212-224; 224 LOC total) — return signature change scope
- `src/subsideo/validation/compare_dswx.py` (lines 10, 209-212, 293-299; 299 LOC total) — return signature change scope
- `src/subsideo/validation/__init__.py` (empty as of 2026-04-21) — Phase 1 populates
- `src/subsideo/validation/metrics.py` (124 lines verified) — UNCHANGED by Phase 1
- `src/subsideo/products/rtc.py` (lines 102-103, 138-139) — 4 rio_cogeo import sites
- `src/subsideo/products/dist.py` (lines 44-49) — 2 rio_cogeo import sites with try/except
- `src/subsideo/products/dswx.py` (lines 503-504, 533) — 3 rio_cogeo import sites
- `tests/unit/test_cslc_pipeline.py` (lines 127-129) — monkey-patch mocks to delete with ENV-02
- `tests/unit/test_compare_dist.py` (lines 65-94, 128-133) — pass_criteria + result.f1 assertions to migrate (candidate for `tests/reference_agreement/`)
- `tests/unit/test_compare_disp.py` (lines 78-129) — correlation/bias assertions (candidate for `tests/reference_agreement/`)
- `tests/unit/test_compare_rtc.py` (lines 46-50, 63-83) — RMSE/correlation assertions (candidate for `tests/reference_agreement/`)
- `tests/unit/test_compare_cslc.py` (lines 41-47) — amplitude_correlation assertions (candidate for `tests/reference_agreement/`)
- `tests/unit/test_compare_dswx.py` (lines 1-113; inspected) — pure plumbing, NO pass_criteria/threshold assertions → STAY in `tests/unit/` (the only one of the 5)
- `run_eval.py` (114 LOC; line 69 hand-coded bounds) — pilot harness-migration target
- `pyproject.toml` (lines 1-260; verified) — optional-dependencies [validation], [viz], [dev] already defined
- `tests/conftest.py` (32 lines) — existing fixtures `po_valley_bbox`, `tmp_cache_dir`
- `tests/integration/__init__.py` (empty) — Phase 1 first resident will be `test_fresh_env_imports.py` + `test_cog_helper.py`
- PyPI JSON for `rio-cogeo`, `tenacity`, `owslib`, `py-spy` (verified 2026-04-21 via `curl https://pypi.org/pypi/<pkg>/json`)
- anaconda.org API for `tophu`, `dist-s1`, `py-spy` conda-forge channel (verified 2026-04-21 via `curl https://api.anaconda.org/package/conda-forge/<pkg>`)
- `opera_utils 0.25.6` installed in env `subsideo`: `get_burst_id_geojson(burst_ids, as_geodataframe=False)` signature verified via Python introspection
- rio_cogeo 6.0.0 `cog_validate` signature: `(src_path, strict=False, config=None, quiet=False) -> Tuple[bool, List[str], List[str]]` [VERIFIED: github.com/cogeotiff/rio-cogeo/blob/6.0.0/rio_cogeo/cogeo.py via WebFetch]

### Secondary (HIGH confidence — cross-referenced)

- `.planning/research/SUMMARY.md` — BOOTSTRAP corrections table (4 items baked into Phase 1)
- `.planning/research/STACK.md` — v1.1 stack deltas; version pin justifications
- `.planning/research/ARCHITECTURE.md` — §1 harness.py placement + §2 _cog/_mp top-level precedent + §6 results/matrix.md manifest + §8 test architecture + §Failure-Mode Boundaries import-cycle analysis + §Build Order internal ordering
- `.planning/research/PITFALLS.md` — M1-M6 metrics-vs-targets; P0.1-P0.4 env pitfalls; P2.1-P2.3 stable-terrain methodology
- `.planning/ROADMAP.md` §Phase 1 — 17 requirements, 6 success criteria, internal ordering
- `.planning/REQUIREMENTS.md` ENV-01..10, GATE-01..05, CSLC-01..02 full text
- `.planning/PROJECT.md` v1.0 Key Decisions + v1.1 Active requirements
- `.planning/STATE.md` accumulated decisions + BOOTSTRAP corrections
- `BOOTSTRAP_V1.1.md` — source-of-truth scope (with 4 research corrections folded in)
- micromamba-docker ReadTheDocs (via WebSearch 2026-04-21) — Dockerfile multi-stage + MAMBA_DOCKERFILE_ACTIVATE pattern
- `CLAUDE.md` at repo root — project-specific conventions (micromamba env, line-length 100, target Python 3.10)

### Tertiary (LOW confidence — needs plan-phase verification)

- A1: `subsideo.burst.db` fallback API (exact function name for bounds lookup)
- A4: `py-spy dump --pid` macOS SIP interaction on M3 Max (permissions may require sudo)
- A7: Whether `mambaorg/micromamba:latest` (vs a pinned tag) is the right choice for reproducibility

## Metadata

**Confidence breakdown:**
- User Constraints (from CONTEXT.md): HIGH — copied verbatim; all 19 decisions locked
- Standard Stack: HIGH — every version pin verified against PyPI / conda-forge on 2026-04-21 or cross-referenced with STACK.md
- Integration Points (file paths, line numbers): HIGH — every file path exists in the repo and every line range was confirmed via `grep -n` or direct Read
- Architecture patterns: HIGH — every pattern follows v1.0 precedent (`_metadata.py`, `products/types.py`, `config.py`)
- API shapes (`cog_validate`, `get_burst_id_geojson`): HIGH — verified via live Python introspection OR WebFetch of GitHub source
- Watchdog mechanics: HIGH — D-10 to D-14 fully specify; Example 7 is a straightforward translation
- Tests split classification: HIGH — inspected all 5 `test_compare_*.py` files; 4 have threshold assertions (→ `tests/reference_agreement/`) and 1 is pure plumbing (→ stays in `tests/unit/`)
- Common Pitfalls: HIGH — grounded in PITFALLS.md P0.1-P0.4 + M1-M6 (all user-selected in D-13) + research session inspection of current state
- Docker / Apptainer: MEDIUM — example Dockerfile patterns cross-referenced from micromamba-docker docs via WebSearch; exact tag pinning is Open Question 6
- py-spy macOS permissions (A4): LOW — untested on M3 Max; watchdog degrades gracefully if attachment fails

**Research date:** 2026-04-21
**Valid until:** 2026-05-21 (30 days — Phase 1 scope is stable infrastructure). Re-verify PyPI / conda-forge versions if plan-phase slips past this date.
