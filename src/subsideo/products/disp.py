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
    threads_per_worker: int = 4,
    n_parallel_bursts: int = 1,
    block_shape: tuple[int, int] = (512, 512),
    n_parallel_unwrap: int = 4,
) -> tuple[list[Path], list[Path]]:
    """Run dolphin PS/DS phase linking on a CSLC stack.

    Parameters
    ----------
    cslc_file_list:
        Paths to CSLC HDF5 files.
    work_dir:
        Working directory for dolphin outputs.
    coherence_threshold:
        Coherence threshold (unused by dolphin directly, kept for API compat).
    threads_per_worker:
        Threads per worker for phase linking computation.
    n_parallel_bursts:
        Number of bursts to process in parallel.
    block_shape:
        Block size for phase linking (rows, cols).
    n_parallel_unwrap:
        Number of parallel unwrapping jobs.

    Returns
    -------
    tuple[list[Path], list[Path]]
        (interferogram_paths, coherence_paths) produced by dolphin.
    """
    from dolphin.workflows.config import (
        DisplacementWorkflow,
        InputOptions,
        WorkerSettings,
        UnwrapOptions,
    )
    from dolphin.workflows.displacement import run as dolphin_run

    work_dir.mkdir(parents=True, exist_ok=True)

    from dolphin.workflows.config._unwrap_options import UnwrapMethod

    # OPERA CSLC HDF5 files store complex SLC data under /data/VV.
    # Use PHASS (isce3 phase-and-slope unwrapper): tree-growing algorithm
    # that always terminates, handles noisy/low-coherence data better
    # than ICU, and is orders of magnitude faster than SNAPHU on large
    # grids (SNAPHU can hang on >70M pixel grids).
    cfg = DisplacementWorkflow(
        cslc_file_list=[str(p) for p in cslc_file_list],
        input_options=InputOptions(subdataset="/data/VV"),
        work_directory=work_dir,
        worker_settings=WorkerSettings(
            threads_per_worker=threads_per_worker,
            n_parallel_bursts=n_parallel_bursts,
            block_shape=block_shape,
        ),
        unwrap_options=UnwrapOptions(
            run_unwrap=True,
            unwrap_method=UnwrapMethod.PHASS,
            n_parallel_jobs=n_parallel_unwrap,
        ),
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


def _unwrap_single(args: tuple) -> Path:
    """Unwrap a single interferogram with snaphu tiling. Worker function."""
    import rasterio
    import snaphu

    ifg_path, cor_path, out_path, ntiles, nproc = args

    with rasterio.open(ifg_path) as ifg_ds:
        ifg_data = ifg_ds.read(1)
        profile = ifg_ds.profile.copy()
    with rasterio.open(cor_path) as cor_ds:
        cor_data = cor_ds.read(1)

    ifg_finite = np.where(np.isfinite(ifg_data), ifg_data, 0.0)
    cor_finite = np.where(np.isfinite(cor_data), cor_data, 0.0)

    if not np.iscomplexobj(ifg_finite):
        ifg_complex = np.exp(1j * ifg_finite.astype(np.float32))
    else:
        ifg_complex = ifg_finite

    unwrapped_arr, _conncomp = snaphu.unwrap(
        igram=ifg_complex,
        corr=cor_finite.astype(np.float32),
        nlooks=1.0,
        cost="smooth",
        init="mcf",
        ntiles=ntiles,
        nproc=nproc,
        tile_overlap=200,
        tile_cost_thresh=200,
        min_region_size=200,
    )

    profile.update(dtype="float32")
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(np.asarray(unwrapped_arr, dtype=np.float32), 1)

    return out_path


def _run_unwrapping(
    masked_ifg_paths: list[Path],
    cor_paths: list[Path],
    work_dir: Path,
    ntiles: tuple[int, int] = (2, 2),
    nproc: int = 2,
    n_parallel_ifgs: int = 4,
) -> list[Path]:
    """Unwrap interferograms using snaphu with tiled + interferogram parallelism.

    Processes ``n_parallel_ifgs`` interferograms concurrently, each with
    snaphu's built-in ``ntiles`` x ``nproc`` tiling. This maximises CPU
    utilisation on multi-core systems.

    Parameters
    ----------
    masked_ifg_paths:
        Masked interferogram GeoTIFFs (complex phase).
    cor_paths:
        Coherence GeoTIFFs matching the interferograms.
    work_dir:
        Output directory for unwrapped GeoTIFFs.
    ntiles:
        Number of tiles (rows, cols) for snaphu tiling within each interferogram.
    nproc:
        Number of parallel snaphu tile workers per interferogram.
    n_parallel_ifgs:
        Number of interferograms to unwrap concurrently.

    Returns
    -------
    list[Path]
        Paths to unwrapped phase GeoTIFFs.
    """
    from concurrent.futures import ProcessPoolExecutor, as_completed

    work_dir.mkdir(parents=True, exist_ok=True)

    # Build argument tuples, skipping already-unwrapped files
    args_list = []
    out_paths = []
    for ifg_path, cor_path in zip(masked_ifg_paths, cor_paths, strict=True):
        out_path = work_dir / f"{ifg_path.stem}_unwrapped.tif"
        out_paths.append(out_path)
        if out_path.exists():
            logger.info("Already unwrapped: {}", out_path.name)
            continue
        args_list.append((ifg_path, cor_path, out_path, ntiles, nproc))

    if args_list:
        logger.info(
            "Unwrapping {} interferograms ({} parallel, {}x{} tiles, {} procs/tile)",
            len(args_list), n_parallel_ifgs, *ntiles, nproc,
        )
        completed = 0
        with ProcessPoolExecutor(max_workers=n_parallel_ifgs) as executor:
            futures = {executor.submit(_unwrap_single, a): a[2] for a in args_list}
            for future in as_completed(futures):
                out = futures[future]
                try:
                    future.result()
                    completed += 1
                    logger.info("Unwrapped {}/{}: {}", completed, len(args_list), out.name)
                except Exception as exc:
                    logger.error("Unwrap failed for {}: {}", out.name, exc)

    logger.info("Phase unwrapping complete: {} files", len(out_paths))
    return out_paths


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
    threads_per_worker: int = 4,
    n_parallel_bursts: int = 1,
    block_shape: tuple[int, int] = (512, 512),
    n_parallel_unwrap: int = 4,
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
    threads_per_worker:
        Threads per worker for dolphin phase linking.
    n_parallel_bursts:
        Number of bursts to process in parallel.
    block_shape:
        Block size for phase linking (rows, cols).
    n_parallel_unwrap:
        Number of parallel unwrapping jobs.

    Returns
    -------
    DISPResult
        Pipeline result with velocity path, time-series paths, and QC info.
    """
    # ENV-04: configure multiprocessing BEFORE any subprocess or matplotlib import
    from subsideo._mp import configure_multiprocessing

    configure_multiprocessing()

    if cdsapirc_path is None:
        cdsapirc_path = Path.home() / ".cdsapirc"

    # D-03: fail fast before any processing
    _validate_cds_credentials(cdsapirc_path)

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Stage 1: dolphin phase linking + ICU unwrapping
        # dolphin handles phase linking, interferogram creation, and
        # unwrapping (ICU) in a single workflow. Coherence masking and
        # separate unwrapping stages are not needed.
        ifg_paths, cor_paths = _run_dolphin_phase_linking(
            cslc_paths, output_dir / "dolphin", coherence_mask_threshold,
            threads_per_worker=threads_per_worker,
            n_parallel_bursts=n_parallel_bursts,
            block_shape=block_shape,
            n_parallel_unwrap=n_parallel_unwrap,
        )

        # dolphin 0.42+ handles the full pipeline: phase linking, unwrapping,
        # network inversion, and velocity estimation. Collect outputs from
        # dolphin's timeseries directory instead of running MintPy separately.
        dolphin_dir = output_dir / "dolphin"
        ts_dir = dolphin_dir / "timeseries"
        unwrap_dir = dolphin_dir / "unwrapped"

        # Velocity (GeoTIFF, units: rad/year in LOS)
        velocity_path = ts_dir / "velocity.tif"
        if not velocity_path.exists():
            velocity_path = None
            logger.warning("No velocity.tif found in dolphin timeseries output")

        # Displacement time-series epochs
        ts_paths = sorted(ts_dir.glob("20*.tif")) if ts_dir.exists() else []
        logger.info("Dolphin produced {} time-series epochs", len(ts_paths))

        # Collect unwrapped outputs for QC
        unwrapped_paths = sorted(unwrap_dir.glob("*.unw.tif")) if unwrap_dir.exists() else []
        logger.info("Dolphin unwrapped {} interferograms", len(unwrapped_paths))

        # Post-unwrap QC (flag-and-continue)
        qc_warnings: list[str] = []
        for uwp in unwrapped_paths:
            qc = _check_unwrap_quality(uwp, ramp_threshold)
            if qc["flagged"]:
                qc_warnings.append(
                    f"Planar ramp anomaly in {qc['path']}: "
                    f"residual RMS {qc['residual_rms']:.3f}"
                )

        return DISPResult(
            velocity_path=velocity_path,
            timeseries_paths=ts_paths,
            output_dir=output_dir,
            valid=velocity_path is not None,
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
