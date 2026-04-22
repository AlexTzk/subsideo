"""Unit tests for subsideo._cog: warning surface + ensure_valid_cog heal path."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds


def _write_cog(path: Path, size: int = 64) -> Path:
    """Write a minimal COG GeoTIFF via rio_cogeo at *path*."""
    from rio_cogeo import cog_translate
    from rio_cogeo.profiles import cog_profiles

    src = path.with_suffix(".src.tif")
    transform = from_bounds(0, 0, size, size, size, size)
    with rasterio.open(
        src,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=1,
        dtype="float32",
        crs=CRS.from_epsg(32632),
        transform=transform,
    ) as dst:
        dst.write(
            np.random.default_rng(0).random((size, size)).astype(np.float32), 1
        )
    cog_translate(
        str(src),
        str(path),
        cog_profiles.get("deflate"),
        in_memory=False,
        quiet=True,
    )
    src.unlink()
    return path


def test_imports_without_rio_cogeo_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Module must import cleanly even if rio_cogeo is not importable.

    The module-top imports must be stdlib + loguru only; rio_cogeo usage is
    deferred inside function bodies.  This test simulates the pip-install
    (non-conda) user by hiding rio_cogeo at sys.modules before re-import.
    """
    import sys

    monkeypatch.setitem(sys.modules, "rio_cogeo", None)
    import importlib

    import subsideo._cog as _cog

    importlib.reload(_cog)
    assert hasattr(_cog, "cog_validate")
    assert hasattr(_cog, "cog_translate")
    assert hasattr(_cog, "cog_profiles")
    assert hasattr(_cog, "ensure_valid_cog")
    assert hasattr(_cog, "RIO_COGEO_VERSION")


def test_rio_cogeo_version_tuple() -> None:
    """RIO_COGEO_VERSION() returns a 3-int tuple; first element is major version."""
    from subsideo._cog import RIO_COGEO_VERSION

    v = RIO_COGEO_VERSION()
    assert isinstance(v, tuple) and len(v) == 3
    assert v[0] == 6, f"Expected rio-cogeo 6.x, got {v}"


def test_cog_validate_returns_triple(tmp_path: Path) -> None:
    """cog_validate returns (is_valid: bool, errors: list, warnings: list)."""
    from subsideo._cog import cog_validate

    cog = _write_cog(tmp_path / "ok.tif")
    result = cog_validate(cog)
    assert isinstance(result, tuple) and len(result) == 3
    is_valid, errors, warnings = result
    assert isinstance(is_valid, bool)
    assert isinstance(errors, list)
    assert isinstance(warnings, list)
    assert is_valid is True
    assert errors == []


def test_ensure_valid_cog_noop_on_valid(tmp_path: Path) -> None:
    """Valid COG with no warnings: ensure_valid_cog is a no-op (mtime unchanged)."""
    from subsideo._cog import ensure_valid_cog

    cog = _write_cog(tmp_path / "ok.tif")
    before = cog.stat().st_mtime
    time.sleep(0.05)
    ensure_valid_cog(cog)
    after = cog.stat().st_mtime
    assert after == before


def test_ensure_valid_cog_heals_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """IFD-offset warning triggers a re-translate; mtime advances after heal."""
    from subsideo import _cog

    cog = _write_cog(tmp_path / "ok.tif")

    calls = {"n": 0}
    real_validate = _cog.cog_validate

    def fake_validate(path: str | Path) -> tuple[bool, list[str], list[str]]:
        calls["n"] += 1
        if calls["n"] == 1:
            return (True, [], ["The offset of the main IFD should be 8 bytes"])
        return real_validate(path)

    monkeypatch.setattr(_cog, "cog_validate", fake_validate)
    before = cog.stat().st_mtime
    time.sleep(0.05)
    _cog.ensure_valid_cog(cog)
    after = cog.stat().st_mtime
    assert after > before


def test_ensure_valid_cog_heals_ifd_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """rio-cogeo 6.0.0 reports IFD-offset as an ERROR with is_valid=False.

    ``ensure_valid_cog`` must treat the IFD-offset error as heal-triggering
    (not a fatal RuntimeError).  This mirrors real behaviour observed on a
    COG after a rasterio ``update_tags`` call pushes the IFD past the 300-byte
    header -- which is the entire point of the P0.3 heal path.
    """
    from subsideo import _cog

    cog = _write_cog(tmp_path / "ok.tif")

    calls = {"n": 0}
    real_validate = _cog.cog_validate

    def fake_validate(path: str | Path) -> tuple[bool, list[str], list[str]]:
        calls["n"] += 1
        if calls["n"] == 1:
            return (
                False,
                [
                    "The offset of the main IFD should be < 300. It is 17128 instead",
                    "The offset of the first block of the image should be after its IFD",
                ],
                [],
            )
        return real_validate(path)

    monkeypatch.setattr(_cog, "cog_validate", fake_validate)
    before = cog.stat().st_mtime
    time.sleep(0.05)
    _cog.ensure_valid_cog(cog)  # must NOT raise
    after = cog.stat().st_mtime
    assert after > before


def test_ensure_valid_cog_raises_on_non_healable_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-IFD error (e.g. missing overview) is not a heal trigger; raise."""
    from subsideo import _cog

    cog = _write_cog(tmp_path / "ok.tif")

    def fake_validate(path: str | Path) -> tuple[bool, list[str], list[str]]:
        return (False, ["This file is not a valid GeoTIFF"], [])

    monkeypatch.setattr(_cog, "cog_validate", fake_validate)
    with pytest.raises(RuntimeError, match="not a valid COG"):
        _cog.ensure_valid_cog(cog)
