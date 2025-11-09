#!/usr/bin/env python3
"""
Simple test script to verify MCP server functionality.
This script tests the render_graph tool through the MCP protocol.
"""

import asyncio
import json
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from app.logger import ConsoleLogger


async def test_mcp_server():
    """Test the MCP server by calling the render_graph tool"""

    # Initialize logger
    logger = ConsoleLogger(name="mcp_test", level=logging.INFO)

    # Define server parameters
    server_params = StdioServerParameters(command="python", args=["app/mcp_server.py"], env=None)

    logger.info("Starting MCP server test")
    print("-" * 50)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            logger.info("MCP server initialized successfully")

            # List available tools
            tools_result = await session.list_tools()
            logger.info("Found tools", count=len(tools_result.tools))
            for tool in tools_result.tools:
                desc = tool.description[:60] if tool.description else "No description"
                print(f"  {tool.name}: {desc}...")

            # Test render_graph tool with line chart
            print("\n" + "-" * 50)
            logger.info("Testing line chart rendering")
            line_args = {
                "title": "Test Line Chart",
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 6, 8, 10],
                "xlabel": "X Axis",
                "ylabel": "Y Axis",
                "type": "line",
            }

            line_result = await session.call_tool("render_graph", line_args)
            logger.info("Line chart rendered successfully", content_items=len(line_result.content))
            for i, content in enumerate(line_result.content):
                print(f"  Item {i+1}: {content.type}")

            # Test render_graph tool with bar chart
            print("\n" + "-" * 50)
            logger.info("Testing bar chart rendering")
            bar_args = {
                "title": "Test Bar Chart",
                "x": [1, 2, 3, 4, 5],
                "y": [5, 8, 3, 7, 4],
                "xlabel": "Categories",
                "ylabel": "Values",
                "type": "bar",
            }

            bar_result = await session.call_tool("render_graph", bar_args)
            logger.info("Bar chart rendered successfully", content_items=len(bar_result.content))

            # Test scatter plot
            print("\n" + "-" * 50)
            logger.info("Testing scatter plot rendering")
            scatter_args = {
                "title": "Test Scatter Plot",
                "x": [1, 2, 3, 4, 5],
                "y": [2, 5, 3, 8, 6],
                "xlabel": "X Values",
                "ylabel": "Y Values",
                "type": "scatter",
            }

            scatter_result = await session.call_tool("render_graph", scatter_args)
            logger.info(
                "Scatter plot rendered successfully", content_items=len(scatter_result.content)
            )

            # Test dark theme
            print("\n" + "-" * 50)
            logger.info("Testing dark theme")
            dark_args = {
                "title": "Dark Theme Chart",
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 6, 8, 10],
                "type": "line",
                "theme": "dark",
            }

            dark_result = await session.call_tool("render_graph", dark_args)
            logger.info(
                "Dark theme chart rendered successfully", content_items=len(dark_result.content)
            )

            # Test validation - mismatched arrays
            print("\n" + "-" * 50)
            logger.info("Testing validation for mismatched arrays")
            error_args = {"title": "Mismatched Arrays", "x": [1, 2, 3], "y": [1, 2], "type": "line"}
            error_result = await session.call_tool("render_graph", error_args)
            assert len(error_result.content) > 0
            error_text = (
                error_result.content[0].text
                if hasattr(error_result.content[0], "text")
                else str(error_result.content[0])
            )
            assert "validation" in error_text.lower() and "length" in error_text.lower()
            logger.info("Validation correctly caught mismatched arrays")

            # Test validation - invalid chart type
            print("\n" + "-" * 50)
            logger.info("Testing validation for invalid chart type")
            invalid_type_args = {
                "title": "Invalid Type",
                "x": [1, 2, 3],
                "y": [1, 2, 3],
                "type": "invalid_type",
            }
            type_result = await session.call_tool("render_graph", invalid_type_args)
            assert len(type_result.content) > 0
            type_text = (
                type_result.content[0].text
                if hasattr(type_result.content[0], "text")
                else str(type_result.content[0])
            )
            assert "validation" in type_text.lower() and (
                "invalid" in type_text.lower() or "type" in type_text.lower()
            )
            logger.info("Validation correctly caught invalid chart type")

            # Test validation - empty arrays
            print("\n" + "-" * 50)
            logger.info("Testing validation for empty arrays")
            empty_args = {"title": "Empty Data", "x": [], "y": [], "type": "line"}
            empty_result = await session.call_tool("render_graph", empty_args)
            assert len(empty_result.content) > 0
            empty_text = (
                empty_result.content[0].text
                if hasattr(empty_result.content[0], "text")
                else str(empty_result.content[0])
            )
            assert "validation" in empty_text.lower() and "empty" in empty_text.lower()
            logger.info("Validation correctly caught empty arrays")

            # Test validation - invalid alpha
            print("\n" + "-" * 50)
            logger.info("Testing validation for invalid alpha")
            alpha_args = {"title": "Bad Alpha", "x": [1, 2, 3], "y": [1, 2, 3], "alpha": 2.5}
            alpha_result = await session.call_tool("render_graph", alpha_args)
            assert len(alpha_result.content) > 0
            alpha_text = (
                alpha_result.content[0].text
                if hasattr(alpha_result.content[0], "text")
                else str(alpha_result.content[0])
            )
            assert "validation" in alpha_text.lower() and "alpha" in alpha_text.lower()
            logger.info("Validation correctly caught invalid alpha")

            print("\n" + "=" * 50)
            logger.info("All tests completed successfully")
            print("=" * 50)


def main():
    """Run the test"""
    logger = ConsoleLogger(name="mcp_test_main", level=logging.INFO)

    try:
        asyncio.run(test_mcp_server())
    except KeyboardInterrupt:
        logger.warning("Test interrupted by user")
    except Exception as e:
        logger.error("Test failed", error=str(e))
        import traceback

        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
