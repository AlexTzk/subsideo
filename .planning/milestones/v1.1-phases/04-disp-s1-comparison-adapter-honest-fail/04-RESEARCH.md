# Phase 4: DISP-S1 Comparison Adapter + Honest FAIL — Research

**Researched:** 2026-04-25
**Domain:** InSAR validation infrastructure (multilook adapter + ramp-attribution diagnostic + honest-FAIL reporting)
**Confidence:** HIGH

---

## Summary

Phase 4 ships **validation-only** infrastructure on top of an **unchanged** dolphin/PHASS pipeline. Three artifacts: (1) `prepare_for_reference()` adapter in `compare_disp.py` with explicit `method=` over a 4-element Literal and a 3-form `reference_grid` union; (2) per-IFG planar-ramp fitter `fit_planar_ramp()` in `selfconsistency.py` plus a `RampAttribution` schema extension to `metrics.json`; (3) a one-page `DISP_UNWRAPPER_SELECTION_BRIEF.md` handoff and v1.1 sub-section appends to `CONCLUSIONS_DISP_N_AM.md` + a renamed `CONCLUSIONS_DISP_EU.md`, plus a `docs/validation_methodology.md` §3 ADR sub-section.

The two re-runs (SoCal + Bologna) consume already-cached CSLCs from `eval-disp/` and `eval-disp-egms/`; **no SAFE re-downloads, no run_cslc invocations, no run_disp invocations** in the warm path. A cold full-pipeline run from CSLCs is also possible if either cache is invalidated. All ramp-fit input rasters (39 unwrapped IFGs per cell) are already on disk under `eval-disp/disp/dolphin/unwrapped/` and `eval-disp-egms/disp/dolphin/unwrapped/`. The dolphin `velocity.tif` rasters exist at `eval-disp/disp/dolphin/timeseries/velocity.tif` (22 MB) and `eval-disp-egms/disp/dolphin/timeseries/velocity.tif` (104 MB).

**Primary recommendation:** Land the 5 file-touch changes per script (adapter call, product-quality block with cross-cell read, ramp-attribution block, schema upgrade, REFERENCE_MULTILOOK_METHOD constant) plus 4 module additions (`prepare_for_reference`, `fit_planar_ramp`, `DISPCellMetrics` + `RampAttribution` + `PerIFGRamp` Pydantic types, two `matrix_writer` render branches) in 4–5 plans. The ~30-min warm re-run per cell + ~5-s ramp fit + ~12-min coherence re-compute per fresh cell makes this a code-volume problem, not a compute problem.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Multilook method ADR:**
- **D-01:** `prepare_for_reference(..., method=...)` accepts `Literal["gaussian", "block_mean", "bilinear", "nearest"]`. Adapter validates `method` against the Literal at call time; refuses `None`/missing per DISP-01 explicit-no-default. No default value at signature level.
- **D-02:** Phase 4 eval scripts pass `method="block_mean"` explicitly. Conservative; matches OPERA's own multilook; minimises kernel-flattery attack surface.
- **D-03:** `docs/validation_methodology.md` §3 contains the ADR sub-section "DISP comparison-adapter design — multilook method choice" (5-part structure: problem → PITFALLS arg → FEATURES arg → decision → constraint).
- **D-04:** Module-level `REFERENCE_MULTILOOK_METHOD: Literal["block_mean"] = "block_mean"` constant + adapter raise-on-missing. Mirrors Phase 1 D-11 EXPECTED_WALL_S pattern.

**DISP self-consistency methodology:**
- **D-05:** Mixed source — coherence from cached CSLC stack via Phase 3 `coherence_stats`; residual from dolphin's `velocity.tif` via `residual_mean_velocity` with `frame_anchor='median'`. Gate stat = `median_of_persistent` (Phase 3 D-01).
- **D-06:** Stable mask = same builder + same parameters as Phase 3 SoCal: `build_stable_mask(worldcover, slope_deg, coastline, waterbodies, coast_buffer_m=5000, water_buffer_m=500, slope_max_deg=10)`.
- **D-07:** Coherence input = sequential 12-day IFGs from CSLC stack via boxcar 5×5 (Phase 3 convention). SoCal: 14 IFGs from 15-epoch stack. Bologna: 18 IFGs from 19-epoch S1A+S1B cross-constellation stack.
- **D-08:** SoCal coherence sub-result reused via cross-cell read from `eval-cslc-selfconsist-nam/metrics.json["per_aoi"][SoCal]["product_quality"]`. Provenance flag in DISP-N.Am. metrics.json: `coherence_source: 'phase3-cached'`. Residual always fresh from dolphin output. Bologna gets fresh coherence + fresh residual (`coherence_source: 'fresh'`).

**Ramp-attribution diagnostic:**
- **D-09:** Diagnostic (a) per-IFG ramp fit always-on; (b) POEORB swap + (c) ERA5 toggle deferred (no-op-on-current-stacks for (b); ERA5 not configured for (c)). Both documented as "available; not run because…".
- **D-10:** New helper `fit_planar_ramp(ifgrams_stack, mask)` in `selfconsistency.py` returning `dict[str, np.ndarray]` per IFG (`ramp_magnitude_rad`, `ramp_direction_deg`, `slope_x`, `slope_y`, `intercept_rad`).
- **D-11:** `metrics.json` `ramp_attribution: {per_ifg, aggregate, attributed_source, attribution_note}`. New Pydantic v2 models `DISPCellMetrics` + `RampAttribution` + `PerIFGRamp` extend `MetricsJson`.
- **D-12:** Auto-attribute via deterministic rule + human review note in CONCLUSIONS prose. Literal includes 'phass', 'orbit', 'tropospheric', 'mixed', 'inconclusive'.

**Brief + CONCLUSIONS shape:**
- **D-13:** CONCLUSIONS update = append v1.1 sections + rename `CONCLUSIONS_DISP_EGMS.md` → `CONCLUSIONS_DISP_EU.md`. Both files keep v1.0 narrative as preamble; append four new v1.1 sections per cell (Product Quality / Reference Agreement / Ramp Attribution / Link to brief).
- **D-14:** Brief cites BOTH v1.1 reference-agreement numbers + ramp-attribution aggregate. Drives candidate prioritisation per attribution label.
- **D-15:** Brief = 4 candidates × (description, success criterion, compute tier, dep delta). One markdown page (~150–250 LOC). Candidates: PHASS+deramping, SPURT native, tophu-SNAPHU tiled, 20×20 m fallback. NO MintPy SBAS as 5th.
- **D-16:** Brief lives at `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md`; committed at Phase 4 close.

**Cross-cutting (carry-forwards):**
- **D-17:** Native 5×10 m stays production default. `run_disp()` unchanged. `prepare_for_reference` is validation-only.
- **D-18:** `prepare_for_reference` lives in `compare_disp.py`, NOT new `validation/adapters.py`.
- **D-19:** First-rollout = CALIBRATING cell rendering for `disp.selfconsistency.*`. Cell-level status = MIXED (CALIBRATING product_quality + FAIL reference_agreement is the expected outcome).
- **D-20:** No pipeline algorithm changes. Re-runs use cached CSLCs + existing `run_disp()`. No `products/disp.py` edits.
- **D-21:** Manifest already wires the cells. `disp:nam` → `eval-disp/`, `disp:eu` → `eval-disp_egms/` (note: actual directory on disk is `eval-disp-egms/` with hyphen — manifest entry needs verification in plan-phase or filesystem rename).

### Claude's Discretion

- Exact `fit_planar_ramp` algorithm: full-burst least-squares plane fit on finite-non-zero pixels in image coordinates; magnitude in rad (peak-to-peak across burst), direction in degrees from East.
- Auto-attribute rule cutoffs: `direction_stability_sigma_deg < 30°` → 'orbit'; `magnitude_vs_coherence_pearson_r > 0.5` → 'phass'; both → 'mixed'; neither → 'inconclusive'. Cutoffs are NOT criteria.py entries.
- `EXPECTED_WALL_S = 60 * 60 * 6` (21600 s; 6 h cap covers warm ~30 min + cold ~3 h + safety margin).
- `DISPCellMetrics` Pydantic v2 schema: extends `MetricsJson` base; one class for both DISP cells (SoCal + Bologna share schema).
- Bologna stable-mask data sources: Natural Earth coastlines + WorldCover class 60 (same as Phase 3 SoCal); revisit only if buffer exclusion is too coarse.
- Whether to render the `bilinear` v1.0 numbers in CONCLUSIONS for continuity — D-13 says "v1.0 numbers cited"; exact framing (sub-section vs footnote) is plan-phase prose decision.
- Brief publication date stamp: introductory paragraph notes "as of `<date>`, current FAIL state is…".

### Deferred Ideas (OUT OF SCOPE)

- ERA5 tropospheric correction integration (DISP-V2-02; folded into Unwrapper Selection follow-up as secondary)
- POEORB swap automation when RESORB epochs are present (D-09 + D-Claude's-Discretion: opportunistic-only; current windows are all-POEORB)
- Gaussian-kernel re-run for kernel-comparison study (`prepare_for_reference(method="gaussian")` — follow-up-milestone scope)
- Promotion of `prepare_for_reference` to `validation/adapters.py` (D-18 promotion rule: 2nd-product trigger)
- `fit_planar_ramp` returning per-IFG residual rasters (disk footprint reasoning; v2 if downstream wants residual rasters)
- DISP self-consistency on dolphin's coherence layer (Q3-rejected; couples validation to product)
- MintPy SBAS as 5th brief candidate (D-15-rejected; intentional 4-candidate framing)
- Full ADR sub-document at `docs/adr/004-multilook-method.md` (D-03-rejected)
- Brief stored in `v1.2-disp-unwrapper-selection/` directory (D-16-rejected; v1.2 not yet roadmapped)
- Per-cell `EXPECTED_WALL_S` tuning (6 h cap as starting point)
- Bologna stable-mask via OSM coastlines (Natural Earth default)

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **DISP-01** | `prepare_for_reference(native_velocity, reference_grid, method=...)` adapter; `method=` no default; 3-form `reference_grid`; never writes back to product | §"Architecture / prepare_for_reference signature" + §"Library APIs / rasterio.warp.reproject" |
| **DISP-02** | DISP self-consistency product-quality gate (coherence > 0.7, residual < 5 mm/yr) at native 5×10 m for SoCal + Bologna from cached CSLC stacks | §"Code Shape / selfconsistency.py" + §"Cross-cell read" + §"Library APIs / Reading dolphin velocity.tif" |
| **DISP-03** | N.Am. + EU re-runs report reference-agreement separately from product-quality; planar-ramp labelled by attributed source via diagnostic | §"Architecture / fit_planar_ramp" + §"DISPCellMetrics + RampAttribution" + §"Auto-attribute rule" |
| **DISP-04** | One-page DISP Unwrapper Selection brief: PHASS+deramping / SPURT native / tophu-SNAPHU tiled / 20×20 m fallback × success criterion | §"Brief structure (4 candidates × 4 columns)" |
| **DISP-05** | Native 5×10 m stays production default; downsampling lives exclusively in `prepare_for_reference`; documented as validation-only in code + methodology doc | §"§3 ADR doc-section" + module docstring update |

---

## Project Constraints (from CLAUDE.md)

- **Python invocation:** `micromamba run -n subsideo python <command>` always
- **Conda-forge only:** isce3, GDAL, dolphin, tophu, snaphu — never `pip install`. (Phase 4 uses none of these directly; no risk.)
- **CDSE / Earthdata creds:** required by EU + N.Am. eval scripts for SAFE/reference download (warm path skips entirely; cold path needs them)
- **CDS API key:** `~/.cdsapirc` checked at script top; ERA5 not actually used (D-09 deferral)
- **EU burst DB:** `t117_249422_iw2` (Bologna) is in `subsideo.burst.db` — `bounds_for_burst` falls through to it
- **Output spec compliance:** velocity.tif units rad/yr (LOS phase rate per dolphin convention) — Phase 4 reads it, doesn't write it
- **`results/matrix.md` writer:** never globs CONCLUSIONS_*.md (PITFALLS R3/R5)
- **Test markers:** `@pytest.mark.validation` for full-pipeline runs; `@pytest.mark.integration` for live network; Phase 4 unit tests are neither

---

## Architecture (HOW)

### prepare_for_reference signature + 3-form reference_grid

**Add to `src/subsideo/validation/compare_disp.py` as new top-level function** (per ARCHITECTURE §3 — extend, do NOT create `adapters.py`):

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import rasterio
import xarray as xr
from rasterio.warp import Resampling, reproject

# Existing module imports already present
from subsideo.validation.results import ProductQualityResult, ReferenceAgreementResult


@dataclass(frozen=True)
class ReferenceGridSpec:
    """Reference-grid specification for point-sampling form (DISP-01 form c).

    Used when no raster reference exists -- e.g. EGMS L2a PS point cloud.
    The adapter samples the native velocity at each (lon, lat) coordinate
    rather than reprojecting onto a raster grid.
    """
    points_lonlat: np.ndarray  # (N, 2) array of (lon, lat) in EPSG:4326
    crs: str = "EPSG:4326"     # CRS the points are expressed in
    point_ids: list[str] | None = None  # optional PS IDs for traceability


MultilookMethod = Literal["gaussian", "block_mean", "bilinear", "nearest"]


def prepare_for_reference(
    native_velocity: Path | xr.DataArray,
    reference_grid: Path | xr.DataArray | ReferenceGridSpec,
    *,
    method: MultilookMethod | None = None,
) -> np.ndarray | xr.DataArray:
    """Multilook subsideo's native 5x10 m DISP velocity to a reference grid.

    Validation-only. Never writes back to the product (DISP-05 + research
    ARCHITECTURE Sec 3 + FEATURES anti-feature).

    Parameters
    ----------
    native_velocity
        Path to the native-resolution velocity GeoTIFF (rad/yr LOS, dolphin
        convention) OR an xr.DataArray with CRS attached via rioxarray.
    reference_grid
        One of three forms (DISP-01):
        (a) Path to a GeoTIFF -- adapter reads CRS + transform + shape via
            rasterio and reprojects native onto the file's grid.
        (b) xr.DataArray with CRS encoded via rioxarray -- adapter
            reprojects native onto the array's grid.
        (c) ReferenceGridSpec -- adapter point-samples the native raster at
            each (lon, lat) coordinate, returning a 1-D ndarray in PS-row
            order (no reprojection).
    method
        REQUIRED. One of {"gaussian", "block_mean", "bilinear", "nearest"}.
        No default value (DISP-01 explicit-no-default). Raises ValueError
        if None or anything outside the Literal.

    Returns
    -------
    np.ndarray | xr.DataArray
        Form (a)/(b): velocity on reference grid as np.ndarray (matches
        existing compare_disp() pattern) OR xr.DataArray with CRS attached
        when input was xr.DataArray (preserve type).
        Form (c): 1-D np.ndarray of sampled values, length == len(spec.points_lonlat).

    Raises
    ------
    ValueError
        If method is None, missing, or not in the Literal.
        If reference_grid form is unsupported.
    """
    if method is None:
        raise ValueError(
            "method= is required (DISP-01 explicit-no-default policy). "
            "Pick one of: 'gaussian', 'block_mean', 'bilinear', 'nearest'."
        )
    valid_methods = ("gaussian", "block_mean", "bilinear", "nearest")
    if method not in valid_methods:
        raise ValueError(
            f"method must be one of {valid_methods}; got {method!r}"
        )

    # Form discrimination
    if isinstance(reference_grid, ReferenceGridSpec):
        return _point_sample(native_velocity, reference_grid, method=method)
    if isinstance(reference_grid, (str, Path)):
        return _resample_onto_path(native_velocity, Path(reference_grid), method=method)
    if isinstance(reference_grid, xr.DataArray):
        return _resample_onto_dataarray(native_velocity, reference_grid, method=method)
    raise ValueError(
        f"reference_grid must be Path | xr.DataArray | ReferenceGridSpec; "
        f"got {type(reference_grid).__name__}"
    )
```

**Three internal helpers** (private to the module):
- `_resample_onto_path(native, ref_tiff_path, method)` — opens ref TIFF, extracts target transform/CRS/shape, dispatches to method-specific kernel
- `_resample_onto_dataarray(native, ref_da, method)` — uses `ref_da.rio.transform()` + `ref_da.rio.crs` + `ref_da.shape` (rioxarray)
- `_point_sample(native, spec, method)` — opens native raster; for each (lon, lat) reprojects to native CRS via `pyproj.Transformer.from_crs(spec.crs, native_crs, always_xy=True)`; uses `rasterio.DatasetReader.sample()` for nearest/bilinear, OR Gaussian-weighted sampling for gaussian, OR block-average around each point for block_mean

**Method dispatch (3 kernel implementations + 1 degenerate)** — see §"Library APIs" for concrete syntax.

**Adapter never writes:** all paths return arrays; the caller (`compare_disp()`, `compare_disp_egms_l2a()`, or eval scripts directly) consumes the result for metric computation.

### fit_planar_ramp algorithm

**Add to `src/subsideo/validation/selfconsistency.py` as new top-level function** (per D-10; module charter broadens to "Sequential-IFG self-consistency primitives"):

```python
def fit_planar_ramp(
    ifgrams_stack: np.ndarray,
    mask: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """Fit a planar phase ramp to each IFG in the stack via least squares.

    For each unwrapped IFG, fit z = a*x + b*y + c on finite-non-zero pixels
    in image (pixel-index) coordinates -- NOT UTM. Reports peak-to-peak
    magnitude across the burst extent, plus direction (degrees from East).

    Per CONTEXT D-Claude's-Discretion: full-burst (not stable-mask-only)
    least-squares plane fit because orbit/tropospheric/PHASS ramps span the
    burst -- masking to stable-only would clip them and bias direction.

    Parameters
    ----------
    ifgrams_stack : (N, H, W) float np.ndarray
        Unwrapped phase in radians per IFG. NaN and zero values are
        excluded from the fit (typical PHASS unwrapper convention: 0 outside
        valid data, NaN for masked-out pixels).
    mask : (H, W) bool np.ndarray | None
        Optional restriction to specific pixels -- not used by D-default.
        Passed through for callers who want stable-mask-only fits.

    Returns
    -------
    dict[str, np.ndarray]
        Per-IFG arrays of length N:
        - 'ramp_magnitude_rad' : peak-to-peak rad across the burst
        - 'ramp_direction_deg' : degrees from East (atan2(slope_y, slope_x) * 180/pi)
        - 'slope_x' : a (rad per pixel column)
        - 'slope_y' : b (rad per pixel row)
        - 'intercept_rad' : c

    Algorithm (per IFG):
        1. Build pixel-coordinate arrays X, Y from np.indices((H, W))
        2. Validity mask: np.isfinite(z) & (z != 0); intersect with caller mask
        3. Flatten and solve A @ [a, b, c] = z via np.linalg.lstsq:
           A = column_stack([X.flat[valid], Y.flat[valid], ones])
        4. Reconstruct plane on full burst grid: z_plane = a*X + b*Y + c
        5. peak-to-peak = z_plane.max() - z_plane.min()
           (over valid pixels; restrict to mask & finite)
        6. direction = atan2(b, a) * 180/pi (East = 0, North = 90)
    """
    import numpy as np  # already imported at module top

    if ifgrams_stack.ndim != 3:
        raise ValueError(
            f"ifgrams_stack must be 3-D (N, H, W); got shape {ifgrams_stack.shape}"
        )
    n_ifg, height, width = ifgrams_stack.shape
    Y, X = np.indices((height, width))
    X_flat = X.ravel().astype(np.float64)
    Y_flat = Y.ravel().astype(np.float64)

    out: dict[str, list[float]] = {
        "ramp_magnitude_rad": [],
        "ramp_direction_deg": [],
        "slope_x": [],
        "slope_y": [],
        "intercept_rad": [],
    }

    for k in range(n_ifg):
        z = ifgrams_stack[k].astype(np.float64)
        valid = np.isfinite(z) & (z != 0.0)
        if mask is not None:
            valid &= mask
        z_flat = z.ravel()
        keep = valid.ravel()

        if int(keep.sum()) < 100:
            # Insufficient pixels for a plane fit -- record NaNs
            out["ramp_magnitude_rad"].append(float("nan"))
            out["ramp_direction_deg"].append(float("nan"))
            out["slope_x"].append(float("nan"))
            out["slope_y"].append(float("nan"))
            out["intercept_rad"].append(float("nan"))
            continue

        A = np.column_stack([
            X_flat[keep],
            Y_flat[keep],
            np.ones(int(keep.sum()), dtype=np.float64),
        ])
        b_vec = z_flat[keep]
        coeffs, _, _, _ = np.linalg.lstsq(A, b_vec, rcond=None)
        a, b, c = float(coeffs[0]), float(coeffs[1]), float(coeffs[2])

        # Reconstruct plane on all valid pixels for peak-to-peak magnitude
        z_plane_flat = a * X_flat[keep] + b * Y_flat[keep] + c
        ramp_magnitude = float(z_plane_flat.max() - z_plane_flat.min())
        # Direction from East (atan2 returns radians in (-pi, pi])
        ramp_direction_deg = float(np.degrees(np.arctan2(b, a)))

        out["ramp_magnitude_rad"].append(ramp_magnitude)
        out["ramp_direction_deg"].append(ramp_direction_deg)
        out["slope_x"].append(a)
        out["slope_y"].append(b)
        out["intercept_rad"].append(c)

    return {k: np.asarray(v, dtype=np.float64) for k, v in out.items()}
```

**Note on direction convention:** `atan2(b, a)` with `a = slope_x` (rad/col) and `b = slope_y` (rad/row) gives East-from-positive-x in image coordinates. Image rows increase downward, so "ramp_direction_deg" of 90° in image-coords ≈ ramp pointing toward image-bottom (image y+); plan-phase prose can clarify whether that maps to map-North or map-South depending on raster origin (Affine convention). For the CONCLUSIONS narrative, treat direction as "in image coordinates, East = 0°" and document the orientation in a single doc-line.

### DISPCellMetrics + RampAttribution + PerIFGRamp Pydantic schema

**Add to `src/subsideo/validation/matrix_schema.py`** (additive only, no edits to existing types per Phase 1 D-09 big-bang lock-in):

```python
# --- Phase 4 DISP comparison-adapter cell metrics (CONTEXT D-11) ---

CoherenceSource = Literal["phase3-cached", "fresh"]
AttributedSource = Literal["phass", "orbit", "tropospheric", "mixed", "inconclusive"]
DISPCellStatus = Literal["PASS", "FAIL", "CALIBRATING", "MIXED", "BLOCKER"]


class PerIFGRamp(BaseModel):
    """One row in RampAttribution.per_ifg (Phase 4 D-11)."""

    model_config = ConfigDict(extra="forbid")

    ifg_idx: int = Field(..., ge=0, description="IFG index in the stack (0..N-1).")
    ref_date_iso: str = Field(
        ...,
        description="ISO-8601 date of the reference (earlier) epoch, e.g. '2024-01-08'.",
    )
    sec_date_iso: str = Field(
        ...,
        description="ISO-8601 date of the secondary (later) epoch.",
    )
    ramp_magnitude_rad: float = Field(
        ...,
        description=(
            "Peak-to-peak ramp magnitude in radians across the burst. NaN "
            "when fit_planar_ramp had insufficient valid pixels (<100)."
        ),
    )
    ramp_direction_deg: float = Field(
        ...,
        description=(
            "Ramp direction in degrees from East in image coordinates "
            "(atan2(slope_y, slope_x) * 180/pi). NaN when fit failed."
        ),
    )
    ifg_coherence_mean: float | None = Field(
        default=None,
        description=(
            "Mean coherence over the stable mask for THIS IFG (not the "
            "stack-wide statistic). Used by aggregate "
            "magnitude_vs_coherence_pearson_r. None when not computed."
        ),
    )


class RampAggregate(BaseModel):
    """Aggregate ramp statistics across the IFG stack (Phase 4 D-11)."""

    model_config = ConfigDict(extra="forbid")

    mean_magnitude_rad: float = Field(
        ...,
        description="Mean of per-IFG ramp_magnitude_rad over finite values.",
    )
    direction_stability_sigma_deg: float = Field(
        ...,
        description=(
            "Circular standard deviation of per-IFG ramp_direction_deg "
            "(degrees). Low values (< 30 deg) indicate orbit-class ramps; "
            "high values indicate PHASS-class ramps."
        ),
    )
    magnitude_vs_coherence_pearson_r: float = Field(
        ...,
        description=(
            "Pearson r between per-IFG ramp_magnitude_rad and ifg_coherence_mean. "
            "Positive correlation (r > 0.5) suggests PHASS-class ramps "
            "(low-coherence IFGs have larger ramps); near-zero suggests orbit."
        ),
    )
    n_ifgs: int = Field(
        ..., ge=1,
        description="Number of IFGs included in the aggregate.",
    )


class RampAttribution(BaseModel):
    """Per-cell ramp-attribution result (Phase 4 D-11 + D-12)."""

    model_config = ConfigDict(extra="forbid")

    per_ifg: list[PerIFGRamp] = Field(
        default_factory=list,
        description="Per-IFG ramp parameters; sortable for CONCLUSIONS rendering.",
    )
    aggregate: RampAggregate = Field(
        ...,
        description="Stack-wide aggregate of ramp statistics.",
    )
    attributed_source: AttributedSource = Field(
        ...,
        description=(
            "Auto-attribute label from the deterministic rule in CONTEXT "
            "D-Claude's-Discretion: 'orbit' if direction sigma < 30 deg AND "
            "coh-correlation < 0.5; 'phass' if direction sigma >= 30 deg AND "
            "coh-correlation > 0.5; 'mixed' if both stability + correlation "
            "are present; 'inconclusive' otherwise; 'tropospheric' reserved "
            "for diagnostic (c) when ERA5 toggle is enabled (Phase 4 D-09 "
            "deferral)."
        ),
    )
    attribution_note: str = Field(
        default="",
        description=(
            "Free-form note written by the eval script. Default: "
            "'Automated; human review pending in CONCLUSIONS'. The "
            "canonical labelling lives in CONCLUSIONS prose; this field "
            "is the audit trail."
        ),
    )


class DISPProductQualityResultJson(ProductQualityResultJson):
    """DISP product-quality with explicit coherence_source provenance flag.

    Inherits measurements + criterion_ids from ProductQualityResultJson.
    Adds coherence_source as a distinct field (not a measurements key) so
    matrix_writer can render the provenance flag inline without confusing
    it with a measurement.
    """

    coherence_source: CoherenceSource = Field(
        ...,
        description=(
            "Provenance flag. 'phase3-cached' = cross-cell read from "
            "eval-cslc-selfconsist-nam/metrics.json[per_aoi][SoCal]. "
            "'fresh' = computed from cached CSLC stack at this run."
        ),
    )


class DISPCellMetrics(MetricsJson):
    """Phase 4 DISP comparison-adapter cell aggregate (CONTEXT D-11).

    matrix_writer detects this schema via presence of ``ramp_attribution``
    in the raw JSON. Shape is symmetric across SoCal and Bologna -- both
    cells carry the same fields even though SoCal coherence comes from
    cross-cell read and Bologna's is fresh.

    Inherits schema_version / runtime_conda_list_hash / criterion_ids_applied
    from MetricsJson. The base product_quality + reference_agreement fields
    are overridden with DISP-specific extensions:
    - product_quality is DISPProductQualityResultJson (adds coherence_source)
    - reference_agreement is the existing ReferenceAgreementResultJson
      (correlation, bias_mm_yr, plus rmse_mm_yr + sample_count via
      measurements dict)
    """

    product_quality: DISPProductQualityResultJson = Field(
        ...,
        description=(
            "DISP self-consistency PQ measurements. Includes "
            "coherence_median_of_persistent + 5 other coherence stats + "
            "residual_mm_yr. coherence_source field is the cross-cell-read "
            "provenance flag (D-08)."
        ),
    )
    reference_agreement: ReferenceAgreementResultJson = Field(
        ...,
        description=(
            "DISP reference-agreement against OPERA DISP-S1 (N.Am.) or "
            "EGMS L2a (EU). Measurements: correlation, bias_mm_yr, "
            "rmse_mm_yr, sample_count."
        ),
    )
    ramp_attribution: RampAttribution = Field(
        ...,
        description="Per-IFG planar-ramp diagnostic (Phase 4 D-09 + D-10 + D-11).",
    )
    cell_status: DISPCellStatus = Field(
        ...,
        description=(
            "Whole-cell verdict. MIXED is the expected first-rollout "
            "status (CALIBRATING product_quality + FAIL reference_agreement). "
            "PASS / FAIL reserved for post-BINDING-promotion (v1.2+ per "
            "GATE-05). BLOCKER for stable-mask < 100 valid pixels."
        ),
    )
```

### matrix_writer disp:nam + disp:eu render branches

**Add to `src/subsideo/validation/matrix_writer.py`** (additive only; mirrors the Phase 3 `_render_cslc_selfconsist_cell` pattern):

```python
# --- Phase 4 DISP rendering (CONTEXT D-19 + D-21) ---

def _is_disp_cell_shape(metrics_path: Path) -> bool:
    """Return True when metrics.json has top-level 'ramp_attribution'.

    Phase 4 D-11 schema discriminator. Checked BEFORE _is_cslc_selfconsist_shape
    (per_aoi) and _is_rtc_eu_shape (per_burst) because the DISP schema is
    structurally disjoint from both -- ramp_attribution is the unambiguous
    Phase 4 marker.
    """
    import json as _json
    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError):
        return False
    return isinstance(raw, dict) and "ramp_attribution" in raw


def _render_disp_cell(
    metrics_path: Path,
    *,
    region: str,
) -> tuple[str, str] | None:
    """Render a Phase 4 DISP cell as (pq_col, ra_col).

    Called for both disp:nam (region='nam') and disp:eu (region='eu').
    PQ column always italicised (CALIBRATING). RA column renders PASS/FAIL
    against criteria.disp.correlation_min + bias_mm_yr_max (BINDING).

    PQ column format:
        "*coh=0.87 ([phase3-cached]) / resid=0.5 mm/yr (CALIBRATING) | attr=phass*"
    RA column format:
        "r=0.04 (>0.92 FAIL) / bias=+23.6 mm/yr (<3 FAIL)"

    The attributed_source label is shown inline in the PQ column (D-19
    "show attributed_source label inline"). The cell-level status (MIXED)
    is implicit from PQ italics + RA non-italics.
    """
    from subsideo.validation.matrix_schema import DISPCellMetrics

    try:
        m = DISPCellMetrics.model_validate_json(metrics_path.read_text())
    except Exception as e:
        logger.warning("Failed to parse DISPCellMetrics from {}: {}", metrics_path, e)
        return None

    # --- PQ side ---
    pq = m.product_quality
    coh_med = pq.measurements.get("coherence_median_of_persistent")
    resid = pq.measurements.get("residual_mm_yr")
    src = pq.coherence_source  # 'phase3-cached' | 'fresh'
    attr = m.ramp_attribution.attributed_source

    parts = []
    if coh_med is not None:
        parts.append(f"coh={float(coh_med):.2f} ([{src}])")
    else:
        parts.append("coh=—")
    if resid is not None:
        parts.append(f"resid={float(resid):.1f} mm/yr")
    else:
        parts.append("resid=—")
    parts.append(f"attr={attr}")
    pq_col = f"*{' / '.join(parts)} (CALIBRATING)*"

    # --- RA side ---
    ra = m.reference_agreement
    rendered_ra = []
    for cid in ra.criterion_ids:
        rendered_ra.append(_render_measurement(cid, ra.measurements))
    ra_col = " / ".join(rendered_ra) if rendered_ra else "—"
    return pq_col, ra_col
```

**Dispatch addition in `write_matrix()`** — insert BEFORE the `_is_cslc_selfconsist_shape` branch (DISP `ramp_attribution` is a distinct discriminator and structurally never co-occurs with `per_aoi` or `per_burst`):

```python
# Phase 4 DISP branch: metrics.json with a 'ramp_attribution' key.
# Checked BEFORE the cslc_selfconsist branch -- DISP schema is structurally
# disjoint from CSLC self-consist (no per_aoi key), so this is an invariant.
if metrics_path.exists() and _is_disp_cell_shape(metrics_path):
    cols = _render_disp_cell(metrics_path, region=str(cell["region"]))
    if cols is not None:
        pq_col, ra_col = cols
        lines.append(
            f"| {product} | {region} | {_escape_table_cell(pq_col)} | "
            f"{_escape_table_cell(ra_col)} |"
        )
        continue
```

### Auto-attribute rule

**Place in `selfconsistency.py` next to `fit_planar_ramp`** (or in eval-script-local helper — plan-phase decides; the rule is small enough either way):

```python
def auto_attribute_ramp(
    direction_stability_sigma_deg: float,
    magnitude_vs_coherence_pearson_r: float,
    *,
    direction_stability_cutoff_deg: float = 30.0,
    coherence_correlation_cutoff: float = 0.5,
) -> Literal["phass", "orbit", "tropospheric", "mixed", "inconclusive"]:
    """Deterministic ramp-source auto-attribute (CONTEXT D-Claude's-Discretion).

    Rules:
        - direction stable (sigma < cutoff_deg): orbit-class signature
        - magnitude correlates with coherence (r > correlation_cutoff): PHASS-class
        - both: 'mixed'
        - neither: 'inconclusive'
        - 'tropospheric': reserved for diagnostic (c) (ERA5 toggle, deferred);
          this rule never returns it.

    Cutoffs are NOT criteria.py entries (this rule is for narrative
    attribution, not gating).
    """
    direction_stable = direction_stability_sigma_deg < direction_stability_cutoff_deg
    coh_correlated = magnitude_vs_coherence_pearson_r > coherence_correlation_cutoff

    if direction_stable and coh_correlated:
        return "mixed"
    if direction_stable:
        return "orbit"
    if coh_correlated:
        return "phass"
    return "inconclusive"
```

**Aggregate computation** (separate helper because it touches both ramp data and IFG-coherence stack):

```python
def compute_ramp_aggregate(
    ramp_data: dict[str, np.ndarray],
    ifg_coherence_per_ifg: np.ndarray,
) -> RampAggregate:
    """Compute aggregate RampAggregate from per-IFG ramp data + coherence.

    direction_stability_sigma_deg is computed via circular standard deviation
    (scipy.stats.circstd or manual atan2-based unwrap) because raw stddev on
    angles in degrees is wrong (does not handle the 359 -> 0 wraparound).
    """
    import numpy as np
    from scipy.stats import circstd  # already a transitive dep

    mag = ramp_data["ramp_magnitude_rad"]
    dir_deg = ramp_data["ramp_direction_deg"]
    coh = ifg_coherence_per_ifg

    finite = np.isfinite(mag) & np.isfinite(dir_deg) & np.isfinite(coh)
    if int(finite.sum()) < 3:
        return RampAggregate(
            mean_magnitude_rad=float("nan"),
            direction_stability_sigma_deg=float("nan"),
            magnitude_vs_coherence_pearson_r=float("nan"),
            n_ifgs=int(finite.sum()),
        )

    mag_f = mag[finite]
    dir_f = dir_deg[finite]
    coh_f = coh[finite]

    mean_magnitude = float(mag_f.mean())
    # Circular std on degrees: convert to radians, scipy handles wrap
    direction_sigma_deg = float(
        np.degrees(circstd(np.radians(dir_f), high=np.pi, low=-np.pi))
    )
    pearson_r = float(np.corrcoef(mag_f, coh_f)[0, 1])
    return RampAggregate(
        mean_magnitude_rad=mean_magnitude,
        direction_stability_sigma_deg=direction_sigma_deg,
        magnitude_vs_coherence_pearson_r=pearson_r,
        n_ifgs=int(finite.sum()),
    )
```

---

## Library APIs (concrete syntax)

### rasterio.warp.reproject for block_mean

`rasterio.warp.Resampling.average` is the rasterio-native block-mean equivalent (D-02):

```python
import rasterio
from rasterio.warp import Resampling, reproject

# Read native velocity
with rasterio.open(native_velocity_path) as src:
    src_data = src.read(1).astype(np.float64)
    src_transform = src.transform
    src_crs = src.crs

# Read reference grid metadata
with rasterio.open(reference_grid_path) as ref:
    dst_transform = ref.transform
    dst_crs = ref.crs
    dst_shape = (ref.height, ref.width)

# Block-mean reproject (Resampling.average == averaging filter)
dst_data = np.full(dst_shape, np.nan, dtype=np.float64)
reproject(
    source=src_data,
    destination=dst_data,
    src_transform=src_transform,
    src_crs=src_crs,
    dst_transform=dst_transform,
    dst_crs=dst_crs,
    resampling=Resampling.average,  # block_mean
)
```

`Resampling.average` is the "averaging" GDAL resampler — for downsampling 5×10 m → 30 m, GDAL averages all source pixels whose centre falls inside each destination pixel's bbox (effectively block-mean weighted by source-pixel coverage of destination cell). Matches OPERA's own multilook semantically.

### scipy.ndimage.gaussian_filter for gaussian

PITFALLS P3.1 specifies σ = 0.5 × reference_spacing. For 30 m reference and 5×10 m native: σ_x = 15 m / 5 m = 3 px (range), σ_y = 15 m / 10 m = 1.5 px (azimuth):

```python
from scipy.ndimage import gaussian_filter

# Two-step: smooth on native grid, then resample to reference via nearest
sigma_pix_y = (0.5 * abs(dst_transform.e)) / abs(src_transform.e)  # row sigma
sigma_pix_x = (0.5 * abs(dst_transform.a)) / abs(src_transform.a)  # col sigma

# Gaussian-smooth native data; nan_policy: replace with mean before filter
src_filled = np.where(np.isfinite(src_data), src_data, 0.0)
src_smoothed = gaussian_filter(src_filled, sigma=(sigma_pix_y, sigma_pix_x))

# Then reproject onto reference grid via nearest (preserves the smoothed value)
reproject(
    source=src_smoothed,
    destination=dst_data,
    src_transform=src_transform,
    src_crs=src_crs,
    dst_transform=dst_transform,
    dst_crs=dst_crs,
    resampling=Resampling.nearest,
)
```

`scipy.ndimage.gaussian_filter` is not NaN-safe; the conventional InSAR workaround is replace-with-zero (or mean) before filter. Plan-phase may consider `astropy.convolution.convolve` for true NaN-aware Gaussian (better but adds astropy import).

### rasterio.warp.Resampling for bilinear / nearest

```python
# bilinear (matches v1.0 line 145 and Stage 9 of run_eval_disp.py)
reproject(
    source=src_data, destination=dst_data,
    src_transform=src_transform, src_crs=src_crs,
    dst_transform=dst_transform, dst_crs=dst_crs,
    resampling=Resampling.bilinear,
)

# nearest (degenerate; for kernel-comparison studies in follow-up milestone)
reproject(
    source=src_data, destination=dst_data,
    src_transform=src_transform, src_crs=src_crs,
    dst_transform=dst_transform, dst_crs=dst_crs,
    resampling=Resampling.nearest,
)
```

### Sampling rasters at points (rasterio.sample / rioxarray)

For DISP-01 form (c) — EGMS L2a PS point list. `compare_disp_egms_l2a()` already does this with `rasterio.DatasetReader.sample()` (lines 325–326 of `compare_disp.py`):

```python
import rasterio
from pyproj import Transformer

# Reproject points from spec.crs to native raster CRS
with rasterio.open(native_velocity_path) as src:
    raster_crs = src.crs
    transformer = Transformer.from_crs(spec.crs, raster_crs, always_xy=True)
    xs, ys = transformer.transform(
        spec.points_lonlat[:, 0],  # lon
        spec.points_lonlat[:, 1],  # lat
    )
    xy = list(zip(xs, ys, strict=True))
    # nearest-neighbour sample
    sampled = np.array([v[0] for v in src.sample(xy)], dtype=np.float64)
```

For methods other than `nearest`:
- `bilinear` at points: extract a 2×2 window via `src.read(1, window=Window(...))` and bilinear-interpolate manually, OR use `rasterio.windows.bounds()` + `scipy.ndimage.map_coordinates(order=1)`.
- `block_mean` at points: extract an N×M window (where N/M = ratio of reference spacing to native spacing) and `.mean()` over finite values.
- `gaussian` at points: extract a window of `~3σ` radius and apply the 2-D Gaussian kernel weighted average.

For Phase 4 production default (D-02 = `block_mean`), the eval scripts call form (a) for SoCal (raster vs raster) and form (c) for Bologna (raster vs PS). Form (c)'s `block_mean` implementation should match D-02 — average all native pixels in the reference-cell footprint around each PS point.

### Reading dolphin velocity.tif + unwrapped IFGs

**Velocity.tif locations (verified on disk):**
- N.Am.: `eval-disp/disp/dolphin/timeseries/velocity.tif` (22 MB, 3959×17881 float32, EPSG:32611)
- EU: `eval-disp-egms/disp/dolphin/timeseries/velocity.tif` (104 MB, 3942×18674 float32, EPSG:32632)

**Units conversion** (already implemented in `compare_disp.py` lines 332–333; `selfconsistency.compute_residual_velocity` step 5):

```python
# dolphin convention: rad/yr (LOS phase rate)
SENTINEL1_WAVELENGTH_M = 0.05546576  # = 0.055465763 m -- C-band carrier

# Read raster
with rasterio.open(velocity_path) as src:
    v_rad_per_year = src.read(1).astype(np.float64)
    velocity_transform = src.transform
    velocity_crs = src.crs

# Convert to mm/yr LOS surface motion
# Sign convention: positive phase rate -> target moving toward sensor
#   -> negative LOS motion (typical InSAR conv with -lambda/(4*pi))
v_mm_yr = -v_rad_per_year * SENTINEL1_WAVELENGTH_M / (4.0 * np.pi) * 1000.0
```

**Unwrapped IFG stack locations (verified on disk):**
- N.Am.: `eval-disp/disp/dolphin/unwrapped/*.unw.tif` — 39 files (sequential + N-step network)
- EU: `eval-disp-egms/disp/dolphin/unwrapped/*.unw.tif` — 39 files

Filename pattern: `<ref_date>_<sec_date>.unw.tif` (e.g. `20240108_20240120.unw.tif`). Same dir contains `*.unw.conncomp.tif` (connected-component labels).

**Loading the unwrapped stack into (N, H, W) for fit_planar_ramp:**

```python
from pathlib import Path
import re
import rasterio

unwrapped_dir = Path("eval-disp/disp/dolphin/unwrapped")  # or eval-disp-egms/...
unw_files = sorted(unwrapped_dir.glob("*.unw.tif"))

date_pattern = re.compile(r"^(\d{8})_(\d{8})\.unw\.tif$")
ifg_records: list[tuple[str, str, np.ndarray]] = []
for f in unw_files:
    m = date_pattern.match(f.name)
    if not m:
        continue
    ref_date = m.group(1)  # YYYYMMDD
    sec_date = m.group(2)
    with rasterio.open(f) as src:
        data = src.read(1).astype(np.float32)
    ifg_records.append((ref_date, sec_date, data))

# Stack into (N, H, W)
ifgrams_unw_stack = np.stack([d for _, _, d in ifg_records], axis=0)
ref_dates = [r for r, _, _ in ifg_records]
sec_dates = [s for _, s, _ in ifg_records]
```

**Important**: dolphin's `unwrapped/*.unw.tif` are typically zero-outside-valid-data, NOT NaN. The `valid = np.isfinite(z) & (z != 0.0)` mask in `fit_planar_ramp` covers this.

**Filtering to sequential-12-day pairs only (D-07):** dolphin's interferogram-network includes both sequential and N-step (look-back) pairs. For ramp attribution, `fit_planar_ramp` should run on ALL 39 — the per-IFG planar-ramp signature is informative regardless of network role. Plan-phase decides whether to filter to N-1 sequential-only (14 for SoCal, 18 for Bologna) for the aggregate, or include all 39. Recommended: include all 39 in `per_ifg`, but `RampAggregate.n_ifgs` reports the count actually used.

**Per-IFG coherence (for `magnitude_vs_coherence_pearson_r` in aggregate):** Two paths:
1. **From dolphin's interferogram-network coherence** (`eval-disp/disp/dolphin/interferograms/*.int.cor.tif`) — fast, but couples validation to product (FEATURES anti-feature).
2. **Compute fresh from CSLC stack via boxcar 5×5** (D-07 convention; reuses `_compute_ifg_coherence_stack` from `run_eval_cslc_selfconsist_nam.py`) — but this gives N-1 = 14 sequential coherence values, not 39.

D-07 says coherence stat is sequential 12-day from CSLC stack. For `magnitude_vs_coherence_pearson_r`, the aggregate uses ONLY the sequential 12-day pairs (matching the CSLC-derived coherence). If `fit_planar_ramp` runs on all 39 unwrapped IFGs, only the 14 sequential ones contribute to `magnitude_vs_coherence_pearson_r` (skip non-sequential when computing aggregate). Plan-phase commits this filter; the simplest implementation is:

```python
def is_sequential_12day(ref_date_iso: str, sec_date_iso: str) -> bool:
    from datetime import datetime
    ref = datetime.fromisoformat(ref_date_iso)
    sec = datetime.fromisoformat(sec_date_iso)
    return abs((sec - ref).days - 12) <= 1  # 12-day baseline ±1 day for cross-sat
```

### Pydantic v2 BaseModel + Field syntax for the new schema types

Already shown above in the schema definitions. Key conventions consumed verbatim from existing `matrix_schema.py`:
- `from pydantic import BaseModel, ConfigDict, Field`
- `model_config = ConfigDict(extra="forbid")` on every BaseModel
- `Field(..., description=...)` for required fields with documentation
- `Field(default=..., description=...)` for optional defaults
- `Field(default_factory=list, ...)` for collection defaults
- `Literal[...]` for enumerated string fields (declared at module top alongside `AOIStatus`, `CSLCCellStatus`)

Self-referential types use `model_rebuild()` after class definition (see `AOIResult.model_rebuild()` at matrix_schema.py:387). Phase 4 schemas don't need this (no self-references).

---

## Code Shape (what to reuse, what to add, what to refactor)

### compare_disp.py — add prepare_for_reference

**New top-level function** `prepare_for_reference(native_velocity, reference_grid, *, method)` per §"Architecture / prepare_for_reference signature".
**New top-level dataclass** `ReferenceGridSpec(points_lonlat, crs, point_ids)`.
**Three private helpers**: `_resample_onto_path`, `_resample_onto_dataarray`, `_point_sample`.

**Module docstring** updated with paragraph: "The `prepare_for_reference` adapter converts subsideo's native 5×10 m DISP velocity to a reference grid (OPERA DISP 30 m or EGMS L2a PS points) for comparison. This is validation-only infrastructure; production DISP output remains at native resolution. See `docs/validation_methodology.md` §3 for the multilook-method ADR."

**Refactor scope decision (plan-phase):**
- **Option A (minimal):** Leave `compare_disp()` Step 2 (`Resampling.bilinear` line 145) and `compare_disp_egms_l2a()` lines 325–326 (`src.sample()` nearest) UNCHANGED. The eval scripts call `prepare_for_reference()` BEFORE `compare_disp_*()` and pass the already-multilooked velocity. Pro: smaller diff, lower risk. Con: two paths for resampling code (the legacy paths are still in `compare_disp.py`).
- **Option B (refactor):** Replace the ad-hoc `Resampling.bilinear` in `compare_disp()` and the nearest sampling in `compare_disp_egms_l2a()` with internal calls to `prepare_for_reference()`. Pro: single source of truth. Con: larger diff; risks behavioural drift on existing v1.0 callers (the only current caller is `run_eval_disp_egms.py` line 550-555 which uses `compare_disp_egms_l2a()`).

**Recommendation:** Option A in Phase 4, defer Option B to a v2 cleanup. Reasoning: `compare_disp()` is unused in v1.1 (run_eval_disp.py Stage 9 does its own ad-hoc reproject and never calls `compare_disp()`); `compare_disp_egms_l2a()` is used by `run_eval_disp_egms.py` and a refactor would be a behaviour change at run-time. The plan-phase final decision.

### selfconsistency.py — add fit_planar_ramp + auto_attribute_ramp + compute_ramp_aggregate

**Three new top-level functions**:
- `fit_planar_ramp(ifgrams_stack, mask=None) -> dict[str, np.ndarray]` (D-10)
- `compute_ramp_aggregate(ramp_data, ifg_coherence_per_ifg) -> RampAggregate` (D-12 helper)
- `auto_attribute_ramp(direction_stability_sigma_deg, magnitude_vs_coherence_pearson_r, *, ...) -> Literal[...]` (D-12)

**Module charter docstring** broadens from "Sequential-IFG coherence + reference-frame residual" to "Sequential-IFG self-consistency primitives" (per D-10 charter expansion).

**No edits** to existing `coherence_stats`, `residual_mean_velocity`, `compute_residual_velocity`.

### matrix_schema.py — add 3 Pydantic types (additive only)

**New types**:
- `PerIFGRamp(BaseModel)` (per-IFG row)
- `RampAggregate(BaseModel)` (stack-wide aggregate)
- `RampAttribution(BaseModel)` (composite of per_ifg + aggregate + attributed_source)
- `DISPProductQualityResultJson(ProductQualityResultJson)` (adds coherence_source field)
- `DISPCellMetrics(MetricsJson)` (composite cell schema)

**Type aliases**:
- `CoherenceSource = Literal["phase3-cached", "fresh"]`
- `AttributedSource = Literal["phass", "orbit", "tropospheric", "mixed", "inconclusive"]`
- `DISPCellStatus = Literal["PASS", "FAIL", "CALIBRATING", "MIXED", "BLOCKER"]`

**No edits** to existing types (Phase 1 D-09 big-bang lock-in).

### matrix_writer.py — add 2 cell render branches

**New helpers**:
- `_is_disp_cell_shape(metrics_path) -> bool` (raw-JSON `ramp_attribution` discriminator)
- `_render_disp_cell(metrics_path, *, region) -> tuple[str, str] | None` (PQ + RA columns)

**Dispatch addition**: insert the disp branch BEFORE the existing `_is_cslc_selfconsist_shape` branch in `write_matrix()` (DISP `ramp_attribution` is a structurally disjoint discriminator; order matters only for unambiguous shape-detection, which is the case here).

**No edits** to base rendering, RTC-EU rendering, or CSLC-self-consist rendering.

### run_eval_disp.py + run_eval_disp_egms.py — 5 changes per script

Per CONTEXT D-Claude's-Discretion (Code Shape script flow):

**(1) Stage 9 ad-hoc reproject → adapter call.** Replace lines 610–632 of `run_eval_disp.py` (`Resampling.bilinear` block) with:

```python
from subsideo.validation.compare_disp import prepare_for_reference

REFERENCE_MULTILOOK_METHOD: Literal["block_mean"] = "block_mean"  # D-04 constant

# build OPERA reference grid spec from corrections/x and corrections/y
opera_ref_path = ref_dir / "opera_velocity_derived.tif"  # convert .npy → COG once
# OR: pass a Path to the first OPERA .nc directly via xarray
opera_ref_da = xr.open_dataarray(downloaded_nc[0])  # form (b)

our_on_opera = prepare_for_reference(
    native_velocity=velocity_path,
    reference_grid=opera_ref_da,
    method=REFERENCE_MULTILOOK_METHOD,
)
```

For Bologna (`run_eval_disp_egms.py`), use form (c):

```python
egms_df = _load_egms_l2a_points(egms_csv_paths, velocity_col="mean_velocity")
egms_spec = ReferenceGridSpec(
    points_lonlat=np.column_stack([egms_df["lon"].values, egms_df["lat"].values]),
    crs="EPSG:4326",
    point_ids=None,  # or egms_df["pid"] if available
)
our_at_ps = prepare_for_reference(
    native_velocity=velocity_path,
    reference_grid=egms_spec,
    method=REFERENCE_MULTILOOK_METHOD,
)
# our_at_ps shape: (N_PS,) in rad/yr; convert to mm/yr; pair with egms_df["mean_velocity"]
```

**(2) Add product-quality computation block (Stage 10).** After Stage 9 reference-agreement is computed, add:

```python
from subsideo.validation.stable_terrain import build_stable_mask
from subsideo.validation.selfconsistency import coherence_stats, residual_mean_velocity
from subsideo.data.worldcover import fetch_worldcover_class60, load_worldcover_for_bbox
from subsideo.data.natural_earth import load_coastline_and_waterbodies

# 10.1 Build stable mask (Phase 3 SoCal-identical params per D-06)
worldcover_dir = OUT / "worldcover"
fetch_worldcover_class60(BURST_BBOX, out_dir=worldcover_dir)
wc_data, wc_transform, wc_crs = load_worldcover_for_bbox(
    worldcover_dir, BURST_BBOX, output_epsg=EPSG
)
slope_deg, dem_transform, dem_crs = _compute_slope_deg(dem_path)  # imported helper
coastline, waterbodies = load_coastline_and_waterbodies(BURST_BBOX)

# Reproject worldcover onto DEM grid (same as Phase 3 _reproject_worldcover_to_dem_grid)
wc_on_dem = _reproject_worldcover_to_dem_grid(wc_data, wc_transform, wc_crs, dem_transform, dem_crs, slope_deg.shape)

stable_mask = build_stable_mask(
    wc_on_dem, slope_deg, coastline=coastline, waterbodies=waterbodies,
    transform=dem_transform, crs=dem_crs,
    coast_buffer_m=5000, water_buffer_m=500, slope_max_deg=10,
)

# 10.2 Coherence: cross-cell read for SoCal; fresh for Bologna (D-08)
phase3_metrics_path = Path("eval-cslc-selfconsist-nam/metrics.json")
if region == "nam" and phase3_metrics_path.exists():
    import json
    phase3 = json.loads(phase3_metrics_path.read_text())
    socal_aoi = next(a for a in phase3["per_aoi"] if a["aoi_name"] == "SoCal")
    coh_stats = socal_aoi["product_quality"]["measurements"]
    coherence_source = "phase3-cached"
else:
    sorted_h5 = sorted(cslc_dir.rglob("*.h5"))
    ifgrams_stack = _compute_ifg_coherence_stack(sorted_h5, boxcar_px=5)
    # Reproject stable_mask onto CSLC grid (Phase 3 pattern)
    stable_mask_cslc = _reproject_stable_mask_to_cslc(stable_mask, dem_transform, dem_crs, ifgrams_stack)
    coh_stats = coherence_stats(ifgrams_stack, stable_mask_cslc, coherence_threshold=0.6)
    coherence_source = "fresh"

# 10.3 Residual velocity: ALWAYS fresh from dolphin output (D-08)
v_rad_per_year = read_dolphin_velocity_tif(velocity_path)  # rasterio open + read(1)
v_mm_yr = -v_rad_per_year * SENTINEL1_WAVELENGTH_M / (4.0 * np.pi) * 1000.0
# Reproject stable_mask onto velocity raster grid (which is at native 5×10 m)
stable_mask_velocity = _reproject_stable_mask_to_velocity(stable_mask, dem_transform, dem_crs, velocity_path)
residual = residual_mean_velocity(v_mm_yr, stable_mask_velocity, frame_anchor="median")
```

**(3) Add ramp-attribution block (Stage 11).** Read all unwrapped IFGs:

```python
from subsideo.validation.selfconsistency import (
    fit_planar_ramp, compute_ramp_aggregate, auto_attribute_ramp,
)

unwrapped_dir = disp_dir / "dolphin" / "unwrapped"
unw_files = sorted(unwrapped_dir.glob("*.unw.tif"))

# Filter to sequential 12-day pairs (D-07: matches CSLC self-consistency methodology)
sequential_unw = [
    f for f in unw_files
    if is_sequential_12day(*parse_dates_from_unw_name(f.name))
]
ifgrams_unw_stack = np.stack([rasterio.open(f).read(1) for f in sequential_unw], axis=0)

# Per-IFG coherence: mean of cached interferograms/*.int.cor.tif over stable_mask
# (Plan-phase decides: dolphin's coherence layer for the per-IFG mean OR re-compute
# from CSLC. Recommend the cached cor.tif for cheapness; the FEATURES anti-feature
# concern is about USING dolphin's coherence as the GATE stat -- using it as a
# diagnostic-attribution input is acceptable per D-12 prose.)
ifg_coh_means = []
for f in sequential_unw:
    cor_file = (disp_dir / "dolphin" / "interferograms" /
                f.name.replace(".unw.tif", ".int.cor.tif"))
    with rasterio.open(cor_file) as src:
        coh = src.read(1)
    # Reproject stable_mask onto coherence grid + compute mean over masked-finite pixels
    ifg_coh_means.append(_mean_coh_over_mask(coh, stable_mask_velocity_or_cor_grid))
ifg_coh_per_ifg = np.array(ifg_coh_means, dtype=np.float64)

# Fit ramps (full-burst per D-Claude's-Discretion; mask=None)
ramp_data = fit_planar_ramp(ifgrams_unw_stack, mask=None)
agg = compute_ramp_aggregate(ramp_data, ifg_coh_per_ifg)
attr = auto_attribute_ramp(
    agg.direction_stability_sigma_deg,
    agg.magnitude_vs_coherence_pearson_r,
)

per_ifg_records = [
    PerIFGRamp(
        ifg_idx=k,
        ref_date_iso=parse_dates_from_unw_name(sequential_unw[k].name)[0],
        sec_date_iso=parse_dates_from_unw_name(sequential_unw[k].name)[1],
        ramp_magnitude_rad=float(ramp_data["ramp_magnitude_rad"][k]),
        ramp_direction_deg=float(ramp_data["ramp_direction_deg"][k]),
        ifg_coherence_mean=float(ifg_coh_per_ifg[k]),
    )
    for k in range(len(sequential_unw))
]
ramp_attribution = RampAttribution(
    per_ifg=per_ifg_records,
    aggregate=agg,
    attributed_source=attr,
    attribution_note="Automated; human review pending in CONCLUSIONS",
)
```

**(4) Write nested metrics.json per DISPCellMetrics schema (Stage 12).**

```python
pq = DISPProductQualityResultJson(
    measurements={
        "coherence_median_of_persistent": coh_stats["median_of_persistent"],
        "residual_mm_yr": residual,
        "coherence_mean": coh_stats["mean"],
        "coherence_median": coh_stats["median"],
        "coherence_p25": coh_stats["p25"],
        "coherence_p75": coh_stats["p75"],
        "persistently_coherent_fraction": coh_stats["persistently_coherent_fraction"],
    },
    criterion_ids=[
        "disp.selfconsistency.coherence_min",
        "disp.selfconsistency.residual_mm_yr_max",
    ],
    coherence_source=coherence_source,
)
ra = ReferenceAgreementResultJson(
    measurements={
        "correlation": float(corr),
        "bias_mm_yr": float(bias_mm),
        "rmse_mm_yr": float(rmse_mm),
        "sample_count": int(n_valid),
    },
    criterion_ids=[
        "disp.correlation_min",
        "disp.bias_mm_yr_max",
    ],
)
cell_status = _resolve_cell_status(pq, ra, ramp_attribution, agg.n_ifgs)
metrics = DISPCellMetrics(
    schema_version=1,
    product_quality=pq,
    reference_agreement=ra,
    ramp_attribution=ramp_attribution,
    cell_status=cell_status,
    criterion_ids_applied=[
        "disp.selfconsistency.coherence_min",
        "disp.selfconsistency.residual_mm_yr_max",
        "disp.correlation_min",
        "disp.bias_mm_yr_max",
    ],
    runtime_conda_list_hash=_compute_conda_list_hash(),
)
(OUT / "metrics.json").write_text(metrics.model_dump_json(indent=2))

meta = MetaJson(
    schema_version=1,
    git_sha=_git_sha(), git_dirty=_git_dirty(),
    run_started_iso=run_start_iso, run_duration_s=time.monotonic() - t_start,
    python_version=sys.version, platform=platform.platform(),
    input_hashes=_collect_input_hashes(),
)
(OUT / "meta.json").write_text(meta.model_dump_json(indent=2))
```

**(5) Declare REFERENCE_MULTILOOK_METHOD constant + EXPECTED_WALL_S.**

At the top of each script (after the existing `EXPECTED_WALL_S` block, both currently `5400`; bump per CONTEXT):

```python
EXPECTED_WALL_S = 60 * 60 * 6   # 21600s -- 6h cap (CONTEXT D-Claude's-Discretion)
REFERENCE_MULTILOOK_METHOD: Literal["block_mean"] = "block_mean"  # D-04
```

Both must be module-top constants the supervisor AST-parses (T-07-06 whitelisted forms; `60 * 60 * 6` is a permitted nested BinOp per supervisor.py:60–66).

---

## Cross-cell read (Phase 3 cache reuse for SoCal coherence)

### eval-cslc-selfconsist-nam/metrics.json key path

**Verified file** (`eval-cslc-selfconsist-nam/metrics.json`, 5 KB, 2026-04-24): has `per_aoi` array with SoCal as the first entry. Schema is `CSLCSelfConsistNAMCellMetrics`.

**Key path for SoCal coherence sub-result:**

```python
import json
phase3 = json.loads(Path("eval-cslc-selfconsist-nam/metrics.json").read_text())
socal = next(a for a in phase3["per_aoi"] if a["aoi_name"] == "SoCal")
coh_measurements = socal["product_quality"]["measurements"]
# coh_measurements is a flat dict with keys:
# - "coherence_median_of_persistent": 0.8867583934749876
# - "residual_mm_yr": -0.10922253876924515  (NOT used; DISP residual is fresh per D-08)
# - "coherence_mean": 0.41552377426345627
# - "coherence_median": 0.4017247853002378
# - "coherence_p25": 0.2741654865177614
# - "coherence_p75": 0.5541118598942245
# - "persistently_coherent_fraction": 0.024691358024691357
```

The DISP-N.Am. eval script then writes back ONLY the 6 coherence keys (drops `residual_mm_yr` since it's pulled fresh from dolphin output). The structural shape of `pq.measurements` is identical between Phase 3 and Phase 4 — Phase 4 just doesn't include the Phase-3-style residual.

### Provenance flag in DISP-N.Am. metrics.json

**Field:** `product_quality.coherence_source: Literal["phase3-cached", "fresh"]` (declared on `DISPProductQualityResultJson`, NOT on the base `ProductQualityResultJson`).

**Audit-trail recipe:**

```python
# In matrix_writer rendering -- visibly show the source:
parts.append(f"coh={coh:.2f} ([{src}])")  # e.g. "coh=0.89 ([phase3-cached])"
```

**Recompute trigger:** if `eval-cslc-selfconsist-nam/metrics.json` is missing, OR has a SHA different from a previous run captured in `meta.json` `input_hashes`, the eval script falls back to the fresh path. Plan-phase commits the recompute-trigger logic; baseline assumption is "if the file is present and parses, trust it" (Phase 3 contract).

---

## Bologna-specific

### Burst footprint + UTM zone

Verified from `run_eval_disp_egms.py` and v1.0 CONCLUSIONS_DISP_EGMS.md §2.1:
- Burst ID: `t117_249422_iw2`
- Relative orbit: 117 (ascending), sensing ~17:06 UTC
- Bbox (WGS84): `lon ∈ [11.227, 12.402]`, `lat ∈ [44.457, 44.785]` — a ~125 km × 32 km strip
- UTM zone: 32N (EPSG:32632), single-zone
- Output extent: 3942 × 18674 px at 5×10 m posting → ~19.7 M valid velocity pixels
- Frame: OPERA F31178 (mentioned in v1.0 narrative; not used because EGMS L2a is the EU reference, not OPERA DISP-S1)

### Stable-mask data sources (Natural Earth coastline / WorldCover / water bodies)

**Per CONTEXT D-Claude's-Discretion: Natural Earth + WorldCover (same as Phase 3 SoCal).**

**Verified data availability:**
- **Natural Earth coastlines:** `subsideo.data.natural_earth.load_coastline_and_waterbodies(bbox)` is implemented and uses cartopy's auto-download from `naturalearth.s3.amazonaws.com`. Bologna bbox `[11.227, 12.402, 44.457, 44.785]` is well inland — closest coastline is the Adriatic at Ravenna (~50 km east of the burst centre). The 5 km coastline buffer per D-06 is **near-irrelevant** for Bologna (matches CONTEXT D-Claude's-Discretion observation).
- **Natural Earth lakes (water bodies):** Po river (large channel) + small reservoirs in the Apennine foothills (south part of burst). Lake Garda (~30 km north) and Lake Maggiore (~150 km west) are well outside the burst.
- **WorldCover class 60 (bare/sparse):** Bologna burst is dominated by **WorldCover class 40 (cropland)** in the Po plain + **class 10 (tree cover)** + **class 50 (built-up)**. Class 60 (bare/sparse vegetation) is essentially **nonexistent** in the Po plain — the Bologna stable-mask via class 60 alone will produce a near-empty mask.
- **Po plain reservoirs:** Natural Earth `lakes` 10m resolution may miss small Po-plain reservoirs (<1 km²) but the 500 m water buffer covers the channel network well.

**RISK FLAG (carry into plan-phase):** the Phase 3 `build_stable_mask(worldcover, slope_deg, coastline, waterbodies, ...)` requires class 60 pixels. **Bologna may produce <100 stable pixels** — the same threshold that triggers a `BLOCKER` in Phase 3 SoCal/Iberian. If Bologna produces an empty mask, the eval script needs to either:
1. **Loosen** class filter to include other classes (class 30 grassland, class 20 shrubland) — but this is per-AOI tuning (PITFALLS P2.1 anti-pattern; CONTEXT D-06 forbids it).
2. **Surface as BLOCKER** explicitly — matches Phase 3 D-11 BLOCKER discipline. CONCLUSIONS narrative documents the empty-mask outcome.
3. **Use OSM (alternative)** — CONTEXT D-Claude's-Discretion says "revisit to OSM if buffer exclusion is too coarse/fine" but the issue here is class 60 ABSENCE, not buffer.

**Recommendation for plan-phase:** pre-validate Bologna stable_mask in a small probe before committing to the 6-h budget. If <100 px, surface as a BLOCKER in metrics.json (`cell_status="BLOCKER"`) with an honest CONCLUSIONS sub-section. Do NOT loosen the class filter — the M1 anti-pattern (per-AOI mask tuning to pass) is exactly what Phase 3 D-11 forbids.

**Plan-phase decision lever:** Use `eval-cslc-selfconsist-eu/metrics.json` (Phase 3 EU = Iberian, not Bologna) as a sanity check that the stable-mask pipeline works on inland EU. If Iberian Meseta-North (which IS bare-sparse-bedrock per Phase 3 narrative) produced 100+ stable pixels, the Bologna empty-mask outcome is a Bologna-specific landscape fact, not a pipeline bug.

### Coherence input (sequential 12-day from S1A+S1B cross-constellation stack)

**Verified from `eval-disp-egms/disp/dolphin/unwrapped/`:** 39 unwrapped IFGs from a 19-epoch stack. Filename pattern uses the 6-day effective cadence (S1A+S1B cross-constellation):
- `20210103_20210109.unw.tif` (6-day pair)
- `20210109_20210115.unw.tif` (6-day pair)
- `20210103_20210121.unw.tif` (18-day, N-step pair from network)
- ...

**For D-07 sequential 12-day filter:** parse dates from filenames; keep pairs where `(sec - ref).days ∈ [11, 13]`. Bologna 2021 H1 is dual-sat era; sequential pairs span both 6-day (same-sat) and 12-day (cross-sat) baselines. CONTEXT D-07 says "sequential 12-day pairs still constructed for coherence-stack consistency with SoCal" — so the eval script forms 12-day baseline pairs even though the sensing cadence is 6-day. If the 19-epoch stack at strict 12-day pairs yields fewer than expected, plan-phase commits whether to:
- Use ALL sequential pairs regardless of baseline (6-day OR 12-day), giving N-1 = 18 pairs.
- Use ONLY 12-day pairs (matches SoCal methodology), giving fewer pairs depending on cadence.

**Recommendation:** the simpler path is "all N-1 sequential pairs" (consecutive epochs in time-sorted order, regardless of 6-day vs 12-day baseline). This is what `_compute_ifg_coherence_stack` in `run_eval_cslc_selfconsist_nam.py:546-550` does (`for path_next in hdf5_paths[1:]`). For SoCal with strict 12-day cadence, this gives the same answer either way; for Bologna it gives 18 pairs at mixed 6/12-day baselines — which CONTEXT D-07 says is acceptable ("sequential 12-day pairs still constructed for coherence-stack consistency"). Plan-phase commits.

---

## Brief + CONCLUSIONS + docs/validation_methodology.md §3

### Brief structure (4 candidates × 4 columns)

**File:** `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md`
**Author:** Claude (research output) drafted in plan-phase; user reviews + greenlights before Phase 4 close commit (D-16).
**Length:** 150–250 LOC, single dense markdown page.

**Skeleton:**

```markdown
# DISP Unwrapper Selection Scoping Brief — v1.1-research handoff

**Date stamp:** YYYY-MM-DD (Phase 4 close)
**Audience:** Future contributor picking up the DISP-V2-01 follow-up milestone
**Status:** Scoping brief; NOT a plan. Candidates proposed; success criteria
proposed. The follow-up milestone commits.

## Context

Phase 4 of v1.1 ran the existing dolphin/PHASS pipeline against:
- N.Am. SoCal `t144_308029_iw1` (15 epochs, Jan-Jun 2024, 14 sequential 12-day IFGs)
- EU Bologna `t117_249422_iw2` (19 epochs, Jan-Jun 2021, ~18 sequential pairs)

**Reference-agreement (block_mean adapter, fresh):**
- N.Am. vs OPERA DISP-S1 30m: r=X.XX, bias=±X.X mm/yr, RMSE=X.X mm/yr, N=XX,XXX
- EU vs EGMS L2a PS: r=X.XX, bias=±X.X mm/yr, RMSE=X.X mm/yr, N=XX,XXX

**Product-quality (CALIBRATING):**
- N.Am.: coherence_med_of_persistent=0.887 (cached from Phase 3), residual=±X.X mm/yr (fresh from dolphin)
- EU: coherence_med_of_persistent=X.XX (fresh), residual=±X.X mm/yr (fresh)

**Ramp attribution:**
- N.Am.: attr=phass / orbit / mixed / inconclusive (auto: aggregate sigma=X.X°, coh-corr=X.XX)
- EU: attr=... (auto: aggregate sigma=X.X°, coh-corr=X.XX)

(Continuity note: v1.0 numbers using `Resampling.bilinear` were r=0.0365 / bias=+23.62 mm/yr (N.Am.) and r=0.32 / bias=+3.35 mm/yr (EU) — see CONCLUSIONS_DISP_*.md v1.0 baseline preamble.)

## Candidate approaches

| # | Approach | Description | Success criterion | Compute tier | Dep delta |
|---|----------|-------------|-------------------|--------------|-----------|
| 1 | PHASS + post-deramping | Keep PHASS unwrapper; subtract per-IFG planar-ramp fit BEFORE dolphin's network inversion. Re-runs from cached unwrapped IFGs. | r > 0.5 OR ramp magnitude < 1.0 rad on all IFGs (current Bologna ramp ~5.5 rad) | S — post-process only (~5 min/cell) | numpy lstsq (already in dolphin); no new conda packages |
| 2 | SPURT native | Switch dolphin's `unwrap_method` from PHASS to SPURT (graph-based unwrapper for large grids, designed for OPERA DISP). One-line config. | r > 0.7 (intermediate target) AND no PHASS-class planar ramps in `fit_planar_ramp` output | M — re-unwrap from cached IFGs (~30 min/cell, dolphin handles parallel jobs) | None (SPURT is part of dolphin 0.42.5; conda-forge already shipped) |
| 3 | tophu + SNAPHU multi-scale tiled | Use tophu's tile-based decomposition (3x3 tiles, 30m downsample factor) wrapping SNAPHU. Empirically validated for OPERA DISP large-scale. | r > 0.85 AND PASS reference-agreement gates on at least one of (N.Am., EU) | L — re-unwrap from cached IFGs at multi-scale (~60 min/cell, M3 Max parallel) | tophu 0.2.1 + snaphu 0.4.1 conda-forge (already in conda-env.yml; v1.0 had hand-pip-install issue) |
| 4 | 20×20 m fallback multilook | Multilook CSLC stack to 20×20 m BEFORE phase linking. Reduces per-IFG pixel count by ~6× (5×10 → 20×20), makes any unwrapper tractable. | PASS reference-agreement gate at 30m comparison after multilook (PASS = the v1.0 PROJECT.md bar of r>0.92, bias<3) | L — re-run dolphin from CSLC stack with downsample option (~3 h/cell cold) | None (dolphin native multilook config); only adds compute |

## Attribution-driven prioritisation (per CONTEXT D-14)

If Phase 4 ramp_attribution = 'phass' → all 4 candidates remain viable; prioritise (1) for fastest signal, (2) for production fix.
If 'orbit' → candidates (1) + (2) become lower-priority (don't address orbit-state-vector errors); diagnostic (b) POEORB swap re-prioritises.
If 'tropospheric' → all candidates lower-priority; diagnostic (c) ERA5 toggle re-prioritises (DISP-V2-02).
If 'mixed' or 'inconclusive' → diagnostic (b) + (c) BEFORE candidate evaluation.

## Out of scope for this brief

- MintPy SBAS as a 5th candidate (intentional 4-candidate framing per CONTEXT D-15)
- ERA5 tropospheric correction integration (DISP-V2-02; folded as secondary)
- Production unwrapper choice (this brief proposes; the follow-up milestone commits)

## Sources

- v1.0 CONCLUSIONS: `CONCLUSIONS_DISP_N_AM.md` §5.1, `CONCLUSIONS_DISP_EU.md` §4.3
- Phase 4 metrics.json: `eval-disp/metrics.json`, `eval-disp_egms/metrics.json`
- Methodology: `docs/validation_methodology.md` §3 (multilook ADR)
```

### CONCLUSIONS append (4 new sub-sections per cell + rename)

**Files:**
- `CONCLUSIONS_DISP_N_AM.md` — append v1.1 sections (existing v1.0 §1–10 preserved as preamble)
- `CONCLUSIONS_DISP_EU.md` ← rename from `CONCLUSIONS_DISP_EGMS.md` via `git mv`. Existing v1.0 §1–10 preserved as preamble.

**v1.1 sub-sections (per file, appended after the v1.0 §10 "Status"):**

```markdown
---

# v1.1 Update (Phase 4) — YYYY-MM-DD

## 11. Product Quality (CALIBRATING)

### 11.1 Coherence (sequential 12-day, boxcar 5×5)
| Stat | Value | Source | Criterion | Verdict |
|------|-------|--------|-----------|---------|
| `coherence_median_of_persistent` | 0.XX | phase3-cached / fresh | > 0.7 | CALIBRATING |
| `coherence_mean` | 0.XX | ... | (informational) | — |
| `coherence_median` | 0.XX | ... | (informational) | — |
| `coherence_p25` / `p75` | 0.XX / 0.XX | ... | (informational) | — |
| `persistently_coherent_fraction` | 0.XX | ... | (informational) | — |

### 11.2 Residual mean velocity (dolphin output, frame_anchor=median)
| Stat | Value | Criterion | Verdict |
|------|-------|-----------|---------|
| `residual_mm_yr` | ±X.X | < 5 mm/yr | CALIBRATING |
| Stable-mask pixels | XX,XXX | (sanity) | — |

## 12. Reference Agreement (BINDING)

| Metric | Value | Criterion | Verdict |
|--------|-------|-----------|---------|
| Pearson r | 0.XX | > 0.92 | PASS / FAIL |
| `bias_mm_yr` | ±X.X | < 3 mm/yr | PASS / FAIL |
| `rmse_mm_yr` | X.X | (informational) | — |
| Sample count | XX,XXX | — | — |

**Comparison method:** `prepare_for_reference(method="block_mean")` (CONTEXT D-02 + ADR §3 in `docs/validation_methodology.md`).

**Continuity with v1.0:** the v1.0 numbers using `Resampling.bilinear` (the ad-hoc multilook in v1.0 Stage 9) were r=0.0365 / bias=+23.62 mm/yr / RMSE=59.56 mm/yr (this cell). The Phase 4 numbers above use the same dolphin output but the new block_mean adapter; the ~XX% delta vs v1.0 is the kernel-choice effect (CONTEXT D-Claude's-Discretion observation that block_mean is the conservative floor).

## 13. Ramp Attribution

### 13.1 Per-IFG ramp parameters (sortable by magnitude)
| ifg_idx | ref_date | sec_date | magnitude_rad | direction_deg | coherence_mean |
|---------|----------|----------|---------------|---------------|----------------|
| ... | (top 5 by magnitude) | ... | ... | ... | ... |
| ... | (rest sorted) | ... | ... | ... | ... |

### 13.2 Aggregate
| Stat | Value | Cutoff | Implication |
|------|-------|--------|-------------|
| `mean_magnitude_rad` | X.X | (informational) | — |
| `direction_stability_sigma_deg` | X.X | < 30° | direction stable / random |
| `magnitude_vs_coherence_pearson_r` | X.XX | > 0.5 | coh-correlated / not |
| `n_ifgs` | NN | — | — |

### 13.3 Auto-attribute label
**Label:** `phass` / `orbit` / `mixed` / `inconclusive`
**Rule:** [direction sigma X.X°] [< 30° → orbit-class | >= 30° → not orbit-class]; [coh-correlation X.XX] [> 0.5 → phass-class | <= 0.5 → not phass-class]; combined → label.

### 13.4 Diagnostic deferrals
- (b) POEORB swap on RESORB epochs: not run because all epochs in this stack are POEORB-era.
- (c) ERA5 toggle: not run because pyaps3 ERA5 path is not enabled in current pipeline (DISP-V2-02).

### 13.5 Human review note
> Automated attribution: <label>.
> Reviewed: <agreed/disagreed/refined to X> — <reasoning>.

## 14. DISP Unwrapper Selection — Handoff

See `.planning/milestones/v1.1-research/DISP_UNWRAPPER_SELECTION_BRIEF.md` for the candidate-prioritisation handoff. The four candidates (PHASS+deramping, SPURT native, tophu-SNAPHU tiled, 20×20 m fallback) each carry a success criterion derived from this cell's reference-agreement FAIL numbers + ramp-attribution label.
```

### §3 ADR doc-section (5-part PITFALLS+FEATURES dialogue)

**File:** `docs/validation_methodology.md` — append after existing §2 (verified ends at line 246; §1 + §2 are Phase 3 work; Phase 4 owns §3 only per Phase 3 D-15 append-only).

**Skeleton (per CONTEXT D-03 5-part structure):**

```markdown
## 3. DISP comparison-adapter design — multilook method choice

**TL;DR:** `subsideo.validation.compare_disp.prepare_for_reference()` requires
an explicit `method=` argument selected from `Literal["gaussian", "block_mean",
"bilinear", "nearest"]`. Phase 4 eval scripts pass `method="block_mean"` —
the conservative kernel that doesn't inflate reference-agreement r through
kernel artefact. Switching the kernel post-measurement requires CONCLUSIONS-
level documentation per the criterion-immutability principle.

### 3.1 Problem statement

subsideo's native DISP velocity is at 5 m × 10 m posting (OPERA CSLC spec).
The two reference products it must compare against — OPERA DISP-S1 (30 m × 30 m)
and EGMS L2a PS (point cloud at PS coordinates) — live on different grids.
Comparing requires multilooking subsideo's velocity onto the reference grid.
The multilook method is a comparison-adapter design choice that materially
changes the reported `correlation` and `bias_mm_yr` values (PITFALLS P3.1
warning sign: r differs by > 0.03 when switching between kernels).

### 3.2 PITFALLS P3.1 argument — Gaussian σ=0.5×reference is physically consistent

PITFALLS P3.1 (`.planning/research/PITFALLS.md` §P3.1) argues that OPERA's 30 m
DISP output is itself produced from multilooked interferograms with an
effective Gaussian smoothing kernel. Multilooking subsideo's 5×10 m output
to 30 m via `gaussian_filter(σ_pix=15m/native_spacing)` then nearest-sampling
onto the reference grid is the apples-to-apples comparison: both fields
carry the same effective spatial-frequency content. Block-mean (the
"averaging" rasterio resampler) under-smooths by truncating high frequencies
discretely rather than rolling them off; bilinear smooths but blurs
discontinuities; nearest preserves sub-pixel offsets and aliases.

### 3.3 FEATURES anti-feature argument — block_mean is the kernel-flattery floor

FEATURES (`.planning/research/FEATURES.md` lines 71 + 142–143 anti-feature
table) argues the inverse: kernel choice can inflate reported r because
each kernel rolls off velocity-difference power differently. Picking the
kernel that gives the highest r is a kernel-choice attack surface — the
reported r in `results/matrix.md` becomes a function of "we picked the
nicest kernel" rather than "the chains agree at the comparison cell size."
Block-mean (`Resampling.average` in rasterio) is the conservative floor:
it matches what OPERA itself uses for its CSLC multilook, and its
high-frequency truncation is the most pessimistic of the four kernels for
reference-agreement r. Anyone arguing Gaussian gives a higher r can rerun
with `method="gaussian"`; we don't pre-commit to the optimistic kernel for
the published metric.

### 3.4 Decision: block_mean as the eval-script default

`subsideo.validation.compare_disp.prepare_for_reference()` accepts all four
kernels — both arguments above are correct on their own terms; the choice is
a posture, not a science argument (CONTEXT 04-CONTEXT.md §Specifics). The
**eval-script default** is `block_mean` because:

1. **Floor behaviour** — block_mean's reported r is the most pessimistic of
   the four. If we PASS at block_mean, we PASS at any kernel; if we FAIL at
   block_mean, the FAIL is unambiguous (not a kernel artefact).
2. **OPERA parity** — OPERA's own multilook in the CSLC pipeline is a
   block-average. Same kernel = same effective smoothing = honest comparison
   of two block-averaged products.
3. **No goalpost-moving (M1)** — switching to Gaussian post-measurement
   because it gives a higher r is exactly the M1 target-creep anti-pattern
   `criteria.py` is designed to prevent. A future PR titled "switch to
   Gaussian for higher r" would be self-evidently wrong.

### 3.5 Constraint: kernel choice is comparison-method, not product-quality

The kernel choice is **a comparison-method decision**, NOT a product-quality
decision. Production `run_disp()` is unchanged at native 5×10 m (DISP-05).
The eval script's `REFERENCE_MULTILOOK_METHOD: Literal["block_mean"] = "block_mean"`
constant lives at module top so it's auditable in the git diff (mirrors the
Phase 1 D-11 `EXPECTED_WALL_S` pattern). Switching kernels post-measurement
requires:

1. A PR diff to the constant (visible in `git log --grep="REFERENCE_MULTILOOK_METHOD"`).
2. A CONCLUSIONS sub-section documenting the new kernel's measured r/bias and
   citing this §3.5 constraint.

There is no env-var override or CLI flag. The kernel is a published-artifact
parameter; it must be code-visible.

(For the alternative-kernel rerun e.g. `method="gaussian"` for kernel-comparison
study: it's deferred to the Unwrapper Selection follow-up milestone per
CONTEXT 04-CONTEXT.md §Deferred. CONCLUSIONS may cite "block_mean reference
shows r=X; the same data with method='gaussian' would yield r=Y" as a v1.2/v2
footnote.)
```

---

## Validation Architecture (test strategy — informs Dimension 8 even with Nyquist disabled)

**Note:** `.planning/config.json` may have `nyquist_validation: false` for this milestone (Phase 3 narrative did not run a fresh Nyquist gate). The test surface below is for Phase 4 plan-phase to consume regardless.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 (already installed; `[dev]` extra in pyproject.toml) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `--cov=subsideo --cov-report=term-missing`, 80% coverage minimum |
| Quick run command | `micromamba run -n subsideo pytest tests/unit/ -x --no-cov` |
| Full suite command | `micromamba run -n subsideo pytest -m "not slow and not integration and not validation"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DISP-01 | `prepare_for_reference` rejects None / missing method | unit | `pytest tests/product_quality/test_prepare_for_reference.py::test_method_none_raises -x` | ❌ Wave 0 (new file) |
| DISP-01 | `prepare_for_reference` accepts each of 4 methods × each of 3 forms (12 cases) on small synthetic 100×100 raster | unit | `pytest tests/product_quality/test_prepare_for_reference.py -x` | ❌ Wave 0 |
| DISP-01 | Adapter never writes back to `native_velocity` (input bytes unchanged after call) | unit | `pytest tests/product_quality/test_prepare_for_reference.py::test_no_write_back -x` | ❌ Wave 0 |
| DISP-02 | `fit_planar_ramp` recovers known-magnitude / known-direction ramp from synthetic 256×256 IFG | unit | `pytest tests/product_quality/test_fit_planar_ramp.py::test_recovers_known_ramp -x` | ❌ Wave 0 |
| DISP-02 | `fit_planar_ramp` returns NaN when valid pixels < 100 | unit | `pytest tests/product_quality/test_fit_planar_ramp.py::test_insufficient_pixels -x` | ❌ Wave 0 |
| DISP-03 | `auto_attribute_ramp` returns each of 4 branches at cutoff edges | unit | `pytest tests/product_quality/test_auto_attribute_ramp.py -x` | ❌ Wave 0 |
| DISP-03 | `DISPCellMetrics` round-trips through `model_dump_json` + `model_validate_json` | unit | `pytest tests/product_quality/test_disp_cell_metrics_schema.py::test_round_trip -x` | ❌ Wave 0 |
| DISP-03 | `matrix_writer._render_disp_cell` produces expected pq_col + ra_col on a fixture metrics.json | unit | `pytest tests/reference_agreement/test_matrix_writer_disp.py -x` | ❌ Wave 0 |
| DISP-04 | (Brief content) — no automated test (manual review per D-16) | manual | n/a (user reviews + greenlights) | n/a |
| DISP-05 | `run_disp()` unchanged: existing test suite for `products/disp.py` still passes | regression | `pytest tests/unit/test_disp.py -x` | ✅ |
| End-to-end | N.Am. eval-disp script (warm cache) produces a valid DISPCellMetrics metrics.json | validation | `pytest -m validation tests/test_run_eval_disp_warm.py` | ❌ Wave 0 (eval-script smoke) |
| End-to-end | EU eval-disp-egms script (warm cache) produces a valid DISPCellMetrics metrics.json | validation | `pytest -m validation tests/test_run_eval_disp_egms_warm.py` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/product_quality/ -x --no-cov -k "prepare_for_reference or fit_planar_ramp or auto_attribute or disp_cell"` (~5 s)
- **Per wave merge:** `pytest tests/ -m "not slow and not integration and not validation"` (~30 s)
- **Phase gate:** Full suite green + `make eval-disp-nam` + `make eval-disp-eu` (warm) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/product_quality/test_prepare_for_reference.py` — covers DISP-01 (12 method×form cases + no-default + no-write-back)
- [ ] `tests/product_quality/test_fit_planar_ramp.py` — covers DISP-02 algorithm correctness (synthetic ramp recovery + NaN edge case)
- [ ] `tests/product_quality/test_auto_attribute_ramp.py` — covers DISP-03 attribution rule (4 branches × cutoff edges)
- [ ] `tests/product_quality/test_disp_cell_metrics_schema.py` — covers DISP-03 schema round-trip
- [ ] `tests/reference_agreement/test_matrix_writer_disp.py` — covers matrix-writer rendering branches
- [ ] `tests/test_run_eval_disp_warm.py` + `tests/test_run_eval_disp_egms_warm.py` — `@pytest.mark.validation` eval-script smoke (warm cache)

**Framework install:** none (pytest, scipy, rasterio, xarray all already installed via `pyproject.toml [validation]` extra; conda env `subsideo` already active).

---

## Pitfalls / open risks for the planner

### Kernel-comparison risk + how D-04 constant guards against it

The single biggest semantic risk in Phase 4 is **kernel-choice contamination**: someone re-runs with `method="gaussian"`, sees a higher r, and tries to publish the gaussian number as the "real" reference-agreement. CONTEXT D-04 + §3.5 of `docs/validation_methodology.md` explicitly forbid this: kernel switches require a CONCLUSIONS-documented PR.

**Mitigation in code:**
- `REFERENCE_MULTILOOK_METHOD: Literal["block_mean"] = "block_mean"` at module top — single source of truth. Supervisor AST-parses (whitelist permits literal Constant assignments).
- `prepare_for_reference()` raises `ValueError` if `method=None` — no implicit defaulting that hides the choice.
- `matrix_writer` echoes the method choice in the rendered cell? **No** — the cell only shows the resulting numbers; the audit trail is the constant in the eval script + the meta.json `git_sha`. Plan-phase may add the method to `meta.json.input_hashes` as a parameter hash for stronger audit.

### NaN handling in fit_planar_ramp (full-burst vs masked)

`fit_planar_ramp` uses the convention `valid = np.isfinite(z) & (z != 0)`. dolphin's unwrapped IFGs are zero-outside-valid-data (NOT NaN). If a future dolphin release switches to NaN-fill, the `(z != 0)` clause becomes redundant; if a future release leaves uninitialised garbage, both clauses are needed. The current convention is safe for both.

**Open question for plan-phase:** does `fit_planar_ramp` accept a `mask` parameter that restricts to stable-mask pixels (CONTEXT D-Claude's-Discretion says "full-burst least-squares plane fit")? Recommendation: keep `mask=None` as default + accept caller-supplied masks (signature already supports it). Eval scripts pass `mask=None` per D-Claude's-Discretion.

### Bologna stable-mask coverage gaps if WorldCover doesn't include Po reservoirs

See §"Bologna-specific / Stable-mask data sources." Bologna burst is in the Po plain (cropland-dominated). WorldCover class 60 (bare/sparse vegetation) is largely absent. **The Bologna stable-mask may produce <100 valid pixels**, which Phase 3 D-11 says triggers a `BLOCKER` cell.

**Plan-phase actions:**
1. Pre-validate Bologna stable-mask in a probe before committing the 6-h budget.
2. If <100 px, surface as `cell_status="BLOCKER"` in metrics.json with an honest CONCLUSIONS sub-section.
3. Do NOT loosen the class filter — that's the M1/P2.1 anti-pattern.

If Bologna is BLOCKER, the Phase 4 success outcome shifts to "1 cell (N.Am.) at MIXED + 1 cell (EU) at BLOCKER." The brief still lands per D-16 (the BLOCKER signal IS information for the follow-up milestone).

### EXPECTED_WALL_S overrun handling (raise budget vs fail-loudly)

D-Claude's-Discretion 6 h cap. Warm re-run is ~30 min/cell (FEATURES line 73), cold is ~3 h/cell. Supervisor wall-time check is `wall > 2 * expected_wall AND cache stale > GRACE_WINDOW_S` (supervisor.py:270) — so 12 h with no cache progress before abort.

**Open question for plan-phase:** if first run blows past 6 h cap (e.g., a SAFE re-download triggered by hash-mismatch on cached file), do we (a) raise EXPECTED_WALL_S to 8 h or 12 h, or (b) fail-loudly and investigate? Recommendation: **fail-loudly first**. Phase 4 is supposed to be warm; an overrun signals cache invalidation that needs investigation, not budget tuning.

### Provenance flag drift (Phase 3 cache modified after DISP eval)

If `eval-cslc-selfconsist-nam/metrics.json` is regenerated between the DISP-N.Am. eval run and the matrix-writer render, the `coherence_source: 'phase3-cached'` flag is misleading (the cached value at read time differs from what was written). Plan-phase commits whether to:
- Capture the cached metrics SHA in `meta.json.input_hashes["phase3_cslc_metrics_sha"]` for audit trail.
- Re-fetch on every run (defeats the cache-reuse optimization).

**Recommendation:** capture SHA in `meta.json.input_hashes`; if SHA changes between runs, matrix-writer surfaces a STALE-FLAG warning (mirror Phase 3 D-15 SoCal cache integrity check pattern). Plan-phase decides exact STALE-FLAG rendering.

### Eval cache directory naming inconsistency (`eval-disp_egms` vs `eval-disp-egms`)

**Verified on disk:** the actual EU cache dir is `eval-disp-egms/` (hyphen). The matrix manifest entry at `results/matrix_manifest.yml` says `cache_dir: eval-disp_egms` (underscore) and `metrics_file: eval-disp_egms/metrics.json`.

**Plan-phase action:** decide between (a) renaming the disk cache dir to match the manifest (`mv eval-disp-egms eval-disp_egms`), or (b) editing the manifest entry to `eval-disp-egms` (matches disk; matches Makefile `eval-disp-eu` target which calls `run_eval_disp_egms.py`). The Makefile target name and the supervisor's `_cache_dir_from_script` (which would derive `eval-disp-egms` from `run_eval_disp_egms.py` per `_cache_dir_from_script`'s `eval-{stem.removeprefix('run_eval_')}` rule = `eval-disp_egms` BUT the script name has `_egms` not `-egms`).

**Recommendation:** edit the manifest to match disk (`eval-disp-egms`). Lower-risk than a rename + reduces confusion for anyone tracing eval-script → cache-dir.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| numpy | fit_planar_ramp lstsq, all schema | ✓ | >=1.26 (pinned <2 per ENV-01) | — |
| scipy | gaussian_filter, circstd | ✓ | >=1.13 | — |
| rasterio | reproject, sample, raster I/O | ✓ | 1.5.0 | — |
| xarray | DataArray reference_grid form | ✓ | >=2024.11 | — |
| rioxarray | xr.DataArray CRS attach for form (b) | ✓ | 0.22.0 | — |
| pyproj | Transformer.from_crs for point sampling | ✓ | 3.7.2 | — |
| pydantic | DISPCellMetrics + RampAttribution + PerIFGRamp | ✓ | >=2.7 | — |
| dolphin | Reading velocity.tif + unwrapped IFGs (already cached, no fresh dolphin call) | ✓ | 0.42.5 | — |
| pyaps3 | ERA5 (diagnostic c — DEFERRED per D-09) | ✗ (not configured) | — | Diagnostic (c) skipped per D-09 |
| EGMStoolkit | EGMS L2a CSV download (already cached) | ✓ | 0.2.15 (cached output) | — |
| earthaccess | OPERA DISP-S1 reference download (already cached) | ✓ | 0.17.0 | — |
| asf-search | S1 SLC search (warm path: not used; CSLCs already produced) | ✓ | 12.0.6 | — |

**Missing dependencies with no fallback:** None. Phase 4 is fully warm-path-runnable; the warm path requires zero network access.

**Missing dependencies with fallback:** pyaps3 (ERA5) — diagnostic (c) explicitly deferred per D-09; no Phase 4 blocker.

---

## Sources

### Primary (HIGH confidence)
- Filesystem inspection (verified 2026-04-25):
  - `eval-disp/disp/dolphin/timeseries/velocity.tif` (22 MB, 3959×17881 float32)
  - `eval-disp-egms/disp/dolphin/timeseries/velocity.tif` (104 MB, 3942×18674 float32)
  - `eval-disp/disp/dolphin/unwrapped/*.unw.tif` (39 files)
  - `eval-disp-egms/disp/dolphin/unwrapped/*.unw.tif` (39 files)
  - `eval-cslc-selfconsist-nam/metrics.json` (5 KB; SoCal coherence schema verified)
- Source code (verified 2026-04-25):
  - `src/subsideo/validation/compare_disp.py` (380 LOC; `compare_disp` line 145 = `Resampling.bilinear`; `compare_disp_egms_l2a` lines 325–326 = `src.sample()`; `_load_egms_l2a_points` shape verified)
  - `src/subsideo/validation/selfconsistency.py` (327 LOC; `coherence_stats` 6 stats; `residual_mean_velocity` `frame_anchor='median'`; `compute_residual_velocity` lambda formula verified)
  - `src/subsideo/validation/stable_terrain.py` (208 LOC; `build_stable_mask` signature verified)
  - `src/subsideo/validation/matrix_schema.py` (449 LOC; Pydantic v2 conventions verified)
  - `src/subsideo/validation/matrix_writer.py` (475 LOC; `_render_cslc_selfconsist_cell` pattern verified)
  - `src/subsideo/validation/criteria.py` (262 LOC; DISP gates already shipped — Phase 4 makes ZERO edits)
  - `src/subsideo/validation/supervisor.py` (331 LOC; AST-parse rules + watchdog logic verified)
  - `src/subsideo/validation/harness.py` (5 helpers; lazy-import discipline verified)
  - `run_eval_disp.py` (859 LOC; Stage 9 ad-hoc reproject lines 610–632 verified)
  - `run_eval_disp_egms.py` (566 LOC; Stage 9 calls `compare_disp_egms_l2a` line 550 verified)
  - `run_eval_cslc_selfconsist_nam.py` (Phase 3 reference for stable-mask + IFG-stack pattern)
- Phase 4 CONTEXT (`.planning/phases/04-disp-s1-comparison-adapter-honest-fail/04-CONTEXT.md`) — 21 locked decisions D-01..D-21
- Research docs (verified 2026-04-25):
  - `.planning/research/PITFALLS.md` §P3.1 (multilook physics), §P3.2 (ramp-attribution methodology)
  - `.planning/research/FEATURES.md` lines 67–76, 142–143 (anti-feature framing)
  - `.planning/research/ARCHITECTURE.md` §3 (`prepare_for_reference` placement rationale)
  - `.planning/research/SUMMARY.md` lines 168–172 + 100–110, 220–230 (Phase 4 row + research flags)
- v1.0 CONCLUSIONS (verified 2026-04-25):
  - `CONCLUSIONS_DISP_N_AM.md` (258 LOC; SoCal r=0.0365 / bias=+23.62 / RMSE 59.56; PHASS planar-ramp evidence)
  - `CONCLUSIONS_DISP_EGMS.md` (304 LOC; Bologna r=0.32 / bias=+3.35 / RMSE 5.14)
- `docs/validation_methodology.md` §1 + §2 (verified ends at line 246; Phase 4 appends §3 only)

### Secondary (MEDIUM confidence)
- `rasterio.warp.Resampling.average` semantics: GDAL averaging filter (validated by rasterio docs + Phase 4 D-02 reasoning).
- `scipy.ndimage.gaussian_filter` non-NaN-aware behaviour: documented stdlib quirk (replace-with-zero workaround).
- `scipy.stats.circstd` for circular standard deviation on degree angles: standard recipe in InSAR ramp-direction analysis.
- Sentinel-1 C-band wavelength `0.05546576 m`: hardcoded in `compare_disp.py:33` and `selfconsistency.py:321` — verified consistent across both consumers.

### Tertiary (LOW confidence)
- Bologna stable-mask coverage assumption: WorldCover class 60 is sparse in Po-plain croplands — based on geographic reasoning, not direct on-disk verification of `eval-cslc-selfconsist-eu/worldcover/` tiles. Plan-phase MUST probe before budget commit.
- Filename pattern `<ref_date>_<sec_date>.unw.tif` for sequential-vs-network classification: parsed via regex; assumes dolphin's filename convention is stable across versions (pattern verified on 39 files in each cache).
- `eval-disp-egms` vs `eval-disp_egms` (manifest vs disk) — verified disk = hyphen; manifest = underscore. Plan-phase MUST resolve.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every library version and signature verified against on-disk source code or pyproject.toml.
- Architecture: HIGH — `prepare_for_reference` placement, schema additions, matrix_writer dispatch all match research ARCHITECTURE §3 and Phase 1/3 precedent patterns.
- Library APIs: HIGH — rasterio.reproject + scipy.gaussian_filter + np.linalg.lstsq + rasterio.sample syntax all verified against existing usage in the codebase.
- Auto-attribute thresholds: MEDIUM — CONTEXT D-Claude's-Discretion gives starting cutoffs (30°, 0.5); plan-phase tunes if SoCal/Bologna numbers misclassify.
- Bologna stable-mask coverage: LOW — geographic reasoning only; plan-phase MUST probe.
- Pitfalls: HIGH — kernel-choice + NaN handling + Bologna mask + EXPECTED_WALL_S all anchored in CONTEXT and Phase 1/3 precedent.

**Research date:** 2026-04-25
**Valid until:** 2026-05-25 (30 days; codebase is stable, library versions pinned via conda env)

## RESEARCH COMPLETE
