"""Offline structural tests for the Phase 8 CSLC AOI probe artifact."""
from __future__ import annotations

from datetime import datetime, timezone


def _epochs() -> list[datetime]:
    return [datetime(2024, 1, 1 + i, 12, 0, tzinfo=timezone.utc) for i in range(15)]


def test_rendered_artifact_has_required_sections_and_no_synthetic_fallback() -> None:
    from scripts.probe_cslc_aoi_candidates import render_markdown

    accepted = []
    required_names = [
        ("SoCal", "locked anchor", "NAM"),
        ("Mojave/Coso-Searles", "Mojave fallback", "NAM"),
        ("Mojave/Pahranagat", "Mojave fallback", "NAM"),
        ("Mojave/Amargosa", "Mojave fallback", "NAM"),
        ("Mojave/Hualapai", "Mojave fallback", "NAM"),
        ("Iberian Meseta-North", "EU primary", "EU"),
        ("EU fallback Ebro Basin", "EU fallback", "EU"),
        ("EU fallback La Mancha", "EU fallback", "EU"),
    ]
    for index, (aoi, category, region) in enumerate(required_names):
        accepted.append(
            {
                "aoi": aoi,
                "category": category,
                "region": region,
                "regime": "test-regime",
                "bbox": (-1.0, 1.0, -0.5, 1.5),
                "candidate_burst_id": f"t000_00000{index}_iw1",
                "opera_cslc_coverage_2024_2025": 15,
                "egms_l2a_stable_ps_ceiling": 1000 if region == "EU" else None,
                "expected_stable_pct_per_worldcover": 0.2,
                "epochs": _epochs(),
                "acquisition_ids": [f"S1A_TEST_{index}_{i:02d}" for i in range(15)],
            }
        )

    artifact = render_markdown(
        probed_at="2026-04-30T00:00:00Z",
        accepted=accepted,
        rejected=[
            {
                "aoi": "Iberian/Alentejo",
                "reason": "v1.1 burst binding was stale",
                "evidence": "test evidence",
            }
        ],
    )

    for aoi, _, _ in required_names:
        assert aoi in artifact
    assert artifact.count("| EU fallback ") >= 2
    assert "SYNTHETIC FALLBACK" not in artifact
    assert "## Rejected Candidates" in artifact
    assert "## Query Parameters" in artifact
    assert "## Selected Sensing Windows" in artifact


def test_probe_output_path_is_v12_artifact() -> None:
    from scripts.probe_cslc_aoi_candidates import OUTPUT_PATH

    assert OUTPUT_PATH.as_posix().endswith(
        ".planning/milestones/v1.2-research/cslc_gate_promotion_aoi_candidates.md"
    )
