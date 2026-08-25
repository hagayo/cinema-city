"""Cinema user profile linked to an external authentication subject."""

from dataclasses import dataclass

from cinema.exceptions import UserValidationError


@dataclass(frozen=True, slots=True)
class User:
    """Represent one persisted user profile."""

    user_id: int
    auth_subject: str
    full_name: str
    phone_number: str
    email: str

    def __post_init__(self) -> None:
        """Validate persisted user data."""
        if self.user_id <= 0:
            raise UserValidationError("User ID must be positive")
        if not self.auth_subject.strip():
            raise UserValidationError("Auth subject cannot be empty")
        if not self.full_name.strip():
            raise UserValidationError("Full name cannot be empty")
        if not self.phone_number:
            raise UserValidationError("Phone number cannot be empty")
        if not self.email:
            raise UserValidationError("Email cannot be empty")
