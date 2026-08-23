"""Unit tests for cinema manager operations."""

from datetime import date, time

import pytest

from cinema.exceptions import NotEnoughScheduleSlotsError
from cinema.models import Cinema, Genre
from cinema.services import CinemaManager


def test_manager_adds_movie_to_catalog() -> None:
    """Cinema manager can create and register a new movie."""
    cinema = Cinema.create_default("Cinema City")
    manager = CinemaManager(cinema)

    movie = manager.add_movie(
        title="Dune",
        duration_minutes=166,
        description="Science fiction epic.",
        genre=Genre.DRAMA,
    )

    assert cinema.movies == [movie]
    assert movie.movie_id == 1


def test_manager_schedules_three_shows_in_every_hall() -> None:
    """One movie is scheduled three times in each of three halls."""
    cinema = Cinema.create_default("Cinema City")
    manager = CinemaManager(cinema)
    movie = manager.add_movie("Dune", 120, "Science fiction epic.", Genre.DRAMA)

    shows = manager.schedule_movie(movie, date(2026, 8, 23))

    assert len(shows) == 9
    assert all(len(hall.schedule.shows) == 3 for hall in cinema.halls)


def test_scheduled_shows_have_different_non_overlapping_times() -> None:
    """Each hall receives three distinct, non-overlapping screening times."""
    cinema = Cinema.create_default("Cinema City")
    manager = CinemaManager(cinema)
    movie = manager.add_movie("Dune", 120, "Science fiction epic.", Genre.DRAMA)

    manager.schedule_movie(movie, date(2026, 8, 23))

    for hall in cinema.halls:
        shows = hall.schedule.shows
        assert len({show.start_time for show in shows}) == 3
        assert all(
            first.end_time <= second.start_time
            for first, second in zip(shows, shows[1:])
        )


def test_schedule_movie_uses_integer_ticket_price() -> None:
    """Scheduled ticket prices are stored as whole shekel integers."""
    cinema = Cinema.create_default("Cinema City")
    manager = CinemaManager(cinema)
    movie = manager.add_movie("Dune", 120, "Science fiction epic.", Genre.DRAMA)

    shows = manager.schedule_movie(
        movie,
        date(2026, 8, 23),
        shows_per_hall=1,
        ticket_price=50,
    )

    assert all(show.ticket_price == 50 for show in shows)
    assert all(isinstance(show.ticket_price, int) for show in shows)


def test_schedule_movie_rejects_negative_ticket_price() -> None:
    """Cinema manager rejects a negative ticket price."""
    cinema = Cinema.create_default("Cinema City")
    manager = CinemaManager(cinema)
    movie = manager.add_movie("Dune", 120, "Science fiction epic.", Genre.DRAMA)

    with pytest.raises(ValueError, match="price"):
        manager.schedule_movie(
            movie,
            date(2026, 8, 23),
            ticket_price=-1,
        )


def test_schedule_movie_is_atomic_when_a_hall_has_too_few_slots() -> None:
    """No show is added if one hall cannot satisfy the scheduling request."""
    cinema = Cinema.create_default("Cinema City")
    manager = CinemaManager(cinema)
    movie = manager.add_movie("Long Movie", 180, "A long movie.", Genre.DRAMA)

    cinema.halls[2].schedule.opening_time = time(22, 0)
    cinema.halls[2].schedule.closing_time = time(23, 0)

    with pytest.raises(NotEnoughScheduleSlotsError):
        manager.schedule_movie(movie, date(2026, 8, 23))

    assert all(not hall.schedule.shows for hall in cinema.halls)
