"""CDSE (Copernicus Data Space Ecosystem) data access client.

Provides OAuth2 authentication, STAC 1.1.0 catalog search for Sentinel-1/2,
and S3 download from the CDSE ``s3://eodata/`` bucket with exponential-backoff retry.

CDSE uses a **non-standard S3 endpoint** -- the #1 integration gotcha.
All boto3 S3 calls are centralised in :meth:`CDSEClient._s3_client` to
ensure ``endpoint_url`` and ``region_name`` are never omitted.
"""
from __future__ import annotations

import os
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

# Legacy (collection, product_type) → new per-product CDSE STAC collection.
# The CDSE STAC catalogue was restructured in Feb 2025 (STAC 1.1.0 rollout):
# the single "SENTINEL-1"/"SENTINEL-2" collections + productType filter were
# replaced with per-product-type collections. Callers still pass the legacy
# pair so we map here and keep the public API stable.
_LEGACY_COLLECTION_MAP: dict[tuple[str, str | None], str] = {
    ("SENTINEL-1", "IW_SLC__1S"): "sentinel-1-slc",
    ("SENTINEL-1", "IW_GRDH_1S"): "sentinel-1-grd",
    ("SENTINEL-1", "GRD"): "sentinel-1-grd",
    ("SENTINEL-2", "S2MSI2A"): "sentinel-2-l2a",
    ("SENTINEL-2", "S2MSI1C"): "sentinel-2-l1c",
    # Fallbacks when no product_type was supplied: default to the most-used
    # product level for each mission (SLC for S1, L2A for S2).
    ("SENTINEL-1", None): "sentinel-1-slc",
    ("SENTINEL-2", None): "sentinel-2-l2a",
}


def _resolve_collection(collection: str, product_type: str | None) -> str:
    """Return the concrete CDSE STAC collection ID for a legacy pair.

    Passes through already-resolved IDs (anything lowercase containing a dash)
    unchanged so new callers can use the native names directly.
    """
    if "-" in collection and collection.islower():
        return collection
    resolved = _LEGACY_COLLECTION_MAP.get((collection, product_type))
    if resolved is None:
        raise ValueError(
            f"No CDSE STAC mapping for collection={collection!r} "
            f"product_type={product_type!r}. Known legacy pairs: "
            f"{sorted(_LEGACY_COLLECTION_MAP.keys())}"
        )
    return resolved


def extract_safe_s3_prefix(item: dict) -> str | None:
    """Derive the ``s3://eodata/.../<scene>.SAFE`` prefix from a STAC item.

    The new CDSE STAC catalogue publishes per-swath/per-polarisation assets
    (e.g. ``iw1-vv``, ``iw2-vv``, ``safe_manifest``) whose S3 hrefs point
    into ``<scene>.SAFE/measurement/*.tiff`` or
    ``<scene>.SAFE/manifest.safe``. The SAFE root is the longest
    ``s3://...`` prefix ending in ``.SAFE`` shared by those assets.

    Returns ``None`` if no S3 asset is found.
    """
    assets = item.get("assets") or {}
    for asset in assets.values():
        href = (asset or {}).get("href", "")
        if not href.startswith("s3://"):
            continue
        marker = ".SAFE/"
        idx = href.find(marker)
        if idx != -1:
            return href[: idx + len(".SAFE")]
        if href.endswith(".SAFE"):
            return href
    return None


class CDSEClient:
    """Unified client for CDSE OAuth2, STAC search, and S3 download.

    Parameters
    ----------
    client_id:
        CDSE OAuth2 client ID (used for STAC search and OData token auth).
    client_secret:
        CDSE OAuth2 client secret.
    s3_access_key, s3_secret_key:
        CDSE S3 access key pair, **separate** from the OAuth2 credentials.
        Created at https://eodata-s3keysmanager.dataspace.copernicus.eu/.
        Falls back to the ``CDSE_S3_ACCESS_KEY`` / ``CDSE_S3_SECRET_KEY``
        environment variables when omitted. Only required for S3 download
        paths; STAC search works without S3 credentials.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        s3_access_key: str | None = None,
        s3_secret_key: str | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._s3_access_key = s3_access_key or os.environ.get("CDSE_S3_ACCESS_KEY")
        self._s3_secret_key = s3_secret_key or os.environ.get("CDSE_S3_SECRET_KEY")

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

        Uses the dedicated CDSE S3 access keys, which are **not** the
        same as the OAuth2 client credentials. Raises ``RuntimeError``
        with setup instructions if the S3 keys are missing.
        """
        if not (self._s3_access_key and self._s3_secret_key):
            raise RuntimeError(
                "CDSE S3 access keys are missing. CDSE S3 download requires "
                "a dedicated key pair, separate from the OAuth client "
                "credentials. Create one at "
                "https://eodata-s3keysmanager.dataspace.copernicus.eu/ and "
                "set CDSE_S3_ACCESS_KEY / CDSE_S3_SECRET_KEY in your .env."
            )
        return boto3.client(
            "s3",
            endpoint_url=CDSE_S3_ENDPOINT,
            region_name="default",
            aws_access_key_id=self._s3_access_key,
            aws_secret_access_key=self._s3_secret_key,
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
        resolved_collection = _resolve_collection(collection, product_type)
        catalog = Client.open(CDSE_STAC_URL)

        search_kwargs: dict = {
            "collections": [resolved_collection],
            "bbox": bbox,
            "datetime": f"{start.isoformat()}Z/{end.isoformat()}Z",
        }

        if max_items is not None:
            search_kwargs["max_items"] = max_items

        logger.debug("CDSE STAC search: {}", search_kwargs)

        # CDSE's anonymous STAC endpoint is fronted by a WAF that throttles
        # aggressive pagination with HTTP 429. Materialise pages with a
        # backoff-retry loop rather than blowing up on the first 429.
        from pystac_client.exceptions import APIError

        # Transient CDSE backend faults we should retry:
        #  - HTTP 429 / Rate limit (WAF pagination throttling)
        #  - Postgres "OutOfMemoryError" raised by the STAC backend under
        #    load — CDSE intermittently returns these even for small
        #    queries and they clear within ~minute.
        transient_markers = ("429", "Rate limit", "OutOfMemoryError", "out of memory")
        max_attempts = 8
        for attempt in range(max_attempts):
            try:
                results = catalog.search(**search_kwargs)
                return list(results.items_as_dicts())
            except APIError as exc:
                msg = str(exc)
                if not any(m in msg for m in transient_markers):
                    raise
                # Exponential backoff capped at 5 minutes.
                wait = min(2 ** (attempt + 2), 300)
                fault = "OOM" if "memory" in msg.lower() else "429"
                logger.warning(
                    "CDSE STAC {} (attempt {}/{}), retrying in {}s",
                    fault,
                    attempt + 1,
                    max_attempts,
                    wait,
                )
                time.sleep(wait)
        raise RuntimeError(
            "CDSE STAC search exhausted retries (WAF 429 / backend OOM)"
        )

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

    def download_safe(
        self,
        safe_s3_prefix: str,
        output_root: Path,
        max_retries: int = 5,
    ) -> Path:
        """Download a complete S1 SAFE directory tree from CDSE S3.

        The CDSE STAC catalogue (Feb 2025 STAC 1.1.0 rollout) no longer
        publishes ``<scene>.zip`` siblings of the SAFE prefix — only the
        unzipped SAFE directory contents are addressable. This helper
        recursively lists all keys under ``safe_s3_prefix`` and mirrors
        them into ``output_root/<scene>.SAFE/``. ``s1reader.load_bursts``
        and compass both accept SAFE directories interchangeably with
        SAFE zips.

        Parameters
        ----------
        safe_s3_prefix:
            ``s3://eodata/.../<scene>.SAFE`` — typically obtained from
            :func:`extract_safe_s3_prefix` on a STAC item.
        output_root:
            Local directory under which ``<scene>.SAFE/`` will be created.
        max_retries:
            Per-object download retry count.

        Returns
        -------
        Path
            The local ``<scene>.SAFE`` directory.
        """
        if not safe_s3_prefix.startswith("s3://"):
            raise ValueError(f"Not an S3 URI: {safe_s3_prefix!r}")
        stripped = safe_s3_prefix.removeprefix("s3://").rstrip("/")
        bucket, prefix = stripped.split("/", 1)
        scene_safe = prefix.rsplit("/", 1)[-1]
        if not scene_safe.endswith(".SAFE"):
            raise ValueError(
                f"Prefix does not end in .SAFE: {safe_s3_prefix!r}"
            )

        local_safe = output_root / scene_safe
        local_safe.mkdir(parents=True, exist_ok=True)

        s3 = self._s3_client()
        paginator = s3.get_paginator("list_objects_v2")
        raw: list[tuple[str, int]] = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix + "/"):
            for obj in page.get("Contents", []) or []:
                raw.append((obj["Key"], obj.get("Size") or 0))

        if not raw:
            raise RuntimeError(
                f"No objects found under {safe_s3_prefix} (empty SAFE prefix)"
            )

        # Filter out S3 directory markers: zero-byte objects whose key is a
        # prefix of another key in the listing. Without this, iterating the
        # raw listing downloads ``<SAFE>/annotation`` as an empty file and
        # then fails to ``mkdir`` ``<SAFE>/annotation/`` for child XMLs.
        key_set = {k for k, _ in raw}
        def _is_dir_marker(k: str, size: int) -> bool:
            if k.endswith("/"):
                return True
            if size != 0:
                return False
            marker = k + "/"
            return any(other.startswith(marker) for other in key_set if other != k)

        keys = [k for k, sz in raw if not _is_dir_marker(k, sz)]
        skipped = len(raw) - len(keys)

        logger.info(
            "Downloading SAFE {} ({} files{}) -> {}",
            scene_safe,
            len(keys),
            f", {skipped} dir-markers skipped" if skipped else "",
            local_safe,
        )

        for key in keys:
            rel = key[len(prefix) + 1 :]  # path relative to <scene>.SAFE/
            dest = local_safe / rel
            if dest.exists() and dest.stat().st_size > 0:
                continue
            # If a stale zero-byte directory-marker file from a prior
            # partial run is sitting where we now need a directory, remove
            # it so ``mkdir`` below can create the directory.
            for ancestor in list(dest.parents)[:-1]:
                if ancestor == local_safe:
                    break
                if ancestor.is_file():
                    ancestor.unlink()
            dest.parent.mkdir(parents=True, exist_ok=True)
            for attempt in range(max_retries):
                try:
                    s3.download_file(bucket, key, str(dest))
                    break
                except ClientError as exc:
                    wait = min(2**attempt, 60)
                    logger.warning(
                        "SAFE object {} attempt {}/{} failed: {}. "
                        "Retrying in {}s",
                        key,
                        attempt + 1,
                        max_retries,
                        exc,
                        wait,
                    )
                    time.sleep(wait)
            else:
                raise RuntimeError(
                    f"CDSE SAFE download failed for s3://{bucket}/{key} "
                    f"after {max_retries} retries"
                )

        from subsideo.validation.harness import validate_safe_path

        if not validate_safe_path(local_safe):
            raise RuntimeError(f"Downloaded SAFE tree failed integrity validation: {local_safe}")
        return local_safe
