# Web Server Tests

This directory contains tests for the FastAPI web server.

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
