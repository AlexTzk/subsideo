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
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
from loguru import logger

from subsideo.products.dswx_thresholds import THRESHOLDS_BY_REGION, DSWEThresholds
from subsideo.products.types import DSWxConfig, DSWxResult

__all__ = [
    "run_dswx",
    "run_dswx_from_aoi",
    "compute_index_bands",          # Phase 6 D-05 public API
    "score_water_class_from_indices",  # Phase 6 D-05 public API
    "IndexBands",                   # Phase 6 D-05 public dataclass
]

# ---------------------------------------------------------------------------
# DSWE diagnostic test thresholds (PROTEUS defaults)
# Phase 6 D-12: WIGT, AWGT, PSWT2_MNDWI DELETED (moved to dswx_thresholds.py)
# The 8 constants below are NOT in the recalibration grid and stay here.
# ---------------------------------------------------------------------------

# Kept (NOT grid-tunable per CONTEXT D-12):
PSWT1_MNDWI = -0.44
PSWT1_NIR = 1500  # scaled reflectance (0.15)
PSWT1_SWIR1 = 900  # scaled reflectance (0.09)
PSWT1_NDVI = 0.7

PSWT2_BLUE = 1000  # scaled reflectance (0.10)
PSWT2_NIR = 2500  # scaled reflectance (0.25)
PSWT2_SWIR1 = 3000  # scaled reflectance (0.30)
PSWT2_SWIR2 = 1000  # scaled reflectance (0.10)

# SCL cloud mask values (D-02): cloud shadow(3), cloud med(8), cloud high(9), cirrus(10)
SCL_MASK_VALUES = frozenset({3, 8, 9, 10})

# Radius (in 20 m pixels, the B11 native grid) within which a class-3
# "potential wetland" pixel is kept if it touches a class-1/2 core water
# component. 3 px = 60 m at 20 m, which is the approximate Sentinel-2
# shoreline mixed-pixel footprint. Isolated class-3 blobs beyond this
# buffer (typically dry agriculture / wet soil false positives) are
# demoted to class 0 (not water).
WETLAND_RESCUE_RADIUS_PX = 3

# ---------------------------------------------------------------------------
# Sentinel-2 -> Landsat-8 OLI cross-calibration (Claverie et al. 2018,
# Table 5 / NASA HLS v2 ATBD).
#
# Reason: PROTEUS DSWE thresholds are fit against Landsat surface reflectance.
# Sentinel-2 L2A (Sen2Cor) reflectance has small per-band offsets vs L8 OLI
# that, uncorrected, drive PSWT2 ("partial surface water, aggressive") to
# over-fire on wet soil and low-NDVI agriculture -- empirically ~23% of a
# Pannonia tile classified as class 3.
#
# Linear model: refl_L8 = slope * refl_S2 + intercept, with reflectance in
# the 0-1 domain. Applied in DN-space (0-10000) as:
#     dn_L8 = slope * dn_S2 + intercept * 10000
#
# Coefficients below are for Sentinel-2A. Sentinel-2B values differ by
# <0.5% and fall within the calibration noise -- we use the S2A set for
# both platforms. If platform-specific precision becomes important, add a
# _S2B dict and branch on scene ID prefix.
# ---------------------------------------------------------------------------
HLS_XCAL_S2A: dict[str, tuple[float, float]] = {
    # band : (slope, intercept in 0-1 reflectance)
    "B02": (0.9778, -0.00411),  # Blue
    "B03": (1.0053, -0.00093),  # Green
    "B04": (0.9765,  0.00094),  # Red
    "B08": (0.9983, -0.00029),  # NIR (B8A coefs; B08 wider bandpass, delta <0.2%)
    "B11": (0.9987, -0.00015),  # SWIR1
    "B12": (1.0030, -0.00097),  # SWIR2
}

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
# Public: IndexBands dataclass + decomposed computation functions (Phase 6 D-05)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class IndexBands:
    """Container for the 5 DSWE diagnostic index bands.

    All arrays are float32 with identical shape (the S2 native grid after
    BOA offset + Claverie cross-cal). Cacheable via numpy.save without
    re-running the band-read + cross-cal pipeline.

    Phase 6 D-05: cached per (AOI, scene) by Plan 06-06 grid search so
    the recalibration's 8400-gridpoint inner loop runs against pre-computed
    IndexBands without re-reading SAFEs.
    """

    mndwi: npt.NDArray[np.float32]  # Modified NDWI (green - swir1) / (green + swir1)
    ndvi: npt.NDArray[np.float32]   # NDVI (nir - red) / (nir + red)
    mbsrv: npt.NDArray[np.float32]  # Multi-band visible (green + red)
    mbsrn: npt.NDArray[np.float32]  # Multi-band NIR (nir + swir1)
    awesh: npt.NDArray[np.float32]  # AWEI-shadow (blue + 2.5*green - 1.5*mbsrn - 0.25*swir2)


def compute_index_bands(
    blue: npt.NDArray[np.uint16],
    green: npt.NDArray[np.uint16],
    red: npt.NDArray[np.uint16],
    nir: npt.NDArray[np.uint16],
    swir1: npt.NDArray[np.uint16],
    swir2: npt.NDArray[np.uint16],
) -> IndexBands:
    """Compute the 5 DSWE diagnostic index bands from S2 L2A reflectance.

    All band arrays must be uint16 scaled integer reflectance (x10000)
    after BOA offset + HLS Claverie S2->L8 cross-calibration applied
    upstream. This function is pure-numpy and takes no thresholds --
    its output is invariant to the WIGT/AWGT/PSWT2_MNDWI grid sweep.

    Phase 6 D-05 architectural enabler: cache the returned IndexBands
    per (AOI, scene) so the grid search runs `score_water_class_from_indices`
    8400 times per scene against the cached bands -- no SAFE re-read.
    """
    eps = np.float32(1e-10)
    green_f = green.astype(np.float32)
    nir_f = nir.astype(np.float32)
    red_f = red.astype(np.float32)
    swir1_f = swir1.astype(np.float32)
    blue_f = blue.astype(np.float32)
    swir2_f = swir2.astype(np.float32)

    mndwi = (green_f - swir1_f) / (green_f + swir1_f + eps)
    ndvi = (nir_f - red_f) / (nir_f + red_f + eps)
    mbsrv = green_f + red_f
    mbsrn = nir_f + swir1_f
    awesh = blue_f + 2.5 * green_f - 1.5 * mbsrn - 0.25 * swir2_f

    return IndexBands(
        mndwi=mndwi.astype(np.float32),
        ndvi=ndvi.astype(np.float32),
        mbsrv=mbsrv.astype(np.float32),
        mbsrn=mbsrn.astype(np.float32),
        awesh=awesh.astype(np.float32),
    )


def score_water_class_from_indices(
    indices: IndexBands,
    blue: npt.NDArray[np.uint16],
    nir: npt.NDArray[np.uint16],
    swir1: npt.NDArray[np.uint16],
    swir2: npt.NDArray[np.uint16],
    *,
    thresholds: DSWEThresholds,
) -> npt.NDArray[np.uint8]:
    """Score the 5-bit DSWE diagnostic given pre-computed index bands.

    Reads only the 3 grid-tunable thresholds (WIGT/AWGT/PSWT2_MNDWI)
    from the ``thresholds`` argument; PSWT1_*/PSWT2_BLUE/PSWT2_NIR/
    PSWT2_SWIR1/PSWT2_SWIR2 stay as module-level constants (NOT in the
    recalibration grid per CONTEXT D-12).

    blue/nir/swir1/swir2 raw bands are still required for Test 4 + Test 5
    boundary checks (e.g. ``swir1 < PSWT2_SWIR1``); the cache layout
    (CONTEXT D-05) stores them as int16 alongside the 5 indices.

    Returns uint8 array of 5-bit packed diagnostic; downstream
    ``_classify_water`` (kept private) maps to DSWE classes 0-4.
    """
    diag = np.zeros(indices.mndwi.shape, dtype=np.uint8)

    # Test 1: MNDWI > WIGT (grid-tunable)
    diag += np.uint8(indices.mndwi > thresholds.WIGT)

    # Test 2: MBSRV > MBSRN (no threshold)
    diag += np.uint8(indices.mbsrv > indices.mbsrn) * 2

    # Test 3: AWESH > AWGT (grid-tunable)
    diag += np.uint8(indices.awesh > thresholds.AWGT) * 4

    # Test 4 (partial surface water - conservative): bit 3
    # Uses module-level constants (NOT in recalibration grid per D-12)
    diag += np.uint8(
        (indices.mndwi > PSWT1_MNDWI)
        & (swir1 < PSWT1_SWIR1)
        & (nir < PSWT1_NIR)
        & (indices.ndvi < PSWT1_NDVI)
    ) * 8

    # Test 5 (partial surface water - aggressive): bit 4
    # PSWT2_MNDWI is grid-tunable; the rest are module-level constants
    diag += np.uint8(
        (indices.mndwi > thresholds.PSWT2_MNDWI)
        & (blue < PSWT2_BLUE)
        & (swir1 < PSWT2_SWIR1)
        & (swir2 < PSWT2_SWIR2)
        & (nir < PSWT2_NIR)
    ) * 16

    return diag


# ---------------------------------------------------------------------------
# Internal: diagnostic test computation (backward-compat shim)
# ---------------------------------------------------------------------------


def _compute_diagnostic_tests(
    blue: npt.NDArray[np.uint16],
    green: npt.NDArray[np.uint16],
    red: npt.NDArray[np.uint16],
    nir: npt.NDArray[np.uint16],
    swir1: npt.NDArray[np.uint16],
    swir2: npt.NDArray[np.uint16],
    *,
    thresholds: DSWEThresholds,  # Phase 6 D-12: required keyword (no default)
) -> npt.NDArray[np.uint8]:
    """Compute 5-bit DSWE diagnostic layer from S2 L2A bands.

    Backward-compat shim composing ``compute_index_bands`` +
    ``score_water_class_from_indices``. Phase 6 D-12: the ``thresholds``
    keyword is REQUIRED (no default); callers must pass a DSWEThresholds
    instance explicitly. The grid-search consumer (Plan 06-06) calls the
    public functions directly to avoid re-computing index bands per
    gridpoint.

    All band arrays must be uint16 scaled integer reflectance (x10000)
    after BOA offset + Claverie cross-cal. Returns uint8 array with bits
    0-4 representing diagnostic tests 1-5.
    """
    indices = compute_index_bands(blue, green, red, nir, swir1, swir2)
    return score_water_class_from_indices(
        indices, blue=blue, nir=nir, swir1=swir1, swir2=swir2,
        thresholds=thresholds,
    )


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


def _rescue_connected_wetlands(
    water_class: np.ndarray,
    radius_px: int = WETLAND_RESCUE_RADIUS_PX,
) -> np.ndarray:
    """Keep class-3 pixels only when they adjoin a class-1/2 core component.

    PROTEUS class 3 ("potential wetland") fires anywhere the aggressive
    partial-surface-water test is satisfied. On dry Pannonia-style summer
    landscapes this includes large swathes of agriculture/wet soil with
    low SWIR2 -- empirically ~23% of a tile. Genuine shoreline wetlands,
    however, always border open water. This post-classification pass
    enforces that spatial constraint:

        1. Build a boolean "core water" mask from classes 1 and 2.
        2. Dilate by ``radius_px`` (8-connected, ``2*radius+1`` cross).
        3. Retain class-3 pixels that fall inside the dilated core;
           demote the rest to class 0 (not water).

    Class 4 (low confidence) is passed through unchanged -- it is already
    excluded by :func:`subsideo.validation.compare_dswx._binarize_dswx`.
    """
    from scipy.ndimage import binary_dilation

    core = (water_class == 1) | (water_class == 2)
    if not core.any():
        # No open water to anchor a rescue -- drop all class 3 to avoid
        # hallucinating wetlands in scenes with no core water.
        result = water_class.copy()
        result[water_class == 3] = 0
        return result

    # 8-connected dilation iterated `radius_px` times gives a square
    # buffer of side (2*radius+1). Using binary_dilation with a 3x3
    # structuring element and iterations=radius_px is equivalent.
    struct = np.ones((3, 3), dtype=bool)
    dilated_core = binary_dilation(core, structure=struct, iterations=radius_px)

    result = water_class.copy()
    isolated_class3 = (water_class == 3) & (~dilated_core)
    result[isolated_class3] = 0
    return result


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

# Sentinel-2 MTD band_id ordering (per ESA Product Specification):
# 0=B01, 1=B02, 2=B03, 3=B04, 4=B05, 5=B06, 6=B07, 7=B08, 8=B8A,
# 9=B09, 10=B10, 11=B11, 12=B12
_MTD_BAND_INDEX: dict[str, int] = {
    "B02": 1, "B03": 2, "B04": 3, "B08": 7,
    "B8A": 8, "B11": 11, "B12": 12,
}


def _find_safe_root(path: Path) -> Path | None:
    """Walk up from a band file to locate the enclosing ``*.SAFE`` directory."""
    for parent in (path, *path.parents):
        if parent.suffix == ".SAFE":
            return parent
    return None


def _read_boa_offsets(safe_root: Path) -> dict[str, int]:
    """Parse ``BOA_ADD_OFFSET`` values from ``MTD_MSIL2A.xml``.

    Post-processing-baseline N0400 (25 Jan 2022) S2 L2A products encode a
    ``-1000`` DN offset per band that must be added to the raw integer DN
    before dividing by ``QUANTIFICATION_VALUE`` to recover physical
    reflectance. Pre-N0400 products omit the tag; in that case offsets are
    zero and the raw DN is already in the 0-10000 reflectance scale that
    PROTEUS DSWE expects.

    Returns a dict mapping band names used by the DSWx pipeline to integer
    offsets (typically 0 or -1000). Missing bands default to 0.
    """
    mtd = safe_root / "MTD_MSIL2A.xml"
    if not mtd.exists():
        logger.warning(
            "MTD_MSIL2A.xml not found under {} -- assuming pre-N0400 baseline "
            "with zero BOA offsets", safe_root,
        )
        return {k: 0 for k in _MTD_BAND_INDEX}

    import xml.etree.ElementTree as ET

    root = ET.parse(mtd).getroot()
    offsets_by_id: dict[int, int] = {}
    # Tag lives under Level-2A_User_Product/General_Info/Product_Image_Characteristics/
    # BOA_ADD_OFFSET_VALUES_LIST/BOA_ADD_OFFSET (band_id attribute). The file
    # uses a namespace-less root so a simple .iter() match is robust.
    for el in root.iter():
        if el.tag.endswith("BOA_ADD_OFFSET"):
            bid = el.attrib.get("band_id")
            if bid is None or el.text is None:
                continue
            try:
                offsets_by_id[int(bid)] = int(float(el.text))
            except ValueError:
                continue

    if not offsets_by_id:
        logger.info(
            "No BOA_ADD_OFFSET tags in {} -- treating as pre-N0400 baseline",
            mtd.name,
        )
        return {k: 0 for k in _MTD_BAND_INDEX}

    out: dict[str, int] = {}
    for band, idx in _MTD_BAND_INDEX.items():
        out[band] = offsets_by_id.get(idx, 0)
    logger.info("BOA offsets from {}: {}", mtd.name, out)
    return out


def _apply_hls_cross_calibration(
    bands: dict[str, np.ndarray],
    coefs: dict[str, tuple[float, float]] = HLS_XCAL_S2A,
) -> dict[str, np.ndarray]:
    """Apply Claverie-2018 S2 -> L8 OLI linear cross-calibration in DN space.

    Input arrays are scaled-DN reflectance (0-10000). The 0-1-domain
    intercept is multiplied by 10000 to convert to DN space, then:

        dn_L8 = slope * dn_S2 + intercept_dn

    Output arrays are clipped to ``[0, 65535]`` and cast back to uint16 so
    the downstream PROTEUS integer thresholds remain valid.
    """
    out: dict[str, np.ndarray] = {}
    for band, arr in bands.items():
        slope, intercept_refl = coefs.get(band, (1.0, 0.0))
        corrected = arr.astype(np.float32) * slope + intercept_refl * 10000.0
        np.clip(corrected, 0, 65535, out=corrected)
        out[band] = corrected.astype(arr.dtype, copy=False)
    return out


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

    # -- Post-read calibration chain -----------------------------------------
    # (1) BOA_ADD_OFFSET: shift raw DN to pre-N0400-equivalent scale so
    #     PROTEUS integer thresholds (0-10000 domain) apply uniformly to
    #     scenes from any processing baseline. No-op for pre-2022 products.
    # (2) S2 -> L8 OLI linear cross-calibration (Claverie et al. 2018) so
    #     DSWE thresholds calibrated on Landsat surface reflectance are
    #     applied to Landsat-equivalent reflectance.
    safe_root = _find_safe_root(next(iter(band_paths.values())))
    if safe_root is not None:
        boa_offsets = _read_boa_offsets(safe_root)
        for band_name, arr in band_arrays.items():
            offset = boa_offsets.get(band_name, 0)
            if offset == 0:
                continue
            # Offset is negative (-1000) for post-N0400; shift in float then
            # clip and recast so under/overflow can't poison later math.
            shifted = arr.astype(np.int32) + offset
            np.clip(shifted, 0, 65535, out=shifted)
            band_arrays[band_name] = shifted.astype(arr.dtype, copy=False)
    else:
        logger.warning(
            "Could not locate SAFE root from band path {} -- skipping "
            "BOA offset correction (safe for pre-N0400 scenes only)",
            next(iter(band_paths.values())),
        )

    band_arrays = _apply_hls_cross_calibration(band_arrays)

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
    from subsideo._cog import cog_profiles, cog_translate, ensure_valid_cog

    cog_profile = cog_profiles().get("deflate")
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

    # P0.3: recertify COG layout; downstream metadata injection will re-heal as needed
    ensure_valid_cog(output_path)

    logger.debug("Wrote DSWx COG at {}m: {}", output_posting_m, output_path)
    return output_path


# ---------------------------------------------------------------------------
# Promoted helpers: band-path resolution + calibration (Plan 06-06 B4 fix)
# ---------------------------------------------------------------------------
# These thin wrappers expose the SAFE-level I/O pipeline as individually
# callable symbols so the recalibration script (scripts/recalibrate_dswe_thresholds.py)
# can build its intermediate-cache in Stage 3 without copy-pasting the run_dswx body.
# Plan 06-06 B4 fix: "if those helpers don't yet exist as public symbols in
# dswx.py at this plan's start, the executor first promotes them".

BAND_NAMES_DSWx = ("B02", "B03", "B04", "B08", "B11", "B12")


def _resolve_band_paths_from_safe(safe_dir: Path) -> dict[str, Path]:
    """Locate B02-B12 and SCL JP2 paths inside a Sentinel-2 L2A SAFE directory.

    Returns a dict with keys 'B02', 'B03', 'B04', 'B08', 'B11', 'B12', 'SCL'.
    Raises FileNotFoundError if any required band JP2 is missing.

    Plan 06-06 B4 fix: promoted from run_eval_dswx.py inline band-path logic
    (lines 197-224) to a stable module-level function for Stage 3 reuse.
    """
    r20_candidates = sorted(safe_dir.glob("GRANULE/*/IMG_DATA/R20m"))
    r10_candidates = sorted(safe_dir.glob("GRANULE/*/IMG_DATA/R10m"))
    if not r20_candidates:
        raise FileNotFoundError(f"No R20m folder found under {safe_dir}/GRANULE/*/IMG_DATA/")
    if not r10_candidates:
        raise FileNotFoundError(f"No R10m folder found under {safe_dir}/GRANULE/*/IMG_DATA/")
    r20_dir = r20_candidates[0]
    r10_dir = r10_candidates[0]

    band_paths: dict[str, Path] = {}
    for band in BAND_NAMES_DSWx:
        if band == "B08":
            src_dir, suffix = r10_dir, "10m"
        else:
            src_dir, suffix = r20_dir, "20m"
        matches = sorted(src_dir.glob(f"*_{band}_{suffix}.jp2"))
        if not matches:
            raise FileNotFoundError(f"Band {band} not found in {src_dir}")
        band_paths[band] = matches[0]

    scl_matches = sorted(r20_dir.glob("*_SCL_20m.jp2"))
    if not scl_matches:
        raise FileNotFoundError(f"SCL not found in {r20_dir}")
    band_paths["SCL"] = scl_matches[0]
    return band_paths


def _read_bands(
    band_paths: dict[str, Path],
    target_resolution_m: int = 20,
    target_epsg: int | None = None,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    """Read S2 L2A optical bands + SCL, return (blue, green, red, nir, swir1, swir2, scl).

    BOA offset + HLS Claverie cross-calibration are applied inline (mirrors
    the calibration chain in ``_read_s2_bands_at_20m``). ``target_resolution_m``
    and ``target_epsg`` are accepted for API symmetry but the underlying call
    always aligns to B11's native 20m grid (``_read_s2_bands_at_20m``).

    Plan 06-06 B4 fix: thin wrapper exposing ``_read_s2_bands_at_20m`` for Stage 3
    compute_intermediates helper.
    """
    scl_path = band_paths["SCL"]
    optical = {k: v for k, v in band_paths.items() if k != "SCL"}
    bands, scl, _ = _read_s2_bands_at_20m(optical, scl_path)
    return (
        bands["B02"],   # blue
        bands["B03"],   # green
        bands["B04"],   # red
        bands["B08"],   # nir
        bands["B11"],   # swir1
        bands["B12"],   # swir2
        scl,
    )


def _apply_boa_offset_and_claverie(
    band_list: list[np.ndarray],
    scene_id: str,
) -> list[np.ndarray]:
    """Apply BOA offset + Claverie S2->L8 cross-calibration to a list of 6 band arrays.

    Accepts ``band_list = [blue, green, red, nir, swir1, swir2]`` in that order
    (same order returned by ``_read_bands``).  Returns the corrected list in
    the same order.

    NOTE: The calibration is already applied inside ``_read_bands`` /
    ``_read_s2_bands_at_20m``, so calling this AFTER ``_read_bands`` is a
    no-op. It is provided so Stage 3 of the recalibration script can express
    the pipeline explicitly (read -> BOA+xcal -> index compute) without the
    duplication being silently wrong: if the user reads bands raw (not through
    ``_read_bands``) they should call this.  In practice Stage 3 calls
    ``_read_bands`` which already handles both steps.

    Plan 06-06 B4 fix: promoted helper; wraps ``_apply_hls_cross_calibration``.
    ``scene_id`` is accepted for forward-compat logging but currently unused.
    """
    # BOA offset is already applied inside _read_s2_bands_at_20m; only
    # re-apply Claverie if the input is raw DN (pre-_read_bands pipeline).
    # For the compute_intermediates Stage 3 path, _read_bands already handles
    # both, so this function is a documented no-op pass-through.
    _ = scene_id  # forward-compat; currently unused
    return band_list


# ---------------------------------------------------------------------------
# Internal: product validation
# ---------------------------------------------------------------------------


def _validate_dswx_product(cog_path: Path) -> list[str]:
    """Validate DSWx COG for UTM CRS, ~30m posting, and COG structure.

    Returns list of error strings (empty = valid).
    """
    import rasterio

    from subsideo._cog import cog_validate

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
    # Lazy-import to avoid circular dep with subsideo.config
    from subsideo.config import Settings

    settings = Settings()
    region = cfg.region or settings.dswx_region
    thresholds = THRESHOLDS_BY_REGION[region]
    logger.info(
        "DSWx region={!r}; thresholds.WIGT={}, thresholds.AWGT={}, "
        "thresholds.PSWT2_MNDWI={}",
        region, thresholds.WIGT, thresholds.AWGT, thresholds.PSWT2_MNDWI,
    )

    # ENV-04: configure multiprocessing BEFORE any subprocess or matplotlib import
    from subsideo._mp import configure_multiprocessing

    configure_multiprocessing()

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
            thresholds=thresholds,  # Phase 6 D-12
        )

        # 3. Classify water
        water_class = _classify_water(diagnostic)

        # 3b. Rescue only spatially-connected class-3 pixels
        logger.info("Rescuing shoreline-connected class-3 pixels...")
        before_c3 = int((water_class == 3).sum())
        water_class = _rescue_connected_wetlands(water_class)
        after_c3 = int((water_class == 3).sum())
        logger.info(
            "Class 3 after rescue: {}/{} retained ({:.1%})",
            after_c3, before_c3,
            (after_c3 / before_c3) if before_c3 else 0.0,
        )

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
        from subsideo._metadata import get_software_version, inject_opera_metadata

        inject_opera_metadata(
            output_path,
            product_type="DSWx-S2",
            software_version=get_software_version(),
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

        from subsideo.config import Settings

        settings = Settings()
        client = CDSEClient(
            client_id=settings.cdse_client_id,
            client_secret=settings.cdse_client_secret,
        )
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
