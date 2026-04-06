"""Unit tests for IONEX wiring and OPERA metadata injection across all pipelines."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import h5py
import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds

from subsideo.products.types import CSLCConfig, CSLCResult, RTCResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AOI = {
    "type": "Polygon",
    "coordinates": [[[11, 48], [12, 48], [12, 49], [11, 49], [11, 48]]],
}

MOCK_STAC_ITEM = {
    "assets": {"data": {"href": "s3://eodata/test.zip"}},
    "properties": {
        "datetime": "2025-01-15T00:00:00",
        "platform": "S1A",
    },
}


def _make_test_hdf5(path: Path, *, with_data: bool = True) -> Path:
    """Create a minimal OPERA-like CSLC HDF5 file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as f:
        if with_data:
            grp = f.create_group("data")
            grp.create_dataset("VV", data=np.zeros((10, 10), dtype=np.complex64))
        f.create_group("metadata")
    return path


def _make_test_geotiff(path: Path, epsg: int = 32632, pixel_size: float = 30.0) -> Path:
    """Write a minimal 10x10 GeoTIFF."""
    path.parent.mkdir(parents=True, exist_ok=True)
    transform = from_bounds(
        500000, 4900000, 500000 + 10 * pixel_size, 4900000 + 10 * pixel_size, 10, 10
    )
    with rasterio.open(
        path, "w", driver="GTiff", height=10, width=10, count=1,
        dtype="float32", crs=CRS.from_epsg(epsg), transform=transform,
    ) as ds:
        ds.write(np.ones((1, 10, 10), dtype=np.float32))
    return path


# ---------------------------------------------------------------------------
# TestGetSoftwareVersion
# ---------------------------------------------------------------------------


class TestGetSoftwareVersion:
    """Tests for get_software_version() helper."""

    def test_returns_string(self) -> None:
        from subsideo._metadata import get_software_version

        result = get_software_version()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_dev_on_missing_package(self) -> None:
        from importlib.metadata import PackageNotFoundError

        from subsideo._metadata import get_software_version

        with patch(
            "importlib.metadata.version",
            side_effect=PackageNotFoundError("subsideo"),
        ):
            result = get_software_version()
        assert result == "dev"


# ---------------------------------------------------------------------------
# TestIonexWiringInCSLC
# ---------------------------------------------------------------------------


class TestIonexWiringInCSLC:
    """Tests for IONEX fetch wiring in run_cslc_from_aoi."""

    def _setup_mocks(self, mocker, tmp_path):
        """Common mock setup for CSLC from AOI tests."""
        # Settings
        mock_settings = MagicMock()
        mock_settings.cdse_client_id = "test-id"
        mock_settings.cdse_client_secret = "test-secret"
        mock_settings.earthdata_username = "ed_user"
        mock_settings.earthdata_password = "ed_pass"
        mocker.patch("subsideo.config.Settings", return_value=mock_settings)

        # CDSEClient
        mock_client = MagicMock()
        mock_client.search_stac.return_value = [MOCK_STAC_ITEM]

        def _fake_download(s3_path, output_path, **kwargs):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.touch()
            return output_path

        mock_client.download.side_effect = _fake_download
        mocker.patch("subsideo.data.cdse.CDSEClient", return_value=mock_client)

        # Burst query
        mock_burst = MagicMock()
        mock_burst.burst_id_jpl = "T123_456789_IW1"
        mock_burst.epsg = 32632
        mocker.patch(
            "subsideo.burst.frames.query_bursts_for_aoi",
            return_value=[mock_burst],
        )

        # DEM
        dem_path = tmp_path / "dem.tif"
        dem_path.touch()
        mocker.patch(
            "subsideo.data.dem.fetch_dem",
            return_value=(dem_path, {"driver": "GTiff"}),
        )

        # Orbit
        orbit_path = tmp_path / "orbit.EOF"
        orbit_path.touch()
        mocker.patch(
            "subsideo.data.orbits.fetch_orbit",
            return_value=orbit_path,
        )

        return mock_settings

    def test_ionex_fetched_and_passed_to_run_cslc(self, tmp_path, mocker) -> None:
        """fetch_ionex is called and tec_file is passed through to run_cslc."""
        self._setup_mocks(mocker, tmp_path)

        ionex_path = tmp_path / "ionex" / "test.ionex"
        mock_fetch_ionex = mocker.patch(
            "subsideo.data.ionosphere.fetch_ionex",
            return_value=ionex_path,
        )

        mock_cslc_result = CSLCResult(
            output_paths=[tmp_path / "cslc.h5"],
            runconfig_path=tmp_path / "runconfig.yaml",
            burst_ids=["T123_456789_IW1"],
            valid=True,
        )
        mock_run_cslc = mocker.patch(
            "subsideo.products.cslc.run_cslc",
            return_value=mock_cslc_result,
        )

        from subsideo.products.cslc import run_cslc_from_aoi

        result = run_cslc_from_aoi(
            aoi=AOI,
            date_range=("2025-01-01", "2025-03-01"),
            output_dir=tmp_path / "out",
        )

        # fetch_ionex was called with correct args
        mock_fetch_ionex.assert_called_once()
        fargs = mock_fetch_ionex.call_args
        assert fargs.kwargs["username"] == "ed_user"
        assert fargs.kwargs["password"] == "ed_pass"

        # tec_file passed to run_cslc
        mock_run_cslc.assert_called_once()
        assert mock_run_cslc.call_args.kwargs["tec_file"] == ionex_path
        assert result.valid is True

    def test_ionex_failure_warns_and_continues(self, tmp_path, mocker) -> None:
        """IONEX download failure does not crash; tec_file=None passed to run_cslc."""
        self._setup_mocks(mocker, tmp_path)

        mocker.patch(
            "subsideo.data.ionosphere.fetch_ionex",
            side_effect=ConnectionError("timeout"),
        )

        mock_cslc_result = CSLCResult(
            output_paths=[tmp_path / "cslc.h5"],
            runconfig_path=tmp_path / "runconfig.yaml",
            burst_ids=["T123_456789_IW1"],
            valid=True,
        )
        mock_run_cslc = mocker.patch(
            "subsideo.products.cslc.run_cslc",
            return_value=mock_cslc_result,
        )

        from subsideo.products.cslc import run_cslc_from_aoi

        result = run_cslc_from_aoi(
            aoi=AOI,
            date_range=("2025-01-01", "2025-03-01"),
            output_dir=tmp_path / "out",
        )

        # Pipeline did not crash
        mock_run_cslc.assert_called_once()
        assert mock_run_cslc.call_args.kwargs["tec_file"] is None
        assert result.valid is True


# ---------------------------------------------------------------------------
# TestMetadataInjectionInRTC
# ---------------------------------------------------------------------------


class TestMetadataInjectionInRTC:
    """Tests for inject_opera_metadata call in run_rtc."""

    def test_run_rtc_calls_inject_opera_metadata(self, tmp_path, mocker) -> None:
        out_dir = tmp_path / "out"
        cog_path = out_dir / "burst.cog.tif"
        tif_path = out_dir / "burst.tif"

        # Create a COG-like tif so glob finds it
        _make_test_geotiff(tif_path)

        # Mock opera-rtc
        mock_rtc_mod = MagicMock()
        mock_rtc_rc = MagicMock()
        mocker.patch.dict("sys.modules", {
            "rtc": MagicMock(),
            "rtc.rtc_s1": mock_rtc_mod,
            "rtc.runconfig": mock_rtc_rc,
        })
        mock_rtc_rc.RunConfig.load_from_yaml.return_value = MagicMock()
        mock_rtc_mod.run_parallel = MagicMock()

        # Mock ensure_cog to just copy the tif
        def _fake_ensure_cog(input_tif, output_cog=None):
            dst = input_tif.with_suffix(".cog.tif")
            _make_test_geotiff(dst)
            return dst

        mocker.patch("subsideo.products.rtc.ensure_cog", side_effect=_fake_ensure_cog)

        # Mock validation
        mocker.patch("subsideo.products.rtc.validate_rtc_product", return_value=[])

        # Mock inject_opera_metadata
        mock_inject = mocker.patch("subsideo._metadata.inject_opera_metadata")

        from subsideo.products.rtc import run_rtc

        result = run_rtc(
            safe_paths=[tmp_path / "S1A.zip"],
            orbit_path=tmp_path / "orbit.EOF",
            dem_path=tmp_path / "dem.tif",
            burst_ids=["T001"],
            output_dir=out_dir,
        )

        mock_inject.assert_called()
        inject_args = mock_inject.call_args
        assert inject_args.kwargs.get("product_type") or inject_args[1].get("product_type") or (
            len(inject_args[0]) > 1 and inject_args[0][1] == "RTC-S1"
        )


# ---------------------------------------------------------------------------
# TestMetadataInjectionInCSLC
# ---------------------------------------------------------------------------


class TestMetadataInjectionInCSLC:
    """Tests for inject_opera_metadata call in run_cslc."""

    def test_run_cslc_calls_inject_opera_metadata(self, tmp_path, mocker) -> None:
        out_dir = tmp_path / "out"
        h5_path = out_dir / "t001_123456_iw1_20230101.h5"

        def _fake_compass_run(run_config_path, grid_type):
            _make_test_hdf5(h5_path)

        mock_module = MagicMock()
        mock_module.run = _fake_compass_run
        mocker.patch.dict("sys.modules", {
            "compass": MagicMock(),
            "compass.s1_cslc": mock_module,
        })

        mock_inject = mocker.patch("subsideo._metadata.inject_opera_metadata")

        from subsideo.products.cslc import run_cslc

        result = run_cslc(
            safe_paths=[tmp_path / "S1A.zip"],
            orbit_path=tmp_path / "orbit.EOF",
            dem_path=tmp_path / "dem.tif",
            burst_ids=["T001"],
            output_dir=out_dir,
        )

        mock_inject.assert_called()
        # Check product_type via positional or keyword arg
        c = mock_inject.call_args
        product_type = c.kwargs.get("product_type", c[1].get("product_type") if len(c) > 1 else c[0][1])
        assert product_type == "CSLC-S1"


# ---------------------------------------------------------------------------
# TestMetadataInjectionInDISP
# ---------------------------------------------------------------------------


class TestMetadataInjectionInDISP:
    """Tests for inject_opera_metadata call in run_disp."""

    def test_run_disp_calls_inject_opera_metadata(self, tmp_path, mocker) -> None:
        out_dir = tmp_path / "out"

        # Create CDS credentials
        cdsapirc = tmp_path / ".cdsapirc"
        cdsapirc.write_text("url: https://cds.climate.copernicus.eu/api\nkey: 12345:abc\n")

        # Mock dolphin
        mock_dolphin_cfg = MagicMock()
        mock_dolphin_outputs = MagicMock()
        ifg_tif = out_dir / "dolphin" / "ifg.tif"
        cor_tif = out_dir / "dolphin" / "cor.tif"
        mock_dolphin_outputs.stitched_ifg_paths = [str(ifg_tif)]
        mock_dolphin_outputs.stitched_cor_paths = [str(cor_tif)]
        mocker.patch.dict("sys.modules", {
            "dolphin": MagicMock(),
            "dolphin.workflows": MagicMock(),
            "dolphin.workflows.config": MagicMock(),
            "dolphin.workflows.displacement": MagicMock(),
            "tophu": MagicMock(),
            "mintpy": MagicMock(),
            "mintpy.smallbaselineApp": MagicMock(),
            "scipy": MagicMock(),
            "scipy.linalg": MagicMock(),
        })

        # Mock all internal stages
        mocker.patch(
            "subsideo.products.disp._run_dolphin_phase_linking",
            return_value=([ifg_tif], [cor_tif]),
        )
        mocker.patch(
            "subsideo.products.disp._apply_coherence_mask",
            return_value=[ifg_tif],
        )
        mocker.patch(
            "subsideo.products.disp._run_unwrapping",
            return_value=[out_dir / "unwrap" / "ifg_unwrapped.tif"],
        )
        mocker.patch(
            "subsideo.products.disp._check_unwrap_quality",
            return_value={"path": "test", "residual_rms": 0.1, "flagged": False},
        )

        # MintPy returns HDF5 files
        ts_h5 = out_dir / "mintpy" / "timeseries.h5"
        vel_h5 = out_dir / "mintpy" / "velocity.h5"
        _make_test_hdf5(ts_h5)
        _make_test_hdf5(vel_h5)

        mocker.patch(
            "subsideo.products.disp._generate_mintpy_template",
            return_value=out_dir / "mintpy" / "smallbaselineApp.cfg",
        )
        mocker.patch(
            "subsideo.products.disp._run_mintpy_timeseries",
            return_value=[ts_h5],
        )

        mock_inject = mocker.patch("subsideo._metadata.inject_opera_metadata")

        from subsideo.products.disp import run_disp

        cslc_paths = [tmp_path / "cslc1.h5", tmp_path / "cslc2.h5"]
        result = run_disp(
            cslc_paths=cslc_paths,
            output_dir=out_dir,
            cdsapirc_path=cdsapirc,
        )

        assert result.valid is True
        mock_inject.assert_called()
        # Check that DISP-S1 product type was used
        all_product_types = []
        for c in mock_inject.call_args_list:
            pt = c.kwargs.get("product_type", c[1].get("product_type") if len(c) > 1 else c[0][1])
            all_product_types.append(pt)
        assert "DISP-S1" in all_product_types


# ---------------------------------------------------------------------------
# TestMetadataInjectionInDIST
# ---------------------------------------------------------------------------


class TestMetadataInjectionInDIST:
    """Tests for inject_opera_metadata call in run_dist."""

    def test_run_dist_calls_inject_opera_metadata(self, tmp_path, mocker) -> None:
        out_dir = tmp_path / "out"

        # Mock dist_s1
        def _fake_dist_workflow(mgrs_tile_id, post_date, track_number, dst_dir):
            dst_dir.mkdir(parents=True, exist_ok=True)
            _make_test_geotiff(dst_dir / "dist_output.tif")

        mocker.patch.dict("sys.modules", {"dist_s1": MagicMock()})
        mocker.patch(
            "dist_s1.run_dist_s1_workflow",
            side_effect=_fake_dist_workflow,
        )

        # Mock validation
        mocker.patch("subsideo.products.dist.validate_dist_product", return_value=[])

        mock_inject = mocker.patch("subsideo._metadata.inject_opera_metadata")

        from subsideo.products.dist import run_dist

        result = run_dist(
            mgrs_tile_id="33UUP",
            post_date="2025-06-15",
            track_number=15,
            output_dir=out_dir,
        )

        mock_inject.assert_called()
        c = mock_inject.call_args
        product_type = c.kwargs.get("product_type", c[1].get("product_type") if len(c) > 1 else c[0][1])
        assert product_type == "DIST-S1"
        # Check run_params contains mgrs_tile_id
        run_params = c.kwargs.get("run_params", c[1].get("run_params") if len(c) > 1 else c[0][3])
        assert run_params["mgrs_tile_id"] == "33UUP"
