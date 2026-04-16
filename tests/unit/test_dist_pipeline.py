"""Unit tests for DIST-S1 pipeline orchestrator.

All tests mock conda-forge-only dependencies (dist-s1, rio-cogeo).
Uses pytest-mock for stubbing.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds

from subsideo.products.types import DISTResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_test_geotiff(
    path: Path, *, epsg: int = 32632, pixel_size: float = 30.0
) -> Path:
    """Write a minimal 20x20 GeoTIFF for testing."""
    if epsg == 4326:
        transform = from_bounds(
            11.0, 48.0, 11.0 + 20 * pixel_size, 48.0 + 20 * pixel_size, 20, 20
        )
    else:
        transform = from_bounds(
            500000, 4900000, 500000 + 20 * pixel_size, 4900000 + 20 * pixel_size, 20, 20
        )
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=20,
        width=20,
        count=1,
        dtype="float32",
        crs=CRS.from_epsg(epsg),
        transform=transform,
    ) as ds:
        ds.write(np.ones((1, 20, 20), dtype=np.float32))
    return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_AOI = {
    "type": "Polygon",
    "coordinates": [
        [
            [11.0, 48.0],
            [12.0, 48.0],
            [12.0, 49.0],
            [11.0, 49.0],
            [11.0, 48.0],
        ]
    ],
}


@pytest.fixture(autouse=True)
def _mock_rio_cogeo(mocker):
    """Ensure rio_cogeo modules are present in sys.modules for lazy imports.

    ``_metadata.inject_opera_metadata`` calls ``rio_cogeo.cogeo.cog_translate``
    to re-translate a COG after tag injection. We stub this to just copy the
    source file to the destination so the downstream ``tmp_path.replace(path)``
    call can find the expected output file.
    """
    import shutil as _shutil

    mock_cog_validate_mod = MagicMock()
    mock_cog_validate_mod.cog_validate = MagicMock(return_value=(True, [], []))

    def _fake_cog_translate(src, dst, *args, **kwargs):
        _shutil.copyfile(str(src), str(dst))

    mock_cogeo_mod = MagicMock()
    mock_cogeo_mod.cog_translate = _fake_cog_translate
    mock_profiles_mod = MagicMock()

    modules = {
        "rio_cogeo": MagicMock(),
        "rio_cogeo.cog_validate": mock_cog_validate_mod,
        "rio_cogeo.cogeo": mock_cogeo_mod,
        "rio_cogeo.profiles": mock_profiles_mod,
    }
    mocker.patch.dict("sys.modules", modules)
    return mock_cog_validate_mod


# ---------------------------------------------------------------------------
# Test 1: validate_dist_product - valid COG with UTM CRS
# ---------------------------------------------------------------------------


def test_validate_dist_valid_cog(tmp_path: Path, _mock_rio_cogeo) -> None:
    """Valid COG with UTM CRS passes validation."""
    from subsideo.products.dist import validate_dist_product

    tif = _make_test_geotiff(tmp_path / "dist.tif", epsg=32632, pixel_size=30.0)
    _mock_rio_cogeo.cog_validate.return_value = (True, [], [])
    errors = validate_dist_product([tif])
    assert errors == []


# ---------------------------------------------------------------------------
# Test 2: validate_dist_product - not a COG
# ---------------------------------------------------------------------------


def test_validate_dist_not_cog(tmp_path: Path, _mock_rio_cogeo) -> None:
    """Plain GeoTIFF (not COG) fails validation."""
    from subsideo.products.dist import validate_dist_product

    tif = _make_test_geotiff(tmp_path / "plain.tif", epsg=32632, pixel_size=30.0)
    _mock_rio_cogeo.cog_validate.return_value = (False, ["not tiled"], [])
    errors = validate_dist_product([tif])
    assert len(errors) >= 1
    assert any("not a valid COG" in e for e in errors)


# ---------------------------------------------------------------------------
# Test 3: validate_dist_product - non-UTM CRS
# ---------------------------------------------------------------------------


def test_validate_dist_non_utm(tmp_path: Path, _mock_rio_cogeo) -> None:
    """File with WGS84 CRS fails UTM check."""
    from subsideo.products.dist import validate_dist_product

    tif = _make_test_geotiff(tmp_path / "wgs84.tif", epsg=4326, pixel_size=0.0003)
    _mock_rio_cogeo.cog_validate.return_value = (True, [], [])
    errors = validate_dist_product([tif])
    assert len(errors) >= 1
    assert any("not UTM" in e for e in errors)


# ---------------------------------------------------------------------------
# Test 4: run_dist with mocked dist-s1
# ---------------------------------------------------------------------------


def test_run_dist_mocked(tmp_path: Path, mocker, _mock_rio_cogeo) -> None:
    """run_dist returns valid DISTResult when dist-s1 succeeds."""
    from subsideo.products.dist import run_dist

    out_dir = tmp_path / "out"

    # Create mock dist_s1 module
    def _fake_workflow(*, mgrs_tile_id, post_date, track_number, dst_dir):
        dst_dir.mkdir(parents=True, exist_ok=True)
        _make_test_geotiff(dst_dir / "disturbance.tif", epsg=32632, pixel_size=30.0)

    mock_module = MagicMock()
    mock_module.run_dist_s1_workflow = _fake_workflow
    mocker.patch.dict("sys.modules", {"dist_s1": mock_module})
    _mock_rio_cogeo.cog_validate.return_value = (True, [], [])

    result = run_dist("33UUP", "2025-06-15", 95, out_dir)

    assert result.valid is True
    assert len(result.output_paths) >= 1
    assert result.output_dir == out_dir


# ---------------------------------------------------------------------------
# Test 5: run_dist raises ImportError when dist-s1 not installed
# ---------------------------------------------------------------------------


def test_run_dist_import_error(tmp_path: Path, mocker) -> None:
    """run_dist raises ImportError with conda-forge instructions."""
    from subsideo.products.dist import run_dist

    # Setting module to None causes ImportError on import attempt
    mocker.patch.dict("sys.modules", {"dist_s1": None})

    with pytest.raises(ImportError, match="conda-forge"):
        run_dist("33UUP", "2025-06-15", 95, tmp_path / "out")


# ---------------------------------------------------------------------------
# Test 6: run_dist returns invalid result on runtime error
# ---------------------------------------------------------------------------


def test_run_dist_runtime_error(tmp_path: Path, mocker) -> None:
    """run_dist returns invalid result when dist-s1 raises."""
    from subsideo.products.dist import run_dist

    def _failing_workflow(**kwargs):
        raise RuntimeError("processing failed")

    mock_module = MagicMock()
    mock_module.run_dist_s1_workflow = _failing_workflow
    mocker.patch.dict("sys.modules", {"dist_s1": mock_module})

    result = run_dist("33UUP", "2025-06-15", 95, tmp_path / "out")

    assert result.valid is False
    assert any("processing failed" in e for e in result.validation_errors)


# ---------------------------------------------------------------------------
# Test 7: _aoi_to_mgrs_tiles returns tile dicts
# ---------------------------------------------------------------------------


def test_aoi_to_mgrs_tiles() -> None:
    """_aoi_to_mgrs_tiles returns list of dicts with correct keys."""
    from subsideo.products.dist import _aoi_to_mgrs_tiles

    tiles = _aoi_to_mgrs_tiles(_AOI)

    assert isinstance(tiles, list)
    assert len(tiles) > 0
    for tile in tiles:
        assert "mgrs_tile_id" in tile
        assert "track_number" in tile
        assert isinstance(tile["mgrs_tile_id"], str)
        assert isinstance(tile["track_number"], int)


# ---------------------------------------------------------------------------
# Test 8: run_dist_from_aoi with mocked deps
# ---------------------------------------------------------------------------


def test_run_dist_from_aoi_mocked(tmp_path: Path, mocker) -> None:
    """AOI entry point builds RTC time series then calls run_dist per tile."""
    from subsideo.products.dist import run_dist_from_aoi

    # Mock _aoi_to_mgrs_tiles
    mocker.patch(
        "subsideo.products.dist._aoi_to_mgrs_tiles",
        return_value=[{"mgrs_tile_id": "33UUP", "track_number": 95}],
    )

    # Mock Settings (lazy import target: subsideo.config)
    mock_settings = MagicMock()
    mock_settings.cdse_client_id = "test-id"
    mock_settings.cdse_client_secret = "test-secret"
    mocker.patch("subsideo.config.Settings", return_value=mock_settings)

    # Mock query_bursts_for_aoi (lazy import inside run_dist_from_aoi)
    mock_burst = MagicMock()
    mock_burst.burst_id_jpl = "T001_000001_IW1"
    mock_burst.epsg = 32632
    mocker.patch(
        "subsideo.burst.frames.query_bursts_for_aoi",
        return_value=[mock_burst],
    )

    # Mock shapely (lazy import inside run_dist_from_aoi)
    mock_shape = MagicMock()
    mock_geom = MagicMock()
    mock_geom.wkt = "POLYGON ((11 48, 12 48, 12 49, 11 49, 11 48))"
    mock_shape.return_value = mock_geom
    mocker.patch.dict(
        "sys.modules",
        {
            "shapely": MagicMock(),
            "shapely.geometry": MagicMock(shape=mock_shape),
        },
    )

    # Mock CDSEClient
    mock_client_instance = MagicMock()
    mock_client_instance.search_stac.return_value = [
        {
            "assets": {"data": {"href": "s3://eodata/test.zip"}},
            "properties": {
                "datetime": "2025-01-15T00:00:00",
                "platform": "S1A",
            },
        }
    ]

    def _fake_download(s3_path, output_path, **kwargs):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.touch()
        return output_path

    mock_client_instance.download.side_effect = _fake_download
    mock_client_cls = MagicMock(return_value=mock_client_instance)
    mocker.patch("subsideo.data.cdse.CDSEClient", mock_client_cls)

    # Mock fetch_dem (returns tuple[Path, dict] per actual signature)
    dem_path = tmp_path / "dem.tif"
    dem_path.touch()
    mocker.patch("subsideo.data.dem.fetch_dem", return_value=(dem_path, {"driver": "GTiff"}))

    # Mock fetch_orbit
    orbit_path = tmp_path / "orbit.EOF"
    orbit_path.touch()
    mocker.patch("subsideo.data.orbits.fetch_orbit", return_value=orbit_path)

    # Mock run_rtc
    mock_rtc_result = MagicMock()
    mock_rtc_result.valid = True
    mock_rtc_result.output_paths = [tmp_path / "rtc_out.tif"]
    mock_run_rtc = mocker.patch(
        "subsideo.products.rtc.run_rtc",
        return_value=mock_rtc_result,
    )

    # Mock run_dist (the inner call)
    mock_dist_result = DISTResult(
        output_paths=[tmp_path / "disturbance.tif"],
        output_dir=tmp_path / "out" / "33UUP",
        valid=True,
    )
    mock_run_dist = mocker.patch(
        "subsideo.products.dist.run_dist",
        return_value=mock_dist_result,
    )

    results = run_dist_from_aoi(
        aoi=_AOI,
        date_range=("2025-01-01", "2025-03-01"),
        output_dir=tmp_path / "out",
    )

    # Verify RTC was called (building time series)
    mock_run_rtc.assert_called()

    # Verify run_dist was called for the MGRS tile
    mock_run_dist.assert_called_once()
    call_kwargs = mock_run_dist.call_args.kwargs
    assert call_kwargs.get("mgrs_tile_id") == "33UUP" or (
        mock_run_dist.call_args.args and mock_run_dist.call_args.args[0] == "33UUP"
    )

    # Verify results
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0].valid is True

    # Verify CDSEClient was called with credentials from Settings
    mock_client_cls.assert_called_once_with(
        client_id="test-id",
        client_secret="test-secret",
    )
