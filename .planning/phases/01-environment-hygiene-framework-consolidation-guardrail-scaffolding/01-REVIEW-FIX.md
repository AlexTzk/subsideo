---
phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
fixed_at: 2026-04-22T00:00:00Z
review_path: .planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/01-REVIEW.md
iteration: 1
findings_in_scope: 12
fixed: 12
skipped: 0
status: all_fixed
---

# Phase 01: Code Review Fix Report

**Fixed at:** 2026-04-22T00:00:00Z
**Source review:** `.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/01-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 12 (2 Critical + 10 Warning; Info out of scope)
- Fixed: 12
- Skipped: 0

Info findings (IN-01 through IN-05) were out of scope per the `critical_warning` fix scope and are not addressed here. Pre-existing unit-test failures (6 failed / 285 passed) were baselined before the fix pass and are unchanged after it -- no regressions were introduced.

## Fixed Issues

### CR-01: Use of `src.nodata` after `rasterio` context manager exits

**Files modified:** `src/subsideo/validation/compare_disp.py`
**Commit:** aaa6b49
**Applied fix:** Captured `src.nodata` into a local `nodata` variable inside the `with rasterio.open(velocity_path) as src:` block (alongside the existing `raster_crs` capture). Removed the post-`with` `src.nodata` re-read that would have raised `RasterioIOError: Dataset is closed`. The subsequent `np.where(sampled == nodata, np.nan, sampled)` now uses the pre-captured local and is safe to execute after the context exit.

### CR-02: Retry policy silently swallows non-retryable 5xx statuses

**Files modified:** `src/subsideo/validation/harness.py`
**Commit:** 9fda0b0
**Applied fix:** Added an explicit `if status >= 400: raise ReferenceDownloadError(source, status, current_url)` branch after the abort/refresh/retry dispatch so any HTTP error status that is not enumerated in `retry_on` fails fast instead of raising `HTTPError` and being swallowed by the broader transport-error handler. Narrowed `except requests.RequestException` to `except (requests.ConnectionError, requests.Timeout)` so only transport-level failures trigger a retry sleep; `HTTPError` can no longer reach this path because the `status >= 400` guard intercepts it first. PITFALLS P0.4 contract restored.

### WR-01: Asymmetric timezone normalization in OPERA frame selection

**Files modified:** `src/subsideo/validation/harness.py`
**Commit:** bc74803
**Applied fix:** Replaced the one-way `ft = ft.replace(tzinfo=None)` with a symmetric branch that covers the four tz combinations: both tz-aware, both tz-naive, `ft` tz-aware & `target_hour` tz-naive (strip `ft`), and `target_hour` tz-aware & `ft` tz-naive (strip `target_hour`). Uses local `ft_cmp` / `target_cmp` variables so the original inputs stay intact. The `TypeError: can't subtract offset-naive and offset-aware datetimes` path is eliminated.

### WR-02: `compare_cslc` falls through on shape mismatch when coords are missing

**Files modified:** `src/subsideo/validation/compare_cslc.py`
**Commit:** 23af1db
**Applied fix:** Added an explicit guard clause at the top of the `if prod_complex.shape != ref_complex.shape:` block that raises `ValueError` when any of `prod_x`, `ref_x`, `prod_y`, `ref_y` is `None`. The error message includes both shapes and both paths for diagnosis. This converts a silent-broadcast-or-opaque-error path into a loud, actionable failure.

### WR-03: Race condition on COG heal temp file

**Files modified:** `src/subsideo/_cog.py`
**Commit:** e45e914
**Applied fix:** Added `import tempfile` at module top. Replaced the deterministic `tmp = path.with_suffix(path.suffix + ".cogtmp")` with `tempfile.NamedTemporaryFile(prefix=path.stem + ".", suffix=".cogtmp", dir=path.parent, delete=False)` so each heal call gets a unique filename, eliminating the overlapping-write race when two pipelines target the same output path. Wrapped the `cog_translate + tmp.replace(path)` pair in `try / except Exception: tmp.unlink(missing_ok=True); raise` so a mid-heal failure does not leak the unique tempfile.

### WR-04: `_CONFIGURED` flag not thread-safe

**Files modified:** `src/subsideo/_mp.py`
**Commit:** f2ee089
**Applied fix:** Added `import threading` and a module-level `_CONFIGURE_LOCK = threading.Lock()`. Refactored `configure_multiprocessing()` to use double-checked locking: the pre-lock `if _CONFIGURED: return` fast path preserves the cheap idempotent-call behavior, and the inside-lock re-check ensures that concurrent cold calls cannot both apply the bundle (MPLBACKEND, RLIMIT_NOFILE, `mp.set_start_method`). Docstring updated to document the thread-safety contract.

### WR-05: Division by zero in CSLC coherence computation

**Files modified:** `src/subsideo/validation/compare_cslc.py`
**Commit:** f426efc
**Applied fix:** Replaced the unconditional `ifg / np.abs(ifg)` with a pre-masked branch: build `ifg_nonzero = np.abs(ifg) > 1e-12`, then if any pixels survive the mask, normalize only those pixels and compute coherence from their mean; otherwise return `coherence = 0.0`. Prevents NaN propagation into the coherence measurement and the downstream gate evaluation.

### WR-06: `sqlite3.connect` context manager does not close connection

**Files modified:** `src/subsideo/burst/db.py`
**Commit:** 3b42f26
**Applied fix:** Added `import contextlib` and wrapped `sqlite3.connect(str(db_path))` in `contextlib.closing(...)` in `query_bounds`. Python's `sqlite3.Connection.__exit__` commits/rollbacks but does NOT close the connection (per CPython docs); `contextlib.closing` ensures the file descriptor is released on every call, stopping the FD leak over long-running eval batches. The `build_burst_db` path already uses explicit `try / finally: conn.close()` and was left unchanged.

### WR-07: Missing `urllib.error` import for exception handler

**Files modified:** `src/subsideo/validation/compare_dswx.py`
**Commit:** 3b06138
**Applied fix:** Added an explicit `import urllib.error` alongside the existing `import urllib.request` at the module top. The reference to `urllib.error.HTTPError` in `_fetch_jrc_tile` no longer relies on the fragile transitive import that ships with recent CPython `urllib.request` but is not guaranteed across versions.

### WR-08: Unvalidated metrics path in matrix manifest

**Files modified:** `src/subsideo/validation/matrix_writer.py`
**Commit:** d58b68c
**Applied fix:** Added a new `_validate_metrics_path(metrics_path_str, manifest_path) -> Path` helper that resolves the path and requires it to land inside at least one of the allowed roots (`Path.cwd().resolve()` or `manifest_path.resolve().parent`). Raises `ValueError` with a detailed message if the resolved path escapes both roots. `write_matrix` now calls this helper instead of unconditionally `Path(cell["metrics_file"])`. The allow-list covers both (a) the normal production layout where manifests and metrics live under `results/` relative to cwd and (b) the pytest fixture layout where manifests live under `tmp_path`.

### WR-09: `credential_preflight` treats whitespace-only values as set

**Files modified:** `src/subsideo/validation/harness.py`
**Commit:** 95f1e96
**Applied fix:** Changed `if not os.environ.get(v)` to `if not (os.environ.get(v) or "").strip()`. A trailing-whitespace mis-edit in `.env` (e.g. `CDSE_CLIENT_ID= ` with a single trailing space) now flags as missing at preflight, rather than passing preflight and failing deeper with a less actionable error.

### WR-10: Supervisor accepts script paths from any location without path validation

**Files modified:** `src/subsideo/validation/supervisor.py`
**Commit:** 21640f5
**Applied fix:** At the top of `supervisor.run`, before spawning the subprocess: (a) `script_path.is_file()` check raises `SystemExit` on missing or non-regular-file paths, (b) `script_path.is_symlink()` check raises `SystemExit` on symlinks (refusing to follow share-dir symlinked payloads), and (c) a naming-convention check that logs a `logger.warning` when the script name does not start with `run_eval`. The naming check is deliberately non-fatal so existing test fixtures (e.g. `quick.py`) and ad-hoc diagnostic scripts continue to run; the file/symlink checks are hard stops per the T-07-01 threat model.

---

_Fixed: 2026-04-22T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
