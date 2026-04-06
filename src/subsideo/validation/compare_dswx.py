"""DSWx-S2 product validation against JRC Global Surface Water."""
from __future__ import annotations

import urllib.request
from pathlib import Path

import numpy as np
from loguru import logger

from subsideo.products.types import DSWxValidationResult
from subsideo.validation.metrics import (
    f1_score,
    overall_accuracy,
    precision_score,
    recall_score,
)

JRC_BASE_URL = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata"
    "/GSWE/MonthlyHistory/LATEST/tiles"
)
# JRC grid: 30m resolution, 10-degree tiles = 40000 pixels
JRC_TILE_SIZE_PIXELS = 40000
JRC_TILE_SIZE_DEGREES = 10.0
# Origin: upper-left at (-180, 80) (global coverage 80N to 60S)
JRC_ORIGIN_LON = -180.0
JRC_ORIGIN_LAT = 80.0


def _jrc_tile_url(year: int, month: int, tile_x: int, tile_y: int) -> str:
    """Build JRC Monthly History tile URL.

    Args:
        year: Year of the monthly history product.
        month: Month (1-12).
        tile_x: Tile x-index (0-based, from left).
        tile_y: Tile y-index (0-based, from top).

    Returns:
        Full URL to the JRC GeoTIFF tile.
    """
    pixel_x = tile_x * JRC_TILE_SIZE_PIXELS
    pixel_y = tile_y * JRC_TILE_SIZE_PIXELS
    return f"{JRC_BASE_URL}/{year}/{year}_{month:02d}/{pixel_x:010d}-{pixel_y:010d}.tif"


def _lonlat_to_jrc_tile(lon: float, lat: float) -> tuple[int, int]:
    """Convert geographic coordinate to JRC tile indices.

    Args:
        lon: Longitude in degrees.
        lat: Latitude in degrees.

    Returns:
        Tuple of (tile_x, tile_y) indices.
    """
    tile_x = int((lon - JRC_ORIGIN_LON) / JRC_TILE_SIZE_DEGREES)
    tile_y = int((JRC_ORIGIN_LAT - lat) / JRC_TILE_SIZE_DEGREES)
    return tile_x, tile_y


def _tiles_for_bounds(
    west: float, south: float, east: float, north: float
) -> list[tuple[int, int]]:
    """Return all JRC tile indices covering a geographic bounding box.

    Args:
        west: Western longitude bound.
        south: Southern latitude bound.
        east: Eastern longitude bound.
        north: Northern latitude bound.

    Returns:
        List of (tile_x, tile_y) tuples covering the bounding box.
    """
    tx_min, ty_max = _lonlat_to_jrc_tile(west, south)
    tx_max, ty_min = _lonlat_to_jrc_tile(east, north)
    tiles = []
    for tx in range(tx_min, tx_max + 1):
        for ty in range(ty_min, ty_max + 1):
            tiles.append((tx, ty))
    return tiles


def _fetch_jrc_tile(url: str, cache_dir: Path) -> Path | None:
    """Download a JRC tile to cache_dir if not already cached.

    Args:
        url: Full URL to the JRC GeoTIFF tile.
        cache_dir: Local directory for caching tiles.

    Returns:
        Path to the cached tile, or None if the tile does not exist (404).
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    filename = url.rsplit("/", maxsplit=1)[-1]
    local_path = cache_dir / filename
    if local_path.exists():
        logger.debug(f"JRC tile cached: {local_path}")
        return local_path
    try:
        logger.info(f"Downloading JRC tile: {url}")
        urllib.request.urlretrieve(url, local_path)  # noqa: S310
        return local_path
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            logger.warning(f"JRC tile not found (ocean?): {url}")
            return None
        raise


def _binarize_dswx(water_class: np.ndarray) -> np.ndarray:
    """Binarize DSWx water classification to water/non-water.

    Per D-05: DSWx water pixels = high + moderate confidence (classes 1, 2).

    Args:
        water_class: Array of DSWx classification values.

    Returns:
        Float32 array: 1.0 = water, 0.0 = not water, NaN = nodata.
    """
    result = np.zeros(water_class.shape, dtype=np.float32)
    result[np.isin(water_class, [1, 2])] = 1.0
    result[water_class == 255] = np.nan
    return result


def _binarize_jrc(jrc: np.ndarray) -> np.ndarray:
    """Binarize JRC Monthly History to water/non-water.

    Per Pitfall 5: JRC encoding is 0=nodata, 1=not water, 2=water.

    Args:
        jrc: Array of JRC classification values.

    Returns:
        Float32 array: 1.0 = water, 0.0 = not water, NaN = nodata.
    """
    result = np.full(jrc.shape, np.nan, dtype=np.float32)
    result[jrc == 1] = 0.0
    result[jrc == 2] = 1.0
    return result


def compare_dswx(
    product_path: Path,
    year: int,
    month: int,
    cache_dir: Path | None = None,
) -> DSWxValidationResult:
    """Compare DSWx-S2 product against JRC Global Surface Water.

    Downloads JRC Monthly History tiles matching the product extent and
    temporal window, binarizes both to water/non-water, and computes
    classification metrics.

    Args:
        product_path: Path to DSWx COG GeoTIFF output.
        year: Year of the JRC monthly history to compare against.
        month: Month (1-12) of the JRC monthly history.
        cache_dir: Optional cache directory for JRC tiles.
            Defaults to ~/.subsideo/jrc_cache.

    Returns:
        DSWxValidationResult with F1, precision, recall, accuracy, and
        pass/fail criteria.
    """
    import rasterio
    from rasterio.merge import merge
    from rasterio.warp import Resampling, calculate_default_transform, reproject, transform_bounds

    if cache_dir is None:
        cache_dir = Path.home() / ".subsideo" / "jrc_cache"

    # 1. Open product and get bounds in EPSG:4326
    with rasterio.open(product_path) as src:
        prod_data = src.read(1)
        prod_profile = src.profile.copy()
        bounds_4326 = transform_bounds(src.crs, "EPSG:4326", *src.bounds)

    west, south, east, north = bounds_4326

    # 2. Determine JRC tiles needed
    tiles = _tiles_for_bounds(west, south, east, north)
    logger.info(f"JRC tiles needed: {len(tiles)} for bounds {bounds_4326}")

    # 3. Download JRC tiles
    tile_paths = []
    for tx, ty in tiles:
        url = _jrc_tile_url(year, month, tx, ty)
        tile_path = _fetch_jrc_tile(url, cache_dir)
        if tile_path is not None:
            tile_paths.append(tile_path)

    if not tile_paths:
        logger.error("No JRC tiles available for the product extent")
        return DSWxValidationResult(
            f1=0.0, precision=0.0, recall=0.0, overall_accuracy=0.0,
            pass_criteria={"f1_gt_0.90": False},
        )

    # 4. Mosaic JRC tiles
    jrc_datasets = [rasterio.open(p) for p in tile_paths]
    try:
        jrc_mosaic, jrc_transform = merge(jrc_datasets)
    finally:
        for ds in jrc_datasets:
            ds.close()
    jrc_mosaic = jrc_mosaic[0]  # Single band

    # 5. Reproject product to JRC grid (WGS84 30m) using nearest neighbour
    dst_crs = "EPSG:4326"
    dst_transform, dst_width, dst_height = calculate_default_transform(
        prod_profile["crs"], dst_crs,
        prod_profile["width"], prod_profile["height"],
        *rasterio.transform.array_bounds(
            prod_profile["height"], prod_profile["width"], prod_profile["transform"],
        ),
    )
    prod_reproj = np.empty((dst_height, dst_width), dtype=prod_data.dtype)
    reproject(
        source=prod_data,
        destination=prod_reproj,
        src_transform=prod_profile["transform"],
        src_crs=prod_profile["crs"],
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        resampling=Resampling.nearest,
    )

    # 6. Crop JRC mosaic to product extent (simplified: use common extent)
    # For now, trim both arrays to the minimum common shape
    min_h = min(prod_reproj.shape[0], jrc_mosaic.shape[0])
    min_w = min(prod_reproj.shape[1], jrc_mosaic.shape[1])
    prod_crop = prod_reproj[:min_h, :min_w]
    jrc_crop = jrc_mosaic[:min_h, :min_w]

    # 7. Binarize both arrays
    prod_bin = _binarize_dswx(prod_crop)
    jrc_bin = _binarize_jrc(jrc_crop)

    # 8. Mask to valid pixels (both non-NaN)
    valid = np.isfinite(prod_bin) & np.isfinite(jrc_bin)
    pred = prod_bin[valid].astype(np.int32)
    ref = jrc_bin[valid].astype(np.int32)

    if pred.size == 0:
        logger.warning("No valid overlapping pixels between DSWx and JRC")
        return DSWxValidationResult(
            f1=0.0, precision=0.0, recall=0.0, overall_accuracy=0.0,
            pass_criteria={"f1_gt_0.90": False},
        )

    # 9. Compute metrics
    f1 = f1_score(pred, ref)
    prec = precision_score(pred, ref)
    rec = recall_score(pred, ref)
    acc = overall_accuracy(pred, ref)

    logger.info(
        f"DSWx validation: F1={f1:.4f}, precision={prec:.4f}, "
        f"recall={rec:.4f}, OA={acc:.4f}"
    )

    return DSWxValidationResult(
        f1=f1,
        precision=prec,
        recall=rec,
        overall_accuracy=acc,
        pass_criteria={"f1_gt_0.90": f1 > 0.90},
    )
