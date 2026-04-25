---
phase: 03-cslc-s1-self-consistency-eu-validation
plan: 05
subsystem: validation/methodology-doc
tags: [methodology, documentation, cslc-06, cross-version-phase, product-quality-vs-reference-agreement, calibrating-discipline]
requires:
  - "Phase 3 Plan 03-03 (N.Am. CSLC self-consistency CONCLUSIONS) — provides §1.3 diagnostic-evidence source (CONCLUSIONS_CSLC_N_AM.md §5.3 v1.0 table) and the SoCal `amp_r=0.982/RMSE=1.290 dB` anchor for §2.2/§2.3"
  - "Phase 3 Plan 03-04 (EU CSLC self-consistency CONCLUSIONS) — provides §2.2 motivating example (Iberian Meseta three-number row, t103_219329_iw1)"
  - "Phase 1 D-04 frozen `Criterion` registry — referenced from §2.1, §2.3 and §2.5 for `BINDING`/`CALIBRATING`/`binding_after_milestone` semantics"
  - ".planning/research/PITFALLS.md §P2.4 — structural-argument source for §1.1; §M1–M6 — anti-creep source for §2.3/§2.4/§2.5"
provides:
  - "docs/validation_methodology.md §1 (CSLC cross-version phase impossibility) — the consolidated artifact-level mitigation for the 'subtract everything' anti-pattern; future PRs adding phase-correction branches must address why the kernel argument no longer holds"
  - "docs/validation_methodology.md §2 (Product-quality vs reference-agreement distinction) — the methodology anchor cited from `compare_cslc.py` and from both CSLC CONCLUSIONS docs"
  - "Code-level cross-link from `src/subsideo/validation/compare_cslc.py` module header to docs/validation_methodology.md#cross-version-phase (PITFALLS P2.4 mitigation plan)"
  - "Regression guard `tests/unit/test_validation_methodology_doc.py` — 12 behavior tests asserting section ordering, required sentinel content, no-stub policy, and cross-link presence"
affects:
  - "Phase 4 (DISP) — will append §3 (DISP ramp-attribution methodology) to docs/validation_methodology.md per CONTEXT D-15 append-only"
  - "Phase 5/6 (DSWx, DIST) — will append §4 (DSWE F1 ceiling) and §5 (cross-sensor precision-first framing) per D-15"
  - "Phase 7 REL-03 — will write the top-level ToC + cross-section consistency pass after all 5 sections land"
tech-stack:
  added: []  # documentation + docstring + tests only; no new runtime deps
  patterns:
    - "append-only methodology doc (D-15) — no stub headings for later phases; each phase appends its own section with its own authoritative evidence"
    - "structural-argument-leads-diagnostic-evidence ordering (PITFALLS P2.4) — the kernel argument is §1.1, the carrier/flattening table is §1.3 appendix"
    - "code-level cross-link from compare_cslc.py docstring to the methodology doc anchor — guards against re-attempt PRs"
key-files:
  created:
    - "docs/validation_methodology.md (247 lines, 2095 words; new file under new docs/ directory)"
    - "tests/unit/test_validation_methodology_doc.py (12 behavior tests)"
  modified:
    - "src/subsideo/validation/compare_cslc.py (module-header docstring expanded; no body changes)"
    - "CONCLUSIONS_CSLC_SELFCONSIST_NAM.md (added §5.4 methodology cross-references)"
    - "CONCLUSIONS_CSLC_SELFCONSIST_EU.md (added §5.5 methodology cross-references)"
decisions:
  - "Filename correction: plan frontmatter listed CONCLUSIONS_CSLC_EU.md; on-disk file is CONCLUSIONS_CSLC_SELFCONSIST_EU.md (committed under SELFCONSIST_ prefix in f6d5492). Tests reference the on-disk filename and accept either form so future filename-rename PRs do not break the regression guard."
  - "No `Plan 03-05 pending` placeholder needed to be removed — Plan 03-03/03-04 outputs (recently committed in f6d5492) shipped without it. The cross-link addition is the substantive change; the placeholder check is preserved as a forward-going regression guard."
  - "Test count is 12 (not the plan-estimate 13). The plan listed 13 behavior tests but Test 7 (policy + isce3 citation) was naturally a single test in the implementation. All 13 plan-spec assertions are covered by the 12 tests (some tests validate two related conditions, e.g. test_isce3_upstream_reference covers both 'isce3' literal + the github.com URL)."
metrics:
  duration: 9min
  completed: 2026-04-25
---

# Phase 03 Plan 05: CSLC Self-Consistency EU Validation — Methodology Doc Summary

CSLC-06 deliverable: created `docs/validation_methodology.md` with §1 (CSLC cross-version phase impossibility) and §2 (product-quality vs reference-agreement distinction) per CONTEXT D-13, leading with the structural isce3 SLC-interpolation-kernel argument (PITFALLS P2.4 mitigation) and motivating §2 with the Iberian Meseta three-number row from Plan 03-04. Wired both CSLC CONCLUSIONS docs and `compare_cslc.py` to cross-link the new anchor; landed 12 regression-guard behavior tests.

## Approach

TDD with test-first RED → GREEN.

1. **RED**: wrote `tests/unit/test_validation_methodology_doc.py` with 12 behavior tests covering doc existence + section ordering + structural-argument-leads-diagnostic + policy + isce3 citation + Iberian motivating example + both-direction anti-creep + compare_cslc.py cross-link + CONCLUSIONS cross-links + no-stub-scaffolding + no-orphan-todos. Confirmed all 12 fail against the empty `docs/` directory. Committed as `5e1dcc0`.
2. **GREEN**: created the methodology doc (247 lines, 2095 words) using the plan template as authoritative content, expanded `compare_cslc.py` module-header docstring with PITFALLS-P2.4 cross-link, appended methodology cross-references to both CONCLUSIONS docs, applied ruff format. All 12 tests pass; ruff `check` and `format --check` both clean on the touched files. Committed as `5cef9dc`.

## Section ordering (PITFALLS P2.4 mitigation)

The §1 ordering is load-bearing. The plan and PITFALLS P2.4 both require the **structural argument** (the SLC interpolation kernel changed upstream of any phase-screen correction) to lead, with the diagnostic evidence (carrier/flattening/both removed → coherence ≈ 0.002) appearing in an appendix later. A fresh contributor reading the doc top-to-bottom must hit the kernel argument before they hit the table — otherwise the diagnostic table reads like an enumerated list ("we tried these three; what should we try next?") instead of like exhausted-options evidence corroborating the structural impossibility.

`test_structural_argument_leads_diagnostic_evidence` enforces this by checking that the byte index of the first `"SLC interpolation kernel"` precedes the byte index of the first `"0.0003"` (or `"0.002"` fallback) in the file.

## Plan §1 content map

| §1 sub | Title | Evidence source |
|--------|-------|-----------------|
| §1 TL;DR | Cross-version coherence ≈ 0; amplitude valid; do not re-attempt | PITFALLS P2.4 + CONCLUSIONS_CSLC_N_AM.md §5 |
| §1.1 | Structural argument: SLC interpolation kernel changed | PITFALLS P2.4 (LEAD per D-14) |
| §1.2 | Policy statement: do NOT re-attempt with additional corrections | PITFALLS P2.4 prevention strategy + plan must_haves |
| §1.3 | Diagnostic evidence (Appendix) | CONCLUSIONS_CSLC_N_AM.md §5.3 v1.0 table |
| §1.4 | Acceptable cross-version validation strategies | CONCLUSIONS_CSLC_N_AM.md §5.4 + CONTEXT |

## Plan §2 content map

| §2 sub | Title | Evidence source |
|--------|-------|-----------------|
| §2 TL;DR | Two distinct categories: product-quality vs reference-agreement | CONTEXT D-13 + PITFALLS M2 |
| §2.1 | Definitions table | PITFALLS M2 + Phase 1 D-04 results.py split |
| §2.2 | Iberian Meseta three-number row (motivating example) | CONCLUSIONS_CSLC_SELFCONSIST_EU.md §5.1 |
| §2.3 | Target-creep prevention (M1) — reference-agreement must not be tightened | PITFALLS M1 + RTC-02 explicit clause |
| §2.4 | Goalpost-moving prevention (M4) — product-quality must not be relaxed | PITFALLS M4 + DSWX-07 ML-replacement upgrade-path discipline |
| §2.5 | First-rollout CALIBRATING discipline (M5 + GATE-05) | PITFALLS M5/M6 + Phase 1 D-04 `binding_after_milestone` |
| §2.6 | Cross-reference to deferred sections (D-15) | CONTEXT D-15 |

## isce3 release-notes URL cited in §1

The §1.1 structural argument cites the upstream [isce3 Releases page](https://github.com/isce-framework/isce3/releases) and notes the kernel change is in the 0.15 → 0.19 range. Per the plan's flexible citation guidance ("if the specific release PR is not easily citable, note the version range + link to the release-notes page"), this is the page-level link rather than a pinned PR URL. PITFALLS P2.4 itself flags the precise minor-version pinpoint as LOW confidence and research-deferred (the optional 0.15 vs 0.19 / 0.25.8 vs 0.25.10 / 0.25.10 vs current-latest diagnostic-experiment menu in P2.4 is not milestone-blocking and Phase 3 does not run it).

## Original prose vs PITFALLS P2.4 copy-paste

The §1 narrative is original prose that cites PITFALLS P2.4 by reference (`.planning/research/PITFALLS.md §P2.4`) rather than copy-pasting from it. Specific phrasings inherited verbatim from the plan template (e.g. "regenerating the OPERA CSLC with the newer isce3 kernel, at which point it is just re-running the pipeline") match the PITFALLS P2.4 wording because the plan template was already a paraphrase of P2.4 — keeping a thin layer of paraphrase across the boundaries (PITFALLS → plan → doc) preserves attribution without hiding the source.

The §2 narrative similarly cites PITFALLS M1/M4/M5/M6 by reference rather than copy-pasting; the only verbatim phrases ("must not be tightened", "must not be relaxed") are the technical anchors the regression-guard tests grep for.

## Deviations from Plan

### Filename Correction (documented; no functional deviation)

**Issue:** Plan frontmatter `files_modified` listed `CONCLUSIONS_CSLC_EU.md` but the on-disk file is `CONCLUSIONS_CSLC_SELFCONSIST_EU.md` (committed in f6d5492 under the `SELFCONSIST_` prefix to mirror `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md`).

**Resolution:** Tests reference the real on-disk filename via `CONCLUSIONS_EU = REPO_ROOT / "CONCLUSIONS_CSLC_SELFCONSIST_EU.md"` and the §2.2 motivating-example assertion accepts either filename via `"CONCLUSIONS_CSLC_EU.md" in section_2 or "CONCLUSIONS_CSLC_SELFCONSIST_EU.md" in section_2`. The methodology doc itself cites both names in §2.2: "`CONCLUSIONS_CSLC_SELFCONSIST_EU.md` (also referred to in the Phase 3 plan frontmatter as `CONCLUSIONS_CSLC_EU.md`; both names refer to the same on-disk document under the `SELFCONSIST_` prefix)". This treats the plan literal as a documented filename correction rather than a code deviation.

### `Plan 03-05 pending` placeholder absent on disk (no functional deviation)

**Issue:** Plan must_have asserted that "Both CONCLUSIONS_CSLC_SELFCONSIST_NAM.md and CONCLUSIONS_CSLC_EU.md have their §5 placeholder cross-links retargeted to the real docs/validation_methodology.md sections (no longer 'Plan 03-05 pending')". On inspection, neither doc currently contains the `Plan 03-05 pending` string — Plans 03-03/03-04 (commit f6d5492) shipped the CONCLUSIONS docs with `## 5. Final Validation Results` directly (different schema from the v1.0 `## 5. Cross-version phase comparison impossibility` heading) and never embedded the placeholder.

**Resolution:** The substantive intent (forbid the placeholder, require the cross-link) remains correct as a forward-going guard. `test_conclusions_cross_links_retargeted` retains both assertions: `assert "Plan 03-05 pending" not in text` (vacuously satisfied today; protects against future regressions) and `assert "docs/validation_methodology.md" in text` (the new substantive check). The cross-link was added as new sub-sections §5.4 (NAM) / §5.5 (EU) so it appears alongside the existing `## 5. Final Validation Results` content rather than retargeting an absent placeholder.

### Test count: 12 vs plan-estimate 13 (no functional deviation)

**Issue:** Plan `<behavior>` block listed 13 numbered behavior tests; the implementation lands 12.

**Resolution:** Test 7 in the plan ("policy statement + isce3 citation") naturally splits across two file-checks but tests one composite behavior (§1 contains both the policy phrase and the upstream changelog reference). The implementation uses two separate test functions — `test_policy_statement_present` and `test_isce3_upstream_reference` — and one combined test where the plan listed two parallel checks. All 13 plan-spec assertions are covered by the 12 functions (no plan-spec assertion is dropped); this is a numbering discrepancy, not a behavior gap.

### Pre-existing mypy error on `compare_cslc.py` (out of scope)

**Issue:** `mypy src/subsideo/validation/compare_cslc.py` reports `error: Missing type arguments for generic type "ndarray"` on the `_load_cslc_complex` signature.

**Resolution:** Confirmed pre-existing (reproduces against pre-commit baseline via `git stash`). Out of scope per the deviation rules: my change was a docstring-only edit at lines 1-26; the function signature at line 41 (was 22) was not touched. Logged here for visibility; not fixed.

## Authentication Gates

None — methodology + docstring + tests only; no network calls or credentials touched.

## Verification Results

### Plan success-criteria checks (16/16 OK)

```
test 1:  doc exists                                    OK
test 2:  line count >= 120 (actual: 247)               OK
test 3:  section 1 heading present                     OK
test 4:  section 2 heading present                     OK
test 5:  no §3/§4/§5 stubs                             OK
test 6:  "SLC interpolation kernel" present            OK
test 7:  "Do NOT re-attempt with additional corrections" present  OK
test 8:  github.com/isce-framework/isce3 link present  OK
test 9:  "three independent" phrase in §2              OK
test 10a: "not tighten" present                        OK
test 10b: "not relax" present                          OK
test 11: compare_cslc.py docstring cross-link present  OK
test 12a: NAM CONCLUSIONS cross-link added             OK
test 12b: EU CONCLUSIONS cross-link added              OK
test 13a: NAM no "Plan 03-05 pending"                  OK
test 13b: EU no "Plan 03-05 pending"                   OK
```

### Behavior-test suite (12/12 PASS)

```
tests/unit/test_validation_methodology_doc.py: 12 passed in 0.03s
```

### ruff (clean)

```
ruff check src/subsideo/validation/compare_cslc.py tests/unit/test_validation_methodology_doc.py: All checks passed!
ruff format --check (after auto-format): clean
```

### Sanity checks on related modules (no regression)

```
tests/unit/test_compare_cslc_egms_l2a.py: 6 passed
tests/unit/test_criteria_registry.py:    17 passed
```

## Downstream Commitments (D-15 append-only — Phase 3 owns nothing of these)

| Section | Owner phase | Source evidence required |
|---------|-------------|--------------------------|
| §3 DISP ramp-attribution | Phase 4 | PHASS N.Am./EU re-runs; Phase 4 ADR on the multilook method (FEATURES vs PITFALLS P3.1 tension) |
| §4 DSWE F1 ≈ 0.92 architectural ceiling | Phase 5 or 6 | DSWX-07 named ML-replacement upgrade path + recalibration data |
| §5 Cross-sensor precision-first framing | Phase 5 | OPERA DIST vs EFFIS comparison + DIST-04 priorities |
| Top-level ToC + final consistency pass | Phase 7 REL-03 | All 5 sections present; ToC writes after the last appender lands |

## Confirmation: no Phase 4/5/6/7 stub scaffolding (D-15 hard rule)

`test_no_stub_scaffolding_for_phase_4_5_6_7` asserts that `## 3.`, `## 4.`, and `## 5.` are absent from the doc. Verified green. Phase 3 does not pre-create headings for sections it does not own.

## Commits

- `5e1dcc0` — `test(03-05): add failing regression guard for docs/validation_methodology.md` (RED)
- `5cef9dc` — `feat(03-05): land docs/validation_methodology.md sections 1+2 (CSLC-06)` (GREEN)

(No REFACTOR commit — the GREEN implementation was already at target shape.)

## Self-Check: PASSED

- `docs/validation_methodology.md` exists at the expected path (247 lines, 2095 words).
- `tests/unit/test_validation_methodology_doc.py` exists with 12 tests, all green.
- Both commit hashes (`5e1dcc0`, `5cef9dc`) appear in `git log --oneline`.
- All 5 modified/created files (docs, tests, compare_cslc.py, both CONCLUSIONS) are tracked in the GREEN commit.
- No orphan TBD/TODO/STUB tokens in §1 or §2 (`test_no_orphan_todos_in_section_1_or_2` green).
- No §3/§4/§5 stubs (`test_no_stub_scaffolding_for_phase_4_5_6_7` green).
- ruff check + format clean on the two touched source files.
