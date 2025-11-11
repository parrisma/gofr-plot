# Web Server Tests

# Web Server Tests

This directory contains tests for the web server (FastAPI) functionality.

## Running Tests

Run all web tests with pytest:

```bash
pytest test/web/ -v
```

**Note:** The test suite uses dependency override to bypass JWT authentication for unit testing. This allows testing the rendering functionality without needing valid tokens.

## Test Files

- `test_ping.py` - Tests the ping endpoint (4 pytest tests)
- `test_web_rendering.py` - Tests chart rendering, formats, themes, and validation (13 pytest tests)
- `manual_test_web_server.py` - Manual test script (not pytest)

## Test Coverage

✅ **Rendering Tests (8 tests):**
- Line charts with base64
- Bar charts with direct image
- Scatter plots
- Dark/Light themes
- SVG/PDF formats
- Custom styling

✅ **Validation Tests (5 tests):**
- Mismatched array lengths
- Invalid chart types
- Empty data arrays
- Invalid alpha values
- Invalid color formats

✅ **Health Check (4 tests):**
- Ping endpoint status
- Timestamp validation
- Service identification

## Running the tests

Make sure you have the environment set up:

```bash
# From the project root
uv sync
```

Then run the test script:

```bash
python test/web/test_web_server.py
```

## What it tests

- Line, bar, and scatter chart rendering
- Base64 and direct image responses
- Different output formats (PNG, SVG, PDF)
- Light and dark themes
- Custom styling (colors, line width, transparency)
- Error handling

The tests use `httpx.AsyncClient` to test the FastAPI application without starting an actual server.
