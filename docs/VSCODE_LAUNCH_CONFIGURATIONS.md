# VS Code Launch Configurations

This document describes the VS Code launch configurations defined in `.vscode/launch.json`.

## Server Launch Configurations

### Launch: Web Server (Port 8000)
- **Purpose**: Start the REST API web server
- **Module**: `app.main_web`
- **Port**: 8000
- **Use Case**: Debug or run the HTTP REST API for graph rendering

### Launch: MCP Server (Port 8001)
- **Purpose**: Start the Model Context Protocol server
- **Module**: `app.main_mcp`
- **Port**: 8001
- **Use Case**: Debug or run the MCP streamable HTTP server for protocol-based graph rendering

## Test Suite Configurations

### Test: All Tests (pytest)
- **Purpose**: Run complete test suite
- **Command**: `pytest test/ -v`
- **Use Case**: Verify all functionality before commits

### Test: Web Server Tests
- **Purpose**: Run only web server tests
- **Command**: `pytest test/web/ -v`
- **Coverage**: 
  - REST API endpoints
  - Request/response handling
  - Authentication
  - Graph rendering via HTTP

### Test: MCP Server Tests
- **Purpose**: Run only MCP server tests
- **Command**: `pytest test/mcp/ -v`
- **Coverage**:
  - MCP protocol implementation
  - Tool discovery and execution
  - Proxy mode
  - Authentication

### Test: Authentication Tests
- **Purpose**: Run only authentication tests
- **Command**: `pytest test/auth/ -v`
- **Coverage**:
  - JWT token creation/validation
  - Group-based access control
  - Token management

### Test: Current File
- **Purpose**: Run tests in currently open file
- **Command**: `pytest ${file} -v`
- **Use Case**: Quick iteration when developing tests

## Manual Test Scripts

### Manual: Web Server Test
- **Purpose**: Interactive web server testing
- **Script**: `test/web/manual_test_web_server.py`
- **Use Case**: Manual verification of web server functionality

### Manual: MCP Server Test
- **Purpose**: Interactive MCP server testing
- **Script**: `test/mcp/manual_test_mcp_server.py`
- **Use Case**: Manual verification of MCP protocol implementation

### Manual: MCP Discovery Test
- **Purpose**: Test MCP server discovery and tool listing
- **Script**: `test/mcp/manual_mcp_discovery.py`
- **Use Case**: Verify MCP tool discovery works correctly

## Utility Scripts

### Utility: Token Manager
- **Purpose**: Manage JWT tokens
- **Script**: `scripts/token_manager.py`
- **Default Args**: `list` (shows all tokens)
- **Use Case**: Create, list, verify, or revoke tokens
- **Available Commands**:
  - `list` - Show all tokens
  - `create <group>` - Create new token
  - `verify <token>` - Verify token validity
  - `revoke <token>` - Revoke a token

## Usage in VS Code

1. **Run/Debug Menu**: Press `F5` or click Run → Start Debugging
2. **Select Configuration**: Choose from the dropdown in the Run and Debug panel
3. **Quick Access**: Use `Ctrl+Shift+D` (Windows/Linux) or `Cmd+Shift+D` (Mac) to open Run and Debug panel

## Debugging Tips

- **Breakpoints**: Click in the gutter to the left of line numbers
- **Variables**: Inspect in the Variables pane during debug
- **Debug Console**: Execute Python expressions while paused
- **Call Stack**: View function call hierarchy

## Environment Variables

All configurations automatically set:
- `PYTHONPATH=${workspaceFolder}` - Ensures imports work correctly

Additional environment variables can be added to any configuration:
```json
"env": {
    "PYTHONPATH": "${workspaceFolder}",
    "GPLOT_DATA_DIR": "/custom/path",
    "GPLOT_JWT_SECRET": "your-secret"
}
```

## Customizing Arguments

To change server ports or other arguments, modify the `args` array:
```json
"args": [
    "--host", "127.0.0.1",
    "--port", "9000",
    "--jwt-secret", "my-secret"
]
```

## Running Without Debugging

To run without the debugger (faster):
1. Open Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P`)
2. Type "Run Without Debugging"
3. Select your configuration
