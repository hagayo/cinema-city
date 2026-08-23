"""Exceptions related to cinema scheduling."""


class ScheduleError(Exception):
    """Base exception for scheduling-related errors."""


class NotEnoughScheduleSlotsError(ScheduleError):
    """Raised when not enough available screening slots can be found."""
