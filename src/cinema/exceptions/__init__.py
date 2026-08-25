"""Application-specific exceptions."""

from cinema.exceptions.auth_errors import AuthorizationError
from cinema.exceptions.base import (
    BusinessError,
    CinemaError,
    MovieAlreadyExistsError,
    ValidationError,
)
from cinema.exceptions.booking_errors import (
    BookingError,
    BookingNotFoundError,
    BookingValidationError,
    SeatAlreadyBookedError,
    SeatNotFoundError,
)
from cinema.exceptions.schedule_errors import (
    NotEnoughScheduleSlotsError,
    ScheduleError,
    ScheduleValidationError,
)
from cinema.exceptions.storage_errors import StorageError
from cinema.exceptions.user_errors import UserIdentityConflictError, UserValidationError

__all__ = [
    "AuthorizationError",
    "BookingError",
    "BookingNotFoundError",
    "BookingValidationError",
    "BusinessError",
    "CinemaError",
    "MovieAlreadyExistsError",
    "NotEnoughScheduleSlotsError",
    "ScheduleError",
    "ScheduleValidationError",
    "SeatAlreadyBookedError",
    "SeatNotFoundError",
    "StorageError",
    "UserIdentityConflictError",
    "UserValidationError",
    "ValidationError",
]
