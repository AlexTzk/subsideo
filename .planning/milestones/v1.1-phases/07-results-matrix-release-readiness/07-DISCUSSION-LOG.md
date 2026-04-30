# Phase 7: Results Matrix + Release Readiness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 7-results-matrix-release-readiness
**Areas discussed:** RTC:NAM RUN_FAILED gap, TrueNAS Linux audit scope, validation_methodology.md finalization, CALIBRATING cells at milestone close

---

## RTC:NAM RUN_FAILED gap

| Option | Description | Selected |
|--------|-------------|----------|
| Fix run_eval.py — migrate it | Add metrics.json + meta.json writes to run_eval.py, re-run, populate with real numbers. REL-01 + REL-05 satisfied for all 10 cells with live data. | |
| Annotate as accepted — add DEFERRED row note | Write eval-rtc/metrics.json with cell_status='DEFERRED' + unblock_condition. Matrix renders DEFERRED (not RUN_FAILED). | ✓ |
| Accept RUN_FAILED as FAIL | Leave as-is — violates REL-05. | |

**User's choice:** Annotate as accepted — DEFERRED sidecar
**Notes:** N.Am. RTC was not the focus of v1.1; EU RTC (Phase 2) was the target. Unblock condition: v1.2 N.Am. RTC re-run.

**Follow-up — unblock condition:**

| Option | Description | Selected |
|--------|-------------|----------|
| v1.2 milestone | Unblock at v1.2 N.Am. RTC harness migration. | ✓ |
| On-demand | Any time run_eval.py is migrated — non-blocking. | |

---

## TrueNAS Linux audit scope

**Clarification from user:** User asked whether REL-04 was about running all evals on Linux or just tasks that couldn't run on ARM64. Clarified that REL-04's "warm-env < 10 min" clause only makes sense with cached sidecars — a full scratch re-run on Linux was not the intent.

| Option | Description | Selected |
|--------|-------------|----------|
| Env builds + matrix renders | Prove lockfile + Dockerfile produce working Linux env; make eval-all runs with cached sidecars; matrix.md regenerates. No heavy eval re-runs. | |
| Full eval re-run on Linux | Actually re-run all evals from scratch on TrueNAS Linux x86-64. | |
| Skip TrueNAS — macOS-only for v1.1 | Defer REL-04 entirely; document as deferred-with-dated-unblock. | ✓ |

**User's choice:** Skip TrueNAS — macOS-only for v1.1
**Notes:** Dockerfile, Apptainer.def, env.lockfile.{osx-arm64,linux-64}.txt already exist (Phase 1 plan 01-09). Homelab not available for v1.1 closure. v1.2 unblock.

---

## validation_methodology.md finalization

**Codebase check performed:** Read docs/validation_methodology.md §2.6 cross-reference table. Confirmed that two REL-03 required findings were listed as deferred to Phase 4/5 and never written: (1) "Cross-sensor precision-first framing (OPERA DIST vs EFFIS) — Phase 5 will append" and (2) "OPERA frame selection by exact UTC hour — Phase 4 harness-first discipline will document".

| Option | Description | Selected |
|--------|-------------|----------|
| Items 2+3 are in the doc — just need a TOC | Already covered somewhere in §2–§4. Phase 7 adds TOC only. | |
| Items 2+3 need new content in Phase 7 | Write dedicated subsections for precision-first framing and UTC-hour selection, then add TOC. | |
| Check the doc first, decide after | Scan doc then decide. | ✓ |

**After check:** Items 2+3 are NOT in the doc. §2.6 cross-reference table explicitly lists them as deferred. Phase 7 must write them.

**Follow-up — section substance:**

| Option | Description | Selected |
|--------|-------------|----------|
| Concise policy statements (~1 page each) | Same voice as existing sections: structural argument + policy + code pointer. §6 = OPERA UTC-hour; §7 = precision-first framing. | ✓ |
| Integrate into existing sections | Append to §3 and §4 as subsections — no new top-level sections. | |

---

## CALIBRATING cells at milestone close

| Option | Description | Selected |
|--------|-------------|----------|
| CALIBRATING = satisfies REL-05 as PASS under calibration bar | Cells that pass their CALIBRATING gate are PASS-under-calibration; Phase 7 confirms ≥3 data points and updates binding_after_milestone='v1.2'. | |
| CALIBRATING = deferred — add dated unblock to each cell | Write CALIBRATING cells as deferred-to-BINDING at v1.2 with dated condition. Satisfies REL-05 strict reading. | ✓ |

**Follow-up — matrix render format:**

| Option | Description | Selected |
|--------|-------------|----------|
| Keep italic CALIBRATING label, add unblock note inline | *coh=X CALIBRATING — binds v1.2* | ✓ |
| Switch to PASS* with footnote | coh=X PASS* (CALIBRATING gate; binds v1.2) | |

**Notes:** CSLC has 3 data points (SoCal + Mojave + Iberian) → eligible for v1.2 binding. DISP has 2 (SoCal + Bologna) → needs 3rd AOI; DISP annotation references DISP_UNWRAPPER_SELECTION_BRIEF.md.

---

## Claude's Discretion

- Wave structure and plan count for Phase 7 (planner determines; expected 2-4 small plans)
- Exact content of §6 and §7 (grounded in harness.py + Phase 4/5 CONCLUSIONS by researcher)

## Deferred Ideas

- TrueNAS Linux full eval re-run (REL-04) — deferred to v1.2; infrastructure already committed
- run_eval.py full harness migration for real N.Am. RTC numbers — deferred to v1.2
- DISP 3rd AOI self-consistency (needed for BINDING promotion) — deferred to DISP Unwrapper Selection milestone (v1.2)
