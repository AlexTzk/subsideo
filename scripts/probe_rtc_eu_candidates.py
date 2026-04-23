"""Probe ASF + NASA Earthdata for Phase 2 RTC-EU candidate bursts.

Runs a one-shot live query against two data sources for each of the five
BOOTSTRAP §1.1 candidate regimes:

1. ``earthaccess.search_data(short_name='OPERA_L2_RTC-S1_V1', ...)`` -- counts
   how many OPERA L2 RTC granules exist over the candidate AOI in the 2024
   - 2025 window (if 0, the candidate is unusable per FEATURES line 50).
2. ``asf_search.search(platform=SENTINEL1, processingLevel='SLC', ...)`` --
   finds a concrete SLC best-match by sensing UTC hour, returning the
   closest granule name and sensing time.

Writes the result as a markdown table to
``.planning/milestones/v1.1-research/rtc_eu_burst_candidates.md``.

This script is NOT invoked under ``supervisor`` and does NOT produce a
matrix cell. It is a pre-eval sub-deliverable per CONTEXT.md §decisions
D-01. Re-runnable: running it again overwrites the artifact with fresh
counts reflecting ASF catalog state at probe time.

Usage::

    micromamba run -n subsideo python scripts/probe_rtc_eu_candidates.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

from dotenv import load_dotenv


class Candidate(NamedTuple):
    # Claude-drafted per D-04; user reviews via the probe artifact.
    regime: str  # Alpine | Scandinavian | Iberian | TemperateFlat | Fire
    label: str  # Human-readable region name.
    bbox: tuple[float, float, float, float]  # (minx_lon, miny_lat, maxx_lon, maxy_lat)
    expected_relorb: int | None  # Hint for ASF narrowing (not binding).
    expected_max_relief_m: int  # Roughly from public DEM inspection.
    centroid_lat: float
    cached_safe_dir: Path | None  # eval-*/input/ where SAFE may already exist.


# -- Claude-drafted five candidates per D-04 --------------------------------
# User reviews this list in the probe artifact. Bbox values are AOI
# bounding boxes (WGS84 lon/lat) roughly covering a 1-2 burst footprint.
# expected_max_relief_m is informational; the eval script computes the
# true value from the cached DEM at run time.
CANDIDATES: list[Candidate] = [
    # 1. Alpine >1000 m relief -- Swiss/Italian Alps (Valtellina / Bernese Oberland).
    Candidate(
        regime="Alpine",
        label="Swiss/Italian Alps (Valtellina region)",
        bbox=(9.5, 46.0, 10.5, 46.7),
        expected_relorb=66,
        expected_max_relief_m=3200,
        centroid_lat=46.35,
        cached_safe_dir=None,
    ),
    # 2. Scandinavian >55°N -- Northern Sweden (Norrbotten lowlands).
    Candidate(
        regime="Scandinavian",
        label="Northern Sweden (Norrbotten, >67°N)",
        bbox=(20.5, 66.8, 22.5, 67.5),
        expected_relorb=29,
        expected_max_relief_m=500,
        centroid_lat=67.15,
        cached_safe_dir=None,
    ),
    # 3. Iberian arid -- Meseta north of Madrid (same AOI family as Phase 3 CSLC).
    Candidate(
        regime="Iberian",
        label="Iberian Meseta (north of Madrid)",
        bbox=(-4.0, 40.8, -3.0, 41.5),
        expected_relorb=154,
        expected_max_relief_m=500,
        centroid_lat=41.15,
        cached_safe_dir=None,
    ),
    # 4. Temperate-flat -- Po plain Bologna; SAFE cached from DISP-EGMS eval.
    Candidate(
        regime="TemperateFlat",
        label="Po plain (Bologna, Italy)",
        bbox=(11.0, 44.2, 11.8, 44.8),
        expected_relorb=117,
        expected_max_relief_m=100,
        centroid_lat=44.50,
        cached_safe_dir=Path("eval-disp-egms/input"),
    ),
    # 5. Portuguese fire footprint -- Aveiro/Viseu 2024; SAFE cached from DIST-EU.
    Candidate(
        regime="Fire",
        label="Central Portugal (Aveiro/Viseu fire footprint)",
        bbox=(-8.6, 40.4, -7.8, 41.0),
        expected_relorb=154,
        expected_max_relief_m=400,
        centroid_lat=40.70,
        cached_safe_dir=Path("eval-dist-eu/input"),
    ),
]


def _bbox_wkt(bbox: tuple[float, float, float, float]) -> str:
    w, s, e, n = bbox
    return f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"


def _probe_opera_count(bbox: tuple[float, float, float, float]) -> int:
    """Return count of OPERA L2 RTC-S1 granules over bbox in 2024-2025."""
    import earthaccess

    results = earthaccess.search_data(
        short_name="OPERA_L2_RTC-S1_V1",
        temporal=("2024-01-01", "2025-12-31"),
        bounding_box=bbox,
    )
    return len(results)


def _probe_best_slc(
    bbox: tuple[float, float, float, float],
    expected_relorb: int | None,
) -> tuple[str | None, str | None]:
    """Return (best_match_sensing_utc_iso, granule_name) or (None, None) on empty."""
    import asf_search as asf

    kwargs: dict[str, object] = dict(
        platform=asf.PLATFORM.SENTINEL1,
        processingLevel="SLC",
        beamMode="IW",
        intersectsWith=_bbox_wkt(bbox),
        start="2024-05-01T00:00:00Z",
        end="2024-10-31T23:59:59Z",
        maxResults=50,
    )
    if expected_relorb is not None:
        kwargs["relativeOrbit"] = expected_relorb
    results = asf.search(**kwargs)  # type: ignore[arg-type]
    if not results:
        return None, None
    # Pick the earliest 2024 summer scene for determinism.
    first = min(results, key=lambda r: str(r.properties.get("startTime", "")))
    return first.properties.get("startTime"), first.properties.get("fileID")


def _check_cached_safe(cand: Candidate) -> str:
    """Return a markdown-friendly path if a SAFE/.zip exists in cached_safe_dir."""
    if cand.cached_safe_dir is None:
        return "(none)"
    d = cand.cached_safe_dir
    if not d.exists() or not d.is_dir():
        return f"(not cached: {d})"
    zips = sorted(d.glob("S1*_SLC*.zip"))
    safes = sorted(d.glob("S1*_SLC*.SAFE"))
    hits = zips + safes
    if not hits:
        return f"(none in {d})"
    return f"`{hits[0]}`"


def _build_row(cand: Candidate) -> dict[str, str]:
    """Run both probes and assemble a row dict for the artifact."""
    try:
        opera_count = _probe_opera_count(cand.bbox)
    except Exception as e:  # noqa: BLE001 - probe tool, keep going
        print(f"  ! opera probe failed for {cand.label}: {e}")
        opera_count = -1
    try:
        sensing, granule = _probe_best_slc(cand.bbox, cand.expected_relorb)
    except Exception as e:  # noqa: BLE001 - probe tool, keep going
        print(f"  ! slc probe failed for {cand.label}: {e}")
        sensing, granule = None, None

    # TODO(user): derive burst_id from granule_name via opera_utils.get_burst_id
    #             once a concrete SLC is chosen. For the probe artifact, we
    #             report the granule name itself and a placeholder burst_id
    #             the user fills in during review.
    burst_id_placeholder = "(derive via opera_utils.get_burst_id on the chosen granule)"
    return {
        "regime": cand.regime,
        "label": cand.label,
        "bbox": f"{cand.bbox}",
        "centroid_lat": f"{cand.centroid_lat:.2f}",
        "expected_max_relief_m": f"~{cand.expected_max_relief_m}",
        "best_match_sensing_utc": sensing or "(no SLC found)",
        "best_match_granule": granule or "(no SLC found)",
        "opera_rtc_granules_2024_2025": (
            "n/a" if opera_count == -1 else str(opera_count)
        ),
        "cached_safe": _check_cached_safe(cand),
        "burst_id": burst_id_placeholder,
    }


ARTIFACT_PATH = Path(
    ".planning/milestones/v1.1-research/rtc_eu_burst_candidates.md"
)


def _render_markdown(rows: list[dict[str, str]]) -> str:
    # Python 3.12+ safe: tz-aware stamp (deprecated utcnow avoided).
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# RTC-S1 EU Burst Candidates -- Probe Report",
        "",
        f"**Probed:** {now_iso}",
        "**Source query:** `asf_search` + `earthaccess` against ASF DAAC.",
        "**Phase:** 2 (RTC-S1 EU Validation)",
        (
            "**Decision:** D-01 (probe artifact) + D-03 (5-regime fixed list) "
            "+ D-04 (Claude drafts; user reviews)."
        ),
        "",
        "## Regime Coverage",
        "",
        (
            "| # | regime | label | centroid_lat | expected_max_relief_m "
            "| opera_rtc_granules_2024_2025 | best_match_sensing_utc "
            "| best_match_granule | cached_safe | burst_id (fill-in) |"
        ),
        (
            "|---|--------|-------|--------------|-----------------------"
            "|------------------------------|------------------------"
            "|--------------------|-------------|---------------------|"
        ),
    ]
    for i, row in enumerate(rows, start=1):
        granule_cell = (
            f"`{row['best_match_granule']}`"
            if row["best_match_granule"] != "(no SLC found)"
            else row["best_match_granule"]
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(i),
                    row["regime"],
                    row["label"],
                    row["centroid_lat"],
                    row["expected_max_relief_m"],
                    row["opera_rtc_granules_2024_2025"],
                    row["best_match_sensing_utc"],
                    granule_cell,
                    row["cached_safe"],
                    row["burst_id"],
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## RTC-01 Mandatory Constraints Audit",
            "",
            "- **>1000 m relief:** row #1 (Alpine, expected ~3200 m) -- PASS candidate.",
            "- **>55°N:** row #2 (Scandinavian, centroid ~67.15°N) -- PASS candidate.",
            "",
            (
                "Claude has drafted the five regime rows per BOOTSTRAP §1.1 + "
                "CONTEXT D-03. User review per D-04 resolves:"
            ),
            "",
            (
                "1. Which granule from `best_match_granule` is the target SLC for each "
                "fresh burst (Alpine / Scandinavian / Iberian)."
            ),
            (
                "2. The concrete `burst_id` (JPL lowercase `t<relorb>_<burst>_iw<swath>`) "
                "derived from the chosen granule. This can be computed via "
                "`opera_utils.burst_frame_db.get_burst_id_geojson()` + visual inspection, "
                "or by running a Python snippet using `opera_utils.get_burst_id` over "
                "the SAFE."
            ),
            (
                "3. Whether any regime should be swapped (opera_rtc_granules_2024_2025 "
                "== 0 makes that candidate unusable)."
            ),
            (
                "4. Sensing UTC hour to pass to `select_opera_frame_by_utc_hour` "
                "(harness default: +-1h tolerance)."
            ),
            "",
            (
                "Plan 02-04 locks the 5-burst final list from this artifact. Downstream "
                "the probe doc is referenced (via `see probe artifact`) but not re-run "
                "at eval time."
            ),
            "",
            "## Query reproducibility",
            "",
            "Re-run: `micromamba run -n subsideo python scripts/probe_rtc_eu_candidates.py`.",
            "",
            (
                "Requires `EARTHDATA_USERNAME` + `EARTHDATA_PASSWORD` in env or `.env`. "
                "Counts reflect ASF catalog state at probe time; a re-run may show "
                "different numbers as OPERA operational products publish."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    load_dotenv()
    if not os.environ.get("EARTHDATA_USERNAME") or not os.environ.get(
        "EARTHDATA_PASSWORD"
    ):
        print(
            "ERROR: EARTHDATA_USERNAME and EARTHDATA_PASSWORD must be set "
            "(env or .env) for the earthaccess.search_data call."
        )
        return 1

    import earthaccess

    try:
        earthaccess.login(strategy="environment")
    except Exception as e:  # noqa: BLE001 - probe tool
        print(f"earthaccess.login failed: {e}")
        return 2

    print(f"Probing {len(CANDIDATES)} RTC-EU candidate regimes ...")
    rows = []
    for cand in CANDIDATES:
        print(f"- {cand.regime}: {cand.label}")
        rows.append(_build_row(cand))

    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(_render_markdown(rows))
    print(f"Wrote probe artifact: {ARTIFACT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
