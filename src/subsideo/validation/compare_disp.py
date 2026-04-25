"""DISP-S1 product validation against EGMS / OPERA reference products.

Three comparison surfaces:

* :func:`compare_disp` -- EGMS **L3 Ortho** raster (vertical displacement).
  Projects subsideo LOS velocity to vertical via the incidence angle and
  resamples onto the EGMS reference grid (v1.0 ad-hoc ``Resampling.bilinear``).
* :func:`compare_disp_egms_l2a` -- EGMS **L2a** per-track PS point cloud
  (LOS mean_velocity, mm/yr). Samples our LOS velocity raster at each PS
  location (v1.0 ``rasterio.DatasetReader.sample`` nearest-neighbour); no
  vertical projection because both fields are LOS on the same orbit track.
* :func:`prepare_for_reference` -- Phase 4 multilook adapter. Validation-only
  infrastructure that converts subsideo's native 5x10 m DISP velocity to a
  reference grid (OPERA DISP 30 m raster path, xr.DataArray, or EGMS L2a PS
  point list) with an explicit ``method=`` argument over
  ``Literal["gaussian", "block_mean", "bilinear", "nearest"]`` (no default
  per DISP-01 + CONTEXT D-04 explicit-no-default). Production DISP output
  remains at native resolution -- this adapter is never wired into
  ``run_disp()`` and never writes back to the product (DISP-05).

  See ``docs/validation_methodology.md`` Sec 3 for the multilook-method ADR
  (Phase 4 D-03 + Phase 3 D-15 append-only doc policy). The eval-script
  default ``method="block_mean"`` is the conservative kernel that minimises
  kernel-flattery attack surface (Phase 4 D-02).

The L2a path is preferred for per-track comparisons because EGMS L2a is
calibrated per ascending/descending pass and is directly co-geometric with
a subsideo DISP run on the matching S1 relative orbit.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import rasterio
import rioxarray  # noqa: F401  (registers .rio accessor on xr.DataArray)
import xarray as xr
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

        # Optional mean_velocity_std column (Phase 3 D-12 stable-PS filter).
        # Existing compare_disp_egms_l2a does not require it; keep it as an
        # additive column only when the CSV publishes it (backward-compat).
        cols_to_keep = ["lon", "lat", velocity_col]
        if "mean_velocity_std" in df.columns:
            cols_to_keep.append("mean_velocity_std")
        frames.append(df[cols_to_keep])

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
        # Capture nodata while the dataset is still open; accessing src.nodata
        # after the ``with`` block exits raises RasterioIOError (CR-01).
        nodata = src.nodata
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


# --- Phase 4 multilook adapter (DISP-01 + DISP-05; CONTEXT D-01..D-04, D-17, D-18) ---


MultilookMethod = Literal["gaussian", "block_mean", "bilinear", "nearest"]


@dataclass(frozen=True)
class ReferenceGridSpec:
    """Reference-grid specification for point-sampling form (DISP-01 form c).

    Used when no raster reference exists -- e.g. EGMS L2a PS point cloud.
    The adapter samples the native velocity at each (lon, lat) coordinate
    rather than reprojecting onto a raster grid.

    Attributes
    ----------
    points_lonlat : (N, 2) np.ndarray
        Array of (lon, lat) coordinates in ``crs``.
    crs : str
        CRS the points are expressed in. Default ``"EPSG:4326"``.
    point_ids : list[str] | None
        Optional PS IDs for traceability; ignored by the adapter.
    """

    points_lonlat: np.ndarray
    crs: str = "EPSG:4326"
    point_ids: list[str] | None = None


def prepare_for_reference(
    native_velocity: Path | str | xr.DataArray,
    reference_grid: Path | str | xr.DataArray | ReferenceGridSpec,
    *,
    method: MultilookMethod | None = None,
) -> np.ndarray | xr.DataArray:
    """Multilook subsideo's native 5x10 m DISP velocity to a reference grid.

    Validation-only. Never writes back to the product (DISP-05 + research
    ARCHITECTURE Sec 3 + FEATURES anti-feature).

    Parameters
    ----------
    native_velocity : Path | str | xr.DataArray
        Path to the native-resolution velocity GeoTIFF (rad/yr LOS, dolphin
        convention) OR an ``xr.DataArray`` with CRS attached via rioxarray.
    reference_grid : Path | str | xr.DataArray | ReferenceGridSpec
        One of three forms (DISP-01):

        (a) Path to a GeoTIFF -- adapter reads CRS + transform + shape via
            rasterio and reprojects native onto the file's grid.
        (b) ``xr.DataArray`` with CRS encoded via rioxarray -- adapter
            reprojects native onto the array's grid.
        (c) :class:`ReferenceGridSpec` -- adapter point-samples the native
            raster at each (lon, lat) coordinate, returning a 1-D ndarray
            in PS-row order (no reprojection).
    method : MultilookMethod | None
        REQUIRED. One of ``{"gaussian", "block_mean", "bilinear", "nearest"}``.
        No default value (DISP-01 explicit-no-default policy). Raises
        :class:`ValueError` if ``None`` or anything outside the Literal.

    Returns
    -------
    np.ndarray | xr.DataArray
        Forms (a)/(b): velocity on reference grid as ``np.ndarray`` (matches
        existing ``compare_disp()`` pattern) OR ``xr.DataArray`` with CRS
        attached when input ``reference_grid`` was an ``xr.DataArray``
        (preserve type).
        Form (c): 1-D ``np.ndarray`` of sampled values, length ==
        ``len(spec.points_lonlat)``.

    Raises
    ------
    ValueError
        If ``method`` is ``None``, missing, or not in the Literal.
        If ``reference_grid`` form is unsupported.
    """
    if method is None:
        raise ValueError(
            "method= is required (DISP-01 explicit-no-default policy). "
            "Pick one of: 'gaussian', 'block_mean', 'bilinear', 'nearest'."
        )
    valid_methods = ("gaussian", "block_mean", "bilinear", "nearest")
    if method not in valid_methods:
        raise ValueError(
            f"method must be one of {valid_methods}; got {method!r}"
        )

    # Form discrimination
    if isinstance(reference_grid, ReferenceGridSpec):
        return _point_sample(native_velocity, reference_grid, method=method)
    if isinstance(reference_grid, (str, Path)):
        return _resample_onto_path(
            native_velocity, Path(reference_grid), method=method
        )
    if isinstance(reference_grid, xr.DataArray):
        return _resample_onto_dataarray(
            native_velocity, reference_grid, method=method
        )
    raise ValueError(
        f"reference_grid must be Path | xr.DataArray | ReferenceGridSpec; "
        f"got {type(reference_grid).__name__}"
    )


def _read_native_as_array(
    native: Path | str | xr.DataArray,
) -> tuple[np.ndarray, rasterio.Affine, rasterio.crs.CRS]:
    """Return (data, transform, crs) for a native velocity raster or DataArray.

    Capture nodata/transform BEFORE the with-block exits (CR-01 already-fixed
    gotcha mirrored from compare_disp_egms_l2a line 294).
    """
    if isinstance(native, xr.DataArray):
        data = native.values.astype(np.float64)
        transform = native.rio.transform()
        crs = native.rio.crs
        return data, transform, crs
    with rasterio.open(Path(native)) as src:
        data = src.read(1).astype(np.float64)
        transform = src.transform
        crs = src.crs
    return data, transform, crs


def _resample_onto_grid(
    src_data: np.ndarray,
    src_transform: rasterio.Affine,
    src_crs: rasterio.crs.CRS,
    dst_transform: rasterio.Affine,
    dst_crs: rasterio.crs.CRS,
    dst_shape: tuple[int, int],
    *,
    method: MultilookMethod,
) -> np.ndarray:
    """Method-dispatched multilook resample.

    Implements (per CONTEXT D-01 + RESEARCH lines 698-781):
      - block_mean : Resampling.average (rasterio-native block-mean / averaging)
      - bilinear   : Resampling.bilinear (v1.0 default; preserved for continuity)
      - nearest    : Resampling.nearest (degenerate; for kernel-comparison studies)
      - gaussian   : scipy.ndimage.gaussian_filter on src grid first, then
                      Resampling.nearest onto dst grid (PITFALLS P3.1 sigma=0.5*ref)
    """
    dst_data = np.full(dst_shape, np.nan, dtype=np.float64)
    if method == "gaussian":
        from scipy.ndimage import gaussian_filter  # lazy

        sigma_pix_y = (
            (0.5 * abs(dst_transform.e)) / abs(src_transform.e)
            if abs(src_transform.e) > 0
            else 0.0
        )
        sigma_pix_x = (
            (0.5 * abs(dst_transform.a)) / abs(src_transform.a)
            if abs(src_transform.a) > 0
            else 0.0
        )
        # NaN handling: scipy.ndimage.gaussian_filter is NOT NaN-safe; replace
        # NaN with 0.0 before filtering (RESEARCH lines 738-746).
        src_filled = np.where(np.isfinite(src_data), src_data, 0.0)
        src_smoothed = gaussian_filter(src_filled, sigma=(sigma_pix_y, sigma_pix_x))
        reproject(
            source=src_smoothed,
            destination=dst_data,
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,
        )
        return dst_data

    rmap: dict[str, Resampling] = {
        "block_mean": Resampling.average,
        "bilinear": Resampling.bilinear,
        "nearest": Resampling.nearest,
    }
    reproject(
        source=src_data,
        destination=dst_data,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        resampling=rmap[method],
    )
    return dst_data


def _resample_onto_path(
    native: Path | str | xr.DataArray,
    ref_path: Path,
    *,
    method: MultilookMethod,
) -> np.ndarray:
    """Form (a): reference is a GeoTIFF on disk."""
    src_data, src_transform, src_crs = _read_native_as_array(native)
    with rasterio.open(ref_path) as ref:
        dst_transform = ref.transform
        dst_crs = ref.crs
        dst_shape = (ref.height, ref.width)
    return _resample_onto_grid(
        src_data,
        src_transform,
        src_crs,
        dst_transform,
        dst_crs,
        dst_shape,
        method=method,
    )


def _resample_onto_dataarray(
    native: Path | str | xr.DataArray,
    ref_da: xr.DataArray,
    *,
    method: MultilookMethod,
) -> xr.DataArray:
    """Form (b): reference is an xr.DataArray with CRS via rioxarray."""
    src_data, src_transform, src_crs = _read_native_as_array(native)
    dst_transform = ref_da.rio.transform()
    dst_crs = ref_da.rio.crs
    if ref_da.ndim != 2:
        raise ValueError(
            f"reference_grid xr.DataArray must be 2-D (H, W); got ndim={ref_da.ndim}"
        )
    dst_shape: tuple[int, int] = (int(ref_da.shape[0]), int(ref_da.shape[1]))
    arr = _resample_onto_grid(
        src_data,
        src_transform,
        src_crs,
        dst_transform,
        dst_crs,
        dst_shape,
        method=method,
    )
    out = xr.DataArray(
        arr,
        dims=ref_da.dims,
        coords={d: ref_da.coords[d] for d in ref_da.dims if d in ref_da.coords},
    )
    out_with_crs: xr.DataArray = out.rio.write_crs(dst_crs).rio.write_transform(dst_transform)
    return out_with_crs


def _point_sample(
    native: Path | str | xr.DataArray,
    spec: ReferenceGridSpec,
    *,
    method: MultilookMethod,
) -> np.ndarray:
    """Form (c): point-sample the native raster at each (lon, lat).

    Implements all 4 methods at points:
      - nearest    : rasterio.DatasetReader.sample() at the projected point
      - bilinear   : 2x2-window read + scipy.ndimage.map_coordinates(order=1)
      - block_mean : N x M window around each point (N/M derived from the
                     reference cell size; for ReferenceGridSpec we use the
                     PS spacing from the median nearest-neighbour distance,
                     OR a default 6 px when only one point) + .mean() over
                     finite values
      - gaussian   : Gaussian-weighted window with sigma = 0.5 * cell_size

    For Phase 4 production callsite (block_mean), the simplest robust
    behaviour at points is: average all native pixels within a +/- N-pixel
    radius around each PS point, where N derives from the ratio of reference
    spacing to native spacing. When ``spec`` does not carry an explicit
    spacing, use a default radius of 6 native pixels (~30 m / 5 m = 6).

    NOTE: for the v1.1 EU eval (Bologna PS comparison), the eval script
    calls this with method='block_mean'. Reference spacing for EGMS L2a
    is irregular at the PS scale; the 6-px default is a reasonable proxy
    matching the OPERA 30 m / native 5 m ratio.
    """
    if isinstance(native, xr.DataArray):
        # We need the file/raster API for sample(); use a temp-disk write
        # only if needed. Cheaper path: convert to ndarray and project xy
        # via the DataArray's transform.
        src_data, src_transform, src_crs = _read_native_as_array(native)
        # Build a virtual MemoryFile for sample()-style access
        from rasterio.io import MemoryFile  # lazy

        height, width = src_data.shape
        with MemoryFile() as memfile:
            with memfile.open(
                driver="GTiff",
                height=height,
                width=width,
                count=1,
                dtype="float64",
                crs=src_crs,
                transform=src_transform,
            ) as ds:
                ds.write(src_data.astype(np.float64), 1)
            with memfile.open() as src_open:
                return _point_sample_from_dataset(src_open, spec, method=method)

    with rasterio.open(Path(native)) as src:
        return _point_sample_from_dataset(src, spec, method=method)


def _point_sample_from_dataset(
    src: rasterio.DatasetReader,
    spec: ReferenceGridSpec,
    *,
    method: MultilookMethod,
) -> np.ndarray:
    """Sample the open dataset at each spec point. Captures nodata/transform
    BEFORE the with-block exits (CR-01 mirror from compare_disp_egms_l2a:294).
    """
    from pyproj import Transformer  # lazy

    raster_crs = src.crs
    src_transform = src.transform
    src_data = src.read(1).astype(np.float64)  # capture early for window reads
    nodata = src.nodata  # capture before with-block exit

    transformer = Transformer.from_crs(spec.crs, raster_crs, always_xy=True)
    xs, ys = transformer.transform(
        spec.points_lonlat[:, 0],
        spec.points_lonlat[:, 1],
    )

    n = len(spec.points_lonlat)
    out = np.full(n, np.nan, dtype=np.float64)

    if method == "nearest":
        xy = list(zip(xs, ys, strict=True))
        sampled = np.array([v[0] for v in src.sample(xy)], dtype=np.float64)
        # Honor nodata
        if nodata is not None:
            sampled = np.where(sampled == nodata, np.nan, sampled)
        return sampled

    # Convert (xs, ys) world coords -> (row, col) pixel coords using inverse
    # affine (a, b, c, d, e, f).
    inv = ~src_transform
    cols, rows = inv * (np.asarray(xs), np.asarray(ys))
    rows = np.asarray(rows, dtype=np.float64)
    cols = np.asarray(cols, dtype=np.float64)

    height, width = src_data.shape

    if method == "bilinear":
        from scipy.ndimage import map_coordinates  # lazy

        # map_coordinates expects (rows, cols) stack
        coords = np.vstack([rows, cols])
        sampled_bilinear = np.asarray(
            map_coordinates(
                src_data,
                coords,
                order=1,
                mode="constant",
                cval=np.nan,
                prefilter=False,
            ),
            dtype=np.float64,
        )
        return sampled_bilinear

    if method == "block_mean":
        # Radius in native pixels (+/- 6 px ~ 30m at 5x10 m posting)
        radius = 6
        for i in range(n):
            r = int(round(rows[i]))
            c = int(round(cols[i]))
            r0 = max(0, r - radius)
            r1 = min(height, r + radius + 1)
            c0 = max(0, c - radius)
            c1 = min(width, c + radius + 1)
            if r1 <= r0 or c1 <= c0:
                out[i] = np.nan
                continue
            win = src_data[r0:r1, c0:c1]
            valid = np.isfinite(win)
            if nodata is not None:
                valid &= win != nodata
            if not valid.any():
                out[i] = np.nan
            else:
                out[i] = float(win[valid].mean())
        return out

    if method == "gaussian":
        from scipy.ndimage import gaussian_filter, map_coordinates  # lazy

        # Apply a Gaussian smooth on the full raster, then bilinear-sample at the
        # projected (row, col). sigma = 0.5 * (reference cell / native cell);
        # we use radius=6 default (~30 m at 5x10 m) -> sigma ~ 3 px.
        src_filled = np.where(np.isfinite(src_data), src_data, 0.0)
        smoothed = gaussian_filter(src_filled, sigma=3.0)
        coords = np.vstack([rows, cols])
        sampled_gauss = np.asarray(
            map_coordinates(
                smoothed,
                coords,
                order=1,
                mode="constant",
                cval=np.nan,
                prefilter=False,
            ),
            dtype=np.float64,
        )
        return sampled_gauss

    raise ValueError(f"Unhandled method: {method}")
