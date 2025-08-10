#!/bin/bash

# Deployment script for SupplyNexus Fulfillment Service
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
    echo "Usage: ./deploy.sh <environment> <command> [options]"
    echo ""
    echo "Environments:"
    echo "  local        - Local development environment"
    echo "  development  - Development environment"
    echo "  staging      - Staging environment"
    echo "  production   - Production environment"
    echo ""
    echo "Commands:"
    echo "  start        - Start all services"
    echo "  stop         - Stop all services"
    echo "  restart      - Restart all services"
    echo "  logs         - Show logs [service_name]"
    echo "  db-upgrade   - Run database migrations"
    echo "  db-status    - Check database migration status"
    echo "  db-history   - Show migration history"
    echo ""
    echo "Examples:"
    echo "  ./deploy.sh local start"
    echo "  ./deploy.sh development start"
    echo "  ./deploy.sh production db-upgrade"
    echo "  ./deploy.sh staging logs backend"
    echo ""
    echo "Legacy usage (still supported):"
    echo "  ENV_FILE=env.development ./deploy.sh start"
}

# Parse arguments
ENVIRONMENT=""
COMMAND=""
SERVICE_NAME=""

# Check if first argument is environment or legacy ENV_FILE
if [ -n "$ENV_FILE" ]; then
    # Legacy mode: ENV_FILE environment variable
    ENVIRONMENT=$(echo "$ENV_FILE" | sed 's/env\.//')
    COMMAND="${1:-start}"
    if [ "$COMMAND" = "logs" ] && [ -n "$2" ]; then
        SERVICE_NAME="$2"
    fi
else
    # New mode: environment as first argument
    if [ $# -lt 2 ]; then
        show_usage
        exit 1
    fi
    
    ENVIRONMENT="$1"
    COMMAND="$2"
    
    # Handle logs command with optional service name
    if [ "$COMMAND" = "logs" ] && [ -n "$3" ]; then
        SERVICE_NAME="$3"
    fi
fi

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
ENV_FILE_PATH="../environments/$ENV_FILE"
if [ ! -f "$ENV_FILE_PATH" ]; then
    print_error "Environment file $ENV_FILE_PATH not found"
    echo "Please create the environment file first:"
    echo "  cp ../environments/env.example $ENV_FILE_PATH"
    echo "  # Then edit $ENV_FILE_PATH with your actual values"
    exit 1
fi

print_status "Using environment: $ENVIRONMENT (file: $ENV_FILE)"

# Change to docker directory
cd docker

# Function to start services
start_services() {
    print_status "Starting services with environment: $ENVIRONMENT"
    docker-compose up -d
    print_success "Services started successfully"
    
    echo ""
    echo "🎉 Deployment complete! Services are running:"
    echo ""
    echo "  📊 Backend API:        http://localhost:8000"
    echo "  📊 API Documentation:  http://localhost:8000/api/v1/docs"
    echo "  🌸 Flower (Celery):    http://localhost:5555"
    echo "  🗃️  PostgreSQL:        localhost:5432"
    echo "  ⚡ Redis:             localhost:6379"
    echo ""
    echo "To view logs, run:"
    echo "  ./deploy.sh $ENVIRONMENT logs"
}

# Function to stop services
stop_services() {
    print_status "Stopping services..."
    docker-compose down
    print_success "Services stopped successfully"
}

# Function to restart services
restart_services() {
    print_status "Restarting services..."
    docker-compose down
    docker-compose up -d
    print_success "Services restarted successfully"
}

# Function to show logs
show_logs() {
    if [ -z "$SERVICE_NAME" ]; then
        print_status "Showing logs for all services..."
        docker-compose logs -f
    else
        print_status "Showing logs for service: $SERVICE_NAME"
        docker-compose logs -f "$SERVICE_NAME"
    fi
}

# Function to run database migrations
run_db_migrations() {
    print_status "Running database migrations for environment: $ENVIRONMENT"
    cd ..
    ENV_FILE="$ENV_FILE" python scripts/db.py upgrade
    print_success "Database migrations completed"
}

# Function to check database status
check_db_status() {
    print_status "Checking database migration status for environment: $ENVIRONMENT"
    cd ..
    ENV_FILE="$ENV_FILE" python scripts/db.py current
}

# Function to show database history
show_db_history() {
    print_status "Showing database migration history for environment: $ENVIRONMENT"
    cd ..
    ENV_FILE="$ENV_FILE" python scripts/db.py history
}

# Main command handling
case "$COMMAND" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    logs)
        show_logs
        ;;
    db-upgrade)
        run_db_migrations
        ;;
    db-status)
        check_db_status
        ;;
    db-history)
        show_db_history
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        echo "Available commands: start, stop, restart, logs, db-upgrade, db-status, db-history"
        exit 1
        ;;
esac
