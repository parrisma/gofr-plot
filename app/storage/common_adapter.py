"""Adapter for gofr-common storage

Adapts the gofr-common storage implementation to the gofr-plot ImageStorageBase interface.
"""

from typing import Optional, Tuple, List
from pathlib import Path
import logging
import uuid

from app.storage.base import ImageStorageBase
from app.storage.exceptions import PermissionDeniedError as PlotPermissionDeniedError
from gofr_common.storage.file_storage import FileStorage as CommonFileStorage
from gofr_common.storage.exceptions import (
    PermissionDeniedError as CommonPermissionDeniedError,
    StorageError,
    ResourceNotFoundError
)

logger = logging.getLogger("storage.adapter")

class CommonStorageAdapter(ImageStorageBase):
    """Adapter for gofr-common FileStorage"""

    def __init__(self, storage_dir: str | Path):
        """
        Initialize adapter with gofr-common FileStorage

        Args:
            storage_dir: Directory to store images
        """
        self._storage = CommonFileStorage(storage_dir)
        logger.info("CommonStorageAdapter initialized", extra={"directory": str(storage_dir)})

    def save_image(
        self, image_data: bytes, format: str = "png", group: Optional[str] = None
    ) -> str:
        """Save image using common storage"""
        try:
            return self._storage.save(image_data, format, group)
        except StorageError as e:
            raise RuntimeError(f"Failed to save image: {str(e)}") from e

    def get_image(
        self, identifier: str, group: Optional[str] = None
    ) -> Optional[Tuple[bytes, str]]:
        """Retrieve image using common storage"""
        try:
            return self._storage.get(identifier, group)
        except CommonPermissionDeniedError as e:
            raise PlotPermissionDeniedError(str(e)) from e
        except ResourceNotFoundError:
            return None
        except StorageError as e:
            raise RuntimeError(f"Failed to retrieve image: {str(e)}") from e
        except ValueError as e:
            # gofr-common might raise ValueError for invalid GUIDs
            raise ValueError(str(e)) from e

    def delete_image(self, identifier: str, group: Optional[str] = None) -> bool:
        """Delete image using common storage"""
        try:
            return self._storage.delete(identifier, group)
        except CommonPermissionDeniedError as e:
            raise PlotPermissionDeniedError(str(e)) from e
        except ValueError as e:
            raise ValueError(str(e)) from e

    def list_images(self, group: Optional[str] = None) -> List[str]:
        """List images using common storage"""
        return self._storage.list(group)

    def exists(self, identifier: str, group: Optional[str] = None) -> bool:
        """Check existence using common storage"""
        return self._storage.exists(identifier, group)

    def purge(self, age_days: int = 0, group: Optional[str] = None) -> int:
        """Purge old images using common storage"""
        return self._storage.purge(age_days, group)

    def resolve_identifier(self, identifier: str, group: Optional[str] = None) -> Optional[str]:
        """Resolve alias or GUID to GUID

        Args:
            identifier: Alias or GUID string
            group: Optional group name for alias resolution

        Returns:
            GUID string if found, None otherwise
        """
        # Try as GUID first
        try:
            uuid.UUID(identifier)
            return identifier
        except ValueError:
            pass

        # Try as alias using internal maps of the common storage
        if hasattr(self._storage, "_alias_to_guid"):
            if group and group in self._storage._alias_to_guid:
                return self._storage._alias_to_guid[group].get(identifier)
        
        return None

    def register_alias(self, alias: str, guid: str, group: str) -> None:
        """Register an alias for a GUID

        Args:
            alias: Alias string
            guid: GUID to associate with alias
            group: Group name for isolation

        Raises:
            ValueError: If alias format invalid or already exists
        """
        self._storage.register_alias(alias, guid, group)

    def unregister_alias(self, alias: str, group: str) -> bool:
        """Remove an alias registration

        Args:
            alias: Alias to remove
            group: Group name

        Returns:
            True if removed, False if not found
        """
        if not hasattr(self._storage, "_alias_to_guid"):
            return False
            
        if group not in self._storage._alias_to_guid:
            return False

        if alias not in self._storage._alias_to_guid[group]:
            return False

        guid = self._storage._alias_to_guid[group][alias]
        
        # Remove from metadata
        try:
            metadata = self._storage.metadata_repo.get(guid)
            if metadata and "aliases" in metadata.extra:
                aliases = metadata.extra["aliases"]
                if alias in aliases:
                    aliases.remove(alias)
                    metadata.extra["aliases"] = aliases
                    self._storage.metadata_repo.save(metadata)
                    
            # Rebuild maps to reflect changes
            self._storage._rebuild_alias_maps()
            return True
        except Exception as e:
            logger.error(f"Failed to unregister alias: {e}")
            return False

    def get_alias(self, guid: str) -> Optional[str]:
        """Get alias for a GUID

        Args:
            guid: GUID string

        Returns:
            Alias if registered, None otherwise
        """
        return self._storage.get_alias(guid)

    def list_aliases(self, group: str) -> dict:
        """List all aliases in a group

        Args:
            group: Group name

        Returns:
            Dictionary mapping alias -> guid
        """
        if hasattr(self._storage, "_alias_to_guid"):
            if group in self._storage._alias_to_guid:
                return self._storage._alias_to_guid[group].copy()
        return {}
