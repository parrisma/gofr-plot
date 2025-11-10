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
echo "Stopping existing gplot_dev container..."
docker stop gplot_dev 2>/dev/null || true

echo "Removing existing gplot_dev container..."
docker rm gplot_dev 2>/dev/null || true

echo "Starting new gplot_dev container..."
echo "Mounting $HOME/devroot/gplot to /home/gplot/devroot/gplot in container"
echo "Mounting $HOME/.ssh to /home/gplot/.ssh (read-only) in container"

docker run -d \
--name gplot_dev \
--network gmcp_net \
-v "$HOME/devroot/gplot":/home/gplot/devroot/gplot \
-v "$HOME/.ssh:/home/gplot/.ssh:ro" \
-p 8000:8000 \
-p 8001:8001 \
gplot_dev:latest

if docker ps -q -f name=gplot_dev | grep -q .; then
    echo "Container gplot_dev is now running"
    echo ""
    echo "To connect from shell: docker exec -it gplot_dev /bin/bash"
    echo "To connect from VS Code: use container name 'gplot_dev'"
    echo "HTTP REST API available at http://localhost:8000"
    echo "MCP SSE Server available at http://localhost:8001/sse"
else
    echo "ERROR: Container gplot_dev failed to start"
    exit 1
fi