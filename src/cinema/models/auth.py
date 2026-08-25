"""Authenticated request identity and authorization values."""

from dataclasses import dataclass
from enum import StrEnum

from cinema.exceptions import AuthorizationError


class Role(StrEnum):
    """Application roles received from the authenticated request."""

    CUSTOMER = "customer"
    MANAGER = "manager"


class Permission(StrEnum):
    """Business permissions that services may require."""

    VIEW_SHOWS = "view:shows"
    BOOK_TICKETS = "book:tickets"
    CANCEL_OWN_BOOKING = "cancel:own-booking"
    MANAGE_MOVIES = "manage:movies"
    MANAGE_SCHEDULE = "manage:schedule"
    VIEW_BOOKINGS = "view:bookings"
    VIEW_REPORT = "view:report"


CUSTOMER_PERMISSIONS = frozenset(
    {
        Permission.VIEW_SHOWS,
        Permission.BOOK_TICKETS,
        Permission.CANCEL_OWN_BOOKING,
    }
)

MANAGER_PERMISSIONS = frozenset(
    {
        Permission.VIEW_SHOWS,
        Permission.MANAGE_MOVIES,
        Permission.MANAGE_SCHEDULE,
        Permission.VIEW_BOOKINGS,
        Permission.VIEW_REPORT,
    }
)


@dataclass(frozen=True, slots=True)
class AuthContext:
    """Identity and permissions produced after JWT verification."""

    auth_subject: str
    role: Role
    permissions: frozenset[Permission]

    def __post_init__(self) -> None:
        if not self.auth_subject.strip():
            raise AuthorizationError("Authenticated subject cannot be empty")

        allowed = (
            CUSTOMER_PERMISSIONS
            if self.role is Role.CUSTOMER
            else MANAGER_PERMISSIONS
        )
        if not self.permissions.issubset(allowed):
            raise AuthorizationError(
                f"Permissions do not match role {self.role.value}"
            )

    def require(self, permission: Permission) -> None:
        """Reject a request that lacks a required business permission."""
        if permission not in self.permissions:
            raise AuthorizationError(
                f"Permission {permission.value} is required"
            )


def customer_auth_context(auth_subject: str) -> AuthContext:
    """Build a customer context for adapters/tests."""

    return AuthContext(
        auth_subject=auth_subject,
        role=Role.CUSTOMER,
        permissions=CUSTOMER_PERMISSIONS,
    )


def manager_auth_context(auth_subject: str) -> AuthContext:
    """Build a manager context for adapters/tests."""

    return AuthContext(
        auth_subject=auth_subject,
        role=Role.MANAGER,
        permissions=MANAGER_PERMISSIONS,
    )
