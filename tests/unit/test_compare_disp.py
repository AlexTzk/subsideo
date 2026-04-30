"""Regression tests for DISP validation comparison helpers."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

from subsideo.validation.compare_disp import (
    _resample_onto_grid,
    compare_disp_egms_l2a,
)


def test_compare_disp_egms_l2a_captures_nodata_before_dataset_closes(
    tmp_path: Path,
) -> None:
    """CR-01: nodata handling must not access a closed rasterio dataset."""
    velocity_path = tmp_path / "velocity.tif"
    transform = from_origin(0.0, 20.0, 1.0, 1.0)
    data = np.add.outer(np.arange(20.0), np.arange(20.0)).astype(np.float32) + 1.0
    data[0, 0] = -9999.0

    with rasterio.open(
        velocity_path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(data, 1)

    rows = []
    for row in range(data.shape[0]):
        for col in range(data.shape[1]):
            x, y = rasterio.transform.xy(transform, row, col)
            rows.append(
                {"longitude": x, "latitude": y, "mean_velocity": float(data[row, col])}
            )
    csv_path = tmp_path / "egms.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    result = compare_disp_egms_l2a(
        velocity_path,
        [csv_path],
        velocity_units="mm_per_year",
    )

    measurements = result.reference_agreement.measurements
    assert measurements["correlation"] == measurements["correlation"]
    assert measurements["bias_mm_yr"] == measurements["bias_mm_yr"]


def test_resample_onto_grid_preserves_nan_for_untouched_cells() -> None:
    """HI-01: rasterio reproject must leave no-overlap destination cells as NaN."""
    src_data = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64)
    src_transform = from_origin(0.0, 2.0, 1.0, 1.0)
    dst_transform = from_origin(-1.0, 3.0, 1.0, 1.0)
    crs = CRS.from_epsg(4326)

    resampled = _resample_onto_grid(
        src_data,
        src_transform,
        crs,
        dst_transform,
        crs,
        (4, 4),
        method="nearest",
    )

    assert np.isnan(resampled[0, 0])
    assert np.isnan(resampled[-1, -1])
    assert np.isfinite(resampled[1:3, 1:3]).all()
