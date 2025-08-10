#!/bin/bash

# SupplyNexus Backend Docker Environment Start Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
ENVIRONMENT=${1:-local}
BACKEND_PORT=${BACKEND_PORT:-8000}

echo -e "${BLUE}🚀 SupplyNexus Backend Docker Start (${ENVIRONMENT})${NC}"
echo -e "${BLUE}==============================================${NC}"
echo -e "Environment: ${GREEN}${ENVIRONMENT}${NC}"
echo -e "Port: ${GREEN}${BACKEND_PORT}${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if environment file exists
ENV_FILE=".env.${ENVIRONMENT}"
if [ ! -f "${BACKEND_DIR}/${ENV_FILE}" ]; then
    echo -e "${RED}❌ Environment file ${ENV_FILE} not found${NC}"
    echo -e "${YELLOW}Available environments: local, development, staging, production${NC}"
    exit 1
fi

# Create logs directory if not exists
LOGS_DIR="logs-${ENVIRONMENT}"
mkdir -p "${BACKEND_DIR}/${LOGS_DIR}"

# Set environment variables
export ENVIRONMENT=${ENVIRONMENT}
export BACKEND_PORT=${BACKEND_PORT}

# Build and start the service
echo -e "${YELLOW}🔨 Building and starting backend service (${ENVIRONMENT})...${NC}"
cd "${BACKEND_DIR}" && docker-compose --env-file ${ENV_FILE} up --build -d

# Wait for service to be ready
echo -e "${YELLOW}⏳ Waiting for service to be ready...${NC}"
timeout=60
counter=0
while [ $counter -lt $timeout ]; do
    if curl -f http://localhost:${BACKEND_PORT}/api/v1/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Service is ready!${NC}"
        break
    fi
    sleep 2
    counter=$((counter + 2))
    echo -n "."
done

if [ $counter -ge $timeout ]; then
    echo -e "${RED}❌ Service failed to start within ${timeout}s${NC}"
    echo -e "${YELLOW}📋 Checking logs...${NC}"
    docker-compose logs backend
    exit 1
fi

# Show service information
echo -e "${GREEN}🎉 Backend service started successfully!${NC}"
echo ""
echo -e "${BLUE}📍 Service URLs:${NC}"
echo -e "   API: ${GREEN}http://localhost:${BACKEND_PORT}${NC}"
echo -e "   API Docs: ${GREEN}http://localhost:${BACKEND_PORT}/api/v1/docs${NC}"
echo -e "   Health Check: ${GREEN}http://localhost:${BACKEND_PORT}/api/v1/health${NC}"
echo ""
echo -e "${BLUE}🔧 Useful Commands:${NC}"
echo -e "   View logs: ${YELLOW}docker-compose logs -f backend${NC}"
echo -e "   Stop service: ${YELLOW}docker-compose down${NC}"
echo -e "   Restart service: ${YELLOW}docker-compose restart backend${NC}"
echo -e "   Shell access: ${YELLOW}docker-compose exec backend bash${NC}"
echo ""
echo -e "${BLUE}📊 Service Status:${NC}"
docker-compose ps
