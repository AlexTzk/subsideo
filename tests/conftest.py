"""Shared pytest fixtures for subsideo tests."""
from __future__ import annotations

from pathlib import Path

import pytest

# Po Valley, Italy -- reference AOI used across tests
PO_VALLEY_BBOX = [9.5, 44.5, 12.5, 45.5]  # [west, south, east, north] WGS84
PO_VALLEY_WKT = "POLYGON((9.5 44.5, 12.5 44.5, 12.5 45.5, 9.5 45.5, 9.5 44.5))"


@pytest.fixture
def po_valley_bbox() -> list[float]:
    return PO_VALLEY_BBOX


@pytest.fixture
def po_valley_wkt() -> str:
    return PO_VALLEY_WKT


@pytest.fixture
def tmp_cache_dir(tmp_path: Path) -> Path:
    cache = tmp_path / ".subsideo"
    cache.mkdir()
    return cache
