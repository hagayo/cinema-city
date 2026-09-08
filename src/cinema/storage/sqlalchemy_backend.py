"""Relational repository adapters used by PostgreSQL-compatible Neon."""

from typing import Any

from sqlalchemy import Engine, create_engine, delete, insert, select, update
from sqlalchemy.engine import Connection, CursorResult, RowMapping
from sqlalchemy.exc import IntegrityError

from cinema.exceptions import (
    BookingNotFoundError,
    BookingValidationError,
    SeatAlreadyBookedError,
    StorageError,
    UserIdentityConflictError,
)
from cinema.models import (
    Booking,
    BookingRequest,
    BookingSeat,
    Cinema,
    Genre,
    Hall,
    Movie,
    MovieShow,
    Seat,
    User,
)
from cinema.services.user_identity import (
    normalize_email,
    normalize_full_name,
    normalize_phone_number,
)
from cinema.storage.interfaces import (
    BookingRepository,
    CinemaConfigRepository,
    MovieRepository,
    ShowRepository,
    UserRepository,
)
from cinema.storage.sqlalchemy_schema import (
    booking_seats,
    bookings,
    cinemas,
    halls,
    movies,
    seats,
    shows,
    users,
)
from cinema.storage.storage_service import StorageService
from cinema.time_utils import from_storage_iso, to_utc_iso


def normalize_database_url(database_url: str) -> str:
    """Select Psycopg 3 when a generic PostgreSQL URL is supplied."""
    return database_url.replace("postgresql://", "postgresql+psycopg://", 1)


def create_database_engine(database_url: str) -> Engine:
    """Create the SQLAlchemy engine shared by repositories and maintenance commands."""
    return create_engine(normalize_database_url(database_url), pool_pre_ping=True)


def create_neon_storage_service(database_url: str) -> StorageService:
    """Create relational repositories without performing DDL or seed operations."""
    engine = create_database_engine(database_url)
    return StorageService(
        config_repository=SqlCinemaConfigRepository(engine),
        movie_repository=SqlMovieRepository(engine),
        show_repository=SqlShowRepository(engine),
        booking_repository=SqlBookingRepository(engine),
        user_repository=SqlUserRepository(engine),
    )


class SqlCinemaConfigRepository(CinemaConfigRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def load(self) -> tuple[Cinema, list[Hall], list[Seat]]:
        with self._engine.connect() as connection:
            cinema_row = connection.execute(select(cinemas)).mappings().one()
            hall_rows = connection.execute(select(halls).order_by(halls.c.hall_id)).mappings()
            seat_rows = connection.execute(select(seats).order_by(seats.c.seat_id)).mappings()
            return (
                Cinema(int(cinema_row["cinema_id"]), str(cinema_row["name"])),
                [Hall(int(row["hall_id"]), str(row["hall_name"])) for row in hall_rows],
                [
                    Seat(
                        int(row["seat_id"]),
                        int(row["hall_id"]),
                        int(row["row_number"]),
                        int(row["seat_number"]),
                    )
                    for row in seat_rows
                ],
            )


class SqlMovieRepository(MovieRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def load(self) -> list[Movie]:
        with self._engine.connect() as connection:
            rows = connection.execute(select(movies).order_by(movies.c.movie_id)).mappings()
            return [_movie(row) for row in rows]

    def find_by_id(self, movie_id: int) -> Movie | None:
        with self._engine.connect() as connection:
            row = (
                connection.execute(select(movies).where(movies.c.movie_id == movie_id))
                .mappings()
                .first()
            )
            return _movie(row) if row is not None else None

    def create(self, movie: Movie) -> int:
        if movie.movie_id is not None:
            raise StorageError("A new movie must not already have an ID")
        try:
            with self._engine.begin() as connection:
                result = connection.execute(
                    insert(movies).values(
                        title=movie.title,
                        duration_minutes=movie.duration_minutes,
                        description=movie.description,
                        genre=movie.genre.value,
                        ticket_price=movie.ticket_price,
                    )
                )
                return _inserted_id(result)
        except IntegrityError as error:
            raise StorageError(f'Movie title "{movie.title}" already exists') from error


class SqlShowRepository(ShowRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def load(self, valid_hall_ids: set[int], valid_movie_ids: set[int]) -> list[MovieShow]:
        with self._engine.connect() as connection:
            rows = connection.execute(select(shows).order_by(shows.c.show_id)).mappings()
            loaded = [_show(row) for row in rows]
        if any(show.hall_id not in valid_hall_ids for show in loaded):
            raise StorageError("Show references an unknown hall")
        if any(show.movie_id not in valid_movie_ids for show in loaded):
            raise StorageError("Show references an unknown movie")
        return loaded

    def find_by_id(self, show_id: int) -> MovieShow | None:
        with self._engine.connect() as connection:
            row = (
                connection.execute(select(shows).where(shows.c.show_id == show_id))
                .mappings()
                .first()
            )
            return _show(row) if row is not None else None

    def create_many(self, new_shows: list[MovieShow]) -> list[int]:
        if any(show.show_id is not None for show in new_shows):
            raise StorageError("New shows must not already have IDs")
        identifiers: list[int] = []
        with self._engine.begin() as connection:
            for show in new_shows:
                result = connection.execute(
                    insert(shows).values(
                        movie_id=show.movie_id,
                        hall_id=show.hall_id,
                        start_time=to_utc_iso(show.start_time),
                        ticket_price=show.ticket_price,
                    )
                )
                identifiers.append(_inserted_id(result))
        return identifiers


class SqlUserRepository(UserRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def load(self) -> list[User]:
        with self._engine.connect() as connection:
            rows = connection.execute(select(users).order_by(users.c.user_id)).mappings()
            return [_user(row) for row in rows]

    def find_by_id(self, user_id: int) -> User | None:
        return self._find(users.c.user_id == user_id)

    def find_by_auth_identity(self, auth_provider: str, auth_subject: str) -> User | None:
        return self._find(
            (users.c.auth_provider == auth_provider.casefold())
            & (users.c.auth_subject == auth_subject)
        )

    def find_by_email(self, email: str) -> User | None:
        return self._find(users.c.email == normalize_email(email)) if email.strip() else None

    def find_by_phone(self, phone_number: str) -> User | None:
        return (
            self._find(users.c.phone_number == normalize_phone_number(phone_number))
            if phone_number.strip()
            else None
        )

    def create(self, user: User) -> int:
        if user.user_id is not None:
            raise StorageError("A new user must not already have an ID")
        values = _user_values(user)
        try:
            with self._engine.begin() as connection:
                _ensure_unique_profile(connection, values)
                result = connection.execute(insert(users).values(**values))
                return _inserted_id(result)
        except IntegrityError as error:
            raise UserIdentityConflictError("User identity already exists") from error

    def update(self, user: User) -> None:
        if user.user_id is None:
            raise StorageError("Cannot update a user without an ID")
        values = _user_values(user)
        try:
            with self._engine.begin() as connection:
                _ensure_unique_profile(connection, values, excluding=user.user_id)
                result = connection.execute(
                    update(users).where(users.c.user_id == user.user_id).values(**values)
                )
                if result.rowcount != 1:
                    raise StorageError(f"User {user.user_id} does not exist")
        except IntegrityError as error:
            raise UserIdentityConflictError("User identity already exists") from error

    def _find(self, condition: Any) -> User | None:
        with self._engine.connect() as connection:
            row = connection.execute(select(users).where(condition)).mappings().first()
            return _user(row) if row is not None else None


class SqlBookingRepository(BookingRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def load(
        self,
        valid_show_ids: set[int],
        valid_user_ids: set[int],
        valid_seat_ids: set[int],
    ) -> tuple[list[Booking], list[BookingSeat]]:
        with self._engine.connect() as connection:
            booking_rows = connection.execute(
                select(bookings).order_by(bookings.c.booking_id)
            ).mappings()
            seat_rows = connection.execute(select(booking_seats)).mappings()
            loaded_bookings = [_booking(row) for row in booking_rows]
            loaded_seats = [_booking_seat(row) for row in seat_rows]
        if any(item.show_id not in valid_show_ids for item in loaded_bookings):
            raise StorageError("Booking references an unknown show")
        if any(item.user_id not in valid_user_ids for item in loaded_bookings):
            raise StorageError("Booking references an unknown user")
        if any(item.seat_id not in valid_seat_ids for item in loaded_seats):
            raise StorageError("Booking references an unknown seat")
        return loaded_bookings, loaded_seats

    def find_by_id(self, booking_id: int) -> Booking | None:
        with self._engine.connect() as connection:
            row = (
                connection.execute(select(bookings).where(bookings.c.booking_id == booking_id))
                .mappings()
                .first()
            )
            return _booking(row) if row is not None else None

    def find_by_user_id(self, user_id: int) -> list[Booking]:
        with self._engine.connect() as connection:
            rows = connection.execute(
                select(bookings)
                .where(bookings.c.user_id == user_id)
                .order_by(bookings.c.booking_id)
            ).mappings()
            return [_booking(row) for row in rows]

    def add(self, request: BookingRequest) -> int:
        try:
            with self._engine.begin() as connection:
                result = connection.execute(
                    insert(bookings).values(user_id=request.user_id, show_id=request.show_id)
                )
                booking_id = _inserted_id(result)
                connection.execute(
                    insert(booking_seats),
                    [
                        {
                            "booking_id": booking_id,
                            "show_id": request.show_id,
                            "seat_id": seat_id,
                        }
                        for seat_id in request.seat_ids
                    ],
                )
                return booking_id
        except IntegrityError as error:
            raise SeatAlreadyBookedError("One or more selected seats are unavailable") from error

    def delete(self, booking_id: int, user_id: int) -> int:
        with self._engine.begin() as connection:
            booking = (
                connection.execute(select(bookings).where(bookings.c.booking_id == booking_id))
                .mappings()
                .first()
            )
            if booking is None:
                raise BookingNotFoundError(f"Booking {booking_id} does not exist")
            if int(booking["user_id"]) != user_id:
                raise BookingValidationError("Booking does not belong to this user")
            selected_rows = connection.execute(
                select(booking_seats.c.seat_id).where(booking_seats.c.booking_id == booking_id)
            ).all()
            count = len(selected_rows)
            connection.execute(
                delete(booking_seats).where(booking_seats.c.booking_id == booking_id)
            )
            connection.execute(delete(bookings).where(bookings.c.booking_id == booking_id))
            return count


def _movie(row: RowMapping) -> Movie:
    return Movie(
        movie_id=int(row["movie_id"]),
        title=str(row["title"]),
        duration_minutes=int(row["duration_minutes"]),
        description=str(row["description"]),
        genre=Genre(str(row["genre"])),
        ticket_price=int(row["ticket_price"]),
    )


def _show(row: RowMapping) -> MovieShow:
    return MovieShow(
        show_id=int(row["show_id"]),
        movie_id=int(row["movie_id"]),
        hall_id=int(row["hall_id"]),
        start_time=from_storage_iso(str(row["start_time"])),
        ticket_price=int(row["ticket_price"]),
    )


def _user(row: RowMapping) -> User:
    return User(
        user_id=int(row["user_id"]),
        auth_provider=str(row["auth_provider"]),
        auth_subject=str(row["auth_subject"]),
        full_name=str(row["full_name"]),
        phone_number=str(row["phone_number"] or ""),
        email=str(row["email"] or ""),
    )


def _user_values(user: User) -> dict[str, Any]:
    return {
        "auth_provider": user.auth_provider.casefold(),
        "auth_subject": user.auth_subject,
        "full_name": normalize_full_name(user.full_name),
        "phone_number": normalize_phone_number(user.phone_number) if user.phone_number else None,
        "email": normalize_email(user.email) if user.email else None,
    }


def _ensure_unique_profile(
    connection: Connection,
    values: dict[str, Any],
    excluding: int | None = None,
) -> None:
    conditions = []
    if values["email"]:
        conditions.append(users.c.email == values["email"])
    if values["phone_number"]:
        conditions.append(users.c.phone_number == values["phone_number"])
    for condition in conditions:
        statement = select(users.c.user_id).where(condition)
        if excluding is not None:
            statement = statement.where(users.c.user_id != excluding)
        if connection.execute(statement).first() is not None:
            raise UserIdentityConflictError("Email or phone already belongs to another user")


def _booking(row: RowMapping) -> Booking:
    return Booking(
        booking_id=int(row["booking_id"]),
        user_id=int(row["user_id"]),
        show_id=int(row["show_id"]),
    )


def _booking_seat(row: RowMapping) -> BookingSeat:
    return BookingSeat(
        booking_id=int(row["booking_id"]),
        show_id=int(row["show_id"]),
        seat_id=int(row["seat_id"]),
    )


def _inserted_id(result: CursorResult[Any]) -> int:
    primary_key = result.inserted_primary_key
    if primary_key is None:
        raise StorageError("Database did not return a primary key")
    identifier = primary_key[0]
    if identifier is None:
        raise StorageError("Database did not return the created entity ID")
    return int(identifier)
