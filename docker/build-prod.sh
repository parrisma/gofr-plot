#!/bin/bash
# =======================================================================
# GOFR-PLOT Production Build Script
# Builds the production Docker image with auto-versioning from pyproject.toml
# =======================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Extract version from pyproject.toml
VERSION=$(grep -E '^version\s*=' pyproject.toml | head -1 | sed 's/.*"\(.*\)".*/\1/')

if [ -z "$VERSION" ]; then
    echo "ERROR: Could not extract version from pyproject.toml"
    exit 1
fi

echo "======================================================================="
echo "Building GOFR-PLOT Production Image"
echo "======================================================================="
echo "Version: ${VERSION}"
echo "Project: ${PROJECT_ROOT}"
echo "======================================================================="

# Build the image with both version tag and latest tag
docker build \
    -f docker/Dockerfile.prod \
    -t gofr-plot-prod:${VERSION} \
    -t gofr-plot-prod:latest \
    .

echo ""
echo "======================================================================="
echo "Build complete: gofr-plot-prod:${VERSION}"
echo "======================================================================="
echo ""
echo "Image tags:"
docker images gofr-plot-prod --format "  {{.Repository}}:{{.Tag}} ({{.Size}})"
echo ""
echo "To run: ./docker/run-prod.sh"
echo "======================================================================="