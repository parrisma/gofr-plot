#!/bin/bash
# gplot MCP Server Startup Script
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

# Configuration with environment variable fallbacks
PORT="${GPLOT_MCP_PORT:-8001}"
JWT_SECRET="${GPLOT_JWT_SECRET:-}"
TOKEN_STORE="${GPLOT_TOKEN_STORE:-data/auth/tokens.json}"
NO_AUTH="${GPLOT_NO_AUTH:-true}"
WEB_URL="${GPLOT_WEB_URL:-http://$(hostname):8000}"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
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
            echo "  --port PORT           Port to run MCP server on (default: 8001)"
            echo "  --jwt-secret SECRET   JWT secret for token validation"
            echo "  --token-store PATH    Path to token store JSON file"
            echo "  --no-auth             Disable authentication"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  GPLOT_MCP_PORT        Default port (default: 8001)"
            echo "  GPLOT_JWT_SECRET      Default JWT secret"
            echo "  GPLOT_TOKEN_STORE     Default token store path"
            echo "  GPLOT_NO_AUTH         Set to 'true' to disable auth"
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
        echo "Provide via --jwt-secret or GPLOT_JWT_SECRET environment variable"
        echo "Or use --no-auth to disable authentication"
        exit 1
    fi
fi

# Build command with DEBUG logging
CMD="uv run python app/main_mcp.py --host 0.0.0.0 --port ${PORT} --web-url ${WEB_URL} --proxy-url-mode url --log-level DEBUG"

if [[ "${NO_AUTH}" == "true" ]]; then
    CMD="${CMD} --no-auth"
    echo -e "${YELLOW}⚠️  Authentication DISABLED${NC}"
else
    CMD="${CMD} --jwt-secret ${JWT_SECRET} --token-store ${TOKEN_STORE}"
    echo -e "${GREEN}✓ Authentication enabled${NC}"
    echo "Token store: ${TOKEN_STORE}"
fi

# Display startup information
echo -e "${GREEN}=== Starting gplot MCP Server ===${NC}"
echo "Port: ${PORT}"
echo "URL: http://localhost:${PORT}/mcp/"
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
