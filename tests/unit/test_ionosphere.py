"""Unit tests for subsideo.data.ionosphere -- mocked CDDIS HTTP calls."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest
import requests

from subsideo.data.ionosphere import fetch_ionex


@pytest.fixture()
def mock_response():
    """Create a mock requests response with fake IONEX data."""
    resp = MagicMock()
    resp.content = b"fake ionex compressed data"
    resp.raise_for_status.return_value = None
    return resp


class TestFetchIonex:
    """Tests for fetch_ionex()."""

    def test_constructs_correct_url(self, mocker, tmp_path, mock_response):
        mock_get = mocker.patch(
            "subsideo.data.ionosphere.requests.get", return_value=mock_response
        )
        # 2023-06-01 is day-of-year 152
        fetch_ionex(date(2023, 6, 1), tmp_path, "user", "pass")
        called_url = mock_get.call_args.args[0]
        assert "cddis.nasa.gov/archive/gnss/products/ionex/2023/152" in called_url
        assert "igsg1520.23i.Z" in called_url

    def test_uses_basic_auth(self, mocker, tmp_path, mock_response):
        mock_get = mocker.patch(
            "subsideo.data.ionosphere.requests.get", return_value=mock_response
        )
        fetch_ionex(date(2023, 6, 1), tmp_path, "myuser", "mypass")
        assert mock_get.call_args.kwargs["auth"] == ("myuser", "mypass")

    def test_writes_file(self, mocker, tmp_path, mock_response):
        mocker.patch("subsideo.data.ionosphere.requests.get", return_value=mock_response)
        result = fetch_ionex(date(2023, 6, 1), tmp_path, "user", "pass")
        assert result.exists()
        assert result.read_bytes() == b"fake ionex compressed data"

    def test_raises_on_http_error(self, mocker, tmp_path):
        error_resp = MagicMock()
        error_resp.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")
        mocker.patch("subsideo.data.ionosphere.requests.get", return_value=error_resp)
        with pytest.raises(requests.HTTPError, match="401"):
            fetch_ionex(date(2023, 6, 1), tmp_path, "user", "badpass")

    def test_creates_output_dir(self, mocker, tmp_path, mock_response):
        mocker.patch("subsideo.data.ionosphere.requests.get", return_value=mock_response)
        out_dir = tmp_path / "nested" / "ionex"
        fetch_ionex(date(2023, 6, 1), out_dir, "user", "pass")
        assert out_dir.exists()

    def test_doy_zero_padding(self, mocker, tmp_path, mock_response):
        """Jan 5 = DOY 005 -- verify 3-digit zero padding."""
        mock_get = mocker.patch(
            "subsideo.data.ionosphere.requests.get", return_value=mock_response
        )
        fetch_ionex(date(2024, 1, 5), tmp_path, "user", "pass")
        called_url = mock_get.call_args.args[0]
        assert "/005/" in called_url
        assert "igsg0050.24i.Z" in called_url

    def test_returns_path_with_correct_filename(self, mocker, tmp_path, mock_response):
        mocker.patch("subsideo.data.ionosphere.requests.get", return_value=mock_response)
        result = fetch_ionex(date(2023, 6, 1), tmp_path, "user", "pass")
        assert result.name == "igsg1520.23i.Z"
