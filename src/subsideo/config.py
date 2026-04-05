"""Pydantic v2 layered settings: env vars > .env > YAML > defaults."""
from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
from ruamel.yaml import YAML

T = TypeVar("T", bound=BaseModel)


class Settings(BaseSettings):
    """Global subsideo configuration.

    Precedence: init kwargs > env vars > .env file > YAML file > defaults.
    """

    cdse_client_id: str = Field(default="", description="CDSE OAuth2 client ID")
    cdse_client_secret: str = Field(default="", description="CDSE OAuth2 client secret")
    earthdata_username: str = Field(default="", description="NASA Earthdata username")
    earthdata_password: str = Field(default="", description="NASA Earthdata password")
    cdsapi_rc: Path = Field(
        default_factory=lambda: Path.home() / ".cdsapirc",
        description="CDS API key file path",
    )
    work_dir: Path = Field(
        default_factory=lambda: Path.cwd() / "work",
        description="Working directory for intermediate files",
    )
    cache_dir: Path = Field(
        default_factory=lambda: Path.home() / ".subsideo",
        description="Cache directory for downloaded data",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Add YAML as the lowest-priority config source."""
        return init_settings, env_settings, dotenv_settings, YamlConfigSettingsSource(settings_cls)


def dump_config(config: BaseModel, path: Path) -> None:
    """Serialize a Pydantic model to YAML (ISCE3 runconfig compatible).

    Uses ruamel.yaml round-trip mode with ``model_dump(mode="json")``
    to ensure Path objects become plain strings and no Python-specific
    YAML tags are emitted.
    """
    yaml = YAML()
    yaml.default_flow_style = False
    data = config.model_dump(mode="json")
    with open(path, "w") as fh:
        yaml.dump(data, fh)


def load_config(cls: type[T], path: Path) -> T:
    """Load a Pydantic model from a YAML file.

    Uses ``model_validate`` (not ``cls(**data)``) so that type coercion
    (e.g. str -> Path) works correctly on round-trip.
    """
    yaml = YAML()
    with open(path) as fh:
        data: dict[str, Any] = yaml.load(fh)
    return cls.model_validate(data)
