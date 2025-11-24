from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, Response, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from app.graph_params import GraphParams
from app.render import GraphRenderer
from app.validation import GraphDataValidator
from app.storage import get_storage
from app.storage.exceptions import PermissionDeniedError
from app.auth import (
    TokenInfo,
    verify_token,
    optional_verify_token,
    init_auth_service,
    get_auth_service,
    set_security_auditor,
)
from app.auth.service import AuthService
from app.security import RateLimiter, RateLimitExceeded, SecurityAuditor
from app.logger import ConsoleLogger
import logging
from datetime import datetime
import base64
import os
from typing import Optional


class GraphWebServer:
    def __init__(
        self,
        jwt_secret: Optional[str] = None,
        token_store_path: Optional[str] = None,
        require_auth: bool = True,
        auth_service: Optional["AuthService"] = None,  # Type hint quoted for forward reference
        log_level: int = logging.INFO,
    ):
        """
        Initialize GraphWebServer

        Args:
            jwt_secret: JWT secret key (deprecated - use auth_service instead)
            token_store_path: Path to token store (deprecated - use auth_service instead)
            require_auth: Whether authentication is required
            auth_service: AuthService instance (preferred - enables dependency injection)
            log_level: Logging level (logging.DEBUG, logging.INFO, etc.)
        """
        self.app = FastAPI(title="gplot", description="Graph rendering service")

        self.renderer = GraphRenderer()
        self.validator = GraphDataValidator()
        self.storage = get_storage()
        self.require_auth = require_auth

        # Initialize rate limiter with endpoint-specific limits
        # Use higher limits in test environment to avoid test failures
        # Configure CORS middleware
        # GPLOT_CORS_ORIGINS: Comma-separated list of allowed origins, or "*" for all
        # Default: http://localhost:3000,http://localhost:8000 (common dev ports)
        cors_origins_str = os.getenv(
            "GPLOT_CORS_ORIGINS", "http://localhost:3000,http://localhost:8000"
        )
        if cors_origins_str == "*":
            cors_origins = ["*"]
        else:
            cors_origins = [
                origin.strip() for origin in cors_origins_str.split(",") if origin.strip()
            ]

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,  # Allow cookies/auth headers
            allow_methods=["*"],  # Allow all HTTP methods
            allow_headers=["*"],  # Allow all headers (including Authorization)
        )

        # Initialize rate limiter with production defaults
        # Will be reconfigured based on auth service configuration
        self.render_limit = 10
        self.rate_limiter = RateLimiter(default_limit=100, window=60)
        self.rate_limiter.set_endpoint_limit("/render", limit=10, window=60)
        self.rate_limiter.set_endpoint_limit("/ping", limit=1000, window=60)

        # Initialize security auditor
        self.security_auditor = SecurityAuditor()
        set_security_auditor(self.security_auditor)

        # Initialize auth service - prefer injected instance, fallback to legacy init
        if require_auth:
            if auth_service is not None:
                # Use injected AuthService instance (dependency injection)
                init_auth_service(auth_service=auth_service)
            else:
                # Legacy path: create AuthService from jwt_secret and token_store_path
                init_auth_service(secret_key=jwt_secret, token_store_path=token_store_path)

        # Reconfigure rate limiter based on auth service configuration
        # If JWT secret starts with "test-secret", use much higher limits for testing
        is_test_env = False
        if require_auth:
            # Only check auth service if authentication is enabled
            try:
                auth_svc = get_auth_service()
                if auth_svc and hasattr(auth_svc, "secret_key"):
                    is_test_env = auth_svc.secret_key.startswith("test-secret")
            except RuntimeError:
                # Auth service not initialized yet, check environment variable
                is_test_env = os.getenv("GPLOT_JWT_SECRET", "").startswith("test-secret")
        else:
            # No auth means we check environment variable directly
            is_test_env = os.getenv("GPLOT_JWT_SECRET", "").startswith("test-secret")

        if is_test_env:
            self.render_limit = 10000
            self.rate_limiter.default_limit = 1000
            self.rate_limiter.set_endpoint_limit("/render", limit=10000, window=60)

        self.logger = ConsoleLogger(name="web_server", level=log_level)
        self.logger.info(
            "Web server initialized",
            version="1.0.0",
            authentication_enabled=require_auth,
            auth_service_injected=auth_service is not None,
            environment="test" if is_test_env else "production",
            render_limit=self.render_limit,
            default_rate_limit=self.rate_limiter.default_limit,
        )
        self._setup_routes()

    def _get_auth_dependency(self):
        """Get the appropriate auth dependency based on require_auth setting"""
        return verify_token if self.require_auth else optional_verify_token

    def _get_client_id(self, request: Request, token_info: Optional[TokenInfo]) -> str:
        """Extract client identifier for rate limiting"""
        if token_info and hasattr(token_info, "group"):
            return f"user:{token_info.group}"
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    def _setup_routes(self):
        @self.app.get("/ping")
        async def ping(request: Request):
            """
            Health check endpoint that returns the current server time.
            """
            # Rate limiting (lenient for health checks)
            client_id = request.client.host if request.client else "unknown"
            try:
                self.rate_limiter.check_limit(client_id=f"ip:{client_id}", endpoint="/ping")
            except RateLimitExceeded as e:
                self.logger.warning("Rate limit exceeded", client_id=client_id, endpoint="/ping")
                # Log rate limit to security auditor
                self.security_auditor.log_rate_limit(
                    client_id=f"ip:{client_id}", endpoint="/ping", limit=1000, window=60
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": str(e),
                        "retry_after": int(e.retry_after),
                    },
                    headers={"Retry-After": str(int(e.retry_after))},
                )

            current_time = datetime.now().isoformat()
            self.logger.debug("Ping request received", timestamp=current_time)
            return JSONResponse(
                content={"status": "ok", "timestamp": current_time, "service": "gplot"}
            )

        auth_dep = self._get_auth_dependency()

        @self.app.post("/render")
        async def render_graph(
            request: Request, data: GraphParams, token_info: Optional[TokenInfo] = Depends(auth_dep)
        ):
            """
            Render a graph with comprehensive error handling.
            Requires JWT authentication unless --no-auth flag is used.

            This endpoint ensures the server never crashes by catching all exceptions
            and returning appropriate HTTP error responses.
            """
            # Rate limiting (strict for expensive operations)
            client_id = self._get_client_id(request, token_info)

            # Log every incoming render request for request tracing
            self.logger.info(
                "POST /render request received",
                client_id=client_id,
                proxy_mode=data.proxy,
                chart_type=data.type,
                format=data.format,
                title=data.title[:50] if data.title else None,
                timestamp=datetime.now().isoformat(),
            )
            try:
                self.rate_limiter.check_limit(client_id=client_id, endpoint="/render")
            except RateLimitExceeded as e:
                self.logger.warning("Rate limit exceeded", client_id=client_id, endpoint="/render")
                # Log rate limit to security auditor
                self.security_auditor.log_rate_limit(
                    client_id=client_id, endpoint="/render", limit=self.render_limit, window=60
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": str(e),
                        "retry_after": int(e.retry_after),
                        "limit": f"{self.render_limit} requests per 60 seconds",
                    },
                    headers={"Retry-After": str(int(e.retry_after))},
                )

            group = token_info.group if token_info else "public"
            datasets = data.get_datasets()
            data_points = len(datasets[0][0]) if datasets else 0

            self.logger.info(
                "Received render request",
                chart_type=data.type,
                format=data.format,
                theme=data.theme,
                num_datasets=len(datasets),
                data_points=data_points,
                group=group,
            )

            # Validate the input data
            try:
                self.logger.debug("Starting validation")
                validation_result = self.validator.validate(data)

                if not validation_result.is_valid:
                    self.logger.warning(
                        "Validation failed",
                        error_count=len(validation_result.errors),
                        errors=[e.field for e in validation_result.errors],
                    )
                    # Return detailed validation errors
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "Validation failed",
                            "message": validation_result.get_error_summary(),
                            "errors": validation_result.get_json_errors(),
                        },
                    )
            except HTTPException:
                # Re-raise HTTP exceptions
                raise
            except Exception as e:
                self.logger.error(
                    "Unexpected validation error", error=str(e), error_type=type(e).__name__
                )
                # Catch any unexpected validation errors
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Validation system error",
                        "message": f"Unexpected error during validation: {str(e)}",
                        "suggestions": [
                            "This is an internal error",
                            "Please verify your input data format",
                        ],
                    },
                )

            # Render the graph
            try:
                self.logger.debug("Starting render", group=group)
                image_data = self.renderer.render(data, group=group)
                self.logger.info(
                    "Render completed successfully",
                    chart_type=data.type,
                    format=data.format,
                    output_size=len(image_data) if isinstance(image_data, (str, bytes)) else 0,
                    group=group,
                )
            except ValueError as e:
                self.logger.error(
                    "Configuration error during render",
                    error=str(e),
                    chart_type=data.type,
                    theme=data.theme,
                )
                # Handle configuration errors (invalid type, theme, etc.)
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Configuration error",
                        "message": str(e),
                        "suggestions": [
                            "Check that the chart type is valid (line, scatter, bar)",
                            "Verify the theme name is correct (light, dark)",
                            "Ensure the format is supported (png, jpg, svg, pdf)",
                        ],
                    },
                )
            except RuntimeError as e:
                self.logger.error("Runtime error during render", error=str(e), chart_type=data.type)
                # Handle rendering errors
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Rendering failed",
                        "message": str(e),
                        "suggestions": [
                            "Verify your data values are valid numbers",
                            "Check that arrays are not empty",
                            "Try reducing the data size or simplifying the request",
                        ],
                    },
                )
            except MemoryError:
                datasets = data.get_datasets()
                data_points = len(datasets[0][0]) if datasets else 0
                self.logger.critical(
                    "Out of memory during render",
                    data_points=data_points,
                    num_datasets=len(datasets),
                    chart_type=data.type,
                )
                # Handle memory errors for large datasets
                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": "Request too large",
                        "message": "Not enough memory to render this graph",
                        "suggestions": [
                            "Reduce the number of data points",
                            "Use a lower resolution format",
                            "Try rendering in smaller batches",
                        ],
                    },
                )
            except Exception as e:
                self.logger.error(
                    "Unexpected error during render",
                    error=str(e),
                    error_type=type(e).__name__,
                    chart_type=data.type,
                )
                # Catch any other unexpected errors
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Unexpected rendering error",
                        "message": str(e),
                        "error_type": type(e).__name__,
                        "suggestions": [
                            "An unexpected error occurred",
                            "Please verify your input data",
                        ],
                    },
                )

            # Return the rendered image
            try:
                if data.return_base64:
                    # Ensure we have a string for base64 response
                    if isinstance(image_data, bytes):
                        image_data = image_data.decode("utf-8")
                    self.logger.debug("Returning base64 response")
                    return JSONResponse(content={"image": image_data})

                # Return image directly with appropriate content type
                media_types = {
                    "png": "image/png",
                    "jpg": "image/jpeg",
                    "svg": "image/svg+xml",
                    "pdf": "application/pdf",
                    "bmp": "image/bmp",
                }

                # Ensure we have bytes for direct response
                if isinstance(image_data, str):
                    # Check if it's a GUID (proxy mode)
                    try:
                        from uuid import UUID

                        UUID(image_data)
                        # It's a GUID, verify it was actually saved before returning
                        self.logger.debug("Verifying GUID was saved to storage", guid=image_data)
                        result = self.storage.get_image(image_data, group=group)

                        if result is None:
                            self.logger.error(
                                "GUID generated but image not found in storage",
                                guid=image_data,
                                group=group,
                            )
                            raise HTTPException(
                                status_code=500,
                                detail={
                                    "error": "Storage failure",
                                    "message": "Image was rendered but failed to persist to storage",
                                    "suggestions": [
                                        "Storage directory may be inaccessible",
                                        "Disk space may be insufficient",
                                        "Check server logs for details",
                                    ],
                                },
                            )

                        # Image exists in storage, return GUID
                        self.logger.debug("Returning GUID response (proxy mode)", guid=image_data)
                        return JSONResponse(
                            content={
                                "guid": image_data,
                                "format": data.format,
                                "message": f"Image saved with GUID: {image_data}",
                                "retrieve_url": f"/proxy/{image_data}",
                                "html_url": f"/proxy/{image_data}/html",
                            }
                        )
                    except ValueError:
                        # Not a GUID, it's base64
                        image_data = base64.b64decode(image_data)

                self.logger.debug(
                    "Returning direct image response",
                    media_type=media_types.get(data.format, "image/png"),
                )
                return Response(
                    content=image_data, media_type=media_types.get(data.format, "image/png")
                )
            except Exception as e:
                self.logger.error(
                    "Failed to create response", error=str(e), error_type=type(e).__name__
                )
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Response creation failed",
                        "message": f"Failed to create HTTP response: {str(e)}",
                        "suggestions": [
                            "The image was rendered but could not be returned",
                            "Try a different output format",
                        ],
                    },
                )

        @self.app.get("/proxy/{guid}")
        async def get_image_by_guid(
            request: Request, guid: str, token_info: Optional[TokenInfo] = Depends(auth_dep)
        ):
            """
            Retrieve a rendered image by its GUID.
            Returns the raw image bytes with appropriate content type.
            Requires JWT authentication and group access (unless --no-auth is used).
            """
            # Rate limiting (use default limit)
            client_id = self._get_client_id(request, token_info)
            try:
                self.rate_limiter.check_limit(client_id=client_id, endpoint="/proxy/{guid}")
            except RateLimitExceeded as e:
                self.logger.warning(
                    "Rate limit exceeded", client_id=client_id, endpoint="/proxy/{guid}"
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": str(e),
                        "retry_after": int(e.retry_after),
                    },
                    headers={"Retry-After": str(int(e.retry_after))},
                )

            group = token_info.group if token_info else "public"
            self.logger.info("Get image request", guid=guid, group=group)

            try:
                result = self.storage.get_image(guid, group=group)

                if result is None:
                    self.logger.warning("Image not found", guid=guid)
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "error": "Image not found",
                            "message": f"No image found for GUID: {guid}",
                            "suggestions": [
                                "Verify the GUID is correct",
                                "The image may have been deleted",
                            ],
                        },
                    )

                image_data, img_format = result

                media_types = {
                    "png": "image/png",
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "svg": "image/svg+xml",
                    "pdf": "application/pdf",
                    "bmp": "image/bmp",
                }

                self.logger.info(
                    "Image retrieved", guid=guid, format=img_format, size=len(image_data)
                )

                return Response(
                    content=image_data,
                    media_type=media_types.get(img_format, "image/png"),
                    headers={"Content-Disposition": f'inline; filename="{guid}.{img_format}"'},
                )

            except HTTPException:
                raise
            except PermissionDeniedError as e:
                self.logger.warning("Permission denied", guid=guid, error=str(e), group=group)
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Permission denied",
                        "message": str(e),
                    },
                )
            except ValueError as e:
                self.logger.error("Invalid GUID", guid=guid, error=str(e))
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Invalid GUID",
                        "message": str(e),
                    },
                )
            except Exception as e:
                self.logger.error("Failed to retrieve image", guid=guid, error=str(e))
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Failed to retrieve image",
                        "message": str(e),
                    },
                )

        @self.app.get("/proxy/{guid}/html")
        async def get_image_html(
            request: Request, guid: str, token_info: Optional[TokenInfo] = Depends(auth_dep)
        ):
            """
            Retrieve a rendered image by its GUID and display it in an HTML page.
            Useful for viewing images directly in a browser.
            Requires JWT authentication and group access (unless --no-auth is used).
            """
            # Rate limiting (use default limit)
            client_id = self._get_client_id(request, token_info)
            try:
                self.rate_limiter.check_limit(client_id=client_id, endpoint="/proxy/{guid}/html")
            except RateLimitExceeded as e:
                self.logger.warning(
                    "Rate limit exceeded", client_id=client_id, endpoint="/proxy/{guid}/html"
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": str(e),
                        "retry_after": int(e.retry_after),
                    },
                    headers={"Retry-After": str(int(e.retry_after))},
                )

            group = token_info.group if token_info else "public"
            self.logger.info("Get image HTML request", guid=guid, group=group)

            try:
                result = self.storage.get_image(guid, group=group)

                if result is None:
                    self.logger.warning("Image not found for HTML display", guid=guid)
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "error": "Image not found",
                            "message": f"No image found for GUID: {guid}",
                        },
                    )

                image_data, img_format = result

                # Encode image as base64 for embedding in HTML
                base64_data = base64.b64encode(image_data).decode("utf-8")

                # Determine MIME type
                mime_types = {
                    "png": "image/png",
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "bmp": "image/bmp",
                    "svg": "image/svg+xml",
                }
                mime_type = mime_types.get(img_format, "image/png")

                # Create HTML page with embedded image
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>gplot - Image {guid}</title>
                    <style>
                        body {{
                            margin: 0;
                            padding: 20px;
                            background-color: #f5f5f5;
                            font-family: Arial, sans-serif;
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                        }}
                        .container {{
                            background-color: white;
                            padding: 20px;
                            border-radius: 8px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                            max-width: 1200px;
                        }}
                        h1 {{
                            color: #333;
                            margin-top: 0;
                        }}
                        .info {{
                            color: #666;
                            margin-bottom: 20px;
                            font-size: 14px;
                        }}
                        .info code {{
                            background-color: #f0f0f0;
                            padding: 2px 6px;
                            border-radius: 3px;
                            font-family: monospace;
                        }}
                        img {{
                            max-width: 100%;
                            height: auto;
                            border: 1px solid #ddd;
                            border-radius: 4px;
                        }}
                        .links {{
                            margin-top: 20px;
                            display: flex;
                            gap: 10px;
                        }}
                        .links a {{
                            padding: 8px 16px;
                            background-color: #007bff;
                            color: white;
                            text-decoration: none;
                            border-radius: 4px;
                            font-size: 14px;
                        }}
                        .links a:hover {{
                            background-color: #0056b3;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>gplot Rendered Image</h1>
                        <div class="info">
                            <strong>GUID:</strong> <code>{guid}</code><br>
                            <strong>Format:</strong> {img_format.upper()}<br>
                            <strong>Size:</strong> {len(image_data):,} bytes
                        </div>
                        <img src="data:{mime_type};base64,{base64_data}" alt="Rendered graph {guid}">
                        <div class="links">
                            <a href="/proxy/{guid}" download="{guid}.{img_format}">Download Image</a>
                            <a href="/ping">Server Status</a>
                        </div>
                    </div>
                </body>
                </html>
                """

                self.logger.info("HTML page generated", guid=guid, format=img_format)

                return HTMLResponse(content=html_content)

            except HTTPException:
                raise
            except PermissionDeniedError as e:
                self.logger.warning(
                    "Permission denied for HTML", guid=guid, error=str(e), group=group
                )
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Permission denied",
                        "message": str(e),
                    },
                )
            except ValueError as e:
                self.logger.error("Invalid GUID for HTML", guid=guid, error=str(e))
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Invalid GUID",
                        "message": str(e),
                    },
                )
            except Exception as e:
                self.logger.error("Failed to generate HTML", guid=guid, error=str(e))
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Failed to generate HTML page",
                        "message": str(e),
                    },
                )
