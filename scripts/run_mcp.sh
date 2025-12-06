#!/bin/bash
# gofr-plot MCP Server Startup Script
# Starts the MCP server with proper authentication and configuration.

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Locate project root relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# Source centralized environment configuration
if [ -f "${PROJECT_ROOT}/gofr-plot.env" ]; then
    source "${PROJECT_ROOT}/gofr-plot.env"
fi

# Configuration with environment variable fallbacks
HOST="${GOFR_PLOT_MCP_HOST:-${GOFR_PLOT_HOST:-0.0.0.0}}"
PORT="${GOFR_PLOT_MCP_PORT:-8010}"
JWT_SECRET="${GOFR_PLOT_JWT_SECRET:-}"
TOKEN_STORE="${GOFR_PLOT_TOKEN_STORE:-${GOFR_PLOT_LOGS}/gofr-plot_tokens.json}"
NO_AUTH="${GOFR_PLOT_NO_AUTH:-true}"
WEB_URL="${GOFR_PLOT_WEB_URL:-http://$(hostname):${GOFR_PLOT_WEB_PORT:-8012}}"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --jwt-secret)
            JWT_SECRET="$2"
            shift 2
            ;;
        --web-url)
            WEB_URL="$2"
            shift 2
            ;;
        --token-store)
            TOKEN_STORE="$2"
            shift 2
            ;;
        --no-auth)
            NO_AUTH="true"
            shift
            ;;
        --web-url)
            WEB_URL="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --host HOST           Host to bind to (default: 0.0.0.0)"
            echo "  --port PORT           Port to run MCP server on (default: 8010)"
            echo "  --jwt-secret SECRET   JWT secret for token validation"
            echo "  --token-store PATH    Path to token store JSON file"
            echo "  --no-auth             Disable authentication"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  GOFR_PLOT_MCP_HOST        Default host (default: 0.0.0.0)"
            echo "  GOFR_PLOT_MCP_PORT        Default port (default: 8010)"
            echo "  GOFR_PLOT_JWT_SECRET      Default JWT secret"
            echo "  GOFR_PLOT_TOKEN_STORE     Default token store path"
            echo "  GOFR_PLOT_NO_AUTH         Set to 'true' to disable auth"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate authentication configuration
if [[ "${NO_AUTH}" != "true" ]]; then
    if [[ -z "${JWT_SECRET}" ]]; then
        echo -e "${RED}Error: JWT secret required when authentication is enabled${NC}"
        echo "Provide via --jwt-secret or GOFR_PLOT_JWT_SECRET environment variable"
        echo "Or use --no-auth to disable authentication"
        exit 1
    fi
fi

# Build command with DEBUG logging
CMD="uv run python app/main_mcp.py --host ${HOST} --port ${PORT} --web-url ${WEB_URL} --proxy-url-mode url --log-level DEBUG"

if [[ "${NO_AUTH}" == "true" ]]; then
    CMD="${CMD} --no-auth"
    echo -e "${YELLOW}⚠️  Authentication DISABLED${NC}"
else
    CMD="${CMD} --jwt-secret ${JWT_SECRET} --token-store ${TOKEN_STORE}"
    echo -e "${GREEN}✓ Authentication enabled${NC}"
    echo "Token store: ${TOKEN_STORE}"
fi

# Display startup information
echo -e "${GREEN}=== Starting gofr-plot MCP Server ===${NC}"
echo "Host: ${HOST}"
echo "Port: ${PORT}"
echo "URL: http://${HOST}:${PORT}/mcp/"
echo ""

# Check if port is already in use
if command -v lsof >/dev/null 2>&1; then
    if lsof -i ":${PORT}" >/dev/null 2>&1; then
        echo -e "${RED}Error: Port ${PORT} is already in use${NC}"
        echo "Running processes:"
        lsof -i ":${PORT}"
        exit 1
    fi
fi

# Start server
echo "Starting server..."
echo "Command: ${CMD}"
echo ""

# Execute with proper signal handling
exec ${CMD}
