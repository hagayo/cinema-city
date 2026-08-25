"""User profile update DTO."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UserProfileUpdate:
    """Editable user profile fields; auth_subject is intentionally excluded."""

    full_name: str
    phone_number: str
    email: str
