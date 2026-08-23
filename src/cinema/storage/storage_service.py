"""Coordinator for loading and saving application state."""

from cinema.models import Booking, Cinema
from cinema.storage.booking_repository import BookingRepository
from cinema.storage.cinema_config_repository import CinemaConfigRepository
from cinema.storage.movie_repository import MovieRepository
from cinema.storage.show_repository import ShowRepository


class StorageService:
    """Coordinate the separate JSON repositories."""

    def __init__(self) -> None:
        """Create the storage coordinator."""
        self.config_repository = CinemaConfigRepository()
        self.movie_repository = MovieRepository()
        self.show_repository = ShowRepository()
        self.booking_repository = BookingRepository()

    def load(self) -> tuple[Cinema, list[Booking]]:
        """Load all persisted application state in dependency order."""
        cinema = self.config_repository.load()
        movies = self.movie_repository.load()
        cinema.movies.extend(movies)
        self.show_repository.load(cinema, movies)
        bookings = self.booking_repository.load(cinema)
        return cinema, bookings

    def save(
        self,
        cinema: Cinema,
        bookings: tuple[Booking, ...] | list[Booking],
    ) -> None:
        """Persist all state through the dedicated repositories."""
        self.config_repository.save(cinema)
        self.movie_repository.save(cinema.movies)
        self.show_repository.save(cinema)
        self.booking_repository.save(bookings)
