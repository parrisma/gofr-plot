# Graph Rendering MCP Server

This MCP (Model Context Protocol) server exposes graph rendering capabilities, allowing clients to generate line and bar charts.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running the MCP Server

The MCP server uses **Streamable HTTP** transport, which is the modern preferred standard for MCP servers (superseding SSE). It's fully compatible with N8N's MCP Client Tool and other modern MCP clients.

Start the server using:

```bash
python -m app.main_mcp
```

The server will start on:
- **Port 8001**: MCP Streamable HTTP endpoint at `http://localhost:8001/mcp`
- **Port 8000**: HTTP REST API at `http://localhost:8000/render` (via web_server.py)

Or run directly:

```bash
python app/main_mcp.py
```

## Available Tools

### `ping`

Health check tool that returns the current server timestamp.

**Parameters:** None

**Returns:**
- Server status and timestamp

### `render_graph`

Renders a graph (line, scatter, or bar chart) and returns it as a base64-encoded image or GUID (proxy mode).

**Parameters:**
- `title` (string, required): The title of the graph
- `x` (array of numbers, required): X-axis data points
- `y` (array of numbers, required): Y-axis data points
- `xlabel` (string, optional): Label for the X-axis (default: "X-axis")
- `ylabel` (string, optional): Label for the Y-axis (default: "Y-axis")
- `type` (string, optional): Graph type - "line", "scatter", or "bar" (default: "line")
- `format` (string, optional): Image format - "png", "bmp", "jpg", "svg", or "pdf" (default: "png")
- `proxy` (boolean, optional): If true, save image to disk and return GUID instead of base64 (default: false)

**Returns:**
- **Normal mode (proxy=false)**: Base64-encoded image and confirmation message
- **Proxy mode (proxy=true)**: GUID string and instructions for retrieval

**Proxy Mode:**

When `proxy=true`, the image is saved to disk with a unique GUID filename (e.g., `{guid}.png`), and the GUID is returned instead of the base64 data. This is useful for:
- Reducing network bandwidth with large images
- Persistent storage of rendered graphs
- Retrieving images later via GUID

### `get_image`

Retrieves a previously rendered image by its GUID (from proxy mode).

**Parameters:**
- `guid` (string, required): The GUID of the image to retrieve

**Returns:**
- Base64-encoded image data
- Success confirmation message

## Example Usage

### Normal Mode (Base64 Response)

```json
{
  "tool": "render_graph",
  "arguments": {
    "title": "Sales Over Time",
    "x": [1, 2, 3, 4, 5],
    "y": [10, 25, 20, 35, 30],
    "xlabel": "Month",
    "ylabel": "Sales ($1000s)",
    "type": "bar"
  }
}
```

Returns base64-encoded image data directly.

### Proxy Mode (GUID Response)

```json
{
  "tool": "render_graph",
  "arguments": {
    "title": "Sales Over Time",
    "x": [1, 2, 3, 4, 5],
    "y": [10, 25, 20, 35, 30],
    "type": "line",
    "format": "png",
    "proxy": true
  }
}
```

Returns:
```
Image saved with GUID: a1b2c3d4-e5f6-7890-1234-567890abcdef
Chart: line - 'Sales Over Time'
Format: png
Use get_image tool with guid='a1b2c3d4-e5f6-7890-1234-567890abcdef' to retrieve the image.
```

### Retrieving Proxy Mode Images

```json
{
  "tool": "get_image",
  "arguments": {
    "guid": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
  }
}
```

Returns the base64-encoded image data.

## Web Server Endpoints

The REST API (port 8000) provides additional ways to access rendered images:

### Render Graph
**POST** `/render`
- Body: GraphParams JSON (same parameters as `render_graph` tool)
- Returns: Base64 JSON or raw image bytes

### Get Image by GUID
**GET** `/render/{guid}`
- Returns: Raw image bytes with appropriate Content-Type
- Example: `http://localhost:8000/render/a1b2c3d4-e5f6-7890-1234-567890abcdef`

### View Image in Browser
**GET** `/render/{guid}/html`
- Returns: HTML page with embedded image
- Example: `http://localhost:8000/render/a1b2c3d4-e5f6-7890-1234-567890abcdef/html`
- Useful for viewing images directly in a web browser

### Health Check
**GET** `/ping`
- Returns: Server status and timestamp

## Configuration

To use this server with Claude Desktop or other MCP clients, add it to your MCP configuration file:

### Claude Desktop Configuration

Edit your Claude Desktop config file:
- MacOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

Add the server configuration:

```json
{
  "mcpServers": {
    "gplot-renderer": {
      "command": "python",
      "args": ["-m", "app.main_mcp"],
      "cwd": "/home/parris3142/devroot/gplot"
    }
  }
}
```

## Image Storage (Proxy Mode)

When using proxy mode (`proxy=true`), images are stored on disk:

- **Default Location**: `/tmp/gplot_images/`
- **Filename Format**: `{guid}.{format}` (e.g., `a1b2c3d4-e5f6-7890-1234-567890abcdef.png`)
- **Supported Formats**: png, bmp, jpg, svg, pdf
- **Persistence**: Files persist until manually deleted (in `/tmp` they may be cleared on reboot)

To configure a custom storage location, set the environment variable:
```bash
export GPLOT_STORAGE_DIR=/path/to/storage
python -m app.main_mcp
```

Or modify `app/storage.py` to change the default `storage_dir` parameter.

**Note**: For production use, consider using a persistent directory outside `/tmp`.

## Architecture

The MCP server uses:
- **Streamable HTTP Transport**: Modern HTTP-based MCP transport (superseding SSE)
- **StreamableHTTPSessionManager**: Manages MCP sessions with resumability support
- **Starlette**: ASGI web framework for HTTP endpoints
- **Uvicorn**: ASGI server for running the application
- `GraphRenderer` from `render.py` for matplotlib-based rendering
- `GraphParams` Pydantic model from `models.py` for data validation
- `ImageStorage` from `storage.py` for GUID-based persistent storage
- MCP protocol for standardized tool exposure

The server runs in Streamable HTTP mode on port 8001:
- **GET /mcp**: Establishes streaming connection for server-to-client messages
- **POST /mcp**: Receives client-to-server messages (can use SSE or JSON response)
- **DELETE /mcp**: Cleans up session resources

This Streamable HTTP transport is compatible with:
- ✅ N8N MCP Client Tool (preferred transport)
- ✅ Claude Desktop (via mcp-remote)
- ✅ Any HTTP-based MCP client
- ✅ Supports both stateful and stateless modes

## N8N Integration

To use this server with N8N:
1. Add an "MCP Client Tool" node to your workflow
2. Configure the endpoint: `http://gplot_dev:8001/mcp` (if running in Docker)
3. Call the `render_graph` or `ping` tools via MCP protocol

See [N8N MCP Integration Guide](./README_N8N_MCP.md) for detailed N8N integration instructions.
