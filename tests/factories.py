"""Factories used by multiple unit tests."""

from datetime import datetime

from cinema.models import Genre, Hall, Movie, MovieShow


def make_movie(
    movie_id: int = 1,
    title: str = "Back to the Future",
    duration_minutes: int = 120,
    genre: Genre = Genre.DRAMA,
) -> Movie:
    """Create a movie suitable for unit tests."""
    return Movie(
        movie_id=movie_id,
        title=title,
        duration_minutes=duration_minutes,
        description="A short movie description.",
        genre=genre,
    )


def make_show(
    show_id: int = 1,
    hall_number: int = 1,
    hour: int = 18,
    minute: int = 0,
    duration_minutes: int = 120,
    ticket_price: int = 42,
    genre: Genre = Genre.DRAMA,
) -> MovieShow:
    """Create a movie show suitable for unit tests."""
    return MovieShow(
        show_id=show_id,
        movie=make_movie(
            duration_minutes=duration_minutes,
            genre=genre,
        ),
        hall_number=hall_number,
        start_time=datetime(2026, 8, 23, hour, minute),
        ticket_price=ticket_price,
    )


def make_small_hall(hall_number: int = 1) -> Hall:
    """Create a small hall for focused unit tests."""
    return Hall.create_default(
        hall_number=hall_number,
        rows=2,
        seats_per_row=2,
    )
