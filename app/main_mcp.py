import argparse
import sys
import asyncio
from app.settings import Settings
from app.auth import AuthService
from app.startup import resolve_auth_config
from app.logger import ConsoleLogger
import logging

logger = ConsoleLogger(name="main_mcp", level=logging.INFO)

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="gplot MCP Server - Graph rendering via Model Context Protocol"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host address to bind to (default: from env or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port number to listen on (default: from env or 8001)",
    )
    parser.add_argument(
        "--jwt-secret",
        type=str,
        default=None,
        help="JWT secret key (default: from GPLOT_JWT_SECRET env var)",
    )
    parser.add_argument(
        "--token-store",
        type=str,
        default=None,
        help="Path to token store file (default: {data_dir}/auth/tokens.json)",
    )
    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="Disable authentication (WARNING: insecure, for development only)",
    )
    parser.add_argument(
        "--web-url",
        type=str,
        default=None,
        help="Web server base URL for proxy mode downloads (default: from GPLOT_WEB_URL env or http://localhost:8000)",
    )
    parser.add_argument(
        "--proxy-url-mode",
        type=str,
        choices=["guid", "url"],
        default="url",
        help="Proxy mode response format: 'url' returns download URL, 'guid' returns only GUID (default: url)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level for all components (default: INFO)",
    )
    args = parser.parse_args()

    # Parse log level
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)

    # Create logger for startup messages
    startup_logger = ConsoleLogger(name="startup", level=log_level)

    try:
        # Resolve authentication configuration using centralized resolver
        jwt_secret, token_store_path, require_auth = resolve_auth_config(
            jwt_secret=args.jwt_secret,
            token_store_path=args.token_store,
            require_auth=not args.no_auth,
            allow_auto_secret=True,
        )

        # Build settings from environment and CLI args
        settings = Settings.from_env(require_auth=require_auth)

        # Override with CLI arguments if provided
        if args.host:
            settings.server.host = args.host
        if args.port:
            settings.server.mcp_port = args.port

        # Use resolved auth configuration
        if require_auth:
            settings.auth.jwt_secret = jwt_secret
            settings.auth.token_store_path = token_store_path
            settings.auth.require_auth = True

        # Resolve defaults and validate
        settings.resolve_defaults()
        settings.validate()

    except ValueError as e:
        startup_logger.error(
            "FATAL: Configuration error",
            error=str(e),
            help="Set GPLOT_JWT_SECRET environment variable or use --jwt-secret flag, or use --no-auth to disable authentication",
        )
        sys.exit(1)

    # Initialize auth service only if auth is required
    auth_service = None
    if require_auth:
        auth_service = AuthService(
            secret_key=jwt_secret,
            token_store_path=str(token_store_path),
        )
        startup_logger.info(
            "Authentication service initialized",
            jwt_enabled=True,
            token_store=str(auth_service.token_store_path),
            secret_fingerprint=auth_service.get_secret_fingerprint(),
        )
    else:
        startup_logger.info("Authentication disabled", jwt_enabled=False)

    # Import and configure mcp_server with auth service (dependency injection)
    from app.mcp_server import mcp_server as mcp_server_module

    mcp_server_module.set_auth_service(auth_service)
    mcp_server_module.set_logger_level(log_level)

    # Configure web URL and proxy mode
    if args.web_url:
        mcp_server_module.web_url_override = args.web_url
    mcp_server_module.proxy_url_mode = args.proxy_url_mode

    try:
        startup_logger.info(
            "Initializing MCP server",
            host=settings.server.host,
            port=settings.server.mcp_port,
            transport="Streamable HTTP",
            jwt_enabled=require_auth,
            web_url=mcp_server_module.web_url_override,
            proxy_url_mode=mcp_server_module.proxy_url_mode,
        )
        # Startup banner will be printed by mcp_server.main()
        asyncio.run(
            mcp_server_module.main(host=settings.server.host, port=settings.server.mcp_port)
        )
        startup_logger.info("MCP server shutdown complete")
    except KeyboardInterrupt:
        startup_logger.info("Shutdown complete")
        sys.exit(0)
    except Exception as e:
        startup_logger.error("Failed to start server", error=str(e), error_type=type(e).__name__)
        print(f"\n✗ FATAL ERROR: Failed to initialize MCP server: {str(e)}\n")
        sys.exit(1)
