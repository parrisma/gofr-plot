# Storage Module

The storage module provides a flexible, extensible architecture for storing and retrieving rendered images.

## Architecture

The module follows the **Strategy Pattern** with an abstract base class and concrete implementations:

```
app/storage/
├── __init__.py          # Public API and global storage instance
├── base.py              # ImageStorageBase abstract class
└── file_storage.py      # FileStorage implementation
```

## Base Interface

`ImageStorageBase` defines the contract that all storage implementations must follow:

- `save_image(image_data: bytes, format: str) -> str` - Save image and return identifier
- `get_image(identifier: str) -> Optional[Tuple[bytes, str]]` - Retrieve image by identifier
- `delete_image(identifier: str) -> bool` - Delete image by identifier
- `list_images() -> List[str]` - List all stored identifiers
- `exists(identifier: str) -> bool` - Check if image exists

## Current Implementation

### FileStorage

Stores images as files in a configurable directory using GUID-based filenames.

**Features:**
- UUID v4 GUIDs for unique filenames
- Format-aware storage (filename includes extension)
- Directory-based organization
- Automatic directory creation
- GUID validation for security

**Configuration:**
```python
from app.storage import FileStorage

# Default: /tmp/gplot_images
storage = FileStorage()

# Custom directory
storage = FileStorage(storage_dir="/var/lib/gplot/images")
```

## Usage

### Basic Usage (Global Instance)

```python
from app.storage import get_storage

# Get the global storage instance (singleton)
storage = get_storage()

# Save an image
guid = storage.save_image(image_bytes, format="png")
print(f"Saved as: {guid}")

# Retrieve an image
result = storage.get_image(guid)
if result:
    image_data, format = result
    print(f"Retrieved {format} image, size: {len(image_data)}")

# Check if exists
if storage.exists(guid):
    print("Image exists")

# Delete an image
if storage.delete_image(guid):
    print("Image deleted")

# List all images
guids = storage.list_images()
print(f"Total images: {len(guids)}")
```

### Custom Storage Implementation

```python
from app.storage import set_storage, ImageStorageBase

# Create custom implementation
class S3Storage(ImageStorageBase):
    def __init__(self, bucket_name: str):
        self.bucket = bucket_name
    
    def save_image(self, image_data: bytes, format: str) -> str:
        # Upload to S3
        key = generate_key()
        upload_to_s3(self.bucket, key, image_data)
        return key
    
    def get_image(self, identifier: str) -> Optional[Tuple[bytes, str]]:
        # Download from S3
        data = download_from_s3(self.bucket, identifier)
        return (data, extract_format(identifier))
    
    # ... implement other methods

# Use custom storage
s3_storage = S3Storage("my-bucket")
set_storage(s3_storage)

# Now all code uses S3 storage
from app.storage import get_storage
storage = get_storage()  # Returns S3Storage instance
```

## Future Implementations

The modular design allows for easy addition of new storage backends:

- **S3Storage** - AWS S3 object storage
- **DatabaseStorage** - Store images in database (PostgreSQL, MongoDB)
- **RedisStorage** - In-memory cache with Redis
- **HybridStorage** - Multi-tier storage (cache + persistent)
- **EncryptedStorage** - Wrapper adding encryption
- **CompressedStorage** - Wrapper adding compression

## Integration

The storage module is used by:

- **Renderer** (`app/render.py`) - Saves images in proxy mode
- **MCP Server** (`app/mcp_server.py`) - Retrieves images via `get_image` tool
- **Web Server** (`app/web_server.py`) - Serves images via HTTP endpoints

All components use `get_storage()` for consistent access to the current storage implementation.

## Error Handling

All methods include comprehensive error handling and logging:

- Invalid identifiers raise `ValueError`
- Storage failures raise `RuntimeError`
- Not found returns `None` or `False` (no exceptions)
- All operations are logged with context

## Logging

Storage operations are logged with structured data:

```python
# Success
self.logger.info("Image saved to file", guid=guid, path=str(filepath))

# Errors
self.logger.error("Failed to save image file", guid=guid, error=str(e))

# Warnings
self.logger.warning("Image file not found", guid=identifier)
```

## Testing

Storage implementations should be tested for:

- Save/retrieve roundtrip
- Format preservation
- Identifier uniqueness
- Error handling
- Non-existent identifiers
- Invalid identifiers
- Concurrent access (if applicable)

Example test:
```python
def test_storage_roundtrip():
    storage = FileStorage("/tmp/test_storage")
    
    # Save
    image_data = b"fake image data"
    guid = storage.save_image(image_data, "png")
    
    # Retrieve
    result = storage.get_image(guid)
    assert result is not None
    retrieved_data, format = result
    assert retrieved_data == image_data
    assert format == "png"
    
    # Clean up
    storage.delete_image(guid)
```

## Thread Safety

The current `FileStorage` implementation is thread-safe for basic operations as the file system handles concurrent access. However, for high-concurrency scenarios, consider:

- File locking mechanisms
- Database-backed storage with ACID guarantees
- Distributed storage with coordination

## Best Practices

1. **Use `get_storage()`** - Always use the global instance for consistency
2. **Handle None returns** - Check if `get_image()` returns None
3. **Validate identifiers** - Let the storage validate, catch `ValueError`
4. **Log operations** - All storage implementations should log key events
5. **Clean up** - Delete old images to prevent storage bloat
6. **Test thoroughly** - Verify your implementation with comprehensive tests

## Migration Guide

To switch storage backends:

1. Implement `ImageStorageBase` interface
2. Call `set_storage()` with your implementation before any storage operations
3. Update configuration/environment variables as needed
4. Test thoroughly with existing code

Example migration to database storage:
```python
# Before app initialization
from app.storage import set_storage
from my_storage import DatabaseStorage

db_storage = DatabaseStorage(connection_string=os.getenv("DB_URL"))
set_storage(db_storage)

# All subsequent code uses database storage
```
