#!/bin/bash

# SupplyNexus Backend Docker Quick Start Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 SupplyNexus Backend Docker Quick Start${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if .env file exists in parent directory
if [ ! -f "../.env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example...${NC}"
    if [ -f "../.env.example" ]; then
        cp ../.env.example ../.env
        echo -e "${GREEN}✅ Created .env file from .env.example${NC}"
        echo -e "${YELLOW}⚠️  Please edit .env file with your configuration${NC}"
    else
        echo -e "${RED}❌ .env.example not found. Please create .env file manually.${NC}"
        exit 1
    fi
fi

# Build and start the service
echo -e "${YELLOW}🔨 Building and starting backend service...${NC}"
docker-compose up --build -d

# Wait for service to be ready
echo -e "${YELLOW}⏳ Waiting for service to be ready...${NC}"
timeout=60
counter=0
while [ $counter -lt $timeout ]; do
    if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
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
echo -e "   API: ${GREEN}http://localhost:8000${NC}"
echo -e "   API Docs: ${GREEN}http://localhost:8000/api/v1/docs${NC}"
echo -e "   Health Check: ${GREEN}http://localhost:8000/api/v1/health${NC}"
echo ""
echo -e "${BLUE}🔧 Useful Commands:${NC}"
echo -e "   View logs: ${YELLOW}docker-compose logs -f backend${NC}"
echo -e "   Stop service: ${YELLOW}docker-compose down${NC}"
echo -e "   Restart service: ${YELLOW}docker-compose restart backend${NC}"
echo -e "   Shell access: ${YELLOW}docker-compose exec backend bash${NC}"
echo ""
echo -e "${BLUE}📊 Service Status:${NC}"
docker-compose ps
