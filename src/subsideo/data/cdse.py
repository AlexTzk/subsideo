"""CDSE (Copernicus Data Space Ecosystem) data access client.

Provides OAuth2 authentication, STAC 1.1.0 catalog search for Sentinel-1/2,
and S3 download from the CDSE ``s3://eodata/`` bucket with exponential-backoff retry.

CDSE uses a **non-standard S3 endpoint** -- the #1 integration gotcha.
All boto3 S3 calls are centralised in :meth:`CDSEClient._s3_client` to
ensure ``endpoint_url`` and ``region_name`` are never omitted.
"""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from loguru import logger
from oauthlib.oauth2 import BackendApplicationClient
from pystac_client import Client
from requests_oauthlib import OAuth2Session

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------
CDSE_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu"
    "/auth/realms/CDSE/protocol/openid-connect/token"
)
CDSE_STAC_URL = "https://stac.dataspace.copernicus.eu/v1"
CDSE_S3_ENDPOINT = "https://eodata.dataspace.copernicus.eu"


class CDSEClient:
    """Unified client for CDSE OAuth2, STAC search, and S3 download.

    Parameters
    ----------
    client_id:
        CDSE OAuth2 client ID (also used as S3 access key).
    client_secret:
        CDSE OAuth2 client secret (also used as S3 secret key).
    """

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    def _get_token(self) -> str:
        """Fetch an OAuth2 access token using client-credentials flow (D-02).

        Uses ``requests_oauthlib.OAuth2Session`` with
        ``oauthlib.oauth2.BackendApplicationClient`` -- never a raw
        ``requests.post``.
        """
        client = BackendApplicationClient(client_id=self._client_id)
        oauth = OAuth2Session(client=client)
        token = oauth.fetch_token(
            token_url=CDSE_TOKEN_URL,
            client_id=self._client_id,
            client_secret=self._client_secret,
        )
        return token["access_token"]

    def _s3_client(self):
        """Return a boto3 S3 client configured for the CDSE endpoint.

        This is the **only** place ``boto3.client("s3")`` is called.
        The CDSE S3 endpoint is non-standard -- omitting ``endpoint_url``
        or ``region_name`` will silently redirect to AWS us-east-1.
        """
        return boto3.client(
            "s3",
            endpoint_url=CDSE_S3_ENDPOINT,
            region_name="default",
            aws_access_key_id=self._client_id,
            aws_secret_access_key=self._client_secret,
        )

    # ------------------------------------------------------------------
    # STAC search
    # ------------------------------------------------------------------
    def search_stac(
        self,
        collection: str,
        bbox: list[float],
        start: datetime,
        end: datetime,
        product_type: str | None = None,
        max_items: int | None = None,
    ) -> list[dict]:
        """Search the CDSE STAC 1.1.0 catalog.

        Parameters
        ----------
        collection:
            STAC collection name, e.g. ``"SENTINEL-1"`` or ``"SENTINEL-2"``.
        bbox:
            Bounding box ``[west, south, east, north]`` in WGS-84.
        start, end:
            Temporal search window.
        product_type:
            Optional product type filter, e.g. ``"IW_SLC__1S"``.
        max_items:
            Maximum number of items to return.

        Returns
        -------
        list[dict]
            STAC item dicts.
        """
        catalog = Client.open(CDSE_STAC_URL)

        search_kwargs: dict = {
            "collections": [collection],
            "bbox": bbox,
            "datetime": f"{start.isoformat()}Z/{end.isoformat()}Z",
        }

        if product_type is not None:
            search_kwargs["query"] = {"productType": {"eq": product_type}}

        if max_items is not None:
            search_kwargs["max_items"] = max_items

        logger.debug("CDSE STAC search: {}", search_kwargs)
        results = catalog.search(**search_kwargs)
        return list(results.items_as_dicts())

    # ------------------------------------------------------------------
    # S3 download
    # ------------------------------------------------------------------
    def download(
        self,
        s3_path: str,
        output_path: Path,
        max_retries: int = 5,
    ) -> Path:
        """Download a file from ``s3://eodata/`` with exponential-backoff retry.

        Parameters
        ----------
        s3_path:
            Full S3 URI, e.g. ``"s3://eodata/Sentinel-1/IW/SLC/test.zip"``.
        output_path:
            Local destination path.
        max_retries:
            Maximum number of download attempts.

        Returns
        -------
        Path
            The *output_path* on success.

        Raises
        ------
        RuntimeError
            If all retry attempts are exhausted.
        """
        # Parse s3://bucket/key
        stripped = s3_path.removeprefix("s3://")
        bucket, key = stripped.split("/", 1)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        s3 = self._s3_client()
        for attempt in range(max_retries):
            try:
                s3.download_file(bucket, key, str(output_path))
                logger.info("Downloaded {} -> {}", s3_path, output_path)
                return output_path
            except ClientError as exc:
                wait = min(2**attempt, 60)
                logger.warning(
                    "CDSE S3 download attempt {}/{} failed: {}. Retrying in {}s",
                    attempt + 1,
                    max_retries,
                    exc,
                    wait,
                )
                time.sleep(wait)

        msg = f"CDSE S3 download failed after {max_retries} retries: {s3_path}"
        raise RuntimeError(msg)
