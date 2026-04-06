"""Unit tests for DSWx-S2 JRC comparison helper functions."""
from __future__ import annotations

import numpy as np
import pytest

from subsideo.validation.compare_dswx import (
    JRC_BASE_URL,
    _binarize_dswx,
    _binarize_jrc,
    _jrc_tile_url,
    _lonlat_to_jrc_tile,
    _tiles_for_bounds,
)


class TestJrcTileUrl:
    """Test JRC Monthly History tile URL construction."""

    def test_url_format(self):
        url = _jrc_tile_url(2024, 6, 2, 3)
        assert "2024" in url
        assert "2024_06" in url
        assert "0000080000-0000120000.tif" in url
        assert url.startswith(JRC_BASE_URL)

    def test_url_zero_indices(self):
        url = _jrc_tile_url(2020, 1, 0, 0)
        assert "0000000000-0000000000.tif" in url
        assert "2020_01" in url

    def test_url_single_digit_month_padded(self):
        url = _jrc_tile_url(2023, 3, 1, 1)
        assert "2023_03" in url


class TestLonlatToJrcTile:
    """Test coordinate to tile index conversion."""

    def test_netherlands(self):
        # lon=5, lat=52 -> tile covering Netherlands
        # tile_x = int((5 - (-180)) / 10) = int(185/10) = 18
        # tile_y = int((80 - 52) / 10) = int(28/10) = 2
        tx, ty = _lonlat_to_jrc_tile(5.0, 52.0)
        assert tx == 18
        assert ty == 2

    def test_origin(self):
        # lon=-180, lat=80 -> tile (0, 0)
        tx, ty = _lonlat_to_jrc_tile(-180.0, 80.0)
        assert tx == 0
        assert ty == 0

    def test_positive_lon(self):
        # lon=10, lat=45
        tx, ty = _lonlat_to_jrc_tile(10.0, 45.0)
        assert tx == 19  # (10 + 180) / 10 = 19
        assert ty == 3   # (80 - 45) / 10 = 3


class TestBinarizeDswx:
    """Test DSWx water classification binarization."""

    def test_class_mapping(self):
        arr = np.array([0, 1, 2, 3, 4, 255], dtype=np.uint8)
        result = _binarize_dswx(arr)
        assert result[0] == 0.0   # class 0 -> not water
        assert result[1] == 1.0   # class 1 -> water
        assert result[2] == 1.0   # class 2 -> water
        assert result[3] == 0.0   # class 3 -> not water
        assert result[4] == 0.0   # class 4 -> not water
        assert np.isnan(result[5])  # 255 -> NaN

    def test_output_dtype(self):
        arr = np.array([0, 1, 2], dtype=np.uint8)
        result = _binarize_dswx(arr)
        assert result.dtype == np.float32


class TestBinarizeJrc:
    """Test JRC water classification binarization."""

    def test_class_mapping(self):
        arr = np.array([0, 1, 2], dtype=np.uint8)
        result = _binarize_jrc(arr)
        assert np.isnan(result[0])  # 0 -> nodata -> NaN
        assert result[1] == 0.0     # 1 -> not water
        assert result[2] == 1.0     # 2 -> water

    def test_output_dtype(self):
        arr = np.array([1, 2], dtype=np.uint8)
        result = _binarize_jrc(arr)
        assert result.dtype == np.float32


class TestTilesForBounds:
    """Test bounding box to tile set conversion."""

    def test_single_tile(self):
        # Small bbox within one tile
        tiles = _tiles_for_bounds(4.0, 51.0, 6.0, 53.0)
        assert len(tiles) >= 1
        assert (18, 2) in tiles  # Netherlands tile

    def test_multi_tile(self):
        # Bbox spanning two tiles in longitude
        tiles = _tiles_for_bounds(-1.0, 51.0, 11.0, 53.0)
        # Should cover tiles from lon -1 (tile 17) to lon 11 (tile 19)
        tile_xs = {t[0] for t in tiles}
        assert 17 in tile_xs
        assert 18 in tile_xs
        assert 19 in tile_xs
