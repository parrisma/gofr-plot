#!/bin/bash
# =======================================================================
# GOFR-PLOT Production Run Script
# Runs the production container with proper volumes and networking
# =======================================================================

set -e

# Default values
DOCKER_NETWORK="${GOFR_PLOT_NETWORK:-gofr-net}"
MCP_PORT="${GOFR_PLOT_MCP_PORT:-8050}"
MCPO_PORT="${GOFR_PLOT_MCPO_PORT:-8051}"
WEB_PORT="${GOFR_PLOT_WEB_PORT:-8052}"
CONTAINER_NAME="gofr-plot-prod"
IMAGE_NAME="gofr-plot:latest"

# JWT Secret - REQUIRED
JWT_SECRET="${GOFR_PLOT_JWT_SECRET:-}"

# Parse command line arguments
while getopts "n:m:o:w:s:h" opt; do
    case $opt in
        n) DOCKER_NETWORK=$OPTARG ;;
        m) MCP_PORT=$OPTARG ;;
        o) MCPO_PORT=$OPTARG ;;
        w) WEB_PORT=$OPTARG ;;
        s) JWT_SECRET=$OPTARG ;;
        h)
            echo "Usage: $0 [-n NETWORK] [-m MCP_PORT] [-o MCPO_PORT] [-w WEB_PORT] [-s JWT_SECRET]"
            echo ""
            echo "Options:"
            echo "  -n NETWORK     Docker network (default: gofr-net)"
            echo "  -m MCP_PORT    MCP server port (default: 8050)"
            echo "  -o MCPO_PORT   MCPO server port (default: 8051)"
            echo "  -w WEB_PORT    Web server port (default: 8052)"
            echo "  -s JWT_SECRET  JWT secret key (required, or set GOFR_PLOT_JWT_SECRET)"
            echo ""
            echo "Environment Variables:"
            echo "  GOFR_PLOT_NETWORK, GOFR_PLOT_MCP_PORT, GOFR_PLOT_MCPO_PORT"
            echo "  GOFR_PLOT_WEB_PORT, GOFR_PLOT_JWT_SECRET"
            exit 0
            ;;
        \?) echo "Invalid option: -$OPTARG" >&2; exit 1 ;;
    esac
done

# Validate JWT secret
if [ -z "$JWT_SECRET" ]; then
    echo "ERROR: JWT_SECRET is required"
    echo "Set GOFR_PLOT_JWT_SECRET environment variable or use -s option"
    exit 1
fi

echo "======================================================================="
echo "Starting GOFR-PLOT Production Container"
echo "======================================================================="

# Create docker network if it doesn't exist
if ! docker network inspect ${DOCKER_NETWORK} >/dev/null 2>&1; then
    echo "Creating network: ${DOCKER_NETWORK}"
    docker network create ${DOCKER_NETWORK}
else
    echo "Network exists: ${DOCKER_NETWORK}"
fi

# Create volumes if they don't exist
for vol in gofr-plot-data gofr-plot-logs; do
    if ! docker volume inspect ${vol} >/dev/null 2>&1; then
        echo "Creating volume: ${vol}"
        docker volume create ${vol}
    else
        echo "Volume exists: ${vol}"
    fi
done

# Stop and remove existing container
if docker ps -aq -f name=${CONTAINER_NAME} | grep -q .; then
    echo "Stopping existing container..."
    docker stop ${CONTAINER_NAME} 2>/dev/null || true
    docker rm ${CONTAINER_NAME} 2>/dev/null || true
fi

echo ""
echo "Configuration:"
echo "  Network:    ${DOCKER_NETWORK}"
echo "  MCP Port:   ${MCP_PORT} -> 8010"
echo "  MCPO Port:  ${MCPO_PORT} -> 8011"
echo "  Web Port:   ${WEB_PORT} -> 8012"
echo "  Data:       gofr-plot-data -> /home/gofr-plot/data"
echo "  Logs:       gofr-plot-logs -> /home/gofr-plot/logs"
echo ""

# Run the container
docker run -d \
    --name ${CONTAINER_NAME} \
    --network ${DOCKER_NETWORK} \
    --restart unless-stopped \
    -v gofr-plot-data:/home/gofr-plot/data \
    -v gofr-plot-logs:/home/gofr-plot/logs \
    -p ${MCP_PORT}:8010 \
    -p ${MCPO_PORT}:8011 \
    -p ${WEB_PORT}:8012 \
    -e GOFR_PLOT_JWT_SECRET="${JWT_SECRET}" \
    -e GOFR_PLOT_MCP_PORT=8010 \
    -e GOFR_PLOT_MCPO_PORT=8011 \
    -e GOFR_PLOT_WEB_PORT=8012 \
    ${IMAGE_NAME}

# Wait for container to start
sleep 2

if docker ps -q -f name=${CONTAINER_NAME} | grep -q .; then
    echo "======================================================================="
    echo "Container started: ${CONTAINER_NAME}"
    echo "======================================================================="
    echo ""
    echo "Endpoints:"
    echo "  MCP Server:  http://localhost:${MCP_PORT}/mcp"
    echo "  MCPO (REST): http://localhost:${MCPO_PORT}"
    echo "  Web Server:  http://localhost:${WEB_PORT}"
    echo "  Health:      http://localhost:${WEB_PORT}/ping"
    echo ""
    echo "Useful commands:"
    echo "  docker logs -f ${CONTAINER_NAME}     # Follow logs"
    echo "  docker exec -it ${CONTAINER_NAME} bash  # Shell access"
    echo "  docker stop ${CONTAINER_NAME}        # Stop container"
    echo "======================================================================="
else
    echo "ERROR: Container failed to start"
    docker logs ${CONTAINER_NAME}
    exit 1
fi