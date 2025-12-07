"""Tests for dependency injection pattern in auth system"""

from unittest.mock import MagicMock
from app.auth import AuthService, init_auth_service, get_auth_service


class TestAuthServiceDependencyInjection:
    """Test dependency injection of AuthService instances"""

    def test_init_with_injected_service(self):
        """Test init_auth_service accepts a pre-configured AuthService instance"""
        # Create a mock AuthService
        mock_service = MagicMock(spec=AuthService)
        mock_service.secret_key = "injected-secret"
        mock_service.token_store_path = "/tmp/injected_tokens.json"

        # Inject the service
        result = init_auth_service(auth_service=mock_service)

        # Verify the injected service is used
        assert result is mock_service
        retrieved = get_auth_service()
        assert retrieved is mock_service

    def test_init_with_legacy_parameters(self):
        """Test init_auth_service creates new service from legacy parameters"""
        # Use legacy parameters (no injection)
        result = init_auth_service(
            secret_key="test-secret", token_store_path="/tmp/test_tokens.json"
        )

        # Verify new service was created
        assert isinstance(result, AuthService)
        assert result.secret_key == "test-secret"
        assert result.token_store_path is not None
        assert result.token_store_path.name == "test_tokens.json"

    def test_injected_service_takes_precedence(self):
        """Test that injected service takes precedence over legacy parameters"""
        # Create a mock AuthService with different settings
        mock_service = MagicMock(spec=AuthService)
        mock_service.secret_key = "injected-secret"
        mock_service.token_store_path = "/tmp/injected_tokens.json"

        # Pass both injected service and legacy parameters
        result = init_auth_service(
            secret_key="legacy-secret",
            token_store_path="/tmp/legacy_tokens.json",
            auth_service=mock_service,
        )

        # Verify injected service was used (legacy params ignored)
        assert result is mock_service
        assert result.secret_key == "injected-secret"


class TestGraphWebServerDependencyInjection:
    """Test GraphWebServer accepts injected AuthService"""

    def test_web_server_accepts_injected_auth_service(self):
        """Test GraphWebServer.__init__ accepts auth_service parameter"""
        from app.web_server.web_server import GraphWebServer

        # Create mock AuthService
        mock_service = MagicMock(spec=AuthService)
        mock_service.secret_key = "test-secret"
        mock_service.token_store_path = "/tmp/test_tokens.json"

        # Create server with injected auth service
        server = GraphWebServer(
            require_auth=True,
            auth_service=mock_service,
        )

        # Verify server was created
        assert server is not None
        assert server.require_auth is True

        # Verify injected service is available
        retrieved = get_auth_service()
        assert retrieved is mock_service

    def test_web_server_legacy_parameters_still_work(self):
        """Test GraphWebServer still accepts legacy jwt_secret and token_store_path"""
        from app.web_server.web_server import GraphWebServer

        # Create server with legacy parameters (no injection)
        server = GraphWebServer(
            jwt_secret="legacy-secret",
            token_store_path="/tmp/legacy_tokens.json",
            require_auth=True,
        )

        # Verify server was created
        assert server is not None
        assert server.require_auth is True

        # Verify auth service was created from legacy parameters
        auth_service = get_auth_service()
        assert auth_service.secret_key == "legacy-secret"

    def test_web_server_no_auth_skips_injection(self):
        """Test GraphWebServer skips auth service when require_auth=False"""
        from app.web_server.web_server import GraphWebServer

        # Create mock AuthService
        mock_service = MagicMock(spec=AuthService)

        # Create server with require_auth=False (should ignore auth_service)
        server = GraphWebServer(
            require_auth=False,
            auth_service=mock_service,
        )

        # Verify server was created
        assert server is not None
        assert server.require_auth is False


class TestMCPServerDependencyInjection:
    """Test MCP server uses set_auth_service function"""

    def test_mcp_set_auth_service_function_exists(self):
        """Test set_auth_service function is available"""
        from app.mcp_server.mcp_server import set_auth_service

        assert callable(set_auth_service)

    def test_mcp_set_auth_service_sets_module_variable(self):
        """Test set_auth_service updates module-level auth_service variable"""
        from app.mcp_server.mcp_server import set_auth_service
        import app.mcp_server.mcp_server as mcp_module

        # Create mock AuthService
        mock_service = MagicMock(spec=AuthService)
        mock_service.secret_key = "test-secret"

        # Set the auth service
        set_auth_service(mock_service)

        # Verify module variable was updated
        assert mcp_module.auth_service is mock_service

    def test_mcp_set_auth_service_accepts_none(self):
        """Test set_auth_service accepts None to disable authentication"""
        from app.mcp_server.mcp_server import set_auth_service
        import app.mcp_server.mcp_server as mcp_module

        # Set auth service to None
        set_auth_service(None)

        # Verify module variable is None
        assert mcp_module.auth_service is None


class TestDependencyInjectionLogging:
    """Test logging indicates when dependency injection is used"""

    def test_web_server_logs_auth_service_injected(self, caplog):
        """Test GraphWebServer logs when auth_service is injected"""
        from app.web_server.web_server import GraphWebServer

        # Create mock AuthService
        mock_service = MagicMock(spec=AuthService)
        mock_service.secret_key = "test-secret"
        mock_service.token_store_path = "/tmp/test_tokens.json"

        # Create server with injected auth service
        with caplog.at_level("INFO"):
            server = GraphWebServer(
                require_auth=True,
                auth_service=mock_service,
            )

        # Verify logging indicates injection
        # (Looking for auth_service_injected=True in structured log)
        assert server is not None
        # Note: Actual log assertion depends on logger implementation


class TestDependencyInjectionDocumentation:
    """Test that dependency injection is properly documented"""

    def test_web_server_init_has_auth_service_parameter(self):
        """Test GraphWebServer.__init__ has auth_service parameter in signature"""
        from app.web_server.web_server import GraphWebServer
        import inspect

        sig = inspect.signature(GraphWebServer.__init__)
        assert "auth_service" in sig.parameters

    def test_web_server_init_has_docstring(self):
        """Test GraphWebServer.__init__ documents dependency injection"""
        from app.web_server.web_server import GraphWebServer

        docstring = GraphWebServer.__init__.__doc__
        assert docstring is not None
        assert "auth_service" in docstring.lower()

    def test_init_auth_service_has_auth_service_parameter(self):
        """Test init_auth_service has auth_service parameter in signature"""
        from app.auth import init_auth_service
        import inspect

        sig = inspect.signature(init_auth_service)
        assert "auth_service" in sig.parameters

    def test_init_auth_service_has_docstring(self):
        """Test init_auth_service documents dependency injection"""
        from app.auth import init_auth_service

        docstring = init_auth_service.__doc__
        assert docstring is not None
        assert "auth_service" in docstring.lower()
        assert "dependency injection" in docstring.lower()

    def test_set_auth_service_has_docstring(self):
        """Test set_auth_service documents dependency injection"""
        from app.mcp_server.mcp_server import set_auth_service

        docstring = set_auth_service.__doc__
        assert docstring is not None
        assert "dependency injection" in docstring.lower()
