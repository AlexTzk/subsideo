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
    pass_criteria: dict[str, bool] = field(default_factory=dict)



@dataclass
class DISPConfig:
    """Configuration for a DISP-S1 displacement time-series run."""

    cslc_file_list: list[Path]
    output_dir: Path
    cdsapirc_path: Path = field(default_factory=lambda: Path.home() / ".cdsapirc")
    coherence_mask_threshold: float = 0.3
    ramp_threshold: float = 1.0
    product_version: str = "0.1.0"


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
class DISTConfig:
    """Configuration for a DIST-S1 surface disturbance run."""

    mgrs_tile_id: str
    post_date: str
    track_number: int
    output_dir: Path


@dataclass
class DISTResult:
    """Output from a DIST-S1 processing run."""

    output_paths: list[Path]
    output_dir: Path
    valid: bool
    validation_errors: list[str] = field(default_factory=list)
