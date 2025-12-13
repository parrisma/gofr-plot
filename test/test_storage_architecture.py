"""Tests for storage architecture improvements (Phase 3)

Tests the shared gofr-common storage implementation and storage registry.
These tests verify that the CommonStorageAdapter correctly wraps gofr-common storage.
"""

import pytest
from datetime import datetime, timedelta
from gofr_common.storage.metadata import JsonMetadataRepository, BlobMetadata
from gofr_common.storage.blob import FileBlobRepository
from app.storage.common_adapter import CommonStorageAdapter
from app.storage import (
    register_storage_backend,
    list_storage_backends,
    set_default_backend,
    get_storage,
    reset_storage,
    ImageStorageBase,
)


# Alias for backward compatibility in tests
ImageMetadata = BlobMetadata

# Metadata Repository Tests


def test_image_metadata_creation():
    """Test ImageMetadata creation"""
    metadata = ImageMetadata(
        guid="test-guid-123",
        format="png",
        size=1024,
        created_at="2025-01-01T00:00:00",
        group="test_group",
    )

    assert metadata.guid == "test-guid-123"
    assert metadata.format == "png"
    assert metadata.size == 1024
    assert metadata.group == "test_group"


def test_image_metadata_to_dict():
    """Test ImageMetadata serialization"""
    metadata = ImageMetadata(
        guid="test-guid",
        format="jpg",
        size=2048,
        created_at="2025-01-01T00:00:00",
        group="group1",
    )

    data = metadata.to_dict()
    assert data["format"] == "jpg"
    assert data["size"] == 2048
    assert data["created_at"] == "2025-01-01T00:00:00"
    assert data["group"] == "group1"


def test_image_metadata_from_dict():
    """Test ImageMetadata deserialization"""
    data = {
        "format": "svg",
        "size": 512,
        "created_at": "2025-01-01T12:00:00",
        "group": "group2",
    }

    metadata = ImageMetadata.from_dict("test-guid", data)
    assert metadata.guid == "test-guid"
    assert metadata.format == "svg"
    assert metadata.size == 512
    assert metadata.group == "group2"


def test_json_metadata_repository(tmp_path):
    """Test JSON metadata repository save/get"""
    metadata_file = tmp_path / "metadata.json"
    repo = JsonMetadataRepository(metadata_file)

    # Save metadata
    metadata = ImageMetadata(
        guid="test-guid-1",
        format="png",
        size=1024,
        created_at=datetime.utcnow().isoformat(),
        group="test",
    )
    repo.save(metadata)

    # Get metadata
    retrieved = repo.get("test-guid-1")
    assert retrieved is not None
    assert retrieved.guid == "test-guid-1"
    assert retrieved.format == "png"
    assert retrieved.size == 1024


def test_json_metadata_repository_delete(tmp_path):
    """Test JSON metadata repository delete"""
    repo = JsonMetadataRepository(tmp_path / "metadata.json")

    metadata = ImageMetadata(
        guid="test-guid", format="png", size=100, created_at=datetime.utcnow().isoformat()
    )
    repo.save(metadata)

    assert repo.exists("test-guid")
    repo.delete("test-guid")
    assert not repo.exists("test-guid")


def test_json_metadata_repository_list(tmp_path):
    """Test JSON metadata repository listing"""
    repo = JsonMetadataRepository(tmp_path / "metadata.json")

    # Save multiple items
    for i in range(3):
        metadata = ImageMetadata(
            guid=f"guid-{i}",
            format="png",
            size=100,
            created_at=datetime.utcnow().isoformat(),
            group="group1" if i < 2 else "group2",
        )
        repo.save(metadata)

    # List all
    all_guids = repo.list_all()
    assert len(all_guids) == 3

    # List filtered by group
    group1_guids = repo.list_all(group="group1")
    assert len(group1_guids) == 2


def test_json_metadata_repository_filter_by_age(tmp_path):
    """Test filtering metadata by age"""
    repo = JsonMetadataRepository(tmp_path / "metadata.json")

    # Create old metadata
    old_time = (datetime.utcnow() - timedelta(days=10)).isoformat()
    metadata1 = ImageMetadata(guid="old-guid", format="png", size=100, created_at=old_time)
    repo.save(metadata1)

    # Create recent metadata
    recent_time = datetime.utcnow().isoformat()
    metadata2 = ImageMetadata(guid="new-guid", format="png", size=100, created_at=recent_time)
    repo.save(metadata2)

    # Filter older than 5 days
    old_items = repo.filter_by_age(5)
    assert len(old_items) == 1
    assert old_items[0].guid == "old-guid"


# Blob Repository Tests


def test_file_blob_repository_save_get(tmp_path):
    """Test blob repository save and retrieve"""
    repo = FileBlobRepository(tmp_path)

    data = b"test image data"
    repo.save("test-guid", data, "png")

    retrieved = repo.get("test-guid", "png")
    assert retrieved == data


def test_file_blob_repository_delete(tmp_path):
    """Test blob repository delete"""
    repo = FileBlobRepository(tmp_path)

    repo.save("test-guid", b"data", "png")
    assert repo.exists("test-guid", "png")

    repo.delete("test-guid", "png")
    assert not repo.exists("test-guid", "png")


def test_file_blob_repository_list(tmp_path):
    """Test blob repository listing"""
    import uuid

    repo = FileBlobRepository(tmp_path)

    # Save multiple blobs with valid UUIDs
    saved_guids = []
    for i in range(3):
        guid = str(uuid.uuid4())
        repo.save(guid, b"data", "png")
        saved_guids.append(guid)

    guids = repo.list_all()
    assert len(guids) == 3
    for saved_guid in saved_guids:
        assert saved_guid in guids


def test_file_blob_repository_get_format(tmp_path):
    """Test blob format detection"""
    repo = FileBlobRepository(tmp_path)

    repo.save("test-guid", b"data", "jpg")

    detected = repo.get_format("test-guid")
    assert detected == "jpg"


# CommonStorageAdapter Integration Tests (replaces FileStorageV2)


def test_common_storage_adapter_save_get(tmp_path):
    """Test CommonStorageAdapter save and retrieve"""
    storage = CommonStorageAdapter(tmp_path)

    data = b"test image data"
    guid = storage.save_image(data, "png", group="test_group")

    retrieved = storage.get_image(guid, group="test_group")
    assert retrieved is not None
    assert retrieved[0] == data
    assert retrieved[1] == "png"


def test_common_storage_adapter_group_isolation(tmp_path):
    """Test group-based access control"""
    storage = CommonStorageAdapter(tmp_path)

    guid = storage.save_image(b"data", "png", group="group1")

    # Should fail with wrong group
    from app.storage.exceptions import PermissionDeniedError

    with pytest.raises(PermissionDeniedError):
        storage.get_image(guid, group="group2")


def test_common_storage_adapter_delete(tmp_path):
    """Test CommonStorageAdapter delete"""
    storage = CommonStorageAdapter(tmp_path)

    guid = storage.save_image(b"data", "png")
    assert storage.exists(guid)

    storage.delete_image(guid)
    assert not storage.exists(guid)


def test_common_storage_adapter_list_filtered(tmp_path):
    """Test CommonStorageAdapter listing with group filter"""
    storage = CommonStorageAdapter(tmp_path)

    # Save images to different groups
    guid1 = storage.save_image(b"data1", "png", group="group1")
    guid2 = storage.save_image(b"data2", "png", group="group1")
    _guid3 = storage.save_image(b"data3", "png", group="group2")  # Different group

    # List by group
    group1_images = storage.list_images(group="group1")
    assert len(group1_images) == 2
    assert guid1 in group1_images
    assert guid2 in group1_images


def test_common_storage_adapter_purge(tmp_path):
    """Test CommonStorageAdapter purge functionality"""
    storage = CommonStorageAdapter(tmp_path)

    # Save some images
    guid1 = storage.save_image(b"data1", "png")
    guid2 = storage.save_image(b"data2", "png")

    # Purge all
    deleted = storage.purge(age_days=0)
    assert deleted == 2
    assert not storage.exists(guid1)
    assert not storage.exists(guid2)


# Storage Registry Tests


def test_list_storage_backends():
    """Test listing available storage backends"""
    backends = list_storage_backends()
    assert "file" in backends
    assert "file_v2" in backends
    assert len(backends) >= 2


def test_register_custom_backend():
    """Test registering a custom storage backend"""
    from app.storage.base import ImageStorageBase

    class MockStorage(ImageStorageBase):
        def save_image(self, image_data: bytes, format: str = "png", group=None):
            return "mock-guid"

        def get_image(self, identifier: str, group=None):
            return (b"mock-data", "png")

        def delete_image(self, identifier: str, group=None):
            return True

        def list_images(self, group=None):
            return []

        def exists(self, identifier: str, group=None):
            return False

        def purge(self, age_days: int = 0, group=None):
            return 0

    # Register custom backend
    register_storage_backend("mock", lambda dir: MockStorage())

    # Verify it's registered
    assert "mock" in list_storage_backends()


def test_set_default_backend():
    """Test setting default storage backend"""
    set_default_backend("file")
    # Default is now set (tested via get_storage behavior)


def test_get_storage_with_backend(tmp_path):
    """Test getting storage with specific backend"""
    reset_storage()

    storage = get_storage(str(tmp_path), backend="file_v2")
    # file_v2 is now mapped to CommonStorageAdapter
    assert isinstance(storage, CommonStorageAdapter)


def test_get_storage_unknown_backend(tmp_path):
    """Test error handling for unknown backend"""
    reset_storage()

    with pytest.raises(ValueError, match="Unknown storage backend"):
        get_storage(str(tmp_path), backend="unknown")


def test_storage_backward_compatibility(tmp_path):
    """Test that default storage still works"""
    reset_storage()

    # Get default storage (should work without errors)
    storage = get_storage(str(tmp_path))
    assert isinstance(storage, ImageStorageBase)

    # Should be able to save/retrieve
    guid = storage.save_image(b"test", "png")
    result = storage.get_image(guid)
    assert result is not None
