"""ASF DAAC search and download for OPERA N.Am. validation products.

VALIDATION-ONLY -- not used for primary EU data access (D-11).
Uses asf-search for granule discovery and earthaccess for authenticated bulk download.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import asf_search as asf
import earthaccess
from loguru import logger


class ASFClient:
    """Client for ASF DAAC search and download of OPERA N.Am. validation products.

    Uses asf-search for granule discovery and earthaccess for authenticated
    bulk download. Validation-only path -- not used for primary EU data access (D-11).
    """

    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password

    def _login(self) -> None:
        """Authenticate with NASA Earthdata via environment variables."""
        earthaccess.login(strategy="environment")

    def search(
        self,
        short_name: str,
        bbox: list[float],
        start: datetime,
        end: datetime,
        max_results: int = 100,
    ) -> list[dict]:
        """Search ASF DAAC for OPERA reference products.

        Args:
            short_name: OPERA product short name, e.g. "OPERA_L2_RTC-S1_V1".
            bbox: [west, south, east, north] in WGS84.
            start: Start datetime (UTC).
            end: End datetime (UTC).
            max_results: Maximum number of results to return.

        Returns:
            List of granule metadata dicts (asf_search result properties).
        """
        logger.info(f"Searching ASF DAAC for {short_name} over {bbox}")
        results = asf.search(
            shortName=short_name,
            intersectsWith=(
                f"POLYGON(({bbox[0]} {bbox[1]},"
                f"{bbox[2]} {bbox[1]},"
                f"{bbox[2]} {bbox[3]},"
                f"{bbox[0]} {bbox[3]},"
                f"{bbox[0]} {bbox[1]}))"
            ),
            start=start.isoformat(),
            end=end.isoformat(),
            maxResults=max_results,
        )
        return [r.properties for r in results]

    def download(
        self,
        granule_urls: list[str],
        output_dir: Path,
    ) -> list[Path]:
        """Download OPERA granules from ASF DAAC using earthaccess.

        Args:
            granule_urls: List of HTTPS granule download URLs from search results.
            output_dir: Directory to save downloaded files.

        Returns:
            List of paths to downloaded files.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self._login()
        logger.info(f"Downloading {len(granule_urls)} granule(s) from ASF DAAC")
        paths = earthaccess.download(granule_urls, local_path=str(output_dir))
        return [Path(p) for p in paths]
