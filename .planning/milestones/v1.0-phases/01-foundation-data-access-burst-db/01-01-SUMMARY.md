---
phase: 01-foundation-data-access-burst-db
plan: 01
subsystem: config
tags: [pydantic-settings, typer, ruamel-yaml, cli, config]

requires: []
provides:
  - "Installable subsideo package with __version__ = 0.1.0"
  - "Settings class with env > .env > YAML > defaults precedence"
  - "dump_config/load_config YAML round-trip helpers (ISCE3 compatible)"
  - "check-env CLI command for credential validation"
  - "Package skeleton: data/, burst/, utils/ subpackages"
  - "Test fixtures: Po Valley AOI, tmp_cache_dir"
affects: [01-02, 01-03, 01-04]

tech-stack:
  added: [pydantic-settings, ruamel.yaml, typer, loguru, requests-oauthlib, dem-stitcher, sentineleof, s1-orbits, earthaccess, asf-search, geopandas, pytest-mock]
  patterns: [layered-config, yaml-round-trip, cli-subcommands]

key-files:
  created:
    - src/subsideo/__init__.py
    - src/subsideo/config.py
    - src/subsideo/cli.py
    - src/subsideo/utils/logging.py
    - tests/conftest.py
    - tests/unit/test_config.py
  modified:
    - pyproject.toml

key-decisions:
  - "Moved conda-forge-only deps (opera-utils, s1-reader, mintpy, gdal) to optional [conda] group so pip install works in dev environments"
  - "YamlConfigSettingsSource requires yaml_file in model_config, not init kwarg; tests use dynamic subclass pattern"

patterns-established:
  - "Layered config: Settings(BaseSettings) with YamlConfigSettingsSource as 4th source"
  - "YAML round-trip: dump_config(model_dump(mode='json')) + load_config(model_validate) for Path coercion"
  - "CLI callback pattern: @app.callback() required for multi-command Typer app"

requirements-completed: [CFG-01, CFG-02]

duration: 8min
completed: 2026-04-05
---

# Phase 01 Plan 01: Package Bootstrap and Config System Summary

**Pydantic-settings layered config (env > .env > YAML) with ISCE3-compatible YAML round-trip and Typer CLI check-env skeleton**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-05T17:34:08Z
- **Completed:** 2026-04-05T17:42:18Z
- **Tasks:** 3
- **Files modified:** 12

## Accomplishments
- Installable package skeleton with all Phase 1 pip dependencies resolved
- Settings class with full layered config (env > .env > YAML > defaults) and ISCE3-compatible YAML serialization
- 8 unit tests covering config precedence, round-trip, Path coercion, and ISCE3 YAML compatibility
- check-env CLI command that validates CDSE/Earthdata credentials and warns on missing CDS API key

## Task Commits

Each task was committed atomically:

1. **Task 1: Package skeleton and dependencies** - `3714de3` (feat)
2. **Task 2: Config unit tests** - `47ba1f7` (test)
3. **Task 3: Typer CLI with check-env** - `3dda69e` (feat)

## Files Created/Modified
- `pyproject.toml` - Added pydantic-settings, data access deps; moved conda-only deps to optional group
- `src/subsideo/__init__.py` - Package root with __version__ = "0.1.0"
- `src/subsideo/config.py` - Settings class, dump_config, load_config
- `src/subsideo/cli.py` - Typer app with check-env subcommand
- `src/subsideo/utils/logging.py` - Loguru-based structured logging setup
- `src/subsideo/utils/__init__.py` - Empty stub
- `src/subsideo/data/__init__.py` - Empty stub
- `src/subsideo/burst/__init__.py` - Empty stub
- `tests/__init__.py` - Empty stub
- `tests/conftest.py` - Po Valley AOI fixtures, tmp_cache_dir
- `tests/unit/__init__.py` - Empty stub
- `tests/unit/test_config.py` - 8 tests for Settings behavior
- `tests/integration/__init__.py` - Empty stub

## Decisions Made
- Moved conda-forge-only packages (opera-utils, s1-reader, mintpy, gdal, cdse-client) to an optional `[conda]` dependency group so `pip install -e .[dev]` works without conda. These are installed via `conda-env.yml` in production.
- pydantic-settings `YamlConfigSettingsSource` reads `yaml_file` from `model_config` at class definition time, not from init kwargs. Tests use a dynamic subclass pattern to override `yaml_file` per test.
- Added `@app.callback()` to Typer app so check-env registers as a subcommand rather than collapsing to the only command.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Moved conda-forge-only deps to optional group**
- **Found during:** Task 1 (pip install verification)
- **Issue:** s1-reader, mintpy, gdal, cdse-client are not on PyPI; `pip install -e .` failed with "package not found"
- **Fix:** Moved these to a new `[conda]` optional dependency group; they are installed via conda-env.yml
- **Files modified:** pyproject.toml
- **Verification:** `uv pip install -e ".[dev]"` succeeds
- **Committed in:** 3714de3 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed YAML source test approach**
- **Found during:** Task 2 (test_yaml_loading failure)
- **Issue:** `_yaml_file` init kwarg is not propagated by pydantic-settings; YAML file path must be in model_config
- **Fix:** Created `_make_yaml_settings()` helper that dynamically subclasses Settings with yaml_file in model_config; also added `yaml_file=None` to Settings.model_config
- **Files modified:** src/subsideo/config.py, tests/unit/test_config.py
- **Verification:** All 8 tests pass including YAML loading and precedence tests
- **Committed in:** 47ba1f7 (Task 2 commit)

**3. [Rule 1 - Bug] Added Typer callback for multi-command app**
- **Found during:** Task 3 (CLI verification)
- **Issue:** Typer with single command collapses to show that command directly; `subsideo --help` didn't list check-env as subcommand
- **Fix:** Added `@app.callback()` decorator so Typer registers it as a command group
- **Files modified:** src/subsideo/cli.py
- **Verification:** `subsideo --help` lists check-env as subcommand
- **Committed in:** 3dda69e (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All auto-fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Package skeleton complete; all subsequent plans can `from subsideo.config import Settings`
- CLI entry point registered; future commands (rtc, cslc, disp, dswx, validate) can be added to `app`
- Config system tested and verified; YAML round-trip works for ISCE3-convention configs

---
*Phase: 01-foundation-data-access-burst-db*
*Completed: 2026-04-05*
