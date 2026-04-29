"""Unit tests for subsideo.data.orbits -- mocked sentineleof and s1-orbits."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from subsideo.data.orbits import fetch_orbit


@pytest.fixture()
def sensing_time():
    return datetime(2024, 1, 15, 6, 30, 0)


class TestFetchOrbit:
    """Tests for fetch_orbit()."""

    def test_uses_sentineleof_primary(self, mocker, tmp_path, sensing_time):
        mock_dl = mocker.patch(
            "eof.download.download_eofs",
            return_value=[str(tmp_path / "orbit.EOF")],
        )
        result = fetch_orbit(sensing_time, "S1A", tmp_path)
        mock_dl.assert_called_once()
        assert result == Path(tmp_path / "orbit.EOF")

    def test_precise_orbit_type(self, mocker, tmp_path, sensing_time):
        mock_dl = mocker.patch(
            "eof.download.download_eofs",
            return_value=[str(tmp_path / "orbit.EOF")],
        )
        fetch_orbit(sensing_time, "S1A", tmp_path)
        assert mock_dl.call_args.kwargs["orbit_type"] == "precise"

    def test_fallback_to_asf_on_esa_failure(self, mocker, tmp_path, sensing_time):
        fallback_path = str(tmp_path / "fallback.EOF")
        mock_dl = mocker.patch(
            "eof.download.download_eofs",
            side_effect=[ConnectionError("POD hub down"), [fallback_path]],
        )
        result = fetch_orbit(sensing_time, "S1A", tmp_path)
        assert mock_dl.call_count == 2
        assert mock_dl.call_args_list[1].kwargs.get("force_asf") is True
        assert result == Path(tmp_path / "fallback.EOF")

    def test_creates_output_dir(self, mocker, tmp_path, sensing_time):
        mocker.patch(
            "eof.download.download_eofs",
            return_value=[str(tmp_path / "orbit.EOF")],
        )
        out_dir = tmp_path / "nested" / "orbits"
        fetch_orbit(sensing_time, "S1A", out_dir)
        assert out_dir.exists()

    def test_passes_satellite_as_mission(self, mocker, tmp_path, sensing_time):
        mock_dl = mocker.patch(
            "eof.download.download_eofs",
            return_value=[str(tmp_path / "orbit.EOF")],
        )
        fetch_orbit(sensing_time, "S1B", tmp_path)
        assert mock_dl.call_args.kwargs["missions"] == ["S1B"]
