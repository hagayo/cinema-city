"""Movie domain model."""

from dataclasses import dataclass

from cinema.models.genre import Genre


MAX_DESCRIPTION_LENGTH = 300
MAX_DURATION_LENGTH = 240


@dataclass(frozen=True, slots=True)
class Movie:
    """A movie that may be screened at different times and halls."""

    movie_id: int
    title: str
    duration_minutes: int
    description: str
    genre: Genre

    def __post_init__(self) -> None:
        """Validate movie data after object creation."""
        if self.movie_id <= 0:
            raise ValueError("Movie ID must be positive")

        if not self.title.strip():
            raise ValueError("Movie title cannot be empty")

        if self.duration_minutes <= 0 or self.duration_minutes > MAX_DURATION_LENGTH:
            raise ValueError("Movie duration must be positive")

        if not self.description.strip():
            raise ValueError("Movie description cannot be empty")

        if len(self.description) > MAX_DESCRIPTION_LENGTH:
            raise ValueError(
                f"Movie description cannot exceed "
                f"{MAX_DESCRIPTION_LENGTH} characters"
            )
