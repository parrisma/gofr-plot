#!/bin/sh

# Usage: ./run-n8n.sh [-r] [-p PORT] [-n NETWORK]
# Options:
#   -r           Recreate doco_volume (drop and recreate if it exists)
#   -p PORT      Port to expose n8n on (default: 5678)
#   -n NETWORK   Docker network to attach to (default: gofr-net)
# Example: ./run-n8n.sh -p 9000 -r -n my-network

# Default values (can be overridden by env vars or command line)
RECREATE_VOLUME=false
N8N_PORT=5678
DOCKER_NETWORK="${GOFR_PLOT_NETWORK:-gofr-net}"

while getopts "rp:n:h" opt; do
    case $opt in
        r)
            RECREATE_VOLUME=true
            ;;
        p)
            N8N_PORT=$OPTARG
            ;;
        n)
            DOCKER_NETWORK=$OPTARG
            ;;
        h)
            echo "Usage: $0 [-r] [-p PORT] [-n NETWORK]"
            echo "  -r           Recreate doco_volume (drop and recreate if it exists)"
            echo "  -p PORT      Port to expose n8n on (default: 5678)"
            echo "  -n NETWORK   Docker network to attach to (default: gofr-net)"
            echo ""
            echo "Environment Variables:"
            echo "  GOFR_PLOT_NETWORK  Default network (default: gofr-net)"
            exit 0
            ;;
        \?)
            echo "Usage: $0 [-r] [-p PORT] [-n NETWORK]"
            exit 1
            ;;
    esac
done

# Get timezone (default to UTC if not set)
TIMEZONE="${TIMEZONE:-UTC}"

# Create n8n_share directory on host if it doesn't exist
N8N_SHARE_DIR="${HOME}/n8n_share"
echo "Checking for n8n_share directory at ${N8N_SHARE_DIR}..."
if [ ! -d "$N8N_SHARE_DIR" ]; then
    echo "Creating n8n_share directory..."
    mkdir -p "$N8N_SHARE_DIR"
    echo "Directory created at ${N8N_SHARE_DIR}"
else
    echo "Directory ${N8N_SHARE_DIR} already exists"
fi

# Create docker network if it doesn't exist
echo "Checking for ${DOCKER_NETWORK} network..."
if ! docker network inspect ${DOCKER_NETWORK} >/dev/null 2>&1; then
    echo "Creating ${DOCKER_NETWORK} network..."
    docker network create ${DOCKER_NETWORK}
else
    echo "Network ${DOCKER_NETWORK} already exists"
fi

# Handle doco_volume creation/recreation
if [ "$RECREATE_VOLUME" = true ]; then
    echo "Recreate flag (-r) detected"
    if docker volume inspect doco_volume >/dev/null 2>&1; then
        echo "Removing existing doco_volume..."
        docker volume rm doco_volume 2>/dev/null || {
            echo "ERROR: Failed to remove doco_volume. It may be in use."
            echo "Stop all containers using the volume first."
            exit 1
        }
    fi
    echo "Creating doco_volume..."
    docker volume create doco_volume
else
    # Create doco_volume if it doesn't exist
    echo "Checking for doco_volume..."
    if ! docker volume inspect doco_volume >/dev/null 2>&1; then
        echo "Creating doco_volume..."
        docker volume create doco_volume
    else
        echo "Volume doco_volume already exists"
    fi
fi

# Stop and remove existing container if it exists
echo "Stopping existing n8n container..."
docker stop n8n 2>/dev/null || true

echo "Removing existing n8n container..."
docker rm n8n 2>/dev/null || true

echo "Starting n8n container..."
echo "Network: $DOCKER_NETWORK"
echo "Port: $N8N_PORT"
docker run -d \
  --name n8n \
  --network ${DOCKER_NETWORK} \
  -p $N8N_PORT:5678 \
  -e GENERIC_TIMEZONE="$TIMEZONE" \
  -e TZ="$TIMEZONE" \
  -e N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true \
  -e N8N_RUNNERS_ENABLED=true \
  -e N8N_LOG_LEVEL=debug \
  -e N8N_LOG_OUTPUT=console \
  -e NODE_FUNCTION_ALLOW_EXTERNAL= \
    -v doco_volume:/home/node/.n8n \
  -v "${N8N_SHARE_DIR}":/data/n8n_share \
  docker.n8n.io/n8nio/n8n

if docker ps -q -f name=n8n | grep -q .; then
    echo "Container n8n is now running"
    echo ""
    echo "==================================================================="
    echo "Access from Host Machine:"
    echo "  n8n Web UI:    http://localhost:$N8N_PORT"
    echo ""
    echo "Access from ${DOCKER_NETWORK} (other containers):"
    echo "  n8n API:       http://n8n:5678"
    echo ""
    echo "Data & Storage:"
    echo "  Volume:        doco_volume"
    echo "  Shared Dir:    ${N8N_SHARE_DIR} -> /data/n8n_share"
    echo ""
    echo "Management:"
    echo "  View logs:     docker logs -f n8n"
    echo "  Stop:          docker stop n8n"
    echo "  Recreate:      ./docker/run-n8n.sh -r -p $N8N_PORT -n $DOCKER_NETWORK"
    echo "==================================================================="
    echo ""
else
    echo "ERROR: Container n8n failed to start"
    docker logs n8n
    exit 1
fi
