"""One-shot helper: query OPERA L2 RTC granules per regime AOI and derive
concrete burst_ids from the granule names.

OPERA RTC granule naming: ``OPERA_L2_RTC-S1_T<track>-<burstnum>-IW<swath>_...``
which contains the burst_id directly. ``opera_utils.get_burst_id`` normalises
this to the lowercase JPL form ``t<track>_<burstnum>_iw<swath>`` that
``run_eval_rtc_eu.py::BURSTS`` expects.

This is a Task 2 sub-deliverable for Plan 02-05 continuation after the
Task 1 checkpoint (user selected ``lgtm-proceed-after-probe``). It bridges
the gap between the probe artifact (which reports SLC best-match granules
but not burst_ids) and the BURSTS literal in run_eval_rtc_eu.py.
"""
from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path
from typing import NamedTuple

from dotenv import load_dotenv


class Regime(NamedTuple):
    name: str
    bbox: tuple[float, float, float, float]
    expected_relorb: int | None
    centroid_lat: float


REGIMES: list[Regime] = [
    Regime("Alpine", (9.5, 46.0, 10.5, 46.7), 66, 46.35),
    Regime("Scandinavian", (20.5, 66.8, 22.5, 67.5), 29, 67.15),
    Regime("Iberian", (-4.0, 40.8, -3.0, 41.5), 154, 41.15),
    Regime("TemperateFlat", (11.0, 44.2, 11.8, 44.8), 117, 44.50),
    Regime("Fire", (-8.6, 40.4, -7.8, 41.0), 154, 40.70),
]


def _granule_burst_id(name: str) -> str | None:
    """Extract burst_id from an OPERA RTC granule name."""
    from opera_utils import get_burst_id

    try:
        return get_burst_id(name)
    except Exception:  # noqa: BLE001
        return None


def _dominant_burst_id(names: list[str]) -> tuple[str | None, int, list[tuple[str, int]]]:
    """Return (most_common_burst_id, count, top_3_tally)."""
    bids = [b for b in (_granule_burst_id(n) for n in names) if b]
    if not bids:
        return None, 0, []
    tally = Counter(bids).most_common()
    return tally[0][0], tally[0][1], tally[:3]


def _pick_sensing_utc_for_burst(names: list[str], burst_id: str) -> str | None:
    """From granules whose burst_id matches, find the 2024 summer best-match sensing time."""
    import earthaccess  # noqa: F401  (just to keep namespace)

    matches: list[tuple[str, str]] = []  # (sensing_time, granule_name)
    for n in names:
        if _granule_burst_id(n) != burst_id:
            continue
        # OPERA RTC name: OPERA_L2_RTC-S1_T<track>-<burst>-IW<sw>_YYYYMMDDTHHMMSSZ_...
        parts = n.split("_")
        # Find the ISO-like token
        for p in parts:
            if len(p) >= 16 and p.endswith("Z") and "T" in p:
                matches.append((p, n))
                break
    if not matches:
        return None
    # Prefer earliest 2024-summer (May-Oct)
    summer = [(t, n) for (t, n) in matches if t.startswith("2024") and "2024-05" <= f"{t[:4]}-{t[4:6]}" <= "2024-10"]
    if summer:
        t, _n = min(summer, key=lambda x: x[0])
    else:
        t, _n = min(matches, key=lambda x: x[0])
    # Render as YYYY-MM-DDTHH:MM:SSZ
    return f"{t[:4]}-{t[4:6]}-{t[6:8]}T{t[9:11]}:{t[11:13]}:{t[13:15]}Z"


def _search_opera_rtc(bbox: tuple[float, float, float, float]) -> list[str]:
    """Return list of OPERA L2 RTC granule names over bbox for 2024 summer."""
    import earthaccess

    results = earthaccess.search_data(
        short_name="OPERA_L2_RTC-S1_V1",
        temporal=("2024-05-01", "2024-10-31"),
        bounding_box=bbox,
    )
    # Each result is a DataGranule; pull name from umm "GranuleUR"
    names: list[str] = []
    for r in results:
        try:
            # DataGranule subclasses dict; the GranuleUR lives under umm.GranuleUR
            names.append(r["umm"]["GranuleUR"])
        except (KeyError, TypeError):
            # fallback: use __repr__ to scrape
            s = str(r)
            if "OPERA_L2_RTC-S1" in s:
                for tok in s.split():
                    if tok.startswith("OPERA_L2_RTC-S1"):
                        names.append(tok.strip("',\""))
                        break
    return names


def main() -> int:
    load_dotenv()
    if not os.environ.get("EARTHDATA_USERNAME") or not os.environ.get("EARTHDATA_PASSWORD"):
        print("ERROR: EARTHDATA creds missing", file=sys.stderr)
        return 1

    import earthaccess

    try:
        earthaccess.login(strategy="environment")
    except Exception as e:  # noqa: BLE001
        print(f"earthaccess.login failed: {e}", file=sys.stderr)
        return 2

    out_path = Path("/tmp/rtc_eu_burst_ids_derived.txt")
    with out_path.open("w") as fh:
        fh.write("# Derived burst_ids from OPERA L2 RTC granule catalog (2024 summer)\n\n")
        for regime in REGIMES:
            print(f"- {regime.name}: searching OPERA RTC over {regime.bbox}")
            names = _search_opera_rtc(regime.bbox)
            if not names:
                msg = f"{regime.name}: NO granules returned for bbox={regime.bbox}"
                print(f"  ! {msg}")
                fh.write(f"{msg}\n")
                continue
            dominant, count, top3 = _dominant_burst_id(names)
            if dominant is None:
                msg = f"{regime.name}: granules returned but no burst_id extractable"
                print(f"  ! {msg}")
                fh.write(f"{msg}\n")
                continue
            sensing = _pick_sensing_utc_for_burst(names, dominant)
            msg = (
                f"{regime.name}: total={len(names)} "
                f"dominant={dominant} (occurrences={count})"
                f" top3={top3}"
                f" best_sensing_utc={sensing}"
            )
            print(f"  {msg}")
            fh.write(msg + "\n")
    print(f"\nWrote: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
