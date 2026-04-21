# Stack Research — v1.1 (N.Am./EU Validation Parity & Scientific PASS)

**Domain:** SAR/InSAR geospatial processing library — hardening an existing v1.0 codebase
**Researched:** 2026-04-20
**Confidence:** HIGH (all non-trivial version claims verified against PyPI JSON metadata or upstream source on 2026-04-20; LOW-confidence claims explicitly flagged)

> **Scope note.** This document is a **delta** against `.planning/milestones/v1.0-research/STACK.md`. The v1.0 stack (isce3 0.25.10, compass 0.5.6, dolphin 0.42.5, tophu 0.2.1, snaphu-py 0.4.1, MintPy 1.6.3, dist-s1 2.0.14, pystac-client 0.9.0, pyaps3 0.3.6/0.3.7, dem-stitcher 2.5.13, opera-utils 0.25.6, etc.) is **unchanged** for v1.1. Below are only the **additions, pins, and version-awareness items** introduced by v1.1 scope: env hygiene (numpy<2, tophu first-class, rio_cogeo centralisation, macOS mp), validation harness, reference-fetching libraries for EFFIS/ESA WorldCover/slope/OPERA-CloudFront, threshold-optimisation tooling for DSWx, Makefile orchestration, and watchdog/timeout patterns.

---

## TL;DR — v1.1 stack deltas

| Change class | Item | Why (v1.1-specific) |
|---|---|---|
| **Pin** | `numpy<2.0` in `conda-env.yml` | Phase 0.1 — removes 4 monkey-patches in `cslc.py`; unblocks compass / s1-reader under the pinned Python 3.11 env (neither upstream ships numpy-2 releases as of 2026-04-20) |
| **First-class dep** | `tophu` via **conda-forge** (not pip) | Phase 0.2 — dolphin's `multiscale_unwrap()` path (used when `unwrap_method ∈ {PHASS, ICU}`, which is our production config) imports tophu at first call; tophu is **not on PyPI**, only conda-forge |
| **Pin** | `rio_cogeo ==6.0.0` (stay on 6.x, do NOT jump to 7.x) | Phase 0.3 — rio-cogeo 7.0.0 **removed Python 3.10 support**; subsideo targets 3.10+. No API move actually happened — v1.0's defensive `try/except` was debugging a symptom that had a different root cause. Centralise on the root-level re-exports |
| **New module** | `subsideo._mp` wrapping `multiprocessing.set_start_method("fork", force=True)` on macOS | Phase 0.4 — dist_s1 hangs on spawn start method; no external library replaces `multiprocessing` stdlib for this |
| **New dep (dev/validation only)** | `tenacity ==9.1.4` | Phase 0.5 — CloudFront + ASF + CDSE retry harness; drop-in for v1.0's ad-hoc retries |
| **New dep (validation only)** | `owslib ==0.35.0` | Phase 4.3 — EFFIS burnt-area fetch via WFS GetFeature (no maintained Python-EFFIS wrapper exists as of 2026-04-20) |
| **New dep (validation only)** | `optuna ==4.8.0` — scoped Optional; fallback is pure nested loop | Phase 5.3 — DSWE threshold grid search (3 thresholds × 12 scenes); overkill for dense grid but the Sobol sampler + joint evaluation + persistent study DB makes recalibration restartable |
| **No new dep** | `gdal.DEMProcessing` (already present via conda-forge GDAL) for slope | Phase 2.1 / 3.2 — no reason to pull in richdem/xdem/whitebox; GDAL is already in the env and `DEMProcessing('slope.tif', dem, 'slope')` is one call |
| **No new dep** | `pystac-client` + `boto3` for ESA WorldCover on AWS Open Data | Phase 2.1 / 3.2 — already in v1.0 stack; WorldCover lives at `s3://esa-worldcover/` public bucket. No need for `terracatalogueclient` (VITO-hosted, requires extra index URL) |
| **Orchestration** | **GNU make** (not `just`, not `taskfile`) | Phase 0.7 — already ubiquitous on macOS + Linux dev containers, no extra install; the caching requirements are timestamp-based on cached eval outputs (which is exactly what `make` does natively); `just` has no file-dependency tracking; `taskfile` would be additive without buying us resume-safety we don't already get from `make` + resume-safe checker functions |
| **Watchdog** | Stdlib `multiprocessing.Process.join(timeout=…)` + `Process.terminate()`; optionally `pebble.ProcessPool` for the unwrap fan-out | Phase 0.4 — stdlib is sufficient for a single product run; `pebble` is only needed inside `_run_unwrapping`'s `ProcessPoolExecutor` fan-out where we already have an executor |

---

## 1. numpy pin

### Current recommendation

| Item | Value | Source |
|---|---|---|
| Pin | `numpy>=1.26,<2.0` | Phase 0.1 in BOOTSTRAP_V1.1.md |
| Pin location | `conda-env.yml` (authoritative) + `pyproject.toml` dependencies updated from `"numpy>=1.26,<3"` to `"numpy>=1.26,<2"` | consistency gate |
| Sunset trigger | All three of {isce3, compass, s1-reader} ship numpy-2-compatible releases. Concrete check: `pip install "numpy>=2.0" compass s1reader isce3` succeeds and `pytest` passes without the four `_patch_*` calls | verifiable |

### Evidence of current upstream status (verified 2026-04-20)

- **isce3** — latest release is v0.25.10 (March 2025). No numpy-2 release announced. The `setup.py` / `meta.yaml` in conda-forge does not advertise numpy-2 support. (Sources: [isce3 releases](https://github.com/isce-framework/isce3/releases), [conda-forge feedstock](https://github.com/conda-forge/isce3-feedstock))
- **compass** — latest release v0.5.6. No PyPI presence for current OPERA-ADT compass. The COMPASS GitHub issues as of 2026-04-20 contain **no active numpy-2 tracker**. (Source: [COMPASS issues](https://github.com/opera-adt/COMPASS/issues))
- **s1-reader** — latest release v0.2.5 (May 2024). No numpy constraint in `requirements.txt` but the `s1_burst_slc.polyfit()` call uses `%f`-format on a numpy array which numpy 2.x rejects. (Source: repo source inspection)
- **pybind11 baseline** — numpy-2 build compatibility requires pybind11 ≥ 2.12.0 ([scipy PR #20347](https://github.com/scipy/scipy/pull/20347)). isce3's conda-forge build currently pins pybind11 < 2.12 for `0.25.x` series. A future isce3 0.26+ rebuild against pybind11 ≥ 2.12 is the precondition for numpy-2 migration across the ADT stack.

### Transitive-dep risk under `numpy<2`

Cross-check against v1.0 stack, verified 2026-04-20:

| Package | Latest (2026-04) | Min numpy | numpy-1.26 support | Status |
|---|---|---|---|---|
| dolphin 0.42.5 | 2026-03-18 | `>=1.23` | YES | safe |
| MintPy 1.6.3 | 2025-11 | `>=1.20` | YES | safe |
| xarray 2024.10+ | 2026-Q1 | `>=1.26` | YES (1.26 is the floor) | safe |
| rasterio 1.4–1.5 | 2026 | `>=1.24` | YES | safe |
| rioxarray 0.22.0 | 2026 | follows xarray | YES | safe |
| scipy 1.14 | 2026 | `>=1.23.5,<2.6` | YES | safe |
| scikit-image 0.24+ | 2026 | `>=1.23` | YES | safe |
| geopandas >=1.0 | 2026 | `>=1.23` | YES | safe |
| h5py 3.12+ | 2026 | `>=1.19` | YES | safe |
| numba (dolphin transitive) | 2026 | `>=1.22,<2.2` | YES | safe |

**Verdict: no transitive dep breaks under `numpy<2.0`.** The pin costs nothing beyond missing numpy-2 performance improvements.

---

## 2. tophu as first-class dependency

### Recommendation

| Item | Value | Source |
|---|---|---|
| Install channel | **conda-forge only** (`- tophu=0.2.1` in `conda-env.yml` `dependencies:` block — NOT the `pip:` sub-block) | tophu is **not on PyPI**; a `pip install tophu` fails with 404 |
| Version | `tophu=0.2.1` | Latest on conda-forge since 2024-02-14; no newer release in the isce-framework/tophu GitHub releases as of 2026-04-20 |

### Root cause of the v1.0 ImportError

dolphin's `dolphin.unwrap.__init__.py` does `from ._tophu import *` unconditionally, but `_tophu.py` defers the actual `import tophu` to inside `multiscale_unwrap()` — so **module-level `from dolphin.unwrap import run` does NOT fail** on a tophu-less env. The v1.0 breakage happens at runtime, when the dispatcher in `_unwrap.py` routes `UnwrapMethod.PHASS` or `UnwrapMethod.ICU` through `multiscale_unwrap()` (verified by inspection of upstream source at `isce-framework/dolphin@main`). Our production config uses `UnwrapMethod.PHASS` (see `src/subsideo/products/disp.py:118`), so every real DISP run hits the tophu path.

**Correction to BOOTSTRAP_V1.1.md §0.2:** the instruction "Add tophu to `conda-env.yml`'s `pip:` block" is wrong — tophu is conda-forge-only. It must go in the top-level `dependencies:` block.

### Regression test

The asserted test `from dolphin.unwrap import run` does **not** verify the fix, because that import succeeds even without tophu. Use instead:

```python
def test_tophu_importable_on_clean_env():
    import tophu  # noqa: F401
```

Or, to match the actual runtime failure mode:

```python
def test_dolphin_multiscale_unwrap_callable():
    from dolphin.unwrap._tophu import multiscale_unwrap  # noqa: F401
    # Will fail with ImportError only when tophu is missing and multiscale_unwrap is invoked
    # but the symbol itself imports fine either way.
    import tophu  # noqa: F401 — the real gate
```

---

## 3. rio_cogeo centralisation

### Recommendation

| Item | Value | Rationale |
|---|---|---|
| Pin | `rio-cogeo==6.0.0` (do NOT move to 7.x) | rio-cogeo 7.0.0 dropped Python 3.10 support; subsideo's `requires-python = ">=3.10"`. Jumping to 7.x forces a Python bump that's out of scope for v1.1. 6.0.0 has the GDAL ≥3.11 COG driver improvements we want (rasterio 1.5 pulls GDAL ≥3.8 — we're fine for the tag-rename change `OVR_RESAMPLING_ALG → OVERVIEW_RESAMPLING`) |
| Import pattern | **Root-level re-exports, everywhere**: `from rio_cogeo import cog_validate, cog_translate, cog_profiles` | Stable since rio-cogeo 2.1.1 (2021); works in 5.x, 6.x, and 7.x without `try/except` — the `__init__.py` re-exports have not moved |
| Central helper | `src/subsideo/_cog.py` with `cog_validate`, `cog_translate`, `cog_profiles` re-exported once for internal use | Phase 0.3 acceptance gate (`rg "from rio_cogeo" src/` returns only `_cog.py`) |

### Correction to BOOTSTRAP_V1.1.md §0.3

The note "Three product files tripped over the rio-cogeo 7.x `cog_validate` move" is a **misdiagnosis**. `cog_validate` has lived at both `rio_cogeo.cogeo.cog_validate` and top-level `rio_cogeo.cog_validate` (re-export) since 2.1.1 — **it did not move in 7.x**. The v1.0 defensive `try/except` in `src/subsideo/products/dist.py:46-49` was catching a symptom whose real cause was probably:

- (a) an env where rio-cogeo was installed but Python 3.10 prevented 7.x loading (ImportError via unrelated transitive), or
- (b) `from rio_cogeo.cog_validate import cog_validate` referencing a **module-as-attribute** access pattern that depends on whether `cog_validate` submodule is eagerly imported at package init time.

Whichever of (a) or (b) it was, the fix is the same: use the package-root re-export (`from rio_cogeo import cog_validate`), which is stable across all 5.x→7.x releases. v1.0's `src/subsideo/products/rtc.py:139` already does this; the remaining inconsistency is `dist.py` and the `rio_cogeo.cogeo.cog_translate` imports in `dswx.py`, `rtc.py`, and `_metadata.py`. Standardise all on root-level imports through `_cog.py`.

### Release history (verified 2026-04-20 via PyPI JSON)

| Version | Released | Notes |
|---|---|---|
| 7.0.2 | 2026-03-27 | latest — Python 3.11+ only |
| 7.0.1 | 2025-12-15 | Python 3.11+ only |
| 7.0.0 | 2025-11-21 | Python 3.11+ only — **breaking for us** |
| **6.0.0** | **2025-11-05** | **recommended pin** |
| 5.4.2 | 2025-06-27 | previous-generation, still on Python 3.9+ |

---

## 4. macOS multiprocessing

### Recommendation

```python
# src/subsideo/_mp.py
"""Multiprocessing start-method configuration for subsideo product runs.

Forces 'fork' on macOS to work around dist_s1 / opera-rtc deadlocks observed
under the 'spawn' default.  No-op on Linux where 'fork' is already the default
(through Python 3.13; Python 3.14 switches Linux to 'forkserver' — see sunset).
"""
from __future__ import annotations

import multiprocessing as mp
import platform
import sys


def configure_multiprocessing() -> None:
    """Force 'fork' start method on macOS.  Idempotent; safe to call from every
    product entry point.
    """
    if platform.system() != "Darwin":
        return
    try:
        # force=True so subsequent calls from other product modules are no-ops
        # rather than RuntimeError.
        mp.set_start_method("fork", force=True)
    except RuntimeError:
        # already set this interpreter session
        pass
```

**Call at the top of every `run_*()` entry point** (not at module import, so that unit-test imports don't force a start method on import). Also set via the `-X` flag when launching under pytest on macOS: `pytest -X dev` does not help here — instead add an autouse fixture in `tests/conftest.py` that calls `configure_multiprocessing()` before any `multiprocessing`-using test.

### No external library replaces this

There is no production-grade library that wraps "force fork on macOS" — `pebble`, `concurrent.futures`, `joblib`, and `multiprocess` (third-party fork of `multiprocessing`) all accept a `start_method`/`context` parameter but do not globally configure it. The BOOTSTRAP instruction of adding `_mp.py` with stdlib is correct and sufficient.

### Interactions with isce3 / dolphin / dist-s1

- **dist-s1**: uses `concurrent.futures.ProcessPoolExecutor` internally for despeckling. ProcessPoolExecutor inherits the global start method. `fork` is required because the workers use lazily-imported isce3 state that doesn't re-initialise cleanly under `spawn`. (Observed in v1.0 DIST EU session; documented in `CONCLUSIONS_DIST_EU.md`.)
- **opera-rtc**: documents the `if __name__ == "__main__":` guard requirement for `spawn`. With `fork` this requirement is relaxed (fork inherits the module-level state).
- **dolphin**: uses its own `ProcessPoolExecutor`-style fan-out in `dolphin.unwrap`. Works under both `fork` and `spawn`, but `fork` is ~2x faster to spawn workers because it skips the re-import cost.

### Sunset trigger

**Python 3.14 deprecates `fork` as the Linux default** and warns on `fork()` in multi-threaded processes. For macOS specifically, `fork` remains available via `set_start_method("fork", force=True)` but emits `DeprecationWarning` if the process is multi-threaded at fork time. Mitigation path when v1.2 bumps to Python 3.14:

1. Audit each `run_*()` for pre-fork threads (loguru's default handler uses threads — configure `loguru.logger.remove()` then `loguru.logger.add(sink, enqueue=False)` pre-fork, or switch sinks to non-threaded).
2. Migrate to `forkserver` start method on macOS (stable since Python 3.8; ships `spawn`-equivalent safety with fork-like performance after warm-up).

References: [Python 3.14 fork deprecation](https://docs.python.org/3/library/multiprocessing.html), [cpython #84559](https://github.com/python/cpython/issues/84559).

---

## 5. Reference-fetching libraries for v1.1 phases

### 5.1 OPERA DIST-S1 v0.1 CloudFront sample (Phase 4.1)

**Recommendation:** `requests ==2.32.x` (already in v1.0) + `tenacity ==9.1.4`.

```python
# validation/harness.py
import tenacity
import requests

@tenacity.retry(
    stop=tenacity.stop_after_attempt(5),
    wait=tenacity.wait_exponential(multiplier=4, min=4, max=300),
    retry=tenacity.retry_if_exception_type(
        (requests.exceptions.HTTPError, requests.exceptions.ConnectionError)
    ),
    before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
)
def download_from_cloudfront(url: str, dest: Path) -> Path:
    ...
```

- **Why `tenacity`**: decorator-based, exponential-backoff with cap, handles 429/503 plus connection errors, supports `before_sleep` hook for logging — all in one library. Latest 9.1.4 verified on PyPI 2026-04-20.
- **Why not just `requests.adapters.HTTPAdapter` with `urllib3.Retry`**: `urllib3.Retry` only handles HTTP-level errors at the session layer; it doesn't compose with download-resume logic (which you want for >1 GB OPERA samples). `tenacity` + `requests.get(stream=True)` + partial-write-resume is cleaner.
- **No newer alternative worth switching to.** `httpx` has built-in retries but lacks the rich `before_sleep`/`retry_if_exception_type` composability; `stamina` (Hynek's `tenacity` reduction) is simpler but doesn't add anything for this pipeline.

The OPERA CloudFront distribution `d2pn8kiwq2w21t.cloudfront.net` serves HTTPS with no auth (unlike ASF DAAC's Earthdata gate), so the harness must support auth-free CloudFront paths distinct from auth-bearing ASF paths — easy with `tenacity` + `requests.Session` parameterisation.

### 5.2 EFFIS burnt-area products (Phase 4.3)

**Recommendation:** `owslib ==0.35.0` against EFFIS's published WFS endpoint.

- **No maintained Python-EFFIS wrapper exists.** Searches for `pyeffis`, `effis-api`, `effis-wms` on PyPI return zero hits as of 2026-04-20.
- **EFFIS official data-access path (verified from [effis.emergency.copernicus.eu/applications/data-and-services](https://forest-fire.emergency.copernicus.eu/applications/data-and-services)):**
  - WMS: layer rendering only (not useful for metrics).
  - **WFS: feature download** — the canonical programmatic path; returns Shapefile or GeoJSON via GetFeature.
  - Download page / XLSX / Shapefile / SpatiaLite bundles for bulk.
  - "DATA REQUEST FORM" for archival / high-res data not in the standard WFS (slow, manual).
- **Pattern:**

```python
from owslib.wfs import WebFeatureService
import geopandas as gpd
from io import BytesIO

wfs = WebFeatureService(
    url="https://maps.effis.emergency.copernicus.eu/effis/ows",
    version="2.0.0",
)
response = wfs.getfeature(
    typename="ba.effis_current",
    bbox=(xmin, ymin, xmax, ymax, "EPSG:4326"),
    outputFormat="application/json",
)
gdf = gpd.read_file(BytesIO(response.read()))
```

- **`owslib` is dormant but stable** (0.35.0 is the recent release; `geopython/OWSLib` is actively maintained by the geopython org). No replacement library exists — this is the standard for WFS/WMS/WCS in Python.
- **Layer name caveat**: EFFIS WFS layer names are not stable across years; the Phase 4.3 implementation must use WFS `GetCapabilities` to discover `ba.effis_*` layer names at runtime rather than hard-coding.

Confidence: **MEDIUM** — EFFIS WFS endpoint URL (`https://maps.effis.emergency.copernicus.eu/effis/ows`) is the historical canonical URL; in Phase 4.3 implementation the actual GetCapabilities response must be retrieved to confirm the 2026 schema. The EFFIS WFS endpoint has in the past been rate-limited and occasionally returned 503 during peak fire season — use the same `tenacity` retry wrapper.

### 5.3 JRC Monthly History tiles (Phase 5.1, 5.4)

**No change from v1.0.** v1.0 uses direct HTTPS against `jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GSWE/`. The [`stactools-packages/jrc-gsw`](https://github.com/stactools-packages/jrc-gsw) package exists for STAC collection creation but is not useful for raw-tile download, and JRC GSW v1.4 (monthly history through 2021) is still the current version — v1.5 has not been published as of 2026-04-20.

**Packaging caveat:** the JRC FTP server occasionally changes the directory layout (verified monthly-history tiles currently at `/GSWE/MonthlyHistory/VER1-4-0/tiles/`). Phase 5 implementation must not hard-code paths beyond what v1.0 already handles.

### 5.4 ESA WorldCover (Phase 2.1, 3.2)

**Recommendation:** direct COG read from AWS Open Data (`s3://esa-worldcover/v200/2021/map/`) using `rasterio` + `boto3` + `fsspec`/`s3fs` (all already in v1.0 `pyproject.toml`).

- **No new library required.** `rioxarray` can read `s3://esa-worldcover/...` COGs directly via `engine="rasterio"` + `rioxarray.open_rasterio(url)` with an `aws-no-sign` environment variable.
- **Why not `terracatalogueclient`**: requires extra index URL (`--extra-index-url https://artifactory.vgt.vito.be/api/pypi/python-packages/simple`), non-trivial to vendor into a clean env, and adds a JVM-backed OpenSearch client for what we need (point-in-bbox raster lookup) — massive over-engineering.
- **Why not `pystac-client` against Planetary Computer**: introduces an Azure auth path (PC needs a signed token for data access), breaking the CDSE-and-nothing-else discipline. AWS Open Data bucket is unsigned/public.
- **Pattern:**

```python
import os
import rioxarray

os.environ["AWS_NO_SIGN_REQUEST"] = "YES"  # public bucket
tile_url = (
    "s3://esa-worldcover/v200/2021/map/"
    f"ESA_WorldCover_10m_2021_v200_{tile_id}_Map.tif"
)
da = rioxarray.open_rasterio(tile_url, masked=True).squeeze()
mask = da == 60  # class 60 = bare / sparse vegetation
```

Tile ID is a 3° × 3° grid code derived from the burst centroid (e.g. `N33W117`). The ESA WorldCover team publishes a [FlatGeobuf grid index](https://esa-worldcover.s3.amazonaws.com/esa_worldcover_grid.fgb) — read once with `geopandas.read_file` to map burst bbox → tile list.

### 5.5 Slope rasters from GLO-30 DEM (Phase 2.1, 3.2)

**Recommendation:** `gdal.DEMProcessing` (already installed via conda-forge GDAL).

```python
from osgeo import gdal

gdal.DEMProcessing(
    str(slope_tif_path),
    str(dem_tif_path),
    "slope",
    computeEdges=True,
    slopeFormat="degree",
)
```

- **Already in the v1.0 env** via GDAL — no new dep.
- **gdaldem is the reference implementation** for OPERA RTC itself (RTC pipelines use GDAL slope + aspect for layover/shadow masking).
- **Why not `richdem`**: C++ extension with its own build system, adds a conda-forge dep purely for a function we have in GDAL already. richdem is better for hydrology-first workflows (flow accumulation, pit filling); we don't need that.
- **Why not `xdem`**: xDEM is designed for DEM-comparison workflows (elevation-time-series, co-registration) — overkill for "slope < 10° mask" which is one `DEMProcessing` call.
- **Why not `whitebox` (`whitebox-tools`)**: Rust-backed, separate binary; same over-engineering argument as richdem.

**Gotcha:** `gdal.DEMProcessing` slope units. Pass `slopeFormat="degree"` explicitly — the default `"percent"` returns % slope, which compares differently against the "slope < 10°" Phase 2 criterion. GDAL 3.11+ auto-scales when the CRS is geographic, but we should always pass lat-lon DEMs in projected UTM before `DEMProcessing` to avoid the unit conversion entirely.

---

## 6. Fit-set / threshold optimisation (Phase 5.3 — DSWx)

**Recommendation:** `optuna ==4.8.0` for the joint grid search over (WIGT, AWGT, PSWT2_MNDWI) against mean F1 over 12 (AOI, scene) fit-set pairs. **Fallback: pure nested Python loops (stdlib).**

### Analysis

The Phase 5.3 search space is small:

- WIGT ∈ [0.08, 0.20] step 0.005 → 25 points
- AWGT ∈ [−0.1, 0.1] step 0.01 → 21 points
- PSWT2 ∈ [−0.65, −0.35] step 0.02 → 16 points

Cross product = **8,400 configurations × 12 fit-set pairs = 100,800 F1 evaluations.** At ~50 ms per F1 (water mask + JRC diff over a ~3000×3000 pixel tile), this is ~85 minutes serial. Not a large hyperparam problem.

**Pure grid search (stdlib) is completely adequate.** Three nested `for` loops + `concurrent.futures.ProcessPoolExecutor(max_workers=8)` cuts the wall time to ~12 minutes.

### Why include `optuna` anyway

| Reason | Value |
|---|---|
| Persistent study DB (`SQLite` backend) | Restart-safe if fit set changes or pipeline is rerun after env upgrade; re-using the 100k stored F1 scores cuts 85 minutes to seconds |
| Joint Sobol sampler as sanity check | For 2 h budget, Sobol over 100 trials would cover the grid at similar quality with full reproducibility (`seed=42`); useful Phase-6 deliverable for "does the coarser grid give the same optimum?" |
| Parameter importance report | `optuna.importance.get_param_importances()` — free side output; useful for "is AWGT actually useful in EU, or can we fix it at 0?" as a Phase-6 follow-up question |
| Pure F1 on mean over pairs can be defined once | `study.optimize(lambda trial: -mean_f1(...), n_trials=100)` |

### Why not `scikit-optimize`

- Not updated since 2023 (skopt 0.9.0). Dormant; `scipy` compatibility broke in recent releases. ([skopt GitHub](https://github.com/scikit-optimize/scikit-optimize))
- Bayesian-optimisation-only; the flat F1 surface from a grid makes the BO priors degenerate.

### Why not `hyperopt`

- Unmaintained (last release 0.2.7 in 2021); TPE-only.

### Decision

Ship `optuna ==4.8.0` as an **optional** dep in `[project.optional-dependencies] validation`. Provide both a pure-Python grid loop (default, no optuna needed) and an optuna driver for Phase 5.3 restart/replay. Phase 6 documentation notes which was used. Lightest-possible v1.1 commit: zero new deps (just the nested loop). Most-useful-restart-story v1.1 commit: add optuna.

---

## 7. Makefile / `make eval-all` orchestration (Phase 0.7)

**Recommendation:** **GNU make** (not `just`, not `taskfile.dev`).

### Analysis

| Criterion | GNU make | just | taskfile.dev |
|---|---|---|---|
| macOS pre-installed | Yes (xcode CLT) | No (brew install) | No (brew / go install) |
| Linux container pre-installed | Yes (coreutils on almost every base image) | No | No |
| File-dependency tracking | Yes (timestamps) | **No** (command runner only) | Yes (checksums — stronger than make's timestamps) |
| Syntax learning cost | Low (decades-old) | Low | Medium (YAML indents) |
| Variable expansion quirks | `$$` vs `$` confusion | Cleaner | YAML-clean |
| Reproducibility — fresh clone | One command | Requires `just` install first | Requires `task` install first |

### Why GNU make for v1.1 specifically

- **Phase 6.3 closure test:** "fresh clone → `micromamba env create -f conda-env.yml` → `make eval-all`". Adding `just` or `taskfile` breaks "fresh clone → one-command eval" because the user must install the runner first. This is a real ergonomic loss for a library whose main audience is scientists, not devs.
- **The caching needed is timestamp-based on cached intermediates.** Our eval outputs are files-on-disk (`eval-dswx-fitset/*.tif`, etc.). `make`'s `target: prereq` timestamp comparison is exactly the right semantic — we don't need taskfile's checksum overhead.
- **Real-world precedent:** isce-framework and opera-adt repos use `make` (e.g., [opera-adt/COMPASS Makefile](https://github.com/opera-adt/COMPASS)). Staying ecosystem-local.
- **taskfile's YAML** becomes verbose quickly for a pipeline with 10+ eval targets, each with its own Python-script invocation.

**Recommended Makefile skeleton (terse, not a full spec):**

```make
SHELL := /bin/bash
RESULTS_DIR := results
PYTHON ?= micromamba run -n subsideo python

.PHONY: eval-all eval-nam eval-eu clean

eval-all: $(RESULTS_DIR)/matrix.md

$(RESULTS_DIR)/matrix.md: eval-rtc-nam eval-rtc-eu eval-cslc-nam eval-cslc-eu \
                          eval-disp-nam eval-disp-eu eval-dist-nam eval-dist-eu \
                          eval-dswx-nam eval-dswx-eu
	$(PYTHON) -m subsideo.validation.matrix --out $@

eval-rtc-nam: eval-rtc/conclusions.json
eval-rtc/conclusions.json: run_eval.py
	$(PYTHON) $< && touch $@

eval-rtc-eu: eval-rtc-eu/conclusions.json
# ...

clean:
	@echo "Refusing to clean eval-*/ caches without explicit prompt."
```

### Escape hatch

If `taskfile` is desired later (e.g. for cross-platform Windows support — currently out of scope), migration is mechanical: `task` can reuse the exact shell recipes.

---

## 8. Watchdog / timeout (Phase 0.4)

**Recommendation:** **stdlib `multiprocessing.Process.join(timeout=…)` + `Process.terminate()`** for the outer `run_*()` watchdog. Use `pebble.ProcessPool` **only** if the existing `ProcessPoolExecutor` fan-out inside `_run_unwrapping` needs per-task timeouts (not currently the scope).

### Analysis

| Approach | Abort inner process | Kill grandchildren | Platform | Complexity |
|---|---|---|---|---|
| `signal.SIGALRM` | Yes (signal handler) | No | UNIX only (no Windows, broken on threaded programs) | Low but fragile |
| `multiprocessing.Process.join(timeout)` + `terminate()` | Yes | **No** (grandchildren orphaned) | All | Low |
| `pebble.ProcessPool(...).future.result(timeout=...)` | Yes | Best-effort via `timeout` | All | Medium |
| `wrapt-timeout-decorator` | Yes (spawns subprocess) | No | All | Low but adds dep |
| `concurrent.futures.ProcessPoolExecutor` | No (no timeout param in `submit`) | — | — | Not suitable |

### Concrete pattern for Phase 0.4

```python
# src/subsideo/_watchdog.py
import multiprocessing as mp
import time
from typing import Callable


def run_with_watchdog(
    target: Callable[..., None],
    args: tuple = (),
    kwargs: dict | None = None,
    timeout_s: float = 3600,
    progress_file: str | None = None,
    stall_window_s: float = 900,
) -> None:
    """Run target in a subprocess.  Abort after timeout_s, or earlier if
    progress_file hasn't been touched in stall_window_s.
    """
    kwargs = kwargs or {}
    ctx = mp.get_context("fork")  # we already forced fork in _mp.py
    proc = ctx.Process(target=target, args=args, kwargs=kwargs)
    proc.start()
    t0 = time.monotonic()
    last_touch = t0
    while proc.is_alive():
        if time.monotonic() - t0 > timeout_s:
            proc.terminate()
            proc.join(5)
            if proc.is_alive():
                proc.kill()
            raise TimeoutError(f"Hard timeout after {timeout_s}s")
        if progress_file and Path(progress_file).exists():
            mtime = Path(progress_file).stat().st_mtime
            if mtime > last_touch:
                last_touch = mtime
        elif progress_file and time.monotonic() - last_touch > stall_window_s:
            proc.terminate()
            proc.join(5)
            if proc.is_alive():
                proc.kill()
            raise TimeoutError(
                f"No progress file updates in {stall_window_s}s"
            )
        time.sleep(10)
    proc.join()
```

### Why not `pebble` as the primary

`pebble` is excellent for "fire a pool of callable tasks, cap each by a timeout." Our Phase 0.4 need is "one long-running product run, terminate cleanly after a stall." Stdlib covers this in ~30 LOC; adding `pebble` as a top-level dep for two calls is unjustified.

**However:** if Phase 0.4's "abort despeckle worker at 2× expected wall time" targets the individual despeckle worker (inside dist_s1's internal `ProcessPoolExecutor`), that's a per-task timeout inside a pool — and switching dist_s1's pool to `pebble.ProcessPool` would be overreach into dist_s1 internals. Not recommended.

### Orphan-process risk

Both stdlib `terminate()` and `pebble` can leave orphaned grandchildren (workers of the dist_s1 internal pool, still holding GDAL dataset handles). Mitigation:

- Put `proc.start()` under a `setsid()` via `os.setsid()` (fork preexec) so the whole group receives the signal on terminate.
- Alternatively: use `os.killpg(os.getpgid(proc.pid), signal.SIGTERM)` in the abort handler.

Confidence: **MEDIUM** — Phase 0.4 observed macOS hangs may have additional root causes beyond "no orphan group kill". Validate with 3 consecutive runs as acceptance gate.

### External-library alternative worth considering

`subprocess.run(args, timeout=…)` if the dist_s1 entry point can be shelled out instead of imported. This gives clean process-group termination via `subprocess.TimeoutExpired` handling. If dist_s1 ships a CLI (`dist-s1 run ...`), shelling out is strictly better than in-process. **Worth verifying during Phase 0.4 implementation.**

---

## 9. Are v1.0 libraries superseded?

### 9.1 dem-stitcher — **No change.** Still recommended.

- **Current: v2.5.13 (2026-02-09)** verified via PyPI JSON 2026-04-20.
- No meaningful competitor. `sardem` (ASF HyP3's DEM fetcher) is less capable (doesn't handle GLO-30 geoid-to-ellipsoid). `cop-dem-staging` is an in-house OPERA utility, not publicly distributed.
- One **v1.1 integration point**: programmatic DEM bounds from burst ID (BOOTSTRAP §0.6). Use:

  ```python
  from opera_utils.burst_frame_db import get_burst_id_geojson
  gj = get_burst_id_geojson(burst_ids=[burst_id])  # returns GeoDataFrame
  bbox = tuple(gj.total_bounds) + (-0.2, -0.2, 0.2, 0.2)  # buffer in degrees
  dem, profile = stitch_dem(bbox, dem_name="glo_30", dst_ellipsoidal_height=True)
  ```

### 9.2 opera-utils — **No change.** Still recommended.

- **Current: v0.25.6 (2026-03-18)** verified via PyPI JSON 2026-04-20.
- v0.25.x adds `opera_utils.burst_frame_db.get_burst_id_geojson()` and `get_burst_geodataframe()` as the programmatic bounds helpers for Phase 0.6 — **no need to write a custom burst→bbox helper**. The module already exposes:
  - `get_burst_id_geojson(burst_ids=[...]) → GeoDataFrame`
  - `get_burst_geodataframe() → GeoDataFrame` (full table)
  - `get_frame_bbox(frame_id) → tuple[float, float, float, float]`
  - `get_intersecting_frames(bbox) → list[int]`
- **Confirm presence in the EU-extended burst DB.** subsideo's EU burst DB augments the opera-utils schema, so Phase 0.6 helper should first try `opera_utils.burst_frame_db.get_burst_id_geojson(...)`, then fall back to the EU DB via `subsideo.burst.db.query(...)`.

### 9.3 pyaps3 — **Upgrade to 0.3.7 (verified 2026-04-20).**

- v1.0 pinned `pyaps3 == 0.3.6` for the Feb 2025 CDS API migration. **Latest PyPI is 0.3.7** (verified PyPI JSON 2026-04-20).
- **Not a blocker for v1.1**; v1.1 Phase 3 explicitly spins DISP unwrapper / ERA5 investigation out to the DISP Unwrapper Selection follow-up milestone. Pin can stay at 0.3.6 for this milestone, with a Future-Work bump to 0.3.7.
- No credible alternative. `phase-o-matic` exists as a lighter xarray-first ERA5 delay tool, but it is unverified, has no published comparison against pyaps3, and isn't adopted by MintPy — switching would force rewriting MintPy's correct_troposphere path. Not in scope.

**Verdict: no change for v1.1. Bump to 0.3.7 is a trivial Future-Work item.**

### 9.4 Everything else

All other v1.0 stack libraries verified current and unchanged:

| v1.0 pick | v1.0 version | Latest (2026-04-20) | Action |
|---|---|---|---|
| asf-search | 12.0.6 | 12.0.7 | Bump to 12.0.7 (trivial patch) |
| earthaccess | 0.17.0 | 0.17.0 | Same |
| pystac-client | 0.9.0 | 0.9.0 | Same |
| sentineleof | 0.11.1 | 0.11.1 | Same |
| rasterio | 1.5.0 | 1.5.x | Same |
| rioxarray | 0.22.0 | 0.22.x | Same |
| MintPy | 1.6.3 | 1.6.3 | Same |
| dolphin | 0.42.5 | 0.42.5 | Same |
| dist-s1 | 2.0.13 | 2.0.14 (2026-04-20) | Bump to 2.0.14 |

---

## Full conda-env.yml delta for v1.1

```diff
  name: subsideo
  channels:
    - conda-forge
    - nodefaults
  dependencies:
    - python=3.11
    - isce3=0.25.10
    - compass=0.5.6
    - s1reader=0.2.5
    - dolphin=0.42.5
+   - tophu=0.2.1              # v1.1 §0.2 — conda-forge only (not on PyPI);
+                              # dolphin's multiscale_unwrap() path (PHASS/ICU)
+                              # imports tophu at first call
    - snaphu-py=0.4.1
    - mintpy=1.6.3
    - dist-s1=2.0.14            # bumped from 2.0.13
    - gdal>=3.11
    - rasterio=1.5.*
    - rioxarray=0.22.*
    - geopandas>=1.0
    - shapely>=2.0
    - pyproj=3.7.*
    - xarray>=2024.11
    - h5py>=3.12
-   - numpy>=1.26
+   - numpy>=1.26,<2.0          # v1.1 §0.1 — compass/s1-reader incompat
    - scipy>=1.14
    - pip
    - pip:
      - opera-utils==0.25.6
      - dem-stitcher==2.5.13
      - asf-search==12.0.7      # bumped from 12.0.6
      - earthaccess==0.17.0
      - sentineleof==0.11.1
      - s1-orbits==0.2.0
      - pyaps3==0.3.6
      - pystac-client==0.9.0
      - boto3>=1.36
-     - rio-cogeo==7.0.2
+     - rio-cogeo==6.0.0         # v1.1 §0.3 — 7.x drops Python 3.10
      - typer==0.24.1
      - pydantic-settings==2.13.1
      - loguru==0.7.3
      - tenacity==9.1.4          # v1.1 §0.5 — retry harness (CloudFront + ASF)
      - owslib==0.35.0           # v1.1 §5.2 — EFFIS WFS burnt-area
      - matplotlib
      - jinja2
      - scikit-image>=0.24
      - EGMStoolkit==0.2.15
      # optional extras below, used only for Phase 5.3 threshold recalibration
      - optuna==4.8.0            # v1.1 §6 — threshold grid search (optional)
```

---

## What to explicitly NOT add

| Avoid | Why (v1.1 context) | Use Instead |
|---|---|---|
| `pip install tophu` | Not on PyPI; returns 404 | conda-forge `tophu=0.2.1` |
| `rio-cogeo ==7.x` | Drops Python 3.10 support; subsideo targets 3.10+ | `rio-cogeo ==6.0.0` |
| Defensive `try/except ImportError` around `rio_cogeo.cog_validate` | There was no actual API move in 7.x; the v1.0 defensive code is debugging a different symptom | Single import: `from rio_cogeo import cog_validate, cog_translate, cog_profiles` via `subsideo._cog` |
| `richdem` / `xdem` / `whitebox-tools` for slope | We already have GDAL in the env | `gdal.DEMProcessing(..., "slope", slopeFormat="degree")` |
| `terracatalogueclient` for ESA WorldCover | Requires VITO extra index URL; heavyweight | Direct S3 read from `s3://esa-worldcover/` (AWS_NO_SIGN) via rioxarray |
| `phase-o-matic` as pyaps3 replacement | Unverified; not MintPy-compatible | `pyaps3>=0.3.6` (keep v1.0 choice) |
| `just` / `taskfile.dev` | Extra install required before `make eval-all`; breaks fresh-clone acceptance | GNU `make` (preinstalled on macOS + all Linux base images) |
| `pebble.ProcessPool` as primary watchdog | Overreach; adds top-level dep for one call site | stdlib `multiprocessing.Process.join(timeout=…)` + `os.killpg` |
| `hyperopt` / `scikit-optimize` | Unmaintained; skopt broken on recent scipy; hyperopt frozen at 0.2.7 from 2021 | `optuna==4.8.0` (optional) or pure-Python nested loop |
| `sentinelsat` for CDSE | v1.0 already retired; CDSE OData API deprecated | pystac-client + boto3 (v1.0 choice) |
| `stactools-packages/jrc-gsw` for JRC download | Geared at STAC-collection metadata, not raw tile fetch | Direct HTTPS against `jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GSWE/` |

---

## Version Compatibility Matrix (v1.1-specific)

| Package | Compatible With | Notes |
|---|---|---|
| numpy `<2.0` | isce3 0.25.x, compass 0.5.6, s1-reader 0.2.5 | v1.1 pin required; sunset when isce3 rebuilds against pybind11≥2.12 |
| tophu 0.2.1 | dolphin 0.42.5, snaphu-py 0.4.1 | Must be installed alongside dolphin regardless of unwrap_method when using PHASS/ICU |
| rio-cogeo 6.0.0 | Python ≥3.10, rasterio 1.4+ (via GDAL ≥3.8), pydantic ≥2 | Stay on 6.x until v1.2 considers a Python 3.12+ baseline |
| tenacity 9.x | Python ≥3.9 | Major version 9 dropped Python 3.7/3.8 — no concern for subsideo |
| owslib 0.35 | lxml (conda-forge), pyproj 3.x | Installed via pip alongside pyproj from conda |
| optuna 4.8 | Python ≥3.8, alembic, sqlalchemy | SQLite backend default; no RDBMS required |
| Python 3.11 | all of the above | Do NOT bump to 3.14 for v1.1 — `fork` deprecation warnings cascade |

---

## Sunset conditions for v1.1 temporary pins

| Pin | Trigger to remove | Effort |
|---|---|---|
| `numpy<2.0` | isce3 ≥0.26 + compass numpy-2 release + s1-reader numpy-2 release all present on conda-forge; `pytest` green without the four `_patch_*` calls | 1 day verification + remove patches |
| `rio-cogeo==6.0.0` | subsideo baseline Python bumps to ≥3.11 (v1.2 scope) | 1 hour: bump pin, run COG validation smoke tests |
| `dist-s1==2.0.14` | dist-s1 2.1+ adds fork-safe despeckler (upstream fix, not ours) | Monitor upstream; no subsideo-side work when it lands |
| `tophu` as conda-forge-pinned | dolphin ≥0.43 makes tophu a declared optional dependency with clean ImportError guards, AND tophu ships to PyPI (currently: neither) | N/A — neither upstream change is scheduled |
| macOS `fork` start method | Python 3.14 baseline; audit pre-fork threads and migrate to `forkserver` | 2-3 days: audit loguru sinks, restructure product entry points |

---

## Sources (verified 2026-04-20)

- **numpy / pybind11**
  - [NumPy 2.0 migration guide](https://numpy.org/doc/stable/numpy_2_0_migration_guide.html)
  - [scipy PR #20347 — pybind11 ≥2.12.0 for numpy 2.0](https://github.com/scipy/scipy/pull/20347)
  - [Ecosystem compatibility issue tracker](https://github.com/numpy/numpy/issues/26191)
- **ISCE / dolphin / tophu**
  - [isce3 releases (latest v0.25.10)](https://github.com/isce-framework/isce3/releases)
  - [dolphin releases (latest v0.42.5 on PyPI, 2026-03-18)](https://pypi.org/project/dolphin/)
  - [dolphin unwrap/__init__.py — unconditional `from ._tophu import *`](https://github.com/isce-framework/dolphin/blob/main/src/dolphin/unwrap/__init__.py)
  - [dolphin unwrap/_tophu.py — deferred tophu import inside multiscale_unwrap()](https://github.com/isce-framework/dolphin/blob/main/src/dolphin/unwrap/_tophu.py)
  - [tophu conda-forge feedstock (v0.2.1, no PyPI)](https://anaconda.org/conda-forge/tophu)
- **COMPASS / s1-reader**
  - [COMPASS repo (no numpy-2 issue tracker as of 2026-04-20)](https://github.com/opera-adt/COMPASS/issues)
  - [s1-reader latest v0.2.5](https://github.com/isce-framework/s1-reader/releases)
- **rio-cogeo**
  - [rio-cogeo CHANGES.md — 7.0.0 drops Python 3.10](https://github.com/cogeotiff/rio-cogeo/blob/main/CHANGES.md)
  - [rio-cogeo __init__.py — root-level re-exports of cog_validate/cog_translate since 2.1.1](https://github.com/cogeotiff/rio-cogeo/blob/main/rio_cogeo/__init__.py)
  - PyPI JSON: latest 7.0.2 (2026-03-27); 6.0.0 (2025-11-05)
- **macOS / multiprocessing**
  - [Python 3.14 multiprocessing docs — fork no longer default](https://docs.python.org/3/library/multiprocessing.html)
  - [cpython #84559 — fork broken with threads](https://github.com/python/cpython/issues/84559)
- **OPERA CloudFront**
  - [OPERA documents CDN](https://d2pn8kiwq2w21t.cloudfront.net/) — unauth HTTPS
- **EFFIS**
  - [EFFIS Data and Services](https://forest-fire.emergency.copernicus.eu/applications/data-and-services) — WMS/WFS endpoints
  - [OWSLib 0.35.0](https://pypi.org/project/OWSLib/) — the only maintained OGC Python client
- **JRC GSW**
  - [JRC GSW Downloads page](https://global-surface-water.appspot.com/download)
  - [stactools-packages/jrc-gsw](https://github.com/stactools-packages/jrc-gsw) (STAC only, not raw tiles)
- **ESA WorldCover**
  - [ESA WorldCover Data Access (s3://esa-worldcover/ public bucket)](https://esa-worldcover.org/en/data-access)
- **Slope / DEM**
  - [gdaldem slope docs](https://gdal.org/en/stable/programs/gdaldem.html)
  - [xDEM terrain attributes](https://xdem.readthedocs.io/en/stable/terrain.html)
- **Optuna / hyperparam**
  - [Optuna 4.8.0 docs](https://optuna.readthedocs.io/)
- **Make vs alternatives**
  - [Applied Go — "Just Make a Task" comparison](https://appliedgo.net/spotlight/just-make-a-task/)
  - [tsh.io — Taskfile vs GNU make](https://tsh.io/blog/taskfile-or-gnu-make-for-automation)
- **Watchdog / timeout**
  - [Pebble 5.2.0 docs](https://pebble.readthedocs.io/)
  - [Alexandra Zaharia — function timeout in Python multiprocessing](https://alexandra-zaharia.github.io/posts/function-timeout-in-python-multiprocessing/)
- **Upgrade candidates**
  - [dem-stitcher 2.5.13 on PyPI (2026-02-09)](https://pypi.org/project/dem-stitcher/)
  - [opera-utils 0.25.6 on PyPI (2026-03-18)](https://pypi.org/project/opera-utils/)
  - [pyaps3 0.3.7 on PyPI](https://pypi.org/project/pyaps3/)
  - [asf-search 12.0.7 on PyPI (2026-04-13)](https://pypi.org/project/asf-search/)
  - [dist-s1 2.0.14 on PyPI (2026-04-20)](https://pypi.org/project/dist-s1/)

---

*Stack research for: subsideo v1.1 N.Am./EU Validation Parity & Scientific PASS*
*Researched: 2026-04-20*
*Superseded by: future v1.2 milestone research (when numpy<2 pin, rio-cogeo 6 pin, or macOS fork workaround can be dropped)*
