"""DISP-S1 product validation against EGMS EU reference products.

Two comparison paths:

* :func:`compare_disp` -- EGMS **L3 Ortho** raster (vertical displacement).
  Projects subsideo LOS velocity to vertical via the incidence angle and
  resamples onto the EGMS reference grid.
* :func:`compare_disp_egms_l2a` -- EGMS **L2a** per-track PS point cloud
  (LOS mean_velocity, mm/yr). Samples our LOS velocity raster at each PS
  location; no vertical projection is needed because both fields are LOS
  on the same orbit track.

The L2a path is preferred for per-track comparisons because EGMS L2a is
calibrated per ascending/descending pass and is directly co-geometric with
a subsideo DISP run on the matching S1 relative orbit.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from loguru import logger
from rasterio.warp import Resampling, reproject

from subsideo.products.types import DISPValidationResult
from subsideo.validation.metrics import bias, rmse, spatial_correlation
from subsideo.validation.results import ProductQualityResult, ReferenceAgreementResult

# Sentinel-1 C-band carrier wavelength (m) -- used to convert LOS phase
# velocity (rad/yr) to surface-motion velocity (mm/yr).
SENTINEL1_WAVELENGTH_M = 0.05546576


def fetch_egms_ortho(
    bbox: tuple[float, float, float, float],
    output_dir: Path,
) -> Path:
    """Download EGMS Ortho product for a bounding box using EGMStoolkit.

    Args:
        bbox: Bounding box as (west, south, east, north) in WGS84 degrees.
        output_dir: Directory to save downloaded EGMS Ortho GeoTIFF(s).

    Returns:
        Path to the downloaded EGMS Ortho GeoTIFF.

    Raises:
        ImportError: If EGMStoolkit is not installed.
        FileNotFoundError: If no GeoTIFF files found after download.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        import EGMStoolkit  # noqa: F811
    except ImportError as err:
        raise ImportError(
            "EGMStoolkit is not installed. Install via pip: pip install EGMStoolkit"
        ) from err

    # EGMStoolkit download for Ortho-level vertical displacement product
    west, south, east, north = bbox
    EGMStoolkit.download(
        bbox=[west, south, east, north],
        product_level="Ortho",
        output_dir=str(output_dir),
    )

    # Find downloaded GeoTIFF(s)
    tif_files = sorted(output_dir.glob("*.tif"))
    if not tif_files:
        raise FileNotFoundError(
            f"No GeoTIFF files found in {output_dir} after EGMS download"
        )

    result_path = tif_files[0]
    logger.info(f"Downloaded EGMS Ortho product for bbox {bbox} to {output_dir}")
    return result_path


def _los_to_vertical(
    los_velocity: np.ndarray,
    incidence_angle: np.ndarray | float,
) -> np.ndarray:
    """Project LOS velocity to vertical component.

    Computes v_vert = v_los / cos(theta) where theta is incidence angle
    in degrees. Handles division by zero by returning NaN.

    Args:
        los_velocity: Line-of-sight velocity array (mm/yr).
        incidence_angle: Incidence angle in degrees (scalar or per-pixel array).

    Returns:
        Vertical velocity array (mm/yr).
    """
    theta_rad = np.radians(incidence_angle)
    cos_theta = np.cos(theta_rad)

    # Avoid division by zero
    with np.errstate(divide="ignore", invalid="ignore"):
        vert = np.where(cos_theta != 0.0, los_velocity / cos_theta, np.nan)

    return vert


def compare_disp(
    product_path: Path,
    egms_ortho_path: Path,
    incidence_angle_path: Path | None = None,
    mean_incidence_deg: float = 33.0,
) -> DISPValidationResult:
    """Compare DISP-S1 velocity product against EGMS Ortho reference.

    Reprojects subsideo output to match the EGMS reference grid (never
    vice versa), projects LOS to vertical using incidence angle, and
    computes correlation and bias metrics over the intersection of valid
    pixels.

    Args:
        product_path: Path to subsideo DISP velocity GeoTIFF (mm/yr, LOS).
        egms_ortho_path: Path to EGMS Ortho vertical displacement GeoTIFF.
        incidence_angle_path: Optional path to per-pixel incidence angle
            GeoTIFF (degrees). If None, uses mean_incidence_deg.
        mean_incidence_deg: Fallback mean incidence angle in degrees.
            Default 33.0 (typical Sentinel-1 IW).

    Returns:
        DISPValidationResult with correlation, bias, and pass criteria.
    """
    # 1. Load EGMS reference grid (target grid -- per Pitfall 4)
    with rasterio.open(egms_ortho_path) as ref:
        egms_data = ref.read(1).astype(np.float64)
        egms_transform = ref.transform
        egms_crs = ref.crs

    # 2. Reproject subsideo product to match EGMS grid
    prod_aligned = np.empty_like(egms_data)
    with rasterio.open(product_path) as prod:
        reproject(
            source=rasterio.band(prod, 1),
            destination=prod_aligned,
            dst_transform=egms_transform,
            dst_crs=egms_crs,
            resampling=Resampling.bilinear,
        )

    # 3. Load or construct incidence angle
    if incidence_angle_path is not None:
        inc_aligned = np.empty_like(egms_data)
        with rasterio.open(incidence_angle_path) as inc:
            reproject(
                source=rasterio.band(inc, 1),
                destination=inc_aligned,
                dst_transform=egms_transform,
                dst_crs=egms_crs,
                resampling=Resampling.bilinear,
            )
        incidence_angle: np.ndarray | float = inc_aligned
    else:
        incidence_angle = mean_incidence_deg

    # 4. Project LOS to vertical
    vert_velocity = _los_to_vertical(prod_aligned, incidence_angle)

    # 5. Mask to intersection: metrics only over valid pixels in both arrays
    valid = np.isfinite(vert_velocity) & np.isfinite(egms_data)
    vert_masked = np.where(valid, vert_velocity, np.nan)
    egms_masked = np.where(valid, egms_data, np.nan)

    # 6. Compute metrics using shared functions
    corr = spatial_correlation(vert_masked, egms_masked)
    bias_val = bias(vert_masked, egms_masked)

    logger.info(f"DISP validation: r={corr:.4f}, bias={bias_val:.2f} mm/yr")

    return DISPValidationResult(
        product_quality=ProductQualityResult(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResult(
            measurements={"correlation": corr, "bias_mm_yr": bias_val},
            criterion_ids=["disp.correlation_min", "disp.bias_mm_yr_max"],
        ),
    )


def _load_egms_l2a_points(
    csv_paths: list[Path],
    velocity_col: str = "mean_velocity",
) -> pd.DataFrame:
    """Load one or more EGMS L2a CSV files into a single DataFrame.

    EGMS L2a CSV schema (per the EGMS user manual / EGMStoolkit
    ``datamergingcsv`` output): pid, easting/northing or longitude/latitude,
    height, mean_velocity (mm/yr), mean_velocity_std, acceleration, ...,
    followed by per-epoch displacement columns (YYYYMMDD).

    Column naming varies between EGMS releases: some use ``longitude``/
    ``latitude``, others use ``easting``/``northing`` (EPSG:3035 metres).
    This loader accepts either.

    Returns a DataFrame with at least ``lon``, ``lat``, and
    ``velocity_col`` columns.
    """
    frames: list[pd.DataFrame] = []
    for p in csv_paths:
        df = pd.read_csv(p)
        cols = {c.lower(): c for c in df.columns}
        if "longitude" in cols and "latitude" in cols:
            df = df.rename(columns={cols["longitude"]: "lon", cols["latitude"]: "lat"})
        elif "easting" in cols and "northing" in cols:
            # EGMS releases 2018_2022 / 2019_2023 publish L2a in EPSG:3035
            # (ETRS89-LAEA) metres. Reproject to lon/lat for a uniform downstream API.
            from pyproj import Transformer

            t = Transformer.from_crs(3035, 4326, always_xy=True)
            lon, lat = t.transform(df[cols["easting"]].values, df[cols["northing"]].values)
            df["lon"] = lon
            df["lat"] = lat
        else:
            raise ValueError(
                f"EGMS L2a file {p.name} has no lon/lat or easting/northing columns: "
                f"{list(df.columns)[:10]}"
            )

        if velocity_col not in df.columns:
            raise ValueError(
                f"EGMS L2a file {p.name} is missing velocity column "
                f"'{velocity_col}'. Available: {list(df.columns)[:15]}"
            )

        frames.append(df[["lon", "lat", velocity_col]])

    merged = pd.concat(frames, ignore_index=True)
    logger.info("Loaded {} EGMS L2a points from {} file(s)", len(merged), len(csv_paths))
    return merged


def compare_disp_egms_l2a(
    velocity_path: Path,
    egms_csv_paths: list[Path],
    velocity_col: str = "mean_velocity",
    velocity_units: str = "rad_per_year",
) -> DISPValidationResult:
    """Compare subsideo DISP LOS velocity against EGMS L2a PS points.

    Samples the subsideo LOS velocity raster at every EGMS PS location
    (nearest-neighbour via :meth:`rasterio.DatasetReader.sample`), converts
    our velocity to mm/yr if needed, and computes correlation, bias, and
    RMSE over the paired samples.

    Both fields are LOS on the matching S1 ascending track, so no vertical
    projection is applied -- this is the fairest per-track comparison.

    Args:
        velocity_path: subsideo DISP velocity GeoTIFF. Units are controlled
            by ``velocity_units``; dolphin writes LOS phase-rate in rad/yr
            by default.
        egms_csv_paths: One or more EGMS L2a CSV files (typically produced
            by ``EGMStoolkit.datamergingcsv``).
        velocity_col: EGMS column with LOS mean velocity in mm/yr.
            Default ``"mean_velocity"``.
        velocity_units: ``"rad_per_year"`` (default, dolphin native) or
            ``"mm_per_year"`` (already post-processed). If rad/yr, values
            are converted via the Sentinel-1 wavelength: ``v_mm = -v_rad *
            λ / (4π) * 1000``.

    Returns:
        DISPValidationResult with correlation, bias (mm/yr), and the
        project pass criteria (r > 0.92, |bias| < 3 mm/yr).
    """
    import geopandas as gpd
    from shapely.geometry import Point

    df = _load_egms_l2a_points([Path(p) for p in egms_csv_paths], velocity_col=velocity_col)

    # Build PS points in EPSG:4326, then reproject to the velocity raster CRS
    points = gpd.GeoDataFrame(
        df,
        geometry=[Point(xy) for xy in zip(df["lon"], df["lat"], strict=True)],
        crs="EPSG:4326",
    )

    with rasterio.open(velocity_path) as src:
        raster_crs = src.crs
        points_proj = points.to_crs(raster_crs)

        # Clip to raster bounds before sampling to avoid wasted I/O
        left, bottom, right, top = src.bounds
        in_bounds = (
            (points_proj.geometry.x >= left)
            & (points_proj.geometry.x <= right)
            & (points_proj.geometry.y >= bottom)
            & (points_proj.geometry.y <= top)
        )
        points_in = points_proj[in_bounds].copy()
        logger.info(
            "EGMS PS points inside velocity raster: {} / {}",
            len(points_in),
            len(points_proj),
        )

        if len(points_in) == 0:
            logger.warning("No EGMS PS points fall inside the velocity raster extent")
            return DISPValidationResult(
                product_quality=ProductQualityResult(measurements={}, criterion_ids=[]),
                reference_agreement=ReferenceAgreementResult(
                    measurements={
                        "correlation": float("nan"),
                        "bias_mm_yr": float("nan"),
                    },
                    criterion_ids=["disp.correlation_min", "disp.bias_mm_yr_max"],
                ),
            )

        xy = list(zip(points_in.geometry.x, points_in.geometry.y, strict=True))
        sampled = np.array([v[0] for v in src.sample(xy)], dtype=np.float64)

    nodata = src.nodata if src.nodata is not None else None
    if nodata is not None:
        sampled = np.where(sampled == nodata, np.nan, sampled)

    # Convert our velocity to mm/yr if needed
    if velocity_units == "rad_per_year":
        our_mm = -sampled * SENTINEL1_WAVELENGTH_M / (4.0 * np.pi) * 1000.0
    elif velocity_units == "mm_per_year":
        our_mm = sampled
    else:
        raise ValueError(f"Unknown velocity_units: {velocity_units!r}")

    ref_mm = points_in[velocity_col].to_numpy(dtype=np.float64)

    valid = np.isfinite(our_mm) & np.isfinite(ref_mm) & (our_mm != 0)
    n_valid = int(valid.sum())
    logger.info("Valid paired samples: {} / {}", n_valid, len(ref_mm))

    if n_valid < 100:
        logger.warning("Too few valid pairs ({}) for meaningful statistics", n_valid)
        return DISPValidationResult(
            product_quality=ProductQualityResult(measurements={}, criterion_ids=[]),
            reference_agreement=ReferenceAgreementResult(
                measurements={
                    "correlation": float("nan"),
                    "bias_mm_yr": float("nan"),
                },
                criterion_ids=["disp.correlation_min", "disp.bias_mm_yr_max"],
            ),
        )

    # Metrics helpers expect same-shape arrays; pass 1-D paired slices
    pred = our_mm[valid]
    ref = ref_mm[valid]

    corr = spatial_correlation(pred, ref)
    bias_val = bias(pred, ref)
    rmse_val = rmse(pred, ref)

    logger.info(
        "DISP vs EGMS L2a: r={:.4f}  bias={:+.2f} mm/yr  RMSE={:.2f} mm/yr  N={}",
        corr,
        bias_val,
        rmse_val,
        n_valid,
    )

    return DISPValidationResult(
        product_quality=ProductQualityResult(measurements={}, criterion_ids=[]),
        reference_agreement=ReferenceAgreementResult(
            measurements={"correlation": corr, "bias_mm_yr": bias_val},
            criterion_ids=["disp.correlation_min", "disp.bias_mm_yr_max"],
        ),
    )
