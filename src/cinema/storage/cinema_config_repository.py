"""JSON persistence for cinema configuration."""

import json
from pathlib import Path
from typing import Any

from cinema.models import Cinema, Hall


DEFAULT_CONFIG_FILE = Path("data/cinema_config.json")


class CinemaConfigRepository:
    """Save and load cinema configuration."""

    def __init__(self, file_path: Path = DEFAULT_CONFIG_FILE) -> None:
        """Create a repository using the given config file."""
        self._file_path = file_path

    def load(self) -> Cinema:
        """Load cinema configuration, creating defaults when missing."""
        if not self._file_path.exists():
            cinema = Cinema.create_default("Cinema City")
            self.save(cinema)
            return cinema

        with self._file_path.open("r", encoding="utf-8") as file:
            data: dict[str, Any] = json.load(file)

        halls = tuple(
            Hall.create_default(
                hall_number=int(hall_data["hall_number"]),
                rows=int(hall_data["rows"]),
                seats_per_row=int(hall_data["seats_per_row"]),
            )
            for hall_data in data["halls"]
        )

        return Cinema(
            name=str(data["name"]),
            halls=halls,
        )

    def save(self, cinema: Cinema) -> None:
        """Persist cinema configuration."""
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "name": cinema.name,
            "halls": [
                {
                    "hall_number": hall.hall_number,
                    "rows": max(seat.row for seat in hall.seats),
                    "seats_per_row": max(
                        seat.seat_number
                        for seat in hall.seats
                        if seat.row == 1
                    ),
                }
                for hall in cinema.halls
            ],
        }

        with self._file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
