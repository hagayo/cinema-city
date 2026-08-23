"""JSON persistence for movie catalog data."""

import json
from pathlib import Path
from typing import Any

from cinema.models import Genre, Movie


DEFAULT_MOVIES_FILE = Path("data/movies.json")


class MovieRepository:
    """Save and load the movie catalog."""

    def __init__(self, file_path: Path = DEFAULT_MOVIES_FILE) -> None:
        """Create a movie repository."""
        self._file_path = file_path

    def load(self) -> list[Movie]:
        """Load all movies from disk."""
        if not self._file_path.exists():
            return []

        with self._file_path.open("r", encoding="utf-8") as file:
            data: list[dict[str, Any]] = json.load(file)

        return [
            Movie(
                movie_id=int(item["movie_id"]),
                title=str(item["title"]),
                duration_minutes=int(item["duration_minutes"]),
                description=str(item["description"]),
                genre=Genre(str(item["genre"])),
            )
            for item in data
        ]

    def save(self, movies: list[Movie]) -> None:
        """Persist all movies."""
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        data = [
            {
                "movie_id": movie.movie_id,
                "title": movie.title,
                "duration_minutes": movie.duration_minutes,
                "description": movie.description,
                "genre": movie.genre.value,
            }
            for movie in movies
        ]

        with self._file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
