#!/usr/bin/env python3
"""JWT Token Management CLI

Command-line utility to create, list, and revoke JWT tokens for gplot authentication.
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.auth import AuthService
from app.logger import ConsoleLogger
import logging


def create_token(args):
    """Create a new JWT token"""
    logger = ConsoleLogger(name="token_manager", level=logging.INFO)

    # Initialize auth service
    auth_service = AuthService(
        secret_key=args.secret or os.environ.get("GPLOT_JWT_SECRET"),
        token_store_path=args.token_store,
    )

    try:
        token = auth_service.create_token(group=args.group, expires_in_seconds=args.expires)

        # Convert seconds to human-readable format
        days = args.expires // 86400
        hours = (args.expires % 86400) // 3600
        minutes = (args.expires % 3600) // 60

        expiry_str = []
        if days > 0:
            expiry_str.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            expiry_str.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            expiry_str.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if not expiry_str:
            expiry_str.append(f"{args.expires} second{'s' if args.expires != 1 else ''}")

        print(f"\n✓ JWT Token Created Successfully\n")
        print(f"Group:      {args.group}")
        print(f"Expires:    {', '.join(expiry_str)} ({args.expires} seconds)")
        print(f"\nToken:")
        print(f"{token}\n")
        print(f"Save this token securely. Use it in the 'Authorization: Bearer <token>' header.")
        print(f"Or pass it as the 'token' parameter in MCP tool calls.\n")

        return 0
    except Exception as e:
        print(f"\n✗ Error creating token: {str(e)}\n", file=sys.stderr)
        return 1


def list_tokens(args):
    """List all tokens"""
    logger = ConsoleLogger(name="token_manager", level=logging.INFO)

    # Initialize auth service
    auth_service = AuthService(
        secret_key=args.secret or os.environ.get("GPLOT_JWT_SECRET"),
        token_store_path=args.token_store,
    )

    try:
        tokens = auth_service.list_tokens()

        if not tokens:
            print("\nNo tokens found.\n")
            return 0

        print(f"\n{len(tokens)} Token(s) Found:\n")
        print(f"{'Group':<20} {'Issued':<25} {'Expires':<25} {'Token (first 20 chars)'}")
        print("-" * 100)

        for token, info in tokens.items():
            group = info.get("group", "N/A")
            issued = info.get("issued_at", "N/A")
            expires = info.get("expires_at", "N/A")

            # Parse dates if possible
            try:
                issued_dt = datetime.fromisoformat(issued)
                issued_str = issued_dt.strftime("%Y-%m-%d %H:%M")
            except:
                issued_str = issued[:16] if len(issued) > 16 else issued

            try:
                expires_dt = datetime.fromisoformat(expires)
                expires_str = expires_dt.strftime("%Y-%m-%d %H:%M")

                # Check if expired
                if expires_dt < datetime.utcnow():
                    expires_str += " (EXPIRED)"
            except:
                expires_str = expires[:16] if len(expires) > 16 else expires

            token_preview = token[:20] + "..."
            print(f"{group:<20} {issued_str:<25} {expires_str:<25} {token_preview}")

        print()
        return 0
    except Exception as e:
        print(f"\n✗ Error listing tokens: {str(e)}\n", file=sys.stderr)
        return 1


def revoke_token(args):
    """Revoke a token"""
    logger = ConsoleLogger(name="token_manager", level=logging.INFO)

    # Initialize auth service
    auth_service = AuthService(
        secret_key=args.secret or os.environ.get("GPLOT_JWT_SECRET"),
        token_store_path=args.token_store,
    )

    try:
        auth_service.revoke_token(args.token)
        print(f"\n✓ Token revoked successfully\n")
        return 0
    except Exception as e:
        print(f"\n✗ Error revoking token: {str(e)}\n", file=sys.stderr)
        return 1


def verify_token(args):
    """Verify a token"""
    logger = ConsoleLogger(name="token_manager", level=logging.INFO)

    # Initialize auth service
    auth_service = AuthService(
        secret_key=args.secret or os.environ.get("GPLOT_JWT_SECRET"),
        token_store_path=args.token_store,
    )

    try:
        token_info = auth_service.verify_token(args.token)

        print(f"\n✓ Token is valid\n")
        print(f"Group:      {token_info.group}")
        print(f"Issued:     {token_info.issued_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Expires:    {token_info.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        # Check if close to expiry
        now = datetime.utcnow()
        days_until_expiry = (token_info.expires_at - now).days
        if days_until_expiry < 7:
            print(f"\n⚠ Warning: Token expires in {days_until_expiry} days")

        print()
        return 0
    except Exception as e:
        print(f"\n✗ Token validation failed: {str(e)}\n", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="gplot JWT Token Manager - Create and manage authentication tokens",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a token for the 'research' group that expires in 30 days (2592000 seconds)
  python token_manager.py create --group research --expires 2592000

  # Create a token that expires in 1 hour
  python token_manager.py create --group research --expires 3600

  # List all tokens
  python token_manager.py list

  # Verify a token
  python token_manager.py verify --token eyJhbGc...

  # Revoke a token
  python token_manager.py revoke --token eyJhbGc...

Environment Variables:
  GPLOT_JWT_SECRET    JWT secret key (can also use --secret option)
        """,
    )

    parser.add_argument(
        "--secret", type=str, help="JWT secret key (default: GPLOT_JWT_SECRET env var)"
    )
    parser.add_argument(
        "--token-store",
        type=str,
        default=None,
        help="Path to token store file (default: /tmp/gplot_tokens.json)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create token
    create_parser = subparsers.add_parser("create", help="Create a new JWT token")
    create_parser.add_argument(
        "--group", type=str, required=True, help="Group name to associate with this token"
    )
    create_parser.add_argument(
        "--expires",
        type=int,
        default=2592000,
        help="Number of seconds until token expires (default: 2592000 = 30 days)",
    )

    # List tokens
    list_parser = subparsers.add_parser("list", help="List all tokens")

    # Revoke token
    revoke_parser = subparsers.add_parser("revoke", help="Revoke a token")
    revoke_parser.add_argument("--token", type=str, required=True, help="Token to revoke")

    # Verify token
    verify_parser = subparsers.add_parser("verify", help="Verify a token")
    verify_parser.add_argument("--token", type=str, required=True, help="Token to verify")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == "create":
        return create_token(args)
    elif args.command == "list":
        return list_tokens(args)
    elif args.command == "revoke":
        return revoke_token(args)
    elif args.command == "verify":
        return verify_token(args)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
