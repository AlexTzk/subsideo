"""RTC-S1 pipeline orchestrator.

Generates opera-rtc YAML runconfigs, invokes the opera-rtc Python API,
post-processes outputs to Cloud-Optimized GeoTIFF, and validates product
compliance (UTM CRS, 30 m posting, COG structure).

All imports of opera-rtc (``rtc``) and ``rio_cogeo`` are lazy — they are
conda-forge-only packages that may not be available in pure-pip environments.
"""
from __future__ import annotations

from pathlib import Path

from loguru import logger
from ruamel.yaml import YAML

from subsideo.products.types import RTCConfig, RTCResult

__all__ = [
    "RTCConfig",
    "RTCResult",
    "generate_rtc_runconfig",
    "ensure_cog",
    "validate_rtc_product",
    "run_rtc",
]


def generate_rtc_runconfig(cfg: RTCConfig, output_yaml: Path) -> Path:
    """Build and write an opera-rtc YAML runconfig from *cfg*.

    The resulting YAML matches the schema expected by
    ``rtc.runconfig.RunConfig.load_from_yaml``.

    Parameters
    ----------
    cfg:
        Populated :class:`RTCConfig` with all input paths resolved.
    output_yaml:
        Destination path for the YAML file.

    Returns
    -------
    Path
        *output_yaml* (for chaining convenience).
    """
    runconfig: dict = {
        "runconfig": {
            "name": "rtc_s1_workflow",
            "groups": {
                "primary_executable": {"product_type": "RTC_S1"},
                "input_file_group": {
                    "safe_file_path": [str(p) for p in cfg.safe_file_paths],
                    "orbit_file_path": [str(cfg.orbit_file_path)],
                    "burst_id": cfg.burst_id,
                },
                "dynamic_ancillary_file_group": {
                    "dem_file": str(cfg.dem_file),
                },
                "product_group": {
                    "product_path": str(cfg.output_dir),
                    "output_dir": str(cfg.output_dir),
                    "product_version": cfg.product_version,
                },
            },
        }
    }

    output_yaml.parent.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    yaml.default_flow_style = False
    with open(output_yaml, "w") as fh:
        yaml.dump(runconfig, fh)

    logger.debug("Wrote RTC runconfig to {}", output_yaml)
    return output_yaml


def ensure_cog(input_tif: Path, output_cog: Path | None = None) -> Path:
    """Convert a GeoTIFF to Cloud-Optimized GeoTIFF using DEFLATE compression.

    opera-rtc outputs plain GeoTIFF; this post-processing step ensures
    OPERA-spec COG compliance (overviews + internal tiling).

    Parameters
    ----------
    input_tif:
        Source GeoTIFF (not necessarily COG).
    output_cog:
        Destination COG path.  Defaults to ``<input_tif>.cog.tif``.

    Returns
    -------
    Path
        The COG file path.
    """
    from rio_cogeo.cogeo import cog_translate
    from rio_cogeo.profiles import cog_profiles

    output_cog = output_cog or input_tif.with_suffix(".cog.tif")
    profile = cog_profiles.get("deflate")
    cog_translate(
        str(input_tif),
        str(output_cog),
        profile,
        overview_level=5,
        overview_resampling="nearest",
        use_cog_driver=True,
    )
    logger.debug("COG-converted {} -> {}", input_tif, output_cog)
    return output_cog


def validate_rtc_product(cog_paths: list[Path]) -> list[str]:
    """Lightweight validation of RTC-S1 COG products.

    Checks each file for:
    1. Existence and readability
    2. Valid COG structure (via ``rio_cogeo.cog_validate``)
    3. UTM CRS (EPSG 326xx or 327xx)
    4. Approximate 30 m pixel size (25--35 m)

    Parameters
    ----------
    cog_paths:
        List of COG GeoTIFF paths to validate.

    Returns
    -------
    list[str]
        Error descriptions.  Empty list means all products are valid.
    """
    import rasterio
    from rio_cogeo.cog_validate import cog_validate

    errors: list[str] = []
    for p in cog_paths:
        if not p.exists():
            errors.append(f"{p}: file does not exist")
            continue

        # COG structure
        is_valid, _, _ = cog_validate(str(p))
        if not is_valid:
            errors.append(f"{p}: not a valid COG")

        # CRS and pixel size
        with rasterio.open(p) as ds:
            epsg = ds.crs.to_epsg() if ds.crs else None
            if epsg is None or not (32601 <= epsg <= 32660 or 32701 <= epsg <= 32760):
                errors.append(f"{p}: CRS is not UTM (EPSG={epsg})")
            pixel_x = abs(ds.transform.a)
            pixel_y = abs(ds.transform.e)
            avg_pixel = (pixel_x + pixel_y) / 2
            if not (25 <= avg_pixel <= 35):
                errors.append(
                    f"{p}: pixel size {avg_pixel:.1f} m outside 25-35 m range"
                )

    return errors


def run_rtc(
    safe_paths: list[Path],
    orbit_path: Path,
    dem_path: Path,
    burst_ids: list[str],
    output_dir: Path,
    product_version: str = "0.1.0",
) -> RTCResult:
    """Execute the full RTC-S1 pipeline.

    Steps:
    1. Build :class:`RTCConfig` from arguments
    2. Generate opera-rtc YAML runconfig
    3. Invoke ``rtc.runconfig.RunConfig.load_from_yaml`` + ``rtc.rtc_s1.run_parallel``
    4. Post-process outputs to COG
    5. Validate products

    Parameters
    ----------
    safe_paths:
        Paths to Sentinel-1 SAFE zip files.
    orbit_path:
        POE or RESORB orbit file.
    dem_path:
        GLO-30 DEM GeoTIFF.
    burst_ids:
        Target burst IDs (e.g. ``["T123-456789-IW2"]``).
    output_dir:
        Directory for pipeline outputs and intermediate files.
    product_version:
        OPERA product version string.

    Returns
    -------
    RTCResult
        Processing result with output paths and validation status.
    """
    cfg = RTCConfig(
        safe_file_paths=safe_paths,
        orbit_file_path=orbit_path,
        dem_file=dem_path,
        burst_id=burst_ids,
        output_dir=output_dir,
        product_version=product_version,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    runconfig_yaml = generate_rtc_runconfig(cfg, output_dir / "rtc_runconfig.yaml")

    try:
        from rtc.rtc_s1 import run_parallel
        from rtc.runconfig import RunConfig

        logger.info("Loading opera-rtc runconfig from {}", runconfig_yaml)
        opera_cfg = RunConfig.load_from_yaml(str(runconfig_yaml))

        logger.info("Running opera-rtc for bursts {}", burst_ids)
        run_parallel(opera_cfg, str(output_dir / "rtc.log"), True)

    except Exception:
        logger.exception("opera-rtc processing failed")
        return RTCResult(
            output_paths=[],
            runconfig_path=runconfig_yaml,
            burst_ids=burst_ids,
            valid=False,
            validation_errors=["opera-rtc processing failed"],
        )

    # Collect output GeoTIFFs and convert to COG
    output_tifs = sorted(output_dir.glob("*.tif"))
    cog_paths = [ensure_cog(p) for p in output_tifs]

    # Validate
    errors = validate_rtc_product(cog_paths)

    result = RTCResult(
        output_paths=cog_paths,
        runconfig_path=runconfig_yaml,
        burst_ids=burst_ids,
        valid=len(errors) == 0,
        validation_errors=errors,
    )

    if result.valid:
        logger.info("RTC pipeline completed successfully: {} COGs", len(cog_paths))
    else:
        logger.warning("RTC pipeline completed with validation errors: {}", errors)

    return result


def run_rtc_from_aoi(
    aoi: dict | Path,
    date_range: tuple[str, str],
    output_dir: Path,
) -> RTCResult:
    """End-to-end RTC-S1 pipeline from AOI and date range.

    Queries CDSE for Sentinel-1 SLC scenes, downloads orbit and DEM,
    resolves EU burst IDs, and runs :func:`run_rtc`.

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
    RTCResult
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
        return RTCResult(
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
        return RTCResult(
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
        return RTCResult(
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
        "RTC from AOI: {} scenes, {} bursts, EPSG:{}",
        len(safe_paths),
        len(burst_ids),
        output_epsg,
    )

    return run_rtc(
        safe_paths=safe_paths,
        orbit_path=orbit_path,
        dem_path=dem_path,
        burst_ids=burst_ids,
        output_dir=output_dir,
    )
