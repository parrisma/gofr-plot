"""JWT Authentication Service

Handles JWT token creation, validation, and group mapping.
"""

import jwt
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
from dataclasses import dataclass
from pathlib import Path
import json
from app.config import get_default_token_store_path
from app.logger import ConsoleLogger
import logging
import hashlib


@dataclass
class TokenInfo:
    """Information extracted from a JWT token"""

    token: str
    group: str
    expires_at: datetime
    issued_at: datetime


class AuthService:
    """Service for JWT authentication and group management"""

    def __init__(self, secret_key: Optional[str] = None, token_store_path: Optional[str] = None):
        """
        Initialize the authentication service

        Args:
            secret_key: Secret key for JWT signing (defaults to env var or generates one)
            token_store_path: Path to store token-group mappings.
                             If None, uses configured default from app.config.
                             If ":memory:", uses in-memory storage without file persistence.
        """
        self.logger = ConsoleLogger(name="auth", level=logging.INFO)

        # Get or create secret key
        secret = secret_key or os.environ.get("GPLOT_JWT_SECRET")
        if not secret:
            self.logger.warning(
                "No JWT secret provided, generating random secret (not suitable for production)"
            )
            secret = os.urandom(32).hex()
        self.secret_key: str = secret

        # Setup token store
        if token_store_path is None:
            token_store_path = get_default_token_store_path()

        # Check for in-memory mode
        self._use_memory_store = token_store_path == ":memory:"

        if self._use_memory_store:
            self.token_store_path = None
            self.token_store = {}
            self.logger.info(
                "AuthService initialized with in-memory token store",
                secret_fingerprint=self._secret_fingerprint(),
            )
        else:
            self.token_store_path = Path(token_store_path)
            self._load_token_store()
            self.logger.info(
                "AuthService initialized",
                token_store=str(self.token_store_path),
                secret_fingerprint=self._secret_fingerprint(),
            )

    def _secret_fingerprint(self) -> str:
        """Return a stable fingerprint for the current secret without exposing it."""
        digest = hashlib.sha256(self.secret_key.encode()).hexdigest()
        return f"sha256:{digest[:12]}"

    def get_secret_fingerprint(self) -> str:
        """Public accessor for the JWT secret fingerprint."""
        return self._secret_fingerprint()

    def _load_token_store(self) -> None:
        """Load token-group mappings from disk (no-op for in-memory mode)"""
        # Skip file I/O for in-memory mode
        if self._use_memory_store:
            self.logger.debug("In-memory mode: skipping token store load")
            return

        # Type assertion: token_store_path is not None when not in memory mode
        assert (
            self.token_store_path is not None
        ), "token_store_path must be set when not using memory mode"

        # ALWAYS log to verify this is being called
        self.logger.info(
            f"_load_token_store called, path={self.token_store_path}, exists={self.token_store_path.exists()}"
        )
        if self.token_store_path.exists():
            try:
                with open(self.token_store_path, "r") as f:
                    self.token_store = json.load(f)
                sample_tokens = list(self.token_store.keys())[:2]
                preview = [f"{token[:12]}..." for token in sample_tokens]
                self.logger.info(
                    "Token store loaded",
                    path=str(self.token_store_path),
                    tokens_count=len(self.token_store),
                    token_preview=preview,
                )
            except Exception as e:
                self.logger.error("Failed to load token store", error=str(e))
                self.token_store = {}
        else:
            self.token_store = {}
            self.logger.debug("Token store initialized as empty", path=str(self.token_store_path))

    def _save_token_store(self) -> None:
        """Save token-group mappings to disk (no-op for in-memory mode)"""
        # Skip file I/O for in-memory mode
        if self._use_memory_store:
            self.logger.debug(
                "In-memory mode: skipping token store save", tokens_count=len(self.token_store)
            )
            return

        # Type assertion: token_store_path is not None when not in memory mode
        assert (
            self.token_store_path is not None
        ), "token_store_path must be set when not using memory mode"

        try:
            self.token_store_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_store_path, "w") as f:
                json.dump(self.token_store, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            self.logger.debug("Token store saved", tokens_count=len(self.token_store))
        except Exception as e:
            self.logger.error("Failed to save token store", error=str(e))
            raise

    def create_token(
        self,
        group: str,
        expires_in_seconds: int = 2592000,
        fingerprint: Optional[str] = None,
        token_id: Optional[str] = None,
    ) -> str:
        """
        Create a new JWT token for a group with enhanced security features

        Args:
            group: The group name to associate with this token
            expires_in_seconds: Number of seconds until token expires (default: 2592000 = 30 days)
            fingerprint: Optional device/client fingerprint for binding (e.g., hash of user-agent + IP)
            token_id: Optional unique token identifier (jti) for revocation tracking

        Returns:
            JWT token string
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=expires_in_seconds)
        not_before = now  # Token valid immediately

        payload = {
            "group": group,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "nbf": int(not_before.timestamp()),  # Not before timestamp
            "aud": "gplot-api",  # Audience claim
        }

        # Add optional claims for enhanced security
        if token_id:
            payload["jti"] = token_id  # JWT ID for revocation tracking
        if fingerprint:
            payload["fp"] = fingerprint  # Device fingerprint for binding

        token = jwt.encode(payload, self.secret_key, algorithm="HS256")

        # Store token-group mapping with enhanced metadata
        token_metadata = {
            "group": group,
            "issued_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "not_before": not_before.isoformat(),
        }
        if token_id:
            token_metadata["jti"] = token_id
        if fingerprint:
            token_metadata["fingerprint"] = fingerprint

        self.token_store[token] = token_metadata
        self._save_token_store()

        self.logger.info(
            "Token created",
            group=group,
            expires_at=expires_at.isoformat(),
            expires_in_seconds=expires_in_seconds,
        )

        return token

    def verify_token(self, token: str, fingerprint: Optional[str] = None) -> TokenInfo:
        """
        Verify a JWT token with enhanced security checks

        Args:
            token: JWT token string
            fingerprint: Optional device/client fingerprint to verify against token binding

        Returns:
            TokenInfo with group and expiry information

        Raises:
            ValueError: If token is invalid, expired, or security checks fail
        """
        self.logger.info(f"verify_token called with token={token[:20]}...")
        try:
            # Reload token store to get latest tokens created by admin
            self.logger.info("About to call _load_token_store from verify_token")
            self._load_token_store()
            self.logger.info(
                f"After _load_token_store, token_store has {len(self.token_store)} tokens"
            )

            # Decode and verify token with enhanced options
            # jwt.decode automatically validates exp, nbf if present
            # Don't require audience - it's optional for backward compatibility
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=["HS256"],
                options={
                    "verify_exp": True,  # Verify expiration
                    "verify_nbf": True,  # Verify not-before (if present)
                    "verify_iat": True,  # Verify issued-at
                    "verify_aud": False,  # Don't require audience (backward compat)
                },
            )

            # Validate required claims
            group = payload.get("group")
            if not group:
                self.logger.error("Token missing group claim")
                raise ValueError("Token missing group claim")

            # Validate audience if present (optional for backward compatibility)
            if "aud" in payload and payload["aud"] != "gplot-api":
                self.logger.error("Token audience mismatch", aud=payload["aud"])
                raise ValueError("Token audience mismatch")

            # Validate fingerprint if token has one and fingerprint provided
            if "fp" in payload:
                stored_fp = payload["fp"]
                if fingerprint and stored_fp != fingerprint:
                    self.logger.warning(
                        "Token fingerprint mismatch",
                        group=group,
                        expected=stored_fp[:12],
                        actual=fingerprint[:12] if fingerprint else None,
                    )
                    raise ValueError("Token fingerprint mismatch - possible token theft")

            # Check if token is in our store (REQUIRED - admin must pre-create tokens)
            if token not in self.token_store:
                self.logger.warning("Token not found in store", group=group)
                raise ValueError("Token not found in token store. Tokens must be created by admin.")

            # Verify token metadata matches
            stored_metadata = self.token_store[token]
            if stored_metadata["group"] != group:
                self.logger.error(
                    "Token group mismatch",
                    stored_group=stored_metadata["group"],
                    token_group=group,
                )
                raise ValueError("Token group mismatch in store")

            issued_at = datetime.fromtimestamp(payload["iat"])
            expires_at = datetime.fromtimestamp(payload["exp"])

            self.logger.debug("Token verified", group=group, expires_at=expires_at.isoformat())

            return TokenInfo(token=token, group=group, expires_at=expires_at, issued_at=issued_at)

        except jwt.ExpiredSignatureError:
            self.logger.warning("Token expired")
            raise ValueError("Token has expired")
        except jwt.ImmatureSignatureError:
            self.logger.warning("Token not yet valid (nbf)")
            raise ValueError("Token not yet valid")
        except jwt.InvalidTokenError as e:
            self.logger.error("Invalid token", error=str(e))
            raise ValueError(f"Invalid token: {str(e)}")

    def revoke_token(self, token: str) -> None:
        """
        Revoke a token by removing it from the store

        Args:
            token: JWT token string to revoke
        """
        # Reload to get latest state
        self._load_token_store()

        if token in self.token_store:
            group = self.token_store[token]["group"]
            del self.token_store[token]
            self._save_token_store()
            self.logger.info("Token revoked", group=group)
        else:
            self.logger.warning("Token not found for revocation")

    def list_tokens(self) -> Dict[str, Dict]:
        """
        List all tokens in the store

        Returns:
            Dictionary of token -> token info
        """
        # Reload to get latest state from shared store
        self._load_token_store()
        return self.token_store.copy()

    def get_group_for_token(self, token: str) -> str:
        """
        Get the group associated with a token

        Args:
            token: JWT token string

        Returns:
            Group name

        Raises:
            ValueError: If token is invalid
        """
        token_info = self.verify_token(token)
        return token_info.group
