---
phase: 05-dist-s1-opera-v0-1-effis-eu
plan: "04"
subsystem: validation/harness
tags: [harness, retry-policy, owslib, additive, pyproject, EFFIS]
completed: "2026-04-25T23:05:37Z"
duration: "~8 minutes"

dependency_graph:
  requires:
    - "05-02 (effis_endpoint_lock.txt — confirmed public endpoint)"
  provides:
    - "RETRY_POLICY['EFFIS'] — consumed by Plan 05-05 effis.py and Plan 05-07 run_eval_dist_eu.py"
    - "owslib>=0.35,<1 pip pin — consumed by any fresh pip install -e .[validation,viz]"
  affects:
    - "src/subsideo/validation/harness.py"
    - "pyproject.toml"

tech_stack:
  added: []
  patterns:
    - "RETRY_POLICY dict extension — additive key, no dispatch body changes"
    - "Literal type alias extension — RetrySource now covers 5 sources"
    - "pyproject.toml pip-layer extras — owslib in validation group, not conda-env.yml"

key_files:
  created: []
  modified:
    - src/subsideo/validation/harness.py
    - pyproject.toml

decisions:
  - "EFFIS retry_on includes both HTTP codes (429/503/504) AND symbolic strings ('ConnectionError'/'TimeoutError') because owslib raises transport failures from urllib3 as Python exceptions rather than HTTP status codes"
  - "504 added beyond the EARTHDATA shape because EFFIS MapServer can take 30+s for large bbox + date-window WFS queries (RESEARCH Probe 3 Risk F)"
  - "owslib goes in pip layer (pyproject.toml), not conda-env.yml, per CLAUDE.md two-layer rule — owslib 0.35.0 is noarch pure-Python"
  - "download_reference_with_retry body left entirely unchanged — the RETRY_POLICY.get(source) dispatch handles the new EFFIS key transparently (CR-02 mitigation honored)"

metrics:
  duration: "~8 minutes"
  completed: "2026-04-25"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
  files_created: 0
---

# Phase 05 Plan 04: Add RETRY_POLICY['EFFIS'] and owslib pin — Summary

**One-liner:** EFFIS WFS retry policy (5th source, owslib transport-error-aware) added to harness + owslib>=0.35,<1 pinned in validation extras.

## What Landed

### Task 1 — RETRY_POLICY['EFFIS'] entry + RetrySource Literal extension

Two surgical edits to `src/subsideo/validation/harness.py`:

**Edit 1 — RetrySource Literal extended:**

```python
# Before
RetrySource = Literal["CDSE", "EARTHDATA", "CLOUDFRONT", "HTTPS"]

# After
RetrySource = Literal["CDSE", "EARTHDATA", "CLOUDFRONT", "HTTPS", "EFFIS"]
```

**Edit 2 — EFFIS entry appended as 5th key in RETRY_POLICY dict:**

```python
"EFFIS": {
    # Phase 5 DIST-05 EFFIS WFS access. Public endpoint (no auth) but
    # owslib raises ConnectionError / TimeoutError from urllib3 rather
    # than HTTP status codes for transport-layer failures, so both kinds
    # appear in retry_on. 504 is added because EFFIS MapServer responses
    # can take 30+s for large bbox + date-window queries (RESEARCH Probe
    # 3 Risk F). The abort_on triplet 401/403/404 mirrors EARTHDATA: 401
    # is impossible on a public endpoint but is included for parity in
    # case the WFS server starts requiring tokens; 404 catches typo'd
    # typenames (chosen layer name from eval-dist_eu/effis_endpoint_lock.txt
    # is locked at Plan 05-05 / 05-07; runtime drift surfaces as 404
    # rather than infinite retry).
    "retry_on": [429, 503, 504, "ConnectionError", "TimeoutError"],
    "abort_on": [401, 403, 404],
},
```

**Rationale for EFFIS shape beyond EARTHDATA:**

| Code / Symbol | Rationale |
|---|---|
| 429 | Rate-limit — EFFIS MapServer is shared public infrastructure |
| 503 | Server overload — standard retry |
| 504 | Gateway timeout — EFFIS MapServer takes 30+ s for large bbox + date-window (RESEARCH Probe 3 Risk F) |
| "ConnectionError" | owslib raises `urllib3.exceptions.ConnectionError` as a Python exception, not an HTTP status, for TCP-layer failures |
| "TimeoutError" | owslib raises `urllib3.exceptions.TimeoutError` for read/connect timeouts beyond the requests timeout parameter |
| 401 abort | Parity with EARTHDATA; EFFIS is public but included in case future token requirement surfaces |
| 403 abort | Standard auth-forbidden abort |
| 404 abort | Catches typo'd WFS typenames — surfaces as a fast abort rather than infinite retry |

**`download_reference_with_retry` body — ZERO changes:**
The existing dispatch at harness.py:542 (`if source not in RETRY_POLICY`) plus `policy = RETRY_POLICY[source]` handles the new key transparently. The CR-02 mitigation at lines 588-596 (fail-fast on any 4xx not in retry_on) is preserved without modification.

### Task 2 — owslib>=0.35,<1 pin in pyproject.toml

Single-line addition to `[project.optional-dependencies] validation`:

```toml
"owslib>=0.35,<1",          # Phase 5 EFFIS WFS access (noarch pure-Python; RESEARCH Probe 5)
```

**Version pin rationale:**
- `>=0.35` — first version with stable WFS 2.0.0 + FES 2.0 support (RESEARCH Probe 5; PyPI 0.35.0 published 2025-10-28)
- `<1` — preemptive upper bound; owslib 1.x not yet released as of 2026-04-25

**conda-env.yml NOT modified** — owslib is noarch pure-Python; it belongs in the pip layer installed via `pip install -e .[validation,viz]` (CLAUDE.md two-layer rule: conda-forge for ISCE3/GDAL/dolphin/tophu/snaphu only).

## Verification Results

```
RETRY_POLICY has 5 entries: ['CDSE', 'EARTHDATA', 'CLOUDFRONT', 'HTTPS', 'EFFIS']
EFFIS retry_on: [429, 503, 504, 'ConnectionError', 'TimeoutError']
EFFIS abort_on: [401, 403, 404]
Existing 4 entries byte-identical OK
ruff: All checks passed
owslib present in validation extras OK
conda-env.yml diff: empty (untouched)
git diff --stat HEAD~2 HEAD: 2 files changed, 17 insertions(+), 1 deletion(-)
```

## Commits

| Task | Commit | Message |
|---|---|---|
| 1 | a5cdb0e | feat(05-04): add RETRY_POLICY['EFFIS'] entry and extend RetrySource Literal |
| 2 | a92d149 | chore(05-04): add owslib>=0.35,<1 to pyproject.toml validation extras |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — this plan is purely additive infrastructure (dict entries + pyproject pin). No rendering or data-wiring stubs.

## Threat Flags

No new threat surface introduced. Both edits are read-only data structures at runtime; no new network endpoints, auth paths, or file access patterns added by this plan. EFFIS endpoint URLs are locked in Plan 05-02's artifact and committed in Plan 05-05 module constants (not in this plan).

## Self-Check: PASSED

- [x] `src/subsideo/validation/harness.py` modified — confirmed via `git diff --stat`
- [x] `pyproject.toml` modified — confirmed via `git diff --stat`
- [x] Commit `a5cdb0e` exists — confirmed via git log
- [x] Commit `a92d149` exists — confirmed via git log
- [x] RETRY_POLICY has 5 entries with EFFIS as 5th — verified via Python introspection
- [x] Existing 4 entries byte-identical — verified via Python assertion
- [x] owslib>=0.35,<1 in validation extras — verified via tomllib
- [x] conda-env.yml untouched — git diff empty
- [x] ruff check passes — all checks passed
