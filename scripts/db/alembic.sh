#!/bin/bash

# Optimized Alembic script using existing Docker image
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
    echo "Optimized Alembic script using existing Docker image"
    echo "Usage: ./alembic.sh <environment> <command> [args...]"
    echo ""
    echo "Environments:"
    echo "  local        - Local development environment"
    echo "  dev          - Development environment"
    echo "  stg          - Staging environment"
    echo "  prod         - Production environment"
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
    echo "  ./alembic.sh dev current"
    echo "  ./alembic.sh dev upgrade"
    echo "  ./alembic.sh prod autogen 'add new table'"
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
    local|dev|stg|prod)
        ;;
    *)
        print_error "Invalid environment: $ENVIRONMENT"
        echo "Valid environments: local, dev, stg, prod"
        exit 1
        ;;
esac

# Get the project root directory
PROJECT_ROOT="$(dirname "$0")/../.."
BACKEND_DIR="$PROJECT_ROOT/backend"

# Set environment file path based on environment
case "$ENVIRONMENT" in
    local)
        ENV_FILE_PATH="$BACKEND_DIR/.env.local"
        ;;
    dev)
        ENV_FILE_PATH="$BACKEND_DIR/.env.dev"
        ;;
    stg)
        ENV_FILE_PATH="$BACKEND_DIR/.env.stg"
        ;;
    prod)
        ENV_FILE_PATH="$BACKEND_DIR/.env.prod"
        ;;
esac

# Check if environment file exists
if [ ! -f "$ENV_FILE_PATH" ]; then
    print_error "Environment file $ENV_FILE_PATH not found"
    echo "Please ensure backend/.env.dev exists"
    exit 1
fi

print_status "Using environment: $ENVIRONMENT (file: $ENV_FILE_PATH)"

# Function to run alembic command using existing Docker image
run_alembic() {
    local alembic_command="$1"
    
    print_status "Running: alembic $alembic_command"
    
    # Use existing backend image if available, otherwise build
    if docker images | grep -q "backend_backend"; then
        print_status "Using existing backend image"
        docker run --rm \
            -v "$BACKEND_DIR:/app" \
            -v "$ENV_FILE_PATH:/app/.env" \
            -w /app \
            --env-file "$ENV_FILE_PATH" \
            --add-host=host.docker.internal:host-gateway \
            backend_backend:latest \
            alembic $alembic_command
    else
        print_warning "Backend image not found, building temporary image..."
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
                alembic $alembic_command
            "
    fi
}

# Main command handling
case "$COMMAND" in
    current)
        run_alembic "current"
        ;;
    history)
        run_alembic "history"
        ;;
    upgrade)
        run_alembic "upgrade head"
        print_success "Database migrations completed"
        ;;
    downgrade)
        run_alembic "downgrade -1"
        print_success "Database downgrade completed"
        ;;
    revision)
        if [ -z "$3" ]; then
            print_error "Revision message is required"
            echo "Usage: ./alembic.sh $ENVIRONMENT revision <message>"
            exit 1
        fi
        run_alembic "revision -m \"$3\""
        ;;
    autogen)
        if [ -z "$3" ]; then
            print_error "Autogen message is required"
            echo "Usage: ./alembic.sh $ENVIRONMENT autogen <message>"
            exit 1
        fi
        run_alembic "revision --autogenerate -m \"$3\""
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        echo "Available commands: current, history, upgrade, downgrade, revision, autogen"
        exit 1
        ;;
esac
