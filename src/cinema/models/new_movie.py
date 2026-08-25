"""Movie creation DTO."""

from dataclasses import dataclass

from cinema.models.genre import Genre


@dataclass(frozen=True, slots=True)
class NewMovie:
    """Data required to create a movie before a movie_id exists."""

    title: str
    duration_minutes: int
    description: str
    genre: Genre
    ticket_price: int
