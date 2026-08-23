"""Business logic for creating and cancelling cinema bookings."""

from cinema.exceptions import (
    BookingNotFoundError,
    SeatAlreadyBookedError,
    SeatNotFoundError,
)
from cinema.models import Booking, Hall, MovieShow, Seat


MAX_SEATS_PER_BOOKING = 5


class BookingService:
    """Manage cinema bookings."""

    def __init__(
        self,
        bookings: list[Booking] | None = None,
    ) -> None:
        """Create a booking service with optional existing bookings."""
        self._bookings = list(bookings) if bookings is not None else []

    @property
    def bookings(self) -> tuple[Booking, ...]:
        """Return an immutable view of current bookings."""
        return tuple(self._bookings)

    @staticmethod
    def find_seat(
        hall: Hall,
        row: int,
        seat_number: int,
    ) -> Seat:
        """Return a physical seat from a hall.

        Raises:
            SeatNotFoundError: If the requested seat does not exist.
        """
        for seat in hall.seats:
            if seat.row == row and seat.seat_number == seat_number:
                return seat

        raise SeatNotFoundError(
            f"Seat {row}-{seat_number} does not exist in hall {hall.hall_number}"
        )

    def is_seat_booked(self, show: MovieShow, seat: Seat) -> bool:
        """Return whether a seat is booked for a specific show."""
        return any(
            booking.show.show_id == show.show_id and seat in booking.seats
            for booking in self._bookings
        )

    def create_booking(
        self,
        booking_id: int,
        hall: Hall,
        show: MovieShow,
        requested_seats: tuple[tuple[int, int], ...],
    ) -> Booking:
        """Create a booking after validating all requested seats.

        Raises:
            ValueError: If the show, amount, or seat adjacency is invalid.
            SeatNotFoundError: If a requested seat does not exist.
            SeatAlreadyBookedError: If a requested seat is already booked.
        """
        if show.hall_number != hall.hall_number:
            raise ValueError("Show does not belong to the given hall")

        if not requested_seats:
            raise ValueError("At least one seat must be requested")

        if len(requested_seats) > MAX_SEATS_PER_BOOKING:
            raise ValueError(
                f"A booking can contain at most {MAX_SEATS_PER_BOOKING} seats"
            )

        seats = tuple(
            self.find_seat(hall, row, seat_number)
            for row, seat_number in requested_seats
        )

        if len(seats) != len(set(seats)):
            raise ValueError("A seat cannot be requested more than once")

        if not self._are_seats_adjacent(seats):
            raise ValueError("Requested seats must be adjacent in the same row")

        for seat in seats:
            if self.is_seat_booked(show, seat):
                raise SeatAlreadyBookedError(
                    f"Seat {seat.row}-{seat.seat_number} is already booked "
                    f"for show {show.show_id}"
                )

        booking = Booking(
            booking_id=booking_id,
            show=show,
            seats=seats,
        )
        self._bookings.append(booking)
        return booking

    def cancel_booking(self, booking_id: int) -> None:
        """Cancel an existing booking.

        Raises:
            BookingNotFoundError: If the booking does not exist.
        """
        for booking in self._bookings:
            if booking.booking_id == booking_id:
                self._bookings.remove(booking)
                return

        raise BookingNotFoundError(f"Booking {booking_id} does not exist")

    @staticmethod
    def _are_seats_adjacent(seats: tuple[Seat, ...]) -> bool:
        """Return whether seats are consecutive and belong to one row."""
        if not seats:
            return False

        row = seats[0].row
        if any(seat.row != row for seat in seats):
            return False

        seat_numbers = sorted(seat.seat_number for seat in seats)
        expected_numbers = list(
            range(seat_numbers[0], seat_numbers[0] + len(seat_numbers))
        )
        return seat_numbers == expected_numbers
