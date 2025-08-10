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

# Check if environment file is specified
if [ -z "$ENV_FILE" ]; then
    print_error "ENV_FILE environment variable is required"
    echo "Usage: ENV_FILE=env.development ./deploy.sh [command]"
    echo ""
    echo "Available environments:"
    echo "  env.development  - Development environment"
    echo "  env.staging      - Staging environment"
    echo "  env.production   - Production environment"
    echo ""
    echo "Available commands:"
    echo "  start     - Start all services"
    echo "  stop      - Stop all services"
    echo "  restart   - Restart all services"
    echo "  logs      - Show logs"
    echo "  db-upgrade - Run database migrations"
    echo "  db-status  - Check database migration status"
    exit 1
fi

# Check if environment file exists
ENV_FILE_PATH="../environments/$ENV_FILE"
if [ ! -f "$ENV_FILE_PATH" ]; then
    print_error "Environment file $ENV_FILE_PATH not found"
    echo "Please create the environment file first:"
    echo "  cp ../environments/env.example $ENV_FILE_PATH"
    echo "  # Then edit $ENV_FILE_PATH with your actual values"
    exit 1
fi

print_status "Using environment file: $ENV_FILE"

# Change to docker directory
cd docker

# Function to start services
start_services() {
    print_status "Starting services with environment: $ENV_FILE"
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
    echo "  ENV_FILE=$ENV_FILE ./deploy.sh logs"
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
    if [ -z "$2" ]; then
        print_status "Showing logs for all services..."
        docker-compose logs -f
    else
        print_status "Showing logs for service: $2"
        docker-compose logs -f "$2"
    fi
}

# Function to run database migrations
run_db_migrations() {
    print_status "Running database migrations..."
    cd ..
    python scripts/db.py upgrade
    print_success "Database migrations completed"
}

# Function to check database status
check_db_status() {
    print_status "Checking database migration status..."
    cd ..
    python scripts/db.py current
}

# Main command handling
case "${1:-start}" in
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
        show_logs "$@"
        ;;
    db-upgrade)
        run_db_migrations
        ;;
    db-status)
        check_db_status
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Available commands: start, stop, restart, logs, db-upgrade, db-status"
        exit 1
        ;;
esac
