"""Domain models and DTOs used by the cinema application."""

from cinema.models.auth import (
    AuthContext,
    Permission,
    Role,
    customer_auth_context,
    manager_auth_context,
)
from cinema.models.booking import Booking
from cinema.models.booking_request import BookingRequest
from cinema.models.booking_seat import BookingSeat
from cinema.models.cinema import Cinema
from cinema.models.genre import Genre
from cinema.models.hall import Hall
from cinema.models.movie import Movie
from cinema.models.movie_show import MovieShow
from cinema.models.movie_show_draft import MovieShowDraft
from cinema.models.new_movie import NewMovie
from cinema.models.new_user import NewUser
from cinema.models.seat import Seat
from cinema.models.user import User
from cinema.models.user_profile_update import UserProfileUpdate

__all__ = [
    "AuthContext",
    "Booking",
    "BookingRequest",
    "BookingSeat",
    "Cinema",
    "Genre",
    "Hall",
    "Movie",
    "MovieShow",
    "MovieShowDraft",
    "NewMovie",
    "NewUser",
    "Permission",
    "Role",
    "Seat",
    "User",
    "UserProfileUpdate",
    "customer_auth_context",
    "manager_auth_context",
]
