"""IONEX TEC map download from CDDIS GNSS archive using Earthdata credentials."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import requests
from loguru import logger


def fetch_ionex(
    date: date,
    output_dir: Path,
    username: str,
    password: str,
) -> Path:
    """Download IONEX TEC map from CDDIS GNSS archive.

    Uses NASA Earthdata credentials (same as ASF DAAC: EARTHDATA_USERNAME/PASSWORD).
    CDDIS uses Basic auth over HTTPS. File is compressed (.Z); returned as-is
    for downstream decompression by ISCE3/pyaps3.

    URL pattern:
        https://cddis.nasa.gov/archive/gnss/products/ionex/{year}/{doy}/igsg{doy}0.{yy}i.Z

    Args:
        date: Date for which to download IONEX map.
        output_dir: Directory to save the compressed IONEX file.
        username: NASA Earthdata username.
        password: NASA Earthdata password.

    Returns:
        Path to downloaded compressed IONEX file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    year = date.year
    doy = date.timetuple().tm_yday
    yy = str(year)[2:]
    filename = f"igsg{doy:03d}0.{yy}i.Z"
    url = f"https://cddis.nasa.gov/archive/gnss/products/ionex/{year}/{doy:03d}/{filename}"

    logger.info(f"Downloading IONEX from {url}")
    response = requests.get(url, auth=(username, password), timeout=120)
    response.raise_for_status()

    out_path = output_dir / filename
    out_path.write_bytes(response.content)
    logger.info(f"IONEX saved to {out_path}")
    return out_path
