---
phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
plan: 01
subsystem: infra
tags: [conda, micromamba, conda-forge, numpy, isce3, tophu, dist-s1, py-spy, rio-cogeo, env-yml, two-layer-install]

# Dependency graph
requires: []
provides:
  - Two-layer `conda-env.yml` manifest at repo root (conda-forge heavies + pip editable install of subsideo[validation,viz] + rio-cogeo==6.0.0)
  - `numpy>=1.26,<2.0` pin (foundation for Plan 01-03 cslc.py monkey-patch removal)
  - `tophu=0.2.1` under conda-forge dependencies (foundation for Plan 01-02 tophu regression test)
  - `dist-s1=2.0.14` bump from currently-installed 2.0.13
  - `py-spy=0.4.1` conda-forge entry (foundation for Plan 01-07 watchdog)
  - `rio-cogeo==6.0.0` pip pin (foundation for Plan 01-04 `_cog.py` helper)
  - Sunset conditions header documenting re-evaluation triggers
  - Audit artifact: dry-run solver output capturing pin-availability conflicts on osx-arm64
affects:
  - Plan 01-02 (tophu regression test consumes conda-forge entry)
  - Plan 01-03 (numpy<2 pin lets cslc.py monkey-patches be deleted)
  - Plan 01-04 (`_cog.py` helper pins through conda-env rio-cogeo 6.0.0)
  - Plan 01-07 (watchdog depends on py-spy conda-forge entry)
  - Plan 01-09 (per-platform lockfiles + Dockerfile consume this manifest)

# Tech tracking
tech-stack:
  added:
    - "conda-env.yml two-layer manifest (new file at repo root)"
    - "py-spy=0.4.1 dep (new to project; conda-env only per D-15)"
  patterns:
    - "Sunset-comment header at top of env manifest enumerating pin-removal triggers"
    - "Two-layer install pattern: conda-forge heavies + trailing `pip: -e .[validation,viz]` section consuming pyproject extras"

key-files:
  created:
    - "conda-env.yml"
    - ".planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/01-01-dryrun.txt"
  modified: []

key-decisions:
  - "Authored conda-env.yml exactly as specified in PLAN.md Task 1 (contents verbatim) rather than pre-emptively relaxing pins; the plan's explicit instruction is 'stop and report — do NOT relax pins without ADR'"
  - "Captured dry-run solver failure as an audit artifact (01-01-dryrun.txt committed to phase dir; `.log` was gitignored) so downstream plan/orchestrator can act on exact pin-conflict list without re-running the probe"

patterns-established:
  - "Pattern: Sunset-comment header on env manifest listing numpy<2 / rio-cogeo==6.0.0 / tophu conda-channel sunset triggers — enables future maintainers to know when each pin can be lifted"
  - "Pattern: pyproject.toml stays the single source of truth for pip deps; conda-env.yml consumes it via `-e .[validation,viz]` rather than duplicating pin lists"

requirements-completed: [ENV-01, ENV-02, ENV-09, ENV-10]

# Metrics
duration: 6min
completed: 2026-04-22
---

# Phase 01 Plan 01: Two-Layer conda-env.yml Manifest Summary

**Authored the canonical two-layer `conda-env.yml` at repo root matching the plan spec verbatim (conda-forge heavies + pip layer with `-e .[validation,viz]` and `rio-cogeo==6.0.0`), and ran the solver dry-run which surfaced six distinct pin-availability conflicts on osx-arm64 — documented as an audit artifact per the plan's 'stop and report' directive.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-04-22T14:04:45Z
- **Completed:** 2026-04-22T14:13:29Z
- **Tasks:** 2 (both attempted; Task 1 succeeded, Task 2 produced the expected 'stop-and-report' signal)
- **Files created:** 2 (`conda-env.yml` + dry-run audit `01-01-dryrun.txt`)

## Accomplishments

- Wrote `conda-env.yml` at repo root (73 lines) exactly matching PLAN.md Task 1 specification — no pins changed, no extra deps, no CUDA layer, no conda-lock directives.
- All 9 grep-based acceptance criteria pass (numpy/tophu/dist-s1/py-spy/rio-cogeo pins present, `-e .[validation,viz]` under pip layer, no duplicate tophu, no CUDA strings, pyproject.toml untouched).
- Automated YAML assertion (parse + all pin checks) passes cleanly.
- Dry-run solver log captured as `.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/01-01-dryrun.txt` for downstream use (renamed from `.log` because repo `.gitignore` excludes `*.log`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Write conda-env.yml with two-layer pinning** — `f0c2241` (feat)
2. **Task 2: Validate conda-env.yml solves on macOS arm64 (dev machine acceptance)** — read-only verification task; no file writes expected per plan contract, so no separate commit. Audit artifact (`01-01-dryrun.txt`) is attached to this SUMMARY's metadata commit.

**Plan metadata:** _(to be added by final docs commit below)_

## Files Created/Modified

- `conda-env.yml` (new, 73 lines) — Two-layer environment manifest at repo root. Conda-forge deps: Python 3.11, numpy 1.26-<2.0, isce3=0.25.10, compass=0.5.6, s1reader=0.2.5, dolphin=0.42.5, tophu=0.2.1, snaphu-py=0.4.1, mintpy=1.6.3, dist-s1=2.0.14, gdal/rasterio/rioxarray/geopandas/shapely/pyproj/xarray/h5py/scikit-image, dem-stitcher, sentineleof, pyaps3, cdsapi, pytest+pytest-cov+pytest-mock, ruff+mypy+pre-commit, py-spy=0.4.1. Pip layer: `-e .[validation,viz]` + `rio-cogeo==6.0.0`. Sunset-comment header documents re-evaluation triggers for numpy<2, rio-cogeo==6.0.0, and tophu conda-channel availability.
- `.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/01-01-dryrun.txt` (new, 58 lines) — Captured output of `CONDA_OVERRIDE_OSX=15.1 micromamba create --dry-run -n subsideo-phase1-probe -f conda-env.yml`. Documents the solver's pin-availability analysis on osx-arm64. (Renamed from `01-01-dryrun.log` because repo `.gitignore` excludes `*.log`.)

## Decisions Made

- **Manifest content is verbatim from plan spec.** PLAN.md Task 1 includes the full YAML body with the explicit note "Details that MUST be honoured (do NOT change in any way)". Following the executor contract — plan fidelity over pre-emptive "fix" of pin choices. The plan's senior-planner pins are preserved.
- **Dry-run failure is reported, not worked around.** Plan Task 2 explicitly states: "If the solver cannot satisfy (e.g. tophu=0.2.1 is unavailable on arm64), stop and report — do NOT relax pins without ADR." This is a Rule 4 architectural decision upstream of this plan — left to the orchestrator / next-wave plan author.
- **`CONDA_OVERRIDE_OSX=15.1` added to probe invocation** after the first run surfaced a libmamba warning ("OSX version not found, defaulting virtual package version to 0") that caused false `__osx >=11.0 missing` reports. The second run with the override isolated the true pin-availability failures.

## Deviations from Plan

None from Task 1 — the file was authored verbatim per spec. Task 2 could not confirm dry-run success (acceptance criterion "transaction plan without PackagesNotFoundError or Conflict:"), but this outcome is explicitly anticipated by the plan ("stop and report — do NOT relax pins without ADR"). No auto-fix was applied; deferred to orchestrator.

## Issues Encountered

### Task 2 dry-run surfaced six pin-availability conflicts on osx-arm64

Confirmed via `CONDA_OVERRIDE_OSX=15.1 micromamba create --dry-run -n subsideo-phase1-probe -f conda-env.yml` (full log: `01-01-dryrun.txt`). Summary table:

| # | Package | Plan pin | conda-forge reality | Conflict |
|---|---------|----------|---------------------|----------|
| 1 | `isce3` | `=0.25.10` | Latest on conda-forge is `0.25.8` (39 versions published; 0.25.10 not yet released) | Pin unsatisfiable on any platform via conda-forge |
| 2 | `snaphu-py` | `=0.4.1` | Correct conda-forge package name is `snaphu` (not `snaphu-py`); `snaphu=0.4.1` exists on osx-arm64 | Package name mismatch — `snaphu-py` is the PyPI name only |
| 3 | `tophu` | `=0.2.1` | Package exists as noarch but carries hard `__linux =*` run-requirement in its depends list (verified via anaconda.org API for all three published versions 0.1.0 / 0.2.0 / 0.2.1) | Not installable on osx-arm64 from conda-forge |
| 4 | `dem-stitcher` | `>=2.5,<3` | Not published on conda-forge (PyPI-only package) | Needs to move to `pip:` layer |
| 5 | `compass` vs `scipy` | `compass=0.5.6` + `scipy>=1.14,<2` | `compass 0.5.6` declares `scipy >=1.0,<1.13` in its conda-forge deps — directly contradicts plan's `scipy>=1.14` | Transitive solver conflict — one of the two pins must move |
| 6 | `rioxarray` vs `numpy` | `rioxarray>=0.22,<1` + `numpy<2.0` | `rioxarray 0.22+` on conda-forge requires `numpy>=2` | Transitive conflict — matches research PITFALLS P0.2 |

**Pre-existing local env state is consistent with findings:** `tophu 0.2.0` in the current `subsideo` env was installed via `pip install git+https://github.com/isce-framework/tophu.git` (verified via `direct_url.json`), not from conda-forge — confirming tophu does not install cleanly from conda-forge on osx-arm64. The existing env contains `isce3 0.25.8` (not 0.25.10), matching the conda-forge latest.

**Active `subsideo` env is UNCHANGED** per Task 2 acceptance:
- No `subsideo-phase1-probe` env was created (`micromamba env list | grep -c subsideo-phase1-probe` returns `0`).
- Active env still reports `numpy 2.4.4` (pre-Task-1 state per RESEARCH.md line 421).
- Task 1 wrote a file only; did not install anything.

**Scope:** Resolving these pin conflicts requires decisions (which pins to relax, whether to relocate packages between conda and pip layers, whether to drop a platform from Phase 1 scope, or whether to defer to a patched upstream release). Per Rule 4 (architectural change) and the plan's explicit "stop and report — do NOT relax pins without ADR", this is left to the orchestrator / next Phase-01 Wave / a follow-up correction plan. Plan 01-09 (reproducibility recipe) cannot produce a clean osx-arm64 lockfile until these are resolved.

## User Setup Required

None - no external service configuration required for the manifest authoring itself. Downstream install (`micromamba env create -f conda-env.yml`) will fail on osx-arm64 until the six pin conflicts above are adjudicated.

## Self-Check: PASSED

- `conda-env.yml` exists at repo root: **FOUND** (`/Volumes/Geospatial/Geospatial/subsideo/conda-env.yml`, 2555 bytes, 73 lines)
- Task 1 commit `f0c2241` in git log: **FOUND** (`git log --oneline | grep f0c2241` — `f0c2241 feat(01-01): add two-layer conda-env.yml for v1.1 environment`)
- All 9 grep-based acceptance criteria: **PASSED** (numpy pin 1, tophu pin 1, dist-s1 pin 1, py-spy pin 1, rio-cogeo pin 1, editable install 1, tophu count 1, no CUDA strings, pyproject.toml unchanged)
- Automated YAML assertion: **PASSED** (`python3 -c "import yaml; ..."` prints "PASS all assertions: YAML parses cleanly, all pins verified")
- Dry-run audit artifact `01-01-dryrun.txt` exists in phase dir: **FOUND** (3651 bytes, 58 lines)
- Active `subsideo` env unchanged: **VERIFIED** (`numpy 2.4.4` still, no probe env created)

## Next Phase Readiness

**What's ready:**
- `conda-env.yml` is in place at repo root — Plans 01-02, 01-03, 01-04, 01-07, 01-09 can all reference it.
- Sunset conditions header enables future maintainers to track pin-lift triggers.
- pyproject.toml untouched per plan contract (M9 in PATTERNS.md).

**Blockers / concerns for orchestrator:**
- **osx-arm64 install path blocked** by six pin conflicts (Issues Encountered). These surfaced deterministically from the dry-run probe specified by Task 2. Fixing them is out of scope for this plan per the plan's own "stop and report" directive. Recommended follow-up paths (NOT applied here, for orchestrator/user decision):
  1. Bump plan pins: `isce3=0.25.8` (latest available), `snaphu=0.4.1` (correct package name), relocate `dem-stitcher` + `tophu` to pip layer, choose one of (`compass` downgrade / `scipy` downgrade), resolve rioxarray-vs-numpy via `rioxarray<0.22`.
  2. Author a Phase 1 ADR that freezes these adjustments and re-runs the probe.
  3. Accept Docker-on-linux-64-only acceptance for Phase 1 and defer osx-arm64 closure to a later milestone.
- **D-18 "both platforms validated in Phase 1" cannot be met** for osx-arm64 until conflicts resolved.
- **Plan 01-09 lockfile generation for osx-arm64** is blocked on the same resolution.
- **Plan 01-02 tophu regression test** (`micromamba run -n subsideo python -c "import tophu"`) will need the tophu layer-assignment decision from the conflict table before it can pass fresh-install on osx-arm64.

---
*Phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding*
*Completed: 2026-04-22*
