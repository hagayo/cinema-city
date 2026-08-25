# Cinema City

Current version: **9.2.0**

Production-style Python teaching project for cinema scheduling, booking,
repository abstractions, persistence, testing, and future Cloudflare D1 integration.

## Setup

```bash
uv sync
```

Run:

```bash
uv run cinema-manager
uv run cinema-customer
```

Developer checks:

```bash
uv run pytest
uv run ruff check .
uv run mypy
uv run pylint src tests
uv run ruff format --check .
```

Windows:

```bat
scripts\check.bat
```

Linux/macOS:

```bash
bash scripts/check.sh
```

## Current architecture

```text
CLI
 ↓
Services
 ↓
Repository Protocols
 ↓
Json*Repository
 ↓
JSON files
```

The business layer depends on repository interfaces, not on JSON persistence.

Current repository abstractions:

```text
CinemaConfigRepository
MovieRepository
ShowRepository
UserRepository
BookingRepository
```

Current implementations:

```text
JsonCinemaConfigRepository
JsonMovieRepository
JsonShowRepository
JsonUserRepository
JsonBookingRepository
```

The future D1 implementation will implement the same repository contracts.


## StorageService stays the application storage facade

`StorageService` deliberately keeps its name. It is the central storage
coordinator and composition point: it groups the injected repository
implementations and coordinates reads that span several repositories.

```text
create_json_storage_service() / future create_d1_storage_service()
                         ↓
                   StorageService
                         ↓
                Repository Interfaces
                         ↓
          Json*Repository / D1*Repository
                         ↓
                     JSON / D1
```

Business services still depend on repository **interfaces**, never on concrete
JSON or D1 classes. `StorageService` is therefore the clear place where students
can see which persistence implementation is currently wired into the
application, without renaming it when the backend changes.

## Auth0 identity and authorization

Authentication identity is separated from the editable user profile.

`User.auth_subject` stores the stable external Auth0 `sub` value:

```text
User
- user_id
- auth_subject   # Auth0 sub
- full_name
- phone_number
- email
```

`email` and `phone_number` are profile data. They are no longer used as proof of
authentication.

After JWT verification, the future Worker will create an `AuthContext` and pass
it into business services:

```text
AuthContext
- auth_subject
- role
- permissions
```

Roles:

```text
Customer
Manager
```

Permissions are explicit business capabilities such as:

```text
book:tickets
cancel:own-booking
manage:movies
manage:schedule
view:bookings
view:report
```

The role/permission relationship is validated, and services call
`actor.require(...)` before protected operations.

The current CLI has no Auth0 login yet, so it asks for a local demo
`auth_subject` to simulate the value that the Worker will later obtain from the
verified JWT.

## Creation DTOs

Persisted entities are separate from creation/update input:

```text
NewMovie
NewUser
UserProfileUpdate
BookingRequest
MovieShowDraft
```

For example, `NewMovie` has no `movie_id`; the repository allocates the ID and
returns a persisted `Movie`.

`UserProfileUpdate` intentionally does not contain `auth_subject`, so normal
profile updates cannot replace the external authentication identity.

## Repository contract tests

Reusable repository behavior tests live in:

```text
tests/contracts/repository_contracts.py
```

The same contract classes are currently executed against the JSON
implementations by:

```text
tests/contracts/test_json_repository_contracts.py
```

A future backend only needs an adapter that supplies its repositories:

```text
TestJsonMovieRepositoryContract
TestD1MovieRepositoryContract
TestNeonMovieRepositoryContract
```

The behavior tests themselves stay the same. This demonstrates that the
application depends on repository contracts rather than a specific database.

## Database-oriented entities

Persisted dataclasses use IDs instead of nested object graphs.

```text
Cinema
- cinema_id
- name

Hall
- hall_id
- hall_name

Seat
- seat_id
- hall_id
- row_number
- seat_number

Movie
- movie_id
- title
- duration_minutes
- description
- genre
- ticket_price

MovieShow
- show_id
- movie_id
- hall_id
- start_time
- ticket_price

User
- user_id
- auth_subject
- full_name
- phone_number
- email

Booking
- booking_id
- user_id
- show_id

BookingSeat
- booking_id
- show_id
- seat_id
```

`BookingSeat.show_id` is intentionally explicit. It allows the database to enforce:

```text
UNIQUE(show_id, seat_id)
```

so the same physical seat cannot be booked twice for the same show.

A single booking can still contain several adjacent seats by storing several
`booking_seats` rows with the same `booking_id`.

## Scheduling

`Hall` contains no scheduling state.

Scheduling logic belongs to:

```text
SchedulingService
```

The service is stateless and reads current data through repository abstractions.

## Current JSON persistence

Current JSON documents use:

```json
"schema_version": 5
```

The JSON implementation remains intentionally available while D1 is introduced,
so students can see that persistence implementations can be exchanged without
rewriting the business layer.

## Cloudflare D1 schema

The initial D1 schema is defined in:

```text
d1/schema.sql
```

It creates:

```text
cinemas
halls
seats
movies
movie_shows
users
bookings
booking_seats
```

The schema is defined before implementing any `D1Repository`.

### Database integrity

The D1 schema contains:

- primary keys for every persisted entity
- foreign keys between related tables
- unique `hall_name`
- unique physical seat coordinate:
  `hall_id + row_number + seat_number`
- case-insensitive unique movie titles
- unique Auth0 identity key: `auth_subject`
- unique user email and phone number as profile-data integrity rules
- unique show start time per hall:
  `hall_id + start_time`
- critical double-booking protection:
  `UNIQUE(show_id, seat_id)`
- a database trigger that rejects a seat that belongs to a different hall than
  the scheduled show
- indexes for common joins and lookups

Deleting a booking cascades only to its `booking_seats` rows. Users, shows,
movies, halls, and seats remain protected by restrictive foreign keys.

## Double-booking protection

Application-level validation still exists in `BookingService`, but it is not the
final line of defense.

The database itself rejects:

```text
show_id = 25
seat_id = 301
```

if that exact pair has already been persisted.

This protects the system even when two requests race concurrently and both pass
the application-level availability check before either request sees the other.

## D1 schema tests

`tests/unit/test_d1_schema.py` loads the exact `d1/schema.sql` into an in-memory
SQLite database and verifies:

- required tables exist
- foreign keys reject orphan rows
- duplicate `show_id + seat_id` is rejected
- the same seat is allowed for different shows
- `BookingSeat.show_id` must match `Booking.show_id`
- a seat must belong to the hall of the show
- booking deletion cascades to junction rows only
- unique business keys are enforced
- CHECK constraints are enforced
- expected indexes exist

These tests validate the schema independently from `BookingService` and from the
future `D1Repository`.

## Testing

Pytest enforces at least:

```text
90% total coverage
```

Run:

```bash
uv run pytest
```
