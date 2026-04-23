# Phase 2: RTC-S1 EU Validation - Pattern Map

**Mapped:** 2026-04-22
**Files analyzed:** 8 (4 CREATE + 4 MODIFY)
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Status | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|--------|------|-----------|----------------|---------------|
| `run_eval_rtc_eu.py` | CREATE | eval-script (entry point) | batch / request-response | `run_eval.py` + `run_eval_disp_egms.py` | exact (fork source) + role-match (declarative-list) |
| `CONCLUSIONS_RTC_EU.md` | CREATE | narrative / reporting doc | n/a (prose) | `CONCLUSIONS_RTC_N_AM.md` | exact (same product, different region) |
| `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` | CREATE | research artifact (table) | n/a (tabular md) | (none — new artifact class for v1.1) | no analog — see FEATURES line 50 + D-01 |
| `scripts/probe_rtc_eu_candidates.py` | CREATE (optional) | one-shot probe script | batch query | `run_eval_disp.py` (asf.search + earthaccess.search_data blocks) | partial |
| `src/subsideo/validation/matrix_schema.py` | MODIFY | Pydantic v2 schema module | data model | existing `MetricsJson` + `ReferenceAgreementResultJson` | exact (same file, extend) |
| `src/subsideo/validation/matrix_writer.py` | MODIFY | markdown renderer | batch read/transform | existing `_render_cell_column` + `write_matrix` | exact (same file, branch in renderer) |
| `src/subsideo/validation/criteria.py` | MODIFY | frozen registry | data registry | existing `Criterion` + `CRITERIA` dict | exact (same file, add entries + extend Literal) |
| `src/subsideo/validation/harness.py` | MODIFY (optional) | validation plumbing | utility | existing `ensure_resume_safe` + `bounds_for_burst` | exact (same file, add sibling helper) |

---

## Pattern Assignments

### `run_eval_rtc_eu.py` (eval-script, request-response batch)

**Primary analog:** `/Volumes/Geospatial/Geospatial/subsideo/run_eval.py` (125 LOC — the explicit fork source per FEATURES line 50).
**Secondary analog (declarative-list + for-loop):** `/Volumes/Geospatial/Geospatial/subsideo/run_eval_disp_egms.py` (the "multi-stage declarative loop" precedent, though it loops over SLC *scenes*, not bursts; the structural pattern transfers).

**Header + `EXPECTED_WALL_S` + main guard** (from `run_eval.py:1-9`):
```python
# run_eval.py — N.Am. RTC validation against OPERA
# Downloads S1 SLC from ASF (not CDSE — CDSE covers EU only)
import warnings; warnings.filterwarnings("ignore")

EXPECTED_WALL_S = 1800   # Plan 01-07 supervisor AST-parses this constant (D-11)

# Required on macOS: multiprocessing uses 'spawn', which re-imports this
# script in worker processes.  All top-level work must be inside this guard.
if __name__ == "__main__":
```

**Phase 2 adjustment:** bump `EXPECTED_WALL_S` to `~10800` (5 bursts × 30 min cold + reference fetches — CONTEXT.md §Phase 1 canonical-refs "~3 h cold, ~2 min warm"). Value must be a literal `int` / simple `BinOp` of literals so `supervisor._parse_expected_wall_s` (see `supervisor.py:94-125`) accepts it. `60 * 60 * 3` is accepted (BinOp of two ints); `timedelta(...)` or a `Name` reference is rejected.

**Imports block** (from `run_eval.py:10-25` — this block is literally the base; add DEM/orbit + BurstConfig + json):
```python
if __name__ == "__main__":
    import asf_search as asf
    import earthaccess
    from pathlib import Path
    from datetime import datetime
    from subsideo.data.dem import fetch_dem
    from subsideo.data.orbits import fetch_orbit
    from subsideo.products.rtc import run_rtc
    from subsideo.validation.harness import (
        bounds_for_burst,
        credential_preflight,
        download_reference_with_retry,
        ensure_resume_safe,
        select_opera_frame_by_utc_hour,
    )
    from dotenv import load_dotenv
    load_dotenv()  # loads .env from the current working directory

    credential_preflight(["EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"])
```

Phase 2 adds: `from subsideo.validation.compare_rtc import compare_rtc`, `from subsideo.validation.matrix_schema import MetricsJson, MetaJson, ...`, `import json`, `import traceback`, plus the `BurstConfig` dataclass (local-to-script per D-discretion).

**OPERA reference search pattern** (from `run_eval.py:37-52`):
```python
# ── 1. Download OPERA reference product from ASF ─────────────────────────────
print("Downloading OPERA reference...")
ref_results = earthaccess.search_data(
    short_name="OPERA_L2_RTC-S1_V1",
    temporal=("2024-06-24", "2024-06-25"),
    granule_name="OPERA_L2_RTC-S1_T144-308029-IW1_20240624T140116Z*",
)
ref_dir = OUT / "opera_reference_308029"
ref_dir.mkdir(exist_ok=True)
# Skip if already downloaded
if not any(ref_dir.glob("*.tif")):
    downloaded = earthaccess.download(ref_results, str(ref_dir))
    print(f"  Downloaded: {[Path(f).name for f in downloaded]}")
else:
    print(f"  Already present: {[p.name for p in ref_dir.glob('*.tif')]}")
```

In Phase 2 this is wrapped per-burst: `ref_dir = OUT / f"opera_reference_{burst.burst_id}"`; the `granule_name` format string is parameterised by `burst.burst_id` + `burst.sensing_time`.

**ASF SLC search + closest-match-by-time pattern** (from `run_eval.py:56-75`):
```python
slc_results = asf.search(
    platform=asf.PLATFORM.SENTINEL1,
    processingLevel="SLC",
    beamMode="IW",
    relativeOrbit=144,
    start="2024-06-24T13:58:00Z",
    end="2024-06-24T14:05:00Z",
    maxResults=5,
)
if not slc_results:
    raise SystemExit("No S1 IW SLC found on ASF — check date/orbit")

for r in slc_results:
    print(f"  {r.properties['fileID']}  {r.properties['startTime']}")

# Pick the scene whose start time is closest to SENSING_DATE
scene = min(slc_results, key=lambda r: abs(
    datetime.fromisoformat(r.properties["startTime"].rstrip("Z")) - SENSING_DATE
))
```

**Per-burst try/except isolation pattern** (from `run_eval_disp_egms.py:371-455` — loop over SLCs, accumulate failed scenes, keep going):
```python
cslc_paths: list[Path] = []
failed_scenes: list[str] = []

for i, item in enumerate(slc_items):
    item_id: str = item.get("id", "")
    scene_id = item_id.removesuffix(".SAFE")
    # ... per-iteration try/except:
    try:
        result = run_cslc(...)
    except Exception as exc:
        elapsed = time.time() - t0
        print(f"FAIL ({elapsed:.0f}s: {exc})")
        failed_scenes.append(date_tag)
        continue
```

Phase 2 D-06 adopts this exact pattern: each burst iteration is wrapped in `try: ... except Exception as e: per_burst.append(BurstResult(status='FAIL', error=repr(e), traceback=traceback.format_exc(), ...))`.

**Declarative-list + for-loop module-level config** (from `run_eval_disp_egms.py:62-78`):
```python
# ── Configuration ────────────────────────────────────────────────────────
BURST_ID = "t117_249422_iw2"
RELATIVE_ORBIT = 117
EGMS_TRACK = 117
EGMS_PASS = "Ascending"
# ...
BURST_BBOX = bounds_for_burst(BURST_ID, buffer_deg=0.0)
EPSG = 32632  # UTM 32N (Bologna)

OUT = Path("./eval-disp-egms")
OUT.mkdir(exist_ok=True)
```

Phase 2 generalises this single-burst config into a `list[BurstConfig]` module-level literal per D-05; each iteration derives `BURST_BBOX`/`EPSG`/etc. from `burst.output_epsg` and `bounds_for_burst(burst.burst_id)`.

**Cache fallback via search paths (D-02 `find_cached_safe`)** — integrated at the SAFE-download stage. Replace `run_eval.py:93-112` inline cache check with a harness helper call; see the harness analog below for the signature.

**`run_rtc` invocation** (from `run_eval.py:114-125` — unchanged in Phase 2):
```python
print("Running RTC pipeline...")
result = run_rtc(
    safe_paths=[safe_path],
    orbit_path=orbit_path,
    dem_path=dem_path,
    burst_ids=[BURST_ID],
    output_dir=OUT / "output",
)
```

**Per-burst result + compare_rtc + metrics accumulation** — no direct analog because no existing eval script writes `metrics.json`. Phase 2 is the first consumer of `MetricsJson` (see `matrix_schema.py:114-153`). Construction template (new to this phase):
```python
from subsideo.validation.matrix_schema import (
    MetricsJson, ProductQualityResultJson, ReferenceAgreementResultJson,
)
metrics = MetricsJson(
    product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
    reference_agreement=ReferenceAgreementResultJson(
        measurements={"rmse_db": worst_rmse, "correlation": worst_r, "bias_db": worst_bias},
        criterion_ids=["rtc.rmse_db_max", "rtc.correlation_min"],
    ),
    criterion_ids_applied=["rtc.rmse_db_max", "rtc.correlation_min"],
)
(OUT / "metrics.json").write_text(metrics.model_dump_json(indent=2))
```

Per D-09/D-10 this top-level `MetricsJson` is *extended* by a `RTCEUCellMetrics` subtype (see `matrix_schema.py` section below) that adds `per_burst: list[BurstResult]` + aggregate fields.

---

### `CONCLUSIONS_RTC_EU.md` (narrative / reporting doc)

**Analog:** `/Volumes/Geospatial/Geospatial/subsideo/CONCLUSIONS_RTC_N_AM.md` (291 lines; the canonical v1.0 RTC CONCLUSIONS template).

**Top-matter pattern** (from `CONCLUSIONS_RTC_N_AM.md:1-21`):
```markdown
# N.Am. RTC-S1 Validation — Session Conclusions

**Date:** 2026-04-11
**Burst:** `T144-308029-IW1`
**Scene:** S1A, 2024-06-24T14:01:16Z, relative orbit 144
**Result: PASS** — subsideo RTC-S1 output matches official OPERA reference to within 0.045 dB RMSE (criterion: < 0.5 dB) with r = 0.9999 (criterion: > 0.99).

---

## 1. Objective

Validate that `subsideo v0.1.0` produces RTC-S1 backscatter products that are numerically equivalent to the official [OPERA L2 RTC-S1](...) products distributed by NASA/JPL via ASF DAAC.

The pass criteria (from the project specification) are:

| Metric | Criterion |
|--------|-----------|
| RMSE   | < 0.5 dB  |
| r (Pearson correlation) | > 0.99 |
```

**Test-setup table pattern** (from `CONCLUSIONS_RTC_N_AM.md:25-46`):
```markdown
### 2.1 Target Burst

| Field | Value |
|-------|-------|
| Burst ID (opera-rtc format) | `t144_308029_iw1` |
| Burst ID (OPERA product format) | `T144-308029-IW1` |
| Sensing time | 2024-06-24T14:01:16Z |
| Platform | Sentinel-1A |
| Relative orbit | 144 |
| Geographic area | Southern California (Ventura / Los Angeles counties) |
| UTM zone | 11N (EPSG:32611) |
```

In Phase 2 replicate this table *per burst* (5 tables, one each). Promote the granular format into a rollup `### 2.1 Target Bursts` table with one row per burst.

**Final results table pattern** (from `CONCLUSIONS_RTC_N_AM.md:230-239`):
```markdown
## 5. Final Validation Results

Comparison performed by reprojecting the subsideo output onto the OPERA reference grid (bilinear resampling), masking to pixels with valid linear-power backscatter in both products, converting to dB, and computing statistics over ~1.95 million pixels covering the full burst footprint.

| Polarisation | Valid pixels | RMSE | Bias | Pearson r | Pass/Fail |
|-------------|-------------|------|------|-----------|-----------|
| VV | 1,949,833 | **0.045 dB** | ~0.0 dB | **0.9999** | PASS |
| VH | 1,949,759 | **0.043 dB** | ~0.0 dB | **0.9999** | PASS |
```

Phase 2 adds per-burst rows: columns `Burst ID | Regime | Lat | Max relief (m) | Cached? | VV RMSE | VV r | VH RMSE | VH r | Pass/Fail | Investigation?`.

**New section mandated by P1.1 + D-14 (no analog — new v1.1 requirement):**
```markdown
## 6. Terrain-Regime Coverage Table

| burst_id | regime | lat | max_relief_m | cached? |
|----------|--------|-----|--------------|---------|
| ... | Alpine (>1000 m relief) | ... | ... | No |
| ... | Scandinavian (>55°N) | ... | ... | No |
| ... | Iberian arid | ... | ... | No |
| ... | Temperate flat (Bologna) | ... | ... | Yes (from eval-disp-egms/) |
| ... | Portuguese fire | ... | ... | Yes (from eval-dist-eu/) |

All five regimes covered. ≥1 burst >1000 m relief: PASS. ≥1 burst >55°N: PASS. (P1.1 cached-bias prevention.)

## 7. Investigation Findings

For each burst whose RMSE ≥ 0.15 dB OR r < 0.999 (per D-13 trigger), a structured sub-section follows:

### 7.X Burst `{burst_id}` — {regime}

**Observation.** RMSE {X} dB (N.Am. baseline 0.045 dB), r {X} (baseline 0.9999), bias {X} dB.

**Top hypotheses:**
1. {Hypothesis 1 — e.g. "steep-relief DEM artefact"}
2. {Hypothesis 2 — e.g. "high-latitude DEM grid anomaly"}
3. {Hypothesis 3 — e.g. "OPERA reference version drift"}

**Evidence:** {one concrete data point per hypothesis}.
```

**Structure to mirror verbatim** from `CONCLUSIONS_RTC_N_AM.md`:
- §1 Objective
- §2 Test Setup (2.1 Target Burst, 2.2 Input Data, 2.3 Processing Environment)
- §3 What Was Run
- §4 Bugs Encountered and Fixed
- §5 Final Validation Results
- §6 Why the Result Is Correct
- §7 Output Files
- §8 Source Files Changed During This Session

Phase 2 additions between §5 and §6: **Terrain-Regime Coverage Table (P1.1)** + **Investigation Findings (D-14, D-15)**.

---

### `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` (research artifact)

**No code analog.** This is a markdown research artifact (committed; machine-readable but human-written) per D-01. Schema:

```markdown
# RTC-S1 EU Burst Candidates — Probe Report

**Probed:** 2026-04-XX
**Source query:** ASF via `asf-search` (OPERA_L2_RTC-S1_V1 temporal 2024-01 .. 2025-12)

| burst_id | regime | best_match_sensing_utc | opera_rtc_granules_2024_2025 | cached_safe | lat | expected_max_relief_m |
|----------|--------|------------------------|------------------------------|-------------|-----|-----------------------|
| ... | Alpine | 2024-... | N | (none) | 46.5 | ~2800 |
| ... | Scandinavian | 2024-... | N | (none) | 67.1 | ~700 |
| ... | Iberian arid | 2024-... | N | (none) | 41.2 | ~400 |
| t117_249422_iw2 | Temperate flat (Bologna) | 2021-... | N | `eval-disp-egms/input/...SAFE.zip` | 44.5 | ~80 |
| ... | Portuguese fire | 2024-09-28 | N | `eval-dist-eu/input/...SAFE.zip` | 40.75 | ~250 |

## Query reproducibility

See `scripts/probe_rtc_eu_candidates.py` (optional sub-deliverable) for the live queries; cached granule counts are a snapshot at probe time.
```

Rationale source: `FEATURES.md:50` ("any burst without ASF OPERA RTC coverage is a wasted compute run").

---

### `scripts/probe_rtc_eu_candidates.py` (optional, one-shot query script)

**Analog:** `/Volumes/Geospatial/Geospatial/subsideo/run_eval_disp.py:179-193` (ASF search block) — same `asf.search(...)` pattern plus `earthaccess.search_data(short_name="OPERA_L2_RTC-S1_V1", ...)` block from `run_eval.py:39-43`.

Pattern (synthesising the two):
```python
import asf_search as asf
import earthaccess
from dotenv import load_dotenv
load_dotenv()
earthaccess.login(strategy="environment")

for burst_id, bbox, regime in CANDIDATES:
    # (a) OPERA RTC reference availability
    ref_results = earthaccess.search_data(
        short_name="OPERA_L2_RTC-S1_V1",
        temporal=("2024-01-01", "2025-12-31"),
        bounding_box=bbox,
    )
    # (b) Sentinel-1 SLC best-match
    slc_results = asf.search(
        platform=asf.PLATFORM.SENTINEL1,
        processingLevel="SLC",
        beamMode="IW",
        intersectsWith=f"POLYGON(({bbox[0]} {bbox[1]},{bbox[2]} {bbox[1]},...))",
        start="2024-01-01T00:00:00Z",
        end="2025-12-31T23:59:59Z",
        maxResults=100,
    )
    # ... write row to rtc_eu_burst_candidates.md
```

No `EXPECTED_WALL_S` — this script is *not* invoked under the supervisor; it is a one-shot query run manually (see CONTEXT.md §Claude's Discretion "hand-run Python script is most consistent with v1.0 style").

---

### `src/subsideo/validation/matrix_schema.py` (MODIFY — Pydantic v2 schema)

**Analog:** existing class hierarchy in the same file (`matrix_schema.py:26-153`). Phase 2 adds a new class **extending** `MetricsJson` (not replacing) to preserve the current contract for the 9 other cells.

**Base class to extend** (from `matrix_schema.py:114-153`):
```python
class MetricsJson(BaseModel):
    """Per-eval scientific sidecar (``<cache_dir>/metrics.json``)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(
        default=1,
        description="Schema version; bump on breaking change (forward-compat hook).",
    )
    product_quality: ProductQualityResultJson = Field(
        default_factory=ProductQualityResultJson,
        description="Product-quality gate measurements + criterion IDs.",
    )
    reference_agreement: ReferenceAgreementResultJson = Field(
        default_factory=ReferenceAgreementResultJson,
        description="Reference-agreement measurements + criterion IDs.",
    )
    criterion_ids_applied: list[str] = Field(
        default_factory=list,
        description=(
            "Union of all criterion IDs used across product_quality and "
            "reference_agreement. Redundant with the sub-result lists but "
            "kept for audit-log simplicity."
        ),
    )
    runtime_conda_list_hash: str | None = Field(
        default=None,
        description=(...),
    )
```

**Phase 2 extension pattern** (add a `BurstResult` sub-model + `RTCEUCellMetrics` subclassing `MetricsJson`):
```python
class BurstResult(BaseModel):
    """Per-burst row inside RTCEUCellMetrics.per_burst.

    Shape aligns with CONTEXT.md D-10.
    """

    model_config = ConfigDict(extra="forbid")

    burst_id: str = Field(..., description="JPL-format burst ID, e.g. 't144_308029_iw1'.")
    regime: str = Field(..., description="Terrain regime label (Alpine / Scandinavian / Iberian / ...).")
    lat: float | None = Field(default=None, description="Centroid latitude (deg).")
    max_relief_m: float | None = Field(default=None, description="Max relief in the burst DEM (m), or None when DEM unavailable.")
    cached: bool = Field(default=False, description="Whether the SAFE was reused from another eval cache.")
    status: Literal["PASS", "FAIL"] = Field(..., description="Per-burst PASS/FAIL from reference_agreement gates.")
    product_quality: ProductQualityResultJson | None = Field(
        default=None,
        description="Null for RTC in v1.1 (no product-quality gate; research convention).",
    )
    reference_agreement: ReferenceAgreementResultJson = Field(
        default_factory=ReferenceAgreementResultJson,
        description="Per-burst RMSE/r/bias measurements + RTC criterion IDs.",
    )
    investigation_required: bool = Field(default=False, description="True if RMSE >= 0.15 dB OR r < 0.999 (D-13 trigger).")
    investigation_reason: str | None = Field(default=None, description="Human-readable trigger explanation, or None.")
    error: str | None = Field(default=None, description="repr(exception) when status == 'FAIL' from try/except; else None.")
    traceback: str | None = Field(default=None, description="Full traceback string when exception caught.")


class RTCEUCellMetrics(MetricsJson):
    """RTC-EU multi-burst aggregate extending the base MetricsJson schema (D-09)."""

    pass_count: int = Field(..., ge=0)
    total: int = Field(..., ge=1)
    all_pass: bool
    any_investigation_required: bool
    reference_agreement_aggregate: dict[str, float] = Field(
        default_factory=dict,
        description="Aggregate summary: worst_rmse_db, worst_r, worst_burst_id.",
    )
    per_burst: list[BurstResult] = Field(default_factory=list)
```

**Key discipline:** `model_config = ConfigDict(extra="forbid")` is the convention across all four existing models (`matrix_schema.py:34, 54, 74, 124`) — Phase 2 preserves it on the new classes. `from __future__ import annotations` as first non-docstring line (`matrix_schema.py:21`).

---

### `src/subsideo/validation/matrix_writer.py` (MODIFY — renderer branch)

**Analog:** existing `_render_cell_column` + `write_matrix` in the same file (`matrix_writer.py:94-204`).

**Existing single-cell renderer** (from `matrix_writer.py:94-111`):
```python
def _render_cell_column(
    result: ProductQualityResult | ReferenceAgreementResult | None,
) -> str:
    """Render one side of a cell (product-quality or reference-agreement column)."""
    if result is None or not result.criterion_ids:
        return "—"
    rendered = [_render_measurement(cid, result.measurements) for cid in result.criterion_ids]
    any_calibrating = any(
        CRITERIA.get(cid) is not None and CRITERIA[cid].type == "CALIBRATING"
        for cid in result.criterion_ids
    )
    body = " / ".join(rendered)
    return f"*{body}*" if any_calibrating else body
```

**Existing write_matrix cell-loop** (from `matrix_writer.py:173-201`):
```python
for cell in cells:
    product = str(cell["product"]).upper()
    region = str(cell["region"]).upper()
    metrics_path = _validate_metrics_path(str(cell["metrics_file"]), manifest_path)
    metrics, err_reason = _load_metrics(metrics_path)
    if metrics is None:
        pq_col = f"RUN_FAILED ({err_reason})"
        ra_col = "RUN_FAILED"
        lines.append(
            f"| {product} | {region} | {_escape_table_cell(pq_col)} | "
            f"{_escape_table_cell(ra_col)} |"
        )
        continue
    pq_result = ProductQualityResult(
        measurements=dict(metrics.product_quality.measurements),
        criterion_ids=list(metrics.product_quality.criterion_ids),
    )
    ra_result = ReferenceAgreementResult(
        measurements=dict(metrics.reference_agreement.measurements),
        criterion_ids=list(metrics.reference_agreement.criterion_ids),
    )
    pq_col = _escape_table_cell(_render_cell_column(pq_result))
    ra_col = _escape_table_cell(_render_cell_column(ra_result))
    lines.append(f"| {product} | {region} | {pq_col} | {ra_col} |")
```

**Phase 2 branch strategy (D-11, D-15):** detect the `RTCEUCellMetrics` shape by reading the raw JSON and checking for the `per_burst` key (or by adding a `cell_schema: Literal["default", "rtc_eu"]` discriminator in the manifest). When detected, override the rendered cell text with the `X/N PASS` format and append the investigation-⚠ when `any_investigation_required`:

```python
# Pseudocode for the new branch (to insert into write_matrix after _load_metrics):
raw = json.loads(metrics_path.read_text())
if "per_burst" in raw:
    rtc_eu = RTCEUCellMetrics.model_validate(raw)
    pass_count, total = rtc_eu.pass_count, rtc_eu.total
    warn = " ⚠" if rtc_eu.any_investigation_required else ""
    ra_col = f"{pass_count}/{total} PASS{warn}"
    pq_col = "—"  # no product-quality gate for RTC in v1.1
    lines.append(f"| {product} | {region} | {pq_col} | {ra_col} |")
    continue
# Fall through to existing single-burst rendering for the 9 other cells.
```

**Helper-function extraction pattern** — match the existing `_load_manifest`, `_load_metrics`, `_render_cell_column`, `_validate_metrics_path` naming (underscore-prefixed module-internal helpers). Add a new `_render_rtc_eu_cell(metrics: RTCEUCellMetrics) -> tuple[str, str]` helper returning `(pq_col, ra_col)` so the main loop stays readable.

**Constraint:** the existing cell-render convention uses Markdown table rows with `_escape_table_cell` to escape pipes (`matrix_writer.py:114-116`). The RTC-EU branch must call `_escape_table_cell(ra_col)` for the same reason, even though `"5/5 PASS"` contains no pipe today — defence in depth for future format changes.

---

### `src/subsideo/validation/criteria.py` (MODIFY — registry additions + Literal extension)

**Analog:** existing `Criterion` dataclass + `CRITERIA: dict[str, Criterion]` registry (`criteria.py:27-158`).

**Existing Criterion dataclass** (from `criteria.py:27-36`):
```python
@dataclass(frozen=True)
class Criterion:
    """A single pass/fail threshold with provenance."""

    name: str
    threshold: float
    comparator: Literal[">", ">=", "<", "<="]
    type: Literal["BINDING", "CALIBRATING"]
    binding_after_milestone: str | None
    rationale: str
```

**Phase 2 extension** (modify the `type` Literal + add 2 registry entries):
```python
type: Literal["BINDING", "CALIBRATING", "INVESTIGATION_TRIGGER"]
```

**Registry-entry pattern to copy** (existing BINDING RTC entries, `criteria.py:40-57`):
```python
    # -- RTC BINDING (v1.0 compare_rtc.py:68-71) --
    "rtc.rmse_db_max": Criterion(
        name="rtc.rmse_db_max", threshold=0.5, comparator="<", type="BINDING",
        binding_after_milestone=None,
        rationale=(
            "OPERA RTC-S1 N.Am. agreement baseline (CONCLUSIONS_RTC_N_AM.md "
            "Sec 3); reference-agreement criterion, never tightened toward "
            "N.Am.'s observed 0.045 dB headroom (PITFALLS M1 target-creep prevention)."
        ),
    ),
    "rtc.correlation_min": Criterion(
        name="rtc.correlation_min", threshold=0.99, comparator=">", type="BINDING",
        binding_after_milestone=None,
        rationale=(
            "OPERA RTC-S1 cross-version correlation, hardcoded v1.0 "
            "compare_rtc.py:70; inherited unchanged."
        ),
    ),
```

**Phase 2 new entries** (paste at the end of the RTC section, before CSLC amplitude):
```python
    # -- RTC-EU INVESTIGATION triggers (Phase 2 D-13) --
    "rtc.eu.investigation_rmse_db_min": Criterion(
        name="rtc.eu.investigation_rmse_db_min", threshold=0.15, comparator=">=",
        type="INVESTIGATION_TRIGGER", binding_after_milestone=None,
        rationale=(
            "EU RTC per-burst investigation trigger: ~3x the N.Am. baseline "
            "(0.045 dB), still far below BINDING rtc.rmse_db_max (0.5 dB). "
            "NOT a gate -- triggers a CONCLUSIONS_RTC_EU.md investigation "
            "sub-section per D-14 when a burst meets or exceeds this RMSE. "
            "(Matrix writer renders INVESTIGATION_TRIGGER cells distinctly from "
            "BINDING/CALIBRATING gates.)"
        ),
    ),
    "rtc.eu.investigation_r_max": Criterion(
        name="rtc.eu.investigation_r_max", threshold=0.999, comparator="<",
        type="INVESTIGATION_TRIGGER", binding_after_milestone=None,
        rationale=(
            "EU RTC per-burst investigation trigger: 1 order of magnitude "
            "below the N.Am. baseline r = 0.9999, still above BINDING "
            "rtc.correlation_min (0.99). Catches structural disagreement "
            "(geometric shift, mis-registration) that RMSE may miss. "
            "NOT a gate -- D-14 CONCLUSIONS investigation trigger."
        ),
    ),
```

**Typed accessor pattern** (from `criteria.py:164-169` — one accessor per CRITERIA entry):
```python
def rtc_rmse_db_max() -> Criterion:
    return CRITERIA["rtc.rmse_db_max"]


def rtc_correlation_min() -> Criterion:
    return CRITERIA["rtc.correlation_min"]
```

Phase 2 adds two matching accessors at the end of the accessor block:
```python
def rtc_eu_investigation_rmse_db_min() -> Criterion:
    return CRITERIA["rtc.eu.investigation_rmse_db_min"]


def rtc_eu_investigation_r_max() -> Criterion:
    return CRITERIA["rtc.eu.investigation_r_max"]
```

**Downstream constraint — matrix_writer.py `_COMPARATOR_FNS` already covers `>=` and `<`** (see `matrix_writer.py:65-70`), so the comparator Literals in the new criteria don't require matrix_writer changes. But **`_render_measurement` currently emits PASS/FAIL verdicts for every criterion type, which is wrong for INVESTIGATION_TRIGGER** — Phase 2 must add a branch in `_render_measurement` (or, preferred, filter INVESTIGATION_TRIGGER criteria out of the main rendering path and surface them only via the per-burst `investigation_required` flag in `RTCEUCellMetrics`).

---

### `src/subsideo/validation/harness.py` (MODIFY — optional new helper for D-02)

**Analog:** existing `ensure_resume_safe` (`harness.py:391-421`) — the closest signature for "check file presence across a directory".

**Existing analog** (from `harness.py:391-421`):
```python
def ensure_resume_safe(
    cache_dir: Path,
    manifest_keys: Sequence[str],
) -> bool:
    """Return True if ``cache_dir`` contains every expected manifest-key entry.

    Non-destructive: never deletes or truncates files. Returns False when any
    listed key is missing, so the caller can decide between re-download and
    abort. Never raises (a corrupt cache_dir surface returns False + warning).
    ...
    """
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

**Phase 2 new helper pattern** (sibling of `ensure_resume_safe`, mirrors its signature style — keyword-only non-default `search_dirs`, `Path` return type, never raises):
```python
def find_cached_safe(
    granule_id: str,
    search_dirs: Sequence[Path],
) -> Path | None:
    """Return the first SAFE/.zip matching ``granule_id`` across ``search_dirs``, or None.

    D-02 mechanism for cross-cell SAFE cache reuse. Checks ``eval-rtc-eu/input/``
    first (caller controls order), then fallbacks such as ``eval-disp-egms/input/``,
    ``eval-dist-eu/input/``, ``eval-dist-eu-nov15/input/``.

    No symlinks, no copies -- returns the Path as-is. Caller passes the result
    to ``run_rtc(safe_paths=[path])`` wherever it lives.

    Parameters
    ----------
    granule_id : str
        S1 granule identifier (e.g. 'S1A_IW_SLC__1SDV_20240624T140113_...'),
        without trailing '.zip' or '.SAFE'. Match is substring-style on
        filename stems to tolerate .zip vs .SAFE directory variants.
    search_dirs : Sequence[Path]
        Directories to probe in order.

    Returns
    -------
    Path | None
        First path whose filename stem contains ``granule_id``; ``None`` when
        no cache hit in any search_dir.
    """
    for d in search_dirs:
        d = Path(d)
        if not d.exists() or not d.is_dir():
            continue
        try:
            for p in d.iterdir():
                if granule_id in p.stem:
                    return p
        except (OSError, PermissionError) as e:
            logger.warning("find_cached_safe: cannot read {}: {}", d, e)
            continue
    return None
```

**Export update** — add `find_cached_safe` to `validation/__init__.py` `__all__` (see `__init__.py:10-19`, `__init__.py:39-62`).

**Optional alternative** (mentioned in D-02 as "or extension to ensure_resume_safe"): extend `ensure_resume_safe` with an optional `fallback_dirs` parameter instead of adding a new helper. Planner chooses. The new-helper approach matches the existing harness convention that each helper has a narrow single purpose (see `harness.py:1-29` docstring "Public helpers").

---

## Shared Patterns (cross-cutting, applied to all Phase 2 files)

### SP-1: `if __name__ == "__main__":` guard (MANDATORY — `_mp` precondition)

**Source:** `run_eval.py:7-9`, `run_eval_disp_egms.py:29`, every `run_eval_*.py` (9/9).
**Apply to:** `run_eval_rtc_eu.py`. The probe script `scripts/probe_rtc_eu_candidates.py` does NOT need this guard (it does no multiprocessing).

```python
import warnings; warnings.filterwarnings("ignore")

EXPECTED_WALL_S = 10800   # Supervisor AST-parses this at the module level (D-11)

if __name__ == "__main__":
    ...  # ALL top-level work inside the guard
```

Rationale: `_mp.configure_multiprocessing()` fires inside `run_rtc()`; macOS `spawn` re-imports the module in every worker (see `CONCLUSIONS_RTC_N_AM.md:139-149` Bug 4 explanation).

### SP-2: `load_dotenv()` + `credential_preflight(...)` first

**Source:** `run_eval.py:24-27`, `run_eval_disp_egms.py:54-60`, `run_eval_cslc.py:26-28`, `run_eval_dist_eu.py:71-76` — uniform idiom across all eval scripts.
**Apply to:** `run_eval_rtc_eu.py`.

```python
from dotenv import load_dotenv
load_dotenv()
credential_preflight(["EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"])
```

Per CONTEXT.md §code-context "Established Patterns": add CDSE creds (`"CDSE_CLIENT_ID", "CDSE_CLIENT_SECRET"`) to the preflight list if any EU SAFE is not cached (Claude's discretion).

### SP-3: `loguru` logging (no `print()` except top-level banners)

**Source:** `harness.py:42` (`from loguru import logger`), `supervisor.py:47`, `matrix_writer.py:28`.
**Apply to:** `run_eval_rtc_eu.py` (use `logger.info(...)`, `logger.warning(...)`; reserve `print()` for section banners like `"=" * 70` headers — see `run_eval_disp_egms.py:83-90` banner pattern).

Per CONTEXT.md §Established Patterns: "Phase 2 script uses `from loguru import logger`; no print() except for top-level banners."

### SP-4: `from __future__ import annotations` as first non-docstring line

**Source:** `harness.py:30`, `matrix_schema.py:21`, `matrix_writer.py:20`, `criteria.py:21`, `results.py:16`, `compare_rtc.py:2` — every modified module uses it.
**Apply to:** new classes added to `matrix_schema.py`, new entries in `criteria.py`, new helper in `harness.py`. The header is already present; Phase 2 does not reintroduce it.

### SP-5: `frozen=True` dataclass immutability for registry entries

**Source:** `criteria.py:27` (`@dataclass(frozen=True) class Criterion:`).
**Apply to:** any new data-registry classes in Phase 2. New INVESTIGATION_TRIGGER entries inherit frozen-ness by virtue of being `Criterion(...)` constructions.

### SP-6: Per-stage `ensure_resume_safe` guard (explicit, not magic)

**Source:** ARCHITECTURE §7 "Resume-safe ensure — recommendation: generic helper in harness, called explicitly per-stage, not magic" + `harness.py:391-421`.
**Apply to:** every stage of the 5-stage per-burst pipeline in `run_eval_rtc_eu.py` (OPERA ref, DEM, orbit, SAFE, RTC) plus the D-08 outer per-burst whole-pipeline skip.

Example call shape (construct before each stage):
```python
expected_outputs = [f"{burst_id}_VV.cog.tif", f"{burst_id}_VH.cog.tif", "metrics_burst.json"]
if ensure_resume_safe(OUT / "output" / burst_id, expected_outputs):
    logger.info("skipping burst {}: cached", burst_id)
    continue
```

### SP-7: `ConfigDict(extra="forbid")` on every new Pydantic model

**Source:** `matrix_schema.py:34, 54, 74, 124` — all four models use it.
**Apply to:** new `BurstResult` + `RTCEUCellMetrics` classes added in Phase 2.

### SP-8: Two-space visual separator for helper-function sections

**Source:** `harness.py:44-45, 96-97, 275-277, 309-311, 386-388, 423-425` — every helper block is preceded by a `# ---...---` ASCII rule + blank line + section title.
**Apply to:** the new `find_cached_safe` helper in `harness.py` (if added).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` | research artifact | n/a | New artifact class introduced by v1.1 (FEATURES line 50, CONTEXT D-01). Prior research artifacts in `.planning/milestones/v1.1-research/` (e.g., `BOOTSTRAP_V1.1.md`) are scope docs, not probe reports. Schema must be defined from scratch by the planner. |
| RTC-EU matrix-cell rendering branch inside `matrix_writer.py` | renderer branch | batch transform | No existing cell type in `matrix_writer.py` uses the `X/N PASS` aggregate format — all 9 other cells render a single PQ + single RA column per `_render_cell_column`. Phase 2 introduces the aggregate format for the first time. Pattern must be synthesised from the existing `write_matrix` loop structure (match the underscore-helper naming + `_escape_table_cell` call). |
| INVESTIGATION_TRIGGER handling in `_render_measurement` | renderer branch | transform | The existing `_render_measurement` in `matrix_writer.py:73-91` hard-codes a PASS/FAIL verdict per criterion. Adding `INVESTIGATION_TRIGGER` requires a new non-verdict rendering path. No prior `type` variant has this shape; branch must be designed by the planner. |

---

## Metadata

**Analog search scope:**
- `/Volumes/Geospatial/Geospatial/subsideo/run_eval*.py` (9 scripts, root)
- `/Volumes/Geospatial/Geospatial/subsideo/CONCLUSIONS_*.md` (N.Am. / EU / session CONCLUSIONS docs at root)
- `/Volumes/Geospatial/Geospatial/subsideo/src/subsideo/validation/` (19 files, all inspected for role + data-flow match)
- `/Volumes/Geospatial/Geospatial/subsideo/results/` (matrix_manifest.yml — single file)
- `/Volumes/Geospatial/Geospatial/subsideo/Makefile` (single file — already has `eval-rtc-eu` target pre-wired per D-12 Phase 1)

**Files scanned (targeted reads):** 12 — `run_eval.py`, `run_eval_disp_egms.py`, `run_eval_cslc.py`, `run_eval_dist_eu.py` (header slice), `CONCLUSIONS_RTC_N_AM.md`, `harness.py`, `matrix_schema.py`, `matrix_writer.py`, `criteria.py`, `results.py`, `compare_rtc.py`, `supervisor.py`.

**Ripgrep searches:** `Literal["BINDING`, `INVESTIGATION_TRIGGER`, `metrics.json`, `RTCValidationResult`, `OPERA_L2_RTC|earthaccess\.search_data`.

**Key patterns identified (cross-file, cross-concern):**
1. Every `run_eval_*.py` uses the identical header: `import warnings; warnings.filterwarnings("ignore")` → `EXPECTED_WALL_S = <int>` → `if __name__ == "__main__":` → `load_dotenv()` → `credential_preflight([...])` → imports from `subsideo.validation.harness`. This is the non-negotiable skeleton for Phase 2's new script.
2. Extensions to the criteria registry follow a strict shape: add a dict entry with full `Criterion(...)` keyword args + rationale docstring + a matching typed accessor function below the registry. Phase 2 follows this shape for the 2 new INVESTIGATION_TRIGGER entries.
3. The Pydantic `matrix_schema.py` is designed to be extended by subclassing `MetricsJson` (the `schema_version` + extra="forbid" discipline is preserved). Phase 2's `RTCEUCellMetrics` subclass is the first consumer of this extension pattern.
4. Every `_private_helper` in `matrix_writer.py` and `harness.py` is colocated in a `# --- section header --- ` block — Phase 2's new `find_cached_safe` in harness and the new `_render_rtc_eu_cell` in matrix_writer follow this convention.

**Pattern extraction date:** 2026-04-22
