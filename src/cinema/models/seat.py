"""Seat domain model."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Seat:
    """A physical seat located inside a cinema hall."""

    row: int
    seat_number: int

    def __post_init__(self) -> None:
        """Validate seat location values."""
        if self.row <= 0:
            raise ValueError("Seat row must be positive")

        if self.seat_number <= 0:
            raise ValueError("Seat number must be positive")
