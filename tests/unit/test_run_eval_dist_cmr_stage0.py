"""Unit tests for run_eval_dist.py Stage 0 CMR probe + DEFERRED metrics.json
contract + CONTEXT D-16 archival hook (Plan 05-06 Task 2).

Phase 5 otherwise only validates the deferred-cell metrics.json contract via
live `make eval-dist-nam` (Plan 05-08 Task 4 smoke test) which requires real
Earthdata creds. These tests close that gap by mocking earthaccess and
driving the three CMR-outcome branches directly.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from subsideo.validation.matrix_schema import DistNamCellMetrics, MetaJson


def _import_run_eval_dist() -> object:
    """Load run_eval_dist.py as a module (the file lives at the repo root,
    not under src/, so it's not on the package path)."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    script_path = repo_root / "run_eval_dist.py"
    spec = importlib.util.spec_from_file_location("run_eval_dist", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fake_earthdata_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the env vars credential_preflight checks for so the script
    doesn't SystemExit before reaching the CMR probe."""
    monkeypatch.setenv("EARTHDATA_USERNAME", "test_user")
    monkeypatch.setenv("EARTHDATA_PASSWORD", "test_pass")


@pytest.fixture
def isolated_eval_dist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run the eval script with cwd = tmp_path so eval-dist/ is created
    in isolation."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _make_mocked_auth() -> object:
    """Mock object satisfying earthaccess.login(strategy='environment')."""

    class FakeAuth:
        authenticated = True

    return FakeAuth()


def test_operational_not_found_writes_deferred_metrics(
    fake_earthdata_env: None, isolated_eval_dist: Path
) -> None:
    """Empty CMR result → DEFERRED metrics.json with operational_not_found."""
    module = _import_run_eval_dist()

    import earthaccess

    with (
        patch.object(earthaccess, "login", return_value=_make_mocked_auth()),
        patch.object(earthaccess, "search_data", return_value=[]),
    ):
        rc = module.run()  # type: ignore[attr-defined]

    assert rc == 0

    metrics_path = isolated_eval_dist / "eval-dist" / "metrics.json"
    assert metrics_path.exists(), "Stage 1 must write metrics.json on operational_not_found"

    metrics = DistNamCellMetrics.model_validate_json(metrics_path.read_text())
    assert metrics.cell_status == "DEFERRED"
    assert metrics.reference_source == "none"
    assert metrics.cmr_probe_outcome == "operational_not_found"
    assert metrics.reference_granule_id is None

    # Blocker 1 contract verification: meta.json uses actual MetaJson field names
    meta_path = isolated_eval_dist / "eval-dist" / "meta.json"
    assert meta_path.exists()
    meta = MetaJson.model_validate_json(meta_path.read_text())  # extra='forbid' is the contract
    assert meta.git_sha  # non-empty
    assert meta.run_started_iso  # populated
    assert meta.run_duration_s >= 0
    assert meta.python_version
    assert meta.platform
    assert meta.input_hashes == {}


def test_probe_failed_writes_deferred_metrics_with_failed_outcome(
    fake_earthdata_env: None, isolated_eval_dist: Path
) -> None:
    """earthaccess.search_data raises ConnectionError → cmr_probe_outcome='probe_failed'."""
    module = _import_run_eval_dist()

    import earthaccess

    with (
        patch.object(earthaccess, "login", return_value=_make_mocked_auth()),
        patch.object(
            earthaccess, "search_data", side_effect=ConnectionError("simulated network outage")
        ),
    ):
        rc = module.run()  # type: ignore[attr-defined]

    assert rc == 0  # script does NOT crash on probe failure; deferred path absorbs

    metrics_path = isolated_eval_dist / "eval-dist" / "metrics.json"
    metrics = DistNamCellMetrics.model_validate_json(metrics_path.read_text())
    assert metrics.cell_status == "DEFERRED"
    assert metrics.reference_source == "none"
    assert metrics.cmr_probe_outcome == "probe_failed"


def test_operational_found_archives_existing_metrics_and_raises(
    fake_earthdata_env: None, isolated_eval_dist: Path
) -> None:
    """Non-empty CMR result → CONTEXT D-16 archival + NotImplementedError.

    Pre-populates eval-dist/metrics.json with a placeholder (simulating a
    prior Phase 5 invocation's deferred metrics.json). Verifies the archival
    hook moves it to eval-dist/archive/v0.1_metrics_*.json BEFORE the
    operational-pipeline-not-implemented signal raises.
    """
    module = _import_run_eval_dist()

    eval_dist = isolated_eval_dist / "eval-dist"
    eval_dist.mkdir()
    pre_existing = eval_dist / "metrics.json"
    pre_existing.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "cell_status": "DEFERRED",
                "reference_source": "none",
                "cmr_probe_outcome": "operational_not_found",
                "reference_granule_id": None,
                "deferred_reason": "prior Phase 5 deferred run",
                "product_quality": {"measurements": {}, "criterion_ids": []},
                "reference_agreement": {"measurements": {}, "criterion_ids": []},
                "criterion_ids_applied": [],
            }
        )
    )

    # Mock granule object that earthaccess.search_data would return on a hit.
    class FakeGranule:
        def render_dict(self) -> dict:
            return {"meta": {"concept-id": "G3000000000-LPCLOUD"}}

    import earthaccess

    with (
        patch.object(earthaccess, "login", return_value=_make_mocked_auth()),
        patch.object(earthaccess, "search_data", return_value=[FakeGranule()]),
        pytest.raises(NotImplementedError) as exc_info,
    ):
        module.run()  # type: ignore[attr-defined]

    msg = str(exc_info.value)
    assert "v1.2" in msg, f"NotImplementedError must point at v1.2; got: {msg}"
    assert any(
        s in msg for s in ("CONTEXT D-16", "archived", "archive/")
    ), f"NotImplementedError must mention D-16 archival; got: {msg}"

    # CONTEXT D-16 archival assertion
    archive_dir = eval_dist / "archive"
    assert archive_dir.exists() and archive_dir.is_dir(), (
        "D-16 requires eval-dist/archive/ directory"
    )

    archived_files = list(archive_dir.glob("v0.1_metrics_*.json"))
    assert len(archived_files) == 1, (
        f"Expected exactly one archived file matching v0.1_metrics_*.json; "
        f"found: {[f.name for f in archived_files]}"
    )

    # The archived file should contain the pre-existing content
    archived_content = json.loads(archived_files[0].read_text())
    assert archived_content["deferred_reason"] == "prior Phase 5 deferred run"

    # The original metrics.json should no longer exist at its old location
    # (the archival was a move, not a copy).
    assert not pre_existing.exists(), (
        "CONTEXT D-16 archival is move-not-copy; old metrics.json should be gone"
    )


def test_operational_found_archives_when_no_prior_metrics_exist(
    fake_earthdata_env: None, isolated_eval_dist: Path
) -> None:
    """If eval-dist/metrics.json does NOT pre-exist on operational_found,
    archival is a no-op (no archive directory needed, no error)."""
    module = _import_run_eval_dist()

    class FakeGranule:
        def render_dict(self) -> dict:
            return {"meta": {"concept-id": "G3000000001-LPCLOUD"}}

    import earthaccess

    with (
        patch.object(earthaccess, "login", return_value=_make_mocked_auth()),
        patch.object(earthaccess, "search_data", return_value=[FakeGranule()]),
        pytest.raises(NotImplementedError),
    ):
        module.run()  # type: ignore[attr-defined]

    archive_dir = isolated_eval_dist / "eval-dist" / "archive"
    if archive_dir.exists():
        assert list(archive_dir.glob("*.json")) == [], (
            "No prior metrics.json existed → no archival should occur"
        )
