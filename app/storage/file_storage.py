"""File-based storage implementation

Stores images as files in a directory with GUID-based filenames.
Supports group-based segregation for access control.
"""

import os
import uuid
import json
from pathlib import Path
from typing import Optional, Tuple, List
from app.storage.base import ImageStorageBase
from app.config import get_default_storage_dir
from app.logger import ConsoleLogger
import logging


class FileStorage(ImageStorageBase):
    """File-based image storage using GUID filenames with group segregation"""

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize file storage

        Args:
            storage_dir: Directory to store images. If None, uses configured default from app.config
        """
        if storage_dir is None:
            storage_dir = get_default_storage_dir()
        self.storage_dir = Path(storage_dir)
        self.metadata_file = self.storage_dir / "metadata.json"
        self.logger = ConsoleLogger(name="file_storage", level=logging.INFO)

        # Create storage directory if it doesn't exist
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self._load_metadata()
            self.logger.info("File storage initialized", directory=str(self.storage_dir))
        except Exception as e:
            self.logger.error("Failed to create storage directory", error=str(e))
            raise RuntimeError(f"Failed to create storage directory: {str(e)}")

    def _load_metadata(self) -> None:
        """Load image metadata including group mappings"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    data = json.load(f)
                    # Validate that metadata is a dict, not a list or other type
                    if isinstance(data, dict):
                        self.metadata = data
                        self.logger.debug("Metadata loaded", images_count=len(self.metadata))
                    else:
                        self.logger.warning(
                            "Metadata has unexpected structure, resetting to empty dict",
                            type=type(data).__name__,
                        )
                        self.metadata = {}
            except Exception as e:
                self.logger.error("Failed to load metadata", error=str(e))
                self.metadata = {}
        else:
            self.metadata = {}
            self.logger.debug("Metadata initialized as empty")

    def _save_metadata(self) -> None:
        """Save image metadata to disk"""
        try:
            with open(self.metadata_file, "w") as f:
                json.dump(self.metadata, f, indent=2)
            self.logger.debug("Metadata saved", images_count=len(self.metadata))
        except Exception as e:
            self.logger.error("Failed to save metadata", error=str(e))
            raise RuntimeError(f"Failed to save metadata: {str(e)}")

    def save_image(
        self, image_data: bytes, format: str = "png", group: Optional[str] = None
    ) -> str:
        """
        Save image data to disk with a unique GUID

        Args:
            image_data: Raw image bytes
            format: Image format (png, jpg, svg, pdf, etc.)
            group: Optional group name for access control

        Returns:
            GUID string (identifier without extension)

        Raises:
            RuntimeError: If save fails
        """
        # Generate unique GUID
        guid = str(uuid.uuid4())
        filename = f"{guid}.{format.lower()}"
        filepath = self.storage_dir / filename

        self.logger.debug(
            "Saving image to file", guid=guid, format=format, size=len(image_data), group=group
        )

        try:
            with open(filepath, "wb") as f:
                f.write(image_data)

            # Store metadata
            self.metadata[guid] = {
                "format": format.lower(),
                "group": group,
                "size": len(image_data),
            }
            self._save_metadata()

            self.logger.info("Image saved to file", guid=guid, path=str(filepath), group=group)
            return guid
        except Exception as e:
            self.logger.error("Failed to save image file", guid=guid, error=str(e))
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

        # Check group access
        if identifier in self.metadata:
            stored_group = self.metadata[identifier].get("group")
            if group is not None and stored_group is not None and stored_group != group:
                self.logger.warning(
                    "Group mismatch",
                    guid=identifier,
                    requested_group=group,
                    stored_group=stored_group,
                )
                raise ValueError(f"Access denied: image belongs to different group")

        self.logger.debug("Retrieving image from file", guid=identifier, group=group)

        # Try common formats (prefer metadata format if available)
        formats = ["png", "jpg", "jpeg", "svg", "pdf"]
        if identifier in self.metadata:
            stored_format = self.metadata[identifier].get("format")
            if stored_format and stored_format in formats:
                formats = [stored_format] + [f for f in formats if f != stored_format]

        for ext in formats:
            filepath = self.storage_dir / f"{identifier}.{ext}"
            if filepath.exists():
                try:
                    with open(filepath, "rb") as f:
                        image_data = f.read()
                    self.logger.info(
                        "Image retrieved from file",
                        guid=identifier,
                        format=ext,
                        size=len(image_data),
                        group=group,
                    )
                    return (image_data, ext)
                except Exception as e:
                    self.logger.error("Failed to read image file", guid=identifier, error=str(e))
                    raise RuntimeError(f"Failed to read image: {str(e)}")

        self.logger.warning("Image file not found", guid=identifier)
        return None

    def delete_image(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Delete image file by GUID

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

        # Check group access
        if identifier in self.metadata:
            stored_group = self.metadata[identifier].get("group")
            if group is not None and stored_group is not None and stored_group != group:
                self.logger.warning(
                    "Group mismatch for deletion",
                    guid=identifier,
                    requested_group=group,
                    stored_group=stored_group,
                )
                raise ValueError(f"Access denied: image belongs to different group")

        deleted = False
        for ext in ["png", "jpg", "jpeg", "svg", "pdf"]:
            filepath = self.storage_dir / f"{identifier}.{ext}"
            if filepath.exists():
                try:
                    filepath.unlink()
                    self.logger.info("Image file deleted", guid=identifier, format=ext, group=group)
                    deleted = True
                except Exception as e:
                    self.logger.error("Failed to delete image file", guid=identifier, error=str(e))

        # Remove from metadata
        if identifier in self.metadata:
            del self.metadata[identifier]
            self._save_metadata()

        return deleted

    def list_images(self, group: Optional[str] = None) -> List[str]:
        """
        List all stored image GUIDs, optionally filtered by group

        Args:
            group: Optional group name to filter by

        Returns:
            List of GUID strings
        """
        try:
            guids = set()
            for filepath in self.storage_dir.iterdir():
                if filepath.is_file() and filepath.suffix in [
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".svg",
                    ".pdf",
                ]:
                    # Extract GUID (filename without extension)
                    guid = filepath.stem
                    try:
                        uuid.UUID(guid)
                        # Filter by group if specified
                        if group is not None:
                            if guid in self.metadata and self.metadata[guid].get("group") == group:
                                guids.add(guid)
                        else:
                            guids.add(guid)
                    except ValueError:
                        # Skip non-GUID files
                        pass
            self.logger.debug("Listed image files", count=len(guids), group=group)
            return sorted(guids)
        except Exception as e:
            self.logger.error("Failed to list image files", error=str(e))
            return []

    def exists(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Check if an image file exists and is accessible to the group

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

        # Check group access if specified
        if group is not None and identifier in self.metadata:
            stored_group = self.metadata[identifier].get("group")
            if stored_group is not None and stored_group != group:
                return False

        # Check for any matching file with common extensions
        for ext in ["png", "jpg", "jpeg", "svg", "pdf"]:
            filepath = self.storage_dir / f"{identifier}.{ext}"
            if filepath.exists():
                return True

        return False
