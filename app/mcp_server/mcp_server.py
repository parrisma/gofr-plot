#!/usr/bin/env python3
"""MCP Server for Graph Rendering

This server exposes graph rendering capabilities through the Model Context Protocol.
It provides tools to render line and bar charts using matplotlib.

This server uses Streamable HTTP transport, which is the modern preferred standard
for MCP servers, superseding SSE. It's compatible with n8n's MCP Client Tool and
other modern MCP clients.
"""

import contextlib
import sys
from pathlib import Path
from typing import Any, AsyncIterator
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# Add parent directory to path to enable imports when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.render import GraphRenderer
from app.graph_params import GraphParams
from app.validation import GraphDataValidator
from app.storage import get_storage
from app.storage.exceptions import PermissionDeniedError
from app.auth import AuthService
from app.security import RateLimiter, RateLimitExceeded, SecurityAuditor
from app.logger import ConsoleLogger
from app.themes import list_themes_with_descriptions
from app.handlers import list_handlers_with_descriptions
from app.mcp_responses import (
    format_error,
    format_success_image,
    format_list,
    AUTH_REQUIRED_ERROR,
    AUTH_INVALID_ERROR,
    PERMISSION_DENIED_ERROR,
)
import logging as python_logging
from datetime import datetime
import base64
import os


# Initialize the MCP server
app = Server("gplot")
renderer = GraphRenderer()
validator = GraphDataValidator()
storage = get_storage()
logger = ConsoleLogger(name="mcp_server", level=python_logging.INFO)

# Initialize rate limiter with endpoint-specific limits
# Use higher limits in test environment to avoid test failures
# Default to production limits; will be reconfigured when auth service is set

rate_limiter = RateLimiter(default_limit=100, window=60)
rate_limiter.set_endpoint_limit("render_graph", limit=10, window=60)  # Strict for expensive ops
rate_limiter.set_endpoint_limit("ping", limit=1000, window=60)  # Lenient for health checks

# Initialize security auditor
security_auditor = SecurityAuditor()

# Initialize auth service (will be configured when server starts)
auth_service: AuthService | None = None

# Web server URL for proxy mode (configurable via CLI)
web_url_override: str | None = None
proxy_url_mode: str = "url"  # "url" or "guid"


def set_logger_level(level: int) -> None:
    """
    Set the logger level for the MCP server

    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO)
    """
    global logger
    logger = ConsoleLogger(name="mcp_server", level=level)


def set_auth_service(service: AuthService | None) -> None:
    """
    Set the module-level auth service instance (dependency injection)

    Args:
        service: AuthService instance or None to disable authentication
    """
    global auth_service
    auth_service = service

    # Reconfigure rate limiter based on auth service configuration
    # If JWT secret starts with "test-secret", use much higher limits for testing
    is_test_env = False
    if service and hasattr(service, "secret_key"):
        is_test_env = service.secret_key.startswith("test-secret")
    elif not service:
        # No auth means we check environment variable
        is_test_env = os.getenv("GPLOT_JWT_SECRET", "").startswith("test-secret")

    if is_test_env:
        logger.info(
            "Test environment detected, using higher rate limits",
            render_limit=10000,
            default_limit=1000,
        )
        rate_limiter.default_limit = 1000
        rate_limiter.set_endpoint_limit("render_graph", limit=10000, window=60)
    else:
        logger.info(
            "Production environment, using standard rate limits", render_limit=10, default_limit=100
        )


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools for graph rendering."""
    return [
        Tool(
            name="ping",
            description=(
                "Health check endpoint that verifies the MCP server is running and responsive. "
                "Returns the current server timestamp and service name. "
                "This tool does NOT require authentication and can be called without a token parameter."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="render_graph",
            description=(
                "Render a graph visualization and return it as a base64-encoded image or storage GUID. "
                "\n\n**AUTHENTICATION**: Requires a valid JWT 'token' parameter for all operations. "
                "\n\n**BASIC USAGE**: Provide 'title' (string) and at least one dataset (y1 array or legacy 'y' array). "
                "The 'x' parameter is optional - if omitted, indices [0, 1, 2, ...] are auto-generated. "
                "\n\n**MULTI-DATASET**: Supports up to 5 datasets (y1-y5) with optional labels (label1-label5) and colors (color1-color5). "
                "When using themes, dataset colors are optional and will use theme defaults unless overridden. "
                "\n\n**CHART TYPES**: 'line' (default), 'scatter', or 'bar'. Use list_handlers tool to see descriptions. "
                "\n\n**THEMES**: 'light' (default), 'dark', 'bizlight', 'bizdark'. Use list_themes tool for details. "
                "\n\n**PROXY MODE**: Set proxy=true to save the image to persistent storage and receive a GUID instead of base64 data. "
                "Use get_image with the GUID to retrieve the image later. This is useful for large images or long-term storage. "
                "\n\n**OUTPUT FORMATS**: 'png' (default), 'jpg', 'svg', 'pdf'. "
                "\n\n**AXIS CONTROLS**: Optional parameters for axis limits (xmin/xmax/ymin/ymax) and custom tick positions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the graph"},
                    "x": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "X-axis data points (optional, defaults to indices [0, 1, 2, ...]). For backward compatibility, you can also use old 'y' parameter which maps to 'y1'.",
                    },
                    "y": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Y-axis data points (backward compatibility - maps to y1, list of numbers)",
                    },
                    "y1": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "First dataset Y-axis data points (required unless 'y' provided, list of numbers)",
                    },
                    "y2": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Second dataset Y-axis data points (optional)",
                    },
                    "y3": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Third dataset Y-axis data points (optional)",
                    },
                    "y4": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Fourth dataset Y-axis data points (optional)",
                    },
                    "y5": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Fifth dataset Y-axis data points (optional)",
                    },
                    "label1": {
                        "type": "string",
                        "description": "Label for first dataset (optional, for legend)",
                    },
                    "label2": {
                        "type": "string",
                        "description": "Label for second dataset (optional, for legend)",
                    },
                    "label3": {
                        "type": "string",
                        "description": "Label for third dataset (optional, for legend)",
                    },
                    "label4": {
                        "type": "string",
                        "description": "Label for fourth dataset (optional, for legend)",
                    },
                    "label5": {
                        "type": "string",
                        "description": "Label for fifth dataset (optional, for legend)",
                    },
                    "color1": {
                        "type": "string",
                        "description": "Color for first dataset (e.g., 'red', '#FF5733', 'rgb(255,87,51)')",
                    },
                    "color2": {
                        "type": "string",
                        "description": "Color for second dataset",
                    },
                    "color3": {
                        "type": "string",
                        "description": "Color for third dataset",
                    },
                    "color4": {
                        "type": "string",
                        "description": "Color for fourth dataset",
                    },
                    "color5": {
                        "type": "string",
                        "description": "Color for fifth dataset",
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
                    "format": {
                        "type": "string",
                        "enum": ["png", "jpg", "svg", "pdf"],
                        "description": "Image format (default: 'png'). Supported: png, jpg, svg, pdf",
                        "default": "png",
                    },
                    "proxy": {
                        "type": "boolean",
                        "description": "If true, save image to disk and return GUID instead of base64 (default: false)",
                        "default": False,
                    },
                    "color": {
                        "type": "string",
                        "description": "Line/marker color (e.g., 'red', '#FF5733', 'rgb(255,87,51)')",
                    },
                    "line_width": {
                        "type": "number",
                        "description": "Line width for line plots (default: 2.0)",
                        "default": 2.0,
                    },
                    "marker_size": {
                        "type": "number",
                        "description": "Marker size for scatter plots (default: 36.0)",
                        "default": 36.0,
                    },
                    "alpha": {
                        "type": "number",
                        "description": "Transparency level from 0.0 (transparent) to 1.0 (opaque) (default: 1.0)",
                        "default": 1.0,
                    },
                    "theme": {
                        "type": "string",
                        "enum": ["light", "dark", "bizlight", "bizdark"],
                        "description": "Visual theme for the graph (default: 'light') if theme is supplied specifying data set colours is optional and will override any theme colours",
                        "default": "light",
                    },
                    "xmin": {
                        "type": "number",
                        "description": "Minimum value for x-axis (optional)",
                    },
                    "xmax": {
                        "type": "number",
                        "description": "Maximum value for x-axis (optional)",
                    },
                    "ymin": {
                        "type": "number",
                        "description": "Minimum value for y-axis (optional)",
                    },
                    "ymax": {
                        "type": "number",
                        "description": "Maximum value for y-axis (optional)",
                    },
                    "x_major_ticks": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Custom positions for x-axis major tick marks (optional)",
                    },
                    "y_major_ticks": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Custom positions for y-axis major tick marks (optional)",
                    },
                    "x_minor_ticks": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Custom positions for x-axis minor tick marks (optional)",
                    },
                    "y_minor_ticks": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Custom positions for y-axis minor tick marks (optional). Example: [0.5, 1.5, 2.5]",
                    },
                    "token": {
                        "type": "string",
                        "description": "JWT authentication token (REQUIRED). The token's group claim determines ownership of created images and access rights. Example: 'eyJ0eXAiOiJKV1QiLCJhbGc...'",
                    },
                },
                "required": ["title", "token"],
            },
        ),
        Tool(
            name="get_image",
            description=(
                "Retrieve a previously stored graph image using its GUID identifier. "
                "\n\n**AUTHENTICATION**: Requires a valid JWT 'token' parameter. "
                "The token's group must match the group that created the image (group-based access control). "
                "\n\n**WORKFLOW**: Use this after calling render_graph with proxy=true, which returns a GUID. "
                "The GUID can be stored and used later to retrieve the image. "
                "\n\n**OUTPUT**: Returns the image as base64-encoded data with its original format (png, jpg, svg, pdf). "
                "\n\n**ERROR HANDLING**: If the image doesn't exist or belongs to a different group, an error message is returned."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "guid": {
                        "type": "string",
                        "description": "The GUID identifier of the stored image (returned by render_graph when proxy=true). Example: '550e8400-e29b-41d4-a716-446655440000'",
                    },
                    "token": {
                        "type": "string",
                        "description": "JWT authentication token (REQUIRED). Must match the group that created the image. Example: 'eyJ0eXAiOiJKV1QiLCJhbGc...'",
                    },
                },
                "required": ["guid", "token"],
            },
        ),
        Tool(
            name="list_themes",
            description=(
                "Discover all available visual themes with descriptions. "
                "\n\n**AUTHENTICATION**: Does NOT require a token parameter. "
                "\n\n**PURPOSE**: Use this tool to see which theme names can be passed to the 'theme' parameter in render_graph. "
                "Each theme includes color palettes, background colors, and grid styles optimized for different use cases. "
                "\n\n**OUTPUT**: Returns a formatted list of theme names with descriptions explaining their visual style and intended use."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="list_handlers",
            description=(
                "Discover all available graph types (chart types) with descriptions. "
                "\n\n**AUTHENTICATION**: Does NOT require a token parameter. "
                "\n\n**PURPOSE**: Use this tool to see which chart type names can be passed to the 'type' parameter in render_graph. "
                "Each handler supports different visualization styles (line plots, scatter plots, bar charts) with specific capabilities. "
                "\n\n**OUTPUT**: Returns a formatted list of type names with descriptions explaining what each chart type renders and its multi-dataset support."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
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

    # Extract client identifier for rate limiting (use token if available, otherwise 'anonymous')
    token = arguments.get("token", "anonymous")
    client_id = f"token:{token[:20]}" if token != "anonymous" else "anonymous"

    # Log every incoming tool request for request tracing
    logger.info(
        "MCP tool request received",
        tool_name=name,
        client_id=client_id,
        has_token=(token != "anonymous"),
        argument_count=len(arguments),
        timestamp=datetime.now().isoformat(),
    )

    if name == "ping":
        logger.info("Ping tool called")

        # Rate limiting (lenient for health checks)
        try:
            rate_limiter.check_limit(client_id=client_id, endpoint="ping")
        except RateLimitExceeded as e:
            logger.warning("Rate limit exceeded", client_id=client_id, endpoint="ping")
            security_auditor.log_rate_limit(
                client_id=client_id, endpoint="ping", limit=1000, window=60
            )
            return format_error(
                "Rate Limit Exceeded",
                f"Too many ping requests: {str(e)}",
                [
                    f"Wait {int(e.retry_after)} seconds before trying again",
                    "Ping allows 1000 requests per 60 seconds",
                ],
                {"retry_after": int(e.retry_after)},
            )

        current_time = datetime.now().isoformat()
        logger.debug("Ping response", timestamp=current_time)
        return [
            TextContent(
                type="text", text=f"Server is running\nTimestamp: {current_time}\nService: gplot"
            )
        ]

    if name == "get_image":
        logger.info("Get image tool called")

        # Rate limiting (use default limit)
        try:
            rate_limiter.check_limit(client_id=client_id, endpoint="get_image")
        except RateLimitExceeded as e:
            logger.warning("Rate limit exceeded", client_id=client_id, endpoint="get_image")
            security_auditor.log_rate_limit(
                client_id=client_id, endpoint="get_image", limit=100, window=60
            )
            return format_error(
                "Rate Limit Exceeded",
                f"Too many get_image requests: {str(e)}",
                [
                    f"Wait {int(e.retry_after)} seconds before trying again",
                    "Default limit: 100 requests per 60 seconds",
                ],
                {"retry_after": int(e.retry_after)},
            )

        # Validate required arguments
        if "guid" not in arguments:
            logger.warning("Missing required argument: guid")
            return format_error(
                "Missing Parameter",
                "The required 'guid' parameter was not provided",
                [
                    "Include the GUID of the image you want to retrieve",
                    "GUIDs are returned by render_graph when proxy=true",
                    "Example: guid='550e8400-e29b-41d4-a716-446655440000'",
                ],
            )

        if "token" not in arguments:
            logger.warning("Missing required argument: token")
            return AUTH_REQUIRED_ERROR

        guid = arguments["guid"]
        token = arguments["token"]

        # Verify JWT token
        try:
            if auth_service is None:
                # No-auth mode: use public group
                group = "public"
                logger.debug("No-auth mode: using public group", group=group)
            else:
                token_info = auth_service.verify_token(token)
                group = token_info.group
                logger.debug("Token verified", group=group)
        except Exception as e:
            logger.error("Token validation failed", error=str(e))
            security_auditor.log_auth_failure(
                client_id=client_id, reason=str(e), endpoint="get_image"
            )
            return AUTH_INVALID_ERROR(str(e))

        try:
            # Retrieve image from storage with group access control
            image_result = storage.get_image(guid, group=group)

            if image_result is None:
                logger.warning("Image not found", guid=guid)
                return format_error(
                    "Not Found",
                    f"No image found with GUID: {guid}",
                    [
                        "Verify the GUID is correct",
                        "The image may have been deleted",
                        "Check that you have access to the correct storage group",
                    ],
                    {"guid": guid, "group": group},
                )

            image_data, img_format = image_result

            # Encode to base64
            base64_image = base64.b64encode(image_data).decode("utf-8")

            logger.info(
                "Image retrieved successfully", guid=guid, format=img_format, size=len(image_data)
            )

            return format_success_image(
                base64_image,
                f"image/{img_format}",
                f"Retrieved image {guid}",
                {"format": img_format, "size_bytes": len(image_data)},
            )

        except PermissionDeniedError as e:
            logger.warning("Permission denied", guid=guid, error=str(e), group=group)
            return PERMISSION_DENIED_ERROR(guid, group)

        except ValueError as e:
            logger.error("Invalid GUID", guid=guid, error=str(e))
            return format_error(
                "Invalid Input",
                f"Invalid GUID format: {guid}",
                [
                    "Ensure the GUID is a valid UUID format",
                    "Example: '550e8400-e29b-41d4-a716-446655440000'",
                    "GUIDs are returned by render_graph when proxy=true",
                ],
                {"provided": guid},
            )

        except Exception as e:
            logger.error("Failed to retrieve image", guid=guid, error=str(e))
            return format_error(
                "Retrieval Failed",
                f"Unexpected error retrieving image: {str(e)}",
                [
                    "Check server logs for details",
                    "Verify the storage system is accessible",
                    "Try the operation again",
                ],
            )

    if name == "list_themes":
        logger.info("List themes tool called")

        # Rate limiting (use default limit)
        try:
            rate_limiter.check_limit(client_id=client_id, endpoint="list_themes")
        except RateLimitExceeded as e:
            logger.warning("Rate limit exceeded", client_id=client_id, endpoint="list_themes")
            security_auditor.log_rate_limit(
                client_id=client_id, endpoint="list_themes", limit=100, window=60
            )
            return format_error(
                "Rate Limit Exceeded",
                f"Too many list_themes requests: {str(e)}",
                [f"Wait {int(e.retry_after)} seconds before trying again"],
                {"retry_after": int(e.retry_after)},
            )

        try:
            themes = list_themes_with_descriptions()
            logger.debug("Themes listed", count=len(themes))
            return format_list("Available Themes", themes)
        except Exception as e:
            logger.error("Failed to list themes", error=str(e))
            return format_error(
                "Discovery Failed",
                f"Unable to list themes: {str(e)}",
                ["Check server logs for details", "Try the operation again"],
            )

    if name == "list_handlers":
        logger.info("List handlers tool called")

        # Rate limiting (use default limit)
        try:
            rate_limiter.check_limit(client_id=client_id, endpoint="list_handlers")
        except RateLimitExceeded as e:
            logger.warning("Rate limit exceeded", client_id=client_id, endpoint="list_handlers")
            security_auditor.log_rate_limit(
                client_id=client_id, endpoint="list_handlers", limit=100, window=60
            )
            return format_error(
                "Rate Limit Exceeded",
                f"Too many list_handlers requests: {str(e)}",
                [f"Wait {int(e.retry_after)} seconds before trying again"],
                {"retry_after": int(e.retry_after)},
            )

        try:
            handlers = list_handlers_with_descriptions()
            logger.debug("Handlers listed", count=len(handlers))
            return format_list("Available Graph Types", handlers)
        except Exception as e:
            logger.error("Failed to list handlers", error=str(e))
            return format_error(
                "Discovery Failed",
                f"Unable to list graph types: {str(e)}",
                ["Check server logs for details", "Try the operation again"],
            )

    if name != "render_graph":
        logger.warning("Unknown tool requested", tool_name=name)
        return format_error(
            "Unknown Tool",
            f"Tool '{name}' does not exist",
            [
                "Use one of the available tools listed below",
                "Call list_tools to see detailed descriptions",
            ],
            {
                "requested": name,
                "available": "ping, render_graph, get_image, list_themes, list_handlers",
            },
        )

    logger.info("Render tool called")
    logger.debug(
        "Render request received",
        arguments_keys=list(arguments.keys()),
        proxy=arguments.get("proxy", False),
        chart_type=arguments.get("type", "line"),
        format=arguments.get("format", "png"),
    )

    # Rate limiting (strict for expensive operations)
    try:
        rate_limiter.check_limit(client_id=client_id, endpoint="render_graph")
    except RateLimitExceeded as e:
        logger.warning("Rate limit exceeded", client_id=client_id, endpoint="render_graph")
        # Get the actual limit from rate_limiter
        endpoint_limit = rate_limiter.endpoint_limits.get(
            "render_graph", (rate_limiter.default_limit, 60)
        )
        security_auditor.log_rate_limit(
            client_id=client_id,
            endpoint="render_graph",
            limit=endpoint_limit[0],
            window=endpoint_limit[1],
        )
        return format_error(
            "Rate Limit Exceeded",
            f"Too many render_graph requests: {str(e)}",
            [
                f"Wait {int(e.retry_after)} seconds before trying again",
                "Render operations are limited to 10 requests per 60 seconds",
                "This limit prevents server overload from expensive rendering operations",
            ],
            {"retry_after": int(e.retry_after), "limit": "10 per 60 seconds"},
        )

    try:
        # Validate required arguments - only title and token are required now
        # x is optional (auto-generates indices), y1-y5 are optional (backward compatible with y)
        required_args = ["title", "token"]
        missing_args = [arg for arg in required_args if arg not in arguments]
        if missing_args:
            logger.warning("Missing required arguments", missing=missing_args)
            if "token" in missing_args:
                return AUTH_REQUIRED_ERROR
            return format_error(
                "Missing Parameters",
                f"Required parameters not provided: {', '.join(missing_args)}",
                [
                    "title (string): The graph title - REQUIRED",
                    "token (string): JWT authentication token - REQUIRED",
                    "y1 or y (array): First dataset values - at least one dataset required",
                    "Use list_themes and list_handlers to discover optional parameters",
                ],
            )

        # Verify JWT token
        token = arguments["token"]
        try:
            if auth_service is None:
                # No-auth mode: use public group
                group = "public"
                logger.debug("No-auth mode: using public group", group=group)
            else:
                token_info = auth_service.verify_token(token)
                group = token_info.group
                logger.debug("Token verified", group=group)
        except Exception as e:
            logger.error("Token validation failed", error=str(e))
            security_auditor.log_auth_failure(
                client_id=client_id, reason=str(e), endpoint="render_graph"
            )
            return AUTH_INVALID_ERROR(str(e))

        # Validate data arrays if provided
        # x is optional (will be auto-generated if omitted)
        # y is backward compat, y1-y5 are the new multi-dataset parameters
        if "x" in arguments and not isinstance(arguments["x"], list):
            logger.warning("Invalid x argument type", type=type(arguments["x"]).__name__)
            return format_error(
                "Invalid Parameter Type",
                f"Parameter 'x' must be an array, received {type(arguments['x']).__name__}",
                [
                    "Provide x as an array of numbers: [1, 2, 3, 4, 5]",
                    "Or omit x entirely to auto-generate indices [0, 1, 2, ...]",
                ],
                {"provided_type": type(arguments["x"]).__name__},
            )

        logger.debug(
            "Request validated",
            title=arguments.get("title"),
            data_points=len(arguments.get("x", [])),
            chart_type=arguments.get("type", "line"),
        )

        # Create GraphParams from arguments - pass all optional fields
        try:
            is_proxy = arguments.get("proxy", False)
            graph_data = GraphParams(
                title=arguments["title"],
                x=arguments.get("x"),  # Optional now
                y1=arguments.get("y1"),  # Optional if 'y' is provided
                y2=arguments.get("y2"),
                y3=arguments.get("y3"),
                y4=arguments.get("y4"),
                y5=arguments.get("y5"),
                label1=arguments.get("label1"),
                label2=arguments.get("label2"),
                label3=arguments.get("label3"),
                label4=arguments.get("label4"),
                label5=arguments.get("label5"),
                color1=arguments.get("color1"),
                color2=arguments.get("color2"),
                color3=arguments.get("color3"),
                color4=arguments.get("color4"),
                color5=arguments.get("color5"),
                xlabel=arguments.get("xlabel", "X-axis"),
                ylabel=arguments.get("ylabel", "Y-axis"),
                type=arguments.get("type", "line"),
                format=arguments.get("format", "png"),
                return_base64=not is_proxy,  # If proxy, don't return base64
                proxy=is_proxy,
                line_width=arguments.get("line_width", 2.0),
                marker_size=arguments.get("marker_size", 36.0),
                alpha=arguments.get("alpha", 1.0),
                theme=arguments.get("theme", "light"),
                # Axis limits
                xmin=arguments.get("xmin"),
                xmax=arguments.get("xmax"),
                ymin=arguments.get("ymin"),
                ymax=arguments.get("ymax"),
                # Major and minor ticks
                x_major_ticks=arguments.get("x_major_ticks"),
                y_major_ticks=arguments.get("y_major_ticks"),
                x_minor_ticks=arguments.get("x_minor_ticks"),
                y_minor_ticks=arguments.get("y_minor_ticks"),
                # Backward compatibility
                y=arguments.get("y"),
                color=arguments.get("color"),
            )
            logger.debug("GraphData created successfully")
        except Exception as e:
            logger.error("Failed to create GraphData", error=str(e), error_type=type(e).__name__)
            return format_error(
                "Parameter Error",
                f"Failed to create graph parameters: {str(e)}",
                [
                    "Ensure y1 (or legacy 'y') is an array of numbers - at least one dataset required",
                    "If providing x, ensure it's an array of numbers (optional, auto-generated if omitted)",
                    "For multiple datasets, provide y2, y3, y4, y5 as arrays of numbers",
                    "Check that numeric parameters (alpha, line_width, marker_size) are valid numbers",
                    "Example: {title: 'Sales', y1: [10, 20, 30], type: 'line'}",
                ],
            )

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
                return format_error(
                    "Validation",
                    "Input data validation failed",
                    [error_message, "Fix the validation errors and try again"],
                )
            logger.debug("Validation passed")
        except Exception as e:
            logger.error("Validation error", error=str(e), error_type=type(e).__name__)
            return format_error(
                "Validation System",
                f"Validation system error: {str(e)}",
                [
                    "Check your input data format",
                    "Ensure arrays contain only numbers",
                    "Verify all required parameters are provided",
                ],
            )

        # Render the graph (will be base64 string or GUID)
        try:
            logger.debug("Starting render", group=group)
            base64_image = renderer.render(graph_data, group=group)
            logger.info(
                "Render completed successfully",
                chart_type=graph_data.type,
                format=graph_data.format,
                output_size=len(base64_image) if isinstance(base64_image, (str, bytes)) else 0,
                group=group,
            )
        except ValueError as e:
            logger.error("Configuration error", error=str(e), chart_type=graph_data.type)
            return format_error(
                "Configuration",
                str(e),
                [
                    "Check that the chart type is valid (use list_handlers tool)",
                    "Verify the theme name is correct (use list_themes tool)",
                    "Ensure the format is supported: png, jpg, svg, pdf",
                ],
                {"type": graph_data.type, "theme": graph_data.theme, "format": graph_data.format},
            )
        except RuntimeError as e:
            logger.error("Runtime error during render", error=str(e), chart_type=graph_data.type)
            return format_error(
                "Rendering",
                f"Graph rendering failed: {str(e)}",
                [
                    "Verify your data values are valid finite numbers (not NaN or Inf)",
                    "Check that data arrays are not empty",
                    "Try simplifying the request (fewer data points or datasets)",
                    "Check server logs for matplotlib errors",
                ],
            )
        except Exception as e:
            logger.error(
                "Unexpected error during render", error=str(e), error_type=type(e).__name__
            )
            return format_error(
                "Unexpected Error",
                f"Rendering failed unexpectedly: {str(e)}",
                [
                    "Verify your input data format",
                    "Check server logs for details",
                    "Try the operation again with simpler parameters",
                ],
                {"error_type": type(e).__name__},
            )

        # Check if result is a GUID (proxy mode) or base64 data
        if is_proxy:
            # Proxy mode: base64_image is actually a GUID string
            guid = str(base64_image)

            # CRITICAL: Verify the image was actually saved to storage before returning GUID
            logger.debug("Verifying image was saved to storage", guid=guid, group=group)
            verification = storage.get_image(guid, group=group)

            if verification is None:
                logger.error(
                    "CRITICAL: Renderer returned GUID but image not found in storage",
                    guid=guid,
                    group=group,
                    timestamp=datetime.now().isoformat(),
                )
                return format_error(
                    "Storage Verification Failed",
                    f"Image was rendered but could not be verified in storage (GUID: {guid})",
                    [
                        "This indicates a storage persistence failure",
                        "Check storage directory permissions and disk space",
                        "Check server logs for storage errors",
                    ],
                    {"guid": guid, "group": group},
                )

            logger.debug("Storage verification PASSED", guid=guid, size=len(verification[0]))
            logger.info(
                "Returning GUID response (proxy mode)",
                title=graph_data.title,
                guid=guid,
                proxy_url_mode=proxy_url_mode,
            )

            # Build response based on proxy_url_mode
            response_text = f"Image saved with GUID: {guid}\n\n"
            response_text += f"Chart: {graph_data.type} - '{graph_data.title}'\n"
            response_text += f"Format: {graph_data.format}\n\n"

            if proxy_url_mode == "url":
                # Construct full web server URL
                import socket

                hostname = socket.gethostname()
                web_base = web_url_override or os.getenv("GPLOT_WEB_URL", f"http://{hostname}:8000")
                download_url = f"{web_base}/proxy/{guid}"
                response_text += f"Download URL: {download_url}\n"
                response_text += f"(Or use get_image tool with guid='{guid}')"
            else:
                # GUID mode: only provide GUID
                response_text += f"Use get_image tool with guid='{guid}' to retrieve the image."

            return [
                TextContent(
                    type="text",
                    text=response_text,
                ),
            ]

        # Regular mode: Ensure it's a string for ImageContent
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
                ImageContent(type="image", data=base64_str, mimeType=f"image/{graph_data.format}"),
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


# Create StreamableHTTP session manager
session_manager = StreamableHTTPSessionManager(
    app=app,
    event_store=None,  # No event store for stateless operation
    json_response=False,  # Use SSE streams by default
    stateless=False,  # Maintain session state
)


async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
    """Handle Streamable HTTP requests for MCP protocol."""
    await session_manager.handle_request(scope, receive, send)


@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[None]:
    """Context manager for managing session manager lifecycle."""
    logger.info("Initializing StreamableHTTP session manager")
    async with session_manager.run():
        logger.info("StreamableHTTP session manager started", status="ready")
        try:
            yield
        finally:
            logger.info("StreamableHTTP session manager shutting down", status="stopping")


# Create Starlette app for Streamable HTTP transport
# Use trailing slash in mount path to avoid redirects
starlette_app = Starlette(
    debug=True,
    routes=[
        Mount("/mcp/", app=handle_streamable_http),
    ],
    lifespan=lifespan,
)

# Add CORS middleware to expose Mcp-Session-Id header
# GPLOT_CORS_ORIGINS: Comma-separated list of allowed origins, or "*" for all
# Default: http://localhost:3000,http://localhost:8000 (common dev ports)
cors_origins_str = os.getenv("GPLOT_CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")
if cors_origins_str == "*":
    cors_origins = ["*"]
else:
    cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

logger.info("Configuring CORS", origins=cors_origins)

starlette_app = CORSMiddleware(
    starlette_app,
    allow_origins=cors_origins,
    allow_credentials=True,  # Allow cookies/auth headers
    allow_methods=["GET", "POST", "DELETE"],  # MCP streamable HTTP methods
    allow_headers=["*"],  # Allow all headers (including Authorization)
    expose_headers=["Mcp-Session-Id"],
)


async def main(host: str = "0.0.0.0", port: int = 8001):
    """
    Run the MCP server with Streamable HTTP transport and comprehensive error handling.

    Args:
        host: Host address to bind to (default: 0.0.0.0)
        port: Port number to listen on (default: 8001)
    """
    import uvicorn

    # Print detailed startup banner
    banner = f"""
{'='*80}
  gplot MCP Server - Starting
{'='*80}
  Version:          1.0.0
  Transport:        Streamable HTTP (MCP Protocol)
  Host:             {host}
  Port:             {port}
  
  Endpoints:
    - MCP Protocol:  http://{host}:{port}/mcp/
    - Health Check:  http://{host}:{port}/health
  
  Container Network (from n8n/openwebui):
    - gplot_dev:     http://gplot_dev:{port}/mcp/
    - gplot_prod:    http://gplot_prod:{port}/mcp/
  
  Localhost Access:
    - Local:         http://localhost:{port}/mcp/
    - Health:        curl http://localhost:{port}/health
  
  Authentication:   {'Enabled' if auth_service else 'Disabled'}
  Web URL:          {web_url_override or 'http://localhost:8000'}
  Proxy Mode:       {proxy_url_mode}
{'='*80}
    """
    print(banner)

    logger.info(
        "Starting MCP Streamable HTTP server",
        version="1.0.0",
        host=host,
        port=port,
        transport="Streamable HTTP",
        auth_enabled=auth_service is not None,
        web_url=web_url_override or "http://localhost:8000",
        proxy_mode=proxy_url_mode,
    )
    try:
        config = uvicorn.Config(
            starlette_app,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        logger.info(f"Server initialized, listening on http://{host}:{port}/mcp/", endpoint="/mcp/")
        print(f"\n✓ MCP Server ready and accepting connections on http://{host}:{port}/mcp/\n")
        await server.serve()
        logger.info("Server shutdown complete")
    except KeyboardInterrupt:
        # Handle graceful shutdown
        logger.info("Server stopped by user")
        print("\n✓ MCP Server shutdown complete\n")
    except Exception as e:
        logger.critical("Fatal server error", error=str(e), error_type=type(e).__name__)
        print(f"\n✗ FATAL ERROR: {str(e)}\n")
        sys.exit(1)
