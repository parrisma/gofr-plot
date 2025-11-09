#!/usr/bin/env python3
"""Test ping endpoint for web server"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from app.web_server import GraphWebServer


def test_ping_endpoint():
    """Test that ping endpoint returns status and timestamp"""
    server = GraphWebServer()
    client = TestClient(server.app)

    response = client.get("/ping")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert data["status"] == "ok"

    assert "timestamp" in data
    assert isinstance(data["timestamp"], str)

    assert "service" in data
    assert data["service"] == "gplot"

    print("✓ Ping endpoint returns correct status and timestamp")


if __name__ == "__main__":
    test_ping_endpoint()
    print("\n" + "=" * 50)
    print("All ping tests passed!")
    print("=" * 50)
