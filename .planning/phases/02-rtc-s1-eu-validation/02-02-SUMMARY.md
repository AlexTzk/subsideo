---
phase: 02-rtc-s1-eu-validation
plan: 02
subsystem: validation / research-artifact
tags:
  - research-artifact
  - burst-selection
  - conclusions-template
  - checkpoint-resolved
dependency_graph:
  requires:
    - Phase 1 harness (bounds_for_burst, select_opera_frame_by_utc_hour, credential_preflight)
    - Phase 1 matrix_schema / criteria / results split (v1.1 big-bang migration)
    - CONCLUSIONS_RTC_N_AM.md canonical v1.0 template
    - PITFALLS P1.1 terrain-regime coverage schema
  provides:
    - Committed probe script (scripts/probe_rtc_eu_candidates.py)
    - Committed probe artifact (.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md)
    - Committed CONCLUSIONS_RTC_EU.md template shell
    - 5-regime Claude-drafted burst candidate list, user-approved as-drafted (D-04 resolved 2026-04-23)
  affects:
    - Plan 02-04 (run_eval_rtc_eu.py) consumes the probe artifact's BURSTS list
    - Plan 02-05 populates CONCLUSIONS_RTC_EU.md placeholders post-eval
tech-stack:
  added: []
  patterns:
    - Probe script uses asf_search + earthaccess (mirrors run_eval_disp.py:179-193 WKT polygon + ASF search pattern)
    - Probe artifact is a committed markdown table -- git-auditable burst selection
    - CONCLUSIONS template mirrors the v1.0 §1-8 skeleton + adds §5a coverage / §5b investigation
    - Uniform "(... burst -- populated from metrics.json post-run)" placeholder across all 5 §2.1 rows (checker WARNING fix, no template-level burst_id)
    - Python 3.12+ safe datetime: tz-aware datetime.now(timezone.utc), no deprecated utcnow()
key-files:
  created:
    - scripts/probe_rtc_eu_candidates.py
    - .planning/milestones/v1.1-research/rtc_eu_burst_candidates.md
    - CONCLUSIONS_RTC_EU.md
  modified: []
decisions:
  - "Claude drafted five regime AOI bboxes (Alpine Valtellina / Scandinavian Norrbotten / Iberian Meseta / Bologna Po plain / Portugal Aveiro-Viseu) per D-04; user approved as-drafted at 2026-04-23T05:58:39Z."
  - "Probe script committed with static fallback artifact so plan is complete even without live Earthdata credentials; re-running populates live ASF counts."
  - "CONCLUSIONS §2.1 Target Bursts uses uniform placeholder convention across all 5 rows -- no hardcoded burst_id (row 4 WARNING fix)."
  - "User checkpoint resolved 2026-04-23 via approve-as-drafted; 5 AOI rows locked for Plan 02-04 consumption; unblocks downstream run_eval_rtc_eu.py BURSTS list."
metrics:
  duration_minutes: 7
  completed_date: "2026-04-23"
  tasks_completed: 3
  tasks_total: 3
  files_created: 3
  commits: 3
status: complete
---

# Phase 2 Plan 02: RTC-EU Burst Probe + CONCLUSIONS Template Summary

**Status:** Complete. Checkpoint resolved 2026-04-23 via `approve-as-drafted`; unblocks Plan 02-04. Probe artifact, CONCLUSIONS template shell, and user approval record all committed; 5-regime burst candidate list is locked for downstream `run_eval_rtc_eu.py::BURSTS` consumption.

**One-liner:** Committed a re-runnable ASF + earthaccess probe script, a git-auditable Claude-drafted 5-regime candidate artifact (Alpine / Scandinavian / Iberian / TemperateFlat / Fire), the CONCLUSIONS_RTC_EU.md shell mirroring v1.0 RTC structure + §5a Terrain-Regime Coverage + §5b Investigation Findings sections, and a user-approval provenance line in the candidates artifact.

## Commits

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Probe script + Claude-drafted candidates markdown | `56505d9` | `scripts/probe_rtc_eu_candidates.py`, `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` |
| 3 | CONCLUSIONS_RTC_EU.md template shell | `b2a4cb6` | `CONCLUSIONS_RTC_EU.md` |
| 2 | User approval record (checkpoint resolution) | `da7f7a7` | `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` |

Task ordering note: Task 3 committed ahead of Task 2 per the orchestrator's pre-checkpoint `<checkpoint_guidance>` (see "Execution Order Note" below). Task 2's commit captures the `approve-as-drafted` user signal returned after the checkpoint paused the original agent.

## Execution Order Note

The plan's task order (1 auto, 2 checkpoint, 3 auto) had an internal inconsistency: Task 2's `what-built` section lists CONCLUSIONS_RTC_EU.md as committed at checkpoint time, but the CONCLUSIONS file is created by Task 3 (after the checkpoint in source-code ordering). The orchestrator's per-worktree `<checkpoint_guidance>` explicitly called for both artifacts to land before the checkpoint. We resolved this by running tasks 1 → 3 → checkpoint so the user has all three artifacts (probe script, probe artifact, CONCLUSIONS shell) available for review when the checkpoint returns.

## Candidate Bursts (D-04, user-approved as-drafted 2026-04-23)

| # | regime | label | centroid_lat | expected_max_relief_m | cached? | cached_source |
|---|--------|-------|--------------|-----------------------|---------|---------------|
| 1 | Alpine | Swiss/Italian Alps (Valtellina region) | 46.35°N | ~3200 m | No | -- |
| 2 | Scandinavian | Northern Sweden (Norrbotten) | 67.15°N | ~500 m | No | -- |
| 3 | Iberian | Iberian Meseta (north of Madrid) | 41.15°N | ~500 m | No | -- |
| 4 | TemperateFlat | Po plain (Bologna, Italy) | 44.50°N | ~100 m | Yes | `eval-disp-egms/input/` |
| 5 | Fire | Central Portugal (Aveiro/Viseu fire footprint) | 40.70°N | ~400 m | Yes | `eval-dist-eu/input/` |

**RTC-01 mandatory constraints:**
- ≥1 burst >1000 m relief: row #1 Alpine (~3200 m expected) -- PASS candidate.
- ≥1 burst >55°N: row #2 Scandinavian (67.15°N) -- PASS candidate.

**P1.1 cached-bias prevention:** 3 of 5 are fresh downloads; both RTC-01-mandatory bursts (Alpine + Scandinavian) are fresh. Cheapness bias structurally excluded.

## Deviations from Plan

### Plan-ordering adjustment (not a rule-based deviation)

Reordered Task 3 (CONCLUSIONS template) ahead of the Task 2 checkpoint per the orchestrator's `<checkpoint_guidance>` directive and to match Task 2's `what-built` expectation that CONCLUSIONS_RTC_EU.md is available for review at checkpoint time. This is not a Rule 1-4 deviation -- it's a resolution of an ordering inconsistency in the plan itself, pre-authorised by the orchestrator prompt.

### Auto-fixed issues

**1. [Rule 3 - Blocking] ruff E501 long lines in probe script markdown strings**
- **Found during:** Task 1 verification.
- **Issue:** Acceptance criteria required `ruff check scripts/probe_rtc_eu_candidates.py` to exit 0, but the plan's literal probe-script template contained 9 lines over the project's 100-char ruff limit (line-length configured in `pyproject.toml:204`).
- **Fix:** Wrapped 9 long string literals in the `_render_markdown` function as multi-line string-concatenation tuples; no behaviour change, all markdown output characters preserved.
- **Files modified:** `scripts/probe_rtc_eu_candidates.py`
- **Commit:** `56505d9`

**2. [Rule 3 - Blocking] `datetime.utcnow()` string + extra `datetime.now(timezone.utc)` in comment**
- **Found during:** Task 1 verification.
- **Issue:** Acceptance criteria required `grep -c "datetime.utcnow()" == 0` and `grep -c "datetime.now(timezone.utc)" == 1`; the plan's literal template comment mentioned both symbols verbatim, bumping the grep counts over/under.
- **Fix:** Reworded the comment to describe the behaviour without naming the symbols ("tz-aware stamp (deprecated utcnow avoided)"), preserving semantic intent.
- **Files modified:** `scripts/probe_rtc_eu_candidates.py`
- **Commit:** `56505d9`

No other deviations. Plan executed as written with the two blocking-issue auto-fixes above.

## Auth Gates

None hit. Task 1's probe script detects missing EARTHDATA credentials gracefully (`main()` returns exit 1 with a clear error message) but is not invoked as part of plan execution; the plan explicitly commits a static initial probe artifact so plan completion does not depend on live credentials. Users can run `micromamba run -n subsideo python scripts/probe_rtc_eu_candidates.py` after `.env` configuration to overwrite the artifact with live counts.

## Checkpoint Resolution

**Type:** decision (despite the plan's `checkpoint:human-verify` label, the orchestrator's per-worktree prompt classified this as a `decision` checkpoint -- user approval of the Claude-drafted 5-burst list was required before Plan 02-04 could consume it).

**Resolved on:** 2026-04-23T05:58:39Z

**User signal:** `approve-as-drafted` -- Claude's 5 regime AOI drafts accepted as-is; no AOI edits, no probe re-run, no rework. Plan 02-04 derives concrete burst_ids from the probe (live) or SAFE inspection at execution time.

**Provenance record:** `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` §User Approval (committed as `da7f7a7`) is the canonical audit line for downstream plans referencing this decision.

## Hand-off to Plan 02-04

- `BURSTS: list[BurstConfig]` entries in `run_eval_rtc_eu.py` derive from the approved probe artifact rows.
- Each fresh-download regime (rows 1-3) needs a concrete `burst_id` (JPL lowercase `t<relorb>_<burst>_iw<swath>`) derived from ASF + `opera_utils.get_burst_id` inspection of the chosen SLC.
- Cached regimes (rows 4-5) get their `burst_id` from inspecting the existing `eval-disp-egms/input/` and `eval-dist-eu/input/` SAFEs (if present); if absent, treat as fresh-download.
- `cached_safe_dir` hints already encoded in the probe `Candidate` namedtuple so D-02 `find_cached_safe` fallback order is documented.

## Self-Check

Files claimed to be created/modified:
- `scripts/probe_rtc_eu_candidates.py` -- FOUND
- `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` -- FOUND (approval section appended in commit `da7f7a7`)
- `CONCLUSIONS_RTC_EU.md` -- FOUND
- `.planning/phases/02-rtc-s1-eu-validation/02-02-SUMMARY.md` -- FOUND (finalized in this session)

Commits claimed:
- `56505d9` -- FOUND (Task 1: probe script + Claude-drafted candidates)
- `b2a4cb6` -- FOUND (Task 3: CONCLUSIONS_RTC_EU.md shell)
- `da7f7a7` -- FOUND (Task 2: user approval record, checkpoint resolution)

Plan-level verification:
- `test -f` for all 3 artifacts: PASS
- Probe parse: PASS
- Probe ruff: PASS
- 5 regime rows in probe artifact: PASS
- §5a + §5b sections in CONCLUSIONS: PASS
- User Approval section present in candidates artifact: PASS
- tasks_completed = tasks_total = 3: PASS
- status: complete: PASS

## Self-Check: PASSED
