# MCP Server Tests

This directory contains tests for the MCP (Model Context Protocol) server functionality.

## Running Tests

**Note:** All MCP tests require JWT authentication.

### Prerequisites

1. **Start the MCP server with the test JWT secret:**
   ```bash
   python3 -m app.main_mcp --port 8001 --jwt-secret "test-secret-key-for-auth-testing"
   ```

2. **Run pytest:**
   ```bash
   pytest test/mcp/ -v
   ```

The tests will automatically create and manage authentication tokens using the same secret.

## Test Files

- `test_ping.py` - Tests the ping tool (pytest)
- `test_mcp_rendering.py` - Tests chart rendering and validation (pytest)
- `test_proxy_mode.py` - Tests proxy mode and image retrieval (pytest)
- `manual_test_mcp_server.py` - Manual test script (not pytest)
- `manual_mcp_discovery.py` - Manual tool discovery script (not pytest)

## Running the tests

Make sure you have the environment set up:

```bash
# From the project root
uv sync
```

Then run the test script:

```bash
python test/mcp/test_mcp_server.py
```

## What it tests

- MCP server initialization
- Tool listing
- Graph rendering (line and bar charts)
- Error handling

The test communicates with the MCP server via stdio and verifies that:
1. The server starts correctly
2. Tools are properly registered
3. The render_graph tool works for different chart types
4. Errors are handled gracefully
