#!/bin/bash
# Restart all gplot servers in correct order: MCP → MCPO → Web
# Verifies each server is operational before continuing
# Usage: ./restart_servers.sh [--kill-all]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source centralized environment configuration
if [ -f "${PROJECT_ROOT}/gplot.env" ]; then
    source "${PROJECT_ROOT}/gplot.env"
fi

# Default ports (from gplot.env or fallback)
MCP_PORT=${GPLOT_MCP_PORT:-8010}
MCPO_PORT=${GPLOT_MCPO_PORT:-8011}
WEB_PORT=${GPLOT_WEB_PORT:-8012}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================================================="
echo "gplot Server Restart Script"
echo "======================================================================="

# Kill existing processes
echo ""
echo "Step 1: Stopping existing servers..."
echo "-----------------------------------------------------------------------"

# Function to kill process and wait for it to die
kill_and_wait() {
    local pattern=$1
    local name=$2
    local pids=$(pgrep -f "$pattern" 2>/dev/null || echo "")
    
    if [ -z "$pids" ]; then
        echo "  - No $name running"
        return 0
    fi
    
    echo "  Killing $name (PIDs: $pids)..."
    pkill -9 -f "$pattern" 2>/dev/null || true
    
    # Wait for processes to die (max 10 seconds)
    for i in {1..20}; do
        if ! pgrep -f "$pattern" >/dev/null 2>&1; then
            echo "  ✓ $name stopped"
            return 0
        fi
        sleep 0.5
    done
    
    echo "  ⚠ Warning: $name may still be running"
    return 1
}

# Kill servers in reverse order (Web, MCPO, MCP)
kill_and_wait "app.main_web" "Web server"
kill_and_wait "mcpo" "MCPO wrapper"
kill_and_wait "app.main_mcp" "MCP server"

# Wait for ports to be released
echo ""
echo "Waiting for ports to be released..."
sleep 2

# Check if --kill-all flag is set
if [ "$1" == "--kill-all" ]; then
    echo ""
    echo "Kill-all mode: Exiting without restart"
    echo "======================================================================="
    exit 0
fi

# Helper function to verify server is responding
verify_server() {
    local port=$1
    local name=$2
    local endpoint=$3
    local max_attempts=15
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -m 2 "http://localhost:${port}${endpoint}" >/dev/null 2>&1; then
            echo -e "  ${GREEN}✓${NC} $name responding on port $port"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    
    echo -e "  ${RED}✗${NC} $name NOT responding after ${max_attempts}s"
    return 1
}

# Start MCP server
echo ""
echo "Step 2: Starting MCP server (port $MCP_PORT)..."
echo "-----------------------------------------------------------------------"

cd "$PROJECT_ROOT"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"

nohup bash "$SCRIPT_DIR/run_mcp.sh" --port $MCP_PORT > "$PROJECT_ROOT/logs/gplot_mcp.log" 2>&1 &
MCP_PID=$!
echo "  MCP server starting (PID: $MCP_PID)"
echo "  Log: $PROJECT_ROOT/logs/gplot_mcp.log"

# Verify MCP is operational
if ! verify_server $MCP_PORT "MCP Server" "/mcp/"; then
    echo -e "${RED}ERROR: MCP server failed to start${NC}"
    tail -20 "$PROJECT_ROOT/logs/gplot_mcp.log"
    exit 1
fi

# Start MCPO wrapper
echo ""
echo "Step 3: Starting MCPO wrapper (port $MCPO_PORT)..."
echo "-----------------------------------------------------------------------"

nohup bash "$SCRIPT_DIR/run_mcpo.sh" --mcp-port $MCP_PORT --port $MCPO_PORT > "$PROJECT_ROOT/logs/gplot_mcpo.log" 2>&1 &
MCPO_PID=$!
echo "  MCPO wrapper starting (PID: $MCPO_PID)"
echo "  Log: $PROJECT_ROOT/logs/gplot_mcpo.log"

# Verify MCPO is operational
if ! verify_server $MCPO_PORT "MCPO Wrapper" "/openapi.json"; then
    echo -e "${RED}ERROR: MCPO wrapper failed to start${NC}"
    tail -20 "$PROJECT_ROOT/logs/gplot_mcpo.log"
    exit 1
fi

# Start Web server
echo ""
echo "Step 4: Starting Web server (port $WEB_PORT)..."
echo "-----------------------------------------------------------------------"

nohup bash "$SCRIPT_DIR/run_web.sh" --port $WEB_PORT > "$PROJECT_ROOT/logs/gplot_web.log" 2>&1 &
WEB_PID=$!
echo "  Web server starting (PID: $WEB_PID)"
echo "  Log: $PROJECT_ROOT/logs/gplot_web.log"

# Verify Web server is operational
if ! verify_server $WEB_PORT "Web Server" "/ping"; then
    echo -e "${RED}ERROR: Web server failed to start${NC}"
    tail -20 "$PROJECT_ROOT/logs/gplot_web.log"
    exit 1
fi

# Summary
echo ""
echo "======================================================================="
echo -e "${GREEN}✓ All servers started and verified operational!${NC}"
echo "======================================================================="
echo ""
echo "Access URLs:"
echo "  MCP Server:    http://localhost:$MCP_PORT/mcp"
echo "  MCPO Proxy:    http://localhost:$MCPO_PORT"
echo "  Web Server:    http://localhost:$WEB_PORT"
echo ""
echo "Process IDs:"
echo "  MCP:   $MCP_PID"
echo "  MCPO:  $MCPO_PID"
echo "  Web:   $WEB_PID"
echo ""
echo "Logs:"
echo "  MCP:   $PROJECT_ROOT/logs/gplot_mcp.log"
echo "  MCPO:  $PROJECT_ROOT/logs/gplot_mcpo.log"
echo "  Web:   $PROJECT_ROOT/logs/gplot_web.log"
echo ""
echo "To stop all servers: $0 --kill-all"
echo "To view logs: tail -f $PROJECT_ROOT/logs/gplot_*.log"
echo "======================================================================="
