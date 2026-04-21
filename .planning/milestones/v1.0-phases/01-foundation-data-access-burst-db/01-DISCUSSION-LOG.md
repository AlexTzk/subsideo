# Phase 1: Foundation, Data Access & Burst DB - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 01-foundation-data-access-burst-db
**Areas discussed:** CDSE access, EU burst DB, DEM sourcing, Orbit/IONEX sourcing
**Mode:** Auto (all areas auto-selected, recommended defaults chosen)

---

## CDSE Data Access

| Option | Description | Selected |
|--------|-------------|----------|
| pystac-client + boto3 | STAC 1.1.0 search + custom S3 endpoint | ✓ |
| cdse-client wrapper | Thin wrapper over STAC/S3 | |
| sentinelsat / OData | Legacy approach (deprecated Nov 2025) | |

**User's choice:** pystac-client + boto3 (auto: recommended default)
**Notes:** CDSE switched to STAC 1.1.0 in Feb 2025. Legacy OData deprecated. OAuth2 client credentials for auth.

---

## EU Burst Database

| Option | Description | Selected |
|--------|-------------|----------|
| Independent SQLite from ESA GeoJSON | Build EU-scoped DB matching opera-burstdb schema | ✓ |
| Extend opera-burstdb directly | Fork/modify the existing N.Am. DB | |
| Runtime query from ESA API | No local DB, query on demand | |

**User's choice:** Independent SQLite from ESA GeoJSON (auto: recommended default)
**Notes:** opera-burstdb is operationally N.Am.-scoped. Same schema enables interop. Cache at ~/.subsideo/.

---

## DEM Sourcing

| Option | Description | Selected |
|--------|-------------|----------|
| dem-stitcher (glo_30) | Purpose-built library with auto height conversion | ✓ |
| Custom tile management | Manual download/mosaic/warp pipeline | |
| OpenTopography API | Cloud-based DEM serving | |

**User's choice:** dem-stitcher (auto: recommended default)
**Notes:** Handles variable longitudinal spacing at high latitudes. Warp to UTM 30m before ISCE3 ingestion.

---

## Orbit/IONEX Sourcing

| Option | Description | Selected |
|--------|-------------|----------|
| sentineleof (primary) + s1-orbits (fallback) | isce-framework maintained + AWS backup | ✓ |
| s1-orbits only | AWS-backed, faster | |
| Custom ESA POD download | Direct HTTP from ESA | |

**User's choice:** sentineleof primary + s1-orbits fallback (auto: recommended default)
**Notes:** IONEX from CDDIS with Earthdata auth. Same credentials as ASF DAAC.

---

## Claude's Discretion

- Internal module structure within data/ and burst/
- Error message formatting and logging verbosity
- Test fixture design for mocked responses

## Deferred Ideas

None — discussion stayed within phase scope
