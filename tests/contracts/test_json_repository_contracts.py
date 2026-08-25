"""Run the reusable repository contracts against the JSON implementation."""

import pytest

from cinema.storage import (
    JsonBookingRepository,
    JsonCinemaConfigRepository,
    JsonMovieRepository,
    JsonShowRepository,
    JsonUserRepository,
)
from tests.conftest import CinemaEnvironment
from tests.contracts.repository_contracts import (
    BookingRepositoryContract,
    CinemaConfigRepositoryContract,
    MovieRepositoryContract,
    ShowRepositoryContract,
    UserRepositoryContract,
)


class TestJsonCinemaConfigRepositoryContract(CinemaConfigRepositoryContract):
    @pytest.fixture
    def config_repository(self, environment: CinemaEnvironment):
        return JsonCinemaConfigRepository(environment.config_file)


class TestJsonMovieRepositoryContract(MovieRepositoryContract):
    @pytest.fixture
    def movie_repository(self, environment: CinemaEnvironment):
        return JsonMovieRepository(
            environment.movies_file,
            environment.state_lock_file,
        )


class TestJsonUserRepositoryContract(UserRepositoryContract):
    @pytest.fixture
    def user_repository(self, environment: CinemaEnvironment):
        return JsonUserRepository(environment.users_file)


class TestJsonShowRepositoryContract(ShowRepositoryContract):
    @pytest.fixture
    def show_repository(self, environment: CinemaEnvironment):
        return JsonShowRepository(
            environment.shows_file,
            environment.state_lock_file,
        )


class TestJsonBookingRepositoryContract(BookingRepositoryContract):
    @pytest.fixture
    def booking_repository(self, environment: CinemaEnvironment):
        return JsonBookingRepository(environment.bookings_file)
