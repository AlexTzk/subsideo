"""Phase 10 DISP ERA5 diagnostic helper tests."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from subsideo.validation.disp_diagnostics import (
    assess_causes_from_era5,
    cache_provenance,
    classify_era5_delta,
    sha256_file,
    summarize_dem,
    summarize_orbit_coverage,
    summarize_terrain,
)
from subsideo.validation.matrix_schema import Era5Diagnostic


def _write_dem(path: Path) -> Path:
    data = np.array(
        [
            [10.0, 20.0, 35.0],
            [24.0, -9999.0, 55.0],
            [30.0, 48.0, 80.0],
        ],
        dtype=np.float32,
    )
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=from_origin(0.0, 90.0, 30.0, 30.0),
        nodata=-9999.0,
    ) as dst:
        dst.write(data, 1)
    return path


def test_summarize_dem_reports_glo30_hash_nodata_and_slope(tmp_path: Path) -> None:
    dem_path = _write_dem(tmp_path / "glo30_utm32611.tif")

    diagnostic = summarize_dem(dem_path, tile_names=["N33W117"])

    assert diagnostic.source == "glo_30"
    assert diagnostic.tile_names == ["N33W117"]
    assert diagnostic.dem_sha256 == sha256_file(dem_path)
    assert diagnostic.nodata_fraction == pytest.approx(1.0 / 9.0)
    assert 0.0 <= diagnostic.nodata_fraction <= 1.0
    assert diagnostic.elevation_min_m == pytest.approx(10.0)
    assert diagnostic.elevation_max_m == pytest.approx(80.0)
    assert diagnostic.slope_p50_deg is not None
    assert diagnostic.slope_p90_deg is not None


def test_summarize_terrain_reports_stable_mask_retention_and_correlation(
    tmp_path: Path,
) -> None:
    dem_path = _write_dem(tmp_path / "glo30_utm32611.tif")
    stable_mask = np.array(
        [
            [True, True, True],
            [True, False, True],
            [True, True, True],
        ],
        dtype=bool,
    )
    ramp = np.arange(9, dtype=np.float64).reshape(3, 3)

    diagnostic = summarize_terrain(dem_path, stable_mask, ramp)

    assert diagnostic.stable_mask_pixels == 8
    assert diagnostic.stable_mask_retention_fraction == pytest.approx(8.0 / 9.0)
    assert diagnostic.elevation_min_m == pytest.approx(10.0)
    assert diagnostic.elevation_max_m == pytest.approx(80.0)
    assert diagnostic.slope_p50_deg is not None
    assert diagnostic.slope_p90_deg is not None
    assert diagnostic.terrain_vs_ramp_pearson_r is not None


def test_summarize_orbit_coverage_parses_poeorb_validity_window() -> None:
    orbit = Path(
        "S1A_OPER_AUX_POEORB_OPOD_20240128T080731_"
        "V20240107T225942_20240109T005942.EOF"
    )

    diagnostic = summarize_orbit_coverage(
        orbit,
        datetime.fromisoformat("2024-01-08T14:01:16"),
    )

    assert diagnostic.orbit_filename == orbit.name
    assert diagnostic.orbit_type == "POEORB"
    assert diagnostic.validity_start_iso == "2024-01-07T22:59:42"
    assert diagnostic.validity_stop_iso == "2024-01-09T00:59:42"
    assert diagnostic.covers_sensing_time is True


def test_summarize_orbit_coverage_leaves_unknown_coverage_when_unparseable() -> None:
    diagnostic = summarize_orbit_coverage(
        Path("custom_orbit_file.EOF"),
        datetime.fromisoformat("2024-01-08T14:01:16"),
    )

    assert diagnostic.orbit_type == "UNKNOWN"
    assert diagnostic.validity_start_iso is None
    assert diagnostic.validity_stop_iso is None
    assert diagnostic.covers_sensing_time is None


def test_cache_provenance_hashes_existing_file_and_validates_mode(tmp_path: Path) -> None:
    payload = tmp_path / "velocity.tif"
    payload.write_bytes(b"disp velocity")

    diagnostic = cache_provenance("velocity_tif", payload, "reused")

    assert diagnostic.name == "velocity_tif"
    assert diagnostic.path == str(payload)
    assert diagnostic.sha256 == sha256_file(payload)
    assert diagnostic.cache_mode == "reused"


def test_cache_provenance_uses_null_hash_for_missing_file(tmp_path: Path) -> None:
    diagnostic = cache_provenance("missing", tmp_path / "missing.tif", "redownloaded")

    assert diagnostic.sha256 is None
    assert diagnostic.cache_mode == "redownloaded"


def test_classify_era5_delta_one_signal_ramp_only_is_not_meaningful() -> None:
    diagnostic = classify_era5_delta(
        baseline_correlation=0.049,
        era5_correlation=0.06,
        baseline_bias_mm_yr=23.6,
        era5_bias_mm_yr=23.2,
        baseline_rmse_mm_yr=59.6,
        era5_rmse_mm_yr=59.0,
        baseline_ramp_mean_magnitude_rad=35.6,
        era5_ramp_mean_magnitude_rad=28.0,
        attribution_flipped=False,
    )

    assert diagnostic.ramp_magnitude_delta_rad == pytest.approx(7.6)
    assert diagnostic.improvement_signals == ["ramp_magnitude_reduced"]
    assert diagnostic.meaningful_improvement is False


def test_classify_era5_delta_two_signals_is_meaningful() -> None:
    diagnostic = classify_era5_delta(
        baseline_correlation=0.049,
        era5_correlation=0.12,
        baseline_bias_mm_yr=23.6,
        era5_bias_mm_yr=21.9,
        baseline_rmse_mm_yr=59.6,
        era5_rmse_mm_yr=58.9,
        baseline_ramp_mean_magnitude_rad=35.6,
        era5_ramp_mean_magnitude_rad=34.0,
        attribution_flipped=False,
    )

    assert diagnostic.correlation_delta == pytest.approx(0.071)
    assert diagnostic.bias_abs_delta_mm_yr == pytest.approx(1.7)
    assert diagnostic.improvement_signals == [
        "reference_correlation_improved",
        "bias_or_rmse_improved",
    ]
    assert diagnostic.meaningful_improvement is True


def test_classify_era5_delta_keeps_signal_order_deterministic() -> None:
    diagnostic = classify_era5_delta(
        baseline_correlation=0.049,
        era5_correlation=0.12,
        baseline_bias_mm_yr=23.6,
        era5_bias_mm_yr=21.9,
        baseline_rmse_mm_yr=59.6,
        era5_rmse_mm_yr=57.0,
        baseline_ramp_mean_magnitude_rad=35.6,
        era5_ramp_mean_magnitude_rad=28.0,
        attribution_flipped=True,
    )

    assert diagnostic.improvement_signals == [
        "attribution_flip",
        "reference_correlation_improved",
        "bias_or_rmse_improved",
        "ramp_magnitude_reduced",
    ]


def test_assess_causes_no_improvement_era5_on_eliminates_only_tropospheric() -> None:
    diagnostic = Era5Diagnostic(
        mode="on",
        improvement_signals=["ramp_magnitude_reduced"],
        meaningful_improvement=False,
    )

    assessment = assess_causes_from_era5(
        diagnostic,
        next_test="Run SPURT native candidate.",
    )

    assert assessment.human_verdict == "inconclusive_narrowed"
    assert assessment.eliminated_causes == ["tropospheric"]
    assert assessment.remaining_causes == [
        "orbit",
        "terrain",
        "unwrapper",
        "cache_or_input_provenance",
    ]
    assert assessment.next_test == "Run SPURT native candidate."


def test_assess_causes_meaningful_improvement_keeps_causes_open() -> None:
    diagnostic = Era5Diagnostic(
        mode="on",
        improvement_signals=[
            "reference_correlation_improved",
            "bias_or_rmse_improved",
        ],
        meaningful_improvement=True,
    )

    assessment = assess_causes_from_era5(
        diagnostic,
        next_test="Compare Phase 11 baseline.",
    )

    assert assessment.human_verdict == "inconclusive"
    assert assessment.eliminated_causes == []
    assert assessment.remaining_causes == [
        "tropospheric",
        "orbit",
        "terrain",
        "unwrapper",
        "cache_or_input_provenance",
    ]
