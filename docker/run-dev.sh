#!/bin/sh

# Usage: ./run-dev.sh [WEB_PORT] [MCP_PORT]
# Defaults: WEB_PORT=8000, MCP_PORT=8001
# Example: ./run-dev.sh 9000 9001

# Parse command line arguments
WEB_PORT=${1:-8000}
MCP_PORT=${2:-8001}

# Create docker network if it doesn't exist
echo "Checking for gplot_net network..."
if ! docker network inspect gplot_net >/dev/null 2>&1; then
    echo "Creating gplot_net network..."
    docker network create gplot_net
else
    echo "Network gplot_net already exists"
fi

# Create docker volume for persistent data if it doesn't exist
echo "Checking for gplot_data_dev volume..."
if ! docker volume inspect gplot_data_dev >/dev/null 2>&1; then
    echo "Creating gplot_data_dev volume..."
    docker volume create gplot_data_dev
    VOLUME_CREATED=true
else
    echo "Volume gplot_data_dev already exists"
    VOLUME_CREATED=false
fi

# Stop and remove existing container if it exists
echo "Stopping existing gplot_dev container..."
docker stop gplot_dev 2>/dev/null || true

echo "Removing existing gplot_dev container..."
docker rm gplot_dev 2>/dev/null || true

echo "Starting new gplot_dev container..."
echo "Mounting $HOME/devroot/gplot to /home/gplot/devroot/gplot in container"
echo "Mounting $HOME/.ssh to /home/gplot/.ssh (read-only) in container"
echo "Mounting gplot_data_dev volume to /home/gplot/devroot/gplot/data in container"
echo "Web port: $WEB_PORT, MCP port: $MCP_PORT"

docker run -d \
--name gplot_dev \
--network gplot_net \
--user $(id -u):$(id -g) \
-v "$HOME/devroot/gplot":/home/gplot/devroot/gplot \
-v "$HOME/.ssh:/home/gplot/.ssh:ro" \
-v gplot_data_dev:/home/gplot/devroot/gplot/data \
-p $WEB_PORT:8000 \
-p $MCP_PORT:8001 \
gplot_dev:latest

if docker ps -q -f name=gplot_dev | grep -q .; then
    echo "Container gplot_dev is now running"
    
    # Fix volume permissions if it was just created
    if [ "$VOLUME_CREATED" = true ]; then
        echo "Fixing permissions on newly created volume..."
        docker exec -u root gplot_dev chown -R gplot:gplot /home/gplot/devroot/gplot/data
        echo "Volume permissions fixed"
    fi
    
    echo ""
    echo "To connect from shell: docker exec -it gplot_dev /bin/bash"
    echo "To connect from VS Code: use container name 'gplot_dev'"
    echo "HTTP REST API available at http://localhost:$WEB_PORT"
    echo "MCP Streamable HTTP Server available at http://localhost:$MCP_PORT/mcp/"
    echo "Persistent data stored in Docker volume: gplot_data_dev"
else
    echo "ERROR: Container gplot_dev failed to start"
    exit 1
fi