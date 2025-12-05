#!/bin/sh

# Usage: ./run-prod.sh [WEB_PORT] [MCP_PORT]
# Defaults: WEB_PORT=8000, MCP_PORT=8001
# Example: ./run-prod.sh 9000 9001

# Parse command line arguments
WEB_PORT=${1:-8000}
MCP_PORT=${2:-8001}

# Create docker network if it doesn't exist
echo "Checking for gofr-net network..."
if ! docker network inspect gofr-net >/dev/null 2>&1; then
    echo "Creating gofr-net network..."
    docker network create gofr-net
else
    echo "Network gofr-net already exists"
fi

# Create docker volume for persistent data if it doesn't exist
echo "Checking for gofr-plot_data volume..."
if ! docker volume inspect gofr-plot_data >/dev/null 2>&1; then
    echo "Creating gofr-plot_data volume..."
    docker volume create gofr-plot_data
    VOLUME_CREATED=true
else
    echo "Volume gofr-plot_data already exists"
    VOLUME_CREATED=false
fi

# Stop and remove existing container if it exists
echo "Stopping existing gofr-plot_prod container..."
docker stop gofr-plot_prod 2>/dev/null || true

echo "Removing existing gofr-plot_prod container..."
docker rm gofr-plot_prod 2>/dev/null || true

echo "Starting new gofr-plot_prod container..."
echo "Mounting gofr-plot_data volume to /home/gofr-plot/data in container"
echo "Web port: $WEB_PORT, MCP port: $MCP_PORT"

docker run -d \
--name gofr-plot_prod \
--network gofr-net \
-v gofr-plot_data:/home/gofr-plot/data \
-p $WEB_PORT:8000 \
-p $MCP_PORT:8001 \
gofr-plot_prod:latest

if docker ps -q -f name=gofr-plot_prod | grep -q .; then
    echo "Container gofr-plot_prod is now running"
    
    # Fix volume permissions if it was just created
    if [ "$VOLUME_CREATED" = true ]; then
        echo "Fixing permissions on newly created volume..."
        docker exec -u root gofr-plot_prod chown -R gofr-plot:gofr-plot /home/gofr-plot/data
        echo "Volume permissions fixed"
    fi
    
    echo ""
    echo "HTTP REST API available at http://localhost:$WEB_PORT"
    echo "MCP Streamable HTTP Server available at http://localhost:$MCP_PORT/mcp/"
    echo "Persistent data stored in Docker volume: gofr-plot_data"
    echo ""
    echo "To run web server: docker exec -it gofr-plot_prod python -m app.main_web"
    echo "To view logs: docker logs -f gofr-plot_prod"
    echo "To stop: docker stop gofr-plot_prod"
else
    echo "ERROR: Container gofr-plot_prod failed to start"
    docker logs gofr-plot_prod
    exit 1
fi
