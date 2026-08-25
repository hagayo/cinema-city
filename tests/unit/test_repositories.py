"""Tests for repository protocols and current JSON implementations."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from cinema.exceptions import (
    BookingNotFoundError,
    BookingValidationError,
    SeatAlreadyBookedError,
    StorageError,
)
from cinema.models import BookingRequest, Genre, MovieShowDraft, NewMovie
from cinema.storage import (
    BookingRepository,
    CinemaConfigRepository,
    JsonBookingRepository,
    JsonCinemaConfigRepository,
    JsonMovieRepository,
    JsonShowRepository,
    JsonUserRepository,
    MovieRepository,
    ShowRepository,
    UserRepository,
)
from cinema.storage.schema import SCHEMA_VERSION
from cinema.time_utils import CINEMA_TIMEZONE
from tests.conftest import CinemaEnvironment


def test_repository_protocols_are_separate_from_json_implementations() -> None:
    assert JsonMovieRepository is not MovieRepository
    assert JsonShowRepository is not ShowRepository
    assert JsonUserRepository is not UserRepository
    assert JsonBookingRepository is not BookingRepository
    assert JsonCinemaConfigRepository is not CinemaConfigRepository


def test_json_config_loads_clean_entities(environment: CinemaEnvironment) -> None:
    cinema, halls, seats = JsonCinemaConfigRepository(environment.config_file).load()

    assert cinema.cinema_id == 1
    assert cinema.name == "Cinema City"
    assert [hall.hall_name for hall in halls] == ["Hall Alpha", "Hall Beta", "Hall Gamma"]
    assert [hall.hall_id for hall in halls] == [1, 2, 3]
    assert len(seats) == 36
    assert seats[0].seat_id == 1
    assert seats[0].hall_id == 1
    assert seats[-1].hall_id == 3


@pytest.mark.parametrize(
    ("halls", "message"),
    [
        (
            [
                {"hall_id": 1, "hall_name": "A", "rows": 1, "seats_per_row": 1},
                {"hall_id": 1, "hall_name": "B", "rows": 1, "seats_per_row": 1},
            ],
            "duplicate hall IDs",
        ),
        (
            [
                {"hall_id": 1, "hall_name": "Same", "rows": 1, "seats_per_row": 1},
                {"hall_id": 2, "hall_name": " same ", "rows": 1, "seats_per_row": 1},
            ],
            "duplicate hall names",
        ),
    ],
)
def test_json_config_rejects_duplicate_halls(
    tmp_path: Path,
    halls: list[dict[str, object]],
    message: str,
) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 5,
                "cinema": {"cinema_id": 1, "name": "Cinema"},
                "halls": halls,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(StorageError, match=message):
        JsonCinemaConfigRepository(path).load()


def test_json_config_rejects_invalid_dimensions(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 5,
                "cinema": {"cinema_id": 1, "name": "Cinema"},
                "halls": [
                    {"hall_id": 1, "hall_name": "A", "rows": 0, "seats_per_row": 1}
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(StorageError, match="dimensions"):
        JsonCinemaConfigRepository(path).load()


def test_movie_repository_allocates_ids_and_enforces_title_uniqueness(
    environment: CinemaEnvironment,
) -> None:
    repo = JsonMovieRepository(environment.movies_file, environment.state_lock_file)

    first = repo.create(NewMovie("Dune", 120, "Description", Genre.DRAMA, 40))
    second = repo.create(NewMovie("Alien", 110, "Description", Genre.THRILLER, 45))

    assert (first.movie_id, second.movie_id) == (1, 2)
    assert repo.load() == [first, second]

    with pytest.raises(StorageError, match="already exists"):
        repo.create(NewMovie("  dune ", 100, "Other", Genre.DRAMA, 40))


def test_movie_repository_rejects_duplicate_persisted_rows(tmp_path: Path) -> None:
    path = tmp_path / "movies.json"
    movie = {
        "movie_id": 1,
        "title": "Dune",
        "duration_minutes": 120,
        "description": "Description",
        "genre": "drama",
        "ticket_price": 40,
    }
    path.write_text(
        json.dumps(
            {
                "schema_version": 5,
                "last_movie_id": 1,
                "movies": [movie, movie],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(StorageError, match="duplicate movie IDs"):
        JsonMovieRepository(path).load()


def test_movie_repository_rejects_invalid_last_movie_id(tmp_path: Path) -> None:
    path = tmp_path / "movies.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 5,
                "last_movie_id": 0,
                "movies": [{
                    "movie_id": 2,
                    "title": "Dune",
                    "duration_minutes": 120,
                    "description": "Description",
                    "genre": "drama",
                    "ticket_price": 40,
                }],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(StorageError, match="last_movie_id"):
        JsonMovieRepository(path).load()


def test_show_repository_allocates_ids_and_persists_foreign_keys(
    environment: CinemaEnvironment,
) -> None:
    repo = JsonShowRepository(environment.shows_file, environment.state_lock_file)
    draft = MovieShowDraft(
        movie_id=1,
        hall_id=2,
        start_time=datetime(2026, 9, 1, 18, tzinfo=CINEMA_TIMEZONE),
        ticket_price=40,
    )

    [show] = repo.create_many([draft])
    assert show.show_id == 1
    assert show.movie_id == 1
    assert show.hall_id == 2
    assert repo.load({1, 2, 3}, {1}) == [show]

    document = json.loads(environment.shows_file.read_text(encoding="utf-8"))
    assert document["shows"][0]["movie_id"] == 1
    assert document["shows"][0]["hall_id"] == 2
    assert "movie" not in document["shows"][0]
    assert "hall_number" not in document["shows"][0]


def test_show_repository_rejects_unknown_foreign_keys(
    environment: CinemaEnvironment,
) -> None:
    repo = JsonShowRepository(environment.shows_file, environment.state_lock_file)
    repo.create_many([
        MovieShowDraft(
            movie_id=9,
            hall_id=8,
            start_time=datetime(2026, 9, 1, 18, tzinfo=CINEMA_TIMEZONE),
            ticket_price=40,
        )
    ])
    with pytest.raises(StorageError, match="unknown hall"):
        repo.load({1}, {1})


def test_show_repository_rejects_bad_last_show_id(tmp_path: Path) -> None:
    path = tmp_path / "shows.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 5,
                "last_show_id": 0,
                "shows": [{
                    "show_id": 2,
                    "movie_id": 1,
                    "hall_id": 1,
                    "start_time": "2026-09-01T15:00:00+00:00",
                    "ticket_price": 40,
                }],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(StorageError, match="last_show_id"):
        JsonShowRepository(path).load({1}, {1})


def test_booking_repository_persists_booking_and_junction_rows(
    environment: CinemaEnvironment,
) -> None:
    repo = JsonBookingRepository(environment.bookings_file)
    booking, rows = repo.add(BookingRequest(user_id=1, show_id=7, seat_ids=(2, 3)))

    assert booking.booking_id == 1
    assert booking.user_id == 1
    assert booking.show_id == 7
    assert [row.seat_id for row in rows] == [2, 3]

    bookings, booking_seats = repo.load({7}, {1}, {1, 2, 3})
    assert bookings == [booking]
    assert booking_seats == rows

    document = json.loads(environment.bookings_file.read_text(encoding="utf-8"))
    assert document["bookings"] == [{"booking_id": 1, "user_id": 1, "show_id": 7}]
    assert document["booking_seats"] == [
        {"booking_id": 1, "show_id": 7, "seat_id": 2},
        {"booking_id": 1, "show_id": 7, "seat_id": 3},
    ]


def test_booking_repository_prevents_double_booking(
    environment: CinemaEnvironment,
) -> None:
    repo = JsonBookingRepository(environment.bookings_file)
    repo.add(BookingRequest(user_id=1, show_id=7, seat_ids=(2,)))

    with pytest.raises(SeatAlreadyBookedError):
        repo.add(BookingRequest(user_id=2, show_id=7, seat_ids=(2,)))


def test_same_seat_can_be_used_for_different_show(
    environment: CinemaEnvironment,
) -> None:
    repo = JsonBookingRepository(environment.bookings_file)
    repo.add(BookingRequest(user_id=1, show_id=7, seat_ids=(2,)))
    second, _ = repo.add(BookingRequest(user_id=2, show_id=8, seat_ids=(2,)))
    assert second.booking_id == 2


def test_booking_repository_delete_removes_junction_rows(
    environment: CinemaEnvironment,
) -> None:
    repo = JsonBookingRepository(environment.bookings_file)
    booking, rows = repo.add(BookingRequest(user_id=1, show_id=7, seat_ids=(2, 3)))
    deleted, deleted_rows = repo.delete(booking.booking_id, 1)
    assert deleted == booking
    assert deleted_rows == rows
    assert repo.load({7}, {1}, {1, 2, 3}) == ([], [])


def test_booking_repository_delete_rejects_missing_or_wrong_user(
    environment: CinemaEnvironment,
) -> None:
    repo = JsonBookingRepository(environment.bookings_file)
    booking, _ = repo.add(BookingRequest(user_id=1, show_id=7, seat_ids=(2,)))

    with pytest.raises(BookingValidationError):
        repo.delete(booking.booking_id, 2)
    with pytest.raises(BookingNotFoundError):
        repo.delete(999, 1)


@pytest.mark.parametrize(
    ("document", "message"),
    [
        (
            {
                "schema_version": 5,
                "last_booking_id": 1,
                "bookings": [{"booking_id": 1, "user_id": 9, "show_id": 7}],
                "booking_seats": [],
            },
            "unknown user",
        ),
        (
            {
                "schema_version": 5,
                "last_booking_id": 1,
                "bookings": [{"booking_id": 1, "user_id": 1, "show_id": 99}],
                "booking_seats": [],
            },
            "unknown show",
        ),
        (
            {
                "schema_version": 5,
                "last_booking_id": 1,
                "bookings": [{"booking_id": 1, "user_id": 1, "show_id": 7}],
                "booking_seats": [{"booking_id": 1, "show_id": 7, "seat_id": 99}],
            },
            "unknown seat",
        ),
    ],
)
def test_booking_repository_validates_foreign_keys(
    tmp_path: Path,
    document: dict[str, object],
    message: str,
) -> None:
    path = tmp_path / "bookings.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(StorageError, match=message):
        JsonBookingRepository(path).load({7}, {1}, {1, 2, 3})


def test_schema_version_constant_is_three() -> None:
    assert SCHEMA_VERSION == 5
