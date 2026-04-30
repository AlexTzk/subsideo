"""Stable-terrain mask construction for CSLC/DISP self-consistency validation.

Combines four exclusion criteria to produce a boolean mask of pixels whose
displacement signal is expected to be dominated by real surface motion
(bare, flat, away from water and coastline) rather than noise or spurious
seasonal scattering shifts:

  1. WorldCover class 60 (bare / sparse vegetation) -- excludes vegetation,
     built-up, cropland, and other classes where the scattering mechanism
     shifts seasonally.
  2. Slope <= 10 degrees -- excludes steep terrain where layover / shadow
     corrupt InSAR signal.
  3. Coastline buffer (default 5 km) -- excludes the littoral zone where
     tidal loading, soil moisture, and wave spray introduce non-stationary
     decorrelation.
  4. Water-body buffer (default 500 m) -- excludes lake/river edges where
     shoreline motion and seasonal level changes corrupt stable-target
     assumptions.

Mitigates PITFALLS P2.1 (stable-mask false-positives from flooded cropland
+ reservoir edges).

Consumed by:
  - validation/selfconsistency.py (residual_mean_velocity)
  - Phase 3 CSLC self-consistency eval (compare_cslc)
  - Phase 4 DISP self-consistency eval (compare_disp)

Pure-function module -- no module-top I/O, no module-top conda-forge
imports. geopandas / shapely / rasterio are lazy-imported inside
`_buffered_geometry_mask` so pip-install-only consumers can import the
module without the conda stack present.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

import numpy as np
from loguru import logger

if TYPE_CHECKING:
    from affine import Affine
    from geopandas import GeoSeries
    from pyproj import CRS as PyprojCRS  # noqa: N811
    from rasterio.crs import CRS as RasterioCRS  # noqa: N811
    from shapely.geometry.base import BaseGeometry

    GeometryLike: TypeAlias = BaseGeometry | GeoSeries
    CRSLike: TypeAlias = RasterioCRS | PyprojCRS | str | int

WORLDCOVER_BARE_SPARSE_CLASS: int = 60  # ESA WorldCover v2 class code
DEFAULT_SLOPE_MAX_DEG: float = 10.0
DEFAULT_COAST_BUFFER_M: float = 5000.0
DEFAULT_WATER_BUFFER_M: float = 500.0


def build_stable_mask(
    worldcover: np.ndarray,
    slope_deg: np.ndarray,
    coastline: GeometryLike | None = None,
    waterbodies: GeometryLike | None = None,
    *,
    transform: Affine | None = None,
    crs: CRSLike | None = None,
    coast_buffer_m: float = DEFAULT_COAST_BUFFER_M,
    water_buffer_m: float = DEFAULT_WATER_BUFFER_M,
    slope_max_deg: float = DEFAULT_SLOPE_MAX_DEG,
) -> np.ndarray:
    """Return a boolean mask of stable-terrain pixels per CSLC-01.

    Parameters
    ----------
    worldcover : (H, W) int np.ndarray
        ESA WorldCover raster. Class codes include 10 (tree cover),
        20 (shrubland), 30 (grassland), 40 (cropland), 50 (built-up),
        60 (bare/sparse vegetation -- the stable class), 70 (snow/ice),
        80 (water), 90 (herbaceous wetland), 95 (mangroves),
        100 (moss/lichen).
    slope_deg : (H, W) float np.ndarray
        Slope in degrees (from DEM). NaN values are treated as non-stable.
    coastline : shapely.geometry.base.BaseGeometry | geopandas.GeoSeries | None
        Coastline geometry in the same CRS as ``transform`` / ``crs``. If None,
        coast buffer is not applied.
    waterbodies : shapely.geometry.base.BaseGeometry | geopandas.GeoSeries | None
        Water-body geometry (polygons). If None, water buffer is not applied.
    transform : affine.Affine | None
        Raster transform (required if ``coastline`` or ``waterbodies`` is
        provided).
    crs : rasterio.crs.CRS | pyproj.CRS | None
        Raster CRS (required if ``coastline`` or ``waterbodies`` is provided).
        Must be a metric (projected) CRS because buffer distances are in metres.
    coast_buffer_m : float, default 5000.0
        Distance from coastline to exclude.
    water_buffer_m : float, default 500.0
        Distance from water bodies to exclude.
    slope_max_deg : float, default 10.0
        Maximum slope (degrees) allowed.

    Returns
    -------
    mask : (H, W) bool np.ndarray
        True where pixel is considered stable terrain (all four gates pass).

    Raises
    ------
    ValueError
        If ``worldcover`` and ``slope_deg`` have mismatched shapes, or if
        a geometry is provided without ``transform`` / ``crs``.

    Notes
    -----
    Returns an all-False mask of matching shape if ``worldcover`` contains
    no ``WORLDCOVER_BARE_SPARSE_CLASS`` pixels. Never raises on an empty
    intersection.
    """
    if worldcover.shape != slope_deg.shape:
        raise ValueError(
            f"worldcover shape {worldcover.shape} != slope_deg shape {slope_deg.shape}"
        )

    # (1) WorldCover class filter
    base = worldcover == WORLDCOVER_BARE_SPARSE_CLASS

    # (2) Slope gate (NaN slope is excluded)
    slope_ok = np.isfinite(slope_deg) & (slope_deg <= slope_max_deg)

    mask = base & slope_ok

    # (3) Coastline buffer -- rasterise buffered coastline into an exclusion mask
    if coastline is not None:
        if transform is None or crs is None:
            raise ValueError("coastline provided but transform/crs missing")
        exclude = _buffered_geometry_mask(
            coastline,
            transform=transform,
            crs=crs,
            shape=mask.shape,
            buffer_m=coast_buffer_m,
        )
        mask &= ~exclude

    # (4) Water-body buffer
    if waterbodies is not None:
        if transform is None or crs is None:
            raise ValueError("waterbodies provided but transform/crs missing")
        exclude = _buffered_geometry_mask(
            waterbodies,
            transform=transform,
            crs=crs,
            shape=mask.shape,
            buffer_m=water_buffer_m,
        )
        mask &= ~exclude

    mask_bool: np.ndarray = np.asarray(mask, dtype=bool)
    n_valid = int(mask_bool.sum())
    logger.debug(
        "build_stable_mask: {} stable px (class_60={}, slope_ok={}, final={})",
        n_valid,
        int(base.sum()),
        int((base & slope_ok).sum()),
        n_valid,
    )
    return mask_bool


def _buffered_geometry_mask(
    geometry: GeometryLike,
    *,
    transform: Affine,
    crs: CRSLike,
    shape: tuple[int, int],
    buffer_m: float,
) -> np.ndarray:
    """Rasterise ``geometry.buffer(buffer_m)`` into a boolean exclusion mask.

    Lazy-imports geopandas, shapely, and rasterio so the top-level module
    can be imported by pip-install-only consumers without those heavies.

    The caller's CRS must already be a projected (metric) CRS because the
    buffer width is in metres.
    """
    import geopandas as gpd
    from rasterio.features import rasterize
    from shapely.geometry.base import BaseGeometry

    if isinstance(geometry, BaseGeometry):
        gs = gpd.GeoSeries([geometry], crs=crs)
    elif isinstance(geometry, gpd.GeoSeries):
        gs = geometry
    else:
        # GeoDataFrame or any iterable of geometries
        gs = gpd.GeoSeries(geometry, crs=crs)

    if getattr(gs, "crs", None) is not None and str(gs.crs) != str(crs):
        gs = gs.to_crs(crs)

    # buffer() on a metric CRS produces polygons in the same CRS
    buffered = gs.buffer(buffer_m)
    geoms = [(g, 1) for g in buffered.geometry if g is not None and not g.is_empty]
    if not geoms:
        return np.zeros(shape, dtype=bool)
    raster = rasterize(
        geoms,
        out_shape=shape,
        transform=transform,
        fill=0,
        default_value=1,
        dtype="uint8",
    )
    result: np.ndarray = np.asarray(raster, dtype=bool)
    return result
