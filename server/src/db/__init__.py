# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import asyncio
import logging
from collections.abc import AsyncGenerator

from alembic.command import upgrade
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import DatabaseConfig, get_db_config

logger = logging.getLogger(__name__)

_async_engine = None
_async_session_maker = None


def run_migrations(db_config: DatabaseConfig) -> None:
    """Run Alembic migrations."""
    from pathlib import Path

    alembic_dir = Path(__file__).parent / "alembic"
    alembic_ini = Path(__file__).parent.parent.parent / "alembic.ini"

    if not alembic_dir.exists() or not alembic_ini.exists():
        logger.warning(
            "Alembic directory or configuration not found, skipping migrations"
        )
        return

    logger.info("Running database migrations")

    alembic_config.set_main_option(
        "sqlalchemy.url", db_config.url.replace("%", "%%").replace("+psycopg", "")
    )
    alembic_config.set_main_option("script_location", str(alembic_dir))

    try:
        upgrade(alembic_config, "head")
        logger.info("Database migrations completed successfully")
    except Exception:
        logger.exception("Failed to run migrations")
        raise


async def _create_dummy_data() -> None:
    async with _async_session_maker() as session:
        await session.execute(
            text(
                "INSERT INTO tenants (ID, NAME) VALUES ('00000000-0000-0000-0000-000000000000', 'Test tenant') ON CONFLICT DO NOTHING"
            )
        )
        await session.commit()


async def init_db() -> None:
    """Initialize database connection on startup with retry logic."""
    global _async_engine, _async_session_maker

    db_config = get_db_config()
    logger.info(
        f"Connecting to database: {db_config.host}:{db_config.port}/{db_config.database}"
    )

    if db_config.run_migrations:
        run_migrations(db_config)

    _async_engine = create_async_engine(
        db_config.url,
        echo=False,
        pool_pre_ping=True,
    )

    _async_session_maker = sessionmaker(
        _async_engine, class_=AsyncSession, expire_on_commit=False
    )

    if db_config.create_dummy_data:
        max_retries = 10
        retry_delay = 1
        for attempt in range(max_retries):
            try:
                await _create_dummy_data()
                break
            except OperationalError as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Failed to connect to database (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {retry_delay}s: {e}"
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 1.5, 5)
                else:
                    logger.error("Failed to connect to database after all retries")
                    raise

    logger.info("Database connection initialized")


async def close_db() -> None:
    """Close database connection on shutdown."""
    if _async_engine:
        await _async_engine.dispose()
        logger.info("Database connection closed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting a database session."""
    if not _async_session_maker:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _async_session_maker() as session:
        yield session


__all__ = ["close_db", "get_session", "init_db"]
