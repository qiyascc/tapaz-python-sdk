from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlsplit

from goodconf import Field, GoodConf, GoodConfConfigDict
from pydantic import BaseModel, SecretStr, field_validator

from ._version import __version__
from .errors import ConfigurationError
from .messages import text

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
ADDRESSES = ("site_url", "graphql_url", "photos_url", "auth_url", "return_to")


class Endpoints(BaseModel):
    photo_upload: str = "/pond"
    photo_rotate: str = "/pond/rotate"
    send_code: str = "/auth"
    verify_code: str = "/auth/verify"


class Settings(GoodConf):
    model_config = GoodConfConfigDict(
        env_prefix="TAPAZ_",
        file_env_var="TAPAZ_CONFIG",
        default_files=["tapaz.toml", "tapaz.yaml", "tapaz.yml", "tapaz.json"],
        extra="ignore",
        env_nested_delimiter="__",
    )

    cookie: SecretStr = Field(default=SecretStr(""), description=text("settings.cookie"))
    site_url: str = Field(default="https://tap.az", description=text("settings.site_url"))
    graphql_url: str = Field(default="https://tap.az/graphql", description=text("settings.graphql_url"))
    photos_url: str = Field(default="https://photos.tap.az", description=text("settings.photos_url"))
    auth_url: str = Field(default="https://api.digit-u.id", description=text("settings.auth_url"))
    return_to: str = Field(default="https://tap.az/", description=text("settings.return_to"))
    endpoints: Endpoints = Field(default_factory=Endpoints, description=text("settings.endpoints"))
    language: str = Field(default="az", description=text("settings.language"))
    source: str = Field(default="DESKTOP", description=text("settings.source"))
    default_region: str = Field(default="420", description=text("settings.default_region"))
    delete_reason: str = Field(default="6", description=text("settings.delete_reason"))
    timeout: float = Field(default=30.0, gt=0, description=text("settings.timeout"))
    connect_timeout: float = Field(default=10.0, gt=0, description=text("settings.connect_timeout"))
    max_retries: int = Field(default=2, ge=0, le=10, description=text("settings.max_retries"))
    login_retries: int = Field(default=2, ge=0, le=10, description=text("settings.login_retries"))
    backoff_base: float = Field(default=0.6, ge=0, description=text("settings.backoff_base"))
    backoff_cap: float = Field(default=8.0, ge=0, description=text("settings.backoff_cap"))
    user_agent: str = Field(default="tapaz-python-sdk/{version}", description=text("settings.user_agent"))
    allow_insecure_http: bool = Field(default=False, description=text("settings.allow_insecure_http"))

    @field_validator(*ADDRESSES)
    @classmethod
    def _address(cls, value: str) -> str:
        parts = urlsplit(value.strip())
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError(text("error.base_url", field="address", url=value))
        return value.strip() if value.strip().endswith("/") and parts.path == "/" else value.strip().rstrip("/")

    def check_transport(self) -> None:
        for name in ADDRESSES:
            url = getattr(self, name)
            parts = urlsplit(url)
            if parts.scheme == "https" or self.allow_insecure_http or parts.hostname in LOCAL_HOSTS:
                continue
            raise ConfigurationError(text("error.insecure", url=url))

    def resolved_user_agent(self) -> str:
        return self.user_agent.replace("{version}", __version__)


Settings.__doc__ = text("settings.description")


def load_settings(config_file: Optional[str] = None, **overrides: Any) -> Settings:
    given = {key: value for key, value in overrides.items() if value is not None}
    return Settings(load=True, config_file=config_file, **given)
