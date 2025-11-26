"""Tests for unified settings system (Phase 1)

Validates the new app.settings module and its typed configuration classes.
"""

import pytest
from app.settings import (
    Settings,
    ServerSettings,
    AuthSettings,
    StorageSettings,
    LogSettings,
    get_settings,
    reset_settings,
)


def test_server_settings_defaults():
    """Test ServerSettings has correct defaults"""
    settings = ServerSettings()
    assert settings.host == "0.0.0.0"
    # Test hardcoded defaults (backward compatibility)
    assert settings.mcp_port == 8001
    assert settings.web_port == 8000
    assert settings.mcpo_port == 8002


def test_server_settings_from_env(monkeypatch):
    """Test ServerSettings loads from environment variables"""
    monkeypatch.setenv("GPLOT_HOST", "127.0.0.1")
    monkeypatch.setenv("GPLOT_MCP_PORT", "9001")
    monkeypatch.setenv("GPLOT_WEB_PORT", "9000")

    settings = ServerSettings.from_env()
    assert settings.host == "127.0.0.1"
    assert settings.mcp_port == 9001
    assert settings.web_port == 9000


def test_auth_settings_requires_secret_when_enabled():
    """Test AuthSettings validates JWT secret requirement"""
    with pytest.raises(ValueError, match="JWT secret is required"):
        AuthSettings(jwt_secret=None, require_auth=True)


def test_auth_settings_allows_no_secret_when_disabled():
    """Test AuthSettings allows missing secret when auth disabled"""
    settings = AuthSettings(jwt_secret=None, require_auth=False)
    assert settings.jwt_secret is None
    assert settings.require_auth is False


def test_auth_settings_secret_fingerprint():
    """Test AuthSettings generates secret fingerprint"""
    settings = AuthSettings(jwt_secret="test-secret", require_auth=True)
    fingerprint = settings.get_secret_fingerprint()
    assert fingerprint.startswith("sha256:")
    assert len(fingerprint) == 19  # "sha256:" + 12 hex chars


def test_storage_settings_from_env(monkeypatch, tmp_path):
    """Test StorageSettings loads from environment"""
    test_data_dir = tmp_path / "test_data"
    monkeypatch.setenv("GPLOT_DATA_DIR", str(test_data_dir))

    settings = StorageSettings.from_env()
    assert settings.data_dir == test_data_dir
    assert settings.storage_dir == test_data_dir / "storage"
    assert settings.auth_dir == test_data_dir / "auth"


def test_storage_settings_ensure_directories(tmp_path):
    """Test StorageSettings creates directories"""
    test_data_dir = tmp_path / "test_data"
    settings = StorageSettings(
        data_dir=test_data_dir,
        storage_dir=test_data_dir / "storage",
        auth_dir=test_data_dir / "auth",
    )

    # Directories don't exist yet
    assert not test_data_dir.exists()

    # Create them
    settings.ensure_directories()

    # Now they exist
    assert test_data_dir.exists()
    assert settings.storage_dir.exists()
    assert settings.auth_dir.exists()


def test_settings_from_env_with_auth(monkeypatch):
    """Test Settings loads complete configuration"""
    monkeypatch.setenv("GPLOT_JWT_SECRET", "test-secret-key")
    monkeypatch.setenv("GPLOT_MCP_PORT", "9001")

    settings = Settings.from_env(require_auth=True)
    assert settings.auth.jwt_secret == "test-secret-key"
    assert settings.server.mcp_port == 9001


def test_settings_from_env_without_auth(monkeypatch):
    """Test Settings works without JWT secret when auth disabled"""
    # No JWT secret set
    monkeypatch.delenv("GPLOT_JWT_SECRET", raising=False)

    settings = Settings.from_env(require_auth=False)
    assert settings.auth.require_auth is False


def test_settings_resolve_defaults(tmp_path, monkeypatch):
    """Test Settings resolves missing defaults"""
    monkeypatch.setenv("GPLOT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("GPLOT_JWT_SECRET", "test-secret")
    # Clear token store env var to test default resolution
    monkeypatch.delenv("GPLOT_TOKEN_STORE", raising=False)

    settings = Settings.from_env(require_auth=True)
    assert settings.auth.token_store_path is None  # Not set yet

    settings.resolve_defaults()

    # Now resolved to default location
    assert settings.auth.token_store_path == tmp_path / "auth" / "tokens.json"


def test_get_settings_singleton(monkeypatch):
    """Test get_settings returns singleton instance"""
    reset_settings()
    monkeypatch.setenv("GPLOT_JWT_SECRET", "test-secret")

    settings1 = get_settings(require_auth=True)
    settings2 = get_settings(require_auth=True)

    # Same instance
    assert settings1 is settings2


def test_get_settings_reload(monkeypatch):
    """Test get_settings can reload configuration"""
    reset_settings()
    monkeypatch.setenv("GPLOT_JWT_SECRET", "secret1")
    monkeypatch.setenv("GPLOT_MCP_PORT", "9001")

    settings1 = get_settings(require_auth=True)
    assert settings1.server.mcp_port == 9001

    # Change environment
    monkeypatch.setenv("GPLOT_MCP_PORT", "9002")

    # Reload
    settings2 = get_settings(reload=True, require_auth=True)
    assert settings2.server.mcp_port == 9002


def test_log_settings_from_env(monkeypatch):
    """Test LogSettings loads from environment"""
    monkeypatch.setenv("GPLOT_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("GPLOT_LOG_FORMAT", "json")

    settings = LogSettings.from_env()
    assert settings.level == "DEBUG"
    assert settings.format == "json"


def test_backward_compatibility_config_class(tmp_path):
    """Test Config class maintains backward compatibility"""
    from app.config import Config

    # Test mode functionality
    Config.set_test_mode(tmp_path)
    assert Config.is_test_mode()
    assert Config.get_data_dir() == tmp_path
    assert Config.get_storage_dir() == tmp_path / "storage"
    assert Config.get_auth_dir() == tmp_path / "auth"
    assert Config.get_token_store_path() == tmp_path / "auth" / "tokens.json"

    Config.clear_test_mode()
    assert not Config.is_test_mode()


def test_backward_compatibility_functions():
    """Test legacy convenience functions still work"""
    from app.config import get_default_storage_dir, get_default_token_store_path

    storage_dir = get_default_storage_dir()
    token_store = get_default_token_store_path()

    assert isinstance(storage_dir, str)
    assert isinstance(token_store, str)
    assert "storage" in storage_dir
    assert "tokens.json" in token_store
