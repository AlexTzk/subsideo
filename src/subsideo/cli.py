"""subsideo CLI -- OPERA-equivalent SAR/InSAR pipelines for the EU."""
from __future__ import annotations

import typer

app = typer.Typer(
    name="subsideo",
    help="OPERA-equivalent SAR/InSAR pipelines for the European Union.",
    no_args_is_help=True,
)


@app.callback()
def _main() -> None:
    """OPERA-equivalent SAR/InSAR pipelines for the European Union."""


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
        # NOTE: Full connectivity check (OAuth2 token fetch) will be added in Plan 04
        # once CDSEClient is implemented. For now, presence check only.
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
