#!/bin/sh

# Stop and remove existing container if it exists
echo "Stopping existing gplot_prod container..."
docker stop gplot_prod 2>/dev/null || true

echo "Removing existing gplot_prod container..."
docker rm gplot_prod 2>/dev/null || true

echo "Starting new gplot_prod container..."

docker run -d \
--name gplot_prod \
-p 8000:8000 \
gplot_prod:latest

if docker ps -q -f name=gplot_prod | grep -q .; then
    echo "Container gplot_prod is now running"
    echo ""
    echo "MCP server is running (communicates via stdio)"
    echo "To run web server instead: docker exec -it gplot_prod python -m app.main"
    echo "To view logs: docker logs -f gplot_prod"
    echo "To stop: docker stop gplot_prod"
else
    echo "ERROR: Container gplot_prod failed to start"
    docker logs gplot_prod
    exit 1
fi
