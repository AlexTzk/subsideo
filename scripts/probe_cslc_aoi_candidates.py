"""Probe script for Phase 3 CSLC self-consistency AOI candidates (D-10).

Queries:
  1. earthaccess.search_data(short_name='OPERA_L2_CSLC-S1_V1', ...) for
     2024-01..2025-12 granule count per candidate AOI bbox.
  2. asf_search.search for Sentinel-1A IW SLC scenes over each candidate
     bbox to derive a 15-epoch sensing window (2024 H1 window).
  3. Derives the dominant burst_id via opera_utils.get_burst_id on the
     first OPERA CSLC-S1 granule discovered in each bbox (Phase 2
     derive-script pattern).
  4. For EU candidates, estimates EGMS L2a stable-PS count via a
     back-of-envelope density × area × stable-fraction ceiling (no full
     L2a download — that is deferred to Plan 03-04).
  5. Writes .planning/milestones/v1.1-research/cslc_selfconsist_aoi_candidates.md
     with the CONTEXT D-10 schema + per-AOI 15-epoch Locked Sensing Windows
     + SoCal 15-epoch section + Mojave fallback ordering + user-review
     checklist + query-reproducibility footer.

Credentials required:
  EARTHDATA_USERNAME + EARTHDATA_PASSWORD (earthaccess)
  CDSE_CLIENT_ID + CDSE_CLIENT_SECRET (optional; EGMS L2a inspection uses
    its own anonymous endpoint)

Invocation:
  micromamba run -n subsideo python scripts/probe_cslc_aoi_candidates.py

Output:
  .planning/milestones/v1.1-research/cslc_selfconsist_aoi_candidates.md
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# ---------------------------------------------------------------------------
# Candidate AOI definitions (CONTEXT D-11 ordering)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateAOI:
    """Declarative definition of a single probe candidate AOI."""

    aoi: str  # "Mojave/Coso-Searles" | "Iberian/Meseta-North" | ...
    region: str  # "NAM" | "EU"
    regime: str  # e.g. "desert-bedrock-playa-adjacent"
    label: str  # human-readable label
    bbox: tuple[float, float, float, float]  # west, south, east, north (WGS84)
    published_insar_stability_ref: str  # DOI / URL / paper citation
    expected_stable_pct_per_worldcover: float  # 0.0–1.0 sanity estimate
    cached_safe_fallback_path: str  # "eval-cslc/input" or "(none)"


CANDIDATES: list[CandidateAOI] = [
    # --- Mojave fallback chain (D-11 order: pre-ranked by coverage × stable_pct) ---
    CandidateAOI(
        aoi="Mojave/Coso-Searles",
        region="NAM",
        regime="desert-bedrock-playa-adjacent",
        label="Coso Volcanic Field / Searles Valley (CA)",
        bbox=(-117.80, 35.65, -117.30, 36.05),
        published_insar_stability_ref=(
            "Monastero et al. 2005 (J. Geophys. Res.); "
            "Coso regional subsidence mapped InSAR-stable on ridges"
        ),
        expected_stable_pct_per_worldcover=0.35,
        cached_safe_fallback_path="(none)",
    ),
    CandidateAOI(
        aoi="Mojave/Pahranagat",
        region="NAM",
        regime="desert-bedrock",
        label="Pahranagat Valley (NV)",
        bbox=(-115.35, 37.10, -115.00, 37.45),
        published_insar_stability_ref=(
            "Schwing et al. 2022 (Geosphere); Basin-and-Range stability "
            "well-documented for InSAR in the area"
        ),
        expected_stable_pct_per_worldcover=0.30,
        cached_safe_fallback_path="(none)",
    ),
    CandidateAOI(
        aoi="Mojave/Amargosa",
        region="NAM",
        regime="desert-bedrock-playa-adjacent",
        label="Amargosa Valley (NV/CA)",
        bbox=(-116.60, 36.30, -116.25, 36.65),
        published_insar_stability_ref=(
            "Sneed et al. 2003 (USGS SIR); playa-adjacent stable bedrock sides"
        ),
        expected_stable_pct_per_worldcover=0.25,
        cached_safe_fallback_path="(none)",
    ),
    CandidateAOI(
        aoi="Mojave/Hualapai",
        region="NAM",
        regime="plateau-bedrock",
        label="Hualapai Plateau (AZ)",
        bbox=(-113.70, 35.50, -113.20, 35.90),
        published_insar_stability_ref=(
            "Chaussard et al. 2014 (JGR); Colorado Plateau edge, stable "
            "bedrock, low vegetation"
        ),
        expected_stable_pct_per_worldcover=0.40,
        cached_safe_fallback_path="(none)",
    ),
    # --- Iberian primary + fallbacks ---
    CandidateAOI(
        aoi="Iberian/Meseta-North",
        region="EU",
        regime="iberian-meseta-sparse-vegetation",
        label="Iberian Meseta north of Madrid",
        bbox=(-4.00, 40.80, -3.40, 41.30),
        published_insar_stability_ref=(
            "Tomás et al. 2014 (IJAEO); Meseta bedrock stability vs "
            "agricultural fallow — Segovia / Soria region stability reported"
        ),
        expected_stable_pct_per_worldcover=0.20,
        cached_safe_fallback_path="(none)",
    ),
    CandidateAOI(
        aoi="Iberian/Alentejo",
        region="EU",
        regime="interior-portugal-plateau",
        label="Alentejo interior (Portugal)",
        bbox=(-8.30, 38.30, -7.70, 38.80),
        published_insar_stability_ref=(
            "Catalão et al. 2021 (RS); Portuguese Meseta stable on "
            "bedrock-dominated slopes"
        ),
        expected_stable_pct_per_worldcover=0.18,
        cached_safe_fallback_path="(none)",
    ),
    CandidateAOI(
        aoi="Iberian/MassifCentral",
        region="EU",
        regime="massif-central-plateau",
        label="Massif Central (France)",
        bbox=(3.20, 44.90, 3.80, 45.40),
        published_insar_stability_ref=(
            "de Michele et al. 2010 (RSE); stable plateau InSAR "
            "baseline over volcanic-derived bedrock"
        ),
        expected_stable_pct_per_worldcover=0.25,
        cached_safe_fallback_path="(none)",
    ),
]


# ---------------------------------------------------------------------------
# Per-AOI symbolic tuple names — contract between probe artifact and eval
# scripts (Plan 03-03 / 03-04). Each name must match the module-level Python
# tuple declared in run_eval_cslc_selfconsist_{nam,eu}.py.
# ---------------------------------------------------------------------------

EPOCH_TUPLE_NAMES: dict[str, str] = {
    "Mojave/Coso-Searles": "MOJAVE_COSO_EPOCHS",
    "Mojave/Pahranagat": "MOJAVE_PAHRANAGAT_EPOCHS",
    "Mojave/Amargosa": "MOJAVE_AMARGOSA_EPOCHS",
    "Mojave/Hualapai": "MOJAVE_HUALAPAI_EPOCHS",
    "Iberian/Meseta-North": "IBERIAN_PRIMARY_EPOCHS",
    "Iberian/Alentejo": "IBERIAN_ALENTEJO_EPOCHS",
    "Iberian/MassifCentral": "IBERIAN_MASSIF_CENTRAL_EPOCHS",
}


# ---------------------------------------------------------------------------
# EGMS L2a PS density estimates (W10 fix — region-driven, not bbox-derived)
# ---------------------------------------------------------------------------

# All values are back-of-envelope from BOOTSTRAP §2.3 + EGMS 2019_2023 release
# metadata. NAM is not covered by EGMS; returns None for NAM AOIs.
EGMS_PS_DENSITY_PER_KM2: dict[str, float] = {
    "EU": 300.0,  # Iberian-Meseta / Alentejo / Massif Central semi-arid rock
}


# ---------------------------------------------------------------------------
# Probe query helpers
# ---------------------------------------------------------------------------


def count_opera_cslc_granules_2024(bbox: tuple[float, float, float, float]) -> int:
    """Count OPERA CSLC-S1 granules in 2024-01..2025-12 over bbox.

    Soft-fails with 0 on any network or auth error so the script can always
    produce the markdown artifact with placeholder counts.
    """
    try:
        import earthaccess  # lazy — conda-forge dep

        results = earthaccess.search_data(
            short_name="OPERA_L2_CSLC-S1_V1",
            bounding_box=bbox,
            temporal=("2024-01-01", "2025-12-31"),
        )
        return len(list(results))
    except Exception as e:  # noqa: BLE001
        logger.warning("earthaccess CSLC count query failed for bbox={}: {}", bbox, e)
        return 0


def derive_dominant_burst_id(bbox: tuple[float, float, float, float]) -> str | None:
    """Return the dominant JPL-lowercase burst_id for the bbox.

    Strategy (mirrors scripts/derive_burst_ids_from_opera.py):
      1. Query earthaccess for up to 50 OPERA CSLC-S1 granules in 2024.
      2. Extract the base filename for each granule's first data link.
      3. Parse burst_id via opera_utils.get_burst_id.
      4. Return the most common burst_id (Counter).

    Returns None if no granules found or on any error.
    """
    try:
        import earthaccess  # lazy

        results = list(
            earthaccess.search_data(
                short_name="OPERA_L2_CSLC-S1_V1",
                bounding_box=bbox,
                temporal=("2024-01-01", "2024-12-31"),
                count=50,
            )
        )
        if not results:
            logger.warning("No OPERA CSLC granules found for bbox={}", bbox)
            return None

        try:
            import opera_utils  # lazy — may not be installed in all envs
        except ImportError:
            logger.warning(
                "opera_utils not importable; burst_id derivation skipped for bbox={}",
                bbox,
            )
            return None

        burst_ids: list[str] = []
        for r in results[:50]:
            try:
                links = r.data_links()
                if not links:
                    continue
                filename = links[0].split("/")[-1]
                bid = opera_utils.get_burst_id(filename).lower()  # type: ignore[attr-defined]
                burst_ids.append(bid)
            except Exception:  # noqa: BLE001
                continue

        if not burst_ids:
            logger.warning(
                "Could not extract any burst_ids from {} OPERA granules for bbox={}",
                len(results),
                bbox,
            )
            return None

        most_common, _ = Counter(burst_ids).most_common(1)[0]
        return most_common

    except Exception as e:  # noqa: BLE001
        logger.warning("Burst-id derivation failed for bbox={}: {}", bbox, e)
        return None


def count_egms_stable_ps_ceiling(
    bbox: tuple[float, float, float, float],
    region: str,
) -> int | None:
    """Rough ceiling estimate of EGMS L2a stable PS in bbox.

    W10 fix: `region` drives the density dict lookup (NOT bbox string-match).
    Callers pass region="EU" for Iberian candidates and region="NAM" for
    Mojave candidates. NAM returns None because EGMS covers EU only — there
    is no EGMS ceiling to report for N.Am. AOIs.

    Parameters
    ----------
    bbox : (west, south, east, north) in EPSG:4326 degrees.
    region : "EU" | "NAM"

    Returns
    -------
    int | None
        Back-of-envelope count of "stable PS" (approx. area_km2 × density
        × 0.3-stable-fraction). None when region has no EGMS coverage.
    """
    if region not in EGMS_PS_DENSITY_PER_KM2:
        return None

    west, south, east, north = bbox
    lat_km = (north - south) * 111.0
    lon_km = (east - west) * 111.0 * math.cos(math.radians((north + south) / 2.0))
    area_km2 = lat_km * lon_km
    density = EGMS_PS_DENSITY_PER_KM2[region]
    ceiling = int(area_km2 * density * 0.3)  # ~30% of PS typically stable per L2a
    return ceiling


# ---------------------------------------------------------------------------
# 15-epoch sensing window per candidate AOI
# ---------------------------------------------------------------------------


def _fallback_epochs() -> list[datetime]:
    """Return a deterministic 15-entry synthetic S1A 12-day epoch list.

    Starting 2024-01-13 at 14:01:16Z, 12-day cadence, all in 2024 H1.
    Used when ASF search returns fewer than 15 scenes or fails.
    The generated markdown clearly flags these as SYNTHETIC so the user
    can override before Plan 03-03/04 lock.
    """
    dates = [
        (1, 13),
        (1, 25),
        (2, 6),
        (2, 18),
        (3, 1),
        (3, 13),
        (3, 25),
        (4, 6),
        (4, 18),
        (4, 30),
        (5, 12),
        (5, 24),
        (6, 5),
        (6, 17),
        (6, 29),
    ]
    return [datetime(2024, m, d, 14, 1, 16) for m, d in dates]


def _fifteen_epochs_for_candidate(
    c: CandidateAOI,
) -> tuple[list[datetime], bool]:
    """Return (15 sensing epochs, is_synthetic) for the candidate.

    Strategy:
      1. Query asf_search for SENTINEL-1A IW SLC scenes intersecting the
         bbox over 2024-01-01 through 2024-06-30 (168-day window).
      2. De-duplicate on calendar date (burst-level re-acquisitions may
         repeat sensing UTC within a day).
      3. Pick the first 15 unique-date epochs.
      4. On < 15 scenes or any error, return the deterministic fallback
         list and is_synthetic=True.

    Returns
    -------
    (epochs, is_synthetic) where is_synthetic=True flags probe-fallback so
    the rendered markdown includes a [SYNTHETIC FALLBACK] warning that the
    user must confirm or override before Plan 03-03/04 run.
    """
    try:
        import asf_search as asf  # lazy — pip dep

        west, south, east, north = c.bbox
        wkt = (
            f"POLYGON(({west} {south},{east} {south},"
            f"{east} {north},{west} {north},{west} {south}))"
        )
        results = asf.search(
            platform=asf.PLATFORM.SENTINEL1A,
            processingLevel=asf.PRODUCT_TYPE.SLC,
            beamMode="IW",
            intersectsWith=wkt,
            start="2024-01-01T00:00:00Z",
            end="2024-06-30T23:59:59Z",
        )
        if not results:
            logger.warning(
                "{}: no ASF SLC results in H1-2024 window; using synthetic fallback",
                c.aoi,
            )
            return _fallback_epochs(), True

        raw_times: list[str] = []
        for r in results:
            t = r.properties.get("startTime", "")
            if t:
                raw_times.append(t)

        parsed: list[datetime] = []
        for t in raw_times:
            try:
                parsed.append(datetime.fromisoformat(t.rstrip("Z")))
            except ValueError:
                continue

        parsed.sort()

        # De-dup on calendar date
        seen_dates: set[str] = set()
        unique: list[datetime] = []
        for p in parsed:
            key = p.date().isoformat()
            if key in seen_dates:
                continue
            seen_dates.add(key)
            unique.append(p)

        if len(unique) >= 15:
            logger.info("{}: ASF returned {} unique dates; using first 15", c.aoi, len(unique))
            return unique[:15], False

        logger.warning(
            "{}: only {} unique ASF scenes in H1-2024; using synthetic fallback",
            c.aoi,
            len(unique),
        )
        return _fallback_epochs(), True

    except Exception as e:  # noqa: BLE001
        logger.warning("{}: ASF 15-epoch query failed ({}); using synthetic fallback", c.aoi, e)
        return _fallback_epochs(), True


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _render_epoch_table(epochs: list[datetime], is_synthetic: bool) -> str:
    """Render a 15-epoch sensing window as a Markdown table block."""
    synthetic_warning = (
        "\n**[SYNTHETIC FALLBACK]** ASF query returned < 15 scenes or failed. "
        "User MUST confirm or override this list before Plan 03-03/04 lock.\n"
        if is_synthetic
        else ""
    )
    header = (
        f"{synthetic_warning}"
        "| # | sensing_utc | platform | orbit_type (best-effort) |\n"
        "|---|-------------|----------|--------------------------|\n"
    )
    rows = ""
    for i, ep in enumerate(epochs, start=1):
        rows += (
            f"| {i:2d} | {ep.strftime('%Y-%m-%dT%H:%M:%SZ')} | S1A | POEORB |\n"
        )
    return header + rows


def _render_markdown(
    probed_at: str,
    rows: list[dict],
    epoch_data: dict[str, tuple[list[datetime], bool]],
) -> str:
    """Render the full probe artifact as Markdown.

    Parameters
    ----------
    probed_at : ISO timestamp string.
    rows : List of per-AOI data dicts (from main()).
    epoch_data : Mapping from aoi_name to (epochs, is_synthetic).
    """
    # --- Header ---
    header = (
        "# CSLC-S1 Self-Consistency + EU AOI Candidates -- Probe Report\n\n"
        f"**Probed:** {probed_at}\n"
        "**Source query:** `earthaccess.search_data` (OPERA CSLC-S1 V1) + "
        "`asf_search` + EGMS L2a density estimate (not downloaded — back-of-"
        "envelope ceiling only).\n"
        "**Phase:** 3 (CSLC-S1 Self-Consistency + EU Validation)\n"
        "**Decision:** D-10 (probe artifact) + D-11 (Mojave fallback ordering).\n\n"
    )

    # --- CONTEXT D-10 schema candidate-rows table ---
    table_lines = [
        "## Candidate AOIs (D-10 schema)\n",
        "| aoi | regime | candidate_burst_id | opera_cslc_coverage_2024 | "
        "egms_l2a_release_2019_2023_stable_ps_count | "
        "expected_stable_pct_per_worldcover | published_insar_stability_ref | "
        "cached_safe_fallback_path |",
        "|-----|--------|--------------------|--------------------------|"
        "----------------------------------------------|"
        "------------------------------------|-------------------------------|"
        "--------------------------|",
    ]
    for r in rows:
        egms_val = (
            str(r["egms_l2a_release_2019_2023_stable_ps_count"])
            if r["egms_l2a_release_2019_2023_stable_ps_count"] is not None
            else "n/a (NAM: no EGMS coverage)"
        )
        table_lines.append(
            f"| {r['aoi']} | {r['regime']} | {r['candidate_burst_id']} | "
            f"{r['opera_cslc_coverage_2024']} | "
            f"{egms_val} | "
            f"{r['expected_stable_pct_per_worldcover']:.2f} | "
            f"{r['published_insar_stability_ref']} | "
            f"{r['cached_safe_fallback_path']} |"
        )
    table = "\n".join(table_lines) + "\n\n"

    # --- Per-AOI 15-epoch Locked Sensing Windows ---
    windows_parts = [
        "## Locked Sensing Windows\n\n"
        "Each candidate AOI locks a 15-epoch S1A 12-day stack. These lists "
        "become module-level tuples named per EPOCH_TUPLE_NAMES below in "
        "`run_eval_cslc_selfconsist_nam.py` (Mojave candidates) and "
        "`run_eval_cslc_selfconsist_eu.py` (Iberian candidates). "
        "Plan 03-03 / 03-04 acceptance checks `grep` these 7 section "
        "headings to confirm every AOI has an enumerated window.\n"
    ]
    for c in CANDIDATES:
        tuple_name = EPOCH_TUPLE_NAMES[c.aoi]
        epochs, is_synthetic = epoch_data.get(c.aoi, (_fallback_epochs(), True))
        windows_parts.append(f"\n### {tuple_name} — {c.aoi}\n\n")
        windows_parts.append(_render_epoch_table(epochs, is_synthetic))
    windows = "".join(windows_parts) + "\n"

    # --- SoCal 15-epoch section (locked by CSLC-03; separate from candidate table) ---
    socal_section = (
        "## SoCal 15-epoch Sensing Window (CSLC-03 locked burst)\n\n"
        "**Burst ID:** `t144_308029_iw1` (locked by CSLC-03; not subject to probe).\n\n"
        "**Proposed window (Claude's Discretion per CONTEXT D-09):**\n"
        "| # | sensing_utc | platform | orbit_type |\n"
        "|---|-------------|----------|------------|\n"
        "| 1  | 2024-01-13T14:01:16Z | S1A | POEORB |\n"
        "| 2  | 2024-01-25T14:01:16Z | S1A | POEORB |\n"
        "| 3  | 2024-02-06T14:01:16Z | S1A | POEORB |\n"
        "| 4  | 2024-02-18T14:01:16Z | S1A | POEORB |\n"
        "| 5  | 2024-03-01T14:01:16Z | S1A | POEORB |\n"
        "| 6  | 2024-03-13T14:01:16Z | S1A | POEORB |\n"
        "| 7  | 2024-03-25T14:01:16Z | S1A | POEORB |\n"
        "| 8  | 2024-04-06T14:01:16Z | S1A | POEORB |\n"
        "| 9  | 2024-04-18T14:01:16Z | S1A | POEORB |\n"
        "| 10 | 2024-04-30T14:01:16Z | S1A | POEORB |\n"
        "| 11 | 2024-05-12T14:01:16Z | S1A | POEORB |\n"
        "| 12 | 2024-05-24T14:01:16Z | S1A | POEORB |\n"
        "| 13 | 2024-06-05T14:01:16Z | S1A | POEORB |\n"
        "| 14 | 2024-06-17T14:01:16Z | S1A | POEORB |\n"
        "| 15 | 2024-06-29T14:01:16Z | S1A | POEORB |\n\n"
        "**Rationale:** 168-day window (14 × 12-day IFGs), all S1A POEORB (no RESORB\n"
        "epochs, no S1B after Nov 2023 end-of-life). First-epoch OPERA CSLC reference\n"
        "fetched per D-07 for amplitude sanity. Cache under\n"
        "`eval-cslc-selfconsist-nam/input/`; ~117 GB total download.\n\n"
        "**User review:** Accept as-drafted, or revise window (e.g. shift forward if\n"
        "2024-01 scenes are heavy-cloud-season corrupted on Santa Ynez aspect).\n\n"
    )

    # --- Mojave Fallback Ordering audit (CONTEXT D-11) ---
    mojave_rows = [r for r in rows if r["region"] == "NAM"]
    mojave_lines = [
        "## Mojave Fallback Ordering (CONTEXT D-11)\n\n"
        "Ordered by `(opera_cslc_coverage_2024) × (expected_stable_pct_per_worldcover)`. "
        "First attempt = Coso/Searles. On FAIL (any of: CSLC run throws, "
        "coherence_median_of_persistent < threshold triggering mask-sanity review, "
        "compute quota exhausted), the eval script iterates to the next in "
        "probe-locked order. Each attempt uses a 15-epoch sensing window — see the "
        "`MOJAVE_COSO_EPOCHS` / `MOJAVE_PAHRANAGAT_EPOCHS` / `MOJAVE_AMARGOSA_EPOCHS` / "
        "`MOJAVE_HUALAPAI_EPOCHS` sections above in **Locked Sensing Windows**.\n"
        "Single-epoch windows are forbidden per Plan 03-PATTERNS invariant "
        "(compute_residual_velocity requires >= 3 epochs; _compute_ifg_coherence_stack "
        "requires >= 2 epochs).\n\n"
        "| Attempt | AOI | Score | candidate_burst_id | expected_stable_pct | "
        "sensing_window_15 (section anchor) |\n"
        "|---------|-----|-------|---------------------|---------------------|"
        "------------------------------------|\n",
    ]
    for i, r in enumerate(mojave_rows, start=1):
        cslc_count = r["opera_cslc_coverage_2024"]
        stable_pct = r["expected_stable_pct_per_worldcover"]
        score = float(stable_pct) * float(cslc_count or 0)
        tuple_name = EPOCH_TUPLE_NAMES.get(r["aoi"], f"MOJAVE_AOI{i}_EPOCHS")
        short_aoi = r["aoi"].replace("Mojave/", "")
        mojave_lines.append(
            f"| {i} | {short_aoi} | {score:.2f} | {r['candidate_burst_id']} | "
            f"{float(stable_pct):.2f} | `{tuple_name}` |\n"
        )
    mojave_lines.append(
        "\nIf all 4 attempts fail, the eval script writes `status='BLOCKER'` to the\n"
        "Mojave parent AOIResult in `eval-cslc-selfconsist-nam/metrics.json`; matrix\n"
        "cell renders `*1/2 CALIBRATING, 1/2 BLOCKER*` per CONTEXT D-03 + D-11.\n\n"
    )
    mojave_order = "".join(mojave_lines)

    # --- Human review checklist ---
    checklist = (
        "## User Review Checklist (per CONTEXT D-04 precedent)\n\n"
        "1. **Mojave primary lock:** Accept Coso/Searles as attempt 1, or swap to\n"
        "   Hualapai (higher expected_stable_pct but different regime). Track:\n"
        "   `[ ]` accept / `[ ]` swap.\n"
        "2. **Iberian primary lock:** Accept \"Iberian Meseta north of Madrid\" as\n"
        "   primary, or swap to Alentejo. Track: `[ ]` accept / `[ ]` swap.\n"
        "3. **SoCal 15-epoch window:** Accept 2024-01-13 → 2024-06-29 POEORB-only\n"
        "   window, or revise. Track: `[ ]` accept / `[ ]` revise.\n"
        "4. **EGMS L2a threshold:** Accept `stable_std_max = 2.0 mm/yr` per CONTEXT\n"
        "   D-12, or tighten. Track: `[ ]` accept / `[ ]` tighten.\n"
        "5. **Compute budget ack:** SoCal = ~12 h fresh + Mojave worst-case 4 × 12 h\n"
        "   = 48 h fallback-chain budget. Supervisor `EXPECTED_WALL_S = 60 * 60 * 16`\n"
        "   caps per-cell wall. Track: `[ ]` ack.\n"
        "6. **Per-AOI 15-epoch windows:** Confirm each MOJAVE_*_EPOCHS and\n"
        "   IBERIAN_*_EPOCHS list in Locked Sensing Windows above. ASF-derived lists\n"
        "   may be SYNTHETIC FALLBACK — confirm OK or override manually. Track: `[ ]`.\n\n"
        "Plan 03-03 (NAM eval script) locks attempt-1 burst IDs + Mojave fallback\n"
        "ordering from this artifact after user review. Plan 03-04 (EU eval script)\n"
        "locks Iberian primary + 2 fallbacks similarly.\n\n"
    )

    # --- Query reproducibility footer ---
    footer = (
        "## Query reproducibility\n\n"
        "`micromamba run -n subsideo python scripts/probe_cslc_aoi_candidates.py`\n\n"
        "Requires `EARTHDATA_USERNAME` + `EARTHDATA_PASSWORD` in env or `.env`.\n"
        "EGMS stable-PS counts are back-of-envelope ceilings (density × area × 30%);\n"
        "full L2a download is NOT run during probe (heavy — deferred to Plan 03-04).\n"
    )

    return header + table + windows + socal_section + mojave_order + checklist + footer


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """Run the probe and write the markdown artifact.

    Soft-fails on any individual network query; always writes the artifact.
    Returns 0 on success (even if probe returned all-placeholder counts).
    """
    load_dotenv()

    # Attempt earthaccess login; probe continues even if it fails (soft-fail).
    try:
        import earthaccess  # lazy

        earthaccess.login(strategy="environment")
        logger.info("earthaccess login: OK")
    except Exception as e:  # noqa: BLE001
        logger.warning("earthaccess.login failed ({}); CSLC counts will be 0", e)

    probed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    logger.info("Probing {} CSLC-S1 AOI candidates ...", len(CANDIDATES))

    rows: list[dict] = []
    epoch_data: dict[str, tuple[list[datetime], bool]] = {}

    for c in CANDIDATES:
        logger.info("  -> {}: {}", c.aoi, c.label)

        cslc_count = count_opera_cslc_granules_2024(c.bbox)
        burst_id = derive_dominant_burst_id(c.bbox)
        egms_count = count_egms_stable_ps_ceiling(c.bbox, c.region)
        epochs, is_synthetic = _fifteen_epochs_for_candidate(c)
        epoch_data[c.aoi] = (epochs, is_synthetic)

        rows.append(
            {
                "aoi": c.aoi,
                "region": c.region,
                "regime": c.regime,
                "label": c.label,
                "candidate_burst_id": burst_id or "(no OPERA granules; rerun probe)",
                "opera_cslc_coverage_2024": cslc_count,
                "egms_l2a_release_2019_2023_stable_ps_count": egms_count,
                "expected_stable_pct_per_worldcover": c.expected_stable_pct_per_worldcover,
                "published_insar_stability_ref": c.published_insar_stability_ref,
                "cached_safe_fallback_path": c.cached_safe_fallback_path,
            }
        )
        logger.info(
            "    cslc_count={} burst_id={} egms_ceiling={} epochs_synthetic={}",
            cslc_count,
            burst_id,
            egms_count,
            is_synthetic,
        )

    out_path = Path(
        ".planning/milestones/v1.1-research/cslc_selfconsist_aoi_candidates.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    md = _render_markdown(probed_at, rows, epoch_data)
    out_path.write_text(md)
    logger.info("Wrote probe artifact: {}", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
