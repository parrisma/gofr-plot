"""Authentication configuration utilities for GOFR-PLOT server.

Re-exports resolve_auth_config from gofr_common.auth.config with
GOFR_PLOT-specific defaults.
"""

from pathlib import Path
from typing import Optional, Tuple

from gofr_common.auth.config import resolve_auth_config as _resolve_auth_config

from app.config import Config


def resolve_auth_config(
    jwt_secret: Optional[str] = None,
    token_store_path: Optional[str] = None,
    require_auth: bool = True,
    allow_auto_secret: bool = True,
) -> Tuple[Optional[str], Optional[Path], bool]:
    """Resolve authentication configuration from CLI args, environment, and defaults.

    Priority chain:
        1. CLI arguments (jwt_secret, token_store_path params)
        2. Environment variables (GOFR_PLOT_JWT_SECRET, GOFR_PLOT_TOKEN_STORE)
        3. Auto-generated secret (only if allow_auto_secret=True and not production)
        4. Default token store path from Config

    Args:
        jwt_secret: JWT secret from CLI argument (takes precedence)
        token_store_path: Token store path from CLI argument (takes precedence)
        require_auth: Whether authentication is required
        allow_auto_secret: Allow auto-generation of dev secret (default: True)

    Returns:
        Tuple of (jwt_secret, token_store_path, require_auth)

    Raises:
        ValueError: If require_auth=True but no JWT secret could be resolved
    """
    # Use default token store path if not provided
    default_token_store = str(Config.get_token_store_path())
    effective_token_store = token_store_path or default_token_store

    resolved_secret, resolved_path, final_require_auth = _resolve_auth_config(
        env_prefix="GOFR_PLOT",
        jwt_secret_arg=jwt_secret,
        token_store_arg=effective_token_store,
        require_auth=require_auth,
        allow_auto_secret=allow_auto_secret,
        exit_on_missing=False,
        logger=None,  # Will create its own logger
    )

    # Convert to Path for backward compatibility with gofr-plot's signature
    resolved_path_obj = Path(resolved_path) if resolved_path else None
    return resolved_secret, resolved_path_obj, final_require_auth

