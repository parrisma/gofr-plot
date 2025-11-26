# Image Alias System

The alias system provides human-friendly names for stored images, making it easier to reference charts without memorizing GUIDs.

## Overview

Instead of using GUIDs like `a1b2c3d4-e5f6-7890-1234-567890abcdef`, you can use memorable aliases like `q4-sales-report` or `monthly-chart`.

### Key Features

- **Human-Readable**: Use meaningful names instead of UUIDs
- **Group-Isolated**: Same alias can exist in different authentication groups
- **Persistent**: Aliases survive server restarts (stored in metadata)
- **Bi-directional**: Look up GUID from alias, or alias from GUID
- **Optional**: Aliases are optional; GUIDs always work

## Alias Rules

| Rule | Requirement |
|------|-------------|
| Length | 3-64 characters |
| Allowed | Letters (a-z, A-Z), numbers (0-9), hyphens (-), underscores (_) |
| Case | Case-sensitive (`Report` ≠ `report`) |
| Uniqueness | Must be unique within a group |

### Valid Examples
- `q4-sales`
- `monthly_report`
- `chart-2024-01`
- `ProjectAlpha_v2`

### Invalid Examples
- `ab` (too short)
- `my chart` (spaces not allowed)
- `report@2024` (@ not allowed)

## Using Aliases

### 1. Render with Alias (MCP)

```json
{
  "tool": "render_graph",
  "arguments": {
    "title": "Q4 Sales Report",
    "y1": [100, 150, 200, 250],
    "type": "bar",
    "proxy": true,
    "alias": "q4-sales",
    "token": "your-jwt-token"
  }
}
```

**Response:**
```
Image saved with GUID: a1b2c3d4-e5f6-7890-1234-567890abcdef
Alias: q4-sales

Chart: bar - 'Q4 Sales Report'
Format: png

Download URL: http://localhost:8000/proxy/a1b2c3d4-e5f6-7890-1234-567890abcdef
Alias URL: http://localhost:8000/proxy/q4-sales
```

### 2. Retrieve by Alias (MCP)

```json
{
  "tool": "get_image",
  "arguments": {
    "identifier": "q4-sales",
    "token": "your-jwt-token"
  }
}
```

### 3. Retrieve by Alias (Web)

```bash
# Direct download
curl http://localhost:8000/proxy/q4-sales -o chart.png

# View in browser
open http://localhost:8000/proxy/q4-sales/html
```

### 4. List Images with Aliases

```json
{
  "tool": "list_images",
  "arguments": {
    "token": "your-jwt-token"
  }
}
```

**Response:**
```
Stored Images in group 'analytics' (3 total):

• a1b2c3d4-e5f6-7890-1234-567890abcdef (alias: q4-sales)
• b2c3d4e5-f6a7-8901-2345-678901bcdef0
• c3d4e5f6-a7b8-9012-3456-789012cdef01 (alias: monthly-report)

Use get_image with a GUID or alias to retrieve an image.
```

## Web API Endpoints

All proxy endpoints accept either GUID or alias as the identifier:

| Endpoint | Description |
|----------|-------------|
| `GET /proxy/{identifier}` | Download raw image |
| `GET /proxy/{identifier}/html` | View in HTML wrapper |

**Examples:**
```bash
# Using GUID
curl http://localhost:8000/proxy/a1b2c3d4-e5f6-7890-1234-567890abcdef

# Using Alias
curl http://localhost:8000/proxy/q4-sales
```

## Storage API

### Register Alias

```python
from app.storage import get_storage

storage = get_storage()

# Save image first
guid = storage.save_image(image_data, "png", group="analytics")

# Register alias
storage.register_alias("q4-sales", guid, "analytics")
```

### Resolve Identifier

```python
# Works with both alias and GUID
guid = storage.resolve_identifier("q4-sales", group="analytics")
# Returns: "a1b2c3d4-e5f6-7890-1234-567890abcdef"

guid = storage.resolve_identifier("a1b2c3d4-e5f6-...", group="analytics")
# Returns: "a1b2c3d4-e5f6-7890-1234-567890abcdef"

guid = storage.resolve_identifier("nonexistent", group="analytics")
# Returns: None
```

### Get Alias for GUID

```python
alias = storage.get_alias("a1b2c3d4-e5f6-7890-1234-567890abcdef")
# Returns: "q4-sales" or None
```

### List Aliases

```python
aliases = storage.list_aliases("analytics")
# Returns: {"q4-sales": "a1b2c3d4-...", "monthly-report": "c3d4e5f6-..."}
```

### Unregister Alias

```python
success = storage.unregister_alias("q4-sales", "analytics")
# Returns: True if removed, False if not found
```

## Group Isolation

Aliases are scoped to authentication groups:

```python
# Group A can use alias "report"
storage.register_alias("report", guid_a, "group-a")

# Group B can also use alias "report" (different GUID)
storage.register_alias("report", guid_b, "group-b")

# Resolve uses group context
storage.resolve_identifier("report", group="group-a")  # Returns guid_a
storage.resolve_identifier("report", group="group-b")  # Returns guid_b
```

## Error Handling

### Duplicate Alias

```python
try:
    storage.register_alias("existing-alias", new_guid, "group")
except ValueError as e:
    print(e)  # "Alias 'existing-alias' already exists in group..."
```

### Invalid Format

```python
try:
    storage.register_alias("ab", guid, "group")  # Too short
except ValueError as e:
    print(e)  # "Invalid alias format: 'ab'. Must be 3-64 characters..."
```

### Not Found

```python
guid = storage.resolve_identifier("nonexistent", group="group")
if guid is None:
    print("Identifier not found")
```

## Best Practices

1. **Use Descriptive Names**: `q4-sales-2024` is better than `chart1`
2. **Be Consistent**: Use a naming convention (e.g., `{project}-{type}-{date}`)
3. **Avoid Conflicts**: Check `list_aliases()` before registering
4. **Group Context**: Always provide the correct group for resolution
5. **Handle None**: Always check if `resolve_identifier()` returns None

## Implementation Details

### Storage Structure

Aliases are stored in the metadata JSON alongside image data:

```json
{
  "a1b2c3d4-e5f6-7890-1234-567890abcdef": {
    "format": "png",
    "size": 12345,
    "created_at": "2024-01-15T10:30:00",
    "group": "analytics",
    "alias": "q4-sales"
  }
}
```

### In-Memory Maps

For fast lookup, two in-memory maps are maintained:

```python
# Group → Alias → GUID
_alias_to_guid = {
    "analytics": {"q4-sales": "a1b2c3d4-...", "monthly-report": "c3d4e5f6-..."},
    "marketing": {"campaign-results": "d4e5f6a7-..."}
}

# GUID → Alias
_guid_to_alias = {
    "a1b2c3d4-...": "q4-sales",
    "c3d4e5f6-...": "monthly-report",
    "d4e5f6a7-...": "campaign-results"
}
```

Maps are rebuilt from metadata on storage initialization.

## Troubleshooting

### Alias Not Found

1. Verify the alias exists: `list_aliases(group)`
2. Check the group context matches
3. Ensure alias wasn't unregistered

### Duplicate Alias Error

1. Use a different alias name
2. Or unregister the existing alias first
3. Or update the existing image instead

### Invalid Alias Format

1. Check length (3-64 characters)
2. Remove special characters
3. Use only letters, numbers, hyphens, underscores

## See Also

- [Proxy Mode Guide](./PROXY_MODE.md) - Using proxy mode with aliases
- [Storage Module](./STORAGE.md) - Storage API reference
- [Authentication Guide](./AUTHENTICATION.md) - Group-based access control
- [MCP README](./MCP_README.md) - MCP tool reference
