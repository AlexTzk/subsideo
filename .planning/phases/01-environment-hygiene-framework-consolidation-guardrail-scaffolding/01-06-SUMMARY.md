---
phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
plan: 06
subsystem: validation
tags: [harness, opera-utils, retry-policy, bounds, mgrs, burst, credentials]

# Dependency graph
requires:
  - phase: 01 (Plan 01-04)
    provides: validation/__init__.py re-export slots (build_stable_mask, coherence_stats, residual_mean_velocity) — Plan 01-06 MUST NOT overwrite
  - phase: 01 (Plan 01-05)
    provides: validation/__init__.py re-export slots (CRITERIA, Criterion, ProductQualityResult, ReferenceAgreementResult, evaluate, measurement_key) — Plan 01-06 MUST NOT overwrite
provides:
  - "subsideo.validation.harness — 6 public helpers + RETRY_POLICY + ReferenceDownloadError"
  - "subsideo.validation.bounds_for_burst — opera_utils primary path + subsideo.burst.db EU fallback (ENV-08)"
  - "subsideo.validation.bounds_for_mgrs_tile — opera_utils primary path + shipped _mgrs_tiles.geojson seed fallback (ENV-08 MGRS-tile consumer)"
  - "subsideo.burst.db.query_bounds — EU-burst bounds lookup via shapely.wkt on the burst_id_map.geometry_wkt column"
  - "src/subsideo/validation/_mgrs_tiles.geojson — seed for 10TFK / 29TNF / 33TXP ships with wheel"
  - "run_eval.py migrated — EXPECTED_WALL_S literal + harness imports + bounds_for_burst (ENV-07 pilot)"
affects: [Plan 01-07 (batch-migrate remaining 6 eval scripts), Plan 01-08 (matrix_writer consumes harness + criteria), Phase 2/3/4/5/6 all eval scripts]

# Tech tracking
tech-stack:
  added:
    - "importlib.resources (stdlib) — read shipped _mgrs_tiles.geojson via packaged resource"
    - "shapely.wkt — re-parse geometry_wkt column in burst_id_map for query_bounds envelope"
  patterns:
    - "Per-source RETRY_POLICY dict with retry_on / abort_on / refresh_url_on keys; caller must pass explicit source (P0.4 mitigation)"
    - "Two-path bounds lookup: opera_utils primary → subsideo-local fallback, with composed ValueError naming both failure causes"
    - "Shipped-with-wheel GeoJSON seed via importlib.resources.files (gitignore *.geojson negated for this path)"
    - "Pilot script shape: EXPECTED_WALL_S module constant + credential_preflight + harness imports inside the `if __name__` guard"

key-files:
  created:
    - "src/subsideo/validation/harness.py (540 lines, 6 helpers + RETRY_POLICY + ReferenceDownloadError)"
    - "src/subsideo/validation/_mgrs_tiles.geojson (seed with 10TFK, 29TNF, 33TXP)"
    - "tests/unit/test_harness.py (20 tests, 277 lines)"
  modified:
    - "src/subsideo/validation/__init__.py (APPEND 8 harness re-exports; Plan 04+05 re-exports preserved; __all__ grew from 9 → 17)"
    - "src/subsideo/burst/db.py (+58 lines: query_bounds function + shapely.wkt import)"
    - "run_eval.py (+12/-1 lines: EXPECTED_WALL_S + harness imports + credential_preflight + bounds_for_burst)"
    - ".gitignore (negation rule for _mgrs_tiles.geojson under the *.geojson block)"

key-decisions:
  - "bounds_for_mgrs_tile: primary path calls opera_utils.burst_frame_db.get_mgrs_tile_geojson inside a try/except; opera-utils 0.25.6 has NO such helper (confirmed via Python introspection), so the seed fallback is the active path. Primary code stays in place for future opera-utils upgrades."
  - "subsideo.burst.db schema lacks separate west/south/east/north columns; query_bounds re-parses geometry_wkt via shapely.wkt.loads and returns .bounds. No schema migration needed."
  - "Seed GeoJSON committed via .gitignore negation (! rule) because *.geojson is a top-level block. Alternative (moving the rule) would touch broader gitignore semantics."
  - "run_eval.py imports all 5 harness names (including 3 currently-unused) per plan instruction ‘still import all 5 so subsequent edits don't need new imports’ — F401 warnings accepted."
  - "Task 2b (_mgrs_tiles.geojson seed) landed in the Task 1 GREEN commit because Task 1's test_bounds_for_mgrs_tile_known_33txp requires the seed to exist; splitting into two commits would have left a broken intermediate state."

patterns-established:
  - "Per-source HTTP retry: retry_on / abort_on dicts keyed by source name; abort_on raises ReferenceDownloadError so caller can distinguish permanent vs transient failure"
  - "CloudFront refresh_url_on = [403]: signed-URL expiry surfaces as an abort, not a retry loop, so the caller refreshes the URL with fresh credentials"
  - "Atomic download: stream to <dest>.partial, rename on success (T-06-04 mitigation)"
  - "Shipped asset via importlib.resources.files('<pkg>').joinpath('<asset>').read_text() — works across editable, wheel, and sdist installs"

requirements-completed: [ENV-06, ENV-07, ENV-08]

# Metrics
duration: 24min
completed: 2026-04-22
---

# Phase 1 Plan 06: Validation Harness + bounds_for_burst/bounds_for_mgrs_tile + run_eval.py Pilot Migration Summary

**Shared-plumbing harness with 6 public helpers, per-source RETRY_POLICY (P0.4 mitigation), opera_utils/burst DB bounds fallback, MGRS-tile seed asset, and run_eval.py pilot proving the ENV-07 diff shape.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-04-22T21:39:22Z
- **Completed:** 2026-04-22T22:03:24Z
- **Tasks:** 5 (RED + GREEN for Task 1; then Tasks 2, 3, 4)
- **Files modified:** 6 (3 created, 3 modified; plus .gitignore negation)
- **Test count:** 20 new tests in test_harness.py (all pass); 72 tests across harness+burst+Plan-04+Plan-05 suites regression-free

## Accomplishments

- `subsideo.validation.harness` ships 6 public helpers (`bounds_for_burst`, `bounds_for_mgrs_tile`, `credential_preflight`, `download_reference_with_retry`, `ensure_resume_safe`, `select_opera_frame_by_utc_hour`) + `RETRY_POLICY` dict + `ReferenceDownloadError` exception class.
- `RETRY_POLICY` has 4 source keys (CDSE, EARTHDATA, CLOUDFRONT, HTTPS) with `retry_on`/`abort_on` lists; CloudFront has the additional `refresh_url_on=[403]` key that surfaces signed-URL expiry as `ReferenceDownloadError` rather than an infinite retry loop (PITFALLS P0.4 mitigation).
- `bounds_for_burst` wraps `opera_utils.burst_frame_db.get_burst_id_geojson` (primary path verified against the pilot burst `t144_308029_iw1`: returns `(-119.48, 33.43, -118.52, 33.77)` pre-buffer) with `subsideo.burst.db.query_bounds` as the EU fallback.
- `bounds_for_mgrs_tile` wraps MGRS helpers from `opera_utils.burst_frame_db` (not present in 0.25.6; defensive try/except handles the `ImportError`) and falls back to the shipped `_mgrs_tiles.geojson` seed covering 10TFK, 29TNF, 33TXP at minimum — every tile referenced by v1.1 `run_eval_*.py` scripts.
- `query_bounds(burst_id)` added to `subsideo.burst.db`; re-parses `geometry_wkt` via `shapely.wkt.loads` and returns `.bounds` (the schema does not have separate west/south/east/north columns, so the helper derives them from the committed WKT).
- `run_eval.py` pilot migrated: `EXPECTED_WALL_S = 1800` module-level constant, `credential_preflight(["EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"])` replaces the ad-hoc auth check, and `bounds_for_burst(BURST_ID, buffer_deg=0.2)` replaces the hand-coded `[-119.7, 33.2, -118.3, 34.0]` literal. Net diff: +12/-1 lines.
- `validation/__init__.py` now re-exports 17 names alphabetically — 8 from harness appended to the 9 already provided by Plans 01-04 (3 names) and 01-05 (6 names). No Plan 04/05 entries were removed or reordered.

## Task Commits

Each task was committed atomically (6 commits total, plus one Rule 1 style fix):

1. **Task 1 RED: failing harness tests** — `2e7734b` (test)
2. **Task 1 GREEN: harness.py + _mgrs_tiles.geojson seed + gitignore negation** — `9c5fdd2` (feat; consolidates Task 2b per plan-notes rationale)
3. **Task 2: subsideo.burst.db.query_bounds EU fallback** — `97d4540` (feat)
4. **Task 3: run_eval.py pilot migration** — `d9a68e2` (feat)
5. **Task 4: validation/__init__.py harness re-exports** — `282a002` (feat)
6. **Rule 1 style fix: Sequence from collections.abc** — `9ff46ef` (style)

_Note: Task 1 followed TDD cycle (test → feat); Task 2b was folded into Task 1 GREEN because the mgrs-tile tests in the RED/GREEN cycle depend on the seed file._

## Files Created/Modified

- **`src/subsideo/validation/harness.py`** — NEW (540 lines, 461 non-blank). Six public helpers + per-source `RETRY_POLICY` dict + `ReferenceDownloadError`. No forbidden imports (no `subsideo.products.*`, no `tenacity`). All conda-forge-sensitive imports stay at module top (`requests`, `loguru.logger`, stdlib only).
- **`src/subsideo/validation/_mgrs_tiles.geojson`** — NEW (1.5 KB). FeatureCollection of 3 MGRS-100km tile Polygon footprints (10TFK, 29TNF, 33TXP) used by v1.1 eval scripts. Ships with wheel via hatchling's default-include behaviour.
- **`tests/unit/test_harness.py`** — NEW (277 lines, 20 tests). Covers: public API imports, `RETRY_POLICY` shape, `credential_preflight` success/failure/empty-string cases, `download_reference_with_retry` source-key enforcement + EARTHDATA 401 abort + CLOUDFRONT 403 abort, `ensure_resume_safe` missing/partial/complete, `select_opera_frame_by_utc_hour` unique/multiple/none/ISO-string inputs, `bounds_for_burst` unknown-raises + buffer-symmetric, `bounds_for_mgrs_tile` known-33TXP + unknown-raises + buffer-symmetric.
- **`src/subsideo/validation/__init__.py`** — MODIFIED (+18/-0). Appends 8 harness imports and 8 new `__all__` entries; Plan 04+05 entries preserved unchanged.
- **`src/subsideo/burst/db.py`** — MODIFIED (+58 lines). Adds `query_bounds(burst_id, cache_dir=None)` plus a `from shapely import wkt as _shapely_wkt` import. `get_burst_db_path` and `build_burst_db` untouched.
- **`run_eval.py`** — MODIFIED (+12/-1). `EXPECTED_WALL_S = 1800` at module level; 5-name harness import block; `credential_preflight` call after `load_dotenv()`; `bounds_for_burst(BURST_ID, buffer_deg=0.2)` replaces the hand-coded literal. Pipeline stages 1-5 (OPERA ref download, ASF SLC search, DEM+orbit, SAFE download, RTC run) untouched.
- **`.gitignore`** — MODIFIED (+3). Adds `!src/subsideo/validation/_mgrs_tiles.geojson` negation under the `*.geojson` top-level block so the packaged seed commits despite the generic rule.

## Decisions Made

- **Task 2b folded into Task 1 GREEN:** The mgrs-tile behaviour tests in Task 1 require `_mgrs_tiles.geojson` to be present. Rather than commit a GREEN state that leaves 3 tests failing, the seed landed alongside harness.py. Task 2b's acceptance criteria were verified post-commit (FeatureCollection shape, tile IDs {10TFK, 29TNF, 33TXP}, closed-ring polygons, non-zero bounds, importlib.resources-readable).
- **bounds_for_mgrs_tile primary path is exception-guarded:** opera-utils 0.25.6 has no MGRS helper (confirmed via `dir(opera_utils.burst_frame_db)` — only burst helpers present). The code still calls `from opera_utils.burst_frame_db import get_mgrs_tile_geojson` inside a try/except so future opera-utils versions that add MGRS helpers start exercising the primary path automatically.
- **query_bounds derives envelope from WKT, not stored columns:** The EU burst SQLite schema (`_CREATE_TABLE_SQL` in burst/db.py line 27) has `geometry_wkt TEXT NOT NULL` but no separate bounds columns. Rather than migrate the schema (out of scope for Plan 01-06 per plan), `query_bounds` parses the WKT via shapely and returns `.bounds`. This matches how `build_burst_db` originally stored the geometry.
- **.gitignore negation chosen over removing the broad rule:** The `*.geojson` block lives under "Geospatial Data" alongside `*.shp`, `*.tif` etc. — removing the rule would let unrelated experimental GeoJSON files accidentally commit. A single-path negation is narrower and explicit.
- **F401 warnings in run_eval.py accepted:** Plan Task 3 action explicitly instructs "still import all 5 so subsequent edits don't need new imports." Ruff reports 3 unused imports (download_reference_with_retry, ensure_resume_safe, select_opera_frame_by_utc_hour) as F401 — these are plan-mandated and will be exercised as run_eval.py grows in future phases.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Commit ordering: seed must land with Task 1 GREEN**

- **Found during:** Task 1 GREEN (right after writing harness.py)
- **Issue:** Running `pytest tests/unit/test_harness.py` after committing harness.py alone would leave `test_bounds_for_mgrs_tile_known_33txp` + `test_bounds_for_mgrs_tile_buffer_symmetric` failing (3 of 20 tests) because `_mgrs_tiles.geojson` did not yet exist. Task 2b was scheduled as a later commit but its artefact is a Task-1-test dependency.
- **Fix:** Created and committed `_mgrs_tiles.geojson` as part of the Task 1 GREEN commit (`9c5fdd2`). Task 2b acceptance criteria verified post-commit (FeatureCollection shape, tile IDs, closed-ring polygons, non-zero bounds). All 20 tests pass.
- **Files modified:** `src/subsideo/validation/_mgrs_tiles.geojson` (new)
- **Verification:** `pytest tests/unit/test_harness.py` — 20 passed. `python -c "import json; d=json.load(open('src/subsideo/validation/_mgrs_tiles.geojson')); assert {'10TFK','29TNF','33TXP'} <= {f['properties']['tile_id'] for f in d['features']}"` — OK.
- **Committed in:** `9c5fdd2` (folded into Task 1 GREEN)

**2. [Rule 3 - Blocking] .gitignore *.geojson blocked the seed commit**

- **Found during:** Task 1 GREEN, staging the seed file
- **Issue:** `.gitignore:233` has a broad `*.geojson` rule under the "Geospatial Data" block. `git add src/subsideo/validation/_mgrs_tiles.geojson` failed with the hint that the file is gitignored.
- **Fix:** Added a single-path negation (`!src/subsideo/validation/_mgrs_tiles.geojson`) immediately after the `*.geojson` rule. The negation is narrow (affects only this packaged asset); the broad rule still ignores ad-hoc GeoJSON scratch files elsewhere in the repo.
- **Files modified:** `.gitignore` (3-line insertion)
- **Verification:** `git check-ignore -v src/subsideo/validation/_mgrs_tiles.geojson` now reports `.gitignore:236:!src/subsideo/validation/_mgrs_tiles.geojson` (negation rule wins); `git add` succeeds; wheel would include the asset via hatchling's `packages = ["src/subsideo"]` directive.
- **Committed in:** `9c5fdd2` (folded into Task 1 GREEN)

**3. [Rule 1 - Bug / style] Ruff UP035: Sequence should come from collections.abc**

- **Found during:** Final ruff sweep (post-Task 4)
- **Issue:** `from typing import Sequence` in harness.py triggered ruff `UP035` (typing.Sequence deprecated since 3.9). The adjacent Plan 01-05 module `validation/results.py` already uses `from collections.abc import Callable`, so the project convention is set.
- **Fix:** Split the import — `from collections.abc import Sequence` (alongside `Callable` convention) and `from typing import Any, Literal` stays for remaining typing-specific names.
- **Files modified:** `src/subsideo/validation/harness.py` (2-line import shuffle)
- **Verification:** `ruff check src/subsideo/validation/harness.py` — `All checks passed!`. `pytest tests/unit/test_harness.py` — still 20/20 green.
- **Committed in:** `9ff46ef`

---

**Total deviations:** 3 auto-fixed (2× Rule 3 blocking, 1× Rule 1 style).
**Impact on plan:** All three were necessary for a working commit stream. The commit-ordering fix avoided a broken intermediate state; the .gitignore negation was the minimum-scope unblock for a packaged asset; the ruff fix matched Phase 1 convention (already used in Plan 01-05's results.py). No scope creep — every deviation is directly required to make a plan-specified artefact work.

## Issues Encountered

- **Worktree base incorrect on startup.** The `<worktree_branch_check>` step detected the base was `eff433b` (pre-Plan-01-05) rather than the expected `92432ad` (post-Plan-01-05). Hard-reset to `92432ad` completed successfully before any other action. This was the standard worktree protocol, not a new issue — recorded for audit traceability.
- **Editable install points at main repo, not this worktree.** `pip install -e .` in the subsideo env was run against the main worktree path. All test runs require `PYTHONPATH="$(pwd)/src:$PYTHONPATH"` prefix to exercise worktree code. No changes needed to the package or env — this is expected behaviour for parallel worktrees; the parent orchestrator's merge step will reconcile once the worktree lands.
- **opera-utils 0.25.6 has no MGRS helpers.** Confirmed via `dir(opera_utils.burst_frame_db)` — only burst helpers are exposed. The `bounds_for_mgrs_tile` primary path is present defensively (for future opera-utils upgrades) but the seed fallback is the active path today. No action required.

## User Setup Required

None — no external service configuration required by this plan.

## Next Phase Readiness

- **Plan 01-07 (Wave 3 — batch-migrate remaining 6 run_eval_*.py scripts) unblocked.** harness.py exposes all 6 helpers + RETRY_POLICY + ReferenceDownloadError that the batch migration will consume. The 3 MGRS-tile seed entries cover every v1.1 script (`run_eval_dist.py` → 10TFK, `run_eval_dist_eu*.py` → 29TNF, `run_eval_dswx.py` → 33TXP).
- **Plan 01-08 (matrix_writer) unaffected** — matrix_writer consumes CRITERIA from Plan 01-05 (already merged) and does not depend on harness.
- **run_eval.py pilot proves the ENV-07 diff shape.** Plan 01-07's acceptance check — "diff between equivalent scripts contains only reference-data differences" — can reference the 12-line diff here as the baseline: scripts post-migration differ only in BURST_ID, SENSING_DATE, EPSG, OUT, and ASF/CDSE reference-data specifics.
- **No blockers.**

## Self-Check: PASSED

Verification of claimed artefacts:

| Artefact                                                | Status    | Evidence                                                                                       |
| ------------------------------------------------------- | --------- | ---------------------------------------------------------------------------------------------- |
| `src/subsideo/validation/harness.py`                    | FOUND     | 540 lines, 461 non-blank; all 6 helpers + RETRY_POLICY + ReferenceDownloadError importable     |
| `src/subsideo/validation/_mgrs_tiles.geojson`           | FOUND     | 1.5 KB; 3 features with tile_ids {10TFK, 29TNF, 33TXP}                                         |
| `src/subsideo/burst/db.py::query_bounds`                | FOUND     | `from subsideo.burst.db import query_bounds` succeeds                                          |
| `src/subsideo/validation/__init__.py` harness re-exports| FOUND     | 8 new names + 9 preserved; `__all__` has 17 entries                                            |
| `run_eval.py` migration                                 | FOUND     | EXPECTED_WALL_S=1800, bounds_for_burst ref x2, credential_preflight ref x2, hand-coded bounds=[] x0 |
| `tests/unit/test_harness.py`                            | FOUND     | 20 tests, all pass                                                                             |
| Commit `2e7734b` (Task 1 RED)                           | FOUND     | `test(01-06): add failing tests for validation harness module`                                 |
| Commit `9c5fdd2` (Task 1 GREEN + Task 2b seed + .gitignore) | FOUND | `feat(01-06): add validation harness with 6 public helpers + RETRY_POLICY`                     |
| Commit `97d4540` (Task 2 query_bounds)                  | FOUND     | `feat(01-06): add subsideo.burst.db.query_bounds EU-burst fallback`                            |
| Commit `d9a68e2` (Task 3 run_eval migration)            | FOUND     | `feat(01-06): migrate run_eval.py to consume validation harness`                               |
| Commit `282a002` (Task 4 __init__.py re-exports)        | FOUND     | `feat(01-06): re-export harness public names from validation package`                          |
| Commit `9ff46ef` (Rule 1 ruff fix)                      | FOUND     | `style(01-06): import Sequence from collections.abc in harness`                                |

All files exist, all commits present, all tests pass, all acceptance criteria verified. No shared-file violations (STATE.md and ROADMAP.md untouched as required by worktree mode).

---
*Phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding*
*Plan: 06*
*Completed: 2026-04-22*
