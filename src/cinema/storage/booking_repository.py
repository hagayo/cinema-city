"""JSON persistence for customer bookings."""

import json
from pathlib import Path
from typing import Any

from cinema.models import Booking, Cinema, Seat

DEFAULT_BOOKINGS_FILE = Path("data/bookings.json")


class BookingRepository:
    """Save and load customer bookings."""

    def __init__(self, file_path: Path = DEFAULT_BOOKINGS_FILE) -> None:
        """Create a booking repository."""
        self._file_path = file_path

    def load(self, cinema: Cinema) -> list[Booking]:
        """Load bookings and reconnect them to scheduled shows."""
        if not self._file_path.exists():
            return []

        with self._file_path.open("r", encoding="utf-8") as file:
            data: list[dict[str, Any]] = json.load(file)

        shows_by_id = {show.show_id: show for hall in cinema.halls for show in hall.schedule.shows}

        return [
            Booking(
                booking_id=int(item["booking_id"]),
                show=shows_by_id[int(item["show_id"])],
                seats=tuple(
                    Seat(
                        row=int(seat_data["row"]),
                        seat_number=int(seat_data["seat_number"]),
                    )
                    for seat_data in item["seats"]
                ),
            )
            for item in data
        ]

    def save(self, bookings: tuple[Booking, ...] | list[Booking]) -> None:
        """Persist all customer bookings."""
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        data = [
            {
                "booking_id": booking.booking_id,
                "show_id": booking.show.show_id,
                "seats": [
                    {
                        "row": seat.row,
                        "seat_number": seat.seat_number,
                    }
                    for seat in booking.seats
                ],
            }
            for booking in bookings
        ]

        with self._file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
