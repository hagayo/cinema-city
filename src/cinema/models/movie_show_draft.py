"""Non-persisted movie-show creation DTO."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class MovieShowDraft:
    """Describe a planned show before the repository allocates its ID."""

    movie_id: int
    hall_id: int
    start_time: datetime
    ticket_price: int
