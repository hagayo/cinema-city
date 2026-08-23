"""Movie-show domain model."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from cinema.models.movie import Movie


@dataclass(frozen=True, slots=True)
class MovieShow:
    """Represent one screening of a movie in a specific hall and time."""

    show_id: int
    movie: Movie
    hall_number: int
    start_time: datetime
    ticket_price: int

    def __post_init__(self) -> None:
        """Validate movie-show values.

        Raises:
            ValueError: If an identifier is invalid or the ticket price is negative.
        """
        if self.show_id <= 0:
            raise ValueError("Show ID must be positive")

        if self.hall_number <= 0:
            raise ValueError("Hall number must be positive")

        if self.ticket_price < 0:
            raise ValueError("Ticket price cannot be negative")

    @property
    def end_time(self) -> datetime:
        """Return the calculated end time of the movie show."""
        return self.start_time + timedelta(minutes=self.movie.duration_minutes)
