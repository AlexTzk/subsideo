---
phase: 12-disp-conclusions-release-readiness
reviewed: 2026-05-06T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - CONCLUSIONS_DISP_EU.md
  - CONCLUSIONS_DISP_N_AM.md
  - docs/validation_methodology.md
  - results/matrix.md
findings:
  critical: 2
  warning: 5
  info: 2
  total: 9
status: issues_found
---

# Phase 12: Code Review Report

**Reviewed:** 2026-05-06
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 12 appended DISP production-posture sections to both conclusions files, added §§9–12 to
`docs/validation_methodology.md`, and updated `results/matrix.md` to v1.2. The narrative
structure is clear and internally logical within each file. However, two cross-file metric
inconsistencies rise to BLOCKER severity: the DISP NAM reference-agreement column in the results
matrix was not updated after Phase 11 ran and still carries Phase 10 ERA5-on numbers rather than
the Phase 11 SPURT baseline, and the N.Am. conclusions file contains a direct copy-paste from the
EU file that attributes `persistent coherence = 0.000` to SoCal — a value that belongs to Bologna
not SoCal. Four additional warnings cover a contradictory section-level self-reference in the
methodology document's own Table of Contents prose, an undocumented narrowing of IFG count
between v1.0 and Phase 4 in the EU conclusions, a version mismatch for EGMStoolkit across files,
and a rounding discrepancy on the EU bias figure. Two info items cover minor style issues.

---

## Critical Issues

### CR-01: DISP NAM reference-agreement column in matrix.md carries stale Phase 10 ERA5-on metrics

**File:** `results/matrix.md:18`

**Issue:** The DISP NAM reference-agreement column reads `0.007 (> 0.92 FAIL) / 55.43 (< 3 FAIL)`.
These figures match exactly the Phase 10 ERA5-on run values (`r=0.0071`, `bias=+55.43 mm/yr`) as
recorded in `CONCLUSIONS_DISP_N_AM.md` under "Phase 10 ERA5 diagnostic" (r=0.0071, bias=+55.4325
mm/yr). However the product-quality column of the same row correctly reflects Phase 11 outcomes
(`spurt:FAIL / deramp:retired`), and `CONCLUSIONS_DISP_N_AM.md` Phase 12 Production Posture
section explicitly states that the named blocker is the SPURT orbit-class ramp on Bologna, whose
metrics are `r=0.003 / bias=+19.89 mm/yr` (SoCal SPURT) — not the ERA5 numbers.

The Phase 11 SPURT baseline metrics for SoCal are: r=0.0027, bias=+19.89 mm/yr (from the
Phase 11 SoCal candidate outcome table in CONCLUSIONS_DISP_N_AM.md). These are the authoritative
numbers for the Phase 11 state of the DISP NAM cell; they were never written back into the matrix.
The ERA5-on run is a diagnostic, not the primary evaluation.

A reader consulting the matrix for the DISP NAM reference-agreement numbers will be shown ERA5-on
diagnostic numbers that are approximately 3× worse on bias than the Phase 11 SPURT baseline (55.43
vs 19.89 mm/yr), creating a materially false impression of the cell's current state.

**Fix:** Update `results/matrix.md` DISP NAM reference-agreement cell to Phase 11 SPURT-baseline
numbers:

```markdown
| DISP | NAM | DEFERRED — spurt:FAIL / deramp:retired / unblock=tophu-SNAPHU+orbital-deramping / interim=spurt-native(caveated) (see CONCLUSIONS_DISP_N_AM.md §Phase12) | 0.003 (> 0.92 FAIL) / 19.89 (< 3 FAIL) |
```

If the intent is to report the "most recent completed" run (Phase 10 ERA5-on), the matrix cell
should explicitly say `[ERA5-on diagnostic]` and cross-reference §8 of the methodology doc to
prevent misreading. Either way the current state is ambiguous and the number set shown does not
match the Phase 11 candidate posture decision in the conclusions file.

---

### CR-02: "persistent coherence is 0.000" incorrectly attributed to SoCal in CONCLUSIONS_DISP_N_AM.md

**File:** `CONCLUSIONS_DISP_N_AM.md` — Phase 10 ERA5 diagnostic section (the "Cause assessment"
narrative paragraph near the end of the Phase 10 section)

**Issue:** The Phase 10 section in `CONCLUSIONS_DISP_N_AM.md` contains this sentence:

> "Product-quality, reference-agreement, and ramp-attribution remain separate evidence streams:
> stable-terrain residual is small (-0.04 mm/yr), but persistent coherence is 0.000 and
> reference agreement still fails."

The claim "persistent coherence is 0.000" is factually wrong for SoCal. Section §11.1 of the same
file shows `coherence_median_of_persistent = 0.8868` (source: `phase3-cached`) with a verdict of
"CALIBRATING (above bar)". The 0.000 figure belongs to Bologna, where the EU file §11.1 reports
`coherence_median_of_persistent = 0.0000` and `persistently_coherent_fraction = 0.000` — a real
signal about Po-plain agricultural coherence.

The N.Am. Phase 10 ERA5 section appears to have been produced by adapting the EU Phase 10 section
without correcting the coherence figure. This is a cross-cell copy-paste error in a measurement
document. A reader auditing the SoCal cell's product-quality evidence stream will find a direct
contradiction between §11.1 (coh=0.887) and the Phase 10 ERA5 section (coh=0.000).

The same sentence structure (same wording, same cadence) appears in `CONCLUSIONS_DISP_EU.md`
Phase 10 ERA5 section:
> "stable-terrain residual is small (+0.14 mm/yr), but persistent coherence is 0.000 and
> reference agreement still fails."

That sentence is correct for the EU file (Bologna coh=0.000). It is incorrect when the same
sentence appears verbatim in the N.Am. file with only the residual sign changed.

**Fix:** Replace the incorrect sentence in `CONCLUSIONS_DISP_N_AM.md` Phase 10 ERA5 diagnostic
"Cause assessment" narrative with a statement that accurately reflects SoCal's coherence:

```markdown
Product-quality, reference-agreement, and ramp-attribution remain separate evidence streams:
stable-terrain residual is small (-0.04 mm/yr), persistent coherence is 0.887 (above the 0.7
CALIBRATING bar — SoCal §11.1), and reference agreement still fails.
```

---

## Warnings

### WR-01: validation_methodology.md §2.6 cross-reference prose contradicts the actual ToC (stale no-stub-headings claim)

**File:** `docs/validation_methodology.md:279–282`

**Issue:** Section §2.6 ("Cross-reference to other sections") ends with this parenthetical:

> "(These sections are appended by later phases per CONTEXT D-15 append-only policy. Phase 3 owns
> only §1 + §2 in this document; no stub headings for later sections are pre-created.)"

This is no longer true. The Table of Contents at the top of the same document explicitly lists
items 9 through 12 (`CSLC CALIBRATING-to-BINDING conditions`, `EGMS L2a reference methodology`,
`DISP ERA5/deramping/unwrapper diagnostics`, `DISP deferred posture and v1.3 handoff`) — these
sections were authored in Phase 12 (this phase). The phrase "no stub headings for later sections
are pre-created" was accurate when §2.6 was written (Phase 3) but now directly contradicts the
populated §§9–12 that Phase 12 has appended.

This is a quality issue because the §2.6 prose represents the document's own claim about its
structure, and that claim is now verifiably false. It misleads a reader who reaches §2.6 after
reading §§9–12.

**Fix:** Update the trailing parenthetical in §2.6 to reflect the current state:

```markdown
(These sections were appended by their authoring phases per CONTEXT D-15 append-only policy.
Phase 3 authored §1 + §2; §3 was appended by Phase 4; §§4–7 by Phases 5–6; §8 by Phase 10;
§§9–12 by Phase 12.)
```

---

### WR-02: EU DISP IFG count drops from 38 (v1.0) to 9 (Phase 4) without explanation in CONCLUSIONS_DISP_EU.md

**File:** `CONCLUSIONS_DISP_EU.md` — §4.3 vs §13.2

**Issue:** The v1.0 baseline section §4.3 explicitly states "every single one of 38 unwrapped
interferograms" carried a planar ramp anomaly, and §4.1 Stage 7 confirms "38 unwrapping QC
warnings". However, the Phase 4 ramp-attribution table (§13.1 / §13.2) reports `n_ifgs = 9` with
the note "(sequential 12-day pairs from 19-epoch S1A+S1B stack (cross-constellation 6-day pairs
filtered out))".

The document does not explain where the 38 interferograms from the dolphin network went, why only
the 9 sequential 12-day pairs are used for Phase 4 ramp attribution, or what happened to the other
29 IFGs. A reader comparing §4.3 (38 IFGs flagged) to §13.2 (9 IFGs in attribution table) will
find a gap of 29 IFGs with no accounting.

The distinction between the full dolphin network interferogram count and the sequential 12-day pair
subset is methodologically important (it is the same convention as the N.Am. cell where n_ifgs=14
from a 15-epoch stack, matching 14 sequential 12-day pairs, not the 39 total interferograms). The
EU case deserves the same explicit bridging note.

**Fix:** Add a sentence in §13.2 to reconcile the two counts:

```markdown
`n_ifgs = 9` — sequential 12-day pairs from the 19-epoch stack. The Phase 4 ramp-attribution
analysis uses only sequential pairs (consistent with the N.Am. §13.2 convention: 14 pairs from a
15-epoch stack). The v1.0 §4.3 "38 unwrapping QC warnings" counts dolphin's full network
interferogram set (non-sequential pairs included); this is a different set.
```

---

### WR-03: EGMStoolkit version is inconsistent across files

**File:** `CONCLUSIONS_DISP_EU.md:114` vs `docs/validation_methodology.md:929` vs `CLAUDE.md`
(project instructions)

**Issue:** `CONCLUSIONS_DISP_EU.md` §3.5 documents that "EGMStoolkit 0.3.0 is GitHub-only" and
was patched locally. `docs/validation_methodology.md` §10.3 also states "EGMStoolkit 0.3.0
(GitHub-only, broken setup.cfg requiring manual patch)". However, `CLAUDE.md`'s Technology Stack
table lists `EGMStoolkit | 0.2.15` as the recommended version under the "Reporting and Validation
Metrics" section.

These two sources are in conflict: the conclusions and methodology files document that version
0.3.0 was actually installed and used (with a manual patch), while the authoritative project
specification file (`CLAUDE.md`) still references 0.2.15. A contributor setting up the validation
environment will follow `CLAUDE.md` and install 0.2.15, but the methodology doc and conclusions
reference 0.3.0 behaviour (different class API, different `workdirectory` kwarg, different bbox
argument handling).

**Fix:** Either update `CLAUDE.md` to reference 0.3.0 (with the manual-patch caveat and pointer
to the broken setup.cfg), or add a footnote in `CONCLUSIONS_DISP_EU.md` §3.5 and
`docs/validation_methodology.md` §10.3 explicitly noting the discrepancy and why 0.3.0 was used
instead of the recommended 0.2.15. The technology-stack entry in `CLAUDE.md` is the canonical
version reference; it should reflect what actually works.

---

### WR-04: matrix.md DISP EU bias rounding is inconsistent with CONCLUSIONS_DISP_EU.md §12

**File:** `results/matrix.md:19`

**Issue:** The DISP EU reference-agreement cell reads `3.461 (< 3 FAIL)`. The authoritative figure
in `CONCLUSIONS_DISP_EU.md` §12 table is `bias_mm_yr = +3.4608`. Rounding `3.4608` to three
decimal places gives `3.461`. Rounding to four significant figures gives `3.461`. However the
matrix also renders the companion N.Am. bias as `55.43` (four significant figures, matching
`+55.4325` → `55.43`), suggesting the matrix uses four-significant-figure rounding as the
convention.

Under four-significant-figure rounding, `3.4608` → `3.461` (correct). Under three-decimal-place
rounding, `3.4608` → `3.461` (also correct). The inconsistency is subtle: the N.Am. bias
`55.4325` rounds to `55.43` (four characters after the decimal point → two), while the EU bias
`3.4608` rounds to `3.461` (four characters after → three). Rendering precision is not uniform.

This is a quality issue in the published results matrix because a reader who checks the
CONCLUSIONS file will find `3.4608` and the matrix `3.461` and will need to verify they are the
same number, whereas the N.Am. column shows the same number of decimal places as the CONCLUSIONS.
Recommend adopting a single precision rule (two decimal places throughout, or two significant
figures after the leading digit for mm/yr values) so all cells are comparable at a glance.

**Fix:** Adopt consistent two-decimal-place rendering for the reference-agreement bias column:
EU: `3.46` (< 3 FAIL); N.Am.: `55.43` (< 3 FAIL). Align the EU DISP conclusions §12 table
to show `3.46` rather than `3.4608` when cited in context, or add a footnote in the matrix
header explaining the rounding convention used.

---

### WR-05: validation_methodology.md §11.3 deformation sanity thresholds not cited against the conclusions evidence

**File:** `docs/validation_methodology.md:962–966`

**Issue:** Section §11.3 defines the PHASS deramping deformation sanity check thresholds:
`abs(trend_delta_mm_yr) > 3.0` flags the candidate. The Phase 11 outcomes in both conclusions
files show trend_delta values of -390.89 mm/yr (SoCal) and -593.03 mm/yr (Bologna) — between
130× and 200× the stated threshold. The methodology document correctly cross-references these
outcomes ("Phase 11 outcomes: SoCal trend_delta=-390.89 mm/yr (flagged); Bologna
trend_delta=-593.03 mm/yr (flagged)") but does not reference the stable_residual_delta_mm_yr
threshold violation separately.

The second threshold is `abs(stable_residual_delta_mm_yr) > 2.0`. CONCLUSIONS_DISP_N_AM.md Phase
11 SoCal table shows `stable_residual=+117.97 mm/yr` (flagged). CONCLUSIONS_DISP_EU.md Phase 11
Bologna table shows `stable_residual_delta=+74.96 mm/yr` (flagged). Both exceed the 2.0 threshold,
but the methodology §11.3 cross-reference paragraph only cites the trend_delta violations and
omits the stable_residual_delta figures entirely. The methodology's own second threshold criterion
is not confirmed against the evidence it is supposed to document.

**Fix:** Extend the Phase 11 outcomes sentence in §11.3 to include both threshold violations:

```markdown
Phase 11 outcomes: SoCal trend_delta=-390.89 mm/yr (flagged; threshold 3.0 mm/yr),
stable_residual_delta=+117.97 mm/yr (flagged; threshold 2.0 mm/yr); Bologna
trend_delta=-593.03 mm/yr (flagged), stable_residual_delta=+74.96 mm/yr (flagged). Both
thresholds fired on both cells.
```

---

## Info

### IN-01: CONCLUSIONS_DISP_EU.md has no section number 9 or 10 between §8 and §11

**File:** `CONCLUSIONS_DISP_EU.md` — section numbering

**Issue:** The document's v1.0 section numbering runs §1 through §8 (Objective through One-line
summary), then the v1.1 Phase 4 additions begin at §11 (Product Quality). Sections §9 and §10 are
absent. The N.Am. conclusions file has the same pattern: §1–§10 in v1.0, then Phase 4 additions at
§11. In the N.Am. file, §10 is explicitly "Status" so the jump from §10 to §11 is clean. In the
EU file, the v1.0 text ends at §8 (One-line summary), making the jump from §8 to §11 a visible gap
of two missing section numbers (§9 and §10).

This is not a cross-file inconsistency per se — the EU file simply had fewer v1.0 sections than
the N.Am. file — but it makes the EU document appear to have missing content to a first-time
reader. A reader looking for §9 (EGMS token section) will not find it and may assume content was
accidentally deleted.

**Fix:** Either renumber the Phase 4 EU additions from §9 onward (to close the gap), or add a
bridging note below §8:

```markdown
> Sections §9 and §10 do not exist in this document. The v1.0 EU conclusions had fewer
> top-level sections than the N.Am. document (8 vs 10). Phase 4 additions begin at §11
> to maintain numbering consistency with CONCLUSIONS_DISP_N_AM.md for cross-citation.
```

---

### IN-02: CONCLUSIONS_DISP_EU.md §Phase10 stable-terrain residual is inconsistently stated in prose vs tabular form

**File:** `CONCLUSIONS_DISP_EU.md` — Phase 10 ERA5 diagnostic section (Cause assessment narrative)

**Issue:** The Phase 10 ERA5 diagnostic Cause assessment narrative in the EU file says:

> "stable-terrain residual is small (+0.14 mm/yr)"

The §11.2 table for the same cell shows `residual_mm_yr = +0.1170`. The ERA5-on table in Phase 10
shows bias unchanged at `+3.4608 mm/yr` (same as v1.1 baseline). The `+0.14 mm/yr` figure does
not appear in any table in the document. It is presumably the stable-terrain residual from the
Phase 10 ERA5-on run (as opposed to the v1.1 baseline `+0.1170`), but no ERA5-on residual table
is shown for the EU cell (unlike the Phase 10 N.Am. section which similarly approximates
`-0.0303` as `-0.04`).

This is a minor precision inconsistency (0.1170 vs 0.14) but it creates a disconnect: the only
tabular residual value shown for this cell is `+0.1170` (§11.2, baseline), while the narrative
asserts `+0.14` (Phase 10 ERA5-on, not separately tabled). A reader trying to reconcile the two
numbers will not find a table to reference.

**Fix:** Either add a Phase 10 ERA5-on residual row to the Phase 10 section of the EU file (as the
N.Am. Phase 10 section's diagnostic provenance table does), or change the narrative to reference
the tabulated baseline value and note that ERA5-on residual is not separately reported:

```markdown
stable-terrain residual is small (+0.1170 mm/yr on stable terrain per §11.2;
ERA5-on residual not separately tabled — delta is negligible)
```

---

_Reviewed: 2026-05-06_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
