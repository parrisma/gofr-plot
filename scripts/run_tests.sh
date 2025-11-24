#!/bin/bash
# gplot Test Runner
# Mirrors doco workflow: consistent auth config, cleanup, optional server start, pytest execution.

set -euo pipefail

# Colors for status output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Locate project root relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# Shared authentication configuration
export GPLOT_JWT_SECRET="test-secret-key-for-secure-testing-do-not-use-in-production"
export GPLOT_TOKEN_STORE="/tmp/gplot_test_tokens.json"
export GPLOT_MCP_PORT="8001"
export GPLOT_WEB_PORT="8000"
export GPLOT_MCPO_PORT="8002"

# Ensure baseline test directories exist
TEST_DATA_ROOT="test/data"
STORAGE_DIR="${TEST_DATA_ROOT}/storage"
AUTH_DIR="${TEST_DATA_ROOT}/auth"
mkdir -p "${STORAGE_DIR}" "${AUTH_DIR}"

print_header() {
    echo -e "${GREEN}=== GPLOT Test Runner ===${NC}"
    echo "Project root: ${PROJECT_ROOT}"al
    echo "JWT Secret: ${GPLOT_JWT_SECRET:0:20}..."
    echo "Token store: ${GPLOT_TOKEN_STORE}"
    echo "MCP Port: ${GPLOT_MCP_PORT}"
    echo "Web Port: ${GPLOT_WEB_PORT}"
    echo "MCPO Port: ${GPLOT_MCPO_PORT}"
    echo "Storage Dir: ${STORAGE_DIR}"
    echo "Auth Dir: ${AUTH_DIR}"
    echo
}

port_in_use() {
    local port=$1
    if command -v lsof >/dev/null 2>&1; then
        lsof -i ":${port}" >/dev/null 2>&1
    elif command -v ss >/dev/null 2>&1; then
        ss -tuln | grep -q ":${port} "
    elif command -v netstat >/dev/null 2>&1; then
        netstat -tuln | grep -q ":${port} "
    else
        timeout 1 bash -c "cat < /dev/null > /dev/tcp/127.0.0.1/${port}" >/dev/null 2>&1
    fi
}

stop_servers() {
    echo "Killing server processes..."
    pkill -9 -f "python.*main_mcp.py" 2>/dev/null || true
    pkill -9 -f "python.*main_web.py" 2>/dev/null || true
    pkill -9 -f "mcpo" 2>/dev/null || true
    
    # Also kill by module invocation pattern
    pkill -9 -f "python.*-m.*app.main_mcp" 2>/dev/null || true
    pkill -9 -f "python.*-m.*app.main_web" 2>/dev/null || true
    
    # Wait for processes to die
    sleep 2
    
    # Verify all dead
    if ps aux | grep -E "python.*(main_mcp|main_web)|mcpo" | grep -v grep >/dev/null 2>&1; then
        echo -e "${RED}WARNING: Some server processes still running after kill attempt${NC}"
        ps aux | grep -E "python.*(main_mcp|main_web)|mcpo" | grep -v grep
        return 1
    else
        echo "All server processes confirmed dead"
        return 0
    fi
}

free_port() {
    local port=$1
    if ! port_in_use "$port"; then
        return 0
    fi

    if command -v lsof >/dev/null 2>&1; then
        lsof -ti ":${port}" | xargs -r kill -9 2>/dev/null || true
    elif command -v ss >/dev/null 2>&1; then
        ss -lptn "sport = :${port}" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d'=' -f2 | xargs -r kill -9 2>/dev/null || true
    elif command -v netstat >/dev/null 2>&1; then
        netstat -tlnp 2>/dev/null | grep ":${port} " | awk '{print $7}' | cut -d'/' -f1 | xargs -r kill -9 2>/dev/null || true
    fi
    sleep 1
}

cleanup_environment() {
    echo -e "${YELLOW}Cleaning up any previous test servers...${NC}"
    if ! stop_servers; then
        echo -e "${RED}Force killing remaining processes...${NC}"
        ps aux | grep -E "python.*(main_mcp|main_web)" | grep -v grep | awk '{print $2}' | xargs -r kill -9 2>/dev/null || true
        sleep 1
        stop_servers || true
    fi

    echo -e "${YELLOW}Purging token store and transient data...${NC}"
    
    # Empty token store (create empty JSON object)
    echo "{}" > "${GPLOT_TOKEN_STORE}" 2>/dev/null || true
    echo "Token store emptied: ${GPLOT_TOKEN_STORE}"
    
    # Clean up other transient data
    rm -f data/sessions/*.json 2>/dev/null || true
    python scripts/storage_manager.py purge --age-days=0 --yes 2>/dev/null || \
        echo "  (storage purge skipped - no existing data)"
    echo -e "${GREEN}Cleanup complete${NC}\n"
}

start_mcp_server() {
    local log_file="${PROJECT_ROOT}/logs/gplot_mcp_test.log"
    echo -e "${YELLOW}Starting MCP server on port ${GPLOT_MCP_PORT}...${NC}"
    
    free_port "${GPLOT_MCP_PORT}"
    
    # Remove stale log file
    rm -f "${log_file}"

    nohup python app/main_mcp.py \
        --port "${GPLOT_MCP_PORT}" \
        --jwt-secret "${GPLOT_JWT_SECRET}" \
        --token-store "${GPLOT_TOKEN_STORE}" \
        --web-url "http://localhost:${GPLOT_WEB_PORT}" \
        --proxy-url-mode url \
        > "${log_file}" 2>&1 &
    MCP_PID=$!
    echo "MCP PID: ${MCP_PID}"

    echo -n "Waiting for MCP server to start"
    for _ in {1..30}; do
        if ! kill -0 ${MCP_PID} 2>/dev/null; then
            echo -e " ${RED}✗${NC}"
            tail -20 "${log_file}"
            return 1
        fi
        if port_in_use "${GPLOT_MCP_PORT}"; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 0.5
    done
    echo -e " ${RED}✗${NC}"
    tail -20 "${log_file}"
    return 1
}

start_web_server() {
    local log_file="${PROJECT_ROOT}/logs/gplot_web_test.log"
    echo -e "${YELLOW}Starting Web server on port ${GPLOT_WEB_PORT}...${NC}"
    
    free_port "${GPLOT_WEB_PORT}"
    
    # Remove stale log file
    rm -f "${log_file}"

    nohup python app/main_web.py \
        --port "${GPLOT_WEB_PORT}" \
        --jwt-secret "${GPLOT_JWT_SECRET}" \
        --token-store "${GPLOT_TOKEN_STORE}" \
        > "${log_file}" 2>&1 &
    WEB_PID=$!
    echo "Web PID: ${WEB_PID}"

    echo -n "Waiting for web server to start"
    for _ in {1..30}; do
        if ! kill -0 ${WEB_PID} 2>/dev/null; then
            echo -e " ${RED}✗${NC}"
            tail -20 "${log_file}"
            return 1
        fi
        if port_in_use "${GPLOT_WEB_PORT}"; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 0.5
    done
    echo -e " ${RED}✗${NC}"
    tail -20 "${log_file}"
    return 1
}

start_mcpo_server() {
    local log_file="${PROJECT_ROOT}/logs/gplot_mcpo_test.log"
    echo -e "${YELLOW}Starting MCPO wrapper on port ${GPLOT_MCPO_PORT}...${NC}"
    
    free_port "${GPLOT_MCPO_PORT}"
    
    # Remove stale log file
    rm -f "${log_file}"
    
    # Wait for MCP server to be available first
    echo -n "Checking MCP server availability"
    for i in {1..30}; do
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${GPLOT_MCP_PORT}/" 2>/dev/null || echo "000")
        if [[ "${HTTP_CODE}" =~ ^(200|404|405)$ ]]; then
            echo -e " ${GREEN}✓${NC}"
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e " ${RED}✗${NC}"
            echo -e "${RED}MCP server not available for MCPO${NC}"
            return 1
        fi
        echo -n "."
        sleep 0.5
    done

    # Start MCPO wrapper (no API key for test mode - JWT passthrough)
    uv tool run mcpo \
        --port "${GPLOT_MCPO_PORT}" \
        --server-type "streamable-http" \
        -- "http://localhost:${GPLOT_MCP_PORT}/mcp" \
        > "${log_file}" 2>&1 &
    MCPO_PID=$!
    echo "MCPO PID: ${MCPO_PID}"

    echo -n "Waiting for MCPO server to start"
    for _ in {1..30}; do
        if ! kill -0 ${MCPO_PID} 2>/dev/null; then
            echo -e " ${RED}✗${NC}"
            tail -20 "${log_file}"
            return 1
        fi
        if port_in_use "${GPLOT_MCPO_PORT}"; then
            # Additional check: verify health endpoint responds
            if curl -s "http://localhost:${GPLOT_MCPO_PORT}/health" >/dev/null 2>&1; then
                echo -e " ${GREEN}✓${NC}"
                return 0
            fi
        fi
        echo -n "."
        sleep 0.5
    done
    echo -e " ${RED}✗${NC}"
    tail -20 "${log_file}"
    return 1
}

print_header

START_SERVERS=false
START_MCPO=false
STOP_ONLY=false
CLEANUP_ONLY=false
PYTEST_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --with-servers|--start-servers)
            START_SERVERS=true
            START_MCPO=true
            shift
            ;;
        --with-mcpo)
            START_SERVERS=true
            START_MCPO=true
            shift
            ;;
        --no-servers|--without-servers)
            START_SERVERS=false
            START_MCPO=false
            shift
            ;;
        --cleanup-only)
            CLEANUP_ONLY=true
            shift
            ;;
        --stop|--stop-servers)
            STOP_ONLY=true
            shift
            ;;
        *)
            PYTEST_ARGS+=("$1")
            shift
            ;;
    esac
done

if [ "$STOP_ONLY" = true ]; then
    echo -e "${YELLOW}Stopping servers and exiting...${NC}"
    stop_servers
    exit 0
fi

if [ "$CLEANUP_ONLY" = true ]; then
    cleanup_environment
    exit 0
fi

cleanup_environment

# Seed default admin token if requested tokens file missing
if [ ! -f "${GPLOT_TOKEN_STORE}" ]; then
    echo -e "${BLUE}Seeding bootstrap token store...${NC}"
    cat <<'JSON' > "${GPLOT_TOKEN_STORE}"
{}
JSON
fi

create_bootstrap_token() {
    python - <<'PY'
import os
from app.auth import AuthService
secret = os.environ["GPLOT_JWT_SECRET"]
store = os.environ["GPLOT_TOKEN_STORE"]
svc = AuthService(secret_key=secret, token_store_path=store)
token = svc.create_token(group="secure", expires_in_seconds=3600)
print(token)
PY
}

MCP_PID=""
WEB_PID=""
MCPO_PID=""
if [ "$START_SERVERS" = true ]; then
    echo -e "${GREEN}=== Starting Test Servers ===${NC}"
    start_mcp_server || { stop_servers; exit 1; }
    start_web_server || { stop_servers; exit 1; }
    start_mcpo_server || { stop_servers; exit 1; }
    echo
fi

echo -e "${GREEN}=== Running Tests ===${NC}"
set +e
if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
    python -m pytest test/ -v
else
    python -m pytest "${PYTEST_ARGS[@]}"
fi
TEST_EXIT_CODE=$?
set -e

if [ "$START_SERVERS" = true ]; then
    echo
    echo -e "${YELLOW}Stopping test servers...${NC}"
    if ! stop_servers; then
        echo -e "${RED}Force killing remaining processes...${NC}"
        ps aux | grep -E "python.*(main_mcp|main_web)" | grep -v grep | awk '{print $2}' | xargs -r kill -9 2>/dev/null || true
        sleep 1
    fi
    # Final verification
    if ps aux | grep -E "python.*(main_mcp|main_web)" | grep -v grep >/dev/null 2>&1; then
        echo -e "${RED}WARNING: Some servers still running after cleanup${NC}"
    fi
fi

# Clean up token store after tests
echo -e "${YELLOW}Cleaning up token store...${NC}"
echo "{}" > "${GPLOT_TOKEN_STORE}" 2>/dev/null || true
echo "Token store emptied"

echo
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}=== Tests Passed ===${NC}"
else
    echo -e "${RED}=== Tests Failed (exit code: ${TEST_EXIT_CODE}) ===${NC}"
    echo "Server logs:"
    echo "  MCP: ${PROJECT_ROOT}/logs/gplot_mcp_test.log"
    echo "  Web: ${PROJECT_ROOT}/logs/gplot_web_test.log"
    if [ "$START_MCPO" = true ]; then
        echo "  MCPO: ${PROJECT_ROOT}/logs/gplot_mcpo_test.log"
    fi
fi

exit $TEST_EXIT_CODE
