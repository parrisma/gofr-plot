"""Authentication module

Provides JWT-based authentication with group mapping.
"""

from .service import AuthService, TokenInfo
from .middleware import get_auth_service, verify_token, init_auth_service

__all__ = [
    "AuthService",
    "TokenInfo",
    "get_auth_service",
    "verify_token",
    "init_auth_service",
]
