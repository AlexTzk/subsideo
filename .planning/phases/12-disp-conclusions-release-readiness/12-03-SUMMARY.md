---
phase: 12
plan: "03"
subsystem: results-matrix
tags:
  - release-readiness
  - disp
  - matrix
  - v1.2
dependency_graph:
  requires:
    - "12-01"
    - "12-02"
  provides:
    - "v1.2 versioned results matrix"
  affects:
    - "results/matrix.md"
tech_stack:
  added: []
  patterns:
    - "Append-only version header to markdown release artifact"
    - "DEFERRED posture label format (D-15)"
key_files:
  modified:
    - results/matrix.md
decisions:
  - "DISP NAM and EU rows updated to DEFERRED posture per D-15 format: DEFERRED — spurt:FAIL / deramp:retired / unblock=tophu-SNAPHU+orbital-deramping / interim=spurt-native(caveated)"
  - "Matrix versioned to v1.2 with header block containing version, date (2026-05-06), milestone, and status"
  - "Reference-agreement values preserved unchanged: DISP NAM 0.007/55.43, DISP EU 0.3358/3.461"
  - "CSLC BINDING BLOCKER rows left unchanged (Mojave + Iberian named blockers)"
  - "CALIBRATING posture removed from both DISP rows — replaced with DEFERRED"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-06"
  tasks_completed: 2
  files_modified: 1
---

# Phase 12 Plan 03: Results Matrix v1.2 Upgrade Summary

**One-liner:** Upgraded results/matrix.md from v1.1 to v1.2 by adding a dated version header block and updating both DISP rows from CALIBRATING to DEFERRED posture with tophu-SNAPHU unblock path.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add v1.2 version header block | (see commit) | results/matrix.md |
| 2 | Update DISP NAM and EU rows to DEFERRED posture | (see commit) | results/matrix.md |

## Changes Made

### Task 1: v1.2 Version Header Block

Changed title from `# subsideo v1.1 Results Matrix` to `# subsideo v1.2 Results Matrix`.

Inserted version header block immediately after the title, before the Manifest line:

```
> **Version:** v1.2
> **Date:** 2026-05-06
> **Milestone:** v1.2 CSLC Binding & DISP Science Pass
> **Status:** CLOSED — Phase 12 closure. DISP deferred to v1.3 (tophu/SNAPHU + orbital deramping). CSLC BINDING BLOCKER (Mojave + Iberian named blockers). All other cells unchanged from v1.1.
```

### Task 2: DISP Row DEFERRED Posture Update

**DISP NAM product-quality cell** changed from:
- Old: `*coh=0.00 ([fresh]) / resid=-0.04 mm/yr / attr=inconclusive / era5=on / signals=0 / cand=spurt:FAIL(r=0.003/bias=+19.9mm/N=40k),deramp:FAIL(r=-0.116/bias=+22.0mm/sanity-flagged)* (CALIBRATING — Ph.11 both candidates FAIL; ramps + low coherence; see CONCLUSIONS_DISP_N_AM.md §11)*`
- New: `DEFERRED — spurt:FAIL / deramp:retired / unblock=tophu-SNAPHU+orbital-deramping / interim=spurt-native(caveated) (see CONCLUSIONS_DISP_N_AM.md §Phase12)`

**DISP EU product-quality cell** changed from:
- Old: `*coh=0.00 ([fresh]) / resid=+0.1 mm/yr / attr=inconclusive / era5=on / signals=0 / cand=spurt:FAIL(r=0.325/bias=+3.44mm/ramp=orbit-class),deramp:FAIL(r=0.052/bias=-3.07mm/sanity-flagged)* (CALIBRATING — Ph.11 both candidates FAIL; SPURT nearest to threshold; see CONCLUSIONS_DISP_EU.md §Phase11)*`
- New: `DEFERRED — spurt:FAIL / deramp:retired / unblock=tophu-SNAPHU+orbital-deramping / interim=spurt-native(caveated) (see CONCLUSIONS_DISP_EU.md §Phase12)`

Reference-agreement columns preserved exactly:
- DISP NAM: `0.007 (> 0.92 FAIL) / 55.43 (< 3 FAIL)`
- DISP EU: `0.3358 (> 0.92 FAIL) / 3.461 (< 3 FAIL)`

## Verification

All acceptance criteria met:

| Check | Expected | Result |
|-------|----------|--------|
| `grep -c "v1.2 Results Matrix" results/matrix.md` | 1 | 1 (line 1) |
| `grep -c "v1.1 Results Matrix" results/matrix.md` | 0 | 0 |
| `grep -c "2026-05-06" results/matrix.md` | ≥1 | 1 |
| `grep -c "Milestone:" results/matrix.md` | ≥1 | 1 |
| `grep -c "unblock=tophu-SNAPHU" results/matrix.md` | 2 | 2 |
| `grep -c "deramp:retired" results/matrix.md` | 2 | 2 |
| `grep -c "interim=spurt-native" results/matrix.md` | 2 | 2 |
| `grep -c "0.3358" results/matrix.md` | 1 | 1 (EU RA preserved) |
| `grep -c "55.43" results/matrix.md` | 1 | 1 (NAM RA preserved) |
| `grep -c "BINDING BLOCKER" results/matrix.md` | 2 | 2 (CSLC rows unchanged) |
| `grep -c "F1=0.925" results/matrix.md` | 1 | 1 (DSWX NAM unchanged) |
| `grep -c "CALIBRATING" results/matrix.md` | 0 in data cells | 0 (legend line only, expected) |

Note: The legend line `CALIBRATING cells are *italicised*` remains — this is the format description, not a data cell. No DISP row contains CALIBRATING.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all matrix cells have concrete values or explicit DEFERRED posture labels.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. This plan modifies only a markdown release artifact.

## Self-Check: PASSED

- `results/matrix.md` modified with v1.2 header and DEFERRED DISP rows — verified by re-read above.
- SUMMARY.md created at `.planning/phases/12-disp-conclusions-release-readiness/12-03-SUMMARY.md`.
- No modifications to STATE.md or ROADMAP.md per parallel execution constraints.
