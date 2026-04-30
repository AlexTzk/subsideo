---
phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
plan: 07
subsystem: infra
tags: [supervisor, watchdog, py-spy, make, subprocess, os.killpg, ast, env07, env08, env09, harness-batch-migration]

requires:
  - phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
    provides: "_mp.configure_multiprocessing (Plan 01-03); validation/harness.py + bounds_for_burst + bounds_for_mgrs_tile + credential_preflight + pilot run_eval.py migration (Plan 01-06)"
provides:
  - "Subprocess supervisor in subsideo.validation.supervisor (os.killpg process-group kill + mtime staleness watchdog + py-spy dump + exit 124)"
  - "Repo-root Makefile with 10 matrix cells (5 products x 2 regions), eval-all / eval-nam / eval-eu aggregators, results-matrix hook, FORCE-guarded clean-cache"
  - "7 batch-migrated eval scripts consuming validation harness (every script declares EXPECTED_WALL_S; zero hand-coded bounds literals; zero ad-hoc credential checks)"
  - "scripts/env07_diff_check.py — machine-verifiable ENV-07 diff classifier"
  - "tests/unit/test_supervisor.py (17 tests covering AST parse, mtime, cache-dir convention, module constants, subprocess happy-path)"
affects: [01-08, phase-02, phase-03, phase-04, phase-05, phase-06]

tech-stack:
  added: [py-spy (conda-forge), GNU Make orchestration]
  patterns:
    - "Supervisor AST-parses module-level EXPECTED_WALL_S literals only (no arbitrary expression eval)"
    - "Makefile recipes delegate to subsideo.validation.supervisor for per-cell subprocess isolation"
    - "Eval-script plumbing lives in validation/harness.py; scripts diff only on reference-data constants (ENV-07)"
    - "MGRS-tile bounds via harness.bounds_for_mgrs_tile + shipped _mgrs_tiles.geojson seed"

key-files:
  created:
    - "src/subsideo/validation/supervisor.py"
    - "Makefile"
    - "scripts/env07_diff_check.py"
    - "tests/unit/test_supervisor.py"
  modified:
    - "run_eval_cslc.py"
    - "run_eval_disp.py"
    - "run_eval_disp_egms.py"
    - "run_eval_dist.py"
    - "run_eval_dist_eu.py"
    - "run_eval_dist_eu_nov15.py"
    - "run_eval_dswx.py"

key-decisions:
  - "EXPECTED_WALL_S AST parser accepts literals + whitelisted BinOps (+, -, *, //) only; rejects Name/Call/Attribute/Subscript and other ops — T-07-06 mitigation"
  - "bounds_for_burst returned tuples are substituted for BURST_BBOX (unbuffered) so existing list(BURST_BBOX) / WKT / STAC call sites continue to work unchanged"
  - "run_eval_dist*.py scripts import bounds_for_mgrs_tile but do NOT call it — dist_s1 auto-derives bounds from mgrs_tile_id; the import is kept for phase-agnostic future use"
  - "clean-cache Makefile target refuses without FORCE=1 (T-07-02 mitigation); plain invocation exits 2 with refusal message"

patterns-established:
  - "Supervisor boundary: `python -m subsideo.validation.supervisor <script>` owns the process group; eval scripts never run directly from Makefile"
  - "Batch-migration commit pattern: entire migration set lands atomically so ENV-07 classifier has a single diff target"
  - "env07_diff_check.py: reference-data patterns + plumbing-violation patterns as explicit regex sets with violation message text"

requirements-completed: [ENV-05, ENV-07, ENV-08, ENV-09]

duration: ~25min
completed: 2026-04-22
---

# Phase 1 Plan 7: Watchdog + Makefile + Batch Migration Summary

**Subprocess watchdog with os.killpg + mtime-staleness + py-spy dump + exit 124, 10-cell Makefile with per-cell isolation, and batch migration of 7 eval scripts onto the harness with machine-verifiable ENV-07 diff gating.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-04-22T15:10:06Z
- **Completed:** 2026-04-22T15:34Z (approx.)
- **Tasks:** 3 (Task 1 TDD RED+GREEN, Task 2, Task 3)
- **Files created:** 4 (supervisor.py, Makefile, env07_diff_check.py, test_supervisor.py)
- **Files modified:** 7 (all remaining eval scripts)

## Accomplishments

- **Subprocess watchdog (ENV-05):** `src/subsideo/validation/supervisor.py` implements the D-10..D-13 contract. Forks the target script via `subprocess.Popen(start_new_session=True)` so the child owns a fresh process group (T-07-01: isce3/dist-s1 grandchildren are killed alongside the Python parent). Polls every 30s; aborts when `wall > 2*EXPECTED_WALL_S` AND cache-dir rglob mtime hasn't advanced for 120s. Before kill: best-effort `py-spy dump --pid <child> > <cache>/watchdog-stacks.txt` (FileNotFoundError / subprocess failure both logged as warnings, never raised). Then `os.killpg(pgid, SIGTERM)` → 30s grace → `os.killpg(pgid, SIGKILL)`. Returns `TIMEOUT_EXIT_CODE = 124` (conventional timeout(1) exit code so Makefile can distinguish watchdog abort from other failures).
- **Safety-bounded AST parser (T-07-06 mitigation):** `_parse_expected_wall_s` accepts only `ast.Constant` (int/float, excluding bool) and `ast.BinOp` whose operator is in the whitelist `{Add, Sub, Mult, FloorDiv}` and whose operands recursively reduce to constants. Rejects Name / Call / Attribute / Subscript / disallowed operators (incl. `**`, `/`, bit-shifts) with a `ValueError` citing the expected forms. No arbitrary-code eval path.
- **Makefile orchestration (ENV-09):** Repo-root Makefile with 10 matrix cells (`eval-{rtc,cslc,disp,dist,dswx}-{nam,eu}`), three aggregators (`eval-nam`, `eval-eu`, `eval-all`), a `results-matrix` hook (consumes Plan 01-08's matrix_writer), and a `clean-cache` target that refuses without `FORCE=1`. Every cell delegates to `$(SUPERVISOR) <script>` = `micromamba run -n subsideo python -m subsideo.validation.supervisor <script>` — per-cell subprocess isolation means one hang/failure does not stage the matrix (use `make -k eval-all` to continue past failures).
- **Batch harness migration (ENV-06/07/08):** All 7 remaining eval scripts now (a) declare `EXPECTED_WALL_S` module-level literal, (b) import the six harness public helpers in a grouped block, (c) call `credential_preflight([...])` with concrete env-var lists at the top of `__main__`, (d) replace every hand-coded numeric bounds literal with `bounds_for_burst` / `bounds_for_mgrs_tile`. `run_eval_dswx.py` uses MGRS tile `33TXP` (Lake Balaton) via the harness seed GeoJSON — ENV-08 migration for MGRS scripts completed in Phase 1, no Phase 6 deferral.
- **ENV-07 machine-verifiable acceptance:** `scripts/env07_diff_check.py` reads a unified diff of two eval scripts and exits 0 iff every `+`/`-` hunk matches a reference-data pattern and contains no plumbing-class violation (`bounds=[-N, ...]`, `for key in (...)`, `if not os.environ.get(...)`). Both acceptance invocations exit 0:
  - `env07_diff_check run_eval_disp.py run_eval_disp_egms.py` → OK
  - `env07_diff_check run_eval_dist.py run_eval_dist_eu.py` → OK

## Task Commits

1. **Task 1 RED (failing tests):** `dac2507` — `test(01-07): add failing tests for validation supervisor` (tests/unit/test_supervisor.py, 17 tests)
2. **Task 1 GREEN (implementation):** `9091518` — `feat(01-07): add subprocess supervisor with mtime watchdog (D-10..D-13)` (src/subsideo/validation/supervisor.py, 309 insertions)
3. **Task 2:** `83f019b` — `feat(01-07): add Makefile with 10-cell eval orchestration (ENV-09)` (Makefile, 62 insertions)
4. **Task 3:** `9b58921` — `refactor(01-07): batch-migrate 7 eval scripts to validation harness` (7 eval scripts + scripts/env07_diff_check.py, 303 insertions/28 deletions)

## Files Created/Modified

**Created:**
- `src/subsideo/validation/supervisor.py` — subprocess watchdog with mtime staleness heuristic (253 non-blank lines; 17/17 unit tests pass)
- `Makefile` — 10-cell matrix orchestration delegating to supervisor (53 non-blank lines; GNU make parses all 15 targets; 12 TAB-indented recipe lines)
- `scripts/env07_diff_check.py` — machine-verifiable ENV-07 diff classifier (151 non-blank lines; categorised violation report on exit 1)
- `tests/unit/test_supervisor.py` — 17 unit tests (AST parse: literals / BinOps / rejected shapes; mtime: empty / with-files / missing; cache-dir convention for pilot and suffixed scripts; module constants; subprocess happy-path integration)

**Modified (all 7 remaining eval scripts migrated):**
- `run_eval_cslc.py` — EXPECTED_WALL_S=2700; credential_preflight(EARTHDATA_*); imports 6 harness helpers
- `run_eval_disp.py` — EXPECTED_WALL_S=5400; credential_preflight(CDSE_* + EARTHDATA_*); BURST_BBOX = bounds_for_burst(buffer_deg=0.0); DEM fetch uses bounds_for_burst(buffer_deg=0.2)
- `run_eval_disp_egms.py` — EXPECTED_WALL_S=5400; credential_preflight(CDSE_* + EARTHDATA_* + EGMS_TOKEN); same bounds_for_burst substitution pattern as run_eval_disp.py
- `run_eval_dist.py` — EXPECTED_WALL_S=1800; credential_preflight(EARTHDATA_*); bounds_for_mgrs_tile imported but not called (dist_s1 auto-derives from mgrs_tile_id); ENV-08 documentation comment added above MGRS_TILE
- `run_eval_dist_eu.py` — EXPECTED_WALL_S=1800; credential_preflight(CDSE_* + EARTHDATA_*); same mgrs_tile auto-derive pattern
- `run_eval_dist_eu_nov15.py` — EXPECTED_WALL_S=1800; same pattern as dist_eu
- `run_eval_dswx.py` — EXPECTED_WALL_S=900; credential_preflight(CDSE_* + CDSE_S3_*); AOI_BBOX = bounds_for_mgrs_tile("33TXP", buffer_deg=0.1)

## Decisions Made

- **AST parser whitelist:** Accept `int/float` constants and `BinOp(Add|Sub|Mult|FloorDiv)` of constants (nested). This matches the plan's explicit relaxation (`30 * 60` is idiomatic and more readable than `1800`) while maintaining the no-arbitrary-eval invariant. Any Name / Call / Attribute / Subscript / disallowed operator raises `ValueError` before the subprocess is launched.
- **`BURST_BBOX` substitution pattern:** Replaced the hand-coded `BURST_BBOX = (w, s, e, n)` tuple with `BURST_BBOX = bounds_for_burst(BURST_ID, buffer_deg=0.0)` rather than renaming every call site. Downstream code (`list(BURST_BBOX)`, unpacking `w, s, e, n = BURST_BBOX`, WKT construction) works identically because `bounds_for_burst` returns a 4-tuple. DEM fetches use a separate `bounds_for_burst(BURST_ID, buffer_deg=0.2)` call at the fetch site for the wider buffer.
- **dist scripts import-only `bounds_for_mgrs_tile`:** `dist_s1.run_dist_s1_workflow` auto-derives its bounds internally from `mgrs_tile_id`, so the scripts never actually pass a `bounds=...` kwarg. The import is retained per the plan's explicit requirement (future phase-agnostic use) and an ENV-08 comment documents why no call site exists.
- **Makefile target naming for placeholder scripts:** `eval-rtc-eu`, `eval-cslc-eu`, and `eval-dswx-nam` reference scripts that don't yet exist (Phase 2 / 3 / 6 deliverables). The targets are declared now so `eval-all` enumerates the full 10-cell matrix from Phase 1 onward; missing scripts fail loudly under per-cell isolation (Plan 01-08 matrix_writer will mark these as `RUN_FAILED`).
- **clean-cache safety guard:** Requires `FORCE=1`. Plain `make clean-cache` exits 2 with a refusal message (T-07-02 mitigation). This matches Open Question 4's recommended posture — accidental wipes of `eval-*/` caches destroy 12h+ of eval runtime.

## Deviations from Plan

**Minor deviation (not auto-fixed; explicit scope choice documented here):**

The plan's Task 3 action text lists hand-coded numeric-bounds call sites that must be replaced. `run_eval_disp.py` and `run_eval_disp_egms.py` both use `BURST_BBOX` for three purposes: (1) STAC/WKT search polygon, (2) `roi.bbox` for EGMStoolkit, (3) DEM fetch. The plan's action directs replacing only the DEM fetch site. I took the stronger approach: replace the `BURST_BBOX` assignment itself with `bounds_for_burst(BURST_ID, buffer_deg=0.0)` so all three downstream uses flow from the harness without hand-coded numeric literals. The ENV-08 acceptance check (`rg 'bounds=\[-?[0-9]'`) returns zero hits across all 8 eval scripts.

Otherwise: plan executed exactly as written. No Rule 1/2/3 auto-fixes were required (no bugs, no missing critical functionality, no blocking issues). No Rule 4 (architectural) checkpoints were hit.

---

**Total deviations:** 0 auto-fixes; 1 scope enhancement (tighter `BURST_BBOX` substitution than the plan's minimum).
**Impact on plan:** Improves ENV-08 coverage; passes the same acceptance gates as the plan's minimum.

## Issues Encountered

- **Parent-repo vs worktree pip-install:** The `subsideo` package is pip-installed from `/Volumes/Geospatial/Geospatial/subsideo/` (parent repo), not from the worktree at `.claude/worktrees/agent-a18b8fbc/`. To verify tests pass against the new `supervisor.py` that lives in the worktree, I staged a copy to the parent repo's `src/subsideo/validation/supervisor.py` for the duration of the verification (copy + test + delete). The worktree commit is authoritative — the staging copy was removed before commit. This is a standard worktree complication, not a plan defect.
- **No other issues** — harness.py API (Plan 01-06 frozen) accepted all 7 migration patterns without modification; the seed GeoJSON already ships 33TXP for Lake Balaton; py-spy is present in the subsideo env (rebuilt 2026-04-22).

## Verification Log

All plan acceptance criteria were verified end-to-end:

| Check | Expected | Actual |
|-------|----------|--------|
| Supervisor tests | 17 pass | 17 passed |
| Supervisor --help | argparse usage | usage printed |
| `make -n eval-rtc-nam` | supervisor invocation | `micromamba run -n subsideo python -m subsideo.validation.supervisor run_eval.py` |
| `make clean-cache` (no FORCE) | exit 2 + refusal | exit 2, refusal message printed |
| All 15 Makefile targets | parse | 15/15 parse OK |
| EXPECTED_WALL_S count | 8 | 8 |
| `credential_preflight(` count | >= 7 | 8 |
| `bounds_for_(burst\|mgrs_tile)(` call count | >= 5 | 6 |
| hand-coded bounds literals | 0 | 0 |
| ad-hoc `if not os.environ.get` | 0 | 0 |
| env07 disp/disp_egms | exit 0 | exit 0 |
| env07 dist/dist_eu | exit 0 | exit 0 |
| supervisor.py non-blank LOC | >=150 | 253 |
| Makefile non-blank LOC | >=15 | 53 |
| env07_diff_check.py non-blank LOC | >=50 | 151 |
| MGRS 33TXP covers Lake Balaton | True | True (seed fallback; opera_utils MGRS helpers absent in 0.25.6) |
| All 8 eval scripts parse as Python | 8/8 | 8/8 |

## Self-Check: PASSED

All created files exist:
- `src/subsideo/validation/supervisor.py` — FOUND
- `Makefile` — FOUND
- `scripts/env07_diff_check.py` — FOUND
- `tests/unit/test_supervisor.py` — FOUND

All commits exist in git log:
- `dac2507` — FOUND
- `9091518` — FOUND
- `83f019b` — FOUND
- `9b58921` — FOUND

## Next Phase Readiness

- **Plan 01-08 (matrix_writer)** can consume the `make results-matrix` target end-to-end. The target invokes `subsideo.validation.matrix_writer --out results/matrix.md`, which is Plan 01-08's primary deliverable.
- **Phase 2 (RTC EU)** and **Phase 3 (CSLC EU)** can add their new eval scripts (`run_eval_rtc_eu.py`, `run_eval_cslc_eu.py`) by copying the migrated N.Am. patterns — the harness API and the supervisor contract are frozen.
- **Phase 6 (DSWx N.Am.)** can add `run_eval_dswx_nam.py` the same way; `bounds_for_mgrs_tile` covers both regions via the shared seed GeoJSON.
- No blockers for downstream phases.

---
*Phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding*
*Completed: 2026-04-22*
