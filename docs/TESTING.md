# Testing Guide

This document describes the testing infrastructure, workflow, and conventions for the gplot project.

## Overview

gplot maintains a comprehensive test suite covering:
- Authentication and authorization
- MCP server functionality
- Web API endpoints
- Storage operations and concurrency
- Graph rendering and validation
- Multi-dataset support

**Current Status**: 210 tests passing in ~9.7 seconds

## Test Runner

### Quick Start

```bash
# Run tests without starting servers (unit/validation tests only)
./scripts/run_tests.sh --no-servers

# Run full integration tests with servers
./scripts/run_tests.sh --with-servers

# Run specific test file
./scripts/run_tests.sh --no-servers test/auth/test_authentication.py
```

### How It Works

The `run_tests.sh` script:

1. **Sets up environment variables** for consistent configuration
2. **Manages server lifecycle** (when using `--with-servers`)
3. **Cleans up resources** before and after test runs
4. **Provides colored output** for easy status tracking

### Environment Variables

The test runner automatically configures:

| Variable | Default | Purpose |
|----------|---------|---------|
| `GPLOT_JWT_SECRET` | `test-secret-key-for...` | JWT token signing secret |
| `GPLOT_TOKEN_STORE` | `/tmp/gplot_test_tokens.json` | Shared token store path |
| `GPLOT_MCP_PORT` | `8001` | MCP server port |
| `GPLOT_WEB_PORT` | `8000` | Web server port |

## Test Organization

```
test/
├── conftest.py              # Shared pytest fixtures
├── auth/                    # Authentication & authorization tests (60+ tests)
│   ├── test_authentication.py
│   ├── test_auth_config.py
│   ├── test_dependency_injection.py
│   └── test_token_store_reload.py
├── mcp/                     # MCP server tests (81 tests)
│   ├── test_mcp_rendering.py        # Chart rendering via MCP protocol
│   ├── test_mcp_handlers.py         # Chart type handlers
│   ├── test_mcp_themes.py           # Theme application
│   ├── test_mcp_multi_dataset.py    # Multi-dataset support
│   ├── test_mcp_proxy_mode.py       # GUID storage/retrieval
│   └── manual_*.py                  # Manual test scripts (excluded from pytest)
├── storage/                 # Storage layer tests (40+ tests)
│   ├── test_concurrent_access.py
│   ├── test_metadata_corruption.py
│   ├── test_storage_failures.py
│   └── test_storage_purge.py
├── validation/              # Validation and rendering tests (50+ tests)
│   ├── test_multi_dataset.py
│   ├── test_axis_controls.py
│   └── test_extreme_values.py
└── web/                     # Web API tests (170+ tests)
    ├── test_web_rendering.py        # Basic chart rendering
    ├── test_web_multi_dataset.py    # Multi-dataset via REST
    ├── test_web_proxy_mode.py       # Proxy endpoints
    └── manual_*.py                  # Manual test scripts (excluded)
```

### MCP Server Tests (81 tests)

The MCP test suite covers Model Context Protocol functionality:

**Test Categories:**
- **Tool Discovery**: Verify `list_tools()` returns all available tools
- **Rendering**: Test `render_graph` tool with all chart types
- **Proxy Mode**: Test GUID generation and `get_image` retrieval
- **Themes**: Verify theme application (light, dark, bizlight, bizdark)
- **Multi-Dataset**: Test plotting up to 5 datasets simultaneously
- **Validation**: Error handling for invalid parameters
- **Authentication**: JWT token validation and group isolation

**Key Test Files:**
- `test_mcp_rendering.py` - Core rendering functionality
- `test_mcp_handlers.py` - Chart type handlers (line, bar, scatter)
- `test_mcp_themes.py` - Theme application
- `test_mcp_multi_dataset.py` - Multi-dataset rendering
- `test_mcp_proxy_mode.py` - GUID storage and retrieval

**Running MCP Tests:**
```bash
# Without servers (unit tests only)
./scripts/run_tests.sh --no-servers test/mcp/

# With MCP server (full integration)
./scripts/run_tests.sh --with-servers test/mcp/
```

**Manual Testing:**
```bash
# Start MCP server
python app/main_mcp.py --port 8001 --jwt-secret "test-secret"

# Run manual test script
python test/mcp/manual_test_mcp_server.py
```

### Web Server Tests (170+ tests)

The Web test suite covers FastAPI REST API functionality:

**Test Categories:**
- **Rendering**: POST `/render` endpoint with all parameters
- **Formats**: PNG, JPG, SVG, PDF output formats
- **Themes**: Light, dark, bizlight, bizdark themes
- **Multi-Dataset**: Up to 5 datasets per chart
- **Proxy Mode**: POST with `proxy=true`, GET `/proxy/{guid}`
- **Validation**: 422 errors for invalid parameters
- **Authentication**: JWT Bearer token validation
- **Health Check**: GET `/ping` endpoint

**Key Test Files:**
- `test_web_rendering.py` - Basic rendering (13 tests)
  - Line charts with base64
  - Bar charts with direct image
  - Scatter plots
  - Dark/Light themes
  - SVG/PDF formats
  - Custom styling
- `test_web_multi_dataset.py` - Multi-dataset support (45 tests)
- `test_web_proxy_mode.py` - Proxy endpoints
- `test_ping.py` - Health check (4 tests)

**Running Web Tests:**
```bash
# Without servers (unit tests only)
./scripts/run_tests.sh --no-servers test/web/

# With Web server (full integration)
./scripts/run_tests.sh --with-servers test/web/
```

**Manual Testing:**
```bash
# Start web server
python app/main_web.py --port 8000 --jwt-secret "test-secret"

# Test with curl
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"x": [1,2,3], "y": [4,5,6], "title": "Test"}'
```

**Note:** Web tests use FastAPI's TestClient with dependency override to bypass JWT authentication for unit testing, allowing focus on rendering functionality without token management.

## Test Fixtures

### Session-Scoped Fixtures (conftest.py)

```python
@pytest.fixture(scope="session")
def test_auth_service():
    """Shared authentication service for all tests"""
    
@pytest.fixture(scope="session")
def test_token():
    """Valid JWT token for testing"""
    
@pytest.fixture(scope="session")
def invalid_token():
    """Invalid token for auth failure tests"""
```

### Function-Scoped Fixtures

```python
@pytest.fixture
def temp_storage_dir(tmp_path):
    """Isolated storage directory per test"""
    
@pytest.fixture
def logger():
    """Test logger instance"""
```

## Running Specific Tests

### By File

```bash
./scripts/run_tests.sh --no-servers test/auth/test_authentication.py
```

### By Class

```bash
pytest test/auth/test_authentication.py::TestMCPAuthentication
```

### By Test Name

```bash
pytest test/auth/test_authentication.py::TestMCPAuthentication::test_mcp_render_with_valid_token
```

### By Marker

```bash
pytest -m asyncio  # Run all async tests
```

## Test Modes

### Unit/Validation Tests (`--no-servers`)

- Fastest execution (~6 seconds)
- No external server dependencies
- Covers validation logic, storage, and auth service
- Ideal for TDD and quick feedback

### Integration Tests (`--with-servers`)

- Complete end-to-end testing (~10 seconds)
- Starts MCP and Web servers automatically
- Tests full request/response cycles
- Validates authentication, rendering, storage

## pytest Configuration

Settings in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["."]
addopts = "--strict-markers --ignore=test/mcp/manual_test_mcp_server.py --ignore=test/mcp/manual_mcp_discovery.py --ignore=test/web/manual_test_web_server.py"
filterwarnings = [
    "ignore::RuntimeWarning:matplotlib",
]
```

**Key settings:**
- `--strict-markers`: Enforces declared markers, catches typos
- `--ignore`: Excludes manual test scripts from discovery
- `asyncio_mode = "auto"`: Automatic async test detection

## Zero-Skip Policy

Tests should not use `pytest.skip()` for missing dependencies or server availability. Instead:

1. **Use test modes**: Run unit tests with `--no-servers`, integration tests with `--with-servers`
2. **Use fixtures**: Make dependencies explicit via pytest fixtures
3. **Use markers**: Tag tests appropriately (`@pytest.mark.asyncio`, etc.)

## Writing New Tests

### Authentication Required

```python
@pytest.mark.asyncio
async def test_authenticated_endpoint(test_auth_service, test_token):
    """Test that requires authentication"""
    auth_service = test_auth_service
    token = test_token
    
    # Your test logic here
```

### Storage Required

```python
def test_storage_operation(temp_storage_dir, logger):
    """Test requiring isolated storage"""
    storage = FileStorage(base_dir=temp_storage_dir, logger=logger)
    
    # Your test logic here
```

### MCP/Web Server Required

```python
@pytest.mark.asyncio
async def test_mcp_endpoint(test_token):
    """Test requiring running MCP server"""
    # Run with: ./scripts/run_tests.sh --with-servers
    
    async with httpx.AsyncClient() as client:
        response = await client.post(...)
```

## Common Test Patterns

### Testing Authentication

```python
# Valid token
response = await client.post(url, headers={"Authorization": f"Bearer {test_token}"})
assert response.status_code == 200

# Missing token
response = await client.post(url)
assert response.status_code == 401

# Invalid token
response = await client.post(url, headers={"Authorization": f"Bearer {invalid_token}"})
assert response.status_code == 401
```

### Testing Group Security

```python
# Create resource in group1
token1 = auth_service.create_token(group="group1")
guid = create_resource(token=token1)

# Try to access from group2 (should fail)
token2 = auth_service.create_token(group="group2")
response = await client.get(f"/proxy/{guid}", headers={"Authorization": f"Bearer {token2}"})
assert response.status_code == 403  # Forbidden
```

### Testing Storage Concurrency

```python
async def test_concurrent_operations():
    tasks = [
        save_data(storage, f"data_{i}")
        for i in range(10)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    assert all(not isinstance(r, Exception) for r in results)
```

## Debugging Failed Tests

### View Full Output

```bash
pytest -v -s test/path/to/test.py
```

### Run with Debugging

```python
import pdb; pdb.set_trace()  # Add breakpoint
```

Or use VS Code's debugging:
- Set breakpoint in test
- Run "Python: Debug Tests" from command palette

### Check Server Logs

When using `--with-servers`, logs are saved to:
- `/tmp/gplot_mcp_test.log`
- `/tmp/gplot_web_test.log`

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run tests
  run: |
    ./scripts/run_tests.sh --with-servers
```

### Docker

```bash
docker run gplot ./scripts/run_tests.sh --with-servers
```

## Test Metrics

Current baseline (as of Phase 5):
- **Total Tests**: 210
- **Duration**: ~9.7 seconds (with servers)
- **Coverage**: Auth, MCP, Web, Storage, Validation
- **Skipped**: 0 (zero-skip policy enforced)

## Best Practices

1. **Use fixtures**: Don't create auth services or storage in tests directly
2. **Isolate tests**: Use `temp_storage_dir` for storage tests
3. **Test one thing**: Each test should verify a single behavior
4. **Clear names**: Test names should describe what they verify
5. **Fast feedback**: Keep unit tests under 0.1s each
6. **Clean up**: Use fixtures with teardown or context managers
7. **No sleeps**: Use mocking instead of timing-based tests

## Troubleshooting

### Port Already in Use

```bash
# Kill existing servers
pkill -9 -f "python.*main_mcp.py"
pkill -9 -f "python.*main_web.py"
```

### Token Store Conflicts

The test runner automatically cleans the token store. If you see auth failures:

```bash
rm /tmp/gplot_test_tokens.json
```

### Stale Server Processes

The test runner includes detection for stale log files. If tests hang:

```bash
./scripts/run_tests.sh --with-servers  # Includes automatic cleanup
```

## See Also

- **[TEST_AUTH.md](./TEST_AUTH.md)** - Comprehensive authentication testing guide
- **[AUTHENTICATION.md](./AUTHENTICATION.md)** - JWT token creation and usage
- **[SECURITY.md](./SECURITY.md)** - Security architecture and best practices
- **[STORAGE.md](./STORAGE.md)** - Storage layer design and concurrency
- **[MCP_README.md](./MCP_README.md)** - MCP protocol details
- **[PROXY_MODE.md](./PROXY_MODE.md)** - GUID-based storage and retrieval
