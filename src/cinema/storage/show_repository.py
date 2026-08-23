"""JSON persistence for scheduled movie shows."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from cinema.models import Cinema, Movie, MovieShow

DEFAULT_SHOWS_FILE = Path("data/shows.json")


class ShowRepository:
    """Save and load scheduled movie shows."""

    def __init__(self, file_path: Path = DEFAULT_SHOWS_FILE) -> None:
        """Create a show repository."""
        self._file_path = file_path

    def load(
        self,
        cinema: Cinema,
        movies: list[Movie],
    ) -> None:
        """Load shows and attach them to each hall schedule."""
        if not self._file_path.exists():
            return

        with self._file_path.open("r", encoding="utf-8") as file:
            data: list[dict[str, Any]] = json.load(file)

        movies_by_id = {movie.movie_id: movie for movie in movies}
        halls_by_number = {hall.hall_number: hall for hall in cinema.halls}

        for item in data:
            hall_number = int(item["hall_number"])
            hall = halls_by_number[hall_number]
            movie = movies_by_id[int(item["movie_id"])]

            hall.schedule.add_show(
                MovieShow(
                    show_id=int(item["show_id"]),
                    movie=movie,
                    hall_number=hall_number,
                    start_time=datetime.fromisoformat(str(item["start_time"])),
                    ticket_price=int(item["ticket_price"]),
                )
            )

    def save(self, cinema: Cinema) -> None:
        """Persist all scheduled shows."""
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        data = [
            {
                "show_id": show.show_id,
                "movie_id": show.movie.movie_id,
                "hall_number": show.hall_number,
                "start_time": show.start_time.isoformat(),
                "ticket_price": show.ticket_price,
            }
            for hall in cinema.halls
            for show in hall.schedule.shows
        ]

        with self._file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
