# Phase 1: Environment Hygiene, Framework Consolidation & Guardrail Scaffolding — Pattern Map

**Mapped:** 2026-04-21
**Files analyzed:** 40 new or modified files
**Analogs found:** 36/40 (4 files — repo-root infra — have no in-codebase analog and consume RESEARCH.md Examples 8–11 as their templates)

---

## 1. New File → Analog Table

| # | New File (to create) | Role | Data Flow | Closest Analog | Match Quality | Why this analog |
|---|-------|------|-----------|----------------|---------------|-----------------|
| 1 | `src/subsideo/_cog.py` | new private utility module (version-drift wrapper) | reads-only (validates/translates COGs in place) | `src/subsideo/_metadata.py` (99 LOC) | EXACT — same top-level `_<name>.py` pattern | Matching precedent: leading-underscore, loguru logger, `from __future__ import annotations`, lazy imports for rio_cogeo — line 71-73 already shows the target style |
| 2 | `src/subsideo/_mp.py` | new private utility module (interpreter-state config) | reads-only (mutates process env + start method) | `src/subsideo/_metadata.py` (99 LOC) | EXACT — same top-level `_<name>.py` pattern | Same leading-underscore precedent; idempotent function with global `_CONFIGURED` flag matches `_metadata.py` module-level constants |
| 3 | `src/subsideo/validation/harness.py` | new public utility module (5 shared helpers) | request-response (wraps HTTP, burst DB lookups) | `src/subsideo/validation/metrics.py` (124 LOC) | ROLE-MATCH — peer module in validation/ | Same validation-layer placement, pure-function style, `from __future__ import annotations`; NOT a leaf (imports from subsideo.data/burst/utils per ARCHITECTURE §Failure-Mode Boundaries) |
| 4 | `src/subsideo/validation/supervisor.py` | new supervisor module (subprocess watchdog) | subprocess supervisor + CLI entry | NO ANALOG (closest: `src/subsideo/cli.py`) | PARTIAL — only `__main__` + argparse shape is shared | Uses RESEARCH.md Example 7 as primary template; borrow `if __name__ == "__main__"` + argparse pattern from cli.py |
| 5 | `src/subsideo/validation/criteria.py` | new data-only constants module (frozen registry) | reads-only (data-only leaf) | `src/subsideo/products/types.py` (163 LOC) | EXACT — same `@dataclass` container pattern | Applies `@dataclass(frozen=True)` (Criterion) + module-level flat dict `CRITERIA` + 13 typed accessor functions; matches products/types.py docstring convention |
| 6 | `src/subsideo/validation/results.py` | new data-only leaf module (generic result types) | reads-only (data-only leaf) | `src/subsideo/products/types.py` (163 LOC) | EXACT — same `@dataclass` pattern | Two `@dataclass` containers + one pure `evaluate()` function; imports only from `subsideo.validation.criteria` (leaf-only, per D-07) |
| 7 | `src/subsideo/validation/stable_terrain.py` | new public utility module (mask construction) | reads-only (loads DEM/WorldCover/OSM) | `src/subsideo/validation/metrics.py` (124 LOC) | ROLE-MATCH — pure-function validation helper | Same validation/ placement; shared module consumed by Phase 3/4 compare_cslc/compare_disp (per ARCHITECTURE §Architectural Responsibility Map) |
| 8 | `src/subsideo/validation/selfconsistency.py` | new public utility module (coherence stats) | reads-only (reads ifgrams, computes stats) | `src/subsideo/validation/metrics.py` (124 LOC) | ROLE-MATCH — pure-function numerical ops | Same pattern: numpy-only input, return scalars/dicts, no I/O; consumes `stable_terrain.py` output |
| 9 | `src/subsideo/validation/matrix_schema.py` | new public schema module (Pydantic v2 models) | config loader (consumed by writers + reader) | `src/subsideo/config.py` (82 LOC) | EXACT — same Pydantic v2 + `SettingsConfigDict` style | Both define BaseModel/BaseSettings with typed fields; matrix_schema.py uses BaseModel (not BaseSettings) since the sidecars aren't settings — but same `from __future__ import annotations` + `Field(...)` style |
| 10 | `src/subsideo/validation/matrix_writer.py` | new aggregation module (reads sidecars) | test consumer + file writer | `src/subsideo/validation/report.py` (existing, ~30 lines inspected) | ROLE-MATCH — also reads per-product results and writes markdown | report.py already has `_CRITERIA_MAP` hand-rolled dict that matrix_writer.py will replace by consuming `CRITERIA` from `validation/criteria.py` |
| 11 | `Dockerfile` | new infra file (multi-stage build) | CI lockfile | NO ANALOG in repo | — | Uses RESEARCH.md Example 9 as sole template (mambaorg/micromamba base, multi-stage) |
| 12 | `Apptainer.def` | new infra file (Singularity recipe) | CI lockfile | NO ANALOG in repo | — | Uses RESEARCH.md Example 10 as sole template (derives from `docker-daemon://subsideo:dev`) |
| 13 | `conda-env.yml` | new infra file (env manifest) | config loader | NO ANALOG in repo | — | Uses RESEARCH.md Example 8 as sole template; pyproject.toml's `[project.optional-dependencies]` layout is the precedent for grouping comments |
| 14 | `env.lockfile.linux-64.txt` | new infra file (explicit lockfile) | CI lockfile | NO ANALOG in repo | — | Generated via `micromamba list --explicit --md5`; no code pattern |
| 15 | `env.lockfile.osx-arm64.txt` | new infra file (explicit lockfile) | CI lockfile | NO ANALOG in repo | — | Same as (14) |
| 16 | `Makefile` | new infra file (orchestration) | subprocess supervisor (calls supervisor.py) | NO ANALOG in repo | — | Uses RESEARCH.md Example 11 as sole template; `~20 lines` target |
| 17 | `results/matrix_manifest.yml` | new data file (10-cell registry) | config loader | `pyproject.toml` optional-dependencies grouping (commented sections) | PARTIAL — only section-labelling convention | Hand-edited YAML; entries read by `matrix_writer.py` |
| 18 | `tests/product_quality/__init__.py` | new test infra (empty marker) | test consumer | `tests/unit/__init__.py` (existing) | EXACT | Empty `__init__.py` — established convention |
| 19 | `tests/product_quality/test_*.py` (from `test_compare_cslc.py`, `test_compare_disp.py`, `test_compare_dist.py`, `test_compare_rtc.py`) | new test modules (migrated) | test consumer | `tests/unit/test_compare_dist.py` (134 LOC) | EXACT — test structure preserved | Move 4 of 5 existing `tests/unit/test_compare_*.py` files here (those with threshold asserts); update imports to use `ProductQualityResult` / `ReferenceAgreementResult` nested access |
| 20 | `tests/reference_agreement/__init__.py` | new test infra (empty marker) | test consumer | `tests/unit/__init__.py` | EXACT | Same as (18) |
| 21 | `tests/reference_agreement/conftest.py` | new test linter + fixtures | test consumer | `tests/conftest.py` (28 LOC) | EXACT + extended | Root conftest provides `po_valley_bbox`, `tmp_cache_dir`; reference_agreement conftest adds an ast-parse collection hook (per Pitfall 6) rejecting threshold assertions |
| 22 | `tests/reference_agreement/test_*.py` | new test modules (plumbing subset) | test consumer | `tests/unit/test_compare_dswx.py` (plumbing-only — see §1.2) | EXACT | The plumbing parts of the 5 original `test_compare_*.py` files migrate here; no threshold assertions |

### 1.1 Test-split migration map

The 5 existing `tests/unit/test_compare_*.py` files split as follows (per Claude's Discretion + Pitfall 6):

| Original file | Threshold asserts? | Target directory | Notes |
|---------------|---------------------|-----------------|-------|
| `tests/unit/test_compare_dswx.py` | NO — plumbing only (confirmed by `grep`; no `pass_criteria` keys, no numeric literal compared to field) | STAYS in `tests/unit/` | The only unit-level compare test |
| `tests/unit/test_compare_rtc.py` | YES — lines 49-50 assert `pass_criteria["rmse_lt_0.5dB"] is True` | → `tests/product_quality/test_compare_rtc.py` (value asserts) + `tests/reference_agreement/test_compare_rtc.py` (plumbing-only — `np.isfinite`, len checks) | Split file (each keeps its original test names) |
| `tests/unit/test_compare_cslc.py` | YES — lines 46-47, 64-65, 83-84 assert `pass_criteria["amplitude_correlation_gt_0.6"]` | → `tests/product_quality/test_compare_cslc.py` | Content dominated by threshold asserts; migrate whole |
| `tests/unit/test_compare_disp.py` | YES — lines 78-79 assert `correlation > 0.99`, `abs(bias_mm_yr) < 0.01`; lines 126-129 assert pass_criteria | → `tests/product_quality/test_compare_disp.py` + `tests/reference_agreement/test_compare_disp.py` for plumbing asserts | Split file |
| `tests/unit/test_compare_dist.py` | YES — lines 70-72 assert `all(result.pass_criteria.values())`; line 94 asserts `pass_criteria["f1_gt_0.80"] is False` | → `tests/product_quality/test_compare_dist.py` + `tests/reference_agreement/test_compare_dist.py` for the shifted-grid plumbing test (128-133: `np.isfinite` only) | Split file |

---

## 2. Modified File → Clean Pattern Table

| # | Modified File | Change | Pattern to Follow | Where to Look |
|---|---------------|--------|-------------------|---------------|
| M1 | `src/subsideo/products/cslc.py` | Delete 4 monkey-patch sites (ENV-02) | Follow the clean unpatched pattern in `src/subsideo/products/rtc.py:217-219` (lazy import inside try/except; no `_patch_*` calls between import and call) | `products/rtc.py:217` — `from rtc.rtc_s1 import run_parallel` followed directly by use, no shims |
| M2 | `src/subsideo/products/{rtc,cslc,disp,dist,dswx}.py` | Insert `_mp.configure_multiprocessing()` as first line of each `run_*()` entry point (ENV-04, D-14) | Insert immediately after the docstring, before any `cfg = ...` construction (see `products/rtc.py:168-213` for existing run_rtc structure: docstring lines 176-203, then config build at 205) | Research Example 2 (§D) |
| M3 | `src/subsideo/products/{rtc,dist,dswx}.py` + `src/subsideo/_metadata.py` | Replace `from rio_cogeo import ...` / `from rio_cogeo.cogeo import ...` (14 sites) with `from subsideo._cog import cog_validate, cog_translate, ensure_valid_cog` (ENV-03) | PRESERVE the lazy-import convention — `_cog` can be imported at module top (it's pure-Python leaf) but its internals defer `rio_cogeo` import into function bodies | `src/subsideo/products/rtc.py:102-103` (inside `ensure_cog` body) and `src/subsideo/products/rtc.py:138-139` (inside `validate_rtc_product` body) |
| M4 | `src/subsideo/validation/compare_{rtc,cslc,disp,dist,dswx}.py` | Change return from flat ValidationResult to nested composite (D-06, D-09) | See Research Example 6 (§M) — existing return in `compare_rtc.py:63-72` becomes a nested construction passing both `ProductQualityResult` and `ReferenceAgreementResult` kwargs | `src/subsideo/validation/compare_rtc.py:63-72` (before) → Research Example 6 (after) |
| M5 | `src/subsideo/products/types.py` | Replace 5 flat ValidationResult dataclasses with composite-shape (D-07) | PRESERVE docstring + `@dataclass` style; only the field list changes. Add `from subsideo.validation.results import ProductQualityResult, ReferenceAgreementResult` at top | `src/subsideo/products/types.py:62-69` (before — `RTCValidationResult` with 4 float fields + pass_criteria dict) → Research Example 6 (after) |
| M6 | All 7 existing `run_eval*.py` scripts | Replace hand-coded credentials checks, bounds, retry loops with harness imports (ENV-06, ENV-07, ENV-08) | Pilot is `run_eval.py:69` (`bounds=[-119.7, 33.2, -118.3, 34.0]`) → `harness.bounds_for_burst(BURST_ID, buffer_deg=0.2)`. Credential pre-flight in `run_eval_dist.py:123-125` → `harness.credential_preflight(["EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"])`. Insert `EXPECTED_WALL_S = <seconds>` module-level constant per D-11 | `run_eval.py:69` (hand-coded bounds), `run_eval_disp.py:51` + `run_eval_disp_egms.py:61` (DEM_BBOX literals), `run_eval_dist.py:122-135` (auth), `run_eval_disp_egms.py:78-93` (CDSE auth) |
| M7 | `src/subsideo/validation/__init__.py` | Populate empty file with harness + results re-exports (ENV-06 discoverability) | File is currently empty (1 line). Add `from subsideo.validation.harness import bounds_for_burst, credential_preflight, ...; from subsideo.validation.results import ProductQualityResult, ReferenceAgreementResult, evaluate` | Keep imports alphabetical, `from __future__ import annotations` only if the module uses type annotations itself |
| M8 | `tests/unit/test_cslc_pipeline.py` | Delete 3 `_patch_*` mocker lines (ENV-02) | Lines 127-129 mock `_patch_compass_burst_db_none_guard`, `_patch_s1reader_numpy2_compat`, `_patch_burst_az_carrier_poly` — all 3 must be removed after the corresponding `products/cslc.py` edits | `tests/unit/test_cslc_pipeline.py:127-129` |
| M9 | `pyproject.toml` | NO CHANGE in Phase 1 (D-15, Open Question 1). py-spy lives only in conda-env.yml | N/A | Don't touch lines 92-164 (optional-dependencies) |
| M10 | `src/subsideo/validation/report.py` | NOT MODIFIED in Phase 1 — existing `_CRITERIA_MAP` is legacy; new `matrix_writer.py` replaces its role. Any overlap is Phase 7 cleanup | N/A | — |

---

## 3. Per-Analog Code Excerpts

### 3.1 Analog: `src/subsideo/_metadata.py` — top-level private module precedent

**Files that copy this pattern:** `_cog.py`, `_mp.py`

**Header + imports (lines 1-13):**
```python
"""OPERA-compliant identification metadata injection for all product types.

Injects provenance, software version, and run parameters into both
GeoTIFF (via rasterio tags) and HDF5 (via /identification group attrs).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger
```

**Lazy import of conda-forge-only deps inside function body (lines 63-74):**
```python
def _inject_geotiff(path: Path, metadata: dict[str, str]) -> None:
    """Write metadata as GeoTIFF tags.
    ...
    """
    import rasterio
    from rio_cogeo.cogeo import cog_translate
    from rio_cogeo.profiles import cog_profiles

    with rasterio.open(path, "r+", IGNORE_COG_LAYOUT_BREAK="YES") as ds:
        ds.update_tags(**metadata)
```

**Key conventions extracted:**
- `"""<one-line summary>.`\n\n`<paragraph>"""` module docstring
- `from __future__ import annotations` as the first non-docstring line
- stdlib imports block, blank line, `from loguru import logger`
- third-party (`rasterio`, `rio_cogeo`) imports deferred inside function bodies
- `_leading_underscore` prefix on module-private helpers (`_inject_geotiff`, `_inject_hdf5`)
- `logger.debug("... {}", path)` (loguru's brace-style, not `%s`)

---

### 3.2 Analog: `src/subsideo/products/types.py` — plain @dataclass result containers

**Files that copy this pattern:** `validation/results.py`, `validation/criteria.py`

**Header + imports (lines 1-10):**
```python
"""Pipeline configuration, result, and validation result types.

Dataclasses (not Pydantic) -- these are plain result containers consumed
by pipeline orchestrators and validation comparison modules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
```

**Flat @dataclass with docstring + field defaults (lines 62-69, the type being migrated):**
```python
@dataclass
class RTCValidationResult:
    """Validation metrics comparing RTC output against reference."""

    rmse_db: float
    correlation: float
    bias_db: float
    ssim_value: float
    pass_criteria: dict[str, bool] = field(default_factory=dict)
```

**Longer @dataclass with structured docstring for DISTValidationResult (lines 115-131):**
```python
@dataclass
class DISTValidationResult:
    """Validation metrics comparing DIST-S1 output against OPERA DIST-S1 reference.

    All fields are binary-classification metrics over the disturbed/
    not-disturbed label, computed on the intersection of valid pixels
    between the product and the reference after reprojection to a
    shared grid. ``pass_criteria`` is a dict of named threshold checks
    that the caller's harness can iterate to produce a pass/fail verdict.
    """

    f1: float
    precision: float
    recall: float
    overall_accuracy: float
    n_valid_pixels: int
    pass_criteria: dict[str, bool] = field(default_factory=dict)
```

**Key conventions extracted:**
- `@dataclass` (plain, not `@dataclass(frozen=True)` — except `Criterion` where frozen is a D-01 requirement)
- `: float = field(default_factory=dict)` idiom for dict defaults
- `from dataclasses import dataclass, field` at top
- Class docstring immediately after decorator
- No `__post_init__` anywhere — pure data containers
- Field names use snake_case, units in suffix (`_db`, `_mm_yr`)

---

### 3.3 Analog: `src/subsideo/config.py` — Pydantic v2 BaseSettings precedent

**Files that copy this pattern:** `validation/matrix_schema.py`

**Header + imports (lines 1-16):**
```python
"""Pydantic v2 layered settings: env vars > .env > YAML > defaults."""
from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
import yaml

T = TypeVar("T", bound=BaseModel)
```

**Class pattern with Field + model_config (lines 19-47):**
```python
class Settings(BaseSettings):
    """Global subsideo configuration.

    Precedence: init kwargs > env vars > .env file > YAML file > defaults.
    """

    cdse_client_id: str = Field(default="", description="CDSE OAuth2 client ID")
    ...
    work_dir: Path = Field(
        default_factory=lambda: Path.cwd() / "work",
        description="Working directory for intermediate files",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        yaml_file=None,
        extra="ignore",
    )
```

**Key conventions extracted:**
- For `matrix_schema.py`: use `BaseModel` (not `BaseSettings` — sidecars are not settings)
- `Field(default=..., description=...)` always with a description
- `Path` for file-path fields, `str` for strings
- No `Optional[...]` — use `T | None` (PEP 604) because `from __future__ import annotations` is active
- Docstring on every model
- Layered-config pattern (`settings_customise_sources`) is NOT needed for matrix_schema.py; that's a Settings-only pattern

---

### 3.4 Analog: `src/subsideo/validation/metrics.py` — pure-function validation helper

**Files that copy this pattern:** `validation/harness.py`, `validation/stable_terrain.py`, `validation/selfconsistency.py`

**Header + imports (lines 1-9):**
```python
"""Pure-function validation metrics for comparing predicted vs reference arrays.

All functions accept numpy arrays and handle NaN/nodata masking internally.
No file I/O -- comparison modules handle loading and spatial alignment.
"""
from __future__ import annotations

import numpy as np
from scipy import stats
```

**Function docstring + NaN-handling pattern (lines 12-22):**
```python
def rmse(predicted: np.ndarray, reference: np.ndarray) -> float:
    """Root Mean Square Error between predicted and reference arrays.

    NaN values in either array are excluded from the computation.
    Returns 0.0 if no valid pairs exist.
    """
    mask = np.isfinite(predicted) & np.isfinite(reference)
    diff = predicted[mask] - reference[mask]
    if len(diff) == 0:
        return 0.0
    return float(np.sqrt(np.mean(diff**2)))
```

**Key conventions extracted:**
- Pure functions (no class), return primitive floats/ints/dicts
- NaN-mask is a first-class concern: always check `np.isfinite(...)` before computation
- `return float(...)` / `return int(...)` — never return raw numpy scalars
- "Returns 0.0 if ..." clause in docstring for edge cases
- Top-level `import numpy as np` is ALLOWED here because numpy is a core pyproject dep; but conda-forge-only deps (rio_cogeo, isce3, dolphin, rasterio) MUST be deferred into function bodies in `stable_terrain.py` / `selfconsistency.py`

---

### 3.5 Analog: `src/subsideo/validation/compare_rtc.py` — existing validation return-shape (BEFORE migration)

**Files that copy this pattern (after migration):** all 5 `compare_*.py` return statements

**Imports + return shape (lines 1-12, 63-72):**
```python
"""RTC-S1 product validation against OPERA N.Am. reference."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from loguru import logger
from rasterio.warp import Resampling, reproject

from subsideo.products.types import RTCValidationResult
from subsideo.validation.metrics import bias, rmse, spatial_correlation, ssim
```

```python
    return RTCValidationResult(
        rmse_db=rmse_val,
        correlation=corr_val,
        bias_db=bias_val,
        ssim_value=ssim_val,
        pass_criteria={
            "rmse_lt_0.5dB": rmse_val < 0.5,
            "correlation_gt_0.99": corr_val > 0.99,
        },
    )
```

**AFTER migration (Research Example 6):**
```python
from subsideo.validation.results import ProductQualityResult, ReferenceAgreementResult
from subsideo.products.types import RTCValidationResult

return RTCValidationResult(
    product_quality=ProductQualityResult(
        measurements={"ssim": ssim_val},
        criterion_ids=[],
    ),
    reference_agreement=ReferenceAgreementResult(
        measurements={
            "rmse_db": rmse_val,
            "correlation": corr_val,
            "bias_db": bias_val,
        },
        criterion_ids=["rtc.rmse_db_max", "rtc.correlation_min"],
    ),
)
```

**Other compare_*.py return sites (for migration scope):**
- `src/subsideo/validation/compare_cslc.py:128-137` (NaN-case return) + `174-183` (normal return)
- `src/subsideo/validation/compare_disp.py:177-184`
- `src/subsideo/validation/compare_dist.py:184-191` (NaN-case) + `217-224` (normal)
- `src/subsideo/validation/compare_dswx.py:277-280` (NaN-case) + `293-299` (normal)

**Key conventions extracted:**
- Both early-return (NaN/empty-mask) paths AND the normal path must be migrated
- `logger.info(...)` before the return is standard — keep it
- Import order: stdlib, blank line, third-party, blank line, local subsideo.* imports

---

### 3.6 Analog: `src/subsideo/products/rtc.py` — unpatched entry-point structure (for ENV-04 insertion point)

**Files that copy this pattern:** `products/{rtc,cslc,disp,dist,dswx}.py` top of `run_*()`

**`run_rtc` entry-point structure (lines 168-215):**
```python
def run_rtc(
    safe_paths: list[Path],
    orbit_path: Path,
    ...
) -> RTCResult:
    """Execute the full RTC-S1 pipeline.

    Steps:
    1. Build :class:`RTCConfig` from arguments
    ...
    Returns
    -------
    RTCResult
        Processing result with output paths and validation status.
    """
    cfg = RTCConfig(
        safe_file_paths=safe_paths,
        ...
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    runconfig_yaml = generate_rtc_runconfig(cfg, output_dir / "rtc_runconfig.yaml")

    try:
        from rtc.rtc_s1 import run_parallel
        from rtc.runconfig import RunConfig, load_parameters
```

**ENV-04 insertion point — IMMEDIATELY after the docstring, BEFORE `cfg = RTCConfig(...)`:**
```python
def run_rtc(...) -> RTCResult:
    """Execute the full RTC-S1 pipeline.
    ...
    """
    # ENV-04: configure multiprocessing BEFORE any subprocess or matplotlib import
    from subsideo._mp import configure_multiprocessing
    configure_multiprocessing()

    cfg = RTCConfig(...)
    ...
```

**Key conventions extracted:**
- Lazy import of `_mp.configure_multiprocessing` INSIDE the run function (NOT at module top — keeps pip-install-only users' imports clean)
- Insert after docstring and before config construction
- Idempotent: safe to call even if already configured (global `_CONFIGURED` flag)

---

### 3.7 Analog: `src/subsideo/products/cslc.py:382-407` — the 4 monkey-patch removal sites (ENV-02)

**Files impacted:** `products/cslc.py`

**Current monkey-patch block to DELETE (lines 384-407):**
```python
try:
    from compass.s1_cslc import run as compass_run

    # Workaround for compass bug: GeoRunConfig.load_from_yaml calls
    # os.path.isfile(burst_database_file) unconditionally, then raises
    # FileNotFoundError — before the None check at line 101 that would
    # use generate_geogrids() without a DB.  Monkey-patch load_from_yaml
    # to skip the burst DB file check when it is None.
    _patch_compass_burst_db_none_guard()                    # ← DELETE CALL + DEF (lines 156-223)

    # Workaround for s1reader numpy 2.x incompatibility: polyfit uses
    # ``%f`` formatting on a numpy array (res from lstsq), which numpy
    # 2.0+ rejects.  Patch the print to use .item().
    _patch_s1reader_numpy2_compat()                         # ← DELETE CALL + DEF (lines 226-293)

    # Workaround for numpy 2.x: np.string_ was removed, use np.bytes_
    import numpy as _np
    if not hasattr(_np, 'string_'):
        _np.string_ = _np.bytes_                            # ← DELETE inline shim (lines 399-402)

    # Workaround for numpy 2.x / isce3 pybind11 incompatibility:
    # burst.get_az_carrier_poly() returns a list-of-lists that pybind11
    # can no longer auto-convert to Poly2d.  Patch it to return Poly2d.
    _patch_burst_az_carrier_poly()                          # ← DELETE CALL + DEF (lines 296-318)

    compass_run(run_config_path=str(runconfig_yaml), grid_type="geo")
```

**Clean pattern after removal (what remains):**
```python
try:
    from compass.s1_cslc import run as compass_run

    compass_run(run_config_path=str(runconfig_yaml), grid_type="geo")
    logger.info("compass CSLC processing complete")
except ImportError:
    logger.error("compass not installed — install via conda-forge")
    return CSLCResult(
        output_paths=[],
        runconfig_path=runconfig_yaml,
        burst_ids=burst_ids or [],
        valid=False,
        validation_errors=["compass not installed (conda-forge required)"],
    )
```

**Module docstring update (lines 7-15):** Remove the "Compatibility notes (2026-04-11)" block referencing the 4 patches; replace with a single-line comment linking to the numpy<2 conda-env.yml sunset note.

**Also delete:** 3 `mocker.patch(...)` lines in `tests/unit/test_cslc_pipeline.py:127-129`.

---

### 3.8 Analog: `run_eval.py` — pilot harness-migration target (ENV-07 pilot)

**Current structure (lines 1-20 + 67-71 — the parts that change):**
```python
# run_eval.py — N.Am. RTC validation against OPERA
# Downloads S1 SLC from ASF (not CDSE — CDSE covers EU only)
import warnings; warnings.filterwarnings("ignore")

# Required on macOS: multiprocessing uses 'spawn', which re-imports this
# script in worker processes.  All top-level work must be inside this guard.
if __name__ == "__main__":
    import asf_search as asf
    import earthaccess
    from pathlib import Path
    from datetime import datetime
    from subsideo.data.dem import fetch_dem
    from subsideo.data.orbits import fetch_orbit
    from subsideo.products.rtc import run_rtc
    from dotenv import load_dotenv
    load_dotenv()

    OUT = Path("./eval-rtc")
    BURST_ID = "t144_308029_iw1"
    SENSING_DATE = datetime(2024, 6, 24, 14, 1, 16)
```

```python
    # ── 3. Download DEM and orbit ─────────────────────────────────────────────────
    print("Fetching DEM and orbit...")
    dem_path, _ = fetch_dem(
        bounds=[-119.7, 33.2, -118.3, 34.0],  # ← HAND-CODED LITERAL TO REPLACE
        output_epsg=32611,
        output_dir=OUT / "dem",
    )
```

**AFTER harness migration (target shape for all 7 scripts):**
```python
# run_eval.py — N.Am. RTC validation against OPERA
# Downloads S1 SLC from ASF (not CDSE — CDSE covers EU only)
import warnings; warnings.filterwarnings("ignore")

EXPECTED_WALL_S = 1800   # D-11: supervisor AST-parses this module-level literal

if __name__ == "__main__":
    from pathlib import Path
    from datetime import datetime
    from subsideo.data.dem import fetch_dem
    from subsideo.data.orbits import fetch_orbit
    from subsideo.products.rtc import run_rtc
    from subsideo.validation.harness import (
        bounds_for_burst,
        credential_preflight,
        download_reference_with_retry,
        select_opera_frame_by_utc_hour,
        ensure_resume_safe,
    )
    from dotenv import load_dotenv
    load_dotenv()

    OUT = Path("./eval-rtc")
    BURST_ID = "t144_308029_iw1"
    SENSING_DATE = datetime(2024, 6, 24, 14, 1, 16)

    credential_preflight(["EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"])
    ...

    # ── 3. Download DEM and orbit ─────────────────────────────────────────────────
    dem_path, _ = fetch_dem(
        bounds=bounds_for_burst(BURST_ID, buffer_deg=0.2),   # ← ENV-08 replacement
        output_epsg=32611,
        output_dir=OUT / "dem",
    )
```

**Credential pre-flight in `run_eval_dist.py:122-135` (another replacement site):**
```python
# BEFORE (lines 122-135):
for key in ("EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"):
    if not os.environ.get(key):
        raise SystemExit(f"{key} not set in environment or .env")
...
session = asf.ASFSession().auth_with_creds(
    username=os.environ["EARTHDATA_USERNAME"],
    password=os.environ["EARTHDATA_PASSWORD"],
)

# AFTER:
credential_preflight(["EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"])
...
session = asf.ASFSession().auth_with_creds(
    username=os.environ["EARTHDATA_USERNAME"],
    password=os.environ["EARTHDATA_PASSWORD"],
)  # auth_with_creds stays — only the pre-flight check is harnessed
```

**Key conventions extracted:**
- Preserve the `import warnings; warnings.filterwarnings("ignore")` line at top
- Preserve the `if __name__ == "__main__":` guard
- Insert `EXPECTED_WALL_S = <int>` as a module-level literal BEFORE the `if __name__ == "__main__"` block (AST parser needs to find it regardless of execution path)
- Keep `load_dotenv()` call site
- Per-script constants (BURST_ID, SENSING_DATE, EPSG, OUT) STAY in each script — they are scientific inputs, not plumbing
- Imports from `subsideo.validation.harness` go in a single grouped `from ... import (... , ...)` block

---

### 3.9 Analog: `tests/unit/test_compare_rtc.py` — test structure for product_quality split

**Files that copy this pattern:** `tests/product_quality/test_compare_rtc.py`, `tests/product_quality/test_compare_{cslc,disp,dist}.py`

**Header + fixture (lines 1-33):**
```python
"""Unit tests for RTC-S1 comparison module using synthetic arrays."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds

from subsideo.validation.compare_rtc import compare_rtc


def _make_rtc_geotiff(
    path: Path, data: np.ndarray, epsg: int = 32632, pixel_size: float = 30.0
) -> Path:
    """Write a minimal GeoTIFF with given 2-D float32 array."""
    rows, cols = data.shape
    transform = from_bounds(0, 0, pixel_size * cols, pixel_size * rows, cols, rows)
    with rasterio.open(
        path, "w", driver="GTiff",
        height=rows, width=cols, count=1, dtype="float32",
        crs=CRS.from_epsg(epsg), transform=transform,
    ) as dst:
        dst.write(data.astype(np.float32), 1)
    return path
```

**Test function with threshold asserts (lines 36-50):**
```python
def test_compare_rtc_identical(tmp_path: Path) -> None:
    """Identical products should yield zero RMSE, perfect correlation."""
    rng = np.random.default_rng(42)
    data = rng.uniform(0.01, 1.0, (100, 100))

    prod = _make_rtc_geotiff(tmp_path / "product.tif", data)
    ref = _make_rtc_geotiff(tmp_path / "reference.tif", data)

    result = compare_rtc(prod, ref)

    assert result.rmse_db == pytest.approx(0.0, abs=1e-6)
    assert result.correlation == pytest.approx(1.0, abs=1e-6)
    assert result.bias_db == pytest.approx(0.0, abs=1e-6)
    assert result.pass_criteria["rmse_lt_0.5dB"] is True    # ← product_quality assertion
    assert result.pass_criteria["correlation_gt_0.99"] is True
```

**AFTER D-09 migration (in `tests/product_quality/test_compare_rtc.py`):**
```python
from subsideo.validation.compare_rtc import compare_rtc
from subsideo.validation.results import evaluate

def test_compare_rtc_identical(tmp_path: Path) -> None:
    ...
    result = compare_rtc(prod, ref)
    # Access metrics via nested composite (D-06)
    assert result.reference_agreement.measurements["rmse_db"] == pytest.approx(0.0, abs=1e-6)
    assert result.reference_agreement.measurements["correlation"] == pytest.approx(1.0, abs=1e-6)
    # Pass/fail computed at read time (D-08)
    outcomes = evaluate(result.reference_agreement)
    assert outcomes["rtc.rmse_db_max"] is True
    assert outcomes["rtc.correlation_min"] is True
```

**Key conventions extracted:**
- `def test_*(tmp_path: Path) -> None` signature with `tmp_path` fixture (pytest built-in)
- `rng = np.random.default_rng(42)` for reproducibility
- Helper `_make_<type>_geotiff` at top of file, leading-underscore
- `pytest.approx(..., abs=1e-6)` for float comparisons
- For PLUMBING-only tests (`tests/reference_agreement/`): `assert np.isfinite(...)`, `assert result.n_valid_pixels > 0`, `assert result is not None` — NO numeric-literal comparisons

---

### 3.10 Analog: `tests/conftest.py` — shared fixtures

**Files that extend this pattern:** `tests/reference_agreement/conftest.py` (ADD linter + reuse)

**Full file (28 lines):**
```python
"""Shared pytest fixtures for subsideo tests."""
from __future__ import annotations

from pathlib import Path

import pytest

# Po Valley, Italy -- reference AOI used across tests
PO_VALLEY_BBOX = [9.5, 44.5, 12.5, 45.5]  # [west, south, east, north] WGS84
PO_VALLEY_WKT = "POLYGON((9.5 44.5, 12.5 44.5, 12.5 45.5, 9.5 45.5, 9.5 44.5))"


@pytest.fixture
def po_valley_bbox() -> list[float]:
    return PO_VALLEY_BBOX


@pytest.fixture
def po_valley_wkt() -> str:
    return PO_VALLEY_WKT


@pytest.fixture
def tmp_cache_dir(tmp_path: Path) -> Path:
    cache = tmp_path / ".subsideo"
    cache.mkdir()
    return cache
```

**New `tests/reference_agreement/conftest.py` skeleton (per Pitfall 6):**
```python
"""Fixtures for reference_agreement tests + linter: rejects threshold assertions.

Per GATE-04 / Pitfall 6, tests in this tree must NOT assert any
criteria.py threshold value. A CI-adjacent linter rejects:
  - numeric-literal comparands in assert statements
  - imports from subsideo.validation.criteria
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest


def pytest_collection_modifyitems(config, items):
    """Reject threshold-asserting tests at collection time."""
    for item in items:
        src = Path(item.fspath).read_text()
        tree = ast.parse(src)
        # ...  AST walk flagging assert statements with numeric literals
```

**Key conventions extracted:**
- Reuse root `conftest.py` fixtures (pytest auto-discovers parent conftest.py)
- Constants SHOUTCASE (`PO_VALLEY_BBOX`); fixtures lowercase
- Linter implemented as `pytest_collection_modifyitems` hook (per A5 — conftest hook is sufficient for v1.1 solo-dev workflow)

---

### 3.11 Analog (PARTIAL): `src/subsideo/cli.py` — argparse + `__main__` for supervisor

**Files that adopt this:** `validation/supervisor.py`

Check the structure of cli.py to match the `if __name__ == "__main__": sys.exit(main())` idiom. The supervisor follows Research Example 7 verbatim.

---

## 4. Cross-Cutting Conventions

### 4.1 Module docstring convention

```python
"""<One-line summary ending in period>.

<Optional paragraph with more detail. Wrap at ~100 chars.>
"""
```

Source: every existing file in `src/subsideo/` (verified in `_metadata.py:1-5`, `products/types.py:1-5`, `validation/metrics.py:1-5`, `validation/compare_rtc.py:1`).

### 4.2 First non-docstring line

```python
from __future__ import annotations
```

Required on every new module; applies to `_cog.py`, `_mp.py`, `criteria.py`, `results.py`, `matrix_schema.py`, `harness.py`, `stable_terrain.py`, `selfconsistency.py`, `supervisor.py`, `matrix_writer.py`.

### 4.3 Loguru logger import

```python
from loguru import logger
```

Always `logger` (lowercase) — never `Logger`. Use brace-style formatting:
```python
logger.info("CSLC validation: amp_corr={:.4f}, amp_RMSE={:.2f} dB", amp_corr, amp_rmse_db)
```
NOT `logger.info("CSLC validation: amp_corr=%.4f" % amp_corr)`.

Source: `_metadata.py:12`, `products/rtc.py:14`, `validation/compare_rtc.py:8`.

### 4.4 @dataclass style

```python
@dataclass
class Foo:
    """<docstring>"""

    field1: type1
    field2: type2 = default
    field3: dict[str, int] = field(default_factory=dict)
```

- blank line between docstring and fields
- `field(default_factory=dict)` idiom for mutable defaults
- no `__post_init__` in Phase 1 modules
- `@dataclass(frozen=True)` ONLY for `Criterion` in `criteria.py` (per D-01)

Source: `products/types.py:62-131` (5 dataclass examples).

### 4.5 Pydantic v2 BaseModel style (for matrix_schema.py only)

```python
class MetaJson(BaseModel):
    """<docstring>"""

    schema_version: int = Field(default=1, description="...")
    git_sha: str = Field(..., description="...")
    run_started_iso: str = Field(..., description="ISO-8601 UTC timestamp")
```

- `Field(default=..., description=...)` always with description
- `Field(...)` (Ellipsis) for required fields
- `T | None` (NOT `Optional[T]`) — `from __future__ import annotations` allows this

Source: `config.py:25-40` (5 Field examples).

### 4.6 Pytest marker naming

Existing markers (pyproject.toml lines 245-248): `slow`, `integration`, `validation`.

Phase 1 ADDS (per Claude's Discretion):
```
"reference_agreement: plumbing-only tests that never assert criteria.py thresholds",
```

Declared in `[tool.pytest.ini_options].markers` list, alphabetical after `integration`.

### 4.7 Run-eval script CLI structure (for 7 `run_eval*.py` scripts)

```python
# <filename>.py — <one-line description>
# <optional context lines>
import warnings; warnings.filterwarnings("ignore")

EXPECTED_WALL_S = 1800     # D-11: supervisor AST-parses this

if __name__ == "__main__":
    # stdlib + third-party imports
    # subsideo imports (including harness)
    # load_dotenv()
    # per-script scientific constants (BURST_ID, BBOX, etc.)
    # credential_preflight(...)
    # pipeline stages
```

Verified against `run_eval.py` (114 LOC) and `run_eval_cslc.py:1-7` (same structure).

### 4.8 Makefile conventions (NEW — no in-repo precedent)

Follow RESEARCH.md Example 11 verbatim. Key rules:
- `.PHONY:` declaration for every non-file target
- `SHELL := /bin/bash` (macOS default is `/bin/sh` which lacks `[[`)
- `PY := micromamba run -n subsideo python` — single indirection point
- `SUPERVISOR := $(PY) -m subsideo.validation.supervisor` — composed from PY
- Two-space indent INSIDE recipes is WRONG; Makefile requires TAB. Inline recipes with `; $(SUPERVISOR) ...` avoid the issue.

---

## 5. Anti-Patterns (MUST NOT introduce)

| # | Anti-Pattern | Why forbidden | Correct approach |
|---|--------------|---------------|------------------|
| A1 | **Rendering logic in `criteria.py`** — e.g. "CALIBRATING cells shown in yellow" constants in `criteria.py` | Conflates data (threshold values) with presentation (matrix_writer output shape). Violates SRP. | CALIBRATING-cell visual distinction lives in `matrix_writer.py` only (per D-03 Claude's Discretion). `criteria.py` stores ONLY threshold + comparator + type + rationale. |
| A2 | **CODEOWNERS file / pre-commit hook enforcing `criteria.py` immutability** | Rejected per D-03 — heavier than needed for solo-dev workflow. | Runtime `frozen=True` on the `Criterion` dataclass + `matrix_writer.py` echoing threshold alongside measured value in `results/matrix.md` (drift visibility via git diff). PR review policy (cite ADR) is the social enforcement. |
| A3 | **`@property` back-compat aliases on `<Product>ValidationResult`** — e.g. `@property def rmse_db(self): return self.reference_agreement.measurements["rmse_db"]` | REJECTED per D-09 big-bang migration. Back-compat aliases would silence the fail-fast behavior that catches any v1.0 script still reading `.rmse_db`. | Single atomic PR replaces all 5 ValidationResult classes + all 5 compare_*.py returns + all 5 test_compare_*.py files. No shims. |
| A4 | **Pre-populating Phase 5 placeholders in `criteria.py`** — e.g. `"dswx.f1_min_recalibrated": Criterion(..., threshold=PLACEHOLDER)` | REJECTED per D-05 — additive-only. A placeholder threshold is a lie (it doesn't reflect an ADR or spec). | Phase 5 adds its own `criteria.py` entries when the recalibration work lands. Phase 1 populates ONLY the 9 criteria listed in D-04 (5 v1.0 BINDING + 4 new CALIBRATING). |
| A5 | **Import direction violation: `products/* → validation/compare_*`** | Cycle — `validation/compare_*.py` already imports `from subsideo.products.types import *ValidationResult`. Adding the reverse creates a cycle. | ONLY `products/types.py → validation/results.py` is allowed (one-way, data-only leaf — per D-07). `validation/harness.py` MUST NEVER import from `subsideo.products.*`. |
| A6 | **Unconditional module-top import of rio_cogeo / isce3 / compass / dolphin in `_cog.py`, `_mp.py`, harness, selfconsistency, stable_terrain** | Breaks `pip install subsideo` users who don't have conda-forge stack. Violates established lazy-import convention. | Defer conda-forge-only imports into function bodies (matches `_metadata.py:71-73` and `products/rtc.py:102-103, 138-139`). Module top imports: stdlib + `loguru` + `numpy`/`scipy` only. |
| A7 | **`cog_validate` warnings swallowed** — e.g. `is_valid, _, _ = cog_validate(...)` | PITFALLS P0.3 — the IFD-offset warning is a real COG-layout break; discarding it causes silent COG degradation. | `_cog.cog_validate` MUST return `tuple[bool, list[str], list[str]]` with warnings surfaced; `ensure_valid_cog(path)` re-translates in place when IFD warning present. |
| A8 | **Naive retry on all HTTP errors** — e.g. `for _ in range(5): try: download() except: sleep(60)` | PITFALLS P0.4 — Earthdata 401 retries forever; CloudFront 403 needs URL refresh not retry. | Per-source `RETRY_POLICY` dict in `harness.py`; `download_reference_with_retry` REFUSES to proceed without an explicit source key. `abort_on` list raises `ReferenceDownloadError`. |
| A9 | **`threading.Thread` or `signal.alarm` watchdog instead of subprocess + os.killpg** | PITFALLS P0.1 — threads leak under fork; SIGALRM fragile under isce3/GDAL C extensions; grandchildren (dist-s1 isce3) aren't killed. | `subprocess.Popen(..., start_new_session=True)` + `os.killpg(pgid, SIGTERM/SIGKILL)` per D-12. |
| A10 | **Moving eval scripts to `scripts/` or `evals/`** | Breaks ~30+ CONCLUSIONS_*.md cross-references. | Keep eval scripts at repo root. Makefile target names abstract location. |
| A11 | **Globbing CONCLUSIONS_*.md to parse metric values** | Fragile — breaks on prose rewording. | `results/matrix_manifest.yml` + per-eval `{meta,metrics}.json` sidecars (Pydantic-schema'd in `matrix_schema.py`). |
| A12 | **Storing `.passed: bool` or `pass_criteria: dict[str, bool]` on result objects** | D-08 — pass/fail is computed at read time via `evaluate(result, criteria)`. Stored bools would drift-fail when `criteria.py` is edited (old `metrics.json` records become inconsistent). | Result objects store `measurements: dict[str, float]` + `criterion_ids: list[str]` only. `evaluate()` is the pass/fail oracle. |
| A13 | **`conda-lock` for v1.1** | Explicitly rejected for v1.1 (research-deferred to v2+). | Per-platform `micromamba list --explicit --md5` → `env.lockfile.<platform>.txt`. |
| A14 | **Test threshold assertions in `tests/reference_agreement/`** | Defeats the split — reference_agreement tests MUST only verify plumbing (no threshold values). | Move threshold-asserting tests to `tests/product_quality/`. Use `conftest.py` AST linter (Pitfall 6) to reject numeric-literal comparands in reference_agreement. |

---

## 6. No-Analog Files

Four files have no in-repo analog (entirely new file type at repo root):

| File | Why no analog | Primary template |
|------|---------------|------------------|
| `Dockerfile` | First Docker file in the repo | RESEARCH.md Example 9 (§J) — `mambaorg/micromamba:latest` multi-stage build |
| `Apptainer.def` | First Singularity recipe in the repo | RESEARCH.md Example 10 (§J) — derives from `docker-daemon://subsideo:dev` |
| `Makefile` | First Makefile in the repo | RESEARCH.md Example 11 (§G) — minimum viable ~20-line target set |
| `env.lockfile.{linux-64,osx-arm64}.txt` | First lockfiles in the repo | Generated output of `micromamba list --explicit --md5` — no hand-written template needed |

`conda-env.yml` also has no in-repo analog; `pyproject.toml`'s `[project.optional-dependencies]` grouping (lines 92-164) is the closest precedent for organising grouped deps with comments.

---

## 7. Metadata

**Analog search scope:**
- `src/subsideo/` (all 4 subdirs: products, validation, burst, data, utils, + root)
- `tests/unit/` (23 test modules inspected)
- `run_eval*.py` (8 scripts at repo root)
- `pyproject.toml`, `CLAUDE.md`, repo-root files

**Files scanned:** ~50 (all modules in `src/subsideo/` + all tests/unit + all run_eval* + config files + 2 research docs)

**Key patterns identified:**
1. Top-level leading-underscore private module precedent (`_metadata.py`) — drives `_cog.py` and `_mp.py` shape
2. Plain `@dataclass` with `from __future__ import annotations` for data containers (`products/types.py`) — drives `criteria.py` and `results.py`
3. Pydantic v2 BaseSettings/BaseModel with `Field(default=..., description=...)` (`config.py`) — drives `matrix_schema.py`
4. Pure-function validation helpers with NaN-mask handling (`validation/metrics.py`) — drives `harness.py`, `stable_terrain.py`, `selfconsistency.py`
5. `if __name__ == "__main__":` + `import warnings; warnings.filterwarnings("ignore")` guard as eval-script top-boilerplate — drives the 7 run_eval migration target shape
6. Lazy imports of conda-forge-only libs inside function bodies (`_metadata.py:71-73`, `products/rtc.py:102-103`) — carried into new leaf modules

**Pattern extraction date:** 2026-04-21

---

## PATTERN MAPPING COMPLETE

- **Phase:** 01 - environment-hygiene-framework-consolidation-guardrail-scaffolding
- **Files classified:** 40 (22 new + 10 modified + 8 unchanged modules referenced)
- **Analogs found:** 36/40 (4 repo-root infra files have no in-repo analog; RESEARCH.md Examples 8–11 are their templates)
- **Coverage:**
  - Files with exact analog: 28 (new files inheriting established precedent)
  - Files with role-match analog: 8 (new public utility modules in validation/)
  - Files with no analog: 4 (repo-root infra)
- **Key patterns:** top-level `_private.py`, plain `@dataclass`, Pydantic v2 BaseModel, pure-function numpy helpers, `from __future__ import annotations`, loguru-style logging, lazy conda-forge imports, `if __name__ == "__main__"` + `EXPECTED_WALL_S` eval-script shape
- **File created:** `.planning/phases/01-environment-hygiene-framework-consolidation-guardrail-scaffolding/01-PATTERNS.md`
- **Ready for planning:** Pattern mapping complete. Planner can reference analog patterns directly in PLAN.md per-file action sections.
