"""Natural Earth coastline + water-body geometries for stable-terrain buffers.

Uses the ``naturalearth`` PyPI package (Claude's Discretion resolution —
CONTEXT 03-CONTEXT.md — over OSM for simplicity at the current AOI scale).
Returns geometries in EPSG:4326.

Note on water-body exclusion: This module provides **coastline geometry only**.
For exclusion of permanent inland water bodies (ephemeral playas, endorheic
lakes missed by Natural Earth ``lakes``), use
``data.worldcover.build_permanent_water_mask`` which reads WorldCover v200
class 200 (permanent water bodies) and applies a 500 m buffer. See
PITFALLS §P2.1 mitigation (b) for rationale.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    import geopandas as gpd

DEFAULT_SCALE = "10m"  # Natural Earth 10m = highest resolution


def load_coastline_and_waterbodies(
    bbox: tuple[float, float, float, float],
    *,
    scale: str = DEFAULT_SCALE,
) -> tuple[gpd.GeoSeries, gpd.GeoSeries]:
    """Return (coastline, waterbodies) GeoSeries clipped to the bbox.

    Both series are in EPSG:4326 (WGS84) and contain only features whose
    geometry intersects the bbox rectangle. Empty GeoSeries (not None) are
    returned when no feature intersects the bbox.

    Parameters
    ----------
    bbox : (west, south, east, north) in EPSG:4326 degrees.
    scale : {'10m', '50m', '110m'}
        Natural Earth resolution. '10m' (highest detail) is the default and
        is appropriate for AOI-scale analysis (tens of km). '50m' / '110m'
        for continental/global overviews only.

    Returns
    -------
    (coastline, waterbodies) : tuple of geopandas.GeoSeries
        Both in EPSG:4326. ``coastline`` carries the Natural Earth coastline
        lines. ``waterbodies`` carries Natural Earth lake polygons.
        Use ``data.worldcover.build_permanent_water_mask`` in addition when
        the AOI may contain ephemeral playas (PITFALLS P2.1 mitigation (b)).

    Raises
    ------
    ImportError
        When the ``naturalearth`` PyPI package is not installed. Install via
        ``pip install naturalearth`` or ``pip install -e ".[dev]"`` (it is
        listed in ``[project.optional-dependencies.dev]``).
    """
    import geopandas as gpd
    from shapely.geometry import box

    try:
        import naturalearth  # lazy
    except ImportError as err:
        raise ImportError(
            "naturalearth PyPI package is required. "
            "Install via: pip install naturalearth  "
            "(or pip install -e '.[dev]' to pull all dev extras)"
        ) from err

    clip_geom = box(*bbox)

    coastline_path = naturalearth.get_path(scale=scale, name="coastline")
    coastline_gdf = gpd.read_file(coastline_path)
    coastline = coastline_gdf[coastline_gdf.intersects(clip_geom)].geometry.reset_index(
        drop=True
    )

    lakes_path = naturalearth.get_path(scale=scale, name="lakes")
    lakes_gdf = gpd.read_file(lakes_path)
    lakes = lakes_gdf[lakes_gdf.intersects(clip_geom)].geometry.reset_index(drop=True)

    logger.debug(
        "Natural Earth {}: {} coastline features, {} lake features in bbox={}",
        scale,
        len(coastline),
        len(lakes),
        bbox,
    )
    return coastline, lakes
