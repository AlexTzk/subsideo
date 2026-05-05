---
phase: 11-disp-unwrapper-deramping-candidates
verified: 2026-05-04T02:00:00Z
status: passed
score: 12/12 must-haves verified
overrides_applied: 0
---

# Phase 11: DISP Unwrapper & Deramping Candidates — Verification Report

**Phase Goal:** Evaluate SPURT native and PHASS post-deramping as DISP candidate unwrappers/deramps for both SoCal (vs OPERA DISP-S1) and Bologna (vs EGMS L2a), producing schema-valid candidate evidence in sidecars and the results matrix.
**Verified:** 2026-05-04T02:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every Phase 11 candidate-cell outcome can be represented as PASS, FAIL, or BLOCKER | VERIFIED | `DISPCandidateStatus = Literal["PASS", "FAIL", "BLOCKER"]` at `matrix_schema.py:735`; `DISPCandidateOutcome` uses it at line 796 |
| 2 | BLOCKER outcomes preserve failed_stage, error_summary, evidence_paths, cached_input_valid, and partial_metrics | VERIFIED | Live sidecars confirm: `failed_stage="spurt_unwrap_or_timeseries"` and `failed_stage="deramped_ifg_timeseries_reentry"` with all D-10 fields present |
| 3 | Candidate evidence is additive and does not replace product_quality, reference_agreement, or ramp_attribution | VERIFIED | `DISPCellMetrics.candidate_outcomes` is a new additive field (`default_factory=list`); all three prior fields confirmed at `matrix_schema.py:907/916/924` |
| 4 | User can run SPURT native on both SoCal and Bologna from cached CSLC stacks | VERIFIED | `run_eval_disp.py` and `run_eval_disp_egms.py` each contain a Stage 11 SPURT block calling `run_disp(..., unwrap_method="spurt")`; SPURT ran and produced BLOCKER outcomes (missing `spurt` module / broken pipe) — the candidate path executed |
| 5 | SPURT candidate outputs are isolated from baseline PHASS outputs | VERIFIED | `candidate_output_dir(OUT_DIR, "spurt_native")` returns `OUT_DIR/candidates/spurt_native`; verified at `run_eval_disp.py:1136` and `run_eval_disp_egms.py:1031` |
| 6 | SPURT comparisons continue to call `prepare_for_reference(method=REFERENCE_MULTILOOK_METHOD)` explicitly | VERIFIED | Lines `run_eval_disp.py:1179` and `run_eval_disp_egms.py:1070` both contain `method=REFERENCE_MULTILOOK_METHOD` |
| 7 | PHASS post-deramping subtracts fitted planar ramps from per-IFG unwrapped phases | VERIFIED | `deramp_ifg_stack` at `selfconsistency.py:555` calls `fit_planar_ramp` and subtracts slope_x*xx + slope_y*yy + intercept_rad per IFG; `write_deramped_unwrapped_ifgs` at line 610 applies it to GeoTIFFs |
| 8 | PHASS deramping is validation-only and does not change native production output | VERIFIED | No `deramped_unwrapped_paths` parameter added to `run_disp`; PHASS block reads from existing output dirs and writes only to `candidates/phass_post_deramp/`; confirmed in `disp.py` |
| 9 | SoCal PHASS deramping records a deformation-signal sanity check with flagging thresholds | VERIFIED | `DISPDeformationSanityCheck` constructed for SoCal at `run_eval_disp.py:1385`; flags at `abs(trend_delta) > 3.0` or `abs(stable_residual_delta) > 2.0` confirmed at lines 1373/1376 |
| 10 | The four required candidate-cell outcomes exist: SPURT/SoCal, SPURT/Bologna, PHASS/SoCal, PHASS/Bologna | VERIFIED | Python validation of live sidecars: SoCal pairs == `{('spurt_native','socal'),('phass_post_deramp','socal')}` ✓; Bologna pairs == `{('spurt_native','bologna'),('phass_post_deramp','bologna')}` ✓ |
| 11 | Candidate status appears in matrix compact hints (cand=) without collapsing PQ/RA/ramp-attribution | VERIFIED | `results/matrix.md` lines 13-14 show `cand=spurt:BLOCKER,deramp:BLOCKER*`; `ra_col.*cand=` grep returns 0 lines confirming D-12 enforcement |
| 12 | Candidate evidence from schema-valid sidecars is summarized in both DISP conclusion files with validation-only posture | VERIFIED | `CONCLUSIONS_DISP_N_AM.md:410` and `CONCLUSIONS_DISP_EU.md:458` both contain `## Phase 11 unwrapper and deramping candidates`; both contain `Phase 12 consumes these candidate outcomes to choose production posture` |

**Score:** 12/12 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/subsideo/validation/matrix_schema.py` | Strict Pydantic candidate evidence models on DISPCellMetrics | VERIFIED | `DISPCandidateName`, `DISPCandidateCell`, `DISPCandidateStatus`, `DISPDeformationSanityCheck`, `DISPCandidateOutcome`, `candidate_outcomes` all present; `ConfigDict(extra="forbid")` on new models |
| `src/subsideo/validation/disp_candidates.py` | Shared candidate helper functions | VERIFIED | All three functions present: `candidate_output_dir`, `candidate_status_from_metrics`, `make_candidate_blocker`; SPURT thresholds (0.7, 5.0) and PHASS thresholds (0.5, 1.0) confirmed; no ERA5 axis |
| `tests/validation/test_disp_candidates.py` | Schema/helper regression tests | VERIFIED | File exists; 94 tests reported passing per SUMMARY-03 |
| `src/subsideo/products/disp.py` | Validation-only unwrap-method override preserving PHASS default | VERIFIED | `unwrap_method: Literal["phass", "spurt"] = "phass"` at lines 66 and 441; `UnwrapMethod.SPURT`/`PHASS` mapping at line 110; `ValueError` guard at line 492 |
| `run_eval_disp.py` | SoCal SPURT + PHASS post-deramp candidate blocks | VERIFIED | Both Stage 11 (SPURT) and Stage 12-pre (PHASS) blocks present; `candidate_outcomes` wired into `DISPCellMetrics` |
| `run_eval_disp_egms.py` | Bologna SPURT + PHASS post-deramp candidate blocks | VERIFIED | Same as above with `cell="bologna"` |
| `src/subsideo/validation/selfconsistency.py` | Deramped-IFG writer | VERIFIED | `deramp_ifg_stack` at line 555; `write_deramped_unwrapped_ifgs` at line 610; calls `fit_planar_ramp` |
| `src/subsideo/validation/matrix_writer.py` | Compact `cand=` hints in `_render_disp_cell` | VERIFIED | `cand=` rendering at lines 497-512; short labels `spurt`/`deramp`; `*` suffix for `partial_metrics=True`; no `cand=` in `ra_col` |
| `eval-disp/metrics.json` | SoCal sidecar with candidate_outcomes | VERIFIED | Exactly 2 outcomes: `(spurt_native, socal)` BLOCKER + `(phass_post_deramp, socal)` BLOCKER* |
| `eval-disp-egms/metrics.json` | Bologna sidecar with candidate_outcomes | VERIFIED | Exactly 2 outcomes: `(spurt_native, bologna)` BLOCKER + `(phass_post_deramp, bologna)` BLOCKER* |
| `results/matrix.md` | Compact Phase 11 candidate hints | VERIFIED | Lines 13-14 contain `cand=spurt:BLOCKER,deramp:BLOCKER*` for both DISP rows |
| `CONCLUSIONS_DISP_N_AM.md` | SoCal Phase 11 candidate evidence section | VERIFIED | `## Phase 11 unwrapper and deramping candidates` section at line 410 with table and D-08/D-13/D-14 prose |
| `CONCLUSIONS_DISP_EU.md` | Bologna Phase 11 candidate evidence section | VERIFIED | `## Phase 11 unwrapper and deramping candidates` section at line 458 with table and D-08/D-13/D-14 prose |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `matrix_schema.py` | `matrix_writer.py` | `DISPCandidateOutcome.candidate_outcomes` compact renderer | VERIFIED | `cand=` rendering block reads `m.candidate_outcomes` using short label map |
| `run_eval_disp.py` | `disp_candidates.py` | `candidate_status_from_metrics`, `make_candidate_blocker`, `candidate_output_dir` | VERIFIED | All three imported and called at lines 930-932 |
| `run_eval_disp.py` | `disp.py` | `run_disp(..., unwrap_method="spurt")` | VERIFIED | Line 1145 |
| `run_eval_disp.py` | `compare_disp.py` | `prepare_for_reference(method=REFERENCE_MULTILOOK_METHOD)` | VERIFIED | Line 1179 |
| `run_eval_disp.py` | `selfconsistency.py` | `write_deramped_unwrapped_ifgs` | VERIFIED | Imported at line 1306; used in PHASS block |
| `run_eval_disp.py` | `matrix_schema.py` | `DISPDeformationSanityCheck` in candidate outcome | VERIFIED | Imported at line 1305; `DISPDeformationSanityCheck` constructed at line 1385 |
| `CONCLUSIONS_DISP_N_AM.md` | `eval-disp/metrics.json` | Numbers copied from schema-valid sidecar | VERIFIED | Conclusion table matches live sidecar BLOCKER values; `spurt_native` referenced |
| `CONCLUSIONS_DISP_EU.md` | `eval-disp-egms/metrics.json` | Numbers copied from schema-valid sidecar | VERIFIED | `phass_post_deramp` referenced; values match live sidecar |

---

## Data-Flow Trace (Level 4)

Not applicable — this phase produces research/validation artifacts (JSON sidecars, markdown), not UI components rendering dynamic data from a backend store. The data flow is script-to-file rather than component-to-API.

---

## Behavioral Spot-Checks

| Behavior | Check | Result | Status |
|----------|-------|--------|--------|
| Live sidecars contain exactly 4 candidate-cell outcome pairs | Python dict-set comparison against expected pairs | SoCal: `{('spurt_native','socal'),('phass_post_deramp','socal')}` ✓; Bologna: `{('spurt_native','bologna'),('phass_post_deramp','bologna')}` ✓ | PASS |
| All 4 outcomes are BLOCKER with correct failed_stage | Python read of status and failed_stage fields | SPURT: `failed_stage=spurt_unwrap_or_timeseries`; PHASS: `failed_stage=deramped_ifg_timeseries_reentry`; all status=BLOCKER | PASS |
| `results/matrix.md` contains `cand=` hints in DISP rows | `grep -n "cand=" results/matrix.md` | Two DISP rows both contain `cand=spurt:BLOCKER,deramp:BLOCKER*` | PASS |
| `cand=` text absent from `ra_col` path in matrix_writer | `grep -c "ra_col.*cand=" matrix_writer.py` | 0 lines — D-12 enforced | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DISP-07 | 11-01, 11-03, 11-04, 11-05 | PHASS post-deramping candidate without changing native 5x10m output | SATISFIED | `write_deramped_unwrapped_ifgs` in `selfconsistency.py`; PHASS BLOCKER in both sidecars; conclusions document IFG-level deramping |
| DISP-08 | 11-01, 11-02, 11-04, 11-05 | At least one alternative unwrapper candidate with structured failure capture | SATISFIED | SPURT native wired in both eval scripts; BLOCKER outcomes with `failed_stage`, `error_summary`, `evidence_paths`, `cached_input_valid` in live sidecars |
| DISP-09 | 11-01, 11-02, 11-03, 11-04, 11-05 | Candidate comparison using `prepare_for_reference(method=...)` with PQ/RA/ramp-attribution separate | SATISFIED | `method=REFERENCE_MULTILOOK_METHOD` at callsites in both scripts; `cand=` hints in PQ column only; RA column unchanged |

All three requirements declared in plan frontmatter are satisfied. No orphaned requirements: REQUIREMENTS.md traceability table maps DISP-07, DISP-08, DISP-09 exclusively to Phase 11.

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `eval-disp/metrics.json`, `eval-disp-egms/metrics.json` | All 4 outcomes are BLOCKER (SPURT not installed; PHASS has no dolphin re-entry API) | Info | This is the correct experimental result, not a stub. BLOCKER with full D-10 evidence fields is the specified outcome for these failure modes. No impact on schema validity or phase goal. |

No blockers, stubs, or placeholder anti-patterns found. The BLOCKER outcomes are real experimental results with structured evidence, explicitly required by D-09 and D-10.

---

## Human Verification Required

None — all must-haves are verifiable from the codebase and live artifacts. The BLOCKER outcomes are the expected scientific result (SPURT not installed in conda env; no public dolphin API for deramped-IFG time-series re-entry), and phase success is defined as producing schema-valid candidate evidence, not as achieving PASS statuses.

---

## Gaps Summary

No gaps. All 12 must-have truths verified. All 13 required artifacts exist and are substantive. All key links confirmed wired. Requirements DISP-07, DISP-08, DISP-09 satisfied. Phase goal achieved.

---

_Verified: 2026-05-04T02:00:00Z_
_Verifier: Claude (gsd-verifier)_
