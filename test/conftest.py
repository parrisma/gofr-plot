"""Pytest configuration and fixtures

Provides shared fixtures for all tests, including temporary data directories.
"""

import sys
from pathlib import Path

# Add project root to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import os
from app.config import Config
from app.storage import reset_storage, get_storage
from app.auth import AuthService

# Test server configuration - reads from environment (set by run_tests.sh)
MCP_PORT = int(os.environ.get("GPLOT_MCP_PORT", "8010"))
WEB_PORT = int(os.environ.get("GPLOT_WEB_PORT", "8012"))
MCPO_PORT = int(os.environ.get("GPLOT_MCPO_PORT", "8011"))

# Test URL constants
MCP_URL = f"http://localhost:{MCP_PORT}/mcp/"
WEB_URL = f"http://localhost:{WEB_PORT}"
MCPO_URL = f"http://localhost:{MCPO_PORT}"


@pytest.fixture(scope="function", autouse=True)
def test_data_dir(tmp_path):
    """
    Automatically provide a temporary data directory for each test

    This fixture:
    - Creates a unique temporary directory for each test
    - Configures app.config to use this directory
    - Cleans up after the test completes
    - Resets storage singleton to ensure fresh state
    - Purges all images from storage after test
    """
    # Set up test mode with temporary directory
    test_dir = tmp_path / "gplot_test_data"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (test_dir / "storage").mkdir(exist_ok=True)
    (test_dir / "auth").mkdir(exist_ok=True)

    # Configure for testing
    Config.set_test_mode(test_dir)

    # Reset storage singleton to ensure tests get fresh storage with test directory
    reset_storage()

    yield test_dir

    # Cleanup: Purge all images from storage
    try:
        storage = get_storage()
        storage.purge(age_days=0)  # Delete all images
    except Exception:
        pass  # Ignore errors during cleanup

    Config.clear_test_mode()
    reset_storage()  # Reset storage after test


@pytest.fixture(scope="function")
def temp_storage_dir(tmp_path):
    """
    Provide a temporary storage directory for specific tests that need it.
    Returns string path for compatibility with storage tests.

    Returns:
        str: Path to temporary storage directory
    """
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return str(storage_dir)


@pytest.fixture(scope="function")
def temp_auth_dir(tmp_path):
    """
    Provide a temporary auth directory for specific tests that need it

    Returns:
        Path object pointing to temporary auth directory
    """
    auth_dir = tmp_path / "auth"
    auth_dir.mkdir(parents=True, exist_ok=True)
    return auth_dir


@pytest.fixture(scope="session")
def test_auth_service():
    """
    Create an AuthService instance for testing with a shared token store

        Uses the same secret and token store as run_tests.sh and launch.json.
        The servers must be started with:
            GPLOT_JWT_SECRET="test-secret-key-for-secure-testing-do-not-use-in-production" (override via env)
            GPLOT_DATA_DIR="<workspace>/test/data"

    Returns:
        AuthService: Configured auth service for testing
    """

    test_secret = os.environ.get(
        "GPLOT_JWT_SECRET", "test-secret-key-for-secure-testing-do-not-use-in-production"
    )
    token_store_path = os.environ.get("GPLOT_TOKEN_STORE", "/tmp/gplot_test_tokens.json")

    auth_service = AuthService(secret_key=test_secret, token_store_path=str(token_store_path))
    return auth_service


@pytest.fixture(scope="function")
def test_jwt_token(test_auth_service):
    """
    Provide a valid JWT token for tests that require authentication.
    Token is created at test start and revoked at test end.

    Returns:
        str: A valid JWT token for testing
    """
    # Create token
    token = test_auth_service.create_token(group="test_group", expires_in_seconds=3600)

    yield token

    # Cleanup: revoke token after test
    try:
        test_auth_service.revoke_token(token)
    except Exception:
        pass  # Token may already be revoked or expired


@pytest.fixture(scope="function")
def test_token(test_auth_service):
    """
    Create a test token for the 'secure' group with 90 second expiry.
    Compatible with authentication tests that expect this fixture name.

    Returns:
        str: A valid JWT token for the 'secure' group
    """
    token = test_auth_service.create_token(group="secure", expires_in_seconds=90)
    return token


@pytest.fixture(scope="function")
def invalid_token():
    """
    Create a token with wrong secret to test authentication failure.
    This token will have correct format but wrong signature.

    Returns:
        str: An invalid JWT token for testing auth failures
    """
    fake_service = AuthService(
        secret_key="wrong-secret-key", token_store_path="/tmp/fake_store.json"
    )
    return fake_service.create_token(group="fake", expires_in_seconds=60)


@pytest.fixture(scope="function")
def logger():
    """
    Provide a ConsoleLogger instance for test logging.
    Reusable across all test files.

    Returns:
        ConsoleLogger: Logger configured for testing
    """
    import logging
    from app.logger import ConsoleLogger

    return ConsoleLogger(name="test", level=logging.INFO)
