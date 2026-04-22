"""Read results/matrix_manifest.yml + per-cell {meta,metrics}.json sidecars,
write results/matrix.md with a two-column layout (product-quality +
reference-agreement), echoing ``CRITERIA`` thresholds alongside measured
values for drift visibility (D-03 matrix-echo).

NEVER parses CONCLUSIONS_*.md (PITFALLS R3 / R5). Missing or malformed
sidecars render as ``RUN_FAILED`` (ENV-09 per-cell isolation).

CALIBRATING cells are rendered in italics (Markdown ``*...*``) -- visually
distinct from BINDING cells (GATE-03). Every rendered measurement carries
its comparator, threshold, and PASS/FAIL verdict so that a criteria.py
threshold edit produces a visible diff of ``results/matrix.md`` under git.

Invocation:
    python -m subsideo.validation.matrix_writer \\
        --manifest results/matrix_manifest.yml \\
        --out results/matrix.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from subsideo.validation.criteria import CRITERIA
from subsideo.validation.matrix_schema import MetricsJson
from subsideo.validation.results import (
    ProductQualityResult,
    ReferenceAgreementResult,
    measurement_key,
)


def _load_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    """Read and validate the manifest cells list."""
    data = yaml.safe_load(manifest_path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{manifest_path}: expected top-level mapping, got {type(data).__name__}")
    if "cells" not in data or not isinstance(data["cells"], list):
        raise ValueError(f"{manifest_path}: missing or invalid 'cells' list")
    return data["cells"]


def _load_metrics(metrics_path: Path) -> tuple[MetricsJson | None, str | None]:
    """Load a metrics.json sidecar; return (parsed, error_reason).

    If the file is missing or invalid, the parsed value is None and
    error_reason is a short human-readable explanation suitable for
    rendering in the RUN_FAILED cell text.
    """
    if not metrics_path.exists():
        return None, f"{metrics_path.name} missing"
    try:
        return MetricsJson.model_validate_json(metrics_path.read_text()), None
    except Exception as e:  # pydantic.ValidationError or JSON decode error
        logger.warning("Failed to parse {}: {}", metrics_path, e)
        return None, f"{metrics_path.name} invalid"


_COMPARATOR_FNS = {
    ">": lambda a, b: float(a) > float(b),
    ">=": lambda a, b: float(a) >= float(b),
    "<": lambda a, b: float(a) < float(b),
    "<=": lambda a, b: float(a) <= float(b),
}


def _render_measurement(cid: str, measurements: dict[str, float]) -> str:
    """Return ``value (<op> threshold VERDICT)`` for one criterion.

    For CALIBRATING criteria, appends ``(CALIBRATING)`` to the verdict so
    both the outer italics AND the inline tag tell the reader this is
    not a release-gating number (D-03 + GATE-03 belt-and-braces).
    """
    crit = CRITERIA.get(cid)
    if crit is None:
        return f"UNKNOWN_CRITERION:{cid}"
    mkey = measurement_key(cid)
    if mkey not in measurements:
        return f"MEASUREMENT_MISSING:{mkey}"
    val = float(measurements[mkey])
    passed = _COMPARATOR_FNS[crit.comparator](val, crit.threshold)
    verdict = "PASS" if passed else "FAIL"
    if crit.type == "CALIBRATING":
        verdict = f"{verdict} (CALIBRATING)"
    return f"{val:.4g} ({crit.comparator} {crit.threshold:.4g} {verdict})"


def _render_cell_column(
    result: ProductQualityResult | ReferenceAgreementResult | None,
) -> str:
    """Render one side of a cell (product-quality or reference-agreement column).

    Returns an em-dash when there are no criteria to evaluate (empty side,
    matching CONTEXT.md §Claude's Discretion -- no-gate cells show '—').
    Cells with ANY CALIBRATING criterion are italicised as a whole (GATE-03).
    """
    if result is None or not result.criterion_ids:
        return "—"
    rendered = [_render_measurement(cid, result.measurements) for cid in result.criterion_ids]
    any_calibrating = any(
        CRITERIA.get(cid) is not None and CRITERIA[cid].type == "CALIBRATING"
        for cid in result.criterion_ids
    )
    body = " / ".join(rendered)
    return f"*{body}*" if any_calibrating else body


def _escape_table_cell(text: str) -> str:
    """Escape pipe characters so one cell's text cannot split the Markdown table."""
    return text.replace("|", "\\|")


def write_matrix(manifest_path: Path, out_path: Path) -> None:
    """Read manifest + sidecars; write a two-column-per-cell Markdown table.

    Per ENV-09: missing per-cell metrics.json sidecars render as ``RUN_FAILED``
    without interrupting the rest of the matrix. Per D-03: each measurement
    is printed alongside its criterion's comparator + threshold + verdict.
    Per GATE-03: CALIBRATING cells wrap in Markdown italics.
    """
    cells = _load_manifest(manifest_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        "# subsideo v1.1 Results Matrix",
        "",
        f"Manifest: `{manifest_path}`",
        "",
        (
            "CALIBRATING cells are *italicised*. See `validation/criteria.py` for "
            "the 13-entry criterion registry; every measurement is echoed alongside "
            "its criterion's threshold (D-03 drift visibility)."
        ),
        "",
        "| Product | Region | Product-quality | Reference-agreement |",
        "|---------|--------|------------------|---------------------|",
    ]

    for cell in cells:
        product = str(cell["product"]).upper()
        region = str(cell["region"]).upper()
        metrics_path = Path(cell["metrics_file"])
        metrics, err_reason = _load_metrics(metrics_path)
        if metrics is None:
            pq_col = f"RUN_FAILED ({err_reason})"
            ra_col = "RUN_FAILED"
            lines.append(
                f"| {product} | {region} | {_escape_table_cell(pq_col)} | "
                f"{_escape_table_cell(ra_col)} |"
            )
            continue
        pq_result = ProductQualityResult(
            measurements=dict(metrics.product_quality.measurements),
            criterion_ids=list(metrics.product_quality.criterion_ids),
        )
        ra_result = ReferenceAgreementResult(
            measurements=dict(metrics.reference_agreement.measurements),
            criterion_ids=list(metrics.reference_agreement.criterion_ids),
        )
        pq_col = _escape_table_cell(_render_cell_column(pq_result))
        ra_col = _escape_table_cell(_render_cell_column(ra_result))
        lines.append(f"| {product} | {region} | {pq_col} | {ra_col} |")

    out_path.write_text("\n".join(lines) + "\n")
    logger.info("results/matrix.md written: {} cells", len(cells))


def main() -> int:
    """CLI entry point: ``python -m subsideo.validation.matrix_writer``."""
    parser = argparse.ArgumentParser(description="subsideo results matrix writer")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("results/matrix_manifest.yml"),
        help="Path to manifest YAML",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("results/matrix.md"),
        help="Output markdown path",
    )
    args = parser.parse_args()
    try:
        write_matrix(args.manifest, args.out)
    except Exception as e:
        logger.error("matrix_writer failed: {}", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
