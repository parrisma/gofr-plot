# Graph Rendering MCP Server

This MCP (Model Context Protocol) server exposes graph rendering capabilities, allowing clients to generate line and bar charts.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running the MCP Server

Start the server using:

```bash
python -m app.mcp_server
```

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
- `GraphRenderer` from `render.py` for matplotlib-based rendering
- `GraphData` Pydantic model from `models.py` for data validation
- MCP protocol for standardized tool exposure

The server runs in stdio mode, communicating via standard input/output streams with the MCP client.
