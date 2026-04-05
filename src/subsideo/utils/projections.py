"""UTM zone utilities using pyproj (handles Norway/Svalbard anomalies)."""
from __future__ import annotations

from pyproj.aoi import AreaOfInterest
from pyproj.database import query_utm_crs_info


def utm_epsg_from_lon(lon: float, lat: float = 45.0) -> int:
    """Return UTM EPSG code using pyproj (handles zone anomalies for Norway/Svalbard).

    Uses ``query_utm_crs_info`` rather than the naive ``int((lon + 180) / 6) + 1``
    formula, which fails for UTM zone anomalies in Norway (zone 32V) and
    Svalbard (zones 31X, 33X, 35X, 37X).

    Parameters
    ----------
    lon : float
        Longitude in degrees (WGS 84).
    lat : float
        Latitude in degrees (WGS 84). Default 45.0 (central EU).

    Returns
    -------
    int
        EPSG code, e.g. 32632 for UTM zone 32N.

    Raises
    ------
    ValueError
        If no UTM CRS is found for the given coordinates.
    """
    results = query_utm_crs_info(
        datum_name="WGS 84",
        area_of_interest=AreaOfInterest(
            west_lon_degree=lon,
            south_lat_degree=lat - 0.5,
            east_lon_degree=lon,
            north_lat_degree=lat + 0.5,
        ),
    )
    if not results:
        raise ValueError(f"No UTM CRS found for lon={lon}, lat={lat}")
    return int(results[0].code)
