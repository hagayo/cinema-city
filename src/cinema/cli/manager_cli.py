"""Interactive command-line interface for the cinema manager."""

from datetime import date

from cinema.cli.input_helpers import read_genre
from cinema.models import Booking, Cinema, Movie
from cinema.services import CinemaManager
from cinema.services.cinema_manager import DEFAULT_TICKET_PRICE
from cinema.storage import StorageService

MAX_TICKET_PRICE = 99


def read_positive_int(prompt: str) -> int:
    """Read a positive integer from standard input."""
    while True:
        raw_value = input(prompt).strip()

        try:
            value = int(raw_value)
        except ValueError:
            print("Please enter a whole number.")
            continue

        if value <= 0:
            print("Please enter a positive number.")
            continue

        return value


def read_ticket_price(prompt: str = "Ticket price [40 NIS]: ") -> int:
    """Read a ticket price between 1 and 99, or use 40 when left empty."""
    while True:
        raw_value = input(prompt).strip()

        if not raw_value:
            return DEFAULT_TICKET_PRICE

        try:
            value = int(raw_value)
        except ValueError:
            print("Please enter a whole number between 1 and 99, or press Enter for 40.")
            continue

        if 1 <= value <= MAX_TICKET_PRICE:
            return value

        print("Ticket price must be between 1 and 99 NIS.")


def read_non_empty_text(prompt: str) -> str:
    """Read non-empty text from standard input."""
    while True:
        value = input(prompt).strip()

        if value:
            return value

        print("Value cannot be empty.")


def find_movie_by_id_or_title(
    movies: list[Movie],
    movie_reference: str,
) -> Movie | None:
    """Find a movie by numeric ID or exact title."""
    normalized_reference = movie_reference.strip()

    if normalized_reference.isdigit():
        movie_id = int(normalized_reference)
        return next(
            (movie for movie in movies if movie.movie_id == movie_id),
            None,
        )

    normalized_title = normalized_reference.casefold()
    return next(
        (movie for movie in movies if movie.title.casefold() == normalized_title),
        None,
    )


def add_movie_interactively(manager: CinemaManager) -> None:
    """Collect movie data and add it to the cinema catalog."""
    print("\nAdd a new movie")

    movie = manager.add_movie(
        title=read_non_empty_text("Movie title: "),
        duration_minutes=read_positive_int("Duration in minutes: "),
        description=read_non_empty_text("Short description: "),
        genre=read_genre(),
        ticket_price=read_ticket_price(),
    )
    print(f'Added movie #{movie.movie_id}: "{movie.title}"')


def schedule_movie_interactively(
    cinema: Cinema,
    manager: CinemaManager,
) -> None:
    """Choose an existing movie and schedule it in all cinema halls."""
    if not cinema.movies:
        print("No movies in catalog.")
        return

    movie = find_movie_by_id_or_title(
        cinema.movies,
        read_non_empty_text("Enter movie ID or exact title: "),
    )

    if movie is None:
        print("Movie not found.")
        return

    shows = manager.schedule_movie(
        movie=movie,
        screening_date=date.today(),
    )
    print(f'Scheduled {len(shows)} shows for "{movie.title}".')


def list_movies(cinema: Cinema) -> None:
    """Print all movies currently stored in the cinema catalog."""
    if not cinema.movies:
        print("No movies in catalog.")
        return

    for movie in cinema.movies:
        print(
            f"{movie.movie_id}. {movie.title} "
            f"({movie.duration_minutes} minutes, {movie.genre.value}, "
            f"{movie.ticket_price} NIS)"
        )


def list_shows_by_hall(cinema: Cinema) -> None:
    """Ask for a hall and print its scheduled shows ordered by start time."""
    hall_number = read_positive_int("Hall number: ")
    hall = next(
        (item for item in cinema.halls if item.hall_number == hall_number),
        None,
    )

    if hall is None:
        print(f"Hall {hall_number} does not exist.")
        return

    shows = sorted(hall.schedule.shows, key=lambda show: show.start_time)

    if not shows:
        print(f"No shows scheduled in hall {hall_number}.")
        return

    print(f"\nHall {hall_number} Shows")
    for show in shows:
        print(
            f"#{show.show_id} | {show.movie.title} | {show.movie.genre.value} | "
            f"{show.start_time:%Y-%m-%d %H:%M} - {show.end_time:%H:%M} | "
            f"{show.ticket_price} NIS"
        )


def list_bookings(bookings: list[Booking]) -> None:
    """Print all customer bookings ordered by booking ID."""
    if not bookings:
        print("No bookings.")
        return

    print("\nBookings")
    for booking in sorted(bookings, key=lambda item: item.booking_id):
        seats = ", ".join(f"R{seat.row}-S{seat.seat_number}" for seat in booking.seats)
        print(
            f"#{booking.booking_id} | {booking.show.movie.title} | "
            f"Show #{booking.show.show_id} | Hall {booking.show.hall_number} | "
            f"{booking.show.start_time:%Y-%m-%d %H:%M} | "
            f"Seats: {seats} | Total: {booking.total_price} NIS"
        )


def run_manager_cli() -> None:
    """Start the persistent cinema manager CLI."""
    repository = StorageService()
    cinema, bookings = repository.load()
    manager = CinemaManager(cinema)

    while True:
        print(
            "\nCinema Manager\n"
            "1. Add movie\n"
            "2. Schedule movie\n"
            "3. List movies\n"
            "4. List shows by hall\n"
            "5. List bookings\n"
            "6. Exit"
        )

        choice = input("Choose an option: ").strip()

        if choice == "1":
            add_movie_interactively(manager)
            repository.save(cinema, bookings)
        elif choice == "2":
            schedule_movie_interactively(cinema, manager)
            repository.save(cinema, bookings)
        elif choice == "3":
            list_movies(cinema)
        elif choice == "4":
            list_shows_by_hall(cinema)
        elif choice == "5":
            list_bookings(bookings)
        elif choice == "6":
            repository.save(cinema, bookings)
            print("Goodbye.")
            return
        else:
            print("Unknown option.")


def main() -> None:
    """Run the cinema manager CLI."""
    run_manager_cli()


if __name__ == "__main__":
    main()
