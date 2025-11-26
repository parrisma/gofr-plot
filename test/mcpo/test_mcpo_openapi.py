"""
MCPO OpenAPI integration tests.

MCPO is infrastructure that exposes MCP tools as REST/OpenAPI endpoints.
These tests verify MCPO correctly proxies requests to the MCP server.

Note: MCP protocol compliance is tested in test/mcp/ using the MCP Python client.
      These tests only verify the MCPO REST→MCP translation layer works.

Requirements:
    - MCPO server running: ./scripts/run_tests.sh --with-servers
    - MCPO translates REST POST to MCP tool calls
    - Returns plain JSON values (strings/lists), not MCP's structured format
"""

import pytest
import requests
from app.logger import ConsoleLogger
import logging

from conftest import MCPO_URL


def is_mcpo_available():
    """Check if MCPO server is running."""
    try:
        response = requests.get(f"{MCPO_URL}/openapi.json", timeout=1)
        return response.status_code == 200
    except:  # noqa: E722 - intentionally broad
        return False


# Skip all tests if MCPO is not available
pytestmark = pytest.mark.skipif(
    not is_mcpo_available(), reason="MCPO server not running (use --with-servers)"
)


@pytest.fixture
def logger():
    """Test logger instance."""
    return ConsoleLogger(name="mcpo_test", level=logging.INFO)


@pytest.fixture
def test_token():
    """Generate test JWT token."""
    from app.auth import AuthService
    import os

    secret = os.environ.get("GPLOT_JWT_SECRET", "test-secret-key")
    store = os.environ.get("GPLOT_TOKEN_STORE", "/tmp/gplot_test_tokens.json")

    svc = AuthService(secret_key=secret, token_store_path=store)
    token = svc.create_token(group="test_group", expires_in_seconds=3600)
    return token


class TestMCPOAvailability:
    """Test MCPO endpoints are available."""

    def test_mcpo_responds(self, logger):
        """MCPO server responds to requests."""
        logger.info("Testing MCPO availability")
        response = requests.get(f"{MCPO_URL}/openapi.json")
        assert response.status_code == 200
        logger.info("MCPO is available")

    def test_openapi_spec_valid(self, logger):
        """OpenAPI spec is valid JSON with correct structure."""
        logger.info("Validating OpenAPI spec")
        response = requests.get(f"{MCPO_URL}/openapi.json")
        spec = response.json()

        assert "openapi" in spec
        assert "info" in spec
        assert spec["info"]["title"] == "gplot"
        assert "paths" in spec
        logger.info("OpenAPI spec valid")

    def test_all_tools_exposed(self, logger):
        """All expected tools are exposed as endpoints."""
        logger.info("Checking tool endpoints")
        response = requests.get(f"{MCPO_URL}/openapi.json")
        spec = response.json()
        paths = spec["paths"]

        expected_tools = ["ping", "render_graph", "get_image", "list_themes", "list_handlers"]
        for tool in expected_tools:
            assert f"/{tool}" in paths, f"Tool {tool} not found"
            logger.info(f"Tool exposed: {tool}")


class TestMCPOToolInvocation:
    """Test tool invocation through MCPO REST API."""

    def test_ping_tool(self, logger):
        """ping tool returns server status."""
        logger.info("Testing ping tool")
        response = requests.post(
            f"{MCPO_URL}/ping", json={}, headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 200
        # MCPO returns plain string
        data = response.json()
        assert isinstance(data, str)
        assert "Server is running" in data or "gplot" in data.lower()
        logger.info("Ping successful")

    def test_list_themes_via_mcpo(self, logger):
        """list_themes returns theme list."""
        logger.info("Testing list_themes")
        response = requests.post(
            f"{MCPO_URL}/list_themes", json={}, headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, str)
        assert "light" in data.lower()
        assert "dark" in data.lower()
        logger.info("Themes listed successfully")

    def test_list_handlers_via_mcpo(self, logger):
        """list_handlers returns handler list."""
        logger.info("Testing list_handlers")
        response = requests.post(
            f"{MCPO_URL}/list_handlers", json={}, headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, str)
        assert "line" in data.lower()
        assert "bar" in data.lower()
        assert "scatter" in data.lower()
        logger.info("Handlers listed successfully")

    def test_render_graph_with_token(self, test_token, logger):
        """render_graph creates chart with auth."""
        logger.info("Testing render_graph")
        response = requests.post(
            f"{MCPO_URL}/render_graph",
            json={
                "token": test_token,
                "chart_type": "line",
                "title": "MCPO Test",
                "y1": [1, 2, 3, 4, 5],
            },
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()
        # Returns list: [base64_image, success_message]
        assert isinstance(data, list)
        assert len(data) == 2
        assert "data:image" in data[0]
        assert "success" in data[1].lower() or "rendered" in data[1].lower()
        logger.info("Chart rendered successfully")


class TestMCPOAuthentication:
    """Test authentication through MCPO."""

    def test_missing_token_validation(self, logger):
        """Missing token is rejected."""
        logger.info("Testing missing token")
        response = requests.post(
            f"{MCPO_URL}/render_graph",
            json={"title": "Test", "y1": [1, 2, 3]},
            headers={"Content-Type": "application/json"},
        )

        # Should fail validation
        assert response.status_code in [400, 422, 500]
        logger.info("Missing token correctly rejected")

    def test_invalid_token_error(self, logger):
        """Invalid token is rejected."""
        logger.info("Testing invalid token")
        response = requests.post(
            f"{MCPO_URL}/render_graph",
            json={"token": "invalid.token.here", "title": "Test", "y1": [1, 2, 3]},
            headers={"Content-Type": "application/json"},
        )

        # MCPO may return error as 200 with error message or as error status
        assert response.status_code != 200 or "error" in response.text.lower()
        logger.info("Invalid token correctly rejected")

    def test_valid_token_accepted(self, test_token, logger):
        """Valid token allows rendering."""
        logger.info("Testing valid token")
        response = requests.post(
            f"{MCPO_URL}/render_graph",
            json={"token": test_token, "title": "Auth Test", "y1": [1, 2, 3]},
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        logger.info("Valid token accepted")


class TestMCPOProxyMode:
    """Test proxy mode through MCPO."""

    def test_proxy_mode_returns_guid(self, test_token, logger):
        """Proxy mode returns GUID."""
        logger.info("Testing proxy mode")
        response = requests.post(
            f"{MCPO_URL}/render_graph",
            json={"token": test_token, "title": "Proxy Test", "y1": [10, 20, 30], "proxy": True},
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()
        # Proxy mode returns GUID string
        assert isinstance(data, str) or (isinstance(data, list) and len(data) > 0)

        # Extract GUID from response
        guid = data if isinstance(data, str) else data[0] if isinstance(data, list) else None
        assert guid
        assert len(guid) > 10  # GUIDs are longer
        logger.info(f"Proxy GUID received: {guid[:20]}...")

    def test_get_image_via_mcpo(self, test_token, logger):
        """get_image retrieves stored image."""
        logger.info("Testing get_image")

        # First create an image in proxy mode
        response1 = requests.post(
            f"{MCPO_URL}/render_graph",
            json={"token": test_token, "title": "Storage Test", "y1": [5, 10, 15], "proxy": True},
            headers={"Content-Type": "application/json"},
        )

        assert response1.status_code == 200
        data1 = response1.json()

        # Extract GUID from response (format varies)
        if isinstance(data1, str):
            guid = data1
        elif isinstance(data1, list) and len(data1) > 0:
            guid = data1[0] if "guid" in str(data1[0]).lower() else data1[0]
        else:
            pytest.skip("Proxy mode returned unexpected format")
            return

        # Now retrieve it
        response2 = requests.post(
            f"{MCPO_URL}/get_image",
            json={"token": test_token, "identifier": guid},
            headers={"Content-Type": "application/json"},
        )

        assert response2.status_code == 200
        data2 = response2.json()
        # Verify we got image data back
        assert isinstance(data2, (str, list)), "Expected string or list response"
        assert len(str(data2)) > 100, "Response seems too short for an image"
        logger.info("Image retrieved successfully")


class TestMCPOMultiDataset:
    """Test multi-dataset rendering through MCPO."""

    def test_multi_dataset_rendering(self, test_token, logger):
        """Multiple datasets render correctly."""
        logger.info("Testing multi-dataset rendering")
        response = requests.post(
            f"{MCPO_URL}/render_graph",
            json={
                "token": test_token,
                "title": "Multi-Dataset Test",
                "y1": [1, 2, 3],
                "y2": [4, 5, 6],
                "y3": [7, 8, 9],
                "label1": "Series 1",
                "label2": "Series 2",
                "label3": "Series 3",
            },
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        logger.info("Multi-dataset chart rendered")


class TestMCPOErrorHandling:
    """Test error handling through MCPO."""

    def test_validation_error_format(self, test_token, logger):
        """Validation errors are returned properly."""
        logger.info("Testing validation errors")
        response = requests.post(
            f"{MCPO_URL}/render_graph",
            json={
                "token": test_token,
                "title": "Bad Data",
                "y1": [1, 2, 3],
                "x": [1, 2],  # Mismatched length
            },
            headers={"Content-Type": "application/json"},
        )

        # MCPO may return different status codes for MCP errors
        # Just verify it doesn't return 200 for invalid data
        assert response.status_code != 200 or "error" in response.text.lower()
        logger.info("Validation error handled")

    def test_invalid_handler_error(self, test_token, logger):
        """Invalid handler type is rejected."""
        logger.info("Testing invalid handler")
        response = requests.post(
            f"{MCPO_URL}/render_graph",
            json={
                "token": test_token,
                "type": "invalid_type",  # Corrected from "chart_type" to "type"
                "title": "Bad Handler",
                "y1": [1, 2, 3],
            },
            headers={"Content-Type": "application/json"},
        )

        # Verify error is returned (may be 200 with error message or error status)
        assert response.status_code != 200 or "error" in response.text.lower()
        logger.info("Invalid handler rejected")
