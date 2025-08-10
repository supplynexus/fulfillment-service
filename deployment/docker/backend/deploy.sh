#!/bin/bash

# SupplyNexus Backend Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-development}
BACKEND_PORT=${BACKEND_PORT:-8000}
ENV_FILE="env.${ENVIRONMENT}"

echo -e "${BLUE}🚀 SupplyNexus Backend Deployment${NC}"
echo -e "${BLUE}================================${NC}"
echo -e "Environment: ${GREEN}${ENVIRONMENT}${NC}"
echo -e "Port: ${GREEN}${BACKEND_PORT}${NC}"
echo -e "Config: ${GREEN}${ENV_FILE}${NC}"
echo ""

# Check if environment file exists
if [ ! -f "../environments/${ENV_FILE}" ]; then
    echo -e "${RED}❌ Environment file ../environments/${ENV_FILE} not found${NC}"
    exit 1
fi

# Stop existing containers
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
docker-compose down --remove-orphans || true

# Build and start
echo -e "${YELLOW}🔨 Building and starting backend service...${NC}"
ENV_FILE=${ENV_FILE} BACKEND_PORT=${BACKEND_PORT} docker-compose up --build -d

# Wait for service to be healthy
echo -e "${YELLOW}⏳ Waiting for service to be healthy...${NC}"
timeout=60
counter=0
while [ $counter -lt $timeout ]; do
    if docker-compose ps | grep -q "healthy"; then
        echo -e "${GREEN}✅ Service is healthy!${NC}"
        break
    fi
    sleep 2
    counter=$((counter + 2))
    echo -n "."
done

if [ $counter -ge $timeout ]; then
    echo -e "${RED}❌ Service failed to become healthy within ${timeout}s${NC}"
    docker-compose logs backend
    exit 1
fi

# Show service status
echo -e "${GREEN}📊 Service Status:${NC}"
docker-compose ps

echo -e "${GREEN}🎉 Backend deployment completed successfully!${NC}"
echo -e "${BLUE}📍 Service URL: http://localhost:${BACKEND_PORT}${NC}"
echo -e "${BLUE}📚 API Docs: http://localhost:${BACKEND_PORT}/api/v1/docs${NC}"
echo -e "${BLUE}💚 Health Check: http://localhost:${BACKEND_PORT}/api/v1/health${NC}"
