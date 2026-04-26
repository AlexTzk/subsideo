"""Validation harness: shared plumbing consumed by every run_eval_*.py script.

Public helpers (ENV-06 / Research §F):

* :func:`select_opera_frame_by_utc_hour` — pick the OPERA frame whose sensing
  UTC hour matches a query datetime (REL-03 methodology).
* :func:`download_reference_with_retry` — per-source-aware HTTPS/S3 download
  with retry + abort semantics (PITFALLS P0.4 mitigation).
* :func:`ensure_resume_safe` — verify prior partial cache state before
  resuming; never raises on missing cache (returns bool).
* :func:`credential_preflight` — fail-fast env-var check; raises SystemExit
  with a listed-names message (replaces ad-hoc ``if not os.environ.get(...)``
  blocks scattered across eval scripts).
* :func:`bounds_for_burst` — wrap ``opera_utils.burst_frame_db`` primary path
  with a ``subsideo.burst.db.query_bounds`` EU fallback (ENV-08).
* :func:`bounds_for_mgrs_tile` — wrap ``opera_utils`` MGRS helpers (when
  available) with a seed-GeoJSON fallback shipped in
  ``src/subsideo/validation/_mgrs_tiles.geojson`` (ENV-08 Plan 01-07 DSWx
  consumer).

Per-source :data:`RETRY_POLICY` dict — Earthdata 401 must NOT retry
forever (PITFALLS P0.4); CloudFront 403 surfaces as an abort so the caller
can refresh the signed URL.

Design constraint: this module MUST NOT import from ``subsideo.products.*`` —
it is a peer of ``validation/compare_*.py`` (ARCHITECTURE §Failure-Mode
Boundaries). Conda-forge-only libraries (rasterio, isce3, dolphin) are
imported inside function bodies when needed.
"""
from __future__ import annotations

import json
import os
import time
from collections.abc import Sequence
from datetime import datetime
from importlib.resources import files as _pkg_files
from pathlib import Path
from typing import Any, Literal

import requests  # type: ignore[import-untyped]
from loguru import logger

# ----------------------------------------------------------------------------
# Retry policy (PITFALLS P0.4)
# ----------------------------------------------------------------------------

RetrySource = Literal["CDSE", "EARTHDATA", "CLOUDFRONT", "HTTPS", "EFFIS", "jrc"]

RETRY_POLICY: dict[str, dict[str, Any]] = {
    "CDSE": {
        "retry_on": [429, 503, "OutOfMemoryError"],
        "abort_on": [401, 403, 404],
    },
    "EARTHDATA": {
        "retry_on": [429, 503],
        "abort_on": [401, 403, 404],
    },
    "CLOUDFRONT": {
        "retry_on": [503, "ExpiredToken"],
        "abort_on": [401, 404],
        # 403 on a signed CloudFront URL means the signature expired; the
        # caller must obtain a fresh URL (not auto-retry with stale one).
        "refresh_url_on": [403],
    },
    "HTTPS": {
        "retry_on": [429, 503],
        "abort_on": [401, 403, 404],
    },
    "EFFIS": {
        # Phase 5 DIST-05 EFFIS WFS access. Public endpoint (no auth) but
        # owslib raises ConnectionError / TimeoutError from urllib3 rather
        # than HTTP status codes for transport-layer failures, so both kinds
        # appear in retry_on. 504 is added because EFFIS MapServer responses
        # can take 30+s for large bbox + date-window queries (RESEARCH Probe
        # 3 Risk F). The abort_on triplet 401/403/404 mirrors EARTHDATA: 401
        # is impossible on a public endpoint but is included for parity in
        # case the WFS server starts requiring tokens; 404 catches typo'd
        # typenames (chosen layer name from eval-dist_eu/effis_endpoint_lock.txt
        # is locked at Plan 05-05 / 05-07; runtime drift surfaces as 404
        # rather than infinite retry).
        "retry_on": [429, 503, 504, "ConnectionError", "TimeoutError"],
        "abort_on": [401, 403, 404],
        # ME-02 fix: declare retry parameters here so effis.py reads them
        # from the policy rather than hardcoding (CONTEXT D-18 single source
        # of truth). Backoff schedule: 2s, 4s, 8s, 16s, 32s (urllib3 caps
        # at 60s by default).
        "max_attempts": 5,
        "backoff_factor": 2,
    },
    "jrc": {
        # Phase 6 DSWX-04 JRC Global Surface Water Monthly History tile fetch.
        # Public HTTPS endpoint (no auth); jeodpp.jrc.ec.europa.eu / EC servers
        # serve large GeoTIFFs (~30 MB each at 10-degree tile size). 404 means
        # tile out-of-coverage (ocean tile or pre-1984/post-2021); benign,
        # propagated as None per existing _fetch_jrc_tile signature (Plan 06-04
        # refactors compare_dswx._fetch_jrc_tile to call download_reference_with_retry
        # with source='jrc'). Backoff schedule: 2s, 4s, 8s, 16s, 32s = 62s total.
        "retry_on": [429, 503, 504, "ConnectionError", "TimeoutError"],
        "abort_on": [401, 403, 404],
        "max_attempts": 5,
        "backoff_factor": 2,
        "max_backoff_s": 60,
    },
}


class ReferenceDownloadError(Exception):
    """Raised when :func:`download_reference_with_retry` hits an abort status.

    Attributes
    ----------
    source : str
        Source key from :data:`RETRY_POLICY` (e.g. ``"CDSE"``).
    status : int | str
        HTTP status code or symbolic status string that triggered the abort.
    url : str
        The URL that returned the abort status.
    """

    def __init__(self, source: str, status: int | str, url: str) -> None:
        super().__init__(
            f"Abort: source={source} status={status} url={url} "
            f"(per RETRY_POLICY[{source!r}]['abort_on'])"
        )
        self.source = source
        self.status = status
        self.url = url


# ----------------------------------------------------------------------------
# Burst bounds (ENV-08)
# ----------------------------------------------------------------------------


def bounds_for_burst(
    burst_id: str,
    buffer_deg: float = 0.2,
) -> tuple[float, float, float, float]:
    """Return ``(west, south, east, north)`` in degrees for a burst_id, buffered.

    Primary path: ``opera_utils.burst_frame_db.get_burst_id_geojson([burst_id],
    as_geodataframe=True)``.
    Fallback path: ``subsideo.burst.db.query_bounds(burst_id)`` for EU bursts
    not yet in opera-utils' N.Am.-only DB (RESEARCH.md Open Question 2).

    Mitigates PITFALLS P1.1 cached-bias (hand-coded bounds drift from the
    true burst footprint over product-generation cycles).

    Parameters
    ----------
    burst_id : str
        JPL-format burst ID (e.g. ``"t144_308029_iw1"``).
    buffer_deg : float, default 0.2
        Symmetric degree buffer applied to all four bounds.

    Returns
    -------
    tuple[float, float, float, float]
        Buffered ``(west, south, east, north)`` in WGS 84 degrees.

    Raises
    ------
    ValueError
        If the burst is not found in either opera_utils or the subsideo EU
        burst DB. The message references both lookup failures.
    """
    west: float
    south: float
    east: float
    north: float
    try:
        from opera_utils.burst_frame_db import get_burst_id_geojson

        gdf = get_burst_id_geojson([burst_id], as_geodataframe=True)
        if len(gdf) == 0:
            raise ValueError(
                f"Burst {burst_id!r} not in opera_utils burst_frame_db"
            )
        w, s, e, n = gdf.total_bounds
        west, south, east, north = float(w), float(s), float(e), float(n)
    except Exception as first_err:  # noqa: BLE001
        logger.debug(
            "opera_utils lookup failed for {}: {}; trying EU burst DB",
            burst_id,
            first_err,
        )
        try:
            from subsideo.burst.db import query_bounds  # Task 2 adds this

            west, south, east, north = query_bounds(burst_id)
        except Exception as second_err:  # noqa: BLE001
            raise ValueError(
                f"Burst {burst_id!r} not in opera_utils or subsideo EU DB: "
                f"(opera_utils: {first_err}; fallback: {second_err})"
            ) from second_err

    return (
        float(west - buffer_deg),
        float(south - buffer_deg),
        float(east + buffer_deg),
        float(north + buffer_deg),
    )


# ----------------------------------------------------------------------------
# MGRS-tile bounds (ENV-08 Plan 01-07 DSWx consumer)
# ----------------------------------------------------------------------------


def bounds_for_mgrs_tile(
    tile_id: str,
    buffer_deg: float = 0.1,
) -> tuple[float, float, float, float]:
    """Return ``(west, south, east, north)`` in degrees for an MGRS-100km tile.

    Primary path: ``opera_utils.burst_frame_db`` MGRS helpers (if available in
    the installed opera-utils version; opera-utils 0.25.6 does not yet ship
    MGRS helpers, so the fallback below is exercised).

    Fallback path: lookup against the
    ``src/subsideo/validation/_mgrs_tiles.geojson`` seed file that ships with
    subsideo. The seed covers v1.1 eval-script tile IDs (10TFK, 29TNF, 33TXP
    at minimum); every tile used by any ``run_eval_*.py`` at v1.1 lands here.

    Used by:

    * ``run_eval_dswx.py`` (Lake Balaton tile 33TXP) — Plan 01-07 Task 3.
    * Imported but not called by ``run_eval_dist*.py`` (dist_s1 auto-derives
      bounds from ``mgrs_tile_id`` internally) — Plan 01-07 Task 3.

    Parameters
    ----------
    tile_id : str
        MGRS-100km tile identifier (e.g. ``"33TXP"``).
    buffer_deg : float, default 0.1
        Symmetric degree buffer applied to all four bounds.

    Returns
    -------
    tuple[float, float, float, float]
        Buffered ``(west, south, east, north)`` in WGS 84 degrees.

    Raises
    ------
    ValueError
        If the tile is not found in either opera_utils (primary) or the
        shipped seed file (fallback).
    """
    # (1) Primary: opera_utils MGRS helpers (if present in installed version).
    try:
        from opera_utils.burst_frame_db import (  # type: ignore[attr-defined]
            get_mgrs_tile_geojson,
        )

        gdf = get_mgrs_tile_geojson([tile_id], as_geodataframe=True)
        if len(gdf) >= 1:
            w, s, e, n = gdf.total_bounds
            return (
                float(w - buffer_deg),
                float(s - buffer_deg),
                float(e + buffer_deg),
                float(n + buffer_deg),
            )
    except (ImportError, AttributeError) as e:
        logger.debug(
            "opera_utils MGRS lookup unavailable ({}); using seed file", e
        )
    except Exception as e:  # noqa: BLE001
        # Any other opera_utils-side failure (e.g. unrecognised tile) ->
        # fall through to the seed-file lookup.
        logger.debug(
            "opera_utils MGRS lookup failed for {}: {}; using seed file",
            tile_id,
            e,
        )

    # (2) Fallback: seed GeoJSON shipped with subsideo.
    seed_path = _pkg_files("subsideo.validation").joinpath("_mgrs_tiles.geojson")
    try:
        data = json.loads(seed_path.read_text())
    except (FileNotFoundError, OSError) as e:
        raise ValueError(
            f"MGRS tile {tile_id!r} not in opera_utils and seed file "
            f"unreadable: {e}"
        ) from e

    for feat in data.get("features", []):
        props = feat.get("properties", {}) or {}
        if props.get("tile_id") == tile_id or props.get("mgrs_tile") == tile_id:
            geom = feat.get("geometry", {}) or {}
            if geom.get("type") == "Polygon":
                coords = geom["coordinates"][0]
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                return (
                    float(min(lons) - buffer_deg),
                    float(min(lats) - buffer_deg),
                    float(max(lons) + buffer_deg),
                    float(max(lats) + buffer_deg),
                )

    raise ValueError(
        f"MGRS tile {tile_id!r} not in opera_utils or {seed_path} "
        f"(seed covers 10TFK, 29TNF, 33TXP, ... — add the missing tile "
        f"if v1.1 eval scripts require it)"
    )


# ----------------------------------------------------------------------------
# Credential preflight (ENV-06)
# ----------------------------------------------------------------------------


def credential_preflight(env_vars: Sequence[str]) -> None:
    """Fail fast if any required env var is unset or empty.

    Called at the top of every eval script (replacing the ad-hoc
    ``if not os.environ.get(...)`` blocks scattered across v1.0 scripts).

    Parameters
    ----------
    env_vars : Sequence[str]
        Names of env vars that must be set (non-empty) for the script to
        proceed.

    Raises
    ------
    SystemExit
        Raised with a one-line message listing every missing var name, so
        the user can fix the ``.env`` / shell export in a single pass.
    """
    # WR-09: strip before truthiness so a whitespace-only value (common result
    # of a ``.env`` mis-edit with a trailing space) is also flagged as missing,
    # rather than passing preflight and failing deeper with a less actionable
    # error.
    missing = [v for v in env_vars if not (os.environ.get(v) or "").strip()]
    if missing:
        raise SystemExit(
            f"credential_preflight: the following env vars are not set or "
            f"empty: {missing}. Check .env or shell export."
        )


# ----------------------------------------------------------------------------
# OPERA frame selection (REL-03)
# ----------------------------------------------------------------------------


def select_opera_frame_by_utc_hour(
    sensing_datetime: datetime,
    frame_metadata: Sequence[dict[str, Any]],
    *,
    tolerance_hours: float = 1.0,
) -> dict[str, Any]:
    """Return the frame whose ``sensing_datetime`` matches the query UTC hour.

    Used when ``asf-search`` returns multiple candidate OPERA frames for the
    same burst — the correct frame is the one whose ``sensing_datetime``
    (exact UTC hour + spatial footprint) matches the source SLC. Matches the
    REL-03 methodological finding "OPERA frame selection by exact UTC hour +
    spatial footprint".

    Parameters
    ----------
    sensing_datetime : datetime
        The query datetime (typically the SLC sensing time).
    frame_metadata : Sequence[dict[str, Any]]
        Candidate frames. Each must expose a ``"sensing_datetime"`` key whose
        value is either a :class:`datetime.datetime` or an ISO-8601 string.
    tolerance_hours : float, keyword-only, default 1.0
        Maximum hours between ``sensing_datetime`` and each candidate frame.

    Returns
    -------
    dict[str, Any]
        The uniquely matching frame dict.

    Raises
    ------
    ValueError
        If zero or multiple frames match within ``tolerance_hours``.
    """
    target_hour = sensing_datetime.replace(minute=0, second=0, microsecond=0)
    matches: list[dict[str, Any]] = []
    for frame in frame_metadata:
        ft = frame.get("sensing_datetime")
        if ft is None:
            continue
        if isinstance(ft, str):
            ft = datetime.fromisoformat(ft.replace("Z", "+00:00"))
        # Normalise tz symmetrically so subtraction never raises
        # TypeError "can't subtract offset-naive and offset-aware datetimes"
        # regardless of which side carries a tzinfo (WR-01).
        if ft.tzinfo is not None and target_hour.tzinfo is None:
            ft_cmp = ft.replace(tzinfo=None)
            target_cmp = target_hour
        elif target_hour.tzinfo is not None and ft.tzinfo is None:
            ft_cmp = ft
            target_cmp = target_hour.replace(tzinfo=None)
        else:
            ft_cmp = ft
            target_cmp = target_hour
        delta = abs((ft_cmp - target_cmp).total_seconds())
        if delta <= tolerance_hours * 3600:
            matches.append(frame)

    if not matches:
        raise ValueError(
            f"No OPERA frame within {tolerance_hours}h of {sensing_datetime}"
        )
    if len(matches) > 1:
        ids = [f.get("id") or f.get("granule") for f in matches]
        raise ValueError(
            f"Multiple OPERA frames within {tolerance_hours}h of "
            f"{sensing_datetime}: {ids}"
        )
    return matches[0]


# ----------------------------------------------------------------------------
# Resume safety
# ----------------------------------------------------------------------------


def ensure_resume_safe(
    cache_dir: Path,
    manifest_keys: Sequence[str],
) -> bool:
    """Return True if ``cache_dir`` contains every expected manifest-key entry.

    Non-destructive: never deletes or truncates files. Returns False when any
    listed key is missing, so the caller can decide between re-download and
    abort. Never raises (a corrupt cache_dir surface returns False + warning).

    Parameters
    ----------
    cache_dir : Path
        Directory to inspect.
    manifest_keys : Sequence[str]
        File names expected to exist at the top level of ``cache_dir``.

    Returns
    -------
    bool
        True if every key is present; False otherwise.
    """
    cache_dir = Path(cache_dir)
    if not cache_dir.exists():
        return False
    try:
        existing = {p.name for p in cache_dir.iterdir()}
    except (OSError, PermissionError) as e:
        logger.warning("ensure_resume_safe: cannot read {}: {}", cache_dir, e)
        return False
    return all(k in existing for k in manifest_keys)


# ----------------------------------------------------------------------------
# Cross-cell SAFE cache reuse (D-02)
# ----------------------------------------------------------------------------


def find_cached_safe(
    granule_id: str,
    search_dirs: Sequence[Path],
) -> Path | None:
    """Return the first S1 SAFE path matching ``granule_id`` across ``search_dirs``.

    Phase 2 D-02 mechanism for cross-cell SAFE cache reuse. Scans each
    directory in order and returns the first path whose filename stem
    contains ``granule_id`` as a substring. This tolerates both
    ``*.zip`` and ``*.SAFE`` directory variants because ``Path.stem``
    strips only a single trailing suffix.

    No symlinks are created; no copies are made. The caller passes the
    returned path to ``run_rtc(safe_paths=[path])`` wherever it lives
    (typically another ``eval-*/input/`` directory owned by a sibling
    matrix cell). Cache partitioning stays per-cell for DEM / orbit /
    OPERA reference products -- only the large SAFE zips are shared.

    Parameters
    ----------
    granule_id : str
        S1 granule identifier fragment (typically the
        ``S1A_IW_SLC__1SDV_<START>_<STOP>_<ORBIT>_<MISSION>_<CHECKSUM>``
        form), without trailing ``.zip`` or ``.SAFE``. Substring-match
        semantics on ``path.stem`` so callers can pass either the full
        granule name or a distinguishing prefix.
    search_dirs : Sequence[Path]
        Directories to probe, in priority order. The typical order is
        ``[eval-rtc-eu/input, eval-disp-egms/input, eval-dist-eu/input,
        eval-dist-eu-nov15/input]``. Missing or unreadable directories
        are silently skipped (warn-logged, never raised).

    Returns
    -------
    Path | None
        First matching path in the first search_dir that contains one;
        ``None`` when no search_dir contains a match.
    """
    for d in search_dirs:
        d = Path(d)
        if not d.exists() or not d.is_dir():
            continue
        try:
            for p in sorted(d.iterdir()):
                if granule_id in p.stem:
                    logger.debug(
                        "find_cached_safe hit: granule_id={} path={}", granule_id, p
                    )
                    return p
        except (OSError, PermissionError) as e:
            logger.warning("find_cached_safe: cannot read {}: {}", d, e)
            continue
    return None


# ----------------------------------------------------------------------------
# Download with per-source retry (ENV-06, PITFALLS P0.4)
# ----------------------------------------------------------------------------


def _coerce_status(resp: requests.Response) -> int:
    try:
        return int(resp.status_code)
    except Exception:  # noqa: BLE001
        return -1


def download_reference_with_retry(
    url: str,
    dest: Path,
    *,
    source: RetrySource,
    max_retries: int = 5,
    backoff_seconds: int = 30,
    session: requests.Session | None = None,
) -> Path:
    """Download ``url`` to ``dest`` applying the per-source retry policy.

    Parameters
    ----------
    url : str
        HTTPS URL to download from.
    dest : Path
        Destination file path. Parents are created as needed. The download
        is streamed to ``<dest>.partial`` and atomically renamed on success
        (T-06-04 mitigation).
    source : {"CDSE", "EARTHDATA", "CLOUDFRONT", "HTTPS"}
        Keyword-only source key into :data:`RETRY_POLICY`. A source key is
        REQUIRED — there is no default (P0.4 mitigation).
    max_retries : int, default 5
        Maximum attempts before raising ``requests.RequestException``.
    backoff_seconds : int, default 30
        Base backoff delay; exponential backoff with 300 s cap.
    session : requests.Session | None, default None
        Optional pre-configured session (for auth / connection pooling).

    Returns
    -------
    Path
        ``dest`` on success.

    Raises
    ------
    ValueError
        If ``source`` is not a key of :data:`RETRY_POLICY` (P0.4 mitigation —
        no implicit default permitted).
    ReferenceDownloadError
        If the response status is in ``RETRY_POLICY[source]['abort_on']`` or,
        for ``CLOUDFRONT``, in ``refresh_url_on`` (caller must refresh the
        signed URL).
    requests.RequestException
        Raised after ``max_retries`` are exhausted on retryable statuses.
    """
    if source not in RETRY_POLICY:
        raise ValueError(
            f"download_reference_with_retry: unknown source {source!r} "
            f"(expected one of {sorted(RETRY_POLICY)})"
        )

    policy = RETRY_POLICY[source]
    sess = session or requests.Session()
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    attempt = 0
    current_url = url
    while attempt < max_retries:
        attempt += 1
        try:
            with sess.get(current_url, stream=True, timeout=300) as resp:
                status = _coerce_status(resp)

                if status in policy.get("abort_on", []):
                    raise ReferenceDownloadError(source, status, current_url)

                if source == "CLOUDFRONT" and status in policy.get(
                    "refresh_url_on", []
                ):
                    logger.warning(
                        "CloudFront URL expired (status 403); caller must "
                        "refresh the signed URL — aborting with "
                        "ReferenceDownloadError."
                    )
                    raise ReferenceDownloadError(source, status, current_url)

                if status in policy.get("retry_on", []):
                    wait = min(backoff_seconds * (2 ** (attempt - 1)), 300)
                    logger.info(
                        "Retry {}/{} for {} ({}): status={}, sleeping {}s",
                        attempt,
                        max_retries,
                        source,
                        current_url,
                        status,
                        wait,
                    )
                    time.sleep(wait)
                    continue

                # CR-02 mitigation: any HTTP error status that is NOT in
                # ``retry_on`` must fail fast. Without this explicit branch,
                # ``resp.raise_for_status()`` raises ``requests.HTTPError``
                # which falls through to the ``except requests.RequestException``
                # handler below and is silently retried up to ``max_retries``
                # -- violating the per-source RETRY_POLICY contract
                # (PITFALLS P0.4).
                if status >= 400:
                    raise ReferenceDownloadError(source, status, current_url)

                resp.raise_for_status()
                # 2xx — stream to a .partial tempfile and atomically rename
                # on success (T-06-04 — avoid half-written files in dest).
                tmp = dest.with_suffix(dest.suffix + ".partial")
                with tmp.open("wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                tmp.replace(dest)
                logger.info("Downloaded {} -> {}", current_url, dest)
                return dest
        except ReferenceDownloadError:
            raise
        except (requests.ConnectionError, requests.Timeout) as e:
            # Only transport-level errors are retried. HTTPErrors are handled
            # above by the explicit status-code branches so they never reach
            # this handler (CR-02 mitigation).
            logger.warning(
                "Transport error for {} attempt {}/{}: {}",
                current_url,
                attempt,
                max_retries,
                e,
            )
            time.sleep(min(backoff_seconds * (2 ** (attempt - 1)), 300))

    raise requests.RequestException(
        f"download_reference_with_retry exhausted {max_retries} attempts "
        f"for {url}"
    )
