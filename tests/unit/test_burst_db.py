"""Unit tests for EU burst database: build, query, and UTM selection.

Uses an in-memory SQLite fixture with synthetic burst records -- no network
access or real ESA GeoJSON required.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from subsideo.burst.db import BurstRecord
from subsideo.burst.frames import query_bursts_for_aoi
from subsideo.burst.tiling import select_utm_epsg


@pytest.fixture
def burst_db(tmp_path: Path) -> Path:
    """Create a test SQLite with 3 synthetic burst records."""
    db_path = tmp_path / "test_burst.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE burst_id_map (
        burst_id_jpl TEXT PRIMARY KEY, burst_id_esa TEXT NOT NULL,
        relative_orbit_number INTEGER NOT NULL, burst_index INTEGER NOT NULL,
        subswath TEXT NOT NULL, geometry_wkt TEXT NOT NULL,
        epsg INTEGER NOT NULL, is_north INTEGER DEFAULT 1
    )""")
    records = [
        # Po Valley (lon~11, lat~45) -> UTM 32N
        (
            "T037-000001-IW2", "ESA_1", 37, 1, "IW2",
            "POLYGON((10.5 44.5, 11.5 44.5, 11.5 45.5, 10.5 45.5, 10.5 44.5))",
            32632, 1,
        ),
        # Lisbon (lon~-9, lat~38.7) -> UTM 29N
        (
            "T081-000010-IW1", "ESA_2", 81, 10, "IW1",
            "POLYGON((-9.5 38.2, -8.5 38.2, -8.5 39.2, -9.5 39.2, -9.5 38.2))",
            32629, 1,
        ),
        # Helsinki (lon~25, lat~60) -> UTM 35N
        (
            "T124-000020-IW3", "ESA_3", 124, 20, "IW3",
            "POLYGON((24.5 59.5, 25.5 59.5, 25.5 60.5, 24.5 60.5, 24.5 59.5))",
            32635, 1,
        ),
    ]
    conn.executemany("INSERT INTO burst_id_map VALUES (?,?,?,?,?,?,?,?)", records)
    conn.commit()
    conn.close()
    return db_path


def test_query_returns_po_valley_burst(burst_db: Path) -> None:
    """AOI covering Po Valley returns exactly the Po Valley burst."""
    po_valley_wkt = "POLYGON((9.5 44.5, 12.5 44.5, 12.5 45.5, 9.5 45.5, 9.5 44.5))"
    results = query_bursts_for_aoi(po_valley_wkt, db_path=burst_db)
    assert len(results) == 1
    assert results[0].burst_id_jpl == "T037-000001-IW2"
    assert results[0].epsg == 32632


def test_query_empty_for_non_intersecting_aoi(burst_db: Path) -> None:
    """AOI over the Atlantic Ocean returns no bursts."""
    ocean_wkt = "POLYGON((-40 20, -35 20, -35 25, -40 25, -40 20))"
    results = query_bursts_for_aoi(ocean_wkt, db_path=burst_db)
    assert results == []


def test_query_returns_multiple_bursts(burst_db: Path) -> None:
    """Large AOI covering both Portugal and Po Valley returns 2 bursts."""
    wide_wkt = "POLYGON((-10 38, 12 38, 12 46, -10 46, -10 38))"
    results = query_bursts_for_aoi(wide_wkt, db_path=burst_db)
    assert len(results) == 2
    ids = {r.burst_id_jpl for r in results}
    assert "T037-000001-IW2" in ids
    assert "T081-000010-IW1" in ids


def test_select_utm_epsg_reads_from_record() -> None:
    """select_utm_epsg returns the EPSG stored in the burst record."""
    record = BurstRecord(
        burst_id_jpl="T037-000001-IW2",
        burst_id_esa="ESA_1",
        relative_orbit_number=37,
        burst_index=1,
        subswath="IW2",
        geometry_wkt="POLYGON((10.5 44.5, 11.5 44.5, 11.5 45.5, 10.5 45.5, 10.5 44.5))",
        epsg=32632,
        is_north=1,
    )
    assert select_utm_epsg(record) == 32632


def test_select_utm_epsg_portugal() -> None:
    """select_utm_epsg returns 32629 for a Portuguese burst record."""
    record = BurstRecord(
        burst_id_jpl="T081-000010-IW1",
        burst_id_esa="ESA_2",
        relative_orbit_number=81,
        burst_index=10,
        subswath="IW1",
        geometry_wkt="POLYGON((-9.5 38.2, -8.5 38.2, -8.5 39.2, -9.5 39.2, -9.5 38.2))",
        epsg=32629,
        is_north=1,
    )
    assert select_utm_epsg(record) == 32629


def test_query_raises_when_db_missing() -> None:
    """query_bursts_for_aoi raises FileNotFoundError for a missing DB."""
    with pytest.raises(FileNotFoundError, match="EU burst DB not found"):
        query_bursts_for_aoi(
            "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
            db_path=Path("/nonexistent.sqlite"),
        )
