"""DIST-S1 pipeline orchestrator.

Wraps opera-adt/dist-s1 with conditional lazy import (conda-forge only).
Produces COG GeoTIFF surface disturbance products from RTC-S1 time series.
"""
from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

from subsideo.products.types import DISTResult

__all__ = [
    "DISTResult",
    "validate_dist_product",
    "run_dist",
    "run_dist_from_aoi",
]


def validate_dist_product(cog_paths: list[Path]) -> list[str]:
    """Lightweight validation of DIST-S1 COG products.

    Checks each file for:
    1. Existence and readability
    2. Valid COG structure (via ``rio_cogeo.cog_validate``)
    3. UTM CRS (EPSG 326xx or 327xx)
    4. Approximate 30 m pixel size (25--35 m)

    Parameters
    ----------
    cog_paths:
        List of COG GeoTIFF paths to validate.

    Returns
    -------
    list[str]
        Error descriptions.  Empty list means all products are valid.
    """
    import rasterio

    # rio_cogeo >= 7.0 moved cog_validate from rio_cogeo.cog_validate to
    # rio_cogeo.cogeo. Support both to avoid coupling to a specific version.
    try:
        from rio_cogeo.cogeo import cog_validate  # rio_cogeo >= 7.0
    except ImportError:
        from rio_cogeo.cog_validate import cog_validate  # rio_cogeo < 7.0

    errors: list[str] = []
    for p in cog_paths:
        if not p.exists():
            errors.append(f"{p}: file does not exist")
            continue

        # COG structure
        is_valid, _, _ = cog_validate(str(p))
        if not is_valid:
            errors.append(f"{p}: not a valid COG")

        # CRS and pixel size
        with rasterio.open(p) as ds:
            epsg = ds.crs.to_epsg() if ds.crs else None
            if epsg is None or not (32601 <= epsg <= 32660 or 32701 <= epsg <= 32760):
                errors.append(f"{p}: CRS is not UTM (EPSG={epsg})")
            pixel_x = abs(ds.transform.a)
            pixel_y = abs(ds.transform.e)
            avg_pixel = (pixel_x + pixel_y) / 2
            if not (25 <= avg_pixel <= 35):
                errors.append(
                    f"{p}: pixel size {avg_pixel:.1f} m outside 25-35 m range"
                )

    return errors


def _aoi_to_mgrs_tiles(aoi: dict) -> list[dict]:
    """Resolve an AOI GeoJSON geometry to an MGRS tile ID and track number.

    Uses the ``mgrs`` library (a GeoTrans C wrapper) to resolve the AOI
    centroid to a canonical 100 km MGRS square ID (zone + band + 2-letter
    square, e.g. ``"32UPU"``). For multi-tile AOIs the caller is
    responsible for iterating sub-polygons — this function returns a single
    representative tile covering the centroid.

    The track number is a rough longitude-based heuristic; for accurate
    Sentinel-1 relative-orbit resolution use the burst database.

    Parameters
    ----------
    aoi:
        GeoJSON geometry dict with ``"type"`` and ``"coordinates"`` keys.

    Returns
    -------
    list[dict]
        Single-element list; the dict has ``"mgrs_tile_id"`` (str) and
        ``"track_number"`` (int) keys.
    """
    import mgrs

    coords = aoi["coordinates"][0]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    # Centroid
    center_lon = sum(lons) / len(lons)
    center_lat = sum(lats) / len(lats)

    # Resolve centroid -> canonical 100 km MGRS square via GeoTrans.
    # MGRSPrecision=0 returns the 5-character square ID (zone + band + col + row).
    mgrs_tile_id = mgrs.MGRS().toMGRS(
        latitude=center_lat,
        longitude=center_lon,
        MGRSPrecision=0,
    )

    # Track number: simplified longitude heuristic. Sentinel-1 has 175
    # relative orbits. For accurate resolution use the burst DB.
    track_number = (int((center_lon + 180) * 175 / 360) % 175) + 1

    logger.debug(
        "AOI centroid ({:.2f}, {:.2f}) -> MGRS tile {}, track {}",
        center_lon,
        center_lat,
        mgrs_tile_id,
        track_number,
    )

    return [{"mgrs_tile_id": mgrs_tile_id, "track_number": track_number}]


def run_dist(
    mgrs_tile_id: str,
    post_date: str,
    track_number: int,
    output_dir: Path,
) -> DISTResult:
    """Run the DIST-S1 surface disturbance pipeline for a single MGRS tile.

    Wraps ``dist_s1.run_dist_s1_workflow()`` with lazy conditional import.
    The dist-s1 package is conda-forge-only and may not be installed.

    Parameters
    ----------
    mgrs_tile_id:
        MGRS tile identifier (e.g. ``"33UUP"``).
    post_date:
        Post-event date string (e.g. ``"2025-06-15"``).
    track_number:
        Sentinel-1 relative orbit / track number.
    output_dir:
        Directory for pipeline outputs.

    Returns
    -------
    DISTResult
        Processing result with output paths and validation status.

    Raises
    ------
    ImportError
        If dist-s1 is not installed.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from dist_s1 import run_dist_s1_workflow
    except ImportError as exc:
        raise ImportError(
            "dist-s1 is not installed. "
            "Install via conda-forge: mamba install -c conda-forge dist-s1"
        ) from exc

    try:
        logger.info(
            "Running DIST-S1 for tile {} (track {}, date {})",
            mgrs_tile_id,
            track_number,
            post_date,
        )
        run_dist_s1_workflow(
            mgrs_tile_id=mgrs_tile_id,
            post_date=post_date,
            track_number=track_number,
            dst_dir=output_dir,
        )
    except Exception as exc:
        logger.error("DIST-S1 processing failed: {}", exc)
        return DISTResult(
            output_paths=[],
            output_dir=output_dir,
            valid=False,
            validation_errors=[f"DIST-S1 processing failed: {exc}"],
        )

    # Collect output COG GeoTIFFs
    cog_paths = sorted(output_dir.glob("*.tif"))

    # Validate
    errors = validate_dist_product(cog_paths)

    # OUT-03: Inject OPERA metadata
    from subsideo._metadata import get_software_version, inject_opera_metadata

    sw_version = get_software_version()
    for cog_path in cog_paths:
        if cog_path.exists():
            inject_opera_metadata(
                cog_path,
                product_type="DIST-S1",
                software_version=sw_version,
                run_params={
                    "mgrs_tile_id": mgrs_tile_id,
                    "track_number": track_number,
                    "post_date": post_date,
                    "output_dir": str(output_dir),
                },
            )

    result = DISTResult(
        output_paths=cog_paths,
        output_dir=output_dir,
        valid=len(errors) == 0,
        validation_errors=errors,
    )

    if result.valid:
        logger.info("DIST-S1 completed successfully: {} COGs", len(cog_paths))
    else:
        logger.warning("DIST-S1 completed with validation errors: {}", errors)

    return result


def run_dist_from_aoi(
    aoi: dict | Path,
    date_range: tuple[str, str],
    output_dir: Path,
) -> list[DISTResult]:
    """End-to-end DIST-S1 pipeline from AOI geometry and date range.

    Resolves MGRS tiles for the AOI, builds an RTC time series by querying
    CDSE for Sentinel-1 scenes and running ``run_rtc()`` for each, then
    calls ``run_dist()`` for each MGRS tile.

    Parameters
    ----------
    aoi:
        GeoJSON dict (``{"type": "Polygon", "coordinates": ...}``) or
        a ``Path`` to a GeoJSON file.
    date_range:
        ``(start_date, end_date)`` strings in ``YYYY-MM-DD`` format.
    output_dir:
        Root directory for all pipeline outputs.

    Returns
    -------
    list[DISTResult]
        One result per MGRS tile processed.
    """
    from datetime import datetime

    from subsideo.burst.frames import query_bursts_for_aoi
    from subsideo.data.cdse import CDSEClient
    from subsideo.data.dem import fetch_dem
    from subsideo.data.orbits import fetch_orbit
    from subsideo.products.rtc import run_rtc

    # Resolve AOI geometry
    if isinstance(aoi, Path):
        with open(aoi) as f:
            aoi = json.load(f)

    if "type" not in aoi or "coordinates" not in aoi:
        raise ValueError("Invalid AOI: must contain 'type' and 'coordinates' keys")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve MGRS tiles for the AOI
    tiles = _aoi_to_mgrs_tiles(aoi)
    logger.info("Resolved {} MGRS tiles for AOI", len(tiles))

    # Build bounding box from AOI
    coords = aoi["coordinates"][0]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    bbox = [min(lons), min(lats), max(lons), max(lats)]

    # Build RTC time series
    start_str, end_str = date_range
    start_dt = datetime.fromisoformat(start_str)
    end_dt = datetime.fromisoformat(end_str)

    from subsideo.config import Settings

    settings = Settings()
    client = CDSEClient(
        client_id=settings.cdse_client_id,
        client_secret=settings.cdse_client_secret,
    )
    scenes = client.search_stac(
        collection="SENTINEL-1",
        bbox=bbox,
        start=start_dt,
        end=end_dt,
        product_type="IW_SLC__1S",
    )
    logger.info("Found {} S1 scenes for RTC time series", len(scenes))

    # Query burst DB for the AOI
    from shapely.geometry import shape

    aoi_geom = shape(aoi)
    bursts = query_bursts_for_aoi(aoi_wkt=aoi_geom.wkt)
    burst_ids = [b.burst_id_jpl for b in bursts] if bursts else []

    # Fetch DEM (after burst query so we can use burst EPSG)
    output_epsg = bursts[0].epsg if bursts else 32632
    dem_path, _dem_profile = fetch_dem(
        bounds=bbox,
        output_epsg=output_epsg,
        output_dir=output_dir / "dem",
    )

    # Process each scene through RTC
    for i, scene in enumerate(scenes):
        logger.info("Building RTC time series: {}/{} scenes...", i + 1, len(scenes))

        s3_key = scene.get("assets", {}).get("data", {}).get("href", "")
        safe_path = output_dir / "safe" / f"scene_{i}.zip"
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        client.download(s3_key, safe_path)

        sensing_time = datetime.fromisoformat(
            scene.get("properties", {}).get("datetime", start_str)
        )
        satellite = scene.get("properties", {}).get("platform", "S1A")
        orbit_path = fetch_orbit(
            sensing_time=sensing_time,
            satellite=satellite,
            output_dir=output_dir / "orbits",
        )

        run_rtc(
            safe_paths=[safe_path],
            orbit_path=orbit_path,
            dem_path=dem_path,
            burst_ids=burst_ids,
            output_dir=output_dir / "rtc" / f"scene_{i}",
        )

    # Run DIST-S1 for each MGRS tile
    results: list[DISTResult] = []
    for tile in tiles:
        logger.info("Running DIST-S1 for tile {}...", tile["mgrs_tile_id"])
        result = run_dist(
            mgrs_tile_id=tile["mgrs_tile_id"],
            post_date=end_str,
            track_number=tile["track_number"],
            output_dir=output_dir / tile["mgrs_tile_id"],
        )
        results.append(result)

    return results
