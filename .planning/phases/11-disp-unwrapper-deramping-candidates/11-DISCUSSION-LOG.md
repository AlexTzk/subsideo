# Phase 11: disp-unwrapper-deramping-candidates - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-05-04
**Phase:** 11-disp-unwrapper-deramping-candidates
**Areas discussed:** Candidate Execution Posture, Deramping Semantics, Failure Evidence Shape

---

## Candidate Execution Posture

### How should Phase 11 schedule candidates?

| Option | Description | Selected |
|--------|-------------|----------|
| SPURT first, then decide | Run SPURT native on both cells first; only plan PHASS deramping/tophu follow-ups after seeing structured SPURT results. | |
| SPURT + PHASS deramping in same phase | Always run SPURT and PHASS deramping so Phase 12 has a direct unwrapper-vs-deramp comparison. | yes |
| Full ladder plan | Plan SPURT, PHASS deramping, and tophu/SNAPHU with stop gates between them. | |

**User's choice:** SPURT + PHASS deramping in same phase.
**Notes:** User accepted the recommendation to include both candidates so Phase 12 has comparative evidence.

### Should those two candidates run on both cells by default?

| Option | Description | Selected |
|--------|-------------|----------|
| Both candidates on both cells | Run SPURT and PHASS deramping for SoCal and Bologna. | yes |
| SPURT on both, PHASS only where useful | Run SPURT for both cells; run PHASS deramping only if ramp/product evidence suggests it can teach us something. | |
| Cell-specific strategy | SPURT for SoCal, PHASS deramping emphasized for Bologna. | |

**User's choice:** Both candidates on both cells.
**Notes:** Locks four candidate-cell outcomes as the core Phase 11 evidence set.

### What should be the default stop condition inside Phase 11?

| Option | Description | Selected |
|--------|-------------|----------|
| No early stop | Always collect all four planned candidate-cell results. | yes |
| Stop only on hard blockers | Continue through all planned runs unless a local implementation issue prevents valid candidate output. | |
| Stop if SPURT clearly passes | If SPURT reaches a convincing PASS on both cells, skip PHASS deramping. | |

**User's choice:** No early stop.
**Notes:** PHASS deramping remains required even if SPURT performs well.

### How should the phase treat candidate ordering during execution?

| Option | Description | Selected |
|--------|-------------|----------|
| SPURT first, then PHASS | Run SPURT first because Phase 10 points to unwrapper change as the main hypothesis, then run PHASS deramping as the comparison. | yes |
| PHASS first, then SPURT | Run the cheap deramping path first for fast signal, then SPURT. | |
| Planner decides by implementation convenience | Keep the context agnostic and let the plan choose the order. | |

**User's choice:** SPURT first, then PHASS.
**Notes:** Preserves Phase 10/v1.1 ordering while still guaranteeing deramping evidence.

---

## Deramping Semantics

### Where should PHASS post-deramping happen conceptually?

| Option | Description | Selected |
|--------|-------------|----------|
| Before network inversion | Subtract fitted planar ramps from per-IFG unwrapped phases before MintPy/time-series inversion. | yes |
| After velocity output | Deramp the final velocity raster only. | |
| Both before and after | More complete but likely over-scopes Phase 11. | |

**User's choice:** Before network inversion.
**Notes:** Matches the v1.1 brief's PHASS post-deramping candidate definition.

### Should deramping be allowed to change native production output?

| Option | Description | Selected |
|--------|-------------|----------|
| Validation candidate only | Keep native production default unchanged; deramping produces candidate outputs/sidecars for comparison only. | yes |
| Candidate production mode | Add a configurable PHASS-deramped production mode if metrics improve. | |
| Promote immediately if it passes | If deramping passes, Phase 11 can make it the new default. | |

**User's choice:** Validation candidate only.
**Notes:** Phase 12 owns production posture.

### What signal-preservation check should deramping include?

| Option | Description | Selected |
|--------|-------------|----------|
| Reference/product metrics only | Trust r, bias, RMSE, stable residual, and ramp attribution. | |
| Add deformation-signal sanity check | Include a lightweight guard that deramping did not simply erase real long-wavelength signal, especially for SoCal. | yes |
| No extra check | Deramping is just a candidate; compare outputs and move on. | |

**User's choice:** Add deformation-signal sanity check.
**Notes:** The v1.1 brief flags SoCal tectonic-signal risk.

### How strict should that sanity check be?

| Option | Description | Selected |
|--------|-------------|----------|
| Advisory only | Record warning evidence, but do not block candidate metrics. | |
| Block production recommendation only | Candidate metrics can be reported, but Phase 12 cannot recommend PHASS deramping if the sanity check flags likely signal erasure. | yes |
| Block candidate success | A flagged sanity check means PHASS deramping cannot count as successful. | |

**User's choice:** Block production recommendation only.
**Notes:** Preserves honest candidate metrics while preventing science-unsafe production recommendation.

---

## Failure Evidence Shape

### What counts as a valid candidate outcome?

| Option | Description | Selected |
|--------|-------------|----------|
| PASS / FAIL / BLOCKER | Candidate-cell result must land in one of these three states with sidecar evidence. | yes |
| Numeric metrics only | Just record r/bias/RMSE/ramp stats and let Phase 12 interpret. | |
| Detailed prose conclusions | Human-readable conclusion sections are enough. | |

**User's choice:** PASS / FAIL / BLOCKER.
**Notes:** Structured sidecars carry the canonical result.

### What should a BLOCKER include at minimum?

| Option | Description | Selected |
|--------|-------------|----------|
| Stage + error + evidence path | Candidate name, cell, failed stage, exception/error summary, logs/artifact paths, and whether cached inputs were valid. | yes |
| Full debug bundle | Everything above plus environment dump, command transcript, dependency versions, and intermediate file inventory. | |
| Short reason code only | Keep it compact; details can live in conclusions. | |

**User's choice:** Stage + error + evidence path.
**Notes:** Enough for audit and replanning without bloating every sidecar.

### Should partial results be preserved when a candidate blocks after producing some outputs?

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve partial metrics | Store whatever schema-valid partial IFG/ramp/reference metrics exist, clearly marked partial. | yes |
| Discard partials | Blocker sidecar only, to avoid misleading comparisons. | |
| Keep only logs | No partial metric schema, just paths to artifacts. | |

**User's choice:** Preserve partial metrics.
**Notes:** Partial structured evidence is useful for the next plan as long as it is clearly marked.

### Where should candidate results be surfaced?

| Option | Description | Selected |
|--------|-------------|----------|
| Sidecars + conclusions + matrix hint | Canonical sidecars, explanatory conclusion sections, and compact matrix status/hint. | yes |
| Sidecars + conclusions only | Keep the matrix unchanged until Phase 12. | |
| Sidecars only | Avoid doc churn in Phase 11. | |

**User's choice:** Sidecars + conclusions + matrix hint.
**Notes:** Phase 12 should be able to consume candidate status without reinterpreting logs.

---

## the agent's Discretion

- Exact schema field names and helper/module split are left to downstream research and planning.
- Exact deformation-signal sanity-check method is left to planning, provided it is explicit enough for Phase 12 production-posture review.

## Deferred Ideas

None - discussion stayed within Phase 11 scope.
