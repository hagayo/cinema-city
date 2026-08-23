"""Print a summary report of the current cinema state."""

from cinema.storage import StorageService


def main() -> None:
    """Load persisted data and print current cinema totals."""
    storage = StorageService()
    cinema, bookings = storage.load()

    total_movies = len(cinema.movies)
    total_shows = sum(len(hall.schedule.shows) for hall in cinema.halls)
    total_bookings = len(bookings)
    total_booked_seats = sum(len(booking.seats) for booking in bookings)

    print("Cinema Report")
    print(f"Movies: {total_movies}")
    print(f"Shows: {total_shows}")
    print(f"Bookings: {total_bookings}")
    print(f"Total booked seats: {total_booked_seats}")


if __name__ == "__main__":
    main()
