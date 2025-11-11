#!/usr/bin/env python3
"""Test JWT authentication for both MCP and Web servers"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncio
import pytest
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from app.auth import AuthService
from app.logger import ConsoleLogger
import logging
import os
import tempfile


# Test configuration
TEST_GROUP = "secure"
TEST_EXPIRY_SECONDS = 90
TEST_JWT_SECRET = "test-secret-key-for-auth-testing"
SHARED_TOKEN_STORE = "/tmp/gplot_test_tokens.json"  # Shared with servers (must match launch.json)
MCP_URL = "http://localhost:8001/mcp/"
WEB_URL = "http://localhost:8000"


@pytest.fixture
def auth_service():
    """Create an auth service using the shared token store that servers use"""
    service = AuthService(secret_key=TEST_JWT_SECRET, token_store_path=SHARED_TOKEN_STORE)
    yield service


@pytest.fixture
def test_token(auth_service):
    """Create a test token for the 'secure' group with 90 second expiry in shared store"""
    token = auth_service.create_token(group=TEST_GROUP, expires_in_seconds=TEST_EXPIRY_SECONDS)
    return token


@pytest.fixture
def invalid_token():
    """Create a token with wrong secret to test authentication failure"""
    # This token will have correct format but wrong signature
    fake_service = AuthService(
        secret_key="wrong-secret-key", token_store_path="/tmp/fake_store.json"
    )
    return fake_service.create_token(group="fake", expires_in_seconds=60)


class TestAuthTokenCreation:
    """Test 1: Create an auth token for group 'secure' with 90 second expiry"""

    def test_create_token(self, auth_service):
        """Test token creation with correct parameters"""
        logger = ConsoleLogger(name="auth_test", level=logging.INFO)
        logger.info(
            "Test 1: Creating auth token", group=TEST_GROUP, expiry_seconds=TEST_EXPIRY_SECONDS
        )

        token = auth_service.create_token(group=TEST_GROUP, expires_in_seconds=TEST_EXPIRY_SECONDS)

        # Verify token is created
        assert token is not None, "Token should not be None"
        assert isinstance(token, str), "Token should be a string"
        assert len(token) > 0, "Token should not be empty"

        logger.info("Token created successfully", token_length=len(token))

        # Verify token can be validated
        token_info = auth_service.verify_token(token)
        assert (
            token_info.group == TEST_GROUP
        ), f"Group mismatch: expected {TEST_GROUP}, got {token_info.group}"

        # Verify expiry is correct (within 1 second tolerance)
        from datetime import datetime

        now = datetime.utcnow()
        expiry_delta = (token_info.expires_at - now).total_seconds()
        assert (
            abs(expiry_delta - TEST_EXPIRY_SECONDS) < 2
        ), f"Expiry mismatch: expected ~{TEST_EXPIRY_SECONDS}s, got {expiry_delta}s"

        logger.info("Token validation passed", group=token_info.group, expires_in=expiry_delta)
        logger.info("✓ Test 1 passed: Token created successfully")


class TestMCPAuthentication:
    """Test 2: Create graph via MCP and test it's only available with token"""

    @pytest.mark.asyncio
    async def test_mcp_render_with_valid_token(self, test_token):
        """Test rendering a graph via MCP with valid token"""
        logger = ConsoleLogger(name="mcp_auth_test", level=logging.INFO)
        logger.info("Test 2a: Testing MCP render with valid token")

        async with streamablehttp_client(MCP_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                logger.info("MCP session initialized")

                # Render a graph with valid token in proxy mode
                result = await session.call_tool(
                    "render_graph",
                    arguments={
                        "title": "Auth Test Graph",
                        "x": [1, 2, 3, 4, 5],
                        "y": [2, 4, 6, 8, 10],
                        "token": test_token,
                        "proxy": True,  # Get GUID back
                    },
                )

                # Verify response
                assert len(result.content) > 0, "No content returned"
                text_content = result.content[0]
                assert hasattr(text_content, "text"), "Response is not text"

                response_text = text_content.text  # type: ignore
                logger.info("MCP render response", response=response_text[:100])

                # Should get a GUID back (proxy mode)
                assert "Error" not in response_text, f"Render failed: {response_text}"

                # Extract GUID from response (assuming format like "Image saved with GUID: xxx")
                import re

                guid_match = re.search(
                    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", response_text
                )
                assert guid_match is not None, f"No GUID found in response: {response_text}"

                guid = guid_match.group(0)
                logger.info("Graph rendered successfully via MCP", guid=guid)

                return guid  # Return for use in retrieval test

    @pytest.mark.asyncio
    async def test_mcp_render_without_token(self):
        """Test that rendering fails without a token"""
        logger = ConsoleLogger(name="mcp_auth_test", level=logging.INFO)
        logger.info("Test 2b: Testing MCP render without token (should fail)")

        async with streamablehttp_client(MCP_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Try to render without token
                result = await session.call_tool(
                    "render_graph",
                    arguments={
                        "title": "Auth Test Graph",
                        "x": [1, 2, 3],
                        "y": [4, 5, 6],
                        # No token provided
                    },
                )

                # Should get an error
                text_content = result.content[0]
                response_text = text_content.text  # type: ignore

                assert (
                    "Missing required argument" in response_text or "token" in response_text.lower()
                ), "Should require token"

                logger.info("✓ MCP correctly rejects request without token")

    @pytest.mark.asyncio
    async def test_mcp_render_with_invalid_token(self, invalid_token):
        """Test that rendering fails with invalid token"""
        logger = ConsoleLogger(name="mcp_auth_test", level=logging.INFO)
        logger.info("Test 2c: Testing MCP render with invalid token (should fail)")

        async with streamablehttp_client(MCP_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Try to render with invalid token
                result = await session.call_tool(
                    "render_graph",
                    arguments={
                        "title": "Auth Test Graph",
                        "x": [1, 2, 3],
                        "y": [4, 5, 6],
                        "token": invalid_token,
                    },
                )

                # Should get an authentication error
                text_content = result.content[0]
                response_text = text_content.text  # type: ignore

                assert (
                    "Authentication Error" in response_text or "Invalid token" in response_text
                ), f"Should reject invalid token, got: {response_text}"

                logger.info("✓ MCP correctly rejects invalid token")

    @pytest.mark.asyncio
    async def test_mcp_get_image_with_valid_token(self, test_token):
        """Test retrieving an image via MCP with valid token"""
        logger = ConsoleLogger(name="mcp_auth_test", level=logging.INFO)
        logger.info("Test 2d: Testing MCP get_image with valid token")

        async with streamablehttp_client(MCP_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # First create an image
                result = await session.call_tool(
                    "render_graph",
                    arguments={
                        "title": "Retrieval Test",
                        "x": [1, 2, 3],
                        "y": [4, 5, 6],
                        "token": test_token,
                        "proxy": True,
                    },
                )

                response_text = result.content[0].text  # type: ignore
                import re

                guid_match = re.search(
                    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", response_text
                )
                assert guid_match is not None, f"No GUID found in response: {response_text}"
                guid = guid_match.group(0)

                logger.info("Image created", guid=guid)

                # Now retrieve it with the same token
                result = await session.call_tool(
                    "get_image",
                    arguments={
                        "guid": guid,
                        "token": test_token,
                    },
                )

                # Should successfully retrieve image
                assert len(result.content) > 0, "No content returned"

                # Check for image content
                has_image = any(hasattr(content, "data") for content in result.content)
                assert has_image, "No image data in response"

                logger.info("✓ Image retrieved successfully via MCP with valid token")

    @pytest.mark.asyncio
    async def test_mcp_get_image_with_different_group_token(self, auth_service, test_token):
        """Test that retrieving an image fails with token from different group"""
        logger = ConsoleLogger(name="mcp_auth_test", level=logging.INFO)
        logger.info("Test 2e: Testing MCP get_image with different group token (should fail)")

        # Create a token for a different group
        other_token = auth_service.create_token(group="other-group", expires_in_seconds=90)

        async with streamablehttp_client(MCP_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Create an image with 'secure' group token
                result = await session.call_tool(
                    "render_graph",
                    arguments={
                        "title": "Group Test",
                        "x": [1, 2, 3],
                        "y": [4, 5, 6],
                        "token": test_token,
                        "proxy": True,
                    },
                )

                response_text = result.content[0].text  # type: ignore
                import re

                guid_match = re.search(
                    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", response_text
                )
                assert guid_match is not None, f"No GUID found in response: {response_text}"
                guid = guid_match.group(0)

                logger.info("Image created with 'secure' group", guid=guid)

                # Try to retrieve with 'other-group' token
                result = await session.call_tool(
                    "get_image",
                    arguments={
                        "guid": guid,
                        "token": other_token,
                    },
                )

                # Should get an access denied error
                text_content = result.content[0]
                response_text = text_content.text  # type: ignore

                assert (
                    "Access denied" in response_text or "different group" in response_text
                ), f"Should deny cross-group access, got: {response_text}"

                logger.info("✓ MCP correctly denies cross-group image access")
                logger.info("✓ Test 2 passed: MCP authentication working correctly")


class TestWebAuthentication:
    """Test 3: Test graph is only available via web with token"""

    @pytest.mark.asyncio
    async def test_web_render_with_valid_token(self, test_token):
        """Test rendering a graph via web API with valid token"""
        logger = ConsoleLogger(name="web_auth_test", level=logging.INFO)
        logger.info("Test 3a: Testing web render with valid token")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{WEB_URL}/render",
                json={
                    "title": "Web Auth Test",
                    "x": [1, 2, 3, 4, 5],
                    "y": [10, 20, 15, 30, 25],
                    "proxy": True,
                },
                headers={"Authorization": f"Bearer {test_token}"},
            )

            logger.info("Web render response", status=response.status_code)

            assert (
                response.status_code == 200
            ), f"Expected 200, got {response.status_code}: {response.text}"

            # In proxy mode, should get a GUID (either as JSON {"image": "..."} or plain string)
            response_data = response.json()
            guid = (
                response_data.get("image")
                if isinstance(response_data, dict)
                else response.text.strip('"')
            )
            assert guid and len(guid) > 0, "Empty GUID returned"

            logger.info("Graph rendered successfully via web", guid=guid)

            return guid

    @pytest.mark.asyncio
    async def test_web_render_without_token(self):
        """Test that rendering fails without authorization header"""
        logger = ConsoleLogger(name="web_auth_test", level=logging.INFO)
        logger.info("Test 3b: Testing web render without token (should fail)")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{WEB_URL}/render",
                json={
                    "title": "Test",
                    "x": [1, 2, 3],
                    "y": [4, 5, 6],
                },
                # No Authorization header
            )

            logger.info("Web render response without token", status=response.status_code)

            assert (
                response.status_code == 403 or response.status_code == 401
            ), f"Expected 401/403, got {response.status_code}"

            logger.info("✓ Web correctly rejects request without token")

    @pytest.mark.asyncio
    async def test_web_render_with_invalid_token(self):
        """Test that rendering fails with invalid token"""
        logger = ConsoleLogger(name="web_auth_test", level=logging.INFO)
        logger.info("Test 3c: Testing web render with invalid token (should fail)")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{WEB_URL}/render",
                json={
                    "title": "Test",
                    "x": [1, 2, 3],
                    "y": [4, 5, 6],
                },
                headers={"Authorization": "Bearer invalid-token-here"},
            )

            logger.info("Web render response with invalid token", status=response.status_code)

            assert response.status_code == 401, f"Expected 401, got {response.status_code}"

            logger.info("✓ Web correctly rejects invalid token")

    @pytest.mark.asyncio
    async def test_web_get_image_with_valid_token(self, test_token):
        """Test retrieving an image via web with valid token"""
        logger = ConsoleLogger(name="web_auth_test", level=logging.INFO)
        logger.info("Test 3d: Testing web get image with valid token")

        async with httpx.AsyncClient() as client:
            # First create an image
            response = await client.post(
                f"{WEB_URL}/render",
                json={
                    "title": "Retrieval Test",
                    "x": [1, 2, 3],
                    "y": [4, 5, 6],
                    "proxy": True,
                },
                headers={"Authorization": f"Bearer {test_token}"},
            )

            assert response.status_code == 200
            response_data = response.json()
            guid = (
                response_data.get("image")
                if isinstance(response_data, dict)
                else response.text.strip('"')
            )
            logger.info("Image created via web", guid=guid)

            # Now retrieve it
            response = await client.get(
                f"{WEB_URL}/render/{guid}", headers={"Authorization": f"Bearer {test_token}"}
            )

            logger.info(
                "Image retrieval response",
                status=response.status_code,
                content_type=response.headers.get("content-type"),
            )

            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            assert "image/" in response.headers.get(
                "content-type", ""
            ), "Should return image content type"
            assert len(response.content) > 0, "Empty image data"

            logger.info("✓ Image retrieved successfully via web with valid token")

    @pytest.mark.asyncio
    async def test_web_get_image_without_token(self, test_token):
        """Test that retrieving an image fails without token"""
        logger = ConsoleLogger(name="web_auth_test", level=logging.INFO)
        logger.info("Test 3e: Testing web get image without token (should fail)")

        async with httpx.AsyncClient() as client:
            # First create an image
            response = await client.post(
                f"{WEB_URL}/render",
                json={
                    "title": "Test",
                    "x": [1, 2, 3],
                    "y": [4, 5, 6],
                    "proxy": True,
                },
                headers={"Authorization": f"Bearer {test_token}"},
            )

            response_data = response.json()
            guid = (
                response_data.get("image")
                if isinstance(response_data, dict)
                else response.text.strip('"')
            )
            logger.info("Image created", guid=guid)

            # Try to retrieve without token
            response = await client.get(f"{WEB_URL}/render/{guid}")

            logger.info("Image retrieval without token", status=response.status_code)

            assert (
                response.status_code == 403 or response.status_code == 401
            ), f"Expected 401/403, got {response.status_code}"

            logger.info("✓ Web correctly denies image access without token")

    @pytest.mark.asyncio
    async def test_web_get_image_with_different_group_token(self, auth_service, test_token):
        """Test that retrieving an image fails with token from different group"""
        logger = ConsoleLogger(name="web_auth_test", level=logging.INFO)
        logger.info("Test 3f: Testing web get image with different group token (should fail)")

        # Create a token for a different group
        other_token = auth_service.create_token(group="other-group", expires_in_seconds=90)

        async with httpx.AsyncClient() as client:
            # Create an image with 'secure' group token
            response = await client.post(
                f"{WEB_URL}/render",
                json={
                    "title": "Group Test",
                    "x": [1, 2, 3],
                    "y": [4, 5, 6],
                    "proxy": True,
                },
                headers={"Authorization": f"Bearer {test_token}"},
            )

            response_data = response.json()
            guid = (
                response_data.get("image")
                if isinstance(response_data, dict)
                else response.text.strip('"')
            )
            logger.info("Image created with 'secure' group", guid=guid)

            # Try to retrieve with 'other-group' token
            response = await client.get(
                f"{WEB_URL}/render/{guid}", headers={"Authorization": f"Bearer {other_token}"}
            )

            logger.info("Cross-group retrieval attempt", status=response.status_code)

            # Should get an error (400 for validation error, 403 for forbidden, or 404 for not found)
            assert response.status_code in [
                400,
                403,
                404,
            ], f"Expected 400/403/404 for cross-group access, got {response.status_code}"

            logger.info("✓ Web correctly denies cross-group image access")
            logger.info("✓ Test 3 passed: Web authentication working correctly")


if __name__ == "__main__":
    # Run all tests
    import pytest

    sys.exit(pytest.main([__file__, "-v", "-s"]))
