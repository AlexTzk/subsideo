---
phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
plan: 02
subsystem: infra
tags: [rio-cogeo, cog, geotiff, lazy-imports, ifd-offset, p0.3, env-03]

# Dependency graph
requires:
  - phase: 01-01
    provides: "conda-env.yml pins rio-cogeo==6.0.0 (two-layer env manifest with numpy<2 + tophu + dist-s1 + py-spy); osx-arm64 env solves cleanly"
provides:
  - "Single-file routing module src/subsideo/_cog.py for all rio_cogeo calls (version-drift-safe upgrade point)"
  - "ensure_valid_cog(path) heal helper fixes P0.3 silent COG degradation after metadata tag writes"
  - "cog_validate returns the full (is_valid, errors, warnings) triple with warnings surfaced via loguru"
  - "Removed dist.py rio_cogeo >= 7.0 try/except API-move ladder (now dead code under the 6.0.0 pin)"
affects:
  - "every future rio-cogeo major upgrade (single-file change in _cog.py)"
  - "Plan 01-10 matrix-writer threshold echo (uses cog_validate for COG sidecars)"
  - "Phase 2 RTC EU reproducibility runs (ensure_cog now auto-heals via ensure_valid_cog)"
  - "Phase 5 DIST validation cycle (validate_dist_product routes through _cog without API-move fragility)"
  - "Phase 6 DSWx recalibration runs (_validate_dswx_product + COG writer route through _cog)"

# Tech tracking
tech-stack:
  added: [] # all tech was already pinned in Plan 01-01 (rio-cogeo==6.0.0)
  patterns:
    - "Version-aware shim pattern: module-top stdlib+loguru only; rio_cogeo imports deferred inside function bodies so pip-only consumers import cleanly"
    - "Heal-after-write pattern: ensure_valid_cog(path) called immediately after any rasterio ds.update_tags(...) to recertify the COG layout"
    - "cog_profiles as a callable wrapper (not a module-level dict attribute) — callers do cog_profiles().get('deflate') to enforce the lazy-import discipline"

key-files:
  created:
    - "src/subsideo/_cog.py (111 LOC) — 5 public names: cog_validate, cog_translate, cog_profiles, ensure_valid_cog, RIO_COGEO_VERSION"
    - "tests/unit/test_cog_helper.py (181 LOC) — 7 unit tests covering lazy-import, version probe, warning surface, IFD-in-warnings heal, IFD-in-errors heal, non-healable-error raise, no-op-on-valid"
    - ".planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/deferred-items.md — 4 pre-existing issues logged (DISP test fixture, 2 ruff violations, 1 mypy type-arg, 5 unrelated unit failures)"
  modified:
    - "src/subsideo/_metadata.py — _inject_geotiff now routes through subsideo._cog.ensure_valid_cog; re-translate is conditional, not every-time"
    - "src/subsideo/products/rtc.py — ensure_cog + validate_rtc_product route through _cog; ensure_valid_cog called post-translate"
    - "src/subsideo/products/dist.py — rio_cogeo >= 7.0 try/except ladder removed; cog_validate routes through _cog"
    - "src/subsideo/products/dswx.py — COG writer + _validate_dswx_product route through _cog"
    - "tests/unit/test_rtc_pipeline.py — autouse fixture updated to mock rio_cogeo.cogeo.{cog_validate,cog_translate} + rio_cogeo.__version__"

key-decisions:
  - "IFD-offset signals land in the errors list (not warnings) under rio-cogeo 6.0.0 — ensure_valid_cog heals on IFD/offset/layout substrings in EITHER list; non-IFD errors still raise RuntimeError"
  - "cog_profiles() is a lazy-import accessor function, not a dict constant — callers must invoke with () to preserve pip-only install compatibility"
  - "dist.py 7.0 API-move try/except ladder deleted (not preserved) — the 6.0.0 conda-forge pin from 01-01 is the contract; any future upgrade is a single-file _cog.py edit"

patterns-established:
  - "Leading-underscore top-level private module: _cog.py follows the _metadata.py precedent (docstring, from __future__ import annotations, loguru logger, lazy conda-forge imports)"
  - "Three-tuple cog_validate surface (bool, list[str], list[str]) with warnings logged at warning level and returned verbatim — no swallowing"
  - "ensure_valid_cog(path) is idempotent on already-valid COGs (mtime unchanged) and heals only on IFD/offset/layout signals — no re-translate loops"

requirements-completed: [ENV-03]

# Metrics
duration: ~23min
completed: 2026-04-22
---

# Phase 01 Plan 02: rio_cogeo Centralisation & P0.3 COG-Heal Summary

**Single-file rio_cogeo routing via `subsideo._cog` — centralises 10+ import sites, surfaces IFD-offset warnings, and re-translates broken COGs in place after metadata tag writes (ENV-03 + PITFALLS P0.3 fix).**

## Performance

- **Duration:** ~23 min
- **Started:** 2026-04-22T19:55:00Z (approx)
- **Completed:** 2026-04-22T20:18:31Z
- **Tasks:** 2 tasks completed (both autonomous)
- **Files modified:** 8 (2 created + 6 modified across src/, tests/, .planning/)
- **Commits:** 5 atomic commits

## Accomplishments

- `src/subsideo/_cog.py` is now the single routing module for every `rio_cogeo` call in `src/`; `rg 'from rio_cogeo|import rio_cogeo' src/` returns hits only within `_cog.py`, all inside function bodies (lazy-import discipline preserved).
- `ensure_valid_cog(path)` wired into every metadata-injection path (`_metadata._inject_geotiff`, `products/rtc.py::ensure_cog`, `products/dswx.py::_write_dswx_cog`) — a broken-layout COG is transparently re-translated in place instead of silently degrading.
- `dist.py` 7.0 API-move `try/except ImportError` ladder deleted (10 lines of dead code gone under the 6.0.0 pin locked in Plan 01-01).
- **7 unit tests** (up from the plan's 6 target) cover the warning surface, both the IFD-in-warnings and IFD-in-errors heal paths, the lazy-import-without-rio-cogeo contract, and the non-healable-error raise path. All pass.
- 44 related unit tests pass across `test_cog_helper.py + test_metadata.py + test_rtc_pipeline.py + test_dist_pipeline.py + test_dswx_pipeline.py`.

## Task Commits

Each task was committed atomically:

1. **Task 1 (TDD): Create `_cog.py` with warning surface + IFD-offset heal path**
   - RED: `de1f1b5` — `test(01-02): add failing tests for _cog helper module`
   - GREEN: `9dc6ccc` — `feat(01-02): add _cog.py wrapper with IFD-offset heal path (ENV-03)`
   - FIX (Rule 1): `775530a` — `fix(01-02): treat rio_cogeo IFD/layout errors as heal-triggering (Rule 1)`

2. **Task 2: Rewrite all rio_cogeo import sites through `_cog` + drop dist.py try/except ladder + insert `ensure_valid_cog` post-tag**
   - `0434b2f` — `refactor(01-02): route all rio_cogeo imports through subsideo._cog (ENV-03)`

3. **Docs: expanded deferred-items with pre-existing suite failures**
   - `a3ecf1a` — `docs(01-02): expand deferred-items with pre-existing test failures`

## Files Created/Modified

### Created

- `src/subsideo/_cog.py` (111 LOC) — Version-aware wrapper around rio-cogeo 6.0.0. Exports `cog_validate`, `cog_translate`, `cog_profiles`, `ensure_valid_cog`, `RIO_COGEO_VERSION`. All `rio_cogeo` imports deferred inside function bodies.
- `tests/unit/test_cog_helper.py` (181 LOC) — 7 unit tests:
  - `test_imports_without_rio_cogeo_installed` — the module is importable under pip-only (no conda-forge).
  - `test_rio_cogeo_version_tuple` — 3-int tuple with major==6.
  - `test_cog_validate_returns_triple` — `(bool, list[str], list[str])` triple shape.
  - `test_ensure_valid_cog_noop_on_valid` — mtime unchanged on a valid COG.
  - `test_ensure_valid_cog_heals_warning` — IFD signal in warnings triggers re-translate.
  - `test_ensure_valid_cog_heals_ifd_error` — IFD signal in errors ALSO triggers re-translate (added after Rule 1 discovery).
  - `test_ensure_valid_cog_raises_on_non_healable_error` — non-IFD errors raise RuntimeError instead of silently healing.
- `.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/deferred-items.md` — Four pre-existing issues documented (1 test fixture, 2 ruff, 1 mypy, 5 unrelated suite failures).

### Modified

- `src/subsideo/_metadata.py` — `_inject_geotiff` now imports `ensure_valid_cog` from `subsideo._cog`; the unconditional re-translate-via-cog_translate loop is replaced with a conditional `ensure_valid_cog(path)` call after `ds.update_tags(**metadata)`. Behavior: still re-translates when IFD layout breaks (the common case after tag write), but no-ops on already-valid files.
- `src/subsideo/products/rtc.py` — `ensure_cog` (line 84) and `validate_rtc_product` (line 120) route through `from subsideo._cog import ...`; `ensure_valid_cog(output_cog)` called as the final step of `ensure_cog` before return.
- `src/subsideo/products/dist.py` — 10-line try/except ladder at lines 44-49 deleted; replaced with `from subsideo._cog import cog_validate`. Docstring reference updated to cite `subsideo._cog.cog_validate`.
- `src/subsideo/products/dswx.py` — Two import sites (COG writer at line 503, `_validate_dswx_product` at line 533) route through `_cog`; `ensure_valid_cog(output_path)` inserted after `cog_translate(...)` in the COG writer path.
- `tests/unit/test_rtc_pipeline.py` — `_mock_rio_cogeo` autouse fixture updated to populate `rio_cogeo.cogeo.cog_validate` + `rio_cogeo.cogeo.cog_translate` + `rio_cogeo.__version__='6.0.0'` so the `_cog`-routed imports find the mock. The legacy `rio_cogeo.cog_validate` mock is preserved for any straggler callers.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] rio-cogeo 6.0.0 reports IFD-offset signals as ERRORS (not WARNINGS)**

- **Found during:** Task 2, the first `pytest tests/unit/test_metadata.py` run after the `_metadata.py` rewrite.
- **Issue:** The plan's research template and the original `ensure_valid_cog` implementation assumed rio-cogeo 6.0.0 reports IFD-offset-past-header and broken-layout signals in the `warnings` list. Empirical testing against rio-cogeo 6.0.0 on a tiny 4×4 GeoTIFF + a tagged COG showed those signals land in the `errors` list with `is_valid=False`.
- **Effect if not fixed:** `ensure_valid_cog(path)` would raise `RuntimeError` on exactly the files it was designed to heal — `test_writes_tags` in `test_metadata.py` failed with `RuntimeError: ... not a valid COG: ['The offset of the main IFD should be < 300. It is 382 instead', ...]`. This is the literal opposite of the P0.3 fix.
- **Fix:** `ensure_valid_cog` now inspects `[*errors, *warnings]` for substrings `"ifd"|"offset"|"layout"` and re-translates on match; only non-IFD errors still raise. Two new unit tests (`test_ensure_valid_cog_heals_ifd_error` + `test_ensure_valid_cog_raises_on_non_healable_error`) lock the behaviour in.
- **Files modified:** `src/subsideo/_cog.py`, `tests/unit/test_cog_helper.py`.
- **Commit:** `775530a fix(01-02): treat rio_cogeo IFD/layout errors as heal-triggering (Rule 1)`.
- **Rationale for auto-fix:** Pure bug fix — the plan's goal is "re-translate a COG in place when an IFD-layout warning is present"; rio-cogeo 6.0.0 calls the same condition an error. Fixing this inline preserves the plan's intent.

**2. [Rule 1 - Bug] test_rtc_pipeline.py autouse fixture did not mock the rio_cogeo.cogeo path**

- **Found during:** Task 2, `pytest test_rtc_pipeline.py` run after the rtc.py rewrite.
- **Issue:** The existing fixture mocked `rio_cogeo.cog_validate` (the old path the codebase used pre-01-02) but did not populate `rio_cogeo.cogeo.cog_validate` or `rio_cogeo.cogeo.cog_translate`. My new `_cog.py` imports from `rio_cogeo.cogeo` — the fixture resolved to a bare MagicMock which unpacked to `()`, breaking `is_valid, errors, warnings = _impl(...)`.
- **Fix:** Fixture now populates both `rio_cogeo.cog_validate.cog_validate` and `rio_cogeo.cogeo.{cog_validate,cog_translate}`; adds `rio_cogeo.__version__='6.0.0'` so the `_get_version()` probe can parse it without hitting the real package during the unit run.
- **Files modified:** `tests/unit/test_rtc_pipeline.py`.
- **Commit:** `0434b2f refactor(01-02): route all rio_cogeo imports through subsideo._cog (ENV-03)`.
- **Rationale for auto-fix:** Test infrastructure must track the `_cog`-routed import path or the migration is not observationally complete. Updating the fixture is the minimum-diff fix and keeps the tests meaningful.

### Deferred (Out of Scope, Pre-Existing)

The full unit suite has 6 failing tests on the current env — none introduced by 01-02. All documented in `.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/deferred-items.md` with verification that they pre-exist `a0b9590` (Plan 01-01 finish state):

- `test_metadata_wiring.py::TestMetadataInjectionInDISP::test_run_disp_calls_inject_opera_metadata` — DISP run produces no `velocity.tif` under mocked fixtures; DISP pipeline issue, not COG.
- `test_compare_dswx.py::{TestJrcTileUrl::test_url_format, TestBinarizeDswx::test_class_mapping}` — JRC URL format + DSWx class mapping.
- `test_disp_pipeline.py::{test_run_disp_mocked, test_run_disp_qc_warning}` — DISP pipeline fixture drift.
- `test_orbits.py::TestFetchOrbit::test_fallback_to_s1_orbits` — s1-orbits fallback path.

Also pre-existing (documented but unfixed): ruff I001 in `products/rtc.py`, ruff F401 in `products/dswx.py:452` (`from_bounds` unused), mypy type-arg missing in `_metadata.py:29`.

## Authentication Gates

None. This plan is pure codebase refactor — no external credential interaction.

## Known Stubs

None. The `_cog.py` module has no placeholder values, no hardcoded empties that flow to UI, and no TODO/FIXME/coming-soon markers. `cog_profiles()` is a wrapper (not a stub) — it returns the real rio_cogeo registry.

## Threat Model Compliance

The plan's `<threat_model>` assigns `mitigate` dispositions to:
- **T-02-01** Silent COG degradation → fixed via `ensure_valid_cog(path)` called post-tag in every metadata-injection path (`_metadata.py:79`, `rtc.py:115`, `dswx.py:518`).
- **T-02-02** Warnings swallowed → `cog_validate` returns the 3-tuple explicitly (`(is_valid, errors, warnings)`); `loguru.logger.warning` fires when warnings non-empty (`_cog.py:55`).
- **T-02-03** Hidden rio_cogeo version drift → `RIO_COGEO_VERSION()` exposed for runtime assertions; the `==6.0.0` pin in conda-env.yml (Plan 01-01) is the contract.
- **T-02-04** Re-translate loop if heal fails → accepted; `ensure_valid_cog` re-translates at most once, no feedback loop.

No new threat surface introduced (the threat_flags section is intentionally omitted — the refactor consolidates existing surface, it does not expand it).

## TDD Gate Compliance

Task 1 followed the RED/GREEN/REFACTOR cycle:

- **RED:** `de1f1b5 test(01-02): add failing tests for _cog helper module` — 5 tests fail with `ModuleNotFoundError: No module named 'subsideo._cog'`, confirmed pre-implementation.
- **GREEN:** `9dc6ccc feat(01-02): add _cog.py wrapper with IFD-offset heal path (ENV-03)` — all 5 tests pass after `_cog.py` creation.
- **REFACTOR:** No cleanup commit was needed — the module was clean on first pass. A follow-up `fix` commit (`775530a`) addressed the Rule 1 IFD-in-errors bug discovered downstream during Task 2 integration, and added 2 new regression tests.

Task 2 did not require TDD — it is a pure refactor of existing callers; the behavior is covered by `test_metadata.py` + `test_rtc_pipeline.py` + `test_dist_pipeline.py` + `test_dswx_pipeline.py` which all pass after the migration.

## Self-Check: PASSED

- Created files exist: `src/subsideo/_cog.py` ✓, `tests/unit/test_cog_helper.py` ✓, `.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/deferred-items.md` ✓.
- All commit hashes present in `git log --all`: `de1f1b5`, `9dc6ccc`, `775530a`, `0434b2f`, `a3ecf1a` — all 5 FOUND.
- Acceptance counts: 0 external rio_cogeo imports ✓, 6 `subsideo._cog` routing imports ✓ (≥4), 8 `ensure_valid_cog` references across 4 files ✓, 0 `rio_cogeo >= 7` comments ✓.
- rio_cogeo 6.0.0 version probe: `RIO_COGEO_VERSION() == (6, 0, 0)` ✓.
- Test suite: 44 related unit tests pass (`test_cog_helper` + `test_metadata` + `test_rtc_pipeline` + `test_dist_pipeline` + `test_dswx_pipeline`).
