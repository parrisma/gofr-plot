#!/bin/bash
set -e

# Standard GOFR user paths - all projects use 'gofr' user
GOFR_USER="gofr"
PROJECT_DIR="/home/${GOFR_USER}/devroot/gofr-plot"
# gofr-common is now a git submodule in lib/gofr-common
COMMON_DIR="$PROJECT_DIR/lib/gofr-common"
VENV_DIR="$PROJECT_DIR/.venv"

echo "======================================================================="
echo "GOFR-PLOT Container Entrypoint"
echo "======================================================================="

# Fix data directory permissions if mounted as volume
if [ -d "$PROJECT_DIR/data" ]; then
    if [ ! -w "$PROJECT_DIR/data" ]; then
        echo "Fixing permissions for $PROJECT_DIR/data..."
        sudo chown -R ${GOFR_USER}:${GOFR_USER} "$PROJECT_DIR/data" 2>/dev/null || \
            echo "Warning: Could not fix permissions. Run container with --user $(id -u):$(id -g)"
    fi
fi

# Configure Docker socket access
if [ -S /var/run/docker.sock ]; then
    echo "Configuring Docker socket access..."
    # Use provided GID or fallback to socket's GID
    TARGET_GID=${DOCKER_GID:-$(stat -c '%g' /var/run/docker.sock)}
    
    # Check if a group with this GID already exists
    if ! getent group "$TARGET_GID" >/dev/null; then
        echo "Creating docker-host group with GID $TARGET_GID"
        sudo groupadd -g "$TARGET_GID" docker-host
    fi
    
    # Add user to the group (whether it existed or we just created it)
    # We use the GID directly to be safe
    echo "Adding user $GOFR_USER to group with GID $TARGET_GID"
    sudo usermod -aG "$TARGET_GID" "$GOFR_USER"
fi

# Create subdirectories if they don't exist
mkdir -p "$PROJECT_DIR/data/storage" "$PROJECT_DIR/data/auth"
mkdir -p "$PROJECT_DIR/logs"

# Ensure virtual environment exists and is valid
if [ ! -f "$VENV_DIR/bin/python" ] || [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "Creating Python virtual environment..."
    cd "$PROJECT_DIR"
    UV_VENV_CLEAR=1 uv venv "$VENV_DIR" --python=python3.11
    echo "Virtual environment created at $VENV_DIR"
fi

# Install gofr-common as editable package
if [ -d "$COMMON_DIR" ]; then
    echo "Installing gofr-common (editable)..."
    cd "$PROJECT_DIR"
    uv pip install -e "$COMMON_DIR"
else
    echo "Warning: gofr-common not found at $COMMON_DIR"
    echo "Make sure the submodule is initialized: git submodule update --init"
fi

# Install project dependencies
if [ -f "$PROJECT_DIR/pyproject.toml" ]; then
    echo "Installing project dependencies from pyproject.toml..."
    cd "$PROJECT_DIR"
    uv pip install -e ".[dev]" || echo "Warning: Could not install project dependencies"
elif [ -f "$PROJECT_DIR/requirements.txt" ]; then
    echo "Installing project dependencies from requirements.txt..."
    cd "$PROJECT_DIR"
    uv pip install -r requirements.txt || echo "Warning: Could not install project dependencies"
fi

# Show installed packages
echo ""
echo "Environment ready. Installed packages:"
uv pip list

echo ""
echo "======================================================================="
echo "Entrypoint complete. Executing: $@"
echo "======================================================================="

exec "$@"
