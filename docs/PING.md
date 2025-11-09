# Ping Endpoint Documentation

## Overview
The ping endpoint provides a simple health check to verify that the gplot server is running and responsive.

## Web Server (REST API)

### Endpoint
```
GET /ping
```

### Response
Returns a JSON object with server status and current timestamp:

```json
{
  "status": "ok",
  "timestamp": "2025-11-09T21:25:07.543000",
  "service": "gplot"
}
```

### Example Usage
```bash
curl http://localhost:8000/ping
```

## MCP Server

### Tool Name
```
ping
```

### Parameters
None required (empty object)

### Response
Returns a text message with server status and timestamp:

```
Server is running
Timestamp: 2025-11-09T21:25:14.073000
Service: gplot
```

### Example Usage
```python
from mcp import ClientSession

result = await session.call_tool("ping", arguments={})
print(result.content[0].text)
```

## Use Cases

1. **Health Monitoring**: Verify the server is running and responsive
2. **Connectivity Testing**: Confirm network connection to the server
3. **Uptime Checks**: Regular polling to monitor service availability
4. **Integration Testing**: Quick validation before running complex operations

## Testing

Run ping-specific tests:
```bash
# Web server ping test
python test/web/test_ping.py

# MCP server ping test
python test/mcp/test_ping.py
```
