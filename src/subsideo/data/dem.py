"""GLO-30 Copernicus DEM download, stitching, and UTM warp via dem-stitcher."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from dem_stitcher import stitch_dem
from loguru import logger
from rasterio.crs import CRS
from rasterio.warp import Resampling, calculate_default_transform, reproject


def fetch_dem(
    bounds: list[float],
    output_epsg: int,
    output_dir: Path,
    output_res_m: float = 30.0,
) -> tuple[Path, dict]:
    """Download and stitch GLO-30 DEM tiles, then warp to UTM at 30m posting.

    Uses dem-stitcher with dem_name='glo_30' (CC-BY). Warping to UTM is MANDATORY
    before ISCE3 ingestion -- raw GLO-30 tiles have variable longitudinal spacing
    above 50N that causes malformed stitched DEMs (D-08).

    Args:
        bounds: [west, south, east, north] in WGS84 degrees.
        output_epsg: Target UTM EPSG code (e.g. 32632 for UTM 32N).
        output_dir: Directory to write output GeoTIFF.
        output_res_m: Output resolution in metres (default 30.0).

    Returns:
        Tuple of (path_to_dem_tif, rasterio_profile).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading GLO-30 DEM for bounds {bounds}")
    data, profile = stitch_dem(
        bounds,
        dem_name="glo_30",
        dst_ellipsoidal_height=True,  # WGS84 ellipsoidal height (not EGM)
        dst_area_or_point="Point",  # pixel-centre convention
    )

    # Warp to target UTM CRS at requested posting
    dst_crs = CRS.from_epsg(output_epsg)
    transform, width, height = calculate_default_transform(
        profile["crs"],
        dst_crs,
        profile["width"],
        profile["height"],
        *bounds,
        resolution=output_res_m,
    )

    out_profile = profile.copy()
    out_profile.update(
        crs=dst_crs,
        transform=transform,
        width=width,
        height=height,
        driver="GTiff",
        compress="lzw",
    )

    out_path = output_dir / f"glo30_utm{output_epsg}.tif"
    with rasterio.open(out_path, "w", **out_profile) as dst:
        reproject(
            source=data,
            destination=rasterio.band(dst, 1),
            src_transform=profile["transform"],
            src_crs=profile["crs"],
            dst_transform=transform,
            dst_crs=dst_crs,
            resampling=Resampling.bilinear,
        )

    logger.info(f"DEM written to {out_path}")
    return out_path, out_profile
