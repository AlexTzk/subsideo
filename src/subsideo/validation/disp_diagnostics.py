"""Pure DISP diagnostic helpers for Phase 10 ERA5 delta assessment."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path

import numpy as np

from subsideo.validation.matrix_schema import (
    CacheMode,
    CacheProvenance,
    CauseAssessment,
    DemDiagnostics,
    Era5Diagnostic,
    OrbitCoverageDiagnostic,
    TerrainDiagnostics,
)

ATTRIBUTION_FLIP_SIGNAL = "attribution_flip"
REFERENCE_CORRELATION_SIGNAL = "reference_correlation_improved"
BIAS_OR_RMSE_SIGNAL = "bias_or_rmse_improved"
RAMP_REDUCTION_SIGNAL = "ramp_magnitude_reduced"


def sha256_file(path: Path) -> str:
    """Return the SHA256 hex digest for a file."""

    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _read_dem_array(dem_path: Path) -> tuple[np.ndarray, np.ndarray, float, float]:
    import rasterio

    with rasterio.open(dem_path) as ds:
        band = ds.read(1, masked=True)
        data = np.asarray(band.filled(np.nan), dtype=np.float64)
        valid = np.isfinite(data)
        if np.ma.is_masked(band):
            valid &= ~np.ma.getmaskarray(band)
        pixel_x_m = abs(float(ds.transform.a)) or 1.0
        pixel_y_m = abs(float(ds.transform.e)) or pixel_x_m
    return data, valid, pixel_y_m, pixel_x_m


def _slope_degrees(data: np.ndarray, valid: np.ndarray, pixel_y_m: float, pixel_x_m: float) -> np.ndarray:
    if valid.any():
        fill = float(np.nanmedian(data[valid]))
    else:
        fill = 0.0
    work = np.where(valid, data, fill)
    dz_dy, dz_dx = np.gradient(work, pixel_y_m, pixel_x_m)
    slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    slope = np.degrees(slope_rad).astype(np.float64)
    return np.where(valid, slope, np.nan)


def _finite_percentile(values: np.ndarray, q: float) -> float | None:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return None
    return float(np.percentile(finite, q))


def _finite_minmax(values: np.ndarray) -> tuple[float | None, float | None]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return None, None
    return float(finite.min()), float(finite.max())


def summarize_dem(dem_path: Path, *, tile_names: list[str] | None = None) -> DemDiagnostics:
    """Summarize a cached GLO-30 DEM without network access."""

    dem_path = Path(dem_path)
    data, valid, pixel_y_m, pixel_x_m = _read_dem_array(dem_path)
    slope = _slope_degrees(data, valid, pixel_y_m, pixel_x_m)
    elevation_min_m, elevation_max_m = _finite_minmax(data[valid])

    return DemDiagnostics(
        source="glo_30",
        tile_names=tile_names or [dem_path.name],
        dem_sha256=sha256_file(dem_path),
        nodata_fraction=float(1.0 - (int(valid.sum()) / float(valid.size))),
        elevation_min_m=elevation_min_m,
        elevation_max_m=elevation_max_m,
        slope_p50_deg=_finite_percentile(slope, 50),
        slope_p90_deg=_finite_percentile(slope, 90),
    )


def summarize_terrain(
    dem_path: Path,
    stable_mask: np.ndarray,
    ramp_magnitude: np.ndarray | None = None,
) -> TerrainDiagnostics:
    """Summarize terrain over stable-mask pixels, with optional ramp correlation."""

    data, valid, pixel_y_m, pixel_x_m = _read_dem_array(Path(dem_path))
    slope = _slope_degrees(data, valid, pixel_y_m, pixel_x_m)
    stable = np.asarray(stable_mask, dtype=bool)
    if stable.shape != data.shape:
        raise ValueError(
            f"stable_mask shape {stable.shape} does not match DEM shape {data.shape}"
        )
    stable_valid = stable & valid
    stable_pixels = int(stable.sum())
    elevation_min_m, elevation_max_m = _finite_minmax(data[stable_valid])

    terrain_vs_ramp_pearson_r: float | None = None
    if ramp_magnitude is not None:
        ramp = np.asarray(ramp_magnitude, dtype=np.float64)
        if ramp.shape == data.shape:
            finite = stable_valid & np.isfinite(slope) & np.isfinite(ramp)
            if int(finite.sum()) >= 2:
                terrain_vs_ramp_pearson_r = float(np.corrcoef(slope[finite], ramp[finite])[0, 1])
                if not np.isfinite(terrain_vs_ramp_pearson_r):
                    terrain_vs_ramp_pearson_r = None

    return TerrainDiagnostics(
        stable_mask_pixels=stable_pixels,
        stable_mask_retention_fraction=(
            float(stable_pixels) / float(stable.size) if stable.size else 0.0
        ),
        elevation_min_m=elevation_min_m,
        elevation_max_m=elevation_max_m,
        slope_p50_deg=_finite_percentile(slope[stable_valid], 50),
        slope_p90_deg=_finite_percentile(slope[stable_valid], 90),
        terrain_vs_ramp_pearson_r=terrain_vs_ramp_pearson_r,
    )


_ORBIT_WINDOW_RE = re.compile(
    r"_V(?P<start>\d{8}T\d{6})_(?P<stop>\d{8}T\d{6})",
)


def _parse_orbit_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%dT%H%M%S")


def summarize_orbit_coverage(
    orbit_path: Path,
    sensing_time: datetime,
) -> OrbitCoverageDiagnostic:
    """Summarize orbit type and conservative filename validity-window coverage."""

    orbit_path = Path(orbit_path)
    name = orbit_path.name
    if "POEORB" in name:
        orbit_type = "POEORB"
    elif "RESORB" in name:
        orbit_type = "RESORB"
    else:
        orbit_type = "UNKNOWN"

    validity_start_iso = None
    validity_stop_iso = None
    covers_sensing_time: bool | None = None
    match = _ORBIT_WINDOW_RE.search(name)
    if match is not None:
        start = _parse_orbit_datetime(match.group("start"))
        stop = _parse_orbit_datetime(match.group("stop"))
        validity_start_iso = start.isoformat()
        validity_stop_iso = stop.isoformat()
        sensing = sensing_time.replace(tzinfo=None)
        covers_sensing_time = start <= sensing <= stop

    return OrbitCoverageDiagnostic(
        sensing_time_iso=sensing_time.isoformat(),
        orbit_filename=name,
        orbit_type=orbit_type,
        validity_start_iso=validity_start_iso,
        validity_stop_iso=validity_stop_iso,
        covers_sensing_time=covers_sensing_time,
    )


def cache_provenance(name: str, path: Path, cache_mode: CacheMode) -> CacheProvenance:
    """Return cache provenance, hashing existing files and tolerating missing paths."""

    path = Path(path)
    return CacheProvenance(
        name=name,
        path=str(path),
        sha256=sha256_file(path) if path.is_file() else None,
        cache_mode=cache_mode,
    )


def classify_era5_delta(
    *,
    baseline_correlation: float,
    era5_correlation: float,
    baseline_bias_mm_yr: float,
    era5_bias_mm_yr: float,
    baseline_rmse_mm_yr: float,
    era5_rmse_mm_yr: float,
    baseline_ramp_mean_magnitude_rad: float,
    era5_ramp_mean_magnitude_rad: float,
    attribution_flipped: bool,
    correlation_min_delta: float = 0.05,
    bias_abs_min_delta_mm_yr: float = 1.0,
    rmse_min_delta_mm_yr: float = 1.0,
    ramp_min_delta_rad: float = 5.0,
) -> Era5Diagnostic:
    """Classify ERA5-on deltas using Phase 10's two-signal rule.

    Delta fields are positive when the ERA5-on run improves over the baseline.
    ``meaningful_improvement`` is true only when at least two independent
    improvement signals are present.
    """

    correlation_delta = era5_correlation - baseline_correlation
    bias_abs_delta_mm_yr = abs(baseline_bias_mm_yr) - abs(era5_bias_mm_yr)
    rmse_delta_mm_yr = baseline_rmse_mm_yr - era5_rmse_mm_yr
    ramp_magnitude_delta_rad = (
        baseline_ramp_mean_magnitude_rad - era5_ramp_mean_magnitude_rad
    )

    improvement_signals: list[str] = []
    if attribution_flipped:
        improvement_signals.append(ATTRIBUTION_FLIP_SIGNAL)
    if correlation_delta >= correlation_min_delta:
        improvement_signals.append(REFERENCE_CORRELATION_SIGNAL)
    if (
        bias_abs_delta_mm_yr >= bias_abs_min_delta_mm_yr
        or rmse_delta_mm_yr >= rmse_min_delta_mm_yr
    ):
        improvement_signals.append(BIAS_OR_RMSE_SIGNAL)
    if ramp_magnitude_delta_rad >= ramp_min_delta_rad:
        improvement_signals.append(RAMP_REDUCTION_SIGNAL)

    return Era5Diagnostic(
        mode="on",
        baseline_correlation=baseline_correlation,
        era5_correlation=era5_correlation,
        correlation_delta=correlation_delta,
        baseline_bias_mm_yr=baseline_bias_mm_yr,
        era5_bias_mm_yr=era5_bias_mm_yr,
        bias_abs_delta_mm_yr=bias_abs_delta_mm_yr,
        baseline_rmse_mm_yr=baseline_rmse_mm_yr,
        era5_rmse_mm_yr=era5_rmse_mm_yr,
        rmse_delta_mm_yr=rmse_delta_mm_yr,
        baseline_ramp_mean_magnitude_rad=baseline_ramp_mean_magnitude_rad,
        era5_ramp_mean_magnitude_rad=era5_ramp_mean_magnitude_rad,
        ramp_magnitude_delta_rad=ramp_magnitude_delta_rad,
        improvement_signals=improvement_signals,
        meaningful_improvement=len(improvement_signals) >= 2,
    )


def assess_causes_from_era5(era5: Era5Diagnostic, *, next_test: str) -> CauseAssessment:
    """Return the structured cause assessment implied by an ERA5 diagnostic."""

    if era5.mode == "on" and not era5.meaningful_improvement:
        return CauseAssessment(
            human_verdict="inconclusive_narrowed",
            eliminated_causes=["tropospheric"],
            remaining_causes=[
                "orbit",
                "terrain",
                "unwrapper",
                "cache_or_input_provenance",
            ],
            next_test=next_test,
        )

    return CauseAssessment(
        human_verdict="inconclusive",
        remaining_causes=[
            "tropospheric",
            "orbit",
            "terrain",
            "unwrapper",
            "cache_or_input_provenance",
        ],
        next_test=next_test,
    )
