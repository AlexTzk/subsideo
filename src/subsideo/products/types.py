"""Product pipeline dataclasses for subsideo."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RTCConfig:
    """Configuration for an RTC-S1 processing run."""

    safe_file_path: list[Path]
    orbit_file_path: Path
    dem_file: Path
    output_dir: Path
    burst_id: list[str] | None = None
    product_version: str = "0.1.0"


@dataclass
class RTCResult:
    """Result of an RTC-S1 processing run."""

    output_paths: list[Path]
    runconfig_path: Path
    burst_ids: list[str]
    valid: bool
    validation_errors: list[str] = field(default_factory=list)


@dataclass
class CSLCConfig:
    """Configuration for a CSLC-S1 processing run."""

    safe_file_paths: list[Path]
    orbit_file_path: Path
    dem_file: Path
    burst_id: list[str] | None
    output_dir: Path
    tec_file: Path | None = None
    product_version: str = "0.1.0"


@dataclass
class CSLCResult:
    """Result of a CSLC-S1 processing run."""

    output_paths: list[Path]
    runconfig_path: Path
    burst_ids: list[str]
    valid: bool
    validation_errors: list[str] = field(default_factory=list)
