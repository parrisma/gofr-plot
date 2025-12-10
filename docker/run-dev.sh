#!/bin/bash
# Run GOFR-PLOT development container
# Uses gofr-plot-dev:latest image (built from gofr-base:latest)
# Standard user: gofr (UID 1000, GID 1000)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# gofr-common is now a git submodule at lib/gofr-common, no separate mount needed

# Standard GOFR user - all projects use same user
GOFR_USER="gofr"
GOFR_UID=1000
GOFR_GID=1000

# Container and image names
CONTAINER_NAME="gofr-plot-dev"
IMAGE_NAME="gofr-plot-dev:latest"

# Defaults from environment or hardcoded (gofr-plot uses 8050-8052)
MCP_PORT="${GOFRPLOT_MCP_PORT:-8050}"
MCPO_PORT="${GOFRPLOT_MCPO_PORT:-8051}"
WEB_PORT="${GOFRPLOT_WEB_PORT:-8052}"
DOCKER_NETWORK="${GOFRPLOT_DOCKER_NETWORK:-gofr-net}"

# Parse command line arguments
while [ $# -gt 0 ]; do
    case $1 in
        --mcp-port)
            MCP_PORT="$2"
            shift 2
            ;;
        --mcpo-port)
            MCPO_PORT="$2"
            shift 2
            ;;
        --web-port)
            WEB_PORT="$2"
            shift 2
            ;;
        --network)
            DOCKER_NETWORK="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--mcp-port PORT] [--mcpo-port PORT] [--web-port PORT] [--network NAME]"
            exit 1
            ;;
    esac
done

echo "======================================================================="
echo "Starting GOFR-PLOT Development Container"
echo "======================================================================="
echo "User: ${GOFR_USER} (UID=${GOFR_UID}, GID=${GOFR_GID})"
echo "Ports: MCP=$MCP_PORT, MCPO=$MCPO_PORT, Web=$WEB_PORT"
echo "Network: $DOCKER_NETWORK"
echo "======================================================================="

# Create docker network if it doesn't exist
if ! docker network inspect $DOCKER_NETWORK >/dev/null 2>&1; then
    echo "Creating network: $DOCKER_NETWORK"
    docker network create $DOCKER_NETWORK
fi

# Create docker volume for persistent data
VOLUME_NAME="gofr-plot-data-dev"
if ! docker volume inspect $VOLUME_NAME >/dev/null 2>&1; then
    echo "Creating volume: $VOLUME_NAME"
    docker volume create $VOLUME_NAME
fi

# Stop and remove existing container
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping existing container: $CONTAINER_NAME"
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
fi

# Run container
# Get host Docker GID to allow container to access docker socket
HOST_DOCKER_GID=$(getent group docker | cut -d: -f3 || echo "999")

docker run -d \
    --name "$CONTAINER_NAME" \
    --network "$DOCKER_NETWORK" \
    -p ${MCP_PORT}:8050 \
    -p ${MCPO_PORT}:8051 \
    -p ${WEB_PORT}:8052 \
    -v "$PROJECT_ROOT:/home/gofr/devroot/gofr-plot:rw" \
    -v ${VOLUME_NAME}:/home/gofr/devroot/gofr-plot/data:rw \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -e GOFRPLOT_ENV=development \
    -e GOFRPLOT_DEBUG=true \
    -e GOFRPLOT_LOG_LEVEL=DEBUG \
    -e DOCKER_GID="$HOST_DOCKER_GID" \
    "$IMAGE_NAME"

echo ""
echo "======================================================================="
echo "Container started: $CONTAINER_NAME"
echo "======================================================================="
echo ""
echo "Ports:"
echo "  - $MCP_PORT: MCP server"
echo "  - $MCPO_PORT: MCPO proxy"
echo "  - $WEB_PORT: Web interface"
echo ""
echo "Useful commands:"
echo "  docker logs -f $CONTAINER_NAME          # Follow logs"
echo "  docker exec -it $CONTAINER_NAME bash    # Shell access"
echo "  docker stop $CONTAINER_NAME             # Stop container"
