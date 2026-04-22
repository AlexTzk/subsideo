"""Unit tests for subsideo.validation.harness.

Covers the 6 public helpers (Plan 01-06 ENV-06 + ENV-08 MGRS-tile
migration) plus RETRY_POLICY abort/retry semantics and
ReferenceDownloadError behaviour.
"""
from __future__ import annotations

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
    )

    assert callable(bounds_for_burst)
    assert callable(bounds_for_mgrs_tile)
    assert callable(credential_preflight)
    assert callable(download_reference_with_retry)
    assert callable(ensure_resume_safe)
    assert callable(select_opera_frame_by_utc_hour)
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

    tight = bounds_for_burst("t144_308029_iw1", buffer_deg=0.0)
    loose = bounds_for_burst("t144_308029_iw1", buffer_deg=0.2)
    assert loose[0] == pytest.approx(tight[0] - 0.2)
    assert loose[1] == pytest.approx(tight[1] - 0.2)
    assert loose[2] == pytest.approx(tight[2] + 0.2)
    assert loose[3] == pytest.approx(tight[3] + 0.2)
    # Floats, ordered
    assert all(isinstance(v, float) for v in loose)
    assert loose[0] < loose[2]
    assert loose[1] < loose[3]
