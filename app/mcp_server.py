#!/usr/bin/env python3
"""MCP Server for Graph Rendering

This server exposes graph rendering capabilities through the Model Context Protocol.
It provides tools to render line and bar charts using matplotlib.

This server uses SSE (Server-Sent Events) transport, making it compatible with
n8n's MCP Client Tool and other modern MCP clients.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# Add parent directory to path to enable imports when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.render import GraphRenderer
from app.models import GraphData
from app.validation import GraphDataValidator
from app.logger import ConsoleLogger
import logging as python_logging
from datetime import datetime


# Initialize the MCP server
app = Server("gplot-renderer")
renderer = GraphRenderer()
validator = GraphDataValidator()
logger = ConsoleLogger(name="mcp_server", level=python_logging.INFO)


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools for graph rendering."""
    return [
        Tool(
            name="ping",
            description="Health check that returns the current server timestamp to verify the server is running.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="render_graph",
            description=(
                "Render a graph (line or bar chart) and return it as a base64-encoded PNG image. "
                "Provide data points, labels, and styling options to create the visualization."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the graph"},
                    "x": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "X-axis data points (list of numbers)",
                    },
                    "y": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Y-axis data points (list of numbers)",
                    },
                    "xlabel": {
                        "type": "string",
                        "description": "Label for the X-axis (default: 'X-axis')",
                        "default": "X-axis",
                    },
                    "ylabel": {
                        "type": "string",
                        "description": "Label for the Y-axis (default: 'Y-axis')",
                        "default": "Y-axis",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["line", "scatter", "bar"],
                        "description": "The type of the graph: 'line', 'scatter', or 'bar' (default: 'line')",
                        "default": "line",
                    },
                },
                "required": ["title", "x", "y"],
            },
        ),
    ]


@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any]
) -> list[TextContent | ImageContent | EmbeddedResource]:
    """
    Handle tool execution requests with comprehensive error handling.

    This function ensures the MCP server never crashes by catching all exceptions
    and returning meaningful error messages to the client.
    """

    if name == "ping":
        logger.info("Ping tool called")
        current_time = datetime.now().isoformat()
        logger.debug("Ping response", timestamp=current_time)
        return [
            TextContent(
                type="text", text=f"Server is running\nTimestamp: {current_time}\nService: gplot"
            )
        ]

    if name != "render_graph":
        logger.warning("Unknown tool requested", tool_name=name)
        return [
            TextContent(
                type="text",
                text=f"Error: Unknown tool '{name}'\n\nAvailable tools:\n- ping\n- render_graph",
            )
        ]

    logger.info("Render tool called")

    try:
        # Validate required arguments
        required_args = ["title", "x", "y"]
        missing_args = [arg for arg in required_args if arg not in arguments]
        if missing_args:
            logger.warning("Missing required arguments", missing=missing_args)
            return [
                TextContent(
                    type="text",
                    text=f"Missing required arguments: {', '.join(missing_args)}\n\n"
                    f"Required: title, x (array), y (array)\n"
                    f"Optional: xlabel, ylabel, type, format, color, line_width, marker_size, alpha, theme",
                )
            ]

        # Validate x and y are arrays
        if not isinstance(arguments.get("x"), list):
            logger.warning("Invalid x argument type", type=type(arguments.get("x")).__name__)
            return [
                TextContent(
                    type="text",
                    text="Error: 'x' must be an array of numbers\n\nExample: x=[1, 2, 3, 4, 5]",
                )
            ]

        if not isinstance(arguments.get("y"), list):
            logger.warning("Invalid y argument type", type=type(arguments.get("y")).__name__)
            return [
                TextContent(
                    type="text",
                    text="Error: 'y' must be an array of numbers\n\nExample: y=[10, 20, 15, 30, 25]",
                )
            ]

        logger.debug(
            "Request validated",
            title=arguments.get("title"),
            data_points=len(arguments.get("x", [])),
            chart_type=arguments.get("type", "line"),
        )

        # Create GraphData from arguments - pass all optional fields
        try:
            graph_data = GraphData(
                title=arguments["title"],
                x=arguments["x"],
                y=arguments["y"],
                xlabel=arguments.get("xlabel", "X-axis"),
                ylabel=arguments.get("ylabel", "Y-axis"),
                type=arguments.get("type", "line"),
                format=arguments.get("format", "png"),
                return_base64=True,
                color=arguments.get("color"),
                line_width=arguments.get("line_width", 2.0),
                marker_size=arguments.get("marker_size", 36.0),
                alpha=arguments.get("alpha", 1.0),
                theme=arguments.get("theme", "light"),
            )
            logger.debug("GraphData created successfully")
        except Exception as e:
            logger.error("Failed to create GraphData", error=str(e), error_type=type(e).__name__)
            return [
                TextContent(
                    type="text",
                    text=f"Error creating graph data: {str(e)}\n\n"
                    f"Suggestions:\n"
                    f"- Ensure x and y are arrays of numbers\n"
                    f"- Check that all numeric parameters (alpha, line_width, marker_size) are valid numbers",
                )
            ]

        # Validate the input data
        try:
            logger.debug("Validating graph data")
            validation_result = validator.validate(graph_data)

            if not validation_result.is_valid:
                logger.warning(
                    "Validation failed",
                    error_count=len(validation_result.errors),
                    errors=[e.field for e in validation_result.errors],
                )
                # Return validation errors as text
                error_message = validation_result.get_error_summary()
                return [TextContent(type="text", text=f"Validation Error:\n\n{error_message}")]
            logger.debug("Validation passed")
        except Exception as e:
            logger.error("Validation error", error=str(e), error_type=type(e).__name__)
            return [
                TextContent(
                    type="text",
                    text=f"Error during validation: {str(e)}\n\n"
                    f"The validation system encountered an unexpected error.\n"
                    f"Please check your input data format.",
                )
            ]

        # Render the graph (will be base64 string)
        try:
            logger.debug("Starting render")
            base64_image = renderer.render(graph_data)
            logger.info(
                "Render completed successfully",
                chart_type=graph_data.type,
                format=graph_data.format,
                output_size=len(base64_image) if isinstance(base64_image, (str, bytes)) else 0,
            )
        except ValueError as e:
            logger.error("Configuration error", error=str(e), chart_type=graph_data.type)
            # Handle known validation errors from renderer
            return [
                TextContent(
                    type="text",
                    text=f"Configuration Error: {str(e)}\n\n"
                    f"Suggestions:\n"
                    f"- Check that the chart type is valid (line, scatter, bar)\n"
                    f"- Verify the theme name is correct (light, dark)\n"
                    f"- Ensure the format is supported (png, jpg, svg, pdf)",
                )
            ]
        except RuntimeError as e:
            logger.error("Runtime error during render", error=str(e), chart_type=graph_data.type)
            # Handle rendering errors
            return [
                TextContent(
                    type="text",
                    text=f"Rendering Error: {str(e)}\n\n"
                    f"The graph rendering process failed.\n"
                    f"Suggestions:\n"
                    f"- Verify your data values are valid numbers\n"
                    f"- Check that arrays are not empty\n"
                    f"- Try reducing the data size or simplifying the request",
                )
            ]
        except Exception as e:
            logger.error(
                "Unexpected error during render", error=str(e), error_type=type(e).__name__
            )
            return [
                TextContent(
                    type="text",
                    text=f"Unexpected rendering error: {str(e)}\n\n"
                    f"An unexpected error occurred during rendering.\n"
                    f"Please verify your input data and try again.",
                )
            ]

        # Ensure it's a string for ImageContent
        try:
            if isinstance(base64_image, bytes):
                base64_image = base64_image.decode("utf-8")
            elif isinstance(base64_image, (bytearray, memoryview)):
                base64_image = bytes(base64_image).decode("utf-8")
            logger.debug("Image encoded successfully")
        except Exception as e:
            logger.error("Failed to encode image", error=str(e))
            return [
                TextContent(
                    type="text",
                    text=f"Error encoding image: {str(e)}\n\n"
                    f"Failed to convert the rendered image to base64 format.",
                )
            ]

        # Type assertion for type checker - base64_image is now definitely a str
        base64_str: str = str(base64_image)

        # Return the rendered image
        try:
            logger.info("Returning successful response", title=graph_data.title)
            result: list[TextContent | ImageContent | EmbeddedResource] = [
                ImageContent(type="image", data=base64_str, mimeType="image/png"),
                TextContent(
                    type="text",
                    text=f"Successfully rendered {graph_data.type} chart: '{graph_data.title}'",
                ),
            ]
            return result
        except Exception as e:
            logger.error("Failed to create response", error=str(e))
            return [
                TextContent(
                    type="text",
                    text=f"Error creating response: {str(e)}\n\n"
                    f"The image was rendered but could not be packaged for return.",
                )
            ]

    except KeyboardInterrupt:
        # Handle graceful shutdown
        logger.info("Interrupted by user")
        raise
    except Exception as e:
        # Ultimate fallback - catch any unexpected exceptions
        logger.critical("Critical error in tool handler", error=str(e), error_type=type(e).__name__)
        return [
            TextContent(
                type="text",
                text=f"Critical Error: {str(e)}\n\n"
                f"An unexpected error occurred. This should not happen.\n"
                f"Please report this issue with your input data.\n\n"
                f"Error type: {type(e).__name__}",
            )
        ]


# Create SSE transport with /messages/ endpoint for POSTing messages
sse = SseServerTransport("/messages/")


async def handle_sse(request: Request) -> Response:
    """Handle SSE connections for MCP protocol."""
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:  # type: ignore[reportPrivateUsage]
        await app.run(
            streams[0],
            streams[1],
            InitializationOptions(
                server_name="gplot-renderer",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
    return Response()


# Create Starlette app for SSE transport
starlette_app = Starlette(
    debug=True,
    routes=[
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
        Mount("/messages/", app=sse.handle_post_message),
    ],
)


async def main():
    """
    Run the MCP server with SSE transport and comprehensive error handling.

    The server runs on port 8001 by default and serves MCP protocol over SSE.
    """
    import uvicorn

    logger.info("Starting MCP SSE server", version="1.0.0", port=8001)
    try:
        config = uvicorn.Config(
            starlette_app,
            host="0.0.0.0",
            port=8001,
            log_level="info",
        )
        server = uvicorn.Server(config)
        logger.info("Server initialized, listening on http://0.0.0.0:8001/sse")
        await server.serve()
    except KeyboardInterrupt:
        # Handle graceful shutdown
        logger.info("Server stopped by user")
        print("\nServer stopped by user", file=sys.stderr)
    except Exception as e:
        logger.critical("Fatal server error", error=str(e), error_type=type(e).__name__)
        print(f"Fatal server error: {str(e)}", file=sys.stderr)
        print(f"Error type: {type(e).__name__}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Failed to start server: {str(e)}", file=sys.stderr)
        sys.exit(1)
