"""Unit tests for booking operations."""

import pytest

from cinema.exceptions import SeatAlreadyBookedError
from cinema.services import BookingService
from tests.factories import make_show, make_small_hall


def test_create_booking_for_available_seat() -> None:
    """Available seat can be booked for a show."""
    hall = make_small_hall()
    show = make_show(hall_number=hall.hall_number)
    service = BookingService()

    booking = service.create_booking(
        booking_id=1,
        hall=hall,
        show=show,
        requested_seats=((1, 1),),
    )

    assert booking.seats[0].row == 1
    assert booking.seats[0].seat_number == 1


def test_same_seat_cannot_be_booked_twice_for_same_show() -> None:
    """Same physical seat cannot be booked twice for one show."""
    hall = make_small_hall()
    show = make_show(hall_number=hall.hall_number)
    service = BookingService()

    service.create_booking(1, hall, show, ((1, 1),))

    with pytest.raises(SeatAlreadyBookedError):
        service.create_booking(2, hall, show, ((1, 1),))


def test_booking_rejects_more_than_five_seats() -> None:
    """A customer cannot book more than five seats at once."""
    hall = make_small_hall()
    show = make_show(hall_number=hall.hall_number)
    service = BookingService()

    with pytest.raises(ValueError, match="at most 5"):
        service.create_booking(
            1,
            hall,
            show,
            ((1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6)),
        )


def test_booking_rejects_non_adjacent_seats() -> None:
    """Requested seats must be consecutive in one row."""
    hall = make_small_hall()
    show = make_show(hall_number=hall.hall_number)
    service = BookingService()

    with pytest.raises(ValueError, match="adjacent"):
        service.create_booking(
            1,
            hall,
            show,
            ((1, 1), (2, 1)),
        )
