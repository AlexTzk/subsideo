"""Unit tests for subsideo.data.worldcover — ESA WorldCover v200 tile fetch helpers."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


class TestTileNaming:
    """_tile_name produces correct filenames for positive/negative lat/lon corners."""

    def test_positive_lat_lon(self) -> None:
        from subsideo.data.worldcover import _tile_name

        name = _tile_name(33, 117)
        assert name == "ESA_WorldCover_10m_2021_v200_N33E117_Map.tif"

    def test_negative_lat_positive_lon(self) -> None:
        from subsideo.data.worldcover import _tile_name

        name = _tile_name(-33, 18)
        assert name == "ESA_WorldCover_10m_2021_v200_S33E018_Map.tif"

    def test_zero_lat(self) -> None:
        from subsideo.data.worldcover import _tile_name

        name = _tile_name(0, 36)
        assert name == "ESA_WorldCover_10m_2021_v200_N00E036_Map.tif"


class TestTilesCoveringBbox:
    """_tiles_covering_bbox returns all 3x3 tile corners covering a bbox."""

    def test_single_tile_bbox(self) -> None:
        from subsideo.data.worldcover import _tiles_covering_bbox

        tiles = _tiles_covering_bbox((34.0, 34.5, 35.9, 36.4))
        # bbox spans one 3-deg tile: lat 33-36, lon 33-36
        assert (33, 33) in tiles

    def test_multi_tile_bbox(self) -> None:
        from subsideo.data.worldcover import _tiles_covering_bbox

        # bbox spanning two lat tiles and two lon tiles
        tiles = _tiles_covering_bbox((-1.0, -1.0, 1.0, 1.0))
        # Expect 4 tiles: lat(-3,-0) x lon(-3, 0)
        assert len(tiles) >= 4

    def test_url_shape(self) -> None:
        """Tile names for a SoCal bbox contain the expected S3 path pattern."""
        from subsideo.data.worldcover import (
            WORLDCOVER_S3_BUCKET,
            WORLDCOVER_S3_PREFIX,
            _tile_name,
            _tiles_covering_bbox,
        )

        bbox = (-118.5, 33.0, -117.0, 34.5)
        tiles = _tiles_covering_bbox(bbox)
        for lat, lon in tiles:
            fn = _tile_name(lat, lon)
            s3_key = f"{WORLDCOVER_S3_PREFIX}/{fn}"
            # Check pattern: must start with version prefix and end with _Map.tif
            assert s3_key.startswith("v200/2021/map/ESA_WorldCover_10m_2021_v200_")
            assert s3_key.endswith("_Map.tif")
            # Full URL shape matches s3://esa-worldcover/v200/2021/map/...
            full_url = f"s3://{WORLDCOVER_S3_BUCKET}/{s3_key}"
            assert full_url.startswith("s3://esa-worldcover/v200/2021/map/")


class TestFetchWorldcoverClass60:
    """fetch_worldcover_class60 downloads tiles via anonymous S3; cache hit skips."""

    def test_cache_hit_skips_s3(self, tmp_path: Path) -> None:
        """If tile already exists in out_dir, boto3.client is never called."""
        from subsideo.data.worldcover import _tile_name, fetch_worldcover_class60

        bbox = (-118.5, 33.0, -118.0, 33.5)
        # Pre-create the tile file so the function sees it as cached
        (tmp_path / _tile_name(33, -120)).write_bytes(b"fake")

        mock_s3 = MagicMock()
        with patch("boto3.client", return_value=mock_s3) as mock_client:
            # Patch to always find tiles as existing - use a bbox that maps to one tile
            from subsideo.data.worldcover import _tiles_covering_bbox

            tiles = _tiles_covering_bbox(bbox)
            # Pre-create all tiles so nothing needs downloading
            for lat, lon in tiles:
                (tmp_path / _tile_name(lat, lon)).write_bytes(b"fake")

            result = fetch_worldcover_class60(bbox, out_dir=tmp_path)

        # download_file should never have been called (all cached)
        mock_s3.download_file.assert_not_called()
        assert result == tmp_path

    def test_download_called_for_missing_tile(self, tmp_path: Path) -> None:
        """Tiles not in out_dir trigger s3.download_file calls."""
        from subsideo.data.worldcover import fetch_worldcover_class60

        bbox = (-118.5, 33.0, -118.0, 33.5)
        mock_s3 = MagicMock()

        with patch("boto3.client", return_value=mock_s3):
            with patch(
                "botocore.UNSIGNED", new=None
            ), patch("botocore.config.Config"):
                fetch_worldcover_class60(bbox, out_dir=tmp_path)

        # At least one download_file call should have been issued
        assert mock_s3.download_file.called


class TestLoadWorldcoverForBbox:
    """load_worldcover_for_bbox returns (uint8 ndarray, Affine, CRS)."""

    def test_returns_uint8_ndarray(self, tmp_path: Path) -> None:
        """Mocked tile read returns (H, W) uint8 ndarray + transform + CRS."""
        import numpy as np
        import rasterio
        from affine import Affine
        from rasterio.crs import CRS
        from rasterio.io import MemoryFile

        from subsideo.data.worldcover import _tile_name, load_worldcover_for_bbox

        # Build a small in-memory tile file
        tile_data = np.full((30, 30), 60, dtype=np.uint8)
        transform = Affine(0.1, 0.0, -120.0, 0.0, -0.1, 36.0)
        crs = CRS.from_epsg(4326)

        bbox = (-120.0, 33.0, -117.0, 36.0)
        tiles_dir = tmp_path

        # Write a fake tile that covers lat=33, lon=-120
        from subsideo.data.worldcover import _tiles_covering_bbox

        tiles = _tiles_covering_bbox(bbox)
        for lat, lon in tiles:
            fn = _tile_name(lat, lon)
            with MemoryFile() as memfile:
                with memfile.open(
                    driver="GTiff",
                    count=1,
                    dtype="uint8",
                    width=30,
                    height=30,
                    crs=crs,
                    transform=transform,
                ) as dataset:
                    dataset.write(tile_data, 1)
                (tiles_dir / fn).write_bytes(memfile.read())

        data, out_transform, out_crs = load_worldcover_for_bbox(bbox, tiles_dir=tiles_dir)

        assert data.dtype == np.uint8
        assert data.ndim == 2
        assert isinstance(out_crs, CRS)


class TestBuildPermanentWaterMask:
    """build_permanent_water_mask extracts class-200 pixels and buffers them."""

    def test_returns_geodataframe_with_buffers(self, tmp_path: Path) -> None:
        """On a grid with class-200 pixels, the returned GDF has at least one polygon."""
        import numpy as np
        from affine import Affine
        from rasterio.crs import CRS
        from rasterio.io import MemoryFile

        from subsideo.data.worldcover import (
            _tile_name,
            _tiles_covering_bbox,
            build_permanent_water_mask,
        )

        bbox = (-120.0, 33.0, -117.0, 36.0)
        tiles = _tiles_covering_bbox(bbox)

        # Build tile data (30x30 pixels, each pixel = 0.1 deg)
        # transform: (lon_start=-120, lat_start=36, pixel_size=0.1deg)
        # bbox rows 0-29 map to lat 36->33; water pixels at rows 5-15 stay within bbox.
        tile_data = np.full((30, 30), 60, dtype=np.uint8)
        tile_data[5:15, 5:15] = 200  # permanent water (within bbox coverage)

        transform = Affine(0.1, 0.0, -120.0, 0.0, -0.1, 36.0)
        crs = CRS.from_epsg(4326)

        for lat, lon in tiles:
            fn = _tile_name(lat, lon)
            with MemoryFile() as memfile:
                with memfile.open(
                    driver="GTiff",
                    count=1,
                    dtype="uint8",
                    width=30,
                    height=30,
                    crs=crs,
                    transform=transform,
                ) as dataset:
                    dataset.write(tile_data, 1)
                (tmp_path / fn).write_bytes(memfile.read())

        gdf = build_permanent_water_mask(bbox, tiles_dir=tmp_path, buffer_m=500.0)

        assert len(gdf) > 0, f"Expected water polygons, got empty GDF; check tile fixture"
        # All geometries should be valid
        assert gdf.geometry.is_valid.all()

    def test_no_water_returns_empty_gdf(self, tmp_path: Path) -> None:
        """Grid with no class-200 pixels -> empty GeoDataFrame."""
        import numpy as np
        from affine import Affine
        from rasterio.crs import CRS
        from rasterio.io import MemoryFile

        from subsideo.data.worldcover import (
            _tile_name,
            _tiles_covering_bbox,
            build_permanent_water_mask,
        )

        bbox = (-120.0, 33.0, -117.0, 36.0)
        tiles = _tiles_covering_bbox(bbox)
        tile_data = np.full((30, 30), 60, dtype=np.uint8)  # all class 60, no water

        transform = Affine(0.1, 0.0, -120.0, 0.0, -0.1, 36.0)
        crs = CRS.from_epsg(4326)

        for lat, lon in tiles:
            fn = _tile_name(lat, lon)
            with MemoryFile() as memfile:
                with memfile.open(
                    driver="GTiff",
                    count=1,
                    dtype="uint8",
                    width=30,
                    height=30,
                    crs=crs,
                    transform=transform,
                ) as dataset:
                    dataset.write(tile_data, 1)
                (tmp_path / fn).write_bytes(memfile.read())

        gdf = build_permanent_water_mask(bbox, tiles_dir=tmp_path, buffer_m=500.0)
        assert len(gdf) == 0
