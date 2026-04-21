# Phase 2: RTC-S1 and CSLC-S1 Pipelines - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 02-rtc-s1-and-cslc-s1-pipelines
**Areas discussed:** RTC Pipeline Wrapping, CSLC Pipeline Wrapping, Validation Architecture, Output Compliance
**Mode:** auto (all areas auto-selected with recommended defaults)

---

## RTC Pipeline Wrapping Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Thin Python API wrapper around opera-rtc | Call opera-rtc's Python API directly for spec-compliant output | ✓ |
| Subprocess/CLI invocation of opera-rtc | Shell out to opera-rtc CLI | |
| Reimplement RTC from raw isce3 calls | Build RTC from isce3 primitives | |

**User's choice:** [auto] Thin Python API wrapper (recommended default)
**Notes:** opera-rtc is the OPERA-ADT reference; wrapping its API gives spec compliance with minimal code duplication.

---

## CSLC Pipeline Wrapping Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Config-driven compass via Python API | Generate YAML runconfig, call compass entry point | ✓ |
| Direct isce3 burst coregistration calls | Use isce3 primitives without compass | |
| Subprocess compass CLI | Shell out to compass command-line | |

**User's choice:** [auto] Config-driven compass execution (recommended default)
**Notes:** compass uses YAML runconfig matching ISCE3 convention already adopted in Phase 01 config system.

---

## Validation Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Shared metrics + per-product comparators | metrics.py for reusable functions, compare_*.py per product | ✓ |
| Monolithic compare module | Single module handling all product comparisons | |
| Validation as part of product modules | Embed validation in products/rtc.py, products/cslc.py | |

**User's choice:** [auto] Shared metrics + per-product comparators (recommended default)
**Notes:** Extensible pattern — Phase 3/4 products add their own compare_*.py modules reusing the same metrics.

---

## Output Format Compliance

| Option | Description | Selected |
|--------|-------------|----------|
| opera-utils + rio-cogeo with post-hoc validation | Use OPERA tooling for writing, validate after | ✓ |
| Schema-driven write-time validation | Validate against spec schema during write | |
| Delegating entirely to opera-rtc/compass output | Trust upstream tool output without checking | |

**User's choice:** [auto] Write with OPERA tools + post-hoc validation check (recommended default)
**Notes:** Belt-and-suspenders: use opera-utils/rio-cogeo for correct structure, then validate_product() confirms compliance.

---

## Claude's Discretion

- Internal helper organization within products/ and validation/
- Test fixture design (synthetic arrays, mocked HDF5/COG)
- Error message formatting for pipeline failures
- numpy vs xarray for intermediate operations

## Deferred Ideas

None
