"""Unit tests for subsideo.data.natural_earth — Natural Earth coastline/waterbody helpers.

Tests mock ``cartopy.io.shapereader.natural_earth`` (the real data source) by
patching the attribute on the ``subsideo.data.natural_earth`` module's
``shapereader`` binding via the import inside the function.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _make_shapereader_mock(coast_path: Path, lakes_path: Path) -> MagicMock:
    """Build a mock shapereader module with natural_earth(resolution, category, name)."""
    calls: list[dict] = []

    def fake_natural_earth(resolution: str, category: str, name: str) -> str:
        calls.append({"resolution": resolution, "category": category, "name": name})
        return str(coast_path) if name == "coastline" else str(lakes_path)

    mock_shapereader = MagicMock()
    mock_shapereader.natural_earth.side_effect = fake_natural_earth
    mock_shapereader.__calls__ = calls  # type: ignore[attr-defined]
    return mock_shapereader


class TestLoadCoastlineAndWaterbodies:
    """load_coastline_and_waterbodies returns (coastline, waterbodies) GeoSeries."""

    def _write_geojson_features(
        self, path: Path, geometries: list[dict]
    ) -> None:
        """Write a minimal GeoJSON FeatureCollection to path."""
        fc = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": geom, "properties": {}}
                for geom in geometries
            ],
        }
        path.write_text(json.dumps(fc))

    def test_returns_two_geoseries(self, tmp_path: Path) -> None:
        """load_coastline_and_waterbodies returns a 2-tuple of GeoSeries."""
        import geopandas as gpd

        from subsideo.data.natural_earth import load_coastline_and_waterbodies

        coast_path = tmp_path / "coastline.geojson"
        lakes_path = tmp_path / "lakes.geojson"

        self._write_geojson_features(coast_path, [
            {"type": "LineString", "coordinates": [[-4.0, 40.0], [-3.0, 41.0]]}
        ])
        self._write_geojson_features(lakes_path, [
            {"type": "Polygon", "coordinates": [
                [[-3.5, 40.0], [-3.0, 40.0], [-3.0, 40.5], [-3.5, 40.5], [-3.5, 40.0]]
            ]}
        ])

        mock_shapereader = _make_shapereader_mock(coast_path, lakes_path)
        with patch(
            "cartopy.io.shapereader.natural_earth",
            side_effect=mock_shapereader.natural_earth.side_effect,
        ):
            coastline, waterbodies = load_coastline_and_waterbodies(
                (-4.0, 39.5, -1.5, 42.0)
            )

        assert isinstance(coastline, gpd.GeoSeries)
        assert isinstance(waterbodies, gpd.GeoSeries)

    def test_coastline_nonempty_iberian_bbox(self, tmp_path: Path) -> None:
        """Clipped coastline GeoSeries has at least one feature for Iberian bbox."""
        from subsideo.data.natural_earth import load_coastline_and_waterbodies

        coast_path = tmp_path / "coastline.geojson"
        lakes_path = tmp_path / "lakes.geojson"

        self._write_geojson_features(coast_path, [
            {"type": "LineString", "coordinates": [[-4.5, 40.0], [-1.0, 40.0]]},
            {"type": "LineString", "coordinates": [[10.0, 50.0], [11.0, 51.0]]},  # outside
        ])
        self._write_geojson_features(lakes_path, [])

        mock_shapereader = _make_shapereader_mock(coast_path, lakes_path)
        with patch(
            "cartopy.io.shapereader.natural_earth",
            side_effect=mock_shapereader.natural_earth.side_effect,
        ):
            coastline, _ = load_coastline_and_waterbodies(
                (-4.0, 39.5, -1.5, 42.0)
            )

        assert len(coastline) > 0, "Clipped coastline should have at least one feature"

    def test_outside_bbox_features_excluded(self, tmp_path: Path) -> None:
        """Features fully outside bbox are filtered out."""
        from subsideo.data.natural_earth import load_coastline_and_waterbodies

        coast_path = tmp_path / "coastline.geojson"
        lakes_path = tmp_path / "lakes.geojson"

        self._write_geojson_features(coast_path, [
            {"type": "LineString", "coordinates": [[10.0, 50.0], [11.0, 51.0]]},
            {"type": "LineString", "coordinates": [[20.0, 60.0], [21.0, 61.0]]},
        ])
        self._write_geojson_features(lakes_path, [])

        mock_shapereader = _make_shapereader_mock(coast_path, lakes_path)
        with patch(
            "cartopy.io.shapereader.natural_earth",
            side_effect=mock_shapereader.natural_earth.side_effect,
        ):
            coastline, waterbodies = load_coastline_and_waterbodies(
                (-4.0, 39.5, -1.5, 42.0)
            )

        assert len(coastline) == 0
        assert len(waterbodies) == 0

    def test_missing_cartopy_raises_import_error(self) -> None:
        """ImportError with helpful message when cartopy cannot be imported."""
        from subsideo.data.natural_earth import load_coastline_and_waterbodies

        # Force the lazy `from cartopy.io import shapereader` inside the function
        # to fail by inserting a sentinel that raises on attribute access.
        with patch.dict("sys.modules", {"cartopy.io": None}):
            with pytest.raises(ImportError, match="cartopy"):
                load_coastline_and_waterbodies((-4.0, 39.5, -1.5, 42.0))

    def test_scale_parameter_forwarded(self, tmp_path: Path) -> None:
        """The scale parameter is passed through to shapereader.natural_earth as 'resolution'."""
        from subsideo.data.natural_earth import load_coastline_and_waterbodies

        coast_path = tmp_path / "coastline.geojson"
        lakes_path = tmp_path / "lakes.geojson"
        self._write_geojson_features(coast_path, [])
        self._write_geojson_features(lakes_path, [])

        calls: list[dict] = []

        def fake_natural_earth(resolution: str, category: str, name: str) -> str:
            calls.append({"resolution": resolution, "category": category, "name": name})
            return str(coast_path) if name == "coastline" else str(lakes_path)

        with patch(
            "cartopy.io.shapereader.natural_earth",
            side_effect=fake_natural_earth,
        ):
            load_coastline_and_waterbodies((-4.0, 39.5, -1.5, 42.0), scale="50m")

        assert all(c["resolution"] == "50m" for c in calls)
        assert all(c["category"] == "physical" for c in calls)
        names = sorted({c["name"] for c in calls})
        assert names == ["coastline", "lakes"]
