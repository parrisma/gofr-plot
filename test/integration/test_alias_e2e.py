"""End-to-end integration tests for alias system

Phase 6: Integration tests that verify the complete alias workflow
across storage, MCP handlers, and Web servers.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta
from app.web_server.web_server import GraphWebServer
from app.auth import TokenInfo, verify_token, AuthService
from app.storage import get_storage
from app.mcp_server.mcp_server import (
    _handle_list_images,
    _handle_get_image,
    set_auth_service,
    set_storage,
)


def mock_verify_token_integration():
    """Mock token for integration tests"""
    return TokenInfo(
        token="integration-test-token",
        group="integration-test",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        issued_at=datetime.utcnow(),
    )


def mock_verify_token_group1():
    """Mock token for group1"""
    return TokenInfo(
        token="group1-token",
        group="group1",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        issued_at=datetime.utcnow(),
    )


def mock_verify_token_group2():
    """Mock token for group2"""
    return TokenInfo(
        token="group2-token",
        group="group2",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        issued_at=datetime.utcnow(),
    )


@pytest.fixture
def web_server():
    """Create a GraphWebServer instance"""
    return GraphWebServer(jwt_secret="test-secret-for-integration")


@pytest.fixture
def web_app(web_server):
    """Get the FastAPI app with auth overridden"""
    web_server.app.dependency_overrides[verify_token] = mock_verify_token_integration
    return web_server.app


@pytest.fixture
def storage():
    """Get storage instance (same as web server uses)"""
    return get_storage()


@pytest.fixture
def mock_auth_service(tmp_path, storage):
    """Create mock auth service for MCP handlers and inject shared storage"""
    from unittest.mock import MagicMock
    from app.mcp_server import mcp_server as mcp_module

    # Save original storage to restore after test
    original_storage = mcp_module.storage

    service = MagicMock(spec=AuthService)
    service.verify_token.return_value = TokenInfo(
        token="mock-token",
        group="integration-test",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        issued_at=datetime.utcnow(),
    )
    set_auth_service(service)
    # Inject the same storage instance used by web server fixtures
    set_storage(storage)

    yield service

    # Restore original storage after test
    set_storage(original_storage)


class TestAliasEndToEnd:
    """End-to-end tests for alias workflow"""

    @pytest.mark.asyncio
    async def test_render_with_alias_then_retrieve_via_web(self, web_app, storage):
        """Render via Web with alias, retrieve via Web proxy"""
        alias = "e2e-test-chart-1"

        transport = ASGITransport(app=web_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Step 1: Render graph with alias
            # Note: return_base64=False is required to get proper JSON with guid field
            render_response = await client.post(
                "/render",
                json={
                    "title": "E2E Test Chart",
                    "y1": [10, 20, 30, 40, 50],
                    "type": "line",
                    "proxy": True,
                    "return_base64": False,
                    "alias": alias,
                },
            )

            assert render_response.status_code == 200, f"Render failed: {render_response.text}"
            data = render_response.json()
            assert "guid" in data
            assert data.get("alias") == alias

            # Step 2: Retrieve via proxy using alias
            proxy_response = await client.get(f"/proxy/{alias}")

            assert proxy_response.status_code == 200, f"Proxy failed: {proxy_response.text}"
            assert proxy_response.headers["content-type"] == "image/png"
            assert len(proxy_response.content) > 100  # Valid image data

    @pytest.mark.asyncio
    async def test_render_with_alias_get_image_mcp(self, web_app, storage, mock_auth_service):
        """Render via Web with alias, retrieve via MCP get_image handler"""
        alias = "e2e-test-chart-2"

        transport = ASGITransport(app=web_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Step 1: Render with alias via web
            render_response = await client.post(
                "/render",
                json={
                    "title": "E2E MCP Retrieval Test",
                    "y1": [5, 15, 25, 35],
                    "type": "bar",
                    "proxy": True,
                    "return_base64": False,
                    "alias": alias,
                },
            )

            assert render_response.status_code == 200
            data = render_response.json()
            # Verify render succeeded (guid is used implicitly by alias)
            assert "guid" in data

        # Step 2: Retrieve via MCP get_image handler using alias
        result = _handle_get_image(
            {"identifier": alias, "token": "mock-token"}, client_id="test-client"
        )

        # Should return image content
        assert len(result) > 0
        # Result should contain image data (ImageContent has 'data' attribute)
        assert any("image" in str(r).lower() for r in result)

    @pytest.mark.asyncio
    async def test_list_images_shows_alias(self, web_app, storage, mock_auth_service):
        """Render with alias, verify list_images shows it"""
        alias = "e2e-list-test-chart"

        transport = ASGITransport(app=web_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Step 1: Render with alias
            render_response = await client.post(
                "/render",
                json={
                    "title": "List Images Test",
                    "y1": [1, 2, 3],
                    "proxy": True,
                    "return_base64": False,
                    "alias": alias,
                },
            )
            assert render_response.status_code == 200

        # Step 2: Call list_images MCP handler
        result = _handle_list_images({"token": "mock-token"}, client_id="test-client")

        # Response should contain the alias
        assert len(result) > 0
        response_text = str(result[0])
        assert alias in response_text, f"Alias '{alias}' not found in list_images response"

    @pytest.mark.asyncio
    async def test_web_render_with_alias_then_retrieve(self, web_app, storage):
        """Render via Web API with alias, retrieve via Web API"""
        alias = "e2e-web-render-chart"

        transport = ASGITransport(app=web_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Step 1: Render via Web API
            render_response = await client.post(
                "/render",
                json={
                    "title": "Web Render with Alias",
                    "y1": [100, 200, 300],
                    "type": "scatter",
                    "proxy": True,
                    "return_base64": False,
                    "alias": alias,
                },
            )

            assert render_response.status_code == 200, f"Render failed: {render_response.text}"
            data = render_response.json()
            assert "guid" in data
            assert data.get("alias") == alias

            # Step 2: Retrieve via alias
            proxy_response = await client.get(f"/proxy/{alias}")

            assert proxy_response.status_code == 200
            assert "image" in proxy_response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_alias_html_endpoint(self, web_app, storage):
        """Render with alias, view HTML page via alias"""
        alias = "e2e-html-test-chart"

        transport = ASGITransport(app=web_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Render with alias
            render_response = await client.post(
                "/render",
                json={
                    "title": "HTML View Test",
                    "y1": [50, 60, 70],
                    "proxy": True,
                    "return_base64": False,
                    "alias": alias,
                },
            )
            assert render_response.status_code == 200

            # Get HTML view via alias
            html_response = await client.get(f"/proxy/{alias}/html")

            assert html_response.status_code == 200
            assert "text/html" in html_response.headers["content-type"]
            assert alias in html_response.text  # Alias should appear in HTML


class TestAliasGroupIsolation:
    """Integration tests for alias group isolation"""

    @pytest.mark.asyncio
    async def test_alias_not_visible_across_groups(self, web_server, storage):
        """Alias created in group1 is not accessible from group2"""
        alias = "group-isolated-chart"

        # Override for group1
        web_server.app.dependency_overrides[verify_token] = mock_verify_token_group1
        app = web_server.app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create chart with alias in group1
            render_response = await client.post(
                "/render",
                json={
                    "title": "Group1 Chart",
                    "y1": [1, 2, 3],
                    "proxy": True,
                    "return_base64": False,
                    "alias": alias,
                },
            )
            assert render_response.status_code == 200

        # Switch to group2
        web_server.app.dependency_overrides[verify_token] = mock_verify_token_group2

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Try to access from group2 - should fail
            proxy_response = await client.get(f"/proxy/{alias}")

            # Should return 404 (alias not found in group2)
            assert proxy_response.status_code == 404

    @pytest.mark.asyncio
    async def test_same_alias_different_groups(self, web_server, storage):
        """Same alias can exist in different groups"""
        alias = "shared-alias-name"

        # Create in group1
        web_server.app.dependency_overrides[verify_token] = mock_verify_token_group1
        app = web_server.app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            render1 = await client.post(
                "/render",
                json={
                    "title": "Group1 Shared Alias",
                    "y1": [10, 20, 30],
                    "proxy": True,
                    "return_base64": False,
                    "alias": alias,
                },
            )
            assert render1.status_code == 200
            guid1 = render1.json()["guid"]

        # Create same alias in group2
        web_server.app.dependency_overrides[verify_token] = mock_verify_token_group2

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            render2 = await client.post(
                "/render",
                json={
                    "title": "Group2 Shared Alias",
                    "y1": [100, 200, 300],  # Different data
                    "proxy": True,
                    "return_base64": False,
                    "alias": alias,
                },
            )
            assert render2.status_code == 200  # Should succeed (no conflict)
            guid2 = render2.json()["guid"]

        # Different GUIDs
        assert guid1 != guid2

        # Both groups can access their own version
        web_server.app.dependency_overrides[verify_token] = mock_verify_token_group1
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            group1_response = await client.get(f"/proxy/{alias}")
            assert group1_response.status_code == 200

        web_server.app.dependency_overrides[verify_token] = mock_verify_token_group2
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            group2_response = await client.get(f"/proxy/{alias}")
            assert group2_response.status_code == 200


class TestAliasErrorHandling:
    """Integration tests for alias error scenarios"""

    @pytest.mark.asyncio
    async def test_invalid_alias_format_still_saves(self, web_app, storage):
        """Invalid alias format still saves image (just without alias)"""
        transport = ASGITransport(app=web_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            render_response = await client.post(
                "/render",
                json={
                    "title": "Invalid Alias Test",
                    "y1": [1, 2, 3],
                    "proxy": True,
                    "return_base64": False,
                    "alias": "a",  # Too short - invalid (must be 3-64 chars)
                },
            )

            # Should still succeed, just without the alias
            assert render_response.status_code == 200
            data = render_response.json()
            assert "guid" in data
            # Invalid alias should not be registered
            assert data.get("alias") is None or "alias" not in data

    @pytest.mark.asyncio
    async def test_nonexistent_alias_returns_404(self, web_app, storage):
        """Requesting non-existent alias returns 404"""
        transport = ASGITransport(app=web_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/proxy/definitely-does-not-exist-12345")

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_image_with_bad_identifier(self, mock_auth_service):
        """get_image with non-existent identifier returns error"""
        result = _handle_get_image(
            {"identifier": "nonexistent-alias-xyz", "token": "mock-token"},
            client_id="test-client",
        )

        # Should return error content (not crash)
        assert len(result) > 0
        response_text = str(result[0]).lower()
        assert "not found" in response_text or "error" in response_text

    @pytest.mark.asyncio
    async def test_retrieve_by_guid_still_works(self, web_app, storage):
        """Can still retrieve by GUID even when alias is set"""
        alias = "e2e-guid-fallback"

        transport = ASGITransport(app=web_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Render with alias
            render_response = await client.post(
                "/render",
                json={
                    "title": "GUID Fallback Test",
                    "y1": [1, 2, 3],
                    "proxy": True,
                    "return_base64": False,
                    "alias": alias,
                },
            )

            assert render_response.status_code == 200
            data = render_response.json()
            guid = data["guid"]

            # Retrieve by GUID (not alias)
            guid_response = await client.get(f"/proxy/{guid}")
            assert guid_response.status_code == 200

            # Retrieve by alias too
            alias_response = await client.get(f"/proxy/{alias}")
            assert alias_response.status_code == 200

            # Both should return same content
            assert guid_response.content == alias_response.content
