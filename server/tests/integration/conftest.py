# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import asyncio
import sys
import time
from pathlib import Path

import docker
import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
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

        # Wait for container to be healthy by attempting a real TCP connection
        # to the mapped host port. This avoids the false-positive from pg_isready
        # targeting the temporary init socket on first boot.
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                with psycopg.connect(
                    host="localhost",
                    port=POSTGRES_PORT,
                    user=POSTGRES_USER,
                    password=POSTGRES_PASSWORD,
                    dbname=POSTGRES_DB,
                    connect_timeout=1,
                ):
                    break
            except psycopg.OperationalError:
                time.sleep(0.5)
        else:
            raise RuntimeError("PostgreSQL container did not become ready")

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
    # Run migrations with retry/backoff for transient connection failures
    max_retries = 10
    retry_delay = 1
    for attempt in range(max_retries):
        try:
            run_migrations(test_db_config)
            break
        except OperationalError:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 5)
            else:
                raise

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
        await test_session.execute(
            text("UPDATE approval_flows SET active_version_id = NULL")
        )
        await test_session.execute(text("DELETE FROM flow_versions"))
        await test_session.execute(text("DELETE FROM approval_flows"))
        await test_session.execute(text("DELETE FROM users"))
        await test_session.execute(text("DELETE FROM tenants"))
        await test_session.commit()
    except Exception:  # noqa: BLE001
        await test_session.rollback()
