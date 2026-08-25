"""Customer CLI E2E test using real JSON persistence."""

from datetime import date, datetime

from cinema.cli import customer_cli
from cinema.models import Genre, NewMovie, manager_auth_context
from cinema.services import CinemaManager, SchedulingService
from cinema.time_utils import CINEMA_TIMEZONE
from tests.conftest import CinemaEnvironment


def test_customer_cli_booking_then_restart(
    environment: CinemaEnvironment,
    monkeypatch,
    capsys,
) -> None:
    storage = environment.storage()
    scheduler = SchedulingService(
        storage.config_repository,
        storage.movie_repository,
        storage.show_repository,
    )
    manager = CinemaManager(storage.movie_repository, scheduler)
    manager_actor = manager_auth_context("auth0|manager")

    movie = manager.add_movie(
        manager_actor,
        NewMovie("Dune", 120, "Description", Genre.DRAMA, 40),
    )
    show = manager.schedule_movie(
        manager_actor,
        movie,
        date(2026, 9, 1),
        1,
    )[0]

    monkeypatch.setattr(
        customer_cli,
        "create_json_storage_service",
        environment.storage,
    )
    monkeypatch.setattr(
        customer_cli,
        "local_now",
        lambda: datetime(2026, 9, 1, 8, tzinfo=CINEMA_TIMEZONE),
    )

    answers = iter(
        [
            "auth0|dana",
            "3",
            str(show.show_id),
            "Dana Cohen",
            "0501234567",
            "dana@example.com",
            "2",
            "1",
            "1",
            "5",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    customer_cli.run_customer_cli()
    assert "confirmed" in capsys.readouterr().out

    restarted = environment.storage()
    _, _, seats, _, shows = restarted.load_catalog()
    users = restarted.user_repository.load()
    bookings, rows = restarted.load_bookings(shows, seats, users)

    assert len(users) == 1
    assert users[0].auth_subject == "auth0|dana"
    assert len(bookings) == 1
    assert bookings[0].show_id == show.show_id
    assert len(rows) == 2
