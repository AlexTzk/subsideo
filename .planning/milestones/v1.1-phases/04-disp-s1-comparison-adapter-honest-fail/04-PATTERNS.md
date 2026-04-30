# Phase 4: DISP-S1 Comparison Adapter + Honest FAIL — Pattern Map

**Mapped:** 2026-04-25
**Files analyzed:** 14 (modified: 9; renamed: 1; new: 2; tests: 4 — likely)
**Analogs found:** 14 / 14 (every target file has at least one strong in-repo analog)

> **Read these first** (mandatory before touching any target):
> - `/Volumes/Geospatial/Geospatial/subsideo/.planning/phases/04-disp-s1-comparison-adapter-honest-fail/04-CONTEXT.md`
> - `/Volumes/Geospatial/Geospatial/subsideo/.planning/phases/04-disp-s1-comparison-adapter-honest-fail/04-RESEARCH.md`
> - `/Volumes/Geospatial/Geospatial/subsideo/.planning/research/PITFALLS.md` §P3.1, §P3.2
> - `/Volumes/Geospatial/Geospatial/subsideo/.planning/research/FEATURES.md` lines 67-76, 142-143
> - `/Volumes/Geospatial/Geospatial/subsideo/.planning/research/ARCHITECTURE.md` §3 (lines 133-158)

---

## File Classification

| Target File | Role | Data Flow | Closest Analog | Match Quality |
|-------------|------|-----------|----------------|---------------|
| `src/subsideo/validation/compare_disp.py` | validation helper, additive top-level fn + dataclass | transform (raster → raster/array) | self (existing `compare_disp` Step 2 reproject) + `selfconsistency.py` (pure-function-helpers + module-level constants pattern) | exact (same module; additive only) |
| `src/subsideo/validation/selfconsistency.py` | validation helper, pure-function module additive extension | transform (stack → per-IFG dict) | self (existing `coherence_stats`, `residual_mean_velocity`) | exact (same module + same docstring + same numpy-only convention) |
| `src/subsideo/validation/matrix_schema.py` | data-model, Pydantic v2 BaseModel additive types | (no I/O — schema only) | existing `RTCEUCellMetrics` + `CSLCSelfConsistNAMCellMetrics` (schema_version-aware extension of `MetricsJson`) | exact (same Phase 1 D-09 additive-only convention) |
| `src/subsideo/validation/matrix_writer.py` | renderer, manifest-driven dispatch + cell render branch | request-response (path → tuple[str, str]) | existing `_render_cslc_selfconsist_cell` + `_is_cslc_selfconsist_shape` | exact (Phase 3 D-08 — symmetric two-cell render branch + JSON shape discriminator) |
| `run_eval_disp.py` | eval-script orchestration, harness consumer | batch (auth → search → reproject → metrics.json) | `run_eval_cslc_selfconsist_nam.py` (closest — same harness + Phase 3 nested PQ block) + self (existing 9-stage pipeline) | role-match (Phase 3 nested PQ block is the closest "product-quality + write metrics.json" pattern) |
| `run_eval_disp_egms.py` | eval-script orchestration, EU variant | batch (auth → CDSE STAC → reproject → metrics.json) | `run_eval_disp.py` post-Phase-4 + `run_eval_cslc_selfconsist_eu.py` | role-match (parallel to N.Am. variant; differs only in CDSE/EGMS data-source) |
| `CONCLUSIONS_DISP_N_AM.md` (modify) | docs, narrative + investigation tables | append-only | `CONCLUSIONS_RTC_EU.md` (multi-section CONCLUSIONS w/ Calibration Framing + Investigation tables + Attribution) | exact (Phase 2 — same multi-section append discipline) |
| `CONCLUSIONS_DISP_EU.md` (post-rename + modify) | docs, narrative + investigation tables | append-only | `CONCLUSIONS_RTC_EU.md` + `CONCLUSIONS_DISP_N_AM.md` post-Phase-4 | exact (mirror of N.Am. variant; rename via `git mv`) |
| `docs/validation_methodology.md` | docs, methodology consolidation | append-only | existing §1 (CSLC cross-version impossibility) + §2 (PQ vs RA distinction) | exact (Phase 3 D-15 single-PR-per-phase append) |
| `results/matrix_manifest.yml` | config, declarative cell list | (parse-only) | existing `disp:eu` cell entry | exact (one-line edit; field already references `CONCLUSIONS_DISP_EU.md`) |
| `CONCLUSIONS_DISP_EGMS.md` → `CONCLUSIONS_DISP_EU.md` (rename) | docs, narrative | rename | (no code analog — `git mv` operation) | n/a |
| `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md` (new) | docs, research handoff | append-only (new file) | `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` + `cslc_selfconsist_aoi_candidates.md` | exact (same v1.1-research/ location + same probe-artifact one-page convention) |
| `tests/unit/test_compare_disp.py` (new) | test, pytest unit | request-response (synthetic raster → assert) | existing `tests/unit/test_compare_*.py` (TBD by plan-phase) | role-match |
| `tests/unit/test_selfconsistency.py` (extend) | test, pytest unit | request-response (synthetic stack → assert) | existing `tests/unit/test_selfconsistency.py` | exact |

---

## Pattern Assignments

### `src/subsideo/validation/compare_disp.py` (validation helper, transform)

**Analog:** `src/subsideo/validation/compare_disp.py` itself (existing `compare_disp` Step 2 reproject — line 138-147) AND `src/subsideo/validation/selfconsistency.py` (module-shape pattern: lazy imports + numpy-only deps + raise-on-misuse).

**Files to read first:**
- `/Volumes/Geospatial/Geospatial/subsideo/src/subsideo/validation/compare_disp.py` (entire — 380 LOC)
- `/Volumes/Geospatial/Geospatial/subsideo/src/subsideo/validation/selfconsistency.py` (lines 1-30 for module docstring + import conventions)

**Existing reproject pattern to refactor** (`compare_disp.py` lines 132-147 — the v1.0 ad-hoc bilinear that Phase 4 D-01/D-02 replaces with `prepare_for_reference(method="block_mean")`):
```python
# 1. Load EGMS reference grid (target grid -- per Pitfall 4)
with rasterio.open(egms_ortho_path) as ref:
    egms_data = ref.read(1).astype(np.float64)
    egms_transform = ref.transform
    egms_crs = ref.crs

# 2. Reproject subsideo product to match EGMS grid
prod_aligned = np.empty_like(egms_data)
with rasterio.open(product_path) as prod:
    reproject(
        source=rasterio.band(prod, 1),
        destination=prod_aligned,
        dst_transform=egms_transform,
        dst_crs=egms_crs,
        resampling=Resampling.bilinear,
    )
```

**Existing point-sampling pattern** (`compare_disp.py` lines 290-326 — the analog for `_point_sample(...)` form-c branch):
```python
with rasterio.open(velocity_path) as src:
    raster_crs = src.crs
    nodata = src.nodata          # capture before exit (CR-01 already-fixed)
    points_proj = points.to_crs(raster_crs)
    left, bottom, right, top = src.bounds
    in_bounds = (
        (points_proj.geometry.x >= left)
        & (points_proj.geometry.x <= right)
        & (points_proj.geometry.y >= bottom)
        & (points_proj.geometry.y <= top)
    )
    points_in = points_proj[in_bounds].copy()
    xy = list(zip(points_in.geometry.x, points_in.geometry.y, strict=True))
    sampled = np.array([v[0] for v in src.sample(xy)], dtype=np.float64)
```

**Module convention to mirror** (existing `compare_disp.py` lines 1-29):
- `from __future__ import annotations` at top
- Module docstring listing the two comparison paths
- Module-level constant `SENTINEL1_WAVELENGTH_M = 0.05546576` (line 33)
- `loguru.logger` imported at module level
- Numpy + rasterio + xarray imports at module top (NOT lazy — these are validation-extras already, see line 21-25)
- `_underscore` private helpers below the public functions (`_los_to_vertical`, `_load_egms_l2a_points`)

**New additions per RESEARCH.md §"Architecture / prepare_for_reference signature"** (lines 109-216):
- `@dataclass(frozen=True) class ReferenceGridSpec` — DISP-01 form (c) for EGMS L2a point-sampling
- `MultilookMethod = Literal["gaussian", "block_mean", "bilinear", "nearest"]`
- `def prepare_for_reference(native_velocity, reference_grid, *, method: MultilookMethod | None = None)` — D-01 explicit-no-default + D-04 raise-on-missing
- 3 private helpers: `_resample_onto_path`, `_resample_onto_dataarray`, `_point_sample`
- 4 method-branch kernels (gaussian via `scipy.ndimage.gaussian_filter`, block_mean via custom 6×6 stride aggregation, bilinear via `Resampling.bilinear`, nearest via `Resampling.nearest`)

**Critical gotcha from existing code (CR-01 already-fixed):**
`compare_disp_egms_l2a()` line 294 captures `nodata = src.nodata` *before* the `with` block exits — the new `_point_sample()` helper MUST mirror this pattern. Accessing `src.nodata` after `with rasterio.open(...) as src:` exits raises RasterioIOError.

**Optional refactor (D-Claude's-Discretion in CONTEXT):**
`compare_disp()` Step 2 (lines 138-147) and `compare_disp_egms_l2a()` Step 2 (lines 290-326) MAY be refactored to internally call `prepare_for_reference(method="bilinear")` to preserve v1.0 semantics — but the eval-script callsites (`run_eval_disp.py` Stage 9, `run_eval_disp_egms.py` Stage 9) MUST use `method="block_mean"` per D-02. Plan-phase decides scope of internal refactor; safest is to leave the two existing top-level functions calling `Resampling.bilinear` directly and only update the eval-script Stage 9 callsites. CONTEXT D-18 is explicit: do NOT extract to `validation/adapters.py`.

---

### `src/subsideo/validation/selfconsistency.py` (validation helper, transform)

**Analog:** Self — existing `coherence_stats` (lines 33-122) and `residual_mean_velocity` (lines 125-185).

**Files to read first:**
- `/Volumes/Geospatial/Geospatial/subsideo/src/subsideo/validation/selfconsistency.py` (entire — 327 LOC)

**Existing pure-function helper pattern** (`selfconsistency.py` lines 33-69):
```python
def coherence_stats(
    ifgrams_stack: np.ndarray,
    stable_mask: np.ndarray,
    *,
    coherence_threshold: float = DEFAULT_COHERENCE_THRESHOLD,
) -> dict[str, float]:
    """Return per-stable-pixel coherence statistics across an IFG stack.

    Ships every candidate statistic (mean / median / p25 / p75 /
    persistently_coherent_fraction) so Phase 3 calibration can pick the
    appropriate bar without another dataclass edit (PITFALLS P2.2).

    Parameters
    ----------
    ifgrams_stack : (N, H, W) float np.ndarray
        Per-IFG coherence arrays in [0, 1]. NaN entries are treated as 0
        ...
    """
    if int(stable_mask.sum()) == 0:
        logger.warning("coherence_stats called with empty stable_mask -- returning zeros")
        return {... zeros ...}
```

**Existing return-dict-of-floats pattern** (`coherence_stats` lines 88-110):
```python
stats: dict[str, float] = {
    "mean": float(vals.mean()),
    "median": float(np.median(vals)),
    "p25": float(np.percentile(vals, 25)),
    "p75": float(np.percentile(vals, 75)),
}
# ... computation ...
stats["persistently_coherent_fraction"] = float(num_persistent) / float(int(stable_mask.sum()))
stats["median_of_persistent"] = float(np.median(per_pixel_mean[persistent_stable]))
```

**Module convention to mirror** (`selfconsistency.py` lines 1-30):
- `from __future__ import annotations` first
- Module docstring describes the broader charter ("Sequential-IFG self-consistency primitives" — Phase 4 D-10 broadens this from "Sequential-IFG coherence + reference-frame residual")
- `import numpy as np` + `from loguru import logger` at module top
- Module-level constant `DEFAULT_COHERENCE_THRESHOLD: float = 0.6` (line 30)
- Lazy-import `h5py` inside function bodies for conda-forge deps (line 241 `import h5py  # lazy`)
- Numpy-only computation; `import scipy.stats import circstd` lazy inside `compute_ramp_aggregate` if used (per RESEARCH.md line 661)
- `logger.debug()` with `{}` placeholder format strings (line 111-121, 179-184)

**New additions per RESEARCH.md §"Architecture / fit_planar_ramp algorithm"** (lines 218-327):
- `def fit_planar_ramp(ifgrams_stack: np.ndarray, mask: np.ndarray | None = None) -> dict[str, np.ndarray]` — D-10 signature
- 5-key return dict: `ramp_magnitude_rad`, `ramp_direction_deg`, `slope_x`, `slope_y`, `intercept_rad` (all length-N np.ndarray)
- `def compute_ramp_aggregate(ramp_data, ifg_coherence_per_ifg) -> RampAggregate` (RESEARCH.md lines 650-691)
- `def auto_attribute_ramp(direction_stability_sigma_deg, magnitude_vs_coherence_pearson_r, *, direction_stability_cutoff_deg=30.0, coherence_correlation_cutoff=0.5) -> Literal[...]` (RESEARCH.md lines 615-644)

**Module-level constants to add (per CONTEXT D-Claude's-Discretion):**
- Cutoffs are NOT criteria.py entries — they live as default kwarg values on `auto_attribute_ramp` (rule is for narrative attribution, not gating).

**Existing raise-on-misuse pattern** (`residual_mean_velocity` lines 161-176):
```python
if int(stable_mask.sum()) == 0:
    raise ValueError("stable_mask is empty; cannot compute residual mean velocity")
# ...
if frame_anchor == "median":
    anchor = float(np.median(vals))
elif frame_anchor == "mean":
    anchor = float(vals.mean())
else:
    raise ValueError(
        f"frame_anchor must be 'median' or 'mean', got {frame_anchor!r}"
    )
```

`fit_planar_ramp` MUST mirror this discipline: raise `ValueError` on `ifgrams_stack.ndim != 3` (RESEARCH.md lines 269-272) and return NaN-filled per-IFG entries when `keep.sum() < 100` (RESEARCH.md lines 294-301).

---

### `src/subsideo/validation/matrix_schema.py` (data-model, Pydantic v2)

**Analog:** Existing `RTCEUCellMetrics` (lines 255-306) and `CSLCSelfConsistNAMCellMetrics` (lines 390-436) — both extend the `MetricsJson` base.

**Files to read first:**
- `/Volumes/Geospatial/Geospatial/subsideo/src/subsideo/validation/matrix_schema.py` (entire — 449 LOC)

**Existing Pydantic v2 BaseModel pattern** (`matrix_schema.py` lines 158-252 — the `BurstResult` row model):
```python
class BurstResult(BaseModel):
    """Per-burst row inside RTCEUCellMetrics.per_burst (Phase 2 D-10).

    Shape: one BurstResult per burst in the declarative BURSTS list ...
    """

    model_config = ConfigDict(extra="forbid")

    burst_id: str = Field(
        ...,
        description="JPL-format burst ID, lowercase, e.g. 't144_308029_iw1'.",
    )
    regime: Literal["Alpine", "Scandinavian", "Iberian", "TemperateFlat", "Fire"] = Field(
        ...,
        description=(
            "Terrain regime label covering the BOOTSTRAP §1.1 five categories. "
            "Matches D-03 (5-burst fixed list). Hand-labelled per burst."
        ),
    )
    lat: float | None = Field(
        default=None,
        description="Centroid latitude (deg). None if DEM/bounds lookup failed.",
    )
    # ... etc
```

**Module convention to mirror** (`matrix_schema.py` lines 1-26):
- `from __future__ import annotations` first non-docstring line (PATTERNS §4.2 reference)
- `from pydantic import BaseModel, ConfigDict, Field` (line 25)
- `from typing import Literal` (line 23) — used for AOIStatus / CellStatus Literals
- `model_config = ConfigDict(extra="forbid")` on every class — Phase 1 D-09 lock-in

**Existing aggregate-extending-base pattern** (`matrix_schema.py` lines 255-306 — `RTCEUCellMetrics(MetricsJson)`):
```python
class RTCEUCellMetrics(MetricsJson):
    """RTC-EU multi-burst aggregate extending the base MetricsJson schema (D-09).

    Inherits schema_version / product_quality / reference_agreement /
    criterion_ids_applied / runtime_conda_list_hash from MetricsJson. Adds
    the aggregate count fields + per_burst drilldown list.

    matrix_writer (Plan 02-03) detects this schema via the presence of
    ``per_burst`` in the raw JSON and renders ``X/N PASS`` + investigation
    annotation instead of the default single-cell PQ/RA columns.
    """

    pass_count: int = Field(..., ge=0, description="Count of bursts ...")
    total: int = Field(..., ge=1, description="Total number of bursts ...")
    all_pass: bool = Field(..., description="True when pass_count == total ...")
    # ...
    per_burst: list[BurstResult] = Field(default_factory=list, description="...")
```

**Existing forward-ref-rebuild pattern** (`matrix_schema.py` lines 311-387 — `AOIResult` with self-referential `attempts: list[AOIResult]`):
```python
class AOIResult(BaseModel):
    """..."""
    # ...
    attempts: list[AOIResult] = Field(
        default_factory=list,
        description="Nested fallback attempts; empty for leaf AOIs.",
    )
    # ...

AOIResult.model_rebuild()  # resolve forward-ref for self-referential 'attempts' list
```

Phase 4 schema additions (`PerIFGRamp`, `RampAggregate`, `RampAttribution`, `DISPProductQualityResultJson`, `DISPCellMetrics`) per RESEARCH.md lines 333-512 — none are self-referential, so `model_rebuild()` is NOT required, but every class MUST have `model_config = ConfigDict(extra="forbid")` and use `Field(..., description=...)` for every field per the convention.

**Schema-version invariant (Phase 1 D-09):**
- All new types are *additive* — no edits to existing fields on `MetricsJson`, `ProductQualityResultJson`, `ReferenceAgreementResultJson`, `BurstResult`, `RTCEUCellMetrics`, `AOIResult`, `CSLCSelfConsist*CellMetrics`.
- `DISPCellMetrics(MetricsJson)` overrides `product_quality` and `reference_agreement` with the existing types (the override is type-narrowing — `DISPProductQualityResultJson` extends `ProductQualityResultJson` to add `coherence_source`). This is allowed because Pydantic v2 supports field-type narrowing on subclass.

---

### `src/subsideo/validation/matrix_writer.py` (renderer, request-response)

**Analog:** Existing `_render_cslc_selfconsist_cell` (lines 254-348) + `_is_cslc_selfconsist_shape` (lines 236-251) — the closest two-cell render branch (cslc:nam + cslc:eu) with JSON shape discriminator.

**Files to read first:**
- `/Volumes/Geospatial/Geospatial/subsideo/src/subsideo/validation/matrix_writer.py` (entire — 475 LOC)
- Specifically lines 233-348 (CSLC self-consist render branch — closest analog for DISP) and lines 351-446 (`write_matrix` dispatch order)

**Existing JSON shape discriminator pattern** (`matrix_writer.py` lines 236-251):
```python
def _is_cslc_selfconsist_shape(metrics_path: Path) -> bool:
    """Return True when the metrics.json has a top-level ``per_aoi`` key.

    Phase 3 D-11 schema discriminator. Checked BEFORE _is_rtc_eu_shape so a
    file that somehow contains both (defensive) is routed to the self-consist
    branch; the schemas are structurally disjoint so this is an invariant,
    not a guess.
    """
    import json as _json

    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.debug("_is_cslc_selfconsist_shape: cannot read {}: {}", metrics_path, e)
        return False
    return isinstance(raw, dict) and "per_aoi" in raw
```

**Existing two-cell symmetric render-branch pattern** (`matrix_writer.py` lines 254-348 — `_render_cslc_selfconsist_cell` handling both nam + eu via `region` parameter):
```python
def _render_cslc_selfconsist_cell(
    metrics_path: Path,
    *,
    region: str,
) -> tuple[str, str] | None:
    """Render a Phase 3 CSLC self-consistency cell as (pq_col, ra_col).

    Called for both cslc:nam (region='nam') and cslc:eu (region='eu'). The
    cell always italicises (CALIBRATING is the only valid status for first
    rollout per Phase 3 D-03 + GATE-05). Appends U+26A0 on any_blocker=True.
    ...
    """
    from subsideo.validation.matrix_schema import (
        CSLCSelfConsistEUCellMetrics,
        CSLCSelfConsistNAMCellMetrics,
    )

    try:
        cls = CSLCSelfConsistEUCellMetrics if region == "eu" else CSLCSelfConsistNAMCellMetrics
        metrics = cls.model_validate_json(metrics_path.read_text())
    except Exception as e:
        logger.warning(
            "Failed to parse CSLCSelfConsist*CellMetrics from {}: {}", metrics_path, e
        )
        return None
    # ... render logic ...
```

**Existing dispatch-insertion pattern** (`matrix_writer.py` lines 388-423 — the `write_matrix` body):
```python
# Phase 3 CSLC self-consistency branch: metrics.json with a ``per_aoi`` key.
# Checked BEFORE the rtc_eu branch so a file with both keys (defensive)
# is routed here (schemas are structurally disjoint, this is an invariant).
if metrics_path.exists() and _is_cslc_selfconsist_shape(metrics_path):
    cols = _render_cslc_selfconsist_cell(metrics_path, region=str(cell["region"]))
    if cols is not None:
        pq_col, ra_col = cols
        lines.append(
            f"| {product} | {region} | {_escape_table_cell(pq_col)} | "
            f"{_escape_table_cell(ra_col)} |"
        )
        continue
    # Fall through to default rendering on parse failure.

# Phase 2 D-11 branch: metrics.json with a ``per_burst`` key ...
if metrics_path.exists() and _is_rtc_eu_shape(metrics_path):
    ...
```

**Phase 4 dispatch insertion (per RESEARCH.md lines 593-608):**
The new `_is_disp_cell_shape` branch (looks for `ramp_attribution` key) MUST be inserted BEFORE the `_is_cslc_selfconsist_shape` branch in `write_matrix()`. RESEARCH.md is explicit that "DISP `ramp_attribution` is a distinct discriminator and structurally never co-occurs with `per_aoi` or `per_burst`" — this is an invariant, not a guess.

**Existing CALIBRATING-italics + warning-glyph pattern** (`matrix_writer.py` lines 343-348):
```python
# Warning glyph on any_blocker (U+26A0)
warn = " ⚠" if metrics.any_blocker else ""
# Italicise as whole-body — CALIBRATING discipline (Phase 1 D-03 / GATE-03)
pq_col = f"*{pq_body}*{warn}"
ra_col = f"*{ra_body}*" if ra_body != "—" else "—"
return pq_col, ra_col
```

DISP cells render with CALIBRATING italics on PQ side + non-italics PASS/FAIL on RA side per CONTEXT D-19 (cell_status = MIXED is the expected outcome). RESEARCH.md lines 565-590 give the full PQ/RA format — copy that shape.

**`_render_measurement` reuse:**
The DISP RA column (RESEARCH.md lines 584-589) uses the existing `_render_measurement(cid, measurements)` helper (matrix_writer.py lines 73-91) for each criterion ID — it produces `value (<op> threshold VERDICT)` strings consistently across the file. Do NOT re-implement this format.

---

### `run_eval_disp.py` (eval-script orchestration, batch)

**Analog:** `run_eval_cslc_selfconsist_nam.py` is the closest harness-consumer + nested-PQ-block pattern. Self (existing 9 stages) provides the auth/search/run_disp/velocity-read scaffolding to keep unchanged.

**Files to read first:**
- `/Volumes/Geospatial/Geospatial/subsideo/run_eval_disp.py` (entire — 859 LOC); pay attention to:
  - lines 19-46 (header + imports + `EXPECTED_WALL_S`)
  - lines 580-670 (Stage 9 reproject + comparison — the v1.0 ad-hoc bilinear that Phase 4 replaces)
- `/Volumes/Geospatial/Geospatial/subsideo/run_eval_cslc_selfconsist_nam.py` (1277 LOC); pay attention to:
  - lines 1-100 (header + EXPECTED_WALL_S + imports + credential_preflight)
  - lines 1100-1245 (per-AOI metrics block + write metrics.json + write meta.json — closest analog for Phase 4 Stage 10/11/12 additions)

**Existing module-header + EXPECTED_WALL_S pattern** (`run_eval_disp.py` lines 1-19):
```python
# run_eval_disp.py — N.Am. DISP-S1 validation against OPERA
#
# Downloads a 6-month stack of S1 IW SLC scenes from ASF DAAC, builds
# a CSLC-S1 stack using compass, runs the full DISP pipeline ...
# ...
# Resume-safe: each stage skips work if outputs already exist.
import warnings; warnings.filterwarnings("ignore")

EXPECTED_WALL_S = 5400   # Plan 01-07 supervisor AST-parses this constant (D-11)
```

Phase 4 D-04 + D-Claude's-Discretion update both eval scripts:
```python
# Phase 4 — bumped from 5400 → 21600 to cover warm + cold + safety margin (CONTEXT D-Claude's-Discretion).
EXPECTED_WALL_S = 60 * 60 * 6   # 21600 s; supervisor AST-parses this constant
REFERENCE_MULTILOOK_METHOD: Literal["block_mean"] = "block_mean"  # Phase 4 D-04
```

**Existing `if __name__ == "__main__":` + harness pattern** (`run_eval_disp.py` lines 21-99 — guard + imports + `load_dotenv()` + `credential_preflight` first):
```python
if __name__ == "__main__":
    import os
    import sys
    import time
    import sqlite3
    from pathlib import Path
    from datetime import datetime
    from dotenv import load_dotenv

    import asf_search as asf
    import earthaccess
    import numpy as np
    import h5py

    from subsideo.products.cslc import run_cslc
    from subsideo.products.disp import run_disp
    from subsideo.data.dem import fetch_dem
    from subsideo.data.orbits import fetch_orbit
    from subsideo.validation.harness import (
        bounds_for_burst,
        bounds_for_mgrs_tile,
        credential_preflight,
        download_reference_with_retry,
        ensure_resume_safe,
        select_opera_frame_by_utc_hour,
    )

    load_dotenv()

    credential_preflight([
        "CDSE_CLIENT_ID", "CDSE_CLIENT_SECRET",
        "EARTHDATA_USERNAME", "EARTHDATA_PASSWORD",
    ])
```

**Existing v1.0 Stage-9 reproject pattern that Phase 4 D-01 replaces** (`run_eval_disp.py` lines 609-632):
```python
# Compare against our velocity by reprojecting our output to OPERA grid
print("\n  Reprojecting our velocity to OPERA grid...")
from rasterio.warp import Resampling, reproject
from rasterio.transform import from_origin

# Build OPERA grid transform from x/y coordinates
opera_dx = float(opera_x[1] - opera_x[0])
opera_dy = float(opera_y[1] - opera_y[0])  # typically negative
opera_transform = from_origin(...)

our_on_opera = np.full(opera_velocity.shape, np.nan, dtype=np.float32)
with rasterio.open(velocity_path) as src:
    reproject(
        source=rasterio.band(src, 1),
        destination=our_on_opera,
        dst_transform=opera_transform,
        dst_crs=f"EPSG:{opera_crs_epsg}",
        resampling=Resampling.bilinear,    # <--- replaced by prepare_for_reference(method="block_mean")
    )
```

**Replacement (per CONTEXT D-04 + D-02):**
```python
# Phase 4 D-01 + D-02: replace ad-hoc Resampling.bilinear with the explicit
# prepare_for_reference adapter at the conservative block_mean method.
from subsideo.validation.compare_disp import prepare_for_reference
import xarray as xr
import rioxarray  # noqa: F401 — registers .rio accessor

opera_da = xr.DataArray(
    opera_velocity,
    dims=("y", "x"),
    coords={"y": opera_y, "x": opera_x},
).rio.write_crs(f"EPSG:{opera_crs_epsg}").rio.write_transform(opera_transform)
our_on_opera = prepare_for_reference(
    velocity_path,
    reference_grid=opera_da,   # form (b) per DISP-01
    method=REFERENCE_MULTILOOK_METHOD,   # D-02 + D-04 module constant
)
```

**Closest pattern for new Stage 10 (product-quality block) — `run_eval_cslc_selfconsist_nam.py` lines 1136-1164:**
```python
# 9. Stable-mask sanity artifacts (P2.1) — use the CSLC-grid stable_mask
_write_sanity_artifacts(
    cfg.aoi_name,
    stable_mask=stable_mask_cslc,
    coherence_stack=ifgrams_stack,
    transform=cslc_transform,
    crs=cslc_crs,
    out_dir=CACHE / "sanity" / cfg.aoi_name,
)

# 10. Build AOIResult -- CALIBRATING per D-03 first-rollout
pq = ProductQualityResultJson(
    measurements={
        "coherence_median_of_persistent": coh_stats["median_of_persistent"],
        "residual_mm_yr": residual,
        # Diagnostics (not gate-critical; surfaced in CONCLUSIONS §4b)
        "coherence_mean": coh_stats["mean"],
        "coherence_median": coh_stats["median"],
        "coherence_p25": coh_stats["p25"],
        "coherence_p75": coh_stats["p75"],
        "persistently_coherent_fraction": coh_stats["persistently_coherent_fraction"],
    },
    criterion_ids=[
        "cslc.selfconsistency.coherence_min",
        "cslc.selfconsistency.residual_mm_yr_max",
    ],
)
```

Phase 4 mirrors this exactly with `disp.selfconsistency.coherence_min` + `residual_mm_yr_max` criterion IDs (Phase 1 D-04 already shipped these). Provenance flag goes on `DISPProductQualityResultJson.coherence_source` (NOT inside `measurements` per RESEARCH.md lines 446-462).

**Closest pattern for cross-cell read (D-08)** — there is no existing cross-cell read in the v1.1 codebase yet; the eval script must:
1. Check existence: `Path("eval-cslc-selfconsist-nam/metrics.json").exists()` (only for SoCal/N.Am., not Bologna)
2. Parse via `CSLCSelfConsistNAMCellMetrics.model_validate_json(...)` (matrix_schema import already in CSLC eval scripts)
3. Drill into `metrics.per_aoi[idx_socal].product_quality.measurements["coherence_median_of_persistent"]`
4. Set `coherence_source = "phase3-cached"` if found; fall back to fresh compute with `coherence_source = "fresh"` otherwise

**Closest pattern for new Stage 11 (ramp-attribution block) — RESEARCH.md lines 261-271 + `run_eval_cslc_selfconsist_nam.py` style:**
```python
unwrapped_ifgrams_stack = read_dolphin_unwrapped_ifgs(disp_dir)  # (N, H, W) rad
ramp_data = fit_planar_ramp(unwrapped_ifgrams_stack, mask=None)
ramp_aggregate = compute_ramp_aggregate(ramp_data, ifg_coherence_per_ifg=...)
attributed_source = auto_attribute_ramp(
    direction_stability_sigma_deg=ramp_aggregate.direction_stability_sigma_deg,
    magnitude_vs_coherence_pearson_r=ramp_aggregate.magnitude_vs_coherence_pearson_r,
)
ramp_attribution = RampAttribution(
    per_ifg=[PerIFGRamp(...) for k, ramp in enumerate(ramp_data)],
    aggregate=ramp_aggregate,
    attributed_source=attributed_source,
    attribution_note="Automated; human review pending in CONCLUSIONS",
)
```

**Closest pattern for new Stage 12 (write metrics.json + meta.json) — `run_eval_cslc_selfconsist_nam.py` lines 1193-1244:**
```python
metrics = CSLCSelfConsistNAMCellMetrics(
    product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
    reference_agreement=ReferenceAgreementResultJson(measurements={}, criterion_ids=[]),
    criterion_ids_applied=[
        "cslc.selfconsistency.coherence_min",
        "cslc.selfconsistency.residual_mm_yr_max",
        "cslc.amplitude_r_min",
        "cslc.amplitude_rmse_db_max",
    ],
    pass_count=pass_count,
    total=total,
    cell_status=cell_status,
    any_blocker=any_blocker,
    product_quality_aggregate=pq_agg,
    reference_agreement_aggregate=ra_agg,
    per_aoi=per_aoi,
)

metrics_path = CACHE / "metrics.json"
metrics_path.write_text(metrics.model_dump_json(indent=2))
logger.info("Wrote {}", metrics_path)

# -- meta.json -----------------------------------------------------------
meta = MetaJson(
    schema_version=1,
    git_sha=git_sha,
    git_dirty=git_dirty,
    run_started_iso=run_started_iso,
    run_duration_s=time.time() - run_started,
    python_version=sys.version.split()[0],
    platform=platform.platform(),
    input_hashes=flat_input_hashes,
)
meta_path = CACHE / "meta.json"
meta_path.write_text(meta.model_dump_json(indent=2))
```

Phase 4 mirror: instantiate `DISPCellMetrics` instead of `CSLCSelfConsistNAMCellMetrics`. The `criterion_ids_applied` list expands to: `disp.selfconsistency.coherence_min`, `disp.selfconsistency.residual_mm_yr_max`, `disp.correlation_min`, `disp.bias_mm_yr_max`. The reference_agreement measurement keys are `correlation`, `bias_mm_yr`, `rmse_mm_yr`, `sample_count` (per RESEARCH.md line 495-498).

**Existing summary-banner pattern at end of run** (`run_eval_cslc_selfconsist_nam.py` lines 1248-1269):
```python
print()
print("=" * 70)
print(
    f"eval-cslc-selfconsist-nam: {pass_count}/{total} {cell_status}",
    ("[investigation]" if any_blocker else ""),
)
for row in per_aoi:
    coh = (
        row.product_quality.measurements.get("coherence_median_of_persistent", -1.0)
        if row.product_quality
        else -1.0
    )
    res = ...
    print(f"  [{row.status}] {row.aoi_name:20s} coh={coh:.3f} residual={res:+.2f} mm/yr")
print("=" * 70)
```

Phase 4 mirrors this exactly — single-cell summary banner with the 4 numbers (coh / resid / r / bias) and the auto-attribute label (e.g. `attr=phass`).

---

### `run_eval_disp_egms.py` (eval-script orchestration, batch — EU variant)

**Analog:** `run_eval_disp.py` post-Phase-4 (parallel changes) AND `run_eval_cslc_selfconsist_eu.py` (CDSE STAC harness pattern).

**Files to read first:**
- `/Volumes/Geospatial/Geospatial/subsideo/run_eval_disp_egms.py` (entire — 565 LOC); pay attention to lines 1-90 (header + imports + CDSE/EGMS credential preflight)
- `/Volumes/Geospatial/Geospatial/subsideo/run_eval_cslc_selfconsist_eu.py` (1130 LOC) for CDSE STAC + EGMS L2a download patterns

**5 changes mirror N.Am. exactly per CONTEXT D-Claude's-Discretion:**
1. Stage 9 ad-hoc reproject → `prepare_for_reference(method="block_mean")` callsite (CONTEXT line 215-216)
2. NEW Stage 10 product-quality block (Bologna fresh path — D-08: `coherence_source="fresh"`, no Phase 3 cache reuse)
3. NEW Stage 11 ramp-attribution block (same `fit_planar_ramp` + `compute_ramp_aggregate` + `auto_attribute_ramp` chain)
4. NEW metrics.json schema upgrade to `DISPCellMetrics`
5. Module-level `REFERENCE_MULTILOOK_METHOD` + `EXPECTED_WALL_S = 21600` constants

**Bologna-specific gotchas:**
- D-21: cache_dir is `eval-disp-egms/` (with hyphen — see `run_eval_disp_egms.py` line 80: `OUT = Path("./eval-disp-egms")`); manifest currently lists `eval-disp_egms` (with underscore — line 63 of `results/matrix_manifest.yml`). Plan-phase verifies and either fixes manifest or adds rename — RESEARCH.md line 50-52 flags this verification.
- Stable mask: same builder + same parameters as SoCal (Natural Earth coastlines + WorldCover class 60). Coastline buffer is irrelevant (~100 km from Bologna burst); water-body buffer applies (Po river + reservoirs). CONTEXT D-Claude's-Discretion confirms.
- 18 IFGs from 19-epoch S1A+S1B cross-constellation stack (vs 14 IFGs / 15 epochs at SoCal).

**EGMS L2a coherence — RESEARCH.md confirms:** Bologna's EGMS L2a CSV reference data is already cached for the existing `compare_disp_egms_l2a` callsite; no re-download required.

---

### `CONCLUSIONS_DISP_N_AM.md` + `CONCLUSIONS_DISP_EU.md` (post-rename) (docs, append-only)

**Analog:** `CONCLUSIONS_RTC_EU.md` (298 LOC, 2026-04-23) — the reference template for multi-section CONCLUSIONS with Calibration Framing + Investigation discipline + Attribution table.

**Files to read first:**
- `/Volumes/Geospatial/Geospatial/subsideo/CONCLUSIONS_RTC_EU.md` (entire — 298 LOC) — Phase 2 multi-section pattern
- `/Volumes/Geospatial/Geospatial/subsideo/CONCLUSIONS_DISP_N_AM.md` (entire — 258 LOC) — v1.0 baseline preserved as preamble per D-13
- `/Volumes/Geospatial/Geospatial/subsideo/CONCLUSIONS_DISP_EGMS.md` (entire — 304 LOC) — v1.0 baseline preserved as preamble per D-13

**Existing multi-section CONCLUSIONS shape** (`CONCLUSIONS_RTC_EU.md` lines 1-30):
```markdown
# EU RTC-S1 Validation -- Session Conclusions

**Date:** 2026-04-23
**Phase:** v1.1 Phase 2 -- RTC-S1 EU Validation
**Bursts:** 5 bursts across 5 terrain regimes
**Result:** MIXED (3/5 PASS, 2/5 FAIL with investigation)

> This document mirrors the structure of `CONCLUSIONS_RTC_N_AM.md` (v1.0 reference). The §5a "Terrain-Regime Coverage Table" and §5b "Investigation Findings" sections are Phase 2 additions required by RTC-01 + RTC-03. Plan 02-05 (post-eval-run) populated all concrete values below from `eval-rtc-eu/metrics.json` and `eval-rtc-eu/meta.json`.

---

## 1. Objective
...
```

**Existing investigation section pattern** (`CONCLUSIONS_RTC_EU.md` §5b — multi-burst per-FAIL-row "Top hypotheses" + "Evidence" sub-sections, lines 220-256):
```markdown
##### 5b.1 Burst `t066_140413_iw1` -- Alpine

**Observation.** RMSE **1.152 dB** (N.Am. baseline 0.045 dB — **25.6× drift**), r **0.9754** ...

**Top hypotheses** (per D-14 for Alpine):

1. **Steep-relief DEM artefact.** ...
2. **SAFE/orbit mismatch.** ...
3. **OPERA reference version drift.** ...

**Evidence** (to populate):
- Hypothesis 1: ...
- Hypothesis 2: ...
- Hypothesis 3: ...
```

**Phase 4 v1.1 sections (per CONTEXT D-13):** Both `CONCLUSIONS_DISP_N_AM.md` and `CONCLUSIONS_DISP_EU.md` keep v1.0 narrative as a "v1.0 baseline" leading section, then append four new v1.1 sections:
1. **Product Quality** — self-consistency CALIBRATING numbers (coherence + residual sub-section)
2. **Reference Agreement** — block_mean adapter r/bias/RMSE numbers (with v1.0 ad-hoc-bilinear comparison cited)
3. **Ramp Attribution** — per-IFG table + aggregate + auto-attribute label + human review note
4. **Link to `DISP_UNWRAPPER_SELECTION_BRIEF.md`**

**v1.0 numbers continuity (CONTEXT D-Claude's-Discretion plan-phase prose decision):**
- N.Am.: r=0.0365 / bias=+23.62 mm/yr (`CONCLUSIONS_DISP_N_AM.md` original §6 — preserve verbatim)
- EU: r=0.32 / bias=+3.35 mm/yr / RMSE 5.14 mm/yr (`CONCLUSIONS_DISP_EGMS.md` original §1)

Plan-phase decides whether v1.0 numbers go in a separate "v1.0 baseline (Resampling.bilinear)" sub-section or as an inline footnote in the v1.1 Reference Agreement section. RESEARCH.md doesn't prescribe — both are valid.

**Existing "Why the Result Is (Partially) Correct" framing** (`CONCLUSIONS_RTC_EU.md` lines 258-267):
This pattern is the framing for Phase 4 closing prose. The DISP cells will close with: "The FAIL is structurally correct — it documents PHASS unwrapper limitation, not a subsideo-layer bug. Phase 4 D-09 + D-10 + D-11 + D-12 give the named upgrade path via `DISP_UNWRAPPER_SELECTION_BRIEF.md` per FEATURES line 67-76."

---

### `docs/validation_methodology.md` (docs, append-only)

**Analog:** Existing §1 (CSLC cross-version impossibility, lines 17-129) + §2 (Product-quality vs reference-agreement distinction, lines 133-247) — Phase 3 wrote both.

**Files to read first:**
- `/Volumes/Geospatial/Geospatial/subsideo/docs/validation_methodology.md` (entire — 247 LOC) for §1 + §2 pattern
- `/Volumes/Geospatial/Geospatial/subsideo/.planning/research/PITFALLS.md` §P3.1 (lines 391-417) and §P3.2 (lines 422-448) for the source material Phase 4 §3 consolidates

**Existing append-only convention** (`docs/validation_methodology.md` lines 1-15):
```markdown
# Validation Methodology

**Scope:** Consolidates cross-cutting validation-methodology findings that span
multiple phases and products. Updated append-only per phase — Phase 3 writes
section 1 + section 2; Phase 4 will append the DISP ramp-attribution section;
Phases 5/6 will append the DSWE F1 ceiling and cross-sensor precision-first
sections; Phase 7 REL-03 will write the top-level table of contents and the
final cross-section consistency pass.

> This document is for us-future-selves and external contributors. The policy
> statements here close specific "wasted re-attempt" anti-patterns the team has
> already hit once (see `.planning/research/PITFALLS.md` §P2.4 and §M1–M6 for
> the underlying source material).

---

## 1. CSLC cross-version phase impossibility
```

**Existing section structure pattern** (§1 lines 17-129 — TL;DR + Structural argument + Policy statement + Diagnostic Evidence Appendix + Acceptable strategies):
```markdown
## 1. CSLC cross-version phase impossibility

<a name="cross-version-phase"></a>

**TL;DR:** Interferometric phase comparison ...

### 1.1 Structural argument — the SLC interpolation kernel changed
...

### 1.2 Policy statement
**Do NOT re-attempt with additional corrections.** ...

### 1.3 Diagnostic Evidence (Appendix)
...

### 1.4 Acceptable cross-version validation strategies
1. **Amplitude-based single-scene comparison** ...
2. **Self-consistency validation on our own chain** ...
3. **Time-series scientific equivalence** ...
```

**Phase 4 §3 structure (per CONTEXT D-03 — 5-part):**
```markdown
## 3. DISP comparison-adapter design — multilook method choice

**TL;DR:** Phase 4 ships ...

### 3.1 Problem statement
5×10 m → 30 m or PS-point-sampling required for reference comparison ...

### 3.2 PITFALLS P3.1 argument (Gaussian σ=0.5×ref physically consistent)
...

### 3.3 FEATURES anti-feature argument (block_mean conservative)
...

### 3.4 Decision: block_mean as eval-script default
...

### 3.5 Constraint: kernel must NOT be tuned to the resulting r/bias
...
```

**Cross-section reference table pattern** (`docs/validation_methodology.md` lines 234-241 — §2.6):
```markdown
| Distinction aspect | Future section (deferred per D-15) |
|--------------------|-----|
| DISP ramp-attribution (reference-agreement diagnostic depth) | Phase 4 will append (PHASS N.Am./EU re-runs as authoritative evidence) |
| DSWE F1 ≈ 0.92 architectural ceiling (product-quality interpretation) | Phase 5 or 6 will append ... |
```

Phase 4's §3 may add an analogous forward-looking pointer to §4 (DSWE F1 ceiling — Phase 5/6) and §5 (cross-sensor precision-first — Phase 5).

---

### `results/matrix_manifest.yml` (config, parse-only)

**Analog:** Existing `disp:eu` cell entry at line 60-66 of the manifest — already references `CONCLUSIONS_DISP_EU.md`.

**Files to read first:**
- `/Volumes/Geospatial/Geospatial/subsideo/results/matrix_manifest.yml` (entire — 98 LOC)

**Existing entry** (lines 60-66):
```yaml
- product: disp
  region: eu
  eval_script: run_eval_disp_egms.py
  cache_dir: eval-disp_egms
  metrics_file: eval-disp_egms/metrics.json
  meta_file: eval-disp_egms/meta.json
  conclusions_doc: CONCLUSIONS_DISP_EU.md
```

**Phase 4 verification:**
- `conclusions_doc: CONCLUSIONS_DISP_EU.md` is already correct — D-13's note that the manifest "needs the conclusions_doc field updated" is technically already satisfied; the actual change is the file rename via `git mv`.
- `cache_dir: eval-disp_egms` (with underscore) does NOT match the on-disk `eval-disp-egms/` (with hyphen — see `run_eval_disp_egms.py` line 80). RESEARCH.md line 50-52 flags this for plan-phase to either fix manifest or rename directory. Recommendation: align manifest to on-disk (lower-cost change; one YAML edit vs filesystem rename + .gitignore update).

---

### `CONCLUSIONS_DISP_EGMS.md` → `CONCLUSIONS_DISP_EU.md` (rename)

**Analog:** None (file rename via `git mv`); no code pattern.

**Pattern:**
```bash
git mv CONCLUSIONS_DISP_EGMS.md CONCLUSIONS_DISP_EU.md
```

**Sequencing:** rename FIRST (commit), then append v1.1 sections to the renamed file (separate commit) so the rename is preserved cleanly in `git log --follow`.

---

### `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md` (new)

**Analog:** `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` (Phase 2, 67 LOC) and `.planning/milestones/v1.1-research/cslc_selfconsist_aoi_candidates.md` (Phase 3, 253 LOC).

**Files to read first:**
- `/Volumes/Geospatial/Geospatial/subsideo/.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` (67 LOC) — minimal probe-artifact-style template
- `/Volumes/Geospatial/Geospatial/subsideo/.planning/milestones/v1.1-research/cslc_selfconsist_aoi_candidates.md` (253 LOC) — denser candidate-evaluation template

**Existing v1.1-research/ artefact convention** (`rtc_eu_burst_candidates.md` lines 1-32):
```markdown
# RTC-S1 EU Burst Candidates -- Probe Report

**Probed:** 2026-04-23T15:40:02Z
**Source query:** `asf_search` + `earthaccess` against ASF DAAC.
**Phase:** 2 (RTC-S1 EU Validation)
**Decision:** D-01 (probe artifact) + D-03 (5-regime fixed list) + D-04 (Claude drafts; user reviews).

## Regime Coverage
| # | regime | label | centroid_lat | ... | best_match_granule | cached_safe | burst_id (fill-in) |
|---|--------|-------|--------------|-----|--------------------|-------------|---------------------|
| 1 | Alpine | Swiss/Italian Alps | 46.35 | ... | `S1A_IW_SLC__1SDV_20240502T053520_..._SLC` | (none) | (derive ...) |
...

## Constraints Audit
- ...

## Plan 02-05 Task 1 Follow-up -- Burst IDs Derived from OPERA L2 RTC Catalog (2026-04-23)
...

## Query reproducibility
...
```

**Phase 4 brief structure (per CONTEXT D-15 — 4 candidates × 4 columns):**
```markdown
# DISP Unwrapper Selection Brief

**Drafted:** 2026-04-25
**Phase:** 4 close (DISP Comparison Adapter + Honest FAIL)
**Decision:** D-13 + D-14 + D-15 + D-16 (Brief lives at `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md`; committed at Phase 4 close).

## Context
As of 2026-04-25, the v1.1 DISP cells (SoCal + Bologna) FAIL the BINDING reference-agreement gate (`disp.correlation_min=0.92`, `disp.bias_mm_yr_max=3.0`) ...

## Candidate Evaluation

| # | Candidate | Description | Success Criterion | Compute Tier | Dep Delta |
|---|-----------|-------------|--------------------|--------------|-----------|
| 1 | PHASS+deramping | ... | r > 0.5 OR ramp_magnitude_rad < 1.0 | S (post-process only) | (none — uses existing dolphin output) |
| 2 | SPURT native | ... | r > 0.6 | M (re-unwrap from cached IFGs) | (spurt added to conda-env.yml) |
| 3 | tophu-SNAPHU tiled | ... | r > 0.7 | M (re-unwrap from cached IFGs) | (tophu/snaphu already conda-forge — config switch) |
| 4 | 20×20 m fallback | ... | r > 0.6 | L (re-unwrap from cached CSLCs) | (none — multilook config change) |

## Per-candidate notes
### 1. PHASS+deramping
...
### 2. SPURT native
...

## Open questions (for the v1.2 milestone roadmapper)
...
```

CONTEXT D-15 is explicit on the 4-candidate frame (NOT 5): NO MintPy SBAS as 5th candidate. CONTEXT D-14 ties success criteria to v1.1 numbers (e.g. "PHASS+deramping target: r > 0.5 OR ramp_magnitude_rad < 1.0 — current Bologna r=0.32 / ramp 5.5 rad").

**Brief publication date stamp** (CONTEXT D-Claude's-Discretion): "as of 2026-04-XX, current FAIL state is..."

---

### Test files (likely new — plan-phase decides)

**Analog:** Existing `tests/unit/test_*.py` patterns (plan-phase will inspect specific tests in scope).

**`tests/unit/test_compare_disp.py` (new)** — `prepare_for_reference` 4 methods × 3 input forms = 12 cases on synthetic 100×100 raster. Validation:
- Method dispatch raises `ValueError` on `method=None` (D-04)
- Method dispatch raises `ValueError` on unknown method
- Each form (Path / xr.DataArray / ReferenceGridSpec) returns the expected shape
- Each method preserves nan/zero handling

**`tests/unit/test_selfconsistency.py` (extend)** — synthetic-ramp recovery tests:
- Build 100×100 synthetic `z = 0.05*x + 0.03*y + noise` and assert `fit_planar_ramp` recovers `slope_x ≈ 0.05`, `slope_y ≈ 0.03` within tolerance
- Test NaN/zero exclusion via `keep.sum() < 100` returns NaN-filled outputs
- `auto_attribute_ramp` 4-branch table: (sigma=10, r=0.1) → 'orbit', (sigma=50, r=0.7) → 'phass', (sigma=10, r=0.7) → 'mixed', (sigma=50, r=0.1) → 'inconclusive'

**`tests/unit/test_matrix_schema.py` (extend)** — `DISPCellMetrics` Pydantic round-trip:
- `model_dump_json()` → `model_validate_json()` preserves all fields
- `extra="forbid"` rejects unknown keys
- `coherence_source` rejects values outside `Literal['phase3-cached', 'fresh']`
- `attributed_source` rejects values outside `Literal['phass', 'orbit', 'tropospheric', 'mixed', 'inconclusive']`

**`tests/unit/test_matrix_writer.py` (extend)** — disp:nam + disp:eu render branch outputs:
- Synthetic `DISPCellMetrics` JSON with both `region='nam'` and `region='eu'` produces correct `(pq_col, ra_col)` tuples
- `_is_disp_cell_shape` returns True on `ramp_attribution`-keyed JSON, False on `per_aoi`-keyed JSON
- Dispatch order: a JSON with both `ramp_attribution` and `per_aoi` keys (defensive case) routes to DISP branch

**Test invocation** (per CLAUDE.md):
```bash
micromamba run -n subsideo pytest tests/unit/test_compare_disp.py -v
micromamba run -n subsideo pytest tests/unit/test_selfconsistency.py -v
```

Tests are NOT marked `@pytest.mark.integration` or `@pytest.mark.validation` — they are pure-numpy synthetic-input unit tests (per CLAUDE.md test-marker discipline).

---

## Shared Patterns

### Pure-Function Pydantic v2 Schema Convention (Phase 1 D-09)
**Source:** `src/subsideo/validation/matrix_schema.py` (lines 1-26)
**Apply to:** `matrix_schema.py` additions (`PerIFGRamp`, `RampAggregate`, `RampAttribution`, `DISPProductQualityResultJson`, `DISPCellMetrics`).

```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class MyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")  # MANDATORY on every class
    field_name: type = Field(..., description="...")  # description MANDATORY
```

### Lazy Imports for Conda-Forge Deps (Phase 1 D-Claude's-Discretion)
**Source:** `src/subsideo/validation/selfconsistency.py` line 241 (`import h5py  # lazy`)
**Apply to:** `compare_disp.py` (`scipy.ndimage.gaussian_filter` for the gaussian method-branch — lazy-import inside `_resample_onto_path` body, not at module top), `selfconsistency.py` (`scipy.stats.circstd` for `compute_ramp_aggregate` — lazy-import inside function body per RESEARCH.md line 661).

```python
def my_function(...):
    import h5py  # lazy per PATTERNS "Two-layer install + lazy imports"
    # ... use h5py ...
```

### CALIBRATING Italics + Warning Glyph (Phase 1 D-03 / GATE-03)
**Source:** `src/subsideo/validation/matrix_writer.py` lines 343-348
**Apply to:** `_render_disp_cell` — italicise PQ side (CALIBRATING) but NOT RA side (BINDING).

```python
warn = " ⚠" if metrics.any_blocker else ""  # U+26A0 escape, not literal glyph
pq_col = f"*{pq_body}*{warn}"  # CALIBRATING italics
ra_col = f"*{ra_body}*" if ra_body != "—" else "—"
```

### `from __future__ import annotations` First Non-Docstring Line
**Source:** Every `src/subsideo/validation/*.py` file (PATTERNS §4.2)
**Apply to:** Every modified Python file in Phase 4.

```python
"""Module docstring."""
from __future__ import annotations
# ... rest of imports
```

### Module-Level EXPECTED_WALL_S Constant (Phase 1 D-11)
**Source:** `run_eval_disp.py` line 19, `run_eval_cslc_selfconsist_nam.py` line 44
**Apply to:** Both Phase 4 eval scripts.

```python
EXPECTED_WALL_S = 60 * 60 * 6   # Plan supervisor AST-parses this constant
```

### Module-Level REFERENCE_MULTILOOK_METHOD Constant (Phase 4 D-04)
**Source:** New per CONTEXT D-04 (mirrors EXPECTED_WALL_S — auditable in git diff)
**Apply to:** Both Phase 4 eval scripts.

```python
REFERENCE_MULTILOOK_METHOD: Literal["block_mean"] = "block_mean"
```

### `if __name__ == "__main__":` + `credential_preflight` First (Phase 1 harness shape)
**Source:** `run_eval_disp.py` lines 21-53, `run_eval_cslc_selfconsist_nam.py` lines 47-101
**Apply to:** Both Phase 4 eval scripts.

```python
if __name__ == "__main__":
    # imports first
    from dotenv import load_dotenv
    from subsideo.validation.harness import credential_preflight, ...

    load_dotenv()
    credential_preflight([
        "CDSE_CLIENT_ID", "CDSE_CLIENT_SECRET",
        "EARTHDATA_USERNAME", "EARTHDATA_PASSWORD",
    ])
    # ... staged pipeline ...
```

### Per-Stage `ensure_resume_safe` Gate
**Source:** Both eval scripts use this throughout (Phase 1 D-Claude's-Discretion harness helper)
**Apply to:** Phase 4 — re-runs are warm by definition with cached CSLCs; new Stage 10 / 11 / 12 should also gate on prior outputs to allow incremental re-runs.

### Aggregate metrics.json + Nested Sub-Results (Phase 2 D-09 / D-10, Phase 3 D-06)
**Source:** `src/subsideo/validation/matrix_schema.py` `MetricsJson` + extension subclasses
**Apply to:** `DISPCellMetrics` adds `ramp_attribution` as a 3rd top-level sub-aggregate alongside the inherited `product_quality` + `reference_agreement` (per CONTEXT line 192).

### Cell-Level meta.json with Input Hashes (Phase 2 D-12)
**Source:** `run_eval_cslc_selfconsist_nam.py` lines 1227-1244
**Apply to:** Both Phase 4 eval scripts — input_hashes dict over: CSLC stack hash, OPERA DISP-S1 reference hashes (N.Am. only), EGMS L2a CSV hashes (EU only), dolphin velocity.tif hash, dolphin internal-coherence-layer hash if read.

### Loguru `{}` Format-String Convention
**Source:** `selfconsistency.py` line 71, 111-121, `matrix_writer.py` lines 286-288
**Apply to:** All `loguru.logger` calls in new code.

```python
logger.warning("coherence_stats called with empty stable_mask -- returning zeros")
logger.debug(
    "coherence_stats: n_stable={}, mean={:.3f}, ...",
    int(stable_mask.sum()),
    stats["mean"],
    ...
)
```

---

## No Analog Found

No file in Phase 4 lacks a clear codebase analog. Two near-misses worth flagging:

| File / Operation | Notes |
|------------------|-------|
| Cross-cell read of `eval-cslc-selfconsist-nam/metrics.json` from `run_eval_disp.py` | No prior cross-cell read in v1.1 codebase. Pattern is straightforward: `Path(...).exists()` + `CSLCSelfConsistNAMCellMetrics.model_validate_json(...)` + drill into `metrics.per_aoi[idx_socal]`. Plan-phase resolves: which AOI index is SoCal (probably 0 — first entry in `AOIS` list per `run_eval_cslc_selfconsist_nam.py` declarative order). |
| `_render_disp_cell` schema discriminator order | DISP branch must check BEFORE `_is_cslc_selfconsist_shape` AND `_is_rtc_eu_shape` (per RESEARCH.md line 593-598). The schemas are structurally disjoint — invariant, not a guess — but the dispatch order matters. |

---

## Metadata

**Analog search scope:**
- `/Volumes/Geospatial/Geospatial/subsideo/src/subsideo/validation/` (compare_disp.py, selfconsistency.py, matrix_schema.py, matrix_writer.py, harness.py, criteria.py)
- `/Volumes/Geospatial/Geospatial/subsideo/run_eval_*.py` (cslc, disp, disp_egms, cslc_selfconsist_nam, cslc_selfconsist_eu)
- `/Volumes/Geospatial/Geospatial/subsideo/CONCLUSIONS_*.md` (RTC_EU, DISP_N_AM, DISP_EGMS)
- `/Volumes/Geospatial/Geospatial/subsideo/.planning/milestones/v1.1-research/` (rtc_eu_burst_candidates.md, cslc_selfconsist_aoi_candidates.md)
- `/Volumes/Geospatial/Geospatial/subsideo/docs/validation_methodology.md`
- `/Volumes/Geospatial/Geospatial/subsideo/results/matrix_manifest.yml`

**Files scanned:** 12 source/script files + 5 docs/config files = 17 files

**Pattern extraction date:** 2026-04-25

## PATTERN MAPPING COMPLETE
