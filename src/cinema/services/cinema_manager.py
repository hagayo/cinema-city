"""Stateless administrative service for a cinema."""

from datetime import date

from cinema.exceptions import MovieAlreadyExistsError
from cinema.models import (
    AuthContext,
    Movie,
    MovieShow,
    NewMovie,
    Permission,
)
from cinema.services.scheduling_service import (
    DEFAULT_SHOWS_PER_HALL,
    SchedulingService,
)
from cinema.storage.interfaces import MovieRepository


class CinemaManager:
    """Perform authorized manager operations through repository abstractions."""

    def __init__(
        self,
        movie_repository: MovieRepository,
        scheduling_service: SchedulingService,
    ) -> None:
        self._movie_repository = movie_repository
        self._scheduling_service = scheduling_service

    def add_movie(
        self,
        actor: AuthContext,
        new_movie: NewMovie,
    ) -> Movie:
        """Authorize, validate title uniqueness, and persist a new movie."""
        actor.require(Permission.MANAGE_MOVIES)

        normalized_title = new_movie.title.strip().casefold()
        if any(
            movie.title.strip().casefold() == normalized_title
            for movie in self._movie_repository.load()
        ):
            raise MovieAlreadyExistsError(
                f'Movie "{new_movie.title.strip()}" already exists'
            )

        return self._movie_repository.create(new_movie)

    def schedule_movie(
        self,
        actor: AuthContext,
        movie: Movie,
        screening_date: date,
        shows_per_hall: int = DEFAULT_SHOWS_PER_HALL,
    ) -> tuple[MovieShow, ...]:
        """Authorize and schedule a persisted movie in every configured hall."""
        actor.require(Permission.MANAGE_SCHEDULE)

        return self._scheduling_service.schedule_movie_for_all_halls(
            movie=movie,
            screening_date=screening_date,
            shows_per_hall=shows_per_hall,
        )
