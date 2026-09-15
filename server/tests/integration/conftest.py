# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import asyncio
import sys
from pathlib import Path

import docker
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from config import DatabaseConfig
from db import run_migrations

POSTGRES_IMAGE = "postgres:16-alpine"
POSTGRES_PORT = 5433
POSTGRES_USER = "gateway_test"
POSTGRES_PASSWORD = "gateway_test"
POSTGRES_DB = "gateway_test"


@pytest.fixture(scope="session")
def monkeypatch_session():
    """Provide a monkeypatch for session scope."""
    from _pytest.monkeypatch import MonkeyPatch

    m = MonkeyPatch()
    yield m
    m.undo()


@pytest.fixture(scope="session")
def docker_container():
    """Start a PostgreSQL Docker container for testing."""
    client = docker.from_env()

    try:
        container = client.containers.run(
            POSTGRES_IMAGE,
            environment={
                "POSTGRES_USER": POSTGRES_USER,
                "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
                "POSTGRES_DB": POSTGRES_DB,
                "POSTGRES_HOST_AUTH_METHOD": "trust",
            },
            ports={"5432/tcp": POSTGRES_PORT},
            detach=True,
            remove=True,
        )

        # Wait for container to be healthy
        import time

        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                container.reload()
                health_status = (
                    container.attrs.get("State", {}).get("Health", {}).get("Status")
                )
                if health_status == "healthy":
                    break
                time.sleep(0.5)
            except Exception:
                time.sleep(0.5)

        yield container

        container.stop()
    except Exception as e:
        print(f"Failed to start PostgreSQL container: {e}")
        raise


@pytest.fixture(scope="session")
def test_db_config(docker_container, monkeypatch_session):
    """Create a database config for the test PostgreSQL instance."""
    # Set environment variables for DatabaseConfig
    monkeypatch_session.setenv("DB_HOST", "localhost")
    monkeypatch_session.setenv("DB_PORT", str(POSTGRES_PORT))
    monkeypatch_session.setenv("DB_USER", POSTGRES_USER)
    monkeypatch_session.setenv("DB_PASSWORD", POSTGRES_PASSWORD)
    monkeypatch_session.setenv("DB_NAME", POSTGRES_DB)
    monkeypatch_session.setenv("DB_RUN_MIGRATIONS", "false")
    monkeypatch_session.setenv("DB_CREATE_DUMMY_DATA", "false")

    return DatabaseConfig()


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine(test_db_config, event_loop):
    """Create a test database engine and run migrations."""
    # Run migrations
    run_migrations(test_db_config)

    # Create engine
    engine = create_async_engine(
        test_db_config.url,
        echo=False,
        pool_pre_ping=True,
    )

    yield engine

    await engine.dispose()


@pytest.fixture(scope="session")
async def test_session_maker(test_engine):
    """Create a session maker for the test database."""
    return sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def test_session(test_session_maker):
    """Create a test database session."""
    async with test_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture(autouse=True)
async def cleanup_database(test_session):
    """Clean up the database after each test."""
    yield

    # Delete all data to ensure clean state for next test
    try:
        await test_session.execute(text("DELETE FROM flow_versions"))
        await test_session.execute(text("DELETE FROM approval_flows"))
        await test_session.execute(
            text(
                "DELETE FROM tenants WHERE id != '00000000-0000-0000-0000-000000000000'"
            )
        )
        await test_session.commit()
    except Exception:
        await test_session.rollback()
