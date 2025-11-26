# N8N Integration Guide

Complete guide for integrating gplot graph rendering with N8N workflow automation.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Method 1: MCP Protocol (Recommended)](#method-1-mcp-protocol-recommended)
4. [Method 2: HTTP REST API](#method-2-http-rest-api)
5. [Proxy Mode](#proxy-mode)
6. [Example Workflows](#example-workflows)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Configuration](#advanced-configuration)

---

## Quick Start

**Prerequisites:**
- gplot server running (MCP on port 8001, Web on port 8000)
- N8N instance running
- Valid JWT bearer token

**Your Bearer Token:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJncm91cCI6Im44biIsImlhdCI6MTc2Mjg4MTI1MSwiZXhwIjoxNzk0NDE3MjUxfQ.Zj2ZLtYmZ5jT579pSB_mHjVqUmhR1xQh6Hx4pqqp6ss
```
- **Group**: n8n
- **Expires**: November 11, 2026

---

## Architecture Overview

### Communication Pattern

```
┌─────────────┐  MCP Streamable HTTP (8001)  ┌────────────┐
│   N8N       │ ────────────────────────►    │   gplot    │
│ Workflows   │     HTTP REST (Port 8000)    │  Service   │
│             │ ────────────────────────►    │            │
└─────────────┘                              └────────────┘
     │                                            │
     │                                            │
     └────────── gplot_net Network ────────────────┘
```

### gplot MCP Capabilities

gplot uses **Streamable HTTP transport** (modern MCP standard) on port 8001, making it fully compatible with N8N's MCP Client Tool.

**Available MCP Tools:**
- ✅ `ping` - Health check endpoint
- ✅ `render_graph` - Generate charts with full parameter support
- ✅ `get_image` - Retrieve stored images by GUID
- ✅ `list_themes` - Discover available themes
- ✅ `list_handlers` - Discover supported chart types

### Docker Network

Both gplot and n8n containers run on the same Docker network (`gplot_net`):
- **gplot_dev REST API:** `http://gplot_dev:8000`
- **gplot_dev MCP Server:** `http://gplot_dev:8001/mcp`
- **gplot_prod REST API:** `http://gplot_prod:8000`
- **gplot_prod MCP Server:** `http://gplot_prod:8001/mcp`
- **n8n:** `http://n8n:5678`

---

## Method 1: MCP Protocol (Recommended)

N8N's MCP Client Tool can connect directly to gplot's Streamable HTTP MCP endpoint.

### Setup Steps

1. **Add MCP Client Node** to your N8N workflow
   - Search for "MCP Client Tool" or "MCP"
   - Add node to workflow

2. **Configure MCP Server Connection**
   - **URL**: `http://localhost:8001/mcp/` (or `http://gplot_dev:8001/mcp/` in Docker)
   - **Transport**: Streamable HTTP (automatic)
   - **Authentication**: Custom Headers (if supported) or pass token in arguments

3. **Test Connection**
   - MCP Client should discover available tools automatically
   - Use `ping` tool to verify connectivity

### Example 1: Simple Chart Generation

**Tool**: `render_graph`

**Arguments**:
```json
{
  "title": "Monthly Sales",
  "x": [1, 2, 3, 4, 5],
  "y": [1200, 1900, 1500, 2100, 1800],
  "type": "bar",
  "format": "png",
  "theme": "light",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response**: Binary image data (PNG) with MIME type `image/png`

### Example 2: Dynamic Data from Previous Node

**Arguments** (using N8N expressions):
```json
{
  "title": "{{ $json.chartTitle }}",
  "x": {{ $json.xData }},
  "y": {{ $json.yData }},
  "type": "{{ $json.chartType }}",
  "format": "png",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Example 3: Health Check

**Tool**: `ping`

**Arguments**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response**:
```
Server is running
Timestamp: 2025-11-26T14:30:00.123456
Service: gplot
```

---

## Method 2: HTTP REST API

Alternative approach using N8N's HTTP Request node to call gplot's REST API directly.

### Setup Steps

1. **Add HTTP Request Node** to your workflow

2. **Configure the node:**
   - **Method**: POST
   - **URL**: `http://localhost:8000/render` (or `http://gplot_dev:8000/render`)
   - **Authentication**: Generic Credential Type
   - **Header Auth**:
     - Name: `Authorization`
     - Value: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

3. **Body (JSON)**:
```json
{
  "title": "My Chart",
  "x": [1, 2, 3, 4, 5],
  "y": [10, 25, 15, 30, 20],
  "type": "bar",
  "format": "png",
  "theme": "light"
}
```

4. **Response Options**:
   - Response Format: JSON
   - Response contains `image_data` (base64 encoded) and `format`

### Dynamic Data Example

```json
{
  "title": "{{ $json.chartTitle }}",
  "x": {{ $json.xValues }},
  "y": {{ $json.yValues }},
  "type": "{{ $json.chartType }}",
  "format": "png"
}
```

---

## Proxy Mode

For workflows that need to save and retrieve charts later, use proxy mode.

### How Proxy Mode Works

1. **Generate with `proxy: true`** - Returns GUID instead of image
2. **Image saved to storage** - Persisted on server
3. **Retrieve later** - Use GUID to get image via MCP or REST

### Benefits

- ✅ Reduces network bandwidth (only GUID transferred initially)
- ✅ Persistent storage of rendered graphs
- ✅ Enables deferred retrieval
- ✅ Multiple access patterns (MCP, REST, browser)
- ✅ Ideal for large images or reusable charts

### MCP Proxy Example

**Step 1 - Generate and Save:**

**Tool**: `render_graph`

**Arguments**:
```json
{
  "title": "Report Chart",
  "x": [1, 2, 3, 4, 5],
  "y": [10, 25, 15, 30, 20],
  "type": "line",
  "format": "png",
  "proxy": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response**:
```json
{
  "guid": "550e8400-e29b-41d4-a716-446655440000",
  "format": "png"
}
```

**Step 2 - Retrieve Later:**

**Tool**: `get_image`

**Arguments**:
```json
{
  "guid": "550e8400-e29b-41d4-a716-446655440000",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response**: Binary image data

### REST Proxy Example

**Step 1 - Generate:**
```bash
POST http://localhost:8000/render
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

{
  "x": [1, 2, 3],
  "y": [10, 20, 30],
  "proxy": true
}
```

**Response**: `{"guid": "550e8400-...", "format": "png"}`

**Step 2 - Retrieve:**
```bash
GET http://localhost:8000/proxy/{guid}
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Step 3 - View in Browser:**
```
GET http://localhost:8000/proxy/{guid}/html
```

---

## Example Workflows

### Workflow 1: Simple Bar Chart

```
[Trigger] → [Set Data] → [HTTP Request (gplot)] → [Save to Storage]
```

### Workflow 2: Database → Chart → Email

```
[Schedule] → [MySQL Query] → [Function: Format Data] → [MCP: render_graph] → [Send Email]
```

**Function Node (Format Data)**:
```javascript
const rows = $input.all();
return {
  json: {
    chartTitle: "Daily Sales",
    xData: rows.map(r => r.day),
    yData: rows.map(r => r.sales),
    chartType: "bar"
  }
};
```

### Workflow 3: Multi-Chart Dashboard

```
[Trigger] → [Split Data] → [MCP: render_graph] × 3 → [Merge Images] → [Upload to Cloud]
```

### Workflow 4: API → Chart → Cloud Storage

```
[HTTP Request: Fetch API] → [MCP: render_graph (proxy)] → [Save GUID] → [Later: get_image] → [S3 Upload]
```

### Workflow 5: Webhook → Slack Notification

```
[Webhook] → [Split Into Batches] → [MCP: render_graph] → [Merge] → [Slack: Send Files]
```

---

## Chart Types

- `line` - Line chart with optional markers
- `bar` - Vertical bar chart  
- `scatter` - Scatter plot

## Themes

- `light` - Light background (default)
- `dark` - Dark background
- `bizlight` - Business light theme
- `bizdark` - Business dark theme

## Output Formats

- `png` - PNG image (default, recommended)
- `jpg` - JPEG image
- `svg` - SVG vector graphics (scalable)
- `pdf` - PDF document

---

## Advanced Configuration

### Custom Styling

```json
{
  "title": "Custom Styled Chart",
  "x": [1, 2, 3, 4, 5],
  "y": [10, 25, 15, 30, 20],
  "type": "line",
  "grid": true,
  "legend": true,
  "xlabel": "Time (hours)",
  "ylabel": "Temperature (°C)",
  "color": "#FF5733",
  "alpha": 0.8,
  "linewidth": 2,
  "marker": "o",
  "markersize": 8,
  "token": "..."
}
```

### Multi-Dataset Charts

Plot up to 5 datasets on a single chart:

```json
{
  "title": "Product Comparison",
  "x": [1, 2, 3, 4, 5],
  "y1": [10, 25, 18, 30, 42],
  "y2": [8, 22, 15, 28, 38],
  "y3": [12, 28, 20, 32, 45],
  "label1": "Product A",
  "label2": "Product B",
  "label3": "Product C",
  "color1": "red",
  "color2": "blue",
  "color3": "green",
  "type": "line"
}
```

### SVG for Scaling

Use SVG format for charts that need to scale without quality loss:

```json
{
  "format": "svg",
  "type": "line",
  ...
}
```

---

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to MCP server

**Solutions**:
- ✅ Verify gplot MCP server is running: `curl http://localhost:8001/mcp/ping`
- ✅ Check N8N can reach the server (same network if using Docker)
- ✅ Use correct URL with trailing slash: `http://localhost:8001/mcp/`

### Authentication Errors

**Problem**: 401 Unauthorized

**Solutions**:
- ✅ Include token in arguments: `"token": "eyJhbG..."`
- ✅ Verify token hasn't expired (check expiry date)
- ✅ Ensure Authorization header format: `Bearer <token>`
- ✅ Check JWT secret matches between servers

### Validation Errors

**Problem**: 422 Validation Error

**Solutions**:
- ✅ Ensure `x` and `y` are arrays of numbers (not strings)
- ✅ Check arrays are same length
- ✅ Verify `type` is one of: line, bar, scatter
- ✅ Validate numeric parameters (alpha: 0-1, linewidth > 0)
- ✅ Check data types in N8N expressions

### Tool Discovery Issues

**Problem**: MCP Client doesn't show gplot tools

**Solutions**:
- ✅ Test connection with ping first
- ✅ Refresh/reinitialize the MCP connection
- ✅ Check MCP server logs for errors
- ✅ Verify URL includes `/mcp/` path

### Empty or Corrupted Images

**Problem**: Image data is empty or invalid

**Solutions**:
- ✅ Check server logs for matplotlib errors
- ✅ Verify data arrays contain valid numbers (not NaN/Infinity)
- ✅ Try different format (png vs svg)
- ✅ Check base64 decoding if using REST API

For detailed troubleshooting, see **[N8N_TROUBLESHOOTING.md](./N8N_TROUBLESHOOTING.md)**

---

## Performance Tips

1. **Use Proxy Mode** for large images or repeated access
2. **SVG format** for charts that need scaling
3. **PNG format** for final output (best compatibility)
4. **Batch requests** when generating multiple charts
5. **Cache GUIDs** when using proxy mode
6. **Streamable HTTP** is faster than stdio for MCP

---

## Security Best Practices

1. **Store tokens securely** in N8N credentials/environment variables
2. **Use HTTPS** in production environments
3. **Rotate tokens** before expiry (current expires: Nov 11, 2026)
4. **Group isolation**: Each token's group can only access its own images
5. **Network isolation**: Run in private Docker network when possible
6. **Never log tokens** in workflow outputs

---

## Testing Your Setup

### Test MCP Connection

```bash
python -c "
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def test():
    async with streamablehttp_client('http://localhost:8001/mcp/') as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            tools = await session.list_tools()
            print('✓ MCP Server OK')
            print(f'  Tools: {[t.name for t in tools.tools]}')

asyncio.run(test())
"
```

**Expected Output**:
```
✓ MCP Server OK
  Tools: ['ping', 'render_graph', 'get_image', 'list_themes', 'list_handlers']
```

### Test REST API

```bash
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{"x": [1,2,3], "y": [4,5,6], "title": "Test"}' \
  -o test_chart.png
```

---

## See Also

- **[PROXY_MODE.md](./PROXY_MODE.md)** - GUID-based storage details
- **[AUTHENTICATION.md](./AUTHENTICATION.md)** - JWT authentication guide
- **[GRAPH_PARAMS.md](./GRAPH_PARAMS.md)** - Complete parameter reference
- **[THEMES.md](./THEMES.md)** - Theme customization
- **[MCP_README.md](./MCP_README.md)** - MCP protocol details
- **[N8N_TROUBLESHOOTING.md](./N8N_TROUBLESHOOTING.md)** - Detailed troubleshooting guide

---

## Getting Help

**Example Implementations**:
- `test/mcp/manual_test_mcp_server.py` - Python MCP client example
- `test/web/manual_test_web_server.py` - HTTP REST example

**Documentation**:
- Check the [main README](../README.md) for basic usage
- Review test files for working code examples
- See component-specific docs for detailed information
