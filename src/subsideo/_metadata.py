"""OPERA-compliant identification metadata injection for all product types.

Injects provenance, software version, and run parameters into both
GeoTIFF (via rasterio tags) and HDF5 (via /identification group attrs).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger


def get_software_version() -> str:
    """Get subsideo package version from installed metadata."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("subsideo")
    except PackageNotFoundError:
        return "dev"


def inject_opera_metadata(
    product_path: Path,
    product_type: str,
    software_version: str,
    run_params: dict,
) -> None:
    """Write OPERA-compliant identification metadata into *product_path*.

    Supports GeoTIFF (.tif/.tiff) and HDF5 (.h5/.hdf5/.he5) formats.
    Unknown extensions are silently skipped with a warning.

    Parameters
    ----------
    product_path:
        Path to the product file.
    product_type:
        OPERA product type string (e.g. ``"RTC-S1"``, ``"DSWx-S2"``).
    software_version:
        Software version string.
    run_params:
        Arbitrary run parameters dict (serialised as JSON).
    """
    suffix = product_path.suffix.lower()
    metadata = {
        "PRODUCT_TYPE": product_type,
        "SOFTWARE_VERSION": software_version,
        "SOFTWARE_NAME": "subsideo",
        "PRODUCTION_DATETIME": datetime.now(timezone.utc).isoformat(),
        "RUN_PARAMETERS": json.dumps(run_params),
    }
    if suffix in (".tif", ".tiff"):
        _inject_geotiff(product_path, metadata)
    elif suffix in (".h5", ".hdf5", ".he5"):
        _inject_hdf5(product_path, metadata)
    else:
        logger.warning("Unknown product format {}, skipping metadata injection", suffix)


def _inject_geotiff(path: Path, metadata: dict[str, str]) -> None:
    """Write metadata as GeoTIFF tags."""
    import rasterio

    with rasterio.open(path, "r+") as ds:
        ds.update_tags(**metadata)
    logger.debug("Injected OPERA metadata into GeoTIFF {}", path)


def _inject_hdf5(path: Path, metadata: dict[str, str]) -> None:
    """Write metadata as HDF5 /identification group attributes."""
    import h5py

    with h5py.File(path, "a") as f:
        grp = f.require_group("/identification")
        for key, value in metadata.items():
            grp.attrs[key] = value
    logger.debug("Injected OPERA metadata into HDF5 {}", path)
