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

## Discovered in Plan 01-03

### Pre-existing ruff violations in products/*.py

- **Files:** `src/subsideo/products/{rtc,cslc,disp,dist,dswx}.py` — 31 ruff errors (mostly import-organisation I001, a few BLE001).
- **Verified pre-existing:** `git stash && ruff check <files>` reports the same 31 errors before any 01-03 edits.
- **Not fixed here:** 01-03 scope is `_mp.py` + configure_multiprocessing insertion + cslc.py patch removal. Touching unrelated imports would broaden the diff.
- **Candidate owner:** a dedicated lint-sweep commit, or Phase 7 pre-release audit.

### Pre-existing mypy missing-stub error for `requests`

- **File:** `src/subsideo/_mp.py:75` and `src/subsideo/data/ionosphere.py:7` — `Library stubs not installed for "requests"`.
- **Verified pre-existing:** `ionosphere.py` produces the identical error on clean checkout; `_mp.py` inherits the same typeshed-gap, unmitigated by `ignore_missing_imports = true` because `types-requests` is partially installed.
- **Not fixed here:** Requires env change (add `types-requests` to dev deps) which is out of Plan 01-03 scope.
- **Candidate owner:** a dedicated env-cleanup commit, or the mypy-strict cleanup sweep.
# Deferred items from Plan 01-09

## Pre-existing test failures (out of scope)

Observed while running `pytest tests/unit -q` inside subsideo:dev container (amd64)
AND on osx-arm64 host — failures reproduce on both platforms, so they are not
caused by the Docker build in Plan 01-09. Documented for a future fix-up pass:

- tests/unit/test_compare_dswx.py::TestJrcTileUrl::test_url_format
  Expected URL tile order is `0000080000-0000120000.tif` but fixture returns
  `0000120000-0000080000.tif`. Likely stale assertion against a different JRC
  tile-ID convention; fix in whichever plan owns `compare_dswx.py`.

- tests/unit/test_compare_dswx.py::TestBinarizeDswx::test_class_mapping
  `np.float32(1.0) == 0.0` assertion — binarize_dswx default classes changed.

- tests/unit/test_disp_pipeline.py::test_run_disp_mocked
  tests/unit/test_disp_pipeline.py::test_run_disp_qc_warning
  Assertion on DISPResult.valid = True after mocked run; the mocks don't
  provide the conda-forge `dolphin.workflows.config._unwrap_options` stub.

- tests/unit/test_metadata_wiring.py::TestMetadataInjectionInCSLC::test_run_cslc_calls_inject_opera_metadata
  tests/unit/test_metadata_wiring.py::TestMetadataInjectionInDISP::test_run_disp_calls_inject_opera_metadata
  Mock-call assertion failure post-01-05 DISP pipeline refactor.

- tests/unit/test_orbits.py::TestFetchOrbit::test_fallback_to_s1_orbits
  Test raises ConnectionError in fallback path before reaching assertion.

Total: 7 pre-existing failures / 291 collected / 283 passing / 1 skipped.
Coverage 63% (below 80% gate) — consequence of 7 FAILs not of Docker build.

Verification that these are pre-existing:
- `pytest tests/unit/test_compare_dswx.py::TestJrcTileUrl::test_url_format` on
  osx-arm64 host => FAIL with same assertion text.
- `pytest tests/unit/test_orbits.py::TestFetchOrbit::test_fallback_to_s1_orbits`
  on osx-arm64 host => FAIL with same ConnectionError.

Plan 01-09 scope is env-create / Docker build / lockfile generation. These
test failures indicate bugs in product/test code that should be addressed by
whichever plan owns the failing test file.
