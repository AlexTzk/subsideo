"""Tests for src/subsideo/validation/harness.py — Phase 6 RETRY_POLICY['jrc'] branch."""
from __future__ import annotations

from typing import get_args

from subsideo.validation.harness import RETRY_POLICY, RetrySource


def test_jrc_retry_policy_present() -> None:
    assert "jrc" in RETRY_POLICY


def test_jrc_retry_policy_shape() -> None:
    policy = RETRY_POLICY["jrc"]
    assert 429 in policy["retry_on"]
    assert 503 in policy["retry_on"]
    assert 504 in policy["retry_on"]
    assert "ConnectionError" in policy["retry_on"]
    assert "TimeoutError" in policy["retry_on"]
    assert 401 in policy["abort_on"]
    assert 403 in policy["abort_on"]
    assert 404 in policy["abort_on"]
    assert policy["max_attempts"] == 5
    assert policy["backoff_factor"] == 2
    assert policy["max_backoff_s"] == 60


def test_retry_source_literal_includes_jrc() -> None:
    assert "jrc" in get_args(RetrySource)


def test_existing_retry_policies_unchanged() -> None:
    # CDSE / EARTHDATA / CLOUDFRONT / HTTPS / EFFIS shapes (Phase 1 + Phase 5 lock).
    for source in ("CDSE", "EARTHDATA", "CLOUDFRONT", "HTTPS", "EFFIS"):
        assert source in RETRY_POLICY, f"existing source {source!r} should be present"
        policy = RETRY_POLICY[source]
        assert "retry_on" in policy
        assert "abort_on" in policy
