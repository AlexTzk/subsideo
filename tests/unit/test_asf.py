"""Unit tests for subsideo.data.asf -- mocked asf-search and earthaccess."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from subsideo.data.asf import ASFClient


@pytest.fixture()
def client():
    return ASFClient(username="testuser", password="testpass")


@pytest.fixture()
def mock_asf_results():
    """Create mock asf_search result objects with .properties dict."""
    r1 = MagicMock()
    r1.properties = {"id": "granule_1", "url": "https://example.com/g1.zip"}
    r2 = MagicMock()
    r2.properties = {"id": "granule_2", "url": "https://example.com/g2.zip"}
    return [r1, r2]


class TestASFClientSearch:
    """Tests for ASFClient.search()."""

    def test_passes_short_name(self, mocker, client, mock_asf_results):
        mock_search = mocker.patch("subsideo.data.asf.asf.search", return_value=mock_asf_results)
        client.search(
            "OPERA_L2_RTC-S1_V1",
            [10, 44, 12, 46],
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        assert mock_search.call_args.kwargs["shortName"] == "OPERA_L2_RTC-S1_V1"

    def test_formats_bbox_as_polygon(self, mocker, client, mock_asf_results):
        mock_search = mocker.patch("subsideo.data.asf.asf.search", return_value=mock_asf_results)
        client.search(
            "OPERA_L2_RTC-S1_V1",
            [10, 44, 12, 46],
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        wkt = mock_search.call_args.kwargs["intersectsWith"]
        assert "POLYGON" in wkt
        assert "10 44" in wkt
        assert "12 46" in wkt

    def test_returns_properties_list(self, mocker, client, mock_asf_results):
        mocker.patch("subsideo.data.asf.asf.search", return_value=mock_asf_results)
        results = client.search(
            "OPERA_L2_RTC-S1_V1",
            [10, 44, 12, 46],
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
        )
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, dict) for r in results)
        assert results[0]["id"] == "granule_1"

    def test_passes_max_results(self, mocker, client, mock_asf_results):
        mock_search = mocker.patch("subsideo.data.asf.asf.search", return_value=mock_asf_results)
        client.search(
            "OPERA_L2_RTC-S1_V1",
            [10, 44, 12, 46],
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
            max_results=50,
        )
        assert mock_search.call_args.kwargs["maxResults"] == 50

    def test_passes_start_end_iso(self, mocker, client, mock_asf_results):
        mock_search = mocker.patch("subsideo.data.asf.asf.search", return_value=mock_asf_results)
        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 31, 23, 59, 59)
        client.search("OPERA_L2_RTC-S1_V1", [10, 44, 12, 46], start, end)
        assert mock_search.call_args.kwargs["start"] == start.isoformat()
        assert mock_search.call_args.kwargs["end"] == end.isoformat()


class TestASFClientDownload:
    """Tests for ASFClient.download()."""

    def test_calls_earthaccess_download(self, mocker, client, tmp_path):
        mocker.patch("subsideo.data.asf.earthaccess.login")
        mock_dl = mocker.patch(
            "subsideo.data.asf.earthaccess.download",
            return_value=[str(tmp_path / "g1.zip"), str(tmp_path / "g2.zip")],
        )
        urls = ["https://example.com/g1.zip", "https://example.com/g2.zip"]
        client.download(urls, tmp_path)
        mock_dl.assert_called_once_with(urls, local_path=str(tmp_path))

    def test_creates_output_dir(self, mocker, client, tmp_path):
        mocker.patch("subsideo.data.asf.earthaccess.login")
        mocker.patch("subsideo.data.asf.earthaccess.download", return_value=[])
        out_dir = tmp_path / "nested" / "downloads"
        client.download([], out_dir)
        assert out_dir.exists()

    def test_returns_list_of_paths(self, mocker, client, tmp_path):
        mocker.patch("subsideo.data.asf.earthaccess.login")
        mocker.patch(
            "subsideo.data.asf.earthaccess.download",
            return_value=[str(tmp_path / "g1.zip")],
        )
        result = client.download(["https://example.com/g1.zip"], tmp_path)
        assert isinstance(result, list)
        assert all(isinstance(p, Path) for p in result)

    def test_login_called_before_download(self, mocker, client, tmp_path):
        """Verify _login() is called so earthaccess session is authenticated."""
        mock_login = mocker.patch("subsideo.data.asf.earthaccess.login")
        mocker.patch("subsideo.data.asf.earthaccess.download", return_value=[])
        client.download([], tmp_path)
        mock_login.assert_called_once()
