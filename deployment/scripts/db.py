#!/usr/bin/env python3
"""
Database management script for deployment environments
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.config import settings


def set_environment():
    """Set environment variables for database operations"""
    # Use environment file if specified
    env_file = os.getenv("ENV_FILE", "env.development")
    print(f"📁 Using environment file: {env_file}")
    
    # Load environment variables from file
    env_file_path = Path(__file__).parent.parent / "environments" / env_file
    if env_file_path.exists():
        with open(env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    # Set default database URLs if not already set
    if not os.getenv("DATABASE_URL"):
        os.environ.setdefault("DATABASE_URL", settings.DATABASE_URL)
    
    if not os.getenv("DATABASE_URL_SYNC"):
        database_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        os.environ.setdefault("DATABASE_URL_SYNC", sync_url)


def run_alembic_command(command):
    """Run alembic command with proper environment"""
    set_environment()
    result = subprocess.run(["alembic"] + command, cwd=backend_dir)
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print("Database management script for SupplyNexus Fulfillment Service")
        print("=" * 60)
        print("\nUsage:")
        print("  python deployment/scripts/db.py <command> [args...]")
        print("\nEnvironment (set ENV_FILE environment variable):")
        print("  ENV_FILE=env.development python deployment/scripts/db.py <command>  # Development")
        print("  ENV_FILE=env.staging python deployment/scripts/db.py <command>      # Staging")
        print("  ENV_FILE=env.production python deployment/scripts/db.py <command>   # Production")
        print("\nOr use the deploy.sh script (recommended):")
        print("  ./deployment/scripts/deploy.sh development db-upgrade")
        print("  ./deployment/scripts/deploy.sh production db-status")
        print("\nAvailable commands:")
        print("  current     - Show current migration version")
        print("  history     - Show migration history")
        print("  upgrade     - Upgrade to latest version")
        print("  downgrade   - Downgrade to previous version")
        print("  revision    - Create new migration")
        print("  autogen     - Auto-generate migration from models")
        print("  reset       - Reset database (drop all tables)")
        print("\nExamples:")
        print("  python deployment/scripts/db.py current")
        print("  python deployment/scripts/db.py upgrade")
        print("  python deployment/scripts/db.py autogen 'add new table'")
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
            print("Usage: python deployment/scripts/db.py revision <message>")
            return 1
        return run_alembic_command(["revision", "-m", sys.argv[2]])
    elif command == "autogen":
        if len(sys.argv) < 3:
            print("Usage: python deployment/scripts/db.py autogen <message>")
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
