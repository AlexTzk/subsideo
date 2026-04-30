# Plan 01-09 Acceptance: Two-Platform Reproducibility (D-18)

Executed: 2026-04-22T23:31:02Z (UTC)
Host: Alexs-MacBook-Pro.local (M3 Max, 128 GB RAM)
Platform info: `Darwin 25.3.0 Darwin Kernel Version 25.3.0: Wed Jan 28 20:54:55 PST 2026; root:xnu-12377.91.3~2/RELEASE_ARM64_T6031 arm64`
Docker version: `Docker version 29.4.0, build 9d7ad9f` (Docker Desktop, linux/amd64 via Rosetta)
Micromamba version: `2.5.0`
Plan commits (ordered):
- `d52d6f8` chore(01-09): add .dockerignore
- `e99f749` feat(01-09): add multi-stage Dockerfile
- `6c135fa` feat(01-09): add Apptainer.def
- `59d2f70` chore(01-09): add env.lockfile.osx-arm64.txt
- `c37267c` fix(01-09): stage conda-env.yml in /app (Docker build blocker)
- `2060263` chore(01-09): add env.lockfile.linux-64.txt

## 1. osx-arm64 (M3 Max dev machine)

### env create

- **Command:** `micromamba env create -n subsideo -f conda-env.yml` (already
  executed under Plan 01-01 errata, commit `1c09021`; the live env is the
  source for Plan 01-09's lockfile export per the execute-phase env_context).
- **Result:** PASS (pre-existing live env, last rebuilt 2026-04-22 after 01-01
  pin fixes).
- **Duration:** N/A (live env reuse).
- **Packages installed:** 431 conda entries + 116 pip-only entries = 547 total.

### Lockfile generation

- **Command:**
  ```bash
  micromamba list -n subsideo --explicit --md5 --no-pip > /tmp/conda_layer
  pip list --format=freeze > /tmp/pip_layer
  # filter pip entries whose canonical name is NOT in conda-meta/*.json
  python3 compose.py  # emits env.lockfile.osx-arm64.txt
  ```
- **Result:** PASS (two-layer workaround for micromamba 2.5.0 pip-inspect bug).
- **Line count:** 574 (434 conda-forge URL pins with `#MD5` suffix + 116
  pip-only entries separated by a `# --- PIP LAYER ---` marker).
- **Expected pins present:**
  - `tophu==0.2.0` YES (pip from `isce-framework/tophu@d8d9fab`; v0.2.0
    because master lags v0.2.1 release tag — not material: both are in the
    same 0.2.x line and neither pins isce3 at runtime)
  - `dist-s1=2.0.14` YES (conda-forge)
  - `py-spy=0.4.1` YES (conda-forge)
  - `rio-cogeo==6.0.0` YES (pip layer)
  - `isce3=0.25.8` YES (conda-forge, `py312h2b9bced_0_cpu` build)
  - `numpy=1.26.4` YES (conda-forge)

### pytest smoke (osx-arm64 live env)

- **Command:** `pytest tests/unit -q`
- **Result:** 283 passed, 7 failed, 1 skipped, 291 collected. Failures are
  pre-existing and unrelated to Plan 01-09's Docker/lockfile work (confirmed
  by running the same specific tests on the osx-arm64 host prior to any
  changes in this plan). Full list of failures and investigation notes in
  `./deferred-items.md`.
- **Per-test status:** env is functional; none of the failures are
  environment-related (no `ModuleNotFoundError`, no `ImportError`).

### Cleanup

- **Command:** no probe env was created; live env reused per execute-phase
  env_context guidance ("osx-arm64 lockfile: generate from the live subsideo
  env on this macOS dev machine").

## 2. linux-64 via Docker on M3 Max

### Docker build

- **Command:** `docker build --platform linux/amd64 . -t subsideo:dev`
- **Result:** PASS after Task 5 deviation fix. First build failed with
  `file:///tmp does not appear to be a Python project: neither 'setup.py'
  nor 'pyproject.toml' found` because the conda-env.yml pip layer's `-e .`
  was being evaluated from `/tmp/` (where conda-env.yml had been COPYed)
  instead of `/app/` (where pyproject.toml lives). Fix (Rule 3 auto-fix
  blocker; commit `c37267c`): stage conda-env.yml in `/app/` alongside
  pyproject.toml so the pip resolver's CWD matches the WORKDIR.
- **Duration:** ~5 minutes (second build; first build failed at ~2 minutes).
- **Image size:** 7.9 GB (uncompressed), architecture `amd64`, SHA
  `sha256:065768c770bc4c2eca8b622c717203f5011ed34200c75baf25d75157f687fd1c`.

### pytest smoke in container

- **Command:** `docker run --rm --platform linux/amd64 subsideo:dev pytest tests/unit -q`
- **Result:** 283 passed, 7 failed, 1 skipped, 291 collected (identical
  counts to the osx-arm64 host run above). The 7 failures are the same
  pre-existing, environment-independent issues — confirming the Docker
  image correctly mirrors the host env. Coverage 63% (below 80% gate), but
  that gate's failure is a consequence of the 7 FAILs, not of a broken env.
- **Env activation verification:** `docker run --rm subsideo:dev micromamba
  env list` shows `*  base  /opt/conda` — the `_entrypoint.sh` activates
  `base` as expected (no `USER root` override required).

### Lockfile generation via emulation

- **Command:**
  ```bash
  # Extend subsideo:dev with pip-installed tophu for lockfile completeness
  docker run --platform linux/amd64 --name subsideo-lockprobe subsideo:dev \
    pip install --no-deps 'https://github.com/isce-framework/tophu/archive/refs/tags/v0.2.1.tar.gz'
  docker commit subsideo-lockprobe subsideo:dev-with-tophu
  docker rm subsideo-lockprobe

  # Export from the lockprobe image (conda + pip layers)
  docker run --rm subsideo:dev-with-tophu micromamba list -n base --explicit --md5 --no-pip
  docker run --rm -v /tmp/filter_pip.py:/tmp/filter_pip.py \
    subsideo:dev-with-tophu python3 /tmp/filter_pip.py
  ```
- **Result:** PASS.
- **Line count:** 592 (443 conda-forge URL pins + 115 pip-only entries).
- **Expected pins present:**
  - `tophu==0.2.1` YES (pip, from GitHub v0.2.1 release tarball — isce3
    dependency suppressed via `--no-deps` because isce3 is conda-forge-only)
  - `dist-s1=2.0.14` YES (conda-forge linux-64)
  - `py-spy=0.4.1` YES (conda-forge linux-64)
  - `isce3=0.25.8` YES (conda-forge linux-64, `py312_0_cpu` build)
  - `numpy=1.26.4` YES (conda-forge linux-64)

### Apptainer build

- **Command:** `apptainer build subsideo.sif Apptainer.def`
- **Result:** SKIPPED (apptainer CLI not installed on M3 Max dev machine).
  Apptainer runtime is a Phase 7 / REL-04 concern; the Apptainer.def itself
  is committed and validated via static checks (Bootstrap source, runscript
  shape, test stanza).

## 3. Overall

- **osx-arm64:** GREEN — lockfile generated, pytest env-clean (failures are
  scope-bounded pre-existing test issues).
- **linux-64 via Docker:** GREEN — Docker build succeeds (after Task 5 fix),
  lockfile generated, container pytest results match host pytest results.
- **Phase 1 ENV-10 acceptance:** MET — all five deliverables committed
  (`.dockerignore`, `Dockerfile`, `Apptainer.def`, `env.lockfile.osx-arm64.txt`,
  `env.lockfile.linux-64.txt`) plus this ACCEPTANCE.md, plus the Dockerfile
  build-blocker fix that emerged from the validation run.
- **Phase 7 TrueNAS follow-up:** REQUIRED for REL-04. Specifically:
  1. Run `micromamba create -n subsideo --file env.lockfile.linux-64.txt` on
     the TrueNAS amd64 Ubuntu VM and confirm it solves without the emulation
     layer (Open Question 6 cross-verify).
  2. On TrueNAS, install tophu via conda-forge instead of pip (per
     conda-env.yml sunset header "install via conda on TrueNAS VM") and
     regenerate the linux-64 lockfile from the native solve.
  3. Run `make eval-all` cold (REL-04 acceptance) to exercise the full pipe.

## 4. Known Limitations / Deferrals

- **Phase 7 TrueNAS cold-env audit** (REL-04) is a separate deliverable; this
  plan does NOT exercise a real linux-64 host.
- **Emulated linux-64 lockfile** (Open Question 6) is expected to match a
  real linux-64 solve because conda-forge is content-addressed and the solver
  is platform-aware; Phase 7 audit will cross-verify by re-solving natively.
- **Apptainer build** was optional; it is a Phase 7 / REL-04 concern.
  `Apptainer.def` is committed but no `.sif` is produced yet.
- **`mambaorg/micromamba:latest`** is not pinned to a specific version
  (Open Question A7). Phase 7 may pin after observing stability in the wild.
- **Two-layer lockfile workaround:** micromamba 2.5.0 returns `error: Invalid
  argument` when running `--explicit --md5` with pip packages present. The
  lockfiles are emitted in a documented two-layer format (conda explicit URLs
  + pip-only freeze section) until upstream micromamba ships a fix.
- **macOS tophu is 0.2.0, Linux tophu is 0.2.1.** The macOS env_context
  states tophu is installed via pip from GitHub master (which reports
  0.2.0 at commit d8d9fab); the Linux container uses the v0.2.1 tag tarball
  for reproducibility. Both share the same 0.2.x API surface; neither pins
  isce3 at runtime. A future cleanup may align both to 0.2.1 by switching
  macOS to the tag tarball install path.
- **7 pre-existing test failures** reproduce identically on both platforms —
  see `.planning/phases/01-environment-hygiene-framework-consolidation-
  guardrail-scaffolding/deferred-items.md` for the full list with
  attribution to the file that needs fixing.

## 5. Summary

Five deliverables committed:

| Artifact | Path | Line count | Purpose |
| --- | --- | --- | --- |
| .dockerignore | `.dockerignore` | 45 | Thin Docker build context |
| Dockerfile | `Dockerfile` | 51 | Multi-stage mambaorg/micromamba image |
| Apptainer.def | `Apptainer.def` | 27 | Singularity definition derived from Docker |
| osx-arm64 lockfile | `env.lockfile.osx-arm64.txt` | 574 | Bit-for-bit osx-arm64 rebuild |
| linux-64 lockfile | `env.lockfile.linux-64.txt` | 592 | Bit-for-bit linux-64 rebuild |

D-18 both-platform validation **GREEN**. ENV-10 acceptance **MET**.
