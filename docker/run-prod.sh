#!/bin/sh

# Usage: ./run-prod.sh [WEB_PORT] [MCP_PORT]
# Defaults: WEB_PORT=8000, MCP_PORT=8001
# Example: ./run-prod.sh 9000 9001

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
echo "Checking for gplot_data volume..."
if ! docker volume inspect gplot_data >/dev/null 2>&1; then
    echo "Creating gplot_data volume..."
    docker volume create gplot_data
    VOLUME_CREATED=true
else
    echo "Volume gplot_data already exists"
    VOLUME_CREATED=false
fi

# Stop and remove existing container if it exists
echo "Stopping existing gplot_prod container..."
docker stop gplot_prod 2>/dev/null || true

echo "Removing existing gplot_prod container..."
docker rm gplot_prod 2>/dev/null || true

echo "Starting new gplot_prod container..."
echo "Mounting gplot_data volume to /home/gplot/data in container"
echo "Web port: $WEB_PORT, MCP port: $MCP_PORT"

docker run -d \
--name gplot_prod \
--network gplot_net \
-v gplot_data:/home/gplot/data \
-p $WEB_PORT:8000 \
-p $MCP_PORT:8001 \
gplot_prod:latest

if docker ps -q -f name=gplot_prod | grep -q .; then
    echo "Container gplot_prod is now running"
    
    # Fix volume permissions if it was just created
    if [ "$VOLUME_CREATED" = true ]; then
        echo "Fixing permissions on newly created volume..."
        docker exec -u root gplot_prod chown -R gplot:gplot /home/gplot/data
        echo "Volume permissions fixed"
    fi
    
    echo ""
    echo "HTTP REST API available at http://localhost:$WEB_PORT"
    echo "MCP Streamable HTTP Server available at http://localhost:$MCP_PORT/mcp/"
    echo "Persistent data stored in Docker volume: gplot_data"
    echo ""
    echo "To run web server: docker exec -it gplot_prod python -m app.main_web"
    echo "To view logs: docker logs -f gplot_prod"
    echo "To stop: docker stop gplot_prod"
else
    echo "ERROR: Container gplot_prod failed to start"
    docker logs gplot_prod
    exit 1
fi
