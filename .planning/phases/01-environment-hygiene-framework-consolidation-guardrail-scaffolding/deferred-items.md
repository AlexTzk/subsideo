# Deferred Items — Phase 01

Out-of-scope issues surfaced during plan execution. Each entry notes the
plan that encountered the issue, the file/test, and the reason for
deferral. These are NOT bugs introduced by the plan; they are pre-existing
issues that should be fixed by the plan most-directly responsible.

## Discovered in Plan 01-02

### DISP metadata-wiring unit test fails before and after 01-02 changes

- **Test:** `tests/unit/test_metadata_wiring.py::TestMetadataInjectionInDISP::test_run_disp_calls_inject_opera_metadata`
- **Failure mode:** `DISPResult.valid is False` because the dolphin run produces no `velocity.tif` under the test's mocked fixtures; the test harness is out-of-date with `subsideo.products.disp.run_disp`'s current path resolution.
- **Verified pre-existing:** `git stash && pytest <test> && git stash pop` shows the same failure on commit `9dc6ccc` (Plan 01-01 finish state) before any 01-02 edits.
- **Not fixed here:** 01-02 scope is rio_cogeo centralisation (ENV-03) and P0.3 COG heal; DISP pipeline fixtures are unrelated.
- **Candidate owner:** Phase 4 DISP work (or a targeted Plan 01-XX if it persists after the wave-1/2 migration).

### Pre-existing ruff violations in products/rtc.py + products/dswx.py

- **Files:** `src/subsideo/products/rtc.py` (I001 import block unsorted), `src/subsideo/products/dswx.py:452` (F401 `from_bounds` imported but unused).
- **Verified pre-existing:** Both errors present at commit `a0b9590` (Plan 01-01 finish state) before any 01-02 edits.
- **Not fixed here:** 01-02 scope is rio_cogeo centralisation (ENV-03); touching these would broaden the diff unnecessarily.
- **Candidate owner:** a dedicated lint-sweep commit or a future plan that legitimately rewrites the surrounding imports.

### Pre-existing mypy type-arg error in _metadata.py

- **File:** `src/subsideo/_metadata.py:29` — `run_params: dict` missing type parameters.
- **Verified pre-existing:** Present verbatim at commit `a0b9590` before any 01-02 edits.
- **Not fixed here:** Out of 01-02 scope (rio_cogeo centralisation); the surrounding function signature is untouched by this plan.
- **Candidate owner:** A strict-typing pass (likely part of the broader v1.1 mypy-strict cleanup, or a Phase 7 audit).

### Other pre-existing unit-test failures on the full suite

Running `pytest tests/unit/ --no-cov -q` shows these pre-existing failures
(all untouched by 01-02 and none overlapping with the 8 files 01-02 modified):

- `test_compare_dswx.py::TestJrcTileUrl::test_url_format`
- `test_compare_dswx.py::TestBinarizeDswx::test_class_mapping`
- `test_disp_pipeline.py::test_run_disp_mocked`
- `test_disp_pipeline.py::test_run_disp_qc_warning`
- `test_orbits.py::TestFetchOrbit::test_fallback_to_s1_orbits`

Scope check: `git diff a0b9590 HEAD --name-only` shows 01-02 only touches
`_cog.py`, `_metadata.py`, `products/{rtc,dist,dswx}.py`,
`tests/unit/test_{cog_helper,rtc_pipeline}.py`, + `deferred-items.md`;
none of the failing tests exercise those files.

Candidate owner: Phase-specific plans for each area (DISP → Phase 4,
DSWx → Phase 5, orbits → targeted fix).
