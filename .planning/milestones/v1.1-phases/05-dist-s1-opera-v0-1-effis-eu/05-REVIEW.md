---
phase: 05-dist-s1-opera-v0-1-effis-eu
reviewed: 2026-04-25T00:00:00Z
depth: standard
iteration: 1
files_reviewed: 11
files_reviewed_list:
  - run_eval_dist.py
  - run_eval_dist_eu.py
  - src/subsideo/validation/bootstrap.py
  - src/subsideo/validation/effis.py
  - src/subsideo/validation/harness.py
  - src/subsideo/validation/matrix_schema.py
  - src/subsideo/validation/matrix_writer.py
  - pyproject.toml
  - tests/unit/test_bootstrap.py
  - tests/unit/test_matrix_writer_dist.py
  - tests/unit/test_run_eval_dist_cmr_stage0.py
findings:
  critical: 0
  high: 2
  medium: 4
  low: 3
  info: 4
  total: 13
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-04-25
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 5 adds the DIST-S1 validation layer: the `bootstrap.py` module, `effis.py` REST
client, two eval scripts (`run_eval_dist.py`, `run_eval_dist_eu.py`), Pydantic schema
extensions in `matrix_schema.py`, and render branches in `matrix_writer.py`, plus
corresponding unit tests.

The code is generally well-structured and follows established project patterns
(declarative EVENTS list, per-event try/except isolation, lazy imports, module-level
constants). No hardcoded credentials or command-injection vectors were found.

Two HIGH findings require attention before the phase closes:

1. **ensure_resume_safe glob pattern** (`run_eval_dist_eu.py:273`): the call passes
   `["*GEN-DIST-STATUS.tif"]` (a glob pattern) to `ensure_resume_safe`, which performs
   exact filename membership testing, not glob matching. The check always returns `False`
   for a populated cache dir, so the resume guard never short-circuits and `dist_s1` is
   re-run unnecessarily (or worse, the output directory is not skipped correctly).

2. **`_chained_retry_for_aveiro` uses `dist_s1_hang` status only from the external try/except, never internally** (`run_eval_dist_eu.py:294–342`): the chained retry catch converts ALL exceptions -- including a supervisor-detected hang -- to `status='crashed'`. The Literal `dist_s1_hang` is therefore dead code in this implementation. This is only an accuracy issue in the schema documentation, not a crash, but it means the CONCLUSIONS and metrics.json distinction between "hung" and "crashed" is never made.

Four MEDIUM findings address logic correctness issues that can affect metric accuracy:

3. `effis.py` non-GeoJSON branch (lines 323–337): the list comprehension that builds
   `raw_features` uses `first.get(...)` for geometry on every iteration, but `f` is the
   loop variable — the geometry is always taken from `first`, not from `f`. All features
   past the first will carry the first feature's geometry.

4. `run_eval_dist_eu.py` mask type mismatch: `subsideo_mask` (from `_binarize_dist`) is
   float32, but `mask_at_false` / `mask_at_true` are also cast to float32 from uint8.
   The metric functions (`f1_score`, etc.) may expect integer/boolean labels; the
   contract with `metrics.py` should be verified.

5. `effis.py` `_build_retry_session` hardcodes `total=5` and `backoff_factor=2` rather
   than reading from `RETRY_POLICY['EFFIS']`. The RETRY_POLICY declaration is the
   single source of truth, but those values are duplicated and can diverge.

6. `matrix_writer.py` `_load_metrics` (line 59): when a metrics file is a recognised
   subtype (e.g., `DistEUCellMetrics`), the dispatch happens via specialised renderers.
   However, if the file is a `DistNamCellMetrics` but `_is_dist_nam_shape` returns False
   (e.g., `cell_status` is something other than `'DEFERRED'`), the file falls through to
   `_load_metrics` which validates against base `MetricsJson` with `extra='forbid'` --
   the `cell_status`, `reference_source`, and `cmr_probe_outcome` fields will cause a
   Pydantic rejection and surface `RUN_FAILED`. This becomes the only render path if
   `cell_status` is ever set to `'PASS'` or `'FAIL'` in v1.2 without a corresponding
   new discriminator being added.

---

## High Issues

### HI-01: `ensure_resume_safe` called with glob pattern instead of exact filename

**File:** `run_eval_dist_eu.py:273`

**Issue:** `ensure_resume_safe(out_dir, ["*GEN-DIST-STATUS.tif"])` passes a glob-style
wildcard pattern as the `manifest_keys` argument. The implementation in `harness.py:432`
builds `{p.name for p in cache_dir.iterdir()}` and checks exact membership
(`all(k in existing for k in manifest_keys)`). The string `"*GEN-DIST-STATUS.tif"` is
never equal to any actual filename such as
`"OPERA_L3_DIST-ALERT-S1_T29TNF_..._GEN-DIST-STATUS.tif"`, so the resume guard always
returns `False`. Consequence: every invocation re-runs `dist_s1` even on a warm cache,
multiplying wall time by 3-4x for the aveiro chained triple. No data corruption, but the
behaviour contradicts the intent documented in the function body and the comment
`"dist_s1 cached for ... at {}"` that follows.

**Fix:**
```python
# Option A: use glob matching in the helper (change harness.py contract)
#   -- invasive change, not recommended

# Option B: pass the sentinel file directly (preferred; no harness change needed)
from pathlib import Path

def _run_dist_for_event_post(cfg, post_date, out_dir, prior_product=None):
    from dist_s1 import run_dist_s1_workflow

    # Check for a concrete output file, not a glob pattern.
    # pick_first is None when the directory is empty/absent.
    existing_sentinel = next(out_dir.glob("*GEN-DIST-STATUS.tif"), None)
    if existing_sentinel is not None:
        logger.info("dist_s1 cached for {} {} at {}", cfg.event_id, post_date, out_dir)
        return out_dir
    # ... rest of the function unchanged
```

Alternatively, update `ensure_resume_safe` to accept a `glob_patterns` flag, but the
direct `next(..., None)` idiom is simpler and avoids changing the shared helper's
contract.

---

### HI-02: `dist_s1_hang` Literal status is unreachable in `_chained_retry_for_aveiro`

**File:** `run_eval_dist_eu.py:294–342`

**Issue:** The `ChainedRunStatus` Literal includes `'dist_s1_hang'` (matrix_schema.py
line 646), and CONTEXT D-14 defines it as a distinct outcome. However,
`_chained_retry_for_aveiro` catches all exceptions via `except Exception as e:` and
maps them to `status='crashed'`. A `dist_s1` hang detected by the supervisor sends
`SIGKILL`, which surfaces as `KeyboardInterrupt` or `SystemExit`, both of which are
NOT caught by `except Exception`. So `dist_s1_hang` is never produced by this code path
-- hangs either propagate as uncaught signals (crashing the script) or appear as
`'crashed'` when an internal timeout mechanism raises a normal `Exception`. The CONCLUSIONS
and metrics.json distinction promised by D-14 is never made. This is a documentation
accuracy issue, but it means the `any_chained_run_failed` aggregate flag will treat
`'crashed'` the same as `'dist_s1_hang'` (per the `status not in ("structurally_valid",
"skipped")` check at line 512), which is correct for the gate but incorrect for the
narrative.

**Fix:**
```python
# In _chained_retry_for_aveiro, distinguish hang vs crash explicitly
# by catching TimeoutError or a dist_s1-specific HangError before the generic handler:
except TimeoutError as e:
    logger.error("chained_retry HANG for {}: {}", cfg.event_id, e)
    return ChainedRunResult(
        status="dist_s1_hang",
        output_dir=str(chained_dst) if chained_dst.exists() else None,
        error=repr(e),
        traceback=traceback.format_exc(),
    )
except Exception as e:
    logger.error("chained_retry crashed for {}: {}", cfg.event_id, e)
    return ChainedRunResult(
        status="crashed",
        ...
    )
```

If the supervisor's `os.killpg` raises a different signal-related exception, add it to
the hang handler. The key fix is ensuring at least one code path can produce
`'dist_s1_hang'` so the Literal is not dead code.

---

## Medium Issues

### ME-01: `raw_features` list comprehension uses `first` geometry for all features

**File:** `src/subsideo/validation/effis.py:323–337`

**Issue:** In the non-GeoJSON branch of `fetch_effis_perimeters`, `raw_features` is
built with:
```python
raw_features = [
    {
        "type": "Feature",
        "geometry": (
            first.get("shape") or first.get("centroid")  # BUG: 'first', not 'f'
            if isinstance(first, dict) else None
        ),
        "properties": {
            k: v for k, v in (f.items() if isinstance(f, dict) else {}.items())
            if k not in ("shape", "centroid")
        },
    }
    for f in features
]
```
The `geometry` field is evaluated from `first` (the first element, captured before the
loop) rather than from the loop variable `f`. Every feature in the output will carry the
geometry of the first feature. Properties come from `f` correctly, but geometries are
all identical. Result: all post-filter burn perimeters are collapsed to one geometry;
rasterisation will be substantially wrong if the REST API returns non-GeoJSON
responses.

**Fix:**
```python
raw_features = [
    {
        "type": "Feature",
        "geometry": (
            f.get("shape") or f.get("centroid")   # fixed: 'f' not 'first'
            if isinstance(f, dict) else None
        ),
        "properties": {
            k: v for k, v in (f.items() if isinstance(f, dict) else {}.items())
            if k not in ("shape", "centroid")
        },
    }
    for f in features
]
```

Note: the EFFIS REST API currently returns GeoJSON (with a `"geometry"` key) so the
first branch is taken and the bug is dormant. But the fallback branch is the declared
"plain dict" handler and is incorrect.

---

### ME-02: Retry parameters in `_build_retry_session` hardcoded, diverging from `RETRY_POLICY`

**File:** `src/subsideo/validation/effis.py:127–132`

**Issue:** `_build_retry_session` hardcodes `total=5` and `backoff_factor=2`, while
`RETRY_POLICY['EFFIS']` declares `max_attempts: 5` and `backoff_factor: 2` in the
harness comment. If RETRY_POLICY['EFFIS'] is ever updated (e.g., to reduce attempts for
WAF-sensitive calls), the `_build_retry_session` copy will be silently stale. The
RETRY_POLICY is the declared single source of truth per the harness architecture.

**Fix:**
```python
def _build_retry_session() -> requests.Session:
    from urllib3.util.retry import Retry

    policy = RETRY_POLICY["EFFIS"]
    status_forcelist = [s for s in policy["retry_on"] if isinstance(s, int)]
    # Read retry params from the policy, not hardcoded
    max_attempts = policy.get("max_attempts", 5)
    backoff_factor = policy.get("backoff_factor", 2)
    retry = Retry(
        total=max_attempts,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    ...
```

Note: `RETRY_POLICY['EFFIS']` in `harness.py` does not currently include
`max_attempts` or `backoff_factor` keys (the CONTEXT D-18 declaration mentions them but
the actual dict only has `retry_on`, `abort_on`). Adding those keys to the dict and
reading them here would fully close the gap.

---

### ME-03: `DistNamCellMetrics` (v1.2 path) will fall through to `RUN_FAILED` in matrix_writer when `cell_status != 'DEFERRED'`

**File:** `src/subsideo/validation/matrix_writer.py:464–484`

**Issue:** `_is_dist_nam_shape` discriminates on `raw.get("cell_status") == "DEFERRED"`.
When v1.2 lands and the cell graduates to `cell_status='PASS'` or `'FAIL'`, the
discriminator returns `False`. The file then falls through to `_load_metrics`, which
validates against base `MetricsJson` with `extra='forbid'`. `DistNamCellMetrics` adds
`cell_status`, `reference_source`, `cmr_probe_outcome`, `reference_granule_id`, and
`deferred_reason` -- all five will cause a Pydantic `ValidationError`, and the cell
renders as `RUN_FAILED`. This is a forward-compatibility gap documented in D-24 / D-25
as a v1.2 concern, but it is not obvious from the code and will cause a silent
regression.

**Fix:** Document the fragility explicitly inline and add a forward-guard:
```python
def _is_dist_nam_shape(metrics_path: Path) -> bool:
    """...
    NOTE: v1.2 forward-compat: when cell_status transitions to PASS/FAIL,
    this discriminator will return False and the file will fall through to
    _load_metrics, which will surface RUN_FAILED because DistNamCellMetrics-
    specific fields are forbidden by base MetricsJson. v1.2 must add a new
    discriminator branch (e.g., check for 'reference_source' key regardless
    of cell_status) and a corresponding _render_dist_nam_full_cell renderer.
    """
    import json as _json
    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.debug("_is_dist_nam_shape: cannot read {}: {}", metrics_path, e)
        return False
    return (
        isinstance(raw, dict)
        and "reference_source" in raw   # present in all DistNamCellMetrics versions
        and "cmr_probe_outcome" in raw  # v1.2 still carries this
    )
```

This makes the discriminator v1.2-safe without requiring a schema break.

---

### ME-04: `input_hashes` in `run_eval_dist_eu.py` stores truncated filter strings, not hashes

**File:** `run_eval_dist_eu.py:575–578`

**Issue:**
```python
input_hashes={
    f"effis_perimeters_{r.event_id}": r.effis_query_meta.filter_string[:64]
    for r in per_event if r.effis_query_meta.filter_string
},
```
`MetaJson.input_hashes` is declared as `dict[str, str]` with description "SHA256 hex
of primary inputs". The code stores the first 64 characters of the EFFIS filter string
parameter dict (e.g., `"{'firedate__gte': '2024-09-15T00:00:00Z', 'firedate__lte'..."`
). This is not a hash; it is a truncated query parameter trace. The field description
says SHA256, so downstream consumers (or audits) that expect hex digests will get
malformed values. For Phase 5's deferred eval path and the honest-FAIL outcome, this is
low-impact, but the field is a provenance contract.

**Fix:**
```python
import hashlib

input_hashes={
    f"effis_perimeters_{r.event_id}": hashlib.sha256(
        r.effis_query_meta.filter_string.encode()
    ).hexdigest()
    for r in per_event if r.effis_query_meta.filter_string
},
```

---

## Low Issues

### LO-01: `test_nan_propagation_through_metric_fn` may be a false pass if `f1_score` returns NaN on all-NaN input

**File:** `tests/unit/test_bootstrap.py:83–101`

**Issue:** The test asserts `np.isfinite(result.point_estimate)` after injecting NaN
into 5% of pixels. This is only a meaningful test if `metrics.f1_score` masks NaN
internally and returns a finite F1. If `f1_score` is not NaN-aware (e.g., it naively
sums without masking), the assertion will pass with `NaN` because `np.isfinite(NaN)`
is `False`, causing a pytest failure -- but only if the metric returns NaN consistently.
The test relies on an undocumented property of `f1_score`. Since `bootstrap.py:93–94`
documents "NaN values are passed through to `metric_fn` which is expected to mask
internally", the test should verify that contract rather than assume it.

**Fix:** Add an assertion that the `metrics.f1_score` function is NaN-aware, or mock
it with a known NaN-safe implementation in this test.

---

### LO-02: All imports in `run_eval_dist_eu.py` are inside `if __name__ == "__main__":`, making the module untestable without `importlib` workarounds

**File:** `run_eval_dist_eu.py:48–593`

**Issue:** All top-level business logic, including `EventConfig`, `EVENTS`,
`process_event`, and `_run_dist_for_event_post`, lives inside the `if __name__ ==
"__main__":` guard. Unlike `run_eval_dist.py` which refactored logic into a `run()`
function that tests can call directly (enabling `test_run_eval_dist_cmr_stage0.py`),
there is no equivalent for `run_eval_dist_eu.py`. The EU eval is not unit-tested at all
(the unit test suite for it was explicitly out of scope per the summaries, but this
creates a pattern inconsistency). If tests are added later, they will require the same
`importlib.util.spec_from_file_location` workaround used in the NAM test.

**Fix (medium term):** Refactor `run_eval_dist_eu.py` to follow the same `run()`
function pattern as `run_eval_dist.py`, with the `__main__` guard calling `run()`.

---

### LO-03: `_country_for_bbox` fallback order: Portugal check is shadowed by Spain check for some AOIs

**File:** `src/subsideo/validation/effis.py:155–161`

**Issue:** The lon range check for Spain is `-10.0 <= lon <= 5.0 and 35.0 <= lat <= 45.0`.
The Portugal check is `-10.0 <= lon <= -6.0 and 39.0 <= lat <= 42.0`. For a bbox
centroid at lon=-7, lat=40 (which would be central Portugal), the Portugal check fires
first and returns `'PT'` correctly. However, for the Aveiro bbox `(-8.8, 40.5, -8.2,
41.0)`, centroid lon=-8.5, lat=40.75 -- Portugal branch fires correctly.

For an AOI centred around lon=-6.5 (eastern Portugal), the check `-10.0 <= -6.5 <= -6.0`
is False (the right bound is -6.0), so the Portugal check misses and the Spain check
matches. This is a minor heuristic issue but could silently cause Aveiro variant AOIs
to be queried with country='ES' instead of 'PT'. The three locked events are fine; the
risk is for future events.

**Fix:** Tighten the docstring to state this heuristic only covers the three locked Phase 5
events, or expand the lon bounds to `-10.0 <= lon <= -5.0` to capture mainland Portugal.

---

## Info Items

### IN-01: `bootstrap.py` `n_blocks_dropped` formula counts corners twice

**File:** `src/subsideo/validation/bootstrap.py:134`

The formula `(n_block_rows + 1) * (n_block_cols + 1) - n_blocks_kept` gives the count
of partial cells (east strip + south strip + SE corner) as tested by `test_block_count_math_for_t11slt_shape`.
For T11SLT: (110+1)*(110+1) - 12100 = 12321 - 12100 = 221. This matches the test
assertion and the RESEARCH Probe 9 corrected count. No bug; this is an informational
note that the formula counts the SE corner partial block (which is neither purely east
nor purely south strip) as 1 partial, which is correct.

---

### IN-02: `sess._effis_abort_on` stores state on `requests.Session` as a private attribute

**File:** `src/subsideo/validation/effis.py:139`

`sess._effis_abort_on = policy.get(...)` attaches a custom attribute to a
`requests.Session` object using a name-mangled-style prefix. This is an acceptable
workaround given the urllib3 Retry API doesn't support abort-on semantics, but it
relies on `requests.Session` accepting arbitrary attributes (which it does). The
`getattr(session, "_effis_abort_on", [...])` call at line 274 correctly provides a
fallback, so this is robust.

---

### IN-03: `run_eval_dist.py` catches `NotImplementedError` then immediately re-raises it

**File:** `run_eval_dist.py:236–238`

```python
except NotImplementedError:
    raise  # Re-raise the v1.2-trigger signal
except Exception as e:
    ...
```
This is correct and intentional (the NotImplementedError must propagate up to the
supervisor), but the pattern is slightly unusual. A comment clarifying that `NotImplementedError`
is a v1.2-trigger signal (not a bug) would improve readability for future maintainers.
The comment at lines 221–232 explains this in the raise site but not in the re-raise
site.

---

### IN-04: `pyproject.toml` pins `owslib>=0.35,<1` but `effis.py` does not import owslib

**File:** `pyproject.toml:126`, `src/subsideo/validation/effis.py`

The CONTEXT D-18 amendment switched from WFS (owslib) to REST API (requests) after the
WFS endpoints failed. The `owslib` dependency in `pyproject.toml` is now unused by Phase
5 code -- `effis.py` uses `requests` directly, not `owslib.wfs.WebFeatureService`. The
pin is harmless but adds an unused dependency. If the WFS path is never re-activated,
this pin can be removed.

---

## Finding Summary Table

| ID | File | Line | Severity | Summary |
|----|------|------|----------|---------|
| HI-01 | `run_eval_dist_eu.py` | 273 | HIGH | `ensure_resume_safe` called with glob pattern; always returns False |
| HI-02 | `run_eval_dist_eu.py` | 294-342 | HIGH | `dist_s1_hang` Literal status is unreachable; all exceptions map to `crashed` |
| ME-01 | `src/subsideo/validation/effis.py` | 323-337 | MEDIUM | `raw_features` list comprehension uses `first.get(geometry)` instead of `f.get(geometry)` for all features |
| ME-02 | `src/subsideo/validation/effis.py` | 127-132 | MEDIUM | Retry params `total=5` / `backoff_factor=2` hardcoded; diverge from RETRY_POLICY |
| ME-03 | `src/subsideo/validation/matrix_writer.py` | 464-484 | MEDIUM | `_is_dist_nam_shape` only matches `cell_status='DEFERRED'`; v1.2 PASS/FAIL cells will surface as `RUN_FAILED` |
| ME-04 | `run_eval_dist_eu.py` | 575-578 | MEDIUM | `input_hashes` stores truncated filter string, not SHA256 hex as declared by `MetaJson` |
| LO-01 | `tests/unit/test_bootstrap.py` | 83-101 | LOW | NaN-propagation test relies on undocumented NaN-masking behaviour of `f1_score` |
| LO-02 | `run_eval_dist_eu.py` | 48-593 | LOW | All logic inside `__main__` guard; EU eval is untestable without `importlib` workarounds |
| LO-03 | `src/subsideo/validation/effis.py` | 155-161 | LOW | `_country_for_bbox` Portugal check may miss eastern Portugal centroid lon > -6.0 |
| IN-01 | `src/subsideo/validation/bootstrap.py` | 134 | INFO | `n_blocks_dropped` formula note -- correct, for transparency |
| IN-02 | `src/subsideo/validation/effis.py` | 139 | INFO | `sess._effis_abort_on` custom attribute on Session; robust but non-standard |
| IN-03 | `run_eval_dist.py` | 236-238 | INFO | `NotImplementedError` re-raise comment could clarify v1.2-trigger semantics |
| IN-04 | `pyproject.toml` | 126 | INFO | `owslib` pin unused after WFS-to-REST pivot in Phase 5 |

---

_Reviewed: 2026-04-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
