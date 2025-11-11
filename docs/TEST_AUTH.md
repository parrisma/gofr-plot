# Authentication Tests

Comprehensive test suite for JWT authentication in gplot.

## Test Coverage

### Test 1: Token Creation
- Creates an auth token for group "secure" with 90 second expiry
- Verifies token is properly created and signed
- Validates token contains correct group and expiry information

### Test 2: MCP Server Authentication
Tests that graphs can only be created and accessed via MCP with valid tokens:
- ✓ Render graph with valid token succeeds
- ✓ Render graph without token fails
- ✓ Render graph with invalid token fails
- ✓ Retrieve image with valid token from same group succeeds
- ✓ Retrieve image with token from different group fails (group isolation)

### Test 3: Web Server Authentication
Tests that graphs can only be created and accessed via web API with valid tokens:
- ✓ Render graph with valid token succeeds
- ✓ Render graph without Authorization header fails
- ✓ Render graph with invalid token fails
- ✓ Retrieve image with valid token from same group succeeds
- ✓ Retrieve image without Authorization header fails
- ✓ Retrieve image with token from different group fails (group isolation)

## Prerequisites

### 1. Install Test Dependencies

```bash
pip install pytest pytest-asyncio httpx
```

Or with uv:

```bash
uv pip install pytest pytest-asyncio httpx
```

### 2. Set JWT Secret

Both servers must use the same JWT secret for the tests to work:

```bash
export GPLOT_JWT_SECRET="test-secret-key-for-auth-testing"
```

### 3. Start Both Servers

**Terminal 1 - Web Server:**
```bash
python app/main.py --jwt-secret "test-secret-key-for-auth-testing"
```

**Terminal 2 - MCP Server:**
```bash
python -m app.main_mcp --jwt-secret "test-secret-key-for-auth-testing"
```

Both servers should be running before executing tests.

## Running the Tests

### Run All Authentication Tests

```bash
# From project root
pytest test/test_authentication.py -v -s
```

### Run Specific Test Classes

```bash
# Test 1: Token creation only
pytest test/test_authentication.py::TestAuthTokenCreation -v -s

# Test 2: MCP authentication only
pytest test/test_authentication.py::TestMCPAuthentication -v -s

# Test 3: Web authentication only
pytest test/test_authentication.py::TestWebAuthentication -v -s
```

### Run Specific Tests

```bash
# Test token creation
pytest test/test_authentication.py::TestAuthTokenCreation::test_create_token -v -s

# Test MCP with valid token
pytest test/test_authentication.py::TestMCPAuthentication::test_mcp_render_with_valid_token -v -s

# Test web with valid token
pytest test/test_authentication.py::TestWebAuthentication::test_web_render_with_valid_token -v -s
```

## Expected Output

```
test/test_authentication.py::TestAuthTokenCreation::test_create_token PASSED
test/test_authentication.py::TestMCPAuthentication::test_mcp_render_with_valid_token PASSED
test/test_authentication.py::TestMCPAuthentication::test_mcp_render_without_token PASSED
test/test_authentication.py::TestMCPAuthentication::test_mcp_render_with_invalid_token PASSED
test/test_authentication.py::TestMCPAuthentication::test_mcp_get_image_with_valid_token PASSED
test/test_authentication.py::TestMCPAuthentication::test_mcp_get_image_with_different_group_token PASSED
test/test_authentication.py::TestWebAuthentication::test_web_render_with_valid_token PASSED
test/test_authentication.py::TestWebAuthentication::test_web_render_without_token PASSED
test/test_authentication.py::TestWebAuthentication::test_web_render_with_invalid_token PASSED
test/test_authentication.py::TestWebAuthentication::test_web_get_image_with_valid_token PASSED
test/test_authentication.py::TestWebAuthentication::test_web_get_image_without_token PASSED
test/test_authentication.py::TestWebAuthentication::test_web_get_image_with_different_group_token PASSED

============= 12 passed in X.XXs =============
```

## Test Configuration

The tests use the following configuration (defined in `test_authentication.py`):

```python
TEST_GROUP = "secure"              # Group name for test tokens
TEST_EXPIRY_SECONDS = 90           # Token expiry time
TEST_JWT_SECRET = "test-secret-key-for-auth-testing"  # Shared secret
MCP_URL = "http://localhost:8001/mcp/"
WEB_URL = "http://localhost:8000"
```

## Troubleshooting

### "Connection refused" errors

Make sure both servers are running:
```bash
# Check if web server is running
curl http://localhost:8000/ping

# Check if MCP server is accessible
curl http://localhost:8001/mcp/
```

### "Authentication Error: Invalid token"

Ensure both servers are using the same JWT secret:
```bash
# Both should use the same secret
export GPLOT_JWT_SECRET="test-secret-key-for-auth-testing"
python -m app.main_web --jwt-secret "test-secret-key-for-auth-testing"
python -m app.main_mcp --jwt-secret "test-secret-key-for-auth-testing"
```

### Tests hang or timeout

- Verify servers are responding: `curl http://localhost:8000/ping`
- Check server logs for errors
- Ensure no firewall is blocking localhost connections

### "ModuleNotFoundError: No module named 'pytest'"

Install test dependencies:
```bash
pip install pytest pytest-asyncio httpx
```

## CI/CD Integration

To run these tests in CI/CD pipelines:

```bash
#!/bin/bash
# Start servers in background
export GPLOT_JWT_SECRET="ci-test-secret"
python app/main.py --jwt-secret "$GPLOT_JWT_SECRET" &
WEB_PID=$!
python app/mcp_server.py --jwt-secret "$GPLOT_JWT_SECRET" &
MCP_PID=$!

# Wait for servers to start
sleep 5

# Run tests
pytest test/test_authentication.py -v

# Capture exit code
EXIT_CODE=$?

# Cleanup
kill $WEB_PID $MCP_PID

exit $EXIT_CODE
```

## Additional Notes

- Tests use temporary token stores that are automatically cleaned up
- Each test is independent and can be run in isolation
- Group isolation is thoroughly tested to ensure security
- Both proxy mode (GUID) and direct mode (base64) rendering are tested
