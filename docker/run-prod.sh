#!/bin/sh

# Create docker network if it doesn't exist
echo "Checking for gmcp_net network..."
if ! docker network inspect gmcp_net >/dev/null 2>&1; then
    echo "Creating gmcp_net network..."
    docker network create gmcp_net
else
    echo "Network gmcp_net already exists"
fi

# Stop and remove existing container if it exists
echo "Stopping existing gplot_prod container..."
docker stop gplot_prod 2>/dev/null || true

echo "Removing existing gplot_prod container..."
docker rm gplot_prod 2>/dev/null || true

echo "Starting new gplot_prod container..."

docker run -d \
--name gplot_prod \
--network gmcp_net \
-p 8000:8000 \
-p 8001:8001 \
gplot_prod:latest

if docker ps -q -f name=gplot_prod | grep -q .; then
    echo "Container gplot_prod is now running"
    echo ""
    echo "MCP SSE Server is running on port 8001"
    echo "HTTP REST API available at http://localhost:8000"
    echo "MCP SSE Server available at http://localhost:8001/sse"
    echo ""
    echo "To run web server: docker exec -it gplot_prod python -m app.main"
    echo "To view logs: docker logs -f gplot_prod"
    echo "To stop: docker stop gplot_prod"
else
    echo "ERROR: Container gplot_prod failed to start"
    docker logs gplot_prod
    exit 1
fi
