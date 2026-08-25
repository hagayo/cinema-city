"""Integration tests across JSON repositories and stateless services."""

from datetime import date, timedelta

import pytest

from cinema.exceptions import SeatAlreadyBookedError
from cinema.models import (
    Genre,
    NewMovie,
    NewUser,
    customer_auth_context,
    manager_auth_context,
)
from cinema.services import BookingService, CinemaManager, SchedulingService
from tests.conftest import CinemaEnvironment


def build_manager(
    environment: CinemaEnvironment,
) -> tuple[object, CinemaManager]:
    storage = environment.storage()
    scheduler = SchedulingService(
        storage.config_repository,
        storage.movie_repository,
        storage.show_repository,
    )
    return storage, CinemaManager(storage.movie_repository, scheduler)


def add_demo_movie(manager: CinemaManager):
    actor = manager_auth_context("auth0|manager")
    movie = manager.add_movie(
        actor,
        NewMovie("Dune", 120, "Description", Genre.DRAMA, 40),
    )
    return actor, movie


def test_full_booking_restart_and_cancellation_lifecycle(
    environment: CinemaEnvironment,
) -> None:
    storage, manager = build_manager(environment)
    actor, movie = add_demo_movie(manager)
    shows = manager.schedule_movie(
        actor,
        movie,
        date(2026, 9, 1),
        shows_per_hall=1,
    )
    show = next(item for item in shows if item.hall_id == 1)

    _, halls, seats, movies, persisted_shows = storage.load_catalog()
    assert len(halls) == 3
    assert len(seats) == 36
    assert movies == [movie]
    assert len(persisted_shows) == 3

    user = storage.user_repository.create(
        NewUser(
            "auth0|dana",
            "Dana Cohen",
            "0501234567",
            "dana@example.com",
        )
    )
    request = BookingService.prepare_booking(
        actor=customer_auth_context(user.auth_subject),
        user=user,
        show=show,
        requested_seats=((1, 1), (1, 2)),
        seats=seats,
    )
    booking, rows = storage.booking_repository.add(request)
    assert booking.show_id == show.show_id
    assert [row.seat_id for row in rows] == [1, 2]

    restarted = environment.storage()
    (
        cinema,
        restarted_halls,
        restarted_seats,
        restarted_movies,
        restarted_shows,
        restarted_users,
        restarted_bookings,
        restarted_rows,
    ) = restarted.load()

    assert cinema.cinema_id == 1
    assert restarted_halls == halls
    assert restarted_seats == seats
    assert restarted_movies == [movie]
    assert restarted_users == [user]
    assert restarted_bookings == [booking]
    assert restarted_rows == rows

    reloaded_show = next(
        item for item in restarted_shows if item.show_id == booking.show_id
    )
    BookingService.validate_cancellation(
        customer_auth_context(user.auth_subject),
        user,
        booking,
        reloaded_show,
        reloaded_show.start_time - timedelta(hours=2),
    )
    restarted.booking_repository.delete(booking.booking_id, user.user_id)

    assert restarted.load_bookings(
        restarted_shows,
        restarted_seats,
        restarted_users,
    ) == ([], [])


def test_second_user_cannot_take_reserved_seat(
    environment: CinemaEnvironment,
) -> None:
    storage, manager = build_manager(environment)
    actor, movie = add_demo_movie(manager)
    show = manager.schedule_movie(actor, movie, date(2026, 9, 1), 1)[0]
    _, _, seats, _, shows = storage.load_catalog()

    first = storage.user_repository.create(
        NewUser(
            "auth0|dana",
            "Dana Cohen",
            "0501234567",
            "dana@example.com",
        )
    )
    second = storage.user_repository.create(
        NewUser(
            "auth0|avi",
            "Avi Levi",
            "0521234567",
            "avi@example.com",
        )
    )

    first_request = BookingService.prepare_booking(
        actor=customer_auth_context(first.auth_subject),
        user=first,
        show=show,
        requested_seats=((1, 1),),
        seats=seats,
    )
    storage.booking_repository.add(first_request)

    bookings, rows = storage.load_bookings(
        shows,
        seats,
        storage.user_repository.load(),
    )

    with pytest.raises(SeatAlreadyBookedError):
        BookingService.prepare_booking(
            actor=customer_auth_context(second.auth_subject),
            user=second,
            show=show,
            requested_seats=((1, 1),),
            seats=seats,
            bookings=bookings,
            booking_seats=rows,
        )


def test_cancelled_seat_can_be_rebooked(
    environment: CinemaEnvironment,
) -> None:
    storage, manager = build_manager(environment)
    actor, movie = add_demo_movie(manager)
    show = manager.schedule_movie(actor, movie, date(2026, 9, 1), 1)[0]
    _, _, seats, _, shows = storage.load_catalog()

    first = storage.user_repository.create(
        NewUser(
            "auth0|dana",
            "Dana Cohen",
            "0501234567",
            "dana@example.com",
        )
    )

    request = BookingService.prepare_booking(
        actor=customer_auth_context(first.auth_subject),
        user=first,
        show=show,
        requested_seats=((1, 1),),
        seats=seats,
    )
    booking, _ = storage.booking_repository.add(request)
    storage.booking_repository.delete(booking.booking_id, first.user_id)

    second = storage.user_repository.create(
        NewUser(
            "auth0|avi",
            "Avi Levi",
            "0521234567",
            "avi@example.com",
        )
    )
    bookings, rows = storage.load_bookings(
        shows,
        seats,
        storage.user_repository.load(),
    )

    new_request = BookingService.prepare_booking(
        actor=customer_auth_context(second.auth_subject),
        user=second,
        show=show,
        requested_seats=((1, 1),),
        seats=seats,
        bookings=bookings,
        booking_seats=rows,
    )
    second_booking, _ = storage.booking_repository.add(new_request)

    assert second_booking.booking_id == 2
