---
phase: 09
slug: cslc-egms-third-number-binding-reruns
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-30
---

# Phase 09 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/unit/test_matrix_schema.py tests/unit/test_matrix_writer.py tests/unit/test_criteria_registry.py tests/unit/test_compare_cslc.py tests/unit/test_run_eval_cslc_selfconsist_nam.py tests/unit/test_run_eval_cslc_selfconsist_eu.py -q` |
| **Full suite command** | `pytest tests/unit/ -x -q --tb=short` |
| **Estimated runtime** | ~120 seconds for focused suite; broad unit runtime depends on local cache/import state |

---

## Sampling Rate

- **After every task commit:** Run the focused Phase 9 unit command when touched files are in schema, matrix writer, criteria, compare_cslc, or CSLC eval scripts.
- **After every plan wave:** Run `pytest tests/unit/ -x -q --tb=short`.
- **Before `$gsd-verify-work`:** Full unit suite must be green; live CSLC rerun artifacts must exist or named blocker sidecars must explain current upstream failure.
- **Max feedback latency:** 120 seconds for focused local tests.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | CSLC-07, VAL-01, VAL-03 | T-09-01-01 / T-09-01-02 | Candidate thresholds and blocker evidence are schema-valid without registry promotion | unit | `pytest tests/unit/test_matrix_schema.py -q` | ✅ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | CSLC-07, VAL-01, VAL-03 | T-09-01-01 | Candidate constants live at true module scope and eval scripts write candidate verdicts | unit | `pytest tests/unit/test_run_eval_cslc_selfconsist_nam.py tests/unit/test_run_eval_cslc_selfconsist_eu.py -q` | ✅ W0 | ⬜ pending |
| 09-02-01 | 02 | 2 | CSLC-10, VAL-01, VAL-03 | T-09-02-01 / T-09-02-02 | EGMS diagnostics expose stable PS counts, valid paired samples, thresholds, adapter column, and blocker reason | unit | `pytest tests/unit/test_compare_cslc.py -q` | ✅ W0 | ⬜ pending |
| 09-02-02 | 02 | 2 | CSLC-10, VAL-01, VAL-03 | T-09-02-02 / T-09-02-03 | Missing EGMS residual becomes named blocker with version, retry, counts, thresholds, and no token leakage | unit | `pytest tests/unit/test_run_eval_cslc_selfconsist_eu.py -q` | ✅ W0 | ⬜ pending |
| 09-03-01 | 03 | 2 | CSLC-11, VAL-01, VAL-03 | T-09-03-01 / T-09-03-02 | Mojave fallback chain records OPERA frame-search evidence without expanding AOI scope | unit | `pytest tests/unit/test_run_eval_cslc_selfconsist_nam.py -q` | ✅ W0 | ⬜ pending |
| 09-03-02 | 03 | 2 | CSLC-11, VAL-01, VAL-03 | T-09-03-02 | Tests pin Coso-Searles/Pahranagat/Amargosa order and reject Hualapai reintroduction | unit | `pytest tests/unit/test_run_eval_cslc_selfconsist_nam.py -q` | ✅ W0 | ⬜ pending |
| 09-04-01 | 04 | 3 | CSLC-07, CSLC-10, CSLC-11, VAL-03 | T-09-04-01 / T-09-04-03 | Matrix renders candidate BINDING PASS/FAIL/BLOCKER without exposing sensitive evidence | unit | `pytest tests/unit/test_matrix_writer.py -q` | ✅ W0 | ⬜ pending |
| 09-04-02 | 04 | 3 | CSLC-07, CSLC-10, CSLC-11, VAL-03 | T-09-04-02 | Conclusions skeleton separates product-quality, reference-agreement, and blocker evidence | grep | `grep -c "TODO(Phase 9 rerun):" CONCLUSIONS_CSLC_SELFCONSIST_NAM.md CONCLUSIONS_CSLC_SELFCONSIST_EU.md` | ✅ W0 | ⬜ pending |
| 09-05-01 | 05 | 4 | CSLC-07, CSLC-10, CSLC-11, VAL-01, VAL-03 | T-09-05-01 / T-09-05-02 | Live reruns write sidecars or accepted named blocker evidence without storing credentials | manual/integration | `make eval-cslc-eu && make eval-cslc-nam && make results-matrix` | ✅ W0 | ⬜ pending |
| 09-05-02 | 05 | 4 | CSLC-07, VAL-03 | T-09-05-03 | Criteria promotion occurs only after regenerated sidecars support BINDING PASS | unit | `pytest tests/unit/test_criteria_registry.py tests/unit/test_matrix_writer.py tests/unit/test_matrix_schema.py -q` | ✅ W0 | ⬜ pending |
| 09-05-03 | 05 | 4 | CSLC-07, CSLC-10, CSLC-11, VAL-01, VAL-03 | T-09-05-03 / T-09-05-04 | Final unit suite and matrix CSLC rows prove execution output is coherent | unit/grep | `pytest tests/unit/ -x -q --tb=short && grep -n "CSLC" results/matrix.md` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements:

- [x] `tests/unit/test_matrix_schema.py`
- [x] `tests/unit/test_matrix_writer.py`
- [x] `tests/unit/test_criteria_registry.py`
- [x] `tests/unit/test_compare_cslc.py`
- [x] `tests/unit/test_run_eval_cslc_selfconsist_nam.py`
- [x] `tests/unit/test_run_eval_cslc_selfconsist_eu.py`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live EU CSLC EGMS rerun | CSLC-10, VAL-01 | Requires credentials and current EGMS/ASF/Earthdata availability | Run `make eval-cslc-eu`; verify `eval-cslc-selfconsist-eu/metrics.json` has finite `egms_l2a_stable_ps_residual_mm_yr` or named `egms_l2a_` blocker evidence |
| Live N.Am. CSLC Mojave rerun | CSLC-11, VAL-01 | Requires cached or downloadable SAFE/OPERA reference data | Run `make eval-cslc-nam`; verify `eval-cslc-selfconsist-nam/metrics.json` has `opera_frame_search` and amplitude sanity or `mojave_opera_frame_unavailable` |
| Final CSLC matrix disposition | CSLC-07, VAL-03 | Depends on regenerated sidecars and possible accepted upstream blockers | Run `make results-matrix`; verify `results/matrix.md` CSLC rows contain `BINDING PASS`, `BINDING FAIL`, or `BINDING BLOCKER` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or manual live-rerun dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s for focused local tests
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
