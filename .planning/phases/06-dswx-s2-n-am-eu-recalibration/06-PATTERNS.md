# Phase 6: DSWx-S2 N.Am. + EU Recalibration - Pattern Map

**Mapped:** 2026-04-26
**Files analyzed:** 22 (8 NEW + 14 MODIFIED) — 5 are research/doc artifacts; 17 source files.
**Analogs found:** 21 / 22 (one first-of-its-kind: `recalibrate_dswe_thresholds.py` joblib parallelism — see "No Analog Found").

---

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------------|------|-----------|----------------|---------------|
| `src/subsideo/products/dswx_thresholds.py` (NEW) | constants + frozen dataclass | request-response (read-only constants) | `src/subsideo/validation/criteria.py` (`Criterion` frozen dataclass + `CRITERIA` registry) | exact (frozen-dataclass + registry-dict precedent) |
| `run_eval_dswx_nam.py` (NEW) | eval-script (orchestrator) | request-response (CDSE → run_dswx → JRC compare → metrics) | `run_eval_dswx.py` (single-AOI EU eval) + `run_eval_dist_eu.py` (declarative EVENTS list + per-event try/except) | exact (forks dswx EU + adds CANDIDATES iteration) |
| `scripts/recalibrate_dswe_thresholds.py` (NEW) | multi-stage compute script | batch + transform (SAFE→intermediate cache→8400-pt grid→LOO-CV→threshold module write) | partial: `run_eval_dist_eu.py` (multi-event try/except + DistEUCellMetrics aggregate); no joblib precedent | first-of-its-kind for joblib parallelism (see "No Analog Found") |
| `notebooks/dswx_aoi_selection.ipynb` (NEW) | research notebook | transform (advisory tag scoring + MD render) | `scripts/probe_cslc_aoi_candidates.py` (CSLC AOI candidate probe-and-commit) | role-match (notebook vs script; same probe-and-commit pattern) |
| `notebooks/dswx_recalibration.ipynb` (NEW) | reporting notebook | request-response (load `*_results.json` + plot) | none — first reporting notebook in subsideo | first-of-its-kind |
| `CONCLUSIONS_DSWX_N_AM.md` (NEW) | conclusions doc | static markdown | `CONCLUSIONS_RTC_N_AM.md` + `CONCLUSIONS_DISP_N_AM.md` (Phase 4 + Phase 2 single-cell N.Am. CONCLUSIONS shape) | exact (template across 5 N.Am. cells) |
| `.planning/milestones/v1.1-research/dswx_fitset_aoi_candidates.md` (NEW) | probe artifact | static markdown | `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` (Phase 2 RTC-EU 5-regime probe) + `cslc_selfconsist_aoi_candidates.md` (Phase 3 CSLC AOI probe) | exact (probe-and-commit table format) |
| `docs/dswx_fitset_aoi_selection.md` (NEW) | rendered notebook | static markdown | none in subsideo (jupyter nbconvert output) | first-of-its-kind for nbconvert auto-rendered docs |
| `src/subsideo/products/dswx.py` (MOD: DELETE 3 module-consts; ADD `thresholds=` keyword; DECOMPOSE 1 fn → 2) | product orchestrator | request-response (band-read → DSWE → COG-write) | `src/subsideo/products/disp.py` + own current shape | self-modification |
| `src/subsideo/products/types.py` (MOD: ADD `region` field to DSWxConfig) | dataclass config | request-response | own current shape (DSWxConfig dataclass) | self-modification |
| `src/subsideo/validation/compare_dswx.py` (MOD: shoreline buffer + JRC retry refactor + diagnostics dict) | comparator | request-response | `src/subsideo/validation/effis.py:_build_retry_session` + own current shape | role-match (effis.py for retry session pattern) |
| `src/subsideo/validation/criteria.py` (MAYBE MOD: add `dswx.nam.investigation_f1_max=0.85`) | criteria registry | request-response | own current `rtc.eu.investigation_rmse_db_min` + `rtc.eu.investigation_r_max` (Phase 2 D-13/D-14) | exact (INVESTIGATION_TRIGGER pattern) |
| `src/subsideo/validation/harness.py` (MOD: add 6th `RETRY_POLICY['jrc']` branch) | harness retry policy | request-response | own current `RETRY_POLICY['EFFIS']` (Phase 5 D-18 amendment) | exact (per-source retry policy entry) |
| `src/subsideo/validation/matrix_schema.py` (MOD: ADD DswxNamCellMetrics, DswxEUCellMetrics + 4 helper types) | Pydantic v2 schema | request-response | own current `DistEUCellMetrics` + `DistNamCellMetrics` (Phase 5 D-25) | exact (additive Pydantic v2 extension; ZERO existing edits) |
| `src/subsideo/validation/matrix_writer.py` (MOD: ADD `_render_dswx_nam_cell` + `_render_dswx_eu_cell` AFTER dist:*) | renderer | request-response | own `_render_dist_eu_cell` + `_render_dist_nam_deferred_cell` + `_is_*_shape` discriminators | exact (dispatch ordering AFTER dist:*) |
| `run_eval_dswx.py` (MOD: 5 changes — region='eu', shoreline buffer, metrics.json schema upgrade, EXPECTED_WALL_S verify) | eval-script | request-response | own current shape | self-modification |
| `CONCLUSIONS_DSWX.md` (MOD: APPEND v1.1 sections after v1.0 baseline preamble) | conclusions doc | static markdown | `CONCLUSIONS_DISP_EU.md` + `CONCLUSIONS_DIST_EU.md` (Phase 4 D-13 + Phase 5 D-22 v1.0-baseline-preamble pattern) | exact (preamble + append pattern) |
| `docs/validation_methodology.md` (MOD: APPEND §5 only, 5 sub-sections) | methodology doc | static markdown | own existing §1 (CSLC cross-version phase) + §2/§3/§4 (Phase 3/4/5 appended) | exact (append-only by phase per Phase 3 D-15) |
| `Makefile` (MOD: verify `recalibrate-dswx` target exists or add) | build target | request-response | existing `eval-dswx-nam` + `eval-dswx-eu` (Phase 1 D-08) | exact |
| `src/subsideo/config.py` (MOD: ADD `dswx_region` field to Settings) | pydantic-settings | request-response | own current `Settings(BaseSettings)` (cdse_client_id, earthdata_username) | self-modification (extend pattern) |
| `results/matrix_manifest.yml` (VERIFY only — already references both cells per D-30) | manifest yaml | static yaml | own current shape | verify-only |

---

## Pattern Assignments

### `src/subsideo/products/dswx_thresholds.py` (constants + frozen dataclass; NEW)

**Analog:** `src/subsideo/validation/criteria.py` (Phase 1 D-09 frozen-dataclass `Criterion` + `CRITERIA: dict[str, Criterion]` registry)

**Imports + `from __future__ import annotations` pattern** (`src/subsideo/validation/criteria.py:22-26`):
```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
```

**Frozen dataclass pattern** (`src/subsideo/validation/criteria.py:28-47`):
```python
@dataclass(frozen=True)
class Criterion:
    """A single pass/fail threshold with provenance.

    ``gate_metric_key`` is only consulted by CSLC/DISP self-consistency
    criteria during matrix_writer measurement rendering (Phase 3 D-04).
    [...]
    """

    name: str
    threshold: float
    comparator: Literal[">", ">=", "<", "<="]
    type: Literal["BINDING", "CALIBRATING", "INVESTIGATION_TRIGGER"]
    binding_after_milestone: str | None
    rationale: str
    gate_metric_key: str = "median_of_persistent"
```

**Registry-dict pattern** (`src/subsideo/validation/criteria.py:50-198`):
```python
CRITERIA: dict[str, Criterion] = {
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
    # ... (15 entries total)
}
```

**Phase 6 application:** Mirror exactly. Use `@dataclass(frozen=True, slots=True)` (D-09 explicit upgrade) for `DSWEThresholds`. Add `slots=True` here even though `Criterion` does not use it — the threshold module is grep-discoverable, the slots upgrade is auditable in PR diff. Provenance fields (D-11) flow as additional dataclass attributes per RESEARCH.md proposed module template.

**Module template** (RESEARCH.md proposes the exact instances):
```python
@dataclass(frozen=True, slots=True)
class DSWEThresholds:
    WIGT: float
    AWGT: float
    PSWT2_MNDWI: float
    grid_search_run_date: str
    fit_set_hash: str
    fit_set_mean_f1: float
    held_out_balaton_f1: float
    loocv_mean_f1: float
    loocv_gap: float
    notebook_path: str
    results_json_path: str
    provenance_note: str

THRESHOLDS_NAM = DSWEThresholds(WIGT=0.124, AWGT=0.0, PSWT2_MNDWI=-0.5, ...)
THRESHOLDS_EU  = DSWEThresholds(WIGT=0.0,   AWGT=0.0, PSWT2_MNDWI=0.0, ...)  # placeholders until grid search

THRESHOLDS_BY_REGION: dict[str, DSWEThresholds] = {
    'nam': THRESHOLDS_NAM,
    'eu':  THRESHOLDS_EU,
}
```

---

### `src/subsideo/config.py` (MOD: pydantic-settings env-var)

**Analog:** Own current `Settings(BaseSettings)` (`src/subsideo/config.py:19-47`)

**Existing pydantic-settings pattern** (`src/subsideo/config.py:1-47`):
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

class Settings(BaseSettings):
    """Global subsideo configuration.

    Precedence: init kwargs > env vars > .env file > YAML file > defaults.
    """

    cdse_client_id: str = Field(default="", description="CDSE OAuth2 client ID")
    cdse_client_secret: str = Field(default="", description="CDSE OAuth2 client secret")
    earthdata_username: str = Field(default="", description="NASA Earthdata username")
    # [...]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        yaml_file=None,
        extra="ignore",
    )
```

**Phase 6 application (D-10):** Add a single field after `cache_dir`:
```python
from typing import Literal  # already imported via TypeVar; add Literal explicitly

class Settings(BaseSettings):
    # ... existing fields ...
    dswx_region: Literal["nam", "eu"] = Field(
        default="nam",
        description="DSWx threshold region selector. SUBSIDEO_DSWX_REGION env var.",
    )
```

`pydantic-settings` auto-derives the env-var name `SUBSIDEO_DSWX_REGION` from the field name. **Do NOT add an `env_prefix`** — current pattern uses `env_file=".env"` with no prefix; field names map verbatim to env vars (e.g. `cdse_client_id` → `CDSE_CLIENT_ID`).

---

### `src/subsideo/products/types.py` (MOD: add `region` field to DSWxConfig)

**Analog:** Own current `DSWxConfig` (`src/subsideo/products/types.py:141-150`)

**Existing dataclass pattern** (`src/subsideo/products/types.py:141-150`):
```python
@dataclass
class DSWxConfig:
    """Configuration for a DSWx-S2 surface water extent run."""

    s2_band_paths: dict[str, Path]  # keys: "B02","B03","B04","B08","B11","B12"
    scl_path: Path
    output_dir: Path
    output_epsg: int | None = None
    output_posting_m: float = 30.0
    product_version: str = "0.1.0"
```

**Phase 6 application (D-10):** Add a single optional field with default `None` (signals "use settings.dswx_region"):
```python
from typing import Literal

@dataclass
class DSWxConfig:
    s2_band_paths: dict[str, Path]
    scl_path: Path
    output_dir: Path
    output_epsg: int | None = None
    output_posting_m: float = 30.0
    product_version: str = "0.1.0"
    region: Literal["nam", "eu"] | None = None  # NEW (Phase 6 D-10)
```

`region=None` is resolved at `run_dswx` call-time via `config.region or settings.dswx_region`.

---

### `src/subsideo/products/dswx.py` (MOD: delete 3 consts; decompose; add `thresholds=` keyword)

**Analog:** Own current shape (`src/subsideo/products/dswx.py:27-39, 100-150, 567-682`).

**Existing 5-test diagnostic** (`src/subsideo/products/dswx.py:100-150`) — to be DECOMPOSED:
```python
def _compute_diagnostic_tests(
    blue: np.ndarray, green: np.ndarray, red: np.ndarray,
    nir: np.ndarray, swir1: np.ndarray, swir2: np.ndarray,
) -> np.ndarray:
    """Compute 5-bit DSWE diagnostic layer from S2 L2A bands."""
    eps = 1e-10

    # Scale-invariant ratios
    green_f = green.astype(np.float32)
    nir_f = nir.astype(np.float32)
    red_f = red.astype(np.float32)
    swir1_f = swir1.astype(np.float32)

    mndwi = (green_f - swir1_f) / (green_f + swir1_f + eps)
    ndvi = (nir_f - red_f) / (nir_f + red_f + eps)

    mbsrv = green_f + red_f
    mbsrn = nir_f + swir1_f
    awesh = (
        blue.astype(np.float32) + 2.5 * green_f
        - 1.5 * mbsrn - 0.25 * swir2.astype(np.float32)
    )

    diag = np.zeros(blue.shape, dtype=np.uint8)
    diag += np.uint8(mndwi > WIGT)                     # Test 1: bit 0
    diag += np.uint8(mbsrv > mbsrn) * 2                # Test 2: bit 1
    diag += np.uint8(awesh > AWGT) * 4                  # Test 3: bit 2

    diag += np.uint8(
        (mndwi > PSWT1_MNDWI) & (swir1 < PSWT1_SWIR1)
        & (nir < PSWT1_NIR) & (ndvi < PSWT1_NDVI)
    ) * 8

    diag += np.uint8(
        (mndwi > PSWT2_MNDWI) & (blue < PSWT2_BLUE)
        & (swir1 < PSWT2_SWIR1) & (swir2 < PSWT2_SWIR2)
        & (nir < PSWT2_NIR)
    ) * 16

    return diag
```

**Phase 6 application (D-05 + D-12):**
- DELETE module-level `WIGT` (line 27), `AWGT` (line 28), `PSWT2_MNDWI` (line 35).
- KEEP module-level `PSWT1_MNDWI/PSWT1_NIR/PSWT1_SWIR1/PSWT1_NDVI` (lines 30-33) AND `PSWT2_BLUE/PSWT2_NIR/PSWT2_SWIR1/PSWT2_SWIR2` (lines 36-39) — not in recalibration grid.
- Lift the body into two PUBLIC functions per RESEARCH.md `_compute_diagnostic_tests` decomposition proposal:
  - `compute_index_bands(blue, green, red, nir, swir1, swir2) -> IndexBands` (lines 113-130 = the 5 indices)
  - `score_water_class_from_indices(indices, blue, nir, swir1, swir2, *, thresholds: DSWEThresholds) -> np.ndarray` (lines 132-148 = the 5-bit packing)
- Update `__all__` (line 21): add `compute_index_bands`, `score_water_class_from_indices`, `IndexBands`.
- Keep private `_compute_diagnostic_tests` as a backward-compat shim that composes the two public functions.

**`run_dswx` resolver** — modify the call site (`src/subsideo/products/dswx.py:603-610`):
```python
# BEFORE (current):
diagnostic = _compute_diagnostic_tests(
    blue=bands["B02"], green=bands["B03"], red=bands["B04"],
    nir=bands["B08"], swir1=bands["B11"], swir2=bands["B12"],
)

# AFTER (Phase 6):
from subsideo.config import Settings
from subsideo.products.dswx_thresholds import THRESHOLDS_BY_REGION

settings = Settings()
region = cfg.region or settings.dswx_region
thresholds = THRESHOLDS_BY_REGION[region]
diagnostic = _compute_diagnostic_tests(
    blue=bands["B02"], green=bands["B03"], red=bands["B04"],
    nir=bands["B08"], swir1=bands["B11"], swir2=bands["B12"],
    thresholds=thresholds,
)
```

---

### `src/subsideo/validation/compare_dswx.py` (MOD: shoreline buffer + JRC retry refactor + diagnostics dict)

**Analog (shoreline buffer):** `src/subsideo/products/dswx.py:_rescue_connected_wetlands` (`src/subsideo/products/dswx.py:175-215`) — already uses `scipy.ndimage.binary_dilation`.

**Existing scipy dilation pattern** (`src/subsideo/products/dswx.py:196-214`):
```python
def _rescue_connected_wetlands(
    water_class: np.ndarray,
    radius_px: int = WETLAND_RESCUE_RADIUS_PX,
) -> np.ndarray:
    """Keep class-3 pixels only when they adjoin a class-1/2 core component."""
    from scipy.ndimage import binary_dilation

    core = (water_class == 1) | (water_class == 2)
    if not core.any():
        result = water_class.copy()
        result[water_class == 3] = 0
        return result

    # 8-connected dilation iterated `radius_px` times gives a square
    # buffer of side (2*radius+1).
    struct = np.ones((3, 3), dtype=bool)
    dilated_core = binary_dilation(core, structure=struct, iterations=radius_px)

    result = water_class.copy()
    isolated_class3 = (water_class == 3) & (~dilated_core)
    result[isolated_class3] = 0
    return result
```

**Phase 6 application (D-16):** Mirror the lazy-import + scipy.ndimage pattern. RESEARCH.md recommends `skimage.segmentation.find_boundaries(mode='thick')` as a cleaner one-liner alternative; both produce the 1-pixel boundary ring. The buffer is computed on the JRC native 4326 grid BEFORE the existing reproject step in `compare_dswx` (`compare_dswx.py:225-282`). New helper:

```python
def _compute_shoreline_buffer_mask(
    jrc_water_class: np.ndarray,
    iterations: int = 1,
) -> np.ndarray:
    """Compute 1-pixel buffer around JRC water/land boundary.

    Inserted BEFORE the rasterio.warp.reproject step in compare_dswx;
    the buffer mask is reprojected alongside the JRC water/land array
    using Resampling.nearest (categorical preservation).
    """
    from scipy.ndimage import binary_dilation

    water = (jrc_water_class == 1).astype(np.uint8)
    non_water = (jrc_water_class == 0).astype(np.uint8)
    water_dilated = binary_dilation(water, iterations=iterations)
    non_water_dilated = binary_dilation(non_water, iterations=iterations)
    return water_dilated & non_water_dilated.astype(bool)
```

**Analog (JRC fetch retry refactor):** `src/subsideo/validation/effis.py:_build_retry_session` (`src/subsideo/validation/effis.py:108-146`) — Phase 5 D-18 amendment for direct `requests.Session` driven by `RETRY_POLICY['EFFIS']`.

**EFFIS retry-session pattern** (`src/subsideo/validation/effis.py:108-146`):
```python
def _build_retry_session() -> requests.Session:
    """Return a ``requests.Session`` mounted with a urllib3 Retry adapter
    keyed on ``RETRY_POLICY['EFFIS']`` per the D-18 amendment.

    The harness still owns the policy declaration; this function projects it
    onto urllib3 + requests primitives for the REST-API dispatch path.
    """
    from urllib3.util.retry import Retry

    policy = RETRY_POLICY["EFFIS"]
    status_forcelist = [s for s in policy["retry_on"] if isinstance(s, int)]
    max_attempts = int(policy.get("max_attempts", 5))
    backoff_factor = float(policy.get("backoff_factor", 2))
    retry = Retry(
        total=max_attempts,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    sess = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=retry)
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    sess._effis_abort_on = policy.get("abort_on", [401, 403, 404])  # type: ignore[attr-defined]
    return sess
```

**Phase 6 application (D-25):** Refactor `compare_dswx._fetch_jrc_tile` (currently uses bare `urllib.request.urlretrieve` at `compare_dswx.py:91-115`). Two paths:

**Option A** (simple — preferred for a stand-alone HTTPS GET): Call the existing `harness.download_reference_with_retry(url, dest, source='jrc')` (`harness.py:517-648`). Requires adding the new `'jrc'` branch to `RETRY_POLICY` (see harness MOD below).

**Option B** (parallel to EFFIS): Define `_build_jrc_session()` in `compare_dswx.py` mirroring `effis.py:_build_retry_session`. Use only if the JRC fetch needs special header injection or rate-limiting controls.

**Recommendation per D-25:** Option A — `harness.download_reference_with_retry(source='jrc', ...)` is the canonical path. Keep `_fetch_jrc_tile` as a thin wrapper that handles the 404 → `None` semantics (currently distinct from `download_reference_with_retry` which raises `ReferenceDownloadError` on 404; `compare_dswx._fetch_jrc_tile` returns `None` for "tile not in coverage" which is benign). Catch the `ReferenceDownloadError` for 404 specifically.

**JRC URL-pattern** (`src/subsideo/validation/compare_dswx.py:32-50`) — keep unchanged unless plan-phase 06-01 verifies URL endpoint drift (RESEARCH.md Open Question 4):
```python
JRC_BASE_URL = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata"
    "/GSWE/MonthlyHistory/LATEST/tiles"
)
JRC_TILE_SIZE_PIXELS = 40000
JRC_TILE_SIZE_DEGREES = 10.0

def _jrc_tile_url(year: int, month: int, tile_x: int, tile_y: int) -> str:
    pixel_x = tile_x * JRC_TILE_SIZE_PIXELS
    pixel_y = tile_y * JRC_TILE_SIZE_PIXELS
    return f"{JRC_BASE_URL}/{year}/{year}_{month:02d}/{pixel_y:010d}-{pixel_x:010d}.tif"
```

**Diagnostics dict pattern (D-16):** Extend `DSWxValidationResult.reference_agreement` (`compare_dswx.py:319-330`):
```python
return DSWxValidationResult(
    product_quality=ProductQualityResult(measurements={}, criterion_ids=[]),
    reference_agreement=ReferenceAgreementResult(
        measurements={
            "f1": f1_shoreline_excluded,            # gate value (D-16)
            "precision": prec, "recall": rec, "accuracy": acc,
        },
        criterion_ids=["dswx.f1_min"],
        # diagnostics live in matrix_schema.DswxEUCellMetrics.reference_agreement.diagnostics:
        # {f1_full_pixels, shoreline_buffer_excluded_pixels, ...} — written by
        # run_eval_dswx.py / run_eval_dswx_nam.py on metrics.json assembly.
    ),
)
```

---

### `src/subsideo/validation/criteria.py` (MAYBE MOD: add `dswx.nam.investigation_f1_max=0.85`)

**Analog:** Own current `rtc.eu.investigation_rmse_db_min` + `rtc.eu.investigation_r_max` (Phase 2 D-13 INVESTIGATION_TRIGGER pattern).

**Existing INVESTIGATION_TRIGGER entries** (`src/subsideo/validation/criteria.py:69-97`):
```python
# -- RTC-EU INVESTIGATION triggers (Phase 2 D-13) --
# NOT gates. Non-gate markers flagging per-burst deviations that warrant
# a structured CONCLUSIONS_RTC_EU.md investigation sub-section (D-14).
# MUST NOT be used to tighten BINDING rtc.rmse_db_max/rtc.correlation_min
# (RTC-02 explicit).
"rtc.eu.investigation_rmse_db_min": Criterion(
    name="rtc.eu.investigation_rmse_db_min", threshold=0.15, comparator=">=",
    type="INVESTIGATION_TRIGGER", binding_after_milestone=None,
    rationale=(
        "EU RTC per-burst investigation trigger (~3x N.Am. baseline "
        "0.045 dB); still well below BINDING rtc.rmse_db_max (0.5 dB). "
        "NOT a gate -- triggers a CONCLUSIONS_RTC_EU.md investigation "
        "sub-section per D-14 when a burst meets or exceeds this RMSE. "
        "RTC-02: reference-agreement gates never tighten based on per-"
        "burst scores (PITFALLS M1 target-creep prevention)."
    ),
),
"rtc.eu.investigation_r_max": Criterion(
    name="rtc.eu.investigation_r_max", threshold=0.999, comparator="<",
    type="INVESTIGATION_TRIGGER", binding_after_milestone=None,
    rationale=(
        "EU RTC per-burst investigation trigger (1 order of magnitude "
        "below N.Am. baseline r = 0.9999); still above BINDING "
        "rtc.correlation_min (0.99). Catches structural disagreement "
        "(geometric shift, mis-registration) that RMSE may miss. "
        "NOT a gate -- D-14 CONCLUSIONS investigation trigger. "
        "RTC-02: criteria never tighten."
    ),
),
```

**Existing BINDING criterion (NEVER edited)** (`src/subsideo/validation/criteria.py:188-197`):
```python
# -- DSWx BINDING (v1.0 compare_dswx.py:298) --
"dswx.f1_min": Criterion(
    name="dswx.f1_min", threshold=0.90, comparator=">", type="BINDING",
    binding_after_milestone=None,
    rationale=(
        "DSWE-family architectural ceiling ~=0.92 per PROTEUS ATBD "
        "(CONCLUSIONS_DSWX.md Sec 3). 0.90 bar is ~2 pts below ceiling; "
        "moving it requires ML upgrade path (DSWX-V2-01) -- M4 goalpost "
        "prevention."
    ),
),
```

**Phase 6 application (D-20 — plan-phase decides; recommended ADD):** Append a new INVESTIGATION_TRIGGER entry — DO NOT edit existing `dswx.f1_min`:
```python
# -- DSWx-N.Am. INVESTIGATION trigger (Phase 6 D-20) --
"dswx.nam.investigation_f1_max": Criterion(
    name="dswx.nam.investigation_f1_max", threshold=0.85, comparator="<",
    type="INVESTIGATION_TRIGGER", binding_after_milestone=None,
    rationale=(
        "N.Am. positive-control DSWx F1 regression trigger. NOT a gate -- "
        "F1 < 0.85 against JRC over Tahoe/Pontchartrain triggers a "
        "BOA-offset / Claverie cross-cal / SCL-mask investigation sub-section "
        "in CONCLUSIONS_DSWX_N_AM.md AND halts EU recalibration via "
        "scripts/recalibrate_dswe_thresholds.py Stage 0 metrics.json gate "
        "(Phase 2 D-13/D-14 pattern; PITFALLS M4 goalpost prevention). "
        "BINDING dswx.f1_min stays at 0.90."
    ),
),
```

---

### `src/subsideo/validation/harness.py` (MOD: add `RETRY_POLICY['jrc']`)

**Analog:** Own current `RETRY_POLICY` dict (`src/subsideo/validation/harness.py:48-91`)

**Existing RETRY_POLICY pattern** (`src/subsideo/validation/harness.py:48-91`):
```python
RetrySource = Literal["CDSE", "EARTHDATA", "CLOUDFRONT", "HTTPS", "EFFIS"]

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
    "EFFIS": {
        # Phase 5 DIST-05 EFFIS WFS access. Public endpoint (no auth) but
        # owslib raises ConnectionError / TimeoutError from urllib3 rather
        # than HTTP status codes for transport-layer failures, so both kinds
        # appear in retry_on. 504 is added because EFFIS MapServer responses
        # can take 30+s for large bbox + date-window queries (RESEARCH Probe
        # 3 Risk F).
        "retry_on": [429, 503, 504, "ConnectionError", "TimeoutError"],
        "abort_on": [401, 403, 404],
        # ME-02 fix: declare retry parameters here so effis.py reads them
        # from the policy rather than hardcoding (CONTEXT D-18 single source
        # of truth). Backoff schedule: 2s, 4s, 8s, 16s, 32s.
        "max_attempts": 5,
        "backoff_factor": 2,
    },
}
```

**Phase 6 application (D-25):** Add the 6th branch (mirror `EFFIS` shape):
```python
# Update Literal:
RetrySource = Literal["CDSE", "EARTHDATA", "CLOUDFRONT", "HTTPS", "EFFIS", "jrc"]

# Append entry to RETRY_POLICY dict (after EFFIS):
"jrc": {
    # Phase 6 DSWX-04 JRC Global Surface Water Monthly History tile fetch.
    # Public HTTPS endpoint (no auth); jeodpp.jrc.ec.europa.eu / EC servers
    # serve large GeoTIFFs (~30 MB each at 10-degree tile size). 404 means
    # tile out-of-coverage (ocean tile or pre-1984/post-2021); benign,
    # propagated as None per existing _fetch_jrc_tile signature.
    "retry_on": [429, 503, 504, "ConnectionError", "TimeoutError"],
    "abort_on": [401, 403, 404],
    "max_attempts": 5,
    "backoff_factor": 2,
    "max_backoff_s": 60,
},
```

**Note on lowercase key:** existing keys use UPPERCASE (CDSE, EARTHDATA, etc.) BUT `'EFFIS'` precedent makes the convention `RetrySource = Literal[..., "EFFIS"]`. Phase 6 D-25 spec uses `'jrc'` lowercase — match D-25 verbatim. If plan-phase 06-01 prefers consistency, use `'JRC'` uppercase; both work, but the CONTEXT explicit phrasing is `RETRY_POLICY['jrc']`.

---

### `src/subsideo/validation/matrix_schema.py` (MOD: ADD DswxNamCellMetrics + DswxEUCellMetrics + 4 helpers)

**Analog:** Own current `DistEUCellMetrics` + `DistNamCellMetrics` (`src/subsideo/validation/matrix_schema.py:797-870`) — Phase 5 D-25 additive Pydantic v2 extension precedent.

**Existing additive-extension pattern** (`src/subsideo/validation/matrix_schema.py:797-820`):
```python
class DistEUCellMetrics(MetricsJson):
    """Phase 5 EU DIST aggregate cell (D-10 + D-25).

    matrix_writer detects this schema via presence of ``per_event`` in raw JSON
    (Plan 05-05 ``_is_dist_eu_shape`` discriminator).
    """

    pass_count: int = Field(..., ge=0, description="Count of events with status == 'PASS'.")
    total: int = Field(..., ge=1, description="Total events (3: aveiro, evros, spain_culebra).")
    all_pass: bool = Field(..., description="True when pass_count == total.")
    cell_status: DistEUCellStatus = Field(..., description="Whole-cell verdict.")
    worst_event_id: str = Field(..., description="event_id of the lowest-F1 event.")
    worst_f1: float = Field(..., description="Lowest F1 across events (point estimate).")
    any_chained_run_failed: bool = Field(
        ...,
        description=(
            "True if Aveiro chained_run.status not in {'structurally_valid', 'skipped'}. "
            "Renders as a warning glyph in matrix_writer (Plan 05-05)."
        ),
    )
    per_event: list[DistEUEventMetrics] = Field(
        default_factory=list,
        description="Per-event drilldown; order matches EVENTS list in run_eval_dist_eu.py.",
    )
```

**Existing Literal-status pattern** (`src/subsideo/validation/matrix_schema.py:644-651`):
```python
DistEUEventID = Literal["aveiro", "evros", "spain_culebra"]
ChainedRunStatus = Literal[
    "structurally_valid", "partial_output", "dist_s1_hang", "crashed", "skipped"
]
CMRProbeOutcome = Literal["operational_found", "operational_not_found", "probe_failed"]
ReferenceSource = Literal["operational_v1", "v0.1_cloudfront", "none"]
DistEUCellStatus = Literal["PASS", "FAIL", "MIXED", "BLOCKER"]
DistNamCellStatus = Literal["PASS", "FAIL", "DEFERRED"]
```

**Phase 6 application (D-26):** Add 6 new types — ZERO edits to existing types per Phase 1 D-09 immutability lock:

```python
# --- Phase 6 DSWx cell metrics (CONTEXT D-26) ---
# matrix_writer detects DswxNamCellMetrics via cell_status + selected_aoi keys;
# DswxEUCellMetrics via region='eu' + thresholds_used keys.

DswxNamCellStatus = Literal["PASS", "FAIL", "BLOCKER"]
DswxEUCellStatus = Literal["PASS", "FAIL", "BLOCKER"]


class DSWEThresholdsRef(BaseModel):
    """Provenance handle for the DSWEThresholds instance applied at run-time."""

    model_config = ConfigDict(extra="forbid")

    region: Literal["nam", "eu"]
    grid_search_run_date: str  # ISO date or '1996-01-01-PROTEUS-baseline' sentinel
    fit_set_hash: str          # sha256 hex of sorted (AOI, scene) IDs concatenated; 'n/a' for NAM


class PerAOIF1Breakdown(BaseModel):
    """One AOI's F1 in the recalibration fit set (DswxEU diagnostic)."""

    model_config = ConfigDict(extra="forbid")

    aoi_id: str                 # 'alcantara' / 'tagus' / etc.
    biome: str                  # 'Mediterranean reservoir' / etc.
    wet_scene_f1: float
    dry_scene_f1: float
    aoi_mean_f1: float


class LOOCVPerFold(BaseModel):
    """One fold of the post-hoc LOO-CV (DswxEU diagnostic)."""

    model_config = ConfigDict(extra="forbid")

    fold_idx: int
    left_out_aoi: str
    refit_best_WIGT: float
    refit_best_AWGT: float
    refit_best_PSWT2_MNDWI: float
    test_f1: float


class RegressionDiagnostic(BaseModel):
    """N.Am. positive-control regression diagnostic (DswxNam D-20)."""

    model_config = ConfigDict(extra="forbid")

    f1_below_regression_threshold: bool
    regression_diagnostic_required: list[str]  # e.g. ['boa_offset_check', 'claverie_xcal_check', 'scl_mask_audit']
    investigation_resolved: bool


class DswxNamCellMetrics(MetricsJson):
    """Phase 6 N.Am. DSWx positive-control cell aggregate (CONTEXT D-26)."""

    selected_aoi: str
    selected_scene_id: str
    cloud_cover_pct: float
    candidates_attempted: list[dict[str, str | int | float]]  # {aoi_name, scenes_found, cloud_min}
    region: Literal["nam"] = "nam"
    cell_status: DswxNamCellStatus
    named_upgrade_path: str | None = None
    regression: RegressionDiagnostic


class DswxEUCellMetrics(MetricsJson):
    """Phase 6 EU DSWx held-out-Balaton cell aggregate (CONTEXT D-26 + D-13)."""

    region: Literal["eu"] = "eu"
    thresholds_used: DSWEThresholdsRef
    fit_set_mean_f1: float
    loocv_mean_f1: float
    loocv_gap: float
    loocv_per_fold: list[LOOCVPerFold]
    per_aoi_breakdown: list[PerAOIF1Breakdown]
    f1_full_pixels: float
    shoreline_buffer_excluded_pixels: int
    cell_status: DswxEUCellStatus
    named_upgrade_path: str | None = None
```

**Note (D-15 honest FAIL):** `named_upgrade_path: str | None = None` mirrors Phase 4 D-11 `attributed_source: str | None` precedent (free-form string side-channel; not a Literal extension). Phase 6 D-15 explicitly chose this over extending `cell_status: Literal[...]` to keep the Literal stable across all 5 products.

---

### `src/subsideo/validation/matrix_writer.py` (MOD: ADD render branches AFTER dist:*)

**Analog:** Own `_render_dist_eu_cell` (`src/subsideo/validation/matrix_writer.py:501-525`) + `_render_dist_nam_deferred_cell` (`matrix_writer.py:528-560`) + their discriminators (`_is_dist_eu_shape`, `_is_dist_nam_shape`).

**Existing dispatch ordering** (`src/subsideo/validation/matrix_writer.py:599-682`):
```python
# Phase 4 DISP branch: metrics.json with a ``ramp_attribution`` key.
if metrics_path.exists() and _is_disp_cell_shape(metrics_path):
    cols = _render_disp_cell(metrics_path, region=str(cell["region"]))
    if cols is not None:
        # ... emit row, continue ...

# Phase 5 DIST-EU branch: metrics.json with a ``per_event`` key.
# Inserted AFTER disp:* per CONTEXT D-24 + the D-24 amendment in
# ROADMAP Phase 5 scope-amendment block (the structurally meaningful
# invariant is AFTER-disp; the relative ordering against cslc:* /
# dswx:* is a contemporary observation, not a forward lock).
if metrics_path.exists() and _is_dist_eu_shape(metrics_path):
    cols = _render_dist_eu_cell(metrics_path)
    if cols is not None:
        # ... emit row, continue ...

# Phase 5 DIST-NAM deferred-cell branch: metrics.json with
# cell_status='DEFERRED' + reference_source key.
if metrics_path.exists() and _is_dist_nam_shape(metrics_path):
    cols = _render_dist_nam_deferred_cell(metrics_path)
    if cols is not None:
        # ... emit row, continue ...

# Phase 3 CSLC self-consistency branch: metrics.json with a ``per_aoi`` key.
# (etc.)
```

**Existing `_render_dist_eu_cell`** (`src/subsideo/validation/matrix_writer.py:501-525`):
```python
def _render_dist_eu_cell(metrics_path: Path) -> tuple[str, str] | None:
    """Render Phase 5 DIST-EU multi-event aggregate as (pq_col, ra_col)."""
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
```

**Existing schema-discriminator pattern** (`src/subsideo/validation/matrix_writer.py:464-498`):
```python
def _is_dist_nam_shape(metrics_path: Path) -> bool:
    """Return True when metrics.json carries the DistNamCellMetrics shape.
    [...]
    """
    import json as _json

    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.debug("_is_dist_nam_shape: cannot read {}: {}", metrics_path, e)
        return False
    return (
        isinstance(raw, dict)
        and "reference_source" in raw
        and "cmr_probe_outcome" in raw
    )
```

**Phase 6 application (D-27):** Insert two new branches AFTER `dist:*` (currently last DIST branch is `_render_dist_nam_deferred_cell` at line 635-644). New branches need:

- `_is_dswx_nam_shape` discriminator: `"selected_aoi" in raw AND "candidates_attempted" in raw`
- `_is_dswx_eu_shape` discriminator: `"thresholds_used" in raw AND "loocv_gap" in raw`
- `_render_dswx_nam_cell` (mirrors `_render_dist_eu_cell` shape — emit `f1=0.XX [PASS|FAIL]`)
- `_render_dswx_eu_cell` (emits `f1=0.XX [PASS|FAIL]` Balaton + `named_upgrade_path` inline + LOO-CV gap inline)

**Sample render-cell template** (mirroring `_render_dist_eu_cell`):
```python
def _render_dswx_eu_cell(metrics_path: Path) -> tuple[str, str] | None:
    """Render Phase 6 EU DSWx held-out-Balaton cell as (pq_col, ra_col).

    pq_col: '—' (DSWx has no product-quality gate; Phase 6 D-26).
    ra_col format: 'F1=0.87 [PASS|FAIL]' + ' — named upgrade: <path>' if named_upgrade_path
                  + ' | LOOCV gap=0.012' inline diagnostic.
    """
    from subsideo.validation.matrix_schema import DswxEUCellMetrics

    try:
        m = DswxEUCellMetrics.model_validate_json(metrics_path.read_text())
    except Exception as e:
        logger.warning("Failed to parse DswxEUCellMetrics from {}: {}", metrics_path, e)
        return None

    f1_balaton = m.reference_agreement.measurements.get("f1", float("nan"))
    verdict = "PASS" if f1_balaton > 0.90 else "FAIL"
    base = f"f1={f1_balaton:.3f} {verdict}"
    if m.named_upgrade_path:
        base += f" — named upgrade: {m.named_upgrade_path}"
    base += f" | LOOCV gap={m.loocv_gap:.3f}"
    pq_col = "—"
    ra_col = base
    return pq_col, ra_col
```

**Insertion order (D-27 explicit):** After the `_is_dist_nam_shape` branch (line 635-644). The dispatcher block grows from 5 to 7 branches.

---

### `run_eval_dswx_nam.py` (NEW: orchestrator with CANDIDATES list)

**Analog:** `run_eval_dswx.py` (single-AOI EU eval, current shape) + `run_eval_dist_eu.py` (declarative EVENTS list with try/except per-event).

**Existing EXPECTED_WALL_S declaration pattern** (`run_eval_dswx.py:25-27`):
```python
import warnings; warnings.filterwarnings("ignore")

EXPECTED_WALL_S = 900   # Plan 01-07 supervisor AST-parses this constant (D-11)
```

**Existing _mp + import block pattern** (`run_eval_dist_eu.py:43-104`):
```python
import warnings; warnings.filterwarnings("ignore")  # noqa: E702, I001

EXPECTED_WALL_S = 60 * 60 * 8   # 28800s; supervisor AST-parses (Phase 1 D-11)


if __name__ == "__main__":
    # Phase 1 ENV-04 mandatory: PITFALLS P0.1 binding pre-condition for DIST-07
    # chained retry; idempotent + thread-safe. Fires BEFORE any
    # requests.Session-using import (asf_search, earthaccess) and BEFORE
    # `from dist_s1 import run_dist_s1_workflow` import.
    from subsideo._mp import configure_multiprocessing
    configure_multiprocessing()

    import hashlib
    import platform
    import subprocess
    import sys
    import time
    import traceback
    from dataclasses import dataclass
    from datetime import date, datetime, timezone
    from pathlib import Path
    from typing import Literal

    import numpy as np
    import rasterio
    from dotenv import load_dotenv
    from loguru import logger

    from subsideo.validation.harness import (
        credential_preflight,
    )
    # ... matrix_schema imports ...

    load_dotenv()
    credential_preflight(["EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"])

    run_started = datetime.now(timezone.utc)
    t_start = time.time()
```

**Existing declarative EVENTS list pattern** (`run_eval_dist_eu.py:113-164`):
```python
@dataclass(frozen=False)  # frozen=False so the track-number probe can update
class EventConfig:
    """Per-event declarative config (CONTEXT D-11)."""

    event_id: Literal["aveiro", "evros", "spain_culebra"]
    post_dates: list[date]
    aoi_bbox_wgs84: tuple[float, float, float, float]  # (W, S, E, N)
    mgrs_tile: str
    track_number: int
    track_number_source: str
    effis_filter_dates: tuple[date, date]
    expected_burnt_area_km2: float
    run_chained: bool
    post_date_buffer_days: int = 5

EVENTS: list[EventConfig] = [
    EventConfig(
        event_id="aveiro",
        post_dates=[date(2024, 9, 28), date(2024, 10, 10), date(2024, 11, 15)],
        aoi_bbox_wgs84=(-8.8, 40.5, -8.2, 41.0),
        mgrs_tile="29TNF",
        track_number=147,
        track_number_source="v1.0_cache",
        effis_filter_dates=(date(2024, 9, 15), date(2024, 9, 25)),
        expected_burnt_area_km2=1350.0,
        run_chained=True,
    ),
    # ... 2 more events ...
]

CACHE = Path("./eval-dist_eu")
CACHE.mkdir(exist_ok=True)
```

**Phase 6 application (D-18):** Mirror `run_eval_dist_eu.py` shape with two adaptations:

1. Use `dataclass(frozen=True)` (no track-number probe overwrite needed).
2. Wrap CANDIDATES iteration in a "first-AOI-with-cloud-free-scene wins" loop instead of running all candidates.

```python
import warnings; warnings.filterwarnings("ignore")  # noqa: E702, I001

EXPECTED_WALL_S = 1800   # 30 min; single AOI single scene (RESEARCH.md EXPECTED_WALL_S section)


if __name__ == "__main__":
    from subsideo._mp import configure_multiprocessing
    configure_multiprocessing()

    import hashlib
    import json as _json
    import os
    import platform
    import subprocess
    import sys
    import time
    import traceback
    from dataclasses import dataclass
    from datetime import datetime, timezone
    from pathlib import Path
    from typing import Literal

    import numpy as np
    from dotenv import load_dotenv
    from loguru import logger

    from subsideo.data.cdse import CDSEClient, extract_safe_s3_prefix
    from subsideo.products.dswx import run_dswx
    from subsideo.products.types import DSWxConfig
    from subsideo.validation.compare_dswx import compare_dswx
    from subsideo.validation.harness import (
        bounds_for_mgrs_tile,
        credential_preflight,
    )
    from subsideo.validation.matrix_schema import (
        DswxNamCellMetrics,
        MetaJson,
        ProductQualityResultJson,
        ReferenceAgreementResultJson,
        RegressionDiagnostic,
    )

    load_dotenv()
    credential_preflight([
        "CDSE_CLIENT_ID", "CDSE_CLIENT_SECRET",
        "CDSE_S3_ACCESS_KEY", "CDSE_S3_SECRET_KEY",
    ])

    @dataclass(frozen=True)
    class AOIConfig:
        """Per-candidate declarative config (D-18)."""
        aoi_name: str
        mgrs_tile: str
        epsg: int
        date_start: str
        date_end: str
        jrc_year: int
        jrc_month: int
        max_cloud_cover: float

    CANDIDATES: list[AOIConfig] = [
        AOIConfig(
            aoi_name="Lake Tahoe (CA)",
            mgrs_tile="10SFH",   # plan-phase 06-01 verifies via STAC
            epsg=32610,
            date_start="2021-07-01", date_end="2021-07-31",
            jrc_year=2021, jrc_month=7, max_cloud_cover=15.0,
        ),
        AOIConfig(
            aoi_name="Lake Pontchartrain (LA)",
            mgrs_tile="15RYP",   # plan-phase 06-01 verifies via STAC
            epsg=32615,
            date_start="2021-07-01", date_end="2021-07-31",
            jrc_year=2021, jrc_month=7, max_cloud_cover=15.0,
        ),
    ]

    CACHE = Path("./eval-dswx_nam")
    CACHE.mkdir(exist_ok=True)

    # -- Stage 1: AOI candidate iteration -----------------------------------
    selected_aoi: AOIConfig | None = None
    selected_scene = None
    candidates_attempted: list[dict] = []
    cdse = CDSEClient(...)

    for cand in CANDIDATES:
        try:
            stac_items = cdse.search_stac(
                collection="SENTINEL-2",
                bbox=list(bounds_for_mgrs_tile(cand.mgrs_tile, buffer_deg=0.1)),
                start=datetime.fromisoformat(f"{cand.date_start}T00:00:00"),
                end=datetime.fromisoformat(f"{cand.date_end}T23:59:59"),
                product_type="S2MSI2A", max_items=50,
            )
            cloud_free = [it for it in stac_items
                          if (it.get("properties", {}).get("eo:cloud_cover") or 100) <= cand.max_cloud_cover]
            candidates_attempted.append({
                "aoi_name": cand.aoi_name,
                "scenes_found": len(stac_items),
                "cloud_min": min((it["properties"].get("eo:cloud_cover", 100) for it in stac_items), default=100),
            })
            if cloud_free:
                selected_aoi = cand
                selected_scene = sorted(cloud_free, key=lambda i: i["properties"].get("eo:cloud_cover", 100))[0]
                logger.info("Selected: {} scene {}", cand.aoi_name, selected_scene.get("id"))
                break
        except Exception as e:
            logger.error("Candidate {} STAC search failed: {}", cand.aoi_name, e)
            candidates_attempted.append({"aoi_name": cand.aoi_name, "error": repr(e)})

    if selected_aoi is None:
        # write metrics.json with cell_status='BLOCKER' + exit non-zero
        ...

    # -- Stage 2-7: Same as run_eval_dswx.py but with config.region='nam' ---
    cfg = DSWxConfig(s2_band_paths=..., scl_path=..., output_dir=..., region="nam")
    result = run_dswx(cfg)
    validation = compare_dswx(result.output_path, year=selected_aoi.jrc_year,
                              month=selected_aoi.jrc_month, ...)

    # -- Stage 8: Regression flag (D-20) ------------------------------------
    f1_balaton = validation.reference_agreement.measurements["f1"]
    f1_below = f1_balaton < 0.85
    regression = RegressionDiagnostic(
        f1_below_regression_threshold=f1_below,
        regression_diagnostic_required=(
            ["boa_offset_check", "claverie_xcal_check", "scl_mask_audit"] if f1_below else []
        ),
        investigation_resolved=False,
    )

    # -- Stage 9: DswxNamCellMetrics write (D-26) ---------------------------
    metrics = DswxNamCellMetrics(
        product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResultJson(
            measurements={"f1": f1_balaton, ...},
            criterion_ids=["dswx.f1_min"],
        ),
        criterion_ids_applied=["dswx.f1_min"],
        selected_aoi=selected_aoi.aoi_name,
        selected_scene_id=selected_scene["id"],
        cloud_cover_pct=selected_scene["properties"]["eo:cloud_cover"],
        candidates_attempted=candidates_attempted,
        cell_status="PASS" if f1_balaton > 0.90 else "FAIL",
        named_upgrade_path=(
            None if f1_balaton > 0.90
            else "ML-replacement (DSWX-V2-01)" if f1_balaton >= 0.85
            else "BOA-offset / Claverie cross-cal regression"
        ),
        regression=regression,
    )
    (CACHE / "metrics.json").write_text(metrics.model_dump_json(indent=2))
```

---

### `run_eval_dswx.py` (MOD: 5 changes per D-26)

**Analog:** Own current shape (`run_eval_dswx.py:1-303`).

**Phase 6 modifications (D-26 + D-16 + D-10):**

1. **Stage 5** (`run_eval_dswx.py:235-241`) — Add `region="eu"` to DSWxConfig:
```python
# BEFORE:
cfg = DSWxConfig(
    s2_band_paths=band_paths, scl_path=scl_path,
    output_dir=dswx_out_dir, output_epsg=EPSG, output_posting_m=30.0,
)

# AFTER (Phase 6 D-10):
cfg = DSWxConfig(
    s2_band_paths=band_paths, scl_path=scl_path,
    output_dir=dswx_out_dir, output_epsg=EPSG, output_posting_m=30.0,
    region="eu",  # NEW
)
```

2. **Stage 7** (`run_eval_dswx.py:284-289`) — `compare_dswx` already returns `DSWxValidationResult`; modifications to its body land via the compare_dswx.py edits (shoreline buffer + diagnostics dict). The eval-script call site reads the new diagnostics dict via the matrix_schema schema (next change).

3. **NEW Stage 9** — Add `DswxEUCellMetrics` write at script tail (currently the script just prints + exits):
```python
# Stage 9: DswxEUCellMetrics write (D-26)
from subsideo.products.dswx_thresholds import THRESHOLDS_EU
from subsideo.validation.matrix_schema import (
    DswxEUCellMetrics, DSWEThresholdsRef,
    PerAOIF1Breakdown, LOOCVPerFold,
)

balaton_f1 = result.reference_agreement.measurements["f1"]

# fit_set_mean_f1, loocv_*, per_aoi_breakdown read from
# scripts/recalibrate_dswe_thresholds_results.json (Phase 6 D-13 + D-14):
recalib_results_path = Path("scripts/recalibrate_dswe_thresholds_results.json")
if recalib_results_path.exists():
    recalib = _json.loads(recalib_results_path.read_text())
    fit_set_mean_f1 = recalib["fit_set_mean_f1"]
    loocv_mean_f1 = recalib["loocv_mean_f1"]
    loocv_gap = recalib["loocv_gap"]
    loocv_per_fold = [LOOCVPerFold(**f) for f in recalib["loocv_per_fold"]]
    per_aoi_breakdown = [PerAOIF1Breakdown(**a) for a in recalib["per_aoi_breakdown"]]
else:
    fit_set_mean_f1 = loocv_mean_f1 = loocv_gap = float("nan")
    loocv_per_fold = []
    per_aoi_breakdown = []

metrics = DswxEUCellMetrics(
    product_quality=ProductQualityResultJson(measurements={}, criterion_ids=[]),
    reference_agreement=ReferenceAgreementResultJson(
        measurements={"f1": balaton_f1, ...},
        criterion_ids=["dswx.f1_min"],
    ),
    criterion_ids_applied=["dswx.f1_min"],
    region="eu",
    thresholds_used=DSWEThresholdsRef(
        region="eu",
        grid_search_run_date=THRESHOLDS_EU.grid_search_run_date,
        fit_set_hash=THRESHOLDS_EU.fit_set_hash,
    ),
    fit_set_mean_f1=fit_set_mean_f1,
    loocv_mean_f1=loocv_mean_f1,
    loocv_gap=loocv_gap,
    loocv_per_fold=loocv_per_fold,
    per_aoi_breakdown=per_aoi_breakdown,
    f1_full_pixels=...,                       # from compare_dswx diagnostics
    shoreline_buffer_excluded_pixels=...,     # from compare_dswx diagnostics
    cell_status="PASS" if balaton_f1 > 0.90 else "FAIL",
    named_upgrade_path=(
        None if balaton_f1 > 0.90
        else "ML-replacement (DSWX-V2-01)" if balaton_f1 >= 0.85
        else "fit-set quality review"
    ),
)
(OUT / "metrics.json").write_text(metrics.model_dump_json(indent=2))
```

4. **EXPECTED_WALL_S** (`run_eval_dswx.py:27`) — RESEARCH.md confirms 900s is sufficient; **no change required**. Plan-phase verifies during 06-01 cold-path probe.

5. **`compare_dswx` shoreline buffer** — handled in `compare_dswx.py` body modification (above).

---

### `notebooks/dswx_aoi_selection.ipynb` (NEW: research notebook)

**Analog:** `scripts/probe_cslc_aoi_candidates.py` (Phase 3 03-02 probe-and-commit) + `scripts/probe_rtc_eu_candidates.py` (Phase 2 D-04).

**Existing CandidateAOI dataclass pattern** (`scripts/probe_cslc_aoi_candidates.py:46-58`):
```python
@dataclass(frozen=True)
class CandidateAOI:
    """Declarative definition of a single probe candidate AOI."""

    aoi: str  # "Mojave/Coso-Searles" | "Iberian/Meseta-North" | ...
    region: str  # "NAM" | "EU"
    regime: str  # e.g. "desert-bedrock-playa-adjacent"
    label: str  # human-readable label
    bbox: tuple[float, float, float, float]  # west, south, east, north (WGS84)
    published_insar_stability_ref: str  # DOI / URL / paper citation
    expected_stable_pct_per_worldcover: float  # 0.0–1.0 sanity estimate
    cached_safe_fallback_path: str  # "eval-cslc/input" or "(none)"


CANDIDATES: list[CandidateAOI] = [
    CandidateAOI(
        aoi="Mojave/Coso-Searles", region="NAM",
        regime="desert-bedrock-playa-adjacent",
        # ... full row ...
    ),
    # ... 17 more candidates ...
]
```

**Phase 6 application (D-01 + D-02):** Notebook structure (cells in order):
1. Markdown cell — purpose, scope, links to BOOTSTRAP §5.2 + CONTEXT.md
2. Imports cell — `geopandas`, `rasterio`, `pystac_client`, `numpy`, `pandas`, `matplotlib`, `subsideo.data.cdse`, `subsideo.validation.harness`, `subsideo.validation.dswx_failure_modes` (NEW YAML; see RESEARCH.md "Notebook rendering mechanism" recommendation)
3. `CandidateAOI` dataclass cell (mirrors `probe_cslc_aoi_candidates.py:47-58` shape)
4. CANDIDATES list cell (18 candidates from RESEARCH.md "EU fit-set candidate AOIs" table)
5. Per-candidate scoring functions: `cloud_free_count(cdse, bbox, year)`, `wet_dry_ratio(jrc_url_pattern, aoi)`, `jrc_unknown_pct(jrc_array)` — auto-reject signals
6. Per-candidate scoring loop with `pd.DataFrame` output (one row per candidate)
7. Auto-reject filter cell (cloud_free < threshold OR wet/dry < 1.2 OR jrc_unknown > 20%)
8. Advisory-flag joining (read `dswx_failure_modes.yml` resource) — overlay frozen / mountain-shadow / tidal-turbidity / drought-year flags
9. 5-AOI selection cell (one per biome; user reviews)
10. Markdown summary cell with rationale per accepted/rejected
11. Write `.planning/milestones/v1.1-research/dswx_fitset_aoi_candidates.md` cell — table + rejection reasoning per Phase 2 `rtc_eu_burst_candidates.md` shape

**Probe artifact format** (from `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` opening):
```markdown
# DSWx-S2 EU Fit-set AOI Candidates -- Probe Report

**Probed:** YYYY-MM-DDThh:mm:ssZ
**Source query:** `pystac_client` against CDSE STAC + JRC GSW Monthly History tile fetches.
**Phase:** 6 (DSWx-S2 EU Recalibration)
**Decision:** D-01 (probe artifact) + D-02 (hybrid auto-reject + advisory pre-screen) + D-03 (P5.4 strict 1.2 ratio).

## Biome Coverage

| # | biome | aoi | bbox | mgrs_tile | jrc_unknown_pct | wet_dry_ratio | cloud_free_2021 | failure_mode_flags | recommended |
|---|-------|-----|------|-----------|-----------------|---------------|-----------------|---------------------|-------------|
| 1 | Mediterranean reservoir | Embalse de Alcántara (ES) | -7.05, 39.55, -6.65, 39.95 | 29SQE | 4.2% | 1.8 | 12 | clean | YES |
| 2 | Atlantic estuary | Tagus estuary (PT) | -9.45, 38.55, -8.85, 39.05 | 29SMC | 6.1% | 1.5 | 8 | tidal_turbidity (advisory) | YES |
| 3 | Boreal lake | Vänern (SE) | 12.40, 58.45, 14.20, 59.45 | 33VVF | 2.8% | 1.4 | 7 | frozen Dec-Feb (auto-reject months) | YES |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |
| 18 | Pannonian plain | Balaton (HU) | 17.20, 46.60, 18.20, 46.95 | 33TXP | 3.5% | 1.4 | 9 | clean | HELD-OUT (test set) |
```

---

### `notebooks/dswx_recalibration.ipynb` (NEW: reporting notebook)

**Analog:** No precedent in subsideo. Closest is `scripts/probe_cslc_aoi_candidates.py` for the matplotlib-figure-rendering pattern.

**Phase 6 application (D-04):** Notebook structure:
1. Markdown cell — purpose (load grid-search results, plot F1 surface, document held-out Balaton verdict)
2. Imports — `pandas`, `matplotlib`, `numpy`, `pyarrow.parquet`, `pathlib.Path`, `subsideo.products.dswx_thresholds`
3. Load `scripts/recalibrate_dswe_thresholds_results.json` cell
4. Per-(AOI, scene) `gridscores.parquet` ingestion (12 files, one per fit-set pair)
5. F1-surface 3D plot per (W, A, P) marginal cell (3 subplots)
6. Joint-best-gridpoint annotation
7. LOO-CV per-fold table cell
8. Held-out Balaton F1 cell (read from `eval-dswx/metrics.json`)
9. Threshold module reproduce cell — `from subsideo.products.dswx_thresholds import THRESHOLDS_EU; print(THRESHOLDS_EU)` — confirms the module-on-disk matches the recalibration result.

---

### `CONCLUSIONS_DSWX_N_AM.md` (NEW)

**Analog:** `CONCLUSIONS_DISP_N_AM.md` (`/Volumes/Geospatial/Geospatial/subsideo/CONCLUSIONS_DISP_N_AM.md`) + `CONCLUSIONS_RTC_N_AM.md` for the single-AOI N.Am. CONCLUSIONS shape.

**Existing CONCLUSIONS_DISP_N_AM.md header pattern** (lines 1-32):
```markdown
# N.Am. DISP-S1 Validation — Session Conclusions

**Date:** 2026-04-13
**Burst:** `t144_308029_iw1` / `T144-308029-IW1`
**Frame:** OPERA `F38504` (Southern California, relative orbit 144, ascending, sensing ~14:01 UTC)
**Period:** 2024-01-08 → 2024-06-24 (6 months, 15 S1A acquisitions at 12-day repeat)
**Result: STRUCTURALLY COMPLETE / SCIENTIFICALLY INCONCLUSIVE** — pipeline runs end-to-end and produces valid-format OPERA-spec outputs, but PHASS-unwrapping quality is insufficient for pixel-level validation against the OPERA DISP-S1 reference. Deferred for a later revisit after unwrapping improvements.

---

## 1. Objective

Validate that `subsideo v0.1.0` produces DISP-S1 (cumulative displacement) products that are scientifically consistent with the official [OPERA L3 DISP-S1] products distributed by NASA/JPL via ASF DAAC.

### 1.1 Pass Criteria (from PROJECT.md)

| Metric | Criterion |
|--------|-----------|
| LOS velocity correlation (Pearson r) | > 0.92 |
| LOS velocity bias (our − OPERA) | < 3 mm/yr |

---

## 2. Test Setup

### 2.1 Target

| Field | Value |
|-------|-------|
| Burst ID | `t144_308029_iw1` |
| Relative orbit | 144 (ascending) |
| Sensing time (per pass) | ~14:01 UTC |
| Geographic area | Southern California |
| UTM zone | 11N (EPSG:32611) |
```

**Phase 6 application (D-21):** Mirror exactly. Five sections per CONTEXT D-21(a):
1. Objective (positive control framing)
2. Test setup (selected AOI + scene + JRC ref)
3. Pipeline run (cold/warm wall + Stage logs)
4. Reference-agreement (F1 + precision + recall + OA; threshold = 0.90 BINDING)
5. Investigation findings — only populated if F1 < 0.85 (D-20)

---

### `CONCLUSIONS_DSWX.md` (MOD: APPEND v1.1 sections)

**Analog:** `CONCLUSIONS_DISP_EU.md` + `CONCLUSIONS_DIST_EU.md` (Phase 4 D-13 + Phase 5 D-22 v1.0-baseline-preamble pattern).

**Existing v1.0 baseline preamble pattern** — example header from current `CONCLUSIONS_DSWX.md:1-23`:
```markdown
# EU DSWx-S2 Validation — Session Conclusions

**Date:** 2026-04-15
**AOI:** Lake Balaton, Hungary (bbox `17.25, 46.70, 18.20, 47.00`, UTM 33N / EPSG:32633)
**Scene:** `S2B_MSIL2A_20210708T094029_N0500_R036_T33TYN_20230203T071138.SAFE`
**Reference:** JRC Global Surface Water Monthly History, release `LATEST`, 2021-07
**Result: STRUCTURALLY COMPLETE / SCIENTIFICALLY CALIBRATION-BOUND** — the full
subsideo → JRC validation plumbing works end-to-end and produces a valid
OPERA-spec DSWx COG. Final metrics against JRC over Lake Balaton are
**F1 0.7957, precision 0.9236, recall 0.6989, accuracy 0.9838**. The pass
criterion (F1 > 0.90) fails because PROTEUS DSWE's absolute PSWT2
thresholds, calibrated on Landsat surface reflectance over North
America, over-fire on dry Pannonia summer landscapes regardless of
reflectance-scale corrections. Closing the F1 gap requires offline
threshold recalibration over a multi-biome fit set — tracked as
follow-up work, not a blocker on v1.0.
```

**Phase 6 application (D-21(b)):** Insert a new heading "## v1.0 Balaton baseline (PROTEUS DSWE defaults; F1=0.7957 against JRC)" and re-bracket lines 1-289 as the v1.0 preamble. APPEND new v1.1 sections AFTER the v1.0 preamble:

```markdown
---

## v1.1 Recalibrated thresholds (region=eu)

[ ... grid search outcome, joint-best WIGT/AWGT/PSWT2_MNDWI, fit-set mean F1 ... ]

## v1.1 Held-out Balaton F1 + LOO-CV gap

[ ... balaton F1 with recalibrated thresholds; LOO-CV gap < 0.02 ... ]

## v1.1 Matrix-cell verdict + named upgrade path

[ ... cell_status; named_upgrade_path if 0.85 ≤ F1 < 0.90; reasoning ... ]
```

---

### `docs/validation_methodology.md` (MOD: APPEND §5)

**Analog:** Own current §1-§4 (Phase 3/4/5 append-only).

**Existing §1 structural-argument-leads pattern** (`docs/validation_methodology.md:17-50`):
```markdown
## 1. CSLC cross-version phase impossibility

<a name="cross-version-phase"></a>

**TL;DR:** Interferometric phase comparison between CSLCs produced by different
isce3 **major** versions yields coherence ≈ 0 regardless of which phase
corrections are applied on top. Amplitude-based metrics (correlation, RMSE in
dB) remain valid across versions. **Do NOT re-attempt with additional
corrections.**

### 1.1 Structural argument — the SLC interpolation kernel changed

[ ... 4-paragraph structural argument ... ]

### 1.2 Policy statement

**Do NOT re-attempt with additional corrections.** [ ... ]
```

**Phase 6 application (D-22):** Append §5 with 5 sub-sections per CONTEXT D-22 structural-leads order:

```markdown
---

## 5. DSWE F1 ceiling, held-out Balaton, and threshold-module design

<a name="dswe-recalibration-methodology"></a>

**TL;DR:** [ ... 3-sentence summary ... ]

### 5.1 DSWE F1 ceiling citation chain

[ Either PROTEUS ATBD direct citation per D-17 path (a)/(c), OR own-data
  fallback per path (d): "Empirical bound observed over our 6-AOI evaluation
  at F1 ≈ X.YZ ..." ]

### 5.2 Held-out Balaton vs fit-set methodology

[ Why Balaton is the gate per BOOTSTRAP §5.4 + PITFALLS P5.1; why fit-set
  mean is not. ]

### 5.3 Shoreline 1-pixel buffer rationale

[ P5.2 commission/omission asymmetry; uniform application across grid search
  + reporting per D-16. ]

### 5.4 LOO-CV overfit detection (gap < 0.02)

[ DSWX-06 acceptance + P5.1; post-hoc on best-gridpoint design per D-14. ]

### 5.5 Threshold module + region selector design

[ DSWX-05 typed-constants over YAML/runtime-config; pydantic-settings env-var
  + DSWxConfig field per D-10; v1.0 module-constant deletion per D-12. ]
```

§5 leads with structural argument (§5.1) before empirical evidence (§5.2-§5.4) before design rationale (§5.5) — Phase 3 D-15 "kernel argument leads, diagnostic appendix follows" precedent.

---

### `Makefile` (MOD: verify `recalibrate-dswx` target)

**Analog:** Existing Makefile has `eval-dswx-nam` + `eval-dswx-eu` (Phase 1 D-08 wired all 10 cells).

**Existing supervisor-wrapped target pattern** (Phase 1 ENV-09):
```makefile
eval-dswx-eu:
	micromamba run -n subsideo python -m subsideo.validation.supervisor run_eval_dswx.py
.PHONY: eval-dswx-eu
```

**Phase 6 application (D-Claude's-Discretion 06-01 verification):**
```makefile
recalibrate-dswx:
	micromamba run -n subsideo python -m subsideo.validation.supervisor scripts/recalibrate_dswe_thresholds.py
.PHONY: recalibrate-dswx
```

Plan-phase 06-01 grep-checks Makefile for `recalibrate-dswx:` literal; if absent, append.

---

### `.planning/milestones/v1.1-research/dswx_fitset_aoi_candidates.md` (NEW probe artifact)

**Analog:** `.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md` (Phase 2 D-04 probe artifact) + `cslc_selfconsist_aoi_candidates.md` (Phase 3 D-10).

**Existing probe-report header + table pattern** (`rtc_eu_burst_candidates.md:1-12`):
```markdown
# RTC-S1 EU Burst Candidates -- Probe Report

**Probed:** 2026-04-23T15:40:02Z
**Source query:** `asf_search` + `earthaccess` against ASF DAAC.
**Phase:** 2 (RTC-S1 EU Validation)
**Decision:** D-01 (probe artifact) + D-03 (5-regime fixed list) + D-04 (Claude drafts; user reviews).

## Regime Coverage

| # | regime | label | centroid_lat | expected_max_relief_m | opera_rtc_granules_2024_2025 | best_match_sensing_utc | best_match_granule | cached_safe | burst_id (fill-in) |
|---|--------|-------|--------------|-----------------------|------------------------------|------------------------|--------------------|-------------|---------------------|
| 1 | Alpine | Swiss/Italian Alps (Valtellina region) | 46.35 | ~3200 | 2907 | 2024-05-02T05:35:20Z | `S1A_IW_SLC__1SDV_...` | (none) | (derive ...) |
```

**Phase 6 application (D-01):** Mirror exactly with biome rows. Already drafted in RESEARCH.md "EU fit-set candidate AOIs" section as the 18-row table. Plan-phase 06-01 lands the .md with user lock-in checkpoint BEFORE fit-set compute commits.

---

## Shared Patterns

### `_mp.configure_multiprocessing()` invocation at top of every `run_*()` (D-23)

**Source:** `src/subsideo/_mp.py:39-109` + `run_eval_dist_eu.py:48-54`
**Apply to:** `run_eval_dswx_nam.py`, `scripts/recalibrate_dswe_thresholds.py` (D-23 explicit list)

**Concrete pattern** (`run_eval_dist_eu.py:48-54`):
```python
if __name__ == "__main__":
    # Phase 1 ENV-04 mandatory: PITFALLS P0.1 binding pre-condition for DIST-07
    # chained retry; idempotent + thread-safe. Fires BEFORE any
    # requests.Session-using import (asf_search, earthaccess) and BEFORE
    # `from dist_s1 import run_dist_s1_workflow` import.
    from subsideo._mp import configure_multiprocessing
    configure_multiprocessing()

    # ... rest of imports ...
```

**RESEARCH.md note (joblib coexistence):** loky default start method is SPAWN, not FORK. `_mp.configure_multiprocessing()` parent-fork bundle and loky-spawn workers coexist cleanly. No special handling needed — call `configure_multiprocessing()` at the top of `recalibrate_dswe_thresholds.py:main()` and use `joblib.Parallel(n_jobs=-1, backend='loky')` with NO context override.

---

### `EXPECTED_WALL_S` declaration before `if __name__ == "__main__"` (D-24)

**Source:** `run_eval_dswx.py:25-27` + `run_eval_dist_eu.py:43-45`
**Apply to:** `run_eval_dswx_nam.py` (1800s), `scripts/recalibrate_dswe_thresholds.py` (21600s)

**Concrete pattern** (`run_eval_dist_eu.py:43-45`):
```python
import warnings; warnings.filterwarnings("ignore")  # noqa: E702, I001

EXPECTED_WALL_S = 60 * 60 * 8   # 28800s; supervisor AST-parses (Phase 1 D-11)
```

The supervisor AST-parser whitelists `BinOp` of literal `Constant` nodes; both `21600` and `60 * 60 * 6` work. Supervisor budget = `2 × EXPECTED_WALL_S` per Phase 1 ENV-05.

---

### `credential_preflight([...])` immediately after `load_dotenv()` (D-23 implicit)

**Source:** `src/subsideo/validation/harness.py:301-328` + `run_eval_dist_eu.py:105-106`
**Apply to:** `run_eval_dswx_nam.py`, `scripts/recalibrate_dswe_thresholds.py`

**Concrete pattern** (`run_eval_dist_eu.py:105-106`):
```python
load_dotenv()
credential_preflight(["EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"])
```

Phase 6 N.Am. + recalibration scripts need 4 vars per CONTEXT integration:
```python
credential_preflight([
    "CDSE_CLIENT_ID", "CDSE_CLIENT_SECRET",
    "CDSE_S3_ACCESS_KEY", "CDSE_S3_SECRET_KEY",
])
```

---

### Per-AOI / per-event try/except isolation (D-Claude's-Discretion 06-01)

**Source:** `run_eval_dist_eu.py:496-531` (per-event try/except + FAIL-row record on exception)
**Apply to:** `run_eval_dswx_nam.py` Stage 1 (CANDIDATES iteration), `scripts/recalibrate_dswe_thresholds.py` Stage 4 (joblib-parallel grid search)

**Concrete pattern** (`run_eval_dist_eu.py:496-531`):
```python
per_event: list[DistEUEventMetrics] = []
for cfg in EVENTS:
    t_event_start = time.time()
    print(f"-- Event: {cfg.event_id} (track={cfg.track_number}) --")
    try:
        row = process_event(cfg)
        per_event.append(row)
        elapsed = time.time() - t_event_start
        print(f"  {cfg.event_id} {row.status} in {elapsed:.0f}s ...")
    except Exception as e:  # noqa: BLE001 -- per-event isolation (Phase 2 D-06)
        elapsed = time.time() - t_event_start
        tb = traceback.format_exc()
        logger.error("Event {} FAIL ({:.0f}s): {}", cfg.event_id, elapsed, e)
        per_event.append(
            DistEUEventMetrics(
                event_id=cfg.event_id, status="FAIL",
                # ... default-zero metrics ...
                error=repr(e), traceback=tb,
            )
        )
```

---

### Pydantic v2 additive extension (NEVER edit existing types)

**Source:** `src/subsideo/validation/matrix_schema.py:797-870` (Phase 5 D-25 lock)
**Apply to:** `matrix_schema.py` Phase 6 D-26 (DswxNamCellMetrics, DswxEUCellMetrics + 4 helpers)

**Pattern:** Each new schema class extends `MetricsJson` (or another existing base). Sub-types use `BaseModel + ConfigDict(extra="forbid")`. ZERO edits to existing types per Phase 1 D-09 immutability lock.

---

### Honest FAIL via `named_upgrade_path: str | None` field, NOT Literal extension (D-15)

**Source:** Phase 4 D-11 `attributed_source: str | None` + Phase 5 D-25 `cell_status` Literal stable
**Apply to:** DswxNamCellMetrics + DswxEUCellMetrics

**Pattern:** Free-form string side-channel field; matrix_writer concatenates `named_upgrade_path` only when set. Keeps cell_status Literal stable across all 5 products (Phase 1 D-09 lock).

---

### v1.0-baseline-preamble + v1.1-section-append for CONCLUSIONS (D-21)

**Source:** Phase 4 D-13 + Phase 5 D-22; `CONCLUSIONS_DISP_EU.md` + `CONCLUSIONS_DIST_EU.md`
**Apply to:** `CONCLUSIONS_DSWX.md` Phase 6 v1.1 append

**Pattern:** v1.0 narrative becomes leading "v1.0 Balaton baseline (PROTEUS DSWE defaults; F1=0.7957 against JRC)" section; v1.1 sections append below. Manifest filename unchanged (`CONCLUSIONS_DSWX.md` for `dswx:eu`, `CONCLUSIONS_DSWX_N_AM.md` for `dswx:nam`) — no `git mv`, no manifest edit needed.

---

### Append-only by phase for `docs/validation_methodology.md` (D-22 + Phase 3 D-15)

**Source:** `docs/validation_methodology.md` §1 + §2 + §3 + §4
**Apply to:** `validation_methodology.md` Phase 6 §5 append

**Pattern:** Phase 6 owns §5 only; Phase 7 owns §6+. NO cross-section TOC at Phase 6 close — that's Phase 7 territory.

---

## No Analog Found

Files with no close match in the codebase (planner should use RESEARCH.md patterns + Context7 documentation):

| File | Role | Data Flow | Reason | Recommended Pattern Source |
|------|------|-----------|--------|----------------------------|
| `scripts/recalibrate_dswe_thresholds.py` (joblib parallel grid search across 12 (AOI, scene) pairs × 8400 gridpoints) | multi-stage compute script | batch + transform | **First joblib-parallel script in subsideo.** No precedent for `Parallel(n_jobs=-1, backend='loky')` over outer fan-out + inner sequential numpy threshold loop. | RESEARCH.md "Joblib + `_mp.configure_multiprocessing()` pattern" section + Context7 `/joblib/joblib` query for `Parallel + delayed` syntax. Stage layout in CONTEXT.md "Claude's Discretion" `recalibrate_dswe_thresholds.py` 11-stage breakdown. |
| `notebooks/dswx_recalibration.ipynb` (loads `*_results.json` + plots F1 surface + reproduces frozen constants) | reporting notebook | request-response (read JSON, render figures) | First reporting notebook in subsideo (existing `notebooks/` dir is empty). | Standard matplotlib `constrained_layout=True` pattern (STACK.md). Read `pyarrow.parquet` for per-pair gridscores; `pandas.DataFrame` for LOO-CV table. |
| `docs/dswx_fitset_aoi_selection.md` (auto-rendered from `notebooks/dswx_aoi_selection.ipynb`) | rendered notebook | static markdown (auto-generated) | First auto-generated docs file. | RESEARCH.md "Notebook rendering mechanism" section: `make dswx-fitset-aoi-md` Makefile target invoking `jupyter nbconvert --to markdown ...` + pre-commit hook gating against drift. |
| `src/subsideo/validation/dswx_failure_modes.yml` (NEW resource per RESEARCH.md "OSM / Copernicus Land Monitoring" recommendation, hardcoded YAML) | YAML resource | static yaml | New YAML resource format in subsideo (no precedent for hardcoded failure-mode mapping). | RESEARCH.md "OSM / Copernicus Land Monitoring failure-mode tag query mechanism" section — option (c) hardcoded list. Read via `importlib.resources.files('subsideo.validation') / 'dswx_failure_modes.yml'`. |

**Key recommendation for `recalibrate_dswe_thresholds.py`:** Use `joblib.Parallel(n_jobs=-1, backend='loky')` with NO `mp_context` override. Loky workers default to spawn, which is SAFE on macOS Python <3.14 and re-imports `subsideo` modules cleanly. Each worker's signature should be picklable: `grid_search_one_pair(aoi_id: str, scene_id: str, intermediate_cache_dir: Path, threshold_grid: list[tuple[float, float, float]]) -> bytes` (returns serialised parquet bytes).

**Per-(AOI, scene) restart-safe checkpoint via `pyarrow.parquet`** (RESEARCH.md "pyarrow availability" section):
```python
import pyarrow as pa
import pyarrow.parquet as pq

table = pa.Table.from_arrays(
    [wigts, awgts, pswt2_mndwis, f1s, precisions, recalls, accuracies,
     n_pixels_total, n_pixels_shoreline_excluded],
    names=['WIGT', 'AWGT', 'PSWT2_MNDWI', 'f1', 'precision', 'recall', 'accuracy',
           'n_pixels_total', 'n_pixels_shoreline_excluded'],
)
pq.write_table(table, output_path / 'gridscores.parquet', compression='zstd')
```

---

## Metadata

**Analog search scope:** `src/subsideo/{products,validation}/`, `run_eval_*.py`, `scripts/`, `notebooks/`, `.planning/milestones/v1.1-research/`, `docs/`, `CONCLUSIONS_*.md`
**Files scanned:** 11 source files (matrix_writer.py, matrix_schema.py, criteria.py, harness.py, effis.py, _mp.py, dswx.py, types.py, config.py, compare_dswx.py) + 4 eval scripts (run_eval_dswx.py, run_eval_dist_eu.py, run_eval_disp.py, run_eval_disp_egms.py) + 1 probe script + 4 CONCLUSIONS files + 1 methodology doc + 2 milestone artifacts.
**Pattern extraction date:** 2026-04-26
**Phase 6 alignment:** D-01..D-30 (CONTEXT lock-in) — all 30 decisions referenced; Claude's Discretion items mapped to RESEARCH.md sections.
