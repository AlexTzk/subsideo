"""Pipeline configuration, result, and validation result types.

Dataclasses (not Pydantic) -- these are plain result containers consumed
by pipeline orchestrators and validation comparison modules.

ValidationResult classes (RTC/CSLC/DISP/DIST/DSWx) are nested composites
per D-06 / GATE-02: each exposes `product_quality` and `reference_agreement`
sub-results. There is no top-level .passed bool -- call
`subsideo.validation.results.evaluate(...)` at read time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from subsideo.validation.results import ProductQualityResult, ReferenceAgreementResult


@dataclass
class RTCConfig:
    """Configuration for a single RTC-S1 processing run."""

    safe_file_paths: list[Path]
    orbit_file_path: Path
    dem_file: Path
    burst_id: list[str]
    output_dir: Path
    product_version: str = "0.1.0"
    output_posting_m: float = 30.0


@dataclass
class CSLCConfig:
    """Configuration for a single CSLC-S1 processing run."""

    safe_file_paths: list[Path]
    orbit_file_path: Path
    dem_file: Path
    burst_id: list[str] | None
    output_dir: Path
    tec_file: Path | None = None
    burst_database_file: Path | None = None
    product_version: str = "0.1.0"


@dataclass
class RTCResult:
    """Output from an RTC-S1 processing run."""

    output_paths: list[Path]
    runconfig_path: Path
    burst_ids: list[str]
    valid: bool
    validation_errors: list[str] = field(default_factory=list)


@dataclass
class CSLCResult:
    """Output from a CSLC-S1 processing run."""

    output_paths: list[Path]
    runconfig_path: Path
    burst_ids: list[str]
    valid: bool
    validation_errors: list[str] = field(default_factory=list)


@dataclass
class RTCValidationResult:
    """Validation metrics comparing RTC output against reference.

    Nested composite (D-06 / GATE-02): product_quality and reference_agreement
    are distinct. No top-level .passed bool -- call
    subsideo.validation.results.evaluate(...) at read time.
    """

    product_quality: ProductQualityResult
    reference_agreement: ReferenceAgreementResult


@dataclass
class CSLCValidationResult:
    """Validation metrics comparing CSLC output against reference.

    Nested composite: product_quality carries self-consistency (Phase 3);
    reference_agreement carries amplitude r / RMSE (v1.0 BINDING).
    """

    product_quality: ProductQualityResult
    reference_agreement: ReferenceAgreementResult


@dataclass
class DISPResult:
    """Output from a DISP-S1 processing run."""

    velocity_path: Path | None
    timeseries_paths: list[Path]
    output_dir: Path
    valid: bool
    qc_warnings: list[str] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)


@dataclass
class DISPValidationResult:
    """Validation metrics comparing DISP output against EGMS / OPERA DISP.

    Nested composite: product_quality carries DISP self-consistency
    (Phase 4); reference_agreement carries correlation / bias vs reference
    after prepare_for_reference() multilook.
    """

    product_quality: ProductQualityResult
    reference_agreement: ReferenceAgreementResult


@dataclass
class DISTResult:
    """Output from a DIST-S1 processing run."""

    output_paths: list[Path]
    output_dir: Path
    valid: bool
    validation_errors: list[str] = field(default_factory=list)


@dataclass
class DISTValidationResult:
    """Validation metrics comparing DIST-S1 output against OPERA DIST-S1 reference.

    Nested composite: product_quality is currently empty (DIST has no
    product-quality gate in v1.1); reference_agreement carries
    F1 / precision / recall / accuracy / n_valid_pixels.
    """

    product_quality: ProductQualityResult
    reference_agreement: ReferenceAgreementResult


@dataclass
class DSWxConfig:
    """Configuration for a DSWx-S2 surface water extent run."""

    s2_band_paths: dict[str, Path]  # keys: "B02","B03","B04","B08","B11","B12"
    scl_path: Path
    output_dir: Path
    output_epsg: int | None = None
    output_posting_m: float = 30.0
    product_version: str = "0.1.0"


@dataclass
class DSWxResult:
    """Output from a DSWx-S2 processing run."""

    output_path: Path | None
    valid: bool
    validation_errors: list[str] = field(default_factory=list)


@dataclass
class DSWxValidationResult:
    """Validation metrics comparing DSWx output against JRC reference.

    Nested composite: product_quality is currently empty; reference_agreement
    carries F1 / precision / recall / accuracy.
    """

    product_quality: ProductQualityResult
    reference_agreement: ReferenceAgreementResult
