"""Improved file-based storage implementation (v2)

Uses separate metadata and blob repositories for better separation of concerns.
"""

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from app.storage.base import ImageStorageBase
from app.storage.metadata import JsonMetadataRepository, ImageMetadata
from app.storage.blob import FileBlobRepository
from app.storage.exceptions import PermissionDeniedError
from app.logger import ConsoleLogger
import logging


class FileStorageV2(ImageStorageBase):
    """
    File-based image storage using separate metadata and blob repositories

    This implementation provides better separation of concerns by splitting
    metadata management from binary data storage.
    """

    def __init__(self, storage_dir: str | Path):
        """
        Initialize file storage with separate repositories

        Args:
            storage_dir: Directory to store images and metadata
        """
        storage_path = Path(storage_dir)
        self.logger = ConsoleLogger(name="file_storage_v2", level=logging.INFO)

        # Initialize repositories
        self.metadata_repo = JsonMetadataRepository(storage_path / "metadata.json")
        self.blob_repo = FileBlobRepository(storage_path)

        # Alias maps: group -> alias -> guid, guid -> alias
        self._alias_to_guid: Dict[str, Dict[str, str]] = {}
        self._guid_to_alias: Dict[str, str] = {}
        self._rebuild_alias_maps()

        self.logger.info("FileStorageV2 initialized", directory=str(storage_path))

    def save_image(
        self, image_data: bytes, format: str = "png", group: Optional[str] = None
    ) -> str:
        """
        Save image data using separate metadata and blob repositories

        Args:
            image_data: Raw image bytes
            format: Image format (png, jpg, svg, pdf, etc.)
            group: Optional group name for access control

        Returns:
            GUID string (identifier without extension)

        Raises:
            RuntimeError: If save fails
        """
        guid = str(uuid.uuid4())

        self.logger.debug(
            "Saving image", guid=guid, format=format, size=len(image_data), group=group
        )

        try:
            # Save blob first
            self.blob_repo.save(guid, image_data, format.lower())

            # Then save metadata
            metadata = ImageMetadata(
                guid=guid,
                format=format.lower(),
                size=len(image_data),
                created_at=datetime.utcnow().isoformat(),
                group=group,
            )
            self.metadata_repo.save(metadata)

            self.logger.info("Image saved", guid=guid, format=format, group=group)
            return guid

        except Exception as e:
            # Cleanup blob if metadata save fails
            try:
                self.blob_repo.delete(guid, format.lower())
            except Exception:
                pass
            self.logger.error("Failed to save image", guid=guid, error=str(e))
            raise RuntimeError(f"Failed to save image: {str(e)}")

    def get_image(
        self, identifier: str, group: Optional[str] = None
    ) -> Optional[Tuple[bytes, str]]:
        """
        Retrieve image data by GUID

        Args:
            identifier: GUID string (without extension)
            group: Optional group name for access control

        Returns:
            Tuple of (image_data, format) or None if not found

        Raises:
            ValueError: If GUID format is invalid or group mismatch
        """
        # Validate GUID format
        try:
            uuid.UUID(identifier)
        except ValueError:
            self.logger.warning("Invalid GUID format", guid=identifier)
            raise ValueError(f"Invalid GUID format: {identifier}")

        # Get metadata
        metadata = self.metadata_repo.get(identifier)

        # Check group access
        if metadata:
            if group is not None and metadata.group is not None and metadata.group != group:
                self.logger.warning(
                    "Group mismatch",
                    guid=identifier,
                    requested_group=group,
                    stored_group=metadata.group,
                )
                raise PermissionDeniedError(
                    f"Access denied: image belongs to group '{metadata.group}', not '{group}'"
                )

        self.logger.debug("Retrieving image", guid=identifier, group=group)

        # Try metadata format first, then fallback to detection
        if metadata:
            blob_data = self.blob_repo.get(identifier, metadata.format)
            if blob_data:
                self.logger.info(
                    "Image retrieved", guid=identifier, format=metadata.format, size=len(blob_data)
                )
                return (blob_data, metadata.format)

        # Fallback: try to detect format
        detected_format = self.blob_repo.get_format(identifier)
        if detected_format:
            blob_data = self.blob_repo.get(identifier, detected_format)
            if blob_data:
                self.logger.info(
                    "Image retrieved (format detected)",
                    guid=identifier,
                    format=detected_format,
                    size=len(blob_data),
                )
                return (blob_data, detected_format)

        self.logger.warning("Image not found", guid=identifier)
        return None

    def delete_image(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Delete image by GUID

        Args:
            identifier: GUID string (without extension)
            group: Optional group name for access control

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If group mismatch
        """
        # Validate GUID format
        try:
            uuid.UUID(identifier)
        except ValueError:
            self.logger.warning("Invalid GUID format for deletion", guid=identifier)
            return False

        # Get metadata
        metadata = self.metadata_repo.get(identifier)

        # Check group access
        if metadata:
            if group is not None and metadata.group is not None and metadata.group != group:
                self.logger.warning(
                    "Group mismatch for deletion",
                    guid=identifier,
                    requested_group=group,
                    stored_group=metadata.group,
                )
                raise PermissionDeniedError(
                    f"Access denied: image belongs to group '{metadata.group}', not '{group}'"
                )

        # Delete blob
        blob_deleted = self.blob_repo.delete(identifier)

        # Delete metadata
        metadata_deleted = self.metadata_repo.delete(identifier)

        if blob_deleted or metadata_deleted:
            self.logger.info("Image deleted", guid=identifier, group=group)
            return True

        return False

    def list_images(self, group: Optional[str] = None) -> List[str]:
        """
        List all stored image GUIDs, optionally filtered by group

        Args:
            group: Optional group name to filter by

        Returns:
            List of GUID strings
        """
        # Use metadata repo for listing (it has group info)
        guids = self.metadata_repo.list_all(group=group)
        self.logger.debug("Listed images", count=len(guids), group=group)
        return guids

    def exists(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Check if an image exists and is accessible to the group

        Args:
            identifier: GUID string (without extension)
            group: Optional group name for access control

        Returns:
            True if image exists and is accessible, False otherwise
        """
        # Validate GUID format
        try:
            uuid.UUID(identifier)
        except ValueError:
            return False

        # Get metadata
        metadata = self.metadata_repo.get(identifier)

        # Check group access if specified
        if group is not None and metadata:
            if metadata.group is not None and metadata.group != group:
                return False

        # Check if blob exists
        return self.blob_repo.exists(identifier)

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
        self.logger.info("Starting purge", age_days=age_days, group=group)

        try:
            # Get metadata for images to delete
            to_delete = self.metadata_repo.filter_by_age(age_days, group)

            deleted_count = 0
            for metadata in to_delete:
                # Delete blob
                self.blob_repo.delete(metadata.guid, metadata.format)
                # Delete metadata
                self.metadata_repo.delete(metadata.guid)
                deleted_count += 1
                self.logger.debug("Purged image", guid=metadata.guid)

            # Clean up orphaned blobs (blobs without metadata)
            all_blob_guids = set(self.blob_repo.list_all())
            all_metadata_guids = set(self.metadata_repo.list_all())
            orphaned_blobs = all_blob_guids - all_metadata_guids

            for guid in orphaned_blobs:
                self.blob_repo.delete(guid)
                deleted_count += 1
                self.logger.debug("Removed orphaned blob", guid=guid)

            self.logger.info(
                "Purge completed", deleted_count=deleted_count, age_days=age_days, group=group
            )
            return deleted_count

        except Exception as e:
            self.logger.error("Purge operation failed", error=str(e))
            raise RuntimeError(f"Failed to purge images: {str(e)}")

    # === Alias Methods ===

    def _rebuild_alias_maps(self) -> None:
        """Rebuild alias maps from persisted metadata"""
        self._alias_to_guid.clear()
        self._guid_to_alias.clear()

        # Iterate through all metadata entries
        for guid in self.metadata_repo.list_all():
            metadata = self.metadata_repo.get(guid)
            if metadata and metadata.extra.get("alias"):
                alias = metadata.extra["alias"]
                group = metadata.group or "default"

                # Build maps
                if group not in self._alias_to_guid:
                    self._alias_to_guid[group] = {}
                self._alias_to_guid[group][alias] = guid
                self._guid_to_alias[guid] = alias

    def _validate_alias(self, alias: str) -> None:
        """Validate alias format

        Args:
            alias: Alias string to validate

        Raises:
            ValueError: If alias format is invalid
        """
        if not re.match(r"^[a-zA-Z0-9_-]{3,64}$", alias):
            raise ValueError(
                f"Invalid alias format: '{alias}'. Must be 3-64 characters, "
                "alphanumeric with hyphens/underscores only."
            )

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
            return identifier  # Valid GUID, return as-is
        except ValueError:
            pass

        # Try as alias
        if group and group in self._alias_to_guid:
            return self._alias_to_guid[group].get(identifier)

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
        self._validate_alias(alias)

        # Check if alias already exists in this group
        if group in self._alias_to_guid and alias in self._alias_to_guid[group]:
            existing_guid = self._alias_to_guid[group][alias]
            if existing_guid != guid:
                raise ValueError(
                    f"Alias '{alias}' already exists in group '{group}' "
                    f"for a different image (GUID: {existing_guid})"
                )
            return  # Already registered for same GUID

        # Verify GUID exists
        if not self.metadata_repo.exists(guid):
            raise ValueError(f"Cannot register alias: GUID '{guid}' not found")

        # Update in-memory maps
        if group not in self._alias_to_guid:
            self._alias_to_guid[group] = {}
        self._alias_to_guid[group][alias] = guid
        self._guid_to_alias[guid] = alias

        # Persist alias in metadata
        metadata = self.metadata_repo.get(guid)
        if metadata:
            # Create updated metadata with alias
            updated_data = metadata.to_dict()
            updated_data["alias"] = alias
            updated_metadata = ImageMetadata.from_dict(guid, updated_data)
            self.metadata_repo.save(updated_metadata)

        self.logger.info("Alias registered", alias=alias, guid=guid, group=group)

    def unregister_alias(self, alias: str, group: str) -> bool:
        """Remove an alias registration

        Args:
            alias: Alias to remove
            group: Group name

        Returns:
            True if removed, False if not found
        """
        if group not in self._alias_to_guid:
            return False

        if alias not in self._alias_to_guid[group]:
            return False

        guid = self._alias_to_guid[group].pop(alias)
        self._guid_to_alias.pop(guid, None)

        # Remove alias from metadata
        metadata = self.metadata_repo.get(guid)
        if metadata and metadata.extra.get("alias"):
            updated_data = metadata.to_dict()
            del updated_data["alias"]
            updated_metadata = ImageMetadata.from_dict(guid, updated_data)
            self.metadata_repo.save(updated_metadata)

        self.logger.info("Alias unregistered", alias=alias, guid=guid, group=group)
        return True

    def get_alias(self, guid: str) -> Optional[str]:
        """Get alias for a GUID

        Args:
            guid: GUID string

        Returns:
            Alias if registered, None otherwise
        """
        return self._guid_to_alias.get(guid)

    def list_aliases(self, group: str) -> dict:
        """List all aliases in a group

        Args:
            group: Group name

        Returns:
            Dictionary mapping aliases to GUIDs
        """
        return dict(self._alias_to_guid.get(group, {}))
