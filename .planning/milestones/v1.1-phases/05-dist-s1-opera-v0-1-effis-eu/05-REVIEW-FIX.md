---
phase: 05-dist-s1-opera-v0-1-effis-eu
fixed_at: 2026-04-26T00:00:00Z
review_path: .planning/phases/05-dist-s1-opera-v0-1-effis-eu/05-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 5: Code Review Fix Report

**Fixed at:** 2026-04-26
**Source review:** `.planning/phases/05-dist-s1-opera-v0-1-effis-eu/05-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (2 HIGH + 4 MEDIUM; LOW + INFO out of scope per fix_scope=critical_warning)
- Fixed: 6
- Skipped: 0
- Out-of-scope (not addressed): LO-01, LO-02, LO-03, IN-01, IN-02, IN-03, IN-04

## Fixed Issues

### HI-01: `ensure_resume_safe` called with glob pattern instead of exact filename

**Files modified:** `run_eval_dist_eu.py`
**Commit:** `1c633e4`
**Applied fix:** Replaced the call `ensure_resume_safe(out_dir, ["*GEN-DIST-STATUS.tif"])` (which performs exact filename membership testing per `harness.py:432`, never matching the literal wildcard string) with `next(out_dir.glob("*GEN-DIST-STATUS.tif"), None)` guarded by `out_dir.exists()`. Removed the now-unused `ensure_resume_safe` import. The resume guard now actually short-circuits warm cache invocations as the comment described.

### HI-02: `dist_s1_hang` Literal status is unreachable in `_chained_retry_for_aveiro`

**Files modified:** `run_eval_dist_eu.py`
**Commit:** `d33b3af`
**Applied fix:** Added `except TimeoutError as e:` ahead of the generic `except Exception` handler, returning a `ChainedRunResult(status="dist_s1_hang", ...)`. The `ChainedRunStatus` Literal value `'dist_s1_hang'` (matrix_schema.py:646) is now reachable via in-process timeout / wallclock supervisor exceptions. Out-of-process SIGKILL still bypasses the handler entirely (the script terminates and an external supervisor reports separately) - this is documented in the new handler comment.
**Note:** This is a logic-correctness change that becomes observable only when a supervisor / dist_s1 internal timer actually raises `TimeoutError`. Tier-1 and Tier-2 verification confirm the syntax + control flow; runtime supervisor wiring should be confirmed by a developer.

### ME-01: `raw_features` list comprehension uses `first` geometry for all features

**Files modified:** `src/subsideo/validation/effis.py`
**Commit:** `010c6b1`
**Applied fix:** Changed `first.get("shape") or first.get("centroid")` to `f.get("shape") or f.get("centroid")` (and the `isinstance(first, dict)` guard to `isinstance(f, dict)`) inside the non-GeoJSON branch comprehension. Each feature now carries its own geometry instead of all features being collapsed onto the first feature's geometry. Properties extraction was already correctly using `f`.

### ME-02: Retry parameters in `_build_retry_session` hardcoded, diverging from `RETRY_POLICY`

**Files modified:** `src/subsideo/validation/effis.py`, `src/subsideo/validation/harness.py`
**Commit:** `44425e8`
**Applied fix:** Added `max_attempts: 5` and `backoff_factor: 2` keys to `RETRY_POLICY['EFFIS']` in `harness.py`. Updated `_build_retry_session` in `effis.py` to read both via `policy.get(...)`, with the historical hardcoded values as defaults. The `RETRY_POLICY` dict is now the genuine single source of truth for retry semantics; future tweaks no longer require parallel edits in two files.

### ME-03: `DistNamCellMetrics` v1.2 path will fall through to `RUN_FAILED` in matrix_writer when `cell_status != 'DEFERRED'`

**Files modified:** `src/subsideo/validation/matrix_writer.py`
**Commit:** `acea4e6`
**Applied fix:** Broadened `_is_dist_nam_shape` to discriminate on `reference_source` + `cmr_probe_outcome` keys (both present across all `DistNamCellMetrics` versions per the v1.1 schema and v1.2 extension plan in D-24/D-25) instead of `cell_status == 'DEFERRED'`. Updated `_render_dist_nam_deferred_cell` to read `cell_status` from the raw dict and emit `f"{cell_status} (CMR: {cmr_outcome})"` so v1.2 PASS/FAIL cells render verbatim instead of being mislabelled as DEFERRED. The v1.1 unit test `test_dist_nam_deferred_render` continues to pass byte-identically (its fixture sets `cell_status='DEFERRED'`, which yields the same output string as before).

### ME-04: `input_hashes` in `run_eval_dist_eu.py` stores truncated filter strings, not hashes

**Files modified:** `run_eval_dist_eu.py`
**Commit:** `7ed7f62`
**Applied fix:** Added `import hashlib`. Replaced `r.effis_query_meta.filter_string[:64]` with `hashlib.sha256(r.effis_query_meta.filter_string.encode("utf-8")).hexdigest()` so `MetaJson.input_hashes` actually stores the SHA256 hex digest its field description promises. Provenance audits now receive a real digest, not a truncated query trace.

## Skipped Issues

None - all in-scope findings were fixed.

## Out-of-Scope (Not Addressed)

The following findings were not addressed because the configured `fix_scope=critical_warning` excludes LOW and INFO severities:

| ID | File | Severity | Summary |
|----|------|----------|---------|
| LO-01 | `tests/unit/test_bootstrap.py` | LOW | NaN-propagation test relies on undocumented NaN-masking behaviour of `f1_score` |
| LO-02 | `run_eval_dist_eu.py` | LOW | All logic inside `__main__` guard; EU eval is untestable without `importlib` workarounds |
| LO-03 | `src/subsideo/validation/effis.py` | LOW | `_country_for_bbox` Portugal check may miss eastern Portugal centroid lon > -6.0 |
| IN-01 | `src/subsideo/validation/bootstrap.py` | INFO | `n_blocks_dropped` formula note - correct, for transparency |
| IN-02 | `src/subsideo/validation/effis.py` | INFO | `sess._effis_abort_on` custom attribute on Session; robust but non-standard |
| IN-03 | `run_eval_dist.py` | INFO | `NotImplementedError` re-raise comment could clarify v1.2-trigger semantics |
| IN-04 | `pyproject.toml` | INFO | `owslib` pin unused after WFS-to-REST pivot in Phase 5 |

These can be addressed in a follow-up pass with `fix_scope=all` or by manual maintenance.

## Verification Performed

For each finding:
- **Tier 1 (always):** Re-read each modified file section, confirmed fix text present and surrounding code intact.
- **Tier 2 (preferred):** Ran `python3 -c "import ast; ast.parse(open(...).read())"` for every modified `.py` file - all passed.
- **Test impact (ME-03 spot-check):** Inspected `tests/unit/test_matrix_writer_dist.py:142-164` and confirmed the `test_dist_nam_deferred_render` assertion `ra_col == "DEFERRED (CMR: operational_not_found)"` still holds because the test fixture sets `cell_status='DEFERRED'` and the new `f"{cell_status} (CMR: {cmr_outcome})"` format produces the same string for that input.

The full `pytest` suite was not executed by this fixer (per workflow scope: full-suite verification belongs to the verifier phase). HI-02 specifically introduces a logic distinction whose runtime path requires supervisor wiring to exercise; the developer should manually confirm that the project's hang-detection mechanism actually raises `TimeoutError` (vs. a custom exception class or out-of-process SIGKILL) so the new handler triggers as intended.

---

_Fixed: 2026-04-26_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
