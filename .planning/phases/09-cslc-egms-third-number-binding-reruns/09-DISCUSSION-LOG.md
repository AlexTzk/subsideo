# Phase 9: CSLC EGMS Third Number & Binding Reruns - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 09-cslc-egms-third-number-and-binding-reruns
**Areas discussed:** Binding gate promotion, EGMS L2a residual failure policy, Mojave amplitude sanity disposition, Matrix/result wording, Rerun cost posture

---

## Binding Gate Promotion

| Option | Description | Selected |
|--------|-------------|----------|
| Promote first, then rerun | Update `criteria.py` from CALIBRATING to BINDING using Phase 8's proposed thresholds, then rerun and let matrix output PASS/FAIL against the new gates. | |
| Rerun first, then promote | Keep current CALIBRATING criteria during execution, inspect regenerated metrics, then promote only if reruns support Phase 8's proposal. | |
| Dual-record transition | Keep `criteria.py` conservative during reruns, but write explicit candidate BINDING verdicts, then promote the registry at closure if supported. | yes |
| You decide | Planner can choose the safest implementation path consistent with Phase 8's threshold rationale. | |

**User's choice:** Dual-record transition.
**Notes:** This avoids silently changing the meaning of old sidecars while still letting Phase 9 produce the BINDING decision it exists to produce.

---

## EGMS L2a Residual Failure Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Only current upstream failure | Acceptable blocker only if EGMS access/API/tooling fails currently and the run records exact error, version, request bounds, and retry evidence. | |
| Also low stable-PS support | Acceptable blocker if EGMS downloads work but too few valid stable PS samples remain after filtering/clipping, provided counts and thresholds are written to sidecars. | yes |
| Broader implementation blocker | Acceptable blocker for any adapter/schema/API mismatch, even if it might be fixable in code, as long as documented. | |
| You decide | Planner decides what is a hard blocker versus fixable implementation work. | |

**User's choice:** Also low stable-PS support.
**Notes:** Upstream access failure and scientifically insufficient stable-PS support are legitimate blockers; adapter/schema issues should usually be fixed in Phase 9.

---

## Mojave Amplitude Sanity Disposition

| Option | Description | Selected |
|--------|-------------|----------|
| Try primary only | Attempt OPERA frame match for the selected Mojave/Coso-Searles fallback; if unavailable, document evidence and move on. | |
| Try fallback chain | Attempt amplitude sanity for Coso/Searles, then Pahranagat/Amargosa if the selected runnable fallback changes; document frame-search evidence for each attempted burst. | yes |
| Deep frame search | Spend extra effort searching nearby frames/dates/overlaps beyond the regenerated AOI probe to recover amplitude sanity if possible. | |
| You decide | Planner chooses the effort level. | |

**User's choice:** Try fallback chain.
**Notes:** This aligns amplitude sanity with the regenerated fallback chain without making nearby-frame hunting a new research project.

---

## Matrix/Result Wording

| Option | Description | Selected |
|--------|-------------|----------|
| Strict BINDING only | No CSLC cell leaves CALIBRATING unless every required evidence path is populated and candidate thresholds pass/fail cleanly. | |
| BINDING with named blocker | Cells may leave CALIBRATING and report BINDING PASS/FAIL or BINDING BLOCKER when a required evidence path is unavailable for an accepted reason. | yes |
| Mixed transition wording | Keep matrix as CALIBRATING but add candidate BINDING wording in conclusions until Phase 12 closes the milestone. | |
| You decide | Planner picks wording based on final metrics. | |

**User's choice:** BINDING with named blocker.
**Notes:** Satisfies the roadmap's "no longer read only as CALIBRATING" requirement while preserving scientific honesty when EGMS or amplitude evidence is unavailable.

---

## Rerun Cost Posture

| Option | Description | Selected |
|--------|-------------|----------|
| Warm-cache first | Validate cached intermediates and sidecars, rerun only missing/stale/invalid AOIs. | |
| Force full rerun | Redownload/recompute enough to prove all Phase 9 metrics from fresh execution, even if cached outputs exist. | |
| Hybrid audit rerun | Use cached SAFEs/intermediates after integrity checks, but force recomputation of metrics/sidecars and final matrix/conclusions. | yes |
| You decide | Planner chooses based on cache state. | |

**User's choice:** Hybrid audit rerun.
**Notes:** Phase 8 hardened cache integrity, so reusing cached inputs is reasonable, but Phase 9 verdict-bearing metrics should be regenerated.

---

## the agent's Discretion

- Exact schema shape for candidate BINDING verdict fields.
- Exact implementation split across eval scripts, schema, matrix writer, tests, and conclusions.
- Whether final registry promotion happens in Phase 9 closure or is deferred if evidence is ambiguous.

## Deferred Ideas

None.
