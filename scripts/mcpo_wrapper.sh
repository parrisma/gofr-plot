#!/bin/bash
# gplot MCPO Flexible Wrapper
# Supports both authentication modes with environment variables and CLI arguments.
# Can start MCPO in public mode (JWT passthrough) or with MCPO API key.

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

# Default configuration
MODE="${GPLOT_MCPO_MODE:-public}"
MCPO_PORT="${GPLOT_MCPO_PORT:-8002}"
MCP_PORT="${GPLOT_MCP_PORT:-8001}"
MCPO_API_KEY="${GPLOT_MCPO_API_KEY:-changeme}"
JWT_TOKEN="${GPLOT_JWT_TOKEN:-}"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --mcp-port)
            MCP_PORT="$2"
            shift 2
            ;;
        --mcpo-port)
            MCPO_PORT="$2"
            shift 2
            ;;
        --api-key)
            MCPO_API_KEY="$2"
            shift 2
            ;;
        --jwt-token)
            JWT_TOKEN="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Flexible MCPO wrapper with environment variable and CLI argument support."
            echo ""
            echo "Options:"
            echo "  --mode MODE           Authentication mode: 'auth' or 'public' (default: public)"
            echo "  --mcp-port PORT       MCP server port (default: 8001)"
            echo "  --mcpo-port PORT      MCPO proxy port (default: 8002)"
            echo "  --api-key KEY         MCPO API key for OpenWebUI (default: changeme)"
            echo "  --jwt-token TOKEN     JWT token for MCP auth (required for auth mode)"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  GPLOT_MCPO_MODE       Authentication mode (default: public)"
            echo "  GPLOT_MCP_PORT        MCP server port (default: 8001)"
            echo "  GPLOT_MCPO_PORT       MCPO proxy port (default: 8002)"
            echo "  GPLOT_MCPO_API_KEY    MCPO API key (default: changeme)"
            echo "  GPLOT_JWT_TOKEN       JWT token for MCP auth"
            echo ""
            echo "Modes:"
            echo "  public - JWT tokens pass through to MCP (group-based security)"
            echo "  auth   - Use MCPO API key + JWT token for MCP backend"
            echo ""
            echo "Examples:"
            echo "  # Public mode (JWT passthrough)"
            echo "  bash scripts/mcpo_wrapper.sh"
            echo ""
            echo "  # Authenticated mode"
            echo "  bash scripts/mcpo_wrapper.sh --mode auth --jwt-token \"your-token\""
            echo ""
            echo "  # Custom ports"
            echo "  bash scripts/mcpo_wrapper.sh --mcp-port 8001 --mcpo-port 8002"
            echo ""
            echo "  # Using environment variables"
            echo "  export GPLOT_MCPO_MODE=auth"
            echo "  export GPLOT_JWT_TOKEN=\"your-token\""
            echo "  bash scripts/mcpo_wrapper.sh"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate mode
if [[ "${MODE}" != "public" && "${MODE}" != "auth" ]]; then
    echo -e "${RED}Error: Invalid mode '${MODE}'. Use 'public' or 'auth'${NC}"
    exit 1
fi

# Validate auth mode requirements
if [[ "${MODE}" == "auth" && -z "${JWT_TOKEN}" ]]; then
    echo -e "${RED}Error: JWT token required for auth mode${NC}"
    echo "Provide via --jwt-token or GPLOT_JWT_TOKEN environment variable"
    exit 1
fi

# Display startup information
echo -e "${BLUE}=== Starting gplot MCPO Wrapper ===${NC}"
echo "Mode:         ${MODE}"
echo "MCPO Port:    ${MCPO_PORT}"
echo "MCP Port:     ${MCP_PORT}"

if [[ "${MODE}" == "auth" ]]; then
    echo "MCPO API Key: ${MCPO_API_KEY:0:10}..."
    echo "JWT Token:    ${JWT_TOKEN:0:20}..."
else
    echo -e "${YELLOW}JWT Passthrough: Enabled${NC}"
fi

echo ""

# Check for stale processes on MCPO port
if command -v lsof >/dev/null 2>&1; then
    if lsof -i ":${MCPO_PORT}" >/dev/null 2>&1; then
        echo -e "${YELLOW}Port ${MCPO_PORT} is already in use:${NC}"
        lsof -i ":${MCPO_PORT}"
        echo ""
        read -p "Kill existing process and continue? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            lsof -ti ":${MCPO_PORT}" | xargs kill -9 2>/dev/null || true
            sleep 1
        else
            exit 1
        fi
    fi
fi

# Wait for MCP server availability
MCP_URL="http://localhost:${MCP_PORT}/mcp"
echo "Waiting for MCP server at ${MCP_URL}..."
MCP_AVAILABLE=false
for i in {1..30}; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${MCP_PORT}/" 2>/dev/null || echo "000")
    if [[ "${HTTP_CODE}" =~ ^(200|404|405)$ ]]; then
        echo -e "${GREEN}✓ MCP server is available (HTTP ${HTTP_CODE})${NC}"
        MCP_AVAILABLE=true
        break
    fi
    
    if [ $i -eq 30 ]; then
        echo -e "${RED}Error: MCP server not responding after 30 seconds${NC}"
        echo "Expected HTTP 200/404/405, got: ${HTTP_CODE}"
        exit 1
    fi
    
    sleep 1
done

# Build MCPO command based on mode with debug logging enabled
CMD="uv tool run mcpo --port ${MCPO_PORT} --server-type streamable-http --log-level debug"

if [[ "${MODE}" == "auth" ]]; then
    CMD="${CMD} --api-key ${MCPO_API_KEY}"
    # In auth mode, JWT token would be used when calling MCP tools
    # The wrapper itself uses API key, tools pass JWT to MCP
fi

CMD="${CMD} -- ${MCP_URL}"

# Display connection information
echo ""
echo -e "${GREEN}=== MCPO Ready ===${NC}"
echo "OpenAPI Spec: http://localhost:${MCPO_PORT}/openapi.json"
echo "Health Check: http://localhost:${MCPO_PORT}/health"
echo ""

if [[ "${MODE}" == "auth" ]]; then
    echo "Authentication: MCPO API Key + MCP JWT Token"
    echo "Example:"
    echo "  curl -H 'X-API-Key: ${MCPO_API_KEY}' \\"
    echo "       http://localhost:${MCPO_PORT}/ping"
else
    echo "Authentication: JWT Passthrough to MCP"
    echo "Example:"
    echo "  curl -X POST http://localhost:${MCPO_PORT}/render_graph \\"
    echo "       -H 'Content-Type: application/json' \\"
    echo "       -d '{\"token\":\"<jwt>\",\"title\":\"Test\",\"y1\":[1,2,3]}'"
fi

echo ""
echo "Starting MCPO..."
echo "Command: ${CMD}"
echo ""

# Execute MCPO with proper signal handling
exec ${CMD}
