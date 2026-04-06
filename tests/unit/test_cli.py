"""Unit tests for the subsideo CLI."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from subsideo.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Help text tests -- every subcommand must register and show help
# ---------------------------------------------------------------------------

PRODUCT_COMMANDS = ["rtc", "cslc", "disp", "dswx", "dist"]


class TestHelpOutput:
    """Verify all subcommands appear and their --help exits cleanly."""

    def test_main_help_lists_all_subcommands(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for cmd in [*PRODUCT_COMMANDS, "validate", "check-env", "build-db"]:
            assert cmd in result.output

    @pytest.mark.parametrize("cmd", PRODUCT_COMMANDS)
    def test_product_command_help(self, cmd: str) -> None:
        result = runner.invoke(app, [cmd, "--help"])
        assert result.exit_code == 0
        assert "--aoi" in result.output
        assert "--start" in result.output
        assert "--end" in result.output
        assert "--out" in result.output
        assert "--verbose" in result.output

    def test_validate_help(self) -> None:
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        assert "--product-dir" in result.output
        assert "--product-type" in result.output
        assert "--reference" in result.output

    def test_check_env_help(self) -> None:
        result = runner.invoke(app, ["check-env", "--help"])
        assert result.exit_code == 0
        assert "--verbose" in result.output

    def test_dswx_help_contains_flags(self) -> None:
        result = runner.invoke(app, ["dswx", "--help"])
        assert result.exit_code == 0
        for flag in ("--start", "--end", "--out", "--aoi"):
            assert flag in result.output


# ---------------------------------------------------------------------------
# AOI validation tests
# ---------------------------------------------------------------------------


class TestAoiValidation:
    """Verify _load_aoi catches invalid input before pipeline runs."""

    def test_missing_aoi_file_exits_nonzero(self, tmp_path: Path) -> None:
        fake_aoi = tmp_path / "nonexistent.geojson"
        result = runner.invoke(
            app,
            ["rtc", "--aoi", str(fake_aoi), "--start", "2024-01-01", "--end", "2024-01-02"],
        )
        assert result.exit_code != 0

    def test_invalid_geometry_type_exits_nonzero(self, tmp_path: Path) -> None:
        aoi_file = tmp_path / "point.geojson"
        aoi_file.write_text(json.dumps({"type": "Point", "coordinates": [10, 45]}))
        result = runner.invoke(
            app,
            ["rtc", "--aoi", str(aoi_file), "--start", "2024-01-01", "--end", "2024-01-02"],
        )
        assert result.exit_code != 0

    def test_dist_cmd_iterates_results(self, tmp_path: Path) -> None:
        """B-06: CLI dist command iterates list[DISTResult], not single result."""
        from unittest.mock import MagicMock

        mock_result_ok = MagicMock()
        mock_result_ok.valid = True
        mock_result_ok.validation_errors = []

        mock_result_fail = MagicMock()
        mock_result_fail.valid = False
        mock_result_fail.validation_errors = ["tile failed"]

        aoi_file = tmp_path / "aoi.geojson"
        aoi_file.write_text(
            json.dumps(
                {
                    "type": "Polygon",
                    "coordinates": [
                        [[11, 48], [12, 48], [12, 49], [11, 49], [11, 48]]
                    ],
                }
            )
        )

        from unittest.mock import patch

        with patch(
            "subsideo.products.dist.run_dist_from_aoi",
            return_value=[mock_result_ok, mock_result_fail],
        ), patch("subsideo.utils.logging.configure_logging"):
            res = runner.invoke(
                app,
                [
                    "dist",
                    "--aoi", str(aoi_file),
                    "--start", "2025-01-01",
                    "--end", "2025-02-01",
                    "--out", str(tmp_path / "out"),
                ],
            )
        assert res.exit_code == 1  # one tile failed
        assert "FAIL" in res.output

    def test_feature_collection_polygon_accepted(self, tmp_path: Path) -> None:
        """_load_aoi should accept FeatureCollection with Polygon geometry."""
        from subsideo.cli import _load_aoi

        aoi_file = tmp_path / "fc.geojson"
        fc = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[10, 45], [11, 45], [11, 46], [10, 46], [10, 45]]],
                    },
                    "properties": {},
                }
            ],
        }
        aoi_file.write_text(json.dumps(fc))
        result = _load_aoi(aoi_file)
        assert result == aoi_file
