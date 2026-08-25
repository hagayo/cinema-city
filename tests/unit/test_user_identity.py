"""Tests for user normalization and auth_subject-based persistence."""

import json
from pathlib import Path

import pytest

from cinema.exceptions import StorageError, UserIdentityConflictError, UserValidationError
from cinema.models import NewUser, UserProfileUpdate
from cinema.services import normalize_email, normalize_full_name, normalize_phone_number
from cinema.storage import JsonUserRepository


def new_user(
    auth_subject: str = "auth0|dana",
    full_name: str = "Dana Cohen",
    phone_number: str = "0501234567",
    email: str = "dana@example.com",
) -> NewUser:
    return NewUser(auth_subject, full_name, phone_number, email)


def test_identity_normalization() -> None:
    assert normalize_full_name("  Dana   Cohen ") == "Dana Cohen"
    assert normalize_email(" DANA@Example.COM ") == "dana@example.com"
    assert normalize_phone_number("050-123-4567") == "+972501234567"
    assert normalize_phone_number("+972 50 123 4567") == "+972501234567"
    assert normalize_phone_number("972501234567") == "+972501234567"


@pytest.mark.parametrize(
    ("value", "normalizer"),
    [
        (" ", normalize_full_name),
        ("x", normalize_full_name),
        ("bad-email", normalize_email),
        ("03-1234567", normalize_phone_number),
    ],
)
def test_invalid_profile_values_are_rejected(value, normalizer) -> None:
    with pytest.raises(UserValidationError):
        normalizer(value)


def test_user_repository_creates_updates_and_finds_by_auth_subject(
    tmp_path: Path,
) -> None:
    repo = JsonUserRepository(tmp_path / "users.json")
    first = repo.create(
        new_user(email="DANA@example.com")
    )
    updated = repo.update(
        first.user_id,
        UserProfileUpdate(
            full_name="Dana Updated",
            phone_number="0521234567",
            email="updated@example.com",
        ),
    )

    assert first.user_id == updated.user_id == 1
    assert updated.auth_subject == "auth0|dana"
    assert updated.full_name == "Dana Updated"
    assert repo.find_by_auth_subject("auth0|dana") == updated
    assert repo.find_by_auth_subject("auth0|missing") is None
    assert repo.load() == [updated]


def test_user_repository_allocates_monotonic_ids(tmp_path: Path) -> None:
    repo = JsonUserRepository(tmp_path / "users.json")
    one = repo.create(new_user())
    two = repo.create(
        new_user(
            auth_subject="auth0|avi",
            full_name="Avi Levi",
            phone_number="0521234567",
            email="avi@example.com",
        )
    )
    assert (one.user_id, two.user_id) == (1, 2)


def test_duplicate_auth_subject_is_rejected(tmp_path: Path) -> None:
    repo = JsonUserRepository(tmp_path / "users.json")
    repo.create(new_user())

    with pytest.raises(UserIdentityConflictError, match="subject"):
        repo.create(
            new_user(
                auth_subject="auth0|dana",
                phone_number="0521234567",
                email="other@example.com",
            )
        )


def test_profile_values_can_be_updated_but_auth_subject_cannot(
    tmp_path: Path,
) -> None:
    repo = JsonUserRepository(tmp_path / "users.json")
    first = repo.create(new_user())
    second = repo.create(
        new_user(
            auth_subject="auth0|avi",
            full_name="Avi Levi",
            phone_number="0521234567",
            email="avi@example.com",
        )
    )

    with pytest.raises(UserIdentityConflictError, match="Email"):
        repo.update(
            second.user_id,
            UserProfileUpdate(
                full_name="Avi",
                phone_number="0531234567",
                email=first.email,
            ),
        )

    with pytest.raises(UserIdentityConflictError, match="Phone"):
        repo.update(
            second.user_id,
            UserProfileUpdate(
                full_name="Avi",
                phone_number=first.phone_number,
                email="avi2@example.com",
            ),
        )

    assert repo.find_by_auth_subject("auth0|avi") == second


def test_update_rejects_unknown_user(tmp_path: Path) -> None:
    repo = JsonUserRepository(tmp_path / "users.json")

    with pytest.raises(StorageError, match="does not exist"):
        repo.update(
            999,
            UserProfileUpdate(
                "Missing User",
                "0521234567",
                "missing@example.com",
            ),
        )


@pytest.mark.parametrize(
    ("users", "message"),
    [
        (
            [
                {
                    "user_id": 1,
                    "auth_subject": "auth0|a",
                    "full_name": "A",
                    "phone_number": "0501234567",
                    "email": "a@a.com",
                },
                {
                    "user_id": 1,
                    "auth_subject": "auth0|b",
                    "full_name": "B",
                    "phone_number": "0521234567",
                    "email": "b@b.com",
                },
            ],
            "duplicate user IDs",
        ),
        (
            [
                {
                    "user_id": 1,
                    "auth_subject": "auth0|same",
                    "full_name": "A",
                    "phone_number": "0501234567",
                    "email": "a@a.com",
                },
                {
                    "user_id": 2,
                    "auth_subject": "auth0|same",
                    "full_name": "B",
                    "phone_number": "0521234567",
                    "email": "b@b.com",
                },
            ],
            "duplicate auth subjects",
        ),
        (
            [
                {
                    "user_id": 1,
                    "auth_subject": "auth0|a",
                    "full_name": "A",
                    "phone_number": "0501234567",
                    "email": "same@a.com",
                },
                {
                    "user_id": 2,
                    "auth_subject": "auth0|b",
                    "full_name": "B",
                    "phone_number": "0521234567",
                    "email": "same@a.com",
                },
            ],
            "duplicate email",
        ),
        (
            [
                {
                    "user_id": 1,
                    "auth_subject": "auth0|a",
                    "full_name": "A",
                    "phone_number": "0501234567",
                    "email": "a@a.com",
                },
                {
                    "user_id": 2,
                    "auth_subject": "auth0|b",
                    "full_name": "B",
                    "phone_number": "0501234567",
                    "email": "b@b.com",
                },
            ],
            "duplicate phone",
        ),
    ],
)
def test_user_repository_rejects_duplicate_rows(
    tmp_path: Path,
    users: list[dict[str, object]],
    message: str,
) -> None:
    path = tmp_path / "users.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 5,
                "last_user_id": 2,
                "users": users,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(StorageError, match=message):
        JsonUserRepository(path).load()


def test_user_repository_rejects_bad_last_id(tmp_path: Path) -> None:
    path = tmp_path / "users.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 5,
                "last_user_id": 0,
                "users": [
                    {
                        "user_id": 1,
                        "auth_subject": "auth0|dana",
                        "full_name": "Dana",
                        "phone_number": "0501234567",
                        "email": "dana@example.com",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(StorageError, match="last_user_id"):
        JsonUserRepository(path).load()
