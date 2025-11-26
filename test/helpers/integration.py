"""Integration test helpers

Utilities for testing MCP and Web servers, making requests, and validating responses.
"""

import requests
from typing import Any, Dict, Optional
from contextlib import contextmanager


class ServerHelper:
    """Base class for server test helpers"""

    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.session = requests.Session()
        if auth_token:
            self.session.headers.update({"Authorization": f"Bearer {auth_token}"})

    def _make_headers(self, extra_headers: Optional[Dict] = None) -> Dict[str, str]:
        """Build request headers"""
        headers = {"Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        return headers


class MCPServerHelper(ServerHelper):
    """Helper for testing MCP server endpoints

    Example:
        import os
        mcp_port = os.environ.get('GPLOT_MCP_PORT', '8010')
        mcp = MCPServerHelper(f"http://localhost:{mcp_port}", auth_token="...")
        response = mcp.create_chart("line", [1, 2, 3])
        assert response["success"]
    """

    def __init__(self, base_url: Optional[str] = None, auth_token: Optional[str] = None):
        if base_url is None:
            import os

            mcp_port = os.environ.get("GPLOT_MCP_PORT", "8010")
            base_url = f"http://localhost:{mcp_port}"
        super().__init__(base_url, auth_token)

    def create_chart(
        self, chart_type: str, data: Any, format: str = "png", **kwargs
    ) -> Dict[str, Any]:
        """Create a chart via MCP protocol

        Args:
            chart_type: Type of chart (line, scatter, bar)
            data: Chart data
            format: Output format (png, jpg, svg, pdf)
            **kwargs: Additional chart parameters

        Returns:
            Response dictionary
        """
        payload = {"type": chart_type, "data": data, "format": format, **kwargs}
        return self.call_tool("create_chart", payload)

    def get_chart(self, guid: str) -> Dict[str, Any]:
        """Retrieve a chart by GUID

        Args:
            guid: Chart GUID

        Returns:
            Response dictionary with chart data
        """
        return self.call_tool("get_chart", {"guid": guid})

    def list_charts(self, group: Optional[str] = None) -> Dict[str, Any]:
        """List charts, optionally filtered by group

        Args:
            group: Optional group filter

        Returns:
            Response dictionary with chart list
        """
        params = {"group": group} if group else {}
        return self.call_tool("list_charts", params)

    def delete_chart(self, guid: str) -> Dict[str, Any]:
        """Delete a chart by GUID

        Args:
            guid: Chart GUID

        Returns:
            Response dictionary
        """
        return self.call_tool("delete_chart", {"guid": guid})

    def ping(self) -> Dict[str, Any]:
        """Ping the server

        Returns:
            Response dictionary
        """
        return self.call_tool("ping", {})

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Response dictionary
        """
        url = f"{self.base_url}/call_tool"
        payload = {"name": tool_name, "arguments": arguments}
        response = self.session.post(url, json=payload, headers=self._make_headers())
        response.raise_for_status()
        return response.json()


class WebServerHelper(ServerHelper):
    """Helper for testing Web server endpoints

    Example:
        import os
        web_port = os.environ.get('GPLOT_WEB_PORT', '8012')
        web = WebServerHelper(f"http://localhost:{web_port}", auth_token="...")
        response = web.render_chart("line", [1, 2, 3])
        assert response.status_code == 200
    """

    def __init__(self, base_url: Optional[str] = None, auth_token: Optional[str] = None):
        if base_url is None:
            import os

            web_port = os.environ.get("GPLOT_WEB_PORT", "8012")
            base_url = f"http://localhost:{web_port}"
        super().__init__(base_url, auth_token)

    def render_chart(
        self, chart_type: str, data: Any, format: str = "png", **kwargs
    ) -> requests.Response:
        """Render a chart via Web API

        Args:
            chart_type: Type of chart (line, scatter, bar)
            data: Chart data
            format: Output format (png, jpg, svg, pdf)
            **kwargs: Additional chart parameters

        Returns:
            Response object
        """
        url = f"{self.base_url}/render"
        payload = {"type": chart_type, "data": data, "format": format, **kwargs}
        return self.session.post(url, json=payload, headers=self._make_headers())

    def get_chart(self, guid: str) -> requests.Response:
        """Retrieve a chart by GUID

        Args:
            guid: Chart GUID

        Returns:
            Response object with image data
        """
        url = f"{self.base_url}/proxy/{guid}"
        return self.session.get(url)

    def list_charts(self, group: Optional[str] = None) -> requests.Response:
        """List charts, optionally filtered by group

        Args:
            group: Optional group filter

        Returns:
            Response object with JSON list
        """
        url = f"{self.base_url}/list"
        params = {"group": group} if group else {}
        return self.session.get(url, params=params)

    def delete_chart(self, guid: str) -> requests.Response:
        """Delete a chart by GUID

        Args:
            guid: Chart GUID

        Returns:
            Response object
        """
        url = f"{self.base_url}/delete/{guid}"
        return self.session.delete(url)

    def ping(self) -> requests.Response:
        """Ping the server

        Returns:
            Response object
        """
        url = f"{self.base_url}/ping"
        return self.session.post(url, json={})


def make_mcp_request(
    tool_name: str,
    arguments: Dict[str, Any],
    base_url: Optional[str] = None,
    auth_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Make a single MCP request

    Args:
        tool_name: MCP tool name
        arguments: Tool arguments
        base_url: Server base URL
        auth_token: Optional auth token

    Returns:
        Response dictionary
    """
    if base_url is None:
        import os

        mcp_port = os.environ.get("GPLOT_MCP_PORT", "8010")
        base_url = f"http://localhost:{mcp_port}"
    helper = MCPServerHelper(base_url, auth_token)
    return helper.call_tool(tool_name, arguments)


def make_web_request(
    endpoint: str,
    method: str = "POST",
    data: Optional[Dict] = None,
    base_url: Optional[str] = None,
    auth_token: Optional[str] = None,
) -> requests.Response:
    """Make a single Web API request

    Args:
        endpoint: API endpoint (e.g., "/render", "/ping")
        method: HTTP method (GET, POST, DELETE)
        data: Request payload
        base_url: Server base URL
        auth_token: Optional auth token

    Returns:
        Response object
    """
    if base_url is None:
        import os

        web_port = os.environ.get("GPLOT_WEB_PORT", "8012")
        base_url = f"http://localhost:{web_port}"
    helper = WebServerHelper(base_url, auth_token)
    url = f"{base_url}{endpoint}"

    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    if method.upper() == "GET":
        return helper.session.get(url, headers=headers)
    elif method.upper() == "POST":
        return helper.session.post(url, json=data, headers=headers)
    elif method.upper() == "DELETE":
        return helper.session.delete(url, headers=headers)
    else:
        raise ValueError(f"Unsupported method: {method}")


@contextmanager
def temporary_auth(helper: ServerHelper, token: str):
    """Context manager for temporary authentication

    Example:
        with temporary_auth(mcp_helper, "temp_token"):
            response = mcp_helper.ping()
    """
    original_token = helper.auth_token
    original_header = helper.session.headers.get("Authorization")

    try:
        helper.auth_token = token
        helper.session.headers["Authorization"] = f"Bearer {token}"
        yield helper
    finally:
        helper.auth_token = original_token
        if original_header:
            helper.session.headers["Authorization"] = original_header
        else:
            helper.session.headers.pop("Authorization", None)


def validate_mcp_response(response: Dict[str, Any], expect_success: bool = True) -> None:
    """Validate MCP response structure

    Args:
        response: MCP response dictionary
        expect_success: Whether to expect success=True

    Raises:
        AssertionError: If response structure is invalid
    """
    assert "success" in response, "Response missing 'success' field"
    assert isinstance(response["success"], bool), "'success' must be boolean"

    if expect_success:
        assert response["success"] is True, f"Expected success, got: {response}"
        if "error" in response:
            assert response["error"] is None, f"Unexpected error: {response['error']}"
    else:
        assert response["success"] is False, "Expected failure, got success"
        assert "error" in response, "Failed response missing 'error' field"


def validate_web_response(
    response: requests.Response,
    expected_status: int = 200,
    expected_content_type: Optional[str] = None,
) -> None:
    """Validate Web API response

    Args:
        response: Response object
        expected_status: Expected HTTP status code
        expected_content_type: Expected Content-Type header

    Raises:
        AssertionError: If response is invalid
    """
    assert (
        response.status_code == expected_status
    ), f"Expected status {expected_status}, got {response.status_code}: {response.text}"

    if expected_content_type:
        content_type = response.headers.get("Content-Type", "")
        assert (
            expected_content_type in content_type
        ), f"Expected content type {expected_content_type}, got {content_type}"
