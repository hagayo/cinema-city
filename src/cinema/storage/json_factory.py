"""Composition root for the current JSON persistence implementation."""

from pathlib import Path

from cinema.storage.app_paths import (
    BOOKINGS_FILE,
    CONFIG_FILE,
    MOVIES_FILE,
    SHOWS_FILE,
    STATE_LOCK_FILE,
    USERS_FILE,
    bootstrap_data_directory,
)
from cinema.storage.json_booking_repository import JsonBookingRepository
from cinema.storage.json_cinema_config_repository import JsonCinemaConfigRepository
from cinema.storage.json_movie_repository import JsonMovieRepository
from cinema.storage.json_show_repository import JsonShowRepository
from cinema.storage.json_user_repository import JsonUserRepository
from cinema.storage.storage_service import StorageService


def create_json_storage_service(
    *,
    config_file: Path = CONFIG_FILE,
    movies_file: Path = MOVIES_FILE,
    shows_file: Path = SHOWS_FILE,
    bookings_file: Path = BOOKINGS_FILE,
    users_file: Path = USERS_FILE,
    state_lock_file: Path = STATE_LOCK_FILE,
    bootstrap: bool = True,
) -> StorageService:
    """Build the application with JSON repositories at one composition boundary."""
    if bootstrap:
        bootstrap_data_directory()

    return StorageService(
        config_repository=JsonCinemaConfigRepository(config_file),
        movie_repository=JsonMovieRepository(movies_file, state_lock_file),
        show_repository=JsonShowRepository(shows_file, state_lock_file),
        booking_repository=JsonBookingRepository(bookings_file),
        user_repository=JsonUserRepository(users_file),
    )
