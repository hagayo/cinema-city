"""Alembic environment for the PostgreSQL-compatible storage adapter."""

from alembic import context
from sqlalchemy import create_engine, pool

from cinema.config import StorageBackend, load_settings
from cinema.exceptions import ConfigurationError
from cinema.storage.sqlalchemy_backend import normalize_database_url
from cinema.storage.sqlalchemy_schema import metadata

config = context.config
target_metadata = metadata


def _database_url() -> str:
    configured_url = config.get_main_option("sqlalchemy.url").strip()
    if configured_url:
        return normalize_database_url(configured_url)
    settings = load_settings()
    if settings.storage_backend is not StorageBackend.NEON:
        raise ConfigurationError("Alembic migrations require STORAGE_BACKEND=neon")
    return normalize_database_url(settings.neon_database_url)


def run_migrations_offline() -> None:
    """Render migrations as SQL without opening a database connection."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations transactionally to the configured database."""
    engine = create_engine(_database_url(), poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
