"""
Schema regression tests for MCP tool definitions.

Validates that tool descriptions contain required keywords to guide LLM usage,
and that error responses follow standardized format.
"""

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from app.logger import ConsoleLogger
import logging
from conftest import MCP_URL

MCP_URL = MCP_URL


@pytest.fixture
async def tools():
    """Get list of tools from MCP server."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return result.tools


class TestToolDescriptions:
    """Test that tool descriptions contain required keywords."""

    @pytest.mark.asyncio
    async def test_ping_mentions_no_auth(self, tools):
        """ping tool should explicitly state it doesn't require authentication."""
        ping_tool = next(t for t in tools if t.name == "ping")

        description = ping_tool.description.lower()
        assert (
            "does not require" in description
            or "no auth" in description
            or "not required" in description
        ), "ping should explicitly state authentication is not required"

    @pytest.mark.asyncio
    async def test_render_graph_mentions_authentication(self, tools):
        """render_graph tool should have AUTHENTICATION section."""
        render_tool = next(t for t in tools if t.name == "render_graph")

        description = render_tool.description
        assert "AUTHENTICATION" in description, "render_graph should have AUTHENTICATION section"
        assert "token" in description.lower(), "render_graph should mention token parameter"

    @pytest.mark.asyncio
    async def test_render_graph_mentions_multi_dataset(self, tools):
        """render_graph tool should explain multi-dataset capability."""
        render_tool = next(t for t in tools if t.name == "render_graph")

        description = render_tool.description
        assert (
            "MULTI-DATASET" in description or "multiple dataset" in description.lower()
        ), "render_graph should explain multi-dataset support"
        assert (
            "y1" in description or "datasets" in description.lower()
        ), "render_graph should mention y1/y2/etc parameters"

    @pytest.mark.asyncio
    async def test_render_graph_mentions_proxy_mode(self, tools):
        """render_graph tool should explain proxy mode."""
        render_tool = next(t for t in tools if t.name == "render_graph")

        description = render_tool.description
        assert (
            "PROXY" in description.upper() or "proxy_mode" in description.lower()
        ), "render_graph should explain proxy_mode parameter"
        assert (
            "guid" in description.lower()
        ), "render_graph should mention guid return value in proxy mode"

    @pytest.mark.asyncio
    async def test_render_graph_mentions_chart_types(self, tools):
        """render_graph tool should list available chart types."""
        render_tool = next(t for t in tools if t.name == "render_graph")

        description = render_tool.description
        assert "line" in description.lower(), "render_graph should mention line charts"
        assert "bar" in description.lower(), "render_graph should mention bar charts"
        assert "scatter" in description.lower(), "render_graph should mention scatter plots"

    @pytest.mark.asyncio
    async def test_render_graph_mentions_themes(self, tools):
        """render_graph tool should mention theme support."""
        render_tool = next(t for t in tools if t.name == "render_graph")

        description = render_tool.description
        assert "theme" in description.lower(), "render_graph should mention theme parameter"

    @pytest.mark.asyncio
    async def test_get_image_mentions_workflow(self, tools):
        """get_image tool should explain two-step workflow."""
        get_image_tool = next(t for t in tools if t.name == "get_image")

        description = get_image_tool.description
        assert "WORKFLOW" in description, "get_image should explain workflow"
        assert "proxy" in description.lower(), "get_image should reference proxy mode"

    @pytest.mark.asyncio
    async def test_get_image_mentions_group_access(self, tools):
        """get_image tool should explain group access control."""
        get_image_tool = next(t for t in tools if t.name == "get_image")

        description = get_image_tool.description
        assert "group" in description.lower(), "get_image should mention group access control"

    @pytest.mark.asyncio
    async def test_list_themes_mentions_discovery(self, tools):
        """list_themes tool should explain discovery purpose."""
        list_themes_tool = next(t for t in tools if t.name == "list_themes")

        description = list_themes_tool.description
        assert (
            "available" in description.lower() or "discover" in description.lower()
        ), "list_themes should explain it lists available themes"

    @pytest.mark.asyncio
    async def test_list_handlers_mentions_discovery(self, tools):
        """list_handlers tool should explain discovery purpose."""
        list_handlers_tool = next(t for t in tools if t.name == "list_handlers")

        description = list_handlers_tool.description
        assert (
            "available" in description.lower() or "supported" in description.lower()
        ), "list_handlers should explain it lists available chart types"


class TestInputSchemaExamples:
    """Test that input schemas include helpful examples."""

    @pytest.mark.asyncio
    async def test_token_parameter_has_example(self, tools):
        """Token parameter should show example JWT format."""
        render_tool = next(t for t in tools if t.name == "render_graph")

        token_desc = render_tool.inputSchema["properties"]["token"]["description"]
        assert "eyJ" in token_desc, "token parameter should include example JWT starting with 'eyJ'"

    @pytest.mark.asyncio
    async def test_identifier_parameter_has_example(self, tools):
        """Identifier parameter should show example format."""
        get_image_tool = next(t for t in tools if t.name == "get_image")

        identifier_desc = get_image_tool.inputSchema["properties"]["identifier"]["description"]
        assert (
            "-" in identifier_desc
            or "uuid" in identifier_desc.lower()
            or "alias" in identifier_desc.lower()
        ), "identifier parameter should mention UUID format, alias, or show example"


class TestErrorResponseFormat:
    """Test that error responses follow standardized format."""

    # NOTE: Missing token and invalid parameter tests removed - MCP framework validates
    # inputSchema (required properties, types) before our tool handler runs, so we cannot
    # control those error messages. These tests would only pass if token were optional in
    # schema but required in practice.

    @pytest.mark.asyncio
    async def test_validation_error_format(self, test_token):
        """Validation errors should return formatted error with context."""
        logger = ConsoleLogger(name="schema_test", level=logging.INFO)

        async with streamablehttp_client(MCP_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "render_graph",
                    arguments={
                        "token": test_token,
                        "handler": "line",
                        "title": "Test Graph",
                        "x": [1, 2, 3],
                        "y1": [4, 5],  # Length mismatch
                    },
                )

                # Should be text content with error
                assert len(result.content) == 1
                assert result.content[0].type == "text"

                error_text = result.content[0].text  # type: ignore[union-attr]
                logger.info("Error response", text=error_text)

                # Check for standardized error format
                assert "Error" in error_text, "Error message should start with 'Error'"
                assert "Validation" in error_text, "Should specify validation error type"
                assert (
                    "length" in error_text.lower() or "mismatch" in error_text.lower()
                ), "Should explain the validation problem"


class TestSuccessResponseFormat:
    """Test that success responses follow standardized format."""

    @pytest.mark.asyncio
    async def test_list_themes_success_format(self):
        """list_themes should return formatted list."""
        logger = ConsoleLogger(name="schema_test", level=logging.INFO)

        async with streamablehttp_client(MCP_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("list_themes", arguments={})

                # Should be text content
                assert len(result.content) == 1
                assert result.content[0].type == "text"

                text = result.content[0].text  # type: ignore[union-attr]
                logger.info("Success response", text=text[:200])

                # Should have title and list format
                assert "Available Themes" in text or "Themes:" in text, "Should have clear title"
                assert "light" in text.lower(), "Should list light theme"
                assert "dark" in text.lower(), "Should list dark theme"

    @pytest.mark.asyncio
    async def test_render_graph_success_has_image(self, test_token):
        """Successful render should return image with success message."""
        logger = ConsoleLogger(name="schema_test", level=logging.INFO)

        async with streamablehttp_client(MCP_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "render_graph",
                    arguments={
                        "token": test_token,
                        "handler": "line",
                        "title": "Test Graph",
                        "x": [1, 2, 3],
                        "y1": [4, 5, 6],
                    },
                )

                # Should have both text and image content
                assert len(result.content) == 2

                # Text content should confirm success
                text_content = next(c for c in result.content if c.type == "text")
                logger.info("Success message", text=text_content.text)
                assert (
                    "success" in text_content.text.lower()
                    or "rendered" in text_content.text.lower()
                ), "Should include success message"

                # Image content should be present
                image_content = next(c for c in result.content if c.type == "image")
                assert image_content.data, "Should include image data"
                assert image_content.mimeType == "image/png", "Should specify MIME type"


class TestToolAvailability:
    """Test that all expected tools are available."""

    @pytest.mark.asyncio
    async def test_all_required_tools_exist(self, tools):
        """All required MCP tools should be registered."""
        tool_names = [t.name for t in tools]

        required_tools = ["ping", "render_graph", "get_image", "list_themes", "list_handlers"]

        for tool_name in required_tools:
            assert tool_name in tool_names, f"Tool '{tool_name}' should be registered"

    @pytest.mark.asyncio
    async def test_all_tools_have_descriptions(self, tools):
        """All tools should have non-empty descriptions."""
        for tool in tools:
            assert tool.description, f"Tool '{tool.name}' should have a description"
            assert (
                len(tool.description) > 20
            ), f"Tool '{tool.name}' description should be substantial"

    @pytest.mark.asyncio
    async def test_all_tools_have_input_schemas(self, tools):
        """All tools should define input schemas."""
        for tool in tools:
            assert tool.inputSchema, f"Tool '{tool.name}' should have inputSchema"
            assert (
                "type" in tool.inputSchema
            ), f"Tool '{tool.name}' inputSchema should have 'type' field"
