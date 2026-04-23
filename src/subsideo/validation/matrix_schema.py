"""Pydantic v2 schemas for per-eval meta.json + metrics.json sidecars.

These files are the contract between eval-script writers (run_eval_*.py)
and matrix_writer (Plan 01-08). matrix_writer NEVER globs CONCLUSIONS_*.md
(PITFALLS R3 / R5). The ``schema_version`` field enables forward evolution
without breaking readers.

meta.json  = provenance  (git_sha, input_hashes, platform, timestamps).
metrics.json = scientific (product_quality + reference_agreement serialised).

Consumes:
  - subsideo.validation.results (ProductQualityResult / ReferenceAgreementResult shape)

Patterns applied:
  - PATTERNS §4.5: Pydantic v2 ``BaseModel`` with ``Field(default=..., description=...)``.
  - PATTERNS §4.2: ``from __future__ import annotations`` as first non-docstring line.
  - D-03: schema drift visible via matrix_writer echoing CRITERIA thresholds alongside
    measured values (not enforced by this module).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProductQualityResultJson(BaseModel):
    """Serialised ``ProductQualityResult`` (validation.results).

    Shape mirrors the dataclass: named measurements + criterion IDs only,
    no stored pass/fail bool (D-08). ``evaluate()`` at read time is the
    pass/fail oracle.
    """

    model_config = ConfigDict(extra="forbid")

    measurements: dict[str, float] = Field(
        default_factory=dict,
        description="Measured values, keyed by measurement_key(criterion_id).",
    )
    criterion_ids: list[str] = Field(
        default_factory=list,
        description="Criterion IDs from validation.criteria.CRITERIA that apply here.",
    )


class ReferenceAgreementResultJson(BaseModel):
    """Serialised ``ReferenceAgreementResult`` (validation.results).

    Identical shape to ``ProductQualityResultJson`` — the distinction
    between product-quality and reference-agreement is structural
    (which field the result lives in), not shape.
    """

    model_config = ConfigDict(extra="forbid")

    measurements: dict[str, float] = Field(
        default_factory=dict,
        description="Measured values, keyed by measurement_key(criterion_id).",
    )
    criterion_ids: list[str] = Field(
        default_factory=list,
        description="Criterion IDs from validation.criteria.CRITERIA that apply here.",
    )


class MetaJson(BaseModel):
    """Per-eval provenance sidecar (``<cache_dir>/meta.json``).

    Provenance only -- never carries scientific results. Written by
    ``run_eval_*.py`` scripts at end of run so that matrix_writer can
    surface reproducibility context alongside measured values.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(
        default=1,
        description="Schema version; bump on breaking change (forward-compat hook).",
    )
    git_sha: str = Field(
        ...,
        description="HEAD sha of subsideo repo at run start.",
    )
    git_dirty: bool = Field(
        ...,
        description="True if repo had uncommitted changes when the run started.",
    )
    run_started_iso: str = Field(
        ...,
        description="ISO-8601 UTC timestamp of run start (e.g. '2026-04-21T00:00:00Z').",
    )
    run_duration_s: float = Field(
        ...,
        description="Wall-clock seconds from supervisor launch to eval completion.",
    )
    python_version: str = Field(
        ...,
        description="Python interpreter version string (sys.version).",
    )
    platform: str = Field(
        ...,
        description="platform.platform() string (e.g. 'darwin-arm64').",
    )
    input_hashes: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "SHA256 hex of primary inputs (SAFE zips, DEM tiles, orbit file, "
            "reference product). Intermediates NOT hashed -- scope per "
            "CONTEXT.md Claude's Discretion metrics.json schema."
        ),
    )


class MetricsJson(BaseModel):
    """Per-eval scientific sidecar (``<cache_dir>/metrics.json``).

    Read-time-evaluable contract: stores measurements + criterion_ids
    without baked-in pass/fail bools (D-08). matrix_writer consumes
    this file + the frozen ``CRITERIA`` registry to compute verdicts
    at render time, so a criteria.py threshold edit re-evaluates old
    metrics.json records correctly.
    """

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
        description=(
            "SHA256 of `conda list --explicit` output at run time, if "
            "available. ``None`` in environments without conda (pip-only "
            "installs, Docker smoke tests)."
        ),
    )


class BurstResult(BaseModel):
    """Per-burst row inside RTCEUCellMetrics.per_burst (Phase 2 D-10).

    Shape: one BurstResult per burst in the declarative BURSTS list in
    run_eval_rtc_eu.py. Matrix writer never reads these directly -- it
    aggregates via the parent RTCEUCellMetrics (D-11). CONCLUSIONS_RTC_EU.md
    (Plan 02-05) is the human-readable drilldown consumer.
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
    max_relief_m: float | None = Field(
        default=None,
        description=(
            "Max relief (max - min elevation, m) computed from the cached DEM "
            "in the burst bbox. None when DEM unavailable or computation failed. "
            "Surfaced in CONCLUSIONS terrain-regime coverage table (P1.1)."
        ),
    )
    cached: bool = Field(
        default=False,
        description=(
            "True when the SAFE was reused from another eval cache via "
            "find_cached_safe (D-02); False when downloaded fresh."
        ),
    )
    status: Literal["PASS", "FAIL"] = Field(
        ...,
        description=(
            "Per-burst verdict from reference_agreement criteria evaluation. "
            "FAIL captures both comparison-threshold failures AND exception "
            "paths in the eval-script try/except (D-06)."
        ),
    )
    product_quality: ProductQualityResultJson | None = Field(
        default=None,
        description=(
            "Null for RTC in v1.1 (no product-quality gate; Phase 1 D-04 + "
            "Phase 2 specifics). Reserved for Phase 3/4 self-consistency."
        ),
    )
    reference_agreement: ReferenceAgreementResultJson = Field(
        default_factory=ReferenceAgreementResultJson,
        description=(
            "Per-burst RMSE/correlation/bias_db measurements + RTC criterion "
            "IDs (rtc.rmse_db_max, rtc.correlation_min). Empty on exception-"
            "path FAIL rows."
        ),
    )
    investigation_required: bool = Field(
        default=False,
        description=(
            "True when RMSE >= 0.15 dB OR r < 0.999 (D-13 non-gate trigger). "
            "Drives the investigation annotation in matrix_writer and a CONCLUSIONS "
            "sub-section per D-14."
        ),
    )
    investigation_reason: str | None = Field(
        default=None,
        description=(
            "Human-readable trigger explanation populated by the eval script "
            "(e.g. 'RMSE 0.17 dB >= 0.15 dB'). None when "
            "investigation_required is False."
        ),
    )
    error: str | None = Field(
        default=None,
        description=(
            "repr(exception) captured by per-burst try/except (D-06). None "
            "when status == 'PASS' or when FAIL originates from a criterion "
            "comparison rather than an exception."
        ),
    )
    traceback: str | None = Field(
        default=None,
        description=(
            "traceback.format_exc() captured by per-burst try/except (D-06). "
            "None on non-exception paths."
        ),
    )


class RTCEUCellMetrics(MetricsJson):
    """RTC-EU multi-burst aggregate extending the base MetricsJson schema (D-09).

    Inherits schema_version / product_quality / reference_agreement /
    criterion_ids_applied / runtime_conda_list_hash from MetricsJson. Adds
    the aggregate count fields + per_burst drilldown list.

    matrix_writer (Plan 02-03) detects this schema via the presence of
    ``per_burst`` in the raw JSON and renders ``X/N PASS`` + investigation
    annotation instead of the default single-cell PQ/RA columns.
    """

    pass_count: int = Field(
        ...,
        ge=0,
        description="Count of bursts with status == 'PASS'.",
    )
    total: int = Field(
        ...,
        ge=1,
        description=(
            "Total number of bursts in per_burst (minimum 1 to avoid "
            "meaningless empty cells)."
        ),
    )
    all_pass: bool = Field(
        ...,
        description="True when pass_count == total (redundant convenience field).",
    )
    any_investigation_required: bool = Field(
        ...,
        description=(
            "True when any per_burst entry has investigation_required == True. "
            "matrix_writer reads this for the investigation annotation (D-15)."
        ),
    )
    reference_agreement_aggregate: dict[str, float | str] = Field(
        default_factory=dict,
        description=(
            "Aggregate summary: worst_rmse_db (float), worst_r (float), "
            "worst_burst_id (str). Drives RTCEU cell narrative in "
            "CONCLUSIONS. Computed by eval script from per_burst."
        ),
    )
    per_burst: list[BurstResult] = Field(
        default_factory=list,
        description=(
            "Per-burst drilldown list (one entry per BURSTS declarative "
            "config entry). Order matches BURSTS order for deterministic "
            "matrix-writer + CONCLUSIONS rendering."
        ),
    )
