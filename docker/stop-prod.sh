#!/bin/bash
# =======================================================================
# GOFR-PLOT Production Stop Script
# Gracefully stops the production container
# =======================================================================

set -e

CONTAINER_NAME="gofr-plot-prod"

echo "======================================================================="
echo "Stopping GOFR-PLOT Production Container"
echo "======================================================================="

if docker ps -q -f name=${CONTAINER_NAME} | grep -q .; then
    echo "Stopping ${CONTAINER_NAME}..."
    docker stop ${CONTAINER_NAME}
    echo "Container stopped"
else
    echo "Container ${CONTAINER_NAME} is not running"
fi

# Optionally remove the container
if [ "$1" = "--rm" ] || [ "$1" = "-r" ]; then
    if docker ps -aq -f name=${CONTAINER_NAME} | grep -q .; then
        echo "Removing ${CONTAINER_NAME}..."
        docker rm ${CONTAINER_NAME}
        echo "Container removed"
    fi
fi

echo "======================================================================="
echo "Done"
echo "======================================================================="
