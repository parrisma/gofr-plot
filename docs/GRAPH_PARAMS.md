# Graph Parameters Module

The `graph_params` module defines the data structures for graph rendering requests.

## Location

```
app/graph_params/
├── __init__.py      # Module exports
└── params.py        # GraphParams class definition
```

## Purpose

Provides a strongly-typed Pydantic model for graph rendering parameters, ensuring:
- Type validation
- Data consistency
- Clear API contracts
- Automatic documentation generation

## GraphParams Class

The `GraphParams` class defines all parameters accepted by the graph rendering system.

### Basic Structure

```python
from app.graph_params import GraphParams

# Create graph parameters
params = GraphParams(
    x=[1, 2, 3, 4, 5],
    y=[2, 4, 6, 8, 10],
    type="line",
    format="png"
)
```

### Core Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `x` | `List[float]` | Yes | - | X-axis data points |
| `y` | `List[float]` | Yes | - | Y-axis data points |
| `type` | `str` | No | `"line"` | Chart type (line, bar, scatter) |
| `format` | `str` | No | `"png"` | Output format (png, svg, pdf, base64) |

### Optional Styling Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `title` | `str` | `None` | Chart title |
| `x_label` | `str` | `None` | X-axis label |
| `y_label` | `str` | `None` | Y-axis label |
| `color` | `str` | `"#1f77b4"` | Primary color (hex format) |
| `colors` | `List[str]` | `None` | Multiple colors for multi-series |
| `line_width` | `float` | `2.0` | Line thickness |
| `alpha` | `float` | `1.0` | Transparency (0.0-1.0) |
| `theme` | `str` | `"light"` | Theme name |

### Advanced Features

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `legend` | `List[str]` | `None` | Legend labels |
| `grid` | `bool` | `True` | Show grid lines |
| `figsize` | `Tuple[int, int]` | `(10, 6)` | Figure size in inches |
| `dpi` | `int` | `100` | Resolution in dots per inch |

### Proxy Mode

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `proxy` | `bool` | `False` | Enable proxy mode (storage) |
| `group` | `str` | `"default"` | Access control group |

## Usage Examples

### Simple Line Chart

```python
from app.graph_params import GraphParams

params = GraphParams(
    x=[1, 2, 3, 4],
    y=[1, 4, 2, 3],
    type="line",
    title="Simple Line Chart"
)
```

### Styled Bar Chart

```python
params = GraphParams(
    x=[1, 2, 3],
    y=[10, 20, 15],
    type="bar",
    color="#2ca02c",
    title="Sales Data",
    x_label="Quarter",
    y_label="Revenue ($K)",
    theme="dark"
)
```

### Multi-Color Scatter Plot

```python
params = GraphParams(
    x=[1, 2, 3, 4, 5],
    y=[2, 4, 6, 8, 10],
    type="scatter",
    colors=["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff"],
    alpha=0.7,
    title="Multi-Color Scatter"
)
```

### High-Resolution PDF Export

```python
params = GraphParams(
    x=[1, 2, 3],
    y=[5, 10, 15],
    type="line",
    format="pdf",
    dpi=300,
    figsize=(12, 8)
)
```

## Validation

The `GraphParams` class automatically validates:

1. **Array Lengths**: X and Y arrays must have same length
2. **Color Format**: Colors must be valid hex codes
3. **Alpha Range**: Alpha must be between 0.0 and 1.0
4. **Chart Type**: Must be one of: line, bar, scatter
5. **Format Type**: Must be one of: png, svg, pdf, base64
6. **Theme Name**: Must be a registered theme

### Example Validation Errors

```python
# Invalid - mismatched array lengths
params = GraphParams(
    x=[1, 2, 3],
    y=[1, 2]  # Error: length mismatch
)

# Invalid - bad color format
params = GraphParams(
    x=[1, 2],
    y=[1, 2],
    color="red"  # Error: must be hex format like "#ff0000"
)

# Invalid - alpha out of range
params = GraphParams(
    x=[1, 2],
    y=[1, 2],
    alpha=1.5  # Error: must be 0.0-1.0
)
```

## Integration

The `GraphParams` class is used throughout the rendering pipeline:

1. **Web Server** (`app/web_server.py`): Validates incoming REST API requests
2. **MCP Server** (`app/mcp_server.py`): Validates MCP tool parameters
3. **Renderers** (`app/render/`): Receives validated parameters
4. **Handlers** (`app/handlers/`): Processes specific chart types
5. **Validators** (`app/validation/`): Performs additional validation

## API Usage

### REST API

```bash
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{
    "x": [1, 2, 3],
    "y": [2, 4, 6],
    "type": "line",
    "format": "png"
  }'
```

### MCP Protocol

```json
{
  "tool": "render_graph",
  "arguments": {
    "x": [1, 2, 3],
    "y": [2, 4, 6],
    "type": "line",
    "format": "base64"
  }
}
```

### Python API

```python
from app.graph_params import GraphParams
from app.render import GraphRenderer

# Create parameters
params = GraphParams(x=[1, 2, 3], y=[2, 4, 6])

# Render graph
renderer = GraphRenderer()
result = renderer.render(params)
```

## Best Practices

1. **Use Type Hints**: Let your IDE/editor provide autocomplete
2. **Validate Early**: Create GraphParams at API boundary
3. **Immutable**: GraphParams is a Pydantic model (immutable after creation)
4. **Documentation**: Model fields are self-documenting

## See Also

- [Render Module](./RENDER.md) - Rendering engine
- [Themes](./THEMES.md) - Theme system
- [Handlers](./RENDER.md#handlers) - Chart type handlers
- [Validation](./RENDER.md#validation) - Validation system
