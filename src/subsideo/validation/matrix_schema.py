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
