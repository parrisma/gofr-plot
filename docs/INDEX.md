# Documentation Index

Complete documentation for the gplot graph rendering service.

## Quick Start

- [Main README](../README.md) - Project overview and getting started

## Core Documentation

### Server and Protocol
- [MCP Server](./MCP_README.md) - Model Context Protocol implementation
- [N8N MCP Integration](./README_N8N_MCP.md) - Integration with N8N workflow automation
- [Proxy Mode](./PROXY_MODE.md) - GUID-based image storage and retrieval
- [Ping Endpoint](./PING.md) - Health check and monitoring

### Security
- [Authentication](./AUTHENTICATION.md) - JWT authentication and group-based access control

### Data Management
- [Data Persistence](./DATA_PERSISTENCE.md) - Data directory structure and configuration
- [Storage System](./STORAGE.md) - Image storage implementation

## Component Documentation

### Rendering System
- [Render Engine](./RENDER.md) - Graph rendering system details
- [Graph Parameters](./GRAPH_PARAMS.md) - GraphParams model and validation
- [Themes](./THEMES.md) - Theme system and custom theme creation

### Infrastructure
- [Logger](./LOGGER.md) - Structured logging system
- [Scripts](./SCRIPTS.md) - Utility scripts (token management, etc.)

## Development

### Docker
- [Docker Setup](./DOCKER.md) - Container configuration, building, and deployment

### VS Code
- [Launch Configurations](./VSCODE_LAUNCH_CONFIGURATIONS.md) - Debug and run configurations

## Testing

- [MCP Tests](./TEST_MCP.md) - MCP server testing guide
- [Web Tests](./TEST_WEB.md) - Web server testing guide
- [Auth Tests](./TEST_AUTH.md) - Authentication testing guide

## Architecture Overview

```
gplot/
├── app/                    # Application code
│   ├── auth/              # Authentication system
│   ├── graph_params/      # Graph parameter definitions
│   ├── logger/            # Logging infrastructure
│   ├── render/            # Graph rendering engine
│   ├── storage/           # Image storage backend
│   ├── themes/            # Theme definitions
│   ├── config.py          # Configuration management
│   ├── main_web.py        # Web server entry point
│   └── main_mcp.py        # MCP server entry point
├── data/                  # Persistent data (volumes)
│   ├── auth/             # JWT tokens
│   └── storage/          # Rendered images
├── docker/               # Docker configurations
├── docs/                 # Documentation
├── scripts/              # Utility scripts
└── test/                 # Test suites
    ├── auth/            # Authentication tests
    ├── mcp/             # MCP server tests
    └── web/             # Web server tests
```

## Key Features

1. **Dual Server Architecture**
   - REST API server (port 8000)
   - MCP protocol server (port 8001)

2. **Flexible Rendering**
   - Multiple chart types (line, bar, scatter)
   - Customizable themes
   - Multiple output formats (PNG, SVG, PDF)

3. **Enterprise Security**
   - JWT-based authentication
   - Group-based access control
   - Token management utilities

4. **Modern Infrastructure**
   - Docker containerization
   - Persistent data volumes
   - UV package management

5. **Comprehensive Testing**
   - Unit tests for all components
   - Integration tests
   - Manual testing scripts

## Getting Help

- Check the [Main README](../README.md) for basic usage
- See component-specific docs for detailed information
- Review test documentation for examples
- Check Docker docs for deployment guidance
