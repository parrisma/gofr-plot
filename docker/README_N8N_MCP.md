# N8N MCP Integration

## Overview

This document explains how N8N interacts with MCP (Model Context Protocol) servers and the limitations of the current setup.

## N8N MCP Capabilities

### 1. N8N as MCP Server (Supported)
N8N can act as an **MCP Server**, exposing n8n workflows and tools to external MCP clients.

**Transport:** SSE (Server-Sent Events) and streamable HTTP  
**Configuration:** Use the "MCP Server Trigger" node in n8n workflows  
**Access:** External clients can connect to n8n's MCP endpoints via HTTP

Example workflow:
1. Create a workflow with "MCP Server Trigger" node
2. Add n8n tool nodes (HTTP Request, Code, etc.)
3. Activate the workflow
4. External MCP clients can call these tools via SSE/HTTP

### 2. N8N as MCP Client (Limited Support)
N8N can act as an **MCP Client**, connecting to external MCP servers to use their tools.

**Important Limitation:** N8N's MCP Client Tool node **only supports SSE/HTTP transport**, NOT stdio transport.

This means:
- ✅ N8N can connect to SSE-based MCP servers (like n8n itself)
- ❌ N8N **cannot directly** connect to stdio-based MCP servers (like gplot)

## Connecting N8N to gplot MCP Server

The gplot MCP server now supports **SSE (Server-Sent Events) transport** on port 8001, making it compatible with N8N's MCP Client Tool!

### Option 1: Use N8N's MCP Client Tool (Recommended for MCP Protocol)
N8N can now connect directly to gplot's SSE MCP endpoint:

**Configuration:**
1. Add "MCP Client Tool" node to your n8n workflow
2. Configure the endpoint:
   - URL: `http://gplot_dev:8001/sse` (dev) or `http://gplot_prod:8001/sse` (prod)
   - Authentication: None (if running on gmcp_net network)
3. Use the `render_graph` or `ping` tools via MCP protocol

**Example MCP Tool Call:**
```json
{
  "tool": "render_graph",
  "arguments": {
    "x": [1, 2, 3, 4, 5],
    "y": [2, 4, 6, 8, 10],
    "title": "Sales Data",
    "type": "line",
    "theme": "dark"
  }
}
```

### Option 2: Use N8N's HTTP Request Node (Alternative)
Instead of using MCP protocol, call gplot's REST API directly:

```json
{
  "method": "POST",
  "url": "http://gplot_dev:8000/render",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "x": [1, 2, 3],
    "y": [4, 5, 6],
    "title": "My Graph"
  }
}
```

This is the **recommended approach** for the current setup.

### Option 3: Use mcp-remote Gateway (For External Clients)
External tools like Claude Desktop can use `mcp-remote` to bridge stdio MCP servers to SSE:

```json
{
  "mcpServers": {
    "gplot": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:8000/mcp",
        "--stdio"
      ]
    }
  }
}
```

However, this is for external clients connecting to n8n or other services, not for n8n itself.

### Current Setup

### Docker Network: gmcp_net
Both gplot and n8n containers run on the same Docker network:
- **gplot_dev/prod REST API:** Accessible at `http://gplot_dev:8000` or `http://gplot_prod:8000`
- **gplot_dev/prod MCP SSE:** Accessible at `http://gplot_dev:8001` or `http://gplot_prod:8001`
- **n8n:** Accessible at `http://n8n:5678`

### Communication Pattern
```
┌─────────────┐     MCP SSE (Port 8001)     ┌────────────┐
│   N8N       │ ────────────────────────►   │   gplot    │
│ Workflows   │     HTTP REST (Port 8000)   │  Service   │
│             │ ────────────────────────►   │            │
└─────────────┘                             └────────────┘
     │                                           │
     │                                           │
     └────────── gmcp_net Network ───────────────┘
```

### Recommended Usage in N8N

1. **Add HTTP Request Node** to your n8n workflow
2. **Configure:**
   - Method: POST
   - URL: `http://gplot_dev:8000/render` (dev) or `http://gplot_prod:8000/render` (prod)
   - Body: JSON with graph parameters

3. **Example Request:**
```json
{
  "x": [1, 2, 3, 4, 5],
  "y": [2, 4, 6, 8, 10],
  "title": "Sales Data",
  "type": "line",
  "format": "png",
  "theme": "dark"
}
```

4. **Handle Response:**
   - Success: Binary image data (base64 encoded)
   - Error: JSON with error message

## Environment Variables

None required for basic gplot + n8n communication via HTTP.

If you want n8n to act as an MCP Server (for external clients):
- Configure authentication in n8n's MCP Server Trigger node
- Expose n8n's port 5678 externally
- Configure reverse proxy with SSE support (disable buffering)

## Summary

- **N8N → gplot (MCP):** Use MCP Client Tool node to connect to `http://gplot_dev:8001/sse` ✅
- **N8N → gplot (REST):** Use HTTP Request node to call `http://gplot_dev:8000/render` ✅
- **N8N as MCP Server:** Supported via SSE (for exposing n8n workflows to external MCP clients) ✅
- **N8N as MCP Client:** Fully supported - gplot now uses SSE transport! ✅
- **gplot MCP Server:** Now accessible via SSE on port 8001, compatible with N8N's MCP Client Tool ✅

You can choose between:
1. **MCP Protocol (Port 8001):** Full MCP tool integration with standardized protocol
2. **HTTP REST API (Port 8000):** Simple HTTP endpoint for direct rendering requests

Both approaches work seamlessly within the gmcp_net Docker network.
