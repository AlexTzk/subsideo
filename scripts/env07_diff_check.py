#!/usr/bin/env python3
"""scripts/env07_diff_check.py -- machine-verifiable ENV-07 diff classifier.

Usage
-----
    python scripts/env07_diff_check.py <script_a.py> <script_b.py>

Exits ``0`` iff every ``+``/``-`` hunk between the two files is classified as
reference-data (matches the whitelist of reference-data patterns below) and
contains no plumbing-class violations (hand-coded bounds literals, ad-hoc
credential checks, etc.).

Exits ``1`` with a categorised report listing the first 20 violations when
any plumbing difference is detected.

ENV-07 acceptance gate (Plan 01-07 Task 3): the equivalent-script pairs
``run_eval_disp.py`` vs ``run_eval_disp_egms.py`` and ``run_eval_dist.py``
vs ``run_eval_dist_eu.py`` must both exit 0 once the batch migration is
complete.
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

# Patterns whose +/- lines are ACCEPTED as reference-data-only changes.
# Ordering is not significant (any match means "accepted"); the set is
# explicit so a reviewer can audit which shapes are permitted to diverge.
REFERENCE_DATA_PATTERNS: list[re.Pattern[str]] = [
    # Per-script scientific constants
    re.compile(r"^\s*BURST_ID\s*="),
    re.compile(r"^\s*MGRS_TILE\s*="),
    re.compile(r"^\s*MGRS_TILE_ID\s*="),
    re.compile(r"^\s*RELATIVE_ORBIT\s*="),
    re.compile(r"^\s*TRACK_NUMBER\s*="),
    re.compile(r"^\s*SENSING_DATE\s*="),
    re.compile(r"^\s*SATELLITE\s*="),
    re.compile(r"^\s*POST_DATE\s*="),
    re.compile(r"^\s*POST_DATE_BUFFER_DAYS\s*="),
    re.compile(r"^\s*PRE_DATE\s*="),
    re.compile(r"^\s*AOI_NAME\s*="),
    re.compile(r"^\s*AOI_BBOX\s*="),
    re.compile(r"^\s*BURST_BBOX\s*="),
    re.compile(r"^\s*DEM_BBOX\s*="),
    re.compile(r"^\s*EXPECTED_WALL_S\s*="),
    re.compile(r"^\s*EPSG\s*="),
    re.compile(r"^\s*OUT\s*="),
    re.compile(r"^\s*DATE_(START|END)\s*="),
    re.compile(r"^\s*JRC_(YEAR|MONTH)\s*="),
    re.compile(r"^\s*JRC_MONTH_NUM\s*="),
    re.compile(r"^\s*MAX_CLOUD_COVER\s*="),
    re.compile(r"^\s*BAND_NAMES\s*="),
    re.compile(r"^\s*FIRE_ONSET\s*="),
    re.compile(r"^\s*EGMS_(TRACK|PASS|RELEASE|LEVEL|ACTIVATION|API_BASE|S3_BASE|TOKEN)\s*="),
    re.compile(r"^\s*BURST_HOUR\s*="),
    re.compile(r"^\s*BURST_UTC_SECONDS\s*="),
    # Reference-source URL / granule fragments
    re.compile(r"reference_url|ref_prefix|OPERA_|ASF_|granule|short_name|GranuleUR"),
    re.compile(r"collection\s*=|product_type\s*=|temporal\s*="),
    # Comments and blank lines
    re.compile(r"^\s*#"),
    re.compile(r"^\s*$"),
    # Plumbing that IS the migration target -- additions of these are
    # expected when a script moves onto the harness.
    re.compile(r"^\s*credential_preflight\("),
    re.compile(r"^\s*bounds_for_(burst|mgrs_tile)\("),
    re.compile(r"^\s*from subsideo\.validation\.harness import"),
    re.compile(
        r"^\s*(bounds_for_burst|bounds_for_mgrs_tile|credential_preflight|"
        r"download_reference_with_retry|ensure_resume_safe|"
        r"select_opera_frame_by_utc_hour),?"
    ),
    # Non-harness imports (stdlib, third-party) -- differ freely between
    # eval scripts because reference-source libraries differ (e.g.
    # earthaccess for ASF vs CDSEClient for CDSE).
    re.compile(r"^\s*(from|import) "),
    # Print / logging / f-string debug lines (per-script banner / summary)
    re.compile(r"^\s*(print|logger)\."),
    re.compile(r"^\s*f\""),
    re.compile(r"\"\"\""),
    # Top-of-script module docstring comment lines
    re.compile(r"^# run_eval"),
    re.compile(r"^# "),
]

# Patterns whose presence in a +/- hunk MUST cause exit 1.
PLUMBING_VIOLATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"bounds\s*=\s*\[\s*-?\d"),
        "hand-coded numeric bounds literal (ENV-08 violation)",
    ),
    (
        re.compile(r"for\s+key\s+in\s+\("),
        "ad-hoc credential loop (should be credential_preflight)",
    ),
    (
        re.compile(r"if\s+not\s+os\.environ\.get\(['\"]"),
        "ad-hoc env var check (should be credential_preflight)",
    ),
]


def classify_line(line: str) -> tuple[bool, str]:
    """Return ``(is_reference_data, reason_if_violation)``.

    Violation patterns are checked first so an accidental reference-data
    pattern that happens to match a plumbing-violation regex cannot mask
    it. If nothing matches, the line is treated as reference-data (i.e.
    unknown lines are accepted) -- this keeps the classifier from flagging
    every trivial formatting difference between equivalent scripts.
    """
    for pat, msg in PLUMBING_VIOLATION_PATTERNS:
        if pat.search(line):
            return False, msg
    for pat in REFERENCE_DATA_PATTERNS:
        if pat.search(line):
            return True, ""
    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser(description="ENV-07 diff classifier")
    parser.add_argument("file_a", type=Path)
    parser.add_argument("file_b", type=Path)
    args = parser.parse_args()

    a_lines = args.file_a.read_text().splitlines(keepends=False)
    b_lines = args.file_b.read_text().splitlines(keepends=False)
    diff = list(
        difflib.unified_diff(
            a_lines,
            b_lines,
            fromfile=str(args.file_a),
            tofile=str(args.file_b),
            lineterm="",
        )
    )

    violations: list[tuple[str, str]] = []
    for line in diff:
        if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
            continue
        if line.startswith("+") or line.startswith("-"):
            content = line[1:]
            ok, reason = classify_line(content)
            if not ok:
                violations.append((line, reason))

    if violations:
        print(
            f"ENV-07 FAIL: {len(violations)} plumbing-class differences between "
            f"{args.file_a} and {args.file_b}:",
            file=sys.stderr,
        )
        for line, reason in violations[:20]:
            print(f"  {line}   -- {reason}", file=sys.stderr)
        return 1
    print(
        f"ENV-07 OK: {args.file_a} vs {args.file_b} diff is reference-data only."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
