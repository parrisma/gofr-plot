# Graph Rendering MCP Server

This MCP (Model Context Protocol) server exposes graph rendering capabilities, allowing clients to generate line and bar charts.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running the MCP Server

The MCP server uses **SSE (Server-Sent Events)** transport, which is the preferred standard for MCP servers and is compatible with N8N's MCP Client Tool.

Start the server using:

```bash
python -m app.mcp_server
```

The server will start on:
- **Port 8001**: MCP SSE endpoint at `http://localhost:8001/sse`
- **Port 8000**: HTTP REST API at `http://localhost:8000/render` (via web_server.py)

Or make it executable and run directly:

```bash
chmod +x app/mcp_server.py
./app/mcp_server.py
```

## Available Tools

### `render_graph`

Renders a graph (line or bar chart) and returns it as a base64-encoded PNG image.

**Parameters:**
- `title` (string, required): The title of the graph
- `x` (array of numbers, required): X-axis data points
- `y` (array of numbers, required): Y-axis data points
- `xlabel` (string, optional): Label for the X-axis (default: "X-axis")
- `ylabel` (string, optional): Label for the Y-axis (default: "Y-axis")
- `style` (string, optional): Graph style - "line" or "bar" (default: "line")

**Returns:**
- A base64-encoded PNG image of the rendered graph
- A text confirmation message

## Example Usage

When integrated with an MCP client, you can call the tool like this:

```json
{
  "tool": "render_graph",
  "arguments": {
    "title": "Sales Over Time",
    "x": [1, 2, 3, 4, 5],
    "y": [10, 25, 20, 35, 30],
    "xlabel": "Month",
    "ylabel": "Sales ($1000s)",
    "style": "bar"
  }
}
```

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
      "args": ["-m", "app.mcp_server"],
      "cwd": "/home/parris3142/devroot/gplot"
    }
  }
}
```

## Architecture

The MCP server uses:
- **SSE (Server-Sent Events) Transport**: Modern HTTP-based MCP transport
- **Starlette**: ASGI web framework for SSE endpoints
- **Uvicorn**: ASGI server for running the application
- `GraphRenderer` from `render.py` for matplotlib-based rendering
- `GraphData` Pydantic model from `models.py` for data validation
- MCP protocol for standardized tool exposure

The server runs in SSE mode on port 8001:
- **GET /sse**: Establishes SSE connection for server-to-client messages
- **POST /messages/**: Receives client-to-server messages with session ID

This SSE transport is compatible with:
- ✅ N8N MCP Client Tool
- ✅ Claude Desktop (via mcp-remote)
- ✅ Any HTTP/SSE-based MCP client

## N8N Integration

To use this server with N8N:
1. Add an "MCP Client Tool" node to your workflow
2. Configure the endpoint: `http://gplot_dev:8001/sse` (if running in Docker)
3. Call the `render_graph` or `ping` tools via MCP protocol

See `docker/README_N8N_MCP.md` for detailed N8N integration instructions.
