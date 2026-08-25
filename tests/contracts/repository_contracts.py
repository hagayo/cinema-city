"""Reusable repository behavior contracts.

A future persistence backend does not copy these tests. It only supplies repository
fixtures by subclassing the relevant contract class.
"""

from datetime import datetime

import pytest

from cinema.exceptions import CinemaError
from cinema.models import (
    BookingRequest,
    Genre,
    MovieShowDraft,
    NewMovie,
    NewUser,
    UserProfileUpdate,
)
from cinema.storage import (
    BookingRepository,
    CinemaConfigRepository,
    MovieRepository,
    ShowRepository,
    UserRepository,
)
from cinema.time_utils import CINEMA_TIMEZONE


class CinemaConfigRepositoryContract:
    """Shared behavior required from every cinema-config repository."""

    @pytest.fixture
    def config_repository(self) -> CinemaConfigRepository:
        raise NotImplementedError

    def test_load_returns_clean_rows(
        self,
        config_repository: CinemaConfigRepository,
    ) -> None:
        cinema, halls, seats = config_repository.load()

        assert cinema.cinema_id > 0
        assert halls
        assert seats
        assert all(hall.hall_id > 0 for hall in halls)
        assert all(seat.hall_id > 0 for seat in seats)
        assert all(
            not hasattr(hall, "seats")
            for hall in halls
        )


class MovieRepositoryContract:
    """Shared behavior required from every movie repository."""

    @pytest.fixture
    def movie_repository(self) -> MovieRepository:
        raise NotImplementedError

    def test_create_allocates_id_and_load_round_trips(
        self,
        movie_repository: MovieRepository,
    ) -> None:
        movie = movie_repository.create(
            NewMovie(
                title="Dune",
                duration_minutes=120,
                description="Description",
                genre=Genre.DRAMA,
                ticket_price=40,
            )
        )

        assert movie.movie_id > 0
        assert movie_repository.load() == [movie]

    def test_create_allocates_distinct_ids(
        self,
        movie_repository: MovieRepository,
    ) -> None:
        first = movie_repository.create(
            NewMovie("Dune", 120, "Description", Genre.DRAMA, 40)
        )
        second = movie_repository.create(
            NewMovie("Alien", 110, "Description", Genre.THRILLER, 45)
        )

        assert first.movie_id != second.movie_id

    def test_duplicate_title_is_rejected(
        self,
        movie_repository: MovieRepository,
    ) -> None:
        movie_repository.create(
            NewMovie("Dune", 120, "Description", Genre.DRAMA, 40)
        )

        with pytest.raises(CinemaError):
            movie_repository.create(
                NewMovie(" dune ", 90, "Other", Genre.DRAMA, 40)
            )


class UserRepositoryContract:
    """Shared behavior required from every user repository."""

    @pytest.fixture
    def user_repository(self) -> UserRepository:
        raise NotImplementedError

    def test_auth_subject_is_the_identity_key(
        self,
        user_repository: UserRepository,
    ) -> None:
        user = user_repository.create(
            NewUser(
                auth_subject="auth0|dana",
                full_name="Dana Cohen",
                phone_number="0501234567",
                email="DANA@example.com",
            )
        )

        assert user.auth_subject == "auth0|dana"
        assert user_repository.find_by_auth_subject("auth0|dana") == user
        assert user_repository.find_by_auth_subject("auth0|missing") is None

    def test_profile_update_preserves_auth_subject(
        self,
        user_repository: UserRepository,
    ) -> None:
        user = user_repository.create(
            NewUser(
                auth_subject="auth0|dana",
                full_name="Dana Cohen",
                phone_number="0501234567",
                email="dana@example.com",
            )
        )

        updated = user_repository.update(
            user.user_id,
            UserProfileUpdate(
                full_name="Dana Updated",
                phone_number="0521234567",
                email="updated@example.com",
            ),
        )

        assert updated.user_id == user.user_id
        assert updated.auth_subject == user.auth_subject
        assert updated.full_name == "Dana Updated"

    def test_duplicate_auth_subject_is_rejected(
        self,
        user_repository: UserRepository,
    ) -> None:
        user_repository.create(
            NewUser(
                "auth0|dana",
                "Dana Cohen",
                "0501234567",
                "dana@example.com",
            )
        )

        with pytest.raises(CinemaError):
            user_repository.create(
                NewUser(
                    "auth0|dana",
                    "Another User",
                    "0521234567",
                    "other@example.com",
                )
            )


class ShowRepositoryContract:
    """Shared behavior required from every show repository."""

    @pytest.fixture
    def show_repository(self) -> ShowRepository:
        raise NotImplementedError

    def test_create_many_allocates_ids_and_round_trips(
        self,
        show_repository: ShowRepository,
    ) -> None:
        drafts = [
            MovieShowDraft(
                movie_id=1,
                hall_id=1,
                start_time=datetime(
                    2026,
                    9,
                    1,
                    18,
                    tzinfo=CINEMA_TIMEZONE,
                ),
                ticket_price=40,
            ),
            MovieShowDraft(
                movie_id=1,
                hall_id=1,
                start_time=datetime(
                    2026,
                    9,
                    1,
                    21,
                    tzinfo=CINEMA_TIMEZONE,
                ),
                ticket_price=40,
            ),
        ]

        shows = show_repository.create_many(drafts)

        assert len(shows) == 2
        assert len({show.show_id for show in shows}) == 2
        assert show_repository.load({1}, {1}) == shows


class BookingRepositoryContract:
    """Shared behavior required from every booking repository."""

    @pytest.fixture
    def booking_repository(self) -> BookingRepository:
        raise NotImplementedError

    def test_booking_and_seat_rows_round_trip(
        self,
        booking_repository: BookingRepository,
    ) -> None:
        booking, rows = booking_repository.add(
            BookingRequest(user_id=1, show_id=7, seat_ids=(1, 2))
        )

        bookings, loaded_rows = booking_repository.load(
            valid_show_ids={7},
            valid_user_ids={1},
            valid_seat_ids={1, 2, 3},
        )

        assert bookings == [booking]
        assert loaded_rows == rows
        assert {row.show_id for row in rows} == {7}

    def test_same_seat_same_show_is_rejected(
        self,
        booking_repository: BookingRepository,
    ) -> None:
        booking_repository.add(
            BookingRequest(user_id=1, show_id=7, seat_ids=(1,))
        )

        with pytest.raises(CinemaError):
            booking_repository.add(
                BookingRequest(user_id=2, show_id=7, seat_ids=(1,))
            )

    def test_same_seat_different_show_is_allowed(
        self,
        booking_repository: BookingRepository,
    ) -> None:
        booking_repository.add(
            BookingRequest(user_id=1, show_id=7, seat_ids=(1,))
        )
        second, _ = booking_repository.add(
            BookingRequest(user_id=2, show_id=8, seat_ids=(1,))
        )

        assert second.show_id == 8

    def test_delete_removes_booking_and_junction_rows(
        self,
        booking_repository: BookingRepository,
    ) -> None:
        booking, _ = booking_repository.add(
            BookingRequest(user_id=1, show_id=7, seat_ids=(1, 2))
        )

        booking_repository.delete(booking.booking_id, user_id=1)

        assert booking_repository.load(
            valid_show_ids={7},
            valid_user_ids={1},
            valid_seat_ids={1, 2, 3},
        ) == ([], [])
