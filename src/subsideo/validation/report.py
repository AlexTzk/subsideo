"""Validation report generation (HTML + Markdown) for all product types."""
from __future__ import annotations

import io
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from loguru import logger


# ---------------------------------------------------------------------------
# Criteria mapping: metric field name -> (human label, pass_criteria key)
# ---------------------------------------------------------------------------
_CRITERIA_MAP: dict[str, tuple[str, str]] = {
    # RTC
    "rmse_db": ("RMSE < 0.5 dB", "rmse_lt_0.5dB"),
    "correlation": ("r > threshold", "correlation_gt_0.99"),
    "bias_db": ("--", ""),
    "ssim_value": ("--", ""),
    # DISP
    "bias_mm_yr": ("bias < 3 mm/yr", "bias_lt_3mm_yr"),
    # DSWx
    "f1": ("F1 > 0.90", "f1_gt_0.90"),
    "precision": ("--", ""),
    "recall": ("--", ""),
    "overall_accuracy": ("--", ""),
    # CSLC
    "phase_rms_rad": ("phase RMS < 0.05 rad", "phase_rms_lt_0.05rad"),
    "coherence": ("--", ""),
}


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


def _metrics_table_from_result(validation_result) -> list[dict]:  # noqa: ANN001
    """Build a metrics table from any ValidationResult dataclass.

    Each entry is a dict with keys: metric, value, criterion, passed.
    """
    table: list[dict] = []
    pass_criteria = getattr(validation_result, "pass_criteria", {})

    for f in fields(validation_result):
        if f.name == "pass_criteria":
            continue
        val = getattr(validation_result, f.name)
        if not isinstance(val, (int, float)):
            continue

        criterion_label, criterion_key = _CRITERIA_MAP.get(f.name, ("--", ""))
        passed = pass_criteria.get(criterion_key) if criterion_key else None

        # Fallback: if static map key not found, search pass_criteria for
        # a key starting with the field name (handles correlation ambiguity
        # between RTC correlation_gt_0.99 and DISP correlation_gt_0.92)
        if passed is None and criterion_key:
            for pc_key, pc_val in pass_criteria.items():
                if pc_key.startswith(f.name):
                    passed = pc_val
                    criterion_label = pc_key  # show actual criterion
                    break

        table.append(
            {
                "metric": f.name,
                "value": f"{val:.4f}",
                "criterion": criterion_label,
                "passed": passed if passed is not None else True,
            }
        )
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
        status = "PASS" if row["passed"] else "FAIL"
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
