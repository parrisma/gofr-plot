"""Response formatting utilities for MCP server.

Re-exports gofr_common.mcp utilities and provides image-specific helpers.
"""

from typing import Any, Dict, List, Optional, Union

from mcp.types import EmbeddedResource, ImageContent, TextContent

# Re-export everything from gofr_common.mcp
from gofr_common.mcp import (
    MCPResponseBuilder,
    error_response,
    format_validation_error,
    json_text,
    success_response,
)

# Type alias
ToolResponse = List[Union[TextContent, ImageContent, EmbeddedResource]]

# Initialize response builder for gofr-plot
_builder = MCPResponseBuilder()


def format_error(
    error_code: str,
    message: str,
    suggestions: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> ToolResponse:
    """Create error response in human-readable plain text format.

    Args:
        error_code: Error type/code (e.g., "Rate Limit Exceeded", "Validation")
        message: Human-readable error message
        suggestions: List of actionable suggestions
        context: Additional context dict

    Returns:
        Plain text error response
    """
    lines = [f"Error ({error_code}): {message}"]

    if context:
        lines.append("")
        lines.append("Context:")
        for key, value in context.items():
            lines.append(f"  {key}: {value}")

    if suggestions:
        lines.append("")
        lines.append("Suggestions:")
        for suggestion in suggestions:
            lines.append(f"• {suggestion}")

    return [TextContent(type="text", text="\n".join(lines))]


def format_success_image(
    image_data: str,
    mime_type: str,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> ToolResponse:
    """Format a successful image response with optional metadata.

    Args:
        image_data: Base64-encoded image data
        mime_type: MIME type (e.g., "image/png")
        message: Optional success message
        details: Optional metadata dict

    Returns:
        List containing ImageContent and optional JSON metadata
    """
    result: ToolResponse = [
        ImageContent(type="image", data=image_data, mimeType=mime_type)
    ]

    if message or details:
        metadata: Dict[str, Any] = {"status": "success"}
        if message:
            metadata["message"] = message
        if details:
            metadata["details"] = details
        result.append(json_text(metadata))

    return result


def format_list(title: str, items: Dict[str, str]) -> ToolResponse:
    """Format a list of items with descriptions as plain text.

    Args:
        title: Title for the list
        items: Dict mapping item names to descriptions

    Returns:
        List containing a single TextContent with formatted list
    """
    from mcp.types import TextContent

    lines = [f"{title}:\n"]
    for name, description in sorted(items.items()):
        lines.append(f"• {name}: {description}")
    return [TextContent(type="text", text="\n".join(lines))]


# Pre-built error responses
AUTH_REQUIRED_ERROR = format_error(
    error_code="Authentication Required",
    message="Authentication required but no token provided",
    suggestions=["Include a valid JWT token in the 'token' parameter"],
)


def AUTH_INVALID_ERROR(error_msg: str) -> ToolResponse:
    """Create auth invalid error response."""
    return format_error(
        error_code="Authentication Invalid",
        message=f"Token validation failed: {error_msg}",
        suggestions=[
            "Verify token hasn't expired and signature is valid",
            "Generate new token if needed",
        ],
    )


def PERMISSION_DENIED_ERROR(resource_id: str, group: str) -> ToolResponse:
    """Create permission denied error response."""
    return format_error(
        error_code="Permission Denied",
        message="Access denied to the requested resource",
        suggestions=[
            "Verify you are using the correct authentication token for this resource's group",
        ],
        context={"resource": resource_id, "your_group": group},
    )


__all__ = [
    # Re-exports from gofr_common
    "json_text",
    "success_response",
    "error_response",
    "format_validation_error",
    "MCPResponseBuilder",
    # Local helpers
    "format_error",
    "format_success_image",
    "format_list",
    "AUTH_REQUIRED_ERROR",
    "AUTH_INVALID_ERROR",
    "PERMISSION_DENIED_ERROR",
]
