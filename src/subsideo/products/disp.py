"""DISP-S1 displacement time-series pipeline orchestrator.

Chains dolphin phase linking, tophu multi-scale unwrapping, and MintPy
time-series inversion (with mandatory ERA5 tropospheric correction) to
produce OPERA-spec DISP-S1 displacement products.

All conda-forge-only imports (dolphin, tophu, MintPy, scipy) are lazy --
kept inside function bodies so the module is importable without them.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from loguru import logger

from subsideo.products.types import DISPResult

# ---------------------------------------------------------------------------
# CDS credential validation (D-03: fail fast before any processing)
# ---------------------------------------------------------------------------


def _validate_cds_credentials(cdsapirc_path: Path) -> None:
    """Check that CDS API credentials file exists and is complete.

    Raises
    ------
    FileNotFoundError
        If *cdsapirc_path* does not exist.
    ValueError
        If the file is missing ``url:`` or ``key:`` lines.
    """
    if not cdsapirc_path.exists():
        raise FileNotFoundError(
            f"CDS API config not found at {cdsapirc_path}. "
            "ERA5 tropospheric correction is mandatory for DISP. "
            "Register at https://cds.climate.copernicus.eu/"
        )

    text = cdsapirc_path.read_text()
    has_url = any(line.strip().startswith("url:") for line in text.splitlines())
    has_key = any(line.strip().startswith("key:") for line in text.splitlines())
    if not (has_url and has_key):
        raise ValueError(
            f"CDS API config at {cdsapirc_path} is incomplete "
            "-- must contain url: and key: fields"
        )


# ---------------------------------------------------------------------------
# Stage 1: dolphin phase linking (D-04: lazy import)
# ---------------------------------------------------------------------------


def _run_dolphin_phase_linking(
    cslc_file_list: list[Path],
    work_dir: Path,
    coherence_threshold: float,
) -> tuple[list[Path], list[Path]]:
    """Run dolphin PS/DS phase linking on a CSLC stack.

    Returns
    -------
    tuple[list[Path], list[Path]]
        (interferogram_paths, coherence_paths) produced by dolphin.
    """
    from dolphin.workflows.config import DisplacementWorkflow
    from dolphin.workflows.displacement import run as dolphin_run

    work_dir.mkdir(parents=True, exist_ok=True)

    cfg = DisplacementWorkflow(
        cslc_file_list=[str(p) for p in cslc_file_list],
    )
    outputs = dolphin_run(cfg)

    ifg_paths = [Path(p) for p in outputs.stitched_ifg_paths]
    cor_paths = [Path(p) for p in outputs.stitched_cor_paths]
    logger.info("dolphin phase linking complete: {} interferograms", len(ifg_paths))
    return ifg_paths, cor_paths


# ---------------------------------------------------------------------------
# Stage 2: coherence masking (D-06)
# ---------------------------------------------------------------------------


def _apply_coherence_mask(
    ifg_paths: list[Path],
    cor_paths: list[Path],
    threshold: float,
) -> list[Path]:
    """Mask interferograms where coherence is below *threshold*.

    Returns
    -------
    list[Path]
        Paths to masked interferogram GeoTIFFs.
    """
    import rasterio

    masked_paths: list[Path] = []

    for ifg_path, cor_path in zip(ifg_paths, cor_paths, strict=True):
        with rasterio.open(cor_path) as cor_ds:
            cor_data = cor_ds.read(1)
        with rasterio.open(ifg_path) as ifg_ds:
            ifg_data = ifg_ds.read(1)
            profile = ifg_ds.profile.copy()

        mask = cor_data < threshold
        ifg_data[mask] = np.nan

        out_path = ifg_path.parent / f"{ifg_path.stem}_masked.tif"
        with rasterio.open(out_path, "w", **profile) as dst:
            dst.write(ifg_data, 1)
        masked_paths.append(out_path)

    logger.info("Coherence masking applied: {} files, threshold={}", len(masked_paths), threshold)
    return masked_paths


# ---------------------------------------------------------------------------
# Stage 3: tophu multi-scale unwrapping
# ---------------------------------------------------------------------------


def _run_unwrapping(
    masked_ifg_paths: list[Path],
    cor_paths: list[Path],
    work_dir: Path,
) -> list[Path]:
    """Unwrap masked interferograms using tophu multi-scale unwrapping.

    Returns
    -------
    list[Path]
        Paths to unwrapped phase GeoTIFFs.
    """
    import rasterio
    import tophu

    work_dir.mkdir(parents=True, exist_ok=True)
    unwrapped_paths: list[Path] = []

    unwrapper = tophu.SnaphuUnwrap(cost="smooth", init="mcf")

    for ifg_path, cor_path in zip(masked_ifg_paths, cor_paths, strict=True):
        with rasterio.open(ifg_path) as ifg_ds:
            ifg_data = ifg_ds.read(1)
            profile = ifg_ds.profile.copy()
        with rasterio.open(cor_path) as cor_ds:
            cor_data = cor_ds.read(1)

        unwrapped, _conncomp = tophu.multiscale_unwrap(
            ifg=ifg_data,
            corr=cor_data,
            nlooks=1.0,
            unwrap_func=unwrapper,
            downsample_factor=(3, 3),
            ntiles=(2, 2),
        )

        out_path = work_dir / f"{ifg_path.stem}_unwrapped.tif"
        profile.update(dtype="float32")
        with rasterio.open(out_path, "w", **profile) as dst:
            dst.write(np.asarray(unwrapped, dtype=np.float32), 1)
        unwrapped_paths.append(out_path)

    logger.info("Phase unwrapping complete: {} files", len(unwrapped_paths))
    return unwrapped_paths


# ---------------------------------------------------------------------------
# Stage 4: post-unwrapping QC (D-05: flag-and-continue)
# ---------------------------------------------------------------------------


def _check_unwrap_quality(unwrapped_path: Path, threshold: float) -> dict:
    """Fit a plane to unwrapped phase and flag anomalous residual.

    Returns
    -------
    dict
        Keys: ``path``, ``residual_rms``, ``flagged``.
    """
    import rasterio
    from scipy.linalg import lstsq

    with rasterio.open(unwrapped_path) as ds:
        phase = ds.read(1).astype(np.float64)

    valid = ~np.isnan(phase)
    if valid.sum() < 4:
        return {"path": str(unwrapped_path), "residual_rms": 0.0, "flagged": False}

    rows, cols = np.where(valid)
    y = rows.astype(np.float64)
    x = cols.astype(np.float64)
    design = np.column_stack([x, y, np.ones(len(x))])
    b = phase[valid]

    coeffs, _residuals, _rank, _sv = lstsq(design, b)
    plane = design @ coeffs
    residual_rms = float(np.sqrt(np.mean((b - plane) ** 2)))

    flagged = residual_rms > threshold

    if flagged:
        logger.warning(
            "Planar ramp anomaly detected in {}: residual RMS {:.3f} > threshold {}",
            unwrapped_path,
            residual_rms,
            threshold,
        )

    return {
        "path": str(unwrapped_path),
        "residual_rms": residual_rms,
        "flagged": flagged,
    }


# ---------------------------------------------------------------------------
# Stage 5: MintPy template + time-series inversion (D-04)
# ---------------------------------------------------------------------------


def _generate_mintpy_template(work_dir: Path, cdsapirc_path: Path) -> Path:
    """Create a MintPy smallbaselineApp.cfg template.

    Returns
    -------
    Path
        Path to the written template file.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = work_dir / "smallbaselineApp.cfg"

    template = (
        "# MintPy configuration generated by subsideo\n"
        "mintpy.load.processor = dolphin\n"
        "mintpy.troposphericDelay.method = pyaps\n"
        "mintpy.troposphericDelay.weatherModel = ERA5\n"
        "mintpy.networkInversion.minTempCoh = 0.7\n"
        "mintpy.timeFunc.polynomial = 1\n"
    )

    cfg_path.write_text(template)
    logger.info("MintPy template written to {}", cfg_path)
    return cfg_path


def _run_mintpy_timeseries(work_dir: Path, template_path: Path) -> list[Path]:
    """Run MintPy time-series inversion.

    Returns
    -------
    list[Path]
        Sorted list of HDF5 output files from MintPy.
    """
    from mintpy.smallbaselineApp import TimeSeriesAnalysis

    app = TimeSeriesAnalysis(
        customTemplateFile=str(template_path),
        workDir=str(work_dir),
    )
    app.open()
    app.run(
        steps=[
            "load_data",
            "modify_network",
            "reference_point",
            "invert_network",
            "correct_troposphere",
            "deramp",
            "correct_dem_error",
            "velocity",
        ]
    )
    app.close()

    h5_paths = sorted(work_dir.glob("*.h5"))
    logger.info("MintPy time-series inversion complete")
    return h5_paths


# ---------------------------------------------------------------------------
# Public API: run_disp (D-01: low-level CSLC-list entry point)
# ---------------------------------------------------------------------------


def run_disp(
    cslc_paths: list[Path],
    output_dir: Path,
    cdsapirc_path: Path | None = None,
    coherence_mask_threshold: float = 0.3,
    ramp_threshold: float = 1.0,
) -> DISPResult:
    """Run the full DISP-S1 displacement time-series pipeline.

    Chains dolphin phase linking -> coherence masking -> tophu unwrapping
    -> post-unwrap QC -> MintPy time-series inversion with ERA5 correction.

    Parameters
    ----------
    cslc_paths:
        Paths to CSLC HDF5 files forming the input stack.
    output_dir:
        Root directory for all pipeline outputs.
    cdsapirc_path:
        Path to CDS API credentials (defaults to ``~/.cdsapirc``).
    coherence_mask_threshold:
        Coherence below this value is masked before unwrapping.
    ramp_threshold:
        Residual RMS threshold for post-unwrap planar ramp flagging.

    Returns
    -------
    DISPResult
        Pipeline result with velocity path, time-series paths, and QC info.
    """
    if cdsapirc_path is None:
        cdsapirc_path = Path.home() / ".cdsapirc"

    # D-03: fail fast before any processing
    _validate_cds_credentials(cdsapirc_path)

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Stage 1: dolphin phase linking
        ifg_paths, cor_paths = _run_dolphin_phase_linking(
            cslc_paths, output_dir / "dolphin", coherence_mask_threshold
        )

        # Stage 2: coherence masking
        masked_ifgs = _apply_coherence_mask(ifg_paths, cor_paths, coherence_mask_threshold)

        # Stage 3: tophu unwrapping
        unwrapped_paths = _run_unwrapping(masked_ifgs, cor_paths, output_dir / "unwrap")

        # Stage 4: post-unwrap QC (flag-and-continue)
        qc_warnings: list[str] = []
        for uwp in unwrapped_paths:
            qc = _check_unwrap_quality(uwp, ramp_threshold)
            if qc["flagged"]:
                qc_warnings.append(
                    f"Planar ramp anomaly in {qc['path']}: "
                    f"residual RMS {qc['residual_rms']:.3f}"
                )

        # Stage 5: MintPy time-series inversion
        mintpy_dir = output_dir / "mintpy"
        template_path = _generate_mintpy_template(mintpy_dir, cdsapirc_path)
        ts_paths = _run_mintpy_timeseries(mintpy_dir, template_path)

        velocity_path = mintpy_dir / "velocity.h5"
        if not velocity_path.exists():
            velocity_path = None

        return DISPResult(
            velocity_path=velocity_path,
            timeseries_paths=ts_paths,
            output_dir=output_dir,
            valid=True,
            qc_warnings=qc_warnings,
        )

    except ImportError as exc:
        dep = str(exc).split("'")[1] if "'" in str(exc) else str(exc)
        logger.error("{} not installed -- install via conda-forge", dep)
        return DISPResult(
            velocity_path=None,
            timeseries_paths=[],
            output_dir=output_dir,
            valid=False,
            validation_errors=[f"{dep} not installed (conda-forge required)"],
        )
    except Exception as exc:
        logger.error("DISP pipeline failed: {}", exc)
        return DISPResult(
            velocity_path=None,
            timeseries_paths=[],
            output_dir=output_dir,
            valid=False,
            validation_errors=[f"DISP pipeline error: {exc}"],
        )


# ---------------------------------------------------------------------------
# Public API: run_disp_from_aoi (D-02: end-to-end AOI + date range)
# ---------------------------------------------------------------------------


def run_disp_from_aoi(
    aoi: dict | Path,
    date_range: tuple[str, str],
    output_dir: Path,
    cdsapirc_path: Path | None = None,
    coherence_mask_threshold: float = 0.3,
    ramp_threshold: float = 1.0,
) -> DISPResult:
    """End-to-end DISP-S1 pipeline from AOI geometry and date range.

    Builds a CSLC stack by querying CDSE for Sentinel-1 IW SLC scenes,
    running ``run_cslc()`` for each scene/burst combination, then feeds
    the CSLC HDF5 stack into ``run_disp()``.

    Parameters
    ----------
    aoi:
        GeoJSON dict (``{"type": "Polygon", "coordinates": ...}``) or
        a ``Path`` to a GeoJSON file.
    date_range:
        ``(start_date, end_date)`` strings in ``YYYY-MM-DD`` format.
    output_dir:
        Root directory for all pipeline outputs.
    cdsapirc_path:
        Path to CDS API credentials (defaults to ``~/.cdsapirc``).
    coherence_mask_threshold:
        Coherence masking threshold for unwrapping.
    ramp_threshold:
        Residual RMS threshold for post-unwrap QC.

    Returns
    -------
    DISPResult
        Pipeline result from the DISP processing stage.
    """
    from datetime import datetime

    from subsideo.burst.frames import query_bursts_for_aoi
    from subsideo.data.cdse import CDSEClient
    from subsideo.data.dem import fetch_dem
    from subsideo.data.orbits import fetch_orbit
    from subsideo.products.cslc import run_cslc

    if cdsapirc_path is None:
        cdsapirc_path = Path.home() / ".cdsapirc"

    # D-03: validate CDS credentials before any processing
    _validate_cds_credentials(cdsapirc_path)

    # Resolve AOI geometry
    if isinstance(aoi, Path):
        with open(aoi) as f:
            aoi = json.load(f)

    if "type" not in aoi or "coordinates" not in aoi:
        return DISPResult(
            velocity_path=None,
            timeseries_paths=[],
            output_dir=output_dir,
            valid=False,
            validation_errors=["Invalid AOI: must contain 'type' and 'coordinates' keys"],
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Convert AOI coordinates to bounding box for CDSE search
        coords = aoi["coordinates"][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        bbox = [min(lons), min(lats), max(lons), max(lats)]

        # Build WKT for burst query
        from shapely.geometry import shape

        aoi_geom = shape(aoi)
        aoi_wkt = aoi_geom.wkt

        # Query burst DB for AOI
        bursts = query_bursts_for_aoi(aoi_wkt)
        if not bursts:
            return DISPResult(
                velocity_path=None,
                timeseries_paths=[],
                output_dir=output_dir,
                valid=False,
                validation_errors=["No EU bursts found for AOI"],
            )
        burst_ids = [b.burst_id_jpl for b in bursts]
        logger.info("Found {} bursts for AOI", len(burst_ids))

        # Search CDSE for S1 IW SLC scenes
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
            collection="SENTINEL-1",
            bbox=bbox,
            start=start_dt,
            end=end_dt,
            product_type="IW_SLC__1S",
        )
        logger.info("Searching CDSE for {} scenes...", len(scenes))

        # Download scenes and fetch DEM/orbits
        output_epsg = bursts[0].epsg
        dem_path, _dem_profile = fetch_dem(
            bounds=bbox,
            output_epsg=output_epsg,
            output_dir=output_dir / "dem",
        )

        cslc_paths: list[Path] = []
        for i, scene in enumerate(scenes):
            logger.info("Building CSLC stack: {}/{} ...", i + 1, len(scenes))

            # Download SAFE file
            s3_key = scene.get("assets", {}).get("data", {}).get("href", "")
            safe_path = output_dir / "safe" / f"scene_{i}.zip"
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            client.download(s3_key, safe_path)

            # Fetch orbit
            sensing_time = datetime.fromisoformat(
                scene.get("properties", {}).get("datetime", start_str)
            )
            satellite = scene.get("properties", {}).get("platform", "S1A")
            orbit_path = fetch_orbit(
                sensing_time=sensing_time,
                satellite=satellite,
                output_dir=output_dir / "orbits",
            )

            # Run CSLC for this scene
            cslc_result = run_cslc(
                safe_paths=[safe_path],
                orbit_path=orbit_path,
                dem_path=dem_path,
                burst_ids=burst_ids,
                output_dir=output_dir / "cslc" / f"scene_{i}",
            )

            if cslc_result.valid:
                cslc_paths.extend(cslc_result.output_paths)
            else:
                logger.warning(
                    "CSLC failed for scene {}: {}", i, cslc_result.validation_errors
                )

        logger.info(
            "CSLC stack complete, {} files. Starting DISP pipeline...", len(cslc_paths)
        )

        if not cslc_paths:
            return DISPResult(
                velocity_path=None,
                timeseries_paths=[],
                output_dir=output_dir,
                valid=False,
                validation_errors=["No valid CSLC products were produced"],
            )

        # Feed CSLC stack into DISP pipeline
        return run_disp(
            cslc_paths=cslc_paths,
            output_dir=output_dir,
            cdsapirc_path=cdsapirc_path,
            coherence_mask_threshold=coherence_mask_threshold,
            ramp_threshold=ramp_threshold,
        )

    except Exception as exc:
        logger.error("DISP AOI pipeline failed: {}", exc)
        return DISPResult(
            velocity_path=None,
            timeseries_paths=[],
            output_dir=output_dir,
            valid=False,
            validation_errors=[f"DISP AOI pipeline error: {exc}"],
        )
