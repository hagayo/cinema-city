"""Authentication/authorization related business errors."""

from cinema.exceptions.base import BusinessError


class AuthorizationError(BusinessError):
    """Raised when an authenticated actor lacks required permission."""
