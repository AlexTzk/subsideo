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
        milestone = crit.binding_after_milestone or "future milestone"
        verdict = f"{verdict} (CALIBRATING — binds {milestone})"
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


# --- Phase 3 CSLC self-consistency rendering (03-CONTEXT D-03 + D-06 + D-11) ---


def _is_cslc_selfconsist_shape(metrics_path: Path) -> bool:
    """Return True when the metrics.json has a top-level ``per_aoi`` key.

    Phase 3 D-11 schema discriminator. Checked BEFORE _is_rtc_eu_shape so a
    file that somehow contains both (defensive) is routed to the self-consist
    branch; the schemas are structurally disjoint so this is an invariant,
    not a guess.
    """
    import json as _json

    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.debug("_is_cslc_selfconsist_shape: cannot read {}: {}", metrics_path, e)
        return False
    return isinstance(raw, dict) and "per_aoi" in raw


def _render_cslc_selfconsist_cell(
    metrics_path: Path,
    *,
    region: str,
) -> tuple[str, str] | None:
    """Render a Phase 3 CSLC self-consistency cell as (pq_col, ra_col).

    Called for both cslc:nam (region='nam') and cslc:eu (region='eu'). The
    cell always italicises (CALIBRATING is the only valid status for first
    rollout per Phase 3 D-03 + GATE-05). Appends U+26A0 on any_blocker=True.

    PQ column worst-case-aggregate format:
        "X/N CALIBRATING | coh=A.AA / resid=B.B mm/yr (<worst_aoi>)"
    EU adds: " / egms_resid=C.C mm/yr" inside the metric group when any AOI
    carries ``egms_l2a_stable_ps_residual_mm_yr`` in its product_quality
    measurements.

    On MIXED cells (W8 fix — AOI attribution): the label reads
        "1/2 CALIBRATING, 1/2 BLOCKER | coh=0.78 / resid=2.1 mm/yr (SoCal)"
    The ``(<worst_aoi>)`` suffix disambiguates which AOI owns the coh/resid
    numbers when the cell is MIXED. Pipe ``|`` separates the status label
    from the metric block; parentheses carry the AOI name.
    """
    from subsideo.validation.matrix_schema import (
        CSLCSelfConsistEUCellMetrics,
        CSLCSelfConsistNAMCellMetrics,
    )

    try:
        cls = CSLCSelfConsistEUCellMetrics if region == "eu" else CSLCSelfConsistNAMCellMetrics
        metrics = cls.model_validate_json(metrics_path.read_text())
    except Exception as e:
        logger.warning(
            "Failed to parse CSLCSelfConsist*CellMetrics from {}: {}", metrics_path, e
        )
        return None

    # Status tally
    cal_count = sum(1 for r in metrics.per_aoi if r.status == "CALIBRATING")
    blocker_count = sum(1 for r in metrics.per_aoi if r.status == "BLOCKER")
    fail_count = sum(1 for r in metrics.per_aoi if r.status == "FAIL")
    tags = [f"{cal_count}/{metrics.total} CALIBRATING"]
    if blocker_count:
        tags.append(f"{blocker_count}/{metrics.total} BLOCKER")
    if fail_count:
        tags.append(f"{fail_count}/{metrics.total} FAIL")
    status_label = ", ".join(tags)
    status_label += " — binds v1.2"  # Phase 7 D-05

    # PQ worst-case across AOIs
    pq_agg = metrics.product_quality_aggregate
    worst_coh = pq_agg.get("worst_coherence_median_of_persistent")
    worst_resid = pq_agg.get("worst_residual_mm_yr")
    parts: list[str] = [
        f"coh={float(worst_coh):.2f}" if worst_coh is not None else "coh=—",
        f"resid={float(worst_resid):.1f} mm/yr" if worst_resid is not None else "resid=—",
    ]
    # EU extras: egms_l2a_stable_ps_residual_mm_yr
    if region == "eu":
        egms_vals = [
            r.product_quality.measurements.get("egms_l2a_stable_ps_residual_mm_yr")
            for r in metrics.per_aoi
            if r.product_quality is not None
        ]
        egms_finite = [v for v in egms_vals if v is not None]
        if egms_finite:
            worst_egms = max(abs(float(v)) for v in egms_finite)
            parts.append(f"egms_resid={worst_egms:.1f} mm/yr")

    # W8 fix: add worst-AOI attribution in parens + pipe-delimit status vs metrics.
    worst_aoi = str(pq_agg.get("worst_aoi") or "")
    metric_body = " / ".join(parts)
    if worst_aoi:
        metric_body = f"{metric_body} ({worst_aoi})"
    pq_body = f"{status_label} | {metric_body}"

    # RA aggregate
    ra_agg = metrics.reference_agreement_aggregate
    worst_r = ra_agg.get("worst_amp_r")
    worst_rmse = ra_agg.get("worst_amp_rmse_db")
    if worst_r is not None or worst_rmse is not None:
        ra_parts: list[str] = []
        if worst_r is not None:
            ra_parts.append(f"amp_r={float(worst_r):.2f}")
        if worst_rmse is not None:
            ra_parts.append(f"amp_rmse={float(worst_rmse):.1f} dB")
        ra_body = " / ".join(ra_parts)
    else:
        ra_body = "—"  # Mojave-only cells skip amplitude sanity (D-07)

    # Warning glyph on any_blocker (U+26A0)
    warn = " ⚠" if metrics.any_blocker else ""
    # Italicise as whole-body — CALIBRATING discipline (Phase 1 D-03 / GATE-03)
    pq_col = f"*{pq_body}*{warn}"
    ra_col = f"*{ra_body}*" if ra_body != "—" else "—"
    return pq_col, ra_col


# --- Phase 4 DISP rendering (CONTEXT D-12 + D-13 + D-19 + D-21) ---


def _is_disp_cell_shape(metrics_path: Path) -> bool:
    """Return True when the metrics.json has a top-level ``ramp_attribution`` key.

    Phase 4 D-11 schema discriminator. Checked BEFORE _is_cslc_selfconsist_shape
    (per_aoi) and _is_rtc_eu_shape (per_burst) because the DISP schema is
    structurally disjoint from both -- ``ramp_attribution`` is the unambiguous
    Phase 4 marker.
    """
    import json as _json

    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.debug("_is_disp_cell_shape: cannot read {}: {}", metrics_path, e)
        return False
    return isinstance(raw, dict) and "ramp_attribution" in raw


def _render_disp_cell(
    metrics_path: Path,
    *,
    region: str,
) -> tuple[str, str] | None:
    """Render a Phase 4 DISP cell as (pq_col, ra_col).

    Called for both disp:nam (region='nam') and disp:eu (region='eu'). PQ
    column always italicised (CALIBRATING per Phase 1 D-04 + Phase 4 D-19).
    RA column renders PASS/FAIL via the existing ``_render_measurement``
    helper (BINDING criteria; non-italics).

    PQ column format:
        "*coh=0.87 ([phase3-cached]) / resid=-0.1 mm/yr / attr=phass (CALIBRATING)*"
    RA column format (uses _render_measurement, e.g.):
        "0.04 (> 0.92 FAIL) / 23.6 (< 3 FAIL)"

    The ``attributed_source`` label is shown inline in the PQ column per
    CONTEXT D-13. The cell-level status (MIXED) is implicit from PQ italics
    plus RA non-italics (per Phase 4 D-19; matrix has no separate cell-status
    column in the v1.1 layout).

    Returns None on JSON parse failure so write_matrix() falls through to the
    default RUN_FAILED rendering.
    """
    from subsideo.validation.matrix_schema import DISPCellMetrics

    try:
        m = DISPCellMetrics.model_validate_json(metrics_path.read_text())
    except Exception as e:
        logger.warning(
            "Failed to parse DISPCellMetrics from {}: {}", metrics_path, e
        )
        return None

    # --- PQ side (italicised, CALIBRATING) ---
    pq = m.product_quality
    coh_med = pq.measurements.get("coherence_median_of_persistent")
    resid = pq.measurements.get("residual_mm_yr")
    src = pq.coherence_source  # 'phase3-cached' | 'fresh'
    attr = m.ramp_attribution.attributed_source

    parts: list[str] = []
    if coh_med is not None:
        parts.append(f"coh={float(coh_med):.2f} ([{src}])")
    else:
        parts.append("coh=—")
    if resid is not None:
        parts.append(f"resid={float(resid):+.1f} mm/yr")
    else:
        parts.append("resid=—")
    parts.append(f"attr={attr}")
    pq_body = " / ".join(parts)

    # CALIBRATING italics; warning glyph if cell_status == BLOCKER (mirrors
    # CSLC self-consist any_blocker convention)
    warn = " ⚠" if m.cell_status == "BLOCKER" else ""
    pq_col = (
        f"*{pq_body} (CALIBRATING — needs 3rd AOI before binding;"
        f" see DISP_UNWRAPPER_SELECTION_BRIEF.md)*{warn}"
    )

    # --- RA side (BINDING, non-italics) ---
    ra = m.reference_agreement
    rendered_ra: list[str] = []
    for cid in ra.criterion_ids:
        rendered_ra.append(_render_measurement(cid, ra.measurements))
    ra_col = " / ".join(rendered_ra) if rendered_ra else "—"
    return pq_col, ra_col


# --- Phase 5 DIST rendering (CONTEXT D-24 + scope amendment 2026-04-25) ---
# Dispatch ordering invariant: DIST branches insert AFTER disp:* per the
# D-24 amendment in ROADMAP Phase 5 scope-amendment block. The BEFORE-cslc/
# dswx part of the original D-24 is a contemporary observation, not a
# forward lock; future phases may legitimately re-order new schemas.


def _is_dist_eu_shape(metrics_path: Path) -> bool:
    """Return True when metrics.json has a top-level ``per_event`` key.

    Phase 5 D-25 schema discriminator. ``per_event`` is structurally disjoint
    from ``ramp_attribution`` (DISP), ``per_aoi`` (CSLC self-consist), and
    ``per_burst`` (RTC-EU); checked AFTER disp:* per Phase 4 D-08 ordering.
    """
    import json as _json

    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.debug("_is_dist_eu_shape: cannot read {}: {}", metrics_path, e)
        return False
    return isinstance(raw, dict) and "per_event" in raw


def _is_dist_nam_shape(metrics_path: Path) -> bool:
    """Return True when metrics.json carries the DistNamCellMetrics shape.

    Phase 5 deferred-cell discriminator (scope amendment 2026-04-25). The
    dist:nam cell ships as DEFERRED until OPERA_L3_DIST-ALERT-S1_V1 publishes
    operationally; the auto-supersede CMR probe in run_eval_dist.py Stage 0
    will repopulate the cell when operational appears (auto-detection
    happens at the next ``make eval-dist-nam`` invocation; no re-planning).

    ME-03 fix (v1.2 forward-compat): when cell_status transitions from
    'DEFERRED' to 'PASS' or 'FAIL' in v1.2, this discriminator must still
    return True so the file is routed to the dist:nam renderer rather than
    falling through to ``_load_metrics``, where pydantic ``extra='forbid'``
    would reject ``cell_status``, ``reference_source``, ``cmr_probe_outcome``,
    ``reference_granule_id``, ``deferred_reason`` and surface the cell as
    ``RUN_FAILED``. The discriminator now keys on ``reference_source`` +
    ``cmr_probe_outcome`` (both present across all DistNamCellMetrics
    versions per the v1.1 schema and v1.2 extension plan in D-24/D-25)
    instead of ``cell_status == 'DEFERRED'``. v1.2 must still add a full
    ``_render_dist_nam_full_cell`` renderer alongside the existing
    ``_render_dist_nam_deferred_cell`` and dispatch on cell_status, but
    the discriminator no longer silently regresses.
    """
    import json as _json

    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.debug("_is_dist_nam_shape: cannot read {}: {}", metrics_path, e)
        return False
    return (
        isinstance(raw, dict)
        and "reference_source" in raw
        and "cmr_probe_outcome" in raw
    )


def _is_rtc_nam_deferred_shape(metrics_path: Path) -> bool:
    """Return True when metrics.json carries the RTC:NAM DEFERRED shape (Phase 7).

    Discriminator: presence of ``unblock_condition`` key in raw JSON. This field
    is unique to the RTC:NAM DEFERRED sidecar and structurally disjoint from all
    other cell schemas (per_burst, per_aoi, ramp_attribution, per_event,
    reference_source+cmr_probe_outcome, selected_aoi+candidates_attempted,
    thresholds_used+loocv_gap).
    """
    import json as _json

    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.debug("_is_rtc_nam_deferred_shape: cannot read {}: {}", metrics_path, e)
        return False
    return isinstance(raw, dict) and "unblock_condition" in raw


def _is_dswx_nam_shape(metrics_path: Path) -> bool:
    """Return True when metrics.json carries the DswxNamCellMetrics shape (Plan 06-04 D-27).

    Discriminator: presence of ``selected_aoi`` AND ``candidates_attempted`` keys
    in raw JSON. These are structurally disjoint from disp:* (ramp_attribution),
    dist:eu (per_event), dist:nam (reference_source + cmr_probe_outcome),
    cslc:* (per_aoi), and rtc:eu (per_burst) schemas.
    """
    import json as _json

    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.debug("_is_dswx_nam_shape: cannot read {}: {}", metrics_path, e)
        return False
    return (
        isinstance(raw, dict)
        and "selected_aoi" in raw
        and "candidates_attempted" in raw
    )


def _is_dswx_eu_shape(metrics_path: Path) -> bool:
    """Return True when metrics.json carries the DswxEUCellMetrics shape (Plan 06-04 D-27).

    Discriminator: presence of ``thresholds_used`` AND ``loocv_gap`` keys in
    raw JSON. Structurally disjoint from all other matrix cell schemas.
    """
    import json as _json

    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.debug("_is_dswx_eu_shape: cannot read {}: {}", metrics_path, e)
        return False
    return (
        isinstance(raw, dict)
        and "thresholds_used" in raw
        and "loocv_gap" in raw
    )


def _render_dist_eu_cell(metrics_path: Path) -> tuple[str, str] | None:
    """Render Phase 5 DIST-EU multi-event aggregate as (pq_col, ra_col).

    pq_col: '—' (DIST has no product-quality gate; CONTEXT "Not this phase").
    ra_col format: 'X/3 PASS' or 'X/3 PASS (Y FAIL)' + worst F1 + chained-retry
    warning glyph when any_chained_run_failed is True.
    """
    from subsideo.validation.matrix_schema import DistEUCellMetrics

    try:
        m = DistEUCellMetrics.model_validate_json(metrics_path.read_text())
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to parse DistEUCellMetrics from {}: {}", metrics_path, e)
        return None

    fail_count = m.total - m.pass_count
    if fail_count > 0:
        base = f"{m.pass_count}/{m.total} PASS ({fail_count} FAIL)"
    else:
        base = f"{m.pass_count}/{m.total} PASS"
    base += f" | worst f1={m.worst_f1:.3f} ({m.worst_event_id})"
    warn = " ⚠" if m.any_chained_run_failed else ""
    ra_col = f"{base}{warn}"
    pq_col = "—"
    return pq_col, ra_col


def _render_dist_nam_deferred_cell(metrics_path: Path) -> tuple[str, str] | None:
    """Render the dist:nam cell (Phase 5 scope amendment + ME-03 v1.2 guard).

    pq_col: '—' (no product-quality gate in v1.1; full schema lands in v1.2).

    ra_col format (v1.1):
        - cell_status == 'DEFERRED': 'DEFERRED (CMR: <cmr_probe_outcome>)' --
          e.g. 'DEFERRED (CMR: operational_not_found)' on miss.

    ra_col format (v1.2 forward-compat -- ME-03):
        - cell_status == 'PASS' / 'FAIL': '<cell_status> (CMR: <cmr_probe_outcome>)'.
          A v1.2 full-schema renderer will likely supersede this with measured
          metrics; until then, surface the cell status verbatim rather than
          mislabelling it as 'DEFERRED'. The discriminator
          (``_is_dist_nam_shape``) was widened to keep these cells routed
          here instead of falling through to ``_load_metrics`` (which would
          produce ``RUN_FAILED`` from pydantic ``extra='forbid'``).
    """
    import json as _json

    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.warning(
            "Failed to read deferred dist:nam metrics from {}: {}", metrics_path, e
        )
        return None

    cmr_outcome = raw.get("cmr_probe_outcome", "probe_failed")
    cell_status = raw.get("cell_status", "DEFERRED")
    pq_col = "—"
    ra_col = f"{cell_status} (CMR: {cmr_outcome})"
    return pq_col, ra_col


def _render_rtc_nam_deferred_cell(metrics_path: Path) -> tuple[str, str] | None:
    """Render the rtc:nam DEFERRED cell (Phase 7 D-01 / D-02).

    pq_col: '—' (no product-quality gate; N.Am. RTC eval not re-run in v1.1).
    ra_col: 'DEFERRED — <unblock_condition>' where unblock_condition is read
    from the sidecar. Consistent with dist:nam DEFERRED rendering pattern but
    without the CMR probe outcome suffix.
    """
    import json as _json

    try:
        raw = _json.loads(metrics_path.read_text())
    except (OSError, ValueError) as e:
        logger.warning(
            "Failed to read deferred rtc:nam metrics from {}: {}", metrics_path, e
        )
        return None
    unblock = raw.get("unblock_condition", "see deferred_reason field")
    pq_col = "—"
    ra_col = f"DEFERRED — {unblock}"
    return pq_col, ra_col


def _render_dswx_nam_cell(metrics_path: Path) -> tuple[str, str] | None:
    """Render Phase 6 N.Am. DSWx positive-control cell as (pq_col, ra_col).

    pq_col: '—' (DSWx has no product-quality gate; CONTEXT D-26).
    ra_col format: 'F1=0.XXX [PASS|FAIL|BLOCKER]' + ' [aoi=<selected_aoi>]' inline +
        ' — named upgrade: <path>' if named_upgrade_path is set +
        ' INVESTIGATION_REQUIRED' if regression.f1_below_regression_threshold AND
        NOT investigation_resolved.
    """
    from subsideo.validation.matrix_schema import DswxNamCellMetrics

    try:
        m = DswxNamCellMetrics.model_validate_json(metrics_path.read_text())
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to parse DswxNamCellMetrics from {}: {}", metrics_path, e)
        return None

    f1_value = m.reference_agreement.measurements.get("f1", float("nan"))
    if m.cell_status == "BLOCKER":
        ra_col = (
            f"BLOCKER [no candidate scene found among {len(m.candidates_attempted)} attempts]"
        )
    else:
        verdict = m.cell_status  # PASS or FAIL
        base = f"F1={f1_value:.3f} {verdict} [aoi={m.selected_aoi}]"
        if m.named_upgrade_path:
            base += f" — named upgrade: {m.named_upgrade_path}"
        if m.regression.f1_below_regression_threshold and not m.regression.investigation_resolved:
            base += " INVESTIGATION_REQUIRED"
        ra_col = base

    pq_col = "—"
    return pq_col, ra_col


def _render_dswx_eu_cell(metrics_path: Path) -> tuple[str, str] | None:
    """Render Phase 6 EU DSWx held-out-Balaton cell as (pq_col, ra_col).

    pq_col: '—' (DSWx has no product-quality gate; CONTEXT D-26).
    ra_col format: 'F1=0.XXX [PASS|FAIL|BLOCKER]' (Balaton; D-13) +
        ' — named upgrade: <path>' if named_upgrade_path is set +
        ' | LOOCV gap=0.XXX' inline diagnostic.
    """
    from subsideo.validation.matrix_schema import DswxEUCellMetrics

    try:
        m = DswxEUCellMetrics.model_validate_json(metrics_path.read_text())
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to parse DswxEUCellMetrics from {}: {}", metrics_path, e)
        return None

    f1_balaton = m.reference_agreement.measurements.get("f1", float("nan"))
    if m.cell_status == "BLOCKER":
        ra_col = f"BLOCKER [LOOCV gap={m.loocv_gap:.3f} (>= 0.02)]"
    else:
        verdict = m.cell_status  # PASS or FAIL
        base = f"F1={f1_balaton:.3f} {verdict}"
        if m.named_upgrade_path:
            base += f" — named upgrade: {m.named_upgrade_path}"
        base += f" | LOOCV gap={m.loocv_gap:.3f}"
        ra_col = base

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

        # Phase 7 RTC:NAM DEFERRED branch: metrics.json with an ``unblock_condition`` key.
        # Inserted BEFORE disp:* per Phase 7 D-01 (RTC:NAM was missing entirely;
        # unblock_condition discriminator is structurally disjoint from all existing
        # discriminators — insertion position is flexible; placed first in chain for clarity).
        if metrics_path.exists() and _is_rtc_nam_deferred_shape(metrics_path):
            cols = _render_rtc_nam_deferred_cell(metrics_path)
            if cols is not None:
                pq_col, ra_col = cols
                lines.append(
                    f"| {product} | {region} | {_escape_table_cell(pq_col)} | "
                    f"{_escape_table_cell(ra_col)} |"
                )
                continue
            # Fall through to default rendering on parse failure.

        # Phase 4 DISP branch: metrics.json with a ``ramp_attribution`` key.
        # Checked BEFORE the cslc_selfconsist (per_aoi) and rtc_eu (per_burst)
        # branches because the schemas are structurally disjoint -- the DISP
        # discriminator is unambiguous (RESEARCH lines 593-608).
        if metrics_path.exists() and _is_disp_cell_shape(metrics_path):
            cols = _render_disp_cell(metrics_path, region=str(cell["region"]))
            if cols is not None:
                pq_col, ra_col = cols
                lines.append(
                    f"| {product} | {region} | {_escape_table_cell(pq_col)} | "
                    f"{_escape_table_cell(ra_col)} |"
                )
                continue
            # Fall through to default rendering on parse failure.

        # Phase 5 DIST-EU branch: metrics.json with a ``per_event`` key.
        # Inserted AFTER disp:* per CONTEXT D-24 + the D-24 amendment in
        # ROADMAP Phase 5 scope-amendment block (the structurally meaningful
        # invariant is AFTER-disp; the relative ordering against cslc:* /
        # dswx:* is a contemporary observation, not a forward lock).
        if metrics_path.exists() and _is_dist_eu_shape(metrics_path):
            cols = _render_dist_eu_cell(metrics_path)
            if cols is not None:
                pq_col, ra_col = cols
                lines.append(
                    f"| {product} | {region} | {_escape_table_cell(pq_col)} | "
                    f"{_escape_table_cell(ra_col)} |"
                )
                continue
            # Fall through to default rendering on parse failure.

        # Phase 5 DIST-NAM deferred-cell branch: metrics.json with
        # cell_status='DEFERRED' + reference_source key. Renders
        # 'DEFERRED (CMR: <outcome>)'. Auto-supersede in v1.2 will replace
        # this branch (different schema) once OPERA_L3_DIST-ALERT-S1_V1
        # publishes operationally.
        if metrics_path.exists() and _is_dist_nam_shape(metrics_path):
            cols = _render_dist_nam_deferred_cell(metrics_path)
            if cols is not None:
                pq_col, ra_col = cols
                lines.append(
                    f"| {product} | {region} | {_escape_table_cell(pq_col)} | "
                    f"{_escape_table_cell(ra_col)} |"
                )
                continue
            # Fall through to default rendering on parse failure.

        # Phase 6 DSWX-N.Am. branch (D-27):
        # Inserted AFTER dist:* per Phase 5 D-24 amendment in ROADMAP scope-amendment block;
        # BEFORE cslc:selfconsist + rtc:eu per W6 invariant.
        # Discriminator (selected_aoi + candidates_attempted) is structurally disjoint
        # from all earlier branches (ramp_attribution, per_event, reference_source, per_aoi,
        # per_burst).
        if metrics_path.exists() and _is_dswx_nam_shape(metrics_path):
            cols = _render_dswx_nam_cell(metrics_path)
            if cols is not None:
                pq_col, ra_col = cols
                lines.append(
                    f"| {product} | {region} | {_escape_table_cell(pq_col)} | "
                    f"{_escape_table_cell(ra_col)} |"
                )
                continue
            # Fall through to default rendering on parse failure.

        # Phase 6 DSWX-EU branch (D-27):
        # Inserted AFTER dswx:nam per D-27; BEFORE cslc:* + rtc:eu per W6 invariant.
        # Discriminator (thresholds_used + loocv_gap) is structurally disjoint from
        # all earlier branches.
        if metrics_path.exists() and _is_dswx_eu_shape(metrics_path):
            cols = _render_dswx_eu_cell(metrics_path)
            if cols is not None:
                pq_col, ra_col = cols
                lines.append(
                    f"| {product} | {region} | {_escape_table_cell(pq_col)} | "
                    f"{_escape_table_cell(ra_col)} |"
                )
                continue
            # Fall through to default rendering on parse failure.

        # Phase 3 CSLC self-consistency branch: metrics.json with a ``per_aoi`` key.
        # Checked BEFORE the rtc_eu branch so a file with both keys (defensive)
        # is routed here (schemas are structurally disjoint, this is an invariant).
        if metrics_path.exists() and _is_cslc_selfconsist_shape(metrics_path):
            cols = _render_cslc_selfconsist_cell(metrics_path, region=str(cell["region"]))
            if cols is not None:
                pq_col, ra_col = cols
                lines.append(
                    f"| {product} | {region} | {_escape_table_cell(pq_col)} | "
                    f"{_escape_table_cell(ra_col)} |"
                )
                continue
            # Fall through to default rendering on parse failure.

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
