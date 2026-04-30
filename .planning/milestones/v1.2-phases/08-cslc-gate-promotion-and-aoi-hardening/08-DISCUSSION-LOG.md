# Phase 8: CSLC Gate Promotion & AOI Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 08-cslc-gate-promotion-and-aoi-hardening
**Areas discussed:** Stable-Terrain Buffer Fix, AOI Probe Regeneration, SAFE Cache Self-Healing, Binding Threshold Rationale, Stale Tests and Shared-Infra Defects

---

## Stable-Terrain Buffer Fix

| Option | Description | Selected |
|--------|-------------|----------|
| Surgical fix | Preserve existing defaults, fix CRS/projection handling, and add regression tests across at least two UTM zones. | |
| Fix + diagnostics | Do the surgical fix, plus emit stable-mask retention metrics for SoCal/Mojave/Iberian so threshold changes are explainable. | yes |
| Fix + diagnostics + artifacts | Also regenerate or commit visual sanity artifacts such as stable-mask-over-basemap and coherence histograms. | |
| You decide | Let the planner choose the smallest version that satisfies CSLC-08. | |

**User's choice:** Fix + diagnostics.
**Notes:** Preserve current defaults (`5 km` coast, `500 m` water). Add retention metrics so SoCal coastal stable-pixel changes and threshold evidence are auditable. Visual artifacts remain optional unless needed.

---

## AOI Probe Regeneration

| Option | Description | Selected |
|--------|-------------|----------|
| Full regeneration | Regenerate the entire probe artifact from live acquisition searches: SoCal, all Mojave fallbacks, Iberian, and at least two EU fallback AOIs. | yes |
| Targeted repair | Replace fabricated tuples for existing active AOIs and validate only two new EU fallbacks; leave unused Mojave fallback ordering mostly intact. | |
| Evidence-first probe | Make the probe artifact the main deliverable with search parameters, rejected candidates, reasons, and selected sensing windows. | |
| You decide | Planner picks the minimum path that satisfies CSLC-09. | |

**User's choice:** Full regeneration.
**Notes:** Downstream planning should treat the regenerated artifact as a clean source of truth rather than patching around v1.1 candidate rows.

---

## SAFE Cache Self-Healing

| Option | Description | Selected |
|--------|-------------|----------|
| Central harness guard | Add a shared helper in `validation/harness.py`, then call it from CSLC/DISP/RTC eval setup before readers consume a SAFE. | |
| Downloader-level guard | Make the download function validate archive completeness and only expose complete files. | |
| Both layers | Downloader writes atomically and validates, while harness/eval setup also checks existing cached files before reuse. | yes |
| You decide | Planner chooses based on least disruption. | |

**User's choice:** Both layers.
**Notes:** New downloads and old cached SAFEs should both be protected. Treat this as shared infrastructure, not a one-script patch.

---

## Binding Threshold Rationale

| Option | Description | Selected |
|--------|-------------|----------|
| Conservative binding proposal | Propose coherence `>= 0.75` and residual `<= 2.0 mm/yr`, justified as below weakest v1.1 coherence but tighter than CALIBRATING residual `5.0`. | yes |
| Aggressive binding proposal | Propose coherence `>= 0.80` and residual `<= 1.5 mm/yr`, close to the weakest observed v1.1 datapoint. | |
| Researcher decides after diagnostics | Phase 8 presents v1.1 and v1.2 values, but downstream research/planning decides exact thresholds. | |
| You decide | Planner picks a proposal. | |

**User's choice:** Conservative binding proposal.
**Notes:** Use v1.1 values as the rationale base: SoCal `0.887` / `-0.109 mm/yr`, Mojave `0.804` / `+1.127 mm/yr`, Iberian `0.868` / `+0.347 mm/yr`. Phase 8 proposes; Phase 9 reruns and promotes.

---

## Stale Tests and Shared-Infra Defects

| Option | Description | Selected |
|--------|-------------|----------|
| Fix real behavior, relax stale structure | Regression-test and fix CR-01/CR-02/HI-01; update or relax stale tests if useful, otherwise remove with documented rationale. | yes |
| Make all existing tests pass | Preserve both stale tests and force implementation/script structure to satisfy them. | |
| Replace stale tests with better invariants | Delete both stale tests and add new tests around regenerated AOI artifact, fallback semantics, and script parity where it matters. | |
| You decide | Planner picks the safest cleanup path. | |

**User's choice:** Fix real behavior, relax stale structure.
**Notes:** Keep behavioral coverage, but do not force accidental v1.1 script shape. CR-01/CR-02/HI-01 need real regression tests.

---

## the agent's Discretion

- Exact retention metrics layout.
- Whether visual sanity artifacts are needed.
- Exact helper split for downloader-level and harness-level SAFE validation.
- Exact stale-test replacement or relaxation strategy once regenerated probe behavior is known.

## Deferred Ideas

None.
