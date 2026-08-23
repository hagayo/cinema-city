"""Tests for the cinema report script."""

from datetime import datetime

import pytest

import cinema_report
from cinema.models import Booking, Cinema, Genre, Movie, MovieShow, Seat


class FakeStorageService:
    """Storage substitute that returns valid domain objects."""

    def load(self) -> tuple[Cinema, list[Booking]]:
        """Return a cinema and real bookings for report testing."""
        cinema = Cinema.create_default("Cinema City")

        movie = Movie(
            movie_id=1,
            title="Dune",
            duration_minutes=120,
            description="Science fiction.",
            genre=Genre.DRAMA,
            ticket_price=40,
        )

        cinema.movies.append(movie)

        show = MovieShow(
            show_id=1,
            movie=movie,
            hall_number=1,
            start_time=datetime(2026, 8, 23, 18, 0),
            ticket_price=movie.ticket_price,
        )

        cinema.halls[0].schedule.add_show(show)

        bookings = [
            Booking(
                booking_id=1,
                show=show,
                seats=(Seat(1, 1), Seat(1, 2)),
            ),
            Booking(
                booking_id=2,
                show=show,
                seats=(Seat(2, 1), Seat(2, 2), Seat(2, 3)),
            ),
        ]

        return cinema, bookings


def test_report_prints_current_totals(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Report prints movie, show, booking, and booked-seat totals."""
    monkeypatch.setattr(
        cinema_report,
        "StorageService",
        FakeStorageService,
    )

    cinema_report.main()

    output = capsys.readouterr().out

    assert "Movies: 1" in output
    assert "Shows: 1" in output
    assert "Bookings: 2" in output
    assert "Total booked seats: 5" in output
