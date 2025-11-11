import uvicorn
import argparse
import os
import sys
import asyncio
from app.auth import AuthService
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
        default="0.0.0.0",
        help="Host address to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port number to listen on (default: 8001)",
    )
    parser.add_argument(
        "--jwt-secret",
        type=str,
        default=None,
        help="JWT secret key (default: from GPLOT_JWT_SECRET env var or auto-generated)",
    )
    parser.add_argument(
        "--token-store",
        type=str,
        default=None,
        help="Path to token store file (default: configured in app.config)",
    )
    args = parser.parse_args()

    # Create logger for startup messages
    startup_logger = ConsoleLogger(name="startup", level=logging.INFO)

    # Initialize auth service
    jwt_secret = args.jwt_secret or os.environ.get("GPLOT_JWT_SECRET")
    auth_service = AuthService(secret_key=jwt_secret, token_store_path=args.token_store)
    startup_logger.info("Authentication service initialized", jwt_enabled=True)

    # Import and configure mcp_server with auth service
    import app.mcp_server as mcp_server_module

    mcp_server_module.auth_service = auth_service
    from app.mcp_server import main

    try:
        startup_logger.info(
            "Starting MCP server",
            host=args.host,
            port=args.port,
            transport="Streamable HTTP",
            jwt_enabled=True,
        )
        asyncio.run(main(host=args.host, port=args.port))
        startup_logger.info("MCP server shutdown complete")
    except KeyboardInterrupt:
        startup_logger.info("Shutdown complete")
        sys.exit(0)
    except Exception as e:
        startup_logger.error("Failed to start server", error=str(e), error_type=type(e).__name__)
        sys.exit(1)
