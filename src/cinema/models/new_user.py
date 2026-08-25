"""User creation DTO."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NewUser:
    """Data required to create a user before a user_id exists."""

    auth_subject: str
    full_name: str
    phone_number: str
    email: str
