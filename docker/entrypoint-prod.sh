#!/bin/bash
set -e

# =======================================================================
# GOFR-PLOT Production Entrypoint
# Runs MCP, MCPO, and Web servers using supervisor
# =======================================================================

# Configuration from environment (with defaults)
export GOFR_PLOT_MCP_PORT="${GOFR_PLOT_MCP_PORT:-8010}"
export GOFR_PLOT_MCPO_PORT="${GOFR_PLOT_MCPO_PORT:-8011}"
export GOFR_PLOT_WEB_PORT="${GOFR_PLOT_WEB_PORT:-8012}"
export GOFR_PLOT_JWT_SECRET="${GOFR_PLOT_JWT_SECRET:?JWT_SECRET is required}"
export GOFR_PLOT_TOKEN_STORE="${GOFR_PLOT_TOKEN_STORE:-/home/gofr-plot/data/auth/tokens.json}"
export GOFR_PLOT_STORAGE_DIR="${GOFR_PLOT_STORAGE_DIR:-/home/gofr-plot/data/storage}"
export GOFR_PLOT_LOG_LEVEL="${GOFR_PLOT_LOG_LEVEL:-INFO}"

# Ensure directories exist
mkdir -p /home/gofr-plot/data/storage
mkdir -p /home/gofr-plot/data/auth
mkdir -p /home/gofr-plot/logs

# Initialize empty token store if it doesn't exist
if [ ! -f "${GOFR_PLOT_TOKEN_STORE}" ]; then
    echo '{"tokens": {}}' > "${GOFR_PLOT_TOKEN_STORE}"
fi

echo "======================================================================="
echo "GOFR-PLOT Production Server Starting"
echo "======================================================================="
echo "MCP Port:     ${GOFR_PLOT_MCP_PORT}"
echo "MCPO Port:    ${GOFR_PLOT_MCPO_PORT}"
echo "Web Port:     ${GOFR_PLOT_WEB_PORT}"
echo "Storage:      ${GOFR_PLOT_STORAGE_DIR}"
echo "Token Store:  ${GOFR_PLOT_TOKEN_STORE}"
echo "Log Level:    ${GOFR_PLOT_LOG_LEVEL}"
echo "======================================================================="

# Generate supervisor config
VENV_BIN="/home/gofr-plot/.venv/bin"

cat > /tmp/supervisord.conf << EOF
[supervisord]
nodaemon=true
logfile=/home/gofr-plot/logs/supervisord.log
pidfile=/tmp/supervisord.pid
loglevel=info

[program:mcp]
command=${VENV_BIN}/python -m app.main_mcp --port ${GOFR_PLOT_MCP_PORT} --jwt-secret "${GOFR_PLOT_JWT_SECRET}" --token-store "${GOFR_PLOT_TOKEN_STORE}" --web-url "http://localhost:${GOFR_PLOT_WEB_PORT}" --proxy-url-mode url
directory=/home/gofr-plot
environment=PYTHONPATH="/home/gofr-plot",PATH="${VENV_BIN}:%(ENV_PATH)s"
autostart=true
autorestart=true
stdout_logfile=/home/gofr-plot/logs/mcp.log
stderr_logfile=/home/gofr-plot/logs/mcp_error.log
priority=10

[program:web]
command=${VENV_BIN}/python -m app.main_web --port ${GOFR_PLOT_WEB_PORT} --jwt-secret "${GOFR_PLOT_JWT_SECRET}" --token-store "${GOFR_PLOT_TOKEN_STORE}"
directory=/home/gofr-plot
environment=PYTHONPATH="/home/gofr-plot",PATH="${VENV_BIN}:%(ENV_PATH)s"
autostart=true
autorestart=true
stdout_logfile=/home/gofr-plot/logs/web.log
stderr_logfile=/home/gofr-plot/logs/web_error.log
priority=20

[program:mcpo]
command=${VENV_BIN}/mcpo --port ${GOFR_PLOT_MCPO_PORT} --server-type streamable-http -- http://localhost:${GOFR_PLOT_MCP_PORT}/mcp
directory=/home/gofr-plot
environment=PATH="${VENV_BIN}:%(ENV_PATH)s"
autostart=true
autorestart=true
startsecs=5
stdout_logfile=/home/gofr-plot/logs/mcpo.log
stderr_logfile=/home/gofr-plot/logs/mcpo_error.log
priority=30
EOF

# Run supervisor
exec supervisord -c /tmp/supervisord.conf
