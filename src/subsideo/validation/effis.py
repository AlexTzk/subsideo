"""EFFIS REST API access + perimeter rasterisation for Phase 5 DIST-S1 EU validation.

DIST-05 + DIST-06 + CONTEXT D-17/D-18/D-19 implementation. Two public
functions:

* :func:`fetch_effis_perimeters` -- REST API query for burnt-area perimeters
  filtered by country + date range; returns ``(gdf, EFFISQueryMeta)``. Caches
  the GeoJSON response under
  ``<cache_dir>/<event_id>/effis_perimeters/perimeters.geojson``
  for warm re-run determinism (CONTEXT D-19).

  **REST pivot (Phase 5 scope amendment 2026-04-25):** Both WFS candidate
  endpoints failed during Plan 05-02 probing (Candidate A: GetCapabilities
  ReadTimeout; Candidate B: DNS NXDOMAIN). The REST API at
  ``https://api.effis.emergency.copernicus.eu/rest/2/burntareas/current/``
  is adopted as the primary access path (lock file: eval-dist_eu/effis_endpoint_lock.txt).
  Per the D-18 amendment in ROADMAP Phase 5 scope-amendment block, network
  access uses ``requests`` directly with a retry-mounted session driven by
  ``harness.RETRY_POLICY['EFFIS']`` -- the harness owns the policy declaration;
  this module owns the dispatch entry point.

  Note: The ``intersects`` geometry filter returns HTTP 403 (WAF-blocked), so
  the REST query uses country + date range parameters, then post-filters
  spatially in code (bounding-box intersection with geopandas).

* :func:`rasterise_perimeters_to_grid` -- dual rasterise per CONTEXT D-17:
  ``all_touched=False`` (primary; gate value; centre-of-pixel inside polygon)
  AND ``all_touched=True`` (diagnostic; +2-4pp F1 inflation per PITFALLS P4.4).
  Returns ``(mask_at_false, mask_at_true)`` -- both uint8 -- for downstream
  ``RasterisationDiagnostic`` population.

Module-level constants
----------------------
The REST endpoint configuration is locked in ``eval-dist_eu/effis_endpoint_lock.txt``
by Plan 05-02. The constants below are copied verbatim from the lock file's
"Downstream constants" block. To change the endpoint, re-run Plan 05-02
(which re-probes and re-locks); do NOT edit these constants directly.

For backward compatibility with Plan 05-05 must_have.truths, the WFS-style
constant names (``EFFIS_WFS_URL``, ``EFFIS_LAYER_NAME``, ``EFFIS_FILTER_NAMESPACE``)
are exported with values derived from the REST probe:

* ``EFFIS_WFS_URL`` is set to the REST URL (the chosen endpoint after WFS failures).
* ``EFFIS_LAYER_NAME`` is ``"burntareas/current"`` (the REST resource path).
* ``EFFIS_FILTER_NAMESPACE`` is ``"drf"`` (Django REST Framework query params).

Lazy-import discipline (Phase 1 pattern)
----------------------------------------
``geopandas``, ``rasterio.features``, and ``json``/``io`` helpers are lazy-imported
inside function bodies so that ``from subsideo.validation import *`` does not pay
the geopandas + GDAL import cost when the consumer only uses non-EFFIS helpers.
``numpy``, ``requests``, ``loguru.logger``, and ``subsideo.validation.harness``
are at module top (always needed for the retry adapter + logging).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import requests
from loguru import logger

from subsideo.validation.harness import (
    RETRY_POLICY,
    ReferenceDownloadError,
)

# --- Endpoint lock (copied verbatim from eval-dist_eu/effis_endpoint_lock.txt
#     Plan 05-02 output; see "Downstream constants" block of that file).
#
# WFS candidates both failed (Candidate A: ReadTimeout; Candidate B: DNS NXDOMAIN).
# REST API adopted as primary. The constant names below mirror the Plan 05-05
# must_have.truths interface contract; values reflect the REST probe outcome.
EFFIS_REST_URL: str = "https://api.effis.emergency.copernicus.eu/rest/2/burntareas/current/"
EFFIS_DATE_PROPERTY: str = "firedate"           # canonical date field name (REST API)
EFFIS_DATE_GTE_PARAM: str = "firedate__gte"     # DRF QueryParam for date lower bound
EFFIS_DATE_LTE_PARAM: str = "firedate__lte"     # DRF QueryParam for date upper bound
EFFIS_COUNTRY_PARAM: str = "country"            # DRF QueryParam for ISO-3166 country
EFFIS_COUNTRY_PT: str = "PT"                    # Portugal
EFFIS_COUNTRY_EL: str = "EL"                    # Greece (NOT "GR" -- confirmed by REST probe)
EFFIS_COUNTRY_ES: str = "ES"                    # Spain
EFFIS_ORDERING_PARAM: str = "ordering"          # DRF QueryParam for result ordering

# Backward-compat aliases matching Plan 05-05 must_have.truths interface contract.
# Consumers that import these four names will get working REST-backed values.
EFFIS_WFS_URL: str = EFFIS_REST_URL             # REST URL is the chosen endpoint post-WFS-failure
EFFIS_LAYER_NAME: str = "burntareas/current"    # REST resource path (was: WFS typename)
EFFIS_FILTER_NAMESPACE: str = "drf"             # DRF QueryParam namespace (was: fes2/fes1)


class EFFISLockMissingError(RuntimeError):
    """Raised when EFFIS_REST_URL is unset (lock file absent or candidate_chosen=neither)."""


def _validate_lock() -> None:
    """Fail-fast guard: ensure endpoint constants are populated.

    Called by both public functions before any network or raster operation.
    """
    if EFFIS_REST_URL.startswith("<paste") or not EFFIS_REST_URL.startswith("https://"):
        raise EFFISLockMissingError(
            "EFFIS endpoint constants are unset; re-run Plan 05-02 to populate "
            "eval-dist_eu/effis_endpoint_lock.txt and update src/subsideo/validation/effis.py."
        )


def _build_retry_session() -> requests.Session:
    """Return a ``requests.Session`` mounted with a urllib3 Retry adapter
    keyed on ``RETRY_POLICY['EFFIS']`` per the D-18 amendment.

    The harness still owns the policy declaration; this function projects it
    onto urllib3 + requests primitives for the REST-API dispatch path.

    Maps numeric entries in ``retry_on`` to urllib3's ``status_forcelist``
    (429, 503, 504). String entries ('ConnectionError', 'TimeoutError')
    are handled by urllib3's default behaviour for non-idempotent GET retries.
    The ``abort_on`` list (401, 403, 404) is NOT passed to urllib3 --
    ``raise_on_status=False`` keeps the session from swallowing them; instead
    the caller checks the response status against ``abort_on`` and raises
    ``ReferenceDownloadError`` explicitly, mirroring harness semantics.
    """
    from urllib3.util.retry import Retry

    policy = RETRY_POLICY["EFFIS"]
    status_forcelist = [s for s in policy["retry_on"] if isinstance(s, int)]
    retry = Retry(
        total=5,
        backoff_factor=2,       # 2s, 4s, 8s, 16s, 32s (cap 60s via harness convention)
        status_forcelist=status_forcelist,
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,  # we check abort_on manually post-response
    )
    sess = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=retry)
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    # Stash abort_on so the caller can post-check (urllib3 doesn't raise on those).
    sess._effis_abort_on = policy.get("abort_on", [401, 403, 404])  # type: ignore[attr-defined]
    return sess


def _country_for_bbox(
    bbox_wgs84: tuple[float, float, float, float],
) -> str | None:
    """Heuristic: return the EFFIS country code for a bbox centre (WGS84).

    Used when the caller does not supply an explicit country parameter.
    Falls back to None (caller must supply it or accept unfiltered results).
    """
    west, south, east, north = bbox_wgs84
    lon = (west + east) / 2.0
    lat = (south + north) / 2.0
    # Simple centroid heuristics for the three locked events
    if 20.0 <= lon <= 30.0 and 39.0 <= lat <= 44.0:
        return EFFIS_COUNTRY_EL   # Greece (Evros)
    if -10.0 <= lon <= -6.0 and 39.0 <= lat <= 42.0:
        return EFFIS_COUNTRY_PT   # Portugal (Aveiro)
    if -10.0 <= lon <= 5.0 and 35.0 <= lat <= 45.0:
        return EFFIS_COUNTRY_ES   # Spain (Culebra / Zamora)
    return None


def fetch_effis_perimeters(
    event_id: str,
    bbox_wgs84: tuple[float, float, float, float],
    date_start: date,
    date_end: date,
    cache_dir: Path,
    *,
    country: str | None = None,
) -> tuple[object, object]:  # (gpd.GeoDataFrame, EFFISQueryMeta)
    """Fetch EFFIS burnt-area perimeters for a country + date range, cache to disk.

    Uses the EFFIS REST API (https://api.effis.emergency.copernicus.eu/rest/)
    with a retry-mounted ``requests.Session`` driven by ``RETRY_POLICY['EFFIS']``
    (D-18 amendment in ROADMAP Phase 5 scope-amendment block).

    The ``intersects`` geometry filter is WAF-blocked (HTTP 403), so this
    function queries by country + date range, then post-filters the response
    by bounding-box intersection in geopandas.

    Parameters
    ----------
    event_id : str
        Identifier used in cache path; must be one of the
        ``DistEUEventID`` Literal values (aveiro / evros / spain_culebra).
    bbox_wgs84 : tuple[float, float, float, float]
        ``(west, south, east, north)`` in EPSG:4326 degrees. Used for
        post-filter spatial intersection.
    date_start, date_end : date
        Inclusive date range for the ``firedate`` property filter.
        Passed as ISO-8601 strings to the REST API.
    cache_dir : Path
        Top-level cache directory (e.g., ``Path("eval-dist_eu")``). The
        response is cached at
        ``cache_dir/event_id/effis_perimeters/perimeters.geojson``.
    country : str | None, keyword-only, default None
        ISO-3166 two-letter country code in EFFIS encoding (e.g. ``"EL"``
        for Greece, NOT ``"GR"``). When None, auto-derived from ``bbox_wgs84``
        centroid heuristics. If derivation also fails, the query runs without
        a country filter (may return many features; spatial post-filter applies).

    Returns
    -------
    tuple[gpd.GeoDataFrame, EFFISQueryMeta]
        The GeoDataFrame in EPSG:4326 + the per-event query metadata for
        meta.json reproducibility audit (CONTEXT D-19).

    Raises
    ------
    EFFISLockMissingError
        If module-level endpoint constants are unset.
    ReferenceDownloadError
        Raised when the REST response status appears in
        ``RETRY_POLICY['EFFIS']['abort_on']`` (401 / 403 / 404). Mirrors
        the abort semantics declared in harness.RETRY_POLICY; the Path-returning
        download helper is NOT called (D-18 amendment: incompatible contract).
    requests.RequestException
        On transport-level failures after retries are exhausted.
    """
    _validate_lock()

    import io
    import json as _json

    import geopandas as gpd
    from shapely.geometry import box as shapely_box

    from subsideo.validation.matrix_schema import EFFISQueryMeta

    cache_path = cache_dir / event_id / "effis_perimeters" / "perimeters.geojson"
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Resolve country code
    resolved_country = country or _country_for_bbox(bbox_wgs84)

    # Build query parameters (DRF filter params per lock file)
    params: dict[str, str] = {
        EFFIS_DATE_GTE_PARAM: f"{date_start.isoformat()}T00:00:00Z",
        EFFIS_DATE_LTE_PARAM: f"{date_end.isoformat()}T23:59:59Z",
        EFFIS_ORDERING_PARAM: f"-{EFFIS_DATE_PROPERTY}",  # descending by date
    }
    if resolved_country:
        params[EFFIS_COUNTRY_PARAM] = resolved_country

    filter_string = str(params)  # lightweight audit trace for EFFISQueryMeta

    # Cache hit short-circuits (CONTEXT D-19 warm re-run path)
    if cache_path.exists() and cache_path.stat().st_size > 0:
        logger.info("EFFIS cache hit for {} at {}", event_id, cache_path)
        gdf = gpd.read_file(cache_path)
        meta = EFFISQueryMeta(
            wfs_endpoint=EFFIS_REST_URL,
            layer_name=EFFIS_LAYER_NAME,
            filter_string=filter_string,
            response_feature_count=len(gdf),
            fetched_at=(
                datetime.fromtimestamp(cache_path.stat().st_mtime, tz=timezone.utc)
                .isoformat()
            ),
        )
        return gdf, meta

    # Cache miss -- live REST fetch with RETRY_POLICY['EFFIS']-driven retries
    logger.info(
        "EFFIS REST fetch for {} country={} dates=[{}..{}]",
        event_id,
        resolved_country or "all",
        date_start,
        date_end,
    )
    session = _build_retry_session()
    abort_on: list[int] = getattr(session, "_effis_abort_on", [401, 403, 404])

    # Paginate through all pages (DRF default page_size varies; use next link)
    features: list[dict[str, object]] = []
    next_url: str | None = EFFIS_REST_URL
    page_params: dict[str, str] | None = dict(params)  # first request carries params

    while next_url is not None:
        resp = session.get(
            next_url,
            params=page_params,
            timeout=60,
            headers={"Accept": "application/json"},
        )
        page_params = None  # subsequent pages use the full next URL (params embedded)

        if resp.status_code in abort_on:
            raise ReferenceDownloadError("EFFIS", resp.status_code, next_url)

        resp.raise_for_status()
        data = resp.json()

        # DRF GeoJSON responses carry results in a "features" list (GeoJSON FeatureCollection)
        # or in a "results" list (DRF paginated generic serialiser).
        if "features" in data:
            features.extend(data["features"])
            next_url = data.get("next")  # GeoJSON + pagination extension
        elif "results" in data:
            features.extend(data["results"])
            next_url = data.get("next")
        else:
            # Single-page or non-paginated GeoJSON FeatureCollection
            features.extend(data if isinstance(data, list) else [data])
            next_url = None

        logger.debug("EFFIS page: {} features so far", len(features))

    logger.info(
        "EFFIS REST fetched {} total features for event_id={}", len(features), event_id
    )

    # Build GeoDataFrame from raw REST features
    if features:
        first = features[0]
        # Each feature may be a GeoJSON Feature dict (with .geometry) or a plain dict.
        # Build a GeoDataFrame from the feature collection.
        if isinstance(first, dict) and "geometry" in first:
            raw_features = features
        else:
            raw_features = [
                {
                    "type": "Feature",
                    # ME-01 fix: read geometry from the loop variable `f`, not
                    # from `first` (the captured first element). Previously
                    # every feature in the output carried the first feature's
                    # geometry, collapsing all post-filter perimeters to a
                    # single shape in the non-GeoJSON branch.
                    "geometry": (
                        f.get("shape") or f.get("centroid")  # type: ignore[union-attr]
                        if isinstance(f, dict) else None
                    ),
                    "properties": {
                        k: v
                        for k, v in (f.items() if isinstance(f, dict) else {}.items())
                        if k not in ("shape", "centroid")
                    },
                }
                for f in features
            ]
        fc = {"type": "FeatureCollection", "features": raw_features}
        gdf = gpd.read_file(io.StringIO(_json.dumps(fc)))
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")
    else:
        # Empty result: return empty GeoDataFrame with correct schema
        gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries([], crs="EPSG:4326"))

    # Spatial post-filter: bbox intersection (intersects filter is WAF-blocked)
    west, south, east, north = bbox_wgs84
    if len(gdf) > 0:
        aoi_box = shapely_box(west, south, east, north)
        mask = gdf.geometry.intersects(aoi_box)
        gdf = gdf[mask].reset_index(drop=True)
        logger.info(
            "EFFIS spatial post-filter: {} features intersect bbox",
            len(gdf),
        )

    # Persist for warm re-runs
    gdf.to_file(cache_path, driver="GeoJSON")

    meta = EFFISQueryMeta(
        wfs_endpoint=EFFIS_REST_URL,
        layer_name=EFFIS_LAYER_NAME,
        filter_string=filter_string,
        response_feature_count=len(gdf),
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )
    return gdf, meta


def rasterise_perimeters_to_grid(
    gdf: object,       # gpd.GeoDataFrame in target CRS already
    out_shape: tuple[int, int],
    transform: object,  # rasterio.Affine
) -> tuple[np.ndarray, np.ndarray]:
    """Dual-rasterise EFFIS perimeters to subsideo's 30 m DIST grid (CONTEXT D-17).

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        Perimeters in the SAME CRS as ``transform`` (caller reprojects to UTM
        before calling). Empty gdf raises ValueError.
    out_shape : tuple[int, int]
        ``(height, width)`` of the target raster in pixels.
    transform : rasterio.Affine
        Affine transform for the target raster.

    Returns
    -------
    mask_at_false : np.ndarray (uint8, shape out_shape)
        ``rasterio.features.rasterize(all_touched=False)`` -- only pixels
        whose centre falls inside a polygon. PRIMARY (gate value) per
        CONTEXT D-17; F1 against this mask is the dist:eu cell metric.
    mask_at_true : np.ndarray (uint8, shape out_shape)
        ``rasterio.features.rasterize(all_touched=True)`` -- pixels touched
        by polygon boundary. DIAGNOSTIC ONLY per CONTEXT D-17; expected
        ~+2-4pp F1 inflation per PITFALLS P4.4.

    Raises
    ------
    EFFISLockMissingError
        If endpoint constants are unset (should never fire after module import,
        but guards against partial-initialisation edge cases).
    ValueError
        If ``gdf`` is empty (no perimeters to rasterise) -- caller is
        responsible for handling zero-feature events.
    """
    _validate_lock()
    if len(gdf) == 0:  # type: ignore[arg-type]
        raise ValueError(
            "Cannot rasterise empty GeoDataFrame -- no EFFIS perimeters to project. "
            "Caller should record zero-feature event in metrics.json and skip."
        )

    from rasterio.enums import MergeAlg
    from rasterio.features import rasterize

    shapes = [(geom, 1) for geom in gdf.geometry]  # type: ignore[union-attr]

    mask_at_false: np.ndarray = rasterize(
        shapes=shapes,
        out_shape=out_shape,
        transform=transform,
        fill=0,
        dtype="uint8",
        all_touched=False,      # CONTEXT D-17 primary: centre-of-pixel
        merge_alg=MergeAlg.replace,
    )
    mask_at_true: np.ndarray = rasterize(
        shapes=shapes,
        out_shape=out_shape,
        transform=transform,
        fill=0,
        dtype="uint8",
        all_touched=True,       # CONTEXT D-17 diagnostic: boundary-touched
        merge_alg=MergeAlg.replace,
    )
    return mask_at_false, mask_at_true
