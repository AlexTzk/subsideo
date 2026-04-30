---
phase: 07-results-matrix-release-readiness
plan: 01
subsystem: validation
tags: [matrix_writer, results, calibrating, deferred, rtc]

requires:
  - phase: 06-dswx-s2-n-am-eu-recalibration
    provides: DSWx row complete in matrix; matrix_writer dispatch chain up to dswx:eu
  - phase: 05-dist-s1-opera-v0-1-effis-eu
    provides: dist:nam DEFERRED sidecar pattern (reference for unblock_condition discriminator design)

provides:
  - eval-rtc/metrics.json: RTC:NAM DEFERRED sidecar with unblock_condition discriminator
  - eval-rtc/meta.json: provenance sidecar (git_sha, platform, timestamps)
  - matrix_writer._is_rtc_nam_deferred_shape: discriminator keyed on unblock_condition presence
  - matrix_writer._render_rtc_nam_deferred_cell: renders pq='—', ra='DEFERRED — <unblock>'
  - matrix_writer CALIBRATING annotations: all three sites updated with binds v1.2 / needs 3rd AOI text
  - results/matrix.md: 10-cell matrix, zero RUN_FAILED entries

affects: [07-03, verification, release]

tech-stack:
  added: []
  patterns:
    - DEFERRED sidecar uses unique discriminator key (unblock_condition) not shared with any other cell schema
    - CALIBRATING annotation carries binding milestone inline ("— binds v1.2") for reader clarity

key-files:
  created:
    - eval-rtc/metrics.json
    - eval-rtc/meta.json
  modified:
    - src/subsideo/validation/matrix_writer.py
    - results/matrix.md

key-decisions:
  - "unblock_condition (not reference_source+cmr_probe_outcome) is the RTC:NAM discriminator — the two-key combo routes to dist:nam renderer"
  - "CALIBRATING annotation extended from '(CALIBRATING)' to '(CALIBRATING — binds {milestone})' at Site A (measurement renderer)"
  - "Site B (_render_cslc_selfconsist_cell) gets '— binds v1.2' appended to status_label"
  - "Site C (_render_disp_cell) gets 'CALIBRATING — needs 3rd AOI before binding; see DISP_UNWRAPPER_SELECTION_BRIEF.md'"

patterns-established:
  - "DEFERRED sidecar pattern: schema_version + empty product_quality/reference_agreement + cell_status=DEFERRED + unique discriminator key"
  - "CALIBRATING cells carry binding milestone annotation inline in the rendered cell string"

requirements-completed: [REL-01, REL-02, REL-05]

duration: completed prior session (commits d93da9c, 4a8ba73, 24ca6f3)
completed: 2026-04-28
---

# Plan 07-01: RTC:NAM DEFERRED sidecar + matrix_writer CALIBRATING binds annotations + matrix regen

**RTC:NAM DEFERRED sidecar written, matrix_writer extended with DEFERRED dispatch + 3-site CALIBRATING binds annotations, results/matrix.md regenerated — 10 cells filled, zero RUN_FAILED.**

## Performance

- **Duration:** prior session
- **Completed:** 2026-04-28
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Wrote `eval-rtc/metrics.json` with `unblock_condition` discriminator (structurally disjoint from all other cell schemas: per_burst, per_aoi, ramp_attribution, reference_source+cmr_probe_outcome, selected_aoi+candidates_attempted, thresholds_used+loocv_gap)
- Extended `matrix_writer.py` with `_is_rtc_nam_deferred_shape()` + `_render_rtc_nam_deferred_cell()` + dispatch branch inserted before DISP branches; three CALIBRATING annotation sites updated
- Regenerated `results/matrix.md` — RTC:NAM now renders "DEFERRED — v1.2 N.Am. RTC re-run", CSLC rows show "binds v1.2", DISP rows show "needs 3rd AOI before binding"

## Task Commits

1. **Task 1: Write eval-rtc DEFERRED sidecars** — `d93da9c` (feat(07-01))
2. **Task 2: Extend matrix_writer.py — DEFERRED branch + CALIBRATING binds** — `4a8ba73` (feat(07-01))
3. **Task 3: Regenerate results/matrix.md** — `24ca6f3` (chore(07-01))

## Files Created/Modified

- `eval-rtc/metrics.json` — RTC:NAM DEFERRED sidecar; `cell_status=DEFERRED`, `unblock_condition="v1.2 N.Am. RTC re-run"`
- `eval-rtc/meta.json` — provenance sidecar; git_sha, platform, run timestamps
- `src/subsideo/validation/matrix_writer.py` — 4 changes: `_is_rtc_nam_deferred_shape`, `_render_rtc_nam_deferred_cell`, dispatch branch, 3 CALIBRATING annotation sites
- `results/matrix.md` — 10 filled cells; RTC:NAM DEFERRED; CSLC/DISP CALIBRATING with binds annotations

## Decisions Made

- `unblock_condition` key chosen as discriminator (not `reference_source`+`cmr_probe_outcome`) because the two-key combination is already owned by the `_render_dist_nam_deferred_cell` path — reusing it would route to the wrong renderer
- CALIBRATING annotation extended to include binding milestone so readers know when calibration resolves, without reading criteria.py

## Deviations from Plan

None — plan executed exactly as written. Discriminator key rule from PATTERNS.md followed.

## Issues Encountered

None.

## Next Phase Readiness

- `results/matrix.md` is complete (10/10 cells). REL-01, REL-02, REL-05 closed.
- Plan 07-03 (pytest + CHANGELOG) can now verify matrix is complete.

---
*Phase: 07-results-matrix-release-readiness*
*Completed: 2026-04-28*
