"""CSLC-S1 product validation against OPERA N.Am. reference.

Uses amplitude-based metrics (correlation, RMSE in dB) rather than
interferometric phase coherence. Phase comparison between different
isce3 major versions (e.g. 0.15 vs 0.25) yields random noise because
the SLC interpolation kernel changed upstream of any phase correction.

**Before adding any phase-correction branch to this module**: see
``docs/validation_methodology.md#cross-version-phase`` (Phase 3 Plan
03-05, PITFALLS P2.4 mitigation). Any PR layering carrier/flattening/
tropospheric/ionospheric/solid-Earth-tide corrections on top of an
existing compare_cslc path MUST address in its PR description why the
SLC-interpolation-kernel argument there no longer holds. A rerun
showing coherence 0.0003 -> 0.0015 is NOT progress; both are random
noise.

Historical evidence: see ``CONCLUSIONS_CSLC_N_AM.md`` Section 5.3 for
the v1.0 diagnostic table (carrier/flattening/both removed -> coherence
~ 0.002 everywhere).

For Phase 3 EU: ``compare_cslc_egms_l2a_residual`` participates in the
product-quality vs reference-agreement distinction documented at
``docs/validation_methodology.md`` Section 2; see
``CONCLUSIONS_CSLC_SELFCONSIST_EU.md`` Section 5 for the Iberian
Meseta three-number row that is the motivating example.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from loguru import logger

from subsideo.products.types import CSLCValidationResult
from subsideo.validation.results import ProductQualityResult, ReferenceAgreementResult


def _load_cslc_complex(
    hdf5_path: Path,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None]:
    """Load complex SLC data and coordinates from OPERA CSLC HDF5.

    Returns
    -------
    tuple of (complex_data, x_coordinates, y_coordinates)
    """
    import h5py

    candidate_paths = [
        "/data/VV",
        "/data/HH",
        "/science/SENTINEL1/CSLC/grids/VV",
        "/science/SENTINEL1/CSLC/grids/HH",
    ]
    with h5py.File(hdf5_path, "r") as f:
        data = None
        for dset_path in candidate_paths:
            if dset_path in f:
                data = f[dset_path][:].astype(np.complex128)
                break
        # Fallback: first complex dataset under /data
        if data is None and "data" in f:
            for key in f["data"]:
                dset = f[f"data/{key}"]
                if hasattr(dset, "shape") and np.issubdtype(dset.dtype, np.complexfloating):
                    data = dset[:].astype(np.complex128)
                    break
        if data is None:
            raise ValueError(f"No complex SLC dataset found in {hdf5_path}")

        # Load coordinates if available (try both compass and OPERA layouts)
        x_coords = y_coords = None
        coord_candidates = [
            ("data/x_coordinates", "data/y_coordinates"),
            (
                "science/SENTINEL1/CSLC/grids/x_coordinates",
                "science/SENTINEL1/CSLC/grids/y_coordinates",
            ),
        ]
        for x_path, y_path in coord_candidates:
            if x_path in f and y_path in f:
                x_coords = f[x_path][:]
                y_coords = f[y_path][:]
                break

    return data, x_coords, y_coords


def compare_cslc(product_path: Path, reference_path: Path) -> CSLCValidationResult:
    """Compare CSLC-S1 product against OPERA N.Am. reference.

    Computes both interferometric phase metrics and amplitude-based metrics.
    Phase coherence between different isce3/compass versions is expected to
    be low due to differences in phase screen computation (carrier phase,
    flattening).  Amplitude-based metrics are version-independent and serve
    as the primary validation criteria.

    Args:
        product_path: Path to subsideo CSLC HDF5.
        reference_path: Path to OPERA N.Am. CSLC HDF5 from ASF DAAC.

    Returns:
        CSLCValidationResult with amplitude and phase metrics.
    """
    # 1. Load complex data with coordinates
    prod_complex, prod_x, prod_y = _load_cslc_complex(product_path)
    ref_complex, ref_x, ref_y = _load_cslc_complex(reference_path)

    # 2. Align grids if shapes differ (find overlapping region by coordinates)
    if prod_complex.shape != ref_complex.shape:
        # WR-02: if coordinates are unavailable, fail loudly rather than
        # silently falling through to the mask step (which would either raise
        # an opaque broadcast error or, worse, broadcast incorrectly).
        if not (
            prod_x is not None and ref_x is not None and prod_y is not None and ref_y is not None
        ):
            raise ValueError(
                f"CSLC shape mismatch ({prod_complex.shape} vs "
                f"{ref_complex.shape}) but coordinates unavailable for "
                f"alignment in {product_path} / {reference_path}"
            )
        if prod_x is not None and ref_x is not None and prod_y is not None and ref_y is not None:
            logger.info(
                "Product shape {} != reference shape {}; aligning by coordinates",
                prod_complex.shape,
                ref_complex.shape,
            )
            x_overlap_min = max(prod_x[0], ref_x[0])
            x_overlap_max = min(prod_x[-1], ref_x[-1])
            # y decreases (north→south): overlap north = min of the two
            # northern edges, overlap south = max of the two southern edges
            y_overlap_max = min(prod_y[0], ref_y[0])
            y_overlap_min = max(prod_y[-1], ref_y[-1])

            px0 = int(np.searchsorted(prod_x, x_overlap_min))
            px1 = int(np.searchsorted(prod_x, x_overlap_max, side="right"))
            py0 = int(np.searchsorted(-prod_y, -y_overlap_max))
            py1 = int(np.searchsorted(-prod_y, -y_overlap_min, side="right"))

            rx0 = int(np.searchsorted(ref_x, x_overlap_min))
            rx1 = int(np.searchsorted(ref_x, x_overlap_max, side="right"))
            ry0 = int(np.searchsorted(-ref_y, -y_overlap_max))
            ry1 = int(np.searchsorted(-ref_y, -y_overlap_min, side="right"))

            prod_complex = prod_complex[py0:py1, px0:px1]
            ref_complex = ref_complex[ry0:ry1, rx0:rx1]

            min_rows = min(prod_complex.shape[0], ref_complex.shape[0])
            min_cols = min(prod_complex.shape[1], ref_complex.shape[1])
            prod_complex = prod_complex[:min_rows, :min_cols]
            ref_complex = ref_complex[:min_rows, :min_cols]

            logger.info(
                "Aligned shapes: product={}, reference={}", prod_complex.shape, ref_complex.shape
            )

    # 3. Mask invalid pixels
    mask = (
        ~np.isnan(prod_complex)
        & ~np.isnan(ref_complex)
        & (np.abs(prod_complex) > 0)
        & (np.abs(ref_complex) > 0)
    )
    if not np.any(mask):
        logger.warning("No valid pixels for CSLC comparison")
        return CSLCValidationResult(
            product_quality=ProductQualityResult(
                measurements={"phase_rms_rad": float("nan"), "coherence": float("nan")},
                criterion_ids=[],
            ),
            reference_agreement=ReferenceAgreementResult(
                measurements={
                    "amplitude_r": float("nan"),
                    "amplitude_rmse_db": float("nan"),
                },
                criterion_ids=["cslc.amplitude_r_min", "cslc.amplitude_rmse_db_max"],
            ),
        )

    prod_masked = prod_complex[mask]
    ref_masked = ref_complex[mask]

    # 4. Amplitude-based metrics (version-independent)
    prod_amp = np.abs(prod_masked)
    ref_amp = np.abs(ref_masked)

    amp_corr = float(np.corrcoef(prod_amp, ref_amp)[0, 1])

    # RMSE in dB — use minimum amplitude threshold to avoid noise-dominated
    # pixels where tiny differences produce huge dB spreads
    amp_thresh = 5.0
    strong_mask = (prod_amp > amp_thresh) & (ref_amp > amp_thresh)
    if np.sum(strong_mask) > 100:
        prod_db = 20 * np.log10(prod_amp[strong_mask])
        ref_db = 20 * np.log10(ref_amp[strong_mask])
    else:
        prod_db = 20 * np.log10(prod_amp)
        ref_db = 20 * np.log10(ref_amp)
    amp_rmse_db = float(np.sqrt(np.mean((prod_db - ref_db) ** 2)))

    # 5. Phase metrics (informational — low coherence expected across isce3 versions)
    ifg = prod_masked * np.conj(ref_masked)
    phase_diff = np.angle(ifg)
    phase_rms = float(np.sqrt(np.mean(phase_diff**2)))

    # WR-05: pre-mask against |ifg|==0 before normalising. The outer ``mask``
    # in step 3 requires ``|prod|>0`` and ``|ref|>0``, but neither guarantees
    # ``|prod * conj(ref)|>0``; division by zero pixels would produce NaN and
    # silently fail the coherence gate downstream.
    ifg_nonzero = np.abs(ifg) > 1e-12
    if np.any(ifg_nonzero):
        ifg_norm = ifg[ifg_nonzero] / np.abs(ifg[ifg_nonzero])
        coherence = float(np.abs(np.mean(ifg_norm)))
    else:
        coherence = 0.0

    logger.info(
        "CSLC validation: amp_corr={:.4f}, amp_RMSE={:.2f} dB, "
        "phase_RMS={:.4f} rad, coherence={:.4f}",
        amp_corr,
        amp_rmse_db,
        phase_rms,
        coherence,
    )

    return CSLCValidationResult(
        product_quality=ProductQualityResult(
            measurements={"phase_rms_rad": phase_rms, "coherence": coherence},
            criterion_ids=[],
        ),
        reference_agreement=ReferenceAgreementResult(
            measurements={
                "amplitude_r": amp_corr,
                "amplitude_rmse_db": amp_rmse_db,
            },
            criterion_ids=["cslc.amplitude_r_min", "cslc.amplitude_rmse_db_max"],
        ),
    )


def compare_cslc_egms_l2a_residual(
    our_velocity_raster: Path,
    egms_csv_paths: list[Path],
    *,
    stable_std_max: float = 2.0,
    velocity_col: str = "mean_velocity",
    min_valid_points: int = 100,
) -> float:
    """Return mean |our_velocity - EGMS L2a stable_ps_velocity| after reference-frame alignment.

    Per CONTEXT 03-CONTEXT.md D-12 + PITFALLS P2.3:

    1. Load EGMS L2a PS points via compare_disp._load_egms_l2a_points
       (cross-module import is function-body-local per PATTERNS rules —
       marks the dependency load-bearing-here-only).
    2. Filter to stable PS: ``df[df['mean_velocity_std'] < stable_std_max]``.
    3. Sample ``our_velocity_raster`` at the stable-PS locations via rasterio.
    4. Reference-frame alignment: subtract the stable-set median of our sampled
       values from every pixel BEFORE computing the paired residual
       (our_aligned = our - np.median(our_stable)). EGMS values are already
       reference-aligned by EGMS itself.
    5. Return ``float(np.mean(|our_aligned - egms_velocity|))`` (mm/yr scalar).
    6. If ``n_valid_ps < min_valid_points``, log a warning and return ``float('nan')``.

    See docs/validation_methodology.md (Plan 03-05) for the product-quality vs
    reference-agreement distinction this helper participates in.

    Args:
        our_velocity_raster: Path to the subsideo CSLC velocity GeoTIFF (mm/yr).
        egms_csv_paths: One or more EGMS L2a CSV files with at least
            ``longitude``/``latitude``/``mean_velocity``/``mean_velocity_std``
            columns (produced by EGMStoolkit).
        stable_std_max: Filter threshold for ``mean_velocity_std`` (mm/yr).
            Points with std >= this value are excluded from the stable-PS set.
            Default 2.0 per BOOTSTRAP §2.3.
        velocity_col: Column name for EGMS mean velocity. Default ``"mean_velocity"``.
        min_valid_points: Minimum number of valid paired samples; returns NaN
            if fewer are available (matches compare_disp_egms_l2a line 339 pattern).

    Returns:
        Mean absolute residual in mm/yr, or NaN if too few valid samples.
    """
    # Function-body-local cross-module import — marks load-bearing-here-only (D-12 + PATTERNS)
    import geopandas as gpd  # noqa: PLC0415
    import rasterio  # noqa: PLC0415
    from shapely.geometry import Point  # noqa: PLC0415

    from subsideo.validation.compare_disp import _load_egms_l2a_points  # noqa: PLC0415

    df = _load_egms_l2a_points([Path(p) for p in egms_csv_paths], velocity_col=velocity_col)
    if "mean_velocity_std" not in df.columns:
        raise ValueError(
            "EGMS L2a CSV(s) missing 'mean_velocity_std' column -- required for "
            "stable-PS filter per Phase 3 D-12. Ensure CSV is EGMS L2a product "
            "(not Ortho) and was produced by EGMStoolkit >= 0.2.15."
        )
    stable_df = df[df["mean_velocity_std"] < stable_std_max].copy()

    points = gpd.GeoDataFrame(
        stable_df,
        geometry=[Point(xy) for xy in zip(stable_df["lon"], stable_df["lat"], strict=True)],
        crs="EPSG:4326",
    )

    with rasterio.open(our_velocity_raster) as src:
        raster_crs = src.crs
        # Capture nodata while dataset is open (CR-01 pattern from compare_disp)
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

        if len(points_in) == 0:
            logger.warning(
                "compare_cslc_egms_l2a_residual: no stable PS within raster bounds "
                "(raster={}, n_stable_ps={})",
                our_velocity_raster.name,
                len(stable_df),
            )
            return float("nan")

        xy = list(zip(points_in.geometry.x, points_in.geometry.y, strict=True))
        our_sampled = np.array([v[0] for v in src.sample(xy)], dtype=np.float64)

    if nodata is not None:
        our_sampled = np.where(our_sampled == nodata, np.nan, our_sampled)

    egms_vals = points_in[velocity_col].values.astype(np.float64)
    valid = np.isfinite(our_sampled) & np.isfinite(egms_vals)
    n_valid = int(valid.sum())
    n_stable_ps = len(stable_df)
    logger.debug(
        "compare_cslc_egms_l2a_residual: n_ps_total={}, n_stable_ps={}, n_in_raster={}, n_valid={}",
        len(df),
        n_stable_ps,
        len(points_in),
        n_valid,
    )

    if n_valid < min_valid_points:
        logger.warning(
            "compare_cslc_egms_l2a_residual: only {} valid paired PS < "
            "min_valid_points={}; returning NaN",
            n_valid,
            min_valid_points,
        )
        return float("nan")

    our_valid = our_sampled[valid]
    egms_valid = egms_vals[valid]

    # Reference-frame alignment (P2.3): subtract stable-set median of OUR chain
    # BEFORE paired residual. EGMS already reference-aligned by EGMS processing.
    our_aligned = our_valid - float(np.median(our_valid))
    residual = float(np.mean(np.abs(our_aligned - egms_valid)))

    logger.info(
        "compare_cslc_egms_l2a_residual: residual={:.3f} mm/yr on {} stable PS",
        residual,
        n_valid,
    )
    return residual
