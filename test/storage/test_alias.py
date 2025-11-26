"""Tests for image alias functionality

Phase 1: Core alias infrastructure tests
"""

import pytest
from app.storage.file_storage import FileStorage


@pytest.fixture
def storage(tmp_path):
    """Create FileStorage with temporary directory"""
    return FileStorage(storage_dir=str(tmp_path))


@pytest.fixture
def sample_image_data():
    """Sample image bytes for testing"""
    return b"fake-image-data-for-testing"


def test_alias_validation_valid(storage):
    """Valid aliases should pass validation"""
    valid_aliases = [
        "q4-report",
        "invoice_march",
        "weekly-summary-v2",
        "abc",  # minimum 3 chars
        "a" * 64,  # maximum 64 chars
        "Report-2024_Q4",
    ]

    for alias in valid_aliases:
        # Should not raise
        storage._validate_alias(alias)


def test_alias_validation_invalid(storage):
    """Invalid aliases should raise ValueError"""
    invalid_aliases = [
        "x",  # too short (< 3)
        "ab",  # too short
        "a" * 65,  # too long (> 64)
        "my report",  # contains space
        "report!!!",  # contains special chars
        "rep@rt",  # contains @
        "report.pdf",  # contains dot
    ]

    for alias in invalid_aliases:
        with pytest.raises(ValueError, match="Invalid alias format"):
            storage._validate_alias(alias)


def test_register_alias_success(storage, sample_image_data):
    """Register alias → GUID mapping"""
    guid = storage.save_image(sample_image_data, "png", "testgroup")

    storage.register_alias("q4-report", guid, "testgroup")

    assert storage.get_alias(guid) == "q4-report"
    aliases = storage.list_aliases("testgroup")
    assert aliases["q4-report"] == guid


def test_resolve_alias_to_guid(storage, sample_image_data):
    """resolve_identifier converts alias to GUID"""
    guid = storage.save_image(sample_image_data, "png", "research")
    storage.register_alias("experiment-1", guid, "research")

    resolved = storage.resolve_identifier("experiment-1", "research")

    assert resolved == guid


def test_resolve_guid_passthrough(storage, sample_image_data):
    """resolve_identifier returns GUID unchanged"""
    guid = storage.save_image(sample_image_data, "png", "research")

    resolved = storage.resolve_identifier(guid, "research")

    assert resolved == guid


def test_resolve_nonexistent_alias_returns_none(storage):
    """resolve_identifier returns None for unknown alias"""
    resolved = storage.resolve_identifier("nonexistent", "testgroup")

    assert resolved is None


def test_resolve_invalid_format_returns_none(storage):
    """resolve_identifier returns None for invalid format"""
    resolved = storage.resolve_identifier("bad alias!!!", "testgroup")

    assert resolved is None


def test_alias_uniqueness_per_group(storage, sample_image_data):
    """Same alias in different groups is allowed"""
    guid1 = storage.save_image(sample_image_data, "png", "group1")
    guid2 = storage.save_image(sample_image_data, "png", "group2")

    storage.register_alias("report", guid1, "group1")
    storage.register_alias("report", guid2, "group2")

    # Both should resolve to different GUIDs
    assert storage.resolve_identifier("report", "group1") == guid1
    assert storage.resolve_identifier("report", "group2") == guid2


def test_duplicate_alias_same_group_fails(storage, sample_image_data):
    """Cannot reuse alias in same group for different GUID"""
    guid1 = storage.save_image(sample_image_data, "png", "testgroup")
    guid2 = storage.save_image(sample_image_data, "png", "testgroup")

    storage.register_alias("report", guid1, "testgroup")

    with pytest.raises(ValueError, match="Alias 'report' already exists"):
        storage.register_alias("report", guid2, "testgroup")


def test_duplicate_alias_same_guid_idempotent(storage, sample_image_data):
    """Registering same alias for same GUID is idempotent"""
    guid = storage.save_image(sample_image_data, "png", "testgroup")

    storage.register_alias("report", guid, "testgroup")
    storage.register_alias("report", guid, "testgroup")  # Should not raise

    assert storage.get_alias(guid) == "report"


def test_get_alias_for_guid(storage, sample_image_data):
    """Retrieve alias from GUID"""
    guid = storage.save_image(sample_image_data, "png", "testgroup")
    storage.register_alias("my-chart", guid, "testgroup")

    alias = storage.get_alias(guid)

    assert alias == "my-chart"


def test_get_alias_for_unaliased_guid_returns_none(storage, sample_image_data):
    """get_alias returns None for GUID without alias"""
    guid = storage.save_image(sample_image_data, "png", "testgroup")

    alias = storage.get_alias(guid)

    assert alias is None


def test_alias_persistence(storage, sample_image_data, tmp_path):
    """Aliases survive FileStorage reload"""
    guid = storage.save_image(sample_image_data, "png", "testgroup")
    storage.register_alias("persistent-alias", guid, "testgroup")

    # Create new storage instance with same directory
    storage2 = FileStorage(storage_dir=str(tmp_path))

    assert storage2.get_alias(guid) == "persistent-alias"
    assert storage2.resolve_identifier("persistent-alias", "testgroup") == guid


def test_unregister_alias(storage, sample_image_data):
    """Remove alias → GUID mapping"""
    guid = storage.save_image(sample_image_data, "png", "testgroup")
    storage.register_alias("temp-alias", guid, "testgroup")

    result = storage.unregister_alias("temp-alias", "testgroup")

    assert result is True
    assert storage.get_alias(guid) is None
    assert storage.resolve_identifier("temp-alias", "testgroup") is None


def test_unregister_nonexistent_alias_returns_false(storage):
    """Unregistering nonexistent alias returns False"""
    result = storage.unregister_alias("nonexistent", "testgroup")

    assert result is False


def test_list_aliases_for_group(storage, sample_image_data):
    """List all aliases in a group"""
    guid1 = storage.save_image(sample_image_data, "png", "research")
    guid2 = storage.save_image(sample_image_data, "png", "research")
    storage.register_alias("experiment-1", guid1, "research")
    storage.register_alias("experiment-2", guid2, "research")

    aliases = storage.list_aliases("research")

    assert len(aliases) == 2
    assert aliases["experiment-1"] == guid1
    assert aliases["experiment-2"] == guid2


def test_list_aliases_empty_group(storage):
    """list_aliases returns empty dict for group with no aliases"""
    aliases = storage.list_aliases("emptygroup")

    assert aliases == {}


def test_alias_group_isolation(storage, sample_image_data):
    """Group A cannot resolve Group B's alias"""
    guid = storage.save_image(sample_image_data, "png", "groupA")
    storage.register_alias("secret-report", guid, "groupA")

    # Try to resolve from different group
    resolved = storage.resolve_identifier("secret-report", "groupB")

    assert resolved is None


def test_invalid_alias_format_rejected(storage, sample_image_data):
    """Reject aliases with invalid formats"""
    guid = storage.save_image(sample_image_data, "png", "testgroup")

    invalid_cases = [
        ("x", "too short"),
        ("my report", "contains space"),
        ("report@2024", "special char"),
        ("a" * 65, "too long"),
    ]

    for invalid_alias, reason in invalid_cases:
        with pytest.raises(ValueError, match="Invalid alias format"):
            storage.register_alias(invalid_alias, guid, "testgroup")
