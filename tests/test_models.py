"""Unit tests for core domain models."""

from datetime import date, datetime, time

import pytest

from cinema.models import Genre, Booking, Cinema, Hall, HallSchedule, Movie, MovieShow, Seat
from tests.factories import make_movie, make_show


def test_default_cinema_contains_three_halls() -> None:
    """Default cinema creates three halls."""
    cinema = Cinema.create_default("Cinema City")
    assert len(cinema.halls) == 3


def test_default_hall_contains_four_hundred_seats() -> None:
    """Default hall contains twenty rows with twenty seats each."""
    cinema = Cinema.create_default("Cinema City")
    assert len(cinema.halls[0].seats) == 400


def test_movie_rejects_non_positive_id() -> None:
    """Movie IDs must be positive."""
    with pytest.raises(ValueError, match="Movie ID"):
        Movie(0, "Dune", 166, "Description", Genre.DRAMA)


def test_movie_rejects_empty_title() -> None:
    """Movie titles cannot be empty."""
    with pytest.raises(ValueError, match="title"):
        Movie(1, " ", 166, "Description", Genre.DRAMA)


def test_movie_rejects_non_positive_duration() -> None:
    """Movie duration must be positive."""
    with pytest.raises(ValueError, match="duration"):
        Movie(1, "Dune", 0, "Description", Genre.DRAMA)


def test_movie_description_has_maximum_length() -> None:
    """Movie description cannot exceed the configured maximum length."""
    with pytest.raises(ValueError, match="description"):
        Movie(1, "Dune", 166, "x" * 301, Genre.DRAMA)


def test_seat_rejects_invalid_position() -> None:
    """Seat coordinates must be positive."""
    with pytest.raises(ValueError, match="row"):
        Seat(row=0, seat_number=1)


def test_hall_rejects_duplicate_seats() -> None:
    """A hall cannot contain the same physical seat twice."""
    seat = Seat(row=1, seat_number=1)
    with pytest.raises(ValueError, match="duplicate"):
        Hall(hall_number=1, seats=(seat, seat))


def test_movie_show_rejects_negative_ticket_price() -> None:
    """Ticket prices cannot be negative."""
    with pytest.raises(ValueError, match="price"):
        MovieShow(
            show_id=1,
            movie=make_movie(),
            hall_number=1,
            start_time=datetime(2026, 8, 23, 18, 0),
            ticket_price=-1,
        )


def test_ticket_price_is_integer_shekels() -> None:
    """Ticket prices and booking totals are whole shekel integers."""
    show = make_show(ticket_price=42)
    booking = Booking(
        booking_id=1,
        show=show,
        seats=(Seat(1, 1), Seat(1, 2)),
    )

    assert isinstance(show.ticket_price, int)
    assert booking.total_price == 84
    assert isinstance(booking.total_price, int)


def test_schedule_rejects_invalid_opening_hours() -> None:
    """Opening time must be earlier than closing time."""
    with pytest.raises(ValueError, match="Opening"):
        HallSchedule(
            hall_number=1,
            opening_time=time(20, 0),
            closing_time=time(10, 0),
        )


def test_hall_schedule_detects_overlap() -> None:
    """Hall schedule rejects overlapping movie shows."""
    schedule = HallSchedule(hall_number=1)
    schedule.add_show(make_show(show_id=1, hour=18, duration_minutes=120))

    second_show = make_show(show_id=2, hour=19, duration_minutes=90)
    assert schedule.has_conflict(second_show) is True


def test_hall_schedule_allows_adjacent_show() -> None:
    """A show may start exactly when the previous movie ends."""
    schedule = HallSchedule(hall_number=1)
    schedule.add_show(make_show(show_id=1, hour=18, duration_minutes=120))

    second_show = make_show(show_id=2, hour=20, duration_minutes=90)
    assert schedule.has_conflict(second_show) is False


def test_find_three_available_start_times_without_overlap() -> None:
    """Suggested screening times do not overlap one another."""
    schedule = HallSchedule(hall_number=1)
    movie = make_movie(duration_minutes=90)

    result = schedule.find_available_start_times(
        movie=movie,
        screening_date=date(2026, 8, 23),
        count=3,
    )

    assert result == (
        datetime(2026, 8, 23, 10, 0),
        datetime(2026, 8, 23, 11, 30),
        datetime(2026, 8, 23, 13, 0),
    )


@pytest.mark.parametrize("count", [0, -1])
def test_find_available_start_times_rejects_invalid_count(count: int) -> None:
    """Requested number of screening times must be positive."""
    schedule = HallSchedule(hall_number=1)

    with pytest.raises(ValueError, match="number"):
        schedule.find_available_start_times(
            movie=make_movie(),
            screening_date=date(2026, 8, 23),
            count=count,
        )


@pytest.mark.parametrize("interval", [0, -30])
def test_find_available_start_times_rejects_invalid_interval(interval: int) -> None:
    """Search interval must be positive."""
    schedule = HallSchedule(hall_number=1)

    with pytest.raises(ValueError, match="Interval"):
        schedule.find_available_start_times(
            movie=make_movie(),
            screening_date=date(2026, 8, 23),
            count=1,
            interval_minutes=interval,
        )
