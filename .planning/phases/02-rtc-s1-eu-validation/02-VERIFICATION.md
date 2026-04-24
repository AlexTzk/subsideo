---
phase: 02-rtc-s1-eu-validation
verified: 2026-04-22T23:15:00Z
status: passed
score: 8/8 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: null
  previous_score: null
  note: "Initial verification (no prior VERIFICATION.md)"
---

# Phase 2: RTC-S1 EU Validation — Verification Report

**Phase Goal:** Users can run `make eval-rtc-eu` and obtain per-burst PASS/FAIL across 3-5 EU bursts covering ≥3 terrain regimes with at least one >1000 m relief AND at least one >55°N — proving Phase 1 harness on a low-risk deterministic product and demonstrating reproducibility-across-geographies without criterion-creep toward N.Am.'s 0.045 dB headroom.

**Verified:** 2026-04-22T23:15:00Z
**Status:** passed
**Re-verification:** No — initial verification.

## Goal Achievement

### Observable Truths (goal-backward derived)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `make eval-rtc-eu` produced `eval-rtc-eu/metrics.json` + `eval-rtc-eu/meta.json` with per-burst PASS/FAIL across 5 bursts | ✓ VERIFIED | metrics.json has 5 per_burst rows (Alpine/Scandinavian/Iberian/TemperateFlat/Fire); pass_count=3, total=5; meta.json has git_sha=00774ca3..., run_duration_s=4204.32 |
| 2 | RTC-01: ≥3 terrain regimes covered | ✓ VERIFIED | 5 regimes present in `per_burst[].regime`: {Alpine, Scandinavian, Iberian, TemperateFlat, Fire} |
| 3 | RTC-01: ≥1 burst with >1000 m relief (structural, from metrics.json) | ✓ VERIFIED | 3 bursts satisfy: Alpine `t066_140413_iw1` max_relief_m=3796.05m; Iberian `t103_219329_iw1` 1494.33m; TemperateFlat `t117_249422_iw2` 1015.86m |
| 4 | RTC-01: ≥1 burst >55°N (structural, from metrics.json) | ✓ VERIFIED | Scandinavian `t058_122828_iw3` lat=67.15°N (12° above the bar) |
| 5 | RTC-02: EU RTC reference-agreement criteria identical to N.Am. (RMSE < 0.5 dB, r > 0.99); no tightened gate | ✓ VERIFIED | criteria.py line 43: `rtc.rmse_db_max` threshold=0.5 BINDING; line 52: `rtc.correlation_min` threshold=0.99 BINDING; rtc.eu.* keys count = 2, all type=INVESTIGATION_TRIGGER (non-gate); zero gate entries with `rtc.eu.` prefix |
| 6 | RTC-03: CONCLUSIONS_RTC_EU.md populated (§2.1 target bursts, §5 results, §5a terrain coverage with checkboxes, §5b investigation sub-sections for all flagged bursts) | ✓ VERIFIED | §2.1 at L34, §5 at L174, §5a at L192, §5b at L212, §5b.1 Alpine at L220, §5b.2 Iberian at L238; both RTC-01 checkboxes ticked ☑ (L207-208) |
| 7 | `results/matrix.md` rtc:eu row renders as `3/5 PASS (2 FAIL) ⚠` via matrix_writer from metrics.json | ✓ VERIFIED | L10: `| RTC | EU | — | 3/5 PASS (2 FAIL) ⚠ |` — ⚠ glyph confirms any_investigation_required=True; em-dash in PQ column confirms no product-quality gate for RTC |
| 8 | All 85 framework unit tests pass (5 test files: matrix_schema + criteria_registry + harness + matrix_writer + rtc_eu_eval) | ✓ VERIFIED | `pytest tests/unit/test_matrix_schema.py tests/unit/test_criteria_registry.py tests/unit/test_harness.py tests/unit/test_matrix_writer.py tests/unit/test_rtc_eu_eval.py --no-cov` → 85 passed, 4 warnings in 38.97s |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/subsideo/validation/matrix_schema.py` | `BurstResult` + `RTCEUCellMetrics` Pydantic classes | ✓ VERIFIED | Imports succeed; `RTCEUCellMetrics.model_validate_json(metrics.json)` succeeds on actual file |
| `src/subsideo/validation/criteria.py` | 15 CRITERIA entries (9 BINDING + 4 CALIBRATING + 2 INVESTIGATION_TRIGGER); `Criterion.type` Literal extended | ✓ VERIFIED | `len(CRITERIA) == 15`; RTC-EU entries at L64, L76; accessors at L246, L250 |
| `src/subsideo/validation/harness.py` | `find_cached_safe(granule_id, search_dirs)` helper | ✓ VERIFIED | Exported from `subsideo.validation` package; used at run_eval_rtc_eu.py:420 |
| `src/subsideo/validation/matrix_writer.py` | `_is_rtc_eu_shape` + `_render_rtc_eu_cell` + INVESTIGATION_TRIGGER filter in `_render_cell_column` | ✓ VERIFIED | L163 `_is_rtc_eu_shape`, L184 `_render_rtc_eu_cell`, L115 filter `!= "INVESTIGATION_TRIGGER"`, L227 ⚠ glyph (u26a0 escape) |
| `run_eval_rtc_eu.py` | Module-level EXPECTED_WALL_S + declarative BURSTS list(5) + per-burst try/except + RTC-EU imports | ✓ VERIFIED | L35 `EXPECTED_WALL_S = 60 * 60 * 4` (14400s); L108 `BURSTS: list[BurstConfig] = [` with 5 regime entries; L585 `except Exception` for per-burst isolation; imports find_cached_safe, RTCEUCellMetrics, BurstResult, credential_preflight |
| `scripts/probe_rtc_eu_candidates.py` | Re-runnable probe script for candidate bursts | ✓ VERIFIED | 12,551 bytes; asf_search + earthaccess pattern |
| `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` | 5-regime probe artifact | ✓ VERIFIED | 5,428 bytes; refreshed Plan 02-05 Task 1 |
| `CONCLUSIONS_RTC_EU.md` | Populated per-burst results, terrain-regime coverage, investigation sub-sections | ✓ VERIFIED | Result line: "MIXED (3/5 PASS, 2/5 FAIL with investigation)"; Date: 2026-04-23; all 5 §2.1 rows concrete; §5a checkboxes ticked ☑ |
| `eval-rtc-eu/metrics.json` | RTCEUCellMetrics with per_burst[5] | ✓ VERIFIED | Valid schema; pass_count=3, total=5, any_investigation_required=true; 5 per_burst entries |
| `eval-rtc-eu/meta.json` | MetaJson provenance (git_sha, run_duration_s, platform, input_hashes) | ✓ VERIFIED | git_sha=00774ca3dd03af8968f575e121bee72928264ddb; run_duration_s=4204.32; platform=macOS-26.3.1-arm64; 8 input hashes |
| `results/matrix.md` | rtc:eu row with X/N PASS format | ✓ VERIFIED | L10: `| RTC | EU | — | 3/5 PASS (2 FAIL) ⚠ |` |
| `tests/unit/test_rtc_eu_eval.py` | Structural invariant tests for run_eval_rtc_eu.py | ✓ VERIFIED | 11,075 bytes; 13 tests pass (part of 85-test sweep) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `run_eval_rtc_eu.py` | `subsideo.validation.harness.find_cached_safe` | import + per-burst call | ✓ WIRED | L67 import; L420 call at `cached_safe = find_cached_safe(...)` |
| `run_eval_rtc_eu.py` | `RTCEUCellMetrics + BurstResult` | metrics.json construction | ✓ WIRED | L71, L75 imports; L653 `metrics = RTCEUCellMetrics(...)`; L536 + L592 `BurstResult(...)` |
| `run_eval_rtc_eu.py` | `CRITERIA['rtc.eu.investigation_*']` | investigation_required derivation | ✓ WIRED | L510 threshold, L513 threshold from CRITERIA lookup (not hardcoded) |
| `matrix_writer.py::write_matrix` | `RTCEUCellMetrics` shape | `_is_rtc_eu_shape(per_burst key)` detection | ✓ WIRED | L163 helper; schema dispatch at L269-... in write_matrix loop |
| `matrix_writer.py::_render_cell_column` | `CRITERIA[cid].type != "INVESTIGATION_TRIGGER"` | criterion filter | ✓ WIRED | L115 filter present; INVESTIGATION_TRIGGER excluded from PQ/RA column rendering |
| `CONCLUSIONS_RTC_EU.md §5 + §5a` | `eval-rtc-eu/metrics.json` per-burst values | human transcription | ✓ WIRED | Concrete RMSE/r/max_relief/lat values transcribed from metrics.json (e.g. Alpine 1.152 dB RMSE, 3796.05m relief, 46.35°N) |
| `CONCLUSIONS_RTC_EU.md §5b` | `per_burst[].investigation_required` | one sub-section per flagged burst | ✓ WIRED | 2 triggered bursts in metrics (Alpine L51 inv=true, Iberian L99 inv=true) → 2 sub-sections in CONCLUSIONS (§5b.1 Alpine, §5b.2 Iberian) — exact 1:1 correspondence |
| `results/matrix.md` rtc:eu row | `eval-rtc-eu/metrics.json` | `matrix_writer` reads metrics.json → X/N PASS rendering | ✓ WIRED | Rendered value `3/5 PASS (2 FAIL) ⚠` matches metrics.json's `pass_count=3, total=5, any_investigation_required=true` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `eval-rtc-eu/metrics.json` | per_burst[] | run_eval_rtc_eu.py invokes run_rtc + compare_rtc for each burst | ✓ Real data (measured RMSE/correlation/bias from 4/5 real RTC runs; Fire FAIL has explicit error + traceback) | ✓ FLOWING |
| `results/matrix.md` | rtc:eu row | matrix_writer reads metrics.json via `_render_rtc_eu_cell` → RTCEUCellMetrics.model_validate_json | ✓ Real data (3/5 PASS rendered from real pass_count; ⚠ from real any_investigation_required) | ✓ FLOWING |
| `CONCLUSIONS_RTC_EU.md §5` | per-burst RMSE/r/max_relief/lat | human-transcribed from eval-rtc-eu/metrics.json (e.g. Alpine 1.152 dB RMSE from per_burst[0], 3796.05m from max_relief_m, 46.35 from lat) | ✓ Real data; values match metrics.json exactly | ✓ FLOWING |
| `CONCLUSIONS_RTC_EU.md §5b.1 Alpine` | observation RMSE/r/bias/SSIM | transcribed from metrics.json per_burst[0] | ✓ Real data: RMSE 1.152, r 0.9754, bias −0.211 matches metrics exactly | ✓ FLOWING |
| `CONCLUSIONS_RTC_EU.md §5b.2 Iberian` | observation RMSE/r/bias/SSIM | transcribed from metrics.json per_burst[2] | ✓ Real data: RMSE 0.354, r 0.9926, bias −0.029 matches metrics exactly | ✓ FLOWING |

No HOLLOW / DISCONNECTED / STATIC data-flow issues detected.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 85 framework tests pass | `python -m pytest tests/unit/test_matrix_schema.py tests/unit/test_criteria_registry.py tests/unit/test_harness.py tests/unit/test_matrix_writer.py tests/unit/test_rtc_eu_eval.py --no-cov` | `85 passed, 4 warnings in 38.97s` | ✓ PASS |
| RTCEUCellMetrics validates actual metrics.json | `python -c "from subsideo.validation.matrix_schema import RTCEUCellMetrics; RTCEUCellMetrics.model_validate_json(open('eval-rtc-eu/metrics.json').read())"` | No exception | ✓ PASS |
| CRITERIA registry has 15 entries, 2 INVESTIGATION_TRIGGER | `python -c "from subsideo.validation.criteria import CRITERIA; assert len(CRITERIA)==15; rtc_eu=[k for k in CRITERIA if k.startswith('rtc.eu.')]; assert len(rtc_eu)==2; assert all(CRITERIA[k].type=='INVESTIGATION_TRIGGER' for k in rtc_eu)"` | No exception | ✓ PASS |
| RTC BINDING thresholds unchanged (RTC-02) | `python -c "from subsideo.validation.criteria import CRITERIA; assert CRITERIA['rtc.rmse_db_max'].threshold==0.5; assert CRITERIA['rtc.correlation_min'].threshold==0.99; assert CRITERIA['rtc.rmse_db_max'].type=='BINDING'; assert CRITERIA['rtc.correlation_min'].type=='BINDING'"` | No exception | ✓ PASS |
| Alpine max_relief_m structurally > 1000 | JSON parse of `per_burst[regime=Alpine].max_relief_m` | 3796.05 > 1000 | ✓ PASS |
| Scandinavian lat structurally > 55 | JSON parse of `per_burst[regime=Scandinavian].lat` | 67.15 > 55 | ✓ PASS |

### Requirements Coverage (RTC-01, RTC-02, RTC-03 × 5 plans)

Plan-frontmatter → PLAN-requirements claim → SUMMARY requirements-completed mapping:

| Requirement | Plan Frontmatter (expected) | Implementation Evidence | Status |
|-------------|-----------------------------|-------------------------|--------|
| **RTC-01** (per-burst PASS/FAIL, ≥3 regimes, ≥1 >1000m relief AND ≥1 >55°N) | 02-01, 02-02, 02-03, 02-04, 02-05 (5 plans) | Framework extensions (schema/criteria/harness) at 02-01; probe at 02-02; matrix_writer branch at 02-03; eval script at 02-04; real run + CONCLUSIONS at 02-05. Structural audit of metrics.json confirms 5 regimes, 3 bursts >1000m, 1 burst >55°N. | ✓ SATISFIED |
| **RTC-02** (EU RTC criteria identical to N.Am., no tightening) | 02-01, 02-05 (2 plans) | 02-01 added 2 INVESTIGATION_TRIGGER entries (non-gates); 02-05 confirmed criteria.py thresholds unchanged. criteria.py line 43: `threshold=0.5` BINDING; line 52: `threshold=0.99,` BINDING; zero rtc.eu.* gate entries (only 2 INVESTIGATION_TRIGGER). Phase 1 guardrail tests `test_investigation_triggers_do_not_mutate_rtc_binding` + `test_no_rtc_eu_gate_entries` pass. | ✓ SATISFIED |
| **RTC-03** (CONCLUSIONS populated with selected bursts, regime coverage, per-burst numerical results, investigation findings for materially-different RMSE) | 02-01, 02-02, 02-03, 02-04, 02-05 (5 plans) | 02-02 authored CONCLUSIONS template shell with §5a/§5b sections; 02-01 added INVESTIGATION_TRIGGER criteria; 02-03 matrix_writer ⚠ flag; 02-04 eval script computes investigation_required; 02-05 populated document — §2.1 target bursts (5 rows concrete), §5 results table (5 rows), §5a coverage table with ticked ☑ checkboxes, §5b.1 Alpine + §5b.2 Iberian investigation sub-sections per D-14. | ✓ SATISFIED |

**Cross-plan audit:** Every RTC-01/02/03 claim in plan frontmatter is covered by at least one SUMMARY's `requirements-completed` field (or, for 02-02 which omits the field, by the plan's actual artifacts). No orphaned requirements from REQUIREMENTS.md Phase 2 traceability (only RTC-01/02/03 are mapped). No ROADMAP-mapped requirements missing from plans.

**ROADMAP Success Criteria coverage:**
- SC-1: "User runs `make eval-rtc-eu` and the matrix cell reports per-burst PASS/FAIL across 3-5 EU bursts spanning ≥3 regimes ... ≥1 burst of >1000 m relief AND ≥1 burst >55°N" → SATISFIED (structural audit above).
- SC-2: "EU RTC reference-agreement criteria are literally the same constants as N.Am." → SATISFIED (criteria.py thresholds 0.5 / 0.99 unchanged; only INVESTIGATION_TRIGGER entries added).
- SC-3: "CONCLUSIONS_RTC_EU.md finds selected bursts, regime-coverage table, per-burst numerical results, and investigation findings for materially-different RMSE" → SATISFIED (populated document has §2.1, §5, §5a, §5b.1, §5b.2).

### Anti-Patterns Found

Scanned files modified in this phase: `src/subsideo/validation/{matrix_schema,criteria,harness,matrix_writer,__init__}.py`, `run_eval_rtc_eu.py`, `CONCLUSIONS_RTC_EU.md`, `scripts/probe_rtc_eu_candidates.py`, `tests/unit/test_rtc_eu_eval.py`, `tests/unit/test_{matrix_schema,criteria_registry,harness,matrix_writer}.py`.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| run_eval_rtc_eu.py | 221, 236, 585 | `except Exception` | ℹ️ Info | Intentional — D-06 per-burst try/except isolation; each has `# noqa: BLE001` comment and documented purpose (cache inspection / git status fallback / per-burst pipeline failure) |
| run_eval_rtc_eu.py | 336 | TODO(user) | ℹ️ Info | Deferred — comment noting future Claude-drafted placeholder update; but actual BURSTS concrete burst_ids already locked from live probe (per Plan 02-05 Task 1 follow-up commit c3f395a) |
| scripts/probe_rtc_eu_candidates.py | various | `except Exception` | ℹ️ Info | Probe tool; failures print warnings and continue — documented with `# noqa: BLE001 - probe tool, keep going` |
| CONCLUSIONS_RTC_EU.md | 230-234, 248-252 | Evidence bullets marked "(to populate)" | ⚠️ Warning | Expected — D-14 template explicitly leaves evidence bullets for post-investigation populate. Observation + Top Hypotheses are concrete. Trigger + status are concrete. The "(to populate)" bullets are investigation follow-up steps, not Phase 2 closure gaps. |

**No blockers found.** All anti-patterns are either intentional per design or expected follow-up work explicitly documented in CONCLUSIONS §4 "Deferred follow-up" subsections.

### Assessment of Alpine/Fire FAILs (user-flagged context)

The user's request flagged Alpine + Fire FAILs as documented non-blocking findings. Independent cross-check:

**Alpine FAIL (`t066_140413_iw1`, RMSE 1.152 dB > 0.5, r 0.9754 < 0.99):**
- Legitimate high-relief terrain observation: 3796m relief is 3-4× higher than any N.Am. validation burst. N.Am. baseline (0.045 dB) was never tested under this regime.
- CONCLUSIONS §5b.1 has full D-14 sub-section: Observation (25.6× drift vs baseline), 3 concrete hypotheses (steep-relief DEM artefact / SAFE-orbit mismatch / OPERA reference version drift), evidence collection procedure per hypothesis.
- RTC-02 is honoured: the 0.5 dB gate threshold was NOT loosened to accommodate this FAIL; the Alpine burst is correctly marked `status=FAIL` in metrics.json (line 38) and the matrix renders "2 FAIL" explicitly in `3/5 PASS (2 FAIL) ⚠`. No criterion-creep.
- Phase 2 goal is "per-burst PASS/FAIL across 3-5 EU bursts" — an honest FAIL on 1 out of 5 bursts IS a legitimate outcome satisfying the goal (not "all 5 must PASS"). The goal is "proving Phase 1 harness on a low-risk deterministic product" — the harness correctly detected the drift, wrote it to metrics.json, rendered it in the matrix, and populated the investigation sub-section. That is exactly the intended behavior.

**Fire FAIL (`t045_094744_iw3`, upstream opera-rtc Topo solver hang):**
- Documented in CONCLUSIONS §4 Bug 5 with full investigation: reproduced twice (v5 + v6), each killed after 45+ min with no output progress at 98.5% CPU. Root cause: likely opera-rtc bug / isce3 Newton solver non-convergence / MP worker pathology for this specific burst geometry. Same opera-rtc install processes Alpine (steeper relief) + TemperateFlat (similar latitude) successfully, so not a generic env issue.
- Per-burst try/except isolation (D-06) correctly contained the hang; other 4 bursts completed. Metrics.json records the failure with explicit `error` + `traceback` fields (line 142-143). Phase 1 mtime-staleness watchdog confirmed recovering from this failure mode — which is a legitimate verification of Phase 1 infrastructure.
- Phase 2 goal is NOT blocked: RTC-01 constraints (≥3 regimes, ≥1 >1000m relief, ≥1 >55°N) are all satisfied WITHOUT the Fire row — Alpine/Iberian/TemperateFlat provide 3 bursts >1000m relief; Scandinavian provides >55°N coverage. Fire added regime diversity (wildfire terrain) which is still represented structurally in per_burst[4].regime="Fire" even though RTC processing failed.
- CONCLUSIONS §4 Bug 5 documents deferred follow-up options: (a) swap for different Portuguese fire-AOI burst_id, or (b) file upstream bug report. Both are out-of-scope for Phase 2 closure per RTC-01 (Fire is not a mandatory constraint).

**Conclusion:** Both FAILs are legitimate non-blocking findings. They represent exactly the kind of honest, measured outcome the milestone's "PASS / honest-FAIL / deferral" philosophy demands. The Phase 2 goal — "per-burst PASS/FAIL documented with investigation when needed" — is achieved by having these FAILs with proper documentation, not subverted by them.

### Human Verification Required

None. All verification can be performed via structural greps + file reads + test-suite invocation as demonstrated above. The user has already provided phase-2-complete checkpoint approval at Plan 02-05 Task 3 per the phase plan's human-verify checkpoint mechanism.

### Gaps Summary

No gaps. Phase 2 goal fully achieved:

- Phase goal from ROADMAP "per-burst PASS/FAIL across 3-5 EU bursts covering ≥3 terrain regimes with ≥1 >1000m relief AND ≥1 >55°N" → **5 bursts processed, 5 regimes covered, 3 bursts >1000m, 1 burst >55°N** — mandatory constraints satisfied with structural margin (3× the minimum relief-coverage bar).
- RTC-01 (per-burst PASS/FAIL ≥3 regimes, mandatory constraints) → verified via metrics.json structural audit.
- RTC-02 (EU criteria identical to N.Am., no tightening) → verified via criteria.py grep + runtime assertion on BINDING threshold unchanged (0.5 / 0.99) and type unchanged (BINDING).
- RTC-03 (CONCLUSIONS populated with bursts / regime coverage / numerical results / investigation findings) → verified via CONCLUSIONS_RTC_EU.md structural grep + cross-reference of 2 flagged bursts (investigation_required=true) to 2 §5b sub-sections.
- All 85 framework tests pass (no regressions in Phase 1 artifacts; new Phase 2 tests validate the extensions).
- Matrix renders correctly: `| RTC | EU | — | 3/5 PASS (2 FAIL) ⚠ |` — the ⚠ glyph correctly signals any_investigation_required=true from metrics.json.
- Alpine FAIL + Fire FAIL are legitimate non-blocking findings per the "honest FAIL or deferral" milestone philosophy; both documented in CONCLUSIONS with investigation sub-section (Alpine) or upstream-bug log (Fire).

**Mode:** Real run (not mock) — meta.json has no `"mock_mode"` marker; real git_sha, real python_version=3.12.13, real 4204s runtime.

---

_Verified: 2026-04-22T23:15:00Z_
_Verifier: Claude (gsd-verifier, Opus 4.7 1M context)_
