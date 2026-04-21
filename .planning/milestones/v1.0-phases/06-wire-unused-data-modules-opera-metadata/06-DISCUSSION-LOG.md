# Phase 6: Wire Unused Data Modules & OPERA Metadata - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 06-wire-unused-data-modules-opera-metadata
**Areas discussed:** IONEX wiring, ASF auto-fetch, Metadata injection scope, Credential sourcing
**Mode:** --auto (all decisions auto-selected)

---

## IONEX Wiring into CSLC

| Option | Description | Selected |
|--------|-------------|----------|
| Inside run_cslc_from_aoi, after orbit fetch | Keeps data-fetch-then-process ordering consistent | ✓ |
| Inside run_cslc, as parameter | Would require callers to handle IONEX themselves | |

**User's choice:** [auto] Inside run_cslc_from_aoi, after orbit fetch (recommended default)

| Option | Description | Selected |
|--------|-------------|----------|
| From SubsideoSettings | Reuses existing config pattern | ✓ |
| Separate env vars | Adds config complexity | |

**User's choice:** [auto] From SubsideoSettings (recommended default)

| Option | Description | Selected |
|--------|-------------|----------|
| Warn and continue (tec_file=None) | Ionospheric correction is optional refinement | ✓ |
| Fail pipeline | Strict but blocks usage without Earthdata credentials | |

**User's choice:** [auto] Warn and continue (recommended default)

---

## ASF Auto-Fetch in Validate CLI

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-fetch when --reference omitted | Matches SC-2 success criteria | ✓ |
| Always require --reference | Simpler but less convenient | |

**User's choice:** [auto] Auto-fetch when --reference omitted (recommended default)

| Option | Description | Selected |
|--------|-------------|----------|
| RTC and CSLC only | DISP/DSWx/DIST have different reference sources | ✓ |
| All product types | Would require OPERA references for all types | |

**User's choice:** [auto] RTC and CSLC only (recommended default)

---

## Metadata Injection Scope

| Option | Description | Selected |
|--------|-------------|----------|
| After product write, before return | Same pattern as DSWx | ✓ |
| Inside each format-specific writer | Would couple metadata to I/O layer | |

**User's choice:** [auto] After product write, before return (recommended default)

| Option | Description | Selected |
|--------|-------------|----------|
| importlib.metadata.version("subsideo") | Standard Python, works with hatch-vcs | ✓ |
| Hardcoded version string | Fragile, requires manual updates | |

**User's choice:** [auto] importlib.metadata.version (recommended default)

---

## Credential Sourcing

| Option | Description | Selected |
|--------|-------------|----------|
| SubsideoSettings for all Earthdata creds | Unified config, consistent with Phase 5 | ✓ |
| Separate config per module | Adds complexity without benefit | |

**User's choice:** [auto] SubsideoSettings (recommended default)

---

## Claude's Discretion

- How to extract bbox/datetime from product files for ASF search matching
- Error message wording for missing credentials
- Whether to add a shared helper for version string or inline it
- Exact run_params dict contents per product type

## Deferred Ideas

None — discussion stayed within phase scope.
