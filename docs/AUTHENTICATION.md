# JWT Authentication Guide

## Overview

gplot uses JWT (JSON Web Tokens) for authentication and group-based access control. Each JWT token is associated with a specific group, and rendered images are segregated by group to ensure secure isolation.

## Key Concepts

- **JWT Token**: A cryptographic token that identifies and authenticates API requests
- **Group**: A logical namespace for organizing and isolating rendered images
- **Token Expiry**: Each token has a configurable expiration date (default: 30 days)
- **Group Segregation**: Images rendered by one group cannot be accessed by tokens from other groups

## Quick Start

### 1. Set JWT Secret (Production)

For production use, set a secure JWT secret key:

```bash
export GPLOT_JWT_SECRET="your-secure-secret-key-here"
```

**Important**: Use a strong, random secret in production. You can generate one with:

```bash
python3 -c "import os; print(os.urandom(32).hex())"
```

### 2. Create a Token

```bash
# Create a token for the 'research' group
python3 scripts/token_manager.py create --group research --expires 30
```

Output:
```
✓ JWT Token Created Successfully

Group:      research
Expires:    30 days

Token:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJncm91cCI6InJlc2VhcmNoIiwiaWF0IjoxNzAwMTIzNDU2LCJleHAiOjE3MDI3MTU0NTZ9.xxx

Save this token securely. Use it in the 'Authorization: Bearer <token>' header.
Or pass it as the 'token' parameter in MCP tool calls.
```

### 3. Use the Token

#### Web API (REST)

```bash
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "title": "My Graph",
    "x": [1, 2, 3, 4, 5],
    "y": [2, 4, 6, 8, 10]
  }'
```

#### MCP Server

```json
{
  "title": "My Graph",
  "x": [1, 2, 3, 4, 5],
  "y": [2, 4, 6, 8, 10],
  "token": "YOUR_TOKEN_HERE"
}
```

## Token Management

### Create Token

```bash
# Create token with default 30-day expiry
python3 scripts/token_manager.py create --group mygroup

# Create token with custom expiry
python3 scripts/token_manager.py create --group mygroup --expires 90
```

### List Tokens

```bash
python3 scripts/token_manager.py list
```

Output:
```
3 Token(s) Found:

Group                Issued                    Expires                   Token (first 20 chars)
----------------------------------------------------------------------------------------------------
research             2024-11-11 14:30         2024-12-11 14:30         eyJhbGciOiJIUzI1NiI...
development          2024-11-10 09:15         2024-12-10 09:15         eyJhbGciOiJIUzI1NiI...
production           2024-11-09 16:45         2025-02-07 16:45         eyJhbGciOiJIUzI1NiI...
```

### Verify Token

```bash
python3 scripts/token_manager.py verify --token YOUR_TOKEN_HERE
```

Output:
```
✓ Token is valid

Group:      research
Issued:     2024-11-11 14:30:00 UTC
Expires:    2024-12-11 14:30:00 UTC
```

### Revoke Token

```bash
python3 scripts/token_manager.py revoke --token YOUR_TOKEN_HERE
```

## Server Configuration

### Web Server

```bash
# Start with explicit JWT secret
python3 app/main.py --jwt-secret "your-secret" --token-store /path/to/tokens.json

# Start with env var (recommended)
export GPLOT_JWT_SECRET="your-secret"
python3 app/main.py

# Custom token store location
python3 app/main.py --token-store /secure/path/tokens.json
```

### MCP Server

```bash
# Start with explicit JWT secret
python3 -m app.main_mcp --jwt-secret "your-secret" --token-store /path/to/tokens.json

# Start with env var (recommended)
export GPLOT_JWT_SECRET="your-secret"
python3 -m app.main_mcp
```

**Important**: Both servers must use the same JWT secret and token store to share authentication.

## Group-Based Access Control

### How It Works

1. **Token Creation**: Each token is assigned to a specific group
2. **Image Storage**: When an image is rendered, it's tagged with the token's group
3. **Image Retrieval**: Images can only be retrieved by tokens from the same group

### Example

```bash
# Create tokens for different groups
python3 scripts/token_manager.py create --group team-a
python3 scripts/token_manager.py create --group team-b

# Team A renders an image (proxy mode)
curl -X POST http://localhost:8000/render \
  -H "Authorization: Bearer TEAM_A_TOKEN" \
  -d '{"title": "Team A Data", "x": [1,2,3], "y": [4,5,6], "proxy": true}'
# Returns: "abc-123-def" (GUID)

# Team A can retrieve it
curl http://localhost:8000/render/abc-123-def \
  -H "Authorization: Bearer TEAM_A_TOKEN"
# Success!

# Team B CANNOT retrieve it
curl http://localhost:8000/render/abc-123-def \
  -H "Authorization: Bearer TEAM_B_TOKEN"
# Error: Access denied
```

## Security Best Practices

### 1. Secure Secret Management

```bash
# Generate a strong secret
python3 -c "import os; print(os.urandom(32).hex())"

# Store in environment variable (don't commit to git)
export GPLOT_JWT_SECRET="generated-secret-here"

# Or use a secrets management system (recommended for production)
export GPLOT_JWT_SECRET=$(aws secretsmanager get-secret-value --secret-id gplot-jwt --query SecretString --output text)
```

### 2. Token Storage Security

```bash
# Use a secure location with restricted permissions
mkdir -p /secure/gplot
chmod 700 /secure/gplot

# Start servers with secure token store
python3 -m app.main_web --token-store /secure/gplot/tokens.json
python3 -m app.main_mcp --token-store /secure/gplot/tokens.json

# Set restrictive permissions
chmod 600 /secure/gplot/tokens.json
```

### 3. Token Rotation

```bash
# Regularly rotate tokens (e.g., every 30-90 days)
python3 scripts/token_manager.py create --group mygroup --expires 30

# Revoke old tokens
python3 scripts/token_manager.py revoke --token OLD_TOKEN
```

### 4. Monitoring

```bash
# Regularly audit tokens
python3 scripts/token_manager.py list

# Check for expired tokens and revoke them
python3 scripts/token_manager.py list | grep "EXPIRED"
```

## Troubleshooting

### "Authentication Error: Token has expired"

Your token has passed its expiration date. Create a new token:

```bash
python3 scripts/token_manager.py create --group yourgroup
```

### "Authentication Error: Invalid token"

The token is malformed or signed with a different secret. Verify:

1. The JWT secret matches on both servers
2. The token wasn't truncated when copying
3. The token exists in the token store

```bash
python3 scripts/token_manager.py verify --token YOUR_TOKEN
```

### "Access denied: image belongs to different group"

You're trying to access an image with a token from a different group. This is expected behavior for group isolation.

### "AuthService not initialized"

The server wasn't started with authentication configured. Ensure:

1. JWT secret is set (via env var or --jwt-secret)
2. Server has permission to access token store path

## API Reference

### Web Server Endpoints

All endpoints require the `Authorization: Bearer <token>` header.

#### POST /render

Render a graph and return base64 image or GUID.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Body:**
```json
{
  "title": "My Graph",
  "x": [1, 2, 3],
  "y": [4, 5, 6],
  "proxy": false
}
```

#### GET /proxy/{guid}

Retrieve a rendered image by GUID.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:** Raw image bytes with appropriate Content-Type

#### GET /proxy/{guid}/html

View a rendered image in an HTML page.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:** HTML page with embedded image

### MCP Tools

All tools require a `token` parameter.

#### render_graph

```json
{
  "title": "My Graph",
  "x": [1, 2, 3, 4, 5],
  "y": [2, 4, 6, 8, 10],
  "token": "YOUR_TOKEN_HERE",
  "proxy": false
}
```

#### get_image

```json
{
  "guid": "abc-123-def",
  "token": "YOUR_TOKEN_HERE"
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GPLOT_JWT_SECRET` | JWT signing secret key | Auto-generated (development only) |

**Warning**: Auto-generated secrets are not suitable for production and will change on server restart.

## Token Store Format

Tokens are stored in JSON format:

```json
{
  "eyJhbGci...": {
    "group": "research",
    "issued_at": "2024-11-11T14:30:00",
    "expires_at": "2024-12-11T14:30:00"
  }
}
```

**Location**: Default is `/tmp/gplot_tokens.json`. Configure with `--token-store` option.

## Production Deployment Checklist

- [ ] Set strong `GPLOT_JWT_SECRET` environment variable
- [ ] Use secure token store location with restrictive permissions (600)
- [ ] Configure both web and MCP servers with same secret and token store
- [ ] Set up token rotation policy (30-90 days)
- [ ] Monitor token usage and audit regularly
- [ ] Use HTTPS/TLS for web server in production
- [ ] Back up token store securely
- [ ] Document group naming conventions for your organization
- [ ] Set up monitoring/alerting for authentication failures

---

## Advanced Features

### Token Fingerprinting

Binds tokens to specific devices/clients to prevent token theft and replay attacks.

**How it works:**
- Generates a fingerprint from request context (User-Agent + Client IP)
- Stores fingerprint in JWT `fp` claim during token creation
- Validates fingerprint matches on every token verification

**Usage:**

```python
from app.auth import AuthService

auth = AuthService(secret_key="your-secret")

# Create token with fingerprint
fingerprint = "device-fingerprint-hash"  # Hash of user-agent + IP
token = auth.create_token(
    group="user-group",
    expires_in_seconds=3600,
    fingerprint=fingerprint
)

# Verify token with fingerprint
token_info = auth.verify_token(token, fingerprint=fingerprint)  # ✅ Success

# Attempting to use token from different device fails
different_fp = "different-device-hash"
token_info = auth.verify_token(token, fingerprint=different_fp)  # ❌ Raises ValueError
```

**Automatic Fingerprinting in Middleware:**

```python
from fastapi import Depends, Request
from app.auth import verify_token

@app.get("/protected")
async def protected_route(
    request: Request,  # Required for fingerprinting
    token_info: TokenInfo = Depends(verify_token)
):
    # Token automatically validated with device fingerprint
    return {"group": token_info.group}
```

### Additional JWT Claims

Enhanced tokens include security-focused JWT standard claims:

| Claim | Description | Required | Validated |
|-------|-------------|----------|-----------|
| `iat` | Issued At - timestamp when token created | Yes | Yes |
| `exp` | Expires - timestamp when token expires | Yes | Yes |
| `nbf` | Not Before - token not valid until this time | Yes | Yes |
| `aud` | Audience - intended recipient (`gplot-api`) | Yes | Yes (if present) |
| `jti` | JWT ID - unique token identifier | Optional | No |
| `fp` | Fingerprint - device binding hash | Optional | Yes (if present) |
| `group` | Group - user's group for access control | Yes | Yes |

**Example Token Payload:**

```json
{
  "group": "analytics-team",
  "iat": 1700000000,
  "exp": 1700003600,
  "nbf": 1700000000,
  "aud": "gplot-api",
  "jti": "unique-token-id-123",
  "fp": "a7f3d8e9c2b1..."
}
```

### Token Secret Fingerprinting

The `AuthService` can generate a fingerprint of the JWT secret for verification and auditing purposes:

```python
from app.auth import AuthService

auth = AuthService(secret_key="your-secret")
fingerprint = auth.get_secret_fingerprint()

print(f"Secret fingerprint: {fingerprint}")
# Output: Secret fingerprint: 2cf24dba5fb0a30e...
```

**Use cases:**
- Verify all services use the same JWT secret
- Audit secret rotation
- Debug authentication issues without exposing secret

### Backward Compatibility

The authentication system maintains backward compatibility with older tokens:

- **Legacy tokens**: Tokens without `fp`, `aud`, or `jti` claims still work
- **Optional fingerprinting**: Fingerprint validation only enforced if `fp` claim present
- **Optional audience**: Audience validation only enforced if `aud` claim present
- **Token store**: Both old and new tokens coexist in token store

This ensures smooth transitions during token rotation and system upgrades.

---

## See Also

- **[SECURITY.md](./SECURITY.md)** - Security architecture and best practices
- **[TEST_AUTH.md](./TEST_AUTH.md)** - Authentication testing guide
- **[DEPENDENCY_INJECTION.md](./DEPENDENCY_INJECTION.md)** - Auth service injection patterns
- **[SCRIPTS.md](./SCRIPTS.md)** - Token management scripts
