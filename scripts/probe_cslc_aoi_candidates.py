"""Probe Phase 8/v1.2 CSLC self-consistency AOI candidates.

The canonical output is:

  .planning/milestones/v1.2-research/cslc_gate_promotion_aoi_candidates.md

Unlike the v1.1 probe, this script never fabricates selected sensing windows.
AOIs with fewer than 15 acquisition-backed ASF timestamps are written to the
Rejected Candidates section with the observed evidence.
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

OUTPUT_PATH = Path(
    ".planning/milestones/v1.2-research/cslc_gate_promotion_aoi_candidates.md"
)
ASF_START = "2024-01-01T00:00:00Z"
ASF_END = "2024-06-30T23:59:59Z"
OPERA_START = "2024-01-01"
OPERA_END = "2025-12-31"


@dataclass(frozen=True)
class CandidateAOI:
    """Declarative definition of one AOI probe candidate."""

    aoi: str
    category: str
    region: str
    regime: str
    label: str
    bbox: tuple[float, float, float, float]
    burst_hint: str | None
    published_insar_stability_ref: str
    expected_stable_pct_per_worldcover: float


CANDIDATES: list[CandidateAOI] = [
    CandidateAOI(
        aoi="SoCal",
        category="locked anchor",
        region="NAM",
        regime="coastal-transverse-range",
        label="Santa Ynez / SoCal CSLC calibration anchor",
        bbox=(-120.40, 34.15, -119.65, 34.75),
        burst_hint="t144_308029_iw1",
        published_insar_stability_ref="v1.1 CSLC self-consistency anchor",
        expected_stable_pct_per_worldcover=0.20,
    ),
    CandidateAOI(
        aoi="Mojave/Coso-Searles",
        category="Mojave fallback",
        region="NAM",
        regime="desert-bedrock-playa-adjacent",
        label="Coso Volcanic Field / Searles Valley",
        bbox=(-117.80, 35.65, -117.30, 36.05),
        burst_hint="t064_135527_iw2",
        published_insar_stability_ref="Monastero et al. 2005; Coso stable ridges",
        expected_stable_pct_per_worldcover=0.35,
    ),
    CandidateAOI(
        aoi="Mojave/Pahranagat",
        category="Mojave fallback",
        region="NAM",
        regime="desert-bedrock",
        label="Pahranagat Valley",
        bbox=(-115.35, 37.10, -115.00, 37.45),
        burst_hint="t173_370296_iw2",
        published_insar_stability_ref="Schwing et al. 2022; Basin-and-Range InSAR stability",
        expected_stable_pct_per_worldcover=0.30,
    ),
    CandidateAOI(
        aoi="Mojave/Amargosa",
        category="Mojave fallback",
        region="NAM",
        regime="desert-bedrock-playa-adjacent",
        label="Amargosa Valley",
        bbox=(-116.60, 36.30, -116.25, 36.65),
        burst_hint="t064_135530_iw3",
        published_insar_stability_ref="Sneed et al. 2003; stable bedrock sides",
        expected_stable_pct_per_worldcover=0.25,
    ),
    CandidateAOI(
        aoi="Mojave/Hualapai",
        category="Mojave fallback",
        region="NAM",
        regime="plateau-bedrock",
        label="Hualapai Plateau",
        bbox=(-113.70, 35.50, -113.20, 35.90),
        burst_hint="t100_213507_iw2",
        published_insar_stability_ref="Chaussard et al. 2014; Colorado Plateau edge",
        expected_stable_pct_per_worldcover=0.40,
    ),
    CandidateAOI(
        aoi="Iberian Meseta-North",
        category="EU primary",
        region="EU",
        regime="iberian-meseta-sparse-vegetation",
        label="Iberian Meseta north of Madrid",
        bbox=(-4.00, 40.80, -3.40, 41.30),
        burst_hint="t103_219329_iw1",
        published_insar_stability_ref="Tomas et al. 2014; Segovia/Soria stability",
        expected_stable_pct_per_worldcover=0.20,
    ),
    CandidateAOI(
        aoi="EU fallback Ebro Basin",
        category="EU fallback",
        region="EU",
        regime="semi-arid-basin",
        label="Ebro Basin / Zaragoza dryland",
        bbox=(-1.20, 41.35, -0.55, 41.85),
        burst_hint=None,
        published_insar_stability_ref="EGMS coverage over semi-arid Ebro Basin",
        expected_stable_pct_per_worldcover=0.22,
    ),
    CandidateAOI(
        aoi="EU fallback La Mancha",
        category="EU fallback",
        region="EU",
        regime="interior-spanish-plateau",
        label="La Mancha dry plateau",
        bbox=(-3.45, 39.05, -2.80, 39.55),
        burst_hint=None,
        published_insar_stability_ref="EGMS coverage over low-relief interior Spain",
        expected_stable_pct_per_worldcover=0.24,
    ),
]

LEGACY_REJECTIONS = [
    {
        "aoi": "Iberian/Alentejo",
        "reason": "v1.1 burst binding was stale",
        "evidence": "run_eval_cslc_selfconsist_eu.py notes t008_016940_iw2 maps outside the intended Portugal AOI",
    },
    {
        "aoi": "Iberian/MassifCentral",
        "reason": "v1.1 burst binding was stale",
        "evidence": "run_eval_cslc_selfconsist_eu.py notes t131_279647_iw2 maps outside the intended France AOI",
    },
]


def count_opera_cslc_granules(bbox: tuple[float, float, float, float]) -> int:
    """Count OPERA CSLC-S1 granules over bbox; return 0 on auth/network failure."""
    try:
        import earthaccess

        results = earthaccess.search_data(
            short_name="OPERA_L2_CSLC-S1_V1",
            bounding_box=bbox,
            temporal=(OPERA_START, OPERA_END),
        )
        return len(list(results))
    except Exception as exc:  # noqa: BLE001
        logger.warning("OPERA CSLC count failed for bbox={}: {}", bbox, exc)
        return 0


def derive_dominant_burst_id(bbox: tuple[float, float, float, float]) -> str | None:
    """Best-effort dominant OPERA burst id over bbox from OPERA CSLC filenames."""
    try:
        import earthaccess
        import opera_utils

        results = list(
            earthaccess.search_data(
                short_name="OPERA_L2_CSLC-S1_V1",
                bounding_box=bbox,
                temporal=(OPERA_START, "2024-12-31"),
                count=50,
            )
        )
        burst_ids: list[str] = []
        for result in results:
            for link in result.data_links()[:1]:
                try:
                    burst_ids.append(opera_utils.get_burst_id(link.split("/")[-1]).lower())
                except Exception:  # noqa: BLE001
                    continue
        if not burst_ids:
            return None
        return Counter(burst_ids).most_common(1)[0][0]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Dominant burst derivation failed for bbox={}: {}", bbox, exc)
        return None


def count_egms_stable_ps_ceiling(
    bbox: tuple[float, float, float, float],
    region: str,
) -> int | None:
    """Return a bounded back-of-envelope EGMS stable PS ceiling for EU AOIs."""
    if region != "EU":
        return None
    west, south, east, north = bbox
    lat_km = (north - south) * 111.0
    lon_km = (east - west) * 111.0 * math.cos(math.radians((north + south) / 2.0))
    return int(lat_km * lon_km * 300.0 * 0.3)


def acquisition_window_for_candidate(
    candidate: CandidateAOI,
) -> tuple[list[datetime], list[str], str | None]:
    """Return acquisition-backed timestamps, identifiers, and a rejection reason."""
    try:
        import asf_search as asf

        west, south, east, north = candidate.bbox
        wkt = (
            f"POLYGON(({west} {south},{east} {south},"
            f"{east} {north},{west} {north},{west} {south}))"
        )
        results = asf.search(
            platform=asf.PLATFORM.SENTINEL1A,
            processingLevel=asf.PRODUCT_TYPE.SLC,
            beamMode="IW",
            intersectsWith=wkt,
            start=ASF_START,
            end=ASF_END,
        )
        by_date: dict[str, tuple[datetime, str]] = {}
        for result in results:
            start_time = result.properties.get("startTime")
            scene_name = result.properties.get("sceneName") or result.properties.get("fileName")
            if not start_time or not scene_name:
                continue
            try:
                parsed = datetime.fromisoformat(str(start_time).replace("Z", "+00:00"))
            except ValueError:
                continue
            by_date.setdefault(parsed.date().isoformat(), (parsed, str(scene_name)))

        selected = [by_date[key] for key in sorted(by_date)[:15]]
        if len(selected) < 15:
            return (
                [item[0] for item in selected],
                [item[1] for item in selected],
                f"ASF returned {len(selected)} unique S1A IW SLC acquisition dates in {ASF_START}..{ASF_END}; need 15",
            )
        return [item[0] for item in selected], [item[1] for item in selected], None
    except Exception as exc:  # noqa: BLE001
        return [], [], f"ASF query failed: {exc}"


def _fmt_time(value: datetime) -> str:
    if value.tzinfo is None:
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _render_window_table(epochs: list[datetime], identifiers: list[str]) -> str:
    lines = [
        "| # | sensing_utc | platform | acquisition_id |",
        "|---|-------------|----------|----------------|",
    ]
    for index, (epoch, identifier) in enumerate(zip(epochs, identifiers, strict=True), 1):
        lines.append(f"| {index} | {_fmt_time(epoch)} | S1A | `{identifier}` |")
    return "\n".join(lines) + "\n"


def render_markdown(
    *,
    probed_at: str,
    accepted: list[dict[str, object]],
    rejected: list[dict[str, str]],
) -> str:
    """Render the v1.2 canonical AOI probe artifact."""
    lines: list[str] = [
        "# CSLC Gate Promotion AOI Candidates -- v1.2 Probe Report",
        "",
        f"**Probed:** {probed_at}",
        "**Phase:** 8 (CSLC Gate Promotion & AOI Hardening)",
        "**Canonical output:** `.planning/milestones/v1.2-research/cslc_gate_promotion_aoi_candidates.md`",
        "",
        "## Query Parameters",
        "",
        f"- ASF SLC query window: `{ASF_START}` to `{ASF_END}`",
        f"- OPERA CSLC count window: `{OPERA_START}` to `{OPERA_END}`",
        "- ASF filters: platform `SENTINEL-1A`, processing level `SLC`, beam mode `IW`, bbox polygon intersects",
        "- Burst strategy: use locked burst hints where available; otherwise derive from OPERA names when possible and validate in eval setup",
        "- Acceptance rule: selected AOIs require 15 concrete acquisition-backed ASF timestamps; short or failed searches are rejected",
        "",
        "## Candidate AOIs",
        "",
        "| aoi | category | region | regime | candidate_burst_id | opera_cslc_coverage_2024_2025 | egms_l2a_stable_ps_ceiling | expected_stable_pct_per_worldcover |",
        "|-----|----------|--------|--------|--------------------|-------------------------------|----------------------------|------------------------------------|",
    ]
    for row in accepted:
        egms = row["egms_l2a_stable_ps_ceiling"]
        lines.append(
            f"| {row['aoi']} | {row['category']} | {row['region']} | {row['regime']} | "
            f"{row['candidate_burst_id']} | {row['opera_cslc_coverage_2024_2025']} | "
            f"{egms if egms is not None else 'n/a'} | "
            f"{float(row['expected_stable_pct_per_worldcover']):.2f} |"
        )

    lines.extend(
        [
            "",
            "## Selected Sensing Windows",
            "",
        ]
    )
    for row in accepted:
        lines.extend(
            [
                f"### {row['aoi']}",
                "",
                f"- category: {row['category']}",
                f"- candidate_burst_id: `{row['candidate_burst_id']}`",
                f"- bbox: `{row['bbox']}`",
                "",
                _render_window_table(
                    row["epochs"],  # type: ignore[arg-type]
                    row["acquisition_ids"],  # type: ignore[arg-type]
                ).rstrip(),
                "",
            ]
        )

    lines.extend(
        [
            "## Rejected Candidates",
            "",
            "| aoi | reason | evidence |",
            "|-----|--------|----------|",
        ]
    )
    for row in rejected:
        lines.append(f"| {row['aoi']} | {row['reason']} | {row['evidence']} |")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    """Run the live probe and write the v1.2 artifact."""
    load_dotenv()
    try:
        import earthaccess

        earthaccess.login(strategy="environment")
        logger.info("earthaccess login succeeded")
    except Exception as exc:  # noqa: BLE001
        logger.warning("earthaccess login failed; OPERA counts may be 0: {}", exc)

    probed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    accepted: list[dict[str, object]] = []
    rejected: list[dict[str, str]] = list(LEGACY_REJECTIONS)

    for candidate in CANDIDATES:
        logger.info("Probing {}", candidate.aoi)
        epochs, acquisition_ids, rejection_reason = acquisition_window_for_candidate(candidate)
        cslc_count = count_opera_cslc_granules(candidate.bbox)
        burst_id = candidate.burst_hint or derive_dominant_burst_id(candidate.bbox)
        if rejection_reason is not None:
            rejected.append(
                {
                    "aoi": candidate.aoi,
                    "reason": "insufficient acquisition-backed sensing window",
                    "evidence": rejection_reason,
                }
            )
            continue
        accepted.append(
            {
                "aoi": candidate.aoi,
                "category": candidate.category,
                "region": candidate.region,
                "regime": candidate.regime,
                "bbox": candidate.bbox,
                "candidate_burst_id": burst_id or "(derive from EU burst DB before eval)",
                "opera_cslc_coverage_2024_2025": cslc_count,
                "egms_l2a_stable_ps_ceiling": count_egms_stable_ps_ceiling(
                    candidate.bbox, candidate.region
                ),
                "expected_stable_pct_per_worldcover": candidate.expected_stable_pct_per_worldcover,
                "epochs": epochs,
                "acquisition_ids": acquisition_ids,
            }
        )

    md = render_markdown(probed_at=probed_at, accepted=accepted, rejected=rejected)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(md)
    logger.info("Wrote {}", OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
