"""DSWx-S2 surface water extent pipeline orchestrator.

Ports the OPERA DSWx-HLS DSWE algorithm (PROTEUS, Apache 2.0) to
Sentinel-2 L2A bands. Classifies pixels into DSWE water classes using
five diagnostic spectral tests, applies SCL cloud masking, and outputs
a 30m UTM Cloud-Optimized GeoTIFF.

All rasterio/rio_cogeo imports are lazy -- kept inside function bodies
so the module is importable without conda-forge-only packages.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from loguru import logger

from subsideo.products.types import DSWxConfig, DSWxResult

__all__ = ["run_dswx", "run_dswx_from_aoi"]

# ---------------------------------------------------------------------------
# DSWE diagnostic test thresholds (PROTEUS defaults)
# ---------------------------------------------------------------------------

WIGT = 0.124  # MNDWI threshold for Test 1
AWGT = 0.0  # AWESH threshold for Test 3

PSWT1_MNDWI = -0.44
PSWT1_NIR = 1500  # scaled reflectance (0.15)
PSWT1_SWIR1 = 900  # scaled reflectance (0.09)
PSWT1_NDVI = 0.7

PSWT2_MNDWI = -0.5
PSWT2_BLUE = 1000  # scaled reflectance (0.10)
PSWT2_NIR = 2500  # scaled reflectance (0.25)
PSWT2_SWIR1 = 3000  # scaled reflectance (0.30)
PSWT2_SWIR2 = 1000  # scaled reflectance (0.10)

# SCL cloud mask values (D-02): cloud shadow(3), cloud med(8), cloud high(9), cirrus(10)
SCL_MASK_VALUES = frozenset({3, 8, 9, 10})

# Diagnostic-to-water-class lookup (32 entries, from PROTEUS)
# 0=Not Water, 1=High Confidence, 2=Moderate, 3=Potential Wetland, 4=Low Confidence
INTERPRETED_WATER_CLASS: dict[int, int] = {
    0b00000: 0, 0b00001: 0, 0b00010: 0, 0b00011: 2,
    0b00100: 0, 0b00101: 2, 0b00110: 2, 0b00111: 1,
    0b01000: 3, 0b01001: 3, 0b01010: 3, 0b01011: 1,
    0b01100: 3, 0b01101: 1, 0b01110: 1, 0b01111: 1,
    0b10000: 4, 0b10001: 4, 0b10010: 4, 0b10011: 2,
    0b10100: 4, 0b10101: 2, 0b10110: 2, 0b10111: 1,
    0b11000: 3, 0b11001: 3, 0b11010: 3, 0b11011: 1,
    0b11100: 3, 0b11101: 1, 0b11110: 1, 0b11111: 1,
}


# ---------------------------------------------------------------------------
# Internal: diagnostic test computation
# ---------------------------------------------------------------------------


def _compute_diagnostic_tests(
    blue: np.ndarray,
    green: np.ndarray,
    red: np.ndarray,
    nir: np.ndarray,
    swir1: np.ndarray,
    swir2: np.ndarray,
) -> np.ndarray:
    """Compute 5-bit DSWE diagnostic layer from S2 L2A bands.

    All band arrays must be uint16 scaled integer reflectance (x10000).
    Returns uint8 array with bits 0-4 representing diagnostic tests 1-5.
    """
    eps = 1e-10

    # Scale-invariant ratios
    green_f = green.astype(np.float32)
    nir_f = nir.astype(np.float32)
    red_f = red.astype(np.float32)
    swir1_f = swir1.astype(np.float32)

    mndwi = (green_f - swir1_f) / (green_f + swir1_f + eps)
    ndvi = (nir_f - red_f) / (nir_f + red_f + eps)

    # Composite values (raw scaled reflectance)
    mbsrv = green_f + red_f
    mbsrn = nir_f + swir1_f
    awesh = (
        blue.astype(np.float32) + 2.5 * green_f
        - 1.5 * mbsrn - 0.25 * swir2.astype(np.float32)
    )

    diag = np.zeros(blue.shape, dtype=np.uint8)
    diag += np.uint8(mndwi > WIGT)                     # Test 1: bit 0
    diag += np.uint8(mbsrv > mbsrn) * 2                # Test 2: bit 1
    diag += np.uint8(awesh > AWGT) * 4                  # Test 3: bit 2

    # Test 4 (partial surface water - conservative): bit 3
    diag += np.uint8(
        (mndwi > PSWT1_MNDWI) & (swir1 < PSWT1_SWIR1)
        & (nir < PSWT1_NIR) & (ndvi < PSWT1_NDVI)
    ) * 8

    # Test 5 (partial surface water - aggressive): bit 4
    diag += np.uint8(
        (mndwi > PSWT2_MNDWI) & (blue < PSWT2_BLUE)
        & (swir1 < PSWT2_SWIR1) & (swir2 < PSWT2_SWIR2)
        & (nir < PSWT2_NIR)
    ) * 16

    return diag


def _classify_water(diagnostic: np.ndarray) -> np.ndarray:
    """Map 5-bit diagnostic values to DSWE water classes.

    Parameters
    ----------
    diagnostic:
        uint8 array of 5-bit diagnostic test results (0-31).

    Returns
    -------
    np.ndarray
        uint8 array of water classes (0-4, 255=fill).
    """
    # Vectorised lookup via fancy indexing
    lut = np.zeros(32, dtype=np.uint8)
    for k, v in INTERPRETED_WATER_CLASS.items():
        lut[k] = v
    # Clip diagnostic to 0-31 range for safety
    clipped = np.clip(diagnostic, 0, 31)
    return lut[clipped]


def _apply_scl_mask(
    water_class: np.ndarray,
    scl: np.ndarray,
) -> np.ndarray:
    """Set water_class to 255 (fill/nodata) where SCL indicates cloud/shadow.

    Parameters
    ----------
    water_class:
        uint8 water classification array.
    scl:
        uint8 Scene Classification Layer array.

    Returns
    -------
    np.ndarray
        Masked water_class array (255 = cloud/shadow fill).
    """
    result = water_class.copy()
    mask = np.isin(scl, list(SCL_MASK_VALUES))
    result[mask] = 255
    return result


# ---------------------------------------------------------------------------
# Internal: band I/O and COG output
# ---------------------------------------------------------------------------


def _read_s2_bands_at_20m(
    band_paths: dict[str, Path],
    scl_path: Path,
) -> tuple[dict[str, np.ndarray], np.ndarray, dict]:
    """Read all S2 L2A bands resampled to 20m grid aligned to B11.

    Uses rasterio.warp.reproject with bilinear for reflectance bands
    and nearest for SCL (categorical data, per Pitfall 2/3).

    Returns
    -------
    tuple
        (band_arrays, scl_array, profile_20m)
    """
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import reproject

    # Use B11 (native 20m) as the reference grid
    with rasterio.open(band_paths["B11"]) as ref_ds:
        ref_profile = ref_ds.profile.copy()
        ref_shape = (ref_ds.height, ref_ds.width)
        ref_transform = ref_ds.transform
        ref_crs = ref_ds.crs

    band_arrays: dict[str, np.ndarray] = {}
    for band_name, band_path in band_paths.items():
        with rasterio.open(band_path) as src:
            dst_arr = np.empty(ref_shape, dtype=src.dtypes[0])
            reproject(
                source=rasterio.band(src, 1),
                destination=dst_arr,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=ref_transform,
                dst_crs=ref_crs,
                resampling=Resampling.bilinear,
            )
            band_arrays[band_name] = dst_arr

    # Read SCL with nearest resampling (categorical)
    with rasterio.open(scl_path) as scl_ds:
        scl_arr = np.empty(ref_shape, dtype=scl_ds.dtypes[0])
        reproject(
            source=rasterio.band(scl_ds, 1),
            destination=scl_arr,
            src_transform=scl_ds.transform,
            src_crs=scl_ds.crs,
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            resampling=Resampling.nearest,
        )

    return band_arrays, scl_arr, ref_profile


def _write_cog_30m(
    water_class: np.ndarray,
    profile_20m: dict,
    output_path: Path,
    output_epsg: int | None,
    output_posting_m: float,
) -> Path:
    """Reproject water_class from 20m to 30m UTM and write as COG.

    Parameters
    ----------
    water_class:
        uint8 classified water array at 20m.
    profile_20m:
        Rasterio profile from the 20m input grid.
    output_path:
        Destination COG path.
    output_epsg:
        Target UTM EPSG. If None, uses the CRS from profile_20m.
    output_posting_m:
        Output pixel size in metres (default 30).

    Returns
    -------
    Path
        The written COG path.
    """
    import rasterio
    from rasterio.crs import CRS
    from rasterio.enums import Resampling
    from rasterio.transform import from_bounds
    from rasterio.warp import calculate_default_transform, reproject

    src_crs = profile_20m.get("crs") or CRS.from_epsg(4326)
    dst_crs = CRS.from_epsg(output_epsg) if output_epsg else src_crs

    src_transform = profile_20m["transform"]
    src_height, src_width = water_class.shape

    # Calculate bounds from source
    left = src_transform.c
    top = src_transform.f
    right = left + src_width * src_transform.a
    bottom = top + src_height * src_transform.e

    dst_transform, dst_width, dst_height = calculate_default_transform(
        src_crs, dst_crs, src_width, src_height,
        left=left, bottom=bottom, right=right, top=top,
        resolution=output_posting_m,
    )

    dst_data = np.full((dst_height, dst_width), 255, dtype=np.uint8)
    reproject(
        source=water_class,
        destination=dst_data,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        resampling=Resampling.nearest,
    )

    # Write to temporary GeoTIFF, then COG-translate
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(".tmp.tif")

    with rasterio.open(
        tmp_path,
        "w",
        driver="GTiff",
        height=dst_height,
        width=dst_width,
        count=1,
        dtype="uint8",
        crs=dst_crs,
        transform=dst_transform,
        nodata=255,
    ) as dst:
        dst.write(dst_data, 1)

    # COG conversion
    from rio_cogeo.cogeo import cog_translate
    from rio_cogeo.profiles import cog_profiles

    cog_profile = cog_profiles.get("deflate")
    cog_translate(
        str(tmp_path),
        str(output_path),
        cog_profile,
        overview_level=5,
        overview_resampling="nearest",
        use_cog_driver=True,
        nodata=255,
    )
    tmp_path.unlink(missing_ok=True)

    logger.debug("Wrote DSWx COG at {}m: {}", output_posting_m, output_path)
    return output_path


# ---------------------------------------------------------------------------
# Internal: product validation
# ---------------------------------------------------------------------------


def _validate_dswx_product(cog_path: Path) -> list[str]:
    """Validate DSWx COG for UTM CRS, ~30m posting, and COG structure.

    Returns list of error strings (empty = valid).
    """
    import rasterio
    from rio_cogeo.cog_validate import cog_validate

    errors: list[str] = []

    if not cog_path.exists():
        return [f"{cog_path}: file does not exist"]

    is_valid, _, _ = cog_validate(str(cog_path))
    if not is_valid:
        errors.append(f"{cog_path}: not a valid COG")

    with rasterio.open(cog_path) as ds:
        epsg = ds.crs.to_epsg() if ds.crs else None
        if epsg is None or not (32601 <= epsg <= 32660 or 32701 <= epsg <= 32760):
            errors.append(f"{cog_path}: CRS is not UTM (EPSG={epsg})")
        pixel_x = abs(ds.transform.a)
        pixel_y = abs(ds.transform.e)
        avg_pixel = (pixel_x + pixel_y) / 2
        if not (25 <= avg_pixel <= 35):
            errors.append(
                f"{cog_path}: pixel size {avg_pixel:.1f} m outside 25-35 m range"
            )

    return errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_dswx(cfg: DSWxConfig) -> DSWxResult:
    """Execute the DSWx-S2 surface water classification pipeline.

    Steps:
    1. Read S2 L2A bands at 20m (aligned to B11 grid)
    2. Compute DSWE 5-bit diagnostic layer
    3. Classify water using PROTEUS lookup table
    4. Apply SCL cloud/shadow mask
    5. Write 30m UTM COG
    6. Inject OPERA metadata
    7. Validate product

    Parameters
    ----------
    cfg:
        :class:`DSWxConfig` with band paths, SCL path, and output settings.

    Returns
    -------
    DSWxResult
        Processing result with output path and validation status.
    """
    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Read bands at 20m
        logger.info("Reading S2 L2A bands at 20m resolution...")
        bands, scl, profile = _read_s2_bands_at_20m(cfg.s2_band_paths, cfg.scl_path)

        # 2. Compute diagnostic tests
        logger.info("Computing DSWE diagnostic tests...")
        diagnostic = _compute_diagnostic_tests(
            blue=bands["B02"],
            green=bands["B03"],
            red=bands["B04"],
            nir=bands["B08"],
            swir1=bands["B11"],
            swir2=bands["B12"],
        )

        # 3. Classify water
        water_class = _classify_water(diagnostic)

        # 4. Apply SCL cloud mask
        logger.info("Applying SCL cloud mask...")
        water_class = _apply_scl_mask(water_class, scl)

        # 5. Write COG at 30m
        output_path = cfg.output_dir / "dswx_s2.tif"
        logger.info("Writing 30m UTM COG to {}", output_path)
        _write_cog_30m(
            water_class, profile, output_path,
            cfg.output_epsg, cfg.output_posting_m,
        )

        # 6. Inject OPERA metadata
        from subsideo._metadata import inject_opera_metadata

        inject_opera_metadata(
            output_path,
            product_type="DSWx-S2",
            software_version=cfg.product_version,
            run_params={
                "s2_bands": [str(p) for p in cfg.s2_band_paths.values()],
                "scl_path": str(cfg.scl_path),
                "output_posting_m": cfg.output_posting_m,
            },
        )

        # 7. Validate
        errors = _validate_dswx_product(output_path)

        result = DSWxResult(
            output_path=output_path,
            valid=len(errors) == 0,
            validation_errors=errors,
        )

        if result.valid:
            logger.info("DSWx pipeline completed successfully: {}", output_path)
        else:
            logger.warning("DSWx pipeline completed with errors: {}", errors)

        return result

    except ImportError as exc:
        dep = str(exc).split("'")[1] if "'" in str(exc) else str(exc)
        logger.error("{} not installed -- install via conda-forge", dep)
        return DSWxResult(
            output_path=None,
            valid=False,
            validation_errors=[f"{dep} not installed (conda-forge required)"],
        )
    except Exception as exc:
        logger.error("DSWx pipeline failed: {}", exc)
        return DSWxResult(
            output_path=None,
            valid=False,
            validation_errors=[f"DSWx pipeline error: {exc}"],
        )


def run_dswx_from_aoi(
    aoi: dict | Path,
    date_range: tuple[str, str],
    output_dir: Path,
) -> DSWxResult:
    """End-to-end DSWx-S2 pipeline from AOI and date range.

    Queries CDSE for Sentinel-2 L2A scenes, downloads required bands
    (B02, B03, B04, B08, B11, B12) and SCL, determines UTM EPSG from
    AOI centroid, and runs :func:`run_dswx`.

    Parameters
    ----------
    aoi:
        GeoJSON dict or Path to GeoJSON file (Polygon/MultiPolygon).
    date_range:
        ``(start_date, end_date)`` in ``YYYY-MM-DD`` format.
    output_dir:
        Root output directory.

    Returns
    -------
    DSWxResult
        Processing result.
    """
    from datetime import datetime

    from shapely.geometry import shape

    from subsideo.data.cdse import CDSEClient
    from subsideo.utils.projections import utm_epsg_from_lon

    # Resolve AOI
    if isinstance(aoi, Path):
        with open(aoi) as f:
            aoi = json.load(f)

    if "type" not in aoi or "coordinates" not in aoi:
        return DSWxResult(
            output_path=None,
            valid=False,
            validation_errors=["Invalid AOI: must contain 'type' and 'coordinates' keys"],
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        aoi_geom = shape(aoi)
        centroid = aoi_geom.centroid
        output_epsg = utm_epsg_from_lon(centroid.x, centroid.y)

        coords = aoi["coordinates"][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        bbox = [min(lons), min(lats), max(lons), max(lats)]

        start_str, end_str = date_range
        start_dt = datetime.fromisoformat(start_str)
        end_dt = datetime.fromisoformat(end_str)

        client = CDSEClient()
        scenes = client.search_stac(
            collection="SENTINEL-2",
            bbox=bbox,
            start=start_dt,
            end=end_dt,
            product_type="S2MSI2A",
        )
        logger.info("Found {} S2 L2A scenes for AOI", len(scenes))

        if not scenes:
            return DSWxResult(
                output_path=None,
                valid=False,
                validation_errors=["No S2 L2A scenes found for AOI and date range"],
            )

        # Use the first scene (lowest cloud cover)
        scene = scenes[0]
        assets = scene.get("assets", {})

        # Download band files
        download_dir = output_dir / "s2_bands"
        download_dir.mkdir(parents=True, exist_ok=True)

        band_names = ["B02", "B03", "B04", "B08", "B11", "B12"]
        band_paths: dict[str, Path] = {}
        for band in band_names:
            href = assets.get(band, {}).get("href", "")
            dst = download_dir / f"{band}.tif"
            client.download(href, dst)
            band_paths[band] = dst

        scl_href = assets.get("SCL", {}).get("href", "")
        scl_path = download_dir / "SCL.tif"
        client.download(scl_href, scl_path)

        cfg = DSWxConfig(
            s2_band_paths=band_paths,
            scl_path=scl_path,
            output_dir=output_dir,
            output_epsg=output_epsg,
        )

        return run_dswx(cfg)

    except Exception as exc:
        logger.error("DSWx AOI pipeline failed: {}", exc)
        return DSWxResult(
            output_path=None,
            valid=False,
            validation_errors=[f"DSWx AOI pipeline error: {exc}"],
        )
