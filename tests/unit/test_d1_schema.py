"""Contract tests for the future Cloudflare D1 SQL schema."""

import sqlite3
from pathlib import Path

import pytest


SCHEMA_FILE = Path(__file__).parents[2] / "d1" / "schema.sql"


@pytest.fixture
def database() -> sqlite3.Connection:
    """Create an in-memory SQLite database using the exact D1 schema."""
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
    yield connection
    connection.close()


def seed_catalog(database: sqlite3.Connection) -> None:
    """Insert the minimum valid rows needed by booking tests."""
    database.execute(
        "INSERT INTO cinemas (cinema_id, name) VALUES (?, ?)",
        (1, "Cinema City"),
    )
    database.execute(
        "INSERT INTO halls (hall_id, cinema_id, hall_name) VALUES (?, ?, ?)",
        (1, 1, "Hall Alpha"),
    )
    database.execute(
        "INSERT INTO halls (hall_id, cinema_id, hall_name) VALUES (?, ?, ?)",
        (2, 1, "Hall Beta"),
    )
    database.execute(
        """
        INSERT INTO seats (seat_id, hall_id, row_number, seat_number)
        VALUES (?, ?, ?, ?)
        """,
        (1, 1, 1, 1),
    )
    database.execute(
        """
        INSERT INTO seats (seat_id, hall_id, row_number, seat_number)
        VALUES (?, ?, ?, ?)
        """,
        (2, 1, 1, 2),
    )
    database.execute(
        """
        INSERT INTO seats (seat_id, hall_id, row_number, seat_number)
        VALUES (?, ?, ?, ?)
        """,
        (3, 2, 1, 1),
    )
    database.execute(
        """
        INSERT INTO movies (
            movie_id,
            title,
            duration_minutes,
            description,
            genre,
            ticket_price
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (1, "Dune", 120, "Description", "drama", 40),
    )
    database.execute(
        """
        INSERT INTO movie_shows (
            show_id,
            movie_id,
            hall_id,
            start_time,
            ticket_price
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (1, 1, 1, "2026-09-01T15:00:00+00:00", 40),
    )
    database.execute(
        """
        INSERT INTO movie_shows (
            show_id,
            movie_id,
            hall_id,
            start_time,
            ticket_price
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (2, 1, 1, "2026-09-02T15:00:00+00:00", 40),
    )
    database.execute(
        """
        INSERT INTO movie_shows (
            show_id,
            movie_id,
            hall_id,
            start_time,
            ticket_price
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (3, 1, 2, "2026-09-01T15:00:00+00:00", 40),
    )
    database.execute(
        """
        INSERT INTO users (
            user_id,
            auth_subject,
            full_name,
            phone_number,
            email
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (1, "auth0|dana", "Dana Cohen", "+972501234567", "dana@example.com"),
    )
    database.execute(
        """
        INSERT INTO users (
            user_id,
            auth_subject,
            full_name,
            phone_number,
            email
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (2, "auth0|avi", "Avi Levi", "+972521234567", "avi@example.com"),
    )


def insert_booking(
    database: sqlite3.Connection,
    booking_id: int,
    user_id: int,
    show_id: int,
) -> None:
    database.execute(
        "INSERT INTO bookings (booking_id, user_id, show_id) VALUES (?, ?, ?)",
        (booking_id, user_id, show_id),
    )


def test_schema_contains_all_required_tables(database: sqlite3.Connection) -> None:
    names = {
        row[0]
        for row in database.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table'"
        )
    }

    assert {
        "cinemas",
        "halls",
        "seats",
        "movies",
        "movie_shows",
        "users",
        "bookings",
        "booking_seats",
    }.issubset(names)


def test_double_booking_same_show_and_seat_is_blocked_by_database(
    database: sqlite3.Connection,
) -> None:
    seed_catalog(database)
    insert_booking(database, 1, 1, 1)
    insert_booking(database, 2, 2, 1)

    database.execute(
        """
        INSERT INTO booking_seats (booking_id, show_id, seat_id)
        VALUES (?, ?, ?)
        """,
        (1, 1, 1),
    )

    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        database.execute(
            """
            INSERT INTO booking_seats (booking_id, show_id, seat_id)
            VALUES (?, ?, ?)
            """,
            (2, 1, 1),
        )


def test_same_seat_is_allowed_for_different_shows(
    database: sqlite3.Connection,
) -> None:
    seed_catalog(database)
    insert_booking(database, 1, 1, 1)
    insert_booking(database, 2, 2, 2)

    database.execute(
        """
        INSERT INTO booking_seats (booking_id, show_id, seat_id)
        VALUES (?, ?, ?)
        """,
        (1, 1, 1),
    )
    database.execute(
        """
        INSERT INTO booking_seats (booking_id, show_id, seat_id)
        VALUES (?, ?, ?)
        """,
        (2, 2, 1),
    )

    count = database.execute(
        "SELECT COUNT(*) FROM booking_seats WHERE seat_id = 1"
    ).fetchone()[0]
    assert count == 2


def test_booking_seat_show_must_match_booking_show(
    database: sqlite3.Connection,
) -> None:
    seed_catalog(database)
    insert_booking(database, 1, 1, 1)

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        database.execute(
            """
            INSERT INTO booking_seats (booking_id, show_id, seat_id)
            VALUES (?, ?, ?)
            """,
            (1, 2, 1),
        )


def test_seat_must_belong_to_show_hall(database: sqlite3.Connection) -> None:
    seed_catalog(database)
    insert_booking(database, 1, 1, 1)

    with pytest.raises(
        sqlite3.IntegrityError,
        match="booking seat does not belong to the show hall",
    ):
        database.execute(
            """
            INSERT INTO booking_seats (booking_id, show_id, seat_id)
            VALUES (?, ?, ?)
            """,
            (1, 1, 3),
        )


def test_booking_delete_cascades_only_junction_rows(
    database: sqlite3.Connection,
) -> None:
    seed_catalog(database)
    insert_booking(database, 1, 1, 1)
    database.execute(
        """
        INSERT INTO booking_seats (booking_id, show_id, seat_id)
        VALUES (?, ?, ?)
        """,
        (1, 1, 1),
    )

    database.execute("DELETE FROM bookings WHERE booking_id = 1")

    assert database.execute(
        "SELECT COUNT(*) FROM booking_seats"
    ).fetchone()[0] == 0
    assert database.execute(
        "SELECT COUNT(*) FROM users WHERE user_id = 1"
    ).fetchone()[0] == 1
    assert database.execute(
        "SELECT COUNT(*) FROM movie_shows WHERE show_id = 1"
    ).fetchone()[0] == 1


def test_foreign_keys_reject_orphan_rows(database: sqlite3.Connection) -> None:
    seed_catalog(database)

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        database.execute(
            "INSERT INTO bookings (booking_id, user_id, show_id) VALUES (?, ?, ?)",
            (1, 999, 1),
        )

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        database.execute(
            "INSERT INTO bookings (booking_id, user_id, show_id) VALUES (?, ?, ?)",
            (1, 1, 999),
        )


def test_unique_business_keys_are_enforced(database: sqlite3.Connection) -> None:
    seed_catalog(database)

    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        database.execute(
            "INSERT INTO halls (hall_id, cinema_id, hall_name) VALUES (?, ?, ?)",
            (9, 1, "Hall Alpha"),
        )

    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        database.execute(
            """
            INSERT INTO seats (seat_id, hall_id, row_number, seat_number)
            VALUES (?, ?, ?, ?)
            """,
            (99, 1, 1, 1),
        )

    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        database.execute(
            """
            INSERT INTO users (
                user_id,
                auth_subject,
                full_name,
                phone_number,
                email
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (9, "auth0|other", "Other", "+972591234567", "DANA@EXAMPLE.COM"),
        )

    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        database.execute(
            """
            INSERT INTO users (
                user_id,
                auth_subject,
                full_name,
                phone_number,
                email
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                10,
                "auth0|dana",
                "Duplicate Subject",
                "+972581234567",
                "unique@example.com",
            ),
        )


def test_check_constraints_are_enforced(database: sqlite3.Connection) -> None:
    seed_catalog(database)

    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        database.execute(
            """
            INSERT INTO movies (
                movie_id,
                title,
                duration_minutes,
                description,
                genre,
                ticket_price
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (9, "Invalid", 0, "Description", "drama", 40),
        )

    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        database.execute(
            """
            INSERT INTO movies (
                movie_id,
                title,
                duration_minutes,
                description,
                genre,
                ticket_price
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (10, "Invalid Genre", 90, "Description", "horror", 40),
        )



def test_same_hall_cannot_have_two_shows_with_same_start_time(
    database: sqlite3.Connection,
) -> None:
    seed_catalog(database)

    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        database.execute(
            """
            INSERT INTO movie_shows (
                show_id,
                movie_id,
                hall_id,
                start_time,
                ticket_price
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (99, 1, 1, "2026-09-01T15:00:00+00:00", 40),
        )

def test_expected_indexes_exist(database: sqlite3.Connection) -> None:
    indexes = {
        row[0]
        for row in database.execute(
            """
            SELECT name
            FROM sqlite_schema
            WHERE type = 'index' AND name NOT LIKE 'sqlite_autoindex%'
            """
        )
    }

    assert {
        "idx_halls_cinema_id",
        "idx_seats_hall_id",
        "idx_movie_shows_movie_id",
        "idx_bookings_user_id",
        "idx_bookings_show_id",
        "idx_booking_seats_booking_id",
        "idx_booking_seats_seat_id",
    }.issubset(indexes)
