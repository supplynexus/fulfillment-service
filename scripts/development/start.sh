#!/bin/bash
# Start development environment

echo "🚀 Starting SupplyNexus Fulfillment Service Development Environment"

docker-compose -f docker-compose.dev.yml up -d

echo "✅ Development environment started!"
echo ""
echo "Services available at:"
echo "  📊 Backend API:        http://localhost:8000"
echo "  📊 API Documentation:  http://localhost:8000/api/v1/docs"
echo "  🖥️  Frontend:          http://localhost:3000"
echo "  🌸 Flower (Celery):    http://localhost:5555"
