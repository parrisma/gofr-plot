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
- `y1` (array of numbers, required): First dataset Y-axis data points (or use `y` for backward compatibility)
- `x` (array of numbers, optional): X-axis data points (defaults to [0, 1, 2, ...])
- `y2`, `y3`, `y4`, `y5` (arrays of numbers, optional): Additional datasets (up to 5 total)
- `label1`, `label2`, `label3`, `label4`, `label5` (strings, optional): Legend labels for each dataset
- `color1`, `color2`, `color3`, `color4`, `color5` (strings, optional): Colors for each dataset
- `xlabel` (string, optional): Label for the X-axis (default: "X-axis")
- `ylabel` (string, optional): Label for the Y-axis (default: "Y-axis")
- `type` (string, optional): Graph type - "line", "scatter", or "bar" (default: "line")
- `format` (string, optional): Image format - "png", "jpg", "svg", or "pdf" (default: "png")
- `proxy` (boolean, optional): If true, save image to disk and return GUID instead of base64 (default: false)
- `alias` (string, optional): Human-friendly name for the image (only used with proxy=true). Must be 3-64 characters, alphanumeric with hyphens/underscores. Example: "q4-sales-chart"
- `token` (string, required): JWT authentication token

**Axis Control Parameters (optional):**
- `xmin` (number, optional): Minimum value for X-axis
- `xmax` (number, optional): Maximum value for X-axis
- `ymin` (number, optional): Minimum value for Y-axis
- `ymax` (number, optional): Maximum value for Y-axis
- `x_major_ticks` (array of numbers, optional): Custom positions for major ticks on X-axis
- `y_major_ticks` (array of numbers, optional): Custom positions for major ticks on Y-axis
- `x_minor_ticks` (array of numbers, optional): Custom positions for minor ticks on X-axis
- `y_minor_ticks` (array of numbers, optional): Custom positions for minor ticks on Y-axis

**Returns:**
- **Normal mode (proxy=false)**: Base64-encoded image and confirmation message
- **Proxy mode (proxy=true)**: GUID string and instructions for retrieval

**Proxy Mode:**

When `proxy=true`, the image is saved to disk with a unique GUID filename (e.g., `{guid}.png`), and the GUID is returned instead of the base64 data. This is useful for:
- Reducing network bandwidth with large images
- Persistent storage of rendered graphs
- Retrieving images later via GUID

### `get_image`

Retrieves a previously rendered image by its GUID or alias (from proxy mode).

**Parameters:**
- `identifier` (string, required): The GUID or alias of the image to retrieve
- `token` (string, required): JWT authentication token

**Returns:**
- Base64-encoded image data
- Success confirmation message

### `list_images`

Discovers all stored images accessible to your token's group.

**Parameters:**
- `token` (string, required): JWT authentication token

**Returns:**
- List of stored images with GUIDs and aliases
- Total count of images in your group
- Usage instructions

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

### With Multiple Datasets

```json
{
  "tool": "render_graph",
  "arguments": {
    "title": "Temperature Comparison",
    "x": [1, 2, 3, 4, 5, 6],
    "y1": [20, 25, 22, 28, 24, 30],
    "y2": [18, 23, 20, 26, 22, 28],
    "y3": [22, 27, 24, 30, 26, 32],
    "label1": "City A",
    "label2": "City B",
    "label3": "City C",
    "color1": "red",
    "color2": "blue",
    "color3": "green",
    "xlabel": "Hour",
    "ylabel": "Temperature (°C)",
    "type": "line"
  }
}
```

This example plots three temperature datasets with labels and colors.

### With Axis Controls

```json
{
  "tool": "render_graph",
  "arguments": {
    "title": "Temperature Data",
    "x": [1, 2, 3, 4, 5, 6],
    "y1": [20, 25, 22, 28, 24, 30],
    "xlabel": "Hour",
    "ylabel": "Temperature (°C)",
    "type": "line",
    "xmin": 0,
    "xmax": 7,
    "ymin": 15,
    "ymax": 35,
    "x_major_ticks": [0, 2, 4, 6],
    "y_major_ticks": [15, 20, 25, 30, 35]
  }
}
```

This example:
- Sets X-axis range from 0 to 7
- Sets Y-axis range from 15 to 35
- Defines custom major tick positions on both axes
- Returns base64-encoded image with the specified axis controls

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
    "proxy": true,
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
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

### Proxy Mode with Alias

```json
{
  "tool": "render_graph",
  "arguments": {
    "title": "Q4 Sales Report",
    "x": [1, 2, 3, 4, 5],
    "y": [10, 25, 20, 35, 30],
    "type": "bar",
    "proxy": true,
    "alias": "q4-sales-report",
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

Returns:
```
Image saved with GUID: a1b2c3d4-e5f6-7890-1234-567890abcdef
Alias: q4-sales-report
Chart: bar - 'Q4 Sales Report'
Format: png
Use get_image with identifier='q4-sales-report' or guid to retrieve.
```

You can then retrieve the image using either:
- `get_image` with `identifier: "q4-sales-report"` (alias)
- `get_image` with `identifier: "a1b2c3d4-e5f6-7890-1234-567890abcdef"` (GUID)

### Retrieving Proxy Mode Images

Using GUID:
```json
{
  "tool": "get_image",
  "arguments": {
    "identifier": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

Using Alias:
```json
{
  "tool": "get_image",
  "arguments": {
    "identifier": "q4-sales-report",
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

Both return the base64-encoded image data.

### Listing Your Images

```json
{
  "tool": "list_images",
  "arguments": {
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

Returns:
```
Stored Images in group 'your-group' (3 total):

• a1b2c3d4-e5f6-7890-1234-567890abcdef (alias: q4-sales-report)
• b2c3d4e5-f6a7-8901-2345-678901bcdef0
• c3d4e5f6-a7b8-9012-3456-789012cdef01 (alias: monthly-chart)

Use get_image with a GUID or alias to retrieve an image.
```

## Web Server Endpoints

The REST API (port 8000) provides additional ways to access rendered images:

### Render Graph
**POST** `/render`
- Body: GraphParams JSON (same parameters as `render_graph` tool)
- Returns: Base64 JSON or raw image bytes

### Get Image by GUID or Alias
**GET** `/proxy/{identifier}`
- `identifier`: Either a GUID or registered alias
- Returns: Raw image bytes with appropriate Content-Type
- Examples:
  - `http://localhost:8000/proxy/a1b2c3d4-e5f6-7890-1234-567890abcdef`
  - `http://localhost:8000/proxy/q4-sales-report`

### View Image in Browser
**GET** `/proxy/{identifier}/html`
- Returns: HTML page with embedded image
- Examples:
  - `http://localhost:8000/proxy/a1b2c3d4-e5f6-7890-1234-567890abcdef/html`
  - `http://localhost:8000/proxy/q4-sales-report/html`
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

## Additional Documentation

- **[Multi-Dataset Support](./MULTI_DATASET.md)**: Plot up to 5 datasets on a single graph with examples
- **[Axis Controls Guide](./AXIS_CONTROLS.md)**: Detailed documentation on axis limits and tick controls with examples
- **[Proxy Mode Guide](./PROXY_MODE.md)**: In-depth guide on using proxy mode for persistent image storage
- **[Image Aliases](./ALIAS.md)**: Human-friendly names for stored images
- **[Authentication Guide](./AUTHENTICATION.md)**: JWT authentication setup and configuration
- **[Themes Guide](./THEMES.md)**: Available themes and customization options
