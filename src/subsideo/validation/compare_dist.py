"""DIST-S1 product validation against OPERA DIST-S1 reference.

Performs a categorical raster comparison of a subsideo DIST-S1 surface-
disturbance product against an OPERA DIST-S1 GEN-DIST-STATUS reference
COG downloaded from ASF DAAC. The product is reprojected with nearest-
neighbour resampling onto the reference grid (the reference is the
authoritative target grid, mirroring the DISP validation convention),
both arrays are binarised to "disturbed / not disturbed" using the
OPERA class table documented below, and standard binary classification
metrics (F1, precision, recall, overall accuracy) are computed on the
intersection of valid pixels.

Binarisation policy
-------------------
The OPERA DIST-S1 GEN-DIST-STATUS layer ships a uint8 multi-class raster
per the OPERA DIST-S1 Product Specification. Label ``1`` represents a
first-detection provisional alert and is noisy; OPERA's own downstream
analysis filters it out. This module follows the same convention:
labels ``>= 2`` count as "disturbed", label ``0`` counts as "not
disturbed", and label ``255`` is nodata.

If a probe of a real OPERA DIST-S1 granule shows a different label
schema, update :data:`DIST_DISTURBED_LABELS` and re-run.

Pass criteria
-------------
Default: ``F1 > 0.80`` and ``overall_accuracy > 0.85``. These are
intentionally looser than the DSWx ``F1 > 0.90`` threshold because
DIST-S1 disturbance is a transient phenomenon -- the OPERA reference
and our output can disagree at the edges of a disturbance polygon
(different anti-aliasing / tile boundary handling) without either being
wrong. A baseline F1 > 0.80 with high accuracy indicates class-label
agreement on the bulk of the disturbed area. Tighten the thresholds
once the first successful eval establishes a realistic floor.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from loguru import logger

from subsideo.products.types import DISTValidationResult
from subsideo.validation.metrics import (
    f1_score,
    overall_accuracy,
    precision_score,
    recall_score,
)

# -----------------------------------------------------------------------------
# OPERA DIST-S1 GEN-DIST-STATUS class labels
# -----------------------------------------------------------------------------
# OPERA DIST-S1 "GEN-DIST-STATUS" layer label values, per the OPERA DIST-S1
# Product Specification (v1.0, Jan 2025). This is the first disturbance
# alert layer -- a uint8 raster the OPERA product ships at 30 m.
#
#   0  = no disturbance
#   1  = first detection (provisional, low confidence)
#   2  = provisional (confirmed)
#   3  = confirmed (first-detection low-confidence)
#   4  = confirmed (provisional low-confidence)
#   5  = confirmed (first-detection high-confidence)
#   6  = confirmed (high-confidence)
#   7  = finished
#   8  = finished (confirmed)
#  255 = nodata / outside disturbance mask
#
# Binarisation policy: "disturbed" = label >= 2 (excludes label 1 which
# is noisy single-detection provisional, matches OPERA's own "confirmed"
# filter). "Not disturbed" = label 0. Label 255 is nodata.
#
# If the planner's probe of a real OPERA DIST-S1 granule shows different
# label semantics, update DIST_DISTURBED_LABELS and re-run.
DIST_DISTURBED_LABELS: frozenset[int] = frozenset({2, 3, 4, 5, 6, 7, 8})
DIST_NODATA_LABELS: frozenset[int] = frozenset({255})


def _binarize_dist(
    raster: np.ndarray,
    disturbed_labels: frozenset[int] = DIST_DISTURBED_LABELS,
    nodata_labels: frozenset[int] = DIST_NODATA_LABELS,
) -> np.ndarray:
    """Binarise a DIST-S1 categorical raster to disturbed/not-disturbed.

    Parameters
    ----------
    raster:
        Input uint8 (or int) raster of GEN-DIST-STATUS labels.
    disturbed_labels:
        Set of integer label values that count as "disturbed".
    nodata_labels:
        Set of integer label values that count as nodata.

    Returns
    -------
    np.ndarray
        Float32 array: ``1.0 = disturbed``, ``0.0 = not disturbed``,
        ``NaN = nodata``.
    """
    result = np.zeros(raster.shape, dtype=np.float32)
    if disturbed_labels:
        disturbed_mask = np.isin(raster, list(disturbed_labels))
        result[disturbed_mask] = 1.0
    if nodata_labels:
        nodata_mask = np.isin(raster, list(nodata_labels))
        result[nodata_mask] = np.nan
    return result


def compare_dist(
    product_path: Path,
    reference_path: Path,
    disturbed_labels: frozenset[int] = DIST_DISTURBED_LABELS,
) -> DISTValidationResult:
    """Compare a subsideo DIST-S1 product against an OPERA DIST-S1 reference.

    The reference is treated as the authoritative target grid: the
    product is reprojected onto the reference's CRS and transform with
    nearest-neighbour resampling (categorical data require NN), then
    both arrays are binarised and compared on the intersection of
    valid (non-NaN) pixels.

    Parameters
    ----------
    product_path:
        Path to the subsideo DIST-S1 COG GeoTIFF output (the
        GEN-DIST-STATUS band).
    reference_path:
        Path to the OPERA DIST-S1 reference COG (same band).
    disturbed_labels:
        Override the default set of "disturbed" label values. Useful if
        the OPERA product-spec class table shifts in a future release.

    Returns
    -------
    DISTValidationResult
        F1, precision, recall, overall accuracy, valid-pixel count, and
        a pass-criteria dict (``f1_gt_0.80``, ``accuracy_gt_0.85``).
    """
    import rasterio
    from rasterio.warp import Resampling, reproject

    # 1. Open the reference raster. It defines the target grid.
    with rasterio.open(reference_path) as ref_ds:
        ref_data = ref_ds.read(1)
        ref_crs = ref_ds.crs
        ref_transform = ref_ds.transform
        ref_height = ref_ds.height
        ref_width = ref_ds.width

    # 2. Open the product raster.
    with rasterio.open(product_path) as prod_ds:
        prod_data = prod_ds.read(1)
        prod_crs = prod_ds.crs
        prod_transform = prod_ds.transform

    # 3. Reproject the product onto the reference grid (nearest for categorical).
    prod_on_ref = np.full((ref_height, ref_width), 255, dtype=prod_data.dtype)
    reproject(
        source=prod_data,
        destination=prod_on_ref,
        src_transform=prod_transform,
        src_crs=prod_crs,
        dst_transform=ref_transform,
        dst_crs=ref_crs,
        resampling=Resampling.nearest,
    )

    # 4. Binarise both arrays.
    prod_bin = _binarize_dist(prod_on_ref, disturbed_labels=disturbed_labels)
    ref_bin = _binarize_dist(ref_data, disturbed_labels=disturbed_labels)

    # 5. Mask to the intersection of valid (non-NaN) pixels.
    valid = np.isfinite(prod_bin) & np.isfinite(ref_bin)
    n_valid = int(valid.sum())

    if n_valid < 100:
        logger.warning(
            "DIST-S1 validation: only {} valid overlapping pixels "
            "(threshold: 100). Metrics will be NaN.",
            n_valid,
        )
        return DISTValidationResult(
            f1=float("nan"),
            precision=float("nan"),
            recall=float("nan"),
            overall_accuracy=float("nan"),
            n_valid_pixels=n_valid,
            pass_criteria={"f1_gt_0.80": False, "accuracy_gt_0.85": False},
        )

    pred = prod_bin[valid].astype(np.int32)
    ref = ref_bin[valid].astype(np.int32)

    # 6. Compute metrics.
    f1 = f1_score(pred, ref)
    prec = precision_score(pred, ref)
    rec = recall_score(pred, ref)
    acc = overall_accuracy(pred, ref)

    logger.info(
        "DIST-S1 validation: F1={:.4f}, precision={:.4f}, "
        "recall={:.4f}, OA={:.4f} (n={:,})",
        f1,
        prec,
        rec,
        acc,
        n_valid,
    )

    pass_criteria = {
        "f1_gt_0.80": bool(f1 > 0.80),
        "accuracy_gt_0.85": bool(acc > 0.85),
    }

    return DISTValidationResult(
        f1=f1,
        precision=prec,
        recall=rec,
        overall_accuracy=acc,
        n_valid_pixels=n_valid,
        pass_criteria=pass_criteria,
    )
