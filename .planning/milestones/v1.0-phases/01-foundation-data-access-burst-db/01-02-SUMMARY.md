---
phase: 01-foundation-data-access-burst-db
plan: 02
subsystem: data-access
tags: [cdse, stac, s3, oauth2, boto3, pystac-client]

requires:
  - "Settings class with cdse_client_id and cdse_client_secret fields (from 01-01)"
provides:
  - "CDSEClient class with OAuth2 auth, STAC search, and S3 download"
  - "CDSE_STAC_URL, CDSE_S3_ENDPOINT, CDSE_TOKEN_URL module constants"
affects: [01-03, 01-04, phase-02]

tech-stack:
  added: [pystac-client, boto3, requests-oauthlib, oauthlib]
  patterns: [lazy-auth, exponential-backoff-retry, centralised-s3-endpoint]

key-files:
  created:
    - src/subsideo/data/cdse.py
    - tests/unit/test_cdse.py
  modified: []

key-decisions:
  - "S3 auth uses client_id/secret directly as AWS credentials, not OAuth2 bearer token -- separate auth mechanisms per CDSE docs"
  - "boto3.client('s3') called in exactly one method (_s3_client) to prevent scattered endpoint misconfiguration"
  - "OAuth2 token fetch is lazy (not at init) to avoid blocking construction and enable credential validation before network calls"

duration: 7min
completed: 2026-04-05
requirements-completed: [DATA-01, DATA-02]
---

# Phase 01 Plan 02: CDSE Data Access Client Summary

**CDSEClient with OAuth2 (requests-oauthlib BackendApplicationClient), STAC 1.1.0 search for S1/S2, and S3 download with exponential-backoff retry**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-05T17:45:55Z
- **Completed:** 2026-04-05T17:52:33Z
- **Tasks:** 1 (TDD: red + green)
- **Files modified:** 2

## Accomplishments

- CDSEClient class implementing full CDSE data access: OAuth2 authentication, STAC catalog search, and S3 download
- OAuth2 uses requests-oauthlib with BackendApplicationClient per D-02 locked decision
- STAC search works identically for SENTINEL-1 and SENTINEL-2 collections (no special-casing)
- S3 download with exponential-backoff retry (2^attempt seconds, capped at 60s) and clear error on exhaustion
- Credential validation with remediation hints pointing to dataspace.copernicus.eu registration
- 16 unit tests covering all behaviors with mocked network calls

## Task Commits

Each task was committed atomically:

1. **TDD Red: Failing tests** - `92bb435` (test)
2. **TDD Green: Implementation** - `004f974` (feat)

## Files Created/Modified

- `src/subsideo/data/cdse.py` - CDSEClient class with OAuth2, STAC search, S3 download, verify_connectivity
- `tests/unit/test_cdse.py` - 16 tests: init, OAuth2, STAC S1/S2 search, S3 download endpoint/retry/path-parsing, credential validation, constants

## Decisions Made

- S3 auth uses client_id/secret directly as AWS access key/secret key (not OAuth2 bearer token) -- CDSE S3 and CDSE OAuth2 are separate auth mechanisms
- boto3.client("s3") is called in exactly one method (_s3_client) to centralise the non-standard endpoint configuration and prevent the most common CDSE integration failure
- OAuth2 token fetch is lazy (triggered by _get_token(), not __init__) to allow credential validation before any network activity

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all methods are fully implemented with real logic.

## Issues Encountered

None.

## Next Phase Readiness

- CDSEClient is ready for use by burst DB (01-03) and DEM/orbit modules (01-04)
- Future plans can `from subsideo.data.cdse import CDSEClient, CDSE_STAC_URL, CDSE_S3_ENDPOINT`
- Integration tests (Phase 2+) will use real CDSE credentials to verify end-to-end connectivity
