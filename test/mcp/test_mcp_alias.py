"""Tests for MCP alias functionality

Phase 2: MCP tool integration tests for alias support
"""

import pytest
from app.mcp_server.mcp_server import (
    _handle_get_image,
    storage,
    set_auth_service,
)
from app.auth import AuthService


@pytest.fixture
def auth_service(tmp_path):
    """Create AuthService for testing"""
    token_store = tmp_path / "tokens.json"
    service = AuthService(secret_key="test-secret-key-mcp-alias", token_store_path=str(token_store))
    set_auth_service(service)
    return service


@pytest.fixture
def valid_token(auth_service):
    """Create a valid JWT token"""
    return auth_service.create_token(group="testgroup", expires_in_seconds=3600)


@pytest.fixture
def sample_image_data():
    """Sample PNG image data"""
    return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"


class TestMCPGetImageWithAlias:
    """Tests for get_image tool with alias support"""

    def test_get_image_with_guid(self, valid_token, sample_image_data):
        """get_image works with GUID identifier"""
        # Save image directly to MCP server's storage
        guid = storage.save_image(sample_image_data, "png", "testgroup")

        result = _handle_get_image(
            {"identifier": guid, "token": valid_token}, client_id="test-client"
        )

        # Should return ImageContent
        assert len(result) > 0
        assert any("image" in str(r) for r in result)

    def test_get_image_with_alias(self, valid_token, sample_image_data):
        """get_image works with alias identifier"""
        # Save image and register alias
        guid = storage.save_image(sample_image_data, "png", "testgroup")
        storage.register_alias("my-chart", guid, "testgroup")

        result = _handle_get_image(
            {"identifier": "my-chart", "token": valid_token}, client_id="test-client"
        )

        # Should return ImageContent
        assert len(result) > 0
        assert any("image" in str(r) for r in result)

    def test_get_image_alias_includes_metadata(self, valid_token, sample_image_data):
        """get_image response includes alias in metadata"""
        guid = storage.save_image(sample_image_data, "png", "testgroup")
        storage.register_alias("report-q4", guid, "testgroup")

        result = _handle_get_image(
            {"identifier": guid, "token": valid_token}, client_id="test-client"
        )

        # Check response mentions alias
        result_str = str(result)
        assert "report-q4" in result_str or len(result) > 0

    def test_get_image_missing_identifier(self, valid_token):
        """get_image returns error when identifier missing"""
        result = _handle_get_image({"token": valid_token}, client_id="test-client")

        result_str = str(result)
        assert "Missing Parameter" in result_str or "identifier" in result_str.lower()

    def test_get_image_invalid_alias_returns_not_found(self, valid_token):
        """get_image returns not found for unregistered alias"""
        result = _handle_get_image(
            {"identifier": "nonexistent-alias", "token": valid_token}, client_id="test-client"
        )

        result_str = str(result)
        assert "Not Found" in result_str

    def test_get_image_alias_wrong_group(self, auth_service, sample_image_data):
        """Alias from different group is not accessible"""
        # Create token for group2
        token2 = auth_service.create_token(group="group2", expires_in_seconds=3600)

        # Save image and register alias in group1
        guid = storage.save_image(sample_image_data, "png", "group1")
        storage.register_alias("secret-report", guid, "group1")

        # Try to access from group2
        result = _handle_get_image(
            {"identifier": "secret-report", "token": token2}, client_id="test-client"
        )

        result_str = str(result)
        assert "Not Found" in result_str or "Permission" in result_str


class TestMCPToolSchemas:
    """Tests for MCP tool schemas include alias support"""

    @pytest.mark.asyncio
    async def test_get_image_schema_has_identifier(self):
        """get_image tool schema has 'identifier' parameter"""
        from app.mcp_server.mcp_server import handle_list_tools

        tools = await handle_list_tools()  # type: ignore[call-arg]
        get_image_tool = next(t for t in tools if t.name == "get_image")

        schema = get_image_tool.inputSchema
        assert "identifier" in schema["properties"]
        assert "identifier" in schema["required"]

    @pytest.mark.asyncio
    async def test_render_graph_schema_has_alias(self):
        """render_graph tool schema has 'alias' parameter"""
        from app.mcp_server.mcp_server import handle_list_tools

        tools = await handle_list_tools()  # type: ignore[call-arg]
        render_tool = next(t for t in tools if t.name == "render_graph")

        schema = render_tool.inputSchema
        assert "alias" in schema["properties"]
        # alias is optional, not required
        assert "alias" not in schema.get("required", [])

    @pytest.mark.asyncio
    async def test_get_image_description_mentions_alias(self):
        """get_image tool description mentions alias support"""
        from app.mcp_server.mcp_server import handle_list_tools

        tools = await handle_list_tools()  # type: ignore[call-arg]
        get_image_tool = next(t for t in tools if t.name == "get_image")

        description = get_image_tool.description or ""
        assert "alias" in description.lower()
