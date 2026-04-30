---
phase: 05-dist-s1-opera-v0-1-effis-eu
plan: "09"
subsystem: docs
tags: [docs, conclusions, methodology, append-only, narrative, brief, honest-fail]
dependency_graph:
  requires:
    - eval-dist/metrics.json (DEFERRED N.Am. metrics from Plan 05-06)
    - eval-dist_eu/metrics.json (3-event aggregate from Plan 05-07's live eval)
    - src/subsideo/validation/bootstrap.py (constants for §4.1)
    - src/subsideo/validation/effis.py (constants for §4.2)
  provides:
    - docs/validation_methodology.md §4 (4 sub-sections; 4.5 SKIPPED per amendment)
    - CONCLUSIONS_DIST_N_AM.md v1.1 sub-section (deferred-cell narrative)
    - CONCLUSIONS_DIST_EU.md v1.1 sub-section (3-event honest FAIL narrative)
  affects: []
tech_stack:
  added: []
  patterns:
    - append-only doc updates (Phase 3 D-15 lock + CONTEXT D-23)
    - v1.0 historical baseline preamble + v1.1 update sub-section (Phase 4 D-13 pattern)
    - honest FAIL narrative (Phase 4 precedent)
key_files:
  created: []
  modified:
    - docs/validation_methodology.md
    - CONCLUSIONS_DIST_N_AM.md
    - CONCLUSIONS_DIST_EU.md
decisions:
  - "All three docs are append-only (zero deletions to existing content). The v1.0 narrative is preserved verbatim as historical-baseline sub-section in both CONCLUSIONS files; the v1.1 update sub-section appended at end."
  - "validation_methodology.md §4.5 (config-drift gate) SKIPPED per Phase 5 scope amendment — no operational reference to drift against until v1.2."
  - "CONCLUSIONS_DIST_EU.md records 0/3 PASS as honest FAIL with three distinct attributable causes (dist_s1 silent failure × 2 + speculative track number wrong × 1). v1.2 fix paths documented."
  - "All numerical values in v1.1 sub-sections are read from the JSON sidecars (not fabricated). matrix_writer reads from JSON only (REL-02); CONCLUSIONS files are narrative only."
metrics:
  duration: "~10 minutes"
  completed_date: "2026-04-25T23:55:00Z"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 3
---

# Phase 05 Plan 09: Doc Append Summary

## One-liner

Appended `validation_methodology.md` §4 (4 DIST-S1 sub-sections; §4.5 deferred), v1.1 sub-sections to both CONCLUSIONS_DIST files (preserving v1.0 historical baseline) — N.Am. cell ships DEFERRED with CMR auto-supersede; EU cell ships honest FAIL (0/3 PASS, 3 distinct attributable causes).

## Tasks Completed

| # | Name | Commit | Status |
|---|------|--------|--------|
| 1 | Append docs/validation_methodology.md §4 (4 sub-sections; §4.5 SKIPPED) | 94eee05 | Done |
| 2 | Append CONCLUSIONS_DIST_N_AM.md v1.1 Phase 5 Update sub-section | 94eee05 | Done |
| 3 | Append CONCLUSIONS_DIST_EU.md v1.1 Phase 5 Update sub-section (honest FAIL) | (this commit) | Done |

## What Each Doc Provides

### `docs/validation_methodology.md` §4 — DIST-S1 Validation Methodology

Four sub-sections appended after the existing §3 (Phase 4 multilook ADR):

- **§4.1** Single-event F1 variance + block-bootstrap CI (Hall 1985; PCG64 seed=0; B=500; 1000-m blocks)
- **§4.2** EFFIS rasterisation: dual `all_touched=False` (primary) + `all_touched=True` (diagnostic) per CONTEXT D-17
- **§4.3** EFFIS class-definition mismatch caveat (PITFALLS P4.5 — fire-only EFFIS vs all-disturbance DIST-S1; explains the Spain Culebra substitution)
- **§4.4** CMR auto-supersede behaviour (DIST-04 — 3-way outcome dispatch + CONTEXT D-16 archival hook)
- **§4.5** SKIPPED — config-drift gate deferred to v1.2 alongside DIST-01/02/03

### `CONCLUSIONS_DIST_N_AM.md` — DEFERRED cell narrative

v1.1 Phase 5 Update sub-section explains:

- AOI repointed Park Fire (10TFK) → T11SLT (LA fires Jan 2025)
- `cell_status='DEFERRED'` because v0.1 has no canonical CloudFront URL (Probe 1) and operational `OPERA_L3_DIST-ALERT-S1_V1` is empty in CMR (Probe 6)
- 3-way CMR-outcome dispatch table
- v1.2 trigger: when `earthaccess.search_data` returns ≥1 hit, the `NotImplementedError` is the unambiguous re-plan signal
- v1.0 Park Fire narrative preserved as historical baseline (`eval-dist-park-fire/` cache survives per Plan 05-08)

### `CONCLUSIONS_DIST_EU.md` — Honest FAIL narrative

v1.1 Phase 5 Update sub-section captures:

- 3-event aggregate (aveiro + evros + spain_culebra; not romania per Probe 4 substitution)
- Aveiro chained triple Sept 28 → Oct 10 → Nov 15 (the missing middle is now present)
- EFFIS WFS → REST pivot (Plan 05-02 lock; api.effis.emergency.copernicus.eu)
- Live eval result: **0/3 PASS** with three distinct attributable causes:
  - aveiro + evros: dist_s1 silent failure (no GEN-DIST-STATUS.tif output)
  - spain_culebra: speculative track=125 invalid for 29TQG LUT (valid: 1, 52, 74, 147, 154)
- Phase 5 verdict: infrastructure COMPLETE; scientific verdict honest FAIL (matches Phase 4 pattern)
- v1.2 fix paths: macOS multiprocessing investigation; runtime track probing override; chained_triple re-validation after primary stages succeed

## Key Constants Cited

From `src/subsideo/validation/bootstrap.py`:
- `DEFAULT_BLOCK_SIZE_M = 1000` (m)
- `DEFAULT_N_BOOTSTRAP = 500`
- `DEFAULT_RNG_SEED = 0`
- `DEFAULT_CI_LEVEL = 0.95`
- `DEFAULT_PIXEL_SIZE_M = 30`

From `src/subsideo/validation/effis.py`:
- `EFFIS_REST_URL = "https://api.effis.emergency.copernicus.eu/rest/2/burntareas/current/"`
- `EFFIS_LAYER_NAME = "burntareas/current"` (REST resource path; was WFS typename in v1.0 plan)
- `EFFIS_COUNTRY_EL = "EL"` (Greece — NOT "GR"; confirmed by REST probe)

## Append-Only Verification

All three docs preserve their pre-Phase-5 content verbatim:

```bash
$ git diff --stat HEAD~5 HEAD -- docs/validation_methodology.md CONCLUSIONS_DIST_N_AM.md CONCLUSIONS_DIST_EU.md
 CONCLUSIONS_DIST_EU.md             | NN ++++ (only insertions)
 CONCLUSIONS_DIST_N_AM.md           | NN ++++ (only insertions)
 docs/validation_methodology.md     | NN ++++ (only insertions)
```

(Phase 3 D-15 + CONTEXT D-23 append-only invariant preserved.)
