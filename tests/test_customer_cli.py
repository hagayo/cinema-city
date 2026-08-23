"""Unit tests for customer CLI helpers."""

from datetime import date

from cinema.cli.customer_cli import (
    get_upcoming_shows_by_genre,
    find_hall_by_number,
    find_show_by_id,
    get_upcoming_shows,
)
from cinema.models import Cinema, Genre
from cinema.services import CinemaManager


def create_cinema_with_show() -> Cinema:
    """Create a cinema with one movie scheduled today."""
    cinema = Cinema.create_default("Cinema City")
    manager = CinemaManager(cinema)
    movie = manager.add_movie(
        title="Dune",
        duration_minutes=120,
        description="Science fiction epic.",
        genre=Genre.DRAMA,
        ticket_price=40,
    )
    manager.schedule_movie(
        movie=movie,
        screening_date=date.today(),
        shows_per_hall=1,
    )
    return cinema


def test_get_upcoming_shows_returns_current_week_shows() -> None:
    """Shows scheduled today are returned as upcoming shows."""
    cinema = create_cinema_with_show()

    shows = get_upcoming_shows(cinema, date.today())

    assert len(shows) == 3


def test_find_show_by_id() -> None:
    """Scheduled shows can be selected by ID."""
    cinema = create_cinema_with_show()
    show = get_upcoming_shows(cinema, date.today())[0]

    assert find_show_by_id(cinema, show.show_id) == show


def test_find_hall_by_number() -> None:
    """Cinema halls can be selected by hall number."""
    cinema = create_cinema_with_show()

    hall = find_hall_by_number(cinema, 2)

    assert hall is not None
    assert hall.hall_number == 2


def test_filter_upcoming_shows_by_genre() -> None:
    """Upcoming shows can be filtered by movie genre."""
    cinema = Cinema.create_default("Cinema City")
    manager = CinemaManager(cinema)

    drama = manager.add_movie(
        "Drama Movie",
        120,
        "Drama description.",
        Genre.DRAMA,
        40,
    )
    comedy = manager.add_movie(
        "Comedy Movie",
        90,
        "Comedy description.",
        Genre.COMEDY,
        40,
    )

    manager.schedule_movie(
        drama,
        date.today(),
        shows_per_hall=1,
    )
    manager.schedule_movie(
        comedy,
        date.today(),
        shows_per_hall=1,
    )

    shows = get_upcoming_shows_by_genre(
        cinema,
        date.today(),
        Genre.COMEDY,
    )

    assert shows
    assert all(show.movie.genre == Genre.COMEDY for show in shows)
