"""Unit tests for subsideo.data.dem -- mocked dem-stitcher and rasterio."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from subsideo.data.dem import fetch_dem


@pytest.fixture()
def _mock_stitch(mocker):
    """Mock stitch_dem to return a small array and a fake rasterio profile."""
    fake_data = np.ones((10, 10), dtype=np.float32)
    fake_profile = {
        "crs": "EPSG:4326",
        "transform": MagicMock(),
        "width": 10,
        "height": 10,
        "count": 1,
        "dtype": "float32",
    }
    mocker.patch("subsideo.data.dem.stitch_dem", return_value=(fake_data, fake_profile))
    return fake_data, fake_profile


@pytest.fixture()
def _mock_rasterio(mocker):
    """Mock rasterio.open, calculate_default_transform, and reproject."""
    mock_transform = MagicMock()
    mocker.patch(
        "subsideo.data.dem.calculate_default_transform",
        return_value=(mock_transform, 20, 20),
    )
    mocker.patch("subsideo.data.dem.reproject")
    mocker.patch("subsideo.data.dem.rasterio.band", return_value=MagicMock())

    mock_file = MagicMock()
    mock_open = mocker.patch("subsideo.data.dem.rasterio.open", return_value=mock_file)
    mock_file.__enter__ = MagicMock(return_value=mock_file)
    mock_file.__exit__ = MagicMock(return_value=False)
    return mock_open


@pytest.mark.usefixtures("_mock_stitch", "_mock_rasterio")
class TestFetchDem:
    """Tests for fetch_dem()."""

    def test_calls_stitch_dem_with_glo30(self, mocker, tmp_path):
        from subsideo.data.dem import stitch_dem as patched_stitch

        fetch_dem([10, 44, 12, 46], 32632, tmp_path)
        patched_stitch.assert_called_once()
        call_kwargs = patched_stitch.call_args
        assert call_kwargs.args[0] == [10, 44, 12, 46]
        assert call_kwargs.kwargs["dem_name"] == "glo_30"
        assert call_kwargs.kwargs["dst_ellipsoidal_height"] is True

    def test_creates_output_dir(self, tmp_path):
        out_dir = tmp_path / "subdir" / "nested"
        fetch_dem([10, 44, 12, 46], 32632, out_dir)
        assert out_dir.exists()

    def test_warps_to_correct_epsg(self, mocker, tmp_path):
        from subsideo.data.dem import calculate_default_transform as patched_cdt

        fetch_dem([10, 44, 12, 46], 32632, tmp_path)
        call_args = patched_cdt.call_args
        # Second positional arg should be the target CRS
        from rasterio.crs import CRS

        assert call_args.args[1] == CRS.from_epsg(32632)

    def test_output_filename_contains_epsg(self, tmp_path):
        path, _ = fetch_dem([10, 44, 12, 46], 32632, tmp_path)
        assert "32632" in path.name

    def test_returns_tuple_of_path_and_profile(self, tmp_path):
        result = fetch_dem([10, 44, 12, 46], 32632, tmp_path)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], Path)
        assert isinstance(result[1], dict)

    def test_pixel_centre_convention(self, mocker, tmp_path):
        from subsideo.data.dem import stitch_dem as patched_stitch

        fetch_dem([10, 44, 12, 46], 32632, tmp_path)
        assert patched_stitch.call_args.kwargs["dst_area_or_point"] == "Point"
