"""Coverage and behavior tests for customer and manager CLI layers."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cinema.cli import customer_cli, manager_cli
from cinema.exceptions import BookingValidationError, MovieAlreadyExistsError
from cinema.models import (
    Booking,
    BookingRequest,
    BookingSeat,
    Genre,
    Hall,
    Movie,
    MovieShow,
    MovieShowDraft,
    NewMovie,
    NewUser,
    Seat,
    User,
    customer_auth_context,
    manager_auth_context,
)
from cinema.time_utils import CINEMA_TIMEZONE
from tests.conftest import CinemaEnvironment


def sample_state():
    halls = [Hall(1, "Hall Alpha"), Hall(2, "Hall Beta")]
    seats = [
        Seat(1, 1, 1, 1),
        Seat(2, 1, 1, 2),
        Seat(3, 2, 1, 1),
        Seat(4, 2, 1, 2),
    ]
    movies = [
        Movie(1, "Dune", 120, "Description", Genre.DRAMA, 40),
        Movie(2, "Alien", 90, "Description", Genre.THRILLER, 45),
    ]
    now = datetime(2026, 9, 1, 12, tzinfo=CINEMA_TIMEZONE)
    shows = [
        MovieShow(1, 1, 1, now + timedelta(hours=2), 40),
        MovieShow(2, 2, 2, now + timedelta(days=1), 45),
        MovieShow(3, 1, 1, now - timedelta(hours=1), 40),
    ]
    return halls, seats, movies, shows, now


def test_customer_show_helpers(capsys) -> None:
    halls, _, movies, shows, now = sample_state()
    upcoming = customer_cli.get_upcoming_shows(shows, now)
    assert [show.show_id for show in upcoming] == [1, 2]

    drama = customer_cli.get_upcoming_shows_by_genre(
        shows, movies, now, Genre.DRAMA
    )
    assert [show.show_id for show in drama] == [1]
    assert customer_cli.find_show_by_id(upcoming, 2) == shows[1]
    assert customer_cli.find_show_by_id(upcoming, 99) is None
    assert customer_cli.find_hall_by_id(halls, 2) == halls[1]
    assert customer_cli.find_hall_by_id(halls, 99) is None

    customer_cli.print_shows(upcoming, movies, halls)
    out = capsys.readouterr().out
    assert "Dune" in out
    assert "Hall Alpha" in out


def test_customer_list_empty_and_genre_empty(monkeypatch, capsys) -> None:
    halls, _, movies, _, now = sample_state()
    assert customer_cli.list_upcoming_shows([], movies, halls, now) == ()
    assert "No shows" in capsys.readouterr().out

    monkeypatch.setattr(customer_cli, "read_genre", lambda: Genre.FAMILY)
    customer_cli.list_upcoming_shows_by_genre([], movies, halls, now)
    assert "No family shows" in capsys.readouterr().out


def test_customer_input_helpers_retry(monkeypatch, capsys) -> None:
    values = iter(["x", "0", "2"])
    monkeypatch.setattr("builtins.input", lambda _: next(values))
    assert customer_cli.read_positive_int("X") == 2
    assert "whole number" in capsys.readouterr().out

    values = iter(["6", "2", "1", "3"])
    monkeypatch.setattr("builtins.input", lambda _: next(values))
    assert customer_cli.read_requested_seats() == ((1, 3), (1, 4))


def test_customer_booking_success(environment: CinemaEnvironment, monkeypatch, capsys) -> None:
    storage = environment.storage()
    movie = storage.movie_repository.create(
        NewMovie("Dune", 120, "Description", Genre.DRAMA, 40)
    )
    show = storage.show_repository.create_many([
        MovieShowDraft(
            movie.movie_id,
            1,
            datetime(2026, 9, 1, 18, tzinfo=CINEMA_TIMEZONE),
            40,
        )
    ])[0]
    _, halls, seats, movies, shows = storage.load_catalog()

    answers = iter(["1", "Dana Cohen", "0501234567", "dana@example.com", "2", "1", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    customer_cli.book_show_interactively(
        actor=customer_auth_context("auth0|dana"),
        halls=halls,
        seats=seats,
        movies=movies,
        shows=shows,
        booking_repository=storage.booking_repository,
        user_repository=storage.user_repository,
        current_time=datetime(2026, 9, 1, 12, tzinfo=CINEMA_TIMEZONE),
    )
    assert "confirmed" in capsys.readouterr().out
    users = storage.user_repository.load()
    bookings, rows = storage.load_bookings(shows, seats, users)
    assert len(bookings) == 1
    assert len(rows) == 2


def test_customer_booking_unavailable_show(
    environment: CinemaEnvironment, monkeypatch, capsys
) -> None:
    storage = environment.storage()
    movie = storage.movie_repository.create(
        NewMovie("Dune", 120, "Description", Genre.DRAMA, 40)
    )
    show = storage.show_repository.create_many([
        MovieShowDraft(
            movie.movie_id,
            1,
            datetime(2026, 9, 1, 18, tzinfo=CINEMA_TIMEZONE),
            40,
        )
    ])[0]
    _, halls, seats, movies, shows = storage.load_catalog()
    monkeypatch.setattr("builtins.input", lambda _: "99")

    customer_cli.book_show_interactively(
        actor=customer_auth_context("auth0|dana"),
        halls=halls,
        seats=seats,
        movies=movies,
        shows=shows,
        booking_repository=storage.booking_repository,
        user_repository=storage.user_repository,
        current_time=show.start_time - timedelta(hours=2),
    )
    assert "not available" in capsys.readouterr().out


def test_customer_cancel_success_and_mismatch(
    environment: CinemaEnvironment, monkeypatch, capsys
) -> None:
    storage = environment.storage()
    movie = storage.movie_repository.create(
        NewMovie("Dune", 120, "Description", Genre.DRAMA, 40)
    )
    show = storage.show_repository.create_many([
        MovieShowDraft(movie.movie_id, 1, datetime(2026, 9, 1, 18, tzinfo=CINEMA_TIMEZONE),
            40)
    ])[0]
    _, _, seats, _, shows = storage.load_catalog()
    user = storage.user_repository.create(
        NewUser(
            "auth0|dana",
            "Dana Cohen",
            "0501234567",
            "dana@example.com",
        )
    )
    request = customer_cli.BookingService.prepare_booking(
        actor=customer_auth_context(user.auth_subject),
        user=user,
        show=show,
        requested_seats=((1, 1),),
        seats=seats,
    )
    booking, _ = storage.booking_repository.add(request)

    answers = iter([str(booking.booking_id)])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    customer_cli.cancel_booking_interactively(
        actor=customer_auth_context("auth0|other"),
        seats=seats,
        shows=shows,
        booking_repository=storage.booking_repository,
        user_repository=storage.user_repository,
        current_time=show.start_time - timedelta(hours=2),
    )
    assert "profile was not found" in capsys.readouterr().out

    answers = iter([str(booking.booking_id)])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    customer_cli.cancel_booking_interactively(
        actor=customer_auth_context(user.auth_subject),
        seats=seats,
        shows=shows,
        booking_repository=storage.booking_repository,
        user_repository=storage.user_repository,
        current_time=show.start_time - timedelta(hours=2),
    )
    assert "cancelled" in capsys.readouterr().out


def test_manager_input_helpers(monkeypatch, capsys) -> None:
    values = iter(["x", "0", "3"])
    monkeypatch.setattr("builtins.input", lambda _: next(values))
    assert manager_cli.read_positive_int("X") == 3

    values = iter(["x", "100", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(values))
    assert manager_cli.read_ticket_price() == 40

    values = iter([" ", "hello"])
    monkeypatch.setattr("builtins.input", lambda _: next(values))
    assert manager_cli.read_non_empty_text("X") == "hello"
    assert capsys.readouterr().out


def test_manager_movie_helpers(environment: CinemaEnvironment, monkeypatch, capsys) -> None:
    storage = environment.storage()
    scheduler = manager_cli.SchedulingService(
        storage.config_repository,
        storage.movie_repository,
        storage.show_repository,
    )
    manager = manager_cli.CinemaManager(storage.movie_repository, scheduler)
    actor = manager_auth_context("auth0|manager")
    movie = manager.add_movie(
        actor,
        NewMovie("Dune", 120, "Description", Genre.DRAMA, 40),
    )

    assert manager_cli.find_movie_by_id_or_title([movie], "1") == movie
    assert manager_cli.find_movie_by_id_or_title([movie], "DUNE") == movie
    assert manager_cli.find_movie_by_id_or_title([movie], "missing") is None

    manager_cli.list_movies([])
    assert "No movies" in capsys.readouterr().out
    manager_cli.list_movies([movie])
    assert "Dune" in capsys.readouterr().out

    answers = iter(["Missing"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert manager_cli.schedule_movie_interactively([movie], manager, actor) == ()
    assert "not found" in capsys.readouterr().out


def test_manager_schedule_and_list_shows(
    environment: CinemaEnvironment, monkeypatch, capsys
) -> None:
    storage = environment.storage()
    scheduler = manager_cli.SchedulingService(
        storage.config_repository,
        storage.movie_repository,
        storage.show_repository,
    )
    manager = manager_cli.CinemaManager(storage.movie_repository, scheduler)
    actor = manager_auth_context("auth0|manager")
    movie = manager.add_movie(
        actor,
        NewMovie("Dune", 120, "Description", Genre.DRAMA, 40),
    )

    monkeypatch.setattr(
        manager_cli,
        "local_now",
        lambda: datetime(2026, 9, 1, 8, tzinfo=CINEMA_TIMEZONE),
    )
    monkeypatch.setattr("builtins.input", lambda _: "1")
    shows = manager_cli.schedule_movie_interactively([movie], manager, actor)
    assert len(shows) == 9

    _, halls, _, movies, loaded_shows = storage.load_catalog()
    monkeypatch.setattr("builtins.input", lambda _: "1")
    manager_cli.list_shows_by_hall(halls, movies, loaded_shows)
    assert "Hall Alpha Shows" in capsys.readouterr().out

    monkeypatch.setattr("builtins.input", lambda _: "99")
    manager_cli.list_shows_by_hall(halls, movies, loaded_shows)
    assert "does not exist" in capsys.readouterr().out


def test_manager_list_bookings_and_report(environment: CinemaEnvironment, capsys) -> None:
    storage = environment.storage()
    movie = storage.movie_repository.create(
        NewMovie("Dune", 120, "Description", Genre.DRAMA, 40)
    )
    show = storage.show_repository.create_many([
        MovieShowDraft(movie.movie_id, 1, datetime(2026, 9, 1, 18, tzinfo=CINEMA_TIMEZONE),
            40)
    ])[0]
    user = storage.user_repository.create(
        NewUser(
            "auth0|dana",
            "Dana Cohen",
            "0501234567",
            "dana@example.com",
        )
    )
    booking, rows = storage.booking_repository.add(
        BookingRequest(user.user_id, show.show_id, (1, 2))
    )
    _, halls, seats, movies, shows = storage.load_catalog()

    manager_cli.list_bookings([], [], seats, shows, movies, halls)
    assert "No bookings" in capsys.readouterr().out

    manager_cli.list_bookings([booking], rows, seats, shows, movies, halls)
    assert "80 NIS" in capsys.readouterr().out

    manager_cli.print_report(storage)
    out = capsys.readouterr().out
    assert "Movies: 1" in out
    assert "Total booked seats: 2" in out


def test_error_handling_wrapper(monkeypatch, capsys) -> None:
    from cinema.cli.error_handling import run_cli_safely
    from cinema.exceptions import StorageError

    with pytest.raises(SystemExit):
        run_cli_safely(lambda: (_ for _ in ()).throw(StorageError("disk")))
    assert "Application error: disk" in capsys.readouterr().out
