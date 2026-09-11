# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    host: str = Field(default="0.0.0.0", alias="HITL_GATEWAY_HOST")
    port: int = Field(default=8080, alias="HITL_GATEWAY_PORT")


def get_app_config() -> AppConfig:
    return AppConfig()


__all__ = ['AppConfig', 'get_app_config']
