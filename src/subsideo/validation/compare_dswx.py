"""DSWx-S2 product validation against JRC Global Surface Water."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from loguru import logger

from subsideo.products.types import DSWxValidationDiagnostics, DSWxValidationResult
from subsideo.validation.metrics import (
    f1_score,
    overall_accuracy,
    precision_score,
    recall_score,
)
from subsideo.validation.results import ProductQualityResult, ReferenceAgreementResult

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


def _compute_shoreline_buffer_mask(
    jrc_water_class: np.ndarray[tuple[int, ...], np.dtype[np.generic]],
    iterations: int = 1,
) -> np.ndarray[tuple[int, ...], np.dtype[np.bool_]]:
    """Compute 1-pixel buffer around JRC water/land class boundary.

    Per CONTEXT D-16: the shoreline buffer mask MUST be computed on the
    JRC reference grid (the source of the boundary), then reprojected
    alongside the JRC water/land array using Resampling.nearest. This
    avoids buffering the DSWx prediction's boundary (which we don't want
    -- we want JRC's boundary uniformly excluded from the F1 evaluation).

    Phase 6 D-16: applied uniformly in BOTH the grid search (Plan 06-06)
    AND final F1 reporting (Plan 06-05 + 06-07). Single source of truth
    for what counts as a fair F1.

    Parameters
    ----------
    jrc_water_class : np.ndarray
        Binary water mask on JRC grid (1=water, 0=non-water). nodata
        pixels (typically jrc class 0 or 255) should be masked out
        BEFORE this call so they don't contribute to the boundary.
    iterations : int, default=1
        Number of dilation iterations (each = 1 pixel buffer at JRC's
        30m posting). 1 matches CONTEXT D-16 "1-pixel buffer".

    Returns
    -------
    np.ndarray
        Boolean mask: True = shoreline buffer (EXCLUDE from F1);
        False = include in F1 evaluation.

    Notes
    -----
    Default 4-connectivity structuring element via the binary_dilation
    iterations parameter. The XOR-of-dilations approach catches the buffer
    ring without consuming pure-water or pure-non-water interior. Per
    PITFALLS P5.2: the buffer mitigates JRC commission (98-99%) /
    omission (74-99%) asymmetry at the shoreline.
    """
    from scipy.ndimage import binary_dilation  # lazy import (Phase 1 pattern)

    water = (jrc_water_class == 1).astype(np.uint8)
    non_water = (jrc_water_class == 0).astype(np.uint8)

    water_dilated = binary_dilation(water, iterations=iterations)
    non_water_dilated = binary_dilation(non_water, iterations=iterations)

    # Shoreline = pixels within 1px of BOTH water AND non-water classes.
    # Per RESEARCH lines 818-820: this XOR-of-dilations correctly handles
    # the asymmetric shoreline even when JRC has nodata interior gaps.
    shoreline_buffer: np.ndarray[tuple[int, ...], np.dtype[np.bool_]] = (
        water_dilated.astype(bool) & non_water_dilated.astype(bool)
    )

    return shoreline_buffer


def _fetch_jrc_tile(url: str, cache_dir: Path) -> Path | None:
    """Download a JRC tile to cache_dir if not already cached.

    Phase 6 D-25: refactored to consume harness.download_reference_with_retry
    (source='jrc') instead of bare urllib.request.urlretrieve. Per-source
    retry policy lives in harness.RETRY_POLICY['jrc'] (Plan 06-02). Preserves
    v1.0 None-on-404 semantics by catching ReferenceDownloadError when the
    underlying status was 404 (benign tile-out-of-coverage).

    Args:
        url: Full URL to the JRC GeoTIFF tile.
        cache_dir: Local directory for caching tiles.

    Returns:
        Path to the cached tile, or None if the tile does not exist (404).
    """
    from subsideo.validation.harness import (
        ReferenceDownloadError,
        download_reference_with_retry,
    )

    cache_dir.mkdir(parents=True, exist_ok=True)
    filename = url.rsplit("/", maxsplit=1)[-1]
    local_path = cache_dir / filename
    if local_path.exists():
        logger.debug(f"JRC tile cached: {local_path}")
        return local_path
    try:
        logger.info(f"Downloading JRC tile: {url}")
        return download_reference_with_retry(
            url=url,
            dest=local_path,
            source="jrc",
        )
    except ReferenceDownloadError as exc:
        # Phase 6 D-25 preserves v1.0 _fetch_jrc_tile semantics: 404 (tile-out-
        # of-coverage; benign for ocean tiles or pre-1984/post-2021 dates) is
        # propagated as None rather than raised. Other ReferenceDownloadErrors
        # (e.g. all 5 retries exhausted, 403 auth) re-raise.
        if getattr(exc, "status", None) == 404 or "404" in str(exc):
            logger.warning(f"JRC tile not in coverage (404): {url}")
            return None
        raise


def _fetch_jrc_tile_for_bbox(
    year: int,
    month: int,
    lonlat_bbox: tuple[float, float, float, float],
    cache_dir: Path,
) -> Path | None:
    """Download and stitch all JRC tiles covering ``lonlat_bbox`` for the given year+month.

    ``lonlat_bbox`` is ``(west, south, east, north)`` in WGS84 degrees.
    Returns a single merged GeoTIFF (virtual merge via rasterio in-memory), or
    ``None`` if no tiles cover the bbox.

    Plan 06-06 B4 fix: promoted helper bridging the Stage 3 ``compute_intermediates``
    call site (which passes year/month/bbox) to the existing ``_fetch_jrc_tile``
    (which takes a per-tile URL). Stitches single-tile case and multi-tile case.
    """
    import rasterio
    from rasterio.merge import merge as rasterio_merge

    west, south, east, north = lonlat_bbox
    tiles = _tiles_for_bounds(west, south, east, north)
    tile_paths: list[Path] = []
    for tx, ty in tiles:
        url = _jrc_tile_url(year, month, tx, ty)
        tp = _fetch_jrc_tile(url=url, cache_dir=cache_dir)
        if tp is not None:
            tile_paths.append(tp)
    if not tile_paths:
        return None
    if len(tile_paths) == 1:
        return tile_paths[0]
    # Multi-tile merge: write merged GeoTIFF to cache
    merged_path = cache_dir / f"merged_{year}_{month:02d}_{west:.2f}_{south:.2f}.tif"
    if not merged_path.exists():
        datasets = [rasterio.open(p) for p in tile_paths]
        try:
            merged_arr, merged_transform = rasterio_merge(datasets)
            profile = datasets[0].profile.copy()
            profile.update(
                width=merged_arr.shape[-1],
                height=merged_arr.shape[-2],
                transform=merged_transform,
                count=1,
            )
            with rasterio.open(merged_path, "w", **profile) as dst:
                dst.write(merged_arr[0], 1)
        finally:
            for ds in datasets:
                ds.close()
    return merged_path


def _reproject_jrc_to_s2_grid(
    jrc_tile_path: Path | None,
    target_epsg: int,
    target_shape: tuple[int, int],
    target_transform: object | None = None,
) -> np.ndarray:
    """Reproject a JRC tile to a target S2 UTM grid.

    Returns a uint8 numpy array aligned to ``target_shape`` (rows, cols).
    If ``jrc_tile_path`` is None or the reprojection produces all-nodata,
    returns a zero array (all pixels treated as non-water).

    ``target_transform`` may be a rasterio Affine or an array with a
    ``.transform`` attribute; if None, the function uses rasterio to
    derive an appropriate transform from ``target_epsg + target_shape``.

    Plan 06-06 B4 fix: promoted helper for Stage 3 compute_intermediates to
    align JRC reference to the S2 UTM grid established by band reading.
    """
    import rasterio
    import rasterio.crs
    from rasterio.enums import Resampling
    from rasterio.transform import from_bounds
    from rasterio.warp import reproject, transform_bounds

    if jrc_tile_path is None:
        return np.zeros(target_shape, dtype=np.uint8)

    rows, cols = target_shape

    # Resolve transform: accept Affine, array with .transform attr, or None
    if target_transform is not None and hasattr(target_transform, "c"):
        # Already an Affine object
        dst_transform = target_transform
    elif target_transform is not None and hasattr(target_transform, "transform"):
        dst_transform = target_transform.transform
    else:
        dst_transform = None  # will be derived below

    with rasterio.open(jrc_tile_path) as src:
        dst_crs = rasterio.crs.CRS.from_epsg(target_epsg)

        if dst_transform is None:
            # Derive an approximate transform by reprojecting the tile bounds
            bounds_4326 = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
            from pyproj import Transformer
            t = Transformer.from_crs("EPSG:4326", f"EPSG:{target_epsg}", always_xy=True)
            min_x, min_y = t.transform(bounds_4326[0], bounds_4326[1])
            max_x, max_y = t.transform(bounds_4326[2], bounds_4326[3])
            dst_transform = from_bounds(min_x, min_y, max_x, max_y, cols, rows)

        dst_arr = np.zeros((rows, cols), dtype=np.uint8)
        reproject(
            source=rasterio.band(src, 1),
            destination=dst_arr,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,
        )
    return dst_arr


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
    from rasterio.windows import Window
    from rasterio.windows import from_bounds as window_from_bounds

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
            product_quality=ProductQualityResult(measurements={}, criterion_ids=[]),
            reference_agreement=ReferenceAgreementResult(
                measurements={
                    "f1": float("nan"),
                    "precision": float("nan"),
                    "recall": float("nan"),
                    "accuracy": float("nan"),
                },
                criterion_ids=["dswx.f1_min"],
            ),
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
            product_quality=ProductQualityResult(measurements={}, criterion_ids=[]),
            reference_agreement=ReferenceAgreementResult(
                measurements={
                    "f1": float("nan"),
                    "precision": float("nan"),
                    "recall": float("nan"),
                    "accuracy": float("nan"),
                },
                criterion_ids=["dswx.f1_min"],
            ),
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

    # Phase 6 D-16: compute shoreline buffer mask on the JRC-aligned window grid.
    # The buffer is computed on the JRC water/land class array (jrc_crop is
    # already in the UTM-aligned window; we use JRC binary water/land to find the
    # boundary). jrc_water_class=1 means water in the binary mask sense (jrc==2
    # in the raw encoding maps to 1.0 in _binarize_jrc; here we work with the
    # raw jrc_crop encoding where 2=water, 1=not-water, 0=nodata).
    # Build a simplified binary (water=True, non-water=False) for the buffer call:
    jrc_binary_for_mask = np.where(jrc_crop == 2, np.uint8(1), np.uint8(0))
    shoreline_mask = _compute_shoreline_buffer_mask(jrc_binary_for_mask, iterations=1)

    # 8. Mask to valid pixels (both non-NaN)
    valid_full = np.isfinite(prod_bin) & np.isfinite(jrc_bin)
    valid_shoreline_excl = valid_full & (~shoreline_mask)

    pred_full = prod_bin[valid_full].astype(np.int32)
    ref_full = jrc_bin[valid_full].astype(np.int32)

    pred = prod_bin[valid_shoreline_excl].astype(np.int32)
    ref = jrc_bin[valid_shoreline_excl].astype(np.int32)

    if pred.size == 0:
        logger.warning("No valid overlapping pixels between DSWx and JRC after shoreline exclusion")
        return DSWxValidationResult(
            product_quality=ProductQualityResult(measurements={}, criterion_ids=[]),
            reference_agreement=ReferenceAgreementResult(
                measurements={
                    "f1": float("nan"),
                    "precision": float("nan"),
                    "recall": float("nan"),
                    "accuracy": float("nan"),
                },
                criterion_ids=["dswx.f1_min"],
            ),
        )

    # 9. Compute shoreline-excluded metrics (gate value per D-16)
    f1 = f1_score(pred, ref)
    prec = precision_score(pred, ref)
    rec = recall_score(pred, ref)
    acc = overall_accuracy(pred, ref)

    # Phase 6 D-16 diagnostic: F1 without shoreline exclusion (P5.2 transparency)
    f1_full = f1_score(pred_full, ref_full) if pred_full.size > 0 else float("nan")
    shoreline_excluded_count = int(shoreline_mask.sum())

    logger.info(
        f"DSWx validation: F1={f1:.4f} (shoreline-excl), "
        f"F1_full={f1_full:.4f}, "
        f"shoreline_excluded_px={shoreline_excluded_count}, "
        f"precision={prec:.4f}, recall={rec:.4f}, OA={acc:.4f}"
    )

    return DSWxValidationResult(
        product_quality=ProductQualityResult(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResult(
            measurements={
                "f1": f1,          # shoreline-excluded (gate per D-16)
                "precision": prec,
                "recall": rec,
                "accuracy": acc,
            },
            criterion_ids=["dswx.f1_min"],
        ),
        diagnostics=DSWxValidationDiagnostics(
            f1_full_pixels=f1_full,
            shoreline_buffer_excluded_pixels=shoreline_excluded_count,
        ),
    )
