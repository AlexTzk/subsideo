---
phase: 05-dist-s1-opera-v0-1-effis-eu
plan: "02"
subsystem: validation/effis
tags: [probe, effis, wfs, rest-api, owslib, network, lock, endpoint-discovery]
dependency_graph:
  requires: []
  provides:
    - eval-dist_eu/effis_endpoint_lock.txt
  affects:
    - src/subsideo/validation/effis.py (Plan 05-05)
    - src/subsideo/validation/harness.py (Plan 05-04)
    - eval scripts EVENTS list (Plan 05-07)
tech_stack:
  added:
    - owslib 0.35.0 (pip install into subsideo conda env; Plan 05-04 will add pyproject.toml pin)
  patterns:
    - EFFIS REST API (DRF-based JSON) replaces planned WFS approach
    - country + firedate__gte/lte filter pattern for event-scoped queries
key_files:
  created:
    - eval-dist_eu/effis_endpoint_lock.txt
  modified: []
decisions:
  - "Adopt EFFIS REST API (api.effis.emergency.copernicus.eu) instead of WFS -- both WFS candidates failed (Candidate A: ReadTimeout; Candidate B: DNS NXDOMAIN). REST API returns HTTP 200 with 117,334 records and supports country + firedate DRF filters."
  - "Greece country code is EL not GR in the EFFIS REST API -- critical for Evros 2023 query."
  - "intersects WKT geometry filter returns 403 Forbidden (WAF-blocked) -- use country + date range filter instead."
metrics:
  duration: "19 minutes"
  completed_date: "2026-04-25T23:22:35Z"
  tasks_completed: 3
  tasks_total: 3
  files_created: 1
  files_modified: 0
---

# Phase 05 Plan 02: EFFIS Endpoint Probe Summary

## One-liner

EFFIS WFS endpoints both unreachable (ReadTimeout + DNS NXDOMAIN); adopted REST API at `api.effis.emergency.copernicus.eu/rest/2/burntareas/current/` — all three Phase-5 events confirmed with 231/36/86 burnt-area features respectively.

## Tasks Completed

| # | Name | Commit | Status |
|---|------|--------|--------|
| 1 | Verify owslib + init lock header | b12c34b | Done |
| 2 | GetCapabilities probe + smoke test | 4ddefb4 | Done |
| 3 | checkpoint:human-verify | — | **APPROVED** (REST pivot accepted by user 2026-04-25) |

## Endpoint Probe Results

### WFS Candidates (both failed)

**Candidate A:** `https://maps.effis.emergency.copernicus.eu/effis`
- DNS resolves to `99.81.131.106`
- HEAD request to GetCapabilities URL returns HTTP 200
- Full GetCapabilities XML body: ReadTimeout at 30s, 60s, and 90s (owslib + streaming)
- Server accepts connections but response body too slow / server-side throttle

**Candidate B:** `http://geohub.jrc.ec.europa.eu/effis/wfs`
- DNS: `NXDOMAIN` — `geohub.jrc.ec.europa.eu` no longer resolves
- JRC appears to have decommissioned this endpoint

### REST API (adopted as primary)

**Endpoint:** `https://api.effis.emergency.copernicus.eu/rest/2/burntareas/current/`
- HTTP 200, Content-Type: application/json
- 117,334 total records
- Supported filters (from OPTIONS): `country`, `ordering`, `firedate__gte`, `firedate__lte`
- Feature fields: `id`, `centroid`, `bbox`, `shape`, `country`, `countryful`, `province`, `commune`, `firedate`, `area_ha`, `broadlea`, `conifer`, `mixed`, `scleroph`, `transit`, `othernatlc`, `agriareas`, `artifsurf`, `otherlc`, `percna2k`, `lastupdate`, `lastfiredate`, `noneu`

### Smoke Test Results

| Event | Country | Date Window | Feature Count | Top Province | Top area_ha |
|-------|---------|-------------|---------------|--------------|-------------|
| aveiro_2024 | PT | 2024-09-08..2024-10-02 | 231 | Região de Aveiro | 23,318 |
| evros_2023 | EL | 2023-08-12..2023-09-15 | 36 | Έβρος | 96,610 |
| spain_culebra_2022 | ES | 2022-06-08..2022-06-30 | 86 | Zamora | 28,046 |

All three events confirmed. Feature counts and province names match known fire locations.

### Critical Discovery: Greece Country Code

The EFFIS REST API uses `EL` for Greece, not `GR`. `country=GR` returns 0 features. `country=EL` returns 2,430 Greek fire records. This is non-obvious and must be hardcoded in `effis.py` (Plan 05-05).

### intersects Filter Warning

The `intersects` WKT geometry filter returns `403 Forbidden` (CDN/WAF blocks complex query strings). Downstream code must use `country + firedate__gte/lte` instead of spatial filtering.

## Downstream Constants (from lock file)

```python
EFFIS_REST_URL = "https://api.effis.emergency.copernicus.eu/rest/2/burntareas/current/"
EFFIS_DATE_PROPERTY = "firedate"
EFFIS_DATE_GTE_PARAM = "firedate__gte"
EFFIS_DATE_LTE_PARAM = "firedate__lte"
EFFIS_COUNTRY_PARAM = "country"
EFFIS_COUNTRY_PT = "PT"   # Portugal
EFFIS_COUNTRY_EL = "EL"   # Greece (NOT "GR")
EFFIS_COUNTRY_ES = "ES"   # Spain
```

## Deviations from Plan

### Structural change: WFS replaced by REST API

**Found during:** Task 2
**Issue:** Both WFS candidates failed — Candidate A (maps.effis.emergency.copernicus.eu) times out on GetCapabilities XML body despite HEAD returning 200; Candidate B (geohub.jrc.ec.europa.eu) has DNS NXDOMAIN (JRC endpoint decommissioned).
**Fix:** Discovered and probed the EFFIS REST API at `api.effis.emergency.copernicus.eu`. All three Phase-5 events return substantial feature counts with correct province names. Lock file documents both the WFS failure and the REST API as the adopted endpoint.
**Impact on downstream plans:**
- Plan 05-04 (harness retry): retry policy should use `requests.HTTPError` / `ConnectionError` patterns rather than owslib WFS exceptions; the REST API is more stable than WFS.
- Plan 05-05 (effis.py): implement REST API client, not owslib WFS. `firedate` property confirmed. `intersects` filter 403-blocked — use `country + date range` filter.
- Plan 05-07 (EVENTS list): country codes are `PT`, `EL`, `ES` (not `GR`).
**Commit:** 4ddefb4

### Auto-fixed: date window expanded for smoke test

The plan specified strict event date ranges (Aveiro 2024-09-15..09-25, Evros 2023-08-19..09-08, Spain 2022-06-15..06-22). Expanded to +/- 7 days to account for MODIS detection lag as instructed in the plan's fallback note. All events still returned clearly correct features.

## Checkpoint State

This plan is `autonomous: false`. Execution paused at Task 3 (checkpoint:human-verify). The lock file at `eval-dist_eu/effis_endpoint_lock.txt` requires user review before downstream plans read from it.

**What to review:** The chosen endpoint is the REST API (not WFS). Plans 05-04, 05-05, and 05-07 will need to implement a REST client rather than owslib WFS. The probe summary block documents the exact URL, filter syntax, and country codes.

## Self-Check

### Created files exist
- eval-dist_eu/effis_endpoint_lock.txt: EXISTS

### Commits exist
- b12c34b: EXISTS (chore(05-02): verify owslib 0.35.0 and initialise EFFIS endpoint lock header)
- 4ddefb4: EXISTS (feat(05-02): complete EFFIS endpoint probe and write lock artifact)

## Self-Check: PASSED
