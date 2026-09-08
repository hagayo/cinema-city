"""SQLAlchemy metadata describing the current relational target schema."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)

NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ix": "ix_%(column_0_label)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)

cinemas = Table(
    "cinemas",
    metadata,
    Column("cinema_id", Integer, primary_key=True),
    Column("name", String(200), nullable=False),
)
halls = Table(
    "halls",
    metadata,
    Column("hall_id", Integer, primary_key=True),
    Column("cinema_id", Integer, ForeignKey("cinemas.cinema_id"), nullable=False),
    Column("hall_name", String(100), nullable=False),
)
seats = Table(
    "seats",
    metadata,
    Column("seat_id", Integer, primary_key=True),
    Column("hall_id", Integer, ForeignKey("halls.hall_id"), nullable=False),
    Column("row_number", Integer, nullable=False),
    Column("seat_number", Integer, nullable=False),
    UniqueConstraint("hall_id", "row_number", "seat_number"),
    CheckConstraint("row_number > 0", name="row_number_positive"),
    CheckConstraint("seat_number > 0", name="seat_number_positive"),
)
movies = Table(
    "movies",
    metadata,
    Column("movie_id", Integer, primary_key=True, autoincrement=True),
    Column("title", String(200), nullable=False, unique=True),
    Column("duration_minutes", Integer, nullable=False),
    Column("description", String(300), nullable=False),
    Column("genre", String(30), nullable=False),
    Column("ticket_price", Integer, nullable=False),
    CheckConstraint(
        "duration_minutes BETWEEN 1 AND 240",
        name="duration_minutes_range",
    ),
    CheckConstraint("ticket_price BETWEEN 1 AND 99", name="ticket_price_range"),
)
shows = Table(
    "shows",
    metadata,
    Column("show_id", Integer, primary_key=True, autoincrement=True),
    Column("movie_id", Integer, ForeignKey("movies.movie_id"), nullable=False),
    Column("hall_id", Integer, ForeignKey("halls.hall_id"), nullable=False),
    Column("start_time", String(64), nullable=False),
    Column("ticket_price", Integer, nullable=False),
    CheckConstraint("ticket_price BETWEEN 1 AND 99", name="ticket_price_range"),
)
users = Table(
    "users",
    metadata,
    Column("user_id", Integer, primary_key=True, autoincrement=True),
    Column("auth_provider", String(50), nullable=False),
    Column("auth_subject", String(255), nullable=False),
    Column("full_name", String(200), nullable=False),
    Column("phone_number", String(30), nullable=True, unique=True),
    Column("email", String(320), nullable=True, unique=True),
    UniqueConstraint("auth_provider", "auth_subject"),
)
bookings = Table(
    "bookings",
    metadata,
    Column("booking_id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.user_id"), nullable=False),
    Column("show_id", Integer, ForeignKey("shows.show_id"), nullable=False),
)
booking_seats = Table(
    "booking_seats",
    metadata,
    Column(
        "booking_id",
        Integer,
        ForeignKey("bookings.booking_id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("show_id", Integer, ForeignKey("shows.show_id"), nullable=False),
    Column("seat_id", Integer, ForeignKey("seats.seat_id"), nullable=False),
    UniqueConstraint("booking_id", "seat_id"),
    UniqueConstraint("show_id", "seat_id"),
)
