"""Cinema hall domain model."""

from dataclasses import dataclass, field
from typing import Self

from cinema.models.hall_schedule import HallSchedule
from cinema.models.seat import Seat


DEFAULT_ROWS = 20
DEFAULT_SEATS_PER_ROW = 20


@dataclass(slots=True)
class Hall:
    """Represent a cinema hall with seats and its own screening schedule."""

    hall_number: int
    seats: tuple[Seat, ...]
    schedule: HallSchedule = field(init=False)

    def __post_init__(self) -> None:
        """Validate hall data and create its schedule.

        Raises:
            ValueError: If the hall number or seat collection is invalid.
        """
        if self.hall_number <= 0:
            raise ValueError("Hall number must be positive")

        if not self.seats:
            raise ValueError("Hall must contain at least one seat")

        if len(self.seats) != len(set(self.seats)):
            raise ValueError("Hall cannot contain duplicate seats")

        self.schedule = HallSchedule(hall_number=self.hall_number)

    @classmethod
    def create_default(
        cls,
        hall_number: int,
        rows: int = DEFAULT_ROWS,
        seats_per_row: int = DEFAULT_SEATS_PER_ROW,
    ) -> Self:
        """Create a hall with a rectangular seat layout.

        Raises:
            ValueError: If rows or seats per row are not positive.
        """
        if rows <= 0:
            raise ValueError("Number of rows must be positive")

        if seats_per_row <= 0:
            raise ValueError("Seats per row must be positive")

        seats = tuple(
            Seat(row=row, seat_number=seat_number)
            for row in range(1, rows + 1)
            for seat_number in range(1, seats_per_row + 1)
        )
        return cls(hall_number=hall_number, seats=seats)
