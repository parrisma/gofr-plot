from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from app.models import GraphData
from app.render import GraphRenderer
from app.validation import GraphDataValidator
from app.logger import ConsoleLogger
import logging
from datetime import datetime


class GraphWebServer:
    def __init__(self):
        self.app = FastAPI(title="gplot", description="Graph rendering service")
        self.renderer = GraphRenderer()
        self.validator = GraphDataValidator()
        self.logger = ConsoleLogger(name="web_server", level=logging.INFO)
        self.logger.info("Web server initialized", version="1.0.0")
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/ping")
        async def ping():
            """
            Health check endpoint that returns the current server time.
            """
            current_time = datetime.now().isoformat()
            self.logger.debug("Ping request received", timestamp=current_time)
            return JSONResponse(
                content={"status": "ok", "timestamp": current_time, "service": "gplot"}
            )

        @self.app.post("/render")
        async def render_graph(data: GraphData):
            """
            Render a graph with comprehensive error handling.

            This endpoint ensures the server never crashes by catching all exceptions
            and returning appropriate HTTP error responses.
            """
            self.logger.info(
                "Received render request",
                chart_type=data.type,
                format=data.format,
                theme=data.theme,
                data_points=len(data.x) if data.x else 0,
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
                self.logger.debug("Starting render")
                image_data = self.renderer.render(data)
                self.logger.info(
                    "Render completed successfully",
                    chart_type=data.type,
                    format=data.format,
                    output_size=len(image_data) if isinstance(image_data, (str, bytes)) else 0,
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
                self.logger.critical(
                    "Out of memory during render",
                    data_points=len(data.x) if data.x else 0,
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
                }

                # Ensure we have bytes for direct response
                if isinstance(image_data, str):
                    import base64

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
