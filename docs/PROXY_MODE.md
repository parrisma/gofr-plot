# Proxy Mode - GUID-Based Image Storage

## Overview

Proxy mode allows rendered images to be saved to disk with a unique GUID identifier instead of returning large base64-encoded data directly. This is useful for:

- **Bandwidth Optimization**: Transfer only a GUID string instead of large base64 data
- **Persistent Storage**: Images remain accessible after rendering
- **Deferred Retrieval**: Retrieve images later via multiple access methods
- **Reusability**: Access the same image multiple times without re-rendering

## How It Works

1. **Render with Proxy Mode**: Call `render_graph` with `proxy=true`
2. **Get GUID**: Server saves image to disk and returns a GUID
3. **Retrieve Image**: Use the GUID to access the image via MCP tool or web endpoint

## Usage

### 1. Render Image (Proxy Mode)

**MCP Tool:**
```json
{
  "tool": "render_graph",
  "arguments": {
    "title": "Sales Chart",
    "x": [1, 2, 3, 4, 5],
    "y": [10, 25, 15, 30, 20],
    "type": "line",
    "format": "png",
    "proxy": true
  }
}
```

**Response:**
```
Image saved with GUID: a1b2c3d4-e5f6-7890-1234-567890abcdef
Chart: line - 'Sales Chart'
Format: png
Use get_image tool with guid='a1b2c3d4-e5f6-7890-1234-567890abcdef' to retrieve the image.
```

### 2. Retrieve Image

#### Option A: MCP `get_image` Tool
```json
{
  "tool": "get_image",
  "arguments": {
    "guid": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
  }
}
```

Returns base64-encoded image data.

#### Option B: Web API (Raw Image)
```bash
curl http://localhost:8000/render/a1b2c3d4-e5f6-7890-1234-567890abcdef -o chart.png
```

#### Option C: Web Browser (HTML View)
```
http://localhost:8000/render/a1b2c3d4-e5f6-7890-1234-567890abcdef/html
```

Opens an HTML page with the embedded image for viewing in a browser.

## Storage Location

- **Default Path**: `/tmp/gplot_images/`
- **Filename Format**: `{guid}.{format}`
- **Example**: `a1b2c3d4-e5f6-7890-1234-567890abcdef.png`

### Custom Storage Directory

Set environment variable before starting the server:

```bash
export GPLOT_STORAGE_DIR=/path/to/custom/storage
python -m app.main_mcp
```

Or modify `app/storage.py` to change the default.

## Supported Formats

All standard image formats are supported in proxy mode:
- `png` (default)
- `bmp`
- `jpg` / `jpeg`
- `svg`
- `pdf`

## API Reference

### MCP Tools

#### `render_graph` (with proxy)
- **Parameter**: `proxy: true`
- **Returns**: Text with GUID and retrieval instructions
- **Storage**: Image saved to `{storage_dir}/{guid}.{format}`

#### `get_image`
- **Parameter**: `guid` (string, required)
- **Returns**: ImageContent with base64 data
- **Error**: 404 if GUID not found

### Web Endpoints

#### `GET /render/{guid}`
- **Returns**: Raw image bytes
- **Content-Type**: `image/png`, `image/bmp`, etc.
- **Headers**: `Content-Disposition: inline; filename="{guid}.{format}"`

#### `GET /render/{guid}/html`
- **Returns**: HTML page with embedded image
- **Features**:
  - Responsive image display
  - Download button
  - GUID and format information
  - File size display

#### `POST /render` (with proxy)
- **Body**: GraphParams JSON with `proxy: true`
- **Returns**: JSON with GUID and URLs
```json
{
  "guid": "...",
  "format": "png",
  "message": "Image saved with GUID: ...",
  "retrieve_url": "/render/{guid}",
  "html_url": "/render/{guid}/html"
}
```

## N8N Integration

### Workflow: Render → Save → Retrieve

```
[Manual Trigger]
    ↓
[MCP Client Tool: render_graph]
  - proxy: true
  - Returns GUID
    ↓
[Extract GUID from response]
    ↓
[HTTP Request: GET /render/{guid}]
  - Download raw image
  - OR visit /render/{guid}/html in browser
```

### Code Node: Extract GUID

```javascript
const response = $json.output;
const guidMatch = response.match(/GUID: ([a-f0-9-]+)/i);
const guid = guidMatch ? guidMatch[1] : null;

return { json: { guid } };
```

## Performance Considerations

### When to Use Proxy Mode

**Use Proxy Mode When:**
- Images are large (>1MB base64 encoded)
- Images need to be accessed multiple times
- Multiple clients need the same image
- Bandwidth is limited
- Storage persistence is required

**Use Normal Mode When:**
- Images are small (<100KB)
- Single-use disposable images
- Immediate consumption required
- No persistence needed

### Storage Management

Images in `/tmp` may be automatically cleared on system reboot. For production:

1. Use persistent directory:
   ```bash
   export GPLOT_STORAGE_DIR=/var/lib/gplot/images
   ```

2. Implement cleanup policy:
   - Delete old images periodically
   - Set up cron job for cleanup
   - Monitor disk usage

## Testing

Run the proxy mode test suite:

```bash
# Start MCP server first
python -m app.main_mcp

# In another terminal
python test/mcp/test_proxy_mode.py
```

Tests verify:
- ✅ Render with proxy returns GUID
- ✅ GUID format is valid UUID
- ✅ Image can be retrieved by GUID
- ✅ Invalid GUID returns error
- ✅ Multiple formats (PNG, BMP) work
- ✅ Web endpoints accessible

## Examples

### Python Client

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def render_and_retrieve():
    url = "http://localhost:8001/mcp/"
    
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Render with proxy
            result = await session.call_tool("render_graph", {
                "title": "Test",
                "x": [1, 2, 3],
                "y": [4, 5, 6],
                "proxy": True
            })
            
            # Extract GUID
            guid = extract_guid(result.content[0].text)
            
            # Retrieve image
            image_result = await session.call_tool("get_image", {
                "guid": guid
            })
            
            # Use base64 image data
            base64_data = image_result.content[0].data
```

### curl Examples

```bash
# Render with proxy
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sales",
    "x": [1,2,3,4,5],
    "y": [10,20,15,25,20],
    "proxy": true
  }'

# Response: {"guid": "...", "format": "png", ...}

# Download image
curl http://localhost:8000/render/{guid} -o chart.png

# View in browser
xdg-open http://localhost:8000/render/{guid}/html
```

## Troubleshooting

### Image Not Found
- Verify GUID is correct (UUID format)
- Check if file exists: `ls /tmp/gplot_images/{guid}.*`
- Ensure server has write permissions to storage directory

### Storage Full
- Check disk space: `df -h /tmp`
- Clean old images: `rm /tmp/gplot_images/*.png`
- Move to larger volume

### Permission Denied
```bash
# Fix permissions
chmod 755 /tmp/gplot_images
chmod 644 /tmp/gplot_images/*
```

## Security Considerations

1. **GUID Exposure**: GUIDs are not secret - anyone with the GUID can access the image
2. **No Authentication**: Web endpoints are unauthenticated
3. **Storage Limits**: Implement quotas to prevent disk exhaustion
4. **Input Validation**: GUIDs are validated as UUIDs to prevent path traversal

For production deployments:
- Add authentication to web endpoints
- Implement access control lists
- Set up storage quotas and monitoring
- Use HTTPS for transport security
