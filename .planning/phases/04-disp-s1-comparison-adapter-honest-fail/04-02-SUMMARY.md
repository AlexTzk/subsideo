---
phase: 04-disp-s1-comparison-adapter-honest-fail
plan: 02
subsystem: validation
tags: [insar, validation, multilook, comparison-adapter, ramp, rasterio, scipy, rioxarray]

# Dependency graph
requires:
  - phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
    provides: rasterio + xarray + rioxarray + scipy installed in conda-env.yml; compare_disp.py module skeleton with v1.0 compare_disp + compare_disp_egms_l2a callsites
  - phase: 03-cslc-s1-self-consistency-eu-validation
    provides: docs/validation_methodology.md §1 + §2 (Phase 4 §3 multilook ADR will append per D-15)
provides:
  - "compare_disp.prepare_for_reference (top-level kw-only-method validation adapter; 3-form reference_grid; explicit-no-default method= per DISP-01 + CONTEXT D-04)"
  - "compare_disp.ReferenceGridSpec (frozen dataclass for DISP-01 form (c) PS-point sampling)"
  - "compare_disp.MultilookMethod (Literal['gaussian', 'block_mean', 'bilinear', 'nearest'] type alias)"
  - "6 private helpers: _read_native_as_array, _resample_onto_grid, _resample_onto_path, _resample_onto_dataarray, _point_sample, _point_sample_from_dataset"
  - "Module docstring documents adapter as validation-only (DISP-05) and references docs/validation_methodology.md §3"
affects: [04-03-matrix-writer-render, 04-04-eval-scripts-rerun, 04-05-conclusions-doc-brief]

# Tech tracking
tech-stack:
  added:
    - "rioxarray (newly imported at module-top in compare_disp.py to register .rio accessor for xr.DataArray form b)"
    - "xarray (newly imported at module-top in compare_disp.py for type annotations; transitive dep was already present)"
    - "scipy.ndimage.gaussian_filter + map_coordinates (lazy-imported inside method-branch helpers; transitive dep already present)"
    - "rasterio.io.MemoryFile (lazy-imported inside _point_sample to bridge xr.DataArray to rasterio.DatasetReader.sample())"
    - "pyproj.Transformer (lazy-imported inside _point_sample_from_dataset for lon/lat -> raster CRS)"
  patterns:
    - "Three-form discriminator dispatch: (Path | str | xr.DataArray | ReferenceGridSpec) routed via isinstance() to (a) _resample_onto_path, (b) _resample_onto_dataarray, (c) _point_sample"
    - "Type-narrowing via local annotation: `out: xr.DataArray = da.rio.write_crs(...).rio.write_transform(...)` to suppress [no-any-return] from rio chained accessor"
    - "Per-method dispatch via dict[str, Resampling] for the three rasterio-native methods + dedicated gaussian branch with scipy.ndimage.gaussian_filter on src grid before reproject"
    - "MemoryFile bridge for form (b) -> form (c) transition: xr.DataArray native is wrapped in an in-memory GeoTIFF so the rasterio.DatasetReader.sample() API stays uniform regardless of input type"
    - "CR-01 mirror at point-sample helper: nodata + transform + read(1) all captured BEFORE the with-block exits, mirroring compare_disp_egms_l2a:294 already-fixed pattern"

key-files:
  created:
    - "tests/product_quality/test_prepare_for_reference.py (187 LOC, 17 tests)"
  modified:
    - "src/subsideo/validation/compare_disp.py (380 -> 806 LOC; +426/-5)"

key-decisions:
  - "Option A minimal refactor preserved: existing compare_disp + compare_disp_egms_l2a unchanged at top-level. Resampling.bilinear callsites at lines 163 + 175 retained for v1.0 continuity. Eval scripts (Plan 04-04) call prepare_for_reference BEFORE these existing functions per CONTEXT D-Claude's-Discretion."
  - "Method-branch lazy-imports for scipy.ndimage + pyproj.Transformer + rasterio.io.MemoryFile inside helper bodies. xarray + rioxarray promoted to module top because they appear in type annotations (cannot be lazy under `from __future__ import annotations` if used at runtime via isinstance checks)."
  - "rioxarray imported at module top with `# noqa: F401  (registers .rio accessor on xr.DataArray)` because the .rio accessor binds via import side-effect — not used as a name."
  - "_point_sample on xr.DataArray input writes to an in-memory MemoryFile rather than reusing the form (a) path (which would force a temp-disk write). Both are validation-only no-write-back semantics on the original xr.DataArray; MemoryFile path adds zero disk I/O."
  - "block_mean at point-sample uses fixed 6-pixel radius (~30 m / 5 m for OPERA 30 m / native 5 m ratio); spec-derived spacing (median nearest-neighbour) deferred to follow-up if EGMS L2a Bologna PS density warrants it."
  - "gaussian sigma at point-sample fixed at 3 px (~half of the 6-px radius); precise PITFALLS-physics sigma=0.5*ref/native handled in the path/dataarray method-branch via dst_transform.e/a ratios."

patterns-established:
  - "Three-form reference_grid adapter: the `reference_grid: Path | xr.DataArray | ReferenceGridSpec` dispatch via isinstance is now the canonical pattern for any future product that needs to multilook to a heterogeneous reference. Promotion to `validation/adapters.py` deferred per CONTEXT D-18 until a 2nd product needs it."
  - "Explicit-no-default discipline at adapter signature: method= is kw-only with default sentinel `None`, raising ValueError citing the policy ID — no silent kernel pick. Audit trail in error message is the proof."
  - "Validation-only adapter discipline: byte-level SHA256 pre/post test in the unit suite enforces no-write-back to the input. Any future adapter on subsideo's product surface must include the same DISP-05 audit test."
  - "Type-narrowing local annotation for rio chained accessors: `out: xr.DataArray = da.rio.write_crs(...).rio.write_transform(...)` returns the chained value with the explicit type to suppress mypy [no-any-return] without a `# type: ignore`."

requirements-completed: [DISP-01, DISP-05]

# Metrics
duration: 9min
completed: 2026-04-25
---

# Phase 04 Plan 02: prepare_for_reference adapter Summary

**1 new top-level adapter function + 1 frozen dataclass + 1 type alias + 6 private helpers added to `compare_disp.py`; 17 unit tests covering 12-cell method-x-form matrix + 3 error-path + 1 DISP-05 no-write-back audit + 1 block_mean spot-check; ruff + mypy clean on touched files; existing compare_disp + compare_disp_egms_l2a unchanged.**

## Performance

- **Duration:** 9 min (8 min 52 sec)
- **Started:** 2026-04-25T07:09:08Z
- **Completed:** 2026-04-25T07:18:00Z
- **Tasks:** 2 (Task 1 RED + GREEN; Task 2 test-suite-as-test commit)
- **Files modified/created:** 2 (1 source modified, 1 test file created)

## Accomplishments

- **`prepare_for_reference` adapter** added at top level of `compare_disp.py` per DISP-01 + DISP-05 + CONTEXT D-01..D-04, D-17, D-18. Validation-only — never writes back to `native_velocity` input (verified by SHA256 byte-equal test). Three reference_grid forms via `isinstance` dispatch:
  - **Form (a)** `Path | str` -> `_resample_onto_path`: opens GeoTIFF, reads CRS + transform + shape, reprojects native onto file's grid via `_resample_onto_grid`.
  - **Form (b)** `xr.DataArray` -> `_resample_onto_dataarray`: reads CRS + transform via `rioxarray.rio` accessor, reprojects native onto array's grid, returns `xr.DataArray` with CRS preserved (type-preservation).
  - **Form (c)** `ReferenceGridSpec` -> `_point_sample`: point-samples native at each (lon, lat) projected to the native CRS via `pyproj.Transformer`. Returns 1-D ndarray of length `len(spec.points_lonlat)`.
- **Four `method` branches** dispatched via the `MultilookMethod` Literal:
  - `block_mean` -> `Resampling.average` (rasterio-native block-mean / averaging — Phase 4 D-02 conservative default).
  - `bilinear` -> `Resampling.bilinear` (v1.0 continuity).
  - `nearest` -> `Resampling.nearest` (degenerate; for kernel-comparison studies in the Unwrapper Selection follow-up).
  - `gaussian` -> `scipy.ndimage.gaussian_filter` on src grid first (sigma = 0.5 * dst_pixel_size / src_pixel_size in each axis, NaN-safe via fill-with-zero), then `Resampling.nearest` onto dst grid (PITFALLS P3.1 sigma=0.5*ref).
- **Explicit-no-default validation discipline:** `method=None` raises `ValueError("method= is required (DISP-01 explicit-no-default policy). Pick one of: ...")`. Bogus method values raise `ValueError("method must be one of (...); got ...")`. Unsupported `reference_grid` form raises `ValueError("reference_grid must be Path | xr.DataArray | ReferenceGridSpec; got ...")`.
- **Module docstring** updated to document the third comparison surface alongside the existing two paths. References `docs/validation_methodology.md` Sec 3 for the multilook-method ADR (Phase 4 D-03 + Phase 3 D-15 append-only doc policy). Documents validation-only / never-writes-back (DISP-05).
- **CR-01 already-fixed gotcha mirrored** in `_point_sample_from_dataset`: `nodata = src.nodata` + `src_transform` + `src_data = src.read(1)` all captured before the `with rasterio.open(...) as src:` block exits. Identical pattern to `compare_disp_egms_l2a:294`.
- **17-test unit suite** at `tests/product_quality/test_prepare_for_reference.py`:
  - 3 error-path tests (method=None / method='bogus' / reference_grid=42).
  - 12 parametrised method-x-form cases (4 methods x 3 forms = 12 distinct test ids on synthetic 100x100 native + 50x50 ref + 10 PS points in EPSG:32611).
  - 1 DISP-05 audit (SHA256 pre/post byte-identical on native_path).
  - 1 spot-check on block_mean (synthetic X+Y plane recovers expected window mean within tolerance).

## Task Commits

Each task committed atomically:

1. **Task 1 RED — failing smoke test for the public API** — `c58ab99` (test). ImportError on `from subsideo.validation.compare_disp import (MultilookMethod, ReferenceGridSpec, prepare_for_reference)` confirmed before implementation.
2. **Task 1 GREEN — prepare_for_reference adapter** — `4bf9922` (feat). +426 / -5 LOC on compare_disp.py.
3. **Task 2 — full 17-test matrix** — `7f21dbf` (test). +182 / -19 LOC vs the smoke test (the smoke test from Task 1 RED was replaced with the full suite which also covers it semantically).

_TDD plan-level gate sequence (test -> feat -> test) holds. Task 1 follows strict RED (ImportError) -> GREEN (impl) flow; Task 2 is a test-only commit because the impl already existed from Task 1 — the tests act as behavior pinning rather than a strict RED -> GREEN cycle. This matches the plan's two-task structure (Task 1 = impl with smoke test, Task 2 = full unit-test matrix)._

## Files Created/Modified

- **`src/subsideo/validation/compare_disp.py`** (modified) — module docstring expanded from 16 -> 28 lines (third comparison surface + ADR doc reference). Imports gained `from dataclasses import dataclass`, `from typing import Literal`, `import rioxarray`, `import xarray as xr`. Appended new `# --- Phase 4 multilook adapter ---` section after `compare_disp_egms_l2a` containing: `MultilookMethod` Literal alias, `ReferenceGridSpec` frozen dataclass, `prepare_for_reference` top-level function, 6 private helpers (`_read_native_as_array`, `_resample_onto_grid`, `_resample_onto_path`, `_resample_onto_dataarray`, `_point_sample`, `_point_sample_from_dataset`). Net +421 LOC; 380 -> 806.
- **`tests/product_quality/test_prepare_for_reference.py`** (created, 187 LOC) — 17 tests under 4 sections (Fixtures / Error-path / Method-x-form matrix / DISP-05 audit + block_mean spot-check). Uses `pytest.mark.parametrize` over `_METHODS: list[MultilookMethod]` to drive the 12-cell matrix.

## Decisions Made

- **Option A minimal refactor** chosen over Option B (refactor `compare_disp` + `compare_disp_egms_l2a` to internally call `prepare_for_reference(method='bilinear')`). Decision rationale: the existing two functions have full v1.0 test coverage and are still called by the eval scripts; refactoring them now would couple Plan 04-02 to Plan 04-04 (eval-script rewire). Option A keeps Plan 04-02 strictly additive — eval scripts (Plan 04-04) call `prepare_for_reference(method='block_mean')` BEFORE invoking the existing top-level functions. CONTEXT D-Claude's-Discretion green-lit either; Option A picked for parallelizability.
- **xarray + rioxarray imported at module top, NOT lazy.** They appear in type annotations (`xr.DataArray` in function signatures) and `isinstance` checks at runtime. Per Phase 1 lazy-import discipline, only conda-forge heavies that aren't on every code path stay lazy. xarray and rioxarray are pip-installable (pyproject.toml validation extras) and required for any form (b) call — promoting them to module top costs ~150 ms import time once vs adding fragile lazy paths.
- **`# noqa: F401` on `import rioxarray`** because the import is purely for side-effect (registering the `.rio` accessor on `xr.DataArray`). The name `rioxarray` is never used after import. Comment documents the side-effect dependency for future readers.
- **MemoryFile bridge for form (b) -> form (c)** in `_point_sample` rather than a temp-disk write or duplicating the sample logic. The xr.DataArray native gets wrapped in an in-memory GeoTIFF (`rasterio.io.MemoryFile`) so the `_point_sample_from_dataset` body stays uniform regardless of input type. Adds zero disk I/O; lazy-imported.
- **block_mean fixed 6-px radius at point-sample.** ReferenceGridSpec doesn't carry a spacing attribute (intentional — EGMS L2a PS density is irregular); a 6-pixel radius (~30 m at 5 m posting) matches the OPERA 30 m / native 5 m ratio. If Plan 04-04 finds the radius too coarse for Bologna PS density, it can pass a tighter `ReferenceGridSpec` (extension is additive).
- **gaussian sigma=3.0 fixed at point-sample.** Half of the 6-px block_mean radius — same physical scale. The full PITFALLS-physics sigma=0.5*ref/native dynamic computation is implemented in the form (a)/(b) path via `dst_transform.e/a` over `src_transform.e/a` ratios.

## Deviations from Plan

Two **Rule 1 / Rule 3** auto-fixes applied during execution; none changed plan intent:

### Rule 1 - Bug: `[arg-type]` mypy error on `dst_shape: tuple[int, ...]` parameter

- **Found during:** Task 1 GREEN mypy check.
- **Issue:** `_resample_onto_dataarray` passes `ref_da.shape` (typed `tuple[int, ...]`) to `_resample_onto_grid`'s `dst_shape: tuple[int, int]` parameter. Mypy flags `[arg-type]`. Plan-as-written had this latent.
- **Fix:** Added explicit 2-D check: `if ref_da.ndim != 2: raise ValueError(...)` and tightened: `dst_shape: tuple[int, int] = (int(ref_da.shape[0]), int(ref_da.shape[1]))`. The runtime check also documents the form (b) constraint (xr.DataArray must be 2-D).
- **Files modified:** `src/subsideo/validation/compare_disp.py`
- **Commit:** `4bf9922` (folded into Task 1 GREEN)

### Rule 1 - Bug: `[no-any-return]` mypy errors on rio accessor + scipy.ndimage chains

- **Found during:** Task 1 GREEN + Task 2 mypy check.
- **Issue:** `da.rio.write_crs(...).rio.write_transform(...)` returns `Any` (because rioxarray's `.rio` accessor isn't fully typed). Same for `scipy.ndimage.map_coordinates(...)` returning `Any`. Mypy flags `[no-any-return]` when these flow into return statements declared as `xr.DataArray` / `np.ndarray`.
- **Fix:** Added explicit local-variable type annotations: `out_with_crs: xr.DataArray = ...` and `sampled_bilinear = np.asarray(map_coordinates(...), dtype=np.float64)` — the np.asarray wrapping coerces back to a fully-typed ndarray; the local annotation does the same for the rio chain. This mirrors Plan 04-01's `np.asarray(..., dtype=np.complex64)` pattern documented in the 04-01 SUMMARY.
- **Files modified:** `src/subsideo/validation/compare_disp.py` (3 sites: `_resample_onto_dataarray`, `_point_sample_from_dataset` bilinear branch, `_point_sample_from_dataset` gaussian branch). Same pattern in test fixture `ref_dataarray`.
- **Commit:** `4bf9922` (Task 1 GREEN) + `7f21dbf` (Task 2 — fixture annotation).

### Rule 3 - Blocking: Unused `# type: ignore[arg-type]` comments on test parametrize bypass

- **Found during:** Task 2 mypy check.
- **Issue:** `prepare_for_reference(native_path, ref_path, method="bogus")  # type: ignore[arg-type]` — mypy flags the ignore as `[unused-ignore]` because `method: MultilookMethod | None` accepts `str` after type-narrowing in this project's mypy config.
- **Fix:** Removed the unused `# type: ignore[arg-type]` comments on lines 112 and 117 of the test file. Behaviour identical (the function still raises ValueError at runtime when "bogus" is passed); the comments were redundant noise.
- **Files modified:** `tests/product_quality/test_prepare_for_reference.py`
- **Commit:** `7f21dbf` (Task 2)

## Issues Encountered

- **Ruff I001 (un-sorted imports)** in test file — auto-fixed via `ruff check --fix`. Section divider comment got reorganised together with the imports (acceptable; behaviour preserved).
- **Initial `Edit` tool failure** on the impl insertion — two identical `return DISPValidationResult(...)` blocks at the end of `compare_disp` and `compare_disp_egms_l2a` had to be disambiguated with the preceding `logger.info(...)` block as anchor. Fix: used multi-line context-aware `old_string`. Adds zero risk because the second occurrence is at end-of-file and the new block is appended exactly where the plan specified (after `compare_disp_egms_l2a` body).
- **`micromamba run -n subsideo`** invocation produced shell errors via the auto-loaded function wrap; resolved by using the env's python directly (`/Users/alex/.local/share/mamba/envs/subsideo/bin/python`). Functionally identical (same env, same packages); plan acceptance commands are honored at the env level. Not a deviation from the plan — same intent.

## TDD Gate Compliance

Plan-level TDD gate sequence per task:

- **Task 1 RED gate (`c58ab99`)** — `test(04-02): add failing smoke test for prepare_for_reference public API` confirmed failing on `ImportError: cannot import name 'MultilookMethod'` before implementation.
- **Task 1 GREEN gate (`4bf9922`)** — `feat(04-02): add prepare_for_reference adapter to compare_disp.py`; smoke test passes.
- **Task 2 (`7f21dbf`)** — `test(04-02): add 17-test matrix for prepare_for_reference adapter`. RED-equivalent: the 17 tests would have failed against an empty implementation (Task 1 RED state); they pass against the GREEN state from Task 1. Per Plan 04-02 task structure, Task 2 is a test-suite commit (not a fresh RED -> GREEN cycle on a different feature).

## User Setup Required

None - no external service configuration required. All work is in-repo Python additions and unit tests against synthetic fixtures (no CDSE / Earthdata / CDS API credentials needed).

## Next Phase Readiness

Wave 1 of Phase 4 complete on this plan. Plan 04-03 (Wave 2: matrix_writer DISP cell render branch) and Plan 04-04 (Wave 3: eval-script rewire) can now consume the public API:

- `from subsideo.validation.compare_disp import prepare_for_reference, ReferenceGridSpec, MultilookMethod` — all three symbols exported.
- Plan 04-04 declarative module-level constant: `REFERENCE_MULTILOOK_METHOD: Literal["block_mean"] = "block_mean"` — the `Literal["block_mean"]` annotation is a subset of `MultilookMethod` and dispatches identically.
- Form (b) (xr.DataArray) is the recommended call pattern for OPERA DISP-S1 reference comparison (N.Am. SoCal); form (c) (ReferenceGridSpec) is the recommended call pattern for EGMS L2a PS comparison (EU Bologna). Form (a) (Path) is available for direct GeoTIFF reference paths.
- `Resampling.bilinear` callsites in v1.0 `compare_disp` (line 163) and `compare_disp_egms_l2a` (line 175) preserved unchanged. Plan 04-04 calls `prepare_for_reference` BEFORE these v1.0 functions per Option A minimal refactor.

No blockers. No threat-flag surfaces beyond the plan's existing threat_model (T-04-02-01 .. T-04-02-05) — all 5 mitigated dispositions match implementation:

- **T-04-02-01 (Tampering / no-write-back)** mitigated by SHA256 pre/post test.
- **T-04-02-02 (Tampering / method= validation)** mitigated by Literal validation + ValueError with DISP-01 audit-trail message.
- **T-04-02-04 (Denial of service / NaN propagation in gaussian)** mitigated by `np.where(np.isfinite(src_data), src_data, 0.0)` fill-before-filter (RESEARCH lines 738-746).
- **T-04-02-03 (Information disclosure)** accepted (DEBUG-only logger).
- **T-04-02-05 (Elevation of privilege / MemoryFile)** accepted (in-memory only; no disk path coercion).

## Self-Check: PASSED

Verifications performed before writing this section:

- **Files exist:**
  - `src/subsideo/validation/compare_disp.py` — FOUND (806 LOC; 380 -> 806; +421 net)
  - `tests/product_quality/test_prepare_for_reference.py` — FOUND (187 LOC, new)
- **All 3 commits exist in git log:**
  - `c58ab99` (Task 1 RED) — FOUND
  - `4bf9922` (Task 1 GREEN) — FOUND
  - `7f21dbf` (Task 2) — FOUND
- **17 plan tests pass** under `/Users/alex/.local/share/mamba/envs/subsideo/bin/python -m pytest tests/product_quality/test_prepare_for_reference.py -v --no-cov` (functionally identical to `micromamba run -n subsideo pytest ...`).
- **All 12 method-x-form parametrised cases collected:** verified via `pytest --collect-only` listing all of `test_form_a_path_each_method[gaussian|block_mean|bilinear|nearest]`, `test_form_b_dataarray_each_method[...]`, `test_form_c_spec_each_method[...]`.
- **Public API imports succeed:** `python -c "from subsideo.validation.compare_disp import prepare_for_reference, ReferenceGridSpec, MultilookMethod"` exits 0.
- **Signature kw-only-method + None default verified:** inspect.signature shows `method` is KEYWORD_ONLY with `default is None` per DISP-01.
- **Existing v1.0 code preserved:** `def compare_disp\b` and `Resampling.bilinear` both still grep-match in compare_disp.py at the v1.0 lines (Option A minimal refactor).
- **Ruff clean** on both touched files.
- **Mypy clean** on both touched files (zero errors above the pre-existing `[type-arg]` baseline; the 12 remaining `[type-arg]` errors on `compare_disp.py` are the bare-`np.ndarray`-without-type-args pattern consistent with existing module style — same baseline preserved by Plan 04-01 SUMMARY).
- **No regressions in pre-existing tests** — 10 existing compare_disp tests (7 product_quality + 3 reference_agreement) + 19 Plan 04-01 tests all pass alongside the 17 new tests = 46 passed.

---
*Phase: 04-disp-s1-comparison-adapter-honest-fail*
*Completed: 2026-04-25*
