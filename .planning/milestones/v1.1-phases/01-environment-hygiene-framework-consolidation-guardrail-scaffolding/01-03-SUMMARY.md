---
phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
plan: 03
subsystem: infra

tags: [multiprocessing, macos-fork, env, numpy, cslc, monkey-patch-removal]

# Dependency graph
requires:
  - phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
    provides: "numpy<2 pin (Plan 01-01 conda-env.yml); _cog.py scaffold (Plan 01-02)"
provides:
  - "src/subsideo/_mp.py: idempotent configure_multiprocessing() bundling start method + MPLBACKEND + RLIMIT_NOFILE + forkserver fallback"
  - "configure_multiprocessing() invoked at top of all 5 run_*() product entry points (rtc/cslc/disp/dist/dswx)"
  - "tests/unit/test_mp_helper.py: 6 unit tests covering idempotence, env var precedence, RLIMIT_NOFILE, macOS start method, no-import-side-effect"
  - "Deletion of 4 numpy-2 monkey-patches in products/cslc.py (3 _patch_* functions + np.string_ shim) obsolete under the new numpy<2 pin"
  - "Cleanup of 3 dependent mocker.patch lines in tests/unit/test_cslc_pipeline.py"
affects: [phase-01-04-tophu, phase-01-07-supervisor, phase-02-rtc-eu, phase-03-cslc-selfconsistency, phase-04-disp-adapter, phase-05-dist, phase-06-dswx]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Top-level private module convention (_mp.py following _metadata.py / _cog.py precedent)"
    - "Idempotent global-flag pattern (_CONFIGURED) for one-shot env setup"
    - "Lazy conda-forge imports inside function bodies (resource, requests) for pip-install-without-conda-forge compat"
    - "configure_multiprocessing() inserted as first executable line after docstring in every run_*() entry point"

key-files:
  created:
    - "src/subsideo/_mp.py"
    - "tests/unit/test_mp_helper.py"
  modified:
    - "src/subsideo/products/rtc.py"
    - "src/subsideo/products/cslc.py"
    - "src/subsideo/products/disp.py"
    - "src/subsideo/products/dist.py"
    - "src/subsideo/products/dswx.py"
    - "tests/unit/test_cslc_pipeline.py"
    - ".planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/deferred-items.md"

key-decisions:
  - "Ship the full P0.1 bundle, not just set_start_method('fork') -- research identified 4 additional failure modes (Cocoa/matplotlib, CFNetwork pool, FD-limit 256, joblib/loky forkserver deprecation)"
  - "Use os.environ.setdefault for MPLBACKEND so pre-existing value is honoured (matches unit-test expectation + user-override semantics)"
  - "Guard RLIMIT_NOFILE raise with try/except (OSError, ValueError) -- macOS sandboxed contexts can reject the setrlimit call; log-and-continue rather than crash"
  - "Use contextlib.suppress(Exception) for the requests import seam (ruff SIM105) -- semantically equivalent, ruff-clean"
  - "Deferred import of configure_multiprocessing *inside* every run_*() function (not at module top) -- preserves the pip-install-without-conda-forge import path and matches PATTERNS.md §3.6"
  - "Delete dependent mocker.patch lines in test_cslc_pipeline.py in the same commit as the cslc.py patch removals to keep Task 3 atomic"

patterns-established:
  - "macOS fork bundle: any process that invokes subprocess / multiprocessing / matplotlib should call configure_multiprocessing() as its first line"
  - "Idempotence via global _CONFIGURED flag: second call short-circuits so mp.set_start_method (which would raise without force=True override) is never re-entered"
  - "ENV-04 insertion idiom: # ENV-04 comment -> deferred import -> configure_multiprocessing() -> blank line -> existing body"

requirements-completed: [ENV-02, ENV-04]

# Metrics
duration: ~12min
completed: 2026-04-22
---

# Phase 1 Plan 3: macOS fork bundle + numpy-2 patch removal Summary

**Full D-14 multiprocessing bundle (start method + MPLBACKEND=Agg + RLIMIT_NOFILE + forkserver fallback) in src/subsideo/_mp.py, invoked at top of every run_*() entry point; 4 obsolete numpy-2 monkey-patches deleted from cslc.py now that numpy<2 is pinned.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-22T20:25:00Z
- **Completed:** 2026-04-22T20:37:17Z
- **Tasks:** 3
- **Files created:** 2
- **Files modified:** 7

## Accomplishments

- Landed ENV-04: `src/subsideo/_mp.py` with the full P0.1-preventing bundle (start method + MPLBACKEND=Agg + RLIMIT_NOFILE + requests seam + forkserver fallback on Python >=3.14), idempotent via a module-level `_CONFIGURED` flag
- All 5 product entry points (`run_rtc`, `run_cslc`, `run_disp`, `run_dist`, `run_dswx`) now invoke `configure_multiprocessing()` as their first executable line
- Landed ENV-02: deleted `_patch_compass_burst_db_none_guard`, `_patch_s1reader_numpy2_compat`, `_patch_burst_az_carrier_poly` (201-line deletion) plus the inline `np.string_ = np.bytes_` shim from `cslc.py` — the numpy<2 pin from Plan 01-01 makes all four workarounds obsolete
- Cleaned up 3 dependent `mocker.patch` lines in `tests/unit/test_cslc_pipeline.py`
- `rg '_patch_' src/subsideo/products/` returns zero hits (ENV-02 acceptance)
- 6 new unit tests covering idempotence, env var precedence, RLIMIT_NOFILE raise, macOS start method, no-import-side-effect

## Task Commits

Each task was committed atomically:

1. **Task 1: Create `_mp.py` with idempotent full bundle** — `2299b9d` (feat)
2. **Task 2: Insert `configure_multiprocessing` into 5 `run_*()` entry points** — `b161808` (feat)
3. **Task 3: Delete 4 monkey-patches from `cslc.py` + test `mocker.patch` cleanup** — `fea7930` (refactor)

## Files Created/Modified

### Created

- **`src/subsideo/_mp.py` (94 lines)** — idempotent `configure_multiprocessing()` bundling MPLBACKEND=Agg + RLIMIT_NOFILE + requests seam + forkserver-fallback start method; lazy `resource`/`requests` imports inside function body for pip-install-without-conda-forge compat.
- **`tests/unit/test_mp_helper.py` (78 lines)** — 6 unit tests: MPLBACKEND default, MPLBACKEND honoured when pre-set, RLIMIT_NOFILE raise, macOS fork start method, idempotence, no-import-side-effect.

### Modified

- **`src/subsideo/products/rtc.py`** — inserted `configure_multiprocessing()` at top of `run_rtc` (line 207, immediately after docstring, before `cfg = RTCConfig(...)`). 01-02's `from subsideo._cog import ...` imports inside `ensure_cog` (line 102) and `validate_rtc_product` (line 141) preserved.
- **`src/subsideo/products/cslc.py`** — inserted `configure_multiprocessing()` at top of `run_cslc` (line 364); deleted 3 `_patch_*` function definitions (181 lines) and the inline `np.string_ = np.bytes_` shim; module docstring rewritten to reference the numpy<2 sunset condition instead of the deleted patch names; file size dropped from 628 LOC to 427 LOC.
- **`src/subsideo/products/disp.py`** — inserted `configure_multiprocessing()` at top of `run_disp` (line 447, before `_validate_cds_credentials`).
- **`src/subsideo/products/dist.py`** — inserted `configure_multiprocessing()` at top of `run_dist` (line 161, before `output_dir.mkdir(...)`). 01-02's `from subsideo._cog import cog_validate` (line 44) preserved.
- **`src/subsideo/products/dswx.py`** — inserted `configure_multiprocessing()` at top of `run_dswx` (line 589). 01-02's `from subsideo._cog import ...` routes (lines 503, 536) preserved.
- **`tests/unit/test_cslc_pipeline.py`** — removed 3 `mocker.patch("subsideo.products.cslc._patch_*")` lines and their comment (4 lines deleted). Remaining 6 tests still pass.
- **`.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/deferred-items.md`** — added "Discovered in Plan 01-03" section documenting the 2 pre-existing scope-boundary issues surfaced (ruff violations in products/*.py, mypy stub gap for requests).

## Decisions Made

- **Full D-14 bundle, not a partial fork-only fix** — research identified 4 failure modes beyond `set_start_method('fork')` (Cocoa/matplotlib state corruption, CFNetwork HTTPS pool corruption, FD-limit 256, joblib/loky forkserver deprecation). The BOOTSTRAP_V1.1.md draft mentioned only the first, but STATE.md and CONTEXT.md D-14 mandate the full bundle. Implemented per D-14.
- **`os.environ.setdefault("MPLBACKEND", "Agg")`** — user-override semantics: if the caller (e.g. a debugger session) has already set `MPLBACKEND=Qt5Agg`, respect it. Unit test `test_honours_existing_mplbackend` pins this behavior.
- **Guarded `setrlimit` with `try/except (OSError, ValueError)` + loguru warn** — macOS sandboxed contexts (some CI runners, some entitlement configurations) reject the setrlimit call. Log-and-continue rather than crash; the plan explicitly wanted this safety net per `deviation rules Rule 2`.
- **`contextlib.suppress(Exception)` for requests seam** — ruff SIM105 preferred. Semantic equivalent of `try/except/pass`, ruff-clean.
- **Deferred import of `configure_multiprocessing` inside the function body** — PATTERNS.md §3.6 mandates this to preserve `pip install subsideo` (no conda-forge stack) compatibility. A module-top import would pay the import cost even when running `pytest tests/unit/` without subsideo's heavy deps.
- **Delete mocker.patch lines in the same commit as the cslc.py patch removals** — keeps Task 3 atomic. Running the tests between Task 2 (insertion) and Task 3 (patch deletion) would cause a transient red state where `test_run_cslc_mocked` references `_patch_*` attributes that no longer exist. Combining avoids that window.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `ruff SIM105` rejected `try/except/pass` for the requests seam**
- **Found during:** Task 1 (initial ruff check on `_mp.py`)
- **Issue:** ruff 0.x enforces SIM105 (prefer `contextlib.suppress(Exception)` over `try/except/pass`). The research template used the older `try/except/pass` idiom.
- **Fix:** Added `import contextlib` at module top and replaced the 4-line `try/except/pass` block with `with contextlib.suppress(Exception): import requests  # noqa: F401`. Semantic equivalent; no behavior change.
- **Files modified:** `src/subsideo/_mp.py`
- **Verification:** `ruff check src/subsideo/_mp.py` passes; all 6 unit tests still pass.
- **Committed in:** `2299b9d` (Task 1 commit)

**2. [Rule 3 - Blocking] `ruff format` wanted blank lines around `from __future__ import annotations`**
- **Found during:** Task 1 (ruff format --check)
- **Issue:** ruff format enforces a blank line between the module docstring and `from __future__ import annotations` (no such constraint in the research template).
- **Fix:** Ran `ruff format src/subsideo/_mp.py tests/unit/test_mp_helper.py` — formatter added a blank line after the closing `"""` of the docstring in both files.
- **Files modified:** `src/subsideo/_mp.py`, `tests/unit/test_mp_helper.py`
- **Verification:** `ruff format --check` passes.
- **Committed in:** `2299b9d` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 Blocking — lint-tooling)
**Impact on plan:** Cosmetic fixes to satisfy the project's ruff configuration. No behavior change. No scope creep.

## Issues Encountered

- **Pre-existing test failures in `tests/unit/test_disp_pipeline.py` (`test_run_disp_mocked`, `test_run_disp_qc_warning`)** — verified pre-existing by `git stash && pytest <tests> && git stash pop`. Both tests were already failing on Plan 01-02's finish state before any 01-03 edits. Already logged in `deferred-items.md` by Plan 01-02; no new entry required.
- **Pre-existing `ruff I001` import-ordering violations in all 5 products/*.py files (31 total)** — verified pre-existing. Out of Plan 01-03 scope (the plan modifies `run_*()` bodies, not the import blocks). Logged in `deferred-items.md` under "Discovered in Plan 01-03".
- **Pre-existing `mypy` missing-stub error for `requests` in `src/subsideo/data/ionosphere.py:7`** — `_mp.py:75` now inherits the same error, but the root cause is a typeshed-gap that exists independent of Plan 01-03. Out of scope; logged in `deferred-items.md`.

## Self-Check

Verifying claims before proceeding.

### Files exist

- `src/subsideo/_mp.py` — FOUND
- `tests/unit/test_mp_helper.py` — FOUND
- `.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/01-03-SUMMARY.md` — FOUND (being written)

### Commits exist

- `2299b9d` (feat(01-03): add _mp.py macOS fork bundle) — FOUND
- `b161808` (feat(01-03): invoke configure_multiprocessing() at top of all 5 run_*() entry points) — FOUND
- `fea7930` (refactor(01-03): delete 4 numpy-2 monkey-patches from cslc.py) — FOUND

### Invariant checks

- `rg '_patch_' src/subsideo/products/` returns 0 hits — PASS
- `rg 'np\.string_\s*=\s*np\.bytes_' src/subsideo/products/` returns 0 hits — PASS
- `rg 'from subsideo\._mp import configure_multiprocessing' src/subsideo/products/` returns 5 hits — PASS
- `rg '^\s*configure_multiprocessing\(\)' src/subsideo/products/` returns 5 hits — PASS
- `from subsideo.products import rtc, cslc, disp, dist, dswx` — succeeds — PASS
- `from subsideo._mp import configure_multiprocessing; configure_multiprocessing(); configure_multiprocessing()` — idempotent — PASS
- `pytest tests/unit/test_mp_helper.py` — 6 passed — PASS
- `pytest tests/unit/test_cslc_pipeline.py` — 6 passed — PASS
- Plan 01-02's `from subsideo._cog import` routes in products/{rtc,dist,dswx}.py still present — PASS (5 hits confirmed)

## Self-Check: PASSED

## User Setup Required

None — no external service configuration required. The macOS fork bundle operates entirely within the interpreter's state and the user's own filesystem (RLIMIT_NOFILE).

## Next Phase Readiness

- ENV-04 boundary is in place: any eval script calling `products.<product>.run_<product>()` now gets the full P0.1 bundle before any subprocess, multiprocessing, or matplotlib work begins.
- Plan 01-07 (supervisor, Wave 3) can rely on `configure_multiprocessing` being in place when it wraps eval-script subprocesses.
- ENV-02 is closed: monkey-patches gone, numpy<2 pin in conda-env.yml.
- Plan 01-04 (tophu conda-forge) is the next wave-2 deliverable; independent of 01-03 outputs but shares the same environment footprint.

---
*Phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding*
*Completed: 2026-04-22*
