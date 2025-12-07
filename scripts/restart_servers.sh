#!/bin/bash
# GOFR-PLOT Server Restart Script
# Wrapper for the shared restart_servers.sh script
#
# Usage: ./restart_servers.sh [--kill-all]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMMON_SCRIPTS="$PROJECT_ROOT/../gofr-common/scripts"

# Check for lib/gofr-common location first (inside container)
if [ -d "$PROJECT_ROOT/lib/gofr-common/scripts" ]; then
    COMMON_SCRIPTS="$PROJECT_ROOT/lib/gofr-common/scripts"
fi

# Source centralized environment configuration
if [ -f "${PROJECT_ROOT}/gofr-plot.env" ]; then
    source "${PROJECT_ROOT}/gofr-plot.env"
fi

# Default to PROD for restart script
export GOFR_PLOT_ENV="${GOFR_PLOT_ENV:-PROD}"

# Re-source to pick up PROD paths
if [ -f "${PROJECT_ROOT}/gofr-plot.env" ]; then
    source "${PROJECT_ROOT}/gofr-plot.env"
fi

# Map project-specific vars to common vars
export GOFR_PROJECT_NAME="gofr-plot"
export GOFR_PROJECT_ROOT="$GOFR_PLOT_ROOT"
export GOFR_LOGS_DIR="$GOFR_PLOT_LOGS"
export GOFR_DATA_DIR="$GOFR_PLOT_DATA"
export GOFR_ENV="$GOFR_PLOT_ENV"
export GOFR_MCP_PORT="${GOFR_PLOT_MCP_PORT:-8010}"
export GOFR_MCPO_PORT="${GOFR_PLOT_MCPO_PORT:-8011}"
export GOFR_WEB_PORT="${GOFR_PLOT_WEB_PORT:-8012}"
export GOFR_MCP_HOST="${GOFR_PLOT_MCP_HOST:-0.0.0.0}"
export GOFR_MCPO_HOST="${GOFR_PLOT_MCPO_HOST:-0.0.0.0}"
export GOFR_WEB_HOST="${GOFR_PLOT_WEB_HOST:-0.0.0.0}"
export GOFR_NETWORK="$GOFR_PLOT_NETWORK"

# Call shared script
source "$COMMON_SCRIPTS/restart_servers.sh" "$@"
