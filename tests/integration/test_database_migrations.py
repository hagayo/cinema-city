"""Integration tests for the versioned relational schema lifecycle."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select

from cinema.storage.sqlalchemy_schema import cinemas, halls, seats
from cinema.storage.sqlalchemy_seed import seed_cinema

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOMAIN_TABLES = {
    "booking_seats",
    "bookings",
    "cinemas",
    "halls",
    "movies",
    "seats",
    "shows",
    "users",
}


def _config(database_url: str) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_initial_migration_seed_and_downgrade(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'migration.db'}"
    config = _config(database_url)

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    assert DOMAIN_TABLES <= set(inspect(engine).get_table_names())
    assert {
        constraint["name"] for constraint in inspect(engine).get_unique_constraints("booking_seats")
    } == {
        "uq_booking_seats_booking_id_seat_id",
        "uq_booking_seats_show_id_seat_id",
    }

    seed_cinema(engine)
    seed_cinema(engine)
    with engine.connect() as connection:
        assert len(connection.execute(select(cinemas)).all()) == 1
        assert len(connection.execute(select(halls)).all()) == 3
        assert len(connection.execute(select(seats)).all()) == 1200
    engine.dispose()

    command.check(config)
    command.downgrade(config, "base")
    downgraded_engine = create_engine(database_url)
    assert DOMAIN_TABLES.isdisjoint(inspect(downgraded_engine).get_table_names())
    downgraded_engine.dispose()


def test_schema_sql_contains_complete_initial_snapshot() -> None:
    schema_sql = (PROJECT_ROOT / "database" / "schema.sql").read_text(encoding="utf-8")
    assert "20260828_0001" in schema_sql
    for table_name in DOMAIN_TABLES:
        assert f"CREATE TABLE {table_name}" in schema_sql
    assert "uq_booking_seats_show_id_seat_id" in schema_sql
