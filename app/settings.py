"""Unified Application Settings

Re-exports configuration from gofr_common.config with GOFR_PLOT prefix.
Maintains backward compatibility with existing gofr-plot code.

Design principles:
- Single source of truth for all configuration
- Environment variable overrides with sensible defaults
- Type-safe settings with validation
- Explicit security requirements (e.g., JWT secret enforcement)
- Test mode support for temporary directories
"""

from pathlib import Path

from gofr_common.config import (
    ServerSettings,
    AuthSettings,
    StorageSettings,
    LogSettings,
    Settings,
    get_settings as _get_settings,
    reset_settings,
    Config,
    get_default_storage_dir,
    get_default_token_store_path,
)

# Project-specific constants
_ENV_PREFIX = "GOFR_PLOT"
_PROJECT_ROOT = Path(__file__).parent.parent

# Default ports for gofr-plot
DEFAULT_MCP_PORT = 8050
DEFAULT_WEB_PORT = 8052
DEFAULT_MCPO_PORT = 8051


def get_settings(reload: bool = False, require_auth: bool = True) -> Settings:
    """
    Get or create global settings instance for GOFR_PLOT

    Args:
        reload: If True, reload settings from environment
        require_auth: Whether authentication is required

    Returns:
        Global Settings instance
    """
    return _get_settings(
        prefix=_ENV_PREFIX,
        reload=reload,
        require_auth=require_auth,
        project_root=_PROJECT_ROOT,
    )


# Re-export everything for backward compatibility
__all__ = [
    # Dataclass settings
    "ServerSettings",
    "AuthSettings",
    "StorageSettings",
    "LogSettings",
    "Settings",
    # Singleton
    "get_settings",
    "reset_settings",
    # Legacy Config class
    "Config",
    # Convenience functions
    "get_default_storage_dir",
    "get_default_token_store_path",
    # Constants
    "DEFAULT_MCP_PORT",
    "DEFAULT_WEB_PORT",
    "DEFAULT_MCPO_PORT",
]
