"""UTM zone selection for EU bursts."""
from __future__ import annotations

from subsideo.burst.db import BurstRecord


def select_utm_epsg(burst_record: BurstRecord) -> int:
    """Return the UTM EPSG code for a burst.

    Reads directly from the burst record (pre-stored at DB build time).
    NEVER derives UTM zone from coordinates at query time -- EU spans
    zones 28N-38N (EPSG 32628-32638) and coordinate-based derivation
    fails for Norway/Svalbard anomalies.
    """
    return burst_record.epsg
