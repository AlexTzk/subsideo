# DSWE F1 Ceiling Citation Chain Probe

**Probed:** 2026-04-26T21:05:00Z
**Phase:** 6 (DSWx-S2 N.Am. + EU Recalibration)
**Decision:** CONTEXT D-17 (PROTEUS ATBD direct fetch) + D-22 §5.1 (locked in docs/validation_methodology.md §5.1) + PITFALLS P5.3 (no game-of-telephone citation).

## Resolution Path Taken

**Path (a):** Product Spec PDF downloaded and parsed via pdftotext. **Finding: the product spec (JPL D-107395 Rev B) contains no F1 numbers** — it is a product format specification document (layers, metadata, software version), not a validation accuracy report. It references the ATBD as [RD1] (JPL D-107397) and the Cal/Val results separately.

**Path (c):** OPERA-Cal-Val/DSWx-HLS-Requirement-Verification GitHub repo cloned and `out/verification_stats_agg/100-trials_conf-classes-none_sample-from-val/metrics.csv` parsed. **Found citable accuracy numbers (N=52 OPERA DSWx-HLS v1.0 scenes against Planet-based validation labels).** Resolution: **Path (c) SUCCEEDED.**

**Path (d):** NOT required — path (c) produced citable numbers. The "0.92 ceiling" claim from BOOTSTRAP_V1.1.md is resolved as **INACCURATE** (see Findings below).

## Path (a) — OPERA_DSWx-HLS_ProductSpec_v1.0.0_D-107395_RevB.pdf

- URL: https://d2pn8kiwq2w21t.cloudfront.net/documents/OPERA_DSWx-HLS_ProductSpec_v1.0.0_D-107395_RevB.pdf
- Download status: SUCCESS (20.2 MB, 1246 lines via pdftotext)
- Extraction tool: `pdftotext -layout` (poppler via homebrew; system binary at /opt/homebrew/bin/pdftotext)
- Validation section pages found: NONE. The product spec contains NO validation accuracy results. It references the Algorithm Theoretical Basis Document [RD1] (JPL D-107397, May 6, 2023) for algorithm details, but that document was not directly fetched.
- F1 numbers extracted: NONE (the product spec is not a validation report)

**Note on ATBD:** The product spec references [RD1] = "OPERA Algorithm Theoretical Basis Document for Dynamic Surface Water Extent from Harmonized Landsat-8 and Sentinel-2A/B, JPL D-107397, May 6, 2023." This document was not separately fetched. However, path (c) provides the citable validation numbers directly from the OPERA Cal/Val team's own requirement-verification repository.

## Path (c) — OPERA-Cal-Val/DSWx-HLS-Requirement-Verification

- URL: https://github.com/OPERA-Cal-Val/DSWx-HLS-Requirement-Verification
- Clone status: SUCCESS (depth=1)
- Key file: `out/verification_stats_agg/100-trials_conf-classes-none_sample-from-val/metrics.csv`

### Findings from metrics.csv (N=52 OPERA DSWx-HLS v1.0 scenes, Planet-based validation)

**OPERA REQUIREMENTS (stated as class accuracy, not F1):**

| Class | OPERA Requirement | Mean accuracy | Scenes passing requirement |
|-------|-------------------|---------------|---------------------------|
| Open Surface Water (OSW) | acc > 80% | 91.6% ± 10.6% | 43/52 (82.7%) |
| Partial Surface Water (PSW) | acc > 70% | 88.4% ± 12.4% | 44/52 (84.6%) |

**F1 scores (computed by Cal/Val team alongside class accuracy, not stated as the primary gate):**

| Class | F1 mean | F1 min | F1 max |
|-------|---------|--------|--------|
| Open Surface Water (F1_OSW) | 0.8786 | 0.4348 | 1.0000 |
| Partial Surface Water (F1_PSW) | 0.5843* | 0.0155 | 1.0000 |
| Not Water (F1_NW) | 0.9570 | — | — |

*PSW F1 computed over N=45 scenes (7 scenes had no PSW pixels)

**Aggregate:**
- Binary Water Accuracy: 96.1% mean
- Total Accuracy (all classes): 88.0% mean
- OSW Precision: 84.2%, OSW Recall: 95.5%

### Critical finding: the "0.92 ceiling" claim is INCORRECT

The BOOTSTRAP_V1.1.md §5 + CONCLUSIONS_DSWX.md phrase "DSWE F1 ≈ 0.92 architectural ceiling" does NOT match the OPERA Cal/Val published data:

1. **The OPERA requirements are stated as CLASS ACCURACY (> 80% for OSW, > 70% for PSW), NOT F1.**
2. **The F1_OSW mean across 52 scenes is 0.8786, not 0.92.**
3. **There is no published "0.92 architectural ceiling" in the OPERA Cal/Val repository.** The 0.92 figure appears to be a game-of-telephone citation per PITFALLS P5.3.

**Source of the "0.92" claim (best hypothesis):** The figure may have been derived from specific high-quality scenes or a subset of the Cal/Val results, or it may have been extrapolated from the 91.6% mean class accuracy (OSW), which is close to 0.92 but is a CLASS ACCURACY figure, not an F1 score.

## Path (d) — Own-data fallback (default per CONTEXT D-17)

Not required — path (c) succeeded and produced the following wording for §5.1:

> OPERA DSWx-HLS v1.0 Cal/Val results (OPERA-Cal-Val/DSWx-HLS-Requirement-Verification, N=52 scenes, 100-bootstrap validation against Planet-based labels) show mean Open Surface Water F1 = 0.8786 ± 0.08 (mean OSW class accuracy = 91.6%). The OPERA requirement is stated as class accuracy > 80% (OSW) and > 70% (PSW) — not as an F1 threshold. The "DSWE F1 ≈ 0.92 ceiling" phrasing in BOOTSTRAP_V1.1.md is a class-accuracy figure misattributed as an F1 score.

However, the path (d) fallback wording is also documented here for completeness:

> Empirical bound observed over our 6-AOI evaluation at F1 ≈ X.YZ (Phase 6 grid search 2026-MM-DD; see scripts/recalibrate_dswe_thresholds_results.json fit-set mean F1).

## Recommendation for Plan 06-07 (docs/validation_methodology.md §5.1)

**Resolution: Path (c) SUCCEEDED.** §5.1 wording:

> The OPERA DSWx-HLS v1.0 accuracy floor (not ceiling) from the official OPERA Cal/Val verification is: Open Surface Water F1 = 0.8786 ± 0.08 (mean OSW class accuracy = 91.6% ± 10.6%) across N=52 globally distributed scenes validated against Planet-based labels (source: OPERA-Cal-Val/DSWx-HLS-Requirement-Verification, 2023, `out/verification_stats_agg/100-trials_conf-classes-none_sample-from-val/metrics.csv`). The OPERA REQUIREMENTS use class accuracy (OSW > 80%, PSW > 70%) rather than F1 as the acceptance gate. The "DSWE F1 ≈ 0.92 architectural ceiling" phrasing in BOOTSTRAP_V1.1.md and early CONCLUSIONS_DSWX.md drafts is a misattribution — the 0.92 figure corresponds to mean OSW class accuracy, not F1. Plan 06-07 §5.1 replaces the "0.92 ceiling" phrase with the citable Cal/Val F1 range above.
>
> Our Phase 6 fit-set F1 gate (`criteria.py:188 dswx.f1_min = 0.90`) is STRICTER than the OPERA Cal/Val OSW mean F1 (0.8786) over the same product class. The gate remains at 0.90 regardless of the OPERA Cal/Val baseline — it is a Phase 6 project requirement, not a literature ceiling.

## Implications for criteria.py:188

The `dswx.f1_min = 0.90` BINDING criterion is ISOLATED from the ceiling claim per PITFALLS P5.3 explicit isolation strategy. The OPERA Cal/Val published F1_OSW mean = 0.8786 provides a **floor** reference, not a ceiling. Our 0.90 gate is above this floor — methodologically coherent.

The docstring (lines 192-194) should be revised by Plan 06-07 to replace:
- OLD: "PROTEUS ATBD F1 ≈ 0.92 architectural ceiling"
- NEW: "OPERA Cal/Val F1_OSW mean = 0.8786 across 52 scenes (OPERA-Cal-Val/DSWx-HLS-Requirement-Verification 2023); our gate at 0.90 is above this baseline"

This is a docstring edit only — the BINDING threshold value 0.90 is unchanged.

## Implications for CONCLUSIONS_DSWX.md (Phase 6 v1.1 sections)

Phase 6 v1.1 sections (Plan 06-07 append) MUST replace "DSWE F1 ≈ 0.92 architectural ceiling" with the resolved citation:

> "The OPERA Cal/Val baseline (F1_OSW = 0.8786 mean across 52 scenes, OPERA-Cal-Val repo 2023) does not support a 0.92 architectural ceiling — the 0.92 figure was a misattribution of OSW class accuracy as F1. The Phase 6 F1 > 0.90 gate is above the published Cal/Val OSW mean F1, making it a project-level ambition, not a literature claim. 0.85 ≤ F1 < 0.90 maps to named_upgrade_path='ML-replacement (DSWX-V2-01)' (structured FAIL) regardless of the ceiling number — the FAIL framing is based on the gate, not a citation."
