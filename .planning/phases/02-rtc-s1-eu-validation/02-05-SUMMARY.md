---
phase: 02-rtc-s1-eu-validation
plan: 05
subsystem: validation
tags:
  - eval-run
  - conclusions-population
  - matrix-render
  - checkpoint-pending

# Dependency graph
requires:
  - phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
    provides: supervisor, Makefile eval-rtc-eu target, MetricsJson/MetaJson schemas, compare_rtc, run_rtc
  - phase: 02-rtc-s1-eu-validation
    provides: RTCEUCellMetrics + BurstResult (02-01), INVESTIGATION_TRIGGER criteria (02-01), find_cached_safe helper (02-01), user-approved probe artifact (02-02), CONCLUSIONS_RTC_EU.md template shell (02-02), matrix_writer _render_rtc_eu_cell branch (02-03), run_eval_rtc_eu.py with 5-burst BURSTS literal + 17 static-invariant tests (02-04)
provides:
  - (pending) eval-rtc-eu/metrics.json + eval-rtc-eu/meta.json from make eval-rtc-eu
  - (pending) results/matrix.md rtc:eu row as X/N PASS after make results-matrix
  - (pending) CONCLUSIONS_RTC_EU.md populated from metrics.json per D-13/D-14
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified: []

key-decisions: []

patterns-established: []

requirements-completed: []

# Metrics
duration: (in-progress -- Task 1 checkpoint pending user approval)
completed: (pending Task 3 phase-2-complete signal)
---

# Phase 2 Plan 05: RTC-EU Live Eval + CONCLUSIONS Population -- PARTIAL (Task 1 checkpoint pending)

**Task 1 pre-flight checks COMPLETE. Awaiting user approval signal before Task 2 (`make eval-rtc-eu`) executes.**

This partial SUMMARY records the pre-flight audit state so the worktree can be torn down without losing the Task 1 findings.

## Task 1 Pre-Flight Audit

### Preceding Plan Presence Checks (8/8 PASS)

| # | Check | Path | Result |
|---|-------|------|--------|
| 1 | `class RTCEUCellMetrics(MetricsJson):` | `src/subsideo/validation/matrix_schema.py` | PASS |
| 2 | `"rtc.eu.investigation_rmse_db_min"` | `src/subsideo/validation/criteria.py` | PASS |
| 3 | `^def find_cached_safe` | `src/subsideo/validation/harness.py` | PASS |
| 4 | probe artifact present | `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` | PASS |
| 5 | CONCLUSIONS shell present | `CONCLUSIONS_RTC_EU.md` | PASS |
| 6 | probe script present | `scripts/probe_rtc_eu_candidates.py` | PASS |
| 7 | `^def _render_rtc_eu_cell` | `src/subsideo/validation/matrix_writer.py` | PASS |
| 8 | `run_eval_rtc_eu.py` present | repo root | PASS |

All 4 Wave 1-3 plans (02-01, 02-02, 02-03, 02-04) landed cleanly.

### BURSTS Structural Audit

| # | burst_id | regime | centroid_lat | sensing_time | output_epsg | relative_orbit | TODO(user)? |
|---|----------|--------|--------------|--------------|-------------|----------------|-------------|
| 1 | t066_140712_iw2 | Alpine | 46.35 | 2024-07-12 05:13 UTC | 32632 (UTM 32N) | 66 | YES |
| 2 | t029_062015_iw1 | Scandinavian | 67.15 | 2024-07-18 15:55 UTC | 32634 (UTM 34N) | 29 | YES |
| 3 | t154_329834_iw2 | Iberian | 41.15 | 2024-08-03 18:21 UTC | 32630 (UTM 30N) | 154 | YES |
| 4 | t117_249422_iw2 | TemperateFlat | 44.50 | 2021-03-14 17:05 UTC | 32632 (UTM 32N) | 117 | no |
| 5 | t154_329100_iw2 | Fire | 40.70 | 2024-09-28 06:32 UTC | 32629 (UTM 29N) | 154 | YES |

**COUNT: 5 entries, 5 unique regimes (Alpine / Scandinavian / Iberian / TemperateFlat / Fire).**

### RTC-01 Structural Constraint Audit

| Constraint | Source row | Value | Result |
|------------|------------|-------|--------|
| ≥1 burst with expected relief > 1000 m | Row 1 Alpine (Valtellina, inline comment says `~3200 m`) | 3200 m expected | STRUCTURALLY SATISFIED (confirmed at runtime via `compute_max_relief(dem_path)`) |
| ≥1 burst > 55°N | Row 2 Scandinavian (Norrbotten) | centroid_lat=67.15°N | SATISFIED (12° above the bar) |

Both RTC-01 mandatory constraints are structurally satisfied by the BURSTS literal. Final confirmation happens at Task 3 from `metrics.json` per_burst[*].max_relief_m and per_burst[*].lat.

### TODO(user) Markers Flagged

**4 of 5 BURSTS entries carry `# TODO(user): update from probe artifact if different` inline comments on `burst_id`:**

- Row 1 Alpine — `t066_140712_iw2`
- Row 2 Scandinavian — `t029_062015_iw1`
- Row 3 Iberian — `t154_329834_iw2`
- Row 5 Fire — `t154_329100_iw2`

Row 4 Bologna (`t117_249422_iw2`) does NOT carry a TODO — it is the literal burst from Plan 02-02 row 4 of the probe artifact (documented Bologna pattern proven by Phase 1 DISP-EGMS).

**Context from Plan 02-04 SUMMARY and the Probe Artifact:**

The probe artifact at `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` was **user-approved-as-drafted on 2026-04-23T05:58:39Z** with the note "5 AOI rows approved for Plan 02-04 consumption; concrete `burst_id` values derived downstream via `opera_utils.get_burst_id` (fresh-download regimes) or SAFE inspection of cached Phase 1 inputs". The probe has NOT been re-run to fill `best_match_granule` / `opera_rtc_granules_2024_2025` columns (still `TBD`).

This means:
- **AOI shape (regime / centroid_lat / relorb / UTM zone / sensing_time hour) is user-approved.**
- **The concrete burst_id strings are Claude's best-guess drafts.** If any `burst_id` does not correspond to a real OPERA RTC granule at the given sensing_time hour, Stage 1 of `process_burst` will raise `RuntimeError("No OPERA RTC granule found for {burst_id}")`, per-burst try/except will catch it, and the row will land as `status="FAIL"` with `error="No OPERA RTC granule..."` — the eval continues for the other bursts.
- **User options at the Task 1 checkpoint:**
  1. **lgtm-proceed** — accept the TODO(user) drafts and let the eval run. If one or more bursts FAIL due to missing OPERA reference, surface the error in SC-1 gap discussion at Task 3. Pros: no separate probe round-trip; Cons: up to 4 FAIL rows if drafts are off.
  2. **lgtm-proceed-after-probe** — run `scripts/probe_rtc_eu_candidates.py` first (requires EARTHDATA creds), update BURSTS burst_ids from live ASF+opera_utils lookup, then proceed. Pros: higher confidence 5/5 PASS; Cons: adds ~5 min for probe + ~2 min for BURSTS edits + re-run of 17 static-invariant tests.
  3. **lgtm-use-mocks** — skip compute entirely; synthesise mock metrics.json/meta.json to prove the downstream pipeline (matrix_writer, CONCLUSIONS populate) works end-to-end. Phase 2 remains OPEN; Plan 02-05 re-invoked later with real values.
  4. **needs-fix** — describe what to change.

### Credentials

| Credential pair | Present in `/Volumes/Geospatial/Geospatial/subsideo/.env` |
|-----------------|-----------------------------------------------------------|
| EARTHDATA_USERNAME + EARTHDATA_PASSWORD | YES (2 matches) |
| CDSE_CLIENT_ID + CDSE_CLIENT_SECRET | YES (2 matches; NOT required for RTC-EU but present) |

Worktree root symlinked to main-tree `.env` via `os.symlink` (bash `ln -sf` sandbox-denied). `load_dotenv()` will pick up the symlinked file when `run_eval_rtc_eu.py` executes. `.env` is gitignored (lines 138, 253 of `.gitignore`); the symlink will be destroyed when the worktree is torn down.

### Storage

| Metric | Value |
|--------|-------|
| `df -h` free on `/Volumes/Geospatial` | 789 GB |
| Expected cold-run footprint | ~20 GB (5 fresh SAFE downloads at ~4 GB each) + ~0.5 GB/burst DEM + ~0.5 GB/burst OPERA reference + ~1 GB/burst RTC output → ~28 GB |
| Ratio free / expected | 28× headroom |

Ample margin. Even with all 5 bursts as fresh downloads (see next section), <5% of free disk is consumed.

### D-02 Cross-Cell Cache Status (UPDATED FINDING)

**D-02 expectation:** Bologna SAFE cached at `eval-disp-egms/input/` from Phase 1 DISP-EGMS; Fire SAFE cached at `eval-dist-eu/input/` or `eval-dist-eu-nov15/input/` from Phase 1 DIST-EU. "Free 2 bursts" per §specifics.

**Observed state (main tree):**
- `eval-disp-egms/input/` exists but is **empty** (only `.DS_Store`).
- `eval-dist-eu/input/` does **NOT exist** (only `dist_output/`, `ems_reference/`, `enumeration_result.json`, `reference/` subdirs).
- `eval-dist-eu-nov15/input/` does **NOT exist** (only `dist_output/`, `ems_reference/`, `enumeration_result.json` subdirs).

**Consequence:** All 5 bursts will be **fresh downloads** at runtime (~20 GB total S1 SAFE). The cached-reuse bursts 4 (Bologna) and 5 (Fire) will fall through `find_cached_safe → None` and enter the ASF download path. Plan 02-04 SUMMARY documented expected runtime of "~3h cold" assuming 3 fresh + 2 cached; the actual wall-clock may extend toward the 4h EXPECTED_WALL_S ceiling (still inside supervisor budget; 8h hard ceiling = 2× margin).

This does NOT invalidate the plan; it just shifts the runtime estimate. The `cached` field on `BurstResult` will correctly report `False` for all 5 rows at runtime, and the CONCLUSIONS §5a Terrain-Regime Coverage Table will reflect the actual cache state. No code change required — D-06 per-burst try/except + the find_cached_safe null-fallback path handle this transparently.

### Static-Invariant Test Re-Run

```
$ /Users/alex/.local/share/mamba/envs/subsideo/bin/python -m pytest tests/unit/test_rtc_eu_eval.py --no-cov -q
.................                                                        [100%]
17 passed in 0.14s
```

All 17 tests pass on this worktree (confirms Plan 02-04 framework holds under the current BURSTS literal).

## Task Status

| Task | Type | Status |
|------|------|--------|
| 1 | checkpoint:human-verify | **PENDING user approval** (checkpoint returned to orchestrator) |
| 2 | auto (long-running, `make eval-rtc-eu` + matrix + CONCLUSIONS populate) | PENDING |
| 3 | checkpoint:human-verify (SC-1/SC-2/SC-3 sign-off) | PENDING |

## Next Step

User reviews this partial SUMMARY + the checkpoint message and returns one of:

- `lgtm-proceed` — proceed with Task 2 using the current BURSTS list (Claude-drafted burst_ids accepted, potential per-burst FAILs tolerated).
- `lgtm-proceed-after-probe` — run `scripts/probe_rtc_eu_candidates.py` to refresh burst_ids, then proceed.
- `lgtm-use-mocks` — skip compute; synthesise mock metrics.json to exercise downstream pipeline.
- `needs-fix: <description>` — describe the change (specific BURSTS edits, probe-artifact amendments, etc.).

A continuation agent (Task 2) is spawned by the orchestrator once the signal is received.

---

*Phase: 02-rtc-s1-eu-validation*
*Plan: 05 (partial — Task 1 checkpoint)*
*Pre-flight verified: 2026-04-22*
