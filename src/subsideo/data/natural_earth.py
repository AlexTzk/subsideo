"""Natural Earth coastline + water-body geometries for stable-terrain buffers.

Uses ``cartopy.io.shapereader.natural_earth`` (already a main dependency via
pyproject.toml) to download Natural Earth shapefiles on demand from
``naturalearth.s3.amazonaws.com`` and cache them under
``~/.local/share/cartopy/shapefiles/natural_earth/``.

Returns geometries in EPSG:4326.

Note on water-body exclusion: this module provides **coastline + lakes only**.
For exclusion of permanent inland water bodies that Natural Earth ``lakes``
misses (ephemeral playas, endorheic pans), use
``data.worldcover.build_permanent_water_mask`` which reads WorldCover v200
class 80 (permanent water) and applies a 500 m buffer. See PITFALLS §P2.1
mitigation (b) for rationale.
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
        When ``cartopy`` is not installed (it is listed as a main dep in
        pyproject.toml; this should not happen in the subsideo environment).
    """
    import geopandas as gpd
    from shapely.geometry import box

    try:
        from cartopy.io import shapereader  # lazy; cartopy is a main dep
    except ImportError as err:
        raise ImportError(
            "cartopy is required for Natural Earth data access. "
            "Install via conda-forge: `mamba install -c conda-forge cartopy` "
            "(or `pip install -e '.[dev]'` to pull all pip-layer extras). "
            "cartopy is already listed as a main dependency in pyproject.toml; "
            "if this error fires, the environment is broken."
        ) from err

    clip_geom = box(*bbox)

    coastline_path = shapereader.natural_earth(
        resolution=scale, category="physical", name="coastline"
    )
    coastline_gdf = gpd.read_file(coastline_path)
    coastline = coastline_gdf[coastline_gdf.intersects(clip_geom)].geometry.reset_index(
        drop=True
    )

    lakes_path = shapereader.natural_earth(
        resolution=scale, category="physical", name="lakes"
    )
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
