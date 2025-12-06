#!/bin/sh

# Usage: ./run-dev.sh [-n NETWORK] [-w WEB_PORT] [-m MCP_PORT]
# Defaults: NETWORK=gofr-net, WEB_PORT=8000, MCP_PORT=8001
# Example: ./run-dev.sh -n my-network -w 9000 -m 9001

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
echo "Checking for gofr-plot_data_dev volume..."
if ! docker volume inspect gofr-plot_data_dev >/dev/null 2>&1; then
    echo "Creating gofr-plot_data_dev volume..."
    docker volume create gofr-plot_data_dev
    VOLUME_CREATED=true
else
    echo "Volume gofr-plot_data_dev already exists"
    VOLUME_CREATED=false
fi

# Stop and remove existing container if it exists
echo "Stopping existing gofr-plot_dev container..."
docker stop gofr-plot_dev 2>/dev/null || true

echo "Removing existing gofr-plot_dev container..."
docker rm gofr-plot_dev 2>/dev/null || true

echo "Starting new gofr-plot_dev container..."
echo "Network: $DOCKER_NETWORK"
echo "Mounting $HOME/devroot/gofr-plot to /home/gofr-plot/devroot/gofr-plot in container"
echo "Mounting $HOME/.ssh to /home/gofr-plot/.ssh (read-only) in container"
echo "Mounting gofr-plot_data_dev volume to /home/gofr-plot/devroot/gofr-plot/data in container"
echo "Web port: $WEB_PORT, MCP port: $MCP_PORT"

docker run -d \
--name gofr-plot_dev \
--network ${DOCKER_NETWORK} \
--user $(id -u):$(id -g) \
-v "$HOME/devroot/gofr-plot":/home/gofr-plot/devroot/gofr-plot \
-v "$HOME/.ssh:/home/gofr-plot/.ssh:ro" \
-v gofr-plot_data_dev:/home/gofr-plot/devroot/gofr-plot/data \
-p 0.0.0.0:$WEB_PORT:8000 \
-p 0.0.0.0:$MCP_PORT:8001 \
gofr-plot_dev:latest

if docker ps -q -f name=gofr-plot_dev | grep -q .; then
    echo "Container gofr-plot_dev is now running"
    
    # Fix volume permissions if it was just created
    if [ "$VOLUME_CREATED" = true ]; then
        echo "Fixing permissions on newly created volume..."
        docker exec -u root gofr-plot_dev chown -R gofr-plot:gofr-plot /home/gofr-plot/devroot/gofr-plot/data
        echo "Volume permissions fixed"
    fi
    
    echo ""
    echo "To connect from shell: docker exec -it gofr-plot_dev /bin/bash"
    echo "To connect from VS Code: use container name 'gofr-plot_dev'"
    echo "HTTP REST API available at http://localhost:$WEB_PORT"
    echo "MCP Streamable HTTP Server available at http://localhost:$MCP_PORT/mcp/"
    echo "Persistent data stored in Docker volume: gofr-plot_data_dev"
else
    echo "ERROR: Container gofr-plot_dev failed to start"
    exit 1
fi