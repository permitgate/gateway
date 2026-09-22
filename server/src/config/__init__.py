# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    host: str = Field(default="0.0.0.0", alias="GATEWAY_HOST")
    port: int = Field(default=8080, alias="GATEWAY_PORT")
    flow_schema_max_size_bytes: int = Field(
        default=65536, alias="FLOW_SCHEMA_MAX_SIZE_BYTES"
    )
    flow_schema_max_depth: int = Field(default=5, alias="FLOW_SCHEMA_MAX_DEPTH")
    flow_schema_max_keys: int = Field(default=100, alias="FLOW_SCHEMA_MAX_KEYS")
    flow_schema_max_pattern_length: int = Field(
        default=200, alias="FLOW_SCHEMA_MAX_PATTERN_LENGTH"
    )


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
        return str(
            URL.create(
                drivername="postgresql+psycopg",
                username=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                database=self.database,
            )
        )


def get_app_config() -> AppConfig:
    return AppConfig()


def get_db_config() -> DatabaseConfig:
    return DatabaseConfig()


__all__ = ["AppConfig", "DatabaseConfig", "get_app_config", "get_db_config"]
