# MCP Server Tests

This directory contains tests for the MCP (Model Context Protocol) server.

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
