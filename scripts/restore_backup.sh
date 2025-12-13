#!/bin/bash
#
# Wrapper script for gofr-plot backup operations
# Sets GOFR_PROJECT and calls shared gofr-common scripts
#

export GOFR_PROJECT=plot
export GOFR_BACKUP_CONTAINER=gofr-plot-backup
export GOFR_DATA_VOLUME=gofr-plot_data

# Determine script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_BACKUP_DIR="${SCRIPT_DIR}/../../gofr-common/scripts/backup"

# Check if script exists
SCRIPT_NAME=$(basename "$0")

if [ ! -f "${COMMON_BACKUP_DIR}/${SCRIPT_NAME}" ]; then
    echo "ERROR: Shared script not found: ${COMMON_BACKUP_DIR}/${SCRIPT_NAME}"
    echo "Ensure gofr-common is available at ${COMMON_BACKUP_DIR}"
    exit 1
fi

# Execute the shared script
exec "${COMMON_BACKUP_DIR}/${SCRIPT_NAME}" "$@"
