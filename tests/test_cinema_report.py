"""Tests for the cinema report script."""

from datetime import date

import cinema_report
from cinema.models import Cinema, Genre
from cinema.services import CinemaManager


class FakeStorageService:
    """Provide deterministic application state for report tests."""

    def load(self):
        """Return one movie, three shows, and two bookings."""
        cinema = Cinema.create_default("Cinema City")
        manager = CinemaManager(cinema)
        movie = manager.add_movie(
            "Comedy",
            90,
            "Funny movie.",
            Genre.COMEDY,
        )
        manager.schedule_movie(movie, date(2026, 8, 23), shows_per_hall=1)
        from types import SimpleNamespace
        return cinema, [
            SimpleNamespace(seats=(1, 2)),
            SimpleNamespace(seats=(3, 4, 5)),
        ]


def test_report_prints_current_totals(monkeypatch, capsys) -> None:
    """Report prints the current totals."""
    monkeypatch.setattr(cinema_report, "StorageService", FakeStorageService)

    cinema_report.main()

    output = capsys.readouterr().out
    assert "Movies: 1" in output
    assert "Shows: 3" in output
    assert "Bookings: 2" in output
    assert "Total booked seats: 5" in output
