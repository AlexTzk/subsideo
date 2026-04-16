"""Pipeline configuration, result, and validation result types.

Dataclasses (not Pydantic) -- these are plain result containers consumed
by pipeline orchestrators and validation comparison modules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


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
    """Validation metrics comparing RTC output against reference."""

    rmse_db: float
    correlation: float
    bias_db: float
    ssim_value: float
    pass_criteria: dict[str, bool] = field(default_factory=dict)


@dataclass
class CSLCValidationResult:
    """Validation metrics comparing CSLC output against reference."""

    phase_rms_rad: float
    coherence: float
    amplitude_correlation: float = 0.0
    amplitude_rmse_db: float = float("inf")
    pass_criteria: dict[str, bool] = field(default_factory=dict)



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
    """Validation metrics comparing DISP output against EGMS reference."""

    correlation: float
    bias_mm_yr: float
    pass_criteria: dict[str, bool] = field(default_factory=dict)


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

    All fields are binary-classification metrics over the disturbed/
    not-disturbed label, computed on the intersection of valid pixels
    between the product and the reference after reprojection to a
    shared grid. ``pass_criteria`` is a dict of named threshold checks
    that the caller's harness can iterate to produce a pass/fail verdict.
    """

    f1: float
    precision: float
    recall: float
    overall_accuracy: float
    n_valid_pixels: int
    pass_criteria: dict[str, bool] = field(default_factory=dict)


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
    """Validation metrics comparing DSWx output against JRC reference."""

    f1: float
    precision: float
    recall: float
    overall_accuracy: float
    pass_criteria: dict[str, bool] = field(default_factory=dict)
