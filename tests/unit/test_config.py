"""Unit tests for subsideo.config — Settings layered config, YAML round-trip, ISCE3 compatibility."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from pydantic_settings import SettingsConfigDict, YamlConfigSettingsSource, PydanticBaseSettingsSource
from subsideo.config import Settings, dump_config, load_config


def _make_yaml_settings(yaml_path: Path, env_file: str = "nonexistent.env") -> type[Settings]:
    """Create a Settings subclass wired to a specific YAML file.

    pydantic-settings reads ``yaml_file`` from ``model_config``, not from
    init kwargs. We dynamically create a subclass with the path baked in.
    """

    class _S(Settings):
        model_config = SettingsConfigDict(
            yaml_file=str(yaml_path),
            env_file=env_file,
            env_file_encoding="utf-8",
            extra="ignore",
        )

        @classmethod
        def settings_customise_sources(
            cls,
            settings_cls: type[Settings],  # type: ignore[override]
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
        ) -> tuple[PydanticBaseSettingsSource, ...]:
            return (
                init_settings,
                env_settings,
                dotenv_settings,
                YamlConfigSettingsSource(settings_cls),
            )

    return _S


def test_env_var_loading(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings picks up CDSE_CLIENT_ID from environment variables."""
    monkeypatch.setenv("CDSE_CLIENT_ID", "test_id_from_env")
    monkeypatch.setenv("CDSE_CLIENT_SECRET", "test_secret")
    s = Settings()
    assert s.cdse_client_id == "test_id_from_env"
    assert s.cdse_client_secret == "test_secret"


def test_dotenv_loading(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Settings loads values from a .env file when env vars are absent."""
    monkeypatch.delenv("CDSE_CLIENT_ID", raising=False)
    monkeypatch.delenv("CDSE_CLIENT_SECRET", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("CDSE_CLIENT_ID=from_dotenv\nCDSE_CLIENT_SECRET=secret_dotenv\n")
    s = Settings(_env_file=str(env_file))
    assert s.cdse_client_id == "from_dotenv"
    assert s.cdse_client_secret == "secret_dotenv"


def test_yaml_loading(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Settings loads values from a YAML file as lowest-priority source."""
    monkeypatch.delenv("CDSE_CLIENT_ID", raising=False)
    monkeypatch.delenv("CDSE_CLIENT_SECRET", raising=False)
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(yaml.dump({"cdse_client_id": "from_yaml", "cdse_client_secret": "yaml_secret"}))
    YamlSettings = _make_yaml_settings(yaml_file)
    s = YamlSettings()
    assert s.cdse_client_id == "from_yaml"
    assert s.cdse_client_secret == "yaml_secret"


def test_env_overrides_yaml(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Env var takes precedence over YAML value for the same key."""
    monkeypatch.setenv("CDSE_CLIENT_ID", "from_env")
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(yaml.dump({"cdse_client_id": "from_yaml"}))
    YamlSettings = _make_yaml_settings(yaml_file)
    s = YamlSettings()
    assert s.cdse_client_id == "from_env"


def test_yaml_round_trip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A config round-tripped through YAML produces a model that compares equal."""
    monkeypatch.delenv("CDSE_CLIENT_ID", raising=False)
    monkeypatch.delenv("CDSE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("EARTHDATA_USERNAME", raising=False)
    monkeypatch.delenv("EARTHDATA_PASSWORD", raising=False)
    original = Settings(
        cdse_client_id="roundtrip_id",
        cdse_client_secret="roundtrip_secret",
        work_dir=Path("/tmp/work"),
        cache_dir=Path("/tmp/cache"),
        _env_file="nonexistent.env",
    )
    yaml_path = tmp_path / "roundtrip.yaml"
    dump_config(original, yaml_path)
    loaded = load_config(Settings, yaml_path)
    assert loaded.cdse_client_id == original.cdse_client_id
    assert loaded.cdse_client_secret == original.cdse_client_secret
    assert loaded.work_dir == original.work_dir
    assert loaded.cache_dir == original.cache_dir


def test_path_fields_are_path_instances() -> None:
    """Settings.cache_dir is a Path instance, not a string."""
    s = Settings(_env_file="nonexistent.env")
    assert isinstance(s.cache_dir, Path)
    assert isinstance(s.work_dir, Path)
    assert isinstance(s.cdsapi_rc, Path)


def test_model_validate_coerces_path(tmp_path: Path) -> None:
    """YAML dump/load of a model with Path fields restores them as Path, not str."""
    original = Settings(
        work_dir=Path("/tmp/test_work"),
        _env_file="nonexistent.env",
    )
    yaml_path = tmp_path / "path_test.yaml"
    dump_config(original, yaml_path)
    loaded = load_config(Settings, yaml_path)
    assert isinstance(loaded.work_dir, Path)
    assert loaded.work_dir == Path("/tmp/test_work")


def test_isce3_yaml_compatibility(tmp_path: Path) -> None:
    """dump_config produces ISCE3-compatible YAML: mapping, snake_case keys, no Python tags."""
    settings = Settings(
        cdse_client_id="test",
        cdse_client_secret="secret",
        work_dir=Path("/tmp/work"),
        _env_file="nonexistent.env",
    )
    yaml_path = tmp_path / "isce3_compat.yaml"
    dump_config(settings, yaml_path)

    # Load and verify structure
    with open(yaml_path) as fh:
        data = yaml.safe_load(fh)

    # Top-level is a mapping (dict), not a sequence or scalar
    assert isinstance(data, dict), f"Expected mapping, got {type(data)}"

    # All keys are lowercase snake_case
    for key in data:
        assert re.fullmatch(r"[a-z][a-z0-9_]*", key), f"Key {key!r} is not lowercase snake_case"

    # No Python-specific YAML tags
    raw_text = yaml_path.read_text()
    assert "!!python" not in raw_text, "Found Python-specific YAML tag in output"
