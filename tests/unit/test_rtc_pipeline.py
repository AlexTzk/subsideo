"""Unit tests for RTC-S1 pipeline orchestrator.

All tests mock conda-forge-only dependencies (opera-rtc, rio-cogeo).
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
import yaml

from subsideo.products.rtc import generate_rtc_runconfig, run_rtc
from subsideo.products.types import RTCConfig, RTCResult


def _make_test_geotiff(
    path: Path, epsg: int = 32632, pixel_size: float = 30.0
) -> Path:
    """Write a minimal 10x10 GeoTIFF for testing."""
    transform = from_bounds(
        500000, 4900000, 500000 + 10 * pixel_size, 4900000 + 10 * pixel_size, 10, 10
    )
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="float32",
        crs=CRS.from_epsg(epsg),
        transform=transform,
    ) as ds:
        ds.write(np.ones((1, 10, 10), dtype=np.float32))
    return path


@pytest.fixture(autouse=True)
def _mock_rio_cogeo(mocker):
    """Ensure rio_cogeo modules are present in sys.modules for lazy imports."""
    mock_cog_validate_mod = MagicMock()
    mock_cog_validate_mod.cog_validate = MagicMock(return_value=(True, [], []))

    mock_cogeo_mod = MagicMock()
    mock_profiles_mod = MagicMock()

    modules = {
        "rio_cogeo": MagicMock(),
        "rio_cogeo.cog_validate": mock_cog_validate_mod,
        "rio_cogeo.cogeo": mock_cogeo_mod,
        "rio_cogeo.profiles": mock_profiles_mod,
    }
    mocker.patch.dict("sys.modules", modules)
    return mock_cog_validate_mod


class TestGenerateRtcRunconfig:
    """Runconfig YAML generation."""

    def test_generate_rtc_runconfig(self, tmp_path: Path) -> None:
        cfg = RTCConfig(
            safe_file_paths=[tmp_path / "S1A.zip"],
            orbit_file_path=tmp_path / "orbit.EOF",
            dem_file=tmp_path / "dem.tif",
            burst_id=["T001-123456-IW1"],
            output_dir=tmp_path / "output",
        )

        out = generate_rtc_runconfig(cfg, tmp_path / "runconfig.yaml")
        assert out == tmp_path / "runconfig.yaml"
        assert out.exists()

        with open(out) as fh:
            data = yaml.safe_load(fh)

        rc = data["runconfig"]
        assert rc["name"] == "rtc_s1_workflow"
        assert rc["groups"]["primary_executable"]["product_type"] == "RTC_S1"
        assert isinstance(rc["groups"]["input_file_group"]["safe_file_path"], list)
        assert all(
            isinstance(s, str)
            for s in rc["groups"]["input_file_group"]["safe_file_path"]
        )
        assert isinstance(
            rc["groups"]["dynamic_ancillary_file_group"]["dem_file"], str
        )
        assert rc["groups"]["product_group"]["product_version"] == "0.1.0"
        assert rc["groups"]["input_file_group"]["burst_id"] == ["T001-123456-IW1"]


class TestValidateRtcProduct:
    """Product validation checks."""

    def test_validate_rtc_product_valid(
        self, tmp_path: Path, _mock_rio_cogeo
    ) -> None:
        from subsideo.products.rtc import validate_rtc_product

        tif = _make_test_geotiff(tmp_path / "rtc.tif", epsg=32632, pixel_size=30.0)
        _mock_rio_cogeo.cog_validate.return_value = (True, [], [])
        errors = validate_rtc_product([tif])
        assert errors == []

    def test_validate_rtc_product_bad_crs(
        self, tmp_path: Path, _mock_rio_cogeo
    ) -> None:
        from subsideo.products.rtc import validate_rtc_product

        tif = _make_test_geotiff(
            tmp_path / "rtc_wgs84.tif", epsg=4326, pixel_size=0.0003
        )
        _mock_rio_cogeo.cog_validate.return_value = (True, [], [])
        errors = validate_rtc_product([tif])
        assert len(errors) >= 1
        assert any("UTM" in e for e in errors)

    def test_validate_rtc_product_missing_file(self, tmp_path: Path) -> None:
        from subsideo.products.rtc import validate_rtc_product

        errors = validate_rtc_product([tmp_path / "nonexistent.tif"])
        assert len(errors) == 1
        assert "does not exist" in errors[0]


class TestRunRtc:
    """Full pipeline with mocked opera-rtc."""

    def test_run_rtc_mocked(self, tmp_path: Path, mocker) -> None:
        out_dir = tmp_path / "out"

        # Mock opera-rtc imports (lazy inside run_rtc)
        mock_runconfig_cls = MagicMock()
        mock_run_parallel = MagicMock()
        mocker.patch.dict(
            "sys.modules",
            {
                "rtc": MagicMock(),
                "rtc.runconfig": MagicMock(RunConfig=mock_runconfig_cls),
                "rtc.rtc_s1": MagicMock(run_parallel=mock_run_parallel),
            },
        )

        # run_parallel side effect: create a dummy .tif in output_dir
        def _create_dummy_tif(cfg, logfile, flag):
            out_dir.mkdir(parents=True, exist_ok=True)
            _make_test_geotiff(out_dir / "burst_rtc.tif")

        mock_run_parallel.side_effect = _create_dummy_tif

        # Mock ensure_cog to pass through
        mocker.patch(
            "subsideo.products.rtc.ensure_cog",
            side_effect=lambda p, o=None: p,
        )

        # Mock validate_rtc_product to return no errors
        mocker.patch(
            "subsideo.products.rtc.validate_rtc_product",
            return_value=[],
        )

        result = run_rtc(
            safe_paths=[tmp_path / "S1A.zip"],
            orbit_path=tmp_path / "orbit.EOF",
            dem_path=tmp_path / "dem.tif",
            burst_ids=["T001"],
            output_dir=out_dir,
        )

        assert result.valid is True
        assert result.burst_ids == ["T001"]
        assert result.runconfig_path == out_dir / "rtc_runconfig.yaml"
        mock_runconfig_cls.load_from_yaml.assert_called_once()
        mock_run_parallel.assert_called_once()

    def test_run_rtc_handles_opera_failure(self, tmp_path: Path, mocker) -> None:
        """Pipeline returns valid=False when opera-rtc raises."""
        mocker.patch.dict(
            "sys.modules",
            {
                "rtc": MagicMock(),
                "rtc.runconfig": MagicMock(
                    RunConfig=MagicMock(
                        load_from_yaml=MagicMock(
                            side_effect=RuntimeError("boom")
                        )
                    )
                ),
                "rtc.rtc_s1": MagicMock(),
            },
        )

        result = run_rtc(
            safe_paths=[tmp_path / "S1A.zip"],
            orbit_path=tmp_path / "orbit.EOF",
            dem_path=tmp_path / "dem.tif",
            burst_ids=["T001"],
            output_dir=tmp_path / "out",
        )

        assert result.valid is False
        assert "failed" in result.validation_errors[0]


MOCK_STAC_ITEM = {
    "assets": {"data": {"href": "s3://eodata/test.zip"}},
    "properties": {
        "datetime": "2025-01-15T00:00:00",
        "platform": "S1A",
    },
}


def test_run_rtc_from_aoi_mocked(tmp_path: Path, mocker) -> None:
    """Verify run_rtc_from_aoi wires all Phase 1 data-access calls correctly."""
    # Mock Settings (B-01)
    mock_settings = MagicMock()
    mock_settings.cdse_client_id = "test-id"
    mock_settings.cdse_client_secret = "test-secret"
    mocker.patch("subsideo.config.Settings", return_value=mock_settings)

    # Mock CDSEClient (B-01 + B-02)
    mock_client_instance = MagicMock()
    mock_client_instance.search_stac.return_value = [MOCK_STAC_ITEM]

    def _fake_download(s3_path: str, output_path: Path, **kwargs: object) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.touch()
        return output_path

    mock_client_instance.download.side_effect = _fake_download
    mock_client_cls = MagicMock(return_value=mock_client_instance)
    mocker.patch("subsideo.data.cdse.CDSEClient", mock_client_cls)

    # Mock burst query (B-03)
    mock_burst = MagicMock()
    mock_burst.burst_id_jpl = "T001_000001_IW1"
    mock_burst.epsg = 32632
    mock_burst_query = mocker.patch(
        "subsideo.burst.frames.query_bursts_for_aoi",
        return_value=[mock_burst],
    )

    # Mock fetch_dem (B-05) — returns tuple
    dem_path = tmp_path / "dem.tif"
    dem_path.touch()
    mock_fetch_dem = mocker.patch(
        "subsideo.data.dem.fetch_dem",
        return_value=(dem_path, {"driver": "GTiff"}),
    )

    # Mock fetch_orbit (B-04)
    orbit_path = tmp_path / "orbit.EOF"
    orbit_path.touch()
    mock_fetch_orbit = mocker.patch(
        "subsideo.data.orbits.fetch_orbit",
        return_value=orbit_path,
    )

    # Mock run_rtc (the inner call)
    mock_rtc_result = RTCResult(
        output_paths=[tmp_path / "rtc.tif"],
        runconfig_path=tmp_path / "runconfig.yaml",
        burst_ids=["T001_000001_IW1"],
        valid=True,
    )
    mocker.patch("subsideo.products.rtc.run_rtc", return_value=mock_rtc_result)

    aoi = {
        "type": "Polygon",
        "coordinates": [
            [[11.0, 48.0], [12.0, 48.0], [12.0, 49.0], [11.0, 49.0], [11.0, 48.0]]
        ],
    }

    from subsideo.products.rtc import run_rtc_from_aoi

    result = run_rtc_from_aoi(
        aoi=aoi,
        date_range=("2025-01-01", "2025-03-01"),
        output_dir=tmp_path / "out",
    )

    # B-01: CDSEClient gets credentials
    mock_client_cls.assert_called_once_with(
        client_id="test-id", client_secret="test-secret"
    )

    # B-02: search_stac called with correct kwargs
    mock_client_instance.search_stac.assert_called_once()
    search_kwargs = mock_client_instance.search_stac.call_args
    assert search_kwargs.kwargs["collection"] == "SENTINEL-1"
    assert search_kwargs.kwargs["product_type"] == "IW_SLC__1S"
    assert isinstance(search_kwargs.kwargs["start"], __import__("datetime").datetime)
    assert isinstance(search_kwargs.kwargs["end"], __import__("datetime").datetime)
    assert isinstance(search_kwargs.kwargs["bbox"], list)

    # B-03: burst query uses frames module with aoi_wkt
    mock_burst_query.assert_called_once()
    assert "aoi_wkt" in mock_burst_query.call_args.kwargs

    # B-04: fetch_orbit with named args
    mock_fetch_orbit.assert_called_once()
    orbit_kwargs = mock_fetch_orbit.call_args.kwargs
    assert "sensing_time" in orbit_kwargs
    assert orbit_kwargs["satellite"] == "S1A"
    assert "output_dir" in orbit_kwargs

    # B-05: fetch_dem with output_epsg and bounds as list
    mock_fetch_dem.assert_called_once()
    dem_kwargs = mock_fetch_dem.call_args.kwargs
    assert dem_kwargs["output_epsg"] == 32632
    assert isinstance(dem_kwargs["bounds"], list)

    assert result.valid is True
