#!/usr/bin/env python3
"""Test ping tool for MCP server"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from app.logger import ConsoleLogger
import logging


async def test_ping():
    """Test that ping tool returns timestamp"""
    logger = ConsoleLogger(name="ping_test", level=logging.INFO)
    logger.info("Starting MCP ping test")

    server_params = StdioServerParameters(command="python", args=["-m", "app.mcp_server"], env=None)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            logger.info("MCP server initialized successfully")

            # List tools to verify ping is available
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]
            logger.info("Found tools", count=len(tool_names), tools=tool_names)

            assert "ping" in tool_names, "ping tool not found"
            logger.info("✓ Ping tool is available")

            # Call ping tool
            result = await session.call_tool("ping", arguments={})

            # Verify response
            assert len(result.content) > 0, "No content returned from ping"
            text_content = result.content[0]
            assert hasattr(text_content, "text"), "Response is not text"

            response_text = text_content.text
            assert "Server is running" in response_text
            assert "Timestamp:" in response_text
            assert "Service: gplot" in response_text

            logger.info("✓ Ping tool returned correct response")
            logger.info("All ping tests completed successfully")


if __name__ == "__main__":
    asyncio.run(test_ping())
    print("\n" + "=" * 50)
    print("All MCP ping tests passed!")
    print("=" * 50)
