"""JSON persistence for user profiles linked to external auth subjects."""

import json
from pathlib import Path
from typing import Any

from cinema.exceptions import (
    BusinessError,
    StorageError,
    UserIdentityConflictError,
)
from cinema.models import NewUser, User, UserProfileUpdate
from cinema.services.user_identity import (
    normalize_email,
    normalize_full_name,
    normalize_phone_number,
)
from cinema.storage.app_paths import USERS_FILE
from cinema.storage.interfaces import UserRepository
from cinema.storage.json_file import atomic_write_json, exclusive_file_lock, read_json
from cinema.storage.schema import SCHEMA_VERSION, validate_schema_version

DEFAULT_USERS_FILE = USERS_FILE


class JsonUserRepository(UserRepository):
    """Persist user profiles while treating auth_subject as external identity."""

    def __init__(self, file_path: Path = DEFAULT_USERS_FILE) -> None:
        self._file_path = file_path

    def load(self) -> list[User]:
        """Load and validate all persisted users."""
        try:
            with exclusive_file_lock(self._file_path):
                _, data = self._read_document()
            return self._deserialize_all(data)
        except StorageError:
            raise
        except (
            OSError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
            BusinessError,
        ) as error:
            raise StorageError(
                f"Could not load user data from {self._file_path}"
            ) from error

    def find_by_auth_subject(self, auth_subject: str) -> User | None:
        """Return the user linked to an authenticated provider subject."""
        normalized_subject = self._normalize_auth_subject(auth_subject)
        return next(
            (
                user
                for user in self.load()
                if user.auth_subject == normalized_subject
            ),
            None,
        )

    def create(self, new_user: NewUser) -> User:
        """Create a user for a new authenticated subject."""
        subject = self._normalize_auth_subject(new_user.auth_subject)
        full_name = normalize_full_name(new_user.full_name)
        phone_number = normalize_phone_number(new_user.phone_number)
        email = normalize_email(new_user.email)

        try:
            with exclusive_file_lock(self._file_path):
                last_user_id, data = self._read_document_for_write()
                users = self._deserialize_all(data)

                if any(user.auth_subject == subject for user in users):
                    raise UserIdentityConflictError(
                        "Authenticated subject already has a user"
                    )

                self._ensure_profile_values_available(
                    users,
                    email=email,
                    phone_number=phone_number,
                )

                user = User(
                    user_id=last_user_id + 1,
                    auth_subject=subject,
                    full_name=full_name,
                    phone_number=phone_number,
                    email=email,
                )
                users.append(user)
                self._write(users, user.user_id)
                return user
        except (StorageError, UserIdentityConflictError):
            raise
        except (
            OSError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
            BusinessError,
        ) as error:
            raise StorageError(
                f"Could not create user in {self._file_path}"
            ) from error

    def update(self, user_id: int, profile: UserProfileUpdate) -> User:
        """Update profile fields without changing the external auth subject."""
        full_name = normalize_full_name(profile.full_name)
        phone_number = normalize_phone_number(profile.phone_number)
        email = normalize_email(profile.email)

        try:
            with exclusive_file_lock(self._file_path):
                last_user_id, data = self._read_document_for_write()
                users = self._deserialize_all(data)
                existing = next(
                    (user for user in users if user.user_id == user_id),
                    None,
                )
                if existing is None:
                    raise StorageError(f"User {user_id} does not exist")

                other_users = [
                    user for user in users if user.user_id != user_id
                ]
                self._ensure_profile_values_available(
                    other_users,
                    email=email,
                    phone_number=phone_number,
                )

                updated = User(
                    user_id=existing.user_id,
                    auth_subject=existing.auth_subject,
                    full_name=full_name,
                    phone_number=phone_number,
                    email=email,
                )
                users = [
                    updated if user.user_id == user_id else user
                    for user in users
                ]
                self._write(users, last_user_id)
                return updated
        except (StorageError, UserIdentityConflictError):
            raise
        except (
            OSError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
            BusinessError,
        ) as error:
            raise StorageError(
                f"Could not update user data in {self._file_path}"
            ) from error

    def _read_document(self) -> tuple[int, list[dict[str, Any]]]:
        document = read_json(self._file_path)
        if not isinstance(document, dict):
            raise TypeError("User data must be a JSON object")

        validate_schema_version(document)
        users = document.get("users")
        last_user_id = document.get("last_user_id")
        if not isinstance(users, list) or not isinstance(last_user_id, int):
            raise TypeError("User data has an invalid document structure")

        user_ids = [int(item["user_id"]) for item in users]
        max_user_id = max(user_ids, default=0)
        if last_user_id < max_user_id:
            raise StorageError(
                "User data last_user_id is lower than an existing user ID"
            )

        return last_user_id, users

    def _read_document_for_write(self) -> tuple[int, list[dict[str, Any]]]:
        if not self._file_path.exists() and self._file_path != DEFAULT_USERS_FILE:
            return 0, []
        return self._read_document()

    def _deserialize_all(self, data: list[dict[str, Any]]) -> list[User]:
        users = [self._deserialize(item) for item in data]

        user_ids = [user.user_id for user in users]
        if len(user_ids) != len(set(user_ids)):
            raise StorageError("User data contains duplicate user IDs")

        subjects = [user.auth_subject for user in users]
        if len(subjects) != len(set(subjects)):
            raise StorageError("User data contains duplicate auth subjects")

        emails = [user.email for user in users]
        if len(emails) != len(set(emails)):
            raise StorageError("User data contains duplicate email addresses")

        phones = [user.phone_number for user in users]
        if len(phones) != len(set(phones)):
            raise StorageError("User data contains duplicate phone numbers")

        return users

    @staticmethod
    def _ensure_profile_values_available(
        users: list[User],
        *,
        email: str,
        phone_number: str,
    ) -> None:
        if any(user.email == email for user in users):
            raise UserIdentityConflictError(
                "Email address already belongs to another user"
            )
        if any(user.phone_number == phone_number for user in users):
            raise UserIdentityConflictError(
                "Phone number already belongs to another user"
            )

    def _write(self, users: list[User], last_user_id: int) -> None:
        atomic_write_json(
            self._file_path,
            {
                "schema_version": SCHEMA_VERSION,
                "last_user_id": last_user_id,
                "users": [self._serialize(user) for user in users],
            },
        )

    @staticmethod
    def _normalize_auth_subject(auth_subject: str) -> str:
        normalized = auth_subject.strip()
        if not normalized:
            raise UserIdentityConflictError(
                "Authenticated subject cannot be empty"
            )
        return normalized

    @staticmethod
    def _serialize(user: User) -> dict[str, Any]:
        return {
            "user_id": user.user_id,
            "auth_subject": user.auth_subject,
            "full_name": user.full_name,
            "phone_number": user.phone_number,
            "email": user.email,
        }

    @staticmethod
    def _deserialize(item: dict[str, Any]) -> User:
        return User(
            user_id=int(item["user_id"]),
            auth_subject=str(item["auth_subject"]).strip(),
            full_name=str(item["full_name"]),
            phone_number=normalize_phone_number(str(item["phone_number"])),
            email=normalize_email(str(item["email"])),
        )
