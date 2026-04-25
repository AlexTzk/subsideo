---
status: approved
phase: 03-cslc-s1-self-consistency-eu-validation
source: [03-VERIFICATION.md]
started: 2026-04-25T01:54:42Z
updated: 2026-04-25T01:58:00Z
signed_off_by: user
signed_off_at: 2026-04-25T01:58:00Z
---

## Current Test

[all signed off — phase approved]

## Tests

### 1. SoCal sparse-mask interpretation sign-off

expected: Sign off that the SoCal coherence number (coh_med_of_persistent=0.887 on 486 valid CSLC pixels, persistent_frac=2.5%) is the right metric on the right pixel population given the `coast_buffer_m` unit bug documented in CONCLUSIONS_CSLC_SELFCONSIST_NAM.md §8 follow-up #2. Confirm the CALIBRATING (not PASS/FAIL) verdict per Phase 3 D-03 first-rollout discipline.

why_human: Scientific validity of metric-on-sparse-mask cannot be verified programmatically; requires human SAR/InSAR judgment of whether 486 valid CSLC pixels yields a robust calibration data point for Phase 4 threshold setting.

artifacts:
- CONCLUSIONS_CSLC_SELFCONSIST_NAM.md §5-§8
- eval-cslc-selfconsist-nam/metrics.json
- eval-cslc-selfconsist-nam/sanity/SoCal/mask_metadata.json

result: approved (2026-04-25 — user sign-off accepts CALIBRATING verdict on 486-pixel mask; `coast_buffer_m` unit bug tracked for later fix)

### 2. Iberian/Meseta-North plausibility sign-off

expected: Sign off that Iberian numbers (92.3% persistent_frac + 0.347 mm/yr residual + 0.891 coh_median_of_persistent) are physically plausible for bare/sparse-vegetation steppe over 6 months. Accept that EGMS L2a third number is deferred (Bug 8) — rollout reports (a)+(b) of the three-number schema and (c) is null.

why_human: Domain expert judgment of whether 92.3% persistent_frac is unusually high but consistent with Iberian Meseta phenology.

artifacts:
- CONCLUSIONS_CSLC_SELFCONSIST_EU.md §5-§8
- eval-cslc-selfconsist-eu/metrics.json
- eval-cslc-selfconsist-eu/sanity/Iberian/mask_metadata.json

result: approved (2026-04-25 — user accepts Iberian numbers and null EGMS L2a third-number per Bug 8 deferral)

### 3. Visual inspection of sanity PNGs

expected: Inspect `eval-cslc-selfconsist-{nam,eu}/sanity/<aoi>/{coherence_histogram.png, stable_mask_over_basemap.png}` for each AOI (SoCal, Mojave/Coso-Searles, Iberian). Confirm no bimodal P2.1 contamination (CONCLUSIONS NAM §5.3 + EU §5.3 claim unimodal). Confirm stable masks visually fall on actual stable terrain (bedrock + steppe), not dunes or playas.

why_human: PNG histogram + georeferenced mask basemap inspection requires visual judgment; not programmatically verifiable.

artifacts:
- eval-cslc-selfconsist-nam/sanity/SoCal/*.png
- eval-cslc-selfconsist-nam/sanity/Mojave/Coso-Searles/*.png
- eval-cslc-selfconsist-eu/sanity/Iberian/*.png

result: approved (2026-04-25 — user visual inspection confirmed no bimodal contamination; masks fall on stable terrain)

### 4. Decision on two deferred follow-ups

expected: Decide whether to proceed to Phase 4 with two outstanding follow-ups deferred (Iberian Alentejo + Massif Central fallback re-derivation after Bug 2; EGMS L2a third-number adapter after Bug 8), OR schedule them as Phase 3 gap-closure work.

why_human: Scope decision — neither follow-up is a Phase 3 contractual must-have; both are recommendations from the rollout surfaced in CONCLUSIONS_CSLC_SELFCONSIST_EU.md §8 #1 + #2.

artifacts:
- CONCLUSIONS_CSLC_SELFCONSIST_EU.md §8

result: approved (2026-04-25 — user accepts both follow-ups as post-phase work; advance to Phase 4)

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
