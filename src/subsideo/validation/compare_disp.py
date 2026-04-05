"""DISP-S1 product validation against EGMS EU Ortho reference.

Downloads EGMS Ortho products via EGMStoolkit, then compares vertical velocity
component: projects subsideo LOS velocity to vertical using incidence angle,
then compares against EGMS Ortho vertical displacement field.
Grid alignment reprojects subsideo output to match the EGMS reference grid.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from loguru import logger
from rasterio.warp import Resampling, reproject

from subsideo.products.types import DISPValidationResult
from subsideo.validation.metrics import bias, spatial_correlation


def fetch_egms_ortho(
    bbox: tuple[float, float, float, float],
    output_dir: Path,
) -> Path:
    """Download EGMS Ortho product for a bounding box using EGMStoolkit.

    Args:
        bbox: Bounding box as (west, south, east, north) in WGS84 degrees.
        output_dir: Directory to save downloaded EGMS Ortho GeoTIFF(s).

    Returns:
        Path to the downloaded EGMS Ortho GeoTIFF.

    Raises:
        ImportError: If EGMStoolkit is not installed.
        FileNotFoundError: If no GeoTIFF files found after download.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        import EGMStoolkit  # noqa: F811
    except ImportError as err:
        raise ImportError(
            "EGMStoolkit is not installed. Install via pip: pip install EGMStoolkit"
        ) from err

    # EGMStoolkit download for Ortho-level vertical displacement product
    west, south, east, north = bbox
    EGMStoolkit.download(
        bbox=[west, south, east, north],
        product_level="Ortho",
        output_dir=str(output_dir),
    )

    # Find downloaded GeoTIFF(s)
    tif_files = sorted(output_dir.glob("*.tif"))
    if not tif_files:
        raise FileNotFoundError(
            f"No GeoTIFF files found in {output_dir} after EGMS download"
        )

    result_path = tif_files[0]
    logger.info(f"Downloaded EGMS Ortho product for bbox {bbox} to {output_dir}")
    return result_path


def _los_to_vertical(
    los_velocity: np.ndarray,
    incidence_angle: np.ndarray | float,
) -> np.ndarray:
    """Project LOS velocity to vertical component.

    Computes v_vert = v_los / cos(theta) where theta is incidence angle
    in degrees. Handles division by zero by returning NaN.

    Args:
        los_velocity: Line-of-sight velocity array (mm/yr).
        incidence_angle: Incidence angle in degrees (scalar or per-pixel array).

    Returns:
        Vertical velocity array (mm/yr).
    """
    theta_rad = np.radians(incidence_angle)
    cos_theta = np.cos(theta_rad)

    # Avoid division by zero
    with np.errstate(divide="ignore", invalid="ignore"):
        vert = np.where(cos_theta != 0.0, los_velocity / cos_theta, np.nan)

    return vert


def compare_disp(
    product_path: Path,
    egms_ortho_path: Path,
    incidence_angle_path: Path | None = None,
    mean_incidence_deg: float = 33.0,
) -> DISPValidationResult:
    """Compare DISP-S1 velocity product against EGMS Ortho reference.

    Reprojects subsideo output to match the EGMS reference grid (never
    vice versa), projects LOS to vertical using incidence angle, and
    computes correlation and bias metrics over the intersection of valid
    pixels.

    Args:
        product_path: Path to subsideo DISP velocity GeoTIFF (mm/yr, LOS).
        egms_ortho_path: Path to EGMS Ortho vertical displacement GeoTIFF.
        incidence_angle_path: Optional path to per-pixel incidence angle
            GeoTIFF (degrees). If None, uses mean_incidence_deg.
        mean_incidence_deg: Fallback mean incidence angle in degrees.
            Default 33.0 (typical Sentinel-1 IW).

    Returns:
        DISPValidationResult with correlation, bias, and pass criteria.
    """
    # 1. Load EGMS reference grid (target grid -- per Pitfall 4)
    with rasterio.open(egms_ortho_path) as ref:
        egms_data = ref.read(1).astype(np.float64)
        egms_transform = ref.transform
        egms_crs = ref.crs

    # 2. Reproject subsideo product to match EGMS grid
    prod_aligned = np.empty_like(egms_data)
    with rasterio.open(product_path) as prod:
        reproject(
            source=rasterio.band(prod, 1),
            destination=prod_aligned,
            dst_transform=egms_transform,
            dst_crs=egms_crs,
            resampling=Resampling.bilinear,
        )

    # 3. Load or construct incidence angle
    if incidence_angle_path is not None:
        inc_aligned = np.empty_like(egms_data)
        with rasterio.open(incidence_angle_path) as inc:
            reproject(
                source=rasterio.band(inc, 1),
                destination=inc_aligned,
                dst_transform=egms_transform,
                dst_crs=egms_crs,
                resampling=Resampling.bilinear,
            )
        incidence_angle: np.ndarray | float = inc_aligned
    else:
        incidence_angle = mean_incidence_deg

    # 4. Project LOS to vertical
    vert_velocity = _los_to_vertical(prod_aligned, incidence_angle)

    # 5. Mask to intersection: metrics only over valid pixels in both arrays
    valid = np.isfinite(vert_velocity) & np.isfinite(egms_data)
    vert_masked = np.where(valid, vert_velocity, np.nan)
    egms_masked = np.where(valid, egms_data, np.nan)

    # 6. Compute metrics using shared functions
    corr = spatial_correlation(vert_masked, egms_masked)
    bias_val = bias(vert_masked, egms_masked)

    logger.info(f"DISP validation: r={corr:.4f}, bias={bias_val:.2f} mm/yr")

    return DISPValidationResult(
        correlation=corr,
        bias_mm_yr=bias_val,
        pass_criteria={
            "correlation_gt_0.92": corr > 0.92,
            "bias_lt_3mm_yr": abs(bias_val) < 3.0,
        },
    )
