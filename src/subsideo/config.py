"""Pydantic v2 layered settings: env vars > .env > YAML > defaults."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, TypeVar

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

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
    dswx_region: Literal["nam", "eu"] = Field(
        default="nam",
        validation_alias="SUBSIDEO_DSWX_REGION",
        description=(
            "DSWx threshold region selector. SUBSIDEO_DSWX_REGION env var. "
            "Determines which DSWEThresholds instance run_dswx applies "
            "(THRESHOLDS_NAM = PROTEUS defaults; THRESHOLDS_EU = Phase 6 "
            "recalibrated). DSWxConfig.region (Plan 06-03) overrides per-call. "
            "Plan 06-02 D-10."
        ),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        yaml_file=None,
        extra="ignore",
        populate_by_name=True,
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

    Uses ``model_dump(mode="json")`` to ensure Path objects become plain
    strings and no Python-specific YAML tags are emitted.
    """
    data = config.model_dump(mode="json")
    with open(path, "w") as fh:
        yaml.dump(data, fh, default_flow_style=False, sort_keys=False)


def load_config(cls: type[T], path: Path) -> T:
    """Load a Pydantic model from a YAML file.

    Uses ``model_validate`` (not ``cls(**data)``) so that type coercion
    (e.g. str -> Path) works correctly on round-trip.
    """
    with open(path) as fh:
        data: dict[str, Any] = yaml.safe_load(fh)
    return cls.model_validate(data)
