"""Centralized authentication configuration resolution

Implements priority chain for JWT secret and token store configuration:
1. CLI arguments (--jwt-secret, --token-store)
2. Environment variables (GPLOT_JWT_SECRET, GPLOT_TOKEN_STORE)
3. Auto-generated dev secret (dev only, not production)
4. Defaults via Config.get_token_store_path()
"""

import os
from typing import Optional, Tuple
from pathlib import Path
from app.config import Config
from app.logger import ConsoleLogger
import logging


def resolve_auth_config(
    jwt_secret: Optional[str] = None,
    token_store_path: Optional[str] = None,
    require_auth: bool = True,
    allow_auto_secret: bool = True,
) -> Tuple[Optional[str], Optional[Path], bool]:
    """Resolve authentication configuration from CLI args, environment, and defaults

    Priority chain:
        1. CLI arguments (jwt_secret, token_store_path params)
        2. Environment variables (GPLOT_JWT_SECRET, GPLOT_TOKEN_STORE)
        3. Auto-generated secret (only if allow_auto_secret=True and not production)
        4. Default token store path from Config

    Args:
        jwt_secret: JWT secret from CLI argument (takes precedence)
        token_store_path: Token store path from CLI argument (takes precedence)
        require_auth: Whether authentication is required
        allow_auto_secret: Allow auto-generation of dev secret (default: True)

    Returns:
        Tuple of (jwt_secret, token_store_path, require_auth)
        - jwt_secret: Resolved JWT secret or None if auth disabled
        - token_store_path: Resolved token store path or None if auth disabled
        - require_auth: Final auth requirement status

    Raises:
        ValueError: If require_auth=True but no JWT secret could be resolved and
                   auto-generation is disabled or in production environment
    """
    logger = ConsoleLogger(name="auth_config", level=logging.INFO)

    # If auth not required, return early
    if not require_auth:
        logger.info("Authentication disabled (--no-auth)")
        return None, None, False

    # Resolve JWT secret with priority chain
    resolved_secret: Optional[str] = None
    secret_source = "none"

    # Priority 1: CLI argument
    if jwt_secret:
        resolved_secret = jwt_secret
        secret_source = "CLI argument"

    # Priority 2: Environment variable
    elif os.environ.get("GPLOT_JWT_SECRET"):
        resolved_secret = os.environ["GPLOT_JWT_SECRET"]
        secret_source = "GPLOT_JWT_SECRET environment variable"

    # Priority 3: Auto-generated (only in development)
    elif allow_auto_secret:
        is_production = os.environ.get("GPLOT_ENV", "").upper() in ("PROD", "PRODUCTION")
        if is_production:
            logger.error(
                "FATAL: No JWT secret provided in production environment",
                help="Set GPLOT_JWT_SECRET environment variable or use --jwt-secret flag",
            )
            raise ValueError("JWT secret required in production mode")
        else:
            resolved_secret = os.urandom(32).hex()
            secret_source = "auto-generated (DEVELOPMENT ONLY)"
            logger.warning(
                "Auto-generated JWT secret - not suitable for production. Tokens will be invalidated on server restart",
                help="Set GPLOT_JWT_SECRET for persistent authentication",
            )

    # If still no secret and auth required, fail
    if not resolved_secret:
        logger.error(
            "FATAL: JWT secret required but not provided",
            require_auth=require_auth,
            allow_auto_secret=allow_auto_secret,
            help="Set GPLOT_JWT_SECRET environment variable or use --jwt-secret flag, or use --no-auth to disable authentication",
        )
        raise ValueError("JWT secret required when authentication is enabled")

    # Resolve token store path with priority chain
    resolved_token_store: Optional[Path] = None
    store_source = "none"

    # Priority 1: CLI argument
    if token_store_path:
        resolved_token_store = Path(token_store_path)
        store_source = "CLI argument"

    # Priority 2: Environment variable
    elif os.environ.get("GPLOT_TOKEN_STORE"):
        resolved_token_store = Path(os.environ["GPLOT_TOKEN_STORE"])
        store_source = "GPLOT_TOKEN_STORE environment variable"

    # Priority 3: Default from Config
    else:
        resolved_token_store = Path(Config.get_token_store_path())
        store_source = "default path"

    # Log resolved configuration
    logger.info(
        "Authentication configuration resolved",
        require_auth=require_auth,
        secret_source=secret_source,
        secret_fingerprint=_fingerprint_secret(resolved_secret) if resolved_secret else "none",
        token_store=str(resolved_token_store),
        store_source=store_source,
    )

    return resolved_secret, resolved_token_store, require_auth


def _fingerprint_secret(secret: str) -> str:
    """Create a safe fingerprint of the secret for logging (first 12 chars of SHA256)"""
    import hashlib

    digest = hashlib.sha256(secret.encode()).hexdigest()
    return f"sha256:{digest[:12]}"
