"""Central runtime paths for cinema data, logs, and application locks."""

import os
from pathlib import Path

from platformdirs import user_data_path, user_log_path

from cinema.storage.schema import SCHEMA_VERSION

APP_NAME = "CinemaCity"


def _runtime_path(environment_name: str, default_path: Path) -> Path:
    configured = os.environ.get(environment_name)
    return (
        Path(configured).expanduser().resolve()
        if configured
        else default_path.resolve()
    )


DATA_DIR = _runtime_path(
    "CINEMA_DATA_DIR",
    user_data_path(APP_NAME, appauthor=False),
)
LOG_DIR = _runtime_path(
    "CINEMA_LOG_DIR",
    user_log_path(APP_NAME, appauthor=False),
)

CONFIG_FILE = DATA_DIR / "cinema_config.json"
MOVIES_FILE = DATA_DIR / "movies.json"
SHOWS_FILE = DATA_DIR / "shows.json"
BOOKINGS_FILE = DATA_DIR / "bookings.json"
USERS_FILE = DATA_DIR / "users.json"
STATE_LOCK_FILE = DATA_DIR / ".cinema_state.lock"
LOG_FILE = LOG_DIR / "cinema.log"


def bootstrap_data_directory() -> None:
    """Create the complete current-schema data set when the data directory is absent."""
    if DATA_DIR.exists():
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    CONFIG_FILE.write_text(
        '{\n'
        f'  "schema_version": {SCHEMA_VERSION},\n'
        '  "cinema": {"cinema_id": 1, "name": "Cinema City"},\n'
        '  "halls": [\n'
        '    {"hall_id": 1, "hall_name": "Hall 1", '
        '"rows": 20, "seats_per_row": 20},\n'
        '    {"hall_id": 2, "hall_name": "Hall 2", '
        '"rows": 20, "seats_per_row": 20},\n'
        '    {"hall_id": 3, "hall_name": "Hall 3", '
        '"rows": 20, "seats_per_row": 20}\n'
        '  ]\n'
        '}\n',
        encoding="utf-8",
    )
    MOVIES_FILE.write_text(
        f'{{\n  "schema_version": {SCHEMA_VERSION},\n'
        '  "last_movie_id": 0,\n  "movies": []\n}\n',
        encoding="utf-8",
    )
    SHOWS_FILE.write_text(
        f'{{\n  "schema_version": {SCHEMA_VERSION},\n'
        '  "last_show_id": 0,\n  "shows": []\n}\n',
        encoding="utf-8",
    )
    BOOKINGS_FILE.write_text(
        f'{{\n  "schema_version": {SCHEMA_VERSION},\n'
        '  "last_booking_id": 0,\n'
        '  "bookings": [],\n'
        '  "booking_seats": []\n}\n',
        encoding="utf-8",
    )
    USERS_FILE.write_text(
        f'{{\n  "schema_version": {SCHEMA_VERSION},\n'
        '  "last_user_id": 0,\n  "users": []\n}\n',
        encoding="utf-8",
    )


def ensure_log_directory() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
