#!/usr/bin/env python3
"""
Test proxy mode storage verification.
Ensures that GUID is only returned when image is successfully saved to storage.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from httpx import AsyncClient, ASGITransport
from app.logger import ConsoleLogger
from app.web_server.web_server import GraphWebServer
from app.auth import TokenInfo, verify_token
from app.storage import get_storage
from datetime import datetime, timedelta
import logging


def mock_verify_token():
    """Mock token verification for testing without authentication"""
    return TokenInfo(
        token="mock-token",
        group="test-group",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        issued_at=datetime.utcnow(),
    )


@pytest.fixture
def server():
    """Create a GraphWebServer instance"""
    return GraphWebServer(jwt_secret="test-secret-for-unit-tests")


@pytest.fixture
def app(server):
    """Get the FastAPI app from the server with auth dependency overridden"""
    # Override the verify_token dependency to bypass authentication in tests
    server.app.dependency_overrides[verify_token] = mock_verify_token
    return server.app


@pytest.mark.asyncio
async def test_proxy_mode_returns_guid_only_when_saved(app):
    """
    Test that proxy mode returns a GUID only when the image is successfully
    saved to storage. The response should include the GUID, format, and URLs.
    """
    logger = ConsoleLogger(name="proxy_storage_test", level=logging.INFO)
    logger.info("Testing proxy mode returns GUID only when image is saved")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={
                "title": "Proxy Mode Test Chart",
                "x": [1, 2, 3, 4, 5],
                "y": [10, 20, 15, 25, 20],
                "type": "line",
                "format": "png",
                "proxy": True,  # Enable proxy mode
                "return_base64": False,
            },
        )

        # Should return 200 OK
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        logger.info("Response received", status=response.status_code, keys=list(data.keys()))

        # Verify response structure
        assert "guid" in data, "Response should contain 'guid' key"
        assert "format" in data, "Response should contain 'format' key"
        assert "message" in data, "Response should contain 'message' key"
        assert "retrieve_url" in data, "Response should contain 'retrieve_url' key"
        assert "html_url" in data, "Response should contain 'html_url' key"

        # Verify GUID format
        guid = data["guid"]
        from uuid import UUID

        try:
            UUID(guid)
            logger.info("GUID format is valid", guid=guid)
        except ValueError:
            pytest.fail(f"GUID {guid} is not a valid UUID format")

        # Verify format
        assert data["format"] == "png", f"Expected format 'png', got {data['format']}"

        # Verify URLs
        assert f"/proxy/{guid}" in data["retrieve_url"], "retrieve_url should contain GUID"
        assert f"/proxy/{guid}" in data["html_url"], "html_url should contain GUID"

        # CRITICAL: Verify the image actually exists in storage
        storage = get_storage()
        result = storage.get_image(guid, group="test-group")

        assert result is not None, f"Image for GUID {guid} should exist in storage"
        image_data, img_format = result
        assert len(image_data) > 0, "Retrieved image should have content"
        assert img_format.lower() == "png", f"Expected format 'png', got {img_format}"

        logger.info(
            "Proxy mode test passed", guid=guid, image_size=len(image_data), format=img_format
        )


@pytest.mark.asyncio
async def test_proxy_mode_guid_is_retrievable(app):
    """
    Test that a GUID returned by proxy mode can be retrieved via the /proxy/{guid} endpoint.
    """
    logger = ConsoleLogger(name="proxy_retrieve_test", level=logging.INFO)
    logger.info("Testing proxy mode GUID is retrievable")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Render with proxy mode
        render_response = await client.post(
            "/render",
            json={
                "title": "Retrievable Chart",
                "x": [1, 2, 3],
                "y": [4, 5, 6],
                "type": "bar",
                "format": "png",
                "proxy": True,
                "return_base64": False,
            },
        )

        assert (
            render_response.status_code == 200
        ), f"Status: {render_response.status_code}, Body: {render_response.text}"
        response_data = render_response.json()
        guid = response_data.get("guid")
        assert guid is not None, f"No GUID in response: {response_data}"
        logger.info("Image rendered with GUID", guid=guid)

        # Step 2: Retrieve the image using the GUID
        retrieve_response = await client.get(f"/proxy/{guid}")

        assert retrieve_response.status_code == 200, (
            f"Expected 200, got {retrieve_response.status_code}. "
            f"GUID {guid} should be retrievable after render."
        )
        assert retrieve_response.headers["content-type"] == "image/png"
        assert len(retrieve_response.content) > 0, "Retrieved image should have content"

        logger.info("GUID is retrievable", guid=guid, image_size=len(retrieve_response.content))


@pytest.mark.asyncio
async def test_proxy_mode_html_view_accessible(app):
    """
    Test that the HTML view endpoint (/proxy/{guid}/html) is accessible
    for GUIDs returned by proxy mode.
    """
    logger = ConsoleLogger(name="proxy_html_test", level=logging.INFO)
    logger.info("Testing proxy mode HTML view is accessible")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Render with proxy mode
        render_response = await client.post(
            "/render",
            json={
                "title": "HTML View Test",
                "x": [1, 2, 3, 4],
                "y": [2, 4, 6, 8],
                "type": "scatter",
                "format": "png",
                "proxy": True,
                "return_base64": False,
            },
        )

        assert render_response.status_code == 200
        response_data = render_response.json()
        guid = response_data.get("guid")
        assert guid is not None, f"No GUID in response: {response_data}"
        logger.info("Image rendered with GUID", guid=guid)

        # Access HTML view
        html_response = await client.get(f"/proxy/{guid}/html")

        assert html_response.status_code == 200, f"HTML view should be accessible for GUID {guid}"
        assert html_response.headers["content-type"].startswith("text/html")
        assert guid in html_response.text, "GUID should appear in HTML content"
        assert len(html_response.content) > 0, "HTML response should have content"

        logger.info("HTML view is accessible", guid=guid, html_size=len(html_response.content))


@pytest.mark.asyncio
async def test_non_proxy_mode_returns_image_bytes(app):
    """
    Test that non-proxy mode returns direct image bytes, not GUID.
    This ensures the fix doesn't break normal rendering.
    """
    logger = ConsoleLogger(name="non_proxy_test", level=logging.INFO)
    logger.info("Testing non-proxy mode returns image bytes")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={
                "title": "Non-Proxy Test",
                "x": [1, 2, 3],
                "y": [4, 5, 6],
                "type": "line",
                "format": "png",
                "proxy": False,  # Disable proxy mode
                "return_base64": False,
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert len(response.content) > 0, "Image content should not be empty"

        # Verify it's NOT a GUID response
        try:
            response.json()
            # If we get here, it's JSON (shouldn't happen for non-proxy mode)
            pytest.fail("Non-proxy mode should return image bytes, not JSON")
        except Exception:
            # Expected - response.content is binary image data, not JSON
            logger.info("Non-proxy mode correctly returns image bytes")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
