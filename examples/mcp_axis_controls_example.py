#!/usr/bin/env python3
"""
Example demonstrating MCP axis control parameters

This script shows how to use the new axis limit and tick control features
through the MCP protocol.
"""

import asyncio
import logging
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from app.auth import AuthService
from app.logger import ConsoleLogger


async def example_axis_limits():
    """Example: Using axis limits"""
    print("\n" + "=" * 60)
    print("Example 1: Axis Limits")
    print("=" * 60)

    # Create authentication token
    auth_service = AuthService(
        secret_key="test-secret-key-for-auth-testing",
        token_store_path="/tmp/gofr-plot_test_tokens.json",
    )
    token = auth_service.create_token(group="demo")

    # Connect to MCP server
    http_url = "http://localhost:8001/mcp/"
    async with streamablehttp_client(http_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Render graph with custom axis limits
            args = {
                "title": "Sales Data with Custom Range",
                "x": [1, 2, 3, 4, 5],
                "y": [120, 150, 135, 180, 200],
                "xlabel": "Quarter",
                "ylabel": "Sales ($K)",
                "type": "line",
                "xmin": 0,
                "xmax": 6,
                "ymin": 100,
                "ymax": 220,
                "color": "#2E86AB",
                "line_width": 2.5,
                "token": token,
            }

            result = await session.call_tool("render_graph", args)

            # Check result
            for content in result.content:
                if content.type == "text":
                    print(content.text)
                elif content.type == "image":
                    print(f"Image received: {len(content.data)} chars base64")


async def example_major_ticks():
    """Example: Using custom major ticks"""
    print("\n" + "=" * 60)
    print("Example 2: Major Ticks")
    print("=" * 60)

    auth_service = AuthService(
        secret_key="test-secret-key-for-auth-testing",
        token_store_path="/tmp/gofr-plot_test_tokens.json",
    )
    token = auth_service.create_token(group="demo")

    http_url = "http://localhost:8001/mcp/"
    async with streamablehttp_client(http_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Render graph with custom major ticks
            args = {
                "title": "Temperature Over 24 Hours",
                "x": [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24],
                "y": [15, 16, 18, 21, 24, 27, 29, 28, 26, 23, 20, 18, 16],
                "xlabel": "Hour",
                "ylabel": "Temperature (°C)",
                "type": "line",
                "x_major_ticks": [0, 6, 12, 18, 24],
                "y_major_ticks": [15, 20, 25, 30],
                "token": token,
            }

            result = await session.call_tool("render_graph", args)

            for content in result.content:
                if content.type == "text":
                    print(content.text)
                elif content.type == "image":
                    print(f"Image received: {len(content.data)} chars base64")


async def example_minor_ticks():
    """Example: Using major and minor ticks together"""
    print("\n" + "=" * 60)
    print("Example 3: Major and Minor Ticks")
    print("=" * 60)

    auth_service = AuthService(
        secret_key="test-secret-key-for-auth-testing",
        token_store_path="/tmp/gofr-plot_test_tokens.json",
    )
    token = auth_service.create_token(group="demo")

    http_url = "http://localhost:8001/mcp/"
    async with streamablehttp_client(http_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Render graph with major and minor ticks
            args = {
                "title": "Precise Measurement Data",
                "x": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                "y": [0, 10, 18, 24, 28, 30, 28, 24, 18, 10, 0],
                "xlabel": "Position (cm)",
                "ylabel": "Value",
                "type": "scatter",
                "xmin": 0,
                "xmax": 10,
                "ymin": 0,
                "ymax": 35,
                "x_major_ticks": [0, 5, 10],
                "x_minor_ticks": [1, 2, 3, 4, 6, 7, 8, 9],
                "y_major_ticks": [0, 10, 20, 30],
                "y_minor_ticks": [5, 15, 25],
                "marker_size": 50,
                "token": token,
            }

            result = await session.call_tool("render_graph", args)

            for content in result.content:
                if content.type == "text":
                    print(content.text)
                elif content.type == "image":
                    print(f"Image received: {len(content.data)} chars base64")


async def example_all_combined():
    """Example: All axis controls combined"""
    print("\n" + "=" * 60)
    print("Example 4: All Controls Combined")
    print("=" * 60)

    auth_service = AuthService(
        secret_key="test-secret-key-for-auth-testing",
        token_store_path="/tmp/gofr-plot_test_tokens.json",
    )
    token = auth_service.create_token(group="demo")

    http_url = "http://localhost:8001/mcp/"
    async with streamablehttp_client(http_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Render graph with all axis controls
            args = {
                "title": "Complete Control Example",
                "x": [1, 2, 3, 4, 5, 6, 7, 8],
                "y": [45, 52, 48, 65, 70, 68, 75, 80],
                "xlabel": "Week",
                "ylabel": "Performance Score",
                "type": "line",
                "xmin": 0,
                "xmax": 9,
                "ymin": 40,
                "ymax": 85,
                "x_major_ticks": [0, 2, 4, 6, 8],
                "y_major_ticks": [40, 50, 60, 70, 80],
                "x_minor_ticks": [1, 3, 5, 7],
                "y_minor_ticks": [45, 55, 65, 75],
                "color": "#E63946",
                "line_width": 3.0,
                "theme": "dark",
                "token": token,
            }

            result = await session.call_tool("render_graph", args)

            for content in result.content:
                if content.type == "text":
                    print(content.text)
                elif content.type == "image":
                    print(f"Image received: {len(content.data)} chars base64")


async def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("MCP Axis Control Examples")
    print("=" * 60)
    print("\nMake sure the MCP server is running:")
    print("  python -m app.main_mcp")
    print()

    try:
        await example_axis_limits()
        await example_major_ticks()
        await example_minor_ticks()
        await example_all_combined()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure the MCP server is running:")
        print("  python -m app.main_mcp")


if __name__ == "__main__":
    asyncio.run(main())
