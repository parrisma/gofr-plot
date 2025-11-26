"""Tests for Web API alias functionality

Phase 3: Web API integration tests for alias support
"""

import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta
from app.web_server.web_server import GraphWebServer
from app.auth import TokenInfo, verify_token
from app.storage import get_storage


def mock_verify_token():
    """Mock token verification for testing without authentication"""
    return TokenInfo(
        token="mock-token",
        group="testgroup",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        issued_at=datetime.utcnow(),
    )


def mock_verify_token_group2():
    """Mock token verification for group2"""
    return TokenInfo(
        token="mock-token-group2",
        group="group2",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        issued_at=datetime.utcnow(),
    )


@pytest.fixture
def server():
    """Create a GraphWebServer instance"""
    return GraphWebServer(jwt_secret="test-secret-for-alias-tests")


@pytest.fixture
def app(server):
    """Get the FastAPI app from the server with auth dependency overridden"""
    server.app.dependency_overrides[verify_token] = mock_verify_token
    return server.app


@pytest.fixture
def storage():
    """Get storage instance"""
    return get_storage()


class TestWebProxyWithAlias:
    """Tests for /proxy/{identifier} endpoint with alias support"""

    @pytest.mark.asyncio
    async def test_proxy_with_guid(self, app, storage):
        """Proxy endpoint works with GUID"""
        # Save image directly
        image_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        guid = storage.save_image(image_data, "png", "testgroup")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/proxy/{guid}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

    @pytest.mark.asyncio
    async def test_proxy_with_alias(self, app, storage):
        """Proxy endpoint works with alias"""
        # Save image and register alias
        image_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        guid = storage.save_image(image_data, "png", "testgroup")
        storage.register_alias("my-web-chart", guid, "testgroup")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/proxy/my-web-chart")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

    @pytest.mark.asyncio
    async def test_proxy_invalid_alias_returns_404(self, app):
        """Proxy endpoint returns 404 for unknown alias"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/proxy/nonexistent-alias")

        assert response.status_code == 404
        data = response.json()
        # Response message includes "no image found" or "not found"
        assert (
            "no image found" in data["detail"]["message"].lower()
            or "not found" in data["detail"]["message"].lower()
        )

    @pytest.mark.asyncio
    async def test_proxy_alias_wrong_group(self, server, storage):
        """Alias from different group returns 404"""
        # Override to use group2 token
        server.app.dependency_overrides[verify_token] = mock_verify_token_group2

        # Save image in group1 with alias (different from token group)
        image_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        guid = storage.save_image(image_data, "png", "group1")
        storage.register_alias("group1-secret", guid, "group1")

        # Try to access with group2 token
        transport = ASGITransport(app=server.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/proxy/group1-secret")

        # Should return 404 (alias not found in group2)
        assert response.status_code == 404


class TestWebRenderWithAlias:
    """Tests for /render endpoint with alias support"""

    @pytest.fixture
    def render_params(self):
        """Basic render parameters"""
        return {
            "title": "Test Chart",
            "y1": [1, 2, 3, 4, 5],
            "type": "line",
            "proxy": True,
            "return_base64": False,
        }

    @pytest.mark.asyncio
    async def test_render_with_alias_returns_alias_info(self, app, render_params):
        """Render with alias returns alias in response"""
        params = {**render_params, "alias": "web-chart-q4"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/render", json=params)

        assert response.status_code == 200
        data = response.json()
        assert "guid" in data
        assert data.get("alias") == "web-chart-q4"
        assert "alias_url" in data

    @pytest.mark.asyncio
    async def test_render_without_alias_works(self, app, render_params):
        """Render without alias still works"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/render", json=render_params)

        assert response.status_code == 200
        data = response.json()
        assert "guid" in data
        assert "alias" not in data

    @pytest.mark.asyncio
    async def test_render_with_invalid_alias_still_saves(self, app, render_params):
        """Render with invalid alias format still saves image"""
        params = {**render_params, "alias": "ab"}  # Too short

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/render", json=params)

        # Should still succeed, just without alias
        assert response.status_code == 200
        data = response.json()
        assert "guid" in data
        # Invalid alias should not be registered
        assert "alias" not in data or data.get("alias") is None

    @pytest.mark.asyncio
    async def test_render_alias_retrievable(self, app, render_params):
        """Rendered image with alias is retrievable by alias"""
        params = {**render_params, "alias": "retrievable-chart"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Render with alias
            render_response = await client.post("/render", json=params)

            assert render_response.status_code == 200
            data = render_response.json()
            assert data.get("alias") == "retrievable-chart"

            # Retrieve by alias
            proxy_response = await client.get("/proxy/retrievable-chart")

        assert proxy_response.status_code == 200
        assert proxy_response.headers["content-type"] == "image/png"


class TestWebProxyHtmlWithAlias:
    """Tests for /proxy/{identifier}/html endpoint with alias support"""

    @pytest.mark.asyncio
    async def test_html_with_guid(self, app, storage):
        """HTML endpoint works with GUID"""
        image_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        guid = storage.save_image(image_data, "png", "testgroup")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/proxy/{guid}/html")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert guid in response.text

    @pytest.mark.asyncio
    async def test_html_with_alias(self, app, storage):
        """HTML endpoint works with alias"""
        image_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        guid = storage.save_image(image_data, "png", "testgroup")
        storage.register_alias("html-chart", guid, "testgroup")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/proxy/html-chart/html")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Should show alias in HTML
        assert "html-chart" in response.text

    @pytest.mark.asyncio
    async def test_html_invalid_identifier_returns_404(self, app):
        """HTML endpoint returns 404 for unknown identifier"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/proxy/nonexistent/html")

        assert response.status_code == 404
