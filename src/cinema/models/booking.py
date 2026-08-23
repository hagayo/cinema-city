"""Booking domain model."""

from dataclasses import dataclass

from cinema.models.movie_show import MovieShow
from cinema.models.seat import Seat


@dataclass(frozen=True, slots=True)
class Booking:
    """Represent one booking for one or more seats in a movie show."""

    booking_id: int
    show: MovieShow
    seats: tuple[Seat, ...]

    def __post_init__(self) -> None:
        """Validate booking identity and requested seats.

        Raises:
            ValueError: If the booking ID or seat collection is invalid.
        """
        if self.booking_id <= 0:
            raise ValueError("Booking ID must be positive")

        if not self.seats:
            raise ValueError("Booking must contain at least one seat")

        if len(self.seats) != len(set(self.seats)):
            raise ValueError("Booking cannot contain duplicate seats")

    @property
    def total_price(self) -> int:
        """Return the booking price in whole Israeli shekels."""
        return self.show.ticket_price * len(self.seats)
