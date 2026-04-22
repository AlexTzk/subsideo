"""EU-scoped Sentinel-1 burst SQLite database.

Builds an opera-utils-compatible burst ID database from ESA's published
Sentinel-1 burst ID GeoJSON (CC-BY 4.0).  The OPERA ``opera-burstdb``
only covers North America; this module provides EU coverage.

Data source: ESA Sentinel-1 burst ID maps, licensed under CC-BY 4.0.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
from loguru import logger
from shapely import wkt as _shapely_wkt
from shapely.geometry import box

from subsideo.utils.projections import utm_epsg_from_lon

ESA_BURST_DB_ATTRIBUTION = (
    "Sentinel-1 burst ID data: ESA (European Space Agency), "
    "licensed under CC-BY 4.0 (https://creativecommons.org/licenses/by/4.0/)"
)

_CREATE_TABLE_SQL = """\
CREATE TABLE IF NOT EXISTS burst_id_map (
    burst_id_jpl TEXT PRIMARY KEY,
    burst_id_esa TEXT NOT NULL,
    relative_orbit_number INTEGER NOT NULL,
    burst_index INTEGER NOT NULL,
    subswath TEXT NOT NULL,
    geometry_wkt TEXT NOT NULL,
    epsg INTEGER NOT NULL,
    is_north INTEGER DEFAULT 1
);
"""

_CREATE_INDEX_SQL = """\
CREATE INDEX IF NOT EXISTS burst_spatial ON burst_id_map(epsg);
"""


@dataclass
class BurstRecord:
    """A single Sentinel-1 burst from the EU burst database."""

    burst_id_jpl: str
    burst_id_esa: str
    relative_orbit_number: int
    burst_index: int
    subswath: str
    geometry_wkt: str
    epsg: int
    is_north: int


def get_burst_db_path(cache_dir: Path | None = None) -> Path:
    """Return the default EU burst database path.

    Parameters
    ----------
    cache_dir : Path | None
        Override cache directory. Defaults to ``~/.subsideo``.

    Returns
    -------
    Path
        ``<cache_dir>/eu_burst_db.sqlite``
    """
    base = cache_dir or (Path.home() / ".subsideo")
    return base / "eu_burst_db.sqlite"


def build_burst_db(
    geojson_source: str | Path,
    output_path: Path | None = None,
    eu_bounds: tuple[float, float, float, float] = (-32.0, 27.0, 45.0, 72.0),
) -> Path:
    """Build the EU burst SQLite from an ESA burst ID GeoJSON.

    Reads the ESA Sentinel-1 burst ID GeoJSON (local file or URL), filters
    to EU bounds, assigns UTM EPSG codes, and writes an opera-utils-compatible
    SQLite database.

    ESA data used under CC-BY 4.0 -- see ``ESA_BURST_DB_ATTRIBUTION``.

    Parameters
    ----------
    geojson_source : str | Path
        URL or local path to the ESA burst ID GeoJSON.
    output_path : Path | None
        Where to write the SQLite. Defaults to ``~/.subsideo/eu_burst_db.sqlite``.
    eu_bounds : tuple[float, float, float, float]
        Bounding box ``(west, south, east, north)`` in WGS 84 degrees.
        Default covers EU: lon -32 to 45, lat 27 to 72.

    Returns
    -------
    Path
        Path to the created SQLite database.
    """
    db_path = output_path or get_burst_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Loading burst GeoJSON from {}", geojson_source)
    gdf = gpd.read_file(geojson_source)

    # Ensure WGS 84
    if gdf.crs is not None and gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")

    # Filter to EU bounding box
    eu_box = box(*eu_bounds)
    gdf = gdf[gdf.geometry.intersects(eu_box)].copy()
    logger.info("Filtered to {} bursts within EU bounds", len(gdf))

    if gdf.empty:
        logger.warning("No bursts found within EU bounds — writing empty database")

    # Detect GeoJSON field names (ESA uses varying conventions)
    cols = set(gdf.columns)
    orbit_col = _find_column(cols, ["relative_orbit_number", "relative_orbit", "orbit"])
    index_col = _find_column(cols, ["burst_index", "burst_idx", "burstIndex"])
    swath_col = _find_column(cols, ["subswath_name", "subswath", "IW", "swath"])
    esa_id_col = _find_column(cols, ["burst_id", "burst_id_esa", "burstId", "id"])

    # Build records
    records: list[tuple[str, str, int, int, str, str, int, int]] = []
    for _, row in gdf.iterrows():
        rel_orbit = int(row[orbit_col])
        b_index = int(row[index_col])
        swath = str(row[swath_col])

        # Normalise subswath to "IW1"/"IW2"/"IW3"
        if swath in ("1", "2", "3"):
            swath = f"IW{swath}"

        esa_id = str(row[esa_id_col]) if esa_id_col else ""
        geom_wkt = row.geometry.wkt
        centroid = row.geometry.centroid
        epsg = utm_epsg_from_lon(centroid.x, centroid.y)
        jpl_id = f"T{rel_orbit:03d}-{b_index:06d}-{swath}"

        records.append((jpl_id, esa_id, rel_orbit, b_index, swath, geom_wkt, epsg, 1))

    # Write to SQLite
    logger.info("Writing {} burst records to {}", len(records), db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(_CREATE_TABLE_SQL)
        conn.execute(_CREATE_INDEX_SQL)
        conn.executemany(
            "INSERT OR REPLACE INTO burst_id_map VALUES (?,?,?,?,?,?,?,?)",
            records,
        )
        conn.commit()
    finally:
        conn.close()

    logger.info("EU burst DB built at {}", db_path)
    return db_path


def _find_column(columns: set[str], candidates: list[str]) -> str:
    """Return the first matching column name from candidates."""
    for c in candidates:
        if c in columns:
            return c
    raise KeyError(
        f"Could not find any of {candidates} in GeoJSON columns: {sorted(columns)}"
    )


def query_bounds(
    burst_id: str,
    cache_dir: Path | None = None,
) -> tuple[float, float, float, float]:
    """Return ``(west, south, east, north)`` in degrees for a burst_id.

    Used as the fallback path by
    :func:`subsideo.validation.harness.bounds_for_burst` when
    ``opera_utils.burst_frame_db`` does not recognise ``burst_id`` (EU
    bursts are not in opera-utils' N.Am.-only DB).

    The EU burst DB schema stores footprints as WKT in the
    ``geometry_wkt`` column (no separate west/south/east/north columns —
    see :data:`_CREATE_TABLE_SQL`); this helper re-parses the WKT via
    shapely and returns the envelope.

    Parameters
    ----------
    burst_id : str
        JPL-format burst ID (e.g. ``"t117_249422_iw2"`` for an EU burst).
    cache_dir : Path | None, default None
        Override cache directory. Defaults to ``~/.subsideo``.

    Returns
    -------
    tuple[float, float, float, float]
        ``(west, south, east, north)`` in WGS 84 degrees.

    Raises
    ------
    ValueError
        If the EU burst DB does not exist yet, or the burst_id is absent.
    """
    db_path = get_burst_db_path(cache_dir)
    if not db_path.exists():
        raise ValueError(
            f"EU burst DB not built yet at {db_path}; run "
            f"`subsideo.burst.db.build_burst_db(...)` first."
        )

    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT geometry_wkt FROM burst_id_map WHERE burst_id_jpl = ?",
            (burst_id,),
        ).fetchone()

    if row is None:
        raise ValueError(
            f"Burst {burst_id!r} not in EU burst DB at {db_path}"
        )

    (geom_wkt,) = row
    geom = _shapely_wkt.loads(geom_wkt)
    west, south, east, north = geom.bounds
    return float(west), float(south), float(east), float(north)
