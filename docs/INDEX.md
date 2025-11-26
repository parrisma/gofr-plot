# Documentation Index

Complete documentation for the gplot graph rendering service.

## Quick Start

- **[Main README](../README.md)** - Project overview and getting started
- **[Quick Reference](#quick-reference)** - Common tasks and commands

---

## User Guides

### Integration Guides
- **[N8N Integration](./N8N_GUIDE.md)** - Complete N8N workflow automation guide (MCP + REST)
  - MCP Protocol setup
  - HTTP REST API usage
  - Proxy mode workflows
  - Example workflows
  - [N8N Troubleshooting](./N8N_TROUBLESHOOTING.md)

### Authentication & Security
- **[Authentication](./AUTHENTICATION.md)** - JWT tokens, group-based access, advanced features
  - Token creation and management
  - Group isolation
  - Token fingerprinting
  - Secret management
- **[Security](./SECURITY.md)** - Security architecture and best practices

---

## Server & Protocol Documentation

### MCP Protocol
- **[MCP Server](./MCP_README.md)** - Model Context Protocol implementation
  - Protocol details
  - Tool definitions
  - Streamable HTTP transport
- **[MCPO Integration](./MCPO.md)** - OpenAPI proxy layer for LLM tools (OpenWebUI, etc.)

### Storage & Proxy
- **[Proxy Mode](./PROXY_MODE.md)** - GUID-based image storage and retrieval
- **[Image Aliases](./ALIAS.md)** - Human-friendly names for stored images
- **[Storage System](./STORAGE.md)** - Image storage implementation
- **[Data Persistence](./DATA_PERSISTENCE.md)** - Data directory structure

### Monitoring
- **[Ping Endpoint](./PING.md)** - Health check and monitoring

---

## Feature Documentation

### Chart Rendering
- **[Render Engine](./RENDER.md)** - Graph rendering system architecture
- **[Graph Parameters](./GRAPH_PARAMS.md)** - Complete parameter reference
- **[Multi-Dataset Support](./MULTI_DATASET.md)** - Plot up to 5 datasets per chart
- **[Axis Controls](./AXIS_CONTROLS.md)** - Axis limits and tick customization
- **[Themes](./THEMES.md)** - Theme system and custom theme creation

---

## Development & Operations

### Development Setup
- **[Docker Setup](./DOCKER.md)** - Container configuration and deployment
- **[VS Code Launch](./VSCODE_LAUNCH_CONFIGURATIONS.md)** - Debug and run configurations
- **[Scripts](./SCRIPTS.md)** - Utility scripts (token management, etc.)
- **[Dependency Injection](./DEPENDENCY_INJECTION.md)** - Auth service DI patterns

### Infrastructure
- **[Logger](./LOGGER.md)** - Structured logging system
- **[CORS Configuration](./CORS.md)** - Cross-origin resource sharing
- **[WSL Network Access](./WSL_NETWORK_ACCESS.md)** - Windows Subsystem for Linux setup

---

## Testing

### Test Guides
- **[Testing Guide](./TESTING.md)** - Comprehensive testing guide
  - Test runner usage
  - MCP server tests (81 tests)
  - Web server tests (170+ tests)
  - Test organization
- **[Auth Testing](./TEST_AUTH.md)** - Authentication testing guide (60+ tests)

---

## Archives

Historical documents and completed plans:

- **[archive/plans/](./archive/plans/)** - Completed project plans
  - [REFRACTOR_PLAN.md](./archive/plans/REFRACTOR_PLAN.md) - Phase 1-8 refactoring (completed Nov 2025)
  - [IMPROVEMENT_PLAN.md](./archive/plans/IMPROVEMENT_PLAN.md) - Original modernization plan
- **[archive/debugging/](./archive/debugging/)** - Debugging sessions
  - [TEST_DEBUGGING_LEARNINGS.md](./archive/debugging/TEST_DEBUGGING_LEARNINGS.md) - Nov 2025 debugging lessons
- **[archive/snapshots/](./archive/snapshots/)** - Point-in-time snapshots
  - [TEST_COVERAGE_MULTI_DATASET.md](./archive/snapshots/TEST_COVERAGE_MULTI_DATASET.md) - Test coverage snapshot

---

## Quick Reference

### Common Tasks

**Start Servers:**
```bash
# Web server
python app/main_web.py --port 8000

# MCP server
python app/main_mcp.py --port 8001

# With Docker
docker-compose up gplot_dev
```

**Create Token:**
```bash
python scripts/token_manager.py create --group mygroup --expires 30
```

**Run Tests:**
```bash
# All tests with servers
./scripts/run_tests.sh --with-servers

# Unit tests only
./scripts/run_tests.sh --no-servers
```

**Generate Chart:**
```bash
# REST API
curl -X POST http://localhost:8000/render \
  -H "Authorization: Bearer <token>" \
  -d '{"x": [1,2,3], "y": [4,5,6], "title": "Test"}'

# MCP (see N8N_GUIDE.md for examples)
```

### Documentation By Use Case

**I want to...**

- **Integrate with N8N** → [N8N_GUIDE.md](./N8N_GUIDE.md)
- **Set up authentication** → [AUTHENTICATION.md](./AUTHENTICATION.md)
- **Use proxy mode** → [PROXY_MODE.md](./PROXY_MODE.md)
- **Use image aliases** → [ALIAS.md](./ALIAS.md)
- **Customize themes** → [THEMES.md](./THEMES.md)
- **Plot multiple datasets** → [MULTI_DATASET.md](./MULTI_DATASET.md)
- **Deploy with Docker** → [DOCKER.md](./DOCKER.md)
- **Run tests** → [TESTING.md](./TESTING.md)
- **Troubleshoot N8N** → [N8N_TROUBLESHOOTING.md](./N8N_TROUBLESHOOTING.md)
- **Understand security** → [SECURITY.md](./SECURITY.md)

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

1. **Triple Server Architecture**
   - REST API server (port 8000)
   - MCP protocol server (port 8001)
   - MCPO OpenAPI proxy (port 8002)

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
