"""Validation report generation (HTML + Markdown) for all product types.

Updated Plan 01-05 (D-09 big-bang): reads the nested-composite
ValidationResult shape (product_quality + reference_agreement) and
derives pass/fail via :func:`subsideo.validation.results.evaluate`.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from loguru import logger

from subsideo.validation.criteria import CRITERIA
from subsideo.validation.results import (
    ProductQualityResult,
    ReferenceAgreementResult,
    evaluate,
    measurement_key,
)

# ---------------------------------------------------------------------------
# Measurement-key mapping: measurement dict key -> human-readable label
# ---------------------------------------------------------------------------
# Used when rendering the metrics table row labels. The criterion column text
# is built from CRITERIA thresholds at read time.
_MEASUREMENT_LABELS: dict[str, str] = {
    # RTC
    "rmse_db": "RMSE (dB)",
    "correlation": "Correlation (r)",
    "bias_db": "Bias (dB)",
    "ssim": "SSIM",
    # DISP
    "bias_mm_yr": "Bias (mm/yr)",
    # CSLC
    "phase_rms_rad": "Phase RMS (rad)",
    "coherence": "Coherence",
    "amplitude_r": "Amplitude r",
    "amplitude_rmse_db": "Amplitude RMSE (dB)",
    # DSWx / DIST classification
    "f1": "F1",
    "precision": "Precision",
    "recall": "Recall",
    "accuracy": "Accuracy",
    "n_valid_pixels": "Valid pixels",
    # DISP/CSLC self-consistency
    "residual_mm_yr": "Residual mean velocity (mm/yr)",
}


def _criterion_label(criterion_id: str) -> str:
    """Render a human-readable criterion label from the CRITERIA registry."""
    crit = CRITERIA.get(criterion_id)
    if crit is None:
        return criterion_id
    return f"{crit.name} {crit.comparator} {crit.threshold}"


def _fig_to_svg(fig) -> str:  # noqa: ANN001
    """Render a matplotlib figure as an SVG string.

    Closes the figure after rendering.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    import matplotlib.pyplot as plt

    plt.close(fig)
    buf.seek(0)
    return buf.read().decode("utf-8")


def _fig_to_png(fig, path: Path) -> Path:  # noqa: ANN001
    """Save a matplotlib figure to *path* as PNG (300 dpi).

    Closes the figure after saving. Returns *path*.
    """
    fig.savefig(str(path), format="png", dpi=300, bbox_inches="tight")
    import matplotlib.pyplot as plt

    plt.close(fig)
    return path


def _make_diff_map(
    product_arr: np.ndarray,
    reference_arr: np.ndarray,
    title: str,
):  # noqa: ANN201
    """Create a spatial difference map figure (product - reference).

    Returns a matplotlib Figure object.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    diff = product_arr.astype(np.float64) - reference_arr.astype(np.float64)
    vmax = max(abs(np.nanmin(diff)), abs(np.nanmax(diff)), 1e-9)

    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(diff, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    fig.colorbar(im, ax=ax, label="Product - Reference")
    ax.set_title(title)
    ax.set_xlabel("Column")
    ax.set_ylabel("Row")
    return fig


def _make_scatter_plot(
    product_arr: np.ndarray,
    reference_arr: np.ndarray,
    title: str,
):  # noqa: ANN201
    """Create a scatter plot of product vs reference values.

    Subsamples to at most 50 000 points for performance.
    Returns a matplotlib Figure object.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    p = product_arr.ravel().astype(np.float64)
    r = reference_arr.ravel().astype(np.float64)
    valid = np.isfinite(p) & np.isfinite(r)
    p, r = p[valid], r[valid]

    # Subsample
    max_pts = 50_000
    if len(p) > max_pts:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(p), max_pts, replace=False)
        p, r = p[idx], r[idx]

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(r, p, s=2, alpha=0.3, edgecolors="none")

    # 1:1 line
    lo = min(r.min(), p.min()) if len(r) > 0 else 0
    hi = max(r.max(), p.max()) if len(r) > 0 else 1
    ax.plot([lo, hi], [lo, hi], "k--", linewidth=1, label="1:1")

    # Linear regression
    if len(r) >= 2:
        coeffs = np.polyfit(r, p, 1)
        ax.plot(
            [lo, hi],
            [coeffs[0] * lo + coeffs[1], coeffs[0] * hi + coeffs[1]],
            "r-",
            linewidth=1,
            label=f"fit (slope={coeffs[0]:.3f})",
        )

    ax.set_xlabel("Reference")
    ax.set_ylabel("Product")
    ax.set_title(title)
    ax.legend(fontsize=8)
    return fig


def _render_sub_result(
    sub_result: ProductQualityResult | ReferenceAgreementResult,
) -> list[dict]:
    """Render one sub-result (product_quality OR reference_agreement) as rows.

    Returns a list of dicts with keys: metric, value, criterion, passed.
    Measurements that have NO corresponding criterion_id on the sub-result
    appear with criterion='--' and passed=None (informational only).
    """
    rows: list[dict] = []

    # Compute pass/fail for each criterion_id listed on this sub-result.
    pass_map: dict[str, bool] = {}
    if sub_result.criterion_ids:
        try:
            pass_map = evaluate(sub_result)
        except KeyError as exc:
            # Missing measurement: surface a warning row and continue.
            logger.warning("evaluate() raised on sub-result: {}", exc)

    # Build a reverse map: measurement_key -> list[criterion_id]
    mkey_to_cids: dict[str, list[str]] = {}
    for cid in sub_result.criterion_ids:
        mkey_to_cids.setdefault(measurement_key(cid), []).append(cid)

    for mkey, mval in sub_result.measurements.items():
        label = _MEASUREMENT_LABELS.get(mkey, mkey)
        cids = mkey_to_cids.get(mkey, [])
        if cids:
            # Emit one row per applicable criterion.
            for cid in cids:
                rows.append(
                    {
                        "metric": label,
                        "value": f"{float(mval):.4f}",
                        "criterion": _criterion_label(cid),
                        "passed": pass_map.get(cid, True),
                    }
                )
        else:
            rows.append(
                {
                    "metric": label,
                    "value": f"{float(mval):.4f}",
                    "criterion": "--",
                    "passed": None,
                }
            )
    return rows


def _metrics_table_from_result(validation_result) -> list[dict]:  # noqa: ANN001
    """Build a metrics table from any (composite) ValidationResult dataclass.

    Each entry is a dict with keys: metric, value, criterion, passed.
    Reads the nested product_quality + reference_agreement sub-results (no
    flat fields; no collapsed pass-dict).
    """
    table: list[dict] = []
    pq = getattr(validation_result, "product_quality", None)
    ra = getattr(validation_result, "reference_agreement", None)
    if isinstance(pq, ProductQualityResult):
        table.extend(_render_sub_result(pq))
    if isinstance(ra, ReferenceAgreementResult):
        table.extend(_render_sub_result(ra))
    return table


def generate_report(
    product_type: str,
    validation_result,  # noqa: ANN001
    product_array: np.ndarray,
    reference_array: np.ndarray,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Generate HTML and Markdown validation reports.

    Args:
        product_type: Human-readable product type name (e.g., "RTC-S1").
        validation_result: A ValidationResult dataclass instance.
        product_array: 2-D array of product values.
        reference_array: 2-D array of reference values.
        output_dir: Directory where report files and figures are written.

    Returns:
        Tuple of (html_path, md_path).
    """
    from jinja2 import Environment, FileSystemLoader
    from markupsafe import Markup

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Build metrics table
    metrics_table = _metrics_table_from_result(validation_result)

    # 2. Generate figures
    diff_fig = _make_diff_map(product_array, reference_array, f"{product_type} Difference Map")
    scatter_fig = _make_scatter_plot(
        product_array, reference_array, f"{product_type} Product vs Reference"
    )

    # 3. SVG for HTML
    diff_map_svg = _fig_to_svg(diff_fig)
    scatter_svg = _fig_to_svg(scatter_fig)

    # 4. PNG for Markdown
    diff_fig2 = _make_diff_map(product_array, reference_array, f"{product_type} Difference Map")
    scatter_fig2 = _make_scatter_plot(
        product_array, reference_array, f"{product_type} Product vs Reference"
    )
    slug = product_type.lower().replace("-", "_").replace(" ", "_")
    diff_png = _fig_to_png(diff_fig2, output_dir / f"{slug}_diff_map.png")
    scatter_png = _fig_to_png(scatter_fig2, output_dir / f"{slug}_scatter.png")

    # 5. Render HTML via Jinja2
    templates_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)
    template = env.get_template("report.html")

    from subsideo import __version__

    generated_at = datetime.now(tz=timezone.utc).isoformat()
    html_content = template.render(
        product_type=product_type,
        generated_at=generated_at,
        software_version=__version__,
        metrics_table=metrics_table,
        diff_map_svg=Markup(diff_map_svg),
        scatter_svg=Markup(scatter_svg),
    )

    html_path = output_dir / f"{slug}_validation.html"
    html_path.write_text(html_content, encoding="utf-8")
    logger.info(f"HTML report written: {html_path}")

    # 6. Write Markdown
    md_lines = [
        f"# {product_type} Validation Report\n",
        f"Generated: {generated_at} | Software: subsideo {__version__}\n",
        "\n## Metric Summary\n",
        "| Metric | Value | Criterion | Status |",
        "|--------|-------|-----------|--------|",
    ]
    for row in metrics_table:
        status = (
            "--" if row["passed"] is None
            else "PASS" if row["passed"]
            else "FAIL"
        )
        md_lines.append(f"| {row['metric']} | {row['value']} | {row['criterion']} | {status} |")

    md_lines.extend(
        [
            "",
            "## Spatial Difference Map",
            "",
            f"![Difference Map]({diff_png.name})",
            "",
            "## Scatter Plot",
            "",
            f"![Scatter Plot]({scatter_png.name})",
        ]
    )

    md_path = output_dir / f"{slug}_validation.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    logger.info(f"Markdown report written: {md_path}")

    return html_path, md_path
