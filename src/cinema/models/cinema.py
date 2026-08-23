"""Cinema domain model."""

from dataclasses import dataclass, field
from typing import Self

from cinema.models.hall import Hall
from cinema.models.movie import Movie


DEFAULT_HALL_COUNT = 3


@dataclass(slots=True)
class Cinema:
    """Represent a cinema containing halls and a movie catalog."""

    name: str
    halls: tuple[Hall, ...]
    movies: list[Movie] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate cinema configuration.

        Raises:
            ValueError: If the name, halls, or hall numbers are invalid.
        """
        if not self.name.strip():
            raise ValueError("Cinema name cannot be empty")

        if not self.halls:
            raise ValueError("Cinema must contain at least one hall")

        hall_numbers = [hall.hall_number for hall in self.halls]
        if len(hall_numbers) != len(set(hall_numbers)):
            raise ValueError("Cinema cannot contain duplicate hall numbers")

    @classmethod
    def create_default(
        cls,
        name: str,
        hall_count: int = DEFAULT_HALL_COUNT,
    ) -> Self:
        """Create a cinema with the default number and size of halls.

        Raises:
            ValueError: If the requested hall count is not positive.
        """
        if hall_count <= 0:
            raise ValueError("Hall count must be positive")

        halls = tuple(
            Hall.create_default(hall_number=hall_number)
            for hall_number in range(1, hall_count + 1)
        )
        return cls(name=name, halls=halls)
