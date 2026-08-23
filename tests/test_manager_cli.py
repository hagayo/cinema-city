"""Unit tests for cinema manager CLI helper functions."""

from unittest.mock import patch

from cinema.cli.manager_cli import (
    find_movie_by_id_or_title,
    list_bookings,
    list_shows_by_hall,
    read_ticket_price,
    read_non_empty_text,
    read_positive_int,
)
from cinema.models import Genre, Movie


def test_read_positive_int_accepts_positive_number() -> None:
    """Positive integers are returned as numbers."""
    with patch("builtins.input", return_value="120"):
        assert read_positive_int("Duration: ") == 120


def test_read_positive_int_retries_after_invalid_input() -> None:
    """Invalid values are rejected until a positive integer is entered."""
    with patch("builtins.input", side_effect=["abc", "0", "90"]):
        assert read_positive_int("Duration: ") == 90


def test_read_non_empty_text_retries_after_empty_input() -> None:
    """Empty strings are rejected."""
    with patch("builtins.input", side_effect=["   ", "Dune"]):
        assert read_non_empty_text("Title: ") == "Dune"


def test_find_movie_by_id() -> None:
    """A movie can be selected by its numeric ID."""
    movie = Movie(1, "Dune", 166, "Science fiction.", Genre.DRAMA, 40)

    assert find_movie_by_id_or_title([movie], "1") == movie


def test_find_movie_by_title_is_case_insensitive() -> None:
    """A movie can be selected by its title without case sensitivity."""
    movie = Movie(1, "Dune", 166, "Science fiction.", Genre.DRAMA, 40)

    assert find_movie_by_id_or_title([movie], "dune") == movie


def test_find_movie_returns_none_when_missing() -> None:
    """Missing movie references return None."""
    movie = Movie(1, "Dune", 166, "Science fiction.", Genre.DRAMA, 40)

    assert find_movie_by_id_or_title([movie], "Avatar") is None


def test_read_ticket_price_uses_default_when_empty() -> None:
    """Pressing Enter uses the default price of 40 NIS."""
    with patch("builtins.input", return_value=""):
        assert read_ticket_price() == 40


def test_read_ticket_price_retries_until_value_is_in_range() -> None:
    """Invalid prices are rejected until a value from 1 to 99 is entered."""
    with patch("builtins.input", side_effect=["abc", "0", "100", "55"]):
        assert read_ticket_price() == 55


def test_list_shows_by_hall_prints_only_selected_hall(capsys) -> None:
    """Manager can list shows for one selected hall."""
    from datetime import date
    from cinema.models import Cinema
    from cinema.services import CinemaManager

    cinema = Cinema.create_default("Cinema City")
    manager = CinemaManager(cinema)
    movie = manager.add_movie("Dune", 120, "Science fiction.", Genre.DRAMA, 40)
    manager.schedule_movie(movie, date(2026, 8, 23), shows_per_hall=1)

    with patch("builtins.input", return_value="2"):
        list_shows_by_hall(cinema)

    output = capsys.readouterr().out
    assert "Hall 2 Shows" in output
    assert "Dune" in output
    assert "Hall 1 Shows" not in output


def test_list_bookings_prints_booking_details(capsys) -> None:
    """Manager booking list includes booking and seat information."""
    from datetime import datetime
    from cinema.models import Booking, MovieShow, Seat

    movie = Movie(1, "Dune", 120, "Science fiction.", Genre.DRAMA, 40)
    show = MovieShow(1, movie, 2, datetime(2026, 8, 23, 18, 0), 40)
    booking = Booking(1, show, (Seat(1, 3), Seat(1, 4)))

    list_bookings([booking])

    output = capsys.readouterr().out
    assert "#1" in output
    assert "Dune" in output
    assert "R1-S3" in output
    assert "Total: 80 NIS" in output
