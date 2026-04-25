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


# --- Phase 3 CSLC self-consistency cell metrics (03-CONTEXT D-03 + D-06 + D-11) ---

AOIStatus = Literal["PASS", "FAIL", "CALIBRATING", "BLOCKER", "SKIPPED"]
CSLCCellStatus = Literal["PASS", "FAIL", "CALIBRATING", "MIXED", "BLOCKER"]


class AOIResult(BaseModel):
    """Per-AOI row for CSLCSelfConsist*CellMetrics.per_aoi (Phase 3 D-06).

    ``attempts`` carries the Mojave fallback-chain per CONTEXT D-11: empty list
    for leaf AOIs (SoCal, Iberian); 1-4 entries for the Mojave parent row with
    ``attempt_index`` + ``reason`` populated on each nested AOIResult. First
    PASS/CALIBRATING attempt wins; all-FAIL => parent status='BLOCKER'.
    """

    model_config = ConfigDict(extra="forbid")

    aoi_name: str = Field(..., description="Stable label: 'SoCal' / 'Mojave' / 'Iberian' / etc.")
    regime: str = Field(default="", description="Free-form regime label for CONCLUSIONS tables.")
    burst_id: str | None = Field(
        default=None,
        description="JPL lowercase burst ID; null for parent Mojave rows.",
    )
    sensing_window: list[str] = Field(
        default_factory=list,
        description=(
            "ISO-8601 UTC strings, one per epoch. 15 entries per leaf AOI "
            "(SoCal + each Mojave fallback + Iberian primary + each Iberian fallback); "
            "empty list for parent Mojave/Iberian rows that delegate to fallback_chain."
        ),
    )
    status: AOIStatus = Field(
        ...,
        description=(
            "AOI verdict. CALIBRATING is the expected first-rollout status per D-03 "
            "(SoCal/Mojave/Iberian = calibration data points 1/2/3). BLOCKER surfaces "
            "when all fallback attempts fail (D-11). SKIPPED marks untried fallbacks "
            "after an earlier attempt passed."
        ),
    )
    attempt_index: int = Field(
        default=0, description="0 for parent/leaf rows; 1..N for nested attempts."
    )
    reason: str | None = Field(
        default=None,
        description="Why this status — human-readable, populated on FAIL/SKIPPED/BLOCKER.",
    )
    attempts: list[AOIResult] = Field(
        default_factory=list,
        description="Nested fallback attempts; empty for leaf AOIs.",
    )
    stable_mask_pixels: int | None = Field(
        default=None,
        description=(
            "Count of True pixels in the stable_terrain.build_stable_mask output "
            "(sanity-check metric)."
        ),
    )
    product_quality: ProductQualityResultJson | None = Field(
        default=None,
        description=(
            "Self-consistency PQ measurements. Null on FAIL-before-PQ-computed or SKIPPED."
        ),
    )
    reference_agreement: ReferenceAgreementResultJson | None = Field(
        default=None,
        description=(
            "OPERA CSLC amplitude sanity. Null for Mojave per CONTEXT D-07."
        ),
    )
    error: str | None = Field(
        default=None, description="repr(exception) on FAIL; null otherwise."
    )
    traceback: str | None = Field(
        default=None, description="traceback.format_exc() on FAIL."
    )


AOIResult.model_rebuild()  # resolve forward-ref for self-referential 'attempts' list


class CSLCSelfConsistNAMCellMetrics(MetricsJson):
    """Phase 3 N.Am. CSLC self-consistency aggregate (CONTEXT D-06).

    matrix_writer detects this schema via presence of ``per_aoi`` key in raw JSON
    (cheap shape-discriminator, same pattern as _is_rtc_eu_shape).
    """

    pass_count: int = Field(
        ..., ge=0, description="Count of AOIs with status in {PASS, CALIBRATING}."
    )
    total: int = Field(..., ge=1, description="Total AOI count (2 for NAM: SoCal + Mojave).")
    cell_status: CSLCCellStatus = Field(
        ...,
        description=(
            "Whole-cell verdict. CALIBRATING = all AOIs CALIBRATING (expected first-rollout). "
            "MIXED = any AOI CALIBRATING + any BLOCKER/FAIL. BLOCKER = all AOIs BLOCKER. "
            "PASS/FAIL reserved for post-BINDING-promotion (v1.2+ per GATE-05)."
        ),
    )
    any_blocker: bool = Field(
        ...,
        description=(
            "True when any AOI has status='BLOCKER' (Mojave fallback exhaustion; D-11). "
            "Drives matrix_writer warning-glyph annotation."
        ),
    )
    product_quality_aggregate: dict[str, float | str] = Field(
        default_factory=dict,
        description=(
            "Worst-case across AOIs: worst_coherence_median_of_persistent (float), "
            "worst_residual_mm_yr (float), worst_aoi (str). Matrix cell consumes these."
        ),
    )
    reference_agreement_aggregate: dict[str, float | str] = Field(
        default_factory=dict,
        description=(
            "Worst-case across AOIs that ran amplitude sanity: worst_amp_r (float), "
            "worst_amp_rmse_db (float), worst_aoi (str). Mojave rows excluded (null RA)."
        ),
    )
    per_aoi: list[AOIResult] = Field(
        default_factory=list,
        description=(
            "Per-AOI drilldown; order matches AOIS declaration in "
            "run_eval_cslc_selfconsist_nam.py."
        ),
    )


class CSLCSelfConsistEUCellMetrics(CSLCSelfConsistNAMCellMetrics):
    """Phase 3 EU CSLC self-consistency aggregate (CONTEXT D-06).

    Schema identical to NAM but distinguished for type-dispatch in matrix_writer.
    Iberian is the only scheduled AOI (calibration data point 3); EU-specific
    ``egms_l2a_stable_ps_residual_mm_yr`` lives inside
    per_aoi[].product_quality.measurements as an additional measurement — not a
    new top-level field — to keep the matrix cell-rendering code symmetric with NAM.
    """

    pass  # inherit-only; class exists so matrix_writer.render dispatch is explicit.


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
            "Pearson r between per-IFG ramp_magnitude_rad and "
            "ifg_coherence_mean. Positive correlation (r > 0.5) suggests "
            "PHASS-class ramps (low-coherence IFGs have larger ramps); "
            "near-zero suggests orbit."
        ),
    )
    n_ifgs: int = Field(
        ...,
        ge=0,
        description="Number of finite IFGs included in the aggregate.",
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
            "D-Claude's-Discretion. 'tropospheric' is reserved for "
            "diagnostic (c) (ERA5 toggle, deferred per D-09); the auto-rule "
            "never returns it."
        ),
    )
    attribution_note: str = Field(
        default="",
        description=(
            "Free-form note written by the eval script. Default: "
            "'Automated; human review pending in CONCLUSIONS'. The "
            "canonical labelling lives in CONCLUSIONS prose; this field is "
            "the audit trail."
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
    are overridden:
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


# --- Phase 5 DIST cell metrics (CONTEXT D-25 + scope amendment 2026-04-25) ---
# Phase 5 ships:
#   - DistEUCellMetrics + DistEUEventMetrics (full schema for the 3-event EU cell;
#     Aveiro chained_run differentiator embedded as ChainedRunResult)
#   - DistNamCellMetrics (MINIMAL deferred-cell shape only; full schema with
#     ConfigDriftReport + reference_agreement.metrics: dict[str, MetricWithCI] +
#     bootstrap_config defers to v1.2 once OPERA_L3_DIST-ALERT-S1_V1 publishes
#     operationally)
#   - 5 helper types (MetricWithCI, BootstrapConfig, EFFISQueryMeta,
#     RasterisationDiagnostic, ChainedRunResult)
# ZERO edits to existing types per Phase 1 D-09 immutability + Phase 4 D-11
# schema-extension lock-in.

DistEUEventID = Literal["aveiro", "evros", "spain_culebra"]
ChainedRunStatus = Literal[
    "structurally_valid", "partial_output", "dist_s1_hang", "crashed", "skipped"
]
CMRProbeOutcome = Literal["operational_found", "operational_not_found", "probe_failed"]
ReferenceSource = Literal["operational_v1", "v0.1_cloudfront", "none"]
DistEUCellStatus = Literal["PASS", "FAIL", "MIXED", "BLOCKER"]
DistNamCellStatus = Literal["PASS", "FAIL", "DEFERRED"]


class MetricWithCI(BaseModel):
    """One reference-agreement metric with point estimate + bootstrap CI bounds (D-07)."""

    model_config = ConfigDict(extra="forbid")

    point: float = Field(..., description="Point estimate (e.g. F1 = 0.823).")
    ci_lower: float = Field(..., description="Lower bound at ci_level (default 2.5 percentile).")
    ci_upper: float = Field(..., description="Upper bound at ci_level (default 97.5 percentile).")


class BootstrapConfig(BaseModel):
    """Bootstrap configuration sub-block for reproducibility audit (D-09).

    Defaults mirror ``subsideo.validation.bootstrap.DEFAULT_*`` constants.
    Switching defaults requires a visible PR diff in BOTH bootstrap.py
    constants AND any eval-script overrides.
    """

    model_config = ConfigDict(extra="forbid")

    block_size_m: int = Field(default=1000, description="Block edge length in metres.")
    n_bootstrap: int = Field(default=500, ge=1, description="Number of bootstrap resamples.")
    ci_level: float = Field(default=0.95, gt=0, lt=1, description="Confidence interval level.")
    n_blocks_kept: int = Field(..., ge=0, description="Full blocks resampled.")
    n_blocks_dropped: int = Field(
        ...,
        ge=0,
        description="Partial blocks dropped at tile edges (D-08 transparency).",
    )
    rng_seed: int = Field(default=0, description="PCG64 seed (np.random.default_rng).")


class EFFISQueryMeta(BaseModel):
    """Per-event EFFIS WFS query metadata for meta.json (D-19 reproducibility audit)."""

    model_config = ConfigDict(extra="forbid")

    wfs_endpoint: str = Field(..., description="WFS GetFeature endpoint URL.")
    layer_name: str = Field(..., description="WFS typename (e.g. 'ms:modis.ba.poly').")
    filter_string: str = Field(..., description="OGC Filter XML serialised at fetch time.")
    response_feature_count: int = Field(..., ge=0, description="Number of features returned.")
    fetched_at: str = Field(..., description="ISO-8601 UTC fetch timestamp.")


class RasterisationDiagnostic(BaseModel):
    """all_touched=True vs False F1 delta for EFFIS rasterisation transparency (D-17).

    Per PITFALLS P4.4: all_touched=True boundary-only labelling can inflate F1 by
    2-4 percentage points vs all_touched=False (centre-in-polygon only). The gate
    value is all_touched=False; the delta is narrative-only.
    """

    model_config = ConfigDict(extra="forbid")

    all_touched_false_f1: float = Field(..., description="Primary F1 (gate value).")
    all_touched_true_f1: float = Field(..., description="Diagnostic F1 (narrative-only).")
    delta_f1: float = Field(
        ...,
        description="all_touched_true - all_touched_false. Expected ~+0.02..+0.04.",
    )


class ChainedRunResult(BaseModel):
    """Aveiro chained ``prior_dist_s1_product`` retry result (D-13, D-14, DIST-07).

    Pass criterion = ``status == 'structurally_valid'``. Other status values
    are non-failures of the EVENT (Aveiro can still PASS on F1 against EFFIS),
    they only fail the DIFFERENTIATOR sub-result.
    """

    model_config = ConfigDict(extra="forbid")

    status: ChainedRunStatus = Field(..., description="See ChainedRunStatus Literal.")
    output_dir: str | None = Field(
        default=None,
        description="Path to chained product dir; None on skip/crash.",
    )
    n_layers_present: int | None = Field(
        default=None,
        ge=0,
        le=10,
        description="10 expected per OPERA spec (TIF_LAYERS).",
    )
    dist_status_nonempty: bool | None = Field(
        default=None,
        description="DIST-STATUS layer has >=1 non-zero pixel.",
    )
    error: str | None = Field(default=None, description="repr(exception) on crashed.")
    traceback: str | None = Field(
        default=None,
        description="traceback.format_exc() on crashed.",
    )


class DistEUEventMetrics(BaseModel):
    """Per-event sub-result row inside DistEUCellMetrics.per_event (D-10).

    Structure mirrors RTCEUCellMetrics.per_burst (Phase 2 D-09). One entry per
    EVENT (aveiro / evros / spain_culebra; substituted from romania per
    RESEARCH Probe 4 ADR -- EFFIS is fire-only and does not cover clear-cuts).
    """

    model_config = ConfigDict(extra="forbid")

    event_id: DistEUEventID = Field(..., description="aveiro / evros / spain_culebra.")
    status: Literal["PASS", "FAIL"] = Field(
        ...,
        description=(
            "Per-event verdict from F1 + accuracy + DIST-05 precision/recall "
            "criteria (precision > 0.70 AND recall > 0.50; enforced inline in "
            "eval script per Phase 1 D-09 -- NOT new criteria.py entries)."
        ),
    )
    f1: MetricWithCI = Field(..., description="F1 with 95% block-bootstrap CI.")
    precision: MetricWithCI = Field(..., description="Precision with CI.")
    recall: MetricWithCI = Field(..., description="Recall with CI.")
    accuracy: MetricWithCI = Field(..., description="Overall accuracy with CI.")
    rasterisation_diagnostic: RasterisationDiagnostic = Field(
        ...,
        description="all_touched delta (D-17).",
    )
    bootstrap_config: BootstrapConfig = Field(
        ...,
        description="Bootstrap params for reproducibility (D-09).",
    )
    effis_query_meta: EFFISQueryMeta = Field(
        ...,
        description="EFFIS WFS query trace (D-19).",
    )
    chained_run: ChainedRunResult | None = Field(
        default=None,
        description="Aveiro-only differentiator (D-13/D-14); None for evros + spain_culebra.",
    )
    error: str | None = Field(
        default=None,
        description="repr(exception) on event-level failure (per-event try/except isolation, Phase 2 D-06).",
    )
    traceback: str | None = Field(
        default=None,
        description="traceback.format_exc() on event-level failure.",
    )


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


class DistNamCellMetrics(MetricsJson):
    """Phase 5 N.Am. DIST deferred-cell shape (scope amendment 2026-04-25).

    MINIMAL schema for the deferred ``dist:nam`` cell. v1.2 will EXTEND this
    class with ``config_drift: ConfigDriftReport``, ``bootstrap_config:
    BootstrapConfig``, and ``reference_agreement.metrics: dict[str,
    MetricWithCI]`` once OPERA_L3_DIST-ALERT-S1_V1 publishes operationally
    in CMR. The CMR auto-supersede probe in run_eval_dist.py Stage 0
    (DIST-04) handles the v1.2 transition without re-planning.

    matrix_writer detects this schema via cell_status == 'DEFERRED' AND
    presence of reference_source key (Plan 05-05 ``_is_dist_nam_shape``).
    """

    cell_status: DistNamCellStatus = Field(
        default="DEFERRED",
        description=(
            "Phase 5 default = 'DEFERRED' until OPERA operational publishes. "
            "v1.2 will override to PASS/FAIL once F1+CI is computable."
        ),
    )
    reference_source: ReferenceSource = Field(
        default="none",
        description=(
            "Stage 0 CMR probe outcome routed: 'operational_v1' on hit (v1.2 path), "
            "'v0.1_cloudfront' (deprecated; legacy literal preserved for forward "
            "compat), 'none' on deferral (Phase 5 default)."
        ),
    )
    cmr_probe_outcome: CMRProbeOutcome = Field(
        ...,
        description=(
            "CMR probe Stage 0 disposition: 'operational_found' / "
            "'operational_not_found' / 'probe_failed'. Echoed inline in "
            "matrix cell render (Plan 05-05)."
        ),
    )
    reference_granule_id: str | None = Field(
        default=None,
        description="UMM-G granule ID on operational_found; None on miss.",
    )
    deferred_reason: str | None = Field(
        default=None,
        description=(
            "Free-form reason string written by run_eval_dist.py on deferred path. "
            "v1.2 unsets this field when supersede happens."
        ),
    )
