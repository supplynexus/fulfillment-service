#!/usr/bin/env python3
"""
Database management script for SupplyNexus Fulfillment Service
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings


def set_environment():
    """Set environment variables for database operations"""
    # Use environment file if specified
    env_file = os.getenv("ENV_FILE")
    if env_file:
        print(f"📁 Using environment file: {env_file}")
    
    os.environ.setdefault("DATABASE_URL", settings.DATABASE_URL)
    os.environ.setdefault("DATABASE_URL_SYNC", settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))


def run_alembic_command(command):
    """Run alembic command with proper environment"""
    set_environment()
    result = subprocess.run(["alembic"] + command, cwd=backend_dir)
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/db.py <command> [args...]")
        print("\nEnvironment:")
        print("  ENV_FILE=../deployment/environments/env.dev python scripts/db.py <command>  # Use dev env")
        print("  ENV_FILE=../deployment/environments/env.stg python scripts/db.py <command>      # Use staging env")
        print("\nAvailable commands:")
        print("  current     - Show current migration version")
        print("  history     - Show migration history")
        print("  upgrade     - Upgrade to latest version")
        print("  downgrade   - Downgrade to previous version")
        print("  revision    - Create new migration")
        print("  autogen     - Auto-generate migration from models")
        print("  reset       - Reset database (drop all tables)")
        return 1

    command = sys.argv[1]
    
    if command == "current":
        return run_alembic_command(["current"])
    elif command == "history":
        return run_alembic_command(["history"])
    elif command == "upgrade":
        return run_alembic_command(["upgrade", "head"])
    elif command == "downgrade":
        return run_alembic_command(["downgrade", "-1"])
    elif command == "revision":
        if len(sys.argv) < 3:
            print("Usage: python scripts/db.py revision <message>")
            return 1
        return run_alembic_command(["revision", "-m", sys.argv[2]])
    elif command == "autogen":
        if len(sys.argv) < 3:
            print("Usage: python scripts/db.py autogen <message>")
            return 1
        return run_alembic_command(["revision", "--autogenerate", "-m", sys.argv[2]])
    elif command == "reset":
        print("⚠️  This will drop all tables! Are you sure? (y/N)")
        if input().lower() != 'y':
            print("Cancelled.")
            return 0
        return run_alembic_command(["downgrade", "base"])
    else:
        print(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
