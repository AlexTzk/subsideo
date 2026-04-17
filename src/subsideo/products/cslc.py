"""CSLC-S1 pipeline orchestrator.

Generates compass YAML runconfigs, invokes the compass Python API
(compass.s1_cslc.run), and validates HDF5 output compliance against
the OPERA CSLC-S1 product specification.

Compatibility notes (2026-04-11):
    compass 0.5.6 / s1reader 0.2.5 / isce3 0.25.8 have multiple
    incompatibilities with numpy >= 2.0.  Four monkey-patches are applied
    before compass invocation — see ``_patch_compass_burst_db_none_guard``,
    ``_patch_s1reader_numpy2_compat``, ``_patch_burst_az_carrier_poly``,
    and the ``np.string_ = np.bytes_`` shim in ``run_cslc()``.
    These can be removed once upstream releases fix the issues.
    Full details in .planning/research/PITFALLS.md (Pitfalls 13-16)
    and CONCLUSIONS_CSLC_N_AM.md.
"""
from __future__ import annotations

import re
from pathlib import Path

from loguru import logger
import yaml

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
    # Only include optional string fields when they have a non-None value —
    # yamale str(required=False) accepts an absent key but rejects a null value.
    dynamic_ancillary: dict = {"dem_file": str(cfg.dem_file.resolve())}
    if cfg.tec_file is not None:
        dynamic_ancillary["tec_file"] = str(cfg.tec_file.resolve())

    runconfig = {
        "runconfig": {
            "name": "cslc_s1_workflow",
            "groups": {
                "pge_name_group": {
                    "pge_name": "CSLC_S1_PGE",
                },
                "input_file_group": {
                    "safe_file_path": [str(p.resolve()) for p in cfg.safe_file_paths],
                    "orbit_file_path": [str(cfg.orbit_file_path.resolve())],
                    "burst_id": cfg.burst_id,
                },
                "dynamic_ancillary_file_group": dynamic_ancillary,
                "static_ancillary_file_group": {
                    **({"burst_database_file": str(cfg.burst_database_file.resolve())}
                       if cfg.burst_database_file is not None else {}),
                },
                "product_path_group": {
                    "product_path": str(cfg.output_dir.resolve()),
                    "scratch_path": str((cfg.output_dir / "scratch").resolve()),
                    "sas_output_file": str(cfg.output_dir.resolve()),
                    "product_version": cfg.product_version,
                },
                "primary_executable": {
                    "product_type": "CSLC_S1",
                },
                "processing": {
                    "geocoding": {
                        # OPERA spec: 5m range x 10m azimuth posting
                        "x_posting": 5.0,
                        "y_posting": 10.0,
                        # Snap grid origin to multiples of posting so pixel
                        # centers fall on the same grid as OPERA products
                        "x_snap": 5.0,
                        "y_snap": 10.0,
                    },
                },
            },
        }
    }

    output_yaml.parent.mkdir(parents=True, exist_ok=True)
    with open(output_yaml, "w") as fh:
        yaml.dump(runconfig, fh, default_flow_style=False, sort_keys=False)

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
                # Check for data in either compass or OPERA layout
                has_data = "data" in f
                opera_grids = "science/SENTINEL1/CSLC/grids"
                has_opera = opera_grids in f

                if not has_data and not has_opera:
                    errors.append(f"{prefix}: missing /data and /science groups")
                    continue

                if has_data and len(f["data"]) == 0:
                    errors.append(f"{prefix}: /data group is empty (no datasets)")
                elif has_opera and len(f[opera_grids]) == 0:
                    errors.append(f"{prefix}: /science/.../grids group is empty")

                # Check metadata or identification group
                if "metadata" not in f and "identification" not in f:
                    errors.append(
                        f"{prefix}: missing /metadata and /identification groups"
                    )
        except Exception as exc:
            errors.append(f"{prefix}: failed to open HDF5 — {exc}")

    return errors


def _patch_compass_burst_db_none_guard():
    """Monkey-patch compass to tolerate burst_database_file=None.

    compass.utils.geo_runconfig.GeoRunConfig.load_from_yaml has a bug:
    it calls os.path.isfile(burst_database_file) and raises FileNotFoundError
    *before* checking ``if burst_database_file is None`` (which would use
    generate_geogrids without a DB).  We patch os.path.isfile within the
    module to return False for None, and suppress the subsequent
    FileNotFoundError so the None code-path is reached.
    """
    import compass.utils.geo_runconfig as _geocfg

    if getattr(_geocfg, '_subsideo_patched', False):
        return

    _orig_load = _geocfg.GeoRunConfig.load_from_yaml.__func__

    @classmethod
    def _patched_load(cls, yaml_runconfig, workflow_name):
        from compass.utils.runconfig import load_validate_yaml
        from compass.utils.geo_grid import generate_geogrids, generate_geogrids_from_db
        from compass.utils.runconfig import create_output_paths, runconfig_to_bursts
        from compass.utils.wrap_namespace import wrap_namespace
        import yaml as _yaml

        cfg = load_validate_yaml(yaml_runconfig, workflow_name)
        groups_cfg = cfg['runconfig']['groups']

        burst_database_file = groups_cfg['static_ancillary_file_group']['burst_database_file']

        # --- patched: skip isfile check when None ---
        if burst_database_file is not None:
            if not _geocfg.os.path.isfile(burst_database_file):
                raise FileNotFoundError(f'{burst_database_file} not found')

        geocoding_dict = groups_cfg['processing']['geocoding']
        _geocfg.check_geocode_dict(geocoding_dict)

        tec_file_path = groups_cfg['dynamic_ancillary_file_group']['tec_file']
        if tec_file_path is not None:
            from compass.utils.helpers import check_file_path
            check_file_path(tec_file_path)

        weather_model_path = groups_cfg['dynamic_ancillary_file_group']['weather_model_file']
        if weather_model_path is not None:
            from compass.utils.helpers import check_file_path
            check_file_path(weather_model_path)

        sns = wrap_namespace(groups_cfg)
        bursts = runconfig_to_bursts(sns)

        dem_file = groups_cfg['dynamic_ancillary_file_group']['dem_file']
        if burst_database_file is None:
            geogrids = generate_geogrids(bursts, geocoding_dict, dem_file)
        else:
            geogrids = generate_geogrids_from_db(
                bursts, geocoding_dict, dem_file, burst_database_file
            )

        empty_ref_dict = {}
        user_plus_default_yaml_str = _yaml.dump(cfg)
        output_paths = create_output_paths(sns, bursts)

        return cls(cfg['runconfig']['name'], sns, bursts, empty_ref_dict,
                   user_plus_default_yaml_str, output_paths, geogrids)

    _geocfg.GeoRunConfig.load_from_yaml = _patched_load
    _geocfg._subsideo_patched = True


def _patch_s1reader_numpy2_compat():
    """Monkey-patch s1reader.s1_burst_slc.polyfit for numpy 2.x.

    s1reader 0.2.5 uses ``%f`` string formatting on the residual array
    returned by np.linalg.lstsq, which numpy >= 2.0 rejects with
    ``TypeError: only 0-dimensional arrays can be converted to Python
    scalars``.  We replace the polyfit function with a version that
    calls ``.item()`` on the residual before formatting.
    """
    import s1reader.s1_burst_slc as _burst_mod

    if getattr(_burst_mod, '_subsideo_numpy2_patched', False):
        return

    import numpy as np

    # Re-implement polyfit with the single-line fix at the print statement.
    # This is a copy of s1reader.s1_burst_slc.polyfit with line 97 fixed.
    def _polyfit_fixed(x, y, z, azimuth_order, range_order,
                       sig=None, snr=None, cond=1.0e-12, max_order=False):
        big_order = max(azimuth_order, range_order)
        arr_list = []
        for ii in range(azimuth_order + 1):
            for jj in range(range_order + 1):
                xfact = np.power(x, ii) * np.power(y, jj)
                if max_order:
                    if (ii + jj) <= big_order:
                        arr_list.append(xfact.reshape((x.size, 1)))
                else:
                    arr_list.append(xfact.reshape((x.size, 1)))

        A = np.hstack(arr_list)
        if sig is not None and snr is not None:
            raise Exception("Only one of sig / snr can be provided")
        if sig is not None:
            snr = 1.0 + 1.0 / sig
        if snr is not None:
            A = A / snr[:, None]
            z = z / snr

        val, res, _, _ = np.linalg.lstsq(A, z, rcond=cond)
        if len(res) > 0:
            chi_sq = float(np.sqrt(res / (1.0 * len(z))).item())
            print("Chi squared: %f" % chi_sq)
        else:
            print("No chi squared value....")
            print("Try reducing rank of polynomial.")

        coeffs = []
        count = 0
        for ii in range(azimuth_order + 1):
            row = []
            for jj in range(range_order + 1):
                if max_order:
                    if (ii + jj) <= big_order:
                        row.append(val[count])
                        count += 1
                    else:
                        row.append(0.0)
                else:
                    row.append(val[count])
                    count += 1
            coeffs.append(row)

        return coeffs

    _burst_mod.polyfit = _polyfit_fixed
    _burst_mod._subsideo_numpy2_patched = True


def _patch_burst_az_carrier_poly():
    """Patch s1reader burst's get_az_carrier_poly to return isce3.core.Poly2d.

    With numpy 2.x, pybind11 can no longer auto-convert list-of-lists to
    isce3.core.Poly2d.  Wrap the return value explicitly.
    """
    import s1reader.s1_burst_slc as _burst_mod

    if getattr(_burst_mod, '_subsideo_poly2d_patched', False):
        return

    _orig_method = _burst_mod.Sentinel1BurstSlc.get_az_carrier_poly

    def _patched_get_az_carrier_poly(self, *args, **kwargs):
        import numpy as np
        import isce3
        result = _orig_method(self, *args, **kwargs)
        if isinstance(result, list):
            return isce3.core.Poly2d(np.array(result, dtype=np.float64))
        return result

    _burst_mod.Sentinel1BurstSlc.get_az_carrier_poly = _patched_get_az_carrier_poly
    _burst_mod._subsideo_poly2d_patched = True


def run_cslc(
    safe_paths: list[Path],
    orbit_path: Path,
    dem_path: Path,
    burst_ids: list[str] | None,
    output_dir: Path,
    tec_file: Path | None = None,
    burst_database_file: Path | None = None,
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
    burst_database_file:
        Optional SQLite burst database with burst_id_map table
        (columns: burst_id_jpl, epsg, xmin, ymin, xmax, ymax).
        Required for correct geogrid computation — without it,
        compass may compute incorrect output grid dimensions.
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
        burst_database_file=burst_database_file,
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

        # Workaround for compass bug: GeoRunConfig.load_from_yaml calls
        # os.path.isfile(burst_database_file) unconditionally, then raises
        # FileNotFoundError — before the None check at line 101 that would
        # use generate_geogrids() without a DB.  Monkey-patch load_from_yaml
        # to skip the burst DB file check when it is None.
        _patch_compass_burst_db_none_guard()

        # Workaround for s1reader numpy 2.x incompatibility: polyfit uses
        # ``%f`` formatting on a numpy array (res from lstsq), which numpy
        # 2.0+ rejects.  Patch the print to use .item().
        _patch_s1reader_numpy2_compat()

        # Workaround for numpy 2.x: np.string_ was removed, use np.bytes_
        import numpy as _np
        if not hasattr(_np, 'string_'):
            _np.string_ = _np.bytes_

        # Workaround for numpy 2.x / isce3 pybind11 incompatibility:
        # burst.get_az_carrier_poly() returns a list-of-lists that pybind11
        # can no longer auto-convert to Poly2d.  Patch it to return Poly2d.
        _patch_burst_az_carrier_poly()

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

    # Collect output HDF5 files (compass writes into subdirectories)
    h5_paths = sorted(output_dir.glob("**/*.h5"))
    logger.info("Found {} CSLC HDF5 outputs", len(h5_paths))

    # Validate products
    errors = validate_cslc_product(h5_paths)

    # OUT-03: Inject OPERA metadata
    from subsideo._metadata import get_software_version, inject_opera_metadata

    sw_version = get_software_version()
    for h5_path in h5_paths:
        if h5_path.exists():
            inject_opera_metadata(
                h5_path,
                product_type="CSLC-S1",
                software_version=sw_version,
                run_params={
                    "safe_paths": [str(p) for p in safe_paths],
                    "orbit_path": str(orbit_path),
                    "dem_path": str(dem_path),
                    "burst_ids": burst_ids or [],
                    "tec_file": str(tec_file) if tec_file else None,
                    "output_dir": str(output_dir),
                },
            )

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

    # DATA-05: Fetch IONEX TEC map (optional)
    tec_file = None
    try:
        from subsideo.data.ionosphere import fetch_ionex

        tec_file = fetch_ionex(
            date=sensing_time.date(),
            output_dir=output_dir / "ionex",
            username=settings.earthdata_username,
            password=settings.earthdata_password,
        )
    except Exception:
        logger.warning("IONEX download failed; proceeding without ionospheric correction")

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
        tec_file=tec_file,
    )
