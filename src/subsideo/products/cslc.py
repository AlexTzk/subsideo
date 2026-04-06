"""CSLC-S1 pipeline orchestrator.

Generates compass YAML runconfigs, invokes the compass Python API
(compass.s1_cslc.run), and validates HDF5 output compliance against
the OPERA CSLC-S1 product specification.
"""
from __future__ import annotations

import re
from pathlib import Path

from loguru import logger
from ruamel.yaml import YAML

from subsideo.products.types import CSLCConfig, CSLCResult


def generate_cslc_runconfig(cfg: CSLCConfig, output_yaml: Path) -> Path:
    """Build a compass-compatible YAML runconfig and write it to disk.

    Parameters
    ----------
    cfg:
        CSLC pipeline configuration.
    output_yaml:
        Destination path for the YAML runconfig file.

    Returns
    -------
    Path
        The *output_yaml* path (for chaining convenience).
    """
    runconfig = {
        "runconfig": {
            "name": "cslc_s1_workflow",
            "groups": {
                "input_file_group": {
                    "safe_file_path": [str(p) for p in cfg.safe_file_paths],
                    "orbit_file_path": [str(cfg.orbit_file_path)],
                    "burst_id": cfg.burst_id,
                },
                "dynamic_ancillary_file_group": {
                    "dem_file": str(cfg.dem_file),
                    "tec_file": str(cfg.tec_file) if cfg.tec_file else None,
                },
                "product_path_group": {
                    "product_path": str(cfg.output_dir),
                    "scratch_path": str(cfg.output_dir / "scratch"),
                    "product_version": cfg.product_version,
                },
                "primary_executable": {
                    "product_type": "CSLC_S1",
                },
            },
        }
    }

    output_yaml.parent.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    yaml.default_flow_style = False
    with open(output_yaml, "w") as fh:
        yaml.dump(runconfig, fh)

    logger.info("Wrote CSLC runconfig to {}", output_yaml)
    return output_yaml


def validate_cslc_product(hdf5_paths: list[Path]) -> list[str]:
    """Lightweight validation of CSLC-S1 HDF5 products.

    Checks each file for basic structural compliance:
    - File exists and is readable
    - Opens with h5py without error
    - Contains a ``/data`` group
    - Contains at least one dataset under ``/data``
    - Contains ``/metadata`` or ``/identification`` group

    Parameters
    ----------
    hdf5_paths:
        Paths to CSLC HDF5 product files.

    Returns
    -------
    list[str]
        Error messages. Empty list means all files are valid.
    """
    import h5py

    errors: list[str] = []

    for path in hdf5_paths:
        prefix = f"{path.name}"

        if not path.exists():
            errors.append(f"{prefix}: file does not exist")
            continue

        try:
            with h5py.File(path, "r") as f:
                # Check /data group
                if "data" not in f:
                    errors.append(f"{prefix}: missing /data group")
                    continue

                data_group = f["data"]
                if len(data_group) == 0:
                    errors.append(f"{prefix}: /data group is empty (no datasets)")

                # Check metadata or identification group
                if "metadata" not in f and "identification" not in f:
                    errors.append(
                        f"{prefix}: missing /metadata and /identification groups"
                    )
        except Exception as exc:
            errors.append(f"{prefix}: failed to open HDF5 — {exc}")

    return errors


def run_cslc(
    safe_paths: list[Path],
    orbit_path: Path,
    dem_path: Path,
    burst_ids: list[str] | None,
    output_dir: Path,
    tec_file: Path | None = None,
    product_version: str = "0.1.0",
) -> CSLCResult:
    """Run the full CSLC-S1 pipeline.

    Builds configuration, generates a compass YAML runconfig, invokes
    ``compass.s1_cslc.run`` via the Python API directly, and
    validates the resulting HDF5 products.

    Parameters
    ----------
    safe_paths:
        Sentinel-1 SAFE/zip file paths.
    orbit_path:
        Precise orbit file path.
    dem_path:
        DEM GeoTIFF file path.
    burst_ids:
        Optional burst ID filter (e.g. ``["T001-123456-IW1"]``).
    output_dir:
        Directory for output products and scratch space.
    tec_file:
        Optional ionospheric TEC correction file.
    product_version:
        Product version string for OPERA metadata.

    Returns
    -------
    CSLCResult
        Pipeline result with output paths, validation status, and errors.
    """
    cfg = CSLCConfig(
        safe_file_paths=safe_paths,
        orbit_file_path=orbit_path,
        dem_file=dem_path,
        burst_id=burst_ids,
        output_dir=output_dir,
        tec_file=tec_file,
        product_version=product_version,
    )

    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "scratch").mkdir(parents=True, exist_ok=True)

    # Generate runconfig
    runconfig_yaml = generate_cslc_runconfig(cfg, output_dir / "cslc_runconfig.yaml")
    logger.info("CSLC runconfig generated at {}", runconfig_yaml)

    # Invoke compass Python API (lazy import — conda-forge only)
    try:
        from compass.s1_cslc import run as compass_run

        compass_run(run_config_path=str(runconfig_yaml), grid_type="geo")
        logger.info("compass CSLC processing complete")
    except ImportError:
        logger.error("compass not installed — install via conda-forge")
        return CSLCResult(
            output_paths=[],
            runconfig_path=runconfig_yaml,
            burst_ids=burst_ids or [],
            valid=False,
            validation_errors=["compass not installed (conda-forge required)"],
        )
    except Exception as exc:
        logger.error("compass CSLC failed: {}", exc)
        return CSLCResult(
            output_paths=[],
            runconfig_path=runconfig_yaml,
            burst_ids=burst_ids or [],
            valid=False,
            validation_errors=[f"compass execution error: {exc}"],
        )

    # Collect output HDF5 files
    h5_paths = sorted(output_dir.glob("*.h5"))
    logger.info("Found {} CSLC HDF5 outputs", len(h5_paths))

    # Validate products
    errors = validate_cslc_product(h5_paths)

    # Derive burst IDs from result if not provided
    result_burst_ids: list[str]
    if burst_ids:
        result_burst_ids = burst_ids
    else:
        # Try to extract burst IDs from output filenames
        # Compass outputs are named like: t001_123456_iw1_YYYYMMDD.h5
        result_burst_ids = []
        burst_pattern = re.compile(r"(t\d{3}_\d{6}_iw\d)", re.IGNORECASE)
        for p in h5_paths:
            m = burst_pattern.search(p.stem)
            if m:
                result_burst_ids.append(m.group(1).upper())
        result_burst_ids = sorted(set(result_burst_ids))

    return CSLCResult(
        output_paths=h5_paths,
        runconfig_path=runconfig_yaml,
        burst_ids=result_burst_ids,
        valid=len(errors) == 0,
        validation_errors=errors,
    )


def run_cslc_from_aoi(
    aoi: dict | Path,
    date_range: tuple[str, str],
    output_dir: Path,
) -> CSLCResult:
    """End-to-end CSLC-S1 pipeline from AOI and date range.

    Queries CDSE for Sentinel-1 SLC scenes, downloads orbit and DEM,
    resolves EU burst IDs, and runs :func:`run_cslc`.

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
    CSLCResult
        Processing result.
    """
    import json as _json
    from datetime import datetime

    from shapely.geometry import shape

    from subsideo.burst.frames import query_bursts_for_aoi
    from subsideo.config import Settings
    from subsideo.data.cdse import CDSEClient
    from subsideo.data.dem import fetch_dem
    from subsideo.data.orbits import fetch_orbit

    # Resolve AOI
    if isinstance(aoi, Path):
        with open(aoi) as f:
            aoi = _json.load(f)

    if "type" not in aoi or "coordinates" not in aoi:
        return CSLCResult(
            output_paths=[],
            runconfig_path=output_dir / "runconfig.yaml",
            burst_ids=[],
            valid=False,
            validation_errors=["Invalid GeoJSON: missing type or coordinates"],
        )

    geom = shape(aoi)

    # B-01: CDSEClient with credentials from Settings
    settings = Settings()
    client = CDSEClient(
        client_id=settings.cdse_client_id,
        client_secret=settings.cdse_client_secret,
    )

    # B-02: search_stac with correct method name and kwargs
    start_dt = datetime.strptime(date_range[0], "%Y-%m-%d")
    end_dt = datetime.strptime(date_range[1], "%Y-%m-%d")
    items = client.search_stac(
        collection="SENTINEL-1",
        bbox=list(geom.bounds),
        start=start_dt,
        end=end_dt,
        product_type="IW_SLC__1S",
    )

    if not items:
        return CSLCResult(
            output_paths=[],
            runconfig_path=output_dir / "runconfig.yaml",
            burst_ids=[],
            valid=False,
            validation_errors=["No Sentinel-1 SLC scenes found for AOI/date range"],
        )

    # B-03: Burst query via frames module
    bursts = query_bursts_for_aoi(aoi_wkt=geom.wkt)
    burst_ids = [b.burst_id_jpl for b in bursts]

    if not bursts:
        return CSLCResult(
            output_paths=[],
            runconfig_path=output_dir / "runconfig.yaml",
            burst_ids=[],
            valid=False,
            validation_errors=["No EU bursts found for AOI"],
        )

    # B-05: fetch_dem with output_epsg from burst record, tuple unpack
    output_epsg = bursts[0].epsg
    dem_path, _dem_profile = fetch_dem(
        bounds=list(geom.bounds),
        output_epsg=output_epsg,
        output_dir=output_dir / "dem",
    )

    # B-04: fetch_orbit with named args from STAC item metadata
    scene = items[0]
    sensing_time = datetime.fromisoformat(
        scene.get("properties", {}).get("datetime", date_range[0]).rstrip("Z")
    )
    satellite = scene.get("properties", {}).get("platform", "S1A")
    orbit_path = fetch_orbit(
        sensing_time=sensing_time,
        satellite=satellite,
        output_dir=output_dir / "orbits",
    )

    # Download first scene
    s3_key = scene.get("assets", {}).get("data", {}).get("href", "")
    safe_path = output_dir / "input" / "scene_0.zip"
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    client.download(s3_key, safe_path)
    safe_paths = [safe_path]

    logger.info(
        "CSLC from AOI: {} scenes, {} bursts, EPSG:{}",
        len(safe_paths),
        len(burst_ids),
        output_epsg,
    )

    return run_cslc(
        safe_paths=safe_paths,
        orbit_path=orbit_path,
        dem_path=dem_path,
        burst_ids=burst_ids,
        output_dir=output_dir,
    )
