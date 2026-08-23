"""Administrative service for a cinema."""

from datetime import date

from cinema.exceptions import NotEnoughScheduleSlotsError
from cinema.models import Cinema, Genre, Hall, Movie, MovieShow


DEFAULT_SHOWS_PER_HALL = 3
DEFAULT_TICKET_PRICE = 42


class CinemaManager:
    """Perform administrative operations reserved for the cinema manager."""

    def __init__(self, cinema: Cinema) -> None:
        """Create a manager for one cinema."""
        self._cinema = cinema
        self._halls_by_number: dict[int, Hall] = {
            hall.hall_number: hall
            for hall in cinema.halls
        }
        self._next_movie_id = max(
            (movie.movie_id for movie in cinema.movies),
            default=0,
        ) + 1
        self._next_show_id = max(
            (
                show.show_id
                for hall in cinema.halls
                for show in hall.schedule.shows
            ),
            default=0,
        ) + 1

    def add_movie(
        self,
        title: str,
        duration_minutes: int,
        description: str,
        genre: Genre,
        ticket_price: int = DEFAULT_TICKET_PRICE,
    ) -> Movie:
        """Create a movie and add it to the cinema catalog."""
        movie = Movie(
            movie_id=self._next_movie_id,
            title=title,
            duration_minutes=duration_minutes,
            description=description,
            genre=genre,
            ticket_price=ticket_price,
        )
        self._cinema.movies.append(movie)
        self._next_movie_id += 1
        return movie

    def schedule_movie(
        self,
        movie: Movie,
        screening_date: date,
        shows_per_hall: int = DEFAULT_SHOWS_PER_HALL,
    ) -> tuple[MovieShow, ...]:
        """Schedule a movie several times in every cinema hall.

        The operation is atomic: all halls are checked before any show is added.

        Raises:
            ValueError: If the movie is unknown or an argument is invalid.
            NotEnoughScheduleSlotsError: If any hall lacks enough free slots.
        """
        if movie not in self._cinema.movies:
            raise ValueError("Movie must belong to the cinema catalog")

        if shows_per_hall <= 0:
            raise ValueError("Shows per hall must be positive")

        planned_shows: list[MovieShow] = []
        next_show_id = self._next_show_id

        for hall in self._cinema.halls:
            available_times = hall.schedule.find_available_start_times(
                movie=movie,
                screening_date=screening_date,
                count=shows_per_hall,
            )

            if len(available_times) < shows_per_hall:
                raise NotEnoughScheduleSlotsError(
                    f"Hall {hall.hall_number} does not have "
                    f"{shows_per_hall} available slots"
                )

            for start_time in available_times:
                planned_shows.append(
                    MovieShow(
                        show_id=next_show_id,
                        movie=movie,
                        hall_number=hall.hall_number,
                        start_time=start_time,
                        ticket_price=movie.ticket_price,
                    )
                )
                next_show_id += 1

        for show in planned_shows:
            self._find_hall(show.hall_number).schedule.add_show(show)

        self._next_show_id = next_show_id
        return tuple(planned_shows)

    def _find_hall(self, hall_number: int) -> Hall:
        """Return a hall by number.

        Raises:
            ValueError: If the cinema does not contain the requested hall.
        """
        try:
            return self._halls_by_number[hall_number]
        except KeyError as error:
            raise ValueError(f"Hall {hall_number} does not exist") from error
