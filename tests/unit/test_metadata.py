"""Tests for OPERA metadata injection utility."""
from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds

from subsideo._metadata import inject_opera_metadata


@pytest.fixture
def tiny_geotiff(tmp_path: Path) -> Path:
    """Create a minimal 4x4 GeoTIFF for metadata testing."""
    path = tmp_path / "test.tif"
    data = np.ones((4, 4), dtype=np.uint8)
    transform = from_bounds(0, 0, 1, 1, 4, 4)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=4,
        width=4,
        count=1,
        dtype="uint8",
        crs="EPSG:4326",
        transform=transform,
    ) as ds:
        ds.write(data, 1)
    return path


@pytest.fixture
def tiny_hdf5(tmp_path: Path) -> Path:
    """Create a minimal HDF5 file for metadata testing."""
    path = tmp_path / "test.h5"
    with h5py.File(path, "w") as f:
        f.create_dataset("data", data=np.zeros((4, 4)))
    return path


class TestInjectOperaMetadataGeoTIFF:
    def test_writes_tags(self, tiny_geotiff: Path):
        inject_opera_metadata(
            tiny_geotiff,
            product_type="DSWx-S2",
            software_version="0.1.0",
            run_params={"threshold": 0.124},
        )
        with rasterio.open(tiny_geotiff) as ds:
            tags = ds.tags()
        assert tags["PRODUCT_TYPE"] == "DSWx-S2"
        assert tags["SOFTWARE_VERSION"] == "0.1.0"
        assert tags["SOFTWARE_NAME"] == "subsideo"
        assert "RUN_PARAMETERS" in tags
        assert "PRODUCTION_DATETIME" in tags

    def test_run_params_is_json(self, tiny_geotiff: Path):
        import json

        inject_opera_metadata(
            tiny_geotiff,
            product_type="RTC-S1",
            software_version="0.1.0",
            run_params={"burst_ids": ["T001"]},
        )
        with rasterio.open(tiny_geotiff) as ds:
            tags = ds.tags()
        parsed = json.loads(tags["RUN_PARAMETERS"])
        assert parsed["burst_ids"] == ["T001"]


class TestInjectOperaMetadataHDF5:
    def test_writes_identification_group(self, tiny_hdf5: Path):
        inject_opera_metadata(
            tiny_hdf5,
            product_type="CSLC-S1",
            software_version="0.2.0",
            run_params={"mode": "test"},
        )
        with h5py.File(tiny_hdf5, "r") as f:
            assert "/identification" in f
            grp = f["/identification"]
            assert grp.attrs["PRODUCT_TYPE"] == "CSLC-S1"
            assert grp.attrs["SOFTWARE_VERSION"] == "0.2.0"
            assert grp.attrs["SOFTWARE_NAME"] == "subsideo"
            assert "RUN_PARAMETERS" in grp.attrs
            assert "PRODUCTION_DATETIME" in grp.attrs

    def test_unknown_suffix_no_error(self, tmp_path: Path):
        """Unknown file extension should log a warning, not raise."""
        fake = tmp_path / "data.zarr"
        fake.touch()
        # Should not raise
        inject_opera_metadata(
            fake,
            product_type="TEST",
            software_version="0.0.1",
            run_params={},
        )
