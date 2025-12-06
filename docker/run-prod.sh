#!/bin/sh

# Usage: ./run-prod.sh [-n NETWORK] [-w WEB_PORT] [-m MCP_PORT]
# Defaults: NETWORK=gofr-net, WEB_PORT=8000, MCP_PORT=8001
# Example: ./run-prod.sh -n my-network -w 9000 -m 9001

# Default values (can be overridden by env vars or command line)
DOCKER_NETWORK="${GOFR_PLOT_NETWORK:-gofr-net}"
WEB_PORT=8000
MCP_PORT=8001

# Parse command line arguments
while getopts "n:w:m:h" opt; do
    case $opt in
        n)
            DOCKER_NETWORK=$OPTARG
            ;;
        w)
            WEB_PORT=$OPTARG
            ;;
        m)
            MCP_PORT=$OPTARG
            ;;
        h)
            echo "Usage: $0 [-n NETWORK] [-w WEB_PORT] [-m MCP_PORT]"
            echo "  -n NETWORK   Docker network to attach to (default: gofr-net)"
            echo "  -w WEB_PORT  Port to expose web server on (default: 8000)"
            echo "  -m MCP_PORT  Port to expose MCP server on (default: 8001)"
            echo ""
            echo "Environment Variables:"
            echo "  GOFR_PLOT_NETWORK  Default network (default: gofr-net)"
            exit 0
            ;;
        \?)
            echo "Usage: $0 [-n NETWORK] [-w WEB_PORT] [-m MCP_PORT]"
            exit 1
            ;;
    esac
done

# Create docker network if it doesn't exist
echo "Checking for ${DOCKER_NETWORK} network..."
if ! docker network inspect ${DOCKER_NETWORK} >/dev/null 2>&1; then
    echo "Creating ${DOCKER_NETWORK} network..."
    docker network create ${DOCKER_NETWORK}
else
    echo "Network ${DOCKER_NETWORK} already exists"
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
echo "Network: $DOCKER_NETWORK"
echo "Mounting gofr-plot_data volume to /home/gofr-plot/data in container"
echo "Web port: $WEB_PORT, MCP port: $MCP_PORT"

docker run -d \
--name gofr-plot_prod \
--network ${DOCKER_NETWORK} \
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
