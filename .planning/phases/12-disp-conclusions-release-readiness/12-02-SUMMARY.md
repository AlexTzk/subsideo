---
phase: 12-disp-conclusions-release-readiness
plan: "02"
subsystem: docs
tags: [validation-methodology, cslc, disp, egms, methodology, documentation]
dependency_graph:
  requires:
    - ".planning/phases/09-cslc-egms-third-number-binding-reruns/09-CONTEXT.md"
    - ".planning/phases/11-disp-unwrapper-deramping-candidates/11-CONTEXT.md"
    - "docs/validation_methodology.md (§1–§8 existing)"
  provides:
    - "docs/validation_methodology.md §9–§12 (v1.2 methodology additions)"
  affects:
    - "Phase 12 plan 03 (REQUIREMENTS.md traceability — references §9 for CSLC-07)"
    - "Phase 12 plan 04 (results/matrix.md v1.2 header)"
tech_stack:
  added: []
  patterns:
    - "Append-only methodology doc discipline (Phase 1 D-15)"
    - "ADR-style section format for CSLC CALIBRATING-to-BINDING gate"
    - "Named-blocker pattern (candidate BINDING with structured evidence)"
key_files:
  created: []
  modified:
    - "docs/validation_methodology.md"
decisions:
  - "Four new sections §9–§12 appended after §8; ToC updated with four new entries"
  - "§9 uses full ADR-style structure: problem statement, two-signal rule, named-blocker definition, per-AOI unblock table, future promotion guidance"
  - "§11 cross-references §8 via inline callout to avoid duplication of ERA5 two-signal rule"
metrics:
  duration: "3 minutes"
  completed_date: "2026-05-07"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
---

# Phase 12 Plan 02: Validation Methodology v1.2 Additions Summary

**One-liner:** Appended four ADR-style methodology sections (§9–§12) to validation_methodology.md covering CSLC CALIBRATING-to-BINDING promotion gate, EGMS L2a named-blocker pattern, DISP ERA5/deramping/unwrapper diagnostics, and DISP v1.2 deferred posture with v1.3 handoff.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Update ToC with §9–§12 anchor links | 04d617d | docs/validation_methodology.md (4 lines added to ToC) |
| 2 | Append §9–§12 section bodies | 5193f35 | docs/validation_methodology.md (164 lines added) |

## What Was Built

`docs/validation_methodology.md` now has twelve top-level sections. The four new sections (§9–§12) document:

**§9 CSLC CALIBRATING-to-BINDING conditions** — Full ADR-style section establishing:
- Two-signal promotion rule: `median_of_persistent >= 0.75` AND `stable_terrain_residual_mm_yr <= 2.0` on all active AOIs with no named blocker outstanding
- Named-blocker definition (evidence-backed, external-to-algorithm reason)
- Per-AOI unblock table for Mojave/Coso-Searles (`required_aoi_binding_blocker` — no OPERA CSLC frame match) and Iberian (`required_aoi_binding_blocker` — EGMS L2a programmatic download gap)
- Future promotion guidance: atomic commit with regenerated sidecars + criteria.py change + matrix update

**§10 EGMS L2a reference methodology and named-blocker pattern** — Documents:
- EGMS L2a as EU DISP reference (EPSG:3035 → WGS84, geopandas point layer, rasterio.sample, rad/yr → mm/yr conversion)
- `prepare_for_reference(method='block_mean')` discipline for EGMS point-cloud comparison
- Phase 9 candidate-BINDING-with-named-blocker pattern for EGMS-dependent cells
- EGMStoolkit 0.3.0 tooling state: no M2M programmatic path as of 2026-04-15

**§11 DISP ERA5/deramping/unwrapper diagnostics** — Consolidates:
- ERA5 two-signal rule outcomes: SoCal worsened (r=0.0071 vs baseline 0.0490), Bologna unchanged
- Phase 11 candidate evaluation methodology (isolated candidates/, DISPCandidateOutcome sidecar)
- PHASS deformation sanity check thresholds: `abs(trend_delta_mm_yr) > 3.0` OR `abs(stable_residual_delta_mm_yr) > 2.0`
- SPURT orbit-class attribution on Bologna (ramp_sigma_deg=7.1°)
- Cross-reference callout to §8 for ERA5 two-signal rule outcomes

**§12 DISP deferred posture and v1.3 handoff** — Documents:
- v1.2 DEFERRED decision with candidate evidence table
- PHASS retirement: SBAS re-inversion instability (trend_delta=-390.89 mm/yr SoCal, -593.03 mm/yr Bologna)
- Named blocker: SPURT orbit-class ramp on Bologna (σ=7.1°)
- Unblock condition: both cells pass r > 0.92 AND bias < 3 mm/yr in same tophu/SNAPHU run
- Interim SPURT note with explicit criteria-failure caveat
- v1.3 recommended candidate order: tophu/SNAPHU → 20×20 m → ERA5+tophu combined; PHASS excluded

## Verification

All acceptance criteria confirmed:
- `grep -c "^## 9\." docs/validation_methodology.md` → 1
- `grep -c "^## 10\." docs/validation_methodology.md` → 1
- `grep -c "^## 11\." docs/validation_methodology.md` → 1
- `grep -c "^## 12\." docs/validation_methodology.md` → 1
- `grep -c "cslc-calibrating-to-binding"` → 2 (ToC + section anchor)
- `grep -c "Two-signal promotion rule"` → 1
- `grep -c "required_aoi_binding_blocker"` → 5 (table + prose across §9/§10)
- `grep -c "SBAS re-inversion"` → 1
- `grep -c "trend_delta=-390"` → 2
- `grep -c "trend_delta=-593"` → 1
- `grep -c "orbit-class"` → 6 (§11.4 + §12.3 + §12.4 + §12.5 + cross-refs)
- `grep -c "^## 1\." docs/validation_methodology.md` → 1 (no §1 duplication)
- `grep -c "^## 8\." docs/validation_methodology.md` → 1 (no §8 duplication)
- Existing §1–§8 content unchanged

## Deviations from Plan

None — plan executed exactly as written. The plan acceptance criteria used unanchored grep patterns (`grep -c "## 9\."`) that also match subsection headers (e.g., `### 9.1`); used anchored `^## 9\.` for verification instead, which correctly returns 1 for each top-level section header.

## Threat Flags

None — all files created/modified are documentation files with no new network endpoints, auth paths, file access patterns, or schema changes.

## Known Stubs

None — this plan is documentation-only with no code or data stubs.

## Self-Check: PASSED

- `docs/validation_methodology.md` exists and contains 1017 lines
- Task 1 commit 04d617d verified in git log
- Task 2 commit 5193f35 verified in git log
- All four top-level section headers §9–§12 confirmed with anchored grep
- ToC entries for §9–§12 confirmed at lines 27–30
