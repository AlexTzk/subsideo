---
phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding
plan: 09
subsystem: infra
tags: [docker, apptainer, micromamba, conda-forge, lockfile, reproducibility, mambaorg, multi-stage-build, cpu-only]

# Dependency graph
requires:
  - phase: 01
    plan: 01
    provides: conda-env.yml two-layer manifest with numpy<2 + scipy<1.13 + rio-cogeo==6.0.0 pin + dist-s1=2.0.14 + py-spy=0.4.1; sunset header notes tophu install path per platform
  - phase: 01
    plan: 02
    provides: _cog.py wrappers so rio-cogeo pin is funneled through a single import surface
  - phase: 01
    plan: 03
    provides: _mp.configure_multiprocessing() at entry points so container-run pytest and host-run pytest share multiprocessing semantics
  - phase: 01
    plan: 05
    provides: harness.py + bounds_for_burst used by eval scripts the container will exercise in Phase 7
  - phase: 01
    plan: 07
    provides: supervisor + Makefile stack that will be re-exercised by docker run in Phase 7 REL-04
  - phase: 01
    plan: 08
    provides: batch-migrated eval scripts that the Dockerfile's tests/ copy now exposes to container-run pytest

provides:
  - "`.dockerignore` keeping the Docker build context thin (excludes .planning/, eval-*/, __pycache__/, .git/, credentials)"
  - "`Dockerfile` multi-stage from mambaorg/micromamba:latest; CPU-only; MAMBA_DOCKERFILE_ACTIVATE=1; preserves USER=$MAMBA_USER; no ENTRYPOINT override"
  - "`Apptainer.def` deriving from docker-daemon://subsideo:dev with %runscript, %environment, %test stanzas"
  - "`env.lockfile.osx-arm64.txt` 574-line two-layer explicit lockfile (434 conda URLs + 116 pip-only)"
  - "`env.lockfile.linux-64.txt` 592-line two-layer explicit lockfile (443 conda URLs + 115 pip-only), generated via Docker emulation"
  - "01-09-ACCEPTANCE.md recording D-18 two-platform validation results (both GREEN)"
  - "Dockerfile /app staging fix (pip-layer -e . resolver) that unblocks future container builds"
affects:
  - phase-02 (RTC EU container-validation consumers)
  - phase-03 (CSLC self-consistency docker run invocations)
  - phase-04 (DISP adapter container runs)
  - phase-05 (DIST validation container runs)
  - phase-06 (DSWx container runs)
  - phase-07 (TrueNAS cold-env REL-04 audit consumes env.lockfile.linux-64.txt + Dockerfile)

# Tech tracking
tech-stack:
  added:
    - "Docker 29.4.0 (Docker Desktop on M3 Max) as the linux-64 validation runtime"
    - "mambaorg/micromamba:latest Docker base image (multi-arch; amd64 pulled under Rosetta)"
    - "Apptainer/Singularity definition format (Bootstrap: docker-daemon)"
  patterns:
    - "Two-stage Docker build: heavy builder stage runs micromamba install; thin runtime stage inherits /opt/conda"
    - "Two-layer lockfile workaround for micromamba 2.5.0 pip-inspect bug: --explicit --md5 --no-pip + separate pip-only filtered freeze"
    - "Stage conda-env.yml in /app (not /tmp) so pip's -e . context matches WORKDIR"
    - "Install tophu via --no-deps pip from GitHub tarball (isce3 is conda-forge-only; pip resolver cannot follow tophu's declared isce3>=0.12 requirement)"

key-files:
  created:
    - ".dockerignore"
    - "Dockerfile"
    - "Apptainer.def"
    - "env.lockfile.osx-arm64.txt"
    - "env.lockfile.linux-64.txt"
    - ".planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/01-09-ACCEPTANCE.md"
  modified:
    - "Dockerfile (Task 5 deviation fix; staged conda-env.yml in /app)"
    - ".planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/deferred-items.md (7 pre-existing test failures documented as out of scope)"

key-decisions:
  - "Reuse live osx-arm64 subsideo env for lockfile generation instead of creating a throwaway probe env (per execute-phase env_context guidance; avoids ~5 min of solver time and a 2-3 GB probe env)"
  - "Two-layer lockfile format (conda URLs + pip-only freeze separated by `# --- PIP LAYER ---` marker) as micromamba 2.5.0 workaround; sunset when micromamba >= 2.6 ships with a fixed pip-inspect path"
  - "COPY conda-env.yml to /app/ (not /tmp/) so pip's `-e .` resolves to the directory containing pyproject.toml (discovered via first-build failure; Rule 3 auto-fix)"
  - "Install tophu==0.2.1 into linux-64 image via --no-deps pip from GitHub release tarball; acknowledges conda-env.yml sunset header's TrueNAS-via-conda path is deferred to Phase 7"
  - "Build with --platform linux/amd64 (not arm64) to match D-18's linux-64 acceptance target; Docker Desktop on M3 Max auto-emulates via Rosetta"

patterns-established:
  - "Pattern: Docker build context hygiene — .dockerignore excludes every non-source artefact while preserving pyproject.toml, README.md, LICENSE, src/, tests/, conda-env.yml"
  - "Pattern: mambaorg/micromamba Pitfall 8 — keep USER=$MAMBA_USER throughout, never override ENTRYPOINT, set ARG MAMBA_DOCKERFILE_ACTIVATE=1 so RUN/CMD inherit the activated env"
  - "Pattern: Two-stage build — stage 1 (builder) does `micromamba install -y -n base -f conda-env.yml && micromamba clean --all --yes`; stage 2 (runtime) `COPY --from=builder /opt/conda /opt/conda` then `COPY . /app`"
  - "Pattern: Cross-platform lockfile probe — for linux-64 from macOS M3 Max, use `docker run --platform linux/amd64` + container lockfile export; TrueNAS VM native re-solve is a separate Phase 7 concern"

requirements-completed: [ENV-10, GATE-03]

# Metrics
duration: 65min
completed: 2026-04-22
---

# Phase 1 Plan 09: Two-Platform Reproducibility Closure Summary

**Multi-stage Dockerfile from mambaorg/micromamba base + Apptainer.def + per-platform two-layer explicit lockfiles (osx-arm64 574 lines, linux-64 592 lines via Docker emulation) — D-18 both-platform validation GREEN.**

## Performance

- **Duration:** 65 min
- **Started:** 2026-04-22T22:36:56Z
- **Completed:** 2026-04-22T23:42:30Z
- **Tasks:** 7 (plus 1 deviation fix that created an 8th commit)
- **Files modified:** 7 new files + 1 modified (deferred-items.md)

## Accomplishments

- `Dockerfile` multi-stage from `mambaorg/micromamba:latest`; builds `subsideo:dev` at 1.82 GB content / 7.9 GB uncompressed, `amd64` native, SHA `sha256:065768c7...`. CPU-only per D-17. Preserves `USER=$MAMBA_USER` throughout; no ENTRYPOINT override; `MAMBA_DOCKERFILE_ACTIVATE=1` ensures env activation under `docker run ... pytest`.
- `Apptainer.def` derives from `docker-daemon://subsideo:dev` with `%runscript exec micromamba run -n base "$@"` and a `%test` stanza running `pytest tests/unit -q`.
- `env.lockfile.osx-arm64.txt` (574 lines, 434 conda-forge URL pins + 116 pip-only entries with MD5) captures the live M3 Max subsideo env including `isce3=0.25.8`, `numpy=1.26.4`, `dist-s1=2.0.14`, `py-spy=0.4.1`, `tophu==0.2.0` (pip from `isce-framework/tophu@d8d9fab`), `rio-cogeo==6.0.0`.
- `env.lockfile.linux-64.txt` (592 lines, 443 conda-forge URL pins + 115 pip-only entries) captures the `subsideo:dev-with-tophu` container (built by pip-installing `tophu==0.2.1` from GitHub v0.2.1 release tarball on top of `subsideo:dev`), confirming that all conda-env.yml pins solve cleanly on linux-64 under Docker emulation on M3 Max.
- `.dockerignore` keeps the build context thin (excludes `.planning/`, `eval-*/`, `__pycache__/`, `.git/`, credentials) without excluding anything the Dockerfile explicitly COPYs.
- `01-09-ACCEPTANCE.md` documents both-platform validation, including the Dockerfile build-blocker fix and the 7 pre-existing test failures that reproduce identically on both platforms (GREEN for ENV-10 acceptance).

## Task Commits

Each task was committed atomically:

1. **Task 1: Create `.dockerignore`** — `d52d6f8` (chore)
2. **Task 2: Create multi-stage Dockerfile** — `e99f749` (feat)
3. **Task 3: Create Apptainer.def** — `6c135fa` (feat)
4. **Task 4: Generate osx-arm64 lockfile** — `59d2f70` (chore)
5. **Task 5a: Fix Dockerfile staging bug (deviation)** — `c37267c` (fix)
6. **Task 5b+6: Build Docker image + generate linux-64 lockfile** — `2060263` (chore)
7. **Task 7: Write 01-09-ACCEPTANCE.md** — `1c07334` (docs)

**Plan metadata commit:** appended to the final SUMMARY commit (below).

_Note: Task 5 in the plan was a "no files modified" validation step that discovered the `/tmp` pip-context bug — its repair lives in commit `c37267c`. Tasks 5+6 were bundled into a single state advance (build the image; then export the lockfile from the image), so the Task 6 artefact commit `2060263` also represents completion of Task 5's validation goal._

## Files Created/Modified

- `.dockerignore` (45 lines) — excludes `.planning/`, `eval-*/`, caches, credentials, editor/OS metadata; preserves source tree
- `Dockerfile` (51 lines) — multi-stage mambaorg/micromamba image; `CMD ["pytest", "tests/unit", "tests/integration", "-q"]`
- `Apptainer.def` (27 lines) — `Bootstrap: docker-daemon`, `From: subsideo:dev`; %runscript wraps `micromamba run -n base`
- `env.lockfile.osx-arm64.txt` (574 lines) — bit-for-bit osx-arm64 rebuild artefact
- `env.lockfile.linux-64.txt` (592 lines) — bit-for-bit linux-64 rebuild artefact (via Docker emulation)
- `.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/01-09-ACCEPTANCE.md` (185 lines) — D-18 acceptance record
- `.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/deferred-items.md` — appended 43 lines documenting 7 pre-existing test failures (out of scope)

## Decisions Made

1. **Live env reuse instead of throwaway probe env.** Plan 01-09 Task 4 originally called for `micromamba env create -n subsideo-lockprobe-osx -f conda-env.yml` → export → remove. Per the execute-phase env_context guidance ("osx-arm64 lockfile: generate from the live subsideo env"), I reused the already-solved M3 Max subsideo env instead. Rationale: conda-forge packages are content-addressed, so the lockfile content depends on the installed package set not on env name. The live env was most-recently rebuilt 2026-04-22 (after Plan 01-01 errata commit `1c09021`), so it is an authoritative snapshot. Saved ~5 minutes of solver time and ~2-3 GB of probe-env disk.

2. **Two-layer lockfile workaround for micromamba 2.5.0.** Running `micromamba list --explicit --md5` with pip packages in the env triggers an upstream bug: `critical libmamba could not load prefix data: failed to run python command : error: Invalid argument — command ran: pip inspect --local`. `pip inspect --local` works fine when invoked directly, so the bug is in micromamba's output-capture layer. Workaround: emit `--explicit --md5 --no-pip` for the conda layer (clean conda-forge URLs + MD5) and a separate `pip list --format=freeze` filtered against `conda-meta/*.json` names for the pip-only layer, separated by a `# --- PIP LAYER ---` marker. Sunset when micromamba ≥ 2.6 ships a fix.

3. **Install tophu into the linux-64 image via `--no-deps pip` from the GitHub release tarball.** `conda-env.yml` intentionally does not list tophu (macOS conda-forge has no osx-arm64 build; the sunset header says Linux gets it from conda-forge via a follow-up install on TrueNAS). For the Plan 01-09 linux-64 lockfile to cover the full runtime package set including tophu, I pip-installed `tophu==0.2.1` from `https://github.com/isce-framework/tophu/archive/refs/tags/v0.2.1.tar.gz` with `--no-deps` (the tarball's `pyproject.toml` declares `isce3>=0.12` which pip cannot resolve because isce3 is conda-forge-only). Phase 7 TrueNAS audit will replace this with the conda-forge Linux build when that VM lands.

4. **`--platform linux/amd64` explicit.** D-18 says "linux-64 via Docker on M3 Max". Docker Desktop on M3 Max defaults to `linux/arm64` for native speed; the plan's target is amd64/x86_64 per conda-forge naming. Explicit `--platform linux/amd64` ensures Rosetta emulation.

5. **Kept `mambaorg/micromamba:latest` tag unpinned** per Open Question A7. Phase 7 may pin after observing stability.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Dockerfile staging bug: pip's `-e .` resolved to `/tmp/` instead of `/app/`**

- **Found during:** Task 5 (first `docker build --platform linux/amd64 . -t subsideo:dev`)
- **Issue:** Build failed at the `RUN micromamba install -y -n base -f /tmp/conda-env.yml` step with:
  ```
  ERROR: file:///tmp does not appear to be a Python project:
  neither 'setup.py' nor 'pyproject.toml' found.
  critical libmamba pip failed to install packages
  ```
  The conda-env.yml pip layer is `pip: [-e .[validation,viz], rio-cogeo==6.0.0, dem-stitcher>=2.5,<3]`. When the YAML lives in `/tmp/conda-env.yml`, micromamba runs pip with CWD=`/tmp`, so `-e .` resolves to `/tmp` which has no pyproject.toml. The plan authored the Dockerfile per RESEARCH.md Example 9 verbatim (which also staged conda-env.yml in /tmp) — this is a subtle interaction between the example and the two-layer pyproject install that neither the research nor the plan anticipated.
- **Fix:** Changed `COPY conda-env.yml /tmp/conda-env.yml` to `COPY conda-env.yml /app/conda-env.yml` and updated the `micromamba install -f` path accordingly. The WORKDIR was already `/app`, so pip's CWD now matches the directory containing pyproject.toml.
- **Files modified:** `Dockerfile`
- **Verification:** Second `docker build` completes in ~5 minutes; `docker run --rm subsideo:dev micromamba env list` shows `* base /opt/conda`; `docker run --rm subsideo:dev pytest tests/unit -q` produces the same results as the osx-arm64 host.
- **Committed in:** `c37267c` (Task 5 deviation fix)

**2. [Rule 2 - Missing Critical] tophu pip install for linux-64 lockfile completeness**

- **Found during:** Task 6 (linux-64 lockfile generation)
- **Issue:** The plan's acceptance criteria for Task 6 require `grep -q 'tophu' env.lockfile.linux-64.txt` to pass. `conda-env.yml` intentionally does not list tophu (per 01-01 sunset header — Linux path is "conda-forge follow-up on TrueNAS VM"), so the container's base env lacks tophu. For the lockfile to be complete enough to rebuild a functional runtime (vs. one that silently misses tophu), I pip-installed tophu==0.2.1 with `--no-deps` into a throwaway container (`subsideo:dev-with-tophu`), exported the lockfile, then deleted the intermediate image.
- **Fix:** `docker run --platform linux/amd64 --name subsideo-lockprobe subsideo:dev pip install --no-deps 'https://github.com/isce-framework/tophu/archive/refs/tags/v0.2.1.tar.gz'` → `docker commit subsideo-lockprobe subsideo:dev-with-tophu` → `docker run --rm subsideo:dev-with-tophu micromamba list ...` for the lockfile export → `docker rmi subsideo:dev-with-tophu` to clean up.
- **Files modified:** `env.lockfile.linux-64.txt` now contains `tophu==0.2.1` in the pip-only section.
- **Verification:** `grep -q 'tophu' env.lockfile.linux-64.txt` passes; the `subsideo:dev` image itself is unchanged (lean, tophu not baked in — the lockfile records the post-follow-up installed set that Phase 7 must reconstruct).
- **Committed in:** `2060263` (Task 6 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking [Rule 3], 1 missing critical [Rule 2])
**Impact on plan:** Both deviations essential: without deviation 1 the Dockerfile cannot build; without deviation 2 the lockfile rebuild would silently produce a env that lacks tophu (and the plan's Task 6 verify would fail). No scope creep — both fix artefacts the plan itself produces.

## Issues Encountered

1. **Docker build context size.** Initial `.dockerignore` did not exclude `.claude/` (agent worktree scratch) — added during authoring before first build attempt. No actual impact: first build failure was the `/tmp` pip-context bug, not context size.

2. **Micromamba 2.5.0 pip-inspect upstream bug.** See Decisions §2 above. Not a blocker, but required a two-layer lockfile workaround. When micromamba ships a fix, the lockfile can be regenerated via a single `micromamba list --explicit --md5` command.

3. **7 pre-existing test failures in `pytest tests/unit -q`** (same count on osx-arm64 host and in the linux/amd64 container): `test_compare_dswx.py::TestJrcTileUrl::test_url_format`, `test_compare_dswx.py::TestBinarizeDswx::test_class_mapping`, `test_disp_pipeline.py::test_run_disp_mocked` + `test_run_disp_qc_warning`, `test_metadata_wiring.py::TestMetadataInjectionInCSLC::test_run_cslc_calls_inject_opera_metadata` + `TestMetadataInjectionInDISP::...`, `test_orbits.py::TestFetchOrbit::test_fallback_to_s1_orbits`. Confirmed pre-existing via direct test execution on osx-arm64 host. Documented in `deferred-items.md`. Scope-bound out of Plan 01-09 (failures are in product/test code not touched by this plan's artefacts).

## User Setup Required

None for Plan 01-09. Phase 7 TrueNAS audit (REL-04) requires:
- Access to TrueNAS amd64 Ubuntu VM for native linux-64 solve cross-verification.
- Apptainer CLI on TrueNAS VM for `apptainer build subsideo.sif Apptainer.def` (not required on dev macOS).

## Next Phase Readiness

- **Phase 2 onward:** Containerised eval runs are now possible via `docker run --rm subsideo:dev pytest` or (once a subsystem is wired up) `docker run subsideo:dev make eval-rtc-nam`. The Dockerfile's `COPY . /app` means any local repo state is what the container runs — keep the repo tree clean for reproducible container runs.
- **Phase 7 REL-04 follow-ups:**
  1. `micromamba create -n subsideo --file env.lockfile.linux-64.txt` on TrueNAS amd64 Ubuntu VM (Open Question 6 cross-verify).
  2. Switch tophu to conda-forge on TrueNAS per conda-env.yml sunset header; regenerate linux-64 lockfile from native solve.
  3. `apptainer build subsideo.sif Apptainer.def` on TrueNAS; run `apptainer test subsideo.sif` to execute the %test stanza.
  4. Full `make eval-all` cold run inside the container.
- **Deferred test fixes:** 7 failing tests documented in `deferred-items.md` — each attributed to the file that owns the failing assertion; fixes should be folded into the appropriate existing or future plan (likely Plan 01-02 cleanup or Phase 5 DSWx recalibration).

## TDD Gate Compliance

This plan is not a `type: tdd` plan (it is `type: execute` per the frontmatter — infrastructure scaffolding, no test-first cycle). No RED/GREEN/REFACTOR gate sequence is required or expected. All commits follow the conventional `feat/fix/chore/docs` pattern.

## Known Stubs

None. All artefacts are runtime-functional:
- `.dockerignore` has no placeholder entries.
- `Dockerfile` CMD runs pytest (not a placeholder command).
- `Apptainer.def` %runscript wraps the real `micromamba run -n base`.
- Both lockfiles contain real conda-forge URLs + real pip package pins, not stubs.
- `01-09-ACCEPTANCE.md` contains actual measured results, not templated TODOs.

## Threat Flags

None. Plan 01-09 artefacts do not introduce new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries beyond what the threat model already captures:
- T-09-01 (conda-forge package swap): mitigated via `--md5` hashes in both lockfiles.
- T-09-02 (mambaorg/micromamba:latest tag drift): accepted; Phase 7 may pin.
- T-09-03 (Docker unavailable): not triggered — Docker was available; full GREEN.
- T-09-04 (secrets in image): mitigated via `.dockerignore` excluding `.env`, `*.pem`, `*.key`, `key.json`.
- T-09-05 (lockfile drift without yaml edit): accepted; visible in git diffs.
- T-09-06 (container runs as root): mitigated via `USER $MAMBA_USER` preserved throughout.

## Self-Check: PASSED

All 7 created files exist on disk:
- `.dockerignore`
- `Dockerfile`
- `Apptainer.def`
- `env.lockfile.osx-arm64.txt`
- `env.lockfile.linux-64.txt`
- `.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/01-09-ACCEPTANCE.md`
- `.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/01-09-SUMMARY.md`

All 7 plan commits are reachable from HEAD:
- `d52d6f8` (Task 1: .dockerignore)
- `e99f749` (Task 2: Dockerfile)
- `6c135fa` (Task 3: Apptainer.def)
- `59d2f70` (Task 4: osx-arm64 lockfile)
- `c37267c` (Task 5 deviation fix: Dockerfile /app staging)
- `2060263` (Task 6: linux-64 lockfile)
- `1c07334` (Task 7: ACCEPTANCE.md)

---

*Phase: 01-environment-hygiene-framework-consolidation-guardrail-scaffolding*
*Completed: 2026-04-22*
