# Docker Setup for gplot

This directory contains Docker configurations for the gplot graph rendering service.

## Architecture

The Docker setup uses a multi-stage approach with UV for Python package management:

1. **Base Image** (`gplot_base`): Ubuntu 22.04 with Python 3.11 and UV installed
2. **Development Image** (`gplot_dev`): Includes Git, GitHub CLI, SSH for VS Code remote development
3. **Production Image** (`gplot_prod`): Minimal image with only runtime dependencies

## Prerequisites

- Docker installed and running
- For development: Your project should be at `~/devroot/gplot`

## Building Images

### 1. Build Base Image (Required First)

```bash
cd /home/parris3142/devroot/gplot
./docker/build-base.sh
```

This creates the `gplot_base:latest` image with Python 3.11 and UV.

### 2. Build Development Image

```bash
./docker/build-dev.sh
```

This creates the `gplot_dev:latest` image configured for VS Code remote development. The build script automatically uses your current user's UID and GID to avoid permission issues.

### 3. Build Production Image

```bash
./docker/build-prod.sh
```

This creates the `gplot_prod:latest` image with the application installed via UV and pyproject.toml.

## Running Containers

### Development Container

```bash
./docker/run-dev.sh
```

This will:
- Stop and remove any existing `gplot_dev` container
- Start a new container named `gplot_dev`
- Mount your local `~/devroot/gplot` directory to `/home/gplot/devroot/gplot`
- Mount your `~/.ssh` directory (read-only) for Git authentication
- Expose port 8000 for the web server

**Connecting to the dev container:**

From terminal:
```bash
docker exec -it gplot_dev /bin/bash
```

From VS Code:
1. Install the "Dev Containers" extension
2. Click the remote connection icon (bottom left)
3. Select "Attach to Running Container"
4. Choose `gplot_dev`

### Production Container

Run the MCP server:
```bash
docker run -d --name gplot_prod -p 8000:8000 gplot_prod:latest
```

Run the web server:
```bash
docker run -d --name gplot_prod -p 8000:8000 gplot_prod:latest python -m app.web_server
```

## Using UV Inside Containers

### Development Container

Once inside the dev container, install dependencies from pyproject.toml:

```bash
# Sync dependencies (install/update)
uv sync

# Install the project in editable mode
uv pip install -e .

# Add a new dependency
uv add <package-name>

# Add a dev dependency
uv add --dev <package-name>

# Run the MCP server
python -m app.mcp_server

# Run the web server
python -m app.main
```

### Production Container

Dependencies are pre-installed during the image build. The production image is ready to run immediately.

## Project Structure Inside Containers

### Development Container
```
/home/gplot/
├── devroot/gplot/          # Your mounted project directory
│   ├── app/
│   ├── docker/
│   ├── pyproject.toml
│   └── ...
├── .venv/                  # UV virtual environment
└── .ssh/                   # Your SSH keys (read-only)
```

### Production Container
```
/home/gplot/
├── app/                    # Application code
├── pyproject.toml          # Project configuration
└── .venv/                  # UV virtual environment with installed deps
```

## Environment Variables

The containers use these environment variables:

- `VIRTUAL_ENV=/home/gplot/.venv`
- `PATH=/home/gplot/.venv/bin:$PATH`

This ensures all Python commands use the UV-managed virtual environment.

## Permissions

- Development container runs as user `gplot` with your host UID/GID
- Production container runs as user `gplot` with system-allocated UID/GID
- This prevents permission issues with mounted volumes in development

## Rebuilding

If you modify dependencies in `pyproject.toml`:

**Development**: Just run `uv sync` inside the container
**Production**: Rebuild the production image with `./docker/build-prod.sh`

## Troubleshooting

### Permission Issues
- Make sure your host directory is at `~/devroot/gplot`
- The dev build script uses your current UID/GID

### UV Not Found
- Rebuild the base image: `./docker/build-base.sh`
- Verify UV is in PATH: `echo $PATH` inside container

### Dependencies Not Installing
- Check `pyproject.toml` syntax
- Try: `uv pip install --verbose -e .`
- View UV logs: `uv pip install --verbose <package>`

### Container Won't Start
- Check if port 8000 is already in use: `lsof -i :8000`
- View container logs: `docker logs gplot_dev`

## Cleaning Up

Remove all gplot containers and images:

```bash
# Stop and remove containers
docker stop gplot_dev gplot_prod 2>/dev/null
docker rm gplot_dev gplot_prod 2>/dev/null

# Remove images
docker rmi gplot_prod:latest gplot_dev:latest gplot_base:latest
```
