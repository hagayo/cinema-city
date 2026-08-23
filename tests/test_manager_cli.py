"""Unit tests for cinema manager CLI helper functions."""

from unittest.mock import patch

from cinema.cli.manager_cli import (
    find_movie_by_id_or_title,
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
    movie = Movie(1, "Dune", 166, "Science fiction.", Genre.DRAMA)

    assert find_movie_by_id_or_title([movie], "1") == movie


def test_find_movie_by_title_is_case_insensitive() -> None:
    """A movie can be selected by its title without case sensitivity."""
    movie = Movie(1, "Dune", 166, "Science fiction.", Genre.DRAMA)

    assert find_movie_by_id_or_title([movie], "dune") == movie


def test_find_movie_returns_none_when_missing() -> None:
    """Missing movie references return None."""
    movie = Movie(1, "Dune", 166, "Science fiction.", Genre.DRAMA)

    assert find_movie_by_id_or_title([movie], "Avatar") is None
