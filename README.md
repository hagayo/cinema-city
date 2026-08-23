# Cinema Booking V5.1

V5.1 fixes the scheduling algorithm and tightens code quality.

## Main changes

- Ticket prices are `int` values in whole Israeli shekels.
- `find_available_start_times()` never proposes overlapping shows.
- Available-time search no longer creates fake `MovieShow` objects.
- `CinemaManager` uses a hall lookup dictionary.
- `Self` is used for class factory return types.
- Public and complex methods include clearer docstrings and raised errors.
- Additional validation tests were added.
- Cache and generated files are excluded from the package.

## Quality commands

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pylint src tests
```


## CLI for the cinema manager

Run the interactive manager interface with:

```bash
uv run cinema-manager
```

The manager can:

- add a movie manually
- enter title, duration and description
- optionally schedule the movie immediately
- list movies already added to the catalog

The CLI is kept in:

```text
src/cinema/cli/
```

It only handles user input/output and delegates business operations to
`CinemaManager`.


## CLI update in V5.3

Movie creation and scheduling are separate manager operations.

```text
1. Add movie
2. Schedule movie
3. List movies
4. Exit
```

`Add movie` only adds a movie to the catalog.

`Schedule movie` asks for an existing movie by:

- movie ID
- exact movie title

and then schedules that movie using `CinemaManager.schedule_movie()`.


## Customer CLI in V5.4

Run:

```bash
uv run cinema-customer
```

The customer can:

1. View all shows scheduled for the coming seven days.
2. Select a show by ID.
3. Book between 1 and 5 adjacent seats.
4. See the total booking price.

For now the customer CLI creates an in-memory demo cinema when it starts.
Persistence will be added later.


## JSON persistence in V5.5

Both CLIs now use the same persistent file:

```text
cinema_data.json
```

The file stores:

- cinema configuration
- movie catalog
- hall schedules
- movie shows
- customer bookings

The persistence layer is isolated in:

```text
src/cinema/storage/json_repository.py
```

The manager and customer CLIs both load the file on startup and save changes
after write operations.


## Persistence split in V5.6

Application state is now stored in four separate JSON files:

```text
data/
├── cinema_config.json
├── movies.json
├── shows.json
└── bookings.json
```

Each file has its own repository:

```text
CinemaConfigRepository
MovieRepository
ShowRepository
BookingRepository
```

`StorageService` only coordinates load/save order between them.


## Developer checks in V5.7

Run all developer checks in sequence:

```bash
bash scripts/check.sh
```

The script stops immediately if any command fails and prints the failing check and its exit code.


## Genres in V5.8

Movies contain a required `Genre` value.

Supported genres:

```text
comedy
drama
thriller
crime
family
```

The cinema manager selects a genre when adding a movie.

The customer CLI includes:

```text
1. Shows this week
2. Search by genre
3. Book tickets
4. Exit
```

Genres are persisted in `data/movies.json`.
