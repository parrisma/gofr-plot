# Proxy Mode - GUID-Based Image Storage

## 🤖 Quick Guide for AI Assistants

When the MCP server responds to a proxy mode render request, **the response includes a complete download URL**:

```
Download URL: http://localhost:8000/proxy/{guid}
```

**Aliases:** If you set an `alias` parameter when rendering (e.g., `alias: "q4-sales"`), you can also access the image using:
```
http://localhost:8000/proxy/q4-sales
```

**What to do:**
1. ✅ Extract this URL from the response text
2. ✅ Provide it directly to the user
3. ✅ Tell them they can click it or paste it in a browser
4. ✅ Use aliases for memorable, reusable URLs
5. ❌ Don't say "I don't have access to the URL" - it's right there in the response!
6. ❌ Don't call `get_image` tool unless specifically needed for base64 data

**Example Response Pattern to Look For:**
```
Image saved with GUID: 0816aa30-13e9-4724-bffa-5679f4042b19
...
Download URL: http://localhost:8000/proxy/0816aa30-13e9-4724-bffa-5679f4042b19
```

The URL is immediately usable - no additional processing needed!

---

## Overview

Proxy mode allows rendered images to be saved to disk with a unique GUID identifier instead of returning large base64-encoded data directly. This is useful for:

- **Bandwidth Optimization**: Transfer only a GUID string instead of large base64 data
- **Persistent Storage**: Images remain accessible after rendering
- **Deferred Retrieval**: Retrieve images later via multiple access methods
- **Reusability**: Access the same image multiple times without re-rendering
- **Direct Browser Access**: Get a URL that can be opened directly in any web browser
- **Friendly Names**: Use aliases like "monthly-report" instead of GUIDs

## Image Aliases

Aliases provide human-friendly names for your stored images:

### Benefits
- **Memorable**: Use names like `q4-sales` instead of `a1b2c3d4-...`
- **Stable URLs**: Update an image while keeping the same alias
- **Group-Isolated**: Same alias can exist in different groups
- **Persistent**: Aliases survive server restarts

### Alias Rules
- Length: 3-64 characters
- Allowed: Letters, numbers, hyphens (`-`), underscores (`_`)
- Examples: `q4-sales`, `monthly_report`, `chart2024`

### Using Aliases

**When Rendering:**
```json
{
  "tool": "render_graph",
  "arguments": {
    "title": "Q4 Sales",
    "y1": [10, 20, 30],
    "proxy": true,
    "alias": "q4-sales",
    "token": "your-jwt-token"
  }
}
```

**When Retrieving:**
```json
{
  "tool": "get_image",
  "arguments": {
    "identifier": "q4-sales",
    "token": "your-jwt-token"
  }
}
```

**Via Web URL:**
```
http://localhost:8000/proxy/q4-sales
http://localhost:8000/proxy/q4-sales/html
```

## How It Works

1. **Render with Proxy Mode**: Call `render_graph` with `proxy=true`
2. **Get Response with URL**: Server saves image to disk and returns both a GUID and a complete download URL
3. **Access Image**: Use the provided URL directly in a browser, curl command, or any HTTP client

**Important for AI Assistants:** When the MCP server is running in URL mode (default), the proxy mode response includes a complete download URL in the format `http://localhost:8000/proxy/{guid}`. This URL can be provided directly to users who want to view or download the image. You do not need to use the `get_image` tool unless specifically working with base64 data.

## Usage

### 1. Render Image (Proxy Mode)

**MCP Tool (without alias):**
```json
{
  "tool": "render_graph",
  "arguments": {
    "title": "Sales Chart",
    "x": [1, 2, 3, 4, 5],
    "y": [10, 25, 15, 30, 20],
    "type": "line",
    "format": "png",
    "proxy": true,
    "token": "your-jwt-token"
  }
}
```

**MCP Tool (with alias):**
```json
{
  "tool": "render_graph",
  "arguments": {
    "title": "Sales Chart",
    "x": [1, 2, 3, 4, 5],
    "y": [10, 25, 15, 30, 20],
    "type": "line",
    "format": "png",
    "proxy": true,
    "alias": "sales-chart",
    "token": "your-jwt-token"
  }
}
```

**Response (with alias):**
```
Image saved with GUID: a1b2c3d4-e5f6-7890-1234-567890abcdef
Alias: sales-chart

Chart: line - 'Sales Chart'
Format: png

Download URL: http://localhost:8000/proxy/a1b2c3d4-e5f6-7890-1234-567890abcdef
Alias URL: http://localhost:8000/proxy/sales-chart
(Or use get_image tool with identifier='sales-chart')
```

**Response (URL mode - default):**
```
Image saved with GUID: a1b2c3d4-e5f6-7890-1234-567890abcdef

Chart: line - 'Sales Chart'
Format: png

Download URL: http://localhost:8000/proxy/a1b2c3d4-e5f6-7890-1234-567890abcdef
(Or use get_image tool with guid='a1b2c3d4-e5f6-7890-1234-567890abcdef')
```

**✨ AI Assistant Note:** The "Download URL" is the complete, ready-to-use URL that can be:
- Opened directly in a web browser
- Used with curl/wget to download the image
- Shared with users for immediate access
- Embedded in HTML or markdown

No additional tools or processing required!

**Response (GUID mode):**
```
Image saved with GUID: a1b2c3d4-e5f6-7890-1234-567890abcdef

Chart: line - 'Sales Chart'
Format: png

Use get_image tool with guid='a1b2c3d4-e5f6-7890-1234-567890abcdef' to retrieve the image.
```

### 2. Retrieve Image

#### Option A: Direct HTTP GET (Recommended - Works Immediately)

The server provides a complete download URL in the proxy mode response. Just use it!

**Using GUID:**
```bash
curl http://localhost:8000/proxy/a1b2c3d4-e5f6-7890-1234-567890abcdef -o chart.png
```

**Using Alias:**
```bash
curl http://localhost:8000/proxy/sales-chart -o chart.png
```

**For Web Browsers:**
```
http://localhost:8000/proxy/sales-chart
http://localhost:8000/proxy/a1b2c3d4-e5f6-7890-1234-567890abcdef
```

Click or paste this URL directly into any browser address bar to view or download the image.

#### Option B: MCP `get_image` Tool (Only if you need base64 data)
```json
{
  "tool": "get_image",
  "arguments": {
    "identifier": "sales-chart",
    "token": "your-jwt-token"
  }
}
```

The `identifier` can be either a GUID or an alias. Returns base64-encoded image data.

#### Option C: MCP `list_images` Tool (Discover stored images)
```json
{
  "tool": "list_images",
  "arguments": {
    "token": "your-jwt-token"
  }
}
```

Returns a list of all images in your group with their GUIDs and aliases.

#### Option D: Web Browser (HTML View)
```
http://localhost:8000/proxy/a1b2c3d4-e5f6-7890-1234-567890abcdef/html
```

Opens an HTML page with the embedded image for viewing in a browser.

## Configuration

### Proxy URL Mode

Control how the MCP server returns proxy mode responses:

**URL Mode (default - Recommended for AI Assistants):** Returns complete download URL
```bash
python -m app.main_mcp --proxy-url-mode url --web-url http://localhost:8000
```

With URL mode enabled (default), AI assistants and automated tools can immediately provide users with working download links without needing to construct URLs or use additional tools.

**GUID Mode:** Returns only GUID (client constructs URL manually)
```bash
python -m app.main_mcp --proxy-url-mode guid
```

Use this mode only if you prefer to construct URLs programmatically or have custom URL routing.

### Web Server Base URL

Set the base URL for proxy downloads:

**CLI Argument:**
```bash
python -m app.main_mcp --web-url http://localhost:8000
```

**Environment Variable:**
```bash
export GPLOT_WEB_URL=http://localhost:8000
python -m app.main_mcp
```

**Priority:** CLI `--web-url` > env `GPLOT_WEB_URL` > default `http://localhost:8000`

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
- **Parameter**: `alias` (optional): Human-friendly name (3-64 chars)
- **Returns**: Text with GUID, alias (if set), and retrieval instructions
- **Storage**: Image saved to `{storage_dir}/{guid}.{format}`

#### `get_image`
- **Parameter**: `identifier` (string, required) - GUID or alias
- **Parameter**: `token` (string, required) - JWT authentication
- **Returns**: ImageContent with base64 data
- **Error**: 404 if identifier not found

#### `list_images`
- **Parameter**: `token` (string, required) - JWT authentication
- **Returns**: List of GUIDs with aliases for your group
- **Purpose**: Discover stored images

### Web Endpoints

#### `GET /proxy/{identifier}`
- **identifier**: GUID or registered alias
- **Returns**: Raw image bytes
- **Content-Type**: `image/png`, `image/bmp`, etc.
- **Headers**: `Content-Disposition: inline; filename="{guid}.{format}"`

#### `GET /proxy/{identifier}/html`
- **identifier**: GUID or registered alias
- **Returns**: HTML page with embedded image
- **Features**:
  - Responsive image display
  - Download button
  - GUID/alias and format information
  - File size display

#### `POST /render` (with proxy)
- **Body**: GraphParams JSON with `proxy: true`
- **Returns**: JSON with GUID and URLs
```json
{
  "guid": "...",
  "format": "png",
  "message": "Image saved with GUID: ...",
  "retrieve_url": "/proxy/{guid}",
  "html_url": "/proxy/{guid}/html"
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
[HTTP Request: GET /proxy/{guid}]
  - Download raw image
  - OR visit /proxy/{guid}/html in browser
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
curl http://localhost:8000/proxy/{guid} -o chart.png

# Open in browser
xdg-open http://localhost:8000/proxy/{guid}/html
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
