"""Tests for the separated JSON repositories."""

from datetime import date

from cinema.models import Cinema, Genre
from cinema.services import BookingService, CinemaManager
from cinema.storage import (
    BookingRepository,
    CinemaConfigRepository,
    MovieRepository,
    ShowRepository,
)


def test_config_repository_persists_hall_layout(tmp_path) -> None:
    """Cinema configuration survives a save/load cycle."""
    repository = CinemaConfigRepository(tmp_path / "config.json")
    cinema = Cinema.create_default("Cinema City")

    repository.save(cinema)
    loaded = repository.load()

    assert loaded.name == "Cinema City"
    assert len(loaded.halls) == 3
    assert len(loaded.halls[0].seats) == 400


def test_movie_repository_persists_movies(tmp_path) -> None:
    """Movie catalog survives a save/load cycle."""
    repository = MovieRepository(tmp_path / "movies.json")
    cinema = Cinema.create_default("Cinema City")
    manager = CinemaManager(cinema)
    movie = manager.add_movie("Dune", 120, "Science fiction.", Genre.DRAMA)

    repository.save(cinema.movies)
    loaded = repository.load()

    assert loaded == [movie]
    assert loaded[0].genre == Genre.DRAMA


def test_show_repository_persists_shows(tmp_path) -> None:
    """Scheduled shows survive a save/load cycle."""
    config_repository = CinemaConfigRepository(tmp_path / "config.json")
    movie_repository = MovieRepository(tmp_path / "movies.json")
    show_repository = ShowRepository(tmp_path / "shows.json")

    cinema = Cinema.create_default("Cinema City")
    manager = CinemaManager(cinema)
    movie = manager.add_movie("Dune", 120, "Science fiction.", Genre.DRAMA)
    manager.schedule_movie(movie, date(2026, 8, 23), shows_per_hall=1)

    config_repository.save(cinema)
    movie_repository.save(cinema.movies)
    show_repository.save(cinema)

    loaded_cinema = config_repository.load()
    loaded_movies = movie_repository.load()
    loaded_cinema.movies.extend(loaded_movies)
    show_repository.load(loaded_cinema, loaded_movies)

    assert sum(
        len(hall.schedule.shows)
        for hall in loaded_cinema.halls
    ) == 3


def test_booking_repository_persists_bookings(tmp_path) -> None:
    """Bookings survive a save/load cycle."""
    booking_repository = BookingRepository(tmp_path / "bookings.json")

    cinema = Cinema.create_default("Cinema City")
    manager = CinemaManager(cinema)
    movie = manager.add_movie("Dune", 120, "Science fiction.", Genre.DRAMA)
    show = manager.schedule_movie(
        movie,
        date(2026, 8, 23),
        shows_per_hall=1,
    )[0]

    hall = cinema.halls[show.hall_number - 1]
    service = BookingService()
    service.create_booking(
        booking_id=1,
        hall=hall,
        show=show,
        requested_seats=((1, 1),),
    )

    booking_repository.save(service.bookings)
    loaded = booking_repository.load(cinema)

    assert len(loaded) == 1
    assert loaded[0].show.show_id == show.show_id
