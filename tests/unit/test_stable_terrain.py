"""Unit tests for subsideo.validation.stable_terrain.build_stable_mask."""
from __future__ import annotations

import numpy as np
import pytest


def test_worldcover_only_all_class_60() -> None:
    from subsideo.validation.stable_terrain import build_stable_mask

    worldcover = np.full((10, 10), 60, dtype=np.int16)
    slope = np.zeros((10, 10), dtype=np.float32)
    mask = build_stable_mask(worldcover, slope)
    assert mask.dtype == np.bool_
    assert mask.all()
    assert mask.shape == (10, 10)


def test_worldcover_no_class_60() -> None:
    from subsideo.validation.stable_terrain import build_stable_mask

    worldcover = np.full((10, 10), 10, dtype=np.int16)  # tree cover
    slope = np.zeros((10, 10), dtype=np.float32)
    mask = build_stable_mask(worldcover, slope)
    assert not mask.any()
    assert mask.shape == (10, 10)


def test_slope_gate_default_10_deg() -> None:
    from subsideo.validation.stable_terrain import build_stable_mask

    worldcover = np.full((4, 4), 60, dtype=np.int16)
    # Each row: [0, 5, 10, 11] -- the first three are <=10, fourth >10
    slope = np.array([[0, 5, 10, 11]] * 4, dtype=np.float32)
    mask = build_stable_mask(worldcover, slope)
    assert mask[:, 0].all() and mask[:, 1].all() and mask[:, 2].all()  # <= 10
    assert not mask[:, 3].any()  # > 10 excluded


def test_slope_gate_tightened() -> None:
    from subsideo.validation.stable_terrain import build_stable_mask

    worldcover = np.full((4, 4), 60, dtype=np.int16)
    slope = np.array([[0, 5, 10, 11]] * 4, dtype=np.float32)
    mask = build_stable_mask(worldcover, slope, slope_max_deg=5.0)
    assert mask[:, 0].all() and mask[:, 1].all()  # <= 5
    assert not mask[:, 2].any()  # > 5 excluded
    assert not mask[:, 3].any()  # > 5 excluded


def test_nan_slope_excluded() -> None:
    from subsideo.validation.stable_terrain import build_stable_mask

    worldcover = np.full((3, 3), 60, dtype=np.int16)
    slope = np.full((3, 3), np.nan, dtype=np.float32)
    mask = build_stable_mask(worldcover, slope)
    assert not mask.any()  # all slope-NaN excluded


def test_shape_mismatch_raises() -> None:
    from subsideo.validation.stable_terrain import build_stable_mask

    with pytest.raises(ValueError, match="shape"):
        build_stable_mask(
            np.full((10, 10), 60, dtype=np.int16),
            np.zeros((5, 5), dtype=np.float32),
        )


def test_module_constants_match_cslc01_spec() -> None:
    """Defaults must match CSLC-01 requirement text exactly."""
    from subsideo.validation.stable_terrain import (
        DEFAULT_COAST_BUFFER_M,
        DEFAULT_SLOPE_MAX_DEG,
        DEFAULT_WATER_BUFFER_M,
        WORLDCOVER_BARE_SPARSE_CLASS,
    )

    assert WORLDCOVER_BARE_SPARSE_CLASS == 60
    assert DEFAULT_SLOPE_MAX_DEG == 10.0
    assert DEFAULT_COAST_BUFFER_M == 5000.0
    assert DEFAULT_WATER_BUFFER_M == 500.0


def test_coast_buffer_excludes_ring() -> None:
    """Coastline through the raster center should exclude a band around it."""
    pytest.importorskip("geopandas", reason="geopandas needed for coast buffer test")
    affine_mod = pytest.importorskip("affine", reason="affine needed for coast buffer test")
    pytest.importorskip("shapely", reason="shapely needed for coast buffer test")
    pytest.importorskip("rasterio", reason="rasterio needed for coast buffer test")

    from rasterio.crs import CRS
    from shapely.geometry import LineString

    from subsideo.validation.stable_terrain import build_stable_mask

    # 100x100 raster at 100 m resolution, extent 0..10000 in both directions
    worldcover = np.full((100, 100), 60, dtype=np.int16)
    slope = np.zeros((100, 100), dtype=np.float32)
    # Affine: origin top-left at (0, 10000), x/y pixel size 100 m, -100 m
    transform = affine_mod.Affine.translation(0, 10000) * affine_mod.Affine.scale(100, -100)
    crs = CRS.from_epsg(32632)  # UTM 32N (metric)
    # Coastline is a horizontal line through the vertical center (y = 5000)
    coastline = LineString([(0, 5000), (10000, 5000)])

    mask = build_stable_mask(
        worldcover, slope, coastline=coastline,
        transform=transform, crs=crs,
        coast_buffer_m=2000.0,  # tighter buffer so excluded band is visible
    )
    # The horizontal band within ~2 km of y=5000 (rows 30..70) must contain excluded pixels
    assert not mask[30:70, :].all()
    # Far corners at y near 10000 and y near 0 remain stable
    assert bool(mask[0, 0]) or bool(mask[-1, -1])


def test_waterbody_buffer_excludes_ring() -> None:
    """A water polygon at the raster center should produce an exclusion ring."""
    pytest.importorskip("geopandas", reason="geopandas needed for water buffer test")
    affine_mod = pytest.importorskip("affine", reason="affine needed for water buffer test")
    pytest.importorskip("shapely", reason="shapely needed for water buffer test")
    pytest.importorskip("rasterio", reason="rasterio needed for water buffer test")

    from rasterio.crs import CRS
    from shapely.geometry import Polygon

    from subsideo.validation.stable_terrain import build_stable_mask

    worldcover = np.full((100, 100), 60, dtype=np.int16)
    slope = np.zeros((100, 100), dtype=np.float32)
    transform = affine_mod.Affine.translation(0, 10000) * affine_mod.Affine.scale(100, -100)
    crs = CRS.from_epsg(32632)
    # Water polygon: small square near center, ~1 km side
    water = Polygon([(4500, 4500), (5500, 4500), (5500, 5500), (4500, 5500), (4500, 4500)])

    mask_default = build_stable_mask(
        worldcover, slope, waterbodies=water,
        transform=transform, crs=crs,
    )
    mask_tight = build_stable_mask(
        worldcover, slope, waterbodies=water,
        transform=transform, crs=crs,
        water_buffer_m=1500.0,  # larger buffer excludes more
    )
    # Larger buffer must exclude at least as many pixels
    assert (~mask_tight).sum() >= (~mask_default).sum()
    # Some exclusion must occur around the water body
    assert (~mask_default).sum() > 0


def test_coast_buffer_reprojects_epsg4326_geoseries_to_utm11() -> None:
    """EPSG:4326 coast geometries must be buffered in UTM metres, not degrees."""
    gpd = pytest.importorskip("geopandas", reason="geopandas needed for CRS reprojection")
    affine_mod = pytest.importorskip("affine", reason="affine needed for raster transform")
    pyproj_mod = pytest.importorskip("pyproj", reason="pyproj needed for test coordinates")
    pytest.importorskip("shapely", reason="shapely needed for geometry")
    pytest.importorskip("rasterio", reason="rasterio needed for rasterize")

    from rasterio.crs import CRS
    from shapely.geometry import LineString

    from subsideo.validation.stable_terrain import build_stable_mask

    raster_crs = CRS.from_string("EPSG:32611")
    transformer = pyproj_mod.Transformer.from_crs("EPSG:4326", raster_crs, always_xy=True)
    center_x, center_y = transformer.transform(-117.1, 34.0)
    transform = (
        affine_mod.Affine.translation(center_x - 5000, center_y + 5000)
        * affine_mod.Affine.scale(100, -100)
    )
    coastline = gpd.GeoSeries(
        [LineString([(-117.1, 33.96), (-117.1, 34.04)])],
        crs="EPSG:4326",
    )

    worldcover = np.full((100, 100), 60, dtype=np.int16)
    slope = np.zeros((100, 100), dtype=np.float32)
    mask = build_stable_mask(
        worldcover,
        slope,
        coastline=coastline,
        transform=transform,
        crs=raster_crs,
        coast_buffer_m=1000.0,
    )

    assert (~mask).sum() > 0
    assert bool(mask[0, 0]) or bool(mask[-1, -1])


def test_waterbody_buffer_reprojects_epsg4326_geoseries_to_utm30() -> None:
    """EPSG:4326 water polygons must respect metric buffers on Iberian UTM grids."""
    gpd = pytest.importorskip("geopandas", reason="geopandas needed for CRS reprojection")
    affine_mod = pytest.importorskip("affine", reason="affine needed for raster transform")
    pyproj_mod = pytest.importorskip("pyproj", reason="pyproj needed for test coordinates")
    pytest.importorskip("shapely", reason="shapely needed for geometry")
    pytest.importorskip("rasterio", reason="rasterio needed for rasterize")

    from rasterio.crs import CRS
    from shapely.geometry import Polygon

    from subsideo.validation.stable_terrain import build_stable_mask

    raster_crs = CRS.from_string("EPSG:32630")
    transformer = pyproj_mod.Transformer.from_crs("EPSG:4326", raster_crs, always_xy=True)
    center_x, center_y = transformer.transform(-4.0, 41.0)
    transform = (
        affine_mod.Affine.translation(center_x - 5000, center_y + 5000)
        * affine_mod.Affine.scale(100, -100)
    )
    water = gpd.GeoSeries(
        [
            Polygon(
                [
                    (-4.005, 40.995),
                    (-3.995, 40.995),
                    (-3.995, 41.005),
                    (-4.005, 41.005),
                    (-4.005, 40.995),
                ]
            )
        ],
        crs="EPSG:4326",
    )

    worldcover = np.full((100, 100), 60, dtype=np.int16)
    slope = np.zeros((100, 100), dtype=np.float32)
    mask_default = build_stable_mask(
        worldcover,
        slope,
        waterbodies=water,
        transform=transform,
        crs=raster_crs,
    )
    mask_larger = build_stable_mask(
        worldcover,
        slope,
        waterbodies=water,
        transform=transform,
        crs=raster_crs,
        water_buffer_m=1500.0,
    )

    assert (~mask_default).sum() > 0
    assert (~mask_larger).sum() >= (~mask_default).sum()


def test_output_dtype_is_bool() -> None:
    from subsideo.validation.stable_terrain import build_stable_mask

    worldcover = np.full((5, 5), 60, dtype=np.int16)
    slope = np.zeros((5, 5), dtype=np.float32)
    mask = build_stable_mask(worldcover, slope)
    assert mask.dtype == np.bool_
