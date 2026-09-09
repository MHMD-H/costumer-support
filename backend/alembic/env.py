"""Alembic environment for the backend PostgreSQL schema."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig
from os import getenv
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

from app.db.models import Base


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)

target_metadata = Base.metadata


def get_alembic_database_url() -> URL:
    """Return the configured PostgreSQL URL using Alembic's async driver."""
    database_url = getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set")

    # Tolerate a duplicated key prefix in local dotenv configuration.
    database_url = database_url.removeprefix("DATABASE_URL=")
    url = make_url(database_url)

    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+asyncpg")
    if url.drivername != "postgresql+asyncpg":
        raise RuntimeError("DATABASE_URL must use PostgreSQL with asyncpg")

    return url


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""
    context.configure(
        url=get_alembic_database_url().render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_server_default=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_server_default=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations through SQLAlchemy's async engine."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_alembic_database_url().render_as_string(hide_password=False)
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
