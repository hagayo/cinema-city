"""Interactive command-line interface for cinema customers."""

from datetime import datetime, timedelta

from cinema.cli.error_handling import run_cli_safely
from cinema.cli.input_helpers import read_genre
from cinema.exceptions import BusinessError
from cinema.models import (
    AuthContext,
    Booking,
    BookingSeat,
    Genre,
    Hall,
    Movie,
    MovieShow,
    NewUser,
    Seat,
    User,
    UserProfileUpdate,
    customer_auth_context,
)
from cinema.services import BookingService
from cinema.storage import (
    BookingRepository,
    UserRepository,
    create_json_storage_service,
)
from cinema.time_utils import local_now

WEEK_DAYS = 7
MAX_SEATS_PER_BOOKING = 5


def get_upcoming_shows(
    shows: list[MovieShow] | tuple[MovieShow, ...],
    current_time: datetime,
) -> tuple[MovieShow, ...]:
    """Return shows that begin within the next seven days."""
    end_time = current_time + timedelta(days=WEEK_DAYS)
    upcoming = [
        show
        for show in shows
        if current_time <= show.start_time < end_time
    ]
    return tuple(sorted(upcoming, key=lambda show: show.start_time))


def get_upcoming_shows_by_genre(
    shows: list[MovieShow] | tuple[MovieShow, ...],
    movies: list[Movie] | tuple[Movie, ...],
    current_time: datetime,
    genre: Genre,
) -> tuple[MovieShow, ...]:
    """Return upcoming shows whose referenced movie has the requested genre."""
    movies_by_id = {movie.movie_id: movie for movie in movies}
    return tuple(
        show
        for show in get_upcoming_shows(shows, current_time)
        if movies_by_id[show.movie_id].genre == genre
    )


def find_show_by_id(
    shows: tuple[MovieShow, ...],
    show_id: int,
) -> MovieShow | None:
    return next((show for show in shows if show.show_id == show_id), None)


def find_hall_by_id(
    halls: list[Hall] | tuple[Hall, ...],
    hall_id: int,
) -> Hall | None:
    return next((hall for hall in halls if hall.hall_id == hall_id), None)


def read_positive_int(prompt: str) -> int:
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
    while True:
        seat_count = read_positive_int("How many seats? (1-5): ")
        if seat_count <= MAX_SEATS_PER_BOOKING:
            break
        print(f"A booking can contain at most {MAX_SEATS_PER_BOOKING} seats.")

    row_number = read_positive_int("Row: ")
    first_seat = read_positive_int("First seat number: ")
    return tuple(
        (row_number, first_seat + offset)
        for offset in range(seat_count)
    )


def print_shows(
    shows: tuple[MovieShow, ...],
    movies: list[Movie] | tuple[Movie, ...],
    halls: list[Hall] | tuple[Hall, ...],
) -> None:
    movies_by_id = {movie.movie_id: movie for movie in movies}
    halls_by_id = {hall.hall_id: hall for hall in halls}
    for show in shows:
        movie = movies_by_id[show.movie_id]
        hall = halls_by_id[show.hall_id]
        print(
            f"{show.show_id}. {movie.title} | {movie.genre.value} | "
            f"{show.start_time:%Y-%m-%d %H:%M} | "
            f"{hall.hall_name} | {show.ticket_price} NIS"
        )


def list_upcoming_shows(
    shows: list[MovieShow] | tuple[MovieShow, ...],
    movies: list[Movie] | tuple[Movie, ...],
    halls: list[Hall] | tuple[Hall, ...],
    current_time: datetime | None = None,
) -> tuple[MovieShow, ...]:
    now = current_time or local_now()
    upcoming = get_upcoming_shows(shows, now)
    if not upcoming:
        print("No shows are scheduled for the coming week.")
        return ()
    print_shows(upcoming, movies, halls)
    return upcoming


def list_upcoming_shows_by_genre(
    shows: list[MovieShow] | tuple[MovieShow, ...],
    movies: list[Movie] | tuple[Movie, ...],
    halls: list[Hall] | tuple[Hall, ...],
    current_time: datetime | None = None,
) -> None:
    genre = read_genre()
    now = current_time or local_now()
    filtered = get_upcoming_shows_by_genre(shows, movies, now, genre)
    if not filtered:
        print(f"No {genre.value} shows are scheduled for the coming week.")
        return
    print_shows(filtered, movies, halls)


def read_local_customer_auth_context() -> AuthContext:
    """Simulate the Auth0 `sub` while the project still runs as a local CLI."""
    while True:
        auth_subject = input("Auth subject (simulates Auth0 sub): ").strip()
        if auth_subject:
            return customer_auth_context(auth_subject)
        print("Auth subject cannot be empty.")


def get_or_create_user_profile(
    actor: AuthContext,
    user_repository: UserRepository,
) -> User:
    """Link the authenticated subject to a profile; email/phone are profile data."""
    full_name = input("Full name: ")
    phone_number = input("Phone number: ")
    email = input("Email: ")

    existing = user_repository.find_by_auth_subject(actor.auth_subject)
    if existing is None:
        return user_repository.create(
            NewUser(
                auth_subject=actor.auth_subject,
                full_name=full_name,
                phone_number=phone_number,
                email=email,
            )
        )

    return user_repository.update(
        existing.user_id,
        UserProfileUpdate(
            full_name=full_name,
            phone_number=phone_number,
            email=email,
        ),
    )


def book_show_interactively(
    *,
    actor: AuthContext,
    halls: list[Hall],
    seats: list[Seat],
    movies: list[Movie],
    shows: list[MovieShow],
    booking_repository: BookingRepository,
    user_repository: UserRepository,
    current_time: datetime | None = None,
) -> None:
    now = current_time or local_now()
    upcoming_shows = list_upcoming_shows(shows, movies, halls, now)
    if not upcoming_shows:
        return

    show = find_show_by_id(
        upcoming_shows,
        read_positive_int("Show ID: "),
    )
    if show is None:
        print("Show is not available for booking in the coming week.")
        return

    if find_hall_by_id(halls, show.hall_id) is None:
        print("Hall not found.")
        return

    try:
        user = get_or_create_user_profile(actor, user_repository)
        users = user_repository.load()
        bookings, booking_seats = booking_repository.load(
            valid_show_ids={item.show_id for item in shows},
            valid_user_ids={item.user_id for item in users},
            valid_seat_ids={seat.seat_id for seat in seats},
        )
        request = BookingService.prepare_booking(
            actor=actor,
            user=user,
            show=show,
            requested_seats=read_requested_seats(),
            seats=seats,
            bookings=bookings,
            booking_seats=booking_seats,
        )
        booking, new_rows = booking_repository.add(request)
    except BusinessError as error:
        print(f"Cannot create booking: {error}")
        return

    total = BookingService.total_price(booking, show, new_rows)
    print(f"Booking #{booking.booking_id} confirmed. Total: {total} NIS")


def cancel_booking_interactively(
    *,
    actor: AuthContext,
    seats: list[Seat],
    shows: list[MovieShow],
    booking_repository: BookingRepository,
    user_repository: UserRepository,
    current_time: datetime | None = None,
) -> None:
    booking_id = read_positive_int("Booking ID to cancel: ")

    try:
        user = user_repository.find_by_auth_subject(actor.auth_subject)
        if user is None:
            print("Cannot cancel booking: authenticated user profile was not found")
            return

        users = user_repository.load()
        bookings, booking_seats = booking_repository.load(
            valid_show_ids={show.show_id for show in shows},
            valid_user_ids={item.user_id for item in users},
            valid_seat_ids={seat.seat_id for seat in seats},
        )
        booking = next(
            (item for item in bookings if item.booking_id == booking_id),
            None,
        )
        if booking is None:
            print("Cannot cancel booking: booking was not found")
            return

        show = next(item for item in shows if item.show_id == booking.show_id)
        BookingService.validate_cancellation(
            actor,
            user,
            booking,
            show,
            current_time or local_now(),
        )
        _, removed_rows = booking_repository.delete(booking_id, user.user_id)
    except BusinessError as error:
        print(f"Cannot cancel booking: {error}")
        return

    print(
        f"Booking #{booking_id} cancelled. "
        f"{len(removed_rows)} seat(s) released."
    )


def run_customer_cli() -> None:
    storage = create_json_storage_service()
    actor = read_local_customer_auth_context()

    while True:
        print(
            "\nCinema Customer\n"
            "1. Shows this week\n"
            "2. Search by genre\n"
            "3. Book tickets\n"
            "4. Cancel booking\n"
            "5. Exit"
        )
        choice = input("Choose an option: ").strip()

        if choice == "1":
            _, halls, _, movies, shows = storage.load_catalog()
            list_upcoming_shows(shows, movies, halls)
        elif choice == "2":
            _, halls, _, movies, shows = storage.load_catalog()
            list_upcoming_shows_by_genre(shows, movies, halls)
        elif choice == "3":
            _, halls, seats, movies, shows = storage.load_catalog()
            book_show_interactively(
                actor=actor,
                halls=halls,
                seats=seats,
                movies=movies,
                shows=shows,
                booking_repository=storage.booking_repository,
                user_repository=storage.user_repository,
            )
        elif choice == "4":
            _, _, seats, _, shows = storage.load_catalog()
            cancel_booking_interactively(
                actor=actor,
                seats=seats,
                shows=shows,
                booking_repository=storage.booking_repository,
                user_repository=storage.user_repository,
            )
        elif choice == "5":
            print("Goodbye.")
            return
        else:
            print("Unknown option.")


def main() -> None:
    run_cli_safely(run_customer_cli)


if __name__ == "__main__":
    main()
