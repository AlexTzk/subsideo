# Phase 3: CSLC-S1 Self-Consistency + EU Validation - Pattern Map

**Mapped:** 2026-04-23
**Files analyzed:** 14 (4 new files, 6 additive edits to existing modules, 2 new CONCLUSIONS, 1 new probe artifact, 1 new methodology doc)
**Analogs found:** 13 / 14 (1 NEW-no-analog: `docs/validation_methodology.md`)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/subsideo/validation/selfconsistency.py` | D-module (shared) | transform (additive edit: 6th stat key + new linear-fit helper) | Self (existing Phase 1 module) | exact-extension |
| `src/subsideo/validation/compare_cslc.py` | comparator (additive edit: new `compare_cslc_egms_l2a_residual` top-level fn) | request-response (PS sampling) | `compare_disp.compare_disp_egms_l2a` (lines 239–374) | role+flow match |
| `src/subsideo/validation/criteria.py` | registry (additive edit: add `gate_metric_key` field to 2 CALIBRATING entries) | config | Self (existing frozen-dataclass module) | exact-extension |
| `src/subsideo/validation/matrix_schema.py` | Pydantic schema (additive: 3 new types) | config | `BurstResult` + `RTCEUCellMetrics` (lines 158–306) | exact-extension |
| `src/subsideo/validation/matrix_writer.py` | renderer (additive: 2 new cell branches) | transform | `_is_rtc_eu_shape` + `_render_rtc_eu_cell` (lines 160–230) | exact-extension |
| `src/subsideo/validation/stable_terrain.py` | D-module (shared) | pure-function | Self (unchanged; signature-only reference) | unchanged |
| `src/subsideo/validation/harness.py` | plumbing (shared) | unchanged in Phase 3 | Self (5-helper module) | unchanged |
| `src/subsideo/validation/supervisor.py` | watchdog | unchanged | Self (Phase 1 subprocess wrapper) | unchanged |
| `run_eval_cslc_selfconsist_nam.py` (NEW at root) | eval script (entry point) | event-driven batch (per-AOI iterate → aggregate) | `run_eval_rtc_eu.py` (727 LOC) | exact pattern-match |
| `run_eval_cslc_selfconsist_eu.py` (NEW at root) | eval script (entry point) | event-driven batch (single-AOI + fallback + EGMS step) | `run_eval_rtc_eu.py` + `compare_disp.compare_disp_egms_l2a` | pattern+flow match |
| `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` (NEW at root) | docs | narrative | `CONCLUSIONS_CSLC_N_AM.md` + `CONCLUSIONS_RTC_EU.md` (multi-AOI) | role match |
| `CONCLUSIONS_CSLC_EU.md` (NEW at root) | docs | narrative | `CONCLUSIONS_CSLC_N_AM.md` (section structure) + `CONCLUSIONS_RTC_EU.md` (multi-number cell) | role match |
| `.planning/milestones/v1.1-research/cslc_selfconsist_aoi_candidates.md` (NEW) | probe artifact | docs | `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` | exact pattern-match |
| `docs/validation_methodology.md` (NEW) | methodology doc | narrative | **NO ANALOG** — first write per D-15 append-only policy | NEW |

---

## Pattern Assignments

### `src/subsideo/validation/selfconsistency.py` (D-module, additive extension)

**Analog:** Self (existing Phase 1 module; 165 LOC). Phase 3 adds `median_of_persistent` as 6th stat key + optional new `compute_residual_velocity(cslc_stack_paths, stable_mask)` linear-fit helper.

**Existing function window — the 10–20 line landing zone for the 6th key** (lines 77–101):

```python
    vals = per_pixel_mean[stable_mask]
    stats: dict[str, float] = {
        "mean": float(vals.mean()),
        "median": float(np.median(vals)),
        "p25": float(np.percentile(vals, 25)),
        "p75": float(np.percentile(vals, 75)),
    }

    # persistently_coherent_fraction = fraction of stable pixels whose
    # per-IFG coherence exceeds the threshold for EVERY IFG in the stack
    per_ifg_above = stack >= coherence_threshold
    all_ifgs_above = per_ifg_above.all(axis=0)  # (H, W)
    num_persistent = int((all_ifgs_above & stable_mask).sum())
    stats["persistently_coherent_fraction"] = float(num_persistent) / float(int(stable_mask.sum()))
    # [PHASE 3 INSERT HERE]
    # median_of_persistent = np.median(per_pixel_mean[all_ifgs_above & stable_mask])
    # stats["median_of_persistent"] = float(...)  # 0.0 if no persistent pixels
    return stats
```

**Existing docstring return-contract** (lines 55–60):

```python
    Returns
    -------
    stats : dict[str, float]
        Keys (exactly five): ``mean``, ``median``, ``p25``, ``p75``,
        ``persistently_coherent_fraction``. All values are Python floats.
```

**Rules to preserve:**
- Keyword-only parameter block (`*,`) already set — add nothing to the call signature; the 6th key is a return-dict addition only (CONTEXT D-01 "no shape change to function signature").
- Update the docstring `Returns` table from "Keys (exactly five)" to "Keys (exactly six)" and add `median_of_persistent` with its definition (per-pixel-mean coherence over the stack, restricted to pixels that are persistently coherent in every IFG).
- Empty-mask sentinel: return `0.0` for `median_of_persistent` in the `int(stable_mask.sum()) == 0` branch so the 6-key dict shape is invariant (matches lines 63–69 current behaviour).
- For `compute_residual_velocity(cslc_stack_paths, stable_mask) -> np.ndarray` (Claude's Discretion per CONTEXT D-Claude's-Discretion residual route): follow the pure-function module style — `loguru.logger` imports at top, lazy-import h5py/rasterio inside the function body, return `(H, W) float np.ndarray` velocity in mm/yr, not a float scalar (the existing `residual_mean_velocity` already reduces to scalar; the new helper produces the velocity raster input to that reduction).

---

### `src/subsideo/validation/compare_cslc.py` (comparator, additive new function)

**Analog:** `src/subsideo/validation/compare_disp.py` lines 187–374 (`_load_egms_l2a_points` + `compare_disp_egms_l2a`).

**PS-point sampling template — to mirror for `compare_cslc_egms_l2a_residual`** (lines 283–337):

```python
    with rasterio.open(velocity_path) as src:
        raster_crs = src.crs
        # Capture nodata while the dataset is still open; accessing src.nodata
        # after the ``with`` block exits raises RasterioIOError (CR-01).
        nodata = src.nodata
        points_proj = points.to_crs(raster_crs)

        # Clip to raster bounds before sampling to avoid wasted I/O
        left, bottom, right, top = src.bounds
        in_bounds = (
            (points_proj.geometry.x >= left)
            & (points_proj.geometry.x <= right)
            & (points_proj.geometry.y >= bottom)
            & (points_proj.geometry.y <= top)
        )
        points_in = points_proj[in_bounds].copy()
        ...
        xy = list(zip(points_in.geometry.x, points_in.geometry.y, strict=True))
        sampled = np.array([v[0] for v in src.sample(xy)], dtype=np.float64)

    if nodata is not None:
        sampled = np.where(sampled == nodata, np.nan, sampled)
```

**Cross-module loader reuse pattern** (lines 275–282):

```python
    df = _load_egms_l2a_points([Path(p) for p in egms_csv_paths], velocity_col=velocity_col)

    # Build PS points in EPSG:4326, then reproject to the velocity raster CRS
    points = gpd.GeoDataFrame(
        df,
        geometry=[Point(xy) for xy in zip(df["lon"], df["lat"], strict=True)],
        crs="EPSG:4326",
    )
```

**Reference-frame alignment anchor (P2.3)** — mirror `selfconsistency.residual_mean_velocity` lines 149–158:

```python
    if frame_anchor == "median":
        anchor = float(np.median(vals))
    ...
    residual = float((vals - anchor).mean())
```

**Rules to preserve:**
- Signature per CONTEXT D-12: `compare_cslc_egms_l2a_residual(our_velocity_raster: Path, egms_csv_paths: list[Path], stable_std_max: float = 2.0) -> float`. Returns a single scalar (mm/yr residual), NOT a `DISPValidationResult` — Phase 3 embeds this scalar into `ProductQualityResult.measurements["egms_l2a_stable_ps_residual_mm_yr"]` in the eval script, not into a new dataclass.
- Cross-module import: `from subsideo.validation.compare_disp import _load_egms_l2a_points` at the function body (NOT module top — the compare_disp private helper import lives inside `compare_cslc_egms_l2a_residual` to mark the cross-module dependency as load-bearing-only-here).
- Stable-PS filter discipline per D-12: `df[df['mean_velocity_std'] < stable_std_max]` — add a second column load (`mean_velocity_std`) that `_load_egms_l2a_points` does not currently return. Either (a) extend `_load_egms_l2a_points` to return `mean_velocity_std` when present (additive, safer), or (b) re-read the CSV inside the new function (not DRY). Prefer (a).
- Reference-frame alignment (P2.3): subtract stable-set median from our velocity BEFORE paired-residual, matching `selfconsistency.residual_mean_velocity` anchor pattern (the EGMS values are already reference-aligned by EGMS; our chain's are not).
- Return NaN (not raise) if n_valid < 100 paired samples — matches `compare_disp_egms_l2a` line 339 warning pattern.
- Module header docstring already references `CONCLUSIONS_CSLC_N_AM.md Section 5` and cross-version impossibility (lines 4–7). Do not edit that docstring; the new function's own docstring cites `docs/validation_methodology.md#cross-version-phase` once CSLC-06 lands (per PITFALLS P2.4 mitigation plan).

---

### `src/subsideo/validation/criteria.py` (registry, additive field on 2 entries)

**Analog:** Self — existing frozen-dataclass module. The two CALIBRATING CSLC entries (lines 107–125).

**Existing CALIBRATING CSLC entries — landing zone for `gate_metric_key` field** (lines 107–125):

```python
    # -- CSLC self-consistency CALIBRATING (Phase 1 D-04) --
    "cslc.selfconsistency.coherence_min": Criterion(
        name="cslc.selfconsistency.coherence_min", threshold=0.7, comparator=">",
        type="CALIBRATING", binding_after_milestone="v1.2",
        rationale=(
            "Stable-terrain sequential-IFG coherence bar -- first rollout Phase 3 "
            "(SoCal / Mojave / Iberian Meseta). Published C-band stable-terrain "
            "coherence is 0.75-0.85 per PITFALLS P2.2; 0.7 is starting bar. "
            "GATE-05: >=3 measured data points before BINDING promotion."
        ),
    ),
    "cslc.selfconsistency.residual_mm_yr_max": Criterion(
        name="cslc.selfconsistency.residual_mm_yr_max", threshold=5.0, comparator="<",
        type="CALIBRATING", binding_after_milestone="v1.2",
        rationale=(
            "Residual mean velocity on reference-frame-aligned stable terrain "
            "(PITFALLS P2.3) -- first rollout Phase 3. Tightening to 1-2 mm/yr "
            "as stacks lengthen beyond 6 months is v2 work (CSLC-V2-02)."
        ),
    ),
```

**Existing frozen dataclass shape** (lines 28–37):

```python
@dataclass(frozen=True)
class Criterion:
    """A single pass/fail threshold with provenance."""

    name: str
    threshold: float
    comparator: Literal[">", ">=", "<", "<="]
    type: Literal["BINDING", "CALIBRATING", "INVESTIGATION_TRIGGER"]
    binding_after_milestone: str | None
    rationale: str
```

**Rules to preserve:**
- Per CONTEXT D-04: add `gate_metric_key: str = 'median_of_persistent'` as a new field on `Criterion` with a default so the 11 non-CSLC-selfconsistency existing entries don't require edits. Field is consulted only by the CSLC-selfconsistency entries; default is irrelevant for BINDING/INVESTIGATION_TRIGGER rows.
- Field position: after `rationale` per dataclass forward-compat convention (defaults at end). Module-header comment "Coverage" (lines 16–21) stays unchanged — field addition is additive, not a new Criterion entry.
- Any change to `gate_metric_key` during Phase 3 calibration (D-04 escape valve) must be documented in the CONCLUSIONS "Calibration Changes" section; the Criterion value at the end of Phase 3 is the committed audit record.
- Frozen `@dataclass(frozen=True)` stays — ImmutabilityGate prevents threshold sliding.

---

### `src/subsideo/validation/matrix_schema.py` (Pydantic schema, additive 3 new types)

**Analog:** `BurstResult` + `RTCEUCellMetrics` in the same file (lines 158–306). Phase 3 adds `AOIResult` (mirrors `BurstResult`), `CSLCSelfConsistNAMCellMetrics` + `CSLCSelfConsistEUCellMetrics` (mirror `RTCEUCellMetrics`).

**`BurstResult` template for per-AOI row** (lines 158–252):

```python
class BurstResult(BaseModel):
    """Per-burst row inside RTCEUCellMetrics.per_burst (Phase 2 D-10)."""

    model_config = ConfigDict(extra="forbid")

    burst_id: str = Field(..., description="JPL-format burst ID, lowercase, e.g. 't144_308029_iw1'.")
    regime: Literal["Alpine", "Scandinavian", "Iberian", "TemperateFlat", "Fire"] = Field(
        ..., description="Terrain regime label..."
    )
    lat: float | None = Field(default=None, description="Centroid latitude (deg). None if DEM/bounds lookup failed.")
    max_relief_m: float | None = Field(default=None, description="Max relief (m)...")
    cached: bool = Field(default=False, description="True when the SAFE was reused from another eval cache...")
    status: Literal["PASS", "FAIL"] = Field(..., description="Per-burst verdict...")
    product_quality: ProductQualityResultJson | None = Field(default=None, description="Null for RTC in v1.1...")
    reference_agreement: ReferenceAgreementResultJson = Field(
        default_factory=ReferenceAgreementResultJson,
        description="Per-burst RMSE/correlation/bias_db measurements..."
    )
    investigation_required: bool = Field(default=False, description="...")
    investigation_reason: str | None = Field(default=None, description="...")
    error: str | None = Field(
        default=None,
        description="repr(exception) captured by per-burst try/except (D-06)..."
    )
    traceback: str | None = Field(default=None, description="traceback.format_exc()...")
```

**`RTCEUCellMetrics` template for multi-AOI aggregate** (lines 255–306):

```python
class RTCEUCellMetrics(MetricsJson):
    """RTC-EU multi-burst aggregate extending the base MetricsJson schema (D-09)."""

    pass_count: int = Field(..., ge=0, description="Count of bursts with status == 'PASS'.")
    total: int = Field(..., ge=1, description="Total number of bursts in per_burst...")
    all_pass: bool = Field(..., description="True when pass_count == total...")
    any_investigation_required: bool = Field(..., description="...")
    reference_agreement_aggregate: dict[str, float | str] = Field(
        default_factory=dict,
        description="Aggregate summary: worst_rmse_db (float), worst_r (float), worst_burst_id (str)..."
    )
    per_burst: list[BurstResult] = Field(
        default_factory=list,
        description="Per-burst drilldown list (one entry per BURSTS declarative config entry)..."
    )
```

**Rules to preserve:**
- `model_config = ConfigDict(extra="forbid")` on every new model — matches existing pattern; prevents silent drift.
- New literal enum: `status: Literal["PASS", "FAIL", "CALIBRATING", "BLOCKER", "SKIPPED"]` on `AOIResult` — extends Phase 2's 2-valued literal. Per CONTEXT D-03/D-11, `BLOCKER` surfaces Mojave fallback exhaustion; `SKIPPED` marks untried fallbacks after an earlier attempt passed; `CALIBRATING` is the expected status for the first rollout.
- Per CONTEXT D-11: `AOIResult.attempts: list[AOIResult] = Field(default_factory=list, ...)` for the Mojave fallback chain. Leaf-AOI rows have `attempts = []`; parent Mojave row has 1–4 `attempts` entries with `attempt_index: int` + `reason: str` fields.
- Per CONTEXT D-07: `reference_agreement: ReferenceAgreementResultJson | None = Field(default=None, ...)` — null for Mojave which skips amplitude sanity.
- New top-level `CSLCSelfConsistNAMCellMetrics.cell_status: Literal["PASS", "FAIL", "CALIBRATING", "MIXED", "BLOCKER"]` per D-03/D-11. Unlike Phase 2's `all_pass: bool`, Phase 3 uses an enum because two leaf AOIs can coexist as `CALIBRATING`/`BLOCKER` combinations that `bool` can't express.
- Two separate cell-metrics classes (`CSLCSelfConsistNAMCellMetrics` + `CSLCSelfConsistEUCellMetrics`) NOT a single parameterised one — mirrors Phase 2's single `RTCEUCellMetrics` instance; matrix_writer's schema-discriminator check (`_is_rtc_eu_shape`) works via JSON-key detection, so the EU class can carry extra `egms_l2a_stable_ps_residual_mm_yr` measurements in `product_quality` without NAM class bloat.
- Order preservation in `per_aoi: list[AOIResult]` — matches `BURSTS` order in the script, mirrors Phase 2 per_burst. Deterministic matrix/CONCLUSIONS rendering depends on this.

---

### `src/subsideo/validation/matrix_writer.py` (renderer, additive 2 new cell branches)

**Analog:** `_is_rtc_eu_shape` + `_render_rtc_eu_cell` (lines 160–230) + the main `write_matrix` branch dispatch (lines 278–291).

**Schema-discriminator pattern** (lines 163–181):

```python
def _is_rtc_eu_shape(metrics_path: Path) -> bool:
    """Return True when the metrics.json has a top-level ``per_burst`` key.

    Cheap schema-discrimination check (D-11 marker). Inspects the raw JSON
    rather than relying on Pydantic validation so that ``_load_metrics``
    (which parses against the base ``MetricsJson`` with ``extra="forbid"``)
    is never asked to validate RTCEUCellMetrics-only fields. Returns False
    on any I/O or JSON error -- the caller falls through to the default
    cell-render path, which then surfaces RUN_FAILED if the file is
    genuinely malformed.
    """
    import json as _json

    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.debug("_is_rtc_eu_shape: cannot read {}: {}", metrics_path, e)
        return False
    return isinstance(raw, dict) and "per_burst" in raw
```

**Aggregate-render pattern** (lines 184–230):

```python
def _render_rtc_eu_cell(
    metrics_path: Path,
) -> tuple[str, str] | None:
    """Render RTC-EU multi-burst aggregate as ``(pq_col, ra_col)``..."""
    from subsideo.validation.matrix_schema import RTCEUCellMetrics

    try:
        metrics = RTCEUCellMetrics.model_validate_json(metrics_path.read_text())
    except Exception as e:
        logger.warning("Failed to parse RTCEUCellMetrics from {}: {}", metrics_path, e)
        return None

    fail_count = metrics.total - metrics.pass_count
    if fail_count > 0:
        base = f"{metrics.pass_count}/{metrics.total} PASS ({fail_count} FAIL)"
    else:
        base = f"{metrics.pass_count}/{metrics.total} PASS"
    warn = " ⚠" if metrics.any_investigation_required else ""
    ra_col = f"{base}{warn}"
    pq_col = "—"
    return pq_col, ra_col
```

**CALIBRATING italicisation pattern** (from `_render_cell_column` lines 110–124):

```python
    any_calibrating = any(
        CRITERIA[cid].type == "CALIBRATING" for cid in gate_cids
    )
    body = " / ".join(rendered)
    return f"*{body}*" if any_calibrating else body
```

**Main dispatch branch** (lines 278–291):

```python
        if metrics_path.exists() and _is_rtc_eu_shape(metrics_path):
            cols = _render_rtc_eu_cell(metrics_path)
            if cols is not None:
                pq_col, ra_col = cols
                lines.append(
                    f"| {product} | {region} | {_escape_table_cell(pq_col)} | "
                    f"{_escape_table_cell(ra_col)} |"
                )
                continue
            # Fall through to default rendering as a best-effort...
```

**Rules to preserve:**
- Follow the same shape-discriminator pattern: Phase 3 adds `_is_cslc_selfconsist_shape(metrics_path)` checking for `per_aoi` key (NOT `per_burst`, so cells are independently discoverable).
- Phase 3 renders both PQ and RA columns (unlike RTC-EU which only has RA). PQ column: `X/N CALIBRATING: coh=A.BB / resid=C.C mm/yr` with A/C from the worst-case PQ measurement across AOIs. RA column: SoCal and Iberian emit `amp_r=X.XX, amp_rmse=Y.Y dB`; Mojave contributes `—`.
- Per CONTEXT D-03 + D-06: CALIBRATING cells render whole-body italics via Markdown `*...*`. Format template: `*X/N CALIBRATING: coh=0.XX / resid=Y.Y mm/yr*` (not `PASS` / `FAIL`). Mojave BLOCKER renders as `*1/2 CALIBRATING, 1/2 BLOCKER*` in the NAM cell.
- Use Unicode escape form (`⚠`) for the warning glyph — not literal `⚠`. Matches the byte-level-ASCII-source convention at line 227 comment.
- The 2 new render functions stay private (`_render_cslc_selfconsist_nam_cell`, `_render_cslc_selfconsist_eu_cell`); only the dispatcher inside `write_matrix` is public surface.
- Fall-through-to-default pattern preserved: if new-shape parsing fails, control returns to the base `MetricsJson` path which surfaces `RUN_FAILED` — matches lines 287–291 RTC-EU comment.
- Per-AOI drilldown does NOT render in matrix.md — it lives in metrics.json + CONCLUSIONS (CONTEXT D-06). The matrix cell is intentionally single-line.

---

### `src/subsideo/validation/stable_terrain.py` (D-module, unchanged consumer reference)

**Analog:** Self (existing Phase 1 module; 208 LOC). No modification in Phase 3 — show the call signature so new scripts call it correctly.

**Public signature (lines 56–67):**

```python
def build_stable_mask(
    worldcover: np.ndarray,
    slope_deg: np.ndarray,
    coastline: GeometryLike | None = None,
    waterbodies: GeometryLike | None = None,
    *,
    transform: Affine | None = None,
    crs: CRSLike | None = None,
    coast_buffer_m: float = DEFAULT_COAST_BUFFER_M,   # 5000.0
    water_buffer_m: float = DEFAULT_WATER_BUFFER_M,   # 500.0
    slope_max_deg: float = DEFAULT_SLOPE_MAX_DEG,     # 10.0
) -> np.ndarray:
```

**Rules to preserve:**
- CONTEXT D-09 + D-Claude's-Discretion "Coastline + water-body data source": scripts MUST pass `coastline` + `waterbodies` geometries for the buffers to fire — defaults are `None` (buffer skipped). Natural Earth 10m coastline is the starting choice per Claude's Discretion.
- Transform + CRS are required whenever `coastline` or `waterbodies` is non-None (lines 129–152). CRS must be projected/metric; buffer distances are in metres.
- Call site in each new eval script: compute `worldcover` + `slope_deg` rasters first at the same grid (matching `transform` + `crs`), then invoke `build_stable_mask`. Output is `(H, W) bool np.ndarray` — used as the `stable_mask` argument to `coherence_stats`, `residual_mean_velocity`, and Phase 3's new `compute_residual_velocity` linear-fit helper.

---

### `src/subsideo/validation/harness.py` (plumbing, unchanged)

**Analog:** Self — 5 helpers declared as public API. Phase 3 is the 4th production consumer (after Phase 1 pilot `run_eval.py`, Phase 2 `run_eval_rtc_eu.py`, and Phase 1's migration of v1.0 scripts).

**Public API consumed by Phase 3 scripts:**

```python
# src/subsideo/validation/harness.py
def select_opera_frame_by_utc_hour(
    sensing_datetime: datetime,
    frame_metadata: Sequence[dict[str, Any]],
    *,
    tolerance_hours: float = 1.0,
) -> dict[str, Any]: ...

def download_reference_with_retry(
    url: str, dest: Path, *, source: RetrySource,
    max_retries: int = 5, backoff_seconds: int = 30,
    session: requests.Session | None = None,
) -> Path: ...

def ensure_resume_safe(
    cache_dir: Path, manifest_keys: Sequence[str],
) -> bool: ...

def credential_preflight(env_vars: Sequence[str]) -> None: ...  # SystemExit on missing

def bounds_for_burst(
    burst_id: str, buffer_deg: float = 0.2,
) -> tuple[float, float, float, float]: ...

def find_cached_safe(
    granule_id: str, search_dirs: Sequence[Path],
) -> Path | None: ...
```

**Rules to preserve:**
- No module edits in Phase 3 unless the 15-epoch OPERA CSLC batch-fetch pattern warrants a new helper (Claude's Discretion per CONTEXT). If added, the new helper mirrors `find_cached_safe` shape (pure-function, `Sequence[Path]` input, `Path | None` or `list[Path]` return, never raises on missing cache).
- `bounds_for_burst(cfg.burst_id, buffer_deg=0.5)` — the `buffer_deg=0.5` choice is now canonical per CONCLUSIONS_RTC_EU.md Bug 4 resolution. Phase 3 scripts should use 0.5 by default (not the 0.2 default) for Alpine-type high-relief geometry safety.
- `select_opera_frame_by_utc_hour` is consumed per-epoch in the 15-epoch SoCal stack (D-07 amplitude sanity against per-epoch OPERA CSLC reference) — pattern mirrors Phase 2 single-epoch per-burst invocation, iterated.

---

### `src/subsideo/validation/supervisor.py` (watchdog, unchanged)

**Analog:** Self — Phase 1 subprocess wrapper. Phase 3's 2 scripts declare `EXPECTED_WALL_S` at module level per Phase 1 D-11 convention.

**`EXPECTED_WALL_S` declaration convention** (from `run_eval_rtc_eu.py` line 35):

```python
# 5 bursts x ~30 min cold + reference/DEM/orbit fetches + supervisor 2x margin.
# Actual wallclock from first cold run populates Plan 02-05 Task 1 checkpoint notes.
EXPECTED_WALL_S = 60 * 60 * 4   # 14400s; supervisor AST-parses (D-11 + T-07-06)
```

**AST-parsed literal constraint** (from `supervisor.py` `_eval_literal_tree` lines 60–91):

```python
_ALLOWED_BINOPS: dict[type, object] = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.FloorDiv: lambda a, b: a // b,
}
```

**Rules to preserve:**
- `EXPECTED_WALL_S` declared BEFORE `if __name__ == "__main__":` guard at module level (not inside). Supervisor AST-parses the module, not the `__main__` block (line 94–125 `_parse_expected_wall_s`).
- Value MUST be a literal int or a BinOp of literals over `+ - * //`. Rejected: `Name` (`SECONDS_PER_HOUR`), `Call` (`timedelta(hours=4).total_seconds()`), `Attribute`, `Subscript`. Phase 3 budgets per CONTEXT D-Claude's-Discretion EXPECTED_WALL_S paragraph: cap at ~16 h = `60 * 60 * 16` for the N.Am. cell (SoCal 12h + Mojave fallback guard with worst-case truncation) and ~14 h = `60 * 60 * 14` for the EU cell.
- Comment above the constant explains the budget arithmetic (mirrors `run_eval_rtc_eu.py` line 33–34 comment) — human-readable rationale next to machine-readable value.
- The module-level `warnings.filterwarnings("ignore")` at line 31 is a convention from Phase 2 scripts; Phase 3 scripts follow it to keep supervisor log output readable.

---

### `run_eval_cslc_selfconsist_nam.py` (NEW, eval script at repo root)

**Analog:** `run_eval_rtc_eu.py` (727 LOC) — Phase 2 declarative-AOI-list + per-AOI try/except + aggregate-reduce template. `run_eval_cslc.py` (209 LOC) is an older single-burst analog, NOT the fork source — its run_cslc+compare-cslc call sequence is useful but the iteration pattern is outdated.

**Module header + EXPECTED_WALL_S declaration** (lines 1–36):

```python
# run_eval_rtc_eu.py -- EU RTC-S1 validation against OPERA L2 RTC-S1 reference
#
# Phase 2 (v1.1) deliverable. Proves Phase 1 harness on a deterministic
# product (RTC) across 5 EU terrain regimes...
#
# Orchestration:
#   - Declarative BURSTS: list[BurstConfig] (D-05)
#   - Per-burst try/except isolation (D-06)
#   - Sequential across bursts (D-07: no burst-level parallelism)
#   - Per-burst whole-pipeline skip + per-stage ensure_resume_safe (D-08)
#   - Cached-SAFE reuse via harness.find_cached_safe (D-02)
#   - Single eval-rtc-eu/metrics.json (RTCEUCellMetrics; D-09, D-10)
#   - Single eval-rtc-eu/meta.json (per-burst input hashes flattened; D-12)
#
# Makefile target: `make eval-rtc-eu` -> supervisor wraps this script.
#   EXPECTED_WALL_S: 4h = 14400s covers 5 bursts...
import warnings; warnings.filterwarnings("ignore")  # noqa: E702, I001

EXPECTED_WALL_S = 60 * 60 * 4   # 14400s; supervisor AST-parses (D-11 + T-07-06)
```

**Declarative `BURSTS: list[BurstConfig]` frozen-dataclass pattern** (lines 90–188):

```python
    @dataclass(frozen=True)
    class BurstConfig:
        """Per-burst declarative config for run_eval_rtc_eu.BURSTS (D-05)."""
        burst_id: str
        regime: Literal["Alpine", "Scandinavian", "Iberian", "TemperateFlat", "Fire"]
        sensing_time: datetime
        output_epsg: int
        centroid_lat: float
        relative_orbit: int | None
        cached_safe_search_dirs: tuple[Path, ...]

    # BURSTS -- locked from .planning/milestones/v1.1-research/rtc_eu_burst_candidates.md
    # (Plan 02-02, user-approved-as-drafted 2026-04-23). Each row mirrors the
    # approved probe artifact regime + centroid_lat + expected relief values.
    BURSTS: list[BurstConfig] = [
        # 1. Alpine (Swiss/Italian Alps, Valtellina) -- >1000 m relief, RTC-01 constraint.
        BurstConfig(
            burst_id="t066_140413_iw1",
            regime="Alpine",
            sensing_time=datetime(2024, 5, 2, 5, 35, 47),
            output_epsg=32632,
            centroid_lat=46.35,
            relative_orbit=66,
            cached_safe_search_dirs=(Path("eval-rtc-eu/input"),),
        ),
        # ... 4 more entries
    ]
```

**Per-burst try/except isolation + `attempts[]`-compatible pattern** (lines 561–608):

```python
    per_burst: list[BurstResult] = []
    per_burst_input_hashes: dict[str, dict[str, str]] = {}
    for cfg in BURSTS:
        t0 = time.time()
        try:
            row = process_burst(cfg)
            per_burst.append(row)
            # ... input hash recording
            logger.info("Burst {} PASS in {:.0f}s", cfg.burst_id, time.time() - t0)
        except Exception as e:  # noqa: BLE001 - per-burst isolation (D-06)
            tb = traceback.format_exc()
            logger.error("Burst {} FAIL ({:.0f}s): {}", cfg.burst_id, time.time() - t0, e)
            per_burst.append(
                BurstResult(
                    burst_id=cfg.burst_id,
                    regime=cfg.regime,
                    lat=cfg.centroid_lat,
                    max_relief_m=None,
                    cached=False,
                    status="FAIL",
                    product_quality=None,
                    reference_agreement=ReferenceAgreementResultJson(
                        measurements={}, criterion_ids=[]
                    ),
                    investigation_required=False,
                    investigation_reason=None,
                    error=repr(e),
                    traceback=tb,
                )
            )
```

**Aggregate metrics.json reduce** (lines 611–697):

```python
    pass_count = sum(1 for r in per_burst if r.status == "PASS")
    total = len(per_burst)
    any_investigation = any(r.investigation_required for r in per_burst)

    # worst_rmse / worst_r computed across PASS rows only...
    passed_rows = [r for r in per_burst if r.status == "PASS"]
    if passed_rows:
        worst = max(passed_rows, key=lambda r: float(
            r.reference_agreement.measurements.get("rmse_db", -1.0)
        ))
        # ...

    metrics = RTCEUCellMetrics(
        product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
        reference_agreement=aggregate_ra,
        criterion_ids_applied=["rtc.rmse_db_max", "rtc.correlation_min"],
        pass_count=pass_count,
        total=total,
        all_pass=(pass_count == total),
        any_investigation_required=any_investigation,
        reference_agreement_aggregate={...},
        per_burst=per_burst,
    )
    metrics_path = CACHE / "metrics.json"
    metrics_path.write_text(metrics.model_dump_json(indent=2))
```

**`credential_preflight` + `earthaccess.login` pre-loop convention** (lines 78–201):

```python
    load_dotenv()
    credential_preflight([
        "EARTHDATA_USERNAME",
        "EARTHDATA_PASSWORD",
    ])
    # ... BURSTS + CACHE + mkdir
    auth = earthaccess.login(strategy="environment")  # noqa: F841
```

**Rules to preserve:**
- `EXPECTED_WALL_S` at module top, BEFORE `if __name__ == "__main__":` guard — supervisor AST-parses the module, not the guard.
- All imports + dataclass + processing logic lives INSIDE `if __name__ == "__main__":` — matches `run_eval_rtc_eu.py` lines 38–727. Scope constraint: Phase 2 D-05 pattern requires the `__main__` guard so `python -c "import run_eval_cslc_selfconsist_nam"` does not trigger the full preflight.
- Declarative AOI list AT MODULE LEVEL (inside `__main__`): `AOIS: list[AOIConfig] = [SoCalAOI, MojaveAOI]`. NOT inside `process_aoi()` — iteration invariant per AOI. Mirrors `BURSTS: list[BurstConfig]` line 108 pattern.
- Mojave's fallback chain is a field on `MojaveConfig`: `fallback_chain: tuple[AOIConfig, ...]` — probe-locked order from `cslc_selfconsist_aoi_candidates.md`. Inner loop iterates fallbacks with per-attempt try/except that appends to `AOIResult.attempts[]`; outer loop still treats Mojave as a single AOI.
- Per-AOI try/except isolation (D-06): one AOI's failure must not block the others. Failure path emits an `AOIResult(status="FAIL", error=repr(e), traceback=tb, ...)` row with empty measurements.
- Aggregate reduce produces `CSLCSelfConsistNAMCellMetrics` (NOT `RTCEUCellMetrics`) with:
  - `cell_status` resolved from per-AOI status combination (PASS/FAIL/CALIBRATING/MIXED/BLOCKER per D-03).
  - `product_quality` sub-aggregate: `{"worst_coherence_median_of_persistent": ..., "worst_residual_mm_yr": ...}`.
  - `reference_agreement_aggregate`: `{"worst_amp_r", "worst_amp_rmse_db", "worst_aoi"}` (SoCal only; Mojave null).
  - `per_aoi: list[AOIResult]` with the two AOI rows (or one + Mojave attempts[] nesting).
- `SENSING_WINDOW[SoCalAOI]` (15 epochs): this is the structural addition vs `run_eval_rtc_eu.py` — an inner per-epoch loop per AOI before `coherence_stats` reduce. Each epoch runs `run_cslc`, writes an HDF5, and optionally calls `compare_cslc` (SoCal epoch 1 only per D-07). The outer per-AOI loop then assembles the `ifgrams_stack` via `compute_ifg_coherence_stack`.
- `_mp.configure_multiprocessing()` fires at the top of `run_cslc()` per Phase 1 D-14 — per-AOI, not per-epoch. Pattern mirrors `run_eval_rtc_eu.py` which lets `run_rtc` handle `_mp` internally.
- Cache layout under `eval-cslc-selfconsist-nam/`: `input/`, `output/`, `opera_reference/`, `dem/`, `orbits/`, `worldcover/`, `coastline/` (matches Phase 2 line 192–196 mkdir pattern + 2 new Phase 3 subdirs). `metrics.json` + `meta.json` at the top level.
- Exit code: `sys.exit(0 if cell_status in ("PASS", "CALIBRATING") else 1)` — supervisor distinguishes watchdog abort (124) from eval fail (1). First-rollout CALIBRATING is a success exit per D-03 (matrix writer italicises; make target passes).

---

### `run_eval_cslc_selfconsist_eu.py` (NEW, eval script at repo root)

**Analog:** Same as NAM script above (`run_eval_rtc_eu.py` template); plus `compare_disp.compare_disp_egms_l2a` (lines 239–374) for the EGMS L2a step.

**EGMStoolkit download pattern** (from `compare_disp.fetch_egms_ortho` lines 36–79):

```python
def fetch_egms_ortho(
    bbox: tuple[float, float, float, float],
    output_dir: Path,
) -> Path:
    """Download EGMS Ortho product for a bounding box using EGMStoolkit."""
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        import EGMStoolkit
    except ImportError as err:
        raise ImportError("EGMStoolkit is not installed. Install via pip: pip install EGMStoolkit") from err
    west, south, east, north = bbox
    EGMStoolkit.download(
        bbox=[west, south, east, north],
        product_level="Ortho",
        output_dir=str(output_dir),
    )
    tif_files = sorted(output_dir.glob("*.tif"))
    if not tif_files:
        raise FileNotFoundError(f"No GeoTIFF files found in {output_dir} after EGMS download")
    return tif_files[0]
```

**Rules to preserve:**
- Script diff from `run_eval_cslc_selfconsist_nam.py` contains only reference-data differences (ENV-07 acceptance per CONTEXT D-05) — AOI list, EGMStoolkit L2a download, EGMS residual call added to `ProductQualityResult.measurements`.
- `AOIS = [IberianAOI]` — single-entry list with inline fallback metadata (Alentejo / Massif Central as `fallback_chain`). EU variant is structurally identical to NAM; only the AOI list differs.
- EGMStoolkit product level is `"L2a"` NOT `"Ortho"` — Iberian CSLC-05 requires per-track PS data for stable-PS residual. Pattern mirrors `fetch_egms_ortho` shape (lazy-import EGMStoolkit, mkdir, call download, collect outputs, raise on empty).
- Per CONTEXT D-12 + PITFALLS P2.3: stable-PS filter is `df[df['mean_velocity_std'] < 2.0]`. Reference-frame alignment via subtracting stable-set median from our velocity BEFORE paired residual.
- Iberian `ProductQualityResult` carries 7 measurements (6 coherence stats + residual + EGMS L2a residual) and 3 criterion_ids (`cslc.selfconsistency.coherence_min`, `cslc.selfconsistency.residual_mm_yr_max`, + a new-in-Phase-3 `cslc.egms_l2a.residual_mm_yr_max` if added to criteria.py OR left off criterion_ids for first-rollout-reported-only mode). Three independent numbers per CONTEXT D-12 + CSLC-05.
- Aggregate cell type: `CSLCSelfConsistEUCellMetrics` with `per_aoi: [IberianResult]` single-entry. EU cell renders `1/1 CALIBRATING` in matrix.md.
- Cache layout: `eval-cslc-selfconsist-eu/` with extra `egms/` subdir for the L2a CSV downloads.

---

### `CONCLUSIONS_CSLC_SELFCONSIST_NAM.md` (NEW, post-eval doc at repo root)

**Analog:** `CONCLUSIONS_CSLC_N_AM.md` (section structure; 319 LOC) + `CONCLUSIONS_RTC_EU.md` (multi-AOI aggregate template; 150+ LOC).

**Section-structure template from CSLC_N_AM** (lines 1–31):

```markdown
# N.Am. CSLC-S1 Validation — Session Conclusions

**Date:** 2026-04-11 (finalised 2026-04-11)
**Burst:** `T144-308029-IW1`
**Scene:** S1A, 2024-06-24T14:01:16Z, relative orbit 144
**Result: PASS** — subsideo CSLC-S1 output matches...
**Reproducibility:** Confirmed — clean re-run...

---

## 1. Objective
## 1.1 Pass Criteria

## 2. Test Setup
### 2.1 Target Burst
### 2.2 Input Data
### 2.3 Processing Environment

## 3. What Was Run
### 3.1 Evaluation Script
### 3.2 CSLC Pipeline
### 3.3 Validation Comparison

## 4. Bugs Encountered and Fixed

## 5. Cross-version phase comparison impossibility
## 5.1 / 5.2 / 5.3 / 5.4

## 6. Final Validation Results

## 7. Output Files

## 8. Source Files Changed During This Session

## 9. Recommendations for Next Steps
```

**Multi-AOI aggregate cell header from RTC_EU** (lines 1–31):

```markdown
# EU RTC-S1 Validation -- Session Conclusions

**Date:** 2026-04-23
**Phase:** v1.1 Phase 2 -- RTC-S1 EU Validation
**Bursts:** 5 bursts across 5 terrain regimes (Alpine / Scandinavian / Iberian / TemperateFlat / Fire)
**Result:** MIXED (3/5 PASS, 2/5 FAIL with investigation)

> This document mirrors the structure of `CONCLUSIONS_RTC_N_AM.md` (v1.0 reference). The §5a "Terrain-Regime Coverage Table" and §5b "Investigation Findings" sections are Phase 2 additions required by RTC-01 + RTC-03. Plan 02-05 (post-eval-run) populated all concrete values below from `eval-rtc-eu/metrics.json` and `eval-rtc-eu/meta.json`.
```

**Rules to preserve:**
- Front-matter header mirrors RTC_EU shape: `**Phase:** v1.1 Phase 3 -- CSLC-S1 Self-Consistency (N.Am.)`, `**AOIs:**`, `**Result:** CALIBRATING (2/2 CALIBRATING)` or `CALIBRATING + BLOCKER` if Mojave exhausts.
- Section structure mirrors CSLC_N_AM §1–9 but ADDS three required Phase 3 sections per CONTEXT D-08:
  - `## 4a. Calibration Framing` (M5 discipline — "this is data point 1/2 of ≥3 required; GATE-05 says no promotion to BINDING until all 3 collected"; NO PASS/FAIL prose; use exact phrase `calibration data point: SoCal=0.XX` and `calibration data point: Mojave=0.YY`).
  - `## 4b. Stable-Mask Sanity Check` (per-AOI coherence histogram + mask-over-optical-basemap PNG per PITFALLS P2.1; reference `eval-cslc-selfconsist-nam/sanity/<aoi>/` artifact dir).
  - `## 4c. Calibration Changes` (any `gate_metric_key` change log from CONTEXT D-04; empty if no change).
- Per-AOI subsections at §2 + §3 + §6: SoCal first (calibration data point 1), Mojave second (calibration data point 2 + any failed fallback attempts). Mirror RTC_EU's per-burst table at §2.1 (lines 38–46) for the "AOI summary" table with columns: `aoi_name, regime, lat, burst_id, sensing_window, stable_mask_pixels, coh_median_of_persistent, residual_mm_yr, amp_r (SoCal only), amp_rmse_db (SoCal only)`.
- §5 "Cross-version phase comparison impossibility" is CROSS-LINKED TO `docs/validation_methodology.md §1` (CSLC-06 deliverable) NOT duplicated — this doc inherits the methodology doc's argument; internal rerun cites `PITFALLS P2.4` once.
- §4 Bugs Encountered section preserved from CSLC_N_AM (empty if none in Phase 3 run).
- No `PASS` / `FAIL` verdict in final §6 summary — use `CALIBRATING: coh=0.XX / resid=Y.Y mm/yr` format per CONTEXT D-03.

---

### `CONCLUSIONS_CSLC_EU.md` (NEW, post-eval doc at repo root)

**Analog:** Same as NAM CONCLUSIONS above, but single-AOI (Iberian) with three-number schema.

**Rules to preserve:**
- All NAM CONCLUSIONS rules apply.
- §6 Final Validation Results table shows THREE independent numbers per CSLC-05 + CONTEXT D-12:
  - OPERA CSLC amplitude sanity: `amp_r`, `amp_rmse_db` (BINDING via `cslc.amplitude_r_min` + `cslc.amplitude_rmse_db_max`).
  - Self-consistency coherence: `coh_median_of_persistent` (CALIBRATING via `cslc.selfconsistency.coherence_min`).
  - Self-consistency + EGMS L2a residual: `residual_mm_yr`, `egms_l2a_stable_ps_residual_mm_yr` (both CALIBRATING).
- Methodology §2 (product-quality vs reference-agreement distinction) cross-link to `docs/validation_methodology.md §2` (CSLC-06). Iberian row is the motivating example per CONTEXT specifics.

---

### `.planning/milestones/v1.1-research/cslc_selfconsist_aoi_candidates.md` (NEW, pre-eval probe artifact)

**Analog:** `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` (67 LOC).

**Header + table + "User review resolves" pattern** (lines 1–30):

```markdown
# RTC-S1 EU Burst Candidates -- Probe Report

**Probed:** 2026-04-23T15:40:02Z
**Source query:** `asf_search` + `earthaccess` against ASF DAAC.
**Phase:** 2 (RTC-S1 EU Validation)
**Decision:** D-01 (probe artifact) + D-03 (5-regime fixed list) + D-04 (Claude drafts; user reviews).

## Regime Coverage

| # | regime | label | centroid_lat | expected_max_relief_m | opera_rtc_granules_2024_2025 | best_match_sensing_utc | best_match_granule | cached_safe | burst_id (fill-in) |
|---|--------|-------|--------------|-----------------------|------------------------------|------------------------|--------------------|-------------|---------------------|
| 1 | Alpine | Swiss/Italian Alps ... | 46.35 | ~3200 | 2907 | 2024-05-02T05:35:20Z | ... | (none) | (derive via ...) |
| ... |

## RTC-01 Mandatory Constraints Audit
- **>1000 m relief:** row #1 (Alpine, expected ~3200 m) -- PASS candidate.
- **>55°N:** row #2 (Scandinavian, centroid ~67.15°N) -- PASS candidate.

Claude has drafted the five regime rows ... User review per D-04 resolves:
1. Which granule ... is the target SLC for each fresh burst
2. The concrete `burst_id` (JPL lowercase t<relorb>_<burst>_iw<swath>) ...
3. Whether any regime should be swapped ...
4. Sensing UTC hour to pass to `select_opera_frame_by_utc_hour` ...

Plan 02-04 locks the 5-burst final list from this artifact. Downstream the probe doc is referenced (via `see probe artifact`) but not re-run at eval time.
```

**Rules to preserve:**
- Front-matter: `**Probed:** <iso>` + `**Phase:** 3 (CSLC-S1 Self-Consistency + EU)` + `**Decision:** D-10 (probe artifact) + D-11 (Mojave fallback ordering)`.
- CONTEXT D-10 columns: `aoi, regime, candidate_burst_id, opera_cslc_coverage_2024, egms_l2a_release_2019_2023_stable_ps_count (EU only), expected_stable_pct_per_worldcover, published_insar_stability_ref, cached_safe_fallback_path`.
- Three AOI rows for Mojave fallback chain (Coso/Searles primary, Pahranagat, Amargosa, Hualapai) — 4 row per CONTEXT D-11 pre-ranked by `(opera_cslc_coverage_2024) × (expected_stable_pct)`. Plus 1 row for Iberian primary + 2 fallbacks (Alentejo + Massif Central).
- NO SoCal row — locked to `t144_308029_iw1` by CSLC-03; outside probe scope per CONTEXT D-10.
- User-review-resolves checklist at bottom (mirror RTC probe lines 22–28): which burst_id wins per AOI, sensing window for SoCal 15-epoch stack (D-09 Claude's Discretion 168-day window), stable_std_max for EGMS L2a (2.0 per D-12 default).
- Query reproducibility footer: `micromamba run -n subsideo python scripts/probe_cslc_aoi_candidates.py` (CONTEXT calls out `scripts/probe_cslc_aoi_candidates.py` as optional sub-deliverable).
- Committed before eval runs — same Phase 2 D-01 discipline.

---

### `docs/validation_methodology.md` (NEW, methodology doc)

**Analog:** **NO IN-REPO ANALOG** — this is the first write per CONTEXT D-15 append-only policy.

Reference texts from CONCLUSIONS_CSLC_N_AM.md §5 (lines 200–228) supply the evidence content for §1:

```markdown
### 5.1 / 5.2 / 5.3 / 5.4 [existing evidence sections]
...
1. **Phase screen computation**: carrier phase estimation, ellipsoidal flattening, geometric Doppler corrections produce different phase screens
2. **SLC interpolation kernel**: the geocoding interpolator may have changed, producing different sub-pixel phase contributions
3. **Solid Earth tide model**: applied corrections produce different phase adjustments
...
Each product internally consistent ... But the absolute phase reference differs between the two chains, making cross-chain interferometric comparison meaningless.
```

Reference for §2 (product-quality vs reference-agreement distinction) from `.planning/research/PITFALLS.md §M1-M6`.

**Rules to preserve:**
- Plain Markdown file (no Sphinx). Lives at `docs/validation_methodology.md` — new `docs/` folder created if not present.
- Phase 3 writes §1 + §2 ONLY per CONTEXT D-13 + D-15. NO stub scaffolding for §3–§5 (Phase 4 / 5 / 6 / 7 own those).
- §1 structural argument (isce3 SLC interpolation kernel changed between 0.15 and 0.25) FIRST per CONTEXT D-14 + PITFALLS P2.4 mitigation — prevents the "this time we'll subtract everything" re-attempt anti-pattern. The diagnostic evidence table (CONCLUSIONS §5.3) is appendix, not lead.
- §1 MUST contain a "do not re-attempt with additional corrections" policy statement audible to future contributors + cite the upstream isce3 0.15→0.19 changelog entry on SLC interpolation.
- §2 motivating example is Iberian Meseta's three-number row (`amp_r`/`amp_rmse_db` reference-agreement vs `coh`/`residual`/`egms_l2a_residual` product-quality) — cites CONCLUSIONS_CSLC_EU.md §6 once it exists.
- No Phase 3 ownership of §3–§5 headings; the ToC is written by Phase 7 REL-03 — CONTEXT D-15 hard rule.

---

## Shared Patterns

### Declarative AOI/BURST list + per-item try/except + aggregate reduce

**Source:** `run_eval_rtc_eu.py` lines 108–188 (BURSTS) + 563–608 (per-burst try/except loop) + 613–697 (aggregate reduce).

**Apply to:** Both new eval scripts (`run_eval_cslc_selfconsist_nam.py`, `run_eval_cslc_selfconsist_eu.py`).

```python
@dataclass(frozen=True)
class AOIConfig:
    aoi_name: str                 # "SoCal" | "Mojave" | "Iberian"
    burst_id: str                 # JPL lowercase
    regime: str
    sensing_window: tuple[datetime, ...]  # 15 consecutive S1A 12-day epochs per AOI (SoCal, each Mojave fallback, Iberian primary + fallbacks)
    # Per-AOI sensing_window rule (Phase 3 CSLC-04 self-consistency gate invariant):
    #   15 consecutive S1A 12-day epochs for EVERY leaf AOI — SoCal, each Mojave
    #   fallback candidate (Coso/Pahranagat/Amargosa/Hualapai), Iberian primary,
    #   and each Iberian fallback (Alentejo / Massif Central).
    #   Locked per-AOI from the Plan 03-02 probe artifact.
    #   A single-epoch window breaks the self-consistency gate by construction:
    #     - compute_residual_velocity requires >= 3 epochs (raises ValueError).
    #     - _compute_ifg_coherence_stack requires >= 2 epochs to form any IFG.
    #   Mojave therefore uses 15-epoch stacks in the same shape as SoCal — the
    #   fallback policy (D-11) chooses WHICH burst; it does not relax the stack shape.
    output_epsg: int
    centroid_lat: float
    cached_safe_search_dirs: tuple[Path, ...]
    fallback_chain: tuple[AOIConfig, ...] = ()  # empty for leaf AOIs, non-empty for Mojave

AOIS: list[AOIConfig] = [ SoCalAOI, MojaveAOI ]

per_aoi: list[AOIResult] = []
for cfg in AOIS:
    try:
        per_aoi.append(process_aoi(cfg))
    except Exception as e:
        tb = traceback.format_exc()
        per_aoi.append(AOIResult(aoi_name=cfg.aoi_name, status="FAIL", error=repr(e), traceback=tb, ...))

# reduce → CSLCSelfConsistNAMCellMetrics → write eval-cslc-selfconsist-nam/metrics.json
```

### `credential_preflight` + `earthaccess.login` + `load_dotenv` pre-loop idiom

**Source:** `run_eval_rtc_eu.py` lines 78–201 + `run_eval_cslc.py` lines 26–28.

**Apply to:** Both new eval scripts.

```python
    load_dotenv()
    credential_preflight(["EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"])
    # CDSE creds are only required for fresh EU SAFE downloads (EU script only);
    # we accept a runtime error per-AOI rather than fail the whole cell upfront.
    auth = earthaccess.login(strategy="environment")  # noqa: F841
```

### Pydantic v2 `BaseModel` + `ConfigDict(extra="forbid")` + `Field(..., description=...)`

**Source:** `matrix_schema.BurstResult` + `RTCEUCellMetrics` (lines 158–306).

**Apply to:** All new `matrix_schema.py` types (`AOIResult`, `CSLCSelfConsistNAMCellMetrics`, `CSLCSelfConsistEUCellMetrics`).

```python
class AOIResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aoi_name: str = Field(..., description="Stable label, e.g. 'SoCal' / 'Mojave' / 'Iberian'.")
    status: Literal["PASS", "FAIL", "CALIBRATING", "BLOCKER", "SKIPPED"] = Field(..., description="...")
    # ... all fields use Field(...) with description
```

### CALIBRATING cell italicisation + Unicode-escape warning glyph

**Source:** `matrix_writer._render_cell_column` lines 120–124 + `_render_rtc_eu_cell` line 227.

**Apply to:** Both new matrix_writer render branches (`_render_cslc_selfconsist_nam_cell`, `_render_cslc_selfconsist_eu_cell`).

```python
    body = " / ".join(rendered)
    return f"*{body}*" if any_calibrating else body
    # ...
    warn = " ⚠" if any_calibration_warning else ""   # U+26A0 WARNING SIGN
```

### Cache layout + `ensure_resume_safe` per-stage skip

**Source:** `run_eval_rtc_eu.py` lines 190–196 + 478–496.

**Apply to:** Both new eval scripts.

```python
    CACHE = Path("eval-cslc-selfconsist-nam")  # or -eu
    CACHE.mkdir(exist_ok=True)
    (CACHE / "input").mkdir(exist_ok=True)
    (CACHE / "output").mkdir(exist_ok=True)
    (CACHE / "opera_reference").mkdir(exist_ok=True)
    (CACHE / "dem").mkdir(exist_ok=True)
    (CACHE / "orbits").mkdir(exist_ok=True)
    (CACHE / "worldcover").mkdir(exist_ok=True)  # Phase 3 new
    (CACHE / "coastline").mkdir(exist_ok=True)   # Phase 3 new
    # EU-only:
    (CACHE / "egms").mkdir(exist_ok=True)        # Phase 3 EU new

    # Per-epoch resume-safe skip:
    expected_h5 = [f"{cfg.burst_id}_{epoch.date().isoformat()}.h5" for epoch in cfg.sensing_window]
    if ensure_resume_safe(burst_out, expected_h5):
        logger.info("All 15 CSLCs cached for {}; skipping run_cslc loop", cfg.burst_id)
```

### Provenance meta.json with per-AOI input hashes

**Source:** `run_eval_rtc_eu.py` lines 675–697 + `MetaJson` schema (lines 68–113).

**Apply to:** Both new eval scripts.

```python
    meta = MetaJson(
        schema_version=1,
        git_sha=git_sha, git_dirty=git_dirty,
        run_started_iso=run_started_iso, run_duration_s=time.time() - run_started,
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        input_hashes=flat_input_hashes,  # per-AOI per-epoch SHA256s flattened with aoi_name prefix
    )
    (CACHE / "meta.json").write_text(meta.model_dump_json(indent=2))
```

### `sha256_of_file` + `get_git_sha` + `compute_max_relief` helpers

**Source:** `run_eval_rtc_eu.py` lines 206–237.

**Apply to:** Both new eval scripts — verbatim reuse of these three helpers.

```python
    def sha256_of_file(p: Path) -> str:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def get_git_sha() -> tuple[str, bool]:
        try:
            sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
            dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
            return sha, dirty
        except Exception:
            return "unknown", True
```

### Summary banner at end of run

**Source:** `run_eval_rtc_eu.py` lines 700–723.

**Apply to:** Both new eval scripts.

```python
    print()
    print("=" * 70)
    print(f"eval-cslc-selfconsist-nam: {pass_count}/{total} CALIBRATING",
          ("[investigation]" if any_investigation else ""))
    for row in per_aoi:
        status_tag = row.status  # PASS / CALIBRATING / BLOCKER / FAIL
        coh = row.product_quality.measurements.get("coherence_median_of_persistent", -1.0) if row.product_quality else -1.0
        res = row.product_quality.measurements.get("residual_mm_yr", -1.0) if row.product_quality else -1.0
        print(f"  [{status_tag}] {row.aoi_name:10s} coh={coh:.3f}  residual={res:+.2f} mm/yr")
    print("=" * 70)
    sys.exit(0 if cell_status in ("PASS", "CALIBRATING") else 1)
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `docs/validation_methodology.md` | methodology doc | narrative | First write per CONTEXT D-15 append-only policy; no prior methodology doc exists. §1 content is consolidated from `CONCLUSIONS_CSLC_N_AM.md §5` + `PITFALLS P2.4`; §2 is consolidated from `PITFALLS M1-M6` + Phase 1 split-dataclass ADR. Planner should treat D-13/D-14/D-15 CONTEXT text as the authoritative content template, not a code-pattern analog. |

---

## Metadata

**Analog search scope:**
- `/Volumes/Geospatial/Geospatial/subsideo/src/subsideo/validation/` — 16 files, all read
- `/Volumes/Geospatial/Geospatial/subsideo/run_eval_*.py` — 9 scripts, Phase 2 and CSLC v1.0 read in full
- `/Volumes/Geospatial/Geospatial/subsideo/CONCLUSIONS_*.md` — 9 docs, CSLC-N-AM + RTC-EU read in full (section-structure templates)
- `/Volumes/Geospatial/Geospatial/subsideo/.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` — 67 LOC read in full
- `/Volumes/Geospatial/Geospatial/subsideo/.planning/research/{SUMMARY,FEATURES,PITFALLS,ARCHITECTURE,STACK}.md` — Phase 3 sections read

**Files scanned:** ~40

**Pattern extraction date:** 2026-04-23
