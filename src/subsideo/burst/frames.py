"""Spatial query layer for the EU burst database."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from shapely import wkt

from subsideo.burst.db import BurstRecord, get_burst_db_path


def query_bursts_for_aoi(
    aoi_wkt: str,
    db_path: Path | None = None,
) -> list[BurstRecord]:
    """Return burst records whose footprints intersect the given AOI.

    Parameters
    ----------
    aoi_wkt : str
        Well-Known Text polygon defining the area of interest (EPSG:4326).
    db_path : Path | None
        Path to the EU burst SQLite. Defaults to ``~/.subsideo/eu_burst_db.sqlite``.

    Returns
    -------
    list[BurstRecord]
        Burst records that intersect the AOI geometry.

    Raises
    ------
    FileNotFoundError
        If the burst database does not exist at *db_path*.
    """
    db_path = db_path or get_burst_db_path()

    if not db_path.exists():
        raise FileNotFoundError(
            f"EU burst DB not found at {db_path}. Run build_burst_db() first."
        )

    aoi_geom = wkt.loads(aoi_wkt)

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT burst_id_jpl, burst_id_esa, relative_orbit_number, "
            "burst_index, subswath, geometry_wkt, epsg, is_north "
            "FROM burst_id_map"
        ).fetchall()
    finally:
        conn.close()

    hits: list[BurstRecord] = []
    for row in rows:
        record = BurstRecord(*row)
        burst_geom = wkt.loads(record.geometry_wkt)
        if aoi_geom.intersects(burst_geom):
            hits.append(record)

    return hits
