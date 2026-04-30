---
phase: 03-cslc-s1-self-consistency-eu-validation
plan: 04
subsystem: validation
status: partial -- Task 1 (code) complete; Task 2 (compute + CONCLUSIONS + sign-off) deferred to user
tags: [cslc, eu, self-consistency, egms, tdd, phase3]
dependency_graph:
  requires:
    - 03-01 (compare_cslc_egms_l2a_residual, CSLCSelfConsistEUCellMetrics, matrix_schema)
    - 03-02 (probe artifact: IberianAOI epochs + burst_id locked)
  provides:
    - run_eval_cslc_selfconsist_eu.py (EU CSLC eval script, Task 1)
    - tests/unit/test_run_eval_cslc_selfconsist_eu.py (static invariant tests, Task 1)
  affects:
    - eval-cslc-selfconsist-eu/ (cache dir, Task 2)
    - CONCLUSIONS_CSLC_EU.md (Task 2 -- NOT created here)
    - results/matrix_manifest.yml cslc:eu cell (Task 2)
tech_stack:
  added: []
  patterns:
    - ENV-07 fork discipline (EU script is near-clone of NAM script)
    - Three-number PQ schema (CSLC-05: amplitude sanity + coherence + EGMS residual)
    - TDD red/green with AST-level source invariant tests
    - _fetch_egms_l2a cache-hit pattern (D-08 resume-safe for EGMS download)
key_files:
  created:
    - run_eval_cslc_selfconsist_eu.py
    - tests/unit/test_run_eval_cslc_selfconsist_eu.py
  modified: []
decisions:
  - "IBERIAN_PRIMARY_EPOCHS tuple pasted verbatim from probe artifact (15 datetime literals)"
  - "Fallback burst_ids for Alentejo (t008_016940_iw2) and MassifCentral (t131_279647_iw2) are probe-derived placeholders pending user confirmation at eval time"
  - "numpy imported at top of __main__ block (not lazily) to allow type annotations in helpers"
  - "matplotlib.use('Agg') called after imports to satisfy ruff I001 sort order"
  - "ENV-07 diff test (Test 7) skips when NAM script absent -- correct for parallel wave execution"
metrics:
  duration: "~25 min (Task 1 only)"
  completed: "2026-04-24"
  tasks_completed: 1
  tasks_total: 2
  files_created: 2
  files_modified: 0
---

# Phase 03 Plan 04: EU CSLC Self-Consistency Eval Script + Tests Summary

**One-liner:** EU CSLC self-consistency eval script with three-number PQ schema (amplitude sanity + coherence + EGMS L2a residual) and 21 static-invariant unit tests — Task 1 complete; Task 2 (14h live compute + CONCLUSIONS) deferred to user.

## Status

**PARTIAL** — Task 1 complete and committed. Task 2 is a `checkpoint:human-verify` requiring 14h live CSLC compute + EGMS L2a comparison + human sign-off. Task 2 is explicitly out of scope for this executor per the objective.

## Task 1 Completed

### TDD Red Phase (commit ac208e5)

`tests/unit/test_run_eval_cslc_selfconsist_eu.py` written with 21 static-invariant + structural tests. All tests confirmed failing before `run_eval_cslc_selfconsist_eu.py` existed.

### TDD Green Phase (commit 52aff66)

`run_eval_cslc_selfconsist_eu.py` implemented from scratch per 03-04 plan spec (Option A — written from plan description rather than forked from sibling NAM script which didn't exist in this worktree).

**Key invariants satisfied:**

| Invariant | Value | Status |
|-----------|-------|--------|
| `EXPECTED_WALL_S` | `60 * 60 * 14` (BinOp at module level) | PASS |
| `AOIS` list length | 1 (IberianAOI only) | PASS |
| `IberianAOI.burst_id` | `t103_219329_iw1` (Meseta-North) | PASS |
| `_IBERIAN_FALLBACKS` tuple length | 2 (Alentejo + MassifCentral) | PASS |
| `run_amplitude_sanity=True` count | 3 (all EU AOIConfig entries) | PASS |
| `CACHE` path | `eval-cslc-selfconsist-eu` | PASS |
| EGMS subdir | `CACHE / "egms"` in mkdir block | PASS |
| `product_level` | `"L2a"` | PASS |
| `release` | `"2019_2023"` | PASS |
| `stable_std_max` | `2.0` | PASS |
| PQ key 1 | `coherence_median_of_persistent` | PASS |
| PQ key 2 | `residual_mm_yr` | PASS |
| PQ key 3 | `egms_l2a_stable_ps_residual_mm_yr` | PASS |
| Reduce class | `CSLCSelfConsistEUCellMetrics` | PASS |

### Epoch Tuples (verbatim from probe artifact)

All 15-entry epoch tuples pasted verbatim from `.planning/milestones/v1.1-research/cslc_selfconsist_aoi_candidates.md`:

**IBERIAN_PRIMARY_EPOCHS (Meseta-North, t103_219329_iw1):**
2024-01-04T06:18:03Z through 2024-03-04T06:18:02Z — 15 epochs over 59 days.

**IBERIAN_ALENTEJO_EPOCHS (Iberian/Alentejo fallback):**
2024-01-01T18:35:22Z through 2024-02-12T06:43:35Z — 15 epochs.

**IBERIAN_MASSIF_CENTRAL_EPOCHS (Iberian/MassifCentral fallback):**
2024-01-01T05:52:18Z through 2024-02-11T06:00:25Z — 15 epochs.

### Test Results

```
21 passed, 1 skipped in GREEN phase
```

Skipped: `test_env07_diff_discipline` — correctly skipped because `run_eval_cslc_selfconsist_nam.py` does not exist in this worktree (parallel wave execution; NAM script is being created concurrently in agent-a4063061). The test will run and enforce ENV-07 once the NAM script is merged.

### Ruff

Both files pass `ruff check` with zero errors.

## Task 2 Deferred to User

Task 2 is `type="checkpoint:human-verify" gate="blocking"`. It requires:

1. Running `make eval-cslc-eu` (~14h cold run budget)
2. Inspecting `eval-cslc-selfconsist-eu/metrics.json` three-number schema values
3. Downloading EGMS L2a per-track CSVs via EGMStoolkit
4. Populating `CONCLUSIONS_CSLC_EU.md` (9-section structure + §6 three-number table)
5. Human sign-off: `lgtm-proceed` or `revise: <specifics>`

**CONCLUSIONS_CSLC_EU.md has NOT been created.** This is correct — it is a Task 2 deliverable.

## Deviations from Plan

**1. [Rule 1 - Bug] ENV-07 diff test adjusted for parallel wave context**
- The plan spec assumes `run_eval_cslc_selfconsist_nam.py` exists as the fork source. In this worktree (base commit `eb644eab`), the NAM script does not yet exist — it is being created by sibling plan 03-03 in a parallel worktree.
- Fix: the EU script was written from scratch using the plan's full spec (Option A per objective). The ENV-07 diff test correctly skips when the NAM script is absent, and will enforce discipline once the NAM script lands in the main branch.

**2. [Rule 2 - Missing critical functionality] `numpy` imported at top of `__main__`**
- The plan spec shows `import numpy as np` lazily at the bottom of the `__main__` block. However, helper functions (`_compute_ifg_coherence_stack`, `_compute_slope_deg`, type annotations) reference `np` earlier in the block.
- Fix: moved `import numpy as np` to the top of the `__main__` import block (with `import earthaccess`). This is ENV-07 compliant since both NAM and EU scripts would have the same fix.

**3. [Rule 2 - Missing critical functionality] `ruff` I001 import ordering in `_write_sanity_artifacts`**
- The plan spec shows `matplotlib.use("Agg")` between `import matplotlib` and `import matplotlib.pyplot`. This violates ruff's I001 import sort rule (call between imports).
- Fix: moved `matplotlib.use("Agg")` after all three imports in the function body. Added blank line between `json` (stdlib) and `matplotlib` (third-party) per isort convention.

## Downstream Contract for Plan 03-05

- `CONCLUSIONS_CSLC_EU.md §6` Iberian row (three-number table) is the motivating example for `docs/validation_methodology.md §2` (Plan 03-05 reads this doc when writing §2).
- The EU script's `CSLCSelfConsistEUCellMetrics` reduce writes `eval-cslc-selfconsist-eu/metrics.json` for matrix_writer.
- First-rollout: Iberian AOIResult.status == `CALIBRATING` (calibration data point 3 per D-03). Matrix cell renders `*1/1 CALIBRATING: coh=X.XX / resid=Y.Y mm/yr / egms_resid=Z.Z mm/yr*`.

## Commits

| Hash | Message |
|------|---------|
| ac208e5 | `test(03-04): add failing tests for run_eval_cslc_selfconsist_eu.py (red phase)` |
| 52aff66 | `feat(03-04): implement run_eval_cslc_selfconsist_eu.py + unit tests (green phase)` |

## Self-Check

- [x] `run_eval_cslc_selfconsist_eu.py` exists at repo root
- [x] `tests/unit/test_run_eval_cslc_selfconsist_eu.py` exists
- [x] 21 tests pass, 1 skipped (ENV-07 diff, NAM absent — expected in parallel wave)
- [x] `EXPECTED_WALL_S = 60 * 60 * 14` at module top level
- [x] `IBERIAN_PRIMARY_EPOCHS` 15-tuple matches probe artifact verbatim
- [x] Three-number schema keys present in pq_measurements
- [x] `CSLCSelfConsistEUCellMetrics` used in reduce
- [x] `CONCLUSIONS_CSLC_EU.md` NOT populated (Task 2 deliverable — correct)
- [x] STATE.md NOT modified (orchestrator owns)
- [x] ROADMAP.md NOT modified (orchestrator owns)

## Self-Check: PASSED
