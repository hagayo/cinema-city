"""Interactive command-line interface for cinema customers."""

from datetime import date, timedelta

from cinema.cli.input_helpers import read_genre
from cinema.models import Cinema, Genre, Hall, MovieShow
from cinema.services import BookingService
from cinema.storage import StorageService

WEEK_DAYS = 7


def get_upcoming_shows(
    cinema: Cinema,
    start_date: date,
) -> tuple[MovieShow, ...]:
    """Return all scheduled shows during the coming seven days."""
    end_date = start_date + timedelta(days=WEEK_DAYS)

    shows = [
        show
        for hall in cinema.halls
        for show in hall.schedule.shows
        if start_date <= show.start_time.date() < end_date
    ]
    return tuple(sorted(shows, key=lambda show: show.start_time))


def get_upcoming_shows_by_genre(
    cinema: Cinema,
    start_date: date,
    genre: Genre,
) -> tuple[MovieShow, ...]:
    """Return upcoming shows filtered by movie genre."""
    return tuple(
        show for show in get_upcoming_shows(cinema, start_date) if show.movie.genre == genre
    )


def find_show_by_id(cinema: Cinema, show_id: int) -> MovieShow | None:
    """Return a scheduled show by ID, or None when missing."""
    return next(
        (show for hall in cinema.halls for show in hall.schedule.shows if show.show_id == show_id),
        None,
    )


def find_hall_by_number(
    cinema: Cinema,
    hall_number: int,
) -> Hall | None:
    """Return a cinema hall by number, or None when missing."""
    return next(
        (hall for hall in cinema.halls if hall.hall_number == hall_number),
        None,
    )


def read_positive_int(prompt: str) -> int:
    """Read a positive integer from standard input."""
    while True:
        value = input(prompt).strip()

        try:
            number = int(value)
        except ValueError:
            print("Please enter a whole number.")
            continue

        if number <= 0:
            print("Please enter a positive number.")
            continue

        return number


def read_requested_seats() -> tuple[tuple[int, int], ...]:
    """Read one to five adjacent seat coordinates."""
    seat_count = read_positive_int("How many seats? (1-5): ")

    if seat_count > 5:
        raise ValueError("A booking can contain at most 5 seats")

    row = read_positive_int("Row: ")
    first_seat = read_positive_int("First seat number: ")

    return tuple((row, first_seat + offset) for offset in range(seat_count))


def print_shows(shows: tuple[MovieShow, ...]) -> None:
    """Print movie shows in a compact customer-friendly format."""
    for show in shows:
        print(
            f"{show.show_id}. {show.movie.title} | "
            f"{show.movie.genre.value} | "
            f"{show.start_time:%Y-%m-%d %H:%M} | "
            f"Hall {show.hall_number} | "
            f"{show.ticket_price} NIS"
        )


def list_upcoming_shows(cinema: Cinema) -> tuple[MovieShow, ...]:
    """Print and return shows scheduled for the coming week."""
    shows = get_upcoming_shows(cinema, date.today())

    if not shows:
        print("No shows are scheduled for the coming week.")
        return ()

    print_shows(shows)
    return shows


def list_upcoming_shows_by_genre(cinema: Cinema) -> None:
    """Print upcoming shows filtered by movie genre."""
    genre = read_genre()
    shows = get_upcoming_shows_by_genre(
        cinema=cinema,
        start_date=date.today(),
        genre=genre,
    )

    if not shows:
        print(f"No {genre.value} shows are scheduled for the coming week.")
        return

    print_shows(shows)


def book_show_interactively(
    cinema: Cinema,
    booking_service: BookingService,
    next_booking_id: int,
) -> int:
    """Create one customer booking and return the next booking ID."""
    if not list_upcoming_shows(cinema):
        return next_booking_id

    show = find_show_by_id(
        cinema,
        read_positive_int("Show ID: "),
    )

    if show is None:
        print("Show not found.")
        return next_booking_id

    hall = find_hall_by_number(cinema, show.hall_number)
    if hall is None:
        print("Hall not found.")
        return next_booking_id

    try:
        booking = booking_service.create_booking(
            booking_id=next_booking_id,
            hall=hall,
            show=show,
            requested_seats=read_requested_seats(),
        )
    except ValueError as error:
        print(error)
        return next_booking_id

    print(f"Booking #{booking.booking_id} confirmed. Total: {booking.total_price} NIS")
    return next_booking_id + 1


def run_customer_cli() -> None:
    """Start the persistent cinema customer CLI."""
    repository = StorageService()
    cinema, stored_bookings = repository.load()
    booking_service = BookingService(stored_bookings)
    next_booking_id = (
        max(
            (booking.booking_id for booking in stored_bookings),
            default=0,
        )
        + 1
    )

    while True:
        print("\nCinema Customer\n1. Shows this week\n2. Search by genre\n3. Book tickets\n4. Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            list_upcoming_shows(cinema)
        elif choice == "2":
            list_upcoming_shows_by_genre(cinema)
        elif choice == "3":
            next_booking_id = book_show_interactively(
                cinema=cinema,
                booking_service=booking_service,
                next_booking_id=next_booking_id,
            )
            repository.save(cinema, booking_service.bookings)
        elif choice == "4":
            repository.save(cinema, booking_service.bookings)
            print("Goodbye.")
            return
        else:
            print("Unknown option.")


def main() -> None:
    """Run the cinema customer CLI."""
    run_customer_cli()


if __name__ == "__main__":
    main()
