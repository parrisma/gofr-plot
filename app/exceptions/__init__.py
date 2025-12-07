"""Custom exceptions for GOFR-PLOT application.

Base exceptions are re-exported from gofr_common.exceptions.
Project-specific exceptions are defined locally.
"""

# Re-export common exceptions from gofr_common
from gofr_common.exceptions import (
    GofrError,
    ValidationError,
    ResourceNotFoundError,
    SecurityError,
    ConfigurationError,
    RegistryError,
)

# Project-specific alias for backward compatibility
GofrPlotError = GofrError

__all__ = [
    # Base exceptions (from gofr_common)
    "GofrError",
    "GofrPlotError",  # Alias for backward compatibility
    "ValidationError",
    "ResourceNotFoundError",
    "SecurityError",
    "ConfigurationError",
    "RegistryError",
]
