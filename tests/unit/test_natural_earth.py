"""Unit tests for subsideo.data.natural_earth — Natural Earth coastline/waterbody helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest


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

        # A simple line (coastline) that intersects bbox
        self._write_geojson_features(coast_path, [
            {"type": "LineString", "coordinates": [[-4.0, 40.0], [-3.0, 41.0]]}
        ])
        # A lake polygon inside the bbox
        self._write_geojson_features(lakes_path, [
            {"type": "Polygon", "coordinates": [
                [[-3.5, 40.0], [-3.0, 40.0], [-3.0, 40.5], [-3.5, 40.5], [-3.5, 40.0]]
            ]}
        ])

        mock_ne = type("MockNE", (), {
            "get_path": staticmethod(lambda scale, name: (
                str(coast_path) if name == "coastline" else str(lakes_path)
            ))
        })()

        with patch.dict("sys.modules", {"naturalearth": mock_ne}):
            coastline, waterbodies = load_coastline_and_waterbodies((-4.0, 39.5, -1.5, 42.0))

        assert isinstance(coastline, gpd.GeoSeries)
        assert isinstance(waterbodies, gpd.GeoSeries)

    def test_coastline_nonempty_iberian_bbox(self, tmp_path: Path) -> None:
        """Clipped coastline GeoSeries has at least one feature for Iberian bbox."""
        coast_path = tmp_path / "coastline.geojson"
        lakes_path = tmp_path / "lakes.geojson"

        # Coastline intersects the bbox (-4, 39.5, -1.5, 42)
        self._write_geojson_features(coast_path, [
            {"type": "LineString", "coordinates": [[-4.5, 40.0], [-1.0, 40.0]]},
            {"type": "LineString", "coordinates": [[10.0, 50.0], [11.0, 51.0]]},  # outside
        ])
        self._write_geojson_features(lakes_path, [])

        mock_ne = type("MockNE", (), {
            "get_path": staticmethod(lambda scale, name: (
                str(coast_path) if name == "coastline" else str(lakes_path)
            ))
        })()

        from subsideo.data.natural_earth import load_coastline_and_waterbodies

        with patch.dict("sys.modules", {"naturalearth": mock_ne}):
            coastline, _ = load_coastline_and_waterbodies((-4.0, 39.5, -1.5, 42.0))

        assert len(coastline) > 0, "Clipped coastline should have at least one feature"

    def test_outside_bbox_features_excluded(self, tmp_path: Path) -> None:
        """Features fully outside bbox are filtered out."""
        coast_path = tmp_path / "coastline.geojson"
        lakes_path = tmp_path / "lakes.geojson"

        # Both features are well outside the Iberian bbox
        self._write_geojson_features(coast_path, [
            {"type": "LineString", "coordinates": [[10.0, 50.0], [11.0, 51.0]]},
            {"type": "LineString", "coordinates": [[20.0, 60.0], [21.0, 61.0]]},
        ])
        self._write_geojson_features(lakes_path, [])

        mock_ne = type("MockNE", (), {
            "get_path": staticmethod(lambda scale, name: (
                str(coast_path) if name == "coastline" else str(lakes_path)
            ))
        })()

        from subsideo.data.natural_earth import load_coastline_and_waterbodies

        with patch.dict("sys.modules", {"naturalearth": mock_ne}):
            coastline, waterbodies = load_coastline_and_waterbodies((-4.0, 39.5, -1.5, 42.0))

        assert len(coastline) == 0
        assert len(waterbodies) == 0

    def test_missing_naturalearth_raises_import_error(self) -> None:
        """ImportError with helpful message when naturalearth not installed."""
        import sys

        # Temporarily remove naturalearth from sys.modules to simulate not installed
        saved = sys.modules.pop("naturalearth", None)
        try:
            # Patch the import so it raises ImportError
            with patch.dict("sys.modules", {"naturalearth": None}):  # type: ignore[dict-item]
                from subsideo.data.natural_earth import load_coastline_and_waterbodies

                with pytest.raises(ImportError, match="naturalearth"):
                    load_coastline_and_waterbodies((-4.0, 39.5, -1.5, 42.0))
        finally:
            if saved is not None:
                sys.modules["naturalearth"] = saved

    def test_scale_parameter_forwarded(self, tmp_path: Path) -> None:
        """The scale parameter is passed through to naturalearth.get_path."""
        coast_path = tmp_path / "coastline.geojson"
        lakes_path = tmp_path / "lakes.geojson"
        self._write_geojson_features(coast_path, [])
        self._write_geojson_features(lakes_path, [])

        calls: list[dict] = []

        def get_path(scale: str, name: str) -> str:
            calls.append({"scale": scale, "name": name})
            return str(coast_path) if name == "coastline" else str(lakes_path)

        mock_ne = type("MockNE", (), {"get_path": staticmethod(get_path)})()

        from subsideo.data.natural_earth import load_coastline_and_waterbodies

        with patch.dict("sys.modules", {"naturalearth": mock_ne}):
            load_coastline_and_waterbodies((-4.0, 39.5, -1.5, 42.0), scale="50m")

        assert all(c["scale"] == "50m" for c in calls)
