#!/bin/sh

# Get timezone (default to UTC if not set)
TIMEZONE="${TIMEZONE:-UTC}"

# Create docker network if it doesn't exist
echo "Checking for gmcp_net network..."
if ! docker network inspect gmcp_net >/dev/null 2>&1; then
    echo "Creating gmcp_net network..."
    docker network create gmcp_net
else
    echo "Network gmcp_net already exists"
fi

# Create n8n data volume if it doesn't exist
echo "Checking for n8n_data volume..."
if ! docker volume inspect n8n_data >/dev/null 2>&1; then
    echo "Creating n8n_data volume..."
    docker volume create n8n_data
else
    echo "Volume n8n_data already exists"
fi

# Stop and remove existing container if it exists
echo "Stopping existing n8n container..."
docker stop n8n 2>/dev/null || true

echo "Removing existing n8n container..."
docker rm n8n 2>/dev/null || true

echo "Starting n8n container..."
docker run -d \
  --name n8n \
  --network gmcp_net \
  -p 5678:5678 \
  -e GENERIC_TIMEZONE="$TIMEZONE" \
  -e TZ="$TIMEZONE" \
  -e N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true \
  -e N8N_RUNNERS_ENABLED=true \
  -v n8n_data:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n

if docker ps -q -f name=n8n | grep -q .; then
    echo "Container n8n is now running"
    echo ""
    echo "n8n is accessible at http://localhost:5678"
    echo "On gmcp_net, other containers can reach it at http://n8n:5678"
    echo ""
    echo "To view logs: docker logs -f n8n"
    echo "To stop: docker stop n8n"
else
    echo "ERROR: Container n8n failed to start"
    docker logs n8n
    exit 1
fi
