"""Base storage interface for image storage

Defines the abstract interface that all storage implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, List


class ImageStorageBase(ABC):
    """Abstract base class for image storage implementations"""

    @abstractmethod
    def save_image(
        self, image_data: bytes, format: str = "png", group: Optional[str] = None
    ) -> str:
        """
        Save image data and return a unique identifier

        Args:
            image_data: Raw image bytes
            format: Image format (png, jpg, svg, pdf, etc.)
            group: Optional group name for access control

        Returns:
            Unique identifier (e.g., GUID, key, path) for the saved image

        Raises:
            RuntimeError: If save fails
        """
        pass

    @abstractmethod
    def get_image(
        self, identifier: str, group: Optional[str] = None
    ) -> Optional[Tuple[bytes, str]]:
        """
        Retrieve image data by identifier

        Args:
            identifier: Unique identifier for the image
            group: Optional group name for access control

        Returns:
            Tuple of (image_data, format) or None if not found

        Raises:
            ValueError: If identifier format is invalid or group mismatch
            RuntimeError: If retrieval fails
        """
        pass

    @abstractmethod
    def delete_image(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Delete image by identifier

        Args:
            identifier: Unique identifier for the image
            group: Optional group name for access control

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If identifier format is invalid or group mismatch
        """
        pass

    @abstractmethod
    def list_images(self, group: Optional[str] = None) -> List[str]:
        """
        List all stored image identifiers

        Args:
            group: Optional group name to filter by

        Returns:
            List of identifier strings
        """
        pass

    @abstractmethod
    def exists(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Check if an image exists

        Args:
            identifier: Unique identifier for the image
            group: Optional group name for access control

        Returns:
            True if image exists, False otherwise
        """
        pass

    @abstractmethod
    def purge(self, age_days: int = 0, group: Optional[str] = None) -> int:
        """
        Delete images older than specified age

        Args:
            age_days: Delete images older than this many days. 0 means delete all.
            group: Optional group name to filter by

        Returns:
            Number of images deleted

        Raises:
            RuntimeError: If purge fails
        """
        pass

    def resolve_identifier(self, identifier: str, group: Optional[str] = None) -> Optional[str]:
        """
        Resolve an alias or GUID to a GUID

        Args:
            identifier: Alias or GUID string
            group: Optional group name for alias resolution

        Returns:
            GUID string if found, None otherwise
        """
        # Default implementation: just return identifier if it looks like a GUID
        import uuid

        try:
            uuid.UUID(identifier)
            return identifier
        except ValueError:
            return None

    def register_alias(self, alias: str, guid: str, group: str) -> None:
        """
        Register an alias for a GUID

        Args:
            alias: Alias string (3-64 chars, alphanumeric + hyphens/underscores)
            guid: GUID to associate with alias
            group: Group name for isolation

        Raises:
            ValueError: If alias format invalid or already exists for different GUID
        """
        pass  # Default: no-op

    def unregister_alias(self, alias: str, group: str) -> bool:
        """
        Remove an alias registration

        Args:
            alias: Alias to remove
            group: Group name

        Returns:
            True if removed, False if not found
        """
        return False  # Default: not found

    def get_alias(self, guid: str) -> Optional[str]:
        """
        Get alias for a GUID

        Args:
            guid: GUID string

        Returns:
            Alias if registered, None otherwise
        """
        return None  # Default: no alias

    def list_aliases(self, group: str) -> dict:
        """
        List all aliases in a group

        Args:
            group: Group name

        Returns:
            Dictionary mapping aliases to GUIDs
        """
        return {}  # Default: empty
