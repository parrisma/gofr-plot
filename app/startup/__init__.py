"""Startup utilities for gplot servers

Provides centralized configuration resolution and initialization logic.
"""

from .auth_config import resolve_auth_config

__all__ = ["resolve_auth_config"]
