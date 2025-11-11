import uvicorn
import argparse
import os
from app.web_server import GraphWebServer
from app.logger import ConsoleLogger
import logging
import sys

logger = ConsoleLogger(name="main", level=logging.INFO)

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="gplot Web Server - Graph rendering REST API")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host address to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port number to listen on (default: 8000)",
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

    # Initialize server with JWT configuration
    jwt_secret = args.jwt_secret or os.environ.get("GPLOT_JWT_SECRET")
    server = GraphWebServer(jwt_secret=jwt_secret, token_store_path=args.token_store)

    try:
        logger.info(
            "Starting web server",
            host=args.host,
            port=args.port,
            transport="HTTP REST API",
            jwt_enabled=True,
        )
        uvicorn.run(server.app, host=args.host, port=args.port)
        logger.info("Web server shutdown complete")
    except KeyboardInterrupt:
        logger.info("Web server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Failed to start web server", error=str(e), error_type=type(e).__name__)
        sys.exit(1)
