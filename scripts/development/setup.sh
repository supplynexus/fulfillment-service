#!/bin/bash
# Setup script for SupplyNexus Fulfillment Service development environment

set -e

echo "🚀 Setting up SupplyNexus Fulfillment Service Development Environment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_requirements() {
    print_status "Checking requirements..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.11+ first."
        exit 1
    fi
    
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js 18+ first."
        exit 1
    fi
    
    print_status "All requirements satisfied ✓"
}

# Create environment file
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f "environment.example" ]; then
            cp environment.example .env
            print_status "Created .env file from environment.example"
            print_warning "Please update .env file with your actual configuration values"
        else
            print_error "environment.example file not found"
            exit 1
        fi
    else
        print_warning ".env file already exists, skipping creation"
    fi
}

# Setup backend
setup_backend() {
    print_status "Setting up backend..."
    
    cd backend
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_status "Created Python virtual environment"
    fi
    
    # Activate virtual environment and install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    print_status "Installed backend dependencies"
    
    cd ..
}

# Setup frontend
setup_frontend() {
    print_status "Setting up frontend..."
    
    cd frontend
    
    # Install dependencies
    npm install
    print_status "Installed frontend dependencies"
    
    cd ..
}

# Setup database
setup_database() {
    print_status "Setting up database..."
    
    # Start only PostgreSQL and Redis for database setup
    docker-compose -f docker-compose.dev.yml up -d postgres redis
    
    # Wait for PostgreSQL to be ready
    print_status "Waiting for PostgreSQL to be ready..."
    sleep 10
    
    # Run database migrations
    cd backend
    source venv/bin/activate
    
    # Initialize Alembic if not already done
    if [ ! -d "../database/migrations/versions" ]; then
        mkdir -p ../database/migrations/versions
        alembic revision --autogenerate -m "Initial migration"
        print_status "Created initial database migration"
    fi
    
    # Run migrations
    alembic upgrade head
    print_status "Applied database migrations"
    
    cd ..
}

# Start development services
start_development() {
    print_status "Starting development services..."
    
    # Start all development services
    docker-compose -f docker-compose.dev.yml up -d
    
    print_status "Development environment is ready!"
    echo ""
    echo "🎉 Setup complete! Your development environment is running:"
    echo ""
    echo "  📊 Backend API:        http://localhost:8000"
    echo "  📊 API Documentation:  http://localhost:8000/api/v1/docs"
    echo "  🖥️  Frontend:          http://localhost:3000"
    echo "  🌸 Flower (Celery):    http://localhost:5555"
    echo "  🗃️  PostgreSQL:        localhost:5432"
    echo "  ⚡ Redis:             localhost:6379"
    echo ""
    echo "To stop the development environment, run:"
    echo "  docker-compose -f docker-compose.dev.yml down"
    echo ""
    echo "To view logs, run:"
    echo "  docker-compose -f docker-compose.dev.yml logs -f [service_name]"
}

# Main execution
main() {
    check_requirements
    setup_environment
    setup_backend
    setup_frontend
    setup_database
    start_development
}

# Run main function
main
