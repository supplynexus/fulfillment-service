#!/bin/bash

# Database management script using Docker for environments without Python
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Database management script using Docker"
    echo "Usage: ./db-docker.sh <environment> <command> [args...]"
    echo ""
    echo "Environments:"
    echo "  local        - Local development environment"
    echo "  development  - Development environment"
    echo "  staging      - Staging environment"
    echo "  production   - Production environment"
    echo ""
    echo "Commands:"
    echo "  current     - Show current migration version"
    echo "  history     - Show migration history"
    echo "  upgrade     - Upgrade to latest version"
    echo "  downgrade   - Downgrade to previous version"
    echo "  revision    - Create new migration"
    echo "  autogen     - Auto-generate migration from models"
    echo ""
    echo "Examples:"
    echo "  ./db-docker.sh development current"
    echo "  ./db-docker.sh development upgrade"
    echo "  ./db-docker.sh production autogen 'add new table'"
}

# Parse arguments
if [ $# -lt 2 ]; then
    show_usage
    exit 1
fi

ENVIRONMENT="$1"
COMMAND="$2"

# Validate environment
case "$ENVIRONMENT" in
    local|development|staging|production)
        ENV_FILE="env.$ENVIRONMENT"
        ;;
    *)
        print_error "Invalid environment: $ENVIRONMENT"
        echo "Valid environments: local, development, staging, production"
        exit 1
        ;;
esac

# Check if environment file exists
ENV_FILE_PATH="$(dirname "$0")/../environments/$ENV_FILE"
if [ ! -f "$ENV_FILE_PATH" ]; then
    print_error "Environment file $ENV_FILE_PATH not found"
    echo "Please create the environment file first:"
    echo "  cp $(dirname "$0")/../environments/env.example $ENV_FILE_PATH"
    exit 1
fi

print_status "Using environment: $ENVIRONMENT (file: $ENV_FILE)"

# Get the project root directory
PROJECT_ROOT="$(dirname "$0")/../.."
BACKEND_DIR="$PROJECT_ROOT/backend"

# Function to run alembic command in Docker
run_alembic_docker() {
    local alembic_command="$1"
    
    print_status "Running: alembic $alembic_command"
    
    # Build a temporary Docker image for database operations
    docker run --rm \
        -v "$BACKEND_DIR:/app" \
        -v "$ENV_FILE_PATH:/app/.env" \
        -w /app \
        --env-file "$ENV_FILE_PATH" \
        --add-host=host.docker.internal:host-gateway \
        python:3.11-slim \
        bash -c "
            apt-get update && apt-get install -y gcc g++ libpq-dev curl
            pip install --no-cache-dir -r requirements.txt
            # Replace localhost with host.docker.internal for database connections
            export DATABASE_URL=\${DATABASE_URL/localhost/host.docker.internal}
            export DATABASE_URL_SYNC=\${DATABASE_URL_SYNC/localhost/host.docker.internal}
            alembic $alembic_command
        "
}

# Main command handling
case "$COMMAND" in
    current)
        run_alembic_docker "current"
        ;;
    history)
        run_alembic_docker "history"
        ;;
    upgrade)
        run_alembic_docker "upgrade head"
        print_success "Database migrations completed"
        ;;
    downgrade)
        run_alembic_docker "downgrade -1"
        print_success "Database downgrade completed"
        ;;
    revision)
        if [ -z "$3" ]; then
            print_error "Revision message is required"
            echo "Usage: ./db-docker.sh $ENVIRONMENT revision <message>"
            exit 1
        fi
        run_alembic_docker "revision -m \"$3\""
        ;;
    autogen)
        if [ -z "$3" ]; then
            print_error "Autogen message is required"
            echo "Usage: ./db-docker.sh $ENVIRONMENT autogen <message>"
            exit 1
        fi
        run_alembic_docker "revision --autogenerate -m \"$3\""
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        echo "Available commands: current, history, upgrade, downgrade, revision, autogen"
        exit 1
        ;;
esac
