# Phase 3: DISP-S1 and DIST-S1 Pipelines - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 03-disp-s1-and-dist-s1-pipelines
**Areas discussed:** DISP pipeline orchestration, EGMS validation approach, DIST-S1 integration, Unwrapping quality control

---

## DISP Pipeline Orchestration

| Option | Description | Selected |
|--------|-------------|----------|
| Single orchestrator | One products/disp.py with run_disp() chaining CSLC→dolphin→tophu→MintPy | ✓ |
| Staged orchestrator | Separate entry points for each stage | |
| You decide | Claude picks best approach | |

**User's choice:** Single orchestrator (Recommended)
**Notes:** Matches RTC/CSLC pattern from Phase 2

---

| Option | Description | Selected |
|--------|-------------|----------|
| Directory of CSLC HDF5 files | User provides directory, pipeline discovers and orders | |
| Explicit file list | User provides ordered list of paths | |
| AOI + date range (end-to-end) | Full automation: AOI+dates → CSLC → dolphin → tophu → MintPy | ✓ |

**User's choice:** AOI + date range (end-to-end)
**Notes:** Full automation preferred

---

| Option | Description | Selected |
|--------|-------------|----------|
| Optional with warning | Apply ERA5 if credentials exist, warn and skip otherwise | |
| Mandatory | Fail if CDS credentials missing | ✓ |
| Always skip | Don't integrate ERA5 correction | |

**User's choice:** Mandatory
**Notes:** ERA5 tropospheric correction required for scientific accuracy

---

## EGMS Validation Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Ortho | Vertical + E-W displacement maps on regular grid (GeoTIFF) | ✓ |
| Calibrated | LOS velocity per PS/DS point, calibrated to GNSS | |
| Basic | Raw LOS velocity per point, uncalibrated | |

**User's choice:** Ortho (Recommended)
**Notes:** Easiest to compare against geocoded output

---

| Option | Description | Selected |
|--------|-------------|----------|
| Compare vertical component only | Project LOS to vertical via incidence angle | ✓ |
| Full decomposition | Combine asc+desc to decompose vertical + E-W | |
| Raw LOS comparison | Compare LOS directly against matching geometry | |

**User's choice:** Compare vertical component only (Recommended)
**Notes:** Standard approach in literature, simpler

---

| Option | Description | Selected |
|--------|-------------|----------|
| Use EGMStoolkit | EGMStoolkit 0.2.15 for download, already in tech stack | ✓ |
| Direct HTTP download | Manual download and parsing | |

**User's choice:** Use EGMStoolkit (Recommended)

---

## DIST-S1 Integration

| Option | Description | Selected |
|--------|-------------|----------|
| Implement now, conditional import | Full wrapper with lazy import, clear error if missing | ✓ |
| Stub only | Interface + types only, TODO implementation | |
| Skip DIST-S1 entirely | Move to Phase 4 or later | |

**User's choice:** Implement now, conditional import (Recommended)
**Notes:** dist-s1 conda-forge release expected ~April 2026

---

| Option | Description | Selected |
|--------|-------------|----------|
| Directory of RTC COGs | User provides directory of RTC outputs | |
| AOI + date range (end-to-end) | Full automation matching DISP pattern | ✓ |

**User's choice:** AOI + date range (end-to-end)
**Notes:** Consistent with DISP orchestration pattern

---

## Unwrapping Quality Control

| Option | Description | Selected |
|--------|-------------|----------|
| Automated with flag-and-continue | Flag in HDF5 metadata, don't fail pipeline | ✓ |
| Automated with hard fail | Fail pipeline on anomaly | |
| Log-only | Compute and log only | |

**User's choice:** Automated with flag-and-continue (Recommended)
**Notes:** Allows batch processing while surfacing issues

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, configurable threshold | Pre-mask below coherence threshold (default 0.3) | ✓ |
| Let tophu handle it | Use coherence as weights only | |
| Both options via config | Support both modes | |

**User's choice:** Yes, configurable threshold (Recommended)
**Notes:** Standard InSAR practice, threshold exposed in config

---

## Claude's Discretion

- Internal helper functions for dolphin/tophu/MintPy config generation
- DISPConfig/DISPResult and DISTConfig/DISTResult dataclass design
- Test fixture design for mocked pipeline outputs
- Whether to cache intermediate CSLC/RTC stacks in end-to-end mode
- Error message formatting for multi-stage pipeline failures

## Deferred Ideas

None — discussion stayed within phase scope
