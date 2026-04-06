"""Unit tests for CDSEClient -- CDSE STAC search and S3 download.

All tests mock network calls (no real CDSE access).
Uses pytest-mock to stub OAuth2Session, boto3.client, and pystac_client.Client.
Do NOT use moto -- moto cannot intercept CDSE's custom S3 endpoint.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from subsideo.data.cdse import (
    CDSE_S3_ENDPOINT,
    CDSE_STAC_URL,
    CDSE_TOKEN_URL,
    CDSEClient,
)


class TestCDSEClientInit:
    """Construction and credential validation."""

    def test_init_stores_credentials(self):
        client = CDSEClient("my_id", "my_secret")
        assert client._client_id == "my_id"
        assert client._client_secret == "my_secret"

    def test_init_does_not_fetch_token(self, mocker):
        """OAuth2 is lazy -- no token fetched at construction time."""
        mock_oauth = mocker.patch("subsideo.data.cdse.OAuth2Session")
        CDSEClient("id", "secret")
        mock_oauth.assert_not_called()



class TestOAuth2:
    """Token fetch uses requests-oauthlib with BackendApplicationClient (D-02)."""

    def test_oauth2_uses_backend_application_client(self, mocker):
        mock_bac = mocker.patch("subsideo.data.cdse.BackendApplicationClient")
        mock_session_cls = mocker.patch("subsideo.data.cdse.OAuth2Session")
        mock_session = MagicMock()
        mock_session.fetch_token.return_value = {"access_token": "tok123"}
        mock_session_cls.return_value = mock_session

        client = CDSEClient("test_id", "test_secret")
        token = client._get_token()

        mock_bac.assert_called_once_with(client_id="test_id")
        mock_session_cls.assert_called_once_with(client=mock_bac.return_value)
        mock_session.fetch_token.assert_called_once_with(
            token_url=CDSE_TOKEN_URL,
            client_id="test_id",
            client_secret="test_secret",
        )
        assert token == "tok123"


class TestSearchStac:
    """STAC search for Sentinel-1 and Sentinel-2 collections."""

    def test_search_stac_sentinel1(self, mocker):
        """DATA-01: S1 IW SLC search uses collection='SENTINEL-1'."""
        mock_item = {
            "id": "S1A_IW_SLC_20230601",
            "assets": {"data": {"href": "s3://eodata/Sentinel-1/IW/SLC/test.zip"}},
        }
        mock_catalog = mocker.patch("subsideo.data.cdse.Client.open")
        mock_search = mock_catalog.return_value.search.return_value
        mock_search.items_as_dicts.return_value = [mock_item]

        client = CDSEClient("test_id", "test_secret")
        results = client.search_stac(
            "SENTINEL-1",
            [9.5, 44.5, 12.5, 45.5],
            datetime(2023, 6, 1),
            datetime(2023, 6, 2),
            product_type="IW_SLC__1S",
        )

        assert len(results) == 1
        assert results[0]["id"] == "S1A_IW_SLC_20230601"

        # Verify STAC URL
        mock_catalog.assert_called_once_with(CDSE_STAC_URL)

        # Verify search params
        call_kwargs = mock_catalog.return_value.search.call_args.kwargs
        assert "SENTINEL-1" in call_kwargs["collections"]
        assert call_kwargs["bbox"] == [9.5, 44.5, 12.5, 45.5]

    def test_search_stac_sentinel2(self, mocker):
        """DATA-02: S2 L2A search uses collection='SENTINEL-2' and results reference s3://eodata/Sentinel-2/."""
        mock_item = {
            "id": "S2A_MSIL2A_20230601T100000",
            "assets": {
                "data": {
                    "href": "s3://eodata/Sentinel-2/MSI/L2A/2023/06/01/test.SAFE"
                }
            },
        }
        mock_catalog = mocker.patch("subsideo.data.cdse.Client.open")
        mock_search = mock_catalog.return_value.search.return_value
        mock_search.items_as_dicts.return_value = [mock_item]

        client = CDSEClient("test_id", "test_secret")
        results = client.search_stac(
            "SENTINEL-2",
            [9.5, 44.5, 12.5, 45.5],
            datetime(2023, 6, 1),
            datetime(2023, 6, 2),
        )

        assert len(results) == 1
        call_kwargs = mock_catalog.return_value.search.call_args.kwargs
        assert "SENTINEL-2" in call_kwargs["collections"]
        assert "Sentinel-2" in results[0]["assets"]["data"]["href"]

    def test_search_stac_passes_max_items(self, mocker):
        """max_items is forwarded to the STAC search."""
        mock_catalog = mocker.patch("subsideo.data.cdse.Client.open")
        mock_search = mock_catalog.return_value.search.return_value
        mock_search.items_as_dicts.return_value = []

        client = CDSEClient("id", "secret")
        client.search_stac(
            "SENTINEL-1",
            [0, 0, 1, 1],
            datetime(2023, 1, 1),
            datetime(2023, 1, 2),
            max_items=10,
        )

        call_kwargs = mock_catalog.return_value.search.call_args.kwargs
        assert call_kwargs["max_items"] == 10


class TestDownload:
    """S3 download with correct endpoint, retry, and path parsing."""

    def test_download_calls_correct_endpoint(self, mocker, tmp_path):
        """boto3 S3 client uses CDSE custom endpoint + region_name='default'."""
        mock_s3 = mocker.patch("subsideo.data.cdse.boto3.client")
        mock_s3.return_value.download_file.return_value = None

        client = CDSEClient("test_id", "test_secret")
        result = client.download(
            "s3://eodata/Sentinel-1/test.zip", tmp_path / "out.zip"
        )

        mock_s3.assert_called_once_with(
            "s3",
            endpoint_url="https://eodata.dataspace.copernicus.eu",
            region_name="default",
            aws_access_key_id="test_id",
            aws_secret_access_key="test_secret",
        )
        mock_s3.return_value.download_file.assert_called_once_with(
            "eodata", "Sentinel-1/test.zip", str(tmp_path / "out.zip")
        )
        assert result == tmp_path / "out.zip"

    def test_download_s2_path(self, mocker, tmp_path):
        """S2 S3 paths are parsed correctly (bucket=eodata, key=Sentinel-2/...)."""
        mock_s3 = mocker.patch("subsideo.data.cdse.boto3.client")
        mock_s3.return_value.download_file.return_value = None

        client = CDSEClient("id", "secret")
        client.download(
            "s3://eodata/Sentinel-2/MSI/L2A/test.zip", tmp_path / "s2.zip"
        )

        mock_s3.return_value.download_file.assert_called_once_with(
            "eodata", "Sentinel-2/MSI/L2A/test.zip", str(tmp_path / "s2.zip")
        )

    def test_download_creates_parent_dirs(self, mocker, tmp_path):
        """Parent directories are created if they don't exist."""
        mock_s3 = mocker.patch("subsideo.data.cdse.boto3.client")
        mock_s3.return_value.download_file.return_value = None

        nested = tmp_path / "a" / "b" / "c" / "out.zip"
        client = CDSEClient("id", "secret")
        client.download("s3://eodata/test.zip", nested)

        assert nested.parent.exists()

    def test_download_retry_on_client_error(self, mocker, tmp_path):
        """ClientError triggers retry with eventual success."""
        mock_s3 = mocker.patch("subsideo.data.cdse.boto3.client")
        mocker.patch("subsideo.data.cdse.time.sleep")  # skip actual sleeping

        error_resp = {"Error": {"Code": "503", "Message": "Slow Down"}}
        mock_s3.return_value.download_file.side_effect = [
            ClientError(error_resp, "download_file"),
            ClientError(error_resp, "download_file"),
            None,  # success on 3rd attempt
        ]

        client = CDSEClient("id", "secret")
        result = client.download(
            "s3://eodata/test.zip", tmp_path / "out.zip", max_retries=5
        )
        assert result == tmp_path / "out.zip"
        assert mock_s3.return_value.download_file.call_count == 3

    def test_download_raises_after_max_retries(self, mocker, tmp_path):
        """Exhausted retries raise RuntimeError."""
        mock_s3 = mocker.patch("subsideo.data.cdse.boto3.client")
        mocker.patch("subsideo.data.cdse.time.sleep")

        error_resp = {"Error": {"Code": "503", "Message": "Slow Down"}}
        mock_s3.return_value.download_file.side_effect = ClientError(
            error_resp, "download_file"
        )

        client = CDSEClient("id", "secret")
        with pytest.raises(RuntimeError, match="failed after 3 retries"):
            client.download(
                "s3://eodata/test.zip", tmp_path / "out.zip", max_retries=3
            )


class TestConstants:
    """Module-level constants are correct."""

    def test_stac_url(self):
        assert CDSE_STAC_URL == "https://stac.dataspace.copernicus.eu/v1"

    def test_s3_endpoint(self):
        assert CDSE_S3_ENDPOINT == "https://eodata.dataspace.copernicus.eu"

    def test_token_url(self):
        assert CDSE_TOKEN_URL == (
            "https://identity.dataspace.copernicus.eu"
            "/auth/realms/CDSE/protocol/openid-connect/token"
        )
