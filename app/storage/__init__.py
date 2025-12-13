"""Image storage module

Provides abstract base class and concrete implementations for image storage.
Includes registry pattern for flexible storage backend selection.

NOTE: The recommended storage backend is 'common' (CommonStorageAdapter) which uses
the shared gofr-common storage implementation. The 'file' backend (FileStorage) is
maintained for backward compatibility but may be deprecated in future versions.
"""

from app.storage.base import ImageStorageBase
from app.storage.file_storage import FileStorage
from app.storage.common_adapter import CommonStorageAdapter
from app.config import get_default_storage_dir
from typing import Optional, Dict, Callable

# Storage backend registry
# 'common' is the preferred backend using gofr-common shared storage
# 'file' is legacy implementation maintained for backward compatibility
_STORAGE_BACKENDS: Dict[str, Callable[[str], ImageStorageBase]] = {
    "file": lambda dir: FileStorage(dir),  # Legacy - maintained for compatibility
    "file_v2": lambda dir: CommonStorageAdapter(dir),  # Alias for common
    "common": lambda dir: CommonStorageAdapter(dir),   # Preferred backend
}

# Global storage instance
_storage: Optional[ImageStorageBase] = None
_default_backend: str = "file_v2"  # Default to improved v2 implementation


def register_storage_backend(name: str, factory: Callable[[str], ImageStorageBase]) -> None:
    """
    Register a custom storage backend

    Args:
        name: Backend name (e.g., 's3', 'azure', 'gcs')
        factory: Factory function that takes storage_dir and returns storage instance
    """
    _STORAGE_BACKENDS[name.lower()] = factory


def list_storage_backends() -> list[str]:
    """Get list of available storage backend names"""
    return list(_STORAGE_BACKENDS.keys())


def set_default_backend(name: str) -> None:
    """
    Set the default storage backend

    Args:
        name: Backend name (must be registered)

    Raises:
        ValueError: If backend is not registered
    """
    global _default_backend
    if name.lower() not in _STORAGE_BACKENDS:
        available = ", ".join(_STORAGE_BACKENDS.keys())
        raise ValueError(f"Unknown storage backend '{name}'. Available: {available}")
    _default_backend = name.lower()


def get_storage(
    storage_dir: Optional[str] = None, backend: Optional[str] = None
) -> ImageStorageBase:
    """
    Get or create the global storage instance

    Args:
        storage_dir: Directory for file storage (only used on first call).
                    If None, uses configured default from app.config
        backend: Storage backend to use. If None, uses default backend.

    Returns:
        ImageStorageBase implementation

    Raises:
        ValueError: If backend is not registered
    """
    global _storage

    if _storage is None:
        if storage_dir is None:
            storage_dir = get_default_storage_dir()

        backend_name = (backend or _default_backend).lower()

        if backend_name not in _STORAGE_BACKENDS:
            available = ", ".join(_STORAGE_BACKENDS.keys())
            raise ValueError(f"Unknown storage backend '{backend}'. Available: {available}")

        _storage = _STORAGE_BACKENDS[backend_name](storage_dir)

    return _storage


def set_storage(storage: Optional[ImageStorageBase]) -> None:
    """
    Set a custom storage implementation or reset to None

    Args:
        storage: Custom storage implementation, or None to reset
    """
    global _storage
    _storage = storage


def reset_storage() -> None:
    """Reset the global storage instance (useful for testing)"""
    global _storage
    _storage = None


__all__ = [
    "ImageStorageBase",
    "FileStorage",
    "CommonStorageAdapter",
    "get_storage",
    "set_storage",
    "reset_storage",
    "register_storage_backend",
    "list_storage_backends",
    "set_default_backend",
]
