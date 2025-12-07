"""  
Logger module for gofr-plot

This module provides a flexible logging interface that allows users to
drop in their own logger implementations.

Re-exports from gofr_common.logger for backward compatibility.

Usage:
    from app.logger import Logger, DefaultLogger

    # Use the default logger
    logger = DefaultLogger()
    logger.info("Application started")

    # Or implement your own
    class MyCustomLogger(Logger):
        def info(self, message: str, **kwargs):
            # Your custom implementation
            pass
"""

# Re-export Logger from gofr_common.logger
from gofr_common.logger import Logger
from .default_logger import DefaultLogger
from .console_logger import ConsoleLogger

__all__ = [
    "Logger",
    "DefaultLogger",
    "ConsoleLogger",
]