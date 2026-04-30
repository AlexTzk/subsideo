"""Unit tests for subsideo.validation.harness.

Covers the 6 public helpers (Plan 01-06 ENV-06 + ENV-08 MGRS-tile
migration) plus RETRY_POLICY abort/retry semantics and
ReferenceDownloadError behaviour.
"""
from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def test_public_api_importable() -> None:
    """Every public name + the exception class is importable."""
    from subsideo.validation.harness import (
        RETRY_POLICY,
        ReferenceDownloadError,
        bounds_for_burst,
        bounds_for_mgrs_tile,
        credential_preflight,
        download_reference_with_retry,
        ensure_resume_safe,
        select_opera_frame_by_utc_hour,
        validate_safe_path,
    )

    assert callable(bounds_for_burst)
    assert callable(bounds_for_mgrs_tile)
    assert callable(credential_preflight)
    assert callable(download_reference_with_retry)
    assert callable(ensure_resume_safe)
    assert callable(select_opera_frame_by_utc_hour)
    assert callable(validate_safe_path)
    assert isinstance(RETRY_POLICY, dict)
    assert issubclass(ReferenceDownloadError, Exception)


def test_retry_policy_shape() -> None:
    """RETRY_POLICY carries the 4 expected source keys with abort/retry lists."""
    from subsideo.validation.harness import RETRY_POLICY

    assert set(RETRY_POLICY.keys()) >= {"CDSE", "EARTHDATA", "CLOUDFRONT", "HTTPS"}

    # CDSE: 401/403/404 abort, 429 retry
    assert 401 in RETRY_POLICY["CDSE"]["abort_on"]
    assert 403 in RETRY_POLICY["CDSE"]["abort_on"]
    assert 404 in RETRY_POLICY["CDSE"]["abort_on"]
    assert 429 in RETRY_POLICY["CDSE"]["retry_on"]

    # EARTHDATA: 401 must abort (P0.4)
    assert 401 in RETRY_POLICY["EARTHDATA"]["abort_on"]
    assert 429 in RETRY_POLICY["EARTHDATA"]["retry_on"]
    assert 401 not in RETRY_POLICY["EARTHDATA"]["retry_on"]

    # CLOUDFRONT: 403 refreshes URL, not auto-retries
    assert RETRY_POLICY["CLOUDFRONT"].get("refresh_url_on") == [403]


def test_credential_preflight_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env var set to a non-empty value → no exception raised."""
    from subsideo.validation.harness import credential_preflight

    monkeypatch.setenv("SUBSIDEO_TEST_PREFLIGHT_VAR", "some_value")
    credential_preflight(["SUBSIDEO_TEST_PREFLIGHT_VAR"])  # must not raise


def test_credential_preflight_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing env var → SystemExit with clear message listing the missing name."""
    from subsideo.validation.harness import credential_preflight

    monkeypatch.delenv("SUBSIDEO_NONEXISTENT_PREFLIGHT_VAR", raising=False)
    with pytest.raises(SystemExit, match="SUBSIDEO_NONEXISTENT_PREFLIGHT_VAR"):
        credential_preflight(["SUBSIDEO_NONEXISTENT_PREFLIGHT_VAR"])


def test_credential_preflight_empty_string_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty-string env var is treated as missing."""
    from subsideo.validation.harness import credential_preflight

    monkeypatch.setenv("SUBSIDEO_EMPTY_PREFLIGHT_VAR", "")
    with pytest.raises(SystemExit, match="SUBSIDEO_EMPTY_PREFLIGHT_VAR"):
        credential_preflight(["SUBSIDEO_EMPTY_PREFLIGHT_VAR"])


def test_download_requires_explicit_source(tmp_path: Path) -> None:
    """Unknown source key must raise ValueError (PITFALLS P0.4 mitigation)."""
    from subsideo.validation.harness import download_reference_with_retry

    with pytest.raises(ValueError, match="unknown source"):
        download_reference_with_retry(
            "https://example.com/x.bin",
            tmp_path / "x.bin",
            source="UNKNOWN",  # type: ignore[arg-type]
        )


def test_download_abort_on_401_earthdata(tmp_path: Path) -> None:
    """Earthdata 401 must raise ReferenceDownloadError (abort_on)."""
    from subsideo.validation.harness import (
        ReferenceDownloadError,
        download_reference_with_retry,
    )

    fake_resp = MagicMock()
    fake_resp.status_code = 401
    fake_resp.__enter__ = lambda self: self
    fake_resp.__exit__ = lambda *a, **k: None

    fake_session = MagicMock()
    fake_session.get.return_value = fake_resp

    with pytest.raises(ReferenceDownloadError) as exc_info:
        download_reference_with_retry(
            "https://example.com/file.zip",
            tmp_path / "file.zip",
            source="EARTHDATA",
            session=fake_session,
            max_retries=1,
        )
    assert exc_info.value.status == 401
    assert exc_info.value.source == "EARTHDATA"


def test_download_cloudfront_403_raises(tmp_path: Path) -> None:
    """CloudFront 403 (refresh_url_on) raises ReferenceDownloadError (caller must refresh URL)."""
    from subsideo.validation.harness import (
        ReferenceDownloadError,
        download_reference_with_retry,
    )

    fake_resp = MagicMock()
    fake_resp.status_code = 403
    fake_resp.__enter__ = lambda self: self
    fake_resp.__exit__ = lambda *a, **k: None

    fake_session = MagicMock()
    fake_session.get.return_value = fake_resp

    with pytest.raises(ReferenceDownloadError):
        download_reference_with_retry(
            "https://d123.cloudfront.net/signed?X-Amz-Signature=abc",
            tmp_path / "file.zip",
            source="CLOUDFRONT",
            session=fake_session,
            max_retries=1,
        )


def test_ensure_resume_safe_missing_cache(tmp_path: Path) -> None:
    """Non-existent cache dir → returns False."""
    from subsideo.validation.harness import ensure_resume_safe

    assert ensure_resume_safe(tmp_path / "no-such-dir", ["a", "b"]) is False


def test_ensure_resume_safe_all_present(tmp_path: Path) -> None:
    """All manifest keys present → returns True."""
    from subsideo.validation.harness import ensure_resume_safe

    (tmp_path / "a").touch()
    (tmp_path / "b").touch()
    assert ensure_resume_safe(tmp_path, ["a", "b"]) is True


def test_ensure_resume_safe_partial(tmp_path: Path) -> None:
    """Some manifest keys missing → returns False (never raises)."""
    from subsideo.validation.harness import ensure_resume_safe

    (tmp_path / "a").touch()
    assert ensure_resume_safe(tmp_path, ["a", "b"]) is False


def test_select_opera_frame_unique() -> None:
    """Exactly one frame within tolerance → return that frame."""
    from datetime import datetime

    from subsideo.validation.harness import select_opera_frame_by_utc_hour

    frames = [
        {"id": "f1", "sensing_datetime": datetime(2024, 6, 24, 14, 5, 0)},
        {"id": "f2", "sensing_datetime": datetime(2024, 6, 24, 18, 0, 0)},
    ]
    r = select_opera_frame_by_utc_hour(datetime(2024, 6, 24, 14, 0, 0), frames)
    assert r["id"] == "f1"


def test_select_opera_frame_multiple_raises() -> None:
    """Multiple frames within tolerance → ValueError."""
    from datetime import datetime

    from subsideo.validation.harness import select_opera_frame_by_utc_hour

    frames = [
        {"id": "f1", "sensing_datetime": datetime(2024, 6, 24, 14, 5, 0)},
        {"id": "f2", "sensing_datetime": datetime(2024, 6, 24, 14, 30, 0)},
    ]
    with pytest.raises(ValueError, match="Multiple"):
        select_opera_frame_by_utc_hour(datetime(2024, 6, 24, 14, 0, 0), frames)


def test_select_opera_frame_none_raises() -> None:
    """No frames within tolerance → ValueError."""
    from datetime import datetime

    from subsideo.validation.harness import select_opera_frame_by_utc_hour

    frames = [{"id": "f1", "sensing_datetime": datetime(2024, 6, 24, 18, 0, 0)}]
    with pytest.raises(ValueError, match="No OPERA frame"):
        select_opera_frame_by_utc_hour(datetime(2024, 6, 24, 14, 0, 0), frames)


def test_select_opera_frame_parses_iso_strings() -> None:
    """ISO string sensing_datetime is accepted."""
    from datetime import datetime

    from subsideo.validation.harness import select_opera_frame_by_utc_hour

    frames = [{"id": "f1", "sensing_datetime": "2024-06-24T14:05:00Z"}]
    r = select_opera_frame_by_utc_hour(datetime(2024, 6, 24, 14, 0, 0), frames)
    assert r["id"] == "f1"


def test_bounds_for_burst_unknown_raises() -> None:
    """Unknown burst_id must raise ValueError mentioning both lookup failures."""
    from subsideo.validation.harness import bounds_for_burst

    with pytest.raises(ValueError):
        bounds_for_burst("bogus_nonexistent_burst_id_999", buffer_deg=0.0)


def test_bounds_for_mgrs_tile_known_33txp() -> None:
    """Known v1.1 tile (33TXP Lake Balaton) returns a valid 4-tuple of floats."""
    from subsideo.validation.harness import bounds_for_mgrs_tile

    result = bounds_for_mgrs_tile("33TXP", buffer_deg=0.1)
    assert isinstance(result, tuple)
    assert len(result) == 4
    west, south, east, north = result
    assert all(isinstance(v, float) for v in result)
    assert west < east, f"west {west} not < east {east}"
    assert south < north, f"south {south} not < north {north}"


def test_bounds_for_mgrs_tile_unknown_raises() -> None:
    """Unknown tile_id raises ValueError referencing the tile identifier."""
    from subsideo.validation.harness import bounds_for_mgrs_tile

    with pytest.raises(ValueError, match="BOGUS_TILE"):
        bounds_for_mgrs_tile("BOGUS_TILE_999", buffer_deg=0.0)


def test_bounds_for_mgrs_tile_buffer_symmetric() -> None:
    """Buffer must expand all 4 bounds symmetrically by buffer_deg."""
    from subsideo.validation.harness import bounds_for_mgrs_tile

    tight = bounds_for_mgrs_tile("33TXP", buffer_deg=0.0)
    loose = bounds_for_mgrs_tile("33TXP", buffer_deg=0.2)
    assert loose[0] == pytest.approx(tight[0] - 0.2)  # west
    assert loose[1] == pytest.approx(tight[1] - 0.2)  # south
    assert loose[2] == pytest.approx(tight[2] + 0.2)  # east
    assert loose[3] == pytest.approx(tight[3] + 0.2)  # north


def test_bounds_for_burst_buffer_symmetric() -> None:
    """bounds_for_burst buffer must be symmetric (N.Am. burst path via opera_utils)."""
    from subsideo.validation.harness import bounds_for_burst

    try:
        tight = bounds_for_burst("t144_308029_iw1", buffer_deg=0.0)
        loose = bounds_for_burst("t144_308029_iw1", buffer_deg=0.2)
    except ValueError as exc:
        pytest.skip(f"burst DB dependency unavailable in this test environment: {exc}")
    assert loose[0] == pytest.approx(tight[0] - 0.2)
    assert loose[1] == pytest.approx(tight[1] - 0.2)
    assert loose[2] == pytest.approx(tight[2] + 0.2)
    assert loose[3] == pytest.approx(tight[3] + 0.2)
    # Floats, ordered
    assert all(isinstance(v, float) for v in loose)
    assert loose[0] < loose[2]
    assert loose[1] < loose[3]


# ---------------------------------------------------------------------------
# Phase 2 additions: find_cached_safe (D-02) cross-cell SAFE cache reuse
# ---------------------------------------------------------------------------


def test_find_cached_safe_returns_none_when_no_hit(tmp_path: Path) -> None:
    from subsideo.validation.harness import find_cached_safe

    empty = tmp_path / "empty"
    empty.mkdir()
    missing = tmp_path / "does-not-exist"
    result = find_cached_safe("S1A_IW_SLC__1SDV_20240624", [empty, missing])
    assert result is None


def test_find_cached_safe_returns_first_match(tmp_path: Path) -> None:
    from subsideo.validation.harness import find_cached_safe

    d1 = tmp_path / "dir1"
    d2 = tmp_path / "dir2"
    d1.mkdir()
    d2.mkdir()
    granule = "S1A_IW_SLC__1SDV_20240624T140113"
    file1 = d1 / f"{granule}_20240624T140140_054466_06A0BA_20E5.zip"
    file2 = d2 / f"{granule}_20240624T140140_054466_06A0BA_20E5.zip"
    file1.write_bytes(b"")
    file2.write_bytes(b"")
    result = find_cached_safe(granule, [d1, d2], require_valid=False)
    assert result == file1


def test_find_cached_safe_substring_match_on_stem(tmp_path: Path) -> None:
    from subsideo.validation.harness import find_cached_safe

    d = tmp_path / "input"
    d.mkdir()
    full_name = "S1A_IW_SLC__1SDV_20240624T140113_20240624T140140_054466_06A0BA_20E5.zip"
    (d / full_name).write_bytes(b"")
    # Match on distinguishing prefix (not the full filename):
    result = find_cached_safe(
        "S1A_IW_SLC__1SDV_20240624T140113", [d], require_valid=False
    )
    assert result is not None
    assert result.name == full_name


def test_find_cached_safe_skips_nonexistent_dir(tmp_path: Path) -> None:
    from subsideo.validation.harness import find_cached_safe

    missing = tmp_path / "nope"
    real = tmp_path / "real"
    real.mkdir()
    granule = "S1A_IW_SLC__1SDV_20240624T140113"
    hit = real / f"{granule}_20240624T140140_054466_06A0BA_20E5.zip"
    hit.write_bytes(b"")
    result = find_cached_safe(granule, [missing, real], require_valid=False)
    assert result == hit


def test_find_cached_safe_skips_non_directory(tmp_path: Path) -> None:
    from subsideo.validation.harness import find_cached_safe

    not_a_dir = tmp_path / "regular_file.txt"
    not_a_dir.write_text("hello")
    real = tmp_path / "real"
    real.mkdir()
    granule = "S1A_IW_SLC__1SDV_20240624"
    hit = real / f"{granule}_XYZ.zip"
    hit.write_bytes(b"")
    result = find_cached_safe(granule, [not_a_dir, real], require_valid=False)
    assert result == hit


def test_find_cached_safe_exported_from_package() -> None:
    # Both import paths must work (harness module + package re-export).
    from subsideo.validation import find_cached_safe as pkg_fn
    from subsideo.validation.harness import find_cached_safe as mod_fn
    assert pkg_fn is mod_fn


def _write_safe_zip(path: Path, *, valid: bool = True) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        if valid:
            zf.writestr("S1.TEST.SAFE/manifest.safe", "<xml />")
            zf.writestr("S1.TEST.SAFE/measurement/data.tiff", b"payload")
        else:
            zf.writestr("README.txt", "not a SAFE")


def test_validate_safe_path_valid_zip(tmp_path: Path) -> None:
    from subsideo.validation.harness import validate_safe_path

    safe_zip = tmp_path / "valid.zip"
    _write_safe_zip(safe_zip)
    assert validate_safe_path(safe_zip) is True


def test_validate_safe_path_bad_zip(tmp_path: Path) -> None:
    from subsideo.validation.harness import validate_safe_path

    bad_zip = tmp_path / "bad.zip"
    bad_zip.write_bytes(b"not a zip")
    assert validate_safe_path(bad_zip) is False


def test_validate_safe_path_zip_without_safe_entries(tmp_path: Path) -> None:
    from subsideo.validation.harness import validate_safe_path

    not_safe = tmp_path / "not-safe.zip"
    _write_safe_zip(not_safe, valid=False)
    assert validate_safe_path(not_safe) is False


def test_validate_safe_path_valid_safe_directory(tmp_path: Path) -> None:
    from subsideo.validation.harness import validate_safe_path

    safe_dir = tmp_path / "S1.TEST.SAFE"
    (safe_dir / "measurement").mkdir(parents=True)
    (safe_dir / "manifest.safe").write_text("<xml />")
    (safe_dir / "measurement" / "data.tiff").write_bytes(b"payload")
    assert validate_safe_path(safe_dir) is True


def test_validate_safe_path_invalid_safe_directory(tmp_path: Path) -> None:
    from subsideo.validation.harness import validate_safe_path

    safe_dir = tmp_path / "S1.TEST.SAFE"
    (safe_dir / "measurement").mkdir(parents=True)
    (safe_dir / "measurement" / "data.tiff").write_bytes(b"payload")
    assert validate_safe_path(safe_dir) is False


def test_find_cached_safe_skips_invalid_first_match(tmp_path: Path) -> None:
    from subsideo.validation.harness import find_cached_safe

    d1 = tmp_path / "dir1"
    d2 = tmp_path / "dir2"
    d1.mkdir()
    d2.mkdir()
    granule = "S1A_IW_SLC__1SDV_20240624T140113"
    invalid = d1 / f"{granule}_bad.zip"
    valid = d2 / f"{granule}_good.zip"
    invalid.write_bytes(b"not a zip")
    _write_safe_zip(valid)
    assert find_cached_safe(granule, [d1, d2]) == valid


def test_validate_safe_path_exported_from_package() -> None:
    from subsideo.validation import validate_safe_path as pkg_fn
    from subsideo.validation.harness import validate_safe_path as mod_fn

    assert pkg_fn is mod_fn


def test_find_cached_safe_oserror_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pathlib import Path as _Path

    from subsideo.validation.harness import find_cached_safe

    d = tmp_path / "restricted"
    d.mkdir()
    granule = "S1A_IW_SLC__1SDV_20240624"

    def _raise(self: _Path) -> None:  # pragma: no cover - replaced via monkeypatch
        raise PermissionError("simulated EACCES")

    monkeypatch.setattr(_Path, "iterdir", _raise)
    # Must return None (not raise) on PermissionError during iterdir.
    result = find_cached_safe(granule, [d])
    assert result is None
