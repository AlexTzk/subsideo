# Phase 1: Environment Hygiene, Framework Consolidation & Guardrail Scaffolding - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
**Areas discussed:** criteria.py API & immutability; Split ValidationResult strategy; Watchdog mechanics; Env & reproducibility recipe

---

## Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| criteria.py API & immutability | Dataclass vs NamedTuple vs module constants; grouping; `binding_after_milestone` encoding; immutability enforcement | ✓ |
| Split ValidationResult strategy | How to split `*ValidationResult` into `ProductQualityResult` + `ReferenceAgreementResult`: nesting, location, back-compat | ✓ |
| Watchdog mechanics | Throughput heuristic, wall-time source, scope (per-stage vs per-script), abort diagnostics | ✓ |
| Env & reproducibility recipe | conda-env.yml shape, lockfile format, container (Dockerfile vs Apptainer), platform matrix | ✓ |

**User's choice:** All four areas selected (multiSelect).
**Notes:** Max-effort session; user opted for full discussion depth.

---

## criteria.py API & immutability

### Q1 — Primary container shape

| Option | Description | Selected |
|--------|-------------|----------|
| Frozen dataclass (Recommended) | `@dataclass(frozen=True) class Criterion: name, threshold, comparator, type, binding_after_milestone, rationale`. Matches existing `products/types.py` pattern; `frozen=True` blocks mutation; easy to hash for drift checks. | ✓ |
| Pydantic v2 model | Richer validation, JSON-serialisable; heavier; overkill for static constants. | |
| NamedTuple | Lightest, immutable by default; extensibility awkward (positional defaults); less Grep-friendly. | |
| Plain module constants | `RTC_RMSE_DB_MAX = 0.5` + separate `CALIBRATING_BINDS` dict; matrix writer can't iterate structurally. | |

**User's choice:** Frozen dataclass (Recommended).

### Q2 — Grouping / access

| Option | Description | Selected |
|--------|-------------|----------|
| Flat REGISTRY + typed accessors (Recommended) | `CRITERIA: dict[str, Criterion]` for iteration, plus typed accessor functions for call-site readability. Hybrid. | ✓ |
| Per-product namespace classes | `class RTC: RMSE_DB_MAX = Criterion(...)`; iteration needs `vars()` introspection. | |
| Flat dict only | Pure `CRITERIA['rtc.rmse_db_max']`; string-keyed everywhere; no type-checker help. | |
| Per-product sub-modules | `criteria/rtc.py`, `criteria/cslc.py`, etc.; fragmentation at v1.1 scale. | |

**User's choice:** Flat REGISTRY + typed accessors (Recommended).

### Q3 — Immutability enforcement + drift visibility

| Option | Description | Selected |
|--------|-------------|----------|
| frozen=True + matrix echo + PR review (Recommended) | Runtime frozen dataclass blocks mutation; matrix_writer prints criterion alongside value (drift produces visible matrix.md git diff); PR review policy for edits. No extra CI. | ✓ |
| Module-hash unit test | `tests/product_quality/test_criteria_hash.py` asserts SHA; annoying on legit edits. | |
| CODEOWNERS + pre-commit hook | Process-heavy for solo-dev project. | |
| Runtime immutability only | `frozen=True` and nothing else; no drift-visibility mechanism. | |

**User's choice:** frozen=True + matrix echo + PR review (Recommended).

### Q4 — Phase 1 scope of criteria.py (multiSelect)

| Option | Description | Selected |
|--------|-------------|----------|
| All v1.0 criteria that exist today (BINDING) | RTC RMSE/r, CSLC amplitude r/RMSE, DISP r/bias, DIST F1/accuracy, DSWx F1. All currently hardcoded; extract to criteria.py. | ✓ |
| Phase-3-needed new CALIBRATING gates | CSLC self-consistency coherence > 0.7, residual < 5 mm/yr; DISP self-consistency same pair. CALIBRATING with `binding_after_milestone='v1.2'`. | ✓ |
| Phase-5-needed DIST/DSWx calibrating placeholders | EFFIS precision/recall; DSWx recalibration F1 re-affirmation. | |
| Matrix-writer metadata criteria | CALIBRATING visual distinguishability + binding-after-milestone enforcement rules. | |

**User's choice:** v1.0 BINDING + Phase-3-needed CALIBRATING gates.
**Notes:** Phase 5 additions deferred — Phase 5 adds its own entries when it lands. Matrix-writer metadata rules excluded from criteria.py (they belong in matrix_writer.py — avoids conflating threshold constants with output-shape logic).

---

## Split ValidationResult strategy

### Q1 — Composition shape

| Option | Description | Selected |
|--------|-------------|----------|
| Nested composite (Recommended) | `CSLCValidationResult: product_quality: ProductQualityResult, reference_agreement: ReferenceAgreementResult`. One return object, two sub-fields. No top-level `.passed`. | ✓ |
| Sibling returns (tuple) | `-> tuple[ProductQualityResult, ReferenceAgreementResult]`; awkward for JSON serialisation. | |
| Single generic with kind discriminator | `ValidationResult: kind, metrics, criteria_ids`. Loses per-product type safety. | |
| Keep per-product shape, just rename fields | Minimal churn; doesn't structurally prevent `.passed` re-emergence. | |

**User's choice:** Nested composite (Recommended).

### Q2 — Location

| Option | Description | Selected |
|--------|-------------|----------|
| New `validation/results.py` module (Recommended) | Clean home next to compare_*.py; no import cycle; per-product types stay in `products/types.py` but compose with new generic types. | ✓ |
| Extend `products/types.py` | Single file for all result types; mixes validation-specific with pipeline orchestration types. | |
| Inside `validation/criteria.py` | Conflates data-output shapes with threshold constants. | |
| Per compare_*.py module | 5 near-identical class definitions; matrix writer needs per-product special-casing. | |

**User's choice:** New `validation/results.py` module (Recommended).

### Q3 — `pass_criteria` shape

| Option | Description | Selected |
|--------|-------------|----------|
| Named fields with criterion IDs (Recommended) | Store `measurements: dict[str, float]` + `criterion_ids: list[str]`; pass/fail computed at read time via `evaluate(result, criteria)` — never stored as bool. Drift-safe against criteria.py edits. | ✓ |
| Keep `pass_criteria: dict[str, bool]` | Stores stale bools that diverge from updated criteria.py. | |
| Both — measurements + pre-computed bools | Redundant but preserves historical truth in metrics.json. | |
| Just the measurements | No criterion provenance in the result. | |

**User's choice:** Named fields with criterion IDs (Recommended).

### Q4 — Migration approach

| Option | Description | Selected |
|--------|-------------|----------|
| Big-bang in Phase 1 (Recommended) | Single commit replaces all 5 per-product ValidationResult types + all 5 compare_*.py returns + all tests. Fail-fast; no dual API. | ✓ |
| Adapter shim during Phase 1, remove in Phase 2 | Dual API risk (M2 conflation). | |
| Defer migration to Phase 2 | Blocks RTC EU until v1.0 migrated. | |
| Per-product migration across phases | Fragments the contract; partial migration means matrix sees two shapes. | |

**User's choice:** Big-bang in Phase 1 (Recommended).

---

## Watchdog mechanics

### Q1 — Throughput heuristic

| Option | Description | Selected |
|--------|-------------|----------|
| Output-dir mtime staleness (Recommended) | Poll cache_dir mtime recursively every 30s; abort if no change for 120s grace AND wall > 2× expected. | ✓ |
| Log-line absence | Parse stdout for any log; dist_s1 legitimately quiet during despeckle — false-positive risk. | |
| Explicit heartbeat API | Requires editing every stage; brittle. | |
| Combined mtime + log fallback | Fewer false-positives; ~20 extra LOC. | |

**User's choice:** Output-dir mtime staleness (Recommended).

### Q2 — Expected wall-time source

| Option | Description | Selected |
|--------|-------------|----------|
| Caller-supplied per-script constant (Recommended) | `EXPECTED_WALL_S = 1800` at top of each run_eval_*.py. Script authors own their workload. | ✓ |
| Central registry in criteria.py | Mixes ops with science; contradicts criteria.py structure. | |
| Adaptive from prior runs | Needs warm history; first runs unbounded. | |
| Config flag / CLI override | Adds drift-prone knob. | |

**User's choice:** Caller-supplied per-script constant (Recommended).

### Q3 — Watchdog scope

| Option | Description | Selected |
|--------|-------------|----------|
| Per-script subprocess wrap via Makefile (Recommended) | `python -m subsideo.validation.supervisor run_eval_dist.py`. Process-group kill via `os.killpg`. Clean cross-cell isolation. | ✓ |
| In-process via `_mp.watchdog()` context manager | Can't reliably kill grandchildren; signal handling under multi-threaded isce3 is fragile. | |
| Both — outer subprocess + inner context manager | Belt + braces; ~2× code. | |
| Per-stage subprocess inside eval script | Too granular; per-stage process overhead. | |

**User's choice:** Per-script subprocess wrap via Makefile (Recommended).

### Q4 — Abort behavior + diagnostics

| Option | Description | Selected |
|--------|-------------|----------|
| py-spy dump + SIGTERM→SIGKILL + exit 124 (Recommended) | Capture stacks to `watchdog-stacks.txt` before killing; conventional timeout(1) exit code. py-spy is light pip dep. | ✓ |
| SIGTERM→SIGKILL only, no dump | Fast; learn nothing about where it hung. | |
| Core dump via ulimit + SIGQUIT | Gigantic cores; overkill for Python-level hangs. | |
| Log-only, don't abort | Defeats ENV-05. | |

**User's choice:** py-spy dump + SIGTERM→SIGKILL + exit 124 (Recommended).

---

## Env & reproducibility recipe

### Q1 — conda-env.yml authoring approach

| Option | Description | Selected |
|--------|-------------|----------|
| Two-layer: conda-env.yml + `pip: -e .[validation,viz]` (Recommended) | conda-forge heavies + trailing pip section installs pure-Python layer from pyproject. Single command creates env. | ✓ |
| Single conda-env.yml lists every package | Duplicates pyproject; two sources of drift. | |
| pyproject single source + conda-env.yml generated | Build-time generator; overkill at v1.1. | |
| conda-lock.yml alongside | Research explicitly deferred to v2. | |

**User's choice:** Two-layer: conda-env.yml for binary + `pip: -e .[validation,viz]` (Recommended).

### Q2 — Lockfile format

| Option | Description | Selected |
|--------|-------------|----------|
| Per-platform explicit: linux-64 + osx-arm64 (Recommended) | Two files; bit-for-bit reproducible; platform-specific. | ✓ |
| Single `conda list --explicit` from Linux | Only Linux; no macOS audit trail. | |
| `mamba env export --no-builds` YAML per platform | Human-readable; not strictly reproducible. | |
| Lockfile + hash manifest | CI-integrity extra; Phase 1 doesn't ship CI. | |

**User's choice:** Per-platform explicit: linux-64 + osx-arm64 (Recommended).

### Q3 — Container recipe

| Option | Description | Selected |
|--------|-------------|----------|
| Dockerfile primary + Apptainer derived (Recommended) | `mambaorg/micromamba` base; multi-stage; Apptainer.def auto-derived via `docker-daemon://`. CPU-only. | ✓ |
| Apptainer .def primary (TrueNAS-first) | Cuts off Docker/GHCR/CI consumers. | |
| Both Docker + Apptainer hand-maintained | Double maintenance; drift risk. | |
| `.devcontainer/devcontainer.json` + Dockerfile | Nice-to-have; not blocking. | |

**User's choice:** Dockerfile primary + Apptainer definition generated from it (Recommended).

### Q4 — Platform matrix for 'fresh clone works' (multiSelect)

| Option | Description | Selected |
|--------|-------------|----------|
| linux-64 (TrueNAS) — closure test target | Primary. REL-04 cold-env under 12h. | |
| osx-arm64 (M3 Max) — dev target | Secondary. ENV-04/05 fork-mode bundle targets this. | ✓ |
| osx-x86_64 (Intel Mac) | Nobody uses Intel Macs. | |
| Windows WSL2 | Out of scope. | |

**User's choice:** osx-arm64 only.
**Notes:** This triggered a clarification follow-up — user initially picked only macOS but had also selected "Dockerfile + linux-64 lockfile" earlier. See next Q.

### Q4.1 — Platform intent clarification

| Option | Description | Selected |
|--------|-------------|----------|
| M3 Max validates; Linux artifacts ship unvalidated for Phase 7 (Recommended) | Defers Linux container testing to Phase 7. | |
| Both platforms validated in Phase 1 | Add Linux validation in Phase 1; shrinks Phase 7 risk. | ✓ |
| Only macOS; skip linux-64 lockfile + Dockerfile in Phase 1 | Defer all Linux artifacts. | |
| Only macOS; accept regression risk on Linux | Would break REL-04/REL-06. | |

**User's choice:** Both platforms validated in Phase 1.
**Notes:** Deliberate choice to shrink Phase 7 surprise surface; adds Phase 1 scope.

### Q4.2 — Linux validation mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Docker run on M3 Max (Recommended) | `docker build . && docker run pytest tests/unit tests/integration`. Catches env-create failures at Phase 1. | ✓ |
| TrueNAS Linux dev container smoke test | Real hardware; slower iteration. | |
| Both — Docker first, TrueNAS at Phase 1 close | Belt + braces. | |
| Linux validation acceptance-criterion-only, mechanism TBD at plan-phase | Defer decision. | |

**User's choice:** Docker run on M3 Max (Recommended).
**Notes:** Phase 7 TrueNAS cold-env `make eval-all` audit still happens separately.

---

## More gray areas check

| Option | Description | Selected |
|--------|-------------|----------|
| Tests split migration scope | How to migrate existing tests into product_quality/ vs reference_agreement/. | |
| Makefile orchestration depth | Per-burst targets, parallelism, Python orchestrator depth. | |
| `metrics.json` + `meta.json` sidecar schema | Single vs two files; hash scope; schema versioning. | |
| I'm ready for CONTEXT.md | Enough captured; remaining details are Claude's discretion. | ✓ |

**User's choice:** I'm ready for CONTEXT.md.

---

## Claude's Discretion

Recorded in CONTEXT.md `<decisions>` §Claude's Discretion:
- Tests split migration scope
- Makefile orchestration depth
- `metrics.json` + `meta.json` sidecar schema split
- `_cog.py` API details
- `harness.py` per-source retry policy encoding
- Pilot eval for harness migration (`run_eval.py`)

## Deferred Ideas

Recorded in CONTEXT.md `<deferred>`:
- Per-burst Makefile target granularity
- `make -j` parallelism
- Adaptive wall-time from prior run history
- `conda-lock` pinning
- Matrix-writer drift unit test
- Per-product test subdirectories
- `.devcontainer/devcontainer.json` for VS Code
- CUDA layer in Dockerfile
- Per-source `tenacity` retry library adoption
- Matrix-writer CALIBRATING-cell visual rendering
- Phase 5 EFFIS + DSWx recalibration criterion placeholders
