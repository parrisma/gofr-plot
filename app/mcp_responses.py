"""Response formatting utilities for MCP server

Provides consistent success and error message formatting across all MCP tools.
"""

from mcp.types import TextContent, ImageContent, EmbeddedResource
from typing import List


def format_error(
    error_type: str, message: str, suggestions: List[str] | None = None, context: dict | None = None
) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Format a consistent error response for MCP tools.

    Args:
        error_type: Category of error (e.g., "Authentication", "Validation", "Configuration")
        message: Clear description of what went wrong
        suggestions: Optional list of actionable next steps
        context: Optional dict of additional context (e.g., {"guid": "...", "group": "..."})

    Returns:
        List containing a single TextContent with formatted error message

    Example:
        >>> format_error(
        ...     "Authentication",
        ...     "Token signature verification failed",
        ...     ["Check that the JWT secret matches the server configuration",
        ...      "Verify the token hasn't been modified"],
        ...     {"group": "analytics"}
        ... )
    """
    lines = [f"Error ({error_type}): {message}"]

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


def format_success_text(
    message: str, details: dict | None = None
) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Format a consistent success response with optional details.

    Args:
        message: Success message
        details: Optional dict of additional information to include

    Returns:
        List containing a single TextContent with formatted success message
    """
    lines = [f"Success: {message}"]

    if details:
        lines.append("")
        for key, value in details.items():
            lines.append(f"{key}: {value}")

    return [TextContent(type="text", text="\n".join(lines))]


def format_success_image(
    image_data: str, mime_type: str, message: str | None = None, details: dict | None = None
) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Format a successful image response with optional accompanying text.

    Args:
        image_data: Base64-encoded image data
        mime_type: MIME type (e.g., "image/png")
        message: Optional success message
        details: Optional dict of details to include

    Returns:
        List containing ImageContent and optional TextContent
    """
    result: list[TextContent | ImageContent | EmbeddedResource] = [
        ImageContent(type="image", data=image_data, mimeType=mime_type)
    ]

    if message or details:
        text_lines = []
        if message:
            text_lines.append(f"Success: {message}")
        if details:
            if message:
                text_lines.append("")
            for key, value in details.items():
                text_lines.append(f"{key}: {value}")

        result.append(TextContent(type="text", text="\n".join(text_lines)))

    return result


def format_list(
    title: str, items: dict[str, str]
) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Format a list of items with descriptions.

    Args:
        title: Title for the list
        items: Dict mapping item names to descriptions

    Returns:
        List containing a single TextContent with formatted list

    Example:
        >>> format_list(
        ...     "Available Themes",
        ...     {"light": "Clean white background", "dark": "Dark background"}
        ... )
    """
    lines = [f"{title}:\n"]
    for name, description in sorted(items.items()):
        lines.append(f"• {name}: {description}")

    return [TextContent(type="text", text="\n".join(lines))]


# Common error messages for reuse
AUTH_REQUIRED_ERROR = format_error(
    "Authentication",
    "Authentication required but no token provided",
    [
        "Include a valid JWT token in the 'token' parameter",
        "Tokens can be created using the token_manager.py script",
        "Example: token='eyJ0eXAiOiJKV1QiLCJhbGc...'",
    ],
)


def AUTH_INVALID_ERROR(error_msg):
    return format_error(
        "Authentication",
        f"Token validation failed: {error_msg}",
        [
            "Verify the token hasn't expired",
            "Check that the token signature is valid",
            "Ensure the token store hasn't been cleared",
            "Generate a new token if needed",
        ],
    )


def PERMISSION_DENIED_ERROR(resource_id, group):
    return format_error(
        "Authorization",
        "Access denied to the requested resource",
        [
            "The resource belongs to a different security group",
            "Verify you are using the correct authentication token for this resource",
            "Contact your administrator if you need access to this group",
        ],
        {"resource": resource_id, "your_group": group},
    )


def format_parameter_error(
    parameter_name: str,
    provided_value: str | None,
    expected_type: str,
    additional_guidance: list[str] | None = None,
) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Format a consistent parameter validation error.

    Args:
        parameter_name: Name of the invalid parameter
        provided_value: The value that was provided (or None if missing)
        expected_type: Expected type/format description
        additional_guidance: Optional list of specific guidance for this parameter

    Returns:
        List containing a single TextContent with formatted parameter error

    Example:
        >>> format_parameter_error(
        ...     "guid",
        ...     "invalid-guid",
        ...     "valid UUID format with hyphens",
        ...     ["Example: '550e8400-e29b-41d4-a716-446655440000'"]
        ... )
    """
    if provided_value is None:
        message = f"Required parameter '{parameter_name}' was not provided"
        suggestions = [
            f"Action Required: Include the '{parameter_name}' parameter in your request",
            f"Expected Type: {expected_type}",
        ]
    else:
        message = f"Invalid value for parameter '{parameter_name}': {provided_value}"
        suggestions = [
            f"Provided: {provided_value}",
            f"Expected: {expected_type}",
            f"Action Required: Correct the '{parameter_name}' parameter and retry",
        ]

    if additional_guidance:
        suggestions.extend(additional_guidance)

    return format_error(
        "Parameter Validation",
        message,
        suggestions,
        {"parameter": parameter_name, "expected_type": expected_type},
    )
