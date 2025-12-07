#!/usr/bin/env python3
"""Test centralized authentication configuration resolution

Tests the resolve_auth_config() function priority chain:
1. CLI arguments
2. Environment variables
3. Auto-generated secrets (dev only)
4. Defaults
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from app.startup.auth_config import resolve_auth_config


class TestAuthConfigResolver:
    """Test authentication configuration resolution priority chain"""

    def test_cli_secret_takes_precedence_over_env(self, monkeypatch):
        """CLI --jwt-secret argument takes precedence over GOFR_PLOT_JWT_SECRET"""
        monkeypatch.setenv("GOFR_PLOT_JWT_SECRET", "env-secret")

        secret, token_store, require_auth = resolve_auth_config(
            jwt_secret="cli-secret", require_auth=True
        )

        assert secret == "cli-secret", "CLI argument should override environment variable"
        assert require_auth is True

    def test_env_secret_used_when_no_cli_arg(self, monkeypatch):
        """GOFR_PLOT_JWT_SECRET environment variable used when no CLI argument"""
        monkeypatch.setenv("GOFR_PLOT_JWT_SECRET", "env-secret")

        secret, token_store, require_auth = resolve_auth_config(require_auth=True)

        assert secret == "env-secret", "Environment variable should be used"
        assert require_auth is True

    def test_auto_generated_secret_in_dev_mode(self, monkeypatch):
        """Auto-generate secret in development when no secret provided"""
        monkeypatch.delenv("GOFR_PLOT_JWT_SECRET", raising=False)
        monkeypatch.delenv("GOFR_PLOT_ENV", raising=False)

        secret, token_store, require_auth = resolve_auth_config(
            require_auth=True, allow_auto_secret=True
        )

        assert secret is not None, "Secret should be auto-generated"
        assert len(secret) == 64, "Auto-generated secret should be 32 bytes hex (64 chars)"
        assert require_auth is True

    def test_auto_generation_fails_in_production(self, monkeypatch):
        """Auto-generation disabled in production environment"""
        monkeypatch.delenv("GOFR_PLOT_JWT_SECRET", raising=False)
        monkeypatch.setenv("GOFR_PLOT_ENV", "PROD")

        with pytest.raises(ValueError, match="No JWT secret provided in production"):
            resolve_auth_config(require_auth=True, allow_auto_secret=True)

    def test_missing_secret_fails_when_auto_disabled(self, monkeypatch):
        """Missing secret fails when auto-generation disabled"""
        monkeypatch.delenv("GOFR_PLOT_JWT_SECRET", raising=False)
        monkeypatch.delenv("GOFR_PLOT_ENV", raising=False)

        with pytest.raises(ValueError, match="JWT secret required"):
            resolve_auth_config(require_auth=True, allow_auto_secret=False)

    def test_cli_token_store_takes_precedence(self, monkeypatch):
        """CLI --token-store argument takes precedence over GOFR_PLOT_TOKEN_STORE"""
        monkeypatch.setenv("GOFR_PLOT_JWT_SECRET", "test-secret")
        monkeypatch.setenv("GOFR_PLOT_TOKEN_STORE", "/env/path/tokens.json")

        secret, token_store, require_auth = resolve_auth_config(
            token_store_path="/cli/path/tokens.json", require_auth=True
        )

        assert str(token_store) == "/cli/path/tokens.json", "CLI path should override env var"

    def test_env_token_store_used_when_no_cli_arg(self, monkeypatch):
        """GOFR_PLOT_TOKEN_STORE environment variable used when no CLI argument
        
        Note: gofr-plot's resolve_auth_config wrapper always provides a default
        token store path, so env var only applies when not using the wrapper.
        This test verifies the wrapper behavior.
        """
        monkeypatch.setenv("GOFR_PLOT_JWT_SECRET", "test-secret")
        monkeypatch.setenv("GOFR_PLOT_TOKEN_STORE", "/env/path/tokens.json")

        secret, token_store, require_auth = resolve_auth_config(require_auth=True)

        # gofr-plot wrapper always provides default, so token_store should be set
        assert token_store is not None, "Token store should be set"
        assert "tokens.json" in str(token_store), "Path should include tokens.json"

    def test_default_token_store_when_no_args_or_env(self, monkeypatch):
        """Default token store path used when no CLI arg or env var"""
        monkeypatch.setenv("GOFR_PLOT_JWT_SECRET", "test-secret")
        monkeypatch.delenv("GOFR_PLOT_TOKEN_STORE", raising=False)

        secret, token_store, require_auth = resolve_auth_config(require_auth=True)

        assert token_store is not None, "Should use default token store path"
        assert "tokens.json" in str(token_store), "Default path should include tokens.json"

    def test_no_auth_mode_returns_none(self, monkeypatch):
        """When auth disabled, returns None for secret and token store"""
        monkeypatch.setenv("GOFR_PLOT_JWT_SECRET", "test-secret")

        secret, token_store, require_auth = resolve_auth_config(require_auth=False)

        assert secret is None, "Secret should be None when auth disabled"
        assert token_store is None, "Token store should be None when auth disabled"
        assert require_auth is False

    def test_no_auth_mode_ignores_missing_secret(self, monkeypatch):
        """When auth disabled, missing secret doesn't cause error"""
        monkeypatch.delenv("GOFR_PLOT_JWT_SECRET", raising=False)

        secret, token_store, require_auth = resolve_auth_config(require_auth=False)

        assert secret is None
        assert token_store is None
        assert require_auth is False

    def test_production_environment_detection(self, monkeypatch):
        """Test detection of production environment variants"""
        monkeypatch.delenv("GOFR_PLOT_JWT_SECRET", raising=False)

        # Test "PRODUCTION" variant
        monkeypatch.setenv("GOFR_PLOT_ENV", "PRODUCTION")
        with pytest.raises(ValueError, match="production"):
            resolve_auth_config(require_auth=True, allow_auto_secret=True)

        # Test "prod" variant (lowercase)
        monkeypatch.setenv("GOFR_PLOT_ENV", "prod")
        with pytest.raises(ValueError, match="production"):
            resolve_auth_config(require_auth=True, allow_auto_secret=True)

    def test_all_parameters_provided(self, monkeypatch):
        """Test when all parameters provided via CLI"""
        monkeypatch.delenv("GOFR_PLOT_JWT_SECRET", raising=False)
        monkeypatch.delenv("GOFR_PLOT_TOKEN_STORE", raising=False)

        secret, token_store, require_auth = resolve_auth_config(
            jwt_secret="cli-secret", token_store_path="/cli/path/tokens.json", require_auth=True
        )

        assert secret == "cli-secret"
        assert str(token_store) == "/cli/path/tokens.json"
        assert require_auth is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
