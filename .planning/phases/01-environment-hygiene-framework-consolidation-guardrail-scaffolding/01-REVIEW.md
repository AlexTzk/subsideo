---
phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
reviewed: 2026-04-22T00:00:00Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - src/subsideo/_cog.py
  - src/subsideo/_mp.py
  - src/subsideo/_metadata.py
  - src/subsideo/burst/db.py
  - src/subsideo/products/types.py
  - src/subsideo/validation/__init__.py
  - src/subsideo/validation/harness.py
  - src/subsideo/validation/supervisor.py
  - src/subsideo/validation/matrix_schema.py
  - src/subsideo/validation/matrix_writer.py
  - src/subsideo/validation/criteria.py
  - src/subsideo/validation/results.py
  - src/subsideo/validation/stable_terrain.py
  - src/subsideo/validation/selfconsistency.py
  - src/subsideo/validation/compare_cslc.py
  - src/subsideo/validation/compare_disp.py
  - src/subsideo/validation/compare_dist.py
  - src/subsideo/validation/compare_dswx.py
  - src/subsideo/validation/compare_rtc.py
  - scripts/env07_diff_check.py
  - conda-env.yml
  - Dockerfile
  - Apptainer.def
  - Makefile
findings:
  critical: 2
  warning: 10
  info: 5
  total: 17
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-04-22T00:00:00Z
**Depth:** standard
**Files Reviewed:** 24
**Status:** issues_found

## Summary

Phase 1 built the environment-hygiene, framework-consolidation, and guardrail-scaffolding foundation for subsideo v1.1. The review covered the multiprocessing bundle (`_mp.py`), COG heal path (`_cog.py`), OPERA metadata injection (`_metadata.py`), EU burst DB (`burst/db.py`), the validation harness (`harness.py`), watchdog supervisor (`supervisor.py`), matrix schema / writer, frozen criteria registry, results module, stable-terrain mask, self-consistency metrics, five product comparison modules, and the environment/orchestration files (`conda-env.yml`, `Dockerfile`, `Apptainer.def`, `Makefile`, `scripts/env07_diff_check.py`).

Overall architecture is sound: the immutability contract on `CRITERIA` is well-preserved via `@dataclass(frozen=True)`, the supervisor AST-whitelist properly rejects arbitrary eval paths, the retry policy correctly refuses to retry on Earthdata 401, and the subprocess process-group handling covers grandchild kills. The YAML manifest loader uses `yaml.safe_load`, the supervisor uses `shell=False` semantics throughout, and no hardcoded credentials or `eval()` appearances were found.

Two critical defects require immediate attention:

1. `compare_disp.py` uses `src.nodata` **after** the `rasterio.open(...)` context manager has closed, which will raise `RasterioIOError` at runtime for every `compare_disp_egms_l2a` call (CR-01).
2. `download_reference_with_retry` has an incorrect retry-semantics pathway: a non-retryable, non-abort 5xx (e.g., CDSE 500, 502, 504) is silently retried up to `max_retries` via the broad `except requests.RequestException` handler, violating the RETRY_POLICY contract documented in PITFALLS P0.4 (CR-02).

The remaining warnings flag concurrency races on the IFD-heal temp file, asymmetric timezone handling in OPERA frame selection, silent shape-mismatch fall-through in `compare_cslc`, non-thread-safe `_CONFIGURED` flag, division-by-zero in CSLC coherence, unvalidated manifest paths in `matrix_writer`, `sqlite3.connect` resource leak, and a missing `urllib.error` import. Info items cover mutable `CRITERIA` dict access, a hardcoded `is_north=1` in EU burst DB records, and a return-type-hint inaccuracy.

## Critical Issues

### CR-01: Use of `src.nodata` after `rasterio` context manager exits

**File:** `src/subsideo/validation/compare_disp.py:319`
**Issue:** In `compare_disp_egms_l2a`, the `src.nodata` attribute is read on line 319, but the `with rasterio.open(velocity_path) as src:` block closes at line 317 (when control leaves the indented block). Accessing properties on a closed rasterio `DatasetReader` raises `RasterioIOError: Dataset is closed`. This code path runs for every EU DISP vs. EGMS L2a comparison whenever the raster has a declared nodata value.

**Fix:** Capture `nodata` inside the `with` block alongside `raster_crs`:
```python
with rasterio.open(velocity_path) as src:
    raster_crs = src.crs
    nodata = src.nodata  # <-- read while dataset is open
    points_proj = points.to_crs(raster_crs)
    # ... (clip + sample as before) ...
    xy = list(zip(points_in.geometry.x, points_in.geometry.y, strict=True))
    sampled = np.array([v[0] for v in src.sample(xy)], dtype=np.float64)

if nodata is not None:
    sampled = np.where(sampled == nodata, np.nan, sampled)
```

### CR-02: Retry policy silently swallows non-retryable 5xx statuses

**File:** `src/subsideo/validation/harness.py:482-536`
**Issue:** The per-source `RETRY_POLICY` enumerates `retry_on` (e.g., `[429, 503]` for CDSE) and `abort_on` (e.g., `[401, 403, 404]`). Any status outside both sets (e.g., a CDSE 500 / 502 / 504 / 400 / 405) reaches the `resp.raise_for_status()` call on line 515, which raises `requests.HTTPError` — a subclass of `requests.RequestException`. The surrounding `except requests.RequestException as e:` handler on line 528 then sleeps and retries the request. Net effect: every HTTP error that is not explicitly enumerated in `abort_on` is retried up to `max_retries`, defeating the PITFALLS P0.4 contract ("Earthdata 401 must NOT retry forever" is fine, but any 5xx ≠ 503 also silently retries).

**Fix:** Classify unknown statuses explicitly — either abort-by-default for unknown statuses, or abort-by-default on 4xx and retry-by-default on 5xx:
```python
if status in policy.get("retry_on", []):
    wait = min(backoff_seconds * (2 ** (attempt - 1)), 300)
    logger.info("Retry {}/{} for {} ({}): status={}, sleeping {}s",
                attempt, max_retries, source, current_url, status, wait)
    time.sleep(wait)
    continue
if status >= 400:
    # Unknown status: fail fast rather than silently retry via RequestException fallback
    raise ReferenceDownloadError(source, status, current_url)
resp.raise_for_status()  # now only 2xx paths continue
```
Additionally, narrow the fallback `except requests.RequestException` to only transport-level errors (e.g., `requests.ConnectionError`, `requests.Timeout`) so HTTPErrors no longer trigger blind retries.

## Warnings

### WR-01: Asymmetric timezone normalization in OPERA frame selection

**File:** `src/subsideo/validation/harness.py:344-369`
**Issue:** `select_opera_frame_by_utc_hour` normalizes one direction only:
```python
if ft.tzinfo is not None and target_hour.tzinfo is None:
    ft = ft.replace(tzinfo=None)
```
If the caller passes a tz-aware `sensing_datetime` but frame metadata values are naive ISO-8601 strings (the `datetime.fromisoformat(...)` without 'Z' case), `target_hour` remains tz-aware and `ft` is naive, so `ft - target_hour` raises `TypeError: can't subtract offset-naive and offset-aware datetimes`.
**Fix:** Normalize both directions symmetrically, or document that `sensing_datetime` must be tz-naive:
```python
if ft.tzinfo is not None and target_hour.tzinfo is None:
    ft = ft.replace(tzinfo=None)
elif target_hour.tzinfo is not None and ft.tzinfo is None:
    target_hour_cmp = target_hour.replace(tzinfo=None)
    delta = abs((ft - target_hour_cmp).total_seconds())
else:
    delta = abs((ft - target_hour).total_seconds())
```

### WR-02: `compare_cslc` falls through on shape mismatch when coords are missing

**File:** `src/subsideo/validation/compare_cslc.py:92-123`
**Issue:** When `prod_complex.shape != ref_complex.shape` and coordinates are not all present (line 93's 4-way `is not None` check fails), the alignment block is silently skipped. Execution continues to line 126's mask computation, which either raises `ValueError: operands could not be broadcast together` or silently broadcasts incorrectly depending on shape dims. Silent failure mode in a validation gate is a class of bug explicitly called out by the phase's PITFALLS policy.
**Fix:** Raise explicitly when coordinate alignment is required but unavailable:
```python
if prod_complex.shape != ref_complex.shape:
    if not (prod_x is not None and ref_x is not None
            and prod_y is not None and ref_y is not None):
        raise ValueError(
            f"CSLC shape mismatch ({prod_complex.shape} vs {ref_complex.shape}) "
            f"but coordinates unavailable for alignment in {product_path} / {reference_path}"
        )
    # ... existing alignment code ...
```

### WR-03: Race condition on COG heal temp file

**File:** `src/subsideo/_cog.py:114-123`
**Issue:** `ensure_valid_cog` writes to a deterministic temp path `path.with_suffix(path.suffix + ".cogtmp")` then `tmp.replace(path)`. If two parallel product pipelines target the same output path (legitimate when pipelines share an output dir with distinct seeds but identical final paths), both processes write to the same `.cogtmp` filename concurrently, and one `replace()` overwrites a half-written file — corrupting the output COG silently.
**Fix:** Use a unique tempfile per heal call via `tempfile.NamedTemporaryFile(..., dir=path.parent, delete=False)`:
```python
import tempfile
tmp_fd = tempfile.NamedTemporaryFile(
    prefix=path.stem + ".", suffix=".cogtmp",
    dir=path.parent, delete=False,
)
tmp_fd.close()
tmp = Path(tmp_fd.name)
try:
    cog_translate(src=str(path), dst=str(tmp), profile=profile,
                  in_memory=False, quiet=True)
    tmp.replace(path)
except Exception:
    tmp.unlink(missing_ok=True)
    raise
```

### WR-04: `_CONFIGURED` flag not thread-safe

**File:** `src/subsideo/_mp.py:31-88`
**Issue:** The module-global `_CONFIGURED` sentinel is read-checked then set without a lock. A multi-threaded caller (matplotlib + loguru background thread + a worker thread calling `configure_multiprocessing`) could race — two threads both observe `_CONFIGURED is False` and both call `mp.set_start_method(..., force=True)`. The second call raises `RuntimeError` (caught by the `except RuntimeError` pass, so no crash) but could corrupt `MPLBACKEND` or `RLIMIT_NOFILE` if each thread partially applies the bundle. Low probability in practice — the function is called at product-entry before any worker threads — but worth hardening.
**Fix:** Use a module-level `threading.Lock` with double-checked locking:
```python
import threading
_CONFIGURE_LOCK = threading.Lock()

def configure_multiprocessing() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    with _CONFIGURE_LOCK:
        if _CONFIGURED:
            return
        # ... existing body ...
        _CONFIGURED = True
```

### WR-05: Division by zero in CSLC coherence computation

**File:** `src/subsideo/validation/compare_cslc.py:169-170`
**Issue:** `ifg_norm = ifg / np.abs(ifg)` — where any pixel has `ifg == 0` (both `prod_masked` and `ref_masked` real and imag zero after masking), division produces `nan+nan*j`. Propagation: `np.mean(ifg_norm)` returns NaN, `coherence` becomes NaN and is stored verbatim in the measurement dict. Downstream `evaluate()` comparison `float(nan) > 0` is always False, so the gate silently fails without diagnostic. The pre-mask on line 126 excludes `np.abs(prod_complex) > 0` and `np.abs(ref_complex) > 0`, but this does NOT guarantee `np.abs(prod * conj(ref)) > 0`.
**Fix:** Mask ifg to strictly non-zero magnitudes before normalization, or use `np.where`:
```python
ifg_nonzero_mask = np.abs(ifg) > 1e-12
if np.any(ifg_nonzero_mask):
    ifg_norm = ifg[ifg_nonzero_mask] / np.abs(ifg[ifg_nonzero_mask])
    coherence = float(np.abs(np.mean(ifg_norm)))
else:
    coherence = 0.0
```

### WR-06: `sqlite3.connect` context manager does not close connection

**File:** `src/subsideo/burst/db.py:216-220`
**Issue:** `with sqlite3.connect(str(db_path)) as conn:` — Python's `sqlite3.Connection` context manager commits/rollbacks on exit but does NOT close the connection (CPython docs, sqlite3 §connect, and confirmed behavior). Every `query_bounds` call leaks one open file-descriptor to the SQLite database. Over a long-running eval batch this accumulates.
**Fix:** Use explicit close via try/finally or `contextlib.closing`:
```python
import contextlib
with contextlib.closing(sqlite3.connect(str(db_path))) as conn:
    row = conn.execute(
        "SELECT geometry_wkt FROM burst_id_map WHERE burst_id_jpl = ?",
        (burst_id,),
    ).fetchone()
```

### WR-07: Missing `urllib.error` import for exception handler

**File:** `src/subsideo/validation/compare_dswx.py:4,110`
**Issue:** The module imports `urllib.request` on line 4 but references `urllib.error.HTTPError` on line 110. CPython's `urllib.request` transitively imports `urllib.error` in recent versions, which makes this work today, but relying on implicit transitive imports is fragile across Python versions and linters (Pyflakes/Ruff F401 equivalents flag this). An explicit import is one line and avoids future breakage.
**Fix:**
```python
import urllib.error
import urllib.request
```

### WR-08: Unvalidated metrics path in matrix manifest

**File:** `src/subsideo/validation/matrix_writer.py:148`
**Issue:** `metrics_path = Path(cell["metrics_file"])` accepts any string from the YAML manifest without validation. A manifest with `metrics_file: ../../../etc/passwd` would resolve outside the expected `results/` / `eval-*/` tree. Because `matrix_writer` only READS the file, the security impact is bounded (no write-side path-traversal), but an attacker who controls the manifest could use it to leak file paths or trigger MetaJson/MetricsJson validation errors on unrelated files. Documented as defense-in-depth per phase threat model (T-07-06 family).
**Fix:** Validate that `metrics_path` is inside an allow-list (e.g., subdirectories of `cwd`):
```python
metrics_path = Path(cell["metrics_file"]).resolve()
try:
    metrics_path.relative_to(Path.cwd().resolve())
except ValueError:
    raise ValueError(
        f"manifest {manifest_path}: cell metrics_file {cell['metrics_file']!r} "
        f"resolves outside the working tree ({metrics_path}); refusing to load."
    )
```

### WR-09: `credential_preflight` treats whitespace-only values as set

**File:** `src/subsideo/validation/harness.py:298-303`
**Issue:** `if not os.environ.get(v)` is falsy for empty string but truthy for whitespace-only (`" "`, `"\t"`). A user who mis-edits `.env` with trailing whitespace will pass this gate and fail deeper in the pipeline with a less-actionable error.
**Fix:** Strip before truthiness check:
```python
missing = [v for v in env_vars if not (os.environ.get(v) or "").strip()]
```

### WR-10: Supervisor accepts script paths from any location without path validation

**File:** `src/subsideo/validation/supervisor.py:231-234,296-305`
**Issue:** `subprocess.Popen([sys.executable, str(script_path)], start_new_session=True)` launches whatever Python file the user passes. No shell interpolation, so shell-injection is not the concern; however, there is no input validation that `script_path` is within the repo's `run_eval_*.py` contract (exists, is a regular file, owned-by-user, not symlinked outside the tree). An attacker who can run `python -m subsideo.validation.supervisor /tmp/evil.py` on a shared-HPC submit node would execute `/tmp/evil.py` under the submit user's credentials. This is the documented threat model (T-07-01) per the supervisor's docstring, but the implementation does not enforce the whitelist implied by the Makefile callers.
**Fix:** Validate the script path matches an expected pattern:
```python
if not script_path.is_file():
    raise SystemExit(f"supervisor: {script_path} is not a regular file")
if script_path.is_symlink():
    raise SystemExit(f"supervisor: {script_path} is a symlink; refusing to execute")
if not script_path.name.startswith("run_eval"):
    logger.warning("supervisor: {} does not match run_eval_*.py naming convention", script_path)
```

## Info

### IN-01: `CRITERIA` dict itself is mutable despite frozen dataclass entries

**File:** `src/subsideo/validation/criteria.py:39-158`
**Issue:** `@dataclass(frozen=True)` makes each `Criterion` instance immutable, but `CRITERIA: dict[str, Criterion]` is an ordinary dict — `CRITERIA["rtc.rmse_db_max"] = Criterion(...)` or `del CRITERIA[...]` succeeds silently. The phase's immutability contract ("Editing this file requires citing an ADR") is enforced at review-time, but a rogue runtime mutation from a test fixture or monkeypatch could drift undetected in matrix output.
**Fix:** Wrap in `types.MappingProxyType` at module end to make the dict read-only at runtime:
```python
from types import MappingProxyType
_CRITERIA_MUT: dict[str, Criterion] = {
    "rtc.rmse_db_max": Criterion(...),
    # ... all entries ...
}
CRITERIA: Mapping[str, Criterion] = MappingProxyType(_CRITERIA_MUT)
```

### IN-02: `is_north=1` hardcoded for all EU burst DB records

**File:** `src/subsideo/burst/db.py:146`
**Issue:** `records.append((jpl_id, esa_id, rel_orbit, b_index, swath, geom_wkt, epsg, 1))` — the `is_north` column is always set to 1. The default `eu_bounds` of `(-32.0, 27.0, 45.0, 72.0)` covers only the Northern Hemisphere so this is correct today, but a future caller passing Southern-Hemisphere AOI bounds (e.g., to cover Portuguese overseas territories or ESA's southern polar missions) would get silently wrong `is_north` values.
**Fix:** Compute from centroid latitude:
```python
is_north = 1 if centroid.y >= 0 else 0
records.append((jpl_id, esa_id, rel_orbit, b_index, swath, geom_wkt, epsg, is_north))
```

### IN-03: Return type hint on `_load_cslc_complex` understates Optional coords

**File:** `src/subsideo/validation/compare_cslc.py:20-25`
**Issue:** The annotation `-> tuple[np.ndarray, np.ndarray, np.ndarray]` claims all three returned arrays are non-None, but lines 54-64 leave `x_coords`/`y_coords` as `None` when neither candidate path is present in the HDF5. Callers (line 88-89) destructure freely without `None`-handling until the downstream `is not None` check. A mypy-strict pass would flag this as `Incompatible return value type`.
**Fix:** Correct the hint:
```python
def _load_cslc_complex(
    hdf5_path: Path,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None]:
```

### IN-04: Supervisor `_parse_expected_wall_s` returns first match via `ast.walk`

**File:** `src/subsideo/validation/supervisor.py:114-125`
**Issue:** `ast.walk(tree)` yields nodes in BFS order from the root, so the first module-level `EXPECTED_WALL_S = ...` assignment is selected. If a script contains a conditional rebinding (e.g., `if os.environ.get("DEBUG"): EXPECTED_WALL_S = 60`), the watchdog sees the first assignment and ignores the override. Unlikely in the current eval scripts (all declare the literal at module top), but worth a docstring note rather than a code change.
**Fix:** Document the contract explicitly in the docstring — "the FIRST module-level assignment wins; conditional or re-bound EXPECTED_WALL_S is ignored by the watchdog" — and consider refactoring to only inspect top-level `ast.Module.body` assignments:
```python
for stmt in tree.body:
    if isinstance(stmt, ast.Assign):
        for target in stmt.targets:
            if isinstance(target, ast.Name) and target.id == "EXPECTED_WALL_S":
                # ... return ...
```

### IN-05: `rasterio.windows.transform` referenced via `rasterio.windows` while module imported as local name

**File:** `src/subsideo/validation/compare_dswx.py:261-264`
**Issue:** Line 183 imports `from rasterio.windows import Window, from_bounds as window_from_bounds`, but line 261 calls `rasterio.windows.transform(...)` via the top-level `rasterio` module (imported on line 180). This works (rasterio re-exports submodules) but is inconsistent with the local aliasing style. Minor nit.
**Fix:** Add `transform` to the local import for consistency:
```python
from rasterio.windows import (
    Window,
    from_bounds as window_from_bounds,
    transform as window_transform,
)
# ... and use window_transform(...) on line 261
```

---

_Reviewed: 2026-04-22T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
