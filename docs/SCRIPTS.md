# Scripts

This directory contains utility scripts for managing the gplot application.

## Available Scripts

### token_manager.py

JWT token management utility for creating, listing, verifying, and revoking authentication tokens.

**Usage:**

```bash
# Create a token
python3 scripts/token_manager.py create --group mygroup --expires 2592000

# List all tokens
python3 scripts/token_manager.py list

# Verify a token
python3 scripts/token_manager.py verify --token YOUR_TOKEN

# Revoke a token
python3 scripts/token_manager.py revoke --token YOUR_TOKEN
```

**Documentation:**
See [Authentication Guide](./AUTHENTICATION.md) for complete token management documentation.

**Environment Variables:**
- `GPLOT_JWT_SECRET`: JWT secret key (can also use `--secret` option)

**Options:**
- `--secret SECRET`: Override JWT secret key
- `--token-store PATH`: Custom token store location (default: `/tmp/gplot_tokens.json`)
