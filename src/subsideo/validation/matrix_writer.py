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
    matching CONTEXT.md Claude's Discretion -- no-gate cells show em-dash).
    Cells with ANY CALIBRATING criterion are italicised as a whole (GATE-03).

    INVESTIGATION_TRIGGER criteria (Phase 2 D-13) are silently filtered out:
    they are non-gate markers and must NOT render a PASS/FAIL verdict in
    the default PQ/RA columns. In practice, eval scripts should never add
    them to a ReferenceAgreementResult.criterion_ids list, but this filter
    provides defence-in-depth (an accidental inclusion renders as if the
    criterion wasn't there, rather than producing a misleading verdict).
    """
    if result is None or not result.criterion_ids:
        return "—"
    gate_cids = [
        cid for cid in result.criterion_ids
        if CRITERIA.get(cid) is not None
        and CRITERIA[cid].type != "INVESTIGATION_TRIGGER"
    ]
    if not gate_cids:
        return "—"
    rendered = [_render_measurement(cid, result.measurements) for cid in gate_cids]
    any_calibrating = any(
        CRITERIA[cid].type == "CALIBRATING" for cid in gate_cids
    )
    body = " / ".join(rendered)
    return f"*{body}*" if any_calibrating else body


def _escape_table_cell(text: str) -> str:
    """Escape pipe characters so one cell's text cannot split the Markdown table."""
    return text.replace("|", "\\|")


def _validate_metrics_path(
    metrics_path_str: str, manifest_path: Path
) -> Path:
    """Resolve *metrics_path_str* and enforce an allow-list (WR-08).

    Accepts paths that resolve inside either the current working directory or
    the manifest's parent directory tree. Rejects anything outside that
    allow-list (e.g. ``../../../etc/passwd``) so a malicious manifest cannot
    trigger reads of arbitrary filesystem paths via ``matrix_writer``.
    """
    resolved = Path(metrics_path_str).resolve()
    allowed_roots = [
        Path.cwd().resolve(),
        manifest_path.resolve().parent,
    ]
    for root in allowed_roots:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise ValueError(
        f"manifest {manifest_path}: cell metrics_file {metrics_path_str!r} "
        f"resolves outside the allowed roots ({[str(r) for r in allowed_roots]}); "
        f"resolved to {resolved}; refusing to load."
    )


# --- RTC-EU multi-burst aggregate rendering (Phase 2 D-11, D-15) ---


def _is_rtc_eu_shape(metrics_path: Path) -> bool:
    """Return True when the metrics.json has a top-level ``per_burst`` key.

    Cheap schema-discrimination check (D-11 marker). Inspects the raw JSON
    rather than relying on Pydantic validation so that ``_load_metrics``
    (which parses against the base ``MetricsJson`` with ``extra="forbid"``)
    is never asked to validate RTCEUCellMetrics-only fields. Returns False
    on any I/O or JSON error -- the caller falls through to the default
    cell-render path, which then surfaces RUN_FAILED if the file is
    genuinely malformed.
    """
    import json as _json

    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.debug("_is_rtc_eu_shape: cannot read {}: {}", metrics_path, e)
        return False
    return isinstance(raw, dict) and "per_burst" in raw


def _render_rtc_eu_cell(
    metrics_path: Path,
) -> tuple[str, str] | None:
    """Render RTC-EU multi-burst aggregate as ``(pq_col, ra_col)``.

    Returns None if the metrics.json cannot be parsed as RTCEUCellMetrics
    (the caller should fall through to RUN_FAILED rendering). Returns a
    tuple of pre-escape column strings when successful; the caller applies
    ``_escape_table_cell`` to each column before emitting the Markdown row.

    pq_col is always the em-dash literal because RTC has no product-quality
    gate in v1.1 (Phase 1 D-04; Phase 2 specifics "No product-quality gate
    for RTC in v1.1").

    ra_col format: ``{pass_count}/{total} PASS`` (or ``... PASS`` + warning
    glyph when ``any_investigation_required`` is True, per D-15). When
    ``pass_count < total``, format is ``X/N PASS (Y FAIL)`` so the matrix
    reader sees at a glance there are failing rows without having to open
    the CONCLUSIONS document.
    """
    from subsideo.validation.matrix_schema import RTCEUCellMetrics

    try:
        metrics = RTCEUCellMetrics.model_validate_json(metrics_path.read_text())
    except Exception as e:  # pydantic.ValidationError or JSON decode error
        logger.warning(
            "Failed to parse RTCEUCellMetrics from {}: {}", metrics_path, e
        )
        return None

    fail_count = metrics.total - metrics.pass_count
    if fail_count > 0:
        base = f"{metrics.pass_count}/{metrics.total} PASS ({fail_count} FAIL)"
    else:
        base = f"{metrics.pass_count}/{metrics.total} PASS"

    # Use Python unicode escape form (U+26A0 WARNING SIGN) so the source
    # byte-level payload is ASCII-only and deterministic across editors,
    # terminals, and git diff. The cross-file convention is: matrix_writer.py
    # uses the escape form (grep-anchorable, ASCII source bytes);
    # run_eval_rtc_eu.py (Plan 02-04) may use the literal glyph inline where
    # readable log tails benefit. Both forms compile to the same ``str``
    # object at runtime and render identically in the rendered matrix cell.
    warn = " \u26a0" if metrics.any_investigation_required else ""
    ra_col = f"{base}{warn}"
    pq_col = "—"
    return pq_col, ra_col


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
        # WR-08: validate metrics_file path before touching the filesystem so
        # a malicious manifest cannot coax matrix_writer into reading
        # arbitrary files (e.g. ``../../../etc/passwd``).
        metrics_path = _validate_metrics_path(
            str(cell["metrics_file"]), manifest_path
        )

        # Phase 2 D-11 branch: metrics.json with a ``per_burst`` key is the
        # RTCEUCellMetrics shape -- render as ``X/N PASS`` aggregate plus a
        # warning glyph when any_investigation_required (D-15). Cell schema
        # discriminator lives in the JSON itself (not the manifest) so that
        # adding a per-burst shape to other cells in a future phase only
        # requires a per-cell metrics.json edit. Check BEFORE ``_load_metrics``
        # because the base ``MetricsJson`` uses ``extra="forbid"`` and would
        # reject the RTCEUCellMetrics-specific fields; ``_render_rtc_eu_cell``
        # validates against the correct subclass.
        if metrics_path.exists() and _is_rtc_eu_shape(metrics_path):
            cols = _render_rtc_eu_cell(metrics_path)
            if cols is not None:
                pq_col, ra_col = cols
                lines.append(
                    f"| {product} | {region} | {_escape_table_cell(pq_col)} | "
                    f"{_escape_table_cell(ra_col)} |"
                )
                continue
            # Fall through to default rendering as a best-effort if the
            # RTCEUCellMetrics validation failed (``_render_rtc_eu_cell``
            # already logged the reason via ``logger.warning``). The default
            # path below will surface a RUN_FAILED cell since base
            # ``MetricsJson`` will also reject the mis-shaped payload.

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
