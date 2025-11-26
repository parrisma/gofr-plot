"""Tests for MCP list_images tool

Phase 4: Discovery tool tests for listing stored images
"""

import pytest
from unittest.mock import MagicMock
from app.mcp_server.mcp_server import (
    _handle_list_images,
    storage,
    set_auth_service,
)
from app.auth import AuthService, TokenInfo
from datetime import datetime, timedelta


def get_text_content(result: list) -> str:
    """Extract text from result, handling union types"""
    if result and hasattr(result[0], "text"):
        return result[0].text  # type: ignore[union-attr]
    return str(result[0]) if result else ""


@pytest.fixture
def mock_auth_service():
    """Create a mock auth service"""
    service = MagicMock(spec=AuthService)
    return service


@pytest.fixture
def valid_token_info():
    """Create valid token info for testing"""
    return TokenInfo(
        token="test-token",
        group="testgroup",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        issued_at=datetime.utcnow(),
    )


class TestListImagesTool:
    """Tests for list_images MCP tool"""

    def test_list_images_requires_token(self, mock_auth_service):
        """list_images requires authentication token"""
        set_auth_service(mock_auth_service)

        result = _handle_list_images({}, client_id="test-client")

        # Should return auth required error
        assert len(result) == 1
        text = get_text_content(result)
        assert "Authentication" in text
        assert "token" in text.lower()

    def test_list_images_rejects_invalid_token(self, mock_auth_service):
        """list_images rejects invalid tokens"""
        mock_auth_service.verify_token.side_effect = Exception("Invalid token")
        set_auth_service(mock_auth_service)

        result = _handle_list_images({"token": "invalid-token"}, client_id="test-client")

        # Should return auth invalid error
        assert len(result) == 1
        text = get_text_content(result)
        assert "invalid" in text.lower() or "authentication" in text.lower()

    def test_list_images_empty_group(self, mock_auth_service, valid_token_info):
        """list_images returns message when no images in group"""
        mock_auth_service.verify_token.return_value = valid_token_info
        set_auth_service(mock_auth_service)

        # Clear any existing images
        for guid in storage.list_images(group="testgroup"):
            storage.delete_image(guid, group="testgroup")

        result = _handle_list_images({"token": "valid-token"}, client_id="test-client")

        assert len(result) == 1
        text = get_text_content(result)
        assert "no images" in text.lower()
        assert "testgroup" in text

    def test_list_images_returns_guids(self, mock_auth_service, valid_token_info):
        """list_images returns stored GUIDs"""
        mock_auth_service.verify_token.return_value = valid_token_info
        set_auth_service(mock_auth_service)

        # Store some test images
        guid1 = storage.save_image(b"\x89PNG\r\n\x1a\n", "png", group="testgroup")
        guid2 = storage.save_image(b"\x89PNG\r\n\x1a\n", "png", group="testgroup")

        try:
            result = _handle_list_images({"token": "valid-token"}, client_id="test-client")

            assert len(result) == 1
            text = get_text_content(result)
            assert guid1 in text
            assert guid2 in text
            assert "testgroup" in text
            assert "2" in text  # count
        finally:
            # Cleanup
            storage.delete_image(guid1, group="testgroup")
            storage.delete_image(guid2, group="testgroup")

    def test_list_images_shows_aliases(self, mock_auth_service, valid_token_info):
        """list_images includes alias info when available"""
        mock_auth_service.verify_token.return_value = valid_token_info
        set_auth_service(mock_auth_service)

        # Store image with alias
        guid = storage.save_image(b"\x89PNG\r\n\x1a\n", "png", group="testgroup")
        storage.register_alias("my-test-alias", guid, "testgroup")

        try:
            result = _handle_list_images({"token": "valid-token"}, client_id="test-client")

            assert len(result) == 1
            text = get_text_content(result)
            assert guid in text
            assert "my-test-alias" in text
            assert "alias" in text.lower()
        finally:
            # Cleanup
            storage.unregister_alias("my-test-alias", "testgroup")
            storage.delete_image(guid, group="testgroup")

    def test_list_images_group_isolation(self, mock_auth_service):
        """list_images only shows images from token's group"""
        # Store image in group1
        guid_group1 = storage.save_image(b"\x89PNG\r\n\x1a\n", "png", group="group1")
        # Store image in group2
        guid_group2 = storage.save_image(b"\x89PNG\r\n\x1a\n", "png", group="group2")

        # Token for group1
        token_info_group1 = TokenInfo(
            token="token1",
            group="group1",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            issued_at=datetime.utcnow(),
        )
        mock_auth_service.verify_token.return_value = token_info_group1
        set_auth_service(mock_auth_service)

        try:
            result = _handle_list_images({"token": "token1"}, client_id="test-client")

            text = get_text_content(result)
            # Should see group1 image
            assert guid_group1 in text
            # Should NOT see group2 image
            assert guid_group2 not in text
        finally:
            # Cleanup
            storage.delete_image(guid_group1, group="group1")
            storage.delete_image(guid_group2, group="group2")

    def test_list_images_includes_usage_hint(self, mock_auth_service, valid_token_info):
        """list_images response includes usage instructions"""
        mock_auth_service.verify_token.return_value = valid_token_info
        set_auth_service(mock_auth_service)

        # Store test image
        guid = storage.save_image(b"\x89PNG\r\n\x1a\n", "png", group="testgroup")

        try:
            result = _handle_list_images({"token": "valid-token"}, client_id="test-client")

            text = get_text_content(result)
            # Should include usage hint
            assert "get_image" in text
        finally:
            storage.delete_image(guid, group="testgroup")


class TestListImagesIntegration:
    """Integration tests for list_images via live server"""

    @pytest.fixture
    def test_auth_service(self, tmp_path):
        """Create real auth service for integration tests"""
        token_store = tmp_path / "tokens.json"
        return AuthService(secret_key="test-secret-key", token_store_path=str(token_store))

    def test_list_images_with_real_auth(self, test_auth_service):
        """list_images works with real authentication"""
        set_auth_service(test_auth_service)

        # Create real token
        token = test_auth_service.create_token(group="integration-test", expires_in_seconds=60)

        # Store an image
        guid = storage.save_image(b"\x89PNG\r\n\x1a\n", "png", group="integration-test")

        try:
            result = _handle_list_images({"token": token}, client_id="test-client")

            text = get_text_content(result)
            assert guid in text
            assert "integration-test" in text
        finally:
            storage.delete_image(guid, group="integration-test")
            test_auth_service.revoke_token(token)
