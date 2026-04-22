"""RTC-S1 product validation against OPERA N.Am. reference."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from loguru import logger
from rasterio.warp import Resampling, reproject

from subsideo.products.types import RTCValidationResult
from subsideo.validation.metrics import bias, rmse, spatial_correlation, ssim
from subsideo.validation.results import ProductQualityResult, ReferenceAgreementResult


def compare_rtc(product_path: Path, reference_path: Path) -> RTCValidationResult:
    """Compare RTC-S1 product against OPERA N.Am. reference in dB domain.

    Per D-08/D-09: loads both products, reprojects subsideo output to match
    reference grid (Pitfall 3), converts to dB (Pitfall 5: RMSE 0.5 dB
    threshold requires dB-domain comparison), and computes all metrics.

    Args:
        product_path: Path to subsideo RTC COG GeoTIFF.
        reference_path: Path to OPERA N.Am. RTC GeoTIFF from ASF DAAC.

    Returns:
        RTCValidationResult with metrics and pass/fail criteria.
    """
    # 1. Load reference grid (this is the target grid)
    with rasterio.open(reference_path) as ref:
        ref_data = ref.read(1).astype(np.float64)
        ref_transform = ref.transform
        ref_crs = ref.crs

    # 2. Reproject subsideo product to match reference grid
    # Per Pitfall 3: always reproject product to reference, not vice versa
    prod_aligned = np.empty_like(ref_data)
    with rasterio.open(product_path) as prod:
        reproject(
            source=rasterio.band(prod, 1),
            destination=prod_aligned,
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            resampling=Resampling.bilinear,
        )

    # 3. Convert to dB domain (RTC is in linear power gamma0)
    # Per Pitfall 5: validation RMSE of 0.5 dB requires dB comparison
    ref_db = 10.0 * np.log10(np.where(ref_data > 0, ref_data, np.nan))
    prod_db = 10.0 * np.log10(np.where(prod_aligned > 0, prod_aligned, np.nan))

    # 4. Compute metrics using shared functions
    rmse_val = rmse(prod_db, ref_db)
    corr_val = spatial_correlation(prod_db, ref_db)
    bias_val = bias(prod_db, ref_db)
    ssim_val = ssim(prod_db, ref_db, data_range=30.0)  # ~30 dB typical SAR range

    logger.info(
        f"RTC validation: RMSE={rmse_val:.3f} dB, r={corr_val:.4f}, "
        f"bias={bias_val:.3f} dB, SSIM={ssim_val:.3f}"
    )

    return RTCValidationResult(
        product_quality=ProductQualityResult(
            measurements={"ssim": ssim_val},
            criterion_ids=[],
        ),
        reference_agreement=ReferenceAgreementResult(
            measurements={
                "rmse_db": rmse_val,
                "correlation": corr_val,
                "bias_db": bias_val,
            },
            criterion_ids=["rtc.rmse_db_max", "rtc.correlation_min"],
        ),
    )
