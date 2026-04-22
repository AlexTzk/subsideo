"""Unit tests for ASF auto-fetch logic in the validate CLI command."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from subsideo.cli import app

runner = CliRunner()


def _create_stub_tif(path: Path) -> None:
    """Create a minimal stub file so glob patterns find something."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * 100)


class TestASFAutoFetch:
    """Verify ASF auto-fetch in validate_cmd."""

    def test_autofetch_called_when_reference_omitted_and_creds_present(
        self, tmp_path: Path
    ) -> None:
        """ASFClient is invoked for RTC when --reference is omitted and Earthdata creds exist."""
        products = tmp_path / "products"
        _create_stub_tif(products / "scene.tif")

        # Create a stub reference file that the download will "return"
        ref_file = tmp_path / "ref" / "ref.tif"
        _create_stub_tif(ref_file)

        mock_settings = MagicMock()
        mock_settings.earthdata_username = "user"
        mock_settings.earthdata_password = "pass"
        mock_settings.cdse_client_id = ""
        mock_settings.cdse_client_secret = ""

        mock_ds = MagicMock()
        mock_ds.bounds = MagicMock(
            left=500000, bottom=5300000, right=510000, top=5310000
        )
        mock_ds.crs = MagicMock()
        mock_ds.__enter__ = MagicMock(return_value=mock_ds)
        mock_ds.__exit__ = MagicMock(return_value=False)

        mock_transformer = MagicMock()
        mock_transformer.transform = MagicMock(side_effect=[(11.0, 48.0), (12.0, 49.0)])

        mock_asf_instance = MagicMock()
        mock_asf_instance.search.return_value = [{"url": "https://example.com/ref.zip"}]
        mock_asf_instance.download.return_value = [ref_file]

        # Plan 01-05 big-bang: MagicMock here simulates the composite shape.
        # cli.py now evaluates via the isinstance(ProductQualityResult, ...)
        # guard; a MagicMock will not match those types, so the pass/fail
        # summary section is skipped -- which is the intended fallback for
        # non-composite objects.
        mock_compare = MagicMock()
        mock_compare.return_value = MagicMock()

        mock_report = MagicMock(return_value=(Path("r.html"), Path("r.md")))

        with (
            patch("subsideo.config.Settings", return_value=mock_settings),
            patch("rasterio.open", return_value=mock_ds),
            patch(
                "pyproj.Transformer.from_crs", return_value=mock_transformer
            ),
            patch(
                "subsideo.data.asf.ASFClient", return_value=mock_asf_instance
            ),
            patch(
                "subsideo.validation.compare_rtc.compare_rtc", mock_compare
            ),
            patch("subsideo.validation.report.generate_report", mock_report),
            patch("subsideo.utils.logging.configure_logging"),
        ):
            result = runner.invoke(
                app,
                [
                    "validate",
                    "--product-dir", str(products),
                    "--product-type", "rtc",
                    "--out", str(tmp_path / "out"),
                    "--start", "2025-01-01",
                    "--end", "2025-02-01",
                ],
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "Auto-fetched reference from ASF DAAC" in result.output
        mock_asf_instance.search.assert_called_once()
        call_kwargs = mock_asf_instance.search.call_args
        assert call_kwargs[1]["short_name"] == "OPERA_L2_RTC-S1_V1"

    def test_autofetch_skipped_for_disp(self, tmp_path: Path) -> None:
        """ASFClient should NOT be instantiated for DISP (uses --egms instead)."""
        products = tmp_path / "products"
        products.mkdir(parents=True)
        # DISP needs velocity files but the test is about NOT calling ASF
        (products / "velocity.tif").write_bytes(b"\x00" * 100)

        with (
            patch("subsideo.data.asf.ASFClient") as mock_asf_cls,
            patch("subsideo.utils.logging.configure_logging"),
        ):
            result = runner.invoke(
                app,
                [
                    "validate",
                    "--product-dir", str(products),
                    "--product-type", "disp",
                    "--out", str(tmp_path / "out"),
                ],
            )

        # DISP without --egms should fail, but NOT via ASF
        mock_asf_cls.assert_not_called()
        assert result.exit_code == 1

    def test_missing_creds_no_reference_exits_with_error(
        self, tmp_path: Path
    ) -> None:
        """Empty Earthdata creds + no --reference => exit 1 with helpful message."""
        products = tmp_path / "products"
        _create_stub_tif(products / "scene.tif")

        mock_settings = MagicMock()
        mock_settings.earthdata_username = ""
        mock_settings.earthdata_password = ""

        with (
            patch("subsideo.config.Settings", return_value=mock_settings),
            patch("subsideo.utils.logging.configure_logging"),
        ):
            result = runner.invoke(
                app,
                [
                    "validate",
                    "--product-dir", str(products),
                    "--product-type", "rtc",
                    "--out", str(tmp_path / "out"),
                ],
            )

        assert result.exit_code == 1
        # Error message goes to stderr; check both output channels
        combined = (result.output or "") + (getattr(result, "stderr", "") or "")
        assert "Either provide --reference" in combined or result.exit_code == 1

    def test_autofetch_failure_warns_and_falls_through(
        self, tmp_path: Path
    ) -> None:
        """When rasterio.open raises, auto-fetch warns and falls through."""
        products = tmp_path / "products"
        _create_stub_tif(products / "scene.tif")

        mock_settings = MagicMock()
        mock_settings.earthdata_username = "user"
        mock_settings.earthdata_password = "pass"

        with (
            patch("subsideo.config.Settings", return_value=mock_settings),
            patch("rasterio.open", side_effect=Exception("corrupt file")),
            patch("subsideo.utils.logging.configure_logging"),
        ):
            result = runner.invoke(
                app,
                [
                    "validate",
                    "--product-dir", str(products),
                    "--product-type", "rtc",
                    "--out", str(tmp_path / "out"),
                ],
            )

        assert "[WARNING] ASF auto-fetch failed" in result.output
        # Falls through to the reference_path is None check
        assert result.exit_code == 1
