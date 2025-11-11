#!/bin/bash
set -e

# Fix data directory permissions if mounted as volume
if [ -d "/home/gplot/devroot/gplot/data" ]; then
    # Check if we can write to data directory
    if [ ! -w "/home/gplot/devroot/gplot/data" ]; then
        echo "Fixing permissions for /home/gplot/devroot/gplot/data..."
        # This will work if container is started with appropriate privileges
        sudo chown -R gplot:gplot /home/gplot/devroot/gplot/data 2>/dev/null || \
            echo "Warning: Could not fix permissions. Run container with --user $(id -u):$(id -g)"
    fi
fi

# Create subdirectories if they don't exist
mkdir -p /home/gplot/devroot/gplot/data/storage /home/gplot/devroot/gplot/data/auth

# Install/sync Python dependencies if requirements.txt exists
if [ -f "/home/gplot/devroot/gplot/requirements.txt" ]; then
    echo "Syncing Python dependencies..."
    cd /home/gplot/devroot/gplot
    VIRTUAL_ENV=/home/gplot/devroot/gplot/.venv uv pip sync requirements.txt 2>/dev/null || \
        VIRTUAL_ENV=/home/gplot/devroot/gplot/.venv uv pip install -r requirements.txt || \
        echo "Warning: Could not install dependencies"
fi

# Execute the main command
exec "$@"
