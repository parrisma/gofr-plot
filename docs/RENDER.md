# Render Module

The render module provides graph rendering capabilities with support for multiple chart types, output formats, themes, and storage backends.

## Architecture

```
app/render/
├── __init__.py          # Public API
└── renderer.py          # GraphRenderer implementation
```

## GraphRenderer Class

The `GraphRenderer` class is the main entry point for graph rendering. It coordinates the entire rendering pipeline:

1. **Handler Selection** - Delegates to appropriate chart handler (line, scatter, bar)
2. **Theme Application** - Applies visual theme to the chart
3. **Data Plotting** - Renders the actual data points
4. **Output Generation** - Produces image in requested format
5. **Storage** - Optionally saves to storage (proxy mode)

## Usage

### Basic Rendering

```python
from app.render import GraphRenderer
from app.graph_params import GraphParams

renderer = GraphRenderer()

data = GraphParams(
    title="Sales Data",
    x=[1, 2, 3, 4, 5],
    y=[10, 25, 18, 30, 42],
    type="line",
    format="png",
    return_base64=True
)

# Returns base64-encoded PNG
base64_image = renderer.render(data)
```

### Proxy Mode

```python
data = GraphParams(
    title="Sales Data",
    x=[1, 2, 3, 4, 5],
    y=[10, 25, 18, 30, 42],
    type="line",
    format="png",
    proxy=True  # Enable proxy mode
)

# Returns GUID instead of image data
guid = renderer.render(data)
print(f"Image saved as: {guid}")
```

### Different Output Formats

```python
# PNG (default)
data = GraphParams(..., format="png")

# SVG (scalable vector)
data = GraphParams(..., format="svg")

# PDF (document)
data = GraphParams(..., format="pdf")

# JPG (compressed)
data = GraphParams(..., format="jpg")
```

### Different Chart Types

```python
# Line chart
data = GraphParams(..., type="line")

# Scatter plot
data = GraphParams(..., type="scatter", marker_size=50)

# Bar chart
data = GraphParams(..., type="bar")
```

### Themes

```python
# Light theme (default)
data = GraphParams(..., theme="light")

# Dark theme
data = GraphParams(..., theme="dark")
```

### Custom Styling

```python
data = GraphParams(
    title="Styled Chart",
    x=[1, 2, 3, 4, 5],
    y=[10, 25, 18, 30, 42],
    type="line",
    color="#FF5733",       # Custom color
    line_width=3.0,        # Thicker line
    alpha=0.8,             # Semi-transparent
    xlabel="Time (days)",  # Custom labels
    ylabel="Value ($)"
)
```

## Return Values

The `render()` method returns different types based on configuration:

- **Base64 string** - When `return_base64=True` (default for MCP)
- **Raw bytes** - When `return_base64=False` (for direct HTTP responses)
- **GUID string** - When `proxy=True` (for storage-based retrieval)

## Error Handling

The renderer provides comprehensive error handling:

```python
try:
    result = renderer.render(data)
except ValueError as e:
    # Configuration errors (invalid type, theme, format)
    print(f"Invalid configuration: {e}")
except RuntimeError as e:
    # Rendering errors (plotting failed, buffer errors, etc.)
    print(f"Rendering failed: {e}")
```

Common errors:
- `ValueError` - Invalid chart type, theme, or format
- `RuntimeError` - Matplotlib errors, buffer failures, storage errors

## Logging

The renderer logs all operations with structured data:

```python
# Success
self.logger.info("Render completed successfully", 
    chart_type=data.type, 
    format=data.format,
    output_size_bytes=image_size)

# Errors
self.logger.error("Failed to plot data", 
    error=str(e), 
    handler=type(handler).__name__)
```

Log levels:
- **DEBUG** - Internal steps (handler selection, theme loading, cleanup)
- **INFO** - Key events (render start, render complete)
- **WARNING** - Recoverable issues (theme color fallback)
- **ERROR** - Failures that prevent rendering

## Dependencies

The renderer integrates with:

- **Handlers** (`app.handlers`) - Chart-type-specific rendering
- **Themes** (`app.themes`) - Visual styling
- **Storage** (`app.storage`) - Proxy mode file storage
- **Models** (`app.models`) - GraphParams input model
- **matplotlib** - Core plotting library

## Handler System

The renderer delegates to specific handlers based on chart type:

```python
self.handlers = {
    "line": LineGraphHandler(),
    "scatter": ScatterGraphHandler(),
    "bar": BarGraphHandler(),
}
```

Handlers implement the `GraphHandler` interface with a `plot(ax, data)` method.

## Theme System

Themes are applied before plotting:

```python
theme = get_theme(data.theme)
theme.apply(fig, ax)
```

The renderer uses the theme's default color if no color is specified.

## Storage Integration

In proxy mode, rendered images are saved to storage:

```python
if data.proxy:
    storage = get_storage()
    guid = storage.save_image(image_data, data.format)
    return guid
```

This allows retrieval via the `get_image` tool or web endpoint.

## Resource Management

The renderer ensures proper cleanup:

```python
finally:
    # Close matplotlib figure
    if fig is not None:
        plt.close(fig)
    
    # Close buffer
    if buf is not None:
        buf.close()
```

This prevents memory leaks when rendering many charts.

## Performance Considerations

- **Figure Creation** - Each render creates a new matplotlib figure
- **Memory** - Figures are closed after rendering to free memory
- **Buffer Size** - Image data held in memory during encoding
- **Storage I/O** - Proxy mode writes to disk synchronously

For high-throughput scenarios, consider:
- Reusing renderer instances (handlers are reusable)
- Monitoring memory usage
- Using async storage backends
- Caching frequently-rendered charts

## Testing

Test the renderer with different configurations:

```python
def test_renderer():
    renderer = GraphRenderer()
    
    # Test each chart type
    for chart_type in ["line", "scatter", "bar"]:
        data = GraphParams(
            title=f"Test {chart_type}",
            x=[1, 2, 3],
            y=[4, 5, 6],
            type=chart_type
        )
        result = renderer.render(data)
        assert isinstance(result, str)  # base64
    
    # Test proxy mode
    data = GraphParams(
        title="Proxy Test",
        x=[1, 2, 3],
        y=[4, 5, 6],
        proxy=True
    )
    guid = renderer.render(data)
    assert len(guid) == 36  # UUID length
```

## Integration

The renderer is used by:

- **MCP Server** (`app.mcp_server`) - `render_graph` tool
- **Web Server** (`app.web_server`) - POST `/render` endpoint
- **Tests** - All rendering tests

All components import via:
```python
from app.render import GraphRenderer
```

## Future Enhancements

Potential improvements:

- **Async Rendering** - Non-blocking for high concurrency
- **Render Queue** - Background processing with job queue
- **Caching** - Cache rendered images for identical inputs
- **Streaming** - Stream large images instead of loading into memory
- **Custom Handlers** - Plugin system for new chart types
- **Batch Rendering** - Render multiple charts in one call
- **Animation** - Support for animated GIFs or videos

## Best Practices

1. **Reuse renderer instances** - Create once, use many times
2. **Handle errors gracefully** - Catch ValueError and RuntimeError
3. **Log appropriately** - Use structured logging for debugging
4. **Clean up** - The renderer handles cleanup automatically
5. **Validate input** - Use GraphDataValidator before rendering
6. **Choose format wisely** - PNG for web, SVG for print, PDF for documents
