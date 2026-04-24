"""ESA WorldCover v200 (2021) tile fetch from public-read S3.

Source: s3://esa-worldcover/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif
(public-read, no credentials, WGS84, 3x3 degree tiles named
N{lat:02d}E{lon:03d}). Consumed by validation/stable_terrain.build_stable_mask.

The CONTEXT Claude's Discretion resolution placed this in ``data/`` (not
inside ``validation/stable_terrain``) for extensibility to Phase 6 DSWx AOI
work — WorldCover tiles are useful beyond stable-mask construction.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    import numpy as np
    from affine import Affine
    from geopandas import GeoDataFrame
    from rasterio.crs import CRS

WORLDCOVER_S3_BUCKET = "esa-worldcover"
WORLDCOVER_S3_PREFIX = "v200/2021/map"
WORLDCOVER_TILE_DEG = 3  # tiles are 3x3 degrees


def _tile_name(lat_south: int, lon_west: int) -> str:
    """Return the ESA WorldCover tile filename for one 3x3 tile corner."""
    ns = "N" if lat_south >= 0 else "S"
    ew = "E" if lon_west >= 0 else "W"
    return f"ESA_WorldCover_10m_2021_v200_{ns}{abs(lat_south):02d}{ew}{abs(lon_west):03d}_Map.tif"


def _tiles_covering_bbox(bbox: tuple[float, float, float, float]) -> list[tuple[int, int]]:
    """Return (lat_south, lon_west) integer tile corners covering the bbox."""
    west, south, east, north = bbox
    lat_tiles = range(
        int(math.floor(south / WORLDCOVER_TILE_DEG) * WORLDCOVER_TILE_DEG),
        int(math.ceil(north / WORLDCOVER_TILE_DEG) * WORLDCOVER_TILE_DEG),
        WORLDCOVER_TILE_DEG,
    )
    lon_tiles = range(
        int(math.floor(west / WORLDCOVER_TILE_DEG) * WORLDCOVER_TILE_DEG),
        int(math.ceil(east / WORLDCOVER_TILE_DEG) * WORLDCOVER_TILE_DEG),
        WORLDCOVER_TILE_DEG,
    )
    return [(lat, lon) for lat in lat_tiles for lon in lon_tiles]


def fetch_worldcover_class60(
    bbox: tuple[float, float, float, float],
    *,
    out_dir: Path,
) -> Path:
    """Download WorldCover tiles covering bbox; return the out_dir path.

    Uses anonymous (no-credential) S3 access; tiles are public-read on
    ``s3://esa-worldcover/``. Idempotent: existing tiles are skipped.

    Parameters
    ----------
    bbox : (west, south, east, north) in EPSG:4326 degrees.
    out_dir : Path
        Directory to cache downloaded tiles. Created if absent.

    Returns
    -------
    Path
        The ``out_dir`` path (all tiles for the bbox are guaranteed to exist
        in this directory after return).
    """
    import boto3  # lazy — conda-forge-shim dep
    from botocore import UNSIGNED
    from botocore.config import Config

    out_dir.mkdir(parents=True, exist_ok=True)
    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))

    tiles = _tiles_covering_bbox(bbox)
    logger.info("WorldCover: fetching {} tiles covering bbox={}", len(tiles), bbox)
    for lat, lon in tiles:
        fn = _tile_name(lat, lon)
        dest = out_dir / fn
        if dest.exists():
            logger.debug("WorldCover: cached {}", dest.name)
            continue
        key = f"{WORLDCOVER_S3_PREFIX}/{fn}"
        logger.info("WorldCover: s3://{}/{} -> {}", WORLDCOVER_S3_BUCKET, key, dest)
        s3.download_file(WORLDCOVER_S3_BUCKET, key, str(dest))
    return out_dir


def load_worldcover_for_bbox(
    bbox: tuple[float, float, float, float],
    *,
    tiles_dir: Path,
) -> tuple[np.ndarray, Affine, CRS]:
    """Load tiles covering bbox into a single mosaic ndarray + transform + CRS.

    Parameters
    ----------
    bbox : (west, south, east, north) in EPSG:4326 degrees.
    tiles_dir : Path
        Directory containing WorldCover tiles covering ``bbox``; typically
        the ``out_dir`` returned by ``fetch_worldcover_class60``.

    Returns
    -------
    (data, transform, crs) : tuple
        ``data`` is (H, W) uint8 WorldCover class codes (class 60 = bare/sparse,
        class 200 = permanent water bodies).
        ``transform`` is an Affine mapping pixel -> WGS84 lon/lat.
        ``crs`` is the rasterio CRS (EPSG:4326 — WorldCover v200 native).
    """
    import numpy as np
    import rasterio
    from rasterio.merge import merge

    tiles = _tiles_covering_bbox(bbox)
    srcs = [rasterio.open(tiles_dir / _tile_name(lat, lon)) for lat, lon in tiles]
    try:
        mosaic, transform = merge(srcs, bounds=bbox)
        crs = srcs[0].crs
    finally:
        for s in srcs:
            s.close()
    return mosaic[0].astype(np.uint8), transform, crs


def build_permanent_water_mask(
    bounds: tuple[float, float, float, float],
    *,
    tiles_dir: Path,
    buffer_m: float = 500.0,
) -> GeoDataFrame:
    """Return permanent-water + buffered-water geometry for stable_terrain.build_stable_mask.

    Rationale (PITFALLS P2.1 mitigation (b)): Natural Earth ``lakes`` misses
    ephemeral playas (Amargosa / Searles / Coso). WorldCover v200 class 200
    ("permanent water bodies") captures these. A ``buffer_m = 500`` default
    applies the Phase 1 stable_terrain water-buffer rule to the classified
    water cells, producing a GeoDataFrame ready to pass as the ``waterbodies``
    arg in ``build_stable_mask(...)``.

    Parameters
    ----------
    bounds : (west, south, east, north) in EPSG:4326 degrees.
    tiles_dir : Path
        Directory containing WorldCover tiles that cover ``bounds``; use
        ``fetch_worldcover_class60(bounds, out_dir=...)`` first.
    buffer_m : float, default 500.0
        Metres to buffer classified water pixels (matches stable_terrain
        water_buffer_m default).

    Returns
    -------
    GeoDataFrame
        Buffered water polygons in the tiles' native CRS (EPSG:4326); caller
        reprojects if needed.
    """
    import geopandas as gpd
    import numpy as np
    from rasterio.features import shapes
    from shapely.geometry import shape

    data, transform, crs = load_worldcover_for_bbox(bounds, tiles_dir=tiles_dir)
    water = (data == 200).astype(np.uint8)
    if not water.any():
        return gpd.GeoDataFrame(geometry=[], crs=crs)
    polys = [
        shape(geom)
        for geom, val in shapes(water, transform=transform)
        if val == 1
    ]
    gdf = gpd.GeoDataFrame(geometry=polys, crs=crs)
    # Reproject to a metric CRS for buffering, then reproject back.
    west, south, east, north = bounds
    center_lon = (west + east) / 2.0
    utm_zone = int((center_lon + 180) / 6) + 1
    center_lat = (south + north) / 2.0
    metric_crs = (
        f"EPSG:326{utm_zone:02d}" if center_lat >= 0 else f"EPSG:327{utm_zone:02d}"
    )
    gdf_m = gdf.to_crs(metric_crs)
    gdf_m["geometry"] = gdf_m.geometry.buffer(buffer_m)
    return gdf_m.to_crs(crs)
