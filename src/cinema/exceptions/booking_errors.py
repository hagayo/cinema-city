"""Exceptions related to cinema bookings."""


class BookingError(Exception):
    """Base exception for booking-related errors."""


class SeatNotFoundError(BookingError):
    """Raised when a requested seat does not exist in the show hall."""


class SeatAlreadyBookedError(BookingError):
    """Raised when a requested seat is already booked for a show."""


class BookingNotFoundError(BookingError):
    """Raised when a requested booking cannot be found."""
