"""Repository abstractions used by business and application layers."""

from typing import Protocol

from cinema.models import (
    Booking,
    BookingRequest,
    BookingSeat,
    Cinema,
    Hall,
    Movie,
    MovieShow,
    MovieShowDraft,
    NewMovie,
    NewUser,
    Seat,
    User,
    UserProfileUpdate,
)


class CinemaConfigRepository(Protocol):
    """Persistence contract for cinema, hall, and physical-seat configuration."""

    def load(self) -> tuple[Cinema, list[Hall], list[Seat]]: ...


class MovieRepository(Protocol):
    """Persistence contract for movies."""

    def load(self) -> list[Movie]: ...

    def create(self, new_movie: NewMovie) -> Movie: ...


class ShowRepository(Protocol):
    """Persistence contract for movie shows."""

    def load(
        self,
        valid_hall_ids: set[int],
        valid_movie_ids: set[int],
    ) -> list[MovieShow]: ...

    def create_many(self, drafts: list[MovieShowDraft]) -> list[MovieShow]: ...


class UserRepository(Protocol):
    """Persistence contract for user profiles linked to external auth subjects."""

    def load(self) -> list[User]: ...

    def find_by_auth_subject(self, auth_subject: str) -> User | None: ...

    def create(self, new_user: NewUser) -> User: ...

    def update(self, user_id: int, profile: UserProfileUpdate) -> User: ...


class BookingRepository(Protocol):
    """Persistence contract for bookings and booking-seat rows."""

    def load(
        self,
        valid_show_ids: set[int],
        valid_user_ids: set[int],
        valid_seat_ids: set[int],
    ) -> tuple[list[Booking], list[BookingSeat]]: ...

    def add(self, request: BookingRequest) -> tuple[Booking, list[BookingSeat]]: ...

    def delete(self, booking_id: int, user_id: int) -> tuple[Booking, list[BookingSeat]]: ...
