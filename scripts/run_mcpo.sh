#!/bin/bash
# gplot MCPO Wrapper Startup Script
# Starts MCPO (Model Context Protocol to OpenAPI) wrapper for the MCP server.
# Exposes MCP tools as REST/OpenAPI endpoints for OpenWebUI and other LLM clients.

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Locate project root relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# Source centralized environment configuration
if [ -f "${PROJECT_ROOT}/gplot.env" ]; then
    source "${PROJECT_ROOT}/gplot.env"
fi

# Configuration with environment variable fallbacks
MCPO_PORT="${GPLOT_MCPO_PORT:-8011}"
MCP_PORT="${GPLOT_MCP_PORT:-8010}"
MCP_URL="http://localhost:${MCP_PORT}/mcp"
MCPO_API_KEY="${GPLOT_MCPO_API_KEY:-}"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            MCPO_PORT="$2"
            shift 2
            ;;
        --mcp-port)
            MCP_PORT="$2"
            MCP_URL="http://localhost:${MCP_PORT}/mcp"
            shift 2
            ;;
        --api-key)
            MCPO_API_KEY="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Starts MCPO wrapper to expose MCP server as OpenAPI/REST endpoints."
            echo ""
            echo "Options:"
            echo "  --port PORT           Port for MCPO to listen on (default: 8011)"
            echo "  --mcp-port PORT       Port where MCP server is running (default: 8010)"
            echo "  --api-key KEY         MCPO API key (optional, for additional auth layer)"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  GPLOT_MCPO_PORT       Default MCPO port (default: 8011)"
            echo "  GPLOT_MCP_PORT        Default MCP port (default: 8010)"
            echo "  GPLOT_MCPO_API_KEY    MCPO API key (optional)"
            echo ""
            echo "Authentication:"
            echo "  - Without --api-key: JWT tokens pass through to MCP (group-based security)"
            echo "  - With --api-key: Additional auth layer at MCPO boundary"
            echo ""
            echo "Connection URLs:"
            echo "  OpenAPI Spec: http://localhost:8011/openapi.json"
            echo "  Health Check: http://localhost:8011/health"
            echo "  Service URL:  http://localhost:8011/gplot-renderer"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Display startup information
echo -e "${BLUE}=== Starting gplot MCPO Wrapper ===${NC}"
echo "MCPO Port: ${MCPO_PORT}"
echo "MCP Server: ${MCP_URL}"

# Check for stale processes on MCPO port
if command -v lsof >/dev/null 2>&1; then
    if lsof -i ":${MCPO_PORT}" >/dev/null 2>&1; then
        echo -e "${RED}Error: Port ${MCPO_PORT} is already in use${NC}"
        echo "Running processes:"
        lsof -i ":${MCPO_PORT}"
        echo ""
        echo "To kill these processes:"
        echo "  lsof -ti :${MCPO_PORT} | xargs kill -9"
        exit 1
    fi
fi

# Wait for MCP server availability
echo ""
echo "Waiting for MCP server at ${MCP_URL}..."
MCP_AVAILABLE=false
for i in {1..30}; do
    # Check if MCP server responds (200, 404, or 405 all indicate server is running)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${MCP_PORT}/" 2>/dev/null || echo "000")
    if [[ "${HTTP_CODE}" =~ ^(200|404|405)$ ]]; then
        echo -e "${GREEN}✓ MCP server is available (HTTP ${HTTP_CODE})${NC}"
        MCP_AVAILABLE=true
        break
    fi
    
    if [ $i -eq 30 ]; then
        echo -e "${RED}Error: MCP server not responding after 30 seconds${NC}"
        echo "Expected HTTP 200/404/405, got: ${HTTP_CODE}"
        echo ""
        echo "Troubleshooting:"
        echo "  1. Check MCP server is running:"
        echo "     ./scripts/run_mcp.sh"
        echo "  2. Verify MCP port: ${MCP_PORT}"
        echo "  3. Check MCP logs if using test runner"
        exit 1
    fi
    
    sleep 1
done

# Build MCPO command
CMD="uv tool run mcpo --port ${MCPO_PORT} --server-type streamable-http"

# Add API key only if provided (omit entirely for no-auth/JWT-passthrough mode)
if [[ -n "${MCPO_API_KEY}" ]]; then
    CMD="${CMD} --api-key ${MCPO_API_KEY}"
    echo -e "${GREEN}✓ MCPO API key authentication enabled${NC}"
else
    echo -e "${YELLOW}⚠️  MCPO authentication disabled${NC}"
    echo "   JWT tokens will pass through to MCP server for group-based security"
fi

CMD="${CMD} -- ${MCP_URL}"

# Display connection information
echo ""
echo -e "${GREEN}=== MCPO Ready ===${NC}"
echo "OpenAPI Spec: http://localhost:${MCPO_PORT}/openapi.json"
echo "Health Check: http://localhost:${MCPO_PORT}/health"
echo "Service URL:  http://localhost:${MCPO_PORT}/gplot-renderer"
echo ""
echo "Example usage:"
echo "  curl http://localhost:${MCPO_PORT}/health"
echo "  curl http://localhost:${MCPO_PORT}/openapi.json | jq"
echo ""
echo "Starting MCPO..."
echo "Command: ${CMD}"
echo ""

# Execute MCPO with proper signal handling
exec ${CMD}
