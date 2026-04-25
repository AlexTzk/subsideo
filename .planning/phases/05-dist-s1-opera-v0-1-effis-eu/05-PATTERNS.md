# Phase 5: DIST-S1 OPERA v0.1 + EFFIS EU - Pattern Map

**Mapped:** 2026-04-25
**Files analyzed:** 17 (per revised scope correction in pattern_mapping_context)
**Analogs found:** 17 / 17

## Scope Correction Acknowledged

Phase 5 reshape (per `<important_scope_correction>`) defers DIST-01/02/03 to v1.2 (CMR auto-supersede stage scaffolds the deferred cell). This pattern map deliberately:

- Maps `compare_dist.py` only to bootstrap CI plumbing (NOT config-drift extraction).
- Maps `run_eval_dist.py` only to Stage 0 CMR probe + deferred-cell `metrics.json` write.
- Maps `bootstrap.py` for EU per-event F1 CI bands (still ships).
- Maps `effis.py` (NEW) for D-17/D-18/D-19 WFS query + rasterise.
- Maps the 3-event `EVENTS` list in `run_eval_dist_eu.py` to Aveiro + Evros (EMSR686, NOT EMSR649) + Spain Sierra de la Culebra (NOT Romania clear-cuts).
- Skips `DistNamCellMetrics` + `ConfigDriftReport` schema additions (deferred to v1.2).
- Adds `dist:nam` render branch to `matrix_writer.py` only as "deferred pending operational publication" path; `dist:eu` renders aggregate `X/3 PASS`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/subsideo/validation/bootstrap.py` (NEW) | utility | transform | `src/subsideo/validation/metrics.py` | role-match (data flow) |
| `src/subsideo/validation/effis.py` (NEW) | service | request-response (WFS) + transform (rasterise) | `src/subsideo/data/cdse.py` (WFS-style) + `run_eval_dist_eu.py:331-435` (rasterise inline) | role-match |
| `src/subsideo/validation/harness.py` (MODIFY) | utility | request-response | self (existing `RETRY_POLICY` dict) | exact (additive 5th source) |
| `src/subsideo/validation/matrix_schema.py` (MODIFY) | model | transform | self (`DISPCellMetrics` block lines 452-628) | exact (additive Pydantic v2 types) |
| `src/subsideo/validation/matrix_writer.py` (MODIFY) | service | transform (render) | self (`_render_disp_cell` lines 372-437; `_render_rtc_eu_cell` lines 184-230) | exact (additive render branch) |
| `src/subsideo/validation/compare_dist.py` (MODIFY) | service | transform | self (existing `compare_dist` lines 112-230) | exact (light bootstrap CI plumbing only) |
| `run_eval_dist.py` (MODIFY) | controller | event-driven (eval pipeline) | self (existing v1.0 Park Fire Stage 2 CMR probe) | exact (Stage 0 reframe + deferred-cell write) |
| `run_eval_dist_eu.py` (REWRITE) | controller | event-driven (multi-event eval) | `run_eval_rtc_eu.py` (declarative `BURSTS` list + try/except + aggregate write) | exact |
| `pyproject.toml` (MODIFY) | config | n/a | self (existing `validation` extras) | exact (single line addition) |
| `docs/validation_methodology.md` (APPEND §4) | doc | n/a | self (existing §3 from Phase 4) | exact (append-only by phase) |
| `CONCLUSIONS_DIST_N_AM.md` (APPEND v1.1) | doc | n/a | `CONCLUSIONS_DISP_EU.md` (v1.0 baseline + v1.1 append per Phase 4 D-13) | exact |
| `CONCLUSIONS_DIST_EU.md` (APPEND v1.1) | doc | n/a | `CONCLUSIONS_DISP_EU.md` (v1.0 baseline + v1.1 append) | exact |
| `ROADMAP.md` (AMEND §Phase 5) | doc | n/a | self | exact (criteria amendment) |
| `REQUIREMENTS.md` (AMEND DIST-01/02/03) | doc | n/a | self | exact (status field append) |
| `eval-dist/` → `eval-dist-park-fire/` (RENAME) | cache-dir | n/a | n/a (filesystem rename) | n/a |
| `eval-dist-eu/` + `eval-dist-eu-nov15/` → `eval-dist_eu/` (CONSOLIDATE) | cache-dir | n/a | `matrix_manifest.yml` line 79 | exact (canonicalises manifest) |
| `run_eval_dist_eu_nov15.py` (DELETE) | controller | n/a | n/a (logic migrates to aveiro chained_run sub-stage) | n/a |

## Pattern Assignments

### `src/subsideo/validation/bootstrap.py` (NEW; utility, transform)

**Analog:** `src/subsideo/validation/metrics.py` (entire file)

**Why this analog:** `metrics.py` is the canonical pure-numpy "metric primitives" module — it sets the convention for new pure-array helpers in `subsideo.validation.*` (no I/O, no rasterio, NaN-safe via `np.isfinite`, lazy import for scipy/scikit-image, returns plain `float` not numpy scalars).

**Imports pattern** (`metrics.py` lines 1-9):
```python
"""Pure-function validation metrics for comparing predicted vs reference arrays.

All functions accept numpy arrays and handle NaN/nodata masking internally.
No file I/O -- comparison modules handle loading and spatial alignment.
"""
from __future__ import annotations

import numpy as np
from scipy import stats
```
Copy verbatim: docstring boilerplate + `from __future__ import annotations` (PATTERNS §4.2 from matrix_schema.py:21) + numpy-at-module-top.

**NaN-safe primitive pattern** (`metrics.py` lines 12-22, `rmse`):
```python
def rmse(predicted: np.ndarray, reference: np.ndarray) -> float:
    mask = np.isfinite(predicted) & np.isfinite(reference)
    diff = predicted[mask] - reference[mask]
    if len(diff) == 0:
        return 0.0
    return float(np.sqrt(np.mean(diff**2)))
```
Copy this NaN-mask + `float()` cast structure for any internal helper that takes 2 raster arrays. The Phase 5 `block_bootstrap_ci` resamples block indices, so its inner-loop `metric_fn(pred_b, ref_b)` already inherits this contract from the metric primitives it wraps (no NaN handling needed in bootstrap.py itself).

**Module-level constants pattern** (Phase 1 D-11 + Phase 4 D-04 — `run_eval_disp.py:24` + `run_eval_disp_egms.py:32`):
```python
EXPECTED_WALL_S = 60 * 60 * 6   # 21600 -- Plan 01-07 supervisor AST-parses this
REFERENCE_MULTILOOK_METHOD: Literal["block_mean"] = "block_mean"  # Phase 4 D-04
```
For `bootstrap.py` (per RESEARCH Probe 9):
```python
DEFAULT_BLOCK_SIZE_M: int = 1000
DEFAULT_N_BOOTSTRAP: int = 500
DEFAULT_RNG_SEED: int = 0
DEFAULT_CI_LEVEL: float = 0.95
DEFAULT_PIXEL_SIZE_M: int = 30
```
Top-of-module, `from __future__ import annotations` first, constants before any function definition. **Auditable in `git log --grep="DEFAULT_BLOCK_SIZE_M"`** — switching the bootstrap config defaults requires a visible PR diff (mirrors the `REFERENCE_MULTILOOK_METHOD` posture).

**BootstrapResult dataclass pattern** (`src/subsideo/products/types.py:128-138` `DISTValidationResult` shape, `src/subsideo/validation/results.py:24-43` `ProductQualityResult`/`ReferenceAgreementResult`):
```python
@dataclass(frozen=True)
class BootstrapResult:
    point_estimate: float
    ci_lower: float
    ci_upper: float
    n_blocks_kept: int
    n_blocks_dropped: int
    n_bootstrap: int
    ci_level: float
    rng_seed: int
```
Copy `@dataclass(frozen=True)` + plain-typed fields + no docstring fields — frozen for hashability + immutability; matches the `Criterion` dataclass convention in `criteria.py:28-47`.

**What to differ:**
- Bootstrap is a methodology helper, not a metric — keeps `metrics.py` clean per CONTEXT D-06.
- Pure-numpy implementation (no scipy) — fixed seed `np.random.default_rng(0)` (PCG64) per RESEARCH Probe 9; Mersenne Twister `RandomState` rejected.
- Block-index calculation: `pixels_per_block_axis = block_size_m // pixel_size_m`; `n_block_rows = H // pixels_per_block_axis`; partial blocks dropped (D-08). RESEARCH Probe 9 corrected the count to 110×110 = 12,100 full blocks for T11SLT (CONTEXT.md said 109×109 = 11,881; the corrected count is binding — but Phase 5 scope correction defers T11SLT, so this only matters for EU per-event blocks).
- Inner-loop `concatenate` is O(B × n_blocks × pixels²) ≈ ~3 minutes per call — acceptable for one-shot Phase 5 use; optimisation deferred.

---

### `src/subsideo/validation/effis.py` (NEW; service, request-response + transform)

**Analog:** `src/subsideo/data/cdse.py` (network-layer pattern) + `run_eval_dist_eu.py:331-435` (existing rasterise-inline pattern that gets PROMOTED into the new module)

**Why this analog:** This is the FIRST WFS consumer in `subsideo/`, so there's no exact role-match existing module. `data/cdse.py` is the closest behavioural analog (network-layer wrapper that the harness retry-policy dispatches to); the inline EMS download + rasterise loop in v1.0 `run_eval_dist_eu.py` Stage 6 is the closest functional analog (it already does `geopandas.read_file → unary_union → rasterio.features.rasterize`).

**owslib WFS recipe** (RESEARCH Probe 3 + canonical Library Quick Reference):
```python
from owslib.wfs import WebFeatureService
from owslib.fes import And, BBox, PropertyIsBetween
from owslib.fes2 import Filter as Filter2  # WFS 2.0.0 Filter class
from owslib.etree import etree

wfs = WebFeatureService(
    url='https://maps.effis.emergency.copernicus.eu/effis',  # plan-phase verifies via GetCapabilities probe
    version='2.0.0',
)
filter_obj = Filter2(And([
    BBox([w, s, e, n], 'urn:ogc:def:crs:EPSG::4326'),
    PropertyIsBetween(propertyname='firedate', lower=start_iso, upper=end_iso),
]))
filter_xml = etree.tostring(filter_obj.toXML()).decode('utf-8')
response = wfs.getfeature(typename='ms:modis.ba.poly', filter=filter_xml)
gdf = geopandas.read_file(BytesIO(response.read()))  # GML auto-detected by pyogrio
```
**Note (Probe 3 + Probe 4):** Plan-phase MUST `GetCapabilities`-probe both Candidate A (`https://maps.effis.emergency.copernicus.eu/effis` with layer `ms:modis.ba.poly`) AND Candidate B (`http://geohub.jrc.ec.europa.eu/effis/wfs`) before locking. The exact endpoint URL + layer name is plan-phase territory.

**Rasterise-inline pattern** (`run_eval_dist_eu.py:425-435`):
```python
ems_raster = rio_rasterize(
    shapes=[(ems_union, 1)],
    out_shape=dist_shape_hw,
    transform=dist_transform,
    fill=0,
    dtype=np.uint8,
)
```
PROMOTE into `effis.py`. Phase 5 D-17 adds the dual-rasterise:
```python
mask_at_false = rasterize(shapes=..., all_touched=False, ...)  # primary (gate value)
mask_at_true  = rasterize(shapes=..., all_touched=True,  ...)  # diagnostic only
```
Both `rasterio.features.rasterize` calls go inside `effis.py::rasterise_perimeters_to_grid()`. The diagnostic delta is reported in `metrics.json per_event[N].rasterisation_diagnostic: {all_touched_false_f1, all_touched_true_f1, delta_f1}` per D-17.

**Lazy-import pattern** (Phase 1 lazy-import discipline; matches `compare_dist.py:142-143`):
```python
def fetch_effis_perimeters(...) -> gpd.GeoDataFrame:
    """Query EFFIS WFS and return a GeoDataFrame in EPSG:4326."""
    from owslib.wfs import WebFeatureService
    from owslib.fes import And, BBox, PropertyIsBetween
    from owslib.fes2 import Filter as Filter2
    from owslib.etree import etree
    import geopandas
    from io import BytesIO
    ...
```
`owslib`, `geopandas`, `rasterio.features` ALL lazy-imported inside function bodies — preserves the import-time invariant that `subsideo.validation.*` modules don't drag conda-forge dependencies just by being imported (matches `harness.py:138` lazy `from opera_utils.burst_frame_db import get_burst_id_geojson`).

**Cache-by-mtime pattern** (`harness.py::ensure_resume_safe` lines 391-421 + `run_eval_dist_eu.py:357` `if not ems_geojsons:`):
```python
def fetch_effis_perimeters(event_id, bbox, dates, cache_dir) -> gpd.GeoDataFrame:
    cache_path = cache_dir / event_id / "effis_perimeters" / "perimeters.geojson"
    if cache_path.exists():
        return geopandas.read_file(cache_path)
    # ... fetch + write to cache_path
```
D-19 wired pattern: response stored at `eval-dist_eu/<event_id>/effis_perimeters/perimeters.geojson` for re-run determinism. Warm re-runs skip the WFS call; mtime check via `harness.ensure_resume_safe` is the cross-check.

**EFFIS query metadata for meta.json** (Phase 2 D-12 + Phase 5 D-19):
```python
@dataclass(frozen=True)
class EFFISQueryMeta:
    """Per-event EFFIS query trace for meta.json (D-19 reproducibility audit)."""
    wfs_endpoint: str
    layer_name: str
    filter_string: str
    response_feature_count: int
    fetched_at: str  # ISO-8601 UTC
```
Mirrors the per-burst input-hash dict pattern in `run_eval_rtc_eu.py:580-581` — eval script aggregates these into `meta.json input_hashes` (or, since the dataclass is structured, into a sibling `effis_query_meta` flat key per Phase 4 D-11 schema additivity).

**What to differ:**
- WFS dispatch goes through harness `download_reference_with_retry(source='effis')` per D-18 (NOT direct `wfs.getfeature` in eval script). The harness branch is the single network-policy enforcement point; `effis.py` calls the harness, not requests/owslib directly for retry semantics — but lazy-imports owslib for the actual WFS object construction (the harness only handles HTTP-layer retry, not WFS protocol).
- New `RETRY_POLICY['effis']` branch in `harness.py` (next section) defines the retry policy for WFS — `503/504/ConnectionError/TimeoutError` retried; `401/403/404` aborted; max 5 attempts with exponential backoff to 60s cap.
- The class-definition mismatch caveat (PITFALLS P4.5 — EFFIS "burnt" includes low-severity ground fire, clear-cuts; DIST "disturbed" includes windthrow, defoliation) is narrative-only in `docs/validation_methodology.md §4.3` per D-23. NOT enforced as a precision/recall floor adjustment in code.

---

### `src/subsideo/validation/harness.py` (MODIFY; utility, request-response)

**Analog:** Self (existing `RETRY_POLICY` dict at lines 50-70 + `download_reference_with_retry` lines 496-627)

**Why this analog:** Phase 1 ENV-06 (D-Claude's-Discretion) explicitly anticipated 5+ sources. The dispatch is purely a dict-key lookup; the function body needs ZERO changes. The Phase 5 addition is mechanically a 5th branch.

**Existing RETRY_POLICY shape** (`harness.py:50-70`):
```python
RetrySource = Literal["CDSE", "EARTHDATA", "CLOUDFRONT", "HTTPS"]

RETRY_POLICY: dict[str, dict[str, Any]] = {
    "CDSE": {
        "retry_on": [429, 503, "OutOfMemoryError"],
        "abort_on": [401, 403, 404],
    },
    "EARTHDATA": {
        "retry_on": [429, 503],
        "abort_on": [401, 403, 404],
    },
    "CLOUDFRONT": {
        "retry_on": [503, "ExpiredToken"],
        "abort_on": [401, 404],
        "refresh_url_on": [403],
    },
    "HTTPS": {
        "retry_on": [429, 503],
        "abort_on": [401, 403, 404],
    },
}
```

**Phase 5 addition** (new 5th branch — mirrors EARTHDATA exactly except for the explicit ConnectionError/TimeoutError addition because owslib raises those from urllib3 not as HTTP statuses):
```python
RetrySource = Literal["CDSE", "EARTHDATA", "CLOUDFRONT", "HTTPS", "EFFIS"]

RETRY_POLICY["EFFIS"] = {
    "retry_on": [429, 503, 504, "ConnectionError", "TimeoutError"],
    "abort_on": [401, 403, 404],
}
```
Insert AFTER `HTTPS` entry. The Literal extension is additive; `download_reference_with_retry` body needs NO change because it dispatches by `source not in RETRY_POLICY` check at line 542 only.

**Critical landmine** (per CR-02 mitigation at `harness.py:589-596`):
```python
# CR-02 mitigation: any HTTP error status that is NOT in
# ``retry_on`` must fail fast. Without this explicit branch,
# ``resp.raise_for_status()`` raises ``requests.HTTPError``
# which falls through to the ``except requests.RequestException``
# handler below and is silently retried up to ``max_retries``
# -- violating the per-source RETRY_POLICY contract
# (PITFALLS P0.4).
if status >= 400:
    raise ReferenceDownloadError(source, status, current_url)
```
For EFFIS, `503/504/429` go to `retry_on` (transient); `401/403/404` go to `abort_on` (caller refreshes credentials or fixes URL); anything else `>= 400` becomes `ReferenceDownloadError`. **Do NOT add EFFIS-specific status handling beyond the dict** — the existing dispatch at lines 561-572 already handles all four cases.

**What to differ from existing branches:**
- EFFIS responses are GML / SHAPEZIP / SPATIALITEZIP — NOT plain HTTPS file streams. The harness `download_reference_with_retry` body still works because it streams the response body to `.partial` and renames; `geopandas.read_file(BytesIO(downloaded_bytes))` parses GML/SHAPEZIP at the consumer end (see `effis.py` rasterise pattern above).
- Plan-phase MUST `GetCapabilities`-probe both candidate endpoints (Probe 3 + Probe 4 of RESEARCH) BEFORE committing the literal URL string. The endpoint URL goes in `effis.py` module-level constant (or eval-script `EVENTS` list per-event override), NOT in `harness.py`.

---

### `src/subsideo/validation/matrix_schema.py` (MODIFY; model, transform)

**Analog:** Self — the `DISPCellMetrics` block at lines 452-628 + `RTCEUCellMetrics` block at lines 255-307 + `BurstResult` block at lines 158-252.

**Why this analog:** Phase 4 D-11 schema-extension pattern is the binding precedent. Phase 5 ADDS new types; ZERO edits to existing types per Phase 1 D-09 big-bang lock.

**Existing pattern — separator comment + Pydantic v2 base** (`matrix_schema.py:452-456`):
```python
# --- Phase 4 DISP comparison-adapter cell metrics (CONTEXT D-11) ---

CoherenceSource = Literal["phase3-cached", "fresh"]
AttributedSource = Literal["phass", "orbit", "tropospheric", "mixed", "inconclusive"]
DISPCellStatus = Literal["PASS", "FAIL", "CALIBRATING", "MIXED", "BLOCKER"]
```

**Phase 5 mirror — separator + Literal aliases**:
```python
# --- Phase 5 DIST cell metrics (CONTEXT D-25) ---

DistEUEventID = Literal["aveiro", "evros", "spain_culebra"]  # NOT 'romania' — substituted per Probe 4
ChainedRunStatus = Literal["structurally_valid", "partial_output", "dist_s1_hang", "crashed", "skipped"]
CMRProbeOutcome = Literal["operational_found", "operational_not_found", "probe_failed"]
ReferenceSource = Literal["operational_v1", "v0.1_cloudfront", "none"]
DistEUCellStatus = Literal["PASS", "FAIL", "MIXED", "BLOCKER"]
DistNamCellStatus = Literal["PASS", "FAIL", "DEFERRED"]  # DEFERRED is the v1.1 default per scope correction
```

**MetricWithCI pattern** (NEW; mirrors `PerIFGRamp` field shape from `matrix_schema.py:459-494`):
```python
class MetricWithCI(BaseModel):
    """One reference-agreement metric with point estimate + bootstrap CI bounds (D-07)."""

    model_config = ConfigDict(extra="forbid")

    point: float = Field(..., description="Point estimate (e.g. F1 = 0.823).")
    ci_lower: float = Field(..., description="Lower bound at ci_level (default 95%).")
    ci_upper: float = Field(..., description="Upper bound at ci_level.")
```
Use `model_config = ConfigDict(extra="forbid")` + `Field(..., description=...)` — matches every existing Pydantic v2 model in this file (PATTERNS §4.5).

**BootstrapConfig pattern** (NEW; mirrors `RampAggregate` from lines 497-527):
```python
class BootstrapConfig(BaseModel):
    """Bootstrap configuration sub-block for reproducibility audit (D-09)."""

    model_config = ConfigDict(extra="forbid")

    block_size_m: int = Field(default=1000, description="Block edge length in metres (D-08 default).")
    n_bootstrap: int = Field(default=500, description="Number of bootstrap resamples (D-09 default).")
    ci_level: float = Field(default=0.95, description="Confidence interval level (D-07 default).")
    n_blocks_kept: int = Field(..., ge=0, description="Full blocks resampled.")
    n_blocks_dropped: int = Field(..., ge=0, description="Partial blocks dropped at tile edges (D-08).")
    rng_seed: int = Field(default=0, description="Fixed seed for default_rng (PCG64) per D-09.")
```

**RasterisationDiagnostic pattern** (NEW; D-17 EFFIS rasterisation transparency):
```python
class RasterisationDiagnostic(BaseModel):
    """all_touched=True vs False F1 delta for EFFIS rasterisation transparency (D-17)."""

    model_config = ConfigDict(extra="forbid")

    all_touched_false_f1: float = Field(..., description="Primary F1 (gate value).")
    all_touched_true_f1: float = Field(..., description="Diagnostic F1 (narrative-only).")
    delta_f1: float = Field(..., description="all_touched_true - all_touched_false. PITFALLS P4.4 expected ~2-4pp.")
```

**ChainedRunResult pattern** (NEW; D-13/D-14 differentiator framing):
```python
class ChainedRunResult(BaseModel):
    """Aveiro chained prior_dist_s1_product retry result (D-13, D-14)."""

    model_config = ConfigDict(extra="forbid")

    status: ChainedRunStatus = Field(..., description="See ChainedRunStatus Literal.")
    output_dir: str | None = Field(default=None, description="Path to chained product dir; None on skip/crash.")
    n_layers_present: int | None = Field(default=None, ge=0, le=10, description="10 expected per OPERA spec.")
    dist_status_nonempty: bool | None = Field(default=None, description="DIST-STATUS layer has >=1 non-zero pixel.")
    error: str | None = Field(default=None, description="repr(exception) on crashed/dist_s1_hang.")
    traceback: str | None = Field(default=None, description="traceback.format_exc() on crashed.")
```

**EFFISQueryMeta pattern** (NEW; D-19 reproducibility audit):
```python
class EFFISQueryMeta(BaseModel):
    """Per-event EFFIS WFS query metadata for meta.json (D-19)."""

    model_config = ConfigDict(extra="forbid")

    wfs_endpoint: str = Field(..., description="WFS GetFeature endpoint URL.")
    layer_name: str = Field(..., description="WFS typename, e.g. 'ms:modis.ba.poly'.")
    filter_string: str = Field(..., description="OGC Filter XML serialised.")
    response_feature_count: int = Field(..., ge=0, description="Number of features returned.")
    fetched_at: str = Field(..., description="ISO-8601 UTC fetch timestamp.")
```

**DistEUEventMetrics pattern** (NEW; mirrors `BurstResult` shape — error/traceback pattern from lines 238-252):
```python
class DistEUEventMetrics(BaseModel):
    """Per-event sub-result row inside DistEUCellMetrics.per_event (D-10)."""

    model_config = ConfigDict(extra="forbid")

    event_id: DistEUEventID = Field(..., description="Aveiro / Evros / Spain_culebra.")
    status: Literal["PASS", "FAIL"] = Field(..., description="Per-event verdict from F1 + precision + recall criteria.")
    f1: MetricWithCI = Field(..., description="F1 with 95% block-bootstrap CI.")
    precision: MetricWithCI = Field(..., description="Precision with CI.")
    recall: MetricWithCI = Field(..., description="Recall with CI.")
    accuracy: MetricWithCI = Field(..., description="Overall accuracy with CI.")
    rasterisation_diagnostic: RasterisationDiagnostic = Field(..., description="all_touched delta (D-17).")
    bootstrap_config: BootstrapConfig = Field(..., description="Bootstrap params for reproducibility.")
    effis_query_meta: EFFISQueryMeta = Field(..., description="EFFIS WFS query trace.")
    chained_run: ChainedRunResult | None = Field(
        default=None,
        description="Aveiro-only differentiator (D-13/D-14); None for evros + spain_culebra.",
    )
    error: str | None = Field(default=None, description="repr(exception) on event-level failure.")
    traceback: str | None = Field(default=None, description="traceback.format_exc() on event-level failure.")
```

**DistEUCellMetrics pattern** (NEW; mirrors `RTCEUCellMetrics` from lines 255-307):
```python
class DistEUCellMetrics(MetricsJson):
    """Phase 5 EU DIST aggregate cell (D-10).

    matrix_writer detects this schema via presence of ``per_event`` in raw JSON.
    """

    pass_count: int = Field(..., ge=0, description="Count of events with status == 'PASS'.")
    total: int = Field(..., ge=1, description="Total events (3: aveiro, evros, spain_culebra).")
    all_pass: bool = Field(..., description="True when pass_count == total.")
    cell_status: DistEUCellStatus = Field(..., description="Whole-cell verdict.")
    worst_event_id: str = Field(..., description="event_id of the lowest-F1 event.")
    worst_f1: float = Field(..., description="Lowest F1 across events (point estimate).")
    any_chained_run_failed: bool = Field(
        ...,
        description="True if Aveiro chained_run.status not in {'structurally_valid', 'skipped'}.",
    )
    per_event: list[DistEUEventMetrics] = Field(
        default_factory=list,
        description="Per-event drilldown; order matches EVENTS list in run_eval_dist_eu.py.",
    )
```

**Deferred-cell DistNamCellMetrics shape (Phase 5 scope correction)**:
Per `<important_scope_correction>`, Phase 5 SKIPS `DistNamCellMetrics + ConfigDriftReport` for v1.2. The `dist:nam` cell instead writes the BASE `MetricsJson` schema with `cell_status='deferred'`, `reference_source='none'`, `cmr_probe_outcome='operational_not_found'` + empty `product_quality.measurements` + `reference_agreement.measurements`. No new Pydantic types required.

To carry the `cell_status='deferred'` literal in the BASE `MetricsJson`, Phase 5 EITHER:
- **Option A:** Adds a new `DistNamCellMetrics` minimal Pydantic v2 type with just `cell_status: Literal['DEFERRED'] = 'DEFERRED'` + `reference_source: ReferenceSource = 'none'` + `cmr_probe_outcome: CMRProbeOutcome` (this is the cleanest read-time-discriminable shape for matrix_writer).
- **Option B:** Writes a free-form `cell_status` key into a top-level dict and lets matrix_writer inspect it. Less clean.

**Recommendation:** Option A — the minimal `DistNamCellMetrics` shape (3 new fields, ~10 LOC) is additive, clean, and gives matrix_writer a clear `_is_dist_nam_shape` discriminator. v1.2 EXTENDS this same class with `config_drift: ConfigDriftReport`, `reference_agreement.metrics: dict[str, MetricWithCI]`, `bootstrap_config: BootstrapConfig` when the operational reference publishes — additive evolution per D-09.

**What to differ from existing types:**
- Phase 5 D-19/D-22 `cell_status` Literal uses `'DEFERRED'` for the dist:nam cell (per `DistNamCellStatus = Literal["PASS", "FAIL", "DEFERRED"]`). This is the FIRST `DEFERRED` cell status across the matrix; `matrix_writer.py` needs the matching render branch (next section).
- `DistEUEventID` Literal uses `'spain_culebra'` (NOT `'romania'`) per RESEARCH Probe 4 substitution + scope correction.

---

### `src/subsideo/validation/matrix_writer.py` (MODIFY; service, transform-render)

**Analog:** Self — `_render_disp_cell` lines 372-437 + `_is_disp_cell_shape` lines 354-369 + dispatch insertion at line 480-488.

**Why this analog:** Phase 4 D-08 ordering invariant: insert AFTER `disp:*` BEFORE the future `dswx:*`. The render-branch pattern is:
1. Schema discriminator (`_is_X_shape(metrics_path) -> bool`) inspects raw JSON for a unique top-level key.
2. Render function (`_render_X_cell(metrics_path, *, region) -> tuple[str, str] | None`) returns `(pq_col, ra_col)` or None on parse fail.
3. Dispatch in `write_matrix()` checks `metrics_path.exists() and _is_X_shape(metrics_path)` BEFORE `_load_metrics` (because base `MetricsJson` uses `extra="forbid"` and would reject schema-specific fields).

**Existing dispatch order** (`matrix_writer.py:480-528`):
```python
# Phase 4 DISP branch -- ramp_attribution key
if metrics_path.exists() and _is_disp_cell_shape(metrics_path):
    cols = _render_disp_cell(metrics_path, region=str(cell["region"]))
    if cols is not None:
        ...

# Phase 3 CSLC self-consist branch -- per_aoi key
if metrics_path.exists() and _is_cslc_selfconsist_shape(metrics_path):
    cols = _render_cslc_selfconsist_cell(metrics_path, region=str(cell["region"]))
    ...

# Phase 2 RTC-EU branch -- per_burst key
if metrics_path.exists() and _is_rtc_eu_shape(metrics_path):
    cols = _render_rtc_eu_cell(metrics_path)
    ...
```
Phase 5 inserts TWO new branches: `_is_dist_eu_shape` (per_event key) + `_is_dist_nam_shape` (cell_status='DEFERRED' key). Order: AFTER disp:* per Phase 4 D-08 ordering invariant.

**Insertion-point pattern** (NEW; mirrors `_is_disp_cell_shape` lines 354-369):
```python
# --- Phase 5 DIST rendering (CONTEXT D-24) ---


def _is_dist_eu_shape(metrics_path: Path) -> bool:
    """Return True when metrics.json has a top-level ``per_event`` key.

    Phase 5 D-25 schema discriminator. Checked BEFORE _is_disp_cell_shape
    (ramp_attribution), _is_cslc_selfconsist_shape (per_aoi), _is_rtc_eu_shape
    (per_burst); per_event is structurally disjoint from all three.
    """
    import json as _json

    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.debug("_is_dist_eu_shape: cannot read {}: {}", metrics_path, e)
        return False
    return isinstance(raw, dict) and "per_event" in raw


def _is_dist_nam_shape(metrics_path: Path) -> bool:
    """Return True when metrics.json has cell_status == 'DEFERRED' + reference_source key.

    Phase 5 deferred-cell discriminator (scope-correction: dist:nam ships as
    deferred until OPERA_L3_DIST-ALERT-S1_V1 publishes operationally; the
    auto-supersede CMR probe in run_eval_dist.py Stage 0 will repopulate the
    cell when operational appears).
    """
    import json as _json

    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.debug("_is_dist_nam_shape: cannot read {}: {}", metrics_path, e)
        return False
    return (
        isinstance(raw, dict)
        and raw.get("cell_status") == "DEFERRED"
        and "reference_source" in raw
    )
```

**Render-function pattern** (NEW; mirrors `_render_rtc_eu_cell` lines 184-230 for X/N PASS aggregate):
```python
def _render_dist_eu_cell(metrics_path: Path) -> tuple[str, str] | None:
    """Render Phase 5 DIST-EU multi-event aggregate as (pq_col, ra_col).

    pq_col: '—' (DIST has no product-quality gate; per CONTEXT D-25 Not-this-phase).
    ra_col format: 'X/3 PASS' or 'X/3 PASS (Y FAIL)' + worst F1 + chained-retry warning glyph.
    """
    from subsideo.validation.matrix_schema import DistEUCellMetrics

    try:
        m = DistEUCellMetrics.model_validate_json(metrics_path.read_text())
    except Exception as e:
        logger.warning("Failed to parse DistEUCellMetrics from {}: {}", metrics_path, e)
        return None

    fail_count = m.total - m.pass_count
    if fail_count > 0:
        base = f"{m.pass_count}/{m.total} PASS ({fail_count} FAIL)"
    else:
        base = f"{m.pass_count}/{m.total} PASS"
    base += f" | worst f1={m.worst_f1:.3f} ({m.worst_event_id})"
    warn = " ⚠" if m.any_chained_run_failed else ""
    ra_col = f"{base}{warn}"
    pq_col = "—"
    return pq_col, ra_col


def _render_dist_nam_deferred_cell(metrics_path: Path) -> tuple[str, str] | None:
    """Render the deferred dist:nam cell (Phase 5 scope correction)."""
    import json as _json

    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.warning("Failed to read deferred dist:nam metrics from {}: {}", metrics_path, e)
        return None

    cmr_outcome = raw.get("cmr_probe_outcome", "probe_failed")
    pq_col = "—"
    ra_col = f"DEFERRED (CMR: {cmr_outcome})"
    return pq_col, ra_col
```

**Dispatch insertion** — INSERT AFTER existing `disp:*` branch at line 488 (per Phase 4 D-08 ordering: disp BEFORE dist BEFORE dswx). Phase 5 adds:
```python
# Phase 5 DIST-EU branch -- per_event key
if metrics_path.exists() and _is_dist_eu_shape(metrics_path):
    cols = _render_dist_eu_cell(metrics_path)
    if cols is not None:
        pq_col, ra_col = cols
        lines.append(
            f"| {product} | {region} | {_escape_table_cell(pq_col)} | "
            f"{_escape_table_cell(ra_col)} |"
        )
        continue

# Phase 5 DIST-NAM deferred-cell branch
if metrics_path.exists() and _is_dist_nam_shape(metrics_path):
    cols = _render_dist_nam_deferred_cell(metrics_path)
    if cols is not None:
        pq_col, ra_col = cols
        lines.append(
            f"| {product} | {region} | {_escape_table_cell(pq_col)} | "
            f"{_escape_table_cell(ra_col)} |"
        )
        continue
```

**What to differ from existing branches:**
- DIST is the FIRST cell with a DEFERRED state (PHASE 5 D-19 + scope correction). Existing cells render PASS/FAIL/CALIBRATING/MIXED/BLOCKER; the deferred-cell render is "DEFERRED (CMR: operational_not_found)" — explicit + auditable.
- No italics for DIST (no CALIBRATING criteria; per `criteria.py:172-186` DIST entries are BINDING only).
- Worst-event-attribution `worst f1=X.XXX (event_id)` mirrors the CSLC self-consistency W8 fix worst-AOI attribution at `matrix_writer.py:323-326`.
- Warning glyph `U+26A0` for `any_chained_run_failed=True` mirrors `_render_rtc_eu_cell` at line 227.

---

### `src/subsideo/validation/compare_dist.py` (MODIFY; service, transform)

**Analog:** Self — existing `compare_dist` at lines 112-230 + binarisation pattern at lines 80-109.

**Why this analog:** Per scope correction, Phase 5 ADDS only bootstrap CI plumbing (NOT config-drift extraction; that defers to v1.2). The bootstrap CI wrapping is mechanically a 4-call addition around existing F1/precision/recall/accuracy point-estimate calls.

**Existing F1 computation block** (`compare_dist.py:199-216`):
```python
pred = prod_bin[valid].astype(np.int32)
ref = ref_bin[valid].astype(np.int32)

# 6. Compute metrics.
f1 = f1_score(pred, ref)
prec = precision_score(pred, ref)
rec = recall_score(pred, ref)
acc = overall_accuracy(pred, ref)

logger.info(
    "DIST-S1 validation: F1={:.4f}, precision={:.4f}, "
    "recall={:.4f}, OA={:.4f} (n={:,})",
    f1, prec, rec, acc, n_valid,
)
```

**Phase 5 wrapping pattern** (NEW; ADD a new function `compare_dist_with_ci` next to existing `compare_dist`; do NOT modify the existing function — Phase 1 D-09 immutability):
```python
def compare_dist_with_ci(
    product_path: Path,
    reference_path: Path,
    *,
    pixel_size_m: int = 30,
    block_size_m: int = 1000,
    n_bootstrap: int = 500,
    rng_seed: int = 0,
    disturbed_labels: frozenset[int] = DIST_DISTURBED_LABELS,
) -> tuple[DISTValidationResult, dict[str, "BootstrapResult"]]:
    """Phase 5 DIST validation with block-bootstrap CI on F1/precision/recall/accuracy.

    Returns the existing DISTValidationResult (point estimates) PLUS a dict
    {'f1': BootstrapResult, 'precision': BootstrapResult, ...} with 95% CI.
    """
    from subsideo.validation.bootstrap import block_bootstrap_ci, BootstrapResult

    # ... reuse existing compare_dist body lines 142-198 verbatim to get prod_bin, ref_bin, valid
    # Reshape to 2-D for spatial-block bootstrap (existing valid mask collapses to 1-D pred/ref)
    # Bootstrap each metric:
    f1_ci = block_bootstrap_ci(
        prod_bin_2d, ref_bin_2d, metric_fn=f1_score,
        block_size_m=block_size_m, pixel_size_m=pixel_size_m,
        n_bootstrap=n_bootstrap, rng_seed=rng_seed,
    )
    prec_ci = block_bootstrap_ci(prod_bin_2d, ref_bin_2d, metric_fn=precision_score, ...)
    rec_ci = block_bootstrap_ci(prod_bin_2d, ref_bin_2d, metric_fn=recall_score, ...)
    acc_ci = block_bootstrap_ci(prod_bin_2d, ref_bin_2d, metric_fn=overall_accuracy, ...)

    # Wrap in DISTValidationResult per existing shape (lines 218-230)
    result = DISTValidationResult(
        product_quality=ProductQualityResult(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResult(
            measurements={
                "f1": f1_ci.point_estimate,
                "precision": prec_ci.point_estimate,
                "recall": rec_ci.point_estimate,
                "accuracy": acc_ci.point_estimate,
                "n_valid_pixels": float(n_valid),
            },
            criterion_ids=["dist.f1_min", "dist.accuracy_min"],
        ),
    )
    ci_results = {"f1": f1_ci, "precision": prec_ci, "recall": rec_ci, "accuracy": acc_ci}
    return result, ci_results
```

**Critical:** The existing `compare_dist` function STAYS UNCHANGED (Phase 1 D-09 immutability + the v1.0 N.Am. Park Fire artefact still uses it). Phase 5 EU `run_eval_dist_eu.py` imports `compare_dist_with_ci` (NEW); v1.0 N.Am. `run_eval_dist.py` continues to import `compare_dist` (legacy point-estimate only, since dist:nam is deferred per scope correction and won't land F1+CI numbers in Phase 5).

**Lazy import** (matches `compare_dist.py:142-143`):
```python
def compare_dist_with_ci(...):
    import rasterio  # already lazy in existing compare_dist
    from subsideo.validation.bootstrap import block_bootstrap_ci, BootstrapResult  # NEW
    ...
```

**What to differ from existing function:**
- New function takes `*, pixel_size_m, block_size_m, n_bootstrap, rng_seed` keyword-only args — matches `block_bootstrap_ci` signature.
- Returns 2-tuple `(DISTValidationResult, dict[str, BootstrapResult])` — caller (eval script) serialises both into `MetricWithCI` Pydantic shape per D-07.
- Existing 1-D `pred`/`ref` arrays in `compare_dist` insufficient for spatial bootstrap — `compare_dist_with_ci` keeps the 2-D `prod_bin` + `ref_bin` arrays (with NaN propagating to invalid pixels) for block-index gather.

---

### `run_eval_dist.py` (MODIFY; controller, event-driven)

**Analog:** Self (v1.0 Park Fire eval, lines 64-451) + the Stage 2 CMR probe at lines 167-188.

**Why this analog:** Per scope correction, Phase 5 ADDS Stage 0 CMR probe + writes a "deferred" `metrics.json` ONLY. The full T11SLT processing logic (config-drift, F1, bootstrap) is DEFERRED to v1.2.

**Existing Stage 2 CMR probe** (`run_eval_dist.py:167-188`):
```python
short_names_to_try = [
    "OPERA_L3_DIST-ALERT-S1_V1",
    "OPERA_L3_DIST-S1_V1",
    "OPERA_L3_DIST-ANN-S1_V1",
    "OPERA_L3_DIST_PROVISIONAL_V0",
]
for sn in short_names_to_try:
    try:
        r = earthaccess.search_data(
            short_name=sn,
            temporal=(DATE_START, DATE_END),
            bounding_box=AOI_BBOX,
            count=20,
        )
        n = len(r) if r else 0
        print(f"  {sn}: {n} hit(s)")
        if r:
            opera_results.extend(r)
            break
    except Exception as exc:
        print(f"  {sn}: ERR {str(exc)[:80]}")
```

**Phase 5 reframe** — Stage 0 CMR probe with auto-supersede branch (D-15):
```python
# Stage 0: CMR auto-supersede probe (D-15)
print("-- Stage 0: CMR probe for operational OPERA_L3_DIST-ALERT-S1_V1 --")
auth = earthaccess.login(strategy="environment")
bbox = bounds_for_mgrs_tile(MGRS_TILE)  # T11SLT
post_dt = datetime.fromisoformat(POST_DATE)
temporal = (
    (post_dt - timedelta(days=CMR_TEMPORAL_TOLERANCE_DAYS)).strftime("%Y-%m-%d"),
    (post_dt + timedelta(days=CMR_TEMPORAL_TOLERANCE_DAYS)).strftime("%Y-%m-%d"),
)

cmr_probe_outcome: CMRProbeOutcome
reference_source: ReferenceSource
try:
    results = earthaccess.search_data(
        short_name="OPERA_L3_DIST-ALERT-S1_V1",
        bounding_box=bbox,
        temporal=temporal,
        count=20,
    )
    if results:
        cmr_probe_outcome = "operational_found"
        reference_source = "operational_v1"
        # ... v1.2 path: download + run full pipeline
        raise NotImplementedError(
            "Operational reference now exists -- full pipeline path is v1.2 work. "
            "Phase 5 scope-correction defers DIST-01/02/03."
        )
    else:
        cmr_probe_outcome = "operational_not_found"
        reference_source = "none"
except Exception as e:
    logger.error("CMR probe failed: {}", e)
    cmr_probe_outcome = "probe_failed"
    reference_source = "none"
```

**Deferred metrics.json write pattern** (NEW; scope-correction):
```python
# Stage 1: Write deferred metrics.json (scope-correction)
deferred_metrics = {
    "schema_version": 1,
    "cell_status": "DEFERRED",
    "reference_source": reference_source,
    "cmr_probe_outcome": cmr_probe_outcome,
    "reference_granule_id": None,
    "product_quality": {"measurements": {}, "criterion_ids": []},
    "reference_agreement": {"measurements": {}, "criterion_ids": []},
    "criterion_ids_applied": [],
    "deferred_reason": (
        "Phase 5 scope correction: DIST-01/02/03 deferred to v1.2 once "
        "OPERA_L3_DIST-ALERT-S1_V1 publishes. CMR probe Stage 0 runs every "
        "invocation; auto-superseded when operational lands."
    ),
}
metrics_path = OUT / "metrics.json"
metrics_path.write_text(json.dumps(deferred_metrics, indent=2))
```

**Critical landmines** (per cross-cutting D-20/D-21 + Phase 1 ENV-04 + ENV-05):
- `_mp.configure_multiprocessing()` MUST fire at the very top of `main()` BEFORE `earthaccess.login()` (Phase 1 ENV-04). v1.0 `run_eval_dist.py` does NOT currently call this — Phase 5 ADDS it.
- `EXPECTED_WALL_S` declaration at module top per Phase 1 D-11 (line 64 already has `EXPECTED_WALL_S = 1800`; Phase 5 may TIGHTEN to 600 since the deferred-cell write is a 1-minute CMR probe + JSON dump, not a 30-minute full pipeline run).
- `from subsideo._mp import configure_multiprocessing` import must come BEFORE any `requests.Session`-using import (P0.1 mitigation) — applies even though Phase 5 dist:nam doesn't run dist-s1 (the import-graph warming still matters for the `earthaccess` HTTPS session).

**Park Fire migration** (D-05):
- `git mv eval-dist/ eval-dist-park-fire/` at Phase 5 start (preserves cache + run.log + opera_reference/).
- New `eval-dist/` directory created fresh. The metrics.json written by the deferred-cell path lives at `eval-dist/metrics.json`.
- v1.0 Park Fire content in `run_eval_dist.py` (lines 96-451) is REPOINTED to T11SLT inline per CONTEXT.md Claude's-Discretion item "(a) — the v1.0 Park Fire script content was a 'structurally complete' run anyway; T11SLT inherits the structure". With the scope correction, however, MOST of the inherited structure (Stages 4-7 dist-s1 invocation + compare) is GUARDED behind the `cmr_probe_outcome == 'operational_found'` branch and raises `NotImplementedError` for Phase 5 (NOT executed; v1.2 work).

**What to differ from existing script:**
- Stage 0 (NEW) replaces the v1.0 Stage 2 free-form short_names_to_try loop — single canonical short_name `OPERA_L3_DIST-ALERT-S1_V1` per RESEARCH Probe 6.
- v1.0 Stages 3-7 (download → enumerate → run_dist → compare) are GATED on `cmr_probe_outcome == 'operational_found'` and raise NotImplementedError otherwise. v1.2 implements the gated path.
- `metrics.json` write now goes through the new `_is_dist_nam_shape` discriminator path in `matrix_writer.py` — `cell_status: 'DEFERRED'` + `reference_source` + `cmr_probe_outcome` keys are read by the deferred-cell render.

---

### `run_eval_dist_eu.py` (REWRITE; controller, event-driven multi-event)

**Analog:** `run_eval_rtc_eu.py` (entire file; declarative `BURSTS: list[BurstConfig]` + per-burst try/except + aggregate `RTCEUCellMetrics` write).

**Why this analog:** Phase 2 D-05/D-06 declarative-AOIS-list pattern is the binding precedent for multi-{burst,AOI,event} aggregate cells. RTC-EU has 5 bursts; DIST-EU has 3 events. Same pattern, different cardinality.

**EXPECTED_WALL_S declaration** (`run_eval_rtc_eu.py:35`):
```python
EXPECTED_WALL_S = 60 * 60 * 4   # 14400s; supervisor AST-parses (D-11 + T-07-06)
```
Phase 5 estimate (per RESEARCH §Recommended Wave Structure + D-12): 6-10 hours for 3 events × ~2h cold + chained retry. Use:
```python
EXPECTED_WALL_S = 60 * 60 * 8   # 28800s; 3 events x 2h cold + chained retry + safety margin
```

**Declarative EVENTS list pattern** (mirrors `BURSTS: list[BurstConfig]` at `run_eval_rtc_eu.py:108-188`):
```python
@dataclass(frozen=True)
class EventConfig:
    """Per-event declarative config for run_eval_dist_eu.EVENTS (D-11)."""
    event_id: Literal["aveiro", "evros", "spain_culebra"]
    post_dates: list[date]              # 1 entry for evros + spain_culebra; 3 entries for aveiro chained triple
    pre_dates: list[date]               # for narrative; dist-s1 auto-fetches via track_number
    aoi_bbox_wgs84: tuple[float, float, float, float]  # (W, S, E, N)
    mgrs_tile: str
    track_number: int
    effis_layer_name: str
    effis_filter_dates: tuple[date, date]   # (start, end) for PropertyIsBetween('firedate', ...)
    expected_burnt_area_km2: float           # narrative sanity check; not a gate
    run_chained: bool                        # True for aveiro only

EVENTS: list[EventConfig] = [
    EventConfig(
        event_id="aveiro",
        post_dates=[date(2024, 9, 28), date(2024, 10, 10), date(2024, 11, 15)],  # chained triple
        pre_dates=[],  # dist-s1 multi-window auto-fetch
        aoi_bbox_wgs84=(-8.8, 40.5, -8.2, 41.0),
        mgrs_tile="29TNF",
        track_number=147,
        effis_layer_name="ms:modis.ba.poly",  # plan-phase confirms
        effis_filter_dates=(date(2024, 9, 15), date(2024, 9, 25)),
        expected_burnt_area_km2=1350.0,  # 135,000 ha
        run_chained=True,
    ),
    EventConfig(
        event_id="evros",  # EMSR686 (NOT EMSR649)
        post_dates=[date(2023, 9, 5)],
        pre_dates=[],
        aoi_bbox_wgs84=(25.9, 40.7, 26.7, 41.4),
        mgrs_tile="35TLF",  # plan-phase confirms via dist_s1_enumerator
        track_number=0,  # plan-phase confirms
        effis_layer_name="ms:modis.ba.poly",
        effis_filter_dates=(date(2023, 8, 19), date(2023, 9, 8)),
        expected_burnt_area_km2=942.5,  # 94,250 ha — largest EU forest fire ever
        run_chained=False,
    ),
    EventConfig(
        event_id="spain_culebra",  # NOT romania (Probe 4 substitution)
        post_dates=[date(2022, 6, 28)],
        pre_dates=[],
        aoi_bbox_wgs84=(-6.5, 41.7, -5.9, 42.2),
        mgrs_tile="29TQG",  # plan-phase confirms
        track_number=0,
        effis_layer_name="ms:modis.ba.poly",
        effis_filter_dates=(date(2022, 6, 15), date(2022, 6, 22)),
        expected_burnt_area_km2=260.0,  # 26,000 ha
        run_chained=False,
    ),
]
```

**Per-event try/except + aggregate pattern** (mirrors `run_eval_rtc_eu.py:560-608`):
```python
per_event: list[DistEUEventMetrics] = []
for cfg in EVENTS:
    t0 = time.time()
    try:
        row = process_event(cfg)
        per_event.append(row)
        logger.info("Event {} PASS in {:.0f}s", cfg.event_id, time.time() - t0)
    except Exception as e:  # noqa: BLE001 - per-event isolation (Phase 2 D-06 pattern)
        tb = traceback.format_exc()
        logger.error("Event {} FAIL ({:.0f}s): {}", cfg.event_id, time.time() - t0, e)
        per_event.append(
            DistEUEventMetrics(
                event_id=cfg.event_id,
                status="FAIL",
                f1=MetricWithCI(point=0.0, ci_lower=0.0, ci_upper=0.0),
                precision=MetricWithCI(point=0.0, ci_lower=0.0, ci_upper=0.0),
                recall=MetricWithCI(point=0.0, ci_lower=0.0, ci_upper=0.0),
                accuracy=MetricWithCI(point=0.0, ci_lower=0.0, ci_upper=0.0),
                rasterisation_diagnostic=RasterisationDiagnostic(
                    all_touched_false_f1=0.0, all_touched_true_f1=0.0, delta_f1=0.0,
                ),
                bootstrap_config=BootstrapConfig(n_blocks_kept=0, n_blocks_dropped=0),
                effis_query_meta=EFFISQueryMeta(
                    wfs_endpoint="", layer_name="", filter_string="",
                    response_feature_count=0, fetched_at="",
                ),
                chained_run=None,
                error=repr(e),
                traceback=tb,
            )
        )
```

**Aveiro chained_run sub-stage** (D-13/D-14; embedded in aveiro `process_event`):
```python
def process_event(cfg: EventConfig) -> DistEUEventMetrics:
    # ... pre-fetch / enumerate / 3x run_dist (Sept 28 → Oct 10 → Nov 15) un-chained
    # ... EFFIS download via harness (source='effis')
    # ... rasterise via effis.py with all_touched=False + diagnostic
    # ... compare_dist_with_ci (F1 + CI)

    chained_run_result: ChainedRunResult | None = None
    if cfg.run_chained:
        try:
            # Re-run Nov 15 with prior_dist_s1_product=<Oct 10 output> (which had prior=<Sept 28>)
            chained_dst = CACHE / cfg.event_id / "chained"
            chained_dst.mkdir(parents=True, exist_ok=True)
            from dist_s1 import run_dist_s1_workflow
            run_dist_s1_workflow(
                mgrs_tile_id=cfg.mgrs_tile,
                post_date=cfg.post_dates[-1].isoformat(),  # 2024-11-15
                track_number=cfg.track_number,
                dst_dir=chained_dst,
                post_date_buffer_days=5,
                device="cpu",
                prior_dist_s1_product=str(oct10_output_dir),  # Oct 10 product as prior
            )
            # Pass criterion D-14: structurally-valid 10-layer DIST-ALERT product
            from dist_s1.data_models.output_models import DistS1ProductDirectory
            prod = DistS1ProductDirectory.from_path(chained_dst)
            n_layers = len([p for p in chained_dst.glob("*GEN-*.tif")])
            dist_status = next(chained_dst.glob("*GEN-DIST-STATUS.tif"), None)
            with rasterio.open(dist_status) as ds:
                nonempty = bool((ds.read(1) > 0).any())
            chained_run_result = ChainedRunResult(
                status="structurally_valid" if (n_layers == 10 and nonempty) else "partial_output",
                output_dir=str(chained_dst),
                n_layers_present=n_layers,
                dist_status_nonempty=nonempty,
            )
        except Exception as e:
            chained_run_result = ChainedRunResult(
                status="crashed",  # or 'dist_s1_hang' if timeout-detected
                error=repr(e),
                traceback=traceback.format_exc(),
            )

    return DistEUEventMetrics(
        event_id=cfg.event_id,
        status="PASS" if (...) else "FAIL",
        f1=MetricWithCI(point=f1_ci.point_estimate, ci_lower=f1_ci.ci_lower, ci_upper=f1_ci.ci_upper),
        # ... rest of metrics + chained_run=chained_run_result
        chained_run=chained_run_result,
    )
```

**Pass criteria** (DIST-05 + criteria.py BINDING entries):
```python
# Per-event status determined by point estimates against existing BINDING criteria
f1_pass = f1_ci.point_estimate > float(CRITERIA["dist.f1_min"].threshold)  # > 0.80
acc_pass = acc_ci.point_estimate > float(CRITERIA["dist.accuracy_min"].threshold)  # > 0.85
# DIST-05 specific: precision > 0.70 AND recall > 0.50 (NOT in criteria.py — narrative-only)
prec_pass = prec_ci.point_estimate > 0.70
rec_pass = rec_ci.point_estimate > 0.50
status = "PASS" if (f1_pass and acc_pass and prec_pass and rec_pass) else "FAIL"
```
**Critical:** No new criteria.py entries needed (DIST-05's `precision > 0.70 AND recall > 0.50` is enforced inline; per Phase 1 D-09 immutability + Phase 5 D-25 "ZERO edits to existing types"). The existing `dist.f1_min` + `dist.accuracy_min` BINDING entries inherit unchanged.

**Aggregate write pattern** (mirrors `run_eval_rtc_eu.py:613-697`):
```python
pass_count = sum(1 for r in per_event if r.status == "PASS")
total = len(per_event)
worst_event = min(per_event, key=lambda r: r.f1.point)
any_chained_failed = any(
    r.chained_run is not None and r.chained_run.status not in ("structurally_valid", "skipped")
    for r in per_event
)
metrics = DistEUCellMetrics(
    product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
    reference_agreement=ReferenceAgreementResultJson(
        measurements={"worst_f1": worst_event.f1.point}, criterion_ids=["dist.f1_min", "dist.accuracy_min"],
    ),
    criterion_ids_applied=["dist.f1_min", "dist.accuracy_min"],
    pass_count=pass_count,
    total=total,
    all_pass=(pass_count == total),
    cell_status="PASS" if pass_count == total else ("MIXED" if pass_count > 0 else "FAIL"),
    worst_event_id=worst_event.event_id,
    worst_f1=worst_event.f1.point,
    any_chained_run_failed=any_chained_failed,
    per_event=per_event,
)
metrics_path = CACHE / "metrics.json"
metrics_path.write_text(metrics.model_dump_json(indent=2))
```

**Cache directory consolidation** (D-11 + Open Question 4):
- Existing: `eval-dist-eu/` (hyphen) + `eval-dist-eu-nov15/` (hyphen)
- Manifest convention: `eval-dist_eu/` (underscore, line 79 of `matrix_manifest.yml`)
- Phase 5 action: `git mv eval-dist-eu/ eval-dist_eu/` + migrate Nov 15 contents into `eval-dist_eu/aveiro/chained/` (consolidates 2 directories into 1).

**Critical landmines:**
- `_mp.configure_multiprocessing()` MUST fire at very top of `main()` BEFORE `earthaccess.login()` AND BEFORE `from dist_s1 import run_dist_s1_workflow` import (P0.1 — chained retry hangs without it). v1.0 scripts MISS this; Phase 5 rewrite ADDS it.
- `EXPECTED_WALL_S` is supervisor-AST-parsed (T-07-06); MUST be a literal int or BinOp of literal int Constants. Use `60 * 60 * 8` form, NOT `8 * 3600` if 3600 is ever a Name reference.
- Per-event try/except isolates failures so 1 broken event doesn't kill the matrix cell (Phase 2 D-06).
- Per-stage `harness.ensure_resume_safe(cache_dir, manifest_keys)` for warm re-runs (Phase 1 D-Claude's-Discretion ENV-06; mirrors `run_eval_rtc_eu.py:478` pattern).
- `dist_s1.run_dist_s1_workflow` invokes joblib/loky → CFNetwork pool → fork hang on macOS without `_mp` bundle. The chained retry is THE binding test for this pre-condition (Phase 1 ENV-04 acceptance criterion was 3 consecutive fresh non-hang runs; Phase 5 EU eval is the 4th+ such proof).

**v1.0 Nov 15 script migration**:
The existing `run_eval_dist_eu_nov15.py` (532 LOC, mostly identical to `run_eval_dist_eu.py` with `POST_DATE = "2024-11-15"` + cache dir `eval-dist-eu-nov15/`) MIGRATES into the aveiro entry's `process_event` body — specifically, the Nov 15 dist-s1 invocation becomes part of the chained triple `run_dist_s1_workflow(post_date='2024-11-15', prior_dist_s1_product=<Oct 10 output>)` call. After migration, `run_eval_dist_eu_nov15.py` is `git rm`'d at Phase 5 close.

**What to differ from `run_eval_rtc_eu.py`:**
- `BURSTS` → `EVENTS` (semantic rename; same shape).
- 5 bursts → 3 events.
- No DEM fetch (dist-s1 auto-handles); no orbit fetch (dist-s1 auto-handles).
- Per-burst BurstResult.error/traceback → per-event DistEUEventMetrics.error/traceback (same shape).
- New chained_run sub-stage for aveiro (no analog in RTC).
- New EFFIS download stage for each event (no analog in RTC; RTC compares against OPERA reference).
- Aggregate `worst_rmse_db / worst_correlation` → `worst_f1 / worst_event_id` semantic shift (DIST is binary classification).

---

### `pyproject.toml` (MODIFY; config)

**Analog:** Self — existing `[project.optional-dependencies] validation` extras block.

**Phase 5 addition** (single line, per RESEARCH Probe 5):
```toml
[project.optional-dependencies]
validation = [
    "opera-utils[disp]>=0.25",
    "pandas>=2.2",
    "scikit-image>=0.22",
    "statsmodels>=0.14",
    "owslib>=0.35,<1",                  # NEW: Phase 5 EFFIS WFS access (noarch pure-Python)
]
```
**Justification:** owslib 0.35.0 is `noarch` pure-Python (no C extensions per PyPI metadata). Pip-layer install on top of conda env is correct per CLAUDE.md "conda-forge-only for isce3/dolphin/tophu/snaphu/GDAL — pure-Python validation tools (owslib, numpy, rasterio Python API) go in pip layer."

**`conda-env.yml` UNCHANGED** — pip layer at end of conda-env.yml (`pip: -e .[validation,viz]`) picks up the new owslib transitively.

---

### `docs/validation_methodology.md` (APPEND §4; doc)

**Analog:** Self (existing §1 from Phase 3 + §2 from Phase 3 + §3 from Phase 4 — append-only by phase per Phase 3 D-15).

**Existing §3 structure** (Phase 4, lines 280-364 — block_mean kernel decision):
- **§3.1** Argument A (PITFALLS framing — physics)
- **§3.2** Argument B (kernel matching practice)
- **§3.3** Anti-feature argument (kernel-flattery floor)
- **§3.4** Decision (block_mean as eval-script default)
- **§3.5** Constraint (kernel choice is comparison-method, not product-quality)

**Phase 5 §4 mirror structure** (per CONTEXT D-23 + scope correction):
- **§4.1** Single-event F1 variance + block-bootstrap CI methodology (1km blocks, B=500, drop-partial-blocks, fixed seed PCG64). Hall (1985) + Lahiri (2003) refs.
- **§4.2** EFFIS rasterisation choice + `all_touched=False` rationale + delta diagnostic (PITFALLS P4.4 mitigation, ~2-4pp F1 swing).
- **§4.3** EFFIS class-definition mismatch caveat (PITFALLS P4.5 — bounds expected precision/recall; narrative caveat only, not a code adjustment).
- **§4.4** CMR auto-supersede behaviour (Stage 0 probe; deferred-cell `metrics.json` shape; archive-on-supersede mechanism for v1.2).
- **(SKIP §4.5 config-drift)** — deferred to v1.2 per scope correction.

**Insertion point:** APPEND after existing §3.5 (line 364 of current file). Use the `---` separator between sections (line 365).

**Section header pattern** (mirrors existing `## 3. ...` at line ~250 of methodology doc):
```markdown
---

## 4. DIST-S1 Validation Methodology

<a name="dist-validation"></a>

**TL;DR:** Phase 5 validates DIST-S1 against EFFIS WFS burnt-area perimeters
across 3 EU events. Single-event F1 inherits ~10pp variance from MGRS-tile
spatial homogeneity assumption violation — block-bootstrap with 1km
non-overlapping blocks (B=500, fixed seed) reports 95% CI alongside the
point estimate. The dist:nam matrix cell ships as DEFERRED pending
operational `OPERA_L3_DIST-ALERT-S1_V1` publication; the auto-supersede
CMR probe in `run_eval_dist.py` Stage 0 will repopulate the cell when
operational lands.

### 4.1 Single-event F1 variance + block-bootstrap CI methodology

[... 1km blocks, B=500, drop-partial-blocks, PCG64 seed=0; cite Hall 1985
+ Lahiri 2003; cite RESEARCH Probe 9 corrected count 110×110 = 12,100
full blocks for 100km tile; module constants in bootstrap.py auditable
in git per Phase 1 D-11 + Phase 4 D-04 ...]

### 4.2 EFFIS rasterisation choice -- all_touched=False as gate value

[... rasterio.features.rasterize default; PITFALLS P4.4 2-4pp F1 swing
mitigation; diagnostic delta reported in metrics.json
per_event[N].rasterisation_diagnostic ...]

### 4.3 EFFIS class-definition mismatch caveat

[... PITFALLS P4.5 — DIST detects clear-cuts/windthrow/defoliation that
EFFIS doesn't include; EFFIS includes low-severity ground fire that DIST
may miss; bounds expected precision/recall; class mismatch is NOT
mitigated in code, only documented here ...]

### 4.4 CMR auto-supersede behaviour

[... Stage 0 probe queries OPERA_L3_DIST-ALERT-S1_V1 for T11SLT 2025-01-21
±7 days; on hit, transparently downloads + supersedes; on miss, writes
deferred cell_status='DEFERRED' metrics.json. Archive-on-supersede
mechanism (eval-dist/archive/v0.1_metrics_*.json) for v1.2 ...]
```

**What to differ from existing §3:**
- Phase 5 owns ONLY §4 (NOT §5/§6 — those are Phase 6 / Phase 7 territory per Phase 3 D-15).
- Single-PR append at Phase 5 close alongside CONCLUSIONS updates.
- No code-style commitments (REFERENCE_MULTILOOK_METHOD-style) for DIST since Phase 5 doesn't introduce a posture decision; the rasterisation choice IS a posture decision and §4.2 names the constant/eval-script seam (`all_touched=False` hardcoded in `effis.py` per D-17).

---

### `CONCLUSIONS_DIST_N_AM.md` (APPEND v1.1 deferred-cell sub-section; doc)

**Analog:** `CONCLUSIONS_DISP_EU.md` (Phase 4 D-13 v1.0 baseline + v1.1 append pattern).

**v1.0 baseline preservation** (per D-22 + Phase 4 D-13):
- Existing 195 LOC `CONCLUSIONS_DIST_N_AM.md` is preserved AS-IS as the leading "v1.0 historical baseline" sub-section.
- v1.1 sub-section APPENDED at end with the deferred-cell narrative.

**v1.1 append section template** (mirrors `CONCLUSIONS_DISP_EU.md` Phase 4 closure verdict structure):
```markdown
---

## v1.1 Phase 5 Update — Deferred pending operational publication

**Date:** 2026-04-25
**Status:** DEFERRED (Phase 5 scope correction)

The Phase 5 plan-phase research finding (RESEARCH Probe 1) determined
that the OPERA DIST-S1 v0.1 sample is not a downloadable HDF5 with
embedded config metadata — it's a notebook recipe that regenerates the
product locally using whichever dist-s1 version is installed. Combined
with the 2026-04-25 confirmation (RESEARCH Probe 6) that
`OPERA_L3_DIST-ALERT-S1_V1` is not yet published in CMR, Phase 5
defers DIST-01/02/03 (config-drift gate, F1+CI against operational
reference) to v1.2 when the operational reference becomes available.

**What ships in Phase 5:**
- CMR auto-supersede probe at Stage 0 of `run_eval_dist.py`. On hit
  (operational lands mid-v1.x), the cell auto-fills without manual
  intervention.
- Deferred `eval-dist/metrics.json` with `cell_status='DEFERRED'`,
  `reference_source='none'`, `cmr_probe_outcome='operational_not_found'`.
- Matrix cell renders as `DEFERRED (CMR: operational_not_found)`.

**v1.0 Park Fire baseline** preserved at top of this document as
historical-baseline sub-section (no F1 against OPERA reference because
the v1.0 cache lives at `eval-dist-park-fire/` post-rename per D-05).
```

**What to differ from v1.0 baseline:**
- v1.0 was "STRUCTURALLY COMPLETE / no comparison" — Phase 5 v1.1 is "DEFERRED pending operational publication", a stricter framing.
- v1.0 cache `eval-dist/` → renamed to `eval-dist-park-fire/` (preserves cache + run.log + opera_reference/ contents).
- New `eval-dist/` is created fresh by Phase 5 with the deferred metrics.json (CMR Stage 0 + JSON dump only).

---

### `CONCLUSIONS_DIST_EU.md` (APPEND v1.1 3-event sub-section; doc)

**Analog:** `CONCLUSIONS_DISP_EU.md` (Phase 4 D-13 v1.0 baseline + v1.1 append pattern).

**v1.0 baseline preservation** (per D-22):
- Existing 240 LOC `CONCLUSIONS_DIST_EU.md` (Aveiro Sept 28 + Nov 15 vs EMS EMSR760) preserved as "v1.0 historical baseline" sub-section.
- v1.1 APPENDS the 3-event aggregate (aveiro + evros + spain_culebra) + chained-retry differentiator narrative.

**v1.1 append section template** (mirrors Phase 4 EU eval narrative shape — calibration framing + per-event table + aggregate result + chained retry framing):
```markdown
---

## v1.1 Phase 5 Update — 3-event aggregate + chained-retry differentiator

**Date:** 2026-04-25
**Status:** [PASS / MIXED / FAIL — depends on actual run]

### 1. Per-event table

| Event | MGRS | post_date | F1 [CI] | precision [CI] | recall [CI] | accuracy [CI] | Verdict |
|-------|------|-----------|---------|----------------|-------------|---------------|---------|
| aveiro | 29TNF | 2024-09-28 | [x] | [y] | [z] | [w] | [PASS/FAIL] |
| evros (EMSR686) | 35TLF | 2023-09-05 | [x] | [y] | [z] | [w] | [PASS/FAIL] |
| spain_culebra | 29TQG | 2022-06-28 | [x] | [y] | [z] | [w] | [PASS/FAIL] |

### 2. EFFIS rasterisation diagnostic (D-17)

[... per-event all_touched=False vs all_touched=True F1 delta; cite
docs/validation_methodology.md §4.2 ...]

### 3. Class-definition caveat (PITFALLS P4.5)

[... narrative-only caveat; bounds expected precision/recall; cite §4.3 ...]

### 4. Chained `prior_dist_s1_product` retry — DIFFERENTIATOR

**Aveiro chain:** Sept 28 → Oct 10 → Nov 15 with `prior_dist_s1_product`
threading. Pass criterion = structurally-valid 10-layer DIST-ALERT
product (D-14): `dist_s1.data_models.output_models.DistS1ProductDirectory.from_path()`
loads + 10 layers present + DIST-STATUS layer non-empty. **No F1
comparison against un-chained baseline** (D-14: alert-promotion's
confirmation-count logic legitimately changes the disturbance footprint).

**Result:** [structurally_valid / partial_output / dist_s1_hang / crashed].

### 5. EFFIS-equivalent substitution

CONTEXT.md original list said "Romania 2022 forest clear-cuts" which EFFIS
does not cover (EFFIS is fire-only). Phase 5 plan-phase substituted
**Spain Sierra de la Culebra June 2022** (~26,000 ha; bbox -6.5/41.7/-5.9/42.2;
MGRS 29TQG) per RESEARCH Probe 4 ADR. Documented here for audit trail.

### 6. EMSR686 correction

CONTEXT.md original text said "Evros Greece EMSR649 2023". EMSR649 was
an Italian flood (verified at emergency.copernicus.eu/mapping/list-of-components/EMSR649);
the Evros 2023 wildfire EMS activation is **EMSR686**. Corrected in
EVENTS list (event_id='evros').
```

**What to differ from v1.0 baseline:**
- v1.0 was 2-event (Aveiro Sept 28 + Aveiro Nov 15) — Phase 5 v1.1 is 3-event (aveiro + evros + spain_culebra).
- v1.0 used Copernicus EMS EMSR760 reference — Phase 5 v1.1 uses EFFIS WFS perimeters (per DIST-05 reframing).
- v1.0 reported precision/recall/F1 inline as point estimates — Phase 5 reports `MetricWithCI` (point + 95% CI) per D-07.
- v1.0 had no chained-retry section — Phase 5 v1.1 adds Section 4 chained-retry DIFFERENTIATOR framing per ROADMAP DIST-07.

---

### `ROADMAP.md` (AMEND §Phase 5; doc)

**Analog:** Self — existing Phase 5 success criteria block at lines 157-173.

**Phase 5 amendment** (per scope correction):
- DIST-01/02/03 marked `[deferred to v1.2]` with rationale citing RESEARCH Probes 1 + 6.
- DIST-04/05/06/07 retained as Phase 5 deliverables.
- Renumbering: success criteria 1, 2, 3 marked deferred; success criteria 4, 5, 6 inherit.

**Pattern**: ADD a single `[deferred to v1.2]` tag inline + a short rationale paragraph below the criteria table. NO restructuring of existing criteria text.

---

### `REQUIREMENTS.md` (AMEND DIST-01/02/03; doc)

**Analog:** Self — existing DIST-01..07 entries.

**Phase 5 amendment** (per scope correction):
- DIST-01: `status='deferred to v1.2'` + rationale "OPERA_L3_DIST-ALERT-S1_V1 not yet published in CMR (verified 2026-04-25)".
- DIST-02: `status='deferred to v1.2'` + rationale "Config-drift gate moot until operational lands".
- DIST-03: `status='deferred to v1.2'` + rationale "F1+CI computation moot until reference exists".
- DIST-04/05/06/07: status unchanged.

**Pattern:** ADD `status:` field per requirement, mirroring existing DIST-V2-01..04 future-work entries. NO new requirements.

---

## Shared Patterns (Cross-cutting)

### 1. `_mp.configure_multiprocessing()` at top of every `run_*()`

**Source:** `src/subsideo/_mp.py:39` + Phase 1 ENV-04 D-14
**Apply to:** `run_eval_dist.py`, `run_eval_dist_eu.py` (rewritten)

**Excerpt** (`_mp.py:62-103`):
```python
def configure_multiprocessing() -> None:
    if _CONFIGURED:
        return
    with _CONFIGURE_LOCK:
        if _CONFIGURED:
            return
        os.environ.setdefault("MPLBACKEND", "Agg")
        # RLIMIT_NOFILE → min(4096, hard)
        # requests import seam warm
        # macOS: fork (Py<3.14) / forkserver (Py>=3.14)
        _CONFIGURED = True
```

**Critical landmine:** Must fire at the very top of `main()` BEFORE any `requests.Session`-using import (`asf_search`, `earthaccess`). v1.0 `run_eval_dist*.py` scripts MISS this; Phase 5 rewrites ADD it. Pre-condition for DIST-07 chained retry (PITFALLS P0.1).

### 2. `EXPECTED_WALL_S` declaration at module top

**Source:** Phase 1 D-11 + `supervisor.py:94-125` AST-parser
**Apply to:** `run_eval_dist.py`, `run_eval_dist_eu.py`

**Excerpt** (`run_eval_rtc_eu.py:35`):
```python
EXPECTED_WALL_S = 60 * 60 * 4   # 14400s; supervisor AST-parses (D-11 + T-07-06)
```

**Critical landmine:** Must be a literal int or whitelisted BinOp of literal Constants (T-07-06). `60 * 60 * 8` is ACCEPTED; `8 * SECONDS_PER_HOUR` is REJECTED (Name reference). Visible in git diff for switching budgets — never an env var or CLI flag.

### 3. Per-event try/except isolation

**Source:** Phase 2 D-06 + `run_eval_rtc_eu.py:563-608`
**Apply to:** `run_eval_dist_eu.py` (3-event loop)

**Excerpt** (`run_eval_rtc_eu.py:585-608`):
```python
except Exception as e:  # noqa: BLE001 - per-burst isolation (D-06)
    tb = traceback.format_exc()
    logger.error("Burst {} FAIL ({:.0f}s): {}", cfg.burst_id, time.time() - t0, e)
    per_burst.append(BurstResult(
        burst_id=cfg.burst_id,
        # ...
        status="FAIL",
        error=repr(e),
        traceback=tb,
    ))
```
Phase 5 mirrors verbatim with `event_id` instead of `burst_id` and `DistEUEventMetrics` instead of `BurstResult`.

### 4. Lazy imports for conda-forge deps

**Source:** Phase 1 lazy-import discipline + `compare_dist.py:142-143`
**Apply to:** `bootstrap.py` (numpy at module top, no scipy), `effis.py` (owslib + geopandas + rasterio inside function bodies)

**Excerpt** (`compare_dist.py:142-143`):
```python
def compare_dist(product_path, reference_path, ...):
    import rasterio
    from rasterio.warp import Resampling, reproject
```

**Apply pattern:** numpy/scipy at module top (pure-Python or thin wrapper); rasterio/geopandas/owslib/h5py/earthaccess INSIDE function bodies. Preserves the import-time invariant that `subsideo.validation.*` modules don't drag conda-forge dependencies just by being imported.

### 5. `harness.ensure_resume_safe` for warm re-runs

**Source:** Phase 1 ENV-06 + `harness.py:391-421`
**Apply to:** `run_eval_dist_eu.py` per-event whole-pipeline skip + per-stage cache check

**Excerpt** (`harness.py:391-421`):
```python
def ensure_resume_safe(cache_dir: Path, manifest_keys: Sequence[str]) -> bool:
    cache_dir = Path(cache_dir)
    if not cache_dir.exists():
        return False
    try:
        existing = {p.name for p in cache_dir.iterdir()}
    except (OSError, PermissionError) as e:
        logger.warning("ensure_resume_safe: cannot read {}: {}", cache_dir, e)
        return False
    return all(k in existing for k in manifest_keys)
```

**Usage** (mirrors `run_eval_rtc_eu.py:478`):
```python
expected_outputs = ["metrics.json", f"{cfg.event_id}/dist_output/...DIST-STATUS.tif"]
if ensure_resume_safe(CACHE / cfg.event_id, expected_outputs):
    logger.info("Event {} cached; skipping", cfg.event_id)
    continue
```

### 6. INVESTIGATION_TRIGGER vs BINDING distinction in `criteria.py`

**Source:** Phase 1 D-04..D-19 + `criteria.py:74-97`
**Apply to:** Phase 5 makes ZERO edits to `criteria.py` per scope correction (existing `dist.f1_min` + `dist.accuracy_min` BINDING entries inherit unchanged).

**Excerpt** (`criteria.py:74-85`):
```python
"rtc.eu.investigation_rmse_db_min": Criterion(
    name="rtc.eu.investigation_rmse_db_min", threshold=0.15, comparator=">=",
    type="INVESTIGATION_TRIGGER", binding_after_milestone=None,
    rationale=(
        "EU RTC per-burst investigation trigger... NOT a gate -- triggers a "
        "CONCLUSIONS_RTC_EU.md investigation sub-section per D-14..."
    ),
),
```

**Critical:** INVESTIGATION_TRIGGER entries are FILTERED out of matrix-cell rendering at `matrix_writer.py:114-116` so they NEVER produce a PASS/FAIL verdict. Phase 5 may OPTIONALLY add an `INVESTIGATION_TRIGGER` for F1 CI width per Claude's-Discretion item (e.g. `dist.eu.investigation_f1_ci_width_max = 0.05`); plan-phase decides whether to add — narrative-only, gate-prevention.

### 7. Manifest-authoritative + matrix_writer never globs CONCLUSIONS

**Source:** REL-02 + `matrix_writer.py` docstring (PITFALLS R3 / R5)
**Apply to:** Phase 5 makes ZERO edits to `matrix_manifest.yml` (lines 76-82 already wire `dist:nam` → `eval-dist/metrics.json` + `dist:eu` → `eval-dist_eu/metrics.json`).

**Excerpt** (`matrix_writer.py:1-7`):
```python
"""Read results/matrix_manifest.yml + per-cell {meta,metrics}.json sidecars,
write results/matrix.md with a two-column layout (product-quality +
reference-agreement), echoing ``CRITERIA`` thresholds alongside measured
values for drift visibility (D-03 matrix-echo).

NEVER parses CONCLUSIONS_*.md (PITFALLS R3 / R5). Missing or malformed
sidecars render as ``RUN_FAILED`` (ENV-09 per-cell isolation).
"""
```

Phase 5 ADDS render branches; the dispatch pattern matches existing branches: schema-discriminator → render-function → fall-through to RUN_FAILED on parse fail.

### 8. v1.0 narrative preserved as baseline preamble in CONCLUSIONS

**Source:** Phase 4 D-13 + `CONCLUSIONS_DISP_EU.md` (entire file)
**Apply to:** `CONCLUSIONS_DIST_N_AM.md` (Park Fire baseline) + `CONCLUSIONS_DIST_EU.md` (Aveiro v1.0 baseline)

**Excerpt** (existing `CONCLUSIONS_DISP_EU.md:1-9`):
```markdown
# EU DISP-S1 Validation — Session Conclusions (EGMS)

**Date:** 2026-04-15
**Burst:** `t117_249422_iw2`
...
**Result: STRUCTURALLY COMPLETE / SCIENTIFICALLY INCONCLUSIVE** — same verdict as the N.Am. run...
```

**Apply pattern:** v1.0 content STAYS at top; Phase 5 v1.1 sub-section APPENDS at end after a `---` separator. Heading shape: `## v1.1 Phase 5 Update — [tagline]`. Date stamp + status framing in the first block.

### 9. Append-only `docs/validation_methodology.md` by phase

**Source:** Phase 3 D-15 + `docs/validation_methodology.md:1-15` preamble
**Apply to:** Phase 5 owns ONLY §4 (NOT §5/§6 — those are Phase 6 / Phase 7 territory).

**Excerpt** (existing `validation_methodology.md:1-8`):
```markdown
# Validation Methodology

**Scope:** Consolidates cross-cutting validation-methodology findings that span
multiple phases and products. Updated append-only per phase — Phase 3 writes
section 1 + section 2; Phase 4 will append the DISP ramp-attribution section;
Phases 5/6 will append the DSWE F1 ceiling and cross-sensor precision-first
sections; Phase 7 REL-03 will write the top-level table of contents and the
final cross-section consistency pass.
```

**Apply pattern:** APPEND `## 4. DIST-S1 Validation Methodology` after existing §3 (line 364). Sub-sections 4.1/4.2/4.3/4.4 per CONTEXT D-23 (skip 4.5 config-drift per scope correction). NO edits to existing §1/§2/§3.

### 10. Auto-attribute Literal schema for status enums

**Source:** Phase 4 D-11 `attributed_source` Literal at `matrix_schema.py:455`
**Apply to:** Phase 5 reuses pattern for 6 new Literal aliases (`DistEUEventID`, `ChainedRunStatus`, `CMRProbeOutcome`, `ReferenceSource`, `DistEUCellStatus`, `DistNamCellStatus`).

**Excerpt** (`matrix_schema.py:454-456`):
```python
CoherenceSource = Literal["phase3-cached", "fresh"]
AttributedSource = Literal["phass", "orbit", "tropospheric", "mixed", "inconclusive"]
DISPCellStatus = Literal["PASS", "FAIL", "CALIBRATING", "MIXED", "BLOCKER"]
```

**Apply pattern:** Type aliases at top of new Phase-5 section block (after the `# --- Phase 5 ... ---` separator). Used as field types in Pydantic v2 BaseModel subclasses. ZERO edits to existing aliases.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/subsideo/validation/effis.py` (NEW) | service | request-response | First WFS consumer in subsideo; no existing WFS module. Closest network analog (`data/cdse.py`) uses STAC + S3 not WFS. Recipe synthesised from RESEARCH Probe 3 + Library Quick Reference + existing `run_eval_dist_eu.py:331-435` rasterise-inline pattern. |

All other Phase 5 files have strong analog matches in the codebase.

---

## Metadata

**Analog search scope:**
- `src/subsideo/validation/*.py` (12 modules)
- `src/subsideo/_mp.py`
- `run_eval_*.py` (10 scripts)
- `CONCLUSIONS_*.md` (10 docs)
- `docs/validation_methodology.md`
- `results/matrix_manifest.yml`
- `pyproject.toml`

**Files scanned:** ~40 (Read tool calls; range-limited to relevant sections for files > 1k LOC)

**Pattern extraction date:** 2026-04-25

**Confidence breakdown:**
- HIGH: harness.RETRY_POLICY shape, matrix_schema.py Pydantic v2 conventions, matrix_writer.py render-branch dispatch, run_eval_rtc_eu.py declarative AOIS-list pattern, _mp.configure_multiprocessing bundle, supervisor EXPECTED_WALL_S AST parsing, criteria.py BINDING/CALIBRATING/INVESTIGATION_TRIGGER distinction, CONCLUSIONS append-only by phase pattern.
- MEDIUM-HIGH: bootstrap.py implementation (per RESEARCH Probe 9 corrected math), effis.py rasterise + WFS recipe (Probe 3 + Probe 5).
- MEDIUM: EVENTS list specifics (Aveiro/Evros/Spain dates+MGRS pending plan-phase enumerator probe).

## PATTERN MAPPING COMPLETE

**Phase:** 5 - DIST-S1 OPERA v0.1 + EFFIS EU
**Files classified:** 17 (revised scope per important_scope_correction)
**Analogs found:** 17 / 17 (effis.py is synthesised from 2 partial analogs + RESEARCH probes)

### Coverage
- Files with exact analog: 14 (harness, matrix_schema, matrix_writer, compare_dist, run_eval_dist, run_eval_dist_eu, pyproject.toml, validation_methodology.md, CONCLUSIONS x2, ROADMAP, REQUIREMENTS, eval-dist rename, run_eval_dist_eu_nov15 deletion)
- Files with role-match analog: 2 (bootstrap.py — metrics.py role; cache-dir consolidation — manifest convention)
- Files with synthesised analog: 1 (effis.py — combines data/cdse.py network shape + run_eval_dist_eu.py rasterise inline)

### Key Patterns Identified
- All eval scripts MUST call `_mp.configure_multiprocessing()` at top of `main()` BEFORE network imports (Phase 1 ENV-04; pre-condition for DIST-07 chained retry per PITFALLS P0.1).
- All eval scripts declare `EXPECTED_WALL_S` as module-level literal int / BinOp of literal Constants (Phase 1 D-11; supervisor AST-parses at supervisor.py:94-125).
- All Pydantic v2 schema additions use `model_config = ConfigDict(extra="forbid")` + `Field(..., description=...)` (PATTERNS §4.5; Phase 1 D-09 immutability — ZERO edits to existing types).
- All matrix_writer render branches follow schema-discriminator + render-function + fall-through-to-RUN_FAILED dispatch (Phase 4 D-08 ordering: rtc → cslc → disp → dist → dswx).
- All multi-{burst,AOI,event} aggregate cells follow declarative-list + per-item try/except + aggregate-write pattern (Phase 2 D-05/D-06 from `run_eval_rtc_eu.py`).
- All append-only docs (`CONCLUSIONS_*.md`, `validation_methodology.md`) preserve v1.0 narrative as leading sub-section + append v1.x sections at end after `---` separator (Phase 4 D-13 + Phase 3 D-15).
- All retry-policy additions to `harness.py` follow the dict-key-extension pattern (Phase 1 ENV-06; Phase 5 adds 5th source 'EFFIS' alongside CDSE/EARTHDATA/CLOUDFRONT/HTTPS).
- Lazy imports for conda-forge deps inside function bodies; numpy at module top (Phase 1 lazy-import discipline).
- Bootstrap CI module-level constants `DEFAULT_BLOCK_SIZE_M`, `DEFAULT_N_BOOTSTRAP`, `DEFAULT_RNG_SEED`, `DEFAULT_CI_LEVEL`, `DEFAULT_PIXEL_SIZE_M` are auditable in git diff (Phase 1 D-11 + Phase 4 D-04 posture).

### Landmines Flagged
- `_mp.configure_multiprocessing()` MUST fire BEFORE any module-level `requests.Session` creation (top-of-script-only; v1.0 dist scripts miss this).
- `EXPECTED_WALL_S` MUST be a literal int or BinOp of literal Constants — Name references / Calls / Attributes are REJECTED by supervisor AST-parser (T-07-06).
- Lazy imports for `rasterio`, `geopandas`, `h5py`, `owslib`, `earthaccess` inside function bodies (preserves import-time invariant).
- INVESTIGATION_TRIGGER vs BINDING distinction in `criteria.py` — Phase 5 makes ZERO edits to existing entries; INVESTIGATION_TRIGGER is non-gate (filtered out at matrix_writer.py:114-116).
- WFS responses are GML / SHAPEZIP / SPATIALITEZIP (not plain HTTPS file streams) — `geopandas.read_file(BytesIO(...))` parses both via pyogrio.
- EFFIS WFS endpoint is plan-phase-locked (RESEARCH Probe 3 left two candidates; both timed out in research session). Plan-phase MUST `GetCapabilities`-probe before committing literal URL.
- Romania 2022 EFFIS coverage gap (Probe 4) substituted with Spain Sierra de la Culebra 2022.
- EMSR686 (NOT EMSR649) for Evros 2023 — CONTEXT.md typo corrected.
- Cache directory consolidation: `eval-dist-eu/` (hyphen) + `eval-dist-eu-nov15/` (hyphen) → `eval-dist_eu/` (underscore matches manifest convention).
- v1.0 `run_eval_dist_eu.py` + `run_eval_dist_eu_nov15.py` content MIGRATES into the rewritten declarative-EVENTS-list `run_eval_dist_eu.py`; v1.0 scripts deleted at Phase 5 close.

### File Created
`/Volumes/Geospatial/Geospatial/subsideo/.planning/phases/05-dist-s1-opera-v0-1-effis-eu/05-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can reference analog patterns + concrete code excerpts directly in PLAN.md files. Per RESEARCH §Recommended Wave Structure, Wave 0 probe artifact + Wave 1 parallel module-adds (bootstrap.py, matrix_schema.py extension, harness EFFIS branch) + Wave 2 sequential extensions (compare_dist + matrix_writer DIST branches) + Wave 3 parallel eval-script rewrites + Wave 4 docs + closure.
