---
phase: 06-dswx-s2-n-am-eu-recalibration
plan: 02
subsystem: dswx-scaffolding
tags: [foundation, schema, threshold-module, retry-policy, additive, immutability, wave-1]
dependency_graph:
  requires:
    - 05-dist-s1-opera-v0-1-effis-eu
    - 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
  provides:
    - src/subsideo/products/dswx_thresholds.py
    - Settings.dswx_region
    - CRITERIA["dswx.nam.investigation_f1_max"]
    - RETRY_POLICY["jrc"]
    - DswxNamCellMetrics, DswxEUCellMetrics, DSWEThresholdsRef, PerAOIF1Breakdown, LOOCVPerFold, RegressionDiagnostic
  affects:
    - 06-03
    - 06-04
    - 06-05
    - 06-06
tech_stack:
  added:
    - src/subsideo/products/dswx_thresholds.py
    - pydantic ConfigDict(ser_json_inf_nan="constants") for NaN-preserving JSON round-trip
  patterns:
    - frozen+slots dataclass for typed threshold constants
    - pydantic-settings validation_alias + populate_by_name for SUBSIDEO_DSWX_REGION
    - ser_json_inf_nan=constants for NaN float preservation in BLOCKER state
key_files:
  created:
    - src/subsideo/products/dswx_thresholds.py
    - tests/unit/test_dswx_thresholds.py
    - tests/unit/test_criteria_dswx_investigation.py
    - tests/unit/test_harness_jrc_retry.py
    - tests/unit/test_matrix_schema_dswx.py
  modified:
    - src/subsideo/config.py
    - src/subsideo/validation/criteria.py
    - src/subsideo/validation/harness.py
    - src/subsideo/validation/matrix_schema.py
    - tests/unit/test_criteria_registry.py
decisions:
  - "frozen+slots DSWEThresholds: slots=True for typo-prevention per CONTEXT D-09"
  - "Settings.dswx_region uses validation_alias=SUBSIDEO_DSWX_REGION + populate_by_name=True"
  - "LOOCVPerFold uses snake_case (refit_best_wigt) per ruff N815 class-scope naming rule"
  - "DswxEUCellMetrics uses ser_json_inf_nan=constants for NaN-preserving JSON round-trip in BLOCKER state"
  - "test_criteria_registry.py count tests updated to 16/3 as additive correction"
metrics:
  duration: "40 minutes"
  completed: "2026-04-26"
  tasks_completed: 3
  files_created: 5
  files_modified: 5
---

# Phase 6 Plan 02: DSWx Wave 1 Foundation Scaffolding Summary

**One-liner:** Pure-additive Wave 1 scaffolding: DSWEThresholds frozen dataclass + dswx_region env-var + RETRY_POLICY[jrc] + 6 Pydantic cell-metrics types + INVESTIGATION_TRIGGER entry, with ZERO changes to existing dswx pipeline behavior.

## Tasks

### Task 1: DSWEThresholds module + Settings.dswx_region (commit 7bed3d3)

Created src/subsideo/products/dswx_thresholds.py with frozen+slots DSWEThresholds dataclass
(WIGT/AWGT/PSWT2_MNDWI + 8 provenance fields), THRESHOLDS_NAM (PROTEUS defaults),
THRESHOLDS_EU (placeholder; Plan 06-06 overwrites), THRESHOLDS_BY_REGION dispatch dict,
and W1 sentinel-comment anchors for Plan 06-06 fail-loud rewrite.

Modified src/subsideo/config.py to add dswx_region: Literal["nam","eu"] with
validation_alias="SUBSIDEO_DSWX_REGION" and populate_by_name=True.

11 unit tests in test_dswx_thresholds.py - all pass.

### Task 2: criteria.py INVESTIGATION_TRIGGER + harness.RETRY_POLICY[jrc] (commit 7c18a7d)

Added dswx.nam.investigation_f1_max INVESTIGATION_TRIGGER (0.85, comparator=<) +
dswx_nam_investigation_f1_max() accessor to criteria.py. Pre-existing 15 entries UNCHANGED.

Added RetrySource literal jrc + RETRY_POLICY[jrc] branch to harness.py.
Pre-existing 5 entries UNCHANGED.

Updated test_criteria_registry.py count assertions (15->16, investigation 2->3).
9 unit tests in new test files - all pass.

### Task 3: 6 new Pydantic v2 types to matrix_schema.py (commit 0332629)

Added DswxNamCellStatus, DswxEUCellStatus, DSWEThresholdsRef, PerAOIF1Breakdown,
LOOCVPerFold, RegressionDiagnostic, DswxNamCellMetrics, DswxEUCellMetrics after
DistNamCellMetrics (Phase 5 D-25 immutability lock honored). ZERO existing type removals.
15 unit tests in test_matrix_schema_dswx.py - all pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] LOOCVPerFold field names renamed to snake_case**
- Found during: Task 3 ruff check (N815 mixed-case class-scope variable)
- Fix: refit_best_WIGT -> refit_best_wigt (etc.)
- Commit: 0332629

**2. [Rule 1 - Bug] DSWEThresholds slots TypeError vs AttributeError in Python 3.12**
- Found during: Task 1 test_dswethresholds_slots
- Fix: pytest.raises((AttributeError, TypeError))
- Commit: 7bed3d3

**3. [Rule 1 - Bug] test_criteria_registry.py count assertions outdated after additive entry**
- Found during: Task 2 broader criteria test run
- Fix: count 15->16, investigation trigger count 2->3
- Commit: 7c18a7d

**4. [Rule 1 - Bug] Settings.dswx_region maps to DSWX_REGION not SUBSIDEO_DSWX_REGION without alias**
- Found during: Task 1 env-var test failure
- Fix: validation_alias="SUBSIDEO_DSWX_REGION" + populate_by_name=True
- Commit: 7bed3d3

**5. [Rule 2 - Missing] DswxEUCellMetrics NaN JSON round-trip broken by default Pydantic null serialization**
- Found during: Task 3 BLOCKER state test
- Fix: ser_json_inf_nan="constants" in DswxNam/EUCellMetrics ConfigDict
- Commit: 0332629

**6. [Rule 3 - Blocking] Worktree/main-repo git context isolation**
- Found during: Post-Task 2 commit infrastructure check
- Issue: Write/Edit tools target main repo absolute paths; commits must land on worktree branch
- Fix: Task 1 found already staged in worktree index; Task 2 cherry-picked (c39f9ae); Task 3 files copied via Python shutil then staged/committed in worktree context
- All three tasks confirmed on worktree branch worktree-agent-aecb5479e7db43ce7

## Known Stubs

- THRESHOLDS_EU in dswx_thresholds.py: PLACEHOLDER threshold values (matching NAM defaults) and NaN provenance metrics. Intentional - Plan 06-06 Stage 10 overwrites. W1 sentinel anchors enable fail-loud rewrite.

## Threat Flags

None.

## Behavior Parity Verification

Full unit test suite: 476 passed, 8 failed (all 8 are pre-existing failures predating base commit 2380a01). ZERO new failures from Plan 06-02. 35 new tests all pass.

## Self-Check: PASSED

- FOUND: src/subsideo/products/dswx_thresholds.py
- FOUND: src/subsideo/config.py (dswx_region + SUBSIDEO_DSWX_REGION)
- FOUND: src/subsideo/validation/criteria.py (dswx.nam.investigation_f1_max)
- FOUND: src/subsideo/validation/harness.py (RETRY_POLICY[jrc])
- FOUND: src/subsideo/validation/matrix_schema.py (DswxNamCellMetrics, DswxEUCellMetrics)
- FOUND: tests/unit/test_dswx_thresholds.py
- FOUND: tests/unit/test_criteria_dswx_investigation.py
- FOUND: tests/unit/test_harness_jrc_retry.py
- FOUND: tests/unit/test_matrix_schema_dswx.py
- FOUND: 7bed3d3 (Task 1 worktree)
- FOUND: 7c18a7d (Task 2 worktree cherry-pick)
- FOUND: 0332629 (Task 3 worktree)
