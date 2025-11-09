# gplot - Graph Rendering Service

A powerful graph rendering service with both REST API and Model Context Protocol (MCP) server support. Built with FastAPI and matplotlib, gplot provides flexible chart generation with theme support.

## Features

- **Multiple Chart Types**: Line charts, scatter plots, and bar charts
- **Dual Interface**: 
  - REST API via FastAPI for web integration
  - MCP Server for AI assistant integration
- **Theme Support**: Built-in light and dark themes with extensible architecture
- **Flexible Output**: PNG, JPG, SVG, and PDF formats
- **Customizable Styling**: Colors, line widths, transparency, and more
- **Session Logging**: Built-in logger with session tracking for debugging

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd gplot

# Install dependencies
uv sync

# Or manually install required packages
uv pip install matplotlib fastapi uvicorn httpx mcp pydantic
```

### Running the Web Server

```bash
# Start the FastAPI server
python app/main.py

# Server will be available at http://localhost:8000
# API documentation at http://localhost:8000/docs
```

### Running the MCP Server

```bash
# Start the MCP server
python app/mcp_server.py
```

## Usage Examples

### REST API

**Generate a line chart:**
```bash
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sales Data",
    "x": [1, 2, 3, 4, 5],
    "y": [10, 25, 18, 30, 42],
    "xlabel": "Month",
    "ylabel": "Sales",
    "type": "line",
    "theme": "dark",
    "return_base64": false
  }' -o chart.png
```

**Generate a scatter plot with custom styling:**
```bash
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Data Points",
    "x": [1, 2, 3, 4, 5],
    "y": [2, 5, 3, 8, 6],
    "type": "scatter",
    "color": "#FF5733",
    "marker_size": 100,
    "alpha": 0.7,
    "format": "svg",
    "return_base64": false
  }' -o scatter.svg
```

### MCP Server

The MCP server exposes the `render_graph` tool for use with AI assistants and other MCP clients.

## Project Structure

```
gplot/
├── app/
│   ├── main.py              # FastAPI web server entry point
│   ├── mcp_server.py        # MCP server entry point
│   ├── models.py            # Pydantic data models
│   ├── render.py            # Main renderer class
│   ├── web_server.py        # FastAPI routes and handlers
│   ├── handlers/            # Chart type handlers
│   │   ├── base.py          # Abstract handler interface
│   │   ├── line.py          # Line chart handler
│   │   ├── scatter.py       # Scatter plot handler
│   │   └── bar.py           # Bar chart handler
│   ├── themes/              # Theme system
│   │   ├── base.py          # Abstract theme interface
│   │   ├── light.py         # Light theme
│   │   ├── dark.py          # Dark theme
│   │   └── README.md        # Theme documentation
│   └── logger/              # Logging system
│       ├── interface.py     # Logger interface
│       ├── default_logger.py
│       ├── console_logger.py
│       └── README.md        # Logging documentation
├── test/
│   ├── mcp/                 # MCP server tests
│   │   ├── test_mcp_server.py
│   │   └── README.md
│   └── web/                 # Web server tests
│       ├── test_web_server.py
│       └── README.md
├── docker/                  # Docker configuration
│   ├── Dockerfile.dev
│   ├── Dockerfile.prod
│   └── README.md
├── .devcontainer/           # VS Code dev container config
├── .vscode/                 # VS Code settings
├── pyproject.toml           # Project dependencies
├── MCP_README.md            # MCP-specific documentation
└── README.md                # This file
```

## Documentation

- **[MCP Server Documentation](./MCP_README.md)** - Model Context Protocol integration details
- **[Logger Module](./app/logger/README.md)** - Custom logging system documentation
- **[Docker Setup](./docker/README.md)** - Container configuration and deployment
- **[MCP Tests](./test/mcp/README.md)** - MCP server testing guide
- **[Web Tests](./test/web/README.md)** - Web server testing guide

## Chart Types

### Line Charts
```json
{
  "type": "line",
  "line_width": 2.0,
  "color": "#1f77b4"
}
```

### Scatter Plots
```json
{
  "type": "scatter",
  "marker_size": 36.0,
  "color": "red"
}
```

### Bar Charts
```json
{
  "type": "bar",
  "color": "green",
  "alpha": 0.8
}
```

## Themes

gplot includes two built-in themes:

- **Light**: Clean, bright colors on white background (default)
- **Dark**: Muted colors on dark background for reduced eye strain

Specify theme in your request:
```json
{
  "theme": "dark"
}
```

Users can also create and register custom themes. See the [Logger Module documentation](./app/logger/README.md) for details.

## Output Formats

Supported output formats:
- **PNG** (default) - Raster image format
- **JPG** - Compressed raster format
- **SVG** - Vector format, scalable
- **PDF** - Document format

## API Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | string | required | Chart title |
| `x` | float[] | required | X-axis data points |
| `y` | float[] | required | Y-axis data points |
| `xlabel` | string | "X-axis" | X-axis label |
| `ylabel` | string | "Y-axis" | Y-axis label |
| `type` | string | "line" | Chart type: line, scatter, bar |
| `theme` | string | "light" | Theme: light, dark |
| `format` | string | "png" | Output format: png, jpg, svg, pdf |
| `return_base64` | boolean | true | Return base64 or binary image |
| `color` | string | null | Custom color (hex, name, or rgb) |
| `line_width` | float | 2.0 | Line width for line charts |
| `marker_size` | float | 36.0 | Marker size for scatter plots |
| `alpha` | float | 1.0 | Transparency (0.0 to 1.0) |

## Development

### Running Tests

```bash
# Run MCP server tests
python test/mcp/test_mcp_server.py

# Run web server tests
python test/web/test_web_server.py

# Or use VS Code launch configurations (F5)
```

### VS Code Integration

The project includes VS Code launch configurations for:
- Running the web server
- Running the MCP server
- Running MCP tests
- Running web server tests

Press `F5` and select the desired configuration.

### Adding New Chart Types

1. Create a new handler in `app/handlers/` extending `GraphHandler`
2. Implement the `plot()` method
3. Register the handler in `GraphRenderer.__init__()`

Example:
```python
from app.handlers.base import GraphHandler

class HistogramHandler(GraphHandler):
    def plot(self, ax: "Axes", data: "GraphData") -> None:
        ax.hist(data.y, bins=10)
```

### Adding Custom Themes

1. Create a new theme in `app/themes/` extending `Theme`
2. Implement required methods
3. Register using `register_theme()`

See [Logger Module documentation](./app/logger/README.md) for examples.

## License

MIT License - See [LICENSE](./LICENSE) file for details

## Contributing

Contributions are welcome! Please ensure:
- Code follows existing style patterns
- New features include tests
- Documentation is updated
- All tests pass

## Architecture

gplot uses a modular architecture:

- **Handlers**: Each chart type has its own handler class
- **Themes**: Pluggable theme system for consistent styling
- **Logger**: Flexible logging with session tracking
- **Dual Interface**: Both REST and MCP protocol support

This design allows easy extension and customization while maintaining clean separation of concerns.
