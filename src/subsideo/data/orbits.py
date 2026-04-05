"""Sentinel-1 orbit file download: sentineleof primary, s1-orbits fallback."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from loguru import logger


def fetch_orbit(sensing_time: datetime, satellite: str, output_dir: Path) -> Path:
    """Download Sentinel-1 orbit file. POEORB-first via sentineleof, RESORB fallback.

    If ESA POD hub is unreachable, falls back to s1-orbits (AWS-backed, ASF HyP3 team).

    Args:
        sensing_time: Acquisition start time (UTC).
        satellite: "S1A", "S1B", or "S1C".
        output_dir: Directory to save .EOF file.

    Returns:
        Path to downloaded .EOF file.
    """
    from eof.download import download_eofs

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"Fetching orbit for {satellite} at {sensing_time} via sentineleof")
        paths = download_eofs(
            [sensing_time],
            missions=[satellite],
            orbit_type="precise",
            output_directory=output_dir,
        )
        return Path(paths[0])
    except Exception as esa_err:
        logger.warning(
            f"ESA POD hub unreachable ({esa_err}), falling back to s1-orbits (AWS)"
        )
        from s1_orbits import fetch_for_scene

        return Path(fetch_for_scene(sensing_time, satellite, output_dir))
