"""Create the initial cinema schema.

Revision ID: 20260828_0001
Revises: None
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260828_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all relational tables and integrity constraints."""
    op.create_table(
        "cinemas",
        sa.Column("cinema_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("cinema_id", name="pk_cinemas"),
    )
    op.create_table(
        "movies",
        sa.Column("movie_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.Column("genre", sa.String(length=30), nullable=False),
        sa.Column("ticket_price", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "duration_minutes BETWEEN 1 AND 240",
            name="duration_minutes_range",
        ),
        sa.CheckConstraint(
            "ticket_price BETWEEN 1 AND 99",
            name="ticket_price_range",
        ),
        sa.PrimaryKeyConstraint("movie_id", name="pk_movies"),
        sa.UniqueConstraint("title", name="uq_movies_title"),
    )
    op.create_table(
        "users",
        sa.Column("user_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("auth_provider", sa.String(length=50), nullable=False),
        sa.Column("auth_subject", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("phone_number", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.PrimaryKeyConstraint("user_id", name="pk_users"),
        sa.UniqueConstraint(
            "auth_provider",
            "auth_subject",
            name="uq_users_auth_provider_auth_subject",
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("phone_number", name="uq_users_phone_number"),
    )
    op.create_table(
        "halls",
        sa.Column("hall_id", sa.Integer(), nullable=False),
        sa.Column("cinema_id", sa.Integer(), nullable=False),
        sa.Column("hall_name", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(
            ["cinema_id"],
            ["cinemas.cinema_id"],
            name="fk_halls_cinema_id_cinemas",
        ),
        sa.PrimaryKeyConstraint("hall_id", name="pk_halls"),
    )
    op.create_table(
        "seats",
        sa.Column("seat_id", sa.Integer(), nullable=False),
        sa.Column("hall_id", sa.Integer(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("seat_number", sa.Integer(), nullable=False),
        sa.CheckConstraint("row_number > 0", name="row_number_positive"),
        sa.CheckConstraint("seat_number > 0", name="seat_number_positive"),
        sa.ForeignKeyConstraint(
            ["hall_id"],
            ["halls.hall_id"],
            name="fk_seats_hall_id_halls",
        ),
        sa.PrimaryKeyConstraint("seat_id", name="pk_seats"),
        sa.UniqueConstraint(
            "hall_id",
            "row_number",
            "seat_number",
            name="uq_seats_hall_id_row_number_seat_number",
        ),
    )
    op.create_table(
        "shows",
        sa.Column("show_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("hall_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.String(length=64), nullable=False),
        sa.Column("ticket_price", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "ticket_price BETWEEN 1 AND 99",
            name="ticket_price_range",
        ),
        sa.ForeignKeyConstraint(
            ["hall_id"],
            ["halls.hall_id"],
            name="fk_shows_hall_id_halls",
        ),
        sa.ForeignKeyConstraint(
            ["movie_id"],
            ["movies.movie_id"],
            name="fk_shows_movie_id_movies",
        ),
        sa.PrimaryKeyConstraint("show_id", name="pk_shows"),
    )
    op.create_table(
        "bookings",
        sa.Column("booking_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("show_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["show_id"],
            ["shows.show_id"],
            name="fk_bookings_show_id_shows",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name="fk_bookings_user_id_users",
        ),
        sa.PrimaryKeyConstraint("booking_id", name="pk_bookings"),
    )
    op.create_table(
        "booking_seats",
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("show_id", sa.Integer(), nullable=False),
        sa.Column("seat_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.booking_id"],
            name="fk_booking_seats_booking_id_bookings",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["seat_id"],
            ["seats.seat_id"],
            name="fk_booking_seats_seat_id_seats",
        ),
        sa.ForeignKeyConstraint(
            ["show_id"],
            ["shows.show_id"],
            name="fk_booking_seats_show_id_shows",
        ),
        sa.UniqueConstraint(
            "booking_id",
            "seat_id",
            name="uq_booking_seats_booking_id_seat_id",
        ),
        sa.UniqueConstraint(
            "show_id",
            "seat_id",
            name="uq_booking_seats_show_id_seat_id",
        ),
    )


def downgrade() -> None:
    """Remove the initial cinema schema in reverse dependency order."""
    op.drop_table("booking_seats")
    op.drop_table("bookings")
    op.drop_table("shows")
    op.drop_table("seats")
    op.drop_table("halls")
    op.drop_table("users")
    op.drop_table("movies")
    op.drop_table("cinemas")
