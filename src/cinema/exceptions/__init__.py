"""Application-specific exceptions."""

from cinema.exceptions.booking_errors import (
    BookingNotFoundError,
    SeatAlreadyBookedError,
    SeatNotFoundError,
)
from cinema.exceptions.schedule_errors import (
    NotEnoughScheduleSlotsError,
)

__all__ = [
    "BookingNotFoundError",
    "NotEnoughScheduleSlotsError",
    "SeatAlreadyBookedError",
    "SeatNotFoundError",
]
