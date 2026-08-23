"""Hall schedule domain model."""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from cinema.models.movie import Movie
from cinema.models.movie_show import MovieShow


DEFAULT_OPENING_TIME = time(hour=10)
DEFAULT_CLOSING_TIME = time(hour=23, minute=59)


@dataclass(slots=True)
class HallSchedule:
    """Manage all scheduled movie shows for one cinema hall."""

    hall_number: int
    opening_time: time = DEFAULT_OPENING_TIME
    closing_time: time = DEFAULT_CLOSING_TIME
    _shows: list[MovieShow] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        """Validate schedule configuration.

        Raises:
            ValueError: If the hall number is invalid or opening hours are reversed.
        """
        if self.hall_number <= 0:
            raise ValueError("Hall number must be positive")

        if self.opening_time >= self.closing_time:
            raise ValueError("Opening time must be earlier than closing time")

    @property
    def shows(self) -> tuple[MovieShow, ...]:
        """Return scheduled shows in chronological order."""
        return tuple(sorted(self._shows, key=lambda show: show.start_time))

    def add_show(self, show: MovieShow) -> None:
        """Add a show when it belongs to this hall and has no conflict.

        Raises:
            ValueError: If the show belongs to another hall or overlaps another show.
        """
        if show.hall_number != self.hall_number:
            raise ValueError("Movie show belongs to another hall")

        if self.has_conflict(show):
            raise ValueError("Movie show conflicts with an existing show")

        self._shows.append(show)

    def has_conflict(self, new_show: MovieShow) -> bool:
        """Return whether a movie show overlaps an existing show."""
        return self._time_range_has_conflict(
            start_time=new_show.start_time,
            end_time=new_show.end_time,
        )

    def find_available_start_times(
        self,
        movie: Movie,
        screening_date: date,
        count: int,
        interval_minutes: int = 30,
    ) -> tuple[datetime, ...]:
        """Return the earliest non-overlapping start times available for a movie.

        Candidate start times are checked at a fixed interval. Times already
        selected by this method are treated as occupied while finding later
        results, preventing the method from returning overlapping suggestions.

        Raises:
            ValueError: If count or interval_minutes is not positive.
        """
        if count <= 0:
            raise ValueError("Requested number of start times must be positive")

        if interval_minutes <= 0:
            raise ValueError("Interval must be positive")

        current_time = datetime.combine(screening_date, self.opening_time)
        closing_datetime = datetime.combine(screening_date, self.closing_time)
        movie_duration = timedelta(minutes=movie.duration_minutes)
        interval = timedelta(minutes=interval_minutes)

        available_times: list[datetime] = []
        planned_ranges: list[tuple[datetime, datetime]] = []

        while current_time + movie_duration <= closing_datetime:
            candidate_end = current_time + movie_duration

            conflicts_with_schedule = self._time_range_has_conflict(
                current_time,
                candidate_end,
            )
            conflicts_with_planned = any(
                self._time_ranges_overlap(
                    current_time,
                    candidate_end,
                    planned_start,
                    planned_end,
                )
                for planned_start, planned_end in planned_ranges
            )

            if not conflicts_with_schedule and not conflicts_with_planned:
                available_times.append(current_time)
                planned_ranges.append((current_time, candidate_end))

                if len(available_times) == count:
                    break

            current_time += interval

        return tuple(available_times)

    def _time_range_has_conflict(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> bool:
        """Return whether a time range overlaps a scheduled movie show."""
        return any(
            self._time_ranges_overlap(
                start_time,
                end_time,
                show.start_time,
                show.end_time,
            )
            for show in self._shows
        )

    @staticmethod
    def _time_ranges_overlap(
        first_start: datetime,
        first_end: datetime,
        second_start: datetime,
        second_end: datetime,
    ) -> bool:
        """Return whether two half-open time ranges overlap."""
        return first_start < second_end and second_start < first_end
