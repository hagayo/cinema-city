"""Tests for CLI menu routing and application-boundary helpers."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from cinema.cli import customer_cli, manager_cli
from cinema.cli.error_handling import run_cli_safely
from cinema.cli.input_helpers import read_genre
from cinema.exceptions import MovieAlreadyExistsError
from cinema.models import Genre, Hall, Movie, MovieShow, Seat, User
from cinema.time_utils import CINEMA_TIMEZONE


def test_read_genre_retries_then_returns_valid(monkeypatch, capsys) -> None:
    answers = iter(["bad", "99", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert read_genre() == list(Genre)[0]
    assert "Invalid genre." in capsys.readouterr().out


def test_customer_menu_routes_every_option(monkeypatch, capsys) -> None:
    storage = MagicMock()
    hall = Hall(1, "Hall A")
    seat = Seat(1, 1, 1, 1)
    movie = Movie(1, "Dune", 120, "Description", Genre.DRAMA, 40)
    show = MovieShow(
        1, 1, 1, datetime(2026, 9, 1, 18, tzinfo=CINEMA_TIMEZONE), 40
    )
    storage.load_catalog.return_value = (
        MagicMock(),
        [hall],
        [seat],
        [movie],
        [show],
    )
    monkeypatch.setattr(customer_cli, "create_json_storage_service", lambda: storage)

    list_week = MagicMock()
    list_genre = MagicMock()
    book = MagicMock()
    cancel = MagicMock()
    monkeypatch.setattr(customer_cli, "list_upcoming_shows", list_week)
    monkeypatch.setattr(customer_cli, "list_upcoming_shows_by_genre", list_genre)
    monkeypatch.setattr(customer_cli, "book_show_interactively", book)
    monkeypatch.setattr(customer_cli, "cancel_booking_interactively", cancel)

    answers = iter(["auth0|dana", "1", "2", "3", "4", "bad", "5"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    customer_cli.run_customer_cli()

    assert list_week.call_count == 1
    assert list_genre.call_count == 1
    assert book.call_count == 1
    assert cancel.call_count == 1
    out = capsys.readouterr().out
    assert "Unknown option." in out
    assert "Goodbye." in out


def test_customer_main_uses_safe_wrapper(monkeypatch) -> None:
    wrapper = MagicMock()
    monkeypatch.setattr(customer_cli, "run_cli_safely", wrapper)
    customer_cli.main()
    wrapper.assert_called_once_with(customer_cli.run_customer_cli)


def test_manager_menu_routes_every_option(monkeypatch, capsys) -> None:
    storage = MagicMock()
    hall = Hall(1, "Hall A")
    seat = Seat(1, 1, 1, 1)
    movie = Movie(1, "Dune", 120, "Description", Genre.DRAMA, 40)
    show = MovieShow(
        1, 1, 1, datetime(2026, 9, 1, 18, tzinfo=CINEMA_TIMEZONE), 40
    )
    user = User(1, "auth0|dana", "Dana Cohen", "+972501234567", "dana@example.com")
    storage.movie_repository.load.return_value = [movie]
    storage.user_repository.load.return_value = [user]
    storage.load_catalog.return_value = (
        MagicMock(),
        [hall],
        [seat],
        [movie],
        [show],
    )
    storage.load_bookings.return_value = ([], [])
    monkeypatch.setattr(manager_cli, "create_json_storage_service", lambda: storage)
    monkeypatch.setattr(manager_cli, "SchedulingService", MagicMock())
    monkeypatch.setattr(manager_cli, "CinemaManager", MagicMock())

    add = MagicMock()
    schedule = MagicMock()
    list_movies = MagicMock()
    list_shows = MagicMock()
    list_bookings = MagicMock()
    report = MagicMock()
    monkeypatch.setattr(manager_cli, "add_movie_interactively", add)
    monkeypatch.setattr(manager_cli, "schedule_movie_interactively", schedule)
    monkeypatch.setattr(manager_cli, "list_movies", list_movies)
    monkeypatch.setattr(manager_cli, "list_shows_by_hall", list_shows)
    monkeypatch.setattr(manager_cli, "list_bookings", list_bookings)
    monkeypatch.setattr(manager_cli, "print_report", report)

    answers = iter(["1", "2", "3", "4", "5", "6", "bad", "7"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    manager_cli.run_manager_cli()

    assert add.call_count == 1
    assert schedule.call_count == 1
    assert list_movies.call_count == 1
    assert list_shows.call_count == 1
    assert list_bookings.call_count == 1
    assert report.call_count == 1
    out = capsys.readouterr().out
    assert "Unknown option." in out
    assert "Goodbye." in out


def test_manager_menu_handles_add_movie_business_error(monkeypatch, capsys) -> None:
    storage = MagicMock()
    monkeypatch.setattr(manager_cli, "create_json_storage_service", lambda: storage)
    monkeypatch.setattr(manager_cli, "SchedulingService", MagicMock())
    monkeypatch.setattr(manager_cli, "CinemaManager", MagicMock())
    monkeypatch.setattr(
        manager_cli,
        "add_movie_interactively",
        MagicMock(side_effect=MovieAlreadyExistsError("duplicate")),
    )
    answers = iter(["1", "7"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    manager_cli.run_manager_cli()
    assert "Cannot add movie: duplicate" in capsys.readouterr().out


def test_manager_main_uses_safe_wrapper(monkeypatch) -> None:
    wrapper = MagicMock()
    monkeypatch.setattr(manager_cli, "run_cli_safely", wrapper)
    manager_cli.main()
    wrapper.assert_called_once_with(manager_cli.run_manager_cli)


def test_safe_wrapper_handles_unexpected_exception(monkeypatch, capsys) -> None:
    monkeypatch.setattr("cinema.cli.error_handling.configure_logging", lambda: None)
    with pytest.raises(SystemExit):
        run_cli_safely(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert "Unexpected application error" in capsys.readouterr().out
