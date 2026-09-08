"""Explicit PostgreSQL seed command for deployment workflows."""

from cinema.config import StorageBackend, load_settings
from cinema.exceptions import ConfigurationError
from cinema.storage.sqlalchemy_backend import create_database_engine
from cinema.storage.sqlalchemy_seed import seed_cinema


def main() -> None:
    """Seed the selected relational database after migrations have completed."""
    settings = load_settings()
    if settings.storage_backend is not StorageBackend.NEON:
        raise ConfigurationError("cinema-db-seed currently supports STORAGE_BACKEND=neon")
    engine = create_database_engine(settings.neon_database_url)
    try:
        seed_cinema(engine)
    finally:
        engine.dispose()
    print("Cinema database seed data is ready.")
