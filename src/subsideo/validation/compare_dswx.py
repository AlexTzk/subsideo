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
    # JRC filename convention is "{pixel_y}-{pixel_x}.tif" (y-offset first,
    # x-offset second). Verified empirically against a known-good tile:
    # 0000520000-0000000000.tif has bounds left=-180, top=-50 -> the first
    # number encodes distance from the origin latitude (80 N) downward.
    return f"{JRC_BASE_URL}/{year}/{year}_{month:02d}/{pixel_y:010d}-{pixel_x:010d}.tif"


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

    Water = classes 1, 2, and 3. Class 3 ("potential wetland") is only
    included because the DSWx pipeline runs a connected-component rescue
    pass (:func:`subsideo.products.dswx._rescue_connected_wetlands`) that
    demotes isolated class-3 blobs to class 0. After that pass, surviving
    class-3 pixels necessarily border open water and represent shoreline
    wetlands / mixed-pixel edges, which JRC Monthly History counts as
    surface water. Class 4 (low confidence) remains excluded.

    Args:
        water_class: Array of DSWx classification values.

    Returns:
        Float32 array: 1.0 = water, 0.0 = not water, NaN = nodata.
    """
    result = np.zeros(water_class.shape, dtype=np.float32)
    result[np.isin(water_class, [1, 2, 3])] = 1.0
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
    from rasterio.warp import Resampling, reproject, transform_bounds
    from rasterio.windows import Window, from_bounds as window_from_bounds

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

    # 4. Mosaic JRC tiles (EPSG:4326, ~30 m / 0.00025 deg)
    jrc_datasets = [rasterio.open(p) for p in tile_paths]
    try:
        jrc_mosaic, jrc_transform = merge(jrc_datasets)
        jrc_crs = jrc_datasets[0].crs
    finally:
        for ds in jrc_datasets:
            ds.close()
    jrc_mosaic = jrc_mosaic[0]  # Single band

    # 5. Window the JRC mosaic to the product bounds (in 4326). This yields
    # a georeferenced reference grid that shares one transform with the
    # reprojected product -- prerequisite for index-aligned comparison.
    prod_west, prod_south, prod_east, prod_north = bounds_4326
    jrc_h, jrc_w = jrc_mosaic.shape
    jrc_win = window_from_bounds(
        prod_west, prod_south, prod_east, prod_north, transform=jrc_transform,
    ).round_offsets().round_lengths()
    # Clip the window to the mosaic extent so we never slice out-of-bounds.
    row_off = max(0, int(jrc_win.row_off))
    col_off = max(0, int(jrc_win.col_off))
    row_end = min(jrc_h, int(jrc_win.row_off + jrc_win.height))
    col_end = min(jrc_w, int(jrc_win.col_off + jrc_win.width))
    if row_end <= row_off or col_end <= col_off:
        logger.error("Product bounds do not intersect JRC mosaic extent")
        return DSWxValidationResult(
            f1=0.0, precision=0.0, recall=0.0, overall_accuracy=0.0,
            pass_criteria={"f1_gt_0.90": False},
        )
    jrc_crop = jrc_mosaic[row_off:row_end, col_off:col_end]
    dst_transform = rasterio.windows.transform(
        Window(col_off, row_off, col_end - col_off, row_end - row_off),
        jrc_transform,
    )
    dst_height, dst_width = jrc_crop.shape
    logger.info(
        f"JRC window: {dst_width}x{dst_height} px "
        f"({col_off},{row_off}) -> ({col_end},{row_end})"
    )

    # 6. Reproject product onto the JRC-aligned window grid
    prod_crop = np.empty((dst_height, dst_width), dtype=prod_data.dtype)
    reproject(
        source=prod_data,
        destination=prod_crop,
        src_transform=prod_profile["transform"],
        src_crs=prod_profile["crs"],
        dst_transform=dst_transform,
        dst_crs=jrc_crs,
        resampling=Resampling.nearest,
    )

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
