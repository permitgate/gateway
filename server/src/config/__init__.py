# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    host: str = Field(default="0.0.0.0", alias="HITL_GATEWAY_HOST")
    port: int = Field(default=8080, alias="HITL_GATEWAY_PORT")


class DatabaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    host: str = Field(default="localhost", alias="DB_HOST")
    port: int = Field(default=5432, alias="DB_PORT")
    user: str = Field(default="postgres", alias="DB_USER")
    password: str = Field(default="postgres", alias="DB_PASSWORD")
    database: str = Field(default="gateway", alias="DB_NAME")
    run_migrations: bool = Field(default=True, alias="DB_RUN_MIGRATIONS")
    create_dummy_data: bool = Field(default=True, alias="DB_CREATE_DUMMY_DATA")

    @property
    def url(self) -> str:
        return f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


def get_app_config() -> AppConfig:
    return AppConfig()


def get_db_config() -> DatabaseConfig:
    return DatabaseConfig()


__all__ = ["AppConfig", "DatabaseConfig", "get_app_config", "get_db_config"]
