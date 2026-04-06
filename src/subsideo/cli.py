"""subsideo CLI -- OPERA-equivalent SAR/InSAR pipelines for the EU."""
from __future__ import annotations

import json
from pathlib import Path

import typer

app = typer.Typer(
    name="subsideo",
    help="OPERA-equivalent SAR/InSAR pipelines for the European Union.",
    no_args_is_help=True,
)


@app.callback()
def _main() -> None:
    """OPERA-equivalent SAR/InSAR pipelines for the European Union."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_aoi(aoi_path: Path) -> Path:
    """Validate GeoJSON AOI file exists and contains Polygon/MultiPolygon."""
    if not aoi_path.exists():
        raise typer.BadParameter(f"AOI file not found: {aoi_path}")
    with open(aoi_path) as f:
        geojson = json.load(f)
    geom_type = geojson.get("type", "")
    if geom_type == "FeatureCollection":
        geom_type = geojson["features"][0]["geometry"]["type"]
    elif geom_type == "Feature":
        geom_type = geojson["geometry"]["type"]
    if geom_type not in ("Polygon", "MultiPolygon"):
        raise typer.BadParameter(
            f"AOI must be Polygon or MultiPolygon, got {geom_type}"
        )
    return aoi_path


# ---------------------------------------------------------------------------
# check-env (existing)
# ---------------------------------------------------------------------------


@app.command("check-env")
def check_env(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
) -> None:
    """Validate all credentials and ancillary service connectivity.

    Checks CDSE OAuth2 credentials, NASA Earthdata credentials, and (optionally)
    the CDS API key. Exits with code 1 if any required credential is missing or invalid.
    """
    from subsideo.config import Settings
    from subsideo.utils.logging import configure_logging

    configure_logging(verbose=verbose)
    s = Settings()
    issues: list[str] = []
    warnings: list[str] = []

    # --- CDSE credentials ---
    if not s.cdse_client_id or not s.cdse_client_secret:
        issues.append(
            "CDSE: CDSE_CLIENT_ID and/or CDSE_CLIENT_SECRET not set. "
            "Register at https://dataspace.copernicus.eu and create OAuth2 client credentials."
        )
    else:
        typer.echo("[OK] CDSE credentials: present")

    # --- Earthdata credentials ---
    if not s.earthdata_username or not s.earthdata_password:
        issues.append(
            "Earthdata: EARTHDATA_USERNAME and/or EARTHDATA_PASSWORD not set. "
            "Register at https://urs.earthdata.nasa.gov"
        )
    else:
        typer.echo("[OK] Earthdata credentials: present")

    # --- CDS API (optional) ---
    if not s.cdsapi_rc.exists():
        warnings.append(
            f"CDS API key not found at {s.cdsapi_rc} -- ERA5 tropospheric correction "
            "will be unavailable. See https://cds.climate.copernicus.eu/how-to-api"
        )
    else:
        typer.echo(f"[OK] CDS API key: found at {s.cdsapi_rc}")

    for w in warnings:
        typer.echo(f"[WARNING] {w}", err=True)

    if issues:
        for issue in issues:
            typer.echo(f"[FAIL] {issue}", err=True)
        raise typer.Exit(code=1)

    typer.echo("[OK] All required credentials present")


# ---------------------------------------------------------------------------
# Product subcommands
# ---------------------------------------------------------------------------


@app.command("rtc")
def rtc_cmd(
    aoi: Path = typer.Option(..., "--aoi", help="GeoJSON file (Polygon/MultiPolygon)"),
    start: str = typer.Option(..., "--start", help="Start date (YYYY-MM-DD)"),
    end: str = typer.Option(..., "--end", help="End date (YYYY-MM-DD)"),
    out: Path = typer.Option(Path("."), "--out", help="Output directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Debug-level logging"),
) -> None:
    """Produce RTC-S1 backscatter products for an EU AOI."""
    from subsideo.utils.logging import configure_logging

    configure_logging(verbose=verbose)
    aoi = _load_aoi(aoi)
    product_dir = out / "rtc"
    product_dir.mkdir(parents=True, exist_ok=True)
    from subsideo.products.rtc import run_rtc_from_aoi

    result = run_rtc_from_aoi(aoi=aoi, date_range=(start, end), output_dir=product_dir)
    if not result.valid:
        typer.echo(f"[FAIL] RTC: {result.validation_errors}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"[OK] RTC products written to {product_dir}")


@app.command("cslc")
def cslc_cmd(
    aoi: Path = typer.Option(..., "--aoi", help="GeoJSON file (Polygon/MultiPolygon)"),
    start: str = typer.Option(..., "--start", help="Start date (YYYY-MM-DD)"),
    end: str = typer.Option(..., "--end", help="End date (YYYY-MM-DD)"),
    out: Path = typer.Option(Path("."), "--out", help="Output directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Debug-level logging"),
) -> None:
    """Produce CSLC-S1 coregistered SLC products for an EU AOI."""
    from subsideo.utils.logging import configure_logging

    configure_logging(verbose=verbose)
    aoi = _load_aoi(aoi)
    product_dir = out / "cslc"
    product_dir.mkdir(parents=True, exist_ok=True)
    from subsideo.products.cslc import run_cslc_from_aoi

    result = run_cslc_from_aoi(aoi=aoi, date_range=(start, end), output_dir=product_dir)
    if not result.valid:
        typer.echo(f"[FAIL] CSLC: {result.validation_errors}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"[OK] CSLC products written to {product_dir}")


@app.command("disp")
def disp_cmd(
    aoi: Path = typer.Option(..., "--aoi", help="GeoJSON file (Polygon/MultiPolygon)"),
    start: str = typer.Option(..., "--start", help="Start date (YYYY-MM-DD)"),
    end: str = typer.Option(..., "--end", help="End date (YYYY-MM-DD)"),
    out: Path = typer.Option(Path("."), "--out", help="Output directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Debug-level logging"),
) -> None:
    """Produce DISP-S1 displacement time-series for an EU AOI."""
    from subsideo.utils.logging import configure_logging

    configure_logging(verbose=verbose)
    aoi = _load_aoi(aoi)
    product_dir = out / "disp"
    product_dir.mkdir(parents=True, exist_ok=True)
    from subsideo.products.disp import run_disp_from_aoi

    result = run_disp_from_aoi(aoi=aoi, date_range=(start, end), output_dir=product_dir)
    if not result.valid:
        typer.echo(f"[FAIL] DISP: {result.validation_errors}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"[OK] DISP products written to {product_dir}")


@app.command("dswx")
def dswx_cmd(
    aoi: Path = typer.Option(..., "--aoi", help="GeoJSON file (Polygon/MultiPolygon)"),
    start: str = typer.Option(..., "--start", help="Start date (YYYY-MM-DD)"),
    end: str = typer.Option(..., "--end", help="End date (YYYY-MM-DD)"),
    out: Path = typer.Option(Path("."), "--out", help="Output directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Debug-level logging"),
) -> None:
    """Produce DSWx-S2 water extent products for an EU AOI."""
    from subsideo.utils.logging import configure_logging

    configure_logging(verbose=verbose)
    aoi = _load_aoi(aoi)
    product_dir = out / "dswx"
    product_dir.mkdir(parents=True, exist_ok=True)
    from subsideo.products.dswx import run_dswx_from_aoi

    result = run_dswx_from_aoi(aoi=aoi, date_range=(start, end), output_dir=product_dir)
    if not result.valid:
        typer.echo(f"[FAIL] DSWx: {result.validation_errors}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"[OK] DSWx products written to {product_dir}")


@app.command("dist")
def dist_cmd(
    aoi: Path = typer.Option(..., "--aoi", help="GeoJSON file (Polygon/MultiPolygon)"),
    start: str = typer.Option(..., "--start", help="Start date (YYYY-MM-DD)"),
    end: str = typer.Option(..., "--end", help="End date (YYYY-MM-DD)"),
    out: Path = typer.Option(Path("."), "--out", help="Output directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Debug-level logging"),
) -> None:
    """Produce DIST-S1 surface disturbance products for an EU AOI.

    Note: dist-s1 must be installed from conda-forge.
    """
    from subsideo.utils.logging import configure_logging

    configure_logging(verbose=verbose)
    aoi = _load_aoi(aoi)
    product_dir = out / "dist"
    product_dir.mkdir(parents=True, exist_ok=True)
    try:
        from subsideo.products.dist import run_dist_from_aoi
    except ImportError:
        typer.echo(
            "[FAIL] DIST: dist-s1 not installed. "
            "Install via: mamba install -c conda-forge dist-s1",
            err=True,
        )
        raise typer.Exit(code=1)
    result = run_dist_from_aoi(aoi=aoi, date_range=(start, end), output_dir=product_dir)
    if not result.valid:
        typer.echo(f"[FAIL] DIST: {result.validation_errors}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"[OK] DIST products written to {product_dir}")


# ---------------------------------------------------------------------------
# Validate subcommand
# ---------------------------------------------------------------------------


@app.command("validate")
def validate_cmd(
    product_dir: Path = typer.Option(
        ..., "--product-dir", help="Directory with product outputs"
    ),
    product_type: str = typer.Option(
        ..., "--product-type", help="Product type: rtc|cslc|disp|dswx"
    ),
    reference_path: Path = typer.Option(
        None, "--reference", help="Reference product path (for rtc/cslc)"
    ),
    egms_path: Path = typer.Option(
        None, "--egms", help="EGMS Ortho reference GeoTIFF (for disp validation)"
    ),
    year: int = typer.Option(None, "--year", help="Year for JRC comparison (dswx)"),
    month: int = typer.Option(None, "--month", help="Month for JRC comparison (dswx)"),
    out: Path = typer.Option(Path("."), "--out", help="Report output directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run validation comparison and generate reports."""
    from subsideo.utils.logging import configure_logging

    configure_logging(verbose=verbose)
    out.mkdir(parents=True, exist_ok=True)

    import numpy as np

    pt = product_type.lower()

    if pt == "rtc":
        from subsideo.validation.compare_rtc import compare_rtc

        product_files = sorted(product_dir.glob("*.tif"))
        if not product_files or reference_path is None:
            typer.echo(
                "[FAIL] rtc validation requires product TIF and --reference", err=True
            )
            raise typer.Exit(code=1)
        result = compare_rtc(product_files[0], reference_path)
    elif pt == "cslc":
        from subsideo.validation.compare_cslc import compare_cslc

        product_files = sorted(product_dir.glob("*.h5"))
        if not product_files or reference_path is None:
            typer.echo(
                "[FAIL] cslc validation requires product HDF5 and --reference", err=True
            )
            raise typer.Exit(code=1)
        result = compare_cslc(product_files[0], reference_path)
    elif pt == "disp":
        from subsideo.validation.compare_disp import compare_disp

        velocity_files = sorted(product_dir.glob("*velocity*.tif")) + sorted(
            product_dir.glob("*velocity*.h5")
        )
        if not velocity_files or egms_path is None:
            typer.echo(
                "[FAIL] disp validation requires velocity file and --egms reference",
                err=True,
            )
            raise typer.Exit(code=1)
        result = compare_disp(velocity_files[0], egms_ortho_path=egms_path)
    elif pt == "dswx":
        from subsideo.validation.compare_dswx import compare_dswx

        product_files = sorted(product_dir.glob("*.tif"))
        if not product_files or year is None or month is None:
            typer.echo(
                "[FAIL] dswx validation requires product TIF and --year/--month",
                err=True,
            )
            raise typer.Exit(code=1)
        result = compare_dswx(product_files[0], year=year, month=month)
    else:
        typer.echo(
            f"[FAIL] Unknown product type: {product_type}. Use rtc|cslc|disp|dswx",
            err=True,
        )
        raise typer.Exit(code=1)

    # Generate report
    from subsideo.validation.report import generate_report

    # Load arrays for report figures
    try:
        import rasterio

        with rasterio.open(product_files[0]) as ds:
            prod_arr = ds.read(1).astype(np.float32)
    except Exception:
        prod_arr = np.zeros((10, 10), dtype=np.float32)
    try:
        if reference_path and reference_path.exists():
            import rasterio

            with rasterio.open(reference_path) as ds:
                ref_arr = ds.read(1).astype(np.float32)
        else:
            ref_arr = np.zeros_like(prod_arr)
    except Exception:
        ref_arr = np.zeros_like(prod_arr)

    html_path, md_path = generate_report(
        product_type=pt.upper(),
        validation_result=result,
        product_array=prod_arr,
        reference_array=ref_arr,
        output_dir=out,
    )
    typer.echo(f"[OK] Reports generated: {html_path}, {md_path}")

    # Print pass/fail summary
    if hasattr(result, "pass_criteria"):
        all_pass = all(result.pass_criteria.values())
        for criterion, passed in result.pass_criteria.items():
            status = "PASS" if passed else "FAIL"
            typer.echo(f"  [{status}] {criterion}")
        if not all_pass:
            raise typer.Exit(code=1)
