"""Idempotent initial data for the PostgreSQL-compatible cinema schema."""

from sqlalchemy import Engine, insert, select

from cinema.storage.sqlalchemy_schema import cinemas, halls, seats


def seed_cinema(engine: Engine) -> None:
    """Create the baseline cinema, halls, and seats when they do not exist."""
    with engine.begin() as connection:
        if connection.execute(select(cinemas.c.cinema_id)).first() is not None:
            return
        connection.execute(insert(cinemas), {"cinema_id": 1, "name": "Cinema City"})
        connection.execute(
            insert(halls),
            [
                {"hall_id": hall_id, "cinema_id": 1, "hall_name": f"Hall {hall_id}"}
                for hall_id in range(1, 4)
            ],
        )
        connection.execute(
            insert(seats),
            [
                {
                    "seat_id": ((hall_id - 1) * 400) + ((row - 1) * 20) + number,
                    "hall_id": hall_id,
                    "row_number": row,
                    "seat_number": number,
                }
                for hall_id in range(1, 4)
                for row in range(1, 21)
                for number in range(1, 21)
            ],
        )
