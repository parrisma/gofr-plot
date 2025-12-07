import uvicorn
import argparse
import sys
from app.settings import Settings
from app.web_server.web_server import GraphWebServer
from app.auth import AuthService
from app.startup import resolve_auth_config
from app.logger import ConsoleLogger
import logging

logger = ConsoleLogger(name="main_web", level=logging.INFO)

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="gofr-plot Web Server - Graph rendering REST API")
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
        help="Port number to listen on (default: from env or 8000)",
    )
    parser.add_argument(
        "--jwt-secret",
        type=str,
        default=None,
        help="JWT secret key (default: from GOFR_PLOT_JWT_SECRET env var)",
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
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level for all components (default: INFO)",
    )
    args = parser.parse_args()

    # Parse log level
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)

    try:
        # Resolve authentication configuration using centralized resolver
        jwt_secret, token_store_path, require_auth = resolve_auth_config(
            jwt_secret=args.jwt_secret,
            token_store_path=args.token_store,
            require_auth=not args.no_auth,
            allow_auto_secret=True,
        )

        # Build settings from environment and CLI args
        # Use require_auth=False initially to avoid validation failure before we apply CLI args
        settings = Settings.from_env(require_auth=False)

        # Override with CLI arguments if provided
        if args.host:
            settings.server.host = args.host
        if args.port:
            settings.server.web_port = args.port

        # Use resolved auth configuration
        if require_auth:
            settings.auth.jwt_secret = jwt_secret
            settings.auth.token_store_path = token_store_path
            settings.auth.require_auth = True

        # Resolve defaults and validate
        settings.resolve_defaults()
        settings.validate()

    except ValueError as e:
        logger.error(
            "FATAL: Configuration error",
            error=str(e),
            help="Set GOFR_PLOT_JWT_SECRET environment variable or use --jwt-secret flag, or use --no-auth to disable authentication",
        )
        sys.exit(1)

    # Create AuthService instance if authentication is enabled (dependency injection)
    auth_service_instance = None
    if require_auth:
        auth_service_instance = AuthService(
            secret_key=jwt_secret,
            token_store_path=str(token_store_path),
        )
        logger.info(
            "Authentication service created",
            token_store=str(auth_service_instance.token_store_path),
            secret_fingerprint=auth_service_instance.get_secret_fingerprint(),
        )

    # Initialize server with dependency injection
    server = GraphWebServer(
        jwt_secret=settings.auth.jwt_secret,  # Legacy parameter (ignored if auth_service provided)
        token_store_path=str(
            settings.auth.token_store_path
        ),  # Legacy parameter (ignored if auth_service provided)
        require_auth=require_auth,
        auth_service=auth_service_instance,  # Dependency injection
        log_level=log_level,  # Pass log level to server
    )

    try:
        # Print detailed startup banner
        banner = f"""
{'='*80}
  gofr-plot Web Server - Starting
{'='*80}
  Version:          1.0.0
  Transport:        HTTP REST API
  Host:             {settings.server.host}
  Port:             {settings.server.web_port}
  
  Endpoints:
    - API Docs:      http://{settings.server.host}:{settings.server.web_port}/docs
    - Health Check:  http://{settings.server.host}:{settings.server.web_port}/ping
    - Render:        http://{settings.server.host}:{settings.server.web_port}/render
    - Proxy:         http://{settings.server.host}:{settings.server.web_port}/proxy/{{guid}}
  
  Container Network (from n8n/openwebui):
    - gofr-plot_dev:     http://gofr-plot_dev:{settings.server.web_port}
    - gofr-plot_prod:    http://gofr-plot_prod:{settings.server.web_port}
  
  Localhost Access:
    - API Docs:      http://localhost:{settings.server.web_port}/docs
    - Render:        curl -X POST http://localhost:{settings.server.web_port}/render
    - Health:        curl http://localhost:{settings.server.web_port}/ping
  
  Authentication:   {'Enabled' if require_auth else 'Disabled'}
  Token Store:      {settings.auth.token_store_path if require_auth else 'N/A'}
  Storage Dir:      {settings.storage.storage_dir}
{'='*80}
        """
        print(banner)

        logger.info(
            "Starting web server",
            host=settings.server.host,
            port=settings.server.web_port,
            transport="HTTP REST API",
            jwt_enabled=require_auth,
            storage_dir=str(settings.storage.storage_dir),
            token_store=str(settings.auth.token_store_path) if require_auth else None,
        )
        print(
            f"\n✓ Web Server ready and accepting connections on http://{settings.server.host}:{settings.server.web_port}\n"
        )
        uvicorn.run(server.app, host=settings.server.host, port=settings.server.web_port)
        logger.info("Web server shutdown complete")
        print("\n✓ Web Server shutdown complete\n")
    except KeyboardInterrupt:
        logger.info("Web server stopped by user")
        print("\n✓ Web Server stopped by user\n")
        sys.exit(0)
    except Exception as e:
        logger.error("Failed to start web server", error=str(e), error_type=type(e).__name__)
        print(f"\n✗ FATAL ERROR: Failed to start Web server: {str(e)}\n")
        sys.exit(1)
