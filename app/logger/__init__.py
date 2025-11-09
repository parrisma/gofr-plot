"""
Logger module for gplot

This module provides a flexible logging interface that allows users to
drop in their own logger implementations.

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

from .interface import Logger
from .default_logger import DefaultLogger
from .console_logger import ConsoleLogger

__all__ = [
    "Logger",
    "DefaultLogger",
    "ConsoleLogger",
]
