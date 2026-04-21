# Architecture Patterns

**Domain:** v1.1 validation-framework extensions for an existing SAR/InSAR geospatial library (subsideo)
**Researched:** 2026-04-20
**Confidence:** HIGH — grounded in the shipped v1.0 layout (`src/subsideo/` inspected directly), BOOTSTRAP_V1.1.md (read in full), and the v1.0 ARCHITECTURE.md for continuity. Every recommendation is tied to an existing v1.0 convention.

---

## Context: v1.0 as the Baseline

v1.0 shipped with this layout (verified by `ls src/subsideo/`):

```
src/subsideo/
├── __init__.py              # one line: __version__
├── _metadata.py             # TOP-LEVEL PRIVATE MODULE (leading underscore) — OPERA metadata injection
├── cli.py                   # typer app, 7 subcommands
├── config.py                # Pydantic BaseSettings
├── burst/                   # db.py, frames.py
├── data/                    # cdse.py, asf.py, dem.py, orbits.py, ionosphere.py
├── products/                # rtc.py, cslc.py, disp.py, dswx.py, dist.py, types.py
├── validation/              # compare_{rtc,cslc,disp,dist,dswx}.py, metrics.py, report.py, templates/
└── utils/                   # logging.py, projections.py
```

**Two conventions matter for v1.1 placement decisions:**

1. **Leading-underscore top-level modules exist** — `_metadata.py` is the precedent. It is a cross-cutting private helper that injects OPERA metadata into every product format and is imported by `products/*.py`. It lives at the top level (not in `utils/`) because it is a first-class internal concern with a narrow public surface.
2. **`utils/` holds general-purpose utilities** — `logging.py` (loguru setup) and `projections.py` (pyproj wrappers). Both are stateless, domain-agnostic helpers, not cross-cutting infrastructure with behavioural side effects.

This distinction drives the `_cog` / `_mp` placement recommendation below.

Eval scripts live at repo root, all nine of them: `run_eval.py`, `run_eval_cslc.py`, `run_eval_disp.py`, `run_eval_disp_egms.py`, `run_eval_dist.py`, `run_eval_dist_eu.py`, `run_eval_dist_eu_nov15.py`, `run_eval_dswx.py`, `find_scene.py`. Total ~3,490 LOC across eval scripts (~388 avg; `run_eval_disp.py` is 844 LOC, mostly plumbing).

Cache dirs sit alongside eval scripts: `eval-cslc/`, `eval-disp/`, `eval-disp-egms/`, `eval-dist/`, `eval-dist-eu/`, `eval-dist-eu-nov15/`, `eval-dswx/`, `eval-rtc/`. One per eval run, sibling to the script that produces it.

---

## v1.1 Module Placement Recommendations

### 1. `subsideo.validation.harness` — validation-plumbing module

**Path:** `src/subsideo/validation/harness.py` (single file, not a subpackage).

**Rationale:**
- The harness is a **validation-framework concern**, not a product concern and not a general utility. It belongs inside `validation/` alongside the `compare_*` modules it serves. Creating a new top-level `subsideo.eval/` package would fragment the validation surface across two import roots.
- A single `harness.py` file is the right granularity: BOOTSTRAP §0.5 specifies exactly four named helpers plus the credential preflight. Total estimated size ~250–350 LOC — well under the split threshold. If the module grows past ~600 LOC in a future milestone, promote to `validation/harness/` package then.
- `compare_*.py` modules stay single-file per product (matching the existing pattern); `harness.py` joins them as peer.

**Public API surface (export from `validation/__init__.py`):**

```python
# subsideo/validation/harness.py
def select_opera_frame_by_utc_hour(
    frames: list[dict],
    burst_utc_hour: int,
    burst_bbox: tuple[float, float, float, float],
) -> dict | None: ...

def download_reference_with_retry(
    urls: list[str],
    out_dir: Path,
    auth: Any | None = None,
    backoff_cap_s: int = 300,
    max_attempts: int = 6,
) -> list[Path]: ...

def ensure_resume_safe(
    output_paths: list[Path],
    checker_fn: Callable[[Path], bool],
) -> bool: ...  # True → outputs complete, skip the stage

def credential_preflight(
    required: list[str] = ["EARTHDATA", "CDSE_OAUTH", "CDSE_S3", "CDSAPIRC"],
) -> None: ...  # raises RuntimeError with setup URLs on failure

# Helper added in Phase 0.6 — lives in the harness because it's eval-script-shared
def bounds_for_burst(
    burst_id: str,
    buffer_deg: float = 0.2,
) -> tuple[float, float, float, float]: ...
```

**Private (module-scoped, leading underscore):** retry state machine, exponential backoff curve, any per-source auth adapters (`_earthdata_session`, `_cloudfront_headers`, etc.).

**Circular-import safety:**
- `validation.harness` must NOT import from `subsideo.products` — harness is used in eval scripts that already orchestrate `products` calls separately.
- `validation.harness` MAY import from `subsideo.data` (for `CDSEClient`, `fetch_*`) and from `subsideo.burst` (for bounds_for_burst → `opera_utils.burst_frame_db`).
- `validation.harness` MAY import from `subsideo.utils` (logging, projections).
- `subsideo.products.*` must NOT import from `validation.*`. This is already the convention in v1.0; v1.1 preserves it.

### 2. `_cog.py` and `_mp.py` — top-level private modules

**Paths:**
- `src/subsideo/_cog.py`
- `src/subsideo/_mp.py`

**Rationale:**
- **Precedent is explicit.** `src/subsideo/_metadata.py` is already a top-level leading-underscore private module used by multiple `products/*.py` files. BOOTSTRAP §0.3 and §0.4 use the same naming (`_cog`, `_mp`) — this is deliberate continuity, not accident.
- **Not `utils/`** because utils contains stateless domain-agnostic helpers (logging setup, pyproj wrappers). `_cog` wraps a third-party version-drift workaround; `_mp` mutates interpreter-global state (start method). Both are cross-cutting infrastructure patches with side effects, not general utilities. The `_metadata.py` convention already sorts this class of concern to the top level.
- **Leading underscore signals: internal API, no external stability contract.** This matches BOOTSTRAP's wording ("private module").

**`_cog.py` public surface:**
```python
# version-aware re-exports
def cog_validate(path: str | Path) -> tuple[bool, list, list]: ...
def cog_translate(src: str, dst: str, profile: dict, **kwargs) -> None: ...
# version sentinel for conditional code paths
RIO_COGEO_VERSION: tuple[int, int, int]
```

Single source of truth. Replaces the four existing inline `try/except ImportError` blocks currently scattered across `products/rtc.py`, `products/dswx.py`, `products/dist.py`, and `_metadata.py`. Acceptance check in BOOTSTRAP §0.3 (`rg "from rio_cogeo" src/` returns only this helper) is the exit gate.

**`_mp.py` public surface:**
```python
def configure_multiprocessing() -> None:
    """Force 'fork' start method on macOS; no-op on Linux (already fork)."""

def watchdog(
    expected_wall_time_s: float,
    multiplier: float = 2.0,
) -> ContextManager[None]:
    """Abort the enclosing call if wall-clock exceeds multiplier × expected
    AND 0-throughput heuristic trips (no log lines for >30s)."""
```

Called at the top of each `run_*()` product entry point in `products/`. Both functions are idempotent-safe on repeat invocation.

**Circular-import safety:**
- `_cog` and `_mp` import only stdlib and third-party libs (`rio_cogeo`, `multiprocessing`). They import nothing from subsideo — they are leaves in the import graph.
- `products/*.py` import them at module top; this is safe because `_cog`/`_mp` have no subsideo deps.

### 3. `subsideo.validation.compare_disp.prepare_for_reference()` placement

**Path:** extend the existing `src/subsideo/validation/compare_disp.py` — do NOT create a new `adapters.py`.

**Rationale:**
- `compare_disp.py` already owns the two DISP-specific comparison paths (`compare_disp` for EGMS Ortho raster, `compare_disp_egms_l2a` for EGMS L2a point cloud) and already contains the equivalent ad-hoc multilook/reprojection logic inside `compare_disp()` Step 2. BOOTSTRAP §3.1 says the adapter "replaces the ad-hoc bilinear reprojection currently in `run_eval_disp.py` Stage 9" — i.e., it extracts an existing pattern.
- A separate `validation/adapters.py` module would require ALL product-comparison modules to adopt an adapter abstraction upfront. That is speculative generality — only DISP needs the native→reference multilook step in v1.1. RTC operates at the reference grid natively; CSLC amplitude comparison is per-pixel at the product grid; DIST compares categorical rasters with no grid-conversion step; DSWx is compared directly to JRC at JRC's 30m grid.
- **Promotion rule:** if a second product needs a reference-grid adapter in a future milestone (e.g. CSLC native-resolution gate in the Unwrapper Selection follow-up), promote `prepare_for_reference` + DISP's helpers into `validation/adapters.py` then. Premature extraction now is architectural over-commitment.

**Public API:**
```python
# subsideo/validation/compare_disp.py — add alongside compare_disp()
def prepare_for_reference(
    native_velocity: Path | np.ndarray,  # 5×10 m native grid
    reference_grid: Path | rasterio.io.DatasetReader,  # target grid
    method: Literal["multilook_mean", "bilinear", "point_sample"] = "multilook_mean",
) -> np.ndarray:  # velocity on reference grid, ready for metric computation
```

Module docstring gets a new paragraph: "The `prepare_for_reference` adapter converts subsideo's native 5×10 m DISP velocity to a reference grid (OPERA DISP 30m or EGMS L2a PS points) for comparison. This is validation-only infrastructure; production DISP output remains at native resolution."

### 4. DSWx threshold constants (Phase 5.3)

**Path:** `src/subsideo/products/dswx_thresholds.py` — constants module with provenance metadata, imported by `products/dswx.py`.

**Rationale for this over the other three options:**
| Option | Reproducibility | Region-override ease | Recommend |
|--------|-----------------|----------------------|-----------|
| Hardcoded in `dswx.py` (v1.0) | ✓ git-tracked | ✗ requires code edit | No — loses provenance metadata |
| **Constants module with provenance** | **✓ git-tracked + docstring** | **✓ import + override** | **YES** |
| YAML/JSON shipped in package | ✓ git-tracked | ✓ editable without code | No — adds runtime file I/O, no type safety |
| pydantic-settings overridable | ✓ env-settable | ✓ per-run override | Partial — use as complement, not replacement |

**Why constants module wins:** reproducibility is the dominant requirement for v1.1 (BOOTSTRAP §5.3 mandates "frozen constants" + "reproducibility notebook"). A Python module with typed constants and a top-of-file docstring tying each threshold to its grid-search run gives the strongest reproducibility story:

```python
# src/subsideo/products/dswx_thresholds.py
"""DSWE threshold constants for DSWx-S2 surface-water classification.

Each region's constants are derived from a documented grid-search run.
Update only via the recalibration workflow in
scripts/recalibrate_dswe_thresholds.py. Never edit in place without
updating PROVENANCE below and the corresponding notebook under
notebooks/dswx_recalibration.ipynb.
"""
from __future__ import annotations
from typing import Literal, NamedTuple

class DSWEThresholds(NamedTuple):
    WIGT: float          # MNDWI water index
    AWGT: float          # AWEI
    PSWT2_MNDWI: float   # partial surface water test 2
    PSWT2_BLUE: float    # ...etc
    # Full DSWE threshold set

# Region: North America (OPERA DSWx-HLS defaults, Landsat-fit)
NAM_LANDSAT = DSWEThresholds(WIGT=0.124, AWGT=0.0, PSWT2_MNDWI=-0.50, ...)

# Region: European Union (grid-searched 2026-04-XX, fit set = 12 AOI pairs)
# Provenance: scripts/recalibrate_dswe_thresholds.py run of YYYY-MM-DD,
# F1 on held-out Balaton = X.XXX, see notebooks/dswx_recalibration.ipynb
EU_S2 = DSWEThresholds(WIGT=0.XXX, AWGT=0.XX, PSWT2_MNDWI=-0.XX, ...)

# Lookup by region tag
THRESHOLDS: dict[str, DSWEThresholds] = {
    "nam": NAM_LANDSAT,
    "eu":  EU_S2,
}
```

**pydantic-settings integration (complement, not replacement):** add an optional `DSWX_REGION` setting to `subsideo.config.Settings` that selects which threshold set `products/dswx.py` imports at runtime. This enables region override via env/`.env` without duplicating constants across config files. The canonical values stay in `dswx_thresholds.py`; settings only choose which set to activate.

**Future extensibility:** third region (v2 global milestone) adds a new `NamedTuple` constant and key in `THRESHOLDS`. No schema change.

### 5. Eval scripts — location and invocation

**Recommendation: leave `run_eval_*.py` at repo root. Do not move to `scripts/` or `evals/`.**

**Rationale:**
- All nine existing eval scripts live at root and are referenced by name in every CONCLUSIONS doc (e.g. `CONCLUSIONS_DISP_N_AM.md` references `run_eval_disp.py`, `CONCLUSIONS_DSWX.md` references `run_eval_dswx.py`). Moving them breaks ~30+ documentation references and all session notes.
- Eval scripts are **entry points, not library code**. They are analogous to `examples/` or `bin/` scripts in other projects. Keeping them at root keeps them discoverable (`ls run_eval*.py`).
- v1.1 adds roughly 5 new eval scripts (`run_eval_rtc_eu.py`, `run_eval_cslc_selfconsistency.py`, `run_eval_cslc_selfconsistency_mojave.py`, `run_eval_cslc_eu.py`, `run_eval_dist_eu_effis.py`, `run_eval_dswx_nam.py`). Going from 9 → 15 eval scripts at root is still manageable. The threshold to consider moving them is ~25+ scripts or a clear grouping pattern (e.g. `evals/rtc/eu.py`, `evals/cslc/nam_mojave.py`); v1.1 does not cross it.
- The Makefile (Phase 0.7) gives an abstraction layer on top of script locations. If moving becomes warranted in v2, the Makefile target names stay stable; only the internal command changes.

**Makefile invocation pattern:**
```makefile
# Makefile at repo root
eval-rtc-nam:  ; python run_eval.py
eval-rtc-eu:   ; python run_eval_rtc_eu.py
eval-cslc-nam: ; python run_eval_cslc.py
eval-cslc-nam-mojave: ; python run_eval_cslc_selfconsistency_mojave.py
eval-cslc-eu:  ; python run_eval_cslc_eu.py
eval-disp-nam: ; python run_eval_disp.py
eval-disp-eu:  ; python run_eval_disp_egms.py
eval-dist-nam: ; python run_eval_dist.py
eval-dist-eu:  ; python run_eval_dist_eu.py
eval-dist-eu-effis: ; python run_eval_dist_eu_effis.py
eval-dswx-nam: ; python run_eval_dswx_nam.py
eval-dswx-eu:  ; python run_eval_dswx.py

eval-nam: eval-rtc-nam eval-cslc-nam eval-cslc-nam-mojave eval-disp-nam eval-dist-nam eval-dswx-nam
eval-eu:  eval-rtc-eu eval-cslc-eu eval-disp-eu eval-dist-eu eval-dist-eu-effis eval-dswx-eu
eval-all: eval-nam eval-eu results-matrix

results-matrix:
	python -m subsideo.validation.matrix_writer --out results/matrix.md
```

**Why direct script invocation over `python -m subsideo.evals.rtc_eu`:**
- Matches how every existing script is invoked today.
- Eval scripts import from `subsideo.*` but are not part of the installed package — they need a `.env` in the cwd, they write to cwd-relative caches. Running as a module changes cwd semantics and breaks the cache-dir-as-sibling convention.
- If in v2 eval scripts become part of the installed package, the Makefile target rewrites are one-line each.

### 6. `results/` and `results/matrix.md` (Phase 6.1)

**Path:** `results/` at repo root, `results/matrix.md` committed as the canonical status artifact.

**Rationale:**
- BOOTSTRAP §6.1 explicitly names `results/matrix.md` — no location ambiguity.
- Sibling to `eval-*/` cache dirs is wrong — cache dirs are gitignored; `results/` is git-tracked.
- Inside an eval cache is wrong — the matrix aggregates across all evals, not one.

**Matrix writer implementation:** `src/subsideo/validation/matrix_writer.py` (new module, peer to `report.py`).

**How the matrix writer discovers cells — recommendation: explicit manifest file, not glob over CONCLUSIONS.**

```yaml
# results/matrix_manifest.yml — committed, hand-edited
cells:
  - product: RTC
    region: "N.Am."
    eval_script: run_eval.py
    cache_dir: eval-rtc
    conclusions_doc: CONCLUSIONS_RTC_N_AM.md
    metrics_file: eval-rtc/metrics.json
  - product: RTC
    region: "EU"
    eval_script: run_eval_rtc_eu.py
    cache_dir: eval-rtc-eu
    conclusions_doc: CONCLUSIONS_RTC_EU.md
    metrics_file: eval-rtc-eu/metrics.json
  # ... 10 cells total for v1.1 (5 products × 2 regions)
```

**Why manifest over glob:**
- Glob over `CONCLUSIONS_*.md` requires parsing free-text markdown to extract numbers. Fragile: any CONCLUSIONS doc wording change breaks matrix generation.
- Manifest + `metrics.json` (each eval script writes one) gives structured input. Machine-readable, schema-validatable.
- Manifest explicitly documents which cells are expected — `make eval-all` can fail loudly if a cell's `metrics.json` is missing rather than silently omitting it.
- Hand-editable: new eval scripts append a block; no code change to the matrix writer.

**Required artifact per eval script:** each `run_eval_*.py` writes `<cache_dir>/metrics.json` with a fixed schema (product_quality_gate: dict, reference_agreement: dict, pass/fail status, run timestamp). This is a small addition — most eval scripts already construct equivalent dicts and print them; they just need to also `json.dump` to disk. Schema lives in `subsideo/validation/matrix_schema.py` as a Pydantic model.

### 7. Cache / intermediate handling

**Convention: one cache dir per eval script, sibling to the script at repo root, gitignored.**

**Rationale:**
- This is the existing pattern (`eval-rtc/`, `eval-disp/`, etc. verified on disk). v1.1 preserves it because every CONCLUSIONS doc and every eval script has this location hard-coded (`OUT = Path("./eval-rtc")` in `run_eval.py` is representative).
- Doubling eval count (9 → 15) makes a flat root with 15 `eval-*/` dirs slightly noisier, but the naming convention keeps them grouped. An alternative nested layout (`eval-cache/rtc/nam/`, `eval-cache/rtc/eu/`) saves ~6 entries at the cost of rewriting every CONCLUSIONS path reference. Not worth it at v1.1 scale.
- Gitignore entry already exists (one line per cache dir pattern: `eval-*/`).

**Resume-safe ensure — recommendation: generic helper in `harness`, called explicitly per-stage, not magic.**

```python
# subsideo/validation/harness.py
def ensure_resume_safe(
    output_paths: list[Path],
    checker_fn: Callable[[Path], bool] = lambda p: p.exists() and p.stat().st_size > 0,
) -> bool:
    """Return True if all output_paths pass checker_fn (stage can be skipped).
    Return False if any path is missing or fails the check (stage must re-run).
    """
```

Each eval script guards each stage explicitly:
```python
stage3_outputs = [cache / "slc" / f"{burst_id}.zip", cache / "dem" / "dem.tif"]
if not ensure_resume_safe(stage3_outputs):
    fetch_slc(...)
    fetch_dem(...)
```

**Why not a decorator/context manager:** decorators hide the output-path contract inside the function body; explicit guards make the "what does this stage produce" contract visible in the call site, which is where a reviewer checks cache correctness. BOOTSTRAP §0.5 specifies `ensure_resume_safe(output_paths, checker_fn)` as a plain function — this recommendation honours that signature.

**Per-product checker_fn:** some products need a stronger check than file existence (e.g. "is this a valid COG", "is this HDF5 parseable"). Provide a small library of checker_fns in `harness`:
```python
checkers = {
    "cog": lambda p: _cog.cog_validate(str(p))[0],
    "hdf5": _is_valid_hdf5,
    "nonempty_dir": lambda p: p.is_dir() and any(p.iterdir()),
}
```

### 8. Test architecture for v1.1

**Recommendation:** expand the existing `tests/` tree without adding new top-level directories. Use test marks + naming to split categories.

**Current structure (verified):**
```
tests/
├── conftest.py                # shared fixtures (po_valley_bbox, tmp_cache_dir)
├── unit/                      # 23 test modules, all mocked
│   ├── test_compare_{rtc,cslc,disp,dist,dswx}.py
│   ├── test_{rtc,cslc,disp,dist,dswx}_pipeline.py
│   ├── test_metrics.py, test_report.py, test_cli.py, ...
└── integration/               # __init__.py only, empty
```

**v1.1 additions — placement:**

| v1.1 test type | Location | Marker | Rationale |
|----------------|----------|--------|-----------|
| Phase 0.2 fresh-env import test (`from dolphin.unwrap import run` doesn't raise) | `tests/integration/test_fresh_env_imports.py` | `@pytest.mark.integration` | Not a unit test — requires real conda env. `integration/` is currently empty; this is the first resident. |
| Phase 0.3 non-mocked `_cog` smoke test | `tests/integration/test_cog_helper.py` | `@pytest.mark.integration` | Exercises real `rio_cogeo`. Integration marker skips it in default `pytest` runs, matches v1.0 convention for `@pytest.mark.integration`. |
| Phase 0.4 watchdog regression test | `tests/unit/test_mp_watchdog.py` | `@pytest.mark.slow` | Watchdog logic is pure Python with mockable time/subprocess. Unit-testable. `slow` marker lets CI exclude it from fast runs. |
| Phase 0.5 harness unit tests | `tests/unit/test_harness.py` | (none — default) | Helpers are mockable (HTTP calls, credential env vars). Fits existing unit pattern. |
| Phase 0.1 unit tests updated for numpy<2 / patches removed | existing `tests/unit/test_cslc_pipeline.py` | (none) | Patch-removal changes unit test content, not structure. |
| DSWx recalibration reproducibility | `scripts/recalibrate_dswe_thresholds.py` + `notebooks/dswx_recalibration.ipynb` | N/A (not a test) | BOOTSTRAP §5.3 specifies notebook, not test. Matrix writer covers the verification path. |

**Not recommended:** adding `tests/regression/` or `tests/smoke/` directories. v1.0's `unit/` + `integration/` split + pytest markers (`@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.validation` — already configured per `CLAUDE.md`) is adequate for v1.1 scope. Adding more top-level dirs fragments test discovery without clear benefit.

**Conftest additions:** add fixtures for
- `mock_earthdata_auth` — mocked earthaccess session.
- `mock_cdse_s3` — moto-backed S3 bucket with CDSE endpoint URL.
- `sample_metrics_json` — canonical metrics.json fixture for matrix writer tests.

All go in the existing `tests/conftest.py`.

---

## Updated Component Boundaries (v1.1 delta on v1.0)

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI / Config Layer                        │
│           (cli.py, config.py — v1.0, unchanged in v1.1)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Product Pipelines (unchanged)                   │
│        products/{rtc,cslc,disp,dist,dswx}.py — v1.0              │
│                                                                  │
│  Each products/*.py now calls at top of run_*():                 │
│    from subsideo._mp import configure_multiprocessing            │
│    configure_multiprocessing()  # NEW in v1.1 Phase 0.4          │
│                                                                  │
│  Each products/*.py imports from subsideo._cog                   │
│    (replacing inline rio_cogeo try/except) — Phase 0.3           │
│                                                                  │
│  products/dswx.py imports from products/dswx_thresholds.py       │
│    (NEW v1.1 Phase 5.3 — constants module)                       │
│                                                                  │
│  products/cslc.py — removes 4 monkey-patches (Phase 0.1)         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│             Validation Layer (extended in v1.1)                  │
│                                                                  │
│  compare_{rtc,cslc,disp,dist,dswx}.py — v1.0, unchanged          │
│    except compare_disp.py adds prepare_for_reference() [§3.1]    │
│                                                                  │
│  metrics.py, report.py — v1.0, unchanged                         │
│                                                                  │
│  NEW IN v1.1:                                                    │
│  + harness.py          -- validation plumbing (Phase 0.5/0.6)    │
│  + matrix_writer.py    -- results/matrix.md generator (Phase 6.1)│
│  + matrix_schema.py    -- Pydantic model for metrics.json        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                Cross-cutting Infrastructure                       │
│                                                                  │
│  Existing (v1.0):                                                │
│  - _metadata.py  (OPERA metadata injection, top-level private)   │
│                                                                  │
│  NEW IN v1.1 (same top-level-private pattern):                   │
│  + _cog.py       (rio_cogeo version-aware wrapper, Phase 0.3)    │
│  + _mp.py        (multiprocessing fork + watchdog, Phase 0.4)    │
│                                                                  │
│  utils/ (unchanged):                                             │
│  - logging.py, projections.py                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         Eval Scripts (repo root — 9 existing + ~6 new)           │
│                                                                  │
│  All eval scripts in v1.1:                                       │
│    from subsideo.validation.harness import (                     │
│        select_opera_frame_by_utc_hour,                           │
│        download_reference_with_retry,                            │
│        ensure_resume_safe,                                       │
│        credential_preflight,                                     │
│        bounds_for_burst,                                         │
│    )                                                             │
│                                                                  │
│  Each writes <cache_dir>/metrics.json on completion.             │
│                                                                  │
│  New in v1.1:                                                    │
│  + run_eval_rtc_eu.py                                            │
│  + run_eval_cslc_selfconsistency.py                              │
│  + run_eval_cslc_selfconsistency_mojave.py                       │
│  + run_eval_cslc_eu.py                                           │
│  + run_eval_dist_eu_effis.py                                     │
│  + run_eval_dswx_nam.py                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│          results/matrix.md (NEW v1.1 — git-tracked)              │
│          results/matrix_manifest.yml (NEW v1.1 — git-tracked)    │
│          Makefile (NEW v1.1, repo root — Phase 0.7)              │
└─────────────────────────────────────────────────────────────────┘

eval-*/ cache dirs at repo root — gitignored, one per eval script
scripts/recalibrate_dswe_thresholds.py — NEW v1.1 Phase 5.3
notebooks/dswx_recalibration.ipynb — NEW v1.1 Phase 5.3
docs/validation_methodology.md — NEW v1.1 Phase 6.2
```

---

## Failure-Mode Boundaries (Import-Cycle Risk Analysis)

### Safe direction (one-way arrows; enforce in code review):

```
cli.py ─→ config.py
cli.py ─→ products/*
cli.py ─→ validation/*

products/*.py ─→ _cog, _mp, _metadata
products/*.py ─→ utils/*
products/*.py ─→ data/*, burst/*
products/*.py ─→ products/types

validation/compare_*.py ─→ metrics.py
validation/compare_*.py ─→ products/types (for *ValidationResult types)
validation/harness.py   ─→ data/*, burst/*, utils/*
validation/matrix_writer.py ─→ matrix_schema.py, validation/harness

eval scripts (repo root) ─→ validation/harness, products/*, data/*

tests/unit/*        ─→ any subsideo.* (mocked I/O)
tests/integration/* ─→ any subsideo.* (real I/O, marked)
```

### Forbidden directions (create cycles / inversion):

| Forbidden import | Risk | Reason |
|------------------|------|--------|
| `products/*` → `validation/*` | **Cycle** | Validation imports `products/types`; products importing validation creates a loop. Also mixes processing with validation (Anti-Pattern 4 from v1.0). |
| `_cog.py` or `_mp.py` → any `subsideo.*` | Loop risk + layering violation | These are leaf modules. Importing upward from them creates a cycle when `products/*` imports them. |
| `utils/*` → `products/*` or `validation/*` | Layering inversion | Utils must be a leaf layer. |
| `validation/harness.py` → `products/*` | **Cycle** | Products will not import harness directly, but eval scripts import both — keeping harness product-free keeps the graph clean. |
| `validation/matrix_writer.py` → `products/*` | Minor layering inversion | Matrix writer reads `metrics.json` files — no need to touch products. |
| `validation/compare_disp.py` → `validation/harness.py` | OK today, risk tomorrow | Currently not needed; if added, guard it. |

### Public-API stability contracts for v1.1 new modules:

| Module | Stability | Contract |
|--------|-----------|----------|
| `subsideo.validation.harness` | **Public-ish** | Functions listed in §1 above are stable across v1.1 patches. Breaking signature changes require a minor-version bump. Eval scripts depend on these — they need a stable API. |
| `subsideo._cog` | **Internal** | Leading underscore. Only `cog_validate`, `cog_translate`, `RIO_COGEO_VERSION` are the documented internal surface. Everything else is free to change. |
| `subsideo._mp` | **Internal** | Only `configure_multiprocessing`, `watchdog`. |
| `subsideo.validation.compare_disp.prepare_for_reference` | **Public** | Part of the validation API. Stable within v1.1. |
| `subsideo.validation.matrix_writer` | **Public** | Used by CI / Makefile. Stable command-line interface. |
| `subsideo.validation.matrix_schema` | **Public** | Pydantic model defining `metrics.json` — eval scripts serialise into it, matrix writer deserialises. Schema evolution requires the usual Pydantic v2 migration discipline. |
| `subsideo.products.dswx_thresholds` | **Public** | Region keys (`"nam"`, `"eu"`) and `DSWEThresholds` NamedTuple fields are stable. Adding regions is non-breaking. |

---

## Patterns to Follow (v1.1-specific)

### Pattern 1: Cross-cutting infrastructure as top-level private module

**What:** Any v1.1 code that (a) wraps a third-party library version drift OR (b) mutates interpreter-global state OR (c) is imported by every product pipeline goes into `src/subsideo/_foo.py` with a leading underscore.

**When:** `_cog`, `_mp`, future `_hdf5` wrapper if h5py 4.x ships incompatibly, etc.

**Precedent:** `_metadata.py` in v1.0.

**Trade-off:** A slight flattening of the package — more files at top level. But grouping by "cross-cutting private infra" at the top avoids creating a speculative `internal/` subpackage.

### Pattern 2: Validation plumbing as harness module, per-product adapters stay in compare_*

**What:** Cross-product validation plumbing (retry, credential checks, frame selection, cache guards, bounds derivation) → `validation/harness.py`. Per-product comparison logic (multilook adapter for DISP, config-drift check for DIST) stays in `validation/compare_<product>.py`.

**When:** Every v1.1 helper whose name is not product-specific → harness. Every helper whose name is product-specific → compare_*.

**Trade-off:** Some grey-area helpers (e.g. `bounds_for_burst` — used by all eval scripts) might feel product-specific in their first use site. Rule of thumb: if the implementation touches only burst IDs / AOIs / HTTP / generic FS, it's harness. If it touches a product's internal grid / metadata / spec, it's compare_*.

### Pattern 3: metrics.json as contract between eval scripts and matrix writer

**What:** Every eval script writes a `metrics.json` at a fixed schema to its cache dir on completion. Matrix writer reads them (and only them), never re-parses free text from CONCLUSIONS docs.

**When:** All eval scripts — old and new.

**Trade-off:** Requires adding a ~10-line `json.dump` block to existing eval scripts. Low cost, high reproducibility benefit.

### Pattern 4: Explicit resume guards over magic caching

**What:** Every eval-script stage guards its re-run with `if not ensure_resume_safe(...): ...`. No decorators, no transparent caching layer.

**When:** Every expensive stage in every eval script. Non-negotiable for downloads and processing steps.

**Trade-off:** Slightly more lines per stage. Payoff: reviewer can see the re-run contract without inspecting hidden framework state.

---

## Anti-Patterns (v1.1-specific)

### Anti-Pattern 1: Putting `_cog.py` or `_mp.py` in `utils/`

**Why bad:** `utils/` is domain-agnostic stateless helpers (pyproj wrapper, log setup). `_mp.configure_multiprocessing()` mutates process start method — that is not a utility, it is interpreter-level configuration. Placing it in `utils/` masks its global side effects.

**Instead:** top-level private modules (`_cog.py`, `_mp.py`), following the `_metadata.py` precedent.

### Anti-Pattern 2: `validation/adapters.py` for a single product's need

**Why bad:** Only DISP needs a native→reference adapter in v1.1. A dedicated adapters module is speculative generality that forces every other `compare_*.py` to justify NOT using the abstraction.

**Instead:** Keep `prepare_for_reference` in `compare_disp.py`. Promote to a shared module only when a second product requires it (earliest: DISP Unwrapper Selection follow-up).

### Anti-Pattern 3: Matrix writer globbing CONCLUSIONS docs

**Why bad:** Regex-extracting metric numbers from free-text markdown breaks on any narrative rewording. Creates invisible coupling between prose and machine-readable output.

**Instead:** `results/matrix_manifest.yml` names the cells; each eval writes `metrics.json`; matrix writer consumes structured input.

### Anti-Pattern 4: Moving eval scripts to `evals/` subpackage now

**Why bad:** Breaks ~30+ CONCLUSIONS doc references and all session notes. Solves a problem (clutter) that doesn't meaningfully exist at v1.1 scale (15 scripts).

**Instead:** Keep at root, let the Makefile target names abstract location. Revisit in v2 if the count crosses ~25+ scripts.

### Anti-Pattern 5: Reading DSWx thresholds from YAML at runtime

**Why bad:** Adds file I/O to an algorithm hot path. Loses type safety. Harder to track provenance (the YAML file's git history is just `"EU thresholds updated"` vs a constants module's in-line docstring tying each value to a specific grid-search run).

**Instead:** `products/dswx_thresholds.py` as a typed Python module with provenance docstrings. pydantic-settings chooses which region's set to activate.

---

## Build Order (Phase 0 Sub-Dependencies)

BOOTSTRAP §Dependencies says "Phase 0 first, then 1–5 parallelisable." That is correct for the outer phase graph, but **Phase 0 itself has internal ordering constraints that BOOTSTRAP does not make explicit:**

```
Phase 0 internal order (serial developer):

0.1 (numpy<2 pin, remove patches)
  │  independent — only touches conda-env.yml and products/cslc.py
  ↓
0.3 (_cog.py centralisation)
  │  touches products/{rtc,dswx,dist}.py + _metadata.py
  │  low-risk, pure refactor, no new feature
  ↓
0.4 (_mp.py + watchdog)
  │  touches products/*.py entry points
  │  depends on _cog being settled (same files)
  │  ALSO: watchdog is a wall-time guard used by harness long-running ops,
  │  so _mp should land BEFORE harness uses it
  ↓
0.5 (harness.py)
  │  CAN import from _mp.watchdog (for download retry wall-time)
  │  DOES NOT import from 0.6 bounds helper yet — but...
  ↓
0.6 (bounds_for_burst)  ← LIVES IN harness.py per recommendation §1
  │  this is a new function on the harness module, not a new file
  │  ordering: after 0.5 opens harness.py, 0.6 adds one function
  ↓
0.7 (Makefile + results/matrix_manifest.yml)
  │  depends on eval scripts being harness-updated (0.5+0.6 complete)
  │  depends on metrics.json schema being agreed (harness + matrix_schema)
  ↓
0.2 (tophu first-class dep + fresh-env import test)
  │  independent of others; can run in parallel with any of 0.1–0.7
  │  Moved LAST here because it's the test that proves conda-env.yml
  │  is correct AFTER 0.1 has added numpy<2 pin and 0.7 has added
  │  Makefile targets that fresh-env would run
```

**Key clarification vs BOOTSTRAP dependency graph:** BOOTSTRAP §Dependencies shows Phase 1 needing "0.5 harness, 0.6 bounds" as separate items. Under the recommendation that `bounds_for_burst` lives inside `validation/harness.py`, 0.6 is not a separate module — it's a follow-up commit to the harness module. This collapses the 0.5/0.6 ordering into a single "harness complete" gate.

**Recommended Phase 0 single-developer serial order:**

1. **0.1** (numpy pin + patch removal) — smallest surface, derisks CSLC unit tests.
2. **0.3** (_cog) — pure refactor; no behavioural change; validates the "top-level private module" pattern before we reuse it for _mp.
3. **0.4** (_mp + watchdog) — reuses the same pattern; used by harness downloads (via watchdog context manager).
4. **0.5 + 0.6** (harness + bounds) — as one integrated push. harness.py opens with all four §0.5 helpers plus bounds_for_burst.
5. **0.2** (tophu pin + fresh-env import test) — now runs against the updated conda-env.yml with numpy<2 AND any harness deps.
6. **0.7** (Makefile + manifest + matrix writer scaffolding) — last, because it depends on all eval scripts being harness-migrated.

**Eval-script migration to harness (interleaved with 0.5):** do one eval script end-to-end first (recommend `run_eval.py` — smallest, well-understood) as the proof-out. Land harness + first migration together. Then batch-migrate the other eight eval scripts in a single commit.

**Parallelisation note for two developers:** 0.2 + 0.3 run parallel (disjoint files). 0.4 + 0.5/0.6 are serially dependent if harness uses `_mp.watchdog`. 0.7 is the join point.

---

## Scalability Considerations (v1.1 horizon only)

| Concern | v1.1 scale (5 products × 2 regions = 10 cells, ~15 eval scripts) | Threshold for architecture change |
|---------|------------------------------------------------------------------|-----------------------------------|
| Eval script count at root | 15 scripts — manageable | Move to `evals/` at 25+ scripts |
| Cache dir count at root | 15 cache dirs — manageable | Nest under `eval-cache/` at 25+ dirs |
| harness.py LOC | ~300–400 LOC — fine as single file | Split to `harness/` package at ~600+ LOC |
| metrics.json schema additions | ~10 cells × 6–10 fields — trivial | Version the schema explicitly when a field changes semantics |
| CONCLUSIONS docs | ~10–12 docs at repo root | Move to `docs/conclusions/` at 20+ docs (v2 milestone concern) |
| Matrix writer perf | 10 metrics.json reads per `make eval-all` — sub-second | N/A for v1.1 |

None of v1.1's scale crosses the architecture-change thresholds. Recommendations are stable for v1.2 and likely v1.3.

---

## Sources

- `BOOTSTRAP_V1.1.md` (read in full, repo root) — HIGH confidence, authoritative v1.1 scope document.
- `.planning/PROJECT.md` — HIGH confidence, current project state after v1.0 ship.
- `.planning/milestones/v1.0-research/ARCHITECTURE.md` — MEDIUM-HIGH confidence, v1.0 design intent; deltas against shipped v1.0 structure (below) noted for continuity.
- Direct inspection of `src/subsideo/` tree, `src/subsideo/validation/`, `src/subsideo/utils/`, `tests/`, and repo root — HIGH confidence (filesystem state as of 2026-04-20).
- `src/subsideo/_metadata.py` (read, 90 lines) — HIGH confidence precedent for top-level private module pattern.
- Context7 / external library docs not required for this research — all placement decisions derive from existing subsideo conventions, not external library recommendations.

**Deltas between v1.0 ARCHITECTURE.md (planned) and v1.0 shipped layout (verified):**
- Planned `access/` subpackage → shipped as `data/` (`data/cdse.py`, `data/asf.py`, etc.).
- Planned `bursts/` → shipped as `burst/` (singular).
- Planned `pipelines/` → shipped as `products/` (one module per product type, combining what the plan split into `pipelines/` + `wrappers/` + spec concerns).
- Planned `config/` subpackage → shipped as single top-level `config.py`.
- Planned `cli/` subpackage → shipped as single `cli.py`.
- Planned `products/` (spec module) → collapsed into `products/*.py` + top-level `_metadata.py`.

These deltas are informative for v1.1: the shipped codebase is **flatter** than the v1.0 plan anticipated. v1.1 should respect that flatness rather than re-introduce nested subpackages. The harness recommendation (single file, not subpackage) follows this principle.

---

*Architecture research for v1.1 N.Am./EU Validation Parity & Scientific PASS milestone*
*Researched: 2026-04-20*
