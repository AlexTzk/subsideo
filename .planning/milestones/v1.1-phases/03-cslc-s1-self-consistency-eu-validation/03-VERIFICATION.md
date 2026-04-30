---
phase: 03-cslc-s1-self-consistency-eu-validation
phase_number: 03
phase_goal: "Users can run SoCal + Mojave + Iberian Meseta CSLC evals and obtain product-quality numbers (self-consistency coherence + residual mean velocity on stable terrain) that do not depend on cross-version phase comparison, plus OPERA CSLC amplitude reference-agreement as a sanity check reported separately, with the cross-version phase impossibility consolidated into methodology documentation."
verification_date: 2026-04-24
re_verification: true
previous_status: partial
previous_score: "10/17 verified, 1 partial, 4 deferred-by-user-decision (pre-deferral baseline; the 03-VERIFICATION.md text-summary 12/17 conflated 'roadmap-track verified' rows with must-have rows — see Re-verification metadata below for the canonical recount)"
status: passed
must_haves_verified: 16
must_haves_total: 18
must_haves_partial: 1
must_haves_failed: 1
requirements: [CSLC-03, CSLC-04, CSLC-05, CSLC-06]
execution_mode: agent_re_verification_after_user_compute
verifier_agent_skipped: false
re_verification_notes:
  gaps_closed:
    - "must_have #15: NAM compute landed (eval-cslc-selfconsist-nam/{metrics.json, meta.json, sanity/, output/} populated; cell_status=CALIBRATING 2/2; CONCLUSIONS_CSLC_SELFCONSIST_NAM.md committed in f6d5492)"
    - "must_have #16: EU compute landed (eval-cslc-selfconsist-eu/{metrics.json, meta.json, sanity/, output/} populated; cell_status=CALIBRATING 1/1; CONCLUSIONS_CSLC_SELFCONSIST_EU.md committed in f6d5492)"
    - "must_have #17: docs/validation_methodology.md §1 + §2 landed (commits 5e1dcc0/5cef9dc/9009189); both CONCLUSIONS docs cross-linked; compare_cslc.py module header retargeted; 12/12 regression tests pass"
  gaps_remaining:
    - "must_have #14: test_env07_diff_discipline still FAIL — pre-existing code-discipline test (not introduced by 03-05); 723 unclassified hunks between NAM/EU scripts; not a functional defect"
    - "must_have #18 (NEW): test_iberian_aoi_fallback_chain_two_entries FAIL — stale test from 03-04 Task 1 made obsolete by Bug 2 fix in commit 2b59ad6 (probe shipped invalid Alentejo + MassifCentral burst IDs; chain explicitly disabled with fallback_chain=()); not a Phase 3 regression"
  regressions: []
  human_sign_off_required:
    - "CONCLUSIONS_CSLC_SELFCONSIST_NAM.md scientific narrative — verifier confirms structure + metric tables match metrics.json; cannot programmatically verify scientific validity of the SoCal sparse-mask interpretation (486 valid CSLC pixels; coast_buffer_m unit bug noted in §8 follow-up #2)"
    - "CONCLUSIONS_CSLC_SELFCONSIST_EU.md scientific narrative — verifier confirms structure + metric tables match metrics.json; cannot programmatically verify Iberian/Meseta-North persistent_frac=92.3% interpretation against ground truth"
gaps: []
deferred:
  - truth: "Iberian/Alentejo + Iberian/Massif Central fallback re-derivation"
    addressed_in: "Follow-up to Phase 3 (re-run probe per CONCLUSIONS_CSLC_SELFCONSIST_EU.md §8 #1)"
    evidence: "CONCLUSIONS EU §4 Bug 2 documents probe-shipped invalid burst IDs (Alentejo bbox in New Zealand; MassifCentral bbox in Arctic Norway); fix is asf-search + footprint-intersection burst re-derivation, deferred to follow-up"
  - truth: "EGMS L2a stable-PS residual third number for Iberian"
    addressed_in: "Follow-up to Phase 3 (per CONCLUSIONS_CSLC_SELFCONSIST_EU.md §8 #2)"
    evidence: "CONCLUSIONS EU §4 Bug 8 documents EGMStoolkit upstream packaging + class-API drift; script's try/except logs failure and continues; egms_l2a_stable_ps_residual_mm_yr is null in metrics.json"
human_verification:
  - test: "Read CONCLUSIONS_CSLC_SELFCONSIST_NAM.md §5–§8 and confirm SoCal sparse stable-mask interpretation (486 valid CSLC pixels, persistent_frac=2.5%, coh_med_of_persistent=0.887) is the honest reading."
    expected: "Sign off that the SoCal coherence number is the right metric on the right pixel population given coast_buffer_m unit bug (§8 follow-up #2). Confirm the CALIBRATING (not PASS/FAIL) verdict per Phase 3 D-03 first-rollout discipline."
    why_human: "Scientific validity of metric-on-sparse-mask cannot be verified programmatically; requires human SAR/InSAR judgment of whether 486 valid CSLC pixels yields a robust calibration data point for Phase 4 threshold setting."
  - test: "Read CONCLUSIONS_CSLC_SELFCONSIST_EU.md §5–§8 and confirm Iberian/Meseta-North 92.3% persistent_frac + 0.347 mm/yr residual + 0.891 median_of_persistent is plausible for bare/sparse-vegetation steppe over 6 months."
    expected: "Sign off that Iberian numbers are physically plausible. Note that EGMS L2a third number is deferred (Bug 8) — accept that the rollout reports (a)+(b) of the three-number schema and (c) is null."
    why_human: "Domain expert judgment of whether 92.3% persistent_frac is unusually high (yes, per CONCLUSIONS) but consistent with Iberian Meseta phenology; verifier cannot determine 'plausible'."
  - test: "Inspect eval-cslc-selfconsist-{nam,eu}/sanity/<aoi>/coherence_histogram.png and stable_mask_over_basemap.png for each AOI (SoCal, Mojave/Coso-Searles, Iberian)."
    expected: "Confirm no bimodal P2.1 contamination in any histogram (CONCLUSIONS NAM §5.3 + EU §5.3 claim unimodal). Confirm stable masks visually fall on actual stable terrain (bedrock + steppe) and not on dunes or playas."
    why_human: "PNG histogram + georeferenced mask basemap inspection requires visual judgment; not programmatically verifiable."
  - test: "Decide whether to proceed to Phase 4 with two outstanding follow-ups deferred (Iberian fallback re-derivation; EGMS L2a third-number adapter)."
    expected: "User accepts deferred follow-ups as Phase 3 sign-off conditions OR schedules them as gap-closure work. CONCLUSIONS_CSLC_SELFCONSIST_EU.md §8 #1 + #2 list these explicitly."
    why_human: "Scope decision — neither follow-up is a Phase 3 contractual must-have; both are recommendations from the rollout."
human_sign_off_completed:
  date: 2026-04-29
  aoi_assessments:
    - aoi: "Mojave/Coso-Searles"
      verdict: "scientifically convincing candidate-threshold PASS"
      rationale: "Large stable-pixel sample, strong coherence, low residual velocity"
    - aoi: "Iberian/Meseta-North"
      verdict: "scientifically convincing candidate-threshold PASS"
      rationale: "Large stable-pixel sample, strong coherence, low residual velocity"
    - aoi: "SoCal"
      verdict: "inconclusive — not PASS, not FAIL"
      note: "486 valid CSLC pixels; gate statistic driven by ~12 persistently coherent pixels; sample too small for robust judgment; CALIBRATING verdict accepted"
  png_inspection: "no bimodal P2.1 contamination detected; stable masks confirmed on actual stable terrain (bedrock + steppe)"
  deferred_accepted:
    - "Iberian Alentejo + MassifCentral fallback re-derivation (CONCLUSIONS EU §8 #1)"
    - "EGMS L2a stable-PS residual third-number adapter (CONCLUSIONS EU §8 #2)"
tags: [verification, post-deferral, human-sign-off-complete, calibrating-rollout, methodology-consolidated]
---

# Phase 03 Verification — CSLC-S1 Self-Consistency + EU Validation

## Status: passed — human sign-off recorded 2026-04-29

Phase 3 plans 03-01 through 03-05 are now all in a closed-loop state on disk:

- **Wave 1** (03-01 + 03-02): scaffolding + AOI probe + lock-in — VERIFIED.
- **Wave 2 Task 1** (03-03 + 03-04): eval scripts + 19 NAM + 22 EU static-invariant tests — VERIFIED (with 1 pre-existing PARTIAL + 1 newly stale FAIL noted below).
- **Wave 2 Task 2** (03-03 + 03-04 compute): user ran `make eval-cslc-{nam,eu}`; both cells produced metrics.json + sanity artifacts + CONCLUSIONS — VERIFIED.
- **Wave 3** (03-05 methodology doc + cross-link retargets): all three commits landed (5e1dcc0/5cef9dc/9009189); 12/12 regression tests green — VERIFIED.

The remaining open items are scientific-narrative sign-off (cannot verify programmatically) and two deferred follow-ups (Iberian Alentejo+MassifCentral fallback re-derivation; EGMS L2a third-number adapter) that are explicitly out-of-scope for Phase 3 contractual closure — both are documented in CONCLUSIONS_CSLC_SELFCONSIST_EU.md §8 with named follow-up paths.

## Post-deferral completion (this re-verification's net new findings)

This section documents the resolution of the four items the previous VERIFICATION.md (2026-04-24, pre-compute) marked as DEFERRED to user.

### 1. NAM compute (must_have #15) — VERIFIED

User ran `make eval-cslc-nam`; cell completed with `cell_status=CALIBRATING, 2/2 PASS, no BLOCKERs`. Evidence on disk:

| Artifact | Path | Status |
|----------|------|--------|
| Per-AOI + cell aggregate metrics | `eval-cslc-selfconsist-nam/metrics.json` | EXISTS, 5025 bytes, schema_version=1 |
| Run provenance (git_sha, hashes) | `eval-cslc-selfconsist-nam/meta.json` | EXISTS, git_sha=`61d4339b...`, 30 input hashes |
| SoCal sanity (P2.1 mitigation) | `eval-cslc-selfconsist-nam/sanity/SoCal/{coherence_histogram.png, mask_metadata.json, stable_mask_over_basemap.png}` | EXISTS (3 files; PNG ~22 KB + ~22 KB; mask metadata: n_stable=486) |
| Mojave/Coso-Searles sanity | `eval-cslc-selfconsist-nam/sanity/Mojave/Coso-Searles/{coherence_histogram.png, mask_metadata.json, stable_mask_over_basemap.png}` | EXISTS (3 files) |
| Compass CSLC outputs | `eval-cslc-selfconsist-nam/output/{SoCal,Mojave}/<burst_id>/<YYYYMMDD>/<...>.h5` | EXISTS (30 files) |
| Three-number schema (NAM) | `metrics.json` per_aoi rows | VERIFIED — `coherence_median_of_persistent` (SoCal=0.887, Mojave=0.804) + `residual_mm_yr` (SoCal=−0.109, Mojave=+1.127) + `amp_r/amp_rmse_db` (SoCal=0.982/1.290 dB; Mojave amp not run per D-07) |
| `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` | repo root | EXISTS, 233 lines, §1–§8 narrative complete; §5.4 methodology cross-links present (added by 03-05) |

Both AOIs gate-positive on the candidate Phase 4 thresholds (coh ≥ 0.7 by 10%+ headroom; |residual| ≤ 3.0 mm/yr by 2.7×+ headroom). 11 fix commits (Bugs 1–11 in CONCLUSIONS §4) landed during the iterative debug pass; the original deferral note about "12h cold, ~48h worst-case Mojave fallback" became 78 minutes (run_duration_s=4691) once Bugs 9a/9b/9c (NaN-propagation + grid-mismatch) were resolved.

### 2. EU compute (must_have #16) — VERIFIED

User ran `make eval-cslc-eu`; cell completed with `cell_status=CALIBRATING, 1/1 PASS, no BLOCKERs`. Evidence on disk:

| Artifact | Path | Status |
|----------|------|--------|
| Per-AOI + cell aggregate metrics | `eval-cslc-selfconsist-eu/metrics.json` | EXISTS, 2209 bytes, schema_version=1 |
| Run provenance | `eval-cslc-selfconsist-eu/meta.json` | EXISTS, git_sha=`f581095b...`, 15 input hashes; run_duration_s=4386 (73 min) |
| Iberian sanity | `eval-cslc-selfconsist-eu/sanity/Iberian/{coherence_histogram.png, mask_metadata.json, stable_mask_over_basemap.png}` | EXISTS (3 files; ~38 KB + ~83 KB) |
| Compass CSLC outputs | `eval-cslc-selfconsist-eu/output/Iberian/t103_219329_iw1/<YYYYMMDD>/<...>.h5` | EXISTS (15 files) |
| Three-number schema (EU) | `metrics.json` per_aoi.Iberian | VERIFIED row (a)/(b)/(c) — (a) `amp_r=0.0` (n/a; OPERA L2 CSLC-S1 V1 is N.Am.-only, by design) + (b) `coherence_median_of_persistent=0.868` (Iberian) + (c) `residual_mm_yr=+0.347` and `egms_l2a_stable_ps_residual_mm_yr` null (EGMS deferred per Bug 8) |
| `CONCLUSIONS_CSLC_SELFCONSIST_EU.md` | repo root | EXISTS, 243 lines, §1–§8 narrative complete; §5.5 methodology cross-links present (added by 03-05) |

Iberian is gate-positive on coh by 24% headroom (0.868 vs 0.7) and on residual by 8.6× headroom (0.347 vs 3.0 mm/yr). Iberian is the cleanest of the three Phase 3 AOIs by every metric.

8 EU-specific bug fixes landed (Bugs 1–8 in CONCLUSIONS §4); two are explicitly deferred follow-ups (Bug 2: Alentejo+MassifCentral burst-ID re-derivation; Bug 8: EGMStoolkit class-API adapter). Both follow-ups are documented in §8 with named resolution paths and are tracked under `deferred` in this VERIFICATION's frontmatter.

### 3. Methodology doc + retargets (must_have #17) — VERIFIED

03-05 plan executed across three commits (5e1dcc0 RED → 5cef9dc GREEN → 9009189 doc). Evidence:

| Artifact | Path | Verification |
|----------|------|--------------|
| `docs/validation_methodology.md` | repo root | EXISTS, 247 lines (>120 min); §1 (CSLC cross-version phase impossibility) + §2 (Product-quality vs reference-agreement distinction); NO §3/§4/§5 stubs (D-15 append-only); §1 leads with structural SLC-interpolation-kernel argument before diagnostic-evidence appendix (PITFALLS P2.4 ordering) |
| Test regression guard | `tests/unit/test_validation_methodology_doc.py` | 12 tests; **12/12 PASS** verified by `python -m pytest tests/unit/test_validation_methodology_doc.py -v`; covers section presence, ordering, isce3 upstream cite, no stubs, NAM+EU CONCLUSIONS cross-link presence, compare_cslc.py docstring cross-link presence, no orphan TBD/TODO/STUB |
| `compare_cslc.py` module-header docstring | `src/subsideo/validation/compare_cslc.py:1-26` | UPDATED — header now contains `docs/validation_methodology.md#cross-version-phase` cross-link with explicit "Before adding any phase-correction branch" warning |
| NAM CONCLUSIONS cross-link | `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` §5.4 | VERIFIED — section now cites `docs/validation_methodology.md#cross-version-phase` and `docs/validation_methodology.md#2-product-quality-vs-reference-agreement-distinction`; no `Plan 03-05 pending` placeholder |
| EU CONCLUSIONS cross-link | `CONCLUSIONS_CSLC_SELFCONSIST_EU.md` §5.5 | VERIFIED — same anchor cross-links; §5.5 contains the three-number motivating-example pointer to methodology §2.2 |

Plan 03-05 also resolved a documented filename discrepancy (plan literal said `CONCLUSIONS_CSLC_EU.md`; on-disk file is `CONCLUSIONS_CSLC_SELFCONSIST_EU.md`) — the methodology doc cites both names in §2.2 and the regression test accepts either.

### 4. Pre-existing code-discipline failure (must_have #14) — STILL PARTIAL

`test_env07_diff_discipline` continues to fail. Detail:

- Pre-existing in the 2026-04-24 (pre-compute) VERIFICATION.md as "1 known failure, code discipline only"
- Re-confirmed today: 723 unclassified hunks between `run_eval_cslc_selfconsist_nam.py` and `run_eval_cslc_selfconsist_eu.py` (the previous VERIFICATION reported 731; the 8-line decrement is due to landed bug fixes since then)
- Functional behavior is correct in both scripts; this is a code-organization mismatch from the parallel-worktree authoring of Plan 03-03 vs 03-04
- Resolution path: align scripts structurally OR relax the regex OR factor a shared helper module — explicitly NOT a Phase 3 must-have closure

### 5. Newly stale test (must_have #18, NEW this re-verification) — FAIL

`test_iberian_aoi_fallback_chain_two_entries` fails today. Root cause: stale test, not regression.

- The test asserts `IberianAOI.fallback_chain=_IBERIAN_FALLBACKS` is wired in the EU script (originally written when the 03-02 probe was assumed correct).
- Bug 2 in CONCLUSIONS_CSLC_SELFCONSIST_EU.md §4 documents that the probe shipped invalid burst IDs for Alentejo (bbox in New Zealand) and Massif Central (bbox in Arctic Norway).
- Fix commit `2b59ad6` set `fallback_chain=()` to disable the broken chain; `_IBERIAN_FALLBACKS` is still defined as a 2-entry tuple (per the test) but is no longer wired to the AOI.
- Re-derivation of correct Alentejo + MassifCentral burst IDs is documented as a follow-up (CONCLUSIONS §8 #1).
- This test was NOT introduced by Plan 03-05's three commits; it fails because of the legitimate Bug 2 fix from 2b59ad6.
- Status: pre-existing carryover after Bug 2 fix — should be relaxed to accept `fallback_chain=()` as the documented post-Bug-2 state.

## What Was Done — full historical record (preserved from initial verification)

### Wave 1 — Foundation (complete)

**Plan 03-01 — Scaffolding** (5/5 tasks, all tests green):
- `src/subsideo/validation/selfconsistency.py` — extended `coherence_stats` to 6-key dict including `median_of_persistent` (P2.2 robust gate, immune to bimodal dune/playa contamination); `compute_residual_velocity` shipped as working implementation (merge-resolved during Wave 2 merge)
- `src/subsideo/validation/criteria.py` — `Criterion` dataclass carries `gate_metric_key` field; CSLC CALIBRATING entries tagged `median_of_persistent`
- `src/subsideo/validation/matrix_schema.py` — `AOIResult` + `CSLCSelfConsistNAMCellMetrics` + `CSLCSelfConsistEUCellMetrics` Pydantic types; `cell_status ∈ {PASS, FAIL, CALIBRATING, MIXED, BLOCKER}`
- `src/subsideo/validation/matrix_writer.py` — `cslc:nam` + `cslc:eu` render branches (CALIBRATING italics + U+26A0 glyph for any BLOCKER in per_aoi)
- `src/subsideo/validation/compare_cslc.py::compare_cslc_egms_l2a_residual` — D-12 signature shipped
- `src/subsideo/data/worldcover.py::fetch_worldcover_class60` — ESA WorldCover s3://esa-worldcover/v200/2021/ fetch
- `src/subsideo/data/natural_earth.py::load_coastline_and_waterbodies` — returns geometries usable by `stable_terrain.build_stable_mask`
- `Makefile` — `eval-cslc-nam` + `eval-cslc-eu` targets wired to supervisor
- `results/matrix_manifest.yml` — `cslc:nam` + `cslc:eu` entries point to new cache dirs
- `pyproject.toml [project.optional-dependencies.dev]` — adds `naturalearth` and `EGMStoolkit==0.2.15` (BLOCKER 5: two-layer install discipline satisfied)

**Plan 03-02 — AOI probe + lock-in** (3/3 tasks; Task 3 checkpoint resolved `lgtm-proceed`):
- `scripts/probe_cslc_aoi_candidates.py` — full probe script with coverage + stability + sensing-window derivation
- `.planning/milestones/v1.1-research/cslc_selfconsist_aoi_candidates.md` — 7 candidate burst IDs (4 Mojave fallback chain + 3 Iberian), SoCal 15-epoch sensing window, Mojave fallback ordering by probe score (Coso 302.40 > Amargosa 224.75 > Hualapai 141.20 > Pahranagat 135.30), user review checklist, query reproducibility footer
- Task 3 human-verify checkpoint auto-approved per `workflow.auto_advance=true` + explicit user confirmation via orchestrator AskUserQuestion

### Wave 2 — Eval scripts + compute (complete)

**Plan 03-03 — N.Am. CSLC self-consistency** (Tasks 1+2 both complete):
- Task 1: `run_eval_cslc_selfconsist_nam.py` (1061 LOC); `tests/unit/test_run_eval_cslc_selfconsist_nam.py` (19 static-invariant tests, 19/19 PASS)
- Task 2: User-run compute landed `eval-cslc-selfconsist-nam/{metrics.json, meta.json, sanity/, output/}`; 11 bug fixes (commits `08e9175`/`a52c1fb`/`ce4f747`/`fa71c0f`/`d6aebe8`/`633deef`/`caa2b80`/`d76601f`/`7cf4fab`/`c9b8f34`/`61d4339`/`f581095`); CONCLUSIONS_CSLC_SELFCONSIST_NAM.md committed in `f6d5492`

**Plan 03-04 — EU CSLC self-consistency** (Tasks 1+2 both complete):
- Task 1: `run_eval_cslc_selfconsist_eu.py` (923 LOC); `tests/unit/test_run_eval_cslc_selfconsist_eu.py` (22 static-invariant tests, 20/22 PASS — see #14 + #18 below)
- Task 2: User-run compute landed `eval-cslc-selfconsist-eu/{metrics.json, meta.json, sanity/, output/}`; 8 EU-specific bug fixes (commits `f02b121`/`2b59ad6`/`5f4218b`/`18df6f1`/`04bf1be`/`f581095`); CONCLUSIONS_CSLC_SELFCONSIST_EU.md committed in `f6d5492`; two follow-ups deferred (Iberian fallback re-derivation; EGMS L2a third-number adapter)

### Wave 3 — Methodology consolidation (complete)

**Plan 03-05 — `docs/validation_methodology.md`** (3 commits):
- `5e1dcc0` (RED): regression-guard test scaffolding (12 tests, all RED)
- `5cef9dc` (GREEN): `docs/validation_methodology.md` §1+§2 (247 lines) + `compare_cslc.py` docstring expansion + NAM/EU CONCLUSIONS cross-link sub-sections
- `9009189` (DOCS): plan completion summary
- 12/12 tests now pass; ruff check + format clean on touched files

### Automated Checks

| Check | Result | Detail |
|-------|--------|--------|
| Ruff lint (10 Phase 3 files) | PASS | All checks passed (per 03-05 SUMMARY.md verification) |
| Phase 3 unit tests | 51/53 PASS (2 fail) | `test_run_eval_cslc_selfconsist_nam.py`: 19/19 PASS; `test_run_eval_cslc_selfconsist_eu.py`: 20/22 PASS (2 fail: env07_diff_discipline + iberian_fallback_chain — both pre-existing or stale, not new); `test_validation_methodology_doc.py`: 12/12 PASS |
| Full unit suite (post-resolution) | 428/436 PASS (8 fail) | 6 pre-existing failures from before Phase 3 (test_compare_dswx, test_disp_pipeline, test_metadata_wiring, test_orbits) + 2 EU script tests (#14 PARTIAL + #18 stale) |
| Three-number schema (NAM) | VERIFIED | `eval-cslc-selfconsist-nam/metrics.json` per_aoi rows contain `coherence_median_of_persistent` + `residual_mm_yr` + `amp_r/amp_rmse_db` (SoCal only — Mojave amp `run_amplitude_sanity=False` per D-07 design) |
| Three-number schema (EU) | VERIFIED row (a)+(b); (c) deferred | `eval-cslc-selfconsist-eu/metrics.json` per_aoi.Iberian: (b) coherence_median_of_persistent=0.868; (c) residual_mm_yr=+0.347; (a) amp_r/amp_rmse_db=0.0 (n/a — OPERA L2 V1 is N.Am.-only by design); EGMS L2a third part of (c) is null (Bug 8 follow-up) |
| Methodology doc presence | VERIFIED | `docs/validation_methodology.md` 247 lines; §1 + §2 present; no §3/§4/§5 stubs; structural argument leads diagnostic evidence; isce3 upstream cite present; "Do NOT re-attempt with additional corrections" present |
| CONCLUSIONS cross-links | VERIFIED | Both CONCLUSIONS docs reference `docs/validation_methodology.md`; no `Plan 03-05 pending` placeholder remains; test_conclusions_cross_links_retargeted PASSES |
| compare_cslc.py header retarget | VERIFIED | Module-header docstring (lines 1-26) contains `docs/validation_methodology.md#cross-version-phase` cross-link; test_compare_cslc_header_references_doc PASSES |
| Probe artifact schema (Wave 1) | VERIFIED | 7 candidate rows + SoCal 15-epoch section + Mojave ordering + checklist + footer |

## Must-Haves Summary Table (re-verified)

| # | Must-Have | Source | Previous Status | Current Status | Notes |
|---|-----------|--------|-----------------|----------------|-------|
| 1 | `coherence_stats` returns 6-key dict with `median_of_persistent` | 03-01 | VERIFIED | VERIFIED | Regression check |
| 2 | `criteria.Criterion` carries `gate_metric_key`; CSLC entries tagged | 03-01 | VERIFIED | VERIFIED | Regression check |
| 3 | `matrix_schema` defines `AOIResult`, `CSLCSelfConsist{NAM,EU}CellMetrics` | 03-01 | VERIFIED | VERIFIED | Regression check |
| 4 | `matrix_writer` renders CALIBRATING italics + U+26A0 on BLOCKER | 03-01 | VERIFIED | VERIFIED | Regression check |
| 5 | `compare_cslc_egms_l2a_residual` exists with D-12 signature | 03-01 | VERIFIED | VERIFIED | Regression check |
| 6 | `data/worldcover.fetch_worldcover_class60` exists | 03-01 | VERIFIED | VERIFIED | Regression check |
| 7 | `data/natural_earth.load_coastline_and_waterbodies` exists | 03-01 | VERIFIED | VERIFIED | Regression check |
| 8 | Makefile `eval-cslc-nam` + `eval-cslc-eu` targets wired | 03-01 | VERIFIED | VERIFIED | User invoked both this session |
| 9 | `matrix_manifest.yml` cslc entries updated | 03-01 | VERIFIED | VERIFIED | Regression check |
| 10 | `pyproject.toml [dev]` extras include naturalearth + EGMStoolkit | 03-01 | VERIFIED | VERIFIED | Regression check |
| 11 | Probe artifact with 7 candidate rows + SoCal window + Mojave ordering | 03-02 | VERIFIED | VERIFIED | Regression check (note: probe was found to ship invalid bursts for Alentejo/MassifCentral — Bug 2; primary AOIs valid) |
| 12 | 03-02 Task 3 checkpoint resolved `lgtm-proceed` | 03-02 | VERIFIED | VERIFIED | Regression check |
| 13 | `run_eval_cslc_selfconsist_nam.py` + 19 static tests green | 03-03 T1 | VERIFIED | VERIFIED | 19/19 PASS confirmed today |
| 14 | `run_eval_cslc_selfconsist_eu.py` + tests green | 03-04 T1 | PARTIAL (test_env07 FAIL) | PARTIAL (test_env07 FAIL — 723 hunks; pre-existing code-discipline) | Same status as previous; not addressed by 03-05 |
| 15 | `make eval-cslc-nam` produces metrics.json + sanity + CONCLUSIONS | 03-03 T2 | DEFERRED | **VERIFIED** | metrics.json populated; sanity/<aoi>/{histogram, mask_metadata, basemap}; CONCLUSIONS_CSLC_SELFCONSIST_NAM.md committed in f6d5492 |
| 16 | `make eval-cslc-eu` produces metrics.json + sanity + CONCLUSIONS | 03-04 T2 | DEFERRED | **VERIFIED** | metrics.json populated; sanity/Iberian/{histogram, mask_metadata, basemap}; CONCLUSIONS_CSLC_SELFCONSIST_EU.md committed in f6d5492 |
| 17 | `docs/validation_methodology.md` §1+§2 + CONCLUSIONS cross-link retargets | 03-05 | DEFERRED | **VERIFIED** | doc 247 lines; 12/12 regression tests PASS; both CONCLUSIONS docs cross-linked; compare_cslc.py header cross-linked |
| 18 | `test_iberian_aoi_fallback_chain_two_entries` passes (NEW — surfaced this re-verification) | 03-04 T1 (post Bug 2) | n/a | **FAIL** (stale test) | Test asserts `fallback_chain=_IBERIAN_FALLBACKS`; Bug 2 fix `2b59ad6` set `fallback_chain=()` because probe shipped invalid Alentejo + MassifCentral burst IDs. Test should be relaxed to accept post-Bug-2 state. Not a Phase 3 regression — fix-commit-driven staleness |

**Score: 16/18 VERIFIED, 1 PARTIAL (#14), 1 FAIL (#18 — stale test)**

The two non-VERIFIED rows (#14 + #18) are both code-discipline / test-staleness concerns about `run_eval_cslc_selfconsist_eu.py` — neither blocks Phase 3 contractual closure.

## Roadmap Success Criteria Coverage

| # | Roadmap SC | Status | Evidence |
|---|------------|--------|----------|
| 1 | SoCal self-consistency on `t144_308029_iw1`, 15 dates, 14 IFGs, coh > 0.7 + residual < 5 mm/yr (CSLC-03) | VERIFIED | metrics.json: SoCal coh_med_of_persistent=0.887 (24% above 0.7); residual=−0.109 mm/yr (45× below 5.0); CONCLUSIONS NAM §5.1 |
| 2 | Mojave self-consistency from fallback list OR exhaustion surfaces blocker (CSLC-04) | VERIFIED | metrics.json: Mojave/Coso-Searles (fallback index 1) CALIBRATING; coh_med_of_persistent=0.804 (15% above 0.7); residual=+1.127 mm/yr (4.4× below 5.0); fallback chain successfully short-circuited on first valid fallback per design |
| 3 | Iberian Meseta three-number row (a)/(b)/(c) reported with no `.passed` collapse (CSLC-05) | VERIFIED-with-deferral | metrics.json + CONCLUSIONS EU §5.1: row reports (a) amp_r=0.0 n/a by design (OPERA L2 V1 N.Am.-only) + (b) coh=0.868 + (c) residual=+0.347 mm/yr (EGMS L2a part of (c) is null per Bug 8 follow-up). Three-number SCHEMA is delivered; EGMS data point is documented deferral. CONCLUSIONS narrative explicitly preserves the category framing |
| 4 | `docs/validation_methodology.md` cross-version phase impossibility section + diagnostic evidence (CSLC-06) | VERIFIED | docs/validation_methodology.md §1.1 (kernel argument leads) + §1.3 (carrier/flattening/both → coh ≈ 0.002 evidence appendix); structural argument precedes diagnostic per PITFALLS P2.4; 12/12 regression tests PASS |

## Requirement Coverage (post-completion)

| Requirement | Plans | Previous Status | Current Status | Evidence |
|-------------|-------|-----------------|----------------|----------|
| CSLC-03 | 03-01, 03-03 | Infrastructure ready; compute deferred | **SATISFIED** | SoCal CALIBRATING row in metrics.json + CONCLUSIONS_CSLC_SELFCONSIST_NAM.md §5.1 + amplitude sanity (0.982/1.290 dB) — REQUIREMENTS.md row 180 should advance from "Pending" → "Validated (CALIBRATING)" |
| CSLC-04 | 03-01, 03-02, 03-03 | Infrastructure ready; compute deferred | **SATISFIED** | Mojave/Coso-Searles CALIBRATING row (fallback chain index 1) — first-valid-fallback short-circuit per design; remaining 3 fallbacks unused by design — REQUIREMENTS.md row 181 should advance from "Pending" → "Validated (CALIBRATING)" |
| CSLC-05 | 03-01, 03-02, 03-04 | Infrastructure ready; compute deferred | **SATISFIED-with-deferral** | Iberian/Meseta-North CALIBRATING row with three-number schema delivered (amp not applicable EU; coh=0.868; residual=+0.347; EGMS L2a third-number deferred per Bug 8). Schema separation enforced (`ProductQualityResult`/`ReferenceAgreementResult` types). REQUIREMENTS.md row 182 should advance from "Pending" → "Validated-with-deferral (CALIBRATING; EGMS L2a third number follow-up)" |
| CSLC-06 | 03-05 | Deferred | **VERIFIED** (already shown as "Validated (Plan 03-05)" in REQUIREMENTS.md row 183) | docs/validation_methodology.md committed; 12/12 regression tests PASS |

## Pre-Existing Failure Annotations (NOT introduced by Phase 3)

| Test | Cause | Carryover Source |
|------|-------|------------------|
| `test_compare_dswx::TestJrcTileUrl::test_url_format` | Phase 2 baseline | Pre-Phase-3 HEAD `dbf62ba` |
| `test_compare_dswx::TestBinarizeDswx::test_class_mapping` | Phase 2 baseline | Pre-Phase-3 HEAD `dbf62ba` |
| `test_disp_pipeline::test_run_disp_mocked` | Phase 2 baseline | Pre-Phase-3 HEAD `dbf62ba` |
| `test_disp_pipeline::test_run_disp_qc_warning` | Phase 2 baseline | Pre-Phase-3 HEAD `dbf62ba` |
| `test_metadata_wiring::TestMetadataInjectionInDISP::test_run_disp_calls_inject_opera_metadata` | Phase 2 baseline | Pre-Phase-3 HEAD `dbf62ba` |
| `test_orbits::TestFetchOrbit::test_fallback_to_s1_orbits` | Phase 2 baseline | Pre-Phase-3 HEAD `dbf62ba` |
| `test_run_eval_cslc_selfconsist_eu::test_env07_diff_discipline` | Code-discipline mismatch (parallel-worktree authoring) | 03-04 Task 1 (`52aff66`); pre-existing in previous VERIFICATION |
| `test_run_eval_cslc_selfconsist_eu::test_iberian_aoi_fallback_chain_two_entries` | Stale test post Bug 2 fix | 03-04 fix commit `2b59ad6`; surfaced for first time in this re-verification (test was written assuming valid fallback chain; Bug 2 made fallback chain invalid; test should be relaxed) |

**No new functional regressions introduced by 03-05's three commits.** The 12/12 methodology-doc regression tests all pass; ruff check + format clean on the four files modified by 03-05.

## Outstanding Items (require human decision)

### 1. Scientific narrative sign-off

The CONCLUSIONS_CSLC_SELFCONSIST_{NAM,EU}.md narratives are present and structurally complete; the verifier confirmed the structure but cannot evaluate scientific validity of the SoCal sparse-mask interpretation (486 valid pixels) or the Iberian 92.3% persistent_frac. Both numbers are within plausible ranges per the narratives, but final sign-off is a domain-expert call.

### 2. Visual sanity-artifact inspection

`coherence_histogram.png` and `stable_mask_over_basemap.png` for SoCal, Mojave/Coso-Searles, and Iberian must be visually inspected for:
- Bimodal distribution → P2.1 mask contamination (CONCLUSIONS NAM §5.3 + EU §5.3 claim unimodal; verifier cannot confirm without pixel-level visual judgment)
- Stable mask falling on actual stable terrain (not dunes / playas / water-body fringes)

### 3. Deferral acceptance for two follow-ups

Two named follow-ups documented in CONCLUSIONS_CSLC_SELFCONSIST_EU.md §8 require either acceptance as out-of-scope for Phase 3 OR scheduling as gap-closure work:

- **(a) Iberian Alentejo + MassifCentral fallback re-derivation** (CONCLUSIONS EU §8 #1): probe shipped invalid burst IDs; re-derive via asf-search + footprint-intersection; restore `fallback_chain=(Alentejo, MassifCentral)` once both validated.
- **(b) EGMS L2a third-number adapter** (CONCLUSIONS EU §8 #2): adapt `_fetch_egms_l2a` to EGMStoolkit 0.3.0 class API; re-run cached eval (~5 min) to populate `egms_l2a_stable_ps_residual_mm_yr`.

Neither is a Phase 3 contractual must-have. Both are recommendations from the rollout. The Roadmap §3 SC-3 three-number schema is "delivered" because the SCHEMA is live (rows (a) reference-agreement / (b) coherence / (c) residual+EGMS) and the framing is enforced by code — the EGMS data point inside row (c) being null is documented and expected per Bug 8.

### 4. Pre-existing test failures cleanup

- `test_env07_diff_discipline` (#14) — pre-existing in previous VERIFICATION; structural alignment of NAM/EU scripts OR test-relaxation OR shared-helper-module factoring; not blocking
- `test_iberian_aoi_fallback_chain_two_entries` (#18) — newly stale; should be updated to accept `fallback_chain=()` post-Bug-2; not blocking
- 6 Phase 2 baseline failures (test_compare_dswx, test_disp_pipeline, test_metadata_wiring, test_orbits) — pre-Phase-3; addressed by Phase 4 or Phase 6 follow-up

## Recommendations for Closing Phase 3

1. **Sign off on CONCLUSIONS narratives** (item 1 above) — read both files and confirm metric interpretations match domain expectations.
2. **Visually inspect 6 PNG sanity artifacts** (item 2 above) — confirm no bimodal P2.1 contamination and that masks fall on stable terrain.
3. **Decide on deferred follow-ups** (item 3 above) — accept as out-of-scope for Phase 3 OR schedule via `/gsd-execute-phase 3 --gaps-only` (no actual gaps remain in must-haves; this is purely about closing the two named follow-ups in CONCLUSIONS EU §8).
4. **Update REQUIREMENTS.md** (item 4 below) — flip CSLC-03/04/05 from "Pending" → "Validated (CALIBRATING)" or "Validated-with-deferral" as appropriate. CSLC-06 is already marked "Validated (Plan 03-05)".
5. **Optional cleanup of #14 + #18** — either at the tail of Phase 3 or as a separate housekeeping commit; non-blocking either way.

---

## REQUIREMENTS.md update suggestion (for orchestrator)

```markdown
| CSLC-03 | Phase 3 | Validated (CALIBRATING)              | (was: Pending)
| CSLC-04 | Phase 3 | Validated (CALIBRATING)              | (was: Pending)
| CSLC-05 | Phase 3 | Validated (CALIBRATING; EGMS deferred) | (was: Pending)
| CSLC-06 | Phase 3 | Validated (Plan 03-05)               | (unchanged)
```

---

## Human Sign-Off (2026-04-29)

Visual inspection of all 6 sanity artifacts (`coherence_histogram.png` + `stable_mask_over_basemap.png` for SoCal, Mojave/Coso-Searles, Iberian) and review of CONCLUSIONS_CSLC_SELFCONSIST_{NAM,EU}.md §5–§8 completed by domain expert.

| AOI | Verdict | Notes |
|-----|---------|-------|
| Mojave/Coso-Searles | Scientifically convincing candidate-threshold PASS | Large stable-pixel sample, strong coherence, low residual velocity |
| Iberian/Meseta-North | Scientifically convincing candidate-threshold PASS | Large stable-pixel sample, strong coherence, low residual velocity |
| SoCal | Inconclusive — not PASS, not FAIL | 486 valid CSLC pixels; gate statistic driven by ~12 persistently coherent pixels. Sample too small to support a robust judgment. CALIBRATING verdict stands. |

No bimodal P2.1 contamination detected in any histogram. Stable masks confirmed to fall on actual stable terrain. SoCal CALIBRATING verdict accepted — the 486-pixel limitation is the correct and honest characterization.

Deferred follow-ups accepted as out-of-scope for Phase 3 closure:
- Iberian Alentejo + MassifCentral burst re-derivation (CONCLUSIONS EU §8 #1)
- EGMS L2a stable-PS residual third-number adapter (CONCLUSIONS EU §8 #2)

Phase 3 closure complete.

---

*This VERIFICATION.md re-verifies Phase 3 after the user-deferred Wave 2 Task 2 compute and Wave 3 methodology-doc work landed (commits f6d5492, 5e1dcc0, 5cef9dc, 9009189). The previous "What Was Done" section is preserved verbatim above; the "Post-deferral completion" section documents the resolution of items 15, 16, 17, plus the two carryover/stale tests (#14 + #18). Human sign-off recorded 2026-04-29 — see §Human Sign-Off above.*

*Re-verified: 2026-04-24 (compute); human sign-off: 2026-04-29*
*Re-verifier: Claude (gsd-verifier subagent, post-deferral re-verification mode)*
